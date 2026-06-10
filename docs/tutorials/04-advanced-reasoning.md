# Tutorial 4: Advanced Reasoning Strategies

Learn about optimization, performance tuning, and advanced reasoning techniques.

## What You'll Learn

- When to precompute inferences
- TBox vs ABox reasoning
- Property characteristics (inverse, transitive, symmetric)
- Handling large ontologies
- Performance profiling

Standard setup:

```python
from hermit import Reasoner
from hermit.model import AtomicConcept, Individual
from hermit.owl_model.class_expression import (
    OWLClass, OWLObjectIntersectionOf, OWLObjectSomeValuesFrom, OWLThing,
)
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_property import OWLObjectProperty
from hermit.owl_model.owl_axiom import (
    OWLClassAssertionAxiom,
    OWLDisjointClassesAxiom,
    OWLEquivalentClassesAxiom,
    OWLInverseObjectPropertiesAxiom,
    OWLObjectPropertyAssertionAxiom,
    OWLSubClassOfAxiom,
    OWLTransitiveObjectPropertyAxiom,
)
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization


def reasoner_from_axioms(axioms, ontology_iri="urn:example:onto"):
    normalized = OWLNormalization().process_ontology(axioms)
    return Reasoner(OWLClausification().clausify(normalized, ontology_iri=ontology_iri))


NS = "http://example.org/"
```

## Part 1: Precompute vs On-Demand Reasoning

`Reasoner` answers queries either way; `precompute_inferences()` classifies
everything up front so subsequent queries hit a cached hierarchy:

```python
Animal = OWLClass(NS + "Animal")
Dog = OWLClass(NS + "Dog")
Cat = OWLClass(NS + "Cat")

axioms = [
    OWLSubClassOfAxiom(Dog, Animal),
    OWLSubClassOfAxiom(Cat, Animal),
]

dog = AtomicConcept.create(NS + "Dog")
cat = AtomicConcept.create(NS + "Cat")
animal = AtomicConcept.create(NS + "Animal")

# Mode 1: Precompute (recommended for repeated queries)
print("=== Precompute Mode ===")
reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()           # does all classification upfront
print("Is Dog a subclass of Animal?", reasoner.is_sub_class_of(dog, animal))
print("Is Cat a subclass of Animal?", reasoner.is_sub_class_of(cat, animal))
reasoner.dispose()

# Mode 2: On-demand (good for one-off queries)
print("\n=== On-Demand Mode ===")
reasoner2 = reasoner_from_axioms(axioms)
# No precompute_inferences() — the subsumption test runs on demand
print("Is Dog a subclass of Animal?", reasoner2.is_sub_class_of(dog, animal))
reasoner2.dispose()
```

### When to Use Each Mode

| Mode | Best For | Trade-offs |
|------|----------|-----------|
| Precompute | Multiple queries, instance retrieval, hierarchies | Slower startup |
| On-Demand | A single satisfiability or subsumption test | Each query may trigger tableau work |

`precompute_inferences` takes keyword flags for what to classify:

```python
reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences(
    class_hierarchy=True,
    object_property_hierarchy=False,
    data_property_hierarchy=False,
)
reasoner.dispose()
```

## Part 2: TBox vs ABox Reasoning

TBox (schema) reasoning vs ABox (data) reasoning:

```python
fido = OWLNamedIndividual(NS + "fido")

axioms = [
    # === TBox (Terminological): class definitions and rules ===
    OWLSubClassOfAxiom(Dog, Animal),
    # === ABox (Assertional): facts about individuals ===
    OWLClassAssertionAxiom(fido, Dog),
]

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

# TBox query: Is Dog a subclass of Animal?
print("TBox: Is Dog ⊑ Animal?", reasoner.is_sub_class_of(dog, animal))

# ABox query: Is fido an animal?
fido_h = Individual.create(NS + "fido")
print("ABox: Is fido an Animal?", reasoner.has_type(fido_h, animal))  # Inferred!

reasoner.dispose()
```

