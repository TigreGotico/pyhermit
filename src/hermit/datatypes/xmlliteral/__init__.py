"""xml:literal datatype handler."""
from typing import Any

from hermit.datatypes.registry import DatatypeHandler, DatatypeRegistry, ValueSpaceSubset


class XMLLiteralValueSpaceSubset(ValueSpaceSubset):
    def __init__(self, empty: bool = False):
        self._empty = empty

    def is_empty(self) -> bool:
        return self._empty

    def contains(self, value: Any) -> bool:
        return not self._empty

    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        if isinstance(other, XMLLiteralValueSpaceSubset):
            return XMLLiteralValueSpaceSubset(self._empty or other._empty)
        return XMLLiteralValueSpaceSubset(empty=True)

    def complement(self) -> ValueSpaceSubset:
        return XMLLiteralValueSpaceSubset(empty=not self._empty)


class XMLLiteralDatatypeHandler(DatatypeHandler):
    IRIS = ("http://www.w3.org/1999/02/22-rdf-syntax-ns#XMLLiteral",)

    def get_datatype_iris(self) -> tuple[str, ...]:
        return self.IRIS

    def parse_literal(self, lexical_form: str, datatype_iri: str) -> Any:
        return lexical_form

    def create_value_space_subset(
        self, datatype_iri: str, facet_uris: Any, facet_values: Any
    ) -> XMLLiteralValueSpaceSubset:
        return XMLLiteralValueSpaceSubset()

    def entire_space(self, datatype_iri: str) -> XMLLiteralValueSpaceSubset:
        return XMLLiteralValueSpaceSubset()

    def empty_space(self, datatype_iri: str) -> XMLLiteralValueSpaceSubset:
        return XMLLiteralValueSpaceSubset(empty=True)

DatatypeRegistry.register(XMLLiteralDatatypeHandler())
