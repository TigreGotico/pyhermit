# Ontology Debugging Guide

How to find and fix issues in your ontologies.

All snippets use the standard setup:

```python
from hermit import Reasoner
from hermit.model import AtomicConcept, AtomicRole, Individual
from hermit.owl_model.class_expression import OWLClass, OWLObjectComplementOf, OWLObjectSomeValuesFrom
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_property import OWLObjectProperty
from hermit.owl_model.owl_axiom import (
    OWLClassAssertionAxiom,
    OWLDisjointClassesAxiom,
    OWLEquivalentClassesAxiom,
    OWLObjectPropertyAssertionAxiom,
    OWLSubClassOfAxiom,
)
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization


def reasoner_from_axioms(axioms, ontology_iri="urn:example:onto"):
    normalized = OWLNormalization().process_ontology(axioms)
    return Reasoner(OWLClausification().clausify(normalized, ontology_iri=ontology_iri))


NS = "http://example.org/"
```

## Problem 1: Unexpected Query Results

### Symptom: Getting fewer instances than expected

```python
Person = OWLClass(NS + "Person")
Employee = OWLClass(NS + "Employee")
alice = OWLNamedIndividual(NS + "alice")

# alice asserted as Employee, but no rule connects Employee to Person
axioms = [OWLClassAssertionAxiom(alice, Employee)]

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

person = AtomicConcept.create(NS + "Person")
instances = reasoner.get_instances(person)
print(f"Persons found: {len(instances)}")  # 0 — why?
reasoner.dispose()
```

### Diagnosis

**Step 1: Check if the class is satisfiable**

```python
reasoner = reasoner_from_axioms(axioms)
if not reasoner.is_satisfiable(person):
    print("ERROR: Person is unsatisfiable (contradictory definition)")
else:
    print("Person is satisfiable — the problem is elsewhere")
reasoner.dispose()
```

**Step 2: Compare direct and inferred instances**

```python
reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

employee = AtomicConcept.create(NS + "Employee")
direct = reasoner.get_instances(employee, direct=True)
all_instances = reasoner.get_instances(employee)
print(f"Direct: {len(direct)}, All: {len(all_instances)}")
reasoner.dispose()
```

**Step 3: Check the inference rules**

```python
# The missing link: nothing says Employee ⊑ Person.
# Fix it:
axioms.append(OWLSubClassOfAxiom(Employee, Person))

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()
print(f"Persons found now: {len(reasoner.get_instances(person))}")  # 1 (alice)
reasoner.dispose()
```

### Solution Checklist

- [ ] Class is satisfiable (`is_satisfiable` returns `True`)
- [ ] Instances are asserted with `OWLClassAssertionAxiom`
- [ ] Inference rules exist (`OWLSubClassOfAxiom` connecting to the queried class)
- [ ] `precompute_inferences()` was called before instance queries

---

## Problem 2: Ontology Inconsistency

### Symptom: `is_consistent()` returns False

**Step 1: Find unsatisfiable classes**

An inconsistent ontology answers every entailment with "true", so first find
classes that are unsatisfiable on their own:

```python
Student = OWLClass(NS + "Student")
Teacher = OWLClass(NS + "Teacher")
TeachingStudent = OWLClass(NS + "TeachingStudent")

axioms = [
    OWLDisjointClassesAxiom([Student, Teacher]),
    OWLSubClassOfAxiom(TeachingStudent, Student),
    OWLSubClassOfAxiom(TeachingStudent, Teacher),
]

reasoner = reasoner_from_axioms(axioms)
print("Consistent?", reasoner.is_consistent())  # True — no individuals yet

unsatisfiable = [
    ac.iri for ac in reasoner.dl_ontology.all_atomic_concepts
    if not reasoner.is_satisfiable(ac)
]
print(f"Unsatisfiable classes: {unsatisfiable}")  # TeachingStudent
reasoner.dispose()
```

**Step 2: Check disjointness violations**

```python
# Asserting an individual into an unsatisfiable class
# makes the whole ontology inconsistent:
alice = OWLNamedIndividual(NS + "alice")
bad = axioms + [
    OWLClassAssertionAxiom(alice, Student),
    OWLClassAssertionAxiom(alice, Teacher),  # alice can't be both!
]

reasoner = reasoner_from_axioms(bad)
print("Consistent?", reasoner.is_consistent())  # False
reasoner.dispose()

# Fix: decide whether the disjointness or the assertion is wrong,
# and rebuild the axiom list without the offending axiom.
```

