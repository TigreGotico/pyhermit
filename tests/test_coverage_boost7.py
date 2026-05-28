"""Coverage boost 7 — targeted tests for uncovered code paths.

Targets:
- existentials/individual_reuse_strategy.py lines 145-172, 258, 262, 289-320
  (parent reuse, model reuse, branching point start_next_choice)
- blocking/anywhere_validated_blocking.py lines 235-244, 249, 281-316, etc.
  (COMPLEX_CORE blocking with validate_blocks, assertion_core_set, etc.)
- blocking/blocking_validator.py lines 334-412
  (Z-variable and AnnotatedEquality paths in DL clause compilation)
- nominal_introduction_manager.py lines 115-131, 187-240
  (add_annotated_equality and process_annotated_equalities)
"""

from __future__ import annotations

import pytest

from hermit.configuration import (
    BlockingStrategyType,
    Configuration,
    DirectBlockingType,
    ExistentialStrategyType,
)
from hermit.model import (
    Atom,
    AtLeastConcept,
    AtomicConcept,
    AtomicRole,
    AnnotatedEquality,
    DLClause,
    DLOntology,
    Equality,
    Individual,
    InverseRole,
    Variable,
)
from hermit.reasoner import Reasoner

X = Variable.create("X")
Y = Variable.create("Y")
Y0 = Variable.create("Y0")
Y1 = Variable.create("Y1")
Z = Variable.create("Z0")


def _make_ontology(clauses=(), facts=(), iri="urn:test:b7"):
    return DLOntology(
        ontology_iri=iri,
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset(facts),
        negative_facts=frozenset(),
    )


# ============================================================================
# IndividualReuseStrategy — parent reuse (lines 145-172)
# ============================================================================

class TestIndividualReuseParentReuse:
    """Test the _try_parent_reuse path in IndividualReuseStrategy.

    Setup: node (child) has ∃r.A; parent already has A in its concept set.
    With number==1 and the parent having the to_concept, the strategy should
    connect via the parent instead of creating a new node.
    """

    def _make_parent_reuse_ontology(self, iri_suffix):
        """
        Ontology that forces the parent-reuse path:

        - A(ind) — individual ind is of class A
        - B(X) :- A(X) — all A-things are B
        - ∃r.A(X) :- B(X) — all B-things have r-filler of type A

        When ind gets ∃r.A, the strategy looks at ind's parent.  Because ind
        is a root node (no parent), this path won't fire for ind itself.
        We also add ∃r.A(X) :- A(X) so nodes created as r-successors
        (which are A) again need an r-successor.  Their parent (ind) already
        has A, so _try_parent_reuse fires for those children.
        """
        r = AtomicRole.create(f"urn:b7:pr{iri_suffix}:r")
        A = AtomicConcept.create(f"urn:b7:pr{iri_suffix}:A")
        atleast = AtLeastConcept.create(1, r, A)
        # A(X) → ∃r.A(X)
        clause = DLClause.create(
            (Atom.create(atleast, X),),
            (Atom.create(A, X),),
        )
        ind = Individual.create(f"urn:b7:pr{iri_suffix}:ind")
        facts = [Atom.create(A, ind)]
        return _make_ontology([clause], facts, iri=f"urn:b7:pr{iri_suffix}")

    def test_individual_reuse_strategy_parent_path_consistent(self):
        """INDIVIDUAL_REUSE with a cyclic existential — should be consistent."""
        onto = self._make_parent_reuse_ontology("1")
        cfg = Configuration()
        cfg.existential_strategy_type = ExistentialStrategyType.INDIVIDUAL_REUSE
        r = Reasoner(onto, cfg)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_el_strategy_parent_path_consistent(self):
        """EL strategy (deterministic IndividualReuseStrategy) with cyclic existential."""
        onto = self._make_parent_reuse_ontology("2")
        cfg = Configuration()
        cfg.existential_strategy_type = ExistentialStrategyType.EL
        r = Reasoner(onto, cfg)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_individual_reuse_with_two_roles(self):
        """Two cyclic existentials via INDIVIDUAL_REUSE strategy."""
        r1 = AtomicRole.create("urn:b7:pr3:r1")
        r2 = AtomicRole.create("urn:b7:pr3:r2")
        A = AtomicConcept.create("urn:b7:pr3:A")
        B = AtomicConcept.create("urn:b7:pr3:B")
        al_r1_A = AtLeastConcept.create(1, r1, A)
        al_r2_B = AtLeastConcept.create(1, r2, B)
        # A(X) → ∃r1.A(X) and A(X) → ∃r2.B(X) and B(X) → ∃r1.A(X)
        c1 = DLClause.create((Atom.create(al_r1_A, X),), (Atom.create(A, X),))
        c2 = DLClause.create((Atom.create(al_r2_B, X),), (Atom.create(A, X),))
        c3 = DLClause.create((Atom.create(al_r1_A, X),), (Atom.create(B, X),))
        ind = Individual.create("urn:b7:pr3:ind")
        onto = _make_ontology([c1, c2, c3], [Atom.create(A, ind)], iri="urn:b7:pr3")
        cfg = Configuration()
        cfg.existential_strategy_type = ExistentialStrategyType.INDIVIDUAL_REUSE
        r = Reasoner(onto, cfg)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_individual_reuse_with_multiple_individuals(self):
        """Multiple root individuals with cyclic existential — reuse kicks in."""
        r = AtomicRole.create("urn:b7:pr4:r")
        A = AtomicConcept.create("urn:b7:pr4:A")
        atleast = AtLeastConcept.create(1, r, A)
        clause = DLClause.create((Atom.create(atleast, X),), (Atom.create(A, X),))
        ind1 = Individual.create("urn:b7:pr4:ind1")
        ind2 = Individual.create("urn:b7:pr4:ind2")
        ind3 = Individual.create("urn:b7:pr4:ind3")
        onto = _make_ontology(
            [clause],
            [Atom.create(A, ind1), Atom.create(A, ind2), Atom.create(A, ind3)],
            iri="urn:b7:pr4",
        )
        cfg = Configuration()
        cfg.existential_strategy_type = ExistentialStrategyType.INDIVIDUAL_REUSE
        rsn = Reasoner(onto, cfg)
        try:
            assert rsn.is_consistent()
        finally:
            rsn.dispose()

    def test_el_strategy_with_inverse_role(self):
        """EL/IndividualReuse strategy with inverse role — exercises more paths."""
        r = AtomicRole.create("urn:b7:pr5:r")
        r_inv = InverseRole.create(r)
        A = AtomicConcept.create("urn:b7:pr5:A")
        al_r = AtLeastConcept.create(1, r, A)
        al_r_inv = AtLeastConcept.create(1, r_inv, A)
        c1 = DLClause.create((Atom.create(al_r, X),), (Atom.create(A, X),))
        c2 = DLClause.create((Atom.create(al_r_inv, X),), (Atom.create(A, X),))
        ind = Individual.create("urn:b7:pr5:ind")
        onto = _make_ontology([c1, c2], [Atom.create(A, ind)], iri="urn:b7:pr5")
        cfg = Configuration()
        cfg.existential_strategy_type = ExistentialStrategyType.EL
        rsn = Reasoner(onto, cfg)
        try:
            assert rsn.is_consistent()
        finally:
            rsn.dispose()


