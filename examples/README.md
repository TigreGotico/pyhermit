# PyHermit Examples — Learning Through Tutorial Progression

Welcome to the comprehensive PyHermit examples collection. This folder contains 15 self-contained, runnable examples that progressively teach you how to use the Python OWL 2 DL reasoner.

## Overview

**Total Examples: 20**
- **Beginner Track (01-05):** Learn core concepts (consistency, subsumption, properties, instances, cardinality)
- **Intermediate Track (06-10):** Real-world patterns (disjointness, complex reasoning, OWL loading, configuration)
- **Advanced Track (11-14, 17):** Integration and special topics (e-commerce, design patterns, testing, inverse roles, contradictions)
- **Advanced+ Track (15-16, 18-20):** Advanced reasoning patterns (multiple inheritance, queries, nominalsI, performance, multi-domain)

All examples are **self-contained and runnable**:
```bash
python 01_hello_world.py
python 02_class_hierarchy.py
# ... and so on
```

## Quick Start

### Run the first example
```bash
python examples/01_hello_world.py
```

### Run all examples
```bash
for i in {01..14} 15 16 17 18 19 20; do
    python examples/${i}_*.py
done
```

### Run with output capture
```bash
python examples/03_object_properties.py > output.txt 2>&1
```

## Examples by Category

### Beginner Track (01-05)

#### 01_hello_world.py
**Purpose:** Basic PyHermit workflow
- Create an ontology with simple subsumption
- Check consistency
- Query concept relationships
- **Key Concepts:** Consistency, satisfiability, subsumption, equivalence
- **Learning Time:** 10 minutes
- **Difficulty:** ⭐

#### 02_class_hierarchy.py
**Purpose:** Multi-level class hierarchies and transitive inference
- Build class hierarchies (Animal → Mammal → Dog)
- Demonstrate transitive subsumption closure
- Query hierarchical relationships
- **Key Concepts:** Hierarchy computation, transitive closure
- **Learning Time:** 10 minutes
- **Difficulty:** ⭐⭐

#### 03_object_properties.py ⭐ (FIXED)
**Purpose:** Object properties and role relationships
- Define roles/properties connecting individuals
- Query role relationships (now working correctly!)
- Type inference from role assertions
- **Key Concepts:** Roles, relationships, object properties
- **Learning Time:** 10 minutes
- **Status:** Role relationship queries now return correct results ✓

#### 04_instance_retrieval.py
**Purpose:** Working with instances and type checking
- Create individuals with types
- Retrieve instances of a class
- Check individual types
- Query role relationships between individuals
- **Key Concepts:** ABox assertions, instance retrieval, type checking
- **Learning Time:** 10 minutes
- **Difficulty:** ⭐⭐

#### 05_cardinality_restrictions.py
**Purpose:** Cardinality constraints and restrictions
- Define minimum and maximum cardinality
- Explain how tableau enforces constraints
- Model real-world constraints (exactly 1 engine per car)
- **Key Concepts:** Cardinality, constraints, model expansion
- **Learning Time:** 15 minutes
- **Difficulty:** ⭐⭐⭐

### Intermediate Track (06-10)

#### 06_disjointness_and_negation.py
**Purpose:** Mutually exclusive concepts
- Define disjoint classes
- Explain limitations of simplified encoding
- Demonstrate concept incompatibility
- **Key Concepts:** Disjointness, negation, concept incompatibility
- **Learning Time:** 15 minutes
- **Note:** Simplified encoding for educational purposes

#### 07_advanced_reasoning.py
**Purpose:** Complex organizational ontology with deep reasoning
- Role hierarchies and transitive roles
- Complex class hierarchies
- Infer organizational structure from facts
- **Key Concepts:** Complex hierarchies, role reasoning
- **Learning Time:** 15 minutes
- **Difficulty:** ⭐⭐⭐

#### 08_loading_owl_files.py
**Purpose:** Integration with OWL file format
- Shows how to load external OWL ontologies
- Example workflow for loading Pizza ontology
- Enables use of real-world ontologies
- **Key Concepts:** OWL integration, external resources
- **Learning Time:** 10 minutes
- **Note:** Requires downloading OWL files

#### 09_configuration_and_performance.py
**Purpose:** Performance tuning and configuration
- Different blocking strategies (ANCESTOR, COMPLEX_CORE)
- Timeout configuration
- Precomputation benefits
- **Key Concepts:** Configuration, performance optimization
- **Learning Time:** 15 minutes

#### 10_complete_example_semantic_web.py
**Purpose:** Real-world scientific publication ontology
- Authors, publications, conferences
- Complex relationships and hierarchies
- Practical semantic web modeling
- **Key Concepts:** Real-world ontology design, semantic web
- **Learning Time:** 20 minutes

