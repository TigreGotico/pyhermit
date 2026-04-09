"""
Nominal (Enumerated) Classes

This example demonstrates:
1. Creating classes with specific individuals (OneOf)
2. Nominal classes for fixed sets of values
3. Exhaustiveness constraints
4. Using nominals for configurations and enumerations
5. Type inference from nominal definitions

Nominal classes define a class as being composed of exactly
a set of named individuals. For example, "Weekday" could be
defined as {Monday, Tuesday, ..., Friday}.
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

    # Create concepts
    weekday = AtomicConcept.create("http://example.org#Weekday")
    weekend_day = AtomicConcept.create("http://example.org#WeekendDay")
    day = AtomicConcept.create("http://example.org#Day")

    http_status = AtomicConcept.create("http://example.org#HTTPStatus")
    success_status = AtomicConcept.create("http://example.org#SuccessStatus")
    error_status = AtomicConcept.create("http://example.org#ErrorStatus")

    color = AtomicConcept.create("http://example.org#Color")
    primary_color = AtomicConcept.create("http://example.org#PrimaryColor")

    # Create individuals for days
    monday = Individual.create("http://example.org#Monday")
    tuesday = Individual.create("http://example.org#Tuesday")
    wednesday = Individual.create("http://example.org#Wednesday")
    thursday = Individual.create("http://example.org#Thursday")
    friday = Individual.create("http://example.org#Friday")
    saturday = Individual.create("http://example.org#Saturday")
    sunday = Individual.create("http://example.org#Sunday")

    # Create individuals for HTTP statuses
    status_200 = Individual.create("http://example.org#Status200")
    status_201 = Individual.create("http://example.org#Status201")
    status_400 = Individual.create("http://example.org#Status400")
    status_404 = Individual.create("http://example.org#Status404")
    status_500 = Individual.create("http://example.org#Status500")

    # Create individuals for colors
    red = Individual.create("http://example.org#Red")
    green = Individual.create("http://example.org#Green")
    blue = Individual.create("http://example.org#Blue")

    # TBox: Rules for enumerations
    clauses = [
        # Day ⊑ Day (reflexive)
        DLClause.create(
            (Atom.create(day, X),),
            (Atom.create(day, X),),
        ),
    ]

    # ABox: Define nominal classes by assertion
    facts = frozenset([
        # Weekdays (Monday-Friday are weekdays)
        Atom.create(weekday, monday),
        Atom.create(weekday, tuesday),
        Atom.create(weekday, wednesday),
        Atom.create(weekday, thursday),
        Atom.create(weekday, friday),
        Atom.create(day, monday),
        Atom.create(day, tuesday),
        Atom.create(day, wednesday),
        Atom.create(day, thursday),
        Atom.create(day, friday),
        # Weekend days (Saturday-Sunday)
        Atom.create(weekend_day, saturday),
        Atom.create(weekend_day, sunday),
        Atom.create(day, saturday),
        Atom.create(day, sunday),
        # HTTP Success Statuses (2xx)
        Atom.create(success_status, status_200),
        Atom.create(success_status, status_201),
        Atom.create(http_status, status_200),
        Atom.create(http_status, status_201),
        # HTTP Error Statuses (4xx, 5xx)
        Atom.create(error_status, status_400),
        Atom.create(error_status, status_404),
        Atom.create(error_status, status_500),
        Atom.create(http_status, status_400),
        Atom.create(http_status, status_404),
        Atom.create(http_status, status_500),
        # Primary Colors
        Atom.create(primary_color, red),
        Atom.create(primary_color, green),
        Atom.create(primary_color, blue),
        Atom.create(color, red),
        Atom.create(color, green),
        Atom.create(color, blue),
    ])

    ontology = DLOntology(
        ontology_iri="urn:tutorial:nominals",
        dl_clauses=frozenset(clauses),
        positive_facts=facts,
    )

    reasoner = Reasoner(ontology)

    try:
        reasoner.precompute_inferences()

        print("=" * 70)
        print("NOMINAL (ENUMERATED) CLASSES")
        print("=" * 70)
        print()

        print("Example 1: Days of the Week")
        print("-" * 70)

        weekdays = reasoner.get_instances(weekday)
        weekend_days = reasoner.get_instances(weekend_day)
        all_days = reasoner.get_instances(day)

        print(f"Weekdays ({len(weekdays)}):")
        for d in sorted(weekdays, key=lambda x: x.iri):
            name = d.iri.split('#')[-1]
            print(f"  - {name}")

        print(f"\nWeekend Days ({len(weekend_days)}):")
        for d in sorted(weekend_days, key=lambda x: x.iri):
            name = d.iri.split('#')[-1]
            print(f"  - {name}")

        print(f"\nAll Days ({len(all_days)}):")
        for d in sorted(all_days, key=lambda x: x.iri):
            name = d.iri.split('#')[-1]
            print(f"  - {name}")
        print()

        print("Example 2: HTTP Status Codes")
        print("-" * 70)

        success_statuses = reasoner.get_instances(success_status)
        error_statuses = reasoner.get_instances(error_status)
        all_statuses = reasoner.get_instances(http_status)

        print(f"Success Statuses ({len(success_statuses)}):")
        for s in sorted(success_statuses, key=lambda x: x.iri):
            name = s.iri.split('#')[-1]
            print(f"  - {name}")

        print(f"\nError Statuses ({len(error_statuses)}):")
        for s in sorted(error_statuses, key=lambda x: x.iri):
            name = s.iri.split('#')[-1]
            print(f"  - {name}")

        print(f"\nAll HTTP Statuses ({len(all_statuses)}):")
        for s in sorted(all_statuses, key=lambda x: x.iri):
            name = s.iri.split('#')[-1]
            print(f"  - {name}")
        print()

        print("Example 3: Primary Colors")
        print("-" * 70)

        primary_colors = reasoner.get_instances(primary_color)
        all_colors = reasoner.get_instances(color)

        print(f"Primary Colors ({len(primary_colors)}):")
        for c in sorted(primary_colors, key=lambda x: x.iri):
            name = c.iri.split('#')[-1]
            print(f"  - {name}")

        print(f"\nAll Colors ({len(all_colors)}):")
        for c in sorted(all_colors, key=lambda x: x.iri):
            name = c.iri.split('#')[-1]
            print(f"  - {name}")
        print()

        print("Type Checking Examples:")
        print("-" * 70)
        print(f"Monday is a Weekday: {reasoner.has_type(monday, weekday)}")
        print(f"Monday is a Day: {reasoner.has_type(monday, day)}")
        print(f"Saturday is a Weekday: {reasoner.has_type(saturday, weekday)}")
        print(f"Saturday is a Day: {reasoner.has_type(saturday, day)}")
        print(f"Status 200 is a Success: {reasoner.has_type(status_200, success_status)}")
        print(f"Status 404 is an Error: {reasoner.has_type(status_404, error_status)}")
        print(f"Status 404 is a Success: {reasoner.has_type(status_404, success_status)}")
        print(f"Red is Primary: {reasoner.has_type(red, primary_color)}")
        print()

        print("=" * 70)
        print("Understanding Nominal Classes")
        print("=" * 70)
        print("""
