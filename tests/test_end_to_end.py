"""End-to-end integration tests using realistic ontologies.

These tests validate the complete reasoning pipeline from OWL files to query results.
The Pizza and Koala ontologies are standard test cases in the OWL community.

To run these tests, download the ontologies:
- Pizza: http://protege.stanford.edu/ontologies/pizza/pizza.owl
- Koala: http://protege.stanford.edu/ontologies/koala.owl

Place them in tests/ontologies/ directory.
"""

from __future__ import annotations

import pytest
from pathlib import Path

# Skip these tests if ontology files are not available
PIZZA_ONTOLOGY = Path(__file__).parent / "ontologies" / "pizza.owl"
KOALA_ONTOLOGY = Path(__file__).parent / "ontologies" / "koala.owl"

pytest.skip(
    allow_module_level=True,
    reason="Pizza and Koala ontologies not yet available in tests/ontologies/",
)


class TestPizzaOntology:
    """Test suite for the Pizza ontology.

    The Pizza ontology is a classic example in OWL education. It describes
    a domain of pizza varieties, toppings, and recipes.

    Key features:
    - Named classes: Pizza, PizzaTopping, DomainConcept
    - Object properties: hasTopping, isBaseFor
    - Data properties: hasCalories
    - Complex restrictions: some/all values from, cardinality constraints
    - Property hierarchies: subsumption relationships
    """

    @pytest.fixture
    def reasoner(self):
        """Load the Pizza ontology and create a reasoner."""
        from hermit import load_ontology, Reasoner

        try:
            ontology = load_ontology(PIZZA_ONTOLOGY)
            reasoner = Reasoner(ontology)
            reasoner.precompute_inferences(class_hierarchy=True)
            yield reasoner
            reasoner.dispose()
        except FileNotFoundError:
            pytest.skip("Pizza ontology not available")

    def test_pizza_is_consistent(self, reasoner):
        """The Pizza ontology should be consistent."""
        assert reasoner.is_consistent()

    def test_pizza_has_classes(self, reasoner):
        """The Pizza ontology should define class hierarchy."""
        from hermit.owl_model.class_expression import OWLThing
        # Get all subclasses of owl:Thing
        subclasses = reasoner.get_sub_classes(OWLThing)
        assert len(subclasses) >= 10  # Pizza ontology has ~100 classes

    def test_pizza_topping_hierarchy(self, reasoner):
        """Pizza toppings should have a subsumption hierarchy."""
        from hermit.owl_model.class_expression import OWLClass
        from hermit.owl_model.iri import IRI

        # Get the PizzaTopping class
        topping = OWLClass(IRI("http://www.co-ode.org/ontologies/pizza/pizza.owl#PizzaTopping"))

        # Get all subclasses
        subclasses = reasoner.get_sub_classes(topping)

        # PizzaTopping should have many subclasses (meat, vegetable, etc.)
        assert len(subclasses) >= 5

    def test_pizza_instances(self, reasoner):
        """Some pizza toppings should have instances."""
        from hermit.owl_model.class_expression import OWLClass
        from hermit.owl_model.iri import IRI

        # Get a specific topping class
        meat_topping = OWLClass(
            IRI("http://www.co-ode.org/ontologies/pizza/pizza.owl#MeatTopping")
        )

        # Get instances
        instances = reasoner.get_instances(meat_topping)

        # MeatTopping should have instances (Pepperoni, etc.)
        assert len(instances) >= 1


class TestKoalaOntology:
    """Test suite for the Koala ontology.

    The Koala ontology describes Australian animals and their characteristics.
    It's a smaller ontology than Pizza but includes interesting features like
    inverse properties and property domains/ranges.

    Key features:
    - Animal classes and hierarchies
    - Properties like eats, liveIn, hasHabitat
    - Inverse property relationships
    - Functional properties (sex)
    - Transitive properties (ancestorOf)
    """

    @pytest.fixture
    def reasoner(self):
        """Load the Koala ontology and create a reasoner."""
        from hermit import load_ontology, Reasoner

        try:
            ontology = load_ontology(KOALA_ONTOLOGY)
            reasoner = Reasoner(ontology)
            reasoner.precompute_inferences(class_hierarchy=True)
            yield reasoner
            reasoner.dispose()
        except FileNotFoundError:
            pytest.skip("Koala ontology not available")

    def test_koala_is_consistent(self, reasoner):
        """The Koala ontology should be consistent."""
        assert reasoner.is_consistent()

    def test_koala_has_animals(self, reasoner):
        """The Koala ontology should define animal classes."""
        from hermit.owl_model.class_expression import OWLThing

        subclasses = reasoner.get_sub_classes(OWLThing)
        assert len(subclasses) >= 5

    def test_koala_animal_hierarchy(self, reasoner):
        """Animal classes should have a subsumption hierarchy."""
        from hermit.owl_model.class_expression import OWLClass
        from hermit.owl_model.iri import IRI

        # Get the Animal class
        animal = OWLClass(IRI("http://www.protege.stanford.edu/ontologies/koala.owl#Animal"))

        # Get subclasses
        subclasses = reasoner.get_sub_classes(animal)

        # Should have several animal types
        assert len(subclasses) >= 3

    def test_koala_koala_specialization(self, reasoner):
        """Koala should be a type of animal with specific properties."""
        from hermit.owl_model.class_expression import OWLClass
        from hermit.owl_model.iri import IRI

        koala = OWLClass(IRI("http://www.protege.stanford.edu/ontologies/koala.owl#Koala"))
        animal = OWLClass(IRI("http://www.protege.stanford.edu/ontologies/koala.owl#Animal"))

        # Koala should be subsumed by Animal
        assert reasoner.is_sub_class_of(koala, animal)


class TestEndToEndPipeline:
    """Test the complete reasoning pipeline."""

    def test_load_and_reason_simple(self):
        """Test parsing and reasoning on a simple inline ontology."""
        from hermit import Reasoner
        from hermit.model import DLOntology, Atom, AtomicConcept, Variable, DLClause

        # Create a simple ontology: Dog ⊑ Animal
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
            positive_facts=frozenset([]),
        )

        reasoner = Reasoner(ontology)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.is_consistent()
            assert reasoner.is_sub_class_of(dog, animal)
        finally:
            reasoner.dispose()

    def test_parser_integration(self):
        """Test that the parser integrates with the reasoner pipeline."""
        # This test would require an OWL file to be present
        # For now, it documents the expected workflow

        # Workflow:
        # 1. from hermit import load_ontology
        # 2. axioms = load_ontology("ontology.owl")  # returns OWLAxiom objects
        # 3. # Convert axioms to DLOntology (via normalization pipeline)
        # 4. reasoner = Reasoner(dl_ontology)
        # 5. reasoner.precompute_inferences()
        # 6. # Query: is_consistent, is_sub_class_of, get_sub_classes, etc.

        pytest.skip("Requires OWL file input")
