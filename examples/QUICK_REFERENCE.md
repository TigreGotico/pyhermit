# PyHermit Quick Reference

## Essential Imports

```python
from hermit import Reasoner, load_ontology
from hermit.model import (
    DLOntology,
    Atom,
    AtomicConcept,
    AtomicRole,
    Variable,
    DLClause,
    Individual,
)
from hermit.configuration import Configuration, BlockingStrategyType
```

## Core Workflow

```python
# 1. Create or load ontology
ontology = DLOntology(
    ontology_iri="urn:example",
    dl_clauses=frozenset(clauses),
    positive_facts=frozenset(facts),
)

# 2. Create reasoner
reasoner = Reasoner(ontology)

# 3. Ask questions
is_consistent = reasoner.is_consistent()
subclasses = reasoner.get_sub_classes(my_class)

# 4. Clean up
reasoner.dispose()
```

## Creating Ontology Elements

### Variables
```python
X = Variable.create("X")
Y = Variable.create("Y")
```

### Concepts (Classes)
```python
person = AtomicConcept.create("http://example.org#Person")
dog = AtomicConcept.create("http://example.org#Dog")
```

### Roles (Properties)
```python
has_owner = AtomicRole.create("http://example.org#hasOwner")
is_parent_of = AtomicRole.create("http://example.org#isParentOf")
```

### Individuals
```python
alice = Individual.create("http://example.org#Alice")
fido = Individual.create("http://example.org#Fido")
```

## Building TBox Rules

### Simple Subsumption: A ⊑ B
```python
DLClause.create(
    (Atom.create(animal, X),),      # consequent (then)
    (Atom.create(dog, X),),         # antecedent (if)
)
# Means: if dog(X) then animal(X) = Dog ⊑ Animal
```

### Existential Restriction: A ⊓ ∃R.B ⊑ C
```python
DLClause.create(
    (Atom.create(has_owner, X, Y), Atom.create(person, Y)),  # then
    (Atom.create(dog, X),),                                   # if
)
# Means: if dog(X) then (∃Y: hasOwner(X,Y) ∧ person(Y))
```

## Adding ABox Facts

```python
facts = frozenset([
    Atom.create(person, alice),           # Alice is a person
    Atom.create(dog, fido),               # Fido is a dog
    Atom.create(has_owner, fido, alice),  # Fido's owner is Alice
])

ontology = DLOntology(
    ontology_iri="urn:example",
    dl_clauses=frozenset(clauses),
    positive_facts=facts,
)
```

## Query Cheat Sheet

### Consistency
```python
is_consistent = reasoner.is_consistent()
```

### Class Hierarchy
```python
reasoner.precompute_inferences(class_hierarchy=True)

# Subsumption
is_sub = reasoner.is_sub_class_of(dog, animal)
is_equiv = reasoner.is_equivalent(a, b)
is_disjoint = reasoner.is_disjoint(male, female)
is_satisfiable = reasoner.is_satisfiable(dog)
```

### Roles
```python
is_sub_role = reasoner.is_sub_role_of(child_role, parent_role)
is_equiv_role = reasoner.is_equivalent_role(role1, role2)
is_functional = reasoner.is_functional(has_heart)  # at most 1
```

### Instances & Types
```python
reasoner.precompute_inferences()

# Get all instances of a class
instances = reasoner.get_instances(person_class)

# Get all types of an individual
types = reasoner.get_types(alice)

# Check if individual has type
has_type = reasoner.has_type(alice, person)

# Check role relationships
has_rel = reasoner.has_role_relationship(fido, has_owner, alice)

# Check individual identity
is_same = reasoner.is_same_individual(alice, alice)
```

### Hierarchies
```python
reasoner.precompute_inferences(class_hierarchy=True)

class_hierarchy = reasoner.get_class_hierarchy()
for node in class_hierarchy:
    print(node)
```

## Configuration

```python
config = Configuration()

# Blocking strategy
config.blocking_strategy_type = BlockingStrategyType.ANCESTOR
# Options: ANCESTOR, PAIRWISE_DIRECT, ANYWHERE

# Timeout (milliseconds)
config.individual_task_timeout = 10000  # 10 seconds

# Create reasoner with config
reasoner = Reasoner(ontology, config)
```

## Common Patterns

