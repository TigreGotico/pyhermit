"""Branching point for disjunction expansion."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hermit.tableau.branching_point import BranchingPoint

if TYPE_CHECKING:
    from hermit.tableau.dependency_set import DependencySet
    from hermit.tableau.ground_disjunction import GroundDisjunction
    from hermit.tableau.tableau import Tableau


class DisjunctionBranchingPoint(BranchingPoint):
    """Branching point created when a ground disjunction is expanded.

    This branching point manages the exploration of individual disjuncts
    of a ground disjunction, adding negated alternatives for previously
    tried disjuncts when backtracking.

    Args:
        tableau: The tableau.
        ground_disjunction: The disjunction being branched on.
        sorted_disjunct_indexes: Indices of disjuncts sorted by heuristic.
    """

    __slots__ = (
        "_ground_disjunction",
        "_sorted_disjunct_indexes",
        "_current_index",
    )

    def __init__(
        self,
        tableau: Tableau,
        ground_disjunction: GroundDisjunction,
        sorted_disjunct_indexes: list[int],
    ) -> None:
        super().__init__(tableau)
        self._ground_disjunction = ground_disjunction
        self._sorted_disjunct_indexes = sorted_disjunct_indexes
        self._current_index = 0

    # ------------------------------------------------------------------
    # BranchingPoint override
    # ------------------------------------------------------------------

    def start_next_choice(
        self, tableau: Tableau, clash_dependency_set: DependencySet
    ) -> None:
        """Advance to the next disjunct, adding negations of previous choices.

        Args:
            tableau: The tableau to advance.
            clash_dependency_set: The dependency set that caused the clash.
        """
        from hermit.model import AtomicConcept, Equality, Inequality

        if tableau.m_use_disjunction_learning:
            self._ground_disjunction.ground_disjunction_header.increase_number_of_backtrackings(  # noqa: E501
                self._sorted_disjunct_indexes[self._current_index]
            )

        self._current_index += 1
        assert self._current_index < self._ground_disjunction.get_number_of_disjuncts()

        current_disjunct_index = self._sorted_disjunct_indexes[self._current_index]

        if tableau.m_tableau_monitor is not None:
            tableau.m_tableau_monitor.disjunct_processing_started(
                self._ground_disjunction, current_disjunct_index
            )

        dependency_set = tableau.dependency_set_factory.get_permanent(
            clash_dependency_set
        )
        if self._current_index + 1 == self._ground_disjunction.get_number_of_disjuncts():
            dependency_set = tableau.dependency_set_factory.remove_branching_point(
                dependency_set, self.level
            )

        # Add negations of all previously tried disjuncts
        for previous_index in range(self._current_index):
            previous_disjunct_index = self._sorted_disjunct_indexes[previous_index]
            dl_predicate = self._ground_disjunction.get_dl_predicate(
                previous_disjunct_index
            )
            if Equality.INSTANCE is dl_predicate or isinstance(
                dl_predicate, Equality
            ):
                tableau.m_extension_manager.add_assertion(
                    Inequality.INSTANCE,
                    self._ground_disjunction.get_argument(previous_disjunct_index, 0),
                    self._ground_disjunction.get_argument(previous_disjunct_index, 1),
                    dependency_set,
                    False,
                )
            elif isinstance(dl_predicate, AtomicConcept):
                tableau.m_extension_manager.add_concept_assertion(
                    dl_predicate.get_negation(),  # type: ignore[attr-defined]
                    self._ground_disjunction.get_argument(previous_disjunct_index, 0),
                    dependency_set,
                    False,
                )

        self._ground_disjunction.add_disjunct_to_tableau(
            tableau, current_disjunct_index, dependency_set
        )

        if tableau.m_tableau_monitor is not None:
            tableau.m_tableau_monitor.disjunct_processing_finished(
                self._ground_disjunction, current_disjunct_index
            )
