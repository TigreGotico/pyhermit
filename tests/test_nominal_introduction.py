"""End-to-end tests for the nominal introduction (NI) rule.

Inverse-functional / functional object properties must clausify through the
at-most path (AnnotatedEquality heads) so that equalities between deep tree
nodes centred on a root node are routed to the NominalIntroductionManager
instead of being merged directly.
"""
from __future__ import annotations

from hermit.configuration import Configuration
from hermit.owl_model.class_expression import OWLClass
from hermit.owl_model.class_expression.restriction import (
    OWLObjectOneOf,
    OWLObjectSomeValuesFrom,
)
from hermit.owl_model.iri import IRI
from hermit.owl_model.owl_axiom import (
    OWLClassAssertionAxiom,
    OWLFunctionalObjectPropertyAxiom,
    OWLInverseFunctionalObjectPropertyAxiom,
    OWLSubClassOfAxiom,
)
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_property import OWLObjectProperty
from hermit.reasoner import Reasoner
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization

EX = "http://example.org/"


def _is_consistent(axioms: list) -> bool:
    norm = OWLNormalization().process_ontology(axioms)
    onto = OWLClausification().clausify(norm, ontology_iri="urn:test:ni")
    reasoner = Reasoner(onto, Configuration())
    try:
        return reasoner.is_consistent()
    finally:
        reasoner.dispose()


def test_inverse_functional_merge_of_deep_tree_nodes_uses_ni_rule() -> None:
    """Two depth-2 tree nodes with a common f-successor nominal must merge.

    The inverse-functional property forces the equality of two tree nodes in
    different branches; the merge is only legal through the NI rule (the
    annotated equality is centred on the root node for ``o``).
    """
    o = OWLNamedIndividual(IRI.create(EX + "o"))
    d = OWLClass(IRI.create(EX + "D"))
    a = OWLClass(IRI.create(EX + "A"))
    a2 = OWLClass(IRI.create(EX + "A2"))
    b = OWLClass(IRI.create(EX + "B"))
    b2 = OWLClass(IRI.create(EX + "B2"))
    r = OWLObjectProperty(IRI.create(EX + "r"))
    s = OWLObjectProperty(IRI.create(EX + "s"))
    f = OWLObjectProperty(IRI.create(EX + "f"))
    nominal_o = OWLObjectOneOf([o])
    axioms = [
        OWLClassAssertionAxiom(o, d),
        OWLSubClassOfAxiom(d, OWLObjectSomeValuesFrom(r, a)),
        OWLSubClassOfAxiom(a, OWLObjectSomeValuesFrom(r, a2)),
        OWLSubClassOfAxiom(a2, OWLObjectSomeValuesFrom(f, nominal_o)),
        OWLSubClassOfAxiom(d, OWLObjectSomeValuesFrom(s, b)),
        OWLSubClassOfAxiom(b, OWLObjectSomeValuesFrom(s, b2)),
        OWLSubClassOfAxiom(b2, OWLObjectSomeValuesFrom(f, nominal_o)),
        OWLInverseFunctionalObjectPropertyAxiom(f),
    ]
    assert _is_consistent(axioms) is True


def test_functional_property_still_merges_successors() -> None:
    """A functional role with two successors in disjoint classes is detected."""
    i = OWLNamedIndividual(IRI.create(EX + "i"))
    c = OWLClass(IRI.create(EX + "C"))
    a = OWLClass(IRI.create(EX + "A"))
    f = OWLObjectProperty(IRI.create(EX + "f"))
    axioms = [
        OWLClassAssertionAxiom(i, c),
        OWLSubClassOfAxiom(c, OWLObjectSomeValuesFrom(f, a)),
        OWLSubClassOfAxiom(
            c,
            OWLObjectSomeValuesFrom(f, a.get_object_complement_of()),
        ),
        OWLFunctionalObjectPropertyAxiom(f),
    ]
    assert _is_consistent(axioms) is False
