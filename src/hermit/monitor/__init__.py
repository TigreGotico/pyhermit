# ruff: noqa: E501
"""_Tableau monitors for observability.

Faithful port of the ``org.semanticweb.HermiT.monitor`` package from the
Java HermiT OWL reasoner.

Classes
-------
TableauMonitor
    Interface (Protocol) defining all monitoring callbacks.
TableauMonitorAdapter
    Base class with no-op implementations of every callback.
TableauMonitorFork
    Forwards every callback to two downstream monitors.
TableauMonitorForwarder
    Conditionally forwards callbacks to a single downstream monitor.
CountingMonitor
    Collects timing, backtracking, node, and blocking statistics.
Timer
    Prints timing statistics to a stream during reasoning.
TimerWithPause
    Like :class:`Timer` but pauses for user input after each statistic.
MemoryConsumptionMonitor
    Tracks tableau memory consumption in addition to counting stats.
"""

from __future__ import annotations

__all__ = [
    "TableauMonitor",
    "TableauMonitorAdapter",
    "TableauMonitorFork",
    "TableauMonitorForwarder",
    "CountingMonitor",
    "Timer",
    "TimerWithPause",
    "MemoryConsumptionMonitor",
]

import sys
import time
from typing import Any, TextIO, TypeAlias

# Forward-reference types not yet ported -- all resolved to Any at runtime.
_Tableau: TypeAlias = Any
_Node: TypeAlias = Any
_BranchingPoint: TypeAlias = Any
_ReasoningTaskDescription: TypeAlias = Any
_DLClauseEvaluator: TypeAlias = Any
_DConjunction: TypeAlias = Any
_GroundDisjunction: TypeAlias = Any
_ExistentialConcept: TypeAlias = Any
_DataRange: TypeAlias = Any
_AnnotatedEquality: TypeAlias = Any


# ---------------------------------------------------------------------------
# TableauMonitor — interface (Protocol via structural subtyping)
# ---------------------------------------------------------------------------

class TableauMonitor:
    """Interface for tableau monitoring callbacks.

    Every method corresponds to an event in the tableau reasoning process.
    Implementations subclass :class:`TableauMonitorAdapter` for default
    no-op behaviour, or implement this interface directly.
    """

    def set_tableau(self, tableau: _Tableau) -> None: ...
    def is_satisfiable_started(self, reasoning_task_description: _ReasoningTaskDescription) -> None: ...
    def is_satisfiable_finished(self, reasoning_task_description: _ReasoningTaskDescription, result: bool) -> None: ...
    def tableau_cleared(self) -> None: ...
    def saturate_started(self) -> None: ...
    def saturate_finished(self, model_found: bool) -> None: ...
    def iteration_started(self) -> None: ...
    def iteration_finished(self) -> None: ...
    def dl_clause_matched_started(self, dl_clause_evaluator: _DLClauseEvaluator, dl_clause_index: int) -> None: ...
    def dl_clause_matched_finished(self, dl_clause_evaluator: _DLClauseEvaluator, dl_clause_index: int) -> None: ...
    def add_fact_started(self, tuple_: tuple[Any, ...], is_core: bool) -> None: ...
    def add_fact_finished(self, tuple_: tuple[Any, ...], is_core: bool, fact_added: bool) -> None: ...
    def merge_started(self, merge_from: _Node, merge_into: _Node) -> None: ...
    def node_pruned(self, node: _Node) -> None: ...
    def merge_fact_started(
        self, merge_from: _Node, merge_into: _Node,
        source_tuple: tuple[Any, ...], target_tuple: tuple[Any, ...],
    ) -> None: ...
    def merge_fact_finished(
        self, merge_from: _Node, merge_into: _Node,
        source_tuple: tuple[Any, ...], target_tuple: tuple[Any, ...],
    ) -> None: ...
    def merge_finished(self, merge_from: _Node, merge_into: _Node) -> None: ...
    def clash_detection_started(self, tuples: tuple[tuple[Any, ...], ...]) -> None: ...
    def clash_detection_finished(self, tuples: tuple[tuple[Any, ...], ...]) -> None: ...
    def clash_detected(self) -> None: ...
    def backtrack_to_started(self, new_current_branching_point: _BranchingPoint) -> None: ...
    def tuple_removed(self, tuple_: tuple[Any, ...]) -> None: ...
    def backtrack_to_finished(self, new_current_branching_point: _BranchingPoint) -> None: ...
    def ground_disjunction_derived(self, ground_disjunction: _GroundDisjunction) -> None: ...
    def process_ground_disjunction_started(self, ground_disjunction: _GroundDisjunction) -> None: ...
    def ground_disjunction_satisfied(self, ground_disjunction: _GroundDisjunction) -> None: ...
    def process_ground_disjunction_finished(self, ground_disjunction: _GroundDisjunction) -> None: ...
    def disjunct_processing_started(self, ground_disjunction: _GroundDisjunction, disjunct: int) -> None: ...
    def disjunct_processing_finished(self, ground_disjunction: _GroundDisjunction, disjunct: int) -> None: ...
    def push_branching_point_started(self, branching_point: _BranchingPoint) -> None: ...
    def push_branching_point_finished(self, branching_point: _BranchingPoint) -> None: ...
    def start_next_branching_point_started(self, branching_point: _BranchingPoint) -> None: ...
    def start_next_branching_point_finished(self, branching_point: _BranchingPoint) -> None: ...
    def existential_expansion_started(
        self, existential_concept: _ExistentialConcept, for_node: _Node,
    ) -> None: ...
    def existential_expansion_finished(
        self, existential_concept: _ExistentialConcept, for_node: _Node,
    ) -> None: ...
    def existential_satisfied(
        self, existential_concept: _ExistentialConcept, for_node: _Node,
    ) -> None: ...
    def nominal_introduction_started(
        self, root_node: _Node, tree_node: _Node,
        annotated_equality: _AnnotatedEquality, argument1: _Node, argument2: _Node,
    ) -> None: ...
    def nominal_introduction_finished(
        self, root_node: _Node, tree_node: _Node,
        annotated_equality: _AnnotatedEquality, argument1: _Node, argument2: _Node,
    ) -> None: ...
    def description_graph_checking_started(
        self, graph_index1: int, tuple_index1: int, position1: int,
        graph_index2: int, tuple_index2: int, position2: int,
    ) -> None: ...
    def description_graph_checking_finished(
        self, graph_index1: int, tuple_index1: int, position1: int,
        graph_index2: int, tuple_index2: int, position2: int,
    ) -> None: ...
    def node_created(self, node: _Node) -> None: ...
    def node_destroyed(self, node: _Node) -> None: ...
    def unknown_datatype_restriction_detection_started(
        self, data_range1: _DataRange, node1: _Node,
        data_range2: _DataRange, node2: _Node,
    ) -> None: ...
    def unknown_datatype_restriction_detection_finished(
        self, data_range1: _DataRange, node1: _Node,
        data_range2: _DataRange, node2: _Node,
    ) -> None: ...
    def datatype_checking_started(self) -> None: ...
    def datatype_checking_finished(self, result: bool) -> None: ...
    def datatype_conjunction_checking_started(
        self, conjunction: _DConjunction,
    ) -> None: ...
    def datatype_conjunction_checking_finished(
        self, conjunction: _DConjunction, result: bool,
    ) -> None: ...
    def blocking_validation_started(self) -> None: ...
    def blocking_validation_finished(self, no_invalidly_blocked: int) -> None: ...
    def possible_instance_is_instance(self) -> None: ...
    def possible_instance_is_not_instance(self) -> None: ...


