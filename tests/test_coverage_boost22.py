"""Coverage boost 22 — ExistsDescriptionGraph, DescriptionGraph, other model classes.

Covers lines: 512-515, 518 (Concept.accept), 664 (Role.__str__),
             1498, 1536, 1565, 1568, 1573, 1579, 1588,
             1624, 1630-1633, 1700, 1711-1713, 1742,
             1805, 1808, 1817, 1821, 1863, 1916, 1965, 1968, 2106
"""

from __future__ import annotations

import pytest

from hermit.model import (
    Atom,
    AtomicConcept,
    AtomicRole,
    DLClause,
    DescriptionGraph,
    DescriptionGraphEdge,
    ExistsDescriptionGraph,
    Variable,
)

X = Variable.create("X")
Y = Variable.create("Y")
NS = "http://test.org#"


def _make_dg(name: str = "TestGraph") -> DescriptionGraph:
    """Create a minimal DescriptionGraph with one vertex and no edges."""
    a = AtomicConcept.create(NS + "A")
    return DescriptionGraph(
        name=NS + name,
        concepts_by_vertex=(a,),
        edges=(),
        start_concepts=frozenset([a]),
    )


class TestExistsDescriptionGraph:
    """Tests for ExistsDescriptionGraph — lines 1624, 1630-1633."""

    def test_accept_exists_description_graph(self):
        """Lines 512-513: Concept.accept() dispatches visit_exists_description_graph."""
        dg = _make_dg()
        edg = ExistsDescriptionGraph.create(dg, 0)

        class Visitor:
            called = None
            def visit_atomic_concept(self, x): self.called = "ac"
            def visit_atomic_negation_concept(self, x): self.called = "anc"
            def visit_at_least_concept(self, x): self.called = "alc"
            def visit_at_least_data_range(self, x): self.called = "aldr"
            def visit_exists_description_graph(self, x): self.called = "edg"
            def visit_other_concept(self, x): self.called = "other"

        v = Visitor()
        edg.accept(v)
        assert v.called == "edg"

    def test_str(self):
        """Line 1624: __str__ works."""
        dg = _make_dg()
        edg = ExistsDescriptionGraph.create(dg, 0)
        s = str(edg)
        assert "existsDG" in s or "TestGraph" in s or NS in s

    def test_eq_same(self):
        """Lines 1630-1632: two ExistsDescriptionGraph with same dg and vertex are equal."""
        dg = _make_dg()
        e1 = ExistsDescriptionGraph.create(dg, 0)
        e2 = ExistsDescriptionGraph.create(dg, 0)
        assert e1 == e2

    def test_eq_different_vertex(self):
        """Two ExistsDescriptionGraph with different vertex are not equal."""
        dg = DescriptionGraph(
            name=NS + "G2",
            concepts_by_vertex=(AtomicConcept.create(NS + "A"), AtomicConcept.create(NS + "B")),
            edges=(),
            start_concepts=frozenset([AtomicConcept.create(NS + "A")]),
        )
        e1 = ExistsDescriptionGraph.create(dg, 0)
        e2 = ExistsDescriptionGraph.create(dg, 1)
        assert e1 != e2

    def test_eq_different_type(self):
        """Line 1633: != different type."""
        dg = _make_dg()
        edg = ExistsDescriptionGraph.create(dg, 0)
        assert edg != 0
        assert edg != "edg"


class TestDescriptionGraph:
    """Tests for DescriptionGraph — lines 1965, 1968."""

    def test_str(self):
        """Line 1965: __str__ abbreviates name."""
        dg = _make_dg("MyGraph")
        s = str(dg)
        assert "MyGraph" in s or NS in s

    def test_repr(self):
        """Line 1968: __repr__ works."""
        dg = _make_dg()
        r = repr(dg)
        assert "DescriptionGraph" in r
        assert "0e" in r or "0v" in r or "1v" in r

    def test_produce_start_dl_clauses(self):
        """DescriptionGraph.produce_start_dl_clauses adds clauses."""
        a = AtomicConcept.create(NS + "A")
        dg = DescriptionGraph(
            name=NS + "G",
            concepts_by_vertex=(a,),
            edges=(),
            start_concepts=frozenset([a]),
        )
        result: set[DLClause] = set()
        dg.produce_start_dl_clauses(result)
        assert len(result) >= 1

    def test_description_graph_edge(self):
        """DescriptionGraphEdge basic tests — lines 1908, 1911-1916."""
        from hermit.model import DescriptionGraphEdge
        r = AtomicRole.create(NS + "r")
        edge = DescriptionGraphEdge(r, 0, 1)
        assert edge.from_vertex == 0
        assert edge.to_vertex == 1
        # hash and eq
        edge2 = DescriptionGraphEdge(r, 0, 1)
        assert hash(edge) == hash(edge2)
        assert edge == edge2
        assert edge != DescriptionGraphEdge(r, 0, 2)


