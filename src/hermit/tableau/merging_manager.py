"""Merging manager -- handles the merge rule for tableau nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from hermit.tableau.dependency_set import DependencySet

if TYPE_CHECKING:
    from hermit.monitor import TableauMonitor
    from hermit.tableau.extension_manager import ExtensionManager
    from hermit.tableau.node import Node
    from hermit.tableau.tableau import Tableau


class MergingManager:
    """Implements the merge rule for combining tableau nodes.

    When an equality assertion *a = b* is derived, the merging manager
    determines which node to merge into which (based on node type
    precedence and structural constraints), copies all assertions, and
    prunes the absorbed node's subtree.

    Args:
        tableau: The owning tableau.
    """

    __slots__ = (
        "m_tableau",
        "m_tableau_monitor",
        "m_extension_manager",
        "m_binary_extension_table_search_1_bound",
        "m_ternary_extension_table_search_1_bound",
        "m_ternary_extension_table_search_2_bound",
        "m_binary_auxiliary_tuple",
        "m_ternary_auxiliary_tuple",
        "m_binary_union_dependency_set",
    )

    def __init__(self, tableau: Tableau) -> None:
        self.m_tableau = tableau
        self.m_tableau_monitor: TableauMonitor | None = tableau.m_tableau_monitor
        self.m_extension_manager: ExtensionManager = tableau.m_extension_manager
        self.m_binary_extension_table_search_1_bound = (
            self.m_extension_manager.m_binary_extension_table.create_retrieval(
                [False, True], "TOTAL"
            )
        )
        self.m_ternary_extension_table_search_1_bound = (
            self.m_extension_manager.m_ternary_extension_table.create_retrieval(
                [False, True, False], "TOTAL"
            )
        )
        self.m_ternary_extension_table_search_2_bound = (
            self.m_extension_manager.m_ternary_extension_table.create_retrieval(
                [False, False, True], "TOTAL"
            )
        )
        self.m_binary_auxiliary_tuple: list[Any] = [None, None]
        self.m_ternary_auxiliary_tuple: list[Any] = [None, None, None]
        self.m_binary_union_dependency_set = _UnionDependencySet(2)

    def clear(self) -> None:
        """Reset all auxiliary buffers and retrievals."""
        self.m_binary_extension_table_search_1_bound.clear()
        self.m_ternary_extension_table_search_1_bound.clear()
        self.m_ternary_extension_table_search_2_bound.clear()
        self.m_binary_auxiliary_tuple[0] = None
        self.m_binary_auxiliary_tuple[1] = None
        self.m_ternary_auxiliary_tuple[0] = None
        self.m_ternary_auxiliary_tuple[1] = None
        self.m_ternary_auxiliary_tuple[2] = None

    def merge_nodes(
        self,
        node0: Node,
        node1: Node,
        dependency_set: DependencySet,
    ) -> bool:
        """Merge two nodes, choosing the merge direction automatically.

        Args:
            node0: First node.
            node1: Second node.
            dependency_set: The dependency set that triggered the merge.

        Returns:
            ``True`` if a merge was performed.
        """
        from hermit.model import DescriptionGraph

        assert node0.node_type is not None and node1.node_type is not None
        assert node0.node_type.is_abstract == node1.node_type.is_abstract

        if not node0.is_active() or not node1.is_active() or node0 is node1:
            return False

        # --- Decide merge direction ---
        merge_from: Node
        merge_into: Node

        node0_precedence = node0.node_type.merge_precedence
        node1_precedence = node1.node_type.merge_precedence

        if node0_precedence < node1_precedence:
            merge_from = node1
            merge_into = node0
        elif node0_precedence > node1_precedence:
            merge_from = node0
            merge_into = node1
        else:
            # Same precedence -- use structural constraints
            node0_cluster_anchor = node0.cluster_anchor
            node1_cluster_anchor = node1.cluster_anchor

            can_merge_0_into_1 = (
                node0.m_parent is node1.m_parent
                or self._is_descendant_of_at_most_three_levels(
                    node0, node1_cluster_anchor
                )
            )
            can_merge_1_into_0 = (
                node0.m_parent is node1.m_parent
                or self._is_descendant_of_at_most_three_levels(
                    node1, node0_cluster_anchor
                )
            )

            if can_merge_0_into_1 and can_merge_1_into_0:
                # Pick the one with fewer positive concepts to merge into
                if (
                    node0.m_number_of_positive_atomic_concepts
                    > node1.m_number_of_positive_atomic_concepts
                ):
                    merge_from = node1
                    merge_into = node0
                else:
                    merge_from = node0
                    merge_into = node1
            elif can_merge_0_into_1:
                merge_from = node0
                merge_into = node1
            elif can_merge_1_into_0:
                merge_from = node1
                merge_into = node0
            else:
                raise RuntimeError("Internal error: unsupported merge type.")

        if self.m_tableau_monitor is not None:
            self.m_tableau_monitor.merge_started(merge_from, merge_into)

        # --- Prune the subtree rooted at merge_from ---
        node: Node | None = merge_from
        while node is not None:
            if (
                node.is_active()
                and node.m_parent is not None
                and (not node.m_parent.is_active() or node.m_parent is merge_from)
            ):
                if self.m_tableau_monitor is not None:
                    self.m_tableau_monitor.node_pruned(node)
                self.m_tableau.prune_node(node)
            node = node.m_next_tableau_node

        # --- Copy unary assertions ---
        self.m_binary_union_dependency_set.m_dependency_sets[1] = dependency_set
        self.m_binary_auxiliary_tuple[1] = merge_into

        retrieval1 = self.m_binary_extension_table_search_1_bound
        retrieval1.get_bindings_buffer()[1] = merge_from
        retrieval1.open()
        tuple_buffer = retrieval1.get_tuple_buffer()
        while not retrieval1.after_last():
            predicate = tuple_buffer[0]
            if not isinstance(predicate, DescriptionGraph):
                self.m_binary_auxiliary_tuple[0] = predicate
                if self.m_tableau_monitor is not None:
                    self.m_tableau_monitor.merge_fact_started(
                        merge_from, merge_into, tuple_buffer, self.m_binary_auxiliary_tuple
                    )
                self.m_binary_union_dependency_set.m_dependency_sets[0] = (
                    retrieval1.get_dependency_set()
                )
                self.m_extension_manager.add_tuple(
                    self.m_binary_auxiliary_tuple,
                    self.m_binary_union_dependency_set,
                    retrieval1.is_core(),
                )
                if self.m_tableau_monitor is not None:
                    self.m_tableau_monitor.merge_fact_finished(
                        merge_from, merge_into, tuple_buffer, self.m_binary_auxiliary_tuple
                    )
            retrieval1.next()

        # --- Copy ternary assertions where merge_from is in position 1 ---
        self.m_ternary_auxiliary_tuple[1] = merge_into

        retrieval2 = self.m_ternary_extension_table_search_1_bound
        retrieval2.get_bindings_buffer()[1] = merge_from
        retrieval2.open()
        tuple_buffer = retrieval2.get_tuple_buffer()
        while not retrieval2.after_last():
            predicate = tuple_buffer[0]
            if not isinstance(predicate, DescriptionGraph):
                self.m_ternary_auxiliary_tuple[0] = predicate
                self.m_ternary_auxiliary_tuple[2] = (
                    merge_into if tuple_buffer[2] is merge_from else tuple_buffer[2]
                )
                if self.m_tableau_monitor is not None:
                    self.m_tableau_monitor.merge_fact_started(
                        merge_from, merge_into, tuple_buffer, self.m_ternary_auxiliary_tuple
                    )
                self.m_binary_union_dependency_set.m_dependency_sets[0] = (
                    retrieval2.get_dependency_set()
                )
                self.m_extension_manager.add_tuple(
                    self.m_ternary_auxiliary_tuple,
                    self.m_binary_union_dependency_set,
                    retrieval2.is_core(),
                )
                if self.m_tableau_monitor is not None:
                    self.m_tableau_monitor.merge_fact_finished(
                        merge_from, merge_into, tuple_buffer, self.m_ternary_auxiliary_tuple
                    )
            retrieval2.next()

        # --- Copy ternary assertions where merge_from is in position 2 ---
        self.m_ternary_auxiliary_tuple[2] = merge_into

        retrieval3 = self.m_ternary_extension_table_search_2_bound
        retrieval3.get_bindings_buffer()[2] = merge_from
        retrieval3.open()
        tuple_buffer = retrieval3.get_tuple_buffer()
        while not retrieval3.after_last():
            predicate = tuple_buffer[0]
            if not isinstance(predicate, DescriptionGraph):
                self.m_ternary_auxiliary_tuple[0] = predicate
                self.m_ternary_auxiliary_tuple[1] = (
                    merge_into if tuple_buffer[1] is merge_from else tuple_buffer[1]
                )
                if self.m_tableau_monitor is not None:
                    self.m_tableau_monitor.merge_fact_started(
                        merge_from, merge_into, tuple_buffer, self.m_ternary_auxiliary_tuple
                    )
                self.m_binary_union_dependency_set.m_dependency_sets[0] = (
                    retrieval3.get_dependency_set()
                )
                self.m_extension_manager.add_tuple(
                    self.m_ternary_auxiliary_tuple,
                    self.m_binary_union_dependency_set,
                    retrieval3.is_core(),
                )
                if self.m_tableau_monitor is not None:
                    self.m_tableau_monitor.merge_fact_finished(
                        merge_from, merge_into, tuple_buffer, self.m_ternary_auxiliary_tuple
                    )
            retrieval3.next()

        # --- Merge description graphs ---
        from hermit.tableau.union_dependency_set import UnionDependencySet as _UDS
        self.m_tableau.m_description_graph_manager.merge_graphs(
            merge_from, merge_into, cast(_UDS, self.m_binary_union_dependency_set)
        )

        # --- Finally merge the nodes ---
        self.m_tableau.merge_node(merge_from, merge_into, dependency_set)

        if self.m_tableau_monitor is not None:
            self.m_tableau_monitor.merge_finished(merge_from, merge_into)

        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_descendant_of_at_most_three_levels(
        self, descendant: Node, ancestor: Node | None
    ) -> bool:
        """Check ancestry up to three levels.

        Merges over more than three levels should not happen in practice.

        Args:
            descendant: The potential descendant node.
            ancestor: The potential ancestor node (may be None).

        Returns:
            ``True`` if *descendant* is within three levels of *ancestor*.
        """
        if descendant is not None:
            parent = descendant.m_parent
            if parent is ancestor:
                return True
            if parent is not None:
                grandparent = parent.m_parent
                if grandparent is ancestor:
                    return True
                if grandparent is not None:
                    great_grandparent = grandparent.m_parent
                    if great_grandparent is ancestor:
                        return True
        return False


class _UnionDependencySet(DependencySet):
    """Minimal union-of-two dependency sets used inline by MergingManager."""

    __slots__ = ("m_dependency_sets", "m_number_of_constituents")

    def __init__(self, n: int) -> None:
        self.m_dependency_sets: list[Any] = [None] * n
        self.m_number_of_constituents = n

    def contains_branching_point(self, branching_point: int) -> bool:
        for ds in self.m_dependency_sets:
            if ds is not None and ds.contains_branching_point(branching_point):
                return True
        return False

    def is_empty(self) -> bool:
        for ds in self.m_dependency_sets:
            if ds is not None and not ds.is_empty():
                return False
        return True

    def get_maximum_branching_point(self) -> int:
        maximum = -1
        for ds in self.m_dependency_sets:
            if ds is not None:
                bp = ds.get_maximum_branching_point()
                if bp > maximum:
                    maximum = bp
        return maximum
