"""Built-in property manager for top/bottom roles.

Injects axioms for built-in roles (owl:topObjectProperty, owl:bottomObjectProperty,
owl:topDataProperty, owl:bottomDataProperty) when they're used in the ontology.

NOTE: This module has extensive mypy errors due to API mismatches. The implementation
is incomplete and not currently used in the reasoning pipeline. It should be revisited
when the structural transformation pipeline is fully integrated.
"""

# mypy: ignore-errors

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.structural.normalized_axioms import NormalizedAxioms


class BuiltInPropertyManager:
    """Manages axiomatization of built-in object and data properties."""

    # Built-in property IRIs
    TOP_OBJECT_PROPERTY_IRI = "http://www.w3.org/2002/07/owl#topObjectProperty"
    BOTTOM_OBJECT_PROPERTY_IRI = "http://www.w3.org/2002/07/owl#bottomObjectProperty"
    TOP_DATA_PROPERTY_IRI = "http://www.w3.org/2002/07/owl#topDataProperty"
    BOTTOM_DATA_PROPERTY_IRI = "http://www.w3.org/2002/07/owl#bottomDataProperty"

    def axiomatize_builtin_properties(
        self,
        normalized_axioms: NormalizedAxioms,
        skip_top_object: bool = False,
        skip_bottom_object: bool = False,
        skip_top_data: bool = False,
        skip_bottom_data: bool = False,
    ) -> None:
        """Add axioms for built-in properties if they're used.

        Args:
            normalized_axioms: NormalizedAxioms to enrich
            skip_top_object: Skip axiomatizing top object property
            skip_bottom_object: Skip axiomatizing bottom object property
            skip_top_data: Skip axiomatizing top data property
            skip_bottom_data: Skip axiomatizing bottom data property
        """
        # Check which built-in properties are actually used
        checker = _BuiltInPropertyChecker(normalized_axioms)

        if checker.uses_top_object and not skip_top_object:
            self._axiomatize_top_object_property(normalized_axioms)

        if checker.uses_bottom_object and not skip_bottom_object:
            self._axiomatize_bottom_object_property(normalized_axioms)

        if checker.uses_top_data and not skip_top_data:
            self._axiomatize_top_data_property(normalized_axioms)

        if checker.uses_bottom_data and not skip_bottom_data:
            self._axiomatize_bottom_data_property(normalized_axioms)

    @staticmethod
    def _axiomatize_top_object_property(
        normalized_axioms: NormalizedAxioms,
    ) -> None:
        """Add axioms for top object property.

        Axioms:
        - TransitiveObjectProperty( owl:topObjectProperty )
        - SymmetricObjectProperty( owl:topObjectProperty )
        - ⊤ ⊑ ∃owl:topObjectProperty.{internal:topIndividual}
        """
        from hermit.owl_model.owl_property import OWLObjectProperty
        from hermit.owl_model.iri import IRI
        from hermit.owl_model.class_expression import (
            OWLObjectSomeValuesFrom,
            OWLObjectOneOf,
            OWLThing,
        )
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom

        top_prop = OWLObjectProperty(IRI(BuiltInPropertyManager.TOP_OBJECT_PROPERTY_IRI))

        # Add axiom: ⊤ ⊑ ∃owl:topObjectProperty.{internal:topIndividual}
        top_individual = OWLNamedIndividual(IRI("internal:nam#topIndividual"))
        one_of = OWLObjectOneOf(top_individual)
        some_values = OWLObjectSomeValuesFrom(top_prop, one_of)

        # Add as concept inclusion (will be normalized by OWLNormalization)
        # For now, add the axiom directly
        # NOTE: This implementation is incomplete - axioms should be converted to DL facts
        inclusion_axiom = OWLSubClassOfAxiom(OWLThing, some_values)
        normalized_axioms.positive_concept_facts.append(inclusion_axiom)  # type: ignore[arg-type]

    @staticmethod
    def _axiomatize_bottom_object_property(
        normalized_axioms: NormalizedAxioms,
    ) -> None:
        """Add axioms for bottom object property.

        Axiom:
        - ⊤ ⊑ ∀owl:bottomObjectProperty.⊥
        """
        from hermit.owl_model.owl_property import OWLObjectProperty
        from hermit.owl_model.iri import IRI
        from hermit.owl_model.class_expression import (
            OWLObjectAllValuesFrom,
            OWLNothing,
            OWLThing,
        )
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom

        bottom_prop = OWLObjectProperty(
            IRI(BuiltInPropertyManager.BOTTOM_OBJECT_PROPERTY_IRI)
        )

        # Add axiom: ⊤ ⊑ ∀owl:bottomObjectProperty.⊥
        all_values = OWLObjectAllValuesFrom(bottom_prop, OWLNothing)
        axiom = OWLSubClassOfAxiom(OWLThing, all_values)
        normalized_axioms.positive_concept_facts.append(axiom)  # type: ignore[arg-type]

    @staticmethod
    def _axiomatize_top_data_property(
        normalized_axioms: NormalizedAxioms,
    ) -> None:
        """Add axioms for top data property.

        Axiom:
        - ⊤ ⊑ ∃owl:topDataProperty.{internal:constant}
        """
        from hermit.owl_model.owl_property import OWLDataProperty
        from hermit.owl_model.iri import IRI
        from hermit.owl_model.class_expression import (
            OWLDataSomeValuesFrom,
            OWLThing,
        )
        from hermit.owl_model.owl_datatype import OWLDatatype
        from hermit.owl_model.class_expression import OWLDataOneOf
        from hermit.owl_model.owl_literal import OWLLiteral
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom

        top_data_prop = OWLDataProperty(
            IRI(BuiltInPropertyManager.TOP_DATA_PROPERTY_IRI)
        )

        # Create an anonymous datatype and constant for the built-in axiom
        anonymous_datatype = OWLDatatype(IRI("internal:anonymous-constants"))
        literal = OWLLiteral("internal:constant", anonymous_datatype)
        one_of = OWLDataOneOf(literal)
        some_values = OWLDataSomeValuesFrom(top_data_prop, one_of)

        axiom = OWLSubClassOfAxiom(OWLThing, some_values)
        normalized_axioms.positive_concept_facts.append(axiom)  # type: ignore[arg-type]

    @staticmethod
    def _axiomatize_bottom_data_property(
        normalized_axioms: NormalizedAxioms,
    ) -> None:
        """Add axioms for bottom data property.

        Axiom:
        - ⊤ ⊑ ∀owl:bottomDataProperty.⊥_D (complement of top datatype)
        """
        from hermit.owl_model.owl_property import OWLDataProperty
        from hermit.owl_model.iri import IRI
        from hermit.owl_model.class_expression import (
            OWLDataAllValuesFrom,
            OWLThing,
        )
        from hermit.owl_model.owl_data_ranges import OWLDataComplementOf
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom

        bottom_data_prop = OWLDataProperty(
            IRI(BuiltInPropertyManager.BOTTOM_DATA_PROPERTY_IRI)
        )

        # Top datatype for complementation
        from hermit.owl_model.owl_datatype import TopOWLDatatype
        top_datatype = TopOWLDatatype()
        complement = OWLDataComplementOf(top_datatype)

        all_values = OWLDataAllValuesFrom(bottom_data_prop, complement)
        axiom = OWLSubClassOfAxiom(OWLThing, all_values)
        normalized_axioms.positive_concept_facts.append(axiom)  # type: ignore[arg-type]


