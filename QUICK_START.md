# PyHermit Quick Start

Get started with PyHermit in 5 minutes.

## Installation

```bash
pip install pyhermit
```

## Your First Program (5 minutes)

```python
from hermit import Reasoner
from hermit.model import (
    DLOntology, OWLClass, OWLNamedIndividual,
    SubClassOf, ClassAssertion
)

# Step 1: Create an ontology
onto = DLOntology()

# Step 2: Define classes
Dog = OWLClass("http://example.org/Dog")
Animal = OWLClass("http://example.org/Animal")

# Step 3: Add rules
onto.add_axiom(SubClassOf(Dog, Animal))  # Dogs are Animals

# Step 4: Add data
fido = OWLNamedIndividual("http://example.org/fido")
onto.add_axiom(ClassAssertion(Dog, fido))  # Fido is a Dog

# Step 5: Create reasoner and reason
reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Step 6: Query
print("Is Fido an Animal?", reasoner.has_type(fido, Animal))  # True (inferred!)
print("Is Fido a Dog?", reasoner.has_type(fido, Dog))  # True (asserted)

# Step 7: Clean up
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
is_subclass = reasoner.is_subclass_of(Dog, Animal)
print(f"Dog ⊆ Animal? {is_subclass}")
```

### Task 2: Get All Instances of a Class

```python
animals = reasoner.get_instances(Animal)
print(f"All animals: {animals}")
```

### Task 3: Add Relationships Between Individuals

```python
from hermit.model import OWLObjectProperty, ObjectPropertyAssertion

hasOwner = OWLObjectProperty("http://example.org/hasOwner")
john = OWLNamedIndividual("http://example.org/john")

onto.add_axiom(ObjectPropertyAssertion(hasOwner, fido, john))
reasoner = Reasoner(onto)
reasoner.precompute_inferences()

owners = reasoner.get_object_property_values(hasOwner, fido)
print(f"Fido's owner: {owners}")
```

### Task 4: Check Consistency

```python
is_consistent = reasoner.is_consistent()
if is_consistent:
    print("Ontology is consistent")
else:
    print("Ontology has contradictions!")
```

### Task 5: Add Constraints (At Least One)

```python
from hermit.model import AtLeast

# Parents must have at least one child
onto.add_axiom(SubClassOf(
    Parent,
    AtLeast(1, hasChild, Person)
))
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

### Path 4: Production System (2-4 hours)
1. All previous steps
2. Read: [Rules & Queries](./docs/tutorials/03-rules-and-queries.md)
3. Read: [Advanced Reasoning](./docs/tutorials/04-advanced-reasoning.md)
4. Reference: [API Reference](./docs/api/core.md)
5. Reference: [Debugging](./docs/recipes/debugging.md), [Patterns](./docs/recipes/patterns.md)

## Common Errors

### Error: `AttributeError: 'OWLClass' object has no attribute 'iri'`

You're using an old API. Use:
```python
# Current API
my_class = OWLClass("http://example.org/MyClass")
print(my_class)  # Prints IRI
```

### Error: `UnsupportedDatatypeException`

You used an unsupported datatype. Use only:
```python
from hermit.model import Literal

# Supported types
Literal("text", "string")
Literal(42, "integer")
Literal(3.14, "double")
Literal(True, "boolean")
Literal("2020-01-15", "date")
```

### Error: Query returns empty set when expecting results

Check:
```python
# 1. Is the class satisfiable?
if not reasoner.is_satisfiable(MyClass):
    print("Class is unsatisfiable!")

# 2. Do instances exist in ontology?
reasoner.precompute_inferences()  # Make sure this was called
instances = reasoner.get_instances(MyClass)
print(f"Found {len(instances)} instances")

# 3. Check assertions
direct_instances = reasoner.get_direct_instances(MyClass)
print(f"Direct: {len(direct_instances)}, All: {len(instances)}")
```

See [Debugging Guide](./docs/recipes/debugging.md) for more.

## Next Steps

| Goal | Resource |
|------|----------|
| Learn fundamentals | [Concepts](./docs/concepts.md) |
| Build ontology | [Tutorial 1](./docs/tutorials/01-build-ontology.md) |
| Add constraints | [Tutorial 2](./docs/tutorials/02-restrictions.md) |
| Add data | [Tutorial 3](./docs/tutorials/03-instances.md) |
| Write rules | [Tutorial 4](./docs/tutorials/03-rules-and-queries.md) |
| Optimize | [Tutorial 5](./docs/tutorials/04-advanced-reasoning.md) |
| Find patterns | [Patterns](./docs/recipes/patterns.md) |
| Debug issues | [Debugging](./docs/recipes/debugging.md) |
| Look up API | [Core API](./docs/api/core.md) |
| Quick answers | [FAQ](./docs/faq.md) |

## Full Documentation

📖 **[Main Documentation Index](./docs/index.md)** — All docs organized by topic

## Getting Help

1. **Check [FAQ](./docs/faq.md)** — Answers to 30+ common questions
2. **Read [Debugging Guide](./docs/recipes/debugging.md)** — How to find issues
3. **Browse [Patterns](./docs/recipes/patterns.md)** — Common design solutions
4. **Review [API Reference](./docs/api/core.md)** — Complete API docs

## License

Apache 2.0 — Free for commercial and private use.

---

**Ready?** Start with [Concepts](./docs/concepts.md) or pick a [Learning Path](#learning-paths)!
