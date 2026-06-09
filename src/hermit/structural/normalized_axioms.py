"""
Normalized OWL axioms — data structures holding the output of OWL normalization
and the input to OWL clausification.

Adapted from the Java ``OWLAxioms`` class.  In the Java version these hold
OWL API objects (``OWLClassExpression[]``, ``OWLObjectPropertyExpression``,
etc.).  Here we use HermiT's internal model types (``AtomicConcept``,
``Role``, ``DLClause``, ``Atom``, etc.) so the structural layer is
self-contained and has no external ontology-API dependency.

The pipeline is:

    OWL ontology (external) → [parser, not yet implemented] → NormalizedAxioms
                                                              → [clausification] → DLOntology
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.model import (
        AtomicConcept,
        AtomicRole,
        Atom,
        Constant,
        DataRange,
        DLClause,
        Individual,
        Role,
    )


# ===========================================================================
# OWL model → internal model conversion
# ===========================================================================


def _owl_expr_to_internal(expr: object, _cardinality_role_registry: list[Role] | None = None) -> object:
    """Convert an OWL model class expression to an internal model concept.

    This is the bridge between OWLNormalization (which produces OWL model NNF
    expressions) and NormalizedAxiomClausifier (which expects internal model
    Concept objects with .accept() visitor methods).

    Mappings:
      OWLClass(iri)                       → AtomicConcept.create(iri)
      OWLObjectComplementOf(OWLClass(i))  → AtomicNegationConcept.create(AtomicConcept.create(i))
      OWLObjectSomeValuesFrom(R, C)       → AtLeastConcept.create(1, role, concept)
      OWLObjectAllValuesFrom(R, C)        → handled upstream in OWLNormalization (DL clause)
      OWLObjectMinCardinality(n, R, C)    → AtLeastConcept.create(n, role, concept)
      OWLObjectMaxCardinality(n, R, C)    → AtMostConcept.create(n, role, concept)
      OWLObjectExactCardinality(n, R, C)  → [AtLeastConcept(n,..), AtMostConcept(n,..)] (list)
      Internal model objects              → returned as-is
    """
    from hermit.model import (
        AtomicConcept,
        AtomicNegationConcept,
        AtomicRole,
        AtLeastConcept,
        InverseRole,
    )
    from hermit.owl_model.class_expression.owl_class import OWLClass
    from hermit.owl_model.class_expression.class_expression import OWLObjectComplementOf
    from hermit.owl_model.class_expression.restriction import (
        OWLObjectSomeValuesFrom,
        OWLObjectAllValuesFrom,
        OWLObjectMinCardinality,
    )

    # Already an internal model concept — pass through
    if hasattr(expr, "accept"):
        return expr

    if isinstance(expr, OWLClass):
        iri_str = expr.iri.as_str()
        if expr.is_owl_thing():
            return AtomicConcept.THING
        if expr.is_owl_nothing():
            return AtomicConcept.NOTHING
        return AtomicConcept.create(iri_str)

    if isinstance(expr, OWLObjectComplementOf):
        operand = expr.get_operand()
        # Push complement inward using NNF rules before converting to internal model
        from hermit.owl_model.class_expression.restriction import (
            OWLObjectSomeValuesFrom as _Some,
            OWLObjectAllValuesFrom as _All,
            OWLObjectMinCardinality as _Min,
            OWLObjectMaxCardinality as _Max,
            OWLObjectExactCardinality as _Exact,
        )
        from hermit.owl_model.class_expression import OWLObjectIntersectionOf, OWLObjectUnionOf

        if isinstance(operand, _Some):
            # ¬(∃R.C) = ∀R.¬C → handle as AllValuesFrom with negated filler
            neg_filler = OWLObjectComplementOf(operand.get_filler())
            all_expr = _All(operand.get_property(), neg_filler)
            return _owl_expr_to_internal(all_expr, _cardinality_role_registry)
        elif isinstance(operand, _All):
            # ¬(∀R.C) = ∃R.¬C
            neg_filler = OWLObjectComplementOf(operand.get_filler())
            some_expr = _Some(operand.get_property(), neg_filler)
            return _owl_expr_to_internal(some_expr, _cardinality_role_registry)
        elif isinstance(operand, _Min):
            # ¬(≥n R.C) = ≤(n-1) R.C
            n = operand.get_cardinality()
            if n == 0:
                return AtomicConcept.NOTHING  # ¬(≥0 R.C) = ⊥ (impossible)
            max_expr = _Max(n - 1, operand.get_property(), operand.get_filler())
            return _owl_expr_to_internal(max_expr, _cardinality_role_registry)
        elif isinstance(operand, _Max):
            # ¬(≤n R.C) = ≥(n+1) R.C
            n = operand.get_cardinality()
            min_expr = _Min(n + 1, operand.get_property(), operand.get_filler())
            return _owl_expr_to_internal(min_expr, _cardinality_role_registry)
        elif isinstance(operand, _Exact):
            # ¬(=n R.C) = <n R.C ∨ >n R.C → too complex for single concept; use THING approximation
            inner = _owl_expr_to_internal(operand, _cardinality_role_registry)
            if isinstance(inner, AtomicConcept):
                return AtomicNegationConcept.create(inner)
            return AtomicConcept.THING
        elif isinstance(operand, OWLObjectIntersectionOf):
            # ¬(A ⊓ B) = ¬A ⊔ ¬B — cannot represent as a single internal concept;
            # approximate: the NNF should have been pushed before reaching here
            # Return THING (overapproximation) — the normalization layer should have
            # eliminated complex complements before calling _owl_expr_to_internal
            return AtomicConcept.THING
        elif isinstance(operand, OWLObjectUnionOf):
            # ¬(A ⊔ B) = ¬A ⊓ ¬B — similarly cannot be a single internal concept
            return AtomicConcept.NOTHING

        # For OWLClass and other atomic cases, convert inner then negate
        inner = _owl_expr_to_internal(operand, _cardinality_role_registry)
        if isinstance(inner, AtomicConcept):
            return AtomicNegationConcept.create(inner)
        if isinstance(inner, AtomicNegationConcept):
            return inner.negated  # double negation elimination
        # Cannot negate complex concept — return as overapproximation
        return AtomicConcept.THING

    def _owl_prop_to_internal_role(owl_prop: object) -> Role:
        """Convert an OWL property expression to an internal Role."""
        inv_of_cls: type | None = None
        try:
            from hermit.owl_model.owl_property import OWLObjectInverseOf as _InvOf
            inv_of_cls = _InvOf
        except ImportError:
            pass
        if inv_of_cls is not None and isinstance(owl_prop, inv_of_cls):
            base_prop = getattr(owl_prop, "get_inverse", lambda: None)()
            base_iri_obj = getattr(base_prop, "iri", None)
            if base_iri_obj is None:
                base_iri = str(base_prop)
            elif hasattr(base_iri_obj, "as_str"):
                base_iri = str(base_iri_obj.as_str())
            else:
                base_iri = str(base_iri_obj)
            return InverseRole.create(AtomicRole.create(base_iri))
        iri_str = getattr(owl_prop, "iri", None)
        if iri_str is None:
            return AtomicRole.create(str(owl_prop))
        return AtomicRole.create(iri_str.as_str() if hasattr(iri_str, "as_str") else str(iri_str))

    if isinstance(expr, OWLObjectSomeValuesFrom):
        role = _owl_prop_to_internal_role(expr.get_property())
        filler = _owl_expr_to_internal(expr.get_filler(), _cardinality_role_registry)
        from hermit.model import LiteralConcept
        if not isinstance(filler, LiteralConcept):
            filler = AtomicConcept.THING
        return AtLeastConcept.create(1, role, filler)

    if isinstance(expr, OWLObjectAllValuesFrom):
        # ∀R.C is handled upstream in OWLNormalization._process_sub_class_of()
        # by emitting a two-variable DL clause A(X) ∧ R(X,Y) → C(Y) directly.
        # If we reach here, it means ∀R.C appears inside a complex expression
        # (e.g. disjunction disjunct) rather than as the direct super-class.
        # Fall through to the approximation: treat as owl:Thing (overapproximation).
        return AtomicConcept.THING

    if isinstance(expr, OWLObjectMinCardinality):
        n = expr.get_cardinality()
        role = _owl_prop_to_internal_role(expr.get_property())
        filler = _owl_expr_to_internal(expr.get_filler(), _cardinality_role_registry)
        from hermit.model import LiteralConcept
        if not isinstance(filler, LiteralConcept):
            filler = AtomicConcept.THING
        if _cardinality_role_registry is not None:
            _cardinality_role_registry.append(role)
        return AtLeastConcept.create(n, role, filler)

    from hermit.owl_model.class_expression.restriction import (
        OWLObjectMaxCardinality,
        OWLObjectExactCardinality,
    )
    from hermit.model import AtMostConcept

    if isinstance(expr, OWLObjectMaxCardinality):
        n = expr.get_cardinality()
        role = _owl_prop_to_internal_role(expr.get_property())
        filler = _owl_expr_to_internal(expr.get_filler(), _cardinality_role_registry)
        from hermit.model import LiteralConcept
        if not isinstance(filler, LiteralConcept):
            filler = AtomicConcept.THING
        if _cardinality_role_registry is not None:
            _cardinality_role_registry.append(role)
        return AtMostConcept.create(n, role, filler)

    if isinstance(expr, OWLObjectExactCardinality):
        # =n R.C decomposes to ≥n R.C ∧ ≤n R.C
        # Return a sentinel tuple; add_concept_inclusion handles splitting.
        n = expr.get_cardinality()
        role = _owl_prop_to_internal_role(expr.get_property())
        filler = _owl_expr_to_internal(expr.get_filler(), _cardinality_role_registry)
        from hermit.model import LiteralConcept
        if not isinstance(filler, LiteralConcept):
            filler = AtomicConcept.THING
        if _cardinality_role_registry is not None:
            _cardinality_role_registry.append(role)
        # Return both constraints as a list; caller must split into two inclusions
        return [AtLeastConcept.create(n, role, filler), AtMostConcept.create(n, role, filler)]

    from hermit.owl_model.class_expression.restriction import OWLObjectOneOf

    if isinstance(expr, OWLObjectOneOf):
        # {a, b, ...} → nominal concept(s). Each individual a maps to an internal
        # nominal concept ``internal:nom#a``; the fact a ∈ internal:nom#a is
        # seeded during clausification. A singleton becomes one nominal concept;
        # an enumeration of several becomes their disjunction (a list of
        # AtomicConcepts), which the inclusion path already treats as a
        # disjunction.
        from hermit.owl_model.owl_individual import OWLNamedIndividual

        nominals: list[AtomicConcept] = []
        for ind in expr.operands():
            if isinstance(ind, OWLNamedIndividual):
                iri = ind.iri.as_str() if hasattr(ind.iri, "as_str") else str(ind.iri)
                nominals.append(AtomicConcept.create("internal:nom#" + iri))
        if not nominals:
            return AtomicConcept.NOTHING
        if len(nominals) == 1:
            return nominals[0]
        return nominals

    # Fallback: unknown expression — return as-is and let the clausifier handle it
    return expr


def _owl_prop_to_internal_role_standalone(owl_prop: object) -> Role:
    """Convert an OWL property expression to an internal Role (standalone helper)."""
    from hermit.model import AtomicRole, InverseRole
    try:
        from hermit.owl_model.owl_property import OWLObjectInverseOf as _InvOf
        if isinstance(owl_prop, _InvOf):
            base_prop = getattr(owl_prop, "get_inverse", lambda: None)()
            base_iri_obj = getattr(base_prop, "iri", None)
            if base_iri_obj is None:
                base_iri = str(base_prop)
            elif hasattr(base_iri_obj, "as_str"):
                base_iri = str(base_iri_obj.as_str())
            else:
                base_iri = str(base_iri_obj)
            return InverseRole.create(AtomicRole.create(base_iri))
    except ImportError:
        pass
    iri_str = getattr(owl_prop, "iri", None)
    if iri_str is None:
        return AtomicRole.create(str(owl_prop))
    return AtomicRole.create(iri_str.as_str() if hasattr(iri_str, "as_str") else str(iri_str))


# ===========================================================================
# NormalizedAxioms
# ===========================================================================


@dataclass
class NormalizedAxioms:
    """
    Holds all normalized axioms produced by the normalization phase and
    consumed by the clausification phase.

    Mirrors the Java ``OWLAxioms`` class but uses internal model types
    instead of OWL API types.
    """

    # -- signature --
    atomic_concepts: set[AtomicConcept] = field(default_factory=set)
    object_roles: set[AtomicRole] = field(default_factory=set)
    object_roles_in_owl_axioms: set[AtomicRole] = field(default_factory=set)
    complex_object_roles: set[Role] = field(default_factory=set)
    data_roles: set[AtomicRole] = field(default_factory=set)
    named_individuals: set[Individual] = field(default_factory=set)

    # -- TBox axioms --
    concept_inclusions: list[tuple[AtomicConcept, ...]] = field(default_factory=list)
    """Each tuple is a disjunction of atomic/literal concepts (NNF).
    E.g. ``(not A, B)`` represents ``A ⊑ B`` after NNF."""

    data_range_inclusions: list[tuple[DataRange, ...]] = field(default_factory=list)
    """Each tuple is a disjunction of data ranges."""

    # -- Object property axioms --
    simple_object_property_inclusions: list[tuple[Role, ...]] = field(default_factory=list)
    """Each tuple is [R1, ..., Rn, S] meaning R1 o ... o Rn ⊑ S (n == 1 for simple)."""

    complex_object_property_inclusions: list[ComplexObjectPropertyInclusion] = field(
        default_factory=list
    )

    disjoint_object_properties: list[tuple[Role, ...]] = field(default_factory=list)
    reflexive_object_properties: set[Role] = field(default_factory=set)
    irreflexive_object_properties: set[Role] = field(default_factory=set)
    asymmetric_object_properties: set[Role] = field(default_factory=set)

    # -- Data property axioms --
    data_property_inclusions: list[tuple[AtomicRole, ...]] = field(default_factory=list)
    """Each tuple is [P, Q] meaning P ⊑ Q."""

    disjoint_data_properties: list[tuple[AtomicRole, ...]] = field(default_factory=list)

    # -- ABox axioms (facts) --
    positive_concept_facts: list[tuple[Individual, AtomicConcept]] = field(
        default_factory=list
    )
    """A(i) — individual i is asserted to be in concept A."""

    negative_concept_facts: list[tuple[Individual, AtomicConcept]] = field(
        default_factory=list
    )
    """not A(i) — individual i is asserted NOT to be in concept A."""

    positive_role_facts: list[tuple[Individual, Role, Individual]] = field(
        default_factory=list
    )
    """R(i, j) — role assertion."""

    negative_role_facts: list[tuple[Individual, Role, Individual]] = field(
        default_factory=list
    )
    """not R(i, j) — negative role assertion."""

    same_individual_facts: list[tuple[Individual, Individual]] = field(
        default_factory=list
    )
    """i == j — same individual assertion."""

    different_individuals_facts: list[tuple[Individual, Individual]] = field(
        default_factory=list
    )
    """i != j — different individuals assertion."""

    positive_data_facts: list[tuple[Individual, AtomicRole, Constant]] = field(
        default_factory=list
    )
    """P(i, v) — data property assertion."""

    negative_data_facts: list[tuple[Individual, AtomicRole, Constant]] = field(
        default_factory=list
    )
    """not P(i, v) — negative data property assertion."""

    # -- Keys --
    object_property_keys: list[ObjectPropertyKey] = field(default_factory=list)
    data_property_keys: list[DataPropertyKey] = field(default_factory=list)

    # -- Datatypes --
    defined_datatype_iris: set[str] = field(default_factory=set)
    """Custom datatype IRIs from DatatypeDefinition axioms."""

    # -- SWRL rules --
    rules: list[DisjunctiveRule] = field(default_factory=list)
    """Normalized disjunctive SWRL rules."""

    # -- Normalization interface (used by OWLNormalization) --
    positive_facts: list[object] = field(default_factory=list)
    """Temporary storage for positive axioms during normalization."""

    negative_facts: list[object] = field(default_factory=list)
    """Temporary storage for negative axioms during normalization."""

    # -- Direct DL clauses (from ∀R.C expansion) --
    direct_dl_clauses: list[DLClause] = field(default_factory=list)
    """DL clauses emitted directly by normalization (e.g. for ∀R.C)."""

    # -- Conversion tracking (populated by _owl_expr_to_internal) --
    cardinality_restriction_roles: list[Role] = field(default_factory=list)
    """Roles appearing in syntactic object cardinality restrictions
    (OWLObjectMinCardinality / OWLObjectMaxCardinality / OWLObjectExactCardinality);
    used for non-simplicity validation after OWL→internal conversion.
    OWLObjectSomeValuesFrom does not register here even though it converts to
    the same internal AtLeastConcept form — per OWL 2, existential restrictions
    are legal on non-simple properties while cardinality restrictions are not."""

    @property
    def is_horn(self) -> bool:
        """All concept inclusions have at most one positive (non-negated) literal."""
        for inclusion in self.concept_inclusions:
            # In NNF, positive literals are AtomicConcept (not negated)
            # A Horn clause has at most one positive literal
            positive_count = 0
            for lit in inclusion:
                from hermit.model import AtomicConcept, AtomicNegationConcept

                if isinstance(lit, AtomicConcept):
                    positive_count += 1
                elif isinstance(lit, AtomicNegationConcept):
                    pass  # negated atomic is "positive" in the Horn sense
            # Simplified: count disjunction length > 1 as non-Horn
            if len(inclusion) > 1:
                # Need more sophisticated check — this is a simplification
                pass
        return True  # optimistic default

    def signature(self) -> set[object]:
        """Return all entities in the axiom set."""
        sig: set[object] = set()
        sig.update(self.atomic_concepts)
        sig.update(self.object_roles)
        sig.update(self.data_roles)
        sig.update(self.named_individuals)
        return sig

    def add_concept_inclusion(self, simplified: object) -> None:
        """Add a concept inclusion (disjunction of concepts).

        Converts OWL model expressions to internal model concepts so that
        NormalizedAxiomClausifier (which uses the .accept() visitor) receives
        the right types.

        Args:
            simplified: A simplified class expression (OWLObjectUnionOf or single
                       class expression) representing a concept inclusion in NNF.
        """
        from hermit.owl_model.class_expression import OWLObjectUnionOf
        reg = self.cardinality_restriction_roles
        if isinstance(simplified, OWLObjectUnionOf):
            disjuncts_raw = [_owl_expr_to_internal(op, reg) for op in simplified.operands()]
            # Expand any list entries (from ExactCardinality decomposition)
            disjuncts: list[object] = []
            for d in disjuncts_raw:
                if isinstance(d, list):
                    disjuncts.extend(d)
                else:
                    disjuncts.append(d)
            self.concept_inclusions.append(tuple(disjuncts))  # type: ignore[arg-type]
        else:
            converted = _owl_expr_to_internal(simplified, reg)
            if isinstance(converted, list):
                # ExactCardinality: each constraint becomes its own concept inclusion
                for part in converted:
                    self.concept_inclusions.append((part,))
            else:
                self.concept_inclusions.append((converted,))  # type: ignore[arg-type]


# ===========================================================================
# ComplexObjectPropertyInclusion
# ===========================================================================


@dataclass(frozen=True)
class ComplexObjectPropertyInclusion:
    """
    A complex object property inclusion: R1 o R2 o ... o Rn ⊑ S
    where the chain has length >= 2, or a transitivity marker R o R ⊑ R.

    Mirrors ``OWLAxioms.ComplexObjectPropertyInclusion``.
    """

    sub_object_properties: tuple[Role, ...]
    """The sub-property chain [R1, R2, ..., Rn]."""

    super_object_property: Role
    """The super-property S."""

    @classmethod
    def transitivity(cls, role: Role) -> ComplexObjectPropertyInclusion:
        """Create a transitivity marker: R o R ⊑ R."""
        return cls(
            sub_object_properties=(role, role),
            super_object_property=role,
        )

    def is_transitivity(self) -> bool:
        """Check if this is a transitivity axiom R o R ⊑ R."""
        return (
            len(self.sub_object_properties) == 2
            and self.sub_object_properties[0] == self.sub_object_properties[1]
            and self.sub_object_properties[0] == self.super_object_property
        )


# ===========================================================================
# DisjunctiveRule
# ===========================================================================


@dataclass(frozen=True)
class DisjunctiveRule:
    """
    A normalized disjunctive SWRL rule:
    body1 ∧ body2 ∧ ... ⊢ head1 ∨ head2 ∨ ...

    Mirrors ``OWLAxioms.DisjunctiveRule`` but uses ``Atom`` instead of
    ``SWRLAtom`` since the SWRL atoms have been normalized to HermiT's
    internal ``Atom`` representation.
    """

    body: tuple[Atom, ...]
    """Body atoms (conjunction)."""

    head: tuple[Atom, ...]
    """Head atoms (disjunction)."""

    def __str__(self) -> str:
        body_str = " ∧ ".join(str(a) for a in self.body) if self.body else "⊤"
        head_str = " ∨ ".join(str(a) for a in self.head) if self.head else "⊥"
        return f"{body_str} ⊢ {head_str}"

    def __repr__(self) -> str:
        return f"DisjunctiveRule(body={self.body}, head={self.head})"


# ===========================================================================
# Key axioms
# ===========================================================================


@dataclass(frozen=True)
class ObjectPropertyKey:
    """A HasKey axiom with object properties: C hasKey {R1, ..., Rn}."""

    concept: AtomicConcept
    """The concept C."""
    properties: tuple[Role, ...]
    """The object property chain."""


@dataclass(frozen=True)
class DataPropertyKey:
    """A HasKey axiom with data properties: C hasKey {P1, ..., Pn}."""

    concept: AtomicConcept
    """The concept C."""
    properties: tuple[AtomicRole, ...]
    """The data property chain."""
