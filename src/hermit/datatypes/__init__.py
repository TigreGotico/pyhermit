"""Datatype handlers for OWL 2 datatypes."""

from hermit.datatypes.registry import (
    DatatypeHandler,
    DatatypeRegistry,
    MalformedLiteralException,
    UnsupportedDatatypeException,
    UnsupportedFacetException,
    ValueSpaceSubset,
)

__all__ = [
    "DatatypeHandler",
    "DatatypeRegistry",
    "MalformedLiteralException",
    "UnsupportedDatatypeException",
    "UnsupportedFacetException",
    "ValueSpaceSubset",
]


def _register_all() -> None:
    """Import all handler sub-packages so they self-register."""
    from hermit.datatypes import owlreal
    from hermit.datatypes import doublenum
    from hermit.datatypes import floatnum
    from hermit.datatypes import datetime as datetime_dt
    from hermit.datatypes import bool as bool_dt
    from hermit.datatypes import anyuri
    from hermit.datatypes import xmlliteral
    from hermit.datatypes import rdfplainliteral
    from hermit.datatypes import binarydata


# Auto-register on first access
_register_all()
