# Tutorial 2: Restrictions and Cardinality

Learn how to constrain properties with cardinality and value restrictions.

## What You'll Learn

- Universal restrictions (∀ - ForAll)
- Existential restrictions (∃ - AtLeast)
- Cardinality constraints
- Value restrictions
- How restrictions interact with reasoning

## Part 1: Existential Restrictions (AtLeast)

Existential restrictions assert that at least one instance exists with a property:

```python
from hermit import Reasoner
from hermit.model import (
    DLOntology, OWLClass, OWLObjectProperty,
    SubClassOf, AtLeast, ClassAssertion,
    OWLNamedIndividual
)

onto = DLOntology()

# Define classes
Parent = OWLClass("http://example.org/Parent")
HasChild = OWLClass("http://example.org/HasChild")
Person = OWLClass("http://example.org/Person")

# Define property
hasChild = OWLObjectProperty("http://example.org/hasChild")

# Add axiom: HasChild must have at least one child
# HasChild ⊆ ∃hasChild.Person
onto.add_axiom(SubClassOf(
    HasChild,
    AtLeast(1, hasChild, Person)
))

reasoner = Reasoner(onto)

# Create a person with no children
person_no_children = OWLNamedIndividual("http://example.org/john")
onto.add_axiom(ClassAssertion(Person, person_no_children))

# Create a parent with a child
parent = OWLNamedIndividual("http://example.org/alice")
child = OWLNamedIndividual("http://example.org/bob")
onto.add_axiom(ClassAssertion(Person, parent))
onto.add_axiom(ClassAssertion(Person, child))

# Add child relationship
from hermit.model import ObjectPropertyAssertion
onto.add_axiom(ObjectPropertyAssertion(hasChild, parent, child))

# Now alice can be a HasChild because she has a child
onto.add_axiom(ClassAssertion(HasChild, parent))

reasoner2 = Reasoner(onto)
reasoner2.precompute_inferences()

print("Is alice a HasChild?", reasoner2.has_type(parent, HasChild))  # True
print("Is john a HasChild?", reasoner2.has_type(person_no_children, HasChild))  # False

reasoner.dispose()
reasoner2.dispose()
```

**Output:**
```
Is alice a HasChild? True
Is john a HasChild? False
```

## Part 2: Universal Restrictions (ForAll)

Universal restrictions constrain all values of a property:

```python
from hermit.model import ForAll, Complement

onto = DLOntology()

# Define classes
GoodTeacher = OWLClass("http://example.org/GoodTeacher")
Student = OWLClass("http://example.org/Student")
Competent = OWLClass("http://example.org/Competent")

# Define property
teaches = OWLObjectProperty("http://example.org/teaches")

# GoodTeacher: All taught students must be competent
# GoodTeacher ⊆ ∀teaches.Competent
onto.add_axiom(SubClassOf(
    GoodTeacher,
    ForAll(teaches, Competent)
))

reasoner = Reasoner(onto)

# Create individuals
teacher = OWLNamedIndividual("http://example.org/prof_smith")
student1 = OWLNamedIndividual("http://example.org/student1")
student2 = OWLNamedIndividual("http://example.org/student2")

onto.add_axiom(ClassAssertion(Person, teacher))
onto.add_axiom(ClassAssertion(Student, student1))
onto.add_axiom(ClassAssertion(Student, student2))
onto.add_axiom(ClassAssertion(Competent, student1))
onto.add_axiom(ClassAssertion(Competent, student2))

# Teach students
onto.add_axiom(ObjectPropertyAssertion(teaches, teacher, student1))
onto.add_axiom(ObjectPropertyAssertion(teaches, teacher, student2))

# Now teacher can be a GoodTeacher
onto.add_axiom(ClassAssertion(GoodTeacher, teacher))

reasoner2 = Reasoner(onto)
reasoner2.precompute_inferences()

print("Is prof_smith a GoodTeacher?", reasoner2.has_type(teacher, GoodTeacher))  # True

reasoner.dispose()
reasoner2.dispose()
```

**Output:**
```
Is prof_smith a GoodTeacher? True
```

## Part 3: Exact Cardinality

Exact cardinality constraints:

```python
onto = DLOntology()

# Define classes
President = OWLClass("http://example.org/President")
Country = OWLClass("http://example.org/Country")

# Define property
governs = OWLObjectProperty("http://example.org/governs")

# A President governs exactly one country
# President ⊆ ∃governs.Country ⊓ ∀governs.Country ⊓ ≤1governs.Country
onto.add_axiom(SubClassOf(
    President,
    AtLeast(1, governs, Country)
))

# This is the typical way to express "exactly one"
# Other restrictions would need to be added for completeness

reasoner = Reasoner(onto)
# ... rest of the example
```

