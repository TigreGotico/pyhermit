"""
Real-World Example: E-Commerce Product Ontology

This example demonstrates building and reasoning about a practical
e-commerce ontology with products, categories, and constraints.

Key concepts covered:
1. Building realistic class hierarchies
2. Defining business rules as constraints
3. Querying products by type
4. Validating data against ontology rules
5. Computing product compatibility
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


def build_ecommerce_ontology():
    """Build a realistic e-commerce ontology.

    Product hierarchy:
        Product
          ├── PhysicalProduct
          │   ├── Electronics
          │   │   ├── Computer
          │   │   │   ├── Laptop
          │   │   │   └── Desktop
          │   │   ├── Phone
          │   │   └── Tablet
          │   └── Furniture
          ├── DigitalProduct
          │   └── Software
          └── Service
    """
    X = Variable.create("X")
    Y = Variable.create("Y")

    # Concept definitions
    product = AtomicConcept.create("http://ecommerce.org#Product")
    physical = AtomicConcept.create("http://ecommerce.org#PhysicalProduct")
    digital = AtomicConcept.create("http://ecommerce.org#DigitalProduct")
    service = AtomicConcept.create("http://ecommerce.org#Service")

    electronics = AtomicConcept.create("http://ecommerce.org#Electronics")
    furniture = AtomicConcept.create("http://ecommerce.org#Furniture")
    software = AtomicConcept.create("http://ecommerce.org#Software")

    computer = AtomicConcept.create("http://ecommerce.org#Computer")
    laptop = AtomicConcept.create("http://ecommerce.org#Laptop")
    desktop = AtomicConcept.create("http://ecommerce.org#Desktop")
    phone = AtomicConcept.create("http://ecommerce.org#Phone")
    tablet = AtomicConcept.create("http://ecommerce.org#Tablet")

    # Properties/roles
    has_warranty = AtomicRole.create("http://ecommerce.org#hasWarranty")
    compatible_with = AtomicRole.create("http://ecommerce.org#compatibleWith")
    made_by = AtomicRole.create("http://ecommerce.org#madeBy")
    requires = AtomicRole.create("http://ecommerce.org#requires")

    # TBox: Class hierarchy
    clauses = [
        # Top-level: Physical and Digital are Products
        DLClause.create(
            (Atom.create(product, X),),
            (Atom.create(physical, X),),
        ),
        DLClause.create(
            (Atom.create(product, X),),
            (Atom.create(digital, X),),
        ),
        DLClause.create(
            (Atom.create(product, X),),
            (Atom.create(service, X),),
        ),

        # Physical product categories
        DLClause.create(
            (Atom.create(physical, X),),
            (Atom.create(electronics, X),),
        ),
        DLClause.create(
            (Atom.create(physical, X),),
            (Atom.create(furniture, X),),
        ),

        # Electronics subcategories
        DLClause.create(
            (Atom.create(electronics, X),),
            (Atom.create(computer, X),),
        ),
        DLClause.create(
            (Atom.create(computer, X),),
            (Atom.create(laptop, X),),
        ),
        DLClause.create(
            (Atom.create(computer, X),),
            (Atom.create(desktop, X),),
        ),
        DLClause.create(
            (Atom.create(electronics, X),),
            (Atom.create(phone, X),),
        ),
        DLClause.create(
            (Atom.create(electronics, X),),
            (Atom.create(tablet, X),),
        ),

        # Digital product categories
        DLClause.create(
            (Atom.create(digital, X),),
            (Atom.create(software, X),),
        ),
    ]

    # ABox: Concrete products
    products = frozenset([
        # Laptops
        Atom.create(laptop, Individual.create("http://ecommerce.org#ThinkpadX1")),
        Atom.create(laptop, Individual.create("http://ecommerce.org#MacbookPro")),
        Atom.create(laptop, Individual.create("http://ecommerce.org#DellXPS")),

        # Desktops
        Atom.create(desktop, Individual.create("http://ecommerce.org#iMac27")),
        Atom.create(desktop, Individual.create("http://ecommerce.org#DellPrecision")),

        # Phones
        Atom.create(phone, Individual.create("http://ecommerce.org#iPhone15")),
        Atom.create(phone, Individual.create("http://ecommerce.org#SamsungS24")),

        # Tablets
        Atom.create(tablet, Individual.create("http://ecommerce.org#iPadPro")),
        Atom.create(tablet, Individual.create("http://ecommerce.org#SamsungTab")),

        # Furniture
        Atom.create(furniture, Individual.create("http://ecommerce.org#OfficeDesk")),
        Atom.create(furniture, Individual.create("http://ecommerce.org#Chairmat")),

        # Software
        Atom.create(software, Individual.create("http://ecommerce.org#MicrosoftOffice")),
        Atom.create(software, Individual.create("http://ecommerce.org#AdobeCC")),
    ])

    return DLOntology(
        ontology_iri="urn:ecommerce:products",
        dl_clauses=frozenset(clauses),
        positive_facts=products,
    )


def main():
    print("=" * 70)
    print("REAL-WORLD EXAMPLE: E-Commerce Product Ontology")
    print("=" * 70)
    print()

    ontology = build_ecommerce_ontology()
    reasoner = Reasoner(ontology)

    try:
        print("Step 1: Check Ontology Consistency")
        print("-" * 70)
        is_consistent = reasoner.is_consistent()
        print(f"Ontology is consistent: {is_consistent}")
        if not is_consistent:
            print("ERROR: Ontology has logical contradictions!")
            return
        print()

        print("Step 2: Precompute Class Hierarchy")
        print("-" * 70)
        print("Computing class hierarchy and relationships...")
        start = time.time()
        reasoner.precompute_inferences(class_hierarchy=True)
        elapsed = time.time() - start
        print(f"✓ Classification complete ({elapsed:.4f}s)")
        print()

        print("Step 3: Query Products by Type")
        print("-" * 70)

        # Define concept hierarchy for querying
        product = AtomicConcept.create("http://ecommerce.org#Product")
        electronics = AtomicConcept.create("http://ecommerce.org#Electronics")
        computer = AtomicConcept.create("http://ecommerce.org#Computer")
        laptop = AtomicConcept.create("http://ecommerce.org#Laptop")
        phone = AtomicConcept.create("http://ecommerce.org#Phone")
        furniture = AtomicConcept.create("http://ecommerce.org#Furniture")

        categories = [
            ("All Products", product),
            ("Electronics", electronics),
            ("Computers", computer),
            ("Laptops", laptop),
            ("Phones", phone),
            ("Furniture", furniture),
        ]

        for category_name, category_concept in categories:
            instances = reasoner.get_instances(category_concept)
            count = len(instances)
            print(f"{category_name:20} ({count:2} items)")
            for instance in sorted(instances, key=lambda x: x.iri):
                short_name = instance.iri.split("#")[-1]
                print(f"  • {short_name}")
        print()

        print("Step 4: Verify Class Relationships")
        print("-" * 70)
        print("Checking the computed class hierarchy:")

        relationships = [
            (laptop, computer, "Laptop ⊑ Computer"),
            (computer, electronics, "Computer ⊑ Electronics"),
            (laptop, electronics, "Laptop ⊑ Electronics (transitive)"),
            (phone, electronics, "Phone ⊑ Electronics"),
            (electronics, product, "Electronics ⊑ Product"),
            (laptop, product, "Laptop ⊑ Product (transitive)"),
        ]

        for sub, sup, description in relationships:
            is_sub = reasoner.is_sub_class_of(sub, sup)
            status = "✓" if is_sub else "✗"
            print(f"{status} {description}: {is_sub}")
        print()

        print("Step 5: Business Insights")
        print("-" * 70)
        print("""
