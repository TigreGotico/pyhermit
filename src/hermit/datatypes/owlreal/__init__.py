"""
OWL Real datatype handler.

Implements owl:real, owl:rational, xsd:decimal, and the xsd integer types
with Java HermiT's numeric interval arithmetic: every value space subset is
a union of ``NumberInterval`` objects that carry a base number range
(INTEGER/DECIMAL/RATIONAL/REAL), an excluded range, and inclusive/exclusive
endpoint bounds.  Integer-based intervals are discrete, so their cardinality
is computed exactly.
"""

from __future__ import annotations

__all__ = [
    "BigRational",
    "BigRationalInfinity",
    "BoundType",
    "NumberInterval",
    "NumberRange",
    "OWLRealDatatypeHandler",
    "OWLRealValueSpaceSubset",
    "OWL_REAL_IRIS",
    "parse_decimal",
    "parse_integer",
    "parse_rational",
]

import math
import re
from decimal import Decimal, InvalidOperation
from enum import Enum, IntEnum
from fractions import Fraction
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
OWL_NS = "http://www.w3.org/2002/07/owl#"

# Interval: (lower, upper, lower_inclusive, upper_inclusive)
Interval = tuple["BigRational", "BigRational", bool, bool]


# ---------------------------------------------------------------------------
# BigRational — port of HermiT's BigRational for owl:real
# ---------------------------------------------------------------------------

class BigRational:
    """
    Arbitrary-precision rational number, port of HermiT's BigRational.
    Uses Python's ``fractions.Fraction`` internally.
    """

    __slots__ = ("_value",)

    def __init__(self, value: Fraction | Decimal | int | float | str) -> None:
        if isinstance(value, Fraction):
            self._value = value
        elif isinstance(value, BigRational):
            self._value = value._value
        else:
            try:
                self._value = Fraction(value)
            except (ValueError, ZeroDivisionError):
                raise MalformedLiteralException(f"Cannot parse as rational: {value}") from None

    @property
    def fraction(self) -> Fraction:
        return self._value

    @property
    def numerator(self) -> int:
        return self._value.numerator

    @property
    def denominator(self) -> int:
        return self._value.denominator

    def __hash__(self) -> int:
        return hash(self._value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BigRationalInfinity):
            return False
        if isinstance(other, BigRational):
            return self._value == other._value
        return False

    def __lt__(self, other: BigRational) -> bool:
        if isinstance(other, BigRationalInfinity):
            return other.is_positive
        return self._value < other._value

    def __le__(self, other: BigRational) -> bool:
        if isinstance(other, BigRationalInfinity):
            return other.is_positive
        return self._value <= other._value

    def __gt__(self, other: BigRational) -> bool:
        if isinstance(other, BigRationalInfinity):
            return not other.is_positive
        return self._value > other._value

    def __ge__(self, other: BigRational) -> bool:
        if isinstance(other, BigRationalInfinity):
            return not other.is_positive
        return self._value >= other._value

    def __repr__(self) -> str:
        return f"BigRational({self._value})"

    @classmethod
    def from_decimal(cls, d: Decimal) -> BigRational:
        return cls(Fraction(d))

    @classmethod
    def infinity(cls, positive: bool = True) -> BigRationalInfinity:
        return BigRationalInfinity(positive)


class BigRationalInfinity(BigRational):
    """Positive or negative infinity for owl:real."""

    __slots__ = ("_positive",)

    def __init__(self, positive: bool = True) -> None:
        self._positive = positive

    @property
    def is_positive(self) -> bool:
        return self._positive

    def __hash__(self) -> int:
        return hash(("inf", self._positive))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BigRationalInfinity):
            return self._positive == other._positive
        return False

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, BigRationalInfinity):
            return not self._positive and other._positive
        return not self._positive

    def __le__(self, other: Any) -> bool:
        return bool(self == other or self < other)

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, BigRationalInfinity):
            return self._positive and not other._positive
        return self._positive

    def __ge__(self, other: Any) -> bool:
        return bool(self == other or self > other)

    def __repr__(self) -> str:
        return "+∞" if self._positive else "-∞"


MINUS_INFINITY = BigRationalInfinity(False)
PLUS_INFINITY = BigRationalInfinity(True)


def _compare(value1: BigRational, value2: BigRational) -> int:
    """Three-way comparison handling infinities."""
    if value1 == value2:
        return 0
    return -1 if value1 < value2 else 1


# ---------------------------------------------------------------------------
# Lexical parsing (Java Numbers port)
# ---------------------------------------------------------------------------

_INTEGER_PATTERN = re.compile(r"[+-]?[0-9]+")
_DECIMAL_PATTERN = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")


