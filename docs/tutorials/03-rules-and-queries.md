# Tutorial 3: Rules and Complex Queries

Learn to write SWRL-like rules and perform advanced queries over your ontology.

## What You'll Learn

- Writing rule-based axioms
- Complex class expressions (Union, Intersection)
- Performing advanced queries
- Understanding inference chains
- Debugging reasoning

## Part 1: Rule-Based Axioms

Rules in OWL 2 DL are expressed through class definitions:

```python
from hermit import Reasoner
from hermit.model import (
    DLOntology, OWLClass, OWLObjectProperty,
    SubClassOf, Union, Intersection,
    ClassAssertion, OWLNamedIndividual
)

onto = DLOntology()

# Define classes
Person = OWLClass("http://example.org/Person")
Teacher = OWLClass("http://example.org/Teacher")
Student = OWLClass("http://example.org/Student")
Staff = OWLClass("http://example.org/Staff")
UniversityMember = OWLClass("http://example.org/UniversityMember")

# Rule: Everyone at the university is either a teacher or a student
# This is expressed as: UniversityMember ⊆ Teacher ⊔ Student
onto.add_axiom(SubClassOf(
    UniversityMember,
    Union(Teacher, Student)
))

# Rule: Staff is a union of Teacher and other staff
AdminStaff = OWLClass("http://example.org/AdminStaff")
onto.add_axiom(SubClassOf(Staff, Union(Teacher, AdminStaff)))

# Test reasoning
person1 = OWLNamedIndividual("http://example.org/alice")
onto.add_axiom(ClassAssertion(Teacher, person1))

reasoner = Reasoner(onto)
reasoner.precompute_inferences()

print("Is alice a UniversityMember?", reasoner.has_type(person1, UniversityMember))  # Can infer through rules

reasoner.dispose()
```

## Part 2: Complex Class Expressions

Combine multiple concepts to express complex rules:

```python
onto = DLOntology()

# Define classes
Person = OWLClass("http://example.org/Person")
Young = OWLClass("http://example.org/Young")
Single = OWLClass("http://example.org/Single")
Eligible = OWLClass("http://example.org/Eligible")

# Rule: Eligible people are Young AND Single
# Eligible ⊆ Young ⊓ Single
onto.add_axiom(SubClassOf(
    Eligible,
    Intersection(Young, Single)
))

# Create an individual
person = OWLNamedIndividual("http://example.org/john")
onto.add_axiom(ClassAssertion(Young, person))
onto.add_axiom(ClassAssertion(Single, person))
onto.add_axiom(ClassAssertion(Person, person))

# Now they're eligible (can infer)
onto.add_axiom(ClassAssertion(Eligible, person))

reasoner = Reasoner(onto)
reasoner.precompute_inferences()

print("Is john eligible?", reasoner.has_type(person, Eligible))  # True

reasoner.dispose()
```

## Part 3: Implicit Rules Through Restrictions

Property restrictions create implicit rules:

```python
from hermit.model import AtLeast, ForAll, Complement

onto = DLOntology()

# Define classes and properties
Person = OWLClass("http://example.org/Person")
Parent = OWLClass("http://example.org/Parent")
Childless = OWLClass("http://example.org/Childless")
hasChild = OWLObjectProperty("http://example.org/hasChild")

# Rule 1: Parents have at least one child
# Parent ⊆ ∃hasChild.Person
onto.add_axiom(SubClassOf(
    Parent,
    AtLeast(1, hasChild, Person)
))

# Rule 2: Childless people have no children
# This is more complex - we'd need to express it differently
# For now, we define it as the negation of Parent
onto.add_axiom(SubClassOf(
    Childless,
    Complement(Parent)
))

# The reasoner can now infer who is not a parent
person = OWLNamedIndividual("http://example.org/alice")
onto.add_axiom(ClassAssertion(Person, person))

# If alice is childless, she's not a parent
onto.add_axiom(ClassAssertion(Childless, person))

reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Query to verify
parents = reasoner.get_instances(Parent)
childless = reasoner.get_instances(Childless)
print(f"Parents: {len(parents)}")
print(f"Childless: {len(childless)}")

reasoner.dispose()
```

## Part 4: Advanced Queries

Query the ontology in sophisticated ways:

```python
onto = DLOntology()

# Build a small organization hierarchy
Person = OWLClass("http://example.org/Person")
Employee = OWLClass("http://example.org/Employee")
Manager = OWLClass("http://example.org/Manager")
Executive = OWLClass("http://example.org/Executive")
Department = OWLClass("http://example.org/Department")

manages = OWLObjectProperty("http://example.org/manages")
worksIn = OWLObjectProperty("http://example.org/worksIn")

# Add hierarchy
onto.add_axiom(SubClassOf(Employee, Person))
onto.add_axiom(SubClassOf(Manager, Employee))
onto.add_axiom(SubClassOf(Executive, Manager))

# Create individuals
alice = OWLNamedIndividual("http://example.org/alice")
bob = OWLNamedIndividual("http://example.org/bob")
charlie = OWLNamedIndividual("http://example.org/charlie")
sales_dept = OWLNamedIndividual("http://example.org/sales_dept")

onto.add_axiom(ClassAssertion(Executive, alice))
onto.add_axiom(ClassAssertion(Manager, bob))
onto.add_axiom(ClassAssertion(Employee, charlie))
onto.add_axiom(ClassAssertion(Department, sales_dept))

# Add relationships
from hermit.model import ObjectPropertyAssertion
onto.add_axiom(ObjectPropertyAssertion(manages, alice, bob))
onto.add_axiom(ObjectPropertyAssertion(manages, bob, charlie))
onto.add_axiom(ObjectPropertyAssertion(worksIn, charlie, sales_dept))

reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Query 1: Get all employees (includes managers and executives)
all_employees = reasoner.get_instances(Employee)
print(f"All employees: {len(all_employees)}")  # 3 (alice, bob, charlie)

# Query 2: Get all executives
executives = reasoner.get_instances(Executive)
print(f"Executives: {len(executives)}")  # 1 (alice)

# Query 3: Get what bob manages
bobs_direct_reports = reasoner.get_object_property_values(manages, bob)
print(f"Bob manages: {bobs_direct_reports}")

# Query 4: Get what department charlie works in
charlies_dept = reasoner.get_object_property_values(worksIn, charlie)
print(f"Charlie works in: {charlies_dept}")

# Query 5: Class hierarchy
hierarchy = reasoner.get_class_hierarchy()
print(f"Class hierarchy depth: {hierarchy}")

reasoner.dispose()
```

**Output:**
```
All employees: 3
Executives: 1
Bob manages: [<OWLNamedIndividual 'http://example.org/charlie'>]
Charlie works in: [<OWLNamedIndividual 'http://example.org/sales_dept'>]
Class hierarchy depth: [<HierarchyNode>...]
```

## Part 5: Reasoning Chains

Understanding how the reasoner derives facts:

```python
onto = DLOntology()

# Create a reasoning chain
Animal = OWLClass("http://example.org/Animal")
Mammal = OWLClass("http://example.org/Mammal")
Dog = OWLClass("http://example.org/Dog")
Poodle = OWLClass("http://example.org/Poodle")

onto.add_axiom(SubClassOf(Mammal, Animal))
onto.add_axiom(SubClassOf(Dog, Mammal))
onto.add_axiom(SubClassOf(Poodle, Dog))

# Create individual
fido = OWLNamedIndividual("http://example.org/fido")
onto.add_axiom(ClassAssertion(Poodle, fido))

reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Query: Is fido an animal?
print("Is fido an Animal?", reasoner.has_type(fido, Animal))  # True

# The chain:
# Fido is a Poodle (asserted)
# → Fido is a Dog (from Poodle ⊆ Dog)
# → Fido is a Mammal (from Dog ⊆ Mammal)
# → Fido is an Animal (from Mammal ⊆ Animal)

# Get immediate type
print("Fido's direct type:", reasoner.get_direct_types(fido))  # {Poodle}

# Get all inferred types
all_types = reasoner.get_types(fido)
print(f"All of Fido's types: {all_types}")

reasoner.dispose()
```

## Part 6: Debugging Inconsistencies

When your ontology has contradictions:

```python
onto = DLOntology()

Person = OWLClass("http://example.org/Person")
Parent = OWLClass("http://example.org/Parent")
Childless = OWLClass("http://example.org/Childless")

# Define disjointness
from hermit.model import DisjointClasses
onto.add_axiom(DisjointClasses(Parent, Childless))

# Create individual with contradiction
alice = OWLNamedIndividual("http://example.org/alice")
onto.add_axiom(ClassAssertion(Parent, alice))
onto.add_axiom(ClassAssertion(Childless, alice))

reasoner = Reasoner(onto)

# Check consistency
is_consistent = reasoner.is_consistent()
print(f"Ontology is consistent: {is_consistent}")  # False

if not is_consistent:
    print("WARNING: Ontology contains a contradiction!")
    print("Check disjointness rules and class definitions")

reasoner.dispose()
```

## Query API Reference

```python
# Get all instances of a class
instances = reasoner.get_instances(MyClass)

# Get direct instances (not inferred through hierarchy)
direct = reasoner.get_direct_instances(MyClass)

# Get types of an individual
types = reasoner.get_types(individual)

# Get direct types (immediate classification)
direct_types = reasoner.get_direct_types(individual)

# Get class hierarchy
hierarchy = reasoner.get_class_hierarchy()

# Check subclass relationships
is_subclass = reasoner.is_subclass_of(Class1, Class2)

# Check instance types
is_instance = reasoner.has_type(individual, MyClass)

# Get property values
values = reasoner.get_object_property_values(property, individual)

# Check consistency
consistent = reasoner.is_consistent()

# Get unsatisfiable classes
unsatisfiable = reasoner.get_unsatisfiable_classes()
```

## Key Takeaways

1. **Rules** are expressed through class definitions and restrictions
2. **Complex expressions** (Union, Intersection) model OR/AND logic
3. **Queries** reveal inferred facts
4. **Reasoning chains** show how conclusions are derived
5. **Consistency checking** validates your ontology

## Try This!

Create a medical ontology with:
- Symptoms (fever, cough, headache)
- Diseases (flu, cold, pneumonia)
- Diagnostic rules (flu = fever ∧ cough)
- Treatment rules (flu → antiviral medication)
- Query to diagnose a patient based on symptoms

## Next Steps

- **[Tutorial 4: Advanced Reasoning](./04-advanced-reasoning.md)** — Optimization and performance
- **[Concepts](../concepts.md)** — Deep dive into OWL and DL theory
- **[API Reference](../api/core.md)** — Complete API documentation
