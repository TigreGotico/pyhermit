"""xsd:double datatype handler.

Implements the xsd:double value space at the bit level, mirroring Java
HermiT: the value space is discrete (consecutive float64 bit patterns),
+0.0 and -0.0 are distinct values, and NaN is a single extra value.
"""
from __future__ import annotations

import math
import struct
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
XSD_DOUBLE = XSD_NS + "double"

_SIGN_MASK = 0x8000000000000000
_MAGNITUDE_MASK = 0x7FFFFFFFFFFFFFFF
_INFINITY_MAGNITUDE = 0x7FF0000000000000
_NAN_BITS = 0x7FF8000000000000


def double_to_bits(value: float) -> int:
    """Return the canonical float64 bit pattern of *value* (NaN canonicalised)."""
    if math.isnan(value):
        return _NAN_BITS
    return int(struct.unpack("<Q", struct.pack("<d", value))[0])


def bits_to_double(bits: int) -> float:
    return float(struct.unpack("<d", struct.pack("<Q", bits & 0xFFFFFFFFFFFFFFFF))[0])


def is_nan_bits(bits: int) -> bool:
    return (bits & _INFINITY_MAGNITUDE) == _INFINITY_MAGNITUDE and (
        bits & 0x000FFFFFFFFFFFFF
    ) != 0


class DoubleValue:
    """An xsd:double data value with bit-level identity."""

    __slots__ = ("_bits", "_value")

    def __init__(self, value: float) -> None:
        self._bits = double_to_bits(value)
        self._value = bits_to_double(self._bits)

    @classmethod
    def from_bits(cls, bits: int) -> DoubleValue:
        result = cls.__new__(cls)
        result._bits = bits & 0xFFFFFFFFFFFFFFFF
        result._value = bits_to_double(bits)
        return result

    @property
    def value(self) -> float:
        return self._value

    @property
    def bits(self) -> int:
        return self._bits

    def is_nan(self) -> bool:
        return is_nan_bits(self._bits)

    def __hash__(self) -> int:
        return hash(("double", self._bits))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DoubleValue):
            return self._bits == other._bits
        return False

    def __repr__(self) -> str:
        return f"DoubleValue({self._value!r})"

    @classmethod
    def parse(cls, lexical_form: str) -> DoubleValue:
        text = lexical_form.strip()
        if text == "INF" or text == "+INF":
            return cls(math.inf)
        if text == "-INF":
            return cls(-math.inf)
        if text == "NaN":
            return cls(math.nan)
        try:
            return cls(float(text))
        except ValueError:
            raise MalformedLiteralException(
                f"Invalid xsd:double literal: {lexical_form!r}"
            ) from None


NEGATIVE_INFINITY_BITS = double_to_bits(-math.inf)
POSITIVE_INFINITY_BITS = double_to_bits(math.inf)
POSITIVE_ZERO_BITS = double_to_bits(0.0)
NEGATIVE_ZERO_BITS = double_to_bits(-0.0)


def next_double_bits(bits: int) -> int:
    """The successor of a double in the bit-level total order."""
    magnitude = bits & _MAGNITUDE_MASK
    positive = (bits & _SIGN_MASK) == 0
    # The successors of NaN and +INF are these numbers themselves.
    if is_nan_bits(bits) or (magnitude == _INFINITY_MAGNITUDE and positive):
        return bits
    if positive:
        return magnitude + 1
    if magnitude == 0:
        # The successor of -0 is +0.
        return 0
    return (magnitude - 1) | _SIGN_MASK


def previous_double_bits(bits: int) -> int:
    """The predecessor of a double in the bit-level total order."""
    magnitude = bits & _MAGNITUDE_MASK
    positive = (bits & _SIGN_MASK) == 0
    # The predecessors of NaN and -INF are these numbers themselves.
    if is_nan_bits(bits) or (magnitude == _INFINITY_MAGNITUDE and not positive):
        return bits
    if not positive:
        return (magnitude + 1) | _SIGN_MASK
    if magnitude == 0:
        # The predecessor of +0 is -0.
        return _SIGN_MASK
    return magnitude - 1


