# HermiT — Python OWL 2 DL Reasoner

[![License: LGPL-3.0](https://img.shields.io/badge/License-LGPL--3.0-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A conformant OWL 2 DL tableau reasoner — a faithful Python port of the [HermiT reasoner](http://hermit-reasoner.com), originally developed at the University of Oxford.

## Features

- **Full OWL 2 DL support** — All constructs from the OWL 2 Direct Semantics specification
- **Tableau-based reasoning** — Hyperresolution calculus with description graphs
- **Multiple blocking strategies** — Ancestor blocking, pairwise direct blocking, anywhere blocking
- **Datatype reasoning** — Full support for all OWL 2 required datatypes (xsd:string, decimal, integer, float, double, dateTime, boolean, anyURI, xml:literal, rdf:PlainLiteral, binary)
- **SWRL rules** — DL-safe SWRL rule support
- **Datalog queries** — Conjunctive query evaluation
- **Incremental ABox** — Add/remove individuals without full re-classification
- **Zero JVM dependency** — Pure Python, no Java required
- **Type hints** — Complete type annotations throughout

## Installation

```bash
pip install hermit-reasoner
```

## Quick Start

```python
from hermit import Reasoner
from hermit.model import OWLOntology

# Load an ontology (RDF/XML or Functional-Style Syntax)
ontology = OWLOntology.load("pizza.owl")

# Create reasoner and classify
reasoner = Reasoner(ontology)
reasoner.precompute_inferences()

# Check consistency
print(f"Consistent: {reasoner.is_consistent()}")

# Get class hierarchy
hierarchy = reasoner.get_class_hierarchy()
for node in hierarchy:
    print(f"  {node}")

# Find instances of a class
instances = reasoner.get_instances("Pizza")
print(f"Pizza instances: {instances}")

# Clean up
reasoner.dispose()
```

## CLI Usage

```bash
# Classify an ontology
hermit classify my_ontology.owl

# Check consistency
hermit consistent my_ontology.owl

# Realize individuals
hermit realize my_ontology.owl

# Check entailment
hermit entails my_ontology.owl "MySubClass ⊑ MySuperClass"

# Run Datalog query
hermit query my_ontology.owl "Query(?x) :- Pizza(?x)"
```

## Architecture

HermiT uses a tableau-based decision procedure for OWL 2 DL:

1. **Normalization** — OWL axioms are converted to negation normal form
2. **Clausification** — Normalized axioms become DL clauses
3. **Tableau expansion** — Clauses are applied to build a model using hyperresolution
4. **Blocking** — Termination is ensured via blocking strategies
5. **Classification** — The saturated model yields subsumption hierarchies

See [ARCHITECTURE.md](ARCHITECTURE.md) for a detailed explanation.

## Project Status

This is an active port of HermiT 1.3.8. The Java original was developed by Boris Motik, Birte Glimm, Giorgos Stoilos, and Ian Horrocks at the University of Oxford.

See [brainstorm.md](brainstorm.md), [sprint.md](sprint.md), and [spec.md](spec.md) for planning documents.

## License

LGPL 3.0 or later — see [LICENSE](LICENSE) and [LICENSE.LESSER](LICENSE.LESSER).

The original HermiT source code is copyright Oxford University Computing Laboratory, 2008–2014.
