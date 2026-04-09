"""
Instance Retrieval: Querying Individuals

This example demonstrates:
1. Creating individuals (instances) in the ABox
2. Asserting types and relationships for individuals
3. Retrieving instances of a class
4. Checking types of individuals
5. Individual equality and identity

The ABox (Assertion Box) contains facts about specific individuals,
while the TBox (Terminological Box) contains class definitions.
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
    # Build a simple ontology with individuals
    # Classes: Person, Doctor
    # Individuals: Alice, Bob, Charlie (doctors), Diana (person)

    X = Variable.create("X")
    Y = Variable.create("Y")

    # Define concepts
    person = AtomicConcept.create("http://example.org#Person")
    doctor = AtomicConcept.create("http://example.org#Doctor")
    patient = AtomicConcept.create("http://example.org#Patient")

    # Define roles
    treats = AtomicRole.create("http://example.org#treats")
    works_at = AtomicRole.create("http://example.org#worksAt")
    hospital = AtomicRole.create("http://example.org#Hospital")

    # TBox rules
    clauses = [
        # Doctor ⊑ Person
        DLClause.create(
            (Atom.create(person, X),),
            (Atom.create(doctor, X),),
        ),
    ]

    # Create individuals
    alice = Individual.create("http://example.org#Alice")
    bob = Individual.create("http://example.org#Bob")
    charlie = Individual.create("http://example.org#Charlie")
    diana = Individual.create("http://example.org#Diana")

    # ABox: Facts about individuals
    facts = frozenset([
        # Alice and Bob are doctors
        Atom.create(doctor, alice),
        Atom.create(doctor, bob),
        # Charlie is a doctor
        Atom.create(doctor, charlie),
        # Diana is a patient
        Atom.create(patient, diana),
        # Relationships
        Atom.create(treats, alice, diana),
        Atom.create(treats, bob, diana),
    ])

    ontology = DLOntology(
        ontology_iri="urn:tutorial:hospital",
        dl_clauses=frozenset(clauses),
        positive_facts=facts,
    )

    reasoner = Reasoner(ontology)

    try:
        reasoner.precompute_inferences()

        print("Ontology Consistency:")
        print(f"Consistent: {reasoner.is_consistent()}")
        print()

        print("Instance Retrieval - All Doctors:")
        print("-" * 40)
        doctors = reasoner.get_instances(doctor)
        for doc in doctors:
            print(f"  {doc.iri}")
        print(f"Total: {len(doctors)} doctors")
        print()

        print("Instance Retrieval - All Persons (includes doctors):")
        print("-" * 40)
        persons = reasoner.get_instances(person)
        for p in persons:
            print(f"  {p.iri}")
        print(f"Total: {len(persons)} persons")
        print()

        print("Type Checking - What types does Alice have?")
        print("-" * 40)
        alice_types = reasoner.get_types(alice)
        for t in alice_types:
            print(f"  {t.iri}")
        print()

        print("Type Checking - Direct queries:")
        print("-" * 40)
        print(f"Alice is a Doctor: {reasoner.has_type(alice, doctor)}")
        print(f"Alice is a Person: {reasoner.has_type(alice, person)}")
        print(f"Alice is a Patient: {reasoner.has_type(alice, patient)}")
        print()

        print("Role Relationships:")
        print("-" * 40)
        print("Checking if role assertions were made between individuals:")
        print(f"Alice treats Diana: {reasoner.has_role_relationship(alice, treats, diana)}")
        print(f"Bob treats Diana: {reasoner.has_role_relationship(bob, treats, diana)}")
        print(f"Diana treats Alice: {reasoner.has_role_relationship(diana, treats, alice)}")
        print()

        print("Subsumption Relationships:")
        print("-" * 40)
        print("Checking concept hierarchy:")
        print(f"Doctor ⊑ Person: {reasoner.is_sub_class_of(doctor, person)}")
        print(f"Patient ⊑ Person: {reasoner.is_sub_class_of(patient, person)}")
        print()

        print("Instance Counting:")
        print("-" * 40)
        print(f"Number of Doctors: {len(reasoner.get_instances(doctor))}")
        print(f"Number of Persons: {len(reasoner.get_instances(person))}")
        print(f"Number of Patients: {len(reasoner.get_instances(patient))}")
        print()

        print("Individual Identity:")
        print("-" * 40)
        print("Note: is_same_individual() is not yet fully implemented in PyHermit.")
        print("See TROUBLESHOOTING.md for details.")

    finally:
        reasoner.dispose()


if __name__ == "__main__":
    main()
