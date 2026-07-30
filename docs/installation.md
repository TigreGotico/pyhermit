# Installation Guide

Get PyHermit running on your system in under 5 minutes.

## Requirements

- Python 3.10 or later.
- pip (the Python package manager).
- No Java or other external dependencies.

## Quick install

```bash
pip install hermit-reasoner
```

PyHermit is now installed and ready to use.

## Verify the installation

Run this script to confirm the install works.

```python
from hermit import Reasoner
from hermit.owl_model.class_expression import OWLClass
from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization

# Create a simple ontology: every Dog is an Animal
Animal = OWLClass("http://example.org/Animal")
Dog = OWLClass("http://example.org/Dog")
axioms = [OWLSubClassOfAxiom(Dog, Animal)]

# Compile the axioms and create a reasoner
normalized = OWLNormalization().process_ontology(axioms)
dl_ontology = OWLClausification().clausify(normalized)
reasoner = Reasoner(dl_ontology)
reasoner.precompute_inferences()

# Check it works
print(f"Reasoner is ready: {reasoner.is_consistent()}")
reasoner.dispose()
```

If the script prints `Reasoner is ready: True`, the installation works.

## For developers

### Install for development

```bash
git clone https://github.com/TigreGotico/pyhermit.git
cd pyhermit
pip install -e ".[dev]"
```

### Run tests

```bash
pytest tests/
```

### Check types

```bash
mypy src/
```

### Lint the code

```bash
ruff check src/
```

## Troubleshooting

### ImportError: No module named 'hermit'

Check that pip installed the package.

```bash
pip show hermit-reasoner
```

If pip does not list the package, reinstall it.

```bash
pip install --force-reinstall hermit-reasoner
```

### Version mismatch

If you have several Python versions installed, target the one you want.

```bash
python3.10 -m pip install hermit-reasoner
```

### The problem persists

Open an issue on GitHub with this information:

- Your Python version: `python --version`.
- Your pip version: `pip --version`.
- The full error message.

---
[Home](index.md) · [Concepts →](concepts.md)