### Advanced Track (11-14, 17)

#### 11_real_world_ecommerce.py
**Purpose:** E-commerce product ontology
- Realistic product category hierarchies (40+ products)
- Business logic applications (recommendations, taxation)
- Performance benchmarking
- **Key Concepts:** Real-world ontology, business logic
- **Learning Time:** 20 minutes
- **Difficulty:** Advanced

#### 12_integration_patterns.py
**Purpose:** Integration into larger applications
- 5 design patterns:
  1. Singleton reasoner management
  2. Query result caching with statistics
  3. Batch query processing
  4. Error handling wrapper
  5. Context manager for resource cleanup
- Thread safety, performance optimization
- **Key Concepts:** Design patterns, integration, caching
- **Learning Time:** 25 minutes
- **Difficulty:** Advanced

#### 13_testing_and_validation.py
**Purpose:** Ontology testing and QA
- Unit test framework for ontologies
- Regression testing for ontology changes
- Ontology profiling and metrics
- **Key Concepts:** Testing, validation, quality assurance
- **Learning Time:** 25 minutes
- **Difficulty:** Advanced

#### 14_inverse_roles.py
**Purpose:** Bidirectional relationships
- Inverse roles (hasChild ↔ hasParent)
- Automatic inference of inverse relationships
- Family/organizational relationships
- **Key Concepts:** Inverse roles, bidirectional relationships
- **Learning Time:** 15 minutes
- **Difficulty:** Intermediate-Advanced

#### 17_contradictions_and_clashes.py
**Purpose:** Detecting and handling inconsistencies
- Identify unsatisfiable concepts
- Detect contradictory axioms
- Debug consistency issues
- **Key Concepts:** Inconsistency detection, clash detection
- **Learning Time:** 20 minutes
- **Difficulty:** Advanced

### Advanced+ Track (15-16, 18-20)

#### 15_multiple_inheritance.py
**Purpose:** Complex hierarchies with multiple parents
- Multiple inheritance (diamond problem)
- Path-based subsumption
- Common ancestor detection
- Automatic inference through inheritance paths
- **Key Concepts:** Multiple inheritance, transitive closure, diamond hierarchies
- **Learning Time:** 20 minutes
- **Difficulty:** Advanced

#### 16_query_patterns.py
**Purpose:** Practical query patterns for real applications
- Hierarchical instance retrieval
- Type-based filtering
- Role relationship chaining
- Business logic patterns
- Performance optimization tips
- **Key Concepts:** Query design, filtering, aggregation, statistics
- **Learning Time:** 25 minutes
- **Difficulty:** Advanced

#### 18_nominal_classes.py
**Purpose:** Enumerated classes and fixed value sets
- Defining classes as unions of individuals (OneOf)
- Exhaustiveness constraints
- Configuration enumerations
- Practical use cases (status codes, colors, days)
- **Key Concepts:** Nominals, enumeration, fixed sets, classification
- **Learning Time:** 20 minutes
- **Difficulty:** Intermediate-Advanced

#### 19_performance_analysis.py
**Purpose:** Performance benchmarking and optimization
- Measuring reasoning time
- Comparing blocking strategies
- Impact of ontology complexity
- Precomputation benefits
- Scalability analysis
- **Key Concepts:** Performance profiling, optimization, blocking strategies
- **Learning Time:** 25 minutes
- **Difficulty:** Advanced

#### 20_multi_domain_reasoning.py
**Purpose:** Integrating multiple domain ontologies
- Cross-domain relationships
- Linking concepts across domains
- Domain-specific hierarchies
- Integration patterns
- Real-world medical example
- **Key Concepts:** Ontology composition, domain integration, cross-domain inference
- **Learning Time:** 25 minutes
- **Difficulty:** Advanced

## Feature Matrix: Which Examples Cover What?

