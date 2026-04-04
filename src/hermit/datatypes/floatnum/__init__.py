"""xsd:float datatype handler."""
from typing import Any

from hermit.datatypes.registry import (
    DatatypeHandler,
    DatatypeRegistry,
    MalformedLiteralException,
    ValueSpaceSubset,
)


class FloatValueSpaceSubset(ValueSpaceSubset):
    def __init__(self, empty: bool = False, entire: bool = False):
        self._empty = empty
        self._entire = entire

    def is_empty(self) -> bool:
        return self._empty

    def contains(self, value: Any) -> bool:
        return self._entire or not self._empty

    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        if isinstance(other, FloatValueSpaceSubset):
            if self._empty or other._empty:
                return FloatValueSpaceSubset(empty=True)
            if self._entire:
                return other
            if other._entire:
                return self
            return FloatValueSpaceSubset()
        return FloatValueSpaceSubset(empty=True)

    def complement(self) -> ValueSpaceSubset:
        if self._entire:
            return FloatValueSpaceSubset(empty=True)
        if self._empty:
            return FloatValueSpaceSubset(entire=True)
        return FloatValueSpaceSubset()


class FloatDatatypeHandler(DatatypeHandler):
    IRIS = ("http://www.w3.org/2001/XMLSchema#float",)

    def get_datatype_iris(self) -> tuple[str, ...]:
        return self.IRIS

    def parse_literal(self, lexical_form: str, datatype_iri: str) -> Any:
        try:
            return float(lexical_form)
        except ValueError:
            raise MalformedLiteralException(f"Invalid float: {lexical_form!r}") from None

    def create_value_space_subset(self, datatype_iri, facet_uris, facet_values):
        return FloatValueSpaceSubset(entire=True)

    def entire_space(self, datatype_iri):
        return FloatValueSpaceSubset(entire=True)

    def empty_space(self, datatype_iri):
        return FloatValueSpaceSubset(empty=True)

DatatypeRegistry.register(FloatDatatypeHandler())
