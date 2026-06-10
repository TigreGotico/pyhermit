"""Automaton-based rewriting of universals over non-simple roles.

Minimal repros for the port of Java HermiT's
``ObjectPropertyInclusionManager.rewriteAxioms``: transitivity propagation,
role-chain composition, and the symmetric/transitive/sub-role interplay, all
expressed through ∀-restrictions whose role carries an automaton.
"""

from __future__ import annotations

import pytest

from hermit.configuration import Configuration
from hermit.model import AtomicRole, InverseRole
from hermit.owl_model.class_expression import OWLClass
from hermit.owl_model.class_expression.class_expression import OWLObjectComplementOf
from hermit.owl_model.class_expression.restriction import (
    OWLObjectAllValuesFrom,
    OWLObjectSomeValuesFrom,
)
from hermit.owl_model.owl_axiom import (
    OWLClassAssertionAxiom,
    OWLObjectPropertyAssertionAxiom,
    OWLObjectPropertyRangeAxiom,
    OWLSubClassOfAxiom,
    OWLSubObjectPropertyOfAxiom,
    OWLSubPropertyChainAxiom,
    OWLSymmetricObjectPropertyAxiom,
    OWLTransitiveObjectPropertyAxiom,
)
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_property import OWLObjectProperty
from hermit.reasoner import Reasoner
from hermit.structural.normalized_axioms import ComplexObjectPropertyInclusion
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization
from hermit.structural.role_automaton import build_role_automata

NS = "http://example.org/auto#"


def _consistent(axioms: list) -> bool:
    normalized = OWLNormalization().process_ontology(axioms)
    ontology = OWLClausification().clausify(normalized, ontology_iri="urn:test:auto")
    config = Configuration()
    config.throw_inconsistent_ontology_exception = False
    reasoner = Reasoner(ontology, config)
    try:
        return reasoner.is_consistent()
    finally:
        reasoner.dispose()


def _denied_edge(source_ind, prop, target_ind) -> list:
    """Premise axioms denying prop(source, target) via ∀prop.¬marker."""
    marker = OWLClass(NS + "Marker")
    source = OWLClass(NS + "Source")
    return [
        OWLClassAssertionAxiom(target_ind, marker),
        OWLClassAssertionAxiom(source_ind, source),
        OWLSubClassOfAxiom(
            source, OWLObjectAllValuesFrom(prop, OWLObjectComplementOf(marker))
        ),
    ]


class TestRoleAutomatonConstruction:
    """The automata built from complex object property inclusions."""

    def test_transitive_role_automaton_has_epsilon_loop(self):
        r = AtomicRole.create(NS + "r")
        automata, complex_properties = build_role_automata(
            [], [ComplexObjectPropertyInclusion.transitivity(r)]
        )
        assert r in automata
        assert r in complex_properties
        assert InverseRole.create(r) in complex_properties
        automaton = automata[r]
        # initial --r--> final plus the ε-move final --> initial
        labels = {t.label for t in automaton.delta()}
        assert labels == {r, None}
        epsilon = [t for t in automaton.delta() if t.label is None][0]
        assert automaton.is_terminal(epsilon.start)
        assert automaton.is_initial(epsilon.end)

    def test_chain_automaton_accepts_chain_word(self):
        m = AtomicRole.create(NS + "m")
        s = AtomicRole.create(NS + "s")
        aunt = AtomicRole.create(NS + "aunt")
        automata, complex_properties = build_role_automata(
            [],
            [
                ComplexObjectPropertyInclusion(
                    sub_object_properties=(m, s), super_object_property=aunt
                )
            ],
        )
        assert aunt in complex_properties
        assert m not in complex_properties
        automaton = automata[aunt]
        labels = [t.label for t in automaton.delta()]
        assert aunt in labels and m in labels and s in labels

    def test_inverse_of_complex_role_gets_mirrored_automaton(self):
        r = AtomicRole.create(NS + "r")
        automata, _ = build_role_automata(
            [], [ComplexObjectPropertyInclusion.transitivity(r)]
        )
        inverse = InverseRole.create(r)
        assert inverse in automata
        labels = {t.label for t in automata[inverse].delta()}
        assert labels == {inverse, None}

    def test_irregular_hierarchy_is_rejected(self):
        r = AtomicRole.create(NS + "r")
        s = AtomicRole.create(NS + "s")
        with pytest.raises(ValueError):
            build_role_automata(
                [(r, s)],
                [
                    ComplexObjectPropertyInclusion(
                        sub_object_properties=(s, s), super_object_property=s
                    ),
                    ComplexObjectPropertyInclusion(
                        sub_object_properties=(s, r), super_object_property=r
                    ),
                ],
            )


