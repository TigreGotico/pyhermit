"""Factory for creating, caching, and managing permanent dependency sets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hermit.tableau.permanent_dependency_set import PermanentDependencySet

if TYPE_CHECKING:
    from hermit.tableau.dependency_set import DependencySet
    from hermit.tableau.union_dependency_set import UnionDependencySet


class _IntegerArray:
    """Lightweight mutable int array used as a merge buffer."""

    __slots__ = ("_elements", "_size")

    def __init__(self) -> None:
        self._elements: list[int] = [0] * 64
        self._size: int = 0

    def clear(self) -> None:
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def __getitem__(self, index: int) -> int:
        return self._elements[index]

    def add(self, element: int) -> None:
        if self._size >= len(self._elements):
            new_len = len(self._elements) * 3 // 2
            new_elements = [0] * new_len
            new_elements[: len(self._elements)] = self._elements
            self._elements = new_elements
        self._elements[self._size] = element
        self._size += 1


class DependencySetFactory:
    """Factory for creating and interning :class:`PermanentDependencySet` instances.

    The factory maintains a hash table of existing permanent sets so that
    structurally equivalent sets share the same object instance: two dependency
    sets with the same content are the *same* object, so equality is object
    identity (``is``) and hashing is structural.

    Interned sets are immutable in content and live for the lifetime of the
    factory; there is no manual reclamation.  Python's garbage collector
    reclaims everything when :meth:`clear` drops the hash table (or when the
    factory itself is collected).  The :meth:`add_usage`, :meth:`remove_usage`
    and :meth:`remove_unused_sets` methods are retained as no-ops so existing
    callers need not change, but they perform no reference counting.
    """

    def __init__(self) -> None:
        self._merge_array = _IntegerArray()
        self._merge_sets: list[PermanentDependencySet] = []
        self._unprocessed_sets: list[UnionDependencySet] = []
        self._empty_set: PermanentDependencySet | None = None
        self._entries: list[PermanentDependencySet | None] = [None] * 16
        self._size: int = 0
        self._resize_threshold: int = int(len(self._entries) * 0.75)
        self._clear()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def size_in_memory(self) -> int:
        """Approximate memory footprint in bytes."""
        return len(self._entries) * 4 + self._size * 20

    def clear(self) -> None:
        """Reset the factory to its initial state."""
        self._clear()

    def _clear(self) -> None:
        self._merge_array.clear()
        self._merge_sets.clear()
        self._unprocessed_sets.clear()

        empty_set = PermanentDependencySet()
        empty_set._branching_point = -1
        empty_set._rest = None

        self._empty_set = empty_set
        self._entries = [None] * 16
        self._resize_threshold = int(len(self._entries) * 0.75)
        self._size = 0

    @property
    def empty_set(self) -> PermanentDependencySet:
        """Return the canonical empty dependency set."""
        assert self._empty_set is not None
        return self._empty_set

    def remove_unused_sets(self) -> None:
        """No-op: interned sets are reclaimed by Python's garbage collector.

        Retained for call-site compatibility.  Interned permanent sets are
        immutable and shared; they live for the lifetime of the factory and
        are dropped wholesale by :meth:`clear`, so there is nothing to reclaim
        eagerly here.
        """

    def add_usage(self, dependency_set: PermanentDependencySet) -> None:
        """No-op: usage is no longer reference-counted (see class docstring)."""

    def remove_usage(self, dependency_set: PermanentDependencySet) -> None:
        """No-op: usage is no longer reference-counted (see class docstring)."""

    def add_branching_point(
        self, dependency_set: DependencySet | None, branching_point: int
    ) -> PermanentDependencySet:
        """Return a permanent set equivalent to *dependency_set* plus *branching_point*."""
        permanent = self.get_permanent(dependency_set)
        if branching_point > permanent._branching_point:
            return self._get_dependency_set(permanent, branching_point)
        elif branching_point == permanent._branching_point:
            return permanent
        else:
            self._merge_array.clear()
            rest = permanent
            while branching_point < rest._branching_point:
                self._merge_array.add(rest._branching_point)
                rest = rest._rest  # type: ignore[assignment]
            if branching_point == rest._branching_point:
                return permanent
            else:
                rest = self._get_dependency_set(rest, branching_point)
                for idx in range(len(self._merge_array) - 1, -1, -1):
                    rest = self._get_dependency_set(
                        rest, self._merge_array[idx]
                    )
                return rest

    def remove_branching_point(
        self, dependency_set: DependencySet, branching_point: int
    ) -> PermanentDependencySet:
        """Return a permanent set with *branching_point* removed."""
        permanent = self.get_permanent(dependency_set)
        if branching_point == permanent._branching_point:
            return permanent._rest  # type: ignore[return-value]
        elif branching_point > permanent._branching_point:
            return permanent
        else:
            self._merge_array.clear()
            rest = permanent
            while branching_point < rest._branching_point:
                self._merge_array.add(rest._branching_point)
                rest = rest._rest  # type: ignore[assignment]
            if branching_point != rest._branching_point:
                return permanent
            else:
                rest = rest._rest  # type: ignore[assignment]
                for idx in range(len(self._merge_array) - 1, -1, -1):
                    rest = self._get_dependency_set(
                        rest, self._merge_array[idx]
                    )
                return rest

    def union_with(
        self, set1: DependencySet, set2: DependencySet
    ) -> PermanentDependencySet:
        """Return the union of two dependency sets."""
        perm1 = self.get_permanent(set1)
        perm2 = self.get_permanent(set2)
        if perm1 is perm2:
            return perm1
        self._merge_array.clear()
        while perm1 is not perm2:
            if perm1._branching_point > perm2._branching_point:
                self._merge_array.add(perm1._branching_point)
                perm1 = perm1._rest  # type: ignore[assignment]
            elif perm1._branching_point < perm2._branching_point:
                self._merge_array.add(perm2._branching_point)
                perm2 = perm2._rest  # type: ignore[assignment]
            else:
                self._merge_array.add(perm1._branching_point)
                perm1 = perm1._rest  # type: ignore[assignment]
                perm2 = perm2._rest  # type: ignore[assignment]
        result = perm1
        for idx in range(len(self._merge_array) - 1, -1, -1):
            result = self._get_dependency_set(result, self._merge_array[idx])
        return result

    def get_permanent(
        self, dependency_set: DependencySet | None
    ) -> PermanentDependencySet:
        """Return a :class:`PermanentDependencySet` equivalent to *dependency_set*.

        If the argument is already permanent it is returned as-is.
        If ``None``, returns the empty set.
        Otherwise the factory flattens any :class:`UnionDependencySet` and
        interns the result.
        """
        if dependency_set is None:
            return self.empty_set
        if isinstance(dependency_set, PermanentDependencySet):
            return dependency_set

        # Flatten union-of-constituents dependency sets. Several distinct union
        # implementations exist (UnionDependencySet plus the lightweight inline
        # unions in MergingManager and ClashManager); they share the
        # m_number_of_constituents / m_dependency_sets duck-typed interface but do
        # not share a base class, so recognise a union by that interface rather
        # than by a single concrete type.
        self._unprocessed_sets.clear()
        self._merge_sets.clear()
        self._unprocessed_sets.append(dependency_set)  # type: ignore[arg-type]

        while self._unprocessed_sets:
            union_ds = self._unprocessed_sets.pop()
            for idx in range(union_ds.m_number_of_constituents):
                constituent = union_ds.m_dependency_sets[idx]
                if constituent is None:
                    continue
                elif isinstance(constituent, PermanentDependencySet):
                    self._merge_sets.append(constituent)
                elif hasattr(constituent, "m_number_of_constituents"):
                    self._unprocessed_sets.append(constituent)  # type: ignore[arg-type]
                else:
                    self._merge_sets.append(constituent)  # type: ignore[arg-type]

        num_sets = len(self._merge_sets)
        self._merge_array.clear()

        # Handle case where there are no merge sets (empty dependency)
        if num_sets == 0:
            return self.empty_set

        while True:
            first_set = self._merge_sets[0]
            maximal = first_set._branching_point
            maximal_index = 0
            has_equals = False
            all_are_equal = True

            for idx in range(1, num_sets):
                perm = self._merge_sets[idx]
                bp = perm._branching_point
                if bp > maximal:
                    maximal = bp
                    has_equals = False
                    maximal_index = idx
                elif bp == maximal:
                    has_equals = True
                if perm is not first_set:
                    all_are_equal = False

            if all_are_equal:
                break

            self._merge_array.add(maximal)
            if has_equals:
                for idx in range(num_sets):
                    perm = self._merge_sets[idx]
                    if perm._branching_point == maximal:
                        self._merge_sets[idx] = perm._rest  # type: ignore[assignment]
            else:
                perm = self._merge_sets[maximal_index]
                self._merge_sets[maximal_index] = perm._rest  # type: ignore[assignment]

        result = self._merge_sets[0]
        for idx in range(len(self._merge_array) - 1, -1, -1):
            result = self._get_dependency_set(result, self._merge_array[idx])
        self._merge_sets.clear()
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_dependency_set(
        self, rest: PermanentDependencySet, branching_point: int
    ) -> PermanentDependencySet:
        """Look up or create a permanent set for (*rest*, *branching_point*)."""
        index = rest._hash() & (len(self._entries) - 1)
        entry: PermanentDependencySet | None = self._entries[index]
        while entry is not None:
            if entry._rest is rest and entry._branching_point == branching_point:
                return entry
            entry = entry._next_entry

        dependency_set = self._create_dependency_set(rest, branching_point)
        dependency_set._next_entry = self._entries[index]
        self._entries[index] = dependency_set
        if self._size >= self._resize_threshold:
            self._resize_entries()
        return dependency_set

    def _create_dependency_set(
        self, rest: PermanentDependencySet, branching_point: int
    ) -> PermanentDependencySet:
        """Allocate and initialise a new interned PermanentDependencySet.

        The new set is immutable in content (``_rest`` and ``_branching_point``
        never change after this point) and is kept alive by the entries table
        for the lifetime of the factory.  No reference counting is performed.
        """
        new_set = PermanentDependencySet()
        new_set._rest = rest
        new_set._branching_point = branching_point
        self._size += 1
        return new_set

    def _resize_entries(self) -> None:
        """Double the hash table size and rehash all entries."""
        new_length = len(self._entries) * 2
        new_length_minus_one = new_length - 1
        new_entries: list[PermanentDependencySet | None] = [None] * new_length

        for old_index in range(len(self._entries)):
            entry = self._entries[old_index]
            while entry is not None:
                next_entry = entry._next_entry
                new_index = entry._hash() & new_length_minus_one
                entry._next_entry = new_entries[new_index]
                new_entries[new_index] = entry
                entry = next_entry

        self._entries = new_entries
        self._resize_threshold = int(len(self._entries) * 0.75)
