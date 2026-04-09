"""
Performance Analysis and Benchmarking

This example demonstrates:
1. Measuring reasoning time
2. Comparing different blocking strategies
3. Impact of ontology complexity
4. Precomputation vs on-demand reasoning
5. Scalability analysis

Understanding performance characteristics is crucial for
deploying ontology-based systems in production environments.
"""

import time
from hermit import Reasoner
from hermit.configuration import Configuration, BlockingStrategyType
from hermit.model import (
    DLOntology,
    Atom,
    AtomicConcept,
    AtomicRole,
    Variable,
    DLClause,
    Individual,
)


def measure_time(func):
    """Decorator to measure execution time."""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        return result, elapsed
    return wrapper


def create_product_ontology(num_categories: int = 10, num_products: int = 50):
    """Create a scalable product ontology."""
    X = Variable.create("X")
    Y = Variable.create("Y")

    # Create category hierarchy
    categories = []
    for i in range(num_categories):
        cat = AtomicConcept.create(f"http://example.org#Category{i}")
        categories.append(cat)

    # Create products
    products = []
    for i in range(num_products):
        prod = Individual.create(f"http://example.org#Product{i}")
        products.append(prod)

    # Create roles
    belongs_to = AtomicRole.create("http://example.org#belongsTo")
    has_supplier = AtomicRole.create("http://example.org#hasSupplier")

    # Build hierarchy (linear for simplicity)
    clauses = []
    for i in range(len(categories) - 1):
        clauses.append(
            DLClause.create(
                (Atom.create(categories[i], X),),
                (Atom.create(categories[i + 1], X),),
            )
        )

    # Add facts
    facts = []
    for i, prod in enumerate(products):
        # Assign products to categories
        cat_idx = i % len(categories)
        facts.append(Atom.create(categories[cat_idx], prod))
        facts.append(
            Atom.create(
                belongs_to,
                prod,
                Individual.create(f"http://example.org#Supplier{i % 5}"),
            )
        )

    return DLOntology(
        ontology_iri="urn:benchmark:products",
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset(facts),
    ), categories, products


