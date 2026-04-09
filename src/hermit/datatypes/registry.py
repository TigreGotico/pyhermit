"""
Datatype handler base class and registry.

Each OWL 2 datatype (xsd:string, xsd:decimal, xsd:integer, xsd:float,
xsd:double, xsd:boolean, xsd:anyURI, xsd:dateTime, xml:literal,
rdf:PlainLiteral, xsd:base64Binary, xsd:hexBinary) is handled by a
``DatatypeHandler`` subclass registered with the ``DatatypeRegistry``.
"""

from __future__ import annotations

__all__ = [
    "DatatypeHandler",
    "DatatypeRegistry",
    "MalformedLiteralException",
    "UnsupportedDatatypeException",
    "UnsupportedFacetException",
    "ValueSpaceSubset",
]

from abc import ABC, abstractmethod
from typing import Any


class MalformedLiteralException(Exception):
    """Raised when a lexical form cannot be parsed for its datatype."""
    pass


class UnsupportedDatatypeException(Exception):
    """Raised when a datatype URI is not recognised."""
    pass


class UnsupportedFacetException(Exception):
    """Raised when a facet restriction is not supported by the datatype."""
    pass


class ValueSpaceSubset(ABC):
    """
    Abstract base for a subset of a datatype value space.

    Mirrors the Java ``ValueSpaceSubset`` interface.  Subsets support
    intersection, complement, emptiness check, and conformance testing.
    """

    @abstractmethod
    def is_empty(self) -> bool:
        """Return ``True`` if this subset contains no values."""
        ...

    @abstractmethod
    def contains(self, value: Any) -> bool:
        """Return ``True`` if the given parsed value is in this subset."""
        ...

    @abstractmethod
    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        """Return the intersection of this subset with another."""
        ...

    @abstractmethod
    def complement(self) -> ValueSpaceSubset:
        """Return the complement of this subset within the datatype's value space."""
        ...

    def has_cardinality_at_least(self, number: int) -> bool:
        """Return True if this subset has at least *number* elements.

        For infinite value spaces, returns True if number >= 1.
        For finite value spaces, would need to count elements.
        """
        if number <= 0:
            return True
        # For our implementation, assume non-empty finite spaces have "enough" values
        return not self.is_empty()

    def contains_data_value(self, value: Any) -> bool:
        """Check if a data value is in this subset.

        Alias for contains() for compatibility.
        """
        return self.contains(value)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


class DatatypeHandler(ABC):
    """
    Abstract base for datatype handlers.

    Each concrete handler is responsible for a set of datatype IRIs
    (e.g., ``xsd:decimal``, ``xsd:double``) and provides:
    - Lexical parsing (``str`` → typed value)
    - Value space subset construction from facet restrictions
    - Subset operations (intersection, complement, emptiness)
    """

    @abstractmethod
    def get_datatype_iris(self) -> tuple[str, ...]:
        """Return the datatype IRIs this handler is responsible for."""
        ...

    @abstractmethod
    def parse_literal(self, lexical_form: str, datatype_iri: str) -> Any:
        """
        Parse a lexical form into a typed value.

        Raises ``MalformedLiteralException`` if the lexical form is invalid.
        """
        ...

    @abstractmethod
    def create_value_space_subset(
        self,
        datatype_iri: str,
        facet_uris: tuple[str, ...],
        facet_values: tuple[Any, ...],
    ) -> ValueSpaceSubset:
        """
        Create a value space subset from facet restrictions.

        ``facet_uris`` and ``facet_values`` are parallel tuples describing
        facet restrictions (e.g., minInclusive, maxLength, pattern).
        """
        ...

    @abstractmethod
    def entire_space(self, datatype_iri: str) -> ValueSpaceSubset:
        """Return a subset representing the entire value space."""
        ...

    @abstractmethod
    def empty_space(self, datatype_iri: str) -> ValueSpaceSubset:
        """Return a subset representing the empty set."""
        ...


class DatatypeRegistry:
    """
    Central registry of datatype handlers.

    Handlers are registered at module load time (see the ``__init__.py``
    files in ``datatypes/`` sub-packages).  The registry dispatches parsing
    and subset construction to the appropriate handler.
    """

    _handlers_by_iri: dict[str, DatatypeHandler] = {}
    _handlers: list[DatatypeHandler] = []

    @classmethod
    def register(cls, handler: DatatypeHandler) -> None:
        """Register a datatype handler."""
        cls._handlers.append(handler)
        for iri in handler.get_datatype_iris():
            cls._handlers_by_iri[iri] = handler

    @classmethod
    def get_handler(cls, datatype_iri: str) -> DatatypeHandler:
        """Get the handler for a datatype IRI."""
        handler = cls._handlers_by_iri.get(datatype_iri)
        if handler is None:
            raise UnsupportedDatatypeException(f"Unsupported datatype: {datatype_iri}")
        return handler

    @classmethod
    def has_handler(cls, datatype_iri: str) -> bool:
        """Check if a handler exists for the given datatype IRI."""
        return datatype_iri in cls._handlers_by_iri

    @classmethod
    def parse_literal(cls, lexical_form: str, datatype_iri: str) -> Any:
        """Parse a lexical form using the registered handler."""
        handler = cls.get_handler(datatype_iri)
        return handler.parse_literal(lexical_form, datatype_iri)

    @classmethod
    def create_value_space_subset(
        cls,
        datatype_iri: str,
        facet_uris: tuple[str, ...],
        facet_values: tuple[Any, ...],
    ) -> ValueSpaceSubset:
        """Create a value space subset using the registered handler."""
        handler = cls.get_handler(datatype_iri)
        return handler.create_value_space_subset(datatype_iri, facet_uris, facet_values)

    @classmethod
    def entire_space(cls, datatype_iri: str) -> ValueSpaceSubset:
        handler = cls.get_handler(datatype_iri)
        return handler.entire_space(datatype_iri)

    @classmethod
    def empty_space(cls, datatype_iri: str) -> ValueSpaceSubset:
        handler = cls.get_handler(datatype_iri)
        return handler.empty_space(datatype_iri)

    @classmethod
    def supported_iris(cls) -> tuple[str, ...]:
        """Return all datatype IRIs currently supported."""
        return tuple(cls._handlers_by_iri.keys())