| Feature | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 |
|---------|----|----|----|----|----|----|----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| **Basic Ontology** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Subsumption** | ✓ | ✓ | ✓ |   | ✓ |   | ✓ | ✓ | ✓ | ✓ | ✓ |   | ✓ |   | ✓ | ✓ |   |   |   |   |
| **Object Properties** |   |   | ✓ | ✓ |   |   | ✓ |   | ✓ | ✓ | ✓ |   | ✓ | ✓ |   | ✓ |   |   |   | ✓ |
| **Existential Restrictions** |   |   | ✓ | ✓ |   |   | ✓ |   | ✓ | ✓ | ✓ |   |   |   |   |   |   |   |   |   |
| **Cardinality** |   |   |   |   | ✓ |   |   |   |   | ✓ | ✓ |   |   |   |   |   |   |   |   |   |
| **Disjointness** |   |   |   |   |   | ✓ |   |   |   |   |   |   |   |   |   |   | ✓ |   |   |   |
| **Instance ABox** |   |   | ✓ | ✓ | ✓ | ✓ | ✓ |   | ✓ | ✓ | ✓ |   | ✓ | ✓ |   | ✓ |   | ✓ |   | ✓ |
| **Type Checking** |   |   | ✓ | ✓ |   |   | ✓ |   | ✓ | ✓ | ✓ |   | ✓ | ✓ | ✓ | ✓ |   | ✓ |   | ✓ |
| **Role Relationships** |   |   | ✓ | ✓ |   |   | ✓ |   | ✓ | ✓ | ✓ |   | ✓ | ✓ |   | ✓ |   |   |   | ✓ |
| **Consistency Checking** | ✓ |   |   | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Class Hierarchy** |   | ✓ |   | ✓ |   |   | ✓ | ✓ | ✓ | ✓ | ✓ |   | ✓ |   | ✓ | ✓ |   |   |   |   |
| **File Loading** |   |   |   |   |   |   |   | ✓ |   |   |   |   |   |   |   |   |   |   |   |   |
| **Inverse Roles** |   |   |   |   |   |   |   |   |   |   |   |   |   | ✓ |   |   |   |   |   |   |
| **Multiple Inheritance** |   |   |   |   |   |   |   |   |   |   |   |   |   |   | ✓ |   |   |   |   |   |
| **Query Patterns** |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | ✓ |   |   |   |   |
| **Design Patterns** |   |   |   |   |   |   |   |   |   |   |   | ✓ |   |   |   |   |   |   |   |   |
| **Nominal Classes** |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | ✓ |   |   |
| **Performance Analysis** |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | ✓ |   |
| **Multi-Domain Integration** |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | ✓ |
| **Testing** |   |   |   |   |   |   |   |   |   |   |   |   | ✓ |   |   |   |   |   |   |   |
| **Inconsistency Detection** |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | ✓ |   |   |   |

## Learning Paths

### Path 1: Beginner (5-10 hours)
01 → 02 → 03 → 04 → 05 → 06
- Covers all fundamental concepts
- Hands-on with ontologies
- Understanding TBox and ABox

### Path 2: Practitioner (15-20 hours)
01 → 02 → 03 → 04 → 05 → 07 → 09 → 10 → 11
- Practical ontology design
- Real-world use cases
- Performance considerations

### Path 3: Advanced Developer (20-30 hours)
All examples in order
- Deep understanding of all features
- Integration patterns
- Testing and validation
- Advanced reasoning concepts

## Common Code Patterns

### Pattern 1: Check Consistency
```python
reasoner = Reasoner(ontology)
is_consistent = reasoner.is_consistent()
reasoner.dispose()
```

### Pattern 2: Query the Class Hierarchy
```python
reasoner = Reasoner(ontology)
reasoner.precompute_inferences(class_hierarchy=True)
subclasses = reasoner.get_sub_classes(my_class)
for sub in subclasses:
    print(sub.iri)
reasoner.dispose()
```

### Pattern 3: Check Subsumption
```python
reasoner = Reasoner(ontology)
is_subclass = reasoner.is_sub_class_of(dog, animal)
reasoner.dispose()
```

### Pattern 4: Instance Retrieval
```python
reasoner = Reasoner(ontology)
reasoner.precompute_inferences()
instances = reasoner.get_instances(my_class)
for instance in instances:
    print(instance.iri)
reasoner.dispose()
```

### Pattern 5: Type Checking
```python
reasoner = Reasoner(ontology)
reasoner.precompute_inferences()
types = reasoner.get_types(individual)
for t in types:
    print(t.iri)
reasoner.dispose()
```

## Debugging Tips

### Ontology is Inconsistent — What went wrong?

When `is_consistent()` returns `False`, it means your ontology has contradictory axioms. Common causes:

1. **Violated disjointness:**
   ```
   Disjoint(Male, Female)
   // But then: Bob is Male and Bob is Female
   → INCONSISTENT
   ```

2. **Violated cardinality:**
   ```
   Person ⊓ ≤2 hasParent
   // But then: Alice has 3 parents
   → INCONSISTENT
   ```

3. **Circular restrictions:**
   ```
   A ⊑ ∃R.B
   B ⊑ ∃R.A
   // Both true for the same instance
   → May be INCONSISTENT (depends on blocking strategy)
   ```

### Performance is Slow

1. **Precompute inferences:** For repeated queries on the same ontology, call `precompute_inferences()` once
2. **Use appropriate blocking:** See Configuration for blocking strategy options
3. **Avoid large cardinalities:** Very high cardinality constraints (≥100) can slow reasoning

### Getting Empty Results

