"""Quasi-order classification for roles (including inverse roles).

Faithful port of
``org.semanticweb.HermiT.hierarchy.QuasiOrderClassificationForRoles``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hermit.hierarchy.quasi_order_classification import QuasiOrderClassification

if TYPE_CHECKING:
    from hermit.hierarchy.classification_progress_monitor import (
        ClassificationProgressMonitor,
    )
    from hermit.model import AtomicConcept, DLClause, Role
    from hermit.tableau.reasoning_task_description import ReasoningTaskDescription
    from hermit.tableau.tableau import Tableau


class QuasiOrderClassificationForRoles(QuasiOrderClassification):
    """Classifies roles using the quasi-order algorithm with inverse-role support.

    This subclass handles the mapping between roles and their proxy atomic
    concepts, and ensures that inverse-role subsumptions are propagated
    correctly.
    """

    def __init__(
        self,
        tableau: Tableau,
        progress_monitor: ClassificationProgressMonitor,
        top_element: AtomicConcept,
        bottom_element: AtomicConcept,
        elements: set[AtomicConcept],
        has_inverses: bool,
        concepts_for_roles: dict[Role, AtomicConcept],
        roles_for_concepts: dict[AtomicConcept, Role],
    ) -> None:
        super().__init__(
            tableau, progress_monitor, top_element, bottom_element, elements
        )
        self.m_has_inverses = has_inverses
        self.m_concepts_for_roles = concepts_for_roles
        self.m_roles_for_concepts = roles_for_concepts

    def _initialise_known_subsumptions_using_told_subsumers_from_clauses(
        self, dl_clauses: set[DLClause]
    ) -> None:
        from hermit.model import AtomicRole

        for dl_clause in dl_clauses:
            if dl_clause.head_length() == 1 and dl_clause.body_length() == 1:
                head_predicate = dl_clause.head_atom(0).predicate
                body_predicate = dl_clause.body_atom(0).predicate
                if (
                    isinstance(head_predicate, AtomicRole)
                    and head_predicate in self.m_concepts_for_roles
                    and isinstance(body_predicate, AtomicRole)
                    and body_predicate in self.m_concepts_for_roles
                ):
                    head_role = head_predicate
                    body_role = body_predicate
                    concept_for_head_role = self.m_concepts_for_roles[head_role]
                    concept_for_body_role = self.m_concepts_for_roles[body_role]
                    assert concept_for_body_role is not None
                    assert concept_for_head_role is not None
                    if (
                        dl_clause.body_atom(0).argument(0)
                        != dl_clause.head_atom(0).argument(0)
                    ):
                        # r -> s^- and r^- -> s
                        body_inv_role = body_role.get_inverse()
                        concept_for_body_inv_role = self.m_concepts_for_roles.get(
                            body_inv_role
                        )
                        if concept_for_body_inv_role is not None:
                            self._add_known_subsumption(
                                concept_for_body_inv_role, concept_for_head_role
                            )
                    else:
                        # r -> s and r^- -> s^-
                        self._add_known_subsumption(
                            concept_for_body_role, concept_for_head_role
                        )

    def _add_known_subsumption(
        self, sub_concept: AtomicConcept, super_concept: AtomicConcept
    ) -> None:
        super()._add_known_subsumption(sub_concept, super_concept)
        if self.m_has_inverses:
            sub_role = self.m_roles_for_concepts.get(sub_concept)
            super_role = self.m_roles_for_concepts.get(super_concept)
            if sub_role is not None and super_role is not None:
                sub_concept_for_inverse = self.m_concepts_for_roles.get(
                    sub_role.get_inverse()
                )
                super_concept_for_inverse = self.m_concepts_for_roles.get(
                    super_role.get_inverse()
                )
                if (
                    sub_concept_for_inverse is not None
                    and super_concept_for_inverse is not None
                ):
                    super()._add_known_subsumption(
                        sub_concept_for_inverse, super_concept_for_inverse
                    )

    def _add_possible_subsumption(
        self, sub_concept: AtomicConcept, super_concept: AtomicConcept
    ) -> None:
        super()._add_possible_subsumption(sub_concept, super_concept)
        if self.m_has_inverses:
            sub_role = self.m_roles_for_concepts.get(sub_concept)
            super_role = self.m_roles_for_concepts.get(super_concept)
            if sub_role is not None and super_role is not None:
                sub_concept_for_inverse = self.m_concepts_for_roles.get(
                    sub_role.get_inverse()
                )
                super_concept_for_inverse = self.m_concepts_for_roles.get(
                    super_role.get_inverse()
                )
                if (
                    sub_concept_for_inverse is not None
                    and super_concept_for_inverse is not None
                ):
                    super()._add_possible_subsumption(
                        sub_concept_for_inverse, super_concept_for_inverse
                    )

    def _get_sat_test_description(
        self, atomic_concept: AtomicConcept
    ) -> ReasoningTaskDescription:
        from hermit.tableau.reasoning_task_description import (
            ReasoningTaskDescription,
        )

        role = self.m_roles_for_concepts.get(atomic_concept)
        return ReasoningTaskDescription.is_role_satisfiable(role, True)

    def _get_subsumption_test_description(
        self, sub_concept: AtomicConcept, super_concept: AtomicConcept
    ) -> ReasoningTaskDescription:
        from hermit.tableau.reasoning_task_description import (
            ReasoningTaskDescription,
        )

        sub_role = self.m_roles_for_concepts.get(sub_concept)
        super_role = self.m_roles_for_concepts.get(super_concept)
        return ReasoningTaskDescription.is_role_subsumed_by(
            sub_role, super_role, True
        )

    def _get_subsumed_by_list_test_description(
        self, sub_concept: AtomicConcept, superconcepts: list[object]
    ) -> ReasoningTaskDescription:
        from hermit.tableau.reasoning_task_description import (
            ReasoningTaskDescription,
        )

        roles: list[object] = []
        for sc in superconcepts:
            assert isinstance(sc, AtomicConcept)
            role = self.m_roles_for_concepts.get(sc)
            roles.append(role)
        sub_role = self.m_roles_for_concepts.get(sub_concept)
        return ReasoningTaskDescription.is_role_subsumed_by_list(
            sub_role, *roles
        )
