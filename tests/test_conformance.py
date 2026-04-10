"""OWL 2 conformance tests.

Tests reasoning correctness against known ontology patterns from the OWL 2
primer and reference test suite.  These test the full pipeline:

  OWL axioms → OWLNormalization → OWLClausification → Tableau → answer

All tests build ontologies programmatically (no file I/O) to avoid network
or file-system dependencies.  Patterns are drawn from:
- The OWL 2 Primer (koala / pizza examples)
- The W3C OWL 2 test cases
"""

from __future__ import annotations

import pytest

from hermit.model import AtomicConcept, Individual, Atom, AtomicRole, Variable
from hermit.model import DLOntology, DLClause
from hermit.structural.owl_normalization import OWLNormalization
from hermit.structural.owl_clausification import OWLClausification
from hermit.reasoner import Reasoner

NS = "http://conformance.test#"

X = Variable.create("X")
Y = Variable.create("Y")


def _reasoner_from_axioms(axioms: list) -> Reasoner:
    norm = OWLNormalization()
    normalized = norm.process_ontology(axioms)
    claus = OWLClausification()
    dl_onto = claus.clausify(normalized, ontology_iri="urn:test:conformance")
    return Reasoner(dl_onto)


def _reasoner_from_dl(
    clauses: list[DLClause],
    positive_facts: list[Atom] | None = None,
    negative_facts: list[Atom] | None = None,
) -> Reasoner:
    dl_onto = DLOntology(
        ontology_iri="urn:test:conformance",
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset(positive_facts or []),
        negative_facts=frozenset(negative_facts or []),
    )
    return Reasoner(dl_onto)


# ---------------------------------------------------------------------------
# OWL 2 Primer: Koala-family patterns
# ---------------------------------------------------------------------------

class TestKoalaPatterns:
    """Reasoning patterns from the OWL 2 Primer koala ontology.

    The koala ontology defines a family taxonomy with marsupials, koalas,
    habitats, and various restrictions.  These tests reproduce key reasoning
    conclusions using equivalent axioms.
    """

    def test_subclass_chain_transitive(self):
        """KoalaWithPhD ⊑ Koala ⊑ Marsupial.

        Encoding: explicit SubClassOf chain.
        Expected: KoalaWithPhD is subsumed by Marsupial.
        """
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom
        from hermit.owl_model.class_expression import OWLClass

        KoalaWithPhD = OWLClass(NS + "KoalaWithPhD")
        Koala = OWLClass(NS + "Koala")
        Marsupial = OWLClass(NS + "Marsupial")

        axioms = [
            OWLSubClassOfAxiom(KoalaWithPhD, Koala),
            OWLSubClassOfAxiom(Koala, Marsupial),
        ]
        r = _reasoner_from_axioms(axioms)
        try:
            phd = AtomicConcept.create(NS + "KoalaWithPhD")
            marsupial = AtomicConcept.create(NS + "Marsupial")
            assert r.is_sub_class_of(phd, marsupial) is True, (
                "KoalaWithPhD must be subsumed by Marsupial via transitivity"
            )
        finally:
            r.dispose()

    def test_disjoint_classes_inconsistency(self):
        """DisjointClasses(Koala, Wombat) with individual in both → inconsistent.

        Expected: is_consistent() = False.
        """
        Koala = AtomicConcept.create(NS + "Koala")
        Wombat = AtomicConcept.create(NS + "Wombat")
        individual_a = Individual.create(NS + "a")

        disj = DLClause.create((), (Atom.create(Koala, X), Atom.create(Wombat, X)))
        r = _reasoner_from_dl(
            [disj],
            positive_facts=[Atom.create(Koala, individual_a), Atom.create(Wombat, individual_a)],
        )
        try:
            assert r.is_consistent() is False, (
                "Individual asserted in two disjoint classes must cause inconsistency"
            )
        finally:
            r.dispose()

    def test_existential_restriction_satisfiable(self):
        """A ⊑ ∃hasHabitat.Forest is satisfiable.

        Expected: A is satisfiable (not ⊑ ⊥).
        """
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom
        from hermit.owl_model.class_expression import OWLClass
        from hermit.owl_model.class_expression.restriction import OWLObjectSomeValuesFrom
        from hermit.owl_model.owl_property import OWLObjectProperty

        A = OWLClass(NS + "A")
        Forest = OWLClass(NS + "Forest")
        hasHabitat = OWLObjectProperty(NS + "hasHabitat")

        axioms = [OWLSubClassOfAxiom(A, OWLObjectSomeValuesFrom(hasHabitat, Forest))]
        r = _reasoner_from_axioms(axioms)
        try:
            a_concept = AtomicConcept.create(NS + "A")
            assert r.is_satisfiable(a_concept) is True, (
                "A with existential restriction ∃hasHabitat.Forest must be satisfiable"
            )
        finally:
            r.dispose()

    def test_unsatisfiable_class_makes_existential_inconsistent(self):
        """A ⊑ ∃R.B, B ⊑ ⊥ (B unsatisfiable) → A is unsatisfiable.

        B is asserted subsumed by Nothing (⊥), so ∃R.B is unsatisfiable,
        and therefore A is unsatisfiable.
        Expected: is_satisfiable(A) = False.
        """
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom
        from hermit.owl_model.class_expression import OWLClass, OWLNothing
        from hermit.owl_model.class_expression.restriction import OWLObjectSomeValuesFrom
        from hermit.owl_model.owl_property import OWLObjectProperty

        A = OWLClass(NS + "A")
        B = OWLClass(NS + "B")
        R = OWLObjectProperty(NS + "R")

        axioms = [
            OWLSubClassOfAxiom(A, OWLObjectSomeValuesFrom(R, B)),
            OWLSubClassOfAxiom(B, OWLNothing),
        ]
        r = _reasoner_from_axioms(axioms)
        try:
            a_concept = AtomicConcept.create(NS + "A")
            assert r.is_satisfiable(a_concept) is False, (
                "A with ∃R.B where B⊑⊥ must be unsatisfiable"
            )
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# OWL 2 Primer: Pizza-family patterns
# ---------------------------------------------------------------------------

