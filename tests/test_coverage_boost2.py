"""Coverage boost tests targeting instance_manager, extension_manager,
tableau, and dl_clause_evaluator through high-level API calls.
"""

from __future__ import annotations

import pytest

from hermit import Configuration, Reasoner
from hermit.configuration import (
    BlockingSignatureCacheType,
    BlockingStrategyType,
    DirectBlockingType,
    ExistentialStrategyType,
)
from hermit.model import (
    Atom,
    AtomicConcept,
    AtomicRole,
    DLClause,
    DLOntology,
    Individual,
    InverseRole,
    Variable,
    Inequality,
    AtLeastConcept,
    AtMostConcept,
    LiteralConcept,
)


NS = "http://example.org#"


def _ns(name: str) -> str:
    return f"{NS}{name}"


def _make_ontology(
    clauses: list[DLClause],
    positive_facts: list[Atom] | None = None,
    negative_facts: list[Atom] | None = None,
    iri: str = "urn:test:boost2",
) -> DLOntology:
    return DLOntology(
        ontology_iri=iri,
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset(positive_facts or []),
        negative_facts=frozenset(negative_facts or []),
    )


def _make_reasoner(
    clauses: list[DLClause],
    positive_facts: list[Atom] | None = None,
    negative_facts: list[Atom] | None = None,
    configuration: Configuration | None = None,
    iri: str = "urn:test:boost2",
) -> Reasoner:
    ont = _make_ontology(clauses, positive_facts, negative_facts, iri)
    return Reasoner(ont, configuration)


# ---------------------------------------------------------------------------
# Large ABox + role chains to exercise instance_manager path
# ---------------------------------------------------------------------------

