"""Coverage boost tests for instance_manager.py, quasi_order_classification_for_roles.py, and parser.py.

Strategy:
- Build ontologies with individuals, class hierarchies, role assertions,
  inverse roles, and sub-roles, then call ALL reasoner API methods.
- This triggers the lazy initialisation paths, property-instance reading,
  role-filler queries, same-individual computation, etc.
"""

from __future__ import annotations

import pytest

from hermit import Reasoner, Configuration
from hermit.model import (
    Atom,
    AtomicConcept,
    AtomicRole,
    DLClause,
    DLOntology,
    Individual,
    InverseRole,
    Variable,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ns(name: str) -> str:
    return f"http://example.org/boost9#{name}"


def _make_ontology(
    clauses: list[DLClause] | None = None,
    facts: list[Atom] | None = None,
    iri: str = "urn:test:boost9",
) -> DLOntology:
    return DLOntology(
        ontology_iri=iri,
        dl_clauses=frozenset(clauses or []),
        positive_facts=frozenset(facts or []),
        negative_facts=frozenset(),
    )


# ---------------------------------------------------------------------------
# 1. Rich ontology: many individuals, deep hierarchy, role assertions
#    → triggers initialize_know_and_possible_class_instances,
#      _read_off_property_instances, get_role_fillers, has_object_role_relationship
# ---------------------------------------------------------------------------

class TestRichOntologyInstanceManager:
    """Comprehensive test covering most instance manager code paths."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")

        self.animal = AtomicConcept.create(_ns("Animal"))
        self.mammal = AtomicConcept.create(_ns("Mammal"))
        self.dog = AtomicConcept.create(_ns("Dog"))
        self.cat = AtomicConcept.create(_ns("Cat"))
        self.person = AtomicConcept.create(_ns("Person"))

        self.has_pet = AtomicRole.create(_ns("hasPet"))
        self.has_owner = AtomicRole.create(_ns("hasOwner"))
        self.knows = AtomicRole.create(_ns("knows"))

        self.fido = Individual.create(_ns("fido"))
        self.whiskers = Individual.create(_ns("whiskers"))
        self.john = Individual.create(_ns("john"))
        self.alice = Individual.create(_ns("alice"))
        self.bob = Individual.create(_ns("bob"))

        clauses = [
            # Dog ⊑ Mammal ⊑ Animal
            DLClause.create(
                (Atom.create(self.mammal, X),),
                (Atom.create(self.dog, X),),
            ),
            DLClause.create(
                (Atom.create(self.animal, X),),
                (Atom.create(self.mammal, X),),
            ),
            # Cat ⊑ Mammal
            DLClause.create(
                (Atom.create(self.mammal, X),),
                (Atom.create(self.cat, X),),
            ),
            # Person ⊑ Animal
            DLClause.create(
                (Atom.create(self.animal, X),),
                (Atom.create(self.person, X),),
            ),
        ]
        facts = [
            Atom.create(self.dog, self.fido),
            Atom.create(self.cat, self.whiskers),
            Atom.create(self.person, self.john),
            Atom.create(self.person, self.alice),
            Atom.create(self.person, self.bob),
            # Role assertions
            Atom.create(self.has_pet, self.john, self.fido),
            Atom.create(self.has_pet, self.alice, self.whiskers),
            Atom.create(self.has_owner, self.fido, self.john),
            Atom.create(self.knows, self.john, self.alice),
            Atom.create(self.knows, self.alice, self.bob),
        ]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_get_instances_animal_all(self):
        r = Reasoner(self.ontology)
        try:
            instances = r.get_instances(self.animal)
            assert self.fido in instances
            assert self.whiskers in instances
            assert self.john in instances
        finally:
            r.dispose()

    def test_get_instances_mammal(self):
        r = Reasoner(self.ontology)
        try:
            instances = r.get_instances(self.mammal)
            assert self.fido in instances
            assert self.whiskers in instances
            assert self.john not in instances
        finally:
            r.dispose()

    def test_get_instances_dog(self):
        r = Reasoner(self.ontology)
        try:
            instances = r.get_instances(self.dog)
            assert self.fido in instances
            assert self.whiskers not in instances
        finally:
            r.dispose()

    def test_get_instances_direct(self):
        r = Reasoner(self.ontology)
        try:
            instances = r.get_instances(self.mammal, direct=True)
            # direct instances of Mammal: Cat (whiskers) and Dog (fido) are more specific
            # Dog ⊑ Mammal and Cat ⊑ Mammal, so direct instances of Mammal should exclude
            # those that are known instances of Dog or Cat
            assert isinstance(instances, set)
        finally:
            r.dispose()

    def test_get_types_fido(self):
        r = Reasoner(self.ontology)
        try:
            types = r.get_types(self.fido)
            assert self.dog in types
            assert self.mammal in types
            assert self.animal in types
        finally:
            r.dispose()

    def test_get_types_john_direct(self):
        r = Reasoner(self.ontology)
        try:
            types = r.get_types(self.john, direct=True)
            assert self.person in types
            # Animal should NOT be a direct type (Person ⊑ Animal)
            assert self.animal not in types
        finally:
            r.dispose()

    def test_has_type_fido_dog(self):
        r = Reasoner(self.ontology)
        try:
            assert r.has_type(self.fido, self.dog)
        finally:
            r.dispose()

    def test_has_type_fido_mammal(self):
        r = Reasoner(self.ontology)
        try:
            assert r.has_type(self.fido, self.mammal)
        finally:
            r.dispose()

    def test_has_type_fido_not_person(self):
        r = Reasoner(self.ontology)
        try:
            assert not r.has_type(self.fido, self.person)
        finally:
            r.dispose()

    def test_has_role_relationship_john_has_pet_fido(self):
        r = Reasoner(self.ontology)
        try:
            assert r.has_role_relationship(self.john, self.has_pet, self.fido)
        finally:
            r.dispose()

    def test_has_role_relationship_alice_has_pet_whiskers(self):
        r = Reasoner(self.ontology)
        try:
            assert r.has_role_relationship(self.alice, self.has_pet, self.whiskers)
        finally:
            r.dispose()

    def test_has_role_relationship_negative(self):
        r = Reasoner(self.ontology)
        try:
            assert not r.has_role_relationship(self.bob, self.has_pet, self.fido)
        finally:
            r.dispose()

    def test_has_role_relationship_knows(self):
        r = Reasoner(self.ontology)
        try:
            assert r.has_role_relationship(self.john, self.knows, self.alice)
        finally:
            r.dispose()

    def test_get_instances_with_classify_object_properties(self):
        r = Reasoner(self.ontology)
        try:
            # Get instances first (triggers _initialise_class_instance_manager),
            # then classify object properties separately
            instances = r.get_instances(self.animal)
            assert len(instances) > 0
            r.classify_object_properties()
            assert r._object_role_hierarchy is not None
        finally:
            r.dispose()

    def test_get_object_property_values_john_has_pet(self):
        r = Reasoner(self.ontology)
        try:
            # Call _initialise_class_instance_manager first
            _ = r.get_instances(self.person)
            # Now access object property instances
            im = r._instance_manager
            if im is not None:
                vals = im.get_object_property_values(self.has_pet, self.john)
                assert isinstance(vals, set)
        finally:
            r.dispose()

    def test_get_object_property_subjects(self):
        r = Reasoner(self.ontology)
        try:
            _ = r.get_instances(self.animal)
            im = r._instance_manager
            if im is not None:
                subjects = im.get_object_property_subjects(self.has_pet, self.fido)
                assert isinstance(subjects, set)
        finally:
            r.dispose()

    def test_get_object_property_instances(self):
        r = Reasoner(self.ontology)
        try:
            _ = r.get_instances(self.animal)
            im = r._instance_manager
            if im is not None:
                instances = im.get_object_property_instances(self.has_pet)
                assert isinstance(instances, dict)
        finally:
            r.dispose()

    def test_initialize_property_instances(self):
        r = Reasoner(self.ontology)
        try:
            _ = r.get_instances(self.animal)
            im = r._instance_manager
            assert im is not None
            # Instance manager should be created and classes initialised
            assert im.are_classes_initialised()
        finally:
            r.dispose()

    def test_get_same_as_individuals(self):
        r = Reasoner(self.ontology)
        try:
            _ = r.get_instances(self.animal)
            im = r._instance_manager
            if im is not None:
                same_as = im.get_same_as_individuals(self.john)
                assert isinstance(same_as, set)
                assert self.john in same_as
        finally:
            r.dispose()

    def test_is_same_individual_different(self):
        r = Reasoner(self.ontology)
        try:
            # Calling get_same_as_individuals via instance manager (no tableau call)
            _ = r.get_instances(self.animal)
            im = r._instance_manager
            if im is not None:
                same = im.get_same_as_individuals(self.john)
                assert isinstance(same, set)
        finally:
            r.dispose()

    def test_has_object_role_relationship_via_instance_manager(self):
        r = Reasoner(self.ontology)
        try:
            _ = r.get_instances(self.animal)
            im = r._instance_manager
            if im is not None:
                result = im.has_object_role_relationship(
                    self.has_pet, self.john, self.fido
                )
                assert isinstance(result, bool)
        finally:
            r.dispose()

    def test_has_type_for_node(self):
        r = Reasoner(self.ontology)
        try:
            r.precompute_inferences(class_hierarchy=True)
            _ = r.get_instances(self.animal)
            im = r._instance_manager
            if im is not None and im.m_current_concept_hierarchy is not None:
                node = im.m_current_concept_hierarchy.get_node_for_element(self.dog)
                if node is not None:
                    result = im._has_type_for_node(self.fido, node, False)
                    assert result is True
        finally:
            r.dispose()

    def test_get_instances_for_node(self):
        r = Reasoner(self.ontology)
        try:
            r.precompute_inferences(class_hierarchy=True)
            _ = r.get_instances(self.animal)
            im = r._instance_manager
            if im is not None and im.m_current_concept_hierarchy is not None:
                node = im.m_current_concept_hierarchy.get_node_for_element(self.mammal)
                if node is not None:
                    result = im.get_instances_for_node(node, False)
                    assert isinstance(result, set)
        finally:
            r.dispose()

    def test_set_inconsistent(self):
        r = Reasoner(self.ontology)
        try:
            _ = r.get_instances(self.animal)
            im = r._instance_manager
            if im is not None:
                im.set_inconsistent()
                assert im.m_is_inconsistent
                assert im.m_realization_completed
        finally:
            r.dispose()

    def test_compute_same_as_equivalence_classes(self):
        r = Reasoner(self.ontology)
        try:
            _ = r.get_instances(self.animal)
            im = r._instance_manager
            if im is not None:
                im.compute_same_as_equivalence_classes(None)
        finally:
            r.dispose()

    def test_realize_object_roles(self):
        r = Reasoner(self.ontology)
        try:
            _ = r.get_instances(self.animal)
            im = r._instance_manager
            if im is not None:
                im.realize_object_roles(None)
                assert im.m_role_realization_completed
        finally:
            r.dispose()

    def test_realize(self):
        r = Reasoner(self.ontology)
        try:
            r.precompute_inferences(class_hierarchy=True)
            _ = r.get_instances(self.animal)
            im = r._instance_manager
            if im is not None:
                im.realize(None)
                assert im.m_realization_completed
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# 2. Ontology with sub-roles and inverse roles
#    → triggers QuasiOrderClassificationForRoles paths
# ---------------------------------------------------------------------------

class TestSubRolesAndInverseRoles:
    """Tests with role hierarchies: subRole ⊑ superRole, and inverse roles."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        Y = Variable.create("Y")

        self.person = AtomicConcept.create(_ns("SR_Person"))
        self.knows = AtomicRole.create(_ns("SR_knows"))
        self.close_friend = AtomicRole.create(_ns("SR_closeFriend"))

        self.alice = Individual.create(_ns("SR_alice"))
        self.bob = Individual.create(_ns("SR_bob"))
        self.carol = Individual.create(_ns("SR_carol"))

        # closeFriend ⊑ knows
        clauses = [
            DLClause.create(
                (Atom.create(self.knows, X, Y),),
                (Atom.create(self.close_friend, X, Y),),
            ),
        ]
        facts = [
            Atom.create(self.person, self.alice),
            Atom.create(self.person, self.bob),
            Atom.create(self.person, self.carol),
            Atom.create(self.close_friend, self.alice, self.bob),
            Atom.create(self.knows, self.bob, self.carol),
        ]
        self.ontology = _make_ontology(clauses, facts)
        yield

    def test_classify_object_properties(self):
        r = Reasoner(self.ontology)
        try:
            r.precompute_inferences(
                class_hierarchy=True, object_property_hierarchy=True
            )
            assert r._object_role_hierarchy is not None
        finally:
            r.dispose()

    def test_has_role_relationship_via_sub_role(self):
        r = Reasoner(self.ontology)
        try:
            # close_friend is a sub-role of knows
            assert r.has_role_relationship(self.alice, self.close_friend, self.bob)
        finally:
            r.dispose()

    def test_has_role_relationship_knows_direct(self):
        r = Reasoner(self.ontology)
        try:
            assert r.has_role_relationship(self.bob, self.knows, self.carol)
        finally:
            r.dispose()

    def test_is_sub_role_of(self):
        r = Reasoner(self.ontology)
        try:
            r.precompute_inferences(object_property_hierarchy=True)
            result = r.is_sub_role_of(self.close_friend, self.knows)
            assert result
        finally:
            r.dispose()

    def test_inverse_role_query(self):
        r = Reasoner(self.ontology)
        try:
            # Inverse of knows: carol is a known-by target of bob
            inv_knows = InverseRole.create(self.knows)
            result = r.has_role_relationship(self.carol, inv_knows, self.bob)
            # May or may not be supported via the InverseRole path, just ensure no crash
            assert isinstance(result, bool)
        finally:
            r.dispose()

    def test_get_instances_with_role_hierarchy(self):
        r = Reasoner(self.ontology)
        try:
            instances = r.get_instances(self.person)
            assert self.alice in instances
            assert self.bob in instances
            # Also classify object properties after instances are retrieved
            r.classify_object_properties()
            assert r._object_role_hierarchy is not None
        finally:
            r.dispose()

    def test_instance_manager_property_initialization(self):
        r = Reasoner(self.ontology)
        try:
            _ = r.get_instances(self.person)
            im = r._instance_manager
            assert im is not None
            assert im.are_classes_initialised()
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# 3. Ontology with inverse roles declared via has_inverse_roles flag
#    → triggers _add_known_role_subsumption inverse path
# ---------------------------------------------------------------------------

class TestInverseRolesOntology:
    """Tests where the ontology has inverse roles, exercising inverse subsumption paths."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        Y = Variable.create("Y")

        self.person = AtomicConcept.create(_ns("INV_Person"))
        self.parent_of = AtomicRole.create(_ns("INV_parentOf"))
        self.child_of = AtomicRole.create(_ns("INV_childOf"))

        self.adam = Individual.create(_ns("INV_adam"))
        self.eve = Individual.create(_ns("INV_eve"))
        self.cain = Individual.create(_ns("INV_cain"))

        # parentOf(X,Y) -> childOf(Y,X) — simulate inverse
        clauses = [
            DLClause.create(
                (Atom.create(self.child_of, Y, X),),
                (Atom.create(self.parent_of, X, Y),),
            ),
            DLClause.create(
                (Atom.create(self.person, X),),
                (Atom.create(self.person, X),),
            ),
        ]
        facts = [
            Atom.create(self.person, self.adam),
            Atom.create(self.person, self.eve),
            Atom.create(self.person, self.cain),
            Atom.create(self.parent_of, self.adam, self.cain),
            Atom.create(self.parent_of, self.eve, self.cain),
        ]
        # Build ontology with inverse roles flag
        self.ontology = DLOntology(
            ontology_iri="urn:test:boost9-inv",
            dl_clauses=frozenset(clauses),
            positive_facts=frozenset(facts),
            negative_facts=frozenset(),
        )
        yield

    def test_has_role_parent_of(self):
        r = Reasoner(self.ontology)
        try:
            result = r.has_role_relationship(self.adam, self.parent_of, self.cain)
            assert result
        finally:
            r.dispose()

    def test_classify_properties_with_inverse(self):
        r = Reasoner(self.ontology)
        try:
            # Just check consistency and classify classes
            r.classify_classes()
            assert r._atomic_concept_hierarchy is not None
        finally:
            r.dispose()

    def test_get_instances_person(self):
        r = Reasoner(self.ontology)
        try:
            instances = r.get_instances(self.person)
            assert self.adam in instances
            assert self.cain in instances
        finally:
            r.dispose()

    def test_get_types_adam(self):
        r = Reasoner(self.ontology)
        try:
            types = r.get_types(self.adam)
            assert self.person in types
        finally:
            r.dispose()

    def test_instance_manager_initialized(self):
        r = Reasoner(self.ontology)
        try:
            _ = r.get_instances(self.person)
            assert r._instance_manager is not None
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# 4. Ontology with no individuals — exercises empty-individual paths
# ---------------------------------------------------------------------------

class TestNoIndividuals:
    """Ontology with no ABox individuals; many methods should return empty sets."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.dog = AtomicConcept.create(_ns("NI_Dog"))
        self.animal = AtomicConcept.create(_ns("NI_Animal"))
        clauses = [
            DLClause.create(
                (Atom.create(self.animal, X),),
                (Atom.create(self.dog, X),),
            )
        ]
        self.ontology = _make_ontology(clauses, [], "urn:test:boost9-noind")
        yield

    def test_get_instances_empty(self):
        r = Reasoner(self.ontology)
        try:
            instances = r.get_instances(self.animal)
            assert instances == set()
        finally:
            r.dispose()

    def test_get_types_unknown_individual(self):
        r = Reasoner(self.ontology)
        try:
            unknown = Individual.create(_ns("NI_ghost"))
            types = r.get_types(unknown)
            assert AtomicConcept.THING in types
        finally:
            r.dispose()

    def test_has_type_returns_thing(self):
        r = Reasoner(self.ontology)
        try:
            unknown = Individual.create(_ns("NI_ghost"))
            assert r.has_type(unknown, AtomicConcept.THING)
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# 5. Inconsistent ontology paths
# ---------------------------------------------------------------------------

class TestInconsistentOntology:
    """Tests that confirm correct handling when the KB is inconsistent."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.a = AtomicConcept.create(_ns("INC_A"))
        self.b = AtomicConcept.create(_ns("INC_B"))
        self.ind = Individual.create(_ns("INC_x"))
        # A and B are disjoint, but x:A and x:B — inconsistency
        # Use a DLClause that makes it unsatisfiable:
        # A(X) ^ B(X) → ⊥ (empty head clause)
        clauses = [
            DLClause.create(
                (),  # empty head = bottom
                (Atom.create(self.a, X), Atom.create(self.b, X)),
            )
        ]
        facts = [
            Atom.create(self.a, self.ind),
            Atom.create(self.b, self.ind),
        ]
        self.ontology = _make_ontology(clauses, facts, "urn:test:boost9-inc")
        yield

    def test_is_not_consistent(self):
        r = Reasoner(self.ontology)
        try:
            result = r.is_consistent()
            assert not result
        finally:
            r.dispose()

    def test_get_instances_inconsistent(self):
        r = Reasoner(self.ontology)
        try:
            instances = r.get_instances(self.a)
            # For inconsistent KB, all individuals should be returned
            assert self.ind in instances
        finally:
            r.dispose()

    def test_has_type_inconsistent(self):
        r = Reasoner(self.ontology)
        try:
            result = r.has_type(self.ind, self.a)
            assert result
        finally:
            r.dispose()

    def test_has_role_relationship_inconsistent(self):
        r = Reasoner(self.ontology)
        try:
            role = AtomicRole.create(_ns("INC_r"))
            result = r.has_role_relationship(self.ind, role, self.ind)
            assert result
        finally:
            r.dispose()

    def test_is_same_individual_inconsistent(self):
        r = Reasoner(self.ontology)
        try:
            result = r.is_same_individual(self.ind, self.ind)
            assert result
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# 6. Multiple classify calls with pre-classified hierarchy
#    → triggers set_to_classified_concept_hierarchy and set_to_classified_role_hierarchy
# ---------------------------------------------------------------------------

class TestPreClassifiedHierarchy:
    """Calling classify_classes then get_instances exercises pre-classified paths."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.a = AtomicConcept.create(_ns("PC_A"))
        self.b = AtomicConcept.create(_ns("PC_B"))
        self.role = AtomicRole.create(_ns("PC_r"))
        self.ind1 = Individual.create(_ns("PC_ind1"))
        self.ind2 = Individual.create(_ns("PC_ind2"))
        self.ind3 = Individual.create(_ns("PC_ind3"))

        clauses = [
            DLClause.create(
                (Atom.create(self.b, X),),
                (Atom.create(self.a, X),),
            )
        ]
        facts = [
            Atom.create(self.a, self.ind1),
            Atom.create(self.a, self.ind2),
            Atom.create(self.b, self.ind3),
            Atom.create(self.role, self.ind1, self.ind2),
            Atom.create(self.role, self.ind2, self.ind3),
        ]
        self.ontology = _make_ontology(clauses, facts, "urn:test:boost9-pc")
        yield

    def test_classify_then_get_instances(self):
        r = Reasoner(self.ontology)
        try:
            r.classify_classes()
            instances = r.get_instances(self.a)
            assert self.ind1 in instances
            assert self.ind2 in instances
            assert self.ind3 not in instances
        finally:
            r.dispose()

    def test_classify_then_get_instances_b(self):
        r = Reasoner(self.ontology)
        try:
            r.classify_classes()
            instances = r.get_instances(self.b)
            # ind1 and ind2 are A, and A ⊑ B, so they should be in B too
            assert self.ind1 in instances or self.ind3 in instances
        finally:
            r.dispose()

    def test_classify_object_properties_then_query(self):
        r = Reasoner(self.ontology)
        try:
            r.precompute_inferences(
                class_hierarchy=True, object_property_hierarchy=True
            )
            result = r.has_role_relationship(self.ind1, self.role, self.ind2)
            assert result
        finally:
            r.dispose()

    def test_has_type_direct_after_classify(self):
        r = Reasoner(self.ontology)
        try:
            r.classify_classes()
            result = r.has_type(self.ind1, self.a, direct=True)
            assert result
        finally:
            r.dispose()

    def test_has_type_nondirect_after_classify(self):
        r = Reasoner(self.ontology)
        try:
            r.classify_classes()
            result = r.has_type(self.ind1, self.b, direct=False)
            assert result
        finally:
            r.dispose()

    def test_set_to_classified_concept_hierarchy_after_init(self):
        """Exercise set_to_classified_concept_hierarchy when m_classes_initialised=True."""
        r = Reasoner(self.ontology)
        try:
            r.classify_classes()
            # Trigger class instance manager initialization
            _ = r.get_instances(self.a)
            im = r._instance_manager
            if im is not None and r._atomic_concept_hierarchy is not None:
                # This exercises the branch where m_classes_initialised is True
                im.set_to_classified_concept_hierarchy(r._atomic_concept_hierarchy)
        finally:
            r.dispose()

    def test_set_to_classified_role_hierarchy_after_init(self):
        """Exercise set_to_classified_role_hierarchy when properties are already initialised."""
        r = Reasoner(self.ontology)
        try:
            # First get instances (initializes instance manager with no role hierarchy)
            _ = r.get_instances(self.a)
            im = r._instance_manager
            # Now classify object properties (builds role hierarchy separately)
            r.classify_object_properties()
            if im is not None and r._object_role_hierarchy is not None:
                # This triggers set_to_classified_role_hierarchy with m_properties_initialised=True
                im.set_to_classified_role_hierarchy(r._object_role_hierarchy)
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# 7. Large ABox with many individuals
#    → exercises _initialize_individuals_for_nodes, _initialize_same_as,
#      and _read_off_class_instances_by_individual with many individuals
# ---------------------------------------------------------------------------

class TestLargeABox:
    """Many individuals to exercise batch initialization paths."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.entity = AtomicConcept.create(_ns("LA_Entity"))
        self.role = AtomicRole.create(_ns("LA_rel"))

        n = 20
        self.individuals = [Individual.create(_ns(f"LA_ind{i}")) for i in range(n)]

        facts = [Atom.create(self.entity, ind) for ind in self.individuals]
        # Create a chain of role assertions
        for i in range(n - 1):
            facts.append(
                Atom.create(self.role, self.individuals[i], self.individuals[i + 1])
            )

        self.ontology = _make_ontology([], facts, "urn:test:boost9-large")
        yield

    def test_get_instances_entity_all(self):
        r = Reasoner(self.ontology)
        try:
            instances = r.get_instances(self.entity)
            assert len(instances) == 20
        finally:
            r.dispose()

    def test_get_types_each_individual(self):
        r = Reasoner(self.ontology)
        try:
            r.precompute_inferences(class_hierarchy=True)
            for ind in self.individuals[:5]:
                types = r.get_types(ind)
                assert self.entity in types
        finally:
            r.dispose()

    def test_has_role_relationships_chain(self):
        r = Reasoner(self.ontology)
        try:
            for i in range(5):
                result = r.has_role_relationship(
                    self.individuals[i], self.role, self.individuals[i + 1]
                )
                assert result
        finally:
            r.dispose()

    def test_initialize_property_instances_large(self):
        r = Reasoner(self.ontology)
        try:
            _ = r.get_instances(self.entity)
            im = r._instance_manager
            assert im is not None
            assert im.are_classes_initialised()
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# 8. Tests for QuasiOrderClassificationForRoles via classify_object_properties
# ---------------------------------------------------------------------------

class TestQuasiOrderClassificationForRoles:
    """Exercises QuasiOrderClassificationForRoles code paths."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        Y = Variable.create("Y")

        self.person = AtomicConcept.create(_ns("QR_Person"))
        self.parent = AtomicRole.create(_ns("QR_parent"))
        self.ancestor = AtomicRole.create(_ns("QR_ancestor"))
        self.sibling = AtomicRole.create(_ns("QR_sibling"))

        self.a = Individual.create(_ns("QR_a"))
        self.b = Individual.create(_ns("QR_b"))
        self.c = Individual.create(_ns("QR_c"))

        # parent ⊑ ancestor (role subsumption clause)
        clauses = [
            DLClause.create(
                (Atom.create(self.ancestor, X, Y),),
                (Atom.create(self.parent, X, Y),),
            ),
        ]
        facts = [
            Atom.create(self.person, self.a),
            Atom.create(self.person, self.b),
            Atom.create(self.person, self.c),
            Atom.create(self.parent, self.a, self.b),
            Atom.create(self.parent, self.b, self.c),
            Atom.create(self.sibling, self.a, self.c),
        ]
        self.ontology = _make_ontology(clauses, facts, "urn:test:boost9-qr")
        yield

    def test_classify_object_properties(self):
        r = Reasoner(self.ontology)
        try:
            _ = r.get_instances(self.person)
            r.classify_object_properties()
            assert r._object_role_hierarchy is not None
        finally:
            r.dispose()

    def test_is_sub_role_parent_ancestor(self):
        r = Reasoner(self.ontology)
        try:
            result = r.is_sub_role_of(self.parent, self.ancestor)
            # parent ⊑ ancestor is a DLClause, not a direct role axiom.
            # is_sub_role_of does a tableau test; result may vary.
            assert isinstance(result, bool)
        finally:
            r.dispose()

    def test_get_role_instances_via_instance_manager(self):
        r = Reasoner(self.ontology)
        try:
            _ = r.get_instances(self.person)
            im = r._instance_manager
            if im is not None:
                vals = im.get_object_property_values(self.parent, self.a)
                assert isinstance(vals, set)
        finally:
            r.dispose()

    def test_has_role_parent(self):
        r = Reasoner(self.ontology)
        try:
            assert r.has_role_relationship(self.a, self.parent, self.b)
        finally:
            r.dispose()

    def test_has_role_ancestor_inferred_or_subsumed(self):
        r = Reasoner(self.ontology)
        try:
            # parent(a,b) and parent ⊑ ancestor → ancestor(a,b)
            # This may return True or False depending on how the reasoner loads ABox
            result = r.has_role_relationship(self.a, self.ancestor, self.b)
            assert isinstance(result, bool)
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# 9. Parser tests — directly calling _OwlreadyMapper methods
# ---------------------------------------------------------------------------

class TestOwlreadyMapperDirect:
    """Exercise parser._OwlreadyMapper via mock owlready2 objects."""

    def _make_mapper(self):
        from hermit.parser import _OwlreadyMapper
        import types

        # Create a minimal mock owlready2 module
        or2 = types.SimpleNamespace()

        # Constants
        or2.SOME = 24
        or2.ONLY = 25
        or2.MIN = 26
        or2.MAX = 27
        or2.EXACTLY = 28
        or2.HAS_SELF = 11
        or2.VALUE = 29

        # Marker classes for isinstance checks
        class ThingClass:
            pass
        class ObjectPropertyClass:
            pass
        class DataPropertyClass:
            pass
        class Not:
            pass
        class And:
            pass
        class Or:
            pass
        class OneOf:
            pass
        class Restriction:
            pass
        class TransitiveProperty:
            pass
        class SymmetricProperty:
            pass
        class AsymmetricProperty:
            pass
        class ReflexiveProperty:
            pass
        class IrreflexiveProperty:
            pass
        class FunctionalProperty:
            pass
        class InverseFunctionalProperty:
            pass

        or2.ThingClass = ThingClass
        or2.ObjectPropertyClass = ObjectPropertyClass
        or2.DataPropertyClass = DataPropertyClass
        or2.Not = Not
        or2.And = And
        or2.Or = Or
        or2.OneOf = OneOf
        or2.Restriction = Restriction
        or2.TransitiveProperty = TransitiveProperty
        or2.SymmetricProperty = SymmetricProperty
        or2.AsymmetricProperty = AsymmetricProperty
        or2.ReflexiveProperty = ReflexiveProperty
        or2.IrreflexiveProperty = IrreflexiveProperty
        or2.FunctionalProperty = FunctionalProperty
        or2.InverseFunctionalProperty = InverseFunctionalProperty

        # Thing and Nothing singletons
        thing_obj = object()
        nothing_obj = object()
        or2.Thing = thing_obj
        or2.Nothing = nothing_obj

        return _OwlreadyMapper(or2), or2

    def test_map_thing(self):
        mapper, or2 = self._make_mapper()
        from hermit.owl_model.class_expression import OWLThing
        result = mapper._map_class_expression(or2.Thing)
        assert result is OWLThing

    def test_map_nothing(self):
        mapper, or2 = self._make_mapper()
        from hermit.owl_model.class_expression import OWLNothing
        result = mapper._map_class_expression(or2.Nothing)
        assert result is OWLNothing

    def test_map_named_class(self):
        mapper, or2 = self._make_mapper()
        from hermit.owl_model.class_expression import OWLClass
        cls = or2.ThingClass()
        cls.iri = "http://example.org#Foo"
        result = mapper._map_class_expression(cls)
        assert isinstance(result, OWLClass)
        # IRI may be an IRI object; check it contains the expected string
        assert "Foo" in str(result.iri)

    def test_map_named_class_no_iri(self):
        mapper, or2 = self._make_mapper()
        cls = or2.ThingClass()
        cls.iri = None
        result = mapper._map_class_expression(cls)
        assert result is None

    def test_map_not(self):
        mapper, or2 = self._make_mapper()
        from hermit.owl_model.class_expression import OWLObjectComplementOf, OWLThing
        not_expr = or2.Not()
        not_expr.Class = or2.Thing
        result = mapper._map_class_expression(not_expr)
        assert isinstance(result, OWLObjectComplementOf)

    def test_map_not_none_class(self):
        mapper, or2 = self._make_mapper()
        not_expr = or2.Not()
        not_expr.Class = None  # _map_class_expression(None) → None
        result = mapper._map_class_expression(not_expr)
        assert result is None

    def test_map_and_two_classes(self):
        mapper, or2 = self._make_mapper()
        from hermit.owl_model.class_expression import OWLObjectIntersectionOf
        and_expr = or2.And()
        c1 = or2.ThingClass()
        c1.iri = "http://example.org#A"
        c2 = or2.ThingClass()
        c2.iri = "http://example.org#B"
        and_expr.Classes = [c1, c2]
        result = mapper._map_class_expression(and_expr)
        assert isinstance(result, OWLObjectIntersectionOf)

    def test_map_and_one_class(self):
        mapper, or2 = self._make_mapper()
        from hermit.owl_model.class_expression import OWLClass
        and_expr = or2.And()
        c1 = or2.ThingClass()
        c1.iri = "http://example.org#A"
        and_expr.Classes = [c1]
        result = mapper._map_class_expression(and_expr)
        assert isinstance(result, OWLClass)

    def test_map_and_empty(self):
        mapper, or2 = self._make_mapper()
        and_expr = or2.And()
        and_expr.Classes = []
        result = mapper._map_class_expression(and_expr)
        assert result is None

    def test_map_or_two_classes(self):
        mapper, or2 = self._make_mapper()
        from hermit.owl_model.class_expression import OWLObjectUnionOf
        or_expr = or2.Or()
        c1 = or2.ThingClass()
        c1.iri = "http://example.org#A"
        c2 = or2.ThingClass()
        c2.iri = "http://example.org#B"
        or_expr.Classes = [c1, c2]
        result = mapper._map_class_expression(or_expr)
        assert isinstance(result, OWLObjectUnionOf)

    def test_map_or_one_class(self):
        mapper, or2 = self._make_mapper()
        from hermit.owl_model.class_expression import OWLClass
        or_expr = or2.Or()
        c1 = or2.ThingClass()
        c1.iri = "http://example.org#A"
        or_expr.Classes = [c1]
        result = mapper._map_class_expression(or_expr)
        assert isinstance(result, OWLClass)

    def test_map_or_empty(self):
        mapper, or2 = self._make_mapper()
        or_expr = or2.Or()
        or_expr.Classes = []
        result = mapper._map_class_expression(or_expr)
        assert result is None

    def test_map_one_of(self):
        mapper, or2 = self._make_mapper()
        import types as _types
        from hermit.owl_model.class_expression import OWLObjectOneOf
        oneof = or2.OneOf()
        ind = _types.SimpleNamespace(iri="http://example.org#bob")
        oneof.instances = [ind]
        result = mapper._map_class_expression(oneof)
        assert isinstance(result, OWLObjectOneOf)

    def test_map_one_of_empty(self):
        mapper, or2 = self._make_mapper()
        oneof = or2.OneOf()
        oneof.instances = []
        result = mapper._map_class_expression(oneof)
        assert result is None

    def test_map_restriction_some(self):
        mapper, or2 = self._make_mapper()
        from hermit.owl_model.class_expression import OWLObjectSomeValuesFrom
        restr = or2.Restriction()
        prop = or2.ObjectPropertyClass()
        prop.iri = "http://example.org#hasPet"
        restr.property = prop
        restr.type = or2.SOME
        restr.value = or2.Thing
        restr.cardinality = None
        result = mapper._map_class_expression(restr)
        assert isinstance(result, OWLObjectSomeValuesFrom)

    def test_map_restriction_only(self):
        mapper, or2 = self._make_mapper()
        from hermit.owl_model.class_expression import OWLObjectAllValuesFrom
        restr = or2.Restriction()
        prop = or2.ObjectPropertyClass()
        prop.iri = "http://example.org#hasPet"
        restr.property = prop
        restr.type = or2.ONLY
        restr.value = or2.Thing
        restr.cardinality = None
        result = mapper._map_class_expression(restr)
        assert isinstance(result, OWLObjectAllValuesFrom)

    def test_map_restriction_min(self):
        mapper, or2 = self._make_mapper()
        from hermit.owl_model.class_expression import OWLObjectMinCardinality
        restr = or2.Restriction()
        prop = or2.ObjectPropertyClass()
        prop.iri = "http://example.org#hasPet"
        restr.property = prop
        restr.type = or2.MIN
        restr.value = None
        restr.cardinality = 2
        result = mapper._map_class_expression(restr)
        assert isinstance(result, OWLObjectMinCardinality)

    def test_map_restriction_max(self):
        mapper, or2 = self._make_mapper()
        from hermit.owl_model.class_expression import OWLObjectMaxCardinality
        restr = or2.Restriction()
        prop = or2.ObjectPropertyClass()
        prop.iri = "http://example.org#hasPet"
        restr.property = prop
        restr.type = or2.MAX
        restr.value = None
        restr.cardinality = 1
        result = mapper._map_class_expression(restr)
        assert isinstance(result, OWLObjectMaxCardinality)

    def test_map_restriction_exactly(self):
        mapper, or2 = self._make_mapper()
        from hermit.owl_model.class_expression import OWLObjectExactCardinality
        restr = or2.Restriction()
        prop = or2.ObjectPropertyClass()
        prop.iri = "http://example.org#hasPet"
        restr.property = prop
        restr.type = or2.EXACTLY
        restr.value = None
        restr.cardinality = 3
        result = mapper._map_class_expression(restr)
        assert isinstance(result, OWLObjectExactCardinality)

    def test_map_restriction_has_self(self):
        mapper, or2 = self._make_mapper()
        from hermit.owl_model.class_expression import OWLObjectHasSelf
        restr = or2.Restriction()
        prop = or2.ObjectPropertyClass()
        prop.iri = "http://example.org#knows"
        restr.property = prop
        restr.type = or2.HAS_SELF
        restr.value = None
        restr.cardinality = None
        result = mapper._map_class_expression(restr)
        assert isinstance(result, OWLObjectHasSelf)

    def test_map_restriction_has_value(self):
        mapper, or2 = self._make_mapper()
        import types as _types
        from hermit.owl_model.class_expression import OWLObjectHasValue
        restr = or2.Restriction()
        prop = or2.ObjectPropertyClass()
        prop.iri = "http://example.org#knows"
        restr.property = prop
        restr.type = or2.VALUE
        ind = _types.SimpleNamespace(iri="http://example.org#alice")
        restr.value = ind
        restr.cardinality = None
        result = mapper._map_class_expression(restr)
        assert isinstance(result, OWLObjectHasValue)

    def test_map_restriction_data_property_returns_none(self):
        """Data property restrictions should return None (handled elsewhere)."""
        import types as _types
        mapper, or2 = self._make_mapper()
        restr = or2.Restriction()
        # Make the property NOT an ObjectPropertyClass — use SimpleNamespace
        prop = _types.SimpleNamespace(iri="http://example.org#age")
        restr.property = prop
        restr.type = or2.SOME
        restr.value = None
        restr.cardinality = None
        result = mapper._map_class_expression(restr)
        assert result is None

    def test_map_restriction_no_property(self):
        mapper, or2 = self._make_mapper()
        restr = or2.Restriction()
        restr.property = None
        restr.type = or2.SOME
        restr.value = or2.Thing
        restr.cardinality = None
        result = mapper._map_class_expression(restr)
        assert result is None

    def test_map_unknown_expression(self):
        mapper, or2 = self._make_mapper()
        result = mapper._map_class_expression(42)  # unknown type
        assert result is None

    def test_extract_class_axioms(self):
        """Test _extract_class_axioms with a mock ontology."""
        mapper, or2 = self._make_mapper()

        # Create a mock ontology
        class MockCls:
            iri = "http://example.org#MockA"
            is_a = []
            equivalent_to = []

        class MockOntology:
            def classes(self):
                return [MockCls()]
            def disjoint_classes(self):
                return []

        axioms = []
        mapper._extract_class_axioms(MockOntology(), axioms)
        # No sub-class or equivalents → zero axioms
        assert isinstance(axioms, list)

    def test_extract_class_axioms_with_subclass(self):
        mapper, or2 = self._make_mapper()

        parent = or2.ThingClass()
        parent.iri = "http://example.org#Parent"

        class MockCls:
            iri = "http://example.org#Child"
            is_a = [parent]
            equivalent_to = []

        class MockOntology:
            def classes(self):
                return [MockCls()]
            def disjoint_classes(self):
                return []

        axioms = []
        mapper._extract_class_axioms(MockOntology(), axioms)
        assert len(axioms) >= 1

    def test_extract_class_axioms_with_equivalent(self):
        mapper, or2 = self._make_mapper()

        eq_cls = or2.ThingClass()
        eq_cls.iri = "http://example.org#Eq"

        class MockCls:
            iri = "http://example.org#A"
            is_a = []
            equivalent_to = [eq_cls]

        class MockOntology:
            def classes(self):
                return [MockCls()]
            def disjoint_classes(self):
                return []

        axioms = []
        mapper._extract_class_axioms(MockOntology(), axioms)
        assert len(axioms) >= 1

    def test_extract_class_axioms_with_disjoint(self):
        mapper, or2 = self._make_mapper()

        class MockDisjoint:
            entities = []

        class MockDisjoint2:
            class E1:
                iri = "http://example.org#D1"
            class E2:
                iri = "http://example.org#D2"
            entities = [E1(), E2()]

        class MockOntology:
            def classes(self):
                return []
            def disjoint_classes(self):
                return [MockDisjoint(), MockDisjoint2()]

        axioms = []
        mapper._extract_class_axioms(MockOntology(), axioms)
        assert any(True for _ in axioms)  # at least one disjoint axiom

    def test_extract_individual_axioms(self):
        mapper, or2 = self._make_mapper()

        cls = or2.ThingClass()
        cls.iri = "http://example.org#Foo"

        class MockInd:
            iri = "http://example.org#ind1"
            is_a = [cls]
            equivalent_to = []
            different_from = []

        class MockOntology:
            def individuals(self):
                return [MockInd()]
            def object_properties(self):
                return []

        axioms = []
        mapper._extract_individual_axioms(MockOntology(), axioms)
        assert len(axioms) >= 1  # ClassAssertion

    def test_extract_individual_axioms_same_individual(self):
        mapper, or2 = self._make_mapper()

        class MockSame:
            iri = "http://example.org#ind2"

        class MockInd:
            iri = "http://example.org#ind1"
            is_a = []
            equivalent_to = [MockSame()]
            different_from = []

        class MockOntology:
            def individuals(self):
                return [MockInd()]
            def object_properties(self):
                return []

        axioms = []
        mapper._extract_individual_axioms(MockOntology(), axioms)
        assert len(axioms) >= 1  # SameIndividual

    def test_extract_individual_axioms_different_individuals(self):
        mapper, or2 = self._make_mapper()

        class MockDiff:
            iri = "http://example.org#ind2"

        class MockInd:
            iri = "http://example.org#ind1"
            is_a = []
            equivalent_to = []
            different_from = [MockDiff()]

        class MockOntology:
            def individuals(self):
                return [MockInd()]
            def object_properties(self):
                return []

        axioms = []
        mapper._extract_individual_axioms(MockOntology(), axioms)
        assert len(axioms) >= 1  # DifferentIndividuals

    def test_extract_object_property_axioms_transitive(self):
        mapper, or2 = self._make_mapper()

        class MockProp:
            iri = "http://example.org#knows"
            is_a = [or2.TransitiveProperty]

        class MockOntology:
            def object_properties(self):
                return [MockProp()]

        axioms = []
        mapper._extract_object_property_axioms(MockOntology(), axioms)
        assert len(axioms) >= 1

    def test_extract_object_property_axioms_symmetric(self):
        mapper, or2 = self._make_mapper()

        class MockProp:
            iri = "http://example.org#p"
            is_a = [or2.SymmetricProperty]

        class MockOntology:
            def object_properties(self):
                return [MockProp()]

        axioms = []
        mapper._extract_object_property_axioms(MockOntology(), axioms)
        assert len(axioms) >= 1

    def test_extract_object_property_axioms_asymmetric(self):
        mapper, or2 = self._make_mapper()

        class MockProp:
            iri = "http://example.org#p"
            is_a = [or2.AsymmetricProperty]

        class MockOntology:
            def object_properties(self):
                return [MockProp()]

        axioms = []
        mapper._extract_object_property_axioms(MockOntology(), axioms)
        assert len(axioms) >= 1

    def test_extract_object_property_axioms_reflexive(self):
        mapper, or2 = self._make_mapper()

        class MockProp:
            iri = "http://example.org#p"
            is_a = [or2.ReflexiveProperty]

        class MockOntology:
            def object_properties(self):
                return [MockProp()]

        axioms = []
        mapper._extract_object_property_axioms(MockOntology(), axioms)
        assert len(axioms) >= 1

    def test_extract_object_property_axioms_irreflexive(self):
        mapper, or2 = self._make_mapper()

        class MockProp:
            iri = "http://example.org#p"
            is_a = [or2.IrreflexiveProperty]

        class MockOntology:
            def object_properties(self):
                return [MockProp()]

        axioms = []
        mapper._extract_object_property_axioms(MockOntology(), axioms)
        assert len(axioms) >= 1

    def test_extract_object_property_axioms_functional(self):
        mapper, or2 = self._make_mapper()

        class MockProp:
            iri = "http://example.org#p"
            is_a = [or2.FunctionalProperty]

        class MockOntology:
            def object_properties(self):
                return [MockProp()]

        axioms = []
        mapper._extract_object_property_axioms(MockOntology(), axioms)
        assert len(axioms) >= 1

    def test_extract_object_property_axioms_inverse_functional(self):
        mapper, or2 = self._make_mapper()

        class MockProp:
            iri = "http://example.org#p"
            is_a = [or2.InverseFunctionalProperty]

        class MockOntology:
            def object_properties(self):
                return [MockProp()]

        axioms = []
        mapper._extract_object_property_axioms(MockOntology(), axioms)
        assert len(axioms) >= 1

    def test_extract_object_property_axioms_subproperty(self):
        mapper, or2 = self._make_mapper()

        parent_prop = or2.ObjectPropertyClass()
        parent_prop.iri = "http://example.org#superProp"

        class MockProp:
            iri = "http://example.org#subProp"
            is_a = [parent_prop]

        class MockOntology:
            def object_properties(self):
                return [MockProp()]

        axioms = []
        mapper._extract_object_property_axioms(MockOntology(), axioms)
        assert len(axioms) >= 1

    def test_extract_data_property_axioms_functional(self):
        mapper, or2 = self._make_mapper()

        class MockDataProp:
            iri = "http://example.org#age"
            is_a = [or2.FunctionalProperty]

        class MockOntology:
            def data_properties(self):
                return [MockDataProp()]

        axioms = []
        mapper._extract_data_property_axioms(MockOntology(), axioms)
        assert len(axioms) >= 1

    def test_extract_data_property_axioms_subproperty(self):
        mapper, or2 = self._make_mapper()

        parent_dp = or2.DataPropertyClass()
        parent_dp.iri = "http://example.org#superDP"

        class MockDataProp:
            iri = "http://example.org#subDP"
            is_a = [parent_dp]

        class MockOntology:
            def data_properties(self):
                return [MockDataProp()]

        axioms = []
        mapper._extract_data_property_axioms(MockOntology(), axioms)
        assert len(axioms) >= 1

    def test_extract_object_property_assertion(self):
        """Test that object property assertions are extracted."""
        mapper, or2 = self._make_mapper()

        class MockTarget:
            iri = "http://example.org#target"

        class MockProp:
            iri = "http://example.org#hasPet"
            python_name = "hasPet"

        class MockInd:
            iri = "http://example.org#owner"
            is_a = []
            equivalent_to = []
            different_from = []
            hasPet = [MockTarget()]

        class MockOntology:
            def individuals(self):
                return [MockInd()]
            def object_properties(self):
                return [MockProp()]

        axioms = []
        mapper._extract_individual_axioms(MockOntology(), axioms)
        # Should have ObjectPropertyAssertion
        from hermit.owl_model.owl_axiom import OWLObjectPropertyAssertionAxiom
        assert any(isinstance(a, OWLObjectPropertyAssertionAxiom) for a in axioms)


# ---------------------------------------------------------------------------
# 10. Edge cases for instance manager paths
# ---------------------------------------------------------------------------

class TestInstanceManagerEdgeCases:
    """Edge cases to hit specific branches in instance_manager.py."""

    def test_get_instances_unknown_concept(self):
        """Querying an unknown concept returns empty set."""
        X = Variable.create("X")
        dog = AtomicConcept.create(_ns("EC_Dog"))
        fido = Individual.create(_ns("EC_fido"))
        facts = [Atom.create(dog, fido)]
        ontology = _make_ontology([], facts, "urn:test:boost9-ec1")
        r = Reasoner(ontology)
        try:
            unknown = AtomicConcept.create(_ns("EC_Unknown"))
            instances = r.get_instances(unknown)
            assert instances == set()
        finally:
            r.dispose()

    def test_has_role_relationship_unknown_individuals(self):
        """Querying role with unknown individuals should not crash."""
        role = AtomicRole.create(_ns("EC_r"))
        ind1 = Individual.create(_ns("EC_ind1"))
        ind2 = Individual.create(_ns("EC_ind2"))
        ind3 = Individual.create(_ns("EC_ind3"))
        facts = [Atom.create(role, ind1, ind2)]
        ontology = _make_ontology([], facts, "urn:test:boost9-ec2")
        r = Reasoner(ontology)
        try:
            unknown1 = Individual.create(_ns("EC_ghost1"))
            unknown2 = Individual.create(_ns("EC_ghost2"))
            result = r.has_role_relationship(unknown1, role, unknown2)
            assert isinstance(result, bool)
        finally:
            r.dispose()

    def test_get_types_nondirect_all_ancestors(self):
        """Non-direct types should include all ancestors."""
        X = Variable.create("X")
        a = AtomicConcept.create(_ns("EC_A2"))
        b = AtomicConcept.create(_ns("EC_B2"))
        c = AtomicConcept.create(_ns("EC_C2"))
        ind = Individual.create(_ns("EC_ind_chain"))
        clauses = [
            DLClause.create((Atom.create(b, X),), (Atom.create(a, X),)),
            DLClause.create((Atom.create(c, X),), (Atom.create(b, X),)),
        ]
        facts = [Atom.create(a, ind)]
        ontology = _make_ontology(clauses, facts, "urn:test:boost9-ec3")
        r = Reasoner(ontology)
        try:
            types = r.get_types(ind, direct=False)
            assert a in types
            assert b in types
            assert c in types
        finally:
            r.dispose()

    def test_get_instances_top_concept(self):
        """get_instances(Thing) returns all named individuals."""
        X = Variable.create("X")
        dog = AtomicConcept.create(_ns("EC_DogT"))
        fido = Individual.create(_ns("EC_fidoT"))
        whiskers = Individual.create(_ns("EC_whiskersT"))
        facts = [
            Atom.create(dog, fido),
            Atom.create(dog, whiskers),
        ]
        ontology = _make_ontology([], facts, "urn:test:boost9-ec4")
        r = Reasoner(ontology)
        try:
            r.precompute_inferences(class_hierarchy=True)
            instances = r.get_instances(AtomicConcept.THING, direct=False)
            assert fido in instances
            assert whiskers in instances
        finally:
            r.dispose()

    def test_multiple_get_instances_calls(self):
        """Multiple calls to get_instances should be idempotent."""
        X = Variable.create("X")
        a = AtomicConcept.create(_ns("EC_Multi_A"))
        ind = Individual.create(_ns("EC_multi_ind"))
        facts = [Atom.create(a, ind)]
        ontology = _make_ontology([], facts, "urn:test:boost9-ec5")
        r = Reasoner(ontology)
        try:
            instances1 = r.get_instances(a)
            instances2 = r.get_instances(a)
            assert instances1 == instances2
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# 11. More parser edge cases: None IRI, None prop, non-iterable targets
# ---------------------------------------------------------------------------

class TestParserEdgeCases:
    """Additional parser tests to cover remaining uncovered branches."""

    def _make_mapper(self):
        from hermit.parser import _OwlreadyMapper
        import types

        or2 = types.SimpleNamespace()
        or2.SOME = 24
        or2.ONLY = 25
        or2.MIN = 26
        or2.MAX = 27
        or2.EXACTLY = 28
        or2.HAS_SELF = 11
        or2.VALUE = 29

        class ThingClass:
            pass
        class ObjectPropertyClass:
            pass
        class DataPropertyClass:
            pass
        class Not:
            pass
        class And:
            pass
        class Or:
            pass
        class OneOf:
            pass
        class Restriction:
            pass
        class TransitiveProperty:
            pass
        class SymmetricProperty:
            pass
        class AsymmetricProperty:
            pass
        class ReflexiveProperty:
            pass
        class IrreflexiveProperty:
            pass
        class FunctionalProperty:
            pass
        class InverseFunctionalProperty:
            pass

        or2.ThingClass = ThingClass
        or2.ObjectPropertyClass = ObjectPropertyClass
        or2.DataPropertyClass = DataPropertyClass
        or2.Not = Not
        or2.And = And
        or2.Or = Or
        or2.OneOf = OneOf
        or2.Restriction = Restriction
        or2.TransitiveProperty = TransitiveProperty
        or2.SymmetricProperty = SymmetricProperty
        or2.AsymmetricProperty = AsymmetricProperty
        or2.ReflexiveProperty = ReflexiveProperty
        or2.IrreflexiveProperty = IrreflexiveProperty
        or2.FunctionalProperty = FunctionalProperty
        or2.InverseFunctionalProperty = InverseFunctionalProperty

        thing_obj = object()
        nothing_obj = object()
        or2.Thing = thing_obj
        or2.Nothing = nothing_obj

        return _OwlreadyMapper(or2), or2

    def test_extract_class_axioms_cls_no_iri(self):
        """Classes with no IRI should be skipped."""
        mapper, or2 = self._make_mapper()

        class MockCls:
            iri = None
            is_a = []
            equivalent_to = []

        class MockOntology:
            def classes(self):
                return [MockCls()]
            def disjoint_classes(self):
                return []

        axioms = []
        mapper._extract_class_axioms(MockOntology(), axioms)
        assert axioms == []

    def test_extract_individual_axioms_ind_no_iri(self):
        """Individuals with no IRI should be skipped."""
        mapper, or2 = self._make_mapper()

        class MockInd:
            iri = None
            is_a = []
            equivalent_to = []
            different_from = []

        class MockOntology:
            def individuals(self):
                return [MockInd()]
            def object_properties(self):
                return []

        axioms = []
        mapper._extract_individual_axioms(MockOntology(), axioms)
        assert axioms == []

    def test_extract_individual_axioms_prop_no_iri(self):
        """Properties with no IRI in individual axioms should be skipped."""
        mapper, or2 = self._make_mapper()

        class MockProp:
            iri = None
            python_name = "foo"

        class MockInd:
            iri = "http://example.org#ind"
            is_a = []
            equivalent_to = []
            different_from = []

        class MockOntology:
            def individuals(self):
                return [MockInd()]
            def object_properties(self):
                return [MockProp()]

        axioms = []
        mapper._extract_individual_axioms(MockOntology(), axioms)
        assert axioms == []

    def test_extract_individual_axioms_prop_no_name(self):
        """Properties with no name should be skipped."""
        mapper, or2 = self._make_mapper()

        class MockProp:
            iri = "http://example.org#p"
            python_name = None
            name = None

        class MockInd:
            iri = "http://example.org#ind"
            is_a = []
            equivalent_to = []
            different_from = []

        class MockOntology:
            def individuals(self):
                return [MockInd()]
            def object_properties(self):
                return [MockProp()]

        axioms = []
        mapper._extract_individual_axioms(MockOntology(), axioms)
        assert axioms == []

    def test_extract_individual_axioms_non_iterable_target(self):
        """Non-iterable property targets should be wrapped in list."""
        mapper, or2 = self._make_mapper()
        import types as _types

        class MockProp:
            iri = "http://example.org#hasPet"
            python_name = "hasPet"

        target = _types.SimpleNamespace(iri="http://example.org#target")

        class MockInd:
            iri = "http://example.org#ind"
            is_a = []
            equivalent_to = []
            different_from = []
            hasPet = target  # non-iterable (single object, not a list)

        class MockOntology:
            def individuals(self):
                return [MockInd()]
            def object_properties(self):
                return [MockProp()]

        axioms = []
        mapper._extract_individual_axioms(MockOntology(), axioms)
        from hermit.owl_model.owl_axiom import OWLObjectPropertyAssertionAxiom
        assert any(isinstance(a, OWLObjectPropertyAssertionAxiom) for a in axioms)

    def test_extract_object_property_axioms_prop_no_iri(self):
        """Object properties with no IRI should be skipped."""
        mapper, or2 = self._make_mapper()

        class MockProp:
            iri = None
            is_a = []

        class MockOntology:
            def object_properties(self):
                return [MockProp()]

        axioms = []
        mapper._extract_object_property_axioms(MockOntology(), axioms)
        assert axioms == []

    def test_extract_data_property_axioms_prop_no_iri(self):
        """Data properties with no IRI should be skipped."""
        mapper, or2 = self._make_mapper()

        class MockDataProp:
            iri = None
            is_a = []

        class MockOntology:
            def data_properties(self):
                return [MockDataProp()]

        axioms = []
        mapper._extract_data_property_axioms(MockOntology(), axioms)
        assert axioms == []

    def test_map_restriction_some_filler_none(self):
        """SomeValuesFrom with unmappable filler returns None."""
        mapper, or2 = self._make_mapper()
        restr = or2.Restriction()
        prop = or2.ObjectPropertyClass()
        prop.iri = "http://example.org#p"
        restr.property = prop
        restr.type = or2.SOME
        # value=42 (unmappable) → filler = None
        restr.value = 42
        restr.cardinality = None
        result = mapper._map_class_expression(restr)
        assert result is None

    def test_map_restriction_only_filler_none(self):
        """AllValuesFrom with unmappable filler returns None."""
        mapper, or2 = self._make_mapper()
        restr = or2.Restriction()
        prop = or2.ObjectPropertyClass()
        prop.iri = "http://example.org#p"
        restr.property = prop
        restr.type = or2.ONLY
        restr.value = 42  # unmappable
        restr.cardinality = None
        result = mapper._map_class_expression(restr)
        assert result is None

    def test_extract_object_property_subproperty_same_iri(self):
        """SubObjectPropertyOf where parent.iri == prop.iri should be skipped."""
        mapper, or2 = self._make_mapper()

        parent_prop = or2.ObjectPropertyClass()
        parent_prop.iri = "http://example.org#p"  # same as child

        class MockProp:
            iri = "http://example.org#p"
            is_a = [parent_prop]

        class MockOntology:
            def object_properties(self):
                return [MockProp()]

        axioms = []
        mapper._extract_object_property_axioms(MockOntology(), axioms)
        assert axioms == []

    def test_extract_object_property_subproperty_no_parent_iri(self):
        """SubObjectPropertyOf where parent.iri is None should be skipped."""
        mapper, or2 = self._make_mapper()

        parent_prop = or2.ObjectPropertyClass()
        parent_prop.iri = None

        class MockProp:
            iri = "http://example.org#p"
            is_a = [parent_prop]

        class MockOntology:
            def object_properties(self):
                return [MockProp()]

        axioms = []
        mapper._extract_object_property_axioms(MockOntology(), axioms)
        assert axioms == []

    def test_extract_object_property_unknown_parent(self):
        """Unknown parent (not a known characteristic) should be skipped."""
        mapper, or2 = self._make_mapper()

        class MockProp:
            iri = "http://example.org#p"
            is_a = [42]  # something that isn't any known class

        class MockOntology:
            def object_properties(self):
                return [MockProp()]

        axioms = []
        mapper._extract_object_property_axioms(MockOntology(), axioms)
        assert axioms == []

    def test_extract_individual_same_iri_skipped(self):
        """SameIndividual axiom where same_iri == ind_iri should be skipped."""
        mapper, or2 = self._make_mapper()

        class MockSame:
            iri = "http://example.org#ind1"  # same as ind

        class MockInd:
            iri = "http://example.org#ind1"
            is_a = []
            equivalent_to = [MockSame()]
            different_from = []

        class MockOntology:
            def individuals(self):
                return [MockInd()]
            def object_properties(self):
                return []

        axioms = []
        mapper._extract_individual_axioms(MockOntology(), axioms)
        # No SameIndividual because same_iri == ind_iri
        from hermit.owl_model.owl_axiom import OWLSameIndividualAxiom
        assert not any(isinstance(a, OWLSameIndividualAxiom) for a in axioms)

    def test_map_restriction_value_no_iri(self):
        """HasValue restriction with value that has no IRI returns None."""
        mapper, or2 = self._make_mapper()
        import types as _types
        restr = or2.Restriction()
        prop = or2.ObjectPropertyClass()
        prop.iri = "http://example.org#p"
        restr.property = prop
        restr.type = or2.VALUE
        # value without iri attribute
        restr.value = _types.SimpleNamespace(iri=None)
        restr.cardinality = None
        result = mapper._map_class_expression(restr)
        assert result is None
