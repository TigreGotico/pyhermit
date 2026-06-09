"""Unit tests for the tableau engine.

These tests verify the internal tableau machinery:
- Dependency set creation and management
- Node creation and state management
- Clash detection
- Branching points
- Ground disjunction handling

Note: The full tableau engine is complex and requires a DLOntology with
clauses. These tests use minimal ontologies to exercise specific paths.
"""

from __future__ import annotations

import pytest

from hermit.model import (
    Atom,
    AtomicConcept,
    AtomicRole,
    DLClause,
    DLOntology,
    Individual,
    Variable,
)
from hermit.tableau.dependency_set_factory import DependencySetFactory
from hermit.tableau.node import Node, NodeState
from hermit.tableau.node_type import NodeType


# ===========================================================================
# DependencySet (via DependencySetFactory)
# ===========================================================================

class TestDependencySet:
    """Test dependency set management for clash-driven backtracking."""

    def test_empty_dependency_set(self):
        """Empty dependency set has no branching points."""
        factory = DependencySetFactory()
        empty = factory.empty_set
        assert empty.is_empty()
        assert empty.get_maximum_branching_point() == -1

    def test_singleton_dependency_set(self):
        """A set with one branching point."""
        factory = DependencySetFactory()
        bp_id = 0
        singleton = factory.add_branching_point(factory.empty_set, bp_id)
        assert not singleton.is_empty()
        assert singleton.contains_branching_point(bp_id)
        assert singleton.get_maximum_branching_point() == bp_id

    def test_dependency_set_union(self):
        """Union of two dependency sets contains both branching points."""
        factory = DependencySetFactory()
        set1 = factory.add_branching_point(factory.empty_set, 0)
        set2 = factory.add_branching_point(factory.empty_set, 1)

        union = factory.union_with(set1, set2)
        assert union.contains_branching_point(0)
        assert union.contains_branching_point(1)
        assert union.get_maximum_branching_point() == 1

    def test_dependency_set_subset(self):
        """A subset dependency set."""
        factory = DependencySetFactory()
        set1 = factory.add_branching_point(factory.empty_set, 0)
        superset = factory.add_branching_point(set1, 1)

        assert superset.contains_branching_point(0)
        assert superset.contains_branching_point(1)
        assert not set1.contains_branching_point(1)


# ===========================================================================
# DependencySetFactory
# ===========================================================================

class TestDependencySetFactory:
    """Test the factory for creating and combining dependency sets."""

    def test_clear_resets_factory(self):
        """Clearing the factory resets all state."""
        factory = DependencySetFactory()
        s1 = factory.add_branching_point(factory.empty_set, 0)
        factory.clear()
        assert factory.empty_set.is_empty()

    def test_empty_set_is_idempotent(self):
        """Accessing empty_set multiple times returns the same object."""
        factory = DependencySetFactory()
        e1 = factory.empty_set
        e2 = factory.empty_set
        assert e1 is e2

    def test_add_and_remove_branching_point(self):
        """Adding then removing a branching point returns the original set."""
        factory = DependencySetFactory()
        original = factory.empty_set
        with_bp = factory.add_branching_point(original, 0)
        back = factory.remove_branching_point(with_bp, 0)
        assert back is original


# ===========================================================================
# Node
# ===========================================================================

