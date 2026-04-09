"""
Class Hierarchy: Exploring the Subsumption Hierarchy

This example shows how to:
1. Build a multi-level class hierarchy
2. Compute the class hierarchy using the reasoner
3. Query subsumption relationships
4. Traverse the computed hierarchy

The reasoner automatically computes which classes are equivalent,
and the subsumption relationships between classes.
"""

from hermit import Reasoner
from hermit.model import (
    DLOntology,
    Atom,
    AtomicConcept,
    Variable,
    DLClause,
)


def main():
    # Build a simple animal hierarchy:
    #        Animal
    #       /      \
    #    Mammal   Bird
    #     /  \      |
    #   Dog Cat   Penguin
    #
    # We'll encode this as DL clauses

    X = Variable.create("X")

    # Create the atomic concepts
    animal = AtomicConcept.create("http://example.org#Animal")
    mammal = AtomicConcept.create("http://example.org#Mammal")
    bird = AtomicConcept.create("http://example.org#Bird")
    dog = AtomicConcept.create("http://example.org#Dog")
    cat = AtomicConcept.create("http://example.org#Cat")
    penguin = AtomicConcept.create("http://example.org#Penguin")

    # Build the hierarchy using subsumption clauses
    clauses = [
        # Mammal ⊑ Animal
        DLClause.create(
            (Atom.create(animal, X),),
            (Atom.create(mammal, X),),
        ),
        # Bird ⊑ Animal
        DLClause.create(
            (Atom.create(animal, X),),
            (Atom.create(bird, X),),
        ),
        # Dog ⊑ Mammal
        DLClause.create(
            (Atom.create(mammal, X),),
            (Atom.create(dog, X),),
        ),
        # Cat ⊑ Mammal
        DLClause.create(
            (Atom.create(mammal, X),),
            (Atom.create(cat, X),),
        ),
        # Penguin ⊑ Bird
        DLClause.create(
            (Atom.create(bird, X),),
            (Atom.create(penguin, X),),
        ),
    ]

    ontology = DLOntology(
        ontology_iri="urn:tutorial:animals",
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset([]),
    )

    reasoner = Reasoner(ontology)

    try:
        print("=" * 60)
        print("CLASS HIERARCHY REASONING")
        print("=" * 60)
        print()

        # Precompute the class hierarchy
        # This triggers classification of all classes
        # classification() computes:
        #   1. Which classes are equivalent
        #   2. Which classes are in subsumption relationships
        #   3. The transitive closure of subsumption
        print("Precomputing class hierarchy...")
        reasoner.precompute_inferences(class_hierarchy=True)
        print("✓ Classification complete")
        print()

        print("Direct Subsumption Relationships:")
        print("-" * 40)

        # Query direct subsumption relationships
        # Direct means: immediate parent in the hierarchy
        direct_pairs = [
            (dog, mammal, "Dog ⊑ Mammal"),
            (mammal, animal, "Mammal ⊑ Animal"),
            (penguin, bird, "Penguin ⊑ Bird"),
            (bird, animal, "Bird ⊑ Animal"),
        ]

        for sub, sup, description in direct_pairs:
            is_subclass = reasoner.is_sub_class_of(sub, sup)
            status = "✓" if is_subclass else "✗"
            print(f"{status} {description}: {is_subclass}")

        print("\nTransitive (Inferred) Subsumption Relationships:")
        print("-" * 40)
        print("These are automatically inferred by the reasoner:")

        # The reasoner automatically computes transitive closure
        # If Dog ⊑ Mammal and Mammal ⊑ Animal, then Dog ⊑ Animal
        transitive_pairs = [
            (dog, animal, "Dog ⊑ Animal (via Mammal)"),
            (cat, animal, "Cat ⊑ Animal (via Mammal)"),
            (penguin, animal, "Penguin ⊑ Animal (via Bird)"),
        ]

        for sub, sup, description in transitive_pairs:
            is_subclass = reasoner.is_sub_class_of(sub, sup)
            status = "✓" if is_subclass else "✗"
            print(f"{status} {description}: {is_subclass}")

        print("\nNegative Cases (Non-Subsumption):")
        print("-" * 40)
        print("These should be false (no subsumption relationship):")

        # Cases where there's no subsumption
        negative_pairs = [
            (dog, bird, "Dog ⊑ Bird (different branches)"),
            (cat, dog, "Cat ⊑ Dog (siblings)"),
            (penguin, mammal, "Penguin ⊑ Mammal (different branches)"),
            (animal, dog, "Animal ⊑ Dog (reverse direction)"),
        ]

        for sub, sup, description in negative_pairs:
            is_subclass = reasoner.is_sub_class_of(sub, sup)
            status = "✗" if is_subclass else "✓"  # Inverted: we want false
            print(f"{status} {description}: {is_subclass}")

        print("\nEquivalence Relationships:")
        print("-" * 40)
        print("Two concepts are equivalent if they have identical semantics")

        # Check if any classes are equivalent
        equivalence_pairs = [
            (dog, mammal, "Dog ≡ Mammal"),
            (dog, dog, "Dog ≡ Dog (always true)"),
            (mammal, animal, "Mammal ≡ Animal"),
            (dog, animal, "Dog ≡ Animal"),
        ]

        for c1, c2, description in equivalence_pairs:
            is_equiv = reasoner.is_equivalent(c1, c2)
            status = "✓" if is_equiv else "✗"
            print(f"{status} {description}: {is_equiv}")

        print("\n" + "=" * 60)
        print("Key Learning Points")
        print("=" * 60)
        print("""
1. SUBSUMPTION (⊑)
   - Sub ⊑ Super means "every Sub is a Super"
   - Example: Dog ⊑ Animal (every dog is an animal)

2. TRANSITIVE CLOSURE
   - Reasoner automatically computes: If A ⊑ B and B ⊑ C, then A ⊑ C
   - Example: Dog ⊑ Animal (inferred via Mammal)

3. EQUIVALENCE (≡)
   - C1 ≡ C2 means they have identical instances
   - Only equal if they mutually subsume each other

4. HIERARCHY COMPUTATION
   - precompute_inferences(class_hierarchy=True) computes all relationships
   - Without precomputation, queries may be slower

5. QUERY PERFORMANCE
   - Subsumption queries: O(1) after classification
   - Equivalence queries: O(1) after classification
        """)

    finally:
        reasoner.dispose()


if __name__ == "__main__":
    main()
