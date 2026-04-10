"""Ground disjunction.

Represents a concrete (ground) disjunction -- a disjunction of DL
predicates applied to specific tableau nodes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Mapping, cast

if TYPE_CHECKING:
    from hermit.model import Concept, DLPredicate, Role
    from hermit.model import Prefixes
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
        from hermit.tableau.node import Node

        for arg in self.m_arguments:
            # Only check nodes, not other argument types
            if isinstance(arg, Node) and arg.is_pruned():
                return True
        return False

    def is_satisfied(self, tableau: Tableau) -> bool:
        """Check if any disjunct is currently satisfied in the tableau."""
        from hermit.model import AnnotatedEquality
        from hermit.tableau.node import Node

        extension_manager = tableau.m_extension_manager
        for disjunct_index in range(self.get_number_of_disjuncts()):
            dl_predicate = self.get_dl_predicate(disjunct_index)
            arity = dl_predicate.arity()
            if arity == 1:
                arg0 = self.get_argument(disjunct_index, 0)
                # Handle case where argument might be a node or stored directly
                if isinstance(arg0, Node):
                    arg0_node = arg0.get_canonical_node()
                else:
                    arg0_node = arg0
                if extension_manager.contains_assertion_unary(
                    dl_predicate, arg0_node
                ):
                    return True
            elif arity == 2:
                arg0 = self.get_argument(disjunct_index, 0)
                arg1 = self.get_argument(disjunct_index, 1)
                arg0_node = arg0.get_canonical_node() if isinstance(arg0, Node) else arg0
                arg1_node = arg1.get_canonical_node() if isinstance(arg1, Node) else arg1
                if extension_manager.contains_assertion_binary(
                    dl_predicate,
                    arg0_node,
                    arg1_node,
                ):
                    return True
            elif arity == 3:
                if isinstance(dl_predicate, AnnotatedEquality):
                    arg0 = self.get_argument(disjunct_index, 0)
                    arg1 = self.get_argument(disjunct_index, 1)
                    arg2 = self.get_argument(disjunct_index, 2)
                    arg0_node = arg0.get_canonical_node() if isinstance(arg0, Node) else arg0
                    arg1_node = arg1.get_canonical_node() if isinstance(arg1, Node) else arg1
                    arg2_node = arg2.get_canonical_node() if isinstance(arg2, Node) else arg2
                    if extension_manager.contains_assertion_ternary(
                        dl_predicate,
                        arg0_node,
                        arg1_node,
                        arg2_node,
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
        from hermit.tableau.node import Node

        dl_predicate = self.get_dl_predicate(disjunct_index)
        arity = dl_predicate.arity()
        if arity == 1:
            arg0 = self.get_argument(disjunct_index, 0)
            if not isinstance(arg0, Node):
                # Skip non-node arguments (shouldn't happen, but be safe)
                return False
            dependency_set = arg0.add_canonical_node_dependency_set(dependency_set)
            arg0_node = arg0.get_canonical_node()
            return tableau.m_extension_manager.add_concept_assertion(
                cast("Concept", dl_predicate),
                arg0_node,
                dependency_set,
                self.is_core(disjunct_index),
            )
        elif arity == 2:
            arg0 = self.get_argument(disjunct_index, 0)
            arg1 = self.get_argument(disjunct_index, 1)
            if not isinstance(arg0, Node) or not isinstance(arg1, Node):
                # Skip if arguments aren't nodes
                return False
            dependency_set = arg0.add_canonical_node_dependency_set(dependency_set)
            dependency_set = arg1.add_canonical_node_dependency_set(dependency_set)
            arg0_node = arg0.get_canonical_node()
            arg1_node = arg1.get_canonical_node()
            return tableau.m_extension_manager.add_role_assertion(
                cast("Role", dl_predicate),
                arg0_node,
                arg1_node,
                dependency_set,
                self.is_core(disjunct_index),
            )
        elif arity == 3:
            if isinstance(dl_predicate, AnnotatedEquality):
                arg0 = self.get_argument(disjunct_index, 0)
                arg1 = self.get_argument(disjunct_index, 1)
                arg2 = self.get_argument(disjunct_index, 2)
                if not isinstance(arg0, Node) or not isinstance(arg1, Node) or not isinstance(arg2, Node):
                    # Skip if arguments aren't nodes
                    return False
                dependency_set = arg0.add_canonical_node_dependency_set(dependency_set)
                dependency_set = arg1.add_canonical_node_dependency_set(dependency_set)
                dependency_set = arg2.add_canonical_node_dependency_set(dependency_set)
                arg0_node = arg0.get_canonical_node()
                arg1_node = arg1.get_canonical_node()
                arg2_node = arg2.get_canonical_node()
                return tableau.m_extension_manager.add_annotated_equality(
                    dl_predicate,
                    arg0_node,
                    arg1_node,
                    arg2_node,
                    dependency_set,
                )
            raise RuntimeError("Unsupported predicate arity.")
        raise RuntimeError("Unsupported predicate arity.")

    def to_string(self, prefixes: "Mapping[str, str] | Prefixes | None" = None) -> str:
        """Return a string representation."""
        from hermit.model import Equality
        from hermit.model import Prefixes as Pfx
        from hermit.tableau.node import Node

        if prefixes is None:
            prefixes = Pfx.SEMANTIC_WEB_PREFIXES
        parts = []
        for disjunct_index in range(self.get_number_of_disjuncts()):
            if disjunct_index != 0:
                parts.append(" v ")
            dl_predicate = self.get_dl_predicate(disjunct_index)
            if Equality.INSTANCE == dl_predicate:
                arg0 = self.get_argument(disjunct_index, 0)
                arg1 = self.get_argument(disjunct_index, 1)
                parts.append(str(arg0.node_id if isinstance(arg0, Node) else arg0))
                parts.append(" == ")
                parts.append(str(arg1.node_id if isinstance(arg1, Node) else arg1))
            else:
                from hermit.model import AnnotatedEquality

                if isinstance(dl_predicate, AnnotatedEquality):
                    arg0 = self.get_argument(disjunct_index, 0)
                    arg1 = self.get_argument(disjunct_index, 1)
                    parts.append("[")
                    parts.append(str(arg0.node_id if isinstance(arg0, Node) else arg0))
                    parts.append(" == ")
                    parts.append(str(arg1.node_id if isinstance(arg1, Node) else arg1))
                    parts.append("]@atMost(")
                    parts.append(str(dl_predicate.cardinality))
                    parts.append(" ")
                    parts.append(str(dl_predicate.on_role))
                    parts.append(" ")
                    parts.append(str(dl_predicate.to_concept))
                    parts.append(")(")
                    arg2 = self.get_argument(disjunct_index, 2)
                    parts.append(str(arg2.node_id if isinstance(arg2, Node) else arg2))
                    parts.append(")")
                else:
                    parts.append(str(dl_predicate))
                    parts.append("(")
                    for argument_index in range(dl_predicate.arity()):
                        if argument_index != 0:
                            parts.append(",")
                        arg = self.get_argument(disjunct_index, argument_index)
                        parts.append(str(arg.node_id if isinstance(arg, Node) else arg))
                    parts.append(")")
        return "".join(parts)

    def __str__(self) -> str:
        from hermit.model import Prefixes as Pfx

        return self.to_string(Pfx.SEMANTIC_WEB_PREFIXES)
