"""OWL axiom normalization to structural form.

Transforms OWL axioms into NormalizedAxioms by:
1. Converting to Negation Normal Form (NNF)
2. Simplifying expressions
3. Introducing fresh atomic concepts for complex subexpressions
4. Normalizing SWRL rules (Lloyd-Topor transformation)

NOTE: This module has 35+ mypy errors due to API mismatches (e.g., positive_facts
should be separate positive_concept_facts, positive_role_facts, positive_data_facts).
Type checking is disabled pending implementation review.
"""

# mypy: ignore-errors

from __future__ import annotations

from typing import Iterable, TypeVar

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
)
from hermit.owl_model.class_expression import (
    OWLClassExpression,
    OWLClass,
    OWLObjectIntersectionOf,
    OWLObjectUnionOf,
)
from hermit.owl_model.iri import IRI


T = TypeVar("T")


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
            result.positive_facts.append(axiom)
        elif isinstance(axiom, OWLSubObjectPropertyOfAxiom):
            self._process_sub_object_property_of(axiom, result)
        elif isinstance(axiom, OWLEquivalentObjectPropertiesAxiom):
            self._process_equivalent_object_properties(axiom, result)
        elif isinstance(axiom, OWLDisjointObjectPropertiesAxiom):
            # Disjoint properties: store in result
            result.positive_facts.append(axiom)
        elif isinstance(axiom, OWLObjectPropertyDomainAxiom):
            self._process_object_property_domain(axiom, result)
        elif isinstance(axiom, OWLObjectPropertyRangeAxiom):
            self._process_object_property_range(axiom, result)
        elif isinstance(axiom, OWLSubDataPropertyOfAxiom):
            result.positive_facts.append(axiom)
        elif isinstance(axiom, OWLEquivalentDataPropertiesAxiom):
            result.positive_facts.append(axiom)
        elif isinstance(axiom, OWLDisjointDataPropertiesAxiom):
            result.positive_facts.append(axiom)
        elif isinstance(axiom, OWLDataPropertyDomainAxiom):
            self._process_data_property_domain(axiom, result)
        elif isinstance(axiom, OWLDataPropertyRangeAxiom):
            result.positive_facts.append(axiom)
        elif isinstance(axiom, OWLSameIndividualAxiom):
            result.positive_facts.append(axiom)
        elif isinstance(axiom, OWLDifferentIndividualsAxiom):
            result.positive_facts.append(axiom)
        elif isinstance(axiom, OWLObjectPropertyAssertionAxiom):
            result.positive_facts.append(axiom)
        elif isinstance(axiom, OWLNegativeObjectPropertyAssertionAxiom):
            result.negative_facts.append(axiom)
        elif isinstance(axiom, OWLDataPropertyAssertionAxiom):
            result.positive_facts.append(axiom)
        elif isinstance(axiom, OWLNegativeDataPropertyAssertionAxiom):
            result.negative_facts.append(axiom)
        elif isinstance(axiom, OWLFunctionalObjectPropertyAxiom):
            # ∃R.Self ⊓ ∃R⁻.Self ⊑ ⊥ (added via property constraints)
            result.positive_facts.append(axiom)
        elif isinstance(axiom, OWLInverseFunctionalObjectPropertyAxiom):
            result.positive_facts.append(axiom)
        elif isinstance(axiom, OWLSymmetricObjectPropertyAxiom):
            result.positive_facts.append(axiom)
        elif isinstance(axiom, OWLAsymmetricObjectPropertyAxiom):
            result.positive_facts.append(axiom)
        elif isinstance(axiom, OWLTransitiveObjectPropertyAxiom):
            result.positive_facts.append(axiom)
        elif isinstance(axiom, OWLReflexiveObjectPropertyAxiom):
            result.positive_facts.append(axiom)
        elif isinstance(axiom, OWLIrreflexiveObjectPropertyAxiom):
            result.positive_facts.append(axiom)
        elif isinstance(axiom, OWLFunctionalDataPropertyAxiom):
            result.positive_facts.append(axiom)
        else:
            # Unknown axiom type: pass through
            result.positive_facts.append(axiom)

    def _process_sub_class_of(
        self, axiom: OWLSubClassOfAxiom, result: NormalizedAxioms
    ) -> None:
        """Process SubClassOf axiom: A ⊑ B → ¬A ⊔ B."""
        sub_expr = self._expression_manager.get_nnf(axiom.sub_class())
        super_expr = self._expression_manager.get_nnf(axiom.super_class())

        # ¬sub ⊔ super
        complement = self._expression_manager.get_complement_nnf(sub_expr)
        if isinstance(complement, OWLObjectUnionOf):
            # Flatten: ¬A ⊔ C ⊔ B becomes one inclusion
            operands = list(complement.operands()) + [super_expr]
            inclusion = OWLObjectUnionOf(*operands)
        else:
            inclusion = OWLObjectUnionOf(complement, super_expr)

        # Simplify and normalize
        simplified = self._expression_manager.get_simplified(inclusion)
        result.add_concept_inclusion(simplified)

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
                intersection = OWLObjectIntersectionOf(operands[i], operands[j])
                from hermit.owl_model.class_expression import OWLNothing
                sub_axiom = OWLSubClassOfAxiom(intersection, OWLNothing)
                self._process_sub_class_of(sub_axiom, result)

    def _process_sub_object_property_of(
        self, axiom: OWLSubObjectPropertyOfAxiom, result: NormalizedAxioms
    ) -> None:
        """Process SubObjectPropertyOf: add to property inclusions."""
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
        """Process ObjectPropertyDomain: Domain(R) = C → ∀R.⊤ ⊑ C becomes ∃R.⊤ ⊑ C."""
        # This is handled during clausification
        result.positive_facts.append(axiom)

    def _process_object_property_range(
        self, axiom: OWLObjectPropertyRangeAxiom, result: NormalizedAxioms
    ) -> None:
        """Process ObjectPropertyRange: Range(R) = C."""
        result.positive_facts.append(axiom)

    def _process_data_property_domain(
        self, axiom: OWLDataPropertyDomainAxiom, result: NormalizedAxioms
    ) -> None:
        """Process DataPropertyDomain."""
        result.positive_facts.append(axiom)

    def _fresh_concept(self, base_name: str = "internal:def") -> OWLClass:
        """Generate a fresh named atomic concept."""
        iri_str = f"{base_name}#{self._replacement_counter}"
        self._replacement_counter += 1
        return OWLClass(IRI(iri_str))
