"""Numeric (owl:real family) datatype reasoning tests.

Builds small DL ontologies directly from internal model objects and checks
that the tableau detects (in)consistency through the datatype manager.
"""

from __future__ import annotations

import pytest

from hermit.configuration import Configuration
from hermit.model import (
    Atom,
    AtLeastDataRange,
    AtomicConcept,
    AtomicNegationDataRange,
    AtomicRole,
    Constant,
    ConstantEnumeration,
    DatatypeRestriction,
    DLClause,
    DLOntology,
    Individual,
    Variable,
)
from hermit.reasoner import Reasoner

XSD = "http://www.w3.org/2001/XMLSchema#"
OWL = "http://www.w3.org/2002/07/owl#"

X = Variable.create("X")
Y = Variable.create("Y")


def _is_consistent(clauses: list[DLClause], facts: list[Atom]) -> bool:
    onto = DLOntology(
        "urn:test:datatypes", frozenset(clauses), frozenset(facts), frozenset()
    )
    config = Configuration()
    config.throw_inconsistent_ontology_exception = False
    reasoner = Reasoner(onto, config)
    try:
        return bool(reasoner.is_consistent())
    finally:
        reasoner.dispose()


def _plain(datatype_iri: str) -> DatatypeRestriction:
    return DatatypeRestriction.create(datatype_iri, (), ())


def _restricted(
    datatype_iri: str, facets: dict[str, tuple[str, str]]
) -> DatatypeRestriction:
    facet_uris = tuple(facets.keys())
    facet_values = tuple(
        Constant.create(lexical, value_iri) for lexical, value_iri in facets.values()
    )
    return DatatypeRestriction.create(datatype_iri, facet_uris, facet_values)


def _all_some_case(
    all_range: object, some_range: object
) -> tuple[list[DLClause], list[Atom]]:
    """A(a), A ⊑ ∀dp.all_range, A ⊑ ∃dp.some_range."""
    a_concept = AtomicConcept.create("urn:test:A")
    dp = AtomicRole.create("urn:test:dp")
    individual = Individual.create("urn:test:a")
    clauses = [
        DLClause.create(
            (Atom.create(all_range, Y),),
            (Atom.create(a_concept, X), Atom.create(dp, X, Y)),
        ),
        DLClause.create(
            (Atom.create(AtLeastDataRange.create(1, dp, some_range), X),),
            (Atom.create(a_concept, X),),
        ),
    ]
    facts = [Atom.create(a_concept, individual)]
    return clauses, facts


class TestIntegerBounds:
    def test_byte_excludes_large_integer(self):
        clauses, facts = _all_some_case(
            _plain(XSD + "byte"),
            ConstantEnumeration.create([Constant.create("6542145", XSD + "integer")]),
        )
        assert not _is_consistent(clauses, facts)

    def test_byte_admits_small_integer(self):
        clauses, facts = _all_some_case(
            _plain(XSD + "byte"),
            ConstantEnumeration.create([Constant.create("100", XSD + "integer")]),
        )
        assert _is_consistent(clauses, facts)

    def test_unsigned_int_excludes_negative(self):
        clauses, facts = _all_some_case(
            _plain(XSD + "unsignedInt"),
            ConstantEnumeration.create([Constant.create("-1", XSD + "integer")]),
        )
        assert not _is_consistent(clauses, facts)

    def test_plus_and_minus_zero_integer_are_equal(self):
        clauses, facts = _all_some_case(
            ConstantEnumeration.create([Constant.create("0", XSD + "integer")]),
            ConstantEnumeration.create([Constant.create("-0", XSD + "integer")]),
        )
        assert _is_consistent(clauses, facts)


