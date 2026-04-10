"""Description graph manager.

Manages description graph expansion and constraint checking during
tableau reasoning. Description graphs are used to encode complex
existential structures efficiently.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hermit.tableau.union_dependency_set import UnionDependencySet

if TYPE_CHECKING:
    from hermit.model import DescriptionGraph, ExistsDescriptionGraph
    from hermit.tableau.extension_manager import ExtensionTable, Retrieval
    from hermit.tableau.node import Node
    from hermit.tableau.tableau import Tableau


class DescriptionGraphManager:
    """Manages description graphs in the tableau."""

    def __init__(self, tableau: Tableau) -> None:
        self.m_tableau = tableau
        self.m_interrupt_flag = tableau.m_interrupt_flag
        self.m_tableau_monitor = tableau.m_tableau_monitor
        self.m_extension_manager = tableau.m_extension_manager
        self.m_merging_manager = tableau.m_merging_manager
        self.m_occurrence_manager = _OccurrenceManager()
        self.m_description_graph_indices: dict[DescriptionGraph, int] = {}
        extension_tables_set: set[ExtensionTable] = set()
        description_graphs_by_index: list[DescriptionGraph] = []
        extension_tables_by_index: list[ExtensionTable] = []
        for description_graph in tableau.m_permanent_dl_ontology.get_all_description_graphs():
            self.m_description_graph_indices[description_graph] = len(
                description_graphs_by_index
            )
            description_graphs_by_index.append(description_graph)
            extension_table = self.m_extension_manager.get_extension_table(
                description_graph.arity() + 1
            )
            extension_tables_by_index.append(extension_table)
            extension_tables_set.add(extension_table)
        self.m_description_graphs_by_index: list[DescriptionGraph] = (
            description_graphs_by_index
        )
        self.m_extension_tables_by_index: list[ExtensionTable] = extension_tables_by_index
        self.m_auxiliary_tuples1: list[list[object | None]] = []
        self.m_auxiliary_tuples2: list[list[object | None]] = []
        for dg in self.m_description_graphs_by_index:
            size = dg.arity() + 1
            self.m_auxiliary_tuples1.append([None] * size)
            self.m_auxiliary_tuples2.append([None] * size)
        self.m_new_nodes: list[Node] = []
        self.m_binary_union_dependency_set = UnionDependencySet(2)
        self.m_delta_old_retrievals: list[Retrieval] = []
        for extension_table in extension_tables_set:
            self.m_delta_old_retrievals.append(
                extension_table.create_retrieval(
                    [False] * extension_table.m_tuple_arity, "DELTA_OLD"
                )
            )

    def clear(self) -> None:
        """Clear all accumulated state."""
        for i in range(len(self.m_auxiliary_tuples1)):
            for j in range(len(self.m_auxiliary_tuples1[i])):
                self.m_auxiliary_tuples1[i][j] = None
                self.m_auxiliary_tuples2[i][j] = None
        self.m_occurrence_manager.clear()
        for tup in self.m_auxiliary_tuples1:
            for i in range(len(tup)):
                tup[i] = None
        for tup in self.m_auxiliary_tuples2:
            for i in range(len(tup)):
                tup[i] = None
        self.m_new_nodes.clear()
        self.m_binary_union_dependency_set.m_dependency_sets[0] = None
        self.m_binary_union_dependency_set.m_dependency_sets[1] = None
        for retrieval in self.m_delta_old_retrievals:
            retrieval.clear()

    def get_description_graph_tuple(
        self, graph_index: int, tuple_index: int
    ) -> list[object | None]:
        """Retrieve a description graph tuple by index."""
        description_graph = self.m_description_graphs_by_index[graph_index]
        extension_table = self.m_extension_tables_by_index[graph_index]
        tup: list[object | None] = [None] * (description_graph.arity() + 1)
        extension_table.m_tuple_table.retrieve_tuple(tup, tuple_index)
        return tup

    def check_graph_constraints(self) -> bool:
        """Check description graph constraints for consistency.

        Returns True if any changes were made.
        """
        has_change = False
        for retrieval_index in range(len(self.m_delta_old_retrievals)):
            if self.m_extension_manager.contains_clash():
                break
            retrieval = self.m_delta_old_retrievals[retrieval_index]
            extension_table = retrieval.get_extension_table()
            retrieval.open()
            tuple_buffer = retrieval.get_tuple_buffer()
            arity = len(tuple_buffer)
            while not retrieval.after_last() and not self.m_extension_manager.contains_clash():
                if isinstance(tuple_buffer[0], DescriptionGraph):
                    this_graph_index = self.m_description_graph_indices[tuple_buffer[0]]
                    this_tuple_index = retrieval.get_current_tuple_index()
                    for this_position_in_tuple in range(1, arity):
                        node: Node = tuple_buffer[this_position_in_tuple]
                        list_node = node.m_first_graph_occurrence_node
                        while list_node != -1:
                            graph_index = self.m_occurrence_manager.get_list_node_component(
                                list_node, _OccurrenceManager.GRAPH_INDEX
                            )
                            tuple_index = self.m_occurrence_manager.get_list_node_component(
                                list_node, _OccurrenceManager.TUPLE_INDEX
                            )
                            position_in_tuple = self.m_occurrence_manager.get_list_node_component(
                                list_node, _OccurrenceManager.POSITION_IN_TUPLE
                            )
                            if (
                                this_graph_index == graph_index
                                and (
                                    this_tuple_index != tuple_index
                                    or this_position_in_tuple != position_in_tuple
                                )
                                and extension_table.is_tuple_active(tuple_index)
                            ):
                                self.m_binary_union_dependency_set.m_dependency_sets[0] = (
                                    retrieval.get_dependency_set()
                                )
                                self.m_binary_union_dependency_set.m_dependency_sets[1] = (
                                    extension_table.get_dependency_set_by_index(tuple_index)
                                )
                                if self.m_tableau_monitor is not None:
                                    self.m_tableau_monitor.description_graph_checking_started(
                                        this_graph_index,
                                        this_tuple_index,
                                        this_position_in_tuple,
                                        graph_index,
                                        tuple_index,
                                        position_in_tuple,
                                    )
                                if this_position_in_tuple == position_in_tuple:
                                    for merge_position in range(arity - 1, 0, -1):
                                        node_first = extension_table.m_tuple_table.get_tuple_object(
                                            this_tuple_index, merge_position
                                        )
                                        node_second = extension_table.m_tuple_table.get_tuple_object(
                                            tuple_index, merge_position
                                        )
                                        if node_first != node_second:
                                            self.m_merging_manager.merge_nodes(
                                                node_first,
                                                node_second,
                                                self.m_binary_union_dependency_set,
                                            )
                                            has_change = True
                                        self.m_interrupt_flag.check_interrupt()
                                else:
                                    self.m_extension_manager.set_clash(
                                        self.m_binary_union_dependency_set
                                    )
                                    has_change = True
                                if self.m_tableau_monitor is not None:
                                    self.m_tableau_monitor.description_graph_checking_finished(
                                        this_graph_index,
                                        this_tuple_index,
                                        this_position_in_tuple,
                                        graph_index,
                                        tuple_index,
                                        position_in_tuple,
                                    )
                            list_node = self.m_occurrence_manager.get_list_node_component(
                                list_node, _OccurrenceManager.NEXT_NODE
                            )
                            self.m_interrupt_flag.check_interrupt()
                retrieval.next()
            self.m_interrupt_flag.check_interrupt()
        return has_change

    def is_satisfied(
        self, exists_description_graph: ExistsDescriptionGraph, node: Node
    ) -> bool:
        """Check if an exists-description-graph is satisfied for a node."""
        graph_index = self.m_description_graph_indices[
            exists_description_graph.description_graph
        ]
        position_in_tuple = exists_description_graph.vertex + 1
        list_node = node.m_first_graph_occurrence_node
        while list_node != -1:
            if (
                graph_index
                == self.m_occurrence_manager.get_list_node_component(
                    list_node, _OccurrenceManager.GRAPH_INDEX
                )
                and position_in_tuple
                == self.m_occurrence_manager.get_list_node_component(
                    list_node, _OccurrenceManager.POSITION_IN_TUPLE
                )
            ):
                return True
            list_node = self.m_occurrence_manager.get_list_node_component(
                list_node, _OccurrenceManager.NEXT_NODE
            )
        return False

    def merge_graphs(
        self,
        merge_from: Node,
        merge_into: Node,
        binary_union_dependency_set: UnionDependencySet,
    ) -> None:
        """Merge graph occurrences from one node to another."""
        list_node = merge_from.m_first_graph_occurrence_node
        while list_node != -1:
            graph_index = self.m_occurrence_manager.get_list_node_component(
                list_node, _OccurrenceManager.GRAPH_INDEX
            )
            tuple_index = self.m_occurrence_manager.get_list_node_component(
                list_node, _OccurrenceManager.TUPLE_INDEX
            )
            position_in_tuple = self.m_occurrence_manager.get_list_node_component(
                list_node, _OccurrenceManager.POSITION_IN_TUPLE
            )
            extension_table = self.m_extension_tables_by_index[graph_index]
            auxiliary_tuple = self.m_auxiliary_tuples1[graph_index]
            extension_table.m_tuple_table.retrieve_tuple(auxiliary_tuple, tuple_index)
            if extension_table.is_tuple_active(tuple_index):
                self.m_binary_union_dependency_set.m_dependency_sets[0] = (
                    extension_table.get_dependency_set_by_index(tuple_index)
                )
                is_core = extension_table.is_core_by_index(tuple_index)
                if self.m_tableau_monitor is not None:
                    source_tuple = self.m_auxiliary_tuples2[graph_index]
                    for i in range(len(auxiliary_tuple)):
                        source_tuple[i] = auxiliary_tuple[i]
                    auxiliary_tuple[position_in_tuple] = merge_into
                    self.m_tableau_monitor.merge_fact_started(
                        merge_from, merge_into, source_tuple, auxiliary_tuple
                    )
                    self.m_extension_manager.add_tuple(
                        auxiliary_tuple, self.m_binary_union_dependency_set, is_core
                    )
                    self.m_tableau_monitor.merge_fact_finished(
                        merge_from, merge_into, source_tuple, auxiliary_tuple
                    )
                else:
                    auxiliary_tuple[position_in_tuple] = merge_into
                    self.m_extension_manager.add_tuple(
                        auxiliary_tuple, self.m_binary_union_dependency_set, is_core
                    )
            list_node = self.m_occurrence_manager.get_list_node_component(
                list_node, _OccurrenceManager.NEXT_NODE
            )

    def description_graph_tuple_added(self, tuple_index: int, tup: list[object]) -> None:
        """Called when a description graph tuple is added."""
        graph_index = self.m_description_graph_indices[tup[0]]  # type: ignore[index]
        for position_in_tuple in range(len(tup) - 1, 0, -1):
            node: Node = tup[position_in_tuple]  # type: ignore[assignment]
            list_node = self.m_occurrence_manager.new_list_node()
            self.m_occurrence_manager.initialize_list_node(
                list_node,
                graph_index,
                tuple_index,
                position_in_tuple,
                node.m_first_graph_occurrence_node,
            )
            node.m_first_graph_occurrence_node = list_node

    def description_graph_tuple_removed(self, tuple_index: int, tup: list[object]) -> None:
        """Called when a description graph tuple is removed."""
        for position_in_tuple in range(len(tup) - 1, 0, -1):
            node: Node = tup[position_in_tuple]  # type: ignore[assignment]
            list_node = node.m_first_graph_occurrence_node
            assert (
                self.m_occurrence_manager.get_list_node_component(
                    list_node, _OccurrenceManager.GRAPH_INDEX
                )
                == self.m_description_graph_indices[tup[0]]  # type: ignore[index]
            )
            assert (
                self.m_occurrence_manager.get_list_node_component(
                    list_node, _OccurrenceManager.TUPLE_INDEX
                )
                == tuple_index
            )
            assert (
                self.m_occurrence_manager.get_list_node_component(
                    list_node, _OccurrenceManager.POSITION_IN_TUPLE
                )
                == position_in_tuple
            )
            node.m_first_graph_occurrence_node = (
                self.m_occurrence_manager.get_list_node_component(
                    list_node, _OccurrenceManager.NEXT_NODE
                )
            )
            self.m_occurrence_manager.delete_list_node(list_node)

    def expand(
        self, exists_description_graph: ExistsDescriptionGraph, for_node: Node
    ) -> None:
        """Expand an exists-description-graph existential."""
        if self.m_tableau.m_tableau_monitor is not None:
            self.m_tableau.m_tableau_monitor.existential_expansion_started(
                exists_description_graph, for_node
            )
        self.m_new_nodes.clear()
        description_graph = exists_description_graph.description_graph
        dependency_set = self.m_extension_manager.get_concept_assertion_dependency_set(
            exists_description_graph, for_node
        )
        assert dependency_set is not None
        graph_index = self.m_description_graph_indices[description_graph]
        auxiliary_tuple = self.m_auxiliary_tuples1[graph_index]
        auxiliary_tuple[0] = description_graph
        for vertex in range(description_graph.arity()):
            if vertex == exists_description_graph.vertex:
                new_node = for_node
            else:
                new_node = self.m_tableau.create_new_graph_node(
                    for_node.cluster_anchor, dependency_set
                )
            self.m_new_nodes.append(new_node)
            auxiliary_tuple[vertex + 1] = new_node
        self.m_extension_manager.add_tuple(auxiliary_tuple, dependency_set, True)
        # Replace all nodes with the canonical node because nodes might have been merged
        for vertex in range(description_graph.arity()):
            new_node = self.m_new_nodes[vertex]
            dependency_set = new_node.add_canonical_node_dependency_set(dependency_set)
            self.m_new_nodes[vertex] = new_node.get_canonical_node()
        # Add the graph layout
        for vertex in range(description_graph.arity()):
            self.m_extension_manager.add_concept_assertion(
                description_graph.atomic_concept_for_vertex(vertex),
                self.m_new_nodes[vertex],
                dependency_set,
                True,
            )
        for edge_index in range(description_graph.number_of_edges()):
            edge = description_graph.edge(edge_index)
            self.m_extension_manager.add_role_assertion(
                edge.atomic_role,
                self.m_new_nodes[edge.from_vertex],
                self.m_new_nodes[edge.to_vertex],
                dependency_set,
                True,
            )
        self.m_new_nodes.clear()
        if self.m_tableau.m_tableau_monitor is not None:
            self.m_tableau.m_tableau_monitor.existential_expansion_finished(
                exists_description_graph, for_node
            )

    def initialise_node(self, node: Node) -> None:
        """Initialize graph occurrence tracking for a new node."""
        node.m_first_graph_occurrence_node = -1

    def destroy_node(self, node: Node) -> None:
        """Clean up graph occurrence tracking for a destroyed node."""
        list_node = node.m_first_graph_occurrence_node
        while list_node != -1:
            next_list_node = self.m_occurrence_manager.get_list_node_component(
                list_node, _OccurrenceManager.NEXT_NODE
            )
            self.m_occurrence_manager.delete_list_node(list_node)
            list_node = next_list_node
        node.m_first_graph_occurrence_node = -1


class _OccurrenceManager:
    """Manages linked lists of graph occurrence nodes per tableau node."""

    GRAPH_INDEX = 0
    TUPLE_INDEX = 1
    POSITION_IN_TUPLE = 2
    NEXT_NODE = 3
    LIST_NODE_SIZE = 4
    LIST_NODE_PAGE_SIZE = LIST_NODE_SIZE * 512

    def __init__(self) -> None:
        self.m_node_pages: list[list[int] | None] = [None] * 10
        self.m_node_pages[0] = [0] * _OccurrenceManager.LIST_NODE_PAGE_SIZE
        self.m_number_of_pages = 1
        self.m_first_free_list_node = 0
        self.set_list_node_component(
            self.m_first_free_list_node, _OccurrenceManager.NEXT_NODE, -1
        )

    def clear(self) -> None:
        """Reset the occurrence manager."""
        self.m_first_free_list_node = 0
        self.set_list_node_component(
            self.m_first_free_list_node, _OccurrenceManager.NEXT_NODE, -1
        )

    def get_list_node_component(self, list_node: int, component: int) -> int:
        """Get an int component from a list node."""
        page = self.m_node_pages[list_node // _OccurrenceManager.LIST_NODE_PAGE_SIZE]
        assert page is not None
        return page[(list_node % _OccurrenceManager.LIST_NODE_PAGE_SIZE) + component]

    def set_list_node_component(
        self, list_node: int, component: int, value: int
    ) -> None:
        """Set an int component on a list node."""
        page = self.m_node_pages[list_node // _OccurrenceManager.LIST_NODE_PAGE_SIZE]
        assert page is not None
        page[(list_node % _OccurrenceManager.LIST_NODE_PAGE_SIZE) + component] = value

    def initialize_list_node(
        self,
        list_node: int,
        graph_index: int,
        tuple_index: int,
        position_in_tuple: int,
        next_list_node: int,
    ) -> None:
        """Initialize all components of a list node."""
        page_index = list_node // _OccurrenceManager.LIST_NODE_PAGE_SIZE
        index_in_page = list_node % _OccurrenceManager.LIST_NODE_PAGE_SIZE
        node_page = self.m_node_pages[page_index]
        assert node_page is not None
        node_page[index_in_page + _OccurrenceManager.GRAPH_INDEX] = graph_index
        node_page[index_in_page + _OccurrenceManager.TUPLE_INDEX] = tuple_index
        node_page[index_in_page + _OccurrenceManager.POSITION_IN_TUPLE] = (
            position_in_tuple
        )
        node_page[index_in_page + _OccurrenceManager.NEXT_NODE] = next_list_node

    def new_list_node(self) -> int:
        """Allocate a new list node."""
        new_list_node = self.m_first_free_list_node
        next_free_list_node = self.get_list_node_component(
            self.m_first_free_list_node, _OccurrenceManager.NEXT_NODE
        )
        if next_free_list_node != -1:
            self.m_first_free_list_node = next_free_list_node
        else:
            self.m_first_free_list_node += _OccurrenceManager.LIST_NODE_SIZE
            page_index = (
                self.m_first_free_list_node // _OccurrenceManager.LIST_NODE_PAGE_SIZE
            )
            if page_index >= self.m_number_of_pages:
                if page_index >= len(self.m_node_pages):
                    new_node_pages: list[list[int] | None] = [None] * (
                        len(self.m_node_pages) * 3 // 2
                    )
                    new_node_pages[: len(self.m_node_pages)] = self.m_node_pages
                    self.m_node_pages = new_node_pages
                self.m_node_pages[page_index] = [0] * (
                    _OccurrenceManager.LIST_NODE_PAGE_SIZE
                )
                self.m_number_of_pages += 1
            self.set_list_node_component(
                self.m_first_free_list_node, _OccurrenceManager.NEXT_NODE, -1
            )
        return new_list_node

    def delete_list_node(self, list_node: int) -> None:
        """Return a list node to the free pool."""
        self.set_list_node_component(
            list_node, _OccurrenceManager.NEXT_NODE, self.m_first_free_list_node
        )
        self.m_first_free_list_node = list_node