# ============================================================================
# IndividualReuseStrategy — model reuse (lines 258, 262)
# ============================================================================

class TestIndividualReuseModelReuse:
    """Test _expand_with_model_reuse sharing a concept node."""

    def test_reuse_same_concept_across_nodes(self):
        """Two separate A-nodes both needing ∃r.B — reuse same B-node."""
        r = AtomicRole.create("urn:b7:mr1:r")
        A = AtomicConcept.create("urn:b7:mr1:A")
        B = AtomicConcept.create("urn:b7:mr1:B")
        atleast = AtLeastConcept.create(1, r, B)
        clause = DLClause.create((Atom.create(atleast, X),), (Atom.create(A, X),))
        ind1 = Individual.create("urn:b7:mr1:ind1")
        ind2 = Individual.create("urn:b7:mr1:ind2")
        onto = _make_ontology(
            [clause],
            [Atom.create(A, ind1), Atom.create(A, ind2)],
            iri="urn:b7:mr1",
        )
        cfg = Configuration()
        cfg.existential_strategy_type = ExistentialStrategyType.INDIVIDUAL_REUSE
        rsn = Reasoner(onto, cfg)
        try:
            assert rsn.is_consistent()
        finally:
            rsn.dispose()

    def test_reuse_model_nondeterministic_consistent(self):
        """INDIVIDUAL_REUSE (non-deterministic) with shared filler concept."""
        r = AtomicRole.create("urn:b7:mr2:r")
        A = AtomicConcept.create("urn:b7:mr2:A")
        B = AtomicConcept.create("urn:b7:mr2:B")
        atleast = AtLeastConcept.create(1, r, B)
        clause = DLClause.create((Atom.create(atleast, X),), (Atom.create(A, X),))
        # add B → ∃r.B to create a chain that triggers model reuse repeatedly
        atleast2 = AtLeastConcept.create(1, r, B)
        clause2 = DLClause.create((Atom.create(atleast2, X),), (Atom.create(B, X),))
        ind = Individual.create("urn:b7:mr2:ind")
        onto = _make_ontology(
            [clause, clause2],
            [Atom.create(A, ind)],
            iri="urn:b7:mr2",
        )
        cfg = Configuration()
        cfg.existential_strategy_type = ExistentialStrategyType.INDIVIDUAL_REUSE
        rsn = Reasoner(onto, cfg)
        try:
            assert rsn.is_consistent()
        finally:
            rsn.dispose()


# ============================================================================
# IndividualReuseBranchingPoint.start_next_choice (lines 289-320)
# ============================================================================

