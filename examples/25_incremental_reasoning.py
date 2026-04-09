"""
Incremental Reasoning and Dynamic Ontologies

This example demonstrates:
1. Adding facts dynamically
2. Reasoning with evolving data
3. Detecting impacts of changes
4. Updating inferences incrementally
5. Handling dynamic ontologies

Real-world systems often need to reason over data that
changes over time, requiring incremental updates rather
than full re-reasoning from scratch.
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

    # Build a project management ontology
    project = AtomicConcept.create("http://example.org/pm#Project")
    team = AtomicConcept.create("http://example.org/pm#Team")
    person = AtomicConcept.create("http://example.org/pm#Person")
    developer = AtomicConcept.create("http://example.org/pm#Developer")
    manager = AtomicConcept.create("http://example.org/pm#Manager")
    senior_developer = AtomicConcept.create("http://example.org/pm#SeniorDeveloper")

    task = AtomicConcept.create("http://example.org/pm#Task")
    completed = AtomicConcept.create("http://example.org/pm#CompletedTask")

    # Roles
    has_member = AtomicRole.create("http://example.org/pm#hasMember")
    manages = AtomicRole.create("http://example.org/pm#manages")
    assigned_to = AtomicRole.create("http://example.org/pm#assignedTo")
    completed_by = AtomicRole.create("http://example.org/pm#completedBy")

    # TBox
    clauses = [
        # Developer ⊑ Person
        DLClause.create(
            (Atom.create(person, X),),
            (Atom.create(developer, X),),
        ),
        # Manager ⊑ Person
        DLClause.create(
            (Atom.create(person, X),),
            (Atom.create(manager, X),),
        ),
        # SeniorDeveloper ⊑ Developer
        DLClause.create(
            (Atom.create(developer, X),),
            (Atom.create(senior_developer, X),),
        ),
        # If someone manages a project, they're a manager
        DLClause.create(
            (Atom.create(manager, X),),
            (Atom.create(manages, X, Y),),
        ),
        # If a task is completed, mark it as completed task
        DLClause.create(
            (Atom.create(completed, X),),
            (Atom.create(completed_by, X, Y),),
        ),
    ]

    # Create individuals
    project_x = Individual.create("http://example.org/pm#ProjectX")
    alice = Individual.create("http://example.org/pm#Alice")
    bob = Individual.create("http://example.org/pm#Bob")
    charlie = Individual.create("http://example.org/pm#Charlie")
    task1 = Individual.create("http://example.org/pm#Task1")
    task2 = Individual.create("http://example.org/pm#Task2")
    task3 = Individual.create("http://example.org/pm#Task3")

    print("=" * 70)
    print("INCREMENTAL REASONING AND DYNAMIC ONTOLOGIES")
    print("=" * 70)
    print()

    # Phase 1: Initial state
    print("PHASE 1: Initial Project Setup")
    print("-" * 70)

    facts_phase1 = frozenset([
        Atom.create(project, project_x),
        Atom.create(person, alice),
        Atom.create(person, bob),
        Atom.create(person, charlie),
        Atom.create(developer, bob),
        Atom.create(developer, charlie),
        Atom.create(task, task1),
        Atom.create(task, task2),
        Atom.create(task, task3),
    ])

    ontology_phase1 = DLOntology(
        ontology_iri="urn:pm:phase1",
        dl_clauses=frozenset(clauses),
        positive_facts=facts_phase1,
    )

    reasoner_phase1 = Reasoner(ontology_phase1)
    reasoner_phase1.precompute_inferences()

    print("Created project with:")
    all_people = reasoner_phase1.get_instances(person)
    all_developers = reasoner_phase1.get_instances(developer)
    all_managers = reasoner_phase1.get_instances(manager)

    print(f"  People: {len(all_people)} ({', '.join([p.iri.split('#')[-1] for p in all_people])})")
    print(f"  Developers: {len(all_developers)} ({', '.join([d.iri.split('#')[-1] for d in all_developers])})")
    print(f"  Managers: {len(all_managers)} ({', '.join([m.iri.split('#')[-1] for m in all_managers]) if all_managers else 'none'})")

    reasoner_phase1.dispose()
    print()

    # Phase 2: Alice becomes project manager
    print("PHASE 2: Alice Appointed as Project Manager")
    print("-" * 70)

    facts_phase2 = frozenset([
        Atom.create(project, project_x),
        Atom.create(person, alice),
        Atom.create(person, bob),
        Atom.create(person, charlie),
        Atom.create(developer, bob),
        Atom.create(developer, charlie),
        Atom.create(task, task1),
        Atom.create(task, task2),
        Atom.create(task, task3),
        # NEW: Alice manages the project
        Atom.create(manages, alice, project_x),
    ])

    ontology_phase2 = DLOntology(
        ontology_iri="urn:pm:phase2",
        dl_clauses=frozenset(clauses),
        positive_facts=facts_phase2,
    )

    reasoner_phase2 = Reasoner(ontology_phase2)
    reasoner_phase2.precompute_inferences()

    all_managers = reasoner_phase2.get_instances(manager)
    alice_types = reasoner_phase2.get_types(alice)

    print(f"Alice now has types: {', '.join([t.iri.split('#')[-1] for t in alice_types if 'Thing' not in t.iri])}")
    print(f"Managers in project: {', '.join([m.iri.split('#')[-1] for m in all_managers])}")

    impact = "Alice is now classified as Manager (inferred from manages relationship)"
    print(f"\nImpact: {impact}")

    reasoner_phase2.dispose()
    print()

    # Phase 3: Assign tasks to team members
    print("PHASE 3: Tasks Assigned to Team")
    print("-" * 70)

    facts_phase3 = frozenset([
        Atom.create(project, project_x),
        Atom.create(person, alice),
        Atom.create(person, bob),
        Atom.create(person, charlie),
        Atom.create(developer, bob),
        Atom.create(developer, charlie),
        Atom.create(task, task1),
        Atom.create(task, task2),
        Atom.create(task, task3),
        Atom.create(manages, alice, project_x),
        # NEW: Task assignments
        Atom.create(assigned_to, task1, bob),
        Atom.create(assigned_to, task2, charlie),
        Atom.create(assigned_to, task3, alice),
    ])

    ontology_phase3 = DLOntology(
        ontology_iri="urn:pm:phase3",
        dl_clauses=frozenset(clauses),
        positive_facts=facts_phase3,
    )

    reasoner_phase3 = Reasoner(ontology_phase3)
    reasoner_phase3.precompute_inferences()

    print("Task assignments:")
    all_tasks = reasoner_phase3.get_instances(task)
    for task_ind in sorted(all_tasks, key=lambda t: t.iri):
        task_name = task_ind.iri.split('#')[-1]
        assigned_to_list = []
        for person_ind in reasoner_phase3.get_instances(person):
            if reasoner_phase3.has_role_relationship(task_ind, assigned_to, person_ind):
                assigned_to_list.append(person_ind.iri.split('#')[-1])
        assigned_str = ", ".join(assigned_to_list) if assigned_to_list else "unassigned"
        print(f"  {task_name}: {assigned_str}")

    reasoner_phase3.dispose()
    print()

    # Phase 4: Complete tasks
    print("PHASE 4: Tasks Completion")
    print("-" * 70)

    facts_phase4 = frozenset([
        Atom.create(project, project_x),
        Atom.create(person, alice),
        Atom.create(person, bob),
        Atom.create(person, charlie),
        Atom.create(developer, bob),
        Atom.create(developer, charlie),
        Atom.create(task, task1),
        Atom.create(task, task2),
        Atom.create(task, task3),
        Atom.create(manages, alice, project_x),
        Atom.create(assigned_to, task1, bob),
        Atom.create(assigned_to, task2, charlie),
        Atom.create(assigned_to, task3, alice),
        # NEW: Task completions
        Atom.create(completed, task1),
        Atom.create(completed_by, task1, bob),
        Atom.create(completed, task2),
        Atom.create(completed_by, task2, charlie),
    ])

    ontology_phase4 = DLOntology(
        ontology_iri="urn:pm:phase4",
        dl_clauses=frozenset(clauses),
        positive_facts=facts_phase4,
    )

    reasoner_phase4 = Reasoner(ontology_phase4)
    reasoner_phase4.precompute_inferences()

    completed_tasks = reasoner_phase4.get_instances(completed)
    print(f"Completed tasks: {len(completed_tasks)}/3")
    for ct in sorted(completed_tasks, key=lambda t: t.iri):
        task_name = ct.iri.split('#')[-1]
        completed_by_list = []
        for person_ind in reasoner_phase4.get_instances(person):
            if reasoner_phase4.has_role_relationship(ct, completed_by, person_ind):
                completed_by_list.append(person_ind.iri.split('#')[-1])
        completed_str = ", ".join(completed_by_list) if completed_by_list else "unknown"
        print(f"  {task_name}: completed by {completed_str}")

    reasoner_phase4.dispose()
    print()

    print("=" * 70)
    print("Incremental Reasoning Patterns")
    print("=" * 70)
    print("""