def parse_integer(lexical_form: str) -> BigRational:
    """Parse an xsd integer lexical form."""
    text = lexical_form.strip()
    if not _INTEGER_PATTERN.fullmatch(text):
        raise MalformedLiteralException(f"Invalid integer literal: {lexical_form!r}")
    return BigRational(Fraction(int(text)))


def parse_decimal(lexical_form: str) -> BigRational:
    """Parse an xsd:decimal lexical form."""
    text = lexical_form.strip()
    if not _DECIMAL_PATTERN.fullmatch(text):
        raise MalformedLiteralException(f"Invalid decimal literal: {lexical_form!r}")
    try:
        return BigRational(Fraction(Decimal(text)))
    except InvalidOperation:
        raise MalformedLiteralException(f"Invalid decimal literal: {lexical_form!r}") from None


def parse_rational(lexical_form: str) -> BigRational:
    """Parse an owl:rational lexical form of shape ``numerator/denominator``."""
    text = lexical_form.strip()
    divide_index = text.find("/")
    if divide_index == -1:
        raise MalformedLiteralException(f"Invalid rational literal: {lexical_form!r}")
    numerator_text = text[:divide_index]
    if numerator_text.startswith("+"):
        numerator_text = numerator_text[1:]
    denominator_text = text[divide_index + 1:]
    if not _INTEGER_PATTERN.fullmatch(numerator_text or "x"):
        raise MalformedLiteralException(f"Invalid rational literal: {lexical_form!r}")
    if not denominator_text.isdigit():
        raise MalformedLiteralException(f"Invalid rational literal: {lexical_form!r}")
    numerator = int(numerator_text)
    denominator = int(denominator_text)
    if denominator <= 0:
        raise MalformedLiteralException(f"Invalid rational literal: {lexical_form!r}")
    return BigRational(Fraction(numerator, denominator))


# ---------------------------------------------------------------------------
# Number ranges and bounds (Java NumberRange / BoundType ports)
# ---------------------------------------------------------------------------

class NumberRange(IntEnum):
    """The kinds of numbers an interval ranges over."""

    NOTHING = 0
    INTEGER = 1
    DECIMAL = 2
    RATIONAL = 3
    REAL = 4

    @property
    def is_dense(self) -> bool:
        return self >= NumberRange.DECIMAL

    @staticmethod
    def intersection(range1: NumberRange, range2: NumberRange) -> NumberRange:
        return min(range1, range2)

    @staticmethod
    def union(range1: NumberRange, range2: NumberRange) -> NumberRange:
        return max(range1, range2)

    @staticmethod
    def is_subset_of(subset: NumberRange, superset: NumberRange) -> bool:
        return subset <= superset

    @staticmethod
    def most_specific_range(value: BigRational) -> NumberRange:
        """Return the most specific range containing *value*."""
        denominator = value.fraction.denominator
        if denominator == 1:
            return NumberRange.INTEGER
        while denominator % 2 == 0:
            denominator //= 2
        while denominator % 5 == 0:
            denominator //= 5
        if denominator == 1:
            return NumberRange.DECIMAL
        return NumberRange.RATIONAL


class BoundType(Enum):
    """Whether an interval endpoint is included."""

    INCLUSIVE = 0
    EXCLUSIVE = 1

    def get_complement(self) -> BoundType:
        return BoundType.EXCLUSIVE if self is BoundType.INCLUSIVE else BoundType.INCLUSIVE

    @staticmethod
    def get_more_restrictive(bound_type1: BoundType, bound_type2: BoundType) -> BoundType:
        if bound_type1 is BoundType.EXCLUSIVE or bound_type2 is BoundType.EXCLUSIVE:
            return BoundType.EXCLUSIVE
        return BoundType.INCLUSIVE


def _nearest_integer_in_bound(
    bound: BigRational, lower_boundary: bool, bound_is_inclusive: bool
) -> BigRational:
    """Return the nearest integer inside the bound (Java getNearestIntegerInBound)."""
    fraction = bound.fraction
    if fraction.denominator == 1:
        if bound_is_inclusive:
            return bound
        return BigRational(fraction + 1 if lower_boundary else fraction - 1)
    if lower_boundary:
        return BigRational(Fraction(math.ceil(fraction)))
    return BigRational(Fraction(math.floor(fraction)))


# ---------------------------------------------------------------------------
# NumberInterval (Java port)
# ---------------------------------------------------------------------------

