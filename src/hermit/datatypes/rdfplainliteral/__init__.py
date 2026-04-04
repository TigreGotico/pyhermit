"""rdf:PlainLiteral datatype handler."""
from typing import Any

from hermit.datatypes.registry import DatatypeHandler, DatatypeRegistry, ValueSpaceSubset


class RDFPlainLiteralValueSpaceSubset(ValueSpaceSubset):
    def __init__(self, empty: bool = False):
        self._empty = empty

    def is_empty(self) -> bool:
        return self._empty

    def contains(self, value: Any) -> bool:
        return not self._empty

    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        if isinstance(other, RDFPlainLiteralValueSpaceSubset):
            return RDFPlainLiteralValueSpaceSubset(self._empty or other._empty)
        return RDFPlainLiteralValueSpaceSubset(empty=True)

    def complement(self) -> ValueSpaceSubset:
        return RDFPlainLiteralValueSpaceSubset(empty=not self._empty)


class RDFPlainLiteralDatatypeHandler(DatatypeHandler):
    IRIS = ("http://www.w3.org/1999/02/22-rdf-syntax-ns#PlainLiteral",)

    def get_datatype_iris(self) -> tuple[str, ...]:
        return self.IRIS

    def parse_literal(self, lexical_form: str, datatype_iri: str) -> Any:
        return lexical_form

    def create_value_space_subset(self, datatype_iri, facet_uris, facet_values):
        return RDFPlainLiteralValueSpaceSubset()

    def entire_space(self, datatype_iri):
        return RDFPlainLiteralValueSpaceSubset()

    def empty_space(self, datatype_iri):
        return RDFPlainLiteralValueSpaceSubset(empty=True)

DatatypeRegistry.register(RDFPlainLiteralDatatypeHandler())