INCREMENTAL REASONING STRATEGIES:

1. FULL RE-REASONING
   When facts change:
   - Create new ontology with updated facts
   - Run reasoner from scratch
   - Compare results to previous state

   Pros: Correct, simple implementation
   Cons: Performance cost, especially for large ontologies

2. DELTA-BASED UPDATING
   Track what changed:
   - Identify added/removed facts
   - Determine affected concepts
   - Update only impacted inferences

   Pros: Efficient for small changes
   Cons: Complex implementation, harder to maintain

3. SNAPSHOT COMPARISON
   Compare states:
   - Before change: snapshot_v1
   - After change: snapshot_v2
   - Report differences

   Pros: Simple, no tracking needed
   Cons: O(n) space, slower for large datasets

CHANGE PROPAGATION:

When a fact is added:
  New Fact → Trigger Rules → Derive New Facts
           → Classify Types → Update Hierarchy
           → Check Constraints → Report Violations

Example:
  Add: manages(Alice, ProjectX)
  Rule: manager(X) ← manages(X, Y)
  Result: Alice inferred to be manager

IMPACT ANALYSIS:

When Alice becomes manager:
  1. Direct change: Alice's type is now {Person, Manager}
  2. Derived effects:
     - Alice gains all properties of Manager
     - Alice can now approve decisions
     - Alice appears in manager listings
  3. Downstream effects:
     - Team structure changes
     - Reporting relationships change
     - Permissions may change