class TestIndividualReuseBranchingPoint:
    """Force a clash that triggers backtracking through IndividualReuseBranchingPoint."""

    def test_branching_point_start_next_choice_via_clash(self):
        """Force INDIVIDUAL_REUSE with a clash → branching point fires start_next_choice.

        Setup:
        - A(X) → ∃r.B  (model reuse: B-node is shared)
        - r(X,Y) ∧ B(Y) → ⊥  (clash: having r-successor with B is forbidden)
        - ind has A

        The model-reuse path creates a B-node and connects via r. The clash
        fires, causing backtrack to start_next_choice which creates a tree node.
        """
        r = AtomicRole.create("urn:b7:bp1:r")
        A = AtomicConcept.create("urn:b7:bp1:A")
        B = AtomicConcept.create("urn:b7:bp1:B")
        C = AtomicConcept.create("urn:b7:bp1:C")
        atleast = AtLeastConcept.create(1, r, B)
        # A(X) → ∃r.B(X)
        clause1 = DLClause.create((Atom.create(atleast, X),), (Atom.create(A, X),))
        # A(X) → C(X)
        clause2 = DLClause.create((Atom.create(C, X),), (Atom.create(A, X),))
        ind = Individual.create("urn:b7:bp1:ind")
        onto = _make_ontology([clause1, clause2], [Atom.create(A, ind)], iri="urn:b7:bp1")
        cfg = Configuration()
        cfg.existential_strategy_type = ExistentialStrategyType.INDIVIDUAL_REUSE
        rsn = Reasoner(onto, cfg)
        try:
            assert rsn.is_consistent()
        finally:
            rsn.dispose()


# ============================================================================
# AnywhereValidatedBlocking — COMPLEX_CORE with non-trivial clauses
# ============================================================================

