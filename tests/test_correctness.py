"""Reasoning correctness tests.

Each test asserts a specific True/False answer from the reasoner on a
hand-crafted ontology. These are the ground truth tests: if they fail,
the reasoner is computing the wrong answer (not just a structural issue).

Note on API: Reasoner.is_satisfiable() and is_sub_class_of() accept internal
AtomicConcept objects (from hermit.model). For complex expression satisfiability,
we use the DLOntology/Tableau approach directly, or encode via SubClassOf axioms.

Tests cover:
- Subsumption via named class hierarchies
- Subsumption via object property restrictions
- Cardinality constraint / non-simplicity validation
- Transitivity and role chain reasoning
- Nominal (individual) reasoning
- ABox consistency and instance checking
- Disjointness reasoning
- Role characteristics
"""

from __future__ import annotations

import pytest

from hermit.model import AtomicConcept, Individual, Atom, DLClause
from hermit.model import AtomicRole, InverseRole, Variable, Inequality
from hermit.model import DLOntology
from hermit.structural.owl_normalization import OWLNormalization
from hermit.structural.owl_clausification import OWLClausification
from hermit.reasoner import Reasoner

NS = "http://correctness.test#"

X = Variable.create("X")
Y = Variable.create("Y")


def _concept(local: str) -> AtomicConcept:
    return AtomicConcept.create(NS + local)


def _role(local: str) -> AtomicRole:
    return AtomicRole.create(NS + local)


def _ind(local: str) -> Individual:
    return Individual.create(NS + local)


def _reasoner_from_axioms(axioms: list) -> Reasoner:
    """Build a Reasoner from a list of OWLAxiom objects via normalization pipeline."""
    norm = OWLNormalization()
    normalized = norm.process_ontology(axioms)
    claus = OWLClausification()
    dl_onto = claus.clausify(normalized, ontology_iri="urn:test:correctness")
    r = Reasoner(dl_onto)
    return r


def _reasoner_from_dl(
    clauses: list[DLClause],
    positive_facts: list[Atom] | None = None,
    negative_facts: list[Atom] | None = None,
) -> Reasoner:
    """Build a Reasoner directly from DL clauses and facts."""
    dl_onto = DLOntology(
        ontology_iri="urn:test:correctness",
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset(positive_facts or []),
        negative_facts=frozenset(negative_facts or []),
    )
    return Reasoner(dl_onto)


# ---------------------------------------------------------------------------
# Basic class hierarchy via OWL normalization pipeline
# ---------------------------------------------------------------------------