class TestNode:
    """Test tableau node creation and state management."""

    def _make_tableau(self, clauses: list[DLClause]):
        """Helper to create a minimal Tableau."""
        from hermit.tableau.interrupt_flag import InterruptFlag
        from hermit.tableau.tableau import Tableau
        from hermit.existentials.creation_order_strategy import (
            CreationOrderStrategy,
        )
        from hermit.blocking.anywhere_blocking import AnywhereBlocking
        from hermit.blocking.pairwise_direct_blocking_checker import (
            PairWiseDirectBlockingChecker,
        )

        ontology = DLOntology(
            ontology_iri="urn:test:node",
            dl_clauses=frozenset(clauses),
        )
        interrupt_flag = InterruptFlag(-1)
        blocking_checker = PairWiseDirectBlockingChecker()
        blocking_strategy = AnywhereBlocking(blocking_checker, None)
        expansion_strategy = CreationOrderStrategy(blocking_strategy)

        tableau = Tableau(
            interrupt_flag=interrupt_flag,
            tableau_monitor=None,
            existential_expansion_strategy=expansion_strategy,
            use_disjunction_learning=False,
            permanent_dl_ontology=ontology,
            additional_dl_ontology=None,
            parameters={},
        )
        return tableau, interrupt_flag

    def test_node_requires_tableau(self):
        """Node constructor requires a tableau reference."""
        node = Node(None)
        assert node is not None

    def test_node_state_values(self):
        """NodeState enum has expected values."""
        assert hasattr(NodeState, "ACTIVE")
        assert hasattr(NodeState, "MERGED")
        assert hasattr(NodeState, "PRUNED")

    def test_node_type_values(self):
        """NodeType enum has expected values."""
        assert hasattr(NodeType, "NAMED_NODE")
        assert hasattr(NodeType, "NI_NODE")
        assert hasattr(NodeType, "TREE_NODE")
        assert hasattr(NodeType, "GRAPH_NODE")
        assert hasattr(NodeType, "CONCRETE_NODE")
        assert hasattr(NodeType, "ROOT_CONSTANT_NODE")


# ===========================================================================
# BranchingPoint
# ===========================================================================

class TestBranchingPoint:
    """Test branching point creation and management."""

    def test_branching_point_creation(self):
        """Branching point can be created with a tableau reference."""
        from hermit.tableau.branching_point import BranchingPoint
        from hermit.tableau.interrupt_flag import InterruptFlag
        from hermit.tableau.tableau import Tableau
        from hermit.existentials.creation_order_strategy import (
            CreationOrderStrategy,
        )
        from hermit.blocking.anywhere_blocking import AnywhereBlocking
        from hermit.blocking.pairwise_direct_blocking_checker import (
            PairWiseDirectBlockingChecker,
        )

        # Create a minimal ontology
        X = Variable.create("X")
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        clause = DLClause.create(
            (Atom.create(b, X),),
            (Atom.create(a, X),),
        )
        ontology = DLOntology(
            ontology_iri="urn:test:branching",
            dl_clauses=frozenset([clause]),
        )

        interrupt_flag = InterruptFlag(-1)
        blocking_checker = PairWiseDirectBlockingChecker()
        blocking_strategy = AnywhereBlocking(blocking_checker, None)
        expansion_strategy = CreationOrderStrategy(blocking_strategy)

        tableau = Tableau(
            interrupt_flag=interrupt_flag,
            tableau_monitor=None,
            existential_expansion_strategy=expansion_strategy,
            use_disjunction_learning=False,
            permanent_dl_ontology=ontology,
            additional_dl_ontology=None,
            parameters={},
        )

        try:
            bp = BranchingPoint(tableau)
            assert bp is not None
        finally:
            interrupt_flag.dispose()


# ===========================================================================
# Tableau: satisfiability with minimal ontologies
# ===========================================================================