## Part 4: Combining Restrictions

Complex restrictions help model real-world constraints:

```python
from hermit.model import AtMost, Intersection

onto = DLOntology()

# Define classes
Supervisor = OWLClass("http://example.org/Supervisor")
Employee = OWLClass("http://example.org/Employee")
Person = OWLClass("http://example.org/Person")

# Define property
supervises = OWLObjectProperty("http://example.org/supervises")

# Supervisor: Person who supervises between 1 and 10 employees
# Supervisor ⊆ ∃supervises.Employee ⊓ ≤10supervises.Employee
onto.add_axiom(SubClassOf(
    Supervisor,
    Intersection(
        AtLeast(1, supervises, Employee),
        AtMost(10, supervises, Employee)
    )
))

# Create persons and mark one as supervisor with employees
supervisor = OWLNamedIndividual("http://example.org/alice")
employees = [
    OWLNamedIndividual(f"http://example.org/employee{i}")
    for i in range(5)
]

onto.add_axiom(ClassAssertion(Person, supervisor))
for emp in employees:
    onto.add_axiom(ClassAssertion(Employee, emp))
    onto.add_axiom(ObjectPropertyAssertion(supervises, supervisor, emp))

onto.add_axiom(ClassAssertion(Supervisor, supervisor))

reasoner = Reasoner(onto)
reasoner.precompute_inferences()

print("Is alice a Supervisor?", reasoner.has_type(supervisor, Supervisor))  # True

reasoner.dispose()
```

## Part 5: Reasoning with Restrictions

How restrictions help the reasoner:

```python
onto = DLOntology()

# Define a restriction-based hierarchy
HasFriends = OWLClass("http://example.org/HasFriends")
Person = OWLClass("http://example.org/Person")
hasFriend = OWLObjectProperty("http://example.org/hasFriend")

# HasFriends ⊆ ∃hasFriend.Person
onto.add_axiom(SubClassOf(
    HasFriends,
    AtLeast(1, hasFriend, Person)
))

person1 = OWLNamedIndividual("http://example.org/alice")
person2 = OWLNamedIndividual("http://example.org/bob")

onto.add_axiom(ClassAssertion(Person, person1))
onto.add_axiom(ClassAssertion(Person, person2))
onto.add_axiom(ObjectPropertyAssertion(hasFriend, person1, person2))

# Alice doesn't have HasFriends type yet
onto.add_axiom(ClassAssertion(HasFriends, person1))

reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Query to understand the restriction
print("Alice has friends?", reasoner.has_type(person1, HasFriends))  # True
print("Alice's friends:", reasoner.get_object_property_values(hasFriend, person1))

reasoner.dispose()
```

## Common Patterns

### 1. "At Least One" (Existential)
```python
# Everyone must have a name
SubClassOf(Person, AtLeast(1, hasName, String))
```

### 2. "All Values" (Universal)
```python
# All friends must be persons
SubClassOf(Person, ForAll(hasFriend, Person))
```

### 3. "Exactly N"
```python
# Parents have exactly 2 biological parents
SubClassOf(
    Person,
    Intersection(
        AtLeast(2, hasParent, Person),
        AtMost(2, hasParent, Person)
    )
)
```

### 4. "At Most N"
```python
# Each person has at most 1 spouse
SubClassOf(Person, AtMost(1, hasSpouse, Person))
```

## Key Takeaways

1. **Existential restrictions (∃)** assert something exists
2. **Universal restrictions (∀)** constrain all values
3. **Cardinality** limits how many values a property can have
4. Restrictions enable the reasoner to infer new facts
5. Combinations of restrictions model complex real-world rules

## Try This!

Create an ontology for a university with:
- Students (at least 1 course, not more than 5)
- Professors (at least 1 student, all students must be enrolled)
- Courses (exactly 1 professor)
- Requirements (prerequisites, corequisites)

## Next Steps

- **[Tutorial 3: Rules and Queries](./03-rules-and-queries.md)** — Learn SWRL-like rules
- **[Tutorial 4: Advanced Reasoning](./04-advanced-reasoning.md)** — Reasoning strategies and optimization
- **[API Reference](../api/core.md)** — OWLClass, properties, and restrictions API
