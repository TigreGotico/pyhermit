"""Interface for dependency sets used in clash-driven backtracking."""

from __future__ import annotations

from abc import ABC, abstractmethod


class DependencySet(ABC):
    """Abstract interface for dependency sets.

    A dependency set records the branching points on which a derived
    assertion depends, enabling conflict-directed backtracking.
    """

    __slots__ = ()

    @abstractmethod
    def contains_branching_point(self, branching_point: int) -> bool:
        """Return ``True`` if *branching_point* is in this set."""
        ...

    @abstractmethod
    def is_empty(self) -> bool:
        """Return ``True`` if the set contains no branching points."""
        ...

    @abstractmethod
    def get_maximum_branching_point(self) -> int:
        """Return the highest branching point in this set, or ``-1`` if empty."""
        ...
