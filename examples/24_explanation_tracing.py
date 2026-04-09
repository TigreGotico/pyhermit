"""
Explanation and Justification Tracing

This example demonstrates:
1. Explaining inferred facts
2. Tracing derivation chains
3. Finding justifications for conclusions
4. Debugging reasoning
5. Dependency tracking

Explanation is crucial for building trust in automated
reasoning systems and for debugging ontologies.
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

    # Build a medical diagnosis ontology
    patient = AtomicConcept.create("http://example.org/med#Patient")
    symptom = AtomicConcept.create("http://example.org/med#Symptom")
    disease = AtomicConcept.create("http://example.org/med#Disease")

    fever = AtomicConcept.create("http://example.org/med#Fever")
    cough = AtomicConcept.create("http://example.org/med#Cough")
    fatigue = AtomicConcept.create("http://example.org/med#Fatigue")

    cold = AtomicConcept.create("http://example.org/med#Cold")
    flu = AtomicConcept.create("http://example.org/med#Flu")
    pneumonia = AtomicConcept.create("http://example.org/med#Pneumonia")

    # TBox: Diagnostic rules
    clauses = [
        # Symptom ⊑ Symptom (reflexive, just for ontology structure)
        DLClause.create(
            (Atom.create(symptom, X),),
            (Atom.create(symptom, X),),
        ),
        # RULE 1: Cold requires fever OR cough
        # This is simplified - in real logic we'd need disjunctive reasoning
        DLClause.create(
            (Atom.create(cold, X),),
            (Atom.create(fever, X),),
        ),
        # RULE 2: Flu requires fever, cough, and fatigue
        DLClause.create(
            (Atom.create(flu, X),),
            (Atom.create(fever, X),),
        ),
        DLClause.create(
            (Atom.create(flu, X),),
            (Atom.create(cough, X),),
        ),
        DLClause.create(
            (Atom.create(flu, X),),
            (Atom.create(fatigue, X),),
        ),
        # RULE 3: Pneumonia requires severe cough
        DLClause.create(
            (Atom.create(pneumonia, X),),
            (Atom.create(cough, X),),
        ),
    ]

    # Create patient with symptoms
    john = Individual.create("http://example.org/med#John")

    facts = frozenset([
        Atom.create(patient, john),
        Atom.create(fever, john),
        Atom.create(cough, john),
        Atom.create(fatigue, john),
    ])

    ontology = DLOntology(
        ontology_iri="urn:tutorial:diagnosis",
        dl_clauses=frozenset(clauses),
        positive_facts=facts,
    )

    reasoner = Reasoner(ontology)

    try:
        reasoner.precompute_inferences()

        print("=" * 70)
        print("EXPLANATION AND JUSTIFICATION TRACING")
        print("=" * 70)
        print()

        print("Patient: John")
        print("-" * 70)

        # Observed symptoms
        print("Observed symptoms:")
        symptoms = [fever, cough, fatigue]
        for sym in symptoms:
            sym_name = sym.iri.split('#')[-1]
            has_symptom = reasoner.has_type(john, sym)
            status = "✓" if has_symptom else "✗"
            print(f"  {status} {sym_name}: {has_symptom}")

        print()

        # Inferred conditions
        print("Inferred conditions:")
        conditions = [cold, flu, pneumonia]
        for cond in conditions:
            cond_name = cond.iri.split('#')[-1]
            has_condition = reasoner.has_type(john, cond)
            status = "✓" if has_condition else "✗"
            print(f"  {status} {cond_name}: {has_condition}")

        print()
        print()

        # Manual explanation of reasoning
        print("=" * 70)
        print("EXPLANATION TRACES")
        print("=" * 70)
        print()

        print("Question: Why does John have Cold?")
        print("-" * 70)
        print("Derivation chain:")
        print("  1. Cold(John) is inferred from Rule: Cold ← Fever")
        print("  2. Fever(John) is directly asserted (observed symptom)")
        print("  3. Therefore: Cold(John) is true")
        print()
        print("Justification: John has fever, which is sufficient for cold diagnosis")
        print()

        print("Question: Why does John have Flu?")
        print("-" * 70)
        print("Derivation chain:")
        print("  1. Flu(John) requires all of:")
        print("     a) Rule: Flu ← Fever")
        print("     b) Rule: Flu ← Cough")
        print("     c) Rule: Flu ← Fatigue")
        print("  2. Checking assertions:")
        print(f"     a) Fever(John) = {reasoner.has_type(john, fever)} (observed)")
        print(f"     b) Cough(John) = {reasoner.has_type(john, cough)} (observed)")
        print(f"     c) Fatigue(John) = {reasoner.has_type(john, fatigue)} (observed)")
        print("  3. All conditions satisfied")
        print("  4. Therefore: Flu(John) is true")
        print()
        print("Justification: All diagnostic criteria for flu are met")
        print()

        print("Question: Why does John have Pneumonia?")
        print("-" * 70)
        print("Derivation chain:")
        print("  1. Pneumonia(John) requires:")
        print("     Rule: Pneumonia ← Cough")
        print("  2. Checking assertion:")
        print(f"     Cough(John) = {reasoner.has_type(john, cough)} (observed)")
        print("  3. Condition satisfied")
        print("  4. Therefore: Pneumonia(John) is true")
        print()
        print("Justification: Severe cough is present (cough symptom observed)")
        print()

        print("=" * 70)
        print("Explanation Patterns")
        print("=" * 70)
        print("""