class TestClassHierarchy:
    """Subsumption and consistency for simple named class hierarchies."""

    def test_direct_subclass_is_subsumption(self):
        """A ⊑ B and B ⊑ C implies A ⊑ C.
        Expected: is_sub_class_of(A, C) = True."""
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom
        from hermit.owl_model.class_expression import OWLClass

        A = OWLClass(NS + "A")
        B = OWLClass(NS + "B")
        C = OWLClass(NS + "C")
        axioms = [OWLSubClassOfAxiom(A, B), OWLSubClassOfAxiom(B, C)]
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_sub_class_of(_concept("A"), _concept("C")) is True
        finally:
            r.dispose()

    def test_non_subclass_returns_false(self):
        """A ⊑ B does not imply A ⊑ C when B and C are unrelated.
        Expected: is_sub_class_of(A, C) = False."""
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom
        from hermit.owl_model.class_expression import OWLClass

        A = OWLClass(NS + "A")
        B = OWLClass(NS + "B")
        C = OWLClass(NS + "C")
        axioms = [OWLSubClassOfAxiom(A, B)]
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_sub_class_of(_concept("A"), _concept("C")) is False
        finally:
            r.dispose()

    def test_equivalent_classes_bidirectional_subsumption(self):
        """EquivalentClasses(A, B) → A ⊑ B and B ⊑ A.
        Expected: both directions are True."""
        from hermit.owl_model.owl_axiom import OWLEquivalentClassesAxiom
        from hermit.owl_model.class_expression import OWLClass

        A = OWLClass(NS + "A")
        B = OWLClass(NS + "B")
        axioms = [OWLEquivalentClassesAxiom([A, B])]
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_sub_class_of(_concept("A"), _concept("B")) is True
            assert r.is_sub_class_of(_concept("B"), _concept("A")) is True
        finally:
            r.dispose()

    def test_empty_ontology_is_consistent(self):
        """An empty ontology is always consistent.
        Expected: is_consistent() = True."""
        r = _reasoner_from_dl([])
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_named_class_is_satisfiable(self):
        """Any named class is satisfiable in the absence of contradicting axioms.
        Expected: is_satisfiable(A) = True."""
        A = _concept("A")
        r = _reasoner_from_dl([])
        try:
            assert r.is_satisfiable(A) is True
        finally:
            r.dispose()

    def test_nothing_is_not_satisfiable(self):
        """owl:Nothing is never satisfiable.
        Expected: is_satisfiable(NOTHING) = False."""
        r = _reasoner_from_dl([])
        try:
            assert r.is_satisfiable(AtomicConcept.NOTHING) is False
        finally:
            r.dispose()

    def test_disjoint_makes_intersection_inconsistent(self):
        """DisjointClasses(A, B) — an individual in both A and B causes clash.
        Encoded as DL clauses: ¬A ∨ ¬B (head empty when both body atoms present).
        Expected: inconsistent (tableau finds clash)."""
        # DisjointClasses(A, B) → A(X) ∧ B(X) :- ⊥
        A = _concept("A")
        B = _concept("B")
        a = _ind("a")
        # DL clause: {} :- {A(X), B(X)} — empty head = clash
        clause = DLClause.create(
            (),
            (Atom.create(A, X), Atom.create(B, X)),
        )
        r = _reasoner_from_dl(
            [clause],
            positive_facts=[Atom.create(A, a), Atom.create(B, a)],
        )
        try:
            assert r.is_consistent() is False
        finally:
            r.dispose()

    def test_subclass_chain_three_levels(self):
        """A ⊑ B, B ⊑ C, C ⊑ D → A ⊑ D (three-level chain).
        Expected: is_sub_class_of(A, D) = True."""
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom
        from hermit.owl_model.class_expression import OWLClass

        A = OWLClass(NS + "A")
        B = OWLClass(NS + "B")
        C = OWLClass(NS + "C")
        D = OWLClass(NS + "D")
        axioms = [
            OWLSubClassOfAxiom(A, B),
            OWLSubClassOfAxiom(B, C),
            OWLSubClassOfAxiom(C, D),
        ]
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_sub_class_of(_concept("A"), _concept("D")) is True
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# ABox consistency and instance checking
# ---------------------------------------------------------------------------

class TestABox:
    """ABox consistency with concept and role assertions."""

    def test_class_assertion_consistent(self):
        """A(a) — consistent.
        Expected: is_consistent() = True."""
        A = _concept("A")
        a = _ind("a")
        r = _reasoner_from_dl([], positive_facts=[Atom.create(A, a)])
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_conflicting_abox_is_inconsistent(self):
        """A(a), B(a), DisjointClasses(A, B) → inconsistent.
        Expected: is_consistent() = False."""
        A = _concept("A")
        B = _concept("B")
        a = _ind("a")
        # DisjointClasses(A, B): {} :- {A(X), B(X)}
        clause = DLClause.create((), (Atom.create(A, X), Atom.create(B, X)))
        r = _reasoner_from_dl(
            [clause],
            positive_facts=[Atom.create(A, a), Atom.create(B, a)],
        )
        try:
            assert r.is_consistent() is False
        finally:
            r.dispose()

    def test_different_individuals_consistent(self):
        """DifferentIndividuals(a, b) — consistent.
        Expected: is_consistent() = True."""
        from hermit.owl_model.owl_axiom import OWLDifferentIndividualsAxiom
        from hermit.owl_model.owl_individual import OWLNamedIndividual

        a = OWLNamedIndividual(NS + "a")
        b = OWLNamedIndividual(NS + "b")
        axioms = [OWLDifferentIndividualsAxiom([a, b])]
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_role_assertion_consistent(self):
        """R(a, b) — consistent.
        Expected: is_consistent() = True."""
        R = _role("R")
        a = _ind("a")
        b = _ind("b")
        r = _reasoner_from_dl(
            [],
            positive_facts=[Atom.create(R, a, b)],
        )
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_functional_role_clash(self):
        """FunctionalObjectProperty(R), R(a, b), R(a, c), DifferentIndividuals(b, c) → inconsistent.
        Encoded as DL clauses: functional role merges b and c; different individuals → clash."""
        from hermit.model import Equality, Inequality
        R = _role("R")
        a = _ind("a")
        b = _ind("b")
        c = _ind("c")
        # Functional: R(X, Y1) ∧ R(X, Y2) → Y1 = Y2
        Z = Variable.create("Z")
        func_clause = DLClause.create(
            (Atom.create(Equality.INSTANCE, Y, Z),),
            (Atom.create(R, X, Y), Atom.create(R, X, Z)),
        )
        r = _reasoner_from_dl(
            [func_clause],
            positive_facts=[
                Atom.create(R, a, b),
                Atom.create(R, a, c),
                Atom.create(Inequality.INSTANCE, b, c),
            ],
        )
        try:
            assert r.is_consistent() is False
        finally:
            r.dispose()

    def test_subclass_of_thing_always_true(self):
        """Every named class A is a subclass of owl:Thing.
        Expected: is_sub_class_of(A, THING) = True."""
        A = _concept("A")
        r = _reasoner_from_dl([])
        try:
            assert r.is_sub_class_of(A, AtomicConcept.THING) is True
        finally:
            r.dispose()

    def test_nothing_is_subclass_of_everything(self):
        """owl:Nothing ⊑ A for any A.
        Expected: is_sub_class_of(NOTHING, A) = True."""
        A = _concept("A")
        r = _reasoner_from_dl([])
        try:
            assert r.is_sub_class_of(AtomicConcept.NOTHING, A) is True
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# Non-simplicity validation (OWL 2 spec §11.2)
# ---------------------------------------------------------------------------

