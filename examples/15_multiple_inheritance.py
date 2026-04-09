"""
Multiple Inheritance and Diamond Problem

This example demonstrates:
1. Multiple inheritance (a class has multiple parents)
2. The diamond problem in ontologies
3. Conflict resolution in complex hierarchies
4. Path-based subsumption queries
5. Common ancestor detection

Multiple inheritance is common in semantic models where entities can belong
to multiple categories. For example, a "Smartphone" is both a "Phone" and
a "Computer" - it's a multiple inheritance diamond.
"""

from hermit import Reasoner
from hermit.model import (
    DLOntology,
    Atom,
    AtomicConcept,
    Variable,
    DLClause,
    Individual,
)


def main():
    X = Variable.create("X")

    # Build a diamond inheritance hierarchy
    #
    #        Device
    #       /      \
    #    Phone   Computer
    #       \      /
    #     Smartphone
    #

    device = AtomicConcept.create("http://example.org#Device")
    phone = AtomicConcept.create("http://example.org#Phone")
    computer = AtomicConcept.create("http://example.org#Computer")
    smartphone = AtomicConcept.create("http://example.org#Smartphone")

    # Additional related concepts
    portable = AtomicConcept.create("http://example.org#Portable")
    communication_device = AtomicConcept.create("http://example.org#CommunicationDevice")

    # TBox: Define the hierarchy
    clauses = [
        # Phone ⊑ Device
        DLClause.create(
            (Atom.create(device, X),),
            (Atom.create(phone, X),),
        ),
        # Computer ⊑ Device
        DLClause.create(
            (Atom.create(device, X),),
            (Atom.create(computer, X),),
        ),
        # Smartphone ⊑ Phone (multiple inheritance: from phone)
        DLClause.create(
            (Atom.create(phone, X),),
            (Atom.create(smartphone, X),),
        ),
        # Smartphone ⊑ Computer (multiple inheritance: from computer)
        DLClause.create(
            (Atom.create(computer, X),),
            (Atom.create(smartphone, X),),
        ),
        # Phone ⊑ CommunicationDevice
        DLClause.create(
            (Atom.create(communication_device, X),),
            (Atom.create(phone, X),),
        ),
        # Computer ⊑ Portable (some computers are portable)
        DLClause.create(
            (Atom.create(portable, X),),
            (Atom.create(computer, X),),
        ),
    ]

    # ABox: Individuals
    iphone = Individual.create("http://example.org#iPhone15")
    laptop = Individual.create("http://example.org#MacbookPro")

    facts = frozenset([
        Atom.create(smartphone, iphone),
        Atom.create(computer, laptop),
    ])

    ontology = DLOntology(
        ontology_iri="urn:tutorial:inheritance",
        dl_clauses=frozenset(clauses),
        positive_facts=facts,
    )

    reasoner = Reasoner(ontology)

    try:
        reasoner.precompute_inferences()

        print("=" * 70)
        print("MULTIPLE INHERITANCE AND THE DIAMOND PROBLEM")
        print("=" * 70)
        print()

        print("Class Hierarchy (Diamond):")
        print("-" * 70)
        print("        Device")
        print("       /      \\")
        print("    Phone   Computer")
        print("       \\      /")
        print("     Smartphone")
        print()

        print("Subsumption Relationships for Smartphone:")
        print("-" * 70)
        print(f"Smartphone ⊑ Phone: {reasoner.is_sub_class_of(smartphone, phone)}")
        print(f"Smartphone ⊑ Computer: {reasoner.is_sub_class_of(smartphone, computer)}")
        print(f"Smartphone ⊑ Device: {reasoner.is_sub_class_of(smartphone, device)}")
        print(f"Smartphone ⊑ CommunicationDevice: {reasoner.is_sub_class_of(smartphone, communication_device)}")
        print(f"Smartphone ⊑ Portable: {reasoner.is_sub_class_of(smartphone, portable)}")
        print()

        print("Type Inference for iPhone15 (Smartphone instance):")
        print("-" * 70)
        iphone_types = reasoner.get_types(iphone)
        for t in sorted(iphone_types, key=lambda c: c.iri):
            type_name = t.iri.split('#')[-1] if '#' in t.iri else t.iri
            print(f"  - {type_name}")
        print()

        print("Direct type checks:")
        print("-" * 70)
        print(f"iPhone15 is a Smartphone: {reasoner.has_type(iphone, smartphone)}")
        print(f"iPhone15 is a Phone: {reasoner.has_type(iphone, phone)}")
        print(f"iPhone15 is a Computer: {reasoner.has_type(iphone, computer)}")
        print(f"iPhone15 is a Device: {reasoner.has_type(iphone, device)}")
        print(f"iPhone15 is a CommunicationDevice: {reasoner.has_type(iphone, communication_device)}")
        print(f"iPhone15 is Portable: {reasoner.has_type(iphone, portable)}")
        print()

        print("=" * 70)
        print("Understanding Multiple Inheritance")
        print("=" * 70)
        print("""
MULTIPLE INHERITANCE:

A class can have multiple parents. In this example:
  Smartphone ⊑ Phone AND Smartphone ⊑ Computer

This means:
  - Every smartphone is a phone
  - Every smartphone is a computer
  - Therefore, every smartphone is a device (through both parents)

THE DIAMOND PROBLEM:

In the hierarchy:
        Device (top)
       /      \\
    Phone   Computer
       \\      /
     Smartphone (bottom)

There are multiple paths from Smartphone to Device:
  Path 1: Smartphone → Phone → Device
  Path 2: Smartphone → Computer → Device

In description logic, this isn't a "problem" - it's simply that:
  - Smartphone inherits all properties from Phone
  - Smartphone inherits all properties from Computer
  - Both paths lead to Device (but Device's properties are inherited once)

RESOLUTION:

The reasoner automatically handles this by:
1. Computing the class hierarchy (which respects all inheritance paths)
2. Properly inferring all transitive relationships
3. Ensuring no properties are duplicated or conflicted

For iPhone15:
  - It's inferred to be a Smartphone (asserted)
  - It's inferred to be a Phone (from Smartphone ⊑ Phone)
  - It's inferred to be a Computer (from Smartphone ⊑ Computer)
  - It's inferred to be a Device (from both paths)
  - It's inferred to be a CommunicationDevice (Phone → CommunicationDevice)
  - It's inferred to be Portable (Computer → Portable)

All these inferences happen automatically through the reasoner!

PRACTICAL IMPLICATIONS:

1. No need to explicitly state "Smartphone ⊑ Device"
   (it's automatically inferred via both parent classes)

2. Queries automatically find all applicable inferences
   reasoner.has_type(iphone, device) returns True
   even though it's not directly asserted

3. Complex hierarchies work naturally
   Multiple inheritance is fully supported in OWL DL
        """)

    finally:
        reasoner.dispose()


if __name__ == "__main__":
    main()
