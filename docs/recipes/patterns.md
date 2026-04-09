# Common Patterns

Reusable patterns and idioms for ontology design and querying.

## Pattern 1: Role Hierarchies

Model hierarchy of relationships.

```python
from hermit.model import SubObjectPropertyOf

# Property hierarchy
# supervises ⊆ manages ⊆ worksFor
onto.add_axiom(SubObjectPropertyOf(supervises, manages))
onto.add_axiom(SubObjectPropertyOf(manages, worksFor))

# Now relationships inherit
# If A supervises B, then A also manages B
```

## Pattern 2: Union Types

Express "A or B" relationships.

```python
from hermit.model import Union

# A Contact can be a Person or an Organization
Contact = Union(Person, Organization)

onto.add_axiom(SubClassOf(
    Email,
    ForAll(sentTo, Contact)  # Email can be sent to Person or Organization
))
```

## Pattern 3: Many-to-Many Relationships

Model relationships where both sides can have multiple partners.

```python
# Student enrolls in multiple Courses
# Course has multiple Students
enrollment = OWLObjectProperty("http://example.org/enrollment")

onto.add_axiom(SubClassOf(
    Student,
    AtLeast(1, enrollment, Course)  # Student in at least 1 course
))

onto.add_axiom(SubClassOf(
    Course,
    AtLeast(1, ReverseProperty(enrollment), Student)  # Course has at least 1 student
))
```

## Pattern 4: Quality Attributes

Add quality scores or ratings.

```python
# Product has quality rating (0-100)
quality = OWLDataProperty("http://example.org/quality")

product = OWLNamedIndividual("http://example.org/laptop")

onto.add_axiom(DataPropertyAssertion(
    quality, product, Literal(85, "integer")
))

# Query by quality
excellent = OWLClass("http://example.org/ExcellentProduct")
onto.add_axiom(SubClassOf(
    Product,
    # Products with quality ≥ 90
    # (Would need a more expressive framework for numeric constraints)
))
```

## Pattern 5: Version Management

Track versions of entities.

```python
# Different versions of a document
version = OWLDataProperty("http://example.org/version")
versionOf = OWLObjectProperty("http://example.org/versionOf")

doc_v1 = OWLNamedIndividual("http://example.org/report_v1")
doc_v2 = OWLNamedIndividual("http://example.org/report_v2")

onto.add_axiom(DataPropertyAssertion(version, doc_v1, Literal(1, "integer")))
onto.add_axiom(DataPropertyAssertion(version, doc_v2, Literal(2, "integer")))
onto.add_axiom(ObjectPropertyAssertion(versionOf, doc_v2, doc_v1))
```

## Pattern 6: Temporal Relationships

Model time-dependent relationships.

```python
# Employment with start and end dates
startDate = OWLDataProperty("http://example.org/startDate")
endDate = OWLDataProperty("http://example.org/endDate")

# Create a "Employment" relationship record
employment = OWLNamedIndividual("http://example.org/emp_alice_2020")

onto.add_axiom(DataPropertyAssertion(startDate, employment, Literal("2020-01-15", "date")))
onto.add_axiom(DataPropertyAssertion(endDate, employment, Literal("2023-12-31", "date")))

# Link people and company
onto.add_axiom(ObjectPropertyAssertion(hasEmployee, company, employment))
onto.add_axiom(ObjectPropertyAssertion(hasEmployer, employment, person))
```

## Pattern 7: Composite Objects

Model objects made up of parts.

```python
# Car made of Engine, Wheels, Transmission
hasPart = OWLObjectProperty("http://example.org/hasPart")

onto.add_axiom(SubClassOf(
    Car,
    Intersection(
        ∃hasPart.Engine,
        ∃hasPart.Wheel,
        ∃hasPart.Transmission
    )
))

# Create a car
my_car = OWLNamedIndividual("http://example.org/my_car")
engine = OWLNamedIndividual("http://example.org/engine_123")
wheel1 = OWLNamedIndividual("http://example.org/wheel_1")

onto.add_axiom(ClassAssertion(Car, my_car))
onto.add_axiom(ClassAssertion(Engine, engine))
onto.add_axiom(ClassAssertion(Wheel, wheel1))

onto.add_axiom(ObjectPropertyAssertion(hasPart, my_car, engine))
onto.add_axiom(ObjectPropertyAssertion(hasPart, my_car, wheel1))
```

## Pattern 8: Reification (Relationship with Attributes)

Add attributes to relationships.

```python
# Instead of:
# manages(alice, bob)
#
# Use:
# (Relationship) -- hasActor --> alice
#              |-- hasTarget --> bob
#              |-- startDate --> 2020-01-01

manages_relationship = OWLNamedIndividual("http://example.org/manages_rel_1")

hasActor = OWLObjectProperty("http://example.org/hasActor")
hasTarget = OWLObjectProperty("http://example.org/hasTarget")
startDate = OWLDataProperty("http://example.org/startDate")

onto.add_axiom(ClassAssertion(ManagementRelationship, manages_relationship))
onto.add_axiom(ObjectPropertyAssertion(hasActor, manages_relationship, alice))
onto.add_axiom(ObjectPropertyAssertion(hasTarget, manages_relationship, bob))
onto.add_axiom(DataPropertyAssertion(startDate, manages_relationship, Literal("2020-01-01", "date")))
```

