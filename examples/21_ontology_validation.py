"""
Ontology Validation and Constraint Checking

This example demonstrates:
1. Validating ontologies against constraints
2. Detecting design errors
3. Checking data quality
4. Enforcing business rules
5. Automated constraint violation detection

Validation is critical for ensuring ontology quality and
catching errors early in the development process.
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

    # Define company domain with constraints
    company = AtomicConcept.create("http://example.org#Company")
    startup = AtomicConcept.create("http://example.org#Startup")
    employee = AtomicConcept.create("http://example.org#Employee")
    manager = AtomicConcept.create("http://example.org#Manager")
    founder = AtomicConcept.create("http://example.org#Founder")
    ceo = AtomicConcept.create("http://example.org#CEO")

    person = AtomicConcept.create("http://example.org#Person")

    # Roles
    works_at = AtomicRole.create("http://example.org#worksAt")
    manages = AtomicRole.create("http://example.org#manages")
    founded_by = AtomicRole.create("http://example.org#foundedBy")
    has_ceo = AtomicRole.create("http://example.org#hasCEO")

    # TBox with business constraints
    clauses = [
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
        # CEO ⊑ Manager
        DLClause.create(
            (Atom.create(manager, X),),
            (Atom.create(ceo, X),),
        ),
        # Founder ⊑ Employee
        DLClause.create(
            (Atom.create(employee, X),),
            (Atom.create(founder, X),),
        ),
        # Startup ⊑ Company
        DLClause.create(
            (Atom.create(company, X),),
            (Atom.create(startup, X),),
        ),
        # CONSTRAINT 1: If X manages Y, then X must be a Manager
        DLClause.create(
            (Atom.create(manager, X),),
            (Atom.create(manages, X, Y),),
        ),
        # CONSTRAINT 2: If X works at Y, then X must be Employee
        DLClause.create(
            (Atom.create(employee, X),),
            (Atom.create(works_at, X, Y),),
        ),
        # CONSTRAINT 3: If X founded Y, then X must be Founder
        DLClause.create(
            (Atom.create(founder, X),),
            (Atom.create(founded_by, Y, X),),
        ),
    ]

    # Create test data
    acme = Individual.create("http://example.org#ACME")
    techstart = Individual.create("http://example.org#TechStart")

    alice = Individual.create("http://example.org#Alice")
    bob = Individual.create("http://example.org#Bob")
    charlie = Individual.create("http://example.org#Charlie")
    diana = Individual.create("http://example.org#Diana")
    eve = Individual.create("http://example.org#Eve")

    # Create scenarios
    print("=" * 70)
    print("ONTOLOGY VALIDATION AND CONSTRAINT CHECKING")
    print("=" * 70)
    print()

    # Scenario 1: Valid data
    print("SCENARIO 1: Valid Company Structure")
    print("-" * 70)

    facts_valid = frozenset([
        Atom.create(startup, techstart),
        Atom.create(company, acme),
        # Alice: CEO
        Atom.create(person, alice),
        Atom.create(ceo, alice),
        Atom.create(works_at, alice, techstart),
        # Bob: Manager
        Atom.create(person, bob),
        Atom.create(manager, bob),
        Atom.create(works_at, bob, techstart),
        Atom.create(manages, bob, charlie),
        # Charlie: Employee
        Atom.create(person, charlie),
        Atom.create(employee, charlie),
        Atom.create(works_at, charlie, techstart),
        # Diana: Founder
        Atom.create(person, diana),
        Atom.create(founder, diana),
        Atom.create(works_at, diana, techstart),
        Atom.create(founded_by, techstart, diana),
    ])

    ontology_valid = DLOntology(
        ontology_iri="urn:validation:valid",
        dl_clauses=frozenset(clauses),
        positive_facts=facts_valid,
    )

    reasoner_valid = Reasoner(ontology_valid)
    reasoner_valid.precompute_inferences()

    print("Validating company structure:")
    print()

    # Check constraint compliance
    constraints_passed = 0
    constraints_total = 0

    # Check all managers actually manage someone
    print("✓ Constraint 1: Managers must manage someone")
    managers = reasoner_valid.get_instances(manager)
    for mgr in managers:
        name = mgr.iri.split('#')[-1]
        all_employees = reasoner_valid.get_instances(employee)
        manages_count = sum(
            1 for emp in all_employees
            if reasoner_valid.has_role_relationship(mgr, manages, emp)
        )
        status = "✓" if manages_count > 0 else "✗"
        print(f"  {status} {name} manages {manages_count} employee(s)")
        constraints_total += 1
        if manages_count > 0:
            constraints_passed += 1

    print()
    print("✓ Constraint 2: All employees work at a company")
    employees = reasoner_valid.get_instances(employee)
    for emp in employees:
        name = emp.iri.split('#')[-1]
        companies = reasoner_valid.get_instances(company)
        works_count = sum(
            1 for company in companies
            if reasoner_valid.has_role_relationship(emp, works_at, company)
        )
        status = "✓" if works_count > 0 else "✗"
        print(f"  {status} {name} works at {works_count} company(ies)")
        constraints_total += 1
        if works_count > 0:
            constraints_passed += 1

    print()
    print("✓ Constraint 3: Founders are employees")
    founders = reasoner_valid.get_instances(founder)
    for founder_ind in founders:
        name = founder_ind.iri.split('#')[-1]
        is_employee = reasoner_valid.has_type(founder_ind, employee)
        status = "✓" if is_employee else "✗"
        print(f"  {status} {name} is employee: {is_employee}")
        constraints_total += 1
        if is_employee:
            constraints_passed += 1

    print()
    print(f"Result: {constraints_passed}/{constraints_total} constraints passed")

    reasoner_valid.dispose()
    print()

    # Scenario 2: Invalid data (constraint violations)
    print("SCENARIO 2: Detecting Constraint Violations")
    print("-" * 70)

    facts_invalid = frozenset([
        Atom.create(startup, techstart),
        # ERROR 1: Non-manager trying to manage someone
        Atom.create(person, eve),
        Atom.create(employee, eve),
        Atom.create(works_at, eve, techstart),
        Atom.create(manages, eve, alice),  # Eve manages but isn't a manager
        # Alice: Regular employee (not manager or CEO)
        Atom.create(person, alice),
        Atom.create(employee, alice),
        Atom.create(works_at, alice, techstart),
    ])

    ontology_invalid = DLOntology(
        ontology_iri="urn:validation:invalid",
        dl_clauses=frozenset(clauses),
        positive_facts=facts_invalid,
    )

    reasoner_invalid = Reasoner(ontology_invalid)
    reasoner_invalid.precompute_inferences()

    print("Checking for violations:")
    print()

    # Check if constraint 1 is enforced
    violations = []
    all_employees = reasoner_invalid.get_instances(employee)
    managers_from_constraint = reasoner_invalid.get_instances(manager)

    for emp in all_employees:
        name = emp.iri.split('#')[-1]
        is_manager = reasoner_invalid.has_type(emp, manager)
        # Check if manages anyone
        all_people = reasoner_invalid.get_instances(person)
        manages_someone = any(
            reasoner_invalid.has_role_relationship(emp, manages, other)
            for other in all_people
            if other != emp
        )

        if manages_someone and not is_manager:
            violations.append(
                f"✗ {name} manages someone but is not classified as Manager"
            )

    if violations:
        print("Violations detected:")
        for v in violations:
            print(f"  {v}")
    else:
        print("✓ No violations detected")

    print()
    reasoner_invalid.dispose()

    print("=" * 70)
    print("Validation Strategies")
    print("=" * 70)
    print("""
