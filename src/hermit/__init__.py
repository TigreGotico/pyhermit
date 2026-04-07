"""
HermiT -- A conformant OWL 2 DL tableau reasoner.

This is a faithful Python port of the HermiT reasoner developed at
the University of Oxford.  It implements the OWL 2 Direct Semantics
via a hyperresolution-based tableau calculus with description graphs.

Basic usage::

    from hermit import Reasoner, Configuration
    from hermit.model import DLOntology

    ontology = ...  # build or load a DLOntology
    reasoner = Reasoner(ontology)
    reasoner.precompute_inferences()
    print(reasoner.is_consistent())
    reasoner.dispose()
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = [
    "Configuration",
    "Reasoner",
    "load_ontology",
]

from hermit.configuration import Configuration
from hermit.reasoner import Reasoner
from hermit.parser import load_ontology
