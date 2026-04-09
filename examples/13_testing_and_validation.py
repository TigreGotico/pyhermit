"""
Testing and Validation: Using PyHermit for Ontology Quality Assurance

This example demonstrates techniques for validating ontologies:

1. Consistency checking
2. Detecting unsatisfiable concepts
3. Testing class relationships
4. Validating individual assertions
5. Regression testing
6. Ontology profiling
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
from dataclasses import dataclass
from typing import List
import time


# =====================================================
# TEST FRAMEWORK
# =====================================================

@dataclass
class TestResult:
    """Result of a single test."""
    test_name: str
    passed: bool
    message: str
    duration_ms: float


class OntologyTestSuite:
    """Test suite for validating ontologies.

    Tests cover:
    - Consistency (no contradictions)
    - Satisfiability (concepts can have instances)
    - Hierarchy (relationships are correct)
    - Data validity (individuals match concepts)
    """

    def __init__(self, ontology: DLOntology):
        self.ontology = ontology
        self.reasoner = Reasoner(ontology)
        self.reasoner.precompute_inferences(class_hierarchy=True)
        self.results: List[TestResult] = []

    def test_consistency(self, expected: bool = True) -> TestResult:
        """Test if ontology is consistent."""
        start = time.time()

        is_consistent = self.reasoner.is_consistent()
        passed = is_consistent == expected

        message = f"Ontology is consistent: {is_consistent}"
        if not passed:
            message += f" (expected: {expected})"

        result = TestResult(
            test_name="Consistency",
            passed=passed,
            message=message,
            duration_ms=(time.time() - start) * 1000,
        )
        self.results.append(result)
        return result

    def test_concept_satisfiable(self, concept: AtomicConcept,
                                 expected: bool = True) -> TestResult:
        """Test if a concept is satisfiable."""
        start = time.time()

        is_satisfiable = self.reasoner.is_satisfiable(concept)
        passed = is_satisfiable == expected

        concept_name = concept.iri.split("#")[-1]
        message = f"{concept_name} is satisfiable: {is_satisfiable}"
        if not passed:
            message += f" (expected: {expected})"

        result = TestResult(
            test_name=f"Satisfiable({concept_name})",
            passed=passed,
            message=message,
            duration_ms=(time.time() - start) * 1000,
        )
        self.results.append(result)
        return result

    def test_subsumption(self, sub: AtomicConcept, sup: AtomicConcept,
                        expected: bool = True) -> TestResult:
        """Test if sub ⊑ sup."""
        start = time.time()

        is_subsumed = self.reasoner.is_sub_class_of(sub, sup)
        passed = is_subsumed == expected

        sub_name = sub.iri.split("#")[-1]
        sup_name = sup.iri.split("#")[-1]
        message = f"{sub_name} ⊑ {sup_name}: {is_subsumed}"
        if not passed:
            message += f" (expected: {expected})"

        result = TestResult(
            test_name=f"Subsumption({sub_name}, {sup_name})",
            passed=passed,
            message=message,
            duration_ms=(time.time() - start) * 1000,
        )
        self.results.append(result)
        return result

    def test_individual_type(self, individual: Individual,
                            concept: AtomicConcept,
                            expected: bool = True) -> TestResult:
        """Test if individual has a specific type."""
        start = time.time()

        has_type = self.reasoner.has_type(individual, concept)
        passed = has_type == expected

        ind_name = individual.iri.split("#")[-1]
        concept_name = concept.iri.split("#")[-1]
        message = f"{ind_name} ∈ {concept_name}: {has_type}"
        if not passed:
            message += f" (expected: {expected})"

        result = TestResult(
            test_name=f"Type({ind_name}, {concept_name})",
            passed=passed,
            message=message,
            duration_ms=(time.time() - start) * 1000,
        )
        self.results.append(result)
        return result

    def test_instance_count(self, concept: AtomicConcept,
                           expected_count: int) -> TestResult:
        """Test that concept has expected number of instances."""
        start = time.time()

        instances = self.reasoner.get_instances(concept)
        actual_count = len(instances)
        passed = actual_count == expected_count

        concept_name = concept.iri.split("#")[-1]
        message = f"{concept_name} has {actual_count} instance(s)"
        if not passed:
            message += f" (expected: {expected_count})"

        result = TestResult(
            test_name=f"InstanceCount({concept_name})",
            passed=passed,
            message=message,
            duration_ms=(time.time() - start) * 1000,
        )
        self.results.append(result)
        return result

    def get_results(self) -> dict:
        """Get aggregated test results."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        total_time = sum(r.duration_ms for r in self.results)

        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': (passed / total * 100) if total > 0 else 0,
            'total_time_ms': total_time,
            'results': self.results,
        }

    def dispose(self):
        """Clean up resources."""
        self.reasoner.dispose()


