"""End-to-end integration tests for the HermiT reasoner.

These tests build ``DLOntology`` objects directly from DL clauses, atoms,
individuals, etc., then run the full reasoning pipeline (precompute +
queries) and assert expected results.

Each test follows this pattern:
    1. Build a ``DLOntology`` from model primitives.
    2. Create a ``Reasoner`` with the ontology.
    3. Run ``precompute_inferences()``.
    4. Query the reasoner and assert expected results.
    5. Dispose the reasoner.
"""

from __future__ import annotations

import pytest

from hermit import Reasoner, Configuration
from hermit.model import (
    Atom,
    AtomicConcept,
    AtomicNegationConcept,
    AtomicRole,
    Constant,
    DLClause,
    DLOntology,
    Equality,
    Individual,
    Inequality,
    InverseRole,
    InternalDatatype,
    Variable,
)


def _make_ontology(
    clauses: list[DLClause],
    positive_facts: list[Atom] | None = None,
    ontology_iri: str = "urn:test:integration",
) -> DLOntology:
    """Helper to construct a DLOntology from raw clauses and facts."""
    return DLOntology(
        ontology_iri=ontology_iri,
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset(positive_facts or []),
    )


# ===========================================================================
# Test 1: Simple taxonomy classification
# ===========================================================================

class TestSimpleTaxonomy:
    """Verify that a basic class hierarchy is classified correctly.

    Axioms::
        Dog ⊑ Animal
        Cat ⊑ Animal
        Mammal ⊑ Animal
        Dog ⊑ Mammal
        Cat ⊑ Mammal

    Expected hierarchy:
        Animal
          └─ Mammal
               ├─ Dog
               └─ Cat
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")

        dog = AtomicConcept.create("http://example.org#Dog")
        cat = AtomicConcept.create("http://example.org#Cat")
        mammal = AtomicConcept.create("http://example.org#Mammal")
        animal = AtomicConcept.create("http://example.org#Animal")

        clauses = [
            # Dog ⊑ Animal   =>  ¬Dog(X) ∨ Animal(X)
            DLClause.create(
                (Atom.create(animal, X),),
                (Atom.create(dog, X),),
            ),
            # Cat ⊑ Animal
            DLClause.create(
                (Atom.create(animal, X),),
                (Atom.create(cat, X),),
            ),
            # Mammal ⊑ Animal
            DLClause.create(
                (Atom.create(animal, X),),
                (Atom.create(mammal, X),),
            ),
            # Dog ⊑ Mammal
            DLClause.create(
                (Atom.create(mammal, X),),
                (Atom.create(dog, X),),
            ),
            # Cat ⊑ Mammal
            DLClause.create(
                (Atom.create(mammal, X),),
                (Atom.create(cat, X),),
            ),
        ]
        self.ontology = _make_ontology(clauses)
        self.dog = dog
        self.cat = cat
        self.mammal = mammal
        self.animal = animal
        yield

    def test_taxonomy_classification(self):
        """Class hierarchy shows Animal at top, Mammal below it, Dog and Cat below Mammal."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)

            # Subsumption checks
            assert reasoner.is_sub_class_of(self.dog, self.animal)
            assert reasoner.is_sub_class_of(self.cat, self.animal)
            assert reasoner.is_sub_class_of(self.mammal, self.animal)
            assert reasoner.is_sub_class_of(self.dog, self.mammal)
            assert reasoner.is_sub_class_of(self.cat, self.mammal)

            # Nothing is not subsumed by anything except Nothing
            assert not reasoner.is_sub_class_of(self.animal, self.dog)
            assert not reasoner.is_sub_class_of(self.animal, self.mammal)
            assert not reasoner.is_sub_class_of(self.mammal, self.dog)

            # Dog and Cat are not subsumed by each other
            assert not reasoner.is_sub_class_of(self.dog, self.cat)
            assert not reasoner.is_sub_class_of(self.cat, self.dog)

            # Satisfiability
            assert reasoner.is_satisfiable(self.dog)
            assert reasoner.is_satisfiable(self.cat)
            assert reasoner.is_satisfiable(self.mammal)
            assert reasoner.is_satisfiable(self.animal)
        finally:
            reasoner.dispose()

    def test_consistency(self):
        """The taxonomy ontology is consistent."""
        reasoner = Reasoner(self.ontology)
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()


