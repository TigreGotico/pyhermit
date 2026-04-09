"""
Configuration and Performance Tuning

This example demonstrates:
1. Using reasoner configuration options
2. Selecting different blocking strategies
3. Setting timeouts for long-running queries
4. Monitoring reasoning performance
5. Trade-offs between soundness and performance

The reasoner can be configured to optimize for different scenarios:
- Correctness (full classification, may be slow)
- Speed (approximate reasoning, may miss some inferences)
- Memory usage (suitable for embedded systems)
"""

from hermit import Reasoner
from hermit.configuration import Configuration, BlockingStrategyType
from hermit.model import (
    DLOntology,
    Atom,
    AtomicConcept,
    Variable,
    DLClause,
)
import time


def create_test_ontology(size: int = 5) -> DLOntology:
    """Create a test ontology with a deep class hierarchy.

    Args:
        size: Depth of the class hierarchy (more = slower to reason)
    """
    X = Variable.create("X")

    clauses = []
    prev_concept = None

    # Create a chain of subsumptions: C0 ⊑ C1 ⊑ C2 ⊑ ... ⊑ Cn
    for i in range(size):
        concept = AtomicConcept.create(f"http://example.org#Class{i}")

        if prev_concept is not None:
            # concept ⊑ prev_concept
            clauses.append(DLClause.create(
                (Atom.create(prev_concept, X),),
                (Atom.create(concept, X),),
            ))

        prev_concept = concept

    return DLOntology(
        ontology_iri="urn:tutorial:performance",
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset([]),
    )


def example_1_default_configuration():
    """Example 1: Using default configuration."""
    print("=" * 60)
    print("EXAMPLE 1: Default Configuration")
    print("=" * 60)
    print()

    ontology = create_test_ontology(size=10)
    config = Configuration()  # Default configuration

    print(f"Blocking Strategy: {config.blocking_strategy_type}")
    print(f"Direct Blocking Type: {config.direct_blocking_type}")
    print(f"Individual Task Timeout: {config.individual_task_timeout}ms")
    print()

    reasoner = Reasoner(ontology, config)

    try:
        start = time.time()
        is_consistent = reasoner.is_consistent()
        elapsed = time.time() - start

        print(f"Consistency: {is_consistent}")
        print(f"Time: {elapsed:.4f}s")
    finally:
        reasoner.dispose()

    print()


def example_2_ancestor_blocking():
    """Example 2: Ancestor blocking (simpler, faster)."""
    print("=" * 60)
    print("EXAMPLE 2: Ancestor Blocking")
    print("=" * 60)
    print()

    ontology = create_test_ontology(size=10)
    config = Configuration()
    config.blocking_strategy_type = BlockingStrategyType.ANCESTOR

    print(f"Blocking Strategy: {config.blocking_strategy_type}")
    print("Ancestor blocking is the simplest form of blocking.")
    print("It only checks a node against its ancestors (parent chain).")
    print()

    reasoner = Reasoner(ontology, config)

    try:
        start = time.time()
        is_consistent = reasoner.is_consistent()
        elapsed = time.time() - start

        print(f"Consistency: {is_consistent}")
        print(f"Time: {elapsed:.4f}s")
    finally:
        reasoner.dispose()

    print()


def example_3_different_blocking_strategies():
    """Example 3: Comparing different blocking strategies."""
    print("=" * 60)
    print("EXAMPLE 3: Comparing Blocking Strategies")
    print("=" * 60)
    print()

    ontology = create_test_ontology(size=8)

    strategies = [
        BlockingStrategyType.ANCESTOR,
        BlockingStrategyType.COMPLEX_CORE,
    ]

    results = []
    for strategy in strategies:
        config = Configuration()
        config.blocking_strategy_type = strategy

        reasoner = Reasoner(ontology, config)

        try:
            start = time.time()
            is_consistent = reasoner.is_consistent()
            elapsed = time.time() - start

            results.append({
                'strategy': strategy.value,
                'consistent': is_consistent,
                'time': elapsed
            })
        finally:
            reasoner.dispose()

    print("Strategy Comparison:")
    print("-" * 60)
    print(f"{'Strategy':<20} {'Consistent':<15} {'Time (s)':<15}")
    print("-" * 60)

    for result in results:
        print(f"{result['strategy']:<20} {str(result['consistent']):<15} {result['time']:<15.4f}")

    print()


