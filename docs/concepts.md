# Core Concepts: From Zero to Understanding OWL Reasoning

Before writing code, let's understand what PyHermit does and why you might need it.

## The Problem

You have structured data — information about people, organizations, products, relationships. You want to:

- Ask questions: "Who are all the managers?"
- Find inconsistencies: "This person is both a student and a teacher in the same program"
- Infer new facts: "If John reports to Alice and Alice reports to Bob, who does John indirectly report to?"

Traditional databases are good at storing data, but terrible at reasoning about relationships and answering complex questions.

## The Solution: Ontologies & Reasoning

An **ontology** is a formal description of concepts and their relationships:

```
Person:
  - has a name (string)
  - has an age (integer, minimum 0)
  - can be a Student
  - can be a Teacher

Teacher:
  - is a type of Person
  - teaches a Course
  - has at least 1 Student

Student:
  - is a type of Person
  - learns from at least 1 Teacher
  - cannot be a Teacher at the same time
```

A **reasoner** is a tool that:

1. **Understands** your ontology (the rules above)
2. **Checks consistency** ("Are there any contradictions?")
3. **Infers** new facts ("If Alice is a Teacher, then Alice is a Person")
4. **Answers queries** ("Who are all the Teachers?")

## Why Reasoning Matters

Without reasoning:
```
Database result for "Who is a Person?"
- John (records say he's a Student)
- Alice (records say she's a Teacher)
```

With reasoning:
```
Reasoner result for "Who is a Person?"
- John (is a Student, therefore a Person)
- Alice (is a Teacher, therefore a Person)
- Bob (is explicitly a Person)
```

The reasoner automatically infers that Students and Teachers are Persons based on the rules.

## The "DL" in "OWL 2 DL"

OWL = Web Ontology Language (W3C standard for ontologies)

DL = Description Logic (mathematical foundation)

DL is a **subset** of first-order logic chosen to be:
- **Decidable** (you always get an answer in finite time)
- **Tractable** (reasonable performance on realistic data)
- **Expressive** (powerful enough for most real-world needs)

## What PyHermit Does

PyHermit implements the **tableau algorithm**, a decision procedure for OWL 2 DL reasoning:

```
Input Ontology + Data
        ↓
Normalization (convert to standard form)
        ↓
Clausification (turn into logical clauses)
        ↓
Tableau Expansion (systematically explore possibilities)
        ↓
Model Found or Contradiction Detected
        ↓
Output: Consistent/Inconsistent, Facts, Hierarchies
```

## A Simple Example

Define the world:

```python
from hermit import Reasoner
from hermit.model import AtomicConcept, Individual
from hermit.owl_model.class_expression import OWLClass
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_axiom import OWLClassAssertionAxiom, OWLSubClassOfAxiom
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization

# Define classes (concepts)
NS = "http://example.org/"
Animal = OWLClass(NS + "Animal")
Dog = OWLClass(NS + "Dog")
Cat = OWLClass(NS + "Cat")

# Define data (an individual)
fido = OWLNamedIndividual(NS + "fido")

# Collect rules and facts as axioms
axioms = [
    OWLSubClassOfAxiom(Dog, Animal),       # "Dogs are Animals"
    OWLSubClassOfAxiom(Cat, Animal),       # "Cats are Animals"
    OWLClassAssertionAxiom(fido, Dog),     # "Fido is a Dog"
]

# Compile and reason
normalized = OWLNormalization().process_ontology(axioms)
dl_ontology = OWLClausification().clausify(normalized)
reasoner = Reasoner(dl_ontology)
reasoner.precompute_inferences()

# Query with hermit.model handles
animal = AtomicConcept.create(NS + "Animal")
dog = AtomicConcept.create(NS + "Dog")
fido_h = Individual.create(NS + "fido")

print(reasoner.has_type(fido_h, animal))  # True (inferred!)
print(reasoner.has_type(fido_h, dog))     # True (asserted)
print(reasoner.is_consistent())           # True (no contradictions)

reasoner.dispose()
```

Output:
```
True
True
True
```

The reasoner inferred that Fido is an Animal even though we only asserted that Fido is a Dog.

## Key Concepts You'll Encounter

### Classes
**What:** Categories or types (like database tables)

**Examples:** Person, Vehicle, Organization

**In code:**
```python
Person = OWLClass("http://example.org/Person")  # hermit.owl_model
```

### Properties
**What:** Relationships or attributes (like database columns)

**Examples:** hasName, hasAge, worksFor

**In code:**
```python
from hermit.owl_model.owl_property import OWLDataProperty, OWLObjectProperty

worksFor = OWLObjectProperty("http://example.org/worksFor")
hasAge = OWLDataProperty("http://example.org/hasAge")
```

### Individuals
**What:** Concrete instances (like database rows)

**Examples:** John (a specific person), Tesla Inc (a specific organization)

**In code:**
```python
john = OWLNamedIndividual("http://example.org/john")  # hermit.owl_model
```

### Axioms
**What:** Rules or statements (the building blocks of ontologies)

**Examples:**
- "Dogs are Animals"
- "Everyone has at least one Parent"
- "You cannot be both a Student and a Teacher"

**In code:**
```python
axioms.append(OWLSubClassOfAxiom(Dog, Animal))
```

### Hierarchy
**What:** The relationships between classes

**Example:**
```
Thing
  └─ Animal
     ├─ Dog
     ├─ Cat
     └─ Bird
```

## Consistency vs. Reasoning

**Consistency checking:** "Are there any logical contradictions?"

Bad ontology:
```python
from hermit.owl_model.class_expression import OWLObjectComplementOf

bad_axioms = [
    OWLSubClassOfAxiom(Dog, Animal),
    OWLSubClassOfAxiom(Dog, OWLObjectComplementOf(Animal)),  # Dog ⊑ ¬Animal: Dog is unsatisfiable
]
```

**Reasoning:** "What can we infer from the rules?"

Good ontology:
```python
good_axioms = [
    OWLSubClassOfAxiom(Dog, Animal),
    OWLClassAssertionAxiom(fido, Dog),
]
# The reasoner infers: fido is an Animal
```

## When to Use OWL Reasoning

✅ **Good use cases:**
- Knowledge graphs (DBpedia, Wikidata)
- Semantic interoperability (different systems sharing data)
- Complex business rules (insurance, healthcare)
- Linked data validation
- Inferring missing data

❌ **Bad use cases:**
- Simple key-value lookups (use a database)
- Real-time analytics on billions of facts (too slow)
- Unstructured text (use NLP instead)

## Next Steps

1. **Read [Your First Program](./first-program.md)** — Run code and see it in action
2. **Explore [Building Your First Ontology](./tutorials/01-build-ontology.md)** — Create real ontologies
3. **Check the [API Reference](./api/core.md)** — Understand all available tools

---

**Key Takeaway:** PyHermit turns structured data and rules into a reasoning engine that automatically infers new facts and checks for contradictions.
