"""Extension manager for tableau assertions.

Manages extension tables that store concept, role, and description-graph
assertions, along with their dependency sets and core flags.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, cast

from hermit.tableau.permanent_dependency_set import PermanentDependencySet

if TYPE_CHECKING:
    from hermit.model import Concept, DataRange, DLPredicate, Role
    from hermit.tableau.dependency_set import DependencySet
    from hermit.tableau.node import Node
    from hermit.tableau.tableau import Tableau


# ------------------------------------------------------------------
# ExtensionTable -- abstract base and concrete implementations
# ------------------------------------------------------------------


class TupleTable:
    """Flat table storing tuples as lists of objects."""

    __slots__ = ("_tuple_arity", "_data", "_size")

    def __init__(self, tuple_arity: int) -> None:
        self._tuple_arity = tuple_arity
        self._data: list[Any | None] = [None] * 64
        self._size = 0

    def clear(self) -> None:
        self._size = 0

    @property
    def size(self) -> int:
        return self._size

    def add_tuple(self, elements: list[Any]) -> int:
        """Append *elements* and return the tuple index."""
        needed = self._size + len(elements)
        if needed > len(self._data):
            new_len = max(needed, len(self._data) * 3 // 2)
            self._data = self._data + [None] * (new_len - len(self._data))
        for i, elem in enumerate(elements):
            self._data[self._size + i] = elem
        idx = self._size
        self._size += len(elements)
        return idx

    def retrieve_tuple(self, buffer: list[Any], tuple_index: int) -> None:
        # Copy only as many columns as the caller's buffer holds. A tuple slot
        # stores the logical columns first and (when dependency sets are kept)
        # one trailing dependency-set column; retrieval consumers size their
        # buffer to the logical arity they expect, so the trailing slot must not
        # overflow it.
        count = min(self._tuple_arity, len(buffer))
        for i in range(count):
            buffer[i] = self._data[tuple_index + i]

    def get_tuple_object(self, tuple_index: int, object_index: int) -> Any:
        return self._data[tuple_index + object_index]

    def truncate(self, size: int) -> None:
        self._size = size


class DependencySetManager(ABC):
    """Manages dependency sets associated with tuples."""

    def __init__(self, extension_table: ExtensionTable) -> None:
        self._extension_table = extension_table

    @abstractmethod
    def get_dependency_set(self, tuple_index: int) -> DependencySet | None: ...

    @abstractmethod
    def store_dependency_set(self, tuple_index: int, dependency_set: DependencySet) -> None: ...


class LastObjectDependencySetManager(DependencySetManager):
    """Stores dependency sets as the last object in each tuple slot."""

    def __init__(self, extension_table: ExtensionTable) -> None:
        super().__init__(extension_table)

    def get_dependency_set(self, tuple_index: int) -> DependencySet | None:
        arity = self._extension_table.m_tuple_arity
        table = self._extension_table.m_tuple_table
        return cast("DependencySet | None", table.get_tuple_object(tuple_index, arity))

    def store_dependency_set(self, tuple_index: int, dependency_set: DependencySet) -> None:
        arity = self._extension_table.m_tuple_arity
        table = self._extension_table.m_tuple_table
        table._data[tuple_index + arity] = dependency_set


class DeterministicDependencySetManager(DependencySetManager):
    """Returns the empty dependency set (deterministic case)."""

    def __init__(self, extension_table: ExtensionTable) -> None:
        super().__init__(extension_table)

    def get_dependency_set(self, tuple_index: int) -> DependencySet | None:
        return self._extension_table.m_tableau.m_dependency_set_factory.empty_set

    def store_dependency_set(self, tuple_index: int, dependency_set: DependencySet) -> None:
        pass


class CoreManager(ABC):
    """Manages core flags for tuples."""

    @abstractmethod
    def is_core(self, tuple_index: int) -> bool: ...

    @abstractmethod
    def mark_core(self, tuple_index: int, is_core: bool) -> None: ...


class RealCoreManager(CoreManager):
    """Stores core flags in a parallel list."""

    def __init__(self) -> None:
        self._core_flags: list[bool] = []

    def is_core(self, tuple_index: int) -> bool:
        if tuple_index < len(self._core_flags):
            return self._core_flags[tuple_index]
        return False

    def mark_core(self, tuple_index: int, is_core: bool) -> None:
        while len(self._core_flags) <= tuple_index:
            self._core_flags.append(False)
        self._core_flags[tuple_index] = is_core


class NoCoreManager(CoreManager):
    """Always returns False (no core tracking)."""

    def is_core(self, tuple_index: int) -> bool:
        return False

    def mark_core(self, tuple_index: int, is_core: bool) -> None:
        pass


class ExtensionTable(ABC):
    """Abstract base for extension tables storing tableau assertions.

    Extension tables track assertions (tuples) and support backtracking
    by truncating to previously saved sizes.
    """

    def __init__(
        self,
        tableau: Tableau,
        tuple_arity: int,
        needs_dependency_sets: bool,
    ) -> None:
        self.m_tableau = tableau
        self.m_tableau_monitor = tableau.m_tableau_monitor
        self.m_tuple_arity = tuple_arity
        self.m_tuple_table = TupleTable(tuple_arity + (1 if needs_dependency_sets else 0))
        self.m_dependency_set_manager: DependencySetManager = (
            LastObjectDependencySetManager(self)
            if needs_dependency_sets
            else DeterministicDependencySetManager(self)
        )
        self.m_core_manager: CoreManager = (
            RealCoreManager() if tuple_arity == 2 else NoCoreManager()
        )
        self.m_indices_by_branching_point: list[int] = [0] * (2 * 3)
        self._after_extension_old_tuple_index = 0
        self._after_extension_this_tuple_index = 0
        self._after_delta_new_tuple_index = 0

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def branching_point_pushed(self) -> None: ...

    @abstractmethod
    def backtrack(self) -> None: ...

    @abstractmethod
    def add_tuple(
        self,
        tuple_data: list[Any],
        dependency_set: DependencySet,
        is_core: bool,
    ) -> bool: ...

    @abstractmethod
    def contains_tuple(self, tuple_data: list[Any]) -> bool: ...

    @abstractmethod
    def get_dependency_set(self, tuple_data: list[Any]) -> DependencySet | None: ...

    @abstractmethod
    def is_core(self, tuple_data: list[Any]) -> bool: ...

    @abstractmethod
    def propagate_delta_new(self) -> bool: ...

    def get_dependency_set_by_index(self, tuple_index: int) -> DependencySet | None:
        """Return the dependency set for the tuple at *tuple_index*."""
        return self.m_dependency_set_manager.get_dependency_set(tuple_index)

    def is_core_by_index(self, tuple_index: int) -> bool:
        """Return whether the tuple at *tuple_index* is a core tuple."""
        return self.m_core_manager.is_core(tuple_index)

    def is_tuple_active(self, tuple_index: int) -> bool:
        """Return True if the tuple at the given flat-array index is currently active."""
        slot_size = self.m_tuple_arity + 1
        return tuple_index < self._after_extension_this_tuple_index * slot_size

    @abstractmethod
    def create_retrieval(
        self,
        bound_mask_or_positions: list[bool] | list[int],
        view_or_bindings: str | list[Any] = "TOTAL",
        tuple_buffer: list[Any] | None = None,
        owns_buffers: bool = False,
        view: str = "TOTAL",
    ) -> Retrieval:
        """Create a retrieval. Supports both Java-overloaded signatures.

        1. ``create_retrieval(bound_mask: list[bool], view: str)``
        2. ``create_retrieval(binding_positions, bindings_buffer, tuple_buffer, owns_buffers, view)``
        """
        ...

    @abstractmethod
    def create_retrieval_full(
        self,
        binding_positions: list[int],
        bindings_buffer: list[Any],
        tuple_buffer: list[Any],
        owns_buffers: bool,
        view: str,
    ) -> Retrieval: ...


class Retrieval(ABC):
    """Abstract iterator over tuples matching a bound pattern."""

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def next(self) -> None: ...

    @abstractmethod
    def after_last(self) -> bool: ...

    @abstractmethod
    def get_tuple_buffer(self) -> list[Any]: ...

    @abstractmethod
    def get_bindings_buffer(self) -> list[Any | None]: ...

    @abstractmethod
    def get_dependency_set(self) -> DependencySet | None: ...

    @abstractmethod
    def is_core(self) -> bool: ...

    @abstractmethod
    def get_extension_table(self) -> ExtensionTable: ...

    @abstractmethod
    def get_current_tuple_index(self) -> int: ...

    @abstractmethod
    def get_binding_positions(self) -> list[int]: ...


class _SimpleRetrieval(Retrieval):
    """Basic retrieval that scans all tuples matching a bound mask.

    Semantics (mirrors Java HermiT):
    - ``open()`` resets to start and pre-loads the first matching tuple.
    - ``after_last()`` returns True when no current valid tuple is loaded.
    - ``next()`` advances to and loads the next matching tuple.
    """

    def __init__(
        self,
        extension_table: ExtensionTable,
        bound_mask: list[bool],
        view: str,
    ) -> None:
        self._extension_table = extension_table
        self._bound_mask = bound_mask
        self._view = view
        # Buffer needs to hold arity+1 elements (includes dependency set slot)
        buf_size = extension_table.m_tuple_arity + 1
        self._tuple_buffer: list[Any] = [None] * buf_size
        self._bindings_buffer: list[Any | None] = [None] * len(bound_mask)
        self._current_index = -1
        self._start_index = 0
        self._end_index = 0
        self._arity = len(bound_mask)
        self._after_last = True

    def clear(self) -> None:
        self._current_index = -1
        self._after_last = True
        # Reset in-place to preserve shared references (evaluator CopyValues workers
        # hold a reference to the same list object).
        for i in range(len(self._tuple_buffer)):
            self._tuple_buffer[i] = None
        for i in range(len(self._bindings_buffer)):
            self._bindings_buffer[i] = None

    def open(self) -> None:
        arity = self._extension_table.m_tuple_arity
        slot_size = arity + 1
        if self._view == "EXTENSION_THIS":
            self._start_index = 0
            self._end_index = self._extension_table._after_extension_this_tuple_index * slot_size
        elif self._view == "EXTENSION_OLD":
            self._start_index = 0
            self._end_index = self._extension_table._after_extension_old_tuple_index * slot_size
        elif self._view == "DELTA_OLD":
            self._start_index = self._extension_table._after_extension_old_tuple_index * slot_size
            self._end_index = self._extension_table._after_extension_this_tuple_index * slot_size
        else:  # TOTAL
            self._start_index = 0
            self._end_index = self._extension_table._after_delta_new_tuple_index * slot_size

        self._current_index = self._start_index
        self._after_last = True
        # Pre-load first match (Java semantics: open() positions at first result)
        self._find_next()

    def _find_next(self) -> None:
        """Search forward from current position and load first match into buffer."""
        table = self._extension_table.m_tuple_table
        arity = self._extension_table.m_tuple_arity
        slot_size = arity + 1
        mask = self._bound_mask
        while self._current_index < self._end_index and self._current_index < table.size:
            match = True
            for i in range(arity):
                if mask[i]:
                    expected = self._bindings_buffer[i]
                    actual = table.get_tuple_object(self._current_index, i)
                    if actual is not expected:
                        match = False
                        break
            if match:
                table.retrieve_tuple(self._tuple_buffer, self._current_index)
                self._current_index += slot_size
                self._after_last = False
                return
            self._current_index += slot_size
        self._current_index = self._end_index
        self._after_last = True

    def next(self) -> None:
        self._after_last = True
        self._find_next()

    def after_last(self) -> bool:
        return self._after_last

    def get_tuple_buffer(self) -> list[Any]:
        return self._tuple_buffer

    def get_bindings_buffer(self) -> list[Any | None]:
        return self._bindings_buffer

    def get_dependency_set(self) -> DependencySet | None:
        idx = self._current_index - (self._extension_table.m_tuple_arity + 1)
        return self._extension_table.m_dependency_set_manager.get_dependency_set(idx)

    def is_core(self) -> bool:
        idx = self._current_index - (self._extension_table.m_tuple_arity + 1)
        return self._extension_table.m_core_manager.is_core(idx)

    def get_extension_table(self) -> ExtensionTable:
        return self._extension_table

    def get_current_tuple_index(self) -> int:
        slot_size = self._extension_table.m_tuple_arity + 1
        return self._current_index - slot_size

    def get_binding_positions(self) -> list[int]:
        return [i for i, bound in enumerate(self._bound_mask) if bound]


class _FullRetrieval(Retrieval):
    """Retrieval using explicit binding positions and external buffers.

    Mirrors the Java ``ExtensionTable.createRetrieval(int[], Object[], Object[], boolean, View)``.
    ``binding_positions[i] == -1`` means slot i is unbound (free variable);
    otherwise it is the index in ``bindings_buffer`` containing the bound value.

    Semantics (mirrors Java HermiT):
    - ``open()`` resets to start and pre-loads the first matching tuple.
    - ``after_last()`` returns True when no current valid tuple is loaded.
    - ``next()`` advances to and loads the next matching tuple.
    """

    def __init__(
        self,
        extension_table: ExtensionTable,
        binding_positions: list[int],
        bindings_buffer: list[Any],
        tuple_buffer: list[Any],
        owns_buffers: bool,
        view: str,
    ) -> None:
        self._extension_table = extension_table
        self._binding_positions = binding_positions
        self._bindings_buffer = bindings_buffer
        self._tuple_buffer = tuple_buffer
        self._owns_buffers = owns_buffers
        self._view = view
        self._current_index = -1
        self._arity = extension_table.m_tuple_arity
        self._after_last = True

    def clear(self) -> None:
        self._current_index = -1
        self._after_last = True

    def open(self) -> None:
        self._current_index = 0
        self._after_last = True
        # Pre-load first match (Java semantics: open() positions at first result)
        self._find_next()

    def _find_next(self) -> None:
        """Search forward from current position and load first match into buffer."""
        table = self._extension_table.m_tuple_table
        arity = self._arity
        slot_size = arity + 1
        positions = self._binding_positions
        bindings = self._bindings_buffer
        while self._current_index < table.size:
            match = True
            for i in range(slot_size):
                pos = positions[i]
                if pos >= 0:
                    expected = bindings[pos]
                    actual = table.get_tuple_object(self._current_index, i)
                    if actual is not expected:
                        match = False
                        break
            if match:
                table.retrieve_tuple(self._tuple_buffer, self._current_index)
                self._current_index += slot_size
                self._after_last = False
                return
            self._current_index += slot_size
        self._current_index = table.size
        self._after_last = True

    def next(self) -> None:
        self._after_last = True
        self._find_next()

    def after_last(self) -> bool:
        return self._after_last

    def get_tuple_buffer(self) -> list[Any]:
        return self._tuple_buffer

    def get_bindings_buffer(self) -> list[Any]:
        return self._bindings_buffer

    def get_dependency_set(self) -> DependencySet | None:
        idx = self._current_index - (self._arity + 1)
        return self._extension_table.m_dependency_set_manager.get_dependency_set(idx)

    def is_core(self) -> bool:
        idx = self._current_index - (self._arity + 1)
        return self._extension_table.m_core_manager.is_core(idx)

    def get_extension_table(self) -> ExtensionTable:
        return self._extension_table

    def get_current_tuple_index(self) -> int:
        slot_size = self._arity + 1
        return self._current_index - slot_size

    def get_binding_positions(self) -> list[int]:
        return [pos for pos in self._binding_positions if pos >= 0]


class ExtensionTableWithTupleIndexes(ExtensionTable):
    """Extension table with tuple-based indexing."""

    def __init__(
        self,
        tableau: Tableau,
        tuple_arity: int,
        needs_dependency_sets: bool,
        tuple_indexes: list[Any] | None = None,
    ) -> None:
        super().__init__(tableau, tuple_arity, needs_dependency_sets)
        self._is_tuple_active_override: Any = None
        # For branching point tracking
        self._bp_tuple_index = 0
        self._bp_delta_index = 0
        self._bp_extension_index = 0

    def clear(self) -> None:
        self.m_tuple_table.clear()
        if isinstance(self.m_core_manager, RealCoreManager):
            self.m_core_manager._core_flags.clear()
        self._after_extension_old_tuple_index = 0
        self._after_extension_this_tuple_index = 0
        self._after_delta_new_tuple_index = 0

    def branching_point_pushed(self) -> None:
        slot_size = self.m_tuple_arity + 1
        self._after_extension_this_tuple_index = self.m_tuple_table.size // slot_size
        self._after_delta_new_tuple_index = self.m_tuple_table.size // slot_size

    def backtrack(self) -> None:
        self.m_tuple_table.truncate(self._after_extension_old_tuple_index * (self.m_tuple_arity + 1))
        slot_size = self.m_tuple_arity + 1
        self._after_extension_this_tuple_index = self.m_tuple_table.size // slot_size
        self._after_delta_new_tuple_index = self.m_tuple_table.size // slot_size

    def add_tuple(
        self,
        tuple_data: list[Any],
        dependency_set: DependencySet,
        is_core: bool,
    ) -> bool:
        if self.contains_tuple(tuple_data):
            return False
        # Store dependency set
        elements = list(tuple_data)
        if self.m_tuple_arity < len(self._tuple_buffer) if hasattr(self, "_tuple_buffer") else True:
            elements.append(dependency_set)
        tuple_index = self.m_tuple_table.add_tuple(elements)
        self.m_dependency_set_manager.store_dependency_set(tuple_index, dependency_set)
        if is_core:
            self.m_core_manager.mark_core(tuple_index, True)

        # Post-add processing (mirrors Java ExtensionTable.postAdd)
        dl_predicate = tuple_data[0]
        from hermit.model import (
            AtomicConcept,
            AtomicNegationConcept,
            AtomicRole,
            DataRange,
            DescriptionGraph,
            ExistentialConcept,
            NegatedAtomicRole,
        )
        if isinstance(dl_predicate, AtomicConcept):
            node = tuple_data[1]
            if node is not None:  # Guard against None nodes from invalid derivations
                node.m_number_of_positive_atomic_concepts += 1
                if self.m_tableau is not None:
                    strat = self.m_tableau.m_existential_expansion_strategy
                    strat.assertion_added_concept(dl_predicate, node, is_core)
        elif isinstance(dl_predicate, ExistentialConcept):
            node = tuple_data[1]
            if node is not None:  # Guard against None nodes
                node.add_unprocessed_existential(dl_predicate)
                if self.m_tableau is not None:
                    strat = self.m_tableau.m_existential_expansion_strategy
                    strat.assertion_added_concept(dl_predicate, node, is_core)
        elif isinstance(dl_predicate, AtomicNegationConcept):
            node = tuple_data[1]
            if node is not None:  # Guard against None nodes
                node.m_number_of_negated_atomic_concepts += 1
        elif isinstance(dl_predicate, DataRange):
            node = tuple_data[1]
            if self.m_tableau is not None:
                strat = self.m_tableau.m_existential_expansion_strategy
                strat.assertion_added_data_range(dl_predicate, node, is_core)
        elif isinstance(dl_predicate, AtomicRole):
            node1 = tuple_data[1]
            node2 = tuple_data[2]
            if self.m_tableau is not None:
                strat = self.m_tableau.m_existential_expansion_strategy
                strat.assertion_added_atomic_role(dl_predicate, node1, node2, is_core)
        elif isinstance(dl_predicate, NegatedAtomicRole):
            node = tuple_data[1]
            node.m_number_of_negated_role_assertions += 1
        elif isinstance(dl_predicate, DescriptionGraph):
            self.m_tableau.m_description_graph_manager.description_graph_tuple_added(tuple_index, tuple_data)

        # Notify clash manager
        self.m_tableau.m_clash_manager.tuple_added(self, tuple_data, dependency_set, is_core)
        return True

    def contains_tuple(self, tuple_data: list[Any]) -> bool:
        table = self.m_tuple_table
        arity = self.m_tuple_arity
        for idx in range(0, table.size, arity + 1):
            match = True
            for i in range(arity):
                if table.get_tuple_object(idx, i) is not tuple_data[i]:
                    match = False
                    break
            if match:
                return True
        return False

    def get_dependency_set(self, tuple_data: list[Any]) -> DependencySet | None:
        table = self.m_tuple_table
        arity = self.m_tuple_arity
        for idx in range(0, table.size, arity + 1):
            match = True
            for i in range(arity):
                if table.get_tuple_object(idx, i) is not tuple_data[i]:
                    match = False
                    break
            if match:
                return self.m_dependency_set_manager.get_dependency_set(idx)
        return None

    def is_core(self, tuple_data: list[Any]) -> bool:
        table = self.m_tuple_table
        arity = self.m_tuple_arity
        for idx in range(0, table.size, arity + 1):
            match = True
            for i in range(arity):
                if table.get_tuple_object(idx, i) is not tuple_data[i]:
                    match = False
                    break
            if match:
                return self.m_core_manager.is_core(idx)
        return False

    def propagate_delta_new(self) -> bool:
        """Propagate delta-new tuples to extension-this, and extension-this to extension-old.

        Mirrors the Java ExtensionTable.propagateDeltaNew():
            boolean deltaNewNotEmpty = (m_afterExtensionThisTupleIndex != m_afterDeltaNewTupleIndex);
            m_afterExtensionOldTupleIndex = m_afterExtensionThisTupleIndex;
            m_afterExtensionThisTupleIndex = m_afterDeltaNewTupleIndex;
            m_afterDeltaNewTupleIndex = m_tupleTable.getFirstFreeTupleIndex();
            return deltaNewNotEmpty;

        Note: The Python TupleTable uses element indices (flat array), not tuple indices.
        Each tuple occupies (arity + 1) element slots (the extra slot is for the dependency set).
        We convert element count to tuple count by dividing by (arity + 1).

        Additional fix: after clear() when both indices are 0 but tuples exist (loaded
        before any propagation), treat all existing tuples as delta_new.
        """
        slot_size = self.m_tuple_arity + 1
        first_free_tuple_index = self.m_tuple_table.size // slot_size

        # If both indices are 0 but there are tuples, treat all as delta_new
        if (
            self._after_extension_this_tuple_index == 0
            and self._after_delta_new_tuple_index == 0
            and first_free_tuple_index > 0
        ):
            self._after_delta_new_tuple_index = first_free_tuple_index

        delta_new_not_empty = (
            self._after_extension_this_tuple_index != self._after_delta_new_tuple_index
        )
        self._after_extension_old_tuple_index = self._after_extension_this_tuple_index
        self._after_extension_this_tuple_index = self._after_delta_new_tuple_index
        self._after_delta_new_tuple_index = first_free_tuple_index
        return delta_new_not_empty

    def create_retrieval(
        self,
        bound_mask_or_positions: list[bool] | list[int],
        view_or_bindings: str | list[Any] = "TOTAL",
        tuple_buffer: list[Any] | None = None,
        owns_buffers: bool = False,
        view: str = "TOTAL",
    ) -> Retrieval:
        """Create a retrieval. Supports both Java-overloaded signatures:

        1. ``create_retrieval(bound_mask: list[bool], view: str)``
        2. ``create_retrieval(binding_positions, bindings_buffer, tuple_buffer, owns_buffers, view)``
        """
        # Detect signature by checking first element type
        if bound_mask_or_positions and isinstance(bound_mask_or_positions[0], bool):
            # Simple retrieval: (bound_mask, view)
            v = view_or_bindings if isinstance(view_or_bindings, str) else view
            return _SimpleRetrieval(self, cast("list[bool]", bound_mask_or_positions), v)
        else:
            # Full retrieval: (binding_positions, bindings_buffer, tuple_buffer, owns_buffers, view)
            bindings = view_or_bindings if isinstance(view_or_bindings, list) else []
            return _FullRetrieval(
                self, cast("list[int]", bound_mask_or_positions), bindings,
                tuple_buffer or [None] * len(bound_mask_or_positions),
                owns_buffers, view
            )

    def create_retrieval_full(
        self,
        binding_positions: list[int],
        bindings_buffer: list[Any],
        tuple_buffer: list[Any],
        owns_buffers: bool,
        view: str,
    ) -> Retrieval:
        return _FullRetrieval(
            self, binding_positions, bindings_buffer, tuple_buffer, owns_buffers, view
        )


class ExtensionTableWithFullIndex(ExtensionTableWithTupleIndexes):
    """Extension table with full indexing (for description graphs)."""

    def __init__(
        self,
        tableau: Tableau,
        tuple_arity: int,
        needs_dependency_sets: bool,
    ) -> None:
        super().__init__(tableau, tuple_arity, needs_dependency_sets)


# ------------------------------------------------------------------
# ExtensionManager
# ------------------------------------------------------------------


class ExtensionManager:
    """Manages extension tables for tableau assertions.

    The extension manager stores tuples representing concept assertions
    (binary), role assertions (ternary), and description-graph assertions
    (n-ary).  It coordinates addition, lookup, and clash detection.

    Args:
        tableau: The owning tableau.
    """

    __slots__ = (
        "m_tableau",
        "m_tableau_monitor",
        "m_dependency_set_factory",
        "m_extension_tables_by_arity",
        "m_all_extension_tables_array",
        "m_binary_extension_table",
        "m_ternary_extension_table",
        "m_binary_auxiliary_tuple_contains",
        "m_binary_auxiliary_tuple_add",
        "m_ternary_auxiliary_tuple_contains",
        "m_ternary_auxiliary_tuple_add",
        "m_fourary_auxiliary_tuple_contains",
        "m_fourary_auxiliary_tuple_add",
        "_clash_dependency_set",
        "_add_active",
    )

    def __init__(self, tableau: Tableau) -> None:
        self.m_tableau = tableau
        self.m_tableau_monitor = tableau.m_tableau_monitor
        self.m_dependency_set_factory = tableau.m_dependency_set_factory
        self.m_extension_tables_by_arity: dict[int, ExtensionTable] = {}

        # Binary extension table (arity 2: concept assertions)
        self.m_binary_extension_table = ExtensionTableWithTupleIndexes(
            tableau, 2, not tableau.is_deterministic()
        )
        self.m_extension_tables_by_arity[2] = self.m_binary_extension_table

        # Ternary extension table (arity 3: role assertions)
        self.m_ternary_extension_table = ExtensionTableWithTupleIndexes(
            tableau, 3, not tableau.is_deterministic()
        )
        self.m_extension_tables_by_arity[3] = self.m_ternary_extension_table

        # Description graph tables (created from permanent ontology)

        for description_graph in tableau.m_permanent_dl_ontology.get_all_description_graphs():
            arity_int = description_graph.number_of_vertices() + 1
            if arity_int not in self.m_extension_tables_by_arity:
                self.m_extension_tables_by_arity[arity_int] = (
                    ExtensionTableWithFullIndex(
                        tableau, arity_int, not tableau.is_deterministic()
                    )
                )

        self.m_all_extension_tables_array: list[ExtensionTable] = list(
            self.m_extension_tables_by_arity.values()
        )

        # Auxiliary tuples for contains / add operations
        self.m_binary_auxiliary_tuple_contains: list[Any] = [None, None]
        self.m_binary_auxiliary_tuple_add: list[Any] = [None, None]
        self.m_ternary_auxiliary_tuple_contains: list[Any] = [None, None, None]
        self.m_ternary_auxiliary_tuple_add: list[Any] = [None, None, None]
        self.m_fourary_auxiliary_tuple_contains: list[Any] = [None, None, None, None]
        self.m_fourary_auxiliary_tuple_add: list[Any] = [None, None, None, None]

        self._clash_dependency_set: PermanentDependencySet | None = None
        self._add_active = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Clear all extension tables and auxiliary buffers."""
        for table in reversed(self.m_all_extension_tables_array):
            table.clear()
        self._clash_dependency_set = None
        for i in range(2):
            self.m_binary_auxiliary_tuple_contains[i] = None
            self.m_binary_auxiliary_tuple_add[i] = None
        for i in range(3):
            self.m_ternary_auxiliary_tuple_contains[i] = None
            self.m_ternary_auxiliary_tuple_add[i] = None
        for i in range(4):
            self.m_fourary_auxiliary_tuple_contains[i] = None
            self.m_fourary_auxiliary_tuple_add[i] = None

    def branching_point_pushed(self) -> None:
        """Notify all extension tables that a new branching point was pushed."""
        for table in reversed(self.m_all_extension_tables_array):
            table.branching_point_pushed()

    def backtrack(self) -> None:
        """Backtrack all extension tables to the current branching point."""
        for table in reversed(self.m_all_extension_tables_array):
            table.backtrack()

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def binary_extension_table(self) -> ExtensionTable:
        """Return the binary (concept-assertion) extension table."""
        return self.m_binary_extension_table

    def get_binary_extension_table(self) -> ExtensionTable:
        """Java-compatible alias for :attr:`binary_extension_table`."""
        return self.m_binary_extension_table

    @property
    def ternary_extension_table(self) -> ExtensionTable:
        """Return the ternary (role-assertion) extension table."""
        return self.m_ternary_extension_table

    def get_ternary_extension_table(self) -> ExtensionTable:
        """Java-compatible alias for :attr:`ternary_extension_table`."""
        return self.m_ternary_extension_table

    def get_extension_table(self, arity: int) -> ExtensionTable:
        """Return the extension table for the given arity."""
        if arity == 2:
            return self.m_binary_extension_table
        if arity == 3:
            return self.m_ternary_extension_table
        return self.m_extension_tables_by_arity[arity]

    def get_extension_tables(self) -> list[ExtensionTable]:
        """Return all extension tables."""
        return list(self.m_extension_tables_by_arity.values())

    # ------------------------------------------------------------------
    # Propagation
    # ------------------------------------------------------------------

    def propagate_delta_new(self) -> bool:
        """Propagate delta-new tuples through hyperresolution rules.

        Returns:
            ``True`` if any changes were made.
        """
        has_change = False
        for table in self.m_all_extension_tables_array:
            if table.propagate_delta_new():
                has_change = True
        return has_change

    # ------------------------------------------------------------------
    # Clash management
    # ------------------------------------------------------------------

    def clear_clash(self) -> None:
        """Clear the current clash dependency set."""
        if self._clash_dependency_set is not None:
            self.m_dependency_set_factory.remove_usage(self._clash_dependency_set)
            self._clash_dependency_set = None

    def set_clash(self, clash_dependency_set: DependencySet) -> None:
        """Record a clash with the given dependency set.

        Args:
            clash_dependency_set: The dependency set that caused the clash.
        """
        if self._clash_dependency_set is not None:
            self.m_dependency_set_factory.remove_usage(self._clash_dependency_set)
        self._clash_dependency_set = self.m_dependency_set_factory.get_permanent(
            clash_dependency_set
        )
        if self._clash_dependency_set is not None:
            self.m_dependency_set_factory.add_usage(self._clash_dependency_set)
        if self.m_tableau_monitor is not None:
            self.m_tableau_monitor.clash_detected()

    @property
    def clash_dependency_set(self) -> DependencySet | None:
        """Return the current clash dependency set, or ``None``."""
        return self._clash_dependency_set

    def contains_clash(self) -> bool:
        """Return ``True`` if a clash has been detected."""
        return self._clash_dependency_set is not None

    # ------------------------------------------------------------------
    # Contains checks
    # ------------------------------------------------------------------

    def contains_concept_assertion(self, concept: Concept, node: Node) -> bool:
        """Check whether *concept* is asserted to *node*."""
        from hermit.model import AtomicConcept

        assert node.node_type is not None
        if node.node_type.is_abstract and AtomicConcept.THING is concept:
            return True
        self.m_binary_auxiliary_tuple_contains[0] = concept
        self.m_binary_auxiliary_tuple_contains[1] = node
        return self.m_binary_extension_table.contains_tuple(
            self.m_binary_auxiliary_tuple_contains
        )

    def contains_data_range_assertion(self, data_range: DataRange, node: Node) -> bool:
        """Check whether *data_range* is asserted to *node*."""
        from hermit.datatypes import InternalDatatype

        assert node.node_type is not None
        if not node.node_type.is_abstract and InternalDatatype.RDFS_LITERAL is data_range:
            return True
        self.m_binary_auxiliary_tuple_contains[0] = data_range
        self.m_binary_auxiliary_tuple_contains[1] = node
        return self.m_binary_extension_table.contains_tuple(
            self.m_binary_auxiliary_tuple_contains
        )

    def contains_role_assertion(
        self, role: Role, node_from: Node, node_to: Node
    ) -> bool:
        """Check whether *role*(*node_from*, *node_to*) is asserted."""
        from hermit.model import AtomicRole, InverseRole

        if isinstance(role, AtomicRole):
            self.m_ternary_auxiliary_tuple_contains[0] = role
            self.m_ternary_auxiliary_tuple_contains[1] = node_from
            self.m_ternary_auxiliary_tuple_contains[2] = node_to
        else:
            assert isinstance(role, InverseRole)
            self.m_ternary_auxiliary_tuple_contains[0] = role.inverse_of
            self.m_ternary_auxiliary_tuple_contains[1] = node_to
            self.m_ternary_auxiliary_tuple_contains[2] = node_from
        return self.m_ternary_extension_table.contains_tuple(
            self.m_ternary_auxiliary_tuple_contains
        )

    def contains_assertion(self, dl_predicate: DLPredicate, *nodes: Node) -> bool:
        """Dispatch to the appropriate contains_assertion_* based on node count."""
        if len(nodes) == 1:
            return self.contains_assertion_unary(dl_predicate, nodes[0])
        elif len(nodes) == 2:
            return self.contains_assertion_binary(dl_predicate, nodes[0], nodes[1])
        elif len(nodes) == 3:
            return self.contains_assertion_ternary(dl_predicate, nodes[0], nodes[1], nodes[2])
        raise ValueError(f"Unsupported number of nodes: {len(nodes)}")

    def contains_assertion_unary(self, dl_predicate: DLPredicate, node: Node) -> bool:
        """Check a unary assertion."""
        from hermit.model import AtomicConcept

        if AtomicConcept.THING is dl_predicate:
            return True
        self.m_binary_auxiliary_tuple_contains[0] = dl_predicate
        self.m_binary_auxiliary_tuple_contains[1] = node
        return self.m_binary_extension_table.contains_tuple(
            self.m_binary_auxiliary_tuple_contains
        )

    def contains_assertion_binary(
        self, dl_predicate: DLPredicate, node0: Node, node1: Node
    ) -> bool:
        """Check a binary assertion."""
        from hermit.model import Equality

        if Equality.INSTANCE is dl_predicate:
            return node0 is node1
        self.m_ternary_auxiliary_tuple_contains[0] = dl_predicate
        self.m_ternary_auxiliary_tuple_contains[1] = node0
        self.m_ternary_auxiliary_tuple_contains[2] = node1
        return self.m_ternary_extension_table.contains_tuple(
            self.m_ternary_auxiliary_tuple_contains
        )

    def contains_assertion_ternary(
        self, dl_predicate: DLPredicate, node0: Node, node1: Node, node2: Node
    ) -> bool:
        """Check a ternary assertion."""
        self.m_fourary_auxiliary_tuple_contains[0] = dl_predicate
        self.m_fourary_auxiliary_tuple_contains[1] = node0
        self.m_fourary_auxiliary_tuple_contains[2] = node1
        self.m_fourary_auxiliary_tuple_contains[3] = node2
        return self.contains_tuple(self.m_fourary_auxiliary_tuple_contains)

    def contains_annotated_equality(
        self,
        annotated_equality: Any,
        node0: Node,
        node1: Node,
        node2: Node,
    ) -> bool:
        """Check an annotated equality."""
        return (
            self.m_tableau.m_nominal_introduction_manager.can_forget_annotation(
                annotated_equality, node0, node1, node2
            )
            and node0 is node1
        )

    def contains_tuple(self, tuple_data: list[Any]) -> bool:
        """Check whether *tuple_data* is present in the appropriate table."""
        from hermit.model import AnnotatedEquality, AtomicConcept, Equality

        if len(tuple_data) == 0:
            return self.contains_clash()
        if AtomicConcept.THING is tuple_data[0]:
            return True
        if Equality.INSTANCE is tuple_data[0]:
            return tuple_data[1] is tuple_data[2]
        if isinstance(tuple_data[0], AnnotatedEquality):
            return (
                self.m_tableau.m_nominal_introduction_manager.can_forget_annotation(
                    tuple_data[0],
                    tuple_data[1],
                    tuple_data[2],
                    tuple_data[3],
                )
                and tuple_data[1] is tuple_data[2]
            )
        return self.get_extension_table(len(tuple_data)).contains_tuple(tuple_data)

    # ------------------------------------------------------------------
    # Dependency-set retrieval
    # ------------------------------------------------------------------

    def get_concept_assertion_dependency_set(
        self, concept: Concept, node: Node
    ) -> DependencySet | None:
        """Return the dependency set for a concept assertion."""
        from hermit.model import AtomicConcept

        if AtomicConcept.THING is concept:
            return self.m_dependency_set_factory.empty_set
        self.m_binary_auxiliary_tuple_contains[0] = concept
        self.m_binary_auxiliary_tuple_contains[1] = node
        return self.m_binary_extension_table.get_dependency_set(
            self.m_binary_auxiliary_tuple_contains
        )

    def get_data_range_assertion_dependency_set(
        self, data_range: DataRange, node: Node
    ) -> DependencySet | None:
        """Return the dependency set for a data-range assertion."""
        from hermit.datatypes import InternalDatatype

        if InternalDatatype.RDFS_LITERAL is data_range:
            return self.m_dependency_set_factory.empty_set
        self.m_binary_auxiliary_tuple_contains[0] = data_range
        self.m_binary_auxiliary_tuple_contains[1] = node
        return self.m_binary_extension_table.get_dependency_set(
            self.m_binary_auxiliary_tuple_contains
        )

    def get_role_assertion_dependency_set(
        self, role: Role, node_from: Node, node_to: Node
    ) -> DependencySet | None:
        """Return the dependency set for a role assertion."""
        from hermit.model import AtomicRole, InverseRole

        if isinstance(role, AtomicRole):
            self.m_ternary_auxiliary_tuple_contains[0] = role
            self.m_ternary_auxiliary_tuple_contains[1] = node_from
            self.m_ternary_auxiliary_tuple_contains[2] = node_to
        else:
            assert isinstance(role, InverseRole)
            self.m_ternary_auxiliary_tuple_contains[0] = role.inverse_of
            self.m_ternary_auxiliary_tuple_contains[1] = node_to
            self.m_ternary_auxiliary_tuple_contains[2] = node_from
        return self.m_ternary_extension_table.get_dependency_set(
            self.m_ternary_auxiliary_tuple_contains
        )

    def get_assertion_dependency_set_unary(
        self, dl_predicate: DLPredicate, node: Node
    ) -> DependencySet | None:
        """Return the dependency set for a unary assertion."""
        self.m_binary_auxiliary_tuple_contains[0] = dl_predicate
        self.m_binary_auxiliary_tuple_contains[1] = node
        return self.m_binary_extension_table.get_dependency_set(
            self.m_binary_auxiliary_tuple_contains
        )

    def get_assertion_dependency_set_binary(
        self, dl_predicate: DLPredicate, node0: Node, node1: Node
    ) -> DependencySet | None:
        """Return the dependency set for a binary assertion."""
        from hermit.model import Equality

        if Equality.INSTANCE is dl_predicate:
            return (
                self.m_dependency_set_factory.empty_set if node0 is node1 else None
            )
        self.m_ternary_auxiliary_tuple_contains[0] = dl_predicate
        self.m_ternary_auxiliary_tuple_contains[1] = node0
        self.m_ternary_auxiliary_tuple_contains[2] = node1
        return self.m_ternary_extension_table.get_dependency_set(
            self.m_ternary_auxiliary_tuple_contains
        )

    def get_assertion_dependency_set_ternary(
        self, dl_predicate: DLPredicate, node0: Node, node1: Node, node2: Node
    ) -> DependencySet | None:
        """Return the dependency set for a ternary assertion."""
        self.m_fourary_auxiliary_tuple_contains[0] = dl_predicate
        self.m_fourary_auxiliary_tuple_contains[1] = node0
        self.m_fourary_auxiliary_tuple_contains[2] = node1
        self.m_fourary_auxiliary_tuple_contains[3] = node2
        return self.get_tuple_dependency_set(self.m_fourary_auxiliary_tuple_contains)

    def get_tuple_dependency_set(
        self, tuple_data: list[Any]
    ) -> DependencySet | None:
        """Return the dependency set for an arbitrary tuple."""
        if len(tuple_data) == 0:
            return self._clash_dependency_set
        return self.get_extension_table(len(tuple_data)).get_dependency_set(tuple_data)

    def is_core(self, tuple_data: list[Any]) -> bool:
        """Return whether *tuple_data* is a core assertion."""
        if len(tuple_data) == 0:
            return True
        return self.get_extension_table(len(tuple_data)).is_core(tuple_data)

    # ------------------------------------------------------------------
    # Add operations
    # ------------------------------------------------------------------

    def add_concept_assertion(
        self,
        concept: Concept,
        node: Node,
        dependency_set: DependencySet,
        is_core: bool,
    ) -> bool:
        """Add a concept assertion to the tableau.

        Args:
            concept: The concept being asserted.
            node: The node receiving the assertion.
            dependency_set: The dependencies of this assertion.
            is_core: Whether the assertion is a core (non-backtrackable) fact.

        Returns:
            ``True`` if the assertion was newly added.
        """
        if self._add_active:
            raise RuntimeError("ExtensionManager is not reentrant.")
        self._add_active = True
        try:
            self.m_binary_auxiliary_tuple_add[0] = concept
            self.m_binary_auxiliary_tuple_add[1] = node
            return self.m_binary_extension_table.add_tuple(
                self.m_binary_auxiliary_tuple_add, dependency_set, is_core
            )
        finally:
            self._add_active = False

    def add_data_range_assertion(
        self,
        data_range: DataRange,
        node: Node,
        dependency_set: DependencySet,
        is_core: bool,
    ) -> bool:
        """Add a data-range assertion to the tableau."""
        if self._add_active:
            raise RuntimeError("ExtensionManager is not reentrant.")
        self._add_active = True
        try:
            self.m_binary_auxiliary_tuple_add[0] = data_range
            self.m_binary_auxiliary_tuple_add[1] = node
            return self.m_binary_extension_table.add_tuple(
                self.m_binary_auxiliary_tuple_add, dependency_set, is_core
            )
        finally:
            self._add_active = False

    def add_role_assertion(
        self,
        role: Role,
        node_from: Node,
        node_to: Node,
        dependency_set: DependencySet,
        is_core: bool,
    ) -> bool:
        """Add a role assertion, handling inverse roles."""
        from hermit.model import AtomicRole, InverseRole

        if isinstance(role, AtomicRole):
            return self.add_assertion_binary(
                role, node_from, node_to, dependency_set, is_core
            )
        else:
            assert isinstance(role, InverseRole)
            return self.add_assertion_binary(
                role.inverse_of, node_to, node_from, dependency_set, is_core
            )

    def add_assertion(
        self,
        dl_predicate: DLPredicate,
        *args: Any,
    ) -> bool:
        """Add an assertion, dispatching by arity.

        Supports the following call signatures (mirroring Java overloading):
        - ``(dl_predicate, node, dependency_set, is_core)`` — unary
        - ``(dl_predicate, node0, node1, dependency_set, is_core)`` — binary
        - ``(dl_predicate, node0, node1, node2, dependency_set, is_core)`` — ternary
        """
        n = len(args)
        if n == 3:
            # Unary: (node, dependency_set, is_core)
            node, ds, core = args
            return self.add_assertion_unary(dl_predicate, node, ds, core)
        elif n == 4:
            # Binary: (node0, node1, dependency_set, is_core)
            node0, node1, ds, core = args
            return self.add_assertion_binary(dl_predicate, node0, node1, ds, core)
        elif n == 5:
            # Ternary: (node0, node1, node2, dependency_set, is_core)
            node0, node1, node2, ds, core = args
            return self.add_assertion_ternary(dl_predicate, node0, node1, node2, ds, core)
        else:
            raise ValueError(
                f"add_assertion requires 3-5 additional arguments, got {n}"
            )

    def add_assertion_unary(
        self,
        dl_predicate: DLPredicate,
        node: Node,
        dependency_set: DependencySet,
        is_core: bool,
    ) -> bool:
        """Add a unary assertion (DLPredicate on a single node)."""
        if self._add_active:
            raise RuntimeError("ExtensionManager is not reentrant.")
        # Canonicalize the node in case it was merged
        if node is not None:
            node = node.get_canonical_node()
        self._add_active = True
        try:
            self.m_binary_auxiliary_tuple_add[0] = dl_predicate
            self.m_binary_auxiliary_tuple_add[1] = node
            return self.m_binary_extension_table.add_tuple(
                self.m_binary_auxiliary_tuple_add, dependency_set, is_core
            )
        finally:
            self._add_active = False

    def add_assertion_binary(
        self,
        dl_predicate: DLPredicate,
        node0: Node,
        node1: Node,
        dependency_set: DependencySet,
        is_core: bool,
    ) -> bool:
        """Add a binary assertion (DLPredicate on two nodes).

        For equality predicates this triggers node merging.
        """
        from hermit.model import Equality

        if Equality.INSTANCE is dl_predicate:
            return self.m_tableau.m_merging_manager.merge_nodes(
                node0, node1, dependency_set
            )
        # Canonicalize nodes in case they were merged
        if node0 is not None:
            node0 = node0.get_canonical_node()
        if node1 is not None:
            node1 = node1.get_canonical_node()
        if node0 is None or node1 is None:
            return False
        if self._add_active:
            raise RuntimeError("ExtensionManager is not reentrant.")
        self._add_active = True
        try:
            self.m_ternary_auxiliary_tuple_add[0] = dl_predicate
            self.m_ternary_auxiliary_tuple_add[1] = node0
            self.m_ternary_auxiliary_tuple_add[2] = node1
            return self.m_ternary_extension_table.add_tuple(
                self.m_ternary_auxiliary_tuple_add, dependency_set, is_core
            )
        finally:
            self._add_active = False

    def add_assertion_ternary(
        self,
        dl_predicate: DLPredicate,
        node0: Node,
        node1: Node,
        node2: Node,
        dependency_set: DependencySet,
        is_core: bool,
    ) -> bool:
        """Add a ternary assertion (DLPredicate on three nodes)."""
        # Canonicalize nodes in case they were merged
        node0 = node0.get_canonical_node()
        node1 = node1.get_canonical_node()
        node2 = node2.get_canonical_node()
        if self._add_active:
            raise RuntimeError("ExtensionManager is not reentrant.")
        self.m_fourary_auxiliary_tuple_add[0] = dl_predicate
        self.m_fourary_auxiliary_tuple_add[1] = node0
        self.m_fourary_auxiliary_tuple_add[2] = node1
        self.m_fourary_auxiliary_tuple_add[3] = node2
        return self.add_tuple(self.m_fourary_auxiliary_tuple_add, dependency_set, is_core)

    def add_annotated_equality(
        self,
        annotated_equality: Any,
        node0: Node,
        node1: Node,
        node2: Node,
        dependency_set: DependencySet,
    ) -> bool:
        """Add an annotated equality via the nominal introduction manager."""
        return self.m_tableau.m_nominal_introduction_manager.add_annotated_equality(
            annotated_equality, node0, node1, node2, dependency_set
        )

    def add_tuple(
        self,
        tuple_data: list[Any],
        dependency_set: DependencySet,
        is_core: bool,
    ) -> bool:
        """Add an arbitrary tuple to the appropriate extension table.

        Special cases:
        - Empty tuple -> clash detection.
        - Equality -> node merging.
        - AnnotatedEquality -> nominal introduction manager.
        """
        from hermit.model import AnnotatedEquality, Equality

        if len(tuple_data) == 0:
            result = self._clash_dependency_set is None
            self.set_clash(dependency_set)
            return result
        if Equality.INSTANCE is tuple_data[0]:
            return self.m_tableau.m_merging_manager.merge_nodes(
                tuple_data[1],
                tuple_data[2],
                dependency_set,
            )
        if isinstance(tuple_data[0], AnnotatedEquality):
            return self.m_tableau.m_nominal_introduction_manager.add_annotated_equality(
                tuple_data[0],
                tuple_data[1],
                tuple_data[2],
                tuple_data[3],
                dependency_set,
            )
        if self._add_active:
            raise RuntimeError("ExtensionManager is not reentrant.")
        self._add_active = True
        try:
            return self.get_extension_table(len(tuple_data)).add_tuple(
                tuple_data, dependency_set, is_core
            )
        finally:
            self._add_active = False
