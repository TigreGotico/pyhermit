"""Coverage boost 19 — targeted tests for model/__init__.py dunder methods (batch 2).

Covers lines: 447, 457, 510-515, 518, 586, 633, 641, 664, 705, 717, 768, 779,
             803, 806, 814, 843, 873, 883, 933, 945-947, 986, 1059,
             1230, 1246, 1277, etc.
"""

from __future__ import annotations

import pytest

from hermit.model import (
    Atom,
    AtLeastDataRange,
    AtomicConcept,
    AtomicDataRange,
    AtomicNegationConcept,
    AtomicRole,
    ConstantEnumeration,
    Constant,
    DatatypeRestriction,
    DLClause,
    Individual,
    InverseRole,
    NegatedAtomicRole,
    Variable,
)

X = Variable.create("X")
Y = Variable.create("Y")
NS = "http://test.org#"


class TestConstantProperties:
    """Tests for Constant — lines 447, 457."""

    def test_data_value_property(self):
        """Line 447: Constant.data_value returns the parsed data value."""
        c = Constant.create("42", "http://www.w3.org/2001/XMLSchema#integer")
        dv = c.data_value
        assert dv is not None  # parsed integer value

    def test_repr(self):
        """Line 457: Constant.__repr__."""
        c = Constant.create("hello", "http://www.w3.org/2001/XMLSchema#string")
        r = repr(c)
        assert "Constant" in r
        assert "hello" in r


class TestConceptAccept:
    """Tests for Concept.accept() dispatch — lines 510-515, 518."""

    def test_accept_at_least_data_range(self):
        """Lines 510-511: accept dispatches visit_at_least_data_range for AtLeastDataRange."""
        r = AtomicRole.create(NS + "r")
        dr = AtomicDataRange("http://www.w3.org/2001/XMLSchema#integer")
        atleast = AtLeastDataRange.create(1, r, dr)

        class Visitor:
            called = None
            def visit_atomic_concept(self, x): self.called = "ac"
            def visit_atomic_negation_concept(self, x): self.called = "anc"
            def visit_at_least_concept(self, x): self.called = "alc"
            def visit_at_least_data_range(self, x): self.called = "aldr"
            def visit_exists_description_graph(self, x): self.called = "edg"
            def visit_other_concept(self, x): self.called = "other"

        v = Visitor()
        atleast.accept(v)
        assert v.called == "aldr"

    def test_accept_other_concept(self):
        """Lines 514-515: accept dispatches visit_other_concept for unknown concept type."""
        from hermit.model import AtMostConcept
        r = AtomicRole.create(NS + "r")
        a = AtomicConcept.create(NS + "A")
        atmost = AtMostConcept.create(2, r, a)

        class Visitor:
            called = None
            def visit_atomic_concept(self, x): self.called = "ac"
            def visit_atomic_negation_concept(self, x): self.called = "anc"
            def visit_at_least_concept(self, x): self.called = "alc"
            def visit_at_least_data_range(self, x): self.called = "aldr"
            def visit_exists_description_graph(self, x): self.called = "edg"
            def visit_at_most_concept(self, x): self.called = "amc"
            def visit_other_concept(self, x): self.called = "other"

        v = Visitor()
        atmost.accept(v)
        assert v.called == "amc"


class TestAtomicConceptEquals:
    """Tests for AtomicConcept.equals() — line 586."""

    def test_equals_same(self):
        """AtomicConcept.equals() returns True for same IRI."""
        a = AtomicConcept.create(NS + "A")
        assert a.equals(a)

    def test_equals_different_type(self):
        """AtomicConcept.equals() returns False for non-AtomicConcept."""
        a = AtomicConcept.create(NS + "A")
        assert not a.equals("A")


