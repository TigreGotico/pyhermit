"""Ancestor blocking strategy.

Faithful port of ``org.semanticweb.HermiT.blocking.AncestorBlocking`` from
the Java HermiT OWL reasoner.

Classes
-------
AncestorBlocking
    Blocks a node only against its ancestors in the tableau tree.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.model import AtomicRole, DLClause, DataRange, Variable
    from hermit.tableau import DLClauseEvaluator, Node, Tableau

from .blocking_signature_cache import BlockingSignatureCache
from .blocking_strategy import BlockingStrategy
from hermit.model import AtomicConcept, AtomicRole, DataRange
from .direct_blocking_checker import DirectBlockingChecker


class AncestorBlocking(BlockingStrategy):
    """Ancestor-based blocking strategy.

    Only checks a node against its ancestors (walking up the parent chain).
    This is the simplest form of blocking and is exact.
    """

    __slots__ = (
        "m_direct_blocking_checker",
        "m_blocking_signature_cache",
        "m_tableau",
        "m_use_blocking_signature_cache",
    )

    def __init__(
        self,
        direct_blocking_checker: DirectBlockingChecker,
        blocking_signature_cache: BlockingSignatureCache | None = None,
    ) -> None:
        self.m_direct_blocking_checker = direct_blocking_checker
        self.m_blocking_signature_cache = blocking_signature_cache
        self.m_tableau: Tableau | None = None
        self.m_use_blocking_signature_cache = False

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
        self.m_direct_blocking_checker.clear()

    def compute_blocking(self, final_chance: bool) -> None:
        assert self.m_tableau is not None
        node = self.m_tableau.get_first_tableau_node()
        while node is not None:
            if node.is_active():
                parent = node.parent
                if parent is None:
                    node.set_blocked(None, False)
                elif parent.is_blocked():
                    node.set_blocked(parent, False)
                elif (
                    self.m_use_blocking_signature_cache
                    and self.m_blocking_signature_cache is not None
                    and self.m_blocking_signature_cache.contains_signature(node)
                ):
                    node.set_blocked(Node.SIGNATURE_CACHE_BLOCKER, True)  # type: ignore[arg-type]
                else:
                    self._check_parent_blocking(node)
            node = node.get_next_tableau_node()

    def is_permanent_assertion(self, concept_or_range: AtomicConcept | DataRange, node: Node) -> bool:
        return True

    def assertion_added(self, concept_or_range: AtomicConcept | DataRange | AtomicRole,
                        node_or_from: Node, node_to_or_is_core: Node | bool,
                        is_core: bool | None = None) -> None:
        if isinstance(concept_or_range, AtomicConcept):
            self.m_direct_blocking_checker.assertion_added(
                concept_or_range, node_or_from, is_core if is_core is not None else False
            )
        elif isinstance(concept_or_range, DataRange):
            self.m_direct_blocking_checker.assertion_added_dr(
                concept_or_range, node_or_from, is_core if is_core is not None else False
            )
        elif isinstance(concept_or_range, AtomicRole) and isinstance(node_to_or_is_core, Node):
            self.m_direct_blocking_checker.assertion_added_role(
                concept_or_range, node_or_from, node_to_or_is_core, is_core if is_core is not None else False
            )

    def assertion_core_set(self, concept_or_range: AtomicConcept | DataRange | AtomicRole,
                           node_or_from: Node, node_to: Node | None = None) -> None:
        # No-op in Java original for concept/data-range; for roles delegates to checker
        if isinstance(concept_or_range, AtomicRole) and node_to is not None:
            self.m_direct_blocking_checker.assertion_added_role(
                concept_or_range, node_or_from, node_to, True
            )

    def assertion_removed(self, concept_or_range: AtomicConcept | DataRange | AtomicRole,
                          node_or_from: Node, node_to_or_is_core: Node | bool,
                          is_core: bool | None = None) -> None:
        if isinstance(concept_or_range, AtomicConcept):
            self.m_direct_blocking_checker.assertion_removed(
                concept_or_range, node_or_from, is_core if is_core is not None else False
            )
        elif isinstance(concept_or_range, DataRange):
            self.m_direct_blocking_checker.assertion_removed_dr(
                concept_or_range, node_or_from, is_core if is_core is not None else False
            )
        elif isinstance(concept_or_range, AtomicRole) and isinstance(node_to_or_is_core, Node):
            self.m_direct_blocking_checker.assertion_removed_role(
                concept_or_range, node_or_from, node_to_or_is_core, is_core if is_core is not None else False
            )

    def nodes_merged(self, merge_from: Node, merge_into: Node) -> None:
        self.m_direct_blocking_checker.nodes_merged(merge_from, merge_into)

    def nodes_unmerged(self, merge_from: Node, merge_into: Node) -> None:
        self.m_direct_blocking_checker.nodes_unmerged(merge_from, merge_into)

    def node_status_changed(self, node: Node) -> None:
        pass

    def node_initialized(self, node: Node) -> None:
        self.m_direct_blocking_checker.node_initialized(node)

    def node_destroyed(self, node: Node) -> None:
        self.m_direct_blocking_checker.node_destroyed(node)

    def model_found(self) -> None:
        if self.m_use_blocking_signature_cache and self.m_blocking_signature_cache is not None:
            assert self.m_tableau is not None
            # Since we've found a model, we know what is blocked and what is not,
            # so we don't need to update the blocking status.
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

    # -- internal helpers --------------------------------------------------

    def _check_parent_blocking(self, node: Node) -> None:
        blocker = node.parent
        while blocker is not None:
            if self.m_direct_blocking_checker.is_blocked_by(blocker, node):
                node.set_blocked(blocker, True)
                break
            blocker = blocker.parent