**Step 3: Check circular negations**

```python
A = OWLClass(NS + "A")
B = OWLClass(NS + "B")

circular = [
    OWLSubClassOfAxiom(A, B),
    OWLSubClassOfAxiom(B, OWLObjectComplementOf(A)),  # B ⊑ ¬A
]
# This means: A ⊑ B ⊑ ¬A → A is unsatisfiable

reasoner = reasoner_from_axioms(circular)
print("A satisfiable?", reasoner.is_satisfiable(AtomicConcept.create(NS + "A")))  # False
reasoner.dispose()
```

**Step 4: Check cardinality conflicts**

```python
from hermit.owl_model.class_expression import (
    OWLObjectMaxCardinality, OWLObjectMinCardinality, OWLThing,
)

hasParent = OWLObjectProperty(NS + "hasParent")
Person = OWLClass(NS + "Person")

conflicting = [
    OWLSubClassOfAxiom(Person, OWLObjectMinCardinality(2, hasParent, OWLThing)),
    OWLSubClassOfAxiom(Person, OWLObjectMaxCardinality(1, hasParent, OWLThing)),
]
# Person must have ≥2 but ≤1 parents → Person is unsatisfiable

reasoner = reasoner_from_axioms(conflicting)
print("Person satisfiable?", reasoner.is_satisfiable(AtomicConcept.create(NS + "Person")))  # False
reasoner.dispose()
```

### Solution Checklist

- [ ] No unsatisfiable classes
- [ ] No disjoint classes with shared instances
- [ ] No circular negations
- [ ] Cardinality constraints don't conflict

---

## Problem 3: Slow Reasoning

### Symptom: `precompute_inferences()` takes too long

```python
import time

reasoner = reasoner_from_axioms(axioms)
start = time.time()
reasoner.precompute_inferences()
elapsed = time.time() - start
print(f"Reasoning took {elapsed:.1f} seconds")
reasoner.dispose()
```

### Diagnosis

**Step 1: Check ontology size**

```python
reasoner = reasoner_from_axioms(axioms)
print(reasoner.stats)  # clauses, atomic_concepts, individuals, is_horn, ...
reasoner.dispose()
```

Horn ontologies (`is_horn: True`) classify much faster — disjunctions
(unions, max-cardinality on the right of ⊑) trigger backtracking search.

**Step 2: Check for expensive constructs**

The usual suspects, in rough order of cost:

- large max-cardinality values in restrictions
- deeply nested disjunctions
- transitive properties combined with deep existential chains
- many `OWLDifferentIndividualsAxiom` pairs with max-cardinality constraints

**Step 3: Time individual queries**

```python
reasoner = reasoner_from_axioms(axioms)
start = time.time()
reasoner.is_consistent()
print(f"Consistency check: {time.time() - start:.3f}s")
reasoner.dispose()
```

### Solution Strategies

- Simplify or remove axioms you don't query
- For one-off checks, skip `precompute_inferences()` and ask directly
- Set `Configuration.individual_task_timeout` to bound each reasoning task:

```python
from hermit import Configuration

config = Configuration()
config.individual_task_timeout = 30_000  # milliseconds per reasoning task

normalized = OWLNormalization().process_ontology(axioms)
dl_onto = OWLClausification().clausify(normalized)
reasoner = Reasoner(dl_onto, config)
print(reasoner.is_consistent())
reasoner.dispose()
```

---

## Problem 4: Wrong Inference

### Symptom: Something that should be inferred isn't, or vice versa

**Step 1: Check the axiom exists**

```python
Dog = OWLClass(NS + "Dog")
Animal = OWLClass(NS + "Animal")

# WRONG: forgot to add the axiom
axioms = []

# Verify what you actually collected:
expected = OWLSubClassOfAxiom(Dog, Animal)
print("Axiom present?", expected in axioms)  # False — there's the bug

axioms.append(expected)
print("Axiom present now?", expected in axioms)  # True
```

(Axiom objects compare by value, so `in` works.)

**Step 2: Check for typos in IRIs**

