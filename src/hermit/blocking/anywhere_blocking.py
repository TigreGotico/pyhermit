"""Anywhere blocking strategy.

Faithful port of ``org.semanticweb.HermiT.blocking.AnywhereBlocking`` from
the Java HermiT OWL reasoner.

Classes
-------
AnywhereBlocking
    Blocks a node against any other node in the tableau (not just ancestors).
BlockersCache
    Hash-based cache of potential blockers used by anywhere blocking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.model import DLClause, Variable
    from hermit.tableau import DLClauseEvaluator, Tableau

from hermit.tableau.node import Node

from hermit.model import AtomicConcept, AtomicRole, DataRange

from .blocking_signature_cache import BlockingSignatureCache
from .blocking_strategy import BlockingStrategy
from .direct_blocking_checker import DirectBlockingChecker


class AnywhereBlocking(BlockingStrategy):
    """Anywhere blocking strategy.

    A node can be blocked by any other node in the tableau with an equivalent
    label, regardless of ancestry.  Uses a hash cache for efficiency.
    """

    __slots__ = (
        "m_direct_blocking_checker",
        "m_current_blockers_cache",
        "m_blocking_signature_cache",
        "m_tableau",
        "m_use_blocking_signature_cache",
        "m_first_changed_node",
    )

    def __init__(
        self,
        direct_blocking_checker: DirectBlockingChecker,
        blocking_signature_cache: BlockingSignatureCache | None = None,
    ) -> None:
        self.m_direct_blocking_checker = direct_blocking_checker
        self.m_current_blockers_cache = _BlockersCache(direct_blocking_checker)
        self.m_blocking_signature_cache = blocking_signature_cache
        self.m_tableau: Tableau | None = None
        self.m_use_blocking_signature_cache = False
        self.m_first_changed_node: Node | None = None

    def initialize(self, tableau: Tableau) -> None:
        self.m_tableau = tableau
        self.m_direct_blocking_checker.initialize(tableau)
        self._update_blocking_signature_cache_usage()

    def additional_dl_ontology_set(self, additional_dl_ontology: object) -> None:
        self._update_blocking_signature_cache_usage()

    def additional_dl_ontology_cleared(self) -> None:
        self._update_blocking_signature_cache_usage()

    def _update_blocking_signature_cache_usage(self) -> None:
        if self.m_tableau is None:
            self.m_use_blocking_signature_cache = False
        else:
            additional = getattr(self.m_tableau, "get_additional_hyperresolution_manager", lambda: None)()
            self.m_use_blocking_signature_cache = additional is None

    def clear(self) -> None:
        self.m_current_blockers_cache.clear()
        self.m_first_changed_node = None
        self.m_direct_blocking_checker.clear()

    def compute_blocking(self, final_chance: bool) -> None:
        if self.m_first_changed_node is not None:
            node = self.m_first_changed_node
            while node is not None:
                self.m_current_blockers_cache.remove_node(node)
                node = node.get_next_tableau_node()

            node = self.m_first_changed_node
            check_blocking_signature_cache = (
                self.m_use_blocking_signature_cache
                and self.m_blocking_signature_cache is not None
                and not self.m_blocking_signature_cache.is_empty()
            )

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
                        elif check_blocking_signature_cache:
                            if self.m_blocking_signature_cache.contains_signature(node):
                                node.set_blocked(Node.SIGNATURE_CACHE_BLOCKER, True)  # type: ignore[arg-type]
                            else:
                                blocker = self.m_current_blockers_cache.get_blocker(node)
                                node.set_blocked(blocker, blocker is not None)
                        else:
                            blocker = self.m_current_blockers_cache.get_blocker(node)
                            node.set_blocked(blocker, blocker is not None)

                    if not node.is_blocked() and self.m_direct_blocking_checker.can_be_blocker(node):
                        self.m_current_blockers_cache.add_node(node)
                    self.m_direct_blocking_checker.clear_blocking_info_changed(node)
                node = node.get_next_tableau_node()

            self.m_first_changed_node = None

    def is_permanent_assertion(self, concept_or_range: AtomicConcept | DataRange, node: Node) -> bool:
        return True

    def assertion_added(self, concept_or_range: AtomicConcept | DataRange | AtomicRole,
                        node_or_from: Node, node_to_or_is_core: Node | bool,
                        is_core: bool | None = None) -> None:
        if isinstance(concept_or_range, AtomicConcept):
            changed = self.m_direct_blocking_checker.assertion_added(
                concept_or_range, node_or_from, is_core if is_core is not None else False
            )
            self._update_node_change(changed)
        elif isinstance(concept_or_range, DataRange):
            self.m_direct_blocking_checker.assertion_added_dr(
                concept_or_range, node_or_from, is_core if is_core is not None else False
            )
        elif isinstance(concept_or_range, AtomicRole) and isinstance(node_to_or_is_core, Node):
            changed = self.m_direct_blocking_checker.assertion_added_role(
                concept_or_range, node_or_from, node_to_or_is_core, is_core if is_core is not None else False
            )
            self._update_node_change(changed)

    def assertion_core_set(self, concept_or_range: AtomicConcept | DataRange | AtomicRole,
                           node_or_from: Node, node_to: Node | None = None) -> None:
        if isinstance(concept_or_range, AtomicRole) and node_to is not None:
            self.m_direct_blocking_checker.assertion_added_role(
                concept_or_range, node_or_from, node_to, True
            )

    def assertion_removed(self, concept_or_range: AtomicConcept | DataRange | AtomicRole,
                          node_or_from: Node, node_to_or_is_core: Node | bool,
                          is_core: bool | None = None) -> None:
        if isinstance(concept_or_range, AtomicConcept):
            changed = self.m_direct_blocking_checker.assertion_removed(
                concept_or_range, node_or_from, is_core if is_core is not None else False
            )
            self._update_node_change(changed)
        elif isinstance(concept_or_range, DataRange):
            self.m_direct_blocking_checker.assertion_removed_dr(
                concept_or_range, node_or_from, is_core if is_core is not None else False
            )
        elif isinstance(concept_or_range, AtomicRole) and isinstance(node_to_or_is_core, Node):
            changed = self.m_direct_blocking_checker.assertion_removed_role(
                concept_or_range, node_or_from, node_to_or_is_core, is_core if is_core is not None else False
            )
            self._update_node_change(changed)

    def nodes_merged(self, merge_from: Node, merge_into: Node) -> None:
        changed = self.m_direct_blocking_checker.nodes_merged(merge_from, merge_into)
        self._update_node_change(changed)

    def nodes_unmerged(self, merge_from: Node, merge_into: Node) -> None:
        changed = self.m_direct_blocking_checker.nodes_unmerged(merge_from, merge_into)
        self._update_node_change(changed)

    def node_status_changed(self, node: Node) -> None:
        self._update_node_change(node)

    def _update_node_change(self, node: Node | None) -> None:
        if node is not None:
            if (
                self.m_first_changed_node is None
                or node.get_node_id() < self.m_first_changed_node.get_node_id()
            ):
                self.m_first_changed_node = node

    def node_initialized(self, node: Node) -> None:
        self.m_direct_blocking_checker.node_initialized(node)

    def node_destroyed(self, node: Node) -> None:
        self.m_current_blockers_cache.remove_node(node)
        self.m_direct_blocking_checker.node_destroyed(node)
        if self.m_first_changed_node is not None and self.m_first_changed_node.get_node_id() >= node.get_node_id():
            self.m_first_changed_node = None

    def model_found(self) -> None:
        if self.m_use_blocking_signature_cache and self.m_blocking_signature_cache is not None:
            assert self.m_first_changed_node is None
            assert self.m_tableau is not None
            node = self.m_tableau.get_first_tableau_node()
            while node is not None:
                if node.is_active() and not node.is_blocked() and self.m_direct_blocking_checker.can_be_blocker(node):
                    self.m_blocking_signature_cache.add_node(node)
                node = node.get_next_tableau_node()

    def is_exact(self) -> bool:
        return True

    def dl_clause_body_compiled(
        self,
        workers: list[DLClauseEvaluator.Worker],
        dl_clause: DLClause,
        variables: list[Variable],
        values_buffer: list[object],
        core_variables: list[bool],
    ) -> None:
        for i in range(len(core_variables)):
            core_variables[i] = True


class _BlockersCache:
    """Hash-based cache of potential blockers.

    Mirrors the package-private ``BlockersCache`` class from the Java original.
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

    def remove_node(self, node: Node) -> None:
        remove_entry = node.get_blocking_cargo()
        if remove_entry is not None:
            assert isinstance(remove_entry, _CacheEntry)
            bucket_index = self._get_index_for(remove_entry.m_hash_code, len(self.m_buckets))
            last_entry: _CacheEntry | None = None
            entry = self.m_buckets[bucket_index]
            while entry is not None:
                if entry is remove_entry:
                    if last_entry is None:
                        self.m_buckets[bucket_index] = entry.m_next_entry
                    else:
                        last_entry.m_next_entry = entry.m_next_entry
                    entry.m_next_entry = self.m_empty_entries
                    entry.m_node = None
                    entry.m_hash_code = 0
                    self.m_empty_entries = entry
                    self.m_number_of_elements -= 1
                    node.set_blocking_cargo(None)
                    return
                last_entry = entry
                entry = entry.m_next_entry
            raise RuntimeError("Internal error: entry not in cache!")

    def add_node(self, node: Node) -> None:
        hash_code = self.m_direct_blocking_checker.blocking_hash_code(node)
        bucket_index = self._get_index_for(hash_code, len(self.m_buckets))
        entry = self.m_buckets[bucket_index]
        while entry is not None:
            if hash_code == entry.m_hash_code and self.m_direct_blocking_checker.is_blocked_by(entry.m_node, node):
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
                if hash_code == entry.m_hash_code and self.m_direct_blocking_checker.is_blocked_by(entry.m_node, node):
                    return entry.m_node
                entry = entry.m_next_entry
        return None

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
    """A single entry in the blockers cache."""

    __slots__ = ("m_node", "m_hash_code", "m_next_entry")

    def __init__(self) -> None:
        self.m_node: Node | None = None
        self.m_hash_code = 0
        self.m_next_entry: _CacheEntry | None = None

    def initialize(self, node: Node, hash_code: int, next_entry: _CacheEntry | None) -> None:
        self.m_node = node
        self.m_hash_code = hash_code
        self.m_next_entry = next_entry