def _is_smaller_equal_parts(
    positive1: bool, magnitude1: int, positive2: bool, magnitude2: int
) -> bool:
    if positive1 and positive2:
        return magnitude1 <= magnitude2
    if not positive1 and positive2:
        return True
    if positive1 and not positive2:
        return False
    return magnitude1 >= magnitude2


def is_smaller_equal_bits(bits1: int, bits2: int) -> bool:
    if is_nan_bits(bits1) or is_nan_bits(bits2):
        return False
    return _is_smaller_equal_parts(
        (bits1 & _SIGN_MASK) == 0,
        bits1 & _MAGNITUDE_MASK,
        (bits2 & _SIGN_MASK) == 0,
        bits2 & _MAGNITUDE_MASK,
    )


def subtract_interval_size_from(
    lower_bound_bits: int, upper_bound_bits: int, argument: int
) -> int:
    """Subtract the number of doubles in [lower, upper] from *argument*."""
    if argument <= 0:
        return 0
    if is_nan_bits(lower_bound_bits) or is_nan_bits(upper_bound_bits):
        return argument
    positive_lower = (lower_bound_bits & _SIGN_MASK) == 0
    positive_upper = (upper_bound_bits & _SIGN_MASK) == 0
    magnitude_lower = lower_bound_bits & _MAGNITUDE_MASK
    magnitude_upper = upper_bound_bits & _MAGNITUDE_MASK
    if not _is_smaller_equal_parts(
        positive_lower, magnitude_lower, positive_upper, magnitude_upper
    ):
        return argument
    if positive_lower and positive_upper:
        size = magnitude_upper - magnitude_lower + 1
        return max(argument - size, 0)
    if not positive_lower and not positive_upper:
        size = magnitude_lower - magnitude_upper + 1
        return max(argument - size, 0)
    # Lower bound negative, upper bound positive.
    start_to_minus_zero = magnitude_lower + 1
    if start_to_minus_zero >= argument:
        return 0
    argument -= start_to_minus_zero
    plus_zero_to_end = 1 + magnitude_upper
    if plus_zero_to_end >= argument:
        return 0
    return argument - plus_zero_to_end


class DoubleInterval:
    """An inclusive interval of float64 bit patterns (no NaN)."""

    __slots__ = ("m_lower_bound_bits", "m_upper_bound_bits")

    def __init__(self, lower_bound_bits: int, upper_bound_bits: int) -> None:
        self.m_lower_bound_bits = lower_bound_bits
        self.m_upper_bound_bits = upper_bound_bits

    def intersect_with(self, that: DoubleInterval) -> DoubleInterval | None:
        if is_smaller_equal_bits(self.m_lower_bound_bits, that.m_lower_bound_bits):
            new_lower = that.m_lower_bound_bits
        else:
            new_lower = self.m_lower_bound_bits
        if is_smaller_equal_bits(self.m_upper_bound_bits, that.m_upper_bound_bits):
            new_upper = self.m_upper_bound_bits
        else:
            new_upper = that.m_upper_bound_bits
        if not is_smaller_equal_bits(new_lower, new_upper):
            return None
        if new_lower == self.m_lower_bound_bits and new_upper == self.m_upper_bound_bits:
            return self
        if new_lower == that.m_lower_bound_bits and new_upper == that.m_upper_bound_bits:
            return that
        return DoubleInterval(new_lower, new_upper)

    def subtract_size_from(self, argument: int) -> int:
        return subtract_interval_size_from(
            self.m_lower_bound_bits, self.m_upper_bound_bits, argument
        )

    def contains_bits(self, bits: int) -> bool:
        if is_nan_bits(bits):
            return False
        return is_smaller_equal_bits(
            self.m_lower_bound_bits, bits
        ) and is_smaller_equal_bits(bits, self.m_upper_bound_bits)

    def enumerate_values(self, values: list[Any]) -> None:
        bits = self.m_lower_bound_bits
        while bits != self.m_upper_bound_bits:
            values.append(DoubleValue.from_bits(bits))
            bits = next_double_bits(bits)
        values.append(DoubleValue.from_bits(self.m_upper_bound_bits))

    def __repr__(self) -> str:
        return f"DOUBLE[{bits_to_double(self.m_lower_bound_bits)}..{bits_to_double(self.m_upper_bound_bits)}]"


