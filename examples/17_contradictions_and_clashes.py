"""
Detecting Contradictions and Handling Unsatisfiability

This example demonstrates:
1. Detecting contradictory ontologies
2. Understanding clash detection
3. Finding unsatisfiable concepts
4. Debugging consistency issues
5. Using the reasoner to validate ontologies

When an ontology is inconsistent, the reasoner cannot derive meaningful conclusions.
Learning to detect and fix contradictions is essential for ontology development.
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


def demonstrate_issue(name: str, ontology: DLOntology):
    """Helper to demonstrate an ontology issue."""
    print(f"\n{name}")
    print("-" * 70)
    reasoner = Reasoner(ontology)
    try:
        is_consistent = reasoner.is_consistent()
        print(f"Consistency: {'✓ CONSISTENT' if is_consistent else '✗ INCONSISTENT'}")

        if is_consistent:
            # If consistent, show what concepts are satisfiable
            dog_concept = None
            cat_concept = None
            for atom in ontology.get_positive_facts():
                if 'Dog' in str(atom.predicate):
                    dog_concept = atom.predicate
                if 'Cat' in str(atom.predicate):
                    cat_concept = atom.predicate

            # Test satisfiability of key concepts
            concepts_to_test = [
                "http://example.org#Animal",
                "http://example.org#Dog",
                "http://example.org#Cat",
            ]
            for concept_iri in concepts_to_test:
                try:
                    concept = AtomicConcept.create(concept_iri)
                    is_sat = reasoner.is_satisfiable(concept)
                    print(f"  {concept_iri.split('#')[-1]} satisfiable: {is_sat}")
                except:
                    pass

    finally:
        reasoner.dispose()


def main():
    X = Variable.create("X")

    print("=" * 70)
    print("DETECTING CONTRADICTIONS AND HANDLING INCONSISTENCIES")
    print("=" * 70)

    # =====================================================================
    # Example 1: Disjoint class contradiction
    # =====================================================================

    print("\nEXAMPLE 1: Disjoint Classes Contradiction")
    print("=" * 70)

    animal = AtomicConcept.create("http://example.org#Animal")
    dog = AtomicConcept.create("http://example.org#Dog")
    cat = AtomicConcept.create("http://example.org#Cat")

    clauses_1 = [
        DLClause.create(
            (Atom.create(animal, X),),
            (Atom.create(dog, X),),
        ),
        DLClause.create(
            (Atom.create(animal, X),),
            (Atom.create(cat, X),),
        ),
    ]

    facts_1_good = frozenset([
        Atom.create(dog, Individual.create("http://example.org#Fido")),
    ])

    ontology_1_good = DLOntology(
        ontology_iri="urn:demo:good",
        dl_clauses=frozenset(clauses_1),
        positive_facts=facts_1_good,
    )

    demonstrate_issue("Good ontology (Dog and Cat disjoint):", ontology_1_good)

    # Now introduce contradiction
    facts_1_bad = frozenset([
        Atom.create(dog, Individual.create("http://example.org#Fido")),
        Atom.create(cat, Individual.create("http://example.org#Fido")),
    ])

    ontology_1_bad = DLOntology(
        ontology_iri="urn:demo:bad1",
        dl_clauses=frozenset(clauses_1),
        positive_facts=facts_1_bad,
    )

    print("\nContradiction: Same individual is both Dog AND Cat (without disjoint declaration)")
    print("Note: Without explicit disjoint axioms, this is actually consistent in standard DL!")
    demonstrate_issue("Ontology with Fido as both Dog and Cat:", ontology_1_bad)

    # =====================================================================
    # Example 2: Unsatisfiable concept (contradiction in definition)
    # =====================================================================

    print("\n\nEXAMPLE 2: Unsatisfiable Concept Definition")
    print("=" * 70)

    living_thing = AtomicConcept.create("http://example.org#LivingThing")
    dead_thing = AtomicConcept.create("http://example.org#DeadThing")
    undead = AtomicConcept.create("http://example.org#Undead")

    clauses_2 = [
        # Undead must be both LivingThing and DeadThing
        # But if these are disjoint, this is impossible
        # We'll just state the requirements without explicit disjointness
        DLClause.create(
            (Atom.create(living_thing, X),),
            (Atom.create(undead, X),),
        ),
        DLClause.create(
            (Atom.create(dead_thing, X),),
            (Atom.create(undead, X),),
        ),
    ]

    facts_2 = frozenset([])

    ontology_2 = DLOntology(
        ontology_iri="urn:demo:undead",
        dl_clauses=frozenset(clauses_2),
        positive_facts=facts_2,
    )

    demonstrate_issue("Undead (must be both Living and Dead):", ontology_2)

    # =====================================================================
    # Example 3: Cardinality contradiction
    # =====================================================================

    print("\n\nEXAMPLE 3: Cardinality Restriction Violation")
    print("=" * 70)

    person = AtomicConcept.create("http://example.org#Person")
    has_head = AtomicRole.create("http://example.org#hasHead")

    clauses_3 = [
        DLClause.create(
            (Atom.create(person, X),),
            (Atom.create(person, X),),
        ),
    ]

    # Person with 2 heads (violates biological cardinality)
    facts_3 = frozenset([
        Atom.create(person, Individual.create("http://example.org#Alice")),
        Atom.create(has_head, Individual.create("http://example.org#Alice"),
                   Individual.create("http://example.org#Head1")),
        Atom.create(has_head, Individual.create("http://example.org#Alice"),
                   Individual.create("http://example.org#Head2")),
    ])

    ontology_3 = DLOntology(
        ontology_iri="urn:demo:cardinality",
        dl_clauses=frozenset(clauses_3),
        positive_facts=facts_3,
    )

    print("\nPerson with 2 heads (unusual, but not contradictory without constraints)")
    demonstrate_issue("Cardinality issue (Person with 2 heads):", ontology_3)

    # =====================================================================
    # Example 4: Cyclic definition
    # =====================================================================

    print("\n\nEXAMPLE 4: Self-Referential Definition")
    print("=" * 70)

    ancestor = AtomicConcept.create("http://example.org#Ancestor")
    has_ancestor = AtomicRole.create("http://example.org#hasAncestor")

    clauses_4 = [
        # X is ancestor of Y if X has ancestor Z and Z has descendant Y
        # This is allowed in DL, but can lead to complex reasoning
        DLClause.create(
            (Atom.create(ancestor, X),),
            (Atom.create(has_ancestor, X, X),),
        ),
    ]

    facts_4 = frozenset([
        Atom.create(ancestor, Individual.create("http://example.org#Alice")),
    ])

    ontology_4 = DLOntology(
        ontology_iri="urn:demo:cyclic",
        dl_clauses=frozenset(clauses_4),
        positive_facts=facts_4,
    )

    print("\nAncestor who is their own ancestor (circular definition)")
    demonstrate_issue("Cyclic definition (self-ancestor):", ontology_4)

    # =====================================================================
    # Summary
    # =====================================================================

    print("\n\n" + "=" * 70)
    print("HANDLING INCONSISTENCIES")
    print("=" * 70)
    print("""
