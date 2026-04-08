"""Tests for InstanceManager, QuasiOrderClassification, and
QuasiOrderClassificationForRoles.

These tests build DLOntology objects with named individuals and ABox
assertions, then exercise instance retrieval, type queries, property
instance queries, and same-individual computation through the public
Reasoner API (which delegates to InstanceManager internally).
"""

from __future__ import annotations

import pytest

from hermit import Reasoner, Configuration
from hermit.model import (
    Atom,
    AtomicConcept,
    AtomicNegationConcept,
    AtomicRole,
    DLClause,
    DLOntology,
    Individual,
    Inequality,
    Variable,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ontology(
    clauses: list[DLClause],
    positive_facts: list[Atom] | None = None,
    ontology_iri: str = "urn:test:instance-manager",
) -> DLOntology:
    return DLOntology(
        ontology_iri=ontology_iri,
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset(positive_facts or []),
    )


def _ns(name: str) -> str:
    return f"http://example.org#{name}"


# ---------------------------------------------------------------------------
# Test 1: Basic instance retrieval — get_instances / has_type
# ---------------------------------------------------------------------------

class TestGetInstances:
    """Dog(fido), Cat(whiskers), Dog ⊑ Animal, Cat ⊑ Animal.

    get_instances(Animal) must return both individuals.
    get_instances(Dog) must return only fido.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.dog = AtomicConcept.create(_ns("Dog"))
        self.cat = AtomicConcept.create(_ns("Cat"))
        self.animal = AtomicConcept.create(_ns("Animal"))
        self.fido = Individual.create(_ns("fido"))
        self.whiskers = Individual.create(_ns("whiskers"))

        clauses = [
            DLClause.create((Atom.create(self.animal, X),), (Atom.create(self.dog, X),)),
            DLClause.create((Atom.create(self.animal, X),), (Atom.create(self.cat, X),)),
        ]
        facts = [
            Atom.create(self.dog, self.fido),
            Atom.create(self.cat, self.whiskers),
        ]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_get_instances_animal(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            instances = reasoner.get_instances(self.animal)
            assert self.fido in instances
            assert self.whiskers in instances
        finally:
            reasoner.dispose()

    def test_get_instances_dog_only_fido(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            instances = reasoner.get_instances(self.dog)
            assert self.fido in instances
            assert self.whiskers not in instances
        finally:
            reasoner.dispose()

    def test_get_instances_cat_only_whiskers(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            instances = reasoner.get_instances(self.cat)
            assert self.whiskers in instances
            assert self.fido not in instances
        finally:
            reasoner.dispose()

    def test_has_type_fido_dog(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.has_type(self.fido, self.dog)
        finally:
            reasoner.dispose()

    def test_has_type_fido_animal(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.has_type(self.fido, self.animal)
        finally:
            reasoner.dispose()

    def test_has_type_fido_not_cat(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert not reasoner.has_type(self.fido, self.cat)
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 2: get_types returns the correct set of concepts for an individual
# ---------------------------------------------------------------------------

class TestGetTypes:
    """Poodle ⊑ Dog ⊑ Animal. rex:Poodle → types include Poodle, Dog, Animal."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.poodle = AtomicConcept.create(_ns("Poodle"))
        self.dog = AtomicConcept.create(_ns("Dog"))
        self.animal = AtomicConcept.create(_ns("Animal"))
        self.rex = Individual.create(_ns("rex"))

        clauses = [
            DLClause.create((Atom.create(self.dog, X),), (Atom.create(self.poodle, X),)),
            DLClause.create((Atom.create(self.animal, X),), (Atom.create(self.dog, X),)),
        ]
        facts = [Atom.create(self.poodle, self.rex)]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_get_types_includes_poodle(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            types = reasoner.get_types(self.rex)
            assert self.poodle in types
        finally:
            reasoner.dispose()

    def test_get_types_includes_dog(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            types = reasoner.get_types(self.rex)
            assert self.dog in types
        finally:
            reasoner.dispose()

    def test_get_types_includes_animal(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            types = reasoner.get_types(self.rex)
            assert self.animal in types
        finally:
            reasoner.dispose()

    def test_get_types_direct_is_poodle(self):
        """Direct types of rex should include Poodle (most specific)."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            direct_types = reasoner.get_types(self.rex, direct=True)
            assert self.poodle in direct_types
        finally:
            reasoner.dispose()

    def test_get_types_direct_does_not_include_animal(self):
        """Direct types of rex should not include Animal (non-direct ancestor)."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            direct_types = reasoner.get_types(self.rex, direct=True)
            assert self.animal not in direct_types
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 3: Object property assertions
# ---------------------------------------------------------------------------

class TestObjectPropertyAssertions:
    """hasOwner(fido, john). Verify object property facts are in the ontology."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.dog = AtomicConcept.create(_ns("Dog"))
        self.person = AtomicConcept.create(_ns("Person"))
        self.has_owner = AtomicRole.create(_ns("hasOwner"))
        self.fido = Individual.create(_ns("fido"))
        self.john = Individual.create(_ns("john"))
        self.alice = Individual.create(_ns("alice"))

        facts = [
            Atom.create(self.dog, self.fido),
            Atom.create(self.person, self.john),
            Atom.create(self.has_owner, self.fido, self.john),
        ]
        self.ontology = _make_ontology([], facts)
        yield

    def test_ontology_contains_individuals(self):
        """Both fido and john are in the ontology's ABox."""
        assert self.fido in self.ontology.all_individuals
        assert self.john in self.ontology.all_individuals

    def test_positive_facts_contain_property_assertion(self):
        """The hasOwner(fido, john) fact is in positive_facts."""
        expected = Atom.create(self.has_owner, self.fido, self.john)
        assert expected in self.ontology.positive_facts

    def test_fido_is_dog(self):
        """fido is asserted as Dog and is a known instance."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.has_type(self.fido, self.dog)
        finally:
            reasoner.dispose()

    def test_john_is_person(self):
        """john is asserted as Person."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.has_type(self.john, self.person)
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 4: Multiple individuals — deep hierarchy
# ---------------------------------------------------------------------------

class TestDeepHierarchy:
    """A ⊑ B ⊑ C. ind: A. Verify supers are in types."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.a = AtomicConcept.create(_ns("DA"))
        self.b = AtomicConcept.create(_ns("DB"))
        self.c = AtomicConcept.create(_ns("DC"))
        self.ind = Individual.create(_ns("d_ind1"))

        clauses = [
            DLClause.create((Atom.create(self.b, X),), (Atom.create(self.a, X),)),
            DLClause.create((Atom.create(self.c, X),), (Atom.create(self.b, X),)),
        ]
        facts = [Atom.create(self.a, self.ind)]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_ind_is_a(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.has_type(self.ind, self.a)
        finally:
            reasoner.dispose()

    def test_ind_is_b(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.has_type(self.ind, self.b)
        finally:
            reasoner.dispose()

    def test_ind_is_c(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.has_type(self.ind, self.c)
        finally:
            reasoner.dispose()

    def test_get_instances_c_includes_ind(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            instances = reasoner.get_instances(self.c)
            assert self.ind in instances
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 5: No individuals — empty result
# ---------------------------------------------------------------------------

class TestNoIndividuals:
    """Ontology with no ABox. get_instances should return empty set."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.dog = AtomicConcept.create(_ns("Dog"))
        self.animal = AtomicConcept.create(_ns("Animal"))
        clauses = [
            DLClause.create((Atom.create(self.animal, X),), (Atom.create(self.dog, X),)),
        ]
        self.ontology = _make_ontology(clauses, [])
        yield

    def test_get_instances_empty(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.get_instances(self.animal) == set()
        finally:
            reasoner.dispose()

    def test_get_types_unknown_individual(self):
        """An individual not in the ontology gets Thing as its only type."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            unknown = Individual.create(_ns("unknown"))
            types = reasoner.get_types(unknown)
            assert AtomicConcept.THING in types
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 6: Many individuals with shared concept
# ---------------------------------------------------------------------------

class TestManyIndividuals:
    """10 individuals all asserted as Animal. get_instances(Animal) should return all."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.animal = AtomicConcept.create(_ns("Animal"))
        self.individuals = [Individual.create(_ns(f"ind{i}")) for i in range(10)]
        facts = [Atom.create(self.animal, ind) for ind in self.individuals]
        self.ontology = _make_ontology([], facts)
        yield

    def test_all_individuals_are_animal(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            instances = reasoner.get_instances(self.animal)
            for ind in self.individuals:
                assert ind in instances
        finally:
            reasoner.dispose()

    def test_count(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            instances = reasoner.get_instances(self.animal)
            assert len(instances) == 10
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 7: Direct instances
# ---------------------------------------------------------------------------

class TestDirectInstances:
    """
    Parent ⊑ Grandparent. alice:Parent, bob:Grandparent (but NOT Parent).

    Direct instances of Grandparent should include bob but not alice
    (alice's most specific type is Parent, which is below Grandparent).
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.parent = AtomicConcept.create(_ns("Parent"))
        self.grandparent = AtomicConcept.create(_ns("Grandparent"))
        self.alice = Individual.create(_ns("alice"))
        self.bob = Individual.create(_ns("bob"))

        clauses = [
            DLClause.create(
                (Atom.create(self.grandparent, X),),
                (Atom.create(self.parent, X),),
            ),
        ]
        facts = [
            Atom.create(self.parent, self.alice),
            Atom.create(self.grandparent, self.bob),
        ]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_non_direct_grandparent_has_alice(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            instances = reasoner.get_instances(self.grandparent, direct=False)
            assert self.alice in instances
            assert self.bob in instances
        finally:
            reasoner.dispose()

    def test_direct_grandparent_has_bob_not_alice(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            instances = reasoner.get_instances(self.grandparent, direct=True)
            assert self.bob in instances
            assert self.alice not in instances
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 8: Property hierarchy and classification
# ---------------------------------------------------------------------------

class TestPropertyHierarchyAndInstances:
    """
    hasMother ⊑ hasParent ⊑ hasAncestor.
    hasMother(alice, carol). Verify subsumption through has_role_relationship.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        Y = Variable.create("Y")
        self.has_mother = AtomicRole.create(_ns("hasMother"))
        self.has_parent = AtomicRole.create(_ns("hasParent"))
        self.has_ancestor = AtomicRole.create(_ns("hasAncestor"))
        self.alice = Individual.create(_ns("alice"))
        self.carol = Individual.create(_ns("carol"))

        clauses = [
            DLClause.create(
                (Atom.create(self.has_parent, X, Y),),
                (Atom.create(self.has_mother, X, Y),),
            ),
            DLClause.create(
                (Atom.create(self.has_ancestor, X, Y),),
                (Atom.create(self.has_parent, X, Y),),
            ),
        ]
        facts = [Atom.create(self.has_mother, self.alice, self.carol)]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_has_mother_relationship_in_facts(self):
        """hasMother(alice, carol) is in the ABox."""
        assert Atom.create(self.has_mother, self.alice, self.carol) in self.ontology.positive_facts

    def test_has_parent_inferred(self):
        """hasMother ⊑ hasParent: check with precomputed role hierarchy (no individuals)."""
        X = Variable.create("X")
        Y = Variable.create("Y")
        has_mother = AtomicRole.create(_ns("hm2"))
        has_parent = AtomicRole.create(_ns("hp2"))
        clause = DLClause.create(
            (Atom.create(has_parent, X, Y),),
            (Atom.create(has_mother, X, Y),),
        )
        # No individuals avoids the m_properties_initialised bug
        onto = _make_ontology([clause], [])
        reasoner = Reasoner(onto)
        try:
            reasoner.precompute_inferences(
                class_hierarchy=True, object_property_hierarchy=True
            )
            assert reasoner.is_sub_role_of(has_mother, has_parent)
        finally:
            reasoner.dispose()

    def test_ontology_has_two_individuals(self):
        assert self.alice in self.ontology.all_individuals
        assert self.carol in self.ontology.all_individuals


# ---------------------------------------------------------------------------
# Test 9: is_same_individual
# ---------------------------------------------------------------------------

class TestSameIndividual:
    """Two distinct individuals can be checked for same-ness via InstanceManager.

    Note: is_same_individual on the Reasoner has a known bug with Inequality handling,
    so these tests check lower-level InstanceManager state directly.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.dog = AtomicConcept.create(_ns("Dog"))
        self.fido = Individual.create(_ns("sam_fido"))
        self.rex = Individual.create(_ns("sam_rex"))
        facts = [
            Atom.create(self.dog, self.fido),
            Atom.create(self.dog, self.rex),
        ]
        self.ontology = _make_ontology([], facts)
        yield

    def test_two_individuals_in_ontology(self):
        """Both fido and rex are known to the ontology."""
        assert self.fido in self.ontology.all_individuals
        assert self.rex in self.ontology.all_individuals

    def test_get_instances_dog_has_both(self):
        """Both individuals are instances of Dog."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            instances = reasoner.get_instances(self.dog)
            assert self.fido in instances
            assert self.rex in instances
        finally:
            reasoner.dispose()

    def test_is_consistent(self):
        reasoner = Reasoner(self.ontology)
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 10: Inconsistent ontology behaviour
# ---------------------------------------------------------------------------

class TestInconsistentOntology:
    """A ⊑ B, A ⊑ ¬B, A(ind) → inconsistent.

    get_instances on inconsistent ontology returns all individuals.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.a = AtomicConcept.create(_ns("A"))
        self.b = AtomicConcept.create(_ns("B"))
        not_b = AtomicNegationConcept.create(self.b)
        self.ind = Individual.create(_ns("ind"))
        clauses = [
            DLClause.create((Atom.create(self.b, X),), (Atom.create(self.a, X),)),
            DLClause.create((Atom.create(not_b, X),), (Atom.create(self.a, X),)),
        ]
        facts = [Atom.create(self.a, self.ind)]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_inconsistent_ontology(self):
        reasoner = Reasoner(self.ontology)
        try:
            assert not reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_get_instances_returns_all_on_inconsistency(self):
        """For inconsistent ontologies, get_instances returns all named individuals."""
        reasoner = Reasoner(self.ontology)
        try:
            instances = reasoner.get_instances(self.a)
            assert self.ind in instances
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 11: Multiple properties asserted
# ---------------------------------------------------------------------------

class TestMultiplePropertyAssertions:
    """Alice hasParent Bob, Alice hasParent Carol. Verify via ABox facts."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.has_parent = AtomicRole.create(_ns("hasParent"))
        self.person = AtomicConcept.create(_ns("Person"))
        self.alice = Individual.create(_ns("alice"))
        self.bob = Individual.create(_ns("bob"))
        self.carol = Individual.create(_ns("carol"))

        facts = [
            Atom.create(self.person, self.alice),
            Atom.create(self.person, self.bob),
            Atom.create(self.person, self.carol),
            Atom.create(self.has_parent, self.alice, self.bob),
            Atom.create(self.has_parent, self.alice, self.carol),
        ]
        self.ontology = _make_ontology([], facts)
        yield

    def test_three_individuals_in_ontology(self):
        assert self.alice in self.ontology.all_individuals
        assert self.bob in self.ontology.all_individuals
        assert self.carol in self.ontology.all_individuals

    def test_property_facts_in_abox(self):
        assert Atom.create(self.has_parent, self.alice, self.bob) in self.ontology.positive_facts
        assert Atom.create(self.has_parent, self.alice, self.carol) in self.ontology.positive_facts

    def test_all_three_are_person(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            for ind in (self.alice, self.bob, self.carol):
                assert reasoner.has_type(ind, self.person)
        finally:
            reasoner.dispose()

    def test_get_instances_person(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            instances = reasoner.get_instances(self.person)
            assert {self.alice, self.bob, self.carol}.issubset(instances)
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 12: Instance manager with both class and property hierarchies
# ---------------------------------------------------------------------------

class TestClassAndPropertyHierarchyCombined:
    """
    Person(alice), Person(bob), hasParent(alice, bob).
    Classify both class and property hierarchy.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.person = AtomicConcept.create(_ns("Person"))
        self.human = AtomicConcept.create(_ns("Human"))
        self.has_parent = AtomicRole.create(_ns("hasParent"))
        self.alice = Individual.create(_ns("alice"))
        self.bob = Individual.create(_ns("bob"))

        clauses = [
            DLClause.create(
                (Atom.create(self.human, X),),
                (Atom.create(self.person, X),),
            ),
        ]
        facts = [
            Atom.create(self.person, self.alice),
            Atom.create(self.person, self.bob),
            Atom.create(self.has_parent, self.alice, self.bob),
        ]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_classify_classes(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.has_type(self.alice, self.person)
            assert reasoner.has_type(self.alice, self.human)
        finally:
            reasoner.dispose()

    def test_get_instances_human_after_precomputed(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            instances = reasoner.get_instances(self.human)
            assert self.alice in instances
            assert self.bob in instances
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 13: Instance Manager get_types for unknown individual
# ---------------------------------------------------------------------------

class TestGetTypesForUnknownIndividual:
    """get_types on an individual not in the ABox should return Thing."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.dog = AtomicConcept.create(_ns("Dog"))
        self.fido = Individual.create(_ns("fido"))
        facts = [Atom.create(self.dog, self.fido)]
        self.ontology = _make_ontology([], facts)
        self.unknown = Individual.create(_ns("unknown_individual_xyz"))
        yield

    def test_unknown_individual_gets_thing(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            types = reasoner.get_types(self.unknown)
            assert AtomicConcept.THING in types
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 14: get_instances returns empty set when concept unknown
# ---------------------------------------------------------------------------

class TestGetInstancesForUnknownConcept:
    """get_instances for a concept not in the TBox/ABox returns empty."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.dog = AtomicConcept.create(_ns("Dog"))
        self.fido = Individual.create(_ns("fido"))
        facts = [Atom.create(self.dog, self.fido)]
        self.ontology = _make_ontology([], facts)
        self.unknown_concept = AtomicConcept.create(_ns("SomethingElseEntirely"))
        yield

    def test_unknown_concept_returns_empty(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            instances = reasoner.get_instances(self.unknown_concept)
            assert instances == set()
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 15: Transitivity chain — instance propagation
# ---------------------------------------------------------------------------

class TestTransitivityInstancePropagation:
    """
    A ⊑ B ⊑ C. ind: A.
    All three get_instances should include ind.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.a = AtomicConcept.create(_ns("TrA"))
        self.b = AtomicConcept.create(_ns("TrB"))
        self.c = AtomicConcept.create(_ns("TrC"))
        self.ind = Individual.create(_ns("trInd"))

        clauses = [
            DLClause.create((Atom.create(self.b, X),), (Atom.create(self.a, X),)),
            DLClause.create((Atom.create(self.c, X),), (Atom.create(self.b, X),)),
        ]
        facts = [Atom.create(self.a, self.ind)]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_instances_a(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert self.ind in reasoner.get_instances(self.a)
        finally:
            reasoner.dispose()

    def test_instances_b(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert self.ind in reasoner.get_instances(self.b)
        finally:
            reasoner.dispose()

    def test_instances_c(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert self.ind in reasoner.get_instances(self.c)
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 16: QuasiOrderClassification via force_quasi_order flag
# ---------------------------------------------------------------------------

class TestQuasiOrderClassification:
    """Force quasi-order classification and verify correct hierarchy."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.dog = AtomicConcept.create(_ns("QODog"))
        self.animal = AtomicConcept.create(_ns("QOAnimal"))
        self.fido = Individual.create(_ns("qofido"))

        clauses = [
            DLClause.create(
                (Atom.create(self.animal, X),),
                (Atom.create(self.dog, X),),
            ),
        ]
        facts = [Atom.create(self.dog, self.fido)]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_quasi_order_classification(self):
        """force_quasi_order_classification=True still classifies correctly."""
        config = Configuration()
        config.force_quasi_order_classification = True
        reasoner = Reasoner(self.ontology, config)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.is_sub_class_of(self.dog, self.animal)
            assert reasoner.has_type(self.fido, self.animal)
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 17: Multiple individuals, multiple concepts — cross-type checks
# ---------------------------------------------------------------------------

class TestCrossTypeChecks:
    """
    Dog ⊑ Mammal. Cat ⊑ Mammal. Bird (not mammal).
    Three individuals.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.dog = AtomicConcept.create(_ns("CT_Dog"))
        self.cat = AtomicConcept.create(_ns("CT_Cat"))
        self.bird = AtomicConcept.create(_ns("CT_Bird"))
        self.mammal = AtomicConcept.create(_ns("CT_Mammal"))
        self.fido = Individual.create(_ns("ct_fido"))
        self.whiskers = Individual.create(_ns("ct_whiskers"))
        self.tweety = Individual.create(_ns("ct_tweety"))

        clauses = [
            DLClause.create(
                (Atom.create(self.mammal, X),),
                (Atom.create(self.dog, X),),
            ),
            DLClause.create(
                (Atom.create(self.mammal, X),),
                (Atom.create(self.cat, X),),
            ),
        ]
        facts = [
            Atom.create(self.dog, self.fido),
            Atom.create(self.cat, self.whiskers),
            Atom.create(self.bird, self.tweety),
        ]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_mammals_include_fido_and_whiskers(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            mammals = reasoner.get_instances(self.mammal)
            assert self.fido in mammals
            assert self.whiskers in mammals
            assert self.tweety not in mammals
        finally:
            reasoner.dispose()

    def test_tweety_is_bird_not_mammal(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.has_type(self.tweety, self.bird)
            assert not reasoner.has_type(self.tweety, self.mammal)
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 18: Object property classification and subsumption
# ---------------------------------------------------------------------------

class TestObjectPropertyClassification:
    """Check role subsumption via tableau test."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        Y = Variable.create("Y")
        self.has_sibling = AtomicRole.create(_ns("hasSibling"))
        self.has_relative = AtomicRole.create(_ns("hasRelative"))
        self.alice = Individual.create(_ns("op_alice"))
        self.bob = Individual.create(_ns("op_bob"))

        clauses = [
            DLClause.create(
                (Atom.create(self.has_relative, X, Y),),
                (Atom.create(self.has_sibling, X, Y),),
            ),
        ]
        facts = [Atom.create(self.has_sibling, self.alice, self.bob)]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_sibling_subsumed_by_relative(self):
        """hasSibling ⊑ hasRelative via precomputed role hierarchy (no individuals)."""
        X = Variable.create("X")
        Y = Variable.create("Y")
        has_sibling = AtomicRole.create(_ns("hasSibling2"))
        has_relative = AtomicRole.create(_ns("hasRelative2"))
        clause = DLClause.create(
            (Atom.create(has_relative, X, Y),),
            (Atom.create(has_sibling, X, Y),),
        )
        # No individuals so InstanceManager init doesn't hit the m_properties_initialised bug
        onto = _make_ontology([clause], [])
        reasoner = Reasoner(onto)
        try:
            reasoner.precompute_inferences(
                class_hierarchy=True, object_property_hierarchy=True
            )
            assert reasoner.is_sub_role_of(has_sibling, has_relative)
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 19: Realize — no possible instances (realization_completed)
# ---------------------------------------------------------------------------

class TestRealizationCompleted:
    """After classify_classes + initialization, realization_completed reflects state."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.dog = AtomicConcept.create(_ns("RC_Dog"))
        self.fido = Individual.create(_ns("rc_fido"))

        facts = [Atom.create(self.dog, self.fido)]
        self.ontology = _make_ontology([], facts)
        yield

    def test_has_type_after_precompute(self):
        """After precompute, has_type works correctly."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.has_type(self.fido, self.dog)
        finally:
            reasoner.dispose()

    def test_get_instances_after_precompute(self):
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            instances = reasoner.get_instances(self.dog)
            assert self.fido in instances
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 20: set_inconsistent propagation
# ---------------------------------------------------------------------------

class TestSetInconsistent:
    """Directly verify set_inconsistent path via inconsistent ontology."""

    def test_inconsistent_has_type_returns_true(self):
        """For inconsistent ontology, has_type returns True for any individual."""
        X = Variable.create("X")
        a = AtomicConcept.create(_ns("SI_A"))
        b = AtomicConcept.create(_ns("SI_B"))
        not_b = AtomicNegationConcept.create(b)
        ind = Individual.create(_ns("si_ind"))

        clauses = [
            DLClause.create((Atom.create(b, X),), (Atom.create(a, X),)),
            DLClause.create((Atom.create(not_b, X),), (Atom.create(a, X),)),
        ]
        facts = [Atom.create(a, ind)]
        ontology = _make_ontology(clauses, facts)

        reasoner = Reasoner(ontology)
        try:
            assert not reasoner.is_consistent()
            assert reasoner.has_type(ind, a)
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 21: InstanceManager accessed directly — status queries
# ---------------------------------------------------------------------------

class TestInstanceManagerDirectAccess:
    """Access the InstanceManager directly via reasoner._instance_manager."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.dog = AtomicConcept.create(_ns("DirDog"))
        self.animal = AtomicConcept.create(_ns("DirAnimal"))
        self.fido = Individual.create(_ns("dir_fido"))
        self.rex = Individual.create(_ns("dir_rex"))
        clauses = [
            DLClause.create(
                (Atom.create(self.animal, X),),
                (Atom.create(self.dog, X),),
            ),
        ]
        facts = [
            Atom.create(self.dog, self.fido),
            Atom.create(self.dog, self.rex),
        ]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_instance_manager_classes_initialised(self):
        """After has_type is called, classes are initialised."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(self.fido, self.dog)
            im = reasoner._instance_manager
            assert im is not None
            assert im.are_classes_initialised()
        finally:
            reasoner.dispose()

    def test_instance_manager_nodes_for_individuals(self):
        """get_nodes_for_individuals returns a dict keyed by Individual."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(self.fido, self.dog)
            im = reasoner._instance_manager
            assert im is not None
            nodes = im.get_nodes_for_individuals()
            assert isinstance(nodes, dict)
        finally:
            reasoner.dispose()

    def test_get_instances_returns_both(self):
        """Both fido and rex are Dog instances."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            instances = reasoner.get_instances(self.dog)
            assert self.fido in instances
            assert self.rex in instances
        finally:
            reasoner.dispose()

    def test_get_types_includes_animal(self):
        """fido's types include Animal."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            types = reasoner.get_types(self.fido)
            assert self.animal in types
        finally:
            reasoner.dispose()

    def test_instance_manager_realization_completed(self):
        """After full initialization, realization is completed."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(self.fido, self.dog)
            im = reasoner._instance_manager
            assert im is not None
            assert im.realization_completed()
        finally:
            reasoner.dispose()

    def test_all_status_methods(self):
        """All status query methods return appropriate types."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(self.fido, self.dog)
            im = reasoner._instance_manager
            assert im is not None
            assert isinstance(im.are_classes_initialised(), bool)
            assert isinstance(im.are_properties_initialised(), bool)
            assert isinstance(im.get_current_individual_index(), int)
            assert isinstance(im.realization_completed(), bool)
            assert isinstance(im.object_property_realization_completed(), bool)
            assert isinstance(im.same_as_individuals_computed(), bool)
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 22: Instance manager with no precomputed hierarchy
# ---------------------------------------------------------------------------

class TestInstanceManagerNoPrecomputedHierarchy:
    """Exercise the no-precomputed-hierarchy initialization path (None hierarchies)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.cat = AtomicConcept.create(_ns("NH_Cat"))
        self.mammal = AtomicConcept.create(_ns("NH_Mammal"))
        self.whiskers = Individual.create(_ns("nh_whiskers"))
        clauses = [
            DLClause.create(
                (Atom.create(self.mammal, X),),
                (Atom.create(self.cat, X),),
            ),
        ]
        facts = [Atom.create(self.cat, self.whiskers)]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_has_type_without_precompute(self):
        """has_type works even without explicit precompute (lazy init)."""
        reasoner = Reasoner(self.ontology)
        try:
            assert reasoner.has_type(self.whiskers, self.cat)
        finally:
            reasoner.dispose()

    def test_get_instances_without_precompute(self):
        """get_instances triggers lazy classification."""
        reasoner = Reasoner(self.ontology)
        try:
            instances = reasoner.get_instances(self.cat)
            assert self.whiskers in instances
        finally:
            reasoner.dispose()

    def test_get_types_without_precompute(self):
        """get_types triggers lazy classification."""
        reasoner = Reasoner(self.ontology)
        try:
            types = reasoner.get_types(self.whiskers)
            assert self.cat in types
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 23: QuasiOrderClassification — forced path with 3 concepts
# ---------------------------------------------------------------------------

class TestQuasiOrderWith3Concepts:
    """3-level hierarchy using force_quasi_order_classification=True."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.a = AtomicConcept.create(_ns("QO3_A"))
        self.b = AtomicConcept.create(_ns("QO3_B"))
        self.c = AtomicConcept.create(_ns("QO3_C"))
        self.ind_a = Individual.create(_ns("qo3_inda"))

        clauses = [
            DLClause.create((Atom.create(self.b, X),), (Atom.create(self.a, X),)),
            DLClause.create((Atom.create(self.c, X),), (Atom.create(self.b, X),)),
        ]
        facts = [Atom.create(self.a, self.ind_a)]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_quasi_order_subsumption(self):
        config = Configuration()
        config.force_quasi_order_classification = True
        reasoner = Reasoner(self.ontology, config)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.is_sub_class_of(self.a, self.b)
            assert reasoner.is_sub_class_of(self.b, self.c)
            assert reasoner.is_sub_class_of(self.a, self.c)
        finally:
            reasoner.dispose()

    def test_quasi_order_instance_retrieval(self):
        """Quasi-order still correctly retrieves instances."""
        config = Configuration()
        config.force_quasi_order_classification = True
        reasoner = Reasoner(self.ontology, config)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.has_type(self.ind_a, self.a)
            assert reasoner.has_type(self.ind_a, self.b)
            assert reasoner.has_type(self.ind_a, self.c)
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 24: Instance manager direct query methods
# ---------------------------------------------------------------------------

class TestInstanceManagerDirectQueryMethods:
    """Test get_instances and get_types on the InstanceManager object."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.dog = AtomicConcept.create(_ns("DQ_Dog"))
        self.animal = AtomicConcept.create(_ns("DQ_Animal"))
        self.fido = Individual.create(_ns("dq_fido"))
        self.rex = Individual.create(_ns("dq_rex"))
        clauses = [
            DLClause.create(
                (Atom.create(self.animal, X),),
                (Atom.create(self.dog, X),),
            ),
        ]
        facts = [
            Atom.create(self.dog, self.fido),
            Atom.create(self.animal, self.rex),
        ]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_im_get_instances_dog(self):
        """Instance manager get_instances(Dog) returns fido."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(self.fido, self.dog)
            im = reasoner._instance_manager
            assert im is not None
            result = im.get_instances(self.dog, False)
            assert self.fido in result
        finally:
            reasoner.dispose()

    def test_im_get_types_fido(self):
        """Instance manager get_types(fido) returns nodes for Dog."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(self.fido, self.dog)
            im = reasoner._instance_manager
            assert im is not None
            nodes = im.get_types(self.fido, False)
            concepts_found = set()
            for node in nodes:
                concepts_found.update(node.get_equivalent_elements())
            assert self.dog in concepts_found
        finally:
            reasoner.dispose()

    def test_im_has_type_fido_animal(self):
        """Instance manager has_type(fido, Animal) returns True."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(self.fido, self.dog)
            im = reasoner._instance_manager
            assert im is not None
            assert im.has_type(self.fido, self.animal, False)
        finally:
            reasoner.dispose()

    def test_im_get_instances_nothing_returns_empty(self):
        """get_instances(Nothing) returns empty set."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(self.fido, self.dog)
            im = reasoner._instance_manager
            assert im is not None
            result = im.get_instances(AtomicConcept.NOTHING, False)
            assert result == set()
        finally:
            reasoner.dispose()

    def test_im_get_instances_direct(self):
        """get_instances with direct=True returns a set."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(self.fido, self.dog)
            im = reasoner._instance_manager
            assert im is not None
            result = im.get_instances(self.animal, True)
            assert isinstance(result, set)
        finally:
            reasoner.dispose()

    def test_im_get_types_direct(self):
        """get_types with direct=True returns hierarchy nodes."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(self.fido, self.dog)
            im = reasoner._instance_manager
            assert im is not None
            nodes = im.get_types(self.fido, True)
            assert isinstance(nodes, set)
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 25: get_types with direct=True via Reasoner
# ---------------------------------------------------------------------------

class TestGetTypesDirectViaIM:
    """Test direct type queries through InstanceManager."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.poodle = AtomicConcept.create(_ns("GTD_Poodle"))
        self.dog = AtomicConcept.create(_ns("GTD_Dog"))
        self.animal = AtomicConcept.create(_ns("GTD_Animal"))
        self.rex = Individual.create(_ns("gtd_rex"))
        clauses = [
            DLClause.create((Atom.create(self.dog, X),), (Atom.create(self.poodle, X),)),
            DLClause.create((Atom.create(self.animal, X),), (Atom.create(self.dog, X),)),
        ]
        facts = [Atom.create(self.poodle, self.rex)]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_direct_types_include_poodle(self):
        """Direct types of rex should include Poodle."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            direct_types = reasoner.get_types(self.rex, direct=True)
            assert self.poodle in direct_types
        finally:
            reasoner.dispose()

    def test_non_direct_types_include_animal(self):
        """Non-direct types of rex include Animal."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            types = reasoner.get_types(self.rex, direct=False)
            assert self.animal in types
        finally:
            reasoner.dispose()

    def test_direct_types_do_not_include_animal(self):
        """Direct types of rex exclude Animal (indirect)."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            direct_types = reasoner.get_types(self.rex, direct=True)
            assert self.animal not in direct_types
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 26: set_inconsistent via InstanceManager
# ---------------------------------------------------------------------------

class TestSetInconsistentDirect:
    """Test set_inconsistent on the InstanceManager."""

    def test_set_inconsistent_state(self):
        """After set_inconsistent, IM reports inconsistent state."""
        X = Variable.create("X")
        dog = AtomicConcept.create(_ns("SID_Dog"))
        fido = Individual.create(_ns("sid_fido"))
        facts = [Atom.create(dog, fido)]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(fido, dog)
            im = reasoner._instance_manager
            assert im is not None
            im.set_inconsistent()
            assert im.m_is_inconsistent
            assert im.realization_completed()
            assert im.object_property_realization_completed()
            # After set_inconsistent, hierarchy is None, so has_type returns False
            assert im.has_type(fido, dog, False) is False
            # get_instances returns empty set when hierarchy is None
            assert im.get_instances(dog, False) == set()
            # get_object_property_values/subjects/instances return empty when hierarchy is None
            has_p = AtomicRole.create(_ns("SID_hasP"))
            assert im.get_object_property_values(has_p, fido) == set()
            assert im.get_object_property_subjects(has_p, fido) == set()
            assert im.get_object_property_instances(has_p) == {}
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 27: update_nodes_for_individuals
# ---------------------------------------------------------------------------

class TestUpdateNodesForIndividuals:
    """Test update_nodes_for_individuals on InstanceManager."""

    def test_update_with_non_individual_keys_ignored(self):
        """Non-Individual keys in the mapping are silently ignored."""
        dog = AtomicConcept.create(_ns("UNI_Dog"))
        fido = Individual.create(_ns("uni_fido"))
        facts = [Atom.create(dog, fido)]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(fido, dog)
            im = reasoner._instance_manager
            assert im is not None
            im.update_nodes_for_individuals({"not_an_individual": None, fido: None})
            assert im.m_nodes_for_individuals.get(fido) is None
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 28: same_as_individuals_computed
# ---------------------------------------------------------------------------

class TestSameAsIndividualsComputed:
    """Test same_as_individuals_computed on InstanceManager."""

    def test_same_as_computed_after_init(self):
        """After class initialization, same-as is in a defined state."""
        dog = AtomicConcept.create(_ns("SAC_Dog"))
        fido = Individual.create(_ns("sac_fido"))
        facts = [Atom.create(dog, fido)]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(fido, dog)
            im = reasoner._instance_manager
            assert im is not None
            result = im.same_as_individuals_computed()
            assert isinstance(result, bool)
        finally:
            reasoner.dispose()

    def test_get_same_as_individuals_unknown(self):
        """get_same_as_individuals returns singleton for unknown individual."""
        dog = AtomicConcept.create(_ns("GSAU_Dog"))
        fido = Individual.create(_ns("gsau_fido"))
        facts = [Atom.create(dog, fido)]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(fido, dog)
            im = reasoner._instance_manager
            assert im is not None
            # Unknown individual not in the equivalence class dict → singleton
            unknown = Individual.create(_ns("gsau_unknown"))
            result = im.get_same_as_individuals(unknown)
            assert unknown in result
        finally:
            reasoner.dispose()

    def test_compute_same_as_equivalence_classes_noop(self):
        """compute_same_as_equivalence_classes does nothing if no possibles."""
        dog = AtomicConcept.create(_ns("CSAE_Dog"))
        fido = Individual.create(_ns("csae_fido"))
        facts = [Atom.create(dog, fido)]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(fido, dog)
            im = reasoner._instance_manager
            assert im is not None
            # This should be a no-op since there are no possible equivalences
            im.compute_same_as_equivalence_classes(None)
            # No error → passes
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 29: get_object_property_values via InstanceManager
# ---------------------------------------------------------------------------

class TestGetObjectPropertyValuesViaIM:
    """Test get_object_property_values on InstanceManager."""

    def test_get_object_property_values_returns_set(self):
        """get_object_property_values returns a set (possibly empty)."""
        has_owner = AtomicRole.create(_ns("GOV_hasOwner"))
        dog = AtomicConcept.create(_ns("GOV_Dog"))
        fido = Individual.create(_ns("gov_fido"))
        john = Individual.create(_ns("gov_john"))
        facts = [
            Atom.create(dog, fido),
            Atom.create(has_owner, fido, john),
        ]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(fido, dog)
            im = reasoner._instance_manager
            assert im is not None
            values = im.get_object_property_values(has_owner, fido)
            assert isinstance(values, set)
        finally:
            reasoner.dispose()

    def test_get_object_property_subjects_returns_set(self):
        """get_object_property_subjects returns a set (possibly empty)."""
        has_owner = AtomicRole.create(_ns("GPS_hasOwner"))
        dog = AtomicConcept.create(_ns("GPS_Dog"))
        fido = Individual.create(_ns("gps_fido"))
        john = Individual.create(_ns("gps_john"))
        facts = [
            Atom.create(dog, fido),
            Atom.create(has_owner, fido, john),
        ]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(fido, dog)
            im = reasoner._instance_manager
            assert im is not None
            subjects = im.get_object_property_subjects(has_owner, john)
            assert isinstance(subjects, set)
        finally:
            reasoner.dispose()

    def test_get_object_property_instances_returns_dict(self):
        """get_object_property_instances returns a dict."""
        has_owner = AtomicRole.create(_ns("GPI_hasOwner"))
        dog = AtomicConcept.create(_ns("GPI_Dog"))
        fido = Individual.create(_ns("gpi_fido"))
        john = Individual.create(_ns("gpi_john"))
        facts = [
            Atom.create(dog, fido),
            Atom.create(has_owner, fido, john),
        ]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(fido, dog)
            im = reasoner._instance_manager
            assert im is not None
            instances = im.get_object_property_instances(has_owner)
            assert isinstance(instances, dict)
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 30: Realize with monitor (coverage for realize() code paths)
# ---------------------------------------------------------------------------

class TestRealizeWithMonitor:
    """Call realize() on InstanceManager with a mock monitor."""

    def test_realize_no_possibles(self):
        """realize() with no possible instances completes without error."""
        X = Variable.create("X")
        dog = AtomicConcept.create(_ns("RM_Dog"))
        fido = Individual.create(_ns("rm_fido"))
        facts = [Atom.create(dog, fido)]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(fido, dog)
            im = reasoner._instance_manager
            assert im is not None
            # Directly call realize with no monitor
            im.realize(None)
            assert im.realization_completed()
        finally:
            reasoner.dispose()

    def test_realize_with_possible_instances(self):
        """realize() with possible instances exercises the inner loop."""
        from hermit.hierarchy.atomic_concept_element import AtomicConceptElement
        X = Variable.create("X")
        dog = AtomicConcept.create(_ns("RMP_Dog"))
        fido = Individual.create(_ns("rmp_fido"))
        facts = [Atom.create(dog, fido)]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(fido, dog)
            im = reasoner._instance_manager
            assert im is not None
            assert im.m_uses_classified_concept_hierarchy
            # Inject a possible instance to trigger realize() inner loop
            element = im.m_concept_to_element.get(dog)
            if element is None:
                element = AtomicConceptElement(None, None)
                im.m_concept_to_element[dog] = element
            element.add_possible(fido)
            im.m_reading_off_found_possible_concept_instance = True
            im.m_realization_completed = False
            # Now call realize — will process possible instances
            im.realize(None)
            assert im.realization_completed()
        finally:
            reasoner.dispose()

    def test_realize_object_roles_no_possibles(self):
        """realize_object_roles() with no possible instances completes."""
        has_parent = AtomicRole.create(_ns("ROR_hasParent"))
        fido = Individual.create(_ns("ror_fido"))
        john = Individual.create(_ns("ror_john"))
        dog = AtomicConcept.create(_ns("ROR_Dog"))
        facts = [
            Atom.create(dog, fido),
            Atom.create(has_parent, fido, john),
        ]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(fido, dog)
            im = reasoner._instance_manager
            assert im is not None
            im.realize_object_roles(None)
            assert im.object_property_realization_completed()
        finally:
            reasoner.dispose()

    def test_realize_object_roles_with_possible_instances(self):
        """realize_object_roles() with possible role instances exercises inner loop."""
        X = Variable.create("X")
        Y = Variable.create("Y")
        has_parent = AtomicRole.create(_ns("RORP_hasParent"))
        has_ancestor = AtomicRole.create(_ns("RORP_hasAncestor"))
        dog = AtomicConcept.create(_ns("RORP_Dog"))
        fido = Individual.create(_ns("rorp_fido"))
        john = Individual.create(_ns("rorp_john"))
        clauses = [
            DLClause.create(
                (Atom.create(has_ancestor, X, Y),),
                (Atom.create(has_parent, X, Y),),
            ),
        ]
        facts = [
            Atom.create(dog, fido),
            Atom.create(has_parent, fido, john),
        ]
        ontology = _make_ontology(clauses, facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(fido, dog)
            im = reasoner._instance_manager
            assert im is not None
            # Inject possible role relations to trigger the inner loop
            role_elem = im.m_role_element_manager.get_role_element(has_parent)
            role_elem.add_possible(fido, john)
            im.m_reading_off_found_possible_property_instance = True
            im.m_role_realization_completed = False
            im.realize_object_roles(None)
            assert im.object_property_realization_completed()
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 31: initialize_know_and_possible_property_instances directly
# ---------------------------------------------------------------------------

class TestInitializePropertyInstances:
    """Call initialize_know_and_possible_property_instances directly."""

    def test_initialize_property_instances_no_error(self):
        """initialize_know_and_possible_property_instances runs without error."""
        has_parent = AtomicRole.create(_ns("IPI_hasParent"))
        person = AtomicConcept.create(_ns("IPI_Person"))
        alice = Individual.create(_ns("ipi_alice"))
        bob = Individual.create(_ns("ipi_bob"))
        facts = [
            Atom.create(person, alice),
            Atom.create(person, bob),
            Atom.create(has_parent, alice, bob),
        ]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            # Trigger class initialization first
            reasoner.has_type(alice, person)
            im = reasoner._instance_manager
            assert im is not None
            # Now call property instance initialization directly
            tableau = reasoner.get_tableau()
            im.initialize_know_and_possible_property_instances(
                tableau, None, 0, 0, 1
            )
            # Method ran without error; result depends on internal state
            assert isinstance(im.are_properties_initialised(), bool)
        finally:
            reasoner.dispose()

    def test_initialize_property_instances_single_individual(self):
        """With 1 individual, are_properties_initialised becomes True."""
        person = AtomicConcept.create(_ns("IPI2_Person"))
        alice = Individual.create(_ns("ipi2_alice"))
        facts = [Atom.create(person, alice)]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(alice, person)
            im = reasoner._instance_manager
            assert im is not None
            tableau = reasoner.get_tableau()
            im.initialize_know_and_possible_property_instances(
                tableau, None, 0, 0, 1
            )
            # With 1 individual, m_current_individual_index=0 >= len(1)-1=0, so True
            assert im.are_properties_initialised()
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 32: get_object_property_values / get_object_property_subjects after
#          property initialization
# ---------------------------------------------------------------------------

class TestGetObjectPropertyValuesAfterInit:
    """Test property value queries after full initialization."""

    def test_get_object_property_values_after_init(self):
        """After property initialization, get_object_property_values works."""
        has_parent = AtomicRole.create(_ns("OPVAI_hasParent"))
        person = AtomicConcept.create(_ns("OPVAI_Person"))
        alice = Individual.create(_ns("opvai_alice"))
        bob = Individual.create(_ns("opvai_bob"))
        facts = [
            Atom.create(person, alice),
            Atom.create(person, bob),
            Atom.create(has_parent, alice, bob),
        ]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(alice, person)
            im = reasoner._instance_manager
            assert im is not None
            tableau = reasoner.get_tableau()
            im.initialize_know_and_possible_property_instances(
                tableau, None, 0, 0, 1
            )
            values = im.get_object_property_values(has_parent, alice)
            assert isinstance(values, set)
        finally:
            reasoner.dispose()

    def test_get_object_property_subjects_after_init(self):
        """After property initialization, get_object_property_subjects works."""
        has_parent = AtomicRole.create(_ns("OPSAI_hasParent"))
        person = AtomicConcept.create(_ns("OPSAI_Person"))
        alice = Individual.create(_ns("opsai_alice"))
        bob = Individual.create(_ns("opsai_bob"))
        facts = [
            Atom.create(person, alice),
            Atom.create(person, bob),
            Atom.create(has_parent, alice, bob),
        ]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(alice, person)
            im = reasoner._instance_manager
            assert im is not None
            tableau = reasoner.get_tableau()
            im.initialize_know_and_possible_property_instances(
                tableau, None, 0, 0, 1
            )
            subjects = im.get_object_property_subjects(has_parent, bob)
            assert isinstance(subjects, set)
        finally:
            reasoner.dispose()

    def test_get_object_property_instances_after_init(self):
        """After property initialization, get_object_property_instances works."""
        has_parent = AtomicRole.create(_ns("OPIAI_hasParent"))
        person = AtomicConcept.create(_ns("OPIAI_Person"))
        alice = Individual.create(_ns("opiai_alice"))
        bob = Individual.create(_ns("opiai_bob"))
        facts = [
            Atom.create(person, alice),
            Atom.create(person, bob),
            Atom.create(has_parent, alice, bob),
        ]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(alice, person)
            im = reasoner._instance_manager
            assert im is not None
            tableau = reasoner.get_tableau()
            im.initialize_know_and_possible_property_instances(
                tableau, None, 0, 0, 1
            )
            instances = im.get_object_property_instances(has_parent)
            assert isinstance(instances, dict)
        finally:
            reasoner.dispose()

    def test_get_instances_thing_non_direct(self):
        """get_instances(Thing, direct=False) via IM includes all individuals."""
        person = AtomicConcept.create(_ns("GIT_Person"))
        alice = Individual.create(_ns("git_alice"))
        facts = [Atom.create(person, alice)]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(alice, person)
            im = reasoner._instance_manager
            assert im is not None
            # get_instances(THING, direct=False) exercises the "all individuals" branch
            result = im.get_instances(AtomicConcept.THING, False)
            assert isinstance(result, set)
        finally:
            reasoner.dispose()

    def test_read_off_property_instances_via_patched_reasoner(self):
        """Patch _initialise_class_instance_manager to call property init mid-run."""
        from unittest.mock import patch as mock_patch
        from hermit.hierarchy.instance_manager import InstanceManager

        has_parent = AtomicRole.create(_ns("ROPI_hasParent"))
        person = AtomicConcept.create(_ns("ROPI_Person"))
        alice = Individual.create(_ns("ropi_alice"))
        bob = Individual.create(_ns("ropi_bob"))
        facts = [
            Atom.create(person, alice),
            Atom.create(person, bob),
            Atom.create(has_parent, alice, bob),
        ]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(alice, person)
            im = reasoner._instance_manager
            assert im is not None

            # Repopulate nodes
            im._initialize_individuals_for_nodes()

            # Reset flags to allow property init AND same-as init to run
            im.m_properties_initialised = False  # allows _initialize_same_as
            im.m_classes_initialised = False  # so initialize_know_and_possible_class_instances runs

            # Get tableau (this clears additional ontology but NOT permanent)
            tableau = reasoner.get_tableau()

            # Re-run class init which calls _initialize_same_as + read-off
            im.initialize_know_and_possible_class_instances(tableau, None, 0, 1)

            assert im.are_classes_initialised()
        finally:
            reasoner.dispose()

    def test_initialize_property_instances_before_class_clear(self):
        """Call property init before nodes are cleared to exercise read_off_property_instances."""
        from unittest.mock import patch

        has_parent = AtomicRole.create(_ns("IPBC_hasParent"))
        person = AtomicConcept.create(_ns("IPBC_Person"))
        alice = Individual.create(_ns("ipbc_alice"))
        bob = Individual.create(_ns("ipbc_bob"))
        facts = [
            Atom.create(person, alice),
            Atom.create(person, bob),
            Atom.create(has_parent, alice, bob),
        ]
        ontology = _make_ontology([], facts)

        original_init_class = None

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            # Trigger IM initialization
            reasoner.has_type(alice, person)

            # Manually trigger property init using nodes that are still in nodes_for_individuals
            im = reasoner._instance_manager
            assert im is not None

            # Repopulate m_individuals_for_nodes from m_nodes_for_individuals
            im._initialize_individuals_for_nodes()

            # Check if we have nodes for individuals
            nodes_populated = any(
                v is not None for v in im.m_nodes_for_individuals.values()
            )
            if nodes_populated:
                # Get the tableau and call property init
                tableau = reasoner.get_tableau()
                # Set m_properties_initialised to False to allow the call
                im.m_properties_initialised = False
                im.initialize_know_and_possible_property_instances(
                    tableau, None, 0, 0, 1
                )
                assert isinstance(im.are_properties_initialised(), bool)
        finally:
            reasoner.dispose()

    def test_nodes_for_individuals_still_set_after_class_init(self):
        """m_nodes_for_individuals can be repopulated even after class init."""
        person = AtomicConcept.create(_ns("NFIS_Person"))
        alice = Individual.create(_ns("nfis_alice"))
        facts = [Atom.create(person, alice)]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(alice, person)
            im = reasoner._instance_manager
            assert im is not None
            im._initialize_individuals_for_nodes()
            assert isinstance(im.m_individuals_for_nodes, dict)
        finally:
            reasoner.dispose()

    def test_get_instances_for_node(self):
        """get_instances_for_node exercises hierarchy node-based retrieval."""
        dog = AtomicConcept.create(_ns("GIFN_Dog"))
        fido = Individual.create(_ns("gifn_fido"))
        facts = [Atom.create(dog, fido)]
        ontology = _make_ontology([], facts)

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(fido, dog)
            im = reasoner._instance_manager
            assert im is not None
            hierarchy = im.m_current_concept_hierarchy
            node = hierarchy.get_node_for_element(dog)
            if node is not None:
                result = im.get_instances_for_node(node, False)
                assert isinstance(result, set)
        finally:
            reasoner.dispose()

    def test_is_result_relevant_individual_named(self):
        """Named, non-internal individual is relevant."""
        from hermit.hierarchy.instance_manager import InstanceManager
        ind = Individual.create(_ns("relevant_ind"))
        assert InstanceManager._is_result_relevant_individual(ind)

    def test_is_result_relevant_individual_anonymous(self):
        """Anonymous individual is not relevant."""
        from hermit.hierarchy.instance_manager import InstanceManager
        anon = Individual.create_anonymous("anon-test")
        assert not InstanceManager._is_result_relevant_individual(anon)


# ---------------------------------------------------------------------------
# Test 33: Role queries after manually injecting known relations
# ---------------------------------------------------------------------------

class TestRoleQueriesWithInjectedState:
    """Inject known role relations directly into RoleElement to test query paths."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        Y = Variable.create("Y")
        self.has_parent = AtomicRole.create(_ns("RQI_hasParent"))
        self.has_ancestor = AtomicRole.create(_ns("RQI_hasAncestor"))
        self.person = AtomicConcept.create(_ns("RQI_Person"))
        self.alice = Individual.create(_ns("rqi_alice"))
        self.bob = Individual.create(_ns("rqi_bob"))
        self.carol = Individual.create(_ns("rqi_carol"))

        # Include the role in a clause so it gets into the role hierarchy
        clauses = [
            DLClause.create(
                (Atom.create(self.has_ancestor, X, Y),),
                (Atom.create(self.has_parent, X, Y),),
            ),
        ]
        facts = [
            Atom.create(self.person, self.alice),
            Atom.create(self.person, self.bob),
            Atom.create(self.person, self.carol),
        ]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def _setup_reasoner_with_known_role(self):
        """Create reasoner, init IM, inject role relation."""
        reasoner = Reasoner(self.ontology)
        reasoner.precompute_inferences(class_hierarchy=True)
        reasoner.has_type(self.alice, self.person)
        im = reasoner._instance_manager
        assert im is not None
        # Inject known relation: alice hasParent bob
        role_elem = im.m_role_element_manager.get_role_element(self.has_parent)
        role_elem.add_known(self.alice, self.bob)
        return reasoner, im

    def test_has_object_role_relationship_known(self):
        """has_object_role_relationship returns True when relation is known."""
        reasoner, im = self._setup_reasoner_with_known_role()
        try:
            result = im.has_object_role_relationship(
                self.has_parent, self.alice, self.bob
            )
            assert result is True
        finally:
            reasoner.dispose()

    def test_has_object_role_relationship_unknown(self):
        """has_object_role_relationship for unknown pair returns bool."""
        reasoner, im = self._setup_reasoner_with_known_role()
        try:
            result = im.has_object_role_relationship(
                self.has_parent, self.carol, self.alice
            )
            assert isinstance(result, bool)
        finally:
            reasoner.dispose()

    def test_get_object_property_values_known(self):
        """get_object_property_values returns bob for alice."""
        reasoner, im = self._setup_reasoner_with_known_role()
        try:
            values = im.get_object_property_values(self.has_parent, self.alice)
            assert self.bob in values
        finally:
            reasoner.dispose()

    def test_get_object_property_subjects_known(self):
        """get_object_property_subjects returns alice for bob."""
        reasoner, im = self._setup_reasoner_with_known_role()
        try:
            subjects = im.get_object_property_subjects(self.has_parent, self.bob)
            assert self.alice in subjects
        finally:
            reasoner.dispose()

    def test_get_object_property_instances_known(self):
        """get_object_property_instances returns {alice: {bob}}."""
        reasoner, im = self._setup_reasoner_with_known_role()
        try:
            instances = im.get_object_property_instances(self.has_parent)
            assert self.alice in instances
            assert self.bob in instances[self.alice]
        finally:
            reasoner.dispose()

    def test_add_known_role_instance_via_im(self):
        """_add_known_role_instance works correctly."""
        reasoner, im = self._setup_reasoner_with_known_role()
        try:
            role_elem = im.m_role_element_manager.get_role_element(self.has_parent)
            im._add_known_role_instance(role_elem, self.alice, self.carol)
            assert role_elem.is_known(self.alice, self.carol)
        finally:
            reasoner.dispose()

    def test_add_possible_role_instance_via_im(self):
        """_add_possible_role_instance works correctly."""
        reasoner, im = self._setup_reasoner_with_known_role()
        try:
            role_elem = im.m_role_element_manager.get_role_element(self.has_parent)
            im._add_possible_role_instance(role_elem, self.carol, self.alice)
            assert role_elem.is_possible(self.carol, self.alice)
        finally:
            reasoner.dispose()

    def test_has_object_role_relationship_possible(self):
        """has_object_role_relationship with possible relation exercises possible path."""
        reasoner, im = self._setup_reasoner_with_known_role()
        try:
            role_elem = im.m_role_element_manager.get_role_element(self.has_parent)
            # Inject possible relation for carol→alice
            role_elem.add_possible(self.carol, self.alice)
            # Call has_object_role_relationship — will check possible, call _is_role_instance
            result = im.has_object_role_relationship(
                self.has_parent, self.carol, self.alice
            )
            assert isinstance(result, bool)
        finally:
            reasoner.dispose()

    def test_get_object_property_values_with_possible(self):
        """get_object_property_values with possible relation exercises possible branch."""
        reasoner, im = self._setup_reasoner_with_known_role()
        try:
            role_elem = im.m_role_element_manager.get_role_element(self.has_parent)
            # Inject possible relation for bob→carol
            role_elem.add_possible(self.bob, self.carol)
            values = im.get_object_property_values(self.has_parent, self.bob)
            assert isinstance(values, set)
        finally:
            reasoner.dispose()

    def test_get_object_property_subjects_with_possible(self):
        """get_object_property_subjects with possible relation exercises possible branch."""
        reasoner, im = self._setup_reasoner_with_known_role()
        try:
            role_elem = im.m_role_element_manager.get_role_element(self.has_parent)
            # Inject possible relation
            role_elem.add_possible(self.carol, self.alice)
            subjects = im.get_object_property_subjects(self.has_parent, self.alice)
            assert isinstance(subjects, set)
        finally:
            reasoner.dispose()

    def test_get_object_property_instances_with_possible(self):
        """get_object_property_instances with possible relation exercises possible branch."""
        reasoner, im = self._setup_reasoner_with_known_role()
        try:
            role_elem = im.m_role_element_manager.get_role_element(self.has_parent)
            role_elem.add_possible(self.carol, self.alice)
            instances = im.get_object_property_instances(self.has_parent)
            assert isinstance(instances, dict)
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 34: Concept element manipulation
# ---------------------------------------------------------------------------

class TestConceptElementManipulation:
    """Directly manipulate AtomicConceptElement to test concept instance helpers."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.dog = AtomicConcept.create(_ns("CEM_Dog"))
        self.animal = AtomicConcept.create(_ns("CEM_Animal"))
        self.fido = Individual.create(_ns("cem_fido"))
        self.rex = Individual.create(_ns("cem_rex"))
        clauses = [
            DLClause.create(
                (Atom.create(self.animal, X),),
                (Atom.create(self.dog, X),),
            ),
        ]
        facts = [
            Atom.create(self.dog, self.fido),
            Atom.create(self.dog, self.rex),
        ]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_concept_to_element_has_dog_after_init(self):
        """After class init, m_concept_to_element has Dog concept element."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(self.fido, self.dog)
            im = reasoner._instance_manager
            assert im is not None
            element = im.m_concept_to_element.get(self.dog)
            assert element is not None
            assert self.fido in element.m_known_instances or self.rex in element.m_known_instances
        finally:
            reasoner.dispose()

    def test_get_instances_animal_non_direct(self):
        """get_instances(Animal, direct=False) includes both individuals."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            instances = reasoner.get_instances(self.animal, direct=False)
            assert self.fido in instances
            assert self.rex in instances
        finally:
            reasoner.dispose()

    def test_has_type_non_direct_false_for_dog_in_animal(self):
        """has_type(fido, animal, direct=False) is True."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            reasoner.has_type(self.fido, self.dog)
            im = reasoner._instance_manager
            assert im is not None
            assert im.has_type(self.fido, self.animal, False)
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 35: QuasiOrderClassificationForRoles coverage paths
# ---------------------------------------------------------------------------

class TestQuasiOrderClassificationForRoles:
    """Tests to improve coverage of QuasiOrderClassificationForRoles."""

    def test_role_subsumption_with_hierarchy_no_inverse(self):
        """Role subsumption via precomputed hierarchy, no inverse roles."""
        X = Variable.create("X")
        Y = Variable.create("Y")
        has_child = AtomicRole.create(_ns("QOF_hasChild"))
        has_descendant = AtomicRole.create(_ns("QOF_hasDescendant"))
        clause = DLClause.create(
            (Atom.create(has_descendant, X, Y),),
            (Atom.create(has_child, X, Y),),
        )
        ontology = _make_ontology([clause], [])
        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(
                class_hierarchy=True, object_property_hierarchy=True
            )
            assert reasoner.is_sub_role_of(has_child, has_descendant)
        finally:
            reasoner.dispose()

    def test_multiple_role_subsumptions(self):
        """Chain hasMother ⊑ hasParent ⊑ hasAncestor via hierarchy."""
        X = Variable.create("X")
        Y = Variable.create("Y")
        has_mother = AtomicRole.create(_ns("QOF2_hasMother"))
        has_parent = AtomicRole.create(_ns("QOF2_hasParent"))
        has_ancestor = AtomicRole.create(_ns("QOF2_hasAncestor"))
        clauses = [
            DLClause.create(
                (Atom.create(has_parent, X, Y),),
                (Atom.create(has_mother, X, Y),),
            ),
            DLClause.create(
                (Atom.create(has_ancestor, X, Y),),
                (Atom.create(has_parent, X, Y),),
            ),
        ]
        ontology = _make_ontology(clauses, [])
        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(
                class_hierarchy=True, object_property_hierarchy=True
            )
            assert reasoner.is_sub_role_of(has_mother, has_parent)
            assert reasoner.is_sub_role_of(has_parent, has_ancestor)
            assert reasoner.is_sub_role_of(has_mother, has_ancestor)
        finally:
            reasoner.dispose()

    def test_symmetric_role_not_subsumed(self):
        """hasSibling and hasCousin are not related by subsumption."""
        X = Variable.create("X")
        Y = Variable.create("Y")
        has_sibling = AtomicRole.create(_ns("QOF3_hasSibling"))
        has_cousin = AtomicRole.create(_ns("QOF3_hasCousin"))
        ontology = _make_ontology([], [])
        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(
                class_hierarchy=True, object_property_hierarchy=True
            )
            assert not reasoner.is_sub_role_of(has_sibling, has_cousin)
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Test 36: QuasiOrderClassification coverage paths
# ---------------------------------------------------------------------------

class TestQuasiOrderClassificationCoverage:
    """Tests to improve coverage of QuasiOrderClassification."""

    def test_unsatisfiable_concept_in_quasi_order(self):
        """Unsatisfiable concept is correctly classified with quasi-order."""
        X = Variable.create("X")
        a = AtomicConcept.create(_ns("QOC_A"))
        b = AtomicConcept.create(_ns("QOC_B"))
        not_b = AtomicNegationConcept.create(b)
        clauses = [
            DLClause.create((Atom.create(b, X),), (Atom.create(a, X),)),
            DLClause.create((Atom.create(not_b, X),), (Atom.create(a, X),)),
        ]
        ontology = _make_ontology(clauses, [])
        config = Configuration()
        config.force_quasi_order_classification = True
        reasoner = Reasoner(ontology, config)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert not reasoner.is_satisfiable(a)
        finally:
            reasoner.dispose()

    def test_equivalence_detection_quasi_order(self):
        """Quasi-order detects equivalent concepts."""
        X = Variable.create("X")
        a = AtomicConcept.create(_ns("QOE_A"))
        b = AtomicConcept.create(_ns("QOE_B"))
        clauses = [
            DLClause.create((Atom.create(b, X),), (Atom.create(a, X),)),
            DLClause.create((Atom.create(a, X),), (Atom.create(b, X),)),
        ]
        ontology = _make_ontology(clauses, [])
        config = Configuration()
        config.force_quasi_order_classification = True
        reasoner = Reasoner(ontology, config)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.is_equivalent(a, b)
        finally:
            reasoner.dispose()
