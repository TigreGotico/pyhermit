"""xsd:dateTime datatype handler.

Implements the xsd:dateTime / xsd:dateTimeStamp value space following Java
HermiT: values map to a millisecond position on the time line, timezoned and
timezoneless values live in separate interval families, and facet bounds use
the maximum timezone correction of ±14 hours when the facet value and the
restricted space differ in timezone presence.
"""
from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Any

from hermit.datatypes.registry import (
    DatatypeHandler,
    DatatypeRegistry,
    MalformedLiteralException,
    UnsupportedFacetException,
    ValueSpaceSubset,
    facet_data_value,
)

XSD_NS = "http://www.w3.org/2001/XMLSchema#"
XSD_DATE_TIME = XSD_NS + "dateTime"
XSD_DATE_TIME_STAMP = XSD_NS + "dateTimeStamp"

MAX_TIME_ZONE_CORRECTION = 14 * 60 * 60 * 1000

_TIME_MIN = -(2 ** 63)
_TIME_MAX = 2 ** 63 - 1

_DATE_TIME_PATTERN = re.compile(
    r"(-?[0-9]{4,})"
    r"-([0-9]{2})"
    r"-([0-9]{2})"
    r"T([0-9]{2})"
    r":([0-9]{2})"
    r":([0-9]{2})(?:[.]([0-9]{1,3}))?"
    r"((Z)|(([+]|-)([0-9]{2}):([0-9]{2})))?"
)


def _trunc_div(dividend: int, divisor: int) -> int:
    """Integer division truncating toward zero."""
    quotient = abs(dividend) // divisor
    return quotient if dividend >= 0 else -quotient


def _days_in_month(year: int, month: int) -> int:
    if month == 2:
        if year % 4 != 0 or (year % 100 == 0 and year % 400 != 0):
            return 28
        return 29
    if month in (4, 6, 9, 11):
        return 30
    return 31


def _time_on_timeline_raw(
    year: int, month: int, day: int, hour: int, minute: int, second: int, millisecond: int
) -> int:
    year_minus_one = year - 1
    time_on_timeline = 31536000 * year_minus_one
    time_on_timeline += 86400 * (
        year_minus_one // 400 - year_minus_one // 100 + year_minus_one // 4
    )
    for month_index in range(1, month):
        time_on_timeline += 86400 * _days_in_month(year, month_index)
    time_on_timeline += 86400 * (day - 1)
    time_on_timeline += 3600 * hour + 60 * minute + second
    return time_on_timeline * 1000 + millisecond


