# Ontology Debugging Guide

How to find and fix issues in your ontologies.

## Problem 1: Unexpected Query Results

### Symptom: Getting fewer instances than expected

```python
# Expected: 100 instances
# Got: 0 instances
instances = reasoner.get_instances(MyClass)
```

### Diagnosis

**Step 1: Check if class is satisfiable**

```python
is_satisfiable = reasoner.is_satisfiable(MyClass)
if not is_satisfiable:
    print("ERROR: MyClass is unsatisfiable (contradictory)")
    # Find what makes it unsatisfiable
    unsatisfiable = reasoner.get_unsatisfiable_classes()
    print(f"Unsatisfiable classes: {unsatisfiable}")
```

**Step 2: Check direct instances**

```python
direct = reasoner.get_direct_instances(MyClass)
print(f"Direct instances: {len(direct)}")

all_instances = reasoner.get_instances(MyClass)
print(f"All instances (including inferred): {len(all_instances)}")

if len(direct) > 0 and len(all_instances) == 0:
    print("ERROR: Direct instances exist but none inferred")
    # The class definition might be broken
```

**Step 3: Check assertions**

```python
# Did you actually assert that individuals are of this type?
onto = DLOntology()

# Create an individual
alice = OWLNamedIndividual("http://example.org/alice")

# WRONG: Just asserting Person doesn't automatically put alice in MyClass
onto.add_axiom(ClassAssertion(Person, alice))

# RIGHT: You need to either:
# Option 1: Directly assert alice is MyClass
onto.add_axiom(ClassAssertion(MyClass, alice))

# Option 2: Or assert a subclass
onto.add_axiom(SubClassOf(Alice, MyClass))  # Alice class, not individual
onto.add_axiom(ClassAssertion(Alice, alice))
```

**Step 4: Check inference rules**

```python
# Maybe there's no rule connecting the data to your class?

# You have:
onto.add_axiom(ClassAssertion(Employee, alice))

# But you query:
instances = reasoner.get_instances(Person)  # Empty!

# Because there's no rule:
# Missing: onto.add_axiom(SubClassOf(Employee, Person))

# Fix it:
onto.add_axiom(SubClassOf(Employee, Person))
reasoner = Reasoner(onto)
reasoner.precompute_inferences()

instances = reasoner.get_instances(Person)  # Now contains alice
```

### Solution Checklist

- [ ] Class is satisfiable (`is_satisfiable == True`)
- [ ] Instances are asserted with `ClassAssertion`
- [ ] Inference rules exist (`SubClassOf` connecting to queried class)
- [ ] Reasoner precomputed inferences (`precompute_inferences()` called)

---

## Problem 2: Ontology Inconsistency

### Symptom: `is_consistent()` returns False

```python
if not reasoner.is_consistent():
    print("Ontology is inconsistent!")
```

### Diagnosis

**Step 1: Find unsatisfiable classes**

```python
unsatisfiable = reasoner.get_unsatisfiable_classes()
if unsatisfiable:
    for cls in unsatisfiable:
        print(f"Unsatisfiable: {cls}")
    # These classes are the source of contradiction
```

**Step 2: Check disjointness violations**

```python
# You might have asserted:
onto.add_axiom(DisjointClasses(Student, Teacher))

# But also said:
onto.add_axiom(ClassAssertion(Student, alice))
onto.add_axiom(ClassAssertion(Teacher, alice))

# alice can't be both → contradiction!

# Fix: Decide if disjointness or assertion is wrong
# Option 1: Remove disjointness
# onto.axioms.remove(DisjointClasses(Student, Teacher))

# Option 2: Fix assertion
# onto.axioms.remove(ClassAssertion(Teacher, alice))
```

**Step 3: Check circular definitions**

```python
# Circular definitions can cause contradictions:
onto.add_axiom(SubClassOf(A, B))
onto.add_axiom(SubClassOf(B, Complement(A)))  # B ⊆ ¬A

# This means: A ⊆ B ⊆ ¬A → contradiction!

# Fix: Make sure restriction chains are consistent
# A ⊆ B ⊆ A  (circular equivalence) = OK
# A ⊆ B ⊆ ¬A (circular negation) = NOT OK
```

**Step 4: Check cardinality conflicts**

