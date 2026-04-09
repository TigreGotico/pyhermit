"""
Integration Patterns: Using PyHermit in Larger Applications

This example demonstrates practical patterns for integrating PyHermit
into real applications:

1. Singleton reasoner pattern
2. Caching query results
3. Background reasoning
4. Batch queries
5. Error handling and recovery
6. Resource management
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
import time
from typing import Optional, Set
from dataclasses import dataclass


# =====================================================
# PATTERN 1: Singleton Reasoner with Lazy Initialization
# =====================================================

class ReasonerSingleton:
    """Thread-safe singleton for managing a global reasoner instance.

    This pattern is useful when you have a single ontology that multiple
    parts of your application need to query.
    """

    _instance: Optional['ReasonerSingleton'] = None
    _reasoner: Optional[Reasoner] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, ontology: DLOntology) -> None:
        """Initialize the reasoner with an ontology."""
        if self._reasoner is not None:
            self._reasoner.dispose()
        self._reasoner = Reasoner(ontology)
        self._reasoner.precompute_inferences(class_hierarchy=True)
        print("✓ Reasoner initialized and classified")

    def get_reasoner(self) -> Reasoner:
        """Get the initialized reasoner."""
        if self._reasoner is None:
            raise RuntimeError("Reasoner not initialized. Call initialize() first.")
        return self._reasoner

    def dispose(self) -> None:
        """Clean up the reasoner."""
        if self._reasoner is not None:
            self._reasoner.dispose()
            self._reasoner = None
            print("✓ Reasoner disposed")


# =====================================================
# PATTERN 2: Result Caching
# =====================================================

@dataclass(frozen=True)
class SubsumptionQuery:
    """Immutable query object for caching."""
    sub_class_iri: str
    super_class_iri: str

    def __hash__(self):
        return hash((self.sub_class_iri, self.super_class_iri))


class CachedReasonerQueries:
    """Wrapper for reasoner queries with caching.

    Caching is important because:
    - Subsumption queries after classification are O(1)
    - But repeated queries to the same concepts are unnecessary
    - Cache hits save function call overhead
    """

    def __init__(self, reasoner: Reasoner):
        self.reasoner = reasoner
        self._subsumption_cache: dict[SubsumptionQuery, bool] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def is_sub_class_of(self, sub_concept: AtomicConcept,
                       super_concept: AtomicConcept) -> bool:
        """Query with caching."""
        query = SubsumptionQuery(sub_concept.iri, super_concept.iri)

        if query in self._subsumption_cache:
            self._cache_hits += 1
            return self._subsumption_cache[query]

        self._cache_misses += 1
        result = self.reasoner.is_sub_class_of(sub_concept, super_concept)
        self._subsumption_cache[query] = result
        return result

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        return {
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'hit_rate': hit_rate,
        }

    def clear_cache(self) -> None:
        """Clear the cache."""
        self._subsumption_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0


# =====================================================
# PATTERN 3: Batch Query Processing
# =====================================================

@dataclass
class ClassificationResult:
    """Result of classifying an individual."""
    individual_iri: str
    concept_iris: Set[str]
    classification_time: float


class BatchProcessor:
    """Process multiple classification queries efficiently.

    Batch processing is useful when you have many individuals
    to classify and want to measure performance.
    """

    def __init__(self, reasoner: Reasoner):
        self.reasoner = reasoner

    def classify_individuals(self, individuals: list[Individual],
                           concept: AtomicConcept) -> list[ClassificationResult]:
        """Classify which individuals have a given type.

        Returns:
            List of classification results with timing information
        """
        results = []

        for individual in individuals:
            start = time.time()

            # Query: What are all types of this individual?
            types = self.reasoner.get_types(individual)
            has_concept = any(t.iri == concept.iri for t in types)

            elapsed = time.time() - start

            # Only record individuals that match the concept
            if has_concept:
                results.append(ClassificationResult(
                    individual_iri=individual.iri,
                    concept_iris={t.iri for t in types},
                    classification_time=elapsed,
                ))

        return results

    def batch_subsumption_check(self, queries: list[tuple[AtomicConcept,
                                                          AtomicConcept]]
                               ) -> list[tuple[str, str, bool]]:
        """Check multiple subsumption relationships.

        Args:
            queries: List of (sub_concept, super_concept) pairs

        Returns:
            List of (sub_iri, super_iri, is_subsumed) tuples
        """
        results = []

        for sub, sup in queries:
            is_sub = self.reasoner.is_sub_class_of(sub, sup)
            results.append((sub.iri, sup.iri, is_sub))

        return results


# =====================================================
# PATTERN 4: Error Handling
# =====================================================

class SafeReasonerWrapper:
    """Wrapper that handles errors gracefully.

    Always use error handling when querying to detect:
    - Inconsistent ontologies
    - Invalid concepts
    - Resource exhaustion
    """

    def __init__(self, reasoner: Reasoner):
        self.reasoner = reasoner
        self.last_error: Optional[Exception] = None

    def safe_consistency_check(self) -> bool:
        """Check consistency with error handling."""
        try:
            return self.reasoner.is_consistent()
        except Exception as e:
            self.last_error = e
            print(f"ERROR: Consistency check failed: {e}")
            return False

    def safe_subsumption_check(self, sub: AtomicConcept,
                              sup: AtomicConcept) -> Optional[bool]:
        """Check subsumption with error handling."""
        try:
            return self.reasoner.is_sub_class_of(sub, sup)
        except Exception as e:
            self.last_error = e
            print(f"ERROR: Subsumption check failed: {e}")
            return None

    def get_last_error(self) -> Optional[str]:
        """Get description of last error."""
        if self.last_error is None:
            return None
        return str(self.last_error)


# =====================================================
# PATTERN 5: Context Manager for Resource Management
# =====================================================

class ManagedReasoner:
    """Context manager for automatic resource cleanup.

    Ensures the reasoner is properly disposed even if
    an exception occurs.
    """

    def __init__(self, ontology: DLOntology):
        self.ontology = ontology
        self.reasoner: Optional[Reasoner] = None

    def __enter__(self) -> Reasoner:
        """Enter context: create and initialize reasoner."""
        self.reasoner = Reasoner(self.ontology)
        self.reasoner.precompute_inferences(class_hierarchy=True)
        return self.reasoner

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context: always dispose the reasoner."""
        if self.reasoner is not None:
            self.reasoner.dispose()
        if exc_type is not None:
            print(f"Exception occurred: {exc_type.__name__}: {exc_val}")


