"""Cache for blocking signatures.

Faithful port of ``org.semanticweb.HermiT.blocking.BlockingSignatureCache``
from the Java HermiT OWL reasoner.

Classes
-------
BlockingSignatureCache
    Hash-based cache of blocking signatures keyed by hash code from a
    ``DirectBlockingChecker``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.tableau import Node

    from .direct_blocking_checker import DirectBlockingChecker

from .blocking_signature import BlockingSignature


class BlockingSignatureCache:
    """Hash-based cache of blocking signatures.

    Stores signatures produced by a ``DirectBlockingChecker`` and supports
    fast ``contains_signature`` queries.
    """

    __slots__ = (
        "m_direct_blocking_checker",
        "m_buckets",
        "m_number_of_elements",
        "m_threshold",
    )

    def __init__(self, direct_blocking_checker: DirectBlockingChecker) -> None:
        self.m_direct_blocking_checker = direct_blocking_checker
        self.m_buckets: list[BlockingSignature | None] = [None] * 1024
        self.m_threshold = int(len(self.m_buckets) * 0.75)
        self.m_number_of_elements = 0

    def is_empty(self) -> bool:
        """Return ``True`` if the cache contains no signatures."""
        return self.m_number_of_elements == 0

    def add_node(self, node: Node) -> bool:
        """Add the blocking signature for *node*.

        Returns ``True`` if the signature was not already present.
        """
        hash_code = self.m_direct_blocking_checker.blocking_hash_code(node)
        bucket_index = self._get_index_for(hash_code, len(self.m_buckets))
        entry = self.m_buckets[bucket_index]
        while entry is not None:
            if hash_code == hash(entry) and entry.blocks_node(node):
                return False
            entry = entry.next_entry

        entry = self.m_direct_blocking_checker.get_blocking_signature_for(node)
        entry.next_entry = self.m_buckets[bucket_index]
        self.m_buckets[bucket_index] = entry
        self.m_number_of_elements += 1
        if self.m_number_of_elements >= self.m_threshold:
            self._resize(len(self.m_buckets) * 2)
        return True

    def contains_signature(self, node: Node) -> bool:
        """Return ``True`` if a signature blocking *node* is cached."""
        if self.m_direct_blocking_checker.can_be_blocked(node):
            hash_code = self.m_direct_blocking_checker.blocking_hash_code(node)
            bucket_index = self._get_index_for(hash_code, len(self.m_buckets))
            entry = self.m_buckets[bucket_index]
            while entry is not None:
                if hash_code == hash(entry) and entry.blocks_node(node):
                    return True
                entry = entry.next_entry
        return False

    # -- internal helpers --------------------------------------------------

    def _resize(self, new_capacity: int) -> None:
        new_buckets: list[BlockingSignature | None] = [None] * new_capacity
        for i in range(len(self.m_buckets)):
            entry = self.m_buckets[i]
            while entry is not None:
                next_entry = entry.next_entry
                new_index = self._get_index_for(hash(entry), new_capacity)
                entry.next_entry = new_buckets[new_index]
                new_buckets[new_index] = entry
                entry = next_entry
        self.m_buckets = new_buckets
        self.m_threshold = int(new_capacity * 0.75)

    @staticmethod
    def _get_index_for(hash_code: int, table_length: int) -> int:
        hash_code += ~(hash_code << 9)
        hash_code ^= (hash_code >> 14)
        hash_code += (hash_code << 4)
        hash_code ^= (hash_code >> 10)
        return hash_code & (table_length - 1)
