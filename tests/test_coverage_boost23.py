"""Coverage boost 23 — dependency_set_factory.py and other quick wins.

Covers lines: 34-37 (IntArray resize), 102, 143, 170-175, 213,
             266-269, 309-310, 322-334, 338-350 in dependency_set_factory.py
"""

from __future__ import annotations

import pytest


class TestIntArrayResize:
    """Tests for _IntArray.add() resize logic — lines 34-37."""

    def test_add_triggers_resize(self):
        """Lines 34-37: adding more than initial capacity triggers resize."""
        from hermit.tableau.dependency_set_factory import _IntegerArray

        arr = _IntegerArray()
        # Default capacity is 64, add 65 elements to trigger resize
        for i in range(65):
            arr.add(i)
        assert arr[64] == 64  # 65th element
        assert arr._size == 65

    def test_add_no_resize_needed(self):
        """_IntegerArray.add() within capacity — no resize."""
        from hermit.tableau.dependency_set_factory import _IntegerArray

        arr = _IntegerArray()
        arr.add(42)
        assert arr[0] == 42
        assert arr._size == 1


class TestDependencySetFactoryMethods:
    """Tests for DependencySetFactory internal methods."""

    def _make_factory(self):
        from hermit.tableau.dependency_set_factory import DependencySetFactory
        from hermit.tableau.permanent_dependency_set import PermanentDependencySet
        return DependencySetFactory()

    def test_add_branching_point_creates_new_set(self):
        """Test add_branching_point creates a new set with the branching point."""
        factory = self._make_factory()
        empty = factory.empty_set
        new_set = factory.add_branching_point(empty, 1)
        assert new_set is not None
        assert new_set.contains_branching_point(1)

    def test_union_creates_combined_set(self):
        """Test union_with of two dependency sets."""
        factory = self._make_factory()
        empty = factory.empty_set
        set1 = factory.add_branching_point(empty, 2)
        set2 = factory.add_branching_point(empty, 5)
        union = factory.union_with(set1, set2)
        assert union.contains_branching_point(2)
        assert union.contains_branching_point(5)

    def test_usage_calls_are_noops(self):
        """add_usage/remove_usage no longer reference-count: they never destroy."""
        factory = self._make_factory()
        empty = factory.empty_set
        ds = factory.add_branching_point(empty, 3)
        factory.add_usage(ds)
        factory.remove_usage(ds)
        # The interned set persists regardless of usage calls.
        assert factory._size == 1
        assert ds.contains_branching_point(3)

    def test_remove_unused_sets_is_noop(self):
        """remove_unused_sets keeps interned sets alive (GC owns reclamation)."""
        factory = self._make_factory()
        empty = factory.empty_set
        ds = factory.add_branching_point(empty, 10)
        factory.add_usage(ds)
        factory.remove_usage(ds)
        factory.remove_unused_sets()  # no-op; must not raise and must not free
        assert factory._size == 1
        assert ds.contains_branching_point(10)

    def test_equal_sets_are_interned_to_same_object(self):
        """Re-creating an equal set returns the same interned instance (is)."""
        factory = self._make_factory()
        empty = factory.empty_set
        ds = factory.add_branching_point(empty, 7)
        factory.add_usage(ds)
        factory.remove_usage(ds)
        factory.remove_unused_sets()
        assert factory._size == 1
        ds2 = factory.add_branching_point(empty, 7)
        # Interning: structurally equal sets share identity, so equality is `is`.
        assert ds2 is ds
        assert factory._size == 1

    def test_add_branching_point_existing_middle_line143(self):
        """Line 143: branching point already exists in middle of chain → return permanent."""
        factory = self._make_factory()
        empty = factory.empty_set
        # Build chain: 5 -> 3 -> empty
        set35 = factory.add_branching_point(empty, 3)
        set35 = factory.add_branching_point(set35, 5)
        # Adding bp=3 again should find it in the middle and return same set
        result = factory.add_branching_point(set35, 3)
        assert result.contains_branching_point(3)
        assert result.contains_branching_point(5)

    def test_remove_branching_point_from_middle_lines170_175(self):
        """Lines 170-175: remove bp from middle of chain."""
        factory = self._make_factory()
        empty = factory.empty_set
        # Build chain: 5 -> 3 -> 1 -> empty
        ds = factory.add_branching_point(empty, 1)
        ds = factory.add_branching_point(ds, 3)
        ds = factory.add_branching_point(ds, 5)
        # Remove bp=3 from middle
        result = factory.remove_branching_point(ds, 3)
        assert result.contains_branching_point(5)
        assert result.contains_branching_point(1)
        assert not result.contains_branching_point(3)

    def test_get_permanent_none_returns_empty_line213(self):
        """Line 213: get_permanent(None) returns empty_set."""
        factory = self._make_factory()
        result = factory.get_permanent(None)
        assert result is factory.empty_set

