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

    @abstractmethod
    def forget_dependency_set(self, tuple_index: int) -> None: ...


class LastObjectDependencySetManager(DependencySetManager):
    """Stores dependency sets as the last object in each tuple slot."""

    def __init__(self, extension_table: ExtensionTable) -> None:
        super().__init__(extension_table)

    def get_dependency_set(self, tuple_index: int) -> DependencySet | None:
        arity = self._extension_table.m_tuple_arity
        table = self._extension_table.m_tuple_table
        return cast("DependencySet | None", table.get_tuple_object(tuple_index, arity))

    def store_dependency_set(self, tuple_index: int, dependency_set: DependencySet) -> None:
        # Intern the (possibly transient) dependency set to its permanent,
        # interned representative and store the permanent in the slot. Storing
        # the interned permanent set -- rather than a transient union -- is what
        # gives the tableau fast ``is``/hash equality on dependency sets. The
        # interned set is immutable and reclaimed by Python's garbage collector;
        # there is no usage counting to register here.
        arity = self._extension_table.m_tuple_arity
        table = self._extension_table.m_tuple_table
        factory = self._extension_table.m_tableau.m_dependency_set_factory
        permanent = factory.get_permanent(dependency_set)
        table._data[tuple_index + arity] = permanent

    def forget_dependency_set(self, tuple_index: int) -> None:
        # No-op: the tuple slot is dropped wholesale when the tuple table is
        # truncated during backtracking, and the interned permanent set is
        # reclaimed by Python's garbage collector once nothing references it.
        pass


class DeterministicDependencySetManager(DependencySetManager):
    """Returns the empty dependency set (deterministic case)."""

    def __init__(self, extension_table: ExtensionTable) -> None:
        super().__init__(extension_table)

    def get_dependency_set(self, tuple_index: int) -> DependencySet | None:
        return self._extension_table.m_tableau.m_dependency_set_factory.empty_set

    def store_dependency_set(self, tuple_index: int, dependency_set: DependencySet) -> None:
        pass

    def forget_dependency_set(self, tuple_index: int) -> None:
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
        self._end_index = 0
        self._arity = extension_table.m_tuple_arity
        self._after_last = True

    def clear(self) -> None:
        self._current_index = -1
        self._after_last = True

    def open(self) -> None:
        # Restrict the scan to the requested view, mirroring Java's
        # UnindexedRetrieval.open(): each view maps to a [start, end) range over
        # the delta boundaries. Bounding the scan (rather than walking the whole
        # tuple table) is both faithful -- hyperresolution secondary atoms are
        # meant to range only over EXTENSION_THIS -- and the dominant perf win on
        # large tableaux, where scanning the full table per clause application is
        # quadratic.
        arity = self._arity
        slot_size = arity + 1
        ext = self._extension_table
        if self._view == "EXTENSION_THIS":
            start = 0
            end = ext._after_extension_this_tuple_index
        elif self._view == "EXTENSION_OLD":
            start = 0
            end = ext._after_extension_old_tuple_index
        elif self._view == "DELTA_OLD":
            start = ext._after_extension_old_tuple_index
            end = ext._after_extension_this_tuple_index
        else:  # TOTAL
            start = 0
            end = ext._after_delta_new_tuple_index
        self._current_index = start * slot_size
        self._end_index = end * slot_size
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
        limit = self._end_index if self._end_index < table.size else table.size
        while self._current_index < limit:
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
        self._current_index = limit
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