class TestPizzaPatterns:
    """Reasoning patterns from the OWL 2 Primer pizza ontology."""

    def test_pizza_with_topping_satisfiable(self):
        """Pizza ⊑ ∃hasTopping.CheeseTopping is satisfiable.

        Expected: Pizza is satisfiable.
        """
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom
        from hermit.owl_model.class_expression import OWLClass
        from hermit.owl_model.class_expression.restriction import OWLObjectSomeValuesFrom
        from hermit.owl_model.owl_property import OWLObjectProperty

        Pizza = OWLClass(NS + "Pizza")
        CheeseTopping = OWLClass(NS + "CheeseTopping")
        hasTopping = OWLObjectProperty(NS + "hasTopping")

        axioms = [OWLSubClassOfAxiom(Pizza, OWLObjectSomeValuesFrom(hasTopping, CheeseTopping))]
        r = _reasoner_from_axioms(axioms)
        try:
            pizza = AtomicConcept.create(NS + "Pizza")
            assert r.is_satisfiable(pizza) is True
        finally:
            r.dispose()

    def test_nothing_not_satisfiable(self):
        """owl:Nothing is always unsatisfiable.

        Expected: is_satisfiable(NOTHING) = False.
        """
        r = _reasoner_from_dl([])
        try:
            assert r.is_satisfiable(AtomicConcept.NOTHING) is False
        finally:
            r.dispose()

    def test_thing_always_satisfiable(self):
        """owl:Thing is always satisfiable.

        Expected: is_satisfiable(THING) = True.
        """
        r = _reasoner_from_dl([])
        try:
            assert r.is_satisfiable(AtomicConcept.THING) is True
        finally:
            r.dispose()

    def test_disjoint_toppings_consistent(self):
        """DisjointClasses(CheeseTopping, MeatTopping) with CheeseTopping(a) → consistent.

        A single individual in one of two disjoint classes is fine.
        Expected: is_consistent() = True.
        """
        CheeseTopping = AtomicConcept.create(NS + "CheeseTopping")
        MeatTopping = AtomicConcept.create(NS + "MeatTopping")
        a = Individual.create(NS + "a")

        disj = DLClause.create((), (Atom.create(CheeseTopping, X), Atom.create(MeatTopping, X)))
        r = _reasoner_from_dl(
            [disj],
            positive_facts=[Atom.create(CheeseTopping, a)],
        )
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_role_subsumption_via_direct_clause(self):
        """hasTopping(a, b) ∧ hasTopping ⊑ hasIngredient → hasIngredient(a, b).

        Encoded as DL clause: hasTopping(X,Y) → hasIngredient(X,Y).
        Query: is the ontology consistent if hasIngredient(a,b) is asserted
        and also ¬hasIngredient(a,b)?  Expected: False (contradiction).
        """
        hasTopping = AtomicRole.create(NS + "hasTopping")
        hasIngredient = AtomicRole.create(NS + "hasIngredient")
        a = Individual.create(NS + "a")
        b = Individual.create(NS + "b")

        # hasTopping(X,Y) → hasIngredient(X,Y)
        subprop_clause = DLClause.create(
            (Atom.create(hasIngredient, X, Y),),
            (Atom.create(hasTopping, X, Y),),
        )
        from hermit.model import Inequality
        # ¬hasIngredient(a,b): model it as negative fact
        r = _reasoner_from_dl(
            [subprop_clause],
            positive_facts=[Atom.create(hasTopping, a, b)],
            negative_facts=[Atom.create(hasIngredient, a, b)],
        )
        try:
            assert r.is_consistent() is False, (
                "Deriving hasIngredient(a,b) from subproperty while asserting its negation must clash"
            )
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# OWL file loading tests (require owlready2)
# ---------------------------------------------------------------------------

