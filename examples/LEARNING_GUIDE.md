# PyHermit Learning Guide — Complete Curriculum

This guide provides a structured learning path through the PyHermit examples, from complete beginner to advanced practitioner.

## How to Use This Guide

1. **Start at your level** — Choose the path that matches your background
2. **Work through sequentially** — Each example builds on prior concepts
3. **Modify and experiment** — Edit the code and see what happens
4. **Read the docstrings** — Each example has extensive comments explaining the concepts
5. **Refer back** — When you forget something, examples are a quick reference

---

## Learning Paths

### Path A: Complete Beginner (0-2 hours)

You're new to OWL, Description Logic, or semantic reasoning.

**Week 1: Foundations**
1. Read: `README.md` introduction
2. Run: `01_hello_world.py` — Understand the basic workflow
3. Run: `02_class_hierarchy.py` — Learn about class relationships
4. Read: Sections in `README.md` on TBox vs ABox

**Week 2: Instances and Properties**
1. Run: `03_object_properties.py` — Understand properties
2. Run: `04_instance_retrieval.py` — Work with individual data
3. Modify: Change the ontology in example 4, see what happens
4. Read: Comments on "some-values-from" and "all-values-from"

**Week 3: Constraints**
1. Run: `05_cardinality_restrictions.py` — Learn about limits
2. Run: `06_disjointness_and_negation.py` — Understand contradictions
3. Read: The "Why it matters" sections

**Week 4: Integration**
1. Run: `10_complete_example_semantic_web.py` — See it all together
2. Modify: Add your own domain (e.g., a library catalog)
3. Read: The analysis section at the end

**Your First Project:**
- Model your own small domain (e.g., family relationships, team structure)
- Create classes, properties, and facts
- Use the reasoner to answer queries
- Compare with manual reasoning

---

### Path B: Web Developer / Programmer (1-3 hours)

You know Python and web APIs, new to semantic reasoning.

**Session 1: Basics (30 mins)**
1. Read: "Quick Start" in `README.md`
2. Skim: `01_hello_world.py` — Focus on the API structure
3. Note: How DLOntology, Reasoner, and queries work

**Session 2: Practical Reasoning (45 mins)**
1. Read: `03_object_properties.py` fully
2. Read: `04_instance_retrieval.py` — Key for building services
3. Run: Both examples
4. Think: "How would I use this in a REST API?"

**Session 3: Real-World Scenarios (60 mins)**
1. Run: `10_complete_example_semantic_web.py`
2. Modify: Add your own individuals and facts
3. Build: A simple query handler function
4. Read: Configuration and performance considerations in example 9

**Session 4: Integration**
1. Design: An ontology for your domain
2. Load: Use `load_ontology()` for external OWL files (example 8)
3. Query: Build a query function that uses the reasoner
4. Cache: Consider precomputation strategies

**Your First Service:**
- Build a REST endpoint that answers semantic queries
- Use PyHermit to reason over domain data
- Handle multiple concurrent requests carefully (create/dispose reasoners)

---

### Path C: Data Scientist / Knowledge Engineer (2-4 hours)

You're familiar with ontologies, databases, or knowledge graphs.

**Session 1: Core Concepts Review (30 mins)**
1. Run: Examples 1-4 to validate concepts
2. Read: `ARCHITECTURE.md` for the reasoning algorithm
3. Compare: "How is this different from my current tools?"

**Session 2: Advanced Reasoning (60 mins)**
1. Read: Example 5 (cardinality) — Crucial for data validation
2. Read: Example 6 (disjointness) — Constraint modeling
3. Read: Example 7 (advanced) — Multi-level reasoning
4. Think: "What constraints exist in my data?"

**Session 3: Modeling Patterns (60 mins)**
1. Read: `FEATURE_PARITY.md` for what's supported
2. Study: Which OWL features apply to your domain
3. Design: Ontology for your knowledge graph
4. Test: Is it consistent? Are inferences correct?

**Session 4: Performance & Scale (30 mins)**
1. Read: Example 9 — Performance tuning
2. Benchmark: Your ontology with different strategies
3. Optimize: Balance correctness vs speed
4. Plan: Deployment considerations

**Session 5: Integration (30 mins)**
1. Load: Real ontologies (example 8)
2. Reason: Over existing knowledge graphs
3. Validate: Results against expected inferences
4. Document: Ontology design decisions

**Your First Knowledge System:**
- Take an existing knowledge graph or database
- Model it as an OWL ontology
- Use PyHermit to infer implicit relationships
- Validate data quality via consistency checks
- Build decision-making logic on top of inference results

---

### Path D: Research/Academic Use (4-6 hours)

You're studying description logic, ontology engineering, or formal reasoning.

**Session 1: Algorithm Deep Dive (90 mins)**
1. Read: `ARCHITECTURE.md` completely
2. Read: Example 7 — Understand the rule system
3. Study: Source code in `src/hermit/tableau/`
4. Note: How blocking strategies work

**Session 2: Expressivity & Decidability (60 mins)**
1. Read: `FEATURE_PARITY.md` — What's supported
2. Study: OWL 2 DL specification excerpts
3. Experiment: Test the boundaries of expressivity
4. Document: What works, what doesn't

**Session 3: Reasoning Strategies (90 mins)**
1. Run: Example 9 with different configurations
2. Benchmark: Impact of different strategies
3. Analyze: Trade-offs in completeness vs complexity
4. Compare: With other reasoners (Hermit Java, Pellet, etc.)

**Session 4: Testing & Validation (60 mins)**
1. Read: Tests in `../tests/` directory
2. Build: Test cases for your domain
3. Verify: Correctness of inferences
4. Document: Edge cases and limitations