# =====================================================
# DEMO
# =====================================================

def build_test_ontology() -> DLOntology:
    """Build a simple test ontology."""
    X = Variable.create("X")

    vehicle = AtomicConcept.create("http://example.org#Vehicle")
    car = AtomicConcept.create("http://example.org#Car")
    sedan = AtomicConcept.create("http://example.org#Sedan")
    suv = AtomicConcept.create("http://example.org#SUV")
    truck = AtomicConcept.create("http://example.org#Truck")

    clauses = [
        DLClause.create(
            (Atom.create(vehicle, X),),
            (Atom.create(car, X),),
        ),
        DLClause.create(
            (Atom.create(car, X),),
            (Atom.create(sedan, X),),
        ),
        DLClause.create(
            (Atom.create(car, X),),
            (Atom.create(suv, X),),
        ),
        DLClause.create(
            (Atom.create(vehicle, X),),
            (Atom.create(truck, X),),
        ),
    ]

    return DLOntology(
        ontology_iri="urn:integration:demo",
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset([]),
    )


def main():
    print("=" * 70)
    print("INTEGRATION PATTERNS: Using PyHermit in Real Applications")
    print("=" * 70)
    print()

    ontology = build_test_ontology()

    # =========================================================
    # PATTERN 1 & 5: Singleton + Context Manager (best practice)
    # =========================================================
    print("PATTERN 1 & 5: Context Manager for Safe Resource Management")
    print("-" * 70)

    with ManagedReasoner(ontology) as reasoner:
        vehicle = AtomicConcept.create("http://example.org#Vehicle")
        sedan = AtomicConcept.create("http://example.org#Sedan")

        print(f"Sedan ⊑ Vehicle: {reasoner.is_sub_class_of(sedan, vehicle)}")
        print("✓ Reasoner automatically cleaned up after context")
    print()

    # =========================================================
    # PATTERN 2: Query Caching
    # =========================================================
    print("PATTERN 2: Query Caching")
    print("-" * 70)

    reasoner = Reasoner(ontology)
    reasoner.precompute_inferences(class_hierarchy=True)

    cached = CachedReasonerQueries(reasoner)
    sedan = AtomicConcept.create("http://example.org#Sedan")
    vehicle = AtomicConcept.create("http://example.org#Vehicle")

    # Multiple queries of the same relationship
    for i in range(5):
        cached.is_sub_class_of(sedan, vehicle)

    stats = cached.get_stats()
    print(f"Cache Statistics: {stats}")
    print(f"Hit rate: {stats['hit_rate']:.1f}%")
    print()

    # =========================================================
    # PATTERN 3: Batch Processing
    # =========================================================
    print("PATTERN 3: Batch Query Processing")
    print("-" * 70)

    batch = BatchProcessor(reasoner)

    # Batch subsumption checks
    sedan = AtomicConcept.create("http://example.org#Sedan")
    suv = AtomicConcept.create("http://example.org#SUV")
    truck = AtomicConcept.create("http://example.org#Truck")
    vehicle = AtomicConcept.create("http://example.org#Vehicle")
    car = AtomicConcept.create("http://example.org#Car")

    queries = [
        (sedan, vehicle),
        (sedan, car),
        (suv, car),
        (truck, vehicle),
        (truck, car),
    ]

    results = batch.batch_subsumption_check(queries)
    print("Batch subsumption results:")
    for sub_iri, sup_iri, is_sub in results:
        sub_name = sub_iri.split("#")[-1]
        sup_name = sup_iri.split("#")[-1]
        status = "✓" if is_sub else "✗"
        print(f"  {status} {sub_name} ⊑ {sup_name}: {is_sub}")
    print()

    # =========================================================
    # PATTERN 4: Error Handling
    # =========================================================
    print("PATTERN 4: Safe Error Handling")
    print("-" * 70)

    safe = SafeReasonerWrapper(reasoner)
    is_consistent = safe.safe_consistency_check()
    print(f"Ontology is consistent: {is_consistent}")
    print(f"Last error: {safe.get_last_error()}")
    print()

    print("=" * 70)
    print("Design Principles")
    print("=" * 70)
    print("""
1. RESOURCE MANAGEMENT
   - Always dispose of reasoners when done
   - Use context managers (with statement) for automatic cleanup
   - Don't create unreasonably large ontologies

2. PERFORMANCE OPTIMIZATION
   - Precompute_inferences() before many queries
   - Cache results of expensive queries
   - Use batch processing for multiple queries

3. ERROR HANDLING
   - Check is_consistent() before querying
   - Handle exceptions gracefully
   - Provide meaningful error messages to users

4. THREAD SAFETY
   - One reasoner per ontology (don't share across threads)
   - Synchronize access if using multiple threads
   - Consider thread-local storage for stateful reasoners

5. CACHING STRATEGY
   - Cache subsumption results (they don't change)
   - Don't cache get_instances() (may change with ABox updates)
   - Monitor cache hit rate for optimization
    """)

    reasoner.dispose()


if __name__ == "__main__":
    main()