import os as _os
_ONTOLOGIES = _os.path.join(_os.path.dirname(__file__), "ontologies")

_owlready2 = pytest.importorskip("owlready2")


class TestOwlFileLoading:
    """Load real .owl files with owlready2 and verify reasoning."""

    KOALA_IRI = "http://protege.stanford.edu/plugins/owl/owl-library/koala.owl"
    PIZZA_IRI = "http://www.co-ode.org/ontologies/pizza/pizza.owl"

    def test_koala_subclass_chain(self):
        """KoalaWithPhD ⊑ Koala ⊑ Marsupial — transitive subclass chain.

        Expected: is_sub_class_of(KoalaWithPhD, Marsupial) = True.
        """
        from hermit.parser import load_ontology
        axioms = load_ontology(_os.path.join(_ONTOLOGIES, "koala.owl"))
        r = _reasoner_from_axioms(axioms)
        try:
            phd = AtomicConcept.create(self.KOALA_IRI + "#KoalaWithPhD")
            marsupial = AtomicConcept.create(self.KOALA_IRI + "#Marsupial")
            assert r.is_sub_class_of(phd, marsupial) is True
        finally:
            r.dispose()

    def test_koala_consistent(self):
        """Koala ontology is globally consistent (no ABox contradictions).

        Expected: is_consistent() = True.
        """
        from hermit.parser import load_ontology
        axioms = load_ontology(_os.path.join(_ONTOLOGIES, "koala.owl"))
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_koala_disjoint_koala_forest(self):
        """Koala and Forest are declared disjoint — neither subsumes the other.

        Expected: is_sub_class_of(Koala, Forest) = False.
        """
        from hermit.parser import load_ontology
        axioms = load_ontology(_os.path.join(_ONTOLOGIES, "koala.owl"))
        r = _reasoner_from_axioms(axioms)
        try:
            koala = AtomicConcept.create(self.KOALA_IRI + "#Koala")
            forest = AtomicConcept.create(self.KOALA_IRI + "#Forest")
            assert r.is_sub_class_of(koala, forest) is False
        finally:
            r.dispose()

    def test_pizza_consistent(self):
        """Pizza ontology is globally consistent.

        Expected: is_consistent() = True.
        """
        from hermit.parser import load_ontology
        axioms = load_ontology(_os.path.join(_ONTOLOGIES, "pizza.owl"))
        r = _reasoner_from_axioms(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_pizza_cheese_subclass_topping(self):
        """CheeseTopping ⊑ PizzaTopping in the pizza ontology.

        Expected: is_sub_class_of(CheeseTopping, PizzaTopping) = True.
        """
        from hermit.parser import load_ontology
        axioms = load_ontology(_os.path.join(_ONTOLOGIES, "pizza.owl"))
        r = _reasoner_from_axioms(axioms)
        try:
            cheese = AtomicConcept.create(self.PIZZA_IRI + "#CheeseTopping")
            topping = AtomicConcept.create(self.PIZZA_IRI + "#PizzaTopping")
            assert r.is_sub_class_of(cheese, topping) is True
        finally:
            r.dispose()