```python
axioms = [OWLSubClassOfAxiom(Dog, Animal)]
reasoner = reasoner_from_axioms(axioms)

# Typo in the query handle: different IRI = different class!
dog_wrong = AtomicConcept.create(NS + "Doog")
dog_right = AtomicConcept.create(NS + "Dog")
animal_h = AtomicConcept.create(NS + "Animal")

print(reasoner.is_sub_class_of(dog_wrong, animal_h))  # False (typo)
print(reasoner.is_sub_class_of(dog_right, animal_h))  # True
reasoner.dispose()
```

**Step 3: Check the inference path**

```python
Mammal = OWLClass(NS + "Mammal")
Poodle = OWLClass(NS + "Poodle")

axioms = [
    OWLSubClassOfAxiom(Poodle, Dog),
    OWLSubClassOfAxiom(Dog, Mammal),
    OWLSubClassOfAxiom(Mammal, Animal),
]
reasoner = reasoner_from_axioms(axioms)

poodle = AtomicConcept.create(NS + "Poodle")
mammal = AtomicConcept.create(NS + "Mammal")

# Debug each link in the chain:
print(f"Poodle ⊑ Dog? {reasoner.is_sub_class_of(poodle, dog_right)}")
print(f"Dog ⊑ Mammal? {reasoner.is_sub_class_of(dog_right, mammal)}")
print(f"Mammal ⊑ Animal? {reasoner.is_sub_class_of(mammal, animal_h)}")
print(f"Poodle ⊑ Animal? {reasoner.is_sub_class_of(poodle, animal_h)}")
reasoner.dispose()

# If the chain is broken, the first False shows the missing axiom
```

**Step 4: Check for contradicting rules**

```python
contradictory = [
    OWLSubClassOfAxiom(Dog, Animal),          # Dog ⊑ Animal
    OWLDisjointClassesAxiom([Dog, Animal]),   # Dog ⊓ Animal = ∅
]

reasoner = reasoner_from_axioms(contradictory)
# Together these make Dog unsatisfiable:
print("Dog satisfiable?", reasoner.is_satisfiable(dog_right))  # False
reasoner.dispose()
```

### Solution Checklist

- [ ] Axiom is actually in the axiom list
- [ ] IRI spelling is consistent between building and querying
- [ ] No contradicting rules
- [ ] Inference chain is complete
- [ ] A fresh reasoner was compiled after changes

---

## Debugging Tools

### Tool 1: Print the Inferred Hierarchy

```python
import sys

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()
reasoner.dump_hierarchies(sys.stdout, classes=True)
reasoner.dispose()
```

### Tool 2: Inspect the Compiled Ontology

```python
reasoner = reasoner_from_axioms(axioms)
print(reasoner.stats)
for clause in sorted(str(c) for c in reasoner.dl_ontology.dl_clauses):
    print(clause)
reasoner.dispose()
```

### Tool 3: Trace Subsumption

```python
def trace_subclass_path(reasoner, sub_iri, sup_iri):
    """Report whether sub ⊑ sup holds."""
    sub = AtomicConcept.create(sub_iri)
    sup = AtomicConcept.create(sup_iri)
    if reasoner.is_sub_class_of(sub, sup):
        print(f"✓ {sub_iri} ⊑ {sup_iri} (verified)")
        return True
    print(f"✗ {sub_iri} ⊄ {sup_iri} (not inferred)")
    return False


reasoner = reasoner_from_axioms(axioms)
trace_subclass_path(reasoner, NS + "Poodle", NS + "Animal")
reasoner.dispose()
```

---

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Forgot axiom | Query returns False | Append the axiom and recompile |
| Typo in IRI | Different classes treated | Use shared `NS` constants |
| Circular negation | Unsatisfiable class | Remove contradicting rules |
| Mixed IRI formats | Different classes | Standardize IRI prefixes |
| Querying a disposed reasoner | `RuntimeError` | Compile a fresh reasoner |
| Subclass instead of equivalence | Defined class never recognizes members | Use `OWLEquivalentClassesAxiom` |

---

**See Also:**
- **[FAQ](../faq.md)** — Quick answers
- **[Patterns](./patterns.md)** — Design patterns
- **[Concepts](../concepts.md)** — How reasoning works
