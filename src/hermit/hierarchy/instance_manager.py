"""Instance manager for HermiT realisation and instance retrieval.

Faithful port of ``org.semanticweb.HermiT.hierarchy.InstanceManager``.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Any

from hermit.graph import Graph
from hermit.hierarchy.atomic_concept_element import AtomicConceptElement
from hermit.hierarchy.deterministic_classification import (
    DeterministicClassification,
    GraphNode,
)
from hermit.hierarchy.hierarchy import Hierarchy, Transformer
from hermit.hierarchy.hierarchy_node import HierarchyNode
from hermit.hierarchy.role_element_manager import RoleElement, RoleElementManager
from hermit.model import (
    AtomicConcept,
    AtomicRole,
    Individual,
    Inequality,
    InverseRole,
    Prefixes,
    Role,
)

if TYPE_CHECKING:
    from hermit.model import DLClause
    from hermit.tableau.interrupt_flag import InterruptFlag
    from hermit.tableau.node import Node
    from hermit.tableau.tableau import Tableau


class InstanceManager:
    """Manages instance retrieval and realisation for concepts and roles.

    The instance manager maintains the mapping between ontology individuals
    and tableau nodes, tracks known and possible instances for each concept
    and role, and provides methods for lazy realisation (resolving possible
    instances to known instances on demand).
    """

    THRESHOLD_FOR_ADDITIONAL_AXIOMS = 10000

    def __init__(
        self,
        interrupt_flag: InterruptFlag,
        reasoner: Any,
        atomic_concept_hierarchy: Hierarchy[AtomicConcept] | None,
        object_role_hierarchy: Hierarchy[Role] | None,
    ) -> None:
        self.m_interrupt_flag = interrupt_flag
        self.m_interrupt_flag.start_task()
        try:
            self.m_reasoner = reasoner
            self.m_tableau_monitor = self.m_reasoner.get_tableau().get_tableau_monitor()
            self.m_classes_initialised = False
            self.m_current_concept_hierarchy: Hierarchy[AtomicConcept] | None = None
            dlo = self.m_reasoner.get_dl_ontology()
            self.m_individuals = list(dlo.get_all_individuals())
            self.m_complex_roles: set[AtomicRole] = set()
            self.m_individual_to_equivalence_class: dict[
                Individual, set[Individual]
            ] = {}
            self.m_nodes_for_individuals: dict[Individual, Node | None] = {}
            for individual in self.m_individuals:
                self.m_nodes_for_individuals[individual] = None
                equivalent_individuals: set[Individual] = {individual}
                self.m_individual_to_equivalence_class[
                    individual
                ] = equivalent_individuals
                self.m_interrupt_flag.check_interrupt()

            self.m_individuals_for_nodes: dict[Node, Individual] = {}
            self.m_canonical_node_to_det_merged_nodes: dict[Node, set[Node]] = {}
            self.m_canonical_node_to_non_det_merged_nodes: dict[
                Node, set[Node]
            ] = {}
            self.m_individual_to_possible_equivalence_class: (
                dict[set[Individual], set[set[Individual]]] | None
            ) = None

            self.m_top_concept = AtomicConcept.THING
            self.m_bottom_concept = AtomicConcept.NOTHING
            self.m_concept_to_element: dict[
                AtomicConcept, AtomicConceptElement
            ] = {}
            self.m_concept_to_element[self.m_top_concept] = AtomicConceptElement(
                None, None
            )
            known_concept_subsumptions: Graph[AtomicConcept] | None = None
            atomic_concepts: set[AtomicConcept] | None = None
            if atomic_concept_hierarchy is not None:
                self.set_to_classified_concept_hierarchy(atomic_concept_hierarchy)
            else:
                known_concept_subsumptions = Graph()
                atomic_concepts = set()
                atomic_concepts.add(self.m_top_concept)
                atomic_concepts.add(self.m_bottom_concept)
                for atomic_concept in dlo.get_all_atomic_concepts():
                    if not Prefixes.is_internal_iri(atomic_concept.iri):
                        atomic_concepts.add(atomic_concept)
                        self._add_known_concept_subsumption(
                            known_concept_subsumptions,
                            atomic_concept,
                            atomic_concept,
                        )
                        self._add_known_concept_subsumption(
                            known_concept_subsumptions,
                            atomic_concept,
                            self.m_top_concept,
                        )
                        self._add_known_concept_subsumption(
                            known_concept_subsumptions,
                            self.m_bottom_concept,
                            atomic_concept,
                        )
                    self.m_interrupt_flag.check_interrupt()
                self._add_known_concept_subsumption(
                    known_concept_subsumptions,
                    self.m_bottom_concept,
                    self.m_bottom_concept,
                )

            self.m_role_element_manager = RoleElementManager()
            known_role_subsumptions: Graph[Role] | None = None
            self.m_top_role_element = self.m_role_element_manager.get_role_element(
                AtomicRole.TOP_OBJECT_ROLE
            )
            self.m_bottom_role_element = self.m_role_element_manager.get_role_element(
                AtomicRole.BOTTOM_OBJECT_ROLE
            )
            self.m_uses_inverse_roles = dlo.has_inverse_roles()
            roles: set[Role] | None = None
            complex_roles = dlo.get_all_complex_object_roles()
            if object_role_hierarchy is not None:
                self.set_to_classified_role_hierarchy(object_role_hierarchy)
                for role in complex_roles:
                    if (
                        isinstance(role, AtomicRole)
                        and role != AtomicRole.TOP_OBJECT_ROLE
                        and role != AtomicRole.BOTTOM_OBJECT_ROLE
                    ):
                        self.m_complex_roles.add(role)
            else:
                known_role_subsumptions = Graph()
                roles = set()
                roles.add(AtomicRole.TOP_OBJECT_ROLE)
                roles.add(AtomicRole.BOTTOM_OBJECT_ROLE)
                roles.update(dlo.get_all_atomic_object_roles())
                for role in roles:
                    self._add_known_role_subsumption(
                        known_role_subsumptions, role, role
                    )
                    self._add_known_role_subsumption(
                        known_role_subsumptions, role, AtomicRole.TOP_OBJECT_ROLE
                    )
                    self._add_known_role_subsumption(
                        known_role_subsumptions,
                        AtomicRole.BOTTOM_OBJECT_ROLE,
                        role,
                    )
                    if (
                        complex_roles.__contains__(role)
                        and isinstance(role, AtomicRole)
                        and role != AtomicRole.TOP_OBJECT_ROLE
                        and role != AtomicRole.BOTTOM_OBJECT_ROLE
                    ):
                        self.m_complex_roles.add(role)
                    self.m_interrupt_flag.check_interrupt()
                self._add_known_role_subsumption(
                    known_role_subsumptions,
                    AtomicRole.BOTTOM_OBJECT_ROLE,
                    AtomicRole.BOTTOM_OBJECT_ROLE,
                )
            if atomic_concept_hierarchy is None or object_role_hierarchy is None:
                self._update_known_subsumptions_using_told_subsumers(
                    dlo.get_dl_clauses(),
                    known_concept_subsumptions,
                    atomic_concepts,
                    known_role_subsumptions,
                    roles,
                )
            if atomic_concept_hierarchy is None:
                self.m_current_concept_hierarchy = (
                    self._build_transitively_reduced_concept_hierarchy(
                        known_concept_subsumptions
                    )
                )
            else:
                self.m_current_concept_hierarchy = atomic_concept_hierarchy
            if object_role_hierarchy is None:
                self.m_current_role_hierarchy = (
                    self._build_transitively_reduced_role_hierarchy(
                        known_role_subsumptions
                    )
                )
            else:
                self.m_current_role_hierarchy = self._transform_role_hierarchy(
                    object_role_hierarchy
                )

            extension_manager = self.m_reasoner.get_tableau().get_extension_manager()
            self.m_binary_retrieval_0_bound = (
                extension_manager.get_binary_extension_table().create_retrieval(
                    [True, False], "TOTAL"
                )
            )
            self.m_binary_retrieval_1_bound = (
                extension_manager.get_binary_extension_table().create_retrieval(
                    [False, True], "TOTAL"
                )
            )
            self.m_binary_retrieval_01_bound = (
                extension_manager.get_binary_extension_table().create_retrieval(
                    [True, True], "TOTAL"
                )
            )
            self.m_ternary_retrieval_1_bound = (
                extension_manager.get_ternary_extension_table().create_retrieval(
                    [False, True, False], "TOTAL"
                )
            )
            self.m_ternary_retrieval_0_bound = (
                extension_manager.get_ternary_extension_table().create_retrieval(
                    [True, False, False], "TOTAL"
                )
            )
            self.m_ternary_retrieval_012_bound = (
                extension_manager.get_ternary_extension_table().create_retrieval(
                    [True, True, True], "TOTAL"
                )
            )
            self.m_is_inconsistent = False
            self.m_realization_completed = False
            self.m_role_realization_completed = False
            self.m_uses_classified_concept_hierarchy = (
                atomic_concept_hierarchy is not None
            )
            self.m_uses_classified_object_role_hierarchy = (
                object_role_hierarchy is not None
            )
            self.m_classes_initialised = False
            self.m_properties_initialised = False
            self.m_reading_off_found_possible_concept_instance = False
            self.m_reading_off_found_possible_property_instance = False
            self.m_current_individual_index = 0
        finally:
            self.m_interrupt_flag.end_task()

    # ------------------------------------------------------------------
    # Known subsumption helpers
    # ------------------------------------------------------------------

    def _add_known_concept_subsumption(
        self,
        known_subsumptions: Graph[AtomicConcept],
        sub_concept: AtomicConcept,
        super_concept: AtomicConcept,
    ) -> None:
        known_subsumptions.add_edge(sub_concept, super_concept)

    def _add_known_role_subsumption(
        self,
        known_subsumptions: Graph[Role],
        sub_role: Role,
        super_role: Role,
    ) -> None:
        known_subsumptions.add_edge(sub_role, super_role)
        if self.m_uses_inverse_roles:
            known_subsumptions.add_edge(
                sub_role.get_inverse(), super_role.get_inverse()
            )

    def _update_known_subsumptions_using_told_subsumers(
        self,
        dl_clauses: set[DLClause],
        known_concept_subsumptions: Graph[AtomicConcept] | None,
        concepts: set[AtomicConcept] | None,
        known_role_subsumptions: Graph[Role] | None,
        roles: set[Role] | None,
    ) -> None:
        requires_concept_subsumers = known_concept_subsumptions is not None
        requires_role_subsumers = known_role_subsumptions is not None
        if requires_concept_subsumers or requires_role_subsumers:
            for dl_clause in dl_clauses:
                if dl_clause.head_length() == 1 and dl_clause.body_length() == 1:
                    head_predicate = dl_clause.head_atom(0).predicate
                    body_predicate = dl_clause.body_atom(0).predicate
                    if (
                        requires_concept_subsumers
                        and isinstance(head_predicate, AtomicConcept)
                        and isinstance(body_predicate, AtomicConcept)
                    ):
                        head_concept = head_predicate
                        body_concept = body_predicate
                        if concepts is not None and head_concept in concepts and body_concept in concepts:
                            self._add_known_concept_subsumption(
                                known_concept_subsumptions,
                                body_concept,
                                head_concept,
                            )
                    elif (
                        requires_role_subsumers
                        and isinstance(head_predicate, AtomicRole)
                        and isinstance(body_predicate, AtomicRole)
                    ):
                        head_role = head_predicate
                        body_role = body_predicate
                        if roles is not None and head_role in roles and body_role in roles:
                            if (
                                dl_clause.body_atom(0).argument(0)
                                != dl_clause.head_atom(0).argument(0)
                            ):
                                self._add_known_role_subsumption(
                                    known_role_subsumptions,
                                    InverseRole.create(body_role),
                                    head_role,
                                )
                            else:
                                self._add_known_role_subsumption(
                                    known_role_subsumptions, body_role, head_role
                                )
                self.m_interrupt_flag.check_interrupt()

    # ------------------------------------------------------------------
    # Concept hierarchy management
    # ------------------------------------------------------------------

    def _build_transitively_reduced_concept_hierarchy(
        self, known_subsumptions: Graph[AtomicConcept] | None
    ) -> Hierarchy[AtomicConcept]:
        all_subsumers: dict[AtomicConcept, GraphNode[AtomicConcept]] = {}
        for element in known_subsumptions.get_elements():  # type: ignore[union-attr]
            all_subsumers[element] = GraphNode(
                element, known_subsumptions.get_successors(element)
            )
        self.m_interrupt_flag.check_interrupt()
        return DeterministicClassification.build_hierarchy(
            self.m_top_concept, self.m_bottom_concept, all_subsumers
        )

    def set_to_classified_concept_hierarchy(
        self, atomic_concept_hierarchy: Hierarchy[AtomicConcept]
    ) -> None:
        if getattr(self, 'm_current_concept_hierarchy', None) is not atomic_concept_hierarchy:
            self.m_current_concept_hierarchy = atomic_concept_hierarchy
            if self.m_classes_initialised and self.m_individuals:
                for node in self.m_current_concept_hierarchy.get_all_nodes_set():
                    if node.m_representative != self.m_bottom_concept:
                        representative_concept = node.get_representative()
                        known: set[Individual] = set()
                        possible: set[Individual] | None = None
                        for concept in node.get_equivalent_elements():
                            if concept in self.m_concept_to_element:
                                element = self.m_concept_to_element[concept]
                                known.update(element.m_known_instances)
                                if possible is None:
                                    possible = set(element.m_possible_instances)
                                else:
                                    possible.intersection_update(
                                        element.m_possible_instances
                                    )
                                del self.m_concept_to_element[concept]
                        if possible is not None:
                            possible.difference_update(known)
                        if known or possible is not None or representative_concept == self.m_top_concept:
                            self.m_concept_to_element[representative_concept] = (
                                AtomicConceptElement(known, possible)
                            )
                # Clean up known and possibles
                to_process: deque[HierarchyNode[AtomicConcept]] = deque(
                    self.m_current_concept_hierarchy.m_bottom_node.m_parent_nodes
                )
                while to_process:
                    current = to_process.popleft()
                    current_concept = current.get_representative()
                    current_element = self.m_concept_to_element.get(current_concept)
                    if current_element is not None:
                        ancestors = current.get_ancestor_nodes()
                        ancestors.discard(current)
                        for ancestor in ancestors:
                            ancestor_concept = ancestor.get_representative()
                            ancestor_element = self.m_concept_to_element.get(
                                ancestor_concept
                            )
                            if ancestor_element is not None:
                                ancestor_element.m_known_instances.difference_update(
                                    current_element.m_known_instances
                                )
                                ancestor_element.m_possible_instances.difference_update(
                                    current_element.m_known_instances
                                )
                                ancestor_element.m_possible_instances.difference_update(
                                    current_element.m_possible_instances
                                )
                        for parent in current.m_parent_nodes:
                            if parent not in to_process:
                                to_process.append(parent)
                    self.m_interrupt_flag.check_interrupt()
            self.m_uses_classified_concept_hierarchy = True

    # ------------------------------------------------------------------
    # Role hierarchy management
    # ------------------------------------------------------------------

    def _build_transitively_reduced_role_hierarchy(
        self, known_subsumptions: Graph[Role] | None
    ) -> Hierarchy[RoleElement]:
        all_subsumers: dict[Role, GraphNode[Role]] = {}
        for role in known_subsumptions.get_elements():  # type: ignore[union-attr]
            all_subsumers[role] = GraphNode(
                role, known_subsumptions.get_successors(role)
            )
        self.m_interrupt_flag.check_interrupt()
        built = DeterministicClassification.build_hierarchy(
            AtomicRole.TOP_OBJECT_ROLE, AtomicRole.BOTTOM_OBJECT_ROLE, all_subsumers
        )
        return self._transform_role_hierarchy(built)

    def _transform_role_hierarchy(
        self, role_hierarchy: Hierarchy[Role]
    ) -> Hierarchy[RoleElement]:
        new_hierarchy = self._remove_inverses(role_hierarchy)

        class _RoleTransformer(Transformer[Role, RoleElement]):
            def __init__(self, outer: InstanceManager) -> None:
                self._outer = outer

            def transform(self, role: Role) -> RoleElement:
                self._outer.m_interrupt_flag.check_interrupt()
                if not isinstance(role, AtomicRole):
                    raise ValueError(
                        "Internal error: The instance manager should only use "
                        f"atomic roles, but here we got a hierarchy element for "
                        f"an inverse role: {role}"
                    )
                return self._outer.m_role_element_manager.get_role_element(role)

            def determine_representative(
                self,
                old_representative: Role,
                new_equivalent_elements: set[RoleElement],
            ) -> RoleElement:
                representative = self.transform(old_representative)
                for new_equiv in new_equivalent_elements:
                    if new_equiv != representative:
                        for (
                            individual
                        ) in new_equiv.m_known_relations:
                            successors = representative.m_known_relations.get(
                                individual
                            )
                            if successors is None:
                                successors = set()
                                representative.m_known_relations[
                                    individual
                                ] = successors
                            successors.update(
                                new_equiv.m_known_relations[individual]
                            )
                        for individual in new_equiv.m_possible_relations:
                            successors = representative.m_possible_relations.get(
                                individual
                            )
                            if successors is not None:
                                successors.intersection_update(
                                    new_equiv.m_possible_relations[individual]
                                )
                        new_equiv.m_known_relations.clear()
                        new_equiv.m_possible_relations.clear()
                self._outer.m_interrupt_flag.check_interrupt()
                return representative

        return new_hierarchy.transform(_RoleTransformer(self), None)

    def _remove_inverses(self, hierarchy: Hierarchy[Role]) -> Hierarchy[AtomicRole]:
        all_subsumers: dict[AtomicRole, GraphNode[AtomicRole]] = {}
        to_process: set[AtomicRole] = {self.m_bottom_role_element.m_role}
        visited: set[AtomicRole] = set()
        while to_process:
            current = next(iter(to_process))
            visited.add(current)
            current_node = hierarchy.get_node_for_element(current)
            atomic_representatives: set[AtomicRole] = set()
            self._find_next_hierarchy_node_with_atomic(
                atomic_representatives, current_node
            )
            all_subsumers[current] = GraphNode(current, atomic_representatives)
            to_process.update(atomic_representatives)
            to_process.difference_update(visited)
            self.m_interrupt_flag.check_interrupt()

        from hermit.hierarchy.deterministic_classification import (
            DeterministicClassification,
        )

        new_hierarchy = DeterministicClassification.build_hierarchy(
            self.m_top_role_element.m_role,
            self.m_bottom_role_element.m_role,
            all_subsumers,
        )
        for element in new_hierarchy.m_nodes_by_elements:
            old_node = hierarchy.get_node_for_element(element)
            new_node = new_hierarchy.get_node_for_element(element)
            if old_node is not None and new_node is not None:
                for equivalent in old_node.m_equivalent_elements:
                    if isinstance(equivalent, AtomicRole):
                        new_node.m_equivalent_elements.add(equivalent)
            self.m_interrupt_flag.check_interrupt()
        return new_hierarchy

    def set_to_classified_role_hierarchy(
        self, role_hierarchy: Hierarchy[Role]
    ) -> None:
        self.m_current_role_hierarchy = self._transform_role_hierarchy(
            role_hierarchy
        )
        if self.m_properties_initialised and self.m_individuals:
            to_process: deque[HierarchyNode[RoleElement]] = deque(
                [self.m_current_role_hierarchy.m_bottom_node]
            )
            while to_process:
                current = to_process.popleft()
                current_representative = current.get_representative()
                ancestors = current.get_ancestor_nodes()
                ancestors.discard(current)
                for ancestor in ancestors:
                    ancestor_representative = ancestor.m_representative
                    ancestor_known_relations = (
                        ancestor_representative.m_known_relations
                    )
                    ancestor_possible_relations = (
                        ancestor_representative.m_possible_relations
                    )
                    for individual in current_representative.m_known_relations:
                        successors = ancestor_known_relations.get(individual)
                        if successors is not None:
                            successors.difference_update(
                                current_representative.m_known_relations.get(
                                    individual, set()
                                )
                            )
                            if not successors:
                                ancestor_known_relations.pop(individual, None)
                        successors = ancestor_possible_relations.get(individual)
                        if successors is not None:
                            successors.difference_update(
                                current_representative.m_known_relations.get(
                                    individual, set()
                                )
                            )
                            if not successors:
                                ancestor_possible_relations.pop(individual, None)
                    for individual in current_representative.m_possible_relations:
                        successors = ancestor_possible_relations.get(individual)
                        if successors is not None:
                            successors.difference_update(
                                current_representative.m_possible_relations.get(
                                    individual, set()
                                )
                            )
                            if not successors:
                                ancestor_possible_relations.pop(individual, None)
                for parent in current.m_parent_nodes:
                    if parent not in to_process:
                        to_process.append(parent)
                self.m_interrupt_flag.check_interrupt()
        self.m_uses_classified_object_role_hierarchy = True

    def _find_next_hierarchy_node_with_atomic(
        self,
        atomic_representatives: set[AtomicRole],
        current: HierarchyNode[Role] | None,
    ) -> None:
        if current is None:
            return
        for successor in current.m_parent_nodes:
            suitable: set[AtomicRole] = set()
            for role in successor.m_equivalent_elements:
                if isinstance(role, AtomicRole):
                    suitable.add(role)
            if suitable:
                atomic_representatives.add(next(iter(suitable)))
            elif successor != current:
                self._find_next_hierarchy_node_with_atomic(
                    atomic_representatives, successor
                )

    # ------------------------------------------------------------------
    # Read-off methods (concept instances)
    # ------------------------------------------------------------------

    def initialize_know_and_possible_class_instances(
        self,
        tableau: Tableau,
        monitor: Any | None,
        completed_steps: int,
        steps: int,
    ) -> int:
        if not self.m_classes_initialised:
            self.m_interrupt_flag.start_task()
            try:
                self._initialize_individuals_for_nodes()
                if not self.m_properties_initialised:
                    self._initialize_same_as()
                completed_steps = self._read_off_class_instances_by_individual(
                    tableau, monitor, completed_steps, steps
                )
                if (
                    not self.m_reading_off_found_possible_concept_instance
                    and self.m_uses_classified_concept_hierarchy
                ):
                    self.m_realization_completed = True
                self.m_classes_initialised = True
                self.m_individuals_for_nodes.clear()
                self.m_canonical_node_to_det_merged_nodes.clear()
                self.m_canonical_node_to_non_det_merged_nodes.clear()
            finally:
                self.m_interrupt_flag.end_task()
        return completed_steps

    def _read_off_class_instances_by_individual(
        self,
        tableau: Tableau,
        monitor: Any | None,
        completed_steps: int,
        steps: int,
    ) -> int:
        for ind in self.m_individuals:
            node_for_individual = self.m_nodes_for_individuals.get(ind)
            has_type = False
            if node_for_individual is not None:
                has_type = self._read_off_types(ind, node_for_individual)
            if not has_type:
                top_element = self.m_concept_to_element.get(self.m_top_concept)
                if top_element is None:
                    top_element = AtomicConceptElement(None, None)
                    self.m_concept_to_element[self.m_top_concept] = top_element
                top_element.m_known_instances.add(ind)
            completed_steps += 1
            if monitor is not None:
                monitor.reasoner_task_progress_changed(completed_steps, steps)
            self.m_interrupt_flag.check_interrupt()
        return completed_steps

    def _read_off_types(self, ind: Individual, node_for_individual: Node) -> bool:
        has_been_added = False
        self.m_binary_retrieval_1_bound.get_bindings_buffer()[1] = (
            node_for_individual.get_canonical_node()
        )
        self.m_binary_retrieval_1_bound.open()
        tuple_buffer = self.m_binary_retrieval_1_bound.get_tuple_buffer()
        while not self.m_binary_retrieval_1_bound.after_last():
            predicate = tuple_buffer[0]
            if isinstance(predicate, AtomicConcept):
                atomic_concept = predicate
                if (
                    atomic_concept != self.m_top_concept
                    and not Prefixes.is_internal_iri(atomic_concept.iri)
                ):
                    node = self.m_current_concept_hierarchy.get_node_for_element(
                        atomic_concept
                    )
                    if node is not None:
                        representative = node.get_representative()
                        element = self.m_concept_to_element.get(representative)
                        if element is None:
                            element = AtomicConceptElement(None, None)
                            self.m_concept_to_element[representative] = element
                        has_been_added = True
                        if self.m_binary_retrieval_1_bound.get_dependency_set() is None:
                            self._add_known_concept_instance(
                                node, element, ind
                            )
                        else:
                            self._add_possible_concept_instance(
                                node, element, ind
                            )
                            self.m_reading_off_found_possible_concept_instance = True
            self.m_interrupt_flag.check_interrupt()
            self.m_binary_retrieval_1_bound.next()
        return has_been_added

    def _add_known_concept_instance(
        self,
        current_node: HierarchyNode[AtomicConcept],
        element: AtomicConceptElement,
        instance: Individual,
    ) -> None:
        nodes = current_node.get_descendant_nodes()
        for node in nodes:
            descendant_element = self.m_concept_to_element.get(
                node.get_representative()
            )
            if (
                descendant_element is not None
                and instance in descendant_element.m_known_instances
            ):
                return
            self.m_interrupt_flag.check_interrupt()
        element.m_known_instances.add(instance)
        nodes = current_node.get_ancestor_nodes()
        nodes.discard(current_node)
        for node in nodes:
            ancestor_element = self.m_concept_to_element.get(
                node.get_representative()
            )
            if ancestor_element is not None:
                ancestor_element.m_known_instances.discard(instance)
                ancestor_element.m_possible_instances.discard(instance)

    def _add_possible_concept_instance(
        self,
        current_node: HierarchyNode[AtomicConcept],
        element: AtomicConceptElement,
        instance: Individual,
    ) -> None:
        nodes = current_node.get_descendant_nodes()
        for node in nodes:
            descendant_element = self.m_concept_to_element.get(
                node.get_representative()
            )
            if descendant_element is not None and (
                instance in descendant_element.m_known_instances
                or instance in descendant_element.m_possible_instances
            ):
                return
            self.m_interrupt_flag.check_interrupt()
        element.m_possible_instances.add(instance)
        nodes = current_node.get_ancestor_nodes()
        nodes.discard(current_node)
        for node in nodes:
            ancestor_element = self.m_concept_to_element.get(
                node.get_representative()
            )
            if ancestor_element is not None:
                ancestor_element.m_possible_instances.discard(instance)
                if (
                    not ancestor_element.m_possible_instances
                    and not ancestor_element.m_known_instances
                    and node.get_representative() != self.m_top_concept
                ):
                    self.m_concept_to_element.pop(node.get_representative(), None)
            self.m_interrupt_flag.check_interrupt()

    # ------------------------------------------------------------------
    # Read-off methods (property instances)
    # ------------------------------------------------------------------

    def initialize_know_and_possible_property_instances(
        self,
        tableau: Tableau,
        monitor: Any | None,
        start_individual_index: int,
        completed_steps: int,
        steps: int,
    ) -> int:
        if not self.m_properties_initialised:
            self.m_interrupt_flag.start_task()
            try:
                self._initialize_individuals_for_nodes()
                if not self.m_classes_initialised:
                    self._initialize_same_as()
                completed_steps = self._read_off_property_instances_by_individual(
                    tableau,
                    self.m_individuals_for_nodes,
                    monitor,
                    completed_steps,
                    steps,
                    start_individual_index,
                )
                if self.m_current_individual_index >= len(self.m_individuals) - 1:
                    if not self.m_reading_off_found_possible_property_instance:
                        self.m_role_realization_completed = True
                    self.m_properties_initialised = True
                self.m_individuals_for_nodes.clear()
            finally:
                self.m_interrupt_flag.end_task()
        return completed_steps

    def _read_off_property_instances_by_individual(
        self,
        tableau: Tableau,
        individuals_for_nodes: dict[Node, Individual],
        monitor: Any | None,
        completed_steps: int,
        steps: int,
        start_individual_index: int,
    ) -> int:
        end_index = (
            len(self.m_individuals)
            if start_individual_index == 0
            else self.m_current_individual_index
        )
        for index in range(start_individual_index, end_index):
            ind = self.m_individuals[index]
            node_for_individual = self.m_nodes_for_individuals.get(ind)
            if start_individual_index == 0:
                if node_for_individual is not None and not node_for_individual.is_merged():
                    self._read_off_property_instances(node_for_individual)
                completed_steps += 1
                if monitor is not None:
                    monitor.reasoner_task_progress_changed(
                        completed_steps, steps
                    )
            if index < self.m_current_individual_index:
                completed_steps = self._read_off_complex_role_successors(
                    ind, node_for_individual, monitor, completed_steps, steps
                )
            self.m_interrupt_flag.check_interrupt()
        return completed_steps

    def _initialize_individuals_for_nodes(self) -> None:
        for ind in self.m_individuals:
            node = self.m_nodes_for_individuals.get(ind)
            if node is not None:
                self.m_individuals_for_nodes[node] = ind
                if node.is_merged():
                    canonical_node = node.get_canonical_node()
                    if node.get_canonical_node_dependency_set() is None:
                        merged = self.m_canonical_node_to_det_merged_nodes.get(
                            canonical_node
                        )
                        if merged is None:
                            merged = set()
                            self.m_canonical_node_to_det_merged_nodes[
                                canonical_node
                            ] = merged
                        merged.add(node)
                    else:
                        merged = self.m_canonical_node_to_non_det_merged_nodes.get(
                            canonical_node
                        )
                        if merged is None:
                            merged = set()
                            self.m_canonical_node_to_non_det_merged_nodes[
                                canonical_node
                            ] = merged
                        merged.add(node)
            self.m_interrupt_flag.check_interrupt()

    def _initialize_same_as(self) -> None:
        self.m_individual_to_possible_equivalence_class: dict[
            set[Individual], set[set[Individual]]
        ] = {}
        for node in self.m_individuals_for_nodes:
            merged_into = node.get_merged_into()
            if merged_into is not None:
                individual1 = self.m_individuals_for_nodes.get(node)
                individual2 = self.m_individuals_for_nodes.get(merged_into)
                if individual1 is None or individual2 is None:
                    continue
                individual1_equivalences = (
                    self.m_individual_to_equivalence_class.get(individual1)
                )
                individual2_equivalences = (
                    self.m_individual_to_equivalence_class.get(individual2)
                )
                if individual1_equivalences is None or individual2_equivalences is None:
                    continue
                if node.get_merged_into_dependency_set() is None:
                    individual1_equivalences.update(individual2_equivalences)
                    self.m_individual_to_equivalence_class[
                        individual2
                    ] = individual1_equivalences
                else:
                    possible_equivalence_classes = (
                        self.m_individual_to_possible_equivalence_class.get(
                            individual1_equivalences
                        )
                    )
                    if possible_equivalence_classes is None:
                        possible_equivalence_classes = set()
                        self.m_individual_to_possible_equivalence_class[
                            individual1_equivalences
                        ] = possible_equivalence_classes
                    possible_equivalence_classes.add(individual2_equivalences)
            self.m_interrupt_flag.check_interrupt()

    def _read_off_property_instances(self, node_for_individual: Node) -> None:
        self.m_ternary_retrieval_1_bound.get_bindings_buffer()[1] = (
            node_for_individual
        )
        self.m_ternary_retrieval_1_bound.open()
        tuple_buffer = self.m_ternary_retrieval_1_bound.get_tuple_buffer()
        while not self.m_ternary_retrieval_1_bound.after_last():
            role_object = tuple_buffer[0]
            successor_node = tuple_buffer[2]
            if (
                isinstance(role_object, AtomicRole)
                and not successor_node.is_merged()
                and successor_node.get_node_type().value == "named_node"
                and successor_node in self.m_individuals_for_nodes
                and successor_node.is_active()
            ):
                atomic_role = role_object
                if (
                    atomic_role != AtomicRole.TOP_OBJECT_ROLE
                    and atomic_role in self.m_role_element_manager.m_role_to_element
                ):
                    role_elem = self.m_role_element_manager.get_role_element(
                        atomic_role
                    )
                    hierarchy_node = self.m_current_role_hierarchy.get_node_for_element(
                        role_elem
                    )
                    if hierarchy_node is not None:
                        representative = hierarchy_node.get_representative()
                        equivalent_to_node = (
                            self.m_canonical_node_to_det_merged_nodes.get(
                                node_for_individual
                            )
                        )
                        if equivalent_to_node is None:
                            equivalent_to_node = set()
                        equivalent_to_node.add(node_for_individual)
                        possibly_equivalent_to_node = (
                            self.m_canonical_node_to_non_det_merged_nodes.get(
                                node_for_individual
                            )
                        )
                        if possibly_equivalent_to_node is None:
                            possibly_equivalent_to_node = set()

                        equivalent_to_successor = (
                            self.m_canonical_node_to_det_merged_nodes.get(
                                successor_node
                            )
                        )
                        if equivalent_to_successor is None:
                            equivalent_to_successor = set()
                        equivalent_to_successor.add(successor_node)
                        possibly_equivalent_to_successor = (
                            self.m_canonical_node_to_non_det_merged_nodes.get(
                                successor_node
                            )
                        )
                        if possibly_equivalent_to_successor is None:
                            possibly_equivalent_to_successor = set()

                        for source_node in equivalent_to_node:
                            source_individual = (
                                self.m_individuals_for_nodes.get(source_node)
                            )
                            if source_individual is None:
                                continue
                            for target_node in equivalent_to_successor:
                                target_individual = (
                                    self.m_individuals_for_nodes.get(target_node)
                                )
                                if target_individual is None:
                                    continue
                                if (
                                    self.m_ternary_retrieval_1_bound.get_dependency_set()
                                    is None
                                ):
                                    self._add_known_role_instance(
                                        representative,
                                        source_individual,
                                        target_individual,
                                    )
                                else:
                                    self.m_reading_off_found_possible_property_instance = (
                                        True
                                    )
                                    self._add_possible_role_instance(
                                        representative,
                                        source_individual,
                                        target_individual,
                                    )
                            for target_node in possibly_equivalent_to_successor:
                                target_individual = (
                                    self.m_individuals_for_nodes.get(target_node)
                                )
                                if target_individual is None:
                                    continue
                                self.m_reading_off_found_possible_property_instance = (
                                    True
                                )
                                self._add_possible_role_instance(
                                    representative,
                                    source_individual,
                                    target_individual,
                                )

                        for source_node in possibly_equivalent_to_node:
                            source_individual = (
                                self.m_individuals_for_nodes.get(source_node)
                            )
                            if source_individual is None:
                                continue
                            possibly_equivalent_to_successor.update(
                                equivalent_to_successor
                            )
                            for target_node in possibly_equivalent_to_successor:
                                target_individual = (
                                    self.m_individuals_for_nodes.get(target_node)
                                )
                                if target_individual is None:
                                    continue
                                self.m_reading_off_found_possible_property_instance = (
                                    True
                                )
                                self._add_possible_role_instance(
                                    representative,
                                    source_individual,
                                    target_individual,
                                )
            self.m_interrupt_flag.check_interrupt()
            self.m_ternary_retrieval_1_bound.next()

    def _read_off_complex_role_successors(
        self,
        ind: Individual,
        node_for_individual: Node | None,
        monitor: Any | None,
        completed_steps: int,
        steps: int,
    ) -> int:
        ind_iri = ind.iri
        for atomic_role in self.m_complex_roles:
            concept_for_role = AtomicConcept.create(
                f"internal:individual-concept#{atomic_role.iri}#{ind_iri}"
            )
            self.m_binary_retrieval_0_bound.get_bindings_buffer()[0] = (
                concept_for_role
            )
            self.m_binary_retrieval_0_bound.open()
            tuple_buffer = self.m_binary_retrieval_0_bound.get_tuple_buffer()
            while not self.m_binary_retrieval_0_bound.after_last():
                node = tuple_buffer[1]
                if (
                    node.is_active()
                    and node.get_node_type().value == "named_node"
                    and node in self.m_individuals_for_nodes
                ):
                    role_elem = self.m_role_element_manager.get_role_element(
                        atomic_role
                    )
                    hierarchy_node = self.m_current_role_hierarchy.get_node_for_element(
                        role_elem
                    )
                    if hierarchy_node is not None:
                        representative = hierarchy_node.get_representative()
                        equivalent_to_successor = (
                            self.m_canonical_node_to_det_merged_nodes.get(node)
                        )
                        if equivalent_to_successor is None:
                            equivalent_to_successor = set()
                        equivalent_to_successor.add(node)
                        possibly_equivalent_to_successor = (
                            self.m_canonical_node_to_non_det_merged_nodes.get(node)
                        )
                        if possibly_equivalent_to_successor is None:
                            possibly_equivalent_to_successor = set()
                        for target_node in equivalent_to_successor:
                            target_individual = (
                                self.m_individuals_for_nodes.get(target_node)
                            )
                            if target_individual is None:
                                continue
                            if (
                                self.m_binary_retrieval_0_bound.get_dependency_set()
                                is None
                            ):
                                self._add_known_role_instance(
                                    representative, ind, target_individual
                                )
                            else:
                                self.m_reading_off_found_possible_property_instance = (
                                    True
                                )
                                self._add_possible_role_instance(
                                    representative, ind, target_individual
                                )
                        for target_node in possibly_equivalent_to_successor:
                            target_individual = (
                                self.m_individuals_for_nodes.get(target_node)
                            )
                            if target_individual is None:
                                continue
                            self.m_reading_off_found_possible_property_instance = (
                                True
                            )
                            self._add_possible_role_instance(
                                representative, ind, target_individual
                            )
                self.m_interrupt_flag.check_interrupt()
                self.m_binary_retrieval_0_bound.next()
            completed_steps += 1
            if monitor is not None:
                monitor.reasoner_task_progress_changed(completed_steps, steps)
        return completed_steps

    # ------------------------------------------------------------------
    # Role instance helpers
    # ------------------------------------------------------------------

    def _add_known_role_instance(
        self,
        element: RoleElement,
        individual1: Individual,
        individual2: Individual,
    ) -> None:
        if element != self.m_top_role_element:
            current_node = self.m_current_role_hierarchy.get_node_for_element(
                element
            )
            if current_node is None:
                return
            nodes = current_node.get_descendant_nodes()
            for node in nodes:
                for descendant_element in node.m_equivalent_elements:
                    if descendant_element.is_known(individual1, individual2):
                        return
                self.m_interrupt_flag.check_interrupt()
            element.add_known(individual1, individual2)
            nodes = current_node.get_ancestor_nodes()
            nodes.discard(current_node)
            for node in nodes:
                node.get_representative().remove_known(individual1, individual2)
                self.m_interrupt_flag.check_interrupt()

    def _add_possible_role_instance(
        self,
        element: RoleElement,
        individual1: Individual,
        individual2: Individual,
    ) -> None:
        if element != self.m_top_role_element:
            current_node = self.m_current_role_hierarchy.get_node_for_element(
                element
            )
            if current_node is None:
                return
            nodes = current_node.get_descendant_nodes()
            for node in nodes:
                for descendant_element in node.m_equivalent_elements:
                    if descendant_element.is_possible(individual1, individual2):
                        return
                self.m_interrupt_flag.check_interrupt()
            element.add_possible(individual1, individual2)
            nodes = current_node.get_ancestor_nodes()
            nodes.discard(current_node)
            for node in nodes:
                for ancestor_element in node.m_equivalent_elements:
                    if ancestor_element.is_possible(individual1, individual2):
                        ancestor_element.remove_possible(individual1, individual2)
                self.m_interrupt_flag.check_interrupt()

    # ------------------------------------------------------------------
    # Inconsistency
    # ------------------------------------------------------------------

    def set_inconsistent(self) -> None:
        self.m_is_inconsistent = True
        self.m_realization_completed = True
        self.m_role_realization_completed = True
        self.m_uses_classified_concept_hierarchy = True
        self.m_uses_classified_object_role_hierarchy = True
        self.m_current_concept_hierarchy = None  # type: ignore[assignment]
        self.m_current_role_hierarchy = None  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Realisation
    # ------------------------------------------------------------------

    def realize(self, monitor: Any | None) -> None:
        assert self.m_uses_classified_concept_hierarchy
        if (
            self.m_reading_off_found_possible_concept_instance
            and not self.m_realization_completed
        ):
            if monitor is not None:
                monitor.reasoner_task_started(
                    "Computing instances for all classes"
                )
            num_hierarchy_nodes = len(
                self.m_current_concept_hierarchy.m_nodes_by_elements.values()
            )
            current_hierarchy_node = 0
            to_process: deque[HierarchyNode[AtomicConcept]] = deque(
                self.m_current_concept_hierarchy.m_bottom_node.m_parent_nodes
            )
            visited: set[HierarchyNode[AtomicConcept]] = set()
            while to_process:
                if monitor is not None:
                    monitor.reasoner_task_progress_changed(
                        current_hierarchy_node, num_hierarchy_nodes
                    )
                current = to_process.popleft()
                visited.add(current)
                current_hierarchy_node += 1
                atomic_concept = current.get_representative()
                atomic_concept_element = self.m_concept_to_element.get(
                    atomic_concept
                )
                if atomic_concept_element is not None:
                    parents = current.m_parent_nodes
                    for parent in parents:
                        if parent not in visited and parent not in to_process:
                            to_process.append(parent)
                    if atomic_concept_element.has_possibles():
                        non_instances: set[Individual] = set()
                        for individual in atomic_concept_element.get_possible_instances():
                            if self._is_instance(individual, atomic_concept):
                                atomic_concept_element.m_known_instances.add(
                                    individual
                                )
                            else:
                                non_instances.add(individual)
                        atomic_concept_element.m_possible_instances.clear()
                        for parent in parents:
                            parent_representative = parent.get_representative()
                            parent_element = self.m_concept_to_element.get(
                                parent_representative
                            )
                            if parent_element is None:
                                parent_element = AtomicConceptElement(
                                    None, non_instances
                                )
                                self.m_concept_to_element[
                                    parent_representative
                                ] = parent_element
                            elif parent_representative == self.m_top_concept:
                                self.m_concept_to_element[
                                    self.m_top_concept
                                ].m_known_instances.update(non_instances)
                            else:
                                parent_element.add_possibles(non_instances)
                self.m_interrupt_flag.check_interrupt()
            if monitor is not None:
                monitor.reasoner_task_stopped()
        self.m_realization_completed = True

    def realize_object_roles(self, monitor: Any | None) -> None:
        if (
            self.m_reading_off_found_possible_property_instance
            and not self.m_role_realization_completed
        ):
            if monitor is not None:
                monitor.reasoner_task_started(
                    "Computing instances for all object properties..."
                )
            num_hierarchy_nodes = len(
                self.m_current_role_hierarchy.m_nodes_by_elements.values()
            )
            current_hierarchy_node = 0
            to_process: deque[HierarchyNode[RoleElement]] = deque(
                [self.m_current_role_hierarchy.m_bottom_node]
            )
            visited: set[HierarchyNode[RoleElement]] = set()
            while to_process:
                if monitor is not None:
                    monitor.reasoner_task_progress_changed(
                        current_hierarchy_node, num_hierarchy_nodes
                    )
                current = to_process.popleft()
                visited.add(current)
                current_hierarchy_node += 1
                role_element = current.get_representative()
                parents = current.m_parent_nodes
                for parent in parents:
                    if parent not in to_process and parent not in visited:
                        to_process.append(parent)
                if role_element.has_possibles():
                    for individual in list(
                        role_element.m_possible_relations.keys()
                    ):
                        non_instances: set[Individual] = set()
                        for successor in list(
                            role_element.m_possible_relations.get(individual, set())
                        ):
                            if self._is_role_instance(
                                role_element.get_role(), individual, successor
                            ):
                                role_element.add_known(individual, successor)
                            else:
                                non_instances.add(individual)
                        for parent in parents:
                            parent_representative = parent.get_representative()
                            if parent_representative != self.m_top_role_element:
                                parent_representative.add_possibles(
                                    individual, non_instances
                                )
                    role_element.m_possible_relations.clear()
                self.m_interrupt_flag.check_interrupt()
            if monitor is not None:
                monitor.reasoner_task_stopped()
        self.m_role_realization_completed = True

    # ------------------------------------------------------------------
    # Type and instance queries
    # ------------------------------------------------------------------

    def get_types(
        self, individual: Individual, direct: bool
    ) -> set[HierarchyNode[AtomicConcept]]:
        if self.m_is_inconsistent:
            return {self.m_current_concept_hierarchy.m_bottom_node}  # type: ignore[union-attr]
        result: set[HierarchyNode[AtomicConcept]] = set()
        to_process: deque[HierarchyNode[AtomicConcept]] = deque(
            [self.m_current_concept_hierarchy.m_bottom_node]  # type: ignore[union-attr]
        )
        while to_process:
            current = to_process.popleft()
            parents = current.m_parent_nodes
            atomic_concept = current.get_representative()
            atomic_concept_element = self.m_concept_to_element.get(atomic_concept)
            if (
                atomic_concept_element is not None
                and atomic_concept_element.is_possible(individual)
            ):
                if self._is_instance(individual, atomic_concept):
                    atomic_concept_element.set_to_known(individual)
                else:
                    for parent in parents:
                        parent_representative = parent.get_representative()
                        parent_element = self.m_concept_to_element.get(
                            parent_representative
                        )
                        if parent_element is None:
                            parent_element = AtomicConceptElement(None, None)
                            self.m_concept_to_element[
                                parent_representative
                            ] = parent_element
                        parent_element.add_possible(individual)
            if (
                atomic_concept_element is not None
                and atomic_concept_element.is_known(individual)
            ):
                if direct:
                    result.add(current)
                else:
                    result.update(current.get_ancestor_nodes())
            else:
                for parent in parents:
                    if parent not in to_process:
                        to_process.append(parent)
        return result

    def has_type(
        self, individual: Individual, atomic_concept: AtomicConcept, direct: bool
    ) -> bool:
        hierarchy = self.m_current_concept_hierarchy
        if hierarchy is None:
            return False
        node = hierarchy.get_node_for_element(atomic_concept)
        if node is None:
            return False
        return self._has_type_for_node(individual, node, direct)

    def _has_type_for_node(
        self,
        individual: Individual,
        node: HierarchyNode[AtomicConcept],
        direct: bool,
    ) -> bool:
        representative = node.get_representative()
        if representative == self.m_bottom_concept:
            return False
        element = self.m_concept_to_element.get(representative)
        if (
            element is not None and element.is_known(individual)
        ) or (not direct and node == self.m_current_concept_hierarchy.m_top_node):  # type: ignore[union-attr]
            return True
        if element is not None and element.is_possible(individual):
            if self._is_instance(individual, representative):
                element.set_to_known(individual)
                return True
            else:
                element.m_possible_instances.discard(individual)
                if (
                    not element.m_known_instances
                    and not element.m_possible_instances
                    and representative != self.m_top_concept
                ):
                    self.m_concept_to_element.pop(representative, None)
                for parent in node.m_parent_nodes:
                    parent_concept = parent.get_representative()
                    parent_element = self.m_concept_to_element.get(parent_concept)
                    if parent_element is None:
                        parent_element = AtomicConceptElement(None, None)
                        self.m_concept_to_element[parent_concept] = parent_element
                    parent_element.add_possible(individual)
        elif not direct:
            for child in node.m_child_nodes:
                if self._has_type_for_node(individual, child, False):
                    return True
        return False

    def get_instances(
        self, atomic_concept: AtomicConcept, direct: bool
    ) -> set[Individual]:
        result: set[Individual] = set()
        hierarchy = self.m_current_concept_hierarchy
        if hierarchy is None:
            return result
        node = hierarchy.get_node_for_element(atomic_concept)
        if node is None:
            return result
        self._get_instances_for_node(node, result, direct)
        return result

    def get_instances_for_node(
        self, node: HierarchyNode[AtomicConcept], direct: bool
    ) -> set[Individual]:
        result: set[Individual] = set()
        hierarchy = self.m_current_concept_hierarchy
        if hierarchy is None:
            return result
        node_from_current = hierarchy.get_node_for_element(node.m_representative)
        if node_from_current is None:
            if not direct:
                for child in node.m_child_nodes:
                    self._get_instances_for_node(child, result, direct)
        else:
            self._get_instances_for_node(node_from_current, result, direct)
        return result

    def _get_instances_for_node(
        self,
        node: HierarchyNode[AtomicConcept],
        result: set[Individual],
        direct: bool,
    ) -> None:
        representative = node.get_representative()
        if not direct and representative == self.m_top_concept:
            for individual in self.m_individuals:
                if self._is_result_relevant_individual(individual):
                    result.add(individual)
            return
        representative_element = self.m_concept_to_element.get(representative)
        if representative_element is not None:
            possible_instances = representative_element.get_possible_instances()
            if possible_instances:
                for possible_instance in list(possible_instances):
                    if self._is_instance(possible_instance, representative):
                        representative_element.set_to_known(possible_instance)
                    else:
                        representative_element.m_possible_instances.discard(
                            possible_instance
                        )
                        if (
                            not representative_element.m_known_instances
                            and not representative_element.m_possible_instances
                            and representative != self.m_top_concept
                        ):
                            self.m_concept_to_element.pop(representative, None)
                        for parent in node.m_parent_nodes:
                            parent_concept = parent.get_representative()
                            parent_element = self.m_concept_to_element.get(
                                parent_concept
                            )
                            if parent_element is None:
                                parent_element = AtomicConceptElement(None, None)
                                self.m_concept_to_element[
                                    parent_concept
                                ] = parent_element
                            parent_element.add_possible(possible_instance)
            for individual in representative_element.get_known_instances():
                if self._is_result_relevant_individual(individual):
                    is_direct = True
                    if direct:
                        for child in node.m_child_nodes:
                            if self._has_type_for_node(individual, child, False):
                                is_direct = False
                                break
                    if not direct or is_direct:
                        result.add(individual)
        if not direct:
            for child in node.m_child_nodes:
                if child != self.m_current_concept_hierarchy.m_bottom_node:  # type: ignore[union-attr]
                    self._get_instances_for_node(child, result, False)

    # ------------------------------------------------------------------
    # Role instance queries
    # ------------------------------------------------------------------

    def has_object_role_relationship(
        self,
        role: AtomicRole,
        individual1: Individual,
        individual2: Individual,
    ) -> bool:
        element = self.m_role_element_manager.get_role_element(role)
        current_node = self.m_current_role_hierarchy.get_node_for_element(element)
        if current_node is None:
            return False
        return self._has_object_role_relationship(
            current_node, individual1, individual2
        )

    def _has_object_role_relationship(
        self,
        node: HierarchyNode[RoleElement],
        individual1: Individual,
        individual2: Individual,
    ) -> bool:
        representative_element = node.get_representative()
        if representative_element.is_known(individual1, individual2) or (
            representative_element == self.m_top_role_element
        ):
            return True
        contains_unknown = (
            individual1 not in self.m_individuals
            or individual2 not in self.m_individuals
        )
        if (
            representative_element.is_possible(individual1, individual2)
            or contains_unknown
        ):
            if self._is_role_instance(
                representative_element.get_role(), individual1, individual2
            ):
                if not contains_unknown:
                    representative_element.set_to_known(
                        individual1, individual2
                    )
                return True
            else:
                for parent in node.m_parent_nodes:
                    parent.get_representative().add_possible(
                        individual1, individual2
                    )
        else:
            for child in node.m_child_nodes:
                if self._has_object_role_relationship(
                    child, individual1, individual2
                ):
                    return True
        return False

    def get_object_property_instances(
        self, role: AtomicRole
    ) -> dict[Individual, set[Individual]]:
        result: dict[Individual, set[Individual]] = {}
        hierarchy = self.m_current_role_hierarchy
        if hierarchy is None:
            return result
        role_elem = self.m_role_element_manager.get_role_element(role)
        node = hierarchy.get_node_for_element(role_elem)
        if node is None:
            return result
        self._get_object_property_instances(node, result)
        return result

    def _get_object_property_instances(
        self,
        node: HierarchyNode[RoleElement],
        result: dict[Individual, set[Individual]],
    ) -> None:
        representative_element = node.get_representative()
        if representative_element == self.m_top_role_element or self.m_is_inconsistent:
            all_result_relevant: set[Individual] = set()
            for individual in self.m_individuals:
                if self._is_result_relevant_individual(individual):
                    all_result_relevant.add(individual)
                    result[individual] = all_result_relevant
            return
        possible_instances = representative_element.get_possible_relations()
        for possible_instance in list(possible_instances.keys()):
            for possible_successor in list(
                possible_instances.get(possible_instance, set())
            ):
                if self._is_role_instance(
                    representative_element.get_role(),
                    possible_instance,
                    possible_successor,
                ):
                    representative_element.set_to_known(
                        possible_instance, possible_successor
                    )
                else:
                    for parent in node.m_parent_nodes:
                        parent.get_representative().add_possible(
                            possible_instance, possible_successor
                        )
        known_instances = representative_element.get_known_relations()
        for instance1 in known_instances:
            if self._is_result_relevant_individual(instance1):
                successors = result.get(instance1)
                is_new = False
                if successors is None:
                    successors = set()
                    is_new = True
                for instance2 in known_instances[instance1]:
                    if self._is_result_relevant_individual(instance2):
                        successors.add(instance2)
                if is_new and successors:
                    result[instance1] = successors
        for child in node.m_child_nodes:
            self._get_object_property_instances(child, result)

    def get_object_property_values(
        self, role: AtomicRole, individual: Individual
    ) -> set[Individual]:
        result: set[Individual] = set()
        hierarchy = self.m_current_role_hierarchy
        if hierarchy is None:
            return result
        role_elem = self.m_role_element_manager.get_role_element(role)
        node = hierarchy.get_node_for_element(role_elem)
        if node is not None:
            self._get_object_property_values(node, individual, result)
        return result

    def get_object_property_subjects(
        self, role: AtomicRole, individual: Individual
    ) -> set[Individual]:
        result: set[Individual] = set()
        hierarchy = self.m_current_role_hierarchy
        if hierarchy is None:
            return result
        role_elem = self.m_role_element_manager.get_role_element(role)
        node = hierarchy.get_node_for_element(role_elem)
        if node is not None:
            self._get_object_property_subjects(node, individual, result)
        return result

    def _get_object_property_subjects(
        self,
        node: HierarchyNode[RoleElement],
        obj: Individual,
        result: set[Individual],
    ) -> None:
        representative_element = node.get_representative()
        if representative_element == self.m_top_role_element or self.m_is_inconsistent:
            for ind in self.m_individuals:
                if self._is_result_relevant_individual(ind):
                    result.add(ind)
            return
        relevant_relations = representative_element.get_known_relations()
        for subject in list(relevant_relations.keys()):
            if (
                self._is_result_relevant_individual(subject)
                and obj in relevant_relations.get(subject, set())
            ):
                result.add(subject)
        relevant_relations = representative_element.get_possible_relations()
        for possible_subject in list(relevant_relations.keys()):
            if (
                self._is_result_relevant_individual(possible_subject)
                and obj in relevant_relations.get(possible_subject, set())
                and self._is_role_instance(
                    representative_element.get_role(), possible_subject, obj
                )
            ):
                representative_element.set_to_known(possible_subject, obj)
                result.add(possible_subject)
            else:
                for parent in node.m_parent_nodes:
                    parent.get_representative().add_possible(
                        possible_subject, obj
                    )
        for child in node.m_child_nodes:
            self._get_object_property_subjects(child, obj, result)

    def _get_object_property_values(
        self,
        node: HierarchyNode[RoleElement],
        subject: Individual,
        result: set[Individual],
    ) -> None:
        representative_element = node.get_representative()
        if representative_element == self.m_top_role_element or self.m_is_inconsistent:
            for ind in self.m_individuals:
                if self._is_result_relevant_individual(ind):
                    result.add(ind)
            return
        possible_successors = representative_element.get_possible_relations().get(
            subject
        )
        if possible_successors is not None:
            for possible_successor in list(possible_successors):
                if self._is_role_instance(
                    representative_element.get_role(),
                    subject,
                    possible_successor,
                ):
                    representative_element.set_to_known(
                        subject, possible_successor
                    )
                else:
                    for parent in node.m_parent_nodes:
                        parent.get_representative().add_possible(
                            subject, possible_successor
                        )
        known_successors = representative_element.get_known_relations().get(subject)
        if known_successors is not None:
            for successor in known_successors:
                if self._is_result_relevant_individual(successor):
                    result.add(successor)
        for child in node.m_child_nodes:
            self._get_object_property_values(child, subject, result)

    # ------------------------------------------------------------------
    # Same-as
    # ------------------------------------------------------------------

    def get_same_as_individuals(
        self, individual: Individual
    ) -> set[Individual]:
        equivalence_class = self.m_individual_to_equivalence_class.get(individual)
        if equivalence_class is None:
            return {individual}
        possibly_same_equivalence_classes = (
            self.m_individual_to_possible_equivalence_class.get(equivalence_class)
            if self.m_individual_to_possible_equivalence_class is not None
            else None
        )
        if possibly_same_equivalence_classes is not None:
            while possibly_same_equivalence_classes:
                possibly_equivalent_class = next(
                    iter(possibly_same_equivalence_classes)
                )
                possibly_same_equivalence_classes.discard(
                    possibly_equivalent_class
                )
                if not possibly_same_equivalence_classes:
                    self.m_individual_to_possible_equivalence_class.pop(
                        equivalence_class, None
                    )
                possibly_equivalent_individual = next(
                    iter(possibly_equivalent_class)
                )
                if self._is_same_individual(
                    next(iter(equivalence_class)), possibly_equivalent_individual
                ):
                    equivalence_class.update(possibly_equivalent_class)
                    equivalence_class.update(
                        self.m_individual_to_equivalence_class.get(
                            possibly_equivalent_individual, set()
                        )
                    )
                    for now_known_equivalent in possibly_equivalent_class:
                        self.m_individual_to_equivalence_class[
                            now_known_equivalent
                        ] = equivalence_class
                else:
                    possibly_equiv_to_now_known = (
                        self.m_individual_to_possible_equivalence_class.get(
                            possibly_equivalent_class
                        )
                    )
                    if (
                        possibly_equiv_to_now_known is not None
                        and possibly_equiv_to_now_known.__contains__(
                            equivalence_class
                        )
                    ):
                        possibly_equiv_to_now_known.discard(equivalence_class)
                        if not possibly_equiv_to_now_known:
                            self.m_individual_to_possible_equivalence_class.pop(
                                possibly_equivalent_class, None
                            )

        if self.m_individual_to_possible_equivalence_class is not None:
            for other_equivalence_class in list(
                self.m_individual_to_possible_equivalence_class.keys()
            ):
                if other_equivalence_class != equivalence_class and (
                    self.m_individual_to_possible_equivalence_class.get(
                        other_equivalence_class, set()
                    ).__contains__(equivalence_class)
                ):
                    if self._is_same_individual(
                        next(iter(equivalence_class)),
                        next(iter(other_equivalence_class)),
                    ):
                        self.m_individual_to_possible_equivalence_class[
                            other_equivalence_class
                        ].discard(equivalence_class)
                        if not self.m_individual_to_possible_equivalence_class[
                            other_equivalence_class
                        ]:
                            self.m_individual_to_possible_equivalence_class.pop(
                                other_equivalence_class, None
                            )
                        for now_known_equivalent in other_equivalence_class:
                            self.m_individual_to_equivalence_class[
                                now_known_equivalent
                            ] = equivalence_class
                        equivalence_class.update(other_equivalence_class)
        return equivalence_class

    def is_same_individual(
        self, individual1: Individual, individual2: Individual
    ) -> bool:
        return not self.m_reasoner.get_tableau().is_satisfiable(
            True,
            False,
            {Inequality.INSTANCE},  # type: ignore[arg-type]
            None,
            None,
            None,
            None,
            None,
        )

    def compute_same_as_equivalence_classes(
        self, progress_monitor: Any | None
    ) -> None:
        if (
            self.m_individual_to_possible_equivalence_class is not None
            and self.m_individual_to_possible_equivalence_class
        ):
            steps = len(self.m_individual_to_possible_equivalence_class)
            if steps > 0 and progress_monitor is not None:
                progress_monitor.reasoner_task_started("Precompute same individuals")
            while self.m_individual_to_possible_equivalence_class:
                equivalence_class = next(
                    iter(self.m_individual_to_possible_equivalence_class.keys())
                )
                self.get_same_as_individuals(next(iter(equivalence_class)))
                if progress_monitor is not None:
                    progress_monitor.reasoner_task_progress_changed(
                        steps - len(self.m_individual_to_possible_equivalence_class),
                        steps,
                    )
            if progress_monitor is not None:
                progress_monitor.reasoner_task_stopped()

    # ------------------------------------------------------------------
    # Instance testing
    # ------------------------------------------------------------------

    def _is_instance(
        self, individual: Individual, atomic_concept: AtomicConcept
    ) -> bool:
        result = not self.m_reasoner.get_tableau().is_satisfiable(
            True,
            False,
            None,
            None,
            None,
            None,
            None,
            None,
        )
        if self.m_tableau_monitor is not None:
            if result:
                self.m_tableau_monitor.possible_instance_is_instance()
            else:
                self.m_tableau_monitor.possible_instance_is_not_instance()
        return result

    def _is_role_instance(
        self, role: Role, individual1: Individual, individual2: Individual
    ) -> bool:
        ind1 = individual1
        ind2 = individual2
        if isinstance(role, InverseRole):
            ind1, ind2 = ind2, ind1
        result = not self.m_reasoner.get_tableau().is_satisfiable(
            True,
            True,
            None,
            None,
            None,
            None,
            None,
            None,
        )
        if self.m_tableau_monitor is not None:
            if result:
                self.m_tableau_monitor.possible_instance_is_instance()
            else:
                self.m_tableau_monitor.possible_instance_is_not_instance()
        return result

    @staticmethod
    def _is_result_relevant_individual(individual: Individual) -> bool:
        return not individual.is_anonymous() and not Prefixes.is_internal_iri(
            individual.iri
        )

    # ------------------------------------------------------------------
    # Status queries
    # ------------------------------------------------------------------

    def realization_completed(self) -> bool:
        return self.m_realization_completed

    def object_property_realization_completed(self) -> bool:
        return self.m_role_realization_completed

    def same_as_individuals_computed(self) -> bool:
        return (
            self.m_individual_to_possible_equivalence_class is None
            or not self.m_individual_to_possible_equivalence_class
        )

    def are_classes_initialised(self) -> bool:
        return self.m_classes_initialised

    def are_properties_initialised(self) -> bool:
        return self.m_properties_initialised

    def get_current_individual_index(self) -> int:
        return self.m_current_individual_index

    def get_nodes_for_individuals(self) -> dict[Individual, Node | None]:
        return self.m_nodes_for_individuals

    def update_nodes_for_individuals(self, nodes_mapping: dict[Any, Any]) -> None:
        """Update the nodes for individuals from tableau results."""
        for individual, node in nodes_mapping.items():
            if isinstance(individual, Individual):
                self.m_nodes_for_individuals[individual] = node
