"""Coverage boost 21 — DataRange subclasses and related model methods.

Covers lines: 1311, 1318, 1331, 1340, 1343, 1351, 1368, 1375, 1378, 1381,
             1384, 1390-1392, 1406, 1409, 1412, 1415, 1418, 1428, 1436,
             1498, 1536, 1565, 1568, 1573, 1579, 1588, etc.
"""

from __future__ import annotations

import pytest

from hermit.model import (
    AtomicDataRange,
    AtomicNegationDataRange,
    ConstantEnumeration,
    Constant,
    DatatypeRestriction,
)

XSD = "http://www.w3.org/2001/XMLSchema#"


def _int_const(val: str) -> Constant:
    return Constant.create(val, XSD + "integer")


class TestAtomicDataRange:
    """Tests for AtomicDataRange — lines 1331, 1340, 1343, 1351."""

    def test_datatype_iri_property(self):
        """Line 1331: datatype_iri property."""
        adr = AtomicDataRange.create(XSD + "integer")
        assert adr.datatype_iri == XSD + "integer"

    def test_str(self):
        """Line 1340: __str__ abbreviates IRI."""
        adr = AtomicDataRange.create(XSD + "integer")
        s = str(adr)
        assert "integer" in s.lower() or "Integer" in s

    def test_repr(self):
        """Line 1343: __repr__ works."""
        adr = AtomicDataRange.create(XSD + "string")
        r = repr(adr)
        assert "AtomicDataRange" in r

    def test_eq_different_type(self):
        """Line 1351: != different type."""
        adr = AtomicDataRange.create(XSD + "integer")
        assert adr != "integer"
        assert adr != 42

    def test_eq_different_iri(self):
        """AtomicDataRange with different IRI not equal."""
        adr1 = AtomicDataRange.create(XSD + "integer")
        adr2 = AtomicDataRange.create(XSD + "string")
        assert adr1 != adr2


class TestAtomicNegationDataRange:
    """Tests for AtomicNegationDataRange — lines 1368, 1375, 1378, 1381, 1384, 1390-1392."""

    def test_negated_property(self):
        """Line 1368: negated property returns base AtomicDataRange."""
        base = AtomicDataRange.create(XSD + "integer")
        neg = AtomicNegationDataRange.create(base)
        assert neg.negated is base

    def test_is_always_true(self):
        """Line 1375: is_always_true() returns False."""
        base = AtomicDataRange.create(XSD + "integer")
        neg = AtomicNegationDataRange.create(base)
        assert not neg.is_always_true()

    def test_is_always_false(self):
        """Line 1378: is_always_false() returns False."""
        base = AtomicDataRange.create(XSD + "integer")
        neg = AtomicNegationDataRange.create(base)
        assert not neg.is_always_false()

    def test_str(self):
        """Line 1381: __str__ starts with ¬."""
        base = AtomicDataRange.create(XSD + "integer")
        neg = AtomicNegationDataRange.create(base)
        s = str(neg)
        assert "¬" in s or "not" in s.lower()

    def test_repr(self):
        """Line 1384: __repr__ works."""
        base = AtomicDataRange.create(XSD + "integer")
        neg = AtomicNegationDataRange.create(base)
        r = repr(neg)
        assert "AtomicNegationDataRange" in r

    def test_eq_different_type(self):
        """Lines 1390-1392: != different type."""
        base = AtomicDataRange.create(XSD + "integer")
        neg = AtomicNegationDataRange.create(base)
        assert neg != base
        assert neg != "neg"

    def test_eq_same(self):
        """Two AtomicNegationDataRange with same base are equal."""
        base = AtomicDataRange.create(XSD + "integer")
        neg1 = AtomicNegationDataRange.create(base)
        neg2 = AtomicNegationDataRange.create(base)
        assert neg1 == neg2


class TestConstantEnumeration:
    """Tests for ConstantEnumeration — lines 1406, 1409, 1412, 1415, 1418, 1428, 1436."""

    def test_constants_property(self):
        """Line 1406: constants property."""
        c1 = _int_const("1")
        ce = ConstantEnumeration.create((c1,))
        assert ce.constants == (c1,)

    def test_get_number_of_constants(self):
        """Line 1409: get_number_of_constants."""
        c1, c2 = _int_const("1"), _int_const("2")
        ce = ConstantEnumeration.create((c1, c2))
        assert ce.get_number_of_constants() == 2

    def test_get_constant(self):
        """Line 1412: get_constant(index)."""
        c1, c2 = _int_const("1"), _int_const("2")
        ce = ConstantEnumeration.create((c1, c2))
        assert ce.get_constant(0) == c1
        assert ce.get_constant(1) == c2

    def test_get_negation(self):
        """Line 1415: get_negation() returns AtomicNegationDataRange."""
        c1 = _int_const("1")
        ce = ConstantEnumeration.create((c1,))
        neg = ce.get_negation()
        assert isinstance(neg, AtomicNegationDataRange)

    def test_is_always_true(self):
        """Line 1418: is_always_true() returns False."""
        c1 = _int_const("1")
        ce = ConstantEnumeration.create((c1,))
        assert not ce.is_always_true()

    def test_repr(self):
        """Line 1428: __repr__ works."""
        c1 = _int_const("1")
        ce = ConstantEnumeration.create((c1,))
        r = repr(ce)
        assert "ConstantEnumeration" in r

    def test_eq_different_type(self):
        """Line 1436: != different type."""
        c1 = _int_const("1")
        ce = ConstantEnumeration.create((c1,))
        assert ce != "enumeration"
        assert ce != 42


class TestDatatypeRestriction:
    """Tests for DatatypeRestriction methods."""

    def test_datatype_iri_property(self):
        """DatatypeRestriction.datatype_iri property."""
        dr = DatatypeRestriction.create(XSD + "integer", (), ())
        assert dr.datatype_iri == XSD + "integer"

    def test_facet_uris_empty(self):
        """DatatypeRestriction with no facets."""
        dr = DatatypeRestriction.create(XSD + "integer", (), ())
        assert len(dr._facet_uris) == 0

    def test_is_always_true(self):
        """DatatypeRestriction.is_always_true() returns False."""
        dr = DatatypeRestriction.create(XSD + "integer", (), ())
        assert not dr.is_always_true()

    def test_is_always_false(self):
        """DatatypeRestriction.is_always_false() returns False."""
        dr = DatatypeRestriction.create(XSD + "integer", (), ())
        assert not dr.is_always_false()
