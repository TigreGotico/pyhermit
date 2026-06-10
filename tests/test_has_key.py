"""HasKey axiom tests: normalization, clausification, and key-driven merging.

Covers the Java HermiT ``OWLNormalization.visit(OWLHasKeyAxiom)`` /
``OWLClausification.clausifyKey`` behaviour: a key clause derives equality of
two named individuals that share values for all key properties, and a clash
when those individuals are asserted different.
"""

from __future__ import annotations

from hermit import Configuration, Reasoner
from hermit.model import (
    AtomicConcept,
    AtomicNegationConcept,
    AtomicRole,
    Equality,
    Individual,
    Inequality,
)
from hermit.owl_model.class_expression import OWLClass, OWLObjectUnionOf
from hermit.owl_model.iri import IRI
from hermit.owl_model.owl_axiom import (
    OWLClassAssertionAxiom,
    OWLDataPropertyAssertionAxiom,
    OWLDifferentIndividualsAxiom,
    OWLHasKeyAxiom,
    OWLObjectPropertyAssertionAxiom,
)
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_literal import _OWLLiteralImplString as OWLStringLiteral
from hermit.owl_model.owl_property import OWLDataProperty, OWLObjectProperty
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization

NS = "http://test.org#"


def _ind(local: str) -> OWLNamedIndividual:
    return OWLNamedIndividual(IRI.create(NS + local))


def _cls(local: str) -> OWLClass:
    return OWLClass(IRI.create(NS + local))


def _obj_prop(local: str) -> OWLObjectProperty:
    return OWLObjectProperty(IRI.create(NS + local))


def _data_prop(local: str) -> OWLDataProperty:
    return OWLDataProperty(IRI.create(NS + local))


def _reasoner(axioms: list) -> Reasoner:
    config = Configuration()
    config.throw_inconsistent_ontology_exception = False
    norm = OWLNormalization().process_ontology(axioms)
    onto = OWLClausification().clausify(norm, ontology_iri="urn:test:haskey")
    return Reasoner(onto, config)


class TestDataPropertyKeyMerging:
    """HasKey with a data property: equal key values merge named individuals."""

    def test_equal_key_values_merge(self):
        thing = OWLClass(IRI.create("http://www.w3.org/2002/07/owl#Thing"))
        ssn = _data_prop("hasSSN")
        axioms = [
            OWLHasKeyAxiom(thing, [ssn]),
            OWLDataPropertyAssertionAxiom(
                _ind("Peter"), ssn, OWLStringLiteral("123-45-6789")
            ),
            OWLDataPropertyAssertionAxiom(
                _ind("Peter_Griffin"), ssn, OWLStringLiteral("123-45-6789")
            ),
        ]
        reasoner = _reasoner(axioms)
        assert reasoner.is_consistent()
        assert reasoner.is_same_individual(
            Individual.create(NS + "Peter"), Individual.create(NS + "Peter_Griffin")
        )

    def test_unequal_key_values_do_not_merge(self):
        thing = OWLClass(IRI.create("http://www.w3.org/2002/07/owl#Thing"))
        ssn = _data_prop("hasSSN")
        axioms = [
            OWLHasKeyAxiom(thing, [ssn]),
            OWLDataPropertyAssertionAxiom(
                _ind("Peter"), ssn, OWLStringLiteral("123-45-6789")
            ),
            OWLDataPropertyAssertionAxiom(
                _ind("Peter_Griffin"), ssn, OWLStringLiteral("987-65-4321")
            ),
        ]
        reasoner = _reasoner(axioms)
        assert reasoner.is_consistent()
        assert not reasoner.is_same_individual(
            Individual.create(NS + "Peter"), Individual.create(NS + "Peter_Griffin")
        )

    def test_key_clash_with_different_individuals(self):
        thing = OWLClass(IRI.create("http://www.w3.org/2002/07/owl#Thing"))
        ssn = _data_prop("hasSSN")
        axioms = [
            OWLHasKeyAxiom(thing, [ssn]),
            OWLDataPropertyAssertionAxiom(
                _ind("Peter"), ssn, OWLStringLiteral("123-45-6789")
            ),
            OWLDataPropertyAssertionAxiom(
                _ind("Peter_Griffin"), ssn, OWLStringLiteral("123-45-6789")
            ),
            OWLDifferentIndividualsAxiom([_ind("Peter"), _ind("Peter_Griffin")]),
        ]
        reasoner = _reasoner(axioms)
        assert not reasoner.is_consistent()

    def test_key_scoped_to_class(self):
        """The key only applies to instances of the key's class expression."""
        member = _cls("GriffinFamilyMember")
        name = _data_prop("hasName")
        axioms = [
            OWLHasKeyAxiom(member, [name]),
            OWLDataPropertyAssertionAxiom(
                _ind("Peter"), name, OWLStringLiteral("Peter")
            ),
            OWLClassAssertionAxiom(_ind("Peter"), member),
            OWLDataPropertyAssertionAxiom(
                _ind("Peter_Griffin"), name, OWLStringLiteral("Peter")
            ),
            OWLClassAssertionAxiom(_ind("Peter_Griffin"), member),
            OWLDataPropertyAssertionAxiom(
                _ind("StPeter"), name, OWLStringLiteral("Peter")
            ),
        ]
        reasoner = _reasoner(axioms)
        assert reasoner.is_consistent()
        peter = Individual.create(NS + "Peter")
        peter_griffin = Individual.create(NS + "Peter_Griffin")
        st_peter = Individual.create(NS + "StPeter")
        assert reasoner.is_same_individual(peter, peter_griffin)
        assert not reasoner.is_same_individual(peter, st_peter)
        assert not reasoner.is_same_individual(peter_griffin, st_peter)


