"""Validated pairwise direct blocking checker.

Faithful port of ``org.semanticweb.HermiT.blocking.ValidatedPairwiseDirectBlockingChecker``
from the Java HermiT OWL reasoner.

Classes
-------
ValidatedPairwiseDirectBlockingChecker
    Pairwise blocking checker with validation tracking.
ValidatedPairwiseBlockingObject
    Concrete blocking object for the validated pairwise checker.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.model import Concept
    from hermit.tableau import Node, Tableau

from hermit.model import AtomicConcept, AtomicRole, DataRange
from hermit.blocking.set_factory import Entry, SetFactory

from .blocking_signature import BlockingSignature
from .direct_blocking_checker import DirectBlockingChecker
from .validated_single_direct_blocking_checker import ValidatedBlockingObject


class ValidatedPairwiseDirectBlockingChecker(DirectBlockingChecker):
    """Pairwise direct blocking checker with validation tracking.

    Like :class:`PairWiseDirectBlockingChecker` but maintains separate change
    flags for blocking and validation, plus core/full label distinctions.
    """

    __slots__ = (
        "_atomic_concepts_set_factory",
        "_atomic_roles_set_factory",
        "_atomic_concepts_buffer",
        "_atomic_roles_buffer",
        "_has_inverses",
        "_tableau",
        "_binary_table_search_1_bound",
        "_ternary_table_search_12_bound",
    )

    def __init__(self, has_inverses: bool) -> None:
        self._atomic_concepts_set_factory: SetFactory[AtomicConcept] = SetFactory()
        self._atomic_roles_set_factory: SetFactory[AtomicRole] = SetFactory()
        self._atomic_concepts_buffer: list[AtomicConcept] = []
        self._atomic_roles_buffer: list[AtomicRole] = []
        self._has_inverses = has_inverses
        self._tableau: Tableau | None = None
        self._binary_table_search_1_bound: object | None = None
        self._ternary_table_search_12_bound: object | None = None

    # -- DirectBlockingChecker ---------------------------------------------

    def initialize(self, tableau: Tableau) -> None:
        self._tableau = tableau
        self._binary_table_search_1_bound = tableau.extension_manager.get_binary_extension_table().create_retrieval(
            [False, True], "TOTAL"
        )
        self._ternary_table_search_12_bound = tableau.extension_manager.get_ternary_extension_table().create_retrieval(
            [False, True, True], "TOTAL"
        )

    def clear(self) -> None:
        self._atomic_concepts_set_factory.clear_nonpermanent()
        self._atomic_roles_set_factory.clear_nonpermanent()
        retrieval = self._binary_table_search_1_bound
        if retrieval is not None and hasattr(retrieval, "clear"):
            retrieval.clear()
        retrieval = self._ternary_table_search_12_bound
        if retrieval is not None and hasattr(retrieval, "clear"):
            retrieval.clear()

    def is_blocked_by(self, blocker: Node, blocked: Node) -> bool:
        from hermit.tableau import NodeType

        blocker_obj = blocker.get_blocking_object()
        blocked_obj = blocked.get_blocking_object()
        blocker_parent_obj = blocker.parent.get_blocking_object()
        blocked_parent_obj = blocked.parent.get_blocking_object()
        assert isinstance(blocker_obj, ValidatedPairwiseBlockingObject)
        assert isinstance(blocked_obj, ValidatedPairwiseBlockingObject)
        assert isinstance(blocker_parent_obj, ValidatedPairwiseBlockingObject)
        assert isinstance(blocked_parent_obj, ValidatedPairwiseBlockingObject)

        return (
            not blocker.is_blocked()
            and blocker.node_type == NodeType.TREE_NODE
            and blocked.node_type == NodeType.TREE_NODE
            and blocker_obj.get_atomic_concepts_label()
            == blocked_obj.get_atomic_concepts_label()
            and blocker_parent_obj.get_atomic_concepts_label()
            == blocked_parent_obj.get_atomic_concepts_label()
        )

    def blocking_hash_code(self, node: Node) -> int:
        node_obj = node.get_blocking_object()
        parent_obj = node.parent.get_blocking_object()
        assert isinstance(node_obj, ValidatedPairwiseBlockingObject)
        assert isinstance(parent_obj, ValidatedPairwiseBlockingObject)
        return (
            node_obj.m_blocking_relevant_hash_code
            + parent_obj.m_blocking_relevant_hash_code
        )

    def can_be_blocker(self, node: Node) -> bool:
        from hermit.tableau import NodeType

        parent = node.parent
        return (
            node.node_type == NodeType.TREE_NODE
            and (not self._has_inverses
                 or parent.node_type == NodeType.TREE_NODE
                 or parent.node_type == NodeType.GRAPH_NODE)
        )

    def can_be_blocked(self, node: Node) -> bool:
        from hermit.tableau import NodeType

        parent = node.parent
        return (
            node.node_type == NodeType.TREE_NODE
            and (not self._has_inverses
                 or parent.node_type == NodeType.TREE_NODE
                 or parent.node_type == NodeType.GRAPH_NODE)
        )

    def has_blocking_info_changed(self, node: Node) -> bool:
        obj = node.get_blocking_object()
        assert isinstance(obj, ValidatedPairwiseBlockingObject)
        return obj.m_has_changed_for_blocking

    def clear_blocking_info_changed(self, node: Node) -> None:
        obj = node.get_blocking_object()
        assert isinstance(obj, ValidatedPairwiseBlockingObject)
        obj.m_has_changed_for_blocking = False

    def has_changed_since_validation(self, node: Node) -> bool:
        obj = node.get_blocking_object()
        assert isinstance(obj, ValidatedPairwiseBlockingObject)
        return obj.m_has_changed_for_validation

    def set_has_changed_since_validation(self, node: Node, has_changed: bool) -> None:
        obj = node.get_blocking_object()
        assert isinstance(obj, ValidatedPairwiseBlockingObject)
        obj.m_has_changed_for_validation = has_changed

    def node_initialized(self, node: Node) -> None:
        if node.get_blocking_object() is None:
            node.set_blocking_object(ValidatedPairwiseBlockingObject(self, node))
        obj = node.get_blocking_object()
        assert isinstance(obj, ValidatedPairwiseBlockingObject)
        obj.initialize()

    def node_destroyed(self, node: Node) -> None:
        obj = node.get_blocking_object()
        assert isinstance(obj, ValidatedPairwiseBlockingObject)
        obj.destroy()

    def assertion_added(self, concept: Concept, node: Node, is_core: bool) -> Node | None:
        obj = node.get_blocking_object()
        assert isinstance(obj, ValidatedPairwiseBlockingObject)
        obj.add_concept(concept, is_core)
        return node if isinstance(concept, AtomicConcept) and is_core else None

    def assertion_removed(self, concept: Concept, node: Node, is_core: bool) -> Node | None:
        obj = node.get_blocking_object()
        assert isinstance(obj, ValidatedPairwiseBlockingObject)
        obj.remove_concept(concept, is_core)
        return node if isinstance(concept, AtomicConcept) and is_core else None

    def assertion_added_dr(self, data_range: DataRange, node: Node, is_core: bool) -> Node | None:
        return None

    def assertion_removed_dr(self, data_range: DataRange, node: Node, is_core: bool) -> Node | None:
        return None

    def assertion_added_role(
        self, atomic_role: AtomicRole, node_from: Node, node_to: Node, is_core: bool
    ) -> Node | None:
        return None

    def assertion_removed_role(
        self, atomic_role: AtomicRole, node_from: Node, node_to: Node, is_core: bool
    ) -> Node | None:
        return None

    def nodes_merged(self, merge_from: Node, merge_into: Node) -> Node | None:
        return None

    def nodes_unmerged(self, merge_from: Node, merge_into: Node) -> Node | None:
        return None

    def get_blocking_signature_for(self, node: Node) -> BlockingSignature:
        return ValidatedPairwiseBlockingSignature(self, node)

    # -- internal helpers --------------------------------------------------

    def _fetch_atomic_concepts_label(
        self, node: Node, only_core: bool,
    ) -> Entry[AtomicConcept] | frozenset[AtomicConcept]:
        self._atomic_concepts_buffer.clear()
        retrieval = self._binary_table_search_1_bound
        retrieval.get_bindings_buffer()[1] = node  # type: ignore[union-attr]
        retrieval.open()  # type: ignore[union-attr]
        tuple_buffer = retrieval.get_tuple_buffer()  # type: ignore[union-attr]
        while not retrieval.after_last():  # type: ignore[union-attr]
            concept = tuple_buffer[0]
            if isinstance(concept, AtomicConcept):
                if not only_core or retrieval.is_core():  # type: ignore[union-attr]
                    self._atomic_concepts_buffer.append(concept)
            retrieval.next()  # type: ignore[union-attr]
        result = self._atomic_concepts_set_factory.get_set(self._atomic_concepts_buffer)
        self._atomic_concepts_buffer.clear()
        return result

    def _fetch_atomic_roles_label(
        self, node_from: Node, node_to: Node, only_core: bool,
    ) -> Entry[AtomicRole] | frozenset[AtomicRole]:
        self._atomic_roles_buffer.clear()
        retrieval = self._ternary_table_search_12_bound
        retrieval.get_bindings_buffer()[1] = node_from  # type: ignore[union-attr]
        retrieval.get_bindings_buffer()[2] = node_to  # type: ignore[union-attr]
        retrieval.open()  # type: ignore[union-attr]
        tuple_buffer = retrieval.get_tuple_buffer()  # type: ignore[union-attr]
        while not retrieval.after_last():  # type: ignore[union-attr]
            atomic_role = tuple_buffer[0]
            if isinstance(atomic_role, AtomicRole) and (not only_core or retrieval.is_core()):  # type: ignore[union-attr]
                self._atomic_roles_buffer.append(atomic_role)
            retrieval.next()  # type: ignore[union-attr]
        result = self._atomic_roles_set_factory.get_set(self._atomic_roles_buffer)
        self._atomic_roles_buffer.clear()
        return result


class ValidatedPairwiseBlockingObject(ValidatedBlockingObject):
    """Blocking object for the validated pairwise direct blocking checker."""

    __slots__ = (
        "_checker",
        "m_node",
        "m_has_changed_for_blocking",
        "m_has_changed_for_validation",
        "m_blocking_relevant_label",
        "m_full_atomic_concepts_label",
        "m_full_from_parent_label",
        "m_full_to_parent_label",
        "m_blocking_relevant_hash_code",
        "m_block_violates_parent_constraints",
        "m_has_already_been_checked",
    )

    def __init__(self, checker: ValidatedPairwiseDirectBlockingChecker, node: Node) -> None:
        self._checker = checker
        self.m_node = node
        self.m_has_changed_for_blocking = False
        self.m_has_changed_for_validation = False
        self.m_blocking_relevant_label: Entry[AtomicConcept] | frozenset[AtomicConcept] | None = None
        self.m_full_atomic_concepts_label: Entry[AtomicConcept] | frozenset[AtomicConcept] | None = None
        self.m_full_from_parent_label: Entry[AtomicRole] | frozenset[AtomicRole] | None = None
        self.m_full_to_parent_label: Entry[AtomicRole] | frozenset[AtomicRole] | None = None
        self.m_blocking_relevant_hash_code = 0
        self.m_block_violates_parent_constraints = False
        self.m_has_already_been_checked = False

    def initialize(self) -> None:
        self.m_blocking_relevant_label = None
        self.m_blocking_relevant_hash_code = 0
        self.m_full_atomic_concepts_label = None
        self.m_full_from_parent_label = None
        self.m_full_to_parent_label = None
        self.m_has_changed_for_blocking = True
        self.m_has_changed_for_validation = True

    def destroy(self) -> None:
        sf_c = self._checker._atomic_concepts_set_factory
        sf_r = self._checker._atomic_roles_set_factory
        if self.m_blocking_relevant_label is not None:
            sf_c.remove_reference(self.m_blocking_relevant_label)
            self.m_blocking_relevant_label = None
        if self.m_full_atomic_concepts_label is not None:
            sf_c.remove_reference(self.m_full_atomic_concepts_label)
            self.m_full_atomic_concepts_label = None
        if self.m_full_from_parent_label is not None:
            sf_r.remove_reference(self.m_full_from_parent_label)
            self.m_full_from_parent_label = None
        if self.m_full_to_parent_label is not None:
            sf_r.remove_reference(self.m_full_to_parent_label)
            self.m_full_to_parent_label = None
        self.m_has_changed_for_blocking = True
        self.m_has_changed_for_validation = True

    def get_atomic_concepts_label(self) -> Entry[AtomicConcept] | frozenset[AtomicConcept]:
        if self.m_blocking_relevant_label is None:
            self.m_blocking_relevant_label = self._checker._fetch_atomic_concepts_label(self.m_node, True)
            self._checker._atomic_concepts_set_factory.add_reference(self.m_blocking_relevant_label)
        return self.m_blocking_relevant_label

    def add_concept(self, concept: Concept, is_core: bool) -> None:
        # For validation purposes not only the core and atomic concept changes matter
        self.m_has_changed_for_validation = True
        if isinstance(concept, AtomicConcept):
            # Relevant for blocking
            if self.m_full_atomic_concepts_label is not None:
                self._checker._atomic_concepts_set_factory.remove_reference(self.m_full_atomic_concepts_label)
                self.m_full_atomic_concepts_label = None
            if is_core:
                if self.m_blocking_relevant_label is not None:
                    self._checker._atomic_concepts_set_factory.remove_reference(self.m_blocking_relevant_label)
                    self.m_blocking_relevant_label = None
                self.m_blocking_relevant_hash_code += hash(concept)
                self.m_has_changed_for_blocking = True

    def remove_concept(self, concept: Concept, is_core: bool) -> None:
        # For validation purposes not only the core and atomic concept changes matter
        self.m_has_changed_for_validation = True
        if isinstance(concept, AtomicConcept):
            if self.m_full_atomic_concepts_label is not None:
                self._checker._atomic_concepts_set_factory.remove_reference(self.m_full_atomic_concepts_label)
                self.m_full_atomic_concepts_label = None
            if is_core:
                if self.m_blocking_relevant_label is not None:
                    self._checker._atomic_concepts_set_factory.remove_reference(self.m_blocking_relevant_label)
                    self.m_blocking_relevant_label = None
                self.m_blocking_relevant_hash_code -= hash(concept)
                self.m_has_changed_for_blocking = True

    def get_full_atomic_concepts_label(self) -> Entry[AtomicConcept] | frozenset[AtomicConcept]:
        if self.m_full_atomic_concepts_label is None:
            self.m_full_atomic_concepts_label = self._checker._fetch_atomic_concepts_label(self.m_node, False)
            self._checker._atomic_concepts_set_factory.add_reference(self.m_full_atomic_concepts_label)
        return self.m_full_atomic_concepts_label

    def get_full_from_parent_label(self) -> Entry[AtomicRole] | frozenset[AtomicRole]:
        if self.m_has_changed_for_validation or self.m_full_from_parent_label is None:
            self.m_full_from_parent_label = self._checker._fetch_atomic_roles_label(
                self.m_node.parent, self.m_node, False
            )
            self._checker._atomic_roles_set_factory.add_reference(self.m_full_from_parent_label)
        return self.m_full_from_parent_label

    def get_full_to_parent_label(self) -> Entry[AtomicRole] | frozenset[AtomicRole]:
        if self.m_has_changed_for_validation or self.m_full_to_parent_label is None:
            self.m_full_to_parent_label = self._checker._fetch_atomic_roles_label(
                self.m_node, self.m_node.parent, False
            )
            self._checker._atomic_roles_set_factory.add_reference(self.m_full_to_parent_label)
        return self.m_full_to_parent_label

    def set_block_violates_parent_constraints(self, violates: bool) -> None:
        self.m_block_violates_parent_constraints = violates

    def set_has_already_been_checked(self, has_been_checked: bool) -> None:
        self.m_has_already_been_checked = has_been_checked

    def has_already_been_checked(self) -> bool:
        return self.m_has_already_been_checked

    def block_violates_parent_constraints(self) -> bool:
        return self.m_block_violates_parent_constraints


class ValidatedPairwiseBlockingSignature(BlockingSignature):
    """Blocking signature for validated pairwise direct blocking."""

    __slots__ = (
        "m_blocking_relevant_concepts_label",
        "m_full_atomic_concepts_label",
        "m_parent_full_atomic_concepts_label",
        "m_from_parent_label",
        "m_to_parent_label",
        "m_hash_code",
    )

    def __init__(self, checker: ValidatedPairwiseDirectBlockingChecker, node: Node) -> None:
        super().__init__()
        node_obj = node.get_blocking_object()
        parent_obj = node.parent.get_blocking_object()
        assert isinstance(node_obj, ValidatedPairwiseBlockingObject)
        assert isinstance(parent_obj, ValidatedPairwiseBlockingObject)

        self.m_blocking_relevant_concepts_label = node_obj.get_atomic_concepts_label()
        self.m_full_atomic_concepts_label = node_obj.get_full_atomic_concepts_label()
        self.m_parent_full_atomic_concepts_label = parent_obj.get_full_atomic_concepts_label()
        self.m_from_parent_label = node_obj.get_full_from_parent_label()
        self.m_to_parent_label = node_obj.get_full_to_parent_label()
        self.m_hash_code = hash(self.m_blocking_relevant_concepts_label)

        checker._atomic_concepts_set_factory.make_permanent(self.m_full_atomic_concepts_label)
        checker._atomic_concepts_set_factory.make_permanent(self.m_parent_full_atomic_concepts_label)
        checker._atomic_roles_set_factory.make_permanent(self.m_from_parent_label)
        checker._atomic_roles_set_factory.make_permanent(self.m_to_parent_label)

    def blocks_node(self, node: Node) -> bool:
        obj = node.get_blocking_object()
        assert isinstance(obj, ValidatedPairwiseBlockingObject)
        return obj.get_atomic_concepts_label() is self.m_blocking_relevant_concepts_label

    def __hash__(self) -> int:
        return self.m_hash_code

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, ValidatedPairwiseBlockingSignature):
            return False
        return (
            self.m_blocking_relevant_concepts_label is other.m_blocking_relevant_concepts_label
            and self.m_full_atomic_concepts_label is other.m_full_atomic_concepts_label
            and self.m_parent_full_atomic_concepts_label is other.m_parent_full_atomic_concepts_label
            and self.m_from_parent_label is other.m_from_parent_label
            and self.m_to_parent_label is other.m_to_parent_label
        )