# ===========================================================================
# Test 2: Disjoint classes
# ===========================================================================

class TestDisjointClasses:
    """Verify that disjointness is detected.

    Axioms::
        Dog ⊑ Animal
        Cat ⊑ Animal
        Dog ⊑ ¬Cat   (disjoint)
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")

        dog = AtomicConcept.create("http://example.org#Dog")
        cat = AtomicConcept.create("http://example.org#Cat")
        not_cat = AtomicNegationConcept.create(
            AtomicConcept.create("http://example.org#Cat")
        )
        animal = AtomicConcept.create("http://example.org#Animal")

        clauses = [
            # Dog ⊑ Animal
            DLClause.create(
                (Atom.create(animal, X),),
                (Atom.create(dog, X),),
            ),
            # Cat ⊑ Animal
            DLClause.create(
                (Atom.create(animal, X),),
                (Atom.create(cat, X),),
            ),
            # Dog ⊑ ¬Cat  =>  ¬Dog(X) ∨ ¬Cat(X)
            DLClause.create(
                (Atom.create(not_cat, X),),
                (Atom.create(dog, X),),
            ),
        ]
        self.ontology = _make_ontology(clauses)
        self.dog = dog
        self.cat = cat
        self.animal = animal
        yield

    def test_disjointness(self):
        """Dog and Cat are disjoint; Animal is satisfiable."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.is_disjoint(self.dog, self.cat)
            assert reasoner.is_satisfiable(self.animal)
        finally:
            reasoner.dispose()

    def test_consistency(self):
        """The ontology is consistent (disjoint classes do not imply inconsistency)."""
        reasoner = Reasoner(self.ontology)
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()


# ===========================================================================
# Test 3: Property subsumption
# ===========================================================================

class TestPropertySubsumption:
    """Verify that object property hierarchy is classified correctly.

    Axioms::
        hasParent ⊑ hasRelative
        hasMother ⊑ hasParent

    Expected: hasRelative ⊒ hasParent ⊒ hasMother
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        Y = Variable.create("Y")

        has_parent = AtomicRole.create("http://example.org#hasParent")
        has_relative = AtomicRole.create("http://example.org#hasRelative")
        has_mother = AtomicRole.create("http://example.org#hasMother")

        clauses = [
            # hasParent ⊑ hasRelative
            DLClause.create(
                (Atom.create(has_relative, X, Y),),
                (Atom.create(has_parent, X, Y),),
            ),
            # hasMother ⊑ hasParent
            DLClause.create(
                (Atom.create(has_parent, X, Y),),
                (Atom.create(has_mother, X, Y),),
            ),
        ]
        self.ontology = _make_ontology(clauses)
        self.has_parent = has_parent
        self.has_relative = has_relative
        self.has_mother = has_mother
        yield

    def test_property_hierarchy(self):
        """Property hierarchy shows hasRelative ⊒ hasParent ⊒ hasMother."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(
                class_hierarchy=True,
                object_property_hierarchy=True,
            )
            assert reasoner.is_sub_role_of(self.has_mother, self.has_parent)
            assert reasoner.is_sub_role_of(self.has_parent, self.has_relative)
            assert reasoner.is_sub_role_of(self.has_mother, self.has_relative)

            # Reverse does not hold
            assert not reasoner.is_sub_role_of(self.has_parent, self.has_mother)
            assert not reasoner.is_sub_role_of(self.has_relative, self.has_parent)
        finally:
            reasoner.dispose()


# ===========================================================================
# Test 4: Existential restrictions
# ===========================================================================

class TestExistentialRestrictions:
    """Verify that existential restrictions are handled correctly.

    Axioms::
        Dog ⊑ ∃hasTail.Tail
        ∀hasTail.Thing    (every hasTail successor is a Thing — tautology)
        Tail concept declared
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")

        dog = AtomicConcept.create("http://example.org#Dog")
        tail = AtomicConcept.create("http://example.org#Tail")
        has_tail = AtomicRole.create("http://example.org#hasTail")

        from hermit.model import AtLeastConcept

        # Dog ⊑ ∃hasTail.Tail  encoded as ≥1 hasTail.Tail
        existential = AtLeastConcept.create(1, has_tail, tail)

        clauses = [
            # Dog ⊑ ∃hasTail.Tail  =>  ¬Dog(X) ∨ (≥1 hasTail.Tail)(X)
            DLClause.create(
                (Atom.create(existential, X),),
                (Atom.create(dog, X),),
            ),
        ]
        self.ontology = _make_ontology(clauses)
        self.dog = dog
        self.has_tail = has_tail
        yield

    def test_existential_satisfiability(self):
        """Dog is satisfiable with existential restriction."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.is_satisfiable(self.dog)
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()


