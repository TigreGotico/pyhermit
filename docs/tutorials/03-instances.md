# Tutorial 3: Working with Instances (ABox)

Learn how to add data (individuals) to your ontology and query them.

## What are Instances?

**Instances** (also called **individuals** or **ABox assertions**) are specific data points that belong to your classes.

```
TBox (Schema):         ABox (Data):
Employee is a Person   Alice is an Employee
Manager ⊆ Employee     Bob is a Manager
                       Alice manages Bob
```

## Part 1: Creating and Adding Instances

```python
from hermit import Reasoner
from hermit.model import (
    DLOntology, OWLClass, OWLNamedIndividual,
    ClassAssertion, SubClassOf
)

onto = DLOntology()

# Schema (TBox)
Person = OWLClass("http://example.org/Person")
Employee = OWLClass("http://example.org/Employee")
onto.add_axiom(SubClassOf(Employee, Person))

# Data (ABox) - Create individuals
alice = OWLNamedIndividual("http://example.org/alice")
bob = OWLNamedIndividual("http://example.org/bob")

# Add facts: alice is an Employee
onto.add_axiom(ClassAssertion(Employee, alice))

# Add facts: bob is a Person
onto.add_axiom(ClassAssertion(Person, bob))

reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Query: Is alice an Employee?
print(reasoner.has_type(alice, Employee))  # True

# Query: Is alice a Person? (inferred!)
print(reasoner.has_type(alice, Person))  # True

reasoner.dispose()
```

## Part 2: Object Properties (Relationships)

Connect instances using properties:

```python
from hermit.model import OWLObjectProperty, ObjectPropertyAssertion

onto = DLOntology()

# Classes
Person = OWLClass("http://example.org/Person")
Company = OWLClass("http://example.org/Company")

# Properties
worksFor = OWLObjectProperty("http://example.org/worksFor")
employs = OWLObjectProperty("http://example.org/employs")

# Individuals
alice = OWLNamedIndividual("http://example.org/alice")
company_a = OWLNamedIndividual("http://example.org/CompanyA")

# Add facts
onto.add_axiom(ClassAssertion(Person, alice))
onto.add_axiom(ClassAssertion(Company, company_a))

# Add relationships
onto.add_axiom(ObjectPropertyAssertion(worksFor, alice, company_a))
onto.add_axiom(ObjectPropertyAssertion(employs, company_a, alice))

reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Query relationships
companies = reasoner.get_object_property_values(worksFor, alice)
print(f"Alice works for: {companies}")  # [CompanyA]

employees = reasoner.get_object_property_values(employs, company_a)
print(f"CompanyA employs: {employees}")  # [alice]

reasoner.dispose()
```

## Part 3: Data Properties (Attributes)

Add typed data values:

```python
from hermit.model import OWLDataProperty, DataPropertyAssertion, Literal

onto = DLOntology()

Person = OWLClass("http://example.org/Person")

# Data properties
hasName = OWLDataProperty("http://example.org/hasName")
hasAge = OWLDataProperty("http://example.org/hasAge")
hasEmail = OWLDataProperty("http://example.org/hasEmail")

alice = OWLNamedIndividual("http://example.org/alice")

onto.add_axiom(ClassAssertion(Person, alice))

# Add data values
onto.add_axiom(DataPropertyAssertion(
    hasName, alice, Literal("Alice Smith", "string")
))
onto.add_axiom(DataPropertyAssertion(
    hasAge, alice, Literal(30, "integer")
))
onto.add_axiom(DataPropertyAssertion(
    hasEmail, alice, Literal("alice@example.org", "string")
))

reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Query data properties
names = reasoner.get_data_property_values(hasName, alice)
print(f"Name: {names}")  # ['Alice Smith']

ages = reasoner.get_data_property_values(hasAge, alice)
print(f"Age: {ages}")  # [30]

reasoner.dispose()
```

## Part 4: Type Checking and Querying

Query what instances belong to a class:

```python
onto = DLOntology()

# Classes
Person = OWLClass("http://example.org/Person")
Employee = OWLClass("http://example.org/Employee")
Manager = OWLClass("http://example.org/Manager")

# Rules
onto.add_axiom(SubClassOf(Employee, Person))
onto.add_axiom(SubClassOf(Manager, Employee))

# Create instances
alice = OWLNamedIndividual("http://example.org/alice")
bob = OWLNamedIndividual("http://example.org/bob")
charlie = OWLNamedIndividual("http://example.org/charlie")

onto.add_axiom(ClassAssertion(Manager, alice))
onto.add_axiom(ClassAssertion(Employee, bob))
onto.add_axiom(ClassAssertion(Person, charlie))

reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Query 1: Get all instances of a class
all_persons = reasoner.get_instances(Person)
print(f"All persons: {len(all_persons)}")  # 3 (alice, bob, charlie)

all_employees = reasoner.get_instances(Employee)
print(f"All employees: {len(all_employees)}")  # 2 (alice, bob)

# Query 2: Get direct instances (not including inferred)
direct_managers = reasoner.get_direct_instances(Manager)
print(f"Direct managers: {len(direct_managers)}")  # 1 (alice)

# Query 3: Get types of an individual
alice_types = reasoner.get_types(alice)
print(f"Alice's types: {alice_types}")  # {Manager, Employee, Person}

# Query 4: Get only direct types
alice_direct_types = reasoner.get_direct_types(alice)
print(f"Alice's direct type: {alice_direct_types}")  # {Manager}

reasoner.dispose()
```

