"""Tuple table with full hash index.

Hash-based index for tuple tables with arbitrary arity. Used primarily
for description graph tuples where the arity exceeds three.
"""

from __future__ import annotations

from hermit.tableau.tuple_table import TupleTable


class TupleTableFullIndex:
    """Full hash index over tuples of arbitrary arity.

    Uses a hash table with chaining to map tuples to their indices
    in the underlying TupleTable.
    """

    BUCKET_OFFSET = 1
    LOAD_FACTOR = 0.75

    def __init__(self, tuple_table: TupleTable, indexed_arity: int) -> None:
        self.m_tuple_table = tuple_table
        self.m_indexed_arity = indexed_arity
        self.m_entry_manager = _EntryManager()
        self.m_buckets: list[int] = []
        self.m_resize_threshold = 0
        self.m_number_of_tuples = 0
        self.clear()

    def size_in_memory(self) -> int:
        """Estimate memory usage."""
        return len(self.m_buckets) * 4 + self.m_entry_manager.size()

    def clear(self) -> None:
        """Clear the index."""
        self.m_buckets = [0] * 16
        self.m_resize_threshold = int(len(self.m_buckets) * TupleTableFullIndex.LOAD_FACTOR)
        self.m_entry_manager.clear()

    def add_tuple(
        self, tup: list[object], tentative_tuple_index: int
    ) -> int:
        """Add a tuple to the index.

        Returns the existing tuple index if already present, otherwise
        returns *tentative_tuple_index*.
        """
        hash_code = self._get_tuple_hash_code(tup)
        entry_index = self._get_bucket_index(hash_code, len(self.m_buckets))
        entry = self.m_buckets[entry_index] - TupleTableFullIndex.BUCKET_OFFSET
        while entry != -1:
            if hash_code == self.m_entry_manager.get_entry_component(
                entry, _EntryManager.ENTRY_HASH_CODE
            ):
                tuple_index = self.m_entry_manager.get_entry_component(
                    entry, _EntryManager.ENTRY_TUPLE_INDEX
                )
                if self.m_tuple_table.tuple_equals(tup, tuple_index, self.m_indexed_arity):
                    return tuple_index
            entry = self.m_entry_manager.get_entry_component(
                entry, _EntryManager.ENTRY_NEXT
            )
        entry = self.m_entry_manager.new_entry()
        self.m_entry_manager.set_entry_component(
            entry,
            _EntryManager.ENTRY_NEXT,
            self.m_buckets[entry_index] - TupleTableFullIndex.BUCKET_OFFSET,
        )
        self.m_entry_manager.set_entry_component(
            entry, _EntryManager.ENTRY_HASH_CODE, hash_code
        )
        self.m_entry_manager.set_entry_component(
            entry, _EntryManager.ENTRY_TUPLE_INDEX, tentative_tuple_index
        )
        self.m_buckets[entry_index] = entry + TupleTableFullIndex.BUCKET_OFFSET
        self.m_number_of_tuples += 1
        if self.m_number_of_tuples >= self.m_resize_threshold:
            self._resize_buckets()
        return tentative_tuple_index

    def _resize_buckets(self) -> None:
        """Double the bucket array and rehash all entries."""
        new_buckets = [0] * (len(self.m_buckets) * 2)
        for bucket_index in range(len(self.m_buckets) - 1, -1, -1):
            entry = self.m_buckets[bucket_index] - TupleTableFullIndex.BUCKET_OFFSET
            while entry != -1:
                next_entry = self.m_entry_manager.get_entry_component(
                    entry, _EntryManager.ENTRY_NEXT
                )
                new_bucket_index = self._get_bucket_index(
                    self.m_entry_manager.get_entry_component(
                        entry, _EntryManager.ENTRY_HASH_CODE
                    ),
                    len(new_buckets),
                )
                self.m_entry_manager.set_entry_component(
                    entry,
                    _EntryManager.ENTRY_NEXT,
                    new_buckets[new_bucket_index] - TupleTableFullIndex.BUCKET_OFFSET,
                )
                new_buckets[new_bucket_index] = entry + TupleTableFullIndex.BUCKET_OFFSET
                entry = next_entry
        self.m_buckets = new_buckets
        self.m_resize_threshold = int(len(new_buckets) * TupleTableFullIndex.LOAD_FACTOR)

    def get_tuple_index(self, tup: list[object]) -> int:
        """Look up a tuple by its values. Returns -1 if not found."""
        hash_code = self._get_tuple_hash_code(tup)
        entry_index = self._get_bucket_index(hash_code, len(self.m_buckets))
        entry = self.m_buckets[entry_index] - TupleTableFullIndex.BUCKET_OFFSET
        while entry != -1:
            if hash_code == self.m_entry_manager.get_entry_component(
                entry, _EntryManager.ENTRY_HASH_CODE
            ):
                tuple_index = self.m_entry_manager.get_entry_component(
                    entry, _EntryManager.ENTRY_TUPLE_INDEX
                )
                if self.m_tuple_table.tuple_equals(tup, tuple_index, self.m_indexed_arity):
                    return tuple_index
            entry = self.m_entry_manager.get_entry_component(
                entry, _EntryManager.ENTRY_NEXT
            )
        return -1

    def get_tuple_index_with_positions(
        self, tuple_buffer: list[object], position_indexes: list[int]
    ) -> int:
        """Look up a tuple using specific positions from a buffer."""
        hash_code = self._get_tuple_hash_code_with_positions(
            tuple_buffer, position_indexes
        )
        entry_index = self._get_bucket_index(hash_code, len(self.m_buckets))
        entry = self.m_buckets[entry_index] - TupleTableFullIndex.BUCKET_OFFSET
        while entry != -1:
            if hash_code == self.m_entry_manager.get_entry_component(
                entry, _EntryManager.ENTRY_HASH_CODE
            ):
                tuple_index = self.m_entry_manager.get_entry_component(
                    entry, _EntryManager.ENTRY_TUPLE_INDEX
                )
                if self.m_tuple_table.tuple_equals_with_positions(
                    tuple_buffer, position_indexes, tuple_index, self.m_indexed_arity
                ):
                    return tuple_index
            entry = self.m_entry_manager.get_entry_component(
                entry, _EntryManager.ENTRY_NEXT
            )
        return -1

    def remove_tuple(self, tuple_index: int) -> bool:
        """Remove a tuple by its index. Returns True if found and removed."""
        hash_code = 0
        for i in range(self.m_indexed_arity):
            obj = self.m_tuple_table.get_tuple_object(tuple_index, i)
            if obj is not None:
                hash_code += hash(obj)
        last_entry = -1
        entry_index = self._get_bucket_index(hash_code, len(self.m_buckets))
        entry = self.m_buckets[entry_index] - TupleTableFullIndex.BUCKET_OFFSET
        while entry != -1:
            next_entry = self.m_entry_manager.get_entry_component(
                entry, _EntryManager.ENTRY_NEXT
            )
            if (
                hash_code
                == self.m_entry_manager.get_entry_component(
                    entry, _EntryManager.ENTRY_HASH_CODE
                )
                and tuple_index
                == self.m_entry_manager.get_entry_component(
                    entry, _EntryManager.ENTRY_TUPLE_INDEX
                )
            ):
                if last_entry == -1:
                    self.m_buckets[entry_index] = (
                        next_entry + TupleTableFullIndex.BUCKET_OFFSET
                    )
                else:
                    self.m_entry_manager.set_entry_component(
                        last_entry, _EntryManager.ENTRY_NEXT, next_entry
                    )
                return True
            last_entry = entry
            entry = next_entry
        return False

    def _get_tuple_hash_code(self, tup: list[object]) -> int:
        """Compute hash code for a full tuple."""
        hash_code = 0
        for i in range(self.m_indexed_arity):
            hash_code += hash(tup[i])
        return hash_code

    def _get_tuple_hash_code_with_positions(
        self, tuple_buffer: list[object], position_indexes: list[int]
    ) -> int:
        """Compute hash code using specific positions from a buffer."""
        hash_code = 0
        for i in range(self.m_indexed_arity):
            hash_code += hash(tuple_buffer[position_indexes[i]])
        return hash_code

    @staticmethod
    def _get_bucket_index(hash_code: int, buckets_length: int) -> int:
        """Compute bucket index (buckets_length must be a power of two minus one pattern)."""
        return hash_code & (buckets_length - 1)


