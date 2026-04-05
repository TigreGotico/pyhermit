"""Direct blocking checker interface.

Faithful port of ``org.semanticweb.HermiT.blocking.DirectBlockingChecker``
from the Java HermiT OWL reasoner.

Classes
-------
DirectBlockingChecker
    Protocol-like abstract base class defining the direct blocking checker
    interface used by blocking strategies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.model import AtomicRole, Concept, DataRange

    from hermit.blocking.blocking_signature import BlockingSignature
    from hermit.tableau import Node, Tableau


class DirectBlockingChecker(ABC):
    """Abstract interface for direct blocking checks.

    A direct blocking checker determines whether one node directly blocks
    another based on their labels (concepts, roles, etc.).
    """

    __slots__ = ()

    @abstractmethod
    def initialize(self, tableau: Tableau) -> None:
        """Initialize the checker with the given *tableau*."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all internal state."""
        ...

    @abstractmethod
    def is_blocked_by(self, blocker: Node, blocked: Node) -> bool:
        """Return ``True`` if *blocker* directly blocks *blocked*."""
        ...

    @abstractmethod
    def blocking_hash_code(self, node: Node) -> int:
        """Return a hash code for *node* suitable for blocking lookups."""
        ...

    @abstractmethod
    def can_be_blocker(self, node: Node) -> bool:
        """Return ``True`` if *node* can serve as a blocker."""
        ...

    @abstractmethod
    def can_be_blocked(self, node: Node) -> bool:
        """Return ``True`` if *node* can be blocked."""
        ...

    @abstractmethod
    def has_blocking_info_changed(self, node: Node) -> bool:
        """Return ``True`` if the blocking info for *node* has changed."""
        ...

    @abstractmethod
    def clear_blocking_info_changed(self, node: Node) -> None:
        """Clear the changed flag for *node*."""
        ...

    @abstractmethod
    def has_changed_since_validation(self, node: Node) -> bool:
        """Return ``True`` if *node* has changed since last validation."""
        ...

    @abstractmethod
    def set_has_changed_since_validation(self, node: Node, has_changed: bool) -> None:
        """Set the changed-since-validation flag for *node*."""
        ...

    @abstractmethod
    def node_initialized(self, node: Node) -> None:
        """Called when *node* has been initialized."""
        ...

    @abstractmethod
    def node_destroyed(self, node: Node) -> None:
        """Called when *node* has been destroyed."""
        ...

    @abstractmethod
    def assertion_added(self, concept: Concept, node: Node, is_core: bool) -> Node | None:
        """Called when a concept assertion was added to *node*.

        Returns the node whose blocking info changed, or ``None``.
        """
        ...

    @abstractmethod
    def assertion_removed(self, concept: Concept, node: Node, is_core: bool) -> Node | None:
        """Called when a concept assertion was removed from *node*.

        Returns the node whose blocking info changed, or ``None``.
        """
        ...

    @abstractmethod
    def assertion_added_dr(self, data_range: DataRange, node: Node, is_core: bool) -> Node | None:
        """Called when a data-range assertion was added to *node*.

        Returns the node whose blocking info changed, or ``None``.
        """
        ...

    @abstractmethod
    def assertion_removed_dr(self, data_range: DataRange, node: Node, is_core: bool) -> Node | None:
        """Called when a data-range assertion was removed from *node*.

        Returns the node whose blocking info changed, or ``None``.
        """
        ...

    @abstractmethod
    def assertion_added_role(
        self, atomic_role: AtomicRole, node_from: Node, node_to: Node, is_core: bool
    ) -> Node | None:
        """Called when a role assertion was added.

        Returns the node whose blocking info changed, or ``None``.
        """
        ...

    @abstractmethod
    def assertion_removed_role(
        self, atomic_role: AtomicRole, node_from: Node, node_to: Node, is_core: bool
    ) -> Node | None:
        """Called when a role assertion was removed.

        Returns the node whose blocking info changed, or ``None``.
        """
        ...

    @abstractmethod
    def nodes_merged(self, merge_from: Node, merge_into: Node) -> Node | None:
        """Called when two nodes were merged.

        Returns the node whose blocking info changed, or ``None``.
        """
        ...

    @abstractmethod
    def nodes_unmerged(self, merge_from: Node, merge_into: Node) -> Node | None:
        """Called when two nodes were unmerged.

        Returns the node whose blocking info changed, or ``None``.
        """
        ...

    @abstractmethod
    def get_blocking_signature_for(self, node: Node) -> BlockingSignature:
        """Return a blocking signature for *node* suitable for caching."""
        ...
