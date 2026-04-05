"""Clash manager -- detects contradictory assertions in the tableau."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hermit.monitor import TableauMonitor
    from hermit.tableau.dependency_set import DependencySet
    from hermit.tableau.extension_manager import ExtensionTable, ExtensionManager


class ClashManager:
    """Detects clashes as soon as contradictory assertions are added.

    The clash manager is notified by extension tables whenever a new tuple
    is added, and checks whether that tuple conflicts with an existing one
    (e.g., both *C(x)* and *~C(x)* are asserted).

    Args:
        tableau: The owning tableau.
    """

    __slots__ = (
        "m_extension_manager",
        "m_ternary_extension_table_search_01_bound",
        "m_tableau_monitor",
        "m_binary_auxiliary_tuple",
        "m_ternary_auxiliary_tuple",
        "m_binary_union_dependency_set",
    )

    # Not-RDFS-literal, used for clash detection
    _NOT_RDFS_LITERAL: Any = None  # set at import time via _get_not_rdfs_literal

    def __init__(self, tableau: Any) -> None:
        self.m_extension_manager: ExtensionManager = tableau.m_extension_manager
        self.m_ternary_extension_table_search_01_bound = (
            self.m_extension_manager.m_ternary_extension_table.create_retrieval(
                [True, True, False], "TOTAL"
            )
        )
        self.m_tableau_monitor: TableauMonitor | None = tableau.m_tableau_monitor
        self.m_binary_auxiliary_tuple: list[Any] = [None, None]
        self.m_ternary_auxiliary_tuple: list[Any] = [None, None, None]
        self.m_binary_union_dependency_set: Any = _UnionDependencySet(2)

    def clear(self) -> None:
        """Reset all auxiliary buffers."""
        self.m_ternary_extension_table_search_01_bound.clear()
        self.m_binary_auxiliary_tuple[0] = None
        self.m_binary_auxiliary_tuple[1] = None
        self.m_ternary_auxiliary_tuple[0] = None
        self.m_ternary_auxiliary_tuple[1] = None
        self.m_ternary_auxiliary_tuple[2] = None
        self.m_binary_union_dependency_set.m_dependency_sets[0] = None
        self.m_binary_union_dependency_set.m_dependency_sets[1] = None

    def tuple_added(
        self,
        extension_table: ExtensionTable,
        tuple_data: list[Any],
        dependency_set: DependencySet,
        is_core: bool,
    ) -> None:
        """Called by an extension table when a tuple has been added.

        This method checks whether the new tuple clashes with an existing one.

        Args:
            extension_table: The table that received the tuple.
            tuple_data: The newly added tuple.
            dependency_set: The dependency set of the new tuple.
            is_core: Whether the tuple is a core assertion.
        """
        from hermit.model import (
            AtomicConcept,
            AtomicNegationConcept,
            AtomicNegationDataRange,
            AtomicRole,
            Inequality,
            NegatedAtomicRole,
        )
        from hermit.datatypes import InternalDatatype
        from hermit.model import LiteralConcept, LiteralDataRange

        dl_predicate_object = tuple_data[0]
        node0 = tuple_data[1]

        # --- Direct clashes ---
        nothing_clash = (
            AtomicConcept.NOTHING is dl_predicate_object
            or self._get_not_rdfs_literal() is dl_predicate_object
            or (Inequality.INSTANCE is dl_predicate_object and tuple_data[1] is tuple_data[2])
        )
        if nothing_clash:
            if self.m_tableau_monitor is not None:
                self.m_tableau_monitor.clash_detection_started(tuple_data)
            self.m_extension_manager.set_clash(dependency_set)
            if self.m_tableau_monitor is not None:
                self.m_tableau_monitor.clash_detection_finished(tuple_data)
            return

        # --- Complementary concept / data-range clashes ---

        is_datatype = isinstance(dl_predicate_object, InternalDatatype)
        is_negated_datatype = (
            isinstance(dl_predicate_object, AtomicNegationDataRange)
            and isinstance(
                dl_predicate_object.get_negated_data_range(), InternalDatatype
            )
        )
        is_atomic_concept_with_negations = (
            isinstance(dl_predicate_object, AtomicConcept)
            and node0._number_of_negated_atomic_concepts > 0
        )
        is_negated_concept_with_positives = (
            isinstance(dl_predicate_object, AtomicNegationConcept)
            and node0._number_of_positive_atomic_concepts > 0
        )

        if (
            is_datatype
            or is_negated_datatype
            or is_atomic_concept_with_negations
            or is_negated_concept_with_positives
        ):
            negation = (
                dl_predicate_object.get_negation()
                if isinstance(dl_predicate_object, (LiteralDataRange, LiteralConcept))
                else None
            )
            if negation is not None:
                self.m_binary_auxiliary_tuple[0] = negation
                self.m_binary_auxiliary_tuple[1] = node0
                if extension_table.contains_tuple(self.m_binary_auxiliary_tuple):
                    self.m_binary_union_dependency_set.m_dependency_sets[0] = (
                        dependency_set
                    )
                    self.m_binary_union_dependency_set.m_dependency_sets[1] = (
                        extension_table.get_dependency_set(self.m_binary_auxiliary_tuple)
                    )
                    if self.m_tableau_monitor is not None:
                        self.m_tableau_monitor.clash_detection_started(
                            tuple_data, self.m_binary_auxiliary_tuple
                        )
                    self.m_extension_manager.set_clash(
                        self.m_binary_union_dependency_set
                    )
                    if self.m_tableau_monitor is not None:
                        self.m_tableau_monitor.clash_detection_finished(
                            tuple_data, self.m_binary_auxiliary_tuple
                        )
            return

        # --- Role / negated-role clashes ---
        is_role_with_negations = (
            isinstance(dl_predicate_object, AtomicRole)
            and node0._number_of_negated_role_assertions > 0
        )
        is_negated_role = isinstance(dl_predicate_object, NegatedAtomicRole)

        if is_role_with_negations or is_negated_role:
            search_predicate: Any
            if isinstance(dl_predicate_object, AtomicRole):
                search_predicate = NegatedAtomicRole.create(dl_predicate_object)
            else:
                search_predicate = dl_predicate_object.get_negated_atomic_role()

            self.m_ternary_auxiliary_tuple[0] = search_predicate
            self.m_ternary_auxiliary_tuple[1] = node0
            self.m_ternary_auxiliary_tuple[2] = tuple_data[2]

            if extension_table.contains_tuple(self.m_ternary_auxiliary_tuple):
                self.m_binary_union_dependency_set.m_dependency_sets[0] = (
                    dependency_set
                )
                self.m_binary_union_dependency_set.m_dependency_sets[1] = (
                    extension_table.get_dependency_set(self.m_ternary_auxiliary_tuple)
                )
                if self.m_tableau_monitor is not None:
                    self.m_tableau_monitor.clash_detection_started(
                        tuple_data, self.m_ternary_auxiliary_tuple
                    )
                self.m_extension_manager.set_clash(self.m_binary_union_dependency_set)
                if self.m_tableau_monitor is not None:
                    self.m_tableau_monitor.clash_detection_finished(
                        tuple_data, self.m_ternary_auxiliary_tuple
                    )
            elif not tuple_data[2].node_type.is_abstract:
                # If the second node is concrete, generate inequalities
                self.m_ternary_auxiliary_tuple[0] = Inequality.INSTANCE
                self.m_ternary_auxiliary_tuple[1] = tuple_data[2]
                self.m_binary_union_dependency_set.m_dependency_sets[0] = (
                    dependency_set
                )
                retrieval = self.m_ternary_extension_table_search_01_bound
                retrieval.get_bindings_buffer()[0] = search_predicate
                retrieval.get_bindings_buffer()[1] = tuple_data[1]
                retrieval.open()
                tuple_buffer = retrieval.get_tuple_buffer()
                while not retrieval.after_last():
                    assert not tuple_buffer[2].node_type.is_abstract
                    self.m_ternary_auxiliary_tuple[2] = tuple_buffer[2]
                    self.m_binary_union_dependency_set.m_dependency_sets[1] = (
                        retrieval.get_dependency_set()
                    )
                    if self.m_tableau_monitor is not None:
                        self.m_tableau_monitor.clash_detection_started(
                            tuple_data, tuple_buffer
                        )
                    # Reentrant call directly to ternary table
                    self.m_extension_manager.m_ternary_extension_table.add_tuple(
                        self.m_ternary_auxiliary_tuple,
                        self.m_binary_union_dependency_set,
                        True,
                    )
                    if self.m_tableau_monitor is not None:
                        self.m_tableau_monitor.clash_detection_finished(
                            tuple_data, tuple_buffer
                        )
                    retrieval.next()

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    @classmethod
    def _get_not_rdfs_literal(cls) -> Any:
        """Lazily compute the negation of RDFS_LITERAL."""
        if cls._NOT_RDFS_LITERAL is None:
            from hermit.datatypes import InternalDatatype

            cls._NOT_RDFS_LITERAL = InternalDatatype.RDFS_LITERAL.get_negation()
        return cls._NOT_RDFS_LITERAL


class _UnionDependencySet:
    """Minimal union-of-two dependency sets, used inline by ClashManager."""

    __slots__ = ("m_dependency_sets",)

    def __init__(self, n: int) -> None:
        self.m_dependency_sets: list[Any] = [None] * n

    def contains_branching_point(self, branching_point: int) -> bool:
        for ds in self.m_dependency_sets:
            if ds is not None and ds.contains_branching_point(branching_point):
                return True
        return False

    def is_empty(self) -> bool:
        for ds in self.m_dependency_sets:
            if ds is not None and not ds.is_empty():
                return False
        return True

    def get_maximum_branching_point(self) -> int:
        maximum = -1
        for ds in self.m_dependency_sets:
            if ds is not None:
                bp = ds.get_maximum_branching_point()
                if bp > maximum:
                    maximum = bp
        return maximum