class DoubleValueSpaceSubset(ValueSpaceSubset):
    def __init__(
        self,
        values: frozenset[float] | None = None,
        empty: bool = False,
        entire: bool = False,
        _negated: bool = False,
    ):
        self._empty = empty or (values is not None and len(values) == 0 and not _negated)
        self._entire = entire and not self._empty
        self._values = values if values is not None else frozenset()
        self._negated = _negated and not self._entire and not self._empty

    def is_empty(self) -> bool:
        return self._empty

    def contains(self, value: Any) -> bool:
        if self._entire:
            return isinstance(value, float)
        if self._empty:
            return False
        if self._negated:
            return isinstance(value, float) and value not in self._values
        return value in self._values

    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        if isinstance(other, DoubleValueSpaceSubset):
            if self._entire:
                return other
            if other._entire:
                return self
            if self._empty or other._empty:
                return DoubleValueSpaceSubset(empty=True)
            if self._negated and other._negated:
                # complement(A) ∩ complement(B) = complement(A ∪ B)
                return DoubleValueSpaceSubset(values=self._values | other._values, _negated=True)
            if self._negated:
                # complement(A) ∩ B = B - A
                return DoubleValueSpaceSubset(values=other._values - self._values)
            if other._negated:
                # A ∩ complement(B) = A - B
                return DoubleValueSpaceSubset(values=self._values - other._values)
            return DoubleValueSpaceSubset(values=self._values & other._values)
        return DoubleValueSpaceSubset(empty=True)

    def complement(self) -> ValueSpaceSubset:
        if self._entire:
            return DoubleValueSpaceSubset(empty=True)
        if self._empty:
            return DoubleValueSpaceSubset(entire=True)
        if self._negated:
            # complement of complement(A) = A
            return DoubleValueSpaceSubset(values=self._values)
        # complement of finite set = negated finite set
        return DoubleValueSpaceSubset(values=self._values, _negated=True)


class EntireDoubleSubset(DoubleValueSpaceSubset):
    """The entire xsd:double value space (all doubles and NaN)."""

    def __init__(self) -> None:
        super().__init__(entire=True)

    def contains_data_value(self, value: Any) -> bool:
        return isinstance(value, DoubleValue)

    def has_cardinality_at_least(self, number: int) -> bool:
        leftover = subtract_interval_size_from(
            NEGATIVE_INFINITY_BITS, POSITIVE_INFINITY_BITS, number
        )
        # The check allows 1 because there is one NaN in the value space.
        return leftover <= 1

    def enumerate_data_values(self, data_values: list[Any]) -> None:
        raise RuntimeError("The xsd:double value space is too large to enumerate.")


class EmptyDoubleSubset(DoubleValueSpaceSubset):
    """The empty xsd:double value space subset."""

    def __init__(self) -> None:
        super().__init__(empty=True)

    def contains_data_value(self, value: Any) -> bool:
        return False

    def has_cardinality_at_least(self, number: int) -> bool:
        return number <= 0

    def enumerate_data_values(self, data_values: list[Any]) -> None:
        return None


class NoNaNDoubleSubset(DoubleValueSpaceSubset):
    """A union of double intervals; never contains NaN."""

    def __init__(self, intervals: list[DoubleInterval]) -> None:
        super().__init__()
        self.m_intervals = intervals

    def contains_data_value(self, value: Any) -> bool:
        if not isinstance(value, DoubleValue):
            return False
        return any(interval.contains_bits(value.bits) for interval in self.m_intervals)

    def has_cardinality_at_least(self, number: int) -> bool:
        left = number
        for interval in self.m_intervals:
            if left <= 0:
                break
            left = interval.subtract_size_from(left)
        return left <= 0

    def enumerate_data_values(self, data_values: list[Any]) -> None:
        for interval in self.m_intervals:
            interval.enumerate_values(data_values)


