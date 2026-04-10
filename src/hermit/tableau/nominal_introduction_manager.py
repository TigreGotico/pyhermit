"""Nominal introduction manager.

Implements the nominal introduction rule (NI rule) which handles
nominals (named individuals) during tableau expansion.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from typing import cast

from hermit.tableau.branching_point import BranchingPoint
from hermit.tableau.dependency_set import DependencySet
from hermit.tableau.tuple_table import TupleTable
from hermit.tableau.tuple_table_full_index import TupleTableFullIndex

if TYPE_CHECKING:
    from hermit.model import AnnotatedEquality
    from hermit.tableau.node import Node
    from hermit.tableau.tableau import Tableau


class NominalIntroductionManager:
    """Implements the nominal introduction rule."""

    def __init__(self, tableau: Tableau) -> None:
        self.m_tableau = tableau
        self.m_dependency_set_factory = tableau.m_dependency_set_factory
        self.m_interrupt_flag = tableau.m_interrupt_flag
        self.m_merging_manager = tableau.m_merging_manager
        self.m_annotated_equalities = TupleTable(5)
        self.m_buffer_for_annotated_equality: list[object | None] = [None] * 5
        self.m_new_root_nodes_table = TupleTable(4)
        self.m_new_root_nodes_index = TupleTableFullIndex(
            self.m_new_root_nodes_table, 3
        )
        self.m_buffer_for_root_nodes: list[object | None] = [None] * 4
        self.m_indices_by_branching_point: list[int] = [0] * (10 * 2)
        self.m_first_unprocessed_annotated_equality = 0

    def clear(self) -> None:
        """Clear all accumulated state."""
        self.m_annotated_equalities.clear()
        for i in range(len(self.m_buffer_for_annotated_equality) - 1, -1, -1):
            self.m_buffer_for_annotated_equality[i] = None
        self.m_new_root_nodes_table.clear()
        self.m_new_root_nodes_index.clear()
        for i in range(len(self.m_buffer_for_root_nodes) - 1, -1, -1):
            self.m_buffer_for_root_nodes[i] = None
        self.m_first_unprocessed_annotated_equality = 0

    def branching_point_pushed(self) -> None:
        """Save state at the current branching point."""
        start = self.m_tableau.m_current_branching_point + 1
        start_idx = start * 3
        required_size = start_idx + 3
        if required_size > len(self.m_indices_by_branching_point):
            new_size = len(self.m_indices_by_branching_point) * 3 // 2
            while required_size > new_size:
                new_size = new_size * 3 // 2
            new_indices = [0] * new_size
            new_indices[: len(self.m_indices_by_branching_point)] = (
                self.m_indices_by_branching_point
            )
            self.m_indices_by_branching_point = new_indices
        self.m_indices_by_branching_point[start_idx] = (
            self.m_first_unprocessed_annotated_equality
        )
        self.m_indices_by_branching_point[start_idx + 1] = (
            self.m_annotated_equalities.first_free_tuple_index
        )
        self.m_indices_by_branching_point[start_idx + 2] = (
            self.m_new_root_nodes_table.first_free_tuple_index
        )

    def backtrack(self) -> None:
        """Restore state to the current branching point."""
        start = self.m_tableau.m_current_branching_point + 1
        start_idx = start * 3
        self.m_first_unprocessed_annotated_equality = (
            self.m_indices_by_branching_point[start_idx]
        )
        first_free_annotated = self.m_indices_by_branching_point[start_idx + 1]
        for tuple_index in range(
            self.m_annotated_equalities.first_free_tuple_index - 1,
            first_free_annotated - 1,
            -1,
        ):
            from hermit.tableau.permanent_dependency_set import PermanentDependencySet

            perm_ds = self.m_annotated_equalities.get_tuple_object(tuple_index, 4)
            if isinstance(perm_ds, PermanentDependencySet):
                self.m_dependency_set_factory.remove_usage(perm_ds)
        self.m_annotated_equalities.truncate(first_free_annotated)
        first_free_root = self.m_indices_by_branching_point[start_idx + 2]
        for tuple_index in range(
            self.m_new_root_nodes_table.first_free_tuple_index - 1,
            first_free_root - 1,
            -1,
        ):
            self.m_new_root_nodes_index.remove_tuple(tuple_index)
        self.m_new_root_nodes_table.truncate(first_free_root)

    def process_annotated_equalities(self) -> bool:
        """Process all pending annotated equalities.

        Returns True if any changes were made.
        """
        result = False
        while (
            self.m_first_unprocessed_annotated_equality
            < self.m_annotated_equalities.first_free_tuple_index
        ):
            self.m_annotated_equalities.retrieve_tuple(
                self.m_buffer_for_annotated_equality,
                self.m_first_unprocessed_annotated_equality,
            )
            self.m_first_unprocessed_annotated_equality += 1
            annotated_equality: AnnotatedEquality = (
                self.m_buffer_for_annotated_equality[0]  # type: ignore[assignment]
            )
            node0: Node = self.m_buffer_for_annotated_equality[1]  # type: ignore[assignment]
            node1: Node = self.m_buffer_for_annotated_equality[2]  # type: ignore[assignment]
            node2: Node = self.m_buffer_for_annotated_equality[3]  # type: ignore[assignment]
            dependency_set: DependencySet = self.m_buffer_for_annotated_equality[4]  # type: ignore[assignment]
            if self._apply_ni_rule(
                annotated_equality, node0, node1, node2, dependency_set
            ):
                result = True
            self.m_interrupt_flag.check_interrupt()
        return result

    def can_forget_annotation(
        self,
        annotated_equality: AnnotatedEquality,
        node0: Node,
        node1: Node,
        node2: Node,
    ) -> bool:
        """Check if the annotation can be forgotten (nodes are stable)."""
        return (
            node0.is_root_node()
            or node1.is_root_node()
            or not node2.is_root_node()
            or (node2.is_parent_of(node0) and node2.is_parent_of(node1))
        )

    def add_annotated_equality(
        self,
        annotated_equality: AnnotatedEquality,
        node0: Node,
        node1: Node,
        node2: Node,
        dependency_set: DependencySet,
    ) -> bool:
        """Add an annotated equality, possibly triggering the NI rule immediately."""
        if not node0.is_active() or not node1.is_active() or not node2.is_active():
            return False
        if self.can_forget_annotation(annotated_equality, node0, node1, node2):
            return self.m_merging_manager.merge_nodes(node0, node1, dependency_set)
        if annotated_equality.cardinality == 1:
            return self._apply_ni_rule(
                annotated_equality, node0, node1, node2, dependency_set
            )
        permanent_dependency_set = self.m_dependency_set_factory.get_permanent(
            dependency_set
        )
        self.m_buffer_for_annotated_equality[0] = annotated_equality
        self.m_buffer_for_annotated_equality[1] = node0
        self.m_buffer_for_annotated_equality[2] = node1
        self.m_buffer_for_annotated_equality[3] = node2
        self.m_buffer_for_annotated_equality[4] = permanent_dependency_set
        self.m_dependency_set_factory.add_usage(permanent_dependency_set)
        self.m_annotated_equalities.add_tuple(self.m_buffer_for_annotated_equality)
        return True

    def _apply_ni_rule(
        self,
        annotated_equality: AnnotatedEquality,
        node0: Node,
        node1: Node,
        node2: Node,
        dependency_set: DependencySet,
    ) -> bool:
        """Apply the nominal introduction rule."""
        if node0.is_pruned() or node1.is_pruned() or node2.is_pruned():
            return False
        dependency_set = node0.add_canonical_node_dependency_set(dependency_set)
        dependency_set = node1.add_canonical_node_dependency_set(dependency_set)
        dependency_set = node2.add_canonical_node_dependency_set(dependency_set)
        node0 = node0.get_canonical_node()
        node1 = node1.get_canonical_node()
        node2 = node2.get_canonical_node()
        if self.can_forget_annotation(annotated_equality, node0, node1, node2):
            return self.m_merging_manager.merge_nodes(node0, node1, dependency_set)
        if not node0.is_root_node() and not node2.is_parent_of(node0):
            ni_target_node = node0
            other_node = node1
        else:
            ni_target_node = node1
            other_node = node0
        if self.m_tableau.m_tableau_monitor is not None:
            self.m_tableau.m_tableau_monitor.nominal_introduction_started(
                node2, ni_target_node, annotated_equality, node0, node1
            )
        if annotated_equality.cardinality > 1:
            branching_point = _NominalIntroductionBranchingPoint(
                self.m_tableau,
                node2,
                ni_target_node,
                other_node,
                annotated_equality,
            )
            self.m_tableau._push_branching_point(branching_point)
            dependency_set = self.m_tableau.m_dependency_set_factory.add_branching_point(
                dependency_set, branching_point.level
            )
        new_root_node = self._get_ni_root_for(
            dependency_set, node2, annotated_equality, 1
        )
        if not new_root_node.is_active():
            assert new_root_node.is_merged()
            dependency_set = new_root_node.add_canonical_node_dependency_set(
                dependency_set
            )
            new_root_node = new_root_node.get_canonical_node()
        self.m_merging_manager.merge_nodes(ni_target_node, new_root_node, dependency_set)
        if not other_node.is_pruned():
            dependency_set = other_node.add_canonical_node_dependency_set(
                dependency_set
            )
            self.m_merging_manager.merge_nodes(
                other_node.get_canonical_node(), new_root_node, dependency_set
            )
        if self.m_tableau.m_tableau_monitor is not None:
            self.m_tableau.m_tableau_monitor.nominal_introduction_finished(
                node2, ni_target_node, annotated_equality, node0, node1
            )
        return True

    def _get_ni_root_for(
        self,
        dependency_set: DependencySet,
        root_node: Node,
        annotated_equality: AnnotatedEquality,
        number: int,
    ) -> Node:
        """Get or create the NI root node for a given configuration."""
        self.m_buffer_for_root_nodes[0] = root_node
        self.m_buffer_for_root_nodes[1] = annotated_equality
        self.m_buffer_for_root_nodes[2] = number
        tuple_index = self.m_new_root_nodes_index.get_tuple_index_with_positions(
            self.m_buffer_for_root_nodes,
            [0, 1, 2],
        )
        if tuple_index == -1:
            new_root_node = self.m_tableau._create_new_ni_node(dependency_set)
            self.m_buffer_for_root_nodes[3] = new_root_node
            self.m_new_root_nodes_index.add_tuple(
                self.m_buffer_for_root_nodes,
                self.m_new_root_nodes_table.first_free_tuple_index,
            )
            self.m_new_root_nodes_table.add_tuple(self.m_buffer_for_root_nodes)
            return new_root_node
        return cast("Node", self.m_new_root_nodes_table.get_tuple_object(tuple_index, 3))


class _NominalIntroductionBranchingPoint(BranchingPoint):
    """Branching point for nominal introduction choices."""

    def __init__(
        self,
        tableau: Tableau,
        root_node: Node,
        ni_target_node: Node,
        other_node: Node,
        annotated_equality: AnnotatedEquality,
    ) -> None:
        super().__init__(tableau)
        self.m_root_node = root_node
        self.m_ni_target_node = ni_target_node
        self.m_other_node = other_node
        self.m_annotated_equality = annotated_equality
        self.m_current_root_node = 1  # First merge is performed from the manager

    def start_next_choice(
        self, tableau: Tableau, clash_dependency_set: DependencySet
    ) -> None:
        self.m_current_root_node += 1
        assert self.m_current_root_node <= self.m_annotated_equality.cardinality
        dependency_set = clash_dependency_set
        if self.m_current_root_node == self.m_annotated_equality.cardinality:
            dependency_set = tableau.m_dependency_set_factory.remove_branching_point(
                dependency_set, self.level
            )
        # Access the NI manager via tableau
        ni_manager = tableau.m_nominal_introduction_manager
        assert isinstance(ni_manager, NominalIntroductionManager)
        new_root_node = ni_manager._get_ni_root_for(
            dependency_set,
            self.m_root_node,
            self.m_annotated_equality,
            self.m_current_root_node,
        )
        if not new_root_node.is_active():
            assert new_root_node.is_merged()
            dependency_set = new_root_node.add_canonical_node_dependency_set(
                dependency_set
            )
            new_root_node = new_root_node.get_canonical_node()
        tableau.m_merging_manager.merge_nodes(
            self.m_ni_target_node, new_root_node, dependency_set
        )
        if not self.m_other_node.is_pruned():
            dependency_set = self.m_other_node.add_canonical_node_dependency_set(
                dependency_set
            )
            tableau.m_merging_manager.merge_nodes(
                self.m_other_node.get_canonical_node(), new_root_node, dependency_set
            )
