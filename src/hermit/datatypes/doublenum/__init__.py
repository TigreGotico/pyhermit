"""xsd:double datatype handler."""
from typing import Any

from hermit.datatypes.registry import (
    DatatypeHandler,
    DatatypeRegistry,
    MalformedLiteralException,
    ValueSpaceSubset,
)


class DoubleValueSpaceSubset(ValueSpaceSubset):
    def __init__(
        self,
        values: frozenset[float] | None = None,
        empty: bool = False,
        entire: bool = False,
    ):
        self._empty = empty or (values is not None and len(values) == 0)
        self._entire = entire and not self._empty
        self._values = values if values is not None else frozenset()

    def is_empty(self) -> bool:
        return self._empty

    def contains(self, value: Any) -> bool:
        if self._entire:
            return isinstance(value, float)
        return value in self._values

    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        if isinstance(other, DoubleValueSpaceSubset):
            if self._entire:
                return other
            if other._entire:
                return self
            return DoubleValueSpaceSubset(values=self._values & other._values)
        return DoubleValueSpaceSubset(empty=True)

    def complement(self) -> ValueSpaceSubset:
        if self._entire:
            return DoubleValueSpaceSubset(empty=True)
        if self._empty:
            return DoubleValueSpaceSubset(entire=True)
        return DoubleValueSpaceSubset(values=frozenset())  # simplified


class DoubleDatatypeHandler(DatatypeHandler):
    IRIS = ("http://www.w3.org/2001/XMLSchema#double",)

    def get_datatype_iris(self) -> tuple[str, ...]:
        return self.IRIS

    def parse_literal(self, lexical_form: str, datatype_iri: str) -> Any:
        try:
            return float(lexical_form)
        except ValueError:
            raise MalformedLiteralException(f"Invalid double: {lexical_form!r}") from None

    def create_value_space_subset(
        self, datatype_iri: str, facet_uris: tuple, facet_values: tuple
    ) -> ValueSpaceSubset:
        return DoubleValueSpaceSubset(entire=True)

    def entire_space(self, datatype_iri: str) -> ValueSpaceSubset:
        return DoubleValueSpaceSubset(entire=True)

    def empty_space(self, datatype_iri: str) -> ValueSpaceSubset:
        return DoubleValueSpaceSubset(empty=True)

DatatypeRegistry.register(DoubleDatatypeHandler())
