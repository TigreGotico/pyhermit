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

We use the standard helper and imports throughout:

```python
from hermit import Reasoner
from hermit.model import AtomicConcept, AtomicRole, Individual
from hermit.owl_model.class_expression import OWLClass
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_property import OWLDataProperty, OWLObjectProperty
from hermit.owl_model.owl_literal import OWLLiteral
from hermit.owl_model.owl_axiom import (
    OWLClassAssertionAxiom,
    OWLDataPropertyAssertionAxiom,
    OWLDisjointClassesAxiom,
    OWLObjectPropertyAssertionAxiom,
    OWLSubClassOfAxiom,
)
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization


def reasoner_from_axioms(axioms, ontology_iri="urn:example:onto"):
    normalized = OWLNormalization().process_ontology(axioms)
    return Reasoner(OWLClausification().clausify(normalized, ontology_iri=ontology_iri))


NS = "http://example.org/"
```

## Part 1: Creating and Adding Instances

```python
# Schema (TBox)
Person = OWLClass(NS + "Person")
Employee = OWLClass(NS + "Employee")

# Data (ABox) — create individuals
alice = OWLNamedIndividual(NS + "alice")
bob = OWLNamedIndividual(NS + "bob")

axioms = [
    OWLSubClassOfAxiom(Employee, Person),
    OWLClassAssertionAxiom(alice, Employee),  # alice is an Employee
    OWLClassAssertionAxiom(bob, Person),      # bob is a Person
]

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

employee = AtomicConcept.create(NS + "Employee")
person = AtomicConcept.create(NS + "Person")
alice_h = Individual.create(NS + "alice")

# Query: Is alice an Employee?
print(reasoner.has_type(alice_h, employee))  # True

# Query: Is alice a Person? (inferred!)
print(reasoner.has_type(alice_h, person))  # True

reasoner.dispose()
```

## Part 2: Object Properties (Relationships)

Connect instances using properties:

```python
Company = OWLClass(NS + "Company")
worksFor = OWLObjectProperty(NS + "worksFor")

company_a = OWLNamedIndividual(NS + "CompanyA")

axioms = [
    OWLClassAssertionAxiom(alice, Person),
    OWLClassAssertionAxiom(company_a, Company),
    # subject, property, object
    OWLObjectPropertyAssertionAxiom(alice, worksFor, company_a),
]

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

works_for_h = AtomicRole.create(NS + "worksFor")
company_a_h = Individual.create(NS + "CompanyA")

print("Does alice work for CompanyA?",
      reasoner.has_role_relationship(alice_h, works_for_h, company_a_h))  # True

reasoner.dispose()
```

## Part 3: Data Properties (Attributes)

Data properties attach typed values. `OWLLiteral` infers the datatype from
the Python value (`str` → `xsd:string`, `int` → `xsd:integer`, `bool` →
`xsd:boolean`, `float` → `xsd:double`):

```python
hasName = OWLDataProperty(NS + "hasName")
hasAge = OWLDataProperty(NS + "hasAge")

axioms = [
    OWLClassAssertionAxiom(alice, Person),
    OWLDataPropertyAssertionAxiom(alice, hasName, OWLLiteral("Alice Smith")),
    OWLDataPropertyAssertionAxiom(alice, hasAge, OWLLiteral(30)),
]

reasoner = reasoner_from_axioms(axioms)
print("Consistent with data values?", reasoner.is_consistent())  # True
reasoner.dispose()
```

Data ranges let the reasoner *classify* individuals by their values:

```python
from hermit.owl_model.class_expression import (
    OWLDataSomeValuesFrom, OWLDatatypeRestriction, OWLFacetRestriction,
)
from hermit.owl_model.owl_literal import IntegerOWLDatatype
from hermit.owl_model.vocab import OWLFacet
from hermit.owl_model.owl_axiom import OWLEquivalentClassesAxiom

Adult = OWLClass(NS + "Adult")
kid = OWLNamedIndividual(NS + "kid")

# Adult ≡ ∃hasAge.integer[≥ 18]
adult_range = OWLDatatypeRestriction(
    IntegerOWLDatatype,
    [OWLFacetRestriction(OWLFacet.MIN_INCLUSIVE, OWLLiteral(18))],
)
axioms = [
    OWLEquivalentClassesAxiom([Adult, OWLDataSomeValuesFrom(hasAge, adult_range)]),
    OWLDataPropertyAssertionAxiom(alice, hasAge, OWLLiteral(30)),
    OWLDataPropertyAssertionAxiom(kid, hasAge, OWLLiteral(7)),
]

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

adult = AtomicConcept.create(NS + "Adult")
print("Is alice an Adult?", reasoner.has_type(alice_h, adult))                    # True (inferred!)
print("Is kid an Adult?", reasoner.has_type(Individual.create(NS + "kid"), adult))  # False

reasoner.dispose()
```

**Output:**
```
Is alice an Adult? True
Is kid an Adult? False
```

## Part 4: Type Checking and Querying

Query what instances belong to a class:

```python
Manager = OWLClass(NS + "Manager")
charlie = OWLNamedIndividual(NS + "charlie")

axioms = [
    OWLSubClassOfAxiom(Employee, Person),
    OWLSubClassOfAxiom(Manager, Employee),
    OWLClassAssertionAxiom(alice, Manager),
    OWLClassAssertionAxiom(bob, Employee),
    OWLClassAssertionAxiom(charlie, Person),
]

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

manager = AtomicConcept.create(NS + "Manager")

# Query 1: Get all instances of a class
all_persons = reasoner.get_instances(person)
print(f"All persons: {len(all_persons)}")  # 3 (alice, bob, charlie)

all_employees = reasoner.get_instances(employee)
print(f"All employees: {len(all_employees)}")  # 2 (alice, bob)

# Query 2: Get only direct instances (most-specific class)
direct_employees = reasoner.get_instances(employee, direct=True)
print(f"Direct employees: {len(direct_employees)}")  # 1 (bob; alice is a Manager)

# Query 3: Get all types of an individual
alice_types = reasoner.get_types(alice_h)
print(f"Alice's types: {sorted(c.iri.split('/')[-1] for c in alice_types)}")

# Query 4: Get only the most specific types
alice_direct = reasoner.get_types(alice_h, direct=True)
print(f"Alice's direct type: {sorted(c.iri.split('/')[-1] for c in alice_direct)}")

reasoner.dispose()
```

**Output:**
```
All persons: 3
All employees: 2
Direct employees: 1
Alice's types: ['Employee', 'Manager', 'Person', 'owl#Thing']
Alice's direct type: ['Manager']
```

## Part 5: Negative Facts (Negation)

Assert what is NOT true:

```python
from hermit.owl_model.class_expression import OWLObjectComplementOf

axioms = [
    OWLClassAssertionAxiom(alice, Person),
    # alice is NOT an Employee
    OWLClassAssertionAxiom(alice, OWLObjectComplementOf(Employee)),
]

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

print(f"Is alice an Employee? {reasoner.has_type(alice_h, employee)}")  # False
print(f"Consistent? {reasoner.is_consistent()}")  # True

reasoner.dispose()
```

## Part 6: Bulk Operations

Efficiently add many instances:

```python
axioms = []
for i in range(1000):
    individual = OWLNamedIndividual(f"{NS}person{i}")
    axioms.append(OWLClassAssertionAxiom(individual, Person))
    axioms.append(OWLDataPropertyAssertionAxiom(
        individual, hasAge, OWLLiteral(20 + (i % 50)),
    ))

# Reason once
reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

all_persons = reasoner.get_instances(person)
print(f"Total persons: {len(all_persons)}")  # 1000

reasoner.dispose()
```

## Part 7: Consistency with Instances

Adding contradictory data:

```python
Student = OWLClass(NS + "Student")

base = [
    # Students and employees are disjoint
    OWLDisjointClassesAxiom([Student, Employee]),
    OWLClassAssertionAxiom(alice, Student),
]

reasoner = reasoner_from_axioms(base)
print(f"Consistent? {reasoner.is_consistent()}")  # True
reasoner.dispose()

# Inconsistent scenario: alice is both
reasoner2 = reasoner_from_axioms(base + [OWLClassAssertionAxiom(alice, Employee)])
print(f"Consistent? {reasoner2.is_consistent()}")  # False
reasoner2.dispose()
```

## Query API Cheat Sheet

All query methods take `hermit.model` handles
(`AtomicConcept.create(iri)`, `Individual.create(iri)`, `AtomicRole.create(iri)`):

```python
# doc-sample: skip (signature reference)
# Type checking
reasoner.has_type(individual, concept)             # bool
reasoner.has_type(individual, concept, direct=True)  # most-specific only

# Get instances
reasoner.get_instances(concept)                    # set of Individual
reasoner.get_instances(concept, direct=True)       # only direct instances

# Get types
reasoner.get_types(individual)                     # set of AtomicConcept
reasoner.get_types(individual, direct=True)        # only most-specific types

# Check relationships
reasoner.has_role_relationship(subject, role, obj) # bool

# Same-individual check
reasoner.is_same_individual(ind1, ind2)            # bool

# Check consistency
reasoner.is_consistent()                           # bool
```

## Real-World Example: Library System

```python
# Classes
Book = OWLClass(NS + "Book")
Author = OWLClass(NS + "Author")
Patron = OWLClass(NS + "Patron")

# Properties
writtenBy = OWLObjectProperty(NS + "writtenBy")
borrowedBy = OWLObjectProperty(NS + "borrowedBy")
hasISBN = OWLDataProperty(NS + "hasISBN")
hasTitle = OWLDataProperty(NS + "hasTitle")

# Data
python_book = OWLNamedIndividual(NS + "python-book")
guido = OWLNamedIndividual(NS + "guido")
alice_patron = OWLNamedIndividual(NS + "alice")

axioms = [
    OWLClassAssertionAxiom(python_book, Book),
    OWLClassAssertionAxiom(guido, Author),
    OWLClassAssertionAxiom(alice_patron, Patron),
    OWLObjectPropertyAssertionAxiom(python_book, writtenBy, guido),
    OWLObjectPropertyAssertionAxiom(python_book, borrowedBy, alice_patron),
    OWLDataPropertyAssertionAxiom(python_book, hasTitle, OWLLiteral("Python Essentials")),
    OWLDataPropertyAssertionAxiom(python_book, hasISBN, OWLLiteral("123-456-789")),
]

reasoner = reasoner_from_axioms(axioms, ontology_iri="urn:example:library")
reasoner.precompute_inferences()

book_h = Individual.create(NS + "python-book")
written_by_h = AtomicRole.create(NS + "writtenBy")
guido_h = Individual.create(NS + "guido")

# Who wrote this book?
print("Written by guido?", reasoner.has_role_relationship(book_h, written_by_h, guido_h))  # True

# All books in the library
books = reasoner.get_instances(AtomicConcept.create(NS + "Book"))
print(f"Books: {sorted(b.iri for b in books)}")

reasoner.dispose()
```

## Key Takeaways

1. **Instances** are the data that belongs to classes
2. **Object properties** connect individuals to each other
3. **Data properties** add typed attributes; data ranges drive classification
4. **Type checking** verifies class membership (asserted *and* inferred)
5. **`direct=True`** restricts queries to most-specific results
6. **Consistency** ensures contradictions are caught

## Try This!

Create an ontology for:
- A person with multiple addresses
- A product with ratings from multiple users
- A student enrolled in multiple courses
- A `Senior` class defined by `hasAge ≥ 65`, recognized automatically

## Next Steps

- **[Advanced Restrictions](./02-restrictions.md)** — Add cardinality constraints to your data
- **[Rules and Queries](./03-rules-and-queries.md)** — Write complex queries
- **[API Reference](../api/core.md)** — Complete API docs