## Pattern 9: Closed-World Assumptions

Use negative facts to enforce closed-world semantics.

```python
from hermit.model import NegativeDataPropertyAssertion

# In OWL (open-world): unknown = could be anything
# Alice's age is not asserted = unknown

# Force closed-world: not asserted = false
# Alice explicitly does NOT have age 30, 31, ...

for age in range(0, 100):
    if age != 28:  # Alice is 28
        onto.add_axiom(NegativeDataPropertyAssertion(
            hasAge, alice, Literal(age, "integer")
        ))
```

## Pattern 10: Constraint Checking

Model constraints as unsatisfiable classes.

```python
# Definition: Valid person = has age ≥ 0 and age ≤ 150
ValidPerson = OWLClass("http://example.org/ValidPerson")

# Definition: Invalid person = the negation
InvalidPerson = Complement(ValidPerson)

# Add a person that violates age constraint
invalid = OWLNamedIndividual("http://example.org/invalid")
onto.add_axiom(ClassAssertion(Person, invalid))
onto.add_axiom(DataPropertyAssertion(hasAge, invalid, Literal(-5, "integer")))

# Check consistency
reasoner = Reasoner(onto)
if not reasoner.is_consistent():
    print("Invalid person added - constraint violated")
```

## Pattern 11: Type Hierarchies with Shortcuts

Create multi-level hierarchies with direct links.

```python
# Standard hierarchy
onto.add_axiom(SubClassOf(Dog, Mammal))
onto.add_axiom(SubClassOf(Mammal, Animal))

# Shortcut (often asserted for efficiency)
onto.add_axiom(SubClassOf(Dog, Animal))  # Direct link

# Reasoner infers both paths
# Dog ⊆ Mammal ⊆ Animal  (transitive)
# Dog ⊆ Animal  (direct)
```

## Pattern 12: Parametric Queries

Query with variable parameters.

```python
def get_all_of_type(reasoner, type_name):
    """Get all instances of a type."""
    cls = OWLClass(f"http://example.org/{type_name}")
    return reasoner.get_instances(cls)

def get_related_via(reasoner, individual, property_name):
    """Get all individuals related via a property."""
    prop = OWLObjectProperty(f"http://example.org/{property_name}")
    return reasoner.get_object_property_values(prop, individual)

# Use
employees = get_all_of_type(reasoner, "Employee")
alice_children = get_related_via(reasoner, alice, "hasChild")
```

## Pattern 13: Ontology Composition

Combine multiple ontologies.

```python
# Create base ontology
base_onto = DLOntology()
# ... add common classes ...

# Create domain-specific ontology
domain_onto = DLOntology()
# ... add domain classes ...

# Combine them
combined_onto = DLOntology()
for axiom in base_onto.logical_axioms:
    combined_onto.add_axiom(axiom)
for axiom in domain_onto.logical_axioms:
    combined_onto.add_axiom(axiom)

reasoner = Reasoner(combined_onto)
reasoner.precompute_inferences()
```

## Pattern 14: Query Caching

Cache query results for performance.

```python
class CachedReasoner:
    def __init__(self, reasoner):
        self.reasoner = reasoner
        self.cache = {}
    
    def get_instances(self, cls):
        key = ("instances", cls.iri)
        if key not in self.cache:
            self.cache[key] = self.reasoner.get_instances(cls)
        return self.cache[key]
    
    def is_subclass(self, cls1, cls2):
        key = ("subclass", cls1.iri, cls2.iri)
        if key not in self.cache:
            self.cache[key] = self.reasoner.is_subclass_of(cls1, cls2)
        return self.cache[key]

# Use
cached = CachedReasoner(reasoner)
instances1 = cached.get_instances(MyClass)  # Computed
instances2 = cached.get_instances(MyClass)  # From cache
```

## Pattern 15: Incremental Ontology Building

Build ontology piece by piece.

```python
def build_organizational_ontology():
    onto = DLOntology()
    
    # Step 1: Core classes
    onto.add_axiom(SubClassOf(
        OWLClass("http://example.org/Organization"),
        OWLClass("http://www.w3.org/2002/07/owl#Thing")
    ))
    
    # Step 2: Employee hierarchy
    onto.add_axiom(SubClassOf(
        OWLClass("http://example.org/Employee"),
        OWLClass("http://example.org/Person")
    ))
    
    # Step 3: Positions
    onto.add_axiom(SubClassOf(
        OWLClass("http://example.org/Manager"),
        OWLClass("http://example.org/Employee")
    ))
    
    return onto

onto = build_organizational_ontology()
```

---

**See Also:**
- **[Rules and Queries](../tutorials/03-rules-and-queries.md)** — More complex patterns
- **[Ontology Debugging](./debugging.md)** — Finding issues in patterns