# ---------------------------------------------------------------------------
# TableauMonitorAdapter — no-op base class
# ---------------------------------------------------------------------------

class TableauMonitorAdapter(TableauMonitor):
    """Adapter with empty implementations of every :class:`TableauMonitor` method.

    Subclass and override only the methods you care about.
    """

    def __init__(self) -> None:
        self._tableau: _Tableau | None = None

    def set_tableau(self, tableau: _Tableau) -> None:
        self._tableau = tableau

    def is_satisfiable_started(self, reasoning_task_description: _ReasoningTaskDescription) -> None:
        pass

    def is_satisfiable_finished(self, reasoning_task_description: _ReasoningTaskDescription, result: bool) -> None:
        pass

    def tableau_cleared(self) -> None:
        pass

    def saturate_started(self) -> None:
        pass

    def saturate_finished(self, model_found: bool) -> None:
        pass

    def iteration_started(self) -> None:
        pass

    def iteration_finished(self) -> None:
        pass

    def dl_clause_matched_started(self, dl_clause_evaluator: _DLClauseEvaluator, dl_clause_index: int) -> None:
        pass

    def dl_clause_matched_finished(self, dl_clause_evaluator: _DLClauseEvaluator, dl_clause_index: int) -> None:
        pass

    def add_fact_started(self, tuple_: tuple[Any, ...], is_core: bool) -> None:
        pass

    def add_fact_finished(self, tuple_: tuple[Any, ...], is_core: bool, fact_added: bool) -> None:
        pass

    def merge_started(self, merge_from: _Node, merge_into: _Node) -> None:
        pass

    def node_pruned(self, node: _Node) -> None:
        pass

    def merge_fact_started(self, merge_from: _Node, merge_into: _Node, source_tuple: tuple[Any, ...], target_tuple: tuple[Any, ...]) -> None:
        pass

    def merge_fact_finished(self, merge_from: _Node, merge_into: _Node, source_tuple: tuple[Any, ...], target_tuple: tuple[Any, ...]) -> None:
        pass

    def merge_finished(self, merge_from: _Node, merge_into: _Node) -> None:
        pass

    def clash_detection_started(self, tuples: tuple[tuple[Any, ...], ...]) -> None:
        pass

    def clash_detection_finished(self, tuples: tuple[tuple[Any, ...], ...]) -> None:
        pass

    def clash_detected(self) -> None:
        pass

    def backtrack_to_started(self, new_current_branching_point: _BranchingPoint) -> None:
        pass

    def tuple_removed(self, tuple_: tuple[Any, ...]) -> None:
        pass

    def backtrack_to_finished(self, new_current_branching_point: _BranchingPoint) -> None:
        pass

    def ground_disjunction_derived(self, ground_disjunction: _GroundDisjunction) -> None:
        pass

    def process_ground_disjunction_started(self, ground_disjunction: _GroundDisjunction) -> None:
        pass

    def ground_disjunction_satisfied(self, ground_disjunction: _GroundDisjunction) -> None:
        pass

    def process_ground_disjunction_finished(self, ground_disjunction: _GroundDisjunction) -> None:
        pass

    def disjunct_processing_started(self, ground_disjunction: _GroundDisjunction, disjunct: int) -> None:
        pass

    def disjunct_processing_finished(self, ground_disjunction: _GroundDisjunction, disjunct: int) -> None:
        pass

    def push_branching_point_started(self, branching_point: _BranchingPoint) -> None:
        pass

    def push_branching_point_finished(self, branching_point: _BranchingPoint) -> None:
        pass

    def start_next_branching_point_started(self, branching_point: _BranchingPoint) -> None:
        pass

    def start_next_branching_point_finished(self, branching_point: _BranchingPoint) -> None:
        pass

    def existential_expansion_started(self, existential_concept: _ExistentialConcept, for_node: _Node) -> None:
        pass

    def existential_expansion_finished(self, existential_concept: _ExistentialConcept, for_node: _Node) -> None:
        pass

    def existential_satisfied(self, existential_concept: _ExistentialConcept, for_node: _Node) -> None:
        pass

    def nominal_introduction_started(self, root_node: _Node, tree_node: _Node, annotated_equality: _AnnotatedEquality, argument1: _Node, argument2: _Node) -> None:
        pass

    def nominal_introduction_finished(self, root_node: _Node, tree_node: _Node, annotated_equality: _AnnotatedEquality, argument1: _Node, argument2: _Node) -> None:
        pass

    def description_graph_checking_started(self, graph_index1: int, tuple_index1: int, position1: int, graph_index2: int, tuple_index2: int, position2: int) -> None:
        pass

    def description_graph_checking_finished(self, graph_index1: int, tuple_index1: int, position1: int, graph_index2: int, tuple_index2: int, position2: int) -> None:
        pass

    def node_created(self, node: _Node) -> None:
        pass

    def node_destroyed(self, node: _Node) -> None:
        pass

    def unknown_datatype_restriction_detection_started(self, data_range1: _DataRange, node1: _Node, data_range2: _DataRange, node2: _Node) -> None:
        pass

    def unknown_datatype_restriction_detection_finished(self, data_range1: _DataRange, node1: _Node, data_range2: _DataRange, node2: _Node) -> None:
        pass

    def datatype_checking_started(self) -> None:
        pass

    def datatype_checking_finished(self, result: bool) -> None:
        pass

    def datatype_conjunction_checking_started(self, conjunction: _DConjunction) -> None:
        pass

    def datatype_conjunction_checking_finished(self, conjunction: _DConjunction, result: bool) -> None:
        pass

    def blocking_validation_started(self) -> None:
        pass

    def blocking_validation_finished(self, no_invalidly_blocked: int) -> None:
        pass

    def possible_instance_is_instance(self) -> None:
        pass

    def possible_instance_is_not_instance(self) -> None:
        pass


# ---------------------------------------------------------------------------
# TableauMonitorFork — split to two monitors
# ---------------------------------------------------------------------------

