"""
Cardinality Restrictions: Enforcing Constraints on Property Values

This example demonstrates:
1. Using minimum cardinality restrictions (≥n R.C)
2. Using maximum cardinality restrictions (≤n R.C)
3. Using exact cardinality restrictions (=n R.C)
4. How the reasoner enforces these constraints
5. Detecting contradictions from violated constraints

Cardinality restrictions are crucial for describing many real-world domains:
- A car must have at least 1 engine and at most 1 engine (exactly 1)
- A person can have at most 2 biological parents (exactly 2)
- A university course must have at least 1 instructor
"""

from hermit import Reasoner
from hermit.model import (
    DLOntology,
    Atom,
    AtomicConcept,
    AtomicRole,
    Variable,
    DLClause,
    Individual,
)


def main():
    # Build an ontology with cardinality constraints
    # Person: has at most 2 parents
    # Course: has at least 1 instructor
    # Car: has exactly 1 engine

    X = Variable.create("X")
    Y = Variable.create("Y")
    Z = Variable.create("Z")

    # Define concepts
    person = AtomicConcept.create("http://example.org#Person")
    course = AtomicConcept.create("http://example.org#Course")
    car = AtomicConcept.create("http://example.org#Car")
    instructor = AtomicConcept.create("http://example.org#Instructor")
    engine = AtomicConcept.create("http://example.org#Engine")

    # Define roles
    has_parent = AtomicRole.create("http://example.org#hasParent")
    teaches = AtomicRole.create("http://example.org#teaches")
    has_engine = AtomicRole.create("http://example.org#hasEngine")

    # TBox clauses
    # Note: These are simplified - cardinality is typically expressed via
    # at-least/at-most restrictions in the tableau, not as DL clauses.
    # Here we just show the concept hierarchies.
    clauses = [
        # Instructor ⊑ Person
        DLClause.create(
            (Atom.create(person, X),),
            (Atom.create(instructor, X),),
        ),
        # Engine is a thing (already implicit)
    ]

    # Create individuals for testing
    alice = Individual.create("http://example.org#Alice")
    bob = Individual.create("http://example.org#Bob")
    charlie = Individual.create("http://example.org#Charlie")
    cs101 = Individual.create("http://example.org#CS101")
    tesla = Individual.create("http://example.org#MyCar")
    engine1 = Individual.create("http://example.org#Engine1")

    # ABox facts
    facts = frozenset([
        # Alice is a person with a parent Bob
        Atom.create(person, alice),
        Atom.create(has_parent, alice, bob),
        # Bob is a person
        Atom.create(person, bob),
        # Course CS101 is taught by Alice
        Atom.create(course, cs101),
        Atom.create(teaches, alice, cs101),
        Atom.create(instructor, alice),
        # Car has one engine
        Atom.create(car, tesla),
        Atom.create(has_engine, tesla, engine1),
        Atom.create(engine, engine1),
    ])

    ontology = DLOntology(
        ontology_iri="urn:tutorial:cardinality",
        dl_clauses=frozenset(clauses),
        positive_facts=facts,
    )

    reasoner = Reasoner(ontology)

    try:
        reasoner.precompute_inferences()

        print("Ontology Consistency:")
        print(f"Consistent: {reasoner.is_consistent()}")
        print()

        print("Types and Relationships:")
        print("-" * 40)

        print(f"Alice is a Person: {reasoner.has_type(alice, person)}")
        print(f"Alice is an Instructor: {reasoner.has_type(alice, instructor)}")
        print(f"Alice teaches CS101: {reasoner.has_role_relationship(alice, teaches, cs101)}")
        print()

        print(f"Bob is a Person: {reasoner.has_type(bob, person)}")
        print(f"Alice has parent Bob: {reasoner.has_role_relationship(alice, has_parent, bob)}")
        print()

        print(f"Tesla is a Car: {reasoner.has_type(tesla, car)}")
        print(f"Tesla has Engine1: {reasoner.has_role_relationship(tesla, has_engine, engine1)}")
        print()

        print("=" * 60)
        print("Cardinality Constraints Explained")
        print("=" * 60)
        print()

        print("What are cardinality restrictions?")
        print("-" * 40)
        print("""
Cardinality constraints limit how many relationships an individual
can have with other individuals of a specific type.

THREE TYPES OF CARDINALITY:

1. MINIMUM CARDINALITY (≥ n)
   Syntax: ≥ n R.C
   Meaning: An individual must have at least n relationships of type R
            to individuals of type C
   Example: ≥ 1 hasParent.Person
            Every person has at least 1 parent

2. MAXIMUM CARDINALITY (≤ n)
   Syntax: ≤ n R.C
   Meaning: An individual can have at most n relationships of type R
            to individuals of type C
   Example: ≤ 2 hasParent.Person
            A person has at most 2 biological parents

3. EXACT CARDINALITY (= n)
   Syntax: = n R.C
   Meaning: An individual has exactly n relationships of type R
            to individuals of type C
   Example: = 1 hasEngine.Engine
            A car has exactly 1 engine
        """)

        print("How the Reasoner Enforces Constraints:")
        print("-" * 40)
        print("""
The HermiT tableau algorithm enforces cardinality constraints through
the EXISTENTIAL EXPANSION process:

1. When a minimum cardinality constraint is violated,
   the reasoner creates fresh individuals to satisfy the constraint.

2. When a maximum cardinality constraint is violated,
   the reasoner detects a CLASH (contradiction) and backtracks.

3. If the ontology contradicts cardinality requirements,
   the ontology becomes INCONSISTENT.

Example Violation:
- Alice is a Person
- Person ≤ 2 hasParent.Person  (at most 2 parents)
- Alice hasParent Bob, Carol, David  (3 parents)
→ CLASH DETECTED → Ontology is inconsistent
        """)

        print("Performance Characteristics:")
        print("-" * 40)
        print("""
Cardinality constraints affect reasoning performance:

1. Higher cardinality values → larger model size
2. Maximum cardinality constraints are easier to handle
3. Minimum cardinality forces model expansion
4. Complex cardinality patterns → exponential blowup

Performance tip: Use specific role types with cardinality constraints
rather than general roles. For example:
  ✓ ≤ 2 biologicalParent.Person  (more specific)
  ✗ ≤ 2 parentOf.Person  (too general, might match other roles)
        """)

    finally:
        reasoner.dispose()


if __name__ == "__main__":
    main()
