# Your First PyHermit Program

A step-by-step walkthrough of your first reasoner program, with explanations at each step.

## The Program

```python
from hermit import Reasoner
from hermit.model import (
    DLOntology, OWLClass, OWLObjectProperty,
    SubClassOf, ObjectPropertyAssertion, ClassAssertion,
    OWLNamedIndividual
)

# Step 1: Define classes (concepts)
Animal = OWLClass("http://example.org/Animal")
Dog = OWLClass("http://example.org/Dog")
Cat = OWLClass("http://example.org/Cat")
Person = OWLClass("http://example.org/Person")

# Step 2: Define properties (relationships)
hasOwner = OWLObjectProperty("http://example.org/hasOwner")
hasFriend = OWLObjectProperty("http://example.org/hasFriend")

# Step 3: Create ontology and add rules
ontology = DLOntology()

# Rule 1: Dogs are animals
ontology.add_axiom(SubClassOf(Dog, Animal))

# Rule 2: Cats are animals
ontology.add_axiom(SubClassOf(Cat, Animal))

# Rule 3: An owner of a dog must be a person
ontology.add_axiom(
    SubClassOf(
        OWLClass.create_from_iri("http://www.w3.org/2002/07/owl#Thing"),
        Person
    )
)

# Step 4: Add data (facts about individuals)
fido = OWLNamedIndividual("http://example.org/fido")
john = OWLNamedIndividual("http://example.org/john")

ontology.add_axiom(ClassAssertion(Dog, fido))       # Fido is a dog
ontology.add_axiom(ObjectPropertyAssertion(hasOwner, fido, john))  # Fido's owner is John

# Step 5: Create reasoner and run inference
reasoner = Reasoner(ontology)
reasoner.precompute_inferences()

# Step 6: Query the reasoner
print("=== Inference Results ===")

# Question 1: Is Fido an Animal?
is_animal = reasoner.has_type(fido, Animal)
print(f"Is Fido an Animal? {is_animal}")

# Question 2: Is Fido a Dog?
is_dog = reasoner.has_type(fido, Dog)
print(f"Is Fido a Dog? {is_dog}")

# Question 3: Is the ontology consistent?
is_consistent = reasoner.is_consistent()
print(f"Is the ontology consistent? {is_consistent}")

# Question 4: Get the class hierarchy
hierarchy = reasoner.get_class_hierarchy()
print(f"\nClass Hierarchy:")
for node in hierarchy:
    print(f"  {node}")

# Step 7: Clean up
reasoner.dispose()
```

## Understanding the Output

Run this program:

```bash
python first_program.py
```

You should see:

```
=== Inference Results ===
Is Fido an Animal? True
Is Fido a Dog? True
Is the ontology consistent? True

Class Hierarchy:
  owl:Thing
    └─ Animal
       ├─ Dog
       └─ Cat
    └─ Person
```

## What Happened?

### The Inference

You told PyHermit:
1. "Dogs are Animals" (SubClassOf(Dog, Animal))
2. "Fido is a Dog" (ClassAssertion(Dog, fido))

PyHermit inferred:
- "Fido is an Animal" ← This wasn't explicitly stated!

This is **reasoning in action**. The reasoner applied the rule "Dogs are Animals" to the fact "Fido is a Dog" and automatically concluded "Fido is an Animal".

### The Hierarchy

The reasoner also computed the class hierarchy, showing the relationships between classes:

```
owl:Thing (the top-level class, everything is a Thing)
├── Animal (subclass of Thing)
│   ├── Dog (subclass of Animal)
│   └── Cat (subclass of Animal)
└── Person (subclass of Thing)
```

## Step-by-Step Breakdown

### Step 1: Define Classes

```python
Animal = OWLClass("http://example.org/Animal")
Dog = OWLClass("http://example.org/Dog")
```

These create class objects. The URL is just an identifier (it doesn't have to exist on the web).

### Step 2: Define Properties

```python
hasOwner = OWLObjectProperty("http://example.org/hasOwner")
```

Properties represent relationships between things (not data values). Later, we'll say "Fido hasOwner John".

### Step 3: Create Ontology and Add Rules

```python
ontology = DLOntology()
ontology.add_axiom(SubClassOf(Dog, Animal))
```

`SubClassOf(Dog, Animal)` means "Every Dog is also an Animal". This is a rule the reasoner will use.

### Step 4: Add Facts

```python
ontology.add_axiom(ClassAssertion(Dog, fido))
```

`ClassAssertion(Dog, fido)` means "Fido is a Dog". This is a fact (a specific instance of a class).

```python
ontology.add_axiom(ObjectPropertyAssertion(hasOwner, fido, john))
```

`ObjectPropertyAssertion(hasOwner, fido, john)` means "Fido's owner is John".

### Step 5: Create Reasoner

```python
reasoner = Reasoner(ontology)
reasoner.precompute_inferences()
```

The reasoner reads your ontology and facts, then computes all possible inferences. This can take time for large ontologies, so you only do it once.

### Step 6: Query the Reasoner

```python
is_animal = reasoner.has_type(fido, Animal)
```

This asks "Is Fido an instance of the Animal class?" The reasoner will return `True` because it inferred that Fido is an Animal.

### Step 7: Clean Up

```python
reasoner.dispose()
```

This releases resources. Always do this when you're done.

## Try This!

Modify the program to ask more questions:

```python
# Does Fido have an owner?
owner = reasoner.get_object_property_values(hasOwner, fido)
print(f"Fido's owner: {owner}")

# Get all animals
animals = reasoner.get_instances(Animal)
print(f"All animals: {animals}")

# Check if Fido is a Cat
is_cat = reasoner.has_type(fido, Cat)
print(f"Is Fido a Cat? {is_cat}")
```

## Key Takeaways

1. **Rules + Facts = Inferences**: Define rules (classes, properties), add facts (instances), and the reasoner finds new facts.

2. **Consistent**: If you add contradictory rules, `is_consistent()` will return `False`.

3. **Automatic**: You don't write code to find inferences — the reasoner does it automatically.

4. **Type-Safe**: Fido is a Dog (you said so), and therefore an Animal (the reasoner inferred it).

## Next Steps

- **[Expand Your Ontology](./tutorials/02-build-ontology.md)** — Add more classes and properties
- **[Work with Restrictions](./tutorials/05-restrictions.md)** — Learn about cardinality and constraints
- **[Use Rules and Queries](./tutorials/06-rules.md)** — Make ontologies more powerful

---

**Congratulations!** You've written your first PyHermit program and seen reasoning in action.