class TableauMonitorFork(TableauMonitor):
    """Forwards every callback to two downstream monitors."""

    def __init__(self, first: TableauMonitor, second: TableauMonitor) -> None:
        self._first = first
        self._second = second

    def set_tableau(self, tableau: _Tableau) -> None:
        self._first.set_tableau(tableau)
        self._second.set_tableau(tableau)

    def is_satisfiable_started(self, reasoning_task_description: _ReasoningTaskDescription) -> None:
        self._first.is_satisfiable_started(reasoning_task_description)
        self._second.is_satisfiable_started(reasoning_task_description)

    def is_satisfiable_finished(self, reasoning_task_description: _ReasoningTaskDescription, result: bool) -> None:
        self._first.is_satisfiable_finished(reasoning_task_description, result)
        self._second.is_satisfiable_finished(reasoning_task_description, result)

    def tableau_cleared(self) -> None:
        self._first.tableau_cleared()
        self._second.tableau_cleared()

    def saturate_started(self) -> None:
        self._first.saturate_started()
        self._second.saturate_started()

    def saturate_finished(self, model_found: bool) -> None:
        self._first.saturate_finished(model_found)
        self._second.saturate_finished(model_found)

    def iteration_started(self) -> None:
        self._first.iteration_started()
        self._second.iteration_started()

    def iteration_finished(self) -> None:
        self._first.iteration_finished()
        self._second.iteration_finished()

    def dl_clause_matched_started(self, dl_clause_evaluator: _DLClauseEvaluator, dl_clause_index: int) -> None:
        self._first.dl_clause_matched_started(dl_clause_evaluator, dl_clause_index)
        self._second.dl_clause_matched_started(dl_clause_evaluator, dl_clause_index)

    def dl_clause_matched_finished(self, dl_clause_evaluator: _DLClauseEvaluator, dl_clause_index: int) -> None:
        self._first.dl_clause_matched_finished(dl_clause_evaluator, dl_clause_index)
        self._second.dl_clause_matched_finished(dl_clause_evaluator, dl_clause_index)

    def add_fact_started(self, tuple_: tuple[Any, ...], is_core: bool) -> None:
        self._first.add_fact_started(tuple_, is_core)
        self._second.add_fact_started(tuple_, is_core)

    def add_fact_finished(self, tuple_: tuple[Any, ...], is_core: bool, fact_added: bool) -> None:
        self._first.add_fact_finished(tuple_, is_core, fact_added)
        self._second.add_fact_finished(tuple_, is_core, fact_added)

    def merge_started(self, merge_from: _Node, merge_into: _Node) -> None:
        self._first.merge_started(merge_from, merge_into)
        self._second.merge_started(merge_from, merge_into)

    def node_pruned(self, node: _Node) -> None:
        self._first.node_pruned(node)
        self._second.node_pruned(node)

    def merge_fact_started(self, merge_from: _Node, merge_into: _Node, source_tuple: tuple[Any, ...], target_tuple: tuple[Any, ...]) -> None:
        self._first.merge_fact_started(merge_from, merge_into, source_tuple, target_tuple)
        self._second.merge_fact_started(merge_from, merge_into, source_tuple, target_tuple)

    def merge_fact_finished(self, merge_from: _Node, merge_into: _Node, source_tuple: tuple[Any, ...], target_tuple: tuple[Any, ...]) -> None:
        self._first.merge_fact_finished(merge_from, merge_into, source_tuple, target_tuple)
        self._second.merge_fact_finished(merge_from, merge_into, source_tuple, target_tuple)

    def merge_finished(self, merge_from: _Node, merge_into: _Node) -> None:
        self._first.merge_finished(merge_from, merge_into)
        self._second.merge_finished(merge_from, merge_into)

    def clash_detection_started(self, tuples: tuple[tuple[Any, ...], ...]) -> None:
        self._first.clash_detection_started(tuples)
        self._second.clash_detection_started(tuples)

    def clash_detection_finished(self, tuples: tuple[tuple[Any, ...], ...]) -> None:
        self._first.clash_detection_finished(tuples)
        self._second.clash_detection_finished(tuples)

    def clash_detected(self) -> None:
        self._first.clash_detected()
        self._second.clash_detected()

    def backtrack_to_started(self, new_current_branching_point: _BranchingPoint) -> None:
        self._first.backtrack_to_started(new_current_branching_point)
        self._second.backtrack_to_started(new_current_branching_point)

    def tuple_removed(self, tuple_: tuple[Any, ...]) -> None:
        self._first.tuple_removed(tuple_)
        self._second.tuple_removed(tuple_)

    def backtrack_to_finished(self, new_current_branching_point: _BranchingPoint) -> None:
        self._first.backtrack_to_finished(new_current_branching_point)
        self._second.backtrack_to_finished(new_current_branching_point)

    def ground_disjunction_derived(self, ground_disjunction: _GroundDisjunction) -> None:
        self._first.ground_disjunction_derived(ground_disjunction)
        self._second.ground_disjunction_derived(ground_disjunction)

    def process_ground_disjunction_started(self, ground_disjunction: _GroundDisjunction) -> None:
        self._first.process_ground_disjunction_started(ground_disjunction)
        self._second.process_ground_disjunction_started(ground_disjunction)

    def ground_disjunction_satisfied(self, ground_disjunction: _GroundDisjunction) -> None:
        self._first.ground_disjunction_satisfied(ground_disjunction)
        self._second.ground_disjunction_satisfied(ground_disjunction)

    def process_ground_disjunction_finished(self, ground_disjunction: _GroundDisjunction) -> None:
        self._first.process_ground_disjunction_finished(ground_disjunction)
        self._second.process_ground_disjunction_finished(ground_disjunction)

    def disjunct_processing_started(self, ground_disjunction: _GroundDisjunction, disjunct: int) -> None:
        self._first.disjunct_processing_started(ground_disjunction, disjunct)
        self._second.disjunct_processing_started(ground_disjunction, disjunct)

    def disjunct_processing_finished(self, ground_disjunction: _GroundDisjunction, disjunct: int) -> None:
        self._first.disjunct_processing_finished(ground_disjunction, disjunct)
        self._second.disjunct_processing_finished(ground_disjunction, disjunct)

    def push_branching_point_started(self, branching_point: _BranchingPoint) -> None:
        self._first.push_branching_point_started(branching_point)
        self._second.push_branching_point_started(branching_point)

    def push_branching_point_finished(self, branching_point: _BranchingPoint) -> None:
        self._first.push_branching_point_finished(branching_point)
        self._second.push_branching_point_finished(branching_point)

    def start_next_branching_point_started(self, branching_point: _BranchingPoint) -> None:
        self._first.start_next_branching_point_started(branching_point)
        self._second.start_next_branching_point_started(branching_point)

    def start_next_branching_point_finished(self, branching_point: _BranchingPoint) -> None:
        self._first.start_next_branching_point_finished(branching_point)
        self._second.start_next_branching_point_finished(branching_point)

    def existential_expansion_started(self, existential_concept: _ExistentialConcept, for_node: _Node) -> None:
        self._first.existential_expansion_started(existential_concept, for_node)
        self._second.existential_expansion_started(existential_concept, for_node)

    def existential_expansion_finished(self, existential_concept: _ExistentialConcept, for_node: _Node) -> None:
        self._first.existential_expansion_finished(existential_concept, for_node)
        self._second.existential_expansion_finished(existential_concept, for_node)

    def existential_satisfied(self, existential_concept: _ExistentialConcept, for_node: _Node) -> None:
        self._first.existential_satisfied(existential_concept, for_node)
        self._second.existential_satisfied(existential_concept, for_node)

    def nominal_introduction_started(self, root_node: _Node, tree_node: _Node, annotated_equality: _AnnotatedEquality, argument1: _Node, argument2: _Node) -> None:
        self._first.nominal_introduction_started(root_node, tree_node, annotated_equality, argument1, argument2)
        self._second.nominal_introduction_started(root_node, tree_node, annotated_equality, argument1, argument2)

    def nominal_introduction_finished(self, root_node: _Node, tree_node: _Node, annotated_equality: _AnnotatedEquality, argument1: _Node, argument2: _Node) -> None:
        self._first.nominal_introduction_finished(root_node, tree_node, annotated_equality, argument1, argument2)
        self._second.nominal_introduction_finished(root_node, tree_node, annotated_equality, argument1, argument2)

    def description_graph_checking_started(self, graph_index1: int, tuple_index1: int, position1: int, graph_index2: int, tuple_index2: int, position2: int) -> None:
        self._first.description_graph_checking_started(graph_index1, tuple_index1, position1, graph_index2, tuple_index2, position2)
        self._second.description_graph_checking_started(graph_index1, tuple_index1, position1, graph_index2, tuple_index2, position2)

    def description_graph_checking_finished(self, graph_index1: int, tuple_index1: int, position1: int, graph_index2: int, tuple_index2: int, position2: int) -> None:
        self._first.description_graph_checking_finished(graph_index1, tuple_index1, position1, graph_index2, tuple_index2, position2)
        self._second.description_graph_checking_finished(graph_index1, tuple_index1, position1, graph_index2, tuple_index2, position2)

    def node_created(self, node: _Node) -> None:
        self._first.node_created(node)
        self._second.node_created(node)

    def node_destroyed(self, node: _Node) -> None:
        self._first.node_destroyed(node)
        self._second.node_destroyed(node)

    def unknown_datatype_restriction_detection_started(self, data_range1: _DataRange, node1: _Node, data_range2: _DataRange, node2: _Node) -> None:
        self._first.unknown_datatype_restriction_detection_started(data_range1, node1, data_range2, node2)
        self._second.unknown_datatype_restriction_detection_started(data_range1, node1, data_range2, node2)

    def unknown_datatype_restriction_detection_finished(self, data_range1: _DataRange, node1: _Node, data_range2: _DataRange, node2: _Node) -> None:
        self._first.unknown_datatype_restriction_detection_finished(data_range1, node1, data_range2, node2)
        self._second.unknown_datatype_restriction_detection_finished(data_range1, node1, data_range2, node2)

    def datatype_checking_started(self) -> None:
        self._first.datatype_checking_started()
        self._second.datatype_checking_started()

    def datatype_checking_finished(self, result: bool) -> None:
        self._first.datatype_checking_finished(result)
        self._second.datatype_checking_finished(result)

    def datatype_conjunction_checking_started(self, conjunction: _DConjunction) -> None:
        self._first.datatype_conjunction_checking_started(conjunction)
        self._second.datatype_conjunction_checking_started(conjunction)

    def datatype_conjunction_checking_finished(self, conjunction: _DConjunction, result: bool) -> None:
        self._first.datatype_conjunction_checking_finished(conjunction, result)
        self._second.datatype_conjunction_checking_finished(conjunction, result)

    def blocking_validation_started(self) -> None:
        self._first.blocking_validation_started()
        self._second.blocking_validation_started()

    def blocking_validation_finished(self, no_invalidly_blocked: int) -> None:
        self._first.blocking_validation_finished(no_invalidly_blocked)
        self._second.blocking_validation_finished(no_invalidly_blocked)

    def possible_instance_is_instance(self) -> None:
        self._first.possible_instance_is_instance()
        self._second.possible_instance_is_instance()

    def possible_instance_is_not_instance(self) -> None:
        self._first.possible_instance_is_not_instance()
        self._second.possible_instance_is_not_instance()


