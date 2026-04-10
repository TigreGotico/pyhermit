"""OWL model utility classes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.owl_model.class_expression.class_expression import OWLClassExpression


class NNF:
    """Converts OWL class expressions to Negation Normal Form (NNF)."""

    def get_class_nnf(self, expression: OWLClassExpression) -> OWLClassExpression:
        """Return the NNF of the given class expression."""
        from hermit.owl_model.class_expression.class_expression import (
            OWLObjectComplementOf,
        )
        from hermit.owl_model.class_expression.nary_boolean_expression import (
            OWLObjectIntersectionOf,
            OWLObjectUnionOf,
        )
        from hermit.owl_model.class_expression.restriction import (
            OWLObjectAllValuesFrom,
            OWLObjectSomeValuesFrom,
        )
        from hermit.owl_model.class_expression.owl_class import OWLClass

        if isinstance(expression, OWLClass):
            return expression

        if isinstance(expression, OWLObjectComplementOf):
            operand = expression.get_operand()
            if isinstance(operand, OWLClass):
                return expression  # ¬A stays as is
            if isinstance(operand, OWLObjectComplementOf):
                # ¬¬C → NNF(C)
                return self.get_class_nnf(operand.get_operand())
            if isinstance(operand, OWLObjectIntersectionOf):
                # ¬(C ⊓ D) → NNF(¬C) ⊔ NNF(¬D)
                operands = [
                    self.get_class_nnf(OWLObjectComplementOf(op))
                    for op in operand.operands()
                ]
                return OWLObjectUnionOf(operands)
            if isinstance(operand, OWLObjectUnionOf):
                # ¬(C ⊔ D) → NNF(¬C) ⊓ NNF(¬D)
                operands = [
                    self.get_class_nnf(OWLObjectComplementOf(op))
                    for op in operand.operands()
                ]
                return OWLObjectIntersectionOf(operands)
            if isinstance(operand, OWLObjectSomeValuesFrom):
                # ¬∃r.C → ∀r.NNF(¬C)
                return OWLObjectAllValuesFrom(
                    operand.get_property(),
                    self.get_class_nnf(OWLObjectComplementOf(operand.get_filler())),
                )
            if isinstance(operand, OWLObjectAllValuesFrom):
                # ¬∀r.C → ∃r.NNF(¬C)
                return OWLObjectSomeValuesFrom(
                    operand.get_property(),
                    self.get_class_nnf(OWLObjectComplementOf(operand.get_filler())),
                )
            return expression  # fallback

        if isinstance(expression, OWLObjectIntersectionOf):
            return OWLObjectIntersectionOf(
                [self.get_class_nnf(op) for op in expression.operands()]
            )

        if isinstance(expression, OWLObjectUnionOf):
            return OWLObjectUnionOf(
                [self.get_class_nnf(op) for op in expression.operands()]
            )

        if isinstance(expression, OWLObjectSomeValuesFrom):
            return OWLObjectSomeValuesFrom(
                expression.get_property(),
                self.get_class_nnf(expression.get_filler()),
            )

        if isinstance(expression, OWLObjectAllValuesFrom):
            return OWLObjectAllValuesFrom(
                expression.get_property(),
                self.get_class_nnf(expression.get_filler()),
            )

        return expression