class TestFacetIntervals:
    def test_min_above_max_is_inconsistent(self):
        clauses, facts = _all_some_case(
            _restricted(
                XSD + "integer",
                {XSD + "maxInclusive": ("10", XSD + "integer")},
            ),
            _restricted(
                XSD + "integer",
                {XSD + "minInclusive": ("18", XSD + "integer")},
            ),
        )
        assert not _is_consistent(clauses, facts)

    def test_compatible_min_max_is_consistent(self):
        clauses, facts = _all_some_case(
            _restricted(
                XSD + "integer",
                {XSD + "maxInclusive": ("20", XSD + "integer")},
            ),
            _restricted(
                XSD + "integer",
                {XSD + "minInclusive": ("18", XSD + "integer")},
            ),
        )
        assert _is_consistent(clauses, facts)

    def test_integer_gap_between_exclusive_bounds_is_inconsistent(self):
        a_concept = AtomicConcept.create("urn:test:A")
        dp = AtomicRole.create("urn:test:dp")
        individual = Individual.create("urn:test:a")
        restriction = _restricted(
            XSD + "integer",
            {
                XSD + "minExclusive": ("4", XSD + "integer"),
                XSD + "maxExclusive": ("5", XSD + "integer"),
            },
        )
        clauses = [
            DLClause.create(
                (Atom.create(AtLeastDataRange.create(1, dp, restriction), X),),
                (Atom.create(a_concept, X),),
            ),
        ]
        facts = [Atom.create(a_concept, individual)]
        assert not _is_consistent(clauses, facts)

    def test_decimal_between_exclusive_integer_bounds_is_consistent(self):
        a_concept = AtomicConcept.create("urn:test:A")
        dp = AtomicRole.create("urn:test:dp")
        individual = Individual.create("urn:test:a")
        restriction = _restricted(
            XSD + "decimal",
            {
                XSD + "minExclusive": ("4", XSD + "integer"),
                XSD + "maxExclusive": ("5", XSD + "integer"),
            },
        )
        clauses = [
            DLClause.create(
                (Atom.create(AtLeastDataRange.create(1, dp, restriction), X),),
                (Atom.create(a_concept, X),),
            ),
        ]
        facts = [Atom.create(a_concept, individual)]
        assert _is_consistent(clauses, facts)


class TestEnumerationsAndComplement:
    def test_intersecting_enumerations_with_complement_is_inconsistent(self):
        # ∀dp.{3,4} ⊓ ∀dp.{2,3} ⊓ ∃dp.¬{3} is unsatisfiable.
        a_concept = AtomicConcept.create("urn:test:A")
        dp = AtomicRole.create("urn:test:dp")
        individual = Individual.create("urn:test:a")
        enum34 = ConstantEnumeration.create([
            Constant.create("3", XSD + "integer"),
            Constant.create("4", XSD + "integer"),
        ])
        enum23 = ConstantEnumeration.create([
            Constant.create("2", XSD + "integer"),
            Constant.create("3", XSD + "integer"),
        ])
        not3 = AtomicNegationDataRange.create(
            ConstantEnumeration.create([Constant.create("3", XSD + "integer")])
        )
        clauses = [
            DLClause.create(
                (Atom.create(enum34, Y),),
                (Atom.create(a_concept, X), Atom.create(dp, X, Y)),
            ),
            DLClause.create(
                (Atom.create(enum23, Y),),
                (Atom.create(a_concept, X), Atom.create(dp, X, Y)),
            ),
            DLClause.create(
                (Atom.create(AtLeastDataRange.create(1, dp, not3), X),),
                (Atom.create(a_concept, X),),
            ),
        ]
        facts = [Atom.create(a_concept, individual)]
        assert not _is_consistent(clauses, facts)

    def test_intersecting_enumerations_without_complement_is_consistent(self):
        a_concept = AtomicConcept.create("urn:test:A")
        dp = AtomicRole.create("urn:test:dp")
        individual = Individual.create("urn:test:a")
        enum34 = ConstantEnumeration.create([
            Constant.create("3", XSD + "integer"),
            Constant.create("4", XSD + "integer"),
        ])
        enum23 = ConstantEnumeration.create([
            Constant.create("2", XSD + "integer"),
            Constant.create("3", XSD + "integer"),
        ])
        clauses = [
            DLClause.create(
                (Atom.create(enum34, Y),),
                (Atom.create(a_concept, X), Atom.create(dp, X, Y)),
            ),
            DLClause.create(
                (Atom.create(enum23, Y),),
                (Atom.create(a_concept, X), Atom.create(dp, X, Y)),
            ),
            DLClause.create(
                (Atom.create(AtLeastDataRange.create(1, dp, enum23), X),),
                (Atom.create(a_concept, X),),
            ),
        ]
        facts = [Atom.create(a_concept, individual)]
        assert _is_consistent(clauses, facts)

    def test_enumerations_with_restriction_above_intersection_is_inconsistent(self):
        # ∀dp.{3,4} ⊓ ∀dp.{2,3} ⊓ ∃dp.(≥4) is unsatisfiable.
        a_concept = AtomicConcept.create("urn:test:A")
        dp = AtomicRole.create("urn:test:dp")
        individual = Individual.create("urn:test:a")
        enum34 = ConstantEnumeration.create([
            Constant.create("3", XSD + "integer"),
            Constant.create("4", XSD + "integer"),
        ])
        enum23 = ConstantEnumeration.create([
            Constant.create("2", XSD + "integer"),
            Constant.create("3", XSD + "integer"),
        ])
        at_least_4 = _restricted(
            XSD + "integer", {XSD + "minInclusive": ("4", XSD + "integer")}
        )
        clauses = [
            DLClause.create(
                (Atom.create(enum34, Y),),
                (Atom.create(a_concept, X), Atom.create(dp, X, Y)),
            ),
            DLClause.create(
                (Atom.create(enum23, Y),),
                (Atom.create(a_concept, X), Atom.create(dp, X, Y)),
            ),
            DLClause.create(
                (Atom.create(AtLeastDataRange.create(1, dp, at_least_4), X),),
                (Atom.create(a_concept, X),),
            ),
        ]
        facts = [Atom.create(a_concept, individual)]
        assert not _is_consistent(clauses, facts)