# ---------------------------------------------------------------------------
# TableauMonitorForwarder — conditional forwarding
# ---------------------------------------------------------------------------

class TableauMonitorForwarder(TableauMonitor):
    """Conditionally forwards every callback to a downstream monitor.

    When :attr:`forwarding_on` is ``False`` all events are silently dropped
    (except :meth:`set_tableau`, which always reaches the target).
    """

    def __init__(self, forwarding_target_monitor: TableauMonitor) -> None:
        self._forwarding_target_monitor = forwarding_target_monitor
        self._forwarding_on: bool = False

    # -- forwarding flag -------------------------------------------------

    @property
    def forwarding_on(self) -> bool:
        """Whether events are forwarded to the target monitor."""
        return self._forwarding_on

    @forwarding_on.setter
    def forwarding_on(self, value: bool) -> None:
        self._forwarding_on = value

    def is_forwarding_on(self) -> bool:
        """Legacy getter — mirrors the Java ``isForwardingOn()``."""
        return self._forwarding_on

    def set_forwarding_on(self, forwarding_on: bool) -> None:
        """Legacy setter — mirrors the Java ``setForwardingOn()``."""
        self._forwarding_on = forwarding_on

    # -- callbacks -------------------------------------------------------

    def set_tableau(self, tableau: _Tableau) -> None:
        self._forwarding_target_monitor.set_tableau(tableau)

    def is_satisfiable_started(self, reasoning_task_description: _ReasoningTaskDescription) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.is_satisfiable_started(reasoning_task_description)

    def is_satisfiable_finished(self, reasoning_task_description: _ReasoningTaskDescription, result: bool) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.is_satisfiable_finished(reasoning_task_description, result)

    def tableau_cleared(self) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.tableau_cleared()

    def saturate_started(self) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.saturate_started()

    def saturate_finished(self, model_found: bool) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.saturate_finished(model_found)

    def iteration_started(self) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.iteration_started()

    def iteration_finished(self) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.iteration_finished()

    def dl_clause_matched_started(self, dl_clause_evaluator: _DLClauseEvaluator, dl_clause_index: int) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.dl_clause_matched_started(dl_clause_evaluator, dl_clause_index)

    def dl_clause_matched_finished(self, dl_clause_evaluator: _DLClauseEvaluator, dl_clause_index: int) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.dl_clause_matched_finished(dl_clause_evaluator, dl_clause_index)

    def add_fact_started(self, tuple_: tuple[Any, ...], is_core: bool) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.add_fact_started(tuple_, is_core)

    def add_fact_finished(self, tuple_: tuple[Any, ...], is_core: bool, fact_added: bool) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.add_fact_finished(tuple_, is_core, fact_added)

    def merge_started(self, merge_from: _Node, merge_into: _Node) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.merge_started(merge_from, merge_into)

    def node_pruned(self, node: _Node) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.node_pruned(node)

    def merge_fact_started(self, merge_from: _Node, merge_into: _Node, source_tuple: tuple[Any, ...], target_tuple: tuple[Any, ...]) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.merge_fact_started(merge_from, merge_into, source_tuple, target_tuple)

    def merge_fact_finished(self, merge_from: _Node, merge_into: _Node, source_tuple: tuple[Any, ...], target_tuple: tuple[Any, ...]) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.merge_fact_finished(merge_from, merge_into, source_tuple, target_tuple)

    def merge_finished(self, merge_from: _Node, merge_into: _Node) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.merge_finished(merge_from, merge_into)

    def clash_detection_started(self, tuples: tuple[tuple[Any, ...], ...]) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.clash_detection_started(tuples)

    def clash_detection_finished(self, tuples: tuple[tuple[Any, ...], ...]) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.clash_detection_finished(tuples)

    def clash_detected(self) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.clash_detected()

    def backtrack_to_started(self, new_current_branching_point: _BranchingPoint) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.backtrack_to_started(new_current_branching_point)

    def tuple_removed(self, tuple_: tuple[Any, ...]) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.tuple_removed(tuple_)

    def backtrack_to_finished(self, new_current_branching_point: _BranchingPoint) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.backtrack_to_finished(new_current_branching_point)

    def ground_disjunction_derived(self, ground_disjunction: _GroundDisjunction) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.ground_disjunction_derived(ground_disjunction)

    def process_ground_disjunction_started(self, ground_disjunction: _GroundDisjunction) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.process_ground_disjunction_started(ground_disjunction)

    def ground_disjunction_satisfied(self, ground_disjunction: _GroundDisjunction) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.ground_disjunction_satisfied(ground_disjunction)

    def process_ground_disjunction_finished(self, ground_disjunction: _GroundDisjunction) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.process_ground_disjunction_finished(ground_disjunction)

    def disjunct_processing_started(self, ground_disjunction: _GroundDisjunction, disjunct: int) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.disjunct_processing_started(ground_disjunction, disjunct)

    def disjunct_processing_finished(self, ground_disjunction: _GroundDisjunction, disjunct: int) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.disjunct_processing_finished(ground_disjunction, disjunct)

    def push_branching_point_started(self, branching_point: _BranchingPoint) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.push_branching_point_started(branching_point)

    def push_branching_point_finished(self, branching_point: _BranchingPoint) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.push_branching_point_finished(branching_point)

    def start_next_branching_point_started(self, branching_point: _BranchingPoint) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.start_next_branching_point_started(branching_point)

    def start_next_branching_point_finished(self, branching_point: _BranchingPoint) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.start_next_branching_point_finished(branching_point)

    def existential_expansion_started(self, existential_concept: _ExistentialConcept, for_node: _Node) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.existential_expansion_started(existential_concept, for_node)

    def existential_expansion_finished(self, existential_concept: _ExistentialConcept, for_node: _Node) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.existential_expansion_finished(existential_concept, for_node)

    def existential_satisfied(self, existential_concept: _ExistentialConcept, for_node: _Node) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.existential_satisfied(existential_concept, for_node)

    def nominal_introduction_started(self, root_node: _Node, tree_node: _Node, annotated_equality: _AnnotatedEquality, argument1: _Node, argument2: _Node) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.nominal_introduction_started(root_node, tree_node, annotated_equality, argument1, argument2)

    def nominal_introduction_finished(self, root_node: _Node, tree_node: _Node, annotated_equality: _AnnotatedEquality, argument1: _Node, argument2: _Node) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.nominal_introduction_finished(root_node, tree_node, annotated_equality, argument1, argument2)

    def description_graph_checking_started(self, graph_index1: int, tuple_index1: int, position1: int, graph_index2: int, tuple_index2: int, position2: int) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.description_graph_checking_started(graph_index1, tuple_index1, position1, graph_index2, tuple_index2, position2)

    def description_graph_checking_finished(self, graph_index1: int, tuple_index1: int, position1: int, graph_index2: int, tuple_index2: int, position2: int) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.description_graph_checking_finished(graph_index1, tuple_index1, position1, graph_index2, tuple_index2, position2)

    def node_created(self, node: _Node) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.node_created(node)

    def node_destroyed(self, node: _Node) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.node_destroyed(node)

    def unknown_datatype_restriction_detection_started(self, data_range1: _DataRange, node1: _Node, data_range2: _DataRange, node2: _Node) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.unknown_datatype_restriction_detection_started(data_range1, node1, data_range2, node2)

    def unknown_datatype_restriction_detection_finished(self, data_range1: _DataRange, node1: _Node, data_range2: _DataRange, node2: _Node) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.unknown_datatype_restriction_detection_finished(data_range1, node1, data_range2, node2)

    def datatype_checking_started(self) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.datatype_checking_started()

    def datatype_checking_finished(self, result: bool) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.datatype_checking_finished(result)

    def datatype_conjunction_checking_started(self, conjunction: _DConjunction) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.datatype_conjunction_checking_started(conjunction)

    def datatype_conjunction_checking_finished(self, conjunction: _DConjunction, result: bool) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.datatype_conjunction_checking_finished(conjunction, result)

    def blocking_validation_started(self) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.blocking_validation_started()

    def blocking_validation_finished(self, no_invalidly_blocked: int) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.blocking_validation_finished(no_invalidly_blocked)

    def possible_instance_is_instance(self) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.possible_instance_is_instance()

    def possible_instance_is_not_instance(self) -> None:
        if self._forwarding_on:
            self._forwarding_target_monitor.possible_instance_is_not_instance()


