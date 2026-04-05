"""Role element manager for tracking known and possible role instances.

Faithful port of ``org.semanticweb.HermiT.hierarchy.RoleElementManager``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.model import AtomicRole, Individual


class RoleElementManager:
    """Manages role elements that track known and possible role instances."""

    def __init__(self) -> None:
        self.m_role_to_element: dict[AtomicRole, RoleElement] = {}

    def get_role_element(self, role: AtomicRole) -> RoleElement:
        if role in self.m_role_to_element:
            return self.m_role_to_element[role]
        element = RoleElement(role, self)
        self.m_role_to_element[role] = element
        return element

    def __str__(self) -> str:
        import os

        lines: list[str] = []
        for role, element in self.m_role_to_element.items():
            lines.append(f"{role} -> {element}")
        return os.linesep.join(lines)


class RoleElement:
    """Stores known and possible instance pairs for a single atomic role."""

    def __init__(self, role: AtomicRole, manager: RoleElementManager) -> None:
        self.m_role: AtomicRole = role
        self._manager = manager
        self.m_known_relations: dict[Individual, set[Individual]] = {}
        self.m_possible_relations: dict[Individual, set[Individual]] = {}

    def get_role(self) -> AtomicRole:
        return self.m_role

    def is_known(self, individual1: Individual, individual2: Individual) -> bool:
        successors = self.m_known_relations.get(individual1)
        return successors is not None and individual2 in successors

    def is_possible(
        self, individual1: Individual, individual2: Individual
    ) -> bool:
        successors = self.m_possible_relations.get(individual1)
        return successors is not None and individual2 in successors

    def get_known_relations(self) -> dict[Individual, set[Individual]]:
        return self.m_known_relations

    def get_possible_relations(self) -> dict[Individual, set[Individual]]:
        return self.m_possible_relations

    def has_possibles(self) -> bool:
        return bool(self.m_possible_relations)

    def set_to_known(self, individual1: Individual, individual2: Individual) -> None:
        successors = self.m_possible_relations.get(individual1)
        if successors is not None:
            successors.discard(individual2)
            if not successors:
                self.m_possible_relations.pop(individual1, None)
        self.add_known(individual1, individual2)

    def add_known(self, individual1: Individual, individual2: Individual) -> bool:
        successors = self.m_known_relations.get(individual1)
        if successors is None:
            successors = set()
            self.m_known_relations[individual1] = successors
        was_added = individual2 not in successors
        successors.add(individual2)
        return was_added

    def add_knowns(
        self, individual: Individual, individuals: set[Individual]
    ) -> bool:
        successors = self.m_known_relations.get(individual)
        if successors is None:
            successors = set()
            self.m_known_relations[individual] = successors
        new_items = individuals - successors
        successors.update(individuals)
        return bool(new_items)

    def remove_known(
        self, individual1: Individual, individual2: Individual
    ) -> bool:
        successors = self.m_known_relations.get(individual1)
        removed = False
        if successors is not None:
            removed = individual2 in successors
            successors.discard(individual2)
            if not successors:
                self.m_known_relations.pop(individual1, None)
        return removed

    def add_possible(
        self, individual1: Individual, individual2: Individual
    ) -> bool:
        successors = self.m_possible_relations.get(individual1)
        if successors is None:
            successors = set()
            self.m_possible_relations[individual1] = successors
        was_added = individual2 not in successors
        successors.add(individual2)
        return was_added

    def remove_possible(
        self, individual1: Individual, individual2: Individual
    ) -> bool:
        successors = self.m_possible_relations.get(individual1)
        removed = False
        if successors is not None:
            removed = individual2 in successors
            successors.discard(individual2)
            if not successors:
                self.m_possible_relations.pop(individual1, None)
        return removed

    def add_possibles(
        self, individual: Individual, individuals: set[Individual]
    ) -> bool:
        successors = self.m_possible_relations.get(individual)
        if successors is None:
            successors = set()
            self.m_possible_relations[individual] = successors
        new_items = individuals - successors
        successors.update(individuals)
        return bool(new_items)

    def __str__(self) -> str:
        parts: list[str] = [str(self.m_role)]
        parts.append(" (known instances: ")
        not_first = False
        for individual, successors in self.m_known_relations.items():
            for successor in successors:
                if not_first:
                    parts.append(", ")
                not_first = True
                parts.append(f"({individual}, {successor})")
        parts.append(" | possible instances: ")
        not_first = False
        for individual, successors in self.m_possible_relations.items():
            for successor in successors:
                if not_first:
                    parts.append(", ")
                not_first = True
                parts.append(f"({individual}, {successor})")
        parts.append(") ")
        return "".join(parts)
