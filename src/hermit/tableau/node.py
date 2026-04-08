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
        "m_tableau",
        "m_node_id",
        "m_node_state",
        "m_parent",
        "m_node_type",
        "m_tree_depth",
        "m_number_of_positive_atomic_concepts",
        "m_number_of_negated_atomic_concepts",
        "m_number_of_negated_role_assertions",
        "m_unprocessed_existentials",
        "m_previous_tableau_node",
        "m_next_tableau_node",
        "m_previous_merged_or_pruned_node",
        "m_merged_into",
        "m_merged_into_dependency_set",
        "m_blocker",
        "m_directly_blocked",
        "m_blocking_object",
        "m_blocking_cargo",
        "m_first_graph_occurrence_node",
    )

    _no_existentials: list[ExistentialConcept] = []

    def __init__(self, tableau: Tableau | None) -> None:
        self.m_tableau = tableau
        self.m_node_id = -1
        # Remaining fields are set by initialise() / destroy()
        self.m_node_state: str | None = None
        self.m_parent: Node | None = None
        self.m_node_type: NodeType | None = None
        self.m_tree_depth = 0
        self.m_number_of_positive_atomic_concepts = 0
        self.m_number_of_negated_atomic_concepts = 0
        self.m_number_of_negated_role_assertions = 0
        self.m_unprocessed_existentials: list[ExistentialConcept] = (
            Node._no_existentials
        )
        self.m_previous_tableau_node: Node | None = None
        self.m_next_tableau_node: Node | None = None
        self.m_previous_merged_or_pruned_node: Node | None = None
        self.m_merged_into: Node | None = None
        self.m_merged_into_dependency_set: PermanentDependencySet | None = None
        self.m_blocker: Node | None = None
        self.m_directly_blocked = False
        self.m_blocking_object: Any = None
        self.m_blocking_cargo: Any = None
        self.m_first_graph_occurrence_node = 0

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
        assert self.m_node_id == -1
        assert self.m_unprocessed_existentials is None or (
            self.m_unprocessed_existentials is Node._no_existentials
        )
        self.m_node_id = node_id
        self.m_node_state = NodeState.ACTIVE
        self.m_parent = parent
        self.m_node_type = node_type
        self.m_tree_depth = tree_depth
        self.m_number_of_positive_atomic_concepts = 0
        self.m_number_of_negated_atomic_concepts = 0
        self.m_number_of_negated_role_assertions = 0
        self.m_unprocessed_existentials = Node._no_existentials
        self.m_previous_tableau_node = None
        self.m_next_tableau_node = None
        self.m_previous_merged_or_pruned_node = None
        self.m_merged_into = None
        self.m_merged_into_dependency_set = None
        self.m_blocker = None
        self.m_directly_blocked = False
        if self.m_tableau is not None:
            self.m_tableau.m_description_graph_manager.initialise_node(self)

    def destroy(self) -> None:
        """Release resources and return the node to an uninitialised state."""
        self.m_node_id = -1
        self.m_node_state = None
        self.m_parent = None
        self.m_node_type = None
        if (
            self.m_unprocessed_existentials is not None
            and self.m_unprocessed_existentials is not Node._no_existentials
        ):
            self.m_unprocessed_existentials.clear()
            if self.m_tableau is not None:
                self.m_tableau.put_existential_concepts_buffer(
                    self.m_unprocessed_existentials
                )
        self.m_unprocessed_existentials = None
        self.m_previous_tableau_node = None
        self.m_next_tableau_node = None
        self.m_previous_merged_or_pruned_node = None
        self.m_merged_into = None
        if self.m_merged_into_dependency_set is not None and self.m_tableau is not None:
            self.m_tableau.m_dependency_set_factory.remove_usage(
                self.m_merged_into_dependency_set
            )
            self.m_merged_into_dependency_set = None
        self.m_blocker = None
        if self.m_tableau is not None:
            self.m_tableau.m_description_graph_manager.destroy_node(self)

    # ------------------------------------------------------------------
    # Basic accessors
    # ------------------------------------------------------------------

    @property
    def tableau(self) -> Tableau | None:
        """Return the tableau that owns this node."""
        return self.m_tableau

    @property
    def node_id(self) -> int:
        """Return the unique node identifier (``-1`` if uninitialised)."""
        return self.m_node_id

    @property
    def parent(self) -> Node | None:
        """Return the parent node, or ``None`` for root-level nodes."""
        return self.m_parent

    @property
    def cluster_anchor(self) -> Node:
        """Return the cluster anchor for this node.

        For tree nodes the node itself is the anchor; otherwise the parent
        is the anchor.
        """
        if self.m_node_type == NodeType.TREE_NODE:
            return self
        return self.m_parent  # type: ignore[return-value]

    def is_root_node(self) -> bool:
        """Return ``True`` if this node has no parent."""
        return self.m_parent is None

    def is_parent_of(self, potential_child: Node) -> bool:
        """Return ``True`` if *potential_child*'s parent is this node."""
        return potential_child.m_parent is self

    def get_blocking_object(self) -> Any | None:
        """Return the blocking object for this node."""
        return self.m_blocking_object

    def set_blocking_object(self, obj: Any) -> None:
        """Set the blocking object for this node."""
        self.m_blocking_object = obj

    def get_blocking_cargo(self) -> Any | None:
        """Return the blocking cargo for this node."""
        return self.m_blocking_cargo

    def set_blocking_cargo(self, cargo: Any) -> None:
        """Set the blocking cargo for this node."""
        self.m_blocking_cargo = cargo

    def get_node_id(self) -> int:
        """Return the node ID."""
        return self.m_node_id

    def is_active(self) -> bool:
        """Return ``True`` if this node is active."""
        return self.m_node_state == NodeState.ACTIVE

    def get_next_tableau_node(self) -> Node | None:
        """Return the next tableau node."""
        return self.m_next_tableau_node

    def get_previous_tableau_node(self) -> Node | None:
        """Return the previous tableau node."""
        return self.m_previous_tableau_node

    def set_next_tableau_node(self, node: Node | None) -> None:
        """Set the next tableau node."""
        self.m_next_tableau_node = node

    def set_previous_tableau_node(self, node: Node | None) -> None:
        """Set the previous tableau node."""
        self.m_previous_tableau_node = node

    def get_parent(self) -> Node | None:
        """Return the parent node."""
        return self.m_parent

    def get_tree_depth(self) -> int:
        """Return the tree depth."""
        return self.m_tree_depth

    def get_node_type(self) -> NodeType | None:
        """Return the node type."""
        return self.m_node_type

    def get_unprocessed_existentials(self) -> list:
        """Return unprocessed existentials."""
        return self.m_unprocessed_existentials

    def set_unprocessed_existentials(self, existentials: list) -> None:
        """Set unprocessed existentials."""
        self.m_unprocessed_existentials = existentials

    def get_merged_into(self) -> Node | None:
        """Return the node this was merged into."""
        return self.m_merged_into

    def set_merged_into(self, node: Node | None) -> None:
        """Set the node this was merged into."""
        self.m_merged_into = node

    def get_directly_blocked(self) -> bool:
        """Return whether this node is directly blocked."""
        return self.m_directly_blocked

    def set_directly_blocked(self, blocked: bool) -> None:
        """Set whether this node is directly blocked."""
        self.m_directly_blocked = blocked

    def get_blocker(self) -> Node | None:
        """Return the blocker node."""
        return self.m_blocker

    def set_blocker(self, node: Node | None) -> None:
        """Set the blocker node."""
        self.m_blocker = node

    def add_unprocessed_existential(self, existential: Any) -> None:
        """Add an unprocessed existential."""
        if self.m_unprocessed_existentials is Node._no_existentials:
            self.m_unprocessed_existentials = []
        self.m_unprocessed_existentials.append(existential)

    def is_ancestor_of(self, potential_descendant: Node | None) -> bool:
        """Return ``True`` if this node is an ancestor of *potential_descendant*."""
        node = potential_descendant
        while node is not None:
            node = node.m_parent
            if node is self:
                return True
        return False

    @property
    def node_type(self) -> NodeType | None:
        """Return the type of this node."""
        return self.m_node_type

    @property
    def tree_depth(self) -> int:
        """Return the tree depth of this node."""
        return self.m_tree_depth

    # ------------------------------------------------------------------
    # Blocking
    # ------------------------------------------------------------------

    def is_blocked(self) -> bool:
        """Return ``True`` if this node is blocked (directly or indirectly)."""
        return self.m_blocker is not None

    def is_directly_blocked(self) -> bool:
        """Return ``True`` if this node is directly blocked."""
        return self.m_directly_blocked

    @property
    def is_indirectly_blocked(self) -> bool:
        """Return ``True`` if this node is indirectly blocked."""
        return self.m_blocker is not None and not self.m_directly_blocked

    @property
    def blocker(self) -> Node | None:
        """Return the node that blocks this one, or ``None``."""
        return self.m_blocker

    def set_blocked(self, blocker: Node | None, directly_blocked: bool) -> None:
        """Set or clear the blocking status.

        Args:
            blocker: The node that blocks this one (``None`` to unblock).
            directly_blocked: Whether the block is direct.
        """
        self.m_blocker = blocker
        self.m_directly_blocked = directly_blocked

    @property
    def blocking_object(self) -> Any:
        """Return the blocking object (PairwiseBlockingObject / SingleBlockingObject)."""
        return self.m_blocking_object

    @blocking_object.setter
    def blocking_object(self, value: Any) -> None:
        """Set the blocking object for this node."""
        self.m_blocking_object = value

    @property
    def blocking_cargo(self) -> Any:
        """Return the blocking cargo (typically a BlockersCache.CacheEntry)."""
        return self.m_blocking_cargo

    @blocking_cargo.setter
    def blocking_cargo(self, value: Any) -> None:
        """Set the blocking cargo for this node."""
        self.m_blocking_cargo = value

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    @property
    def number_of_positive_atomic_concepts(self) -> int:
        """Return the count of positive atomic concepts asserted to this node."""
        return self.m_number_of_positive_atomic_concepts

    def is_merged(self) -> bool:
        """Return ``True`` if the node has been merged into another."""
        return self.m_node_state == NodeState.MERGED

    @property
    def merged_into(self) -> Node | None:
        """Return the node this one was merged into, or ``None``."""
        return self.m_merged_into

    @property
    def merged_into_dependency_set(self) -> PermanentDependencySet | None:
        """Return the dependency set associated with the merge, or ``None``."""
        return self.m_merged_into_dependency_set

    def is_pruned(self) -> bool:
        """Return ``True`` if the node has been pruned."""
        return self.m_node_state == NodeState.PRUNED

    # ------------------------------------------------------------------
    # Linked-list navigation
    # ------------------------------------------------------------------

    @property
    def previous_tableau_node(self) -> Node | None:
        """Return the previous node in the tableau linked list."""
        return self.m_previous_tableau_node

    @property
    def next_tableau_node(self) -> Node | None:
        """Return the next node in the tableau linked list."""
        return self.m_next_tableau_node

    # ------------------------------------------------------------------
    # Canonical node and dependency-set resolution
    # ------------------------------------------------------------------

    def get_canonical_node(self) -> Node:
        """Follow merge links to find the canonical (surviving) node."""
        result = self
        while result.m_merged_into is not None:
            result = result.m_merged_into
        return result

    def get_canonical_node_dependency_set(self) -> PermanentDependencySet:
        """Return the union of dependency sets along the merge chain."""
        assert self.m_tableau is not None
        return self.add_canonical_node_dependency_set(
            self.m_tableau.m_dependency_set_factory.empty_set
        )

    def add_canonical_node_dependency_set(
        self, dependency_set: DependencySet
    ) -> PermanentDependencySet:
        """Return *dependency_set* unioned with all merge-chain sets."""
        assert self.m_tableau is not None
        factory = self.m_tableau.m_dependency_set_factory
        result = factory.get_permanent(dependency_set)
        node: Node | None = self
        while node.m_merged_into is not None:
            result = factory.union_with(result, node.m_merged_into_dependency_set)
            node = node.m_merged_into
        return result

    # ------------------------------------------------------------------
    # Unprocessed existentials
    # ------------------------------------------------------------------

    def _add_to_unprocessed_existentials(
        self, existential_concept: ExistentialConcept
    ) -> None:
        """Add *existential_concept* to the unprocessed queue."""
        assert Node._no_existentials == []
        if self.m_unprocessed_existentials is Node._no_existentials:
            assert self.m_tableau is not None
            self.m_unprocessed_existentials = (
                self.m_tableau.get_existential_concepts_buffer()
            )
            assert self.m_unprocessed_existentials == []
        self.m_unprocessed_existentials.append(existential_concept)

    def _remove_from_unprocessed_existentials(
        self, existential_concept: ExistentialConcept
    ) -> None:
        """Remove *existential_concept* from the unprocessed queue."""
        assert self.m_unprocessed_existentials is not Node._no_existentials
        assert len(self.m_unprocessed_existentials) > 0
        if existential_concept is self.m_unprocessed_existentials[-1]:
            self.m_unprocessed_existentials.pop()
        else:
            assert existential_concept in self.m_unprocessed_existentials
            self.m_unprocessed_existentials.remove(existential_concept)
        if len(self.m_unprocessed_existentials) == 0:
            assert self.m_tableau is not None
            self.m_tableau.put_existential_concepts_buffer(
                self.m_unprocessed_existentials
            )
            self.m_unprocessed_existentials = Node._no_existentials

    def has_unprocessed_existentials(self) -> bool:
        """Return ``True`` if there are unprocessed existential concepts."""
        return len(self.m_unprocessed_existentials) > 0

    def get_some_unprocessed_existential(self) -> ExistentialConcept:
        """Return an arbitrary unprocessed existential concept (LIFO order)."""
        return self.m_unprocessed_existentials[-1]

    @property
    def unprocessed_existentials(self) -> list[ExistentialConcept]:
        """Return the list of unprocessed existential concepts."""
        return self.m_unprocessed_existentials

    # ------------------------------------------------------------------
    # Debugging
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return str(self.m_node_id)

    def __repr__(self) -> str:
        return f"Node(id={self.m_node_id}, state={self.m_node_state})"
