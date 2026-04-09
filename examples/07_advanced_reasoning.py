"""
Advanced Reasoning: Complex Class Expressions and Queries

This example demonstrates:
1. Multi-level class hierarchies
2. Role reasoning and relationships
3. Querying complex ontologies
4. Classification with instances

This is where the power of OWL reasoning shows:
the reasoner automatically computes subsumption relationships
and classifies individuals into classes based on rules.
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
    # Build a multi-level ontology:
    # - Person hierarchy (Employee → Manager, Engineer)
    # - Project relationships
    # - Individuals with roles

    X = Variable.create("X")
    Y = Variable.create("Y")

    # Concepts
    person = AtomicConcept.create("http://example.org#Person")
    employee = AtomicConcept.create("http://example.org#Employee")
    manager = AtomicConcept.create("http://example.org#Manager")
    engineer = AtomicConcept.create("http://example.org#Engineer")
    senior_engineer = AtomicConcept.create("http://example.org#SeniorEngineer")
    project = AtomicConcept.create("http://example.org#Project")

    # Roles
    works_for = AtomicRole.create("http://example.org#worksFor")
    manages = AtomicRole.create("http://example.org#manages")
    works_on = AtomicRole.create("http://example.org#worksOn")

    # TBox rules
    clauses = [
        # Employee ⊑ Person
        DLClause.create(
            (Atom.create(person, X),),
            (Atom.create(employee, X),),
        ),
        # Manager ⊑ Employee
        DLClause.create(
            (Atom.create(employee, X),),
            (Atom.create(manager, X),),
        ),
        # Engineer ⊑ Employee
        DLClause.create(
            (Atom.create(employee, X),),
            (Atom.create(engineer, X),),
        ),
        # SeniorEngineer ⊑ Engineer
        DLClause.create(
            (Atom.create(engineer, X),),
            (Atom.create(senior_engineer, X),),
        ),
    ]

    # Create individuals
    alice = Individual.create("http://example.org#Alice")
    bob = Individual.create("http://example.org#Bob")
    charlie = Individual.create("http://example.org#Charlie")
    diana = Individual.create("http://example.org#Diana")
    project1 = Individual.create("http://example.org#Project1")

    # ABox facts
    facts = frozenset([
        # People and their roles
        Atom.create(manager, alice),
        Atom.create(engineer, bob),
        Atom.create(senior_engineer, charlie),
        Atom.create(engineer, diana),
        # Relationships
        Atom.create(manages, alice, bob),
        Atom.create(manages, alice, diana),
        Atom.create(works_on, bob, project1),
        Atom.create(works_on, charlie, project1),
        Atom.create(works_on, diana, project1),
        # Project
        Atom.create(project, project1),
    ])

    ontology = DLOntology(
        ontology_iri="urn:tutorial:organization",
        dl_clauses=frozenset(clauses),
        positive_facts=facts,
    )

    reasoner = Reasoner(ontology)

    try:
        reasoner.precompute_inferences()

        print("=" * 50)
        print("ADVANCED REASONING — ORGANIZATION")
        print("=" * 50)
        print()

        print("Concept Hierarchy (Subsumption):")
        print("-" * 40)

        # Test subsumption relationships
        subsumptions = [
            (manager, employee, "Manager ⊑ Employee"),
            (manager, person, "Manager ⊑ Person"),
            (engineer, employee, "Engineer ⊑ Employee"),
            (senior_engineer, engineer, "SeniorEngineer ⊑ Engineer"),
            (senior_engineer, employee, "SeniorEngineer ⊑ Employee"),
            (senior_engineer, person, "SeniorEngineer ⊑ Person"),
        ]

        for sub, sup, description in subsumptions:
            is_sub = reasoner.is_sub_class_of(sub, sup)
            status = "✓" if is_sub else "✗"
            print(f"{status} {description}: {is_sub}")
        print()

        print("Type Classification (Inferred):")
        print("-" * 40)

        # Get all types for each individual
        for name, ind in [("Alice", alice), ("Bob", bob), ("Charlie", charlie), ("Diana", diana)]:
            types = reasoner.get_types(ind)
            type_names = sorted([t.iri.split('#')[-1] for t in types])
            print(f"{name}: {', '.join(type_names)}")
        print()

        print("Instance Retrieval:")
        print("-" * 40)

        # Get all instances of different classes
        for cls_name, cls in [("Employee", employee), ("Manager", manager),
                              ("Engineer", engineer), ("SeniorEngineer", senior_engineer)]:
            instances = reasoner.get_instances(cls)
            instance_names = sorted([i.iri.split('#')[-1] for i in instances])
            print(f"{cls_name}s: {instance_names}")
        print()

        print("Role Relationships:")
        print("-" * 40)

        # Check specific role relationships
        print(f"Alice manages Bob: {reasoner.has_role_relationship(alice, manages, bob)}")
        print(f"Alice manages Charlie: {reasoner.has_role_relationship(alice, manages, charlie)}")
        print(f"Alice manages Diana: {reasoner.has_role_relationship(alice, manages, diana)}")
        print(f"Bob manages Diana: {reasoner.has_role_relationship(bob, manages, diana)}")
        print()

        print("Summary of Reasoning:")
        print("-" * 40)
        print("""
What the reasoner inferred:

1. AUTOMATIC TYPE INFERENCE:
   • Alice: Manager → Employee → Person (transitively inferred)
   • Bob: Engineer → Employee → Person
   • Charlie: SeniorEngineer → Engineer → Employee → Person
   • Diana: Engineer → Employee → Person

2. HIERARCHICAL RELATIONSHIPS:
   • All relationships flow through the hierarchy
   • Subclass relationships are transitive
   • The reasoner automatically computes all implications

3. CONSISTENCY:
   • The ontology is consistent
   • All facts are logically sound
   • The type hierarchy is properly structured

This demonstrates how complex ontologies enable automatic
reasoning: define rules once, the reasoner handles inference!
        """)

    finally:
        reasoner.dispose()


if __name__ == "__main__":
    main()
