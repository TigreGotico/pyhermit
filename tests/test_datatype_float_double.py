"""xsd:float / xsd:double datatype reasoning tests.

Covers the discrete bit-level value spaces: discreteness of consecutive
floats, distinct +0.0/-0.0, INF endpoints, and NaN handling.
"""

from __future__ import annotations

from hermit.configuration import Configuration
from hermit.model import (
    Atom,
    AtLeastDataRange,
    AtomicConcept,
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

X = Variable.create("X")
Y = Variable.create("Y")

SMALLEST_POSITIVE_FLOAT = "1.401298464324817e-45"


def _is_consistent(clauses: list[DLClause], facts: list[Atom]) -> bool:
    onto = DLOntology(
        "urn:test:float", frozenset(clauses), frozenset(facts), frozenset()
    )
    config = Configuration()
    config.throw_inconsistent_ontology_exception = False
    reasoner = Reasoner(onto, config)
    try:
        return bool(reasoner.is_consistent())
    finally:
        reasoner.dispose()


def _exists_case(data_range: object) -> tuple[list[DLClause], list[Atom]]:
    a_concept = AtomicConcept.create("urn:test:A")
    dp = AtomicRole.create("urn:test:dp")
    individual = Individual.create("urn:test:a")
    clauses = [
        DLClause.create(
            (Atom.create(AtLeastDataRange.create(1, dp, data_range), X),),
            (Atom.create(a_concept, X),),
        ),
    ]
    facts = [Atom.create(a_concept, individual)]
    return clauses, facts


def _float_restriction(facets: dict[str, str]) -> DatatypeRestriction:
    facet_uris = tuple(facets.keys())
    facet_values = tuple(
        Constant.create(lexical, XSD + "float") for lexical in facets.values()
    )
    return DatatypeRestriction.create(XSD + "float", facet_uris, facet_values)


class TestFloatDiscreteness:
    def test_no_float_strictly_between_zero_and_smallest_subnormal(self):
        clauses, facts = _exists_case(
            _float_restriction({
                XSD + "minExclusive": "0.0",
                XSD + "maxExclusive": SMALLEST_POSITIVE_FLOAT,
            })
        )
        assert not _is_consistent(clauses, facts)

    def test_float_exists_between_zero_inclusive_and_smallest_subnormal(self):
        clauses, facts = _exists_case(
            _float_restriction({
                XSD + "minInclusive": "0.0",
                XSD + "maxExclusive": SMALLEST_POSITIVE_FLOAT,
            })
        )
        assert _is_consistent(clauses, facts)

    def test_empty_float_facet_interval_is_inconsistent(self):
        clauses, facts = _exists_case(
            _float_restriction({
                XSD + "minInclusive": "2.0",
                XSD + "maxInclusive": "1.0",
            })
        )
        assert not _is_consistent(clauses, facts)


class TestSignedZeros:
    def test_plus_and_minus_zero_float_are_distinct(self):
        # ∀dp.{+0.0f} ⊓ ∃dp.{-0.0f} is unsatisfiable.
        a_concept = AtomicConcept.create("urn:test:A")
        dp = AtomicRole.create("urn:test:dp")
        individual = Individual.create("urn:test:a")
        plus_zero = ConstantEnumeration.create([Constant.create("0.0", XSD + "float")])
        minus_zero = ConstantEnumeration.create([Constant.create("-0.0", XSD + "float")])
        clauses = [
            DLClause.create(
                (Atom.create(plus_zero, Y),),
                (Atom.create(a_concept, X), Atom.create(dp, X, Y)),
            ),
            DLClause.create(
                (Atom.create(AtLeastDataRange.create(1, dp, minus_zero), X),),
                (Atom.create(a_concept, X),),
            ),
        ]
        facts = [Atom.create(a_concept, individual)]
        assert not _is_consistent(clauses, facts)

    def test_same_lexical_zero_floats_are_equal(self):
        a_concept = AtomicConcept.create("urn:test:A")
        dp = AtomicRole.create("urn:test:dp")
        individual = Individual.create("urn:test:a")
        plus_zero = ConstantEnumeration.create([Constant.create("0.0", XSD + "float")])
        clauses = [
            DLClause.create(
                (Atom.create(plus_zero, Y),),
                (Atom.create(a_concept, X), Atom.create(dp, X, Y)),
            ),
            DLClause.create(
                (Atom.create(AtLeastDataRange.create(1, dp, plus_zero), X),),
                (Atom.create(a_concept, X),),
            ),
        ]
        facts = [Atom.create(a_concept, individual)]
        assert _is_consistent(clauses, facts)

    def test_minus_zero_below_min_inclusive_plus_zero(self):
        # minInclusive +0.0 normalises to -0.0, so -0.0 conforms.
        clauses, facts = _exists_case(
            _float_restriction({XSD + "minInclusive": "0.0"})
        )
        assert _is_consistent(clauses, facts)


class TestFloatValueSemantics:
    def test_zero_bit_patterns_distinct(self):
        from hermit.datatypes.floatnum import FloatValue

        assert FloatValue.parse("0.0") != FloatValue.parse("-0.0")
        assert FloatValue.parse("0") == FloatValue.parse("0.0")

    def test_nan_equals_itself(self):
        from hermit.datatypes.floatnum import FloatValue

        assert FloatValue.parse("NaN") == FloatValue.parse("NaN")

    def test_infinities_parse(self):
        from hermit.datatypes.floatnum import FloatValue
        import math

        assert FloatValue.parse("INF").value == math.inf
        assert FloatValue.parse("-INF").value == -math.inf

    def test_float_and_double_values_are_distinct(self):
        from hermit.datatypes.doublenum import DoubleValue
        from hermit.datatypes.floatnum import FloatValue

        assert FloatValue.parse("1.0") != DoubleValue.parse("1.0")

    def test_float_cardinality_counts_discrete_values(self):
        from hermit.datatypes.floatnum import FloatDatatypeHandler, FloatValue

        handler = FloatDatatypeHandler()
        subset = handler.create_value_space_subset(
            XSD + "float",
            (XSD + "minInclusive", XSD + "maxInclusive"),
            (FloatValue.parse("-0.0"), FloatValue.parse("0.0")),
        )
        # Exactly two values: -0.0 and +0.0.
        assert subset.has_cardinality_at_least(2)
        assert not subset.has_cardinality_at_least(3)
        values: list[object] = []
        subset.enumerate_data_values(values)
        assert len(values) == 2


class TestDoubleDiscreteness:
    def test_no_double_strictly_between_adjacent_values(self):
        from hermit.datatypes.doublenum import (
            DoubleValue,
            bits_to_double,
            next_double_bits,
        )

        lower = DoubleValue.parse("1.0")
        upper = bits_to_double(next_double_bits(lower.bits))
        facets = {
            XSD + "minExclusive": "1.0",
            XSD + "maxExclusive": repr(upper),
        }
        facet_uris = tuple(facets.keys())
        facet_values = tuple(
            Constant.create(lexical, XSD + "double") for lexical in facets.values()
        )
        restriction = DatatypeRestriction.create(
            XSD + "double", facet_uris, facet_values
        )
        clauses, facts = _exists_case(restriction)
        assert not _is_consistent(clauses, facts)

    def test_double_exists_in_inclusive_interval(self):
        facets = {
            XSD + "minInclusive": "1.0",
            XSD + "maxInclusive": "2.0",
        }
        facet_uris = tuple(facets.keys())
        facet_values = tuple(
            Constant.create(lexical, XSD + "double") for lexical in facets.values()
        )
        restriction = DatatypeRestriction.create(
            XSD + "double", facet_uris, facet_values
        )
        clauses, facts = _exists_case(restriction)
        assert _is_consistent(clauses, facts)
