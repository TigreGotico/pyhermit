"""Binary Equality disjuncts in ground disjunctions must merge nodes.

A qualified data max-cardinality over more than two values produces a ground
disjunction whose disjuncts are plain binary Equality atoms over concrete
nodes; backtracking into a later disjunct goes through
``GroundDisjunction.add_disjunct_to_tableau``, which must dispatch Equality
to the merging manager rather than asserting it as a role.
"""
from __future__ import annotations

from hermit.configuration import Configuration
from hermit.owl_model.class_expression.restriction import OWLDataMaxCardinality
from hermit.owl_model.iri import IRI
from hermit.owl_model.owl_axiom import (
    OWLClassAssertionAxiom,
    OWLDataPropertyAssertionAxiom,
)
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_literal import OWLLiteral, TopOWLDatatype
from hermit.owl_model.owl_property import OWLDataProperty
from hermit.reasoner import Reasoner
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization

EX = "http://example.org/"


def _is_consistent(axioms: list) -> bool:
    norm = OWLNormalization().process_ontology(axioms)
    onto = OWLClausification().clausify(norm, ontology_iri="urn:test:gdeq")
    reasoner = Reasoner(onto, Configuration())
    try:
        return reasoner.is_consistent()
    finally:
        reasoner.dispose()


def test_data_max_cardinality_two_with_three_values_is_inconsistent() -> None:
    a = OWLNamedIndividual(IRI.create(EX + "a"))
    p = OWLDataProperty(IRI.create(EX + "p"))
    axioms = [
        OWLDataPropertyAssertionAxiom(a, p, OWLLiteral(1)),
        OWLDataPropertyAssertionAxiom(a, p, OWLLiteral(2)),
        OWLDataPropertyAssertionAxiom(a, p, OWLLiteral(3)),
        OWLClassAssertionAxiom(a, OWLDataMaxCardinality(2, p, TopOWLDatatype)),
    ]
    assert _is_consistent(axioms) is False


def test_data_max_cardinality_two_with_two_values_is_consistent() -> None:
    a = OWLNamedIndividual(IRI.create(EX + "a"))
    p = OWLDataProperty(IRI.create(EX + "p"))
    axioms = [
        OWLDataPropertyAssertionAxiom(a, p, OWLLiteral(1)),
        OWLDataPropertyAssertionAxiom(a, p, OWLLiteral(2)),
        OWLClassAssertionAxiom(a, OWLDataMaxCardinality(2, p, TopOWLDatatype)),
    ]
    assert _is_consistent(axioms) is True
