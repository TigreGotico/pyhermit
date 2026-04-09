# Tutorial 4: Advanced Reasoning Strategies

Learn about optimization, performance tuning, and advanced reasoning techniques.

## What You'll Learn

- When to use precompute vs on-demand reasoning
- Understanding blocking strategies
- Optimizing large ontologies
- Reasoning over ABox (assertional facts)
- Performance profiling

## Part 1: Precompute vs On-Demand Reasoning

PyHermit offers two reasoning modes:

```python
from hermit import Reasoner
from hermit.model import DLOntology, OWLClass, SubClassOf

onto = DLOntology()

# Build a small ontology
Animal = OWLClass("http://example.org/Animal")
Dog = OWLClass("http://example.org/Dog")
Cat = OWLClass("http://example.org/Cat")

onto.add_axiom(SubClassOf(Dog, Animal))
onto.add_axiom(SubClassOf(Cat, Animal))

reasoner = Reasoner(onto)

# Mode 1: Precompute (Recommended for repeated queries)
print("=== Precompute Mode ===")
reasoner.precompute_inferences()  # Does all work upfront
print("Is Dog a subclass of Animal?", reasoner.is_subclass_of(Dog, Animal))  # Instant
print("Is Cat a subclass of Animal?", reasoner.is_subclass_of(Cat, Animal))  # Instant

reasoner.dispose()

# Mode 2: On-Demand (Good for one-off queries or memory constraints)
print("\n=== On-Demand Mode ===")
reasoner2 = Reasoner(onto)
# Don't call precompute_inferences()
# Instead, query directly
print("Is Dog a subclass of Animal?", reasoner2.is_subclass_of(Dog, Animal))  # Work on-demand

reasoner2.dispose()
```

### When to Use Each Mode

| Mode | Best For | Trade-offs |
|------|----------|-----------|
| Precompute | Multiple queries, cached results, class hierarchy | Slower startup, more memory |
| On-Demand | Single queries, memory-constrained, dynamic changes | Slower per-query |

## Part 2: TBox vs ABox Reasoning

TBox (schema) reasoning vs ABox (data) reasoning:

```python
from hermit.model import ClassAssertion, OWLNamedIndividual

onto = DLOntology()

# === TBox (Terminological) ===
# Class definitions and rules
Animal = OWLClass("http://example.org/Animal")
Dog = OWLClass("http://example.org/Dog")
onto.add_axiom(SubClassOf(Dog, Animal))

# === ABox (Assertional) ===
# Facts about individuals
fido = OWLNamedIndividual("http://example.org/fido")
onto.add_axiom(ClassAssertion(Dog, fido))

reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# TBox query: Is Dog a subclass of Animal?
print("TBox: Is Dog ⊆ Animal?", reasoner.is_subclass_of(Dog, Animal))

# ABox query: Is fido an animal?
print("ABox: Is fido an Animal?", reasoner.has_type(fido, Animal))  # Inferred!

reasoner.dispose()
```

## Part 3: Consistency and Satisfiability

Important reasoning tasks:

```python
from hermit.model import Intersection, DisjointClasses, ForAll

onto = DLOntology()

Person = OWLClass("http://example.org/Person")
Employee = OWLClass("http://example.org/Employee")
Unemployed = OWLClass("http://example.org/Unemployed")

# Task 1: Consistency Checking
# Is the entire ontology consistent?
onto.add_axiom(SubClassOf(Employee, Person))
onto.add_axiom(SubClassOf(Unemployed, Person))
onto.add_axiom(DisjointClasses(Employee, Unemployed))

reasoner = Reasoner(onto)
print("Is ontology consistent?", reasoner.is_consistent())  # True

# Task 2: Satisfiability Checking
# Can a class have any instances?
Contradiction = OWLClass("http://example.org/Contradiction")
onto.add_axiom(SubClassOf(
    Contradiction,
    Intersection(Employee, Unemployed)  # Impossible!
))

reasoner2 = Reasoner(onto)
print("Is Contradiction satisfiable?", reasoner2.is_satisfiable(Contradiction))  # False

# Task 3: Find Unsatisfiable Classes
unsatisfiable = reasoner2.get_unsatisfiable_classes()
print(f"Unsatisfiable classes: {len(unsatisfiable)}")

reasoner.dispose()
reasoner2.dispose()
```

## Part 4: Handling Large Ontologies

Strategies for scaling to large datasets:

```python
# Strategy 1: Incremental Reasoning
print("=== Incremental Reasoning ===")

onto = DLOntology()
reasoner = Reasoner(onto)

# Add and reason incrementally
Animal = OWLClass("http://example.org/Animal")
Dog = OWLClass("http://example.org/Dog")
onto.add_axiom(SubClassOf(Dog, Animal))

reasoner = Reasoner(onto)  # Re-create reasoner for new facts
reasoner.precompute_inferences()

# Add more facts
Cat = OWLClass("http://example.org/Cat")
onto.add_axiom(SubClassOf(Cat, Animal))

reasoner2 = Reasoner(onto)  # Re-create reasoner
reasoner2.precompute_inferences()

reasoner.dispose()
reasoner2.dispose()

# Strategy 2: Filtering by Relevant Classes
print("\n=== Filtering Large Results ===")

onto2 = DLOntology()
# ... build large ontology ...

reasoner3 = Reasoner(onto2)
reasoner3.precompute_inferences()

# Instead of getting ALL instances (might be millions)
# Only get instances of specific classes
important_class = OWLClass("http://example.org/ImportantClass")
instances = reasoner3.get_instances(important_class)
print(f"Instances of ImportantClass: {len(instances)}")

reasoner3.dispose()
```

