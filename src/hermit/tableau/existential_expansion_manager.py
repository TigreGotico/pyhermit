"""Existential expansion manager.

Manages the expansion of at-least restrictions in a tableau, including
functional expansion, normal expansion, and tracking of which existentials
have been processed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hermit.model import (
    AtLeast,
    AtLeastConcept,
    AtLeastDataRange,
    AtomicRole,
    Inequality,
    InverseRole,
    Role,
)
from hermit.tableau.dependency_set import DependencySet
from hermit.tableau.tuple_table import TupleTable
from hermit.tableau.union_dependency_set import UnionDependencySet

if TYPE_CHECKING:
    from hermit.model import ExistentialConcept
    from hermit.tableau.extension_manager import Retrieval
    from hermit.tableau.node import Node
    from hermit.tableau.tableau import Tableau


class ExistentialExpansionManager:
    """Manages the expansion of at-least restrictions in a tableau."""

    def __init__(self, tableau: Tableau) -> None:
        self.m_tableau = tableau
        self.m_extension_manager = tableau.m_extension_manager
        self.m_expanded_existentials = TupleTable(2)
        self.m_auxiliary_tuple: list[object | None] = [None, None]
        self.m_auxiliary_nodes: list[Node] = []
        ext_table = self.m_extension_manager.get_ternary_extension_table()
        self.m_ternary_extension_table_search01_bound: Retrieval = (
            ext_table.create_retrieval([True, True, False], "TOTAL")
        )
        self.m_ternary_extension_table_search02_bound: Retrieval = (
            ext_table.create_retrieval([True, False, True], "TOTAL")
        )
        self.m_functional_roles: dict[Role, list[Role]] = {}
        self._update_functional_roles()
        self.m_binary_union_dependency_set = UnionDependencySet(2)
        self.m_indices_by_branching_point: list[int] = [0] * 2

    def _update_functional_roles(self) -> None:
        """Build the functional role hierarchy from DL clauses."""
        from hermit.graph import Graph

        super_role_graph: Graph[Role] = Graph()
        functional_roles: set[Role] = set()
        self._load_dl_clauses_into_graph(
            self.m_tableau.m_permanent_dl_ontology.get_dl_clauses(),
            super_role_graph,
            functional_roles,
        )
        for role in super_role_graph.get_elements():
            super_role_graph.add_edge(role, role)
            super_role_graph.add_edge(role.get_inverse(), role.get_inverse())
        super_role_graph.transitively_close()
        sub_role_graph: Graph[Role] = super_role_graph.get_inverse()
        self.m_functional_roles.clear()
        for role in super_role_graph.get_elements():
            relevant_roles: set[Role] = set()
            all_superroles = super_role_graph.get_successors(role)
            for superrole in all_superroles:
                if superrole in functional_roles:
                    relevant_roles.update(sub_role_graph.get_successors(superrole))
            if relevant_roles:
                self.m_functional_roles[role] = list(relevant_roles)

    def _load_dl_clauses_into_graph(
        self,
        dl_clauses: set[object],
        super_role_graph: Any,
        functional_roles: set[Role],
    ) -> None:
        """Load DL clauses into the role graph and functional role set."""
        from hermit.model import AtomicRole, DLClause

        for dl_clause in dl_clauses:
            if not isinstance(dl_clause, DLClause):
                continue
            if dl_clause.is_atomic_role_inclusion():
                subrole = dl_clause.get_body_atom(0).get_dl_predicate()
                superrole = dl_clause.get_head_atom(0).get_dl_predicate()
                assert isinstance(subrole, AtomicRole)
                assert isinstance(superrole, AtomicRole)
                super_role_graph.add_edge(subrole, superrole)
                super_role_graph.add_edge(subrole.get_inverse(), superrole.get_inverse())
            elif dl_clause.is_atomic_role_inverse_inclusion():
                subrole = dl_clause.get_body_atom(0).get_dl_predicate()
                superrole = dl_clause.get_head_atom(0).get_dl_predicate()
                assert isinstance(subrole, AtomicRole)
                assert isinstance(superrole, AtomicRole)
                super_role_graph.add_edge(subrole, superrole.get_inverse())
                super_role_graph.add_edge(subrole.get_inverse(), superrole)
            elif dl_clause.is_functionality_axiom():
                atomic_role = dl_clause.get_body_atom(0).get_dl_predicate()
                assert isinstance(atomic_role, AtomicRole)
                functional_roles.add(atomic_role)
            elif dl_clause.is_inverse_functionality_axiom():
                atomic_role = dl_clause.get_body_atom(0).get_dl_predicate()
                assert isinstance(atomic_role, AtomicRole)
                functional_roles.add(atomic_role.get_inverse())

    def mark_existential_processed(
        self, existential_concept: ExistentialConcept, for_node: Node
    ) -> None:
        """Mark an existential as processed on a node."""
        self.m_auxiliary_tuple[0] = existential_concept
        self.m_auxiliary_tuple[1] = for_node
        self.m_expanded_existentials.add_tuple(self.m_auxiliary_tuple)
        for_node._remove_from_unprocessed_existentials(existential_concept)

    def branching_point_pushed(self) -> None:
        """Save state for backtracking at the current branching point."""
        start = self.m_tableau.m_current_branching_point + 1
        required_size = start + 1
        if required_size > len(self.m_indices_by_branching_point):
            new_size = len(self.m_indices_by_branching_point) * 3 // 2
            while required_size > new_size:
                new_size = new_size * 3 // 2
            new_indices = [0] * new_size
            new_indices[: len(self.m_indices_by_branching_point)] = (
                self.m_indices_by_branching_point
            )
            self.m_indices_by_branching_point = new_indices
        self.m_indices_by_branching_point[start] = (
            self.m_expanded_existentials.first_free_tuple_index
        )

    def backtrack(self) -> None:
        """Restore state to the current branching point."""
        new_first_free = self.m_indices_by_branching_point[
            self.m_tableau.m_current_branching_point + 1
        ]
        for tuple_index in range(
            self.m_expanded_existentials.first_free_tuple_index - 1,
            new_first_free - 1,
            -1,
        ):
            self.m_expanded_existentials.retrieve_tuple(
                self.m_auxiliary_tuple, tuple_index
            )
            existential_concept = self.m_auxiliary_tuple[0]
            for_node = self.m_auxiliary_tuple[1]
            assert isinstance(existential_concept, AtLeast)
            assert isinstance(for_node, Node)
            for_node._add_to_unprocessed_existentials(existential_concept)
        self.m_expanded_existentials.truncate(new_first_free)

    def clear(self) -> None:
        """Clear all accumulated state."""
        self.m_expanded_existentials.clear()
        self.m_auxiliary_tuple[0] = None
        self.m_auxiliary_tuple[1] = None
        self.m_ternary_extension_table_search01_bound.clear()
        self.m_ternary_extension_table_search02_bound.clear()
        self.m_binary_union_dependency_set.m_dependency_sets[0] = None
        self.m_binary_union_dependency_set.m_dependency_sets[1] = None

    def try_functional_expansion(self, at_least: AtLeast, for_node: Node) -> bool:
        """Attempt functional expansion (uses functionality axioms).

        Returns True if expansion was performed (or a clash was detected).
        """
        if at_least.number == 1:
            result: list[object | None] = [None, None]
            if self._get_functional_expansion_node(at_least.on_role, for_node, result):
                if self.m_tableau.m_tableau_monitor is not None:
                    self.m_tableau.m_tableau_monitor.existential_expansion_started(
                        at_least, for_node
                    )
                functionality_node: Node = result[0]  # type: ignore[assignment]
                self.m_binary_union_dependency_set.m_dependency_sets[0] = (
                    self.m_extension_manager.get_concept_assertion_dependency_set(
                        at_least, for_node
                    )
                )
                assert isinstance(result[1], DependencySet)
                self.m_binary_union_dependency_set.m_dependency_sets[1] = result[1]
                self.m_extension_manager.add_role_assertion(
                    at_least.on_role,
                    for_node,
                    functionality_node,
                    self.m_binary_union_dependency_set,
                    True,
                )
                if isinstance(at_least, AtLeastConcept):
                    self.m_extension_manager.add_concept_assertion(
                        at_least.to_concept,
                        functionality_node,
                        self.m_binary_union_dependency_set,
                        True,
                    )
                else:
                    assert isinstance(at_least, AtLeastDataRange)
                    self.m_extension_manager.add_data_range_assertion(
                        at_least.to_data_range,
                        functionality_node,
                        self.m_binary_union_dependency_set,
                        True,
                    )
                if self.m_tableau.m_tableau_monitor is not None:
                    self.m_tableau.m_tableau_monitor.existential_expansion_finished(
                        at_least, for_node
                    )
                return True
        elif at_least.number > 1 and at_least.on_role in self.m_functional_roles:
            if self.m_tableau.m_tableau_monitor is not None:
                self.m_tableau.m_tableau_monitor.existential_expansion_started(
                    at_least, for_node
                )
            existential_dependency_set = (
                self.m_extension_manager.get_concept_assertion_dependency_set(
                    at_least, for_node
                )
            )
            assert existential_dependency_set is not None
            self.m_extension_manager.set_clash(existential_dependency_set)
            if self.m_tableau.m_tableau_monitor is not None:
                self.m_tableau.m_tableau_monitor.existential_expansion_finished(
                    at_least, for_node
                )
            return True
        return False

    def _get_functional_expansion_node(
        self, role: Role, for_node: Node, result: list[object | None]
    ) -> bool:
        """Find an existing node that satisfies functionality constraints."""
        relevant_roles = self.m_functional_roles.get(role)
        if relevant_roles is not None:
            for relevant_role in relevant_roles:
                retrieval: Retrieval
                to_node_index: int
                if isinstance(relevant_role, AtomicRole):
                    retrieval = self.m_ternary_extension_table_search01_bound
                    retrieval.get_bindings_buffer()[0] = relevant_role
                    retrieval.get_bindings_buffer()[1] = for_node
                    to_node_index = 2
                else:
                    retrieval = self.m_ternary_extension_table_search02_bound
                    assert isinstance(relevant_role, InverseRole)
                    retrieval.get_bindings_buffer()[0] = relevant_role.inverse_of
                    retrieval.get_bindings_buffer()[2] = for_node
                    to_node_index = 1
                retrieval.open()
                if not retrieval.after_last():
                    result[0] = retrieval.get_tuple_buffer()[to_node_index]
                    result[1] = retrieval.get_dependency_set()
                    return True
        return False

    def do_normal_expansion_concept(
        self, at_least_concept: AtLeastConcept, for_node: Node
    ) -> None:
        """Normal (non-functional) expansion for a concept at-least."""
        if self.m_tableau.m_tableau_monitor is not None:
            self.m_tableau.m_tableau_monitor.existential_expansion_started(
                at_least_concept, for_node
            )
        existential_dependency_set = (
            self.m_extension_manager.get_concept_assertion_dependency_set(
                at_least_concept, for_node
            )
        )
        assert existential_dependency_set is not None
        cardinality = at_least_concept.number
        if cardinality == 1:
            new_node = self.m_tableau.create_new_tree_node(
                existential_dependency_set, for_node
            )
            self.m_extension_manager.add_role_assertion(
                at_least_concept.on_role,
                for_node,
                new_node,
                existential_dependency_set,
                True,
            )
            self.m_extension_manager.add_concept_assertion(
                at_least_concept.to_concept,
                new_node,
                existential_dependency_set,
                True,
            )
        else:
            self.m_auxiliary_nodes.clear()
            for _index in range(cardinality):
                new_node = self.m_tableau.create_new_tree_node(
                    existential_dependency_set, for_node
                )
                self.m_extension_manager.add_role_assertion(
                    at_least_concept.on_role,
                    for_node,
                    new_node,
                    existential_dependency_set,
                    True,
                )
                self.m_extension_manager.add_concept_assertion(
                    at_least_concept.to_concept,
                    new_node,
                    existential_dependency_set,
                    True,
                )
                self.m_auxiliary_nodes.append(new_node)
            for outer_index in range(cardinality):
                outer_node = self.m_auxiliary_nodes[outer_index]
                for inner_index in range(outer_index + 1, cardinality):
                    self.m_extension_manager.add_assertion(
                        Inequality.INSTANCE,
                        outer_node,
                        self.m_auxiliary_nodes[inner_index],
                        existential_dependency_set,
                        True,
                    )
            self.m_auxiliary_nodes.clear()
        if self.m_tableau.m_tableau_monitor is not None:
            self.m_tableau.m_tableau_monitor.existential_expansion_finished(
                at_least_concept, for_node
            )

    def do_normal_expansion_data_range(
        self, at_least_data_range: AtLeastDataRange, for_node: Node
    ) -> None:
        """Normal (non-functional) expansion for a data range at-least."""
        if self.m_tableau.m_tableau_monitor is not None:
            self.m_tableau.m_tableau_monitor.existential_expansion_started(
                at_least_data_range, for_node
            )
        existential_dependency_set = (
            self.m_extension_manager.get_concept_assertion_dependency_set(
                at_least_data_range, for_node
            )
        )
        assert existential_dependency_set is not None
        cardinality = at_least_data_range.number
        if cardinality == 1:
            new_node = self.m_tableau.create_new_concrete_node(
                existential_dependency_set, for_node
            )
            self.m_extension_manager.add_role_assertion(
                at_least_data_range.on_role,
                for_node,
                new_node,
                existential_dependency_set,
                True,
            )
            self.m_extension_manager.add_data_range_assertion(
                at_least_data_range.to_data_range,
                new_node,
                existential_dependency_set,
                True,
            )
        else:
            self.m_auxiliary_nodes.clear()
            for _index in range(cardinality):
                new_node = self.m_tableau.create_new_concrete_node(
                    existential_dependency_set, for_node
                )
                self.m_extension_manager.add_role_assertion(
                    at_least_data_range.on_role,
                    for_node,
                    new_node,
                    existential_dependency_set,
                    True,
                )
                self.m_extension_manager.add_data_range_assertion(
                    at_least_data_range.to_data_range,
                    new_node,
                    existential_dependency_set,
                    True,
                )
                self.m_auxiliary_nodes.append(new_node)
            for outer_index in range(cardinality):
                outer_node = self.m_auxiliary_nodes[outer_index]
                for inner_index in range(outer_index + 1, cardinality):
                    self.m_extension_manager.add_assertion(
                        Inequality.INSTANCE,
                        outer_node,
                        self.m_auxiliary_nodes[inner_index],
                        existential_dependency_set,
                        True,
                    )
            self.m_auxiliary_nodes.clear()
        if self.m_tableau.m_tableau_monitor is not None:
            self.m_tableau.m_tableau_monitor.existential_expansion_finished(
                at_least_data_range, for_node
            )

    def expand(self, at_least: AtLeast, for_node: Node) -> None:
        """Expand an at-least restriction, choosing the appropriate strategy."""
        if not self.try_functional_expansion(at_least, for_node):
            if isinstance(at_least, AtLeastConcept):
                self.do_normal_expansion_concept(at_least, for_node)
            else:
                assert isinstance(at_least, AtLeastDataRange)
                self.do_normal_expansion_data_range(at_least, for_node)