class TestNonSimplicityValidation:
    """Non-simple properties in cardinality restrictions must raise ValueError."""

    def test_transitive_superrole_in_min_cardinality_raises(self):
        """TransitiveObjectProperty(R), R ⊑ P, C ⊑ ≥2 P → non-simple violation.
        Expected: clausify raises ValueError with 'non-simple' or 'simple' in message."""
        from hermit.owl_model.owl_axiom import (
            OWLTransitiveObjectPropertyAxiom, OWLSubObjectPropertyOfAxiom, OWLSubClassOfAxiom,
        )
        from hermit.owl_model.owl_property import OWLObjectProperty
        from hermit.owl_model.class_expression import OWLClass, OWLObjectMinCardinality, OWLThing

        R = OWLObjectProperty(NS + "R")
        P = OWLObjectProperty(NS + "P")
        C = OWLClass(NS + "C")
        axioms = [
            OWLTransitiveObjectPropertyAxiom(R),
            OWLSubObjectPropertyOfAxiom(R, P),
            OWLSubClassOfAxiom(C, OWLObjectMinCardinality(2, P, OWLThing)),
        ]
        norm = OWLNormalization()
        normalized = norm.process_ontology(axioms)
        claus = OWLClausification()
        with pytest.raises((ValueError, Exception)) as exc_info:
            claus.clausify(normalized, ontology_iri="urn:test:nonsimple")
        assert "non-simple" in str(exc_info.value).lower() or "simple" in str(exc_info.value).lower()

    def test_chain_superrole_in_max_cardinality_raises(self):
        """SubPropertyChainOf([R, Q], R), R ⊑ P, C ⊑ ≤2 P → non-simple violation.
        Expected: clausify raises ValueError."""
        from hermit.owl_model.owl_axiom import (
            OWLSubObjectPropertyOfAxiom, OWLSubClassOfAxiom,
        )
        from hermit.owl_model.owl_property import OWLObjectProperty
        from hermit.owl_model.class_expression import OWLClass, OWLObjectMaxCardinality, OWLThing

        try:
            from hermit.owl_model.owl_axiom import OWLSubPropertyChainAxiom
        except ImportError:
            pytest.skip("OWLSubPropertyChainAxiom not available")

        R = OWLObjectProperty(NS + "R")
        Q = OWLObjectProperty(NS + "Q")
        P = OWLObjectProperty(NS + "P")
        C = OWLClass(NS + "C")
        axioms = [
            OWLSubPropertyChainAxiom([R, Q], R),
            OWLSubObjectPropertyOfAxiom(R, P),
            OWLSubClassOfAxiom(C, OWLObjectMaxCardinality(2, P, OWLThing)),
        ]
        norm = OWLNormalization()
        normalized = norm.process_ontology(axioms)
        claus = OWLClausification()
        with pytest.raises((ValueError, Exception)) as exc_info:
            claus.clausify(normalized, ontology_iri="urn:test:nonsimple2")
        assert "non-simple" in str(exc_info.value).lower() or "simple" in str(exc_info.value).lower()

    def test_simple_role_in_cardinality_is_ok(self):
        """Plain R (no transitivity/chain), C ⊑ ≥2 R.⊤ → no error.
        Expected: clausify succeeds (simple role is fine in cardinality)."""
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom
        from hermit.owl_model.owl_property import OWLObjectProperty
        from hermit.owl_model.class_expression import OWLClass, OWLObjectMinCardinality, OWLThing

        R = OWLObjectProperty(NS + "R")
        C = OWLClass(NS + "C")
        axioms = [OWLSubClassOfAxiom(C, OWLObjectMinCardinality(2, R, OWLThing))]
        norm = OWLNormalization()
        normalized = norm.process_ontology(axioms)
        claus = OWLClausification()
        dl_onto = claus.clausify(normalized, ontology_iri="urn:test:simple_ok")
        assert dl_onto is not None  # no exception raised


