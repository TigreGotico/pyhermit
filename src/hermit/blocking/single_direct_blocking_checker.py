"""Single direct blocking checker.

Faithful port of ``org.semanticweb.HermiT.blocking.SingleDirectBlockingChecker``
from the Java HermiT OWL reasoner.

Classes
-------
SingleDirectBlockingChecker
    Checks blocking based solely on the atomic concept label of a single node.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.model import AtomicConcept, AtomicRole, Concept, DataRange
    from hermit.tableau import Node, Tableau

from hermit.blocking.set_factory import Entry, SetFactory

from .blocking_signature import BlockingSignature
from .direct_blocking_checker import DirectBlockingChecker


class SingleDirectBlockingChecker(DirectBlockingChecker):
    """Direct blocking checker that compares only atomic concept labels.

    A node *blocked* is blocked by *blocker* when they are both tree nodes
    and their atomic concept labels are identical (same canonical set).
    """

    __slots__ = (
        "_atomic_concepts_set_factory",
        "_atomic_concepts_buffer",
        "_tableau",
        "_binary_table_search_1_bound",
    )

    def __init__(self) -> None:
        self._atomic_concepts_set_factory: SetFactory[AtomicConcept] = SetFactory()
        self._atomic_concepts_buffer: list[AtomicConcept] = []
        self._tableau: Tableau | None = None
        self._binary_table_search_1_bound: object | None = None  # ExtensionTable.Retrieval

    # -- DirectBlockingChecker ---------------------------------------------

    def initialize(self, tableau: Tableau) -> None:
        self._tableau = tableau
        self._binary_table_search_1_bound = tableau.extension_manager.get_binary_extension_table().create_retrieval(
            [False, True], "TOTAL"
        )

    def clear(self) -> None:
        self._atomic_concepts_set_factory.clear_nonpermanent()
        retrieval = self._binary_table_search_1_bound
        if retrieval is not None and hasattr(retrieval, "clear"):
            retrieval.clear()

    def is_blocked_by(self, blocker: Node, blocked: Node) -> bool:  # type: ignore[name-defined]
        from hermit.tableau import NodeType

        blocker_obj = blocker.get_blocking_object()
        blocked_obj = blocked.get_blocking_object()
        assert isinstance(blocker_obj, SingleBlockingObject)
        assert isinstance(blocked_obj, SingleBlockingObject)
        return (
            not blocker.is_blocked()
            and blocker.node_type == NodeType.TREE_NODE
            and blocked.node_type == NodeType.TREE_NODE
            and blocker_obj.get_atomic_concepts_label()
            == blocked_obj.get_atomic_concepts_label()
        )

    def blocking_hash_code(self, node: Node) -> int:  # type: ignore[name-defined]
        obj = node.get_blocking_object()
        assert isinstance(obj, SingleBlockingObject)
        return obj.m_atomic_concepts_label_hash_code

    def can_be_blocker(self, node: Node) -> bool:  # type: ignore[name-defined]
        from hermit.tableau import NodeType

        return node.node_type == NodeType.TREE_NODE

    def can_be_blocked(self, node: Node) -> bool:  # type: ignore[name-defined]
        from hermit.tableau import NodeType

        return node.node_type == NodeType.TREE_NODE

    def has_blocking_info_changed(self, node: Node) -> bool:  # type: ignore[name-defined]
        obj = node.get_blocking_object()
        assert isinstance(obj, SingleBlockingObject)
        return obj.m_has_changed

    def clear_blocking_info_changed(self, node: Node) -> None:  # type: ignore[name-defined]
        obj = node.get_blocking_object()
        assert isinstance(obj, SingleBlockingObject)
        obj.m_has_changed = False

    def has_changed_since_validation(self, node: Node) -> bool:  # type: ignore[name-defined]
        return False

    def set_has_changed_since_validation(self, node: Node, has_changed: bool) -> None:  # type: ignore[name-defined]
        pass  # no-op for single blocking

    def node_initialized(self, node: Node) -> None:  # type: ignore[name-defined]
        if node.get_blocking_object() is None:
            node.set_blocking_object(SingleBlockingObject(self, node))
        obj = node.get_blocking_object()
        assert isinstance(obj, SingleBlockingObject)
        obj.initialize()

    def node_destroyed(self, node: Node) -> None:  # type: ignore[name-defined]
        obj = node.get_blocking_object()
        assert isinstance(obj, SingleBlockingObject)
        obj.destroy()

    def assertion_added(self, concept: Concept, node: Node, is_core: bool) -> Node | None:  # type: ignore[name-defined]
        if isinstance(concept, AtomicConcept):
            obj = node.get_blocking_object()
            assert isinstance(obj, SingleBlockingObject)
            obj.add_atomic_concept(concept)
            return node
        return None

    def assertion_removed(self, concept: Concept, node: Node, is_core: bool) -> Node | None:  # type: ignore[name-defined]
        if isinstance(concept, AtomicConcept):
            obj = node.get_blocking_object()
            assert isinstance(obj, SingleBlockingObject)
            obj.remove_atomic_concept(concept)
            return node
        return None

    def assertion_added_dr(self, data_range: DataRange, node: Node, is_core: bool) -> Node | None:  # type: ignore[name-defined]
        return None

    def assertion_removed_dr(self, data_range: DataRange, node: Node, is_core: bool) -> Node | None:  # type: ignore[name-defined]
        return None

    def assertion_added_role(
        self, atomic_role: AtomicRole, node_from: Node, node_to: Node, is_core: bool
    ) -> Node | None:  # type: ignore[name-defined]
        return None

    def assertion_removed_role(
        self, atomic_role: AtomicRole, node_from: Node, node_to: Node, is_core: bool
    ) -> Node | None:  # type: ignore[name-defined]
        return None

    def nodes_merged(self, merge_from: Node, merge_into: Node) -> Node | None:  # type: ignore[name-defined]
        return None

    def nodes_unmerged(self, merge_from: Node, merge_into: Node) -> Node | None:  # type: ignore[name-defined]
        return None

    def get_blocking_signature_for(self, node: Node) -> BlockingSignature:  # type: ignore[name-defined]
        return SingleBlockingSignature(self, node)

    # -- internal helpers --------------------------------------------------

    def _fetch_atomic_concepts_label(self, node: Node) -> Entry[AtomicConcept] | frozenset[AtomicConcept]:  # type: ignore[name-defined]
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


class SingleBlockingObject:
    """Blocking object used by :class:`SingleDirectBlockingChecker`.

    In the Java original this is a non-static inner class with an implicit
    reference to the enclosing ``SingleDirectBlockingChecker``.  Here we pass
    the checker explicitly.
    """

    __slots__ = (
        "_checker",
        "m_node",
        "m_has_changed",
        "m_atomic_concepts_label",
        "m_atomic_concepts_label_hash_code",
    )

    def __init__(self, checker: SingleDirectBlockingChecker, node: Node) -> None:  # type: ignore[name-defined]
        self._checker = checker
        self.m_node = node
        self.m_has_changed = False
        self.m_atomic_concepts_label: Entry[AtomicConcept] | frozenset[AtomicConcept] | None = None
        self.m_atomic_concepts_label_hash_code = 0

    def initialize(self) -> None:
        self.m_atomic_concepts_label = None
        self.m_atomic_concepts_label_hash_code = 0
        self.m_has_changed = True

    def destroy(self) -> None:
        if self.m_atomic_concepts_label is not None:
            self._checker._atomic_concepts_set_factory.remove_reference(self.m_atomic_concepts_label)
            self.m_atomic_concepts_label = None

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


class SingleBlockingSignature(BlockingSignature):
    """Blocking signature for single direct blocking."""

    __slots__ = ("m_atomic_concepts_label",)

    def __init__(self, checker: SingleDirectBlockingChecker, node: Node) -> None:  # type: ignore[name-defined]
        super().__init__()
        obj = node.get_blocking_object()
        assert isinstance(obj, SingleBlockingObject)
        self.m_atomic_concepts_label = obj.get_atomic_concepts_label()
        checker._atomic_concepts_set_factory.make_permanent(self.m_atomic_concepts_label)

    def blocks_node(self, node: Node) -> bool:  # type: ignore[name-defined]
        obj = node.get_blocking_object()
        assert isinstance(obj, SingleBlockingObject)
        return obj.get_atomic_concepts_label() == self.m_atomic_concepts_label

    def __hash__(self) -> int:
        return hash(self.m_atomic_concepts_label)

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, SingleBlockingSignature):
            return False
        return self.m_atomic_concepts_label is other.m_atomic_concepts_label