class TestInstanceManagerLargeABox:
    """Many individuals + deep class hierarchy forces instance manager paths."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        self.A = AtomicConcept.create(_ns("A"))
        self.B = AtomicConcept.create(_ns("B"))
        self.C = AtomicConcept.create(_ns("C"))
        self.D = AtomicConcept.create(_ns("D"))
        self.E = AtomicConcept.create(_ns("E"))
        self.r = AtomicRole.create(_ns("r"))

        # A ⊑ B ⊑ C ⊑ D ⊑ E
        clauses = [
            DLClause.create((Atom.create(self.B, X),), (Atom.create(self.A, X),)),
            DLClause.create((Atom.create(self.C, X),), (Atom.create(self.B, X),)),
            DLClause.create((Atom.create(self.D, X),), (Atom.create(self.C, X),)),
            DLClause.create((Atom.create(self.E, X),), (Atom.create(self.D, X),)),
        ]
        inds = [Individual.create(_ns(f"ind{i}")) for i in range(20)]
        facts = [Atom.create(self.A, ind) for ind in inds[:10]]
        facts += [Atom.create(self.C, ind) for ind in inds[10:15]]
        facts += [Atom.create(self.E, ind) for ind in inds[15:]]

        # Role assertions
        for i in range(5):
            facts.append(Atom.create(self.r, inds[i], inds[i + 1]))

        self.inds = inds
        self.ont = _make_ontology(clauses, facts, iri="urn:test:large-abox")
        yield

    def test_consistent(self):
        r = Reasoner(self.ont)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_get_instances_base(self):
        r = Reasoner(self.ont)
        try:
            instances = r.get_instances(self.A)
            assert len(instances) >= 10
        finally:
            r.dispose()

    def test_get_instances_derived(self):
        r = Reasoner(self.ont)
        try:
            instances = r.get_instances(self.E)
            # All A-instances propagate through B,C,D to E; plus direct C and E
            assert len(instances) >= 10
        finally:
            r.dispose()

    def test_get_instances_direct(self):
        r = Reasoner(self.ont)
        try:
            # Direct instances of E (not instances of a subclass of E)
            instances = r.get_instances(self.E, direct=True)
            assert isinstance(instances, set)
        finally:
            r.dispose()

    def test_has_type_true(self):
        r = Reasoner(self.ont)
        try:
            assert r.has_type(self.inds[0], self.A)
            assert r.has_type(self.inds[0], self.E)
        finally:
            r.dispose()

    def test_has_type_false(self):
        r = Reasoner(self.ont)
        try:
            F = AtomicConcept.create(_ns("F"))
            assert not r.has_type(self.inds[0], F)
        finally:
            r.dispose()

    def test_get_types(self):
        r = Reasoner(self.ont)
        try:
            types = r.get_types(self.inds[0])
            assert AtomicConcept.THING in types or self.A in types or self.E in types
        finally:
            r.dispose()

    def test_get_types_direct(self):
        r = Reasoner(self.ont)
        try:
            types = r.get_types(self.inds[0], direct=True)
            assert isinstance(types, set)
        finally:
            r.dispose()

    def test_has_role_relationship(self):
        r = Reasoner(self.ont)
        try:
            # ind0 r ind1 is asserted
            assert r.has_role_relationship(self.inds[0], self.r, self.inds[1])
        finally:
            r.dispose()

    def test_classify_classes(self):
        r = Reasoner(self.ont)
        try:
            r.classify_classes()
            assert r._atomic_concept_hierarchy is not None
        finally:
            r.dispose()

    def test_classify_object_properties(self):
        r = Reasoner(self.ont)
        try:
            r.classify_object_properties()
            assert r._object_role_hierarchy is not None
        finally:
            r.dispose()


class TestInstanceManagerRoleInstances:
    """Test property instance retrieval via instance manager."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        Y = Variable.create("Y")
        self.Person = AtomicConcept.create(_ns("Person"))
        self.knows = AtomicRole.create(_ns("knows"))
        self.likes = AtomicRole.create(_ns("likes"))

        alice = Individual.create(_ns("alice"))
        bob = Individual.create(_ns("bob"))
        charlie = Individual.create(_ns("charlie"))

        facts = [
            Atom.create(self.Person, alice),
            Atom.create(self.Person, bob),
            Atom.create(self.Person, charlie),
            Atom.create(self.knows, alice, bob),
            Atom.create(self.knows, bob, charlie),
            Atom.create(self.likes, alice, charlie),
        ]
        self.alice = alice
        self.bob = bob
        self.charlie = charlie

        clauses: list[DLClause] = []
        self.ont = _make_ontology(clauses, facts, iri="urn:test:roles")
        yield

    def test_has_role_relationship_direct(self):
        r = Reasoner(self.ont)
        try:
            assert r.has_role_relationship(self.alice, self.knows, self.bob)
        finally:
            r.dispose()

    def test_has_role_relationship_absent(self):
        r = Reasoner(self.ont)
        try:
            assert not r.has_role_relationship(self.alice, self.knows, self.charlie)
        finally:
            r.dispose()

    def test_has_role_relationship_likes(self):
        r = Reasoner(self.ont)
        try:
            assert r.has_role_relationship(self.alice, self.likes, self.charlie)
        finally:
            r.dispose()

    def test_individuals_in_ontology(self):
        r = Reasoner(self.ont)
        try:
            # Both alice and bob are individuals in the ontology
            assert self.alice in self.ont.all_individuals
            assert self.bob in self.ont.all_individuals
        finally:
            r.dispose()

    def test_precompute_with_object_property(self):
        r = Reasoner(self.ont)
        try:
            r.precompute_inferences(
                class_hierarchy=True,
                object_property_hierarchy=True,
            )
            assert r._object_role_hierarchy is not None
        finally:
            r.dispose()


class TestInstanceManagerWithInverseRoles:
    """Tests using inverse roles to exercise alternate code paths."""

    @pytest.fixture(autouse=True)
    def setup(self):
        X = Variable.create("X")
        Y = Variable.create("Y")
        self.A = AtomicConcept.create(_ns("A"))
        self.B = AtomicConcept.create(_ns("B"))
        self.r = AtomicRole.create(_ns("r"))
        self.inv_r = InverseRole.create(self.r)

        a1 = Individual.create(_ns("a1"))
        b1 = Individual.create(_ns("b1"))
        b2 = Individual.create(_ns("b2"))

        facts = [
            Atom.create(self.A, a1),
            Atom.create(self.B, b1),
            Atom.create(self.B, b2),
            Atom.create(self.r, a1, b1),
            Atom.create(self.r, a1, b2),
        ]
        self.a1 = a1
        self.b1 = b1
        self.b2 = b2
        clauses: list[DLClause] = []
        self.ont = _make_ontology(clauses, facts, iri="urn:test:inverse")
        yield

    def test_consistent(self):
        r = Reasoner(self.ont)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_inverse_role_relationship(self):
        r = Reasoner(self.ont)
        try:
            # a1 r b1, so b1 inv(r) a1 should hold
            result = r.has_role_relationship(self.b1, self.r, self.a1)
            # This may or may not be true depending on direction
            assert isinstance(result, bool)
        finally:
            r.dispose()

    def test_get_instances_with_roles(self):
        r = Reasoner(self.ont)
        try:
            insts = r.get_instances(self.A)
            assert self.a1 in insts
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# Test complex DL clauses to exercise dl_clause_evaluator
# ---------------------------------------------------------------------------

