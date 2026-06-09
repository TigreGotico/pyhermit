"""xsd:dateTime datatype reasoning tests.

Covers the timeline value space: facet intervals, timezone handling, and the
±14h maximum timezone correction between timezoned and timezoneless values.
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


def _is_consistent(clauses: list[DLClause], facts: list[Atom]) -> bool:
    onto = DLOntology(
        "urn:test:datetime", frozenset(clauses), frozenset(facts), frozenset()
    )
    config = Configuration()
    config.throw_inconsistent_ontology_exception = False
    reasoner = Reasoner(onto, config)
    try:
        return bool(reasoner.is_consistent())
    finally:
        reasoner.dispose()


def _restriction(facets: dict[str, str]) -> DatatypeRestriction:
    facet_uris = tuple(facets.keys())
    facet_values = tuple(
        Constant.create(lexical, XSD + "dateTime") for lexical in facets.values()
    )
    return DatatypeRestriction.create(XSD + "dateTime", facet_uris, facet_values)


def _value_vs_range_case(
    value_lexical: str, facets: dict[str, str]
) -> tuple[list[DLClause], list[Atom]]:
    """A(a), A ⊑ ∃dp.{value}, A ⊑ ∀dp.restriction."""
    a_concept = AtomicConcept.create("urn:test:A")
    dp = AtomicRole.create("urn:test:dp")
    individual = Individual.create("urn:test:a")
    enum = ConstantEnumeration.create(
        [Constant.create(value_lexical, XSD + "dateTime")]
    )
    clauses = [
        DLClause.create(
            (Atom.create(AtLeastDataRange.create(1, dp, enum), X),),
            (Atom.create(a_concept, X),),
        ),
        DLClause.create(
            (Atom.create(_restriction(facets), Y),),
            (Atom.create(a_concept, X), Atom.create(dp, X, Y)),
        ),
    ]
    facts = [Atom.create(a_concept, individual)]
    return clauses, facts


class TestDateTimeIntervals:
    def test_value_outside_min_max_window_is_inconsistent(self):
        clauses, facts = _value_vs_range_case(
            "2007-10-08T20:44:11.656+01:00",
            {
                XSD + "minInclusive": "2008-07-08T20:44:11.656+01:00",
                XSD + "maxInclusive": "2008-10-08T20:44:11.656+01:00",
            },
        )
        assert not _is_consistent(clauses, facts)

    def test_value_inside_min_max_window_is_consistent(self):
        clauses, facts = _value_vs_range_case(
            "2008-08-08T20:44:11.656+01:00",
            {
                XSD + "minInclusive": "2008-07-08T20:44:11.656+01:00",
                XSD + "maxInclusive": "2008-10-08T20:44:11.656+01:00",
            },
        )
        assert _is_consistent(clauses, facts)

    def test_contradicting_min_max_facets_are_inconsistent(self):
        a_concept = AtomicConcept.create("urn:test:A")
        dp = AtomicRole.create("urn:test:dp")
        individual = Individual.create("urn:test:a")
        restriction = _restriction({
            XSD + "minInclusive": "2009-01-01T00:00:00Z",
            XSD + "maxInclusive": "2008-01-01T00:00:00Z",
        })
        clauses = [
            DLClause.create(
                (Atom.create(AtLeastDataRange.create(1, dp, restriction), X),),
                (Atom.create(a_concept, X),),
            ),
        ]
        facts = [Atom.create(a_concept, individual)]
        assert not _is_consistent(clauses, facts)

    def test_timezone_offset_normalises_to_timeline(self):
        # 12:00Z and 13:00+01:00 denote the same time-line point.
        clauses, facts = _value_vs_range_case(
            "2008-01-01T13:00:00+01:00",
            {
                XSD + "minInclusive": "2008-01-01T12:00:00Z",
                XSD + "maxInclusive": "2008-01-01T12:00:00Z",
            },
        )
        assert _is_consistent(clauses, facts)


class TestDateTimeValueSemantics:
    def test_equal_timeline_same_timezone_is_equal(self):
        from hermit.datatypes.datetime import DateTimeValue

        value1 = DateTimeValue.parse("2008-01-01T13:00:00+01:00")
        value2 = DateTimeValue.parse("2008-01-01T13:00:00+01:00")
        assert value1 == value2

    def test_equal_timeline_different_timezone_is_distinct_value(self):
        from hermit.datatypes.datetime import DateTimeValue

        with_z = DateTimeValue.parse("2008-01-01T12:00:00Z")
        with_offset = DateTimeValue.parse("2008-01-01T13:00:00+01:00")
        assert with_z is not None and with_offset is not None
        assert with_z.time_on_timeline == with_offset.time_on_timeline
        assert with_z != with_offset

    def test_timezoneless_value_is_distinct_from_timezoned(self):
        from hermit.datatypes.datetime import DateTimeValue

        no_tz = DateTimeValue.parse("2008-01-01T12:00:00")
        with_tz = DateTimeValue.parse("2008-01-01T12:00:00Z")
        assert no_tz != with_tz

    def test_invalid_lexical_forms_rejected(self):
        from hermit.datatypes.datetime import DateTimeValue

        assert DateTimeValue.parse("not-a-date") is None
        assert DateTimeValue.parse("2008-13-01T00:00:00") is None
        assert DateTimeValue.parse("2008-02-30T00:00:00") is None
        assert DateTimeValue.parse("2008-01-01T24:00:01") is None

    def test_datetime_stamp_requires_timezone(self):
        import pytest

        from hermit.datatypes.datetime import DateTimeDatatypeHandler
        from hermit.datatypes.registry import MalformedLiteralException

        handler = DateTimeDatatypeHandler()
        handler.parse_data_value("2008-01-01T12:00:00Z", XSD + "dateTimeStamp")
        with pytest.raises(MalformedLiteralException):
            handler.parse_data_value("2008-01-01T12:00:00", XSD + "dateTimeStamp")

    def test_timezoneless_bound_constrains_timezoned_with_correction(self):
        # A timezoneless facet bound restricts timezoned values only beyond
        # the ±14h maximum timezone correction.
        from hermit.datatypes.datetime import DateTimeDatatypeHandler, DateTimeValue

        handler = DateTimeDatatypeHandler()
        subset = handler.create_value_space_subset(
            XSD + "dateTime",
            (XSD + "minInclusive",),
            (Constant.create("2008-01-01T12:00:00", XSD + "dateTime"),),
        )
        clearly_before = DateTimeValue.parse("2008-01-01T00:00:00+14:00")
        clearly_after = DateTimeValue.parse("2008-01-02T12:00:00Z")
        within_correction = DateTimeValue.parse("2008-01-01T12:00:00Z")
        assert not subset.contains_data_value(clearly_before)
        assert subset.contains_data_value(clearly_after)
        # Comparison is indeterminate within the correction window, so the
        # timezoned value does not definitely satisfy the bound.
        assert not subset.contains_data_value(within_correction)
