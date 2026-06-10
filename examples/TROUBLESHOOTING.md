# Troubleshooting Guide

Having problems with PyHermit? This guide covers common issues and solutions.

## Table of Contents
- [Consistency Issues](#consistency-issues)
- [Performance Problems](#performance-problems)
- [Query Results](#query-results)
- [Data & Format Issues](#data--format-issues)
- [Integration Issues](#integration-issues)

---

## Consistency Issues

### Problem: Ontology is Inconsistent (When It Shouldn't Be)

**Symptom:** `reasoner.is_consistent()` returns `False` unexpectedly.

**Diagnosis:** Add this code to find what's unsatisfiable:

```python
if not reasoner.is_consistent():
    print("Unsatisfiable concepts:")
    for cls in ontology.all_atomic_concepts:
        if not reasoner.is_satisfiable(cls):
            print(f"  - {cls.iri}")
```

**Common Causes:**

1. **Violated Disjointness**
   ```python
   # Problem:
   Disjoint(A, B)
   # But fact says: instance is both A and B
   
   # Solution: Remove one of the facts or remove disjointness
   ```

2. **Violated Cardinality**
   ```python
   # Problem:
   PersonMax2Parents = Person ⊓ ≤2 hasParent
   # But fact says: Alice has 3 parents
   
   # Solution: Fix the cardinality or the facts
   ```

3. **Circular Constraints**
   ```python
   # Problem:
   A ⊑ ∃R.B
   B ⊑ ∃R.A
   # Can create infinite chains
   
   # Solution: Use blocking strategy or add guards
   ```

4. **Wrong Negation**
   ```python
   # Problem:
   A ⊑ ¬B  # A implies not B
   # But fact says: something is both A and B
   
   # Solution: Check logical consistency of rules
   ```

**Solution Steps:**

1. Comment out half the axioms, check if consistent
2. If consistent, problem is in commented-out part
3. Narrow down to the specific axiom
4. Fix or remove the problematic axiom

### Problem: Ontology is Consistent When It Should Be Inconsistent

**Symptom:** `is_consistent()` returns `True` but you have contradictory facts.

**Diagnosis:**

1. Check that facts are actually in the ontology:
```python
print("Facts in ontology:")
for fact in ontology.positive_facts:
    print(f"  {fact}")
```

2. Check that disjointness is properly expressed:
```python
# Verify class hierarchy includes disjoint declarations
for cls in ontology.all_atomic_concepts:
    print(f"  {cls.iri}")
```

3. Verify axioms are correct:
```python
print(f"Ontology has {len(ontology.dl_clauses)} clauses")
for clause in list(ontology.dl_clauses)[:5]:
    print(f"  {clause}")
```

**Solution:**

- Ensure disjoint classes are properly declared
- Verify cardinality constraints are in the TBox
- Check that contradictory facts are actually in the ABox

---

## Performance Problems

### Problem: Reasoning is Extremely Slow

**Symptom:** Reasoning takes minutes or hours for a simple query.

**Quick Fixes (try in order):**

1. **Set a timeout**
   ```python
   config = Configuration()
   config.individual_task_timeout = 5000  # 5 seconds
   reasoner = Reasoner(ontology, config)
   ```

2. **Use a simpler blocking strategy**
   ```python
   config.blocking_strategy_type = BlockingStrategyType.ANCESTOR
   ```

3. **Don't use precomputation if not needed**
   ```python
   # Instead of:
   reasoner.precompute_inferences(class_hierarchy=True)
   
   # Just query specific classes:
   reasoner.is_sub_class_of(A, B)
   ```

**Detailed Diagnosis:**

```python
import time

config = Configuration()
config.blocking_strategy_type = BlockingStrategyType.ANCESTOR

reasoner = Reasoner(ontology, config)

start = time.time()
result = reasoner.is_consistent()
elapsed = time.time() - start

print(f"Time: {elapsed:.2f}s")
if elapsed > 5:
    print("Consider simplifying the ontology or using simpler blocking")
```

**Root Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Deep class hierarchies | Use ANCESTOR blocking |
| Large cardinalities (≥50) | Reduce or remove high cardinalities |
| Complex negation | Simplify axioms |
| Many individuals | Reduce ABox facts or use incremental reasoning |
| Circular rules | Add guards or use blocking |

### Problem: Out of Memory

**Symptom:** `MemoryError` or "out of memory" errors.

**Causes:**
- Ontology is too large
- Infinite blocking leads to unbounded model
- Cached inferences consume all RAM

**Solutions:**

1. **Reduce ontology size**
   - Split into modules
   - Remove unnecessary facts
   - Simplify cardinalities

2. **Clear reasoner cache**
   ```python
   reasoner.dispose()
   # Create a new reasoner for next use
   ```

3. **Reduce precomputation**
   ```python
   # Instead of full precomputation:
   reasoner.precompute_inferences(class_hierarchy=False)
   
   # Or avoid precomputation:
   reasoner.is_consistent()  # Just check consistency
   ```

4. **Use garbage collection**
   ```python
   import gc
   reasoner.dispose()
   gc.collect()
   ```

---

## Query Results

### Problem: get_instances() Returns Empty List

**Symptom:** `reasoner.get_instances(my_class)` returns `[]` even though there should be instances.

**Checklist:**

1. Did you call `precompute_inferences()`?
   ```python
   # WRONG:
   instances = reasoner.get_instances(my_class)
   
   # CORRECT:
   reasoner.precompute_inferences()
   instances = reasoner.get_instances(my_class)
   ```

2. Is the class actually in the ontology?
   ```python
   my_iri = "http://example.org#Dog"
   all_classes = [c.iri for c in ontology.all_atomic_concepts]
   if my_iri in all_classes:
       print("Class exists")
   else:
       print("Class NOT in ontology!")
   ```

3. Are there any individuals in the ontology?
   ```python
   print(f"Total individuals: {len(ontology.all_individuals)}")
   for ind in list(ontology.all_individuals)[:5]:
       print(f"  - {ind.iri}")
   ```

4. Are facts actually asserted?
   ```python
   print(f"Total facts: {len(ontology.positive_facts)}")
   for fact in list(ontology.positive_facts)[:5]:
       print(f"  - {fact}")
   ```

5. Are instances subsumed by the class?
   ```python
   reasoner.precompute_inferences()
   
   # Check what types each individual has
   for ind in ontology.all_individuals:
       types = reasoner.get_types(ind)
       print(f"{ind.iri}:")
       for t in types:
           print(f"  - {t.iri}")
   ```

### Problem: Subsumption Queries Return False Unexpectedly

**Similar checklist as above, but for classes.**

1. Called `precompute_inferences(class_hierarchy=True)`?
2. Parent class actually exists?
3. Any subclasses actually exist?
4. Subsumption relationships properly defined?

```python
# Debug subsumption
reasoner.precompute_inferences(class_hierarchy=True)

class_a = AtomicConcept.create("http://example.org#ClassA")
class_b = AtomicConcept.create("http://example.org#ClassB")

# Check if B is subsumed by A
is_sub = reasoner.is_sub_class_of(class_b, class_a)
print(f"B ⊑ A: {is_sub}")

# If False, why?
b_satisfiable = reasoner.is_satisfiable(class_b)
print(f"B satisfiable: {b_satisfiable}")
```

### Problem: Results Are Unexpected

**Symptom:** Query result doesn't match what you expected.

**Diagnosis Process:**

1. **Verify the ontology is what you think**
   ```python
   print(f"Classes: {len(ontology.all_atomic_concepts)}")
   print(f"Clauses: {len(ontology.dl_clauses)}")
   print(f"Individuals: {len(ontology.all_individuals)}")
   print(f"Facts: {len(ontology.positive_facts)}")
   ```

2. **Check consistency**
   ```python
   if not reasoner.is_consistent():
       print("WARNING: Ontology is inconsistent!")
   ```

3. **Trace the inference**
   ```python
   # For subsumption queries
   A = AtomicConcept.create("http://example.org#A")
   B = AtomicConcept.create("http://example.org#B")
   
   # Check each step
   is_equiv = reasoner.is_equivalent(A, B)
   is_sub = reasoner.is_sub_class_of(A, B)
   
   print(f"A ≡ B: {is_equiv}")
   print(f"A ⊑ B: {is_sub}")
   print(f"B ⊑ A: {reasoner.is_sub_class_of(B, A)}")
   ```

4. **Check intermediate inferences**
   ```python
   # For instance queries
   individual = Individual.create("http://example.org#Bob")
   
   types = reasoner.get_types(individual)
   print(f"Direct types: {[t.iri for t in types]}")
   
   # Check if in specific class
   person = AtomicConcept.create("http://example.org#Person")
   print(f"Is person: {reasoner.has_type(individual, person)}")
   ```

---

## Data & Format Issues

### Problem: load_ontology() Fails

**Symptom:** `FileNotFoundError` or import errors when loading OWL files.

**Solutions:**

1. **Check file exists**
   ```python
   from pathlib import Path
   
   file = Path("ontology.owl")
   if file.exists():
       print("File found")
   else:
       print(f"File not found: {file.absolute()}")
   ```

2. **Check file format**
   ```python
   # Supported formats (stdlib reader, no extra packages):
   # - RDF/XML (.owl, .rdf)
   # - OWL/XML (.owx, .owl)
   # - Functional-Style Syntax (.ofn)
   ```

3. **Use absolute paths**
   ```python
   from pathlib import Path
   
   # Better than relative paths:
   ontology = load_ontology(Path(__file__).parent / "ontology.owl")
   ```

### Problem: Wrong IRI Format

**Symptom:** Concepts/roles created but reasoner doesn't recognize them.

**Common Mistakes:**

```python
# WRONG: Missing # or /
dog = AtomicConcept.create("http://example.org:Dog")

# CORRECT: Use # or /
dog = AtomicConcept.create("http://example.org#Dog")
dog = AtomicConcept.create("http://example.org/Dog")

# WRONG: Mixing formats
has_owner = AtomicRole.create("http://example.org/hasOwner")
dog_with_owner = AtomicConcept.create("http://example.org#DogWithOwner")
# ^ Different base, may cause issues

# CORRECT: Consistent format
base = "http://example.org"
has_owner = AtomicRole.create(f"{base}#hasOwner")
dog_with_owner = AtomicConcept.create(f"{base}#DogWithOwner")
```

### Problem: Atom Creation Fails

**Symptom:** `TypeError` or `ValueError` when creating `Atom` objects.

**Common Mistakes:**

```python
# WRONG: Too many arguments
Atom.create(concept, variable1, variable2)  # concept atoms take 2 args

# CORRECT:
Atom.create(concept, variable1)              # concept atom
Atom.create(role, variable1, variable2)      # role atom

# WRONG: Variable not created
Atom.create(concept, "X")  # String, not Variable

# CORRECT:
X = Variable.create("X")
Atom.create(concept, X)
```

---

## Integration Issues

### Problem: Using Reasoner in Multi-threaded App

**Symptom:** Crashes, hangs, or incorrect results in concurrent code.

**Solution: Don't share reasoners**

```python
# WRONG: Sharing reasoner across threads
reasoner = Reasoner(ontology)

def thread_func():
    result = reasoner.is_consistent()  # UNSAFE!
    return result

# CORRECT: Create per thread
import threading

def thread_func(ontology):
    reasoner = Reasoner(ontology)
    try:
        result = reasoner.is_consistent()
        return result
    finally:
        reasoner.dispose()

# Or use a thread pool with per-thread reasoners
```

### Problem: Reasoner Not Cleaning Up

**Symptom:** Memory leaks, file handles open, processes hanging.

**Solution: Always dispose**

```python
# WRONG:
reasoner = Reasoner(ontology)
result = reasoner.is_consistent()
# Forgot to dispose!

# CORRECT:
reasoner = Reasoner(ontology)
try:
    result = reasoner.is_consistent()
finally:
    reasoner.dispose()

# Or use context manager (if available):
with Reasoner(ontology) as reasoner:
    result = reasoner.is_consistent()
# Automatically disposed
```

### Problem: Ontology Modification Not Reflected

**Symptom:** Change ontology but reasoner still gives old results.

**Solution: Create new reasoner**

```python
# WRONG: Reusing reasoner after ontology change
ontology = DLOntology(...)
reasoner = Reasoner(ontology)
result1 = reasoner.is_consistent()

ontology = DLOntology(...)  # New ontology!
# But reasoner still has old ontology!
result2 = reasoner.is_consistent()  # Wrong result!

# CORRECT: New reasoner for new ontology
ontology1 = DLOntology(...)
reasoner1 = Reasoner(ontology1)
result1 = reasoner1.is_consistent()
reasoner1.dispose()

ontology2 = DLOntology(...)
reasoner2 = Reasoner(ontology2)
result2 = reasoner2.is_consistent()
reasoner2.dispose()
```

---

## Debugging Techniques

### Print Debug Info

```python
# Check ontology structure
print(f"Classes: {len(ontology.all_atomic_concepts)}")
print(f"Individuals: {len(ontology.all_individuals)}")
print(f"Facts: {len(ontology.positive_facts)}")
print(f"Clauses: {len(ontology.dl_clauses)}")

# Sample elements
print("\nFirst 5 classes:")
for cls in list(ontology.all_atomic_concepts)[:5]:
    print(f"  {cls.iri}")

print("\nFirst 5 facts:")
for fact in list(ontology.positive_facts)[:5]:
    print(f"  {fact}")
```

### Enable Reasoning Monitor

```python
from hermit.monitor import Timer

monitor = Timer()
config = Configuration()
config.monitor = monitor

reasoner = Reasoner(ontology, config)
# ... reasoning ...
# monitor.stop()  # Check timing info
```

### Test Incrementally

```python
# Build ontology piece by piece
clauses = []
facts = []

# Add subsumption
clauses.append(DLClause.create(...))
ontology = DLOntology(..., dl_clauses=frozenset(clauses), ...)
reasoner = Reasoner(ontology)
assert reasoner.is_consistent()
print("✓ Subsumption works")

# Add role
clauses.append(DLClause.create(...))
# ... test again ...

# Incrementally build up to full ontology
```

---

## Still Stuck?

1. **Simplify**: Create minimal failing example
2. **Test**: Run against the examples in `examples/`
3. **Log**: Print intermediate results
4. **Compare**: What would Protégé or Java Hermit do?
5. **Ask**: Post on semantic web forums or GitHub issues

---

**Remember: The reasoner is always correct — the ontology might be wrong!**
