"""Tuple table -- flat storage for tuples of objects.

The actual implementation of the tuple tables used in the ExtensionTable
class. Uses paged arrays for efficient memory reuse during backtracking.
"""

from __future__ import annotations


class TupleTable:
    """Paged flat table storing tuples as lists of objects.

    Uses pages of fixed size (power of two) for efficient memory management.
    During backtracking, tuples are not physically removed -- the pointer
    to the first free tuple index is simply reset.
    """

    PAGE_SIZE = 512  # Must be a power of two!

    __slots__ = ("m_arity", "m_pages", "m_number_of_pages", "m_tuple_capacity", "m_first_free_tuple_index")

    def __init__(self, arity: int) -> None:
        self.m_arity = arity
        self.m_pages: list[list[object | None] | None] = []
        self.m_number_of_pages = 0
        self.m_tuple_capacity = 0
        self.m_first_free_tuple_index = 0
        self.clear()

    def size_in_memory(self) -> int:
        """Estimate memory usage in bytes (approximate)."""
        size = len(self.m_pages) * 4
        for i in range(len(self.m_pages) - 1, -1, -1):
            page = self.m_pages[i]
            if page is not None:
                size += len(page) * 4
        return size

    @property
    def first_free_tuple_index(self) -> int:
        """Return the index of the first free tuple slot."""
        return self.m_first_free_tuple_index

    def add_tuple(self, tuple_buffer: list[object]) -> int:
        """Append *tuple_buffer* and return the tuple index."""
        new_tuple_index = self.m_first_free_tuple_index
        if new_tuple_index == self.m_tuple_capacity:
            if self.m_number_of_pages == len(self.m_pages):
                new_pages: list[list[object | None] | None] = [None] * (
                    self.m_number_of_pages * 3 // 2
                )
                new_pages[: self.m_number_of_pages] = self.m_pages[: self.m_number_of_pages]
                self.m_pages = new_pages
            self.m_pages[self.m_number_of_pages] = [None] * (
                self.m_arity * TupleTable.PAGE_SIZE
            )
            self.m_number_of_pages += 1
            self.m_tuple_capacity += TupleTable.PAGE_SIZE
        page = self.m_pages[new_tuple_index // TupleTable.PAGE_SIZE]
        assert page is not None
        start = (new_tuple_index % TupleTable.PAGE_SIZE) * self.m_arity
        for i, elem in enumerate(tuple_buffer):
            page[start + i] = elem
        self.m_first_free_tuple_index += 1
        return new_tuple_index

    def tuple_equals(
        self, tuple_buffer: list[object], tuple_index: int, compare_length: int
    ) -> bool:
        """Check if the stored tuple matches *tuple_buffer* up to *compare_length*."""
        page = self.m_pages[tuple_index // TupleTable.PAGE_SIZE]
        assert page is not None
        start = (tuple_index % TupleTable.PAGE_SIZE) * self.m_arity
        for i in range(compare_length - 1, -1, -1):
            if tuple_buffer[i] != page[start + i]:
                return False
        return True

    def tuple_equals_with_positions(
        self,
        tuple_buffer: list[object],
        position_indexes: list[int],
        tuple_index: int,
        compare_length: int,
    ) -> bool:
        """Check tuple equality using explicit position indexes."""
        page = self.m_pages[tuple_index // TupleTable.PAGE_SIZE]
        assert page is not None
        start = (tuple_index % TupleTable.PAGE_SIZE) * self.m_arity
        for i in range(compare_length - 1, -1, -1):
            if tuple_buffer[position_indexes[i]] != page[start + i]:
                return False
        return True

    def retrieve_tuple(self, tuple_buffer: list[object | None], tuple_index: int) -> None:
        """Copy the tuple at *tuple_index* into *tuple_buffer*."""
        page = self.m_pages[tuple_index // TupleTable.PAGE_SIZE]
        assert page is not None
        start = (tuple_index % TupleTable.PAGE_SIZE) * self.m_arity
        for i in range(len(tuple_buffer)):
            tuple_buffer[i] = page[start + i]

    def get_tuple_object(self, tuple_index: int, object_index: int) -> object | None:
        """Return the object at the given position in the tuple."""
        assert object_index < self.m_arity
        page = self.m_pages[tuple_index // TupleTable.PAGE_SIZE]
        assert page is not None
        return page[(tuple_index % TupleTable.PAGE_SIZE) * self.m_arity + object_index]

    def set_tuple_object(
        self, tuple_index: int, object_index: int, obj: object | None
    ) -> None:
        """Set the object at the given position in the tuple."""
        page = self.m_pages[tuple_index // TupleTable.PAGE_SIZE]
        assert page is not None
        page[(tuple_index % TupleTable.PAGE_SIZE) * self.m_arity + object_index] = obj

    def truncate(self, new_first_free_tuple_index: int) -> None:
        """Truncate the table to the given size (for backtracking)."""
        self.m_first_free_tuple_index = new_first_free_tuple_index

    def nullify_tuple(self, tuple_index: int) -> None:
        """Nullify all objects in the tuple at *tuple_index*."""
        page = self.m_pages[tuple_index // TupleTable.PAGE_SIZE]
        assert page is not None
        start = (tuple_index % TupleTable.PAGE_SIZE) * self.m_arity
        for i in range(self.m_arity):
            page[start + i] = None

    def clear(self) -> None:
        """Clear the table and reset all state."""
        self.m_pages = [None] * 10
        self.m_number_of_pages = 1
        self.m_pages[0] = [None] * (self.m_arity * TupleTable.PAGE_SIZE)
        self.m_tuple_capacity = self.m_number_of_pages * TupleTable.PAGE_SIZE
        self.m_first_free_tuple_index = 0
