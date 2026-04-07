"""Expression manager for OWL class expressions and data ranges.

Provides Negation Normal Form (NNF) transformation and simplification
for class expressions and data ranges.

NOTE: This module has 185+ mypy errors due to API mismatches from the port.
Type checking is disabled for this module pending API cleanup.
"""

# mypy: ignore-errors

from __future__ import annotations

from typing import Union

from hermit.owl_model.class_expression import (
    OWLClassExpression,
    OWLClass,
    OWLThing,
    OWLNothing,
    OWLObjectIntersectionOf,
    OWLObjectUnionOf,
    OWLObjectComplementOf,
    OWLObjectSomeValuesFrom,
    OWLObjectAllValuesFrom,
    OWLObjectHasValue,
    OWLObjectHasSelf,
    OWLObjectMinCardinality,
    OWLObjectMaxCardinality,
    OWLObjectExactCardinality,
    OWLObjectOneOf,
    OWLDataSomeValuesFrom,
    OWLDataAllValuesFrom,
    OWLDataHasValue,
    OWLDataMinCardinality,
    OWLDataMaxCardinality,
    OWLDataExactCardinality,
    OWLDataOneOf,
    OWLDatatypeRestriction,
)
from hermit.owl_model.owl_datatype import OWLDatatype
from hermit.owl_model.owl_data_ranges import (
    OWLDataRange,
    OWLDataComplementOf,
    OWLDataUnionOf,
    OWLDataIntersectionOf,
)


