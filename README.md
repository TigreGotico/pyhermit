# PyHermit — Python OWL 2 DL Reasoner

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A faithful Python port of [HermiT](http://hermit-reasoner.com), a conformant OWL 2 DL reasoner developed at the University of Oxford. Reasons about OWL ontologies using tableau-based decision procedures — no JVM required.

## Key Features

- **OWL 2 DL reasoning** — Full support for all Direct Semantics constructs
- **Tableau algorithm** — Hyperresolution with configurable blocking strategies
- **Non-simple property validation** — Enforces OWL 2 spec: transitive, role-chain, and inherited-superrole properties are rejected at clausification time if used in cardinality restrictions, hasSelf, asymmetric, irreflexive, or disjoint axioms (`ValueError`)
- **All OWL 2 datatypes** — xsd:string, decimal, integer, float, double, dateTime, boolean, anyURI, etc.
- **SWRL rules & Datalog queries** — DL-safe rule support with query evaluation
- **OWL file parsing** — Load OWL/RDF files via owlready2 (`hermit.parser.load_ontology`)
- **Pure Python** — No JVM, no external binaries, single `pip install`
- **Type-safe** — Complete type hints, passes `mypy --strict`

## Install

```bash
pip install hermit-reasoner
```

## Basic Usage

```python
from hermit import Reasoner
from hermit.model import (
    DLOntology, OWLClass, OWLNamedIndividual, OWLObjectProperty,
    SubClassOf, ClassAssertion, ObjectPropertyAssertion,
)

Animal = OWLClass("http://example.org/Animal")
Dog = OWLClass("http://example.org/Dog")
hasOwner = OWLObjectProperty("http://example.org/hasOwner")
fido = OWLNamedIndividual("http://example.org/fido")
john = OWLNamedIndividual("http://example.org/john")

ontology = DLOntology()
ontology.add_axiom(SubClassOf(Dog, Animal))
ontology.add_axiom(ClassAssertion(Dog, fido))
ontology.add_axiom(ObjectPropertyAssertion(hasOwner, fido, john))

reasoner = Reasoner(ontology)
reasoner.precompute_inferences()

assert reasoner.is_consistent()
assert reasoner.has_type(fido, Animal)   # inferred
hierarchy = reasoner.get_class_hierarchy()
instances = reasoner.get_instances(Animal)
reasoner.dispose()
```

## Load from OWL Files

```python
from hermit.parser import load_ontology
from hermit.structural.owl_normalization import OWLNormalization
from hermit.structural.owl_clausification import OWLClausification
from hermit import Reasoner

axioms = load_ontology("path/to/ontology.owl")  # requires owlready2

normalization = OWLNormalization()
normalized = normalization.normalize(axioms)

clausification = OWLClausification()
dl_ontology = clausification.clausify(normalized)  # raises ValueError on OWL 2 violations

reasoner = Reasoner(dl_ontology)
reasoner.precompute_inferences()
```

## Architecture

```
OWL Ontology
    |
    v
OWLNormalization  (NNF, fresh-concept introduction, simple/complex property classification)
    |
    v
OWLClausification (DL clauses; non-simple property validation via ObjectPropertyInclusionManager)
    |
    v
Tableau Expansion (hyperresolution with blocking)
    |
    v
Classification & Instance Retrieval
```

See [docs/](docs/) for architecture detail and API reference.

## Non-Simple Property Enforcement

OWL 2 forbids non-simple properties (transitive, or appearing as superroles of a role chain) in certain axiom positions. PyHermit enforces this at clausification time:

```python
from hermit.structural.owl_clausification import OWLClausification

clausification = OWLClausification()
try:
    dl_ontology = clausification.clausify(normalized_axioms)
except ValueError as e:
    # e.g. "Non-simple property '...' cannot be asymmetric (OWL 2 violation)"
    print(e)
```

Constraints checked (per OWL 2 spec Section 11.2):
- `AsymmetricObjectProperty`
- `IrreflexiveObjectProperty`
- `DisjointObjectProperties`
- Cardinality restrictions (`ObjectMinCardinality`, `ObjectMaxCardinality`, `ObjectExactCardinality`)
- `ObjectHasSelf`

Source: `ObjectPropertyInclusionManager._validate_complex_property_constraints` — `src/hermit/structural/object_property_inclusion_manager.py:216`

## Project Status

**Feature-complete port of Java HermiT 1.3.8**

- TBox reasoning (classification, subsumption) — Production Ready
- ABox instance retrieval — Production Ready
- Datatype reasoning — Production Ready
- SWRL rules & Datalog — Production Ready
- Non-simple property validation — Production Ready
- OWL file parsing (owlready2) — Production Ready

**Test Results:** 2244 tests, all passing (0 skips, 0 xfails)

## AI Transparency

This port was developed with [Claude](https://claude.ai) (Anthropic) as the primary developer.
All source code was written by Claude. See git history for development record.

## Documentation

- **[docs/](docs/)** — Architecture, API reference, tutorials, recipes
- **[examples/](examples/)** — Working examples from basic to advanced
- **[Original Source](https://github.com/sesuncedu/hermit-reasoner)** — Java HermiT

## License

Apache 2.0 or later. See [LICENSE](LICENSE).

Based on HermiT, copyright Oxford University Computing Laboratory 2008–2014.