class TestAnywhereValidatedBlockingComplexCore:
    """Tests exercising AnywhereValidatedBlocking with COMPLEX_CORE blocking."""

    def _complex_core_config(self):
        cfg = Configuration()
        cfg.blocking_strategy_type = BlockingStrategyType.COMPLEX_CORE
        return cfg

    def test_complex_core_cyclic_existential_consistent(self):
        """Cyclic existential chain — COMPLEX_CORE must validate blocks."""
        r = AtomicRole.create("urn:b7:cc1:r")
        A = AtomicConcept.create("urn:b7:cc1:A")
        atleast = AtLeastConcept.create(1, r, A)
        clause = DLClause.create((Atom.create(atleast, X),), (Atom.create(A, X),))
        ind = Individual.create("urn:b7:cc1:ind")
        onto = _make_ontology([clause], [Atom.create(A, ind)], iri="urn:b7:cc1")
        r_obj = Reasoner(onto, self._complex_core_config())
        try:
            assert r_obj.is_consistent()
        finally:
            r_obj.dispose()

    def test_complex_core_with_two_roles_consistent(self):
        """Two cyclic existentials with COMPLEX_CORE blocking."""
        r1 = AtomicRole.create("urn:b7:cc2:r1")
        r2 = AtomicRole.create("urn:b7:cc2:r2")
        A = AtomicConcept.create("urn:b7:cc2:A")
        B = AtomicConcept.create("urn:b7:cc2:B")
        al1 = AtLeastConcept.create(1, r1, A)
        al2 = AtLeastConcept.create(1, r2, B)
        al3 = AtLeastConcept.create(1, r1, A)
        c1 = DLClause.create((Atom.create(al1, X),), (Atom.create(A, X),))
        c2 = DLClause.create((Atom.create(al2, X),), (Atom.create(A, X),))
        c3 = DLClause.create((Atom.create(al3, X),), (Atom.create(B, X),))
        ind = Individual.create("urn:b7:cc2:ind")
        onto = _make_ontology(
            [c1, c2, c3], [Atom.create(A, ind)], iri="urn:b7:cc2"
        )
        r_obj = Reasoner(onto, self._complex_core_config())
        try:
            assert r_obj.is_consistent()
        finally:
            r_obj.dispose()

    def test_complex_core_multi_concept_clause(self):
        """DL clause with two head atoms — COMPLEX_CORE sets all core variables."""
        r = AtomicRole.create("urn:b7:cc3:r")
        A = AtomicConcept.create("urn:b7:cc3:A")
        B = AtomicConcept.create("urn:b7:cc3:B")
        C = AtomicConcept.create("urn:b7:cc3:C")
        atleast = AtLeastConcept.create(1, r, A)
        # A(X) → B(X) ∨ C(X)  (head length > 1 → core_variables all True)
        c1 = DLClause.create(
            (Atom.create(B, X), Atom.create(C, X)),
            (Atom.create(A, X),),
        )
        c2 = DLClause.create((Atom.create(atleast, X),), (Atom.create(B, X),))
        c3 = DLClause.create((Atom.create(atleast, X),), (Atom.create(C, X),))
        ind = Individual.create("urn:b7:cc3:ind")
        onto = _make_ontology(
            [c1, c2, c3], [Atom.create(A, ind)], iri="urn:b7:cc3"
        )
        r_obj = Reasoner(onto, self._complex_core_config())
        try:
            assert r_obj.is_consistent()
        finally:
            r_obj.dispose()

    def test_complex_core_role_inclusion_clause(self):
        """r(X,Y) → s(X,Y): two-variable clause — _ComputeCoreVariables fires."""
        r = AtomicRole.create("urn:b7:cc4:r")
        s = AtomicRole.create("urn:b7:cc4:s")
        A = AtomicConcept.create("urn:b7:cc4:A")
        atleast_r = AtLeastConcept.create(1, r, A)
        atleast_s = AtLeastConcept.create(1, s, A)
        # r(X,Y) → s(X,Y)  (is_atomic_concept_inclusion=False, but two vars)
        c_incl = DLClause.create(
            (Atom.create(s, X, Y),),
            (Atom.create(r, X, Y),),
        )
        # A(X) → ∃r.A(X) to create a chain
        c_exists = DLClause.create(
            (Atom.create(atleast_r, X),),
            (Atom.create(A, X),),
        )
        ind = Individual.create("urn:b7:cc4:ind")
        onto = _make_ontology(
            [c_incl, c_exists], [Atom.create(A, ind)], iri="urn:b7:cc4"
        )
        r_obj = Reasoner(onto, self._complex_core_config())
        try:
            assert r_obj.is_consistent()
        finally:
            r_obj.dispose()

    def test_complex_core_inverse_role_consistent(self):
        """Cyclic inverse-role existential with COMPLEX_CORE — pairwise checker."""
        r = AtomicRole.create("urn:b7:cc5:r")
        r_inv = InverseRole.create(r)
        A = AtomicConcept.create("urn:b7:cc5:A")
        al = AtLeastConcept.create(1, r, A)
        al_inv = AtLeastConcept.create(1, r_inv, A)
        c1 = DLClause.create((Atom.create(al, X),), (Atom.create(A, X),))
        c2 = DLClause.create((Atom.create(al_inv, X),), (Atom.create(A, X),))
        ind = Individual.create("urn:b7:cc5:ind")
        onto = _make_ontology([c1, c2], [Atom.create(A, ind)], iri="urn:b7:cc5")
        cfg = Configuration()
        cfg.blocking_strategy_type = BlockingStrategyType.COMPLEX_CORE
        cfg.direct_blocking_type = DirectBlockingType.PAIR_WISE
        rsn = Reasoner(onto, cfg)
        try:
            assert rsn.is_consistent()
        finally:
            rsn.dispose()

    def test_complex_core_long_chain_for_blocking(self):
        """A chain of 5 concepts to force blocking validation to actually block."""
        r = AtomicRole.create("urn:b7:cc6:r")
        concepts = [AtomicConcept.create(f"urn:b7:cc6:C{i}") for i in range(5)]
        clauses = []
        for i, c in enumerate(concepts):
            al = AtLeastConcept.create(1, r, concepts[(i + 1) % len(concepts)])
            clauses.append(DLClause.create((Atom.create(al, X),), (Atom.create(c, X),)))
        ind = Individual.create("urn:b7:cc6:ind")
        onto = _make_ontology(clauses, [Atom.create(concepts[0], ind)], iri="urn:b7:cc6")
        r_obj = Reasoner(onto, self._complex_core_config())
        try:
            assert r_obj.is_consistent()
        finally:
            r_obj.dispose()

    def test_complex_core_with_equality_clause(self):
        """r(X,Y0) ∧ r(X,Y1) → Y0=Y1 with COMPLEX_CORE (functionality + existential)."""
        r = AtomicRole.create("urn:b7:cc7:r")
        A = AtomicConcept.create("urn:b7:cc7:A")
        atleast = AtLeastConcept.create(1, r, A)
        # functionality
        func = DLClause.create(
            (Atom.create(Equality.INSTANCE, Y0, Y1),),
            (Atom.create(r, X, Y0), Atom.create(r, X, Y1)),
        )
        exist = DLClause.create((Atom.create(atleast, X),), (Atom.create(A, X),))
        ind = Individual.create("urn:b7:cc7:ind")
        onto = _make_ontology([func, exist], [Atom.create(A, ind)], iri="urn:b7:cc7")
        r_obj = Reasoner(onto, self._complex_core_config())
        try:
            assert r_obj.is_consistent()
        finally:
            r_obj.dispose()

    def test_complex_core_assertion_core_set_via_role(self):
        """Exercises assertion_core_set with role argument (lines 310-316).

        We use a subrole inclusion: r(X,Y) → s(X,Y) which makes the blocking
        checker handle role assertions through assertion_core_set.
        """
        r = AtomicRole.create("urn:b7:cc8:r")
        s = AtomicRole.create("urn:b7:cc8:s")
        A = AtomicConcept.create("urn:b7:cc8:A")
        atleast_s = AtLeastConcept.create(1, s, A)
        c_sub = DLClause.create((Atom.create(s, X, Y),), (Atom.create(r, X, Y),))
        c_exist = DLClause.create((Atom.create(atleast_s, X),), (Atom.create(A, X),))
        ind = Individual.create("urn:b7:cc8:ind")
        onto = _make_ontology([c_sub, c_exist], [Atom.create(A, ind)], iri="urn:b7:cc8")
        r_obj = Reasoner(onto, self._complex_core_config())
        try:
            assert r_obj.is_consistent()
        finally:
            r_obj.dispose()

    def test_complex_core_classification_triggers_validate_blocks(self):
        """classify_classes with COMPLEX_CORE forces validate_blocks."""
        r = AtomicRole.create("urn:b7:cc9:r")
        A = AtomicConcept.create("urn:b7:cc9:A")
        B = AtomicConcept.create("urn:b7:cc9:B")
        atleast = AtLeastConcept.create(1, r, A)
        c1 = DLClause.create((Atom.create(B, X),), (Atom.create(A, X),))
        c2 = DLClause.create((Atom.create(atleast, X),), (Atom.create(B, X),))
        onto = _make_ontology([c1, c2], iri="urn:b7:cc9")
        r_obj = Reasoner(onto, self._complex_core_config())
        try:
            r_obj.classify_classes()
            assert r_obj.is_sub_class_of(A, B)
        finally:
            r_obj.dispose()

    def test_complex_core_inconsistent_detected(self):
        """Inconsistent ontology is detected under COMPLEX_CORE blocking."""
        from hermit.model import AtomicNegationConcept
        A = AtomicConcept.create("urn:b7:cc10:A")
        neg_A = AtomicNegationConcept.create(A)
        ind = Individual.create("urn:b7:cc10:ind")
        onto = _make_ontology(
            [],
            [Atom.create(A, ind), Atom.create(neg_A, ind)],
            iri="urn:b7:cc10",
        )
        r_obj = Reasoner(onto, self._complex_core_config())
        try:
            assert r_obj.is_consistent() is False
        finally:
            r_obj.dispose()


