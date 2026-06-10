"""
Loading OWL Files: Working with Real Ontologies

This example demonstrates:
1. Loading OWL ontologies from files with the stdlib reader
2. Compiling loaded axioms into a Reasoner (normalize -> clausify)
3. Exploring a loaded ontology programmatically
4. The OWL syntaxes the loader understands (RDF/XML, OWL/XML,
   Functional-Style Syntax)

The loader is `hermit.parser.load_ontology` — pure standard library, no
external dependencies. It returns the same `hermit.owl_model` axiom objects
you would build by hand, so loaded and hand-built ontologies go through the
identical pipeline.

A small pizza ontology ships in examples/resources/example.owl. Classic
public test ontologies work the same way, e.g. the Pizza ontology from
https://protege.stanford.edu/ontologies/pizza/pizza.owl
"""

import sys
from pathlib import Path

from hermit import Reasoner
from hermit.model import AtomicConcept, Individual
from hermit.parser import load_ontology
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization


def reasoner_from_file(path):
    """Load an OWL document and compile it into a Reasoner.

    Pipeline: load_ontology -> OWLNormalization -> OWLClausification -> Reasoner
    """
    axioms = load_ontology(path)
    print(f"✓ Loaded {len(axioms)} axioms from {Path(path).name}")

    normalized = OWLNormalization().process_ontology(axioms)
    dl_ontology = OWLClausification().clausify(
        normalized, ontology_iri=Path(path).stem
    )
    return Reasoner(dl_ontology)


def main():
    ontology_path = Path(__file__).parent / "resources" / "example.owl"

    print("=" * 60)
    print(f"Loading Ontology: {ontology_path.name}")
    print("=" * 60)
    print()

    try:
        reasoner = reasoner_from_file(ontology_path)
    except FileNotFoundError:
        print(f"✗ File not found: {ontology_path}")
        return
    except ValueError as e:
        print(f"✗ Error parsing ontology: {e}")
        print()
        print("Supported formats:")
        print("  • RDF/XML (.owl, .rdf)")
        print("  • OWL/XML (.owx, .owl)")
        print("  • Functional-Style Syntax (.ofn)")
        return

    try:
        print()
        print("Performing initial consistency check...")
        is_consistent = reasoner.is_consistent()
        print(f"Ontology is consistent: {is_consistent}")
        print()

        if not is_consistent:
            print("⚠️  Ontology is INCONSISTENT")
            print("The ontology contains contradictory axioms.")
            return

        print("Computing class hierarchy...")
        reasoner.precompute_inferences(class_hierarchy=True)
        print("✓ Hierarchy computed")
        print()

        # Basic statistics about the compiled ontology
        stats = reasoner.stats
        print(f"Atomic concepts: {stats['atomic_concepts']}")
        print(f"DL clauses:      {stats['clauses']}")
        print(f"Individuals:     {stats['individuals']}")
        print()

        # Print the inferred class hierarchy
        print("Inferred class hierarchy:")
        print("-" * 40)
        reasoner.dump_hierarchies(sys.stdout, classes=True)
        print()

        # Query specific relationships from the pizza ontology
        ns = "http://example.org/pizza#"
        margherita = AtomicConcept.create(ns + "MargheritaPizza")
        vegetarian = AtomicConcept.create(ns + "VegetarianPizza")
        food = AtomicConcept.create(ns + "Food")

        print("Sample queries:")
        print("-" * 40)

        # Subsumption chain through the hierarchy
        print(f"MargheritaPizza ⊑ Food: "
              f"{reasoner.is_sub_class_of(margherita, food)}")

        # A non-trivial inference: Margherita pizzas only have cheese or
        # vegetable toppings, so they are vegetarian.
        print(f"MargheritaPizza ⊑ VegetarianPizza: "
              f"{reasoner.is_sub_class_of(margherita, vegetarian)}")

        # ABox: the individual inherits the inferred classification
        my_pizza = Individual.create(ns + "myMargherita")
        print(f"myMargherita is a VegetarianPizza: "
              f"{reasoner.has_type(my_pizza, vegetarian)}")

    finally:
        reasoner.dispose()


if __name__ == "__main__":
    main()