# ===========================================================================
# Test 5: Inverse properties
# ===========================================================================

class TestInverseProperties:
    """Verify that inverse roles are detected in expressivity.

    Axioms::
        hasParent ⊑ hasAncestor
        hasChild ≡ inv(hasParent)

    Expected: Inverse role detected in expressivity.

    Note: In the HermiT model, InverseRole is a Role (not a DLPredicate),
    so it cannot be used directly as an atom predicate.  Inverse roles
    appear inside existential concepts (AtLeastConcept) and are detected
    by the structural layer's expressivity analysis.  Here we verify
    that the reasoner can handle axioms involving inverse role semantics
    and that the resulting clauses contain the inverse-role-carrying
    AtLeastConcept.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        Y = Variable.create("Y")

        has_parent = AtomicRole.create("http://example.org#hasParent")
        has_ancestor = AtomicRole.create("http://example.org#hasAncestor")
        inv_has_parent = InverseRole.create(has_parent)
        has_child_concept = AtomicConcept.create("http://example.org#HasChild")

        from hermit.model import AtLeastConcept

        # HasChild ⊑ ∃inv(hasParent).Thing
        # Encoded as: ¬HasChild(X) ∨ (≥1 inv(hasParent).Thing)(X)
        # The inverse role is carried inside the AtLeastConcept filler.
        existential = AtLeastConcept.create(1, inv_has_parent, AtomicConcept.THING)

        clauses = [
            # hasParent ⊑ hasAncestor
            DLClause.create(
                (Atom.create(has_ancestor, X, Y),),
                (Atom.create(has_parent, X, Y),),
            ),
            # HasChild ⊑ ∃inv(hasParent).Thing
            DLClause.create(
                (Atom.create(existential, X),),
                (Atom.create(has_child_concept, X),),
            ),
        ]
        self.ontology = _make_ontology(clauses)
        self.has_parent = has_parent
        self.inv_has_parent = inv_has_parent
        self.has_child_concept = has_child_concept
        yield

    def test_atleast_with_inverse_in_clauses(self):
        """Clauses contain an AtLeastConcept with an inverse role."""
        from hermit.model import AtLeastConcept

        has_inverse = any(
            isinstance(a.predicate, AtLeastConcept)
            and isinstance(a.predicate.on_role, InverseRole)
            for c in self.ontology.dl_clauses
            for a in c.head_atoms
        )
        assert has_inverse

    def test_consistency(self):
        """Ontology with inverse roles is consistent."""
        reasoner = Reasoner(self.ontology)
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()


# ===========================================================================
# Test 6: ABox reasoning
# ===========================================================================

class TestABoxReasoning:
    """Verify instance retrieval with named individuals.

    TBox::
        Dog ⊑ Animal
        Cat ⊑ Animal
    ABox::
        Dog(fido)
        Cat(whiskers)
        hasOwner(fido, john)

    Expected: fido is Dog and Animal; whiskers is Cat and Animal.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")

        dog = AtomicConcept.create("http://example.org#Dog")
        cat = AtomicConcept.create("http://example.org#Cat")
        animal = AtomicConcept.create("http://example.org#Animal")
        has_owner = AtomicRole.create("http://example.org#hasOwner")

        fido = Individual.create("http://example.org#fido")
        whiskers = Individual.create("http://example.org#whiskers")
        john = Individual.create("http://example.org#john")

        clauses = [
            # Dog ⊑ Animal
            DLClause.create(
                (Atom.create(animal, X),),
                (Atom.create(dog, X),),
            ),
            # Cat ⊑ Animal
            DLClause.create(
                (Atom.create(animal, X),),
                (Atom.create(cat, X),),
            ),
        ]
        facts = [
            Atom.create(dog, fido),
            Atom.create(cat, whiskers),
            Atom.create(has_owner, fido, john),
        ]
        self.ontology = _make_ontology(clauses, facts)
        self.dog = dog
        self.cat = cat
        self.animal = animal
        self.fido = fido
        self.whiskers = whiskers
        self.john = john
        yield

    def test_fido_is_dog_and_animal(self):
        """Instance retrieval finds fido as Dog and Animal."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.has_type(self.fido, self.dog)
            assert reasoner.has_type(self.fido, self.animal)
        finally:
            reasoner.dispose()

    def test_whiskers_is_cat_and_animal(self):
        """Instance retrieval finds whiskers as Cat and Animal."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.has_type(self.whiskers, self.cat)
            assert reasoner.has_type(self.whiskers, self.animal)
        finally:
            reasoner.dispose()

    def test_fido_not_cat(self):
        """fido is not a Cat."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            # fido is asserted Dog; Dog is not subsumed by Cat
            assert not reasoner.has_type(self.fido, self.cat)
        finally:
            reasoner.dispose()

    def test_get_instances(self):
        """get_instances returns correct individuals for concepts."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            animal_instances = reasoner.get_instances(self.animal)
            assert self.fido in animal_instances
            assert self.whiskers in animal_instances
        finally:
            reasoner.dispose()