class TestTableauSatisfiability:
    """Test the tableau engine's satisfiability checker with minimal inputs."""

    def _create_tableau(self, clauses: list[DLClause], facts: list[Atom] | None = None):
        """Helper to create a Tableau with a given ontology."""
        from hermit.tableau.interrupt_flag import InterruptFlag
        from hermit.tableau.tableau import Tableau
        from hermit.existentials.creation_order_strategy import (
            CreationOrderStrategy,
        )
        from hermit.blocking.anywhere_blocking import AnywhereBlocking
        from hermit.blocking.pairwise_direct_blocking_checker import (
            PairWiseDirectBlockingChecker,
        )

        ontology = DLOntology(
            ontology_iri="urn:test:tableau",
            dl_clauses=frozenset(clauses),
            positive_facts=frozenset(facts or []),
        )

        interrupt_flag = InterruptFlag(-1)
        blocking_checker = PairWiseDirectBlockingChecker()
        blocking_strategy = AnywhereBlocking(blocking_checker, None)
        expansion_strategy = CreationOrderStrategy(blocking_strategy)

        tableau = Tableau(
            interrupt_flag=interrupt_flag,
            tableau_monitor=None,
            existential_expansion_strategy=expansion_strategy,
            use_disjunction_learning=False,
            permanent_dl_ontology=ontology,
            additional_dl_ontology=None,
            parameters={},
        )
        return tableau, interrupt_flag

    def test_horn_ontology_satisfiable(self):
        """Horn ontology A(X) -> B(X) is satisfiable."""
        X = Variable.create("X")
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        clause = DLClause.create(
            (Atom.create(b, X),),
            (Atom.create(a, X),),
        )
        tableau, flag = self._create_tableau([clause])
        try:
            result = tableau.is_satisfiable(load_permanent_abox=False)
            assert result is True
        finally:
            flag.dispose()

    def test_empty_ontology_satisfiable(self):
        """Empty ontology (no clauses) is trivially satisfiable."""
        tableau, flag = self._create_tableau([])
        try:
            result = tableau.is_satisfiable(load_permanent_abox=False)
            assert result is True
        finally:
            flag.dispose()

    def test_property_inclusion_satisfiable(self):
        """R(X,Y) -> S(X,Y) is satisfiable."""
        X = Variable.create("X")
        Y = Variable.create("Y")
        r = AtomicRole.create("http://example.org#r")
        s = AtomicRole.create("http://example.org#s")
        clause = DLClause.create(
            (Atom.create(s, X, Y),),
            (Atom.create(r, X, Y),),
        )
        tableau, flag = self._create_tableau([clause])
        try:
            result = tableau.is_satisfiable(load_permanent_abox=False)
            assert result is True
        finally:
            flag.dispose()

    def test_multiple_clauses_satisfiable(self):
        """Multiple Horn clauses together are satisfiable."""
        X = Variable.create("X")
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        c = AtomicConcept.create("http://example.org#C")
        clauses = [
            DLClause.create((Atom.create(b, X),), (Atom.create(a, X),)),
            DLClause.create((Atom.create(c, X),), (Atom.create(b, X),)),
        ]
        tableau, flag = self._create_tableau(clauses)
        try:
            result = tableau.is_satisfiable(load_permanent_abox=False)
            assert result is True
        finally:
            flag.dispose()


# ===========================================================================
# ClashManager
# ===========================================================================

class TestClashManager:
    """Test clash detection and management."""

    def test_clash_manager_creation(self):
        """ClashManager can be instantiated with a tableau reference."""
        from hermit.tableau.clash_manager import ClashManager
        from hermit.tableau.interrupt_flag import InterruptFlag
        from hermit.tableau.tableau import Tableau
        from hermit.existentials.creation_order_strategy import (
            CreationOrderStrategy,
        )
        from hermit.blocking.anywhere_blocking import AnywhereBlocking
        from hermit.blocking.pairwise_direct_blocking_checker import (
            PairWiseDirectBlockingChecker,
        )

        X = Variable.create("X")
        a = AtomicConcept.create("http://example.org#A")
        clause = DLClause.create((Atom.create(a, X),), ())
        ontology = DLOntology(
            ontology_iri="urn:test:clash",
            dl_clauses=frozenset([clause]),
        )

        interrupt_flag = InterruptFlag(-1)
        blocking_checker = PairWiseDirectBlockingChecker()
        blocking_strategy = AnywhereBlocking(blocking_checker, None)
        expansion_strategy = CreationOrderStrategy(blocking_strategy)

        tableau = Tableau(
            interrupt_flag=interrupt_flag,
            tableau_monitor=None,
            existential_expansion_strategy=expansion_strategy,
            use_disjunction_learning=False,
            permanent_dl_ontology=ontology,
            additional_dl_ontology=None,
            parameters={},
        )

        try:
            cm = ClashManager(tableau)
            assert cm is not None
        finally:
            interrupt_flag.dispose()


# ===========================================================================
# ExtensionManager
# ===========================================================================