class NumberInterval:
    """An interval over a number range with an excluded sub-range."""

    __slots__ = (
        "m_base_range",
        "m_excluded_range",
        "m_lower_bound",
        "m_lower_bound_type",
        "m_upper_bound",
        "m_upper_bound_type",
    )

    m_base_range: NumberRange
    m_excluded_range: NumberRange
    m_lower_bound: BigRational
    m_lower_bound_type: BoundType
    m_upper_bound: BigRational
    m_upper_bound_type: BoundType

    def __init__(
        self,
        base_range: NumberRange,
        excluded_range: NumberRange,
        lower_bound: BigRational,
        lower_bound_type: BoundType,
        upper_bound: BigRational,
        upper_bound_type: BoundType,
    ) -> None:
        self.m_base_range = base_range
        self.m_excluded_range = excluded_range
        if base_range is NumberRange.INTEGER:
            # Adjust the end-points so that they fit into the INTEGER range.
            if isinstance(lower_bound, BigRationalInfinity):
                self.m_lower_bound = lower_bound
                self.m_lower_bound_type = lower_bound_type
            else:
                self.m_lower_bound = _nearest_integer_in_bound(
                    lower_bound, True, lower_bound_type is BoundType.INCLUSIVE
                )
                self.m_lower_bound_type = BoundType.INCLUSIVE
            if isinstance(upper_bound, BigRationalInfinity):
                self.m_upper_bound = upper_bound
                self.m_upper_bound_type = upper_bound_type
            else:
                self.m_upper_bound = _nearest_integer_in_bound(
                    upper_bound, False, upper_bound_type is BoundType.INCLUSIVE
                )
                self.m_upper_bound_type = BoundType.INCLUSIVE
        else:
            self.m_lower_bound = lower_bound
            self.m_lower_bound_type = lower_bound_type
            self.m_upper_bound = upper_bound
            self.m_upper_bound_type = upper_bound_type

    def intersect_with(self, that: NumberInterval) -> NumberInterval | None:
        """Intersection of this interval with *that*; ``None`` if disjoint."""
        new_base_range = NumberRange.intersection(self.m_base_range, that.m_base_range)
        new_excluded_range = NumberRange.union(self.m_excluded_range, that.m_excluded_range)
        if NumberRange.is_subset_of(new_base_range, new_excluded_range):
            return None
        lower_comparison = _compare(self.m_lower_bound, that.m_lower_bound)
        if lower_comparison < 0:
            new_lower_bound = that.m_lower_bound
            new_lower_bound_type = that.m_lower_bound_type
        elif lower_comparison > 0:
            new_lower_bound = self.m_lower_bound
            new_lower_bound_type = self.m_lower_bound_type
        else:
            new_lower_bound = self.m_lower_bound
            new_lower_bound_type = BoundType.get_more_restrictive(
                self.m_lower_bound_type, that.m_lower_bound_type
            )
        upper_comparison = _compare(self.m_upper_bound, that.m_upper_bound)
        if upper_comparison < 0:
            new_upper_bound = self.m_upper_bound
            new_upper_bound_type = self.m_upper_bound_type
        elif upper_comparison > 0:
            new_upper_bound = that.m_upper_bound
            new_upper_bound_type = that.m_upper_bound_type
        else:
            new_upper_bound = self.m_upper_bound
            new_upper_bound_type = BoundType.get_more_restrictive(
                self.m_upper_bound_type, that.m_upper_bound_type
            )
        if NumberInterval.is_interval_empty(
            new_base_range, new_excluded_range,
            new_lower_bound, new_lower_bound_type,
            new_upper_bound, new_upper_bound_type,
        ):
            return None
        # Avoid creating a new interval object unless needed; the superset
        # tables in OWLRealDatatypeHandler depend on this identity check.
        if self._is_equal(
            new_base_range, new_excluded_range,
            new_lower_bound, new_lower_bound_type,
            new_upper_bound, new_upper_bound_type,
        ):
            return self
        if that._is_equal(
            new_base_range, new_excluded_range,
            new_lower_bound, new_lower_bound_type,
            new_upper_bound, new_upper_bound_type,
        ):
            return that
        return NumberInterval(
            new_base_range, new_excluded_range,
            new_lower_bound, new_lower_bound_type,
            new_upper_bound, new_upper_bound_type,
        )

    def _is_equal(
        self,
        base_range: NumberRange,
        excluded_range: NumberRange,
        lower_bound: BigRational,
        lower_bound_type: BoundType,
        upper_bound: BigRational,
        upper_bound_type: BoundType,
    ) -> bool:
        return (
            self.m_base_range is base_range
            and self.m_excluded_range is excluded_range
            and self.m_lower_bound == lower_bound
            and self.m_lower_bound_type is lower_bound_type
            and self.m_upper_bound == upper_bound
            and self.m_upper_bound_type is upper_bound_type
        )

    def subtract_size_from(self, argument: int) -> int:
        """Subtract the number of values in this interval from *argument*."""
        if argument <= 0:
            return 0
        if self.m_lower_bound == self.m_upper_bound:
            # The interval is not empty; hence, it is a singleton.
            return argument - 1
        # If the base range is dense, the interval is infinite.
        if self.m_base_range.is_dense:
            return 0
        # The base range is INTEGER and the excluded range must be NOTHING.
        if isinstance(self.m_lower_bound, BigRationalInfinity) or isinstance(
            self.m_upper_bound, BigRationalInfinity
        ):
            return 0
        size = int(self.m_upper_bound.fraction) - int(self.m_lower_bound.fraction) + 1
        if size <= 0:
            return 0
        return max(argument - size, 0)

    def contains_number(self, number: BigRational) -> bool:
        if isinstance(number, BigRationalInfinity):
            return False
        most_specific_range = NumberRange.most_specific_range(number)
        if not NumberRange.is_subset_of(most_specific_range, self.m_base_range):
            return False
        if NumberRange.is_subset_of(most_specific_range, self.m_excluded_range):
            return False
        lower_comparison = _compare(self.m_lower_bound, number)
        if lower_comparison > 0 or (
            lower_comparison == 0 and self.m_lower_bound_type is BoundType.EXCLUSIVE
        ):
            return False
        upper_comparison = _compare(self.m_upper_bound, number)
        if upper_comparison < 0 or (
            upper_comparison == 0 and self.m_upper_bound_type is BoundType.EXCLUSIVE
        ):
            return False
        return True

    def enumerate_numbers(self, numbers: list[Any]) -> None:
        if self.m_lower_bound == self.m_upper_bound:
            numbers.append(self.m_lower_bound)
            return
        if self.m_base_range.is_dense:
            raise RuntimeError("The data range is infinite.")
        if isinstance(self.m_lower_bound, BigRationalInfinity) or isinstance(
            self.m_upper_bound, BigRationalInfinity
        ):
            raise RuntimeError("The data range is infinite.")
        integer = int(self.m_lower_bound.fraction)
        end = int(self.m_upper_bound.fraction)
        while integer <= end:
            numbers.append(BigRational(Fraction(integer)))
            integer += 1

    @staticmethod
    def is_interval_empty(
        base_range: NumberRange,
        excluded_range: NumberRange,
        lower_bound: BigRational,
        lower_bound_type: BoundType,
        upper_bound: BigRational,
        upper_bound_type: BoundType,
    ) -> bool:
        if NumberRange.is_subset_of(base_range, excluded_range):
            return True
        bound_comparison = _compare(lower_bound, upper_bound)
        if bound_comparison > 0:
            return True
        if bound_comparison == 0:
            if (
                lower_bound_type is BoundType.EXCLUSIVE
                or upper_bound_type is BoundType.EXCLUSIVE
                or isinstance(lower_bound, BigRationalInfinity)
            ):
                return True
            most_specific_range = NumberRange.most_specific_range(lower_bound)
            return not NumberRange.is_subset_of(
                most_specific_range, base_range
            ) or NumberRange.is_subset_of(most_specific_range, excluded_range)
        # Lower bound is smaller than the upper bound.
        if base_range.is_dense:
            return False
        if isinstance(lower_bound, BigRationalInfinity) or isinstance(
            upper_bound, BigRationalInfinity
        ):
            return False
        lower_bound_inclusive = _nearest_integer_in_bound(
            lower_bound, True, lower_bound_type is BoundType.INCLUSIVE
        )
        upper_bound_inclusive = _nearest_integer_in_bound(
            upper_bound, False, upper_bound_type is BoundType.INCLUSIVE
        )
        return _compare(lower_bound_inclusive, upper_bound_inclusive) > 0

    def __repr__(self) -> str:
        parts = [self.m_base_range.name]
        if self.m_excluded_range is not NumberRange.NOTHING:
            parts.append("\\" + self.m_excluded_range.name)
        parts.append("[" if self.m_lower_bound_type is BoundType.INCLUSIVE else "<")
        parts.append(str(self.m_lower_bound))
        parts.append(" .. ")
        parts.append(str(self.m_upper_bound))
        parts.append("]" if self.m_upper_bound_type is BoundType.INCLUSIVE else ">")
        return "".join(parts)


