"""Structural layer: normalization, clausification, expressivity analysis."""

from hermit.structural.builtin_property_manager import BuiltInPropertyManager
from hermit.structural.expression_manager import ExpressionManager
from hermit.structural.normalized_axioms import (
    ComplexObjectPropertyInclusion,
    DataPropertyKey,
    DisjunctiveRule,
    NormalizedAxioms,
    ObjectPropertyKey,
)
from hermit.structural.object_property_inclusion_manager import (
    ObjectPropertyInclusionManager,
)
from hermit.structural.owl_axioms_expressivity import OWLAxiomsExpressivity
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization

__all__ = [
    "BuiltInPropertyManager",
    "ComplexObjectPropertyInclusion",
    "DataPropertyKey",
    "DisjunctiveRule",
    "ExpressionManager",
    "NormalizedAxioms",
    "ObjectPropertyInclusionManager",
    "ObjectPropertyKey",
    "OWLAxiomsExpressivity",
    "OWLClausification",
    "OWLNormalization",
]