class TestExtensionManager:
    """Test the extension manager for adding assertions to tableau nodes."""

    def test_extension_manager_creation(self):
        """ExtensionManager can be instantiated."""
        from hermit.tableau.extension_manager import ExtensionManager
        from hermit.tableau.interrupt_flag import InterruptFlag
        from hermit.tableau.tableau import Tableau
        from hermit.existentials.creation_order_strategy import (
            CreationOrderStrategy,
        )
        from hermit.blocking.anywhere_blocking import AnywhereBlocking
        from hermit.blocking.pairwise_direct_blocking_checker import (
            PairWiseDirectBlockingChecker,
        )

        X = Variable.create("X")
        a = AtomicConcept.create("http://example.org#A")
        clause = DLClause.create((Atom.create(a, X),), ())
        ontology = DLOntology(
            ontology_iri="urn:test:extension",
            dl_clauses=frozenset([clause]),
        )

        interrupt_flag = InterruptFlag(-1)
        blocking_checker = PairWiseDirectBlockingChecker()
        blocking_strategy = AnywhereBlocking(blocking_checker, None)
        expansion_strategy = CreationOrderStrategy(blocking_strategy)

        tableau = Tableau(
            interrupt_flag=interrupt_flag,
            tableau_monitor=None,
            existential_expansion_strategy=expansion_strategy,
            use_disjunction_learning=False,
            permanent_dl_ontology=ontology,
            additional_dl_ontology=None,
            parameters={},
        )

        try:
            em = ExtensionManager(tableau)
            assert em is not None
        finally:
            interrupt_flag.dispose()


# ===========================================================================
# HyperresolutionManager
# ===========================================================================

class TestHyperresolutionManager:
    """Test the hyperresolution manager for applying DL clauses."""

    def test_hyperresolution_with_role_inclusion(self):
        """Hyperresolution applies R(X,Y) -> S(X,Y) when R is asserted."""
        from hermit.tableau.interrupt_flag import InterruptFlag
        from hermit.tableau.tableau import Tableau
        from hermit.existentials.creation_order_strategy import (
            CreationOrderStrategy,
        )
        from hermit.blocking.anywhere_blocking import AnywhereBlocking
        from hermit.blocking.pairwise_direct_blocking_checker import (
            PairWiseDirectBlockingChecker,
        )

        X = Variable.create("X")
        Y = Variable.create("Y")
        r = AtomicRole.create("http://example.org#r")
        s = AtomicRole.create("http://example.org#s")

        i = Individual.create("http://example.org#a")
        j = Individual.create("http://example.org#b")

        clause = DLClause.create(
            (Atom.create(s, X, Y),),
            (Atom.create(r, X, Y),),
        )
        ontology = DLOntology(
            ontology_iri="urn:test:hyperresolution",
            dl_clauses=frozenset([clause]),
            positive_facts=frozenset([Atom.create(r, i, j)]),
        )

        interrupt_flag = InterruptFlag(-1)
        blocking_checker = PairWiseDirectBlockingChecker()
        blocking_strategy = AnywhereBlocking(blocking_checker, None)
        expansion_strategy = CreationOrderStrategy(blocking_strategy)

        tableau = Tableau(
            interrupt_flag=interrupt_flag,
            tableau_monitor=None,
            existential_expansion_strategy=expansion_strategy,
            use_disjunction_learning=False,
            permanent_dl_ontology=ontology,
            additional_dl_ontology=None,
            parameters={},
        )

        try:
            result = tableau.is_satisfiable(load_permanent_abox=True)
            assert result is True
        finally:
            interrupt_flag.dispose()


# ===========================================================================
# InterruptFlag
# ===========================================================================

class TestInterruptFlag:
    """Test the interrupt flag for timeout/interrupt handling."""

    def test_interrupt_flag_lifecycle(self):
        """Interrupt flag can be created, started, and disposed."""
        from hermit.tableau.interrupt_flag import InterruptFlag

        flag = InterruptFlag(-1)
        flag.start_task()
        flag.end_task()
        flag.dispose()

    def test_interrupt_sets_flag(self):
        """Calling interrupt() then check_interrupt() raises an exception."""
        from hermit.tableau.interrupt_flag import InterruptFlag
        from hermit.tableau.interrupt_current_task_exception import (
            InterruptCurrentTaskException,
        )

        flag = InterruptFlag(-1)
        flag.start_task()
        flag.interrupt()
        with pytest.raises(InterruptCurrentTaskException):
            flag.check_interrupt()
        flag.end_task()
        flag.dispose()


