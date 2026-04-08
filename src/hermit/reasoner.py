"""Main Reasoner class for HermiT.

Faithful port of ``org.semanticweb.HermiT.Reasoner`` from the Java HermiT OWL
reasoner, adapted to use the internal ``hermit.model.DLOntology`` directly
instead of the OWL API ``OWLOntology``.
"""

from __future__ import annotations

__all__ = ["Reasoner"]

from collections.abc import Collection
from typing import TYPE_CHECKING, Any

from hermit.configuration import Configuration
from hermit.hierarchy.hierarchy import Hierarchy
from hermit.hierarchy.hierarchy_dumper_fss import HierarchyDumperFSS
from hermit.hierarchy.hierarchy_node import HierarchyNode
from hermit.hierarchy.hierarchy_printer_fss import HierarchyPrinterFSS
from hermit.hierarchy.instance_manager import InstanceManager
from hermit.hierarchy.quasi_order_classification import QuasiOrderClassification
from hermit.hierarchy.quasi_order_classification_for_roles import (
    QuasiOrderClassificationForRoles,
)
from hermit.model import (
    AtomicConcept,
    AtomicRole,
    Atom,
    Constant,
    DLOntology,
    Individual,
    Inequality,
    Prefixes,
    Role,
)
from hermit.tableau.interrupt_flag import InterruptFlag
from hermit.tableau.reasoning_task_description import ReasoningTaskDescription

if TYPE_CHECKING:
    from hermit.monitor import TableauMonitor
    from hermit.tableau.tableau import Tableau


