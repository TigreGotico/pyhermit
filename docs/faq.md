# Frequently Asked Questions (FAQ)

Quick answers to common questions about PyHermit.

## Getting Started

### Q: What's the difference between PyHermit and other reasoners?

**A:** PyHermit is a Python port of the HermiT reasoner (originally Java). It implements the **OWL 2 DL** standard with tableau-based reasoning.

| Reasoner | Language | OWL Profile | Strengths |
|----------|----------|-------------|-----------|
| HermiT (Java) | Java | OWL 2 DL | Fast, mature, original |
| **PyHermit** | Python | OWL 2 DL | Python ecosystem, integrations |
| Pellet | Java | OWL 2 DL | Modular ontologies |
| RDFlib | Python | Basic | Simple, lightweight |
| Owlready2 | Python | OWL 2 | High-level API |

### Q: Can I use PyHermit in my application?

**A:** Yes. PyHermit is:
- ✅ Production-ready (100% test passing)
- ✅ Apache 2.0 licensed (commercial-friendly)
- ✅ Pure Python (no Java dependencies)
- ✅ Embeddable in applications

### Q: Is PyHermit faster than the Java version?

**A:** No. Java HermiT is faster due to JVM optimizations. Use PyHermit when you need:
- Integration with Python libraries (pandas, numpy, scikit-learn)
- Ontologies < 10,000 classes
- Don't need extreme performance

## Ontology Design

### Q: How do I model "A has at least one B"?

**A:** Use **AtLeast** (existential restriction):

```python
from hermit.model import AtLeast

# Every Parent has at least one Child
onto.add_axiom(SubClassOf(
    Parent,
    AtLeast(1, hasChild, Child)
))
```

### Q: How do I model "all A are B" or "if A then B"?

**A:** Use **SubClassOf** (subsumption):

```python
# All Dogs are Animals
onto.add_axiom(SubClassOf(Dog, Animal))

# If something has only harmful properties, it's harmful
onto.add_axiom(SubClassOf(
    Intersection(hasOnly(Property), harmfulProperty),
    Harmful
))
```

### Q: How do I say "A and B are mutually exclusive"?

**A:** Use **DisjointClasses**:

```python
from hermit.model import DisjointClasses

# Students and Employees cannot be the same
onto.add_axiom(DisjointClasses(Student, Employee))
```

### Q: Can I model inheritance chains?

**A:** Yes, naturally:

```python
onto.add_axiom(SubClassOf(Dog, Mammal))
onto.add_axiom(SubClassOf(Mammal, Animal))

# Reasoner automatically infers: Dog ⊆ Animal
```

### Q: How do I express "exactly 2 parents"?

**A:** Combine **AtLeast** and **AtMost**:

```python
from hermit.model import AtMost, Intersection

onto.add_axiom(SubClassOf(
    Person,
    Intersection(
        AtLeast(2, hasParent, Person),
        AtMost(2, hasParent, Person)
    )
))
```

### Q: Can I have circular class definitions?

**A:** Yes, but be careful:

```python
# Safe circular definition
onto.add_axiom(SubClassOf(Parent, Intersection(Person, ∃hasChild.Child)))
onto.add_axiom(SubClassOf(Child, Intersection(Person, ∃hasParent.Parent)))

# Unsafe - creates contradiction
onto.add_axiom(SubClassOf(A, B))
onto.add_axiom(SubClassOf(B, Complement(A)))  # A ⊆ B ⊆ ¬A = unsatisfiable
```

## Reasoning & Queries

### Q: What's the difference between precompute_inferences() and on-demand reasoning?

**A:**

```python
# Precompute: Do all work upfront, then query fast
reasoner.precompute_inferences()
is_subclass = reasoner.is_subclass_of(Class1, Class2)  # Instant

# On-demand: Reason as you query (slower per query)
# Don't call precompute_inferences()
is_subclass = reasoner.is_subclass_of(Class1, Class2)  # Slower
```

**When to use:**
- **Precompute:** Multiple queries, cached results needed
- **On-demand:** Single query, memory-constrained systems

### Q: Why is my query returning fewer results than expected?

**A:** Common causes:

1. **Instance not in right class:**
   ```python
   # You expect alice to be an Employee
   onto.add_axiom(ClassAssertion(Person, alice))  # Wrong!
   onto.add_axiom(ClassAssertion(Employee, alice))  # Correct
   ```

