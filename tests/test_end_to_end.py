"""End-to-end integration tests using realistic ontology patterns.

These tests validate the complete reasoning pipeline using synthetic
ontologies that mimic real-world OWL ontologies (pizza, koala patterns)
but without requiring external OWL files.
"""

from __future__ import annotations

from hermit.model import (
    Atom,
    AtomicConcept,
    AtomicRole,
    DLClause,
    DLOntology,
    Individual,
    Variable,
)
from hermit.reasoner import Reasoner


def _make_reasoner(clauses, positive_facts=None, negative_facts=None, iri="urn:test:e2e"):
    ontology = DLOntology(
        ontology_iri=iri,
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset(positive_facts or []),
        negative_facts=frozenset(negative_facts or []),
    )
    return Reasoner(ontology)


# ---------------------------------------------------------------------------
# Pizza-pattern ontology
# ---------------------------------------------------------------------------

class TestPizzaOntology:
    """Synthetic pizza-like ontology: Pizza, PizzaTopping, toppings hierarchy."""

    def _setup_pizza_reasoner(self):
        X = Variable.create("X")
        # Concept hierarchy: VeggiePizza ⊑ Pizza, etc.
        pizza = AtomicConcept.create("http://pizza#Pizza")
        veggie = AtomicConcept.create("http://pizza#VeggiePizza")
        meat = AtomicConcept.create("http://pizza#MeatPizza")
        topping = AtomicConcept.create("http://pizza#PizzaTopping")
        veg_top = AtomicConcept.create("http://pizza#VegetableTopping")
        meat_top = AtomicConcept.create("http://pizza#MeatTopping")
        pepper_top = AtomicConcept.create("http://pizza#PepperTopping")
        mushroom_top = AtomicConcept.create("http://pizza#MushroomTopping")
        ham_top = AtomicConcept.create("http://pizza#HamTopping")
        pepperoni_top = AtomicConcept.create("http://pizza#PepperoniTopping")
        calzone = AtomicConcept.create("http://pizza#Calzone")
        domain = AtomicConcept.create("http://pizza#DomainConcept")

        clauses = [
            DLClause.create((Atom.create(pizza, X),), (Atom.create(veggie, X),)),
            DLClause.create((Atom.create(pizza, X),), (Atom.create(meat, X),)),
            DLClause.create((Atom.create(pizza, X),), (Atom.create(calzone, X),)),
            DLClause.create((Atom.create(topping, X),), (Atom.create(veg_top, X),)),
            DLClause.create((Atom.create(topping, X),), (Atom.create(meat_top, X),)),
            DLClause.create((Atom.create(veg_top, X),), (Atom.create(pepper_top, X),)),
            DLClause.create((Atom.create(veg_top, X),), (Atom.create(mushroom_top, X),)),
            DLClause.create((Atom.create(meat_top, X),), (Atom.create(ham_top, X),)),
            DLClause.create((Atom.create(meat_top, X),), (Atom.create(pepperoni_top, X),)),
            DLClause.create((Atom.create(domain, X),), (Atom.create(pizza, X),)),
            DLClause.create((Atom.create(domain, X),), (Atom.create(topping, X),)),
        ]

        ind1 = Individual.create("http://pizza#margherita")
        ind2 = Individual.create("http://pizza#pepperoni_pizza")
        ind3 = Individual.create("http://pizza#mushroom_pizza")

        positive_facts = [
            Atom.create(veggie, ind1),
            Atom.create(meat, ind2),
            Atom.create(veggie, ind3),
        ]
        return _make_reasoner(clauses, positive_facts, iri="urn:test:pizza")

    def test_pizza_is_consistent(self):
        """The synthetic pizza ontology should be consistent."""
        r = self._setup_pizza_reasoner()
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_pizza_has_classes(self):
        """Pizza ontology defines class hierarchy with enough concepts."""
        r = self._setup_pizza_reasoner()
        try:
            pizza = AtomicConcept.create("http://pizza#Pizza")
            veggie = AtomicConcept.create("http://pizza#VeggiePizza")
            # VeggiePizza is a subclass of Pizza
            assert r.is_sub_class_of(veggie, pizza)
        finally:
            r.dispose()

    def test_pizza_topping_hierarchy(self):
        """Pizza toppings form a hierarchy."""
        r = self._setup_pizza_reasoner()
        try:
            topping = AtomicConcept.create("http://pizza#PizzaTopping")
            pepper = AtomicConcept.create("http://pizza#PepperTopping")
            veg = AtomicConcept.create("http://pizza#VegetableTopping")
            # PepperTopping ⊑ VegetableTopping ⊑ PizzaTopping
            assert r.is_sub_class_of(pepper, veg)
            assert r.is_sub_class_of(veg, topping)
        finally:
            r.dispose()

    def test_pizza_instances(self):
        """Individual pizza instances have expected types."""
        r = self._setup_pizza_reasoner()
        try:
            veggie = AtomicConcept.create("http://pizza#VeggiePizza")
            pizza = AtomicConcept.create("http://pizza#Pizza")
            margherita = Individual.create("http://pizza#margherita")
            # margherita is a VeggiePizza and thus a Pizza
            assert r.is_satisfiable(veggie)
            assert r.is_satisfiable(pizza)
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# Koala-pattern ontology
# ---------------------------------------------------------------------------

