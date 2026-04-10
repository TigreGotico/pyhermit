"""
OWL Real datatype handler.

Implements the xsd:decimal/xsd:integer/xsd:nonNegativeInteger/etc. value
space using Python's ``decimal.Decimal`` for arbitrary precision.
"""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from typing import Any

# Interval: (lower, upper, lower_inclusive, upper_inclusive)
Interval = tuple["BigRational", "BigRational", bool, bool]

from hermit.datatypes.registry import (
    DatatypeHandler,
    DatatypeRegistry,
    MalformedLiteralException,
    ValueSpaceSubset,
)

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

    def __hash__(self) -> int:
        return hash(self._value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BigRational):
            return self._value == other._value
        return False

    def __lt__(self, other: BigRational) -> bool:
        return self._value < other._value

    def __le__(self, other: BigRational) -> bool:
        return self._value <= other._value

    def __gt__(self, other: BigRational) -> bool:
        return self._value > other._value

    def __ge__(self, other: BigRational) -> bool:
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

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, BigRationalInfinity):
            return self._positive and not other._positive
        return self._positive

    def __repr__(self) -> str:
        return "+∞" if self._positive else "-∞"


# ---------------------------------------------------------------------------
# OWLRealValueSpaceSubset
# ---------------------------------------------------------------------------

class OWLRealValueSpaceSubset(ValueSpaceSubset):
    """
    A subset of the owl:real value space.

    Represented as a list of intervals (lower, upper, lower_inclusive, upper_inclusive).
    """

    def __init__(self, intervals: list[Interval] | None = None, empty: bool = False) -> None:
        if empty:
            self._intervals: list[Interval] = []
        elif intervals is None:
            # Entire space: (-∞, +∞)
            neg_inf = BigRational.infinity(False)
            pos_inf = BigRational.infinity(True)
            self._intervals = [(neg_inf, pos_inf, True, True)]
        else:
            self._intervals = intervals

    def is_empty(self) -> bool:
        return len(self._intervals) == 0

    def contains(self, value: Any) -> bool:
        if not isinstance(value, BigRational):
            return False
        for lo, hi, lo_inc, hi_inc in self._intervals:
            if self._in_range(value, lo, hi, lo_inc, hi_inc):
                return True
        return False

    @staticmethod
    def _in_range(val: BigRational, lo: Any, hi: Any, lo_inc: bool, hi_inc: bool) -> bool:
        lo_ok = bool((val > lo) if not lo_inc else (val >= lo))
        hi_ok = bool((val < hi) if not hi_inc else (val <= hi))
        return lo_ok and hi_ok

    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        if not isinstance(other, OWLRealValueSpaceSubset):
            return OWLRealValueSpaceSubset(empty=True)
        result: list[Interval] = []
        for a in self._intervals:
            for b in other._intervals:
                inter = self._intersect_intervals(a, b)
                if inter is not None:
                    result.append(inter)
        return OWLRealValueSpaceSubset(result if result else None, empty=not result)

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

    def complement(self) -> ValueSpaceSubset:
        neg_inf = BigRational.infinity(False)
        pos_inf = BigRational.infinity(True)
        result: list[Interval] = []
        prev_hi: BigRational = neg_inf
        prev_hi_inc = True

        for lo, hi, lo_inc, hi_inc in sorted(self._intervals, key=lambda x: x[0]):
            if lo > prev_hi or (lo == prev_hi and (lo_inc or prev_hi_inc)):
                # Gap before this interval
                result.append((prev_hi, lo, prev_hi_inc, not lo_inc))
            if hi > prev_hi or (hi == prev_hi and hi_inc):
                prev_hi = hi
                prev_hi_inc = hi_inc

        if prev_hi < pos_inf or (prev_hi == pos_inf and not prev_hi_inc):
            result.append((prev_hi, pos_inf, not prev_hi_inc, True))

        return OWLRealValueSpaceSubset(result if result else None, empty=not result)

    def __repr__(self) -> str:
        if not self._intervals:
            return "OWLRealValueSpaceSubset(∅)"
        parts = []
        for lo, hi, lo_i, hi_i in self._intervals:
            lb = "[" if lo_i else "("
            rb = "]" if hi_i else ")"
            parts.append(f"{lb}{lo},{hi}{rb}")
        return f"OWLRealValueSpaceSubset({' ∪ '.join(parts)})"