class TestRationalEquality:
    def test_decimal_half_equals_rational_half(self):
        # ∀dp.{0.5, 1/2} with ≥2 dp fillers is unsatisfiable (one value).
        a_concept = AtomicConcept.create("urn:test:A")
        dp = AtomicRole.create("urn:test:dp")
        individual = Individual.create("urn:test:a")
        enum = ConstantEnumeration.create([
            Constant.create("0.5", XSD + "decimal"),
            Constant.create("1/2", OWL + "rational"),
        ])
        clauses = [
            DLClause.create(
                (Atom.create(enum, Y),),
                (Atom.create(a_concept, X), Atom.create(dp, X, Y)),
            ),
            DLClause.create(
                (Atom.create(AtLeastDataRange.create(2, dp, enum), X),),
                (Atom.create(a_concept, X),),
            ),
        ]
        facts = [Atom.create(a_concept, individual)]
        assert not _is_consistent(clauses, facts)

    def test_two_distinct_rationals_satisfy_cardinality_two(self):
        a_concept = AtomicConcept.create("urn:test:A")
        dp = AtomicRole.create("urn:test:dp")
        individual = Individual.create("urn:test:a")
        enum = ConstantEnumeration.create([
            Constant.create("0.5", XSD + "decimal"),
            Constant.create("1/3", OWL + "rational"),
        ])
        clauses = [
            DLClause.create(
                (Atom.create(enum, Y),),
                (Atom.create(a_concept, X), Atom.create(dp, X, Y)),
            ),
            DLClause.create(
                (Atom.create(AtLeastDataRange.create(2, dp, enum), X),),
                (Atom.create(a_concept, X),),
            ),
        ]
        facts = [Atom.create(a_concept, individual)]
        assert _is_consistent(clauses, facts)


class TestValueSpaceProperties:
    def test_rational_parse_reduces(self):
        from hermit.datatypes.owlreal import parse_rational

        assert parse_rational("2/4") == parse_rational("1/2")

    def test_rational_rejects_zero_denominator(self):
        from hermit.datatypes.owlreal import parse_rational
        from hermit.datatypes.registry import MalformedLiteralException

        with pytest.raises(MalformedLiteralException):
            parse_rational("1/0")

    def test_integer_interval_cardinality_is_exact(self):
        from hermit.datatypes.owlreal import BigRational, OWLRealDatatypeHandler

        handler = OWLRealDatatypeHandler()
        subset = handler.create_value_space_subset(
            XSD + "integer",
            (XSD + "minInclusive", XSD + "maxInclusive"),
            (BigRational(1), BigRational(3)),
        )
        assert subset.has_cardinality_at_least(3)
        assert not subset.has_cardinality_at_least(4)
        values: list[object] = []
        subset.enumerate_data_values(values)
        assert sorted(v.fraction for v in values) == [1, 2, 3]  # type: ignore[attr-defined]

    def test_minus_infinity_float_not_in_owl_real(self):
        from hermit.datatypes.owlreal import OWLRealDatatypeHandler
        from hermit.datatypes.floatnum import FloatValue

        handler = OWLRealDatatypeHandler()
        subset = handler.create_value_space_subset(OWL + "real", (), ())
        assert not subset.contains_data_value(FloatValue.parse("-INF"))