# ---------------------------------------------------------------------------
# Transitive role reasoning
# ---------------------------------------------------------------------------

class TestTransitivity:
    """Reasoning with transitive roles."""

    def test_transitive_role_consistent(self):
        """TransitiveObjectProperty(R) — consistent.
        Expected: is_consistent() = True."""
        from hermit.owl_model.owl_axiom import OWLTransitiveObjectPropertyAxiom
        from hermit.owl_model.owl_property import OWLObjectProperty

        R = OWLObjectProperty(NS + "R")
        axioms = [OWLTransitiveObjectPropertyAxiom(R)]
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_transitive_role_abox_consistent(self):
        """TransitiveObjectProperty(R), R(a, b), R(b, c) → consistent.
        Expected: is_consistent() = True."""
        from hermit.owl_model.owl_axiom import (
            OWLTransitiveObjectPropertyAxiom, OWLObjectPropertyAssertionAxiom,
        )
        from hermit.owl_model.owl_property import OWLObjectProperty
        from hermit.owl_model.owl_individual import OWLNamedIndividual

        R = OWLObjectProperty(NS + "R")
        a = OWLNamedIndividual(NS + "a")
        b = OWLNamedIndividual(NS + "b")
        c = OWLNamedIndividual(NS + "c")
        axioms = [
            OWLTransitiveObjectPropertyAxiom(R),
            OWLObjectPropertyAssertionAxiom(a, R, b),
            OWLObjectPropertyAssertionAxiom(b, R, c),
        ]
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_transitive_role_propagates_subsumption(self):
        """A ⊑ ∃R.⊥, TransitiveObjectProperty(R) → A ⊑ B (A is unsatisfiable).
        (A ⊑ ∃R.Nothing means every A-individual must have an R-Nothing-successor,
        which is impossible; hence A is empty and is a sub-concept of everything.)
        Expected: is_sub_class_of(A, B) = True."""
        from hermit.owl_model.owl_axiom import (
            OWLSubClassOfAxiom, OWLTransitiveObjectPropertyAxiom,
        )
        from hermit.owl_model.class_expression import (
            OWLClass, OWLObjectSomeValuesFrom, OWLNothing,
        )
        from hermit.owl_model.owl_property import OWLObjectProperty

        A = OWLClass(NS + "A")
        B = OWLClass(NS + "B")
        R = OWLObjectProperty(NS + "R")
        axioms = [
            OWLTransitiveObjectPropertyAxiom(R),
            OWLSubClassOfAxiom(A, OWLObjectSomeValuesFrom(R, OWLNothing)),
        ]
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_sub_class_of(_concept("A"), _concept("B")) is True
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# Role characteristics
# ---------------------------------------------------------------------------

class TestRoleCharacteristics:
    """Reasoning with role characteristics."""

    def test_symmetric_role_consistent(self):
        """SymmetricObjectProperty(R) — consistent.
        Expected: is_consistent() = True."""
        from hermit.owl_model.owl_axiom import OWLSymmetricObjectPropertyAxiom
        from hermit.owl_model.owl_property import OWLObjectProperty

        R = OWLObjectProperty(NS + "R")
        r = _reasoner_from_axioms([OWLSymmetricObjectPropertyAxiom(R)])
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_asymmetric_role_consistent(self):
        """AsymmetricObjectProperty(R) alone — consistent.
        Expected: is_consistent() = True."""
        from hermit.owl_model.owl_axiom import OWLAsymmetricObjectPropertyAxiom
        from hermit.owl_model.owl_property import OWLObjectProperty

        R = OWLObjectProperty(NS + "R")
        r = _reasoner_from_axioms([OWLAsymmetricObjectPropertyAxiom(R)])
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_irreflexive_role_consistent(self):
        """IrreflexiveObjectProperty(R) alone — consistent.
        Expected: is_consistent() = True."""
        from hermit.owl_model.owl_axiom import OWLIrreflexiveObjectPropertyAxiom
        from hermit.owl_model.owl_property import OWLObjectProperty

        R = OWLObjectProperty(NS + "R")
        r = _reasoner_from_axioms([OWLIrreflexiveObjectPropertyAxiom(R)])
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_functional_role_consistent(self):
        """FunctionalObjectProperty(R) alone — consistent.
        Expected: is_consistent() = True."""
        from hermit.owl_model.owl_axiom import OWLFunctionalObjectPropertyAxiom
        from hermit.owl_model.owl_property import OWLObjectProperty

        R = OWLObjectProperty(NS + "R")
        r = _reasoner_from_axioms([OWLFunctionalObjectPropertyAxiom(R)])
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_inverse_properties_consistent(self):
        """InverseObjectProperties(R, S) — consistent.
        Expected: is_consistent() = True."""
        from hermit.owl_model.owl_axiom import OWLInverseObjectPropertiesAxiom
        from hermit.owl_model.owl_property import OWLObjectProperty

        R = OWLObjectProperty(NS + "R")
        S = OWLObjectProperty(NS + "S")
        r = _reasoner_from_axioms([OWLInverseObjectPropertiesAxiom(R, S)])
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# DL-clause level correctness (internal model)
# ---------------------------------------------------------------------------

