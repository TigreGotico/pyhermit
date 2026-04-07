"""Datalog engine for ABox materialization and conjunctive query evaluation.

Provides:
- QueryResultCollector: interface for collecting query results
- DatalogEngine: materializes the ABox and manages term/node mappings
- ConjunctiveQuery: evaluates conjunctive queries over materialized ABox
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hermit.model import DLOntology
    from hermit.tableau.extension_manager import ExtensionManager


class QueryResultCollector(ABC):
    """Abstract base class for collecting conjunctive query results."""

    @abstractmethod
    def process_result(self, query: ConjunctiveQuery, result: list[Any]) -> None:
        """Process a query result.

        Args:
            query: The query that produced this result
            result: List of answer terms
        """
        pass


class DatalogEngine:
    """Materializes the ABox and provides term/node mappings for query evaluation."""

    def __init__(self, dl_ontology: DLOntology) -> None:
        """Initialize the Datalog engine.

        Args:
            dl_ontology: The DL ontology to materialize

        Raises:
            ValueError: If any DL clause has a disjunctive head
        """
        # Validate: no disjunctive heads allowed
        for dl_clause in dl_ontology.dl_clauses:
            if len(dl_clause.head_atoms) > 1:
                raise ValueError(
                    "Datalog engine does not support disjunctive clause heads"
                )

        self.dl_ontology = dl_ontology
        self.terms_to_nodes: dict[Any, Any] = {}
        self.nodes_to_terms: dict[Any, Any] = {}
        self.terms_to_equivalence_classes: dict[Any, set[Any]] = {}
        self.terms_to_representatives: dict[Any, Any] = {}
        self.extension_manager: ExtensionManager | None = None
        self._materialized = False

    def materialize(self) -> bool:
        """Materialize the ABox via tableau reasoning.

        Returns:
            True if consistent, False if unsatisfiable
        """
        if not self._materialized:
            # Import here to avoid circular dependency
            from hermit.tableau.tableau import Tableau

            # Create tableau with null existential expansion (no new nodes)
            tableau = Tableau(
                interrupt_flag=None,  # type: ignore[arg-type]
                blocking_strategy=None,
                existential_strategy=_NullExistentialExpansionStrategy(),
                use_model_completion=False,
                dl_ontology=self.dl_ontology,
            )

            # Materialize: run tableau to fixpoint
            is_consistent = tableau.is_satisfiable(
                load_permanent_abox=True,
                final_check=False,
            )

            if is_consistent:
                self.extension_manager = tableau.extension_manager
                self._build_term_mappings(tableau)
                self._materialized = True

            return is_consistent
        return self.extension_manager is not None

    def _build_term_mappings(self, tableau: Any) -> None:
        """Build term/node mappings from tableau nodes.

        Args:
            tableau: The tableau containing the nodes
        """
        # Map nodes from tableau to terms
        for term, node in self.terms_to_nodes.items():
            canonical_node = node.canonical_node
            canonical_term = self.nodes_to_terms.get(canonical_node)

            if canonical_term is None:
                # First time seeing this canonical node
                canonical_term = term
                self.nodes_to_terms[canonical_node] = term

            # Build equivalence class
            eq_class = self.terms_to_equivalence_classes.get(canonical_term)
            if eq_class is None:
                eq_class = set()
                self.terms_to_equivalence_classes[canonical_term] = eq_class

            eq_class.add(term)
            self.terms_to_representatives[term] = canonical_term

    def get_equivalence_class(self, term: Any) -> set[Any] | None:
        """Get the equivalence class of a term.

        Args:
            term: The term to look up

        Returns:
            Set of equivalent terms, or None if not found
        """
        return self.terms_to_equivalence_classes.get(term)

    def get_representative(self, term: Any) -> Any | None:
        """Get the canonical representative of a term.

        Args:
            term: The term to look up

        Returns:
            The representative term, or None if not found
        """
        return self.terms_to_representatives.get(term)


class ConjunctiveQuery:
    """Evaluates conjunctive queries over a materialized ABox."""

    def __init__(
        self,
        datalog_engine: DatalogEngine,
        query_atoms: list[Any],
        answer_terms: list[Any],
    ) -> None:
        """Initialize a conjunctive query.

        Args:
            datalog_engine: The Datalog engine providing materialized data
            query_atoms: Atoms in the query body
            answer_terms: Terms to return in results

        Raises:
            ValueError: If the ontology is unsatisfiable
        """
        if not datalog_engine.materialize():
            raise ValueError("Cannot query unsatisfiable ontology")

        self.datalog_engine = datalog_engine
        self.query_atoms = query_atoms
        self.answer_terms = answer_terms
        self.result_buffer = list(answer_terms)

    def evaluate(self, collector: QueryResultCollector) -> None:
        """Evaluate the query and pass results to collector.

        Args:
            collector: Callback to process each result
        """
        # For now, simplified implementation
        # A full implementation would use DLClauseEvaluator workers
        # to systematically search for all satisfying bindings

        # Simple case: if no query atoms, return empty binding
        if not self.query_atoms:
            collector.process_result(self, self.result_buffer)

    def get_query_atom_count(self) -> int:
        """Get the number of atoms in the query."""
        return len(self.query_atoms)

    def get_query_atom(self, index: int) -> Any:
        """Get a query atom by index."""
        return self.query_atoms[index]

    def get_answer_term_count(self) -> int:
        """Get the number of answer terms."""
        return len(self.answer_terms)

    def get_answer_term(self, index: int) -> Any:
        """Get an answer term by index."""
        return self.answer_terms[index]


class _NullExistentialExpansionStrategy:
    """Expansion strategy that doesn't expand existentials.

    Used by DatalogEngine to materialize without creating new nodes.
    This ensures the reasoning is exact (no completeness loss via blocking).
    """

    def initialize(self, tableau: Any) -> None:
        """Initialize (no-op)."""
        pass

    def additional_dl_ontology_set(self, dl_ontology: Any) -> None:
        """Handle additional ontology (no-op)."""
        pass

    def additional_dl_ontology_cleared(self) -> None:
        """Handle ontology cleared (no-op)."""
        pass

    def clear(self) -> None:
        """Clear state (no-op)."""
        pass

    def expand_existentials(self, final_chance: bool) -> bool:
        """Expand existentials (always returns False - no expansion)."""
        return False

    def assertion_added_concept(
        self, concept: Any, node: Any, is_core: bool
    ) -> None:
        """Handle assertion added (no-op)."""
        pass

    def assertion_core_set_concept(self, concept: Any, node: Any) -> None:
        """Handle core flag set (no-op)."""
        pass

    def assertion_removed_concept(
        self, concept: Any, node: Any, is_core: bool
    ) -> None:
        """Handle assertion removed (no-op)."""
        pass

    def assertion_added_data_range(
        self, data_range: Any, node: Any, is_core: bool
    ) -> None:
        """Handle assertion added (no-op)."""
        pass

    def assertion_core_set_data_range(self, data_range: Any, node: Any) -> None:
        """Handle core flag set (no-op)."""
        pass

    def assertion_removed_data_range(
        self, data_range: Any, node: Any, is_core: bool
    ) -> None:
        """Handle assertion removed (no-op)."""
        pass

    def assertion_added_atomic_role(
        self, role: Any, from_node: Any, to_node: Any, is_core: bool
    ) -> None:
        """Handle role assertion added (no-op)."""
        pass

    def assertion_core_set_atomic_role(
        self, role: Any, from_node: Any, to_node: Any
    ) -> None:
        """Handle role assertion core set (no-op)."""
        pass

    def assertion_removed_atomic_role(
        self, role: Any, from_node: Any, to_node: Any, is_core: bool
    ) -> None:
        """Handle role assertion removed (no-op)."""
        pass

    def nodes_merged(self, from_node: Any, to_node: Any) -> None:
        """Handle nodes merged (no-op)."""
        pass

    def nodes_unmerged(self, from_node: Any, to_node: Any) -> None:
        """Handle nodes unmerged (no-op)."""
        pass

    def node_status_changed(self, node: Any) -> None:
        """Handle node status changed (no-op)."""
        pass

    def node_initialized(self, node: Any) -> None:
        """Handle node initialized (no-op)."""
        pass

    def node_destroyed(self, node: Any) -> None:
        """Handle node destroyed (no-op)."""
        pass

    def branching_point_pushed(self) -> None:
        """Handle branching point pushed (no-op)."""
        pass

    def backtrack(self) -> None:
        """Handle backtracking (no-op)."""
        pass

    def model_found(self) -> None:
        """Handle model found (no-op)."""
        pass

    def is_deterministic(self) -> bool:
        """Is deterministic."""
        return True

    def is_exact(self) -> bool:
        """Is exact (no blocking needed)."""
        return True

    def dl_clause_body_compiled(
        self,
        workers: list[Any],
        dl_clause: Any,
        variables: list[Any],
        values_buffer: list[Any],
        core_variables: list[bool],
    ) -> None:
        """Handle DL clause compilation (no-op)."""
        pass


__all__ = [
    "ConjunctiveQuery",
    "DatalogEngine",
    "QueryResultCollector",
]