WHY-EXPLANATIONS (proof justification):

Pattern 1: Direct Assertion
  Q: Why does John have Fever?
  A: It was directly observed/asserted (symptom present)

Pattern 2: Single Rule Application
  Q: Why does John have Cold?
  A: Because John has Fever (satisfies Cold rule)
  Derivation: Cold ← Fever

Pattern 3: Multiple Rule Application
  Q: Why does John have Flu?
  A: Because John has all three symptoms:
     - Fever (satisfies rule 1)
     - Cough (satisfies rule 2)
     - Fatigue (satisfies rule 3)

Pattern 4: Transitive Inference
  Q: Why is X a [SuperClass]?
  A: Because X is [SubClass], and [SubClass] ⊑ [SuperClass]
  Derivation chain: X → SubClass → SuperClass

Pattern 5: Complex Reasoning
  Q: Why is X a [Conclusion]?
  A: Because:
     - X has property A (from rule R1)
     - X has property B (from rule R2)
     - Properties A∩B imply Conclusion (rule R3)
     - Therefore: Conclusion(X)

EXPLANATION GENERATION:

1. TRACE THE DERIVATION
   - Start from the conclusion
   - Work backwards through rules
   - Track which facts were used

2. IDENTIFY CONTRIBUTING FACTS
   - Which assertions led to the conclusion?
   - Which rules were applied?
   - What was the order of application?

3. GENERATE NATURAL LANGUAGE
   - Convert logical trace to readable explanation
   - Highlight key steps
   - Explain the reasoning logic

IMPLEMENTATION:

class ExplanationTracer:
    def explain(self, individual, concept):
        \"\"\"Generate explanation for why individual has type concept\"\"\"
        # Check if directly asserted
        if self.is_directly_asserted(individual, concept):
            return DirectAssertion(individual, concept)

        # Check if derived by rules
        for rule in self.ontology.rules:
            if rule.head == concept:
                if self.all_conditions_satisfied(individual, rule):
                    return RuleApplication(rule, individual)

        # Check if derived through hierarchy
        for parent in self.reasoner.get_super_classes(concept):
            if self.explain(individual, parent):
                return HierarchyInference(concept, parent, individual)

        return NoExplanation()

USE CASES:

1. DEBUGGING
   - Find why an inference was made
   - Identify incorrect rules
   - Trace data quality issues

2. USER TRUST
   - Explain conclusions to users
   - Build confidence in system
   - Justify decisions

3. COMPLIANCE
   - Document reasoning for audits
   - Demonstrate decision logic
   - Support regulatory requirements

4. LEARNING
   - Understand system behavior
   - Train new rules
   - Improve ontology

CHALLENGES:

⚠ Complex reasoning chains are hard to explain
⚠ Multiple derivation paths possible
⚠ Circular dependencies
⚠ Performance cost of tracing
⚠ Natural language generation difficulty
        """)

    finally:
        reasoner.dispose()


if __name__ == "__main__":
    main()