class TestAtLeastConcept:
    """Tests for AtLeastConcept additional methods — lines 1498, 1536."""

    def test_at_least_concept_str(self):
        """Line 1498: AtLeastConcept.__str__."""
        from hermit.model import AtLeastConcept
        r = AtomicRole.create(NS + "r")
        a = AtomicConcept.create(NS + "A")
        alc = AtLeastConcept.create(2, r, a)
        s = str(alc)
        assert "2" in s or ">=" in s or "A" in s

    def test_at_least_concept_repr(self):
        """AtLeastConcept.__repr__."""
        from hermit.model import AtLeastConcept
        r = AtomicRole.create(NS + "r")
        a = AtomicConcept.create(NS + "A")
        alc = AtLeastConcept.create(2, r, a)
        s = repr(alc)
        assert "AtLeastConcept" in s or "2" in s


class TestAtMostConcept:
    """Tests for AtMostConcept additional methods — lines 1565, 1568, 1573, 1579, 1588."""

    def test_at_most_concept_properties(self):
        """AtMostConcept number, on_role, to_concept properties."""
        from hermit.model import AtMostConcept
        r = AtomicRole.create(NS + "r")
        a = AtomicConcept.create(NS + "A")
        amc = AtMostConcept.create(3, r, a)
        assert amc.number == 3
        assert amc.on_role == r
        assert amc.to_concept == a

    def test_at_most_concept_str(self):
        """Line 1573 approx: AtMostConcept.__str__ works."""
        from hermit.model import AtMostConcept
        r = AtomicRole.create(NS + "r")
        a = AtomicConcept.create(NS + "A")
        amc = AtMostConcept.create(3, r, a)
        s = str(amc)
        assert "3" in s or "<=" in s or "A" in s

    def test_at_most_concept_eq_different_type(self):
        """AtMostConcept != different type."""
        from hermit.model import AtMostConcept
        r = AtomicRole.create(NS + "r")
        a = AtomicConcept.create(NS + "A")
        amc = AtMostConcept.create(1, r, a)
        assert amc != "amc"
        assert amc != 42


class TestAnnotatedEquality:
    """Tests for AnnotatedEquality — lines 1700, 1711-1713."""

    def test_annotated_equality_basic(self):
        """AnnotatedEquality creation and access."""
        from hermit.model import AnnotatedEquality
        r = AtomicRole.create(NS + "r")
        a = AtomicConcept.create(NS + "A")
        ae = AnnotatedEquality(2, r, a)
        assert ae.cardinality == 2
        assert ae.on_role == r
        assert ae.to_concept == a

    def test_annotated_equality_str(self):
        """AnnotatedEquality.__str__ works."""
        from hermit.model import AnnotatedEquality
        r = AtomicRole.create(NS + "r")
        a = AtomicConcept.create(NS + "A")
        ae = AnnotatedEquality(2, r, a)
        s = str(ae)
        assert "2" in s or "AnnotatedEquality" in s or "A" in s

    def test_annotated_equality_hash_eq(self):
        """AnnotatedEquality hash and eq."""
        from hermit.model import AnnotatedEquality
        r = AtomicRole.create(NS + "r")
        a = AtomicConcept.create(NS + "A")
        ae1 = AnnotatedEquality(2, r, a)
        ae2 = AnnotatedEquality(2, r, a)
        assert hash(ae1) == hash(ae2)
        assert ae1 == ae2
        assert ae1 != AnnotatedEquality(3, r, a)
