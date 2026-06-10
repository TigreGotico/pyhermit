"""Object property inclusion manager for role chain handling.

Manages axiomatization of complex (non-simple) object properties and role chains.
A property is non-simple if it is transitive, appears as the superrole of a role
chain, or is a superrole (via SubObjectPropertyOf) of any such property; the set
is closed under inverses.

Called by OWLClausification.clausify() before producing DL clauses for two
purposes:

1. Enforce OWL 2 spec Section 11.2: non-simple properties may not appear in
   cardinality restrictions, hasSelf, asymmetric, irreflexive, or disjoint
   axioms. The check is syntactic, as in the Java original: only min/max/exact
   cardinality restriction syntax is restricted — someValuesFrom over a
   non-simple property is legal even though it normalizes to the same internal
   at-least form.
2. Give role chains and transitivity their tableau semantics: every universal
   restriction over a non-simple role is unfolded through the role's automaton
   (see ``hermit.structural.role_automaton``), the port of the Java
   ``rewriteAxioms`` automaton-state rewriting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from hermit.model import AtomicConcept, DLClause
    from hermit.structural.normalized_axioms import NormalizedAxioms
    from hermit.structural.role_automaton import Automaton


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
        new_positive_concept_facts: list[tuple[Individual, AtomicConcept]] = []

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
                inv = cp.get_inverse()
                if isinstance(inv, AtomicRole):
                    complex_prop_iris[inv.iri] = cp

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
                Atom.create(role_pred, var_x, var_y),  # type: ignore[arg-type]
            )
            new_clauses.append(DLClause.create((head_atom,), body_atoms))
            facts_to_remove.append(fact)

        # Apply removals and additions
        for fact in facts_to_remove:
            if fact in normalized_axioms.negative_facts:
                normalized_axioms.negative_facts.remove(fact)

        normalized_axioms.positive_concept_facts.extend(new_positive_concept_facts)

        if hasattr(normalized_axioms, "dl_clauses"):
            normalized_axioms.dl_clauses.extend(new_clauses)
        elif hasattr(normalized_axioms, "rules"):
            # Store in positive_facts for later clausification
            for clause in new_clauses:
                normalized_axioms.positive_facts.append(clause)

        return replacement_index

    def rewrite_axioms(self, normalized_axioms: NormalizedAxioms) -> None:
        """Rewrite axioms to handle complex properties.

        Validates that complex properties don't appear in asymmetric or
        irreflexive constraints, and unfolds every universal restriction over
        a non-simple role through that role's automaton.

        Args:
            normalized_axioms: Axioms to rewrite (modified in-place)

        Raises:
            ValueError: If complex properties violate constraints or the
                property hierarchy is not regular
        """
        # Detect which properties are complex (non-simple)
        self._detect_complex_properties(normalized_axioms)

        # Validate constraints on complex properties
        self._validate_complex_property_constraints(normalized_axioms)

        # Replace universals over non-simple roles by automaton unfoldings
        self._rewrite_universals_over_automata(normalized_axioms)

    def _rewrite_universals_over_automata(
        self, normalized_axioms: NormalizedAxioms
    ) -> None:
        """Unfold every ∀R.C over a non-simple role R through R's automaton.

        Port of the rewriting in Java ``rewriteAxioms``: each distinct pair
        (R, C) with an automaton for R gets one fresh concept per automaton
        state (the initial state's concept replaces the universal); every
        transition ``s --S--> t`` yields ``Q_t(Y) :- Q_s(X), S(X,Y)`` (an
        ε-move yields ``Q_t(X) :- Q_s(X)``) and every accepting state implies
        the filler. The originally emitted two-variable clause for the
        universal is removed — its effect is subsumed by the automaton's
        ``initial --R--> final`` transition.
        """
        from hermit.model import (
            Atom,
            AtomicConcept,
            AtomicNegationConcept,
            DLClause,
            Variable,
        )
        from hermit.structural.role_automaton import build_role_automata

        records = normalized_axioms.all_values_from_records
        if not records:
            return
        automata, _complex = build_role_automata(
            normalized_axioms.simple_object_property_inclusions,
            normalized_axioms.complex_object_property_inclusions,
        )

        x_var = Variable.create("X")
        counter = 0

        def _fresh() -> AtomicConcept:
            nonlocal counter
            concept = AtomicConcept.create(f"internal:all#{counter}")
            counter += 1
            return concept

        replaced: dict[tuple[object, object], AtomicConcept] = {}
        new_clauses: list[DLClause] = []
        for guard, role, filler, clause in records:
            automaton = automata.get(role)
            if automaton is None:
                continue
            if isinstance(filler, AtomicConcept) and filler.is_always_true():
                continue
            try:
                normalized_axioms.direct_dl_clauses.remove(clause)
            except ValueError:
                pass
            key = (role, filler)
            initial_concept = replaced.get(key)
            if initial_concept is None:
                initial_concept = _fresh()
                replaced[key] = initial_concept
                self._emit_automaton_clauses(
                    automaton, initial_concept, filler, new_clauses, _fresh
                )
            # Entry clause: the universal's guard implies the initial state.
            body_atoms: list[Atom] = []
            if isinstance(guard, AtomicNegationConcept):
                body_atoms.append(Atom.create(guard.negated, x_var))
            elif hasattr(guard, "arity") or hasattr(guard, "accept"):
                body_atoms.append(Atom.create(guard, x_var))  # type: ignore[arg-type]
            new_clauses.append(
                DLClause.create(
                    (Atom.create(initial_concept, x_var),), tuple(body_atoms)
                )
            )
        normalized_axioms.direct_dl_clauses.extend(new_clauses)

    @staticmethod
    def _emit_automaton_clauses(
        automaton: Automaton,
        initial_concept: AtomicConcept,
        filler: object,
        out_clauses: list[DLClause],
        fresh: Callable[[], AtomicConcept],
    ) -> None:
        """Emit the DL clauses encoding one role automaton for one filler."""
        from hermit.model import (
            Atom,
            AtomicConcept,
            AtomicNegationConcept,
            DLClause,
            Variable,
        )
        from hermit.structural.owl_clausification import _role_atom

        x_var = Variable.create("X")
        y_var = Variable.create("Y")

        state_concepts: dict[int, AtomicConcept] = {}
        for state in automaton.states():
            state_concepts[id(state)] = (
                initial_concept if automaton.is_initial(state) else fresh()
            )
        for transition in automaton.delta():
            from_atom = Atom.create(state_concepts[id(transition.start)], x_var)
            to_concept = state_concepts[id(transition.end)]
            if transition.label is None:
                out_clauses.append(
                    DLClause.create((Atom.create(to_concept, x_var),), (from_atom,))
                )
            else:
                out_clauses.append(
                    DLClause.create(
                        (Atom.create(to_concept, y_var),),
                        (from_atom, _role_atom(transition.label, x_var, y_var)),
                    )
                )
        for final_state in automaton.terminals():
            final_atom = Atom.create(state_concepts[id(final_state)], x_var)
            if isinstance(filler, AtomicNegationConcept):
                out_clauses.append(
                    DLClause.create(
                        (), (final_atom, Atom.create(filler.negated, x_var))
                    )
                )
            elif isinstance(filler, AtomicConcept) and filler.is_always_false():
                out_clauses.append(DLClause.create((), (final_atom,)))
            elif isinstance(filler, AtomicConcept):
                out_clauses.append(
                    DLClause.create((Atom.create(filler, x_var),), (final_atom,))
                )

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
        for cprop in list(complex_set):
            complex_set.add(_get_inverse(cprop))
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
        normalized_axioms: NormalizedAxioms, complex_props: set[object]
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

        def _check_expr(expr: object) -> None:
            """Recursively check a class expression for non-simple violations.

            The check is syntactic, mirroring the Java original: only OWL-level
            cardinality restrictions (min/max/exact) and Self restrictions are
            inspected. Internal AtLeastConcept/AtMostConcept forms are NOT
            checked here because existential restrictions (legal on non-simple
            properties) convert to the same AtLeastConcept shape; roles from
            syntactic cardinality restrictions are validated via
            ``cardinality_restriction_roles`` instead.
            """
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
            # Recurse into unions/intersections
            operands = getattr(expr, "_operands", None) or []
            operands_fn = getattr(expr, "operands", None)
            if callable(operands_fn):
                operands = list(operands_fn())
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

        # cardinality_restriction_roles: roles from syntactic object cardinality
        # restrictions (min/max/exact) recorded during OWL→internal conversion.
        # Roles that only occur in someValuesFrom never register here, so a
        # non-simple property under an existential restriction is accepted.
        for role in normalized_axioms.cardinality_restriction_roles:
            if role in complex_props:
                raise ValueError(
                    f"Non-simple property '{role}' or its inverse appears in "
                    f"a cardinality restriction (OWL 2 violation)"
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
                transitions = getattr(state, "transitions", None)
                if transitions is not None and label in transitions:
                    next_states.update(transitions[label])
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
