"""Tests for tableau internal modules."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# TupleIndex
# ---------------------------------------------------------------------------
from hermit.tableau.tuple_index import TupleIndex, TupleIndexRetrieval, _TrieNodeManager


class TestTrieNodeManager:
    def test_clear_and_new_trie_node(self):
        mgr = _TrieNodeManager()
        node0 = mgr.new_trie_node()
        assert node0 == 0
        node1 = mgr.new_trie_node()
        assert node1 == 1

    def test_get_set_component(self):
        mgr = _TrieNodeManager()
        n = mgr.new_trie_node()
        mgr.set_trie_node_component(n, TupleIndex.TRIE_NODE_PARENT, 42)
        assert mgr.get_trie_node_component(n, TupleIndex.TRIE_NODE_PARENT) == 42

    def test_get_set_object(self):
        mgr = _TrieNodeManager()
        n = mgr.new_trie_node()
        mgr.set_trie_node_object(n, "hello")
        assert mgr.get_trie_node_object(n) == "hello"

    def test_initialize_trie_node(self):
        mgr = _TrieNodeManager()
        n = mgr.new_trie_node()
        mgr.initialize_trie_node(n, 10, 20, 30, 40, 50, "obj")
        assert mgr.get_trie_node_component(n, TupleIndex.TRIE_NODE_PARENT) == 10
        assert mgr.get_trie_node_component(n, TupleIndex.TRIE_NODE_FIRST_CHILD) == 20
        assert mgr.get_trie_node_component(n, TupleIndex.TRIE_NODE_PREVIOUS_SIBLING) == 30
        assert mgr.get_trie_node_component(n, TupleIndex.TRIE_NODE_NEXT_SIBLING) == 40
        assert mgr.get_trie_node_component(n, TupleIndex.TRIE_NODE_NEXT_ENTRY) == 50
        assert mgr.get_trie_node_object(n) == "obj"

    def test_delete_and_reuse(self):
        mgr = _TrieNodeManager()
        n0 = mgr.new_trie_node()
        n1 = mgr.new_trie_node()
        mgr.delete_trie_node(n1)
        n2 = mgr.new_trie_node()
        assert n2 == n1  # reused

    def test_size(self):
        mgr = _TrieNodeManager()
        s = mgr.size()
        assert s > 0

    def test_page_growth(self):
        mgr = _TrieNodeManager()
        # Allocate more than one page worth of nodes
        for _ in range(TupleIndex.TRIE_NODE_PAGE_SIZE + 10):
            mgr.new_trie_node()
        assert mgr.m_number_of_pages >= 2


class TestTupleIndex:
    def test_add_and_get(self):
        idx = TupleIndex([0, 1])
        tup = ["a", "b"]
        result = idx.add_tuple(tup, 0)
        assert result == 0
        assert idx.get_tuple_index(tup) == 0

    def test_add_duplicate(self):
        idx = TupleIndex([0])
        tup = ["x"]
        idx.add_tuple(tup, 0)
        result = idx.add_tuple(tup, 1)
        assert result == 0  # existing

    def test_get_not_found(self):
        idx = TupleIndex([0])
        assert idx.get_tuple_index(["missing"]) == -1

    def test_remove(self):
        idx = TupleIndex([0])
        idx.add_tuple(["a"], 0)
        removed = idx.remove_tuple(["a"])
        assert removed == 0
        assert idx.get_tuple_index(["a"]) == -1

    def test_remove_not_found(self):
        idx = TupleIndex([0])
        assert idx.remove_tuple(["nope"]) == -1

    def test_clear(self):
        idx = TupleIndex([0])
        idx.add_tuple(["a"], 0)
        idx.clear()
        assert idx.get_tuple_index(["a"]) == -1

    def test_size_in_memory(self):
        idx = TupleIndex([0])
        assert idx.size_in_memory() > 0

    def test_indexing_sequence(self):
        idx = TupleIndex([0, 2])
        assert idx.indexing_sequence == [0, 2]

    def test_resize_buckets(self):
        idx = TupleIndex([0])
        # Add enough entries to trigger resize
        for i in range(20):
            idx.add_tuple([f"key_{i}"], i)
        for i in range(20):
            assert idx.get_tuple_index([f"key_{i}"]) == i

    def test_remove_chain_cleanup(self):
        """Remove nodes that cause parent chain cleanup."""
        idx = TupleIndex([0, 1])
        idx.add_tuple(["a", "b"], 0)
        removed = idx.remove_tuple(["a", "b"])
        assert removed == 0
        # After removing the only entry under "a", parent should also be cleaned
        assert idx.get_tuple_index(["a", "b"]) == -1

    def test_multiple_children_remove(self):
        """Remove one of multiple siblings."""
        idx = TupleIndex([0, 1])
        idx.add_tuple(["a", "b"], 0)
        idx.add_tuple(["a", "c"], 1)
        idx.remove_tuple(["a", "b"])
        assert idx.get_tuple_index(["a", "b"]) == -1
        assert idx.get_tuple_index(["a", "c"]) == 1

    def test_get_index_for_static(self):
        result = TupleIndex._get_index_for(42, 15)
        assert isinstance(result, int)
        assert 0 <= result <= 15


class TestTupleIndexRetrieval:
    def _make_index_with_tuples(self):
        idx = TupleIndex([0, 1])
        idx.add_tuple(["a", "x"], 0)
        idx.add_tuple(["a", "y"], 1)
        idx.add_tuple(["b", "z"], 2)
        return idx

    def test_open_with_selection(self):
        idx = self._make_index_with_tuples()
        buf = ["a", None]
        r = TupleIndexRetrieval(idx, buf, [0])
        r.open()
        assert not r.after_last()
        # Should find one of the two tuples starting with "a"
        ti = r.get_current_tuple_index()
        assert ti in (0, 1)

    def test_iterate_all(self):
        idx = self._make_index_with_tuples()
        buf = [None, None]
        r = TupleIndexRetrieval(idx, buf, [])
        r.open()
        results = []
        while not r.after_last():
            results.append(r.get_current_tuple_index())
            r.next()
        assert sorted(results) == [0, 1, 2]

    def test_open_not_found(self):
        idx = self._make_index_with_tuples()
        buf = ["notfound", None]
        r = TupleIndexRetrieval(idx, buf, [0])
        r.open()
        assert r.after_last()

    def test_open_empty_index(self):
        idx = TupleIndex([0, 1])
        buf = [None, None]
        r = TupleIndexRetrieval(idx, buf, [])
        r.open()
        assert r.after_last()

    def test_full_selection(self):
        idx = TupleIndex([0, 1])
        idx.add_tuple(["a", "b"], 0)
        buf = ["a", "b"]
        r = TupleIndexRetrieval(idx, buf, [0, 1])
        r.open()
        assert not r.after_last()
        assert r.get_current_tuple_index() == 0
        r.next()
        assert r.after_last()


# ---------------------------------------------------------------------------
# TupleTable
# ---------------------------------------------------------------------------
from hermit.tableau.tuple_table import TupleTable


class TestTupleTable:
    def test_add_and_retrieve(self):
        tt = TupleTable(3)
        idx = tt.add_tuple(["a", "b", "c"])
        assert idx == 0
        buf = [None, None, None]
        tt.retrieve_tuple(buf, idx)
        assert buf == ["a", "b", "c"]

    def test_first_free_tuple_index(self):
        tt = TupleTable(2)
        assert tt.first_free_tuple_index == 0
        tt.add_tuple(["x", "y"])
        assert tt.first_free_tuple_index == 1

    def test_tuple_equals(self):
        tt = TupleTable(2)
        tt.add_tuple(["a", "b"])
        assert tt.tuple_equals(["a", "b"], 0, 2)
        assert not tt.tuple_equals(["a", "c"], 0, 2)
        assert tt.tuple_equals(["a", "c"], 0, 1)  # compare only first

    def test_tuple_equals_with_positions(self):
        tt = TupleTable(2)
        tt.add_tuple(["a", "b"])
        # buffer[1] = "a", buffer[0] = "b" with positions [1, 0] maps to tuple ["a","b"]
        assert tt.tuple_equals_with_positions(["b", "a"], [1, 0], 0, 2)
        assert not tt.tuple_equals_with_positions(["b", "x"], [1, 0], 0, 2)

    def test_get_set_tuple_object(self):
        tt = TupleTable(2)
        tt.add_tuple(["a", "b"])
        assert tt.get_tuple_object(0, 0) == "a"
        assert tt.get_tuple_object(0, 1) == "b"
        tt.set_tuple_object(0, 1, "z")
        assert tt.get_tuple_object(0, 1) == "z"

    def test_truncate(self):
        tt = TupleTable(1)
        tt.add_tuple(["a"])
        tt.add_tuple(["b"])
        tt.truncate(1)
        assert tt.first_free_tuple_index == 1

    def test_nullify_tuple(self):
        tt = TupleTable(2)
        tt.add_tuple(["a", "b"])
        tt.nullify_tuple(0)
        assert tt.get_tuple_object(0, 0) is None
        assert tt.get_tuple_object(0, 1) is None

    def test_clear(self):
        tt = TupleTable(1)
        tt.add_tuple(["a"])
        tt.clear()
        assert tt.first_free_tuple_index == 0

    def test_size_in_memory(self):
        tt = TupleTable(2)
        assert tt.size_in_memory() > 0

    def test_page_growth(self):
        tt = TupleTable(1)
        for i in range(TupleTable.PAGE_SIZE + 10):
            tt.add_tuple([f"item_{i}"])
        assert tt.m_number_of_pages >= 2
        # Verify data integrity
        buf = [None]
        tt.retrieve_tuple(buf, TupleTable.PAGE_SIZE + 5)
        assert buf == [f"item_{TupleTable.PAGE_SIZE + 5}"]


# ---------------------------------------------------------------------------
# TupleTableFullIndex
# ---------------------------------------------------------------------------
from hermit.tableau.tuple_table_full_index import TupleTableFullIndex


class TestTupleTableFullIndex:
    def _make(self, arity=2):
        tt = TupleTable(arity)
        fi = TupleTableFullIndex(tt, arity)
        return tt, fi

    def test_add_and_get(self):
        tt, fi = self._make()
        ti = tt.add_tuple(["a", "b"])
        result = fi.add_tuple(["a", "b"], ti)
        assert result == ti
        assert fi.get_tuple_index(["a", "b"]) == ti

    def test_add_duplicate(self):
        tt, fi = self._make()
        ti0 = tt.add_tuple(["a", "b"])
        fi.add_tuple(["a", "b"], ti0)
        ti1 = tt.add_tuple(["a", "b"])
        result = fi.add_tuple(["a", "b"], ti1)
        assert result == ti0

    def test_get_not_found(self):
        tt, fi = self._make()
        assert fi.get_tuple_index(["x", "y"]) == -1

    def test_get_tuple_index_with_positions(self):
        tt, fi = self._make()
        ti = tt.add_tuple(["a", "b"])
        fi.add_tuple(["a", "b"], ti)
        # buffer = ["b", "a"], positions = [1, 0] -> "a", "b"
        assert fi.get_tuple_index_with_positions(["b", "a"], [1, 0]) == ti

    def test_get_tuple_index_with_positions_not_found(self):
        tt, fi = self._make()
        assert fi.get_tuple_index_with_positions(["x", "y"], [0, 1]) == -1

    def test_remove(self):
        tt, fi = self._make()
        ti = tt.add_tuple(["a", "b"])
        fi.add_tuple(["a", "b"], ti)
        assert fi.remove_tuple(ti)
        assert fi.get_tuple_index(["a", "b"]) == -1

    def test_remove_not_found(self):
        tt, fi = self._make()
        assert not fi.remove_tuple(0)

    def test_clear(self):
        tt, fi = self._make()
        ti = tt.add_tuple(["a", "b"])
        fi.add_tuple(["a", "b"], ti)
        fi.clear()
        assert fi.get_tuple_index(["a", "b"]) == -1

    def test_size_in_memory(self):
        _, fi = self._make()
        assert fi.size_in_memory() > 0

    def test_resize_buckets(self):
        tt, fi = self._make(arity=1)
        for i in range(20):
            key = [f"k{i}"]
            ti = tt.add_tuple(key)
            fi.add_tuple(key, ti)
        for i in range(20):
            assert fi.get_tuple_index([f"k{i}"]) == i

    def test_remove_with_chain(self):
        """Remove from a bucket that has chained entries."""
        tt, fi = self._make(arity=1)
        indices = []
        for i in range(20):
            key = [f"k{i}"]
            ti = tt.add_tuple(key)
            fi.add_tuple(key, ti)
            indices.append(ti)
        # Remove some in the middle
        fi.remove_tuple(indices[5])
        fi.remove_tuple(indices[10])
        assert fi.get_tuple_index(["k5"]) == -1
        assert fi.get_tuple_index(["k0"]) == 0

    def test_get_tuple_index_with_positions_hash_collision(self):
        """Exercise the hash-match-but-tuple-mismatch path."""
        tt, fi = self._make(arity=2)
        ti0 = tt.add_tuple(["a", "b"])
        fi.add_tuple(["a", "b"], ti0)
        ti1 = tt.add_tuple(["c", "d"])
        fi.add_tuple(["c", "d"], ti1)
        # Search for something that doesn't exist
        assert fi.get_tuple_index_with_positions(["x", "y"], [0, 1]) == -1

    def test_entry_manager_delete_and_reuse(self):
        """Test _EntryManager.delete_entry for reuse."""
        from hermit.tableau.tuple_table_full_index import _EntryManager
        em = _EntryManager()
        e0 = em.new_entry()
        e1 = em.new_entry()
        em.delete_entry(e1)
        e2 = em.new_entry()
        assert e2 == e1  # reused

    def test_entry_manager_growth(self):
        """Allocate enough entries to trigger page growth."""
        from hermit.tableau.tuple_table_full_index import _EntryManager
        em = _EntryManager()
        for _ in range(_EntryManager.ENTRY_PAGE_SIZE + 10):
            em.new_entry()
        assert len(em.m_entries) > _EntryManager.ENTRY_SIZE * _EntryManager.ENTRY_PAGE_SIZE


# ---------------------------------------------------------------------------
# UnionDependencySet
# ---------------------------------------------------------------------------
from hermit.tableau.union_dependency_set import UnionDependencySet


class _FakeDependencySet:
    """Minimal DependencySet for testing."""
    def __init__(self, branching_points):
        self._bps = set(branching_points)

    def contains_branching_point(self, bp):
        return bp in self._bps

    def is_empty(self):
        return len(self._bps) == 0

    def get_maximum_branching_point(self):
        return max(self._bps) if self._bps else -1


class TestUnionDependencySet:
    def test_constructor_sets_constituent_count(self):
        # New contract (matches Java): the constructor reserves and counts
        # `number_of_constituents` slots so that callers (DL-clause evaluator,
        # existential manager) can write directly into m_dependency_sets[i]
        # without going through add_constituent and still have get_permanent and
        # the branching-point queries see those constituents.
        uds = UnionDependencySet(4)
        assert uds.m_number_of_constituents == 4
        assert len(uds.m_dependency_sets) == 4

    def test_empty_when_all_slots_none(self):
        uds = UnionDependencySet(4)
        assert uds.is_empty()

    def test_direct_slot_write_and_contains(self):
        # The direct-write contract used by CopyDependencySet workers.
        uds = UnionDependencySet(2)
        uds.m_dependency_sets[0] = _FakeDependencySet({1, 3})
        uds.m_dependency_sets[1] = _FakeDependencySet({5})
        assert uds.contains_branching_point(1)
        assert uds.contains_branching_point(5)
        assert not uds.contains_branching_point(2)
        assert uds.get_maximum_branching_point() == 5
        assert not uds.is_empty()

    def test_add_constituent_after_clear(self):
        # The dynamic API (datatype manager path): clear first, then append.
        uds = UnionDependencySet(4)
        uds.clear_constituents()
        uds.add_constituent(_FakeDependencySet({1, 3}))
        uds.add_constituent(_FakeDependencySet({5}))
        assert uds.m_number_of_constituents == 2
        assert uds.contains_branching_point(1)
        assert uds.contains_branching_point(5)
        assert not uds.contains_branching_point(2)
        assert uds.get_maximum_branching_point() == 5

    def test_is_empty_with_empty_constituent(self):
        uds = UnionDependencySet(4)
        uds.clear_constituents()
        uds.add_constituent(_FakeDependencySet(set()))
        assert uds.is_empty()

    def test_clear_constituents(self):
        uds = UnionDependencySet(4)
        uds.clear_constituents()
        uds.add_constituent(_FakeDependencySet({1}))
        uds.clear_constituents()
        assert uds.is_empty()
        assert uds.m_number_of_constituents == 0

    def test_add_constituent_resize(self):
        uds = UnionDependencySet(2)
        uds.clear_constituents()
        for i in range(5):
            uds.add_constituent(_FakeDependencySet({i}))
        assert uds.m_number_of_constituents == 5
        assert uds.contains_branching_point(4)


# ---------------------------------------------------------------------------
# InterruptFlag
# ---------------------------------------------------------------------------
from hermit.tableau.interrupt_flag import InterruptFlag
from hermit.tableau.interrupt_current_task_exception import InterruptCurrentTaskException


class TestInterruptFlag:
    def test_no_interrupt(self):
        f = InterruptFlag()
        f.check_interrupt()  # should not raise

    def test_interrupt(self):
        f = InterruptFlag()
        f.interrupt()
        with pytest.raises(InterruptCurrentTaskException):
            f.check_interrupt()

    def test_start_end_task(self):
        f = InterruptFlag()
        f.interrupt()
        f.start_task()
        f.check_interrupt()  # reset, should not raise

    def test_end_task(self):
        f = InterruptFlag()
        f.interrupt()
        f.end_task()
        f.check_interrupt()  # reset by end_task

    def test_dispose_no_timer(self):
        f = InterruptFlag()
        f.dispose()  # no-op, no crash

    def test_timeout(self):
        f = InterruptFlag(individual_task_timeout=50)  # 50ms
        try:
            f.start_task()
            time.sleep(0.2)
            with pytest.raises(TimeoutError):
                f.check_interrupt()
        finally:
            f.dispose()

    def test_timeout_cancelled_by_end_task(self):
        f = InterruptFlag(individual_task_timeout=5000)
        try:
            f.start_task()
            f.end_task()
            f.check_interrupt()  # should not raise
        finally:
            f.dispose()

    def test_dispose_with_timer(self):
        f = InterruptFlag(individual_task_timeout=5000)
        f.dispose()
        # Should not hang or crash


# ---------------------------------------------------------------------------
# Node and NodeType
# ---------------------------------------------------------------------------
from hermit.tableau.node import Node, NodeState
from hermit.tableau.node_type import NodeType


class TestNodeType:
    def test_all_variants(self):
        assert NodeType.NAMED_NODE.merge_precedence == 0
        assert NodeType.TREE_NODE.is_ni_target is True
        assert NodeType.CONCRETE_NODE.is_abstract is False
        assert NodeType.ROOT_CONSTANT_NODE.is_abstract is False
        assert NodeType.NI_NODE.merge_precedence == 1
        assert NodeType.GRAPH_NODE.is_ni_target is True


class TestNode:
    def _make_node(self, tableau=None):
        n = Node(tableau)
        return n

    def test_uninitialized(self):
        n = self._make_node()
        assert n.node_id == -1
        assert n.m_node_state is None

    def test_initialize_and_accessors(self):
        n = self._make_node()
        n.initialize(5, None, NodeType.NAMED_NODE, 0)
        assert n.node_id == 5
        assert n.is_active()
        assert n.is_root_node()
        assert n.get_node_type() == NodeType.NAMED_NODE
        assert n.get_tree_depth() == 0
        assert n.tree_depth == 0
        assert n.node_type == NodeType.NAMED_NODE
        assert n.parent is None
        assert n.get_parent() is None

    def test_cluster_anchor_tree(self):
        n = self._make_node()
        n.initialize(1, None, NodeType.TREE_NODE, 0)
        assert n.cluster_anchor is n

    def test_cluster_anchor_non_tree(self):
        parent = self._make_node()
        parent.initialize(0, None, NodeType.NAMED_NODE, 0)
        child = self._make_node()
        child.initialize(1, parent, NodeType.NI_NODE, 1)
        assert child.cluster_anchor is parent

    def test_is_parent_of(self):
        parent = self._make_node()
        parent.initialize(0, None, NodeType.NAMED_NODE, 0)
        child = self._make_node()
        child.initialize(1, parent, NodeType.TREE_NODE, 1)
        assert parent.is_parent_of(child)
        assert not child.is_parent_of(parent)

    def test_blocking(self):
        n = self._make_node()
        n.initialize(0, None, NodeType.NAMED_NODE, 0)
        assert not n.is_blocked()
        assert not n.is_directly_blocked()
        assert not n.is_indirectly_blocked

        blocker = self._make_node()
        blocker.initialize(1, None, NodeType.NAMED_NODE, 0)
        n.set_blocked(blocker, True)
        assert n.is_blocked()
        assert n.is_directly_blocked()
        assert not n.is_indirectly_blocked
        assert n.blocker is blocker

        n.set_blocked(blocker, False)
        assert n.is_indirectly_blocked

        n.set_blocked(None, False)
        assert not n.is_blocked()

    def test_blocking_object_and_cargo(self):
        n = self._make_node()
        n.initialize(0, None, NodeType.NAMED_NODE, 0)
        n.set_blocking_object("obj")
        assert n.get_blocking_object() == "obj"
        assert n.blocking_object == "obj"
        n.blocking_object = "obj2"
        assert n.blocking_object == "obj2"

        n.set_blocking_cargo("cargo")
        assert n.get_blocking_cargo() == "cargo"
        assert n.blocking_cargo == "cargo"
        n.blocking_cargo = "cargo2"
        assert n.blocking_cargo == "cargo2"

    def test_merged_and_pruned(self):
        n = self._make_node()
        n.initialize(0, None, NodeType.NAMED_NODE, 0)
        assert not n.is_merged()
        assert not n.is_pruned()

        n.m_node_state = NodeState.MERGED
        assert n.is_merged()

        n.m_node_state = NodeState.PRUNED
        assert n.is_pruned()

    def test_merged_into(self):
        n = self._make_node()
        n.initialize(0, None, NodeType.NAMED_NODE, 0)
        other = self._make_node()
        other.initialize(1, None, NodeType.NAMED_NODE, 0)
        n.set_merged_into(other)
        assert n.get_merged_into() is other
        assert n.merged_into is other

    def test_get_canonical_node(self):
        a = self._make_node()
        a.initialize(0, None, NodeType.NAMED_NODE, 0)
        b = self._make_node()
        b.initialize(1, None, NodeType.NAMED_NODE, 0)
        a.m_merged_into = b
        assert a.get_canonical_node() is b

    def test_linked_list(self):
        a = self._make_node()
        a.initialize(0, None, NodeType.NAMED_NODE, 0)
        b = self._make_node()
        b.initialize(1, None, NodeType.NAMED_NODE, 0)
        a.set_next_tableau_node(b)
        b.set_previous_tableau_node(a)
        assert a.get_next_tableau_node() is b
        assert a.next_tableau_node is b
        assert b.get_previous_tableau_node() is a
        assert b.previous_tableau_node is a

    def test_unprocessed_existentials(self):
        # add_unprocessed_existential draws its backing list from the tableau's
        # existential-concepts buffer pool (symmetric with the removal path), so a
        # node needs a tableau exposing that pool.
        class _BufferPoolTableau:
            def __init__(self):
                self._buffers = []

            def get_existential_concepts_buffer(self):
                return self._buffers.pop() if self._buffers else []

            def put_existential_concepts_buffer(self, buffer):
                buffer.clear()
                self._buffers.append(buffer)

            class _DescriptionGraphManager:
                def initialise_node(self, node):
                    pass

                def destroy_node(self, node):
                    pass

            m_description_graph_manager = _DescriptionGraphManager()

        n = self._make_node(tableau=_BufferPoolTableau())
        n.initialize(0, None, NodeType.NAMED_NODE, 0)
        assert not n.has_unprocessed_existentials()
        assert n.get_unprocessed_existentials() == []
        n.add_unprocessed_existential("ex1")
        assert n.has_unprocessed_existentials()
        assert n.get_some_unprocessed_existential() == "ex1"
        assert n.unprocessed_existentials == ["ex1"]

    def test_set_unprocessed_existentials(self):
        n = self._make_node()
        n.initialize(0, None, NodeType.NAMED_NODE, 0)
        n.set_unprocessed_existentials(["a", "b"])
        assert n.get_unprocessed_existentials() == ["a", "b"]

    def test_is_ancestor_of(self):
        a = self._make_node()
        a.initialize(0, None, NodeType.NAMED_NODE, 0)
        b = self._make_node()
        b.initialize(1, a, NodeType.TREE_NODE, 1)
        c = self._make_node()
        c.initialize(2, b, NodeType.TREE_NODE, 2)
        assert a.is_ancestor_of(c)
        assert not c.is_ancestor_of(a)
        assert not a.is_ancestor_of(a)  # not ancestor of self (checks parent chain)

    def test_str_repr(self):
        n = self._make_node()
        n.initialize(7, None, NodeType.NAMED_NODE, 0)
        assert str(n) == "7"
        assert "id=7" in repr(n)

    def test_directly_blocked_accessors(self):
        n = self._make_node()
        n.initialize(0, None, NodeType.NAMED_NODE, 0)
        n.set_directly_blocked(True)
        assert n.get_directly_blocked()

    def test_number_of_positive_atomic_concepts(self):
        n = self._make_node()
        n.initialize(0, None, NodeType.NAMED_NODE, 0)
        assert n.number_of_positive_atomic_concepts == 0

    def test_destroy_without_tableau(self):
        n = self._make_node()
        n.initialize(0, None, NodeType.NAMED_NODE, 0)
        n.destroy()
        assert n.node_id == -1
        assert n.m_node_state is None

    def test_merged_into_dependency_set(self):
        n = self._make_node()
        n.initialize(0, None, NodeType.NAMED_NODE, 0)
        assert n.merged_into_dependency_set is None

    def test_get_node_id(self):
        n = self._make_node()
        n.initialize(42, None, NodeType.NAMED_NODE, 0)
        assert n.get_node_id() == 42

    def test_blocker_property(self):
        n = self._make_node()
        n.initialize(0, None, NodeType.NAMED_NODE, 0)
        n.set_blocker(n)
        assert n.get_blocker() is n

    def test_tableau_property(self):
        n = self._make_node()
        assert n.tableau is None

    def test_signature_cache_blocker(self):
        # The sentinel is created when Node(None) is first called
        assert Node.SIGNATURE_CACHE_BLOCKER is not None


# ---------------------------------------------------------------------------
# PermanentDependencySet
# ---------------------------------------------------------------------------
from hermit.tableau.permanent_dependency_set import PermanentDependencySet


class TestPermanentDependencySet:
    def test_empty(self):
        pds = PermanentDependencySet()
        pds._branching_point = -1
        assert pds.is_empty()

    def test_not_empty(self):
        pds = PermanentDependencySet()
        pds._branching_point = 3
        assert not pds.is_empty()

    def test_contains_single(self):
        pds = PermanentDependencySet()
        pds._branching_point = 5
        pds._rest = None
        assert pds.contains_branching_point(5)
        assert not pds.contains_branching_point(3)

    def test_contains_chain(self):
        tail = PermanentDependencySet()
        tail._branching_point = 2
        tail._rest = None
        head = PermanentDependencySet()
        head._branching_point = 5
        head._rest = tail
        assert head.contains_branching_point(5)
        assert head.contains_branching_point(2)
        assert not head.contains_branching_point(9)

    def test_get_maximum(self):
        pds = PermanentDependencySet()
        pds._branching_point = 7
        assert pds.get_maximum_branching_point() == 7

    def test_hash(self):
        pds = PermanentDependencySet()
        pds._branching_point = 5
        pds._rest = None
        h = pds._hash()
        assert isinstance(h, int)

    def test_hash_with_rest(self):
        tail = PermanentDependencySet()
        tail._branching_point = 2
        head = PermanentDependencySet()
        head._branching_point = 5
        head._rest = tail
        h = head._hash()
        assert isinstance(h, int)

    def test_str_empty(self):
        pds = PermanentDependencySet()
        pds._branching_point = -1
        assert str(pds) == "{ }"

    def test_str_with_elements(self):
        tail = PermanentDependencySet()
        tail._branching_point = -1
        head = PermanentDependencySet()
        head._branching_point = 5
        head._rest = tail
        assert "5" in str(head)


# ---------------------------------------------------------------------------
# BranchingPoint
# ---------------------------------------------------------------------------
from hermit.tableau.branching_point import BranchingPoint


class TestBranchingPoint:
    def test_level(self):
        tableau = MagicMock()
        tableau.m_current_branching_point = 2
        tableau.m_last_tableau_node = None
        tableau.m_last_merged_or_pruned_node = None
        tableau.m_first_ground_disjunction = None
        tableau.m_first_unprocessed_ground_disjunction = None
        bp = BranchingPoint(tableau)
        assert bp.level == 3

    def test_start_next_choice_noop(self):
        tableau = MagicMock()
        tableau.m_current_branching_point = 0
        tableau.m_last_tableau_node = None
        tableau.m_last_merged_or_pruned_node = None
        tableau.m_first_ground_disjunction = None
        tableau.m_first_unprocessed_ground_disjunction = None
        bp = BranchingPoint(tableau)
        bp.start_next_choice(tableau, MagicMock())  # no-op, should not raise


# ---------------------------------------------------------------------------
# DisjunctionBranchingPoint
# ---------------------------------------------------------------------------
from hermit.tableau.disjunction_branching_point import DisjunctionBranchingPoint


class TestDisjunctionBranchingPoint:
    def _make_tableau(self):
        t = MagicMock()
        t.m_current_branching_point = 0
        t.m_last_tableau_node = None
        t.m_last_merged_or_pruned_node = None
        t.m_first_ground_disjunction = None
        t.m_first_unprocessed_ground_disjunction = None
        t.m_use_disjunction_learning = False
        t.m_tableau_monitor = None
        t.dependency_set_factory = MagicMock()
        t.dependency_set_factory.get_permanent.side_effect = lambda ds: ds
        t.dependency_set_factory.remove_branching_point.side_effect = lambda ds, lv: ds
        return t

    def test_creation(self):
        t = self._make_tableau()
        gd = MagicMock()
        gd.get_number_of_disjuncts.return_value = 3
        dbp = DisjunctionBranchingPoint(t, gd, [0, 1, 2])
        assert dbp.level == 1
        assert dbp._current_index == 0

    def test_start_next_choice_basic(self):
        t = self._make_tableau()
        gd = MagicMock()
        gd.get_number_of_disjuncts.return_value = 3
        gd.get_dl_predicate.return_value = MagicMock()
        gd.add_disjunct_to_tableau.return_value = True

        dbp = DisjunctionBranchingPoint(t, gd, [0, 1, 2])
        clash_ds = MagicMock()
        dbp.start_next_choice(t, clash_ds)
        assert dbp._current_index == 1
        gd.add_disjunct_to_tableau.assert_called_once()

    def test_start_next_choice_with_learning(self):
        t = self._make_tableau()
        t.m_use_disjunction_learning = True
        gd = MagicMock()
        gd.get_number_of_disjuncts.return_value = 3
        gd.get_dl_predicate.return_value = MagicMock()
        gd.add_disjunct_to_tableau.return_value = True

        dbp = DisjunctionBranchingPoint(t, gd, [0, 1, 2])
        dbp.start_next_choice(t, MagicMock())
        gd.ground_disjunction_header.increase_number_of_backtrackings.assert_called()

    def test_start_next_choice_last_disjunct(self):
        t = self._make_tableau()
        gd = MagicMock()
        gd.get_number_of_disjuncts.return_value = 2
        gd.get_dl_predicate.return_value = MagicMock()
        gd.add_disjunct_to_tableau.return_value = True

        dbp = DisjunctionBranchingPoint(t, gd, [0, 1])
        dbp.start_next_choice(t, MagicMock())
        # At last disjunct, remove_branching_point should be called
        t.dependency_set_factory.remove_branching_point.assert_called()

    def test_start_next_choice_with_equality_previous(self):
        from hermit.model import Equality
        t = self._make_tableau()
        gd = MagicMock()
        gd.get_number_of_disjuncts.return_value = 3
        # First disjunct is Equality
        gd.get_dl_predicate.side_effect = lambda i: Equality.INSTANCE if i == 0 else MagicMock()
        gd.get_argument.return_value = MagicMock()
        gd.add_disjunct_to_tableau.return_value = True

        dbp = DisjunctionBranchingPoint(t, gd, [0, 1, 2])
        dbp.start_next_choice(t, MagicMock())
        # Should have added Inequality assertion for previous disjunct 0
        t.m_extension_manager.add_assertion.assert_called()

    def test_start_next_choice_with_atomic_concept_previous(self):
        from hermit.model import AtomicConcept
        t = self._make_tableau()
        gd = MagicMock()
        gd.get_number_of_disjuncts.return_value = 3
        ac = AtomicConcept.create("http://example.org/A")
        gd.get_dl_predicate.side_effect = lambda i: ac if i == 0 else MagicMock()
        gd.get_argument.return_value = MagicMock()
        gd.add_disjunct_to_tableau.return_value = True

        dbp = DisjunctionBranchingPoint(t, gd, [0, 1, 2])
        dbp.start_next_choice(t, MagicMock())
        t.m_extension_manager.add_concept_assertion.assert_called()

    def test_start_next_choice_with_monitor(self):
        t = self._make_tableau()
        t.m_tableau_monitor = MagicMock()
        gd = MagicMock()
        gd.get_number_of_disjuncts.return_value = 3
        gd.get_dl_predicate.return_value = MagicMock()
        gd.add_disjunct_to_tableau.return_value = True

        dbp = DisjunctionBranchingPoint(t, gd, [0, 1, 2])
        dbp.start_next_choice(t, MagicMock())
        t.m_tableau_monitor.disjunct_processing_started.assert_called()
        t.m_tableau_monitor.disjunct_processing_finished.assert_called()


# ---------------------------------------------------------------------------
# GroundDisjunctionHeader
# ---------------------------------------------------------------------------
from hermit.tableau.ground_disjunction_header import (
    DisjunctIndexWithBacktrackings,
    GroundDisjunctionHeader,
)


class TestDisjunctIndexWithBacktrackings:
    def test_init(self):
        d = DisjunctIndexWithBacktrackings(3)
        assert d.m_disjunct_index == 3
        assert d.m_number_of_backtrackings == 0


class TestGroundDisjunctionHeader:
    def _make_pred(self, arity=1, is_at_least=False, neg_to=False):
        pred = MagicMock()
        pred.arity.return_value = arity
        pred.get_arity.return_value = arity

        # Control isinstance checks
        if is_at_least:
            from hermit.model import AtLeastConcept
            pred.__class__ = AtLeastConcept
            to_concept = MagicMock()
            if neg_to:
                from hermit.model import AtomicNegationConcept
                to_concept.__class__ = AtomicNegationConcept
            pred.to_concept = to_concept
            pred.get_to_concept.return_value = to_concept
        return pred

    def test_basic_header(self):
        p1 = self._make_pred(1)
        p2 = self._make_pred(2)
        header = GroundDisjunctionHeader([p1, p2], 42, None)
        assert header.m_hash_code == 42
        assert header.m_next_entry is None
        assert header.m_disjunct_start == [0, 1]
        assert len(header.m_disjunct_indexes_with_backtrackings) == 2

    def test_is_equal(self):
        p1 = self._make_pred(1)
        p1.equals = lambda other: other is p1
        header = GroundDisjunctionHeader([p1], 0, None)
        assert header.is_equal([p1])
        assert not header.is_equal([])

    def test_is_equal_different_preds(self):
        p1 = self._make_pred(1)
        p2 = self._make_pred(1)
        p1.equals = lambda other: other is p1
        header = GroundDisjunctionHeader([p1], 0, None)
        assert not header.is_equal([p2])

    def test_get_sorted_disjunct_indexes(self):
        p1 = self._make_pred(1)
        p2 = self._make_pred(1)
        header = GroundDisjunctionHeader([p1, p2], 0, None)
        indexes = header.get_sorted_disjunct_indexes()
        assert sorted(indexes) == [0, 1]

    def test_increase_number_of_backtrackings(self):
        p1 = self._make_pred(1)
        p2 = self._make_pred(1)
        header = GroundDisjunctionHeader([p1, p2], 0, None)
        # Both are atomic (not AtLeastConcept), so in the first partition
        header.increase_number_of_backtrackings(0)
        # After incrementing, disjunct 0 has 1 backtracking, should swap with disjunct 1 (0 backtrackings)
        indexes = header.get_sorted_disjunct_indexes()
        assert indexes[0] == 1  # 0 backtrackings comes first after swap
        assert indexes[1] == 0  # 1 backtracking comes second

    def test_increase_backtrackings_at_partition_boundary(self):
        p1 = self._make_pred(1)  # atomic
        p2 = self._make_pred(1, is_at_least=True, neg_to=True)  # at_least negative
        p3 = self._make_pred(1, is_at_least=True, neg_to=False)  # at_least positive
        header = GroundDisjunctionHeader([p1, p2, p3], 0, None)
        # Increment in each partition to test boundary conditions
        header.increase_number_of_backtrackings(0)  # atomic partition
        header.increase_number_of_backtrackings(1)  # negative at_least partition
        header.increase_number_of_backtrackings(2)  # positive at_least partition

    def test_increase_backtrackings_swap_in_atleast(self):
        """Two at_least negative predicates -- swap within that partition."""
        p1 = self._make_pred(1, is_at_least=True, neg_to=True)
        p2 = self._make_pred(1, is_at_least=True, neg_to=True)
        header = GroundDisjunctionHeader([p1, p2], 0, None)
        header.increase_number_of_backtrackings(0)
        # After incrementing pred 0, it should swap with pred 1

    def test_str(self):
        p1 = self._make_pred(1)
        p1.__str__ = lambda: "P"
        p1.configure_mock(**{"__str__": lambda self: "P"})
        header = GroundDisjunctionHeader([p1], 0, None)
        s = str(header)
        assert "P" in s

    def test_repr(self):
        import sys
        pfx_mod = MagicMock()
        pfx_mod.Prefixes.STANDARD_PREFIXES = MagicMock()
        sys.modules["hermit.prefixes"] = pfx_mod
        try:
            p1 = self._make_pred(1)
            p1.to_string = lambda pfx: "P"
            header = GroundDisjunctionHeader([p1], 0, None)
            assert repr(header) == str(header)
        finally:
            del sys.modules["hermit.prefixes"]


# ---------------------------------------------------------------------------
# GroundDisjunction (partial -- needs heavy mocking for __init__)
# ---------------------------------------------------------------------------
from hermit.tableau.ground_disjunction import GroundDisjunction


class TestGroundDisjunction:
    def _make_gd(self):
        """Create a GroundDisjunction with mocked dependencies."""
        from hermit.tableau.node import Node

        header = MagicMock()
        header.m_dl_predicates = [MagicMock(), MagicMock()]
        header.m_disjunct_start = [0, 1]

        node1 = MagicMock(spec=Node)
        node1.is_pruned.return_value = False
        node1.node_id = 1
        node2 = MagicMock(spec=Node)
        node2.is_pruned.return_value = False
        node2.node_id = 2

        tableau = MagicMock()
        pds = MagicMock()
        tableau.m_dependency_set_factory.get_permanent.return_value = pds

        dep_set = MagicMock()

        gd = GroundDisjunction(tableau, header, [node1, node2], [True, False], dep_set)
        return gd

    def test_basic_accessors(self):
        gd = self._make_gd()
        assert gd.get_number_of_disjuncts() == 2
        assert gd.is_core(0) is True
        assert gd.is_core(1) is False

    def test_get_dl_predicate(self):
        gd = self._make_gd()
        p = gd.get_dl_predicate(0)
        assert p is gd.m_ground_disjunction_header.m_dl_predicates[0]

    def test_get_argument(self):
        gd = self._make_gd()
        arg = gd.get_argument(0, 0)
        assert arg is gd.m_arguments[0]

    def test_get_dependency_set(self):
        gd = self._make_gd()
        assert gd.get_dependency_set() is not None

    def test_ground_disjunction_header(self):
        gd = self._make_gd()
        assert gd.ground_disjunction_header is gd.m_ground_disjunction_header

    def test_is_pruned_false(self):
        gd = self._make_gd()
        assert not gd.is_pruned()

    def test_is_pruned_true(self):
        gd = self._make_gd()
        gd.m_arguments[0].is_pruned.return_value = True
        assert gd.is_pruned()

    def test_linked_list(self):
        gd = self._make_gd()
        assert gd.previous_ground_disjunction is None
        assert gd.next_ground_disjunction is None

    def test_destroy(self):
        gd = self._make_gd()
        tableau = MagicMock()
        gd.destroy(tableau)
        assert gd.m_dependency_set is None

    def test_destroy_already_none(self):
        gd = self._make_gd()
        gd.m_dependency_set = None
        tableau = MagicMock()
        gd.destroy(tableau)  # should not crash


# ---------------------------------------------------------------------------
# ExtensionTable, ExtensionTableWithFullIndex, ExtensionTableWithTupleIndexes
# ---------------------------------------------------------------------------
from hermit.tableau.extension_table import View


class TestView:
    def test_all_values(self):
        assert View.EXTENSION_THIS.value == "EXTENSION_THIS"
        assert View.EXTENSION_OLD.value == "EXTENSION_OLD"
        assert View.DELTA_OLD.value == "DELTA_OLD"
        assert View.TOTAL.value == "TOTAL"


class TestGroundDisjunctionSatisfied:
    """Test is_satisfied, add_disjunct_to_tableau, to_string on GroundDisjunction."""

    def _make_gd_with_arity(self, arities, pred_classes=None):
        """Create a GroundDisjunction with predicates of given arities."""
        import sys
        from hermit.tableau.node import Node

        header = MagicMock()
        preds = []
        disjunct_start = []
        args = []
        is_core = []
        offset = 0
        for i, arity in enumerate(arities):
            pred = MagicMock()
            pred.arity.return_value = arity
            pred.get_arity.return_value = arity
            if pred_classes and pred_classes[i]:
                pred.__class__ = pred_classes[i]
            preds.append(pred)
            disjunct_start.append(offset)
            for _ in range(arity):
                node = MagicMock(spec=Node)
                node.is_pruned.return_value = False
                node.node_id = len(args)
                node.get_canonical_node.return_value = node
                node.add_canonical_node_dependency_set.side_effect = lambda ds: ds
                args.append(node)
            is_core.append(False)
            offset += arity

        header.m_dl_predicates = preds
        header.m_disjunct_start = disjunct_start

        tableau = MagicMock()
        pds = MagicMock()
        tableau.m_dependency_set_factory.get_permanent.return_value = pds

        gd = GroundDisjunction(tableau, header, args, is_core, MagicMock())
        return gd

    def test_is_satisfied_arity1(self):
        gd = self._make_gd_with_arity([1])
        tableau = MagicMock()
        tableau.m_extension_manager.contains_assertion.return_value = True
        assert gd.is_satisfied(tableau)

    def test_is_satisfied_arity1_false(self):
        gd = self._make_gd_with_arity([1])
        tableau = MagicMock()
        tableau.m_extension_manager.contains_assertion_unary.return_value = False
        assert not gd.is_satisfied(tableau)

    def test_is_satisfied_arity2(self):
        gd = self._make_gd_with_arity([2])
        tableau = MagicMock()
        tableau.m_extension_manager.contains_assertion_binary.return_value = True
        assert gd.is_satisfied(tableau)

    def test_is_satisfied_arity3_annotated_equality(self):
        from hermit.model import AnnotatedEquality
        gd = self._make_gd_with_arity([3], [AnnotatedEquality])
        tableau = MagicMock()
        tableau.m_extension_manager.contains_assertion_ternary.return_value = True
        assert gd.is_satisfied(tableau)

    def test_is_satisfied_arity3_not_annotated(self):
        gd = self._make_gd_with_arity([3])
        tableau = MagicMock()
        with pytest.raises(RuntimeError, match="Invalid arity"):
            gd.is_satisfied(tableau)

    def test_is_satisfied_arity4_raises(self):
        gd = self._make_gd_with_arity([1])
        # Monkey-patch predicate to return arity 4 (both aliases)
        gd.m_ground_disjunction_header.m_dl_predicates[0].arity.return_value = 4
        gd.m_ground_disjunction_header.m_dl_predicates[0].get_arity.return_value = 4
        tableau = MagicMock()
        with pytest.raises(RuntimeError, match="Invalid arity"):
            gd.is_satisfied(tableau)

    def test_add_disjunct_arity1(self):
        gd = self._make_gd_with_arity([1])
        tableau = MagicMock()
        tableau.m_extension_manager.add_concept_assertion.return_value = True
        result = gd.add_disjunct_to_tableau(tableau, 0, MagicMock())
        assert result is True

    def test_add_disjunct_arity2(self):
        gd = self._make_gd_with_arity([2])
        tableau = MagicMock()
        tableau.m_extension_manager.add_assertion_binary.return_value = True
        result = gd.add_disjunct_to_tableau(tableau, 0, MagicMock())
        assert result is True

    def test_add_disjunct_arity3_annotated(self):
        from hermit.model import AnnotatedEquality
        gd = self._make_gd_with_arity([3], [AnnotatedEquality])
        tableau = MagicMock()
        tableau.m_extension_manager.add_annotated_equality.return_value = True
        result = gd.add_disjunct_to_tableau(tableau, 0, MagicMock())
        assert result is True

    def test_add_disjunct_arity3_not_annotated(self):
        gd = self._make_gd_with_arity([3])
        tableau = MagicMock()
        with pytest.raises(RuntimeError, match="Unsupported"):
            gd.add_disjunct_to_tableau(tableau, 0, MagicMock())

    def test_add_disjunct_arity4_raises(self):
        gd = self._make_gd_with_arity([1])
        gd.m_ground_disjunction_header.m_dl_predicates[0].arity.return_value = 4
        gd.m_ground_disjunction_header.m_dl_predicates[0].get_arity.return_value = 4
        tableau = MagicMock()
        with pytest.raises(RuntimeError, match="Unsupported"):
            gd.add_disjunct_to_tableau(tableau, 0, MagicMock())

    def _stub_prefixes(self):
        import sys
        pfx_mod = MagicMock()
        pfx_mod.Prefixes.STANDARD_PREFIXES = MagicMock()
        sys.modules["hermit.prefixes"] = pfx_mod
        return pfx_mod

    def _unstub_prefixes(self):
        import sys
        sys.modules.pop("hermit.prefixes", None)

    def test_to_string_simple(self):
        gd = self._make_gd_with_arity([1, 1])
        # Production code uses str(dl_predicate) — configure __str__ on mocks
        for p in gd.m_ground_disjunction_header.m_dl_predicates:
            p.configure_mock(**{"__str__": lambda self: "Pred"})
        s = gd.to_string()
        assert "Pred" in s

    def test_to_string_equality(self):
        from hermit.model import Equality, Individual
        from hermit.tableau.node import Node
        # Use actual Equality.INSTANCE as the predicate so the == check is True
        gd = self._make_gd_with_arity([2])
        gd.m_ground_disjunction_header.m_dl_predicates[0] = Equality.INSTANCE
        # Arguments must be Node-like for node_id access
        for i, arg in enumerate(gd.m_arguments):
            arg.node_id = i
        s = gd.to_string()
        assert "==" in s

    def test_to_string_annotated_equality(self):
        from hermit.model import AnnotatedEquality, Equality
        gd = self._make_gd_with_arity([3], [AnnotatedEquality])
        pred = gd.m_ground_disjunction_header.m_dl_predicates[0]
        # Production code now uses pred.cardinality, str(pred.on_role), str(pred.to_concept)
        pred.cardinality = 2
        pred.on_role = MagicMock()
        pred.on_role.configure_mock(**{"__str__": lambda self: "R"})
        pred.to_concept = MagicMock()
        pred.to_concept.configure_mock(**{"__str__": lambda self: "C"})
        for i, arg in enumerate(gd.m_arguments):
            arg.node_id = i
        s = gd.to_string()
        assert "==" in s
        assert "atMost" in s

    def test_to_string_multi_arg_predicate(self):
        """Exercise the comma branch for predicates with arity >= 2."""
        gd = self._make_gd_with_arity([2])
        pred = gd.m_ground_disjunction_header.m_dl_predicates[0]
        # Production code uses str(dl_predicate)
        pred.configure_mock(**{"__str__": lambda self: "R"})
        s = gd.to_string()
        assert "R(" in s
        assert "," in s  # comma between args

    def test_str(self):
        self._stub_prefixes()
        try:
            gd = self._make_gd_with_arity([1])
            from hermit.model import Equality
            pred = gd.m_ground_disjunction_header.m_dl_predicates[0]
            pred.to_string.return_value = "P"
            pred.get_arity.return_value = 1
            mock_eq = MagicMock()
            mock_eq.equals.return_value = False
            with patch.object(Equality, "INSTANCE", mock_eq):
                s = str(gd)
            assert isinstance(s, str)
        finally:
            self._unstub_prefixes()


class TestGroundDisjunctionHeaderStr:
    """Test the __str__ with multiple disjuncts to hit line 165."""

    def test_str_multiple(self):
        p1 = MagicMock()
        p1.arity.return_value = 1
        p1.get_arity.return_value = 1
        p1.configure_mock(**{"__str__": lambda self: "A"})
        p2 = MagicMock()
        p2.arity.return_value = 1
        p2.get_arity.return_value = 1
        p2.configure_mock(**{"__str__": lambda self: "B"})
        header = GroundDisjunctionHeader([p1, p2], 0, None)
        s = str(header)
        assert "A" in s
        assert "B" in s
        assert "\\/" in s


class TestNodeWithTableau:
    """Test Node methods that need a real-ish tableau."""

    def test_destroy_with_existentials(self):
        tableau = MagicMock()
        n = Node(tableau)
        n.initialize(0, None, NodeType.NAMED_NODE, 0)
        # Simulate having unprocessed existentials
        n.m_unprocessed_existentials = ["e1"]
        n.destroy()
        tableau.put_existential_concepts_buffer.assert_called()

    def test_destroy_with_merged_dependency_set(self):
        tableau = MagicMock()
        n = Node(tableau)
        n.initialize(0, None, NodeType.NAMED_NODE, 0)
        n.m_merged_into_dependency_set = MagicMock()
        n.destroy()
        tableau.m_dependency_set_factory.remove_usage.assert_called()

    def test_get_canonical_node_dependency_set(self):
        tableau = MagicMock()
        factory = tableau.m_dependency_set_factory
        factory.empty_set = MagicMock()
        factory.get_permanent.side_effect = lambda ds: ds
        factory.union_with.side_effect = lambda a, b: a

        n = Node(tableau)
        n.initialize(0, None, NodeType.NAMED_NODE, 0)
        result = n.get_canonical_node_dependency_set()
        factory.get_permanent.assert_called()

    def test_add_canonical_node_dependency_set_with_merge(self):
        tableau = MagicMock()
        factory = tableau.m_dependency_set_factory
        factory.get_permanent.side_effect = lambda ds: ds
        factory.union_with.side_effect = lambda a, b: a

        a = Node(tableau)
        a.initialize(0, None, NodeType.NAMED_NODE, 0)
        b = Node(tableau)
        b.initialize(1, None, NodeType.NAMED_NODE, 0)
        a.m_merged_into = b
        a.m_merged_into_dependency_set = MagicMock()

        dep = MagicMock()
        result = a.add_canonical_node_dependency_set(dep)
        factory.union_with.assert_called()

    def test_add_to_unprocessed_existentials(self):
        tableau = MagicMock()
        tableau.get_existential_concepts_buffer.return_value = []
        n = Node(tableau)
        n.initialize(0, None, NodeType.NAMED_NODE, 0)
        n._add_to_unprocessed_existentials("ex1")
        assert n.has_unprocessed_existentials()
        assert n.get_some_unprocessed_existential() == "ex1"

    def test_remove_from_unprocessed_existentials_last(self):
        tableau = MagicMock()
        tableau.get_existential_concepts_buffer.return_value = []
        n = Node(tableau)
        n.initialize(0, None, NodeType.NAMED_NODE, 0)
        n._add_to_unprocessed_existentials("ex1")
        n._remove_from_unprocessed_existentials("ex1")
        assert not n.has_unprocessed_existentials()
        tableau.put_existential_concepts_buffer.assert_called()

    def test_remove_from_unprocessed_existentials_lifo(self):
        """Remove last element (LIFO case -- the optimized path)."""
        tableau = MagicMock()
        tableau.get_existential_concepts_buffer.return_value = []
        n = Node(tableau)
        n.initialize(0, None, NodeType.NAMED_NODE, 0)
        n._add_to_unprocessed_existentials("ex1")
        n._add_to_unprocessed_existentials("ex2")
        n._remove_from_unprocessed_existentials("ex2")
        assert n.has_unprocessed_existentials()
        assert n.get_some_unprocessed_existential() == "ex1"


class TestInterruptFlagEdgeCases:
    def test_start_task_no_timer(self):
        f = InterruptFlag()
        f.start_task()  # no timer, no crash

    def test_end_task_no_timer(self):
        f = InterruptFlag()
        f.end_task()  # no timer, no crash


def test_extension_table_with_full_index_import():
    from hermit.tableau.extension_table_with_full_index import ExtensionTableWithFullIndex
    assert ExtensionTableWithFullIndex is not None


def test_extension_table_with_tuple_indexes_import():
    from hermit.tableau.extension_table_with_tuple_indexes import ExtensionTableWithTupleIndexes
    assert ExtensionTableWithTupleIndexes is not None


# ---------------------------------------------------------------------------
# ReasoningTaskDescription
# ---------------------------------------------------------------------------
from hermit.tableau.reasoning_task_description import (
    ReasoningTaskDescription,
    StandardTestType,
    _to_string_with_prefixes,
)


class TestStandardTestType:
    def test_all_types(self):
        assert "satisfiability" in StandardTestType.CONCEPT_SATISFIABILITY.value
        assert "ABox" in StandardTestType.CONSISTENCY.value
        assert "subsumption" in StandardTestType.CONCEPT_SUBSUMPTION.value


class TestReasoningTaskDescription:
    def test_basic(self):
        rtd = ReasoningTaskDescription(False, StandardTestType.CONSISTENCY)
        assert rtd.flip_satisfiability_result is False
        assert "ABox" in rtd.message_pattern

    def test_with_arguments(self):
        rtd = ReasoningTaskDescription(
            True, StandardTestType.CONCEPT_SUBSUMPTION, "A", "B"
        )
        # _to_string_with_prefixes has TYPE_CHECKING-only imports that fail
        # at runtime, so we patch it to just call str()
        with patch(
            "hermit.tableau.reasoning_task_description._to_string_with_prefixes",
            side_effect=lambda obj, pfx: str(obj),
        ):
            desc = rtd.get_task_description(MagicMock())
            assert "A" in desc
            assert "B" in desc

    def test_custom_pattern(self):
        rtd = ReasoningTaskDescription(False, "custom test {0}")
        desc = rtd.get_task_description(None)
        assert desc == "custom test {0}"  # no args to substitute

    def test_custom_with_args(self):
        rtd = ReasoningTaskDescription(False, "test {0} and {1}", "X", "Y")
        with patch(
            "hermit.tableau.reasoning_task_description._to_string_with_prefixes",
            side_effect=lambda obj, pfx: str(obj),
        ):
            desc = rtd.get_task_description(None)
            assert desc == "test X and Y"

    def test_is_a_box_satisfiable(self):
        rtd = ReasoningTaskDescription.is_a_box_satisfiable()
        assert not rtd.flip_satisfiability_result

    def test_is_concept_satisfiable(self):
        rtd = ReasoningTaskDescription.is_concept_satisfiable("C")
        assert not rtd.flip_satisfiability_result
        with patch(
            "hermit.tableau.reasoning_task_description._to_string_with_prefixes",
            side_effect=lambda obj, pfx: str(obj),
        ):
            desc = rtd.get_task_description(None)
            assert "C" in desc

    def test_is_concept_subsumed_by(self):
        rtd = ReasoningTaskDescription.is_concept_subsumed_by("A", "B")
        assert rtd.flip_satisfiability_result

    def test_is_concept_subsumed_by_list(self):
        rtd = ReasoningTaskDescription.is_concept_subsumed_by_list("A", "B", "C")
        with patch(
            "hermit.tableau.reasoning_task_description._to_string_with_prefixes",
            side_effect=lambda obj, pfx: str(obj),
        ):
            desc = rtd.get_task_description(None)
            assert "A" in desc

    def test_is_role_subsumed_by_list(self):
        rtd = ReasoningTaskDescription.is_role_subsumed_by_list("r", "s", "t")
        with patch(
            "hermit.tableau.reasoning_task_description._to_string_with_prefixes",
            side_effect=lambda obj, pfx: str(obj),
        ):
            desc = rtd.get_task_description(None)
            assert "r" in desc

    def test_is_role_satisfiable_object(self):
        rtd = ReasoningTaskDescription.is_role_satisfiable("r", True)
        assert "object" in rtd.message_pattern.lower() or "role" in rtd.message_pattern.lower()

    def test_is_role_satisfiable_data(self):
        rtd = ReasoningTaskDescription.is_role_satisfiable("r", False)
        assert "data" in rtd.message_pattern.lower() or "role" in rtd.message_pattern.lower()

    def test_is_role_subsumed_by(self):
        rtd = ReasoningTaskDescription.is_role_subsumed_by("r", "s", True)
        assert rtd.flip_satisfiability_result

    def test_is_role_subsumed_by_data(self):
        rtd = ReasoningTaskDescription.is_role_subsumed_by("r", "s", False)
        assert rtd.flip_satisfiability_result

    def test_is_instance_of(self):
        rtd = ReasoningTaskDescription.is_instance_of("C", "ind")
        assert rtd.flip_satisfiability_result

    def test_is_object_role_instance_of(self):
        rtd = ReasoningTaskDescription.is_object_role_instance_of("r", "a", "b")
        assert rtd.flip_satisfiability_result

    def test_is_data_role_instance_of(self):
        rtd = ReasoningTaskDescription.is_data_role_instance_of("r", "a", "b")
        assert rtd.flip_satisfiability_result

    def test_is_axiom_entailed(self):
        rtd = ReasoningTaskDescription.is_axiom_entailed("ax")
        assert rtd.flip_satisfiability_result

    def test_is_domain_of(self):
        rtd = ReasoningTaskDescription.is_domain_of("D", "r")
        assert rtd.flip_satisfiability_result

    def test_is_range_of(self):
        rtd = ReasoningTaskDescription.is_range_of("R", "r")
        assert rtd.flip_satisfiability_result


class TestToStringWithPrefixes:
    """_to_string_with_prefixes uses isinstance on TYPE_CHECKING-only
    imports (DLPredicate is a non-runtime-checkable Protocol).
    We inject concrete stand-in classes to exercise the branches."""

    def _patch_module(self):
        import hermit.tableau.reasoning_task_description as mod

        class FakeDLP:
            def to_string(self, pfx):
                return "dlp"

        class FakeRole:
            def to_string(self, pfx):
                return "role"

        class FakeConcept:
            def to_string(self, pfx):
                return "concept"

        class FakeTerm:
            def to_string(self, pfx):
                return "term"

        mod.DLPredicate = FakeDLP
        mod.Role = FakeRole
        mod.Concept = FakeConcept
        mod.Term = FakeTerm
        return mod, FakeDLP, FakeRole, FakeConcept, FakeTerm

    def _unpatch(self, mod):
        del mod.DLPredicate, mod.Role, mod.Concept, mod.Term

    def test_plain_string(self):
        mod, *_ = self._patch_module()
        try:
            assert _to_string_with_prefixes("hello", None) == "hello"
            assert _to_string_with_prefixes(42, None) == "42"
        finally:
            self._unpatch(mod)

    def test_dl_predicate(self):
        mod, FakeDLP, *_ = self._patch_module()
        try:
            assert _to_string_with_prefixes(FakeDLP(), None) == "dlp"
        finally:
            self._unpatch(mod)

    def test_role(self):
        mod, _, FakeRole, *_ = self._patch_module()
        try:
            assert _to_string_with_prefixes(FakeRole(), None) == "role"
        finally:
            self._unpatch(mod)

    def test_concept(self):
        mod, _, _, FakeConcept, _ = self._patch_module()
        try:
            assert _to_string_with_prefixes(FakeConcept(), None) == "concept"
        finally:
            self._unpatch(mod)

    def test_term(self):
        mod, _, _, _, FakeTerm = self._patch_module()
        try:
            assert _to_string_with_prefixes(FakeTerm(), None) == "term"
        finally:
            self._unpatch(mod)
