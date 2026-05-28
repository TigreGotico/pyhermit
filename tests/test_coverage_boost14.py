"""Coverage boost 14 — targeted tests for datatypes/registry.py.

Covers lines: 75, 84, 291-309 (disjoint checks), 322-357 (is_subset_of)
"""

from __future__ import annotations

import pytest

from hermit.datatypes.registry import DatatypeRegistry, ValueSpaceSubset

XSD = "http://www.w3.org/2001/XMLSchema#"

# Convenient shortcuts
xsd_string = XSD + "string"
xsd_integer = XSD + "integer"
xsd_decimal = XSD + "decimal"
xsd_boolean = XSD + "boolean"
xsd_float = XSD + "float"
xsd_double = XSD + "double"
xsd_date = XSD + "date"
xsd_dateTime = XSD + "dateTime"
xsd_hexBinary = XSD + "hexBinary"
xsd_base64 = XSD + "base64Binary"
xsd_long = XSD + "long"
xsd_int = XSD + "int"
xsd_nonNegInt = XSD + "nonNegativeInteger"
xsd_posInt = XSD + "positiveInteger"
xsd_negInt = XSD + "negativeInteger"
xsd_nonPosInt = XSD + "nonPositiveInteger"


class TestIsDisjointWith:
    """Tests for DatatypeRegistry.is_disjoint_with() — covers lines 291-309."""

    def test_numeric_disjoint_from_boolean(self):
        """Numbers are disjoint from booleans (line 291)."""
        assert DatatypeRegistry.is_disjoint_with(xsd_integer, xsd_boolean)

    def test_boolean_disjoint_from_numeric(self):
        """Booleans are disjoint from numbers (line 293)."""
        assert DatatypeRegistry.is_disjoint_with(xsd_boolean, xsd_integer)

    def test_numeric_disjoint_from_datetime(self):
        """Numbers are disjoint from dates (line 291)."""
        assert DatatypeRegistry.is_disjoint_with(xsd_integer, xsd_dateTime)

    def test_numeric_disjoint_from_binary(self):
        """Numbers are disjoint from binary (line 291)."""
        assert DatatypeRegistry.is_disjoint_with(xsd_integer, xsd_hexBinary)

    def test_boolean_disjoint_from_datetime(self):
        """Booleans are disjoint from dates (line 297)."""
        assert DatatypeRegistry.is_disjoint_with(xsd_boolean, xsd_dateTime)

    def test_boolean_disjoint_from_binary(self):
        """Booleans are disjoint from binaries (line 297)."""
        assert DatatypeRegistry.is_disjoint_with(xsd_boolean, xsd_hexBinary)

    def test_datetime_disjoint_from_boolean(self):
        """Dates are disjoint from booleans (reverse, line 299)."""
        assert DatatypeRegistry.is_disjoint_with(xsd_dateTime, xsd_boolean)

    def test_datetime_disjoint_from_binary(self):
        """Dates are disjoint from binaries (line 303)."""
        assert DatatypeRegistry.is_disjoint_with(xsd_dateTime, xsd_hexBinary)

    def test_binary_disjoint_from_datetime(self):
        """Binaries are disjoint from dates (line 305)."""
        assert DatatypeRegistry.is_disjoint_with(xsd_hexBinary, xsd_dateTime)

    def test_integer_not_disjoint_from_decimal(self):
        """Integers are not disjoint from decimals (same numeric group)."""
        assert not DatatypeRegistry.is_disjoint_with(xsd_integer, xsd_decimal)

    def test_string_not_disjoint_from_string(self):
        """String not disjoint from itself."""
        assert not DatatypeRegistry.is_disjoint_with(xsd_string, xsd_string)


class TestIsSubsetOf:
    """Tests for DatatypeRegistry.is_subset_of() — covers lines 322-357."""

    def test_same_type_is_subset_of_itself(self):
        """Line 319-320: same type is subset of itself."""
        assert DatatypeRegistry.is_subset_of(xsd_integer, xsd_integer)
        assert DatatypeRegistry.is_subset_of(xsd_string, xsd_string)

    def test_long_subset_of_integer(self):
        """xsd:long ⊆ xsd:integer."""
        assert DatatypeRegistry.is_subset_of(xsd_long, xsd_integer)

    def test_long_subset_of_decimal(self):
        """xsd:long ⊆ xsd:decimal."""
        assert DatatypeRegistry.is_subset_of(xsd_long, xsd_decimal)

    def test_int_subset_of_long(self):
        """xsd:int ⊆ xsd:long."""
        assert DatatypeRegistry.is_subset_of(xsd_int, xsd_long)

    def test_non_negative_integer_subset_of_integer(self):
        """xsd:nonNegativeInteger ⊆ xsd:integer."""
        assert DatatypeRegistry.is_subset_of(xsd_nonNegInt, xsd_integer)

    def test_positive_integer_subset_of_non_negative(self):
        """xsd:positiveInteger ⊆ xsd:nonNegativeInteger."""
        assert DatatypeRegistry.is_subset_of(xsd_posInt, xsd_nonNegInt)

    def test_negative_integer_subset_of_integer(self):
        """xsd:negativeInteger ⊆ xsd:nonPositiveInteger."""
        assert DatatypeRegistry.is_subset_of(xsd_negInt, xsd_nonPosInt)

    def test_decimal_subset_of_float(self):
        """xsd:decimal ⊆ xsd:float."""
        assert DatatypeRegistry.is_subset_of(xsd_decimal, xsd_float)

    def test_float_subset_of_double(self):
        """xsd:float ⊆ xsd:double."""
        assert DatatypeRegistry.is_subset_of(xsd_float, xsd_double)

    def test_integer_not_subset_of_string(self):
        """Integer is not subset of string (line 357: return False)."""
        assert not DatatypeRegistry.is_subset_of(xsd_integer, xsd_string)

    def test_string_not_subset_of_integer(self):
        """String is not subset of integer."""
        assert not DatatypeRegistry.is_subset_of(xsd_string, xsd_integer)

    def test_unknown_type_not_subset(self):
        """Unknown type returns False."""
        assert not DatatypeRegistry.is_subset_of("urn:unknown", xsd_integer)


class TestValueSpaceSubsetMethods:
    """Tests for ValueSpaceSubset methods — covers lines 75, 84."""

    def test_has_cardinality_at_least_zero_returns_true(self):
        """Line 75: has_cardinality_at_least(0) or negative returns True."""
        from hermit.datatypes.registry import DatatypeRegistry

        # Get a real subset via the registry
        subset = DatatypeRegistry.entire_space(xsd_boolean)
        assert subset.has_cardinality_at_least(0)
        assert subset.has_cardinality_at_least(-1)

    def test_contains_data_value_alias(self):
        """Line 84: contains_data_value delegates to contains()."""
        subset = DatatypeRegistry.entire_space(xsd_boolean)
        # For the entire boolean space, True and False should be contained
        result = subset.contains_data_value(True)
        assert result == subset.contains(True)
