"""Built-in property manager for top/bottom roles.

Mirrors the Java ``BuiltInPropertyManager``: when an ontology uses
owl:topObjectProperty, owl:bottomObjectProperty, owl:topDataProperty, or
owl:bottomDataProperty, the corresponding semantics are injected as OWL
axioms before normalization:

* topObjectProperty — transitive, symmetric, and every individual has a
  topObjectProperty successor (a fresh nominal).
* bottomObjectProperty — empty extension: ⊤ ⊑ ∀bot.⊥.
* topDataProperty — every individual has a topDataProperty successor (an
  anonymous constant).
* bottomDataProperty — empty extension: ⊤ ⊑ ∀bot.¬rdfs:Literal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.owl_model.owl_axiom import OWLAxiom


class BuiltInPropertyManager:
    """Axiomatizes built-in object and data properties when they are used."""

    TOP_OBJECT_PROPERTY_IRI = "http://www.w3.org/2002/07/owl#topObjectProperty"
    BOTTOM_OBJECT_PROPERTY_IRI = "http://www.w3.org/2002/07/owl#bottomObjectProperty"
    TOP_DATA_PROPERTY_IRI = "http://www.w3.org/2002/07/owl#topDataProperty"
    BOTTOM_DATA_PROPERTY_IRI = "http://www.w3.org/2002/07/owl#bottomDataProperty"

    def axioms_for_builtin_properties(
        self, axioms: list[OWLAxiom]
    ) -> list[OWLAxiom]:
        """Return the axiomatization for built-in properties used in *axioms*."""
        used: set[str] = set()
        for axiom in axioms:
            _collect_property_iris(axiom, used)

        extra: list[OWLAxiom] = []
        if self.TOP_OBJECT_PROPERTY_IRI in used:
            extra.extend(self._top_object_property_axioms())
        if self.BOTTOM_OBJECT_PROPERTY_IRI in used:
            extra.append(self._bottom_object_property_axiom())
        if self.TOP_DATA_PROPERTY_IRI in used:
            extra.append(self._top_data_property_axiom())
        if self.BOTTOM_DATA_PROPERTY_IRI in used:
            extra.append(self._bottom_data_property_axiom())
        return extra

    def _top_object_property_axioms(self) -> list[OWLAxiom]:
        """topObjectProperty is transitive, symmetric, and universal."""
        from hermit.owl_model.class_expression import (
            OWLObjectOneOf,
            OWLObjectSomeValuesFrom,
            OWLThing,
        )
        from hermit.owl_model.owl_axiom import (
            OWLSubClassOfAxiom,
            OWLSymmetricObjectPropertyAxiom,
            OWLTransitiveObjectPropertyAxiom,
        )
        from hermit.owl_model.iri import IRI
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        from hermit.owl_model.owl_property import OWLObjectProperty

        top_prop = OWLObjectProperty(self.TOP_OBJECT_PROPERTY_IRI)
        top_individual = OWLNamedIndividual(IRI("internal:nam#", "topIndividual"))
        has_top_individual = OWLObjectSomeValuesFrom(
            top_prop, OWLObjectOneOf(top_individual)
        )
        return [
            OWLTransitiveObjectPropertyAxiom(top_prop),
            OWLSymmetricObjectPropertyAxiom(top_prop),
            OWLSubClassOfAxiom(OWLThing, has_top_individual),
        ]

    def _bottom_object_property_axiom(self) -> OWLAxiom:
        """bottomObjectProperty has an empty extension: ⊤ ⊑ ∀bot.⊥."""
        from hermit.owl_model.class_expression import (
            OWLNothing,
            OWLObjectAllValuesFrom,
            OWLThing,
        )
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom
        from hermit.owl_model.owl_property import OWLObjectProperty

        bottom_prop = OWLObjectProperty(self.BOTTOM_OBJECT_PROPERTY_IRI)
        return OWLSubClassOfAxiom(
            OWLThing, OWLObjectAllValuesFrom(bottom_prop, OWLNothing)
        )

    def _top_data_property_axiom(self) -> OWLAxiom:
        """topDataProperty is universal: ⊤ ⊑ ∃top.{anonymous constant}."""
        from hermit.owl_model.class_expression import OWLThing
        from hermit.owl_model.class_expression.restriction import (
            OWLDataOneOf,
            OWLDataSomeValuesFrom,
        )
        from hermit.owl_model.iri import IRI
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom
        from hermit.owl_model.owl_datatype import OWLDatatype
        from hermit.owl_model.owl_literal import OWLLiteral
        from hermit.owl_model.owl_property import OWLDataProperty

        top_prop = OWLDataProperty(self.TOP_DATA_PROPERTY_IRI)
        new_constant = OWLLiteral(  # type: ignore[abstract]
            "internal:constant",
            OWLDatatype(IRI("internal:", "anonymous-constants")),
        )
        has_top_constant = OWLDataSomeValuesFrom(
            top_prop, OWLDataOneOf([new_constant])
        )
        return OWLSubClassOfAxiom(OWLThing, has_top_constant)

    def _bottom_data_property_axiom(self) -> OWLAxiom:
        """bottomDataProperty has an empty extension: ⊤ ⊑ ∀bot.¬⊤D."""
        from hermit.owl_model.class_expression import OWLThing
        from hermit.owl_model.class_expression.restriction import (
            OWLDataAllValuesFrom,
        )
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom
        from hermit.owl_model.owl_data_ranges import OWLDataComplementOf
        from hermit.owl_model.owl_literal import TopOWLDatatype
        from hermit.owl_model.owl_property import OWLDataProperty

        bottom_prop = OWLDataProperty(self.BOTTOM_DATA_PROPERTY_IRI)
        return OWLSubClassOfAxiom(
            OWLThing,
            OWLDataAllValuesFrom(bottom_prop, OWLDataComplementOf(TopOWLDatatype)),
        )


_CHILD_GETTERS = (
    "get_property",
    "get_properties",
    "get_sub_property",
    "get_super_property",
    "get_inverse",
    "get_inverse_property",
    "get_first_property",
    "get_second_property",
    "get_filler",
    "get_operand",
    "get_sub_class",
    "get_super_class",
    "get_class_expression",
    "get_domain",
    "get_range",
)
_CHILD_ITERATORS = (
    "operands",
    "properties",
    "class_expressions",
    "property_chain",
)


def _collect_property_iris(node: object, used: set[str]) -> None:
    """Recursively collect property IRIs from an OWL axiom or expression."""
    from hermit.owl_model.owl_property import OWLDataProperty, OWLObjectProperty

    if isinstance(node, (OWLObjectProperty, OWLDataProperty)):
        iri = node.iri
        used.add(iri.as_str() if hasattr(iri, "as_str") else str(iri))
        return
    for getter_name in _CHILD_GETTERS:
        getter = getattr(node, getter_name, None)
        if getter is None:
            continue
        try:
            child = getter()
        except Exception:  # noqa: BLE001 - probe-style traversal
            continue
        if child is not None:
            _collect_property_iris(child, used)
    for iterator_name in _CHILD_ITERATORS:
        iterator = getattr(node, iterator_name, None)
        if iterator is None:
            continue
        try:
            children = list(iterator())
        except Exception:  # noqa: BLE001 - probe-style traversal
            continue
        for child in children:
            _collect_property_iris(child, used)