# ---------------------------------------------------------------------------
# CountingMonitor — statistics collector
# ---------------------------------------------------------------------------

class TestRecord:
    """Record of a single reasoning test run.

    Mirrors the Java ``CountingMonitor.TestRecord`` inner class.
    """

    __slots__ = ("_test_time", "_test_description", "_test_result")

    def __init__(self, test_time: int, test_description: str, result: bool) -> None:
        self._test_time = test_time
        self._test_description = test_description
        self._test_result = result

    @property
    def test_time(self) -> int:
        """Duration of the test in milliseconds."""
        return self._test_time

    @property
    def test_description(self) -> str:
        """Human-readable description of the test."""
        return self._test_description

    @property
    def test_result(self) -> bool:
        """Whether the test was satisfiable."""
        return self._test_result

    def __lt__(self, other: TestRecord) -> bool:
        if not isinstance(other, TestRecord):
            return NotImplemented
        if self._test_time != other._test_time:
            return self._test_time > other._test_time  # descending
        return self._test_description.lower() < other._test_description.lower()

    def __le__(self, other: TestRecord) -> bool:
        return self == other or self < other

    def __gt__(self, other: TestRecord) -> bool:
        return not self <= other

    def __ge__(self, other: TestRecord) -> bool:
        return not self < other

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TestRecord):
            return NotImplemented
        return (
            self._test_time == other._test_time
            and self._test_description == other._test_description
        )

    def __ne__(self, other: object) -> bool:
        return not self == other

    def __repr__(self) -> str:
        suffix = ""
        if self._test_time > 1000:
            suffix = f" ({CountingMonitor.millis_to_hours_minutes_seconds_string(self._test_time)})"
        return (
            f"{self._test_time} ms{suffix} for {self._test_description} "
            f"(result: {self._test_result})"
        )


