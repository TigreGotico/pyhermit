# Installation Guide

Get PyHermit up and running on your system in less than 5 minutes.

## Requirements

- Python 3.10 or later
- pip (Python package manager)
- No Java or external dependencies required

## Quick Install

```bash
pip install hermit-reasoner
```

That's it! PyHermit is now installed and ready to use.

## Verify Installation

To confirm everything works:

```python
from hermit import Reasoner
from hermit.model import DLOntology, OWLClass, SubClassOf

# Create a simple ontology
Animal = OWLClass("http://example.org/Animal")
Dog = OWLClass("http://example.org/Dog")

ontology = DLOntology()
ontology.add_axiom(SubClassOf(Dog, Animal))

# Create a reasoner
reasoner = Reasoner(ontology)
reasoner.precompute_inferences()

# Check it works
print(f"Reasoner is ready: {reasoner.is_consistent()}")
reasoner.dispose()
```

If you see `Reasoner is ready: True`, the installation is successful!

## For Developers

### Install for Development

```bash
git clone https://github.com/TigreGotico/pyhermit.git
cd pyhermit
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/
```

### Type Checking

```bash
mypy src/
```

### Linting

```bash
ruff check src/
```

## Troubleshooting

### ImportError: No module named 'hermit'

Make sure pip installed the package correctly:

```bash
pip show hermit-reasoner
```

If not listed, try reinstalling:

```bash
pip install --force-reinstall hermit-reasoner
```

### Version Mismatch

If you have multiple Python versions, use the specific version:

```bash
python3.10 -m pip install hermit-reasoner
```

### Still Having Issues?

Open an issue on GitHub with:
- Your Python version: `python --version`
- Your pip version: `pip --version`
- Full error message

---

**Next:** Read [Concepts](./concepts.md) to understand OWL and reasoning.
