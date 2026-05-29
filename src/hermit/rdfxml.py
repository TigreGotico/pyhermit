"""Stdlib RDF/XML reader.

Parses an RDF/XML document into a flat list of RDF triples using only the
standard-library :mod:`xml.etree.ElementTree`. The grammar implemented covers
the subset that OWL 2 ontologies in RDF/XML serialization use, plus the
RDF/XML productions the W3C OWL test corpus relies on:

* node elements (typed and ``rdf:Description``) with ``rdf:about`` / ``rdf:ID`` /
  ``rdf:nodeID`` subjects, and blank-node subjects for anonymous nodes,
* property elements with ``rdf:resource`` / ``rdf:nodeID`` object references,
  nested node objects, and literal text content (``rdf:datatype`` / ``xml:lang``),
* ``rdf:parseType="Collection"`` (RDF list of the collected node objects),
* ``rdf:parseType="Resource"`` (anonymous node inline),
* ``rdf:parseType="Literal"`` (XML literal content),
* the ``rdf:type`` shorthand of a typed node element,
* ``xml:base`` resolution and bare/relative IRI resolution against the base.

Object identity for IRIs is the absolute IRI string. Blank nodes are
represented by :class:`BNode`. Literals are :class:`Literal`.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import urldefrag, urljoin

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
XML_NS = "http://www.w3.org/XML/1998/namespace"

RDF_TYPE = RDF + "type"
RDF_FIRST = RDF + "first"
RDF_REST = RDF + "rest"
RDF_NIL = RDF + "nil"
RDF_DESCRIPTION = RDF + "Description"
RDF_RDF = RDF + "RDF"


@dataclass(frozen=True)
class BNode:
    """A blank node, identified by a generated or document-supplied id."""

    id: str

    def __str__(self) -> str:  # pragma: no cover - debugging aid
        return f"_:{self.id}"


@dataclass(frozen=True)
class Literal:
    """An RDF literal with an optional datatype IRI and language tag."""

    value: str
    datatype: str | None = None
    lang: str | None = None


# A triple object is an IRI string, a BNode, or a Literal.
Term = str | BNode | Literal
Triple = tuple[Term, str, Term]


class _BNodeFactory:
    def __init__(self) -> None:
        self._counter = 0
        self._named: dict[str, BNode] = {}

    def fresh(self) -> BNode:
        self._counter += 1
        return BNode(f"b{self._counter}")

    def named(self, node_id: str) -> BNode:
        if node_id not in self._named:
            self._named[node_id] = BNode(f"n{node_id}")
        return self._named[node_id]


def _tag(elem: ET.Element) -> str:
    """Return an element/attribute tag as a flat ``namespace+local`` IRI.

    ElementTree reports namespaced names as ``{namespace}local``; OWL/RDF
    namespaces already end in ``#`` or ``/`` so concatenation reproduces the
    original IRI.
    """
    t = elem.tag
    if t.startswith("{"):
        ns, local = t[1:].split("}", 1)
        return ns + local
    return t


def _qname_to_iri(name: str) -> str:
    if name.startswith("{"):
        ns, local = name[1:].split("}", 1)
        return ns + local
    return name


def _local_attr(elem: ET.Element, name: str) -> str | None:
    """Return an RDF/XML attribute value, accepting both the namespaced and
    (non-conformant but corpus-present) bare attribute spellings."""
    val = elem.get(f"{{{RDF}}}{name}")
    if val is None:
        val = elem.get(name)
    return val


def _resolve(base: str, ref: str) -> str:
    """Resolve a possibly-relative IRI reference against the base IRI."""
    if not ref:
        return base
    # Absolute IRIs (have a scheme) are returned unchanged.
    if "://" in ref or ref.startswith("urn:") or ref.startswith("mailto:"):
        return ref
    return urljoin(base, ref)


def parse_rdfxml(text: str, base: str = "") -> list[Triple]:
    """Parse an RDF/XML document string into a list of triples."""
    root = ET.fromstring(text)
    triples: list[Triple] = []
    bnodes = _BNodeFactory()
    doc_base = root.get(f"{{{XML_NS}}}base") or base
    doc_base = urldefrag(doc_base)[0] if doc_base else base

    if _tag(root) == RDF_RDF:
        for child in root:
            _node_element(child, doc_base, triples, bnodes)
    else:
        # A document whose root is itself a node element.
        _node_element(root, doc_base, triples, bnodes)
    return triples


def _current_base(elem: ET.Element, base: str) -> str:
    own = elem.get(f"{{{XML_NS}}}base")
    if own:
        return urldefrag(_resolve(base, own))[0]
    return base


def _node_subject(
    elem: ET.Element, base: str, bnodes: _BNodeFactory
) -> Term:
    about = _local_attr(elem, "about")
    if about is not None:
        return _resolve(base, about)
    node_id = _local_attr(elem, "nodeID")
    if node_id is not None:
        return bnodes.named(node_id)
    rid = _local_attr(elem, "ID")
    if rid is not None:
        return _resolve(base, "#" + rid)
    return bnodes.fresh()


def _node_element(
    elem: ET.Element,
    base: str,
    triples: list[Triple],
    bnodes: _BNodeFactory,
) -> Term:
    """Process a node element, returning the subject it denotes."""
    base = _current_base(elem, base)
    subject = _node_subject(elem, base, bnodes)

    # Typed node element: <owl:Class .../> means subject rdf:type owl:Class.
    if _tag(elem) != RDF_DESCRIPTION:
        triples.append((subject, RDF_TYPE, _tag(elem)))

    for prop in elem:
        _property_element(prop, subject, base, triples, bnodes)
    return subject


def _list_from_collection(
    items: list[Term],
    triples: list[Triple],
    bnodes: _BNodeFactory,
) -> Term:
    """Build an RDF list (rdf:first/rdf:rest/rdf:nil) from collected objects."""
    if not items:
        return RDF_NIL
    head: Term = RDF_NIL
    for item in reversed(items):
        cell = bnodes.fresh()
        triples.append((cell, RDF_FIRST, item))
        triples.append((cell, RDF_REST, head))
        head = cell
    return head


def _property_element(
    elem: ET.Element,
    subject: Term,
    base: str,
    triples: list[Triple],
    bnodes: _BNodeFactory,
) -> None:
    base = _current_base(elem, base)
    pred = _tag(elem)

    # rdf:resource — IRI object reference.
    resource = _local_attr(elem, "resource")
    if resource is not None:
        triples.append((subject, pred, _resolve(base, resource)))
        _reify_property_attrs(elem, _resolve(base, resource), base, triples, bnodes)
        return

    # rdf:nodeID — blank-node object reference.
    node_id = _local_attr(elem, "nodeID")
    if node_id is not None:
        triples.append((subject, pred, bnodes.named(node_id)))
        return

    parse_type = elem.get(f"{{{RDF}}}parseType") or elem.get("parseType")

    if parse_type == "Collection":
        items = [_node_element(child, base, triples, bnodes) for child in elem]
        triples.append((subject, pred, _list_from_collection(items, triples, bnodes)))
        return

    if parse_type == "Resource":
        anon = bnodes.fresh()
        triples.append((subject, pred, anon))
        for child in elem:
            _property_element(child, anon, base, triples, bnodes)
        return

    if parse_type == "Literal":
        inner = "".join(ET.tostring(c, encoding="unicode") for c in elem)
        text = (elem.text or "") + inner
        triples.append(
            (subject, pred, Literal(text, RDF + "XMLLiteral"))
        )
        return

    children = list(elem)
    if children:
        # Property whose value is one or more nested node elements.
        for child in children:
            obj = _node_element(child, base, triples, bnodes)
            triples.append((subject, pred, obj))
        return

    # Property attributes on the property element shorthand (e.g.
    # <ex:p ex:q="v"/>) create an anonymous object node.
    extra = _property_attributes(elem)
    if extra:
        anon = bnodes.fresh()
        triples.append((subject, pred, anon))
        for p_iri, val in extra:
            triples.append((anon, p_iri, Literal(val)))
        return

    # Literal text content.
    text = elem.text or ""
    datatype = _local_attr(elem, "datatype")
    if datatype is not None:
        datatype = _resolve(base, datatype)
    lang = elem.get(f"{{{XML_NS}}}lang")
    triples.append((subject, pred, Literal(text, datatype, lang)))


def _property_attributes(elem: ET.Element) -> list[tuple[str, str]]:
    """Return non-RDF property attributes (the property-attribute shorthand)."""
    out: list[tuple[str, str]] = []
    for key, val in elem.attrib.items():
        if key.startswith(f"{{{RDF}}}") or key.startswith(f"{{{XML_NS}}}"):
            continue
        if key in ("about", "ID", "resource", "nodeID", "datatype", "parseType"):
            continue
        if not key.startswith("{"):
            continue
        out.append((_qname_to_iri(key), val))
    return out


def _reify_property_attrs(
    elem: ET.Element,
    obj: Term,
    base: str,
    triples: list[Triple],
    bnodes: _BNodeFactory,
) -> None:
    """Handle property attributes co-located with rdf:resource (rare)."""
    for p_iri, val in _property_attributes(elem):
        if isinstance(obj, (str, BNode)):
            triples.append((obj, p_iri, Literal(val)))
