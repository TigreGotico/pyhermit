# Tutorial 1: Building Your First Ontology

Learn how to construct ontologies from scratch with classes, properties, and axioms.

## What You'll Learn

- Creating OWL classes and properties
- Adding hierarchy and relationships
- Writing subsumption and disjointness axioms
- Building increasingly complex ontologies

All tutorials use the helper from [First Program](../first-program.md):

```python
from hermit import Reasoner
from hermit.model import AtomicConcept, AtomicRole, Individual
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization


def reasoner_from_axioms(axioms, ontology_iri="urn:example:onto"):
    """Compile OWL axioms into a Reasoner (normalize -> clausify)."""
    normalized = OWLNormalization().process_ontology(axioms)
    return Reasoner(OWLClausification().clausify(normalized, ontology_iri=ontology_iri))
```

## Part 1: Simple Class Hierarchy

Let's model a basic organizational structure:

```python
from hermit.owl_model.class_expression import OWLClass
from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom

NS = "http://example.org/"

# Step 1: Define classes (concepts)
Person = OWLClass(NS + "Person")
Employee = OWLClass(NS + "Employee")
Manager = OWLClass(NS + "Manager")

# Step 2: Add rules (axioms) to define the hierarchy
axioms = [
    OWLSubClassOfAxiom(Employee, Person),   # Every Employee is a Person
    OWLSubClassOfAxiom(Manager, Employee),  # Every Manager is an Employee
]

# Step 3: Create reasoner and run inference
reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

# Step 4: Query the reasoner (hermit.model handles)
person = AtomicConcept.create(NS + "Person")
employee = AtomicConcept.create(NS + "Employee")
manager = AtomicConcept.create(NS + "Manager")

print("Is Manager a Person?", reasoner.is_sub_class_of(manager, person))    # True
print("Is Employee a Person?", reasoner.is_sub_class_of(employee, person))  # True
print("Is Person an Employee?", reasoner.is_sub_class_of(person, employee)) # False

reasoner.dispose()
```

**Output:**
```
Is Manager a Person? True
Is Employee a Person? True
Is Person an Employee? False
```

### What Just Happened?

The reasoner automatically inferred that **Manager is a subclass of Person** by following the chain:
- Manager ⊑ Employee (you stated)
- Employee ⊑ Person (you stated)
- Therefore: Manager ⊑ Person (the reasoner inferred)

This is **transitivity** of subsumption.

## Part 2: Adding Instances

Now let's add actual people:

```python
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_axiom import OWLClassAssertionAxiom

# Create instances
alice = OWLNamedIndividual(NS + "alice")
bob = OWLNamedIndividual(NS + "bob")
charlie = OWLNamedIndividual(NS + "charlie")

# Add facts (individual first, class second)
axioms += [
    OWLClassAssertionAxiom(alice, Employee),
    OWLClassAssertionAxiom(bob, Manager),
    OWLClassAssertionAxiom(charlie, Person),
]

# Rebuild reasoner
reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

alice_h = Individual.create(NS + "alice")
bob_h = Individual.create(NS + "bob")

# Query instance types
print("Is alice an Employee?", reasoner.has_type(alice_h, employee))  # True
print("Is alice a Person?", reasoner.has_type(alice_h, person))       # True (inferred!)
print("Is bob a Manager?", reasoner.has_type(bob_h, manager))         # True
print("Is bob an Employee?", reasoner.has_type(bob_h, employee))      # True (inferred!)
print("Is bob a Person?", reasoner.has_type(bob_h, person))           # True (inferred!)

# Get all instances of Person
persons = reasoner.get_instances(person)
print(f"All persons: {len(persons)}")  # 3 (alice, bob, charlie)

reasoner.dispose()
```

**Output:**
```
Is alice an Employee? True
Is alice a Person? True
Is bob a Manager? True
Is bob an Employee? True
Is bob a Person? True
All persons: 3
```

## Part 3: Disjoint Classes

Let's model mutually exclusive concepts:

```python
from hermit.owl_model.owl_axiom import OWLDisjointClassesAxiom

# Additional class
Student = OWLClass(NS + "Student")

axioms += [
    OWLSubClassOfAxiom(Student, Person),
    # An Employee cannot be a Student
    OWLDisjointClassesAxiom([Employee, Student]),
]

# Test consistency
reasoner = reasoner_from_axioms(axioms)
print("Is ontology consistent?", reasoner.is_consistent())  # True
reasoner.dispose()

# Create a contradiction
dana = OWLNamedIndividual(NS + "dana")
contradictory = axioms + [
    OWLClassAssertionAxiom(dana, Employee),
    OWLClassAssertionAxiom(dana, Student),
]

reasoner2 = reasoner_from_axioms(contradictory)
print("Is ontology consistent (with contradiction)?", reasoner2.is_consistent())  # False
reasoner2.dispose()
```

**Output:**
```
Is ontology consistent? True
Is ontology consistent (with contradiction)? False
```

## Part 4: Properties (Relationships)

Add relationships between individuals:

```python
from hermit.owl_model.owl_property import OWLObjectProperty
from hermit.owl_model.owl_axiom import OWLObjectPropertyAssertionAxiom

# Define properties
manages = OWLObjectProperty(NS + "manages")
worksFor = OWLObjectProperty(NS + "worksFor")

# Add property relationships (subject, property, object)
axioms += [
    OWLObjectPropertyAssertionAxiom(bob, manages, alice),
    OWLObjectPropertyAssertionAxiom(alice, worksFor, bob),
]

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

# Query relationships
manages_h = AtomicRole.create(NS + "manages")
works_for_h = AtomicRole.create(NS + "worksFor")

print("Does bob manage alice?",
      reasoner.has_role_relationship(bob_h, manages_h, alice_h))    # True
print("Does alice work for bob?",
      reasoner.has_role_relationship(alice_h, works_for_h, bob_h))  # True
print("Does alice manage bob?",
      reasoner.has_role_relationship(alice_h, manages_h, bob_h))    # False

reasoner.dispose()
```

## Key Takeaways

1. **Class hierarchies** are the foundation of ontologies
2. **Subsumption** (`OWLSubClassOfAxiom`) establishes "is-a" relationships
3. **Instances** (`OWLClassAssertionAxiom`) are the actual data
4. **Reasoning** automatically infers new facts from rules
5. **Disjointness** rules enforce consistency
6. **Properties** represent relationships between individuals

## Try This!

Extend the ontology with:
- More employee types (CEO, TeamLead, Intern)
- Properties like `salary`, `department`
- Property restrictions (e.g., Managers manage at least 2 employees)

## Next Steps

- **[Tutorial 2: Restrictions and Cardinality](./02-restrictions.md)** — Learn about at-least and at-most restrictions
- **[Tutorial 3: Rules and Queries](./03-rules-and-queries.md)** — Write complex rules
- **[API Reference](../api/core.md)** — Complete API documentation