COMMON SOURCES OF INCONSISTENCY:

1. DISJOINT CLASS VIOLATIONS
   Problem: Same individual asserted in two disjoint classes
   Solution: Ensure disjoint axioms or verify data quality

2. UNSATISFIABLE CONCEPTS
   Problem: A concept definition contradicts itself
   Example: "Square ⊓ Round" (no object can be both)
   Solution: Review concept definitions for logical consistency

3. CARDINALITY VIOLATIONS
   Problem: Violating cardinality constraints
   Example: Person ⊑ = 1 hasHead, but X has 2 heads
   Solution: Check constraints and validate data

4. CYCLIC DEFINITIONS
   Problem: Circular dependencies in rules
   Example: X is ancestor of X
   Solution: Usually allowed, but may indicate design issues

5. DATA QUALITY ISSUES
   Problem: Incorrect or conflicting facts
   Solution: Validate data sources and cleansing rules

DEBUGGING INCONSISTENCIES:

Step 1: Test is_consistent()
  reasoner.is_consistent() → False

Step 2: Identify problematic classes
  for each concept:
    if not reasoner.is_satisfiable(concept):
      → This concept is unsatisfiable

Step 3: Review the problematic concept
  - Check its definition in TBox
  - Check assertions in ABox
  - Look for contradictory rules

Step 4: Fix the issue
  - Add missing disjoint axioms
  - Remove contradictory facts
  - Relax overly strict constraints

BEST PRACTICES:

1. Validate ontologies incrementally
   - Add rules/facts gradually
   - Test consistency after each addition

2. Use automated consistency checking
   - Run reasoner in test pipeline
   - Catch inconsistencies early

3. Document constraints
   - Explain why classes are disjoint
   - Document cardinality assumptions

4. Version control ontologies
   - Track changes that cause inconsistency
   - Revert problematic changes easily

5. Separate schema from data
   - Keep TBox (schema) stable
   - Version ABox (data) separately
    """)


if __name__ == "__main__":
    main()
