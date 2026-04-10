"""Core tableau engine for HermiT.

Coordinates tableau expansion, backtracking, and satisfiability checking
for a clausified DL ontology.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hermit.tableau.branching_point import BranchingPoint
from hermit.tableau.clash_manager import ClashManager
from hermit.tableau.dependency_set import DependencySet
from hermit.tableau.dependency_set_factory import DependencySetFactory
from hermit.tableau.extension_manager import ExtensionManager
from hermit.tableau.interrupt_flag import InterruptFlag
from hermit.tableau.merging_manager import MergingManager
from hermit.tableau.node import Node, NodeState
from hermit.tableau.node_type import NodeType

if TYPE_CHECKING:
    from hermit.model import Atom
    from hermit.tableau.reasoning_task_description import ReasoningTaskDescription


class Tableau:
    """Main tableau expansion engine.

    Represents the state of a reasoning run on a set of clauses and
    coordinates extension of the ABox as well as retraction of facts
    when backtracking.

    Args:
        interrupt_flag: Flag for interrupting long-running tasks.
        tableau_monitor: Optional monitor for observing tableau events.
        existential_expansion_strategy: Strategy for expanding existentials.
        use_disjunction_learning: Whether to enable disjunction learning.
        permanent_dl_ontology: The permanent (non-changing) DL ontology.
        additional_dl_ontology: Optional additional DL ontology.
        parameters: Configuration parameters.
    """

    __slots__ = (
        "m_interrupt_flag",
        "m_parameters",
        "m_tableau_monitor",
        "m_existential_expansion_strategy",
        "m_permanent_dl_ontology",
        "m_additional_dl_ontology",
        "m_dependency_set_factory",
        "m_extension_manager",
        "m_clash_manager",
        "m_permanent_hyperresolution_manager",
        "m_additional_hyperresolution_manager",
        "m_merging_manager",
        "m_existential_expansion_manager",
        "m_nominal_introduction_manager",
        "m_description_graph_manager",
        "m_datatype_manager",
        "m_existential_concepts_buffers",
        "m_use_disjunction_learning",
        "m_has_description_graphs",
        "m_branching_points",
        "m_current_branching_point",
        "m_nonbacktrackable_branching_point",
        "m_is_current_model_deterministic",
        "m_needs_thing_extension",
        "m_needs_named_extension",
        "m_needs_rdfs_literal_extension",
        "m_check_datatypes",
        "m_check_unknown_datatype_restrictions",
        "m_allocated_nodes",
        "m_number_of_nodes_in_tableau",
        "m_number_of_merged_or_pruned_nodes",
        "m_number_of_node_creations",
        "m_first_free_node",
        "m_first_tableau_node",
        "m_last_tableau_node",
        "m_last_merged_or_pruned_node",
        "m_first_ground_disjunction",
        "m_first_unprocessed_ground_disjunction",
    )

    def __init__(
        self,
        interrupt_flag: InterruptFlag,
        tableau_monitor: Any | None,
        existential_expansion_strategy: Any,
        use_disjunction_learning: bool,
        permanent_dl_ontology: Any,
        additional_dl_ontology: Any | None,
        parameters: dict[str, Any],
    ) -> None:
        if additional_dl_ontology is not None:
            graphs = additional_dl_ontology.get_all_description_graphs()
            if graphs and len(graphs) > 0:
                raise ValueError(
                    "Additional ontology cannot contain description graphs."
                )

        self.m_interrupt_flag = interrupt_flag
        self.m_interrupt_flag.start_task()
        try:
            self.m_parameters = parameters
            self.m_tableau_monitor = tableau_monitor
            self.m_existential_expansion_strategy = existential_expansion_strategy
            self.m_permanent_dl_ontology = permanent_dl_ontology
            self.m_additional_dl_ontology = additional_dl_ontology

            self.m_dependency_set_factory = DependencySetFactory()
            self.m_extension_manager = ExtensionManager(self)
            self.m_clash_manager = ClashManager(self)

            # Import here to avoid circular imports at module level
            from hermit.tableau.hyperresolution_manager import (
                HyperresolutionManager,
            )

            self.m_permanent_hyperresolution_manager = HyperresolutionManager(
                self, permanent_dl_ontology.get_dl_clauses()
            )
            self.m_additional_hyperresolution_manager: HyperresolutionManager | None
            if self.m_additional_dl_ontology is not None:
                self.m_additional_hyperresolution_manager = HyperresolutionManager(
                    self, self.m_additional_dl_ontology.get_dl_clauses()
                )
            else:
                self.m_additional_hyperresolution_manager = None

            self.m_merging_manager = MergingManager(self)
            from hermit.tableau.existential_expansion_manager import (
                ExistentialExpansionManager,
            )

            self.m_existential_expansion_manager = ExistentialExpansionManager(self)
            from hermit.tableau.nominal_introduction_manager import (
                NominalIntroductionManager,
            )

            self.m_nominal_introduction_manager = NominalIntroductionManager(self)
            from hermit.tableau.description_graph_manager import (
                DescriptionGraphManager,
            )

            self.m_description_graph_manager = DescriptionGraphManager(self)
            from hermit.tableau.datatype_manager import DatatypeManager

            self.m_datatype_manager = DatatypeManager(self)

            self.m_existential_expansion_strategy.initialize(self)
            self.m_existential_concepts_buffers: list[list[Any]] = []
            self.m_use_disjunction_learning = use_disjunction_learning
            self.m_has_description_graphs = (
                len(self.m_permanent_dl_ontology.get_all_description_graphs()) > 0
            )

            self.m_branching_points: list[BranchingPoint | None] = [None, None]
            self.m_current_branching_point = -1
            self.m_nonbacktrackable_branching_point = -1

            # Java field defaults — Python slots require explicit initialization
            self.m_allocated_nodes: int = 0
            self.m_number_of_nodes_in_tableau: int = 0
            self.m_number_of_merged_or_pruned_nodes: int = 0
            self.m_number_of_node_creations: int = 0
            self.m_first_free_node: Node | None = None
            self.m_first_tableau_node: Node | None = None
            self.m_last_tableau_node: Node | None = None
            self.m_last_merged_or_pruned_node: Node | None = None
            self.m_first_ground_disjunction: Any = None
            self.m_first_unprocessed_ground_disjunction: Any = None
            self.m_is_current_model_deterministic: bool = True

            self._update_flags_dependent_on_additional_ontology()

            if self.m_tableau_monitor is not None:
                self.m_tableau_monitor.set_tableau(self)
        finally:
            self.m_interrupt_flag.end_task()

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def interrupt_flag(self) -> InterruptFlag:
        """Return the interrupt flag."""
        return self.m_interrupt_flag

    @property
    def permanent_dl_ontology(self) -> Any:
        """Return the permanent DL ontology."""
        return self.m_permanent_dl_ontology

    @property
    def additional_dl_ontology(self) -> Any | None:
        """Return the additional DL ontology, if any."""
        return self.m_additional_dl_ontology

    @property
    def parameters(self) -> dict[str, Any]:
        """Return the configuration parameters."""
        return self.m_parameters

    @property
    def tableau_monitor(self) -> Any | None:
        """Return the tableau monitor."""
        return self.m_tableau_monitor

    def get_tableau_monitor(self) -> Any:
        """Return the tableau monitor (Java-compatible alias)."""
        return self.m_tableau_monitor

    def get_extension_manager(self) -> Any:
        """Return the extension manager (Java-compatible alias)."""
        return self.m_extension_manager

    @property
    def existential_expansion_strategy(self) -> Any:
        """Return the existential expansion strategy."""
        return self.m_existential_expansion_strategy

    def is_deterministic(self) -> bool:
        """Return ``True`` if the current ontology set is Horn."""
        perm_horn = self.m_permanent_dl_ontology.is_horn()
        add_horn = (
            self.m_additional_dl_ontology is None
            or self.m_additional_dl_ontology.is_horn()
        )
        strat_det = bool(self.m_existential_expansion_strategy.is_deterministic())
        return perm_horn and add_horn and strat_det

    @property
    def dependency_set_factory(self) -> DependencySetFactory:
        """Return the dependency-set factory."""
        return self.m_dependency_set_factory

    @property
    def extension_manager(self) -> ExtensionManager:
        """Return the extension manager."""
        return self.m_extension_manager

    @property
    def permanent_hyperresolution_manager(self) -> Any:
        """Return the permanent hyperresolution manager."""
        return self.m_permanent_hyperresolution_manager

    @property
    def additional_hyperresolution_manager(self) -> Any | None:
        """Return the additional hyperresolution manager."""
        return self.m_additional_hyperresolution_manager

    @property
    def merging_manager(self) -> MergingManager:
        """Return the merging manager."""
        return self.m_merging_manager

    @property
    def existential_expansion_manager(self) -> Any:
        """Return the existential expansion manager."""
        return self.m_existential_expansion_manager

    @property
    def nominal_introduction_manager(self) -> Any:
        """Return the nominal introduction manager."""
        return self.m_nominal_introduction_manager

    @property
    def description_graph_manager(self) -> Any:
        """Return the description graph manager."""
        return self.m_description_graph_manager

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Reset the tableau to its initial empty state."""
        self.m_allocated_nodes = 0
        self.m_number_of_nodes_in_tableau = 0
        self.m_number_of_merged_or_pruned_nodes = 0
        self.m_number_of_node_creations = 0
        self.m_first_free_node = None
        self.m_first_tableau_node = None
        self.m_last_tableau_node = None
        self.m_last_merged_or_pruned_node = None
        self.m_first_ground_disjunction = None
        self.m_first_unprocessed_ground_disjunction = None
        self.m_branching_points = [None, None]
        self.m_current_branching_point = -1
        self.m_nonbacktrackable_branching_point = -1
        self.m_dependency_set_factory.clear()
        self.m_extension_manager.clear()
        self.m_clash_manager.clear()
        self.m_permanent_hyperresolution_manager.clear()
        if self.m_additional_hyperresolution_manager is not None:
            self.m_additional_hyperresolution_manager.clear()
        self.m_merging_manager.clear()
        self.m_existential_expansion_manager.clear()
        self.m_nominal_introduction_manager.clear()
        self.m_description_graph_manager.clear()
        self.m_is_current_model_deterministic = True
        self.m_existential_expansion_strategy.clear()
        self.m_datatype_manager.clear()
        self.m_existential_concepts_buffers.clear()
        if self.m_tableau_monitor is not None:
            self.m_tableau_monitor.tableau_cleared()

    # ------------------------------------------------------------------
    # Additional ontology support
    # ------------------------------------------------------------------

    def supports_additional_dl_ontology(self, additional_dl_ontology: Any) -> bool:
        """Check whether *additional_dl_ontology* is compatible.

        Returns:
            ``True`` if the additional ontology can be used with this tableau.
        """
        from hermit.model import AtomicRole, DLClause

        has_inverse_roles = (
            self.m_permanent_dl_ontology.has_inverse_roles()
            or (
                self.m_additional_dl_ontology is not None
                and self.m_additional_dl_ontology.has_inverse_roles()
            )
        )
        has_nominals = (
            self.m_permanent_dl_ontology.has_nominals()
            or (
                self.m_additional_dl_ontology is not None
                and self.m_additional_dl_ontology.has_nominals()
            )
        )
        is_horn = (
            self.m_permanent_dl_ontology.is_horn()
            or (
                self.m_additional_dl_ontology is not None
                and self.m_additional_dl_ontology.is_horn()
            )
        )
        permanent_has_bottom = self.m_permanent_dl_ontology.contains_object_role(
            AtomicRole.BOTTOM_OBJECT_ROLE
        )
        has_bottom = permanent_has_bottom or (
            self.m_additional_dl_ontology is not None
            and self.m_additional_dl_ontology.contains_object_role(
                AtomicRole.BOTTOM_OBJECT_ROLE
            )
        )

        graphs = additional_dl_ontology.get_all_description_graphs()
        if (
            (graphs and len(graphs) > 0)
            or (additional_dl_ontology.has_inverse_roles() and not has_inverse_roles)
            or (additional_dl_ontology.has_nominals() and not has_nominals)
            or (not additional_dl_ontology.is_horn() and is_horn)
            or (has_bottom and not permanent_has_bottom)
        ):
            return False

        for dl_clause in additional_dl_ontology.get_dl_clauses():
            if isinstance(dl_clause, DLClause):
                if (
                    dl_clause.is_atomic_role_inclusion()
                    or dl_clause.is_atomic_role_inverse_inclusion()
                    or dl_clause.is_functionality_axiom()
                    or dl_clause.is_inverse_functionality_axiom()
                ):
                    return False
        return True

    def set_additional_dl_ontology(self, additional_dl_ontology: Any) -> None:
        """Set the additional DL ontology.

        Raises:
            ValueError: If the additional ontology is incompatible.
        """
        if not self.supports_additional_dl_ontology(additional_dl_ontology):
            raise ValueError(
                "Additional DL-ontology contains features that are incompatible "
                "with this tableau."
            )
        self.m_additional_dl_ontology = additional_dl_ontology
        from hermit.tableau.hyperresolution_manager import HyperresolutionManager

        self.m_additional_hyperresolution_manager = HyperresolutionManager(
            self, additional_dl_ontology.get_dl_clauses()
        )
        self.m_existential_expansion_strategy.additional_dl_ontology_set(
            additional_dl_ontology
        )
        self.m_datatype_manager.additional_dl_ontology_set(additional_dl_ontology)
        self._update_flags_dependent_on_additional_ontology()

    def clear_additional_dl_ontology(self) -> None:
        """Remove the additional DL ontology."""
        self.m_additional_dl_ontology = None
        self.m_additional_hyperresolution_manager = None
        self.m_existential_expansion_strategy.additional_dl_ontology_cleared()
        self.m_datatype_manager.additional_dl_ontology_cleared()
        self._update_flags_dependent_on_additional_ontology()

    def _update_flags_dependent_on_additional_ontology(self) -> None:
        """Update cached boolean flags that depend on the additional ontology."""
        from hermit.model import AtomicConcept
        from hermit.datatypes import InternalDatatype

        def has_delta_consumer(hrm: Any, predicate: Any) -> bool:
            if hrm is None:
                return False
            return predicate in hrm.m_tuple_consumers_by_delta_predicate

        self.m_needs_thing_extension = has_delta_consumer(
            self.m_permanent_hyperresolution_manager, AtomicConcept.THING
        )
        self.m_needs_named_extension = has_delta_consumer(
            self.m_permanent_hyperresolution_manager, AtomicConcept.INTERNAL_NAMED
        )
        self.m_needs_rdfs_literal_extension = has_delta_consumer(
            self.m_permanent_hyperresolution_manager, InternalDatatype.RDFS_LITERAL
        )
        self.m_check_datatypes = self.m_permanent_dl_ontology.has_datatypes()
        self.m_check_unknown_datatype_restrictions = (
            self.m_permanent_dl_ontology.has_unknown_datatype_restrictions()
        )

        if self.m_additional_hyperresolution_manager is not None:
            self.m_needs_thing_extension |= has_delta_consumer(
                self.m_additional_hyperresolution_manager, AtomicConcept.THING
            )
            self.m_needs_named_extension |= has_delta_consumer(
                self.m_additional_hyperresolution_manager,
                AtomicConcept.INTERNAL_NAMED,
            )
            self.m_needs_rdfs_literal_extension |= has_delta_consumer(
                self.m_additional_hyperresolution_manager,
                InternalDatatype.RDFS_LITERAL,
            )

        if self.m_additional_dl_ontology is not None:
            self.m_check_datatypes |= self.m_additional_dl_ontology.has_datatypes()
            self.m_check_unknown_datatype_restrictions |= (
                self.m_additional_dl_ontology.has_unknown_datatype_restrictions()
            )

    # ------------------------------------------------------------------
    # Satisfiability checking
    # ------------------------------------------------------------------

    def is_satisfiable(
        self,
        load_permanent_abox: bool = False,
        load_additional_abox: bool = False,
        per_test_positive_facts_no_dependency: set[Any] | None = None,
        per_test_negative_facts_no_dependency: set[Any] | None = None,
        per_test_positive_facts_dummy_dependency: set[Any] | None = None,
        per_test_negative_facts_dummy_dependency: set[Any] | None = None,
        nodes_for_individuals: dict[Any, Node] | None = None,
        reasoning_task_description: ReasoningTaskDescription | None = None,
    ) -> bool:
        """Check whether the ontology is satisfiable.

        Args:
            load_permanent_abox: Whether to load the permanent ABox.
            load_additional_abox: Whether to load the additional ABox.
            per_test_positive_facts_no_dependency: Positive facts with no dependencies.
            per_test_negative_facts_no_dependency: Negative facts with no dependencies.
            per_test_positive_facts_dummy_dependency: Positive facts with a dummy
                dependency (triggers a branching point).
            per_test_negative_facts_dummy_dependency: Negative facts with a dummy
                dependency.
            nodes_for_individuals: If provided, will be populated with the mapping
                from individuals to tableau nodes.
            reasoning_task_description: Description for logging/monitoring.

        Returns:
            ``True`` if the ontology is satisfiable.
        """
        if self.m_tableau_monitor is not None:
            self.m_tableau_monitor.is_satisfiable_started(
                reasoning_task_description
            )

        self.clear()

        load_permanent = (
            load_permanent_abox
            or self.m_permanent_dl_ontology.has_nominals()
            or (
                self.m_additional_dl_ontology is not None
                and self.m_additional_dl_ontology.has_nominals()
            )
        )

        terms_to_nodes: dict[Any, Node] = {}

        # Load permanent ABox
        if load_permanent:
            for atom in self.m_permanent_dl_ontology.get_positive_facts():
                self._load_positive_fact(
                    terms_to_nodes, atom, self.m_dependency_set_factory.empty_set
                )
            for atom in self.m_permanent_dl_ontology.get_negative_facts():
                self._load_negative_fact(
                    terms_to_nodes, atom, self.m_dependency_set_factory.empty_set
                )

        # Load additional ABox
        if load_additional_abox and self.m_additional_dl_ontology is not None:
            for atom in self.m_additional_dl_ontology.get_positive_facts():
                self._load_positive_fact(
                    terms_to_nodes, atom, self.m_dependency_set_factory.empty_set
                )
            for atom in self.m_additional_dl_ontology.get_negative_facts():
                self._load_negative_fact(
                    terms_to_nodes, atom, self.m_dependency_set_factory.empty_set
                )

        # Per-test facts (no dependency)
        if per_test_positive_facts_no_dependency:
            for atom in per_test_positive_facts_no_dependency:
                self._load_positive_fact(
                    terms_to_nodes, atom, self.m_dependency_set_factory.empty_set
                )
        if per_test_negative_facts_no_dependency:
            for atom in per_test_negative_facts_no_dependency:
                self._load_negative_fact(
                    terms_to_nodes, atom, self.m_dependency_set_factory.empty_set
                )

        # Per-test facts (dummy dependency -- creates a branching point)
        if (
            per_test_positive_facts_dummy_dependency
            or per_test_negative_facts_dummy_dependency
        ):
            self.m_branching_points[0] = BranchingPoint(self)
            self.m_current_branching_point += 1
            self.m_nonbacktrackable_branching_point = self.m_current_branching_point
            self.m_dependency_set_factory.add_branching_point(
                self.m_dependency_set_factory.empty_set,
                self.m_current_branching_point,
            )
            dummy_dep = self.m_dependency_set_factory.add_branching_point(
                self.m_dependency_set_factory.empty_set,
                self.m_current_branching_point,
            )
            if per_test_positive_facts_dummy_dependency:
                for atom in per_test_positive_facts_dummy_dependency:
                    self._load_positive_fact(terms_to_nodes, atom, dummy_dep)
            if per_test_negative_facts_dummy_dependency:
                for atom in per_test_negative_facts_dummy_dependency:
                    self._load_negative_fact(terms_to_nodes, atom, dummy_dep)

        # Map individuals to nodes
        if nodes_for_individuals is not None:
            from hermit.model import Atom as _Atom, AtomicConcept as _AC

            for individual, _existing_node in nodes_for_individuals.items():
                if terms_to_nodes.get(individual) is None:
                    top_assertion = _Atom.create(_AC.THING, individual)
                    self._load_positive_fact(
                        terms_to_nodes,
                        top_assertion,
                        self.m_dependency_set_factory.empty_set,
                    )
                nodes_for_individuals[individual] = terms_to_nodes[individual]

        # Ensure at least one individual exists
        if self.m_first_tableau_node is None:
            self._create_new_ni_node(self.m_dependency_set_factory.empty_set)

        result = self._run_calculus()

        if self.m_tableau_monitor is not None:
            self.m_tableau_monitor.is_satisfiable_finished(
                reasoning_task_description, result
            )
        return result

    # ------------------------------------------------------------------
    # Fact loading
    # ------------------------------------------------------------------

    def _load_positive_fact(
        self,
        terms_to_nodes: dict[Any, Node],
        atom: Atom,
        dependency_set: DependencySet,
    ) -> None:
        """Load a positive fact (ground atom) into the tableau."""
        from hermit.model import (
            AnnotatedEquality,
            AtomicConcept,
            AtomicRole,
            DescriptionGraph,
            Equality,
            Inequality,
            LiteralConcept,
        )

        dl_predicate = atom.predicate
        if isinstance(dl_predicate, LiteralConcept):
            self.m_extension_manager.add_concept_assertion(
                dl_predicate,
                self._get_node_for_term(terms_to_nodes, atom.argument(0), dependency_set),
                dependency_set,
                True,
            )
        elif (
            isinstance(dl_predicate, AtomicRole)
            or Equality.INSTANCE is dl_predicate
            or Inequality.INSTANCE is dl_predicate
        ):
            self.m_extension_manager.add_assertion_binary(
                dl_predicate,
                self._get_node_for_term(terms_to_nodes, atom.argument(0), dependency_set),
                self._get_node_for_term(terms_to_nodes, atom.argument(1), dependency_set),
                dependency_set,
                True,
            )
        elif isinstance(dl_predicate, DescriptionGraph):
            description_graph = dl_predicate
            arity = description_graph.arity()
            tup: list[Any] = [None] * (arity + 1)
            tup[0] = description_graph
            for arg_idx in range(arity):
                tup[arg_idx + 1] = self._get_node_for_term(
                    terms_to_nodes, atom.argument(arg_idx), dependency_set
                )
            self.m_extension_manager.add_tuple(tup, dependency_set, True)
        elif isinstance(dl_predicate, AtomicConcept):
            self.m_extension_manager.add_concept_assertion(
                dl_predicate,
                self._get_node_for_term(terms_to_nodes, atom.argument(0), dependency_set),
                dependency_set,
                True,
            )
        elif isinstance(dl_predicate, AnnotatedEquality):
            self.m_extension_manager.add_annotated_equality(
                dl_predicate,
                self._get_node_for_term(terms_to_nodes, atom.argument(0), dependency_set),
                self._get_node_for_term(terms_to_nodes, atom.argument(1), dependency_set),
                self._get_node_for_term(terms_to_nodes, atom.argument(2), dependency_set),
                dependency_set,
            )
        else:
            raise ValueError("Unsupported type of positive ground atom.")

    def _load_negative_fact(
        self,
        terms_to_nodes: dict[Any, Node],
        atom: Atom,
        dependency_set: DependencySet,
    ) -> None:
        """Load a negative fact (negated ground atom) into the tableau."""
        from hermit.model import (
            AtomicRole,
            Equality,
            Inequality,
            NegatedAtomicRole,
        )
        from hermit.model import LiteralConcept

        dl_predicate = atom.predicate
        if isinstance(dl_predicate, LiteralConcept):
            self.m_extension_manager.add_concept_assertion(
                dl_predicate.get_negation(),
                self._get_node_for_term(terms_to_nodes, atom.argument(0), dependency_set),
                dependency_set,
                True,
            )
        elif isinstance(dl_predicate, AtomicRole):
            tup = self.m_extension_manager.m_ternary_auxiliary_tuple_add
            tup[0] = NegatedAtomicRole.create(dl_predicate)
            tup[1] = self._get_node_for_term(
                terms_to_nodes, atom.argument(0), dependency_set
            )
            tup[2] = self._get_node_for_term(
                terms_to_nodes, atom.argument(1), dependency_set
            )
            self.m_extension_manager.add_tuple(tup, dependency_set, True)
        elif Equality.INSTANCE is dl_predicate:
            self.m_extension_manager.add_assertion_binary(
                Inequality.INSTANCE,
                self._get_node_for_term(terms_to_nodes, atom.argument(0), dependency_set),
                self._get_node_for_term(terms_to_nodes, atom.argument(1), dependency_set),
                dependency_set,
                True,
            )
        elif Inequality.INSTANCE is dl_predicate:
            self.m_extension_manager.add_assertion_binary(
                Equality.INSTANCE,
                self._get_node_for_term(terms_to_nodes, atom.argument(0), dependency_set),
                self._get_node_for_term(terms_to_nodes, atom.argument(1), dependency_set),
                dependency_set,
                True,
            )
        else:
            raise ValueError("Unsupported type of negative ground atom.")

    def _get_node_for_term(
        self,
        terms_to_nodes: dict[Any, Node],
        term: Any,
        dependency_set: DependencySet,
    ) -> Node:
        """Return (or create) the tableau node for *term*."""
        from hermit.model import Individual
        from hermit.model import ConstantEnumeration

        node = terms_to_nodes.get(term)
        if node is None:
            if isinstance(term, Individual):
                if term.is_anonymous():
                    node = self._create_new_ni_node(dependency_set)
                else:
                    node = self.create_new_named_node(dependency_set)
            else:
                constant = term
                node = self.create_new_root_constant_node(dependency_set)
                if not constant.is_anonymous():
                    self.m_extension_manager.add_assertion_unary(
                        ConstantEnumeration.create([constant]),
                        node,
                        dependency_set,
                        True,
                    )
            terms_to_nodes[term] = node
        return node.get_canonical_node()

    # ------------------------------------------------------------------
    # Main calculus loop
    # ------------------------------------------------------------------

    def _run_calculus(self) -> bool:
        """Run the main tableau expansion loop.

        Returns:
            ``True`` if the tableau is clash-free (satisfiable).
        """
        self.m_interrupt_flag.start_task()
        try:
            existentials_are_exact = (
                self.m_existential_expansion_strategy.is_exact()
            )

            if self.m_tableau_monitor is not None:
                self.m_tableau_monitor.saturate_started()

            has_more_work = True
            while has_more_work:
                if self.m_tableau_monitor is not None:
                    self.m_tableau_monitor.iteration_started()
                has_more_work = self._do_iteration()
                if self.m_tableau_monitor is not None:
                    self.m_tableau_monitor.iteration_finished()

                if (
                    not existentials_are_exact
                    and not has_more_work
                    and not self.m_extension_manager.contains_clash()
                ):
                    if self.m_tableau_monitor is not None:
                        self.m_tableau_monitor.iteration_started()
                    has_more_work = self.m_existential_expansion_strategy.expand_existentials(
                        True
                    )
                    if self.m_tableau_monitor is not None:
                        self.m_tableau_monitor.iteration_finished()

            if self.m_tableau_monitor is not None:
                self.m_tableau_monitor.saturate_finished(
                    not self.m_extension_manager.contains_clash()
                )

            if not self.m_extension_manager.contains_clash():
                self.m_existential_expansion_strategy.model_found()
                return True
            return False
        finally:
            self.m_interrupt_flag.end_task()

    def _do_iteration(self) -> bool:
        """Perform one iteration of the tableau expansion.

        Returns:
            ``True`` if more work remains.
        """
        if not self.m_extension_manager.contains_clash():
            self.m_nominal_introduction_manager.process_annotated_equalities()
            has_change = False
            while (
                self.m_extension_manager.propagate_delta_new()
                and not self.m_extension_manager.contains_clash()
            ):
                if self.m_has_description_graphs and not self.m_extension_manager.contains_clash():
                    self.m_description_graph_manager.check_graph_constraints()
                if not self.m_extension_manager.contains_clash():
                    self.m_permanent_hyperresolution_manager.apply_dl_clauses()
                    if self.m_additional_hyperresolution_manager is not None:
                        self.m_additional_hyperresolution_manager.apply_dl_clauses()
                if (
                    self.m_check_unknown_datatype_restrictions
                    and not self.m_extension_manager.contains_clash()
                ):
                    self.m_datatype_manager.apply_unknown_datatype_restriction_semantics()
                if (
                    self.m_check_datatypes
                    and not self.m_extension_manager.contains_clash()
                ):
                    self.m_datatype_manager.check_datatype_constraints()
                if not self.m_extension_manager.contains_clash():
                    self.m_nominal_introduction_manager.process_annotated_equalities()
                has_change = True
            if has_change:
                return True

        # Existential expansion
        if not self.m_extension_manager.contains_clash():
            if self.m_existential_expansion_strategy.expand_existentials(False):
                return True

        # Ground disjunction processing
        if not self.m_extension_manager.contains_clash():
            while self.m_first_unprocessed_ground_disjunction is not None:
                ground_disjunction = self.m_first_unprocessed_ground_disjunction
                if self.m_tableau_monitor is not None:
                    self.m_tableau_monitor.process_ground_disjunction_started(
                        ground_disjunction
                    )
                self.m_first_unprocessed_ground_disjunction = (
                    ground_disjunction.m_previous_ground_disjunction
                )
                if not ground_disjunction.is_pruned() and not ground_disjunction.is_satisfied(
                    self
                ):
                    sorted_indexes = (
                        ground_disjunction.ground_disjunction_header.get_sorted_disjunct_indexes()
                    )
                    dependency_set = ground_disjunction.get_dependency_set()
                    if ground_disjunction.get_number_of_disjuncts() > 1:
                        from hermit.tableau.disjunction_branching_point import (
                            DisjunctionBranchingPoint,
                        )

                        branching_point = DisjunctionBranchingPoint(
                            self, ground_disjunction, sorted_indexes
                        )
                        self._push_branching_point(branching_point)
                        dependency_set = self.m_dependency_set_factory.add_branching_point(
                            dependency_set, branching_point.level
                        )
                    if self.m_tableau_monitor is not None:
                        self.m_tableau_monitor.disjunct_processing_started(
                            ground_disjunction, sorted_indexes[0]
                        )
                    ground_disjunction.add_disjunct_to_tableau(
                        self, sorted_indexes[0], dependency_set
                    )
                    if self.m_tableau_monitor is not None:
                        self.m_tableau_monitor.disjunct_processing_finished(
                            ground_disjunction, sorted_indexes[0]
                        )
                        self.m_tableau_monitor.process_ground_disjunction_finished(
                            ground_disjunction
                        )
                    return True
                else:
                    if self.m_tableau_monitor is not None:
                        self.m_tableau_monitor.ground_disjunction_satisfied(
                            ground_disjunction
                        )
                self.m_interrupt_flag.check_interrupt()

        # Backtracking
        if self.m_extension_manager.contains_clash():
            clash_dependency_set = self.m_extension_manager.clash_dependency_set
            assert clash_dependency_set is not None
            new_current_branching_point = (
                clash_dependency_set.get_maximum_branching_point()
            )
            if new_current_branching_point <= self.m_nonbacktrackable_branching_point:
                return False
            self._backtrack_to(new_current_branching_point)
            current_bp = self.get_current_branching_point()
            assert current_bp is not None
            if self.m_tableau_monitor is not None:
                self.m_tableau_monitor.start_next_branching_point_started(
                    current_bp
                )
            current_bp.start_next_choice(self, clash_dependency_set)
            if self.m_tableau_monitor is not None:
                self.m_tableau_monitor.start_next_branching_point_finished(
                    current_bp
                )
            self.m_dependency_set_factory.remove_unused_sets()
            return True

        return False

    # ------------------------------------------------------------------
    # Branching point management
    # ------------------------------------------------------------------

    def is_current_model_deterministic(self) -> bool:
        """Return whether the current model was built deterministically."""
        return self.m_is_current_model_deterministic

    def get_current_branching_point_level(self) -> int:
        """Return the current branching-point level."""
        return self.m_current_branching_point

    def get_current_branching_point(self) -> BranchingPoint | None:
        """Return the current branching point."""
        if 0 <= self.m_current_branching_point < len(self.m_branching_points):
            return self.m_branching_points[self.m_current_branching_point]
        return None

    def add_ground_disjunction(self, ground_disjunction: Any) -> None:
        """Add a ground disjunction to the unprocessed list.

        Args:
            ground_disjunction: The disjunction to add.
        """
        ground_disjunction.m_next_ground_disjunction = self.m_first_ground_disjunction
        ground_disjunction.m_previous_ground_disjunction = None
        if self.m_first_ground_disjunction is not None:
            self.m_first_ground_disjunction.m_previous_ground_disjunction = (
                ground_disjunction
            )
        self.m_first_ground_disjunction = ground_disjunction
        if self.m_first_unprocessed_ground_disjunction is None:
            self.m_first_unprocessed_ground_disjunction = ground_disjunction
        if self.m_tableau_monitor is not None:
            self.m_tableau_monitor.ground_disjunction_derived(ground_disjunction)

    @property
    def first_unprocessed_ground_disjunction(self) -> Any | None:
        """Return the first unprocessed ground disjunction."""
        return self.m_first_unprocessed_ground_disjunction

    def _push_branching_point(self, branching_point: BranchingPoint) -> None:
        """Push a branching point onto the stack.

        Args:
            branching_point: The branching point to push.
        """
        assert (
            self.m_current_branching_point + 1 == branching_point.level
        )
        if self.m_tableau_monitor is not None:
            self.m_tableau_monitor.push_branching_point_started(branching_point)
        self.m_current_branching_point += 1
        if self.m_current_branching_point >= len(self.m_branching_points):
            new_length = self.m_current_branching_point * 3 // 2
            new_bps: list[BranchingPoint | None] = [None] * new_length
            new_bps[: len(self.m_branching_points)] = self.m_branching_points
            self.m_branching_points = new_bps
        self.m_branching_points[self.m_current_branching_point] = branching_point
        self.m_extension_manager.branching_point_pushed()
        self.m_existential_expansion_manager.branching_point_pushed()
        self.m_existential_expansion_strategy.branching_point_pushed()
        self.m_nominal_introduction_manager.branching_point_pushed()
        self.m_is_current_model_deterministic = False
        if self.m_tableau_monitor is not None:
            self.m_tableau_monitor.push_branching_point_finished(branching_point)

    def _backtrack_to(self, new_current_branching_point: int) -> None:
        """Backtrack to the given branching-point level.

        Args:
            new_current_branching_point: The level to backtrack to.
        """
        branching_point = self.m_branching_points[new_current_branching_point]
        assert branching_point is not None
        if self.m_tableau_monitor is not None:
            self.m_tableau_monitor.backtrack_to_started(branching_point)

        # Backtrack branching point list
        for idx in range(new_current_branching_point + 1, len(self.m_branching_points)):
            self.m_branching_points[idx] = None
        self.m_current_branching_point = new_current_branching_point

        # Backtrack unprocessed ground disjunctions
        self.m_first_unprocessed_ground_disjunction = (
            branching_point._first_unprocessed_ground_disjunction
        )

        # Backtrack added ground disjunctions
        first_should_be = branching_point._first_ground_disjunction
        while self.m_first_ground_disjunction is not first_should_be:
            self.m_first_ground_disjunction.destroy(self)
            self.m_first_ground_disjunction = (
                self.m_first_ground_disjunction.m_next_ground_disjunction
            )
        if self.m_first_ground_disjunction is not None:
            self.m_first_ground_disjunction.m_previous_ground_disjunction = None

        # Backtrack existentials
        self.m_existential_expansion_strategy.backtrack()
        self.m_existential_expansion_manager.backtrack()

        # Backtrack nominal introduction
        self.m_nominal_introduction_manager.backtrack()

        # Backtrack extensions
        self.m_extension_manager.backtrack()

        # Backtrack node merges / prunes
        last_should_be = branching_point._last_merged_or_pruned_node
        while self.m_last_merged_or_pruned_node is not last_should_be:
            self._backtrack_last_merged_or_pruned_node()

        # Backtrack node change list
        last_tableau_should_be = branching_point._last_tableau_node
        while last_tableau_should_be is not self.m_last_tableau_node:
            self._destroy_last_tableau_node()

        # Finish
        self.m_extension_manager.clear_clash()
        if self.m_tableau_monitor is not None:
            self.m_tableau_monitor.backtrack_to_finished(branching_point)

    # ------------------------------------------------------------------
    # Node creation
    # ------------------------------------------------------------------

    def create_new_named_node(self, dependency_set: DependencySet) -> Node:
        """Create a named node (individual named in input ontology)."""
        return self._create_new_node_raw(dependency_set, None, NodeType.NAMED_NODE, 0)

    def _create_new_ni_node(self, dependency_set: DependencySet) -> Node:
        """Create a NI node (nominal-introduction, not named in input)."""
        return self._create_new_node_raw(dependency_set, None, NodeType.NI_NODE, 0)

    def create_new_tree_node(
        self, dependency_set: DependencySet, parent: Node
    ) -> Node:
        """Create a tree node generated by existential expansion."""
        return self._create_new_node_raw(
            dependency_set, parent, NodeType.TREE_NODE, parent.tree_depth + 1
        )

    def create_new_concrete_node(
        self, dependency_set: DependencySet, parent: Node
    ) -> Node:
        """Create a concrete (datatype) node."""
        return self._create_new_node_raw(
            dependency_set, parent, NodeType.CONCRETE_NODE, parent.tree_depth + 1
        )

    def create_new_root_constant_node(self, dependency_set: DependencySet) -> Node:
        """Create a root constant node for datatype reasoning."""
        return self._create_new_node_raw(
            dependency_set, None, NodeType.ROOT_CONSTANT_NODE, 0
        )

    def create_new_graph_node(
        self, parent: Node | None, dependency_set: DependencySet
    ) -> Node:
        """Create a description-graph node."""
        depth = 0 if parent is None else parent.tree_depth
        return self._create_new_node_raw(
            dependency_set, parent, NodeType.GRAPH_NODE, depth
        )

    def _create_new_node_raw(
        self,
        dependency_set: DependencySet,
        parent: Node | None,
        node_type: NodeType,
        tree_depth: int,
    ) -> Node:
        """Create a new node, reusing a recycled one if possible."""
        from hermit.model import AtomicConcept
        from hermit.datatypes import InternalDatatype

        if self.m_first_free_node is None:
            node = Node(self)
            self.m_allocated_nodes += 1
        else:
            node = self.m_first_free_node
            self.m_first_free_node = node.m_next_tableau_node

        assert node.m_node_id == -1
        assert node.m_node_state is None
        node.initialize(
            self.m_number_of_nodes_in_tableau + 1, parent, node_type, tree_depth
        )
        self.m_number_of_nodes_in_tableau += 1

        self.m_existential_expansion_strategy.node_initialized(node)

        node.m_previous_tableau_node = self.m_last_tableau_node
        if self.m_last_tableau_node is None:
            self.m_first_tableau_node = node
        else:
            self.m_last_tableau_node.m_next_tableau_node = node
        self.m_last_tableau_node = node

        self.m_existential_expansion_strategy.node_status_changed(node)
        self.m_number_of_node_creations += 1

        if self.m_tableau_monitor is not None:
            self.m_tableau_monitor.node_created(node)

        if node_type.is_abstract:
            self.m_extension_manager.add_concept_assertion(
                AtomicConcept.THING, node, dependency_set, True
            )
            if (
                node_type == NodeType.NAMED_NODE
                and self.m_needs_named_extension
            ):
                self.m_extension_manager.add_concept_assertion(
                    AtomicConcept.INTERNAL_NAMED, node, dependency_set, True
                )
        else:
            self.m_extension_manager.add_data_range_assertion(
                InternalDatatype.RDFS_LITERAL, node, dependency_set, True
            )

        return node

    # ------------------------------------------------------------------
    # Node merge / prune / backtrack
    # ------------------------------------------------------------------

    def merge_node(
        self,
        node: Node,
        merge_into: Node,
        dependency_set: DependencySet,
    ) -> None:
        """Merge *node* into *merge_into*.

        Concept and role assertions should have already been copied.
        """
        assert node.m_node_state == NodeState.ACTIVE
        assert node.m_merged_into is None
        assert node.m_merged_into_dependency_set is None
        assert node.m_previous_merged_or_pruned_node is None

        node.m_merged_into = merge_into
        node.m_merged_into_dependency_set = (
            self.m_dependency_set_factory.get_permanent(dependency_set)
        )
        self.m_dependency_set_factory.add_usage(node.m_merged_into_dependency_set)
        node.m_node_state = NodeState.MERGED
        node.m_previous_merged_or_pruned_node = self.m_last_merged_or_pruned_node
        self.m_last_merged_or_pruned_node = node
        self.m_number_of_merged_or_pruned_nodes += 1
        self.m_existential_expansion_strategy.node_status_changed(node)
        self.m_existential_expansion_strategy.nodes_merged(node, merge_into)

    def prune_node(self, node: Node) -> None:
        """Mark *node* as pruned."""
        assert node.m_node_state == NodeState.ACTIVE
        assert node.m_merged_into is None
        assert node.m_merged_into_dependency_set is None
        assert node.m_previous_merged_or_pruned_node is None

        node.m_node_state = NodeState.PRUNED
        node.m_previous_merged_or_pruned_node = self.m_last_merged_or_pruned_node
        self.m_last_merged_or_pruned_node = node
        self.m_number_of_merged_or_pruned_nodes += 1
        self.m_existential_expansion_strategy.node_status_changed(node)

    def _backtrack_last_merged_or_pruned_node(self) -> None:
        """Undo the most recent merge or prune."""
        node = self.m_last_merged_or_pruned_node
        assert node is not None

        saved_merged_info: Node | None = None
        if node.m_node_state == NodeState.MERGED:
            assert node.m_merged_into_dependency_set is not None
            self.m_dependency_set_factory.remove_usage(
                node.m_merged_into_dependency_set
            )
            saved_merged_info = node.m_merged_into
            node.m_merged_into = None
            node.m_merged_into_dependency_set = None

        node.m_node_state = NodeState.ACTIVE
        self.m_last_merged_or_pruned_node = node.m_previous_merged_or_pruned_node
        node.m_previous_merged_or_pruned_node = None
        self.m_number_of_merged_or_pruned_nodes -= 1
        self.m_existential_expansion_strategy.node_status_changed(node)
        if saved_merged_info is not None:
            self.m_existential_expansion_strategy.nodes_unmerged(node, saved_merged_info)

    def _destroy_last_tableau_node(self) -> None:
        """Destroy and recycle the last tableau node."""
        node = self.m_last_tableau_node
        assert node is not None
        assert node.m_node_state == NodeState.ACTIVE
        assert node.m_merged_into is None
        assert node.m_merged_into_dependency_set is None
        assert node.m_previous_merged_or_pruned_node is None

        self.m_existential_expansion_strategy.node_destroyed(node)
        if node.m_previous_tableau_node is None:
            self.m_first_tableau_node = None
        else:
            node.m_previous_tableau_node.m_next_tableau_node = None
        self.m_last_tableau_node = node.m_previous_tableau_node

        node.destroy()
        node.m_next_tableau_node = self.m_first_free_node
        self.m_first_free_node = node
        self.m_number_of_nodes_in_tableau -= 1

        if self.m_tableau_monitor is not None:
            self.m_tableau_monitor.node_destroyed(node)

    # ------------------------------------------------------------------
    # Statistics and navigation
    # ------------------------------------------------------------------

    @property
    def number_of_node_creations(self) -> int:
        """Return the total number of node creations."""
        return self.m_number_of_node_creations

    @property
    def first_tableau_node(self) -> Node | None:
        """Return the first node in the tableau linked list."""
        return self.m_first_tableau_node

    def get_first_tableau_node(self) -> Node | None:
        """Return the first node (Java-compatible alias for first_tableau_node)."""
        return self.m_first_tableau_node

    @property
    def last_tableau_node(self) -> Node | None:
        """Return the last node in the tableau linked list."""
        return self.m_last_tableau_node

    @property
    def number_of_allocated_nodes(self) -> int:
        """Return the total number of allocated (including recycled) nodes."""
        return self.m_allocated_nodes

    @property
    def number_of_nodes_in_tableau(self) -> int:
        """Return the current number of nodes in the tableau."""
        return self.m_number_of_nodes_in_tableau

    @property
    def number_of_merged_or_pruned_nodes(self) -> int:
        """Return the number of merged or pruned nodes."""
        return self.m_number_of_merged_or_pruned_nodes

    def get_node(self, node_id: int) -> Node | None:
        """Find a node by its ID.

        Args:
            node_id: The node ID to look up.

        Returns:
            The node, or ``None`` if not found.
        """
        node = self.m_first_tableau_node
        while node is not None:
            if node.node_id == node_id:
                return node
            node = node.m_next_tableau_node
        return None

    def get_existential_concepts_buffer(self) -> list[Any]:
        """Return a reusable buffer for existential concepts."""
        if not self.m_existential_concepts_buffers:
            return []
        return self.m_existential_concepts_buffers.pop()

    def put_existential_concepts_buffer(self, buffer: list[Any]) -> None:
        """Return a used existential-concepts buffer to the pool.

        Args:
            buffer: An empty list to be reused.
        """
        assert len(buffer) == 0
        self.m_existential_concepts_buffers.append(buffer)

    def check_tableau_list(self) -> None:
        """Verify integrity of the tableau node linked list.

        Raises:
            RuntimeError: If the linked-list invariants are violated.
        """
        node = self.m_first_tableau_node
        count = 0
        while node is not None:
            if node.m_previous_tableau_node is None:
                if self.m_first_tableau_node is not node:
                    raise RuntimeError("First tableau node is pointing wrongly.")
            else:
                if node.m_previous_tableau_node.m_next_tableau_node is not node:
                    raise RuntimeError("Previous tableau node is pointing wrongly.")
            if node.m_next_tableau_node is None:
                if self.m_last_tableau_node is not node:
                    raise RuntimeError("Last tableau node is pointing wrongly.")
            else:
                if node.m_next_tableau_node.m_previous_tableau_node is not node:
                    raise RuntimeError("Next tableau node is pointing wrongly.")
            count += 1
            node = node.m_next_tableau_node
        if count != self.m_number_of_nodes_in_tableau:
            raise RuntimeError("Invalid number of nodes in the tableau.")
