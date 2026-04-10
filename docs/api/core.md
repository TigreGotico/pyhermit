# Core API Reference

Complete reference for the main PyHermit APIs.

## Main Classes

### Reasoner

The main entry point for reasoning operations.

```python
from hermit import Reasoner

reasoner = Reasoner(ontology)
```

#### Methods

**Initialization & Control**

```python
# Create reasoner
reasoner = Reasoner(ontology)

# Precompute all inferences (recommended for multiple queries)
reasoner.precompute_inferences(class_hierarchy=True)

# Dispose (release resources)
reasoner.dispose()
```

**TBox (Class) Reasoning**

```python
# Check if Class1 is a subclass of Class2
is_subclass = reasoner.is_subclass_of(Class1, Class2)  # bool

# Check if a class can have instances
is_satisfiable = reasoner.is_satisfiable(MyClass)  # bool

# Get unsatisfiable classes
unsatisfiable = reasoner.get_unsatisfiable_classes()  # Set[OWLClass]

# Get all classes
classes = reasoner.get_classes()  # Set[OWLClass]

# Get class hierarchy
hierarchy = reasoner.get_class_hierarchy()  # HierarchyNode

# Get subclasses
subclasses = reasoner.get_subclasses(MyClass)  # Set[OWLClass]

# Get superclasses
superclasses = reasoner.get_superclasses(MyClass)  # Set[OWLClass]
```

**ABox (Individual) Reasoning**

```python
# Check if individual has type
has_type = reasoner.has_type(individual, MyClass)  # bool

# Get all types of individual (including inferred)
types = reasoner.get_types(individual)  # Set[OWLClass]

# Get only direct types (asserted)
direct_types = reasoner.get_direct_types(individual)  # Set[OWLClass]

# Get all instances of a class
instances = reasoner.get_instances(MyClass)  # Set[OWLNamedIndividual]

# Get only direct instances
direct_instances = reasoner.get_direct_instances(MyClass)  # Set[OWLNamedIndividual]
```

**Property Reasoning**

```python
# Get all individuals that have property relationship
values = reasoner.get_object_property_values(property, individual)  # Set[OWLNamedIndividual]

# Get all data values
data_values = reasoner.get_data_property_values(property, individual)  # Set[object]

# Get individuals related by property
related = reasoner.get_related_individuals(property, individual)  # Set[OWLNamedIndividual]
```

**Consistency**

```python
# Check if ontology is consistent
is_consistent = reasoner.is_consistent()  # bool
```

---

### DLOntology

Container for axioms (TBox and ABox).

```python
from hermit.model import DLOntology

onto = DLOntology()
```

#### Methods

```python
# Add an axiom
onto.add_axiom(axiom)

# Get all axioms
axioms = onto.logical_axioms  # Iterable[Axiom]

# Add multiple axioms
onto.add_axioms([axiom1, axiom2, axiom3])
```

---

## Class Definitions

### OWLClass

Represents a class (concept) in OWL.

```python
from hermit.model import OWLClass

# Create a class
Person = OWLClass("http://example.org/Person")
```

#### Methods

```python
# Get IRI
iri = MyClass.iri  # str

# String representation
str_repr = str(MyClass)  # "http://example.org/Person"
```

---

### OWLNamedIndividual

Represents an individual (instance) in OWL.

```python
from hermit.model import OWLNamedIndividual

# Create an individual
alice = OWLNamedIndividual("http://example.org/alice")
```

#### Methods

```python
# Get IRI
iri = alice.iri  # str
```

---

## Properties

### OWLObjectProperty

Represents a relationship between individuals.

```python
from hermit.model import OWLObjectProperty

# Create property
hasChild = OWLObjectProperty("http://example.org/hasChild")
```

### OWLDataProperty

Represents an attribute with typed values.

```python
from hermit.model import OWLDataProperty

# Create property
hasAge = OWLDataProperty("http://example.org/hasAge")
```

---

## Axioms (Rules)

### SubClassOf

"A is a subclass of B" (A ⊆ B)

```python
from hermit.model import SubClassOf

onto.add_axiom(SubClassOf(Dog, Animal))
```

### Intersection

"A AND B" (A ⊓ B)

```python
from hermit.model import Intersection

intersection = Intersection(Parent, Teacher)  # Both parent and teacher
```

### Union

"A OR B" (A ⊔ B)

```python
from hermit.model import Union

union = Union(Student, Teacher)  # Either student or teacher
```

### Complement

