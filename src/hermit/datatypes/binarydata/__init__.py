"""xsd:base64Binary and xsd:hexBinary datatype handlers."""
import base64
from typing import Any

from hermit.datatypes.registry import (
    DatatypeHandler,
    DatatypeRegistry,
    MalformedLiteralException,
    ValueSpaceSubset,
)


class BinaryDataValueSpaceSubset(ValueSpaceSubset):
    def __init__(self, empty: bool = False):
        self._empty = empty

    def is_empty(self) -> bool:
        return self._empty

    def contains(self, value: Any) -> bool:
        return not self._empty

    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        if isinstance(other, BinaryDataValueSpaceSubset):
            return BinaryDataValueSpaceSubset(self._empty or other._empty)
        return BinaryDataValueSpaceSubset(empty=True)

    def complement(self) -> ValueSpaceSubset:
        return BinaryDataValueSpaceSubset(empty=not self._empty)


class BinaryDataDatatypeHandler(DatatypeHandler):
    IRIS = (
        "http://www.w3.org/2001/XMLSchema#base64Binary",
        "http://www.w3.org/2001/XMLSchema#hexBinary",
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

    def create_value_space_subset(
        self, datatype_iri: str, facet_uris: Any, facet_values: Any
    ) -> BinaryDataValueSpaceSubset:
        return BinaryDataValueSpaceSubset()

    def entire_space(self, datatype_iri: str) -> BinaryDataValueSpaceSubset:
        return BinaryDataValueSpaceSubset()

    def empty_space(self, datatype_iri: str) -> BinaryDataValueSpaceSubset:
        return BinaryDataValueSpaceSubset(empty=True)

DatatypeRegistry.register(BinaryDataDatatypeHandler())
