"""Coverage boost 12 — targeted tests for:

- quasi_order_classification_for_roles.py line 79: _add_known_subsumption in swapped-arg + inverse branch
- quasi_order_classification_for_roles.py lines 158-168: _get_subsumed_by_list_test_description
- Various other low-hanging fruit
"""

from __future__ import annotations

import pytest

from hermit.model import (
    Atom,
    AtomicConcept,
    AtomicRole,
    DLClause,
    DLOntology,
    Individual,
    InverseRole,
    Variable,
)
from hermit.reasoner import Reasoner

X = Variable.create("X")
Y = Variable.create("Y")


def _ns(local: str) -> str:
    return f"urn:test:boost12:{local}"


def _make_ontology(clauses=(), facts=(), iri="urn:test:boost12"):
    return DLOntology(
        ontology_iri=iri,
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset(facts),
        negative_facts=frozenset(),
    )


class TestQOCFRLines79And158:
    """Cover quasi_order_classification_for_roles.py lines 79 and 158-168."""

    def test_swapped_args_with_inverse_role_in_ontology(self):
        """Line 79: swapped-arg DL clause with inverse role also present.

        r(Y,X)->s(X,Y) encodes r^-→s. When has_inverses=True and InverseRole(r)
        is in concepts_for_roles, concept_for_body_inv_role is not None → line 79.
        """
        ns = _ns("swap_inv.")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")
        inv_r = InverseRole(r)

        # Swapped-arg clause: r^- -> s
        r_inv_sub_s = DLClause.create(
            (Atom.create(s, X, Y),),
            (Atom.create(r, Y, X),),
        )
        # Direct clause involving InverseRole to ensure has_inverses=True
        # and InverseRole(r) ends up in m_concepts_for_roles
        inv_r_sub_s = DLClause.create(
            (Atom.create(s, X, Y),),
            (Atom.create(inv_r, X, Y),),
        )

        ont = _make_ontology(clauses=[r_inv_sub_s, inv_r_sub_s])
        reasoner = Reasoner(ont)
        assert reasoner._dl_ontology.has_inverse_roles()
        reasoner.classify_object_properties()
        assert reasoner._object_role_hierarchy is not None
        # r^- should be subsumed by s via the swapped-arg path
        assert reasoner.is_sub_role_of(inv_r, s)

    def test_subsumed_by_list_description_via_possible_subsumptions(self):
        """Lines 158-168: _get_subsumed_by_list_test_description called during
        tableau-based possible-subsumption checking.

        To trigger the list-based check, we need multiple candidate subsumers
        so the algorithm calls is_satisfiable with a list-form description.
        Set up: t -> r, t -> s (t might be subsumed by r and s).
        """
        ns = _ns("sublist.")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")
        t = AtomicRole(ns + "t")

        # t subsumes r and t subsumes s (roles r and s are sub-roles of t)
        r_sub_t = DLClause.create(
            (Atom.create(t, X, Y),),
            (Atom.create(r, X, Y),),
        )
        s_sub_t = DLClause.create(
            (Atom.create(t, X, Y),),
            (Atom.create(s, X, Y),),
        )

        ont = _make_ontology(clauses=[r_sub_t, s_sub_t])
        reasoner = Reasoner(ont)
        reasoner.classify_object_properties()
        assert reasoner._object_role_hierarchy is not None
        # r <= t and s <= t
        assert reasoner.is_sub_role_of(r, t)
        assert reasoner.is_sub_role_of(s, t)

    def test_multiple_superroles_triggers_list_check(self):
        """Three-level hierarchy where the middle role has two possible superroles."""
        ns = _ns("multisuper.")
        r = AtomicRole(ns + "r")
        s1 = AtomicRole(ns + "s1")
        s2 = AtomicRole(ns + "s2")

        r_sub_s1 = DLClause.create(
            (Atom.create(s1, X, Y),),
            (Atom.create(r, X, Y),),
        )
        r_sub_s2 = DLClause.create(
            (Atom.create(s2, X, Y),),
            (Atom.create(r, X, Y),),
        )

        ont = _make_ontology(clauses=[r_sub_s1, r_sub_s2])
        reasoner = Reasoner(ont)
        reasoner.classify_object_properties()
        assert reasoner.is_sub_role_of(r, s1)
        assert reasoner.is_sub_role_of(r, s2)

    def test_four_unrelated_roles_triggers_list_check(self):
        """Lines 158-168: with 4 unrelated roles and only r->t told, r1,r2,r3 are
        all possible subsumers of t (count=3, between 2 and 7), triggering the
        list-based tableau subsumption check.
        """
        ns = _ns("fouroles.")
        r = AtomicRole(ns + "r")
        s1 = AtomicRole(ns + "s1")
        s2 = AtomicRole(ns + "s2")
        s3 = AtomicRole(ns + "s3")

        # Only one told subsumption: r -> s1
        r_sub_s1 = DLClause.create(
            (Atom.create(s1, X, Y),),
            (Atom.create(r, X, Y),),
        )

        ont = _make_ontology(clauses=[r_sub_s1])
        reasoner = Reasoner(ont)
        reasoner.classify_object_properties()
        assert reasoner._object_role_hierarchy is not None
        assert reasoner.is_sub_role_of(r, s1)
        assert not reasoner.is_sub_role_of(r, s2)
        assert not reasoner.is_sub_role_of(r, s3)

    def test_inverse_in_both_swapped_and_direct(self):
        """Both swapped-arg and direct inverse clauses for same role pair."""
        ns = _ns("both_inv.")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")
        inv_r = InverseRole(r)
        inv_s = InverseRole(s)

        # r -> s (direct)
        r_sub_s = DLClause.create(
            (Atom.create(s, X, Y),),
            (Atom.create(r, X, Y),),
        )
        # r^- -> s^- via swapped-args of r -> s
        r_sub_s_swap = DLClause.create(
            (Atom.create(s, Y, X),),
            (Atom.create(r, Y, X),),
        )
        # Ensures InverseRole in ontology
        inv_r_sub_inv_s = DLClause.create(
            (Atom.create(inv_s, X, Y),),
            (Atom.create(inv_r, X, Y),),
        )

        ont = _make_ontology(clauses=[r_sub_s, inv_r_sub_inv_s])
        reasoner = Reasoner(ont)
        assert reasoner._dl_ontology.has_inverse_roles()
        reasoner.classify_object_properties()
        assert reasoner.is_sub_role_of(r, s)
        assert reasoner.is_sub_role_of(inv_r, inv_s)