class DateTimeValue:
    """An xsd:dateTime data value (position on the time line + timezone)."""

    __slots__ = ("_time_on_timeline", "_last_day_instant", "_time_zone_offset")

    def __init__(
        self,
        time_on_timeline: int,
        last_day_instant: bool,
        time_zone_offset: int | None,
    ) -> None:
        self._time_on_timeline = time_on_timeline
        self._last_day_instant = last_day_instant
        self._time_zone_offset = time_zone_offset

    @classmethod
    def from_components(
        cls,
        year: int,
        month: int,
        day: int,
        hour: int,
        minute: int,
        second: int,
        millisecond: int,
        time_zone_offset: int | None,
    ) -> DateTimeValue:
        raw = _time_on_timeline_raw(year, month, day, hour, minute, second, millisecond)
        if time_zone_offset is not None:
            raw -= time_zone_offset * 60 * 1000
        last_day_instant = hour == 24 and minute == 0 and second == 0 and millisecond == 0
        return cls(raw, last_day_instant, time_zone_offset)

    @property
    def time_on_timeline(self) -> int:
        return self._time_on_timeline

    @property
    def last_day_instant(self) -> bool:
        return self._last_day_instant

    def has_time_zone_offset(self) -> bool:
        return self._time_zone_offset is not None

    @property
    def time_zone_offset(self) -> int | None:
        return self._time_zone_offset

    def __hash__(self) -> int:
        return hash((
            self._time_on_timeline, self._last_day_instant, self._time_zone_offset,
        ))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DateTimeValue):
            return (
                self._time_on_timeline == other._time_on_timeline
                and self._last_day_instant == other._last_day_instant
                and self._time_zone_offset == other._time_zone_offset
            )
        return False

    def __repr__(self) -> str:
        return (
            f"DateTimeValue(timeline={self._time_on_timeline}, "
            f"tz={self._time_zone_offset})"
        )

    @staticmethod
    def parse(lexical_form: str) -> DateTimeValue | None:
        match = _DATE_TIME_PATTERN.fullmatch(lexical_form.strip())
        if match is None:
            return None
        try:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            hour = int(match.group(4))
            minute = int(match.group(5))
            second = int(match.group(6))
            millisecond_text = match.group(7)
            if millisecond_text is not None:
                millisecond = int(millisecond_text.ljust(3, "0"))
            else:
                millisecond = 0
            if (
                year < -9999 or year > 9999
                or month <= 0 or month > 12
                or day <= 0 or day > _days_in_month(year, month)
                or hour < 0 or hour > 24
                or (hour == 24 and (minute != 0 or second != 0 or millisecond != 0))
                or minute < 0 or minute >= 60
                or second < 0 or second >= 60
                or millisecond < 0 or millisecond >= 1000
            ):
                return None
            time_zone_offset: int | None
            if match.group(8) is None:
                time_zone_offset = None
            elif match.group(9) is not None:
                time_zone_offset = 0
            else:
                sign = -1 if match.group(11) == "-" else 1
                tz_hour = int(match.group(12))
                tz_minute = int(match.group(13))
                if (
                    tz_hour < 0 or tz_hour > 14
                    or (tz_hour == 14 and tz_minute != 0)
                    or tz_minute < 0 or tz_minute >= 60
                ):
                    return None
                time_zone_offset = sign * (tz_hour * 60 + tz_minute)
            return DateTimeValue.from_components(
                year, month, day, hour, minute, second, millisecond, time_zone_offset
            )
        except ValueError:
            return None

    @staticmethod
    def is_last_day_instant(time_on_timeline: int) -> bool:
        return time_on_timeline % (1000 * 60 * 60 * 24) == 0

    @staticmethod
    def seconds_are_zero(time_on_timeline: int) -> bool:
        return time_on_timeline % (1000 * 60) == 0

    @staticmethod
    def get_minutes_in_day(time_on_timeline: int) -> int:
        # Truncating division and sign-preserving remainder.
        minutes = _trunc_div(time_on_timeline, 1000 * 60)
        return minutes - _trunc_div(minutes, 24 * 60) * (24 * 60)


class IntervalType(Enum):
    WITH_TIMEZONE = 0
    WITHOUT_TIMEZONE = 1


class DateTimeBoundType(Enum):
    INCLUSIVE = 0
    EXCLUSIVE = 1

    def get_complement(self) -> DateTimeBoundType:
        if self is DateTimeBoundType.INCLUSIVE:
            return DateTimeBoundType.EXCLUSIVE
        return DateTimeBoundType.INCLUSIVE

    @staticmethod
    def get_more_restrictive(
        bound_type1: DateTimeBoundType, bound_type2: DateTimeBoundType
    ) -> DateTimeBoundType:
        if bound_type1 is DateTimeBoundType.EXCLUSIVE or bound_type2 is DateTimeBoundType.EXCLUSIVE:
            return DateTimeBoundType.EXCLUSIVE
        return DateTimeBoundType.INCLUSIVE


