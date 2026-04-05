"""Atomic concept element storing known and possible instances.

Faithful port of ``org.semanticweb.HermiT.hierarchy.AtomicConceptElement``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.model import Individual


class AtomicConceptElement:
    """Stores known and possible instance individuals for a concept.

    This class is used by the instance manager to track which individuals
    are definitely instances (known) and which might be instances (possible)
    of a given atomic concept.
    """

    def __init__(
        self,
        known: set[Individual] | None,
        possible: set[Individual] | None,
    ) -> None:
        self.m_known_instances: set[Individual] = (
            set() if known is None else known
        )
        self.m_possible_instances: set[Individual] = (
            set() if possible is None else possible
        )

    def is_known(self, individual: Individual) -> bool:
        return individual in self.m_known_instances

    def is_possible(self, individual: Individual) -> bool:
        return individual in self.m_possible_instances

    def get_known_instances(self) -> set[Individual]:
        return self.m_known_instances

    def get_possible_instances(self) -> set[Individual]:
        return self.m_possible_instances

    def has_possibles(self) -> bool:
        return bool(self.m_possible_instances)

    def set_to_known(self, individual: Individual) -> None:
        self.m_possible_instances.discard(individual)
        self.m_known_instances.add(individual)

    def add_possible(self, individual: Individual) -> bool:
        was_added = individual not in self.m_possible_instances
        self.m_possible_instances.add(individual)
        return was_added

    def add_possibles(self, individuals: set[Individual]) -> bool:
        new_items = individuals - self.m_possible_instances
        self.m_possible_instances.update(individuals)
        return bool(new_items)

    def __str__(self) -> str:
        parts: list[str] = [" (known instances: "]
        not_first = False
        for individual in self.m_known_instances:
            if not_first:
                parts.append(", ")
            not_first = True
            parts.append(str(individual))
        parts.append(" | possible instances: ")
        not_first = False
        for individual in self.m_possible_instances:
            if not_first:
                parts.append(", ")
            not_first = True
            parts.append(str(individual))
        parts.append(") ")
        return "".join(parts)
