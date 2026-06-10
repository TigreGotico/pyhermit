# PyHermit Documentation

Welcome to PyHermit — a Python port of the HermiT OWL 2 DL reasoner.

## Getting Started

1. **[Installation](./installation.md)** — Set up PyHermit
2. **[Concepts](./concepts.md)** — What are ontologies and reasoning?
3. **[First Program](./first-program.md)** — Your first reasoner code

## Tutorials

### Level 0: Foundations
- **[What is an Ontology?](./tutorials/00-ontologies.md)**

### Level 1: Beginner
- **[Building Your First Ontology](./tutorials/01-build-ontology.md)**

### Level 2: Intermediate
- **[Restrictions & Cardinality](./tutorials/02-restrictions.md)**
- **[Working with Instances](./tutorials/03-instances.md)**

### Level 3: Advanced
- **[Rules & Complex Queries](./tutorials/03-rules-and-queries.md)**
- **[Advanced Reasoning Strategies](./tutorials/04-advanced-reasoning.md)**

## Architecture

PyHermit processes OWL ontologies through a fixed pipeline:

```
OWL Axioms
    |
    v
OWLNormalization          src/hermit/structural/owl_normalization.py
    |  - Converts to Negation Normal Form
    |  - Populates simple_object_property_inclusions
    |    (from SubObjectPropertyOf, InverseObjectProperties)
    |  - Populates complex_object_property_inclusions
    |    (from TransitiveObjectProperty, SubPropertyChainOf)
    v
OWLClausification         src/hermit/structural/owl_clausification.py
    |  - Calls ObjectPropertyInclusionManager.rewrite_axioms()
    |  - Raises ValueError for OWL 2 non-simplicity violations
    |  - Produces DLClauses and fact sets
    v
Tableau Expansion         src/hermit/tableau/
    |  - Hyperresolution with configurable blocking
    v
DLOntology / Reasoner     src/hermit/reasoner.py
```

### Key Classes

| Class | Purpose | Source |
|---|---|---|
| `OWLNormalization` | Transforms OWL axioms to NNF; classifies simple/complex properties | `src/hermit/structural/owl_normalization.py:111` |
| `OWLClausification` | Converts normalized axioms to DL clauses; enforces non-simplicity | `src/hermit/structural/owl_clausification.py:89` |
| `ObjectPropertyInclusionManager` | Detects non-simple properties; validates OWL 2 constraints | `src/hermit/structural/object_property_inclusion_manager.py:35` |
| `NormalizedAxioms` | Dataclass holding all normalized axiom collections | `src/hermit/structural/normalized_axioms.py` |
| `load_ontology` | Loads OWL files (RDF/XML, OWL/XML, FSS) via the stdlib readers into `OWLAxiom` objects | `src/hermit/parser.py:24` |
| `Reasoner` | Main entry point for queries: consistency, classification, retrieval | `src/hermit/reasoner.py` |

### Non-Simple Property Validation

`ObjectPropertyInclusionManager.rewrite_axioms()` is called inside `OWLClausification.clausify()` at `src/hermit/structural/owl_clausification.py:139`. It raises `ValueError` if a non-simple property (transitive, in a role chain, or a superrole thereof) appears in:

- `AsymmetricObjectProperty`
- `IrreflexiveObjectProperty`
- `DisjointObjectProperties`
- `ObjectMinCardinality`, `ObjectMaxCardinality`, `ObjectExactCardinality`
- `ObjectHasSelf`

Detection uses a fixpoint propagation through `simple_object_property_inclusions` and always marks inverses of complex properties as complex. Source: `ObjectPropertyInclusionManager._detect_complex_properties` — `src/hermit/structural/object_property_inclusion_manager.py:311`.

## API Reference

- **[Core API](./api/core.md)** — Reasoner, classes, properties, axioms

## Recipes & Patterns

- **[Common Design Patterns](./recipes/patterns.md)**
- **[Debugging Guide](./recipes/debugging.md)**

## FAQ

- **[Frequently Asked Questions](./faq.md)**

## External Resources

- **[HermiT Official](http://hermit-reasoner.com)** — Original Java reasoner
- **[OWL 2 Specification](https://www.w3.org/OWL/)** — W3C standard
