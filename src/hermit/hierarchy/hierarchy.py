"""Hierarchy data structure for HermiT classification.

Faithful port of ``org.semanticweb.HermiT.hierarchy.Hierarchy``.
"""

from __future__ import annotations

from collections.abc import Collection
from io import StringIO
from typing import Generic, Protocol, TypeVar

from hermit.hierarchy.hierarchy_node import HierarchyNode

E = TypeVar("E")
T = TypeVar("T")
E_contra = TypeVar("E_contra", contravariant=True)
T_proto = TypeVar("T_proto")


class HierarchyNodeVisitor(Protocol[E]):
    """Visitor for depth-first traversal of a hierarchy."""

    def redirect(self, nodes: list[HierarchyNode[E]]) -> bool:
        """Optionally redirect the current node and parent.

        Args:
            nodes: A two-element list [current_node, parent_node] that can be
                modified to redirect traversal.

        Returns:
            True to continue visiting, False to skip.
        """
        ...

    def visit(
        self,
        level: int,
        node: HierarchyNode[E],
        parent_node: HierarchyNode[E] | None,
        first_visit: bool,
    ) -> None:
        """Called for each visited node."""
        ...


class Transformer(Protocol[E_contra, T_proto]):
    """Transforms elements from one type to another during hierarchy copying."""

    def transform(self, element: E_contra) -> T_proto:
        """Transform a single element."""
        ...

    def determine_representative(
        self, old_representative: E_contra, new_equivalent_elements: set[T_proto]
    ) -> T_proto:
        """Choose the representative for a newly created node."""
        ...


