"""Temporary dependency set formed as a union of constituents."""

from __future__ import annotations

from hermit.tableau.dependency_set import DependencySet


class UnionDependencySet(DependencySet):
    """A temporary dependency set that is the union of multiple constituents.

    This is a lightweight, mutable structure used during computation.  When
    a permanent representation is needed, pass it to
    :meth:`DependencySetFactory.get_permanent`.

    Args:
        number_of_constituents: Initial capacity for constituent sets.
    """

    def __init__(self, number_of_constituents: int) -> None:
        self.m_dependency_sets: list[DependencySet | None] = [
            None
        ] * number_of_constituents
        self.m_number_of_constituents = number_of_constituents

    # -- DependencySet interface ---------------------------------------

    def contains_branching_point(self, branching_point: int) -> bool:
        """Return ``True`` if any constituent contains *branching_point*."""
        for idx in range(self.m_number_of_constituents - 1, -1, -1):
            constituent = self.m_dependency_sets[idx]
            if constituent is not None and constituent.contains_branching_point(
                branching_point
            ):
                return True
        return False

    def get_maximum_branching_point(self) -> int:
        """Return the maximum branching point across all constituents."""
        maximum = self.m_dependency_sets[0].get_maximum_branching_point()  # type: ignore[union-attr]
        for idx in range(self.m_number_of_constituents - 1, 0, -1):
            constituent = self.m_dependency_sets[idx]
            if constituent is not None:
                bp = constituent.get_maximum_branching_point()
                if bp > maximum:
                    maximum = bp
        return maximum

    def is_empty(self) -> bool:
        """Return ``True`` when every constituent is empty."""
        for idx in range(self.m_number_of_constituents - 1, -1, -1):
            constituent = self.m_dependency_sets[idx]
            if constituent is not None and not constituent.is_empty():
                return False
        return True

    # -- Mutators ------------------------------------------------------

    def clear_constituents(self) -> None:
        """Remove all constituents from this union."""
        for idx in range(self.m_number_of_constituents):
            self.m_dependency_sets[idx] = None
        self.m_number_of_constituents = 0

    def add_constituent(self, constituent: DependencySet) -> None:
        """Append *constituent* to this union, resizing the internal array if needed."""
        if self.m_number_of_constituents == len(self.m_dependency_sets):
            new_len = self.m_number_of_constituents * 3 // 2
            new_array: list[DependencySet | None] = [None] * new_len
            new_array[: len(self.m_dependency_sets)] = self.m_dependency_sets
            self.m_dependency_sets = new_array
        self.m_dependency_sets[self.m_number_of_constituents] = constituent
        self.m_number_of_constituents += 1