NOMINAL CLASSES:

A nominal class is defined as the union of specific named individuals.
In OWL: SomeClass ≡ {individual1, individual2, ..., individualN}

In PyHermit, nominals are modeled by:
  1. Creating individuals for each value
  2. Asserting facts that define the nominal class
  3. Querying with get_instances() to retrieve all members

EXAMPLES:

1. Days of the Week
   Weekday = {Monday, Tuesday, Wednesday, Thursday, Friday}
   Weekend = {Saturday, Sunday}

2. HTTP Status Codes
   SuccessStatus = {200, 201, ...}
   ErrorStatus = {400, 404, 500, ...}

3. Enumerated Values
   Any finite set of constants can be represented

USE CASES:

1. CONFIGURATION ENUMERATIONS
   ✓ Status codes (success, pending, failed, etc.)
   ✓ Log levels (DEBUG, INFO, WARNING, ERROR)
   ✓ User roles (Admin, Editor, Viewer, Guest)
   ✓ Days of week, months, seasons

2. VALIDATION AND CONSTRAINTS
   ✓ Check if a value is in allowed set
   ✓ Enumerate valid transitions
   ✓ Define fixed vocabularies

3. SEMANTIC CLASSIFICATION
   ✓ Group related constants
   ✓ Enable type-based logic
   ✓ Support reasoning over enumerated values

IMPLEMENTATION PATTERNS:

Pattern 1: Static Enumeration
   Color = {Red, Green, Blue}
   [Define in TBox, never changes]

Pattern 2: Dynamic Classification
   RequestStatus = {Pending, Active, Completed, Failed}
   [Add individuals as requests are created]

Pattern 3: Hierarchical Enums
   HTTPStatus = {2xx, 3xx, 4xx, 5xx}
   SuccessStatus ⊆ HTTPStatus = {200, 201, ...}
   ErrorStatus ⊆ HTTPStatus = {400, 404, ...}

QUERYING:

All members of a nominal class:
   members = reasoner.get_instances(color)

Check membership:
   is_member = reasoner.has_type(red, color)

Count members:
   count = len(reasoner.get_instances(status))
        """)

    finally:
        reasoner.dispose()


if __name__ == "__main__":
    main()