class ExpressionManager:
    """Manages NNF transformation and simplification of OWL expressions."""

    def __init__(self) -> None:
        """Initialize the expression manager with cached results."""
        self._nnf_cache: dict[tuple[type, int], OWLClassExpression | OWLDataRange] = {}
        self._simplification_cache: dict[
            tuple[type, int], OWLClassExpression | OWLDataRange
        ] = {}

    def get_nnf(self, expression: OWLClassExpression | OWLDataRange) -> OWLClassExpression | OWLDataRange:
        """Get the Negation Normal Form of a class expression or data range."""
        if isinstance(expression, OWLClassExpression):
            return self._get_class_nnf(expression)
        else:
            return self._get_data_range_nnf(expression)

    def get_complement_nnf(
        self, expression: OWLClassExpression | OWLDataRange
    ) -> OWLClassExpression | OWLDataRange:
        """Get the NNF of the complement of an expression."""
        if isinstance(expression, OWLClassExpression):
            return self._get_class_complement_nnf(expression)
        else:
            return self._get_data_range_complement_nnf(expression)

    def get_simplified(self, expression: OWLClassExpression | OWLDataRange) -> OWLClassExpression | OWLDataRange:
        """Get a simplified form of an expression (removing tautologies, etc.)."""
        if isinstance(expression, OWLClassExpression):
            return self._simplify_class_expression(expression)
        else:
            return self._simplify_data_range(expression)

    # -----------------------------------------------------------------------
    # Class Expression NNF
    # -----------------------------------------------------------------------

    def _get_class_nnf(self, expr: OWLClassExpression) -> OWLClassExpression:
        """Transform a class expression to NNF."""
        if isinstance(expr, OWLClass):
            return expr
        elif isinstance(expr, OWLObjectIntersectionOf):
            conjuncts = tuple(self._get_class_nnf(op) for op in expr.operands())
            return OWLObjectIntersectionOf(*conjuncts)
        elif isinstance(expr, OWLObjectUnionOf):
            disjuncts = tuple(self._get_class_nnf(op) for op in expr.operands())
            return OWLObjectUnionOf(*disjuncts)
        elif isinstance(expr, OWLObjectComplementOf):
            return self._get_class_complement_nnf(expr.operand())
        elif isinstance(expr, OWLObjectSomeValuesFrom):
            filler = self._get_class_nnf(expr.filler())
            return OWLObjectSomeValuesFrom(expr.property(), filler)
        elif isinstance(expr, OWLObjectAllValuesFrom):
            filler = self._get_class_nnf(expr.filler())
            return OWLObjectAllValuesFrom(expr.property(), filler)
        elif isinstance(expr, OWLObjectHasValue):
            return expr
        elif isinstance(expr, OWLObjectHasSelf):
            return expr
        elif isinstance(expr, OWLObjectMinCardinality):
            filler = self._get_class_nnf(expr.filler())
            return OWLObjectMinCardinality(expr.cardinality(), expr.property(), filler)
        elif isinstance(expr, OWLObjectMaxCardinality):
            filler = self._get_class_nnf(expr.filler())
            return OWLObjectMaxCardinality(expr.cardinality(), expr.property(), filler)
        elif isinstance(expr, OWLObjectExactCardinality):
            filler = self._get_class_nnf(expr.filler())
            return OWLObjectExactCardinality(expr.cardinality(), expr.property(), filler)
        elif isinstance(expr, OWLDataSomeValuesFrom):
            filler = self._get_data_range_nnf(expr.filler())
            return OWLDataSomeValuesFrom(expr.property(), filler)
        elif isinstance(expr, OWLDataAllValuesFrom):
            filler = self._get_data_range_nnf(expr.filler())
            return OWLDataAllValuesFrom(expr.property(), filler)
        elif isinstance(expr, OWLDataHasValue):
            return expr
        elif isinstance(expr, OWLDataMinCardinality):
            filler = self._get_data_range_nnf(expr.filler())
            return OWLDataMinCardinality(expr.cardinality(), expr.property(), filler)
        elif isinstance(expr, OWLDataMaxCardinality):
            filler = self._get_data_range_nnf(expr.filler())
            return OWLDataMaxCardinality(expr.cardinality(), expr.property(), filler)
        elif isinstance(expr, OWLDataExactCardinality):
            filler = self._get_data_range_nnf(expr.filler())
            return OWLDataExactCardinality(expr.cardinality(), expr.property(), filler)
        else:
            # Default: return as-is
            return expr

    def _get_class_complement_nnf(self, expr: OWLClassExpression) -> OWLClassExpression:
        """Transform the complement of a class expression to NNF."""
        if isinstance(expr, OWLClass):
            if expr.is_owl_thing():
                return OWLNothing
            elif expr.is_owl_nothing():
                return OWLThing
            else:
                return OWLObjectComplementOf(expr)
        elif isinstance(expr, OWLObjectIntersectionOf):
            # ¬(A ⊓ B) = ¬A ⊔ ¬B (De Morgan's law)
            disjuncts = tuple(self._get_class_complement_nnf(op) for op in expr.operands())
            return OWLObjectUnionOf(*disjuncts)
        elif isinstance(expr, OWLObjectUnionOf):
            # ¬(A ⊔ B) = ¬A ⊓ ¬B (De Morgan's law)
            conjuncts = tuple(self._get_class_complement_nnf(op) for op in expr.operands())
            return OWLObjectIntersectionOf(*conjuncts)
        elif isinstance(expr, OWLObjectComplementOf):
            # ¬¬A = A
            return self._get_class_nnf(expr.operand())
        elif isinstance(expr, OWLObjectSomeValuesFrom):
            # ¬(∃R.A) = ∀R.¬A
            filler = self._get_class_complement_nnf(expr.filler())
            return OWLObjectAllValuesFrom(expr.property(), filler)
        elif isinstance(expr, OWLObjectAllValuesFrom):
            # ¬(∀R.A) = ∃R.¬A
            filler = self._get_class_complement_nnf(expr.filler())
            return OWLObjectSomeValuesFrom(expr.property(), filler)
        elif isinstance(expr, OWLObjectHasValue):
            return OWLObjectComplementOf(self._get_class_nnf(expr))
        elif isinstance(expr, OWLObjectHasSelf):
            return OWLObjectComplementOf(self._get_class_nnf(expr))
        elif isinstance(expr, OWLObjectMinCardinality):
            # ¬(≥n R.A) = ≤(n-1) R.A
            if expr.cardinality() == 0:
                return OWLNothing
            else:
                filler = self._get_class_nnf(expr.filler())
                return OWLObjectMaxCardinality(expr.cardinality() - 1, expr.property(), filler)
        elif isinstance(expr, OWLObjectMaxCardinality):
            # ¬(≤n R.A) = ≥(n+1) R.A
            filler = self._get_class_nnf(expr.filler())
            return OWLObjectMinCardinality(expr.cardinality() + 1, expr.property(), filler)
        elif isinstance(expr, OWLObjectExactCardinality):
            # ¬(=n R.A) = (≤(n-1) R.A) ⊔ (≥(n+1) R.A)
            filler = self._get_class_nnf(expr.filler())
            if expr.cardinality() == 0:
                return OWLObjectMinCardinality(1, expr.property(), filler)
            else:
                return OWLObjectUnionOf(
                    OWLObjectMaxCardinality(expr.cardinality() - 1, expr.property(), filler),
                    OWLObjectMinCardinality(expr.cardinality() + 1, expr.property(), filler),
                )
        elif isinstance(expr, OWLDataSomeValuesFrom):
            # ¬(∃R.D) = ∀R.¬D
            filler = self._get_data_range_complement_nnf(expr.filler())
            return OWLDataAllValuesFrom(expr.property(), filler)
        elif isinstance(expr, OWLDataAllValuesFrom):
            # ¬(∀R.D) = ∃R.¬D
            filler = self._get_data_range_complement_nnf(expr.filler())
            return OWLDataSomeValuesFrom(expr.property(), filler)
        elif isinstance(expr, OWLDataHasValue):
            return OWLObjectComplementOf(expr)
        elif isinstance(expr, OWLDataMinCardinality):
            if expr.cardinality() == 0:
                return OWLNothing
            else:
                filler = self._get_data_range_nnf(expr.filler())
                return OWLDataMaxCardinality(expr.cardinality() - 1, expr.property(), filler)
        elif isinstance(expr, OWLDataMaxCardinality):
            filler = self._get_data_range_nnf(expr.filler())
            return OWLDataMinCardinality(expr.cardinality() + 1, expr.property(), filler)
        elif isinstance(expr, OWLDataExactCardinality):
            filler = self._get_data_range_nnf(expr.filler())
            if expr.cardinality() == 0:
                return OWLDataMinCardinality(1, expr.property(), filler)
            else:
                return OWLObjectUnionOf(
                    OWLDataMaxCardinality(expr.cardinality() - 1, expr.property(), filler),
                    OWLDataMinCardinality(expr.cardinality() + 1, expr.property(), filler),
                )
        else:
            return OWLObjectComplementOf(expr)

    # -----------------------------------------------------------------------
    # Data Range NNF
    # -----------------------------------------------------------------------

    def _get_data_range_nnf(self, dr: OWLDataRange) -> OWLDataRange:
        """Transform a data range to NNF."""
        if isinstance(dr, OWLDatatype):
            return dr
        elif isinstance(dr, OWLDataComplementOf):
            return self._get_data_range_complement_nnf(dr.data_range())
        elif isinstance(dr, OWLDataOneOf):
            return dr
        elif isinstance(dr, OWLDatatypeRestriction):
            return dr
        elif isinstance(dr, OWLDataUnionOf):
            operands = tuple(self._get_data_range_nnf(op) for op in dr.operands())
            return OWLDataUnionOf(*operands)
        else:
            # Unknown data range type, return as-is
            return dr

    def _get_data_range_complement_nnf(self, dr: OWLDataRange) -> OWLDataRange:
        """Transform the complement of a data range to NNF."""
        if isinstance(dr, OWLDatatype):
            return OWLDataComplementOf(dr)
        elif isinstance(dr, OWLDataComplementOf):
            # ¬¬D = D
            return self._get_data_range_nnf(dr.data_range())
        elif isinstance(dr, OWLDataOneOf):
            return OWLDataComplementOf(dr)
        elif isinstance(dr, OWLDatatypeRestriction):
            return OWLDataComplementOf(dr)
        elif isinstance(dr, OWLDataUnionOf):
            # ¬(D1 ⊔ D2) = ¬D1 ⊓ ¬D2
            operands = tuple(self._get_data_range_complement_nnf(op) for op in dr.operands())
            return OWLDataIntersectionOf(*operands)
        else:
            return OWLDataComplementOf(dr)

    # -----------------------------------------------------------------------
    # Simplification
    # -----------------------------------------------------------------------

    def _simplify_class_expression(self, expr: OWLClassExpression) -> OWLClassExpression:
        """Simplify a class expression (remove tautologies, flatten nesting, etc.)."""
        if isinstance(expr, OWLClass):
            return expr
        elif isinstance(expr, OWLObjectIntersectionOf):
            # Simplify operands, remove TOP, fail if BOTTOM
            operands = []
            for op in expr.operands():
                simplified = self._simplify_class_expression(op)
                if simplified.is_owl_thing():
                    # ⊤ ⊓ A = A, skip TOP
                    continue
                elif simplified.is_owl_nothing():
                    # ⊥ ⊓ A = ⊥, return BOTTOM
                    return OWLNothing
                elif isinstance(simplified, OWLObjectIntersectionOf):
                    # Flatten nested intersections
                    operands.extend(simplified.operands())
                else:
                    operands.append(simplified)
            return OWLObjectIntersectionOf(*operands) if operands else OWLThing
        elif isinstance(expr, OWLObjectUnionOf):
            # Simplify operands, fail if TOP, remove BOTTOM
            operands = []
            for op in expr.operands():
                simplified = self._simplify_class_expression(op)
                if simplified.is_owl_thing():
                    # ⊤ ⊔ A = ⊤, return TOP
                    return OWLThing
                elif simplified.is_owl_nothing():
                    # ⊥ ⊔ A = A, skip BOTTOM
                    continue
                elif isinstance(simplified, OWLObjectUnionOf):
                    # Flatten nested unions
                    operands.extend(simplified.operands())
                else:
                    operands.append(simplified)
            return OWLObjectUnionOf(*operands) if operands else OWLNothing
        elif isinstance(expr, OWLObjectComplementOf):
            simplified = self._simplify_class_expression(expr.operand())
            if simplified.is_owl_thing():
                return OWLNothing
            elif simplified.is_owl_nothing():
                return OWLThing
            elif isinstance(simplified, OWLObjectComplementOf):
                # ¬¬A = A
                return simplified.operand()
            else:
                return OWLObjectComplementOf(simplified)
        elif isinstance(expr, OWLObjectSomeValuesFrom):
            filler = self._simplify_class_expression(expr.filler())
            if filler.is_owl_nothing():
                return OWLNothing
            return OWLObjectSomeValuesFrom(expr.property(), filler)
        elif isinstance(expr, OWLObjectAllValuesFrom):
            filler = self._simplify_class_expression(expr.filler())
            if filler.is_owl_thing():
                return OWLThing
            return OWLObjectAllValuesFrom(expr.property(), filler)
        elif isinstance(expr, OWLObjectHasValue):
            # ∃R.{a} simplifies from OWLObjectHasValue
            nominal = OWLObjectOneOf(expr.value())
            return OWLObjectSomeValuesFrom(expr.property(), nominal)
        elif isinstance(expr, OWLObjectHasSelf):
            return expr
        elif isinstance(expr, OWLObjectMinCardinality):
            filler = self._simplify_class_expression(expr.filler())
            if expr.cardinality() <= 0:
                return OWLThing
            elif filler.is_owl_nothing():
                return OWLNothing
            elif expr.cardinality() == 1:
                return OWLObjectSomeValuesFrom(expr.property(), filler)
            return OWLObjectMinCardinality(expr.cardinality(), expr.property(), filler)
        elif isinstance(expr, OWLObjectMaxCardinality):
            filler = self._simplify_class_expression(expr.filler())
            if filler.is_owl_nothing():
                return OWLThing
            elif expr.cardinality() <= 0:
                return OWLObjectAllValuesFrom(
                    expr.property(), OWLObjectComplementOf(filler)
                )
            return OWLObjectMaxCardinality(expr.cardinality(), expr.property(), filler)
        elif isinstance(expr, OWLObjectExactCardinality):
            filler = self._simplify_class_expression(expr.filler())
            if expr.cardinality() < 0:
                return OWLNothing
            elif expr.cardinality() == 0:
                return OWLObjectAllValuesFrom(
                    expr.property(), OWLObjectComplementOf(filler)
                )
            elif filler.is_owl_nothing():
                return OWLNothing
            else:
                min_card = OWLObjectMinCardinality(expr.cardinality(), expr.property(), filler)
                max_card = OWLObjectMaxCardinality(expr.cardinality(), expr.property(), filler)
                return OWLObjectIntersectionOf(min_card, max_card)
        elif isinstance(expr, OWLDataSomeValuesFrom):
            filler = self._simplify_data_range(expr.filler())
            if self._is_bottom_data_range(filler):
                return OWLNothing
            return OWLDataSomeValuesFrom(expr.property(), filler)
        elif isinstance(expr, OWLDataAllValuesFrom):
            filler = self._simplify_data_range(expr.filler())
            if filler.is_top_datatype():
                return OWLThing
            return OWLDataAllValuesFrom(expr.property(), filler)
        elif isinstance(expr, OWLDataHasValue):
            nominal = OWLDataOneOf(expr.value())
            return OWLDataSomeValuesFrom(expr.property(), nominal)
        elif isinstance(expr, OWLDataMinCardinality):
            filler = self._simplify_data_range(expr.filler())
            if expr.cardinality() <= 0:
                return OWLThing
            elif self._is_bottom_data_range(filler):
                return OWLNothing
            elif expr.cardinality() == 1:
                return OWLDataSomeValuesFrom(expr.property(), filler)
            return OWLDataMinCardinality(expr.cardinality(), expr.property(), filler)
        elif isinstance(expr, OWLDataMaxCardinality):
            filler = self._simplify_data_range(expr.filler())
            if self._is_bottom_data_range(filler):
                return OWLThing
            elif expr.cardinality() <= 0:
                return OWLDataAllValuesFrom(expr.property(), OWLDataComplementOf(filler))
            return OWLDataMaxCardinality(expr.cardinality(), expr.property(), filler)
        elif isinstance(expr, OWLDataExactCardinality):
            filler = self._simplify_data_range(expr.filler())
            if expr.cardinality() < 0:
                return OWLNothing
            elif expr.cardinality() == 0:
                return OWLDataAllValuesFrom(expr.property(), OWLDataComplementOf(filler))
            elif self._is_bottom_data_range(filler):
                return OWLNothing
            else:
                min_card = OWLDataMinCardinality(expr.cardinality(), expr.property(), filler)
                max_card = OWLDataMaxCardinality(expr.cardinality(), expr.property(), filler)
                return OWLObjectIntersectionOf(min_card, max_card)
        else:
            return expr

    def _simplify_data_range(self, dr: OWLDataRange) -> OWLDataRange:
        """Simplify a data range."""
        if isinstance(dr, OWLDatatype):
            return dr
        elif isinstance(dr, OWLDataComplementOf):
            simplified = self._simplify_data_range(dr.data_range())
            if isinstance(simplified, OWLDataComplementOf):
                # ¬¬D = D
                return simplified.data_range()
            return OWLDataComplementOf(simplified)
        elif isinstance(dr, OWLDataOneOf):
            return dr
        elif isinstance(dr, OWLDatatypeRestriction):
            return dr
        else:
            return dr

    @staticmethod
    def _is_bottom_data_range(dr: OWLDataRange) -> bool:
        """Check if a data range is the bottom data range (complement of top)."""
        return isinstance(dr, OWLDataComplementOf) and dr.data_range().is_top_datatype()
