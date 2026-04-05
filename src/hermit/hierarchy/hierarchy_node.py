"""Hierarchy node for HermiT classification hierarchies.

Faithful port of ``org.semanticweb.HermiT.hierarchy.HierarchyNode``.
"""

from __future__ import annotations

from collections import deque
from typing import Generic, TypeVar

E = TypeVar("E")


class HierarchyNode(Generic[E]):
    """A node in a classification hierarchy.

    Each node holds a representative element, a set of equivalent elements,
    and links to parent and child nodes.
    """

    __slots__ = (
        "m_representative",
        "m_equivalent_elements",
        "m_parent_nodes",
        "m_child_nodes",
    )

    def __init__(self, representative: E) -> None:
        self.m_representative: E = representative
        self.m_equivalent_elements: set[E] = {representative}
        self.m_parent_nodes: set[HierarchyNode[E]] = set()
        self.m_child_nodes: set[HierarchyNode[E]] = set()

    def get_representative(self) -> E:
        """Return the representative element of this node."""
        return self.m_representative

    def is_equivalent_element(self, element: E) -> bool:
        """Check whether *element* is equivalent to the representative."""
        return element in self.m_equivalent_elements

    def is_ancestor_element(self, ancestor: E) -> bool:
        """Check whether *ancestor* appears in any ancestor node."""
        for node in self._ancestor_bfs({self}):
            if node.is_equivalent_element(ancestor):
                return True
        return False

    def is_descendant_element(self, descendant: E) -> bool:
        """Check whether *descendant* appears in any descendant node."""
        for node in self._descendant_bfs({self}):
            if node.is_equivalent_element(descendant):
                return True
        return False

    def get_equivalent_elements(self) -> frozenset[E]:
        """Return an immutable view of equivalent elements."""
        return frozenset(self.m_equivalent_elements)

    def get_parent_nodes(self) -> frozenset[HierarchyNode[E]]:
        """Return an immutable view of parent nodes."""
        return frozenset(self.m_parent_nodes)

    def get_child_nodes(self) -> frozenset[HierarchyNode[E]]:
        """Return an immutable view of child nodes."""
        return frozenset(self.m_child_nodes)

    def get_ancestor_nodes(self) -> set[HierarchyNode[E]]:
        """Return all ancestor nodes (including this node)."""
        return self._ancestor_bfs({self})

    def get_descendant_nodes(self) -> set[HierarchyNode[E]]:
        """Return all descendant nodes (including this node)."""
        return self._descendant_bfs({self})

    def __str__(self) -> str:
        return str(self.m_equivalent_elements)

    @staticmethod
    def compute_ancestor_nodes(
        input_nodes: set[HierarchyNode[E]],
    ) -> set[HierarchyNode[E]]:
        """BFS over parent links starting from *input_nodes*."""
        result: set[HierarchyNode[E]] = set()
        to_visit: deque[HierarchyNode[E]] = deque(input_nodes)
        while to_visit:
            current = to_visit.popleft()
            if current not in result:
                result.add(current)
                to_visit.extend(current.m_parent_nodes)
        return result

    @staticmethod
    def compute_descendant_nodes(
        input_nodes: set[HierarchyNode[E]],
    ) -> set[HierarchyNode[E]]:
        """BFS over child links starting from *input_nodes*."""
        result: set[HierarchyNode[E]] = set()
        to_visit: deque[HierarchyNode[E]] = deque(input_nodes)
        while to_visit:
            current = to_visit.popleft()
            if current not in result:
                result.add(current)
                to_visit.extend(current.m_child_nodes)
        return result

    # --- internal helpers --------------------------------------------------

    def _ancestor_bfs(
        self, input_nodes: set[HierarchyNode[E]]
    ) -> set[HierarchyNode[E]]:
        result: set[HierarchyNode[E]] = set()
        to_visit: deque[HierarchyNode[E]] = deque(input_nodes)
        while to_visit:
            current = to_visit.popleft()
            if current not in result:
                result.add(current)
                to_visit.extend(current.m_parent_nodes)
        return result

    def _descendant_bfs(
        self, input_nodes: set[HierarchyNode[E]]
    ) -> set[HierarchyNode[E]]:
        result: set[HierarchyNode[E]] = set()
        to_visit: deque[HierarchyNode[E]] = deque(input_nodes)
        while to_visit:
            current = to_visit.popleft()
            if current not in result:
                result.add(current)
                to_visit.extend(current.m_child_nodes)
        return result