2. **Class is unsatisfiable:**
   ```python
   unsatisfiable = reasoner.get_unsatisfiable_classes()
   if not unsatisfiable:
       print("All classes are satisfiable")
   ```

3. **Missing inference:**
   ```python
   # Check if reasoning was done
   reasoner.precompute_inferences()
   # Then query again
   ```

### Q: Can I check if a class is satisfiable (can have instances)?

**A:** Yes:

```python
is_satisfiable = reasoner.is_satisfiable(MyClass)
if not is_satisfiable:
    print(f"{MyClass} cannot have any instances")
```

### Q: How do I find contradictions in my ontology?

**A:**

```python
# Check overall consistency
if not reasoner.is_consistent():
    print("Ontology has contradictions")

# Find unsatisfiable classes (the culprits)
unsatisfiable = reasoner.get_unsatisfiable_classes()
for cls in unsatisfiable:
    print(f"Unsatisfiable: {cls}")
```

### Q: Can I query inverse relationships?

**A:** Yes, if you define them:

```python
from hermit.model import InverseOf

hasChild = OWLObjectProperty("...")
hasParent = OWLObjectProperty("...")

onto.add_axiom(InverseOf(hasParent, hasChild))

# Now both relationships work
parents = reasoner.get_object_property_values(hasParent, child)
children = reasoner.get_object_property_values(hasChild, parent)
```

## Performance & Optimization

### Q: Why is reasoning slow for my ontology?

**A:** Check these:

1. **Ontology size:**
   ```python
   # > 50,000 axioms?
   classes = reasoner.get_classes()
   axioms = len(onto.logical_axioms)
   print(f"Classes: {len(classes)}, Axioms: {axioms}")
   ```

2. **Complex restrictions:**
   ```python
   # Very restrictive = slow
   onto.add_axiom(SubClassOf(
       MyClass,
       Intersection(
           AtLeast(5, prop1, Class1),
           AtMost(10, prop2, Class2),
           ForAll(prop3, Complement(Class3)),
           # ... many more
       )
   ))
   ```

3. **No precomputation:**
   ```python
   # Slow: reasoning on every query
   for q in queries:
       reasoner.is_subclass_of(q[0], q[1])  # Reason each time
   
   # Better: precompute once
   reasoner.precompute_inferences()
   for q in queries:
       reasoner.is_subclass_of(q[0], q[1])  # Instant
   ```

### Q: Can I optimize by filtering irrelevant classes?

**A:** Yes:

```python
# Only reason about classes you need
relevant_classes = [Class1, Class2, Class3]

reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Query only relevant classes
for cls in relevant_classes:
    instances = reasoner.get_instances(cls)
    print(f"{cls}: {len(instances)}")
```

### Q: What's the maximum ontology size PyHermit can handle?

**A:** Depends on constraints:

| Size | Classes | Axioms | Time | Recommendation |
|------|---------|--------|------|-----------------|
| Small | < 100 | < 500 | < 1s | Use PyHermit |
| Medium | 100-10k | 500-50k | 1-60s | Use PyHermit |
| Large | 10k-100k | 50k-500k | 1-10min | Use Java HermiT |
| Huge | > 100k | > 500k | > 10min | Use specialized tools |

## Data Handling

### Q: Can I use strings, numbers, and dates as property values?

**A:** Yes, using **DataProperty**:

```python
from hermit.model import Literal, OWLDataProperty, DataPropertyAssertion

hasName = OWLDataProperty("...")
hasAge = OWLDataProperty("...")
hasBirthDate = OWLDataProperty("...")

onto.add_axiom(DataPropertyAssertion(hasName, person, Literal("Alice", "string")))
onto.add_axiom(DataPropertyAssertion(hasAge, person, Literal(30, "integer")))
onto.add_axiom(DataPropertyAssertion(hasBirthDate, person, Literal("1990-01-15", "date")))
```

### Q: Can I have multi-valued properties?

**A:** Yes, add multiple assertions:

```python
# Alice has multiple emails
onto.add_axiom(DataPropertyAssertion(hasEmail, alice, Literal("alice@work.com", "string")))
onto.add_axiom(DataPropertyAssertion(hasEmail, alice, Literal("alice@home.com", "string")))

# Query all values
emails = reasoner.get_data_property_values(hasEmail, alice)
# Returns: {Literal("alice@work.com"), Literal("alice@home.com")}
```

### Q: How do I handle missing data?

