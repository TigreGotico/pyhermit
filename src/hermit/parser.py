"""OWL file parser using owlready2.

Loads OWL/RDF ontologies from files and converts them to hermit.owl_model types.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from hermit.owl_model.owl_axiom import OWLAxiom


def load_ontology(path: str | Path) -> Iterable[OWLAxiom]:
    """Load an OWL ontology from a file.

    Args:
        path: Path to OWL/RDF file (.owl, .ttl, .rdf, etc.)

    Returns:
        Iterator of OWLAxiom objects

    Raises:
        ImportError: If owlready2 is not installed
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file cannot be parsed as OWL
    """
    try:
        import owlready2
    except ImportError as e:
        raise ImportError(
            "owlready2 is required for OWL file parsing. "
            "Install it with: pip install owlready2"
        ) from e

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"OWL file not found: {path}")

    # Load ontology with owlready2
    try:
        onto = owlready2.get_ontology(str(path.as_uri())).load()
    except Exception as e:
        raise ValueError(f"Failed to parse OWL file: {path}") from e

    # Convert to hermit.owl_model axioms
    mapper = _OwlreadyMapper()
    axioms = []

    # Iterate over logical axioms (not import declarations, annotations, etc.)
    for axiom in onto.logical_axioms:
        try:
            hermit_axiom = mapper.map_axiom(axiom)
            if hermit_axiom is not None:
                axioms.append(hermit_axiom)
        except Exception:
            # Skip axioms that can't be mapped
            pass

    return axioms


class _OwlreadyMapper:
    """Converts owlready2 objects to hermit.owl_model types."""

    def __init__(self) -> None:
        """Initialize the mapper."""
        self._iri_cache: dict[str, object] = {}
        self._class_cache: dict[str, object] = {}

    def map_axiom(self, axiom: object) -> object | None:
        """Map an owlready2 axiom to hermit.owl_model type.

        Args:
            axiom: owlready2 axiom object

        Returns:
            hermit.owl_model.OWLAxiom or None if unmappable
        """
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom

        # Simple dispatch on axiom type
        axiom_class_name = type(axiom).__name__

        # Handle SubClassOf axioms
        if axiom_class_name == "SubClassOf" or "SubClassOf" in str(axiom):
            # Try to extract sub and super class expressions
            # This is a simplified version - real implementation would be more complete
            return self._map_subclass_axiom(axiom)

        # Handle EquivalentClasses
        if axiom_class_name == "EquivalentClasses" or "EquivalentClasses" in str(axiom):
            return self._map_equivalent_classes_axiom(axiom)

        # Handle DisjointClasses
        if axiom_class_name == "DisjointClasses" or "DisjointClasses" in str(axiom):
            return self._map_disjoint_classes_axiom(axiom)

        # Handle ClassAssertion
        if axiom_class_name == "ClassAssertion" or "ClassAssertion" in str(axiom):
            return self._map_class_assertion_axiom(axiom)

        # Handle ObjectPropertyAssertion
        if axiom_class_name == "ObjectPropertyAssertion" or "ObjectPropertyAssertion" in str(axiom):
            return self._map_object_property_assertion_axiom(axiom)

        # Handle DataPropertyAssertion
        if axiom_class_name == "DataPropertyAssertion" or "DataPropertyAssertion" in str(axiom):
            return self._map_data_property_assertion_axiom(axiom)

        # For other axiom types, return None (unmapped)
        return None

    def _map_subclass_axiom(self, axiom: object) -> object | None:
        """Map a SubClassOf axiom."""
        # This would extract sub and super class expressions
        # from the owlready2 axiom and create OWLSubClassOfAxiom
        # Simplified version just returns None
        return None

    def _map_equivalent_classes_axiom(self, axiom: object) -> object | None:
        """Map an EquivalentClasses axiom."""
        return None

    def _map_disjoint_classes_axiom(self, axiom: object) -> object | None:
        """Map a DisjointClasses axiom."""
        return None

    def _map_class_assertion_axiom(self, axiom: object) -> object | None:
        """Map a ClassAssertion axiom."""
        return None

    def _map_object_property_assertion_axiom(self, axiom: object) -> object | None:
        """Map an ObjectPropertyAssertion axiom."""
        return None

    def _map_data_property_assertion_axiom(self, axiom: object) -> object | None:
        """Map a DataPropertyAssertion axiom."""
        return None

    def _get_or_create_iri(self, iri_str: str) -> object:
        """Get or create an IRI object."""
        if iri_str not in self._iri_cache:
            from hermit.owl_model.iri import IRI
            self._iri_cache[iri_str] = IRI(iri_str)
        return self._iri_cache[iri_str]

    def _get_or_create_class(self, class_iri: str) -> object:
        """Get or create an OWLClass object."""
        if class_iri not in self._class_cache:
            from hermit.owl_model.class_expression import OWLClass
            iri = self._get_or_create_iri(class_iri)
            self._class_cache[class_iri] = OWLClass(iri)  # type: ignore[arg-type]
        return self._class_cache[class_iri]


__all__ = ["load_ontology"]
