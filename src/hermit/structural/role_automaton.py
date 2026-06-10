"""Finite automata over roles for complex object property inclusions.

Port of the automaton machinery in
``org.semanticweb.HermiT.structural.ObjectPropertyInclusionManager``
(``createAutomata`` and its helpers), together with the subset of the
``rationals`` library HermiT relies on (``Automaton``/``State``/``Transition``)
and ``org.semanticweb.HermiT.graph.Graph``.

Every non-simple object property R receives an automaton whose language is a
set of role words R1…Rn with R1 ∘ … ∘ Rn ⊑ R (always containing the word "R"
itself).  The clausification phase unfolds each universal restriction ∀R.C
through this automaton: automaton states become fresh concepts, transitions
become universal propagation clauses, and accepting states imply the filler.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hermit.model import AtomicRole

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from hermit.model import Role
    from hermit.structural.normalized_axioms import ComplexObjectPropertyInclusion


# ===========================================================================
# Automaton primitives
# ===========================================================================


class State:
    """An automaton state with identity semantics."""

    __slots__ = ("index",)

    def __init__(self, index: int) -> None:
        self.index = index

    def __repr__(self) -> str:
        return f"State({self.index})"


class Transition:
    """A transition ``start --label--> end``; ``label is None`` is an ε-move."""

    __slots__ = ("start", "label", "end")

    def __init__(self, start: State, label: Role | None, end: State) -> None:
        self.start = start
        self.label = label
        self.end = end

    def _key(self) -> tuple[int, Role | None, int]:
        return (id(self.start), self.label, id(self.end))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Transition):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self) -> int:
        return hash(self._key())

    def __repr__(self) -> str:
        return f"Transition({self.start!r}, {self.label!r}, {self.end!r})"


class Automaton:
    """A nondeterministic finite automaton over role labels.

    Mirrors the ``rationals.Automaton`` API surface used by HermiT: states are
    added with initial/terminal flags, transitions may carry ``None`` (ε)
    labels, and insertion order is preserved for deterministic output.
    """

    def __init__(self) -> None:
        self._states: list[State] = []
        self._initials: list[State] = []
        self._terminals: list[State] = []
        self._transitions: list[Transition] = []
        self._transition_set: set[Transition] = set()

    def add_state(self, initial: bool = False, terminal: bool = False) -> State:
        state = State(len(self._states))
        self._states.append(state)
        if initial:
            self._initials.append(state)
        if terminal:
            self._terminals.append(state)
        return state

    def add_transition(self, start: State, label: Role | None, end: State) -> None:
        transition = Transition(start, label, end)
        if transition not in self._transition_set:
            self._transition_set.add(transition)
            self._transitions.append(transition)

    def states(self) -> Sequence[State]:
        return self._states

    def initials(self) -> Sequence[State]:
        return self._initials

    def terminals(self) -> Sequence[State]:
        return self._terminals

    def delta(self) -> Sequence[Transition]:
        return self._transitions

    @property
    def initial(self) -> State:
        return self._initials[0]

    @property
    def terminal(self) -> State:
        return self._terminals[0]

    def delta_from(self, start: State, end: State) -> list[Transition]:
        return [
            t for t in self._transitions if t.start is start and t.end is end
        ]

    def is_initial(self, state: State) -> bool:
        return state in self._initials

    def is_terminal(self, state: State) -> bool:
        return state in self._terminals

    def clone(self) -> Automaton:
        copy = Automaton()
        mapping: dict[int, State] = {}
        for state in self._states:
            mapping[id(state)] = copy.add_state(
                self.is_initial(state), self.is_terminal(state)
            )
        for transition in self._transitions:
            copy.add_transition(
                mapping[id(transition.start)],
                transition.label,
                mapping[id(transition.end)],
            )
        return copy


def get_mirrored_copy(automaton: Automaton) -> Automaton:
    """Reverse all transitions, inverting labels and swapping initial/terminal."""
    mirrored = Automaton()
    mapping: dict[int, State] = {}
    for state in automaton.states():
        mapping[id(state)] = mirrored.add_state(
            automaton.is_terminal(state), automaton.is_initial(state)
        )
    for transition in automaton.delta():
        label = transition.label
        mirrored.add_transition(
            mapping[id(transition.end)],
            None if label is None else label.get_inverse(),
            mapping[id(transition.start)],
        )
    return mirrored


def _get_disjoint_union(automaton1: Automaton, automaton2: Automaton) -> dict[int, State]:
    """Copy ``automaton2``'s states/transitions into ``automaton1``.

    The copied states are neither initial nor terminal; the returned map sends
    ``id(state-of-automaton2)`` to the corresponding new state.
    """
    mapping: dict[int, State] = {}
    for state in automaton2.states():
        mapping[id(state)] = automaton1.add_state(False, False)
    for transition in automaton2.delta():
        automaton1.add_transition(
            mapping[id(transition.start)],
            transition.label,
            mapping[id(transition.end)],
        )
    return mapping


def _automata_connector(
    bigger: Automaton, smaller: Automaton, transition: Transition
) -> None:
    """Inline ``smaller`` into ``bigger`` across ``transition`` with ε-moves."""
    mapping = _get_disjoint_union(bigger, smaller)
    old_start = mapping[id(smaller.initial)]
    old_final = mapping[id(smaller.terminal)]
    bigger.add_transition(transition.start, None, old_start)
    bigger.add_transition(old_final, None, transition.end)


def _increase_automaton_with_inverse_property_automaton(
    property_automaton: Automaton, inverse_property_automaton: Automaton
) -> None:
    transitions = property_automaton.delta_from(
        property_automaton.initial, property_automaton.terminal
    )
    _automata_connector(
        property_automaton,
        get_mirrored_copy(inverse_property_automaton),
        transitions[0],
    )


# ===========================================================================
# Graph (port of org.semanticweb.HermiT.graph.Graph)
# ===========================================================================


class Graph:
    """A directed graph over roles with HermiT's ``Graph`` operations."""

    def __init__(self) -> None:
        self._elements: list[Role] = []
        self._element_set: set[Role] = set()
        self._successors: dict[Role, set[Role]] = {}

    def _add_element(self, element: Role) -> None:
        if element not in self._element_set:
            self._element_set.add(element)
            self._elements.append(element)

    def add_edge(self, from_element: Role, to_element: Role) -> None:
        self._add_element(from_element)
        self._add_element(to_element)
        self._successors.setdefault(from_element, set()).add(to_element)

    def get_elements(self) -> list[Role]:
        return list(self._elements)

    def get_successors(self, element: Role) -> set[Role]:
        return self._successors.setdefault(element, set())

    def clone(self) -> Graph:
        copy = Graph()
        for element in self._elements:
            copy._add_element(element)
        for element, successors in self._successors.items():
            copy._successors[element] = set(successors)
        return copy

    def get_inverse(self) -> Graph:
        inverse = Graph()
        for element in self._elements:
            inverse._add_element(element)
        for element, successors in self._successors.items():
            for successor in successors:
                inverse.add_edge(successor, element)
        return inverse

    def transitively_close(self) -> None:
        changed = True
        while changed:
            changed = False
            for element in self._elements:
                successors = self._successors.get(element)
                if not successors:
                    continue
                additions: set[Role] = set()
                for successor in successors:
                    additions.update(self._successors.get(successor, set()))
                if not additions.issubset(successors):
                    successors.update(additions)
                    changed = True

    def remove_elements(self, elements: Iterable[Role]) -> None:
        removed = set(elements)
        self._elements = [e for e in self._elements if e not in removed]
        self._element_set -= removed
        for element in removed:
            self._successors.pop(element, None)
        for successors in self._successors.values():
            successors -= removed