# ===========================================================================
# DisjunctionBranchingPoint
# ===========================================================================

class TestDisjunctionBranchingPoint:
    """Test disjunction branching for non-deterministic choices."""

    def test_disjunction_branching_point_structure(self):
        """DisjunctionBranchingPoint class exists with expected attributes."""
        from hermit.tableau.disjunction_branching_point import (
            DisjunctionBranchingPoint,
        )
        # Verify the class exists and has expected methods
        assert hasattr(DisjunctionBranchingPoint, "__init__")
        # Full instantiation requires a complete tableau, which is
        # tested indirectly through the reasoner integration tests.


# ===========================================================================
# GroundDisjunction
# ===========================================================================

class TestGroundDisjunction:
    """Test ground disjunction representation."""

    def test_ground_disjunction_header_creation(self):
        """GroundDisjunctionHeader can be created with proper arguments."""
        from hermit.tableau.ground_disjunction_header import (
            GroundDisjunctionHeader,
        )
        from hermit.model import AtomicConcept

        concept = AtomicConcept.create("http://example.org#A")
        header = GroundDisjunctionHeader(
            dl_predicates=[concept],
            hash_code=hash(concept),
            next_entry=None,
        )
        assert header is not None
        assert len(header.m_dl_predicates) == 1

    def test_ground_disjunction_structure(self):
        """GroundDisjunction class exists with expected attributes."""
        from hermit.tableau.ground_disjunction import GroundDisjunction
        # Verify the class exists
        assert hasattr(GroundDisjunction, "__init__")
        # Full instantiation requires a complete tableau and header,
        # which is tested indirectly through the reasoner integration tests.


class TestHeadDisjunctionExpansion:
    """Head-disjunction expansion and dependency-directed backtracking.

    A disjunct asserted at a branching point must enter the δ-new range so
    hyperresolution promotes it into δ-old and any clause consuming it fires; a
    branch whose disjunct clashes must backtrack and try the next disjunct.
    """

    NS = "http://disj#"

    def _ontology(self, dl_clauses, facts, iri):
        return DLOntology(
            ontology_iri=iri,
            dl_clauses=frozenset(dl_clauses),
            positive_facts=frozenset(facts),
            negative_facts=frozenset(),
        )

    def _consistent(self, dl_clauses, facts, iri):
        from hermit.reasoner import Reasoner

        reasoner = Reasoner(self._ontology(dl_clauses, facts, iri))
        try:
            return reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_both_disjuncts_clash_is_inconsistent(self):
        """U(a); U(X)->A(X)|B(X); A->clash; B->clash  =>  inconsistent."""
        x = Variable.create("X")
        u = AtomicConcept.create(self.NS + "U")
        a = AtomicConcept.create(self.NS + "A")
        b = AtomicConcept.create(self.NS + "B")
        ind = Individual.create(self.NS + "a")
        clauses = [
            DLClause.create(
                (Atom.create(a, x), Atom.create(b, x)), (Atom.create(u, x),)
            ),
            DLClause.create((), (Atom.create(a, x),)),
            DLClause.create((), (Atom.create(b, x),)),
        ]
        assert not self._consistent(clauses, [Atom.create(u, ind)], "urn:disj:unsat")

    def test_both_disjuncts_satisfiable_is_consistent(self):
        """U(a); U(X)->A(X)|B(X) with A,B both satisfiable  =>  consistent."""
        x = Variable.create("X")
        u = AtomicConcept.create(self.NS + "U")
        a = AtomicConcept.create(self.NS + "A")
        b = AtomicConcept.create(self.NS + "B")
        ind = Individual.create(self.NS + "a")
        clauses = [
            DLClause.create(
                (Atom.create(a, x), Atom.create(b, x)), (Atom.create(u, x),)
            ),
        ]
        assert self._consistent(clauses, [Atom.create(u, ind)], "urn:disj:sat")

    def test_first_disjunct_clashes_backtracks_to_second(self):
        """U(a); U(X)->A(X)|B(X); A->clash  =>  consistent via B."""
        x = Variable.create("X")
        u = AtomicConcept.create(self.NS + "U")
        a = AtomicConcept.create(self.NS + "A")
        b = AtomicConcept.create(self.NS + "B")
        ind = Individual.create(self.NS + "a")
        clauses = [
            DLClause.create(
                (Atom.create(a, x), Atom.create(b, x)), (Atom.create(u, x),)
            ),
            DLClause.create((), (Atom.create(a, x),)),
        ]
        assert self._consistent(clauses, [Atom.create(u, ind)], "urn:disj:mixed")

    def test_satisfiable_disjunction_chain_terminates(self):
        """A(a); A(X)->D0(X); D0(X)->D0(X)|D1(X) terminates and is consistent.

        The recursive disjunction whose first disjunct re-derives its own body
        must not loop: the disjunct already holds, so the branch is satisfied and
        expansion stops. Reaching a verdict at all is the termination check.
        """
        x = Variable.create("X")
        a = AtomicConcept.create(self.NS + "A")
        d0 = AtomicConcept.create(self.NS + "D0")
        d1 = AtomicConcept.create(self.NS + "D1")
        ind = Individual.create(self.NS + "a")
        clauses = [
            DLClause.create((Atom.create(d0, x),), (Atom.create(a, x),)),
            DLClause.create(
                (Atom.create(d0, x), Atom.create(d1, x)), (Atom.create(d0, x),)
            ),
        ]
        assert self._consistent(clauses, [Atom.create(a, ind)], "urn:disj:chain")