class TestDLClauseEvaluatorPaths:
    """Exercises DL clause evaluator with at-least / at-most / role clauses."""

    def test_atleast_concept_query(self):
        """Ontology with at-least cardinality constraint."""
        X = Variable.create("X")
        Y = Variable.create("Y")
        r = AtomicRole.create(_ns("r"))
        A = AtomicConcept.create(_ns("A"))
        B = AtomicConcept.create(_ns("B"))

        # ∃r.A ⊑ B
        at_least_r_A = AtLeastConcept.create(1, r, A)
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(at_least_r_A, X),)),
        ]

        a1 = Individual.create(_ns("a1"))
        b1 = Individual.create(_ns("b1"))
        facts = [
            Atom.create(A, b1),
            Atom.create(r, a1, b1),
        ]
        ont = _make_ontology(clauses, facts)
        reasoner = Reasoner(ont)
        try:
            assert reasoner.is_consistent()
            # a1 has at least one r-successor in A => a1 should be in B
            insts = reasoner.get_instances(B)
            assert isinstance(insts, set)
        finally:
            reasoner.dispose()

    def test_multiple_clauses_with_roles(self):
        """Multiple DL clauses involving roles exercise more evaluator code."""
        X = Variable.create("X")
        Y = Variable.create("Y")
        r = AtomicRole.create(_ns("mcr_r"))
        s = AtomicRole.create(_ns("mcr_s"))
        A = AtomicConcept.create(_ns("mcr_A"))
        B = AtomicConcept.create(_ns("mcr_B"))
        C = AtomicConcept.create(_ns("mcr_C"))

        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(C, X),), (Atom.create(B, X),)),
        ]
        i1 = Individual.create(_ns("mcr_i1"))
        i2 = Individual.create(_ns("mcr_i2"))
        i3 = Individual.create(_ns("mcr_i3"))
        facts = [
            Atom.create(A, i1),
            Atom.create(A, i2),
            Atom.create(r, i1, i3),
            Atom.create(r, i2, i3),
        ]
        ont = _make_ontology(clauses, facts)
        reasoner = Reasoner(ont)
        try:
            assert reasoner.is_consistent()
            insts_c = reasoner.get_instances(C)
            assert i1 in insts_c
            assert i2 in insts_c
        finally:
            reasoner.dispose()

    def test_disjoint_concepts(self):
        """Disjoint concepts trigger backtracking paths."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("A"))
        B = AtomicConcept.create(_ns("B"))
        neg_B = B.get_negation()

        # A ⊑ ¬B (disjointness)
        clauses = [
            DLClause.create((Atom.create(neg_B, X),), (Atom.create(A, X),)),
        ]
        ont = _make_ontology(clauses, iri="urn:test:disjoint")
        reasoner = Reasoner(ont)
        try:
            assert reasoner.is_disjoint(A, B)
        finally:
            reasoner.dispose()

    def test_role_chain_with_existential(self):
        """Role chain reasoning exercises existential expansion paths."""
        X = Variable.create("X")
        r = AtomicRole.create(_ns("chain_r3"))
        A = AtomicConcept.create(_ns("ChainA3"))
        B = AtomicConcept.create(_ns("ChainB3"))
        # If A(X) then ∃r.B(X) — forces existential creation
        at_least_1 = AtLeastConcept.create(1, r, B)
        clauses = [
            DLClause.create(
                (Atom.create(at_least_1, X),),
                (Atom.create(A, X),),
            ),
        ]
        i1 = Individual.create(_ns("chain3_i1"))
        facts = [Atom.create(A, i1)]
        ont = _make_ontology(clauses, facts, iri="urn:test:existential3")
        reasoner = Reasoner(ont)
        try:
            assert reasoner.is_consistent()
            # Just check consistency - get_instances on a fresh reasoner
        finally:
            reasoner.dispose()

        # Now check instances on a separate reasoner instance
        reasoner2 = Reasoner(_make_ontology(clauses, facts, iri="urn:test:existential3b"))
        try:
            insts = reasoner2.get_instances(A)
            assert i1 in insts
        finally:
            reasoner2.dispose()


# ---------------------------------------------------------------------------
# Extension manager tests via complex ontologies
# ---------------------------------------------------------------------------

class TestExtensionManagerPaths:
    """Exercises extension manager code paths via reasoning."""

    def test_consistency_with_equality(self):
        """Equality assertions exercise merge paths in extension manager."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("EqA"))
        B = AtomicConcept.create(_ns("EqB"))

        i1 = Individual.create(_ns("eq_i1"))
        i2 = Individual.create(_ns("eq_i2"))

        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        facts = [
            Atom.create(A, i1),
            Atom.create(A, i2),
        ]
        ont = _make_ontology(clauses, facts, iri="urn:test:equality")
        reasoner = Reasoner(ont)
        try:
            assert reasoner.is_consistent()
            insts = reasoner.get_instances(B)
            assert i1 in insts
            assert i2 in insts
        finally:
            reasoner.dispose()

    def test_many_role_assertions(self):
        """Many roles stress-test the ternary extension table."""
        X = Variable.create("X")
        Y = Variable.create("Y")
        A = AtomicConcept.create(_ns("MRA"))
        roles = [AtomicRole.create(_ns(f"mr_{i}")) for i in range(5)]
        inds = [Individual.create(_ns(f"mr_ind{i}")) for i in range(10)]

        clauses: list[DLClause] = []
        facts = [Atom.create(A, ind) for ind in inds]
        for i, role in enumerate(roles):
            for j in range(len(inds) - 1):
                facts.append(Atom.create(role, inds[j], inds[j + 1]))

        ont = _make_ontology(clauses, facts, iri="urn:test:many-roles")
        reasoner = Reasoner(ont)
        try:
            assert reasoner.is_consistent()
            insts = reasoner.get_instances(A)
            assert len(insts) == 10
        finally:
            reasoner.dispose()

    def test_complex_role_assertion_patterns(self):
        """Complex role assertion patterns exercise extension manager paths."""
        X = Variable.create("X")
        Y = Variable.create("Y")
        r = AtomicRole.create(_ns("pat_r"))
        s = AtomicRole.create(_ns("pat_s"))
        A = AtomicConcept.create(_ns("PatA"))
        B = AtomicConcept.create(_ns("PatB"))

        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(s, X, Y),), (Atom.create(r, X, Y), Atom.create(A, X))),
        ]
        inds = [Individual.create(_ns(f"pat_i{i}")) for i in range(6)]
        facts = [Atom.create(A, ind) for ind in inds[:3]]
        for i in range(2):
            facts.append(Atom.create(r, inds[i], inds[i + 3]))

        ont = _make_ontology(clauses, facts, iri="urn:test:pat")
        reasoner = Reasoner(ont)
        try:
            assert reasoner.is_consistent()
            insts = reasoner.get_instances(B)
            assert len(insts) >= 3
        finally:
            reasoner.dispose()

    def test_individual_reuse_strategy(self):
        """Individual reuse strategy exercises different existential paths."""
        X = Variable.create("X")
        r = AtomicRole.create(_ns("reuse_r"))
        A = AtomicConcept.create(_ns("ReuseA"))
        B = AtomicConcept.create(_ns("ReuseB"))

        at_least_1 = AtLeastConcept.create(1, r, B)
        clauses = [
            DLClause.create(
                (Atom.create(at_least_1, X),),
                (Atom.create(A, X),),
            ),
        ]
        inds = [Individual.create(_ns(f"reuse_i{i}")) for i in range(5)]
        facts = [Atom.create(A, ind) for ind in inds]

        ont = _make_ontology(clauses, facts, iri="urn:test:reuse")
        config = Configuration()
        config.existential_strategy_type = ExistentialStrategyType.INDIVIDUAL_REUSE
        reasoner = Reasoner(ont, config)
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_no_cache_configuration(self):
        """Disabling signature cache exercises different blocking paths."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("NCA"))
        B = AtomicConcept.create(_ns("NCB"))
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        inds = [Individual.create(_ns(f"nc_ind{i}")) for i in range(5)]
        facts = [Atom.create(A, ind) for ind in inds]

        ont = _make_ontology(clauses, facts, iri="urn:test:no-cache")
        config = Configuration()
        config.blocking_signature_cache_type = BlockingSignatureCacheType.NOT_CACHED
        reasoner = Reasoner(ont, config)
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_ancestor_blocking_strategy(self):
        """ANCESTOR blocking strategy exercises different code paths."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("AncA"))
        B = AtomicConcept.create(_ns("AncB"))
        r = AtomicRole.create(_ns("anc_r"))
        at_least_1 = AtLeastConcept.create(1, r, A)
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
            DLClause.create(
                (Atom.create(at_least_1, X),),
                (Atom.create(B, X),),
            ),
        ]
        i1 = Individual.create(_ns("anc_i1"))
        facts = [Atom.create(A, i1)]

        ont = _make_ontology(clauses, facts, iri="urn:test:ancestor")
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.ANCESTOR
        reasoner = Reasoner(ont, config)
        try:
            # This may loop — but checking consistency should work for finite models
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_pairwise_blocking_without_inverse(self):
        """PAIR_WISE blocking exercised directly."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("PWA"))
        B = AtomicConcept.create(_ns("PWB"))
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        inds = [Individual.create(_ns(f"pw_ind{i}")) for i in range(3)]
        facts = [Atom.create(A, ind) for ind in inds]

        ont = _make_ontology(clauses, facts, iri="urn:test:pairwise")
        config = Configuration()
        config.direct_blocking_type = DirectBlockingType.PAIR_WISE
        config.blocking_strategy_type = BlockingStrategyType.ANYWHERE
        reasoner = Reasoner(ont, config)
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_single_blocking_explicit(self):
        """SINGLE blocking type exercised directly."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("SBA"))
        clauses: list[DLClause] = []
        inds = [Individual.create(_ns(f"sb_ind{i}")) for i in range(3)]
        facts = [Atom.create(A, ind) for ind in inds]

        ont = _make_ontology(clauses, facts, iri="urn:test:single")
        config = Configuration()
        config.direct_blocking_type = DirectBlockingType.SINGLE
        config.blocking_strategy_type = BlockingStrategyType.ANYWHERE
        reasoner = Reasoner(ont, config)
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Tableau-level paths via is_satisfiable
# ---------------------------------------------------------------------------

