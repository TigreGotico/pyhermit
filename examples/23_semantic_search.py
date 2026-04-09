"""
Semantic Search and Discovery

This example demonstrates:
1. Semantic search beyond keyword matching
2. Finding semantically similar entities
3. Concept expansion for search
4. Ranking results by relevance
5. Cross-domain search

Semantic search goes beyond string matching by understanding
the meaning of concepts and relationships, enabling more
intelligent and useful search results.
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

    # Build a product ontology for semantic search
    product = AtomicConcept.create("http://example.org/shop#Product")
    electronics = AtomicConcept.create("http://example.org/shop#Electronics")
    computer = AtomicConcept.create("http://example.org/shop#Computer")
    laptop = AtomicConcept.create("http://example.org/shop#Laptop")
    notebook = AtomicConcept.create("http://example.org/shop#Notebook")
    gaming_laptop = AtomicConcept.create("http://example.org/shop#GamingLaptop")
    budget_laptop = AtomicConcept.create("http://example.org/shop#BudgetLaptop")

    phone = AtomicConcept.create("http://example.org/shop#Phone")
    smartphone = AtomicConcept.create("http://example.org/shop#Smartphone")
    tablet = AtomicConcept.create("http://example.org/shop#Tablet")

    portable = AtomicConcept.create("http://example.org/shop#Portable")
    high_performance = AtomicConcept.create("http://example.org/shop#HighPerformance")
    budget_friendly = AtomicConcept.create("http://example.org/shop#BudgetFriendly")

    # Roles
    has_category = AtomicRole.create("http://example.org/shop#hasCategory")
    similar_to = AtomicRole.create("http://example.org/shop#similarTo")

    # TBox: Ontology for product hierarchy
    clauses = [
        # Computer ⊑ Electronics
        DLClause.create(
            (Atom.create(electronics, X),),
            (Atom.create(computer, X),),
        ),
        # Laptop ⊑ Computer
        DLClause.create(
            (Atom.create(computer, X),),
            (Atom.create(laptop, X),),
        ),
        # Notebook ⊑ Laptop
        DLClause.create(
            (Atom.create(laptop, X),),
            (Atom.create(notebook, X),),
        ),
        # GamingLaptop ⊑ Laptop
        DLClause.create(
            (Atom.create(laptop, X),),
            (Atom.create(gaming_laptop, X),),
        ),
        # BudgetLaptop ⊑ Laptop
        DLClause.create(
            (Atom.create(laptop, X),),
            (Atom.create(budget_laptop, X),),
        ),
        # Phone ⊑ Electronics
        DLClause.create(
            (Atom.create(electronics, X),),
            (Atom.create(phone, X),),
        ),
        # Smartphone ⊑ Phone
        DLClause.create(
            (Atom.create(phone, X),),
            (Atom.create(smartphone, X),),
        ),
        # Tablet ⊑ Electronics
        DLClause.create(
            (Atom.create(electronics, X),),
            (Atom.create(tablet, X),),
        ),
        # Portable products
        # Laptop ⊑ Portable
        DLClause.create(
            (Atom.create(portable, X),),
            (Atom.create(laptop, X),),
        ),
        # Smartphone ⊑ Portable
        DLClause.create(
            (Atom.create(portable, X),),
            (Atom.create(smartphone, X),),
        ),
        # Tablet ⊑ Portable
        DLClause.create(
            (Atom.create(portable, X),),
            (Atom.create(tablet, X),),
        ),
    ]

    # Products
    macbook = Individual.create("http://example.org/shop#MacbookPro")
    thinkpad = Individual.create("http://example.org/shop#ThinkpadX1")
    budget_laptop_ind = Individual.create("http://example.org/shop#BudgetLaptop2000")
    gaming_laptop_ind = Individual.create("http://example.org/shop#AlienwareLaptop")
    iphone = Individual.create("http://example.org/shop#iPhone15")
    ipad = Individual.create("http://example.org/shop#iPad")

    facts = frozenset([
        # Product types
        Atom.create(product, macbook),
        Atom.create(notebook, macbook),
        Atom.create(high_performance, macbook),
        Atom.create(product, thinkpad),
        Atom.create(notebook, thinkpad),
        Atom.create(product, budget_laptop_ind),
        Atom.create(budget_laptop, budget_laptop_ind),
        Atom.create(budget_friendly, budget_laptop_ind),
        Atom.create(product, gaming_laptop_ind),
        Atom.create(gaming_laptop, gaming_laptop_ind),
        Atom.create(high_performance, gaming_laptop_ind),
        Atom.create(product, iphone),
        Atom.create(smartphone, iphone),
        Atom.create(portable, iphone),
        Atom.create(product, ipad),
        Atom.create(tablet, ipad),
        Atom.create(portable, ipad),
    ])

    ontology = DLOntology(
        ontology_iri="urn:tutorial:semantic_search",
        dl_clauses=frozenset(clauses),
        positive_facts=facts,
    )

    reasoner = Reasoner(ontology)

    try:
        reasoner.precompute_inferences()

        print("=" * 70)
        print("SEMANTIC SEARCH AND DISCOVERY")
        print("=" * 70)
        print()

        print("Search Example 1: User searches for 'laptop'")
        print("-" * 70)

        # Direct search
        laptops = reasoner.get_instances(laptop)
        print(f"Direct match (Laptop): {len(laptops)} products")
        for l in laptops:
            print(f"  - {l.iri.split('#')[-1]}")

        print()
        print("Semantic expansion (all subtypes of Laptop):")
        for l in laptops:
            print(f"  - {l.iri.split('#')[-1]}")

        print()

        print("Search Example 2: User searches for 'portable device'")
        print("-" * 70)

        portables = reasoner.get_instances(portable)
        print(f"Results for 'Portable': {len(portables)} products")
        for p in sorted(portables, key=lambda x: x.iri):
            name = p.iri.split('#')[-1]
            product_type = []
            if reasoner.has_type(p, laptop):
                product_type.append("Laptop")
            if reasoner.has_type(p, smartphone):
                product_type.append("Smartphone")
            if reasoner.has_type(p, tablet):
                product_type.append("Tablet")
            types_str = " / ".join(product_type) if product_type else "Unknown"
            print(f"  - {name} ({types_str})")

        print()

        print("Search Example 3: User searches for 'high-performance devices'")
        print("-" * 70)

        high_perf = reasoner.get_instances(high_performance)
        print(f"Results for 'High-Performance': {len(high_perf)} products")
        for hp in sorted(high_perf, key=lambda x: x.iri):
            name = hp.iri.split('#')[-1]
            print(f"  - {name}")

        print()

        print("Search Example 4: Find alternatives to MacbookPro")
        print("-" * 70)

        # Get products in same category
        macbook_types = reasoner.get_types(macbook)
        print(f"MacbookPro is a: {', '.join([t.iri.split('#')[-1] for t in macbook_types if t.iri != 'http://www.w3.org/2002/07/owl#Thing'])}")

        print()
        print("Alternative products:")

        # Find all products that share at least one type with MacbookPro
        alternatives = []
        for product_ind in reasoner.get_instances(product):
            if product_ind == macbook:
                continue
            # Check if they share any category
            shared_types = reasoner.get_types(product_ind) & macbook_types
            if shared_types:
                # Filter out generic types
                shared_types = {
                    t for t in shared_types
                    if t.iri not in [
                        "http://www.w3.org/2002/07/owl#Thing",
                        "http://example.org/shop#Product",
                    ]
                }
                if shared_types:
                    alternatives.append((product_ind, shared_types))

        for alt_product, shared in sorted(alternatives, key=lambda x: x[0].iri):
            name = alt_product.iri.split('#')[-1]
            shared_str = ", ".join([t.iri.split('#')[-1] for t in shared])
            print(f"  - {name} (shared: {shared_str})")

        print()

        print("=" * 70)
        print("Semantic Search Strategies")
        print("=" * 70)
        print("""