IMPLEMENTATION:

class IncrementalReasoner:
    def __init__(self, ontology):
        self.ontology = ontology
        self.reasoner = Reasoner(ontology)
        self.current_facts = set(ontology.positive_facts)
        self.current_inferences = {}

    def add_facts(self, new_facts):
        # Create new ontology with added facts
        updated_facts = self.current_facts | new_facts
        new_ontology = DLOntology(
            ontology_iri=self.ontology.ontology_iri,
            dl_clauses=self.ontology.dl_clauses,
            positive_facts=updated_facts
        )

        # Re-reason
        self.reasoner.dispose()
        self.reasoner = Reasoner(new_ontology)
        self.reasoner.precompute_inferences()
        self.current_facts = updated_facts

    def get_changes(self):
        # Report what inferences changed
        old_inferences = self.current_inferences
        new_inferences = self.reasoner.get_all_inferences()
        return {
            'added': new_inferences - old_inferences,
            'removed': old_inferences - new_inferences
        }

APPLICATIONS:

1. REAL-TIME SYSTEMS
   - Stock market analysis
   - Network monitoring
   - Sensor data processing

2. COLLABORATIVE SYSTEMS
   - Wiki-style knowledge bases
   - Crowd-sourced data
   - Continuous updates

3. EVOLVING DATA
   - Growing datasets
   - Periodic updates
   - Data cleaning

PERFORMANCE CONSIDERATIONS:

- Small changes: Full re-reasoning is acceptable
- Medium changes: Optimize reasoner configuration
- Large changes: Consider external caching
- Frequent changes: Batch updates before reasoning

BEST PRACTICES:

1. Batch changes when possible
2. Monitor reasoning time
3. Cache stable inferences
4. Track change history
5. Document reasoning timeline
    """)


if __name__ == "__main__":
    main()
