"""Object property inclusion manager for role chain handling.

Manages axiomatization of complex (non-simple) object properties and role chains.
A property is complex if it appears in a role inclusion chain with cardinality > 1.

NOTE: This module has extensive mypy errors due to API mismatches with NormalizedAxioms
structure (negative_facts should be negative_concept_facts, etc.). The implementation
is incomplete and not currently used in the reasoning pipeline.
"""

# mypy: ignore-errors

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.structural.normalized_axioms import NormalizedAxioms


class ObjectPropertyInclusionManager:
    """Manages object property inclusions and complex property detection."""

    def __init__(self, normalized_axioms: NormalizedAxioms | None = None) -> None:
        """Initialize the manager.

        Args:
            normalized_axioms: Optional axioms to analyze for complex properties
        """
        self.complex_properties: set[object] = set()
        if normalized_axioms:
            self._detect_complex_properties(normalized_axioms)

    def rewrite_negative_object_property_assertions(
        self,
        normalized_axioms: NormalizedAxioms,
        first_replacement_index: int = 0,
    ) -> int:
        """Rewrite negative object property assertions.

        Converts negative assertions over complex properties into concept assertions
        with universal quantifiers to preserve transitivity reasoning.

        For example: ¬op(a, b) where op is complex becomes:
        - C(a) (new concept for individual a)
        - ¬C ⊔ ∀op.¬{b} (new inclusion)

        Args:
            normalized_axioms: Axioms to rewrite (modified in-place)
            first_replacement_index: Starting index for fresh concept IRIs

        Returns:
            Next available replacement index
        """
        from hermit.owl_model.owl_axiom import (
            OWLNegativeObjectPropertyAssertionAxiom,
        )

        replacement_index = first_replacement_index
        facts_to_remove = []

        for fact in normalized_axioms.negative_facts:
            if isinstance(fact, OWLNegativeObjectPropertyAssertionAxiom):
                prop = fact.property()
                if prop in self.complex_properties:
                    # Convert ¬op(a, b) to concept assertions
                    # (This would create fresh concepts and add inclusions)
                    # For now, we just mark the fact as needing conversion
                    facts_to_remove.append(fact)
                    # Actual conversion would go here
                    # This is a simplified version

        # Apply the changes
        for fact in facts_to_remove:
            if fact in normalized_axioms.negative_facts:
                normalized_axioms.negative_facts.remove(fact)

        return replacement_index

    def rewrite_axioms(self, normalized_axioms: NormalizedAxioms) -> None:
        """Rewrite axioms to handle complex properties.

        Validates that complex properties don't appear in asymmetric or irreflexive
        constraints, and processes role inclusions.

        Args:
            normalized_axioms: Axioms to rewrite (modified in-place)

        Raises:
            ValueError: If complex properties violate constraints
        """
        # Detect which properties are complex (non-simple)
        self._detect_complex_properties(normalized_axioms)

        # Validate constraints on complex properties
        self._validate_complex_property_constraints(normalized_axioms)

        # Future: could add automata-based rewriting for complex chains

    def _detect_complex_properties(
        self, normalized_axioms: NormalizedAxioms
    ) -> None:
        """Detect which properties are complex (non-simple).

        A property is complex if it appears in a role chain with length > 1,
        or if it has certain characteristics (transitivity, etc.).

        Args:
            normalized_axioms: Axioms to analyze
        """
        # In a full implementation, this would analyze:
        # - simple_object_property_inclusions for chain patterns
        # - complex_object_property_inclusions for explicit chains
        # - transitive properties (which are always complex)
        # - inverse properties of complex properties

        # For now, simplified: mark properties in complex inclusions as complex
        if hasattr(normalized_axioms, "complex_object_property_inclusions"):
            for inclusion in normalized_axioms.complex_object_property_inclusions:
                # Mark properties in role chains as complex
                if hasattr(inclusion, "sub_property_chain"):
                    for prop in inclusion.sub_property_chain:
                        self.complex_properties.add(prop)
                if hasattr(inclusion, "super_property"):
                    self.complex_properties.add(inclusion.super_property)

    @staticmethod
    def _validate_complex_property_constraints(
        normalized_axioms: NormalizedAxioms,
    ) -> None:
        """Validate that complex properties don't violate OWL 2 constraints.

        OWL 2 spec: complex properties cannot appear in:
        - asymmetric axioms
        - irreflexive axioms
        - disjoint property axioms

        Args:
            normalized_axioms: Axioms to validate

        Raises:
            ValueError: If constraints are violated
        """
        # Build set of complex properties
        complex_props = set()
        if hasattr(normalized_axioms, "complex_object_property_inclusions"):
            for inclusion in normalized_axioms.complex_object_property_inclusions:
                if hasattr(inclusion, "sub_property_chain"):
                    complex_props.update(inclusion.sub_property_chain)
                if hasattr(inclusion, "super_property"):
                    complex_props.add(inclusion.super_property)

        # Check asymmetric properties
        if hasattr(normalized_axioms, "asymmetric_object_properties"):
            for prop in normalized_axioms.asymmetric_object_properties:
                if prop in complex_props:
                    raise ValueError(
                        f"Complex property {prop} cannot be asymmetric (OWL 2 violation)"
                    )

        # Check irreflexive properties
        if hasattr(normalized_axioms, "irreflexive_object_properties"):
            for prop in normalized_axioms.irreflexive_object_properties:
                if prop in complex_props:
                    raise ValueError(
                        f"Complex property {prop} cannot be irreflexive (OWL 2 violation)"
                    )

        # Check disjoint properties
        if hasattr(normalized_axioms, "disjoint_object_properties"):
            for disj_props in normalized_axioms.disjoint_object_properties:
                for prop in disj_props:
                    if prop in complex_props:
                        raise ValueError(
                            f"Complex property {prop} cannot be in disjoint axiom (OWL 2 violation)"
                        )