## Part 3: Consistency and Satisfiability

Important reasoning tasks:

```python
Person = OWLClass(NS + "Person")
Employee = OWLClass(NS + "Employee")
Unemployed = OWLClass(NS + "Unemployed")

# Task 1: Consistency — is the entire ontology contradiction-free?
axioms = [
    OWLSubClassOfAxiom(Employee, Person),
    OWLSubClassOfAxiom(Unemployed, Person),
    OWLDisjointClassesAxiom([Employee, Unemployed]),
]

reasoner = reasoner_from_axioms(axioms)
print("Is ontology consistent?", reasoner.is_consistent())  # True
reasoner.dispose()

# Task 2: Satisfiability — can a class have any instances?
Contradiction = OWLClass(NS + "Contradiction")
axioms.append(OWLSubClassOfAxiom(
    Contradiction,
    OWLObjectIntersectionOf([Employee, Unemployed]),  # Impossible!
))

reasoner2 = reasoner_from_axioms(axioms)
contradiction = AtomicConcept.create(NS + "Contradiction")
print("Is Contradiction satisfiable?", reasoner2.is_satisfiable(contradiction))  # False

# Task 3: Find all unsatisfiable classes
reasoner2.precompute_inferences()
unsatisfiable = [
    ac for ac in reasoner2.dl_ontology.all_atomic_concepts
    if not ac.iri.startswith("internal:") and not reasoner2.is_satisfiable(ac)
]
print(f"Unsatisfiable classes: {[c.iri for c in unsatisfiable]}")

reasoner2.dispose()
```

**Output:**
```
Is ontology consistent? True
Is Contradiction satisfiable? False
Unsatisfiable classes: ['http://example.org/Contradiction']
```

## Part 4: Property Characteristics

Property axioms feed class-level inference:

```python
hasChild = OWLObjectProperty(NS + "hasChild")
hasParent = OWLObjectProperty(NS + "hasParent")
manages = OWLObjectProperty(NS + "manages")

Child = OWLClass(NS + "Child")
alice = OWLNamedIndividual(NS + "alice")
bob = OWLNamedIndividual(NS + "bob")

# Inverse properties: hasChild(alice, bob) implies hasParent(bob, alice),
# so a class defined by hasParent recognizes bob:
axioms = [
    OWLInverseObjectPropertiesAxiom(hasChild, hasParent),
    OWLEquivalentClassesAxiom([Child, OWLObjectSomeValuesFrom(hasParent, OWLThing)]),
    OWLObjectPropertyAssertionAxiom(alice, hasChild, bob),
]

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()
child = AtomicConcept.create(NS + "Child")
print("Is bob a Child?", reasoner.has_type(Individual.create(NS + "bob"), child))  # True
reasoner.dispose()

# Transitivity at the TBox level: managers reach everyone below them
Mgr = OWLClass(NS + "Mgr")
Mid = OWLClass(NS + "Mid")
Eng = OWLClass(NS + "Eng")
ReachesEng = OWLClass(NS + "ReachesEng")

axioms = [
    OWLTransitiveObjectPropertyAxiom(manages),
    OWLSubClassOfAxiom(Mgr, OWLObjectSomeValuesFrom(manages, Mid)),
    OWLSubClassOfAxiom(Mid, OWLObjectSomeValuesFrom(manages, Eng)),
    OWLEquivalentClassesAxiom([ReachesEng, OWLObjectSomeValuesFrom(manages, Eng)]),
]

reasoner = reasoner_from_axioms(axioms)
mgr = AtomicConcept.create(NS + "Mgr")
reaches = AtomicConcept.create(NS + "ReachesEng")
print("Mgr ⊑ ReachesEng?", reasoner.is_sub_class_of(mgr, reaches))  # True (via transitivity)
reasoner.dispose()
```

**Output:**
```
Is bob a Child? True
Mgr ⊑ ReachesEng? True
```

Note: OWL 2 restricts where transitive (non-simple) properties may appear —
using one inside a cardinality restriction raises `ValueError` at
clausification time.