class TestTransitivePropagation:
    """∀R.C must constrain every R-chain when R is transitive."""

    def _axioms(self, *, transitive: bool) -> list:
        part_of = OWLObjectProperty(NS + "partOf")
        a_cls = OWLClass(NS + "A")
        b_cls = OWLClass(NS + "B")
        axioms = [
            OWLSubClassOfAxiom(
                a_cls,
                OWLObjectSomeValuesFrom(
                    part_of, OWLObjectSomeValuesFrom(part_of, b_cls)
                ),
            ),
            OWLSubClassOfAxiom(
                a_cls,
                OWLObjectAllValuesFrom(part_of, OWLObjectComplementOf(b_cls)),
            ),
            OWLClassAssertionAxiom(OWLNamedIndividual(NS + "a"), a_cls),
        ]
        if transitive:
            axioms.append(OWLTransitiveObjectPropertyAxiom(part_of))
        return axioms

    def test_transitive_part_of_propagates_universal(self):
        assert not _consistent(self._axioms(transitive=True))

    def test_without_transitivity_remains_satisfiable(self):
        assert _consistent(self._axioms(transitive=False))

    def test_transitive_super_role_constrains_sub_role_chains(self):
        """∀R.C with transitive S ⊑ R reaches two-S-step successors."""
        r = OWLObjectProperty(NS + "r")
        s = OWLObjectProperty(NS + "s")
        a = OWLNamedIndividual(NS + "a")
        b = OWLNamedIndividual(NS + "b")
        c = OWLNamedIndividual(NS + "c")
        marker = OWLClass(NS + "Marker")
        axioms = [
            OWLSubObjectPropertyOfAxiom(s, r),
            OWLTransitiveObjectPropertyAxiom(s),
            OWLObjectPropertyAssertionAxiom(a, s, b),
            OWLObjectPropertyAssertionAxiom(b, s, c),
            OWLObjectPropertyRangeAxiom(r, OWLObjectComplementOf(marker)),
            OWLClassAssertionAxiom(c, marker),
        ]
        assert not _consistent(axioms)
        assert _consistent(axioms[1:])


class TestRoleChainComposition:
    """S1 ∘ S2 ⊑ R must compose through universals over R."""

    def test_chain_composes(self):
        m = OWLObjectProperty(NS + "hasMother")
        s = OWLObjectProperty(NS + "hasSister")
        aunt = OWLObjectProperty(NS + "hasAunt")
        a = OWLNamedIndividual(NS + "stewie")
        b = OWLNamedIndividual(NS + "lois")
        c = OWLNamedIndividual(NS + "carol")
        facts = [
            OWLObjectPropertyAssertionAxiom(a, m, b),
            OWLObjectPropertyAssertionAxiom(b, s, c),
            *_denied_edge(a, aunt, c),
        ]
        assert not _consistent([OWLSubPropertyChainAxiom([m, s], aunt), *facts])
        assert _consistent(facts)

    def test_chain_with_super_role_on_left(self):
        """p ∘ q ⊑ p composes repeatedly."""
        p = OWLObjectProperty(NS + "p")
        q = OWLObjectProperty(NS + "q")
        a = OWLNamedIndividual(NS + "a")
        b = OWLNamedIndividual(NS + "b")
        c = OWLNamedIndividual(NS + "c")
        facts = [
            OWLObjectPropertyAssertionAxiom(a, p, b),
            OWLObjectPropertyAssertionAxiom(b, q, c),
            *_denied_edge(a, p, c),
        ]
        assert not _consistent([OWLSubPropertyChainAxiom([p, q], p), *facts])
        assert _consistent(facts)


