"""OWL axiom normalization to structural form.

Transforms OWL axioms into NormalizedAxioms by:
1. Converting to Negation Normal Form (NNF)
2. Simplifying expressions
3. Introducing fresh atomic concepts for complex subexpressions
4. Normalizing SWRL rules (Lloyd-Topor transformation)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar
from collections.abc import Iterable

if TYPE_CHECKING:
    from hermit.model import Individual, Role

from hermit.structural.expression_manager import ExpressionManager
from hermit.structural.normalized_axioms import NormalizedAxioms
from hermit.owl_model.owl_axiom import (
    OWLAxiom,
    OWLSubClassOfAxiom,
    OWLEquivalentClassesAxiom,
    OWLDisjointClassesAxiom,
    OWLClassAssertionAxiom,
    OWLSubObjectPropertyOfAxiom,
    OWLEquivalentObjectPropertiesAxiom,
    OWLDisjointObjectPropertiesAxiom,
    OWLObjectPropertyDomainAxiom,
    OWLObjectPropertyRangeAxiom,
    OWLSubDataPropertyOfAxiom,
    OWLEquivalentDataPropertiesAxiom,
    OWLDisjointDataPropertiesAxiom,
    OWLDataPropertyDomainAxiom,
    OWLDataPropertyRangeAxiom,
    OWLSameIndividualAxiom,
    OWLDifferentIndividualsAxiom,
    OWLObjectPropertyAssertionAxiom,
    OWLNegativeObjectPropertyAssertionAxiom,
    OWLDataPropertyAssertionAxiom,
    OWLNegativeDataPropertyAssertionAxiom,
    OWLFunctionalObjectPropertyAxiom,
    OWLInverseFunctionalObjectPropertyAxiom,
    OWLSymmetricObjectPropertyAxiom,
    OWLAsymmetricObjectPropertyAxiom,
    OWLTransitiveObjectPropertyAxiom,
    OWLReflexiveObjectPropertyAxiom,
    OWLIrreflexiveObjectPropertyAxiom,
    OWLFunctionalDataPropertyAxiom,
    OWLInverseObjectPropertiesAxiom,
)
from hermit.owl_model.class_expression import (
    OWLClassExpression,
    OWLClass,
    OWLObjectIntersectionOf,
    OWLObjectUnionOf,
)
from hermit.owl_model.iri import IRI


T = TypeVar("T")


def _is_sub_property_chain_axiom(axiom: object) -> bool:
    """Check if an axiom is an OWLSubPropertyChainAxiom."""
    try:
        from hermit.owl_model.owl_axiom import OWLSubPropertyChainAxiom
        return isinstance(axiom, OWLSubPropertyChainAxiom)
    except ImportError:
        return False


def _iri_str(owl_obj: object) -> str | None:
    """Extract IRI string from an OWL model object (IRI or string)."""
    iri = getattr(owl_obj, "iri", None)
    if iri is None:
        return None
    if isinstance(iri, str):
        return iri
    return iri.as_str() if hasattr(iri, "as_str") else str(iri)


def _owl_ind_to_internal(owl_ind: object) -> Individual | None:
    """Convert an OWL named individual to an internal Individual."""
    from hermit.model import Individual
    iri = _iri_str(owl_ind)
    if iri is None:
        return None
    return Individual.create(iri)


def _owl_prop_to_role(owl_prop: object) -> Role | None:
    """Convert an OWL model property expression to an internal model Role.

    Returns an AtomicRole or InverseRole, or None if conversion fails.
    """
    from hermit.model import AtomicRole, InverseRole
    from hermit.owl_model.owl_property import OWLObjectProperty, OWLObjectInverseOf

    if isinstance(owl_prop, OWLObjectProperty):
        iri_str = owl_prop.iri.as_str() if hasattr(owl_prop.iri, "as_str") else str(owl_prop.iri)
        return AtomicRole.create(iri_str)
    if isinstance(owl_prop, OWLObjectInverseOf):
        base_iri = owl_prop.get_inverse().iri
        iri_str = base_iri.as_str() if hasattr(base_iri, "as_str") else str(base_iri)
        return InverseRole.create(AtomicRole.create(iri_str))
    return None


class OWLNormalization:
    """Transforms OWL axioms to normalized form for reasoning."""

    def __init__(
        self,
        prefixes: dict[str, str] | None = None,
        first_replacement_index: int = 0,
    ) -> None:
        """Initialize OWL normalization.

        Args:
            prefixes: Optional namespace prefixes for fresh concept generation
            first_replacement_index: Starting index for fresh concept IRIs
        """
        self.prefixes = prefixes or {}
        self._replacement_counter = first_replacement_index
        self._definitions: dict[OWLClassExpression, OWLClass] = {}
        self._expression_manager = ExpressionManager()

    def process_ontology(
        self, axioms: Iterable[OWLAxiom]
    ) -> NormalizedAxioms:
        """Transform OWL axioms to normalized form.

        Args:
            axioms: OWL axioms to normalize

        Returns:
            NormalizedAxioms containing normalized inclusions and facts
        """
        normalized = NormalizedAxioms()

        for axiom in axioms:
            self._process_axiom(axiom, normalized)

        return normalized

    def _process_axiom(self, axiom: OWLAxiom, result: NormalizedAxioms) -> None:
        """Process a single axiom and add to normalized result."""
        if isinstance(axiom, OWLSubClassOfAxiom):
            self._process_sub_class_of(axiom, result)
        elif isinstance(axiom, OWLEquivalentClassesAxiom):
            self._process_equivalent_classes(axiom, result)
        elif isinstance(axiom, OWLDisjointClassesAxiom):
            self._process_disjoint_classes(axiom, result)
        elif isinstance(axiom, OWLClassAssertionAxiom):
            self._process_class_assertion(axiom, result)
        elif isinstance(axiom, OWLSubObjectPropertyOfAxiom):
            self._process_sub_object_property_of(axiom, result)
        elif _is_sub_property_chain_axiom(axiom):
            self._process_sub_property_chain(axiom, result)
        elif isinstance(axiom, OWLEquivalentObjectPropertiesAxiom):
            self._process_equivalent_object_properties(axiom, result)
        elif isinstance(axiom, OWLDisjointObjectPropertiesAxiom):
            roles = [_owl_prop_to_role(p) for p in axiom.properties()]
            valid_roles = [r for r in roles if r is not None]
            if len(valid_roles) >= 2:
                result.disjoint_object_properties.append(tuple(valid_roles))
        elif isinstance(axiom, OWLObjectPropertyDomainAxiom):
            self._process_object_property_domain(axiom, result)
        elif isinstance(axiom, OWLObjectPropertyRangeAxiom):
            self._process_object_property_range(axiom, result)
        elif isinstance(axiom, OWLSubDataPropertyOfAxiom):
            from hermit.model import AtomicRole as _AtomicRole
            sub_iri = _iri_str(axiom.get_sub_property())
            sup_iri = _iri_str(axiom.get_super_property())
            if sub_iri is not None and sup_iri is not None:
                result.data_property_inclusions.append(
                    (_AtomicRole.create(sub_iri), _AtomicRole.create(sup_iri))
                )
        elif isinstance(axiom, OWLEquivalentDataPropertiesAxiom):
            from hermit.model import AtomicRole as _AtomicRole
            props = list(axiom.properties())
            iris = [_iri_str(p) for p in props]
            valid_iris = [iri for iri in iris if iri is not None]
            # Expand P ≡ Q ≡ … into pairwise inclusions (Pi ⊑ Pj) and (Pj ⊑ Pi)
            for i in range(len(valid_iris)):
                for j in range(i + 1, len(valid_iris)):
                    r_i = _AtomicRole.create(valid_iris[i])
                    r_j = _AtomicRole.create(valid_iris[j])
                    result.data_property_inclusions.append((r_i, r_j))
                    result.data_property_inclusions.append((r_j, r_i))
        elif isinstance(axiom, OWLDisjointDataPropertiesAxiom):
            from hermit.model import AtomicRole as _AtomicRole
            data_iris = [_iri_str(p) for p in axiom.properties()]
            data_roles = [_AtomicRole.create(iri) for iri in data_iris if iri is not None]
            if len(data_roles) >= 2:
                result.disjoint_data_properties.append(tuple(data_roles))
        elif isinstance(axiom, OWLDataPropertyDomainAxiom):
            self._process_data_property_domain(axiom, result)
        elif isinstance(axiom, OWLDataPropertyRangeAxiom):
            # DataPropertyRange(P, DR): ⊤ ⊑ ∀P.DR
            from hermit.owl_model.class_expression import OWLThing
            from hermit.owl_model.class_expression.restriction import (
                OWLDataAllValuesFrom,
            )
            self._process_sub_class_of(
                OWLSubClassOfAxiom(
                    OWLThing,
                    OWLDataAllValuesFrom(axiom.get_property(), axiom.get_range()),
                ),
                result,
            )
        elif isinstance(axiom, OWLSameIndividualAxiom):
            self._process_same_individual(axiom, result)
        elif isinstance(axiom, OWLDifferentIndividualsAxiom):
            self._process_different_individuals(axiom, result)
        elif isinstance(axiom, OWLObjectPropertyAssertionAxiom):
            self._process_object_property_assertion(axiom, result)
        elif isinstance(axiom, OWLNegativeObjectPropertyAssertionAxiom):
            result.negative_facts.append(axiom)  # kept for ObjectPropertyInclusionManager
        elif isinstance(axiom, OWLDataPropertyAssertionAxiom):
            self._process_data_property_assertion(axiom, result)
        elif isinstance(axiom, OWLNegativeDataPropertyAssertionAxiom):
            result.negative_facts.append(axiom)
        elif isinstance(axiom, OWLFunctionalObjectPropertyAxiom):
            from hermit.model import Atom, DLClause, Variable, Equality
            role = _owl_prop_to_role(axiom.get_property())
            if role is not None:
                xv = Variable.create("X")
                yv = Variable.create("Y")
                zv = Variable.create("Z")
                from hermit.structural.owl_clausification import _role_atom
                head = (Atom.create(Equality.INSTANCE, yv, zv),)
                body = (_role_atom(role, xv, yv), _role_atom(role, xv, zv))
                result.direct_dl_clauses.append(DLClause.create(head, body))
        elif isinstance(axiom, OWLInverseFunctionalObjectPropertyAxiom):
            from hermit.model import Atom, DLClause, Variable, Equality
            role = _owl_prop_to_role(axiom.get_property())
            if role is not None:
                xv = Variable.create("X")
                yv = Variable.create("Y")
                zv = Variable.create("Z")
                from hermit.structural.owl_clausification import _role_atom
                head = (Atom.create(Equality.INSTANCE, xv, yv),)
                body = (_role_atom(role, xv, zv), _role_atom(role, yv, zv))
                result.direct_dl_clauses.append(DLClause.create(head, body))
        elif isinstance(axiom, OWLSymmetricObjectPropertyAxiom):
            from hermit.model import InverseRole, AtomicRole
            role = _owl_prop_to_role(axiom.get_property())
            if role is not None:
                if isinstance(role, AtomicRole):
                    inv: InverseRole | AtomicRole = InverseRole.create(role)
                else:
                    # role is InverseRole(R); its inverse is R itself
                    assert isinstance(role, InverseRole)
                    inv = role.inverse_of  # the underlying AtomicRole
                result.simple_object_property_inclusions.append((role, inv))
        elif isinstance(axiom, OWLAsymmetricObjectPropertyAxiom):
            role = _owl_prop_to_role(axiom.get_property())
            if role is not None:
                result.asymmetric_object_properties.add(role)
        elif isinstance(axiom, OWLTransitiveObjectPropertyAxiom):
            # Transitivity: R ∘ R ⊑ R  →  complex property inclusion
            from hermit.structural.normalized_axioms import ComplexObjectPropertyInclusion
            role = _owl_prop_to_role(axiom.get_property())
            if role is not None:
                result.complex_object_property_inclusions.append(
                    ComplexObjectPropertyInclusion.transitivity(role)
                )
        elif isinstance(axiom, OWLReflexiveObjectPropertyAxiom):
            role = _owl_prop_to_role(axiom.get_property())
            if role is not None:
                result.reflexive_object_properties.add(role)
        elif isinstance(axiom, OWLIrreflexiveObjectPropertyAxiom):
            role = _owl_prop_to_role(axiom.get_property())
            if role is not None:
                result.irreflexive_object_properties.add(role)
        elif isinstance(axiom, OWLFunctionalDataPropertyAxiom):
            # FunctionalDataProperty(P): ⊤ ⊑ ≤1 P.rdfs:Literal
            from hermit.owl_model.class_expression import OWLThing
            from hermit.owl_model.class_expression.restriction import (
                OWLDataMaxCardinality,
            )
            from hermit.owl_model.owl_literal import TopOWLDatatype
            self._process_sub_class_of(
                OWLSubClassOfAxiom(
                    OWLThing,
                    OWLDataMaxCardinality(
                        1, axiom.get_property(), TopOWLDatatype
                    ),
                ),
                result,
            )
        elif isinstance(axiom, OWLInverseObjectPropertiesAxiom):
            # InverseObjectProperties(S, S-): S- ≡ S⁻¹
            # Add simple inclusions: S- ⊑ S⁻¹ and S ⊑ (S-)⁻¹
            from hermit.model import AtomicRole, InverseRole
            first = _owl_prop_to_role(axiom.get_first_property())
            second = _owl_prop_to_role(axiom.get_second_property())
            if first is not None and second is not None:
                # second ⊑ first⁻¹
                first_atomic = first if isinstance(first, AtomicRole) else AtomicRole.create(str(first))
                second_atomic = second if isinstance(second, AtomicRole) else AtomicRole.create(str(second))
                result.simple_object_property_inclusions.append((second, InverseRole.create(first_atomic)))
                # first ⊑ second⁻¹
                result.simple_object_property_inclusions.append((first, InverseRole.create(second_atomic)))
            result.positive_facts.append(axiom)
        else:
            # Unknown axiom type: pass through
            result.positive_facts.append(axiom)

    def _process_sub_class_of(
        self, axiom: OWLSubClassOfAxiom, result: NormalizedAxioms
    ) -> None:
        """Process SubClassOf axiom: A ⊑ B → ¬A ⊔ B.

        Special case: A ⊑ ∀R.C is handled by emitting a two-variable DL clause
        A(X) ∧ R(X,Y) → C(Y) directly, bypassing the concept-inclusion path.
        """
        from hermit.owl_model.class_expression.restriction import (
            OWLDataAllValuesFrom,
            OWLObjectAllValuesFrom,
            OWLObjectExactCardinality,
            OWLObjectMinCardinality,
            OWLObjectMaxCardinality,
        )

        sub_expr = self._expression_manager.get_nnf(axiom.sub_class)
        super_expr = self._expression_manager.get_nnf(axiom.super_class)

        # {a1,...,an} ⊑ C distributes into the class assertions C(ai).
        from hermit.owl_model.class_expression.restriction import OWLObjectOneOf
        if isinstance(sub_expr, OWLObjectOneOf):
            for individual in sub_expr.operands():
                self._process_class_assertion(
                    OWLClassAssertionAxiom(individual, axiom.super_class), result
                )
            return

        # Intercept ∀R.C with a named sub-class: emit the two-variable DL
        # clause directly. Other sub-expressions fall through to the generic
        # inclusion path, whose union handling introduces the proper auxiliary
        # concept (a complement sub-class must become a disjunction, not a
        # positive body guard).
        if isinstance(super_expr, OWLObjectAllValuesFrom) and isinstance(
            sub_expr, OWLClass
        ):
            self._emit_all_values_from_clause(sub_expr, super_expr, result)
            return

        # Intercept ∀P.DR on a data property: emit the DL clause directly
        if isinstance(super_expr, OWLDataAllValuesFrom) and isinstance(
            sub_expr, OWLClass
        ):
            self._emit_data_all_values_from_clause(sub_expr, super_expr, result)
            return

        # Intercept =n R.C: decompose to ≥n R.C and ≤n R.C (two separate axioms)
        if isinstance(super_expr, OWLObjectExactCardinality):
            n = super_expr.get_cardinality()
            prop = super_expr.get_property()
            filler = super_expr.get_filler()
            self._process_sub_class_of(
                OWLSubClassOfAxiom(axiom.sub_class, OWLObjectMinCardinality(n, prop, filler)),
                result,
            )
            self._process_sub_class_of(
                OWLSubClassOfAxiom(axiom.sub_class, OWLObjectMaxCardinality(n, prop, filler)),
                result,
            )
            return

        # ¬sub ⊔ super
        complement = self._expression_manager.get_complement_nnf(sub_expr)
        if isinstance(complement, OWLObjectUnionOf):
            # Flatten: ¬A ⊔ C ⊔ B becomes one inclusion
            operands = list(complement.operands()) + [super_expr]
            inclusion = OWLObjectUnionOf(operands)  # type: ignore[arg-type]
        else:
            inclusion = OWLObjectUnionOf([complement, super_expr])  # type: ignore[list-item]

        # Simplify and normalize
        simplified = self._expression_manager.get_simplified(inclusion)

        # If the simplified form is a disjunction containing ∀R.C operands,
        # replace each with a fresh auxiliary concept and emit the DL clause
        # directly.  This avoids the overapproximation (→ ⊤) that occurred
        # when ∀R.C appeared nested inside a union.
        if isinstance(simplified, OWLObjectUnionOf):
            operand_list = list(simplified.operands())
            changed = False
            new_operands: list[OWLClassExpression] = []
            for operand in operand_list:
                if isinstance(operand, (OWLObjectAllValuesFrom, OWLDataAllValuesFrom)):
                    fresh = self._fresh_concept("internal:allvalues-aux")
                    if isinstance(operand, OWLObjectAllValuesFrom):
                        self._emit_all_values_from_clause(fresh, operand, result)
                    else:
                        self._emit_data_all_values_from_clause(fresh, operand, result)
                    new_operands.append(fresh)
                    changed = True
                else:
                    new_operands.append(operand)
            if changed:
                simplified = OWLObjectUnionOf(new_operands)

        # Structural transformation for conjunction operands.
        #
        # After NNF + simplification a head clause is a disjunction of literals.
        # A disjunct may still be an OWLObjectIntersectionOf -- e.g. the NNF of
        # DisjointClasses produces (not b and not c) as one disjunct. The
        # clausifier expects every operand to be a literal, so we eliminate the
        # conjunction the way Java HermiT's OWLNormalization does:
        #
        #   * single conjunction disjunct  sub <= X1 and ... and Xm
        #     -> split into m inclusions sub <= X1, ..., sub <= Xm
        #   * conjunction among several disjuncts
        #     -> introduce a fresh Q with Q == X1 and ... and Xm (both
        #        directions) and replace the disjunct with Q.
        rewritten = self._eliminate_conjunction_disjuncts(simplified, result)
        if rewritten is None:
            # the inclusion was fully discharged by splitting
            return

        self._add_inclusion(rewritten, result)

    def _add_inclusion(self, expr: object, result: NormalizedAxioms) -> None:
        """Add a concept inclusion after replacing complex restriction fillers."""
        result.add_concept_inclusion(self._replace_complex_fillers(expr, result))

    @staticmethod
    def _is_literal_expression(expr: object) -> bool:
        """A literal in the structural normal form: C or ¬C for atomic C."""
        from hermit.owl_model.class_expression.class_expression import (
            OWLObjectComplementOf,
        )

        if isinstance(expr, OWLClass):
            return True
        return isinstance(expr, OWLObjectComplementOf) and isinstance(
            expr.get_operand(), OWLClass
        )

    def _get_definition_for(
        self, expr: OWLClassExpression, result: NormalizedAxioms
    ) -> OWLClass:
        """Return a named concept Q with Q ⊑ expr, creating it on first use.

        Mirrors the Java ``getDefinitionFor``/``m_newInclusions`` pattern: the
        defining inclusion is emitted once per distinct expression; positively
        occurring subexpressions only need the Q ⊑ expr direction.
        """
        definition = self._definitions.get(expr)
        if definition is None:
            definition = self._fresh_concept("internal:def")
            self._definitions[expr] = definition
            self._process_sub_class_of(OWLSubClassOfAxiom(definition, expr), result)
        return definition

    def _replace_complex_fillers(
        self, expr: object, result: NormalizedAxioms
    ) -> object:
        """Replace non-literal fillers of quantified restrictions by definitions.

        Mirrors the Java ``NormalizationVisitor`` handling of
        ``OWLObjectSomeValuesFrom`` / ``OWLObjectMinCardinality`` /
        ``OWLObjectMaxCardinality``: a complex filler C becomes a fresh named
        concept Q with Q ⊑ C (for the positively occurring some/min fillers) or
        Q ⊑ ¬C with filler ¬Q (for the negatively occurring max filler), so no
        constraint is weakened during the OWL → internal conversion.
        """
        if isinstance(expr, OWLObjectUnionOf):
            operands = [
                self._replace_complex_fillers(op, result) for op in expr.operands()
            ]
            return OWLObjectUnionOf(operands)  # type: ignore[arg-type]

        from hermit.owl_model.class_expression.class_expression import (
            OWLObjectComplementOf,
        )
        from hermit.owl_model.class_expression.restriction import (
            OWLDataAllValuesFrom,
            OWLObjectAllValuesFrom,
            OWLObjectMaxCardinality,
            OWLObjectMinCardinality,
            OWLObjectSomeValuesFrom,
        )

        if isinstance(expr, OWLObjectAllValuesFrom):
            fresh = self._fresh_concept("internal:allvalues-aux")
            self._emit_all_values_from_clause(fresh, expr, result)
            return fresh

        if isinstance(expr, OWLDataAllValuesFrom):
            fresh = self._fresh_concept("internal:allvalues-aux")
            self._emit_data_all_values_from_clause(fresh, expr, result)
            return fresh

        if isinstance(expr, (OWLObjectSomeValuesFrom, OWLObjectMinCardinality)):
            filler = expr.get_filler()
            if self._is_literal_expression(filler):
                return expr
            definition = self._get_definition_for(filler, result)
            if isinstance(expr, OWLObjectSomeValuesFrom):
                return OWLObjectSomeValuesFrom(expr.get_property(), definition)
            return OWLObjectMinCardinality(
                expr.get_cardinality(), expr.get_property(), definition
            )

        if isinstance(expr, OWLObjectMaxCardinality):
            filler = expr.get_filler()
            if self._is_literal_expression(filler):
                return expr
            complement = self._expression_manager.get_complement_nnf(
                self._expression_manager.get_simplified(filler)
            )
            assert isinstance(complement, OWLClassExpression)
            definition = self._get_definition_for(complement, result)
            return OWLObjectMaxCardinality(
                expr.get_cardinality(),
                expr.get_property(),
                OWLObjectComplementOf(definition),
            )

        return expr

    def _eliminate_conjunction_disjuncts(
        self, simplified: object, result: NormalizedAxioms
    ) -> object | None:
        """Remove OWLObjectIntersectionOf operands from a head disjunction.

        Returns the rewritten expression to add as a single concept inclusion,
        or ``None`` if the inclusion was fully handled by splitting (the single
        conjunction case, which emits its own inclusions).
        """
        from hermit.owl_model.class_expression import (
            OWLObjectIntersectionOf,
            OWLObjectUnionOf,
        )

        if isinstance(simplified, OWLObjectIntersectionOf):
            # sub <= C1 and ... and Cm  ==>  one inclusion per conjunct.
            for conjunct in simplified.operands():
                inc = self._define_conjunct_as_inclusion(conjunct, result)
                self._add_inclusion(inc, result)
            return None

        if isinstance(simplified, OWLObjectUnionOf):
            operands = list(simplified.operands())
            if not any(isinstance(o, OWLObjectIntersectionOf) for o in operands):
                return simplified
            new_operands: list[object] = []
            for operand in operands:
                if isinstance(operand, OWLObjectIntersectionOf):
                    fresh = self._fresh_concept("internal:and-aux")
                    # Q -> X_j   (Q <= X_j) for every conjunct
                    for conjunct in operand.operands():
                        self._process_sub_class_of(
                            OWLSubClassOfAxiom(fresh, conjunct), result
                        )
                    # X_1 and ... and X_m -> Q  (the conjunction <= Q)
                    self._process_sub_class_of(
                        OWLSubClassOfAxiom(operand, fresh), result
                    )
                    new_operands.append(fresh)
                else:
                    new_operands.append(operand)
            return OWLObjectUnionOf(new_operands)  # type: ignore[arg-type]

        return simplified

    def _define_conjunct_as_inclusion(
        self, conjunct: object, result: NormalizedAxioms
    ) -> object:
        """Return a NNF expression suitable as a single-disjunct inclusion.

        If the conjunct is itself complex (nested conjunction/disjunction) it is
        recursively normalised by routing through _process_sub_class_of with a
        fresh definition; otherwise it is returned unchanged.
        """
        from hermit.owl_model.class_expression import (
            OWLObjectIntersectionOf,
            OWLObjectUnionOf,
        )

        if isinstance(conjunct, OWLObjectIntersectionOf):
            # flatten nested conjunction
            fresh = self._fresh_concept("internal:and-aux")
            for inner in conjunct.operands():
                self._process_sub_class_of(OWLSubClassOfAxiom(fresh, inner), result)
            self._process_sub_class_of(OWLSubClassOfAxiom(conjunct, fresh), result)
            return fresh
        if isinstance(conjunct, OWLObjectUnionOf):
            fresh = self._fresh_concept("internal:or-aux")
            self._process_sub_class_of(OWLSubClassOfAxiom(fresh, conjunct), result)
            return fresh
        return conjunct

    def _emit_all_values_from_clause(
        self,
        sub_expr: object,
        all_values: object,
        result: NormalizedAxioms,
    ) -> None:
        """Emit A(X) ∧ R(X,Y) → C(Y) for SubClassOf(A, ∀R.C).

        The two-variable DL clause is added directly to result.direct_dl_clauses
        so that OWLClausification can pass it straight to DLOntology.
        """
        from hermit.structural.normalized_axioms import _owl_expr_to_internal
        from hermit.model import (
            Atom,
            AtomicConcept,
            DLClause,
            Variable,
        )

        x_var = Variable.create("X")
        y_var = Variable.create("Y")

        # Convert subclass to internal body concept (guard atom)
        sub_concept = _owl_expr_to_internal(sub_expr, result.cardinality_restriction_roles)

        # Extract role and filler from ∀R.C
        owl_prop = getattr(all_values, "get_property", lambda: None)()
        owl_filler = getattr(all_values, "get_filler", lambda: None)()

        from hermit.structural.normalized_axioms import _owl_prop_to_internal_role_standalone
        role = _owl_prop_to_internal_role_standalone(owl_prop)
        if not self._is_literal_expression(owl_filler) and isinstance(
            owl_filler, OWLClassExpression
        ):
            # Complex filler: introduce Q with Q ⊑ filler and propagate Q,
            # so the universal constraint is preserved instead of weakened.
            owl_filler = self._get_definition_for(owl_filler, result)
        filler_concept = _owl_expr_to_internal(owl_filler, result.cardinality_restriction_roles)

        from hermit.model import LiteralConcept
        if not isinstance(filler_concept, LiteralConcept):
            filler_concept = AtomicConcept.THING

        # Body: A(X) ∧ R(X, Y)
        # Head: C(Y)
        body_atoms: list[Atom] = [Atom.create(role, x_var, y_var)]  # type: ignore[arg-type]
        if hasattr(sub_concept, "arity") or hasattr(sub_concept, "accept"):
            # sub_concept is a valid DLPredicate — add as guard
            from hermit.model import AtomicNegationConcept
            if isinstance(sub_concept, AtomicNegationConcept):
                # A negated concept in body position means the guard is ¬A(X);
                # we add the positive version as body guard
                body_atoms.insert(0, Atom.create(sub_concept.negated, x_var))
            else:
                body_atoms.insert(0, Atom.create(sub_concept, x_var))  # type: ignore[arg-type]

        head_atom = Atom.create(filler_concept, y_var)  # type: ignore[arg-type]
        clause = DLClause.create((head_atom,), tuple(body_atoms))
        result.direct_dl_clauses.append(clause)
        guard: object = (
            sub_concept
            if hasattr(sub_concept, "arity") or hasattr(sub_concept, "accept")
            else AtomicConcept.THING
        )
        result.all_values_from_records.append((guard, role, filler_concept, clause))

    def _emit_data_all_values_from_clause(
        self,
        sub_expr: object,
        all_values: object,
        result: NormalizedAxioms,
    ) -> None:
        """Emit A(X) ∧ P(X,Y) → DR(Y) for SubClassOf(A, ∀P.DR).

        Mirrors the Java ``NormalizedAxiomClausifier`` handling of
        ``OWLDataAllValuesFrom``: a negated internal datatype filler puts the
        positive datatype in the body; other fillers go to the head; the
        always-false ¬rdfs:Literal filler yields an empty head.
        """
        from hermit.structural.normalized_axioms import (
            _owl_data_prop_to_internal_role,
            _owl_data_range_to_internal,
            _owl_expr_to_internal,
        )
        from hermit.model import (
            Atom,
            AtomicNegationConcept,
            AtomicNegationDataRange,
            DLClause,
            InternalDatatype,
            Variable,
        )

        owl_prop = getattr(all_values, "get_property", lambda: None)()
        owl_filler = getattr(all_values, "get_filler", lambda: None)()
        data_role = _owl_data_prop_to_internal_role(owl_prop)
        data_range = _owl_data_range_to_internal(owl_filler)
        if data_role is None or data_range is None:
            return

        x_var = Variable.create("X")
        y_var = Variable.create("Y")
        body_atoms: list[Atom] = [Atom.create(data_role, x_var, y_var)]

        sub_concept = _owl_expr_to_internal(
            sub_expr, result.cardinality_restriction_roles
        )
        if hasattr(sub_concept, "arity") or hasattr(sub_concept, "accept"):
            if isinstance(sub_concept, AtomicNegationConcept):
                body_atoms.insert(0, Atom.create(sub_concept.negated, x_var))
            else:
                body_atoms.insert(0, Atom.create(sub_concept, x_var))  # type: ignore[arg-type]

        head_atoms: list[Atom] = []
        if isinstance(data_range, AtomicNegationDataRange) and isinstance(
            data_range.negated, InternalDatatype
        ):
            inner = data_range.negated
            if not inner.is_always_true():
                body_atoms.append(Atom.create(inner, y_var))
        elif not data_range.is_always_false():
            head_atoms.append(Atom.create(data_range, y_var))

        result.direct_dl_clauses.append(
            DLClause.create(tuple(head_atoms), tuple(body_atoms))
        )

    def _process_equivalent_classes(
        self, axiom: OWLEquivalentClassesAxiom, result: NormalizedAxioms
    ) -> None:
        """Process EquivalentClasses: A ≡ B → (A ⊑ B) ∧ (B ⊑ A)."""
        operands = list(axiom.class_expressions())
        for i in range(len(operands)):
            for j in range(i + 1, len(operands)):
                # Add A ⊑ B and B ⊑ A
                sub_axiom = OWLSubClassOfAxiom(operands[i], operands[j])
                self._process_sub_class_of(sub_axiom, result)

                super_axiom = OWLSubClassOfAxiom(operands[j], operands[i])
                self._process_sub_class_of(super_axiom, result)

    def _process_disjoint_classes(
        self, axiom: OWLDisjointClassesAxiom, result: NormalizedAxioms
    ) -> None:
        """Process DisjointClasses: DisjointClasses(A, B, C) → (A ⊓ B ⊑ ⊥), etc."""
        operands = list(axiom.class_expressions())
        # Pairwise disjointness: each pair adds an inclusion
        for i in range(len(operands)):
            for j in range(i + 1, len(operands)):
                # A ⊓ B ⊑ ⊥
                intersection = OWLObjectIntersectionOf([operands[i], operands[j]])
                from hermit.owl_model.class_expression import OWLNothing
                sub_axiom = OWLSubClassOfAxiom(intersection, OWLNothing)
                self._process_sub_class_of(sub_axiom, result)

    def _process_sub_object_property_of(
        self, axiom: OWLSubObjectPropertyOfAxiom, result: NormalizedAxioms
    ) -> None:
        """Process SubObjectPropertyOf: add to simple property inclusions."""
        sub = _owl_prop_to_role(axiom.get_sub_property())
        sup = _owl_prop_to_role(axiom.get_super_property())
        if sub is not None and sup is not None:
            result.simple_object_property_inclusions.append((sub, sup))
        result.positive_facts.append(axiom)

    def _process_sub_property_chain(self, axiom: object, result: NormalizedAxioms) -> None:
        """Process SubPropertyChainOf([R1,...,Rn], S): complex property inclusion."""
        from hermit.structural.normalized_axioms import ComplexObjectPropertyInclusion
        chain = [_owl_prop_to_role(p) for p in axiom.get_property_chain()]  # type: ignore[attr-defined]
        sup = _owl_prop_to_role(axiom.get_super_property())  # type: ignore[attr-defined]
        if sup is not None and all(r is not None for r in chain) and len(chain) >= 2:
            chain_roles = [r for r in chain if r is not None]
            result.complex_object_property_inclusions.append(
                ComplexObjectPropertyInclusion(
                    sub_object_properties=tuple(chain_roles),
                    super_object_property=sup,
                )
            )
        result.positive_facts.append(axiom)

    def _process_equivalent_object_properties(
        self, axiom: OWLEquivalentObjectPropertiesAxiom, result: NormalizedAxioms
    ) -> None:
        """Process EquivalentObjectProperties: add bidirectional inclusions."""
        props = list(axiom.properties())
        for i in range(len(props)):
            for j in range(i + 1, len(props)):
                # Add R ⊑ S and S ⊑ R
                from hermit.owl_model.owl_axiom import OWLSubObjectPropertyOfAxiom
                result.positive_facts.append(
                    OWLSubObjectPropertyOfAxiom(props[i], props[j])
                )
                result.positive_facts.append(
                    OWLSubObjectPropertyOfAxiom(props[j], props[i])
                )

    def _process_object_property_domain(
        self, axiom: OWLObjectPropertyDomainAxiom, result: NormalizedAxioms
    ) -> None:
        """Process ObjectPropertyDomain(R, C): ∃R.⊤ ⊑ C.

        A literal domain becomes the Horn clause C(X) :- R(X,Y); a complex
        domain routes through the generic inclusion path (Java emits the
        inclusion {domain, ∀R.⊥}).
        """
        from hermit.model import Atom, AtomicConcept, DLClause, Variable
        from hermit.owl_model.class_expression.restriction import (
            OWLObjectSomeValuesFrom,
        )
        from hermit.owl_model.class_expression import OWLThing
        from hermit.structural.owl_clausification import _role_atom

        role = _owl_prop_to_role(axiom.get_property())
        domain = self._expression_manager.get_nnf(axiom.get_domain())
        if role is None or not isinstance(domain, OWLClassExpression):
            return
        if isinstance(domain, OWLClass):
            xv = Variable.create("X")
            yv = Variable.create("Y")
            iri = _iri_str(domain)
            if iri is None:
                return
            head = (Atom.create(AtomicConcept.create(iri), xv),)
            result.direct_dl_clauses.append(
                DLClause.create(head, (_role_atom(role, xv, yv),))
            )
            return
        self._process_sub_class_of(
            OWLSubClassOfAxiom(
                OWLObjectSomeValuesFrom(axiom.get_property(), OWLThing), domain
            ),
            result,
        )

    def _process_object_property_range(
        self, axiom: OWLObjectPropertyRangeAxiom, result: NormalizedAxioms
    ) -> None:
        """Process ObjectPropertyRange(R, C): ⊤ ⊑ ∀R.C."""
        from hermit.owl_model.class_expression import OWLThing
        from hermit.owl_model.class_expression.restriction import (
            OWLObjectAllValuesFrom,
        )
        self._process_sub_class_of(
            OWLSubClassOfAxiom(
                OWLThing,
                OWLObjectAllValuesFrom(axiom.get_property(), axiom.get_range()),
            ),
            result,
        )

    def _process_data_property_domain(
        self, axiom: OWLDataPropertyDomainAxiom, result: NormalizedAxioms
    ) -> None:
        """Process DataPropertyDomain(P, C): ∃P.rdfs:Literal ⊑ C."""
        from hermit.model import Atom, AtomicConcept, DLClause, Variable
        from hermit.structural.normalized_axioms import (
            _owl_data_prop_to_internal_role,
        )

        data_role = _owl_data_prop_to_internal_role(axiom.get_property())
        domain = self._expression_manager.get_nnf(axiom.get_domain())
        if data_role is None:
            return
        if isinstance(domain, OWLClass):
            iri = _iri_str(domain)
            if iri is None:
                return
            xv = Variable.create("X")
            yv = Variable.create("Y")
            head = (Atom.create(AtomicConcept.create(iri), xv),)
            result.direct_dl_clauses.append(
                DLClause.create(head, (Atom.create(data_role, xv, yv),))
            )
            return
        from hermit.owl_model.class_expression.restriction import (
            OWLDataSomeValuesFrom,
        )
        from hermit.owl_model.owl_literal import TopOWLDatatype
        if isinstance(domain, OWLClassExpression):
            self._process_sub_class_of(
                OWLSubClassOfAxiom(
                    OWLDataSomeValuesFrom(axiom.get_property(), TopOWLDatatype),
                    domain,
                ),
                result,
            )

    def _process_class_assertion(
        self, axiom: OWLClassAssertionAxiom, result: NormalizedAxioms
    ) -> None:
        """Route ClassAssertion(C, a) to typed positive_concept_facts.

        A complex class expression gets a definition Q with Q ⊑ C and the
        assertion becomes Q(a), as in the Java visit(OWLClassAssertionAxiom).
        """
        from hermit.model import AtomicConcept
        from hermit.owl_model.class_expression import OWLClass
        ind = _owl_ind_to_internal(axiom.get_individual())
        ce = axiom.get_class_expression()
        if ind is None:
            result.positive_facts.append(axiom)
            return
        if isinstance(ce, OWLClass):
            iri = _iri_str(ce)
            if iri is not None:
                concept = AtomicConcept.create(iri)
                result.positive_concept_facts.append((ind, concept))
                result.named_individuals.add(ind)
                return
        if isinstance(ce, OWLClassExpression):
            nnf = self._expression_manager.get_nnf(ce)
            assert isinstance(nnf, OWLClassExpression)
            definition = self._get_definition_for(nnf, result)
            def_iri = _iri_str(definition)
            assert def_iri is not None
            result.positive_concept_facts.append(
                (ind, AtomicConcept.create(def_iri))
            )
            result.named_individuals.add(ind)
            return
        result.positive_facts.append(axiom)

    def _process_object_property_assertion(
        self, axiom: OWLObjectPropertyAssertionAxiom, result: NormalizedAxioms
    ) -> None:
        """Route ObjectPropertyAssertion(R, a, b) to typed positive_role_facts."""
        ind1 = _owl_ind_to_internal(axiom.get_subject())
        role = _owl_prop_to_role(axiom.get_property())
        ind2 = _owl_ind_to_internal(axiom.get_object())
        if ind1 is not None and role is not None and ind2 is not None:
            result.positive_role_facts.append((ind1, role, ind2))
            result.named_individuals.add(ind1)
            result.named_individuals.add(ind2)
        else:
            result.positive_facts.append(axiom)

    def _process_data_property_assertion(
        self, axiom: OWLDataPropertyAssertionAxiom, result: NormalizedAxioms
    ) -> None:
        """Route DataPropertyAssertion(P, a, v) to typed positive_data_facts."""
        from hermit.model import AtomicRole, Constant
        from hermit.owl_model.owl_property import OWLDataProperty
        ind = _owl_ind_to_internal(axiom.get_subject())
        owl_prop = axiom.get_property()
        literal = axiom.get_object()
        if ind is not None and isinstance(owl_prop, OWLDataProperty):
            prop_iri = _iri_str(owl_prop)
            if prop_iri is not None:
                prop = AtomicRole.create(prop_iri)
                lit_val = getattr(literal, "get_literal", lambda: str(literal))()
                lit_dt = getattr(getattr(literal, "get_datatype", lambda: None)(), "iri", None)
                dt_iri = (lit_dt.as_str() if hasattr(lit_dt, "as_str") else str(lit_dt)) if lit_dt else "http://www.w3.org/2001/XMLSchema#string"
                value = Constant.create(lit_val, dt_iri)
                result.positive_data_facts.append((ind, prop, value))
                result.named_individuals.add(ind)
                return
        result.positive_facts.append(axiom)

    def _process_same_individual(
        self, axiom: OWLSameIndividualAxiom, result: NormalizedAxioms
    ) -> None:
        """Route SameIndividual axiom to same_individual_facts."""
        raw = [_owl_ind_to_internal(i) for i in axiom.individuals()]
        inds: list[Individual] = [i for i in raw if i is not None]
        for i in range(len(inds)):
            result.named_individuals.add(inds[i])
            for j in range(i + 1, len(inds)):
                result.same_individual_facts.append((inds[i], inds[j]))

    def _process_different_individuals(
        self, axiom: OWLDifferentIndividualsAxiom, result: NormalizedAxioms
    ) -> None:
        """Route DifferentIndividuals axiom to different_individuals_facts."""
        raw = [_owl_ind_to_internal(i) for i in axiom.individuals()]
        inds: list[Individual] = [i for i in raw if i is not None]
        for i in range(len(inds)):
            result.named_individuals.add(inds[i])
            for j in range(i + 1, len(inds)):
                result.different_individuals_facts.append((inds[i], inds[j]))

    def _fresh_concept(self, base_name: str = "internal:def") -> OWLClass:
        """Generate a fresh named atomic concept."""
        idx = self._replacement_counter
        self._replacement_counter += 1
        return OWLClass(IRI(f"{base_name}#", str(idx)))
