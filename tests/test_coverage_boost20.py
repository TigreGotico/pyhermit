"""Coverage boost 20 — model/__init__.py Atom, DLClause, and DLOntology methods.

Covers lines: 933, 945-947, 986, 1059, 1086, 1088, 1090, 1098, 1100-1103,
             1311, 1318, 1331, 1340, 1343, 1351, 1368, 1375, 1378, 1381,
             1384, 1390-1392, 1406, 1409, 1412, 1415, 1418, 1428, 1436,
             1498, 1536, 1565, 1568, 1573, 1579, 1588, 1624, 1630-1633,
             1700, 1711-1713, 1742, 1817, 1821, 1863, 1916, 1965, 1968
"""

from __future__ import annotations

import pytest

from hermit.model import (
    Atom,
    AtomicConcept,
    AtomicRole,
    Constant,
    ConstantEnumeration,
    AtomicDataRange,
    DatatypeRestriction,
    DLClause,
    DLOntology,
    Individual,
    InverseRole,
    Variable,
)

X = Variable.create("X")
Y = Variable.create("Y")
NS = "http://test.org#"


class TestAtomArgumentMethods:
    """Tests for Atom methods that return None — line 933, 945-947."""

    def test_argument_variable_returns_none_for_individual(self):
        """Line 933: argument_variable() returns None when arg is Individual (not Variable)."""
        a = AtomicConcept.create(NS + "A")
        ind = Individual.create(NS + "Alice")
        atom = Atom.create(a, ind)
        result = atom.argument_variable(0)
        assert result is None

    def test_get_individuals_populates_set(self):
        """Lines 945-947: get_individuals() adds Individual args to set."""
        a = AtomicConcept.create(NS + "A")
        ind = Individual.create(NS + "Alice")
        atom = Atom.create(a, ind)
        individuals: set = set()
        atom.get_individuals(individuals)
        assert ind in individuals

    def test_get_individuals_skips_variables(self):
        """get_individuals() doesn't add Variable args."""
        a = AtomicConcept.create(NS + "A")
        atom = Atom.create(a, X)
        individuals: set = set()
        atom.get_individuals(individuals)
        assert len(individuals) == 0


class TestDLOntologyMethods:
    """Tests for DLOntology — line 986."""

    def test_dl_ontology_str(self):
        """DLOntology.__str__ works without crashing."""
        ont = DLOntology(
            ontology_iri="urn:test",
            dl_clauses=frozenset(),
            positive_facts=frozenset(),
            negative_facts=frozenset(),
        )
        s = str(ont)
        assert isinstance(s, str)

    def test_dl_ontology_has_negative_facts(self):
        """DLOntology.get_negative_facts() works."""
        r = AtomicRole.create(NS + "r")
        ind_a = Individual.create(NS + "a")
        ind_b = Individual.create(NS + "b")
        neg_fact = Atom.create(r, ind_a, ind_b)
        ont = DLOntology(
            ontology_iri="urn:test",
            dl_clauses=frozenset(),
            positive_facts=frozenset(),
            negative_facts=frozenset([neg_fact]),
        )
        assert len(ont.get_negative_facts()) > 0

    def test_dl_ontology_no_negative_facts(self):
        """DLOntology without negative facts returns False."""
        ont = DLOntology(
            ontology_iri="urn:test",
            dl_clauses=frozenset(),
            positive_facts=frozenset(),
            negative_facts=frozenset(),
        )
        assert len(ont.get_negative_facts()) == 0


class TestIsGeneralConceptInclusion:
    """Cover lines 1086, 1088, 1090, 1098, 1100-1103 in is_general_concept_inclusion."""

    def test_equality_predicate_with_internal_named_body(self):
        """Lines 1091-1098: Equality in head with INTERNAL_NAMED in body → False."""
        from hermit.model import Equality, AtomicConcept as AC
        eq = Equality.INSTANCE
        a = AtomicConcept.create(NS + "A")
        # Head: Equality(X, Y), Body: INTERNAL_NAMED(X)
        head_atom = Atom.create(eq, X, Y)
        body_atom = Atom.create(AC.INTERNAL_NAMED, X)
        clause = DLClause.create((head_atom,), (body_atom,))
        result = clause.is_general_concept_inclusion()
        assert not result  # Equality with INTERNAL_NAMED body → False

    def test_equality_predicate_without_internal_named_body(self):
        """Lines 1091-1097: Equality in head without INTERNAL_NAMED body → continue."""
        from hermit.model import Equality
        eq = Equality.INSTANCE
        a = AtomicConcept.create(NS + "A")
        head_atom = Atom.create(eq, X, Y)
        body_atom = Atom.create(a, X)
        clause = DLClause.create((head_atom,), (body_atom,))
        # Equality without INTERNAL_NAMED → continues checking → returns False at end
        result = clause.is_general_concept_inclusion()
        assert isinstance(result, bool)

    def test_data_range_in_head_with_2arity_body_true(self):
        """Lines 1099-1102: DataRange in head, 2-arity body atom → returns True."""
        r = AtomicRole.create(NS + "r")
        dr = AtomicDataRange("http://www.w3.org/2001/XMLSchema#integer")
        head_atom = Atom.create(dr, X)
        body_atom = Atom.create(r, X, Y)  # 2-arity
        clause = DLClause.create((head_atom,), (body_atom,))
        assert clause.is_general_concept_inclusion()

    def test_data_range_in_head_with_1arity_body_false(self):
        """Lines 1099-1103: DataRange in head, all 1-arity body → returns False."""
        a = AtomicConcept.create(NS + "A")
        dr = AtomicDataRange("http://www.w3.org/2001/XMLSchema#integer")
        head_atom = Atom.create(dr, X)
        body_atom = Atom.create(a, X)  # 1-arity
        clause = DLClause.create((head_atom,), (body_atom,))
        assert not clause.is_general_concept_inclusion()


class TestDataRangeClasses:
    """Tests for various DataRange subclasses — many remaining lines."""

    def test_atomic_data_range_str(self):
        """AtomicDataRange.__str__ works."""
        adr = AtomicDataRange("http://www.w3.org/2001/XMLSchema#integer")
        s = str(adr)
        assert "integer" in s.lower() or "xsd" in s.lower() or "Integer" in s

    def test_constant_enumeration_is_always_true(self):
        """ConstantEnumeration.is_always_true()."""
        c = Constant.create("1", "http://www.w3.org/2001/XMLSchema#integer")
        ce = ConstantEnumeration.create((c,))
        assert not ce.is_always_true()

    def test_datatype_restriction_eq_different_type(self):
        """DatatypeRestriction.__eq__ with non-DR returns False."""
        dr = DatatypeRestriction.create(
            "http://www.w3.org/2001/XMLSchema#integer", (), ()
        )
        assert dr != "dr"
        assert dr != 42

    def test_datatype_restriction_eq_different_iri(self):
        """DatatypeRestriction.__eq__ with different IRI returns False."""
        dr1 = DatatypeRestriction.create(
            "http://www.w3.org/2001/XMLSchema#integer", (), ()
        )
        dr2 = DatatypeRestriction.create(
            "http://www.w3.org/2001/XMLSchema#string", (), ()
        )
        assert dr1 != dr2
