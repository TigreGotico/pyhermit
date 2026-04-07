"""Graph utilities for HermiT."""

from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class Graph(Generic[T]):
    """Directed graph with adjacency-list representation.

    Faithful port of ``org.semanticweb.HermiT.graph.Graph``.
    """

    __slots__ = ("_elements", "_successors_by_nodes")

    def __init__(self) -> None:
        self._elements: set[T] = set()
        self._successors_by_nodes: dict[T, set[T]] = {}

    def add_edge(self, frm: T, to: T) -> None:
        successors = self._successors_by_nodes.get(frm)
        if successors is None:
            successors = set()
            self._successors_by_nodes[frm] = successors
        successors.add(to)
        self._elements.add(frm)
        self._elements.add(to)

    def add_edges(self, frm: T, to: set[T]) -> None:
        successors = self._successors_by_nodes.get(frm)
        if successors is None:
            successors = set()
            self._successors_by_nodes[frm] = successors
        successors.update(to)
        self._elements.add(frm)
        self._elements.update(to)

    def get_elements(self) -> set[T]:
        return self._elements

    def get_successors(self, node: T) -> set[T]:
        result = self._successors_by_nodes.get(node)
        if result is None:
            return set()
        return result

    def transitively_close(self) -> None:
        for reachable in self._successors_by_nodes.values():
            to_process = list(reachable)
            while to_process:
                element_on_path = to_process.pop()
                element_on_path_successors = self._successors_by_nodes.get(
                    element_on_path
                )
                if element_on_path_successors is not None:
                    for successor in element_on_path_successors:
                        if reachable.add(successor):
                            to_process.append(successor)

    def get_inverse(self) -> Graph[T]:
        result: Graph[T] = Graph()
        for frm, successors in self._successors_by_nodes.items():
            for successor in successors:
                result.add_edge(successor, frm)
        return result

    def clone(self) -> Graph[T]:
        result: Graph[T] = Graph()
        result._elements = set(self._elements)
        for frm, successors in self._successors_by_nodes.items():
            for successor in successors:
                result.add_edge(frm, successor)
        return result

    def remove_elements(self, elements: set[T]) -> None:
        for element in elements:
            self._elements.discard(element)
            self._successors_by_nodes.pop(element, None)

    def is_reachable_successor(self, from_node: T, to_node: T) -> bool:
        if from_node == to_node:
            return True
        result: set[T] = set()
        to_visit: list[T] = [from_node]
        while to_visit:
            current = to_visit.pop(0)
            successors = self.get_successors(current)
            if to_node in successors:
                return True
            if result.add(current):
                to_visit.extend(successors)
        return False

    def get_reachable_successors(self, from_node: T) -> set[T]:
        result: set[T] = set()
        to_visit: list[T] = [from_node]
        visited: set[T] = set()
        while to_visit:
            current = to_visit.pop(0)
            if current not in visited:
                visited.add(current)
                result.add(current)
                to_visit.extend(self.get_successors(current))
        return result

    def __str__(self) -> str:
        import os

        lines: list[str] = []
        for element in self._elements:
            successors = self._successors_by_nodes.get(element)
            succ_str = (
                ", ".join(str(s) for s in successors) if successors else ""
            )
            lines.append(f"{element} -> {{ {succ_str} }}")
        return os.linesep.join(lines)