### Check if ontology is consistent
```python
reasoner = Reasoner(ontology)
try:
    if reasoner.is_consistent():
        print("OK")
    else:
        print("CONTRADICTION FOUND")
finally:
    reasoner.dispose()
```

### Get all subclasses
```python
from hermit.owl_model.class_expression import OWLThing

reasoner.precompute_inferences(class_hierarchy=True)
all_classes = reasoner.get_sub_classes(OWLThing)
for cls in all_classes:
    print(cls.iri)
```

### Classify individuals
```python
reasoner.precompute_inferences()

for individual in ontology.all_individuals:
    types = reasoner.get_types(individual)
    print(f"{individual.iri}:")
    for t in types:
        print(f"  - {t.iri}")
```

### Check entailment (subsumption)
```python
reasoner = Reasoner(ontology)
if reasoner.is_sub_class_of(doctor, person):
    print("Doctor ⊑ Person is entailed")
reasoner.dispose()
```

### Find role relationships
```python
reasoner.precompute_inferences()

has_owner = AtomicRole.create("http://example.org#hasOwner")
if reasoner.has_role_relationship(fido, has_owner, alice):
    print("Fido's owner is Alice")
```

## Error Handling

```python
try:
    reasoner = Reasoner(ontology)
    result = reasoner.is_consistent()
    # ... queries ...
except TimeoutError:
    print("Reasoning timed out")
except Exception as e:
    print(f"Error: {e}")
finally:
    reasoner.dispose()
```

## Tips & Tricks

### Always dispose
```python
reasoner = Reasoner(ontology)
try:
    # ... use reasoner ...
finally:
    reasoner.dispose()  # IMPORTANT: releases resources
```

### Create fresh reasoner for each ontology
```python
# DON'T reuse:
ontology1 = ...
ontology2 = ...
reasoner = Reasoner(ontology1)
# reasoner.is_consistent()  # wrong ontology if you change it

# DO this:
reasoner1 = Reasoner(ontology1)
reasoner2 = Reasoner(ontology2)
# use them separately
```

### Precompute for multiple queries
```python
# Bad: recomputes for each query
reasoner.is_sub_class_of(A, B)
reasoner.is_sub_class_of(C, D)
reasoner.is_sub_class_of(E, F)

# Good: precompute once
reasoner.precompute_inferences(class_hierarchy=True)
reasoner.is_sub_class_of(A, B)
reasoner.is_sub_class_of(C, D)
reasoner.is_sub_class_of(E, F)
```

### Debug inconsistencies
```python
if not reasoner.is_consistent():
    # Find what's satisfiable and what's not
    for cls in ontology.all_classes:
        if not reasoner.is_satisfiable(cls):
            print(f"Unsatisfiable: {cls.iri}")
```

### Check DL expressivity needed
```python
ontology = DLOntology(...)

# Check if ontology uses specific features
has_inverse = ontology.has_inverse_roles()
has_nominals = ontology.has_nominals()
has_complex_roles = ontology.has_complex_roles()
```

## Performance Tuning

```python
# For large ontologies
config = Configuration()
config.blocking_strategy_type = BlockingStrategyType.ANCESTOR  # faster
config.individual_task_timeout = 30000  # 30 seconds

# For maximum correctness
config.blocking_strategy_type = BlockingStrategyType.PAIRWISE_DIRECT  # slower but complete
config.individual_task_timeout = 600000  # 10 minutes

reasoner = Reasoner(ontology, config)
```

## Loading Files

```python
from pathlib import Path

# Load OWL file
ontology = load_ontology(Path("ontology.owl"))
reasoner = Reasoner(ontology)
```

## Quick IRIs

Common base URIs:
```python
# Custom domain
base = "http://example.org"
dog = AtomicConcept.create(f"{base}#Dog")

# Standard namespaces
owl = "http://www.w3.org/2002/07/owl#"
rdf = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
rdfs = "http://www.w3.org/2000/01/rdf-schema#"
xsd = "http://www.w3.org/2001/XMLSchema#"
```

## One-Liners

```python
# Is A a subclass of B?
Reasoner(ontology).is_sub_class_of(A, B)

# Are A and B equivalent?
Reasoner(ontology).is_equivalent(A, B)

# Is the ontology consistent?
Reasoner(ontology).is_consistent()

# Get all instances of class C
Reasoner(ontology).precompute_inferences() or \
Reasoner(ontology).get_instances(C)
```

---

**For more details, see the full examples in the examples/ directory.**