**A:** Use **open-world assumption** (default):

```python
# In OWL, if you don't assert something, it's unknown (not false)
onto.add_axiom(ClassAssertion(Person, alice))
# alice has unknown age (not asserted)

age = reasoner.get_data_property_values(hasAge, alice)
if not age:
    print("Age unknown")  # True
```

To change to **closed-world assumption**:

```python
# Add negative assertion
from hermit.model import NegativeDataPropertyAssertion
onto.add_axiom(NegativeDataPropertyAssertion(hasAge, alice, Literal(30, "integer")))
# Now alice definitely doesn't have age 30
```

## Integration & APIs

### Q: Can I load RDF/OWL files?

**A:** Use **load_ontology**:

```python
from hermit.parser import load_ontology

onto = load_ontology("path/to/ontology.owl")
reasoner = Reasoner(onto)
reasoner.precompute_inferences()
```

### Q: Can I export the reasoned ontology?

**A:** Extract what you need:

```python
# Get all inferred facts
all_classes = reasoner.get_classes()
for cls in all_classes:
    instances = reasoner.get_instances(cls)
    print(f"{cls}: {instances}")
```

### Q: Can I use PyHermit with pandas/numpy?

**A:** Yes:

```python
import pandas as pd
from hermit import Reasoner

onto = DLOntology()
# ... build ontology ...

reasoner = Reasoner(onto)
reasoner.precompute_inferences()

# Convert to DataFrame
data = []
for cls in reasoner.get_classes():
    for inst in reasoner.get_instances(cls):
        data.append({"class": cls, "instance": inst})

df = pd.DataFrame(data)
print(df)
```

### Q: Can I integrate PyHermit with a web service?

**A:** Yes:

```python
from flask import Flask, request, jsonify
from hermit import Reasoner

app = Flask(__name__)
reasoner = None  # Initialized on startup

@app.route("/query", methods=["POST"])
def query():
    cls = request.json["class"]
    instances = list(reasoner.get_instances(cls))
    return jsonify({"instances": instances})

if __name__ == "__main__":
    onto = load_ontology("ontology.owl")
    reasoner = Reasoner(onto)
    reasoner.precompute_inferences()
    app.run()
```

## Troubleshooting

### Q: I get "UnsupportedDatatypeException" - what does this mean?

**A:** You used an unsupported datatype:

```python
# Supported datatypes
supported = [
    "xsd:string", "xsd:integer", "xsd:decimal", "xsd:float",
    "xsd:double", "xsd:boolean", "xsd:anyURI", "xsd:dateTime",
    "xsd:base64Binary", "xsd:hexBinary"
]

# Use only these!
onto.add_axiom(DataPropertyAssertion(
    hasAge, person, Literal(30, "xsd:integer")  # ✓ OK
))
```

### Q: My reasoner hangs or is very slow

**A:** Try:

1. **Check memory:** Is your machine out of RAM?
2. **Reduce axioms:** Remove unnecessary rules
3. **Check for loops:** Are rules creating infinite loops?
4. **Profile:** Where is time spent?

```python
import time

start = time.time()
reasoner.precompute_inferences()
elapsed = time.time() - start

print(f"Reasoning took {elapsed:.1f}s")
if elapsed > 60:
    print("Consider simplifying your ontology")
```

### Q: How do I debug why an inference didn't happen?

**A:**

```python
# 1. Check class is satisfiable
if reasoner.is_satisfiable(MyClass):
    print(f"{MyClass} is satisfiable")
else:
    print(f"{MyClass} is unsatisfiable (no instances possible)")

# 2. Check direct types
direct_types = reasoner.get_direct_types(individual)
print(f"Direct types: {direct_types}")

# 3. Check inferred types
all_types = reasoner.get_types(individual)
print(f"All types: {all_types}")

# 4. Verify subsumption relationships
is_subclass = reasoner.is_subclass_of(Class1, Class2)
print(f"{Class1} ⊆ {Class2}: {is_subclass}")
```

## License & Community

### Q: Can I use PyHermit commercially?

**A:** Yes. Apache 2.0 license allows commercial use without restriction.

### Q: Where do I report bugs?

**A:** GitHub Issues: https://github.com/anthropics/...

### Q: Can I contribute to PyHermit?

**A:** Yes! See CONTRIBUTING.md for guidelines.

---

**Still have questions?** Check the [full documentation](./index.md) or open an issue.