class _IndexedRetrieval(Retrieval):
    """Retrieval answered from a trie ``TupleIndex``.

    Mirrors the Java ``ExtensionTableWithTupleIndexes.IndexedRetrieval``: the
    bound prefix of the index's indexing sequence is resolved by a trie walk
    (``TupleIndexRetrieval``); the remaining bound positions, if any, are
    checked per candidate; the view restricts candidates to a tuple-index
    range.
    """

    def __init__(
        self,
        extension_table: ExtensionTable,
        tuple_index: Any,
        binding_positions: list[int],
        bindings_buffer: list[Any],
        tuple_buffer: list[Any],
        owns_buffers: bool,
        view: str,
    ) -> None:
        from hermit.tableau.tuple_index import TupleIndexRetrieval

        self._extension_table = extension_table
        self._binding_positions = binding_positions
        self._bindings_buffer = bindings_buffer
        self._tuple_buffer = tuple_buffer
        self._owns_buffers = owns_buffers
        self._view = view
        self._arity = extension_table.m_tuple_arity
        indexing_sequence = tuple_index.indexing_sequence
        selection_indices: list[int] = []
        for position in indexing_sequence:
            if binding_positions[position] != -1:
                selection_indices.append(binding_positions[position])
            else:
                break
        self._inner = TupleIndexRetrieval(
            tuple_index, bindings_buffer, selection_indices
        )
        number_of_bound = sum(
            1
            for position in range(self._arity)
            if binding_positions[position] != -1
        )
        self._check_tuple_selection = number_of_bound > len(selection_indices)
        self._current_index = -1
        self._first_index = 0
        self._end_index = 0
        self._after_last = True

    def clear(self) -> None:
        self._current_index = -1
        self._after_last = True
        if self._owns_buffers:
            for i in range(len(self._tuple_buffer)):
                self._tuple_buffer[i] = None
            for i in range(len(self._bindings_buffer)):
                self._bindings_buffer[i] = None

    def open(self) -> None:
        ext = self._extension_table
        slot_size = self._arity + 1
        if self._view == "EXTENSION_THIS":
            start = 0
            end = ext._after_extension_this_tuple_index
        elif self._view == "EXTENSION_OLD":
            start = 0
            end = ext._after_extension_old_tuple_index
        elif self._view == "DELTA_OLD":
            start = ext._after_extension_old_tuple_index
            end = ext._after_extension_this_tuple_index
        else:  # TOTAL
            start = 0
            end = ext._after_delta_new_tuple_index
        self._first_index = start * slot_size
        self._end_index = end * slot_size
        self._after_last = True
        self._inner.open()
        self._advance_to_valid()

    def _advance_to_valid(self) -> None:
        table = self._extension_table.m_tuple_table
        inner = self._inner
        first = self._first_index
        end = self._end_index
        while not inner.after_last():
            tuple_index = inner.get_current_tuple_index()
            if first <= tuple_index < end:
                table.retrieve_tuple(self._tuple_buffer, tuple_index)
                if self._is_tuple_valid():
                    self._current_index = tuple_index
                    self._after_last = False
                    return
            inner.next()
        self._after_last = True

    def _is_tuple_valid(self) -> bool:
        if self._check_tuple_selection:
            positions = self._binding_positions
            buffer = self._tuple_buffer
            bindings = self._bindings_buffer
            for index in range(self._arity):
                pos = positions[index]
                if pos != -1 and buffer[index] is not bindings[pos]:
                    return False
        return True

    def next(self) -> None:
        self._after_last = True
        self._inner.next()
        self._advance_to_valid()

    def after_last(self) -> bool:
        return self._after_last

    def get_tuple_buffer(self) -> list[Any]:
        return self._tuple_buffer

    def get_bindings_buffer(self) -> list[Any]:
        return self._bindings_buffer

    def get_dependency_set(self) -> DependencySet | None:
        return self._extension_table.m_dependency_set_manager.get_dependency_set(
            self._current_index
        )

    def is_core(self) -> bool:
        return self._extension_table.m_core_manager.is_core(self._current_index)

    def get_extension_table(self) -> ExtensionTable:
        return self._extension_table

    def get_current_tuple_index(self) -> int:
        return self._current_index

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
        # Trie indexes answering bound-prefix retrievals in sub-linear time;
        # values are flat element indexes into the tuple table.
        self.m_tuple_indexes: list[Any] = list(tuple_indexes) if tuple_indexes else []
        # For branching point tracking
        self._bp_tuple_index = 0
        self._bp_delta_index = 0
        self._bp_extension_index = 0
        # Membership hash index: maps a key built from the identities of a
        # tuple's logical columns to that tuple's flat element-index in the
        # tuple table. Mirrors Java's hash tuple-index and makes contains_tuple
        # /get_dependency_set/is_core O(1) instead of a linear scan over the
        # whole table. At most one live slot exists per key because add_tuple
        # rejects duplicates before inserting, so a single int value per key is
        # sufficient; backtrack() removes keys for every truncated tuple to keep
        # the index consistent with the table.
        self._membership_index: dict[tuple[int, ...], int] = {}

    def _tuple_key(self, tuple_data: list[Any]) -> tuple[int, ...]:
        """Build the membership-index key from a tuple's logical columns.

        Columns are compared by object identity throughout the tableau, so the
        key uses ``id()`` of each logical column (the dependency-set column is
        excluded). Model objects live for the tableau's lifetime, so their ids
        are stable while indexed.
        """
        arity = self.m_tuple_arity
        if arity == 2:
            return (id(tuple_data[0]), id(tuple_data[1]))
        if arity == 3:
            return (id(tuple_data[0]), id(tuple_data[1]), id(tuple_data[2]))
        return tuple(id(tuple_data[i]) for i in range(arity))

    def _key_at_index(self, element_index: int) -> tuple[int, ...]:
        """Build the membership-index key for the stored tuple at *element_index*."""
        table = self.m_tuple_table
        arity = self.m_tuple_arity
        return tuple(
            id(table.get_tuple_object(element_index, i)) for i in range(arity)
        )

    def clear(self) -> None:
        self.m_tuple_table.clear()
        if isinstance(self.m_core_manager, RealCoreManager):
            self.m_core_manager._core_flags.clear()
        self._membership_index.clear()
        for tuple_index in self.m_tuple_indexes:
            tuple_index.clear()
        self._after_extension_old_tuple_index = 0
        self._after_extension_this_tuple_index = 0
        self._after_delta_new_tuple_index = 0

    def branching_point_pushed(self) -> None:
        # Mirror Java ExtensionTable.branchingPointPushed: snapshot all three
        # delta boundaries for the current level into m_indices_by_branching_point
        # at offset level*3, without mutating any of them. Collapsing them here is
        # what jammed disjuncts asserted after a push into "extension-this" so their
        # clash never re-entered DELTA_OLD.
        level = self.m_tableau.get_current_branching_point_level()
        start = level * 3
        required_size = start + 3
        if required_size > len(self.m_indices_by_branching_point):
            new_size = len(self.m_indices_by_branching_point) * 3 // 2
            while required_size > new_size:
                new_size = new_size * 3 // 2
            new_indices = [0] * new_size
            new_indices[: len(self.m_indices_by_branching_point)] = (
                self.m_indices_by_branching_point
            )
            self.m_indices_by_branching_point = new_indices
        self.m_indices_by_branching_point[start] = self._after_extension_old_tuple_index
        self.m_indices_by_branching_point[start + 1] = self._after_extension_this_tuple_index
        self.m_indices_by_branching_point[start + 2] = self._after_delta_new_tuple_index

    def backtrack(self) -> None:
        # Mirror Java ExtensionTable.backtrack: restore all three boundaries from
        # the snapshot and truncate the tuple table to the saved afterDeltaNew,
        # running postRemove + forgetDependencySet for every dropped tuple.
        level = self.m_tableau.get_current_branching_point_level()
        start = level * 3
        slot_size = self.m_tuple_arity + 1
        new_after_delta_new = self.m_indices_by_branching_point[start + 2]
        table = self.m_tuple_table
        arity = self.m_tuple_arity
        for tuple_index in range(self._after_delta_new_tuple_index - 1, new_after_delta_new - 1, -1):
            element_index = tuple_index * slot_size
            key = self._key_at_index(element_index)
            existing = self._membership_index.get(key)
            if existing == element_index:
                del self._membership_index[key]
            if self.m_tuple_indexes:
                removed_tuple = [
                    table.get_tuple_object(element_index, i) for i in range(arity)
                ]
                for trie_index in self.m_tuple_indexes:
                    trie_index.remove_tuple(removed_tuple)
            self.m_dependency_set_manager.forget_dependency_set(element_index)
            self._post_remove(element_index)
        self.m_tuple_table.truncate(new_after_delta_new * slot_size)
        self._after_extension_old_tuple_index = self.m_indices_by_branching_point[start]
        self._after_extension_this_tuple_index = self.m_indices_by_branching_point[start + 1]
        self._after_delta_new_tuple_index = new_after_delta_new

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
        self._membership_index[self._tuple_key(tuple_data)] = tuple_index
        for trie_index in self.m_tuple_indexes:
            trie_index.add_tuple(tuple_data, tuple_index)
        self.m_dependency_set_manager.store_dependency_set(tuple_index, dependency_set)
        if is_core:
            self.m_core_manager.mark_core(tuple_index, True)
        # Advance the delta-new boundary to the new free index, mirroring Java
        # ExtensionTable.addTuple (which sets m_afterDeltaNewTupleIndex =
        # m_tupleTable.getFirstFreeTupleIndex()). A freshly added tuple must sit
        # inside DELTA_NEW = [afterExtensionThis, afterDeltaNew) so the next
        # propagate_delta_new reports the range as non-empty and the driver loop
        # applies the DL clauses to it. Without this, a disjunct asserted after a
        # branching-point push is never re-examined and its clash never fires.
        self._after_delta_new_tuple_index = self.m_tuple_table.size // (
            self.m_tuple_arity + 1
        )

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

    def _post_remove(self, element_index: int) -> None:
        """Undo the side effects of a tuple add (mirrors Java ExtensionTable.postRemove).

        Decrements the per-node assertion counters, drops the existential from the
        node's unprocessed queue, and notifies the expansion strategy that the
        assertion was removed. *element_index* is the flat array index of the tuple.
        """
        from hermit.model import (
            AtomicConcept,
            AtomicNegationConcept,
            AtomicRole,
            DataRange,
            DescriptionGraph,
            ExistentialConcept,
            NegatedAtomicRole,
        )

        table = self.m_tuple_table
        dl_predicate = table.get_tuple_object(element_index, 0)
        is_core = self.m_core_manager.is_core(element_index)
        strat = (
            self.m_tableau.m_existential_expansion_strategy
            if self.m_tableau is not None
            else None
        )
        if isinstance(dl_predicate, AtomicConcept):
            node = table.get_tuple_object(element_index, 1)
            if node is not None:
                if strat is not None:
                    strat.assertion_removed_concept(dl_predicate, node, is_core)
                node.m_number_of_positive_atomic_concepts -= 1
        elif isinstance(dl_predicate, ExistentialConcept):
            node = table.get_tuple_object(element_index, 1)
            if node is not None:
                if strat is not None:
                    strat.assertion_removed_concept(dl_predicate, node, is_core)
                node._remove_from_unprocessed_existentials(dl_predicate)
        elif isinstance(dl_predicate, AtomicNegationConcept):
            # Mirror postAdd: only the counter is touched here; the expansion
            # strategy is not notified for negated atomic concepts.
            node = table.get_tuple_object(element_index, 1)
            if node is not None:
                node.m_number_of_negated_atomic_concepts -= 1
        elif isinstance(dl_predicate, DataRange):
            node = table.get_tuple_object(element_index, 1)
            if node is not None and strat is not None:
                strat.assertion_removed_data_range(dl_predicate, node, is_core)
        elif isinstance(dl_predicate, AtomicRole):
            node1 = table.get_tuple_object(element_index, 1)
            node2 = table.get_tuple_object(element_index, 2)
            if strat is not None:
                strat.assertion_removed_atomic_role(dl_predicate, node1, node2, is_core)
        elif isinstance(dl_predicate, NegatedAtomicRole):
            node = table.get_tuple_object(element_index, 1)
            if node is not None:
                node.m_number_of_negated_role_assertions -= 1
        elif isinstance(dl_predicate, DescriptionGraph):
            tuple_buffer: list[Any] = [None] * (self.m_tuple_arity + 1)
            table.retrieve_tuple(tuple_buffer, element_index)
            self.m_tableau.m_description_graph_manager.description_graph_tuple_removed(
                element_index, tuple_buffer
            )

    def contains_tuple(self, tuple_data: list[Any]) -> bool:
        return self._tuple_key(tuple_data) in self._membership_index

    def get_dependency_set(self, tuple_data: list[Any]) -> DependencySet | None:
        idx = self._membership_index.get(self._tuple_key(tuple_data))
        if idx is None:
            return None
        return self.m_dependency_set_manager.get_dependency_set(idx)

    def is_core(self, tuple_data: list[Any]) -> bool:
        idx = self._membership_index.get(self._tuple_key(tuple_data))
        if idx is None:
            return False
        return self.m_core_manager.is_core(idx)

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
            # Simple retrieval: (bound_mask, view). Mirror the Java overload by
            # translating the mask into binding positions with owned buffers so
            # the trie indexes answer these retrievals as well.
            v = view_or_bindings if isinstance(view_or_bindings, str) else view
            bound_mask = cast("list[bool]", bound_mask_or_positions)
            binding_positions = [
                i if bound else -1 for i, bound in enumerate(bound_mask)
            ] + [-1]
            return self.create_retrieval_full(
                binding_positions,
                [None] * len(bound_mask),
                [None] * (len(bound_mask) + 1),
                True,
                v,
            )
        else:
            # Full retrieval: (binding_positions, bindings_buffer, tuple_buffer, owns_buffers, view)
            bindings = view_or_bindings if isinstance(view_or_bindings, list) else []
            return self.create_retrieval_full(
                cast("list[int]", bound_mask_or_positions), bindings,
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
        # Pick the trie index whose indexing-sequence prefix covers the most
        # bound positions, as in the Java createRetrieval; fall back to the
        # scanning retrieval when no index helps.
        selected: Any = None
        bound_prefix_in_selected = 0
        for trie_index in self.m_tuple_indexes:
            bound_prefix = 0
            for position in trie_index.indexing_sequence:
                if binding_positions[position] != -1:
                    bound_prefix += 1
                else:
                    break
            if bound_prefix > bound_prefix_in_selected:
                selected = trie_index
                bound_prefix_in_selected = bound_prefix
        if selected is None:
            return _FullRetrieval(
                self, binding_positions, bindings_buffer, tuple_buffer,
                owns_buffers, view
            )
        return _IndexedRetrieval(
            self, selected, binding_positions, bindings_buffer, tuple_buffer,
            owns_buffers, view
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

        from hermit.tableau.tuple_index import TupleIndex

        # Binary extension table (arity 2: concept assertions)
        self.m_binary_extension_table = ExtensionTableWithTupleIndexes(
            tableau, 2, not tableau.is_deterministic(),
            [TupleIndex([1, 0]), TupleIndex([0, 1])],
        )
        self.m_extension_tables_by_arity[2] = self.m_binary_extension_table

        # Ternary extension table (arity 3: role assertions)
        self.m_ternary_extension_table = ExtensionTableWithTupleIndexes(
            tableau, 3, not tableau.is_deterministic(),
            [TupleIndex([0, 1, 2]), TupleIndex([1, 2, 0]), TupleIndex([2, 0, 1])],
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
