"""Quasi-order classification algorithm for HermiT.

Faithful port of ``org.semanticweb.HermiT.hierarchy.QuasiOrderClassification``.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from hermit.graph import Graph
from hermit.hierarchy.deterministic_classification import (
    DeterministicClassification,
    GraphNode,
)
from hermit.hierarchy.hierarchy import Hierarchy
from hermit.hierarchy.hierarchy_node import HierarchyNode
from hermit.hierarchy.hierarchy_search import Relation
from hermit.model import AtomicConcept

if TYPE_CHECKING:
    from hermit.hierarchy.classification_progress_monitor import (
        ClassificationProgressMonitor,
    )
    from hermit.model import DLClause, Individual
    from hermit.tableau.node import Node
    from hermit.tableau.reasoning_task_description import ReasoningTaskDescription
    from hermit.tableau.tableau import Tableau


class QuasiOrderClassification:
    """Classifies atomic concepts using the quasi-order optimisation.

    This algorithm incrementally discovers subsumption relationships,
    pruning the search space using known and possible subsumers.  It
    implements the leaf-node strategy from the enhanced traversal
    classification algorithm.
    """

    def __init__(
        self,
        tableau: Tableau,
        progress_monitor: ClassificationProgressMonitor,
        top_element: AtomicConcept,
        bottom_element: AtomicConcept,
        elements: set[AtomicConcept],
    ) -> None:
        self.m_tableau = tableau
        self.m_progress_monitor = progress_monitor
        self.m_top_element = top_element
        self.m_bottom_element = bottom_element
        self.m_elements = elements
        self.m_known_subsumptions: Graph[AtomicConcept] = Graph()
        self.m_possible_subsumptions: Graph[AtomicConcept] = Graph()

    def classify(self) -> Hierarchy[AtomicConcept]:
        relation: Relation[AtomicConcept] = _ClassificationRelation(self)
        return self._build_hierarchy(relation)

    # ------------------------------------------------------------------
    # Build hierarchy
    # ------------------------------------------------------------------

    def _build_hierarchy(
        self, hierarchy_relation: Relation[AtomicConcept]
    ) -> Hierarchy[AtomicConcept]:
        total_number_of_tasks = float(len(self.m_elements))
        self._make_concept_unsatisfiable(self.m_bottom_element)
        self._initialise_known_subsumptions_using_told_subsumers()
        tasks_performed = self._update_subsumptions_using_leaf_node_strategy(
            total_number_of_tasks
        )

        # Remove known subsumers from possible subsumptions.
        unclassified_elements: set[AtomicConcept] = set()
        for element in self.m_elements:
            if not self._is_unsatisfiable(element):
                self.m_possible_subsumptions.get_successors(element).difference_update(
                    self._get_all_known_subsumers(element)
                )
                if self.m_possible_subsumptions.get_successors(element):
                    unclassified_elements.add(element)
                    continue

        classified_elements: set[AtomicConcept] = set()
        while unclassified_elements:
            unclassified_element: AtomicConcept | None = None
            for element in unclassified_elements:
                self.m_possible_subsumptions.get_successors(element).difference_update(
                    self._get_all_known_subsumers(element)
                )
                if self.m_possible_subsumptions.get_successors(element):
                    unclassified_element = element
                    break
                classified_elements.add(element)
                while len(unclassified_elements) < (
                    total_number_of_tasks - tasks_performed
                ):
                    self.m_progress_monitor.element_classified(element)
                    tasks_performed += 1

            unclassified_elements.difference_update(classified_elements)
            if not unclassified_elements:
                break

            unknown_possible_subsumers = self.m_possible_subsumptions.get_successors(
                unclassified_element
            )
            if (
                not self._is_every_possible_subsumer_non_subsumer(
                    unknown_possible_subsumers, unclassified_element, 2, 7
                )
                and unknown_possible_subsumers
            ):
                small_hierarchy = self._build_hierarchy_of_unknown_possible(
                    unknown_possible_subsumers
                )
                self._check_unknown_subsumers_using_enhanced_traversal(
                    hierarchy_relation, small_hierarchy.get_top_node(), unclassified_element
                )
            unknown_possible_subsumers.clear()

        return self._build_transitively_reduced_hierarchy(
            self.m_known_subsumptions, self.m_elements
        )

    def _build_hierarchy_of_unknown_possible(
        self, unknown_subsumers: set[AtomicConcept]
    ) -> Hierarchy[AtomicConcept]:
        small_known_subsumptions: Graph[AtomicConcept] = Graph()
        for unknown_subsumer_0 in unknown_subsumers:
            small_known_subsumptions.add_edge(self.m_bottom_element, unknown_subsumer_0)
            small_known_subsumptions.add_edge(unknown_subsumer_0, self.m_top_element)
            known_subsumers_of_element = self._get_all_known_subsumers(
                unknown_subsumer_0
            )
            for unknown_subsumer_1 in unknown_subsumers:
                if unknown_subsumer_1 in known_subsumers_of_element:
                    small_known_subsumptions.add_edge(
                        unknown_subsumer_0, unknown_subsumer_1
                    )
        unknown_subsumers_with_top_bottom: set[AtomicConcept] = set(unknown_subsumers)
        unknown_subsumers_with_top_bottom.add(self.m_bottom_element)
        unknown_subsumers_with_top_bottom.add(self.m_top_element)
        return self._build_transitively_reduced_hierarchy(
            small_known_subsumptions, unknown_subsumers_with_top_bottom
        )

    # ------------------------------------------------------------------
    # Leaf-node strategy
    # ------------------------------------------------------------------

    def _update_subsumptions_using_leaf_node_strategy(
        self, total_number_of_tasks: float
    ) -> float:
        concepts_processed = 0.0
        hierarchy = self._build_transitively_reduced_hierarchy(
            self.m_known_subsumptions, self.m_elements
        )
        to_process: list[HierarchyNode[AtomicConcept]] = list(
            hierarchy.get_bottom_node().m_parent_nodes
        )
        unsat_hierarchy_nodes: set[HierarchyNode[AtomicConcept]] = set()
        while to_process:
            current_hierarchy_element = to_process.pop()
            current_hierarchy_concept = current_hierarchy_element.m_representative
            if concepts_processed < math.ceil(total_number_of_tasks * 0.85):
                self.m_progress_monitor.element_classified(
                    current_hierarchy_concept
                )
                concepts_processed += 1.0
            if not self._concept_has_been_processed_already(
                current_hierarchy_concept
            ):
                root_node_of_model = self._build_model_for_concept(
                    current_hierarchy_concept
                )
                if root_node_of_model is None:
                    self._make_concept_unsatisfiable(current_hierarchy_concept)
                    unsat_hierarchy_nodes.add(current_hierarchy_element)
                    to_process.extend(current_hierarchy_element.m_parent_nodes)
                    visited: set[HierarchyNode[AtomicConcept]] = set()
                    to_visit: list[HierarchyNode[AtomicConcept]] = list(
                        current_hierarchy_element.m_child_nodes
                    )
                    while to_visit:
                        current = to_visit.pop(0)
                        if current not in visited and current not in unsat_hierarchy_nodes:
                            visited.add(current)
                            to_visit.extend(current.m_child_nodes)
                            unsat_hierarchy_nodes.add(current)
                            self._make_concept_unsatisfiable(
                                current.m_representative
                            )
                            if current in to_process:
                                to_process.remove(current)
                            for parent_of_removed_concept in current.m_parent_nodes:
                                if not self._concept_has_been_processed_already(
                                    parent_of_removed_concept.m_representative
                                ):
                                    to_process.append(parent_of_removed_concept)
                else:
                    self._read_known_subsumers_from_root_node(
                        current_hierarchy_concept, root_node_of_model
                    )
                    self._update_possible_subsumers()
        return concepts_processed

    def _concept_has_been_processed_already(
        self, at_concept: AtomicConcept
    ) -> bool:
        return bool(
            self.m_possible_subsumptions.get_successors(at_concept)
        ) or self._is_unsatisfiable(at_concept)

    # ------------------------------------------------------------------
    # Model building and subsumer reading
    # ------------------------------------------------------------------

    def _build_model_for_concept(self, concept: AtomicConcept) -> Node | None:
        from hermit.model import Atom as AtomCls, Individual

        fresh_individual = Individual.create_anonymous("fresh-individual")
        checked_node: dict[Individual, Node | None] = {fresh_individual: None}
        if self.m_tableau.is_satisfiable(
            False,
            False,
            {AtomCls.create(concept, fresh_individual)},
            None,
            None,
            None,
            checked_node,
            self._get_sat_test_description(concept),
        ):
            return checked_node[fresh_individual]
        return None

    def _make_concept_unsatisfiable(self, concept: AtomicConcept) -> None:
        self._add_known_subsumption(concept, self.m_bottom_element)
        self.m_possible_subsumptions.get_successors(concept).clear()

    def _is_unsatisfiable(self, concept: AtomicConcept) -> bool:
        return self.m_bottom_element in self.m_known_subsumptions.get_successors(
            concept
        )

    def _read_known_subsumers_from_root_node(
        self, subconcept: AtomicConcept, checked_node: Node
    ) -> None:
        if not checked_node.get_canonical_node_dependency_set():
            checked_node = checked_node.get_canonical_node()
            extension_manager = self.m_tableau.get_extension_manager()
            retrieval = extension_manager.get_binary_extension_table().create_retrieval(
                [False, True], "TOTAL"
            )
            retrieval.get_bindings_buffer()[1] = checked_node
            retrieval.open()
            while not retrieval.after_last():
                concept_object = retrieval.get_tuple_buffer()[0]
                if (
                    isinstance(concept_object, AtomicConcept)
                    and retrieval.get_dependency_set() is None
                    and concept_object in self.m_elements
                ):
                    self._add_known_subsumption(
                        subconcept, concept_object
                    )
                retrieval.next()

    def _update_possible_subsumers(self) -> None:
        extension_manager = self.m_tableau.get_extension_manager()
        retrieval = extension_manager.get_binary_extension_table().create_retrieval(
            [False, False], "TOTAL"
        )
        retrieval.open()
        tuple_buffer = retrieval.get_tuple_buffer()
        while not retrieval.after_last():
            concept_object = tuple_buffer[0]
            if isinstance(concept_object, AtomicConcept) and concept_object in self.m_elements:
                atomic_concept = concept_object
                node = tuple_buffer[1]
                if node.is_active() and not node.is_blocked():
                    if not self.m_possible_subsumptions.get_successors(atomic_concept):
                        self._read_possible_subsumers_from_node_label(
                            atomic_concept, node
                        )
                    else:
                        self._prune_possible_subsumers_of_concept(
                            atomic_concept, node
                        )
            retrieval.next()

    def _prune_possible_subsumers(self) -> None:
        extension_manager = self.m_tableau.get_extension_manager()
        retrieval = extension_manager.get_binary_extension_table().create_retrieval(
            [False, False], "TOTAL"
        )
        retrieval.open()
        tuple_buffer = retrieval.get_tuple_buffer()
        while not retrieval.after_last():
            concept_object = tuple_buffer[0]
            if isinstance(concept_object, AtomicConcept) and concept_object in self.m_elements:
                node = tuple_buffer[1]
                if node.is_active() and not node.is_blocked():
                    self._prune_possible_subsumers_of_concept(
                        concept_object, node
                    )
            retrieval.next()

    def _prune_possible_subsumers_of_concept(
        self, atomic_concept: AtomicConcept, node: Node
    ) -> None:
        possible_subsumers_of_concept = set(
            self.m_possible_subsumptions.get_successors(atomic_concept)
        )
        extension_manager = self.m_tableau.get_extension_manager()
        for atomic_con in possible_subsumers_of_concept:
            if not extension_manager.contains_concept_assertion(
                atomic_con, node
            ):
                self.m_possible_subsumptions.get_successors(
                    atomic_concept
                ).discard(atomic_con)

    def _read_possible_subsumers_from_node_label(
        self, atomic_concept: AtomicConcept, node: Node
    ) -> None:
        extension_manager = self.m_tableau.get_extension_manager()
        retrieval = extension_manager.get_binary_extension_table().create_retrieval(
            [False, True], "TOTAL"
        )
        retrieval.get_bindings_buffer()[1] = node
        retrieval.open()
        while not retrieval.after_last():
            concept = retrieval.get_tuple_buffer()[0]
            if isinstance(concept, AtomicConcept) and concept in self.m_elements:
                self._add_possible_subsumption(atomic_concept, concept)
            retrieval.next()

    # ------------------------------------------------------------------
    # Hierarchy building helpers
    # ------------------------------------------------------------------

    def _build_transitively_reduced_hierarchy(
        self,
        known_subsumptions: Graph[AtomicConcept],
        elements: set[AtomicConcept],
    ) -> Hierarchy[AtomicConcept]:
        all_subsumers: dict[AtomicConcept, GraphNode[AtomicConcept]] = {}
        for element in elements:
            extended_subs: set[AtomicConcept] = set(
                known_subsumptions.get_successors(element)
            )
            extended_subs.add(self.m_top_element)
            extended_subs.add(element)
            all_subsumers[element] = GraphNode(element, extended_subs)
        all_subsumers[self.m_bottom_element] = GraphNode(
            self.m_bottom_element, set(elements)
        )
        return DeterministicClassification.build_hierarchy(
            self.m_top_element, self.m_bottom_element, all_subsumers
        )

    def _initialise_known_subsumptions_using_told_subsumers(self) -> None:
        self._initialise_known_subsumptions_using_told_subsumers_from_clauses(
            self.m_tableau.get_permanent_dl_ontology().get_dl_clauses()
        )

    def _initialise_known_subsumptions_using_told_subsumers_from_clauses(
        self, dl_clauses: set[DLClause]
    ) -> None:
        for dl_clause in dl_clauses:
            if dl_clause.head_length() == 1 and dl_clause.body_length() == 1:
                head_predicate = dl_clause.head_atom(0).predicate
                body_predicate = dl_clause.body_atom(0).predicate
                if isinstance(head_predicate, AtomicConcept) and isinstance(
                    body_predicate, AtomicConcept
                ):
                    head_concept = head_predicate
                    body_concept = body_predicate
                    if head_concept in self.m_elements and body_concept in self.m_elements:
                        self._add_known_subsumption(body_concept, head_concept)

    # ------------------------------------------------------------------
    # Enhanced traversal
    # ------------------------------------------------------------------

    def _check_unknown_subsumers_using_enhanced_traversal(
        self,
        hierarchy_relation: Relation[AtomicConcept],
        start_node: HierarchyNode[AtomicConcept],
        picked_element: AtomicConcept,
    ) -> None:
        start_search: set[HierarchyNode[AtomicConcept]] = {start_node}
        visited: set[HierarchyNode[AtomicConcept]] = set(start_search)
        to_process: list[HierarchyNode[AtomicConcept]] = list(start_search)
        while to_process:
            current = to_process.pop(0)
            subordinate_elements = current.m_child_nodes
            for subordinate_element in subordinate_elements:
                element = subordinate_element.m_representative
                if subordinate_element in visited:
                    continue
                if hierarchy_relation.does_subsume(element, picked_element):
                    self._add_known_subsumption(picked_element, element)
                    self._add_known_subsumptions(
                        picked_element, subordinate_element.m_equivalent_elements
                    )
                    if subordinate_element not in visited:
                        visited.add(subordinate_element)
                        to_process.append(subordinate_element)
                visited.add(subordinate_element)

    def _is_every_possible_subsumer_non_subsumer(
        self,
        unknown_possible_subsumers: set[AtomicConcept],
        picked_element: AtomicConcept,
        lower_bound: int,
        upper_bound: int,
    ) -> bool:
        if (
            len(unknown_possible_subsumers) > lower_bound
            and len(unknown_possible_subsumers) < upper_bound
        ):
            from hermit.model import Atom as AtomCls, Individual

            fresh_individual = Individual.create_anonymous("fresh-individual")
            subconcept_assertion = AtomCls.create(picked_element, fresh_individual)
            superconcept_assertions: set[AtomCls] = set()
            superconcepts: list[object] = []
            for unknown_sup_node in unknown_possible_subsumers:
                atom = AtomCls.create(unknown_sup_node, fresh_individual)
                superconcept_assertions.add(atom)
                superconcepts.append(atom.predicate)

            checked_node: dict[Individual, Node | None] = {
                fresh_individual: None
            }
            is_subsumed_by = not self.m_tableau.is_satisfiable(
                False,
                False,
                {subconcept_assertion},
                None,
                None,
                superconcepts,  # type: ignore[arg-type]
                checked_node,
                self._get_subsumed_by_list_test_description(
                    picked_element, superconcepts
                ),
            )
            if not is_subsumed_by:
                self._prune_possible_subsumers()
            else:
                root = checked_node[fresh_individual]
                if root is not None:
                    self._read_known_subsumers_from_root_node(
                        picked_element, root
                    )
                self.m_possible_subsumptions.get_successors(
                    picked_element
                ).difference_update(
                    self._get_all_known_subsumers(picked_element)
                )
            return not is_subsumed_by
        return False

    # ------------------------------------------------------------------
    # Subsumer management
    # ------------------------------------------------------------------

    def _get_all_known_subsumers(self, child: AtomicConcept) -> set[AtomicConcept]:
        return self.m_known_subsumptions.get_reachable_successors(child)

    def _add_known_subsumption(
        self, sub_concept: AtomicConcept, super_concept: AtomicConcept
    ) -> None:
        self.m_known_subsumptions.add_edge(sub_concept, super_concept)

    def _add_known_subsumptions(
        self, sub_concept: AtomicConcept, super_concepts: set[AtomicConcept]
    ) -> None:
        self.m_known_subsumptions.add_edges(sub_concept, super_concepts)

    def _add_possible_subsumption(
        self, sub_concept: AtomicConcept, super_concept: AtomicConcept
    ) -> None:
        self.m_possible_subsumptions.add_edge(sub_concept, super_concept)

    # ------------------------------------------------------------------
    # Reasoning task descriptions
    # ------------------------------------------------------------------

    def _get_sat_test_description(
        self, atomic_concept: AtomicConcept
    ) -> ReasoningTaskDescription:
        from hermit.tableau.reasoning_task_description import (
            ReasoningTaskDescription,
        )

        return ReasoningTaskDescription.is_concept_satisfiable(atomic_concept)

    def _get_subsumption_test_description(
        self, sub_concept: AtomicConcept, super_concept: AtomicConcept
    ) -> ReasoningTaskDescription:
        from hermit.tableau.reasoning_task_description import (
            ReasoningTaskDescription,
        )

        return ReasoningTaskDescription.is_concept_subsumed_by(
            sub_concept, super_concept
        )

    def _get_subsumed_by_list_test_description(
        self, sub_concept: AtomicConcept, superconcepts: list[object]
    ) -> ReasoningTaskDescription:
        from hermit.tableau.reasoning_task_description import (
            ReasoningTaskDescription,
        )

        return ReasoningTaskDescription.is_concept_subsumed_by_list(
            sub_concept, *superconcepts
        )


# ---------------------------------------------------------------------------
# Internal helper: the subsumption relation
# ---------------------------------------------------------------------------


class _ClassificationRelation(Relation[AtomicConcept]):
    """Adapts QuasiOrderClassification as a HierarchySearch relation."""

    def __init__(self, qoc: QuasiOrderClassification) -> None:
        self._qoc = qoc

    def does_subsume(self, parent: AtomicConcept, child: AtomicConcept) -> bool:
        all_known_subsumers = self._qoc._get_all_known_subsumers(child)
        if parent in all_known_subsumers:
            return True
        if parent not in self._qoc.m_possible_subsumptions.get_successors(child):
            return False

        from hermit.model import Atom as AtomCls, Individual

        fresh_individual = Individual.create_anonymous("fresh-individual")
        checked_node: dict[Individual, Node | None] = {fresh_individual: None}
        is_subsumed_by = not self._qoc.m_tableau.is_satisfiable(
            True,
            False,
            {AtomCls.create(child, fresh_individual)},
            None,
            {AtomCls.create(parent, fresh_individual)},
            None,
            checked_node,
            self._qoc._get_subsumption_test_description(child, parent),
        )
        if not is_subsumed_by:
            self._qoc._prune_possible_subsumers()
        root = checked_node[fresh_individual]
        if root is not None:
            self._qoc._read_known_subsumers_from_root_node(child, root)
        self._qoc.m_possible_subsumptions.get_successors(child).difference_update(
            self._qoc._get_all_known_subsumers(child)
        )
        return is_subsumed_by