# ===========================================================================
# Automata construction (port of createAutomata and helpers)
# ===========================================================================


class RoleAutomataBuilder:
    """Builds the complete automaton for every non-simple object property.

    Faithful port of ``ObjectPropertyInclusionManager.createAutomata``: the
    result maps each non-simple property (and its inverse) to an automaton
    accepting the role words that imply it.
    """

    def __init__(
        self,
        simple_inclusions: Sequence[tuple[Role, ...]],
        complex_inclusions: Sequence[ComplexObjectPropertyInclusion],
    ) -> None:
        self._simple_inclusions: list[tuple[Role, Role]] = [
            (inclusion[0], inclusion[1])
            for inclusion in simple_inclusions
            if len(inclusion) >= 2
        ]
        self._complex_inclusions = list(complex_inclusions)
        self.complex_properties: set[Role] = set()

    # -- Entry point --------------------------------------------------------

    def build(self) -> dict[Role, Automaton]:
        automata_by_property: dict[Role, Automaton] = {}
        equivalent_properties = self._find_equivalent_properties()
        symmetric_properties = self._find_symmetric_properties()
        inverse_properties_map = self._build_inverse_properties_map()
        property_dependency_graph = self._build_property_ordering(
            equivalent_properties
        )
        self._check_for_regularity(property_dependency_graph, equivalent_properties)

        complex_dependency_graph = property_dependency_graph.clone()
        transitive_properties: set[Role] = set()
        individual_automata = self._build_individual_automata(
            complex_dependency_graph, equivalent_properties, transitive_properties
        )
        simple_properties = self._find_simple_properties(
            complex_dependency_graph, individual_automata
        )

        property_dependency_graph.remove_elements(simple_properties)
        complex_dependency_graph.remove_elements(simple_properties)
        self.complex_properties.update(complex_dependency_graph.get_elements())

        for sub, sup in self._simple_inclusions:
            if sub in self.complex_properties and sup in individual_automata:
                automaton = individual_automata[sup]
                automaton.add_transition(automaton.initial, sub, automaton.terminal)

        for complex_property in list(self.complex_properties):
            self.complex_properties.add(complex_property.get_inverse())

        self._connect_all_automata(
            automata_by_property,
            property_dependency_graph,
            inverse_properties_map,
            individual_automata,
            symmetric_properties,
            transitive_properties,
        )

        automata_for_equivalents: dict[Role, Automaton] = {}
        for prop, automaton in automata_by_property.items():
            equivalents = equivalent_properties.get(prop)
            if equivalents is None:
                continue
            for equivalent in equivalents:
                if equivalent != prop and equivalent not in automata_by_property:
                    automata_for_equivalents[equivalent] = automaton.clone()
                    self.complex_properties.add(equivalent)
                inverse_equivalent = equivalent.get_inverse()
                if (
                    inverse_equivalent != prop
                    and inverse_equivalent not in automata_by_property
                ):
                    automata_for_equivalents[inverse_equivalent] = get_mirrored_copy(
                        automaton.clone()
                    )
                    self.complex_properties.add(inverse_equivalent)
        automata_by_property.update(automata_for_equivalents)
        return automata_by_property

    # -- Simple-inclusion analyses -------------------------------------------

    def _find_symmetric_properties(self) -> set[Role]:
        symmetric: set[Role] = set()
        for sub, sup in self._simple_inclusions:
            if sup.get_inverse() == sub or sup == sub.get_inverse():
                symmetric.add(sub)
                symmetric.add(sub.get_inverse())
        return symmetric

    def _build_inverse_properties_map(self) -> dict[Role, set[Role]]:
        from hermit.model import InverseRole

        inverse_map: dict[Role, set[Role]] = {}

        def _record(prop: Role, inverse: Role) -> None:
            inverse_map.setdefault(prop, set()).add(inverse)
            inverse_map.setdefault(inverse, set()).add(prop)

        for sub, sup in self._simple_inclusions:
            if isinstance(sup, InverseRole):
                _record(sub, sup.get_inverse())
            elif isinstance(sub, InverseRole):
                _record(sup, sub.get_inverse())
        return inverse_map

    def _find_equivalent_properties(self) -> dict[Role, set[Role]]:
        dependency_graph = Graph()
        equivalent: dict[Role, set[Role]] = {}
        for sub, sup in self._simple_inclusions:
            if sub != sup and sub != sup.get_inverse():
                dependency_graph.add_edge(sub, sup)
        dependency_graph.transitively_close()
        for prop in dependency_graph.get_elements():
            successors = dependency_graph.get_successors(prop)
            if prop in successors or prop.get_inverse() in successors:
                equivalent_set: set[Role] = set()
                for successor in successors:
                    successor_successors = dependency_graph.get_successors(successor)
                    if successor != prop and (
                        prop in successor_successors
                        or prop.get_inverse() in successor_successors
                    ):
                        equivalent_set.add(successor)
                equivalent[prop] = equivalent_set
        return equivalent

    # -- Dependency graph and regularity ---------------------------------------

    def _build_property_ordering(
        self, equivalent_properties: dict[Role, set[Role]]
    ) -> Graph:
        dependency_graph = Graph()
        for sub, sup in self._simple_inclusions:
            if (
                sub != sup
                and sub != sup.get_inverse()
                and sup not in equivalent_properties.get(sub, set())
            ):
                dependency_graph.add_edge(sub, sup)
        for inclusion in self._complex_inclusions:
            super_property = inclusion.super_object_property
            sub_properties = inclusion.sub_object_properties
            if (
                len(sub_properties) != 2
                and super_property == sub_properties[0]
                and super_property == sub_properties[-1]
            ):
                raise ValueError("The given property hierarchy is not regular.")
            for i, sub_property in enumerate(sub_properties):
                if (
                    len(sub_properties) != 2
                    and 0 < i < len(sub_properties) - 1
                    and (
                        sub_property == super_property
                        or sub_property
                        in equivalent_properties.get(super_property, set())
                    )
                ):
                    raise ValueError("The given property hierarchy is not regular.")
                if (
                    sub_property != super_property
                    and sub_property.get_inverse() == super_property
                ):
                    # Self-inverse built-in roles (owl:topObjectProperty) have
                    # inverse(R) == R, so their transitivity inclusion
                    # (R, R) ⊑ R must not be flagged as irregular.
                    raise ValueError("The given property hierarchy is not regular.")
                if sub_property != super_property:
                    dependency_graph.add_edge(sub_property, super_property)
        return dependency_graph

    @staticmethod
    def _check_for_regularity(
        dependency_graph: Graph, equivalent_properties: dict[Role, set[Role]]
    ) -> None:
        regularity_graph = dependency_graph.clone()
        trimmed = True
        while trimmed:
            trimmed = False
            snapshot = regularity_graph.clone()
            for prop in snapshot.get_elements():
                for successor in snapshot.get_successors(prop):
                    if successor in equivalent_properties.get(prop, set()):
                        for successor_successor in snapshot.get_successors(successor):
                            if successor_successor != prop:
                                regularity_graph.add_edge(prop, successor_successor)
                        trimmed = True
                        regularity_graph.get_successors(prop).discard(successor)
        regularity_graph.transitively_close()
        for prop in regularity_graph.get_elements():
            successors = regularity_graph.get_successors(prop)
            if prop in successors or prop.get_inverse() in successors:
                raise ValueError(
                    "The given property hierarchy is not regular.\n"
                    f"There is a cyclic dependency involving property {prop}"
                )

    # -- Individual (per-axiom) automata ---------------------------------------

    def _build_individual_automata(
        self,
        complex_dependency_graph: Graph,
        equivalent_properties: dict[Role, set[Role]],
        transitive_properties: set[Role],
    ) -> dict[Role, Automaton]:
        automata: dict[Role, Automaton] = {}
        for inclusion in self._complex_inclusions:
            sub_properties = inclusion.sub_object_properties
            super_property = inclusion.super_object_property
            automaton = automata.get(super_property)
            if automaton is None:
                automaton = Automaton()
                initial = automaton.add_state(True, False)
                final = automaton.add_state(False, True)
                automaton.add_transition(initial, super_property, final)
            else:
                initial = automaton.initial
                final = automaton.terminal

            def _label(role: Role, super_property: Role = super_property) -> Role:
                if role in equivalent_properties.get(super_property, set()):
                    return super_property
                return role

            if (
                len(sub_properties) == 2
                and sub_properties[0] == super_property
                and sub_properties[1] == super_property
            ):
                # R ∘ R ⊑ R
                automaton.add_transition(final, None, initial)
                transitive_properties.add(super_property)
            elif sub_properties[0] == super_property:
                # R ∘ S2 ∘ … ∘ Sn ⊑ R
                from_state = final
                for i in range(1, len(sub_properties) - 1):
                    from_state = self._add_new_transition(
                        automaton, from_state, _label(sub_properties[i])
                    )
                automaton.add_transition(
                    from_state, _label(sub_properties[-1]), final
                )
            elif sub_properties[-1] == super_property:
                # S1 ∘ … ∘ Sn-1 ∘ R ⊑ R
                from_state = initial
                for i in range(len(sub_properties) - 2):
                    from_state = self._add_new_transition(
                        automaton, from_state, _label(sub_properties[i])
                    )
                automaton.add_transition(
                    from_state, _label(sub_properties[-2]), initial
                )
            else:
                # S1 ∘ … ∘ Sn ⊑ R
                from_state = initial
                for i in range(len(sub_properties) - 1):
                    from_state = self._add_new_transition(
                        automaton, from_state, _label(sub_properties[i])
                    )
                automaton.add_transition(
                    from_state, _label(sub_properties[-1]), final
                )
            automata[super_property] = automaton

        # For transitive properties nothing else depends on, the automaton is
        # complete; mirror it for the inverse unless the inverse has its own.
        for inclusion in self._complex_inclusions:
            super_property = inclusion.super_object_property
            sub_properties = inclusion.sub_object_properties
            if (
                len(sub_properties) == 2
                and sub_properties[0] == super_property
                and sub_properties[1] == super_property
                and super_property not in complex_dependency_graph.get_elements()
                and super_property.get_inverse() not in automata
            ):
                complex_dependency_graph.add_edge(super_property, super_property)
                automata[super_property.get_inverse()] = get_mirrored_copy(
                    automata[super_property]
                )

        # The top object property always gets an automaton: it is implicitly
        # transitive and may appear in queries.
        top = AtomicRole.TOP_OBJECT_ROLE
        if top not in automata:
            automaton = Automaton()
            initial = automaton.add_state(True, False)
            final = automaton.add_state(False, True)
            automaton.add_transition(initial, top, final)
            automaton.add_transition(final, None, initial)
            automata[top] = automaton
        return automata

    @staticmethod
    def _add_new_transition(
        automaton: Automaton, from_state: State, label: Role
    ) -> State:
        to_state = automaton.add_state(False, False)
        automaton.add_transition(from_state, label, to_state)
        return to_state

    @staticmethod
    def _find_simple_properties(
        complex_dependency_graph: Graph,
        individual_automata: dict[Role, Automaton],
    ) -> set[Role]:
        simple_properties: set[Role] = set()
        graph_with_inverses = complex_dependency_graph.clone()
        for prop in complex_dependency_graph.get_elements():
            for successor in complex_dependency_graph.get_successors(prop):
                graph_with_inverses.add_edge(
                    prop.get_inverse(), successor.get_inverse()
                )
        inverted_graph = graph_with_inverses.get_inverse()
        inverted_graph.transitively_close()
        for prop in inverted_graph.get_elements():
            has_complex_subproperty = False
            for sub in inverted_graph.get_successors(prop):
                if sub in individual_automata or sub.get_inverse() in individual_automata:
                    has_complex_subproperty = True
                    break
            if (
                not has_complex_subproperty
                and prop not in individual_automata
                and prop.get_inverse() not in individual_automata
            ):
                simple_properties.add(prop)
        return simple_properties

    # -- Connecting automata along the role hierarchy --------------------------

    def _connect_all_automata(
        self,
        complete_automata: dict[Role, Automaton],
        property_dependency_graph: Graph,
        inverse_properties_map: dict[Role, set[Role]],
        individual_automata: dict[Role, Automaton],
        symmetric_properties: set[Role],
        transitive_properties: set[Role],
    ) -> None:
        trans_closed_graph = property_dependency_graph.clone()
        trans_closed_graph.transitively_close()

        properties_to_start_recursion = [
            prop
            for prop in trans_closed_graph.get_elements()
            if not trans_closed_graph.get_successors(prop)
        ]
        inverse_dependency_graph = property_dependency_graph.get_inverse()

        for super_property in properties_to_start_recursion:
            self._build_complete_automata(
                super_property,
                inverse_properties_map,
                individual_automata,
                complete_automata,
                inverse_dependency_graph,
                symmetric_properties,
                transitive_properties,
            )

        for prop, automaton in individual_automata.items():
            if prop not in complete_automata:
                inverse = prop.get_inverse()
                if (
                    inverse in complete_automata
                    and inverse in inverse_dependency_graph.get_elements()
                ) or inverse in individual_automata:
                    inverse_automaton = complete_automata.get(
                        inverse, individual_automata.get(inverse)
                    )
                    assert inverse_automaton is not None
                    _increase_automaton_with_inverse_property_automaton(
                        automaton, inverse_automaton
                    )
                complete_automata[prop] = automaton

        for _ in range(2):
            extra: dict[Role, Automaton] = {}
            for prop, automaton in complete_automata.items():
                inverse = prop.get_inverse()
                if inverse not in complete_automata and inverse not in extra:
                    extra[inverse] = get_mirrored_copy(automaton)
            complete_automata.update(extra)

        extra = {}
        for prop, automaton in complete_automata.items():
            for inverse_property in inverse_properties_map.get(prop, set()):
                inverse_automaton = complete_automata.get(inverse_property)
                if inverse_automaton is not None:
                    _increase_automaton_with_inverse_property_automaton(
                        automaton, inverse_automaton
                    )
                    extra[prop] = automaton
                else:
                    extra[inverse_property] = get_mirrored_copy(automaton)
        complete_automata.update(extra)

    def _build_complete_automata(
        self,
        property_to_build: Role,
        inverse_properties_map: dict[Role, set[Role]],
        individual_automata: dict[Role, Automaton],
        complete_automata: dict[Role, Automaton],
        inverse_dependency_graph: Graph,
        symmetric_properties: set[Role],
        transitive_properties: set[Role],
    ) -> Automaton:
        from hermit.model import InverseRole

        if property_to_build in complete_automata:
            return complete_automata[property_to_build]
        inverse_property = property_to_build.get_inverse()
        if (
            inverse_property in complete_automata
            and property_to_build not in individual_automata
        ):
            mirrored = get_mirrored_copy(complete_automata[inverse_property])
            complete_automata[property_to_build] = mirrored
            return mirrored

        def _recurse(prop: Role) -> Automaton:
            return self._build_complete_automata(
                prop,
                inverse_properties_map,
                individual_automata,
                complete_automata,
                inverse_dependency_graph,
                symmetric_properties,
                transitive_properties,
            )

        if not inverse_dependency_graph.get_successors(
            property_to_build
        ) and not inverse_dependency_graph.get_successors(inverse_property):
            # Leaf property: no (inverse) sub-role is complex.
            automaton = individual_automata.get(property_to_build)
            if automaton is None:
                declared_inverses = inverse_properties_map.get(property_to_build)
                if declared_inverses is not None:
                    for inverse in declared_inverses:
                        if inverse in individual_automata and inverse != property_to_build:
                            automaton = get_mirrored_copy(_recurse(inverse))
                            complete_automata[property_to_build] = automaton
                            return automaton
                elif inverse_property in individual_automata:
                    automaton = get_mirrored_copy(_recurse(inverse_property))
                    if property_to_build not in complete_automata:
                        complete_automata[property_to_build] = automaton
                    else:
                        automaton = complete_automata[property_to_build]
                    return automaton
                automaton = Automaton()
                initial = automaton.add_state(True, False)
                final = automaton.add_state(False, True)
                automaton.add_transition(initial, property_to_build, final)
                self._finalize_construction(
                    complete_automata,
                    property_to_build,
                    automaton,
                    symmetric_properties,
                    transitive_properties,
                )
                return automaton
            if (
                isinstance(inverse_property, InverseRole)
                and inverse_property in individual_automata
            ):
                inverse_automaton = _recurse(inverse_property)
                _increase_automaton_with_inverse_property_automaton(
                    automaton, get_mirrored_copy(inverse_automaton)
                )
                if property_to_build not in complete_automata:
                    self._finalize_construction(
                        complete_automata,
                        property_to_build,
                        automaton,
                        symmetric_properties,
                        transitive_properties,
                    )
                else:
                    automaton = complete_automata[property_to_build]
            else:
                self._increase_with_defined_inverse_if_necessary(
                    property_to_build,
                    automaton,
                    inverse_properties_map,
                    individual_automata,
                )
                self._finalize_construction(
                    complete_automata,
                    property_to_build,
                    automaton,
                    symmetric_properties,
                    transitive_properties,
                )
            return automaton

        # Non-leaf property: fold in the automata of all complex sub-roles.
        automaton = individual_automata.get(property_to_build)
        if automaton is None:
            automaton = Automaton()
            initial = automaton.add_state(True, False)
            final = automaton.add_state(False, True)
            automaton.add_transition(initial, property_to_build, final)
            base_transition = automaton.delta()[0]
            for smaller in inverse_dependency_graph.get_successors(property_to_build):
                smaller_automaton = _recurse(smaller)
                _automata_connector(automaton, smaller_automaton, base_transition)
                automaton.add_transition(initial, smaller, final)
        else:
            for smaller in inverse_dependency_graph.get_successors(property_to_build):
                matched = False
                for transition in list(automaton.delta()):
                    if transition.label is not None and transition.label == smaller:
                        smaller_automaton = _recurse(smaller)
                        if len(smaller_automaton.delta()) != 1:
                            _automata_connector(
                                automaton, smaller_automaton, transition
                            )
                        matched = True
                if not matched:
                    smaller_automaton = _recurse(smaller)
                    initial_to_final = automaton.delta_from(
                        automaton.initial, automaton.terminal
                    )[0]
                    _automata_connector(
                        automaton, smaller_automaton, initial_to_final
                    )

        if (
            isinstance(inverse_property, InverseRole)
            and inverse_property in individual_automata
        ):
            inverse_automaton = _recurse(inverse_property)
            _increase_automaton_with_inverse_property_automaton(
                automaton, get_mirrored_copy(inverse_automaton)
            )
            if property_to_build not in complete_automata:
                self._finalize_construction(
                    complete_automata,
                    property_to_build,
                    automaton,
                    symmetric_properties,
                    transitive_properties,
                )
            else:
                automaton = complete_automata[property_to_build]
        else:
            self._increase_with_defined_inverse_if_necessary(
                property_to_build,
                automaton,
                inverse_properties_map,
                individual_automata,
            )
            if property_to_build not in complete_automata:
                self._finalize_construction(
                    complete_automata,
                    property_to_build,
                    automaton,
                    symmetric_properties,
                    transitive_properties,
                )
            else:
                automaton = complete_automata[property_to_build]
        return automaton

    @staticmethod
    def _finalize_construction(
        complete_automata: dict[Role, Automaton],
        property_to_build: Role,
        automaton: Automaton,
        symmetric_properties: set[Role],
        transitive_properties: set[Role],
    ) -> None:
        if property_to_build.get_inverse() in transitive_properties:
            automaton.add_transition(automaton.terminal, None, automaton.initial)
        if property_to_build in symmetric_properties:
            transition = Transition(
                automaton.initial,
                property_to_build.get_inverse(),
                automaton.terminal,
            )
            _automata_connector(automaton, get_mirrored_copy(automaton), transition)
        complete_automata[property_to_build] = automaton
        complete_automata[property_to_build.get_inverse()] = get_mirrored_copy(
            automaton
        )

    @staticmethod
    def _increase_with_defined_inverse_if_necessary(
        property_to_build: Role,
        automaton: Automaton,
        inverse_properties_map: dict[Role, set[Role]],
        individual_automata: dict[Role, Automaton],
    ) -> None:
        declared_inverses = inverse_properties_map.get(property_to_build)
        if declared_inverses is not None:
            for inverse in declared_inverses:
                if inverse in individual_automata and inverse != property_to_build:
                    _increase_automaton_with_inverse_property_automaton(
                        automaton, individual_automata[inverse]
                    )
        else:
            inverse_property = property_to_build.get_inverse()
            if inverse_property in individual_automata:
                _increase_automaton_with_inverse_property_automaton(
                    automaton, individual_automata[inverse_property]
                )


def build_role_automata(
    simple_inclusions: Sequence[tuple[Role, ...]],
    complex_inclusions: Sequence[ComplexObjectPropertyInclusion],
) -> tuple[dict[Role, Automaton], set[Role]]:
    """Build the complete automata map for all non-simple object properties.

    Returns the map from property to automaton and the set of non-simple
    (complex) properties discovered during construction.
    """
    builder = RoleAutomataBuilder(simple_inclusions, complex_inclusions)
    automata = builder.build()
    return automata, builder.complex_properties