```python
# Conflicting cardinality constraints:
onto.add_axiom(SubClassOf(Person, AtLeast(2, hasParent, Person)))
onto.add_axiom(SubClassOf(Person, AtMost(1, hasParent, Person)))

# Person must have ≥2 but ≤1 parents → contradiction!

# Fix: Make sure cardinality constraints don't conflict
onto.add_axiom(SubClassOf(Person, AtLeast(1, hasParent, Person)))
onto.add_axiom(SubClassOf(Person, AtMost(2, hasParent, Person)))  # ≥1 and ≤2 = OK
```

### Solution Checklist

- [ ] No unsatisfiable classes
- [ ] No disjoint classes with shared instances
- [ ] No circular negations
- [ ] Cardinality constraints don't conflict

---

## Problem 3: Slow Reasoning

### Symptom: `precompute_inferences()` takes > 60 seconds

```python
import time

start = time.time()
reasoner.precompute_inferences()
elapsed = time.time() - start

print(f"Reasoning took {elapsed:.1f} seconds")
if elapsed > 60:
    print("Too slow! Investigating...")
```

### Diagnosis

**Step 1: Check ontology size**

```python
classes = reasoner.get_classes()
axioms = len(onto.logical_axioms)

print(f"Classes: {len(classes)}")
print(f"Axioms: {axioms}")

# Guidelines:
# < 1000 axioms = fast
# 1000-10000 = moderate
# 10000-100000 = slow
# > 100000 = very slow (consider Java HermiT)
```

**Step 2: Check for complex restrictions**

```python
# Very restrictive constraints = slow reasoning

# SLOW: Many nested restrictions
onto.add_axiom(SubClassOf(MyClass, Intersection(
    AtLeast(5, prop1, Class1),
    AtMost(10, prop2, Class2),
    ForAll(prop3, Class3),
    ForAll(prop4, Complement(Class4)),
    # ... many more ...
)))

# FASTER: Simple restrictions
onto.add_axiom(SubClassOf(MyClass, AtLeast(1, prop, Class)))
```

**Step 3: Check for property chains**

```python
# Transitive properties increase complexity
onto.add_axiom(Transitive(manages))

# This can lead to exponential reasoning in deep hierarchies

# Better: Use only when necessary
# Only mark properties as transitive if you truly need it
```

### Solution Strategies

**Strategy 1: Simplify ontology**

```python
# Remove unnecessary axioms
# Merge similar classes
# Use flatter hierarchies instead of deep ones
```

**Strategy 2: Use on-demand reasoning**

```python
# Instead of precomputing everything:
reasoner = Reasoner(onto)
# Don't call precompute_inferences()

# Query as needed (slower per query, but faster startup)
is_subclass = reasoner.is_subclass_of(Class1, Class2)
```

**Strategy 3: Filter by relevant subset**

```python
# Create a smaller ontology with only relevant classes
relevant_classes = [ClassA, ClassB, ClassC]
mini_onto = DLOntology()

for axiom in onto.logical_axioms:
    # Only keep axioms involving relevant classes
    if involves_relevant_class(axiom, relevant_classes):
        mini_onto.add_axiom(axiom)

reasoner = Reasoner(mini_onto)
reasoner.precompute_inferences()
```

---

## Problem 4: Wrong Inference

### Symptom: Something that should be inferred isn't, or vice versa

```python
# Expected: reasoner.is_subclass_of(Dog, Animal) == True
# Actual: False

is_subclass = reasoner.is_subclass_of(Dog, Animal)
assert is_subclass, "Dog should be a subclass of Animal"
```

### Diagnosis

**Step 1: Check the axiom exists**

```python
# Make sure you actually added the rule

# WRONG: Forgot to add axiom
onto = DLOntology()
Dog = OWLClass("http://example.org/Dog")
Animal = OWLClass("http://example.org/Animal")
# Missing: onto.add_axiom(SubClassOf(Dog, Animal))

# RIGHT: Added the axiom
onto.add_axiom(SubClassOf(Dog, Animal))

# Verify in ontology
axiom = SubClassOf(Dog, Animal)
if axiom not in onto.logical_axioms:
    print("ERROR: Axiom not in ontology")
```

**Step 2: Check for typos in IRIs**

