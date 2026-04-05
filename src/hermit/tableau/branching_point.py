"""Base branching point for tableau backtracking."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.tableau.dependency_set import DependencySet
    from hermit.tableau.tableau import Tableau


class BranchingPoint:
    """Snapshot of the tableau state at a branching decision.

    A branching point captures enough information to restore the tableau
    to this state during backtracking.  Subclasses (such as
    :class:`DisjunctionBranchingPoint`) add choice-specific data.

    Args:
        tableau: The tableau whose state is being snapshotted.
    """

    __slots__ = (
        "_level",
        "_last_tableau_node",
        "_last_merged_or_pruned_node",
        "_first_ground_disjunction",
        "_first_unprocessed_ground_disjunction",
    )

    def __init__(self, tableau: Tableau) -> None:
        self._level = tableau.m_current_branching_point + 1
        self._last_tableau_node = tableau.m_last_tableau_node
        self._last_merged_or_pruned_node = tableau.m_last_merged_or_pruned_node
        self._first_ground_disjunction = tableau.m_first_ground_disjunction
        self._first_unprocessed_ground_disjunction = (
            tableau.m_first_unprocessed_ground_disjunction
        )

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def level(self) -> int:
        """Return the branching level (depth) of this point."""
        return self._level

    def start_next_choice(
        self, tableau: Tableau, clash_dependency_set: DependencySet
    ) -> None:
        """Advance to the next choice at this branching point.

        The base implementation is a no-op; subclasses override to
        implement choice-specific behaviour (e.g., trying the next
        disjunct).

        Args:
            tableau: The tableau to advance.
            clash_dependency_set: The dependency set that caused the clash
                triggering this backtrack.
        """