_DOUBLE_ENTIRE = EntireDoubleSubset()
_EMPTY_SUBSET = EmptyDoubleSubset()

_SUPPORTED_FACET_URIS = frozenset({
    XSD_NS + "minInclusive",
    XSD_NS + "minExclusive",
    XSD_NS + "maxInclusive",
    XSD_NS + "maxExclusive",
})


def _facet_bits(facet_value: Any) -> int:
    raw = facet_data_value(facet_value)
    if isinstance(raw, DoubleValue):
        return raw.bits
    if isinstance(raw, bool):
        raise UnsupportedFacetException(
            "xsd:double facets take only doubles as values."
        )
    if isinstance(raw, (int, float)):
        return double_to_bits(float(raw))
    fraction = getattr(raw, "fraction", None)
    if fraction is not None:
        return double_to_bits(float(fraction))
    if isinstance(raw, str):
        return DoubleValue.parse(raw).bits
    raise UnsupportedFacetException(
        f"xsd:double facets take only doubles as values, not {raw!r}."
    )


class DoubleDatatypeHandler(DatatypeHandler):
    IRIS = (XSD_DOUBLE,)

    def get_datatype_iris(self) -> tuple[str, ...]:
        return self.IRIS

    def parse_literal(self, lexical_form: str, datatype_iri: str) -> Any:
        try:
            return float(lexical_form)
        except ValueError:
            if lexical_form == "INF" or lexical_form == "+INF":
                return math.inf
            if lexical_form == "-INF":
                return -math.inf
            raise MalformedLiteralException(f"Invalid double: {lexical_form!r}") from None

    def parse_data_value(self, lexical_form: str, datatype_iri: str) -> Any:
        return DoubleValue.parse(lexical_form)

    def validate_datatype_restriction(self, datatype_restriction: Any) -> None:
        for index in range(datatype_restriction.number_of_facet_restrictions() - 1, -1, -1):
            facet_uri = datatype_restriction.facet_uri(index)
            if facet_uri not in _SUPPORTED_FACET_URIS:
                raise UnsupportedFacetException(
                    f"A facet with URI '{facet_uri}' is not supported on xsd:double; "
                    "only xsd:minInclusive, xsd:maxInclusive, xsd:minExclusive, "
                    "and xsd:maxExclusive are supported."
                )
            _facet_bits(datatype_restriction.facet_value(index))

    def create_value_space_subset(
        self, datatype_iri: str, facet_uris: tuple[str, ...], facet_values: tuple[object, ...]
    ) -> ValueSpaceSubset:
        if not facet_uris:
            return _DOUBLE_ENTIRE
        interval = self._interval_for(facet_uris, facet_values)
        if interval is None:
            return _EMPTY_SUBSET
        return NoNaNDoubleSubset([interval])

    def conjoin_with_dr(
        self, value_space_subset: ValueSpaceSubset, datatype_restriction: Any
    ) -> ValueSpaceSubset:
        facet_uris: tuple[str, ...] = getattr(datatype_restriction, "_facet_uris", ())
        facet_values: tuple[Any, ...] = getattr(datatype_restriction, "_facet_values", ())
        if not facet_uris or isinstance(value_space_subset, EmptyDoubleSubset):
            return value_space_subset
        interval = self._interval_for(facet_uris, facet_values)
        if interval is None:
            return _EMPTY_SUBSET
        if isinstance(value_space_subset, EntireDoubleSubset):
            return NoNaNDoubleSubset([interval])
        assert isinstance(value_space_subset, NoNaNDoubleSubset)
        new_intervals: list[DoubleInterval] = []
        for old_interval in value_space_subset.m_intervals:
            intersection = old_interval.intersect_with(interval)
            if intersection is not None:
                new_intervals.append(intersection)
        if not new_intervals:
            return _EMPTY_SUBSET
        return NoNaNDoubleSubset(new_intervals)

    def conjoin_with_dr_negation(
        self, value_space_subset: ValueSpaceSubset, datatype_restriction: Any
    ) -> ValueSpaceSubset:
        facet_uris: tuple[str, ...] = getattr(datatype_restriction, "_facet_uris", ())
        facet_values: tuple[Any, ...] = getattr(datatype_restriction, "_facet_values", ())
        if not facet_uris or isinstance(value_space_subset, EmptyDoubleSubset):
            return _EMPTY_SUBSET
        interval = self._interval_for(facet_uris, facet_values)
        if interval is None:
            return value_space_subset
        complement_intervals: list[DoubleInterval] = []
        if interval.m_lower_bound_bits != NEGATIVE_INFINITY_BITS:
            complement_intervals.append(
                DoubleInterval(
                    NEGATIVE_INFINITY_BITS,
                    previous_double_bits(interval.m_lower_bound_bits),
                )
            )
        if interval.m_upper_bound_bits != POSITIVE_INFINITY_BITS:
            complement_intervals.append(
                DoubleInterval(
                    next_double_bits(interval.m_upper_bound_bits),
                    POSITIVE_INFINITY_BITS,
                )
            )
        if isinstance(value_space_subset, EntireDoubleSubset):
            if not complement_intervals:
                return _EMPTY_SUBSET
            return NoNaNDoubleSubset(complement_intervals)
        assert isinstance(value_space_subset, NoNaNDoubleSubset)
        new_intervals: list[DoubleInterval] = []
        for old_interval in value_space_subset.m_intervals:
            for complement_interval in complement_intervals:
                intersection = old_interval.intersect_with(complement_interval)
                if intersection is not None:
                    new_intervals.append(intersection)
        if not new_intervals:
            return _EMPTY_SUBSET
        return NoNaNDoubleSubset(new_intervals)

    @staticmethod
    def _interval_for(
        facet_uris: tuple[str, ...], facet_values: tuple[Any, ...]
    ) -> DoubleInterval | None:
        lower_bound_bits = NEGATIVE_INFINITY_BITS
        upper_bound_bits = POSITIVE_INFINITY_BITS
        for facet_uri, facet_value in zip(facet_uris, facet_values, strict=False):
            bits = _facet_bits(facet_value)
            if facet_uri == XSD_NS + "minInclusive":
                if bits == POSITIVE_ZERO_BITS:
                    bits = NEGATIVE_ZERO_BITS
                if is_smaller_equal_bits(lower_bound_bits, bits):
                    lower_bound_bits = bits
            elif facet_uri == XSD_NS + "minExclusive":
                if bits == NEGATIVE_ZERO_BITS:
                    bits = POSITIVE_ZERO_BITS
                bits = next_double_bits(bits)
                if is_smaller_equal_bits(lower_bound_bits, bits):
                    lower_bound_bits = bits
            elif facet_uri == XSD_NS + "maxInclusive":
                if bits == NEGATIVE_ZERO_BITS:
                    bits = POSITIVE_ZERO_BITS
                if is_smaller_equal_bits(bits, upper_bound_bits):
                    upper_bound_bits = bits
            elif facet_uri == XSD_NS + "maxExclusive":
                if bits == POSITIVE_ZERO_BITS:
                    bits = NEGATIVE_ZERO_BITS
                bits = previous_double_bits(bits)
                if is_smaller_equal_bits(bits, upper_bound_bits):
                    upper_bound_bits = bits
            else:
                raise UnsupportedFacetException(
                    f"Facet '{facet_uri}' is not supported by xsd:double."
                )
        if not is_smaller_equal_bits(lower_bound_bits, upper_bound_bits):
            return None
        return DoubleInterval(lower_bound_bits, upper_bound_bits)

    def entire_space(self, datatype_iri: str) -> ValueSpaceSubset:
        return _DOUBLE_ENTIRE

    def empty_space(self, datatype_iri: str) -> ValueSpaceSubset:
        return _EMPTY_SUBSET

DatatypeRegistry.register(DoubleDatatypeHandler())