class CountingMonitor(TableauMonitorAdapter):
    """Collects statistics about tableau reasoning.

    Tracks time, backtracking count, node counts, blocking validation
    metrics, and per-test records.  Faithful port of the Java
    ``CountingMonitor``.
    """

    def __init__(self) -> None:
        super().__init__()
        self._problem_start_time: int = 0
        self._validation_start_time: int = 0
        self._test_no: int = 0
        # Current test
        self._time: int = 0
        self._number_of_backtrackings: int = 0
        self._number_of_nodes: int = 0
        self._number_of_blocked_nodes: int = 0
        self._reasoning_task_description: _ReasoningTaskDescription | None = None
        self._test_result: bool = False
        # Validated blocking
        self._initial_model_size: int = 0
        self._initially_blocked: int = 0
        self._initially_invalid: int = 0
        self._no_validations: int = 0
        self._validation_time: int = 0
        # Overall numbers
        self._test_records: dict[str, list[TestRecord]] = {}
        self._overall_time: int = 0
        self._overall_number_of_backtrackings: int = 0
        self._overall_number_of_nodes: int = 0
        self._overall_number_of_blocked_nodes: int = 0
        self._overall_number_of_tests: int = 0
        self._overall_number_of_clashes: int = 0
        self._possible_instances_tested: int = 0
        self._possible_instances_instances: int = 0
        # Overall blocking validation
        self._overall_initial_model_size: int = 0
        self._overall_initially_blocked: int = 0
        self._overall_initially_invalid: int = 0
        self._overall_no_validations: int = 0
        self._overall_validation_time: int = 0

    # -- reset -----------------------------------------------------------

    def reset(self) -> None:
        """Reset all current-test and overall statistics to zero."""
        self._problem_start_time = 0
        self._validation_start_time = 0
        self._time = 0
        self._number_of_backtrackings = 0
        self._number_of_nodes = 0
        self._number_of_blocked_nodes = 0
        self._reasoning_task_description = None
        self._test_result = False
        self._initial_model_size = 0
        self._initially_blocked = 0
        self._initially_invalid = 0
        self._no_validations = 0
        self._validation_time = 0
        self._test_records.clear()
        self._overall_time = 0
        self._overall_number_of_backtrackings = 0
        self._overall_number_of_nodes = 0
        self._overall_number_of_blocked_nodes = 0
        self._overall_number_of_tests = 0
        self._overall_number_of_clashes = 0
        self._possible_instances_tested = 0
        self._possible_instances_instances = 0
        self._overall_initial_model_size = 0
        self._overall_initially_blocked = 0
        self._overall_initially_invalid = 0
        self._overall_no_validations = 0
        self._overall_validation_time = 0

    # -- callbacks -------------------------------------------------------

    def is_satisfiable_started(self, reasoning_task_description: _ReasoningTaskDescription) -> None:
        super().is_satisfiable_started(reasoning_task_description)
        self._test_no += 1
        self._reasoning_task_description = reasoning_task_description
        self._overall_number_of_tests += 1
        self._problem_start_time = self._now_ms()
        self._number_of_backtrackings = 0
        self._number_of_nodes = 0
        self._number_of_blocked_nodes = 0
        self._initial_model_size = 0
        self._initially_blocked = 0
        self._initially_invalid = 0
        self._no_validations = 0
        self._validation_time = 0

    def is_satisfiable_finished(self, reasoning_task_description: _ReasoningTaskDescription, result: bool) -> None:
        super().is_satisfiable_finished(reasoning_task_description, result)
        # Note: the Java version calls flipSatisfiabilityResult() which is on
        # _ReasoningTaskDescription; we replicate the logic inline here.
        # When the tableau module is ported this will use the real method.
        result = self._maybe_flip_result(reasoning_task_description, result)
        self._test_result = result
        self._time = self._now_ms() - self._problem_start_time
        message_pattern = self._get_message_pattern(reasoning_task_description)
        records = self._test_records.get(message_pattern)
        if records is None:
            records = []
            self._test_records[message_pattern] = records
        test_desc = self._get_task_description(reasoning_task_description)
        records.append(TestRecord(self._time, test_desc, self._test_result))
        self._overall_time += self._time
        self._overall_number_of_backtrackings += self._number_of_backtrackings
        self._number_of_nodes = self._get_number_of_nodes_in_tableau()
        self._number_of_blocked_nodes = self._count_blocked_nodes()
        self._overall_number_of_nodes += self._number_of_nodes
        self._overall_number_of_blocked_nodes += self._number_of_blocked_nodes
        self._overall_initial_model_size += self._initial_model_size
        self._overall_initially_blocked += self._initially_blocked
        self._overall_initially_invalid += self._initially_invalid
        self._overall_no_validations += self._no_validations
        self._overall_validation_time += self._validation_time

    def backtrack_to_finished(self, new_current_branching_point: _BranchingPoint) -> None:
        self._number_of_backtrackings += 1

    def possible_instance_is_instance(self) -> None:
        self._possible_instances_tested += 1
        self._possible_instances_instances += 1

    def possible_instance_is_not_instance(self) -> None:
        self._possible_instances_tested += 1

    def blocking_validation_started(self) -> None:
        self._no_validations += 1
        if self._no_validations == 1 and self._tableau is not None:
            node = self._tableau.get_first_tableau_node()
            while node is not None:
                if node.is_active():
                    self._initial_model_size += 1
                    if node.is_blocked() and node.has_unprocessed_existentials():
                        self._initially_blocked += 1
                node = node.get_next_tableau_node()
        self._validation_start_time = self._now_ms()

    def blocking_validation_finished(self, no_invalidly_blocked: int) -> None:
        self._validation_time += self._now_ms() - self._validation_start_time
        if self._no_validations == 1:
            self._initially_invalid = no_invalidly_blocked

    def clash_detected(self) -> None:
        self._overall_number_of_clashes += 1

    # -- helpers to access tableau (stub-safe) ----------------------------

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def _maybe_flip_result(reasoning_task_description: _ReasoningTaskDescription, result: bool) -> bool:
        # Deferred call — when _ReasoningTaskDescription is ported this will
        # use the real method.  For now we conservatively assume no flip.
        try:
            if hasattr(reasoning_task_description, "flip_satisfiability_result"):
                if reasoning_task_description.flip_satisfiability_result():
                    return not result
        except Exception:
            pass
        return result

    @staticmethod
    def _get_message_pattern(reasoning_task_description: _ReasoningTaskDescription) -> str:
        try:
            return str(reasoning_task_description.message_pattern)
        except AttributeError:
            return str(reasoning_task_description)

    @staticmethod
    def _get_task_description(reasoning_task_description: _ReasoningTaskDescription) -> str:
        try:
            from hermit.model import Prefixes
            return str(reasoning_task_description.get_task_description(Prefixes.STANDARD))
        except Exception:
            return str(reasoning_task_description)

    def _get_number_of_nodes_in_tableau(self) -> int:
        if self._tableau is None:
            return 0
        try:
            return int(self._tableau.get_number_of_nodes_in_tableau() - self._tableau.get_number_of_merged_or_pruned_nodes())
        except AttributeError:
            return 0

    def _count_blocked_nodes(self) -> int:
        if self._tableau is None:
            return 0
        count = 0
        try:
            node = self._tableau.get_first_tableau_node()
            while node is not None:
                if node.is_active() and node.is_blocked() and node.has_unprocessed_existentials():
                    count += 1
                node = node.get_next_tableau_node()
        except AttributeError:
            pass
        return count

    # -- getters: test records --------------------------------------------

    def get_used_message_patterns(self) -> set[str]:
        """Return the set of message patterns seen so far."""
        return set(self._test_records.keys())

    def get_time_sorted_test_records(self, limit: int, message_pattern: str | None = None) -> list[TestRecord]:
        """Return up to ``limit`` test records sorted by time (descending)."""
        filtered: list[TestRecord] = []
        if message_pattern is None:
            for records in self._test_records.values():
                filtered.extend(records)
        else:
            filtered = list(self._test_records.get(message_pattern, []))
        filtered.sort()
        if limit > len(filtered):
            limit = len(filtered)
        return filtered[:limit]

    # -- getters: current test --------------------------------------------

    @property
    def time(self) -> int:
        """Duration of the current test in ms."""
        return self._time

    def get_time(self) -> int:
        return self._time

    @property
    def number_of_backtrackings(self) -> int:
        return self._number_of_backtrackings

    def get_number_of_backtrackings(self) -> int:
        return self._number_of_backtrackings

    @property
    def number_of_nodes(self) -> int:
        return self._number_of_nodes

    def get_number_of_nodes(self) -> int:
        return self._number_of_nodes

    @property
    def number_of_blocked_nodes(self) -> int:
        return self._number_of_blocked_nodes

    def get_number_of_blocked_nodes(self) -> int:
        return self._number_of_blocked_nodes

    def get_test_description(self) -> str:
        if self._reasoning_task_description is None:
            return ""
        return str(self._get_task_description(self._reasoning_task_description))

    def get_test_result(self) -> bool:
        return self._test_result

    # -- getters: current test blocking validation ------------------------

    def get_initial_model_size(self) -> int:
        return self._initial_model_size

    def get_initially_blocked(self) -> int:
        return self._initially_blocked

    def get_initially_invalid(self) -> int:
        return self._initially_invalid

    def get_no_validations(self) -> int:
        return self._no_validations

    def get_validation_time(self) -> int:
        return self._validation_time

    # -- getters: overall -------------------------------------------------

    def get_overall_time(self) -> int:
        return self._overall_time

    def get_overall_number_of_backtrackings(self) -> int:
        return self._overall_number_of_backtrackings

    def get_overall_number_of_nodes(self) -> int:
        return self._overall_number_of_nodes

    def get_overall_number_of_blocked_nodes(self) -> int:
        return self._overall_number_of_blocked_nodes

    def get_overall_number_of_tests(self) -> int:
        return self._overall_number_of_tests

    def get_overall_number_of_clashes(self) -> int:
        return self._overall_number_of_clashes

    def get_number_of_possible_instances_tested(self) -> int:
        return self._possible_instances_tested

    def get_number_of_possible_instances_instances(self) -> int:
        return self._possible_instances_instances

    # -- getters: overall blocking validation -----------------------------

    def get_overall_initial_model_size(self) -> int:
        return self._overall_initial_model_size

    def get_overall_initially_blocked(self) -> int:
        return self._overall_initially_blocked

    def get_overall_initially_invalid(self) -> int:
        return self._overall_initially_invalid

    def get_overall_no_validations(self) -> int:
        return self._overall_no_validations

    def get_overall_validation_time(self) -> int:
        return self._overall_validation_time

    # -- getters: averages ------------------------------------------------

    def get_average_time(self) -> int:
        if self._test_no == 0:
            return 0
        return self._overall_time // self._test_no

    def get_average_number_of_backtrackings(self) -> float:
        if self._test_no == 0:
            return 0
        return self._get_rounded(self._overall_number_of_backtrackings, self._test_no)

    def get_average_number_of_nodes(self) -> float:
        if self._test_no == 0:
            return 0
        return self._get_rounded(self._overall_number_of_nodes, self._test_no)

    def get_average_number_of_blocked_nodes(self) -> float:
        if self._test_no == 0:
            return 0
        return self._get_rounded(self._overall_number_of_blocked_nodes, self._test_no)

    def get_average_number_of_clashes(self) -> float:
        if self._test_no == 0:
            return 0
        return self._get_rounded(self._overall_number_of_clashes, self._test_no)

    def get_possibles_to_instances(self) -> float:
        if self._possible_instances_tested == 0:
            return 0.0
        return self._get_rounded(self._possible_instances_instances, self._possible_instances_tested)

    # -- getters: average blocking validation -----------------------------

    def get_average_initial_model_size(self) -> float:
        if self._test_no == 0:
            return 0
        return self._get_rounded(self._overall_initial_model_size, self._test_no)

    def get_average_initially_blocked(self) -> float:
        if self._test_no == 0:
            return 0
        return self._get_rounded(self._overall_initially_blocked, self._test_no)

    def get_average_initially_invalid(self) -> float:
        if self._test_no == 0:
            return 0
        return self._get_rounded(self._overall_initially_invalid, self._test_no)

    def get_average_no_validations(self) -> float:
        if self._test_no == 0:
            return 0
        return self._get_rounded(self._overall_no_validations, self._test_no)

    def get_average_validation_time(self) -> int:
        if self._test_no == 0:
            return 0
        return self._overall_validation_time // self._test_no

    # -- rounding helper --------------------------------------------------

    @staticmethod
    def _get_rounded(numerator: int, denominator: int, no_decimal_places: int = 2) -> float:
        number = numerator / denominator
        tmp = int(number * (10 ** no_decimal_places))
        return float(tmp / (10 ** no_decimal_places))

    # -- static utility ---------------------------------------------------

    @staticmethod
    def millis_to_hours_minutes_seconds_string(millis: int) -> str:
        """Format milliseconds as a compact ``XhYmZsNNNms`` string."""
        total_secs = millis // 1000
        ms = total_secs % 1000
        time_str = f"{ms:03d}ms"
        secs = total_secs % 60
        if secs > 0:
            time_str = f"{secs:02d}s" + time_str
        mins = (total_secs % 3600) // 60
        if mins > 0:
            time_str = f"{mins:02d}m" + time_str
        hours = total_secs // 3600
        if hours > 0:
            time_str = f"{hours:02d}h" + time_str
        return time_str


