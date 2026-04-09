# Tutorial 1: Building Your First Ontology

Learn how to construct ontologies from scratch with classes, properties, and axioms.

## What You'll Learn

- Creating OWL classes and properties
- Adding hierarchy and relationships
- Writing subsumption and disjointness axioms
- Building increasingly complex ontologies

## Part 1: Simple Class Hierarchy

Let's model a basic organizational structure:

```python
from hermit import Reasoner
from hermit.model import (
    DLOntology, OWLClass, SubClassOf,
    ClassAssertion, OWLNamedIndividual
)

# Step 1: Create an ontology
onto = DLOntology()

# Step 2: Define classes (concepts)
Person = OWLClass("http://example.org/Person")
Employee = OWLClass("http://example.org/Employee")
Manager = OWLClass("http://example.org/Manager")

# Step 3: Add rules (axioms) to define the hierarchy
# Every Employee is a Person
onto.add_axiom(SubClassOf(Employee, Person))

# Every Manager is an Employee
onto.add_axiom(SubClassOf(Manager, Employee))

# Step 4: Create reasoner and run inference
reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Step 5: Query the reasoner
print("Is Manager a Person?", reasoner.is_subclass_of(Manager, Person))  # True
print("Is Employee a Person?", reasoner.is_subclass_of(Employee, Person))  # True
print("Is Person an Employee?", reasoner.is_subclass_of(Person, Employee))  # False

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
- Manager ⊆ Employee (you stated)
- Employee ⊆ Person (you stated)
- Therefore: Manager ⊆ Person (the reasoner inferred)

This is **transitivity** of subsumption.

## Part 2: Adding Instances

Now let's add actual people:

```python
from hermit.model import ClassAssertion, OWLNamedIndividual

# Create instances
alice = OWLNamedIndividual("http://example.org/alice")
bob = OWLNamedIndividual("http://example.org/bob")
charlie = OWLNamedIndividual("http://example.org/charlie")

# Add facts
onto.add_axiom(ClassAssertion(Employee, alice))
onto.add_axiom(ClassAssertion(Manager, bob))
onto.add_axiom(ClassAssertion(Person, charlie))

# Rebuild reasoner
reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Query instance types
print("Is alice an Employee?", reasoner.has_type(alice, Employee))  # True
print("Is alice a Person?", reasoner.has_type(alice, Person))  # True (inferred!)
print("Is bob a Manager?", reasoner.has_type(bob, Manager))  # True
print("Is bob an Employee?", reasoner.has_type(bob, Employee))  # True (inferred!)
print("Is bob a Person?", reasoner.has_type(bob, Person))  # True (inferred!)

# Get all instances of Person
persons = reasoner.get_instances(Person)
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
from hermit.model import DisjointClasses

# Additional classes
Student = OWLClass("http://example.org/Student")

# Add to ontology
onto.add_axiom(SubClassOf(Student, Person))

# Define that an Employee cannot be a Student
onto.add_axiom(DisjointClasses(Employee, Student))

# Test consistency
reasoner = Reasoner(onto)
print("Is ontology consistent?", reasoner.is_consistent())  # True

# Create a contradiction
alice_student = OWLNamedIndividual("http://example.org/alice_student")
onto.add_axiom(ClassAssertion(Employee, alice_student))
onto.add_axiom(ClassAssertion(Student, alice_student))

# Test again
reasoner2 = Reasoner(onto)
print("Is ontology consistent (with contradiction)?", reasoner2.is_consistent())  # False

reasoner.dispose()
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
from hermit.model import OWLObjectProperty, ObjectPropertyAssertion

# Define a property
manages = OWLObjectProperty("http://example.org/manages")
worksFor = OWLObjectProperty("http://example.org/worksFor")

# Add property relationships
onto.add_axiom(ObjectPropertyAssertion(manages, bob, alice))
onto.add_axiom(ObjectPropertyAssertion(worksFor, alice, bob))

reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Query relationships
managers_of_alice = reasoner.get_object_property_values(manages, bob)
alice_works_for = reasoner.get_object_property_values(worksFor, alice)

print(f"Bob manages: {managers_of_alice}")
print(f"Alice works for: {alice_works_for}")

reasoner.dispose()
```

## Key Takeaways

1. **Class hierarchies** are the foundation of ontologies
2. **Subsumption** (SubClassOf) establishes "is-a" relationships
3. **Instances** (ClassAssertion) are the actual data
4. **Reasoning** automatically infers new facts from rules
5. **Disjointness** rules enforce consistency
6. **Properties** represent relationships between individuals

## Try This!

Extend the ontology with:
- More employee types (CEO, TeamLead, Intern)
- Properties like `salary`, `department`
- Property restrictions (e.g., Managers have at least 2 employees)
- Transitivity rules (if A manages B and B manages C, does A indirectly manage C?)

## Next Steps

- **[Tutorial 2: Restrictions and Cardinality](./02-restrictions.md)** — Learn about at-least and at-most restrictions
- **[Tutorial 3: Rules and Queries](./03-rules-and-queries.md)** — Write complex rules like SWRL
- **[API Reference](../api/core.md)** — Complete API documentation
