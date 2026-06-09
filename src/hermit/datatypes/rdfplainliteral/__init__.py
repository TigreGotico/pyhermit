"""rdf:PlainLiteral and xsd string-family datatype handler."""
from __future__ import annotations

import re
from typing import Any

from hermit.datatypes.registry import (
    DatatypeHandler,
    DatatypeRegistry,
    MalformedLiteralException,
    UnsupportedFacetException,
    ValueSpaceSubset,
    facet_data_value,
)

XSD_NS = "http://www.w3.org/2001/XMLSchema#"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

RDF_PLAIN_LITERAL = RDF_NS + "PlainLiteral"
XSD_STRING = XSD_NS + "string"

# Lexical-space checks for the pattern-based string datatypes.
_DATATYPE_PATTERNS: dict[str, re.Pattern[str]] = {
    XSD_NS + "normalizedString": re.compile(r"[^\r\n\t]*"),
    XSD_NS + "token": re.compile(r"(?!\s)(?!.*\s\s)(?!.*\s$)[^\r\n\t]*", re.DOTALL),
    XSD_NS + "Name": re.compile(r"[A-Za-z_:][A-Za-z0-9._:\-]*"),
    XSD_NS + "NCName": re.compile(r"[A-Za-z_][A-Za-z0-9._\-]*"),
    XSD_NS + "NMTOKEN": re.compile(r"[A-Za-z0-9._:\-]+"),
    XSD_NS + "language": re.compile(r"[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})*"),
}

_SUPPORTED_FACET_URIS = frozenset({
    XSD_NS + "minLength",
    XSD_NS + "maxLength",
    XSD_NS + "length",
    XSD_NS + "pattern",
    RDF_NS + "langRange",
})

_DATATYPE_SUPERSETS: dict[str, frozenset[str]] = {
    RDF_PLAIN_LITERAL: frozenset({RDF_PLAIN_LITERAL}),
    XSD_STRING: frozenset({RDF_PLAIN_LITERAL, XSD_STRING}),
    XSD_NS + "normalizedString": frozenset({
        RDF_PLAIN_LITERAL, XSD_STRING, XSD_NS + "normalizedString",
    }),
    XSD_NS + "token": frozenset({
        RDF_PLAIN_LITERAL, XSD_STRING, XSD_NS + "normalizedString", XSD_NS + "token",
    }),
    XSD_NS + "Name": frozenset({
        RDF_PLAIN_LITERAL, XSD_STRING, XSD_NS + "normalizedString",
        XSD_NS + "token", XSD_NS + "Name",
    }),
    XSD_NS + "NCName": frozenset({
        RDF_PLAIN_LITERAL, XSD_STRING, XSD_NS + "normalizedString",
        XSD_NS + "token", XSD_NS + "Name", XSD_NS + "NCName",
    }),
    XSD_NS + "NMTOKEN": frozenset({
        RDF_PLAIN_LITERAL, XSD_STRING, XSD_NS + "normalizedString",
        XSD_NS + "token", XSD_NS + "NMTOKEN",
    }),
    XSD_NS + "language": frozenset({
        RDF_PLAIN_LITERAL, XSD_STRING, XSD_NS + "normalizedString",
        XSD_NS + "token", XSD_NS + "language",
    }),
}


class PlainLiteralDataValue:
    """A language-tagged rdf:PlainLiteral value."""

    __slots__ = ("_string", "_language_tag")

    def __init__(self, string: str, language_tag: str) -> None:
        self._string = string
        self._language_tag = language_tag.lower()

    @property
    def string(self) -> str:
        return self._string

    @property
    def language_tag(self) -> str:
        return self._language_tag

    def __hash__(self) -> int:
        return hash((self._string, self._language_tag))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PlainLiteralDataValue):
            return (
                self._string == other._string
                and self._language_tag == other._language_tag
            )
        return False

    def __repr__(self) -> str:
        return f'"{self._string}"@{self._language_tag}'


def _matches_datatype(value: Any, datatype_iri: str) -> bool:
    """Check membership of a parsed value in a string datatype's value space."""
    if isinstance(value, PlainLiteralDataValue):
        return datatype_iri == RDF_PLAIN_LITERAL
    if not isinstance(value, str):
        return False
    if datatype_iri in (RDF_PLAIN_LITERAL, XSD_STRING):
        return True
    pattern = _DATATYPE_PATTERNS.get(datatype_iri)
    return pattern is not None and pattern.fullmatch(value) is not None


class RDFPlainLiteralValueSpaceSubset(ValueSpaceSubset):
    def __init__(self, empty: bool = False):
        self._empty = empty

    def is_empty(self) -> bool:
        return self._empty

    def contains(self, value: Any) -> bool:
        return not self._empty

    def contains_data_value(self, value: Any) -> bool:
        if self._empty:
            return False
        return isinstance(value, (str, PlainLiteralDataValue))

    def has_cardinality_at_least(self, number: int) -> bool:
        return number <= 0 or not self._empty

    def enumerate_data_values(self, data_values: list[Any]) -> None:
        if self._empty:
            return
        raise RuntimeError("The data range is infinite.")

    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        if isinstance(other, RDFPlainLiteralValueSpaceSubset):
            return RDFPlainLiteralValueSpaceSubset(self._empty or other._empty)
        return RDFPlainLiteralValueSpaceSubset(empty=True)

    def complement(self) -> ValueSpaceSubset:
        return RDFPlainLiteralValueSpaceSubset(empty=not self._empty)


