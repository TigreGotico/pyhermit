"""
Hello World: Load an Ontology and Check Consistency

This example demonstrates the most basic PyHermit workflow:
1. Create or load an ontology
2. Create a reasoner
3. Check if the ontology is consistent
4. Clean up resources

A consistent ontology means there exists at least one model (interpretation)
that satisfies all the axioms. An inconsistent ontology has no models.
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
    # Create a simple ontology: Dog ⊑ Animal
    # This says "every dog is an animal"

    X = Variable.create("X")
    dog = AtomicConcept.create("http://example.org#Dog")
    animal = AtomicConcept.create("http://example.org#Animal")

    # DL clauses are the compiled form of OWL axioms
    # This clause implements the subsumption: Dog ⊑ Animal
    # Structure: DLClause.create(head, body)
    #   head: conclusions to derive
    #   body: premises that must be true
    # This clause says: "If X is a dog, then X is an animal"
    clauses = [
        DLClause.create(
            (Atom.create(animal, X),),  # consequent (head): animal(X)
            (Atom.create(dog, X),),     # antecedent (body): dog(X)
        ),
    ]

    # Create the ontology
    # ontology_iri: unique identifier for this ontology
    # dl_clauses: the terminological box (TBox) - class definitions
    # positive_facts: the assertional box (ABox) - facts about individuals
    ontology = DLOntology(
        ontology_iri="urn:tutorial:animals",
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset([]),  # no facts (ABox) in this example
    )

    # Create a reasoner to answer queries about the ontology
    # The reasoner uses the HermiT tableau algorithm to derive inferences
    reasoner = Reasoner(ontology)

    try:
        print("=" * 60)
        print("HELLO WORLD: Basic Consistency Checking")
        print("=" * 60)
        print()

        # Query 1: Check consistency
        # For this simple ontology, it should be consistent
        # An inconsistent ontology means there's a logical contradiction
        is_consistent = reasoner.is_consistent()
        print(f"1. Ontology is consistent: {is_consistent}")
        print("   (No logical contradictions found)")
        print()

        # Query 2: Check if Dog is satisfiable
        # Satisfiable means: it's logically possible for something to be a Dog
        # (not contradicted by the ontology axioms)
        dog_satisfiable = reasoner.is_satisfiable(dog)
        print(f"2. Dog is satisfiable: {dog_satisfiable}")
        print("   (A dog can exist without contradiction)")
        print()

        # Query 3: Check if Animal is satisfiable
        animal_satisfiable = reasoner.is_satisfiable(animal)
        print(f"3. Animal is satisfiable: {animal_satisfiable}")
        print()

        # Query 4: Check subsumption (is Dog a subclass of Animal?)
        # is_sub_class_of(sub, super) returns True if sub ⊑ super
        dog_is_subclass_of_animal = reasoner.is_sub_class_of(dog, animal)
        print(f"4. Dog ⊑ Animal (subsumption): {dog_is_subclass_of_animal}")
        print("   (Every dog is an animal)")
        print()

        # Query 5: Check equivalence
        # Two concepts are equivalent if they have the same instances
        are_equivalent = reasoner.is_equivalent(dog, animal)
        print(f"5. Dog ≡ Animal (equivalence): {are_equivalent}")
        print("   (Not equivalent - not every animal is a dog)")
        print()

        print("=" * 60)
        print("Key Concepts")
        print("=" * 60)
        print("""
Consistency: The ontology has no logical contradictions
            No model exists that violates the axioms

Satisfiability: A concept can have instances
              A concept is satisfiable if it's not contradicted

Subsumption: One concept is more specific than another
           Dog ⊑ Animal means every dog is an animal

Equivalence: Two concepts have identical semantics
           C1 ≡ C2 means C1 and C2 have the same instances

The tableau algorithm:
- Starts with an assertion
- Expands it using ontology rules
- Detects clashes (contradictions)
- Uses blocking to ensure termination
        """)

    finally:
        # Always dispose of the reasoner when done
        # This releases internal data structures and threads
        reasoner.dispose()


if __name__ == "__main__":
    main()