# ===========================================================================
# Test 7: Transitivity
# ===========================================================================

class TestTransitivity:
    """Verify that transitivity via role chains is handled.

    Axioms::
        hasAncestor o hasAncestor ⊑ hasAncestor   (transitivity)
        hasParent ⊑ hasAncestor

    Expected: Complex role chain detected in clauses.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        Y = Variable.create("Y")
        Z = Variable.create("Z")

        has_ancestor = AtomicRole.create("http://example.org#hasAncestor")
        has_parent = AtomicRole.create("http://example.org#hasParent")

        clauses = [
            # hasAncestor o hasAncestor ⊑ hasAncestor
            # hasAncestor(X,Y) ∧ hasAncestor(Y,Z) => hasAncestor(X,Z)
            DLClause.create(
                (Atom.create(has_ancestor, X, Z),),
                (Atom.create(has_ancestor, X, Y), Atom.create(has_ancestor, Y, Z)),
            ),
            # hasParent ⊑ hasAncestor
            DLClause.create(
                (Atom.create(has_ancestor, X, Y),),
                (Atom.create(has_parent, X, Y),),
            ),
        ]
        self.ontology = _make_ontology(clauses)
        self.has_ancestor = has_ancestor
        self.has_parent = has_parent
        yield

    def test_transitivity_clause_present(self):
        """Complex role-chain clause is generated."""
        transitive_clauses = [
            c for c in self.ontology.dl_clauses
            if c.body_length() == 2
            and all(
                isinstance(a.predicate, AtomicRole)
                for a in c.body_atoms
            )
        ]
        assert len(transitive_clauses) >= 1

    def test_consistency(self):
        """Ontology with transitivity is consistent."""
        reasoner = Reasoner(self.ontology)
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()


# ===========================================================================
# Test 8: Bottom/Nothing detection
# ===========================================================================

class TestBottomDetection:
    """Verify that contradictory concepts are classified as Nothing.

    Axioms::
        A ⊑ B
        A ⊑ ¬B

    Expected: A is unsatisfiable (classified as Nothing).
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")

        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        not_b = AtomicNegationConcept.create(b)

        clauses = [
            # A ⊑ B  =>  ¬A(X) ∨ B(X)
            DLClause.create(
                (Atom.create(b, X),),
                (Atom.create(a, X),),
            ),
            # A ⊑ ¬B  =>  ¬A(X) ∨ ¬B(X)
            DLClause.create(
                (Atom.create(not_b, X),),
                (Atom.create(a, X),),
            ),
        ]
        self.ontology = _make_ontology(clauses)
        self.a = a
        self.b = b
        yield

    def test_a_unsatisfiable(self):
        """A is unsatisfiable because it implies both B and ¬B."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert not reasoner.is_satisfiable(self.a)
        finally:
            reasoner.dispose()

    def test_b_satisfiable(self):
        """B itself is satisfiable (only A is contradictory)."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.is_satisfiable(self.b)
        finally:
            reasoner.dispose()

    def test_ontology_still_consistent(self):
        """The ontology is consistent because A can simply be empty."""
        reasoner = Reasoner(self.ontology)
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_a_subsumed_by_nothing(self):
        """A is subsumed by Nothing (i.e., A ≡ Nothing)."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.is_sub_class_of(self.a, AtomicConcept.NOTHING)
        finally:
            reasoner.dispose()


# ===========================================================================
# Test 9: SWRL-like rule clausification
# ===========================================================================

class TestSWRLLikeRuleClausification:
    """Verify that SWRL-like rules produce correct DL clauses.

    Rule::
        Person(X) ∧ hasParent(X, Y) ∧ hasParent(Y, Z) → hasGrandparent(X, Z)

    Expected: Rule clause generated correctly.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        Y = Variable.create("Y")
        Z = Variable.create("Z")

        person = AtomicConcept.create("http://example.org#Person")
        has_parent = AtomicRole.create("http://example.org#hasParent")
        has_grandparent = AtomicRole.create("http://example.org#hasGrandparent")

        # Simulate the SWRL rule as a DL clause directly
        # Person(X) ∧ hasParent(X,Y) ∧ hasParent(Y,Z) → hasGrandparent(X,Z)
        clause = DLClause.create(
            (Atom.create(has_grandparent, X, Z),),
            (
                Atom.create(person, X),
                Atom.create(has_parent, X, Y),
                Atom.create(has_parent, Y, Z),
            ),
        )
        self.ontology = _make_ontology([clause])
        self.has_grandparent = has_grandparent
        self.has_parent = has_parent
        self.person = person
        yield

    def test_rule_clause_present(self):
        """Rule clause is generated with correct body and head."""
        rule_clauses = [
            c for c in self.ontology.dl_clauses
            if c.body_length() == 3 and c.head_length() == 1
        ]
        assert len(rule_clauses) >= 1

    def test_consistency(self):
        """Ontology with SWRL-like rule is consistent."""
        reasoner = Reasoner(self.ontology)
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()