class RDFPlainLiteralFacetSubset(RDFPlainLiteralValueSpaceSubset):
    """A subset of a string datatype's value space restricted by facets."""

    def __init__(
        self,
        datatype_iri: str,
        min_length: int = 0,
        max_length: int | None = None,
        patterns: tuple[re.Pattern[str], ...] = (),
        empty: bool = False,
    ) -> None:
        if max_length is not None and min_length > max_length:
            empty = True
        super().__init__(empty=empty)
        self._datatype_iri = datatype_iri
        self._min_length = min_length
        self._max_length = max_length
        self._patterns = patterns

    def contains_data_value(self, value: Any) -> bool:
        if self._empty:
            return False
        if not _matches_datatype(value, self._datatype_iri):
            return False
        text = value.string if isinstance(value, PlainLiteralDataValue) else value
        assert isinstance(text, str)
        if len(text) < self._min_length:
            return False
        if self._max_length is not None and len(text) > self._max_length:
            return False
        return all(pattern.fullmatch(text) is not None for pattern in self._patterns)


def _to_int(value: Any) -> int:
    if isinstance(value, bool):
        raise UnsupportedFacetException("Length facets take integer values.")
    if isinstance(value, int):
        return value
    fraction = getattr(value, "fraction", None)
    if fraction is not None and fraction.denominator == 1:
        return int(fraction)
    try:
        return int(str(value))
    except ValueError:
        raise UnsupportedFacetException(
            f"Length facets take integer values, not {value!r}."
        ) from None


class RDFPlainLiteralDatatypeHandler(DatatypeHandler):
    IRIS = (
        RDF_PLAIN_LITERAL,
        XSD_STRING,
        XSD_NS + "normalizedString",
        XSD_NS + "token",
        XSD_NS + "Name",
        XSD_NS + "NCName",
        XSD_NS + "NMTOKEN",
        XSD_NS + "language",
    )

    def get_datatype_iris(self) -> tuple[str, ...]:
        return self.IRIS

    def parse_literal(self, lexical_form: str, datatype_iri: str) -> Any:
        return lexical_form

    def parse_data_value(self, lexical_form: str, datatype_iri: str) -> Any:
        if datatype_iri == RDF_PLAIN_LITERAL:
            last_at = lexical_form.rfind("@")
            if last_at == -1:
                raise MalformedLiteralException(
                    f"Invalid rdf:PlainLiteral literal: {lexical_form!r}"
                )
            string = lexical_form[:last_at]
            language_tag = lexical_form[last_at + 1:]
            if not language_tag:
                return string
            return PlainLiteralDataValue(string, language_tag)
        if not _matches_datatype(lexical_form, datatype_iri):
            raise MalformedLiteralException(
                f"Invalid {datatype_iri} literal: {lexical_form!r}"
            )
        return lexical_form

    def validate_datatype_restriction(self, datatype_restriction: Any) -> None:
        for index in range(datatype_restriction.number_of_facet_restrictions() - 1, -1, -1):
            facet_uri = datatype_restriction.facet_uri(index)
            if facet_uri not in _SUPPORTED_FACET_URIS:
                raise UnsupportedFacetException(
                    f"Facet with URI '{facet_uri}' is not supported on "
                    "rdf:PlainLiteral; only xsd:minLength, xsd:maxLength, "
                    "xsd:length, xsd:pattern, and rdf:langRange are supported."
                )

    def create_value_space_subset(
        self, datatype_iri: str, facet_uris: Any, facet_values: Any
    ) -> RDFPlainLiteralValueSpaceSubset:
        if not facet_uris:
            return RDFPlainLiteralFacetSubset(datatype_iri or RDF_PLAIN_LITERAL)
        min_length = 0
        max_length: int | None = None
        patterns: list[re.Pattern[str]] = []
        for facet_uri, facet_value in zip(facet_uris, facet_values, strict=False):
            raw = facet_data_value(facet_value)
            if facet_uri == XSD_NS + "minLength":
                min_length = max(min_length, _to_int(raw))
            elif facet_uri == XSD_NS + "maxLength":
                limit = _to_int(raw)
                max_length = limit if max_length is None else min(max_length, limit)
            elif facet_uri == XSD_NS + "length":
                value = _to_int(raw)
                min_length = max(min_length, value)
                max_length = value if max_length is None else min(max_length, value)
            elif facet_uri == XSD_NS + "pattern":
                try:
                    patterns.append(re.compile(str(raw)))
                except re.error:
                    pass
            # rdf:langRange restricts only language-tagged literals; it never
            # empties the plain-string part of the space.
        return RDFPlainLiteralFacetSubset(
            datatype_iri or RDF_PLAIN_LITERAL,
            min_length=min_length,
            max_length=max_length,
            patterns=tuple(patterns),
        )

    def entire_space(self, datatype_iri: str) -> RDFPlainLiteralValueSpaceSubset:
        return RDFPlainLiteralFacetSubset(datatype_iri or RDF_PLAIN_LITERAL)

    def empty_space(self, datatype_iri: str) -> RDFPlainLiteralValueSpaceSubset:
        return RDFPlainLiteralValueSpaceSubset(empty=True)

    def is_subset_of_datatype(
        self, subset_datatype_iri: str, superset_datatype_iri: str
    ) -> bool:
        return superset_datatype_iri in _DATATYPE_SUPERSETS[subset_datatype_iri]


DatatypeRegistry.register(RDFPlainLiteralDatatypeHandler())