class Reasoner:
    """Answers queries about the logical implications of a DL ontology.

    A Reasoner is associated with a single knowledge base (``DLOntology``),
    which is loaded when the reasoner is constructed.  By default a full
    classification of all atomic terms in the knowledge base is *not*
    performed at construction time --- call :meth:`precompute_inferences`
    explicitly (or individual inference methods which will trigger it).

    Args:
        dl_ontology: The DL ontology to reason over.
        configuration: Reasoner configuration (blocking strategy, timeouts,
            etc.).  A default configuration is used if ``None``.
    """

    def __init__(
        self,
        dl_ontology: DLOntology,
        configuration: Configuration | None = None,
    ) -> None:
        self._configuration = configuration if configuration is not None else Configuration()
        self._dl_ontology = dl_ontology
        self._interrupt_flag = InterruptFlag(self._configuration.individual_task_timeout)
        self._prefixes = Prefixes()
        self._tableau: Tableau | None = None
        self._is_consistent: bool | None = None
        self._atomic_concept_hierarchy: Hierarchy[AtomicConcept] | None = None
        self._object_role_hierarchy: Hierarchy[Role] | None = None
        self._data_role_hierarchy: Hierarchy[AtomicRole] | None = None
        self._instance_manager: InstanceManager | None = None

        self._create_prefixes()
        self._tableau = self._create_tableau(
            self._interrupt_flag, self._configuration, self._dl_ontology
        )

    # ------------------------------------------------------------------
    # Accessors (used by InstanceManager and other internals)
    # ------------------------------------------------------------------

    def get_configuration(self) -> Configuration:
        """Return the configuration."""
        return self._configuration

    def get_dl_ontology(self) -> DLOntology:
        """Return the loaded DL ontology."""
        return self._dl_ontology

    def get_tableau(self) -> Tableau:
        """Return the tableau, clearing any additional ontology first."""
        if self._tableau is None:
            raise RuntimeError("Tableau has been disposed.")
        self._tableau.clear_additional_dl_ontology()
        return self._tableau

    @property
    def configuration(self) -> Configuration:
        """Return a clone of the configuration."""
        return self._configuration.clone()

    @property
    def dl_ontology(self) -> DLOntology:
        """Return the loaded DL ontology."""
        return self._dl_ontology

    @property
    def prefixes(self) -> Prefixes:
        """Return the prefix manager."""
        return self._prefixes

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def dispose(self) -> None:
        """Release resources held by the reasoner."""
        self._clear_state()
        self._interrupt_flag.dispose()

    def _clear_state(self) -> None:
        self._tableau = None
        self._is_consistent = None
        self._atomic_concept_hierarchy = None
        self._object_role_hierarchy = None
        self._data_role_hierarchy = None
        self._instance_manager = None

    def interrupt(self) -> None:
        """Interrupt any currently running reasoning task."""
        self._interrupt_flag.interrupt()

    # ------------------------------------------------------------------
    # Prefix creation
    # ------------------------------------------------------------------

    def _create_prefixes(self) -> None:
        self._prefixes = Prefixes()
        self._prefixes.declare_semantic_web_prefixes()
        individual_iris: set[str] = set()
        anon_individual_iris: set[str] = set()
        for individual in self._dl_ontology.all_individuals:
            if individual.is_anonymous():
                anon_individual_iris.add(individual.iri)
            else:
                individual_iris.add(individual.iri)
        self._prefixes.declare_internal_prefixes(individual_iris, anon_individual_iris)
        if self._dl_ontology.ontology_iri:
            self._prefixes.declare_default_prefix(self._dl_ontology.ontology_iri + "#")

    # ------------------------------------------------------------------
    # Tableau creation
    # ------------------------------------------------------------------

    @staticmethod
    def _create_tableau(
        interrupt_flag: InterruptFlag,
        configuration: Configuration,
        permanent_dl_ontology: DLOntology,
    ) -> Tableau:
        """Create a Tableau instance with the configured blocking strategy,
        existential expansion strategy, and monitor."""
        from hermit.blocking.blocking_signature_cache import (
            BlockingSignatureCache,
        )
        from hermit.existentials.creation_order_strategy import (
            CreationOrderStrategy,
        )
        from hermit.existentials.individual_reuse_strategy import (
            IndividualReuseStrategy,
        )
        from hermit.tableau.tableau import Tableau

        has_inverse_roles = permanent_dl_ontology.has_inverse_roles()
        has_nominals = permanent_dl_ontology.has_nominals()

        # --- Tableau monitor ---
        monitor: TableauMonitor | None = None
        if configuration.monitor is not None:
            monitor = configuration.monitor
        elif configuration.tableau_monitor_type.value == "TIMING":
            from hermit.monitor import Timer

            monitor = Timer()
        elif configuration.tableau_monitor_type.value == "DEBUGGER_HISTORY_ON":
            from hermit.debugger.debugger import Debugger  # type: ignore[import-untyped, unused-ignore]

            monitor = Debugger(None, True)
        elif configuration.tableau_monitor_type.value == "DEBUGGER_NO_HISTORY":
            from hermit.debugger.debugger import Debugger  # type: ignore[import-untyped, unused-ignore]

            monitor = Debugger(None, False)

        # --- Direct blocking checker ---
        from hermit.blocking.pairwise_direct_blocking_checker import (
            PairWiseDirectBlockingChecker,
        )
        from hermit.blocking.single_direct_blocking_checker import (
            SingleDirectBlockingChecker,
        )
        from hermit.blocking.validated_pairwise_direct_blocking_checker import (
            ValidatedPairwiseDirectBlockingChecker,
        )
        from hermit.blocking.validated_single_direct_blocking_checker import (
            ValidatedSingleDirectBlockingChecker,
        )
        from hermit.blocking.ancestor_blocking import AncestorBlocking
        from hermit.blocking.anywhere_blocking import AnywhereBlocking
        from hermit.blocking.anywhere_validated_blocking import AnywhereValidatedBlocking

        direct_blocking_checker: Any
        blocking_strategy_type = configuration.blocking_strategy_type
        direct_blocking_type = configuration.direct_blocking_type

        if direct_blocking_type.value == "OPTIMAL":
            if blocking_strategy_type.value in ("SIMPLE_CORE", "COMPLEX_CORE"):
                direct_blocking_checker = ValidatedSingleDirectBlockingChecker(has_inverse_roles)
            elif has_inverse_roles:
                direct_blocking_checker = PairWiseDirectBlockingChecker()
            else:
                direct_blocking_checker = SingleDirectBlockingChecker()
        elif direct_blocking_type.value == "SINGLE":
            if blocking_strategy_type.value in ("SIMPLE_CORE", "COMPLEX_CORE"):
                direct_blocking_checker = ValidatedSingleDirectBlockingChecker(has_inverse_roles)
            else:
                direct_blocking_checker = SingleDirectBlockingChecker()
        elif direct_blocking_type.value == "PAIR_WISE":
            if blocking_strategy_type.value in ("SIMPLE_CORE", "COMPLEX_CORE"):
                direct_blocking_checker = ValidatedPairwiseDirectBlockingChecker(has_inverse_roles)
            else:
                direct_blocking_checker = PairWiseDirectBlockingChecker()
        else:
            raise ValueError(f"Unknown direct blocking type: {direct_blocking_type}")

        # --- Blocking signature cache ---
        blocking_signature_cache: BlockingSignatureCache | None = None
        if not has_nominals and blocking_strategy_type.value not in (
            "SIMPLE_CORE",
            "COMPLEX_CORE",
        ):
            if configuration.blocking_signature_cache_type.value == "CACHED":
                blocking_signature_cache = BlockingSignatureCache(direct_blocking_checker)

        # --- Blocking strategy ---
        blocking_strategy: Any
        bsv = blocking_strategy_type.value
        if bsv == "ANCESTOR":
            blocking_strategy = AncestorBlocking(direct_blocking_checker, blocking_signature_cache)
        elif bsv == "ANYWHERE":
            blocking_strategy = AnywhereBlocking(direct_blocking_checker, blocking_signature_cache)
        elif bsv == "SIMPLE_CORE":
            blocking_strategy = AnywhereValidatedBlocking(
                direct_blocking_checker, has_inverse_roles, True
            )
        elif bsv == "COMPLEX_CORE":
            blocking_strategy = AnywhereValidatedBlocking(
                direct_blocking_checker, has_inverse_roles, False
            )
        elif bsv == "OPTIMAL":
            blocking_strategy = AnywhereBlocking(direct_blocking_checker, blocking_signature_cache)
        else:
            raise ValueError(f"Unknown blocking strategy type: {blocking_strategy_type}")

        # --- Existential expansion strategy ---
        existentials_expansion_strategy: Any
        esv = configuration.existential_strategy_type.value
        if esv == "CREATION_ORDER":
            existentials_expansion_strategy = CreationOrderStrategy(blocking_strategy)
        elif esv == "EL":
            existentials_expansion_strategy = IndividualReuseStrategy(blocking_strategy, True)
        elif esv == "INDIVIDUAL_REUSE":
            existentials_expansion_strategy = IndividualReuseStrategy(blocking_strategy, False)
        else:
            raise ValueError(
                f"Unknown existential strategy type: {configuration.existential_strategy_type}"
            )

        return Tableau(
            interrupt_flag=interrupt_flag,
            tableau_monitor=monitor,
            existential_expansion_strategy=existentials_expansion_strategy,
            use_disjunction_learning=configuration.use_disjunction_learning,
            permanent_dl_ontology=permanent_dl_ontology,
            additional_dl_ontology=None,
            parameters=dict(configuration.parameters),
        )

    # ------------------------------------------------------------------
    # Tableau helper (for additional axioms)
    # ------------------------------------------------------------------

    def _get_tableau_with_facts(self, additional_facts: Collection[Atom]) -> Tableau:
        """Return the tableau with additional positive facts."""
        t = self.get_tableau()
        t.set_additional_dl_ontology(
            DLOntology(
                ontology_iri="uri:urn:internal-kb",
                positive_facts=frozenset(additional_facts),
            )
        )
        return t

    def _tableau_satisfiable(
        self,
        load_permanent: bool = False,
        load_additional: bool = False,
        pos_no_dep: set[Atom] | None = None,
        neg_no_dep: set[Atom] | None = None,
        pos_dummy: set[Atom] | None = None,
        neg_dummy: set[Atom] | None = None,
        nodes_for_individuals: dict[Any, Any] | None = None,
        task_desc: ReasoningTaskDescription | None = None,
    ) -> bool:
        """Convenience wrapper around Tableau.is_satisfiable."""
        return self.get_tableau().is_satisfiable(
            load_permanent,
            load_additional,
            pos_no_dep,
            neg_no_dep,
            pos_dummy,
            neg_dummy,
            nodes_for_individuals,
            task_desc,
        )

    # ------------------------------------------------------------------
    # Consistency
    # ------------------------------------------------------------------

    def is_consistent(self) -> bool:
        """Check whether the ontology is consistent."""
        if self._is_consistent is None:
            self._is_consistent = self._tableau_satisfiable(
                load_permanent=True,
                task_desc=ReasoningTaskDescription.is_a_box_satisfiable(),
            )
        return self._is_consistent

    # ------------------------------------------------------------------
    # Concept satisfiability & subsumption
    # ------------------------------------------------------------------

    def is_satisfiable(self, concept: AtomicConcept) -> bool:
        """Check whether an atomic concept is satisfiable (non-empty)."""
        if not self.is_consistent():
            return False
        if self._atomic_concept_hierarchy is not None:
            node = self._atomic_concept_hierarchy.get_node_for_element(concept)
            if node is not None:
                return node is not self._atomic_concept_hierarchy.get_bottom_node()
        # Fallback: tableau test with fresh individual
        fresh = Individual.create_anonymous("fresh-individual")
        assertion = Atom.create(concept, fresh)
        return self._get_tableau_with_facts({assertion}).is_satisfiable(
            True, True, None, None, None, None, None,
            ReasoningTaskDescription.is_concept_satisfiable(concept),
        )

    def is_sub_class_of(self, sub: AtomicConcept, sup: AtomicConcept) -> bool:
        """Check whether ``sub`` is subsumed by ``sup``."""
        if (
            not self.is_consistent()
            or sub is AtomicConcept.NOTHING
            or sup is AtomicConcept.THING
        ):
            return True
        if self._atomic_concept_hierarchy is not None:
            sub_node = self._atomic_concept_hierarchy.get_node_for_element(sub)
            if sub_node is not None:
                return sub_node.is_equivalent_element(sup) or sub_node.is_ancestor_element(sup)
        # Tableau test
        fresh = Individual.create_anonymous("fresh-individual")
        pos: set[Atom] = {Atom.create(sub, fresh)}
        neg_concept = sup.get_negation()
        neg: set[Atom] = {Atom.create(neg_concept, fresh)}  # type: ignore[arg-type]
        return not self._get_tableau_with_facts(pos | neg).is_satisfiable(
            True, False, None, None, None, None, None,
            ReasoningTaskDescription.is_concept_subsumed_by(sub, sup),
        )

    def is_equivalent(self, c1: AtomicConcept, c2: AtomicConcept) -> bool:
        """Check whether two atomic concepts are equivalent."""
        return self.is_sub_class_of(c1, c2) and self.is_sub_class_of(c2, c1)

    def is_disjoint(self, c1: AtomicConcept, c2: AtomicConcept) -> bool:
        """Check whether two atomic concepts are disjoint."""
        if not self.is_consistent():
            return True
        fresh = Individual.create_anonymous("fresh-individual")
        assertions: set[Atom] = {Atom.create(c1, fresh), Atom.create(c2, fresh)}
        return not self._get_tableau_with_facts(assertions).is_satisfiable(
            True, False, None, None, None, None, None,
            ReasoningTaskDescription(True, "disjointness of {0} and {1}", c1, c2),
        )

    # ------------------------------------------------------------------
    # Role inferences
    # ------------------------------------------------------------------

    def is_sub_role_of(self, sub: Role, sup: Role) -> bool:
        """Check whether role ``sub`` is subsumed by role ``sup``."""
        if not self.is_consistent():
            return True
        if sub is AtomicRole.BOTTOM_OBJECT_ROLE or sup is AtomicRole.TOP_OBJECT_ROLE:
            return True
        # Use cached hierarchy if available
        if self._object_role_hierarchy is not None:
            sub_node = self._object_role_hierarchy.get_node_for_element(sub)
            if sub_node is not None:
                return sub_node.is_equivalent_element(sup) or sub_node.is_ancestor_element(sup)
        # Tableau test
        fresh_a = Individual.create_anonymous("fresh-individual-A")
        fresh_b = Individual.create_anonymous("fresh-individual-B")
        sub_assertion = sub.get_role_assertion(fresh_a, fresh_b)
        sup_assertion = sup.get_role_assertion(fresh_a, fresh_b)
        pos: set[Atom] = {sub_assertion}
        neg: set[Atom] = {sup_assertion}
        return not self._get_tableau_with_facts(pos | neg).is_satisfiable(
            True, False, None, None, None, None, None,
            ReasoningTaskDescription.is_role_subsumed_by(sub, sup, True),
        )

    def is_equivalent_role(self, r1: Role, r2: Role) -> bool:
        """Check whether two roles are equivalent."""
        return self.is_sub_role_of(r1, r2) and self.is_sub_role_of(r2, r1)

    def is_disjoint_role(self, r1: Role, r2: Role) -> bool:
        """Check whether two roles are disjoint."""
        if not self.is_consistent():
            return True
        fresh_a = Individual.create_anonymous("fresh-individual-A")
        fresh_b = Individual.create_anonymous("fresh-individual-B")
        assertions: set[Atom] = {
            r1.get_role_assertion(fresh_a, fresh_b),
            r2.get_role_assertion(fresh_a, fresh_b),
        }
        return not self._get_tableau_with_facts(assertions).is_satisfiable(
            True, False, None, None, None, None, None,
            ReasoningTaskDescription(True, "disjointness of {0} and {1}", r1, r2),
        )

    def is_functional(self, role: AtomicRole) -> bool:
        """Check whether an atomic role is functional."""
        if not self.is_consistent():
            return True
        fresh_ind = Individual.create_anonymous("fresh-individual")
        fresh_a = Constant.create_anonymous("fresh-constant-A")
        fresh_b = Constant.create_anonymous("fresh-constant-B")
        assertions: set[Atom] = {
            role.get_role_assertion(fresh_ind, fresh_a),
            role.get_role_assertion(fresh_ind, fresh_b),
        }
        assert Inequality.INSTANCE is not None
        assertions.add(Atom.create(Inequality.INSTANCE, fresh_a, fresh_b))
        return not self._get_tableau_with_facts(assertions).is_satisfiable(
            True, False, None, None, None, None, None,
            ReasoningTaskDescription(True, "functionality of {0}", role),
        )

    # ------------------------------------------------------------------
    # Individual inferences
    # ------------------------------------------------------------------

    def has_type(
        self, individual: Individual, concept: AtomicConcept, direct: bool = False
    ) -> bool:
        """Check whether an individual has a given type."""
        if not self.is_consistent():
            return True
        if not self._dl_ontology.contains_individual(individual):
            return concept is AtomicConcept.THING
        self.classify_classes()
        self._initialise_class_instance_manager()
        if self._instance_manager is None:
            return False
        return bool(self._instance_manager.has_type(individual, concept, direct))

    def has_role_relationship(
        self, subject: Individual, role: AtomicRole, obj: Individual
    ) -> bool:
        """Check whether (subject, obj) is in the extension of ``role``."""
        if not self.is_consistent():
            return True
        self._initialise_class_instance_manager()
        if self._instance_manager is None:
            return False
        return bool(
            self._instance_manager.has_object_role_relationship(role, subject, obj)
        )

    def get_instances(
        self, concept: AtomicConcept, direct: bool = False
    ) -> set[Individual]:
        """Return all individuals that are instances of ``concept``."""
        if self._dl_ontology.all_individuals == frozenset():
            return set()
        if not self.is_consistent():
            return {
                ind
                for ind in self._dl_ontology.all_individuals
                if not ind.is_anonymous() and not Prefixes.is_internal_iri(ind.iri)
            }
        if direct or self._atomic_concept_hierarchy is None:
            self.classify_classes()
        self._initialise_class_instance_manager()
        if self._instance_manager is None:
            return set()
        result = self._instance_manager.get_instances(concept, direct)
        return {
            ind
            for ind in result
            if not ind.is_anonymous() and not Prefixes.is_internal_iri(ind.iri)
        }

    def get_types(
        self, individual: Individual, direct: bool = False
    ) -> set[AtomicConcept]:
        """Return the types of an individual."""
        if not self._dl_ontology.contains_individual(individual):
            self.classify_classes()
            return {AtomicConcept.THING}
        if direct:
            self.classify_classes()
        self._initialise_class_instance_manager()
        if self._instance_manager is None:
            return set()
        if direct and self._atomic_concept_hierarchy is not None:
            self._instance_manager.set_to_classified_concept_hierarchy(
                self._atomic_concept_hierarchy
            )
        hierarchy_nodes = self._instance_manager.get_types(individual, direct)
        # Extract concepts from hierarchy nodes
        concepts: set[AtomicConcept] = set()
        for node in hierarchy_nodes:
            concepts.update(node.get_equivalent_elements())
        return concepts

    def is_same_individual(self, i1: Individual, i2: Individual) -> bool:
        """Check whether two named individuals are the same."""
        if not self.is_consistent():
            return True
        if self._dl_ontology.all_individuals == frozenset():
            return False
        self._initialise_class_instance_manager()
        if self._instance_manager is None:
            return False
        self._instance_manager.compute_same_as_equivalence_classes(
            self._configuration.reasoner_progress_monitor
        )
        return bool(self._instance_manager.is_same_individual(i1, i2))

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def precompute_inferences(
        self,
        *,
        class_hierarchy: bool = True,
        object_property_hierarchy: bool = False,
        data_property_hierarchy: bool = False,
    ) -> None:
        """Precompute selected inference types.

        Keyword-only arguments control which inferences are precomputed.
        By default only the class hierarchy is computed.
        """
        if class_hierarchy:
            self.classify_classes()
        if object_property_hierarchy:
            self.classify_object_properties()
        if data_property_hierarchy:
            self.classify_data_properties()

    def classify_classes(self) -> None:
        """Classify all atomic concepts, building the concept hierarchy."""
        if self._atomic_concept_hierarchy is not None:
            return
        relevant: set[AtomicConcept] = {AtomicConcept.THING, AtomicConcept.NOTHING}
        for ac in self._dl_ontology.all_atomic_concepts:
            if not Prefixes.is_internal_iri(ac.iri):
                relevant.add(ac)

        if not self.is_consistent():
            self._atomic_concept_hierarchy = Hierarchy.empty_hierarchy(
                relevant, AtomicConcept.THING, AtomicConcept.NOTHING
            )
            return

        progress = _ClassificationProgressMonitorAdapter(
            self._configuration.reasoner_progress_monitor, len(relevant)
        )
        self._atomic_concept_hierarchy = self._classify_atomic_concepts(
            self.get_tableau(),
            progress,
            AtomicConcept.THING,
            AtomicConcept.NOTHING,
            relevant,
            self._configuration.force_quasi_order_classification,
        )

    def classify_object_properties(self) -> None:
        """Classify object property roles."""
        if self._object_role_hierarchy is not None:
            return

        # Collect object roles from DL clauses (both head and body atoms)
        concepts_for_roles: dict[Role, AtomicConcept] = {}
        roles_for_concepts: dict[AtomicConcept, Role] = {}
        relevant_roles: set[Role] = set()

        for clause in self._dl_ontology.dl_clauses:
            # Collect from head atoms
            for atom in clause.head_atoms:
                if isinstance(atom.predicate, AtomicRole):
                    role: Role = atom.predicate
                    if role not in (
                        AtomicRole.TOP_OBJECT_ROLE,
                        AtomicRole.BOTTOM_OBJECT_ROLE,
                        AtomicRole.TOP_DATA_ROLE,
                        AtomicRole.BOTTOM_DATA_ROLE,
                    ):
                        relevant_roles.add(role)
                        if self._dl_ontology.has_inverse_roles():
                            inv = role.get_inverse()
                            relevant_roles.add(inv)
            # Also collect from body atoms
            for atom in clause.body_atoms:
                if isinstance(atom.predicate, AtomicRole):
                    role: Role = atom.predicate
                    if role not in (
                        AtomicRole.TOP_OBJECT_ROLE,
                        AtomicRole.BOTTOM_OBJECT_ROLE,
                        AtomicRole.TOP_DATA_ROLE,
                        AtomicRole.BOTTOM_DATA_ROLE,
                    ):
                        relevant_roles.add(role)
                        if self._dl_ontology.has_inverse_roles():
                            inv = role.get_inverse()
                            relevant_roles.add(inv)

        for role in relevant_roles:
            if isinstance(role, AtomicRole):
                concept = AtomicConcept.create("internal:prop#" + role.iri)
            else:
                # role is InverseRole
                inv_role = role.get_inverse()
                if isinstance(inv_role, AtomicRole):
                    concept = AtomicConcept.create("internal:prop#inv#" + inv_role.iri)
                else:
                    continue
            concepts_for_roles[role] = concept
            roles_for_concepts[concept] = role

        concepts_for_roles[AtomicRole.TOP_OBJECT_ROLE] = AtomicConcept.THING
        roles_for_concepts[AtomicConcept.THING] = AtomicRole.TOP_OBJECT_ROLE
        concepts_for_roles[AtomicRole.BOTTOM_OBJECT_ROLE] = AtomicConcept.NOTHING
        roles_for_concepts[AtomicConcept.NOTHING] = AtomicRole.BOTTOM_OBJECT_ROLE

        if not self.is_consistent():
            all_roles: set[Role] = set(roles_for_concepts.keys())
            top_node_r: HierarchyNode[Role] = HierarchyNode(AtomicRole.TOP_OBJECT_ROLE)
            top_node_r.m_equivalent_elements = {AtomicRole.TOP_OBJECT_ROLE}
            bot_node_r: HierarchyNode[Role] = HierarchyNode(AtomicRole.BOTTOM_OBJECT_ROLE)
            bot_node_r.m_equivalent_elements = {AtomicRole.BOTTOM_OBJECT_ROLE}
            top_node_r.m_child_nodes = {bot_node_r}
            bot_node_r.m_parent_nodes = {top_node_r}
            hier: Hierarchy[Role] = Hierarchy(top_node_r, bot_node_r)
            for r in all_roles:
                node_r: HierarchyNode[Role] = HierarchyNode(r)
                node_r.m_equivalent_elements = {r}
                node_r.m_parent_nodes = {top_node_r}
                node_r.m_child_nodes = {bot_node_r}
                hier.m_nodes_by_elements[r] = node_r
            self._object_role_hierarchy = hier
            return

        progress = _ClassificationProgressMonitorAdapter(
            self._configuration.reasoner_progress_monitor, len(concepts_for_roles)
        )
        self._object_role_hierarchy = self._classify_atomic_concepts_for_roles(
            self.get_tableau(),
            progress,
            AtomicConcept.THING,
            AtomicConcept.NOTHING,
            set(roles_for_concepts.keys()),
            self._dl_ontology.has_inverse_roles(),
            concepts_for_roles,
            roles_for_concepts,
            self._configuration.force_quasi_order_classification,
        )

    def classify_data_properties(self) -> None:
        """Classify data properties."""
        if self._data_role_hierarchy is not None:
            return
        self._data_role_hierarchy = Hierarchy.empty_hierarchy(
            {AtomicRole.TOP_DATA_ROLE, AtomicRole.BOTTOM_DATA_ROLE},
            AtomicRole.TOP_DATA_ROLE,
            AtomicRole.BOTTOM_DATA_ROLE,
        )

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_atomic_concepts(
        tableau: Tableau,
        progress_monitor: _ClassificationProgressMonitorAdapter,
        top_element: AtomicConcept,
        bottom_element: AtomicConcept,
        elements: set[AtomicConcept],
        force_quasi_order: bool,
    ) -> Hierarchy[AtomicConcept]:
        if tableau.m_use_disjunction_learning and not force_quasi_order:
            from hermit.hierarchy.deterministic_classification import (
                DeterministicClassification,
            )

            return DeterministicClassification(
                tableau, progress_monitor, top_element, bottom_element, elements
            ).classify()
        else:
            return QuasiOrderClassification(
                tableau, progress_monitor, top_element, bottom_element, elements
            ).classify()

    @staticmethod
    def _classify_atomic_concepts_for_roles(
        tableau: Tableau,
        progress_monitor: _ClassificationProgressMonitorAdapter,
        top_element: AtomicConcept,
        bottom_element: AtomicConcept,
        roles: set[Role],
        has_inverses: bool,
        concepts_for_roles: dict[Role, AtomicConcept],
        roles_for_concepts: dict[AtomicConcept, Role],
        force_quasi_order: bool,
    ) -> Hierarchy[Role]:
        elements: set[AtomicConcept] = set(concepts_for_roles.values())
        # Always use QuasiOrderClassificationForRoles — DeterministicClassification
        # delegates to plain QuasiOrderClassification which lacks the role-specific
        # subsumption extraction from DL clauses.
        atomic_hierarchy = QuasiOrderClassificationForRoles(
            tableau,
            progress_monitor,
            top_element,
            bottom_element,
            elements,
            has_inverses,
            concepts_for_roles,
            roles_for_concepts,
        ).classify()

        class _RoleTransformer:
            def transform(self, ac: AtomicConcept) -> Role:
                result = roles_for_concepts.get(ac)
                if result is not None:
                    return result
                # Fallback: should not happen if concepts_for_roles is complete
                raise KeyError(f"No role mapping for concept {ac}")

            def determine_representative(
                self,
                old_representative: AtomicConcept,
                new_equivalent_elements: set[Role],
            ) -> Role:
                result = roles_for_concepts.get(old_representative)
                if result is not None:
                    return result
                raise KeyError(f"No role mapping for concept {old_representative}")

        return atomic_hierarchy.transform(_RoleTransformer(), None)

    # ------------------------------------------------------------------
    # Instance manager
    # ------------------------------------------------------------------

    def _initialise_class_instance_manager(self) -> None:
        if (
            self._instance_manager is not None
            and self._instance_manager.are_classes_initialised()
        ):
            return
        if self._atomic_concept_hierarchy is None:
            self.classify_classes()
        if self._instance_manager is None:
            self._instance_manager = InstanceManager(
                self._interrupt_flag,
                self,
                self._atomic_concept_hierarchy,
                self._object_role_hierarchy,
            )
        if self._is_consistent is not None and not self._is_consistent:
            self._instance_manager.set_inconsistent()
            return
        tableau = self.get_tableau()
        nodes_mapping: dict[Any, Any] = dict(self._instance_manager.get_nodes_for_individuals())
        is_consistent = tableau.is_satisfiable(
            True,
            True,
            None,
            None,
            None,
            None,
            nodes_mapping,
            ReasoningTaskDescription(
                False,
                "Initial tableau for reading-off known and possible class instances.",
            ),
        )
        # Update the instance manager with the nodes discovered by the tableau
        self._instance_manager.update_nodes_for_individuals(nodes_mapping)
        if not is_consistent:
            self._instance_manager.set_inconsistent()
        else:
            self._instance_manager.initialize_know_and_possible_class_instances(
                tableau, self._configuration.reasoner_progress_monitor, 0, 1
            )
        if self._is_consistent is None:
            self._is_consistent = is_consistent
        tableau.clear_additional_dl_ontology()

    # ------------------------------------------------------------------
    # Hierarchy dumping / printing
    # ------------------------------------------------------------------

    def dump_hierarchies(
        self,
        out,  # type: Any  # TextIO-like
        classes: bool = True,
        object_properties: bool = False,
        data_properties: bool = False,
    ) -> None:
        """Write hierarchies in a compact textual form."""
        printer = HierarchyDumperFSS(out)
        if classes:
            self.classify_classes()
            if self._atomic_concept_hierarchy is not None:
                printer.print_atomic_concept_hierarchy(self._atomic_concept_hierarchy)
        if object_properties:
            self.classify_object_properties()
            if self._object_role_hierarchy is not None:
                printer.print_object_property_hierarchy(self._object_role_hierarchy)
        if data_properties:
            self.classify_data_properties()
            if self._data_role_hierarchy is not None:
                printer.print_data_property_hierarchy(self._data_role_hierarchy)

    def print_hierarchies(
        self,
        out,  # type: Any  # TextIO-like
        classes: bool = True,
        object_properties: bool = False,
        data_properties: bool = False,
    ) -> None:
        """Print hierarchies as a Functional-Style Syntax ontology."""
        ontology_iri = self._dl_ontology.ontology_iri or "http://example.org/ontology"
        printer = HierarchyPrinterFSS(out, ontology_iri + "#")
        if classes and self._atomic_concept_hierarchy is not None:
            self.classify_classes()
            printer.load_atomic_concept_prefix_iris(
                self._atomic_concept_hierarchy.get_all_elements()
            )
        if object_properties and self._object_role_hierarchy is not None:
            self.classify_object_properties()
            # Filter to only AtomicRole for prefix loading
            atomic_roles = {
                e for e in self._object_role_hierarchy.get_all_elements()
                if isinstance(e, AtomicRole)
            }
            printer.load_atomic_role_prefix_iris(atomic_roles)
        if data_properties and self._data_role_hierarchy is not None:
            self.classify_data_properties()
            printer.load_atomic_role_prefix_iris(
                self._data_role_hierarchy.get_all_elements()
            )
        printer.start_printing()
        at_lf = True
        if classes and self._atomic_concept_hierarchy is not None:
            if not self._atomic_concept_hierarchy.is_empty():
                printer.print_atomic_concept_hierarchy(self._atomic_concept_hierarchy)
                at_lf = False
        if object_properties and self._object_role_hierarchy is not None:
            if not self._object_role_hierarchy.is_empty():
                if not at_lf:
                    out.write("\n")
                printer.print_role_hierarchy(self._object_role_hierarchy, True)
                at_lf = False
        if data_properties and self._data_role_hierarchy is not None:
            if not self._data_role_hierarchy.is_empty():
                if not at_lf:
                    out.write("\n")
                printer.print_role_hierarchy(self._data_role_hierarchy, False)  # type: ignore[arg-type]
                at_lf = False
        printer.end_printing()

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def stats(self) -> dict[str, int | str | bool]:
        """Return basic statistics about the loaded ontology."""
        return {
            "ontology_iri": self._dl_ontology.ontology_iri or "(anonymous)",
            "clauses": len(self._dl_ontology.dl_clauses),
            "positive_facts": len(self._dl_ontology.positive_facts),
            "negative_facts": len(self._dl_ontology.negative_facts),
            "atomic_concepts": len(self._dl_ontology.all_atomic_concepts),
            "individuals": len(self._dl_ontology.all_individuals),
            "has_inverse_roles": self._dl_ontology.has_inverse_roles(),
            "has_nominals": self._dl_ontology.has_nominals(),
            "has_datatypes": self._dl_ontology.has_datatypes(),
            "has_at_most": self._dl_ontology.has_at_most_restrictions(),
            "is_horn": self._dl_ontology.is_horn(),
            "description_graphs": len(self._dl_ontology.all_description_graphs),
        }

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Reasoner(ontology={self._dl_ontology.ontology_iri!r}, "
            f"clauses={len(self._dl_ontology.dl_clauses)}, "
            f"concepts={len(self._dl_ontology.all_atomic_concepts)}, "
            f"individuals={len(self._dl_ontology.all_individuals)})"
        )


# ---------------------------------------------------------------------------
# ClassificationProgressMonitorAdapter
# ---------------------------------------------------------------------------

class _ClassificationProgressMonitorAdapter:
    """Adapts the optional ``ReasonerProgressMonitor`` to the
    ``ClassificationProgressMonitor`` protocol used by classification
    algorithms."""

    def __init__(self, monitor: Any | None, total: int) -> None:
        self._monitor = monitor
        self._total = total
        self._processed = 0

    def element_classified(self, element: AtomicConcept) -> None:
        self._processed += 1
        if self._monitor is not None:
            try:
                self._monitor.reasonerTaskProgressChanged(self._processed, self._total)
            except AttributeError:
                try:
                    self._monitor.reasoner_task_progressed(self._processed, self._total)
                except AttributeError:
                    pass
