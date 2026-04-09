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
    structurally equivalent sets share the same object instance.  It also
    tracks usage counts and reclaims unused sets.
    """

    def __init__(self) -> None:
        self._merge_array = _IntegerArray()
        self._merge_sets: list[PermanentDependencySet] = []
        self._unprocessed_sets: list[UnionDependencySet] = []
        self._empty_set: PermanentDependencySet | None = None
        self._first_unused_set: PermanentDependencySet | None = None
        self._first_destroyed_set: PermanentDependencySet | None = None
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
        empty_set._usage_counter = 1
        empty_set._rest = None
        empty_set._previous_unused_set = None
        empty_set._next_unused_set = None

        self._empty_set = empty_set
        self._first_unused_set = None
        self._first_destroyed_set = None
        self._entries = [None] * 16
        self._resize_threshold = int(len(self._entries) * 0.75)
        self._size = 0

    @property
    def empty_set(self) -> PermanentDependencySet:
        """Return the canonical empty dependency set."""
        assert self._empty_set is not None
        return self._empty_set

    def remove_unused_sets(self) -> None:
        """Destroy all dependency sets whose usage counter has reached zero."""
        while self._first_unused_set is not None:
            self._destroy_dependency_set(self._first_unused_set)

    def add_usage(self, dependency_set: PermanentDependencySet) -> None:
        """Increment the usage counter for *dependency_set*."""
        assert (
            dependency_set._branching_point >= 0
            or dependency_set is self._empty_set
        )
        if dependency_set._usage_counter == 0:
            self._remove_from_unused_list(dependency_set)
        dependency_set._usage_counter += 1

    def remove_usage(self, dependency_set: PermanentDependencySet) -> None:
        """Decrement the usage counter; add to unused list when it hits zero."""
        assert (
            dependency_set._branching_point >= 0
            or dependency_set is self._empty_set
        )
        assert dependency_set._usage_counter > 0
        assert dependency_set._previous_unused_set is None
        assert dependency_set._next_unused_set is None
        dependency_set._usage_counter -= 1
        if dependency_set._usage_counter == 0:
            self._add_to_unused_list(dependency_set)

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

        # Flatten UnionDependencySet constituents
        from hermit.tableau.union_dependency_set import UnionDependencySet

        self._unprocessed_sets.clear()
        self._merge_sets.clear()
        self._unprocessed_sets.append(dependency_set)  # type: ignore[arg-type]

        while self._unprocessed_sets:
            union_ds = self._unprocessed_sets.pop()
            for idx in range(union_ds.m_number_of_constituents):
                constituent = union_ds.m_dependency_sets[idx]
                if isinstance(constituent, UnionDependencySet):
                    self._unprocessed_sets.append(constituent)
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
        """Allocate and initialise a new PermanentDependencySet."""
        if self._first_destroyed_set is None:
            new_set = PermanentDependencySet()
        else:
            new_set = self._first_destroyed_set
            self._first_destroyed_set = self._first_destroyed_set._next_entry

        new_set._rest = rest
        new_set._branching_point = branching_point
        new_set._usage_counter = 0
        self.add_usage(new_set._rest)  # type: ignore[arg-type]
        self._add_to_unused_list(new_set)
        self._size += 1
        return new_set

    def _destroy_dependency_set(self, dependency_set: PermanentDependencySet) -> None:
        """Remove *dependency_set* from the factory."""
        assert dependency_set._branching_point >= 0
        assert dependency_set._usage_counter == 0
        assert dependency_set._rest is not None
        assert dependency_set._rest._usage_counter > 0

        self._remove_from_unused_list(dependency_set)
        self.remove_usage(dependency_set._rest)  # type: ignore[arg-type]
        self._remove_from_entries(dependency_set)
        dependency_set._rest = None
        dependency_set._branching_point = -2
        dependency_set._next_entry = self._first_destroyed_set
        self._first_destroyed_set = dependency_set
        self._size -= 1

    def _remove_from_entries(self, dependency_set: PermanentDependencySet) -> None:
        """Remove *dependency_set* from the hash table."""
        index = dependency_set._hash() & (len(self._entries) - 1)
        last_entry: PermanentDependencySet | None = None
        entry: PermanentDependencySet | None = self._entries[index]
        while entry is not None:
            if entry is dependency_set:
                if last_entry is None:
                    self._entries[index] = dependency_set._next_entry
                else:
                    last_entry._next_entry = dependency_set._next_entry
                return
            last_entry = entry
            entry = entry._next_entry
        raise RuntimeError(
            "Internal error: dependency set not in the entries table. "
            "Please inform HermiT authors about this."
        )

    def _remove_from_unused_list(self, dependency_set: PermanentDependencySet) -> None:
        """Unlink *dependency_set* from the doubly-linked unused list."""
        if dependency_set._previous_unused_set is not None:
            dependency_set._previous_unused_set._next_unused_set = (
                dependency_set._next_unused_set
            )
        else:
            self._first_unused_set = dependency_set._next_unused_set
        if dependency_set._next_unused_set is not None:
            dependency_set._next_unused_set._previous_unused_set = (
                dependency_set._previous_unused_set
            )
        dependency_set._previous_unused_set = None
        dependency_set._next_unused_set = None

    def _add_to_unused_list(self, dependency_set: PermanentDependencySet) -> None:
        """Prepend *dependency_set* to the doubly-linked unused list."""
        dependency_set._previous_unused_set = None
        dependency_set._next_unused_set = self._first_unused_set
        if self._first_unused_set is not None:
            self._first_unused_set._previous_unused_set = dependency_set
        self._first_unused_set = dependency_set

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
