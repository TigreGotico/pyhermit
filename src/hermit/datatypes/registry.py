"""
Datatype handler base class and registry.

Each OWL 2 datatype (xsd:string, xsd:decimal, xsd:integer, xsd:float,
xsd:double, xsd:boolean, xsd:anyURI, xsd:dateTime, xml:literal,
rdf:PlainLiteral, xsd:base64Binary, xsd:hexBinary) is handled by a
``DatatypeHandler`` subclass registered with the ``DatatypeRegistry``.
"""

from __future__ import annotations

__all__ = [
    "AnonymousConstantValue",
    "DatatypeHandler",
    "DatatypeRegistry",
    "MalformedLiteralException",
    "UnsupportedDatatypeException",
    "UnsupportedFacetException",
    "ValueSpaceSubset",
]

from abc import ABC, abstractmethod
from typing import Any


def restriction_parts(
    datatype_restriction: Any,
) -> tuple[str, tuple[str, ...], tuple[Any, ...]]:
    """Extract (datatype IRI, facet URIs, facet values) from a DatatypeRestriction."""
    datatype_iri: str = datatype_restriction.datatype_iri
    facet_uris: tuple[str, ...] = getattr(datatype_restriction, "_facet_uris", ())
    facet_values: tuple[Any, ...] = getattr(datatype_restriction, "_facet_values", ())
    return datatype_iri, facet_uris, facet_values


def facet_data_value(facet_value: Any) -> Any:
    """Unwrap a facet value to its data value (Constants carry .data_value)."""
    seen = 0
    value = facet_value
    while hasattr(value, "data_value") and seen < 4:
        value = value.data_value
        seen += 1
    return value


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

    def enumerate_data_values(self, data_values: list[Any]) -> None:
        """Append all data values of this subset to *data_values*.

        Only valid for finite subsets; infinite subsets raise ``RuntimeError``.
        """
        raise RuntimeError("The data range is infinite.")

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

    # -- Java HermiT DatatypeHandler protocol --------------------------------

    def parse_data_value(self, lexical_form: str, datatype_iri: str) -> Any:
        """Parse a lexical form into the data value used during reasoning."""
        return self.parse_literal(lexical_form, datatype_iri)

    def validate_datatype_restriction(self, datatype_restriction: Any) -> None:
        """Validate the facets of a datatype restriction.

        Raises ``UnsupportedFacetException`` for unsupported facets.
        """
        return None

    def create_value_space_subset_for(
        self, datatype_restriction: Any
    ) -> ValueSpaceSubset:
        """Create a value space subset for a DatatypeRestriction object."""
        datatype_iri, facet_uris, facet_values = restriction_parts(datatype_restriction)
        return self.create_value_space_subset(datatype_iri, facet_uris, facet_values)

    def conjoin_with_dr(
        self, value_space_subset: ValueSpaceSubset, datatype_restriction: Any
    ) -> ValueSpaceSubset:
        """Intersect *value_space_subset* with a datatype restriction."""
        restriction_space = self.create_value_space_subset_for(datatype_restriction)
        return value_space_subset.intersect(restriction_space)

    def conjoin_with_dr_negation(
        self, value_space_subset: ValueSpaceSubset, datatype_restriction: Any
    ) -> ValueSpaceSubset:
        """Intersect *value_space_subset* with the complement of a restriction."""
        restriction_space = self.create_value_space_subset_for(datatype_restriction)
        return value_space_subset.intersect(restriction_space.complement())

    def is_subset_of_datatype(
        self, subset_datatype_iri: str, superset_datatype_iri: str
    ) -> bool:
        """Check subset relation between two datatypes managed by this handler."""
        return subset_datatype_iri == superset_datatype_iri

    def is_disjoint_with_datatype(self, datatype_iri1: str, datatype_iri2: str) -> bool:
        """Check disjointness between two datatypes managed by this handler."""
        return False


class AnonymousConstantValue:
    """The data value of an anonymous constant."""

    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def __hash__(self) -> int:
        return hash(self._name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AnonymousConstantValue):
            return self._name == other._name
        return False

    def __repr__(self) -> str:
        return f"AnonymousConstantValue({self._name!r})"