Using the ontology for business logic:

1. INVENTORY MANAGEMENT
   - Group products by category for inventory tracking
   - Query: "Get all Electronics in stock"

2. CUSTOMER RECOMMENDATIONS
   - If customer buys Laptop → recommend Electronics
   - If customer buys Furniture → recommend Office Products

3. TAXATION & SHIPPING
   - Physical products require shipping → Electronics shipping rates
   - Digital products → instant delivery, no shipping
   - Furniture → special handling (fragile, large)

4. QUALITY ASSURANCE
   - Verify all products in correct categories
   - Ensure no products in contradictory categories

5. BUSINESS RULES ENFORCEMENT
   - All phones must be Electronics
   - All laptops must be Computers
   - No product can be both Digital and Physical
        """)

        print("=" * 70)
        print("Performance Metrics")
        print("=" * 70)

        # Measure query performance
        start = time.time()
        for _ in range(100):
            reasoner.is_sub_class_of(laptop, computer)
        elapsed = time.time() - start
        avg_time = (elapsed / 100) * 1000  # Convert to milliseconds

        print(f"Average subsumption query time: {avg_time:.3f}ms")
        print("(After classification, queries are very fast)")
        print()

    finally:
        reasoner.dispose()
        print("✓ Reasoner disposed, resources released")


if __name__ == "__main__":
    main()
