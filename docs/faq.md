# Frequently Asked Questions (FAQ)

Quick answers to common questions about PyHermit.

Code snippets assume the standard setup from
[First Program](./first-program.md):

```python
from hermit import Reasoner
from hermit.model import AtomicConcept, AtomicRole, Individual
from hermit.owl_model.class_expression import (
    OWLClass,
    OWLObjectComplementOf,
    OWLObjectIntersectionOf,
    OWLObjectMaxCardinality,
    OWLObjectMinCardinality,
    OWLObjectSomeValuesFrom,
)
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_property import OWLDataProperty, OWLObjectProperty
from hermit.owl_model.owl_literal import OWLLiteral
from hermit.owl_model.owl_axiom import (
    OWLClassAssertionAxiom,
    OWLDataPropertyAssertionAxiom,
    OWLDisjointClassesAxiom,
    OWLEquivalentClassesAxiom,
    OWLInverseObjectPropertiesAxiom,
    OWLNegativeDataPropertyAssertionAxiom,
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

## Getting started

### Q: What is the difference between PyHermit and other reasoners?

A: PyHermit is a Python port of the HermiT reasoner, originally written in Java. It implements OWL 2 DL reasoning with the hypertableau calculus.

| Reasoner | Language | OWL Profile | Strengths |
|----------|----------|-------------|-----------|
| HermiT (Java) | Java | OWL 2 DL | Fast, mature, original |
| PyHermit | Python | OWL 2 DL | Pure Python, no JVM, easy embedding |
| Pellet | Java | OWL 2 DL | Modular ontologies |
| RDFlib | Python | RDFS-level | Simple, lightweight triple store |

### Q: Can I use PyHermit in my application?

A: Yes. PyHermit is LGPL-3.0-or-later licensed, matching upstream HermiT. It is pure Python with no Java dependencies, and it embeds in applications as a library (dynamic linking keeps the LGPL terms permissive for proprietary applications). It is conformance-tested: 340 of 350 W3C OWL WG Approved-DL test cases pass at a 20-second per-case budget, with zero wrong answers.

### Q: Is PyHermit faster than the Java version?

A: No. Java HermiT is faster because of JVM optimizations. Use PyHermit when you need integration with Python libraries (pandas, numpy, scikit-learn), a reasoner without a JVM dependency, or you work with small-to-medium ontologies.

## Ontology design

### Q: How do I model "A has at least one B"?

A: Use an existential restriction (`OWLObjectSomeValuesFrom`, or `OWLObjectMinCardinality` for counts).

```python
Parent = OWLClass(NS + "Parent")
Child = OWLClass(NS + "Child")
hasChild = OWLObjectProperty(NS + "hasChild")

# Every Parent has at least one Child
axiom = OWLSubClassOfAxiom(Parent, OWLObjectSomeValuesFrom(hasChild, Child))
```

### Q: How do I model "all A are B" or "if A then B"?

A: Use `OWLSubClassOfAxiom` (subsumption).

```python
Dog = OWLClass(NS + "Dog")
Animal = OWLClass(NS + "Animal")

# All Dogs are Animals
axiom = OWLSubClassOfAxiom(Dog, Animal)
```

### Q: How do I say "A and B are mutually exclusive"?

A: Use `OWLDisjointClassesAxiom`.

```python
Student = OWLClass(NS + "Student")
Employee = OWLClass(NS + "Employee")

# Nothing can be both a Student and an Employee
axiom = OWLDisjointClassesAxiom([Student, Employee])
```

### Q: Can I model inheritance chains?

A: Yes, naturally.

```python
Mammal = OWLClass(NS + "Mammal")

axioms = [
    OWLSubClassOfAxiom(Dog, Mammal),
    OWLSubClassOfAxiom(Mammal, Animal),
]

reasoner = reasoner_from_axioms(axioms)
# Reasoner automatically infers: Dog is a subclass of Animal
print(reasoner.is_sub_class_of(
    AtomicConcept.create(NS + "Dog"), AtomicConcept.create(NS + "Animal")
))  # True
reasoner.dispose()
```

### Q: How do I express "exactly 2 parents"?

A: Combine min- and max-cardinality, or use `OWLObjectExactCardinality`.

```python
Person = OWLClass(NS + "Person")
hasParent = OWLObjectProperty(NS + "hasParent")

axiom = OWLSubClassOfAxiom(
    Person,
    OWLObjectIntersectionOf([
        OWLObjectMinCardinality(2, hasParent, Person),
        OWLObjectMaxCardinality(2, hasParent, Person),
    ]),
)
```

### Q: Can I have circular class references?

A: Yes, but be careful.

```python
# Safe circular reference — Parents have Child children, Children have Parent parents
hasChild = OWLObjectProperty(NS + "hasChild")
safe = [
    OWLSubClassOfAxiom(Parent, OWLObjectSomeValuesFrom(hasChild, Child)),
    OWLSubClassOfAxiom(Child, OWLObjectSomeValuesFrom(hasParent, Parent)),
]

