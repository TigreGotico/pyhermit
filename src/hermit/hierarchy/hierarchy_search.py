"""Hierarchy search algorithms for HermiT classification.

Faithful port of ``org.semanticweb.HermiT.hierarchy.HierarchySearch``.
"""

from __future__ import annotations

from collections import deque
from typing import Generic, Protocol, TypeVar

from hermit.hierarchy.hierarchy_node import HierarchyNode

E = TypeVar("E")
U = TypeVar("U")


class Relation(Protocol[E]):
    """Protocol defining the subsumption relation used during hierarchy search."""

    def does_subsume(self, parent: E, child: E) -> bool:
        """Return True if *parent* subsumes *child*."""
        ...


class SearchPredicate(Protocol[U]):
    """Predicate and navigation interface for generic graph search."""

    def get_successor_elements(self, u: U) -> set[U]:
        """Return successors of *u* in the search direction."""
        ...

    def get_predecessor_elements(self, u: U) -> set[U]:
        """Return predecessors of *u* (opposite direction)."""
        ...

    def true_of(self, u: U) -> bool:
        """Return True if the search predicate holds for *u*."""
        ...


class HierarchySearch:
    """Algorithms for finding the position of an element in a hierarchy.

    The search uses a subsumption oracle (``Relation``) to determine
    where a new element fits within the existing hierarchy structure.
    """

    @staticmethod
    def find_position(
        hierarchy_relation: Relation[E],
        element: E,
        top_node: HierarchyNode[E],
        bottom_node: HierarchyNode[E],
    ) -> HierarchyNode[E]:
        """Find where *element* belongs in the hierarchy.

        Returns an existing node if the element is equivalent to a node's
        elements, otherwise creates a new node.
        """
        parent_nodes = HierarchySearch._find_parents(
            hierarchy_relation, element, top_node
        )
        child_nodes = HierarchySearch._find_children(
            hierarchy_relation, element, bottom_node, parent_nodes
        )
        if parent_nodes == child_nodes:
            assert len(parent_nodes) == 1 and len(child_nodes) == 1
            return next(iter(parent_nodes))
        else:
            equivalent_elements: set[E] = {element}
            return HierarchyNode(
                element,
            )
            # We need to construct properly
            new_node: HierarchyNode[E] = HierarchyNode(element)
            new_node.m_equivalent_elements = equivalent_elements
            new_node.m_parent_nodes = parent_nodes
            new_node.m_child_nodes = child_nodes
            return new_node

    @staticmethod
    def _find_parents(
        hierarchy_relation: Relation[E],
        element: E,
        top_node: HierarchyNode[E],
    ) -> set[HierarchyNode[E]]:
        class _ParentPredicate(SearchPredicate[HierarchyNode[E]]):
            def __init__(self) -> None:
                self._relation = hierarchy_relation
                self._element = element

            def get_successor_elements(
                self, u: HierarchyNode[E]
            ) -> set[HierarchyNode[E]]:
                return u.m_child_nodes

            def get_predecessor_elements(
                self, u: HierarchyNode[E]
            ) -> set[HierarchyNode[E]]:
                return u.m_parent_nodes

            def true_of(self, u: HierarchyNode[E]) -> bool:
                return self._relation.does_subsume(
                    u.m_representative, self._element
                )

        return HierarchySearch.search(
            _ParentPredicate(), {top_node}, None
        )

    @staticmethod
    def _find_children(
        hierarchy_relation: Relation[E],
        element: E,
        bottom_node: HierarchyNode[E],
        parent_nodes: set[HierarchyNode[E]],
    ) -> set[HierarchyNode[E]]:
        if len(parent_nodes) == 1 and hierarchy_relation.does_subsume(
            element, next(iter(parent_nodes)).m_representative
        ):
            return parent_nodes

        # Determine the set of nodes that are descendants of each node in
        # parent_nodes (intersection).
        parent_iter = iter(parent_nodes)
        marked: set[HierarchyNode[E]] = set(
            next(parent_iter).get_descendant_nodes()
        )
        for parent_node in parent_iter:
            freshly_marked: set[HierarchyNode[E]] = set()
            visited: set[HierarchyNode[E]] = set()
            to_process: deque[HierarchyNode[E]] = deque()
            to_process.append(parent_node)
            while to_process:
                current_node = to_process.popleft()
                for child_node in current_node.m_child_nodes:
                    if child_node in marked:
                        freshly_marked.add(child_node)
                    elif child_node not in visited:
                        visited.add(child_node)
                        to_process.append(child_node)
            to_process.extend(freshly_marked)
            while to_process:
                current_node = to_process.popleft()
                for child_node in current_node.m_child_nodes:
                    if child_node not in freshly_marked:
                        freshly_marked.add(child_node)
                        to_process.append(child_node)
            marked = freshly_marked

        # Determine the subset of marked that is directly above the
        # bottomNode and that is below the current element.
        above_bottom_nodes: set[HierarchyNode[E]] = set()
        for node in marked:
            if (
                bottom_node in node.m_child_nodes
                and hierarchy_relation.does_subsume(
                    element, node.m_representative
                )
            ):
                above_bottom_nodes.add(node)

        # If this set is empty, omit the bottom search phase.
        if not above_bottom_nodes:
            return {bottom_node}

        class _ChildPredicate(SearchPredicate[HierarchyNode[E]]):
            def __init__(self) -> None:
                self._relation = hierarchy_relation
                self._element = element

            def get_successor_elements(
                self, u: HierarchyNode[E]
            ) -> set[HierarchyNode[E]]:
                return u.m_parent_nodes

            def get_predecessor_elements(
                self, u: HierarchyNode[E]
            ) -> set[HierarchyNode[E]]:
                return u.m_child_nodes

            def true_of(self, u: HierarchyNode[E]) -> bool:
                return self._relation.does_subsume(
                    self._element, u.m_representative
                )

        return HierarchySearch.search(
            _ChildPredicate(), above_bottom_nodes, marked
        )

    @staticmethod
    def search(
        search_predicate: SearchPredicate[U],
        start_search: set[U],
        possibilities: set[U] | None,
    ) -> set[U]:
        """Generic upward search in a DAG.

        Starting from *start_search*, follow successors and collect
        the maximal nodes for which *search_predicate.true_of* holds.
        """
        cache = _SearchCache(search_predicate, possibilities)
        result: set[U] = set()
        visited: set[U] = set(start_search)
        to_process: deque[U] = deque(start_search)
        while to_process:
            current = to_process.popleft()
            found_subordinate_element = False
            subordinate_elements = search_predicate.get_successor_elements(
                current
            )
            for subordinate_element in subordinate_elements:
                if cache.true_of(subordinate_element):
                    found_subordinate_element = True
                    if subordinate_element not in visited:
                        visited.add(subordinate_element)
                        to_process.append(subordinate_element)
            if not found_subordinate_element:
                result.add(current)
        return result


class _SearchCache(Generic[U]):
    """Caches positive/negative evaluations of the search predicate."""

    def __init__(
        self,
        search_predicate: SearchPredicate[U],
        possibilities: set[U] | None,
    ) -> None:
        self.m_search_predicate = search_predicate
        self.m_possibilities = possibilities
        self.m_positives: set[U] = set()
        self.m_negatives: set[U] = set()

    def true_of(self, element: U) -> bool:
        if element in self.m_positives:
            return True
        if element in self.m_negatives or (
            self.m_possibilities is not None and element not in self.m_possibilities
        ):
            return False
        for superordinate_element in self.m_search_predicate.get_predecessor_elements(
            element
        ):
            if not self.true_of(superordinate_element):
                self.m_negatives.add(element)
                return False
        if self.m_search_predicate.true_of(element):
            self.m_positives.add(element)
            return True
        else:
            self.m_negatives.add(element)
            return False
