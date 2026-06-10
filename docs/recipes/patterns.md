# Common Patterns

Reusable patterns and idioms for ontology design and querying.

All patterns share this setup (the helper from
[First Program](../first-program.md) plus common imports):

```python
from hermit import Reasoner
from hermit.model import AtomicConcept, AtomicRole, Individual
from hermit.owl_model.class_expression import (
    OWLClass,
    OWLObjectAllValuesFrom,
    OWLObjectComplementOf,
    OWLObjectIntersectionOf,
    OWLObjectSomeValuesFrom,
    OWLObjectUnionOf,
    OWLThing,
)
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_property import OWLDataProperty, OWLObjectProperty
from hermit.owl_model.owl_literal import OWLLiteral
from hermit.owl_model.owl_axiom import (
    OWLClassAssertionAxiom,
    OWLDataPropertyAssertionAxiom,
    OWLEquivalentClassesAxiom,
    OWLInverseObjectPropertiesAxiom,
    OWLNegativeDataPropertyAssertionAxiom,
    OWLObjectPropertyAssertionAxiom,
    OWLSubClassOfAxiom,
    OWLSubObjectPropertyOfAxiom,
)
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization


def reasoner_from_axioms(axioms, ontology_iri="urn:example:onto"):
    normalized = OWLNormalization().process_ontology(axioms)
    return Reasoner(OWLClausification().clausify(normalized, ontology_iri=ontology_iri))


NS = "http://example.org/"
```

## Pattern 1: Role Hierarchies

Model a hierarchy of relationships.

```python
supervises = OWLObjectProperty(NS + "supervises")
manages = OWLObjectProperty(NS + "manages")
worksWith = OWLObjectProperty(NS + "worksWith")

# Property hierarchy: supervises ⊑ manages ⊑ worksWith
hierarchy_axioms = [
    OWLSubObjectPropertyOfAxiom(supervises, manages),
    OWLSubObjectPropertyOfAxiom(manages, worksWith),
]

# Relationships inherit: if A supervises B, A also manages B.
# Verify at the TBox level:
reasoner = reasoner_from_axioms(hierarchy_axioms)
reasoner.precompute_inferences(class_hierarchy=True, object_property_hierarchy=True)
print(reasoner.is_sub_role_of(
    AtomicRole.create(NS + "supervises"), AtomicRole.create(NS + "manages")
))  # True
reasoner.dispose()
```

## Pattern 2: Union Types

Express "A or B" relationships.

```python
Person = OWLClass(NS + "Person")
Organization = OWLClass(NS + "Organization")
Email = OWLClass(NS + "Email")
sentTo = OWLObjectProperty(NS + "sentTo")

# A Contact is a Person or an Organization
Contact = OWLObjectUnionOf([Person, Organization])

union_axioms = [
    # Email can only be sent to Persons or Organizations
    OWLSubClassOfAxiom(Email, OWLObjectAllValuesFrom(sentTo, Contact)),
]
```

## Pattern 3: Many-to-Many Relationships

Both sides can have multiple partners — use a property and its inverse.

```python
Student = OWLClass(NS + "Student")
Course = OWLClass(NS + "Course")
enrolledIn = OWLObjectProperty(NS + "enrolledIn")
hasStudent = OWLObjectProperty(NS + "hasStudent")

m2m_axioms = [
    OWLInverseObjectPropertiesAxiom(enrolledIn, hasStudent),
    # Every Student is enrolled in at least one Course
    OWLSubClassOfAxiom(Student, OWLObjectSomeValuesFrom(enrolledIn, Course)),
    # Every Course has at least one Student
    OWLSubClassOfAxiom(Course, OWLObjectSomeValuesFrom(hasStudent, Student)),
]
```

## Pattern 4: Defined Classes (Recognition)

Let the reasoner classify individuals into a category automatically. The key
is **equivalence**, not subclass:

```python
hasPet = OWLObjectProperty(NS + "hasPet")
Pet = OWLClass(NS + "Pet")
PetOwner = OWLClass(NS + "PetOwner")

fido = OWLNamedIndividual(NS + "fido")
anna = OWLNamedIndividual(NS + "anna")

defined_axioms = [
    # PetOwner ≡ ∃hasPet.Pet — anyone with a pet IS a PetOwner
    OWLEquivalentClassesAxiom([PetOwner, OWLObjectSomeValuesFrom(hasPet, Pet)]),
    OWLClassAssertionAxiom(fido, Pet),
    OWLObjectPropertyAssertionAxiom(anna, hasPet, fido),
]

reasoner = reasoner_from_axioms(defined_axioms)
reasoner.precompute_inferences()
owners = reasoner.get_instances(AtomicConcept.create(NS + "PetOwner"))
print(sorted(i.iri for i in owners))  # ['http://example.org/anna']
reasoner.dispose()
```

