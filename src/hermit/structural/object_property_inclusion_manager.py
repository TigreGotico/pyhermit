"""Object property inclusion manager for role chain handling.

Manages axiomatization of complex (non-simple) object properties and role chains.
A property is non-simple if it is transitive, appears as the superrole of a role
chain, or is a superrole (via SubObjectPropertyOf) of any such property.

Called by OWLClausification.clausify() before producing DL clauses to enforce
OWL 2 spec Section 11.2: non-simple properties may not appear in cardinality
restrictions, hasSelf, asymmetric, irreflexive, or disjoint axioms.
"""

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

        from hermit.model import AtomicConcept, Atom, DLClause, Individual, Variable

        replacement_index = first_replacement_index
        facts_to_remove = []
        new_clauses: list[DLClause] = []
        new_positive_concept_facts: list[tuple] = []

        var_x = Variable.create("X")
        var_y = Variable.create("Y")

        from hermit.model import AtomicRole, InverseRole, Inequality

        def _iri_str(owl_obj: object) -> str | None:
            """Extract IRI string from an OWL model object."""
            iri = getattr(owl_obj, "iri", None)
            if iri is None:
                return None
            if isinstance(iri, str):
                return iri
            # IRI object — use as_str() if available, else str()
            as_str = getattr(iri, "as_str", None)
            return as_str() if callable(as_str) else str(iri)

        # Build IRI → internal Role lookup for complex properties
        complex_prop_iris: dict[str, object] = {}
        for cp in self.complex_properties:
            if isinstance(cp, AtomicRole):
                complex_prop_iris[cp.iri] = cp
            elif isinstance(cp, InverseRole):
                complex_prop_iris[cp.get_inverse().iri] = cp

        for fact in normalized_axioms.negative_facts:
            if not isinstance(fact, OWLNegativeObjectPropertyAssertionAxiom):
                continue
            owl_prop = fact.get_property()
            prop_iri = _iri_str(owl_prop)
            if prop_iri is None or prop_iri not in complex_prop_iris:
                continue

            # ¬op(a, b) where op is complex:
            # Introduce fresh concept F_i, add F_i(a) and clause
            # F_i(X) ∧ op(X, Y) → Y ≠ b
            owl_subj = fact.get_subject()
            owl_obj = fact.get_object()
            subj_iri = _iri_str(owl_subj)
            obj_iri = _iri_str(owl_obj)
            if subj_iri is None or obj_iri is None:
                continue

            subject_ind = Individual.create(subj_iri)
            obj_ind = Individual.create(obj_iri)
            role_pred = complex_prop_iris[prop_iri]

            fresh_iri = f"internal:negated-property-replacement#{replacement_index}"
            fresh_concept = AtomicConcept.create(fresh_iri)
            replacement_index += 1

            # Positive concept fact: F_i(a)
            new_positive_concept_facts.append((subject_ind, fresh_concept))

            # DL clause: F_i(X) ∧ op(X, Y) → Y ≠ obj
            head_atom = Atom.create(Inequality.INSTANCE, var_y, obj_ind)
            body_atoms = (
                Atom.create(fresh_concept, var_x),
                Atom.create(role_pred, var_x, var_y),
            )
            new_clauses.append(DLClause.create((head_atom,), body_atoms))
            facts_to_remove.append(fact)

        # Apply removals and additions
        for fact in facts_to_remove:
            if fact in normalized_axioms.negative_facts:
                normalized_axioms.negative_facts.remove(fact)

        normalized_axioms.positive_concept_facts.extend(new_positive_concept_facts)

        if hasattr(normalized_axioms, "dl_clauses"):
            normalized_axioms.dl_clauses.extend(new_clauses)  # type: ignore[attr-defined]
        elif hasattr(normalized_axioms, "rules"):
            # Store in positive_facts for later clausification
            for clause in new_clauses:
                normalized_axioms.positive_facts.append(clause)

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
        """Detect the full set of non-simple (complex) object properties.

        Mirrors Java's ObjectPropertyInclusionManager.createAutomata():

        1. Directly complex: properties appearing in complex_object_property_inclusions
           (transitivity R∘R⊑R, or chains R1∘...∘Rn⊑S).
        2. Indirectly complex: superroles of complex properties via simple inclusions
           (if R complex and R⊑P, then P complex).
        3. Inverses of complex properties are also complex.
        """
        from hermit.model import AtomicRole, InverseRole

        # Step 1: seed with directly complex properties
        directly_complex: set[object] = set()
        for inclusion in normalized_axioms.complex_object_property_inclusions:
            # The super-property of any chain is complex
            directly_complex.add(inclusion.super_object_property)
            # Chain members that are the same as super (transitivity) are also complex
            for prop in inclusion.sub_object_properties:
                if prop == inclusion.super_object_property:
                    directly_complex.add(prop)

        def _get_inverse(prop: object) -> object:
            if isinstance(prop, AtomicRole):
                return InverseRole.create(prop)
            elif isinstance(prop, InverseRole):
                return prop.get_inverse()
            return prop

        # Step 2+3: fixpoint — propagate through simple inclusions and
        # always add inverses of complex properties until stable
        complex_set = set(directly_complex)
        # seed inverses of initial complex properties
        for prop in list(complex_set):
            complex_set.add(_get_inverse(prop))
        changed = True
        while changed:
            changed = False
            for (sub, sup) in normalized_axioms.simple_object_property_inclusions:
                if sub in complex_set and sup not in complex_set:
                    complex_set.add(sup)
                    complex_set.add(_get_inverse(sup))
                    changed = True

        self.complex_properties.update(complex_set)

    def _validate_complex_property_constraints(
        self, normalized_axioms: NormalizedAxioms
    ) -> None:
        """Validate that non-simple properties don't violate OWL 2 constraints.

        OWL 2 spec: non-simple properties cannot appear in:
        - asymmetric axioms
        - irreflexive axioms
        - disjoint property axioms
        - cardinality restrictions (min, max, exact)
        - hasSelf restrictions

        Raises:
            ValueError: If constraints are violated
        """
        complex_props = self.complex_properties

        def _is_complex(role: object) -> bool:
            return role in complex_props

        # Check asymmetric properties
        for prop in normalized_axioms.asymmetric_object_properties:
            if _is_complex(prop):
                raise ValueError(
                    f"Non-simple property '{prop}' cannot be asymmetric (OWL 2 violation)"
                )

        # Check irreflexive properties
        for prop in normalized_axioms.irreflexive_object_properties:
            if _is_complex(prop):
                raise ValueError(
                    f"Non-simple property '{prop}' cannot be irreflexive (OWL 2 violation)"
                )

        # Check disjoint properties
        for disj_props in normalized_axioms.disjoint_object_properties:
            for prop in disj_props:
                if _is_complex(prop):
                    raise ValueError(
                        f"Non-simple property '{prop}' cannot be in disjoint properties axiom (OWL 2 violation)"
                    )

        # Check cardinality restrictions and hasSelf in concept inclusions
        self._check_concept_inclusions_for_non_simple(normalized_axioms, complex_props)

    @staticmethod
    def _check_concept_inclusions_for_non_simple(
        normalized_axioms: NormalizedAxioms, complex_props: set
    ) -> None:
        """Scan concept inclusions for non-simple properties in cardinality/self restrictions."""
        from hermit.owl_model.class_expression.restriction import (
            OWLObjectCardinalityRestriction,
            OWLObjectHasSelf,
        )

        def _role_iri(owl_prop: object) -> str | None:
            """Get IRI string from an OWL property expression."""
            iri = getattr(owl_prop, "iri", None)
            if iri is None:
                return None
            return iri.as_str() if hasattr(iri, "as_str") else str(iri)

        def _is_non_simple_owl_prop(owl_prop: object) -> bool:
            """Check if an OWL property expression corresponds to a non-simple internal role."""
            from hermit.model import AtomicRole, InverseRole
            from hermit.owl_model.owl_property import OWLObjectInverseOf

            iri = _role_iri(owl_prop)
            if iri is None:
                return False
            if isinstance(owl_prop, OWLObjectInverseOf):
                base_iri = _role_iri(owl_prop.get_inverse())
                if base_iri is None:
                    return False
                inv_role = InverseRole.create(AtomicRole.create(base_iri))
                atomic_role = AtomicRole.create(base_iri)
                return inv_role in complex_props or atomic_role in complex_props
            else:
                atomic = AtomicRole.create(iri)
                inv = InverseRole.create(atomic)
                return atomic in complex_props or inv in complex_props

        def _is_non_simple_internal_role(role: object) -> bool:
            """Check if an internal model role is non-simple."""
            return role in complex_props

        def _check_expr(expr: object) -> None:
            """Recursively check a class expression for non-simple violations."""
            from hermit.model import AtLeastConcept as _AtLeastConcept

            if isinstance(expr, OWLObjectCardinalityRestriction):
                prop = expr.get_property()
                if _is_non_simple_owl_prop(prop):
                    raise ValueError(
                        f"Non-simple property '{prop}' or its inverse appears in "
                        f"the cardinality restriction '{expr}' (OWL 2 violation)"
                    )
            elif isinstance(expr, OWLObjectHasSelf):
                prop = expr.get_property()
                if _is_non_simple_owl_prop(prop):
                    raise ValueError(
                        f"Non-simple property '{prop}' appears in a Self restriction "
                        f"(OWL 2 violation)"
                    )
            elif isinstance(expr, _AtLeastConcept):
                # Already-converted internal model cardinality restriction
                role = expr._on_role  # type: ignore[attr-defined]
                if _is_non_simple_internal_role(role):
                    raise ValueError(
                        f"Non-simple property '{role}' appears in a cardinality "
                        f"restriction (OWL 2 violation)"
                    )
            # Recurse into unions/intersections
            operands = getattr(expr, "_operands", None) or []
            if callable(getattr(expr, "operands", None)):
                operands = list(expr.operands())
            for op in operands:
                _check_expr(op)

        # concept_inclusions stores tuple-of-expressions
        for inclusion in normalized_axioms.concept_inclusions:
            for expr in inclusion:
                _check_expr(expr)

        # positive_facts stores OWLObjectUnionOf / other OWL axioms/expressions
        from hermit.owl_model.class_expression import OWLObjectUnionOf as _OWLObjectUnionOf
        for fact in normalized_axioms.positive_facts:
            if isinstance(fact, _OWLObjectUnionOf):
                for op in fact.operands():
                    _check_expr(op)

        # max_cardinality_roles: roles from OWLObjectMaxCardinality after OWL→internal conversion
        for role in normalized_axioms.max_cardinality_roles:
            if _is_non_simple_internal_role(role):
                raise ValueError(
                    f"Non-simple property '{role}' appears in a max-cardinality "
                    f"restriction (OWL 2 violation)"
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
