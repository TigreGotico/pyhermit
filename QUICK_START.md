# PyHermit Quick Start

Get started with PyHermit in 5 minutes.

## Installation

```bash
pip install hermit-reasoner
```

The package installs as the `hermit` module — pure Python, no JVM.

## Your First Program (5 minutes)

PyHermit has two layers: **build** an ontology with `hermit.owl_model` axiom
objects (OWL-API-style), **query** with lightweight `hermit.model` handles.
A small helper compiles axioms into a `Reasoner`:

```python
from hermit import Reasoner
from hermit.model import AtomicConcept, Individual
from hermit.owl_model.class_expression import OWLClass
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_axiom import OWLClassAssertionAxiom, OWLSubClassOfAxiom
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization


def reasoner_from_axioms(axioms, ontology_iri="urn:example:onto"):
    """Compile OWL axioms into a Reasoner (normalize -> clausify)."""
    normalized = OWLNormalization().process_ontology(axioms)
    return Reasoner(OWLClausification().clausify(normalized, ontology_iri=ontology_iri))


NS = "http://example.org/"

# Step 1: Define classes
Dog = OWLClass(NS + "Dog")
Animal = OWLClass(NS + "Animal")

# Step 2: Define an individual
fido = OWLNamedIndividual(NS + "fido")

# Step 3: Collect rules and data as axioms
axioms = [
    OWLSubClassOfAxiom(Dog, Animal),       # Dogs are Animals
    OWLClassAssertionAxiom(fido, Dog),     # Fido is a Dog
]

# Step 4: Compile and reason
reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

# Step 5: Query with hermit.model handles
dog = AtomicConcept.create(NS + "Dog")
animal = AtomicConcept.create(NS + "Animal")
fido_h = Individual.create(NS + "fido")

print("Is Fido an Animal?", reasoner.has_type(fido_h, animal))  # True (inferred!)
print("Is Fido a Dog?", reasoner.has_type(fido_h, dog))         # True (asserted)

# Step 6: Clean up
reasoner.dispose()
```

**Output:**
```
Is Fido an Animal? True
Is Fido a Dog? True
```

## Common Tasks

### Task 1: Check Subclass Relationships

```python
reasoner = reasoner_from_axioms(axioms)
is_subclass = reasoner.is_sub_class_of(dog, animal)
print(f"Dog ⊑ Animal? {is_subclass}")  # True
```

### Task 2: Get All Instances of a Class

```python
animals = reasoner.get_instances(animal)
print(f"All animals: {sorted(i.iri for i in animals)}")
```

### Task 3: Add Relationships Between Individuals

```python
from hermit.model import AtomicRole
from hermit.owl_model.owl_property import OWLObjectProperty
from hermit.owl_model.owl_axiom import OWLObjectPropertyAssertionAxiom

reasoner.dispose()

hasOwner = OWLObjectProperty(NS + "hasOwner")
john = OWLNamedIndividual(NS + "john")

axioms.append(OWLObjectPropertyAssertionAxiom(fido, hasOwner, john))
reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

has_owner = AtomicRole.create(NS + "hasOwner")
john_h = Individual.create(NS + "john")
print("Is John Fido's owner?", reasoner.has_role_relationship(fido_h, has_owner, john_h))  # True
```

### Task 4: Check Consistency

```python
if reasoner.is_consistent():
    print("Ontology is consistent")
else:
    print("Ontology has contradictions!")
```

### Task 5: Add Constraints (At Least One)

```python
from hermit.owl_model.class_expression import OWLObjectMinCardinality

Parent = OWLClass(NS + "Parent")
Person = OWLClass(NS + "Person")
hasChild = OWLObjectProperty(NS + "hasChild")

# Parents must have at least one child
axioms.append(OWLSubClassOfAxiom(
    Parent,
    OWLObjectMinCardinality(1, hasChild, Person),
))

reasoner.dispose()
```

## Learning Paths