def _entire_real_interval() -> NumberInterval:
    return NumberInterval(
        NumberRange.REAL, NumberRange.NOTHING,
        MINUS_INFINITY, BoundType.EXCLUSIVE,
        PLUS_INFINITY, BoundType.EXCLUSIVE,
    )


def _legacy_tuple_to_interval(legacy: Interval) -> NumberInterval | None:
    """Convert a legacy ``(lo, hi, lo_inc, hi_inc)`` tuple to a NumberInterval."""
    lo, hi, lo_inc, hi_inc = legacy
    lo_type = BoundType.INCLUSIVE if lo_inc else BoundType.EXCLUSIVE
    hi_type = BoundType.INCLUSIVE if hi_inc else BoundType.EXCLUSIVE
    if isinstance(lo, BigRationalInfinity):
        lo_type = BoundType.EXCLUSIVE
    if isinstance(hi, BigRationalInfinity):
        hi_type = BoundType.EXCLUSIVE
    if NumberInterval.is_interval_empty(
        NumberRange.REAL, NumberRange.NOTHING, lo, lo_type, hi, hi_type
    ):
        return None
    return NumberInterval(
        NumberRange.REAL, NumberRange.NOTHING, lo, lo_type, hi, hi_type
    )


# ---------------------------------------------------------------------------
# OWLRealValueSpaceSubset
# ---------------------------------------------------------------------------

