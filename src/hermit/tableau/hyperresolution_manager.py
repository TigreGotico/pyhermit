"""Hyperresolution manager.

Compiles and applies DL clauses during tableau expansion using a
bytecode-style virtual machine approach. DL clauses are compiled into
sequences of Worker instructions that are executed to derive new facts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hermit.model import (
        Atom,
        AtomicConcept,
        AtomicRole,
        DLClause,
        DLPredicate,
        Variable,
    )
    from hermit.tableau.dl_clause_evaluator import DLClauseEvaluator
    from hermit.tableau.extension_manager import Retrieval
    from hermit.tableau.node import Node
    from hermit.tableau.tableau import Tableau


class CompiledDLClauseInfo:
    """Linked-list node for compiled DL clause evaluators."""

    __slots__ = ("m_evaluator", "m_next", "m_index_in_list")

    def __init__(
        self,
        evaluator: DLClauseEvaluator,
        next_info: CompiledDLClauseInfo | None,
    ) -> None:
        self.m_evaluator = evaluator
        self.m_next = next_info
        self.m_index_in_list: int = (
            1 if next_info is None else next_info.m_index_in_list + 1
        )


class BodyAtomsSwapper:
    """Reorders body atoms of a DL clause for optimal evaluation."""

    def __init__(self, dl_clause: DLClause) -> None:
        self.m_dl_clause = dl_clause
        self.m_node_id_comparison_atoms: list[Atom] = []
        self.m_used_atoms: list[bool] = []
        self.m_reordered_atoms: list[Atom] = []
        self.m_bound_variables: set[Variable] = set()

    def get_swapped_dl_clause(self, body_index: int) -> DLClause:
        """Return a DL clause with body atoms reordered starting at *body_index*."""
        self.m_node_id_comparison_atoms.clear()
        self.m_used_atoms = [False] * self.m_dl_clause.get_body_length()
        self.m_reordered_atoms.clear()
        self.m_bound_variables.clear()
        atom = self.m_dl_clause.get_body_atom(body_index)
        atom.get_variables(self.m_bound_variables)
        self.m_reordered_atoms.append(atom)
        self.m_used_atoms[body_index] = True
        while len(self.m_reordered_atoms) != self.m_dl_clause.get_body_length():
            best_atom: Atom | None = None
            best_atom_index = -1
            best_atom_goodness = -1000
            for index in range(self.m_dl_clause.get_body_length() - 1, -1, -1):
                if not self.m_used_atoms[index]:
                    atom = self.m_dl_clause.get_body_atom(index)
                    atom_goodness = self._get_atom_goodness(atom)
                    if atom_goodness > best_atom_goodness:
                        best_atom = atom
                        best_atom_goodness = atom_goodness
                        best_atom_index = index
            assert best_atom is not None
            self.m_reordered_atoms.append(best_atom)
            self.m_used_atoms[best_atom_index] = True
            best_atom.get_variables(self.m_bound_variables)
            if best_atom in self.m_node_id_comparison_atoms:
                self.m_node_id_comparison_atoms.remove(best_atom)
        body_atoms: list[Atom] = list(self.m_reordered_atoms)
        return self.m_dl_clause.get_changed_dl_clause(None, body_atoms)

    def _get_atom_goodness(self, atom: Atom) -> int:
        """Score an atom for reordering purposes."""
        from hermit.model import NodeIDLessEqualThan, NodeIDsAscendingOrEqual

        if NodeIDLessEqualThan.INSTANCE == atom.get_dl_predicate():
            if (
                atom.get_argument_variable(0) in self.m_bound_variables
                and atom.get_argument_variable(1) in self.m_bound_variables
            ):
                return 1000
            return -2000
        if isinstance(atom.get_dl_predicate(), NodeIDsAscendingOrEqual):
            number_of_unbound_variables = 0
            for argument_index in range(atom.arity() - 1, -1, -1):
                term = atom.get_argument(argument_index)
                from hermit.model import Variable

                if isinstance(term, Variable):
                    if term not in self.m_bound_variables:
                        number_of_unbound_variables += 1
            if number_of_unbound_variables > 0:
                return -5000
            return 5000
        number_of_bound_variables = 0
        number_of_unbound_variables = 0
        for argument_index in range(atom.arity() - 1, -1, -1):
            term = atom.get_argument(argument_index)
            from hermit.model import Variable

            if isinstance(term, Variable):
                if term in self.m_bound_variables:
                    number_of_bound_variables += 1
                else:
                    number_of_unbound_variables += 1
        goodness = number_of_bound_variables * 100 - number_of_unbound_variables * 10
        if (
            atom.get_dl_predicate().arity() == 2
            and number_of_unbound_variables == 1
            and self.m_node_id_comparison_atoms
        ):
            unbound_variable = atom.get_argument_variable(0)
            if unbound_variable in self.m_bound_variables:
                unbound_variable = atom.get_argument_variable(1)
            for compare_atom in reversed(self.m_node_id_comparison_atoms):
                arg0 = compare_atom.get_argument_variable(0)
                arg1 = compare_atom.get_argument_variable(1)
                if (
                    (arg0 in self.m_bound_variables or unbound_variable == arg0)
                    and (arg1 in self.m_bound_variables or unbound_variable == arg1)
                ):
                    goodness += 5
                    break
        return goodness


class DLClauseBodyKey:
    """Hash key for DL clause bodies (set of body atoms)."""

    def __init__(self, dl_clause: DLClause) -> None:
        self.m_dl_clause = dl_clause
        hash_code = 0
        for atom_index in range(dl_clause.get_body_length()):
            hash_code += dl_clause.get_body_atom(atom_index).__hash__()
        self.m_hash_code = hash_code

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, DLClauseBodyKey):
            return False
        that_dl_clause = other.m_dl_clause
        if self.m_dl_clause.get_body_length() != that_dl_clause.get_body_length():
            return False
        for atom_index in range(self.m_dl_clause.get_body_length()):
            if not self.m_dl_clause.get_body_atom(atom_index).equals(
                that_dl_clause.get_body_atom(atom_index)
            ):
                return False
        return True

    def __hash__(self) -> int:
        return self.m_hash_code


class HyperresolutionManager:
    """Manages hyperresolution-based DL clause application.

    Compiles DL clauses into efficient bytecode-style workers that are
    executed during tableau expansion to derive new assertions.
    """

    def __init__(self, tableau: Tableau, dl_clauses: set[DLClause]) -> None:
        self.m_interrupt_flag = tableau.m_interrupt_flag
        self.m_extension_manager = tableau.m_extension_manager
        self.m_tuple_consumers_by_delta_predicate: dict[
            DLPredicate, CompiledDLClauseInfo
        ] = {}
        self.m_atomic_role_tuple_consumers_unguarded: dict[
            AtomicRole, CompiledDLClauseInfo
        ] = {}
        self.m_atomic_role_tuple_consumers_by_guard_concept1: dict[
            AtomicRole, dict[AtomicConcept, CompiledDLClauseInfo]
        ] = {}
        self.m_atomic_role_tuple_consumers_by_guard_concept2: dict[
            AtomicRole, dict[AtomicConcept, CompiledDLClauseInfo]
        ] = {}

        # Index DL clauses by body
        dl_clauses_by_body: dict[DLClauseBodyKey, list[DLClause]] = {}
        for dl_clause in dl_clauses:
            key = DLClauseBodyKey(dl_clause)
            dl_clauses_for_key = dl_clauses_by_body.get(key)
            if dl_clauses_for_key is None:
                dl_clauses_for_key = []
                dl_clauses_by_body[key] = dl_clauses_for_key
            dl_clauses_for_key.append(dl_clause)
            self.m_interrupt_flag.check_interrupt()

        # Compile the DL clauses
        retrievals_by_arity: dict[int, Retrieval] = {}
        from hermit.tableau.dl_clause_evaluator import (
            BufferSupply,
            DLClauseEvaluator,
            GroundDisjunctionHeaderManager,
            ValuesBufferManager,
        )

        buffer_supply = BufferSupply()
        no_terms_to_nodes: dict[Any, Any] = {}
        values_buffer_manager = ValuesBufferManager(dl_clauses, no_terms_to_nodes)
        ground_disjunction_header_manager = GroundDisjunctionHeaderManager()
        union_dependency_sets_by_size: dict[int, Any] = {}
        guarding_atomic_concept_atoms1: list[Atom] = []
        guarding_atomic_concept_atoms2: list[Atom] = []

        for entry_key, dl_clause_list in dl_clauses_by_body.items():
            body_dl_clause = entry_key.m_dl_clause
            body_atoms_swapper = BodyAtomsSwapper(body_dl_clause)
            for body_atom_index in range(body_dl_clause.get_body_length()):
                if self._is_predicate_with_extension(
                    body_dl_clause.get_body_atom(body_atom_index).get_dl_predicate()
                ):
                    swapped_dl_clause = body_atoms_swapper.get_swapped_dl_clause(
                        body_atom_index
                    )
                    delta_atom = swapped_dl_clause.get_body_atom(0)
                    delta_dl_predicate = delta_atom.get_dl_predicate()
                    arity = delta_dl_predicate.arity() + 1
                    first_table_retrieval = retrievals_by_arity.get(arity)
                    if first_table_retrieval is None:
                        extension_table = self.m_extension_manager.get_extension_table(
                            arity
                        )
                        first_table_retrieval = extension_table.create_retrieval(
                            [False] * extension_table.m_tuple_arity, "DELTA_OLD"
                        )
                        retrievals_by_arity[arity] = first_table_retrieval
                    evaluator = DLClauseEvaluator(
                        tableau,
                        swapped_dl_clause,
                        dl_clause_list,
                        first_table_retrieval,
                        buffer_supply,
                        values_buffer_manager,
                        ground_disjunction_header_manager,
                        union_dependency_sets_by_size,
                    )
                    normal_tuple_consumer = CompiledDLClauseInfo(
                        evaluator, self.m_tuple_consumers_by_delta_predicate.get(delta_dl_predicate)
                    )
                    self.m_tuple_consumers_by_delta_predicate[
                        delta_dl_predicate
                    ] = normal_tuple_consumer
                    from hermit.model import AtomicRole, Variable

                    if (
                        isinstance(delta_dl_predicate, AtomicRole)
                        and isinstance(delta_atom.get_argument(0), Variable)
                        and isinstance(delta_atom.get_argument(1), Variable)
                    ):
                        delta_atomic_role: AtomicRole = delta_dl_predicate
                        self._get_atomic_role_clause_guard(
                            swapped_dl_clause,
                            guarding_atomic_concept_atoms1,
                            guarding_atomic_concept_atoms2,
                        )
                        if guarding_atomic_concept_atoms1:
                            compiled_dl_clause_infos = (
                                self.m_atomic_role_tuple_consumers_by_guard_concept1.get(
                                    delta_atomic_role
                                )
                            )
                            if compiled_dl_clause_infos is None:
                                compiled_dl_clause_infos = {}
                                self.m_atomic_role_tuple_consumers_by_guard_concept1[
                                    delta_atomic_role
                                ] = compiled_dl_clause_infos
                            for guarding_atom in guarding_atomic_concept_atoms1:
                                atomic_concept: AtomicConcept = guarding_atom.get_dl_predicate()  # type: ignore[assignment]
                                optimized_tuple_consumer = CompiledDLClauseInfo(
                                    evaluator, compiled_dl_clause_infos.get(atomic_concept)
                                )
                                compiled_dl_clause_infos[atomic_concept] = (
                                    optimized_tuple_consumer
                                )
                        if guarding_atomic_concept_atoms2:
                            compiled_dl_clause_infos = (
                                self.m_atomic_role_tuple_consumers_by_guard_concept2.get(
                                    delta_atomic_role
                                )
                            )
                            if compiled_dl_clause_infos is None:
                                compiled_dl_clause_infos = {}
                                self.m_atomic_role_tuple_consumers_by_guard_concept2[
                                    delta_atomic_role
                                ] = compiled_dl_clause_infos
                            for guarding_atom in guarding_atomic_concept_atoms2:
                                atomic_concept = guarding_atom.get_dl_predicate()  # type: ignore[assignment]
                                optimized_tuple_consumer = CompiledDLClauseInfo(
                                    evaluator, compiled_dl_clause_infos.get(atomic_concept)
                                )
                                compiled_dl_clause_infos[atomic_concept] = (
                                    optimized_tuple_consumer
                                )
                        if (
                            not guarding_atomic_concept_atoms1
                            and not guarding_atomic_concept_atoms2
                        ):
                            unguarded_tuple_consumer = CompiledDLClauseInfo(
                                evaluator,
                                self.m_atomic_role_tuple_consumers_unguarded.get(
                                    delta_atomic_role
                                ),
                            )
                            self.m_atomic_role_tuple_consumers_unguarded[
                                delta_atomic_role
                            ] = unguarded_tuple_consumer
                    buffer_supply.reuse_buffers()
                    self.m_interrupt_flag.check_interrupt()

        self.m_delta_old_retrievals: list[Retrieval] = [None] * len(  # type: ignore[list-item]
            retrievals_by_arity
        )
        list(retrievals_by_arity.values()).__iter__()
        for i, val in enumerate(retrievals_by_arity.values()):
            self.m_delta_old_retrievals[i] = val
        self.m_binary_table_retrieval = (
            self.m_extension_manager.get_extension_table(2).create_retrieval(
                [False, True], "EXTENSION_THIS"
            )
        )
        self.m_buffers_to_clear = buffer_supply.get_all_buffers()
        self.m_union_dependency_sets_to_clear: list[Any] = [None] * len(
            union_dependency_sets_by_size
        )
        for i, val in enumerate(union_dependency_sets_by_size.values()):
            self.m_union_dependency_sets_to_clear[i] = val
        self.m_values_buffer = values_buffer_manager.m_values_buffer
        self.m_max_number_of_variables = values_buffer_manager.m_max_number_of_variables

    def _get_atomic_role_clause_guard(
        self,
        swapped_dl_clause: DLClause,
        guarding_atomic_concept_atoms1: list[Atom],
        guarding_atomic_concept_atoms2: list[Atom],
    ) -> None:
        """Identify guard atoms for atomic role clauses."""
        from hermit.model import AtomicConcept

        guarding_atomic_concept_atoms1.clear()
        guarding_atomic_concept_atoms2.clear()
        delta_old_atom = swapped_dl_clause.get_body_atom(0)
        x = delta_old_atom.get_argument_variable(0)
        y = delta_old_atom.get_argument_variable(1)
        for body_index in range(1, swapped_dl_clause.get_body_length()):
            atom = swapped_dl_clause.get_body_atom(body_index)
            if isinstance(atom.get_dl_predicate(), AtomicConcept):
                variable = atom.get_argument_variable(0)
                if variable is not None:
                    if x == variable:
                        guarding_atomic_concept_atoms1.append(atom)
                    if y == variable:
                        guarding_atomic_concept_atoms2.append(atom)

    @staticmethod
    def _is_predicate_with_extension(dl_predicate: DLPredicate) -> bool:
        """Check if a predicate has an extension in the tableau."""
        from hermit.model import NodeIDLessEqualThan, NodeIDsAscendingOrEqual

        return not NodeIDLessEqualThan.INSTANCE.equals(dl_predicate) and not isinstance(
            dl_predicate, NodeIDsAscendingOrEqual
        )

    def clear(self) -> None:
        """Clear all retrieval state."""
        for retrieval in reversed(self.m_delta_old_retrievals):
            retrieval.clear()
        self.m_binary_table_retrieval.clear()
        for buffer in reversed(self.m_buffers_to_clear):
            for i in range(len(buffer)):
                buffer[i] = None
        for uds in reversed(self.m_union_dependency_sets_to_clear):
            if uds is not None:
                for i in range(len(uds.m_dependency_sets)):
                    uds.m_dependency_sets[i] = None
        for i in range(self.m_max_number_of_variables):
            self.m_values_buffer[i] = None

    def apply_dl_clauses(self) -> None:
        """Apply all compiled DL clauses."""
        for delta_old_retrieval in self.m_delta_old_retrievals:
            delta_old_retrieval.open()
            delta_old_tuple_buffer = delta_old_retrieval.get_tuple_buffer()
            # Tuple arity: 2 for binary (concept assertions), 3 for ternary (role assertions)
            tuple_arity = delta_old_retrieval._extension_table.m_tuple_arity  # type: ignore[attr-defined]
            while not delta_old_retrieval.after_last() and not self.m_extension_manager.contains_clash():
                delta_old_predicate = delta_old_tuple_buffer[0]
                unoptimized_compiled_dl_clause_info = (
                    self.m_tuple_consumers_by_delta_predicate.get(delta_old_predicate)
                )
                apply_unoptimized = True
                # Dispatch on tuple arity: only role assertions (arity 3) use the optimization.
                from hermit.model import AtomicRole
                is_role_assertion = isinstance(delta_old_predicate, AtomicRole) and tuple_arity == 3
                if (
                    unoptimized_compiled_dl_clause_info is not None
                    and delta_old_tuple_buffer[1] is not None
                    and is_role_assertion
                ):
                    node1 = delta_old_tuple_buffer[1]
                    node2: Node = delta_old_tuple_buffer[2]
                    unguarded_compiled_dl_clause_info = (
                        self.m_atomic_role_tuple_consumers_unguarded.get(
                            delta_old_predicate
                        )
                    )
                    unguarded_count = (
                        0
                        if unguarded_compiled_dl_clause_info is None
                        else unguarded_compiled_dl_clause_info.m_index_in_list
                    )
                    if (
                        unoptimized_compiled_dl_clause_info.m_index_in_list
                        > node1.number_of_positive_atomic_concepts
                        + node2.number_of_positive_atomic_concepts
                        + unguarded_count
                    ):
                        apply_unoptimized = False
                        while (
                            unguarded_compiled_dl_clause_info is not None
                            and not self.m_extension_manager.contains_clash()
                        ):
                            unguarded_compiled_dl_clause_info.m_evaluator.evaluate()
                            unguarded_compiled_dl_clause_info = (
                                unguarded_compiled_dl_clause_info.m_next
                            )
                        if not self.m_extension_manager.contains_clash():
                            compiled_dl_clause_infos = (
                                self.m_atomic_role_tuple_consumers_by_guard_concept1.get(
                                    delta_old_predicate
                                )
                            )
                            if compiled_dl_clause_infos is not None:
                                self.m_binary_table_retrieval.get_bindings_buffer()[
                                    1
                                ] = delta_old_tuple_buffer[1]
                                self.m_binary_table_retrieval.open()
                                binary_table_tuple_buffer = (
                                    self.m_binary_table_retrieval.get_tuple_buffer()
                                )
                                while (
                                    not self.m_binary_table_retrieval.after_last()
                                    and not self.m_extension_manager.contains_clash()
                                ):
                                    atomic_concept_object = binary_table_tuple_buffer[0]
                                    from hermit.model import AtomicConcept

                                    if isinstance(atomic_concept_object, AtomicConcept):
                                        optimized_compiled_dl_clause_info = (
                                            compiled_dl_clause_infos.get(
                                                atomic_concept_object
                                            )
                                        )
                                        while (
                                            optimized_compiled_dl_clause_info
                                            is not None
                                            and not self.m_extension_manager.contains_clash()
                                        ):
                                            optimized_compiled_dl_clause_info.m_evaluator.evaluate()
                                            optimized_compiled_dl_clause_info = (
                                                optimized_compiled_dl_clause_info.m_next
                                            )
                                    self.m_binary_table_retrieval.next()
                        if not self.m_extension_manager.contains_clash():
                            compiled_dl_clause_infos = (
                                self.m_atomic_role_tuple_consumers_by_guard_concept2.get(
                                    delta_old_predicate
                                )
                            )
                            if compiled_dl_clause_infos is not None:
                                self.m_binary_table_retrieval.get_bindings_buffer()[
                                    1
                                ] = delta_old_tuple_buffer[2]
                                self.m_binary_table_retrieval.open()
                                binary_table_tuple_buffer = (
                                    self.m_binary_table_retrieval.get_tuple_buffer()
                                )
                                while (
                                    not self.m_binary_table_retrieval.after_last()
                                    and not self.m_extension_manager.contains_clash()
                                ):
                                    atomic_concept_object = binary_table_tuple_buffer[0]
                                    from hermit.model import AtomicConcept

                                    if isinstance(atomic_concept_object, AtomicConcept):
                                        optimized_compiled_dl_clause_info = (
                                            compiled_dl_clause_infos.get(
                                                atomic_concept_object
                                            )
                                        )
                                        while (
                                            optimized_compiled_dl_clause_info
                                            is not None
                                            and not self.m_extension_manager.contains_clash()
                                        ):
                                            optimized_compiled_dl_clause_info.m_evaluator.evaluate()
                                            optimized_compiled_dl_clause_info = (
                                                optimized_compiled_dl_clause_info.m_next
                                            )
                                    self.m_binary_table_retrieval.next()
                if apply_unoptimized:
                    while (
                        unoptimized_compiled_dl_clause_info is not None
                        and not self.m_extension_manager.contains_clash()
                    ):
                        unoptimized_compiled_dl_clause_info.m_evaluator.evaluate()
                        unoptimized_compiled_dl_clause_info = (
                            unoptimized_compiled_dl_clause_info.m_next
                        )
                delta_old_retrieval.next()
