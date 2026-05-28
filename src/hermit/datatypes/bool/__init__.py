"""xsd:boolean datatype handler."""
from typing import Any

from hermit.datatypes.registry import (
    DatatypeHandler,
    DatatypeRegistry,
    MalformedLiteralException,
    ValueSpaceSubset,
)


class BooleanValueSpaceSubset(ValueSpaceSubset):
    def __init__(self, values: frozenset[bool] = frozenset({True, False})):
        self._values = values

    def is_empty(self) -> bool:
        return len(self._values) == 0

    def contains(self, value: Any) -> bool:
        return value in self._values

    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        if isinstance(other, BooleanValueSpaceSubset):
            return BooleanValueSpaceSubset(self._values & other._values)
        return BooleanValueSpaceSubset(frozenset())

    def complement(self) -> ValueSpaceSubset:
        return BooleanValueSpaceSubset(frozenset({True, False}) - self._values)


class BooleanDatatypeHandler(DatatypeHandler):
    IRIS = ("http://www.w3.org/2001/XMLSchema#boolean",)

    def get_datatype_iris(self) -> tuple[str, ...]:
        return self.IRIS

    def parse_literal(self, lexical_form: str, datatype_iri: str) -> Any:
        if lexical_form in ("true", "1"):
            return True
        if lexical_form in ("false", "0"):
            return False
        raise MalformedLiteralException(f"Invalid boolean: {lexical_form!r}")

    def create_value_space_subset(
        self, datatype_iri: str, facet_uris: Any, facet_values: Any
    ) -> BooleanValueSpaceSubset:
        return BooleanValueSpaceSubset()

    def entire_space(self, datatype_iri: str) -> BooleanValueSpaceSubset:
        return BooleanValueSpaceSubset()

    def empty_space(self, datatype_iri: str) -> BooleanValueSpaceSubset:
        return BooleanValueSpaceSubset(frozenset())

DatatypeRegistry.register(BooleanDatatypeHandler())
