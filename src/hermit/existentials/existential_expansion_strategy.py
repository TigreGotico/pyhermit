"""Existential expansion strategy interface.

Strategy objects are responsible for selecting which existentials should be
expanded first, as well as how the new nodes are introduced. The latter is
usually delegated to tableau.ExistentialExpansionManager, but strategies
are free to provide their own node-introduction implementations
(but be careful---it's tough to get right!)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.model import (
        AtomicRole,
        Concept,
        DLClause,
        DataRange,
        Variable,
    )
    from hermit.tableau.dl_clause_evaluator import Worker as DLClauseWorker
    from hermit.tableau.node import Node
    from hermit.tableau.tableau import Tableau


class ExistentialExpansionStrategy(ABC):
    """Interface for strategies that control existential expansion order and node introduction."""

    @abstractmethod
    def initialize(self, tableau: Tableau) -> None:
        """Initialize the strategy with the given tableau."""
        ...

    @abstractmethod
    def additional_dl_ontology_set(self, additional_dl_ontology: object) -> None:
        """Called when an additional DL ontology is set."""
        ...

    @abstractmethod
    def additional_dl_ontology_cleared(self) -> None:
        """Called when the additional DL ontology is cleared."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all state accumulated during the current reasoning run."""
        ...

    @abstractmethod
    def expand_existentials(self, final_chance: bool) -> bool:
        """Expand existentials according to this strategy.

        Args:
            final_chance: Whether this is the last chance to expand.

        Returns:
            True if extensions changed, False otherwise.
        """
        ...

    @abstractmethod
    def assertion_added_concept(
        self, concept: Concept, node: Node, is_core: bool
    ) -> None:
        """Called when a concept assertion is added."""
        ...

    @abstractmethod
    def assertion_added_data_range(
        self, data_range: DataRange, node: Node, is_core: bool
    ) -> None:
        """Called when a data range assertion is added."""
        ...

    @abstractmethod
    def assertion_core_set_concept(self, concept: Concept, node: Node) -> None:
        """Called when a concept assertion is marked as core."""
        ...

    @abstractmethod
    def assertion_core_set_data_range(self, data_range: DataRange, node: Node) -> None:
        """Called when a data range assertion is marked as core."""
        ...

    @abstractmethod
    def assertion_removed_concept(
        self, concept: Concept, node: Node, is_core: bool
    ) -> None:
        """Called when a concept assertion is removed."""
        ...

    @abstractmethod
    def assertion_removed_data_range(
        self, data_range: DataRange, node: Node, is_core: bool
    ) -> None:
        """Called when a data range assertion is removed."""
        ...

    @abstractmethod
    def assertion_added_atomic_role(
        self, atomic_role: AtomicRole, node_from: Node, node_to: Node, is_core: bool
    ) -> None:
        """Called when an atomic role assertion is added."""
        ...

    @abstractmethod
    def assertion_core_set_atomic_role(
        self, atomic_role: AtomicRole, node_from: Node, node_to: Node
    ) -> None:
        """Called when an atomic role assertion is marked as core."""
        ...

    @abstractmethod
    def assertion_removed_atomic_role(
        self, atomic_role: AtomicRole, node_from: Node, node_to: Node, is_core: bool
    ) -> None:
        """Called when an atomic role assertion is removed."""
        ...

    @abstractmethod
    def nodes_merged(self, merge_from: Node, merge_into: Node) -> None:
        """Called when two nodes are merged."""
        ...

    @abstractmethod
    def nodes_unmerged(self, merge_from: Node, merge_into: Node) -> None:
        """Called when a merge between two nodes is undone."""
        ...

    @abstractmethod
    def node_status_changed(self, node: Node) -> None:
        """Called when a node's status changes."""
        ...

    @abstractmethod
    def node_initialized(self, node: Node) -> None:
        """Called when a node is initialized."""
        ...

    @abstractmethod
    def node_destroyed(self, node: Node) -> None:
        """Called when a node is destroyed."""
        ...

    @abstractmethod
    def branching_point_pushed(self) -> None:
        """Called when a branching point is pushed."""
        ...

    @abstractmethod
    def backtrack(self) -> None:
        """Called when backtracking occurs."""
        ...

    @abstractmethod
    def model_found(self) -> None:
        """Called when a model is found."""
        ...

    @abstractmethod
    def is_deterministic(self) -> bool:
        """Return True if the strategy is deterministic."""
        ...

    @abstractmethod
    def is_exact(self) -> bool:
        """Return True if the strategy is exact."""
        ...

    @abstractmethod
    def dl_clause_body_compiled(
        self,
        workers: list[DLClauseWorker],
        dl_clause: DLClause,
        variables: list[Variable],
        values_buffer: list[object | None],
        core_variables: list[bool],
    ) -> None:
        """Called when a DL clause body is compiled."""
        ...
