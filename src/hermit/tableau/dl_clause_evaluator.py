"""DL Clause evaluator.

Compiles DL clauses into bytecode-style Worker instructions that are
executed during tableau expansion. The evaluator uses a small virtual
machine with a program counter and various instruction types.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from hermit.tableau.union_dependency_set import UnionDependencySet

if TYPE_CHECKING:
    from hermit.model import (
        Atom,
        DLClause,
        DLPredicate,
        Term,
        Variable,
    )
    from hermit.monitor.tableau_monitor import TableauMonitor
    from hermit.tableau.dependency_set import DependencySet
    from hermit.tableau.extension_manager import ExtensionManager, Retrieval
    from hermit.tableau.ground_disjunction_header import GroundDisjunctionHeader
    from hermit.tableau.node import Node
    from hermit.tableau.tableau import Tableau
    from hermit.tableau.union_dependency_set import UnionDependencySet

CRLF = "\n"


# ------------------------------------------------------------------
# Worker interface and concrete implementations
# ------------------------------------------------------------------


class Worker(ABC):
    """Base class for DL clause evaluation workers."""

    @abstractmethod
    def execute(self, program_counter: int) -> int:
        """Execute this worker and return the next program counter."""
        ...


class BranchingWorker(Worker):
    """A worker that represents a branching point."""

    @abstractmethod
    def get_branching_address(self) -> int:
        """Return the branching address."""
        ...

    @abstractmethod
    def set_branching_address(self, branching_address: int) -> None:
        """Set the branching address."""
        ...


class CopyValues(Worker):
    """Copy a value from one buffer position to another."""

    __slots__ = ("m_from_buffer", "m_from_index", "m_to_buffer", "m_to_index")

    def __init__(
        self,
        from_buffer: list[object | None],
        from_index: int,
        to_buffer: list[object | None],
        to_index: int,
    ) -> None:
        self.m_from_buffer = from_buffer
        self.m_from_index = from_index
        self.m_to_buffer = to_buffer
        self.m_to_index = to_index

    def execute(self, program_counter: int) -> int:
        value = self.m_from_buffer[self.m_from_index]
        # Canonicalize nodes in case they were merged
        from hermit.tableau.node import Node
        if isinstance(value, Node):
            value = value.get_canonical_node()
        self.m_to_buffer[self.m_to_index] = value
        return program_counter + 1

    def __str__(self) -> str:
        return f"Copy {self.m_from_index} --> {self.m_to_index}"


class CopyDependencySet(Worker):
    """Copy a dependency set from a retrieval to a target array."""

    __slots__ = ("m_retrieval", "m_target_dependency_sets", "m_target_index")

    def __init__(
        self,
        retrieval: Retrieval,
        target_dependency_sets: list[DependencySet | None],
        target_index: int,
    ) -> None:
        self.m_retrieval = retrieval
        self.m_target_dependency_sets = target_dependency_sets
        self.m_target_index = target_index

    def execute(self, program_counter: int) -> int:
        self.m_target_dependency_sets[self.m_target_index] = (
            self.m_retrieval.get_dependency_set()
        )
        return program_counter + 1

    def __str__(self) -> str:
        return f"Copy dependency set to {self.m_target_index}"


class BranchIfNotEqual(BranchingWorker):
    """Branch if two buffer positions are not equal."""

    __slots__ = ("m_not_equal_program_counter", "m_buffer", "m_index1", "m_index2")

    def __init__(
        self,
        not_equal_program_counter: int,
        buffer: list[object | None],
        index1: int,
        index2: int,
    ) -> None:
        self.m_not_equal_program_counter = not_equal_program_counter
        self.m_buffer = buffer
        self.m_index1 = index1
        self.m_index2 = index2

    def execute(self, program_counter: int) -> int:
        if self.m_buffer[self.m_index1] == self.m_buffer[self.m_index2]:
            return program_counter + 1
        return self.m_not_equal_program_counter

    def get_branching_address(self) -> int:
        return self.m_not_equal_program_counter

    def set_branching_address(self, branching_address: int) -> None:
        self.m_not_equal_program_counter = branching_address

    def __str__(self) -> str:
        return f"Branch to {self.m_not_equal_program_counter} if {self.m_index1} != {self.m_index2}"


class BranchIfNotNodeIDLessEqualThan(BranchingWorker):
    """Branch if node IDs are not in less-equal order."""

    __slots__ = ("m_not_less_program_counter", "m_buffer", "m_index1", "m_index2")

    def __init__(
        self,
        not_less_program_counter: int,
        buffer: list[object | None],
        index1: int,
        index2: int,
    ) -> None:
        self.m_not_less_program_counter = not_less_program_counter
        self.m_buffer = buffer
        self.m_index1 = index1
        self.m_index2 = index2

    def execute(self, program_counter: int) -> int:
        node1_id = self.m_buffer[self.m_index1].node_id  # type: ignore[union-attr]
        node2_id = self.m_buffer[self.m_index2].node_id  # type: ignore[union-attr]
        if node1_id <= node2_id:
            return program_counter + 1
        return self.m_not_less_program_counter

    def get_branching_address(self) -> int:
        return self.m_not_less_program_counter

    def set_branching_address(self, branching_address: int) -> None:
        self.m_not_less_program_counter = branching_address

    def __str__(self) -> str:
        return (
            f"Branch to {self.m_not_less_program_counter} "
            f"if {self.m_index1}.ID > {self.m_index2}.ID"
        )


class BranchIfNotNodeIDsAscendingOrEqual(BranchingWorker):
    """Branch if node IDs are not ascending or all equal."""

    __slots__ = ("m_branch_program_counter", "m_buffer", "m_node_indexes")

    def __init__(
        self,
        branch_program_counter: int,
        buffer: list[object | None],
        node_indexes: list[int],
    ) -> None:
        self.m_branch_program_counter = branch_program_counter
        self.m_buffer = buffer
        self.m_node_indexes = node_indexes

    def execute(self, program_counter: int) -> int:
        strictly_ascending = True
        all_equal = True
        last_node_id = self.m_buffer[self.m_node_indexes[0]].node_id  # type: ignore[union-attr]
        for idx in range(1, len(self.m_node_indexes)):
            node_id = self.m_buffer[self.m_node_indexes[idx]].node_id  # type: ignore[union-attr]
            if last_node_id >= node_id:
                strictly_ascending = False
            if node_id != last_node_id:
                all_equal = False
            last_node_id = node_id
        if (not strictly_ascending and all_equal) or (strictly_ascending and not all_equal):
            return program_counter + 1
        return self.m_branch_program_counter

    def get_branching_address(self) -> int:
        return self.m_branch_program_counter

    def set_branching_address(self, branching_address: int) -> None:
        self.m_branch_program_counter = branching_address

    def __str__(self) -> str:
        return (
            f"Branch to {self.m_branch_program_counter} "
            "if node IDs are not ascending or equal"
        )


class OpenRetrieval(Worker):
    """Open a retrieval iterator."""

    __slots__ = ("m_retrieval",)

    def __init__(self, retrieval: Retrieval) -> None:
        self.m_retrieval = retrieval

    def execute(self, program_counter: int) -> int:
        self.m_retrieval.open()
        return program_counter + 1

    def __str__(self) -> str:
        positions = self.m_retrieval.get_binding_positions()
        buf = self.m_retrieval.get_bindings_buffer()
        return f"Open {buf[positions[0]]}" if positions else "Open"


class NextRetrieval(Worker):
    """Advance a retrieval to the next tuple."""

    __slots__ = ("m_retrieval",)

    def __init__(self, retrieval: Retrieval) -> None:
        self.m_retrieval = retrieval

    def execute(self, program_counter: int) -> int:
        self.m_retrieval.next()
        return program_counter + 1

    def __str__(self) -> str:
        positions = self.m_retrieval.get_binding_positions()
        buf = self.m_retrieval.get_bindings_buffer()
        return f"Next {buf[positions[0]]}" if positions else "Next"


class HasMoreRetrieval(BranchingWorker):
    """Branch if a retrieval has no more tuples."""

    __slots__ = ("m_eof_program_counter", "m_retrieval")

    def __init__(
        self, eof_program_counter: int, retrieval: Retrieval
    ) -> None:
        self.m_eof_program_counter = eof_program_counter
        self.m_retrieval = retrieval

    def execute(self, program_counter: int) -> int:
        if self.m_retrieval.after_last():
            return self.m_eof_program_counter
        return program_counter + 1

    def get_branching_address(self) -> int:
        return self.m_eof_program_counter

    def set_branching_address(self, branching_address: int) -> None:
        self.m_eof_program_counter = branching_address

    def __str__(self) -> str:
        positions = self.m_retrieval.get_binding_positions()
        buf = self.m_retrieval.get_bindings_buffer()
        return (
            f"Branch to {self.m_eof_program_counter} "
            f"if {buf[positions[0]]} is empty"
        )


class JumpTo(BranchingWorker):
    """Unconditional jump to a program counter."""

    __slots__ = ("m_jump_to",)

    def __init__(self, jump_to: int) -> None:
        self.m_jump_to = jump_to

    def execute(self, program_counter: int) -> int:
        return self.m_jump_to

    def get_branching_address(self) -> int:
        return self.m_jump_to

    def set_branching_address(self, branching_address: int) -> None:
        self.m_jump_to = branching_address

    def __str__(self) -> str:
        return f"Jump to {self.m_jump_to}"


class CallMatchStartedOnMonitor(Worker):
    """Notify the monitor that a DL clause match has started."""

    __slots__ = ("m_tableau_monitor", "m_dl_clause_evaluator", "m_dl_clause_index")

    def __init__(
        self,
        tableau_monitor: TableauMonitor,
        dl_clause_evaluator: DLClauseEvaluator,
        dl_clause_index: int,
    ) -> None:
        self.m_tableau_monitor = tableau_monitor
        self.m_dl_clause_evaluator = dl_clause_evaluator
        self.m_dl_clause_index = dl_clause_index

    def execute(self, program_counter: int) -> int:
        self.m_tableau_monitor.dl_clause_matched_started(
            self.m_dl_clause_evaluator, self.m_dl_clause_index
        )
        return program_counter + 1

    def __str__(self) -> str:
        return "Monitor -> Match started"


class CallMatchFinishedOnMonitor(Worker):
    """Notify the monitor that a DL clause match has finished."""

    __slots__ = ("m_tableau_monitor", "m_dl_clause_evaluator", "m_dl_clause_index")

    def __init__(
        self,
        tableau_monitor: TableauMonitor,
        dl_clause_evaluator: DLClauseEvaluator,
        dl_clause_index: int,
    ) -> None:
        self.m_tableau_monitor = tableau_monitor
        self.m_dl_clause_evaluator = dl_clause_evaluator
        self.m_dl_clause_index = dl_clause_index

    def execute(self, program_counter: int) -> int:
        self.m_tableau_monitor.dl_clause_matched_finished(
            self.m_dl_clause_evaluator, self.m_dl_clause_index
        )
        return program_counter + 1

    def __str__(self) -> str:
        return "Monitor -> Match finished"


class SetClash(Worker):
    """Set a clash in the extension manager."""

    __slots__ = ("m_extension_manager", "m_dependency_set")

    def __init__(
        self,
        extension_manager: ExtensionManager,
        dependency_set: DependencySet,
    ) -> None:
        self.m_extension_manager = extension_manager
        self.m_dependency_set = dependency_set

    def execute(self, program_counter: int) -> int:
        self.m_extension_manager.set_clash(self.m_dependency_set)
        return program_counter + 1

    def __str__(self) -> str:
        return "Set clash"


class DeriveUnaryFact(Worker):
    """Derive a unary fact (concept assertion)."""

    __slots__ = (
        "m_extension_manager",
        "m_values_buffer",
        "m_core_variables",
        "m_dependency_set",
        "m_dl_predicate",
        "m_argument_index",
    )

    def __init__(
        self,
        extension_manager: ExtensionManager,
        values_buffer: list[object | None],
        core_variables: list[bool],
        dependency_set: DependencySet,
        dl_predicate: DLPredicate,
        argument_index: int,
    ) -> None:
        self.m_extension_manager = extension_manager
        self.m_values_buffer = values_buffer
        self.m_core_variables = core_variables
        self.m_dependency_set = dependency_set
        self.m_dl_predicate = dl_predicate
        self.m_argument_index = argument_index

    def execute(self, program_counter: int) -> int:
        from hermit.tableau.node import Node
        argument = self.m_values_buffer[self.m_argument_index]
        if not isinstance(argument, Node):
            # Buffer contains non-Node data (e.g. stale/garbage); skip derivation.
            return program_counter + 1
        is_core = self.m_core_variables[self.m_argument_index]
        argument = argument.get_canonical_node()
        self.m_extension_manager.add_assertion(
            self.m_dl_predicate, argument, self.m_dependency_set, is_core
        )
        return program_counter + 1

    def __str__(self) -> str:
        return "Derive unary fact"


class DeriveBinaryFact(Worker):
    """Derive a binary fact (role assertion or equality)."""

    __slots__ = (
        "m_extension_manager",
        "m_values_buffer",
        "m_dependency_set",
        "m_dl_predicate",
        "m_argument_index1",
        "m_argument_index2",
    )

    def __init__(
        self,
        extension_manager: ExtensionManager,
        values_buffer: list[object | None],
        dependency_set: DependencySet,
        dl_predicate: DLPredicate,
        argument_index1: int,
        argument_index2: int,
    ) -> None:
        self.m_extension_manager = extension_manager
        self.m_values_buffer = values_buffer
        self.m_dependency_set = dependency_set
        self.m_dl_predicate = dl_predicate
        self.m_argument_index1 = argument_index1
        self.m_argument_index2 = argument_index2

    def execute(self, program_counter: int) -> int:
        argument1: Node = self.m_values_buffer[self.m_argument_index1]  # type: ignore[assignment]
        argument2: Node = self.m_values_buffer[self.m_argument_index2]  # type: ignore[assignment]
        # Canonicalize in case nodes were merged after being added to the buffer
        if argument1 is not None:
            argument1 = argument1.get_canonical_node()
        if argument2 is not None:
            argument2 = argument2.get_canonical_node()
        self.m_extension_manager.add_assertion(
            self.m_dl_predicate,
            argument1,
            argument2,
            self.m_dependency_set,
            True,
        )
        return program_counter + 1

    def __str__(self) -> str:
        return "Derive binary fact"


class DeriveTernaryFact(Worker):
    """Derive a ternary fact (annotated equality)."""

    __slots__ = (
        "m_extension_manager",
        "m_values_buffer",
        "m_dependency_set",
        "m_dl_predicate",
        "m_argument_index1",
        "m_argument_index2",
        "m_argument_index3",
    )

    def __init__(
        self,
        extension_manager: ExtensionManager,
        values_buffer: list[object | None],
        dependency_set: DependencySet,
        dl_predicate: DLPredicate,
        argument_index1: int,
        argument_index2: int,
        argument_index3: int,
    ) -> None:
        self.m_extension_manager = extension_manager
        self.m_values_buffer = values_buffer
        self.m_dependency_set = dependency_set
        self.m_dl_predicate = dl_predicate
        self.m_argument_index1 = argument_index1
        self.m_argument_index2 = argument_index2
        self.m_argument_index3 = argument_index3

    def execute(self, program_counter: int) -> int:
        argument1: Node = self.m_values_buffer[self.m_argument_index1]  # type: ignore[assignment]
        argument2: Node = self.m_values_buffer[self.m_argument_index2]  # type: ignore[assignment]
        argument3: Node = self.m_values_buffer[self.m_argument_index3]  # type: ignore[assignment]
        # Canonicalize in case nodes were merged after being added to the buffer
        if argument1 is not None:
            argument1 = argument1.get_canonical_node()
        if argument2 is not None:
            argument2 = argument2.get_canonical_node()
        if argument3 is not None:
            argument3 = argument3.get_canonical_node()
        self.m_extension_manager.add_assertion(
            self.m_dl_predicate,
            argument1,
            argument2,
            argument3,
            self.m_dependency_set,
            True,
        )
        return program_counter + 1

    def __str__(self) -> str:
        return "Derive ternary fact"


class DeriveDisjunction(Worker):
    """Derive a ground disjunction and add it to the tableau."""

    __slots__ = (
        "m_tableau",
        "m_values_buffer",
        "m_core_variables",
        "m_dependency_set",
        "m_ground_disjunction_header",
        "m_copy_is_core",
        "m_copy_values_to_arguments",
    )

    def __init__(
        self,
        values_buffer: list[object | None],
        core_variables: list[bool],
        dependency_set: DependencySet,
        tableau: Tableau,
        ground_disjunction_header: GroundDisjunctionHeader,
        copy_is_core: list[int],
        copy_values_to_arguments: list[int],
    ) -> None:
        self.m_values_buffer = values_buffer
        self.m_core_variables = core_variables
        self.m_dependency_set = dependency_set
        self.m_tableau = tableau
        self.m_ground_disjunction_header = ground_disjunction_header
        self.m_copy_is_core = copy_is_core
        self.m_copy_values_to_arguments = copy_values_to_arguments

    def clear(self) -> None:
        """Clear internal buffers (currently a no-op)."""

    def execute(self, program_counter: int) -> int:
        from hermit.tableau.ground_disjunction import GroundDisjunction

        arguments: list[Node] = [None] * len(self.m_copy_values_to_arguments)  # type: ignore[list-item]
        for argument_index in range(len(self.m_copy_values_to_arguments) - 1, -1, -1):
            arguments[argument_index] = self.m_values_buffer[
                self.m_copy_values_to_arguments[argument_index]
            ]
        is_core = [False] * len(self.m_copy_is_core)
        for copy_index in range(len(self.m_copy_is_core) - 1, -1, -1):
            copy_from = self.m_copy_is_core[copy_index]
            if copy_from == -1:
                is_core[copy_index] = True
            else:
                is_core[copy_index] = self.m_core_variables[copy_from]
        ground_disjunction = GroundDisjunction(
            self.m_tableau,
            self.m_ground_disjunction_header,
            arguments,
            is_core,
            self.m_tableau.m_dependency_set_factory.get_permanent(self.m_dependency_set),
        )
        if not ground_disjunction.is_satisfied(self.m_tableau):
            self.m_tableau.add_ground_disjunction(ground_disjunction)
        return program_counter + 1

    def __str__(self) -> str:
        return "Derive disjunction"


# ------------------------------------------------------------------
# Buffer and Manager helpers
# ------------------------------------------------------------------


class BufferSupply:
    """Pool of reusable object buffers."""

    def __init__(self) -> None:
        self.m_all_buffers: list[list[object | None]] = []
        self.m_available_buffers_by_arity: dict[int, list[list[object | None]]] = {}

    def reuse_buffers(self) -> None:
        """Return all buffers to the available pool by arity."""
        self.m_available_buffers_by_arity.clear()
        for buffer in self.m_all_buffers:
            arity = len(buffer)
            buffers = self.m_available_buffers_by_arity.get(arity)
            if buffers is None:
                buffers = []
                self.m_available_buffers_by_arity[arity] = buffers
            buffers.append(buffer)

    def get_buffer(self, arity: int) -> list[object | None]:
        """Get a buffer of the given arity."""
        buffers = self.m_available_buffers_by_arity.get(arity)
        if buffers is None or not buffers:
            buffer: list[object | None] = [None] * arity
            self.m_all_buffers.append(buffer)
            return buffer
        return buffers.pop()

    def get_all_buffers(self) -> list[list[object | None]]:
        """Return all buffers ever allocated."""
        return list(self.m_all_buffers)


class ValuesBufferManager:
    """Manages the values buffer for variable and term bindings."""

    def __init__(
        self,
        dl_clauses: set[DLClause],
        terms_to_nodes: dict[Term, Node],
    ) -> None:
        body_dl_predicates: set[DLPredicate] = set()
        variables: set[Variable] = set()
        self.m_body_nonvariable_terms_to_indexes: dict[Term, int] = {}
        max_number_of_variables = 0
        for dl_clause in dl_clauses:
            variables.clear()
            for body_index in range(dl_clause.get_body_length() - 1, -1, -1):
                atom = dl_clause.get_body_atom(body_index)
                body_dl_predicates.add(atom.get_dl_predicate())
                for argument_index in range(atom.arity()):
                    term = atom.get_argument(argument_index)
                    from hermit.model import Variable

                    if isinstance(term, Variable):
                        variables.add(term)
                    else:
                        self.m_body_nonvariable_terms_to_indexes[term] = -1
            if len(variables) > max_number_of_variables:
                max_number_of_variables = len(variables)
        self.m_values_buffer: list[object | None] = [None] * (
            max_number_of_variables + len(body_dl_predicates) + len(self.m_body_nonvariable_terms_to_indexes)
        )
        self.m_body_dl_predicates_to_indexes: dict[DLPredicate, int] = {}
        binding_index = max_number_of_variables
        for body_dl_predicate in body_dl_predicates:
            self.m_body_dl_predicates_to_indexes[body_dl_predicate] = binding_index
            self.m_values_buffer[binding_index] = body_dl_predicate
            binding_index += 1
        for term in self.m_body_nonvariable_terms_to_indexes:
            term_node = terms_to_nodes.get(term)
            if term_node is None:
                raise ValueError(f"Term '{term}' is unknown to the reasoner.")
            self.m_body_nonvariable_terms_to_indexes[term] = binding_index
            self.m_values_buffer[binding_index] = term_node.get_canonical_node()
            binding_index += 1
        self.m_max_number_of_variables = max_number_of_variables


class GroundDisjunctionHeaderManager:
    """Hash-based cache for GroundDisjunctionHeader objects."""

    def __init__(self) -> None:
        self.m_buckets: list[GroundDisjunctionHeader | None] = [None] * 1024
        self.m_threshold = int(len(self.m_buckets) * 0.75)
        self.m_number_of_elements = 0

    def get(self, dl_predicates: list[DLPredicate]) -> GroundDisjunctionHeader:
        """Get or create a GroundDisjunctionHeader for the given predicates."""
        hash_code = 0
        for disjunct_index in range(len(dl_predicates)):
            hash_code = hash_code * 7 + dl_predicates[disjunct_index].__hash__()
        bucket_index = self._get_index_for(hash_code, len(self.m_buckets))
        entry = self.m_buckets[bucket_index]
        while entry is not None:
            if hash_code == entry.m_hash_code and entry.is_equal(dl_predicates):
                return entry
            entry = entry.m_next_entry
        from hermit.tableau.ground_disjunction_header import GroundDisjunctionHeader

        entry = GroundDisjunctionHeader(dl_predicates, hash_code, entry)
        self.m_buckets[bucket_index] = entry
        self.m_number_of_elements += 1
        if self.m_number_of_elements >= self.m_threshold:
            self._resize(len(self.m_buckets) * 2)
        return entry

    def _resize(self, new_capacity: int) -> None:
        """Resize the hash table."""
        new_buckets: list[GroundDisjunctionHeader | None] = [None] * new_capacity
        for entry in self.m_buckets:
            current = entry
            while current is not None:
                next_entry = current.m_next_entry
                new_index = self._get_index_for(current.m_hash_code, new_capacity)
                current.m_next_entry = new_buckets[new_index]
                new_buckets[new_index] = current
                current = next_entry
        self.m_buckets = new_buckets
        self.m_threshold = int(new_capacity * 0.75)

    @staticmethod
    def _get_index_for(hash_code: int, table_length: int) -> int:
        """Compute a bucket index with additional mixing."""
        hash_code += ~(hash_code << 9)
        hash_code ^= (hash_code >> 14) & 0xFFFFFFFF
        hash_code += (hash_code << 4)
        hash_code ^= (hash_code >> 10) & 0xFFFFFFFF
        return hash_code & (table_length - 1)


# ------------------------------------------------------------------
# DL Clause Evaluator
# ------------------------------------------------------------------


class DLClauseEvaluator:
    """Evaluates compiled DL clauses.

    A DL clause is compiled into a sequence of Worker instructions.
    The evaluate() method runs the compiled "program" until completion
    or a clash is detected.
    """

    def __init__(
        self,
        tableau: Tableau,
        body_dl_clause: DLClause,
        head_dl_clauses: list[DLClause],
        first_atom_retrieval: Retrieval,
        buffer_supply: BufferSupply,
        values_buffer_manager: ValuesBufferManager,
        ground_disjunction_header_manager: GroundDisjunctionHeaderManager,
        union_dependency_sets_by_size: dict[int, UnionDependencySet],
    ) -> None:
        self.m_interrupt_flag = tableau.m_interrupt_flag
        self.m_extension_manager = tableau.m_extension_manager
        compiler = _DLClauseCompiler(
            buffer_supply,
            values_buffer_manager,
            ground_disjunction_header_manager,
            union_dependency_sets_by_size,
            self,
            self.m_extension_manager,
            tableau.m_existential_expansion_strategy,
            body_dl_clause,
            head_dl_clauses,
            first_atom_retrieval,
        )
        self.m_retrievals: list[Retrieval] = list(compiler.m_retrievals)
        self.m_workers: list[Worker] = list(compiler.m_workers)
        self.m_body_dl_clause = body_dl_clause
        self.m_head_dl_clauses = head_dl_clauses

    def get_body_length(self) -> int:
        """Return the number of body atoms."""
        return self.m_body_dl_clause.get_body_length()

    def get_body_atom(self, atom_index: int) -> Atom:
        """Return the body atom at the given index."""
        return self.m_body_dl_clause.get_body_atom(atom_index)

    def get_number_of_dl_clauses(self) -> int:
        """Return the number of head DL clauses."""
        return len(self.m_head_dl_clauses)

    def get_dl_clause(self, dl_clause_index: int) -> DLClause:
        """Return the head DL clause at the given index."""
        return self.m_head_dl_clauses[dl_clause_index]

    def get_head_length(self, dl_clause_index: int) -> int:
        """Return the number of head atoms in the given DL clause."""
        return self.m_head_dl_clauses[dl_clause_index].get_head_length()

    def get_head_atom(self, dl_clause_index: int, atom_index: int) -> Atom:
        """Return the head atom at the given index."""
        return self.m_head_dl_clauses[dl_clause_index].get_head_atom(atom_index)

    def get_tuple_matched_to_body(self, atom_index: int) -> list[object | None]:
        """Return the tuple buffer matched to the body atom at *atom_index*."""
        return self.m_retrievals[atom_index].get_tuple_buffer()

    def evaluate(self) -> None:
        """Execute the compiled DL clause program."""
        program_counter = 0
        while program_counter < len(self.m_workers) and not self.m_extension_manager.contains_clash():
            self.m_interrupt_flag.check_interrupt()
            program_counter = self.m_workers[program_counter].execute(program_counter)

    def __str__(self) -> str:
        maximal_pc_length = len(str(max(0, len(self.m_workers) - 1)))
        lines = []
        for program_counter in range(len(self.m_workers)):
            pc_string = str(program_counter)
            padding = " " * (maximal_pc_length - len(pc_string))
            lines.append(f"{padding}{pc_string}: {self.m_workers[program_counter]}{CRLF}")
        return "".join(lines)


# ------------------------------------------------------------------
# ConjunctionCompiler and DLClauseCompiler
# ------------------------------------------------------------------


class ConjunctionCompiler:
    """Compiles a conjunction of body atoms into Worker instructions."""

    def __init__(
        self,
        buffer_supply: BufferSupply,
        values_buffer_manager: ValuesBufferManager,
        union_dependency_sets_by_size: dict[int, UnionDependencySet] | None,
        extension_manager: ExtensionManager,
        body_atoms: list[Atom],
        head_variables: list[Variable],
    ) -> None:
        from hermit.model import NodeIDLessEqualThan, NodeIDsAscendingOrEqual

        self.m_buffer_supply = buffer_supply
        self.m_values_buffer_manager = values_buffer_manager
        self.m_extension_manager = extension_manager
        self.m_body_atoms = body_atoms
        self.m_variables: list[Variable] = []
        self.m_bound_so_far: set[Variable] = set()
        number_of_real_atoms = 0

        # Collect ALL variables from body and head first
        # This ensures all variables are available when compiling
        seen_variables: set[Variable] = set()
        for body_index in range(len(self.m_body_atoms)):
            atom = self.m_body_atoms[body_index]
            for argument_index in range(atom.arity()):
                variable = atom.get_argument_variable(argument_index)
                if variable is not None and variable not in seen_variables:
                    self.m_variables.append(variable)
                    seen_variables.add(variable)
            if atom.get_dl_predicate() != NodeIDLessEqualThan.INSTANCE and not isinstance(
                atom.get_dl_predicate(), NodeIDsAscendingOrEqual
            ):
                number_of_real_atoms += 1

        # Add head variables that haven't been seen yet
        for variable in head_variables:
            if variable not in seen_variables:
                self.m_variables.append(variable)
                seen_variables.add(variable)
        if union_dependency_sets_by_size is not None:
            uds = union_dependency_sets_by_size.get(number_of_real_atoms)
            if uds is None:
                uds = UnionDependencySet(number_of_real_atoms)
                union_dependency_sets_by_size[number_of_real_atoms] = uds
            self.m_union_dependency_set: UnionDependencySet | None = uds
        else:
            self.m_union_dependency_set = None
        self.m_retrievals: list[Retrieval] = []
        self.m_workers: list[Worker] = []
        self.m_labels: list[int | None] = []

    def generate_code(
        self, first_body_atom_to_compile: int, first_atom_retrieval: Retrieval
    ) -> None:
        """Generate the Worker instruction sequence."""
        self.m_labels.append(None)
        self.m_retrievals.append(first_atom_retrieval)
        after_rule = self._add_label()
        if first_body_atom_to_compile > 0:
            self._compile_check_unbound_variable_matches(
                self.m_body_atoms[0], first_atom_retrieval, after_rule
            )
            self._compile_generate_bindings(first_atom_retrieval, self.m_body_atoms[0])
            if self.m_union_dependency_set is not None:
                self.m_workers.append(
                    CopyDependencySet(
                        first_atom_retrieval,
                        self.m_union_dependency_set.m_dependency_sets,
                        0,
                    )
                )
        self._compile_body_atom(first_body_atom_to_compile, after_rule)
        self._set_label_program_counter(after_rule)
        for worker in self.m_workers:
            if isinstance(worker, BranchingWorker):
                branching_address = worker.get_branching_address()
                if branching_address < 0:
                    resolved_address = self.m_labels[-branching_address]
                    assert resolved_address is not None
                    worker.set_branching_address(resolved_address)

    def _occurs_in_body_atoms_after(self, variable: Variable, start_index: int) -> bool:
        """Check if *variable* occurs in body atoms after *start_index*."""
        for argument_index in range(start_index, len(self.m_body_atoms)):
            if self.m_body_atoms[argument_index].contains_variable(variable):
                return True
        return False

    def _compile_body_atom(self, body_atom_index: int, last_atom_next_element: int) -> None:
        """Compile a single body atom."""
        from hermit.model import NodeIDLessEqualThan, NodeIDsAscendingOrEqual

        if body_atom_index == len(self.m_body_atoms):
            self._compile_heads()
        elif self.m_body_atoms[body_atom_index].get_dl_predicate() == NodeIDLessEqualThan.INSTANCE:
            atom = self.m_body_atoms[body_atom_index]
            variable1_index = self.m_variables.index(atom.get_argument_variable(0))
            variable2_index = self.m_variables.index(atom.get_argument_variable(1))
            self.m_workers.append(
                BranchIfNotNodeIDLessEqualThan(
                    last_atom_next_element,
                    self.m_values_buffer_manager.m_values_buffer,
                    variable1_index,
                    variable2_index,
                )
            )
            self._compile_body_atom(body_atom_index + 1, last_atom_next_element)
        elif isinstance(
            self.m_body_atoms[body_atom_index].get_dl_predicate(),
            NodeIDsAscendingOrEqual,
        ):
            atom = self.m_body_atoms[body_atom_index]
            node_indexes = [0] * atom.arity()
            for index in range(atom.arity()):
                node_indexes[index] = self.m_variables.index(
                    atom.get_argument_variable(index)
                )
            self.m_workers.append(
                BranchIfNotNodeIDsAscendingOrEqual(
                    last_atom_next_element,
                    self.m_values_buffer_manager.m_values_buffer,
                    node_indexes,
                )
            )
            self._compile_body_atom(body_atom_index + 1, last_atom_next_element)
        else:
            # Each atom is compiled into:
            #   retrieval.open()
            # loopStart:   if (!retrieval.hasMore) goto afterLoop
            #              if (!retrieval.unboundVariableMatches) goto nextElement
            #              generate bindings
            #              copy dependency set
            #                  < next atom code >
            # nextElement: retrieval.next
            #              goto loopStart
            # afterLoop:
            after_loop = self._add_label()
            next_element = self._add_label()
            atom = self.m_body_atoms[body_atom_index]
            # binding_positions has one slot per tuple element (predicate + args + dep_set)
            # The extension table stores tuples as [predicate, arg0, ..., argN, dep_set]
            # slot_size in the retrieval = m_tuple_arity + 1, so we need that many positions
            ext_table = self.m_extension_manager.get_extension_table(atom.arity() + 1)
            slot_size = ext_table.m_tuple_arity + 1
            binding_positions = [-1] * slot_size
            binding_positions[0] = self.m_values_buffer_manager.m_body_dl_predicates_to_indexes[
                atom.get_dl_predicate()
            ]
            for argument_index in range(atom.arity()):
                term = atom.get_argument(argument_index)
                from hermit.model import Variable

                if isinstance(term, Variable):
                    if term in self.m_bound_so_far:
                        binding_positions[argument_index + 1] = self.m_variables.index(term)
                    else:
                        binding_positions[argument_index + 1] = -1
                else:
                    binding_positions[argument_index + 1] = (
                        self.m_values_buffer_manager.m_body_nonvariable_terms_to_indexes[term]
                    )
            # Last slot is dependency set — always unbound (-1)
            binding_positions[slot_size - 1] = -1
            retrieval = ext_table.create_retrieval(
                binding_positions,
                self.m_values_buffer_manager.m_values_buffer,
                self.m_buffer_supply.get_buffer(ext_table.m_tuple_arity),
                False,
                "EXTENSION_THIS",
            )
            self.m_retrievals.append(retrieval)
            self.m_workers.append(OpenRetrieval(retrieval))
            loop_start = len(self.m_workers)
            self.m_workers.append(HasMoreRetrieval(after_loop, retrieval))
            self._compile_check_unbound_variable_matches(atom, retrieval, next_element)
            self._compile_generate_bindings(retrieval, atom)
            if self.m_union_dependency_set is not None:
                self.m_workers.append(
                    CopyDependencySet(
                        retrieval,
                        self.m_union_dependency_set.m_dependency_sets,
                        len(self.m_retrievals) - 1,
                    )
                )
            self._compile_body_atom(body_atom_index + 1, next_element)
            self._set_label_program_counter(next_element)
            self.m_workers.append(NextRetrieval(retrieval))
            self.m_workers.append(JumpTo(loop_start))
            self._set_label_program_counter(after_loop)

    def _compile_check_unbound_variable_matches(
        self, atom: Atom, retrieval: Retrieval, jump_index: int
    ) -> None:
        """Add workers that check unbound variables match within an atom."""
        for outer_argument_index in range(atom.arity()):
            variable = atom.get_argument_variable(outer_argument_index)
            if variable is not None and variable not in self.m_bound_so_far:
                for inner_argument_index in range(
                    outer_argument_index + 1, atom.arity()
                ):
                    if variable == atom.get_argument(inner_argument_index):
                        self.m_workers.append(
                            BranchIfNotEqual(
                                jump_index,
                                retrieval.get_tuple_buffer(),
                                outer_argument_index + 1,
                                inner_argument_index + 1,
                            )
                        )

    def _compile_generate_bindings(
        self, retrieval: Retrieval, atom: Atom
    ) -> None:
        """Add workers that copy unbound variables from retrieval to values buffer."""
        for argument_index in range(atom.arity()):
            variable = atom.get_argument_variable(argument_index)
            if variable is not None and variable not in self.m_bound_so_far:
                try:
                    variable_index = self.m_variables.index(variable)
                except ValueError:
                    # Variable not yet in m_variables, skip it
                    # (This can happen for variables that only appear in the head)
                    continue
                if variable_index != -1:
                    self.m_workers.append(
                        CopyValues(
                            retrieval.get_tuple_buffer(),
                            argument_index + 1,
                            self.m_values_buffer_manager.m_values_buffer,
                            variable_index,
                        )
                    )
                    self.m_bound_so_far.add(variable)

    def _add_label(self) -> int:
        """Add a forward label and return its negative ID."""
        label_index = len(self.m_labels)
        self.m_labels.append(None)
        return -label_index

    def _set_label_program_counter(self, label_id: int) -> None:
        """Resolve a label to the current program counter."""
        self.m_labels[-label_id] = len(self.m_workers)

    @abstractmethod
    def _compile_heads(self) -> None:
        """Compile the head atoms (implemented by subclass)."""
        ...


class _DLClauseCompiler(ConjunctionCompiler):
    """Compiles DL clause bodies and heads into Workers."""

    def __init__(
        self,
        buffer_supply: BufferSupply,
        values_buffer_manager: ValuesBufferManager,
        ground_disjunction_header_manager: GroundDisjunctionHeaderManager,
        union_dependency_sets_by_size: dict[int, UnionDependencySet],
        dl_clause_evaluator: DLClauseEvaluator,
        extension_manager: ExtensionManager,
        existential_expansion_strategy: object,
        body_dl_clause: DLClause,
        head_dl_clauses: list[DLClause],
        first_atom_retrieval: Retrieval,
    ) -> None:
        body_atoms = body_dl_clause.get_body_atoms()
        head_variables = _get_head_variables(head_dl_clauses)
        super().__init__(
            buffer_supply,
            values_buffer_manager,
            union_dependency_sets_by_size,
            extension_manager,
            body_atoms,
            head_variables,
        )
        self.m_dl_clause_evaluator = dl_clause_evaluator
        self.m_ground_disjunction_header_manager = ground_disjunction_header_manager
        self.m_existential_expansion_strategy = existential_expansion_strategy
        self.m_body_dl_clause = body_dl_clause
        self.m_head_dl_clauses = head_dl_clauses
        self.m_core_variables: list[bool] = [False] * len(self.m_variables)
        self.generate_code(1, first_atom_retrieval)

    def _compile_heads(self) -> None:
        """Compile the head atoms of the DL clause."""
        # Notify the expansion strategy about compilation
        self.m_existential_expansion_strategy.dl_clause_body_compiled(  # type: ignore[attr-defined]  # Java-ported duck typing: strategy may or may not have this method
            self.m_workers,
            self.m_body_dl_clause,
            self.m_variables,
            self.m_values_buffer_manager.m_values_buffer,
            self.m_core_variables,
        )
        for dl_clause_index in range(len(self.m_head_dl_clauses)):
            if self.m_extension_manager.m_tableau_monitor is not None:
                self.m_workers.append(
                    CallMatchStartedOnMonitor(
                        self.m_extension_manager.m_tableau_monitor,
                        self.m_dl_clause_evaluator,
                        dl_clause_index,
                    )
                )
            if self.m_head_dl_clauses[dl_clause_index].get_head_length() == 0:
                self.m_workers.append(
                    SetClash(
                        self.m_extension_manager,
                        self.m_union_dependency_set,  # type: ignore[arg-type]
                    )
                )
            elif self.m_head_dl_clauses[dl_clause_index].get_head_length() == 1:
                atom = self.m_head_dl_clauses[dl_clause_index].get_head_atom(0)
                arity = atom.arity()
                if arity == 1:
                    variable = atom.get_argument_variable(0)
                    variable_index = self.m_variables.index(variable)
                    self.m_workers.append(
                        DeriveUnaryFact(
                            self.m_extension_manager,
                            self.m_values_buffer_manager.m_values_buffer,
                            self.m_core_variables,
                            self.m_union_dependency_set,  # type: ignore[arg-type]
                            atom.get_dl_predicate(),
                            variable_index,
                        )
                    )
                elif arity == 2:
                    var0 = atom.get_argument_variable(0)
                    var1 = atom.get_argument_variable(1)
                    self.m_workers.append(
                        DeriveBinaryFact(
                            self.m_extension_manager,
                            self.m_values_buffer_manager.m_values_buffer,
                            self.m_union_dependency_set,  # type: ignore[arg-type]
                            atom.get_dl_predicate(),
                            self.m_variables.index(var0),
                            self.m_variables.index(var1),
                        )
                    )
                elif arity == 3:
                    var0 = atom.get_argument_variable(0)
                    var1 = atom.get_argument_variable(1)
                    var2 = atom.get_argument_variable(2)
                    self.m_workers.append(
                        DeriveTernaryFact(
                            self.m_extension_manager,
                            self.m_values_buffer_manager.m_values_buffer,
                            self.m_union_dependency_set,  # type: ignore[arg-type]
                            atom.get_dl_predicate(),
                            self.m_variables.index(var0),
                            self.m_variables.index(var1),
                            self.m_variables.index(var2),
                        )
                    )
                else:
                    raise ValueError("Unsupported atom arity.")
            else:
                total_number_of_arguments = 0
                head_length = self.m_head_dl_clauses[dl_clause_index].get_head_length()
                for head_index in range(head_length):
                    total_number_of_arguments += self.m_head_dl_clauses[
                        dl_clause_index
                    ].get_head_atom(head_index).arity()
                head_dl_predicates: list[DLPredicate] = [None] * head_length  # type: ignore[list-item]
                copy_is_core = [0] * head_length
                copy_values_to_arguments = [0] * total_number_of_arguments
                index = 0
                for head_index in range(head_length):
                    head_atom = self.m_head_dl_clauses[dl_clause_index].get_head_atom(
                        head_index
                    )
                    head_dl_predicates[head_index] = head_atom.get_dl_predicate()
                    for argument_index in range(head_atom.arity()):
                        variable = head_atom.get_argument_variable(argument_index)
                        variable_index = self.m_variables.index(variable)
                        copy_values_to_arguments[index] = variable_index
                        index += 1
                    if head_dl_predicates[head_index].arity() == 1:
                        variable = head_atom.get_argument_variable(0)
                        copy_is_core[head_index] = self.m_variables.index(variable)
                    else:
                        copy_is_core[head_index] = -1
                ground_disjunction_header = (
                    self.m_ground_disjunction_header_manager.get(head_dl_predicates)
                )
                self.m_workers.append(
                    DeriveDisjunction(
                        self.m_values_buffer_manager.m_values_buffer,
                        self.m_core_variables,
                        self.m_union_dependency_set,  # type: ignore[arg-type]
                        self.m_extension_manager.m_tableau,
                        ground_disjunction_header,
                        copy_is_core,
                        copy_values_to_arguments,
                    )
                )
            if self.m_extension_manager.m_tableau_monitor is not None:
                self.m_workers.append(
                    CallMatchFinishedOnMonitor(
                        self.m_extension_manager.m_tableau_monitor,
                        self.m_dl_clause_evaluator,
                        dl_clause_index,
                    )
                )


def _get_head_variables(head_dl_clauses: list[DLClause]) -> list[Any]:
    """Extract all variables from head atoms."""
    result: list[Any] = []
    for dl_clause in head_dl_clauses:
        for head_index in range(dl_clause.get_head_length()):
            atom = dl_clause.get_head_atom(head_index)
            for argument_index in range(atom.arity()):
                variable = atom.get_argument_variable(argument_index)
                if variable is not None and variable not in result:
                    result.append(variable)
    return result
