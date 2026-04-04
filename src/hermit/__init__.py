"""
HermiT — A conformant OWL 2 DL tableau reasoner.

This is a faithful Python port of the HermiT reasoner developed at
the University of Oxford.  It implements the OWL 2 Direct Semantics
via a hyperresolution-based tableau calculus with description graphs.

Basic usage::

    from hermit import Reasoner
    from hermit.model import OWLOntology

    ontology = OWLOntology.load("pizza.owl")
    reasoner = Reasoner(ontology)
    reasoner.precompute_inferences()
    print(reasoner.is_consistent())
    reasoner.dispose()
"""

__version__ = "0.1.0"
__all__ = ["Reasoner", "Configuration"]


def __getattr__(name: str):
    if name == "Reasoner":
        from hermit.reasoner import Reasoner
        return Reasoner
    if name == "Configuration":
        from hermit.configuration import Configuration
        return Configuration
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