def example_4_timeout_configuration():
    """Example 4: Setting timeout limits."""
    print("=" * 60)
    print("EXAMPLE 4: Timeout Configuration")
    print("=" * 60)
    print()

    ontology = create_test_ontology(size=20)  # Deep hierarchy

    configs = [
        (1000, "1 second"),
        (5000, "5 seconds"),
        (30000, "30 seconds"),
    ]

    print("Timeouts limit how long a single reasoning task can run.")
    print("This is useful for interactive applications or service limits.")
    print()

    for timeout_ms, description in configs:
        config = Configuration()
        config.individual_task_timeout = timeout_ms

        reasoner = Reasoner(ontology, config)

        try:
            print(f"Timeout: {description} ({timeout_ms}ms)")

            start = time.time()
            try:
                is_consistent = reasoner.is_consistent()
                elapsed = time.time() - start
                print(f"  Completed in {elapsed:.4f}s - Result: {is_consistent}")
            except TimeoutError:
                elapsed = time.time() - start
                print(f"  TIMEOUT after {elapsed:.4f}s")
        finally:
            reasoner.dispose()

    print()


def example_5_exact_reasoning():
    """Example 5: Exact vs approximate reasoning."""
    print("=" * 60)
    print("EXAMPLE 5: Exact Reasoning Guarantees")
    print("=" * 60)
    print()

    ontology = create_test_ontology(size=10)
    config = Configuration()

    reasoner = Reasoner(ontology, config)

    try:
        # Check consistency with the current configuration
        is_consistent = reasoner.is_consistent()

        print(f"Ontology is consistent: {is_consistent}")
        print(f"Configuration blocking strategy: {config.blocking_strategy_type}")
        print()

        print("""
About Reasoning Strategies in HermiT:
✓ All inferences are logically sound and complete
✓ The tableau method finds all consequences of the ontology
✓ Different blocking strategies affect performance:
  - ANCESTOR: Simplest, may create larger models
  - ANYWHERE: More sophisticated, smaller models
  - COMPLEX_CORE / SIMPLE_CORE: Intermediate strategies
  - OPTIMAL: Automatically chooses best strategy

HermiT guarantees exact reasoning regardless of strategy!
Trade-off: Different strategies affect reasoning speed.
            """)
    finally:
        reasoner.dispose()

    print()


def example_6_precomputation():
    """Example 6: Benefits of precomputing inferences."""
    print("=" * 60)
    print("EXAMPLE 6: Precomputation Benefits")
    print("=" * 60)
    print()

    ontology = create_test_ontology(size=15)

    reasoner = Reasoner(ontology)

    try:
        # Approach 1: Without precomputation
        print("Approach 1: Query without precomputation")
        print("-" * 40)

        start = time.time()
        result = reasoner.is_consistent()
        time1 = time.time() - start
        print(f"First consistency check: {time1:.4f}s")

        start = time.time()
        result = reasoner.is_consistent()
        time2 = time.time() - start
        print(f"Second consistency check: {time2:.4f}s")

        reasoner.dispose()

    except Exception as e:
        print(f"Note: {e}")

    # Approach 2: With precomputation
    print()
    print("Approach 2: Precompute then query")
    print("-" * 40)

    reasoner = Reasoner(ontology)

    try:
        start = time.time()
        reasoner.precompute_inferences(class_hierarchy=True)
        precomp_time = time.time() - start
        print(f"Precomputation: {precomp_time:.4f}s")

        start = time.time()
        result = reasoner.is_consistent()
        time1 = time.time() - start
        print(f"Query 1: {time1:.4f}s")

        start = time.time()
        result = reasoner.is_consistent()
        time2 = time.time() - start
        print(f"Query 2: {time2:.4f}s")

        print()
        print(f"Precomputation helps when you have many queries!")
    finally:
        reasoner.dispose()

    print()


if __name__ == "__main__":
    # Run all examples
    example_1_default_configuration()
    example_2_ancestor_blocking()
    example_3_different_blocking_strategies()
    example_4_timeout_configuration()
    example_5_exact_reasoning()
    example_6_precomputation()

    print("=" * 60)
    print("Configuration Summary")
    print("=" * 60)
    print("""
Key configuration options:

1. **Blocking Strategy** (BlockingStrategyType)
   - ANCESTOR: Simplest, fastest
   - PAIRWISE_DIRECT: More complex, complete
   - ANYWHERE: Most complete, slowest

2. **Individual Task Timeout** (milliseconds)
   - Default: 600000 (10 minutes)
   - Set lower for time-critical applications

3. **Direct Blocking Type** (DirectBlockingType)
   - OPTIMAL: Best choice for most cases
   - SINGLE: Single blocking (faster, less complete)
   - PAIR_WISE: Pair-wise blocking (slower, more complete)

4. **Monitor Type** (TableauMonitorType)
   - NO_MONITOR: Fast (no tracking)
   - TIMING: Track timing information
   - DEBUGGER_*: Debug reasoning process

5. **Precomputation**
   - Use precompute_inferences() for multiple queries
   - Trade startup time for query speed

Choose based on your needs:
- Correctness: Use PAIRWISE_DIRECT blocking
- Speed: Use ANCESTOR blocking
- Accuracy: Set generous timeouts
- Responsiveness: Set low timeouts
    """)
