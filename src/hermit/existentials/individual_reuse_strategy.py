"""Individual reuse strategy for existential expansion.

This strategy attempts to reuse existing individuals (nodes) when expanding
existential restrictions, reducing the overall number of nodes created.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from hermit.existentials.abstract_expansion_strategy import AbstractExpansionStrategy
from hermit.model import AtomicConcept
from hermit.tableau.tuple_table import TupleTable

if TYPE_CHECKING:
    from hermit.blocking.blocking_strategy import BlockingStrategy
    from hermit.model import AtLeast, AtLeastConcept
    from hermit.tableau.branching_point import BranchingPoint
    from hermit.tableau.dependency_set import DependencySet
    from hermit.tableau.node import Node
    from hermit.tableau.tableau import Tableau


@dataclass
class NodeBranchingPointPair:
    """Pairs a reused node with the branching point level at which it was created."""

    m_node: Node
    m_branching_point: int


class IndividualReuseStrategy(AbstractExpansionStrategy):
    """Strategy that reuses existing individuals when expanding existentials."""

    def __init__(
        self, strategy: BlockingStrategy, is_deterministic: bool
    ) -> None:
        super().__init__(strategy, True)
        self.m_is_deterministic = is_deterministic
        self.m_reused_nodes: dict[AtomicConcept, NodeBranchingPointPair] = {}
        self.m_do_reuse_concepts_always: set[AtomicConcept] = set()
        self.m_dont_reuse_concepts_this_run: set[AtomicConcept] = set()
        self.m_dont_reuse_concepts_ever: set[AtomicConcept] = set()
        self.m_reuse_backtracking_table = TupleTable(1)
        self.m_auxiliary_buffer: list[object | None] = [None]
        self.m_indices_by_branching_point: list[int] = [0] * 10

    def initialize(self, tableau: Tableau) -> None:
        super().initialize(tableau)
        self.m_do_reuse_concepts_always.clear()
        self.m_dont_reuse_concepts_ever.clear()
        object_val = tableau.m_parameters.get("IndividualReuseStrategy.reuseAlways")
        if isinstance(object_val, set):
            self.m_do_reuse_concepts_always.update(object_val)  # type: ignore[arg-type]
        object_val = tableau.m_parameters.get("IndividualReuseStrategy.reuseNever")
        if isinstance(object_val, set):
            self.m_dont_reuse_concepts_ever.update(object_val)  # type: ignore[arg-type]

    def clear(self) -> None:
        super().clear()
        self.m_reused_nodes.clear()
        self.m_reuse_backtracking_table.clear()
        self.m_dont_reuse_concepts_this_run.clear()
        self.m_dont_reuse_concepts_this_run.update(self.m_dont_reuse_concepts_ever)

    def branching_point_pushed(self) -> None:
        assert self.m_tableau is not None
        start = self.m_tableau.m_current_branching_point + 1
        required_size = start + 1
        if required_size > len(self.m_indices_by_branching_point):
            new_size = len(self.m_indices_by_branching_point) * 3 // 2
            while required_size > new_size:
                new_size = new_size * 3 // 2
            new_indices = [0] * new_size
            new_indices[: len(self.m_indices_by_branching_point)] = (
                self.m_indices_by_branching_point
            )
            self.m_indices_by_branching_point = new_indices
        self.m_indices_by_branching_point[start] = (
            self.m_reuse_backtracking_table.first_free_tuple_index
        )

    def backtrack(self) -> None:
        assert self.m_tableau is not None
        required_first_free = self.m_indices_by_branching_point[
            self.m_tableau.m_current_branching_point + 1
        ]
        for index in range(
            self.m_reuse_backtracking_table.first_free_tuple_index - 1, required_first_free - 1, -1
        ):
            reuse_concept = self.m_reuse_backtracking_table.get_tuple_object(
                index, 0
            )
            assert isinstance(reuse_concept, AtomicConcept)
            result = self.m_reused_nodes.pop(reuse_concept, None)
            assert result is not None
        self.m_reuse_backtracking_table.truncate(required_first_free)

    def model_found(self) -> None:
        self.m_dont_reuse_concepts_ever.update(self.m_dont_reuse_concepts_this_run)

    def is_deterministic(self) -> bool:
        return self.m_is_deterministic

    def get_concept_for_node(self, node: Node) -> AtomicConcept | None:
        for concept, pair in self.m_reused_nodes.items():
            if pair.m_node is node:
                return concept
        return None

    def get_dont_reuse_concepts_ever(self) -> set[AtomicConcept]:
        return self.m_dont_reuse_concepts_ever

    def _expand_existential(self, at_least: AtLeast, for_node: Node) -> None:
        # Mark existential as processed BEFORE branching takes place!
        self.m_existential_expansion_manager.mark_existential_processed(  # type: ignore[union-attr]
            at_least, for_node
        )
        if not self.m_existential_expansion_manager.try_functional_expansion(  # type: ignore[union-attr]
            at_least, for_node
        ):
            from hermit.model import AtLeastDataRange

            if isinstance(at_least, AtLeastDataRange):
                self.m_existential_expansion_manager.do_normal_expansion_data_range(  # type: ignore[union-attr]
                    at_least, for_node
                )
            else:
                at_least_concept: AtLeastConcept = at_least  # type: ignore[assignment]
                if not self._try_parent_reuse(at_least_concept, for_node):
                    if not self._expand_with_model_reuse(at_least_concept, for_node):
                        self.m_existential_expansion_manager.do_normal_expansion_concept(  # type: ignore[union-attr]
                            at_least_concept, for_node
                        )

    def _try_parent_reuse(
        self, at_least_concept: AtLeastConcept, node: Node
    ) -> bool:
        if at_least_concept.number == 1:
            parent = node.parent
            if parent is not None and self.m_extension_manager.contains_concept_assertion(  # type: ignore[union-attr]
                at_least_concept.to_concept, parent
            ):
                dependency_set = self.m_extension_manager.get_concept_assertion_dependency_set(  # type: ignore[union-attr]
                    at_least_concept, node
                )
                if not self.m_is_deterministic:
                    from hermit.existentials.individual_reuse_strategy import (
                        IndividualReuseBranchingPoint,
                    )

                    branching_point: BranchingPoint = IndividualReuseBranchingPoint(
                        self.m_tableau,  # type: ignore[arg-type]
                        at_least_concept,
                        node,
                        True,
                    )
                    self.m_tableau._push_branching_point(branching_point)  # type: ignore[union-attr]
                    dependency_set = (
                        self.m_tableau.m_dependency_set_factory.add_branching_point(  # type: ignore[union-attr]
                            dependency_set, branching_point.level
                        )
                    )
                self.m_extension_manager.add_role_assertion(  # type: ignore[union-attr]
                    at_least_concept.on_role,
                    node,
                    parent,
                    dependency_set,
                    True,
                )
                return True
        return False

    def _expand_with_model_reuse(
        self, at_least_concept: AtLeastConcept, node: Node
    ) -> bool:
        to_concept = at_least_concept.to_concept
        if not isinstance(to_concept, AtomicConcept):
            return False
        from hermit.model import Prefixes

        if Prefixes.is_internal_iri(to_concept.iri):
            return False
        if at_least_concept.number == 1 and (
            to_concept in self.m_do_reuse_concepts_always
            or to_concept not in self.m_dont_reuse_concepts_this_run
        ):
            if (
                self.m_tableau is not None
                and self.m_tableau.m_tableau_monitor is not None
            ):
                self.m_tableau.m_tableau_monitor.existential_expansion_started(
                    at_least_concept, node
                )
            dependency_set = self.m_extension_manager.get_concept_assertion_dependency_set(  # type: ignore[union-attr]
                at_least_concept, node
            )
            existential_node: Node
            reuse_info = self.m_reused_nodes.get(to_concept)
            if reuse_info is None:
                # No existential with the target concept has been expanded.
                if not self.m_is_deterministic:
                    from hermit.existentials.individual_reuse_strategy import (
                        IndividualReuseBranchingPoint,
                    )

                    branching_point: BranchingPoint = IndividualReuseBranchingPoint(
                        self.m_tableau,  # type: ignore[arg-type]
                        at_least_concept,
                        node,
                        False,
                    )
                    self.m_tableau._push_branching_point(branching_point)  # type: ignore[union-attr]
                    dependency_set = (
                        self.m_tableau.m_dependency_set_factory.add_branching_point(  # type: ignore[union-attr]
                            dependency_set, branching_point.level
                        )
                    )
                # Create a root node so that keys are not applicable
                existential_node = self.m_tableau._create_new_ni_node(  # type: ignore[union-attr]
                    dependency_set
                )
                reuse_info = NodeBranchingPointPair(
                    existential_node,
                    self.m_tableau.m_current_branching_point + 1,  # type: ignore[union-attr]
                )
                self.m_reused_nodes[to_concept] = reuse_info
                self.m_extension_manager.add_concept_assertion(  # type: ignore[union-attr]
                    to_concept, existential_node, dependency_set, True
                )
                self.m_auxiliary_buffer[0] = to_concept
                self.m_reuse_backtracking_table.add_tuple(
                    self.m_auxiliary_buffer
                )
            else:
                dependency_set = reuse_info.m_node.add_canonical_node_dependency_set(
                    dependency_set
                )
                existential_node = reuse_info.m_node.get_canonical_node()
                if not self.m_is_deterministic:
                    dependency_set = (
                        self.m_tableau.m_dependency_set_factory.add_branching_point(  # type: ignore[union-attr]
                            dependency_set, reuse_info.m_branching_point
                        )
                    )
            self.m_extension_manager.add_role_assertion(  # type: ignore[union-attr]
                at_least_concept.on_role,
                node,
                existential_node,
                dependency_set,
                True,
            )
            if (
                self.m_tableau is not None
                and self.m_tableau.m_tableau_monitor is not None
            ):
                self.m_tableau.m_tableau_monitor.existential_expansion_finished(
                    at_least_concept, node
                )
            return True
        return False


class IndividualReuseBranchingPoint:
    """Branching point for the individual reuse strategy."""

    def __init__(
        self,
        tableau: Tableau,
        existential: AtLeastConcept,
        node: Node,
        was_parent_reuse: bool,
    ) -> None:
        from hermit.tableau.branching_point import BranchingPoint

        self._bp = BranchingPoint(tableau)
        self.m_existential = existential
        self.m_node = node
        self.m_was_parent_reuse = was_parent_reuse

    @property
    def level(self) -> int:
        return self._bp.level

    def start_next_choice(
        self, tableau: Tableau, clash_dependency_set: DependencySet
    ) -> None:
        if not self.m_was_parent_reuse:
            to_concept = self.m_existential.to_concept
            assert isinstance(to_concept, AtomicConcept)
            # Access the strategy's dont-reuse set via the tableau
            strategy = tableau.m_existential_expansion_strategy
            if isinstance(strategy, IndividualReuseStrategy):
                strategy.m_dont_reuse_concepts_this_run.add(to_concept)
        dependency_set = tableau.m_dependency_set_factory.remove_branching_point(
            clash_dependency_set, self._bp.level
        )
        if tableau.m_tableau_monitor is not None:
            tableau.m_tableau_monitor.existential_expansion_started(
                self.m_existential, self.m_node
            )
        existential_node = tableau.create_new_tree_node(
            dependency_set, self.m_node
        )
        tableau.m_extension_manager.add_concept_assertion(
            self.m_existential.to_concept,
            existential_node,
            dependency_set,
            True,
        )
        tableau.m_extension_manager.add_role_assertion(
            self.m_existential.on_role,
            self.m_node,
            existential_node,
            dependency_set,
            True,
        )
        if tableau.m_tableau_monitor is not None:
            tableau.m_tableau_monitor.existential_expansion_finished(
                self.m_existential, self.m_node
            )
