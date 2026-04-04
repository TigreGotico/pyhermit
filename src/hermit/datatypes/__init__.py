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
    from hermit.datatypes import (  # noqa: F401 (side-effect: handlers register on import)
        anyuri,
        binarydata,
        bool as bool_dt,
        datetime as datetime_dt,
        doublenum,
        floatnum,
        owlreal,
        rdfplainliteral,
        xmlliteral,
    )


# Auto-register on first access
_register_all()