# Unsafe — circular negation makes A unsatisfiable
A = OWLClass(NS + "A")
B = OWLClass(NS + "B")
unsafe = [
    OWLSubClassOfAxiom(A, B),
    OWLSubClassOfAxiom(B, OWLObjectComplementOf(A)),  # A is a subclass of B is a subclass of not-A
]
```

## Reasoning and queries

### Q: What is the difference between precompute_inferences() and on-demand reasoning?

A:

```python
axioms = [OWLSubClassOfAxiom(Dog, Animal)]
dog = AtomicConcept.create(NS + "Dog")
animal = AtomicConcept.create(NS + "Animal")

# Precompute: classify everything upfront, then query the cached hierarchy
reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()
print(reasoner.is_sub_class_of(dog, animal))  # served from the hierarchy
reasoner.dispose()

# On-demand: each query may trigger tableau work
reasoner = reasoner_from_axioms(axioms)
print(reasoner.is_sub_class_of(dog, animal))  # computed on demand
reasoner.dispose()
```

Use precompute when you run multiple queries, retrieve instances, or need the full hierarchy. Use on-demand for a single satisfiability or subsumption test.

### Q: Why does my query return fewer results than expected?

A: Check these common causes.

1. The instance is not asserted into the right class. Check your `OWLClassAssertionAxiom`s (the individual comes first).
2. A rule is missing. There is no `OWLSubClassOfAxiom` connecting the asserted class to the queried class.
3. A defined class uses subclass-of instead of equivalent-to. The reasoner can only recognize members of a class defined with `OWLEquivalentClassesAxiom`.

See the [Debugging Guide](./recipes/debugging.md) for a step-by-step diagnosis.

### Q: Can I check if a class is satisfiable (can have instances)?

A: Yes.

```python
reasoner = reasoner_from_axioms(unsafe)
a = AtomicConcept.create(NS + "A")
if not reasoner.is_satisfiable(a):
    print("A cannot have any instances")
reasoner.dispose()
```

### Q: How do I find contradictions in my ontology?

A:

```python
reasoner = reasoner_from_axioms(unsafe)

# Check overall consistency
if not reasoner.is_consistent():
    print("Ontology has contradictions")

# Find unsatisfiable classes (the culprits)
unsatisfiable = [
    ac.iri for ac in reasoner.dl_ontology.all_atomic_concepts
    if not reasoner.is_satisfiable(ac)
]
print(f"Unsatisfiable: {unsatisfiable}")
reasoner.dispose()
```

### Q: Can I query inverse relationships?

A: Yes. Declare the inverse property, or query with an `InverseRole` handle directly.

```python
from hermit.model import InverseRole

alice = OWLNamedIndividual(NS + "alice")
bob = OWLNamedIndividual(NS + "bob")

axioms = [OWLObjectPropertyAssertionAxiom(alice, hasChild, bob)]
reasoner = reasoner_from_axioms(axioms)

has_child = AtomicRole.create(NS + "hasChild")
alice_h = Individual.create(NS + "alice")
bob_h = Individual.create(NS + "bob")

# Forward direction
print(reasoner.has_role_relationship(alice_h, has_child, bob_h))  # True

# Inverse direction via an InverseRole handle
print(reasoner.has_role_relationship(bob_h, InverseRole.create(has_child), alice_h))  # True
reasoner.dispose()
```

## Performance and optimization

### Q: Why is reasoning slow for my ontology?

A: Check these points.

1. Ontology size and shape:
   ```python
   reasoner = reasoner_from_axioms(axioms)
   print(reasoner.stats)  # clauses, atomic_concepts, individuals, is_horn
   reasoner.dispose()
   ```
   Horn ontologies (`is_horn: True`) avoid backtracking and classify much faster.
2. Expensive constructs: large max-cardinalities, deeply nested disjunctions, and transitive properties over deep existential chains.
3. No precomputation: call `precompute_inferences()` once before a batch of queries, instead of letting every query re-reason.

### Q: What is the maximum ontology size PyHermit can handle?

A: It depends on the constructs used, not just raw counts. A Horn ontology with 50,000 simple subclass axioms classifies quickly, while a few hundred axioms mixing disjunctions, cardinalities, and transitivity can be hard. As a rule of thumb, prefer Java HermiT above roughly 10,000 classes, or when classification times stop being acceptable.

## Data handling

### Q: Can I use strings, numbers, and dates as property values?

A: Yes, with data properties and `OWLLiteral`. PyHermit infers the datatype from the Python type.

```python
from datetime import date

person = OWLNamedIndividual(NS + "person1")
hasName = OWLDataProperty(NS + "hasName")
hasAge = OWLDataProperty(NS + "hasAge")
hasBirthDate = OWLDataProperty(NS + "hasBirthDate")