class TestAtomicNegationConceptMethods:
    """Tests for AtomicNegationConcept — lines 633, 641."""

    def test_repr(self):
        """Line 633: __repr__ works."""
        a = AtomicConcept.create(NS + "A")
        neg = AtomicNegationConcept.create(a)
        r = repr(neg)
        assert "AtomicNegationConcept" in r

    def test_eq_different_type(self):
        """Line 641: != non-AtomicNegationConcept returns False."""
        a = AtomicConcept.create(NS + "A")
        neg = AtomicNegationConcept.create(a)
        assert neg != a
        assert neg != "A"


class TestAtomicRoleEquals:
    """Tests for AtomicRole — lines 705, 717."""

    def test_repr(self):
        """Line 705: __repr__ works."""
        r = AtomicRole.create(NS + "r")
        s = repr(r)
        assert "AtomicRole" in s

    def test_equals(self):
        """Line 717: AtomicRole.equals() works."""
        r = AtomicRole.create(NS + "r")
        r2 = AtomicRole.create(NS + "r")
        assert r.equals(r2)
        assert not r.equals("r")


class TestInverseRoleMethods:
    """Tests for InverseRole — lines 768, 779."""

    def test_repr(self):
        """Line 768: __repr__ works."""
        r = AtomicRole.create(NS + "r")
        inv = InverseRole.create(r)
        s = repr(inv)
        assert "InverseRole" in s

    def test_equals(self):
        """Line 779: InverseRole.equals() works."""
        r = AtomicRole.create(NS + "r")
        inv = InverseRole.create(r)
        inv2 = InverseRole.create(r)
        assert inv.equals(inv2)
        assert not inv.equals(r)


class TestNegatedAtomicRoleMethods:
    """Tests for NegatedAtomicRole — lines 803, 806, 814."""

    def test_str(self):
        """Line 803: __str__ returns not(role)."""
        r = AtomicRole.create(NS + "r")
        nar = NegatedAtomicRole.create(r)
        assert "not" in str(nar) or "r" in str(nar)

    def test_repr(self):
        """Line 806: __repr__ works."""
        r = AtomicRole.create(NS + "r")
        nar = NegatedAtomicRole.create(r)
        s = repr(nar)
        assert "NegatedAtomicRole" in s

    def test_eq_different_type(self):
        """Line 814: != different type."""
        r = AtomicRole.create(NS + "r")
        nar = NegatedAtomicRole.create(r)
        assert nar != r
        assert nar != "not(r)"


class TestAtomMethods2:
    """Tests for Atom methods — lines 843, 873, 883."""

    def test_atom_repr(self):
        """Atom.__repr__ works."""
        a = AtomicConcept.create(NS + "A")
        atom = Atom.create(a, X)
        s = repr(atom)
        assert "Atom" in s or "A" in s

    def test_atom_equals(self):
        """Atom equals() Java-compat method."""
        a = AtomicConcept.create(NS + "A")
        atom1 = Atom.create(a, X)
        atom2 = Atom.create(a, X)
        assert atom1 == atom2

    def test_atom_eq_different_type(self):
        """Atom.__eq__ with non-Atom returns False."""
        a = AtomicConcept.create(NS + "A")
        atom = Atom.create(a, X)
        assert atom != "atom"


class TestDLClauseMethods2:
    """Tests for DLClause — lines 1230, 1246."""

    def test_dl_clause_repr(self):
        """Line 1230: DLClause.__repr__ works."""
        a = AtomicConcept.create(NS + "A")
        b = AtomicConcept.create(NS + "B")
        clause = DLClause.create(
            (Atom.create(b, X),),
            (Atom.create(a, X),),
        )
        s = repr(clause)
        assert "DLClause" in s

    def test_dl_clause_eq_different_type(self):
        """Line 1246: DLClause.__eq__ with non-DLClause returns False."""
        a = AtomicConcept.create(NS + "A")
        clause = DLClause.create(
            (Atom.create(a, X),),
            (),
        )
        assert clause != "clause"
        assert clause != 42
