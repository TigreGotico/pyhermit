"""Deterministic classification algorithm for HermiT.

Faithful port of ``org.semanticweb.HermiT.hierarchy.DeterministicClassification``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from hermit.hierarchy.hierarchy import Hierarchy
from hermit.hierarchy.hierarchy_node import HierarchyNode

if TYPE_CHECKING:
    from hermit.hierarchy.classification_progress_monitor import (
        ClassificationProgressMonitor,
    )
    from hermit.model import AtomicConcept, Individual
    from hermit.tableau.node import Node
    from hermit.tableau.tableau import Tableau

T = TypeVar("T")


class DeterministicClassification(Generic[T]):
    """Classifies atomic concepts using a deterministic tableau.

    This classification algorithm uses the deterministic model generated
    by the tableau to determine all subsumption relationships in a single
    pass, then constructs the hierarchy using Tarjan's SCC algorithm.
    """

    def __init__(
        self,
        tableau: Tableau,
        progress_monitor: ClassificationProgressMonitor,
        top_element: AtomicConcept,
        bottom_element: AtomicConcept,
        elements: set[AtomicConcept],
    ) -> None:
        self.m_tableau = tableau
        self.m_progress_monitor = progress_monitor
        self.m_top_element = top_element
        self.m_bottom_element = bottom_element
        self.m_elements = elements

    def classify(self) -> Hierarchy[AtomicConcept]:
        if not self.m_tableau.is_deterministic():
            raise RuntimeError(
                "DeterministicClassification can only be used with a "
                "deterministic tableau."
            )
        from hermit.model import Atom as AtomCls, Individual

        fresh_individual = Individual.create_anonymous("fresh-individual")
        if not self.m_tableau.is_satisfiable(
            True,
            {AtomCls.create(self.m_top_element, fresh_individual)},
            None,
            None,
            None,
            None,
            None,
            None,
        ):
            return Hierarchy.empty_hierarchy(
                self.m_elements, self.m_top_element, self.m_bottom_element
            )

        all_subsumers: dict[AtomicConcept, GraphNode[AtomicConcept]] = {}
        for element in self.m_elements:
            subsumers: set[AtomicConcept]
            nodes_for_individuals: dict[Individual, Node | None] = {
                fresh_individual: None
            }
            if not self.m_tableau.is_satisfiable(
                True,
                {AtomCls.create(element, fresh_individual)},
                None,
                None,
                None,
                nodes_for_individuals,
                None,
                None,
            ):
                subsumers = set(self.m_elements)
            else:
                subsumers = {self.m_top_element}
                extension_manager = self.m_tableau.get_extension_manager()
                retrieval = extension_manager.get_binary_extension_table().create_retrieval(
                    [False, True], "TOTAL"
                )
                node = nodes_for_individuals[fresh_individual]
                if node is not None:
                    retrieval.get_bindings_buffer()[1] = node.get_canonical_node()
                retrieval.open()
                while not retrieval.after_last():
                    subsumer = retrieval.get_tuple_buffer()[0]
                    if (
                        isinstance(subsumer, AtomicConcept)
                        and subsumer in self.m_elements
                    ):
                        subsumers.add(subsumer)
                    retrieval.next()

            all_subsumers[element] = GraphNode(element, subsumers)
            self.m_progress_monitor.element_classified(element)

        return DeterministicClassification.build_hierarchy(
            self.m_top_element, self.m_bottom_element, all_subsumers
        )

    @staticmethod
    def build_hierarchy(
        top_element: T,
        bottom_element: T,
        graph_nodes: dict[T, GraphNode[T]],
    ) -> Hierarchy[T]:
        """Build a hierarchy from a subsumption graph using Tarjan's SCC."""
        top_node: HierarchyNode[T] = HierarchyNode(top_element)
        bottom_node: HierarchyNode[T] = HierarchyNode(bottom_element)
        hierarchy: Hierarchy[T] = Hierarchy(top_node, bottom_node)

        # Compute SCCs and create hierarchy nodes in topological order.
        topological_order: list[HierarchyNode[T]] = []
        stack: list[GraphNode[T]] = []
        dfs_index = _DFSIndex()
        bottom_graph_node = graph_nodes.get(bottom_element)
        if bottom_graph_node is not None:
            DeterministicClassification._visit(
                stack, dfs_index, graph_nodes, bottom_graph_node, hierarchy, topological_order
            )

        # Process nodes in topological order.
        reachable_from: dict[HierarchyNode[T], set[HierarchyNode[T]]] = {}
        all_successors: list[GraphNode[T]] = []
        for index in range(len(topological_order)):
            node = topological_order[index]
            reachable_from_node: set[HierarchyNode[T]] = {node}
            reachable_from[node] = reachable_from_node
            all_successors.clear()
            for element in node.m_equivalent_elements:
                graph_node = graph_nodes.get(element)
                if graph_node is not None:
                    for successor in graph_node.m_successors:
                        successor_graph_node = graph_nodes.get(successor)
                        if successor_graph_node is not None:
                            all_successors.append(successor_graph_node)

            # Sort successors by topological order (ascending).
            all_successors.sort(
                key=lambda gn: gn.m_topological_order_index
            )
            for successor_index in range(len(all_successors) - 1, -1, -1):
                successor_graph_node = all_successors[successor_index]
                successor_node = hierarchy.m_nodes_by_elements.get(
                    successor_graph_node.m_element
                )
                if successor_node is not None and successor_node not in reachable_from_node:
                    node.m_parent_nodes.add(successor_node)
                    successor_node.m_child_nodes.add(node)
                    reachable_from_node.add(successor_node)
                    reachable_from_node.update(
                        reachable_from.get(successor_node, set())
                    )

        return hierarchy

    @staticmethod
    def _visit(
        stack: list[GraphNode[T]],
        dfs_index: _DFSIndex,
        graph_nodes: dict[T, GraphNode[T]],
        graph_node: GraphNode[T],
        hierarchy: Hierarchy[T],
        topological_order: list[HierarchyNode[T]],
    ) -> None:
        graph_node.m_dfs_index = dfs_index.m_value
        dfs_index.m_value += 1
        graph_node.m_scc_head = graph_node
        stack.append(graph_node)

        for successor in graph_node.m_successors:
            successor_graph_node = graph_nodes.get(successor)
            if successor_graph_node is not None:
                if successor_graph_node.not_visited():
                    DeterministicClassification._visit(
                        stack,
                        dfs_index,
                        graph_nodes,
                        successor_graph_node,
                        hierarchy,
                        topological_order,
                    )
                if (
                    not successor_graph_node.is_assigned_to_scc()
                    and successor_graph_node.m_scc_head is not None
                    and successor_graph_node.m_scc_head.m_dfs_index
                    < graph_node.m_scc_head.m_dfs_index
                ):
                    graph_node.m_scc_head = successor_graph_node.m_scc_head

        if graph_node.m_scc_head is graph_node:
            next_topological_order_index = len(topological_order)
            equivalent_elements: set[T] = set()
            popped_node: GraphNode[T] | None = None
            while True:
                popped_node = stack.pop()
                popped_node.m_topological_order_index = (
                    next_topological_order_index
                )
                equivalent_elements.add(popped_node.m_element)
                if popped_node is graph_node:
                    break

            hierarchy_node: HierarchyNode[T]
            if hierarchy.get_top_node().m_representative in equivalent_elements:
                hierarchy_node = hierarchy.get_top_node()
            elif hierarchy.get_bottom_node().m_representative in equivalent_elements:
                hierarchy_node = hierarchy.get_bottom_node()
            else:
                hierarchy_node = HierarchyNode(graph_node.m_element)

            for element in equivalent_elements:
                hierarchy_node.m_equivalent_elements.add(element)
                hierarchy.m_nodes_by_elements[element] = hierarchy_node

            topological_order.append(hierarchy_node)


class GraphNode(Generic[T]):
    """Graph node used during hierarchy construction.

    Stores an element and its known successors, plus temporary fields
    for Tarjan's SCC algorithm.
    """

    def __init__(self, element: T, successors: set[T]) -> None:
        self.m_element: T = element
        self.m_successors: set[T] = successors
        self.m_dfs_index: int = -1
        self.m_scc_head: GraphNode[T] | None = None
        self.m_topological_order_index: int = -1

    def not_visited(self) -> bool:
        return self.m_dfs_index == -1

    def is_assigned_to_scc(self) -> bool:
        return self.m_topological_order_index != -1


class _TopologicalOrderComparator:
    """Comparator for GraphNode by topological order index."""

    INSTANCE: _TopologicalOrderComparator | None = None

    def __init__(self) -> None:
        pass

    def __call__(self, gn1: GraphNode[Any], gn2: GraphNode[Any]) -> int:
        return gn1.m_topological_order_index - gn2.m_topological_order_index


_TopologicalOrderComparator.INSTANCE = _TopologicalOrderComparator()


class _DFSIndex:
    """Mutable counter for DFS numbering in Tarjan's SCC."""

    def __init__(self) -> None:
        self.m_value: int = 0