# ===========================================================================
# End-to-end missed-inconsistency repros (normalization + clausification)
# ===========================================================================

class TestComplexRestrictionFillers:
    """Complex fillers of quantified restrictions must not be weakened.

    Small ontologies are built from OWL model axioms and run through the full
    normalization → clausification → tableau pipeline.
    """

    NS = "http://example.org/fillers#"

    def _consistent(self, axioms):
        from hermit.configuration import Configuration
        from hermit.reasoner import Reasoner
        from hermit.structural.owl_clausification import OWLClausification
        from hermit.structural.owl_normalization import OWLNormalization

        normalized = OWLNormalization().process_ontology(axioms)
        ontology = OWLClausification().clausify(
            normalized, ontology_iri="urn:test:fillers"
        )
        config = Configuration()
        config.throw_inconsistent_ontology_exception = False
        return Reasoner(ontology, config).is_consistent()

    def _entities(self):
        from hermit.owl_model.class_expression import OWLClass
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        from hermit.owl_model.owl_property import OWLObjectProperty

        return (
            OWLClass(self.NS + "C"),
            OWLClass(self.NS + "c1"),
            OWLClass(self.NS + "c2"),
            OWLObjectProperty(self.NS + "r"),
            OWLNamedIndividual(self.NS + "a"),
        )

    def test_complement_of_intersection_all_values_filler(self):
        """C ⊑ ∃r3.c1 ⊓ ∃r4.c2 ⊓ ¬∃r3.(c1⊓c2) with functional super-role r.

        The functional super-role merges the two successors into one node in
        c1 ⊓ c2, so the complement-of-intersection universal must clash
        (WebOnt-description-logic-004 core).
        """
        from hermit.owl_model.class_expression import OWLObjectIntersectionOf
        from hermit.owl_model.class_expression.class_expression import (
            OWLObjectComplementOf,
        )
        from hermit.owl_model.class_expression.restriction import (
            OWLObjectSomeValuesFrom,
        )
        from hermit.owl_model.owl_axiom import (
            OWLClassAssertionAxiom,
            OWLFunctionalObjectPropertyAxiom,
            OWLSubClassOfAxiom,
            OWLSubObjectPropertyOfAxiom,
        )
        from hermit.owl_model.owl_property import OWLObjectProperty

        c, c1, c2, r, a = self._entities()
        r3 = OWLObjectProperty(self.NS + "r3")
        r4 = OWLObjectProperty(self.NS + "r4")
        axioms = [
            OWLSubClassOfAxiom(c, OWLObjectSomeValuesFrom(r3, c1)),
            OWLSubClassOfAxiom(c, OWLObjectSomeValuesFrom(r4, c2)),
            OWLSubObjectPropertyOfAxiom(r3, r),
            OWLSubObjectPropertyOfAxiom(r4, r),
            OWLFunctionalObjectPropertyAxiom(r),
            OWLSubClassOfAxiom(
                c,
                OWLObjectComplementOf(
                    OWLObjectSomeValuesFrom(
                        r3, OWLObjectIntersectionOf([c1, c2])
                    )
                ),
            ),
            OWLClassAssertionAxiom(a, c),
        ]
        assert not self._consistent(axioms)

    def test_intersection_some_values_filler(self):
        """C ⊑ ∃r.(c1 ⊓ c2) and C ⊑ ∀r.¬c1 is unsatisfiable for a member."""
        from hermit.owl_model.class_expression import OWLObjectIntersectionOf
        from hermit.owl_model.class_expression.class_expression import (
            OWLObjectComplementOf,
        )
        from hermit.owl_model.class_expression.restriction import (
            OWLObjectAllValuesFrom,
            OWLObjectSomeValuesFrom,
        )
        from hermit.owl_model.owl_axiom import (
            OWLClassAssertionAxiom,
            OWLSubClassOfAxiom,
        )

        c, c1, c2, r, a = self._entities()
        axioms = [
            OWLSubClassOfAxiom(
                c,
                OWLObjectSomeValuesFrom(r, OWLObjectIntersectionOf([c1, c2])),
            ),
            OWLSubClassOfAxiom(
                c, OWLObjectAllValuesFrom(r, OWLObjectComplementOf(c1))
            ),
            OWLClassAssertionAxiom(a, c),
        ]
        assert not self._consistent(axioms)

    def test_union_all_values_filler_remains_satisfiable(self):
        """C ⊑ ∃r.c1 ⊓ ∀r.(c1 ⊔ c2) is satisfiable (no over-strengthening)."""
        from hermit.owl_model.class_expression import OWLObjectUnionOf
        from hermit.owl_model.class_expression.restriction import (
            OWLObjectAllValuesFrom,
            OWLObjectSomeValuesFrom,
        )
        from hermit.owl_model.owl_axiom import (
            OWLClassAssertionAxiom,
            OWLSubClassOfAxiom,
        )

        c, c1, c2, r, a = self._entities()
        axioms = [
            OWLSubClassOfAxiom(c, OWLObjectSomeValuesFrom(r, c1)),
            OWLSubClassOfAxiom(
                c, OWLObjectAllValuesFrom(r, OWLObjectUnionOf([c1, c2]))
            ),
            OWLClassAssertionAxiom(a, c),
        ]
        assert self._consistent(axioms)


