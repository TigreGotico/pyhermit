"""Tuple index -- trie-based index for fast tuple lookup.

Implements a prefix tree (trie) over tuple components to enable
O(k) lookup of tuples by their indexed positions.
"""

from __future__ import annotations


class TupleIndex:
    """Trie-based index for fast tuple retrieval.

    The index is built over a subset of tuple positions specified by
    *indexing_sequence*. It supports add, lookup, and removal of tuples.
    """

    LOAD_FACTOR = 0.7
    BUCKET_OFFSET = 1

    # Trie node component indices
    TRIE_NODE_PARENT = 0
    TRIE_NODE_FIRST_CHILD = 1
    TRIE_NODE_TUPLE_INDEX = 1
    TRIE_NODE_PREVIOUS_SIBLING = 2
    TRIE_NODE_NEXT_SIBLING = 3
    TRIE_NODE_NEXT_ENTRY = 4
    TRIE_NODE_SIZE = 5
    TRIE_NODE_PAGE_SIZE = 1024

    def __init__(self, indexing_sequence: list[int]) -> None:
        self.m_indexing_sequence = indexing_sequence
        self.m_trie_node_manager = _TrieNodeManager()
        self.m_root = 0
        self.m_buckets: list[int] = []
        self.m_buckets_length_minus_one = 0
        self.m_resize_threshold = 0
        self.m_number_of_nodes = 0
        self.clear()

    def size_in_memory(self) -> int:
        """Estimate memory usage."""
        size = len(self.m_buckets) * 4 + self.m_trie_node_manager.size()
        return size

    @property
    def indexing_sequence(self) -> list[int]:
        """Return the sequence of tuple positions used for indexing."""
        return self.m_indexing_sequence

    def clear(self) -> None:
        """Clear the index and reset to initial state."""
        self.m_trie_node_manager.clear()
        self.m_root = self.m_trie_node_manager.new_trie_node()
        self.m_trie_node_manager.initialize_trie_node(
            self.m_root, -1, -1, -1, -1, -1, None
        )
        self.m_buckets = [0] * 16
        self.m_buckets_length_minus_one = len(self.m_buckets) - 1
        self.m_resize_threshold = int(len(self.m_buckets) * TupleIndex.LOAD_FACTOR)
        self.m_number_of_nodes = 0

    def add_tuple(self, tup: list[object], potential_tuple_index: int) -> int:
        """Add a tuple to the index.

        Returns the existing tuple index if the tuple was already present,
        otherwise returns *potential_tuple_index*.
        """
        trie_node = self.m_root
        for position in self.m_indexing_sequence:
            obj = tup[position]
            trie_node = self._get_child_node_add_if_necessary(trie_node, obj)
        if self.m_trie_node_manager.get_trie_node_component(
            trie_node, TupleIndex.TRIE_NODE_TUPLE_INDEX
        ) == -1:
            self.m_trie_node_manager.set_trie_node_component(
                trie_node, TupleIndex.TRIE_NODE_TUPLE_INDEX, potential_tuple_index
            )
            return potential_tuple_index
        return self.m_trie_node_manager.get_trie_node_component(
            trie_node, TupleIndex.TRIE_NODE_TUPLE_INDEX
        )

    def get_tuple_index(self, tup: list[object]) -> int:
        """Look up the tuple index for *tup*, or -1 if not found."""
        trie_node = self.m_root
        for position in self.m_indexing_sequence:
            obj = tup[position]
            trie_node = self._get_child_node(trie_node, obj)
            if trie_node == -1:
                return -1
        return self.m_trie_node_manager.get_trie_node_component(
            trie_node, TupleIndex.TRIE_NODE_TUPLE_INDEX
        )

    def remove_tuple(self, tup: list[object]) -> int:
        """Remove a tuple from the index.

        Returns the tuple index that was removed, or -1 if not found.
        """
        leaf_trie_node = self.m_root
        for position in self.m_indexing_sequence:
            obj = tup[position]
            leaf_trie_node = self._get_child_node(leaf_trie_node, obj)
            if leaf_trie_node == -1:
                return -1
        tuple_index = self.m_trie_node_manager.get_trie_node_component(
            leaf_trie_node, TupleIndex.TRIE_NODE_TUPLE_INDEX
        )
        trie_node = self.m_trie_node_manager.get_trie_node_component(
            leaf_trie_node, TupleIndex.TRIE_NODE_PARENT
        )
        self._remove_trie_node(leaf_trie_node)
        while (
            trie_node != self.m_root
            and self.m_trie_node_manager.get_trie_node_component(
                trie_node, TupleIndex.TRIE_NODE_FIRST_CHILD
            )
            == -1
        ):
            parent_trie_node = self.m_trie_node_manager.get_trie_node_component(
                trie_node, TupleIndex.TRIE_NODE_PARENT
            )
            self._remove_trie_node(trie_node)
            trie_node = parent_trie_node
        return tuple_index

    def _remove_trie_node(self, trie_node: int) -> None:
        """Remove a trie node from the structure."""
        obj = self.m_trie_node_manager.get_trie_node_object(trie_node)
        parent = self.m_trie_node_manager.get_trie_node_component(
            trie_node, TupleIndex.TRIE_NODE_PARENT
        )
        bucket_index = TupleIndex._get_index_for(
            hash(obj) + parent, self.m_buckets_length_minus_one
        )
        child = self.m_buckets[bucket_index] - TupleIndex.BUCKET_OFFSET
        previous_child = -1
        while child != -1:
            next_child = self.m_trie_node_manager.get_trie_node_component(
                child, TupleIndex.TRIE_NODE_NEXT_ENTRY
            )
            if child == trie_node:
                self.m_number_of_nodes -= 1
                previous_sibling = self.m_trie_node_manager.get_trie_node_component(
                    trie_node, TupleIndex.TRIE_NODE_PREVIOUS_SIBLING
                )
                next_sibling = self.m_trie_node_manager.get_trie_node_component(
                    trie_node, TupleIndex.TRIE_NODE_NEXT_SIBLING
                )
                if previous_sibling == -1:
                    self.m_trie_node_manager.set_trie_node_component(
                        parent, TupleIndex.TRIE_NODE_FIRST_CHILD, next_sibling
                    )
                else:
                    self.m_trie_node_manager.set_trie_node_component(
                        previous_sibling, TupleIndex.TRIE_NODE_NEXT_SIBLING, next_sibling
                    )
                if next_sibling != -1:
                    self.m_trie_node_manager.set_trie_node_component(
                        next_sibling,
                        TupleIndex.TRIE_NODE_PREVIOUS_SIBLING,
                        previous_sibling,
                    )
                if previous_child == -1:
                    self.m_buckets[bucket_index] = next_child + TupleIndex.BUCKET_OFFSET
                else:
                    self.m_trie_node_manager.set_trie_node_component(
                        previous_child, TupleIndex.TRIE_NODE_NEXT_ENTRY, next_child
                    )
                self.m_trie_node_manager.delete_trie_node(trie_node)
                return
            previous_child = child
            child = next_child
        raise RuntimeError("Internal error: should be able to remove the child node.")

    def _get_child_node(self, parent: int, obj: object) -> int:
        """Look up a child node by parent and object key."""
        bucket_index = TupleIndex._get_index_for(
            hash(obj) + parent, self.m_buckets_length_minus_one
        )
        child = self.m_buckets[bucket_index] - TupleIndex.BUCKET_OFFSET
        while child != -1:
            if parent == self.m_trie_node_manager.get_trie_node_component(
                child, TupleIndex.TRIE_NODE_PARENT
            ) and obj == self.m_trie_node_manager.get_trie_node_object(child):
                return child
            child = self.m_trie_node_manager.get_trie_node_component(
                child, TupleIndex.TRIE_NODE_NEXT_ENTRY
            )
        return -1

    def _get_child_node_add_if_necessary(self, parent: int, obj: object) -> int:
        """Look up or create a child node."""
        hash_code = hash(obj) + parent
        bucket_index = TupleIndex._get_index_for(
            hash_code, self.m_buckets_length_minus_one
        )
        child = self.m_buckets[bucket_index] - TupleIndex.BUCKET_OFFSET
        while child != -1:
            if parent == self.m_trie_node_manager.get_trie_node_component(
                child, TupleIndex.TRIE_NODE_PARENT
            ) and obj == self.m_trie_node_manager.get_trie_node_object(child):
                return child
            child = self.m_trie_node_manager.get_trie_node_component(
                child, TupleIndex.TRIE_NODE_NEXT_ENTRY
            )
        if self.m_number_of_nodes >= self.m_resize_threshold:
            self._resize_buckets()
            bucket_index = TupleIndex._get_index_for(
                hash_code, self.m_buckets_length_minus_one
            )
        child = self.m_trie_node_manager.new_trie_node()
        next_sibling = self.m_trie_node_manager.get_trie_node_component(
            parent, TupleIndex.TRIE_NODE_FIRST_CHILD
        )
        if next_sibling != -1:
            self.m_trie_node_manager.set_trie_node_component(
                next_sibling, TupleIndex.TRIE_NODE_PREVIOUS_SIBLING, child
            )
        self.m_trie_node_manager.set_trie_node_component(
            parent, TupleIndex.TRIE_NODE_FIRST_CHILD, child
        )
        self.m_trie_node_manager.initialize_trie_node(
            child,
            parent,
            -1,
            -1,
            next_sibling,
            self.m_buckets[bucket_index] - TupleIndex.BUCKET_OFFSET,
            obj,
        )
        self.m_buckets[bucket_index] = child + TupleIndex.BUCKET_OFFSET
        self.m_number_of_nodes += 1
        return child

    def _resize_buckets(self) -> None:
        """Double the hash bucket array and rehash all entries."""
        if self.m_buckets_length_minus_one + 1 == 0x40000000:
            self.m_resize_threshold = 2**31 - 1
        else:
            new_buckets = [0] * (len(self.m_buckets) * 2)
            new_buckets_length_minus_one = len(new_buckets) - 1
            for bucket_index in range(self.m_buckets_length_minus_one, -1, -1):
                trie_node = self.m_buckets[bucket_index] - TupleIndex.BUCKET_OFFSET
                while trie_node != -1:
                    next_trie_node = self.m_trie_node_manager.get_trie_node_component(
                        trie_node, TupleIndex.TRIE_NODE_NEXT_ENTRY
                    )
                    h = (
                        hash(self.m_trie_node_manager.get_trie_node_object(trie_node))
                        + self.m_trie_node_manager.get_trie_node_component(
                            trie_node, TupleIndex.TRIE_NODE_PARENT
                        )
                    )
                    new_bucket_index = TupleIndex._get_index_for(
                        h, new_buckets_length_minus_one
                    )
                    self.m_trie_node_manager.set_trie_node_component(
                        trie_node,
                        TupleIndex.TRIE_NODE_NEXT_ENTRY,
                        new_buckets[new_bucket_index] - TupleIndex.BUCKET_OFFSET,
                    )
                    new_buckets[new_bucket_index] = trie_node + TupleIndex.BUCKET_OFFSET
                    trie_node = next_trie_node
            self.m_buckets = new_buckets
            self.m_buckets_length_minus_one = new_buckets_length_minus_one
            self.m_resize_threshold = int(
                len(self.m_buckets) * TupleIndex.LOAD_FACTOR
            )

    @staticmethod
    def _get_index_for(hash_code: int, table_length_minus_one: int) -> int:
        """Compute a hash bucket index with additional mixing."""
        hash_code += ~(hash_code << 9)
        hash_code ^= (hash_code >> 14) & 0xFFFFFFFF
        hash_code += (hash_code << 4)
        hash_code ^= (hash_code >> 10) & 0xFFFFFFFF
        return hash_code & table_length_minus_one


