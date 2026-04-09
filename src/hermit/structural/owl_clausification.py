"""
OWL Clausification — converts normalized axioms into DL clauses.

Port of ``org.semanticweb.HermiT.structural.OWLClausification``.

This is the critical bridge between the normalization layer and the tableau
reasoner.  It takes a ``NormalizedAxioms`` instance (produced by the
normalization phase) and a collection of ``DescriptionGraph`` objects, and
produces a ``DLOntology`` containing:

- **DLClause** objects — universal rules of the form head :- body
- **Positive facts** — ground atoms asserted to be true
- **Negative facts** — ground atoms asserted to be false
- Metadata: atomic concepts, roles, individuals, expressivity flags

The clausification process handles:
- Normalized concept inclusion axioms (GCIs)
- Normalized data range inclusion axioms
- Object and data property inclusion axioms
- Property characteristics (asymmetric, reflexive, irreflexive, disjoint)
- Bottom data property clauses
- HasKey axioms (object and data property keys)
- Description graph start clauses
- ABox facts (concept assertions, role assertions, same/different individuals)
- SWRL rules (disjunctive rules)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hermit.model import (
    AtLeastConcept,
    AtLeastDataRange,
    AtMostConcept,
    Atom,
    AtomicConcept,
    AtomicNegationConcept,
    AtomicRole,
    Concept,
    Constant,
    ConstantEnumeration,
    DataRange,
    DatatypeRestriction,
    DescriptionGraph,
    DLOntology,
    DLClause,
    Equality,
    ExistsDescriptionGraph,
    Individual,
    Inequality,
    InternalDatatype,
    InverseRole,
    LiteralDataRange,
    Prefixes,
    Role,
    Term,
    Variable,
)
from hermit.structural.normalized_axioms import (
    DataPropertyKey,
    DisjunctiveRule,
    NormalizedAxioms,
    ObjectPropertyKey,
)

if TYPE_CHECKING:
    from collections.abc import Collection

# ---------------------------------------------------------------------------
# Standard variables used throughout clausification
# ---------------------------------------------------------------------------

X = Variable.create("X")
Y = Variable.create("Y")
Z = Variable.create("Z")


# ===========================================================================
# OWLClausification
# ===========================================================================

class OWLClausification:
    """
    Converts normalized axioms and description graphs into a DL ontology
    (set of DL clauses + facts).

    Usage::

        clausification = OWLClausification(warning_monitor)
        dl_ontology = clausification.clausify(axioms, description_graphs)
    """

    def __init__(
        self,
        warning_monitor: Any | None = None,
        ignore_unsupported_datatypes: bool = False,
    ) -> None:
        self._warning_monitor = warning_monitor
        self._ignore_unsupported_datatypes = ignore_unsupported_datatypes

    def clausify(
        self,
        axioms: NormalizedAxioms,
        description_graphs: Collection[DescriptionGraph] | None = None,
        ontology_iri: str | None = None,
    ) -> DLOntology:
        """
        Clausify the given normalized axioms into a DL ontology.

        Parameters
        ----------
        axioms : NormalizedAxioms
            The normalized axioms to clausify.
        description_graphs : collection of DescriptionGraph, optional
            Description graphs for existential expansion.
        ontology_iri : str, optional
            IRI for the resulting ontology.
        """
        if description_graphs is None:
            description_graphs = []
        if ontology_iri is None:
            ontology_iri = "urn:hermit:kb"

        dl_clauses: set[DLClause] = set()
        positive_facts: set[Atom] = set()
        negative_facts: set[Atom] = set()
        all_unknown_datatype_restrictions: set[DatatypeRestriction] = set()

        # -- Non-simple property validation and rewriting --
        from hermit.structural.object_property_inclusion_manager import ObjectPropertyInclusionManager
        opm = ObjectPropertyInclusionManager()
        opm.rewrite_axioms(axioms)

        # -- Property inclusion clauses --
        self._clausify_property_inclusions(axioms, dl_clauses)

        # -- Bottom data property clause --
        if self._uses_bottom_data_property(axioms):
            body_atom = Atom.create(AtomicRole.BOTTOM_DATA_ROLE, X, Y)
            dl_clauses.add(DLClause.create((), (body_atom,)))

        # -- Data range converter (needed for subsequent steps) --
        data_range_converter = DataRangeConverter(
            self._warning_monitor,
            set(axioms.defined_datatype_iris),
            all_unknown_datatype_restrictions,
            self._ignore_unsupported_datatypes,
        )

        # -- Concept inclusion clauses --
        clausifier = NormalizedAxiomClausifier(data_range_converter, positive_facts)
        for inclusion in axioms.concept_inclusions:
            for concept in inclusion:
                concept.accept(clausifier)
            dl_clause = clausifier.get_dl_clause()
            dl_clauses.add(dl_clause.get_safe_version(AtomicConcept.THING))
            # Flush pairwise clauses emitted by visit_at_most_concept
            extra = getattr(clausifier, "_extra_clauses", None)
            if extra:
                for ec in extra:
                    dl_clauses.add(ec.get_safe_version(AtomicConcept.THING))
                extra.clear()

        # -- Data range inclusion clauses --
        data_range_clausifier = NormalizedDataRangeAxiomClausifier(
            data_range_converter, set(axioms.defined_datatype_iris)
        )
        for inclusion in axioms.data_range_inclusions:  # type: ignore[assignment]
            for data_range in inclusion:
                data_range.accept(data_range_clausifier)
            dl_clause = data_range_clausifier.get_dl_clause()
            dl_clauses.add(
                dl_clause.get_safe_version(InternalDatatype.RDFS_LITERAL)  # type: ignore[arg-type]
            )

        # -- Direct DL clauses (e.g. from ∀R.C normalization) --
        from hermit.model import DLClause as _DLClause
        for direct_clause in getattr(axioms, "direct_dl_clauses", []):
            if isinstance(direct_clause, _DLClause):
                dl_clauses.add(direct_clause.get_safe_version(AtomicConcept.THING))

        # -- Key clauses --
        for obj_key in axioms.object_property_keys:
            dl_clauses.add(self._clausify_object_key(obj_key))
        for data_key in axioms.data_property_keys:
            dl_clauses.add(self._clausify_data_key(data_key))

        # -- Fact clauses --
        fact_clausifier = FactClausifier(
            data_range_converter, positive_facts, negative_facts
        )
        fact_clausifier.clausify_facts(axioms)

        # -- Description graph start clauses --
        for dg in description_graphs:
            dg.produce_start_dl_clauses(dl_clauses)

        # -- Collect signature --
        individuals = set(axioms.named_individuals)

        # Tag all named individuals with INTERNAL_NAMED if keys or rules exist
        if axioms.object_property_keys or axioms.data_property_keys or axioms.rules:
            for individual in individuals:
                positive_facts.add(
                    Atom.create(AtomicConcept.INTERNAL_NAMED, individual)
                )

        # -- Expressivity flags --
        # (These are computed but not passed to DLOntology in the current model)
        self._has_inverses(axioms)
        self._has_nominals_check(axioms)

        # -- SWRL rule clausification --
        if axioms.rules:
            NormalizedRuleClausifier(
                set(axioms.object_roles_in_owl_axioms),
                description_graphs,
                data_range_converter,
                dl_clauses,
            ).process_rules(axioms.rules)

        return DLOntology(
            ontology_iri=ontology_iri,
            dl_clauses=frozenset(dl_clauses),
            positive_facts=frozenset(positive_facts),
            negative_facts=frozenset(negative_facts),
        )

    # -- Helpers ----------------------------------------------------------------

    def _clausify_property_inclusions(
        self,
        axioms: NormalizedAxioms,
        dl_clauses: set[DLClause],
    ) -> None:
        """Generate DL clauses from object and data property inclusions and characteristics."""
        # Simple object property inclusions: R ⊑ S
        for inclusion in axioms.simple_object_property_inclusions:
            if len(inclusion) >= 2:
                sub_role = inclusion[0]
                super_role = inclusion[1]
                sub_atom = _role_atom(sub_role, X, Y)
                super_atom = _role_atom(super_role, X, Y)
                dl_clauses.add(DLClause.create((super_atom,), (sub_atom,)))

        # Data property inclusions: P ⊑ Q
        for inclusion in axioms.data_property_inclusions:
            if len(inclusion) >= 2:
                sub_prop = Atom.create(inclusion[0], X, Y)
                super_prop = Atom.create(inclusion[1], X, Y)
                dl_clauses.add(DLClause.create((super_prop,), (sub_prop,)))

        # Asymmetric: R(X,Y) ∧ R(Y,X) -> ⊥
        for obj_prop in axioms.asymmetric_object_properties:
            role_atom = _role_atom(obj_prop, X, Y)
            inverse_role_atom = _role_atom(obj_prop, Y, X)
            dl_clauses.add(DLClause.create((), (role_atom, inverse_role_atom)))

        # Reflexive: Thing(X) -> R(X,X)
        for obj_prop in axioms.reflexive_object_properties:
            role_atom = _role_atom(obj_prop, X, X)
            body_atom = Atom.create(AtomicConcept.THING, X)
            dl_clauses.add(DLClause.create((role_atom,), (body_atom,)))

        # Irreflexive: R(X,X) -> ⊥
        for obj_prop in axioms.irreflexive_object_properties:
            role_atom = _role_atom(obj_prop, X, X)
            dl_clauses.add(DLClause.create((), (role_atom,)))

        # Disjoint object properties: R_i(X,Y) ∧ R_j(X,Y) -> ⊥
        for properties in axioms.disjoint_object_properties:
            for i in range(len(properties)):
                for j in range(i + 1, len(properties)):
                    atom_i = _role_atom(properties[i], X, Y)
                    atom_j = _role_atom(properties[j], X, Y)
                    dl_clauses.add(DLClause.create((), (atom_i, atom_j)))

        # Disjoint data properties: P_i(X,Y) ∧ P_j(X,Z) -> Y ≠ Z
        for properties in axioms.disjoint_data_properties:
            for i in range(len(properties)):
                for j in range(i + 1, len(properties)):
                    atom_i = Atom.create(properties[i], X, Y)
                    atom_j = Atom.create(properties[j], X, Z)
                    atom_ineq = Atom.create(Inequality.INSTANCE, Y, Z)  # type: ignore[arg-type]
                    dl_clauses.add(DLClause.create((atom_ineq,), (atom_i, atom_j)))

    @staticmethod
    def _uses_bottom_data_property(axioms: NormalizedAxioms) -> bool:
        """Check if bottom data property appears in data property inclusions."""
        for inclusion in axioms.data_property_inclusions:
            for role in inclusion:
                if role is AtomicRole.BOTTOM_DATA_ROLE:
                    return True
        return False

    @staticmethod
    def _has_inverses(axioms: NormalizedAxioms) -> bool:
        """Check if any roles are inverse roles."""
        for role in axioms.complex_object_roles:
            if isinstance(role, InverseRole):
                return True
        for inclusion in axioms.simple_object_property_inclusions:
            for role in inclusion:
                if isinstance(role, InverseRole):
                    return True
        return False

    @staticmethod
    def _has_nominals_check(axioms: NormalizedAxioms) -> bool:
        """Check if the axioms contain nominals."""
        for inclusion in axioms.concept_inclusions:
            for concept in inclusion:
                if isinstance(concept, AtomicConcept):
                    if concept.iri.startswith("internal:nom#"):
                        return True
        return False

    @staticmethod
    def _clausify_object_key(key: ObjectPropertyKey) -> DLClause:
        """Clausify an object property HasKey axiom: C hasKey {R1,...,Rn}."""
        head_atoms: list[Atom] = []
        body_atoms: list[Atom] = []

        x1 = Variable.create("X1")
        x2 = Variable.create("X2")

        # Head: X1 == X2
        head_atoms.append(Atom.create(Equality.INSTANCE, x1, x2))  # type: ignore[arg-type]

        # Body: both are named individuals
        body_atoms.append(Atom.create(AtomicConcept.INTERNAL_NAMED, x1))
        body_atoms.append(Atom.create(AtomicConcept.INTERNAL_NAMED, x2))

        # Concept expression
        concept = key.concept
        if not concept.is_always_true():
            body_atoms.append(Atom.create(concept, x1))
            body_atoms.append(Atom.create(concept, x2))

        # Object properties — go to body
        y_index = 1
        for prop in key.properties:
            y_var = Variable.create(f"Y{y_index}")
            y_index += 1
            body_atoms.append(_role_atom(prop, x1, y_var))
            body_atoms.append(_role_atom(prop, x2, y_var))
            body_atoms.append(Atom.create(AtomicConcept.INTERNAL_NAMED, y_var))

        return DLClause.create(tuple(head_atoms), tuple(body_atoms))

    @staticmethod
    def _clausify_data_key(key: DataPropertyKey) -> DLClause:
        """Clausify a data property HasKey axiom: C hasKey {P1,...,Pn}."""
        head_atoms: list[Atom] = []
        body_atoms: list[Atom] = []

        x1 = Variable.create("X1")
        x2 = Variable.create("X2")

        # Head: X1 == X2
        head_atoms.append(Atom.create(Equality.INSTANCE, x1, x2))  # type: ignore[arg-type]

        # Body: both are named individuals
        body_atoms.append(Atom.create(AtomicConcept.INTERNAL_NAMED, x1))
        body_atoms.append(Atom.create(AtomicConcept.INTERNAL_NAMED, x2))

        # Concept expression
        concept = key.concept
        if not concept.is_always_true():
            body_atoms.append(Atom.create(concept, x1))
            body_atoms.append(Atom.create(concept, x2))

        # Data properties — go to body, head gets inequality
        y_index = 1
        for prop in key.properties:
            y_var = Variable.create(f"Y{y_index}")
            y_index += 1
            body_atoms.append(Atom.create(prop, x1, y_var))

            y2_var = Variable.create(f"Y{y_index}")
            y_index += 1
            body_atoms.append(Atom.create(prop, x2, y2_var))

            head_atoms.append(Atom.create(Inequality.INSTANCE, y_var, y2_var))  # type: ignore[arg-type]

        return DLClause.create(tuple(head_atoms), tuple(body_atoms))


# ===========================================================================
# Role atom helper
# ===========================================================================

def _role_atom(role: Role, first: Term, second: Term) -> Atom:
    """Create a role atom, handling inverse roles by swapping arguments."""
    if isinstance(role, InverseRole):
        return Atom.create(role.inverse_of, second, first)
    return Atom.create(role, first, second)  # type: ignore[arg-type]


# ===========================================================================
# NormalizedAxiomClausifier
# ===========================================================================

class NormalizedAxiomClausifier:
    """
    Converts a disjunction of concepts (from a normalized concept inclusion)
    into a DL clause.

    Each concept in the disjunction is visited and generates head/body atoms:
    - AtomicConcept → head atom Concept(X)
    - AtomicNegationConcept → body atom (negation goes to body)
    - AtLeastConcept → AtLeastConcept(X) in head
    - AtLeastDataRange → AtLeastDataRange(X) in head
    - ExistsDescriptionGraph → ExistsDescriptionGraph(X) in head
    - NodeIDLessEqualThan → in head/body
    - NodeIDsAscendingOrEqual → in head
    - AnnotatedEquality → in head

    This mirrors the Java ``NormalizedAxiomClausifier`` which implements
    ``OWLClassExpressionVisitor``.
    """

    def __init__(
        self,
        data_range_converter: DataRangeConverter,
        positive_facts: set[Atom],
    ) -> None:
        self._data_range_converter = data_range_converter
        self._head_atoms: list[Atom] = []
        self._body_atoms: list[Atom] = []
        self._positive_facts = positive_facts
        self._y_index = 0
        self._z_index = 0

    # -- DL clause construction ------------------------------------------------

    def get_dl_clause(self) -> DLClause:
        """Build the DL clause from accumulated atoms and reset state."""
        head = tuple(self._head_atoms)
        body = tuple(self._body_atoms)
        self._head_atoms.clear()
        self._body_atoms.clear()
        self._y_index = 0
        self._z_index = 0
        return DLClause.create(head, body)

    # -- Fresh variable generation --------------------------------------------

    def _ensure_y_not_zero(self) -> None:
        """Ensure y_index is at least 1 (first Y variable already used)."""
        if self._y_index == 0:
            self._y_index += 1

    def _next_y(self) -> Variable:
        """
        Return fresh Y variable: Y on first call, Y1, Y2, ... on subsequent.
        """
        if self._y_index == 0:
            result = Y
        else:
            result = Variable.create(f"Y{self._y_index}")
        self._y_index += 1
        return result

    def _next_z(self) -> Variable:
        """
        Return fresh Z variable: Z on first call, Z1, Z2, ... on subsequent.
        """
        if self._z_index == 0:
            result = Z
        else:
            result = Variable.create(f"Z{self._z_index}")
        self._z_index += 1
        return result

    # -- Nominal handling -----------------------------------------------------

    def _concept_for_nominal(self, individual: Individual) -> AtomicConcept:
        """
        Create an atomic concept for a nominal {individual} and assert a
        positive fact linking it to the individual.
        """
        if individual.is_anonymous():
            concept = AtomicConcept.create(f"internal:anon#{individual.iri}")
        else:
            concept = AtomicConcept.create(f"internal:nom#{individual.iri}")
        self._positive_facts.add(Atom.create(concept, individual))
        return concept

    # -- Visitor methods (called via Concept.accept) ---------------------------

    def visit_atomic_concept(self, concept: AtomicConcept) -> None:
        """Atomic concept -> head atom Concept(X)."""
        self._head_atoms.append(Atom.create(concept, X))

    def visit_atomic_negation_concept(self, concept: AtomicNegationConcept) -> None:
        """
        Negated atomic concept — the complement side of an inclusion.
        In the normalized GCI ¬A ⊔ B (i.e. A ⊑ B), the negated A goes to body.
        """
        self._body_atoms.append(Atom.create(concept.negated, X))

    def visit_at_least_concept(self, concept: AtLeastConcept) -> None:
        """AtLeastConcept -> AtLeastConcept(X) in head."""
        if not concept.is_always_false():
            self._head_atoms.append(Atom.create(concept, X))

    def visit_at_least_data_range(self, concept: AtLeastDataRange) -> None:
        """AtLeastDataRange -> AtLeastDataRange(X) in head."""
        if not concept.is_always_false():
            self._head_atoms.append(Atom.create(concept, X))

    def visit_at_most_concept(self, concept: AtMostConcept) -> None:
        """AtMostConcept (≤n R.C) -> pairwise inequality DL clauses.

        For ≤n R.C: generate n+1 fresh Y-variables.  For each pair (Yi, Yj)
        with i < j, emit a separate DL clause:

            A(X) ∧ R(X, Yi) ∧ C(Yi) ∧ R(X, Yj) ∧ C(Yj) → Yi ≠ Yj

        The body atom A(X) is whatever is currently in self._body_atoms
        (the subclass of the current GCI).  The method temporarily builds
        each pairwise clause and accumulates them in self._head_atoms as a
        sentinel — the caller (clausify()) must flush each clause immediately.

        Implementation note: for ≤0 R.C we emit one clause:
            A(X) ∧ R(X, Y) ∧ C(Y) → ⊥   (empty head = contradiction)
        """
        n = concept.number
        role = concept.on_role
        filler = concept.to_concept

        # Save current body (the A(X) guard from the GCI subclass)
        saved_body = list(self._body_atoms)

        if n == 0:
            # ≤0 R.C: A(X) ∧ R(X,Y) ∧ C(Y) → ⊥
            y_var = Variable.create("Y")
            body = tuple(saved_body) + (
                Atom.create(role, X, y_var),  # type: ignore[arg-type]
                Atom.create(filler, y_var),  # type: ignore[arg-type]
            )
            self._extra_clauses: list[DLClause]
            if not hasattr(self, "_extra_clauses"):
                self._extra_clauses = []
            self._extra_clauses.append(DLClause.create((), body))
        else:
            # ≤n R.C: pairwise inequality for n+1 witnesses
            y_vars = [Variable.create(f"Y{i}") for i in range(n + 1)]
            if not hasattr(self, "_extra_clauses"):
                self._extra_clauses = []
            for i in range(n + 1):
                for j in range(i + 1, n + 1):
                    body = tuple(saved_body) + (
                        Atom.create(role, X, y_vars[i]),  # type: ignore[arg-type]
                        Atom.create(filler, y_vars[i]),  # type: ignore[arg-type]
                        Atom.create(role, X, y_vars[j]),  # type: ignore[arg-type]
                        Atom.create(filler, y_vars[j]),  # type: ignore[arg-type]
                    )
                    head = (Atom.create(Inequality.INSTANCE, y_vars[i], y_vars[j]),)  # type: ignore[arg-type]
                    self._extra_clauses.append(DLClause.create(head, body))

        # No head atoms from this visit — the clauses are in _extra_clauses
        # The caller must consume _extra_clauses after get_dl_clause()

    def visit_exists_description_graph(self, concept: ExistsDescriptionGraph) -> None:
        """ExistsDescriptionGraph -> head atom."""
        self._head_atoms.append(Atom.create(concept, X))

    def visit_other_concept(self, concept: Concept) -> None:
        """
        Fallback for concept types not handled above.
        In the normalized form this should not normally be reached for
        complex concepts; only atomic/negated-atomic and at-least variants
        appear.
        """
        # Treat as head atom if it's a DLPredicate
        if hasattr(concept, "arity"):
            self._head_atoms.append(Atom.create(concept, X))
        else:
            self._body_atoms.append(Atom.create(AtomicConcept.THING, X))


# ===========================================================================
# NormalizedDataRangeAxiomClausifier
# ===========================================================================

class NormalizedDataRangeAxiomClausifier:
    """
    Converts a disjunction of data ranges (from a normalized data range
    inclusion) into a DL clause.

    Mirrors the Java ``NormalizedDataRangeAxiomClausifier`` which implements
    ``OWLDataVisitor``.
    """

    def __init__(
        self,
        data_range_converter: DataRangeConverter,
        defined_datatype_iris: set[str],
    ) -> None:
        self._data_range_converter = data_range_converter
        self._defined_datatype_iris = defined_datatype_iris
        self._head_atoms: list[Atom] = []
        self._body_atoms: list[Atom] = []
        self._y_index = 0

    def get_dl_clause(self) -> DLClause:
        """Build the DL clause and reset state."""
        head = tuple(self._head_atoms)
        body = tuple(self._body_atoms)
        self._head_atoms.clear()
        self._body_atoms.clear()
        self._y_index = 0
        return DLClause.create(head, body)

    def _ensure_y_not_zero(self) -> None:
        if self._y_index == 0:
            self._y_index += 1

    def _next_y(self) -> Variable:
        if self._y_index == 0:
            result = Y
        else:
            result = Variable.create(f"Y{self._y_index}")
        self._y_index += 1
        return result

    # -- Visitor methods (called via DataRange.accept) -------------------------

    def visit_internal_datatype(self, dt: InternalDatatype) -> None:
        """Internal datatype reference -> head atom."""
        self._head_atoms.append(Atom.create(dt, X))

    def visit_datatype_restriction(self, dr: DatatypeRestriction) -> None:
        """Datatype with facet restrictions -> head atom."""
        self._head_atoms.append(Atom.create(dr, X))

    def visit_constant_enumeration(self, dr: ConstantEnumeration) -> None:
        """Data enumeration -> head atom."""
        self._head_atoms.append(Atom.create(dr, X))

    def visit_other_data_range(self, dr: DataRange) -> None:
        """
        Fallback — handles negated data ranges and other types.
        If it's a negated internal datatype, the inner part goes to body.
        """
        if hasattr(dr, "get_negation"):
            negated = dr.get_negation()
            if isinstance(negated, InternalDatatype):
                if not negated.is_always_true():
                    self._body_atoms.append(Atom.create(negated, X))
                return
        # Default: add to head
        if not dr.is_always_false():
            self._head_atoms.append(Atom.create(dr, X))


# ===========================================================================
# DataRangeConverter
# ===========================================================================

class DataRangeConverter:
    """
    Converts OWL data ranges to ``LiteralDataRange`` model objects.

    Handles datatypes, datatype restrictions, complement, enumerations,
    and literals.

    Mirrors the Java ``DataRangeConverter`` which implements
    ``OWLDataVisitorEx<Object>``.
    """

    def __init__(
        self,
        warning_monitor: Any | None,
        defined_datatype_iris: set[str],
        all_unknown_datatype_restrictions: set[DatatypeRestriction],
        ignore_unsupported_datatypes: bool,
    ) -> None:
        self._warning_monitor = warning_monitor
        self._defined_datatype_iris = defined_datatype_iris
        self._all_unknown_datatype_restrictions = all_unknown_datatype_restrictions
        self._ignore_unsupported_datatypes = ignore_unsupported_datatypes

    def convert_data_range(self, data_range: DataRange) -> LiteralDataRange:
        """Convert a data range to a LiteralDataRange (pass-through for already-converted)."""
        return data_range  # type: ignore[return-value]

    def visit_datatype(self, datatype_iri: str) -> LiteralDataRange:
        """Convert a datatype reference by IRI."""
        if datatype_iri == InternalDatatype.RDFS_LITERAL_IRI:
            assert InternalDatatype.RDFS_LITERAL is not None
            return InternalDatatype.RDFS_LITERAL  # type: ignore[return-value]
        if (
            datatype_iri.startswith("internal:defdata#")
            or datatype_iri in self._defined_datatype_iris
        ):
            return InternalDatatype.create(datatype_iri)  # type: ignore[return-value]

        datatype = DatatypeRestriction.create(
            datatype_iri,
            DatatypeRestriction.NO_FACET_URIS,
            DatatypeRestriction.NO_FACET_VALUES,
        )

        if datatype_iri.startswith("internal:unknown-datatype#"):
            self._all_unknown_datatype_restrictions.add(datatype)
        else:
            # Attempt validation via registry
            try:
                from hermit.datatypes.registry import DatatypeRegistry

                # Validate the datatype is known (method may not exist in all versions)
                getattr(DatatypeRegistry, "validate_datatype_restriction", lambda x: None)(datatype)
            except Exception:
                if self._ignore_unsupported_datatypes:
                    if self._warning_monitor is not None:
                        self._warning_monitor.warning(
                            f"Ignoring unsupported datatype '{datatype_iri}'."
                        )
                    self._all_unknown_datatype_restrictions.add(datatype)
                else:
                    raise

        return datatype  # type: ignore[return-value]

    def visit_data_complement_of(self, data_range: DataRange) -> LiteralDataRange:
        """Convert complement of a data range."""
        inner = self.convert_data_range(data_range)
        # For AtomicDataRange subclasses, get_negation returns the negation
        negation_fn = getattr(inner, "get_negation", None)
        if negation_fn is not None:
            result: LiteralDataRange = negation_fn()
            return result
        # Fallback: inner is already a LiteralDataRange
        return inner

    def visit_data_one_of(self, constants: list[Constant]) -> ConstantEnumeration:
        """Convert a data enumeration."""
        return ConstantEnumeration.create(constants)

    def visit_literal(
        self,
        lexical_form: str,
        datatype_iri: str,
        lang: str | None = None,
    ) -> Constant:
        """Convert a literal to a Constant."""
        try:
            if lang is not None:
                # Plain literal with language tag
                return Constant.create(
                    f"{lexical_form}@{lang}",
                    f"{Prefixes.SEMANTIC_WEB_PREFIXES['rdf:']}PlainLiteral",
                )
            else:
                return Constant.create(lexical_form, datatype_iri)
        except Exception:
            if self._ignore_unsupported_datatypes:
                if self._warning_monitor is not None:
                    self._warning_monitor.warning(
                        f"Ignoring unsupported datatype '{lexical_form}'^^{datatype_iri}."
                    )
                return Constant.create_anonymous(lexical_form)
            raise


# ===========================================================================
# FactClausifier
# ===========================================================================

class FactClausifier:
    """
    Converts ABox facts (individual axioms) into positive/negative fact atoms.

    Handles:
    - SameIndividual -> equality facts
    - DifferentIndividuals -> inequality facts
    - ClassAssertion -> positive/negative concept facts
    - ObjectPropertyAssertion -> positive role facts
    - NegativeObjectPropertyAssertion -> negative role facts
    - DataPropertyAssertion -> positive data facts
    - NegativeDataPropertyAssertion -> negative data facts

    Mirrors the Java ``FactClausifier`` which extends ``OWLAxiomVisitorAdapter``.
    """

    def __init__(
        self,
        data_range_converter: DataRangeConverter,
        positive_facts: set[Atom],
        negative_facts: set[Atom],
    ) -> None:
        self._data_range_converter = data_range_converter
        self._positive_facts = positive_facts
        self._negative_facts = negative_facts

    def clausify_facts(self, axioms: NormalizedAxioms) -> None:
        """Process all facts from the normalized axioms."""
        # Same individual facts: i == j
        for ind1, ind2 in axioms.same_individual_facts:
            self._positive_facts.add(Atom.create(Equality.INSTANCE, ind1, ind2))  # type: ignore[arg-type]

        # Different individuals facts: i != j
        for ind1, ind2 in axioms.different_individuals_facts:
            self._positive_facts.add(Atom.create(Inequality.INSTANCE, ind1, ind2))  # type: ignore[arg-type]

        # Positive concept facts: A(i)
        for individual, concept in axioms.positive_concept_facts:
            if isinstance(concept, AtomicConcept):
                self._positive_facts.add(Atom.create(concept, individual))

        # Negative concept facts: not A(i) -> A(i) in negative facts
        for individual, concept in axioms.negative_concept_facts:
            if isinstance(concept, AtomicConcept):
                self._negative_facts.add(Atom.create(concept, individual))

        # Positive role facts: R(i, j)
        for ind1, role, ind2 in axioms.positive_role_facts:
            atom = _role_atom(role, ind1, ind2)
            self._positive_facts.add(atom)

        # Negative role facts: not R(i, j)
        for ind1, role, ind2 in axioms.negative_role_facts:
            atom = _role_atom(role, ind1, ind2)
            self._negative_facts.add(atom)

        # Positive data facts: P(i, v)
        for individual, prop, value in axioms.positive_data_facts:
            self._positive_facts.add(Atom.create(prop, individual, value))

        # Negative data facts: not P(i, v)
        for individual, prop, value in axioms.negative_data_facts:
            self._negative_facts.add(Atom.create(prop, individual, value))


# ===========================================================================
# NormalizedRuleClausifier
# ===========================================================================

class NormalizedRuleClausifier:
    """
    Converts normalized disjunctive SWRL rules into DL clauses.

    Each rule ``body1 ∧ ... ∧ body_n ⊢ head_1 ∨ ... ∨ head_m``
    becomes a DL clause with body and head atoms.

    Abstract variables (SWRL variables) are restricted to named individuals
    by adding ``INTERNAL_NAMED(var)`` body atoms.

    Mirrors the Java ``NormalizedRuleClausifier`` which implements
    ``SWRLObjectVisitorEx<Atom>``.
    """

    def __init__(
        self,
        object_properties_in_owl_axioms: set[AtomicRole],
        description_graphs: Collection[DescriptionGraph],
        data_range_converter: DataRangeConverter,
        dl_clauses: set[DLClause],
    ) -> None:
        self._object_properties_in_owl_axioms = object_properties_in_owl_axioms
        self._data_range_converter = data_range_converter
        self._dl_clauses = dl_clauses
        self._head_atoms: list[Atom] = []
        self._body_atoms: list[Atom] = []
        self._abstract_variables: set[Variable] = set()

        # Collect graph object properties from description graphs
        self._graph_object_properties: set[str] = set()
        for dg in description_graphs:
            for i in range(dg.number_of_edges()):
                edge = dg.edge(i)
                self._graph_object_properties.add(edge.atomic_role.iri)

    def process_rules(self, rules: Collection[DisjunctiveRule]) -> None:
        """Clausify all rules."""
        for rule in rules:
            self._clausify_rule(rule)

    def _clausify_rule(self, rule: DisjunctiveRule) -> None:
        """Convert a single disjunctive rule to a DL clause."""
        self._head_atoms.clear()
        self._body_atoms.clear()
        self._abstract_variables.clear()

        # Process body atoms
        for atom in rule.body:
            self._body_atoms.append(atom)
            self._collect_variables(atom)

        # Process head atoms
        for atom in rule.head:
            self._head_atoms.append(atom)
            self._collect_variables(atom)

        # Restrict abstract variables to named individuals
        for var in self._abstract_variables:
            self._body_atoms.append(Atom.create(AtomicConcept.INTERNAL_NAMED, var))

        dl_clause = DLClause.create(
            tuple(self._head_atoms), tuple(self._body_atoms)
        )
        self._dl_clauses.add(dl_clause)

        self._head_atoms.clear()
        self._body_atoms.clear()
        self._abstract_variables.clear()

    def _collect_variables(self, atom: Atom) -> None:
        """Extract variables from an atom and mark them as abstract."""
        for i in range(atom.arity()):
            arg = atom.argument(i)
            if isinstance(arg, Variable):
                self._abstract_variables.add(arg)