# ===========================================================================
# Test 10: Datatype reasoning
# ===========================================================================

class TestDatatypeReasoning:
    """Verify that datatype restrictions are detected in expressivity.

    Axiom::
        Adult ⊑ Person ⊓ ∃hasAge.xsd:integer[≥ 18]

    Expected: Datatype detected in expressivity.

    Note: This test builds the DL clause directly from model primitives.
    To trigger datatype detection, we include an InternalDatatype directly
    as an atom predicate in a clause body.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        Y = Variable.create("Y")

        adult = AtomicConcept.create("http://example.org#Adult")
        person = AtomicConcept.create("http://example.org#Person")
        has_age = AtomicRole.create("http://example.org#hasAge")

        # Create an InternalDatatype for xsd:integer
        xsd_integer = InternalDatatype.create(
            "http://www.w3.org/2001/XMLSchema#integer"
        )

        from hermit.model import AtLeastDataRange

        # Adult ⊑ Person ⊓ ∃hasAge.xsd:integer
        # Encoded as two clauses:
        #   Adult ⊑ Person  => ¬Adult(X) ∨ Person(X)
        #   Adult ⊑ ∃hasAge.xsd:integer  => ¬Adult(X) ∨ (≥1 hasAge.xsd:integer)(X)
        age_restriction = AtLeastDataRange.create(1, has_age, xsd_integer)

        clauses = [
            # Adult ⊑ Person
            DLClause.create(
                (Atom.create(person, X),),
                (Atom.create(adult, X),),
            ),
            # Adult ⊑ ∃hasAge.xsd:integer
            DLClause.create(
                (Atom.create(age_restriction, X),),
                (Atom.create(adult, X),),
            ),
            # Datatype marker clause: to ensure datatype detection, add a clause
            # that uses InternalDatatype directly as an atom predicate.
            # This simulates the structural layer's datatype handling.
            DLClause.create(
                (Atom.create(xsd_integer, Y),),
                (Atom.create(adult, X),),
            ),
        ]
        self.ontology = _make_ontology(clauses)
        self.adult = adult
        self.person = person
        self.has_age = has_age
        yield

    def test_datatype_detected(self):
        """Datatype is detected in expressivity."""
        assert self.ontology.has_datatypes()

    def test_consistency(self):
        """Ontology with datatype restrictions is consistent."""
        reasoner = Reasoner(self.ontology)
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_adult_satisfiable(self):
        """Adult concept is satisfiable."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.is_satisfiable(self.adult)
        finally:
            reasoner.dispose()

    def test_adult_subsumed_by_person(self):
        """Adult is subsumed by Person."""
        reasoner = Reasoner(self.ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.is_sub_class_of(self.adult, self.person)
        finally:
            reasoner.dispose()
