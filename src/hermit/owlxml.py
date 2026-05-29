"""OWL/XML reader.

Parses the OWL 2 XML serialization (https://www.w3.org/TR/owl2-xml-serialization/)
into :mod:`hermit.owl_model` axioms. Element names mirror the Functional-Style
Syntax constructors, so this reader translates the XML element tree into the
same intermediate term objects the FSS builder consumes and then reuses that
builder.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

from hermit.fss import _Builder, _Expr, _IRI, _Lit, _Parser

if TYPE_CHECKING:
    from hermit.owl_model.owl_axiom import OWLAxiom

OWL = "http://www.w3.org/2002/07/owl#"
XSD = "http://www.w3.org/2001/XMLSchema#"
OWLX = "http://www.w3.org/2002/07/owl#"

_AXIOM_TAGS = {
    "SubClassOf", "EquivalentClasses", "DisjointClasses", "DisjointUnion",
    "ClassAssertion", "ObjectPropertyAssertion", "DataPropertyAssertion",
    "SameIndividual", "DifferentIndividuals", "SubObjectPropertyOf",
    "EquivalentObjectProperties", "InverseObjectProperties",
    "ObjectPropertyDomain", "ObjectPropertyRange", "TransitiveObjectProperty",
    "SymmetricObjectProperty", "AsymmetricObjectProperty",
    "ReflexiveObjectProperty", "IrreflexiveObjectProperty",
    "FunctionalObjectProperty", "InverseFunctionalObjectProperty",
    "SubDataPropertyOf", "EquivalentDataProperties", "DataPropertyDomain",
    "FunctionalDataProperty", "Declaration",
}


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def parse_owlxml(text: str) -> list[OWLAxiom]:
    """Parse an OWL/XML document into OWL axioms."""
    from hermit.owl_model.owl_axiom import OWLAxiom

    root = ET.fromstring(text)
    parser = _Parser("")
    base = root.get("ontologyIRI") or root.get(
        "{http://www.w3.org/XML/1998/namespace}base"
    )
    if base:
        parser.base = base
    # Collect prefixes declared as <Prefix name="ex:" IRI="..."/>.
    for child in root:
        if _localname(child.tag) == "Prefix":
            name = child.get("name", "")
            iri = child.get("IRI", "")
            if name and not name.endswith(":"):
                name += ":"
            parser.prefixes[name] = iri
    builder = _Builder(parser)
    axioms: list[OWLAxiom] = []
    for child in root:
        ln = _localname(child.tag)
        if ln not in _AXIOM_TAGS:
            continue
        args = [_to_term(c, parser) for c in child if not _is_annotation_tag(c)]
        try:
            ax = builder.build(ln, args)
        except Exception:
            ax = None
        if ax is not None:
            if isinstance(ax, list):
                axioms.extend(ax)
            elif isinstance(ax, OWLAxiom):
                axioms.append(ax)
    return axioms


def _is_annotation_tag(elem: ET.Element) -> bool:
    return _localname(elem.tag) == "Annotation"


def _abbrev(elem: ET.Element, parser: _Parser) -> str:
    iri = elem.get("IRI")
    if iri is not None:
        if iri.startswith("#") or (":" not in iri and iri):
            return parser.base + iri if parser.base else iri
        return iri
    ab = elem.get("abbreviatedIRI")
    if ab is not None:
        prefix, _, local = ab.partition(":")
        pfx = prefix + ":"
        return parser.prefixes.get(pfx, "") + local
    return elem.text or ""


def _to_term(elem: ET.Element, parser: _Parser) -> object:
    ln = _localname(elem.tag)
    if ln in ("Class", "ObjectProperty", "DataProperty", "NamedIndividual",
              "Datatype", "AnnotationProperty", "AnonymousIndividual"):
        return _IRI(_abbrev(elem, parser))
    if ln == "Literal":
        dt = elem.get("datatypeIRI")
        return _Lit(elem.text or "", dt, None)
    if ln in ("ObjectMinCardinality", "ObjectMaxCardinality",
              "ObjectExactCardinality", "DataMinCardinality",
              "DataMaxCardinality", "DataExactCardinality"):
        card = elem.get("cardinality", "0")
        args: list[object] = [_IRI(card)]
        args.extend(_to_term(c, parser) for c in elem)
        return _Expr(ln, args)
    # Generic constructor element.
    return _Expr(ln, [_to_term(c, parser) for c in elem])


__all__ = ["parse_owlxml"]
