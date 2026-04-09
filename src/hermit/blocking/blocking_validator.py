"""Blocking validator for validated blocking.

Faithful port of ``org.semanticweb.HermiT.blocking.BlockingValidator`` from
the Java HermiT OWL reasoner.

Classes
-------
BlockingValidator
    Checks whether DL clauses are applicable given the current state of the
    extensions, used to validate that a block is sound.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hermit.model import (
        AnnotatedEquality,
        AtLeastConcept,
        AtomicConcept,
        AtomicRole,
        DLClause,
        Equality,
        Variable,
    )
    from hermit.tableau import ExtensionManager, Node, Tableau

from abc import ABC, abstractmethod

from hermit.model import (
    AtLeastConcept,
    AtomicConcept,
    AtomicRole,
    Variable,
)
from .validated_single_direct_blocking_checker import ValidatedBlockingObject


class _ArgumentType(Enum):
    XVAR = 0
    YVAR = 1
    ZVAR = 2


class _YConstraint:
    __slots__ = ("m_y_concepts", "m_x2y_roles", "m_y2x_roles")

    def __init__(
        self,
        y_concepts: list[AtomicConcept],
        x2y_roles: list[AtomicRole],
        y2x_roles: list[AtomicRole],
    ) -> None:
        self.m_y_concepts = y_concepts
        self.m_x2y_roles = x2y_roles
        self.m_y2x_roles = y2x_roles

    def is_satisfied_explicitly(self, extension_manager: ExtensionManager, node_x: Node, node_y: Node) -> bool:
        for role in self.m_x2y_roles:
            if not extension_manager.contains_assertion(role, node_x, node_y):
                return False
        for role in self.m_y2x_roles:
            if not extension_manager.contains_assertion(role, node_y, node_x):
                return False
        for concept in self.m_y_concepts:
            if not extension_manager.contains_assertion(concept, node_y):
                return False
        return True

    def is_satisfied_via_mirroring_y(self, extension_manager: ExtensionManager, node_x: Node, node_y: Node) -> bool:
        for role in self.m_x2y_roles:
            if not extension_manager.contains_assertion(role, node_x, node_y):
                return False
        for role in self.m_y2x_roles:
            if not extension_manager.contains_assertion(role, node_y, node_x):
                return False
        node_y_mirror: Node
        if node_y.is_blocked() and not node_y.get_blocking_object().block_violates_parent_constraints():  # type: ignore[union-attr]
            node_y_mirror = node_y.get_blocker()  # type: ignore[union-attr]
        else:
            node_y_mirror = node_y
        for concept in self.m_y_concepts:
            if not extension_manager.contains_assertion(concept, node_y_mirror):
                return False
        return True


class _ConsequenceAtom(ABC):
    """Abstract base class for consequence atoms."""

    @abstractmethod
    def is_satisfied(self, extension_manager: ExtensionManager, dl_clause_info: DLClauseInfo, blocked_x: Node) -> bool: ...


class _SimpleConsequenceAtom(_ConsequenceAtom):
    __slots__ = ("m_assertion_buffer", "m_argument_types", "m_argument_indexes", "m_dl_predicate")

    def __init__(
        self,
        dl_predicate: Any,
        argument_types: list[_ArgumentType],
        argument_indexes: list[int],
    ) -> None:
        self.m_dl_predicate = dl_predicate
        self.m_assertion_buffer: list[Any] = [None] * (len(argument_indexes) + 1)
        self.m_assertion_buffer[0] = dl_predicate
        self.m_argument_types = argument_types
        self.m_argument_indexes = argument_indexes

    def is_satisfied(self, extension_manager: ExtensionManager, dl_clause_info: DLClauseInfo, blocked_x: Node) -> bool:
        for arg_idx in range(len(self.m_argument_indexes) - 1, -1, -1):
            arg_type = self.m_argument_types[arg_idx]
            if arg_type == _ArgumentType.XVAR:
                self.m_assertion_buffer[arg_idx + 1] = dl_clause_info.m_x_node
            elif arg_type == _ArgumentType.YVAR:
                self.m_assertion_buffer[arg_idx + 1] = dl_clause_info.m_y_nodes[self.m_argument_indexes[arg_idx]]
            elif arg_type == _ArgumentType.ZVAR:
                self.m_assertion_buffer[arg_idx + 1] = dl_clause_info.m_z_nodes[self.m_argument_indexes[arg_idx]]

        if isinstance(self.m_dl_predicate, AnnotatedEquality):
            return self.m_assertion_buffer[1] is self.m_assertion_buffer[2]
        return extension_manager.contains_tuple(tuple(self.m_assertion_buffer))


class _X2YOrY2XConsequenceAtom(_ConsequenceAtom):
    __slots__ = ("m_atomic_role", "m_y_argument_index", "m_is_x2y")

    def __init__(self, atomic_role: AtomicRole, y_argument_index: int, is_x2y: bool) -> None:
        self.m_atomic_role = atomic_role
        self.m_y_argument_index = y_argument_index
        self.m_is_x2y = is_x2y

    def is_satisfied(self, extension_manager: ExtensionManager, dl_clause_info: DLClauseInfo, blocked_x: Node) -> bool:
        node_y = dl_clause_info.m_y_nodes[self.m_y_argument_index]
        if node_y is blocked_x.parent:
            node_x_real = blocked_x
        else:
            node_x_real = dl_clause_info.m_x_node
        if self.m_is_x2y:
            return extension_manager.contains_assertion(self.m_atomic_role, node_x_real, node_y)
        return extension_manager.contains_assertion(self.m_atomic_role, node_y, node_x_real)


class _MirroredYConsequenceAtom(_ConsequenceAtom):
    __slots__ = ("m_atomic_concept", "m_y_argument_index")

    def __init__(self, atomic_concept: AtomicConcept, y_argument_index: int) -> None:
        self.m_atomic_concept = atomic_concept
        self.m_y_argument_index = y_argument_index

    def is_satisfied(self, extension_manager: ExtensionManager, dl_clause_info: DLClauseInfo, blocked_x: Node) -> bool:
        node_y = dl_clause_info.m_y_nodes[self.m_y_argument_index]
        node_y_mirror: Node
        if node_y.is_blocked():
            node_y_mirror = node_y.get_blocker()
        else:
            node_y_mirror = node_y
        return extension_manager.contains_assertion(self.m_atomic_concept, node_y_mirror)

    def is_satisfied_non_mirrored(self, extension_manager: ExtensionManager, dl_clause_info: DLClauseInfo) -> bool:
        return extension_manager.contains_assertion(
            self.m_atomic_concept, dl_clause_info.m_y_nodes[self.m_y_argument_index]
        )


class DLClauseInfo:
    """Preprocessed information about a DL clause for validation."""

    __slots__ = (
        "m_x_concepts",
        "m_x2x_roles",
        "m_y_constraints",
        "m_z_concepts",
        "m_x2y_retrievals",
        "m_x2y_roles",
        "m_y2x_retrievals",
        "m_y2x_roles",
        "m_z_retrievals",
        "m_consequences_for_blocked_x",
        "m_consequences_for_nonblocked_x",
        "m_dl_clause",
        "m_x_node",
        "m_y_nodes",
        "m_y_variables",
        "m_z_nodes",
        "m_z_variables",
    )

    def __init__(self, dl_clause: DLClause, extension_manager: ExtensionManager) -> None:
        self.m_dl_clause = dl_clause

        x_variable = Variable.create("X")  # type: ignore[name-defined]

        x_concepts: set[AtomicConcept] = set()
        x2x_roles: set[AtomicRole] = set()
        ys: set[Variable] = set()  # type: ignore[valid-type]
        y2concepts: dict[Variable, set[AtomicConcept]] = {}  # type: ignore[valid-type]
        z2concepts: dict[Variable, set[AtomicConcept]] = {}  # type: ignore[valid-type]
        x2y_roles: dict[Variable, set[AtomicRole]] = {}  # type: ignore[valid-type]
        y2x_roles: dict[Variable, set[AtomicRole]] = {}  # type: ignore[valid-type]

        for i in range(dl_clause.body_length()):
            atom = dl_clause.body_atom(i)
            predicate = atom.predicate
            var1 = atom.argument_variable(0)

            if isinstance(predicate, AtomicConcept):
                if var1 == x_variable:
                    x_concepts.add(predicate)
                elif var1.get_name().startswith("Y"):
                    ys.add(var1)
                    if var1 not in y2concepts:
                        y2concepts[var1] = set()
                    y2concepts[var1].add(predicate)
                elif var1.get_name().startswith("Z"):
                    if var1 not in z2concepts:
                        z2concepts[var1] = set()
                    z2concepts[var1].add(predicate)
            elif isinstance(predicate, AtomicRole):
                var2 = atom.argument_variable(1)
                if var1 == x_variable:
                    if var2 == x_variable:
                        x2x_roles.add(predicate)
                    elif var2.get_name().startswith("Y"):
                        ys.add(var2)
                        if var2 not in x2y_roles:
                            x2y_roles[var2] = set()
                        x2y_roles[var2].add(predicate)
                elif var2 == x_variable:
                    if var1.get_name().startswith("Y"):
                        ys.add(var1)
                        if var1 not in y2x_roles:
                            y2x_roles[var1] = set()
                        y2x_roles[var1].add(predicate)

        self.m_x_node: Node | None = None
        self.m_x_concepts = list(x_concepts)
        self.m_x2x_roles = list(x2x_roles)

        self.m_y_variables = list(ys)
        self.m_y_nodes: list[Node | None] = [None] * len(self.m_y_variables)
        self.m_y_constraints: list[_YConstraint] = []
        num_xy_roles = 0
        x2y_retrievals: list[Any] = []
        x2y_role_list: list[AtomicRole] = []
        y2x_retrievals: list[Any] = []
        y2x_role_list: list[AtomicRole] = []

        for y_var in self.m_y_variables:
            y_concepts_list = list(y2concepts.get(y_var, set()))
            xy_roles = x2y_roles.get(y_var)
            yx_roles = y2x_roles.get(y_var)

            if xy_roles is not None:
                x2y_retrievals.append(
                    extension_manager.get_ternary_extension_table().create_retrieval([True, True, False], "TOTAL")
                )
                x2y_role_list.append(next(iter(xy_roles)))
                num_xy_roles += 1
            if yx_roles is not None:
                y2x_retrievals.append(
                    extension_manager.get_ternary_extension_table().create_retrieval([True, False, True], "TOTAL")
                )
                y2x_role_list.append(next(iter(yx_roles)))

            self.m_y_constraints.append(
                _YConstraint(y_concepts_list, list(xy_roles) if xy_roles else [], list(yx_roles) if yx_roles else [])
            )

        self.m_x2y_retrievals = x2y_retrievals
        self.m_x2y_roles = x2y_role_list
        self.m_y2x_retrievals = y2x_retrievals
        self.m_y2x_roles = y2x_role_list

        self.m_z_variables = list(z2concepts.keys())
        self.m_z_nodes: list[Node | None] = [None] * len(self.m_z_variables)
        self.m_z_concepts: list[list[AtomicConcept]] = [
            list(z2concepts[zv]) for zv in self.m_z_variables
        ]
        self.m_z_retrievals = [
            extension_manager.get_binary_extension_table().create_retrieval([True, False], "TOTAL")
            for _ in range(len(self.m_z_variables))
        ]

        self.m_consequences_for_blocked_x: list[_ConsequenceAtom] = [None] * dl_clause.head_length()  # type: ignore[list-item]
        self.m_consequences_for_nonblocked_x: list[_ConsequenceAtom] = [None] * dl_clause.head_length()  # type: ignore[list-item]

        for i in range(dl_clause.head_length()):
            atom = dl_clause.head_atom(i)
            predicate = atom.predicate
            var1 = atom.argument_variable(0)
            var2 = atom.argument_variable(1) if predicate.arity() == 2 else None

            if isinstance(predicate, AtomicConcept):
                arg_type = _ArgumentType.YVAR
                arg_index = self._get_index_for(self.m_y_variables, var1)
                if arg_index == -1:
                    assert var1 == x_variable
                    arg_index = 0
                    arg_type = _ArgumentType.XVAR
                self.m_consequences_for_blocked_x[i] = _SimpleConsequenceAtom(
                    predicate, [arg_type], [arg_index]
                )
                if arg_type == _ArgumentType.XVAR:
                    self.m_consequences_for_nonblocked_x[i] = self.m_consequences_for_blocked_x[i]
                else:
                    self.m_consequences_for_nonblocked_x[i] = _MirroredYConsequenceAtom(
                        predicate, arg_index
                    )
            elif hasattr(predicate, "number"):  # AtLeastConcept
                assert var1 == x_variable
                self.m_consequences_for_blocked_x[i] = _SimpleConsequenceAtom(
                    predicate, [_ArgumentType.XVAR], [0]
                )
                self.m_consequences_for_nonblocked_x[i] = self.m_consequences_for_blocked_x[i]
            elif predicate == Equality.INSTANCE:
                if var1 == x_variable or var2 == x_variable:
                    if var2 == x_variable:
                        var1, var2 = var2, var1
                    assert var2.get_name().startswith("Z")
                    var2_index = self._get_index_for(self.m_z_variables, var2)
                    self.m_consequences_for_blocked_x[i] = _SimpleConsequenceAtom(
                        predicate, [_ArgumentType.XVAR, _ArgumentType.ZVAR], [0, var2_index]
                    )
                    self.m_consequences_for_nonblocked_x[i] = self.m_consequences_for_blocked_x[i]
                elif var1.get_name().startswith("Z") or (var2 and var2.get_name().startswith("Z")):
                    if var2 and var2.get_name().startswith("Y"):
                        var1, var2 = var2, var1
                    assert var2.get_name().startswith("Z")
                    var2_index = self._get_index_for(self.m_z_variables, var2)
                    var1_index = self._get_index_for(self.m_y_variables, var1)
                    self.m_consequences_for_blocked_x[i] = _SimpleConsequenceAtom(
                        predicate, [_ArgumentType.YVAR, _ArgumentType.ZVAR], [var1_index, var2_index]
                    )
                    self.m_consequences_for_nonblocked_x[i] = self.m_consequences_for_blocked_x[i]
                elif var1.get_name().startswith("Y") and var2 and var2.get_name().startswith("Y"):
                    var1_index = self._get_index_for(self.m_y_variables, var1)
                    var2_index = self._get_index_for(self.m_y_variables, var2)
                    self.m_consequences_for_blocked_x[i] = _SimpleConsequenceAtom(
                        predicate, [_ArgumentType.YVAR, _ArgumentType.YVAR], [var1_index, var2_index]
                    )
                    self.m_consequences_for_nonblocked_x[i] = self.m_consequences_for_blocked_x[i]
            elif isinstance(predicate, AnnotatedEquality):
                var1 = atom.argument_variable(0)
                var2 = atom.argument_variable(1)
                var1_index = self._get_index_for(self.m_y_variables, var1)
                var2_index = self._get_index_for(self.m_y_variables, var2)
                self.m_consequences_for_blocked_x[i] = _SimpleConsequenceAtom(
                    predicate,
                    [_ArgumentType.YVAR, _ArgumentType.YVAR, _ArgumentType.XVAR],
                    [var1_index, var2_index, 0],
                )
                self.m_consequences_for_nonblocked_x[i] = self.m_consequences_for_blocked_x[i]
            elif isinstance(predicate, AtomicRole):
                if var1 == x_variable and var2 == x_variable:
                    self.m_consequences_for_blocked_x[i] = _SimpleConsequenceAtom(
                        predicate, [_ArgumentType.XVAR, _ArgumentType.XVAR], [0, 0]
                    )
                    self.m_consequences_for_nonblocked_x[i] = self.m_consequences_for_blocked_x[i]
                else:
                    assert var1 == x_variable or var2 == x_variable
                    arg_index = -1
                    if var1 == x_variable:
                        arg_index = self._get_index_for(self.m_y_variables, var2)
                        if arg_index == -1:
                            arg_index = self._get_index_for(self.m_z_variables, var2)
                            assert arg_index > -1
                            self.m_consequences_for_blocked_x[i] = _SimpleConsequenceAtom(
                                predicate, [_ArgumentType.XVAR, _ArgumentType.ZVAR], [0, arg_index]
                            )
                            self.m_consequences_for_nonblocked_x[i] = self.m_consequences_for_blocked_x[i]
                        else:
                            self.m_consequences_for_blocked_x[i] = _X2YOrY2XConsequenceAtom(
                                predicate, arg_index, True
                            )
                            self.m_consequences_for_nonblocked_x[i] = _SimpleConsequenceAtom(
                                predicate, [_ArgumentType.XVAR, _ArgumentType.YVAR], [0, arg_index]
                            )
                    else:
                        arg_index = self._get_index_for(self.m_y_variables, var1)
                        if arg_index == -1:
                            arg_index = self._get_index_for(self.m_z_variables, var1)
                            assert arg_index > -1
                            self.m_consequences_for_blocked_x[i] = _SimpleConsequenceAtom(
                                predicate, [_ArgumentType.ZVAR, _ArgumentType.XVAR], [arg_index, 0]
                            )
                            self.m_consequences_for_nonblocked_x[i] = self.m_consequences_for_blocked_x[i]
                        else:
                            self.m_consequences_for_blocked_x[i] = _X2YOrY2XConsequenceAtom(
                                predicate, arg_index, False
                            )
                            self.m_consequences_for_nonblocked_x[i] = _SimpleConsequenceAtom(
                                predicate, [_ArgumentType.YVAR, _ArgumentType.XVAR], [arg_index, 0]
                            )

    def clear(self) -> None:
        for retrieval in self.m_x2y_retrievals:
            if hasattr(retrieval, "clear"):
                retrieval.clear()
        for retrieval in self.m_y2x_retrievals:
            if hasattr(retrieval, "clear"):
                retrieval.clear()
        for retrieval in self.m_z_retrievals:
            if hasattr(retrieval, "clear"):
                retrieval.clear()

    def _get_index_for(self, variables: list[Variable], variable: Variable) -> int:  # type: ignore[valid-type]
        for index, var in enumerate(variables):
            if var == variable:
                return index
        return -1


class BlockingValidator:
    """Validates that blocks are sound with respect to DL clause applicability.

    Checks whether the rules from some set are applicable given the current
    state of the extensions.
    """

    __slots__ = (
        "m_extension_manager",
        "m_binary_retrieval_1_bound",
        "m_ternary_retrieval_01_bound",
        "m_ternary_retrieval_02_bound",
        "m_ternary_retrieval_1_bound",
        "m_ternary_retrieval_2_bound",
        "m_dl_clause_infos",
        "m_dl_clause_infos_by_x_concepts",
        "m_dl_clause_infos_without_x_concepts",
        "in_valid_atleast_for_blocked_parent",
        "in_valid_clauses_for_blocked_parent",
        "in_valid_atleast_for_blocker",
        "in_valid_clauses_for_blocker",
    )

    def __init__(self, tableau: Tableau, dl_clauses: set[DLClause]) -> None:
        self.m_extension_manager = tableau.extension_manager
        self.m_binary_retrieval_1_bound = self.m_extension_manager.get_binary_extension_table().create_retrieval(
            [False, True], "TOTAL"
        )
        self.m_ternary_retrieval_01_bound = self.m_extension_manager.get_ternary_extension_table().create_retrieval(
            [True, True, False], "TOTAL"
        )
        self.m_ternary_retrieval_02_bound = self.m_extension_manager.get_ternary_extension_table().create_retrieval(
            [True, False, True], "TOTAL"
        )
        self.m_ternary_retrieval_1_bound = self.m_extension_manager.get_ternary_extension_table().create_retrieval(
            [False, True, False], "TOTAL"
        )
        self.m_ternary_retrieval_2_bound = self.m_extension_manager.get_ternary_extension_table().create_retrieval(
            [False, False, True], "TOTAL"
        )

        self.m_dl_clause_infos: list[DLClauseInfo] = []
        for dl_clause in dl_clauses:
            if dl_clause.is_general_concept_inclusion():
                clause_info = DLClauseInfo(dl_clause, self.m_extension_manager)
                if len(clause_info.m_y_nodes) > 0 or len(clause_info.m_z_concepts) > 0:
                    self.m_dl_clause_infos.append(clause_info)

        self.m_dl_clause_infos_by_x_concepts: dict[AtomicConcept, list[DLClauseInfo]] = {}
        self.m_dl_clause_infos_without_x_concepts: list[DLClauseInfo] = []
        for dl_clause_info in self.m_dl_clause_infos:
            if len(dl_clause_info.m_x_concepts) == 0:
                self.m_dl_clause_infos_without_x_concepts.append(dl_clause_info)
            else:
                for x_concept in dl_clause_info.m_x_concepts:
                    if x_concept not in self.m_dl_clause_infos_by_x_concepts:
                        self.m_dl_clause_infos_by_x_concepts[x_concept] = []
                    self.m_dl_clause_infos_by_x_concepts[x_concept].append(dl_clause_info)

        self.in_valid_atleast_for_blocked_parent: dict[AtLeastConcept, Node] = {}
        self.in_valid_clauses_for_blocked_parent: dict[DLClauseInfo, Node] = {}
        self.in_valid_atleast_for_blocker: dict[AtLeastConcept, Node] = {}
        self.in_valid_clauses_for_blocker: dict[DLClauseInfo, Node] = {}

    def clear(self) -> None:
        if hasattr(self.m_binary_retrieval_1_bound, "clear"):
            self.m_binary_retrieval_1_bound.clear()
        if hasattr(self.m_ternary_retrieval_01_bound, "clear"):
            self.m_ternary_retrieval_01_bound.clear()
        if hasattr(self.m_ternary_retrieval_02_bound, "clear"):
            self.m_ternary_retrieval_02_bound.clear()
        if hasattr(self.m_ternary_retrieval_1_bound, "clear"):
            self.m_ternary_retrieval_1_bound.clear()
        if hasattr(self.m_ternary_retrieval_2_bound, "clear"):
            self.m_ternary_retrieval_2_bound.clear()
        for index in range(len(self.m_dl_clause_infos) - 1, -1, -1):
            self.m_dl_clause_infos[index].clear()

    def clear_invalids(self) -> None:
        self.in_valid_atleast_for_blocked_parent.clear()
        self.in_valid_atleast_for_blocker.clear()
        self.in_valid_clauses_for_blocked_parent.clear()
        self.in_valid_clauses_for_blocker.clear()

    def has_violation(self) -> bool:
        return (
            bool(self.in_valid_atleast_for_blocker)
            or bool(self.in_valid_clauses_for_blocker)
            or bool(self.in_valid_atleast_for_blocked_parent)
            or bool(self.in_valid_clauses_for_blocked_parent)
        )

    def blocker_changed(self, node: Node) -> None:
        parent = node.parent
        blocking_obj = parent.get_blocking_object()
        assert isinstance(blocking_obj, ValidatedBlockingObject)
        blocking_obj.set_has_already_been_checked(False)

    def is_block_valid(self, blocked: Node) -> bool:
        blocked_parent = blocked.parent
        blocking_obj = blocked_parent.get_blocking_object()
        assert isinstance(blocking_obj, ValidatedBlockingObject)
        if not blocking_obj.has_already_been_checked():
            self._reset_child_flags(blocked_parent)
            self._check_constraints_for_nonblocked_x(blocked_parent)
            blocking_obj.set_has_already_been_checked(True)

        blocked_obj = blocked.get_blocking_object()
        assert isinstance(blocked_obj, ValidatedBlockingObject)
        if blocked_obj.block_violates_parent_constraints():
            return False
        if not self._satisfies_constraints_for_blocked_x(blocked):
            return False
        return True

    def _reset_child_flags(self, parent: Node) -> None:
        self.m_ternary_retrieval_1_bound.get_bindings_buffer()[1] = parent
        self.m_ternary_retrieval_1_bound.open()
        tuple_buffer = self.m_ternary_retrieval_1_bound.get_tuple_buffer()
        while not self.m_ternary_retrieval_1_bound.after_last():
            node = tuple_buffer[2]
            if not node.is_ancestor_of(parent):
                blocking_obj = node.get_blocking_object()
                assert isinstance(blocking_obj, ValidatedBlockingObject)
                blocking_obj.set_block_violates_parent_constraints(False)
            self.m_ternary_retrieval_1_bound.next()

        self.m_ternary_retrieval_2_bound.get_bindings_buffer()[2] = parent
        self.m_ternary_retrieval_2_bound.open()
        tuple_buffer = self.m_ternary_retrieval_2_bound.get_tuple_buffer()
        while not self.m_ternary_retrieval_2_bound.after_last():
            node = tuple_buffer[1]
            if not node.is_ancestor_of(parent):
                blocking_obj = node.get_blocking_object()
                assert isinstance(blocking_obj, ValidatedBlockingObject)
                blocking_obj.set_block_violates_parent_constraints(False)
            self.m_ternary_retrieval_2_bound.next()

    def _satisfies_constraints_for_blocked_x(self, blocked_x: Node) -> bool:
        blocker = blocked_x.get_blocker()
        blocker_parent = blocker.parent
        self.m_binary_retrieval_1_bound.get_bindings_buffer()[1] = blocker
        self.m_binary_retrieval_1_bound.open()
        tuple_buffer = self.m_binary_retrieval_1_bound.get_tuple_buffer()
        while not self.m_binary_retrieval_1_bound.after_last():
            item = tuple_buffer[0]
            if isinstance(item, AtomicConcept):
                dl_clause_infos = self.m_dl_clause_infos_by_x_concepts.get(item)
                if dl_clause_infos is not None:
                    for dl_clause_info in dl_clause_infos:
                        if not self._satisfies_dl_clause_for_blocked_x(dl_clause_info, blocked_x):
                            return False
            elif hasattr(item, "number"):  # AtLeastConcept
                if (
                    self.m_extension_manager.contains_role_assertion(item.on_role, blocker, blocker_parent)
                    and self.m_extension_manager.contains_concept_assertion(item.to_concept, blocker_parent)
                ):
                    if not self._is_satisfied_at_least_for_blocked(item, blocked_x, blocker, blocker_parent):
                        return False
            self.m_binary_retrieval_1_bound.next()

        for dl_clause_info in self.m_dl_clause_infos_without_x_concepts:
            if not self._satisfies_dl_clause_for_blocked_x(dl_clause_info, blocked_x):
                return False
        return True

    def _is_satisfied_at_least_for_blocked(
        self, atleast: AtLeastConcept, blocked_x: Node, blocker: Node, blocker_parent: Node
    ) -> bool:
        r = atleast.on_role
        c = atleast.to_concept
        blocked_x_parent = blocked_x.parent

        if self.m_extension_manager.contains_role_assertion(r, blocked_x, blocked_x_parent) \
                and self.m_extension_manager.contains_concept_assertion(c, blocked_x_parent):
            return True

        from hermit.model import InverseRole

        if isinstance(r, AtomicRole):
            retrieval = self.m_ternary_retrieval_01_bound
            retrieval.get_bindings_buffer()[0] = r
            retrieval.get_bindings_buffer()[1] = blocker
            position = 2
        else:
            assert isinstance(r, InverseRole)
            retrieval = self.m_ternary_retrieval_02_bound
            retrieval.get_bindings_buffer()[0] = r.inverse_of
            retrieval.get_bindings_buffer()[2] = blocker
            position = 1

        retrieval.open()
        tuple_buffer = retrieval.get_tuple_buffer()
        suitable_successors = 0
        required_successors = atleast.number
        while not retrieval.after_last() and suitable_successors < required_successors:
            r_successor = tuple_buffer[position]
            if r_successor != blocker_parent and self.m_extension_manager.contains_concept_assertion(c, r_successor):
                suitable_successors += 1
            retrieval.next()

        if suitable_successors < required_successors:
            return False
        return True

    def _satisfies_dl_clause_for_blocked_x(self, dl_clause_info: DLClauseInfo, blocked_x: Node) -> bool:
        assert blocked_x.is_directly_blocked()
        blocked_x_parent = blocked_x.parent
        blocker = blocked_x.get_blocker()

        for atomic_concept in dl_clause_info.m_x_concepts:
            if not self.m_extension_manager.contains_assertion(atomic_concept, blocker):
                return True
        for atomic_role in dl_clause_info.m_x2x_roles:
            if not self.m_extension_manager.contains_assertion(atomic_role, blocker, blocker):
                return True

        matching_y_constraint_index = -1
        for y_index in range(len(dl_clause_info.m_y_constraints)):
            if matching_y_constraint_index == -1:
                y_constraint = dl_clause_info.m_y_constraints[y_index]
                if y_constraint.is_satisfied_explicitly(
                    self.m_extension_manager, blocked_x, blocked_x_parent
                ):
                    matching_y_constraint_index = y_index

        if matching_y_constraint_index == -1:
            return True

        dl_clause_info.m_x_node = blocker
        dl_clause_info.m_y_nodes[matching_y_constraint_index] = blocked_x_parent
        result = self._satisfies_dl_clause_for_blocked_x_and_any_z(
            dl_clause_info, blocked_x, matching_y_constraint_index, 0
        )
        dl_clause_info.m_x_node = None
        dl_clause_info.m_y_nodes[matching_y_constraint_index] = None
        return result

    def _satisfies_dl_clause_for_blocked_x_and_any_z(
        self, dl_clause_info: DLClauseInfo, blocked_x: Node, parent_of_blocked_x_index: int, to_match_index: int
    ) -> bool:
        if to_match_index == len(dl_clause_info.m_z_nodes):
            return self._satisfies_dl_clause_for_blocked_x_any_z_and_any_y(
                dl_clause_info, blocked_x, parent_of_blocked_x_index, 0, 0
            )
        else:
            z_concepts = dl_clause_info.m_z_concepts[to_match_index]
            retrieval = dl_clause_info.m_z_retrievals[to_match_index]
            retrieval.get_bindings_buffer()[0] = z_concepts[0]
            retrieval.open()
            tuple_buffer = retrieval.get_tuple_buffer()
            while not retrieval.after_last():
                node_z = tuple_buffer[1]
                all_matched = True
                for idx in range(1, len(z_concepts)):
                    if not self.m_extension_manager.contains_assertion(z_concepts[idx], node_z):
                        all_matched = False
                        break
                if all_matched:
                    dl_clause_info.m_z_nodes[to_match_index] = node_z
                    result = self._satisfies_dl_clause_for_blocked_x_and_any_z(
                        dl_clause_info, blocked_x, parent_of_blocked_x_index, to_match_index + 1
                    )
                    dl_clause_info.m_z_nodes[to_match_index] = None
                    if not result:
                        return False
                retrieval.next()
            return True

    def _satisfies_dl_clause_for_blocked_x_any_z_and_any_y(
        self,
        dl_clause_info: DLClauseInfo,
        blocked_x: Node,
        parent_of_blocked_x_index: int,
        to_match_index_x_to_y: int,
        to_match_index_y_to_x: int,
    ) -> bool:
        if (to_match_index_x_to_y + to_match_index_y_to_x) == parent_of_blocked_x_index:
            if len(dl_clause_info.m_y_constraints[parent_of_blocked_x_index].m_x2y_roles) != 0:
                return self._satisfies_dl_clause_for_blocked_x_any_z_and_any_y(
                    dl_clause_info, blocked_x, parent_of_blocked_x_index,
                    to_match_index_x_to_y + 1, to_match_index_y_to_x,
                )
            else:
                return self._satisfies_dl_clause_for_blocked_x_any_z_and_any_y(
                    dl_clause_info, blocked_x, parent_of_blocked_x_index,
                    to_match_index_x_to_y, to_match_index_y_to_x + 1,
                )
        elif (to_match_index_x_to_y + to_match_index_y_to_x) == len(dl_clause_info.m_y_constraints):
            return self._satisfies_dl_clause_for_blocked_x_and_matched_nodes(
                dl_clause_info, blocked_x, parent_of_blocked_x_index,
            )
        else:
            x_to_y_increment = 0
            y_to_x_increment = 0
            blocker = blocked_x.get_blocker()
            blocker_parent = blocker.parent
            y_constraint = dl_clause_info.m_y_constraints[to_match_index_x_to_y + to_match_index_y_to_x]
            assert len(y_constraint.m_x2y_roles) != 0 or len(y_constraint.m_y2x_roles) != 0

            y_node_index: int
            retrieval: Any
            if len(y_constraint.m_x2y_roles) != 0:
                retrieval = dl_clause_info.m_x2y_retrievals[to_match_index_x_to_y]
                retrieval.get_bindings_buffer()[0] = dl_clause_info.m_x2y_roles[to_match_index_x_to_y]
                retrieval.get_bindings_buffer()[1] = blocker
                y_node_index = 2
                x_to_y_increment = 1
            else:
                retrieval = dl_clause_info.m_y2x_retrievals[to_match_index_y_to_x]
                retrieval.get_bindings_buffer()[0] = dl_clause_info.m_y2x_roles[to_match_index_y_to_x]
                retrieval.get_bindings_buffer()[2] = blocker
                y_node_index = 1
                y_to_x_increment = 1

            retrieval.open()
            tuple_buffer = retrieval.get_tuple_buffer()
            while not retrieval.after_last():
                node_y = tuple_buffer[y_node_index]
                if node_y != blocker_parent and y_constraint.is_satisfied_explicitly(
                    self.m_extension_manager, blocker, node_y
                ):
                    dl_clause_info.m_y_nodes[to_match_index_x_to_y + to_match_index_y_to_x] = node_y
                    result = self._satisfies_dl_clause_for_blocked_x_any_z_and_any_y(
                        dl_clause_info, blocked_x, parent_of_blocked_x_index,
                        to_match_index_x_to_y + x_to_y_increment,
                        to_match_index_y_to_x + y_to_x_increment,
                    )
                    dl_clause_info.m_y_nodes[to_match_index_x_to_y + to_match_index_y_to_x] = None
                    if not result:
                        return False
                retrieval.next()
            return True

    def _satisfies_dl_clause_for_blocked_x_and_matched_nodes(
        self, dl_clause_info: DLClauseInfo, blocked_x: Node, parent_of_blocked_x_index: int
    ) -> bool:
        for consequence_atom in dl_clause_info.m_consequences_for_blocked_x:
            if consequence_atom.is_satisfied(self.m_extension_manager, dl_clause_info, blocked_x):
                return True
        return False

    # -- Non-blocked X constraint checks -----------------------------------

    def _check_constraints_for_nonblocked_x(self, nonblocked_x: Node) -> None:
        self.m_binary_retrieval_1_bound.get_bindings_buffer()[1] = nonblocked_x
        self.m_binary_retrieval_1_bound.open()
        tuple_buffer = self.m_binary_retrieval_1_bound.get_tuple_buffer()
        while not self.m_binary_retrieval_1_bound.after_last():
            item = tuple_buffer[0]
            if hasattr(item, "number"):  # AtLeastConcept
                self._check_at_least_for_nonblocked(item, nonblocked_x)
            self.m_binary_retrieval_1_bound.next()

        for dl_clause_info in self.m_dl_clause_infos:
            self._check_dl_clause_for_nonblocked_x(dl_clause_info, nonblocked_x)

    def _check_at_least_for_nonblocked(self, atleast: AtLeastConcept, nonblocked: Node) -> None:
        suitable_successors = 0
        required_successors = atleast.number
        r = atleast.on_role
        c = atleast.to_concept

        from hermit.model import InverseRole

        if isinstance(r, AtomicRole):
            retrieval = self.m_ternary_retrieval_01_bound
            retrieval.get_bindings_buffer()[0] = r
            retrieval.get_bindings_buffer()[1] = nonblocked
            position = 2
        else:
            assert isinstance(r, InverseRole)
            retrieval = self.m_ternary_retrieval_02_bound
            retrieval.get_bindings_buffer()[0] = r.inverse_of
            retrieval.get_bindings_buffer()[2] = nonblocked
            position = 1

        retrieval.open()
        tuple_buffer = retrieval.get_tuple_buffer()
        possibly_invalidly_blocked: list[Node] = []
        while not retrieval.after_last() and suitable_successors < required_successors:
            r_successor = tuple_buffer[position]
            if r_successor.is_blocked() and not r_successor.get_blocking_object().block_violates_parent_constraints():  # type: ignore[union-attr]
                if self.m_extension_manager.contains_concept_assertion(c, r_successor.get_blocker()):
                    suitable_successors += 1
                else:
                    possibly_invalidly_blocked.append(r_successor)
            elif self.m_extension_manager.contains_concept_assertion(c, r_successor):
                suitable_successors += 1
            retrieval.next()

        for i in range(len(possibly_invalidly_blocked)):
            if suitable_successors >= required_successors:
                break
            blocked_node = possibly_invalidly_blocked[i]
            if self.m_extension_manager.contains_concept_assertion(c, blocked_node):
                blocked_node.get_blocking_object().set_block_violates_parent_constraints(True)  # type: ignore[union-attr]
                suitable_successors += 1

    def _check_dl_clause_for_nonblocked_x(self, dl_clause_info: DLClauseInfo, nonblocked_x: Node) -> None:
        for atomic_concept in dl_clause_info.m_x_concepts:
            if not self.m_extension_manager.contains_assertion(atomic_concept, nonblocked_x):
                return
        for atomic_role in dl_clause_info.m_x2x_roles:
            if not self.m_extension_manager.contains_assertion(atomic_role, nonblocked_x, nonblocked_x):
                return
        dl_clause_info.m_x_node = nonblocked_x
        self._check_dl_clause_for_nonblocked_x_and_any_z(dl_clause_info, nonblocked_x, 0)
        dl_clause_info.m_x_node = None

    def _check_dl_clause_for_nonblocked_x_and_any_z(
        self, dl_clause_info: DLClauseInfo, nonblocked_x: Node, to_match_index: int
    ) -> None:
        if to_match_index == len(dl_clause_info.m_z_nodes):
            self._check_dl_clause_for_nonblocked_x_any_z_and_any_y(dl_clause_info, nonblocked_x, 0, 0)
        else:
            z_concepts = dl_clause_info.m_z_concepts[to_match_index]
            retrieval = dl_clause_info.m_z_retrievals[to_match_index]
            retrieval.get_bindings_buffer()[0] = z_concepts[0]
            retrieval.open()
            tuple_buffer = retrieval.get_tuple_buffer()
            while not retrieval.after_last():
                node_z = tuple_buffer[1]
                all_matched = True
                for idx in range(1, len(z_concepts)):
                    if not self.m_extension_manager.contains_assertion(z_concepts[idx], node_z):
                        all_matched = False
                        break
                if all_matched:
                    dl_clause_info.m_z_nodes[to_match_index] = node_z
                    self._check_dl_clause_for_nonblocked_x_and_any_z(
                        dl_clause_info, nonblocked_x, to_match_index + 1
                    )
                    dl_clause_info.m_z_nodes[to_match_index] = None
                    return
                retrieval.next()

    def _check_dl_clause_for_nonblocked_x_any_z_and_any_y(
        self,
        dl_clause_info: DLClauseInfo,
        nonblocked_x: Node,
        to_match_index_x_to_y: int,
        to_match_index_y_to_x: int,
    ) -> None:
        if (to_match_index_x_to_y + to_match_index_y_to_x) == len(dl_clause_info.m_y_constraints):
            self._check_dl_clause_for_nonblocked_x_and_matched_nodes(dl_clause_info, nonblocked_x)
        else:
            y_constraint = dl_clause_info.m_y_constraints[to_match_index_x_to_y + to_match_index_y_to_x]
            assert len(y_constraint.m_x2y_roles) != 0 or len(y_constraint.m_y2x_roles) != 0
            x_to_y_increment = 0
            y_to_x_increment = 0
            y_node_index: int
            retrieval: Any

            if len(y_constraint.m_x2y_roles) != 0:
                x_to_y_increment = 1
                retrieval = dl_clause_info.m_x2y_retrievals[to_match_index_x_to_y]
                retrieval.get_bindings_buffer()[0] = dl_clause_info.m_x2y_roles[to_match_index_x_to_y]
                retrieval.get_bindings_buffer()[1] = nonblocked_x
            else:
                y_to_x_increment = 1
                retrieval = dl_clause_info.m_y2x_retrievals[to_match_index_y_to_x]
                retrieval.get_bindings_buffer()[0] = dl_clause_info.m_y2x_roles[to_match_index_y_to_x]
                retrieval.get_bindings_buffer()[2] = nonblocked_x
                y_node_index = 1

            retrieval.open()
            tuple_buffer = retrieval.get_tuple_buffer()
            while not retrieval.after_last():
                node_y = tuple_buffer[y_node_index]
                if y_constraint.is_satisfied_via_mirroring_y(self.m_extension_manager, nonblocked_x, node_y):
                    dl_clause_info.m_y_nodes[to_match_index_x_to_y + to_match_index_y_to_x] = node_y
                    self._check_dl_clause_for_nonblocked_x_any_z_and_any_y(
                        dl_clause_info, nonblocked_x,
                        to_match_index_x_to_y + x_to_y_increment,
                        to_match_index_y_to_x + y_to_x_increment,
                    )
                    dl_clause_info.m_y_nodes[to_match_index_x_to_y + to_match_index_y_to_x] = None
                retrieval.next()

    def _check_dl_clause_for_nonblocked_x_and_matched_nodes(
        self, dl_clause_info: DLClauseInfo, nonblocked_x: Node
    ) -> None:
        contains_at_least_one_blocked_y = False
        for y_node in dl_clause_info.m_y_nodes:
            if y_node is not None and y_node.is_blocked():
                blocking_obj = y_node.get_blocking_object()
                if not blocking_obj.block_violates_parent_constraints():  # type: ignore[union-attr]
                    contains_at_least_one_blocked_y = True
                    break
        if not contains_at_least_one_blocked_y:
            return

        for consequence_atom in dl_clause_info.m_consequences_for_nonblocked_x:
            if consequence_atom.is_satisfied(self.m_extension_manager, dl_clause_info, nonblocked_x):
                return

        for i in range(len(dl_clause_info.m_y_constraints) - 1, -1, -1):
            y_constraint = dl_clause_info.m_y_constraints[i]
            yi = dl_clause_info.m_y_nodes[i]
            for c in y_constraint.m_y_concepts:
                if (
                    yi is not None
                    and yi.is_blocked()
                    and not yi.get_blocking_object().block_violates_parent_constraints()  # type: ignore[union-attr]
                    and not self.m_extension_manager.contains_assertion(c, yi)
                    and self.m_extension_manager.contains_assertion(c, yi.get_blocker())
                ):
                    yi.get_blocking_object().set_block_violates_parent_constraints(True)  # type: ignore[union-attr]
                    return

        for consequence_atom in dl_clause_info.m_consequences_for_nonblocked_x:
            if isinstance(consequence_atom, _MirroredYConsequenceAtom):
                if consequence_atom.is_satisfied_non_mirrored(self.m_extension_manager, dl_clause_info):
                    node_y = dl_clause_info.m_y_nodes[consequence_atom.m_y_argument_index]
                    if node_y is not None:
                        node_y.get_blocking_object().set_block_violates_parent_constraints(True)  # type: ignore[union-attr]
                    return