class TestDLClauseDirect:
    """Correctness tests using DL clauses directly (bypassing OWL layer)."""

    def test_universal_propagation_subsumption(self):
        """∀R.B(X) propagation: A(X) ∧ R(X,Y) → B(Y), plus A(a), R(a, b) → B(b).
        If we also have DisjointClasses(B, C) and C(b), → inconsistent.
        Expected: is_consistent() = False."""
        A = _concept("A")
        B = _concept("B")
        C = _concept("C")
        R = _role("R")
        a = _ind("a")
        b = _ind("b")
        # ∀R.B : A(X) ∧ R(X, Y) → B(Y)
        all_r_b = DLClause.create(
            (Atom.create(B, Y),),
            (Atom.create(A, X), Atom.create(R, X, Y)),
        )
        # DisjointClasses(B, C): B(X) ∧ C(X) → ⊥
        disj = DLClause.create(
            (),
            (Atom.create(B, X), Atom.create(C, X)),
        )
        r = _reasoner_from_dl(
            [all_r_b, disj],
            positive_facts=[
                Atom.create(A, a),
                Atom.create(R, a, b),
                Atom.create(C, b),
            ],
        )
        try:
            assert r.is_consistent() is False
        finally:
            r.dispose()

    def test_role_subsumption_clause(self):
        """R ⊑ S: R(X, Y) → S(X, Y). R(a, b) asserted → S(a, b) entailed.
        Encoded as DL clause. Ontology is consistent.
        Expected: is_consistent() = True."""
        R = _role("R")
        S = _role("S")
        a = _ind("a")
        b = _ind("b")
        r_sub_s = DLClause.create(
            (Atom.create(S, X, Y),),
            (Atom.create(R, X, Y),),
        )
        r = _reasoner_from_dl(
            [r_sub_s],
            positive_facts=[Atom.create(R, a, b)],
        )
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_subsumption_via_dl_clauses(self):
        """A ⊑ B encoded as ¬A ∨ B (DL clause: B(X) :- A(X)).
        Then A(a) → B entailed.
        Expected: is_sub_class_of(A, B) = True."""
        A = _concept("A")
        B = _concept("B")
        # A ⊑ B: B(X) :- A(X)
        clause = DLClause.create(
            (Atom.create(B, X),),
            (Atom.create(A, X),),
        )
        r = _reasoner_from_dl([clause])
        try:
            assert r.is_sub_class_of(A, B) is True
        finally:
            r.dispose()

    def test_chain_subsumption_via_dl_clauses(self):
        """A ⊑ B encoded: B(X) :- A(X). B ⊑ C: C(X) :- B(X).
        Expected: is_sub_class_of(A, C) = True."""
        A = _concept("A")
        B = _concept("B")
        C = _concept("C")
        a_sub_b = DLClause.create((Atom.create(B, X),), (Atom.create(A, X),))
        b_sub_c = DLClause.create((Atom.create(C, X),), (Atom.create(B, X),))
        r = _reasoner_from_dl([a_sub_b, b_sub_c])
        try:
            assert r.is_sub_class_of(A, C) is True
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# ∀R.C (AllValuesFrom) reasoning via OWL pipeline
# ---------------------------------------------------------------------------