"NOT A" (¬A)

```python
from hermit.model import Complement

not_student = Complement(Student)
```

### AtLeast

"At least N R some C" (≥N R.C)

```python
from hermit.model import AtLeast

onto.add_axiom(SubClassOf(
    Parent,
    AtLeast(1, hasChild, Person)  # Has at least one child
))
```

### AtMost

"At most N R some C" (≤N R.C)

```python
from hermit.model import AtMost

onto.add_axiom(SubClassOf(
    MonogamousPerson,
    AtMost(1, hasSpouse, Person)  # At most one spouse
))
```

### ForAll

"All R have C" (∀R.C)

```python
from hermit.model import ForAll

onto.add_axiom(SubClassOf(
    GoodTeacher,
    ForAll(teaches, Competent)  # All taught students are competent
))
```

### ClassAssertion

"Individual I has class C" (I:C)

```python
from hermit.model import ClassAssertion

onto.add_axiom(ClassAssertion(Dog, fido))  # fido is a Dog
```

### ObjectPropertyAssertion

"Individual I has property P to individual J" (P(I,J))

```python
from hermit.model import ObjectPropertyAssertion

onto.add_axiom(ObjectPropertyAssertion(hasChild, alice, bob))
```

### DataPropertyAssertion

"Individual I has data property P with value V"

```python
from hermit.model import DataPropertyAssertion, Literal

onto.add_axiom(DataPropertyAssertion(
    hasAge, alice, Literal(30, "integer")
))
```

### DisjointClasses

"A and B are mutually exclusive" (A ⊓ B ⊓ ¬C)

```python
from hermit.model import DisjointClasses

onto.add_axiom(DisjointClasses(Student, Teacher))
```

### EquivalentClasses

"A and B are equivalent" (A ≡ B)

```python
from hermit.model import EquivalentClasses

onto.add_axiom(EquivalentClasses(
    Parent,
    Intersection(Person, ∃hasChild.Person)
))
```

### InverseOf

"Property P1 is inverse of P2"

```python
from hermit.model import InverseOf

onto.add_axiom(InverseOf(hasParent, hasChild))
```

### Transitive

"Property is transitive" (if A→B→C then A→C)

```python
from hermit.model import Transitive

onto.add_axiom(Transitive(manages))  # If A manages B and B manages C, then A manages C
```

### Symmetric

"Property is symmetric" (if A→B then B→A)

```python
from hermit.model import Symmetric

onto.add_axiom(Symmetric(hasFriend))
```

---

## Data Types

### Literal

Represents a typed data value.

```python
from hermit.model import Literal

name = Literal("Alice", "string")
age = Literal(30, "integer")
pi = Literal(3.14159, "double")
active = Literal(True, "boolean")
birth = Literal("1990-01-15", "date")
```

### Supported Data Types

```
"string"      - Text
"integer"     - Whole numbers
"decimal"     - Fixed-point decimal
"float"       - Single-precision floating point
"double"      - Double-precision floating point
"boolean"     - True/False
"date"        - ISO 8601 date (YYYY-MM-DD)
"dateTime"    - ISO 8601 datetime
"anyURI"      - URIs
"base64Binary" - Base64-encoded data
"hexBinary"   - Hexadecimal-encoded data
```

---

## Exception Types

### UnsupportedDatatypeException

Raised when using an unsupported datatype.

```python
from hermit.datatypes.registry import UnsupportedDatatypeException

try:
    value = Literal(12345, "unsupported_type")
except UnsupportedDatatypeException as e:
    print(f"Error: {e}")
```

### MalformedLiteralException

Raised when a literal value doesn't match its type.

```python
from hermit.datatypes.registry import MalformedLiteralException

try:
    value = Literal("not_a_number", "integer")
except MalformedLiteralException as e:
    print(f"Error: {e}")
```

---

## Complete Example