class TestObjectPropertyKeyMerging:
    """HasKey with an object property: shared named successors merge."""

    def test_equal_object_key_values_merge(self):
        thing = OWLClass(IRI.create("http://www.w3.org/2002/07/owl#Thing"))
        owner = _obj_prop("hasOwner")
        axioms = [
            OWLHasKeyAxiom(thing, [owner]),
            OWLObjectPropertyAssertionAxiom(_ind("car1"), owner, _ind("alice")),
            OWLObjectPropertyAssertionAxiom(_ind("car2"), owner, _ind("alice")),
        ]
        reasoner = _reasoner(axioms)
        assert reasoner.is_consistent()
        assert reasoner.is_same_individual(
            Individual.create(NS + "car1"), Individual.create(NS + "car2")
        )

    def test_unequal_object_key_values_do_not_merge(self):
        thing = OWLClass(IRI.create("http://www.w3.org/2002/07/owl#Thing"))
        owner = _obj_prop("hasOwner")
        axioms = [
            OWLHasKeyAxiom(thing, [owner]),
            OWLObjectPropertyAssertionAxiom(_ind("car1"), owner, _ind("alice")),
            OWLObjectPropertyAssertionAxiom(_ind("car2"), owner, _ind("bob")),
        ]
        reasoner = _reasoner(axioms)
        assert reasoner.is_consistent()
        assert not reasoner.is_same_individual(
            Individual.create(NS + "car1"), Individual.create(NS + "car2")
        )

    def test_object_key_inconsistency(self):
        thing = OWLClass(IRI.create("http://www.w3.org/2002/07/owl#Thing"))
        owner = _obj_prop("hasOwner")
        axioms = [
            OWLHasKeyAxiom(thing, [owner]),
            OWLObjectPropertyAssertionAxiom(_ind("car1"), owner, _ind("alice")),
            OWLObjectPropertyAssertionAxiom(_ind("car2"), owner, _ind("alice")),
            OWLDifferentIndividualsAxiom([_ind("car1"), _ind("car2")]),
        ]
        reasoner = _reasoner(axioms)
        assert not reasoner.is_consistent()


class TestHasKeyNormalization:
    """Shape of the normalized keys and the resulting DL clauses."""

    def test_mixed_key_yields_single_object_key(self):
        thing = OWLClass(IRI.create("http://www.w3.org/2002/07/owl#Thing"))
        owner = _obj_prop("hasOwner")
        plate = _data_prop("hasPlate")
        norm = OWLNormalization().process_ontology(
            [OWLHasKeyAxiom(thing, [owner, plate])]
        )
        assert len(norm.object_property_keys) == 1
        assert not norm.data_property_keys
        key = norm.object_property_keys[0]
        assert key.properties == (AtomicRole.create(NS + "hasOwner"),)
        assert key.data_properties == (AtomicRole.create(NS + "hasPlate"),)

    def test_data_only_key_yields_data_key(self):
        member = _cls("Member")
        name = _data_prop("hasName")
        norm = OWLNormalization().process_ontology(
            [OWLHasKeyAxiom(member, [name])]
        )
        assert not norm.object_property_keys
        assert len(norm.data_property_keys) == 1
        key = norm.data_property_keys[0]
        assert key.concept == AtomicConcept.create(NS + "Member")
        assert key.properties == (AtomicRole.create(NS + "hasName"),)

    def test_complex_class_expression_gets_definition(self):
        union = OWLObjectUnionOf([_cls("A"), _cls("B")])
        name = _data_prop("hasName")
        norm = OWLNormalization().process_ontology([OWLHasKeyAxiom(union, [name])])
        assert len(norm.data_property_keys) == 1
        concept = norm.data_property_keys[0].concept
        assert isinstance(concept, AtomicConcept)
        assert concept.iri.startswith("internal:def#")

    def test_data_key_clause_shape(self):
        """The key clause matches Java clausifyKey: NAMED guards, equality head,
        per-property body atoms and head inequality."""
        member = _cls("Member")
        name = _data_prop("hasName")
        norm = OWLNormalization().process_ontology(
            [OWLHasKeyAxiom(member, [name])]
        )
        clause = OWLClausification._clausify_data_key(norm.data_property_keys[0])

        head_predicates = [atom.predicate for atom in clause.head_atoms]
        assert Equality.INSTANCE in head_predicates
        assert Inequality.INSTANCE in head_predicates

        body_predicates = [atom.predicate for atom in clause.body_atoms]
        assert body_predicates.count(AtomicConcept.INTERNAL_NAMED) == 2
        assert body_predicates.count(AtomicConcept.create(NS + "Member")) == 2
        assert body_predicates.count(AtomicRole.create(NS + "hasName")) == 2

    def test_negated_concept_key_clause_shape(self):
        """A negated concept name moves the positive atoms into the head."""
        from hermit.structural.normalized_axioms import DataPropertyKey

        negated = AtomicNegationConcept.create(AtomicConcept.create(NS + "Member"))
        key = DataPropertyKey(negated, (AtomicRole.create(NS + "hasName"),))
        clause = OWLClausification._clausify_data_key(key)

        head_predicates = [atom.predicate for atom in clause.head_atoms]
        assert head_predicates.count(AtomicConcept.create(NS + "Member")) == 2
        body_predicates = [atom.predicate for atom in clause.body_atoms]
        assert AtomicConcept.create(NS + "Member") not in body_predicates