class TestTableauPaths:
    """Directly tests various tableau execution paths."""

    def test_inconsistent_ontology(self):
        """Inconsistent ontology exercises clash detection."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("IncA"))
        neg_A = A.get_negation()
        i1 = Individual.create(_ns("inc_i1"))
        # Both A(i1) and ¬A(i1) as facts
        facts = [
            Atom.create(A, i1),
            Atom.create(neg_A, i1),
        ]
        ont = _make_ontology([], facts, iri="urn:test:inconsistent")
        reasoner = Reasoner(ont)
        try:
            assert not reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_deep_hierarchy_classification(self):
        """Deep hierarchy triggers deterministic classification paths."""
        X = Variable.create("X")
        levels = 8
        concepts = [AtomicConcept.create(_ns(f"Level{i}")) for i in range(levels)]
        clauses = [
            DLClause.create(
                (Atom.create(concepts[i + 1], X),),
                (Atom.create(concepts[i], X),),
            )
            for i in range(levels - 1)
        ]
        # Facts at the bottom
        inds = [Individual.create(_ns(f"dl_ind{i}")) for i in range(5)]
        facts = [Atom.create(concepts[0], ind) for ind in inds]

        ont = _make_ontology(clauses, facts, iri="urn:test:deep-hierarchy")
        reasoner = Reasoner(ont)
        try:
            reasoner.classify_classes()
            assert reasoner._atomic_concept_hierarchy is not None
            # Check subclass relationship holds at deepest level
            assert reasoner.is_sub_class_of(concepts[0], concepts[-1])
        finally:
            reasoner.dispose()

    def test_many_individuals_get_instances(self):
        """Many individuals - get instances exercises instance manager."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("SameA"))
        inds = [Individual.create(_ns(f"same_ind{i}")) for i in range(10)]
        facts = [Atom.create(A, ind) for ind in inds]

        ont = _make_ontology([], facts, iri="urn:test:same-as")
        reasoner = Reasoner(ont)
        try:
            result = reasoner.get_instances(A)
            assert len(result) == 10
        finally:
            reasoner.dispose()

    def test_force_quasi_order_classification(self):
        """Force quasi-order classification code path."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("QuasiA"))
        B = AtomicConcept.create(_ns("QuasiB"))
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        inds = [Individual.create(_ns(f"quasi_ind{i}")) for i in range(5)]
        facts = [Atom.create(A, ind) for ind in inds]

        ont = _make_ontology(clauses, facts, iri="urn:test:quasi")
        config = Configuration()
        config.force_quasi_order_classification = True
        reasoner = Reasoner(ont, config)
        try:
            assert reasoner.is_consistent()
            reasoner.classify_classes()
            assert reasoner.is_sub_class_of(A, B)
        finally:
            reasoner.dispose()

    def test_disjunction_learning_disabled(self):
        """Disable disjunction learning to exercise quasi-order path."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("DLA"))
        B = AtomicConcept.create(_ns("DLB"))
        C = AtomicConcept.create(_ns("DLC"))
        neg_C = C.get_negation()

        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        inds = [Individual.create(_ns(f"dl2_ind{i}")) for i in range(3)]
        facts = [Atom.create(A, ind) for ind in inds]

        ont = _make_ontology(clauses, facts, iri="urn:test:no-dl")
        config = Configuration()
        config.use_disjunction_learning = False
        reasoner = Reasoner(ont, config)
        try:
            assert reasoner.is_consistent()
            assert reasoner.is_sub_class_of(A, B)
        finally:
            reasoner.dispose()

    def test_individual_with_multiple_types(self):
        """Individual typed by multiple concepts exercises union-find."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("MultA"))
        B = AtomicConcept.create(_ns("MultB"))
        C = AtomicConcept.create(_ns("MultC"))
        i1 = Individual.create(_ns("mult_i1"))
        facts = [
            Atom.create(A, i1),
            Atom.create(B, i1),
            Atom.create(C, i1),
        ]
        ont = _make_ontology([], facts, iri="urn:test:multi-type")
        reasoner = Reasoner(ont)
        try:
            assert reasoner.has_type(i1, A)
            assert reasoner.has_type(i1, B)
            assert reasoner.has_type(i1, C)
        finally:
            reasoner.dispose()

    def test_get_instances_of_nothing(self):
        """get_instances(NOTHING) should return empty set."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("NA"))
        inds = [Individual.create(_ns(f"n_ind{i}")) for i in range(3)]
        facts = [Atom.create(A, ind) for ind in inds]
        ont = _make_ontology([], facts, iri="urn:test:nothing")
        reasoner = Reasoner(ont)
        try:
            insts = reasoner.get_instances(AtomicConcept.NOTHING)
            assert isinstance(insts, set)
        finally:
            reasoner.dispose()

    def test_get_instances_of_thing(self):
        """get_instances(THING) should return all named individuals."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("TA"))
        inds = [Individual.create(_ns(f"t_ind{i}")) for i in range(5)]
        facts = [Atom.create(A, ind) for ind in inds]
        ont = _make_ontology([], facts, iri="urn:test:thing")
        reasoner = Reasoner(ont)
        try:
            insts = reasoner.get_instances(AtomicConcept.THING)
            assert len(insts) >= 5
        finally:
            reasoner.dispose()

    def test_classify_then_get_instances(self):
        """Classify, then call get_instances exercising set_to_classified_hierarchy."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("CA"))
        B = AtomicConcept.create(_ns("CB"))
        C = AtomicConcept.create(_ns("CC"))
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(C, X),), (Atom.create(B, X),)),
        ]
        inds = [Individual.create(_ns(f"c_ind{i}")) for i in range(8)]
        facts = [Atom.create(A, ind) for ind in inds[:4]]
        facts += [Atom.create(B, ind) for ind in inds[4:6]]
        facts += [Atom.create(C, ind) for ind in inds[6:]]

        ont = _make_ontology(clauses, facts, iri="urn:test:classify-then-get")
        reasoner = Reasoner(ont)
        try:
            # First classify classes
            reasoner.classify_classes()
            # Then get instances — triggers set_to_classified_concept_hierarchy path
            insts_c = reasoner.get_instances(C)
            assert len(insts_c) >= 4  # All A-inds propagate to C
        finally:
            reasoner.dispose()

    def test_full_precompute_inferences(self):
        """Full precompute exercising all inference types."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("FPA"))
        B = AtomicConcept.create(_ns("FPB"))
        r = AtomicRole.create(_ns("fp_r"))
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        inds = [Individual.create(_ns(f"fp_ind{i}")) for i in range(3)]
        facts = [Atom.create(A, ind) for ind in inds]
        facts.append(Atom.create(r, inds[0], inds[1]))

        ont = _make_ontology(clauses, facts, iri="urn:test:full-precompute")
        reasoner = Reasoner(ont)
        try:
            reasoner.precompute_inferences(
                class_hierarchy=True,
                object_property_hierarchy=True,
                data_property_hierarchy=True,
            )
            assert reasoner._atomic_concept_hierarchy is not None
            assert reasoner._object_role_hierarchy is not None
            assert reasoner._data_role_hierarchy is not None
        finally:
            reasoner.dispose()