## Pattern 5: Version Management

Track versions of entities.

```python
version = OWLDataProperty(NS + "version")
versionOf = OWLObjectProperty(NS + "versionOf")

doc_v1 = OWLNamedIndividual(NS + "report_v1")
doc_v2 = OWLNamedIndividual(NS + "report_v2")

version_axioms = [
    OWLDataPropertyAssertionAxiom(doc_v1, version, OWLLiteral(1)),
    OWLDataPropertyAssertionAxiom(doc_v2, version, OWLLiteral(2)),
    OWLObjectPropertyAssertionAxiom(doc_v2, versionOf, doc_v1),
]
```

## Pattern 6: Temporal Relationships

Model time-dependent relationships with a relationship individual.

```python
from datetime import date

startDate = OWLDataProperty(NS + "startDate")
endDate = OWLDataProperty(NS + "endDate")
hasEmployee = OWLObjectProperty(NS + "hasEmployee")
hasEmployer = OWLObjectProperty(NS + "hasEmployer")

employment = OWLNamedIndividual(NS + "emp_alice_2020")
company = OWLNamedIndividual(NS + "acme")
alice = OWLNamedIndividual(NS + "alice")

temporal_axioms = [
    OWLDataPropertyAssertionAxiom(employment, startDate, OWLLiteral(date(2020, 1, 15))),
    OWLDataPropertyAssertionAxiom(employment, endDate, OWLLiteral(date(2023, 12, 31))),
    # Link person and company through the employment record
    OWLObjectPropertyAssertionAxiom(company, hasEmployee, employment),
    OWLObjectPropertyAssertionAxiom(employment, hasEmployer, alice),
]
```

## Pattern 7: Composite Objects

Model objects made up of parts.

```python
Car = OWLClass(NS + "Car")
Engine = OWLClass(NS + "Engine")
Wheel = OWLClass(NS + "Wheel")
hasPart = OWLObjectProperty(NS + "hasPart")

composite_axioms = [
    # Every Car has an Engine and a Wheel
    OWLSubClassOfAxiom(
        Car,
        OWLObjectIntersectionOf([
            OWLObjectSomeValuesFrom(hasPart, Engine),
            OWLObjectSomeValuesFrom(hasPart, Wheel),
        ]),
    ),
]

my_car = OWLNamedIndividual(NS + "my_car")
engine = OWLNamedIndividual(NS + "engine_123")
wheel1 = OWLNamedIndividual(NS + "wheel_1")

composite_axioms += [
    OWLClassAssertionAxiom(my_car, Car),
    OWLClassAssertionAxiom(engine, Engine),
    OWLClassAssertionAxiom(wheel1, Wheel),
    OWLObjectPropertyAssertionAxiom(my_car, hasPart, engine),
    OWLObjectPropertyAssertionAxiom(my_car, hasPart, wheel1),
]
```

## Pattern 8: Reification (Relationship with Attributes)

Add attributes to relationships by promoting them to individuals.

```python
# Instead of:  manages(alice, bob)
# Use a relationship individual with actor / target / attributes:

ManagementRelationship = OWLClass(NS + "ManagementRelationship")
hasActor = OWLObjectProperty(NS + "hasActor")
hasTarget = OWLObjectProperty(NS + "hasTarget")

bob = OWLNamedIndividual(NS + "bob")
rel = OWLNamedIndividual(NS + "manages_rel_1")

reified_axioms = [
    OWLClassAssertionAxiom(rel, ManagementRelationship),
    OWLObjectPropertyAssertionAxiom(rel, hasActor, alice),
    OWLObjectPropertyAssertionAxiom(rel, hasTarget, bob),
    OWLDataPropertyAssertionAxiom(rel, startDate, OWLLiteral(date(2020, 1, 1))),
]
```

## Pattern 9: Negative Assertions

OWL is open-world: what is not asserted is *unknown*, not false. Negative
assertions state explicit falsehoods:

```python
hasAge = OWLDataProperty(NS + "hasAge")

negative_axioms = [
    # alice definitely does not have age 30
    OWLNegativeDataPropertyAssertionAxiom(alice, hasAge, OWLLiteral(30)),
]

reasoner = reasoner_from_axioms(negative_axioms)
print(reasoner.is_consistent())  # True

# Asserting the contradicted value makes the ontology inconsistent:
reasoner2 = reasoner_from_axioms(negative_axioms + [
    OWLDataPropertyAssertionAxiom(alice, hasAge, OWLLiteral(30)),
])
print(reasoner2.is_consistent())  # False
reasoner.dispose()
reasoner2.dispose()
```

## Pattern 10: Constraint Checking

Model value constraints with data ranges; violations surface as
inconsistency:

```python
from hermit.owl_model.class_expression import (
    OWLDataAllValuesFrom, OWLDatatypeRestriction, OWLFacetRestriction,
)
from hermit.owl_model.owl_literal import IntegerOWLDatatype
from hermit.owl_model.vocab import OWLFacet

Person = OWLClass(NS + "Person")

# Person ages must be 0..150
valid_age = OWLDatatypeRestriction(IntegerOWLDatatype, [
    OWLFacetRestriction(OWLFacet.MIN_INCLUSIVE, OWLLiteral(0)),
    OWLFacetRestriction(OWLFacet.MAX_INCLUSIVE, OWLLiteral(150)),
])

constraint_axioms = [
    OWLSubClassOfAxiom(Person, OWLDataAllValuesFrom(hasAge, valid_age)),
]

invalid = OWLNamedIndividual(NS + "invalid")
reasoner = reasoner_from_axioms(constraint_axioms + [
    OWLClassAssertionAxiom(invalid, Person),
    OWLDataPropertyAssertionAxiom(invalid, hasAge, OWLLiteral(-5)),
])
if not reasoner.is_consistent():
    print("Invalid person added - constraint violated")
reasoner.dispose()
```

## Pattern 11: Parametric Queries

Query with variable parameters.

```python
def get_all_of_type(reasoner, type_name):
    """Get all instances of a type."""
    concept = AtomicConcept.create(f"{NS}{type_name}")
    return reasoner.get_instances(concept)


def are_related(reasoner, subject_name, property_name, object_name):
    """Check whether two named individuals are related by a property."""
    return reasoner.has_role_relationship(
        Individual.create(f"{NS}{subject_name}"),
        AtomicRole.create(f"{NS}{property_name}"),
        Individual.create(f"{NS}{object_name}"),
    )


reasoner = reasoner_from_axioms(composite_axioms)
reasoner.precompute_inferences()
print(len(get_all_of_type(reasoner, "Wheel")))            # 1
print(are_related(reasoner, "my_car", "hasPart", "engine_123"))  # True
reasoner.dispose()
```

## Pattern 12: Ontology Composition

Combine multiple axiom sets.

```python
# Base vocabulary shared across domains
base_axioms = [
    OWLSubClassOfAxiom(OWLClass(NS + "Employee"), Person),
]

# Domain-specific additions
domain_axioms = [
    OWLSubClassOfAxiom(OWLClass(NS + "Engineer"), OWLClass(NS + "Employee")),
]

# Axiom lists compose by concatenation
reasoner = reasoner_from_axioms(base_axioms + domain_axioms)
reasoner.precompute_inferences()
print(reasoner.is_sub_class_of(
    AtomicConcept.create(NS + "Engineer"), AtomicConcept.create(NS + "Person")
))  # True
reasoner.dispose()
```

## Pattern 13: Query Caching

Cache query results for repeated lookups.

```python
class CachedReasoner:
    def __init__(self, reasoner):
        self.reasoner = reasoner
        self.cache = {}

    def get_instances(self, concept):
        key = ("instances", concept.iri)
        if key not in self.cache:
            self.cache[key] = self.reasoner.get_instances(concept)
        return self.cache[key]

    def is_sub_class_of(self, sub, sup):
        key = ("subclass", sub.iri, sup.iri)
        if key not in self.cache:
            self.cache[key] = self.reasoner.is_sub_class_of(sub, sup)
        return self.cache[key]


reasoner = reasoner_from_axioms(base_axioms + domain_axioms)
cached = CachedReasoner(reasoner)
engineer = AtomicConcept.create(NS + "Engineer")
person = AtomicConcept.create(NS + "Person")
print(cached.is_sub_class_of(engineer, person))  # Computed
print(cached.is_sub_class_of(engineer, person))  # From cache
reasoner.dispose()
```

## Pattern 14: Incremental Ontology Building

Build the axiom list piece by piece, then compile once.

```python
def build_organizational_ontology():
    axioms = []

    # Step 1: Core classes
    axioms.append(OWLSubClassOfAxiom(OWLClass(NS + "Organization"), OWLThing))

    # Step 2: Employee hierarchy
    axioms.append(OWLSubClassOfAxiom(
        OWLClass(NS + "Employee"), OWLClass(NS + "Person"),
    ))

    # Step 3: Positions
    axioms.append(OWLSubClassOfAxiom(
        OWLClass(NS + "Manager"), OWLClass(NS + "Employee"),
    ))

    return axioms


reasoner = reasoner_from_axioms(build_organizational_ontology())
print(reasoner.is_consistent())  # True
reasoner.dispose()
```

---

**See Also:**
- **[Rules and Queries](../tutorials/03-rules-and-queries.md)** — More complex patterns
- **[Ontology Debugging](./debugging.md)** — Finding issues in patterns