SEMANTIC SEARCH TECHNIQUES:

1. CONCEPT EXPANSION
   Query: "laptop"
   Expanded to: Laptop | Notebook | GamingLaptop | BudgetLaptop
   Retrieves all subtypes automatically

2. HIERARCHICAL SEARCH
   Query: "portable device"
   Result: All products of type Portable and its subtypes
   Includes: Laptops, Smartphones, Tablets

3. ATTRIBUTE-BASED SEARCH
   Query: "high-performance"
   Result: All products marked as high-performance
   Semantic similarity: Find products with similar attributes

4. CROSS-CATEGORY DISCOVERY
   Query: Find alternatives to MacbookPro
   Logic: Find other products sharing same category
   Result: ThinkpadX1 (both are notebooks)

SEARCH PATTERNS:

Pattern 1: Direct Type Matching
    results = reasoner.get_instances(search_concept)

Pattern 2: Semantic Expansion
    base_types = ontology.get_all_subtypes(search_concept)
    results = union(reasoner.get_instances(t) for t in base_types)

Pattern 3: Attribute Matching
    results = [p for p in products
               if reasoner.has_type(p, attribute_concept)]

Pattern 4: Relationship-Based Discovery
    related = [p for p in products
               if reasoner.has_role_relationship(p, relates_to, query)]

RANKING STRATEGIES:

1. SPECIFICITY RANKING
   Exact match > Subtype match > Supertype match

2. POPULARITY RANKING
   More attributes = more relevant

3. RECENCY RANKING
   Newer products ranked higher

4. HYBRID RANKING
   Combine multiple factors with weights

IMPLEMENTATION:

class SemanticSearchEngine:
    def __init__(self, reasoner):
        self.reasoner = reasoner

    def search(self, query_concept, limit=10):
        # Expand query to all subtypes
        all_types = self.get_all_subtypes(query_concept)

        # Get all matching individuals
        results = []
        for type_concept in all_types:
            results.extend(self.reasoner.get_instances(type_concept))

        # Rank and return
        return self.rank_results(results)[:limit]

    def get_all_subtypes(self, concept):
        types = {concept}
        # Find all subtypes recursively
        for c in self.reasoner.get_sub_classes(concept):
            types.update(self.get_all_subtypes(c))
        return types

ADVANTAGES:

✓ Finds results users expect (semantic intent)
✓ Handles synonyms and related terms
✓ Discovers related products
✓ Reduces "no results" failures
✓ Improves user satisfaction

CHALLENGES:

⚠ Ontology must be comprehensive
⚠ Requires careful category design
⚠ Performance with large result sets
⚠ Ranking quality depends on attributes
        """)

    finally:
        reasoner.dispose()


if __name__ == "__main__":
    main()
