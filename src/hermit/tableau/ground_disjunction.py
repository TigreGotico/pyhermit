"""Ground disjunction.

Represents a concrete (ground) disjunction -- a disjunction of DL
predicates applied to specific tableau nodes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.model import DLPredicate
    from hermit.prefixes import Prefixes
    from hermit.tableau.dependency_set import DependencySet
    from hermit.tableau.ground_disjunction_header import GroundDisjunctionHeader
    from hermit.tableau.node import Node
    from hermit.tableau.permanent_dependency_set import PermanentDependencySet
    from hermit.tableau.tableau import Tableau


class GroundDisjunction:
    """A ground (fully instantiated) disjunction in the tableau.

    A ground disjunction represents a disjunction of DL predicates
    applied to specific nodes. When none of the disjuncts is satisfied,
    the tableau must branch on the disjuncts.
    """

    __slots__ = (
        "m_ground_disjunction_header",
        "m_arguments",
        "m_is_core",
        "m_dependency_set",
        "m_previous_ground_disjunction",
        "m_next_ground_disjunction",
    )

    def __init__(
        self,
        tableau: Tableau,
        ground_disjunction_header: GroundDisjunctionHeader,
        arguments: list[Node],
        is_core: list[bool],
        dependency_set: DependencySet,
    ) -> None:
        self.m_ground_disjunction_header = ground_disjunction_header
        self.m_arguments = arguments
        self.m_is_core = is_core
        self.m_dependency_set: PermanentDependencySet | None = (
            tableau.m_dependency_set_factory.get_permanent(dependency_set)
        )
        tableau.m_dependency_set_factory.add_usage(self.m_dependency_set)
        self.m_previous_ground_disjunction: GroundDisjunction | None = None
        self.m_next_ground_disjunction: GroundDisjunction | None = None

    @property
    def previous_ground_disjunction(self) -> GroundDisjunction | None:
        """Return the previous disjunction in the linked list."""
        return self.m_previous_ground_disjunction

    @property
    def next_ground_disjunction(self) -> GroundDisjunction | None:
        """Return the next disjunction in the linked list."""
        return self.m_next_ground_disjunction

    def destroy(self, tableau: Tableau) -> None:
        """Release resources and unregister from the dependency set factory."""
        if self.m_dependency_set is not None:
            tableau.m_dependency_set_factory.remove_usage(self.m_dependency_set)
            self.m_dependency_set = None

    def get_number_of_disjuncts(self) -> int:
        """Return the number of disjuncts."""
        return len(self.m_ground_disjunction_header.m_dl_predicates)

    def get_dl_predicate(self, disjunct_index: int) -> DLPredicate:
        """Return the DL predicate at the given disjunct index."""
        return self.m_ground_disjunction_header.m_dl_predicates[disjunct_index]

    def get_argument(self, disjunct_index: int, argument_index: int) -> Node:
        """Return the node argument for a specific disjunct."""
        offset = self.m_ground_disjunction_header.m_disjunct_start[disjunct_index]
        return self.m_arguments[offset + argument_index]

    def is_core(self, disjunct_index: int) -> bool:
        """Return whether the disjunct is core."""
        return self.m_is_core[disjunct_index]

    def get_dependency_set(self) -> DependencySet | None:
        """Return the dependency set for this disjunction."""
        return self.m_dependency_set

    @property
    def ground_disjunction_header(self) -> GroundDisjunctionHeader:
        """Return the shared header."""
        return self.m_ground_disjunction_header

    def is_pruned(self) -> bool:
        """Return True if any argument node is pruned."""
        for arg in self.m_arguments:
            if arg.is_pruned():
                return True
        return False

    def is_satisfied(self, tableau: Tableau) -> bool:
        """Check if any disjunct is currently satisfied in the tableau."""
        from hermit.model import AnnotatedEquality

        extension_manager = tableau.m_extension_manager
        for disjunct_index in range(self.get_number_of_disjuncts()):
            dl_predicate = self.get_dl_predicate(disjunct_index)
            arity = dl_predicate.get_arity()
            if arity == 1:
                if extension_manager.contains_assertion(
                    dl_predicate, self.get_argument(disjunct_index, 0).get_canonical_node()
                ):
                    return True
            elif arity == 2:
                if extension_manager.contains_assertion(
                    dl_predicate,
                    self.get_argument(disjunct_index, 0).get_canonical_node(),
                    self.get_argument(disjunct_index, 1).get_canonical_node(),
                ):
                    return True
            elif arity == 3:
                if isinstance(dl_predicate, AnnotatedEquality):
                    if extension_manager.contains_assertion(
                        dl_predicate,
                        self.get_argument(disjunct_index, 0).get_canonical_node(),
                        self.get_argument(disjunct_index, 1).get_canonical_node(),
                        self.get_argument(disjunct_index, 2).get_canonical_node(),
                    ):
                        return True
                else:
                    raise RuntimeError("Invalid arity of DL-predicate.")
            else:
                raise RuntimeError("Invalid arity of DL-predicate.")
        return False

    def add_disjunct_to_tableau(
        self, tableau: Tableau, disjunct_index: int, dependency_set: DependencySet
    ) -> bool:
        """Add a specific disjunct to the tableau.

        Returns True if the assertion was newly added.
        """
        from hermit.model import AnnotatedEquality

        dl_predicate = self.get_dl_predicate(disjunct_index)
        arity = dl_predicate.get_arity()
        if arity == 1:
            dependency_set = self.get_argument(disjunct_index, 0).add_canonical_node_dependency_set(
                dependency_set
            )
            return tableau.m_extension_manager.add_assertion(
                dl_predicate,
                self.get_argument(disjunct_index, 0).get_canonical_node(),
                dependency_set,
                self.is_core(disjunct_index),
            )
        elif arity == 2:
            dependency_set = self.get_argument(disjunct_index, 0).add_canonical_node_dependency_set(
                dependency_set
            )
            dependency_set = self.get_argument(disjunct_index, 1).add_canonical_node_dependency_set(
                dependency_set
            )
            return tableau.m_extension_manager.add_assertion(
                dl_predicate,
                self.get_argument(disjunct_index, 0).get_canonical_node(),
                self.get_argument(disjunct_index, 1).get_canonical_node(),
                dependency_set,
                self.is_core(disjunct_index),
            )
        elif arity == 3:
            if isinstance(dl_predicate, AnnotatedEquality):
                dependency_set = self.get_argument(
                    disjunct_index, 0
                ).add_canonical_node_dependency_set(dependency_set)
                dependency_set = self.get_argument(
                    disjunct_index, 1
                ).add_canonical_node_dependency_set(dependency_set)
                dependency_set = self.get_argument(
                    disjunct_index, 2
                ).add_canonical_node_dependency_set(dependency_set)
                return tableau.m_extension_manager.add_annotated_equality(
                    dl_predicate,
                    self.get_argument(disjunct_index, 0).get_canonical_node(),
                    self.get_argument(disjunct_index, 1).get_canonical_node(),
                    self.get_argument(disjunct_index, 2).get_canonical_node(),
                    dependency_set,
                )
            raise RuntimeError("Unsupported predicate arity.")
        raise RuntimeError("Unsupported predicate arity.")

    def to_string(self, prefixes: Prefixes | None = None) -> str:
        """Return a string representation."""
        from hermit.model import Equality
        from hermit.prefixes import Prefixes as Pfx

        if prefixes is None:
            prefixes = Pfx.STANDARD_PREFIXES
        parts = []
        for disjunct_index in range(self.get_number_of_disjuncts()):
            if disjunct_index != 0:
                parts.append(" v ")
            dl_predicate = self.get_dl_predicate(disjunct_index)
            if Equality.INSTANCE.equals(dl_predicate):
                parts.append(str(self.get_argument(disjunct_index, 0).node_id))
                parts.append(" == ")
                parts.append(str(self.get_argument(disjunct_index, 1).node_id))
            else:
                from hermit.model import AnnotatedEquality

                if isinstance(dl_predicate, AnnotatedEquality):
                    parts.append("[")
                    parts.append(str(self.get_argument(disjunct_index, 0).node_id))
                    parts.append(" == ")
                    parts.append(str(self.get_argument(disjunct_index, 1).node_id))
                    parts.append("]@atMost(")
                    parts.append(str(dl_predicate.get_cardinality()))
                    parts.append(" ")
                    parts.append(dl_predicate.get_on_role().to_string(prefixes))
                    parts.append(" ")
                    parts.append(dl_predicate.get_to_concept().to_string(prefixes))
                    parts.append(")(")
                    parts.append(str(self.get_argument(disjunct_index, 2).node_id))
                    parts.append(")")
                else:
                    parts.append(dl_predicate.to_string(prefixes))
                    parts.append("(")
                    for argument_index in range(dl_predicate.get_arity()):
                        if argument_index != 0:
                            parts.append(",")
                        parts.append(str(self.get_argument(disjunct_index, argument_index).node_id))
                    parts.append(")")
        return "".join(parts)

    def __str__(self) -> str:
        from hermit.prefixes import Prefixes as Pfx

        return self.to_string(Pfx.STANDARD_PREFIXES)
