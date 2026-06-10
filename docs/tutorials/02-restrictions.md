# Tutorial 2: Restrictions and Cardinality

Learn how to constrain properties with cardinality and value restrictions.

## What You'll Learn

- Existential restrictions (∃ — `OWLObjectSomeValuesFrom`)
- Universal restrictions (∀ — `OWLObjectAllValuesFrom`)
- Cardinality constraints (`OWLObjectMinCardinality`, `OWLObjectMaxCardinality`)
- How restrictions interact with reasoning

As in every tutorial, we use the `reasoner_from_axioms` helper from
[First Program](../first-program.md):

```python
from hermit import Reasoner
from hermit.model import AtomicConcept, Individual
from hermit.owl_model.class_expression import (
    OWLClass,
    OWLObjectAllValuesFrom,
    OWLObjectIntersectionOf,
    OWLObjectMaxCardinality,
    OWLObjectMinCardinality,
    OWLObjectSomeValuesFrom,
    OWLThing,
)
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_property import OWLObjectProperty
from hermit.owl_model.owl_axiom import (
    OWLClassAssertionAxiom,
    OWLDifferentIndividualsAxiom,
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

## Part 1: Existential Restrictions (SomeValuesFrom)

An existential restriction `∃hasChild.Person` describes "things with at least
one child that is a Person". Defining a class as **equivalent** to a
restriction lets the reasoner *recognize* individuals:

```python
Person = OWLClass(NS + "Person")
Parent = OWLClass(NS + "Parent")
hasChild = OWLObjectProperty(NS + "hasChild")

# Parent ≡ ∃hasChild.Person  — anything with a Person child IS a Parent
axioms = [
    OWLEquivalentClassesAxiom([Parent, OWLObjectSomeValuesFrom(hasChild, Person)]),
]

# alice has a child; john does not
alice = OWLNamedIndividual(NS + "alice")
bob = OWLNamedIndividual(NS + "bob")
john = OWLNamedIndividual(NS + "john")

axioms += [
    OWLClassAssertionAxiom(alice, Person),
    OWLClassAssertionAxiom(bob, Person),
    OWLClassAssertionAxiom(john, Person),
    OWLObjectPropertyAssertionAxiom(alice, hasChild, bob),
]

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

parent = AtomicConcept.create(NS + "Parent")
alice_h = Individual.create(NS + "alice")
john_h = Individual.create(NS + "john")

print("Is alice a Parent?", reasoner.has_type(alice_h, parent))  # True (inferred!)
print("Is john a Parent?", reasoner.has_type(john_h, parent))    # False (unknown)

reasoner.dispose()
```

**Output:**
```
Is alice a Parent? True
Is john a Parent? False
```

Note the asymmetry: alice is *inferred* to be a Parent, while john is simply
*not known* to be one — OWL reasoning is open-world.

## Part 2: Universal Restrictions (AllValuesFrom)

Universal restrictions constrain **all** values of a property. They propagate
types onto property fillers:

```python
GoodTeacher = OWLClass(NS + "GoodTeacher")
Competent = OWLClass(NS + "Competent")
teaches = OWLObjectProperty(NS + "teaches")

# GoodTeacher ⊑ ∀teaches.Competent — everyone a GoodTeacher teaches is Competent
axioms = [
    OWLSubClassOfAxiom(GoodTeacher, OWLObjectAllValuesFrom(teaches, Competent)),
]

prof = OWLNamedIndividual(NS + "prof_smith")
student1 = OWLNamedIndividual(NS + "student1")

axioms += [
    OWLClassAssertionAxiom(prof, GoodTeacher),
    OWLObjectPropertyAssertionAxiom(prof, teaches, student1),
]

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

competent = AtomicConcept.create(NS + "Competent")
student1_h = Individual.create(NS + "student1")

# The reasoner propagates the restriction onto student1:
print("Is student1 Competent?", reasoner.has_type(student1_h, competent))  # True (inferred!)

reasoner.dispose()
```

**Output:**
```
Is student1 Competent? True
```

## Part 3: Cardinality Restrictions

Min- and max-cardinality limit how many distinct fillers a property may have:

```python
Pet = OWLClass(NS + "Pet")
PetOwner = OWLClass(NS + "PetOwner")
hasPet = OWLObjectProperty(NS + "hasPet")

# PetOwner ⊑ ≥1 hasPet.Pet  (at least one pet)
axioms = [
    OWLSubClassOfAxiom(PetOwner, OWLObjectMinCardinality(1, hasPet, Pet)),
]