1. **Did you call `precompute_inferences()`?** Some queries require the class hierarchy
2. **Check the IRI format:** Ensure your class IRIs match what's in the ontology
3. **Verify the ontology loaded:** Check `ontology.all_classes`, `ontology.all_individuals`

## Frequently Asked Questions

### Q: Can I load ontologies from files?
**A:** Yes! Example 8 shows this. You need `owlready2` installed:
```bash
pip install owlready2
```

### Q: What's the difference between TBox and ABox?
**A:**
- **TBox** (Terminological Box): Class definitions and rules
- **ABox** (Assertion Box): Facts about individuals

### Q: Can I update the ontology after creating a reasoner?
**A:** No. Create a new reasoner with the updated ontology. PyHermit optimizes for static ontologies.

### Q: How do I handle large ontologies?
**A:** Use `Configuration` to adjust blocking strategies and timeouts. See the main documentation.

### Q: What OWL features are supported?
**A:** Full OWL 2 DL — see `../FEATURE_PARITY.md` for details.

### Q: Which example should I start with?
**A:** Start with `01_hello_world.py`, then `02_class_hierarchy.py`. They build naturally.

## Key Fixes in This Version

### ✓ Fixed: Role Relationship Queries (Examples 03, 04)
**Issue:** `has_role_relationship()` was always returning False for directly asserted roles

**Root Cause:** Role assertions are consumed by the tableau during reasoning and not persistently stored in the extension table. The instance manager's retrieval system couldn't find them later.

**Solution:** Modified `reasoner.has_role_relationship()` in `src/hermit/reasoner.py` to:
1. **First check** the original ontology's positive facts directly
2. **Then fall back** to the instance manager for inferred relationships

**Result:** Role relationship queries now work correctly ✓

Example output:
```
Role Relationships:
----------------------------------------
Fido hasOwner Alice: True
```

## Testing

All 20 examples pass successfully:
```
✓ Example 01 - hello_world
✓ Example 02 - class_hierarchy  
✓ Example 03 - object_properties
✓ Example 04 - instance_retrieval
✓ Example 05 - cardinality_restrictions
✓ Example 06 - disjointness_and_negation
✓ Example 07 - advanced_reasoning
✓ Example 08 - loading_owl_files
✓ Example 09 - configuration_and_performance
✓ Example 10 - complete_example_semantic_web
✓ Example 11 - real_world_ecommerce
✓ Example 12 - integration_patterns
✓ Example 13 - testing_and_validation
✓ Example 14 - inverse_roles
✓ Example 15 - multiple_inheritance
✓ Example 16 - query_patterns
✓ Example 17 - contradictions_and_clashes
✓ Example 18 - nominal_classes
✓ Example 19 - performance_analysis
✓ Example 20 - multi_domain_reasoning
```

## Performance Notes

- Examples 01-07: < 100ms each
- Examples 08-10: < 500ms each (more complex ontologies)
- Examples 11-14, 17: < 1s each (real-world complexity)
- Examples 15-16, 18-20: < 2s each (advanced reasoning patterns, benchmarking)

**Total runtime for all 20 examples: < 30 seconds**

## Documentation Files

- **README.md** — This file (comprehensive overview)
- **LEARNING_GUIDE.md** — Structured learning paths for different audiences
- **QUICK_REFERENCE.md** — Copy-paste code patterns and snippets
- **TROUBLESHOOTING.md** — Solutions to 20+ common problems

## Next Steps

After working through these examples:

1. **Read the main documentation:** See `../README.md` and `../ARCHITECTURE.md`
2. **Explore the API:** Check `src/hermit/reasoner.py` for the full Reasoner API
3. **Build your own ontology:** Create an ontology for your domain
4. **Handle errors:** Add try/except blocks and logging to production code
5. **Optimize:** Use `Configuration` to tune the reasoner for your needs

## Additional Resources

### In This Repository
- `../README.md` — Main project overview
- `../ARCHITECTURE.md` — How the reasoner works
- `../FEATURE_PARITY.md` — What OWL features are supported
- `../src/hermit/reasoner.py` — Full Reasoner API
- `../tests/` — Additional usage patterns

### External Resources
- **OWL 2 Specification:** https://www.w3.org/TR/owl2-overview/
- **Description Logic Handbook:** https://www.semantic-web-book.org/
- **Protégé Ontology Editor:** https://protege.stanford.edu/
- **HermiT Original:** http://hermit-reasoner.com/

## Contributing Examples

Have a great example or tutorial? Contributions are welcome! Please:
1. Create numbered file: `XX_topic_name.py`
2. Include docstring with purpose and concepts
3. Add helpful comments throughout
4. End with explanation section
5. Test with `python examples/XX_*.py`
6. Update this README

---

**Happy reasoning! 🧠**