# =====================================================
# ONTOLOGY PROFILER
# =====================================================

class OntologyProfiler:
    """Profile ontology characteristics for quality analysis."""

    @staticmethod
    def profile(ontology: DLOntology) -> dict:
        """Get profiling statistics."""
        return {
            'num_clauses': len(ontology.dl_clauses),
            'num_facts': len(ontology.positive_facts),
            'ontology_iri': ontology.ontology_iri,
        }


# =====================================================
# REGRESSION TESTING
# =====================================================

class RegressionTestSuite:
    """Regression test suite for ontology changes.

    Use this to ensure changes don't break existing functionality.
    """

    def __init__(self, name: str):
        self.name = name
        self.test_cases: List[tuple] = []

    def add_subsumption_test(self, sub_iri: str, sup_iri: str, expected: bool):
        """Add a subsumption test case."""
        self.test_cases.append(('subsumption', sub_iri, sup_iri, expected))

    def add_satisfiability_test(self, concept_iri: str, expected: bool):
        """Add a satisfiability test case."""
        self.test_cases.append(('satisfiable', concept_iri, None, expected))

    def add_consistency_test(self, expected: bool):
        """Add a consistency test case."""
        self.test_cases.append(('consistent', None, None, expected))

    def run(self, ontology: DLOntology) -> dict:
        """Run all regression tests."""
        reasoner = Reasoner(ontology)
        reasoner.precompute_inferences(class_hierarchy=True)

        passed = 0
        failed = 0
        failures = []

        for test_case in self.test_cases:
            test_type = test_case[0]

            if test_type == 'consistent':
                actual = reasoner.is_consistent()
                expected = test_case[3]
                if actual == expected:
                    passed += 1
                else:
                    failed += 1
                    failures.append(f"Consistency: expected {expected}, got {actual}")

            elif test_type == 'satisfiable':
                concept_iri = test_case[1]
                concept = AtomicConcept.create(concept_iri)
                actual = reasoner.is_satisfiable(concept)
                expected = test_case[3]
                if actual == expected:
                    passed += 1
                else:
                    failed += 1
                    concept_name = concept_iri.split("#")[-1]
                    failures.append(
                        f"Satisfiable({concept_name}): "
                        f"expected {expected}, got {actual}"
                    )

            elif test_type == 'subsumption':
                sub_iri = test_case[1]
                sup_iri = test_case[2]
                sub = AtomicConcept.create(sub_iri)
                sup = AtomicConcept.create(sup_iri)
                actual = reasoner.is_sub_class_of(sub, sup)
                expected = test_case[3]
                if actual == expected:
                    passed += 1
                else:
                    failed += 1
                    sub_name = sub_iri.split("#")[-1]
                    sup_name = sup_iri.split("#")[-1]
                    failures.append(
                        f"{sub_name} ⊑ {sup_name}: "
                        f"expected {expected}, got {actual}"
                    )

        reasoner.dispose()

        return {
            'name': self.name,
            'total': passed + failed,
            'passed': passed,
            'failed': failed,
            'pass_rate': (passed / (passed + failed) * 100) if (passed + failed) > 0 else 0,
            'failures': failures,
        }


# =====================================================
# DEMO
# =====================================================

def build_test_ontology() -> DLOntology:
    """Build an ontology for testing."""
    X = Variable.create("X")

    # Concepts
    animal = AtomicConcept.create("http://test.org#Animal")
    dog = AtomicConcept.create("http://test.org#Dog")
    cat = AtomicConcept.create("http://test.org#Cat")
    poodle = AtomicConcept.create("http://test.org#Poodle")

    clauses = [
        DLClause.create(
            (Atom.create(animal, X),),
            (Atom.create(dog, X),),
        ),
        DLClause.create(
            (Atom.create(animal, X),),
            (Atom.create(cat, X),),
        ),
        DLClause.create(
            (Atom.create(dog, X),),
            (Atom.create(poodle, X),),
        ),
    ]

    # Test individuals
    facts = frozenset([
        Atom.create(dog, Individual.create("http://test.org#Fido")),
        Atom.create(dog, Individual.create("http://test.org#Rex")),
        Atom.create(cat, Individual.create("http://test.org#Whiskers")),
        Atom.create(poodle, Individual.create("http://test.org#Fluffy")),
    ])

    return DLOntology(
        ontology_iri="urn:test:animals",
        dl_clauses=frozenset(clauses),
        positive_facts=facts,
    )


