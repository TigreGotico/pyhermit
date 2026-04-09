"""
Loading OWL Files: Working with Real Ontologies

This example demonstrates:
1. Loading OWL ontologies from files
2. Working with existing ontologies (e.g., Pizza, Koala)
3. Exploring ontologies programmatically
4. Handling different OWL syntaxes (RDF/XML, Functional Syntax, TTL)
5. Performance considerations with large ontologies

NOTE: This example requires an OWL file to be present.
The Pizza ontology (a classic example) can be downloaded from:
  http://protege.stanford.edu/ontologies/pizza/pizza.owl
"""

from pathlib import Path
from hermit import Reasoner, load_ontology


def main():
    # Path to an OWL file
    # You can download example ontologies:
    # - Pizza: http://protege.stanford.edu/ontologies/pizza/pizza.owl
    # - Koala: http://protege.stanford.edu/ontologies/koala.owl

    ontology_path = Path(__file__).parent / "resources" / "example.owl"

    if not ontology_path.exists():
        print("=" * 60)
        print("OWL File Not Found")
        print("=" * 60)
        print()
        print(f"Expected file: {ontology_path}")
        print()
        print("To use this example, you need to:")
        print()
        print("1. Download an OWL ontology:")
        print("   • Pizza: http://protege.stanford.edu/ontologies/pizza/pizza.owl")
        print("   • Koala: http://protege.stanford.edu/ontologies/koala.owl")
        print()
        print("2. Place it in the 'resources' folder (examples/resources/)")
        print()
        print("3. Update the 'ontology_path' variable in this script")
        print()
        print("=" * 60)
        print()
        print("For now, showing how you would use the library with OWL files...")
        print()
        show_usage_example()
        return

    print("=" * 60)
    print(f"Loading Ontology: {ontology_path.name}")
    print("=" * 60)
    print()

    try:
        # Load the ontology from file
        # The load_ontology function supports RDF/XML and Functional Syntax
        ontology = load_ontology(ontology_path)
        print(f"✓ Ontology loaded successfully")
        print()

        # Create a reasoner for the ontology
        reasoner = Reasoner(ontology)

        try:
            print("Performing initial consistency check...")
            is_consistent = reasoner.is_consistent()
            print(f"Ontology is consistent: {is_consistent}")
            print()

            if is_consistent:
                print("Computing class hierarchy (this may take a moment)...")
                reasoner.precompute_inferences(class_hierarchy=True)
                print("✓ Hierarchy computed")
                print()

                # Get all classes
                from hermit.owl_model.class_expression import OWLThing
                all_classes = reasoner.get_sub_classes(OWLThing)
                print(f"Total classes in ontology: {len(all_classes)}")
                print()

                # Show first 10 classes
                print("Sample classes:")
                for cls in list(all_classes)[:10]:
                    print(f"  - {cls.iri}")
                print()

                # Explore specific relationships
                print("Class Hierarchy Examples:")
                print("-" * 40)
                if len(all_classes) >= 2:
                    classes_list = list(all_classes)
                    for i, cls in enumerate(classes_list[:3]):
                        subclasses = reasoner.get_sub_classes(cls)
                        if subclasses:
                            print(f"\nSubclasses of {cls.iri.split('#')[-1]}:")
                            for sub in list(subclasses)[:3]:
                                print(f"  ⊑ {sub.iri.split('#')[-1]}")

            else:
                print("⚠️  Ontology is INCONSISTENT")
                print("The ontology contains contradictory axioms.")
                print()

        finally:
            reasoner.dispose()

    except ImportError:
        print("⚠️  OWL API not available")
        print()
        print("To load OWL files, you need to install owlready2:")
        print("  pip install owlready2")
        print()
        show_usage_example()

    except Exception as e:
        print(f"✗ Error loading ontology: {e}")
        print()
        print("Make sure the file is a valid OWL ontology in one of these formats:")
        print("  • RDF/XML (.owl)")
        print("  • Functional Syntax (.fss)")
        print("  • Turtle (.ttl)")


def show_usage_example():
    """Show example code for loading and using OWL files."""
    print("Example usage (once owlready2 is installed):")
    print("=" * 60)
    print("""
# Python code to load and reason about an OWL ontology:

from pathlib import Path
from hermit import load_ontology, Reasoner

# Load an OWL file
ontology = load_ontology("pizza.owl")
reasoner = Reasoner(ontology)

try:
    # Check consistency
    if reasoner.is_consistent():
        print("Ontology is consistent")

        # Compute inferences
        reasoner.precompute_inferences(class_hierarchy=True)

        # Get the class hierarchy
        from hermit.owl_model.class_expression import OWLThing
        classes = reasoner.get_sub_classes(OWLThing)
        for cls in classes:
            print(f"Class: {cls.iri}")

        # Query specific classes
        # Example: Find all Pizza classes
        # pizza_class = ...
        # pizza_instances = reasoner.get_instances(pizza_class)

finally:
    reasoner.dispose()
    """)
    print("=" * 60)


if __name__ == "__main__":
    main()