reasoner = reasoner_from_axioms(axioms)
pet_owner = AtomicConcept.create(NS + "PetOwner")
print("Is PetOwner satisfiable?", reasoner.is_satisfiable(pet_owner))  # True
reasoner.dispose()
```

Max-cardinality violations make the ontology **inconsistent** — but only when
the fillers are known to be different (OWL has no unique-name assumption):

```python
Monogamous = OWLClass(NS + "Monogamous")
hasSpouse = OWLObjectProperty(NS + "hasSpouse")

dave = OWLNamedIndividual(NS + "dave")
eve = OWLNamedIndividual(NS + "eve")
fran = OWLNamedIndividual(NS + "fran")

axioms = [
    # Monogamous ⊑ ≤1 hasSpouse.Thing
    OWLSubClassOfAxiom(Monogamous, OWLObjectMaxCardinality(1, hasSpouse, OWLThing)),
    OWLClassAssertionAxiom(dave, Monogamous),
    OWLObjectPropertyAssertionAxiom(dave, hasSpouse, eve),
    OWLObjectPropertyAssertionAxiom(dave, hasSpouse, fran),
]

# Without DifferentIndividuals the reasoner can merge eve and fran:
reasoner = reasoner_from_axioms(axioms)
print("Consistent (eve, fran may be equal)?", reasoner.is_consistent())  # True
reasoner.dispose()

# Declare them distinct and the constraint is violated:
axioms.append(OWLDifferentIndividualsAxiom([eve, fran]))
reasoner = reasoner_from_axioms(axioms)
print("Consistent (eve ≠ fran)?", reasoner.is_consistent())  # False
reasoner.dispose()
```

**Output:**
```
Consistent (eve, fran may be equal)? True
Consistent (eve ≠ fran)? False
```

## Part 4: Combining Restrictions

Complex restrictions model real-world constraints:

```python
Supervisor = OWLClass(NS + "Supervisor")
Employee = OWLClass(NS + "Employee")
supervises = OWLObjectProperty(NS + "supervises")

# Supervisor ⊑ (≥1 supervises.Employee) ⊓ (≤10 supervises.Employee)
axioms = [
    OWLSubClassOfAxiom(
        Supervisor,
        OWLObjectIntersectionOf([
            OWLObjectMinCardinality(1, supervises, Employee),
            OWLObjectMaxCardinality(10, supervises, Employee),
        ]),
    ),
]

supervisor = OWLNamedIndividual(NS + "alice")
employees = [OWLNamedIndividual(f"{NS}employee{i}") for i in range(5)]

axioms.append(OWLClassAssertionAxiom(supervisor, Supervisor))
for emp in employees:
    axioms.append(OWLClassAssertionAxiom(emp, Employee))
    axioms.append(OWLObjectPropertyAssertionAxiom(supervisor, supervises, emp))

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

print("Consistent with 5 supervisees?", reasoner.is_consistent())  # True

reasoner.dispose()
```

## Common Patterns

These fragments assume classes/properties defined as above.

### 1. "At Least One" (Existential)
```python
# Every Parent has at least one Person child
OWLSubClassOfAxiom(Parent, OWLObjectSomeValuesFrom(hasChild, Person))
```

### 2. "All Values" (Universal)
```python
# All of a Person's spouses are Persons
OWLSubClassOfAxiom(Person, OWLObjectAllValuesFrom(hasSpouse, Person))
```

### 3. "Exactly N"
```python
# Every Person has exactly 2 biological parents
hasParent = OWLObjectProperty(NS + "hasParent")
OWLSubClassOfAxiom(
    Person,
    OWLObjectIntersectionOf([
        OWLObjectMinCardinality(2, hasParent, Person),
        OWLObjectMaxCardinality(2, hasParent, Person),
    ]),
)
```

(`OWLObjectExactCardinality(2, hasParent, Person)` is the shorthand.)

### 4. "At Most N"
```python
# Each person has at most 1 spouse
OWLSubClassOfAxiom(Person, OWLObjectMaxCardinality(1, hasSpouse, Person))
```

## Key Takeaways

1. **Existential restrictions (∃)** assert something exists
2. **Universal restrictions (∀)** constrain all values and propagate types
3. **Cardinality** limits how many fillers a property can have
4. **Equivalence axioms** let the reasoner *recognize* members of a defined class
5. Cardinality clashes need `OWLDifferentIndividualsAxiom` — no unique-name assumption

## Try This!

Create an ontology for a university with:
- Students (at least 1 course, not more than 5)
- Professors (everything they teach is a Course)
- Courses (exactly 1 professor)

## Next Steps

- **[Tutorial 3: Rules and Queries](./03-rules-and-queries.md)** — Complex class expressions
- **[Tutorial 4: Advanced Reasoning](./04-advanced-reasoning.md)** — Reasoning strategies and performance
- **[API Reference](../api/core.md)** — Restriction classes API