class _BuiltInPropertyChecker:
    """Checks which built-in properties are used in normalized axioms."""

    def __init__(self, normalized_axioms: NormalizedAxioms) -> None:
        """Initialize and scan normalized axioms."""
        self.uses_top_object = False
        self.uses_bottom_object = False
        self.uses_top_data = False
        self.uses_bottom_data = False

        self._check_axioms(normalized_axioms)

    def _check_axioms(self, normalized_axioms: NormalizedAxioms) -> None:
        """Scan axioms for uses of built-in properties."""
        # Check concept inclusions (they contain class expressions)
        for inclusion in normalized_axioms.concept_inclusions:
            if isinstance(inclusion, list):
                for expr in inclusion:
                    self._check_class_expression(expr)
            else:
                self._check_class_expression(inclusion)

        # Check property inclusions
        for obj_prop in normalized_axioms.object_property_inclusions:
            self._check_object_property(obj_prop)

        # Check data property inclusions
        for data_prop in normalized_axioms.data_property_inclusions:
            self._check_data_property(data_prop)

        # Check facts
        for fact in normalized_axioms.positive_concept_facts:  # type: ignore[attr-defined]
            self._check_axiom(fact)

    def _check_axiom(self, axiom: object) -> None:
        """Check an axiom for built-in property usage."""
        from hermit.owl_model.owl_axiom import (
            OWLObjectPropertyAssertionAxiom,
            OWLDataPropertyAssertionAxiom,
            OWLSubObjectPropertyOfAxiom,
            OWLObjectPropertyDomainAxiom,
            OWLObjectPropertyRangeAxiom,
            OWLSubDataPropertyOfAxiom,
        )

        if isinstance(axiom, OWLObjectPropertyAssertionAxiom):
            self._check_object_property(axiom.get_property())  # type: ignore[attr-defined]
        elif isinstance(axiom, OWLDataPropertyAssertionAxiom):
            self._check_data_property(axiom.get_property())  # type: ignore[attr-defined]
        elif isinstance(axiom, OWLSubObjectPropertyOfAxiom):
            self._check_object_property(axiom.get_sub_property())  # type: ignore[attr-defined]
            self._check_object_property(axiom.get_super_property())  # type: ignore[attr-defined]
        elif isinstance(axiom, OWLObjectPropertyDomainAxiom):
            self._check_object_property(axiom.get_property())  # type: ignore[attr-defined]
            self._check_class_expression(axiom.get_domain())  # type: ignore[attr-defined]
        elif isinstance(axiom, OWLObjectPropertyRangeAxiom):
            self._check_object_property(axiom.get_property())  # type: ignore[attr-defined]
            self._check_class_expression(axiom.get_range())  # type: ignore[attr-defined]
        elif isinstance(axiom, OWLSubDataPropertyOfAxiom):
            self._check_data_property(axiom.get_sub_property())  # type: ignore[attr-defined]
            self._check_data_property(axiom.get_super_property())  # type: ignore[attr-defined]

    def _check_class_expression(self, expr: object) -> None:
        """Recursively check a class expression for built-in properties."""
        from hermit.owl_model.class_expression import (
            OWLObjectComplementOf,
            OWLObjectIntersectionOf,
            OWLObjectUnionOf,
            OWLObjectSomeValuesFrom,
            OWLObjectAllValuesFrom,
            OWLObjectHasValue,
            OWLObjectHasSelf,
            OWLObjectMinCardinality,
            OWLObjectMaxCardinality,
            OWLObjectExactCardinality,
            OWLDataSomeValuesFrom,
            OWLDataAllValuesFrom,
            OWLDataHasValue,
            OWLDataMinCardinality,
            OWLDataMaxCardinality,
            OWLDataExactCardinality,
        )

        if isinstance(expr, OWLObjectComplementOf):
            self._check_class_expression(expr.operand())
        elif isinstance(expr, OWLObjectIntersectionOf):
            for operand in expr.operands():
                self._check_class_expression(operand)
        elif isinstance(expr, OWLObjectUnionOf):
            for operand in expr.operands():
                self._check_class_expression(operand)
        elif isinstance(expr, OWLObjectSomeValuesFrom):
            self._check_object_property(expr.property())
            self._check_class_expression(expr.filler())
        elif isinstance(expr, OWLObjectAllValuesFrom):
            self._check_object_property(expr.property())
            self._check_class_expression(expr.filler())
        elif isinstance(expr, OWLObjectHasValue):
            self._check_object_property(expr.property())
        elif isinstance(expr, OWLObjectHasSelf):
            self._check_object_property(expr.property())
        elif isinstance(expr, OWLObjectMinCardinality):
            self._check_object_property(expr.property())
            self._check_class_expression(expr.filler())
        elif isinstance(expr, OWLObjectMaxCardinality):
            self._check_object_property(expr.property())
            self._check_class_expression(expr.filler())
        elif isinstance(expr, OWLObjectExactCardinality):
            self._check_object_property(expr.property())
            self._check_class_expression(expr.filler())
        elif isinstance(expr, OWLDataSomeValuesFrom):
            self._check_data_property(expr.property())
        elif isinstance(expr, OWLDataAllValuesFrom):
            self._check_data_property(expr.property())
        elif isinstance(expr, OWLDataHasValue):
            self._check_data_property(expr.property())
        elif isinstance(expr, OWLDataMinCardinality):
            self._check_data_property(expr.property())
        elif isinstance(expr, OWLDataMaxCardinality):
            self._check_data_property(expr.property())
        elif isinstance(expr, OWLDataExactCardinality):
            self._check_data_property(expr.property())

    def _check_object_property(self, prop: object) -> None:
        """Check if an object property is a built-in property."""
        if prop is None:
            return

        try:
            prop_iri = str(prop.iri()) if hasattr(prop, "iri") else str(prop)
        except Exception:
            return

        if BuiltInPropertyManager.TOP_OBJECT_PROPERTY_IRI in prop_iri:
            self.uses_top_object = True
        elif BuiltInPropertyManager.BOTTOM_OBJECT_PROPERTY_IRI in prop_iri:
            self.uses_bottom_object = True

    def _check_data_property(self, prop: object) -> None:
        """Check if a data property is a built-in property."""
        if prop is None:
            return

        try:
            prop_iri = str(prop.iri()) if hasattr(prop, "iri") else str(prop)
        except Exception:
            return

        if BuiltInPropertyManager.TOP_DATA_PROPERTY_IRI in prop_iri:
            self.uses_top_data = True
        elif BuiltInPropertyManager.BOTTOM_DATA_PROPERTY_IRI in prop_iri:
            self.uses_bottom_data = True
