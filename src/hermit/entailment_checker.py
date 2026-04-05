"""Entailment checker for HermiT.

Faithful port of ``org.semanticweb.HermiT.EntailmentChecker`` from the Java
HermiT OWL reasoner.

The Java version uses the OWL API axiom visitor pattern.  Since this Python
port works directly with the internal DL model, the checker operates on
pairs of atomic concepts, roles, and individuals rather than OWL axioms.
"""

from __future__ import annotations

__all__ = ["EntailmentChecker"]

from typing import TYPE_CHECKING

from hermit.model import AtomicConcept, AtomicRole, Individual

if TYPE_CHECKING:
    from hermit.reasoner import Reasoner


class EntailmentChecker:
    """Checks whether concept / role / individual entailments hold.

    This is a simplified version of the Java ``EntailmentChecker`` that
    works with the internal model types (``AtomicConcept``, ``AtomicRole``,
    ``Individual``) instead of OWL API axiom objects.

    Args:
        reasoner: The reasoner instance to use for checking.
    """

    def __init__(self, reasoner: Reasoner) -> None:
        self._reasoner = reasoner

    # ------------------------------------------------------------------
    # Batch entailment check
    # ------------------------------------------------------------------

    def entails(
        self,
        sub_class_pairs: set[tuple[AtomicConcept, AtomicConcept]] | None = None,
        equivalent_class_pairs: set[tuple[AtomicConcept, AtomicConcept]] | None = None,
        disjoint_class_pairs: set[tuple[AtomicConcept, AtomicConcept]] | None = None,
        sub_role_pairs: set[tuple[AtomicRole, AtomicRole]] | None = None,
        equivalent_role_pairs: set[tuple[AtomicRole, AtomicRole]] | None = None,
        disjoint_role_pairs: set[tuple[AtomicRole, AtomicRole]] | None = None,
        type_assertions: set[tuple[Individual, AtomicConcept]] | None = None,
        role_assertions: set[tuple[Individual, AtomicRole, Individual]] | None = None,
        same_individual_pairs: set[tuple[Individual, Individual]] | None = None,
    ) -> bool:
        """Check whether all given entailments hold.

        Each parameter is a collection of entailments to check.  All must
        hold for the method to return ``True``.

        Args:
            sub_class_pairs: Pairs ``(sub, super)`` to check subsumption.
            equivalent_class_pairs: Pairs to check equivalence.
            disjoint_class_pairs: Pairs to check disjointness.
            sub_role_pairs: Pairs ``(sub, super)`` for role subsumption.
            equivalent_role_pairs: Pairs to check role equivalence.
            disjoint_role_pairs: Pairs to check role disjointness.
            type_assertions: Pairs ``(individual, concept)`` to check typing.
            role_assertions: Triples ``(subj, role, obj)`` to check role fillers.
            same_individual_pairs: Pairs to check identity.

        Returns:
            ``True`` if all entailments hold, ``False`` otherwise.
        """
        if not self._reasoner.is_consistent():
            # Inconsistent ontology entails everything
            return True

        if sub_class_pairs:
            for sub, sup in sub_class_pairs:
                if not self._reasoner.is_sub_class_of(sub, sup):
                    return False

        if equivalent_class_pairs:
            for c1, c2 in equivalent_class_pairs:
                if not self._reasoner.is_equivalent(c1, c2):
                    return False

        if disjoint_class_pairs:
            for c1, c2 in disjoint_class_pairs:
                if not self._reasoner.is_disjoint(c1, c2):
                    return False

        if sub_role_pairs:
            for sub, sup in sub_role_pairs:  # type: ignore[assignment]
                if not self._reasoner.is_sub_role_of(sub, sup):  # type: ignore[arg-type]
                    return False

        if equivalent_role_pairs:
            for r1, r2 in equivalent_role_pairs:
                if not self._reasoner.is_equivalent_role(r1, r2):
                    return False

        if disjoint_role_pairs:
            for r1, r2 in disjoint_role_pairs:
                if not self._reasoner.is_disjoint_role(r1, r2):
                    return False

        if type_assertions:
            for ind, concept in type_assertions:
                if not self._reasoner.has_type(ind, concept):
                    return False

        if role_assertions:
            for subj, role, obj in role_assertions:
                if not self._reasoner.has_role_relationship(subj, role, obj):
                    return False

        if same_individual_pairs:
            for i1, i2 in same_individual_pairs:
                if not self._reasoner.is_same_individual(i1, i2):
                    return False

        return True

    # ------------------------------------------------------------------
    # Single entailment checks
    # ------------------------------------------------------------------

    def entails_sub_class_of(self, sub: AtomicConcept, sup: AtomicConcept) -> bool:
        """Check ``sub <= sup``."""
        if not self._reasoner.is_consistent():
            return True
        return self._reasoner.is_sub_class_of(sub, sup)

    def entails_equivalent(self, c1: AtomicConcept, c2: AtomicConcept) -> bool:
        """Check ``c1 == c2``."""
        if not self._reasoner.is_consistent():
            return True
        return self._reasoner.is_equivalent(c1, c2)

    def entails_disjoint(self, c1: AtomicConcept, c2: AtomicConcept) -> bool:
        """Check ``c1 disjoint c2``."""
        if not self._reasoner.is_consistent():
            return True
        return self._reasoner.is_disjoint(c1, c2)

    def entails_type(self, individual: Individual, concept: AtomicConcept) -> bool:
        """Check ``C(a)``."""
        if not self._reasoner.is_consistent():
            return True
        return self._reasoner.has_type(individual, concept)

    def entails_role(
        self, subject: Individual, role: AtomicRole, obj: Individual,
    ) -> bool:
        """Check ``R(a, b)``."""
        if not self._reasoner.is_consistent():
            return True
        return self._reasoner.has_role_relationship(subject, role, obj)

    def entails_same_individual(self, i1: Individual, i2: Individual) -> bool:
        """Check ``a == b``."""
        if not self._reasoner.is_consistent():
            return True
        return self._reasoner.is_same_individual(i1, i2)
