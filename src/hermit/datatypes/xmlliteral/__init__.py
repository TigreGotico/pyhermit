"""rdf:XMLLiteral datatype handler."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from hermit.datatypes.registry import (
    DatatypeHandler,
    DatatypeRegistry,
    MalformedLiteralException,
    UnsupportedFacetException,
    ValueSpaceSubset,
)

_WRAPPER_OPEN = "<arbitraryTag>"
_WRAPPER_CLOSE = "</arbitraryTag>"


def _canonicalize_xml(lexical_form: str) -> str:
    """Canonicalize an rdf:XMLLiteral lexical form.

    Mirrors the Java ``XMLLiteral.parse``: the XML content (a document
    fragment) is wrapped in an arbitrary element, canonicalized with comments
    preserved, and unwrapped, so that equality of XMLLiteral values is
    equality of their canonical form (attribute order, self-closing tags,
    and whitespace in tags do not matter).
    """
    canonical = ET.canonicalize(
        _WRAPPER_OPEN + lexical_form + _WRAPPER_CLOSE, with_comments=True
    )
    assert canonical.startswith(_WRAPPER_OPEN)
    assert canonical.endswith(_WRAPPER_CLOSE)
    return canonical[len(_WRAPPER_OPEN):-len(_WRAPPER_CLOSE)]


class XMLLiteralValue:
    """An rdf:XMLLiteral data value, distinct from plain strings."""

    __slots__ = ("_xml",)

    def __init__(self, xml: str) -> None:
        self._xml = xml

    @property
    def xml(self) -> str:
        return self._xml

    def __hash__(self) -> int:
        return hash(("XMLLiteral", self._xml))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, XMLLiteralValue):
            return self._xml == other._xml
        return False

    def __repr__(self) -> str:
        return f"XMLLiteralValue({self._xml!r})"


class XMLLiteralValueSpaceSubset(ValueSpaceSubset):
    def __init__(self, empty: bool = False):
        self._empty = empty

    def is_empty(self) -> bool:
        return self._empty

    def contains(self, value: Any) -> bool:
        return not self._empty

    def contains_data_value(self, value: Any) -> bool:
        return not self._empty and isinstance(value, XMLLiteralValue)

    def has_cardinality_at_least(self, number: int) -> bool:
        return number <= 0 or not self._empty

    def enumerate_data_values(self, data_values: list[Any]) -> None:
        if self._empty:
            return
        raise RuntimeError("The data range is infinite.")

    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        if isinstance(other, XMLLiteralValueSpaceSubset):
            return XMLLiteralValueSpaceSubset(self._empty or other._empty)
        return XMLLiteralValueSpaceSubset(empty=True)

    def complement(self) -> ValueSpaceSubset:
        return XMLLiteralValueSpaceSubset(empty=not self._empty)


class XMLLiteralDatatypeHandler(DatatypeHandler):
    IRIS = ("http://www.w3.org/1999/02/22-rdf-syntax-ns#XMLLiteral",)

    def get_datatype_iris(self) -> tuple[str, ...]:
        return self.IRIS

    def parse_literal(self, lexical_form: str, datatype_iri: str) -> Any:
        try:
            return _canonicalize_xml(lexical_form)
        except ET.ParseError as error:
            raise MalformedLiteralException(
                f"Invalid rdf:XMLLiteral: {lexical_form!r}"
            ) from error

    def parse_data_value(self, lexical_form: str, datatype_iri: str) -> Any:
        return XMLLiteralValue(self.parse_literal(lexical_form, datatype_iri))

    def validate_datatype_restriction(self, datatype_restriction: Any) -> None:
        if datatype_restriction.number_of_facet_restrictions() > 0:
            raise UnsupportedFacetException(
                "The rdf:XMLLiteral datatype does not provide any facets."
            )

    def create_value_space_subset(
        self, datatype_iri: str, facet_uris: Any, facet_values: Any
    ) -> XMLLiteralValueSpaceSubset:
        return XMLLiteralValueSpaceSubset()

    def entire_space(self, datatype_iri: str) -> XMLLiteralValueSpaceSubset:
        return XMLLiteralValueSpaceSubset()

    def empty_space(self, datatype_iri: str) -> XMLLiteralValueSpaceSubset:
        return XMLLiteralValueSpaceSubset(empty=True)

DatatypeRegistry.register(XMLLiteralDatatypeHandler())