class DateTimeInterval:
    """An interval on the time line for one timezone-presence family."""

    __slots__ = (
        "m_interval_type",
        "m_lower_bound",
        "m_lower_bound_type",
        "m_upper_bound",
        "m_upper_bound_type",
    )

    def __init__(
        self,
        interval_type: IntervalType,
        lower_bound: int,
        lower_bound_type: DateTimeBoundType,
        upper_bound: int,
        upper_bound_type: DateTimeBoundType,
    ) -> None:
        self.m_interval_type = interval_type
        self.m_lower_bound = lower_bound
        self.m_lower_bound_type = lower_bound_type
        self.m_upper_bound = upper_bound
        self.m_upper_bound_type = upper_bound_type

    def intersect_with(self, that: DateTimeInterval) -> DateTimeInterval | None:
        if self.m_interval_type is not that.m_interval_type:
            return None
        if self.m_lower_bound < that.m_lower_bound:
            new_lower_bound = that.m_lower_bound
            new_lower_bound_type = that.m_lower_bound_type
        elif self.m_lower_bound > that.m_lower_bound:
            new_lower_bound = self.m_lower_bound
            new_lower_bound_type = self.m_lower_bound_type
        else:
            new_lower_bound = self.m_lower_bound
            new_lower_bound_type = DateTimeBoundType.get_more_restrictive(
                self.m_lower_bound_type, that.m_lower_bound_type
            )
        if self.m_upper_bound < that.m_upper_bound:
            new_upper_bound = self.m_upper_bound
            new_upper_bound_type = self.m_upper_bound_type
        elif self.m_upper_bound > that.m_upper_bound:
            new_upper_bound = that.m_upper_bound
            new_upper_bound_type = that.m_upper_bound_type
        else:
            new_upper_bound = self.m_upper_bound
            new_upper_bound_type = DateTimeBoundType.get_more_restrictive(
                self.m_upper_bound_type, that.m_upper_bound_type
            )
        if DateTimeInterval.is_interval_empty(
            new_lower_bound, new_lower_bound_type, new_upper_bound, new_upper_bound_type
        ):
            return None
        if self._is_equal(
            self.m_interval_type, new_lower_bound, new_lower_bound_type,
            new_upper_bound, new_upper_bound_type,
        ):
            return self
        if that._is_equal(
            self.m_interval_type, new_lower_bound, new_lower_bound_type,
            new_upper_bound, new_upper_bound_type,
        ):
            return that
        return DateTimeInterval(
            self.m_interval_type, new_lower_bound, new_lower_bound_type,
            new_upper_bound, new_upper_bound_type,
        )

    def _is_equal(
        self,
        interval_type: IntervalType,
        lower_bound: int,
        lower_bound_type: DateTimeBoundType,
        upper_bound: int,
        upper_bound_type: DateTimeBoundType,
    ) -> bool:
        return (
            self.m_interval_type is interval_type
            and self.m_lower_bound == lower_bound
            and self.m_lower_bound_type is lower_bound_type
            and self.m_upper_bound == upper_bound
            and self.m_upper_bound_type is upper_bound_type
        )

    def subtract_size_from(self, argument: int) -> int:
        if argument <= 0:
            return 0
        if self.m_lower_bound < self.m_upper_bound:
            # Seconds are decimal numbers in principle, so the interval is infinite.
            return 0
        # Since the interval is not empty, both bounds are inclusive.
        if self.m_interval_type is IntervalType.WITHOUT_TIMEZONE:
            number_of_values = 1
            if DateTimeValue.is_last_day_instant(self.m_lower_bound):
                number_of_values += 1
            return max(0, argument - number_of_values)
        number_of_values = 840 + 840 + 1
        if DateTimeValue.seconds_are_zero(self.m_lower_bound):
            minutes_in_day = DateTimeValue.get_minutes_in_day(self.m_lower_bound)
            if self.m_lower_bound >= 0:
                if 0 <= minutes_in_day <= 840:
                    number_of_values += 1
                if 1440 - 840 <= minutes_in_day:
                    number_of_values += 1
            else:
                if -840 <= minutes_in_day <= 0:
                    number_of_values += 1
                if minutes_in_day <= -1440 + 840:
                    number_of_values += 1
        return max(0, argument - number_of_values)

    def contains_date_time(self, date_time: DateTimeValue) -> bool:
        if date_time.has_time_zone_offset():
            if self.m_interval_type is IntervalType.WITHOUT_TIMEZONE:
                return False
        else:
            if self.m_interval_type is IntervalType.WITH_TIMEZONE:
                return False
        time_on_timeline = date_time.time_on_timeline
        if self.m_lower_bound > time_on_timeline or (
            self.m_lower_bound == time_on_timeline
            and self.m_lower_bound_type is DateTimeBoundType.EXCLUSIVE
        ):
            return False
        if self.m_upper_bound < time_on_timeline or (
            self.m_upper_bound == time_on_timeline
            and self.m_upper_bound_type is DateTimeBoundType.EXCLUSIVE
        ):
            return False
        return True

    def enumerate_date_times(self, date_times: list[Any]) -> None:
        if self.m_lower_bound != self.m_upper_bound:
            raise RuntimeError("The data range is infinite.")
        # Since the interval is not empty, both bounds are inclusive.
        if self.m_interval_type is IntervalType.WITHOUT_TIMEZONE:
            date_times.append(DateTimeValue(self.m_lower_bound, False, None))
            if DateTimeValue.is_last_day_instant(self.m_lower_bound):
                date_times.append(DateTimeValue(self.m_lower_bound, True, None))
        else:
            for time_zone_offset in range(-840, 841):
                date_times.append(
                    DateTimeValue(self.m_lower_bound, False, time_zone_offset)
                )
            if DateTimeValue.seconds_are_zero(self.m_lower_bound):
                minutes_in_day = DateTimeValue.get_minutes_in_day(self.m_lower_bound)
                if self.m_lower_bound >= 0:
                    if 0 <= minutes_in_day <= 840:
                        date_times.append(
                            DateTimeValue(self.m_lower_bound, True, -minutes_in_day)
                        )
                    if 1440 - 840 <= minutes_in_day:
                        date_times.append(
                            DateTimeValue(self.m_lower_bound, True, 1440 - minutes_in_day)
                        )
                else:
                    if -840 <= minutes_in_day <= 0:
                        date_times.append(
                            DateTimeValue(self.m_lower_bound, True, -1440 - minutes_in_day)
                        )
                    if minutes_in_day <= -1440 + 840:
                        date_times.append(
                            DateTimeValue(self.m_lower_bound, True, -minutes_in_day)
                        )

    @staticmethod
    def is_interval_empty(
        lower_bound: int,
        lower_bound_type: DateTimeBoundType,
        upper_bound: int,
        upper_bound_type: DateTimeBoundType,
    ) -> bool:
        return lower_bound > upper_bound or (
            lower_bound == upper_bound
            and (
                lower_bound_type is DateTimeBoundType.EXCLUSIVE
                or upper_bound_type is DateTimeBoundType.EXCLUSIVE
            )
        )

    def __repr__(self) -> str:
        left = "[" if self.m_lower_bound_type is DateTimeBoundType.INCLUSIVE else "<"
        right = "]" if self.m_upper_bound_type is DateTimeBoundType.INCLUSIVE else ">"
        return (
            f"{self.m_interval_type.name}{left}{self.m_lower_bound} .. "
            f"{self.m_upper_bound}{right}"
        )