class Hierarchy(Generic[E]):
    """A subsumption hierarchy with top and bottom nodes.

    The hierarchy is a directed acyclic graph where edges go from
    subsumers (parents) to subsumees (children).
    """

    def __init__(
        self,
        top_node: HierarchyNode[E],
        bottom_node: HierarchyNode[E],
    ) -> None:
        self.m_top_node: HierarchyNode[E] = top_node
        self.m_bottom_node: HierarchyNode[E] = bottom_node
        self.m_nodes_by_elements: dict[E, HierarchyNode[E]] = {}
        for element in top_node.m_equivalent_elements:
            self.m_nodes_by_elements[element] = top_node
        for element in bottom_node.m_equivalent_elements:
            self.m_nodes_by_elements[element] = bottom_node

    def get_top_node(self) -> HierarchyNode[E]:
        return self.m_top_node

    def get_bottom_node(self) -> HierarchyNode[E]:
        return self.m_bottom_node

    def is_empty(self) -> bool:
        return (
            len(self.m_nodes_by_elements) == 2
            and len(self.m_top_node.m_equivalent_elements) == 1
            and len(self.m_bottom_node.m_equivalent_elements) == 1
        )

    def get_node_for_element(self, element: E) -> HierarchyNode[E] | None:
        return self.m_nodes_by_elements.get(element)

    def get_all_nodes(self) -> Collection[HierarchyNode[E]]:
        return list(self.m_nodes_by_elements.values())

    def get_all_nodes_set(self) -> set[HierarchyNode[E]]:
        return set(self.m_nodes_by_elements.values())

    def get_all_elements(self) -> set[E]:
        return set(self.m_nodes_by_elements.keys())

    def get_depth(self) -> int:
        depth_finder = _HierarchyDepthFinder[E](self.m_bottom_node)
        self.traverse_depth_first(depth_finder)
        return depth_finder.depth

    def transform(
        self,
        transformer: Transformer[E, T],
        comparator: object | None,  # Comparator[T] | None
    ) -> Hierarchy[T]:
        """Create a new hierarchy with transformed elements.

        Args:
            transformer: Transforms elements from type E to T.
            comparator: If not None, uses sorted (TreeSet-like) containers.
                Since Python dicts are insertion-ordered, this primarily
                affects element set ordering.

        Returns:
            A new Hierarchy[T].
        """
        old_to_new: dict[HierarchyNode[E], HierarchyNode[T]] = {}
        for old_node in self.m_nodes_by_elements.values():
            new_equivalent_elements: set[T] = set()
            new_parent_nodes: set[HierarchyNode[T]] = set()
            new_child_nodes: set[HierarchyNode[T]] = set()

            for old_element in old_node.m_equivalent_elements:
                new_element = transformer.transform(old_element)
                new_equivalent_elements.add(new_element)

            new_representative = transformer.determine_representative(
                old_node.m_representative, new_equivalent_elements
            )
            new_node = HierarchyNode[T](
                new_representative
            )
            new_node.m_equivalent_elements = new_equivalent_elements
            new_node.m_parent_nodes = new_parent_nodes
            new_node.m_child_nodes = new_child_nodes
            old_to_new[old_node] = new_node

        for old_parent_node in self.m_nodes_by_elements.values():
            new_parent_node = old_to_new[old_parent_node]
            for old_child_node in old_parent_node.m_child_nodes:
                new_child_node = old_to_new[old_child_node]
                new_parent_node.m_child_nodes.add(new_child_node)
                new_child_node.m_parent_nodes.add(new_parent_node)

        new_top_node = old_to_new[self.m_top_node]
        new_bottom_node = old_to_new[self.m_bottom_node]
        new_hierarchy: Hierarchy[T] = Hierarchy(new_top_node, new_bottom_node)
        for new_node in old_to_new.values():
            for new_element in new_node.m_equivalent_elements:
                new_hierarchy.m_nodes_by_elements[new_element] = new_node
        return new_hierarchy

    def traverse_depth_first(self, visitor: HierarchyNodeVisitor[E]) -> None:
        redirect_buffer: list[HierarchyNode[E] | None] = [None, None]
        visited: set[HierarchyNode[E]] = set()
        self._traverse_depth_first(
            visitor, 0, self.m_top_node, None, visited, redirect_buffer
        )

    def _traverse_depth_first(
        self,
        visitor: HierarchyNodeVisitor[E],
        level: int,
        node: HierarchyNode[E],
        parent_node: HierarchyNode[E] | None,
        visited: set[HierarchyNode[E]],
        redirect_buffer: list[HierarchyNode[E] | None],
    ) -> None:
        redirect_buffer[0] = node
        redirect_buffer[1] = parent_node
        if visitor.redirect(redirect_buffer):  # type: ignore[arg-type]
            node = redirect_buffer[0]  # type: ignore[assignment]
            parent_node = redirect_buffer[1]
            first_visit = node not in visited
            if first_visit:
                visited.add(node)
            visitor.visit(level, node, parent_node, first_visit)
            if first_visit:
                for child_node in node.m_child_nodes:
                    self._traverse_depth_first(
                        visitor,
                        level + 1,
                        child_node,
                        node,
                        visited,
                        redirect_buffer,
                    )

    def __str__(self) -> str:
        buffer = StringIO()

        class _StringVisitor(HierarchyNodeVisitor[E]):
            def redirect(self, nodes: list[HierarchyNode[E]]) -> bool:
                return True

            def visit(
                self,
                level: int,
                node: HierarchyNode[E],
                parent_node: HierarchyNode[E] | None,
                first_visit: bool,
            ) -> None:
                if node != hierarchy.m_bottom_node:
                    self._print_node(level, node, parent_node, first_visit)

            def _print_node(
                self,
                level: int,
                node: HierarchyNode[E],
                parent_node: HierarchyNode[E] | None,
                first_visit: bool,
            ) -> None:
                equivalences = node.get_equivalent_elements()
                print_sub_class_of = parent_node is not None
                print_equivalences = first_visit and len(equivalences) > 1
                if print_sub_class_of or print_equivalences:
                    buffer.write("    " * level)
                    buffer.write(str(node.get_representative()))
                    if print_equivalences:
                        buffer.write("[")
                        first = True
                        for element in equivalences:
                            if node.get_representative() != element:
                                if not first:
                                    buffer.write(" ")
                                else:
                                    first = False
                                buffer.write(str(element))
                        buffer.write("]")
                    if print_sub_class_of:
                        assert parent_node is not None
                        buffer.write(" -> ")
                        buffer.write(str(parent_node.get_representative()))
                    buffer.write("\n")

        hierarchy = self
        self.traverse_depth_first(_StringVisitor())
        buffer.flush()
        return buffer.getvalue()

    @staticmethod
    def empty_hierarchy(
        elements: Collection[T], top_element: T, bottom_element: T
    ) -> Hierarchy[T]:
        top_bottom_node: HierarchyNode[T] = HierarchyNode(top_element)
        top_bottom_node.m_equivalent_elements.add(top_element)
        top_bottom_node.m_equivalent_elements.add(bottom_element)
        top_bottom_node.m_equivalent_elements.update(elements)
        return Hierarchy[T](top_bottom_node, top_bottom_node)

    @staticmethod
    def trivial_hierarchy(top_element: T, bottom_element: T) -> Hierarchy[T]:
        top_node: HierarchyNode[T] = HierarchyNode(top_element)
        top_node.m_equivalent_elements.add(top_element)
        bottom_node: HierarchyNode[T] = HierarchyNode(bottom_element)
        bottom_node.m_equivalent_elements.add(bottom_element)
        top_node.m_child_nodes.add(bottom_node)
        bottom_node.m_parent_nodes.add(top_node)
        return Hierarchy[T](top_node, bottom_node)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _HierarchyDepthFinder(Generic[E]):
    """Visitor that computes the maximum depth of the hierarchy."""

    def __init__(self, bottom_node: HierarchyNode[E]) -> None:
        self.m_bottom_node: HierarchyNode[E] = bottom_node
        self.depth: int = 0

    def redirect(self, nodes: list[HierarchyNode[E]]) -> bool:
        return True

    def visit(
        self,
        level: int,
        node: HierarchyNode[E],
        parent_node: HierarchyNode[E] | None,
        first_visit: bool,
    ) -> None:
        if node == self.m_bottom_node and level > self.depth:
            self.depth = level


class _HierarchyNodeComparator(Generic[E]):
    """Comparator for HierarchyNode based on representative element."""

    def __init__(self, element_comparator: object) -> None:
        self.m_element_comparator = element_comparator

    def compare(
        self, n1: HierarchyNode[E], n2: HierarchyNode[E]
    ) -> int:
        from functools import cmp_to_key
        from typing import Any
        from collections.abc import Callable

        comparator: Callable[[Any, Any], int] = self.m_element_comparator  # type: ignore[assignment]
        cmp = cmp_to_key(comparator)
        k1 = cmp(n1.m_representative)
        k2 = cmp(n2.m_representative)
        if k1 < k2:
            return -1
        elif k1 > k2:
            return 1
        return 0