```python
# Typo in class name:
onto.add_axiom(SubClassOf(Dog, Animal))

# But then query with wrong spelling:
Dog_wrong = OWLClass("http://example.org/Doog")  # Typo!
is_subclass = reasoner.is_subclass_of(Dog_wrong, Animal)  # False!

# These are different classes because IRIs don't match

# Fix: Use consistent IRIs or reuse class objects
Dog = OWLClass("http://example.org/Dog")
onto.add_axiom(SubClassOf(Dog, Animal))
is_subclass = reasoner.is_subclass_of(Dog, Animal)  # True
```

**Step 3: Check inference path**

```python
# Trace the inference chain manually

# You have:
onto.add_axiom(SubClassOf(Poodle, Dog))
onto.add_axiom(SubClassOf(Dog, Mammal))
onto.add_axiom(SubClassOf(Mammal, Animal))

# Expected chain: Poodle ⊆ Dog ⊆ Mammal ⊆ Animal

# Debug each step:
print(f"Poodle ⊆ Dog? {reasoner.is_subclass_of(Poodle, Dog)}")
print(f"Dog ⊆ Mammal? {reasoner.is_subclass_of(Dog, Mammal)}")
print(f"Mammal ⊆ Animal? {reasoner.is_subclass_of(Mammal, Animal)}")
print(f"Poodle ⊆ Animal? {reasoner.is_subclass_of(Poodle, Animal)}")

# If chain is broken, find the broken link
```

**Step 4: Check for contradicting rules**

```python
# You might have conflicting rules:

onto.add_axiom(SubClassOf(Dog, Animal))  # Dog ⊆ Animal

# But also:
onto.add_axiom(DisjointClasses(Dog, Animal))  # Dog ⊓ Animal = ∅

# These contradict each other!
# The second rule negates the first

# Fix: Keep only one or none of them
```

### Solution Checklist

- [ ] Axiom is actually in ontology
- [ ] IRI spelling is consistent
- [ ] No contradicting rules
- [ ] Inference chain is complete
- [ ] Reasoner was reinitialized after changes

---

## Debugging Tools

### Tool 1: Print Ontology Structure

```python
def print_hierarchy(reasoner, cls, depth=0):
    """Print class hierarchy."""
    indent = "  " * depth
    print(f"{indent}{cls}")
    
    subclasses = reasoner.get_subclasses(cls)
    for sub in subclasses:
        print_hierarchy(reasoner, sub, depth + 1)

# Use it
root = OWLClass("http://www.w3.org/2002/07/owl#Thing")
print_hierarchy(reasoner, root)
```

### Tool 2: Verify Axiom Presence

```python
def check_axiom(onto, expected_axiom):
    """Check if axiom is in ontology."""
    for axiom in onto.logical_axioms:
        if axiom == expected_axiom:
            return True
    return False

# Use it
is_present = check_axiom(onto, SubClassOf(Dog, Animal))
if not is_present:
    print("ERROR: Dog ⊆ Animal axiom not found")
```

### Tool 3: Trace Inferences

```python
def trace_subclass_path(reasoner, sub, sup):
    """Try to trace why sub is subclass of sup."""
    if reasoner.is_subclass_of(sub, sup):
        print(f"✓ {sub} ⊆ {sup} (verified)")
        return True
    else:
        print(f"✗ {sub} ⊄ {sup} (not inferred)")
        
        # Check intermediate steps
        subs = reasoner.get_superclasses(sub)
        sups = reasoner.get_subclasses(sup)
        
        print(f"  Superclasses of {sub}: {subs}")
        print(f"  Subclasses of {sup}: {sups}")
        
        return False

# Use it
trace_subclass_path(reasoner, Dog, Animal)
```

---

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Forgot axiom | Query returns False | Add axiom with `onto.add_axiom()` |
| Typo in IRI | Different classes treated | Use same class object everywhere |
| Circular negation | Unsatisfiable class | Remove contradicting rules |
| Mixed IRI formats | Different classes | Standardize IRI format (http:// vs http://) |
| Didn't call `precompute_inferences()` | Slow queries | Call once before querying |
| Assertions on class instead of individual | No instances | Use `OWLNamedIndividual` not `OWLClass` |

---

**See Also:**
- **[FAQ](../faq.md)** — Quick answers
- **[Patterns](./patterns.md)** — Design patterns
- **[Concepts](../concepts.md)** — How reasoning works