## Part 5: Reasoning About Properties

Advanced property reasoning:

```python
from hermit.model import InverseOf, Transitive, Symmetric

onto = DLOntology()

# Define properties with characteristics
hasParent = OWLObjectProperty("http://example.org/hasParent")
hasChild = OWLObjectProperty("http://example.org/hasChild")
hasFriend = OWLObjectProperty("http://example.org/hasFriend")
manages = OWLObjectProperty("http://example.org/manages")

Person = OWLClass("http://example.org/Person")

# Property 1: Inverse relationship
# hasChild is the inverse of hasParent
onto.add_axiom(InverseOf(hasParent, hasChild))

# Property 2: Transitivity
# If A manages B and B manages C, then A manages C
onto.add_axiom(Transitive(manages))

# Property 3: Symmetry
# If A is friends with B, then B is friends with A
onto.add_axiom(Symmetric(hasFriend))

# Now create facts
alice = OWLNamedIndividual("http://example.org/alice")
bob = OWLNamedIndividual("http://example.org/bob")
charlie = OWLNamedIndividual("http://example.org/charlie")

from hermit.model import ObjectPropertyAssertion
onto.add_axiom(ObjectPropertyAssertion(manages, alice, bob))
onto.add_axiom(ObjectPropertyAssertion(manages, bob, charlie))

reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Query: Does Alice manage Charlie (through transitivity)?
# This requires special reasoning over role chains
print("Alice manages Charlie:", 
      reasoner.get_object_property_values(manages, alice))

reasoner.dispose()
```

## Part 6: Performance Profiling

Understanding where time is spent:

```python
import time
from hermit import Reasoner
from hermit.model import (
    DLOntology, OWLClass, SubClassOf,
    ClassAssertion, OWLNamedIndividual
)

onto = DLOntology()

# Build a moderately complex ontology
classes = [OWLClass(f"http://example.org/Class{i}") for i in range(100)]
individuals = [OWLNamedIndividual(f"http://example.org/Ind{i}") for i in range(100)]

# Add hierarchy
for i in range(1, len(classes)):
    onto.add_axiom(SubClassOf(classes[i], classes[0]))

# Add facts
for i, ind in enumerate(individuals):
    onto.add_axiom(ClassAssertion(classes[i % len(classes)], ind))

# Measure precomputation time
start = time.time()
reasoner = Reasoner(onto)
onto_time = time.time() - start
print(f"Reasoner creation: {onto_time:.3f}s")

start = time.time()
reasoner.precompute_inferences()
reasoning_time = time.time() - start
print(f"Precompute_inferences: {reasoning_time:.3f}s")

# Measure query time
start = time.time()
for _ in range(10):
    reasoner.is_subclass_of(classes[50], classes[0])
query_time = (time.time() - start) / 10
print(f"Average query time: {query_time:.6f}s")

reasoner.dispose()
```

## Part 7: Error Handling

Graceful error handling:

```python
from hermit.datatypes.registry import UnsupportedDatatypeException

onto = DLOntology()

# ... build ontology ...

try:
    reasoner = Reasoner(onto)
    reasoner.precompute_inferences()
    
    # Queries
    result = reasoner.is_subclass_of(Class1, Class2)
    
except UnsupportedDatatypeException as e:
    print(f"Unsupported datatype: {e}")
    # Handle gracefully
except Exception as e:
    print(f"Reasoning failed: {e}")
finally:
    reasoner.dispose()
```

## Optimization Checklist

- ✅ Use precompute_inferences() for repeated queries
- ✅ Check is_consistent() first if unsure about ontology
- ✅ Use appropriate data structures (sets, hashmaps)
- ✅ Profile before optimizing
- ✅ Consider incremental reasoning for dynamic data
- ✅ Filter large result sets early
- ✅ Dispose reasoner to free memory
- ✅ Avoid repeated reasoner creation for same ontology

## Key Takeaways

1. **Precompute** for speed, **On-Demand** for memory
2. **TBox** reasons about classes, **ABox** about instances
3. **Consistency** checks whole ontology, **Satisfiability** checks classes
4. **Property characteristics** enable advanced reasoning
5. **Profiling** guides optimization efforts

## Try This!

Create a complex ontology with:
- 1000+ classes in a hierarchy
- 100+ individuals with properties
- Profile reasoning time
- Optimize by filtering results
- Measure performance improvement

## Next Steps

- **[API Reference](../api/core.md)** — Complete API documentation
- **[Concepts](../concepts.md)** — Deep dive into reasoning algorithms
- **[Examples](../examples.md)** — Real-world usage patterns
