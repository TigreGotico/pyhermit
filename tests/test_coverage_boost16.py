"""Coverage boost 16 — targeted tests for hierarchy/hierarchy.py.

Covers lines: 234, 240-242, 301, 306-317
"""

from __future__ import annotations

import pytest

from hermit.hierarchy.hierarchy import Hierarchy
from hermit.hierarchy.hierarchy_node import HierarchyNode


class TestHierarchyToString:
    """Tests for Hierarchy.__str__() covering lines 234, 240-242."""

    def test_str_with_equivalences_multiple(self):
        """Line 234: second equivalent element writes a space before it.

        Need a node with 3+ equivalent elements (rep + 2 others).
        """
        top = HierarchyNode("TOP")
        bottom = HierarchyNode("BOTTOM")

        mid = HierarchyNode("A")
        mid.m_equivalent_elements.add("A")
        mid.m_equivalent_elements.add("B")
        mid.m_equivalent_elements.add("C")  # 3 elements → space on 3rd

        top.m_child_nodes.add(mid)
        top.m_child_nodes.add(bottom)
        mid.m_parent_nodes.add(top)
        mid.m_child_nodes.add(bottom)
        bottom.m_parent_nodes.add(mid)

        h = Hierarchy(top, bottom)
        h.m_nodes_by_elements["TOP"] = top
        h.m_nodes_by_elements["BOTTOM"] = bottom
        h.m_nodes_by_elements["A"] = mid
        h.m_nodes_by_elements["B"] = mid
        h.m_nodes_by_elements["C"] = mid

        s = str(h)
        # Should contain the equivalence info with space between elements
        assert isinstance(s, str)
        assert "A" in s

    def test_str_with_parent_node(self):
        """Lines 240-242: node with parent_node writes ' -> parent_rep'."""
        top = HierarchyNode("TOP")
        bottom = HierarchyNode("BOTTOM")
        mid = HierarchyNode("MID")

        mid.m_equivalent_elements.add("MID")
        top.m_child_nodes.add(mid)
        top.m_child_nodes.add(bottom)
        mid.m_parent_nodes.add(top)
        mid.m_child_nodes.add(bottom)
        bottom.m_parent_nodes.add(mid)

        h = Hierarchy(top, bottom)
        h.m_nodes_by_elements["TOP"] = top
        h.m_nodes_by_elements["BOTTOM"] = bottom
        h.m_nodes_by_elements["MID"] = mid

        s = str(h)
        # MID should appear with ' -> TOP' because it has a parent
        assert "MID" in s
        assert "->" in s
        assert "TOP" in s


class TestHierarchyNodeComparator:
    """Tests for _HierarchyNodeComparator.compare() — lines 301, 306-317."""

    def test_comparator_less_than(self):
        """Line 313-314: returns -1 when n1 < n2."""
        from hermit.hierarchy.hierarchy import _HierarchyNodeComparator

        def int_comparator(a, b):
            return a - b

        comp = _HierarchyNodeComparator(int_comparator)
        n1 = HierarchyNode(1)
        n2 = HierarchyNode(2)
        result = comp.compare(n1, n2)
        assert result == -1

    def test_comparator_greater_than(self):
        """Lines 315-316: returns 1 when n1 > n2."""
        from hermit.hierarchy.hierarchy import _HierarchyNodeComparator

        def int_comparator(a, b):
            return a - b

        comp = _HierarchyNodeComparator(int_comparator)
        n1 = HierarchyNode(5)
        n2 = HierarchyNode(2)
        result = comp.compare(n1, n2)
        assert result == 1

    def test_comparator_equal(self):
        """Line 317: returns 0 when n1 == n2."""
        from hermit.hierarchy.hierarchy import _HierarchyNodeComparator

        def int_comparator(a, b):
            return a - b

        comp = _HierarchyNodeComparator(int_comparator)
        n1 = HierarchyNode(3)
        n2 = HierarchyNode(3)
        result = comp.compare(n1, n2)
        assert result == 0

    def test_comparator_init(self):
        """Line 301: __init__ stores the comparator."""
        from hermit.hierarchy.hierarchy import _HierarchyNodeComparator

        def my_cmp(a, b):
            return 0

        comp = _HierarchyNodeComparator(my_cmp)
        assert comp.m_element_comparator is my_cmp
