"""xsd:anyURI datatype handler."""
from typing import Any

from hermit.datatypes.registry import DatatypeHandler, DatatypeRegistry, ValueSpaceSubset


class AnyURIValueSpaceSubset(ValueSpaceSubset):
    def __init__(self, empty: bool = False):
        self._empty = empty

    def is_empty(self) -> bool:
        return self._empty

    def contains(self, value: Any) -> bool:
        return not self._empty

    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        if isinstance(other, AnyURIValueSpaceSubset):
            return AnyURIValueSpaceSubset(self._empty or other._empty)
        return AnyURIValueSpaceSubset(empty=True)

    def complement(self) -> ValueSpaceSubset:
        return AnyURIValueSpaceSubset(empty=not self._empty)


class AnyURIDatatypeHandler(DatatypeHandler):
    IRIS = ("http://www.w3.org/2001/XMLSchema#anyURI",)

    def get_datatype_iris(self) -> tuple[str, ...]:
        return self.IRIS

    def parse_literal(self, lexical_form: str, datatype_iri: str) -> Any:
        return lexical_form  # URI is just the string

    def create_value_space_subset(self, datatype_iri, facet_uris, facet_values):
        return AnyURIValueSpaceSubset()

    def entire_space(self, datatype_iri):
        return AnyURIValueSpaceSubset()

    def empty_space(self, datatype_iri):
        return AnyURIValueSpaceSubset(empty=True)

DatatypeRegistry.register(AnyURIDatatypeHandler())
