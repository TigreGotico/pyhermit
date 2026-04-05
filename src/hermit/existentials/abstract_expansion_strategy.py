"""Abstract expansion strategy implementing common existential expansion logic.

Implements the shared functionality of existential expansion strategies,
leaving only the actual processing of existentials in need of expansion
to subclasses.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from hermit.existentials.existential_expansion_strategy import (
    ExistentialExpansionStrategy,
)
from hermit.model import (
    AtLeast,
    AtLeastConcept,
    AtLeastDataRange,
    AtomicRole,
    Inequality,
    InverseRole,
    Role,
)

if TYPE_CHECKING:
    from hermit.blocking.blocking_strategy import BlockingStrategy
    from hermit.model import Concept, DLClause, DataRange, Variable
    from hermit.monitor.tableau_monitor import TableauMonitor
    from hermit.tableau.dl_clause_evaluator import DLClauseEvaluator
    from hermit.tableau.extension_manager import Retrieval as ExtRetrieval
    from hermit.tableau.node import Node
    from hermit.tableau.tableau import Tableau


class SatType(Enum):
    """Satisfaction status for an at-least restriction."""

    NOT_SATISFIED = 0
    PERMANENTLY_SATISFIED = 1
    CURRENTLY_SATISFIED = 2


class AbstractExpansionStrategy(ExistentialExpansionStrategy):
    """Abstract base for existential expansion strategies.

    Implements the common bits of an ExistentialsExpansionStrategy, leaving
    only actual processing of existentials in need of expansion to subclasses.
    """

    def __init__(
        self, blocking_strategy: BlockingStrategy, expand_node_at_a_time: bool
    ) -> None:
        self.m_blocking_strategy = blocking_strategy
        self.m_expand_node_at_a_time = expand_node_at_a_time
        self.m_processed_existentials: list[AtLeast] = []
        self.m_auxiliary_nodes1: list[Node] = []
        self.m_auxiliary_nodes2: list[Node] = []
        self.m_tableau: Tableau | None = None
        self.m_interrupt_flag = None
        self.m_extension_manager = None
        self.m_ternary_extension_table_search01_bound: ExtRetrieval | None = None
        self.m_ternary_extension_table_search02_bound: ExtRetrieval | None = None
        self.m_existential_expansion_manager = None
        self.m_description_graph_manager = None

    def initialize(self, tableau: Tableau) -> None:
        self.m_tableau = tableau
        self.m_interrupt_flag = tableau.m_interrupt_flag
        self.m_extension_manager = tableau.m_extension_manager
        ext_table = self.m_extension_manager.get_ternary_extension_table()
        self.m_ternary_extension_table_search01_bound = ext_table.create_retrieval(
            [True, True, False], "TOTAL"
        )
        self.m_ternary_extension_table_search02_bound = ext_table.create_retrieval(
            [True, False, True], "TOTAL"
        )
        self.m_existential_expansion_manager = tableau.m_existential_expansion_manager
        self.m_description_graph_manager = tableau.m_description_graph_manager
        self.m_blocking_strategy.initialize(tableau)

    def additional_dl_ontology_set(self, additional_dl_ontology: object) -> None:
        self.m_blocking_strategy.additional_dl_ontology_set(additional_dl_ontology)

    def additional_dl_ontology_cleared(self) -> None:
        self.m_blocking_strategy.additional_dl_ontology_cleared()

    def clear(self) -> None:
        self.m_blocking_strategy.clear()
        self.m_processed_existentials.clear()
        if self.m_ternary_extension_table_search01_bound is not None:
            self.m_ternary_extension_table_search01_bound.clear()
        if self.m_ternary_extension_table_search02_bound is not None:
            self.m_ternary_extension_table_search02_bound.clear()

    def expand_existentials(self, final_chance: bool) -> bool:
        monitor: TableauMonitor | None = (
            self.m_tableau.m_tableau_monitor if self.m_tableau else None
        )
        self.m_blocking_strategy.compute_blocking(final_chance)
        extensions_changed = False
        node = self.m_tableau.m_first_tableau_node if self.m_tableau else None
        while node is not None and (
            not extensions_changed or not self.m_expand_node_at_a_time
        ):
            if node.is_active() and not node.is_blocked and node.has_unprocessed_existentials():
                # The node's set of unprocessed existentials may be changed during
                # operation, so make a local copy to loop over.
                self.m_processed_existentials.clear()
                self.m_processed_existentials.extend(node.unprocessed_existentials)
                for index in range(len(self.m_processed_existentials) - 1, -1, -1):
                    existential_concept = self.m_processed_existentials[index]
                    if isinstance(existential_concept, AtLeast):
                        at_least: AtLeast = existential_concept
                        sat = self._is_satisfied(at_least, node)
                        if sat == SatType.NOT_SATISFIED:
                            self._expand_existential(at_least, node)
                            extensions_changed = True
                        elif sat == SatType.PERMANENTLY_SATISFIED:
                            # Not satisfied by a nominal so that the NN/NI rule
                            # can break the existential.
                            self.m_existential_expansion_manager.mark_existential_processed(
                                existential_concept, node
                            )
                            if monitor is not None:
                                monitor.existential_satisfied(
                                    existential_concept, node
                                )
                        # CURRENTLY_SATISFIED: do nothing
                        elif monitor is not None:
                            monitor.existential_satisfied(existential_concept, node)
                    else:
                        from hermit.model import ExistsDescriptionGraph

                        if isinstance(existential_concept, ExistsDescriptionGraph):
                            exists_description_graph: ExistsDescriptionGraph = (
                                existential_concept
                            )
                            if not self.m_description_graph_manager.is_satisfied(
                                exists_description_graph, node
                            ):
                                self.m_description_graph_manager.expand(
                                    exists_description_graph, node
                                )
                                extensions_changed = True
                            elif monitor is not None:
                                monitor.existential_satisfied(
                                    exists_description_graph, node
                                )
                            self.m_existential_expansion_manager.mark_existential_processed(
                                existential_concept, node
                            )
                        else:
                            raise RuntimeError("Unsupported type of existential.")
                    self.m_interrupt_flag.check_interrupt()
            node = node.next_tableau_node
            if self.m_interrupt_flag is not None:
                self.m_interrupt_flag.check_interrupt()
        return extensions_changed

    def assertion_added_concept(
        self, concept: Concept, node: Node, is_core: bool
    ) -> None:
        self.m_blocking_strategy.assertion_added_concept(concept, node, is_core)

    def assertion_core_set_concept(self, concept: Concept, node: Node) -> None:
        self.m_blocking_strategy.assertion_core_set_concept(concept, node)

    def assertion_removed_concept(
        self, concept: Concept, node: Node, is_core: bool
    ) -> None:
        self.m_blocking_strategy.assertion_removed_concept(concept, node, is_core)

    def assertion_added_data_range(
        self, data_range: DataRange, node: Node, is_core: bool
    ) -> None:
        self.m_blocking_strategy.assertion_added_data_range(data_range, node, is_core)

    def assertion_core_set_data_range(self, data_range: DataRange, node: Node) -> None:
        self.m_blocking_strategy.assertion_core_set_data_range(data_range, node)

    def assertion_removed_data_range(
        self, data_range: DataRange, node: Node, is_core: bool
    ) -> None:
        self.m_blocking_strategy.assertion_removed_data_range(data_range, node, is_core)

    def assertion_added_atomic_role(
        self, atomic_role: AtomicRole, node_from: Node, node_to: Node, is_core: bool
    ) -> None:
        self.m_blocking_strategy.assertion_added_atomic_role(
            atomic_role, node_from, node_to, is_core
        )

    def assertion_core_set_atomic_role(
        self, atomic_role: AtomicRole, node_from: Node, node_to: Node
    ) -> None:
        self.m_blocking_strategy.assertion_core_set_atomic_role(
            atomic_role, node_from, node_to
        )

    def assertion_removed_atomic_role(
        self, atomic_role: AtomicRole, node_from: Node, node_to: Node, is_core: bool
    ) -> None:
        self.m_blocking_strategy.assertion_removed_atomic_role(
            atomic_role, node_from, node_to, is_core
        )

    def nodes_merged(self, merge_from: Node, merge_into: Node) -> None:
        self.m_blocking_strategy.nodes_merged(merge_from, merge_into)

    def nodes_unmerged(self, merge_from: Node, merge_into: Node) -> None:
        self.m_blocking_strategy.nodes_unmerged(merge_from, merge_into)

    def node_status_changed(self, node: Node) -> None:
        self.m_blocking_strategy.node_status_changed(node)

    def node_initialized(self, node: Node) -> None:
        self.m_blocking_strategy.node_initialized(node)

    def node_destroyed(self, node: Node) -> None:
        self.m_blocking_strategy.node_destroyed(node)

    def branching_point_pushed(self) -> None:
        pass

    def backtrack(self) -> None:
        pass

    def model_found(self) -> None:
        self.m_blocking_strategy.model_found()

    def is_exact(self) -> bool:
        return self.m_blocking_strategy.is_exact()

    def dl_clause_body_compiled(
        self,
        workers: list[DLClauseEvaluator.Worker],
        dl_clause: DLClause,
        variables: list[Variable],
        values_buffer: list[object | None],
        core_variables: list[bool],
    ) -> None:
        self.m_blocking_strategy.dl_clause_body_compiled(
            workers, dl_clause, variables, values_buffer, core_variables
        )

    def _is_satisfied(self, at_least: AtLeast, for_node: Node) -> SatType:
        """Check whether *at_least* is satisfied for *for_node*."""
        cardinality = at_least.get_number()
        if cardinality <= 0:
            return SatType.PERMANENTLY_SATISFIED

        on_role: Role = at_least.get_on_role()
        retrieval: ExtRetrieval
        to_node_index: int
        if isinstance(on_role, AtomicRole):
            retrieval = self.m_ternary_extension_table_search01_bound  # type: ignore[assignment]
            retrieval.get_bindings_buffer()[0] = on_role
            retrieval.get_bindings_buffer()[1] = for_node
            to_node_index = 2
        else:
            retrieval = self.m_ternary_extension_table_search02_bound  # type: ignore[assignment]
            assert isinstance(on_role, InverseRole)
            retrieval.get_bindings_buffer()[0] = on_role.get_inverse_of()
            retrieval.get_bindings_buffer()[2] = for_node
            to_node_index = 1

        if cardinality == 1:
            retrieval.open()
            tuple_buffer = retrieval.get_tuple_buffer()
            while not retrieval.after_last():
                to_node: Node = tuple_buffer[to_node_index]  # type: ignore[assignment]
                if isinstance(at_least, AtLeastDataRange):
                    at_least_dr: AtLeastDataRange = at_least
                    to_data_range = at_least_dr.get_to_data_range()
                    if self.m_extension_manager.contains_data_range_assertion(  # type: ignore[union-attr]
                        to_data_range, to_node
                    ):
                        is_perm = self._is_permanent_satisfier(for_node, to_node)
                        is_perm_assert = (
                            self.m_blocking_strategy.is_permanent_assertion(  # type: ignore[union-attr]
                                to_data_range, to_node
                            )
                        )
                        if is_perm and is_perm_assert:
                            return SatType.PERMANENTLY_SATISFIED
                        return SatType.CURRENTLY_SATISFIED
                else:
                    at_least_c: AtLeastConcept = at_least  # type: ignore[assignment]
                    to_concept = at_least_c.get_to_concept()
                    if (
                        not to_node.is_blocked or for_node.is_parent_of(to_node)
                    ) and self.m_extension_manager.contains_concept_assertion(  # type: ignore[union-attr]
                        to_concept, to_node
                    ):
                        is_perm = self._is_permanent_satisfier(for_node, to_node)
                        is_perm_assert = (
                            self.m_blocking_strategy.is_permanent_assertion(  # type: ignore[union-attr]
                                to_concept, to_node
                            )
                        )
                        if is_perm and is_perm_assert:
                            return SatType.PERMANENTLY_SATISFIED
                        return SatType.CURRENTLY_SATISFIED
                retrieval.next()
            return SatType.NOT_SATISFIED
        else:
            self.m_auxiliary_nodes1.clear()
            retrieval.open()
            tuple_buffer = retrieval.get_tuple_buffer()
            all_satisfiers_are_permanent = True
            while not retrieval.after_last():
                to_node = tuple_buffer[to_node_index]  # type: ignore[assignment]
                if isinstance(at_least, AtLeastDataRange):
                    at_least_dr = at_least
                    to_data_range = at_least_dr.get_to_data_range()
                    if self.m_extension_manager.contains_data_range_assertion(  # type: ignore[union-attr]
                        to_data_range, to_node
                    ):
                        if (
                            not self._is_permanent_satisfier(for_node, to_node)
                            or not self.m_blocking_strategy.is_permanent_assertion(  # type: ignore[union-attr]
                                to_data_range, to_node
                            )
                        ):
                            all_satisfiers_are_permanent = False
                        self.m_auxiliary_nodes1.append(to_node)
                else:
                    at_least_c = at_least  # type: ignore[assignment]
                    to_concept = at_least_c.get_to_concept()
                    if (
                        not to_node.is_blocked or for_node.is_parent_of(to_node)
                    ) and self.m_extension_manager.contains_concept_assertion(  # type: ignore[union-attr]
                        to_concept, to_node
                    ):
                        if (
                            not self._is_permanent_satisfier(for_node, to_node)
                            or not self.m_blocking_strategy.is_permanent_assertion(  # type: ignore[union-attr]
                                to_concept, to_node
                            )
                        ):
                            all_satisfiers_are_permanent = False
                        self.m_auxiliary_nodes1.append(to_node)
                retrieval.next()
            if len(self.m_auxiliary_nodes1) >= cardinality:
                self.m_auxiliary_nodes2.clear()
                if self._contains_subset_of_n_unequal_nodes(
                    for_node,
                    self.m_auxiliary_nodes1,
                    0,
                    self.m_auxiliary_nodes2,
                    cardinality,
                ):
                    return (
                        SatType.PERMANENTLY_SATISFIED
                        if all_satisfiers_are_permanent
                        else SatType.CURRENTLY_SATISFIED
                    )
            return SatType.NOT_SATISFIED

    def _is_permanent_satisfier(self, for_node: Node, to_node: Node) -> bool:
        """Return True if the satisfier is permanent (won't be undone by backtracking)."""
        return (
            for_node is to_node
            or for_node.parent is to_node
            or to_node.parent is for_node
            or to_node.is_root_node()
        )

    def _contains_subset_of_n_unequal_nodes(
        self,
        for_node: Node,
        nodes: list[Node],
        start_at: int,
        selected_nodes: list[Node],
        cardinality: int,
    ) -> bool:
        """Check if there exists a subset of *cardinality* mutually unequal nodes."""
        if len(selected_nodes) == cardinality:
            return True
        index = start_at
        while index < len(nodes):
            node = nodes[index]
            for selected_node in selected_nodes:
                if not self.m_extension_manager.contains_assertion(  # type: ignore[union-attr]
                    Inequality.INSTANCE, node, selected_node
                ) and not self.m_extension_manager.contains_assertion(  # type: ignore[union-attr]
                    Inequality.INSTANCE, selected_node, node
                ):
                    break
            else:
                selected_nodes.append(node)
                if self._contains_subset_of_n_unequal_nodes(
                    for_node, nodes, index + 1, selected_nodes, cardinality
                ):
                    return True
                selected_nodes.pop()
            index += 1
        return False

    def _expand_existential(self, at_least: AtLeast, for_node: Node) -> None:
        """Perform the actual expansion of an existential restriction.

        Subclasses must implement this method.
        """
        raise NotImplementedError