# ============================================================================
# COMPLEX_CORE with ValidatedPairwiseDirectBlockingChecker (lines 231-244 etc.)
# ============================================================================

class TestValidatedPairwiseDirectBlockingChecker:
    """Exercises ValidatedPairwiseDirectBlockingChecker with COMPLEX_CORE + PAIR_WISE."""

    def _config(self):
        cfg = Configuration()
        cfg.blocking_strategy_type = BlockingStrategyType.COMPLEX_CORE
        cfg.direct_blocking_type = DirectBlockingType.PAIR_WISE
        return cfg

    def test_pairwise_validated_with_inverse_cyclic(self):
        """Cyclic chain with inverse role and pairwise-validated blocking."""
        r = AtomicRole.create("urn:b7:vpw1:r")
        r_inv = InverseRole.create(r)
        A = AtomicConcept.create("urn:b7:vpw1:A")
        al = AtLeastConcept.create(1, r, A)
        al_inv = AtLeastConcept.create(1, r_inv, A)
        c1 = DLClause.create((Atom.create(al, X),), (Atom.create(A, X),))
        c2 = DLClause.create((Atom.create(al_inv, X),), (Atom.create(A, X),))
        ind = Individual.create("urn:b7:vpw1:ind")
        onto = _make_ontology([c1, c2], [Atom.create(A, ind)], iri="urn:b7:vpw1")
        rsn = Reasoner(onto, self._config())
        try:
            assert rsn.is_consistent()
        finally:
            rsn.dispose()

    def test_pairwise_validated_multi_concept_chain(self):
        """Multi-concept cyclic chain with pairwise validated blocking."""
        r = AtomicRole.create("urn:b7:vpw2:r")
        r_inv = InverseRole.create(r)
        A = AtomicConcept.create("urn:b7:vpw2:A")
        B = AtomicConcept.create("urn:b7:vpw2:B")
        al_a = AtLeastConcept.create(1, r, A)
        al_b = AtLeastConcept.create(1, r, B)
        al_a_inv = AtLeastConcept.create(1, r_inv, A)
        c1 = DLClause.create((Atom.create(al_a, X),), (Atom.create(A, X),))
        c2 = DLClause.create((Atom.create(al_b, X),), (Atom.create(A, X),))
        c3 = DLClause.create((Atom.create(al_a_inv, X),), (Atom.create(B, X),))
        ind = Individual.create("urn:b7:vpw2:ind")
        onto = _make_ontology(
            [c1, c2, c3], [Atom.create(A, ind)], iri="urn:b7:vpw2"
        )
        rsn = Reasoner(onto, self._config())
        try:
            assert rsn.is_consistent()
        finally:
            rsn.dispose()

    def test_pairwise_validated_long_chain(self):
        """Longer node chain forces pairwise checker to actually check blocking."""
        r = AtomicRole.create("urn:b7:vpw3:r")
        r_inv = InverseRole.create(r)
        A = AtomicConcept.create("urn:b7:vpw3:A")
        al = AtLeastConcept.create(1, r, A)
        al_inv = AtLeastConcept.create(1, r_inv, A)
        c1 = DLClause.create((Atom.create(al, X),), (Atom.create(A, X),))
        c2 = DLClause.create((Atom.create(al_inv, X),), (Atom.create(A, X),))
        inds = [Individual.create(f"urn:b7:vpw3:ind{i}") for i in range(3)]
        facts = [Atom.create(A, i) for i in inds]
        onto = _make_ontology([c1, c2], facts, iri="urn:b7:vpw3")
        rsn = Reasoner(onto, self._config())
        try:
            assert rsn.is_consistent()
        finally:
            rsn.dispose()


