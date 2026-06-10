"""End-to-end tests for ObjectHasSelf (∃R.Self) support.

∃R.Self and ¬∃R.Self are literal concepts in the structural normal form: the
clausifier emits the role atom R(X,X) in the head (positive occurrence) or
the body (negative occurrence). The property must be simple.
"""
from __future__ import annotations

import pytest

from hermit.configuration import Configuration
from hermit.owl_model.class_expression import OWLClass
from hermit.owl_model.class_expression.class_expression import OWLObjectComplementOf
from hermit.owl_model.class_expression.restriction import OWLObjectHasSelf
from hermit.owl_model.iri import IRI
from hermit.owl_model.owl_axiom import (
    OWLClassAssertionAxiom,
    OWLObjectPropertyAssertionAxiom,
    OWLSubClassOfAxiom,
    OWLTransitiveObjectPropertyAxiom,
)
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_property import OWLObjectProperty
from hermit.reasoner import Reasoner
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization

EX = "http://example.org/"

LIKES = OWLObjectProperty(IRI.create(EX + "likes"))
PETER = OWLNamedIndividual(IRI.create(EX + "Peter"))
SELF_LIKES = OWLObjectHasSelf(LIKES)


def _reasoner(axioms: list) -> Reasoner:
    norm = OWLNormalization().process_ontology(axioms)
    onto = OWLClausification().clausify(norm, ontology_iri="urn:test:self")
    return Reasoner(onto, Configuration())


def _is_consistent(axioms: list) -> bool:
    reasoner = _reasoner(axioms)
    try:
        return reasoner.is_consistent()
    finally:
        reasoner.dispose()


def test_has_self_assertion_is_consistent() -> None:
    """ClassAssertion(∃likes.Self, Peter) is satisfiable."""
    assert _is_consistent([OWLClassAssertionAxiom(PETER, SELF_LIKES)]) is True


def test_has_self_entails_reflexive_edge() -> None:
    """∃likes.Self(Peter) plus the denial of likes(Peter,Peter) clashes.

    The positive Self literal must clausify to the head atom likes(X,X).
    The denial asserts Peter ∈ ∀likes.¬{Peter}-style marker: here it is
    encoded by making every likes-successor of Peter distinct from Peter
    via a fresh class.
    """
    marker = OWLClass(IRI.create(EX + "Marker"))
    from hermit.owl_model.class_expression.restriction import (
        OWLObjectAllValuesFrom,
    )

    axioms = [
        OWLClassAssertionAxiom(PETER, SELF_LIKES),
        OWLClassAssertionAxiom(PETER, OWLObjectComplementOf(marker)),
        OWLSubClassOfAxiom(
            OWLClass(IRI.create("http://www.w3.org/2002/07/owl#Thing")),
            OWLObjectAllValuesFrom(LIKES, marker),
        ),
    ]
    assert _is_consistent(axioms) is False


def test_reflexive_edge_entails_has_self() -> None:
    """likes(Peter,Peter) contradicts ¬∃likes.Self(Peter).

    The negated Self literal must clausify to the body atom likes(X,X) —
    this also exercises the DL-clause evaluator on a binary body atom with
    both arguments bound to the same variable.
    """
    axioms = [
        OWLObjectPropertyAssertionAxiom(PETER, LIKES, PETER),
        OWLClassAssertionAxiom(PETER, OWLObjectComplementOf(SELF_LIKES)),
    ]
    assert _is_consistent(axioms) is False


def test_negated_has_self_alone_is_consistent() -> None:
    assert (
        _is_consistent(
            [OWLClassAssertionAxiom(PETER, OWLObjectComplementOf(SELF_LIKES))]
        )
        is True
    )


@pytest.mark.parametrize("negated", [False, True])
def test_has_self_requires_simple_property(negated: bool) -> None:
    """A non-simple (transitive) property in a Self restriction is rejected."""
    a = OWLClass(IRI.create(EX + "A"))
    sup = OWLObjectComplementOf(SELF_LIKES) if negated else SELF_LIKES
    axioms = [
        OWLTransitiveObjectPropertyAxiom(LIKES),
        OWLSubClassOfAxiom(a, sup),
    ]
    norm = OWLNormalization().process_ontology(axioms)
    with pytest.raises(ValueError, match="[Nn]on-simple"):
        OWLClausification().clausify(norm, ontology_iri="urn:test:self")
