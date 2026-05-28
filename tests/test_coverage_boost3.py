"""Coverage boost tests targeting blocking_validator, anywhere_validated_blocking,
and validated_pairwise_direct_blocking_checker through SIMPLE_CORE / COMPLEX_CORE
blocking configurations and complex ontologies.
"""

from __future__ import annotations

import pytest

from hermit import Configuration, Reasoner
from hermit.configuration import (
    BlockingSignatureCacheType,
    BlockingStrategyType,
    DirectBlockingType,
    ExistentialStrategyType,
)
from hermit.model import (
    Atom,
    AtomicConcept,
    AtomicRole,
    DLClause,
    DLOntology,
    Individual,
    InverseRole,
    Variable,
    AtLeastConcept,
    AtMostConcept,
)


NS = "http://example.org/bv#"


def _ns(name: str) -> str:
    return f"{NS}{name}"


def _make_ontology(
    clauses: list[DLClause],
    positive_facts: list[Atom] | None = None,
    negative_facts: list[Atom] | None = None,
    iri: str = "urn:test:boost3",
) -> DLOntology:
    return DLOntology(
        ontology_iri=iri,
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset(positive_facts or []),
        negative_facts=frozenset(negative_facts or []),
    )


def _simple_core_reasoner(
    clauses: list[DLClause],
    positive_facts: list[Atom] | None = None,
    iri: str = "urn:test:simple-core",
) -> Reasoner:
    """Create reasoner with SIMPLE_CORE blocking (triggers AnywhereValidatedBlocking)."""
    ont = _make_ontology(clauses, positive_facts, iri=iri)
    config = Configuration()
    config.blocking_strategy_type = BlockingStrategyType.SIMPLE_CORE
    return Reasoner(ont, config)


def _complex_core_reasoner(
    clauses: list[DLClause],
    positive_facts: list[Atom] | None = None,
    iri: str = "urn:test:complex-core",
) -> Reasoner:
    """Create reasoner with COMPLEX_CORE blocking (triggers AnywhereValidatedBlocking)."""
    ont = _make_ontology(clauses, positive_facts, iri=iri)
    config = Configuration()
    config.blocking_strategy_type = BlockingStrategyType.COMPLEX_CORE
    return Reasoner(ont, config)


def _pairwise_validated_reasoner(
    clauses: list[DLClause],
    positive_facts: list[Atom] | None = None,
    iri: str = "urn:test:pairwise-validated",
) -> Reasoner:
    """Create reasoner with PAIR_WISE + SIMPLE_CORE (ValidatedPairwiseDirectBlockingChecker)."""
    ont = _make_ontology(clauses, positive_facts, iri=iri)
    config = Configuration()
    config.direct_blocking_type = DirectBlockingType.PAIR_WISE
    config.blocking_strategy_type = BlockingStrategyType.SIMPLE_CORE
    return Reasoner(ont, config)


# ---------------------------------------------------------------------------
# AnywhereValidatedBlocking (SIMPLE_CORE) tests
# ---------------------------------------------------------------------------

