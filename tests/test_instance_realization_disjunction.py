"""Instance realization must agree across classification algorithms.

Mirrors Java ``InstanceManager.isInstance``: a possible instance is
confirmed by testing satisfiability of the ABox plus the negated class
assertion. The ontology below derives ``Q(stewie)`` only through a
disjunction (``Q == not Girl``), so with disjunction learning enabled the
read-off marks stewie as a *possible* instance of ``Q`` and the answer
depends on the confirmation test.
"""

from __future__ import annotations

import pytest

from hermit.configuration import Configuration
from hermit.model import AtomicConcept, Individual
from hermit.owl_model.class_expression import OWLClass, OWLObjectComplementOf
from hermit.owl_model.iri import IRI
from hermit.owl_model.owl_axiom import (
    OWLClassAssertionAxiom,
    OWLDisjointClassesAxiom,
    OWLEquivalentClassesAxiom,
)
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.reasoner import Reasoner
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization

_NS = "http://example.org/"


def _build_reasoner(use_disjunction_learning: bool) -> Reasoner:
    boy = OWLClass(IRI.create(_NS + "Boy"))
    girl = OWLClass(IRI.create(_NS + "Girl"))
    q = OWLClass(IRI.create(_NS + "Q"))
    stewie = OWLNamedIndividual(IRI.create(_NS + "Stewie"))
    axioms = [
        OWLDisjointClassesAxiom([boy, girl]),
        OWLClassAssertionAxiom(stewie, boy),
        OWLEquivalentClassesAxiom([q, OWLObjectComplementOf(girl)]),
    ]
    config = Configuration()
    config.throw_inconsistent_ontology_exception = False
    config.use_disjunction_learning = use_disjunction_learning
    normalized = OWLNormalization().process_ontology(axioms)
    ontology = OWLClausification().clausify(
        normalized, ontology_iri="urn:test:instance-realization"
    )
    return Reasoner(ontology, config)


@pytest.mark.parametrize("use_disjunction_learning", [False, True])
class TestComplementInstanceRealization:
    def test_boy_subclass_of_q(self, use_disjunction_learning: bool) -> None:
        reasoner = _build_reasoner(use_disjunction_learning)
        try:
            assert reasoner.is_sub_class_of(
                AtomicConcept.create(_NS + "Boy"),
                AtomicConcept.create(_NS + "Q"),
            )
        finally:
            reasoner.dispose()

    def test_stewie_has_type_q(self, use_disjunction_learning: bool) -> None:
        reasoner = _build_reasoner(use_disjunction_learning)
        try:
            assert reasoner.has_type(
                Individual.create(_NS + "Stewie"),
                AtomicConcept.create(_NS + "Q"),
            )
        finally:
            reasoner.dispose()

    def test_stewie_not_girl(self, use_disjunction_learning: bool) -> None:
        reasoner = _build_reasoner(use_disjunction_learning)
        try:
            assert not reasoner.has_type(
                Individual.create(_NS + "Stewie"),
                AtomicConcept.create(_NS + "Girl"),
            )
        finally:
            reasoner.dispose()

    def test_get_instances_of_q(self, use_disjunction_learning: bool) -> None:
        reasoner = _build_reasoner(use_disjunction_learning)
        try:
            assert Individual.create(_NS + "Stewie") in reasoner.get_instances(
                AtomicConcept.create(_NS + "Q")
            )
        finally:
            reasoner.dispose()