class OWLRealValueSpaceSubset(ValueSpaceSubset):
    """
    A subset of the owl:real value space: a union of ``NumberInterval``s.

    Accepts legacy ``(lower, upper, lower_inclusive, upper_inclusive)``
    tuples as well as ``NumberInterval`` objects.
    """

    def __init__(
        self,
        intervals: list[Interval] | list[NumberInterval] | None = None,
        empty: bool = False,
    ) -> None:
        self.m_intervals: list[NumberInterval] = []
        if not empty:
            if intervals is None:
                self.m_intervals.append(_entire_real_interval())
            else:
                for item in intervals:
                    if isinstance(item, NumberInterval):
                        self.m_intervals.append(item)
                    else:
                        converted = _legacy_tuple_to_interval(item)
                        if converted is not None:
                            self.m_intervals.append(converted)
        # Legacy view of the intervals as 4-tuples.
        self._intervals: list[Interval] = [
            (
                iv.m_lower_bound,
                iv.m_upper_bound,
                iv.m_lower_bound_type is BoundType.INCLUSIVE,
                iv.m_upper_bound_type is BoundType.INCLUSIVE,
            )
            for iv in self.m_intervals
        ]

    def is_empty(self) -> bool:
        return len(self.m_intervals) == 0

    def contains(self, value: Any) -> bool:
        if not isinstance(value, BigRational):
            return False
        return any(iv.contains_number(value) for iv in self.m_intervals)

    def contains_data_value(self, value: Any) -> bool:
        return self.contains(value)

    def has_cardinality_at_least(self, number: int) -> bool:
        left = number
        for interval in self.m_intervals:
            if left <= 0:
                break
            left = interval.subtract_size_from(left)
        return left <= 0

    def enumerate_data_values(self, data_values: list[Any]) -> None:
        for interval in self.m_intervals:
            interval.enumerate_numbers(data_values)

    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        if not isinstance(other, OWLRealValueSpaceSubset):
            return OWLRealValueSpaceSubset(empty=True)
        result: list[NumberInterval] = []
        for interval1 in self.m_intervals:
            for interval2 in other.m_intervals:
                intersection = interval1.intersect_with(interval2)
                if intersection is not None:
                    result.append(intersection)
        return OWLRealValueSpaceSubset(result, empty=not result)

    @staticmethod
    def _complement_pieces(interval: NumberInterval) -> list[NumberInterval]:
        """The complement of *interval* within owl:real, as up to three pieces."""
        pieces: list[NumberInterval] = []
        if not isinstance(interval.m_lower_bound, BigRationalInfinity):
            pieces.append(
                NumberInterval(
                    NumberRange.REAL, NumberRange.NOTHING,
                    MINUS_INFINITY, BoundType.EXCLUSIVE,
                    interval.m_lower_bound, interval.m_lower_bound_type.get_complement(),
                )
            )
        if interval.m_base_range is not NumberRange.REAL:
            pieces.append(
                NumberInterval(
                    NumberRange.REAL, interval.m_base_range,
                    interval.m_lower_bound, interval.m_lower_bound_type,
                    interval.m_upper_bound, interval.m_upper_bound_type,
                )
            )
        if not isinstance(interval.m_upper_bound, BigRationalInfinity):
            pieces.append(
                NumberInterval(
                    NumberRange.REAL, NumberRange.NOTHING,
                    interval.m_upper_bound, interval.m_upper_bound_type.get_complement(),
                    PLUS_INFINITY, BoundType.EXCLUSIVE,
                )
            )
        return pieces

    def complement(self) -> ValueSpaceSubset:
        current: list[NumberInterval] = [_entire_real_interval()]
        for interval in self.m_intervals:
            pieces = self._complement_pieces(interval)
            next_intervals: list[NumberInterval] = []
            for accumulated in current:
                for piece in pieces:
                    intersection = accumulated.intersect_with(piece)
                    if intersection is not None:
                        next_intervals.append(intersection)
            current = next_intervals
        return OWLRealValueSpaceSubset(current, empty=not current)

    @staticmethod
    def _intersect_intervals(
        a: Interval, b: Interval
    ) -> Interval | None:
        lo_a, hi_a, lo_a_inc, hi_a_inc = a
        lo_b, hi_b, lo_b_inc, hi_b_inc = b

        # Determine max of lowers
        if lo_a > lo_b:
            lo, lo_i = lo_a, lo_a_inc
        elif lo_b > lo_a:
            lo, lo_i = lo_b, lo_b_inc
        else:
            lo, lo_i = lo_a, lo_a_inc and lo_b_inc

        # Determine min of uppers
        if hi_a < hi_b:
            hi, hi_i = hi_a, hi_a_inc
        elif hi_b < hi_a:
            hi, hi_i = hi_b, hi_b_inc
        else:
            hi, hi_i = hi_a, hi_a_inc and hi_b_inc

        if lo > hi or (lo == hi and not (lo_i and hi_i)):
            return None
        return (lo, hi, lo_i, hi_i)

    def __repr__(self) -> str:
        if not self.m_intervals:
            return "OWLRealValueSpaceSubset(∅)"
        parts = [str(iv) for iv in self.m_intervals]
        return f"OWLRealValueSpaceSubset({' ∪ '.join(parts)})"