## Part 5: Negative Facts (Negation)

Assert what is NOT true:

```python
from hermit.model import Complement

onto = DLOntology()

Person = OWLClass("http://example.org/Person")
NotEmployee = Complement(OWLClass("http://example.org/Employee"))

alice = OWLNamedIndividual("http://example.org/alice")

onto.add_axiom(ClassAssertion(Person, alice))
onto.add_axiom(ClassAssertion(NotEmployee, alice))

# Now alice is a Person but not an Employee

reasoner = Reasoner(onto)
reasoner.precompute_inferences()

Employee = OWLClass("http://example.org/Employee")
print(f"Is alice an Employee? {reasoner.has_type(alice, Employee)}")  # False

reasoner.dispose()
```

## Part 6: Bulk Operations

Efficiently add many instances:

```python
onto = DLOntology()

Person = OWLClass("http://example.org/Person")
hasAge = OWLDataProperty("http://example.org/hasAge")

# Add 1000 people
people = []
for i in range(1000):
    person = OWLNamedIndividual(f"http://example.org/person{i}")
    onto.add_axiom(ClassAssertion(Person, person))
    onto.add_axiom(DataPropertyAssertion(
        hasAge, person, Literal(20 + (i % 50), "integer")
    ))
    people.append(person)

# Reason once
reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Query
all_persons = reasoner.get_instances(Person)
print(f"Total persons: {len(all_persons)}")

reasoner.dispose()
```

## Part 7: Consistency with Instances

Adding contradictory data:

```python
from hermit.model import DisjointClasses

onto = DLOntology()

Student = OWLClass("http://example.org/Student")
Employee = OWLClass("http://example.org/Employee")

# Students and employees are disjoint
onto.add_axiom(DisjointClasses(Student, Employee))

alice = OWLNamedIndividual("http://example.org/alice")

# Consistent scenario
onto.add_axiom(ClassAssertion(Student, alice))

reasoner = Reasoner(onto)
print(f"Consistent? {reasoner.is_consistent()}")  # True

# Inconsistent scenario
onto.add_axiom(ClassAssertion(Employee, alice))

reasoner2 = Reasoner(onto)
print(f"Consistent? {reasoner2.is_consistent()}")  # False

reasoner.dispose()
reasoner2.dispose()
```

## Query API Cheat Sheet

```python
# Type checking
reasoner.has_type(individual, class_)  # bool

# Get instances
reasoner.get_instances(class_)  # Set of individuals
reasoner.get_direct_instances(class_)  # Only direct instances

# Get types
reasoner.get_types(individual)  # All types (inferred)
reasoner.get_direct_types(individual)  # Only asserted types

# Get property values
reasoner.get_object_property_values(property, individual)  # Set of individuals
reasoner.get_data_property_values(property, individual)  # Set of data values

# Check relationships
reasoner.get_related_individuals(property, individual)  # Connected individuals

# Check consistency
reasoner.is_consistent()  # bool
```

## Real-World Example: Library System

```python
onto = DLOntology()

# Classes
Book = OWLClass("http://example.org/Book")
Author = OWLClass("http://example.org/Author")
Patron = OWLClass("http://example.org/Patron")

# Properties
writtenBy = OWLObjectProperty("http://example.org/writtenBy")
borrowedBy = OWLObjectProperty("http://example.org/borrowedBy")
hasISBN = OWLDataProperty("http://example.org/hasISBN")
hasTitle = OWLDataProperty("http://example.org/hasTitle")

# Data
python_book = OWLNamedIndividual("http://example.org/python-book")
guido = OWLNamedIndividual("http://example.org/guido")
alice_patron = OWLNamedIndividual("http://example.org/alice")

# Schema
onto.add_axiom(SubClassOf(Book, OWLClass("http://www.w3.org/2002/07/owl#Thing")))

# Add facts
onto.add_axiom(ClassAssertion(Book, python_book))
onto.add_axiom(ClassAssertion(Author, guido))
onto.add_axiom(ClassAssertion(Patron, alice_patron))

onto.add_axiom(ObjectPropertyAssertion(writtenBy, python_book, guido))
onto.add_axiom(ObjectPropertyAssertion(borrowedBy, python_book, alice_patron))

onto.add_axiom(DataPropertyAssertion(hasTitle, python_book, Literal("Python Essentials", "string")))
onto.add_axiom(DataPropertyAssertion(hasISBN, python_book, Literal("123-456-789", "string")))

# Query
reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Who wrote this book?
authors = reasoner.get_object_property_values(writtenBy, python_book)
print(f"Authors: {authors}")

# Who borrowed this book?
borrowers = reasoner.get_object_property_values(borrowedBy, python_book)
print(f"Borrowers: {borrowers}")

reasoner.dispose()
```

## Key Takeaways

1. **Instances** are the data that belongs to classes
2. **Object properties** connect individuals to each other
3. **Data properties** add typed attributes
4. **Type checking** verifies class membership
5. **Queries** retrieve instances and related data
6. **Consistency** ensures contradictions are caught

## Try This!

Create an ontology for:
- A person with multiple addresses
- A product with ratings from multiple users
- A student enrolled in multiple courses with grades
- Query for all students in a course with grade > 8.0

## Next Steps

- **[Advanced Restrictions](./02-restrictions.md)** — Add cardinality constraints to your data
- **[Rules and Queries](./03-rules-and-queries.md)** — Write complex queries
- **[API Reference](../api/core.md)** — Complete API docs