# ---------------------------------------------------------------------------
# OWLRealDatatypeHandler
# ---------------------------------------------------------------------------

OWL_REAL_IRIS = (
    "http://www.w3.org/2002/07/owl#real",
    "http://www.w3.org/2001/XMLSchema#decimal",
    "http://www.w3.org/2001/XMLSchema#integer",
    "http://www.w3.org/2001/XMLSchema#nonPositiveInteger",
    "http://www.w3.org/2001/XMLSchema#negativeInteger",
    "http://www.w3.org/2001/XMLSchema#nonNegativeInteger",
    "http://www.w3.org/2001/XMLSchema#positiveInteger",
    "http://www.w3.org/2001/XMLSchema#long",
    "http://www.w3.org/2001/XMLSchema#int",
    "http://www.w3.org/2001/XMLSchema#short",
    "http://www.w3.org/2001/XMLSchema#byte",
    "http://www.w3.org/2001/XMLSchema#unsignedLong",
    "http://www.w3.org/2001/XMLSchema#unsignedInt",
    "http://www.w3.org/2001/XMLSchema#unsignedShort",
    "http://www.w3.org/2001/XMLSchema#unsignedByte",
)


class OWLRealDatatypeHandler(DatatypeHandler):
    """Handler for owl:real and xsd numeric datatypes."""

    def get_datatype_iris(self) -> tuple[str, ...]:
        return OWL_REAL_IRIS

    def parse_literal(self, lexical_form: str, datatype_iri: str) -> Any:
        try:
            return BigRational(lexical_form)
        except (ValueError, MalformedLiteralException):
            raise MalformedLiteralException(f"Invalid {datatype_iri} literal: {lexical_form!r}") from None

    def create_value_space_subset(
        self,
        datatype_iri: str,
        facet_uris: tuple[str, ...],
        facet_values: tuple[Any, ...],
    ) -> ValueSpaceSubset:
        # Build interval from facet restrictions
        lo: BigRational = BigRational.infinity(False)
        hi: BigRational = BigRational.infinity(True)
        lo_inc = True
        hi_inc = True

        xsd_ns = "http://www.w3.org/2001/XMLSchema#"

        def _to_rational(v: Any) -> BigRational:
            if isinstance(v, BigRational):
                return v
            raw = v.data_value if hasattr(v, "data_value") else v
            return BigRational(raw)

        for uri, val in zip(facet_uris, facet_values, strict=True):
            br = _to_rational(val)
            if uri == xsd_ns + "minInclusive":
                if br < lo or (br == lo and not lo_inc):
                    lo, lo_inc = br, True
            elif uri == xsd_ns + "maxInclusive":
                if br > hi or (br == hi and not hi_inc):
                    hi, hi_inc = br, True
            elif uri == xsd_ns + "minExclusive":
                if br > lo or (br == lo and lo_inc):
                    lo, lo_inc = br, False
            elif uri == xsd_ns + "maxExclusive":
                if br < hi or (br == hi and hi_inc):
                    hi, hi_inc = br, False

        if lo > hi or (lo == hi and not (lo_inc and hi_inc)):
            return OWLRealValueSpaceSubset(empty=True)
        return OWLRealValueSpaceSubset([(lo, hi, lo_inc, hi_inc)])

    def entire_space(self, datatype_iri: str) -> ValueSpaceSubset:
        return OWLRealValueSpaceSubset()

    def empty_space(self, datatype_iri: str) -> ValueSpaceSubset:
        return OWLRealValueSpaceSubset(empty=True)


# Register
DatatypeRegistry.register(OWLRealDatatypeHandler())
