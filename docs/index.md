# PyHermit Documentation

Welcome to PyHermit — a Python implementation of the HermiT OWL 2 DL reasoner. This guide takes you from complete beginner to advanced user.

## 🚀 Getting Started (15 minutes)

1. **[Installation](./installation.md)** — Set up PyHermit
2. **[Concepts](./concepts.md)** — What are ontologies and reasoning?
3. **[First Program](./first-program.md)** — Your first reasoner code

## 📚 Tutorials (Zero to Hero)

### Level 0: Foundations
- **[What is an Ontology?](./tutorials/00-ontologies.md)** — Understanding the concepts before coding

### Level 1: Beginner (Classes & Rules)
- **[Building Your First Ontology](./tutorials/01-build-ontology.md)**
  - Creating classes and properties
  - Class hierarchies and inheritance
  - Adding constraints and rules

### Level 2: Intermediate (Instances & Queries)
- **[Restrictions & Cardinality](./tutorials/02-restrictions.md)**
  - Existential restrictions (∃)
  - Universal restrictions (∀)
  - Cardinality constraints
  
- **[Working with Instances](./tutorials/03-instances.md)**
  - Adding data and individuals
  - Type checking
  - Running queries

### Level 3: Advanced (Rules & Optimization)
- **[Rules & Complex Queries](./tutorials/03-rules-and-queries.md)**
  - SWRL-like rules
  - Complex queries
  - Reasoning chains

- **[Advanced Reasoning Strategies](./tutorials/04-advanced-reasoning.md)**
  - Performance optimization
  - Precomputation vs on-demand
  - Profiling and tuning

## 🔍 How PyHermit Works

**Coming soon:** Deep dives into the algorithms and architecture

- Tableau algorithm explanation
- Normalization and clausification
- Blocking strategies
- Class hierarchy computation

## 📖 API Reference

- **[Core API](./api/core.md)** — Reasoner, classes, properties, axioms

**Coming soon:**
- OWL model reference
- Query API
- Configuration options

## 💡 Recipes & Patterns

- **[Common Design Patterns](./recipes/patterns.md)** — 15 reusable ontology patterns
- **[Debugging Guide](./recipes/debugging.md)** — How to find and fix issues

**Coming soon:**
- Integration examples
- Performance optimization

## ❓ FAQ

- **[Frequently Asked Questions](./faq.md)** — Quick answers to 30+ common questions

## 🔗 External Resources

- **[HermiT Official](http://hermit-reasoner.com)** — Original Java reasoner
- **[OWL 2 Specification](https://www.w3.org/OWL/)** — W3C standard
- **[RDF Concepts](https://www.w3.org/TR/rdf-concepts/)** — RDF basics

## 🎯 Learning Paths

### I want to...

**...understand ontologies**
1. [What is an Ontology?](./tutorials/00-ontologies.md)
2. [Concepts](./concepts.md)
3. [First Program](./first-program.md)

**...build a simple ontology**
1. [Installation](./installation.md)
2. [Building Your First Ontology](./tutorials/01-build-ontology.md)
3. [First Program](./first-program.md) (reference)

**...add data and query it**
1. [Restrictions](./tutorials/02-restrictions.md)
2. [Instances](./tutorials/03-instances.md)
3. [Rules & Queries](./tutorials/03-rules-and-queries.md)

**...debug my ontology**
1. [Debugging Guide](./recipes/debugging.md)
2. [FAQ](./faq.md)
3. [Concepts](./concepts.md) (for deeper understanding)

**...optimize for performance**
1. [Advanced Reasoning](./tutorials/04-advanced-reasoning.md)
2. [FAQ - Performance section](./faq.md#performance--optimization)
3. [Debugging Guide](./recipes/debugging.md)

---

**Recommendation:** Start with [Concepts](./concepts.md) if you're new to ontologies, or jump to [Installation](./installation.md) if you're ready to code.

**Questions?** Check the [FAQ](./faq.md) or [Debugging Guide](./recipes/debugging.md).