def main():
    print("=" * 70)
    print("PERFORMANCE ANALYSIS AND BENCHMARKING")
    print("=" * 70)
    print()

    # Test 1: Impact of ontology size
    print("TEST 1: Scalability - Increasing Ontology Size")
    print("-" * 70)

    test_configs = [
        (5, 20, "Small"),
        (10, 50, "Medium"),
        (15, 100, "Large"),
    ]

    times = {"consistency": [], "hierarchy": [], "instances": []}

    for num_cats, num_prods, label in test_configs:
        ontology, categories, products = create_product_ontology(num_cats, num_prods)
        reasoner = Reasoner(ontology)

        # Measure consistency check
        @measure_time
        def check_consistency():
            return reasoner.is_consistent()

        consistent, cons_time = check_consistency()
        times["consistency"].append(cons_time)

        # Measure hierarchy computation
        @measure_time
        def compute_hierarchy():
            reasoner.precompute_inferences()

        _, hier_time = compute_hierarchy()
        times["hierarchy"].append(hier_time)

        # Measure instance retrieval
        @measure_time
        def retrieve_instances():
            return reasoner.get_instances(categories[0])

        instances, inst_time = retrieve_instances()
        times["instances"].append(inst_time)

        print(
            f"{label:8} (cats={num_cats:2}, prods={num_prods:3}): "
            f"consistency={cons_time:7.4f}s, "
            f"hierarchy={hier_time:7.4f}s, "
            f"instances={inst_time:7.4f}s"
        )

        reasoner.dispose()

    print()

    # Test 2: Different blocking strategies
    print("TEST 2: Blocking Strategy Comparison")
    print("-" * 70)

    ontology, categories, products = create_product_ontology(10, 50)

    strategies = [
        (BlockingStrategyType.OPTIMAL, "OPTIMAL"),
        (BlockingStrategyType.ANCESTOR, "ANCESTOR"),
        (BlockingStrategyType.COMPLEX_CORE, "COMPLEX_CORE"),
    ]

    for strategy_type, name in strategies:
        config = Configuration()
        config.blocking_strategy_type = strategy_type

        reasoner = Reasoner(ontology, configuration=config)

        @measure_time
        def test_consistency():
            return reasoner.is_consistent()

        _, time_taken = test_consistency()
        print(f"  {name:15}: {time_taken:7.4f}s")

        reasoner.dispose()

    print()

    # Test 3: Precomputation impact
    print("TEST 3: Precomputation Impact on Query Performance")
    print("-" * 70)

    ontology, categories, products = create_product_ontology(10, 50)
    reasoner = Reasoner(ontology)

    # Cold queries (no precomputation)
    print("  Without precomputation (cold queries):")
    @measure_time
    def cold_query_1():
        return reasoner.get_instances(categories[0])

    _, time1 = cold_query_1()
    print(f"    First query:  {time1:7.4f}s")

    @measure_time
    def cold_query_2():
        return reasoner.get_instances(categories[1])

    _, time2 = cold_query_2()
    print(f"    Second query: {time2:7.4f}s")

    # Precompute
    print("  With precomputation (warm queries):")

    @measure_time
    def precompute():
        reasoner.precompute_inferences()

    _, precomp_time = precompute()
    print(f"    Precomputation: {precomp_time:7.4f}s")

    @measure_time
    def warm_query_1():
        return reasoner.get_instances(categories[0])

    _, time3 = warm_query_1()
    print(f"    First query:  {time3:7.4f}s")

    @measure_time
    def warm_query_2():
        return reasoner.get_instances(categories[1])

    _, time4 = warm_query_2()
    print(f"    Second query: {time4:7.4f}s")

    reasoner.dispose()
    print()

    # Test 4: Operation costs
    print("TEST 4: Cost of Different Operations")
    print("-" * 70)

    ontology, categories, products = create_product_ontology(10, 50)
    reasoner = Reasoner(ontology)
    reasoner.precompute_inferences()

    # Consistency check
    @measure_time
    def test_is_consistent():
        return reasoner.is_consistent()

    _, cons_time = test_is_consistent()

    # Subsumption check
    @measure_time
    def test_subsumption():
        return reasoner.is_sub_class_of(categories[0], categories[-1])

    _, subs_time = test_subsumption()

    # Satisfiability check
    @measure_time
    def test_satisfiability():
        return reasoner.is_satisfiable(categories[0])

    _, sat_time = test_satisfiability()

    # Instance retrieval (small set)
    @measure_time
    def test_instances():
        return reasoner.get_instances(categories[0])

    _, inst_time = test_instances()

    # Type checking
    @measure_time
    def test_type():
        return reasoner.has_type(products[0], categories[0])

    _, type_time = test_type()

    print(f"  Consistency:      {cons_time:7.4f}s")
    print(f"  Subsumption:      {subs_time:7.4f}s")
    print(f"  Satisfiability:   {sat_time:7.4f}s")
    print(f"  Instance retrieval: {inst_time:7.4f}s")
    print(f"  Type checking:    {type_time:7.4f}s")

    reasoner.dispose()
    print()

    print("=" * 70)
    print("Performance Guidelines and Best Practices")
    print("=" * 70)
    print("""
TIMING CHARACTERISTICS:

Consistency Check (~ms):
  ✓ Usually very fast for most ontologies
  ✓ Scales with ontology complexity
  ✓ Good for quick validation

Subsumption Checking (~ms):
  ✓ Fast for individual queries
  ✓ Precompute if checking many pairs
  ✓ Computed as part of hierarchy

Instance Retrieval (~10-100ms):
  ✓ Requires tableau expansion
  ✓ Faster with precomputation
  ✓ Scales with number of individuals

Type Checking (~1-10ms):
  ✓ Very fast for direct types
  ✓ Slower for transitive inference
  ✓ Can be batched

Precomputation (~100-1000ms):
  ✓ One-time cost at startup
  ✓ Speeds up repeated queries
  ✓ Recommended for batch operations

OPTIMIZATION STRATEGIES:

1. STARTUP PHASE
   ontology = load_ontology(...)
   reasoner = Reasoner(ontology)
   reasoner.precompute_inferences()  # ~100-500ms

2. QUERY PHASE
   # Now queries are ~10-100x faster
   for query in queries:
       result = reasoner.is_sub_class_of(a, b)  # ~1ms

3. BLOCKING STRATEGY SELECTION
   - OPTIMAL: Best for correctness, slower
   - ANCESTOR: Simple blocking, faster
   - COMPLEX_CORE: Balance between speed and correctness

4. ONTOLOGY DESIGN
   - Limit cardinality constraints (expensive)
   - Avoid very deep hierarchies (slow)
   - Use atomic roles when possible
   - Minimize existential quantification

5. BATCH OPERATIONS
   # Better: Batch before reasoning
   instances = reasoner.get_instances(concept)
   for inst in instances:
       process(inst)

   # Worse: Individual queries
   for inst in all_individuals:
       if reasoner.has_type(inst, concept):
           process(inst)

DEPLOYMENT RECOMMENDATIONS:

- Small ontologies (<1000 individuals): Use on-demand
- Medium ontologies (1000-10K): Precompute at startup
- Large ontologies (10K+): Consider caching results
- Real-time systems: Cache precomputed results
- Batch systems: Use precomputation with batching

MEMORY CONSIDERATIONS:

- Tableau expansion creates intermediate nodes
- Precomputation trades time for memory
- Monitor memory usage with large ontologies
- Consider timeout settings for very large reasonings
    """)


if __name__ == "__main__":
    main()