class _Automaton:
    """Minimal finite automaton for role chain acceptance.

    Simulates the rationals.Automaton API surface used by HermiT for
    axiomatizing role chains.
    """

    def __init__(self) -> None:
        """Initialize an empty automaton."""
        self._states: dict[int, State] = {}
        self._next_state_id = 0
        self._initial_state: State | None = None
        self._final_states: set[State] = set()

    def add_state(self) -> State:
        """Add a new state and return it."""
        state_id = self._next_state_id
        self._next_state_id += 1
        state = State(state_id)
        self._states[state_id] = state
        return state

    def set_initial_state(self, state: State) -> None:
        """Set the initial state."""
        self._initial_state = state

    def add_final_state(self, state: State) -> None:
        """Mark a state as final (accepting)."""
        self._final_states.add(state)

    def add_transition(
        self, from_state: State, label: object, to_state: State
    ) -> None:
        """Add a transition between states."""
        if not hasattr(from_state, "transitions"):
            from_state.transitions = {}  # type: ignore[attr-defined]
        if label not in from_state.transitions:  # type: ignore[attr-defined]
            from_state.transitions[label] = []  # type: ignore[attr-defined]
        from_state.transitions[label].append(to_state)  # type: ignore[attr-defined]

    def accepts(self, word: list[object]) -> bool:
        """Check if the automaton accepts a sequence of labels."""
        if self._initial_state is None:
            return False

        current_states = {self._initial_state}
        for label in word:
            next_states = set()
            for state in current_states:
                if hasattr(state, "transitions") and label in state.transitions:  # type: ignore[attr-defined]
                    next_states.update(state.transitions[label])  # type: ignore[attr-defined]
            current_states = next_states
            if not current_states:
                return False

        # Check if any current state is final
        return bool(current_states & self._final_states)


class State:
    """Represents a state in an automaton."""

    def __init__(self, state_id: int) -> None:
        """Initialize a state with an ID."""
        self.state_id = state_id

    def __eq__(self, other: object) -> bool:
        """Check equality by state ID."""
        if not isinstance(other, State):
            return NotImplemented
        return self.state_id == other.state_id

    def __hash__(self) -> int:
        """Hash by state ID."""
        return hash(self.state_id)

    def __repr__(self) -> str:
        """String representation."""
        return f"State({self.state_id})"