**Session 5: Extensions & Integration (60 mins)**
1. Study: How to add custom rules
2. Build: Domain-specific extensions
3. Integrate: With external systems
4. Publish: Your findings

**Your Research Project:**
- Choose a research question about semantic reasoning
- Build test cases using PyHermit
- Measure performance and correctness
- Compare with other approaches
- Document and publish results

---

## Progression Checklist

As you progress, check off these milestones:

### Level 1: Fundamentals
- [ ] Understand OWL classes and subsumption
- [ ] Can create simple ontologies programmatically
- [ ] Know how to check consistency
- [ ] Can query class hierarchies

### Level 2: Instances & Properties
- [ ] Understand ABox and TBox
- [ ] Can assert facts about individuals
- [ ] Can retrieve instances of classes
- [ ] Understand object properties and their directions

### Level 3: Constraints
- [ ] Know cardinality constraints
- [ ] Understand disjointness
- [ ] Can detect contradictions
- [ ] Can model real-world constraints

### Level 4: Integration
- [ ] Can load external OWL files
- [ ] Can build domain ontologies
- [ ] Understand performance/correctness trade-offs
- [ ] Can integrate with applications

### Level 5: Advanced
- [ ] Deep understanding of blocking strategies
- [ ] Can optimize reasoning for specific domains
- [ ] Understand tableau algorithm details
- [ ] Can extend and customize the reasoner

---

## Common Pitfalls & Solutions

### Pitfall 1: "My ontology says X, but the reasoner says Y"

**Cause:** You're not considering logical inference. OWL is not about what you explicitly write, but what logically follows.

**Solution:** Draw the inference chain. If the reasoner says X and you disagree, either:
- [ ] The ontology is wrong (fix it)
- [ ] Your understanding is wrong (read more about DL)
- [ ] The reasoner has a bug (file an issue)

### Pitfall 2: "The consistency check is taking forever"

**Cause:** Your ontology or rules are too complex.

**Solutions:**
- [ ] Set a timeout via Configuration
- [ ] Try a simpler blocking strategy
- [ ] Break your ontology into modules
- [ ] Reduce cardinality constraints
- [ ] Check for infinite loops in rules

### Pitfall 3: "I'm getting empty results from queries"

**Causes:**
- [ ] Forgot to call `precompute_inferences()`
- [ ] Wrong class IRI format
- [ ] Class not actually in ontology
- [ ] Class has no instances

**Solutions:**
- [ ] Always precompute before instance queries
- [ ] Double-check IRI strings (use print statements)
- [ ] List all classes: `ontology.all_classes`
- [ ] Verify facts were added to ABox

### Pitfall 4: "I changed the ontology but reasoner still gives old results"

**Cause:** Reasoner caches inferences. You need a new reasoner instance for a modified ontology.

**Solution:** Always create a new Reasoner for a new/modified ontology. Don't reuse reasoners.

### Pitfall 5: "Different runs give different results"

**Cause:** You're reusing a disposed reasoner or mixing reasoner instances.

**Solution:**
- [ ] Only use a reasoner until you call dispose()
- [ ] Create one new reasoner per ontology
- [ ] Don't share reasoners across threads

---

## Reference: Which Example for Which Task?

| Task | Example |
|------|---------|
| Learn the basics | 01 |
| Explore class hierarchies | 02 |
| Work with properties | 03 |
| Query individuals | 04 |
| Model constraints (cardinality) | 05 |
| Detect contradictions | 06 |
| Complex reasoning | 07 |
| Load OWL files | 08 |
| Tune performance | 09 |
| See it all together | 10 |

---

## Recommended Study Time

- **Complete Beginner:** 8-12 hours (1-2 weeks at 1-2 hours/day)
- **Programmer New to Semantic Web:** 4-6 hours (2-3 sessions)
- **Data Scientist with DL Background:** 2-4 hours (1-2 sessions)
- **Researcher/Academic:** 6-10 hours (deep study over 2-3 weeks)

---

## Learning Resources

### Within This Repository
- `README.md` — Overview and features
- `ARCHITECTURE.md` — Algorithm explanation
- `FEATURE_PARITY.md` — What's implemented
- `src/hermit/reasoner.py` — API documentation
- `tests/` — Additional usage examples

### External Resources
- [OWL 2 Primer](https://www.w3.org/TR/owl2-primer/) — Learn OWL
- [Description Logic Handbook](https://www.semantic-web-book.org/) — Theory
- [Protégé Tutorial](https://protege.stanford.edu/products.html) — Visual ontology editor
- [HermiT Original Paper](http://hermit-reasoner.com) — Original research

### Practice Ontologies
- [Pizza Ontology](http://protege.stanford.edu/ontologies/pizza/pizza.owl) — Learning ontology
- [Koala Ontology](http://protege.stanford.edu/ontologies/koala.owl) — Small example
- [YAGO](https://www.mpi-inf.mpg.de/departments/databases-and-information-systems/research/yago-naga/yago) — Large knowledge base
- [BioTopLite](http://purl.obolibrary.org/obo/biotoplite.owl) — Biology ontology

---

## Next Steps After Learning

Once you've worked through the examples:

1. **Build something real** — Model your own domain
2. **Contribute** — Add more examples or improvements
3. **Deploy** — Integrate into your application
4. **Optimize** — Profile and tune for production
5. **Extend** — Consider custom reasoning rules
6. **Share** — Publish your ontology and learnings

---

## Feedback & Questions

- **Stuck on an example?** Check the docstrings and comments
- **Want to see a different scenario?** Request or contribute an example
- **Found a bug?** File an issue on GitHub
- **Have suggestions?** Contributions welcome!

---

**Happy learning! The semantic web awaits. 🌐**
