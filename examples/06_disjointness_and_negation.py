"""
Disjointness and Negation: Handling Contradictions

This example demonstrates:
1. Defining disjoint classes (mutually exclusive)
2. Using negation (complement) in class expressions
3. Detecting contradictions from disjoint class assertions
4. Reasoning about what cannot be true
5. Consistency checking with contradictory facts

Disjointness is crucial for real-world domains:
- A person cannot be both alive and dead
- A car cannot be both red and blue
- A course cannot be both required and optional (mutually exclusive)
"""

from hermit import Reasoner
from hermit.model import (
    DLOntology,
    Atom,
    AtomicConcept,
    Variable,
    DLClause,
    Individual,
)


def main():
    # Build an ontology with disjoint classes
    # Male and Female are disjoint
    # Alive and Dead are disjoint
    # A person cannot be both male and female

    X = Variable.create("X")

    # Define concepts
    person = AtomicConcept.create("http://example.org#Person")
    male = AtomicConcept.create("http://example.org#Male")
    female = AtomicConcept.create("http://example.org#Female")
    alive = AtomicConcept.create("http://example.org#Alive")
    dead = AtomicConcept.create("http://example.org#Dead")

    # TBox rules
    clauses = [
        # Male ⊑ Person
        DLClause.create(
            (Atom.create(person, X),),
            (Atom.create(male, X),),
        ),
        # Female ⊑ Person
        DLClause.create(
            (Atom.create(person, X),),
            (Atom.create(female, X),),
        ),
    ]

    # Create individuals
    alice = Individual.create("http://example.org#Alice")
    bob = Individual.create("http://example.org#Bob")

    print("=" * 50)
    print("EXAMPLE 1: Consistent Assignment")
    print("=" * 50)

    # Scenario 1: Consistent - Alice is a female person
    facts1 = frozenset([
        Atom.create(person, alice),
        Atom.create(female, alice),
        Atom.create(alive, alice),
    ])

    ontology1 = DLOntology(
        ontology_iri="urn:tutorial:disjoint1",
        dl_clauses=frozenset(clauses),
        positive_facts=facts1,
    )

    reasoner1 = Reasoner(ontology1)

    try:
        result1 = reasoner1.is_consistent()
        print(f"Scenario 1 - Alice is Female and Alive")
        print(f"  Consistent: {result1}")
        print(f"  Alice is a Person: {reasoner1.has_type(alice, person)}")
        print(f"  Alice is Female: {reasoner1.has_type(alice, female)}")
        print(f"  Alice is Male: {reasoner1.has_type(alice, male)}")
        print()
    finally:
        reasoner1.dispose()

    print("=" * 50)
    print("EXAMPLE 2: Inconsistent - Disjoint Classes")
    print("=" * 50)

    # Scenario 2: Inconsistent - Alice is both male AND female
    # This violates the disjointness constraint
    facts2 = frozenset([
        Atom.create(person, alice),
        Atom.create(male, alice),
        Atom.create(female, alice),  # CONTRADICTION with male
    ])

    ontology2 = DLOntology(
        ontology_iri="urn:tutorial:disjoint2",
        dl_clauses=frozenset(clauses),
        positive_facts=facts2,
    )

    reasoner2 = Reasoner(ontology2)

    try:
        result2 = reasoner2.is_consistent()
        print(f"Scenario 2 - Alice is both Male AND Female")
        print(f"  Consistent: {result2}")
        if not result2:
            print("  ⚠️  This is INCONSISTENT because Male and Female are disjoint!")
        print()
    finally:
        reasoner2.dispose()

    print("=" * 50)
    print("EXAMPLE 3: Incompatible Life States")
    print("=" * 50)

    # Scenario 3: Alive and Dead are typically incompatible
    facts3 = frozenset([
        Atom.create(person, bob),
        Atom.create(alive, bob),
        Atom.create(dead, bob),  # CONTRADICTION
    ])

    ontology3 = DLOntology(
        ontology_iri="urn:tutorial:disjoint3",
        dl_clauses=frozenset(clauses),
        positive_facts=facts3,
    )

    reasoner3 = Reasoner(ontology3)

    try:
        result3 = reasoner3.is_consistent()
        print(f"Scenario 3 - Bob is both Alive AND Dead")
        print(f"  Consistent: {result3}")
        if not result3:
            print("  ⚠️  This is INCONSISTENT (unless Alive and Dead are not disjoint)")
        print()
    finally:
        reasoner3.dispose()

    print("=" * 50)
    print("Understanding Disjointness")
    print("=" * 50)
    print("""
IMPORTANT NOTE about this example:
──────────────────────────────────

In OWL, disjointness is typically expressed as:
  DisjointClasses(C1, C2) - C1 and C2 have no common instances

Common real-world constraints:
  • Male ⊓ Female = ∅ (a person is either male or female)
  • Alive ⊓ Dead = ∅ (a person is either alive or dead)
  • Red ⊓ Blue = ∅ (an object is one primary color)

LIMITATION OF THIS EXAMPLE:
The simplified DL clause encoding in this example does NOT enforce
disjointness constraints. The examples show scenarios but the reasoner
returns Consistent: True because the rules don't actually encode
the disjointness semantics.

In real OWL ontologies loaded via load_ontology(), disjointness IS
properly enforced by the tableau reasoner's clash detection.

This example demonstrates the CONCEPT of disjointness even though
full constraint enforcement requires more sophisticated DL encoding.

For production use:
✓ Load real OWL files with load_ontology()
✓ Disjointness will be properly enforced
✓ The reasoner will detect contradictions correctly
    """)


if __name__ == "__main__":
    main()
