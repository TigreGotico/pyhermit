"""Ground disjunction header.

Stores the shared structure of ground disjunctions, including the
disjunct predicates and disjunct ordering with backtracking counts
for disjunction learning.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.model import DLPredicate



class DisjunctIndexWithBacktrackings:
    """Tracks a disjunct index and its backtrack count for learning."""

    __slots__ = ("m_disjunct_index", "m_number_of_backtrackings")

    def __init__(self, index: int) -> None:
        self.m_disjunct_index = index
        self.m_number_of_backtrackings = 0


class GroundDisjunctionHeader:
    """Shared header for ground disjunctions with the same DL predicates.

    Ground disjunctions that share the same DL predicates share a header.
    The header also manages disjunct ordering with backtracking counts
    for disjunction learning optimization.
    """

    __slots__ = (
        "m_dl_predicates",
        "m_disjunct_start",
        "m_hash_code",
        "m_disjunct_indexes_with_backtrackings",
        "m_first_at_least_positive_index",
        "m_first_at_least_negative_index",
        "m_next_entry",
    )

    def __init__(
        self,
        dl_predicates: list[DLPredicate],
        hash_code: int,
        next_entry: GroundDisjunctionHeader | None,
    ) -> None:
        self.m_dl_predicates = dl_predicates
        self.m_disjunct_start = [0] * len(self.m_dl_predicates)
        arguments_size = 0
        for disjunct_index in range(len(self.m_dl_predicates)):
            self.m_disjunct_start[disjunct_index] = arguments_size
            arguments_size += self.m_dl_predicates[disjunct_index].arity()
        self.m_hash_code = hash_code
        self.m_next_entry = next_entry
        self.m_disjunct_indexes_with_backtrackings: list[DisjunctIndexWithBacktrackings] = [
            DisjunctIndexWithBacktrackings(0) for _ in range(len(dl_predicates))
        ]
        # Disjuncts are arranged in a particular order that works well in practice:
        # 1. At-least concepts over negated atomic concepts
        # 2. Atomic concept disjuncts
        # 3. At-least concepts not over negated atomic concepts
        from hermit.model import AtLeastConcept, AtomicNegationConcept

        number_of_at_least_positive_disjuncts = 0
        number_of_at_least_negative_disjuncts = 0
        for dl_pred in self.m_dl_predicates:
            if isinstance(dl_pred, AtLeastConcept):
                at_least: AtLeastConcept = dl_pred
                if isinstance(at_least.to_concept, AtomicNegationConcept):
                    number_of_at_least_negative_disjuncts += 1
                else:
                    number_of_at_least_positive_disjuncts += 1
        self.m_first_at_least_negative_index = (
            len(self.m_disjunct_indexes_with_backtrackings)
            - number_of_at_least_positive_disjuncts
            - number_of_at_least_negative_disjuncts
        )
        self.m_first_at_least_positive_index = (
            len(self.m_disjunct_indexes_with_backtrackings)
            - number_of_at_least_positive_disjuncts
        )
        next_atomic_disjunct = 0
        next_at_least_negative_disjunct = self.m_first_at_least_negative_index
        next_at_least_positive_disjunct = self.m_first_at_least_positive_index
        for index in range(len(self.m_dl_predicates)):
            dl_pred = self.m_dl_predicates[index]
            if isinstance(dl_pred, AtLeastConcept):
                at_least = dl_pred
                if isinstance(at_least.to_concept, AtomicNegationConcept):
                    self.m_disjunct_indexes_with_backtrackings[
                        next_at_least_negative_disjunct
                    ] = DisjunctIndexWithBacktrackings(index)
                    next_at_least_negative_disjunct += 1
                else:
                    self.m_disjunct_indexes_with_backtrackings[
                        next_at_least_positive_disjunct
                    ] = DisjunctIndexWithBacktrackings(index)
                    next_at_least_positive_disjunct += 1
            else:
                self.m_disjunct_indexes_with_backtrackings[
                    next_atomic_disjunct
                ] = DisjunctIndexWithBacktrackings(index)
                next_atomic_disjunct += 1

    def is_equal(self, dl_predicates: list[DLPredicate]) -> bool:
        """Check if this header matches the given predicate list."""
        if len(self.m_dl_predicates) != len(dl_predicates):
            return False
        for i in range(len(self.m_dl_predicates) - 1, -1, -1):
            if self.m_dl_predicates[i] != dl_predicates[i]:
                return False
        return True

    def get_sorted_disjunct_indexes(self) -> list[int]:
        """Return disjunct indexes sorted by backtracking count."""
        return [
            entry.m_disjunct_index
            for entry in self.m_disjunct_indexes_with_backtrackings
        ]

    def increase_number_of_backtrackings(self, disjunct_index: int) -> None:
        """Increment backtracking count and bubble-sort the disjunct."""
        for index in range(len(self.m_disjunct_indexes_with_backtrackings)):
            entry = self.m_disjunct_indexes_with_backtrackings[index]
            if entry.m_disjunct_index == disjunct_index:
                entry.m_number_of_backtrackings += 1
                # Find the partition end -- swapping stops when backtrack count
                # is lower than the next, or at partition boundary.
                if index < self.m_first_at_least_negative_index:
                    partition_end = self.m_first_at_least_negative_index
                elif index < self.m_first_at_least_positive_index:
                    partition_end = self.m_first_at_least_positive_index
                else:
                    partition_end = len(self.m_disjunct_indexes_with_backtrackings)
                current_index = index
                next_index = current_index + 1
                while (
                    next_index < partition_end
                    and entry.m_number_of_backtrackings
                    > self.m_disjunct_indexes_with_backtrackings[
                        next_index
                    ].m_number_of_backtrackings
                ):
                    self.m_disjunct_indexes_with_backtrackings[current_index] = (
                        self.m_disjunct_indexes_with_backtrackings[next_index]
                    )
                    self.m_disjunct_indexes_with_backtrackings[next_index] = entry
                    current_index = next_index
                    next_index += 1
                break

    def __str__(self) -> str:
        """Return a string representation."""
        parts = []
        for disjunct_index in range(len(self.m_dl_predicates)):
            if disjunct_index > 0:
                parts.append(" \\/ ")
            parts.append(str(self.m_dl_predicates[disjunct_index]))
            parts.append(" (")
            for entry in self.m_disjunct_indexes_with_backtrackings:
                if entry.m_disjunct_index == disjunct_index:
                    parts.append(str(entry.m_number_of_backtrackings))
                    break
            parts.append(")")
        return "".join(parts)

    def __repr__(self) -> str:
        return self.__str__()