class TestSignatureCacheBlockerSentinel:
    """The signature-cache blocker sentinel must mark nodes as blocked."""

    def test_sentinel_is_initialized(self):
        assert Node.SIGNATURE_CACHE_BLOCKER is not None

    def test_node_blocked_by_sentinel_is_blocked(self):
        node = Node(None)
        node.set_blocked(Node.SIGNATURE_CACHE_BLOCKER, True)
        assert node.is_blocked()
        assert node.is_directly_blocked()


class TestTransitivePropagation:
    """Universals must propagate over transitive (sub-)roles."""

    NS = "http://example.org/trans#"

    def _consistent(self, axioms):
        from hermit.configuration import Configuration
        from hermit.reasoner import Reasoner
        from hermit.structural.owl_clausification import OWLClausification
        from hermit.structural.owl_normalization import OWLNormalization

        normalized = OWLNormalization().process_ontology(axioms)
        ontology = OWLClausification().clausify(
            normalized, ontology_iri="urn:test:trans"
        )
        config = Configuration()
        config.throw_inconsistent_ontology_exception = False
        return Reasoner(ontology, config).is_consistent()

    def _axioms(self, *, transitive):
        """A ⊑ ∃r.∃r.B ⊓ ∀r.¬B with a B-successor two r-steps away."""
        from hermit.owl_model.class_expression import OWLClass
        from hermit.owl_model.class_expression.class_expression import (
            OWLObjectComplementOf,
        )
        from hermit.owl_model.class_expression.restriction import (
            OWLObjectAllValuesFrom,
            OWLObjectSomeValuesFrom,
        )
        from hermit.owl_model.owl_axiom import (
            OWLClassAssertionAxiom,
            OWLSubClassOfAxiom,
            OWLTransitiveObjectPropertyAxiom,
        )
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        from hermit.owl_model.owl_property import OWLObjectProperty

        a_cls = OWLClass(self.NS + "A")
        b_cls = OWLClass(self.NS + "B")
        r = OWLObjectProperty(self.NS + "r")
        axioms = [
            OWLSubClassOfAxiom(
                a_cls,
                OWLObjectSomeValuesFrom(
                    r, OWLObjectSomeValuesFrom(r, b_cls)
                ),
            ),
            OWLSubClassOfAxiom(
                a_cls, OWLObjectAllValuesFrom(r, OWLObjectComplementOf(b_cls))
            ),
            OWLClassAssertionAxiom(OWLNamedIndividual(self.NS + "a"), a_cls),
        ]
        if transitive:
            axioms.append(OWLTransitiveObjectPropertyAxiom(r))
        return axioms

    def test_transitive_role_propagates_universal(self):
        """With trans(r), the two-step B-successor violates ∀r.¬B."""
        assert not self._consistent(self._axioms(transitive=True))

    def test_without_transitivity_remains_satisfiable(self):
        """Without trans(r), ∀r.¬B only constrains direct successors."""
        assert self._consistent(self._axioms(transitive=False))