class TestEquivalentObjectProperties:
    """p ≡ q must yield mutual role-inclusion clauses."""

    def test_equivalent_properties_transfer_edges(self):
        from hermit.owl_model.owl_axiom import OWLEquivalentObjectPropertiesAxiom

        p = OWLObjectProperty(NS + "p")
        q = OWLObjectProperty(NS + "q")
        a = OWLNamedIndividual(NS + "a")
        b = OWLNamedIndividual(NS + "b")
        facts = [
            OWLObjectPropertyAssertionAxiom(a, p, b),
            *_denied_edge(a, q, b),
        ]
        assert not _consistent(
            [OWLEquivalentObjectPropertiesAxiom([p, q]), *facts]
        )
        assert _consistent(facts)

    def test_equivalent_properties_populate_inclusions(self):
        from hermit.owl_model.owl_axiom import OWLEquivalentObjectPropertiesAxiom

        p = OWLObjectProperty(NS + "p")
        q = OWLObjectProperty(NS + "q")
        normalized = OWLNormalization().process_ontology(
            [OWLEquivalentObjectPropertiesAxiom([p, q])]
        )
        p_role = AtomicRole.create(NS + "p")
        q_role = AtomicRole.create(NS + "q")
        inclusions = set(normalized.simple_object_property_inclusions)
        assert (p_role, q_role) in inclusions
        assert (q_role, p_role) in inclusions


class TestComplementOfEnumeration:
    """¬{a1,…,an} must exclude every listed individual."""

    def test_complement_of_enumeration_excludes_members(self):
        from hermit.owl_model.class_expression.restriction import OWLObjectOneOf

        a = OWLNamedIndividual(NS + "a")
        b = OWLNamedIndividual(NS + "b")
        c = OWLNamedIndividual(NS + "c")
        q = OWLClass(NS + "q")
        axioms = [
            OWLSubClassOfAxiom(
                q, OWLObjectComplementOf(OWLObjectOneOf([a, b, c]))
            ),
            OWLClassAssertionAxiom(b, q),
        ]
        assert not _consistent(axioms)

    def test_complement_of_enumeration_allows_non_members(self):
        from hermit.owl_model.class_expression.restriction import OWLObjectOneOf

        a = OWLNamedIndividual(NS + "a")
        b = OWLNamedIndividual(NS + "b")
        d = OWLNamedIndividual(NS + "d")
        q = OWLClass(NS + "q")
        axioms = [
            OWLSubClassOfAxiom(q, OWLObjectComplementOf(OWLObjectOneOf([a, b]))),
            OWLClassAssertionAxiom(d, q),
        ]
        assert _consistent(axioms)


class TestSymmetricTransitiveInterplay:
    """Symmetric + transitive roles propagate universals in both directions."""

    def test_symmetric_transitive_range(self):
        p = OWLObjectProperty(NS + "p")
        a = OWLNamedIndividual(NS + "a")
        b = OWLNamedIndividual(NS + "b")
        c = OWLNamedIndividual(NS + "c")
        marker = OWLClass(NS + "Marker")
        guard = OWLClass(NS + "Guard")
        # p(b,a), p(b,c); symmetry gives p(a,b); transitivity gives p(a,c).
        axioms = [
            OWLSymmetricObjectPropertyAxiom(p),
            OWLTransitiveObjectPropertyAxiom(p),
            OWLObjectPropertyAssertionAxiom(b, p, a),
            OWLObjectPropertyAssertionAxiom(b, p, c),
            OWLClassAssertionAxiom(a, guard),
            OWLClassAssertionAxiom(c, marker),
            OWLSubClassOfAxiom(
                guard, OWLObjectAllValuesFrom(p, OWLObjectComplementOf(marker))
            ),
        ]
        assert not _consistent(axioms)
        # Without symmetry there is no p-path from a, so no clash.
        assert _consistent(axioms[1:])