class TestAnywhereValidatedBlockingSimpleCore:
    """Tests with SIMPLE_CORE blocking to exercise blocking_validator and
    anywhere_validated_blocking code paths."""

    def test_basic_consistency_simple_core(self):
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("SCa"))
        B = AtomicConcept.create(_ns("SCb"))
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        inds = [Individual.create(_ns(f"sc_basic_{i}")) for i in range(5)]
        facts = [Atom.create(A, ind) for ind in inds]

        r = _simple_core_reasoner(clauses, facts, "urn:test:sc-basic")
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_existential_with_simple_core(self):
        """Existential expansion with SIMPLE_CORE triggers blocking validator."""
        X = Variable.create("X")
        r_role = AtomicRole.create(_ns("sc_r"))
        A = AtomicConcept.create(_ns("SC_ExA"))
        B = AtomicConcept.create(_ns("SC_ExB"))

        at_least_1 = AtLeastConcept.create(1, r_role, B)
        # A ⊑ ∃r.B and B ⊑ ∃r.B (creates chain → triggers blocking)
        clauses = [
            DLClause.create(
                (Atom.create(at_least_1, X),),
                (Atom.create(A, X),),
            ),
            DLClause.create(
                (Atom.create(at_least_1, X),),
                (Atom.create(B, X),),
            ),
        ]
        i1 = Individual.create(_ns("sc_ex_i1"))
        facts = [Atom.create(A, i1)]

        reasoner = _simple_core_reasoner(clauses, facts, "urn:test:sc-existential")
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_complex_hierarchy_simple_core(self):
        """Complex hierarchy with SIMPLE_CORE exercises more blocking validator paths."""
        X = Variable.create("X")
        levels = 5
        concepts = [AtomicConcept.create(_ns(f"SCLevel{i}")) for i in range(levels)]
        clauses = [
            DLClause.create(
                (Atom.create(concepts[i + 1], X),),
                (Atom.create(concepts[i], X),),
            )
            for i in range(levels - 1)
        ]
        inds = [Individual.create(_ns(f"sc_hier_{i}")) for i in range(10)]
        facts = [Atom.create(concepts[0], ind) for ind in inds]

        reasoner = _simple_core_reasoner(clauses, facts, "urn:test:sc-hierarchy")
        try:
            assert reasoner.is_consistent()
            assert reasoner.is_sub_class_of(concepts[0], concepts[-1])
        finally:
            reasoner.dispose()

    def test_get_instances_simple_core(self):
        """Instance retrieval with SIMPLE_CORE blocking."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("SCIA"))
        B = AtomicConcept.create(_ns("SCIB"))
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        inds = [Individual.create(_ns(f"sci_{i}")) for i in range(8)]
        facts = [Atom.create(A, ind) for ind in inds]

        reasoner = _simple_core_reasoner(clauses, facts, "urn:test:sc-instances")
        try:
            assert reasoner.is_consistent()
            insts = reasoner.get_instances(B)
            assert len(insts) >= 8
        finally:
            reasoner.dispose()

    def test_subsumption_with_simple_core(self):
        """Subsumption check with SIMPLE_CORE."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("SCS_A"))
        B = AtomicConcept.create(_ns("SCS_B"))
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        ont = _make_ontology(clauses, iri="urn:test:sc-subsumption")
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.SIMPLE_CORE
        reasoner = Reasoner(ont, config)
        try:
            assert reasoner.is_sub_class_of(A, B)
        finally:
            reasoner.dispose()

    def test_role_chain_simple_core(self):
        """Role chain with SIMPLE_CORE blocking to trigger blocking validator paths."""
        X = Variable.create("X")
        Y = Variable.create("Y")
        r = AtomicRole.create(_ns("sc_chain_r"))
        s = AtomicRole.create(_ns("sc_chain_s"))
        A = AtomicConcept.create(_ns("SC_ChA"))
        B = AtomicConcept.create(_ns("SC_ChB"))
        clauses = [
            DLClause.create((Atom.create(s, X, Y),), (Atom.create(r, X, Y),)),
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        inds = [Individual.create(_ns(f"sc_chain_{i}")) for i in range(4)]
        facts = [Atom.create(A, inds[i]) for i in range(3)]
        facts.append(Atom.create(r, inds[0], inds[1]))
        facts.append(Atom.create(r, inds[1], inds[2]))

        reasoner = _simple_core_reasoner(clauses, facts, "urn:test:sc-chain")
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_deep_existential_chain_simple_core(self):
        """Deep existential chain triggers blocking in SIMPLE_CORE mode."""
        X = Variable.create("X")
        r = AtomicRole.create(_ns("sc_deep_r"))
        A = AtomicConcept.create(_ns("SC_DeepA"))
        # A ⊑ ∃r.A creates an infinite chain that blocking must handle
        at_least_1 = AtLeastConcept.create(1, r, A)
        clauses = [
            DLClause.create(
                (Atom.create(at_least_1, X),),
                (Atom.create(A, X),),
            ),
        ]
        i1 = Individual.create(_ns("sc_deep_i1"))
        facts = [Atom.create(A, i1)]

        reasoner = _simple_core_reasoner(clauses, facts, "urn:test:sc-deep")
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_classify_with_simple_core(self):
        """classify_classes with SIMPLE_CORE."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("SCC_A"))
        B = AtomicConcept.create(_ns("SCC_B"))
        C = AtomicConcept.create(_ns("SCC_C"))
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(C, X),), (Atom.create(B, X),)),
        ]
        inds = [Individual.create(_ns(f"scc_{i}")) for i in range(5)]
        facts = [Atom.create(A, ind) for ind in inds]

        reasoner = _simple_core_reasoner(clauses, facts, "urn:test:scc-classify")
        try:
            reasoner.classify_classes()
            assert reasoner._atomic_concept_hierarchy is not None
            assert reasoner.is_sub_class_of(A, C)
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# AnywhereValidatedBlocking (COMPLEX_CORE) tests
# ---------------------------------------------------------------------------

class TestAnywhereValidatedBlockingComplexCore:
    """Tests with COMPLEX_CORE blocking."""

    def test_basic_consistency_complex_core(self):
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("CC_A"))
        B = AtomicConcept.create(_ns("CC_B"))
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        inds = [Individual.create(_ns(f"cc_basic_{i}")) for i in range(5)]
        facts = [Atom.create(A, ind) for ind in inds]

        reasoner = _complex_core_reasoner(clauses, facts, "urn:test:cc-basic")
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_existential_with_complex_core(self):
        """Existential chain with COMPLEX_CORE."""
        X = Variable.create("X")
        r_role = AtomicRole.create(_ns("cc_r"))
        A = AtomicConcept.create(_ns("CC_ExA"))
        B = AtomicConcept.create(_ns("CC_ExB"))

        at_least_1 = AtLeastConcept.create(1, r_role, B)
        clauses = [
            DLClause.create(
                (Atom.create(at_least_1, X),),
                (Atom.create(A, X),),
            ),
            DLClause.create(
                (Atom.create(at_least_1, X),),
                (Atom.create(B, X),),
            ),
        ]
        i1 = Individual.create(_ns("cc_ex_i1"))
        facts = [Atom.create(A, i1)]

        reasoner = _complex_core_reasoner(clauses, facts, "urn:test:cc-existential")
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_deep_chain_complex_core(self):
        """A ⊑ ∃r.A infinite chain in COMPLEX_CORE."""
        X = Variable.create("X")
        r = AtomicRole.create(_ns("cc_deep_r"))
        A = AtomicConcept.create(_ns("CC_DeepA"))
        at_least_1 = AtLeastConcept.create(1, r, A)
        clauses = [
            DLClause.create(
                (Atom.create(at_least_1, X),),
                (Atom.create(A, X),),
            ),
        ]
        i1 = Individual.create(_ns("cc_deep_i1"))
        facts = [Atom.create(A, i1)]

        reasoner = _complex_core_reasoner(clauses, facts, "urn:test:cc-deep")
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_get_instances_complex_core(self):
        """Instance retrieval with COMPLEX_CORE blocking."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("CCIA"))
        B = AtomicConcept.create(_ns("CCIB"))
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        inds = [Individual.create(_ns(f"cci_{i}")) for i in range(6)]
        facts = [Atom.create(A, ind) for ind in inds]

        reasoner = _complex_core_reasoner(clauses, facts, "urn:test:cc-instances")
        try:
            insts = reasoner.get_instances(B)
            assert len(insts) >= 6
        finally:
            reasoner.dispose()

    def test_classify_complex_core(self):
        """classify_classes with COMPLEX_CORE."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("CCC_A"))
        B = AtomicConcept.create(_ns("CCC_B"))
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        inds = [Individual.create(_ns(f"ccc_{i}")) for i in range(4)]
        facts = [Atom.create(A, ind) for ind in inds]

        reasoner = _complex_core_reasoner(clauses, facts, "urn:test:cc-classify")
        try:
            reasoner.classify_classes()
            assert reasoner.is_sub_class_of(A, B)
        finally:
            reasoner.dispose()

    def test_multiple_existentials_complex_core(self):
        """Multiple existentials with COMPLEX_CORE triggers more validator paths."""
        X = Variable.create("X")
        r1 = AtomicRole.create(_ns("cc_r1"))
        r2 = AtomicRole.create(_ns("cc_r2"))
        A = AtomicConcept.create(_ns("CC_MA"))
        B = AtomicConcept.create(_ns("CC_MB"))
        C = AtomicConcept.create(_ns("CC_MC"))

        at_least_r1_B = AtLeastConcept.create(1, r1, B)
        at_least_r2_C = AtLeastConcept.create(1, r2, C)
        clauses = [
            DLClause.create((Atom.create(at_least_r1_B, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(at_least_r2_C, X),), (Atom.create(A, X),)),
        ]
        inds = [Individual.create(_ns(f"cc_multi_{i}")) for i in range(3)]
        facts = [Atom.create(A, ind) for ind in inds]

        reasoner = _complex_core_reasoner(clauses, facts, "urn:test:cc-multi")
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# ValidatedPairwiseDirectBlockingChecker tests
# ---------------------------------------------------------------------------

class TestValidatedPairwiseChecker:
    """PAIR_WISE + SIMPLE_CORE exercises ValidatedPairwiseDirectBlockingChecker."""

    def test_basic_pairwise_validated(self):
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("PV_A"))
        B = AtomicConcept.create(_ns("PV_B"))
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        inds = [Individual.create(_ns(f"pv_{i}")) for i in range(5)]
        facts = [Atom.create(A, ind) for ind in inds]

        reasoner = _pairwise_validated_reasoner(clauses, facts, "urn:test:pv-basic")
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_existential_pairwise_validated(self):
        """Existential with pairwise-validated checker."""
        X = Variable.create("X")
        r = AtomicRole.create(_ns("pv_r"))
        A = AtomicConcept.create(_ns("PV_ExA"))
        B = AtomicConcept.create(_ns("PV_ExB"))

        at_least_1 = AtLeastConcept.create(1, r, B)
        clauses = [
            DLClause.create((Atom.create(at_least_1, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(at_least_1, X),), (Atom.create(B, X),)),
        ]
        i1 = Individual.create(_ns("pv_ex_i1"))
        facts = [Atom.create(A, i1)]

        reasoner = _pairwise_validated_reasoner(clauses, facts, "urn:test:pv-existential")
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_deep_chain_pairwise_validated(self):
        """Infinite chain with pairwise validated checker."""
        X = Variable.create("X")
        r = AtomicRole.create(_ns("pv_deep_r"))
        A = AtomicConcept.create(_ns("PV_DeepA"))
        at_least_1 = AtLeastConcept.create(1, r, A)
        clauses = [
            DLClause.create((Atom.create(at_least_1, X),), (Atom.create(A, X),)),
        ]
        i1 = Individual.create(_ns("pv_deep_i1"))
        facts = [Atom.create(A, i1)]

        reasoner = _pairwise_validated_reasoner(clauses, facts, "urn:test:pv-deep")
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_pairwise_validated_complex_core(self):
        """PAIR_WISE + COMPLEX_CORE combination."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("PVCC_A"))
        B = AtomicConcept.create(_ns("PVCC_B"))
        r = AtomicRole.create(_ns("pvcc_r"))
        at_least_1 = AtLeastConcept.create(1, r, A)
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(at_least_1, X),), (Atom.create(B, X),)),
        ]
        i1 = Individual.create(_ns("pvcc_i1"))
        facts = [Atom.create(A, i1)]

        ont = _make_ontology(clauses, facts, iri="urn:test:pvcc")
        config = Configuration()
        config.direct_blocking_type = DirectBlockingType.PAIR_WISE
        config.blocking_strategy_type = BlockingStrategyType.COMPLEX_CORE
        reasoner = Reasoner(ont, config)
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_classify_pairwise_validated(self):
        """classify_classes with pairwise validated checker."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("PVC_A"))
        B = AtomicConcept.create(_ns("PVC_B"))
        C = AtomicConcept.create(_ns("PVC_C"))
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(C, X),), (Atom.create(B, X),)),
        ]
        inds = [Individual.create(_ns(f"pvc_{i}")) for i in range(4)]
        facts = [Atom.create(A, ind) for ind in inds]

        reasoner = _pairwise_validated_reasoner(clauses, facts, "urn:test:pv-classify")
        try:
            reasoner.classify_classes()
            assert reasoner.is_sub_class_of(A, C)
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Blocking validator specific tests via validated blocking
# ---------------------------------------------------------------------------

class TestBlockingValidatorPaths:
    """Tests designed to exercise specific blocking validator code paths."""

    def test_blocking_with_role_assertions(self):
        """Role assertions on blocked nodes require validator checks."""
        X = Variable.create("X")
        Y = Variable.create("Y")
        r = AtomicRole.create(_ns("bv_r"))
        A = AtomicConcept.create(_ns("BV_A"))
        B = AtomicConcept.create(_ns("BV_B"))

        # A ⊑ ∃r.A (cycle triggers blocking)
        at_least_1 = AtLeastConcept.create(1, r, A)
        clauses = [
            DLClause.create((Atom.create(at_least_1, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]

        i1 = Individual.create(_ns("bv_i1"))
        facts = [Atom.create(A, i1)]

        for bst in [BlockingStrategyType.SIMPLE_CORE, BlockingStrategyType.COMPLEX_CORE]:
            ont = _make_ontology(clauses, facts, iri=f"urn:test:bv-{bst.value}")
            config = Configuration()
            config.blocking_strategy_type = bst
            reasoner = Reasoner(ont, config)
            try:
                assert reasoner.is_consistent()
            finally:
                reasoner.dispose()

    def test_blocking_with_multiple_roles(self):
        """Multiple roles on chain nodes exercise blocking validator fully."""
        X = Variable.create("X")
        Y = Variable.create("Y")
        r1 = AtomicRole.create(_ns("bv_mr1"))
        r2 = AtomicRole.create(_ns("bv_mr2"))
        A = AtomicConcept.create(_ns("BV_MRA"))
        B = AtomicConcept.create(_ns("BV_MRB"))

        at_least_r1_A = AtLeastConcept.create(1, r1, A)
        at_least_r2_B = AtLeastConcept.create(1, r2, B)
        clauses = [
            DLClause.create((Atom.create(at_least_r1_A, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(at_least_r2_B, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        i1 = Individual.create(_ns("bv_mr_i1"))
        facts = [Atom.create(A, i1)]

        for bst in [BlockingStrategyType.SIMPLE_CORE, BlockingStrategyType.COMPLEX_CORE]:
            ont = _make_ontology(clauses, facts, iri=f"urn:test:bv-mr-{bst.value}")
            config = Configuration()
            config.blocking_strategy_type = bst
            reasoner = Reasoner(ont, config)
            try:
                assert reasoner.is_consistent()
            finally:
                reasoner.dispose()

    def test_blocking_validator_with_atleast_chain(self):
        """AtLeast chain combined with blocking validation."""
        X = Variable.create("X")
        r = AtomicRole.create(_ns("bv_am_r"))
        A = AtomicConcept.create(_ns("BV_AmA"))
        B = AtomicConcept.create(_ns("BV_AmB"))
        C = AtomicConcept.create(_ns("BV_AmC"))

        at_least_1_B = AtLeastConcept.create(1, r, B)
        at_least_1_C = AtLeastConcept.create(1, r, C)
        clauses = [
            DLClause.create((Atom.create(at_least_1_B, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(at_least_1_C, X),), (Atom.create(A, X),)),
        ]
        i1 = Individual.create(_ns("bv_am_i1"))
        facts = [Atom.create(A, i1)]

        for bst in [BlockingStrategyType.SIMPLE_CORE, BlockingStrategyType.COMPLEX_CORE]:
            ont = _make_ontology(clauses, facts, iri=f"urn:test:bv-am-{bst.value}")
            config = Configuration()
            config.blocking_strategy_type = bst
            reasoner = Reasoner(ont, config)
            try:
                assert reasoner.is_consistent()
            finally:
                reasoner.dispose()

    def test_many_individuals_validated_blocking(self):
        """Many individuals with validated blocking to stress-test the code."""
        X = Variable.create("X")
        r = AtomicRole.create(_ns("bv_many_r"))
        A = AtomicConcept.create(_ns("BV_ManyA"))
        B = AtomicConcept.create(_ns("BV_ManyB"))

        at_least_1 = AtLeastConcept.create(1, r, A)
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(at_least_1, X),), (Atom.create(B, X),)),
        ]
        inds = [Individual.create(_ns(f"bv_many_{i}")) for i in range(15)]
        facts = [Atom.create(A, ind) for ind in inds]

        for bst in [BlockingStrategyType.SIMPLE_CORE, BlockingStrategyType.COMPLEX_CORE]:
            ont = _make_ontology(clauses, facts, iri=f"urn:test:bv-many-{bst.value}")
            config = Configuration()
            config.blocking_strategy_type = bst
            reasoner = Reasoner(ont, config)
            try:
                assert reasoner.is_consistent()
            finally:
                reasoner.dispose()

    def test_get_instances_with_validated_blocking(self):
        """Instance retrieval triggers full blocking validator pipeline."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("BVI_A"))
        B = AtomicConcept.create(_ns("BVI_B"))
        C = AtomicConcept.create(_ns("BVI_C"))
        r = AtomicRole.create(_ns("bvi_r"))

        at_least_1 = AtLeastConcept.create(1, r, C)
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(at_least_1, X),), (Atom.create(B, X),)),
        ]
        inds = [Individual.create(_ns(f"bvi_{i}")) for i in range(10)]
        facts = [Atom.create(A, ind) for ind in inds]

        for bst in [BlockingStrategyType.SIMPLE_CORE, BlockingStrategyType.COMPLEX_CORE]:
            ont = _make_ontology(clauses, facts, iri=f"urn:test:bvi-{bst.value}")
            config = Configuration()
            config.blocking_strategy_type = bst
            reasoner = Reasoner(ont, config)
            try:
                insts = reasoner.get_instances(B)
                assert len(insts) >= 10
            finally:
                reasoner.dispose()

    def test_classify_validated_blocking(self):
        """Full classification pipeline with validated blocking."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("BVClass_A"))
        B = AtomicConcept.create(_ns("BVClass_B"))
        C = AtomicConcept.create(_ns("BVClass_C"))
        D = AtomicConcept.create(_ns("BVClass_D"))
        r = AtomicRole.create(_ns("bvc_r"))

        at_least_1 = AtLeastConcept.create(1, r, D)
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(C, X),), (Atom.create(B, X),)),
            DLClause.create((Atom.create(at_least_1, X),), (Atom.create(C, X),)),
        ]
        inds = [Individual.create(_ns(f"bvc_{i}")) for i in range(5)]
        facts = [Atom.create(A, ind) for ind in inds]

        for bst in [BlockingStrategyType.SIMPLE_CORE, BlockingStrategyType.COMPLEX_CORE]:
            ont = _make_ontology(clauses, facts, iri=f"urn:test:bvc-{bst.value}")
            config = Configuration()
            config.blocking_strategy_type = bst
            reasoner = Reasoner(ont, config)
            try:
                reasoner.classify_classes()
                assert reasoner.is_sub_class_of(A, C)
            finally:
                reasoner.dispose()

    def test_inconsistency_detected_validated_blocking(self):
        """Inconsistency detected with validated blocking."""
        X = Variable.create("X")
        A = AtomicConcept.create(_ns("BVInc_A"))
        neg_A = A.get_negation()

        i1 = Individual.create(_ns("bv_inc_i1"))
        facts = [
            Atom.create(A, i1),
            Atom.create(neg_A, i1),
        ]
        for bst in [BlockingStrategyType.SIMPLE_CORE, BlockingStrategyType.COMPLEX_CORE]:
            ont = _make_ontology([], facts, iri=f"urn:test:bv-inc-{bst.value}")
            config = Configuration()
            config.blocking_strategy_type = bst
            reasoner = Reasoner(ont, config)
            try:
                assert not reasoner.is_consistent()
            finally:
                reasoner.dispose()

    def test_pairwise_validated_with_existentials(self):
        """PAIR_WISE validated checker with multiple existentials."""
        X = Variable.create("X")
        r1 = AtomicRole.create(_ns("pvex_r1"))
        r2 = AtomicRole.create(_ns("pvex_r2"))
        A = AtomicConcept.create(_ns("PVEX_A"))
        B = AtomicConcept.create(_ns("PVEX_B"))
        C = AtomicConcept.create(_ns("PVEX_C"))

        at_least_r1_B = AtLeastConcept.create(1, r1, B)
        at_least_r2_C = AtLeastConcept.create(1, r2, C)
        clauses = [
            DLClause.create((Atom.create(at_least_r1_B, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(at_least_r2_C, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(at_least_r1_B, X),), (Atom.create(B, X),)),
        ]
        i1 = Individual.create(_ns("pvex_i1"))
        facts = [Atom.create(A, i1)]

        for bst in [BlockingStrategyType.SIMPLE_CORE, BlockingStrategyType.COMPLEX_CORE]:
            ont = _make_ontology(clauses, facts, iri=f"urn:test:pvex-{bst.value}")
            config = Configuration()
            config.direct_blocking_type = DirectBlockingType.PAIR_WISE
            config.blocking_strategy_type = bst
            reasoner = Reasoner(ont, config)
            try:
                assert reasoner.is_consistent()
            finally:
                reasoner.dispose()

    def test_single_validated_with_existentials(self):
        """SINGLE validated checker with existentials."""
        X = Variable.create("X")
        r = AtomicRole.create(_ns("sv_r"))
        A = AtomicConcept.create(_ns("SV_A"))
        B = AtomicConcept.create(_ns("SV_B"))

        at_least_1 = AtLeastConcept.create(1, r, B)
        clauses = [
            DLClause.create((Atom.create(at_least_1, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(at_least_1, X),), (Atom.create(B, X),)),
        ]
        inds = [Individual.create(_ns(f"sv_{i}")) for i in range(3)]
        facts = [Atom.create(A, ind) for ind in inds]

        for bst in [BlockingStrategyType.SIMPLE_CORE, BlockingStrategyType.COMPLEX_CORE]:
            ont = _make_ontology(clauses, facts, iri=f"urn:test:sv-{bst.value}")
            config = Configuration()
            config.direct_blocking_type = DirectBlockingType.SINGLE
            config.blocking_strategy_type = bst
            reasoner = Reasoner(ont, config)
            try:
                assert reasoner.is_consistent()
            finally:
                reasoner.dispose()
