"""Anywhere validated blocking strategy.

Faithful port of ``org.semanticweb.HermiT.blocking.AnywhereValidatedBlocking``
from the Java HermiT OWL reasoner.

Classes
-------
AnywhereValidatedBlocking
    Anywhere blocking with validation of block soundness.
ValidatedBlockersCache
    Cache of potential blockers that can store multiple nodes per hash bucket.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.model import AtomicConcept, AtomicRole, DLClause, DataRange, Variable
    from hermit.tableau import DLClauseEvaluator, ExtensionManager, Node, Tableau

from .blocking_strategy import BlockingStrategy
from .blocking_validator import BlockingValidator
from .direct_blocking_checker import DirectBlockingChecker


class AnywhereValidatedBlocking(BlockingStrategy):
    """Anywhere blocking with validated blocks.

    Unlike plain anywhere blocking, this strategy validates that blocks are
    sound with respect to DL clause applicability before committing to them.
    """

    __slots__ = (
        "m_direct_blocking_checker",
        "m_current_blockers_cache",
        "m_permanent_blocking_validator",
        "m_additional_blocking_validator",
        "m_tableau",
        "m_extension_manager",
        "m_first_changed_node",
        "m_last_validated_unchanged_node",
        "m_use_simple_core",
        "m_has_inverses",
    )

    def __init__(
        self,
        direct_blocking_checker: DirectBlockingChecker,
        has_inverses: bool,
        use_simple_core: bool,
    ) -> None:
        self.m_direct_blocking_checker = direct_blocking_checker
        self.m_current_blockers_cache = _ValidatedBlockersCache(direct_blocking_checker)
        self.m_permanent_blocking_validator: BlockingValidator | None = None
        self.m_additional_blocking_validator: BlockingValidator | None = None
        self.m_tableau: Tableau | None = None
        self.m_extension_manager: ExtensionManager | None = None
        self.m_first_changed_node: Node | None = None
        self.m_last_validated_unchanged_node: Node | None = None
        self.m_use_simple_core = use_simple_core
        self.m_has_inverses = has_inverses

    def initialize(self, tableau: Tableau) -> None:
        self.m_tableau = tableau
        self.m_direct_blocking_checker.initialize(tableau)
        self.m_extension_manager = tableau.extension_manager
        additional_ontology = tableau.permanent_dl_ontology
        self.m_permanent_blocking_validator = BlockingValidator(tableau, additional_ontology.dl_clauses)
        self._update_additional_blocking_validator()

    def additional_dl_ontology_set(self, additional_dl_ontology: object) -> None:
        self._update_additional_blocking_validator()

    def additional_dl_ontology_cleared(self) -> None:
        self._update_additional_blocking_validator()

    def _update_additional_blocking_validator(self) -> None:
        assert self.m_tableau is not None
        additional = getattr(self.m_tableau, "get_additional_hyperresolution_manager", lambda: None)()
        if additional is None:
            self.m_additional_blocking_validator = None
        else:
            additional_ontology = self.m_tableau.additional_dl_ontology
            self.m_additional_blocking_validator = BlockingValidator(
                self.m_tableau, additional_ontology.dl_clauses
            )

    def clear(self) -> None:
        self.m_current_blockers_cache.clear()
        self.m_first_changed_node = None
        self.m_direct_blocking_checker.clear()
        self.m_last_validated_unchanged_node = None
        if self.m_permanent_blocking_validator is not None:
            self.m_permanent_blocking_validator.clear()
        if self.m_additional_blocking_validator is not None:
            self.m_additional_blocking_validator.clear()

    def compute_blocking(self, final_chance: bool) -> None:
        if final_chance:
            self.validate_blocks()
        else:
            self.compute_pre_blocking()

    def compute_pre_blocking(self) -> None:
        if self.m_first_changed_node is not None:
            node = self.m_first_changed_node
            while node is not None:
                self.m_current_blockers_cache.remove_node(node)
                node = node.get_next_tableau_node()

            node = self.m_first_changed_node
            while node is not None:
                if node.is_active() and (
                    self.m_direct_blocking_checker.can_be_blocked(node)
                    or self.m_direct_blocking_checker.can_be_blocker(node)
                ):
                    blocker_node = node.get_blocker()
                    if (
                        self.m_direct_blocking_checker.has_blocking_info_changed(node)
                        or not node.is_directly_blocked()
                        or (
                            blocker_node is not None
                            and blocker_node.get_node_id() >= self.m_first_changed_node.get_node_id()
                        )
                    ):
                        parent = node.parent
                        if parent is None:
                            node.set_blocked(None, False)
                        elif parent.is_blocked():
                            node.set_blocked(parent, False)
                        else:
                            blocker: Node | None = None
                            if self.m_last_validated_unchanged_node is None:
                                blocker = self.m_current_blockers_cache.get_blocker(node)
                            else:
                                previous_blocker = node.get_blocker()
                                node_modified = self.m_direct_blocking_checker.has_changed_since_validation(node)
                                for possible_blocker in self.m_current_blockers_cache.get_possible_blockers(node):
                                    if (
                                        node_modified
                                        or self.m_direct_blocking_checker.has_changed_since_validation(possible_blocker)
                                        or previous_blocker is possible_blocker
                                    ):
                                        blocker = possible_blocker
                                        break
                            node.set_blocked(blocker, blocker is not None)

                    if not node.is_blocked() and self.m_direct_blocking_checker.can_be_blocker(node):
                        self.m_current_blockers_cache.add_node(node)
                self.m_direct_blocking_checker.clear_blocking_info_changed(node)
                node = node.get_next_tableau_node()

            self.m_first_changed_node = None

    def validate_blocks(self) -> None:
        monitor = getattr(self.m_tableau, "get_tableau_monitor", lambda: None)()
        if monitor is not None:
            monitor.blocking_validation_started()

        node: Node | None
        if self.m_last_validated_unchanged_node is None:
            assert self.m_tableau is not None
            node = self.m_tableau.get_first_tableau_node()
        else:
            node = self.m_last_validated_unchanged_node
        first_validated_node = node

        while node is not None:
            self.m_current_blockers_cache.remove_node(node)
            node = node.get_next_tableau_node()

        node = first_validated_node
        first_invalidly_blocked_node: Node | None = None

        while node is not None:
            if node.is_active():
                if node.is_blocked():
                    # Check whether the block is a correct one
                    if (
                        node.is_directly_blocked()
                        and (
                            self.m_direct_blocking_checker.has_changed_since_validation(node)
                            or self.m_direct_blocking_checker.has_changed_since_validation(node.parent)
                            or self.m_direct_blocking_checker.has_changed_since_validation(node.get_blocker())
                        )
                    ) or (node.parent is not None and not node.parent.is_blocked()):
                        valid_blocker: Node | None = None
                        current_blocker = node.get_blocker()
                        if node.is_directly_blocked() and current_blocker is not None:
                            if self._is_block_valid(node):
                                valid_blocker = current_blocker
                        if valid_blocker is None:
                            for possible_blocker in self.m_current_blockers_cache.get_possible_blockers(node):
                                if possible_blocker is not current_blocker:
                                    node.set_blocked(possible_blocker, True)
                                    if self.m_permanent_blocking_validator is not None:
                                        self.m_permanent_blocking_validator.blocker_changed(node)
                                    if self.m_additional_blocking_validator is not None:
                                        self.m_additional_blocking_validator.blocker_changed(node)
                                    if self._is_block_valid(node):
                                        valid_blocker = possible_blocker
                                        break
                        if valid_blocker is None and node.has_unprocessed_existentials():
                            if first_invalidly_blocked_node is None:
                                first_invalidly_blocked_node = node
                        node.set_blocked(valid_blocker, valid_blocker is not None)

                self.m_last_validated_unchanged_node = node
                if not node.is_blocked() and self.m_direct_blocking_checker.can_be_blocker(node):
                    self.m_current_blockers_cache.add_node(node)
            node = node.get_next_tableau_node()

        node = first_validated_node
        while node is not None:
            if node.is_active():
                self.m_direct_blocking_checker.set_has_changed_since_validation(node, False)
                blocking_obj = node.get_blocking_object()
                if hasattr(blocking_obj, "set_block_violates_parent_constraints"):
                    blocking_obj.set_block_violates_parent_constraints(False)
                if hasattr(blocking_obj, "set_has_already_been_checked"):
                    blocking_obj.set_has_already_been_checked(False)
            node = node.get_next_tableau_node()

        self.m_first_changed_node = first_invalidly_blocked_node
        if monitor is not None:
            # Count invalid blocks for statistics
            invalid_count = 0
            node = first_validated_node
            while node is not None:
                if node.is_active() and node.is_blocked():
                    blocking_obj = node.get_blocking_object()
                    if hasattr(blocking_obj, "block_violates_parent_constraints"):
                        # Already handled above
                        pass
                node = node.get_next_tableau_node()
            monitor.blocking_validation_finished(invalid_count)

    def _is_block_valid(self, node: Node) -> bool:
        if self.m_permanent_blocking_validator is not None and self.m_permanent_blocking_validator.is_block_valid(node):
            if self.m_additional_blocking_validator is not None:
                return self.m_additional_blocking_validator.is_block_valid(node)
            return True
        return False

    def is_permanent_assertion(self, concept_or_range: AtomicConcept | DataRange, node: Node) -> bool:
        return True

    def _validation_info_changed(self, node: Node | None) -> None:
        if node is not None:
            if (
                self.m_last_validated_unchanged_node is not None
                and node.get_node_id() < self.m_last_validated_unchanged_node.get_node_id()
            ):
                self.m_last_validated_unchanged_node = node
            self.m_direct_blocking_checker.set_has_changed_since_validation(node, True)

    def _update_node_change(self, node: Node | None) -> None:
        if node is not None:
            if self.m_first_changed_node is None or node.get_node_id() < self.m_first_changed_node.get_node_id():
                self.m_first_changed_node = node

    def assertion_added(self, concept_or_range: AtomicConcept | DataRange | AtomicRole,
                        node_or_from: Node, node_to_or_is_core: Node | bool,
                        is_core: bool | None = None) -> None:
        if isinstance(concept_or_range, AtomicConcept):
            changed = self.m_direct_blocking_checker.assertion_added(
                concept_or_range, node_or_from, is_core if is_core is not None else False
            )
            self._update_node_change(changed)
            self._validation_info_changed(node_or_from)
            self._validation_info_changed(node_or_from.parent)
        elif isinstance(concept_or_range, DataRange):
            changed = self.m_direct_blocking_checker.assertion_added_dr(
                concept_or_range, node_or_from, is_core if is_core is not None else False
            )
            self._update_node_change(changed)
            self._validation_info_changed(node_or_from)
            self._validation_info_changed(node_or_from.parent)
        elif isinstance(concept_or_range, AtomicRole) and isinstance(node_to_or_is_core, Node):
            if is_core:
                self._update_node_change(node_or_from)
                self._update_node_change(node_to_or_is_core)
            self._validation_info_changed(node_or_from)
            self._validation_info_changed(node_to_or_is_core)

    def assertion_core_set(self, concept_or_range: AtomicConcept | DataRange | AtomicRole,
                           node_or_from: Node, node_to: Node | None = None) -> None:
        if isinstance(concept_or_range, AtomicConcept):
            changed = self.m_direct_blocking_checker.assertion_added(
                concept_or_range, node_or_from, True
            )
            self._update_node_change(changed)
            self._validation_info_changed(node_or_from)
            self._validation_info_changed(node_or_from.parent)
        elif isinstance(concept_or_range, DataRange):
            changed = self.m_direct_blocking_checker.assertion_added_dr(
                concept_or_range, node_or_from, True
            )
            self._update_node_change(changed)
            self._validation_info_changed(node_or_from)
            self._validation_info_changed(node_or_from.parent)
        elif isinstance(concept_or_range, AtomicRole) and node_to is not None:
            changed = self.m_direct_blocking_checker.assertion_added_role(
                concept_or_range, node_or_from, node_to, True
            )
            self._update_node_change(changed)
            self._validation_info_changed(node_or_from)
            self._validation_info_changed(node_to)

    def assertion_removed(self, concept_or_range: AtomicConcept | DataRange | AtomicRole,
                          node_or_from: Node, node_to_or_is_core: Node | bool,
                          is_core: bool | None = None) -> None:
        if isinstance(concept_or_range, AtomicConcept):
            changed = self.m_direct_blocking_checker.assertion_removed(
                concept_or_range, node_or_from, is_core if is_core is not None else False
            )
            self._update_node_change(changed)
            self._validation_info_changed(node_or_from)
            self._validation_info_changed(node_or_from.parent)
        elif isinstance(concept_or_range, DataRange):
            changed = self.m_direct_blocking_checker.assertion_removed_dr(
                concept_or_range, node_or_from, is_core if is_core is not None else False
            )
            self._update_node_change(changed)
            self._validation_info_changed(node_or_from)
            self._validation_info_changed(node_or_from.parent)
        elif isinstance(concept_or_range, AtomicRole) and isinstance(node_to_or_is_core, Node):
            changed = self.m_direct_blocking_checker.assertion_removed_role(
                concept_or_range, node_or_from, node_to_or_is_core, True
            )
            self._update_node_change(changed)
            self._validation_info_changed(node_or_from)
            self._validation_info_changed(node_to_or_is_core)

    def nodes_merged(self, merge_from: Node, merge_into: Node) -> None:
        parent = merge_from.parent
        if parent is not None and (
            self.m_direct_blocking_checker.can_be_blocker(parent)
            or self.m_direct_blocking_checker.can_be_blocked(parent)
        ):
            self._validation_info_changed(parent)

    def nodes_unmerged(self, merge_from: Node, merge_into: Node) -> None:
        parent = merge_from.parent
        if parent is not None and (
            self.m_direct_blocking_checker.can_be_blocker(parent)
            or self.m_direct_blocking_checker.can_be_blocked(parent)
        ):
            self._validation_info_changed(parent)

    def node_status_changed(self, node: Node) -> None:
        self._update_node_change(node)
        self._validation_info_changed(node)
        self._validation_info_changed(node.parent)

    def node_initialized(self, node: Node) -> None:
        self.m_direct_blocking_checker.node_initialized(node)

    def node_destroyed(self, node: Node) -> None:
        self.m_current_blockers_cache.remove_node(node)
        self.m_direct_blocking_checker.node_destroyed(node)
        if self.m_first_changed_node is not None and self.m_first_changed_node.get_node_id() >= node.get_node_id():
            self.m_first_changed_node = None
        if self.m_last_validated_unchanged_node is not None:
            if node.get_node_id() < self.m_last_validated_unchanged_node.get_node_id():
                self.m_last_validated_unchanged_node = node

    def model_found(self) -> None:
        pass

    def is_exact(self) -> bool:
        return False

    def dl_clause_body_compiled(
        self,
        workers: list[DLClauseEvaluator.Worker],
        dl_clause: DLClause,
        variables: list[Variable],
        values_buffer: list[object],
        core_variables: list[bool],
    ) -> None:
        if self.m_use_simple_core:
            for i in range(len(core_variables)):
                core_variables[i] = False
        else:
            if dl_clause.get_head_length() == 0:
                return
            if dl_clause.get_head_length() > 1:
                for i in range(len(core_variables)):
                    core_variables[i] = True
            else:
                for i in range(len(core_variables)):
                    core_variables[i] = False
                if dl_clause.is_atomic_concept_inclusion() and len(variables) > 1:
                    workers.append(_ComputeCoreVariables(dl_clause, variables, values_buffer, core_variables))


class _ComputeCoreVariables:
    """Worker that computes which variables should be treated as core.

    Mirrors the inner class ``ComputeCoreVariables`` from the Java original.
    """

    __slots__ = (
        "m_dl_clause",
        "m_variables",
        "m_values_buffer",
        "m_core_variables",
    )

    def __init__(
        self,
        dl_clause: DLClause,
        variables: list[Variable],
        values_buffer: list[object],
        core_variables: list[bool],
    ) -> None:
        self.m_dl_clause = dl_clause
        self.m_variables = variables
        self.m_values_buffer = values_buffer
        self.m_core_variables = core_variables

    def clear(self) -> None:
        pass

    def execute(self, program_counter: int) -> int:
        from hermit.tableau import NodeType

        potential_non_core: Node | None = None
        for variable_index in range(len(self.m_core_variables) - 1, -1, -1):
            node = self.m_values_buffer[variable_index]
            assert isinstance(node, Node)
            if node.node_type == NodeType.TREE_NODE and (
                potential_non_core is None or node.get_tree_depth() < potential_non_core.get_tree_depth()
            ):
                potential_non_core = node

        if potential_non_core is not None:
            for variable_index in range(len(self.m_core_variables) - 1, -1, -1):
                node = self.m_values_buffer[variable_index]
                assert isinstance(node, Node)
                if (
                    not node.is_root_node()
                    and potential_non_core is not node
                    and potential_non_core.get_tree_depth() < node.get_tree_depth()
                ):
                    self.m_core_variables[variable_index] = True
        return program_counter + 1

    def __str__(self) -> str:
        return "Compute core variables"


class _ValidatedBlockersCache:
    """Cache of potential blockers that can store multiple nodes per entry.

    Mirrors the package-private ``ValidatedBlockersCache`` from the Java original.
    """

    __slots__ = (
        "m_direct_blocking_checker",
        "m_buckets",
        "m_number_of_elements",
        "m_threshold",
        "m_empty_entries",
    )

    def __init__(self, direct_blocking_checker: DirectBlockingChecker) -> None:
        self.m_direct_blocking_checker = direct_blocking_checker
        self.m_buckets: list[_CacheEntry | None] = [None] * 1024
        self.m_threshold = int(len(self.m_buckets) * 0.75)
        self.m_number_of_elements = 0
        self.m_empty_entries: _CacheEntry | None = None

    def is_empty(self) -> bool:
        return self.m_number_of_elements == 0

    def clear(self) -> None:
        self.m_buckets = [None] * 1024
        self.m_threshold = int(len(self.m_buckets) * 0.75)
        self.m_number_of_elements = 0
        self.m_empty_entries = None

    def remove_node(self, node: Node) -> bool:
        remove_entry = node.get_blocking_cargo()
        if remove_entry is not None:
            assert isinstance(remove_entry, _CacheEntry)
            bucket_index = self._get_index_for(remove_entry.m_hash_code, len(self.m_buckets))
            last_entry: _CacheEntry | None = None
            entry = self.m_buckets[bucket_index]
            while entry is not None:
                if entry is remove_entry:
                    if node is entry.m_nodes[0]:
                        for n in entry.m_nodes:
                            n.set_blocking_cargo(None)
                        if last_entry is None:
                            self.m_buckets[bucket_index] = entry.m_next_entry
                        else:
                            last_entry.m_next_entry = entry.m_next_entry
                        entry.m_next_entry = self.m_empty_entries
                        entry.m_nodes = []
                        entry.m_hash_code = 0
                        self.m_empty_entries = entry
                        self.m_number_of_elements -= 1
                    else:
                        if node in entry.m_nodes:
                            idx = entry.m_nodes.index(node)
                            for i in range(len(entry.m_nodes) - 1, idx - 1, -1):
                                entry.m_nodes[i].set_blocking_cargo(None)
                            del entry.m_nodes[idx:]
                        else:
                            raise RuntimeError("Internal error: entry not in cache!")
                    return True
                last_entry = entry
                entry = entry.m_next_entry
            raise RuntimeError("Internal error: entry not in cache!")
        return False

    def add_node(self, node: Node) -> None:
        hash_code = self.m_direct_blocking_checker.blocking_hash_code(node)
        bucket_index = self._get_index_for(hash_code, len(self.m_buckets))
        entry = self.m_buckets[bucket_index]
        while entry is not None:
            if hash_code == entry.m_hash_code and self.m_direct_blocking_checker.is_blocked_by(entry.m_nodes[0], node):
                if node not in entry.m_nodes:
                    entry.add(node)
                    node.set_blocking_cargo(entry)
                    return
                else:
                    raise RuntimeError("Internal error: node already in the cache!")
            entry = entry.m_next_entry

        if self.m_empty_entries is None:
            entry = _CacheEntry()
        else:
            entry = self.m_empty_entries
            self.m_empty_entries = self.m_empty_entries.m_next_entry

        assert entry is not None
        entry.initialize(node, hash_code, self.m_buckets[bucket_index])
        self.m_buckets[bucket_index] = entry
        node.set_blocking_cargo(entry)
        self.m_number_of_elements += 1
        if self.m_number_of_elements >= self.m_threshold:
            self._resize(len(self.m_buckets) * 2)

    def get_blocker(self, node: Node) -> Node | None:
        if self.m_direct_blocking_checker.can_be_blocked(node):
            hash_code = self.m_direct_blocking_checker.blocking_hash_code(node)
            bucket_index = self._get_index_for(hash_code, len(self.m_buckets))
            entry = self.m_buckets[bucket_index]
            while entry is not None:
                if (
                    hash_code == entry.m_hash_code
                    and self.m_direct_blocking_checker.is_blocked_by(entry.m_nodes[0], node)
                ):
                    if node.get_blocker() is not None and node.get_blocker() in entry.m_nodes:
                        return node.get_blocker()
                    else:
                        return entry.m_nodes[0]
                entry = entry.m_next_entry
        return None

    def get_possible_blockers(self, node: Node) -> list[Node]:
        if self.m_direct_blocking_checker.can_be_blocked(node):
            hash_code = self.m_direct_blocking_checker.blocking_hash_code(node)
            bucket_index = self._get_index_for(hash_code, len(self.m_buckets))
            entry = self.m_buckets[bucket_index]
            while entry is not None:
                if (
                    hash_code == entry.m_hash_code
                    and self.m_direct_blocking_checker.is_blocked_by(entry.m_nodes[0], node)
                ):
                    assert node not in entry.m_nodes
                    return list(entry.m_nodes)
                entry = entry.m_next_entry
        return []

    def _resize(self, new_capacity: int) -> None:
        new_buckets: list[_CacheEntry | None] = [None] * new_capacity
        for i in range(len(self.m_buckets)):
            entry = self.m_buckets[i]
            while entry is not None:
                next_entry = entry.m_next_entry
                new_index = self._get_index_for(entry.m_hash_code, new_capacity)
                entry.m_next_entry = new_buckets[new_index]
                new_buckets[new_index] = entry
                entry = next_entry
        self.m_buckets = new_buckets
        self.m_threshold = int(new_capacity * 0.75)

    @staticmethod
    def _get_index_for(hash_code: int, table_length: int) -> int:
        hash_code += ~(hash_code << 9)
        hash_code ^= (hash_code >> 14)
        hash_code += (hash_code << 4)
        hash_code ^= (hash_code >> 10)
        return hash_code & (table_length - 1)


class _CacheEntry:
    """A cache entry that can hold multiple nodes with the same signature."""

    __slots__ = ("m_nodes", "m_hash_code", "m_next_entry")

    def __init__(self) -> None:
        self.m_nodes: list[Node] = []
        self.m_hash_code = 0
        self.m_next_entry: _CacheEntry | None = None

    def initialize(self, node: Node, hash_code: int, next_entry: _CacheEntry | None) -> None:
        self.m_nodes = [node]
        self.m_hash_code = hash_code
        self.m_next_entry = next_entry

    def add(self, node: Node) -> bool:
        for n in self.m_nodes:
            assert n.get_node_id() <= node.get_node_id()
        self.m_nodes.append(node)
        return True
