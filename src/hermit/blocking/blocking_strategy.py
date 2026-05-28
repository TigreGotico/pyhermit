"""Blocking strategy interface for tableau termination.

Faithful port of ``org.semanticweb.HermiT.blocking.BlockingStrategy`` from
the Java HermiT OWL reasoner.

Classes
-------
BlockingStrategy
    Protocol-like abstract base class defining the blocking strategy interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.model import AtomicConcept, AtomicRole, DLClause, DataRange, Variable
    from hermit.tableau import Node, Tableau, Worker


class BlockingStrategy(ABC):
    """Abstract interface for tableau blocking strategies.

    A blocking strategy determines when a node in the tableau should stop
    expanding because its state is "blocked" by another node with an equivalent
    or more general label.
    """

    __slots__ = ()

    @abstractmethod
    def initialize(self, tableau: Tableau) -> None:
        """Initialize the strategy with the given *tableau*."""
        ...

    @abstractmethod
    def additional_dl_ontology_set(self, additional_dl_ontology: object) -> None:
        """Called when an additional DL ontology has been set."""
        ...

    @abstractmethod
    def additional_dl_ontology_cleared(self) -> None:
        """Called when the additional DL ontology has been cleared."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all internal state."""
        ...

    @abstractmethod
    def compute_blocking(self, final_chance: bool) -> None:
        """Compute blocking for all active nodes.

        Parameters
        ----------
        final_chance:
            ``True`` if this is the last opportunity to compute blocking
            before model construction.
        """
        ...

    @abstractmethod
    def is_permanent_assertion(self, concept_or_range: AtomicConcept | DataRange, node: Node) -> bool:
        """Return ``True`` if the assertion is permanent for *node*."""
        ...

    @abstractmethod
    def assertion_added(self, concept_or_range: AtomicConcept | DataRange | AtomicRole,
                        node_or_from: Node, node_to_or_is_core: Node | bool,
                        is_core: bool | None = None) -> None:
        """Called when an assertion has been added.

        Overloaded for concept/data-range assertions (two positional args plus
        *is_core*) and role assertions (three positional args).
        """
        ...

    @abstractmethod
    def assertion_core_set(self, concept_or_range: AtomicConcept | DataRange | AtomicRole,
                           node_or_from: Node, node_to: Node | None = None) -> None:
        """Called when the core status of an assertion has been set."""
        ...

    @abstractmethod
    def assertion_removed(self, concept_or_range: AtomicConcept | DataRange | AtomicRole,
                          node_or_from: Node, node_to_or_is_core: Node | bool,
                          is_core: bool | None = None) -> None:
        """Called when an assertion has been removed."""
        ...

    @abstractmethod
    def nodes_merged(self, merge_from: Node, merge_into: Node) -> None:
        """Called when two nodes have been merged."""
        ...

    @abstractmethod
    def nodes_unmerged(self, merge_from: Node, merge_into: Node) -> None:
        """Called when two nodes have been unmerged."""
        ...

    @abstractmethod
    def node_status_changed(self, node: Node) -> None:
        """Called when the status of *node* has changed."""
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
    def model_found(self) -> None:
        """Called when a model has been found."""
        ...

    @abstractmethod
    def is_exact(self) -> bool:
        """Return ``True`` if this blocking strategy is exact."""
        ...

    @abstractmethod
    def dl_clause_body_compiled(
        self,
        workers: list[Worker],
        dl_clause: DLClause,
        variables: list[Variable],
        values_buffer: list[object],
        core_variables: list[bool],
    ) -> None:
        """Called when a DL clause body has been compiled.

        Parameters
        ----------
        workers:
            List to which worker objects may be appended.
        dl_clause:
            The compiled clause.
        variables:
            Variables in the clause.
        values_buffer:
            Buffer for values.
        core_variables:
            Mutable list of booleans indicating core variables.
        """
        ...