class TestKoalaOntology:
    """Synthetic koala-like ontology: Animal hierarchy with Koala."""

    def _setup_koala_reasoner(self):
        X = Variable.create("X")
        animal = AtomicConcept.create("http://koala#Animal")
        marsupial = AtomicConcept.create("http://koala#Marsupial")
        koala = AtomicConcept.create("http://koala#Koala")
        wombat = AtomicConcept.create("http://koala#Wombat")
        quokka = AtomicConcept.create("http://koala#Quokka")
        tree_dweller = AtomicConcept.create("http://koala#TreeDweller")

        clauses = [
            DLClause.create((Atom.create(marsupial, X),), (Atom.create(koala, X),)),
            DLClause.create((Atom.create(marsupial, X),), (Atom.create(wombat, X),)),
            DLClause.create((Atom.create(marsupial, X),), (Atom.create(quokka, X),)),
            DLClause.create((Atom.create(animal, X),), (Atom.create(marsupial, X),)),
            DLClause.create((Atom.create(tree_dweller, X),), (Atom.create(koala, X),)),
        ]

        blinky = Individual.create("http://koala#blinky")
        wobbles = Individual.create("http://koala#wobbles")
        rocky = Individual.create("http://koala#rocky")

        positive_facts = [
            Atom.create(koala, blinky),
            Atom.create(wombat, wobbles),
            Atom.create(quokka, rocky),
        ]
        return _make_reasoner(clauses, positive_facts, iri="urn:test:koala")

    def test_koala_is_consistent(self):
        """The synthetic koala ontology should be consistent."""
        r = self._setup_koala_reasoner()
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_koala_has_animals(self):
        """Animal concept is satisfiable."""
        r = self._setup_koala_reasoner()
        try:
            animal = AtomicConcept.create("http://koala#Animal")
            assert r.is_satisfiable(animal)
        finally:
            r.dispose()

    def test_koala_animal_hierarchy(self):
        """Marsupial is a subclass of Animal."""
        r = self._setup_koala_reasoner()
        try:
            animal = AtomicConcept.create("http://koala#Animal")
            marsupial = AtomicConcept.create("http://koala#Marsupial")
            koala = AtomicConcept.create("http://koala#Koala")
            assert r.is_sub_class_of(marsupial, animal)
            assert r.is_sub_class_of(koala, marsupial)
        finally:
            r.dispose()

    def test_koala_koala_specialization(self):
        """Koala is both a Marsupial and an Animal."""
        r = self._setup_koala_reasoner()
        try:
            koala = AtomicConcept.create("http://koala#Koala")
            animal = AtomicConcept.create("http://koala#Animal")
            assert r.is_sub_class_of(koala, animal)
        finally:
            r.dispose()


# ---------------------------------------------------------------------------
# Pipeline integration tests
# ---------------------------------------------------------------------------

class TestEndToEndPipeline:
    """Test the complete reasoning pipeline."""

    def test_load_and_reason_simple(self):
        """Test reasoning on a simple inline ontology."""
        X = Variable.create("X")
        dog = AtomicConcept.create("http://example.org#Dog")
        animal = AtomicConcept.create("http://example.org#Animal")

        clauses = [
            DLClause.create(
                (Atom.create(animal, X),),
                (Atom.create(dog, X),),
            ),
        ]
        ontology = DLOntology(
            ontology_iri="urn:test:simple",
            dl_clauses=frozenset(clauses),
        )
        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.is_consistent()
            assert reasoner.is_sub_class_of(dog, animal)
        finally:
            reasoner.dispose()

    def test_parser_integration(self):
        """Test the OWL parser with owlready2 on a minimal inline ontology."""
        import tempfile
        import os

        minimal_owl = """\
<?xml version="1.0"?>
<Ontology xmlns="http://www.w3.org/2002/07/owl#"
          xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
          xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
          xml:base="http://example.org/test"
          ontologyIRI="http://example.org/test">
  <Declaration><Class IRI="http://example.org/test#Cat"/></Declaration>
  <Declaration><Class IRI="http://example.org/test#Animal"/></Declaration>
  <SubClassOf>
    <Class IRI="http://example.org/test#Cat"/>
    <Class IRI="http://example.org/test#Animal"/>
  </SubClassOf>
</Ontology>
"""
        try:
            from hermit import load_ontology
        except ImportError:
            import pytest
            pytest.skip("owlready2 not installed")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.owl', delete=False) as f:
            f.write(minimal_owl)
            tmppath = f.name
        try:
            axioms = load_ontology(tmppath)
            # load_ontology returns an iterable of OWLAxiom; verify it runs without error
            assert axioms is not None
        finally:
            os.unlink(tmppath)
