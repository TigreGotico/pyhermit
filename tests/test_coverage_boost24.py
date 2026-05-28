"""Coverage boost 24 — remaining model/__init__.py lines and other modules.

Covers lines: 843, 873, 883 (Equality/Inequality repr), 1059 (get_body_atoms),
             1086, 1088, 1090 (is_general_concept_inclusion branches),
             1277 (make_safe empty clause), 1311, 1318 (InternalDatatype accept),
             1536, 1565, 1568 (AtLeastDataRange eq/AtMostConcept),
             1700, 1711-1713, 1742 (NodeIDLessEqualThan, NodeIDsAscendingOrEqual),
             1805, 1808 (DatatypeRestriction facet eq), 1817, 1821, 1863, 1916, 2106
"""

from __future__ import annotations

import pytest

from hermit.model import (
    Atom,
    AtomicConcept,
    AtomicRole,
    Constant,
    DLClause,
    DLOntology,
    Individual,
    InverseRole,
    Variable,
)

X = Variable.create("X")
Y = Variable.create("Y")
NS = "http://test.org#"
XSD = "http://www.w3.org/2001/XMLSchema#"


class TestEqualityInequality:
    """Tests for Equality.__repr__ (line 843) and Inequality repr (line 873)."""

    def test_equality_repr(self):
        """Line 843: Equality.__repr__ returns 'Equality'."""
        from hermit.model import Equality
        eq = Equality.INSTANCE
        assert repr(eq) == "Equality"

    def test_inequality_repr(self):
        """Line 873: Inequality.__repr__ returns 'Inequality'."""
        from hermit.model import Inequality
        ineq = Inequality.INSTANCE
        assert repr(ineq) == "Inequality"

    def test_inequality_equals(self):
        """Line 883: Inequality.equals() method."""
        from hermit.model import Inequality
        ineq = Inequality.INSTANCE
        assert ineq.equals(Inequality.INSTANCE)
        assert not ineq.equals("ineq")


class TestDLClauseGetMethods:
    """Tests for DLClause.get_body_atoms() (line 1059) and get_head_atoms() (line 1057)."""

    def test_get_body_atoms(self):
        """Line 1059: get_body_atoms() returns body atoms tuple."""
        a = AtomicConcept.create(NS + "A")
        b = AtomicConcept.create(NS + "B")
        clause = DLClause.create(
            (Atom.create(b, X),),
            (Atom.create(a, X),),
        )
        body = clause.get_body_atoms()
        assert len(body) == 1
        assert body[0].predicate == a

    def test_get_head_atoms(self):
        """Line 1057: get_head_atoms() returns head atoms tuple."""
        a = AtomicConcept.create(NS + "A")
        b = AtomicConcept.create(NS + "B")
        clause = DLClause.create(
            (Atom.create(b, X),),
            (Atom.create(a, X),),
        )
        head = clause.get_head_atoms()
        assert len(head) == 1
        assert head[0].predicate == b


class TestIsGCIAdditionalBranches:
    """Test is_general_concept_inclusion branches for lines 1086, 1088, 1090."""

    def test_annotated_equality_in_head_line1086(self):
        """Line 1086: AnnotatedEquality in head → returns True."""
        from hermit.model import AnnotatedEquality
        r = AtomicRole.create(NS + "r")
        a = AtomicConcept.create(NS + "A")
        ae = AnnotatedEquality(2, r, a)
        Z = Variable.create("Z")
        head_atom = Atom.create(ae, X, Y, Z)  # arity 3
        body_atom = Atom.create(a, X)
        clause = DLClause.create((head_atom,), (body_atom,))
        assert clause.is_general_concept_inclusion()

    def test_node_id_less_equal_than_in_head_line1088(self):
        """Line 1088: NodeIDLessEqualThan in head → returns True."""
        from hermit.model import NodeIDLessEqualThan
        a = AtomicConcept.create(NS + "A")
        nle = NodeIDLessEqualThan.INSTANCE
        head_atom = Atom.create(nle, X, Y)
        body_atom = Atom.create(a, X)
        clause = DLClause.create((head_atom,), (body_atom,))
        assert clause.is_general_concept_inclusion()

    def test_node_ids_ascending_in_head_line1090(self):
        """Line 1090: NodeIDsAscendingOrEqual in head → returns True."""
        from hermit.model import NodeIDsAscendingOrEqual
        a = AtomicConcept.create(NS + "A")
        nao = NodeIDsAscendingOrEqual.create(2)
        head_atom = Atom.create(nao, X, Y)
        body_atom = Atom.create(a, X)
        clause = DLClause.create((head_atom,), (body_atom,))
        assert clause.is_general_concept_inclusion()


