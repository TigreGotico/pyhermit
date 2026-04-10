"""xsd:dateTime datatype handler."""
from datetime import datetime
from typing import Any

from hermit.datatypes.registry import (
    DatatypeHandler,
    DatatypeRegistry,
    MalformedLiteralException,
    ValueSpaceSubset,
)


class DateTimeValueSpaceSubset(ValueSpaceSubset):
    def __init__(self, empty: bool = False, entire: bool = False):
        self._empty = empty
        self._entire = entire

    def is_empty(self) -> bool:
        return self._empty

    def contains(self, value: Any) -> bool:
        return self._entire

    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        if isinstance(other, DateTimeValueSpaceSubset):
            if self._empty or other._empty:
                return DateTimeValueSpaceSubset(empty=True)
            return DateTimeValueSpaceSubset(entire=True)
        return DateTimeValueSpaceSubset(empty=True)

    def complement(self) -> ValueSpaceSubset:
        return DateTimeValueSpaceSubset(empty=not self._empty)


class DateTimeDatatypeHandler(DatatypeHandler):
    IRIS = (
        "http://www.w3.org/2001/XMLSchema#dateTime",
        "http://www.w3.org/2001/XMLSchema#date",
        "http://www.w3.org/2001/XMLSchema#time",
        "http://www.w3.org/2001/XMLSchema#duration",
        "http://www.w3.org/2001/XMLSchema#gYear",
        "http://www.w3.org/2001/XMLSchema#gMonth",
        "http://www.w3.org/2001/XMLSchema#gDay",
        "http://www.w3.org/2001/XMLSchema#gYearMonth",
        "http://www.w3.org/2001/XMLSchema#gMonthDay",
    )

    def get_datatype_iris(self) -> tuple[str, ...]:
        return self.IRIS

    def parse_literal(self, lexical_form: str, datatype_iri: str) -> Any:
        try:
            # ISO 8601 format
            return datetime.fromisoformat(lexical_form.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            raise MalformedLiteralException(f"Invalid dateTime: {lexical_form!r}") from None

    def create_value_space_subset(self, datatype_iri: str, facet_uris: Any, facet_values: Any) -> DateTimeValueSpaceSubset:
        return DateTimeValueSpaceSubset(entire=True)

    def entire_space(self, datatype_iri: str) -> DateTimeValueSpaceSubset:
        return DateTimeValueSpaceSubset(entire=True)

    def empty_space(self, datatype_iri: str) -> DateTimeValueSpaceSubset:
        return DateTimeValueSpaceSubset(empty=True)

DatatypeRegistry.register(DateTimeDatatypeHandler())