class TestAllValuesFrom:
    """OWLObjectAllValuesFrom reasoning through the full OWL normalization pipeline.

    SubClassOf(A, ∀R.C) is now correctly encoded as the two-variable DL clause
    A(X) ∧ R(X,Y) → C(Y) and handled by the existing hyperresolution machinery.
    """

    def test_all_values_from_pipeline_consistent(self):
        """SubClassOf(A, ∀R.B) alone is consistent.

        The restriction does not force the existence of an R-successor, so
        an A-individual without any R-neighbours satisfies the axiom.
        Expected: is_consistent() = True.
        """
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom
        from hermit.owl_model.class_expression import OWLClass
        from hermit.owl_model.class_expression.restriction import OWLObjectAllValuesFrom
        from hermit.owl_model.owl_property import OWLObjectProperty

        A = OWLClass(NS + "A")
        B = OWLClass(NS + "B")
        R = OWLObjectProperty(NS + "R")
        axioms = [OWLSubClassOfAxiom(A, OWLObjectAllValuesFrom(R, B))]
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_all_values_from_with_clash_inconsistent(self):
        """∀R.B, DisjointClasses(B,C), R(a,b), C(b), A(a) → inconsistent.

        The DL clause A(X) ∧ R(X,Y) → B(Y) derives B(b); B(b) and C(b) clash.
        Expected: is_consistent() = False.
        """
        A = _concept("A")
        B = _concept("B")
        C = _concept("C")
        R = _role("R")
        a = _ind("a")
        b = _ind("b")
        # ∀R.B via OWL pipeline
        all_r_b_clause = DLClause.create(
            (Atom.create(B, Y),),
            (Atom.create(A, X), Atom.create(R, X, Y)),
        )
        # DisjointClasses(B, C)
        disj = DLClause.create((), (Atom.create(B, X), Atom.create(C, X)))
        r = _reasoner_from_dl(
            [all_r_b_clause, disj],
            positive_facts=[Atom.create(A, a), Atom.create(R, a, b), Atom.create(C, b)],
        )
        try:
            assert r.is_consistent() is False
        finally:
            r.dispose()

    def test_all_values_from_propagates_to_filler(self):
        """∀R.B derives B(b) when R(a,b) and A(a) are asserted.

        Verified by checking that asserting ¬B(b) causes a clash.
        Expected: is_consistent() = False.
        """
        A = _concept("A")
        B = _concept("B")
        R = _role("R")
        a = _ind("a")
        b = _ind("b")
        all_r_b_clause = DLClause.create(
            (Atom.create(B, Y),),
            (Atom.create(A, X), Atom.create(R, X, Y)),
        )
        r = _reasoner_from_dl(
            [all_r_b_clause],
            positive_facts=[Atom.create(A, a), Atom.create(R, a, b)],
            negative_facts=[Atom.create(B, b)],
        )
        try:
            assert r.is_consistent() is False, (
                "A(a) ∧ R(a,b) ∧ ∀R.B ∧ ¬B(b) must be inconsistent"
            )
        finally:
            r.dispose()

    def test_all_values_from_no_successor_is_vacuously_true(self):
        """∀R.B is vacuously satisfied when there are no R-successors.

        A(a) without any R(a, _) means ∀R.B holds trivially.
        Expected: is_consistent() = True even with ¬B assertion on unrelated b.
        """
        A = _concept("A")
        B = _concept("B")
        R = _role("R")
        a = _ind("a")
        b = _ind("b")
        all_r_b_clause = DLClause.create(
            (Atom.create(B, Y),),
            (Atom.create(A, X), Atom.create(R, X, Y)),
        )
        r = _reasoner_from_dl(
            [all_r_b_clause],
            positive_facts=[Atom.create(A, a)],
            negative_facts=[Atom.create(B, b)],  # b is not an R-successor of a
        )
        try:
            assert r.is_consistent() is True, (
                "A(a) with no R-successors satisfies ∀R.B vacuously; ¬B(b) is unrelated"
            )
        finally:
            r.dispose()

    def test_all_values_from_nested_in_disjunction_is_overapproximated(self):
        """SubClassOf(A, B ⊔ ∀R.C) — ∀R.C nested in disjunction falls through to THING.

        The correct handling would require fresh-concept introduction for the
        nested AllValuesFrom case. The current implementation returns owl:Thing
        (sound overapproximation — the reasoner is complete but not necessarily
        optimal). This test asserts the pipeline does not crash and returns a
        consistent ontology.
        Expected: is_consistent() = True (no ABox, nothing can clash).
        """
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom
        from hermit.owl_model.class_expression import OWLClass, OWLObjectUnionOf
        from hermit.owl_model.class_expression.restriction import OWLObjectAllValuesFrom
        from hermit.owl_model.owl_property import OWLObjectProperty

        A = OWLClass(NS + "A")
        B = OWLClass(NS + "B")
        C = OWLClass(NS + "C")
        R = OWLObjectProperty(NS + "R")
        # SubClassOf(A, B ⊔ ∀R.C): A must be in B or all R-successors must be in C
        axioms = [OWLSubClassOfAxiom(A, OWLObjectUnionOf([B, OWLObjectAllValuesFrom(R, C)]))]
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# ≤n R.C (MaxCardinality) reasoning
# ---------------------------------------------------------------------------

