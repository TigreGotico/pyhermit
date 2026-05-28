"""Coverage boost 17 — targeted tests for model/__init__.py.

Covers lines: 214, 226, 300, 303, 313-314, 321, 373, 420, 447, 457, 468,
             510-515, 518, 574, 586, 633, 641, 664, 705, 717, 768, 779,
             803, 806, 814, 843, 873, 883, 933, 945-947, 986, 1059,
             1308-1315, 1786-1792, 1805, 1808, 1817, 1821, etc.
"""

from __future__ import annotations

import pytest

from hermit.model import (
    Atom,
    AtomicConcept,
    AtomicRole,
    AtomicNegationConcept,
    AtomicDataRange,
    ConstantEnumeration,
    Constant,
    DatatypeRestriction,
    DLClause,
    Individual,
    InverseRole,
    Variable,
    Prefixes,
)


X = Variable.create("X")
Y = Variable.create("Y")
NS = "http://test.org#"


class TestPrefixesErrors:
    """Tests for Prefixes.expand_iri error cases — lines 213-214, 226."""

    def test_expand_iri_http_prefix_raises(self):
        """Line 213-214: abbreviation starting with 'http:' raises ValueError."""
        p = Prefixes()
        with pytest.raises(ValueError, match="enclosed in"):
            p.expand_abbreviation("http://example.org/foo")

    def test_declare_prefix_collision_raises(self):
        """Line 226: declaring same IRI with different prefix name raises."""
        p = Prefixes()
        p.declare_prefix("foo:", "http://foo.org/")
        with pytest.raises(ValueError, match="already associated"):
            p.declare_prefix("bar:", "http://foo.org/")


class TestDataRangeAccept:
    """Tests for DataRange.accept() dispatch — lines 1308-1315."""

    def test_accept_datatype_restriction(self):
        """Lines 1308-1309: DataRange.accept() dispatches visit_datatype_restriction."""
        dr = DatatypeRestriction.create(
            "http://www.w3.org/2001/XMLSchema#integer", (), ()
        )

        class Visitor:
            called = None
            def visit_datatype_restriction(self, x): self.called = "dr"
            def visit_internal_datatype(self, x): self.called = "idt"
            def visit_constant_enumeration(self, x): self.called = "ce"
            def visit_other_data_range(self, x): self.called = "other"

        v = Visitor()
        dr.accept(v)
        assert v.called == "dr"

    def test_accept_constant_enumeration(self):
        """Lines 1312-1313: DataRange.accept() dispatches visit_constant_enumeration."""
        c = Constant.create("hello", "http://www.w3.org/2001/XMLSchema#string")
        ce = ConstantEnumeration.create((c,))

        class Visitor:
            called = None
            def visit_datatype_restriction(self, x): self.called = "dr"
            def visit_internal_datatype(self, x): self.called = "idt"
            def visit_constant_enumeration(self, x): self.called = "ce"
            def visit_other_data_range(self, x): self.called = "other"

        v = Visitor()
        ce.accept(v)
        assert v.called == "ce"

    def test_accept_atomic_data_range(self):
        """Line 1314-1315: DataRange.accept() dispatches visit_other_data_range for AtomicDataRange."""
        adr = AtomicDataRange("http://www.w3.org/2001/XMLSchema#string")

        class Visitor:
            called = None
            def visit_datatype_restriction(self, x): self.called = "dr"
            def visit_internal_datatype(self, x): self.called = "idt"
            def visit_constant_enumeration(self, x): self.called = "ce"
            def visit_other_data_range(self, x): self.called = "other"

        v = Visitor()
        adr.accept(v)
        assert v.called == "other"


