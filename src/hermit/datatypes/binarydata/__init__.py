"""xsd:base64Binary and xsd:hexBinary datatype handlers."""
from __future__ import annotations

import base64
import binascii
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
XSD_HEX_BINARY = XSD_NS + "hexBinary"
XSD_BASE_64_BINARY = XSD_NS + "base64Binary"

_SUPPORTED_FACET_URIS = frozenset({
    XSD_NS + "minLength",
    XSD_NS + "maxLength",
    XSD_NS + "length",
})

_HEX_PATTERN = re.compile(r"(?:[0-9a-fA-F]{2})*")


class BinaryDataValue:
    """A binary data value carrying its binary datatype kind."""

    __slots__ = ("_datatype_iri", "_data")

    def __init__(self, datatype_iri: str, data: bytes) -> None:
        self._datatype_iri = datatype_iri
        self._data = data

    @property
    def datatype_iri(self) -> str:
        return self._datatype_iri

    @property
    def data(self) -> bytes:
        return self._data

    def __hash__(self) -> int:
        return hash((self._datatype_iri, self._data))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BinaryDataValue):
            return self._datatype_iri == other._datatype_iri and self._data == other._data
        return False

    def __repr__(self) -> str:
        return f"BinaryDataValue({self._datatype_iri!r}, {self._data!r})"


class BinaryDataValueSpaceSubset(ValueSpaceSubset):
    def __init__(self, empty: bool = False):
        self._empty = empty

    def is_empty(self) -> bool:
        return self._empty

    def contains(self, value: Any) -> bool:
        return not self._empty

    def contains_data_value(self, value: Any) -> bool:
        return not self._empty and isinstance(value, BinaryDataValue)

    def has_cardinality_at_least(self, number: int) -> bool:
        return number <= 0 or not self._empty

    def enumerate_data_values(self, data_values: list[Any]) -> None:
        if self._empty:
            return
        raise RuntimeError("The data range is infinite.")

    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        if isinstance(other, BinaryDataValueSpaceSubset):
            return BinaryDataValueSpaceSubset(self._empty or other._empty)
        return BinaryDataValueSpaceSubset(empty=True)

    def complement(self) -> ValueSpaceSubset:
        return BinaryDataValueSpaceSubset(empty=not self._empty)


class BinaryDataFacetSubset(BinaryDataValueSpaceSubset):
    """A binary value space restricted to one binary kind and length bounds."""

    def __init__(
        self,
        datatype_iri: str,
        min_length: int = 0,
        max_length: int | None = None,
        empty: bool = False,
    ) -> None:
        if max_length is not None and min_length > max_length:
            empty = True
        super().__init__(empty=empty)
        self._datatype_iri = datatype_iri
        self._min_length = min_length
        self._max_length = max_length

    def contains_data_value(self, value: Any) -> bool:
        if self._empty or not isinstance(value, BinaryDataValue):
            return False
        if value.datatype_iri != self._datatype_iri:
            return False
        if len(value.data) < self._min_length:
            return False
        return self._max_length is None or len(value.data) <= self._max_length

    def has_cardinality_at_least(self, number: int) -> bool:
        if number <= 0:
            return True
        if self._empty:
            return False
        if self._max_length is None:
            return True
        # Number of octet sequences with length in [min_length, max_length].
        count = 0
        for length in range(self._min_length, self._max_length + 1):
            count += 256 ** length
            if count >= number:
                return True
        return count >= number


class BinaryDataDatatypeHandler(DatatypeHandler):
    IRIS = (
        XSD_BASE_64_BINARY,
        XSD_HEX_BINARY,
    )

    def get_datatype_iris(self) -> tuple[str, ...]:
        return self.IRIS

    def parse_literal(self, lexical_form: str, datatype_iri: str) -> Any:
        if datatype_iri.endswith("base64Binary"):
            try:
                return base64.b64decode(lexical_form)
            except Exception:
                raise MalformedLiteralException(f"Invalid base64Binary: {lexical_form!r}") from None
        elif datatype_iri.endswith("hexBinary"):
            try:
                return bytes.fromhex(lexical_form)
            except ValueError:
                raise MalformedLiteralException(f"Invalid hexBinary: {lexical_form!r}") from None
        return lexical_form

    def parse_data_value(self, lexical_form: str, datatype_iri: str) -> Any:
        if datatype_iri == XSD_HEX_BINARY:
            text = lexical_form.strip()
            if not _HEX_PATTERN.fullmatch(text):
                raise MalformedLiteralException(f"Invalid hexBinary: {lexical_form!r}")
            return BinaryDataValue(XSD_HEX_BINARY, bytes.fromhex(text))
        try:
            data = base64.b64decode(lexical_form, validate=False)
        except (binascii.Error, ValueError):
            raise MalformedLiteralException(
                f"Invalid base64Binary: {lexical_form!r}"
            ) from None
        return BinaryDataValue(XSD_BASE_64_BINARY, data)

    def validate_datatype_restriction(self, datatype_restriction: Any) -> None:
        for index in range(datatype_restriction.number_of_facet_restrictions() - 1, -1, -1):
            facet_uri = datatype_restriction.facet_uri(index)
            if facet_uri not in _SUPPORTED_FACET_URIS:
                raise UnsupportedFacetException(
                    f"Facet with URI '{facet_uri}' is not supported on binary "
                    "datatypes; only xsd:minLength, xsd:maxLength, and "
                    "xsd:length are supported."
                )

    def create_value_space_subset(
        self, datatype_iri: str, facet_uris: Any, facet_values: Any
    ) -> BinaryDataValueSpaceSubset:
        min_length = 0
        max_length: int | None = None
        if facet_uris:
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
        return BinaryDataFacetSubset(
            datatype_iri, min_length=min_length, max_length=max_length
        )

    def entire_space(self, datatype_iri: str) -> BinaryDataValueSpaceSubset:
        return BinaryDataValueSpaceSubset()

    def empty_space(self, datatype_iri: str) -> BinaryDataValueSpaceSubset:
        return BinaryDataValueSpaceSubset(empty=True)

    def is_disjoint_with_datatype(self, datatype_iri1: str, datatype_iri2: str) -> bool:
        return datatype_iri1 != datatype_iri2


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


DatatypeRegistry.register(BinaryDataDatatypeHandler())