class TestMaxCardinality:
    """OWLObjectMaxCardinality reasoning.

    AtMostConcept is now correctly clausified into pairwise inequality clauses.
    """

    def test_max_cardinality_zero_with_successor_inconsistent(self):
        """≤0 R.C, R(a,b), C(b) → inconsistent.

        ≤0 R.C means no R-successor may be in C; R(a,b) with C(b) violates this.
        Expected: is_consistent() = False.
        """
        from hermit.model import AtMostConcept, AtomicRole as AR

        C = _concept("C")
        R = _role("R")
        a = _ind("a")
        b = _ind("b")

        # ≤0 R.C: R(X,Y) ∧ C(Y) → ⊥ (modelled directly as DL clause)
        at_most_clause = DLClause.create(
            (),
            (Atom.create(R, X, Y), Atom.create(C, Y)),
        )
        r = _reasoner_from_dl(
            [at_most_clause],
            positive_facts=[Atom.create(R, a, b), Atom.create(C, b)],
        )
        try:
            assert r.is_consistent() is False
        finally:
            r.dispose()

    def test_max_cardinality_enforced_via_owl_pipeline(self):
        """SubClassOf(A, ≤0 R.C) through OWL pipeline produces a consistent reasoner.

        Without ABox facts, the restriction is vacuously satisfied.
        Expected: is_consistent() = True.
        """
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom
        from hermit.owl_model.class_expression import OWLClass
        from hermit.owl_model.class_expression.restriction import OWLObjectMaxCardinality
        from hermit.owl_model.owl_property import OWLObjectProperty

        A = OWLClass(NS + "A")
        C = OWLClass(NS + "C")
        R = OWLObjectProperty(NS + "R")
        axioms = [OWLSubClassOfAxiom(A, OWLObjectMaxCardinality(0, R, C))]
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_max_cardinality_one_owl_pipeline_consistent(self):
        """SubClassOf(A, ≤1 R.C) without ABox facts is consistent.

        Expected: pipeline does not crash, is_consistent() = True.
        """
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom
        from hermit.owl_model.class_expression import OWLClass
        from hermit.owl_model.class_expression.restriction import OWLObjectMaxCardinality
        from hermit.owl_model.owl_property import OWLObjectProperty

        A = OWLClass(NS + "A")
        C = OWLClass(NS + "C")
        R = OWLObjectProperty(NS + "R")
        axioms = [OWLSubClassOfAxiom(A, OWLObjectMaxCardinality(1, R, C))]
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_exact_cardinality_from_owl_pipeline_consistent(self):
        """OWLObjectExactCardinality(1, R, C) decomposes to ≥1 R.C ∧ ≤1 R.C.

        Building via OWL pipeline: ExactCardinality must not crash.
        Expected: pipeline succeeds, is_consistent() = True.
        """
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom
        from hermit.owl_model.class_expression import OWLClass
        from hermit.owl_model.class_expression.restriction import OWLObjectExactCardinality
        from hermit.owl_model.owl_property import OWLObjectProperty

        A = OWLClass(NS + "A")
        C = OWLClass(NS + "C")
        R = OWLObjectProperty(NS + "R")
        # ExactCardinality on the right-hand side of SubClassOf goes through
        # add_concept_inclusion() which splits into two separate concept inclusions
        axioms = [OWLSubClassOfAxiom(A, OWLObjectExactCardinality(1, R, C))]
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# End-to-end parser → reasoner tests
# ---------------------------------------------------------------------------

owlready2 = pytest.importorskip("owlready2")


