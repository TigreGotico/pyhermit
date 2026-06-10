# Core API Reference

Complete reference for the main PyHermit APIs.

PyHermit has two layers:

- **`hermit.owl_model`** — OWL-API-style entities and axioms used to *build*
  ontologies (also what `load_ontology` returns).
- **`hermit.model`** — the internal DL model. `Reasoner` queries take these
  lightweight, interned handles: `AtomicConcept`, `AtomicRole`, `Individual`.

Axioms are compiled into a reasoner through the normalization →
clausification pipeline (see [below](#clausification-pipeline)).

## Main Classes

### Reasoner

The main entry point for reasoning operations. Source: `src/hermit/reasoner.py`.

```python
# doc-sample: skip (signature reference)
from hermit import Reasoner, Configuration

reasoner = Reasoner(dl_ontology)                 # DLOntology from clausification
reasoner = Reasoner(dl_ontology, Configuration())
```

#### Methods

**Initialization & Control**

```python
# doc-sample: skip (signature reference)
# Precompute inferences (recommended before batches of queries)
reasoner.precompute_inferences(
    class_hierarchy=True,             # default
    object_property_hierarchy=False,
    data_property_hierarchy=False,
)

# Dispose (release tableau resources; the reasoner is unusable afterwards)
reasoner.dispose()

# Interrupt a long-running task from another thread
reasoner.interrupt()
```

**TBox (Class) Reasoning** — arguments are `AtomicConcept` handles

```python
# doc-sample: skip (signature reference)
reasoner.is_consistent()              # bool — whole ontology
reasoner.is_satisfiable(concept)      # bool — can the class have instances?
reasoner.is_sub_class_of(sub, sup)    # bool
reasoner.is_equivalent(c1, c2)        # bool
reasoner.is_disjoint(c1, c2)          # bool
```

**Role (Property) Reasoning** — arguments are `AtomicRole` / `Role` handles

```python
# doc-sample: skip (signature reference)
reasoner.is_sub_role_of(sub, sup)     # bool
reasoner.is_equivalent_role(r1, r2)   # bool
reasoner.is_disjoint_role(r1, r2)     # bool
reasoner.is_functional(role)          # bool
```

**ABox (Individual) Reasoning** — `Individual` + `AtomicConcept` handles

```python
# doc-sample: skip (signature reference)
reasoner.has_type(individual, concept)               # bool (inferred included)
reasoner.has_type(individual, concept, direct=True)  # most-specific only

reasoner.get_instances(concept)                # set[Individual]
reasoner.get_instances(concept, direct=True)   # direct instances only

reasoner.get_types(individual)                 # set[AtomicConcept]
reasoner.get_types(individual, direct=True)    # most-specific types only

reasoner.has_role_relationship(subject, role, obj)   # bool
reasoner.is_same_individual(i1, i2)                  # bool
```

**Classification & Output**

```python
# doc-sample: skip (signature reference)
reasoner.classify_classes()             # build the concept hierarchy
reasoner.classify_object_properties()   # build the object-role hierarchy
reasoner.classify_data_properties()     # build the data-role hierarchy

import sys
reasoner.dump_hierarchies(sys.stdout, classes=True)   # compact SubClassOf lines
reasoner.print_hierarchies(sys.stdout, classes=True)  # full FSS ontology

reasoner.stats   # dict: clauses, atomic_concepts, individuals, is_horn, ...
```

---

### Query Handles (`hermit.model`)

`Reasoner` methods take interned handles created from IRIs:

```python
from hermit.model import AtomicConcept, AtomicRole, Individual, InverseRole

person = AtomicConcept.create("http://example.org/Person")
has_pet = AtomicRole.create("http://example.org/hasPet")
alice = Individual.create("http://example.org/alice")
inv = InverseRole.create(has_pet)   # query the inverse direction

print(person.iri)     # the IRI string
print(AtomicConcept.THING.iri)   # owl:Thing
print(AtomicConcept.NOTHING.iri)  # owl:Nothing
```

Handles are value-interned: `AtomicConcept.create(iri)` returns the same
object for the same IRI.

---

### DLOntology

The compiled form of an ontology: DL clauses plus fact sets. Produced by
`OWLClausification.clausify()`; you rarely construct one by hand.

```python
# doc-sample: skip (signature reference)
dl_ontology.ontology_iri          # str | None
dl_ontology.dl_clauses            # frozenset[DLClause]
dl_ontology.get_positive_facts()  # ABox atoms
dl_ontology.all_atomic_concepts   # frozenset[AtomicConcept]
dl_ontology.all_individuals       # frozenset[Individual]
```

For advanced use, `DLOntology` (with `DLClause`, `Atom`, `Variable` from
`hermit.model`) can be built directly — see the `examples/` scripts, which
construct ontologies at this level.

---

## Building Ontologies (`hermit.owl_model`)

### Entities

```python
from hermit.owl_model.class_expression import OWLClass
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_property import OWLDataProperty, OWLObjectProperty

Person = OWLClass("http://example.org/Person")
alice = OWLNamedIndividual("http://example.org/alice")
hasChild = OWLObjectProperty("http://example.org/hasChild")
hasAge = OWLDataProperty("http://example.org/hasAge")
```

### Class Expressions

From `hermit.owl_model.class_expression`:

| Constructor | DL syntax | Meaning |
|---|---|---|
| `OWLObjectIntersectionOf([A, B])` | A ⊓ B | both A and B |
| `OWLObjectUnionOf([A, B])` | A ⊔ B | A or B |
| `OWLObjectComplementOf(A)` | ¬A | not A |
| `OWLObjectSomeValuesFrom(p, A)` | ∃p.A | has some p-filler in A |
| `OWLObjectAllValuesFrom(p, A)` | ∀p.A | all p-fillers in A |
| `OWLObjectMinCardinality(n, p, A)` | ≥n p.A | at least n fillers |
| `OWLObjectMaxCardinality(n, p, A)` | ≤n p.A | at most n fillers |
| `OWLObjectExactCardinality(n, p, A)` | =n p.A | exactly n fillers |
| `OWLObjectHasValue(p, a)` | ∃p.{a} | filler is the individual a |
| `OWLObjectHasSelf(p)` | ∃p.Self | relates to itself |
| `OWLObjectOneOf([a, b])` | {a, b} | enumerated class |
| `OWLDataSomeValuesFrom(d, range)` | ∃d.range | data filler in range |
| `OWLDataAllValuesFrom(d, range)` | ∀d.range | all data fillers in range |
| `OWLThing` / `OWLNothing` | ⊤ / ⊥ | top / bottom class |

### Axioms

From `hermit.owl_model.owl_axiom` (the most common ones):

```python
# doc-sample: skip (signature reference)
OWLSubClassOfAxiom(sub_class, super_class)
OWLEquivalentClassesAxiom([ce1, ce2])
OWLDisjointClassesAxiom([ce1, ce2, ...])
OWLDisjointUnionAxiom(cls, [ce1, ce2, ...])

OWLClassAssertionAxiom(individual, class_expression)   # individual FIRST
OWLObjectPropertyAssertionAxiom(subject, property_, object_)
OWLNegativeObjectPropertyAssertionAxiom(subject, property_, object_)
OWLDataPropertyAssertionAxiom(subject, property_, literal)
OWLNegativeDataPropertyAssertionAxiom(subject, property_, literal)
OWLSameIndividualAxiom([i1, i2])
OWLDifferentIndividualsAxiom([i1, i2, ...])

OWLSubObjectPropertyOfAxiom(sub_property, super_property)
OWLSubPropertyChainAxiom([p1, p2], super_property)
OWLInverseObjectPropertiesAxiom(first, second)
OWLEquivalentObjectPropertiesAxiom([p1, p2])
OWLDisjointObjectPropertiesAxiom([p1, p2])
OWLObjectPropertyDomainAxiom(property_, domain_ce)
OWLObjectPropertyRangeAxiom(property_, range_ce)

OWLFunctionalObjectPropertyAxiom(p)
OWLInverseFunctionalObjectPropertyAxiom(p)
OWLTransitiveObjectPropertyAxiom(p)
OWLSymmetricObjectPropertyAxiom(p)
OWLAsymmetricObjectPropertyAxiom(p)
OWLReflexiveObjectPropertyAxiom(p)
OWLIrreflexiveObjectPropertyAxiom(p)

OWLSubDataPropertyOfAxiom(sub, sup)
OWLFunctionalDataPropertyAxiom(d)
OWLDataPropertyDomainAxiom(d, domain_ce)
OWLDataPropertyRangeAxiom(d, data_range)
OWLHasKeyAxiom(ce, [p1, d1, ...])
```

### Literals and Data Ranges

`OWLLiteral` infers the OWL datatype from the Python value:

```python
from datetime import date, datetime
from hermit.owl_model.owl_literal import OWLLiteral

OWLLiteral("Alice")              # xsd:string
OWLLiteral(30)                   # xsd:integer
OWLLiteral(3.14)                 # xsd:double
OWLLiteral(True)                 # xsd:boolean
OWLLiteral(date(1990, 1, 15))    # xsd:date
OWLLiteral(datetime(2020, 1, 15, 12, 0))  # xsd:dateTime
```

Facet-restricted ranges support value comparisons:

```python
from hermit.owl_model.class_expression import OWLDatatypeRestriction, OWLFacetRestriction
from hermit.owl_model.owl_literal import IntegerOWLDatatype
from hermit.owl_model.vocab import OWLFacet

# integer values from 0 to 150
age_range = OWLDatatypeRestriction(IntegerOWLDatatype, [
    OWLFacetRestriction(OWLFacet.MIN_INCLUSIVE, OWLLiteral(0)),
    OWLFacetRestriction(OWLFacet.MAX_INCLUSIVE, OWLLiteral(150)),
])
```

---

## Complete Example

```python
from hermit import Reasoner
from hermit.model import AtomicConcept, Individual
from hermit.owl_model.class_expression import OWLClass, OWLObjectSomeValuesFrom
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_property import OWLDataProperty, OWLObjectProperty
from hermit.owl_model.owl_literal import OWLLiteral
from hermit.owl_model.owl_axiom import (
    OWLClassAssertionAxiom,
    OWLDataPropertyAssertionAxiom,
    OWLDisjointClassesAxiom,
    OWLObjectPropertyAssertionAxiom,
    OWLSubClassOfAxiom,
)
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization

NS = "http://example.org/"

# Define entities
Person = OWLClass(NS + "Person")
Parent = OWLClass(NS + "Parent")
Child = OWLClass(NS + "Child")
hasChild = OWLObjectProperty(NS + "hasChild")
hasAge = OWLDataProperty(NS + "hasAge")
alice = OWLNamedIndividual(NS + "alice")
bob = OWLNamedIndividual(NS + "bob")

# Collect axioms
axioms = [
    # Rules
    OWLSubClassOfAxiom(Parent, Person),
    OWLSubClassOfAxiom(Child, Person),
    OWLSubClassOfAxiom(Parent, OWLObjectSomeValuesFrom(hasChild, Child)),
    OWLDisjointClassesAxiom([Parent, Child]),
    # Facts
    OWLClassAssertionAxiom(alice, Parent),
    OWLClassAssertionAxiom(bob, Child),
    OWLObjectPropertyAssertionAxiom(alice, hasChild, bob),
    OWLDataPropertyAssertionAxiom(alice, hasAge, OWLLiteral(40)),
    OWLDataPropertyAssertionAxiom(bob, hasAge, OWLLiteral(10)),
]

# Compile
normalized = OWLNormalization().process_ontology(axioms)
dl_ontology = OWLClausification().clausify(normalized, ontology_iri="urn:example:family")
reasoner = Reasoner(dl_ontology)
reasoner.precompute_inferences()

# Query
person = AtomicConcept.create(NS + "Person")
parent = AtomicConcept.create(NS + "Parent")
child = AtomicConcept.create(NS + "Child")
alice_h = Individual.create(NS + "alice")
bob_h = Individual.create(NS + "bob")

print(f"Is alice a Person? {reasoner.has_type(alice_h, person)}")  # True (inferred)
print(f"Is bob a Person? {reasoner.has_type(bob_h, person)}")      # True (inferred)
print(f"All Parents: {sorted(i.iri for i in reasoner.get_instances(parent))}")
print(f"All Children: {sorted(i.iri for i in reasoner.get_instances(child))}")

reasoner.dispose()
```

---

## Clausification Pipeline

### OWLNormalization

Transforms raw `OWLAxiom` objects into `NormalizedAxioms`. Source: `src/hermit/structural/owl_normalization.py`.

```python
# doc-sample: skip (signature reference)
from hermit.structural.owl_normalization import OWLNormalization

normalization = OWLNormalization()
normalized = normalization.process_ontology(axioms)  # Iterable[OWLAxiom] -> NormalizedAxioms
```

`process_ontology()` populates, among other collections:
- `normalized.simple_object_property_inclusions` — from `SubObjectPropertyOf` and `InverseObjectProperties` axioms
- `normalized.complex_object_property_inclusions` — from `TransitiveObjectProperty` and `SubPropertyChainOf` axioms

### OWLClausification

Converts `NormalizedAxioms` to a `DLOntology`. Source: `src/hermit/structural/owl_clausification.py`.

```python
# doc-sample: skip (signature reference)
from hermit.structural.owl_clausification import OWLClausification

clausification = OWLClausification()
dl_ontology = clausification.clausify(normalized, ontology_iri="urn:example:onto")

# Tolerate datatypes outside the OWL 2 set:
clausification = OWLClausification(ignore_unsupported_datatypes=True)
```

`clausify()` calls `ObjectPropertyInclusionManager.rewrite_axioms()` before producing DL clauses. This raises `ValueError` for any OWL 2 non-simplicity violation — see below.

### ObjectPropertyInclusionManager

Detects non-simple properties and validates OWL 2 constraints. Source: `src/hermit/structural/object_property_inclusion_manager.py`.

A property is **non-simple** if it:
1. Appears as the superrole of a transitive axiom or role chain
2. Is a superrole of a non-simple property via `SubObjectPropertyOf`
3. Is the inverse of a non-simple property

`rewrite_axioms()` raises `ValueError` if a non-simple property appears in:
- `AsymmetricObjectProperty`
- `IrreflexiveObjectProperty`
- `DisjointObjectProperties`
- `ObjectMinCardinality`, `ObjectMaxCardinality`, `ObjectExactCardinality`
- `ObjectHasSelf`

### load_ontology

Loads OWL documents (RDF/XML, OWL/XML, Functional-Style Syntax) via the
stdlib readers. Source: `src/hermit/parser.py`.

```python
# doc-sample: skip (needs an .owl file on disk)
from hermit.parser import load_ontology, load_ontology_from_string

axioms = load_ontology("path/to/ontology.owl")        # list[OWLAxiom]
axioms = load_ontology_from_string(document_text)     # parse from memory
```

Raises `FileNotFoundError` if the path does not exist, `ValueError` if the file cannot be parsed.

### Non-Simplicity Errors (ValueError)

`OWLClausification.clausify()` raises `ValueError` with a message of the form:

```
Non-simple property '<iri>' cannot be asymmetric (OWL 2 violation)
Non-simple property '<iri>' cannot be irreflexive (OWL 2 violation)
Non-simple property '<iri>' cannot be in disjoint properties axiom (OWL 2 violation)
Non-simple property '<iri>' or its inverse appears in a cardinality restriction (OWL 2 violation)
Non-simple property '<iri>' appears in a Self restriction (OWL 2 violation)
```

---

## Configuration

```python
from hermit import Configuration

config = Configuration()
config.individual_task_timeout = 30_000   # ms per reasoning task (-1 = none)
```

Other fields control blocking strategy, existential expansion strategy,
tableau monitoring, and fresh-entity policy — see
`src/hermit/configuration.py` for the full set.

---

## See Also

- **[Tutorials](../tutorials/01-build-ontology.md)** — Guided examples
- **[First Program](../first-program.md)** — The canonical build-then-query workflow