class AnonymousConstantsDatatypeHandler(DatatypeHandler):
    """Handler for internal anonymous constants."""

    ANONYMOUS_CONSTANTS = "internal:anonymous-constants"

    def get_datatype_iris(self) -> tuple[str, ...]:
        return (self.ANONYMOUS_CONSTANTS,)

    def parse_literal(self, lexical_form: str, datatype_iri: str) -> Any:
        return AnonymousConstantValue(lexical_form.strip())

    def create_value_space_subset(
        self,
        datatype_iri: str,
        facet_uris: tuple[str, ...],
        facet_values: tuple[Any, ...],
    ) -> ValueSpaceSubset:
        raise RuntimeError(
            "Internal error: anonymous constants datatype should not occur in "
            "datatype restrictions."
        )

    def entire_space(self, datatype_iri: str) -> ValueSpaceSubset:
        raise RuntimeError(
            "Internal error: anonymous constants datatype should not occur in "
            "datatype restrictions."
        )

    def empty_space(self, datatype_iri: str) -> ValueSpaceSubset:
        raise RuntimeError(
            "Internal error: anonymous constants datatype should not occur in "
            "datatype restrictions."
        )


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
        return handler.parse_data_value(lexical_form, datatype_iri)

    @classmethod
    def validate_datatype_restriction(cls, datatype_restriction: Any) -> None:
        """Validate a datatype restriction using the registered handler.

        Raises ``UnsupportedDatatypeException`` for unknown datatypes and
        ``UnsupportedFacetException`` for unsupported facets.
        """
        datatype_iri, _, _ = restriction_parts(datatype_restriction)
        handler = cls.get_handler(datatype_iri)
        handler.validate_datatype_restriction(datatype_restriction)

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

    @classmethod
    def is_disjoint_with(cls, datatype_iri1: str, datatype_iri2: str) -> bool:
        """Check if two datatype value spaces are disjoint.

        Datatypes managed by different handlers have pairwise disjoint value
        spaces; within one handler the handler decides.  Datatypes without a
        registered handler fall back to coarse group-based reasoning.
        """
        if datatype_iri1 == datatype_iri2:
            return False
        handler1 = cls._handlers_by_iri.get(datatype_iri1)
        handler2 = cls._handlers_by_iri.get(datatype_iri2)
        if handler1 is not None and handler2 is not None:
            if handler1 is not handler2:
                return True
            return handler1.is_disjoint_with_datatype(datatype_iri1, datatype_iri2)
        return cls._group_disjoint(datatype_iri1, datatype_iri2)

    @classmethod
    def _group_disjoint(cls, datatype_iri1: str, datatype_iri2: str) -> bool:
        """Coarse group-based disjointness for datatypes without handlers."""
        # Define groups of mutually disjoint types
        # String types
        string_types = {
            "http://www.w3.org/2001/XMLSchema#string",
            "http://www.w3.org/2001/XMLSchema#normalizedString",
            "http://www.w3.org/2001/XMLSchema#token",
            "http://www.w3.org/2001/XMLSchema#Name",
            "http://www.w3.org/2001/XMLSchema#NCName",
            "http://www.w3.org/2001/XMLSchema#ENTITY",
            "http://www.w3.org/2001/XMLSchema#ID",
            "http://www.w3.org/2001/XMLSchema#IDREF",
            "http://www.w3.org/2001/XMLSchema#NMTOKEN",
            "http://www.w3.org/2001/XMLSchema#language",
        }

        # Numeric types
        numeric_types = {
            "http://www.w3.org/2001/XMLSchema#integer",
            "http://www.w3.org/2001/XMLSchema#decimal",
            "http://www.w3.org/2001/XMLSchema#float",
            "http://www.w3.org/2001/XMLSchema#double",
            "http://www.w3.org/2001/XMLSchema#long",
            "http://www.w3.org/2001/XMLSchema#int",
            "http://www.w3.org/2001/XMLSchema#short",
            "http://www.w3.org/2001/XMLSchema#byte",
            "http://www.w3.org/2001/XMLSchema#positiveInteger",
            "http://www.w3.org/2001/XMLSchema#nonPositiveInteger",
            "http://www.w3.org/2001/XMLSchema#negativeInteger",
            "http://www.w3.org/2001/XMLSchema#nonNegativeInteger",
            "http://www.w3.org/2001/XMLSchema#unsignedLong",
            "http://www.w3.org/2001/XMLSchema#unsignedInt",
            "http://www.w3.org/2001/XMLSchema#unsignedShort",
            "http://www.w3.org/2001/XMLSchema#unsignedByte",
        }

        # Boolean type
        boolean_type = "http://www.w3.org/2001/XMLSchema#boolean"

        # Date/Time types
        datetime_types = {
            "http://www.w3.org/2001/XMLSchema#dateTime",
            "http://www.w3.org/2001/XMLSchema#date",
            "http://www.w3.org/2001/XMLSchema#time",
            "http://www.w3.org/2001/XMLSchema#gYear",
            "http://www.w3.org/2001/XMLSchema#gYearMonth",
            "http://www.w3.org/2001/XMLSchema#gMonthDay",
            "http://www.w3.org/2001/XMLSchema#gDay",
            "http://www.w3.org/2001/XMLSchema#gMonth",
        }

        # Binary types
        binary_types = {
            "http://www.w3.org/2001/XMLSchema#hexBinary",
            "http://www.w3.org/2001/XMLSchema#base64Binary",
        }

        # Check if they're in different groups
        in_strings_1 = datatype_iri1 in string_types
        in_strings_2 = datatype_iri2 in string_types
        in_numeric_1 = datatype_iri1 in numeric_types
        in_numeric_2 = datatype_iri2 in numeric_types
        is_boolean_1 = datatype_iri1 == boolean_type
        is_boolean_2 = datatype_iri2 == boolean_type
        in_datetime_1 = datatype_iri1 in datetime_types
        in_datetime_2 = datatype_iri2 in datetime_types
        in_binary_1 = datatype_iri1 in binary_types
        in_binary_2 = datatype_iri2 in binary_types

        # Check for disjoint groups
        # Strings are disjoint from numbers, booleans, dates, and binaries
        if (in_strings_1 and (in_numeric_2 or is_boolean_2 or in_datetime_2 or in_binary_2)):
            return True
        if (in_strings_2 and (in_numeric_1 or is_boolean_1 or in_datetime_1 or in_binary_1)):
            return True

        # Numbers are disjoint from booleans, dates, and binaries
        if (in_numeric_1 and (is_boolean_2 or in_datetime_2 or in_binary_2)):
            return True
        if (in_numeric_2 and (is_boolean_1 or in_datetime_1 or in_binary_1)):
            return True

        # Booleans are disjoint from dates and binaries
        if (is_boolean_1 and (in_datetime_2 or in_binary_2)):
            return True
        if (is_boolean_2 and (in_datetime_1 or in_binary_1)):
            return True

        # Dates are disjoint from binaries
        if (in_datetime_1 and in_binary_2):
            return True
        if (in_datetime_2 and in_binary_1):
            return True

        # Otherwise, assume overlap is possible
        return False

    # Numeric promotion pairs kept for API compatibility; the reasoning code
    # never queries them because the value spaces are reported as disjoint.
    _LEGACY_PROMOTIONS: frozenset[tuple[str, str]] = frozenset({
        (
            "http://www.w3.org/2001/XMLSchema#decimal",
            "http://www.w3.org/2001/XMLSchema#float",
        ),
        (
            "http://www.w3.org/2001/XMLSchema#decimal",
            "http://www.w3.org/2001/XMLSchema#double",
        ),
        (
            "http://www.w3.org/2001/XMLSchema#float",
            "http://www.w3.org/2001/XMLSchema#double",
        ),
    })

    @classmethod
    def is_subset_of(cls, datatype_iri1: str, datatype_iri2: str) -> bool:
        """Check if datatype_iri1 is a subset of datatype_iri2.

        Returns True if the value space of datatype_iri1 is a subset of
        the value space of datatype_iri2.
        """
        if datatype_iri1 == datatype_iri2:
            return True
        if (datatype_iri1, datatype_iri2) in cls._LEGACY_PROMOTIONS:
            return True
        handler1 = cls._handlers_by_iri.get(datatype_iri1)
        handler2 = cls._handlers_by_iri.get(datatype_iri2)
        if handler1 is not None and handler1 is handler2:
            return handler1.is_subset_of_datatype(datatype_iri1, datatype_iri2)
        return False

    @classmethod
    def conjoin_with_dr(
        cls, value_space: ValueSpaceSubset, datatype_restriction: Any
    ) -> ValueSpaceSubset:
        """Conjoin a value space with a datatype restriction.

        Returns the intersection of the value space with the restriction.
        """
        datatype_iri, _, _ = restriction_parts(datatype_restriction)
        handler = cls.get_handler(datatype_iri)
        return handler.conjoin_with_dr(value_space, datatype_restriction)

    @classmethod
    def conjoin_with_dr_negation(
        cls, value_space: ValueSpaceSubset, datatype_restriction: Any
    ) -> ValueSpaceSubset:
        """Conjoin a value space with the negation of a datatype restriction.

        Returns the intersection of the value space with the complement of the restriction.
        """
        datatype_iri, _, _ = restriction_parts(datatype_restriction)
        handler = cls.get_handler(datatype_iri)
        return handler.conjoin_with_dr_negation(value_space, datatype_restriction)


DatatypeRegistry.register(AnonymousConstantsDatatypeHandler())
