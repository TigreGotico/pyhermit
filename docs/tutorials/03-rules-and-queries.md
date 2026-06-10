# Tutorial 3b: Rules and Complex Queries

Learn to express rule-like axioms and perform advanced queries over your ontology.

## What You'll Learn

- Writing rule-based axioms
- Complex class expressions (`OWLObjectUnionOf`, `OWLObjectIntersectionOf`)
- Performing advanced queries
- Understanding inference chains
- Debugging reasoning

Standard setup:

```python
from hermit import Reasoner
from hermit.model import AtomicConcept, AtomicRole, Individual
from hermit.owl_model.class_expression import (
    OWLClass,
    OWLObjectComplementOf,
    OWLObjectIntersectionOf,
    OWLObjectSomeValuesFrom,
    OWLObjectUnionOf,
)
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

## Part 1: Rule-Based Axioms

Rules in OWL 2 DL are expressed through class axioms. "Every teacher or
student is a university member" becomes a subclass axiom with a **union on
the left-hand side**:

```python
Teacher = OWLClass(NS + "Teacher")
Student = OWLClass(NS + "Student")
UniversityMember = OWLClass(NS + "UniversityMember")

# Rule: Teacher ⊔ Student ⊑ UniversityMember
axioms = [
    OWLSubClassOfAxiom(OWLObjectUnionOf([Teacher, Student]), UniversityMember),
]

# Test reasoning
alice = OWLNamedIndividual(NS + "alice")
axioms.append(OWLClassAssertionAxiom(alice, Teacher))

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

member = AtomicConcept.create(NS + "UniversityMember")
alice_h = Individual.create(NS + "alice")

print("Is alice a UniversityMember?", reasoner.has_type(alice_h, member))  # True (inferred!)

reasoner.dispose()
```

**Output:**
```
Is alice a UniversityMember? True
```

## Part 2: Complex Class Expressions

Combine multiple concepts. An **equivalence** axiom makes the rule
bidirectional: anyone who is Young and Single is *recognized* as Eligible:

```python
Young = OWLClass(NS + "Young")
Single = OWLClass(NS + "Single")
Eligible = OWLClass(NS + "Eligible")

# Rule: Eligible ≡ Young ⊓ Single
axioms = [
    OWLEquivalentClassesAxiom([Eligible, OWLObjectIntersectionOf([Young, Single])]),
]

john = OWLNamedIndividual(NS + "john")
axioms += [
    OWLClassAssertionAxiom(john, Young),
    OWLClassAssertionAxiom(john, Single),
]

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

eligible = AtomicConcept.create(NS + "Eligible")
john_h = Individual.create(NS + "john")

print("Is john eligible?", reasoner.has_type(john_h, eligible))  # True (inferred!)

reasoner.dispose()
```

**Output:**
```
Is john eligible? True
```

With `OWLSubClassOfAxiom(Eligible, ...)` instead, the rule would only work
top-down (every Eligible is Young and Single) — the reasoner could never
*conclude* that john is Eligible.

## Part 3: Implicit Rules Through Restrictions

Property restrictions create implicit rules:

```python
Person = OWLClass(NS + "Person")
Parent = OWLClass(NS + "Parent")
Childless = OWLClass(NS + "Childless")
hasChild = OWLObjectProperty(NS + "hasChild")

axioms = [
    # Rule 1: Parent ≡ ∃hasChild.Person — having a child makes you a Parent
    OWLEquivalentClassesAxiom([Parent, OWLObjectSomeValuesFrom(hasChild, Person)]),
    # Rule 2: Childless ⊑ ¬Parent
    OWLSubClassOfAxiom(Childless, OWLObjectComplementOf(Parent)),
]

mary = OWLNamedIndividual(NS + "mary")
junior = OWLNamedIndividual(NS + "junior")
ivy = OWLNamedIndividual(NS + "ivy")

axioms += [
    OWLClassAssertionAxiom(junior, Person),
    OWLObjectPropertyAssertionAxiom(mary, hasChild, junior),
    OWLClassAssertionAxiom(ivy, Childless),
]

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

parent = AtomicConcept.create(NS + "Parent")
print("Is mary a Parent?", reasoner.has_type(Individual.create(NS + "mary"), parent))  # True
print("Is ivy a Parent?", reasoner.has_type(Individual.create(NS + "ivy"), parent))    # False
print(f"Parents found: {len(reasoner.get_instances(parent))}")  # 1

reasoner.dispose()
```

## Part 4: Advanced Queries

Query the ontology in sophisticated ways:

```python
Employee = OWLClass(NS + "Employee")
Manager = OWLClass(NS + "Manager")
Executive = OWLClass(NS + "Executive")
Department = OWLClass(NS + "Department")

manages = OWLObjectProperty(NS + "manages")
worksIn = OWLObjectProperty(NS + "worksIn")

alice = OWLNamedIndividual(NS + "alice")
bob = OWLNamedIndividual(NS + "bob")
charlie = OWLNamedIndividual(NS + "charlie")
sales_dept = OWLNamedIndividual(NS + "sales_dept")