## Part 5: Handling Large Ontologies

```python
# Strategy 1: Batch your axioms, compile once
big_axioms = []
classes = [OWLClass(f"{NS}Class{i}") for i in range(200)]
for i in range(1, len(classes)):
    big_axioms.append(OWLSubClassOfAxiom(classes[i], classes[i // 2]))

reasoner = reasoner_from_axioms(big_axioms)
reasoner.precompute_inferences()

# Strategy 2: Query only the classes you need
c150 = AtomicConcept.create(f"{NS}Class150")
c0 = AtomicConcept.create(f"{NS}Class0")
print("Class150 ⊑ Class0?", reasoner.is_sub_class_of(c150, c0))

# Reasoner statistics
print(reasoner.stats)

reasoner.dispose()
```

When data changes, build a new axiom list and compile a fresh reasoner —
`Reasoner` instances are immutable snapshots of the ontology.

## Part 6: Performance Profiling

Understanding where time is spent:

```python
import time

axioms = []
classes = [OWLClass(f"{NS}Class{i}") for i in range(100)]
individuals = [OWLNamedIndividual(f"{NS}Ind{i}") for i in range(100)]

# Add hierarchy
for i in range(1, len(classes)):
    axioms.append(OWLSubClassOfAxiom(classes[i], classes[0]))

# Add facts
for i, ind in enumerate(individuals):
    axioms.append(OWLClassAssertionAxiom(ind, classes[i % len(classes)]))

# Measure compile time
start = time.time()
reasoner = reasoner_from_axioms(axioms)
print(f"Reasoner creation: {time.time() - start:.3f}s")

# Measure classification time
start = time.time()
reasoner.precompute_inferences()
print(f"precompute_inferences: {time.time() - start:.3f}s")

# Measure query time
c50 = AtomicConcept.create(f"{NS}Class50")
c0 = AtomicConcept.create(f"{NS}Class0")
start = time.time()
for _ in range(10):
    reasoner.is_sub_class_of(c50, c0)
print(f"Average query time: {(time.time() - start) / 10:.6f}s")

reasoner.dispose()
```

## Part 7: Error Handling

Clausification validates OWL 2 restrictions and raises `ValueError`; always
dispose reasoners when done:

```python
from hermit.owl_model.class_expression import OWLObjectMaxCardinality

axioms = [
    OWLTransitiveObjectPropertyAxiom(manages),
    # OWL 2 violation: non-simple property in a cardinality restriction
    OWLSubClassOfAxiom(Person, OWLObjectMaxCardinality(1, manages, OWLThing)),
]

try:
    reasoner = reasoner_from_axioms(axioms)
except ValueError as e:
    print(f"Rejected at clausification: {e}")
```

**Output:**
```
Rejected at clausification: Non-simple property '<http://example.org/manages>' or its inverse appears in a cardinality restriction (OWL 2 violation)
```

## Optimization Checklist

- ✅ Use `precompute_inferences()` for repeated queries
- ✅ Check `is_consistent()` first if unsure about the ontology
- ✅ Compile axioms once; treat reasoners as snapshots
- ✅ Profile before optimizing
- ✅ Dispose reasoners to free resources
- ✅ Avoid repeated reasoner creation for the same axiom set

## Key Takeaways

1. **Precompute** for repeated queries; on-demand for one-off checks
2. **TBox** reasons about classes, **ABox** about instances
3. **Consistency** checks the whole ontology, **satisfiability** checks one class
4. **Property characteristics** (inverse, transitive) drive classification
5. **Profiling** guides optimization efforts

## Try This!

Create a complex ontology with:
- 1000+ classes in a hierarchy
- 100+ individuals with properties
- Profile reasoning time
- Measure the effect of precomputing vs on-demand queries

## Next Steps

- **[API Reference](../api/core.md)** — Complete API documentation
- **[Concepts](../concepts.md)** — Deep dive into reasoning
- **[Patterns](../recipes/patterns.md)** — Real-world usage patterns