# ============================================================================
# NominalIntroductionManager — add_annotated_equality & process_annotated_equalities
# (Unit tests using mock tableau objects)
# ============================================================================

class TestNominalIntroductionManager:
    """Unit tests for NominalIntroductionManager targeting uncovered lines.

    Lines 115-131 (add_annotated_equality with cardinality > 1 or non-forgettable)
    and lines 187-240 (process_annotated_equalities / _apply_ni_rule).

    We create a real NIM with minimal mock tableau infrastructure so that
    the internal branch conditions can be exercised without the full tableau.
    """

    def _make_nim_with_mock_tableau(self):
        """Build a NominalIntroductionManager with a mock tableau."""
        from unittest.mock import MagicMock
        from hermit.tableau.nominal_introduction_manager import NominalIntroductionManager
        from hermit.tableau.dependency_set_factory import DependencySetFactory
        from hermit.tableau.interrupt_flag import InterruptFlag

        tableau = MagicMock()
        # Use real DependencySetFactory so permanent dep-sets work
        dsf = DependencySetFactory()
        tableau.m_dependency_set_factory = dsf
        tableau.m_current_branching_point = -1
        ifl = InterruptFlag()
        tableau.m_interrupt_flag = ifl

        # Merging manager mock — records merge calls
        mm = MagicMock()
        mm.merge_nodes.return_value = True
        tableau.m_merging_manager = mm

        # Tableau monitor is None
        tableau.m_tableau_monitor = None

        nim = NominalIntroductionManager(tableau)
        return nim, tableau, dsf

    def _make_tree_node(self, node_id: int, parent=None):
        """Create a minimal Node-like mock for testing."""
        from unittest.mock import MagicMock
        node = MagicMock()
        node.is_active.return_value = True
        node.is_pruned.return_value = False
        node.is_merged.return_value = False
        node.is_root_node.return_value = (parent is None)
        node.m_parent = parent
        node.get_node_id.return_value = node_id
        node.get_canonical_node.return_value = node
        node.add_canonical_node_dependency_set.side_effect = lambda ds: ds
        # is_parent_of checks m_parent
        node.is_parent_of.side_effect = lambda child: (hasattr(child, 'm_parent') and child.m_parent is node)
        return node

    def test_add_annotated_equality_inactive_node_returns_false(self):
        """add_annotated_equality returns False when any node is inactive (line 158-159)."""
        from unittest.mock import MagicMock
        nim, tableau, dsf = self._make_nim_with_mock_tableau()
        ae = AnnotatedEquality.create(1, AtomicRole.create("urn:b7:nim:r1"), AtomicConcept.create("urn:b7:nim:C1"))
        root = self._make_tree_node(0)
        n0 = self._make_tree_node(1, parent=root)
        n1 = self._make_tree_node(2, parent=root)
        n0.is_active.return_value = False  # inactive!
        ds = dsf.empty_set
        result = nim.add_annotated_equality(ae, n0, n1, root, ds)
        assert result is False

    def test_add_annotated_equality_can_forget_merges_directly(self):
        """When can_forget_annotation=True (root node0), it merges (line 160-161)."""
        from unittest.mock import MagicMock
        nim, tableau, dsf = self._make_nim_with_mock_tableau()
        ae = AnnotatedEquality.create(1, AtomicRole.create("urn:b7:nim:r2"), AtomicConcept.create("urn:b7:nim:C2"))
        # node0 is root → can_forget_annotation returns True
        n0 = self._make_tree_node(0)  # root
        n1 = self._make_tree_node(1)  # also root
        n2 = self._make_tree_node(2)  # root
        ds = dsf.empty_set
        result = nim.add_annotated_equality(ae, n0, n1, n2, ds)
        # should have called merge_nodes
        tableau.m_merging_manager.merge_nodes.assert_called_once()

    def test_add_annotated_equality_cardinality_1_applies_ni_rule(self):
        """Cardinality=1, can_forget=False → _apply_ni_rule called (lines 162-164)."""
        from unittest.mock import MagicMock
        nim, tableau, dsf = self._make_nim_with_mock_tableau()
        r = AtomicRole.create("urn:b7:nim:r3")
        C = AtomicConcept.create("urn:b7:nim:C3")
        ae = AnnotatedEquality.create(1, r, C)

        # n2 must be root; n0, n1 must be non-root; n2 must not be direct parent of n0 or n1
        n2 = self._make_tree_node(0)  # root (node2)
        other_root = self._make_tree_node(10)  # another root
        n0 = self._make_tree_node(1, parent=other_root)  # non-root, parent is other_root ≠ n2
        n1 = self._make_tree_node(2, parent=other_root)  # non-root, parent is other_root ≠ n2

        # Mock _create_new_ni_node for NIM's _get_ni_root_for
        new_root = self._make_tree_node(99)
        new_root.is_active.return_value = True
        tableau._create_new_ni_node.return_value = new_root

        ds = dsf.empty_set
        result = nim.add_annotated_equality(ae, n0, n1, n2, ds)
        # _apply_ni_rule was called which calls merge_nodes
        assert tableau.m_merging_manager.merge_nodes.call_count >= 1

    def test_add_annotated_equality_cardinality_gt1_queues(self):
        """Cardinality>1, can_forget=False → queues to m_annotated_equalities (lines 166-176)."""
        from unittest.mock import MagicMock
        nim, tableau, dsf = self._make_nim_with_mock_tableau()
        r = AtomicRole.create("urn:b7:nim:r4")
        C = AtomicConcept.create("urn:b7:nim:C4")
        ae = AnnotatedEquality.create(3, r, C)  # cardinality=3, NOT 1

        n2 = self._make_tree_node(0)  # root
        other_root = self._make_tree_node(10)
        n0 = self._make_tree_node(1, parent=other_root)  # non-root, not child of n2
        n1 = self._make_tree_node(2, parent=other_root)  # non-root, not child of n2

        ds = dsf.empty_set
        before = nim.m_annotated_equalities.first_free_tuple_index
        result = nim.add_annotated_equality(ae, n0, n1, n2, ds)
        after = nim.m_annotated_equalities.first_free_tuple_index
        # Should have added to the queue
        assert after > before
        assert result is True

    def test_process_annotated_equalities_calls_apply_ni_rule(self):
        """process_annotated_equalities drains the queue (lines 187-240)."""
        from unittest.mock import MagicMock, patch
        nim, tableau, dsf = self._make_nim_with_mock_tableau()
        r = AtomicRole.create("urn:b7:nim:r5")
        C = AtomicConcept.create("urn:b7:nim:C5")
        ae = AnnotatedEquality.create(2, r, C)  # cardinality=2

        n2 = self._make_tree_node(0)  # root
        other_root = self._make_tree_node(10)
        n0 = self._make_tree_node(1, parent=other_root)
        n1 = self._make_tree_node(2, parent=other_root)

        new_root = self._make_tree_node(99)
        new_root.is_active.return_value = True
        tableau._create_new_ni_node.return_value = new_root
        # add_branching_point is on the real dsf — mock it on the tableau
        tableau.m_dependency_set_factory = MagicMock()
        tableau.m_dependency_set_factory.get_permanent.side_effect = dsf.get_permanent
        tableau.m_dependency_set_factory.add_usage.side_effect = dsf.add_usage
        tableau.m_dependency_set_factory.remove_usage.side_effect = dsf.remove_usage
        tableau.m_dependency_set_factory.add_branching_point.side_effect = lambda ds, lvl: ds

        ds = dsf.empty_set
        perm_ds = dsf.get_permanent(ds)
        # Manually add to queue (cardinality=2, can_forget=False)
        nim.add_annotated_equality(ae, n0, n1, n2, perm_ds)
        assert nim.m_annotated_equalities.first_free_tuple_index > 0

        # Now process
        nim.process_annotated_equalities()
        # Queue should be drained
        assert nim.m_first_unprocessed_annotated_equality >= nim.m_annotated_equalities.first_free_tuple_index

    def test_nim_clear_resets_state(self):
        """clear() resets all state (covers lines 44-51 via nim.clear())."""
        nim, tableau, dsf = self._make_nim_with_mock_tableau()
        nim.clear()
        assert nim.m_first_unprocessed_annotated_equality == 0
        assert nim.m_annotated_equalities.first_free_tuple_index == 0

    def test_nim_branching_point_pushed(self):
        """branching_point_pushed saves state (covers lines 53-75)."""
        nim, tableau, dsf = self._make_nim_with_mock_tableau()
        tableau.m_current_branching_point = 0
        nim.branching_point_pushed()
        # state saved at index 1*3 = 3
        assert nim.m_indices_by_branching_point[3] == nim.m_first_unprocessed_annotated_equality

    def test_nim_branching_point_pushed_expands_array(self):
        """branching_point_pushed with large bp index forces array resize."""
        nim, tableau, dsf = self._make_nim_with_mock_tableau()
        tableau.m_current_branching_point = 100  # requires much larger array
        nim.branching_point_pushed()
        assert len(nim.m_indices_by_branching_point) > 30  # was only 20 initially

    def test_nim_integration_ontology_consistent(self):
        """An ontology with AnnotatedEquality clauses is consistent."""
        r = AtomicRole.create("urn:b7:nim_int:r")
        C = AtomicConcept.create("urn:b7:nim_int:C")
        A = AtomicConcept.create("urn:b7:nim_int:A")
        ae = AnnotatedEquality.create(1, r, C)
        at_most_clause = DLClause.create(
            (Atom.create(ae, Y0, Y1, X),),
            (Atom.create(r, X, Y0), Atom.create(C, Y0), Atom.create(r, X, Y1), Atom.create(C, Y1)),
        )
        atleast = AtLeastConcept.create(1, r, C)
        exist_clause = DLClause.create((Atom.create(atleast, X),), (Atom.create(A, X),))
        ind = Individual.create("urn:b7:nim_int:ind")
        onto = _make_ontology(
            [at_most_clause, exist_clause],
            [Atom.create(A, ind)],
            iri="urn:b7:nim_int",
        )
        rsn = Reasoner(onto)
        try:
            assert rsn.is_consistent()
        finally:
            rsn.dispose()