# ---------------------------------------------------------------------------
# OWLRealDatatypeHandler
# ---------------------------------------------------------------------------

OWL_REAL_IRIS = (
    OWL_NS + "real",
    OWL_NS + "rational",
    XSD_NS + "decimal",
    XSD_NS + "integer",
    XSD_NS + "nonPositiveInteger",
    XSD_NS + "negativeInteger",
    XSD_NS + "nonNegativeInteger",
    XSD_NS + "positiveInteger",
    XSD_NS + "long",
    XSD_NS + "int",
    XSD_NS + "short",
    XSD_NS + "byte",
    XSD_NS + "unsignedLong",
    XSD_NS + "unsignedInt",
    XSD_NS + "unsignedShort",
    XSD_NS + "unsignedByte",
)

_ZERO = BigRational(0)


def _build_intervals_by_datatype() -> dict[str, NumberInterval]:
    inc = BoundType.INCLUSIVE
    exc = BoundType.EXCLUSIVE
    rows: list[tuple[str, NumberRange, BigRational, BoundType, BigRational, BoundType]] = [
        (OWL_NS + "real", NumberRange.REAL, MINUS_INFINITY, exc, PLUS_INFINITY, exc),
        (OWL_NS + "rational", NumberRange.RATIONAL, MINUS_INFINITY, exc, PLUS_INFINITY, exc),
        (XSD_NS + "decimal", NumberRange.DECIMAL, MINUS_INFINITY, exc, PLUS_INFINITY, exc),
        (XSD_NS + "integer", NumberRange.INTEGER, MINUS_INFINITY, exc, PLUS_INFINITY, exc),
        (XSD_NS + "nonNegativeInteger", NumberRange.INTEGER, _ZERO, inc, PLUS_INFINITY, exc),
        (XSD_NS + "positiveInteger", NumberRange.INTEGER, _ZERO, exc, PLUS_INFINITY, exc),
        (XSD_NS + "nonPositiveInteger", NumberRange.INTEGER, MINUS_INFINITY, exc, _ZERO, inc),
        (XSD_NS + "negativeInteger", NumberRange.INTEGER, MINUS_INFINITY, exc, _ZERO, exc),
        (
            XSD_NS + "long", NumberRange.INTEGER,
            BigRational(-(2 ** 63)), inc, BigRational(2 ** 63 - 1), inc,
        ),
        (
            XSD_NS + "int", NumberRange.INTEGER,
            BigRational(-(2 ** 31)), inc, BigRational(2 ** 31 - 1), inc,
        ),
        (
            XSD_NS + "short", NumberRange.INTEGER,
            BigRational(-(2 ** 15)), inc, BigRational(2 ** 15 - 1), inc,
        ),
        (
            XSD_NS + "byte", NumberRange.INTEGER,
            BigRational(-(2 ** 7)), inc, BigRational(2 ** 7 - 1), inc,
        ),
        (
            XSD_NS + "unsignedLong", NumberRange.INTEGER,
            _ZERO, inc, BigRational(2 ** 64 - 1), inc,
        ),
        (
            XSD_NS + "unsignedInt", NumberRange.INTEGER,
            _ZERO, inc, BigRational(2 ** 32 - 1), inc,
        ),
        (
            XSD_NS + "unsignedShort", NumberRange.INTEGER,
            _ZERO, inc, BigRational(2 ** 16 - 1), inc,
        ),
        (
            XSD_NS + "unsignedByte", NumberRange.INTEGER,
            _ZERO, inc, BigRational(2 ** 8 - 1), inc,
        ),
    ]
    return {
        iri: NumberInterval(base, NumberRange.NOTHING, lo, lo_type, hi, hi_type)
        for iri, base, lo, lo_type, hi, hi_type in rows
    }


