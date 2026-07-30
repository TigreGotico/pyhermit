# Your First PyHermit Program

A step-by-step walkthrough of your first reasoner program, with an explanation at each step.

## The two halves of the API

PyHermit splits work between two layers.

1. Build an ontology. Create OWL entities and axioms with the `hermit.owl_model` classes (the same shapes as the OWL API). Then compile them into a reasoner through normalization and clausification.
2. Querying the reasoner: `Reasoner` methods take lightweight handles from `hermit.model`, such as `AtomicConcept.create(iri)`, `Individual.create(iri)`, and `AtomicRole.create(iri)`.

Every program in these docs uses the same small helper to compile axioms into a `Reasoner`.

```python
from hermit import Reasoner
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization


def reasoner_from_axioms(axioms, ontology_iri="urn:example:onto"):
    """Compile OWL axioms into a Reasoner (normalize -> clausify)."""
    normalized = OWLNormalization().process_ontology(axioms)
    dl_ontology = OWLClausification().clausify(normalized, ontology_iri=ontology_iri)
    return Reasoner(dl_ontology)
```

## The program

```python
from hermit.model import AtomicConcept, AtomicRole, Individual
from hermit.owl_model.class_expression import OWLClass
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_property import OWLObjectProperty
from hermit.owl_model.owl_axiom import (
    OWLClassAssertionAxiom,
    OWLObjectPropertyAssertionAxiom,
    OWLSubClassOfAxiom,
)

# Step 1: Define classes (concepts)
NS = "http://example.org/"
Animal = OWLClass(NS + "Animal")
Dog = OWLClass(NS + "Dog")
Cat = OWLClass(NS + "Cat")
Person = OWLClass(NS + "Person")

# Step 2: Define properties (relationships)
hasOwner = OWLObjectProperty(NS + "hasOwner")

# Step 3: Define individuals (the data)
fido = OWLNamedIndividual(NS + "fido")
john = OWLNamedIndividual(NS + "john")

# Step 4: Collect the axioms (rules first, then facts)
axioms = [
    # Rules: dogs and cats are animals
    OWLSubClassOfAxiom(Dog, Animal),
    OWLSubClassOfAxiom(Cat, Animal),
    # Facts: Fido is a dog owned by John, who is a person
    OWLClassAssertionAxiom(fido, Dog),
    OWLClassAssertionAxiom(john, Person),
    OWLObjectPropertyAssertionAxiom(fido, hasOwner, john),
]

# Step 5: Compile the axioms into a reasoner
reasoner = reasoner_from_axioms(axioms, ontology_iri="urn:example:pets")
reasoner.precompute_inferences()

# Step 6: Query the reasoner (queries use hermit.model handles)
animal = AtomicConcept.create(NS + "Animal")
dog = AtomicConcept.create(NS + "Dog")
cat = AtomicConcept.create(NS + "Cat")
fido_h = Individual.create(NS + "fido")
john_h = Individual.create(NS + "john")
has_owner = AtomicRole.create(NS + "hasOwner")

print("=== Inference Results ===")

# Question 1: Is Fido an Animal?  (inferred, never asserted)
print(f"Is Fido an Animal? {reasoner.has_type(fido_h, animal)}")

# Question 2: Is Fido a Dog?  (asserted)
print(f"Is Fido a Dog? {reasoner.has_type(fido_h, dog)}")

# Question 3: Is the ontology consistent?
print(f"Is the ontology consistent? {reasoner.is_consistent()}")

# Question 4: Does Fido have an owner?
print(f"Is John Fido's owner? {reasoner.has_role_relationship(fido_h, has_owner, john_h)}")

# Question 5: Subsumption (is Dog a kind of Animal?)
print(f"Is Dog a subclass of Animal? {reasoner.is_sub_class_of(dog, animal)}")

# Step 7: Clean up
reasoner.dispose()
```

## Understanding the output

Run this program.

```bash
python first_program.py
```

You should see:

```
=== Inference Results ===
Is Fido an Animal? True
Is Fido a Dog? True
Is the ontology consistent? True
Is John Fido's owner? True
Is Dog a subclass of Animal? True
```

## What happened?

### The inference

You told PyHermit:
1. "Dogs are Animals" (`OWLSubClassOfAxiom(Dog, Animal)`).
2. "Fido is a Dog" (`OWLClassAssertionAxiom(fido, Dog)`).

PyHermit inferred: "Fido is an Animal." This fact was never stated explicitly.

This is reasoning in action. The reasoner applies the rule "Dogs are Animals" to the fact "Fido is a Dog" and concludes "Fido is an Animal."

### The pipeline

`reasoner_from_axioms` runs the same pipeline the file loader uses.

```
OWL axioms (hermit.owl_model)
    |
    v
OWLNormalization.process_ontology()   (negation normal form, fresh concepts)
    |
    v
OWLClausification.clausify()          (DL clauses, OWL 2 validity checks)
    |
    v
Reasoner(dl_ontology)                 (hypertableau reasoning)
```

## Step-by-step breakdown

### Step 1: Define classes

```python
Animal = OWLClass("http://example.org/Animal")
Dog = OWLClass("http://example.org/Dog")
```

These calls create class objects. The IRI is just an identifier. It does not have to exist on the web.

### Step 2: Define properties

```python
hasOwner = OWLObjectProperty("http://example.org/hasOwner")
```

Properties represent relationships between individuals, not data values. Later, the program states "Fido hasOwner John."

### Steps 3-4: Collect axioms

```python
axioms = [
    OWLSubClassOfAxiom(Dog, Animal),
    OWLClassAssertionAxiom(fido, Dog),
]
```

`OWLSubClassOfAxiom(Dog, Animal)` states a rule: "Every Dog is also an Animal." `OWLClassAssertionAxiom(fido, Dog)` states a fact: "Fido is a Dog." Note the argument order: the individual comes first in a class assertion, matching the OWL API.

### Step 5: Compile and precompute

```python
reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()
```

The reasoner compiles your axioms, then computes the class hierarchy up front. This can take time for large ontologies, so you only do it once.

### Step 6: Query with handles

```python
animal = AtomicConcept.create("http://example.org/Animal")
fido_h = Individual.create("http://example.org/fido")
reasoner.has_type(fido_h, animal)
```

Query methods take `hermit.model` handles, created from the same IRIs used when building the axioms. The handles are interned: calling `AtomicConcept.create` twice with the same IRI returns the same object.

### Step 7: Clean up

```python
reasoner.dispose()
```

This call releases resources. Always call it when you finish with a reasoner.

## Try this

Modify the program to ask more questions, before `dispose()`.

```python
reasoner = reasoner_from_axioms(axioms, ontology_iri="urn:example:pets")
reasoner.precompute_inferences()

# Get every animal in the ontology
animals = reasoner.get_instances(animal)
print(f"All animals: {sorted(i.iri for i in animals)}")

# Get all of Fido's types (including inferred ones)
types = reasoner.get_types(fido_h)
print(f"Fido's types: {sorted(c.iri for c in types)}")

# Check if Fido is a Cat
print(f"Is Fido a Cat? {reasoner.has_type(fido_h, cat)}")

reasoner.dispose()
```

## Key takeaways

1. Rules plus facts equal inferences. Define rules (subclass axioms, restrictions), add facts (assertions), and the reasoner finds new facts.
2. Consistency: if you add contradictory axioms, `is_consistent()` returns `False`.
3. Two layers: build with `hermit.owl_model` axioms, query with `hermit.model` handles.
4. Automatic: you do not write code to find inferences. The reasoner does it.

## Next steps

- [Building Your First Ontology](./tutorials/01-build-ontology.md) adds more classes and properties.
- [Restrictions & Cardinality](./tutorials/02-restrictions.md) covers cardinality and constraints.
- [Rules & Complex Queries](./tutorials/03-rules-and-queries.md) covers more complex ontology rules.

---
[← Concepts](concepts.md) · [Home](index.md) · [FAQ →](faq.md)