### Path 1: Beginner (30 minutes)
1. Read: [Concepts](./docs/concepts.md)
2. Read: [First Program](./docs/first-program.md)
3. Try: Modify the program above
4. Reference: [FAQ](./docs/faq.md)

### Path 2: Build an Ontology (1 hour)
1. Read: [What is an Ontology?](./docs/tutorials/00-ontologies.md)
2. Read: [Building Your First Ontology](./docs/tutorials/01-build-ontology.md)
3. Create: Your own 10-class ontology
4. Reference: [Patterns](./docs/recipes/patterns.md)

### Path 3: Add Data & Query (1-2 hours)
1. Previous path steps
2. Read: [Restrictions](./docs/tutorials/02-restrictions.md)
3. Read: [Instances](./docs/tutorials/03-instances.md)
4. Create: Ontology with 100+ instances and constraints
5. Reference: [FAQ](./docs/faq.md), [Debugging](./docs/recipes/debugging.md)

### Path 4: Going Deeper (2-4 hours)
1. All previous steps
2. Read: [Rules & Queries](./docs/tutorials/03-rules-and-queries.md)
3. Read: [Advanced Reasoning](./docs/tutorials/04-advanced-reasoning.md)
4. Reference: [API Reference](./docs/api/core.md)
5. Reference: [Debugging](./docs/recipes/debugging.md), [Patterns](./docs/recipes/patterns.md)

## Common Errors

### Error: `ImportError: cannot import name 'OWLClass' from 'hermit.model'`

Entity classes live in `hermit.owl_model`, not `hermit.model`:

```python
from hermit.owl_model.class_expression import OWLClass  # building
from hermit.model import AtomicConcept                  # querying
```

### Error: `RuntimeError: Tableau has been disposed.`

You queried a reasoner after calling `dispose()`. Create a fresh reasoner
with `reasoner_from_axioms(axioms)`.

### Error: Query returns empty set when expecting results

Check:
```python
reasoner = reasoner_from_axioms(axioms)

# 1. Is the class satisfiable?
parent = AtomicConcept.create(NS + "Parent")
if not reasoner.is_satisfiable(parent):
    print("Class is unsatisfiable!")

# 2. Do instances exist in the ontology?
reasoner.precompute_inferences()  # Make sure this was called
instances = reasoner.get_instances(animal)
print(f"Found {len(instances)} instances")

# 3. Direct vs inferred instances
direct_instances = reasoner.get_instances(animal, direct=True)
print(f"Direct: {len(direct_instances)}, All: {len(instances)}")

reasoner.dispose()
```

See [Debugging Guide](./docs/recipes/debugging.md) for more.

## Next Steps

| Goal | Resource |
|------|----------|
| Learn fundamentals | [Concepts](./docs/concepts.md) |
| Build ontology | [Tutorial 1](./docs/tutorials/01-build-ontology.md) |
| Add constraints | [Tutorial 2](./docs/tutorials/02-restrictions.md) |
| Add data | [Tutorial 3](./docs/tutorials/03-instances.md) |
| Write rules | [Rules & Queries](./docs/tutorials/03-rules-and-queries.md) |
| Optimize | [Advanced Reasoning](./docs/tutorials/04-advanced-reasoning.md) |
| Find patterns | [Patterns](./docs/recipes/patterns.md) |
| Debug issues | [Debugging](./docs/recipes/debugging.md) |
| Look up API | [Core API](./docs/api/core.md) |
| Quick answers | [FAQ](./docs/faq.md) |

## Full Documentation

📖 **[Main Documentation Index](./docs/index.md)** — All docs organized by topic

## Getting Help

1. **Check [FAQ](./docs/faq.md)** — Answers to common questions
2. **Read [Debugging Guide](./docs/recipes/debugging.md)** — How to find issues
3. **Browse [Patterns](./docs/recipes/patterns.md)** — Common design solutions
4. **Review [API Reference](./docs/api/core.md)** — Complete API docs

## License

LGPL-3.0-or-later, matching upstream HermiT.

---

**Ready?** Start with [Concepts](./docs/concepts.md) or pick a [Learning Path](#learning-paths)!