_INTERVALS_BY_DATATYPE: dict[str, NumberInterval] = _build_intervals_by_datatype()
_SUBSETS_BY_DATATYPE: dict[str, OWLRealValueSpaceSubset] = {
    iri: OWLRealValueSpaceSubset([interval])
    for iri, interval in _INTERVALS_BY_DATATYPE.items()
}


def _build_relation_tables() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    supersets: dict[str, set[str]] = {iri: set() for iri in _INTERVALS_BY_DATATYPE}
    disjoints: dict[str, set[str]] = {iri: set() for iri in _INTERVALS_BY_DATATYPE}
    for iri1, interval1 in _INTERVALS_BY_DATATYPE.items():
        for iri2, interval2 in _INTERVALS_BY_DATATYPE.items():
            intersection = interval1.intersect_with(interval2)
            if intersection is None:
                disjoints[iri1].add(iri2)
            elif intersection is interval1:
                supersets[iri1].add(iri2)
    return supersets, disjoints


_DATATYPE_SUPERSETS, _DATATYPE_DISJOINTS = _build_relation_tables()

_SUPPORTED_FACET_URIS = frozenset({
    XSD_NS + "minInclusive",
    XSD_NS + "minExclusive",
    XSD_NS + "maxInclusive",
    XSD_NS + "maxExclusive",
})

_EMPTY_SUBSET = OWLRealValueSpaceSubset(empty=True)


def _to_rational(value: Any) -> BigRational:
    """Coerce a facet value to a BigRational."""
    raw = facet_data_value(value)
    if isinstance(raw, BigRational):
        return raw
    return BigRational(raw)


