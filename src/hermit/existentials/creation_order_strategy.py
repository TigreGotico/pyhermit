"""Creation order strategy for existential expansion.

Strategy for expanding all existentials on the oldest node in the tableau
with unexpanded existentials. This usually closely approximates a breadth-first
expansion. (Existentials introduced onto parent nodes as a result of constraints
on their children can produce newer nodes of lower depth than older nodes,
which could result in slight non-breadth-first behavior.)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hermit.existentials.abstract_expansion_strategy import AbstractExpansionStrategy

if TYPE_CHECKING:
    from hermit.blocking.blocking_strategy import BlockingStrategy
    from hermit.model import AtLeast
    from hermit.tableau.node import Node


class CreationOrderStrategy(AbstractExpansionStrategy):
    """Breadth-first-style existential expansion ordered by node creation time."""

    def __init__(self, strategy: BlockingStrategy) -> None:
        super().__init__(strategy, True)

    def is_deterministic(self) -> bool:
        return True

    def _expand_existential(self, at_least: AtLeast, for_node: Node) -> None:
        self.m_existential_expansion_manager.expand(at_least, for_node)  # type: ignore[union-attr]
        self.m_existential_expansion_manager.mark_existential_processed(  # type: ignore[union-attr]
            at_least, for_node
        )
