"""
Inverse Roles: Modeling Bidirectional Relationships

This example demonstrates:
1. Defining inverse roles (bidirectional relationships)
2. Using role inverses in queries
3. Reasoning about inverse relationships
4. Understanding symmetric vs inverse roles

Inverse roles are crucial for expressing relationships that work in both directions.
For example, if "Alice is married to Bob", then "Bob is married to Alice".
"""

from hermit import Reasoner
from hermit.model import (
    DLOntology,
    Atom,
    AtomicConcept,
    AtomicRole,
    InverseRole,
    Variable,
    DLClause,
    Individual,
)


def main():
    # Build an ontology with inverse roles
    # Person concept
    # Roles: hasChild (parent to child), hasParent (child to parent)
    # These are inverses: if X hasChild Y, then Y hasParent X

    X = Variable.create("X")
    Y = Variable.create("Y")

    # Concepts
    person = AtomicConcept.create("http://example.org#Person")
    parent = AtomicConcept.create("http://example.org#Parent")
    child = AtomicConcept.create("http://example.org#Child")

    # Roles
    has_child = AtomicRole.create("http://example.org#hasChild")
    has_parent = AtomicRole.create("http://example.org#hasParent")

    # TBox: Rules
    clauses = [
        # Parent ⊑ Person
        DLClause.create(
            (Atom.create(person, X),),
            (Atom.create(parent, X),),
        ),
        # Child ⊑ Person
        DLClause.create(
            (Atom.create(person, X),),
            (Atom.create(child, X),),
        ),
        # If X has parent Y, then X is a child
        DLClause.create(
            (Atom.create(child, X),),
            (Atom.create(has_parent, X, Y),),
        ),
        # If X has child Y, then X is a parent
        DLClause.create(
            (Atom.create(parent, X),),
            (Atom.create(has_child, X, Y),),
        ),
        # If X has child Y, then Y has parent X (inverse relationship)
        DLClause.create(
            (Atom.create(has_parent, Y, X),),
            (Atom.create(has_child, X, Y),),
        ),
    ]

    # ABox: Facts
    # Alice is a person with children Bob and Charlie
    alice = Individual.create("http://example.org#Alice")
    bob = Individual.create("http://example.org#Bob")
    charlie = Individual.create("http://example.org#Charlie")
    diana = Individual.create("http://example.org#Diana")

    facts = frozenset([
        Atom.create(person, alice),
        Atom.create(person, bob),
        Atom.create(person, charlie),
        Atom.create(person, diana),
        # Alice has children Bob and Charlie
        Atom.create(has_child, alice, bob),
        Atom.create(has_child, alice, charlie),
        # Diana has child Bob (so Bob has two parents)
        Atom.create(has_child, diana, bob),
    ])

    ontology = DLOntology(
        ontology_iri="urn:tutorial:family",
        dl_clauses=frozenset(clauses),
        positive_facts=facts,
    )

    reasoner = Reasoner(ontology)

    try:
        print("=" * 70)
        print("INVERSE ROLES: Bidirectional Relationships")
        print("=" * 70)
        print()

        reasoner.precompute_inferences()

        print("Forward Role Relationships (hasChild):")
        print("-" * 70)
        print(f"Alice hasChild Bob: {reasoner.has_role_relationship(alice, has_child, bob)}")
        print(f"Alice hasChild Charlie: {reasoner.has_role_relationship(alice, has_child, charlie)}")
        print(f"Alice hasChild Diana: {reasoner.has_role_relationship(alice, has_child, diana)}")
        print(f"Diana hasChild Bob: {reasoner.has_role_relationship(diana, has_child, bob)}")
        print()

        print("Inverse Role Relationships (hasParent):")
        print("-" * 70)
        print(f"Bob hasParent Alice: {reasoner.has_role_relationship(bob, has_parent, alice)}")
        print(f"Bob hasParent Diana: {reasoner.has_role_relationship(bob, has_parent, diana)}")
        print(f"Charlie hasParent Alice: {reasoner.has_role_relationship(charlie, has_parent, alice)}")
        print(f"Alice hasParent Bob: {reasoner.has_role_relationship(alice, has_parent, bob)}")
        print()

        print("Type Inference from Role Relationships:")
        print("-" * 70)
        print(f"Alice is a Parent: {reasoner.has_type(alice, parent)}")
        print(f"Bob is a Child: {reasoner.has_type(bob, child)}")
        print(f"Charlie is a Child: {reasoner.has_type(charlie, child)}")
        print(f"Diana is a Parent: {reasoner.has_type(diana, parent)}")
        print()

        print("=" * 70)
        print("Understanding Inverse Roles")
        print("=" * 70)
        print("""
INVERSE ROLES (Inverse relationships):

1. DEFINITION
   If R is a role, then inverseOf(R) is the inverse role.
   For any individuals a, b: if R(a, b) then inverseOf(R)(b, a)

2. EXAMPLE
   Role: hasChild
   Inverse: hasParent (hasChild⁻)

   If Alice hasChild Bob, then Bob hasParent Alice automatically

3. EXPRESSING IN DL CLAUSES
   You don't need to explicitly assert both directions.
   State the forward direction; the reasoner handles the inverse.

   Example in ontology:
   - Alice hasChild Bob (asserted)
   - Bob hasParent Alice (automatically inferred)

4. USE CASES
   - Parent/Child relationships
   - Owns/OwnedBy
   - Teaches/TaughtBy
   - Manages/ManagedBy
   - Any bidirectional relationship

5. PERFORMANCE NOTE
   Inverse roles affect reasoning performance:
   - More complex blocking calculations needed
   - Larger model sizes may result
   - Plan ontologies with inverse roles accordingly

6. SYMMETRIC vs INVERSE
   - Symmetric: loves(X, Y) → loves(Y, X) (symmetric role)
   - Inverse: hasChild(X, Y) → hasParent(Y, X) (different roles)
        """)

    finally:
        reasoner.dispose()


if __name__ == "__main__":
    main()