class TestGetSafeVersionEmptyClause:
    """Test DLClause.get_safe_version when head and body are empty (line 1277)."""

    def test_get_safe_version_empty_clause_adds_x(self):
        """Line 1277: empty clause → adds Variable('X') as unsafe."""
        from hermit.model import AtomicConcept as AC
        safe = AC.INTERNAL_NAMED
        clause = DLClause.create((), ())
        result = clause.get_safe_version(safe)
        # Should add body atom for X
        assert len(result.body_atoms) >= 1


class TestInternalDatatype:
    """Tests for InternalDatatype accept (line 1311) and __str__ (line 1318)."""

    def test_accept_internal_datatype_line1311(self):
        """Line 1311: DataRange.accept() dispatches visit_internal_datatype."""
        from hermit.model import InternalDatatype
        idt = InternalDatatype(XSD + "integer")

        class Visitor:
            called = None
            def visit_datatype_restriction(self, x): self.called = "dr"
            def visit_internal_datatype(self, x): self.called = "idt"
            def visit_constant_enumeration(self, x): self.called = "ce"
            def visit_other_data_range(self, x): self.called = "other"

        v = Visitor()
        idt.accept(v)
        assert v.called == "idt"

    def test_internal_datatype_str_line1318(self):
        """Line 1318: InternalDatatype.__str__ returns abbreviated IRI."""
        from hermit.model import InternalDatatype
        idt = InternalDatatype(XSD + "integer")
        s = str(idt)
        assert "integer" in s.lower() or "xsd" in s.lower()


class TestAtLeastDataRangeEq:
    """Tests for AtLeastDataRange.__eq__ false branch (line 1536)."""

    def test_at_least_data_range_eq_different_type(self):
        """Line 1536: AtLeastDataRange.__eq__ returns False for non-AtLeastDataRange."""
        from hermit.model import AtLeastDataRange, AtomicDataRange
        r = AtomicRole.create(NS + "r")
        dr = AtomicDataRange(XSD + "integer")
        atleast = AtLeastDataRange.create(1, r, dr)
        assert atleast != "other"
        assert atleast != 42


class TestAtMostConceptNoVisitor:
    """Tests for AtMostConcept.accept with missing method (line 1573)."""

    def test_at_most_concept_accept_missing_method_raises(self):
        """Line 1573: AtMostConcept.accept raises AttributeError if method missing."""
        from hermit.model import AtMostConcept
        r = AtomicRole.create(NS + "r")
        a = AtomicConcept.create(NS + "A")
        amc = AtMostConcept.create(1, r, a)

        class BadVisitor:
            pass

        with pytest.raises(AttributeError):
            amc.accept(BadVisitor())


class TestNodeIDLessEqualThan:
    """Tests for NodeIDLessEqualThan — lines 1700, 1711-1713, 1742."""

    def test_str_line1700(self):
        """Line 1700: __str__ returns '<='."""
        from hermit.model import NodeIDLessEqualThan
        nle = NodeIDLessEqualThan.INSTANCE
        assert str(nle) == "<="

    def test_hash_line1711(self):
        """Line 1711: __hash__ returns 10."""
        from hermit.model import NodeIDLessEqualThan
        nle = NodeIDLessEqualThan.INSTANCE
        assert hash(nle) == 10

    def test_eq_line1712(self):
        """Line 1712: __eq__ True for same type."""
        from hermit.model import NodeIDLessEqualThan
        nle = NodeIDLessEqualThan.INSTANCE
        assert nle == NodeIDLessEqualThan.INSTANCE
        assert nle != "other"

    def test_equals_line1713(self):
        """Line 1713: equals() method."""
        from hermit.model import NodeIDLessEqualThan
        nle = NodeIDLessEqualThan.INSTANCE
        assert nle.equals(NodeIDLessEqualThan.INSTANCE)

    def test_create_returns_singleton_line1742(self):
        """Lines 1719-1720, 1742: NodeIDLessEqualThan.create() returns INSTANCE."""
        from hermit.model import NodeIDLessEqualThan
        nle = NodeIDLessEqualThan.create()
        assert nle is NodeIDLessEqualThan.INSTANCE


