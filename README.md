# PyHermit: Python OWL 2 DL Reasoner

[![License: LGPL-3.0](https://img.shields.io/badge/License-LGPL--3.0-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0.html)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

PyHermit is a Python port of [HermiT](http://hermit-reasoner.com), an OWL 2 DL reasoner developed at the University of Oxford. It reasons about OWL ontologies with tableau-based decision procedures and needs no JVM.

## Features

- OWL 2 DL reasoning: a tableau decision procedure over the OWL 2 Direct Semantics constructs.
- Tableau algorithm: hyperresolution with configurable blocking strategies.
- Non-simple property validation: the OWL 2 spec forbids transitive, role-chain, and inherited-superrole properties in cardinality restrictions, `hasSelf`, asymmetric, irreflexive, or disjoint axioms. PyHermit rejects these at clausification time with a `ValueError`.
- All OWL 2 datatypes: `xsd:string`, `decimal`, `integer`, `float`, `double`, `dateTime`, `boolean`, `anyURI`, and more.
- SWRL rules and Datalog queries: DL-safe rule support with query evaluation.
- OWL file parsing: load RDF/XML, OWL/XML, and Functional-Style Syntax through a pure stdlib reader (`hermit.parser.load_ontology`).
- Pure Python: no JVM, no external binaries, a single `pip install`.
- Full type hints: the code passes `mypy --strict`.

## Install

```bash
pip install hermit-reasoner
```

## Basic usage

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

## Load from OWL files

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
OWLClausification (DL clauses, non-simple property validation via ObjectPropertyInclusionManager)
    |
    v
Tableau Expansion (hyperresolution with blocking)
    |
    v
Classification & Instance Retrieval
```

See [docs/](docs/) for architecture detail and API reference.

## Non-simple property enforcement

OWL 2 forbids non-simple properties (transitive, or a superrole of a role chain) in certain axiom positions. PyHermit enforces this at clausification time:

```python
from hermit.structural.owl_clausification import OWLClausification

clausification = OWLClausification()
try:
    dl_ontology = clausification.clausify(normalized)
except ValueError as e:
    # e.g. "Non-simple property '...' cannot be asymmetric (OWL 2 violation)"
    print(e)
```

PyHermit checks these constraints, per OWL 2 spec Section 11.2:

- `AsymmetricObjectProperty`
- `IrreflexiveObjectProperty`
- `DisjointObjectProperties`
- Cardinality restrictions (`ObjectMinCardinality`, `ObjectMaxCardinality`, `ObjectExactCardinality`)
- `ObjectHasSelf`

Source: `ObjectPropertyInclusionManager._validate_complex_property_constraints`, at `src/hermit/structural/object_property_inclusion_manager.py:360`.

## Project status

PyHermit is a structural port of Java HermiT. The reasoning core is implemented: tableau, blocking, hyperresolution, classification, datatype reasoning, and SWRL/Datalog query answering. Ontology loading uses a pure stdlib reader (RDF/XML, OWL/XML, Functional-Style Syntax).

- TBox reasoning (classification, subsumption)
- ABox instance retrieval
- Datatype reasoning
- SWRL rules and Datalog query answering
- Non-simple property validation
- OWL file parsing through a pure stdlib reader (RDF/XML, OWL/XML, FSS)

**Conformance:** PyHermit passes 340 of 350 W3C OWL WG Approved-DL test cases at a 20-second per-case budget. Run this with `pytest -m slow tests/test_wg_conformance.py`, or `python scripts/wg_run.py approved --list-fails --timeout=20`. It reports zero wrong answers, zero errors, and zero unchecked conclusions. The 10 non-passing cases time out on hard combinatorial ontologies. Several of them pass with the 300-second budget the Java harness uses. `FAITHFULNESS_AUDIT.md` documents intentional divergences from the Java original.

The unit suite passes under `pytest` (the W3C conformance corpus is marked `slow` and excluded by default). The code passes `mypy --strict` and `ruff`.

## Documentation

- [docs/README.md](docs/README.md): a learning guide covering OWL 2 DL reasoning and the hypertableau calculus from scratch, mapped to this codebase (see the [algorithms series](docs/algorithms/00-overview.md)).
- [FAITHFULNESS_AUDIT.md](FAITHFULNESS_AUDIT.md): where and why PyHermit diverges from Java HermiT.
- [docs/](docs/): architecture, API reference, tutorials, and recipes.
- [examples/](examples/): working examples, from basic to advanced.
- [Original source](https://github.com/phillord/hermit-reasoner): Java HermiT.

## Related projects

- [phillord/hermit-reasoner](https://github.com/phillord/hermit-reasoner): the Java HermiT reasoner this project ports.

## License

LGPL-3.0-or-later, matching upstream HermiT. See [LICENSE](LICENSE).

Based on HermiT, copyright Oxford University Computing Laboratory 2008-2014.
