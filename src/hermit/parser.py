"""OWL file parser.

Loads OWL ontologies and converts them to :mod:`hermit.owl_model` axiom
objects (mirroring the OWL API used by Java HermiT). The document is dispatched
by syntax to a standard-library reader -- RDF/XML, OWL/XML, or Functional-Style
Syntax -- each emitting first-class :class:`OWLAxiom` objects.

Pipeline::

    OWL file -> RDF/XML | OWL/XML | FSS reader -> list[OWLAxiom]
                                              -> OWLNormalization -> NormalizedAxioms
                                              -> OWLClausification -> DLOntology
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.owl_model.owl_axiom import OWLAxiom


def load_ontology(path: str | Path) -> list[OWLAxiom]:
    """Load an OWL ontology from a file.

    Args:
        path: Path to an OWL document (.owl, .rdf, .owx, .ofn, ...).

    Returns:
        List of OWLAxiom objects covering the logical axioms of the document.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the file cannot be parsed as OWL.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"OWL file not found: {path}")

    text = path.read_text(encoding="utf-8")
    return load_ontology_from_string(text, base=path.as_uri(), suffix=path.suffix)


def load_ontology_from_string(
    text: str, base: str = "", suffix: str = ""
) -> list[OWLAxiom]:
    """Load OWL axioms from an in-memory ontology document.

    Dispatches by content: Functional-Style Syntax, OWL/XML, and RDF/XML are
    each parsed by the built-in stdlib readers. This is the faithful loading
    path that emits the same axioms the OWL API would, avoiding silent axiom
    loss (typed-node ABox assertions, custom datatypes, FSS).
    """
    stripped = text.lstrip()
    if _is_functional(text, stripped, suffix):
        from hermit.fss import parse_functional_syntax

        return parse_functional_syntax(text)

    if _is_owl_xml(stripped):
        from hermit.owlxml import parse_owlxml

        return parse_owlxml(text)

    from hermit.owl_rdf import map_triples_to_axioms
    from hermit.rdfxml import parse_rdfxml

    triples = parse_rdfxml(text, base)
    return map_triples_to_axioms(triples)


def _is_functional(text: str, stripped: str, suffix: str) -> bool:
    if suffix == ".ofn":
        return True
    if stripped.startswith("<"):
        return False
    return (
        stripped.startswith("Prefix(")
        or stripped.startswith("Ontology(")
        or "\nOntology(" in text
        or bool(stripped) and stripped.startswith("#")
        and ("Ontology(" in text or "Prefix(" in text)
    )


def _is_owl_xml(stripped: str) -> bool:
    head = stripped
    if head.startswith("<?xml") and "?>" in head:
        head = head[head.find("?>") + 2:].lstrip()
    while head.startswith("<!--") and "-->" in head:
        head = head[head.find("-->") + 3:].lstrip()
    # OWL/XML documents have a root <Ontology> element (default owl: namespace);
    # RDF/XML documents have <rdf:RDF> or <owl:Ontology> nested under rdf:RDF.
    return head.startswith("<Ontology")


__all__ = ["load_ontology", "load_ontology_from_string"]