axioms = [
    OWLDataPropertyAssertionAxiom(person, hasName, OWLLiteral("Alice")),
    OWLDataPropertyAssertionAxiom(person, hasAge, OWLLiteral(30)),
    OWLDataPropertyAssertionAxiom(person, hasBirthDate, OWLLiteral(date(1990, 1, 15))),
]
```

### Q: Can I have multi-valued properties?

A: Yes. Add multiple assertions.

```python
hasEmail = OWLDataProperty(NS + "hasEmail")

axioms = [
    OWLDataPropertyAssertionAxiom(person, hasEmail, OWLLiteral("alice@work.example")),
    OWLDataPropertyAssertionAxiom(person, hasEmail, OWLLiteral("alice@home.example")),
]
```

### Q: How do I handle missing data?

A: OWL uses the open-world assumption: if you do not assert something, it is unknown, not false. To state an explicit falsehood, use a negative assertion.

```python
axiom = OWLNegativeDataPropertyAssertionAxiom(person, hasAge, OWLLiteral(30))
# person definitely does not have age 30
```

## Integration and APIs

### Q: Can I load RDF/OWL files?

A: Use `load_ontology` (a pure stdlib reader for RDF/XML, OWL/XML, and Functional-Style Syntax), then compile the axioms as usual.

```python
# doc-sample: skip (needs an .owl file on disk)
from hermit.parser import load_ontology

axioms = load_ontology("path/to/ontology.owl")  # list[OWLAxiom]
reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()
```

### Q: Can I export the reasoned hierarchy?

A: Dump it in Functional-Style Syntax.

```python
import io, sys

reasoner = reasoner_from_axioms([OWLSubClassOfAxiom(Dog, Animal)])
reasoner.precompute_inferences()
reasoner.dump_hierarchies(sys.stdout, classes=True)
reasoner.dispose()
```

### Q: Can I use PyHermit with pandas/numpy?

A: Yes.

```python
axioms = [
    OWLSubClassOfAxiom(Dog, Animal),
    OWLClassAssertionAxiom(OWLNamedIndividual(NS + "fido"), Dog),
]
reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

# Collect class membership rows
rows = []
for concept in reasoner.dl_ontology.all_atomic_concepts:
    for inst in reasoner.get_instances(concept):
        rows.append({"class": concept.iri, "instance": inst.iri})

# import pandas as pd; df = pd.DataFrame(rows)
print(sorted((r["class"], r["instance"]) for r in rows))
reasoner.dispose()
```

### Q: Can I integrate PyHermit with a web service?

A: Yes. Compile the reasoner once at startup and answer queries from it.

```python
# doc-sample: skip (illustrative server sketch)
from flask import Flask, request, jsonify
from hermit.parser import load_ontology

app = Flask(__name__)
axioms = load_ontology("ontology.owl")
reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

@app.route("/instances", methods=["POST"])
def instances():
    concept = AtomicConcept.create(request.json["class_iri"])
    result = [i.iri for i in reasoner.get_instances(concept)]
    return jsonify({"instances": result})
```

## Troubleshooting

### Q: I get "UnsupportedDatatypeException". What does this mean?

A: The ontology uses a datatype the reasoner does not implement. Stick to the OWL 2 datatypes (`xsd:string`, `xsd:integer`, `xsd:decimal`, `xsd:float`, `xsd:double`, `xsd:boolean`, `xsd:dateTime`, `xsd:anyURI`, `xsd:base64Binary`, `xsd:hexBinary`, and so on), or construct the clausifier with `OWLClausification(ignore_unsupported_datatypes=True)` to skip them.

### Q: My reasoner hangs or runs very slowly

A: Try these steps.

1. Check the ontology shape: `reasoner.stats`. Non-Horn ontologies backtrack.
2. Reduce axioms: remove rules you do not query.
3. Set a task timeout: `Configuration.individual_task_timeout` (in milliseconds).
4. Profile: time `is_consistent()` and `precompute_inferences()` separately.

### Q: How do I debug why an inference did not happen?

A: Walk the chain. See the [Debugging Guide](./recipes/debugging.md#problem-4-wrong-inference).

```python
reasoner = reasoner_from_axioms([OWLSubClassOfAxiom(Dog, Animal)])
dog = AtomicConcept.create(NS + "Dog")
animal = AtomicConcept.create(NS + "Animal")

# 1. Is the class satisfiable?
print(f"Dog satisfiable: {reasoner.is_satisfiable(dog)}")

# 2. Does the subsumption hold?
print(f"Dog is a subclass of Animal: {reasoner.is_sub_class_of(dog, animal)}")
reasoner.dispose()
```

## License and community

### Q: Can I use PyHermit commercially?

A: Yes. The LGPL-3.0-or-later license allows commercial use; if you modify PyHermit itself, those modifications must be shared under the same license, but linking it into your own application does not.

### Q: Where do I report bugs?

A: Open an issue on [GitHub](https://github.com/TigreGotico/pyhermit/issues).

For more detail, see the [full documentation](./index.md).

---
[← First Program](first-program.md) · [Home](index.md)