class OWLRealDatatypeHandler(DatatypeHandler):
    """Handler for owl:real, owl:rational, and xsd numeric datatypes."""

    def get_datatype_iris(self) -> tuple[str, ...]:
        return OWL_REAL_IRIS

    def parse_literal(self, lexical_form: str, datatype_iri: str) -> Any:
        try:
            if datatype_iri == OWL_NS + "real":
                raise MalformedLiteralException(
                    f"owl:real has no lexical forms: {lexical_form!r}"
                )
            if datatype_iri == OWL_NS + "rational":
                return parse_rational(lexical_form)
            if datatype_iri == XSD_NS + "decimal":
                return parse_decimal(lexical_form)
            return parse_integer(lexical_form)
        except MalformedLiteralException:
            raise
        except (ValueError, ArithmeticError):
            raise MalformedLiteralException(
                f"Invalid {datatype_iri} literal: {lexical_form!r}"
            ) from None

    def validate_datatype_restriction(self, datatype_restriction: Any) -> None:
        for index in range(datatype_restriction.number_of_facet_restrictions() - 1, -1, -1):
            facet_uri = datatype_restriction.facet_uri(index)
            if facet_uri not in _SUPPORTED_FACET_URIS:
                raise UnsupportedFacetException(
                    f"A facet with URI '{facet_uri}' is not supported on datatypes "
                    "derived from owl:real; only xsd:minInclusive, xsd:maxInclusive, "
                    "xsd:minExclusive, and xsd:maxExclusive are supported."
                )
            facet_value = datatype_restriction.facet_value(index)
            try:
                _to_rational(facet_value)
            except MalformedLiteralException:
                raise UnsupportedFacetException(
                    f"The facet with URI '{facet_uri}' takes only numbers as values "
                    f"when used on a datatype derived from owl:real, but the value "
                    f"is {facet_value!r}."
                ) from None

    def create_value_space_subset(
        self,
        datatype_iri: str,
        facet_uris: tuple[str, ...],
        facet_values: tuple[Any, ...],
    ) -> ValueSpaceSubset:
        if not facet_uris:
            return _SUBSETS_BY_DATATYPE[datatype_iri]
        interval = self._interval_for(datatype_iri, facet_uris, facet_values)
        if interval is None:
            return _EMPTY_SUBSET
        return OWLRealValueSpaceSubset([interval])

    def conjoin_with_dr(
        self, value_space_subset: ValueSpaceSubset, datatype_restriction: Any
    ) -> ValueSpaceSubset:
        datatype_iri = datatype_restriction.datatype_iri
        facet_uris: tuple[str, ...] = getattr(datatype_restriction, "_facet_uris", ())
        facet_values: tuple[Any, ...] = getattr(datatype_restriction, "_facet_values", ())
        interval = self._interval_for(datatype_iri, facet_uris, facet_values)
        if interval is None:
            return _EMPTY_SUBSET
        assert isinstance(value_space_subset, OWLRealValueSpaceSubset)
        new_intervals: list[NumberInterval] = []
        for old_interval in value_space_subset.m_intervals:
            intersection = old_interval.intersect_with(interval)
            if intersection is not None:
                new_intervals.append(intersection)
        if not new_intervals:
            return _EMPTY_SUBSET
        return OWLRealValueSpaceSubset(new_intervals)

    def conjoin_with_dr_negation(
        self, value_space_subset: ValueSpaceSubset, datatype_restriction: Any
    ) -> ValueSpaceSubset:
        datatype_iri = datatype_restriction.datatype_iri
        facet_uris: tuple[str, ...] = getattr(datatype_restriction, "_facet_uris", ())
        facet_values: tuple[Any, ...] = getattr(datatype_restriction, "_facet_values", ())
        interval = self._interval_for(datatype_iri, facet_uris, facet_values)
        if interval is None:
            return value_space_subset
        complement_pieces = OWLRealValueSpaceSubset._complement_pieces(interval)
        assert isinstance(value_space_subset, OWLRealValueSpaceSubset)
        new_intervals: list[NumberInterval] = []
        for old_interval in value_space_subset.m_intervals:
            for piece in complement_pieces:
                intersection = old_interval.intersect_with(piece)
                if intersection is not None:
                    new_intervals.append(intersection)
        if not new_intervals:
            return _EMPTY_SUBSET
        return OWLRealValueSpaceSubset(new_intervals)

    @staticmethod
    def _interval_for(
        datatype_iri: str,
        facet_uris: tuple[str, ...],
        facet_values: tuple[Any, ...],
    ) -> NumberInterval | None:
        base_interval = _INTERVALS_BY_DATATYPE[datatype_iri]
        if not facet_uris:
            return base_interval
        base_range = base_interval.m_base_range
        excluded_range = base_interval.m_excluded_range
        lower_bound = base_interval.m_lower_bound
        lower_bound_type = base_interval.m_lower_bound_type
        upper_bound = base_interval.m_upper_bound
        upper_bound_type = base_interval.m_upper_bound_type
        for facet_uri, facet_value in zip(facet_uris, facet_values, strict=True):
            facet_data = _to_rational(facet_value)
            if facet_uri == XSD_NS + "minInclusive":
                if _compare(facet_data, lower_bound) > 0:
                    lower_bound = facet_data
                    lower_bound_type = BoundType.INCLUSIVE
            elif facet_uri == XSD_NS + "minExclusive":
                comparison = _compare(facet_data, lower_bound)
                if comparison > 0:
                    lower_bound = facet_data
                    lower_bound_type = BoundType.EXCLUSIVE
                elif comparison == 0:
                    lower_bound_type = BoundType.EXCLUSIVE
            elif facet_uri == XSD_NS + "maxInclusive":
                if _compare(facet_data, upper_bound) < 0:
                    upper_bound = facet_data
                    upper_bound_type = BoundType.INCLUSIVE
            elif facet_uri == XSD_NS + "maxExclusive":
                comparison = _compare(facet_data, upper_bound)
                if comparison < 0:
                    upper_bound = facet_data
                    upper_bound_type = BoundType.EXCLUSIVE
                elif comparison == 0:
                    upper_bound_type = BoundType.EXCLUSIVE
            else:
                raise UnsupportedFacetException(
                    f"Facet '{facet_uri}' is not supported by owl:real."
                )
        if NumberInterval.is_interval_empty(
            base_range, excluded_range,
            lower_bound, lower_bound_type,
            upper_bound, upper_bound_type,
        ):
            return None
        return NumberInterval(
            base_range, excluded_range,
            lower_bound, lower_bound_type,
            upper_bound, upper_bound_type,
        )

    def entire_space(self, datatype_iri: str) -> ValueSpaceSubset:
        return _SUBSETS_BY_DATATYPE[datatype_iri]

    def empty_space(self, datatype_iri: str) -> ValueSpaceSubset:
        return _EMPTY_SUBSET

    def is_subset_of_datatype(
        self, subset_datatype_iri: str, superset_datatype_iri: str
    ) -> bool:
        return superset_datatype_iri in _DATATYPE_SUPERSETS[subset_datatype_iri]

    def is_disjoint_with_datatype(self, datatype_iri1: str, datatype_iri2: str) -> bool:
        return datatype_iri2 in _DATATYPE_DISJOINTS[datatype_iri1]


# Register
DatatypeRegistry.register(OWLRealDatatypeHandler())