def _interval_all_with_timezone() -> DateTimeInterval:
    return DateTimeInterval(
        IntervalType.WITH_TIMEZONE,
        _TIME_MIN, DateTimeBoundType.EXCLUSIVE,
        _TIME_MAX, DateTimeBoundType.EXCLUSIVE,
    )


def _interval_all_without_timezone() -> DateTimeInterval:
    return DateTimeInterval(
        IntervalType.WITHOUT_TIMEZONE,
        _TIME_MIN, DateTimeBoundType.EXCLUSIVE,
        _TIME_MAX, DateTimeBoundType.EXCLUSIVE,
    )


class DateTimeValueSpaceSubset(ValueSpaceSubset):
    def __init__(self, empty: bool = False, entire: bool = False):
        self._empty = empty
        self._entire = entire

    def is_empty(self) -> bool:
        return self._empty

    def contains(self, value: Any) -> bool:
        return self._entire

    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        if isinstance(other, DateTimeValueSpaceSubset):
            if self._empty or other._empty:
                return DateTimeValueSpaceSubset(empty=True)
            return DateTimeValueSpaceSubset(entire=True)
        return DateTimeValueSpaceSubset(empty=True)

    def complement(self) -> ValueSpaceSubset:
        return DateTimeValueSpaceSubset(empty=not self._empty)