class TestNodeIDsAscendingOrEqual:
    """Tests for NodeIDsAscendingOrEqual.equals() (line 1742)."""

    def test_equals(self):
        """Line 1742: NodeIDsAscendingOrEqual.equals() method."""
        from hermit.model import NodeIDsAscendingOrEqual
        nao1 = NodeIDsAscendingOrEqual.create(2)
        nao2 = NodeIDsAscendingOrEqual.create(2)
        assert nao1.equals(nao2)
        assert not nao1.equals("other")


class TestDatatypeRestrictionEqFacets:
    """Tests for DatatypeRestriction with facets — lines 1805, 1808, 1817, 1821."""

    def test_eq_different_facet_count_line1805(self):
        """Line 1805: different number of facets → False."""
        from hermit.model import DatatypeRestriction
        c = Constant.create("5", XSD + "integer")
        dr1 = DatatypeRestriction.create(
            XSD + "integer",
            (XSD + "minInclusive",),
            (c,),
        )
        dr2 = DatatypeRestriction.create(XSD + "integer", (), ())
        assert dr1 != dr2

    def test_eq_facet_mismatch_line1808(self):
        """Line 1808: same facet count but different facet value → False."""
        from hermit.model import DatatypeRestriction
        c1 = Constant.create("5", XSD + "integer")
        c2 = Constant.create("10", XSD + "integer")
        dr1 = DatatypeRestriction.create(
            XSD + "integer",
            (XSD + "minInclusive",),
            (c1,),
        )
        dr2 = DatatypeRestriction.create(
            XSD + "integer",
            (XSD + "minInclusive",),
            (c2,),
        )
        assert dr1 != dr2

    def test_eq_same_facets_line1817(self):
        """Line 1817: same facets → True."""
        from hermit.model import DatatypeRestriction
        c = Constant.create("5", XSD + "integer")
        dr1 = DatatypeRestriction.create(
            XSD + "integer",
            (XSD + "minInclusive",),
            (c,),
        )
        dr2 = DatatypeRestriction.create(
            XSD + "integer",
            (XSD + "minInclusive",),
            (c,),
        )
        assert dr1 == dr2


class TestInternalDatatypeStr:
    """Tests for InternalDatatype.__str__ and __eq__ — lines 1863, 1916."""

    def test_internal_datatype_str_line1863(self):
        """Line 1863: InternalDatatype.__str__ abbreviates IRI."""
        from hermit.model import InternalDatatype
        idt = InternalDatatype(XSD + "string")
        s = str(idt)
        assert isinstance(s, str)
        assert len(s) > 0

    def test_internal_datatype_eq_line1916(self):
        """Line 1916: InternalDatatype.__eq__ False for different type."""
        from hermit.model import InternalDatatype
        idt = InternalDatatype(XSD + "integer")
        assert idt != "idt"
        assert idt != 42


class TestDLOntologyIndividuals:
    """Tests for DLOntology._individuals_from_atoms — line 2106."""

    def test_dl_ontology_individuals_from_positive_facts(self):
        """Line 2106: DLOntology collects individuals from positive/negative facts."""
        r = AtomicRole.create(NS + "r")
        ind_a = Individual.create(NS + "a")
        ind_b = Individual.create(NS + "b")
        pos_fact = Atom.create(r, ind_a, ind_b)
        ont = DLOntology(
            ontology_iri="urn:test",
            dl_clauses=frozenset(),
            positive_facts=frozenset([pos_fact]),
            negative_facts=frozenset(),
        )
        # accessing individuals triggers the 2106 branch
        inds = ont.all_individuals
        assert ind_a in inds
        assert ind_b in inds
