"""Pairwise direct blocking checker.

Faithful port of ``org.semanticweb.HermiT.blocking.PairWiseDirectBlockingChecker``
from the Java HermiT OWL reasoner.

Classes
-------
PairWiseDirectBlockingChecker
    Checks blocking based on atomic concept labels of a node and its parent,
    plus role labels between node and parent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hermit.model import AtomicConcept, AtomicRole, DataRange
from hermit.blocking.set_factory import Entry, SetFactory

from .blocking_signature import BlockingSignature
from .direct_blocking_checker import DirectBlockingChecker


class PairWiseDirectBlockingChecker(DirectBlockingChecker):
    """Direct blocking checker that compares node + parent labels.

    A node *blocked* is blocked by *blocker* when both are tree nodes, their
    atomic concept labels match, their parent concept labels match, and the
    role labels between node and parent match in both directions.
    """

    __slots__ = (
        "_atomic_concepts_set_factory",
        "_atomic_roles_set_factory",
        "_atomic_concepts_buffer",
        "_atomic_roles_buffer",
        "_tableau",
        "_binary_table_search_1_bound",
        "_ternary_table_search_12_bound",
    )

    def __init__(self) -> None:
        self._atomic_concepts_set_factory: SetFactory[AtomicConcept] = SetFactory()
        self._atomic_roles_set_factory: SetFactory[AtomicRole] = SetFactory()
        self._atomic_concepts_buffer: list[AtomicConcept] = []
        self._atomic_roles_buffer: list[AtomicRole] = []
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
        assert isinstance(blocker_obj, PairWiseBlockingObject)
        assert isinstance(blocked_obj, PairWiseBlockingObject)
        assert isinstance(blocker_parent_obj, PairWiseBlockingObject)
        assert isinstance(blocked_parent_obj, PairWiseBlockingObject)

        return (
            not blocker.is_blocked()
            and blocker.node_type == NodeType.TREE_NODE
            and blocked.node_type == NodeType.TREE_NODE
            and blocker_obj.get_atomic_concepts_label()
            == blocked_obj.get_atomic_concepts_label()
            and blocker_parent_obj.get_atomic_concepts_label()
            == blocked_parent_obj.get_atomic_concepts_label()
            and blocker_obj.get_from_parent_label()
            == blocked_obj.get_from_parent_label()
            and blocker_obj.get_to_parent_label()
            == blocked_obj.get_to_parent_label()
        )

    def blocking_hash_code(self, node: Node) -> int:
        node_obj = node.get_blocking_object()
        parent_obj = node.parent.get_blocking_object()
        assert isinstance(node_obj, PairWiseBlockingObject)
        assert isinstance(parent_obj, PairWiseBlockingObject)
        return (
            node_obj.m_atomic_concepts_label_hash_code
            + parent_obj.m_atomic_concepts_label_hash_code
            + node_obj.m_from_parent_label_hash_code
            + node_obj.m_to_parent_label_hash_code
        )

    def can_be_blocker(self, node: Node) -> bool:
        from hermit.tableau import NodeType

        parent = node.parent
        return (
            node.node_type == NodeType.TREE_NODE
            and (parent.node_type == NodeType.TREE_NODE or parent.node_type == NodeType.GRAPH_NODE)
        )

    def can_be_blocked(self, node: Node) -> bool:
        from hermit.tableau import NodeType

        parent = node.parent
        return (
            node.node_type == NodeType.TREE_NODE
            and (parent.node_type == NodeType.TREE_NODE or parent.node_type == NodeType.GRAPH_NODE)
        )

    def has_blocking_info_changed(self, node: Node) -> bool:
        obj = node.get_blocking_object()
        assert isinstance(obj, PairWiseBlockingObject)
        return obj.m_has_changed

    def clear_blocking_info_changed(self, node: Node) -> None:
        obj = node.get_blocking_object()
        assert isinstance(obj, PairWiseBlockingObject)
        obj.m_has_changed = False

    def has_changed_since_validation(self, node: Node) -> bool:
        return False

    def set_has_changed_since_validation(self, node: Node, has_changed: bool) -> None:
        pass  # no-op

    def node_initialized(self, node: Node) -> None:
        if node.get_blocking_object() is None:
            node.set_blocking_object(PairWiseBlockingObject(self, node))
        obj = node.get_blocking_object()
        assert isinstance(obj, PairWiseBlockingObject)
        obj.initialize()

    def node_destroyed(self, node: Node) -> None:
        obj = node.get_blocking_object()
        assert isinstance(obj, PairWiseBlockingObject)
        obj.destroy()

    def assertion_added(self, concept: Concept, node: Node, is_core: bool) -> Node | None:
        if isinstance(concept, AtomicConcept):
            obj = node.get_blocking_object()
            assert isinstance(obj, PairWiseBlockingObject)
            obj.add_atomic_concept(concept)
            return node
        return None

    def assertion_removed(self, concept: Concept, node: Node, is_core: bool) -> Node | None:
        if isinstance(concept, AtomicConcept):
            obj = node.get_blocking_object()
            assert isinstance(obj, PairWiseBlockingObject)
            obj.remove_atomic_concept(concept)
            return node
        return None

    def assertion_added_dr(self, data_range: DataRange, node: Node, is_core: bool) -> Node | None:
        return None

    def assertion_removed_dr(self, data_range: DataRange, node: Node, is_core: bool) -> Node | None:
        return None

    def assertion_added_role(
        self, atomic_role: AtomicRole, node_from: Node, node_to: Node, is_core: bool
    ) -> Node | None:
        if node_from.is_parent_of(node_to):
            obj = node_to.get_blocking_object()
            assert isinstance(obj, PairWiseBlockingObject)
            obj.add_to_from_parent_label(atomic_role)
            return node_to
        elif node_to.is_parent_of(node_from):
            obj = node_from.get_blocking_object()
            assert isinstance(obj, PairWiseBlockingObject)
            obj.add_to_to_parent_label(atomic_role)
            return node_from
        else:
            # Relations between root nodes or back-links -- not relevant for blocking.
            return None

    def assertion_removed_role(
        self, atomic_role: AtomicRole, node_from: Node, node_to: Node, is_core: bool
    ) -> Node | None:
        if node_from.is_parent_of(node_to):
            obj = node_to.get_blocking_object()
            assert isinstance(obj, PairWiseBlockingObject)
            obj.remove_from_from_parent_label(atomic_role)
            return node_to
        elif node_to.is_parent_of(node_from):
            obj = node_from.get_blocking_object()
            assert isinstance(obj, PairWiseBlockingObject)
            obj.remove_from_to_parent_label(atomic_role)
            return node_from
        else:
            return None

    def nodes_merged(self, merge_from: Node, merge_into: Node) -> Node | None:
        return None

    def nodes_unmerged(self, merge_from: Node, merge_into: Node) -> Node | None:
        return None

    def get_blocking_signature_for(self, node: Node) -> BlockingSignature:
        return PairWiseBlockingSignature(self, node)

    # -- internal helpers --------------------------------------------------

    def _fetch_atomic_concepts_label(self, node: Node) -> Entry[AtomicConcept] | frozenset[AtomicConcept]:
        self._atomic_concepts_buffer.clear()
        retrieval = self._binary_table_search_1_bound
        retrieval.get_bindings_buffer()[1] = node  # type: ignore[union-attr]
        retrieval.open()  # type: ignore[union-attr]
        tuple_buffer = retrieval.get_tuple_buffer()  # type: ignore[union-attr]
        while not retrieval.after_last():  # type: ignore[union-attr]
            concept = tuple_buffer[0]
            if isinstance(concept, AtomicConcept):
                self._atomic_concepts_buffer.append(concept)
            retrieval.next()  # type: ignore[union-attr]
        result = self._atomic_concepts_set_factory.get_set(self._atomic_concepts_buffer)
        self._atomic_concepts_buffer.clear()
        return result

    def _fetch_edge_label(self, node_from: Node, node_to: Node) -> Entry[AtomicRole] | frozenset[AtomicRole]:
        self._atomic_roles_buffer.clear()
        retrieval = self._ternary_table_search_12_bound
        retrieval.get_bindings_buffer()[1] = node_from  # type: ignore[union-attr]
        retrieval.get_bindings_buffer()[2] = node_to  # type: ignore[union-attr]
        retrieval.open()  # type: ignore[union-attr]
        tuple_buffer = retrieval.get_tuple_buffer()  # type: ignore[union-attr]
        while not retrieval.after_last():  # type: ignore[union-attr]
            atomic_role = tuple_buffer[0]
            if isinstance(atomic_role, AtomicRole):
                self._atomic_roles_buffer.append(atomic_role)
            retrieval.next()  # type: ignore[union-attr]
        result = self._atomic_roles_set_factory.get_set(self._atomic_roles_buffer)
        self._atomic_roles_buffer.clear()
        return result


class PairWiseBlockingObject:
    """Blocking object used by :class:`PairWiseDirectBlockingChecker`."""

    __slots__ = (
        "_checker",
        "m_node",
        "m_has_changed",
        "m_atomic_concepts_label",
        "m_atomic_concepts_label_hash_code",
        "m_from_parent_label",
        "m_from_parent_label_hash_code",
        "m_to_parent_label",
        "m_to_parent_label_hash_code",
    )

    def __init__(self, checker: PairWiseDirectBlockingChecker, node: Node) -> None:
        self._checker = checker
        self.m_node = node
        self.m_has_changed = False
        self.m_atomic_concepts_label: Entry[AtomicConcept] | frozenset[AtomicConcept] | None = None
        self.m_atomic_concepts_label_hash_code = 0
        self.m_from_parent_label: Entry[AtomicRole] | frozenset[AtomicRole] | None = None
        self.m_from_parent_label_hash_code = 0
        self.m_to_parent_label: Entry[AtomicRole] | frozenset[AtomicRole] | None = None
        self.m_to_parent_label_hash_code = 0

    def initialize(self) -> None:
        self.m_atomic_concepts_label = None
        self.m_atomic_concepts_label_hash_code = 0
        self.m_from_parent_label = None
        self.m_from_parent_label_hash_code = 0
        self.m_to_parent_label = None
        self.m_to_parent_label_hash_code = 0
        self.m_has_changed = True

    def destroy(self) -> None:
        sf_c = self._checker._atomic_concepts_set_factory
        sf_r = self._checker._atomic_roles_set_factory
        if self.m_atomic_concepts_label is not None:
            sf_c.remove_reference(self.m_atomic_concepts_label)
            self.m_atomic_concepts_label = None
        if self.m_from_parent_label is not None:
            sf_r.remove_reference(self.m_from_parent_label)
            self.m_from_parent_label = None
        if self.m_to_parent_label is not None:
            sf_r.remove_reference(self.m_to_parent_label)
            self.m_to_parent_label = None

    def get_atomic_concepts_label(self) -> Entry[AtomicConcept] | frozenset[AtomicConcept]:
        if self.m_atomic_concepts_label is None:
            self.m_atomic_concepts_label = self._checker._fetch_atomic_concepts_label(self.m_node)
            self._checker._atomic_concepts_set_factory.add_reference(self.m_atomic_concepts_label)
        return self.m_atomic_concepts_label

    def add_atomic_concept(self, atomic_concept: AtomicConcept) -> None:
        if self.m_atomic_concepts_label is not None:
            self._checker._atomic_concepts_set_factory.remove_reference(self.m_atomic_concepts_label)
            self.m_atomic_concepts_label = None
        self.m_atomic_concepts_label_hash_code += hash(atomic_concept)
        self.m_has_changed = True

    def remove_atomic_concept(self, atomic_concept: AtomicConcept) -> None:
        if self.m_atomic_concepts_label is not None:
            self._checker._atomic_concepts_set_factory.remove_reference(self.m_atomic_concepts_label)
            self.m_atomic_concepts_label = None
        self.m_atomic_concepts_label_hash_code -= hash(atomic_concept)
        self.m_has_changed = True

    def get_from_parent_label(self) -> Entry[AtomicRole] | frozenset[AtomicRole]:
        if self.m_from_parent_label is None:
            self.m_from_parent_label = self._checker._fetch_edge_label(self.m_node.parent, self.m_node)
            self._checker._atomic_roles_set_factory.add_reference(self.m_from_parent_label)
        return self.m_from_parent_label

    def add_to_from_parent_label(self, atomic_role: AtomicRole) -> None:
        if self.m_from_parent_label is not None:
            self._checker._atomic_roles_set_factory.remove_reference(self.m_from_parent_label)
            self.m_from_parent_label = None
        self.m_from_parent_label_hash_code += hash(atomic_role)
        self.m_has_changed = True

    def remove_from_from_parent_label(self, atomic_role: AtomicRole) -> None:
        if self.m_from_parent_label is not None:
            self._checker._atomic_roles_set_factory.remove_reference(self.m_from_parent_label)
            self.m_from_parent_label = None
        self.m_from_parent_label_hash_code -= hash(atomic_role)
        self.m_has_changed = True

    def get_to_parent_label(self) -> Entry[AtomicRole] | frozenset[AtomicRole]:
        if self.m_to_parent_label is None:
            self.m_to_parent_label = self._checker._fetch_edge_label(self.m_node, self.m_node.parent)
            self._checker._atomic_roles_set_factory.add_reference(self.m_to_parent_label)
        return self.m_to_parent_label

    def add_to_to_parent_label(self, atomic_role: AtomicRole) -> None:
        if self.m_to_parent_label is not None:
            self._checker._atomic_roles_set_factory.remove_reference(self.m_to_parent_label)
            self.m_to_parent_label = None
        self.m_to_parent_label_hash_code += hash(atomic_role)
        self.m_has_changed = True

    def remove_from_to_parent_label(self, atomic_role: AtomicRole) -> None:
        if self.m_to_parent_label is not None:
            self._checker._atomic_roles_set_factory.remove_reference(self.m_to_parent_label)
            self.m_to_parent_label = None
        self.m_to_parent_label_hash_code -= hash(atomic_role)
        self.m_has_changed = True


class PairWiseBlockingSignature(BlockingSignature):
    """Blocking signature for pairwise direct blocking."""

    __slots__ = (
        "m_atomic_concept_label",
        "m_parent_atomic_concept_label",
        "m_from_parent_label",
        "m_to_parent_label",
        "m_hash_code",
    )

    def __init__(self, checker: PairWiseDirectBlockingChecker, node: Node) -> None:
        super().__init__()
        node_obj = node.get_blocking_object()
        parent_obj = node.parent.get_blocking_object()
        assert isinstance(node_obj, PairWiseBlockingObject)
        assert isinstance(parent_obj, PairWiseBlockingObject)

        self.m_atomic_concept_label = node_obj.get_atomic_concepts_label()
        self.m_parent_atomic_concept_label = parent_obj.get_atomic_concepts_label()
        self.m_from_parent_label = node_obj.get_from_parent_label()
        self.m_to_parent_label = node_obj.get_to_parent_label()
        self.m_hash_code = (
            hash(self.m_atomic_concept_label)
            + hash(self.m_parent_atomic_concept_label)
            + hash(self.m_from_parent_label)
            + hash(self.m_to_parent_label)
        )
        checker._atomic_concepts_set_factory.make_permanent(self.m_atomic_concept_label)
        checker._atomic_concepts_set_factory.make_permanent(self.m_parent_atomic_concept_label)
        checker._atomic_roles_set_factory.make_permanent(self.m_from_parent_label)
        checker._atomic_roles_set_factory.make_permanent(self.m_to_parent_label)

    def blocks_node(self, node: Node) -> bool:
        node_obj = node.get_blocking_object()
        parent_obj = node.parent.get_blocking_object()
        assert isinstance(node_obj, PairWiseBlockingObject)
        assert isinstance(parent_obj, PairWiseBlockingObject)
        return (
            node_obj.get_atomic_concepts_label() is self.m_atomic_concept_label
            and parent_obj.get_atomic_concepts_label() is self.m_parent_atomic_concept_label
            and node_obj.get_from_parent_label() is self.m_from_parent_label
            and node_obj.get_to_parent_label() is self.m_to_parent_label
        )

    def __hash__(self) -> int:
        return self.m_hash_code

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, PairWiseBlockingSignature):
            return False
        return (
            self.m_atomic_concept_label is other.m_atomic_concept_label
            and self.m_parent_atomic_concept_label is other.m_parent_atomic_concept_label
            and self.m_from_parent_label is other.m_from_parent_label
            and self.m_to_parent_label is other.m_to_parent_label
        )
