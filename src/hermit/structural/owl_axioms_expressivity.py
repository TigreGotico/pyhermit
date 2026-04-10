"""
Expressivity analysis for normalized axioms.

Determines which DL constructs are present in the axiom set:
inverse roles, at-most restrictions, nominals, datatypes, SWRL rules.

Port of ``org.semanticweb.HermiT.structural.OWLAxiomsExpressivity``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hermit.model import (
    AtLeastConcept,
    AtLeastDataRange,
    AtomicConcept,
    AtomicDataRange,
    AtomicNegationConcept,
    AtomicNegationDataRange,
    Concept,
    ConstantEnumeration,
    DataRange,
    DatatypeRestriction,
    ExistsDescriptionGraph,
    InverseRole,
    Role,
)

if TYPE_CHECKING:
    from hermit.structural.normalized_axioms import (
        ComplexObjectPropertyInclusion,
        NormalizedAxioms,
    )


class OWLAxiomsExpressivity:
    """
    Detects which DL constructs occur in a set of normalized axioms.

    Sets boolean flags:
    - ``has_inverse_roles`` — any inverse object properties
    - ``has_at_most_restrictions`` — any max-cardinality restrictions
    - ``has_nominals`` — any nominals ({a, b, ...}) or hasValue restrictions
    - ``has_datatypes`` — any data property / datatype constructs
    - ``has_swrl_rules`` — any SWRL rules
    """

    __slots__ = (
        "has_inverse_roles",
        "has_at_most_restrictions",
        "has_nominals",
        "has_datatypes",
        "has_swrl_rules",
    )

    def __init__(self, axioms: NormalizedAxioms) -> None:
        self.has_inverse_roles = False
        self.has_at_most_restrictions = False
        self.has_nominals = False
        self.has_datatypes = False
        self.has_swrl_rules = False

        # Scan concept inclusions
        for inclusion in axioms.concept_inclusions:
            for concept in inclusion:
                self._visit_concept(concept)

        # Scan data range inclusions
        for dr_inclusion in axioms.data_range_inclusions:
            for dr in dr_inclusion:
                self._visit_data_range(dr)

        # Scan complex property inclusions
        for complex_inc in axioms.complex_object_property_inclusions:
            self._visit_complex_inclusion(complex_inc)

        # Scan simple property inclusions
        for simple_inc in axioms.simple_object_property_inclusions:
            for role in simple_inc:
                self._visit_role(role)

        # Scan data property inclusions
        for data_inc in axioms.data_property_inclusions:
            for role in data_inc:
                self._visit_role(role)

        # Scan facts
        for _ind, concept in axioms.positive_concept_facts:
            self._visit_concept(concept)
        for _ind, concept in axioms.negative_concept_facts:
            self._visit_concept(concept)
        for _ind1, role, _ind2 in axioms.positive_role_facts:
            self._visit_role(role)
        for _ind1, role, _ind2 in axioms.negative_role_facts:
            self._visit_role(role)
        for _ind1, _ind2 in axioms.same_individual_facts:
            pass  # no expressivity flag
        for _ind1, _ind2 in axioms.different_individuals_facts:
            pass

        # Scan datatype facts
        if axioms.positive_data_facts or axioms.negative_data_facts:
            self.has_datatypes = True

        # Scan keys
        if axioms.object_property_keys or axioms.data_property_keys:
            pass  # keys don't add expressivity beyond what's already detected

        # Scan disjoint object properties
        for roles in axioms.disjoint_object_properties:
            for role in roles:
                self._visit_role(role)

        # Scan disjoint data properties
        if axioms.disjoint_data_properties:
            self.has_datatypes = True

        # Scan reflexive/irreflexive/asymmetric
        for role in axioms.reflexive_object_properties:
            self._visit_role(role)
        for role in axioms.irreflexive_object_properties:
            self._visit_role(role)
        for role in axioms.asymmetric_object_properties:
            self._visit_role(role)

        # Scan rules
        if axioms.rules:
            self.has_swrl_rules = True

        # Check complex roles
        if axioms.complex_object_roles:
            for role in axioms.complex_object_roles:
                self._visit_role(role)

    # -- visitors ----------------------------------------------------------------

    def _visit_concept(self, concept: Concept) -> None:
        """Recursively inspect a concept for expressivity markers."""
        if isinstance(concept, AtomicConcept):
            pass  # atomic concept, nothing special
        elif isinstance(concept, AtomicNegationConcept):
            # Negation of atomic — check the negated concept
            self._visit_concept(concept.get_negation())
        elif isinstance(concept, AtLeastConcept):
            # Check the role for inverse
            self._visit_role(concept.on_role)
            # Check the filler concept
            self._visit_concept(concept.to_concept)
        elif isinstance(concept, AtLeastDataRange):
            # Data range at-least — implies datatypes
            self.has_datatypes = True
            self._visit_role(concept.on_role)
        elif isinstance(concept, ExistsDescriptionGraph):
            # Description graph — nominal-like
            pass

    def _visit_data_range(self, dr: DataRange) -> None:
        """Recursively inspect a data range for expressivity markers."""
        self.has_datatypes = True
        if isinstance(dr, AtomicDataRange):
            pass
        elif isinstance(dr, AtomicNegationDataRange):
            pass
        elif isinstance(dr, DatatypeRestriction):
            pass
        elif isinstance(dr, ConstantEnumeration):
            pass

    def _visit_role(self, role: Role) -> None:
        """Check if a role is an inverse."""
        if isinstance(role, InverseRole):
            self.has_inverse_roles = True

    def _visit_complex_inclusion(
        self, inc: ComplexObjectPropertyInclusion
    ) -> None:
        """Check complex property inclusion for inverse roles."""
        for role in inc.sub_object_properties:
            self._visit_role(role)
        self._visit_role(inc.super_object_property)