class DateTimeUnionSubset(DateTimeValueSpaceSubset):
    """A union of date-time intervals over both timezone families."""

    def __init__(self, intervals: list[DateTimeInterval], entire: bool = False) -> None:
        super().__init__(empty=not intervals, entire=entire)
        self.m_intervals = intervals

    def contains_data_value(self, value: Any) -> bool:
        if not isinstance(value, DateTimeValue):
            return False
        return any(
            interval.contains_date_time(value) for interval in self.m_intervals
        )

    def has_cardinality_at_least(self, number: int) -> bool:
        left = number
        for interval in self.m_intervals:
            if left <= 0:
                break
            left = interval.subtract_size_from(left)
        return left <= 0

    def enumerate_data_values(self, data_values: list[Any]) -> None:
        for interval in self.m_intervals:
            interval.enumerate_date_times(data_values)


_ENTIRE_SUBSET = DateTimeUnionSubset(
    [_interval_all_with_timezone(), _interval_all_without_timezone()], entire=True
)
_WITH_TIMEZONE_SUBSET = DateTimeUnionSubset([_interval_all_with_timezone()])
_EMPTY_SUBSET = DateTimeUnionSubset([])

_SUPPORTED_FACET_URIS = frozenset({
    XSD_NS + "minInclusive",
    XSD_NS + "minExclusive",
    XSD_NS + "maxInclusive",
    XSD_NS + "maxExclusive",
})