class _EntryManager:
    """Manages hash table entries stored as flat int arrays."""

    ENTRY_SIZE = 3
    ENTRY_NEXT = 0
    ENTRY_HASH_CODE = 1
    ENTRY_TUPLE_INDEX = 2
    ENTRY_PAGE_SIZE = 512

    def __init__(self) -> None:
        self.m_entries: list[int] = []
        self.m_first_free_entry = 0
        self.clear()

    def size(self) -> int:
        """Estimate memory usage."""
        return len(self.m_entries) * 4

    def clear(self) -> None:
        """Reset the entry pool."""
        self.m_entries = [0] * (_EntryManager.ENTRY_SIZE * _EntryManager.ENTRY_PAGE_SIZE)
        self.m_first_free_entry = 0
        self.m_entries[self.m_first_free_entry + _EntryManager.ENTRY_NEXT] = -1

    def get_entry_component(self, entry: int, component: int) -> int:
        """Get an int component from an entry."""
        return self.m_entries[entry + component]

    def set_entry_component(self, entry: int, component: int, value: int) -> None:
        """Set an int component on an entry."""
        self.m_entries[entry + component] = value

    def new_entry(self) -> int:
        """Allocate a new entry."""
        result = self.m_first_free_entry
        next_free_entry = self.m_entries[
            self.m_first_free_entry + _EntryManager.ENTRY_NEXT
        ]
        if next_free_entry == -1:
            self.m_first_free_entry += _EntryManager.ENTRY_SIZE
            if self.m_first_free_entry >= len(self.m_entries):
                new_entries = [0] * (
                    len(self.m_entries) + _EntryManager.ENTRY_SIZE * _EntryManager.ENTRY_PAGE_SIZE
                )
                new_entries[: len(self.m_entries)] = self.m_entries
                self.m_entries = new_entries
            self.m_entries[
                self.m_first_free_entry + _EntryManager.ENTRY_NEXT
            ] = -1
        else:
            self.m_first_free_entry = next_free_entry
        return result

    def delete_entry(self, entry: int) -> None:
        """Return an entry to the free pool."""
        self.m_entries[entry + _EntryManager.ENTRY_NEXT] = self.m_first_free_entry
        self.m_first_free_entry = entry
