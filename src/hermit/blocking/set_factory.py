"""Factory for canonical immutable sets.

Faithful port of ``org.semanticweb.HermiT.blocking.SetFactory`` from the Java
HermiT OWL reasoner.

This class ensures that each distinct set exists only once, allowing sets to be
compared with identity (``is`` in Python).  Instances are used to create various
labels in blocking.

Classes
-------
SetFactory
    Creates and interns immutable sets of elements of type *E*.
"""

from __future__ import annotations

from collections.abc import Collection, Iterator
from typing import Generic, TypeVar

E = TypeVar("E")


class SetFactory(Generic[E]):
    """Factory that canonicalises immutable sets.

    Each distinct set (by element equality) is stored exactly once.  The
    returned ``FrozenSetEntry`` objects implement ``collections.abc.Set`` and
    compare equal only by identity, enabling ``is`` comparison.
    """

    __slots__ = (
        "_unused_entries",
        "_entries",
        "_size",
        "_resize_threshold",
    )

    def __init__(self) -> None:
        self._unused_entries: list[Entry[E] | None] = [None] * 32
        self._entries: list[Entry[E] | None] = [None] * 16
        self._size = 0
        self._resize_threshold = int(0.75 * len(self._entries))

    def clear_nonpermanent(self) -> None:
        """Remove all non-permanent entries from the cache."""
        for i in range(len(self._entries) - 1, -1, -1):
            entry = self._entries[i]
            while entry is not None:
                next_entry = entry.m_next_entry
                if not entry.m_permanent:
                    self._remove_entry(entry)
                    self._leave_entry(entry)
                entry = next_entry

    def add_reference(self, s: frozenset[E] | Entry[E]) -> None:
        """Increment the reference count for *s*."""
        entry = self._as_entry(s)
        entry.m_reference_count += 1

    def remove_reference(self, s: frozenset[E] | Entry[E]) -> None:
        """Decrement the reference count and possibly evict the entry."""
        entry = self._as_entry(s)
        entry.m_reference_count -= 1
        if entry.m_reference_count == 0 and not entry.m_permanent:
            self._remove_entry(entry)
            self._leave_entry(entry)

    def make_permanent(self, s: frozenset[E] | Entry[E]) -> None:
        """Mark *s* as permanent so it will never be evicted."""
        self._as_entry(s).m_permanent = True

    def get_set(self, elements: list[E]) -> frozenset[E] | Entry[E]:
        """Return the canonical set containing exactly *elements*.

        If an equivalent set already exists it is returned; otherwise a new
        entry is created, stored, and returned.
        """
        hash_code = sum(hash(e) for e in elements)
        index = self._get_index_for(hash_code, len(self._entries))
        entry: Entry[E] | None = self._entries[index]
        while entry is not None:
            if hash_code == entry.m_hash_code and entry._equals_list(elements):
                return entry
            entry = entry.m_next_entry

        entry = self._get_entry(len(elements))
        entry._initialise(elements, hash_code)
        entry.m_previous_entry = None
        entry.m_next_entry = self._entries[index]
        if entry.m_next_entry is not None:
            entry.m_next_entry.m_previous_entry = entry
        self._entries[index] = entry
        self._size += 1
        if self._size > self._resize_threshold:
            self._resize()
        return entry

    # -- internal helpers --------------------------------------------------

    def _as_entry(self, s: frozenset[E] | Entry[E]) -> Entry[E]:
        if isinstance(s, Entry):
            return s
        # Should not happen in normal usage -- all sets come from this factory.
        raise TypeError(f"Expected Entry, got {type(s).__name__}")

    def _resize(self) -> None:
        new_entries: list[Entry[E] | None] = [None] * (len(self._entries) * 2)
        for index in range(len(self._entries)):
            entry = self._entries[index]
            while entry is not None:
                next_entry = entry.m_next_entry
                new_index = self._get_index_for(entry.m_hash_code, len(new_entries))
                entry.m_next_entry = new_entries[new_index]
                entry.m_previous_entry = None
                if entry.m_next_entry is not None:
                    entry.m_next_entry.m_previous_entry = entry
                new_entries[new_index] = entry
                entry = next_entry
        self._entries = new_entries
        self._resize_threshold = int(0.75 * len(self._entries))

    def _remove_entry(self, entry: Entry[E]) -> None:
        if entry.m_next_entry is not None:
            entry.m_next_entry.m_previous_entry = entry.m_previous_entry
        if entry.m_previous_entry is not None:
            entry.m_previous_entry.m_next_entry = entry.m_next_entry
        index = self._get_index_for(entry.m_hash_code, len(self._entries))
        if self._entries[index] is entry:
            self._entries[index] = entry.m_next_entry
        entry.m_next_entry = None
        entry.m_previous_entry = None

    def _get_entry(self, size: int) -> Entry[E]:
        if size >= len(self._unused_entries):
            new_size = len(self._unused_entries)
            while new_size <= size:
                new_size = new_size * 3 // 2
            new_unused: list[Entry[E] | None] = [None] * new_size
            new_unused[: len(self._unused_entries)] = self._unused_entries
            self._unused_entries = new_unused
        entry = self._unused_entries[size]
        if entry is None:
            return Entry(size)
        else:
            self._unused_entries[size] = entry.m_next_entry
            entry.m_next_entry = None
            return entry

    def _leave_entry(self, entry: Entry[E]) -> None:
        entry.m_next_entry = self._unused_entries[entry.size()]
        entry.m_previous_entry = None
        self._unused_entries[entry.size()] = entry

    @staticmethod
    def _get_index_for(hash_code: int, table_length: int) -> int:
        return hash_code & (table_length - 1)


class Entry(Generic[E]):
    """An immutable set entry that also acts as a set.

    Mirrors the Java ``SetFactory.Entry`` inner class.
    """

    __slots__ = (
        "m_table",
        "m_hash_code",
        "m_previous_entry",
        "m_next_entry",
        "m_reference_count",
        "m_permanent",
    )

    def __init__(self, size: int) -> None:
        self.m_table: list[E] = [None] * size  # type: ignore[list-item]
        self.m_hash_code = 0
        self.m_previous_entry: Entry[E] | None = None
        self.m_next_entry: Entry[E] | None = None
        self.m_reference_count = 0
        self.m_permanent = False

    def _initialise(self, elements: list[E], hash_code: int) -> None:
        for i, e in enumerate(elements):
            self.m_table[i] = e
        self.m_hash_code = hash_code

    def _equals_list(self, elements: list[E]) -> bool:
        if len(self.m_table) != len(elements):
            return False
        for item in self.m_table:
            if item not in elements:
                return False
        return True

    # -- collections.abc.Set protocol ---------------------------------------

    def __contains__(self, item: object) -> bool:
        return any(item == elem for elem in self.m_table)

    def __iter__(self) -> Iterator[E]:
        return iter(self.m_table)

    def __len__(self) -> int:
        return len(self.m_table)

    def isdisjoint(self, other: Collection[E]) -> bool:
        return all(item not in self for item in other)

    # -- mutation (not supported) ------------------------------------------

    def clear(self) -> None:
        raise NotImplementedError

    def add(self, item: E) -> bool:
        raise NotImplementedError

    def discard(self, item: E) -> None:
        raise NotImplementedError

    # -- object protocol ---------------------------------------------------

    def __hash__(self) -> int:
        return self.m_hash_code

    def __eq__(self, other: object) -> bool:
        return self is other

    def size(self) -> int:
        """Return the number of elements."""
        return len(self.m_table)

    def __repr__(self) -> str:
        return f"SetFactory.Entry({self.m_table!r})"