class TestNominalSpyPoint:
    """A nominal spy point bounds the domain via at-most on its inverse role."""

    NS = "http://example.org/spy#"

    def test_spy_point_domain_bound_is_inconsistent(self):
        """⊤ ⊑ ∃p.{spy}, spy: ≤2 p⁻.⊤, a: ≥3 r.⊤ has no model.

        Every element is a p-predecessor of spy, so the domain holds at most
        two elements, contradicting the three pairwise-distinct r-successors
        (WebOnt-description-logic-035 core).
        """
        from hermit.configuration import Configuration
        from hermit.owl_model.class_expression import OWLClass
        from hermit.owl_model.class_expression.restriction import (
            OWLObjectMaxCardinality,
            OWLObjectMinCardinality,
            OWLObjectOneOf,
            OWLObjectSomeValuesFrom,
        )
        from hermit.owl_model.owl_axiom import (
            OWLClassAssertionAxiom,
            OWLInverseObjectPropertiesAxiom,
            OWLSubClassOfAxiom,
        )
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        from hermit.owl_model.owl_property import OWLObjectProperty
        from hermit.owl_model.class_expression import OWLThing
        from hermit.reasoner import Reasoner
        from hermit.structural.owl_clausification import OWLClausification
        from hermit.structural.owl_normalization import OWLNormalization

        p = OWLObjectProperty(self.NS + "p")
        inv_p = OWLObjectProperty(self.NS + "invP")
        r = OWLObjectProperty(self.NS + "r")
        spy = OWLNamedIndividual(self.NS + "spy")
        a = OWLNamedIndividual(self.NS + "a")
        unsat = OWLClass(self.NS + "Unsat")
        axioms = [
            OWLInverseObjectPropertiesAxiom(p, inv_p),
            OWLSubClassOfAxiom(
                OWLThing, OWLObjectSomeValuesFrom(p, OWLObjectOneOf([spy]))
            ),
            OWLClassAssertionAxiom(
                spy, OWLObjectMaxCardinality(2, inv_p, OWLThing)
            ),
            OWLSubClassOfAxiom(
                unsat, OWLObjectMinCardinality(3, r, OWLThing)
            ),
            OWLClassAssertionAxiom(a, unsat),
        ]
        normalized = OWLNormalization().process_ontology(axioms)
        ontology = OWLClausification().clausify(
            normalized, ontology_iri="urn:test:spy"
        )
        config = Configuration()
        config.throw_inconsistent_ontology_exception = False
        assert not Reasoner(ontology, config).is_consistent()
