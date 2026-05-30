"""Permanent (interned) dependency set stored in the factory's hash table."""

from __future__ import annotations

from hermit.tableau.dependency_set import DependencySet


class PermanentDependencySet(DependencySet):
    """A permanent, interned dependency set.

    Permanent dependency sets are managed by :class:`DependencySetFactory`
    and are shared (interned) so that structural equality is equivalent to
    object identity (``is``).  They are organised as a linked list of branching
    points sorted in descending order.

    Once created by the factory the *content* of a permanent set is immutable:
    ``_rest`` and ``_branching_point`` are never reassigned, which is what
    makes interning (and ``is``-equality) sound.  There is no reference
    counting; interned sets are reclaimed by Python's garbage collector when
    the factory's hash table is dropped.

    Fields:

    * ``_rest`` -- the remainder of the linked list (tail); immutable content.
    * ``_branching_point`` -- the branching point stored at this node
      (``-1`` indicates the empty set); immutable content.
    * ``_next_entry`` -- next entry in the same hash bucket; pure table
      bookkeeping, reassigned only on rehash.
    """

    __slots__ = (
        "_rest",
        "_branching_point",
        "_next_entry",
    )

    def __init__(self) -> None:
        self._rest: PermanentDependencySet | None = None
        self._branching_point: int = -2
        self._next_entry: PermanentDependencySet | None = None

    # -- DependencySet interface ---------------------------------------

    def contains_branching_point(self, branching_point: int) -> bool:
        """Return ``True`` if *branching_point* appears in this set."""
        node: PermanentDependencySet | None = self
        while node is not None:
            if node._branching_point == branching_point:
                return True
            node = node._rest
        return False

    def is_empty(self) -> bool:
        """Return ``True`` when the set represents the empty dependency set."""
        return self._branching_point == -1

    def get_maximum_branching_point(self) -> int:
        """Return the highest branching point (first element in the list)."""
        return self._branching_point

    # -- Internal helpers (used by DependencySetFactory) ----------------

    def _hash(self) -> int:
        """Hash function consistent with the Java implementation."""
        # The Java code computes: (rest.hashCode() + branchingPoint) & (length-1)
        rest_hash = hash(self._rest) if self._rest is not None else 0
        return rest_hash + self._branching_point

    # -- Debugging -----------------------------------------------------

    def __str__(self) -> str:
        parts: list[str] = []
        dep: PermanentDependencySet | None = self
        while dep is not None and dep._branching_point != -1:
            parts.append(str(dep._branching_point))
            dep = dep._rest
        return "{ " + ", ".join(parts) + " }" if parts else "{ }"
