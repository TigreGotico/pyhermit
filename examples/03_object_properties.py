"""
Object Properties: Reasoning about Relationships

This example demonstrates:
1. Creating object properties (relations between individuals)
2. Using some/all-values-from restrictions (∃R.C / ∀R.C)
3. Querying role relationships
4. Understanding role semantics and constraints

Object properties connect individuals (instances) in an ontology.
For example, "hasOwner" connects a Dog to a Person.
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
    Constant,
)


def main():
    # Build a simple ontology with roles:
    # Person and Dog classes
    # Role: hasOwner (connects Dog to Person)
    # Rule: DogWithOwner = Dog ⊓ ∃hasOwner.Person

    X = Variable.create("X")
    Y = Variable.create("Y")

    # Concepts
    person = AtomicConcept.create("http://example.org#Person")
    dog = AtomicConcept.create("http://example.org#Dog")
    dog_with_owner = AtomicConcept.create("http://example.org#DogWithOwner")

    # Roles (object properties)
    has_owner = AtomicRole.create("http://example.org#hasOwner")

    # Define DogWithOwner ⊑ Dog ⊓ ∃hasOwner.Person
    # This means: a DogWithOwner is a Dog that has at least one owner who is a Person
    clauses = [
        # DogWithOwner ⊑ Dog
        DLClause.create(
            (Atom.create(dog, X),),
            (Atom.create(dog_with_owner, X),),
        ),
        # DogWithOwner ⊑ ∃hasOwner.Person
        # (a DogWithOwner must have an owner who is a Person)
        DLClause.create(
            (Atom.create(has_owner, X, Y), Atom.create(person, Y)),
            (Atom.create(dog_with_owner, X),),
        ),
    ]

    # Create individuals
    fido = Individual.create("http://example.org#Fido")
    alice = Individual.create("http://example.org#Alice")

    # Create facts: Fido is a DogWithOwner, Alice is a Person, Fido hasOwner Alice
    facts = frozenset([
        Atom.create(dog_with_owner, fido),
        Atom.create(person, alice),
        Atom.create(has_owner, fido, alice),
    ])

    ontology = DLOntology(
        ontology_iri="urn:tutorial:pets",
        dl_clauses=frozenset(clauses),
        positive_facts=facts,
    )

    reasoner = Reasoner(ontology)

    try:
        reasoner.precompute_inferences()

        print("Consistency Check:")
        print(f"Ontology is consistent: {reasoner.is_consistent()}")
        print()

        print("Role Relationships:")
        print("-" * 40)

        # Check if Fido has owner Alice
        has_relationship = reasoner.has_role_relationship(fido, has_owner, alice)
        print(f"Fido hasOwner Alice: {has_relationship}")

        print("\nType Checking:")
        print("-" * 40)

        # What types does Fido have?
        fido_types = reasoner.get_types(fido)
        print(f"Types of Fido:")
        for type_concept in fido_types:
            print(f"  - {type_concept.iri}")

        # What types does Alice have?
        alice_types = reasoner.get_types(alice)
        print(f"Types of Alice:")
        for type_concept in alice_types:
            print(f"  - {type_concept.iri}")

        # Check specific types
        fido_is_dog = reasoner.has_type(fido, dog)
        fido_is_person = reasoner.has_type(fido, person)
        print(f"\nFido is a Dog: {fido_is_dog}")
        print(f"Fido is a Person: {fido_is_person}")

    finally:
        reasoner.dispose()


if __name__ == "__main__":
    main()