AUTOMATED CONSTRAINT CHECKING:

1. STRUCTURAL CONSTRAINTS
   ✓ Role domain/range constraints
   ✓ Cardinality constraints
   ✓ Disjointness violations
   ✓ Subsumption conflicts

2. BUSINESS RULE CONSTRAINTS
   ✓ Manager must have employees
   ✓ Employee must work at company
   ✓ Founder must be employee
   ✓ CEO must be manager

3. DATA QUALITY CONSTRAINTS
   ✓ No orphaned individuals
   ✓ Referential integrity
   ✓ Mandatory properties
   ✓ Value constraints

VALIDATION PATTERNS:

Pattern 1: Direct Constraint Checking
    for person in people:
        if has_role(person, manages, X):
            assert has_type(person, manager)

Pattern 2: Consistency-Based Validation
    if not ontology.is_consistent():
        # Find contradictory axioms
        for concept in concepts:
            if not reasoner.is_satisfiable(concept):
                # Concept is unsatisfiable

Pattern 3: Inference-Based Validation
    inferred_type = reasoner.get_types(individual)
    expected_type = schema.get_type(individual)
    if inferred_type != expected_type:
        # Constraint violation

VALIDATION CHECKLIST:

Before deployment:
□ Consistency check: is_consistent() == True
□ No unsatisfiable concepts: is_satisfiable(C) for all C
□ Constraint compliance: business rules verified
□ Data quality: no orphaned/dangling references
□ Performance: reasoning completes within timeout
□ Coverage: all individuals have expected types
□ Coherence: no unexpected type conflicts

IMPLEMENTATION:

class OntologyValidator:
    def __init__(self, reasoner):
        self.reasoner = reasoner

    def validate_constraints(self, constraints):
        violations = []
        for constraint in constraints:
            if not self.check_constraint(constraint):
                violations.append(constraint)
        return violations

    def check_constraint(self, constraint):
        # Implement specific constraint checking logic
        pass

TOOLS FOR VALIDATION:

1. Static Analysis: Parse ontology structure
2. Consistency Checking: Run tableau reasoning
3. Query Validation: Execute test queries
4. Regression Testing: Compare to known good state
5. Metrics Analysis: Check ontology statistics

BENEFITS:

✓ Early error detection
✓ Reduced data quality issues
✓ Better system reliability
✓ Easier debugging
✓ Improved documentation
    """)


if __name__ == "__main__":
    main()
