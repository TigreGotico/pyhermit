# Core Concepts: From Zero to Understanding OWL Reasoning

Before you write code, this page explains what PyHermit does and why you might need it.

## The problem

You have structured data: information about people, organizations, products, and relationships. You want to:

- Ask questions: "Who are all the managers?"
- Find inconsistencies: "This person is both a student and a teacher in the same program."
- Infer new facts: "If John reports to Alice and Alice reports to Bob, who does John indirectly report to?"

Traditional databases store data well, but they do not reason about relationships or answer complex questions.

## The solution: ontologies and reasoning

An ontology is a formal description of concepts and their relationships.

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

A reasoner is a tool that:

1. Reads your ontology (the rules above).
2. Checks consistency: "Are there any contradictions?"
3. Infers new facts: "If Alice is a Teacher, then Alice is a Person."
4. Answers queries: "Who are all the Teachers?"

## Why reasoning matters

Without reasoning, a database only returns what it was told:

```
Database result for "Who is a Person?"
- John (records say he's a Student)
- Alice (records say she's a Teacher)
```

With reasoning, the same question also returns inferred facts:

```
Reasoner result for "Who is a Person?"
- John (is a Student, therefore a Person)
- Alice (is a Teacher, therefore a Person)
- Bob (is explicitly a Person)
```

The reasoner infers that Students and Teachers are Persons, based on the rules.

## The "DL" in "OWL 2 DL"

OWL means Web Ontology Language, the W3C standard for ontologies. DL means Description Logic, its mathematical foundation.

DL is a subset of first-order logic. The subset is decidable, so a query always returns an answer in finite time. It stays expressive enough for most real-world ontologies while keeping reasonable performance on realistic data.

## What PyHermit does

PyHermit implements the tableau algorithm, a decision procedure for OWL 2 DL reasoning.

```
Input Ontology + Data
        |
        v
Normalization (convert to standard form)
        |
        v
Clausification (turn into logical clauses)
        |
        v
Tableau Expansion (systematically explore possibilities)
        |
        v
Model Found or Contradiction Detected
        |
        v
Output: Consistent/Inconsistent, Facts, Hierarchies
```

## A simple example

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

The reasoner infers that Fido is an Animal, even though the axioms only assert that Fido is a Dog.

## Key concepts you will meet

### Classes

Classes are categories or types, like database tables. Examples: Person, Vehicle, Organization.

```python
Person = OWLClass("http://example.org/Person")  # hermit.owl_model
```

### Properties

Properties are relationships or attributes, like database columns. Examples: hasName, hasAge, worksFor.

```python
from hermit.owl_model.owl_property import OWLDataProperty, OWLObjectProperty

worksFor = OWLObjectProperty("http://example.org/worksFor")
hasAge = OWLDataProperty("http://example.org/hasAge")
```

### Individuals

Individuals are concrete instances, like database rows. Examples: John (a specific person), Tesla Inc (a specific organization).

```python
john = OWLNamedIndividual("http://example.org/john")  # hermit.owl_model
```

### Axioms

Axioms are rules or statements, the building blocks of ontologies. Examples:

- "Dogs are Animals."
- "Everyone has at least one Parent."
- "You cannot be both a Student and a Teacher."

```python
axioms.append(OWLSubClassOfAxiom(Dog, Animal))
```

### Hierarchy

A hierarchy is the set of relationships between classes.

```
Thing
  |- Animal
     |- Dog
     |- Cat
     |- Bird
```

## Consistency vs. reasoning

Consistency checking asks: "Are there any logical contradictions?"

```python
from hermit.owl_model.class_expression import OWLObjectComplementOf

bad_axioms = [
    OWLSubClassOfAxiom(Dog, Animal),
    OWLSubClassOfAxiom(Dog, OWLObjectComplementOf(Animal)),  # Dog is unsatisfiable
]
```

Reasoning asks: "What can we infer from the rules?"

```python
good_axioms = [
    OWLSubClassOfAxiom(Dog, Animal),
    OWLClassAssertionAxiom(fido, Dog),
]
# The reasoner infers: fido is an Animal
```

## When to use OWL reasoning

Good use cases:
- Knowledge graphs (DBpedia, Wikidata).
- Semantic interoperability between systems that share data.
- Complex business rules, for example in insurance or healthcare.
- Linked data validation.
- Inferring missing data.

Poor use cases:
- Simple key-value lookups. Use a database instead.
- Real-time analytics on billions of facts. This is too slow.
- Unstructured text. Use NLP instead.

## Next steps

1. Read [Your First Program](./first-program.md) to run code and see reasoning in action.
2. Explore [Building Your First Ontology](./tutorials/01-build-ontology.md) to create real ontologies.
3. Check the [API Reference](./api/core.md) for the full list of available tools.

---
[← Installation](installation.md) · [Home](index.md) · [First Program →](first-program.md)