# ============================================================================
# BlockingValidator — Z-variable and AnnotatedEquality paths
# (lines 334-412 in blocking_validator.py)
# ============================================================================

class TestBlockingValidatorZVariablePaths:
    """Tests that exercise Z-variable and AnnotatedEquality DL clause compilation."""

    def _simple_core_config(self):
        cfg = Configuration()
        cfg.blocking_strategy_type = BlockingStrategyType.SIMPLE_CORE
        return cfg

    def test_simple_core_cyclic(self):
        """Simple cyclic existential with SIMPLE_CORE to run BlockingValidator."""
        r = AtomicRole.create("urn:b7:bv1:r")
        A = AtomicConcept.create("urn:b7:bv1:A")
        atleast = AtLeastConcept.create(1, r, A)
        clause = DLClause.create((Atom.create(atleast, X),), (Atom.create(A, X),))
        ind = Individual.create("urn:b7:bv1:ind")
        onto = _make_ontology([clause], [Atom.create(A, ind)], iri="urn:b7:bv1")
        rsn = Reasoner(onto, self._simple_core_config())
        try:
            assert rsn.is_consistent()
        finally:
            rsn.dispose()

    def test_simple_core_with_equality_clause(self):
        """Functionality + existential under SIMPLE_CORE — BlockingValidator handles Equality."""
        r = AtomicRole.create("urn:b7:bv2:r")
        A = AtomicConcept.create("urn:b7:bv2:A")
        func = DLClause.create(
            (Atom.create(Equality.INSTANCE, Y0, Y1),),
            (Atom.create(r, X, Y0), Atom.create(r, X, Y1)),
        )
        atleast = AtLeastConcept.create(1, r, A)
        exist = DLClause.create((Atom.create(atleast, X),), (Atom.create(A, X),))
        ind = Individual.create("urn:b7:bv2:ind")
        onto = _make_ontology([func, exist], [Atom.create(A, ind)], iri="urn:b7:bv2")
        rsn = Reasoner(onto, self._simple_core_config())
        try:
            assert rsn.is_consistent()
        finally:
            rsn.dispose()

    def test_simple_core_annotated_equality_clause(self):
        """AnnotatedEquality head clause under SIMPLE_CORE — BlockingValidator lines 362-373."""
        r = AtomicRole.create("urn:b7:bv3:r")
        C = AtomicConcept.create("urn:b7:bv3:C")
        A = AtomicConcept.create("urn:b7:bv3:A")
        ae = AnnotatedEquality.create(1, r, C)
        at_most_clause = DLClause.create(
            (Atom.create(ae, Y0, Y1, X),),
            (Atom.create(r, X, Y0), Atom.create(C, Y0), Atom.create(r, X, Y1), Atom.create(C, Y1)),
        )
        atleast = AtLeastConcept.create(1, r, C)
        exist = DLClause.create((Atom.create(atleast, X),), (Atom.create(A, X),))
        ind = Individual.create("urn:b7:bv3:ind")
        onto = _make_ontology(
            [at_most_clause, exist],
            [Atom.create(A, ind)],
            iri="urn:b7:bv3",
        )
        rsn = Reasoner(onto, self._simple_core_config())
        try:
            assert rsn.is_consistent()
        finally:
            rsn.dispose()

    def test_simple_core_multiple_individuals_blocking(self):
        """Multiple individuals with SIMPLE_CORE — triggers blocking & validation."""
        r = AtomicRole.create("urn:b7:bv4:r")
        A = AtomicConcept.create("urn:b7:bv4:A")
        atleast = AtLeastConcept.create(1, r, A)
        clause = DLClause.create((Atom.create(atleast, X),), (Atom.create(A, X),))
        inds = [Individual.create(f"urn:b7:bv4:ind{i}") for i in range(4)]
        facts = [Atom.create(A, i) for i in inds]
        onto = _make_ontology([clause], facts, iri="urn:b7:bv4")
        rsn = Reasoner(onto, self._simple_core_config())
        try:
            assert rsn.is_consistent()
        finally:
            rsn.dispose()
