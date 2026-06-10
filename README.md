# PyHermit — Python OWL 2 DL Reasoner

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A Python port of [HermiT](http://hermit-reasoner.com), an OWL 2 DL reasoner developed at the University of Oxford. Reasons about OWL ontologies using tableau-based decision procedures — no JVM required.

## Key Features

- **OWL 2 DL reasoning** — tableau decision procedure over the OWL 2 Direct Semantics constructs
- **Tableau algorithm** — Hyperresolution with configurable blocking strategies
- **Non-simple property validation** — Enforces OWL 2 spec: transitive, role-chain, and inherited-superrole properties are rejected at clausification time if used in cardinality restrictions, hasSelf, asymmetric, irreflexive, or disjoint axioms (`ValueError`)
- **All OWL 2 datatypes** — xsd:string, decimal, integer, float, double, dateTime, boolean, anyURI, etc.
- **SWRL rules & Datalog queries** — DL-safe rule support with query evaluation
- **OWL file parsing** — Load RDF/XML, OWL/XML, and Functional-Style Syntax via a pure stdlib reader (`hermit.parser.load_ontology`)
- **Pure Python** — No JVM, no external binaries, single `pip install`
- **Type-safe** — Complete type hints, passes `mypy --strict`

## Install

```bash
pip install hermit-reasoner
```

## Basic Usage

```python
from hermit import Reasoner
from hermit.model import AtomicConcept, AtomicRole, Individual
from hermit.owl_model.class_expression import OWLClass
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_property import OWLObjectProperty
from hermit.owl_model.owl_axiom import (
    OWLClassAssertionAxiom, OWLObjectPropertyAssertionAxiom, OWLSubClassOfAxiom,
)
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization

NS = "http://example.org/"
Animal = OWLClass(NS + "Animal")
Dog = OWLClass(NS + "Dog")
hasOwner = OWLObjectProperty(NS + "hasOwner")
fido = OWLNamedIndividual(NS + "fido")
john = OWLNamedIndividual(NS + "john")

axioms = [
    OWLSubClassOfAxiom(Dog, Animal),
    OWLClassAssertionAxiom(fido, Dog),
    OWLObjectPropertyAssertionAxiom(fido, hasOwner, john),
]

normalized = OWLNormalization().process_ontology(axioms)
dl_ontology = OWLClausification().clausify(normalized, ontology_iri="urn:example:pets")

reasoner = Reasoner(dl_ontology)
reasoner.precompute_inferences()

animal = AtomicConcept.create(NS + "Animal")          # query handles
fido_h = Individual.create(NS + "fido")

assert reasoner.is_consistent()
assert reasoner.has_type(fido_h, animal)              # inferred
assert reasoner.has_role_relationship(
    fido_h, AtomicRole.create(NS + "hasOwner"), Individual.create(NS + "john")
)
instances = reasoner.get_instances(animal)            # {fido}
reasoner.dispose()
```

## Load from OWL Files

```python
from hermit.parser import load_ontology
from hermit.structural.owl_normalization import OWLNormalization
from hermit.structural.owl_clausification import OWLClausification
from hermit import Reasoner

axioms = load_ontology("path/to/ontology.owl")  # stdlib reader: RDF/XML, OWL/XML, FSS

normalized = OWLNormalization().process_ontology(axioms)
dl_ontology = OWLClausification().clausify(normalized)  # raises ValueError on OWL 2 violations

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
    dl_ontology = clausification.clausify(normalized)
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

Source: `ObjectPropertyInclusionManager._validate_complex_property_constraints` — `src/hermit/structural/object_property_inclusion_manager.py:360`

## Project Status

Structural port of Java HermiT. The reasoning core (tableau, blocking,
hyperresolution, classification, datatype reasoning, SWRL/Datalog query
answering) is implemented; ontology loading uses a pure stdlib reader
(RDF/XML, OWL/XML, Functional-Style Syntax).

- TBox reasoning (classification, subsumption)
- ABox instance retrieval
- Datatype reasoning
- SWRL rules & Datalog query answering
- Non-simple property validation
- OWL file parsing via a pure stdlib reader (RDF/XML, OWL/XML, FSS)

**Conformance:** passes 340/350 W3C OWL WG Approved-DL test cases at a 20 s
per-case budget (`pytest -m slow tests/test_wg_conformance.py`, or
`python scripts/wg_run.py approved --list-fails --timeout=20`), with zero
wrong answers, errors, or unchecked conclusions — the 10 non-passing cases
are timeouts on hard combinatorial ontologies (several pass with the 300 s
budget the Java harness uses). Intentional divergences from the Java original
are documented in `FAITHFULNESS_AUDIT.md`.

The unit suite passes under `pytest` (the W3C conformance corpus is marked
`slow` and excluded by default); the code passes `mypy --strict` and `ruff`.

## Documentation

- **[docs/README.md](docs/README.md)** — Learning guide: OWL 2 DL reasoning and
  the hypertableau calculus from scratch, mapped to this codebase
  ([algorithms series](docs/algorithms/00-overview.md))
- **[FAITHFULNESS_AUDIT.md](FAITHFULNESS_AUDIT.md)** — Where and why pyhermit
  diverges from Java HermiT
- **[docs/](docs/)** — Architecture, API reference, tutorials, recipes
- **[examples/](examples/)** — Working examples from basic to advanced
- **[Original Source](https://github.com/phillord/hermit-reasoner)** — Java HermiT

## License

Apache 2.0. See [LICENSE](LICENSE).

Based on HermiT, copyright Oxford University Computing Laboratory 2008–2014.