def main():
    print("=" * 70)
    print("TESTING AND VALIDATION: Ontology Quality Assurance")
    print("=" * 70)
    print()

    ontology = build_test_ontology()

    # =========================================================
    # Unit Tests
    # =========================================================
    print("UNIT TESTS: Individual Test Cases")
    print("-" * 70)

    suite = OntologyTestSuite(ontology)

    animal = AtomicConcept.create("http://test.org#Animal")
    dog = AtomicConcept.create("http://test.org#Dog")
    cat = AtomicConcept.create("http://test.org#Cat")
    poodle = AtomicConcept.create("http://test.org#Poodle")
    fido = Individual.create("http://test.org#Fido")

    # Test 1: Consistency
    result = suite.test_consistency(expected=True)
    print(f"{'✓' if result.passed else '✗'} {result.message}")

    # Test 2: Concept satisfiability
    result = suite.test_concept_satisfiable(dog, expected=True)
    print(f"{'✓' if result.passed else '✗'} {result.message}")

    # Test 3: Subsumption relationships
    result = suite.test_subsumption(dog, animal, expected=True)
    print(f"{'✓' if result.passed else '✗'} {result.message}")

    result = suite.test_subsumption(poodle, dog, expected=True)
    print(f"{'✓' if result.passed else '✗'} {result.message}")

    result = suite.test_subsumption(poodle, animal, expected=True)
    print(f"{'✓' if result.passed else '✗'} {result.message}")

    result = suite.test_subsumption(dog, cat, expected=False)
    print(f"{'✓' if result.passed else '✗'} {result.message}")

    # Test 4: Individual types
    result = suite.test_individual_type(fido, dog, expected=True)
    print(f"{'✓' if result.passed else '✗'} {result.message}")

    result = suite.test_individual_type(fido, animal, expected=True)
    print(f"{'✓' if result.passed else '✗'} {result.message}")

    # Test 5: Instance counts
    result = suite.test_instance_count(dog, expected_count=3)  # Fido, Rex, Fluffy (as poodle)
    print(f"{'✓' if result.passed else '✗'} {result.message}")

    result = suite.test_instance_count(poodle, expected_count=1)  # Just Fluffy
    print(f"{'✓' if result.passed else '✗'} {result.message}")

    # Get summary
    test_results = suite.get_results()
    print()
    print(f"Test Summary: {test_results['passed']}/{test_results['total']} passed")
    print(f"Pass rate: {test_results['pass_rate']:.1f}%")
    print(f"Total time: {test_results['total_time_ms']:.2f}ms")
    print()

    suite.dispose()

    # =========================================================
    # Regression Testing
    # =========================================================
    print("REGRESSION TESTING: Version Control for Ontologies")
    print("-" * 70)

    regression_suite = RegressionTestSuite("Animal Ontology v1.0")
    regression_suite.add_consistency_test(True)
    regression_suite.add_subsumption_test("http://test.org#Dog", "http://test.org#Animal", True)
    regression_suite.add_subsumption_test("http://test.org#Poodle", "http://test.org#Dog", True)
    regression_suite.add_satisfiability_test("http://test.org#Dog", True)

    results = regression_suite.run(ontology)

    print(f"Suite: {results['name']}")
    print(f"Results: {results['passed']}/{results['total']} tests passed")
    print(f"Pass rate: {results['pass_rate']:.1f}%")

    if results['failures']:
        print("Failures:")
        for failure in results['failures']:
            print(f"  ✗ {failure}")
    else:
        print("✓ All regression tests passed!")

    print()

    # =========================================================
    # Ontology Profiling
    # =========================================================
    print("ONTOLOGY PROFILING: Size and Complexity")
    print("-" * 70)

    profile = OntologyProfiler.profile(ontology)
    print(f"Ontology IRI: {profile['ontology_iri']}")
    print(f"Number of DL clauses: {profile['num_clauses']}")
    print(f"Number of facts: {profile['num_facts']}")
    print()

    print("=" * 70)
    print("Best Practices for Ontology Validation")
    print("=" * 70)
    print("""
1. TEST EARLY, TEST OFTEN
   - Run consistency checks immediately after changes
   - Use regression tests to catch regressions early

2. TEST COVERAGE
   - Test all critical subsumption relationships
   - Test satisfiability of important concepts
   - Verify instance counts match expectations

3. AUTOMATED TESTING
   - Create test suites for your domain ontologies
   - Run tests in CI/CD pipelines
   - Track test coverage over time

4. REGRESSION TESTING
   - Maintain a suite of regression tests
   - Run before and after ontology updates
   - Document breaking changes

5. PROFILING
   - Monitor ontology size growth
   - Track reasoning performance trends
   - Identify expensive subsumptions

6. ERROR MESSAGES
   - Provide meaningful error messages for test failures
   - Log which concepts/individuals caused failures
   - Track failure patterns
    """)


if __name__ == "__main__":
    main()