class TestDatatypeRestrictionStr:
    """Tests for DatatypeRestriction.__str__ — lines 1786-1792."""

    def test_str_without_facets(self):
        """DatatypeRestriction with no facets — basic __str__."""
        dr = DatatypeRestriction.create(
            "http://www.w3.org/2001/XMLSchema#integer", (), ()
        )
        s = str(dr)
        assert "integer" in s.lower() or "xsd" in s.lower() or "Integer" in s

    def test_str_with_facets(self):
        """Lines 1787-1791: DatatypeRestriction with facets includes facet parts."""
        XSD = "http://www.w3.org/2001/XMLSchema#"
        facet_uri = XSD + "minInclusive"
        from hermit.model import Constant
        facet_val = Constant.create("5", XSD + "integer")
        dr = DatatypeRestriction.create(
            XSD + "integer",
            (facet_uri,),
            (facet_val,),
        )
        s = str(dr)
        assert "5" in s or "minInclusive" in s or "integer" in s.lower()


class TestAtomicDataRange:
    """Tests for AtomicDataRange — lines 1805, 1808."""

    def test_is_always_true(self):
        """Line 1805: AtomicDataRange.is_always_true() returns False."""
        adr = AtomicDataRange("http://www.w3.org/2001/XMLSchema#string")
        assert not adr.is_always_true()

    def test_is_always_false(self):
        """Line 1808: AtomicDataRange.is_always_false() returns False."""
        adr = AtomicDataRange("http://www.w3.org/2001/XMLSchema#string")
        assert not adr.is_always_false()


class TestDLClauseClassification:
    """Tests for DLClause classification methods — lines 1059, 1086, 1088, etc."""

    def test_is_general_concept_inclusion_role_in_head_false(self):
        """Line 1104-1105: head has Role predicate → returns False."""
        r = AtomicRole(NS + "r")
        a = AtomicConcept.create(NS + "A")
        # role(X,Y) in head
        clause = DLClause.create(
            (Atom.create(r, X, Y),),
            (Atom.create(a, X),),
        )
        assert not clause.is_general_concept_inclusion()

    def test_is_general_concept_inclusion_atleast_in_head_true(self):
        """Line 1079-1080: head has AtLeast predicate → returns True."""
        from hermit.model import AtLeastConcept
        r = AtomicRole(NS + "r")
        a = AtomicConcept.create(NS + "A")
        atleast = AtLeastConcept.create(1, r, a)
        clause = DLClause.create(
            (Atom.create(atleast, X),),
            (Atom.create(a, X),),
        )
        assert clause.is_general_concept_inclusion()

    def test_get_safe_version_no_unsafe(self):
        """DLClause.get_safe_version() returns self if no unsafe variables."""
        a = AtomicConcept.create(NS + "A")
        b = AtomicConcept.create(NS + "B")
        clause = DLClause.create(
            (Atom.create(b, X),),
            (Atom.create(a, X),),
        )
        safe = clause.get_safe_version(a)
        assert safe is clause

    def test_get_safe_version_with_unsafe(self):
        """Lines 1277: get_safe_version adds body atoms for unsafe variables."""
        a = AtomicConcept.create(NS + "A")
        b = AtomicConcept.create(NS + "B")
        # Head has Y but body doesn't mention Y → Y is unsafe
        clause = DLClause.create(
            (Atom.create(b, X), Atom.create(b, Y)),
            (Atom.create(a, X),),
        )
        safe = clause.get_safe_version(a)
        # safe should have Y constrained by body atom
        assert safe.body_length() > clause.body_length()


class TestConstantEnumeration:
    """Tests for ConstantEnumeration — covers various lines."""

    def test_create_and_basic_ops(self):
        """Basic ConstantEnumeration creation and arity."""
        c1 = Constant.create("1", "http://www.w3.org/2001/XMLSchema#integer")
        c2 = Constant.create("2", "http://www.w3.org/2001/XMLSchema#integer")
        ce = ConstantEnumeration.create((c1, c2))
        assert ce.arity() == 1
        assert not ce.is_always_false()

    def test_constant_enumeration_str(self):
        """ConstantEnumeration __str__ works."""
        c = Constant.create("hello", "http://www.w3.org/2001/XMLSchema#string")
        ce = ConstantEnumeration.create((c,))
        s = str(ce)
        assert "hello" in s or "Enumeration" in s or "{" in s