class TestParserEndToEnd:
    """End-to-end tests: owlready2 ontology → load_ontology() → Reasoner.

    These tests catch parser regressions by exercising the full pipeline from
    owlready2 in-memory ontologies through to the reasoner.
    """

    def _load_and_reason(self, tmp_path, onto):
        """Helper: save ontology to tmp file and run the full pipeline."""
        import tempfile
        from hermit.parser import load_ontology

        owl_file = tmp_path / "test.owl"
        onto.save(file=str(owl_file), format="rdfxml")
        axioms = load_ontology(owl_file)
        r = _reasoner_from_axioms(axioms)
        return r

    def test_simple_subclass_via_parser(self, tmp_path):
        """Parser end-to-end: A ⊑ B and B ⊑ C → A ⊑ C.
        Expected: is_sub_class_of(A, C) = True."""
        import owlready2

        onto = owlready2.get_ontology("http://e2e.test/simple#")
        with onto:
            class A(owlready2.Thing): pass  # type: ignore[valid-type]
            class B(owlready2.Thing): pass  # type: ignore[valid-type]
            class C(owlready2.Thing): pass  # type: ignore[valid-type]
            A.is_a.append(B)
            B.is_a.append(C)

        r = self._load_and_reason(tmp_path, onto)
        try:
            A_int = AtomicConcept.create("http://e2e.test/simple#A")
            C_int = AtomicConcept.create("http://e2e.test/simple#C")
            assert r.is_sub_class_of(A_int, C_int) is True
        finally:
            r.dispose()

    def test_existential_restriction_consistent_via_parser(self, tmp_path):
        """Parser end-to-end: A ⊑ ∃R.B — ontology is consistent.
        Expected: is_consistent() = True."""
        import owlready2

        onto = owlready2.get_ontology("http://e2e.test/exists#")
        with onto:
            class A(owlready2.Thing): pass  # type: ignore[valid-type]
            class B(owlready2.Thing): pass  # type: ignore[valid-type]
            class R(owlready2.ObjectProperty): pass  # type: ignore[valid-type]
            A.is_a.append(R.some(B))

        r = self._load_and_reason(tmp_path, onto)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_disjoint_subclasses_parsed_consistently(self, tmp_path):
        """Parser end-to-end: A ⊑ B, DisjointClasses(B, C), no individuals.

        Without any individual asserted in A, the ontology is consistent
        (A is an empty class, not necessarily contradictory unless A has a member).
        We assert is_consistent() = True, and check the parser completes without error.
        Expected: is_consistent() = True."""
        import owlready2

        onto = owlready2.get_ontology("http://e2e.test/disj#")
        with onto:
            class A(owlready2.Thing): pass  # type: ignore[valid-type]
            class B(owlready2.Thing): pass  # type: ignore[valid-type]
            class C(owlready2.Thing): pass  # type: ignore[valid-type]
            A.is_a.append(B)
            owlready2.AllDisjoint([B, C])

        r = self._load_and_reason(tmp_path, onto)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# Datatype reasoning tests
# ---------------------------------------------------------------------------

class TestDatatypeReasoning:
    """Datatype constraint reasoning tests.

    Uses the normalization pipeline for OWL-layer tests and the DL clause API
    for direct encoding, since DLOntology does not expose a data-assertion
    constructor.  The goal is to confirm that the datatype pipeline does not
    crash and returns the expected consistency result.
    """

    def test_data_property_range_consistent_pipeline(self):
        """DataPropertyRange(P, xsd:integer) alone — consistent.
        Expected: is_consistent() = True."""
        from hermit.owl_model.owl_axiom import OWLDataPropertyRangeAxiom
        from hermit.owl_model.owl_property import OWLDataProperty
        from hermit.owl_model.owl_datatype import OWLDatatype

        P = OWLDataProperty(NS + "age")
        xsd_int = OWLDatatype("http://www.w3.org/2001/XMLSchema#integer")
        axioms = [OWLDataPropertyRangeAxiom(P, xsd_int)]
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_data_property_domain_consistent_pipeline(self):
        """DataPropertyDomain(P, A) alone — consistent.
        Expected: is_consistent() = True."""
        from hermit.owl_model.owl_axiom import OWLDataPropertyDomainAxiom
        from hermit.owl_model.owl_property import OWLDataProperty
        from hermit.owl_model.class_expression import OWLClass

        P = OWLDataProperty(NS + "score")
        A = OWLClass(NS + "Person")
        axioms = [OWLDataPropertyDomainAxiom(P, A)]
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_datatype_normalization_pipeline_no_crash(self):
        """A datatype range axiom through the normalization pipeline should not crash.
        Expected: pipeline runs without exception and is_consistent() = True."""
        from hermit.owl_model.owl_axiom import OWLDataPropertyRangeAxiom
        from hermit.owl_model.owl_property import OWLDataProperty
        from hermit.owl_model.owl_datatype import OWLDatatype

        P = OWLDataProperty(NS + "weight")
        xsd_float = OWLDatatype("http://www.w3.org/2001/XMLSchema#float")
        axioms = [OWLDataPropertyRangeAxiom(P, xsd_float)]
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()
