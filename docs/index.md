# PyHermit Documentation

Welcome to PyHermit — a Python implementation of the HermiT OWL 2 DL reasoner. This guide takes you from complete beginner to advanced user.

## Getting Started

- **[Installation](./installation.md)** — Get PyHermit working on your machine (5 min)
- **[Concepts](./concepts.md)** — Learn what OWL, DL, and reasoning mean (10 min)
- **[Your First Program](./first-program.md)** — Run your first reasoner example (10 min)

## Tutorials by Level

### Beginner (No Prior Knowledge)

These assume you've never worked with ontologies or semantic web before.

1. **[Understanding Ontologies](./tutorials/01-ontologies.md)**
   - What is an ontology?
   - Why use semantic web technologies?
   - Real-world examples

2. **[Building Your First Ontology](./tutorials/02-build-ontology.md)**
   - Creating classes and properties
   - Defining relationships
   - Adding constraints

3. **[Using PyHermit to Reason](./tutorials/03-basic-reasoning.md)**
   - Loading ontologies
   - Consistency checking
   - Finding class hierarchies

### Intermediate

For users comfortable with the basics who want to solve real problems.

4. **[Working with Instances](./tutorials/04-instances.md)**
   - Adding individuals (data)
   - Type checking
   - Retrieving instances

5. **[Advanced Class Restrictions](./tutorials/05-restrictions.md)**
   - Cardinality constraints
   - Existential and universal restrictions
   - Property chains

6. **[SWRL Rules & Queries](./tutorials/06-rules.md)**
   - Adding DL-safe SWRL rules
   - Evaluating Datalog queries
   - Practical rule examples

### Advanced

For developers building production systems.

7. **[Performance & Optimization](./tutorials/07-performance.md)**
   - Blocking strategies
   - Configuration tuning
   - Profiling your ontologies

8. **[Custom Reasoner Integration](./tutorials/08-integration.md)**
   - Embedding PyHermit in applications
   - Extending the reasoner
   - Building on top of PyHermit

## How PyHermit Works

### The Algorithm

- **[Tableau Algorithm Explained](./algorithm/tableau.md)** — The core reasoning mechanism
- **[Normalization & Clausification](./algorithm/normalization.md)** — How formulas are transformed
- **[Blocking Strategies](./algorithm/blocking.md)** — How termination is ensured
- **[Class Hierarchy Computation](./algorithm/classification.md)** — Building subsumption relations

### Architecture

- **[System Architecture](./architecture/overview.md)** — High-level system design
- **[Module Structure](./architecture/modules.md)** — Key components and their roles
- **[Data Flow](./architecture/dataflow.md)** — How data moves through the system

## API Reference

- **[Core API](./api/core.md)** — Reasoner, Ontology, and basic types
- **[OWL Model](./api/owl-model.md)** — Classes, properties, and axioms
- **[Query API](./api/queries.md)** — Datalog and conjunctive queries
- **[Configuration](./api/configuration.md)** — Reasoner configuration options

## Recipes & Examples

- **[Common Patterns](./recipes/patterns.md)** — Standard usage patterns
- **[Ontology Debugging](./recipes/debugging.md)** — Finding and fixing issues
- **[Integration Examples](./recipes/integration.md)** — Real-world use cases
- **[Performance Tips](./recipes/performance.md)** — Optimization strategies

## FAQ

- **[Frequently Asked Questions](./faq.md)** — Quick answers to common questions

## External Resources

- **[HermiT Official](http://hermit-reasoner.com)** — Original Java reasoner
- **[OWL 2 Specification](https://www.w3.org/OWL/)** — W3C OWL 2 standard
- **[Semantic Web Primer](https://www.w3.org/TR/rdf-primer/)** — RDF and semantic web basics

---

**Start with [Installation](./installation.md) or [Concepts](./concepts.md) depending on your background.**

Questions? Check the [FAQ](./faq.md) or open an issue on GitHub.
