"""xsd:anyURI datatype handler."""
from __future__ import annotations

import re
from typing import Any

from hermit.datatypes.registry import (
    DatatypeHandler,
    DatatypeRegistry,
    UnsupportedFacetException,
    ValueSpaceSubset,
    facet_data_value,
)

XSD_NS = "http://www.w3.org/2001/XMLSchema#"

_SUPPORTED_FACET_URIS = frozenset({
    XSD_NS + "minLength",
    XSD_NS + "maxLength",
    XSD_NS + "length",
    XSD_NS + "pattern",
})


class AnyURIValue:
    """An xsd:anyURI data value, distinct from plain strings."""

    __slots__ = ("_uri",)

    def __init__(self, uri: str) -> None:
        self._uri = uri

    @property
    def uri(self) -> str:
        return self._uri

    def __hash__(self) -> int:
        return hash(("anyURI", self._uri))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AnyURIValue):
            return self._uri == other._uri
        return False

    def __repr__(self) -> str:
        return f"AnyURIValue({self._uri!r})"


class AnyURIValueSpaceSubset(ValueSpaceSubset):
    def __init__(self, empty: bool = False):
        self._empty = empty

    def is_empty(self) -> bool:
        return self._empty

    def contains(self, value: Any) -> bool:
        return not self._empty

    def contains_data_value(self, value: Any) -> bool:
        return not self._empty and isinstance(value, AnyURIValue)

    def has_cardinality_at_least(self, number: int) -> bool:
        return number <= 0 or not self._empty

    def enumerate_data_values(self, data_values: list[Any]) -> None:
        if self._empty:
            return
        raise RuntimeError("The data range is infinite.")

    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        if isinstance(other, AnyURIValueSpaceSubset):
            return AnyURIValueSpaceSubset(self._empty or other._empty)
        return AnyURIValueSpaceSubset(empty=True)

    def complement(self) -> ValueSpaceSubset:
        return AnyURIValueSpaceSubset(empty=not self._empty)


class AnyURIFacetSubset(AnyURIValueSpaceSubset):
    """xsd:anyURI value space restricted by length and pattern facets."""

    def __init__(
        self,
        min_length: int = 0,
        max_length: int | None = None,
        patterns: tuple[re.Pattern[str], ...] = (),
        empty: bool = False,
    ) -> None:
        if max_length is not None and min_length > max_length:
            empty = True
        super().__init__(empty=empty)
        self._min_length = min_length
        self._max_length = max_length
        self._patterns = patterns

    def contains_data_value(self, value: Any) -> bool:
        if self._empty or not isinstance(value, AnyURIValue):
            return False
        text = value.uri
        if len(text) < self._min_length:
            return False
        if self._max_length is not None and len(text) > self._max_length:
            return False
        return all(pattern.fullmatch(text) is not None for pattern in self._patterns)


class AnyURIDatatypeHandler(DatatypeHandler):
    IRIS = (XSD_NS + "anyURI",)

    def get_datatype_iris(self) -> tuple[str, ...]:
        return self.IRIS

    def parse_literal(self, lexical_form: str, datatype_iri: str) -> Any:
        return lexical_form  # URI is just the string

    def parse_data_value(self, lexical_form: str, datatype_iri: str) -> Any:
        return AnyURIValue(lexical_form)

    def validate_datatype_restriction(self, datatype_restriction: Any) -> None:
        for index in range(datatype_restriction.number_of_facet_restrictions() - 1, -1, -1):
            facet_uri = datatype_restriction.facet_uri(index)
            if facet_uri not in _SUPPORTED_FACET_URIS:
                raise UnsupportedFacetException(
                    f"Facet with URI '{facet_uri}' is not supported on xsd:anyURI; "
                    "only xsd:minLength, xsd:maxLength, xsd:length, and "
                    "xsd:pattern are supported."
                )

    def create_value_space_subset(
        self, datatype_iri: str, facet_uris: Any, facet_values: Any
    ) -> AnyURIValueSpaceSubset:
        if not facet_uris:
            return AnyURIValueSpaceSubset()
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
        return AnyURIFacetSubset(
            min_length=min_length, max_length=max_length, patterns=tuple(patterns)
        )

    def entire_space(self, datatype_iri: str) -> AnyURIValueSpaceSubset:
        return AnyURIValueSpaceSubset()

    def empty_space(self, datatype_iri: str) -> AnyURIValueSpaceSubset:
        return AnyURIValueSpaceSubset(empty=True)


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


DatatypeRegistry.register(AnyURIDatatypeHandler())
