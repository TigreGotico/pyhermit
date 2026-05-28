"""Coverage boost 25 — atomic_concept_element, datatypes/registry, hierarchy_search.

Covers:
- atomic_concept_element.py lines 68, 75 (__str__ with multiple instances)
- datatypes/registry.py line 286 (is_disjoint_with: strings_2 and numeric_1)
- datatypes/registry.py lines 368-379 (conjoin_with_dr)
- hierarchy_search.py lines 72-73, 141-143, 182, 185
"""

from __future__ import annotations

import pytest


class TestAtomicConceptElementStr:
    """Tests for AtomicConceptElement.__str__ with multiple instances (lines 68, 75)."""

    def test_str_multiple_known_instances(self):
        """Lines 68, 75: __str__ with 2+ known and 2+ possible instances."""
        from hermit.hierarchy.atomic_concept_element import AtomicConceptElement
        from hermit.model import Individual

        ind_a = Individual.create("http://test.org#a")
        ind_b = Individual.create("http://test.org#b")
        ind_c = Individual.create("http://test.org#c")

        elem = AtomicConceptElement({ind_a, ind_b}, {ind_c, ind_a})

        s = str(elem)
        assert "known instances" in s
        assert "possible instances" in s


class TestDatatypeRegistryIsDisjoint:
    """Tests for DatatypeRegistry.is_disjoint_with line 286."""

    def test_numeric_disjoint_from_string(self):
        """Line 286: numeric type1, string type2 → True (in_strings_2 branch)."""
        from hermit.datatypes.registry import DatatypeRegistry
        XSD = "http://www.w3.org/2001/XMLSchema#"
        # string is type2, integer is type1 → in_strings_2 and in_numeric_1
        assert DatatypeRegistry.is_disjoint_with(XSD + "integer", XSD + "string")


class TestDatatypeRegistryConjoinWithDr:
    """Tests for DatatypeRegistry.conjoin_with_dr lines 368-379."""

    def test_conjoin_with_dr_basic(self):
        """Lines 368-379: conjoin_with_dr intersects value space with restriction."""
        from hermit.datatypes.registry import DatatypeRegistry
        from hermit.model import DatatypeRestriction, Constant

        XSD = "http://www.w3.org/2001/XMLSchema#"
        c = Constant.create("5", XSD + "integer")
        dr = DatatypeRestriction.create(
            XSD + "integer",
            (XSD + "minInclusive",),
            (c,),
        )
        # Create a value space for integer
        vs = DatatypeRegistry.create_value_space_subset(XSD + "integer", (), ())
        result = DatatypeRegistry.conjoin_with_dr(vs, dr)
        assert result is not None


class TestHierarchySearch:
    """Tests for HierarchySearch lines 72-73, 141-143, 182, 185."""

    def _make_hierarchy(self):
        """Build a small role hierarchy for search tests."""
        from hermit.hierarchy.hierarchy import Hierarchy
        from hermit.model import AtomicRole

        NS = "http://test.org#"
        top = AtomicRole.TOP_OBJECT_ROLE
        bot = AtomicRole.BOTTOM_OBJECT_ROLE
        r = AtomicRole.create(NS + "r")
        s = AtomicRole.create(NS + "s")

        # Build hierarchy with r and s under top, above bottom
        from hermit.hierarchy.hierarchy import HierarchyNode
        top_node = HierarchyNode(top)
        bot_node = HierarchyNode(bot)
        r_node = HierarchyNode(r)
        s_node = HierarchyNode(s)

        # Wire up: top -> r, s -> bot
        top_node.m_child_nodes = {r_node, s_node}
        r_node.m_parent_nodes = {top_node}
        r_node.m_child_nodes = {bot_node}
        s_node.m_parent_nodes = {top_node}
        s_node.m_child_nodes = {bot_node}
        bot_node.m_parent_nodes = {r_node, s_node}

        return top_node, bot_node, r_node, s_node, r, s, top, bot

    def test_hierarchy_search_direct_children(self):
        """Test HierarchySearch.search finds direct children."""
        from hermit.hierarchy.hierarchy_search import HierarchySearch, SearchPredicate
        from hermit.hierarchy.hierarchy import HierarchyNode
        from hermit.model import AtomicRole

        NS = "http://test.org#"
        top_node, bot_node, r_node, s_node, r, s, top, bot = self._make_hierarchy()

        class SubsumesTop(SearchPredicate):
            def get_successor_elements(self, u):
                return u.m_parent_nodes
            def get_predecessor_elements(self, u):
                return u.m_child_nodes
            def true_of(self, u):
                return u.m_representative is top or u.m_representative is r or u.m_representative is s

        result = HierarchySearch.search(SubsumesTop(), {r_node, s_node}, {top_node, r_node, s_node, bot_node})
        assert r_node in result or s_node in result