# ---------------------------------------------------------------------------
# Timer — prints statistics during reasoning
# ---------------------------------------------------------------------------

class Timer(TableauMonitorAdapter):
    """Prints timing and resource statistics to a stream.

    Faithful port of the Java ``Timer`` monitor.
    """

    def __init__(self, output: TextIO | None = None) -> None:
        super().__init__()
        self._output: TextIO = output if output is not None else sys.stdout
        self._problem_start_time: int = 0
        self._last_status_time: int = 0
        self._number_of_backtrackings: int = 0
        self._test_number: int = 0

    def _start(self) -> None:
        self._number_of_backtrackings = 0
        self._problem_start_time = CountingMonitor._now_ms()
        self._last_status_time = self._problem_start_time

    def is_satisfiable_started(self, reasoning_task_description: _ReasoningTaskDescription) -> None:
        task_desc = self._get_task_description(reasoning_task_description)
        self._output.write(f"{task_desc} ...")
        self._output.flush()
        self._start()

    def is_satisfiable_finished(self, reasoning_task_description: _ReasoningTaskDescription, result: bool) -> None:
        result = CountingMonitor._maybe_flip_result(reasoning_task_description, result)
        self._output.write("YES\n" if result else "NO\n")
        self._do_statistics()

    def iteration_started(self) -> None:
        if CountingMonitor._now_ms() - self._last_status_time > 30000:
            if self._last_status_time == self._problem_start_time:
                self._output.write("\n")
            self._do_statistics()
            self._last_status_time = CountingMonitor._now_ms()

    def saturate_started(self) -> None:
        self._test_number += 1

    def backtrack_to_finished(self, new_current_branching_point: _BranchingPoint) -> None:
        self._number_of_backtrackings += 1

    def _do_statistics(self) -> None:
        duration_so_far = CountingMonitor._now_ms() - self._problem_start_time
        self._output.write("    Test:   ")
        self._print_padded_int(self._test_number, 7)
        self._output.write("  Duration:  ")
        self._print_padded_ms(duration_so_far, 7)
        if self._tableau is not None:
            self._output.write("   Current branching point: ")
            try:
                self._print_padded_int(self._tableau.get_current_branching_point_level(), 7)
            except AttributeError:
                self._print_padded_int(0, 7)
        if self._number_of_backtrackings > 0:
            self._output.write(f"    Backtrackings: {self._number_of_backtrackings}")
        self._output.write("\n")
        self._output.write("    Nodes:  allocated:    ")
        if self._tableau is not None:
            try:
                self._print_padded_int(self._tableau.get_number_of_allocated_nodes(), 7)
            except AttributeError:
                self._print_padded_int(0, 7)
            self._output.write("    used: ")
            try:
                self._print_padded_int(self._tableau.get_number_of_node_creations(), 7)
            except AttributeError:
                self._print_padded_int(0, 7)
            self._output.write("    in tableau: ")
            try:
                self._print_padded_int(self._tableau.get_number_of_nodes_in_tableau(), 7)
            except AttributeError:
                self._print_padded_int(0, 7)
            try:
                merged = self._tableau.get_number_of_merged_or_pruned_nodes()
            except AttributeError:
                merged = 0
            if merged > 0:
                self._output.write(f"    merged/pruned: {merged}")
        else:
            self._print_padded_int(0, 7)
            self._output.write("    used: ")
            self._print_padded_int(0, 7)
            self._output.write("    in tableau: ")
            self._print_padded_int(0, 7)
        self._output.write("\n")
        self._output.write("    Sizes:  binary table: ")
        if self._tableau is not None:
            try:
                ext_mgr = self._tableau.get_extension_manager()
                self._print_padded_kb(ext_mgr.get_binary_extension_table().size_in_memory() // 1000, 7)
            except AttributeError:
                self._print_padded_kb(0, 7)
            self._output.write("    ternary table: ")
            try:
                ext_mgr = self._tableau.get_extension_manager()
                self._print_padded_kb(ext_mgr.get_ternary_extension_table().size_in_memory() // 1000, 7)
            except AttributeError:
                self._print_padded_kb(0, 7)
            self._output.write("    dependency set factory: ")
            try:
                dsf = self._tableau.get_dependency_set_factory()
                self._print_padded_kb(dsf.size_in_memory() // 1000, 7)
            except AttributeError:
                self._print_padded_kb(0, 7)
        else:
            self._print_padded_kb(0, 7)
            self._output.write("    ternary table: ")
            self._print_padded_kb(0, 7)
            self._output.write("    dependency set factory: ")
            self._print_padded_kb(0, 7)
        self._output.write("\n\n")
        self._output.flush()

    def _print_padded_int(self, number: int, padding: int) -> None:
        num_str = str(number)
        self._output.write(num_str)
        for _ in range(len(num_str), padding):
            self._output.write(" ")

    def _print_padded_ms(self, number: int, padding: int) -> None:
        num_str = f"{number} ms"
        self._output.write(num_str)
        for _ in range(len(num_str), padding):
            self._output.write(" ")

    def _print_padded_kb(self, number: int, padding: int) -> None:
        num_str = f"{number} kb"
        self._output.write(num_str)
        for _ in range(len(num_str), padding):
            self._output.write(" ")

    @staticmethod
    def _get_task_description(reasoning_task_description: _ReasoningTaskDescription) -> str:
        try:
            from hermit.model import Prefixes
            return str(reasoning_task_description.get_task_description(Prefixes.STANDARD))
        except Exception:
            return str(reasoning_task_description)


# ---------------------------------------------------------------------------
# TimerWithPause
# ---------------------------------------------------------------------------

class TimerWithPause(Timer):
    """Like :class:`Timer` but pauses for user input after each statistics dump.

    Faithful port of the Java ``TimerWithPause``.
    """

    def __init__(self, output: TextIO | None = None) -> None:
        super().__init__(output)

    def _do_statistics(self) -> None:
        super()._do_statistics()
        print("Press something to continue.. ", end="", flush=True)
        try:
            sys.stdin.readline()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# MemoryConsumptionMonitor
# ---------------------------------------------------------------------------

class MemoryConsumptionMonitor(CountingMonitor):
    """Tracks tableau memory consumption in addition to counting statistics.

    Faithful port of the Java ``MemoryConsumptionMonitor``.
    """

    def __init__(self) -> None:
        super().__init__()
        self._binary_table_mem: int = 0  # in KB
        self._ternary_table_mem: int = 0  # in KB
        self._dependency_sets_mem: int = 0  # in KB
        self._sum_binary_table_mem: int = 0  # in KB
        self._sum_ternary_table_mem: int = 0  # in KB
        self._sum_dependency_sets_mem: int = 0  # in KB
        self._max_mem: int = 0  # in KB
        self._test_number: int = 0

    def is_satisfiable_started(self, reasoning_task_description: _ReasoningTaskDescription) -> None:
        super().is_satisfiable_started(reasoning_task_description)
        self._test_number += 1

    def is_satisfiable_finished(self, reasoning_task_description: _ReasoningTaskDescription, result: bool) -> None:
        super().is_satisfiable_finished(reasoning_task_description, result)
        if self._tableau is not None:
            try:
                ext_mgr = self._tableau.get_extension_manager()
                self._binary_table_mem = ext_mgr.get_binary_extension_table().size_in_memory() // 1024
                self._ternary_table_mem = ext_mgr.get_ternary_extension_table().size_in_memory() // 1024
            except AttributeError:
                self._binary_table_mem = 0
                self._ternary_table_mem = 0
            try:
                dsf = self._tableau.get_dependency_set_factory()
                self._dependency_sets_mem = dsf.size_in_memory() // 1024
            except AttributeError:
                self._dependency_sets_mem = 0
        else:
            self._binary_table_mem = 0
            self._ternary_table_mem = 0
            self._dependency_sets_mem = 0
        self._sum_binary_table_mem += self._binary_table_mem
        self._sum_ternary_table_mem += self._ternary_table_mem
        self._sum_dependency_sets_mem += self._dependency_sets_mem
        total = self._binary_table_mem + self._ternary_table_mem + self._dependency_sets_mem
        if total > self._max_mem:
            self._max_mem = total

    def reset(self) -> None:
        super().reset()
        self._binary_table_mem = 0
        self._ternary_table_mem = 0
        self._dependency_sets_mem = 0
        self._sum_binary_table_mem = 0
        self._sum_ternary_table_mem = 0
        self._sum_dependency_sets_mem = 0
        self._max_mem = 0
        self._test_number = 0

    # -- current test getters ----------------------------------------------

    def get_current_tableau_expansion_memory_use(self) -> int:
        """Total memory used by the current tableau expansion in KB."""
        return self._binary_table_mem + self._ternary_table_mem + self._dependency_sets_mem

    def get_current_tableau_expansion_binary_table_size(self) -> int:
        return self._binary_table_mem

    def get_current_tableau_expansion_ternary_table_size(self) -> int:
        return self._ternary_table_mem

    def get_current_tableau_expansion_dependency_sets_size(self) -> int:
        return self._dependency_sets_mem

    # -- average getters ---------------------------------------------------

    def get_average_tableau_expansion_memory_use(self) -> int:
        if self._test_number == 0:
            return 0
        return (self._sum_binary_table_mem + self._sum_ternary_table_mem + self._sum_dependency_sets_mem) // self._test_number

    def get_average_tableau_expansion_binary_table_size(self) -> int:
        if self._test_number == 0:
            return 0
        return self._sum_binary_table_mem // self._test_number

    def get_average_tableau_expansion_ternary_table_size(self) -> int:
        if self._test_number == 0:
            return 0
        return self._sum_ternary_table_mem // self._test_number

    def get_average_tableau_expansion_dependency_sets_size(self) -> int:
        if self._test_number == 0:
            return 0
        return self._sum_dependency_sets_mem // self._test_number

    # -- max getter --------------------------------------------------------

    def get_max_tableau_expansion_memory_use(self) -> int:
        return self._max_mem