def _facet_date_time(facet_value: Any) -> DateTimeValue:
    raw = facet_data_value(facet_value)
    if isinstance(raw, DateTimeValue):
        return raw
    if isinstance(raw, str):
        parsed = DateTimeValue.parse(raw)
        if parsed is not None:
            return parsed
    if isinstance(raw, datetime):
        offset: int | None = None
        if raw.tzinfo is not None:
            delta = raw.utcoffset()
            offset = int(delta.total_seconds() // 60) if delta is not None else 0
        return DateTimeValue.from_components(
            raw.year, raw.month, raw.day, raw.hour, raw.minute, raw.second,
            raw.microsecond // 1000, offset,
        )
    raise UnsupportedFacetException(
        f"xsd:dateTime facets take only date/time values, not {raw!r}."
    )


class DateTimeDatatypeHandler(DatatypeHandler):
    IRIS = (
        XSD_DATE_TIME,
        XSD_DATE_TIME_STAMP,
        XSD_NS + "date",
        XSD_NS + "time",
        XSD_NS + "duration",
        XSD_NS + "gYear",
        XSD_NS + "gMonth",
        XSD_NS + "gDay",
        XSD_NS + "gYearMonth",
        XSD_NS + "gMonthDay",
    )

    def get_datatype_iris(self) -> tuple[str, ...]:
        return self.IRIS

    def parse_literal(self, lexical_form: str, datatype_iri: str) -> Any:
        try:
            # ISO 8601 format
            return datetime.fromisoformat(lexical_form.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            raise MalformedLiteralException(f"Invalid dateTime: {lexical_form!r}") from None

    def parse_data_value(self, lexical_form: str, datatype_iri: str) -> Any:
        if datatype_iri in (XSD_DATE_TIME, XSD_DATE_TIME_STAMP):
            date_time = DateTimeValue.parse(lexical_form)
            if date_time is None or (
                datatype_iri == XSD_DATE_TIME_STAMP
                and not date_time.has_time_zone_offset()
            ):
                raise MalformedLiteralException(
                    f"Invalid {datatype_iri} literal: {lexical_form!r}"
                )
            return date_time
        return self.parse_literal(lexical_form, datatype_iri)

    def validate_datatype_restriction(self, datatype_restriction: Any) -> None:
        if datatype_restriction.datatype_iri not in (XSD_DATE_TIME, XSD_DATE_TIME_STAMP):
            return
        for index in range(datatype_restriction.number_of_facet_restrictions() - 1, -1, -1):
            facet_uri = datatype_restriction.facet_uri(index)
            if facet_uri not in _SUPPORTED_FACET_URIS:
                raise UnsupportedFacetException(
                    f"Facet with URI '{facet_uri}' is not supported on xsd:dateTime; "
                    "only xsd:minInclusive, xsd:maxInclusive, xsd:minExclusive, "
                    "and xsd:maxExclusive are supported."
                )
            _facet_date_time(datatype_restriction.facet_value(index))

    def create_value_space_subset(
        self, datatype_iri: str, facet_uris: Any, facet_values: Any
    ) -> DateTimeValueSpaceSubset:
        if datatype_iri not in (XSD_DATE_TIME, XSD_DATE_TIME_STAMP):
            return DateTimeValueSpaceSubset(entire=True)
        if not facet_uris:
            if datatype_iri == XSD_DATE_TIME:
                return _ENTIRE_SUBSET
            return _WITH_TIMEZONE_SUBSET
        with_tz, without_tz = self._intervals_for(datatype_iri, facet_uris, facet_values)
        intervals = [iv for iv in (with_tz, without_tz) if iv is not None]
        if not intervals:
            return _EMPTY_SUBSET
        return DateTimeUnionSubset(intervals)

    def conjoin_with_dr(
        self, value_space_subset: ValueSpaceSubset, datatype_restriction: Any
    ) -> ValueSpaceSubset:
        datatype_iri = datatype_restriction.datatype_iri
        if datatype_iri not in (XSD_DATE_TIME, XSD_DATE_TIME_STAMP) or not isinstance(
            value_space_subset, DateTimeUnionSubset
        ):
            return super().conjoin_with_dr(value_space_subset, datatype_restriction)
        facet_uris: tuple[str, ...] = getattr(datatype_restriction, "_facet_uris", ())
        facet_values: tuple[Any, ...] = getattr(datatype_restriction, "_facet_values", ())
        with_tz, without_tz = self._intervals_for(datatype_iri, facet_uris, facet_values)
        restriction_intervals = [iv for iv in (with_tz, without_tz) if iv is not None]
        if not restriction_intervals:
            return _EMPTY_SUBSET
        new_intervals: list[DateTimeInterval] = []
        for old_interval in value_space_subset.m_intervals:
            for restriction_interval in restriction_intervals:
                intersection = old_interval.intersect_with(restriction_interval)
                if intersection is not None:
                    new_intervals.append(intersection)
        if not new_intervals:
            return _EMPTY_SUBSET
        return DateTimeUnionSubset(new_intervals)

    def conjoin_with_dr_negation(
        self, value_space_subset: ValueSpaceSubset, datatype_restriction: Any
    ) -> ValueSpaceSubset:
        datatype_iri = datatype_restriction.datatype_iri
        if datatype_iri not in (XSD_DATE_TIME, XSD_DATE_TIME_STAMP) or not isinstance(
            value_space_subset, DateTimeUnionSubset
        ):
            return super().conjoin_with_dr_negation(value_space_subset, datatype_restriction)
        facet_uris: tuple[str, ...] = getattr(datatype_restriction, "_facet_uris", ())
        facet_values: tuple[Any, ...] = getattr(datatype_restriction, "_facet_values", ())
        with_tz, without_tz = self._intervals_for(datatype_iri, facet_uris, facet_values)
        if with_tz is None and without_tz is None:
            return value_space_subset
        complemented_intervals: list[DateTimeInterval] = []
        if with_tz is None:
            complemented_intervals.append(_interval_all_with_timezone())
        else:
            if with_tz.m_lower_bound != _TIME_MIN:
                complemented_intervals.append(
                    DateTimeInterval(
                        IntervalType.WITH_TIMEZONE,
                        _TIME_MIN, DateTimeBoundType.EXCLUSIVE,
                        with_tz.m_lower_bound,
                        with_tz.m_lower_bound_type.get_complement(),
                    )
                )
            if with_tz.m_upper_bound != _TIME_MAX:
                complemented_intervals.append(
                    DateTimeInterval(
                        IntervalType.WITH_TIMEZONE,
                        with_tz.m_upper_bound,
                        with_tz.m_upper_bound_type.get_complement(),
                        _TIME_MAX, DateTimeBoundType.EXCLUSIVE,
                    )
                )
        if without_tz is None:
            complemented_intervals.append(_interval_all_without_timezone())
        else:
            if without_tz.m_lower_bound != _TIME_MIN:
                complemented_intervals.append(
                    DateTimeInterval(
                        IntervalType.WITHOUT_TIMEZONE,
                        _TIME_MIN, DateTimeBoundType.EXCLUSIVE,
                        without_tz.m_lower_bound,
                        without_tz.m_lower_bound_type.get_complement(),
                    )
                )
            if without_tz.m_upper_bound != _TIME_MAX:
                complemented_intervals.append(
                    DateTimeInterval(
                        IntervalType.WITHOUT_TIMEZONE,
                        without_tz.m_upper_bound,
                        without_tz.m_upper_bound_type.get_complement(),
                        _TIME_MAX, DateTimeBoundType.EXCLUSIVE,
                    )
                )
        new_intervals: list[DateTimeInterval] = []
        for old_interval in value_space_subset.m_intervals:
            for complemented_interval in complemented_intervals:
                intersection = old_interval.intersect_with(complemented_interval)
                if intersection is not None:
                    new_intervals.append(intersection)
        if not new_intervals:
            return _EMPTY_SUBSET
        return DateTimeUnionSubset(new_intervals)

    @staticmethod
    def _intervals_for(
        datatype_iri: str,
        facet_uris: tuple[str, ...],
        facet_values: tuple[Any, ...],
    ) -> tuple[DateTimeInterval | None, DateTimeInterval | None]:
        with_tz: DateTimeInterval | None = _interval_all_with_timezone()
        without_tz: DateTimeInterval | None = None
        if datatype_iri == XSD_DATE_TIME:
            without_tz = _interval_all_without_timezone()
        if not facet_uris:
            return with_tz, without_tz
        for facet_uri, facet_value in zip(facet_uris, facet_values, strict=False):
            facet_date_time = _facet_date_time(facet_value)
            timeline = facet_date_time.time_on_timeline
            if facet_uri in (XSD_NS + "minInclusive", XSD_NS + "minExclusive"):
                bound_type = (
                    DateTimeBoundType.INCLUSIVE
                    if facet_uri == XSD_NS + "minInclusive"
                    else DateTimeBoundType.EXCLUSIVE
                )
                if facet_date_time.has_time_zone_offset():
                    if with_tz is not None:
                        with_tz = with_tz.intersect_with(
                            DateTimeInterval(
                                IntervalType.WITH_TIMEZONE,
                                timeline, bound_type,
                                _TIME_MAX, DateTimeBoundType.EXCLUSIVE,
                            )
                        )
                    if without_tz is not None:
                        without_tz = without_tz.intersect_with(
                            DateTimeInterval(
                                IntervalType.WITHOUT_TIMEZONE,
                                timeline + MAX_TIME_ZONE_CORRECTION,
                                DateTimeBoundType.EXCLUSIVE,
                                _TIME_MAX, DateTimeBoundType.EXCLUSIVE,
                            )
                        )
                else:
                    if with_tz is not None:
                        with_tz = with_tz.intersect_with(
                            DateTimeInterval(
                                IntervalType.WITH_TIMEZONE,
                                timeline + MAX_TIME_ZONE_CORRECTION,
                                DateTimeBoundType.EXCLUSIVE,
                                _TIME_MAX, DateTimeBoundType.EXCLUSIVE,
                            )
                        )
                    if without_tz is not None:
                        without_tz = without_tz.intersect_with(
                            DateTimeInterval(
                                IntervalType.WITHOUT_TIMEZONE,
                                timeline, bound_type,
                                _TIME_MAX, DateTimeBoundType.EXCLUSIVE,
                            )
                        )
            elif facet_uri in (XSD_NS + "maxInclusive", XSD_NS + "maxExclusive"):
                bound_type = (
                    DateTimeBoundType.INCLUSIVE
                    if facet_uri == XSD_NS + "maxInclusive"
                    else DateTimeBoundType.EXCLUSIVE
                )
                if facet_date_time.has_time_zone_offset():
                    if with_tz is not None:
                        with_tz = with_tz.intersect_with(
                            DateTimeInterval(
                                IntervalType.WITH_TIMEZONE,
                                _TIME_MIN, DateTimeBoundType.EXCLUSIVE,
                                timeline, bound_type,
                            )
                        )
                    if without_tz is not None:
                        without_tz = without_tz.intersect_with(
                            DateTimeInterval(
                                IntervalType.WITHOUT_TIMEZONE,
                                _TIME_MIN, DateTimeBoundType.EXCLUSIVE,
                                timeline - MAX_TIME_ZONE_CORRECTION,
                                DateTimeBoundType.EXCLUSIVE,
                            )
                        )
                else:
                    if with_tz is not None:
                        with_tz = with_tz.intersect_with(
                            DateTimeInterval(
                                IntervalType.WITH_TIMEZONE,
                                _TIME_MIN, DateTimeBoundType.EXCLUSIVE,
                                timeline - MAX_TIME_ZONE_CORRECTION,
                                DateTimeBoundType.EXCLUSIVE,
                            )
                        )
                    if without_tz is not None:
                        without_tz = without_tz.intersect_with(
                            DateTimeInterval(
                                IntervalType.WITHOUT_TIMEZONE,
                                _TIME_MIN, DateTimeBoundType.EXCLUSIVE,
                                timeline, bound_type,
                            )
                        )
            else:
                raise UnsupportedFacetException(
                    f"Facet '{facet_uri}' is not supported by xsd:dateTime."
                )
        return with_tz, without_tz

    def entire_space(self, datatype_iri: str) -> DateTimeValueSpaceSubset:
        if datatype_iri == XSD_DATE_TIME_STAMP:
            return _WITH_TIMEZONE_SUBSET
        if datatype_iri == XSD_DATE_TIME:
            return _ENTIRE_SUBSET
        return DateTimeValueSpaceSubset(entire=True)

    def empty_space(self, datatype_iri: str) -> DateTimeValueSpaceSubset:
        return DateTimeValueSpaceSubset(empty=True)

    def is_subset_of_datatype(
        self, subset_datatype_iri: str, superset_datatype_iri: str
    ) -> bool:
        if subset_datatype_iri == superset_datatype_iri:
            return True
        return (
            subset_datatype_iri == XSD_DATE_TIME_STAMP
            and superset_datatype_iri == XSD_DATE_TIME
        )

DatatypeRegistry.register(DateTimeDatatypeHandler())
