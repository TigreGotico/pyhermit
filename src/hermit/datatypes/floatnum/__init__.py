"""xsd:float datatype handler.

Implements the xsd:float value space at the bit level, mirroring Java
HermiT: the value space is discrete (consecutive float32 bit patterns),
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
XSD_FLOAT = XSD_NS + "float"

_SIGN_MASK = 0x80000000
_MAGNITUDE_MASK = 0x7FFFFFFF
_INFINITY_MAGNITUDE = 0x7F800000
_NAN_BITS = 0x7FC00000


def float_to_bits(value: float) -> int:
    """Return the canonical float32 bit pattern of *value* (NaN canonicalised)."""
    if math.isnan(value):
        return _NAN_BITS
    try:
        packed = struct.pack("<f", value)
    except OverflowError:
        packed = struct.pack("<f", math.inf if value > 0 else -math.inf)
    return int(struct.unpack("<I", packed)[0])


def bits_to_float(bits: int) -> float:
    return float(struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0])


def is_nan_bits(bits: int) -> bool:
    return (bits & _INFINITY_MAGNITUDE) == _INFINITY_MAGNITUDE and (
        bits & 0x007FFFFF
    ) != 0


class FloatValue:
    """An xsd:float data value with bit-level identity."""

    __slots__ = ("_bits", "_value")

    def __init__(self, value: float) -> None:
        self._bits = float_to_bits(value)
        self._value = bits_to_float(self._bits)

    @classmethod
    def from_bits(cls, bits: int) -> FloatValue:
        result = cls.__new__(cls)
        result._bits = bits & 0xFFFFFFFF
        result._value = bits_to_float(bits)
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
        return hash(("float", self._bits))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FloatValue):
            return self._bits == other._bits
        return False

    def __repr__(self) -> str:
        return f"FloatValue({self._value!r})"

    @classmethod
    def parse(cls, lexical_form: str) -> FloatValue:
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
                f"Invalid xsd:float literal: {lexical_form!r}"
            ) from None


NEGATIVE_INFINITY_BITS = float_to_bits(-math.inf)
POSITIVE_INFINITY_BITS = float_to_bits(math.inf)
POSITIVE_ZERO_BITS = float_to_bits(0.0)
NEGATIVE_ZERO_BITS = float_to_bits(-0.0)


def next_float_bits(bits: int) -> int:
    """The successor of a float in the bit-level total order."""
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


def previous_float_bits(bits: int) -> int:
    """The predecessor of a float in the bit-level total order."""
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
    """Subtract the number of floats in [lower, upper] from *argument*."""
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


class FloatInterval:
    """An inclusive interval of float32 bit patterns (no NaN)."""

    __slots__ = ("m_lower_bound_bits", "m_upper_bound_bits")

    def __init__(self, lower_bound_bits: int, upper_bound_bits: int) -> None:
        self.m_lower_bound_bits = lower_bound_bits
        self.m_upper_bound_bits = upper_bound_bits

    def intersect_with(self, that: FloatInterval) -> FloatInterval | None:
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
        return FloatInterval(new_lower, new_upper)

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
            values.append(FloatValue.from_bits(bits))
            bits = next_float_bits(bits)
        values.append(FloatValue.from_bits(self.m_upper_bound_bits))

    def __repr__(self) -> str:
        return f"FLOAT[{bits_to_float(self.m_lower_bound_bits)}..{bits_to_float(self.m_upper_bound_bits)}]"


class FloatValueSpaceSubset(ValueSpaceSubset):
    def __init__(self, empty: bool = False, entire: bool = False):
        self._empty = empty
        self._entire = entire

    def is_empty(self) -> bool:
        return self._empty

    def contains(self, value: Any) -> bool:
        return self._entire or not self._empty

    def intersect(self, other: ValueSpaceSubset) -> ValueSpaceSubset:
        if isinstance(other, FloatValueSpaceSubset):
            if self._empty or other._empty:
                return FloatValueSpaceSubset(empty=True)
            if self._entire:
                return other
            if other._entire:
                return self
            return FloatValueSpaceSubset()
        return FloatValueSpaceSubset(empty=True)

    def complement(self) -> ValueSpaceSubset:
        if self._entire:
            return FloatValueSpaceSubset(empty=True)
        if self._empty:
            return FloatValueSpaceSubset(entire=True)
        return FloatValueSpaceSubset()


class EntireFloatSubset(FloatValueSpaceSubset):
    """The entire xsd:float value space (all floats and NaN)."""

    def __init__(self) -> None:
        super().__init__(entire=True)

    def contains_data_value(self, value: Any) -> bool:
        return isinstance(value, FloatValue)

    def has_cardinality_at_least(self, number: int) -> bool:
        leftover = subtract_interval_size_from(
            NEGATIVE_INFINITY_BITS, POSITIVE_INFINITY_BITS, number
        )
        # The check allows 1 because there is one NaN in the value space.
        return leftover <= 1

    def enumerate_data_values(self, data_values: list[Any]) -> None:
        raise RuntimeError("The xsd:float value space is too large to enumerate.")


class EmptyFloatSubset(FloatValueSpaceSubset):
    """The empty xsd:float value space subset."""

    def __init__(self) -> None:
        super().__init__(empty=True)

    def contains_data_value(self, value: Any) -> bool:
        return False

    def has_cardinality_at_least(self, number: int) -> bool:
        return number <= 0

    def enumerate_data_values(self, data_values: list[Any]) -> None:
        return None


class NoNaNFloatSubset(FloatValueSpaceSubset):
    """A union of float intervals; never contains NaN."""

    def __init__(self, intervals: list[FloatInterval]) -> None:
        super().__init__()
        self.m_intervals = intervals

    def contains_data_value(self, value: Any) -> bool:
        if not isinstance(value, FloatValue):
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


_FLOAT_ENTIRE = EntireFloatSubset()
_EMPTY_SUBSET = EmptyFloatSubset()

_SUPPORTED_FACET_URIS = frozenset({
    XSD_NS + "minInclusive",
    XSD_NS + "minExclusive",
    XSD_NS + "maxInclusive",
    XSD_NS + "maxExclusive",
})


def _facet_bits(facet_value: Any) -> int:
    raw = facet_data_value(facet_value)
    if isinstance(raw, FloatValue):
        return raw.bits
    if isinstance(raw, bool):
        raise UnsupportedFacetException(
            "xsd:float facets take only floats as values."
        )
    if isinstance(raw, (int, float)):
        return float_to_bits(float(raw))
    fraction = getattr(raw, "fraction", None)
    if fraction is not None:
        return float_to_bits(float(fraction))
    if isinstance(raw, str):
        return FloatValue.parse(raw).bits
    raise UnsupportedFacetException(
        f"xsd:float facets take only floats as values, not {raw!r}."
    )


class FloatDatatypeHandler(DatatypeHandler):
    IRIS = (XSD_FLOAT,)

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
            raise MalformedLiteralException(f"Invalid float: {lexical_form!r}") from None

    def parse_data_value(self, lexical_form: str, datatype_iri: str) -> Any:
        return FloatValue.parse(lexical_form)

    def validate_datatype_restriction(self, datatype_restriction: Any) -> None:
        for index in range(datatype_restriction.number_of_facet_restrictions() - 1, -1, -1):
            facet_uri = datatype_restriction.facet_uri(index)
            if facet_uri not in _SUPPORTED_FACET_URIS:
                raise UnsupportedFacetException(
                    f"A facet with URI '{facet_uri}' is not supported on xsd:float; "
                    "only xsd:minInclusive, xsd:maxInclusive, xsd:minExclusive, "
                    "and xsd:maxExclusive are supported."
                )
            _facet_bits(datatype_restriction.facet_value(index))

    def create_value_space_subset(
        self, datatype_iri: str, facet_uris: Any, facet_values: Any
    ) -> FloatValueSpaceSubset:
        if not facet_uris:
            return _FLOAT_ENTIRE
        interval = self._interval_for(facet_uris, facet_values)
        if interval is None:
            return _EMPTY_SUBSET
        return NoNaNFloatSubset([interval])

    def conjoin_with_dr(
        self, value_space_subset: ValueSpaceSubset, datatype_restriction: Any
    ) -> ValueSpaceSubset:
        facet_uris: tuple[str, ...] = getattr(datatype_restriction, "_facet_uris", ())
        facet_values: tuple[Any, ...] = getattr(datatype_restriction, "_facet_values", ())
        if not facet_uris or isinstance(value_space_subset, EmptyFloatSubset):
            return value_space_subset
        interval = self._interval_for(facet_uris, facet_values)
        if interval is None:
            return _EMPTY_SUBSET
        if isinstance(value_space_subset, EntireFloatSubset):
            return NoNaNFloatSubset([interval])
        assert isinstance(value_space_subset, NoNaNFloatSubset)
        new_intervals: list[FloatInterval] = []
        for old_interval in value_space_subset.m_intervals:
            intersection = old_interval.intersect_with(interval)
            if intersection is not None:
                new_intervals.append(intersection)
        if not new_intervals:
            return _EMPTY_SUBSET
        return NoNaNFloatSubset(new_intervals)

    def conjoin_with_dr_negation(
        self, value_space_subset: ValueSpaceSubset, datatype_restriction: Any
    ) -> ValueSpaceSubset:
        facet_uris: tuple[str, ...] = getattr(datatype_restriction, "_facet_uris", ())
        facet_values: tuple[Any, ...] = getattr(datatype_restriction, "_facet_values", ())
        if not facet_uris or isinstance(value_space_subset, EmptyFloatSubset):
            return _EMPTY_SUBSET
        interval = self._interval_for(facet_uris, facet_values)
        if interval is None:
            return value_space_subset
        complement_intervals: list[FloatInterval] = []
        if interval.m_lower_bound_bits != NEGATIVE_INFINITY_BITS:
            complement_intervals.append(
                FloatInterval(
                    NEGATIVE_INFINITY_BITS,
                    previous_float_bits(interval.m_lower_bound_bits),
                )
            )
        if interval.m_upper_bound_bits != POSITIVE_INFINITY_BITS:
            complement_intervals.append(
                FloatInterval(
                    next_float_bits(interval.m_upper_bound_bits),
                    POSITIVE_INFINITY_BITS,
                )
            )
        if isinstance(value_space_subset, EntireFloatSubset):
            if not complement_intervals:
                return _EMPTY_SUBSET
            return NoNaNFloatSubset(complement_intervals)
        assert isinstance(value_space_subset, NoNaNFloatSubset)
        new_intervals: list[FloatInterval] = []
        for old_interval in value_space_subset.m_intervals:
            for complement_interval in complement_intervals:
                intersection = old_interval.intersect_with(complement_interval)
                if intersection is not None:
                    new_intervals.append(intersection)
        if not new_intervals:
            return _EMPTY_SUBSET
        return NoNaNFloatSubset(new_intervals)

    @staticmethod
    def _interval_for(
        facet_uris: tuple[str, ...], facet_values: tuple[Any, ...]
    ) -> FloatInterval | None:
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
                bits = next_float_bits(bits)
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
                bits = previous_float_bits(bits)
                if is_smaller_equal_bits(bits, upper_bound_bits):
                    upper_bound_bits = bits
            else:
                raise UnsupportedFacetException(
                    f"Facet '{facet_uri}' is not supported by xsd:float."
                )
        if not is_smaller_equal_bits(lower_bound_bits, upper_bound_bits):
            return None
        return FloatInterval(lower_bound_bits, upper_bound_bits)

    def entire_space(self, datatype_iri: str) -> FloatValueSpaceSubset:
        return _FLOAT_ENTIRE

    def empty_space(self, datatype_iri: str) -> FloatValueSpaceSubset:
        return _EMPTY_SUBSET

DatatypeRegistry.register(FloatDatatypeHandler())