class _TrieNodeManager:
    """Manages a pool of trie nodes stored in paged arrays."""

    def __init__(self) -> None:
        self.m_index_pages: list[list[int] | None] = []
        self.m_object_pages: list[list[object | None] | None] = []
        self.m_first_free_trie_node = 0
        self.m_number_of_pages = 0
        self.clear()

    def size(self) -> int:
        """Estimate memory usage."""
        size = len(self.m_index_pages) * 4 + len(self.m_object_pages) * 4
        for i in range(len(self.m_index_pages) - 1, -1, -1):
            if self.m_index_pages[i] is not None:
                size += len(self.m_index_pages[i]) * 4
        for i in range(len(self.m_object_pages) - 1, -1, -1):
            if self.m_object_pages[i] is not None:
                size += len(self.m_object_pages[i]) * 4
        return size

    def clear(self) -> None:
        """Reset the node pool."""
        self.m_index_pages = [None] * 10
        self.m_index_pages[0] = [0] * (
            TupleIndex.TRIE_NODE_SIZE * TupleIndex.TRIE_NODE_PAGE_SIZE
        )
        self.m_object_pages = [None] * 10
        self.m_object_pages[0] = [None] * TupleIndex.TRIE_NODE_PAGE_SIZE
        self.m_number_of_pages = 1
        self.m_first_free_trie_node = 0
        self.set_trie_node_component(
            self.m_first_free_trie_node, TupleIndex.TRIE_NODE_NEXT_SIBLING, -1
        )

    def get_trie_node_component(self, trie_node: int, component: int) -> int:
        """Get an integer component from a trie node."""
        page = self.m_index_pages[trie_node // TupleIndex.TRIE_NODE_PAGE_SIZE]
        assert page is not None
        return page[(trie_node % TupleIndex.TRIE_NODE_PAGE_SIZE) * TupleIndex.TRIE_NODE_SIZE + component]

    def set_trie_node_component(
        self, trie_node: int, component: int, value: int
    ) -> None:
        """Set an integer component on a trie node."""
        page = self.m_index_pages[trie_node // TupleIndex.TRIE_NODE_PAGE_SIZE]
        assert page is not None
        page[(trie_node % TupleIndex.TRIE_NODE_PAGE_SIZE) * TupleIndex.TRIE_NODE_SIZE + component] = value

    def get_trie_node_object(self, trie_node: int) -> object | None:
        """Get the object stored in a trie node."""
        page = self.m_object_pages[trie_node // TupleIndex.TRIE_NODE_PAGE_SIZE]
        assert page is not None
        return page[trie_node % TupleIndex.TRIE_NODE_PAGE_SIZE]

    def set_trie_node_object(
        self, trie_node: int, obj: object | None
    ) -> None:
        """Set the object stored in a trie node."""
        page = self.m_object_pages[trie_node // TupleIndex.TRIE_NODE_PAGE_SIZE]
        assert page is not None
        page[trie_node % TupleIndex.TRIE_NODE_PAGE_SIZE] = obj

    def initialize_trie_node(
        self,
        trie_node: int,
        parent: int,
        first_child: int,
        previous_sibling: int,
        next_sibling: int,
        next_entry: int,
        obj: object | None,
    ) -> None:
        """Initialize all components of a trie node."""
        page_index = trie_node // TupleIndex.TRIE_NODE_PAGE_SIZE
        index_in_page = trie_node % TupleIndex.TRIE_NODE_PAGE_SIZE
        index_page = self.m_index_pages[page_index]
        assert index_page is not None
        start = index_in_page * TupleIndex.TRIE_NODE_SIZE
        index_page[start + TupleIndex.TRIE_NODE_PARENT] = parent
        index_page[start + TupleIndex.TRIE_NODE_FIRST_CHILD] = first_child
        index_page[start + TupleIndex.TRIE_NODE_PREVIOUS_SIBLING] = previous_sibling
        index_page[start + TupleIndex.TRIE_NODE_NEXT_SIBLING] = next_sibling
        index_page[start + TupleIndex.TRIE_NODE_NEXT_ENTRY] = next_entry
        object_page = self.m_object_pages[page_index]
        assert object_page is not None
        object_page[index_in_page] = obj

    def new_trie_node(self) -> int:
        """Allocate a new trie node from the pool."""
        new_trie_node = self.m_first_free_trie_node
        next_free_trie_node = self.get_trie_node_component(
            self.m_first_free_trie_node, TupleIndex.TRIE_NODE_NEXT_SIBLING
        )
        if next_free_trie_node != -1:
            self.m_first_free_trie_node = next_free_trie_node
        else:
            self.m_first_free_trie_node += 1
            if self.m_first_free_trie_node < 0:
                raise MemoryError(
                    "The space of nodes in TupleIndex was exhausted: "
                    "the ontology is just too large."
                )
            page_index = self.m_first_free_trie_node // TupleIndex.TRIE_NODE_PAGE_SIZE
            if page_index >= self.m_number_of_pages:
                if page_index >= len(self.m_index_pages):
                    new_index_pages: list[list[int] | None] = [None] * (
                        len(self.m_index_pages) * 3 // 2
                    )
                    new_index_pages[: len(self.m_index_pages)] = self.m_index_pages[
                        : len(self.m_index_pages)
                    ]
                    self.m_index_pages = new_index_pages
                    new_object_pages: list[list[object | None] | None] = [None] * (
                        len(self.m_object_pages) * 3 // 2
                    )
                    new_object_pages[: len(self.m_object_pages)] = self.m_object_pages[
                        : len(self.m_object_pages)
                    ]
                    self.m_object_pages = new_object_pages
                self.m_index_pages[page_index] = [0] * (
                    TupleIndex.TRIE_NODE_SIZE * TupleIndex.TRIE_NODE_PAGE_SIZE
                )
                self.m_object_pages[page_index] = [None] * TupleIndex.TRIE_NODE_PAGE_SIZE
                self.m_number_of_pages += 1
            self.set_trie_node_component(
                self.m_first_free_trie_node, TupleIndex.TRIE_NODE_NEXT_SIBLING, -1
            )
        return new_trie_node

    def delete_trie_node(self, trie_node: int) -> None:
        """Return a trie node to the free pool."""
        self.set_trie_node_component(
            trie_node, TupleIndex.TRIE_NODE_NEXT_SIBLING, self.m_first_free_trie_node
        )
        self.set_trie_node_object(trie_node, None)
        self.m_first_free_trie_node = trie_node


class TupleIndexRetrieval:
    """Retrieval iterator that walks a TupleIndex trie.

    Used by ExtensionTableWithTupleIndexes for indexed retrievals.
    """

    def __init__(
        self,
        tuple_index: TupleIndex,
        bindings_buffer: list[object | None],
        selection_indices: list[int],
    ) -> None:
        self.m_tuple_index = tuple_index
        self.m_bindings_buffer = bindings_buffer
        self.m_selection_indices = selection_indices
        self.m_selection_indices_length = len(selection_indices)
        self.m_indexing_sequence_length = len(tuple_index.m_indexing_sequence)
        self.m_current_trie_node = 0

    def open(self) -> None:
        """Position the iterator at the first matching tuple."""
        self.m_current_trie_node = self.m_tuple_index.m_root
        for position in range(self.m_selection_indices_length):
            obj = self.m_bindings_buffer[self.m_selection_indices[position]]
            self.m_current_trie_node = self.m_tuple_index._get_child_node(
                self.m_current_trie_node, obj
            )
            if self.m_current_trie_node == -1:
                return
        if (
            self.m_selection_indices_length == 0
            and self.m_tuple_index.m_trie_node_manager.get_trie_node_component(
                self.m_tuple_index.m_root, TupleIndex.TRIE_NODE_FIRST_CHILD
            )
            == -1
        ):
            self.m_current_trie_node = -1
        else:
            for _index in range(
                self.m_selection_indices_length, self.m_indexing_sequence_length
            ):
                self.m_current_trie_node = (
                    self.m_tuple_index.m_trie_node_manager.get_trie_node_component(
                        self.m_current_trie_node, TupleIndex.TRIE_NODE_FIRST_CHILD
                    )
                )

    def after_last(self) -> bool:
        """Return True if past the last matching tuple."""
        return self.m_current_trie_node == -1

    def get_current_tuple_index(self) -> int:
        """Return the tuple index of the current position."""
        return self.m_tuple_index.m_trie_node_manager.get_trie_node_component(
            self.m_current_trie_node, TupleIndex.TRIE_NODE_TUPLE_INDEX
        )

    def next(self) -> None:
        """Advance to the next matching tuple."""
        trie_node_depth = self.m_indexing_sequence_length
        while (
            trie_node_depth != self.m_selection_indices_length
            and self.m_tuple_index.m_trie_node_manager.get_trie_node_component(
                self.m_current_trie_node, TupleIndex.TRIE_NODE_NEXT_SIBLING
            )
            == -1
        ):
            self.m_current_trie_node = (
                self.m_tuple_index.m_trie_node_manager.get_trie_node_component(
                    self.m_current_trie_node, TupleIndex.TRIE_NODE_PARENT
                )
            )
            trie_node_depth -= 1
        if trie_node_depth == self.m_selection_indices_length:
            self.m_current_trie_node = -1
        else:
            self.m_current_trie_node = (
                self.m_tuple_index.m_trie_node_manager.get_trie_node_component(
                    self.m_current_trie_node, TupleIndex.TRIE_NODE_NEXT_SIBLING
                )
            )
            for _index in range(trie_node_depth, self.m_indexing_sequence_length):
                self.m_current_trie_node = (
                    self.m_tuple_index.m_trie_node_manager.get_trie_node_component(
                        self.m_current_trie_node, TupleIndex.TRIE_NODE_FIRST_CHILD
                    )
                )