```python
from hermit import Reasoner
from hermit.model import (
    DLOntology, OWLClass, OWLNamedIndividual,
    OWLObjectProperty, OWLDataProperty,
    SubClassOf, ClassAssertion, ObjectPropertyAssertion,
    DataPropertyAssertion, AtLeast, Literal,
    DisjointClasses
)

# Create ontology
onto = DLOntology()

# Define classes
Person = OWLClass("http://example.org/Person")
Parent = OWLClass("http://example.org/Parent")
Child = OWLClass("http://example.org/Child")

# Define properties
hasChild = OWLObjectProperty("http://example.org/hasChild")
hasAge = OWLDataProperty("http://example.org/hasAge")

# Add rules
onto.add_axiom(SubClassOf(Parent, Person))
onto.add_axiom(SubClassOf(Child, Person))
onto.add_axiom(SubClassOf(Parent, AtLeast(1, hasChild, Child)))
onto.add_axiom(DisjointClasses(Parent, Child))

# Add facts
alice = OWLNamedIndividual("http://example.org/alice")
bob = OWLNamedIndividual("http://example.org/bob")

onto.add_axiom(ClassAssertion(Parent, alice))
onto.add_axiom(ClassAssertion(Child, bob))
onto.add_axiom(ObjectPropertyAssertion(hasChild, alice, bob))
onto.add_axiom(DataPropertyAssertion(hasAge, alice, Literal(40, "integer")))
onto.add_axiom(DataPropertyAssertion(hasAge, bob, Literal(10, "integer")))

# Reason
reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Query
print(f"Is alice a Person? {reasoner.has_type(alice, Person)}")  # True (inferred)
print(f"Is bob a Person? {reasoner.has_type(bob, Person)}")  # True
print(f"All Parents: {reasoner.get_instances(Parent)}")  # {alice}
print(f"All Children: {reasoner.get_instances(Child)}")  # {bob}

reasoner.dispose()
```

---

---

## Clausification Pipeline

### OWLNormalization

Transforms raw `OWLAxiom` objects into `NormalizedAxioms`. Source: `src/hermit/structural/owl_normalization.py:94`.

```python
from hermit.structural.owl_normalization import OWLNormalization

normalization = OWLNormalization()
normalized = normalization.normalize(axioms)  # list[OWLAxiom] -> NormalizedAxioms
```

`normalize()` populates:
- `normalized.simple_object_property_inclusions` — from `SubObjectPropertyOf` and `InverseObjectProperties` axioms (`owl_normalization.py:271`, `owl_normalization.py:208`)
- `normalized.complex_object_property_inclusions` — from `TransitiveObjectProperty` and `SubPropertyChainOf` axioms (`owl_normalization.py:190`, `owl_normalization.py:280`)

### OWLClausification

Converts `NormalizedAxioms` to a `DLOntology`. Source: `src/hermit/structural/owl_clausification.py:82`.

```python
from hermit.structural.owl_clausification import OWLClausification

clausification = OWLClausification()
dl_ontology = clausification.clausify(normalized)
```

`clausify()` calls `ObjectPropertyInclusionManager.rewrite_axioms()` before producing DL clauses (`owl_clausification.py:132`). This raises `ValueError` for any OWL 2 non-simplicity violation — see below.

### ObjectPropertyInclusionManager

Detects non-simple properties and validates OWL 2 constraints. Source: `src/hermit/structural/object_property_inclusion_manager.py:21`.

A property is **non-simple** if it:
1. Appears as the superrole of a transitive axiom or role chain (`_detect_complex_properties` — `object_property_inclusion_manager.py:167`)
2. Is a superrole of a non-simple property via `SubObjectPropertyOf`
3. Is the inverse of a non-simple property

`rewrite_axioms()` raises `ValueError` if a non-simple property appears in (`object_property_inclusion_manager.py:216`):
- `AsymmetricObjectProperty`
- `IrreflexiveObjectProperty`
- `DisjointObjectProperties`
- `ObjectMinCardinality`, `ObjectMaxCardinality`, `ObjectExactCardinality`
- `ObjectHasSelf`

### load_ontology

Loads OWL/RDF files via owlready2. Source: `src/hermit/parser.py:25`.

```python
from hermit.parser import load_ontology

axioms = load_ontology("path/to/ontology.owl")  # list[OWLAxiom]
```

Raises `ImportError` if owlready2 is not installed, `FileNotFoundError` if the path does not exist, `ValueError` if the file cannot be parsed.

### NonSimicityError (ValueError)

`OWLClausification.clausify()` raises `ValueError` with a message of the form:

```
Non-simple property '<iri>' cannot be asymmetric (OWL 2 violation)
Non-simple property '<iri>' cannot be irreflexive (OWL 2 violation)
Non-simple property '<iri>' cannot be in disjoint properties axiom (OWL 2 violation)
Non-simple property '<iri>' or its inverse appears in the cardinality restriction '...' (OWL 2 violation)
Non-simple property '<iri>' appears in a Self restriction (OWL 2 violation)
```

---

## See Also

- **[Tutorials](../tutorials/)** — Guided examples
