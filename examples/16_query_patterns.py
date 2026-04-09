"""
Advanced Query Patterns

This example demonstrates:
1. Complex instance retrieval patterns
2. Type-based filtering
3. Hierarchical queries
4. Combining multiple queries for business logic
5. Performance optimization tips

Query patterns are essential for extracting useful information from
your ontology after reasoning completes. This example shows practical
patterns for real-world applications.
"""

from hermit import Reasoner
from hermit.model import (
    DLOntology,
    Atom,
    AtomicConcept,
    AtomicRole,
    Variable,
    DLClause,
    Individual,
)


def main():
    X = Variable.create("X")
    Y = Variable.create("Y")

    # Build an organization ontology
    organization = AtomicConcept.create("http://example.org#Organization")
    company = AtomicConcept.create("http://example.org#Company")
    startup = AtomicConcept.create("http://example.org#Startup")
    enterprise = AtomicConcept.create("http://example.org#Enterprise")

    person = AtomicConcept.create("http://example.org#Person")
    employee = AtomicConcept.create("http://example.org#Employee")
    manager = AtomicConcept.create("http://example.org#Manager")
    director = AtomicConcept.create("http://example.org#Director")
    cto = AtomicConcept.create("http://example.org#CTO")

    # Roles
    works_at = AtomicRole.create("http://example.org#worksAt")
    manages = AtomicRole.create("http://example.org#manages")
    supervises = AtomicRole.create("http://example.org#supervises")

    # TBox
    clauses = [
        # Company ⊑ Organization
        DLClause.create(
            (Atom.create(organization, X),),
            (Atom.create(company, X),),
        ),
        # Startup ⊑ Company
        DLClause.create(
            (Atom.create(company, X),),
            (Atom.create(startup, X),),
        ),
        # Enterprise ⊑ Company
        DLClause.create(
            (Atom.create(company, X),),
            (Atom.create(enterprise, X),),
        ),
        # Employee ⊑ Person
        DLClause.create(
            (Atom.create(person, X),),
            (Atom.create(employee, X),),
        ),
        # Manager ⊑ Employee
        DLClause.create(
            (Atom.create(employee, X),),
            (Atom.create(manager, X),),
        ),
        # Director ⊑ Manager
        DLClause.create(
            (Atom.create(manager, X),),
            (Atom.create(director, X),),
        ),
        # CTO ⊑ Director
        DLClause.create(
            (Atom.create(director, X),),
            (Atom.create(cto, X),),
        ),
        # If X manages Y, then X is a Manager
        DLClause.create(
            (Atom.create(manager, X),),
            (Atom.create(manages, X, Y),),
        ),
    ]

    # ABox: Create individuals
    techcorp = Individual.create("http://example.org#TechCorp")
    faststart = Individual.create("http://example.org#FastStart")

    alice = Individual.create("http://example.org#Alice")
    bob = Individual.create("http://example.org#Bob")
    charlie = Individual.create("http://example.org#Charlie")
    diana = Individual.create("http://example.org#Diana")

    facts = frozenset([
        # Organizations
        Atom.create(enterprise, techcorp),
        Atom.create(startup, faststart),
        # People at TechCorp
        Atom.create(employee, alice),
        Atom.create(works_at, alice, techcorp),
        Atom.create(cto, alice),  # Alice is CTO
        Atom.create(employee, bob),
        Atom.create(works_at, bob, techcorp),
        Atom.create(manager, bob),
        Atom.create(manages, bob, charlie),  # Bob manages Charlie
        Atom.create(manages, bob, diana),    # Bob manages Diana
        # People at FastStart
        Atom.create(employee, charlie),
        Atom.create(works_at, charlie, faststart),
        Atom.create(employee, diana),
        Atom.create(works_at, diana, techcorp),
    ])

    ontology = DLOntology(
        ontology_iri="urn:tutorial:queries",
        dl_clauses=frozenset(clauses),
        positive_facts=facts,
    )

    reasoner = Reasoner(ontology)

    try:
        reasoner.precompute_inferences()

        print("=" * 70)
        print("ADVANCED QUERY PATTERNS")
        print("=" * 70)
        print()

        # Pattern 1: Get all instances of a concept and its subclasses
        print("PATTERN 1: Hierarchical Instance Retrieval")
        print("-" * 70)
        print("Query: All 'Manager' individuals (includes Director, CTO)")
        managers = reasoner.get_instances(manager)
        for mgr in sorted(managers, key=lambda x: x.iri):
            name = mgr.iri.split('#')[-1]
            print(f"  - {name}")
        print(f"Total: {len(managers)} managers")
        print()

        # Pattern 2: Filter instances by additional properties
        print("PATTERN 2: Filter by Role Relationships")
        print("-" * 70)
        print("Query: Managers who work at TechCorp")
        managers_at_techcorp = [
            m for m in managers
            if reasoner.has_role_relationship(m, works_at, techcorp)
        ]
        for mgr in sorted(managers_at_techcorp, key=lambda x: x.iri):
            name = mgr.iri.split('#')[-1]
            print(f"  - {name}")
        print(f"Total: {len(managers_at_techcorp)}")
        print()

        # Pattern 3: Collect related instances through roles
        print("PATTERN 3: Follow Relationship Chains")
        print("-" * 70)
        print("Query: Find all employees managed by Bob")
        bob_manages = set()
        all_employees = reasoner.get_instances(employee)
        for emp in all_employees:
            if reasoner.has_role_relationship(bob, manages, emp):
                bob_manages.add(emp)
        for emp in sorted(bob_manages, key=lambda x: x.iri):
            name = emp.iri.split('#')[-1]
            print(f"  - {name}")
        print(f"Total: {len(bob_manages)} employees")
        print()

        # Pattern 4: Count instances by type for reporting
        print("PATTERN 4: Statistics and Reporting")
        print("-" * 70)
        concepts = [
            ("Employees", employee),
            ("Managers", manager),
            ("Directors", director),
            ("CTOs", cto),
            ("Companies", company),
            ("Enterprises", enterprise),
            ("Startups", startup),
        ]
        for label, concept in concepts:
            count = len(reasoner.get_instances(concept))
            print(f"  {label:20} {count:3} instances")
        print()

        # Pattern 5: Type-based logic (business rules)
        print("PATTERN 5: Type-Based Business Logic")
        print("-" * 70)
        print("Rule: High-level executives (Director+) at enterprises get parking")
        high_level = reasoner.get_instances(director)
        enterprises = reasoner.get_instances(enterprise)
        has_parking = []
        for person in high_level:
            for org in enterprises:
                if reasoner.has_role_relationship(person, works_at, org):
                    has_parking.append(person)
                    break
        for person in sorted(has_parking, key=lambda x: x.iri):
            name = person.iri.split('#')[-1]
            print(f"  ✓ {name} gets parking")
        print()

        # Pattern 6: Find instances with specific type combinations
        print("PATTERN 6: Multi-Type Filtering")
        print("-" * 70)
        print("Query: Employees at TechCorp who are NOT managers")
        all_at_techcorp = [
            e for e in reasoner.get_instances(employee)
            if reasoner.has_role_relationship(e, works_at, techcorp)
        ]
        non_managers = [
            e for e in all_at_techcorp
            if not reasoner.has_type(e, manager)
        ]
        for emp in sorted(non_managers, key=lambda x: x.iri):
            name = emp.iri.split('#')[-1]
            print(f"  - {name}")
        print(f"Total: {len(non_managers)}")
        print()

        print("=" * 70)
        print("Query Pattern Best Practices")
        print("=" * 70)
        print("""
1. PRECOMPUTE FOR REPEATED QUERIES
   reasoner.precompute_inferences()
   → Required before get_instances() for accurate results
   → Call once, reuse for multiple queries

2. USE GENERATORS FOR LARGE RESULT SETS
   instances = reasoner.get_instances(concept)
   for inst in instances:  # Iterate, don't build list
       # Process each instance

3. FILTER IN PYTHON VS. ONTOLOGY
   Python filtering: reasoner.get_instances() + filter()
   → Use for complex business logic
   → Use for combining multiple criteria

   Ontology-based: Create subclasses in TBox
   → Use for stable criteria
   → Use for performance-critical paths

4. CACHE HIERARCHY QUERIES
   managers = reasoner.get_instances(manager)
   → Includes all directors, CTOs (subclasses)
   → Use for role-based access control

5. UNDERSTAND TRANSITIVE INFERENCE
   query: has_type(alice, company)
   → Returns False even if alice.works_at.parent_org=company
   → Requires explicit has_type rule in ontology
   → Or computed through get_types() then hierarchy checking

6. PERFORMANCE TIPS
   - Use get_instances(concept) not has_type() in loops
   - Precompute_inferences() once at startup
   - Cache results if queries are repeated
   - Filter in-memory for complex predicates
        """)

    finally:
        reasoner.dispose()


if __name__ == "__main__":
    main()
