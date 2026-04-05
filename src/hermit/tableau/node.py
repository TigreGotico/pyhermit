"""Tableau node representing an individual or a datatype value."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hermit.tableau.node_type import NodeType

if TYPE_CHECKING:
    from hermit.model import ExistentialConcept
    from hermit.tableau.dependency_set import DependencySet
    from hermit.tableau.permanent_dependency_set import PermanentDependencySet
    from hermit.tableau.tableau import Tableau


class NodeState:
    """Possible states of a :class:`Node`."""

    ACTIVE = "active"
    MERGED = "merged"
    PRUNED = "pruned"


class Node:
    """A node in the tableau, representing an individual or value.

    Nodes are initially ``ACTIVE`` but may later be marked ``MERGED`` or
    ``PRUNED``, which deactivates them without destroying the object
    (enabling object reuse).

    The signature cache blocker is a singleton sentinel used during
    pairwise blocking.
    """

    # Sentinel for blocking-cache operations
    SIGNATURE_CACHE_BLOCKER: Node | None = None

    __slots__ = (
        "_tableau",
        "_node_id",
        "_node_state",
        "_parent",
        "_node_type",
        "_tree_depth",
        "_number_of_positive_atomic_concepts",
        "_number_of_negated_atomic_concepts",
        "_number_of_negated_role_assertions",
        "_unprocessed_existentials",
        "_previous_tableau_node",
        "_next_tableau_node",
        "_previous_merged_or_pruned_node",
        "_merged_into",
        "_merged_into_dependency_set",
        "_blocker",
        "_directly_blocked",
        "_blocking_object",
        "_blocking_cargo",
        "_first_graph_occurrence_node",
    )

    _no_existentials: list[ExistentialConcept] = []

    def __init__(self, tableau: Tableau | None) -> None:
        self._tableau = tableau
        self._node_id = -1
        # Remaining fields are set by initialise() / destroy()
        self._node_state: str | None = None
        self._parent: Node | None = None
        self._node_type: NodeType | None = None
        self._tree_depth = 0
        self._number_of_positive_atomic_concepts = 0
        self._number_of_negated_atomic_concepts = 0
        self._number_of_negated_role_assertions = 0
        self._unprocessed_existentials: list[ExistentialConcept] = (
            Node._no_existentials
        )
        self._previous_tableau_node: Node | None = None
        self._next_tableau_node: Node | None = None
        self._previous_merged_or_pruned_node: Node | None = None
        self._merged_into: Node | None = None
        self._merged_into_dependency_set: PermanentDependencySet | None = None
        self._blocker: Node | None = None
        self._directly_blocked = False
        self._blocking_object: Any = None
        self._blocking_cargo: Any = None
        self._first_graph_occurrence_node = 0

        # Initialise sentinel on first construction
        if Node.SIGNATURE_CACHE_BLOCKER is None and tableau is None:
            Node.SIGNATURE_CACHE_BLOCKER = self

    # ------------------------------------------------------------------
    # Initialisation / destruction
    # ------------------------------------------------------------------

    def initialize(
        self,
        node_id: int,
        parent: Node | None,
        node_type: NodeType,
        tree_depth: int,
    ) -> None:
        """Set up the node with the given identity and type.

        Args:
            node_id: Unique identifier within the tableau.
            parent: Parent node (``None`` for root-level nodes).
            node_type: The type of this node.
            tree_depth: Depth in the tree (0 for root-level nodes).
        """
        assert self._node_id == -1
        assert self._unprocessed_existentials is None or (
            self._unprocessed_existentials is Node._no_existentials
        )
        self._node_id = node_id
        self._node_state = NodeState.ACTIVE
        self._parent = parent
        self._node_type = node_type
        self._tree_depth = tree_depth
        self._number_of_positive_atomic_concepts = 0
        self._number_of_negated_atomic_concepts = 0
        self._number_of_negated_role_assertions = 0
        self._unprocessed_existentials = Node._no_existentials
        self._previous_tableau_node = None
        self._next_tableau_node = None
        self._previous_merged_or_pruned_node = None
        self._merged_into = None
        self._merged_into_dependency_set = None
        self._blocker = None
        self._directly_blocked = False
        if self._tableau is not None:
            self._tableau.m_description_graph_manager.initialise_node(self)

    def destroy(self) -> None:
        """Release resources and return the node to an uninitialised state."""
        self._node_id = -1
        self._node_state = None
        self._parent = None
        self._node_type = None
        if (
            self._unprocessed_existentials is not None
            and self._unprocessed_existentials is not Node._no_existentials
        ):
            self._unprocessed_existentials.clear()
            if self._tableau is not None:
                self._tableau.put_existential_concepts_buffer(
                    self._unprocessed_existentials
                )
        self._unprocessed_existentials = None
        self._previous_tableau_node = None
        self._next_tableau_node = None
        self._previous_merged_or_pruned_node = None
        self._merged_into = None
        if self._merged_into_dependency_set is not None and self._tableau is not None:
            self._tableau.m_dependency_set_factory.remove_usage(
                self._merged_into_dependency_set
            )
            self._merged_into_dependency_set = None
        self._blocker = None
        if self._tableau is not None:
            self._tableau.m_description_graph_manager.destroy_node(self)

    # ------------------------------------------------------------------
    # Basic accessors
    # ------------------------------------------------------------------

    @property
    def tableau(self) -> Tableau | None:
        """Return the tableau that owns this node."""
        return self._tableau

    @property
    def node_id(self) -> int:
        """Return the unique node identifier (``-1`` if uninitialised)."""
        return self._node_id

    @property
    def parent(self) -> Node | None:
        """Return the parent node, or ``None`` for root-level nodes."""
        return self._parent

    @property
    def cluster_anchor(self) -> Node:
        """Return the cluster anchor for this node.

        For tree nodes the node itself is the anchor; otherwise the parent
        is the anchor.
        """
        if self._node_type == NodeType.TREE_NODE:
            return self
        return self._parent  # type: ignore[return-value]

    def is_root_node(self) -> bool:
        """Return ``True`` if this node has no parent."""
        return self._parent is None

    def is_parent_of(self, potential_child: Node) -> bool:
        """Return ``True`` if *potential_child*'s parent is this node."""
        return potential_child._parent is self

    def is_ancestor_of(self, potential_descendant: Node | None) -> bool:
        """Return ``True`` if this node is an ancestor of *potential_descendant*."""
        node = potential_descendant
        while node is not None:
            node = node._parent
            if node is self:
                return True
        return False

    @property
    def node_type(self) -> NodeType | None:
        """Return the type of this node."""
        return self._node_type

    @property
    def tree_depth(self) -> int:
        """Return the tree depth of this node."""
        return self._tree_depth

    # ------------------------------------------------------------------
    # Blocking
    # ------------------------------------------------------------------

    @property
    def is_blocked(self) -> bool:
        """Return ``True`` if this node is blocked (directly or indirectly)."""
        return self._blocker is not None

    @property
    def is_directly_blocked(self) -> bool:
        """Return ``True`` if this node is directly blocked."""
        return self._directly_blocked

    @property
    def is_indirectly_blocked(self) -> bool:
        """Return ``True`` if this node is indirectly blocked."""
        return self._blocker is not None and not self._directly_blocked

    @property
    def blocker(self) -> Node | None:
        """Return the node that blocks this one, or ``None``."""
        return self._blocker

    def set_blocked(self, blocker: Node | None, directly_blocked: bool) -> None:
        """Set or clear the blocking status.

        Args:
            blocker: The node that blocks this one (``None`` to unblock).
            directly_blocked: Whether the block is direct.
        """
        self._blocker = blocker
        self._directly_blocked = directly_blocked

    @property
    def blocking_object(self) -> Any:
        """Return the blocking object (PairwiseBlockingObject / SingleBlockingObject)."""
        return self._blocking_object

    @blocking_object.setter
    def blocking_object(self, value: Any) -> None:
        """Set the blocking object for this node."""
        self._blocking_object = value

    @property
    def blocking_cargo(self) -> Any:
        """Return the blocking cargo (typically a BlockersCache.CacheEntry)."""
        return self._blocking_cargo

    @blocking_cargo.setter
    def blocking_cargo(self, value: Any) -> None:
        """Set the blocking cargo for this node."""
        self._blocking_cargo = value

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    @property
    def number_of_positive_atomic_concepts(self) -> int:
        """Return the count of positive atomic concepts asserted to this node."""
        return self._number_of_positive_atomic_concepts

    def is_active(self) -> bool:
        """Return ``True`` if the node is active."""
        return self._node_state == NodeState.ACTIVE

    def is_merged(self) -> bool:
        """Return ``True`` if the node has been merged into another."""
        return self._node_state == NodeState.MERGED

    @property
    def merged_into(self) -> Node | None:
        """Return the node this one was merged into, or ``None``."""
        return self._merged_into

    @property
    def merged_into_dependency_set(self) -> PermanentDependencySet | None:
        """Return the dependency set associated with the merge, or ``None``."""
        return self._merged_into_dependency_set

    def is_pruned(self) -> bool:
        """Return ``True`` if the node has been pruned."""
        return self._node_state == NodeState.PRUNED

    # ------------------------------------------------------------------
    # Linked-list navigation
    # ------------------------------------------------------------------

    @property
    def previous_tableau_node(self) -> Node | None:
        """Return the previous node in the tableau linked list."""
        return self._previous_tableau_node

    @property
    def next_tableau_node(self) -> Node | None:
        """Return the next node in the tableau linked list."""
        return self._next_tableau_node

    # ------------------------------------------------------------------
    # Canonical node and dependency-set resolution
    # ------------------------------------------------------------------

    def get_canonical_node(self) -> Node:
        """Follow merge links to find the canonical (surviving) node."""
        result = self
        while result._merged_into is not None:
            result = result._merged_into
        return result

    def get_canonical_node_dependency_set(self) -> PermanentDependencySet:
        """Return the union of dependency sets along the merge chain."""
        assert self._tableau is not None
        return self.add_canonical_node_dependency_set(
            self._tableau.m_dependency_set_factory.empty_set
        )

    def add_canonical_node_dependency_set(
        self, dependency_set: DependencySet
    ) -> PermanentDependencySet:
        """Return *dependency_set* unioned with all merge-chain sets."""
        assert self._tableau is not None
        factory = self._tableau.m_dependency_set_factory
        result = factory.get_permanent(dependency_set)
        node: Node | None = self
        while node._merged_into is not None:
            result = factory.union_with(result, node._merged_into_dependency_set)
            node = node._merged_into
        return result

    # ------------------------------------------------------------------
    # Unprocessed existentials
    # ------------------------------------------------------------------

    def _add_to_unprocessed_existentials(
        self, existential_concept: ExistentialConcept
    ) -> None:
        """Add *existential_concept* to the unprocessed queue."""
        assert Node._no_existentials == []
        if self._unprocessed_existentials is Node._no_existentials:
            assert self._tableau is not None
            self._unprocessed_existentials = (
                self._tableau.get_existential_concepts_buffer()
            )
            assert self._unprocessed_existentials == []
        self._unprocessed_existentials.append(existential_concept)

    def _remove_from_unprocessed_existentials(
        self, existential_concept: ExistentialConcept
    ) -> None:
        """Remove *existential_concept* from the unprocessed queue."""
        assert self._unprocessed_existentials is not Node._no_existentials
        assert len(self._unprocessed_existentials) > 0
        if existential_concept is self._unprocessed_existentials[-1]:
            self._unprocessed_existentials.pop()
        else:
            removed = self._unprocessed_existentials.remove(existential_concept)
            assert removed
        if len(self._unprocessed_existentials) == 0:
            assert self._tableau is not None
            self._tableau.put_existential_concepts_buffer(
                self._unprocessed_existentials
            )
            self._unprocessed_existentials = Node._no_existentials

    def has_unprocessed_existentials(self) -> bool:
        """Return ``True`` if there are unprocessed existential concepts."""
        return len(self._unprocessed_existentials) > 0

    def get_some_unprocessed_existential(self) -> ExistentialConcept:
        """Return an arbitrary unprocessed existential concept (LIFO order)."""
        return self._unprocessed_existentials[-1]

    @property
    def unprocessed_existentials(self) -> list[ExistentialConcept]:
        """Return the list of unprocessed existential concepts."""
        return self._unprocessed_existentials

    # ------------------------------------------------------------------
    # Debugging
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return str(self._node_id)

    def __repr__(self) -> str:
        return f"Node(id={self._node_id}, state={self._node_state})"
