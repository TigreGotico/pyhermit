"""xsd:boolean datatype handler."""
from typing import Any

from hermit.datatypes.registry import (
    DatatypeHandler,
    DatatypeRegistry,
    MalformedLiteralException,
    UnsupportedFacetException,
    ValueSpaceSubset,
)


class BooleanValueSpaceSubset(ValueSpaceSubset):
    def __init__(self, values: frozenset[bool] = frozenset({True, False})):
        self._values = values

    def is_empty(self) -> bool:
        return len(self._values) == 0

    def contains(self, value: Any) -> bool:
        return value in self._values

    def contains_data_value(self, value: Any) -> bool:
        return isinstance(value, bool) and value in self._values

    def has_cardinality_at_least(self, number: int) -> bool:
        return number <= len(self._values)

    def enumerate_data_values(self, data_values: list[Any]) -> None:
        if False in self._values:
            data_values.append(False)
        if True in self._values:
            data_values.append(True)

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

    def parse_data_value(self, lexical_form: str, datatype_iri: str) -> Any:
        text = lexical_form.strip()
        if text.lower() == "true" or text == "1":
            return True
        if text.lower() == "false" or text == "0":
            return False
        raise MalformedLiteralException(f"Invalid boolean: {lexical_form!r}")

    def validate_datatype_restriction(self, datatype_restriction: Any) -> None:
        if datatype_restriction.number_of_facet_restrictions() > 0:
            raise UnsupportedFacetException(
                "The xsd:boolean datatype does not provide any facets."
            )

    def create_value_space_subset(
        self, datatype_iri: str, facet_uris: Any, facet_values: Any
    ) -> BooleanValueSpaceSubset:
        return BooleanValueSpaceSubset()

    def conjoin_with_dr(
        self, value_space_subset: ValueSpaceSubset, datatype_restriction: Any
    ) -> ValueSpaceSubset:
        return value_space_subset

    def conjoin_with_dr_negation(
        self, value_space_subset: ValueSpaceSubset, datatype_restriction: Any
    ) -> ValueSpaceSubset:
        return BooleanValueSpaceSubset(frozenset())

    def entire_space(self, datatype_iri: str) -> BooleanValueSpaceSubset:
        return BooleanValueSpaceSubset()

    def empty_space(self, datatype_iri: str) -> BooleanValueSpaceSubset:
        return BooleanValueSpaceSubset(frozenset())

DatatypeRegistry.register(BooleanDatatypeHandler())
