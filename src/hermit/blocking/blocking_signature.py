"""Blocking signature abstraction for blocking caches.

Faithful port of ``org.semanticweb.HermiT.blocking.BlockingSignature`` from
the Java HermiT OWL reasoner.

Classes
-------
BlockingSignature
    Abstract base class representing a signature that can block a node.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.tableau import Node


class BlockingSignature(ABC):
    """Abstract blocking signature.

    A signature captures the essential properties of a node that are relevant
    for blocking decisions.  Subclasses implement ``blocks_node`` to test
    whether this signature blocks a given node, and provide ``__hash__`` /
    ``__eq__`` for use in hash-based caches.
    """

    __slots__ = ("_next_entry",)

    def __init__(self) -> None:
        self._next_entry: BlockingSignature | None = None

    @property
    def next_entry(self) -> BlockingSignature | None:
        """Return the next entry in the hash-chain, or ``None``."""
        return self._next_entry

    @next_entry.setter
    def next_entry(self, next_entry: BlockingSignature | None) -> None:
        """Set the next entry in the hash-chain."""
        self._next_entry = next_entry

    @abstractmethod
    def blocks_node(self, node: Node) -> bool:
        """Return ``True`` if this signature blocks the given *node*."""
        ...

    @abstractmethod
    def __hash__(self) -> int: ...

    @abstractmethod
    def __eq__(self, other: object) -> bool: ...