axioms = [
    # Hierarchy
    OWLSubClassOfAxiom(Employee, Person),
    OWLSubClassOfAxiom(Manager, Employee),
    OWLSubClassOfAxiom(Executive, Manager),
    # Individuals
    OWLClassAssertionAxiom(alice, Executive),
    OWLClassAssertionAxiom(bob, Manager),
    OWLClassAssertionAxiom(charlie, Employee),
    OWLClassAssertionAxiom(sales_dept, Department),
    # Relationships
    OWLObjectPropertyAssertionAxiom(alice, manages, bob),
    OWLObjectPropertyAssertionAxiom(bob, manages, charlie),
    OWLObjectPropertyAssertionAxiom(charlie, worksIn, sales_dept),
]

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

employee = AtomicConcept.create(NS + "Employee")
executive = AtomicConcept.create(NS + "Executive")
manages_h = AtomicRole.create(NS + "manages")

# Query 1: All employees (includes managers and executives)
print(f"All employees: {len(reasoner.get_instances(employee))}")  # 3

# Query 2: All executives
print(f"Executives: {len(reasoner.get_instances(executive))}")  # 1

# Query 3: Does bob manage charlie?
bob_h = Individual.create(NS + "bob")
charlie_h = Individual.create(NS + "charlie")
print("Bob manages charlie:", reasoner.has_role_relationship(bob_h, manages_h, charlie_h))  # True

# Query 4: Print the inferred class hierarchy
import sys
reasoner.dump_hierarchies(sys.stdout, classes=True)

reasoner.dispose()
```

**Output:**
```
All employees: 3
Executives: 1
Bob manages charlie: True
SubClassOf( <http://example.org/Employee> <http://example.org/Person> )
SubClassOf( <http://example.org/Executive> <http://example.org/Manager> )
SubClassOf( <http://example.org/Manager> <http://example.org/Employee> )
```

## Part 5: Reasoning Chains

Understanding how the reasoner derives facts:

```python
Animal = OWLClass(NS + "Animal")
Mammal = OWLClass(NS + "Mammal")
Dog = OWLClass(NS + "Dog")
Poodle = OWLClass(NS + "Poodle")

fido = OWLNamedIndividual(NS + "fido")

axioms = [
    OWLSubClassOfAxiom(Mammal, Animal),
    OWLSubClassOfAxiom(Dog, Mammal),
    OWLSubClassOfAxiom(Poodle, Dog),
    OWLClassAssertionAxiom(fido, Poodle),
]

reasoner = reasoner_from_axioms(axioms)
reasoner.precompute_inferences()

animal = AtomicConcept.create(NS + "Animal")
fido_h = Individual.create(NS + "fido")

# Query: Is fido an animal?
print("Is fido an Animal?", reasoner.has_type(fido_h, animal))  # True

# The chain:
# Fido is a Poodle (asserted)
# → Fido is a Dog (from Poodle ⊑ Dog)
# → Fido is a Mammal (from Dog ⊑ Mammal)
# → Fido is an Animal (from Mammal ⊑ Animal)

# Most specific type only
direct = reasoner.get_types(fido_h, direct=True)
print("Fido's direct type:", sorted(c.iri.split('/')[-1] for c in direct))  # ['Poodle']

# All inferred types
all_types = reasoner.get_types(fido_h)
print(f"All of Fido's types: {sorted(c.iri.split('/')[-1] for c in all_types)}")

reasoner.dispose()
```

## Part 6: Debugging Inconsistencies

When your ontology has contradictions:

```python
axioms = [
    OWLDisjointClassesAxiom([Parent, Childless]),
    # Contradiction: alice is both
    OWLClassAssertionAxiom(alice, Parent),
    OWLClassAssertionAxiom(alice, Childless),
]

reasoner = reasoner_from_axioms(axioms)

is_consistent = reasoner.is_consistent()
print(f"Ontology is consistent: {is_consistent}")  # False

if not is_consistent:
    print("WARNING: Ontology contains a contradiction!")
    print("Check disjointness rules and class definitions")

reasoner.dispose()
```

## Query API Reference

```python
# doc-sample: skip (signature reference)
# Get all instances of a class
instances = reasoner.get_instances(concept)

# Get direct instances only
direct = reasoner.get_instances(concept, direct=True)

# Get types of an individual
types = reasoner.get_types(individual)
direct_types = reasoner.get_types(individual, direct=True)

# Subsumption / equivalence / disjointness between classes
reasoner.is_sub_class_of(sub, sup)
reasoner.is_equivalent(c1, c2)
reasoner.is_disjoint(c1, c2)

# Instance and role checks
reasoner.has_type(individual, concept)
reasoner.has_role_relationship(subject, role, obj)

# Consistency and satisfiability
reasoner.is_consistent()
reasoner.is_satisfiable(concept)

# Hierarchy output
reasoner.dump_hierarchies(sys.stdout, classes=True)
```

## Key Takeaways

1. **Rules** are expressed through class axioms and restrictions
2. **Union on the left** of ⊑ means "any of these implies…"
3. **Equivalence axioms** make definitions bidirectional — required for the reasoner to *recognize* members
4. **Queries** reveal inferred facts
5. **Consistency checking** validates your ontology

## Try This!

Create a medical ontology with:
- Symptoms (fever, cough, headache)
- Diseases (flu, cold, pneumonia)
- A definition `FluCandidate ≡ ∃hasSymptom.Fever ⊓ ∃hasSymptom.Cough`
- A patient with fever and cough — is the patient a FluCandidate?

## Next Steps

- **[Tutorial 4: Advanced Reasoning](./04-advanced-reasoning.md)** — Optimization and performance
- **[Concepts](../concepts.md)** — Deep dive into OWL and DL theory
- **[API Reference](../api/core.md)** — Complete API documentation
