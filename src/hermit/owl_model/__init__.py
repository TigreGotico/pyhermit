# vendored from owlapy 1.6.4 — MIT License

"""OWL model types (vendored from owlapy).

This package contains a pure-Python vendored copy of owlapy's OWL model
types. All imports have been rewritten from owlapy.* to hermit.owl_model.*.
"""

from __future__ import annotations

# Core types
from .iri import IRI
from .owl_object import OWLObject, OWLEntity, OWLNamedObject
from .owl_annotation import OWLAnnotationSubject, OWLAnnotationValue
from .owl_axiom import OWLAxiom

# Import submodules for lazy access to other types
from . import (
    owl_datatype,
    owl_individual,
    owl_property,
    owl_data_ranges,
    owl_literal,
    class_expression,
    namespaces,
)

__all__ = [
    "IRI",
    "OWLObject",
    "OWLEntity",
    "OWLNamedObject",
    "OWLAnnotationSubject",
    "OWLAnnotationValue",
    "OWLAxiom",
    # Submodules
    "owl_datatype",
    "owl_individual",
    "owl_property",
    "owl_data_ranges",
    "owl_literal",
    "class_expression",
    "namespaces",
]
