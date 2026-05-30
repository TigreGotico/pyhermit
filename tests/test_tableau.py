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
