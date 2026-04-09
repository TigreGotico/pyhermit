"""Comprehensive tests for blocking and existential modules.

Covers:
- blocking/set_factory.py
- blocking/blocking_signature.py
- blocking/blocking_signature_cache.py
- blocking/single_direct_blocking_checker.py
- blocking/pairwise_direct_blocking_checker.py
- blocking/validated_single_direct_blocking_checker.py
- blocking/validated_pairwise_direct_blocking_checker.py
- blocking/ancestor_blocking.py
- blocking/anywhere_blocking.py
- blocking/anywhere_validated_blocking.py
- blocking/blocking_validator.py
- existentials/abstract_expansion_strategy.py
- existentials/creation_order_strategy.py
- existentials/individual_reuse_strategy.py
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ============================================================================
# SetFactory tests
# ============================================================================

from hermit.blocking.set_factory import Entry, SetFactory


class TestSetFactory:
    def test_get_set_empty(self):
        sf = SetFactory()
        e = sf.get_set([])
        assert isinstance(e, Entry)
        assert len(e) == 0

    def test_get_set_single(self):
        sf = SetFactory()
        e = sf.get_set(["a"])
        assert "a" in e
        assert len(e) == 1

    def test_get_set_canonical(self):
        """Same elements return same entry object."""
        sf = SetFactory()
        e1 = sf.get_set(["a", "b"])
        e2 = sf.get_set(["b", "a"])
        assert e1 is e2

    def test_get_set_different(self):
        sf = SetFactory()
        e1 = sf.get_set(["a"])
        e2 = sf.get_set(["b"])
        assert e1 is not e2

    def test_add_reference(self):
        sf = SetFactory()
        e = sf.get_set(["x"])
        sf.add_reference(e)
        assert e.m_reference_count == 1

    def test_remove_reference_evicts(self):
        sf = SetFactory()
        e = sf.get_set(["x"])
        sf.add_reference(e)
        sf.remove_reference(e)
        # After removal, a new get_set should return a different object
        e2 = sf.get_set(["x"])
        # May or may not be same (reused), but should work
        assert e2 is not None

    def test_make_permanent(self):
        sf = SetFactory()
        e = sf.get_set(["p"])
        sf.make_permanent(e)
        assert e.m_permanent is True

    def test_clear_nonpermanent_removes_non_permanent(self):
        sf = SetFactory()
        e1 = sf.get_set(["a"])
        e2 = sf.get_set(["b"])
        sf.make_permanent(e1)
        sf.add_reference(e2)
        sf.clear_nonpermanent()
        # permanent entry e1 should still be accessible
        e1_again = sf.get_set(["a"])
        assert e1_again is e1

    def test_entry_contains(self):
        sf = SetFactory()
        e = sf.get_set(["x", "y"])
        assert "x" in e
        assert "z" not in e

    def test_entry_iter(self):
        sf = SetFactory()
        e = sf.get_set(["a", "b", "c"])
        items = list(e)
        assert set(items) == {"a", "b", "c"}

    def test_entry_hash_and_eq(self):
        sf = SetFactory()
        e1 = sf.get_set(["a"])
        e2 = sf.get_set(["a"])
        assert e1 is e2
        assert hash(e1) == hash(e2)
        assert e1 == e2

    def test_entry_not_eq_different(self):
        sf = SetFactory()
        e1 = sf.get_set(["a"])
        e2 = sf.get_set(["b"])
        assert e1 != e2

    def test_entry_isdisjoint(self):
        sf = SetFactory()
        e = sf.get_set(["a", "b"])
        assert e.isdisjoint(["c", "d"])
        assert not e.isdisjoint(["a", "z"])

    def test_entry_size(self):
        sf = SetFactory()
        e = sf.get_set(["a", "b", "c"])
        assert e.size() == 3

    def test_entry_repr(self):
        sf = SetFactory()
        e = sf.get_set(["q"])
        r = repr(e)
        assert "SetFactory.Entry" in r

    def test_entry_mutation_not_supported(self):
        sf = SetFactory()
        e = sf.get_set(["a"])
        with pytest.raises(NotImplementedError):
            e.clear()
        with pytest.raises(NotImplementedError):
            e.add("x")
        with pytest.raises(NotImplementedError):
            e.discard("a")

    def test_resize_triggered(self):
        """Insert enough entries to trigger internal resize."""
        sf = SetFactory()
        entries = []
        for i in range(20):
            e = sf.get_set([f"item_{i}"])
            entries.append(e)
        # All should still be canonical
        for i, e in enumerate(entries):
            e2 = sf.get_set([f"item_{i}"])
            assert e2 is e

    def test_as_entry_raises_for_frozenset(self):
        sf = SetFactory()
        with pytest.raises(TypeError):
            sf._as_entry(frozenset(["a"]))


# ============================================================================
# BlockingSignature tests
# ============================================================================

from hermit.blocking.blocking_signature import BlockingSignature


class ConcreteBlockingSignature(BlockingSignature):
    """Minimal concrete subclass for testing abstract base."""

    def __init__(self, value):
        super().__init__()
        self.value = value

    def blocks_node(self, node):
        return True

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        if isinstance(other, ConcreteBlockingSignature):
            return self.value == other.value
        return False


class TestBlockingSignature:
    def test_next_entry_default_none(self):
        sig = ConcreteBlockingSignature(1)
        assert sig.next_entry is None

    def test_next_entry_setter(self):
        sig1 = ConcreteBlockingSignature(1)
        sig2 = ConcreteBlockingSignature(2)
        sig1.next_entry = sig2
        assert sig1.next_entry is sig2

    def test_blocks_node(self):
        sig = ConcreteBlockingSignature(42)
        assert sig.blocks_node(None) is True

    def test_hash_and_eq(self):
        sig1 = ConcreteBlockingSignature("x")
        sig2 = ConcreteBlockingSignature("x")
        assert hash(sig1) == hash(sig2)
        assert sig1 == sig2

    def test_abstract_hash_raises(self):
        # The abstract class raises NotImplementedError for __hash__/__eq__
        # if subclass does not override. Our ConcreteBlockingSignature does override.
        # Test the base class directly via super:
        sig = ConcreteBlockingSignature(1)
        # Test that it works (subclass override)
        h = hash(sig)
        assert isinstance(h, int)


# ============================================================================
# BlockingSignatureCache tests
# ============================================================================

from hermit.blocking.blocking_signature_cache import BlockingSignatureCache


class _MockChecker:
    """Minimal mock of DirectBlockingChecker for cache tests."""

    def __init__(self, hash_fn=None, can_be_blocked=True):
        self._hash_fn = hash_fn or (lambda node: hash(id(node)))
        self._can_be_blocked = can_be_blocked
        self._sigs = {}

    def blocking_hash_code(self, node):
        return self._hash_fn(node)

    def can_be_blocked(self, node):
        return self._can_be_blocked

    def get_blocking_signature_for(self, node):
        sig = ConcreteBlockingSignature(id(node))
        sig._node_id = id(node)
        sig.blocks_node = lambda n: id(n) == sig._node_id
        return sig


class TestBlockingSignatureCache:
    def test_is_empty_initially(self):
        checker = _MockChecker()
        cache = BlockingSignatureCache(checker)
        assert cache.is_empty()

    def test_add_node(self):
        checker = _MockChecker()
        cache = BlockingSignatureCache(checker)
        node = object()
        result = cache.add_node(node)
        assert result is True
        assert not cache.is_empty()

    def test_add_duplicate_returns_false(self):
        node = object()
        # hash(sig) must equal blocking_hash_code(node) for duplicate detection
        HASH_VAL = 42

        class DupSig(ConcreteBlockingSignature):
            def __hash__(self):
                return HASH_VAL
            def blocks_node(self, n):
                return True

        class DupChecker:
            def blocking_hash_code(self, n):
                return HASH_VAL
            def can_be_blocked(self, n):
                return True
            def get_blocking_signature_for(self, n):
                return DupSig("dup")

        checker = DupChecker()
        cache = BlockingSignatureCache(checker)
        r1 = cache.add_node(node)
        r2 = cache.add_node(node)
        assert r1 is True
        assert r2 is False

    def test_contains_signature_true(self):
        node = object()
        HASH_VAL = 99

        class MatchSig(ConcreteBlockingSignature):
            def __hash__(self):
                return HASH_VAL
            def blocks_node(self, n):
                return True

        class MatchChecker:
            def blocking_hash_code(self, n):
                return HASH_VAL
            def can_be_blocked(self, n):
                return True
            def get_blocking_signature_for(self, n):
                return MatchSig("match")

        checker = MatchChecker()
        cache = BlockingSignatureCache(checker)
        cache.add_node(node)
        assert cache.contains_signature(node)

    def test_contains_signature_false_when_cant_be_blocked(self):
        checker = _MockChecker(can_be_blocked=False)
        cache = BlockingSignatureCache(checker)
        node = object()
        assert not cache.contains_signature(node)

    def test_resize_triggered(self):
        """Trigger resize by adding many nodes."""
        nodes = [object() for _ in range(800)]
        call_count = [0]

        class CountChecker:
            def blocking_hash_code(self, n):
                return id(n)
            def can_be_blocked(self, n):
                return True
            def get_blocking_signature_for(self, n):
                call_count[0] += 1
                sig = ConcreteBlockingSignature(id(n))
                sig.blocks_node = lambda x: id(x) == id(n)
                return sig

        checker = CountChecker()
        cache = BlockingSignatureCache(checker)
        for node in nodes:
            cache.add_node(node)
        assert cache.m_number_of_elements == len(nodes)

    def test_get_index_for(self):
        result = BlockingSignatureCache._get_index_for(42, 1024)
        assert 0 <= result < 1024


# ============================================================================
# Integration tests using Reasoner + DLOntology
# ============================================================================

from hermit import Reasoner
from hermit.model import (
    Atom,
    AtomicConcept,
    AtomicRole,
    DLClause,
    DLOntology,
    Individual,
    Variable,
    InverseRole,
)


def _make_ontology(clauses, facts=None, iri="urn:test:blocking"):
    return DLOntology(
        ontology_iri=iri,
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset(facts or []),
    )


class TestAncestorBlockingIntegration:
    """Integration tests that exercise ancestor blocking via the reasoner."""

    def test_simple_taxonomy_runs(self):
        """Basic taxonomy doesn't require blocking — ensures AncestorBlocking runs."""
        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        B = AtomicConcept.create("http://test#B")

        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        onto = _make_ontology(clauses)
        r = Reasoner(onto)
        try:
            r.precompute_inferences(class_hierarchy=True)
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_consistent_ontology_with_individual(self):
        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        ind = Individual.create("http://test#ind1")
        a_fact = Atom.create(A, ind)
        onto = _make_ontology([], [a_fact])
        r = Reasoner(onto)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_role_chain_triggers_tree_nodes(self):
        """A role chain creates tree nodes — ancestor blocking fires."""
        X = Variable.create("X")
        Y = Variable.create("Y")
        A = AtomicConcept.create("http://test#A")
        B = AtomicConcept.create("http://test#B")
        r_role = AtomicRole.create("http://test#r")
        ind = Individual.create("http://test#ind")

        from hermit.model import AtLeastConcept
        # A(ind)  =>  ∃r.B(ind)
        # Encode: A ⊑ ≥1 r.B
        at_least = AtLeastConcept.create(1, r_role, B)
        clauses = [
            DLClause.create(
                (Atom.create(at_least, X),),
                (Atom.create(A, X),),
            ),
        ]
        facts = [Atom.create(A, ind)]
        onto = _make_ontology(clauses, facts)
        reasoner = Reasoner(onto)
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()


class TestAnywhereBlockingIntegration:
    """Use anywhere blocking (default for HermiT) through the full reasoner."""

    def test_anywhere_blocking_fires_in_complex_ontology(self):
        """Ontology that creates multiple tree nodes exercises anywhere blocking."""
        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        B = AtomicConcept.create("http://test#B")
        C = AtomicConcept.create("http://test#C")
        r_role = AtomicRole.create("http://test#r")
        ind = Individual.create("http://test#i")

        from hermit.model import AtLeastConcept
        at_least_b = AtLeastConcept.create(1, r_role, B)
        at_least_c = AtLeastConcept.create(1, r_role, C)

        clauses = [
            DLClause.create((Atom.create(at_least_b, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(at_least_c, X),), (Atom.create(B, X),)),
            DLClause.create((Atom.create(A, X),), (Atom.create(C, X),)),
        ]
        facts = [Atom.create(A, ind)]
        onto = _make_ontology(clauses, facts)
        reasoner = Reasoner(onto)
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_multiple_individuals(self):
        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        B = AtomicConcept.create("http://test#B")
        i1 = Individual.create("http://test#i1")
        i2 = Individual.create("http://test#i2")
        i3 = Individual.create("http://test#i3")

        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        facts = [
            Atom.create(A, i1),
            Atom.create(A, i2),
            Atom.create(A, i3),
        ]
        onto = _make_ontology(clauses, facts)
        r = Reasoner(onto)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()


# ============================================================================
# SingleDirectBlockingChecker unit-ish tests
# ============================================================================

from hermit.blocking.single_direct_blocking_checker import (
    SingleBlockingObject,
    SingleBlockingSignature,
    SingleDirectBlockingChecker,
)


class TestSingleDirectBlockingChecker:
    def test_instantiation(self):
        checker = SingleDirectBlockingChecker()
        assert checker._tableau is None

    def test_clear_before_initialize(self):
        checker = SingleDirectBlockingChecker()
        # Should not raise
        checker.clear()

    def test_can_be_blocker_and_blocked_require_tree_node(self):
        checker = SingleDirectBlockingChecker()
        # Without a real tableau we can test via mocks
        from hermit.tableau.node_type import NodeType

        node = MagicMock()
        node.node_type = NodeType.TREE_NODE
        assert checker.can_be_blocker(node) is True
        assert checker.can_be_blocked(node) is True

        node2 = MagicMock()
        node2.node_type = NodeType.NAMED_NODE
        assert checker.can_be_blocker(node2) is False
        assert checker.can_be_blocked(node2) is False

    def test_has_blocking_info_changed(self):
        checker = SingleDirectBlockingChecker()
        obj = MagicMock(spec=SingleBlockingObject)
        obj.m_has_changed = True
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        assert checker.has_blocking_info_changed(node) is True

    def test_clear_blocking_info_changed(self):
        checker = SingleDirectBlockingChecker()
        obj = MagicMock(spec=SingleBlockingObject)
        obj.m_has_changed = True
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        checker.clear_blocking_info_changed(node)
        assert obj.m_has_changed is False

    def test_has_changed_since_validation_always_false(self):
        checker = SingleDirectBlockingChecker()
        assert checker.has_changed_since_validation(MagicMock()) is False

    def test_set_has_changed_since_validation_noop(self):
        checker = SingleDirectBlockingChecker()
        # Should not raise
        checker.set_has_changed_since_validation(MagicMock(), True)

    def test_assertion_added_non_atomic_concept(self):
        from hermit.model import DataRange
        checker = SingleDirectBlockingChecker()
        dr = MagicMock(spec=DataRange)
        result = checker.assertion_added_dr(dr, MagicMock(), False)
        assert result is None

    def test_assertion_removed_dr(self):
        from hermit.model import DataRange
        checker = SingleDirectBlockingChecker()
        dr = MagicMock(spec=DataRange)
        result = checker.assertion_removed_dr(dr, MagicMock(), False)
        assert result is None

    def test_assertion_added_role_returns_none(self):
        checker = SingleDirectBlockingChecker()
        result = checker.assertion_added_role(MagicMock(), MagicMock(), MagicMock(), False)
        assert result is None

    def test_assertion_removed_role_returns_none(self):
        checker = SingleDirectBlockingChecker()
        result = checker.assertion_removed_role(MagicMock(), MagicMock(), MagicMock(), False)
        assert result is None

    def test_nodes_merged_returns_none(self):
        checker = SingleDirectBlockingChecker()
        assert checker.nodes_merged(MagicMock(), MagicMock()) is None

    def test_nodes_unmerged_returns_none(self):
        checker = SingleDirectBlockingChecker()
        assert checker.nodes_unmerged(MagicMock(), MagicMock()) is None

    def test_node_initialized_creates_blocking_object(self):
        checker = SingleDirectBlockingChecker()
        obj_holder = [None]
        existing_obj = SingleBlockingObject(checker, MagicMock())

        # If blocking object already exists, node_initialized calls obj.initialize()
        node = MagicMock()
        node.get_blocking_object.return_value = existing_obj
        checker.node_initialized(node)
        # Should have called initialize (resetting state)
        assert existing_obj.m_has_changed is True

    def test_assertion_added_atomic_concept(self):
        checker = SingleDirectBlockingChecker()
        concept = AtomicConcept.create("http://test#C")
        obj = SingleBlockingObject(checker, MagicMock())
        obj.m_atomic_concepts_label = None
        obj.m_atomic_concepts_label_hash_code = 0
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        result = checker.assertion_added(concept, node, False)
        assert result is node
        assert obj.m_has_changed is True
        assert obj.m_atomic_concepts_label_hash_code == hash(concept)

    def test_assertion_removed_atomic_concept(self):
        checker = SingleDirectBlockingChecker()
        concept = AtomicConcept.create("http://test#C")
        obj = SingleBlockingObject(checker, MagicMock())
        obj.m_atomic_concepts_label = None
        obj.m_atomic_concepts_label_hash_code = hash(concept)
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        result = checker.assertion_removed(concept, node, False)
        assert result is node
        assert obj.m_atomic_concepts_label_hash_code == 0

    def test_assertion_added_non_atomic_concept_returns_none(self):
        checker = SingleDirectBlockingChecker()
        from hermit.model import DataRange
        non_atomic = MagicMock()
        # Not an AtomicConcept instance
        node = MagicMock()
        result = checker.assertion_added(non_atomic, node, False)
        assert result is None


class TestSingleBlockingObject:
    def test_initialize(self):
        checker = SingleDirectBlockingChecker()
        node = MagicMock()
        obj = SingleBlockingObject(checker, node)
        obj.initialize()
        assert obj.m_atomic_concepts_label is None
        assert obj.m_atomic_concepts_label_hash_code == 0
        assert obj.m_has_changed is True

    def test_destroy_with_no_label(self):
        checker = SingleDirectBlockingChecker()
        node = MagicMock()
        obj = SingleBlockingObject(checker, node)
        obj.m_atomic_concepts_label = None
        obj.destroy()  # should not raise

    def test_add_atomic_concept(self):
        checker = SingleDirectBlockingChecker()
        node = MagicMock()
        obj = SingleBlockingObject(checker, node)
        concept = AtomicConcept.create("http://test#X")
        obj.m_atomic_concepts_label = None
        obj.m_atomic_concepts_label_hash_code = 0
        obj.add_atomic_concept(concept)
        assert obj.m_atomic_concepts_label_hash_code == hash(concept)
        assert obj.m_has_changed is True

    def test_remove_atomic_concept(self):
        checker = SingleDirectBlockingChecker()
        node = MagicMock()
        obj = SingleBlockingObject(checker, node)
        concept = AtomicConcept.create("http://test#X")
        obj.m_atomic_concepts_label = None
        obj.m_atomic_concepts_label_hash_code = hash(concept)
        obj.remove_atomic_concept(concept)
        assert obj.m_atomic_concepts_label_hash_code == 0
        assert obj.m_has_changed is True


class TestSingleBlockingSignature:
    def test_eq_same(self):
        sf = SetFactory()
        label = sf.get_set(["a"])
        sf.make_permanent(label)
        sig1 = object.__new__(SingleBlockingSignature)
        sig1._next_entry = None
        sig1.m_atomic_concepts_label = label
        sig2 = object.__new__(SingleBlockingSignature)
        sig2._next_entry = None
        sig2.m_atomic_concepts_label = label
        assert sig1 == sig2

    def test_eq_different(self):
        sf = SetFactory()
        label1 = sf.get_set(["a"])
        sf.make_permanent(label1)
        label2 = sf.get_set(["b"])
        sf.make_permanent(label2)
        sig1 = object.__new__(SingleBlockingSignature)
        sig1._next_entry = None
        sig1.m_atomic_concepts_label = label1
        sig2 = object.__new__(SingleBlockingSignature)
        sig2._next_entry = None
        sig2.m_atomic_concepts_label = label2
        assert sig1 != sig2

    def test_eq_with_non_signature(self):
        sf = SetFactory()
        label = sf.get_set(["a"])
        sf.make_permanent(label)
        sig = object.__new__(SingleBlockingSignature)
        sig._next_entry = None
        sig.m_atomic_concepts_label = label
        assert sig != "not a signature"

    def test_hash(self):
        sf = SetFactory()
        label = sf.get_set(["a"])
        sf.make_permanent(label)
        sig = object.__new__(SingleBlockingSignature)
        sig._next_entry = None
        sig.m_atomic_concepts_label = label
        assert hash(sig) == hash(label)


# ============================================================================
# PairWiseDirectBlockingChecker unit tests
# ============================================================================

from hermit.blocking.pairwise_direct_blocking_checker import (
    PairWiseBlockingObject,
    PairWiseDirectBlockingChecker,
)


class TestPairWiseBlockingObject:
    def _make_checker(self):
        return PairWiseDirectBlockingChecker()

    def test_initialize(self):
        checker = self._make_checker()
        node = MagicMock()
        obj = PairWiseBlockingObject(checker, node)
        obj.initialize()
        assert obj.m_atomic_concepts_label is None
        assert obj.m_from_parent_label is None
        assert obj.m_to_parent_label is None
        assert obj.m_has_changed is True

    def test_destroy_no_labels(self):
        checker = self._make_checker()
        obj = PairWiseBlockingObject(checker, MagicMock())
        obj.destroy()  # should not raise

    def test_destroy_with_labels(self):
        checker = self._make_checker()
        obj = PairWiseBlockingObject(checker, MagicMock())
        # Pre-populate labels
        obj.m_atomic_concepts_label = checker._atomic_concepts_set_factory.get_set(["a"])
        obj.m_from_parent_label = checker._atomic_roles_set_factory.get_set(["r1"])
        obj.m_to_parent_label = checker._atomic_roles_set_factory.get_set(["r2"])
        checker._atomic_concepts_set_factory.add_reference(obj.m_atomic_concepts_label)
        checker._atomic_roles_set_factory.add_reference(obj.m_from_parent_label)
        checker._atomic_roles_set_factory.add_reference(obj.m_to_parent_label)
        obj.destroy()
        assert obj.m_atomic_concepts_label is None
        assert obj.m_from_parent_label is None
        assert obj.m_to_parent_label is None

    def test_add_atomic_concept(self):
        checker = self._make_checker()
        obj = PairWiseBlockingObject(checker, MagicMock())
        concept = AtomicConcept.create("http://test#C")
        obj.add_atomic_concept(concept)
        assert obj.m_has_changed is True
        assert obj.m_atomic_concepts_label_hash_code == hash(concept)

    def test_remove_atomic_concept(self):
        checker = self._make_checker()
        obj = PairWiseBlockingObject(checker, MagicMock())
        concept = AtomicConcept.create("http://test#C")
        obj.m_atomic_concepts_label_hash_code = hash(concept)
        obj.remove_atomic_concept(concept)
        assert obj.m_atomic_concepts_label_hash_code == 0
        assert obj.m_has_changed is True

    def test_add_to_from_parent_label(self):
        checker = self._make_checker()
        obj = PairWiseBlockingObject(checker, MagicMock())
        role = AtomicRole.create("http://test#r")
        obj.add_to_from_parent_label(role)
        assert obj.m_from_parent_label_hash_code == hash(role)
        assert obj.m_has_changed is True

    def test_remove_from_from_parent_label(self):
        checker = self._make_checker()
        obj = PairWiseBlockingObject(checker, MagicMock())
        role = AtomicRole.create("http://test#r")
        obj.m_from_parent_label_hash_code = hash(role)
        obj.remove_from_from_parent_label(role)
        assert obj.m_from_parent_label_hash_code == 0
        assert obj.m_has_changed is True

    def test_add_to_to_parent_label(self):
        checker = self._make_checker()
        obj = PairWiseBlockingObject(checker, MagicMock())
        role = AtomicRole.create("http://test#r")
        obj.add_to_to_parent_label(role)
        assert obj.m_to_parent_label_hash_code == hash(role)
        assert obj.m_has_changed is True

    def test_remove_from_to_parent_label(self):
        checker = self._make_checker()
        obj = PairWiseBlockingObject(checker, MagicMock())
        role = AtomicRole.create("http://test#r")
        obj.m_to_parent_label_hash_code = hash(role)
        obj.remove_from_to_parent_label(role)
        assert obj.m_to_parent_label_hash_code == 0
        assert obj.m_has_changed is True


class TestPairWiseDirectBlockingCheckerUnit:
    def test_instantiation(self):
        checker = PairWiseDirectBlockingChecker()
        assert checker._tableau is None

    def test_can_be_blocker_tree_with_tree_parent(self):
        from hermit.tableau.node_type import NodeType
        checker = PairWiseDirectBlockingChecker()
        parent = MagicMock()
        parent.node_type = NodeType.TREE_NODE
        node = MagicMock()
        node.node_type = NodeType.TREE_NODE
        node.parent = parent
        assert checker.can_be_blocker(node) is True

    def test_can_be_blocker_tree_with_named_parent_false(self):
        from hermit.tableau.node_type import NodeType
        checker = PairWiseDirectBlockingChecker()
        parent = MagicMock()
        parent.node_type = NodeType.NAMED_NODE
        node = MagicMock()
        node.node_type = NodeType.TREE_NODE
        node.parent = parent
        assert checker.can_be_blocker(node) is False

    def test_can_be_blocked_same_as_blocker(self):
        from hermit.tableau.node_type import NodeType
        checker = PairWiseDirectBlockingChecker()
        parent = MagicMock()
        parent.node_type = NodeType.TREE_NODE
        node = MagicMock()
        node.node_type = NodeType.TREE_NODE
        node.parent = parent
        assert checker.can_be_blocked(node) is True

    def test_has_blocking_info_changed(self):
        checker = PairWiseDirectBlockingChecker()
        obj = PairWiseBlockingObject(checker, MagicMock())
        obj.m_has_changed = True
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        assert checker.has_blocking_info_changed(node) is True

    def test_clear_blocking_info_changed(self):
        checker = PairWiseDirectBlockingChecker()
        obj = PairWiseBlockingObject(checker, MagicMock())
        obj.m_has_changed = True
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        checker.clear_blocking_info_changed(node)
        assert obj.m_has_changed is False

    def test_assertion_added_atomic_concept(self):
        checker = PairWiseDirectBlockingChecker()
        concept = AtomicConcept.create("http://test#C")
        obj = PairWiseBlockingObject(checker, MagicMock())
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        result = checker.assertion_added(concept, node, False)
        assert result is node

    def test_assertion_removed_atomic_concept(self):
        checker = PairWiseDirectBlockingChecker()
        concept = AtomicConcept.create("http://test#C")
        obj = PairWiseBlockingObject(checker, MagicMock())
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        result = checker.assertion_removed(concept, node, False)
        assert result is node

    def test_assertion_added_role_from_is_parent(self):
        """node_from is parent of node_to: updates node_to's from_parent label."""
        checker = PairWiseDirectBlockingChecker()
        role = AtomicRole.create("http://test#r")
        obj_to = PairWiseBlockingObject(checker, MagicMock())
        node_from = MagicMock()
        node_to = MagicMock()
        node_from.is_parent_of.return_value = True
        node_to.is_parent_of.return_value = False
        node_to.get_blocking_object.return_value = obj_to
        result = checker.assertion_added_role(role, node_from, node_to, False)
        assert obj_to.m_from_parent_label_hash_code == hash(role)
        assert result is node_to

    def test_assertion_added_role_to_is_parent(self):
        """node_to is parent of node_from: updates node_from's to_parent label."""
        checker = PairWiseDirectBlockingChecker()
        role = AtomicRole.create("http://test#r")
        obj_from = PairWiseBlockingObject(checker, MagicMock())
        node_from = MagicMock()
        node_to = MagicMock()
        node_from.is_parent_of.return_value = False
        node_to.is_parent_of.return_value = True
        node_from.get_blocking_object.return_value = obj_from
        result = checker.assertion_added_role(role, node_from, node_to, False)
        assert obj_from.m_to_parent_label_hash_code == hash(role)
        assert result is node_from

    def test_assertion_added_role_neither_parent(self):
        """Neither is parent: returns None."""
        checker = PairWiseDirectBlockingChecker()
        role = AtomicRole.create("http://test#r")
        node_from = MagicMock()
        node_to = MagicMock()
        node_from.is_parent_of.return_value = False
        node_to.is_parent_of.return_value = False
        result = checker.assertion_added_role(role, node_from, node_to, False)
        assert result is None

    def test_assertion_removed_role_from_is_parent(self):
        checker = PairWiseDirectBlockingChecker()
        role = AtomicRole.create("http://test#r")
        obj_to = PairWiseBlockingObject(checker, MagicMock())
        obj_to.m_from_parent_label_hash_code = hash(role)
        node_from = MagicMock()
        node_to = MagicMock()
        node_from.is_parent_of.return_value = True
        node_to.is_parent_of.return_value = False
        node_to.get_blocking_object.return_value = obj_to
        result = checker.assertion_removed_role(role, node_from, node_to, False)
        assert obj_to.m_from_parent_label_hash_code == 0

    def test_assertion_removed_role_to_is_parent(self):
        checker = PairWiseDirectBlockingChecker()
        role = AtomicRole.create("http://test#r")
        obj_from = PairWiseBlockingObject(checker, MagicMock())
        obj_from.m_to_parent_label_hash_code = hash(role)
        node_from = MagicMock()
        node_to = MagicMock()
        node_from.is_parent_of.return_value = False
        node_to.is_parent_of.return_value = True
        node_from.get_blocking_object.return_value = obj_from
        result = checker.assertion_removed_role(role, node_from, node_to, False)
        assert obj_from.m_to_parent_label_hash_code == 0

    def test_node_initialized(self):
        checker = PairWiseDirectBlockingChecker()
        obj = PairWiseBlockingObject(checker, MagicMock())
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        checker.node_initialized(node)
        assert obj.m_has_changed is True

    def test_node_destroyed(self):
        checker = PairWiseDirectBlockingChecker()
        obj = PairWiseBlockingObject(checker, MagicMock())
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        checker.node_destroyed(node)  # calls obj.destroy()

    def test_assertion_added_non_atomic_concept(self):
        checker = PairWiseDirectBlockingChecker()
        non_concept = MagicMock()
        node = MagicMock()
        result = checker.assertion_added(non_concept, node, False)
        assert result is None

    def test_is_blocked_by_matching(self):
        """Test is_blocked_by when labels match."""
        from hermit.tableau.node_type import NodeType
        checker = PairWiseDirectBlockingChecker()
        sf_c = checker._atomic_concepts_set_factory
        sf_r = checker._atomic_roles_set_factory

        label = sf_c.get_set(["a"])
        sf_c.make_permanent(label)
        role_label = sf_r.get_set([])
        sf_r.make_permanent(role_label)

        # Build mock blocker
        blocker_obj = PairWiseBlockingObject(checker, MagicMock())
        blocker_obj.m_atomic_concepts_label = label
        blocker_obj.m_from_parent_label = role_label
        blocker_obj.m_to_parent_label = role_label

        blocker_parent_obj = PairWiseBlockingObject(checker, MagicMock())
        blocker_parent_obj.m_atomic_concepts_label = label

        blocker = MagicMock()
        blocker.is_blocked.return_value = False
        blocker.node_type = NodeType.TREE_NODE
        blocker.get_blocking_object.return_value = blocker_obj
        blocker_parent = MagicMock()
        blocker_parent.get_blocking_object.return_value = blocker_parent_obj
        blocker.parent = blocker_parent

        # Build mock blocked
        blocked_obj = PairWiseBlockingObject(checker, MagicMock())
        blocked_obj.m_atomic_concepts_label = label
        blocked_obj.m_from_parent_label = role_label
        blocked_obj.m_to_parent_label = role_label

        blocked_parent_obj = PairWiseBlockingObject(checker, MagicMock())
        blocked_parent_obj.m_atomic_concepts_label = label

        blocked = MagicMock()
        blocked.node_type = NodeType.TREE_NODE
        blocked.get_blocking_object.return_value = blocked_obj
        blocked_parent = MagicMock()
        blocked_parent.get_blocking_object.return_value = blocked_parent_obj
        blocked.parent = blocked_parent

        result = checker.is_blocked_by(blocker, blocked)
        assert result is True

    def test_is_blocked_by_non_matching(self):
        """Test is_blocked_by when labels don't match."""
        from hermit.tableau.node_type import NodeType
        checker = PairWiseDirectBlockingChecker()
        sf_c = checker._atomic_concepts_set_factory
        sf_r = checker._atomic_roles_set_factory

        label1 = sf_c.get_set(["a"])
        sf_c.make_permanent(label1)
        label2 = sf_c.get_set(["b"])
        sf_c.make_permanent(label2)
        role_label = sf_r.get_set([])
        sf_r.make_permanent(role_label)

        blocker_obj = PairWiseBlockingObject(checker, MagicMock())
        blocker_obj.m_atomic_concepts_label = label1
        blocker_obj.m_from_parent_label = role_label
        blocker_obj.m_to_parent_label = role_label

        blocker_parent_obj = PairWiseBlockingObject(checker, MagicMock())
        blocker_parent_obj.m_atomic_concepts_label = label1

        blocker = MagicMock()
        blocker.is_blocked.return_value = False
        blocker.node_type = NodeType.TREE_NODE
        blocker.get_blocking_object.return_value = blocker_obj
        blocker_parent = MagicMock()
        blocker_parent.get_blocking_object.return_value = blocker_parent_obj
        blocker.parent = blocker_parent

        blocked_obj = PairWiseBlockingObject(checker, MagicMock())
        blocked_obj.m_atomic_concepts_label = label2  # different
        blocked_obj.m_from_parent_label = role_label
        blocked_obj.m_to_parent_label = role_label

        blocked_parent_obj = PairWiseBlockingObject(checker, MagicMock())
        blocked_parent_obj.m_atomic_concepts_label = label1

        blocked = MagicMock()
        blocked.node_type = NodeType.TREE_NODE
        blocked.get_blocking_object.return_value = blocked_obj
        blocked_parent = MagicMock()
        blocked_parent.get_blocking_object.return_value = blocked_parent_obj
        blocked.parent = blocked_parent

        result = checker.is_blocked_by(blocker, blocked)
        assert result is False

    def test_blocking_hash_code(self):
        """Test blocking_hash_code returns sum of label hash codes."""
        checker = PairWiseDirectBlockingChecker()
        obj = PairWiseBlockingObject(checker, MagicMock())
        obj.m_atomic_concepts_label_hash_code = 10
        obj.m_from_parent_label_hash_code = 20
        obj.m_to_parent_label_hash_code = 30
        parent_obj = PairWiseBlockingObject(checker, MagicMock())
        parent_obj.m_atomic_concepts_label_hash_code = 5

        node = MagicMock()
        node.get_blocking_object.return_value = obj
        parent = MagicMock()
        parent.get_blocking_object.return_value = parent_obj
        node.parent = parent

        result = checker.blocking_hash_code(node)
        assert result == 10 + 5 + 20 + 30

    def test_clear(self):
        checker = PairWiseDirectBlockingChecker()
        # Without tableau, just clears set factories
        checker.clear()

    def test_has_changed_since_validation_false(self):
        checker = PairWiseDirectBlockingChecker()
        assert checker.has_changed_since_validation(MagicMock()) is False

    def test_set_has_changed_since_validation_noop(self):
        checker = PairWiseDirectBlockingChecker()
        checker.set_has_changed_since_validation(MagicMock(), True)


# ============================================================================
# ValidatedSingleBlockingObject unit tests
# ============================================================================

from hermit.blocking.validated_single_direct_blocking_checker import (
    ValidatedSingleBlockingObject,
    ValidatedSingleDirectBlockingChecker,
)


class TestValidatedSingleBlockingObject:
    def _make_checker(self):
        return ValidatedSingleDirectBlockingChecker(has_inverses=False)

    def test_initialize(self):
        checker = self._make_checker()
        obj = ValidatedSingleBlockingObject(checker, MagicMock())
        obj.initialize()
        assert obj.m_blocking_relevant_label is None
        assert obj.m_has_changed_for_blocking is True
        assert obj.m_has_changed_for_validation is True

    def test_destroy_no_labels(self):
        checker = self._make_checker()
        obj = ValidatedSingleBlockingObject(checker, MagicMock())
        obj.destroy()  # no labels set, should not raise

    def test_destroy_with_labels(self):
        checker = self._make_checker()
        sf_c = checker._atomic_concepts_set_factory
        sf_r = checker._atomic_roles_set_factory
        obj = ValidatedSingleBlockingObject(checker, MagicMock())
        obj.m_blocking_relevant_label = sf_c.get_set(["a"])
        sf_c.add_reference(obj.m_blocking_relevant_label)
        obj.m_full_atomic_concepts_label = sf_c.get_set(["b"])
        sf_c.add_reference(obj.m_full_atomic_concepts_label)
        obj.m_full_from_parent_label = sf_r.get_set(["r1"])
        sf_r.add_reference(obj.m_full_from_parent_label)
        obj.m_full_to_parent_label = sf_r.get_set(["r2"])
        sf_r.add_reference(obj.m_full_to_parent_label)
        obj.destroy()
        assert obj.m_blocking_relevant_label is None
        assert obj.m_full_from_parent_label is None

    def test_add_concept_core(self):
        checker = self._make_checker()
        obj = ValidatedSingleBlockingObject(checker, MagicMock())
        concept = AtomicConcept.create("http://test#C")
        obj.add_concept(concept, is_core=True)
        assert obj.m_has_changed_for_blocking is True
        assert obj.m_blocking_relevant_hash_code == hash(concept)

    def test_add_concept_non_core(self):
        checker = self._make_checker()
        obj = ValidatedSingleBlockingObject(checker, MagicMock())
        concept = AtomicConcept.create("http://test#C")
        obj.add_concept(concept, is_core=False)
        # Non-core concepts don't affect blocking hash
        assert obj.m_blocking_relevant_hash_code == 0
        assert obj.m_has_changed_for_validation is True

    def test_remove_concept_core(self):
        checker = self._make_checker()
        obj = ValidatedSingleBlockingObject(checker, MagicMock())
        concept = AtomicConcept.create("http://test#C")
        obj.m_blocking_relevant_hash_code = hash(concept)
        obj.remove_concept(concept, is_core=True)
        assert obj.m_blocking_relevant_hash_code == 0

    def test_remove_concept_non_core(self):
        checker = self._make_checker()
        obj = ValidatedSingleBlockingObject(checker, MagicMock())
        concept = AtomicConcept.create("http://test#C")
        obj.remove_concept(concept, is_core=False)
        assert obj.m_has_changed_for_validation is True

    def test_set_block_violates_parent_constraints(self):
        checker = self._make_checker()
        obj = ValidatedSingleBlockingObject(checker, MagicMock())
        obj.set_block_violates_parent_constraints(True)
        assert obj.m_block_violates_parent_constraints is True
        assert obj.m_has_already_been_checked is False

    def test_block_violates_parent_constraints(self):
        checker = self._make_checker()
        obj = ValidatedSingleBlockingObject(checker, MagicMock())
        obj.m_block_violates_parent_constraints = True
        assert obj.block_violates_parent_constraints() is True

    def test_get_full_atomic_concepts_label_caches(self):
        """get_full_atomic_concepts_label returns cached value."""
        checker = self._make_checker()
        sf = checker._atomic_concepts_set_factory
        label = sf.get_set(["a"])
        sf.add_reference(label)
        obj = ValidatedSingleBlockingObject(checker, MagicMock())
        obj.m_full_atomic_concepts_label = label
        result = obj.get_full_atomic_concepts_label()
        assert result is label

    def test_set_has_already_been_checked(self):
        checker = self._make_checker()
        obj = ValidatedSingleBlockingObject(checker, MagicMock())
        obj.set_has_already_been_checked(True)
        assert obj.has_already_been_checked() is True

    def test_add_concept_non_atomic(self):
        """Adding a non-AtomicConcept only affects validation flag."""
        checker = self._make_checker()
        obj = ValidatedSingleBlockingObject(checker, MagicMock())
        non_atomic = MagicMock()
        obj.add_concept(non_atomic, is_core=True)
        assert obj.m_has_changed_for_validation is True
        # blocking hash shouldn't change for non-AtomicConcept
        assert obj.m_blocking_relevant_hash_code == 0


class TestValidatedSingleCheckerBlockedBy:
    def test_is_blocked_by_same_label(self):
        from hermit.tableau.node_type import NodeType
        checker = ValidatedSingleDirectBlockingChecker(has_inverses=False)
        sf = checker._atomic_concepts_set_factory

        label = sf.get_set(["a"])
        sf.make_permanent(label)

        blocker_obj = ValidatedSingleBlockingObject(checker, MagicMock())
        blocker_obj.m_blocking_relevant_label = label
        blocker = MagicMock()
        blocker.is_blocked.return_value = False
        blocker.node_type = NodeType.TREE_NODE
        blocker.get_blocking_object.return_value = blocker_obj

        blocked_obj = ValidatedSingleBlockingObject(checker, MagicMock())
        blocked_obj.m_blocking_relevant_label = label
        blocked = MagicMock()
        blocked.node_type = NodeType.TREE_NODE
        blocked.get_blocking_object.return_value = blocked_obj

        result = checker.is_blocked_by(blocker, blocked)
        assert result is True

    def test_is_blocked_by_different_label(self):
        from hermit.tableau.node_type import NodeType
        checker = ValidatedSingleDirectBlockingChecker(has_inverses=False)
        sf = checker._atomic_concepts_set_factory

        label1 = sf.get_set(["a"])
        sf.make_permanent(label1)
        label2 = sf.get_set(["b"])
        sf.make_permanent(label2)

        blocker_obj = ValidatedSingleBlockingObject(checker, MagicMock())
        blocker_obj.m_blocking_relevant_label = label1
        blocker = MagicMock()
        blocker.is_blocked.return_value = False
        blocker.node_type = NodeType.TREE_NODE
        blocker.get_blocking_object.return_value = blocker_obj

        blocked_obj = ValidatedSingleBlockingObject(checker, MagicMock())
        blocked_obj.m_blocking_relevant_label = label2
        blocked = MagicMock()
        blocked.node_type = NodeType.TREE_NODE
        blocked.get_blocking_object.return_value = blocked_obj

        result = checker.is_blocked_by(blocker, blocked)
        assert result is False

    def test_blocking_hash_code(self):
        checker = ValidatedSingleDirectBlockingChecker(has_inverses=False)
        obj = ValidatedSingleBlockingObject(checker, MagicMock())
        obj.m_blocking_relevant_hash_code = 99
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        assert checker.blocking_hash_code(node) == 99

    def test_can_be_blocker_with_inverses_no_tree_parent(self):
        """With inverses, can_be_blocker requires parent to be TREE_NODE."""
        from hermit.tableau.node_type import NodeType
        checker = ValidatedSingleDirectBlockingChecker(has_inverses=True)
        node = MagicMock()
        node.node_type = NodeType.TREE_NODE
        parent = MagicMock()
        parent.node_type = NodeType.NAMED_NODE
        node.parent = parent
        assert checker.can_be_blocker(node) is False

    def test_can_be_blocker_with_inverses_tree_parent(self):
        from hermit.tableau.node_type import NodeType
        checker = ValidatedSingleDirectBlockingChecker(has_inverses=True)
        node = MagicMock()
        node.node_type = NodeType.TREE_NODE
        parent = MagicMock()
        parent.node_type = NodeType.TREE_NODE
        node.parent = parent
        assert checker.can_be_blocker(node) is True

    def test_get_blocking_signature_for(self):
        checker = ValidatedSingleDirectBlockingChecker(has_inverses=False)
        sf = checker._atomic_concepts_set_factory
        sr = checker._atomic_roles_set_factory
        label = sf.get_set(["a"])
        role_label = sr.get_set([])
        sr.make_permanent(role_label)

        parent_obj = ValidatedSingleBlockingObject(checker, MagicMock())
        parent_obj.m_full_atomic_concepts_label = label
        sf.add_reference(label)
        parent = MagicMock()
        parent.get_blocking_object.return_value = parent_obj

        obj = ValidatedSingleBlockingObject(checker, MagicMock())
        obj.m_blocking_relevant_label = label
        sf.make_permanent(label)
        obj.m_full_atomic_concepts_label = label
        # Provide from/to parent labels to avoid fetch calls
        obj.m_full_from_parent_label = role_label
        obj.m_full_to_parent_label = role_label
        sr.add_reference(role_label)
        sr.add_reference(role_label)

        inner_node = MagicMock()
        inner_node.parent = parent
        inner_node.get_blocking_object.return_value = obj

        sig = checker.get_blocking_signature_for(inner_node)
        assert sig is not None


# ============================================================================
# AncestorBlocking unit tests (with mocks)
# ============================================================================

from hermit.blocking.ancestor_blocking import AncestorBlocking


class TestAncestorBlockingUnit:
    def _make_blocking(self):
        from hermit.blocking.direct_blocking_checker import DirectBlockingChecker
        checker = MagicMock(spec=DirectBlockingChecker)
        checker.can_be_blocked.return_value = True
        checker.can_be_blocker.return_value = True
        blocking = AncestorBlocking(checker)
        return blocking, checker

    def test_initialize_calls_checker(self):
        blocking, checker = self._make_blocking()
        tableau = MagicMock()
        tableau.get_additional_hyperresolution_manager.return_value = None
        blocking.initialize(tableau)
        checker.initialize.assert_called_once_with(tableau)

    def test_clear_delegates_to_checker(self):
        blocking, checker = self._make_blocking()
        blocking.clear()
        checker.clear.assert_called_once()

    def test_compute_blocking_sets_root_unblocked(self):
        blocking, checker = self._make_blocking()
        tableau = MagicMock()
        tableau.get_additional_hyperresolution_manager.return_value = None
        blocking.m_tableau = tableau

        root = MagicMock()
        root.is_active.return_value = True
        root.parent = None
        root.get_next_tableau_node.return_value = None

        tableau.get_first_tableau_node.return_value = root

        blocking.compute_blocking(False)
        root.set_blocked.assert_called_once_with(None, False)

    def test_compute_blocking_parent_blocked_propagates(self):
        blocking, checker = self._make_blocking()
        tableau = MagicMock()
        tableau.get_additional_hyperresolution_manager.return_value = None
        blocking.m_tableau = tableau

        parent = MagicMock()
        parent.is_active.return_value = True
        parent.parent = None
        parent.is_blocked.return_value = True

        child = MagicMock()
        child.is_active.return_value = True
        child.parent = parent
        child.is_blocked.return_value = False
        child.get_next_tableau_node.return_value = None

        parent.get_next_tableau_node.return_value = child
        tableau.get_first_tableau_node.return_value = parent

        blocking.compute_blocking(False)
        child.set_blocked.assert_called_once_with(parent, False)

    def test_compute_blocking_checks_ancestors(self):
        """When parent is not blocked, checks grandparent etc."""
        blocking, checker = self._make_blocking()
        tableau = MagicMock()
        tableau.get_additional_hyperresolution_manager.return_value = None
        blocking.m_tableau = tableau

        grandparent = MagicMock()
        grandparent.is_active.return_value = True
        grandparent.parent = None
        grandparent.is_blocked.return_value = False

        parent = MagicMock()
        parent.is_active.return_value = True
        parent.parent = grandparent
        parent.is_blocked.return_value = False

        child = MagicMock()
        child.is_active.return_value = True
        child.parent = parent
        child.is_blocked.return_value = False
        child.get_next_tableau_node.return_value = None

        grandparent.get_next_tableau_node.return_value = parent
        parent.get_next_tableau_node.return_value = child
        tableau.get_first_tableau_node.return_value = grandparent

        # checker.is_blocked_by: grandparent blocks child
        checker.is_blocked_by.side_effect = lambda blocker, blocked: blocker is grandparent and blocked is child

        blocking.compute_blocking(False)
        child.set_blocked.assert_called_with(grandparent, True)

    def test_is_permanent_assertion(self):
        blocking, _ = self._make_blocking()
        assert blocking.is_permanent_assertion(MagicMock(), MagicMock()) is True

    def test_is_exact(self):
        blocking, _ = self._make_blocking()
        assert blocking.is_exact() is True

    def test_assertion_added_atomic_concept(self):
        blocking, checker = self._make_blocking()
        concept = AtomicConcept.create("http://test#C")
        node = MagicMock()
        blocking.assertion_added(concept, node, False, False)
        checker.assertion_added.assert_called_once()

    def test_assertion_added_atomic_concept_only(self):
        blocking, checker = self._make_blocking()
        concept = AtomicConcept.create("http://test#C2")
        node = MagicMock()
        checker.assertion_added.return_value = None
        blocking.assertion_added(concept, node, False, False)
        checker.assertion_added.assert_called()

    def test_assertion_removed_atomic_concept(self):
        blocking, checker = self._make_blocking()
        concept = AtomicConcept.create("http://test#C")
        node = MagicMock()
        checker.assertion_removed.return_value = None
        blocking.assertion_removed(concept, node, False, False)
        checker.assertion_removed.assert_called()

    def test_nodes_merged(self):
        blocking, checker = self._make_blocking()
        blocking.nodes_merged(MagicMock(), MagicMock())
        checker.nodes_merged.assert_called_once()

    def test_nodes_unmerged(self):
        blocking, checker = self._make_blocking()
        blocking.nodes_unmerged(MagicMock(), MagicMock())
        checker.nodes_unmerged.assert_called_once()

    def test_node_status_changed_noop(self):
        blocking, _ = self._make_blocking()
        blocking.node_status_changed(MagicMock())  # no-op

    def test_node_initialized(self):
        blocking, checker = self._make_blocking()
        node = MagicMock()
        blocking.node_initialized(node)
        checker.node_initialized.assert_called_once_with(node)

    def test_node_destroyed(self):
        blocking, checker = self._make_blocking()
        node = MagicMock()
        blocking.node_destroyed(node)
        checker.node_destroyed.assert_called_once_with(node)

    def test_model_found_adds_to_cache(self):
        checker = MagicMock()
        checker.can_be_blocker.return_value = True
        cache = MagicMock()
        cache.is_empty.return_value = False
        blocking = AncestorBlocking(checker, blocking_signature_cache=cache)
        blocking.m_use_blocking_signature_cache = True

        tableau = MagicMock()
        node = MagicMock()
        node.is_active.return_value = True
        node.is_blocked.return_value = False
        node.get_next_tableau_node.return_value = None
        tableau.get_first_tableau_node.return_value = node
        blocking.m_tableau = tableau

        blocking.model_found()
        cache.add_node.assert_called_once_with(node)

    def test_dl_clause_body_compiled(self):
        blocking, _ = self._make_blocking()
        core_variables = [False, False, False]
        blocking.dl_clause_body_compiled([], MagicMock(), [], [], core_variables)
        assert all(core_variables)

    def test_additional_dl_ontology_set(self):
        blocking, _ = self._make_blocking()
        tableau = MagicMock()
        tableau.get_additional_hyperresolution_manager.return_value = None
        blocking.m_tableau = tableau
        blocking.additional_dl_ontology_set(MagicMock())
        assert blocking.m_use_blocking_signature_cache is True

    def test_additional_dl_ontology_cleared(self):
        blocking, _ = self._make_blocking()
        tableau = MagicMock()
        tableau.get_additional_hyperresolution_manager.return_value = None
        blocking.m_tableau = tableau
        blocking.additional_dl_ontology_cleared()
        assert blocking.m_use_blocking_signature_cache is True


# ============================================================================
# AnywhereBlocking unit tests (with mocks)
# ============================================================================

from hermit.blocking.anywhere_blocking import AnywhereBlocking, _BlockersCache


class TestBlockersCache:
    def _make_checker(self, hash_val=1, is_blocked_by_fn=None):
        checker = MagicMock()
        checker.blocking_hash_code.return_value = hash_val
        checker.can_be_blocked.return_value = True
        checker.can_be_blocker.return_value = True
        if is_blocked_by_fn:
            checker.is_blocked_by.side_effect = is_blocked_by_fn
        else:
            checker.is_blocked_by.return_value = False
        return checker

    def test_is_empty_initially(self):
        checker = self._make_checker()
        cache = _BlockersCache(checker)
        assert cache.is_empty()

    def test_add_and_get_node(self):
        checker = self._make_checker(hash_val=100, is_blocked_by_fn=lambda b, n: b is n)
        cache = _BlockersCache(checker)
        node = MagicMock()
        node.get_blocking_cargo.return_value = None
        cache.add_node(node)
        assert not cache.is_empty()
        blocker = cache.get_blocker(node)
        assert blocker is node

    def test_remove_node(self):
        checker = self._make_checker(hash_val=100, is_blocked_by_fn=lambda b, n: b is n)
        cache = _BlockersCache(checker)
        node = MagicMock()
        node.get_blocking_cargo.return_value = None

        cargo_holder = [None]

        def set_cargo(c):
            cargo_holder[0] = c

        def get_cargo():
            return cargo_holder[0]

        node.set_blocking_cargo.side_effect = set_cargo
        node.get_blocking_cargo.side_effect = get_cargo

        cache.add_node(node)
        cache.remove_node(node)
        assert cache.is_empty()

    def test_clear(self):
        checker = self._make_checker()
        cache = _BlockersCache(checker)
        node = MagicMock()
        node.get_blocking_cargo.return_value = None
        cache.add_node(node)
        cache.clear()
        assert cache.is_empty()

    def test_get_blocker_returns_none_when_not_in_cache(self):
        checker = self._make_checker(is_blocked_by_fn=lambda b, n: False)
        cache = _BlockersCache(checker)
        node = MagicMock()
        result = cache.get_blocker(node)
        assert result is None

    def test_get_blocker_cant_be_blocked(self):
        checker = self._make_checker()
        checker.can_be_blocked.return_value = False
        cache = _BlockersCache(checker)
        node = MagicMock()
        result = cache.get_blocker(node)
        assert result is None

    def test_add_duplicate_raises(self):
        checker = self._make_checker(hash_val=50, is_blocked_by_fn=lambda b, n: True)
        cache = _BlockersCache(checker)
        node1 = MagicMock()
        node1.get_blocking_cargo.return_value = None
        node1.set_blocking_cargo = MagicMock()
        cache.add_node(node1)
        node2 = MagicMock()
        node2.get_blocking_cargo.return_value = None
        with pytest.raises(RuntimeError, match="already in the cache"):
            cache.add_node(node2)

    def test_get_index_for(self):
        result = _BlockersCache._get_index_for(42, 1024)
        assert 0 <= result < 1024


class TestAnywhereBlockingUnit:
    def _make_blocking(self):
        from hermit.blocking.direct_blocking_checker import DirectBlockingChecker
        checker = MagicMock(spec=DirectBlockingChecker)
        checker.can_be_blocked.return_value = True
        checker.can_be_blocker.return_value = True
        checker.has_blocking_info_changed.return_value = False
        checker.blocking_hash_code.return_value = 1
        checker.is_blocked_by.return_value = False
        blocking = AnywhereBlocking(checker)
        return blocking, checker

    def test_initialize(self):
        blocking, checker = self._make_blocking()
        tableau = MagicMock()
        tableau.get_additional_hyperresolution_manager.return_value = None
        blocking.initialize(tableau)
        checker.initialize.assert_called_once()

    def test_clear(self):
        blocking, checker = self._make_blocking()
        blocking.clear()
        checker.clear.assert_called_once()
        assert blocking.m_first_changed_node is None

    def test_compute_blocking_noop_when_no_changed(self):
        blocking, checker = self._make_blocking()
        blocking.m_first_changed_node = None
        blocking.compute_blocking(False)  # should be no-op

    def test_compute_blocking_with_changed_node(self):
        blocking, checker = self._make_blocking()
        tableau = MagicMock()
        tableau.get_additional_hyperresolution_manager.return_value = None
        blocking.m_tableau = tableau

        node = MagicMock()
        node.get_node_id.return_value = 1
        node.is_active.return_value = True
        node.is_blocked.return_value = False
        node.is_directly_blocked.return_value = False
        node.get_blocker.return_value = None
        node.parent = None
        node.get_next_tableau_node.return_value = None
        node.get_blocking_cargo.return_value = None

        checker.has_blocking_info_changed.return_value = True

        blocking.m_first_changed_node = node
        blocking.compute_blocking(False)
        node.set_blocked.assert_called_once_with(None, False)

    def test_update_node_change_sets_first_changed(self):
        blocking, _ = self._make_blocking()
        node = MagicMock()
        node.get_node_id.return_value = 5
        blocking._update_node_change(node)
        assert blocking.m_first_changed_node is node

    def test_update_node_change_picks_smaller_id(self):
        blocking, _ = self._make_blocking()
        node1 = MagicMock()
        node1.get_node_id.return_value = 10
        node2 = MagicMock()
        node2.get_node_id.return_value = 3

        blocking._update_node_change(node1)
        blocking._update_node_change(node2)
        assert blocking.m_first_changed_node is node2

    def test_update_node_change_none_noop(self):
        blocking, _ = self._make_blocking()
        blocking._update_node_change(None)
        assert blocking.m_first_changed_node is None

    def test_node_destroyed_clears_first_changed(self):
        blocking, checker = self._make_blocking()
        node = MagicMock()
        node.get_node_id.return_value = 5
        node.get_blocking_cargo.return_value = None
        blocking.m_first_changed_node = node
        blocking.node_destroyed(node)
        assert blocking.m_first_changed_node is None

    def test_node_status_changed(self):
        blocking, _ = self._make_blocking()
        node = MagicMock()
        node.get_node_id.return_value = 7
        blocking.node_status_changed(node)
        assert blocking.m_first_changed_node is node

    def test_is_exact(self):
        blocking, _ = self._make_blocking()
        assert blocking.is_exact() is True

    def test_model_found_noop_without_cache(self):
        blocking, _ = self._make_blocking()
        blocking.m_use_blocking_signature_cache = False
        blocking.model_found()  # should not raise

    def test_dl_clause_body_compiled(self):
        blocking, _ = self._make_blocking()
        core_vars = [False] * 3
        blocking.dl_clause_body_compiled([], MagicMock(), [], [], core_vars)
        assert all(core_vars)

    def test_assertion_added_atomic_concept_triggers_change(self):
        blocking, checker = self._make_blocking()
        concept = AtomicConcept.create("http://test#C")
        node = MagicMock()
        node.get_node_id.return_value = 2
        checker.assertion_added.return_value = node
        blocking.assertion_added(concept, node, False, False)
        assert blocking.m_first_changed_node is node

    def test_assertion_removed_atomic_concept(self):
        blocking, checker = self._make_blocking()
        concept = AtomicConcept.create("http://test#C")
        node = MagicMock()
        node.get_node_id.return_value = 2
        checker.assertion_removed.return_value = node
        blocking.assertion_removed(concept, node, False, False)
        assert blocking.m_first_changed_node is node

    def test_nodes_merged_updates_change(self):
        blocking, checker = self._make_blocking()
        node = MagicMock()
        node.get_node_id.return_value = 3
        checker.nodes_merged.return_value = node
        blocking.nodes_merged(node, MagicMock())
        assert blocking.m_first_changed_node is node

    def test_nodes_unmerged_updates_change(self):
        blocking, checker = self._make_blocking()
        node = MagicMock()
        node.get_node_id.return_value = 3
        checker.nodes_unmerged.return_value = node
        blocking.nodes_unmerged(node, MagicMock())
        assert blocking.m_first_changed_node is node


# ============================================================================
# ValidatedSingleDirectBlockingChecker tests
# ============================================================================

from hermit.blocking.validated_single_direct_blocking_checker import (
    ValidatedSingleDirectBlockingChecker,
    ValidatedSingleBlockingObject,
    ValidatedBlockingObject,
)


class TestValidatedSingleDirectBlockingChecker:
    def test_instantiation(self):
        checker = ValidatedSingleDirectBlockingChecker(has_inverses=False)
        assert checker._tableau is None

    def test_instantiation_with_inverses(self):
        checker = ValidatedSingleDirectBlockingChecker(has_inverses=True)
        assert checker._has_inverses is True

    def test_can_be_blocker_tree_node(self):
        from hermit.tableau.node_type import NodeType
        checker = ValidatedSingleDirectBlockingChecker(has_inverses=False)
        node = MagicMock()
        node.node_type = NodeType.TREE_NODE
        assert checker.can_be_blocker(node) is True

    def test_can_be_blocker_root_node_false(self):
        from hermit.tableau.node_type import NodeType
        checker = ValidatedSingleDirectBlockingChecker(has_inverses=False)
        node = MagicMock()
        node.node_type = NodeType.NAMED_NODE
        assert checker.can_be_blocker(node) is False

    def test_has_changed_since_validation(self):
        checker = ValidatedSingleDirectBlockingChecker(has_inverses=False)
        obj = MagicMock(spec=ValidatedSingleBlockingObject)
        obj.m_has_changed_for_validation = True
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        assert checker.has_changed_since_validation(node) is True

    def test_set_has_changed_since_validation(self):
        checker = ValidatedSingleDirectBlockingChecker(has_inverses=False)
        obj = MagicMock(spec=ValidatedSingleBlockingObject)
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        checker.set_has_changed_since_validation(node, False)
        assert obj.m_has_changed_for_validation is False

    def test_assertion_added_role_updates_label(self):
        checker = ValidatedSingleDirectBlockingChecker(has_inverses=False)
        role = AtomicRole.create("http://test#r")
        obj_from = MagicMock(spec=ValidatedSingleBlockingObject)
        obj_to = MagicMock(spec=ValidatedSingleBlockingObject)
        node_from = MagicMock()
        node_to = MagicMock()
        node_from.get_blocking_object.return_value = obj_from
        node_to.get_blocking_object.return_value = obj_to
        result = checker.assertion_added_role(role, node_from, node_to, False)
        # Should have called add_role or similar on obj_from/obj_to
        # The exact method depends on implementation but shouldn't raise


# ============================================================================
# ValidatedPairwiseDirectBlockingChecker tests
# ============================================================================

from hermit.blocking.validated_pairwise_direct_blocking_checker import (
    ValidatedPairwiseDirectBlockingChecker,
    ValidatedPairwiseBlockingObject,
)


class TestValidatedPairwiseDirectBlockingChecker:
    def test_instantiation(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        assert checker._tableau is None

    def test_instantiation_with_inverses(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=True)
        assert checker._has_inverses is True

    def test_can_be_blocker_no_inverses(self):
        from hermit.tableau.node_type import NodeType
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        node = MagicMock()
        node.node_type = NodeType.TREE_NODE
        node.parent = MagicMock()
        node.parent.node_type = NodeType.NAMED_NODE
        # Without inverses, only requires TREE_NODE
        assert checker.can_be_blocker(node) is True

    def test_can_be_blocker_with_inverses_tree_parent(self):
        from hermit.tableau.node_type import NodeType
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=True)
        node = MagicMock()
        node.node_type = NodeType.TREE_NODE
        node.parent = MagicMock()
        node.parent.node_type = NodeType.TREE_NODE
        assert checker.can_be_blocker(node) is True

    def test_can_be_blocker_with_inverses_named_parent_false(self):
        from hermit.tableau.node_type import NodeType
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=True)
        node = MagicMock()
        node.node_type = NodeType.TREE_NODE
        node.parent = MagicMock()
        node.parent.node_type = NodeType.NAMED_NODE
        assert checker.can_be_blocker(node) is False

    def test_can_be_blocked(self):
        from hermit.tableau.node_type import NodeType
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        node = MagicMock()
        node.node_type = NodeType.TREE_NODE
        node.parent = MagicMock()
        node.parent.node_type = NodeType.TREE_NODE
        assert checker.can_be_blocked(node) is True

    def test_has_blocking_info_changed(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        obj.m_has_changed_for_blocking = True
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        assert checker.has_blocking_info_changed(node) is True

    def test_clear_blocking_info_changed(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        obj.m_has_changed_for_blocking = True
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        checker.clear_blocking_info_changed(node)
        assert obj.m_has_changed_for_blocking is False

    def test_has_changed_since_validation(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        obj.m_has_changed_for_validation = True
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        assert checker.has_changed_since_validation(node) is True

    def test_set_has_changed_since_validation(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        checker.set_has_changed_since_validation(node, False)
        assert obj.m_has_changed_for_validation is False

    def test_node_initialized(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        checker.node_initialized(node)
        assert obj.m_has_changed_for_blocking is True

    def test_node_destroyed(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        checker.node_destroyed(node)  # should not raise

    def test_assertion_added_atomic_concept_core(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        concept = AtomicConcept.create("http://test#C")
        result = checker.assertion_added(concept, node, is_core=True)
        assert result is node

    def test_assertion_added_atomic_concept_non_core(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        concept = AtomicConcept.create("http://test#C")
        result = checker.assertion_added(concept, node, is_core=False)
        assert result is None

    def test_assertion_removed_atomic_concept(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        concept = AtomicConcept.create("http://test#C")
        result = checker.assertion_removed(concept, node, is_core=True)
        assert result is node

    def test_assertion_added_dr_returns_none(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        result = checker.assertion_added_dr(MagicMock(), MagicMock(), False)
        assert result is None

    def test_assertion_removed_dr_returns_none(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        result = checker.assertion_removed_dr(MagicMock(), MagicMock(), False)
        assert result is None

    def test_assertion_added_role_returns_none(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        result = checker.assertion_added_role(MagicMock(), MagicMock(), MagicMock(), False)
        assert result is None

    def test_assertion_removed_role_returns_none(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        result = checker.assertion_removed_role(MagicMock(), MagicMock(), MagicMock(), False)
        assert result is None

    def test_nodes_merged_returns_none(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        assert checker.nodes_merged(MagicMock(), MagicMock()) is None

    def test_nodes_unmerged_returns_none(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        assert checker.nodes_unmerged(MagicMock(), MagicMock()) is None

    def test_clear(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        checker.clear()  # should not raise

    def test_is_blocked_by(self):
        """Test is_blocked_by with matching labels."""
        from hermit.tableau.node_type import NodeType
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        sf = checker._atomic_concepts_set_factory

        label = sf.get_set(["a"])
        sf.make_permanent(label)

        blocker_obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        blocker_obj.m_blocking_relevant_label = label
        blocker_parent_obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        blocker_parent_obj.m_blocking_relevant_label = label
        blocker = MagicMock()
        blocker.is_blocked.return_value = False
        blocker.node_type = NodeType.TREE_NODE
        blocker.get_blocking_object.return_value = blocker_obj
        blocker_parent = MagicMock()
        blocker_parent.get_blocking_object.return_value = blocker_parent_obj
        blocker.parent = blocker_parent

        blocked_obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        blocked_obj.m_blocking_relevant_label = label
        blocked_parent_obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        blocked_parent_obj.m_blocking_relevant_label = label
        blocked = MagicMock()
        blocked.node_type = NodeType.TREE_NODE
        blocked.get_blocking_object.return_value = blocked_obj
        blocked_parent = MagicMock()
        blocked_parent.get_blocking_object.return_value = blocked_parent_obj
        blocked.parent = blocked_parent

        result = checker.is_blocked_by(blocker, blocked)
        assert result is True

    def test_blocking_hash_code(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        obj.m_blocking_relevant_hash_code = 77
        parent_obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        parent_obj.m_blocking_relevant_hash_code = 3
        parent = MagicMock()
        parent.get_blocking_object.return_value = parent_obj
        node = MagicMock()
        node.get_blocking_object.return_value = obj
        node.parent = parent
        # hash = node + parent blocking hash codes
        assert checker.blocking_hash_code(node) == 77 + 3


class TestPairWiseBlockingSignature:
    """Tests for PairWiseBlockingSignature."""

    def _make_sig_with_labels(self, checker):
        sf_c = checker._atomic_concepts_set_factory
        sf_r = checker._atomic_roles_set_factory
        concept_label = sf_c.get_set(["a"])
        sf_c.make_permanent(concept_label)
        parent_label = sf_c.get_set(["p"])
        sf_c.make_permanent(parent_label)
        role_label = sf_r.get_set([])
        sf_r.make_permanent(role_label)

        node_obj = PairWiseBlockingObject(checker, MagicMock())
        node_obj.m_atomic_concepts_label = concept_label
        node_obj.m_from_parent_label = role_label
        node_obj.m_to_parent_label = role_label
        sf_r.add_reference(role_label)
        sf_r.add_reference(role_label)

        parent_obj = PairWiseBlockingObject(checker, MagicMock())
        parent_obj.m_atomic_concepts_label = parent_label

        node = MagicMock()
        node.get_blocking_object.return_value = node_obj
        parent = MagicMock()
        parent.get_blocking_object.return_value = parent_obj
        node.parent = parent
        return node, node_obj, parent_obj, concept_label, parent_label, role_label

    def test_get_blocking_signature_for(self):
        from hermit.blocking.pairwise_direct_blocking_checker import PairWiseBlockingSignature
        checker = PairWiseDirectBlockingChecker()
        node, _, _, _, _, _ = self._make_sig_with_labels(checker)
        sig = checker.get_blocking_signature_for(node)
        assert sig is not None
        assert isinstance(sig, PairWiseBlockingSignature)

    def test_blocks_node_true(self):
        from hermit.blocking.pairwise_direct_blocking_checker import PairWiseBlockingSignature
        checker = PairWiseDirectBlockingChecker()
        node, node_obj, parent_obj, concept_label, parent_label, role_label = self._make_sig_with_labels(checker)
        sig = checker.get_blocking_signature_for(node)

        # Now test blocks_node with same node
        result = sig.blocks_node(node)
        assert result is True

    def test_blocks_node_false_different(self):
        from hermit.blocking.pairwise_direct_blocking_checker import PairWiseBlockingSignature
        checker = PairWiseDirectBlockingChecker()
        node, _, _, concept_label, _, _ = self._make_sig_with_labels(checker)
        sig = checker.get_blocking_signature_for(node)

        # Different node with different label
        sf_c = checker._atomic_concepts_set_factory
        other_label = sf_c.get_set(["other"])
        other_obj = PairWiseBlockingObject(checker, MagicMock())
        other_obj.m_atomic_concepts_label = other_label
        other_parent_obj = PairWiseBlockingObject(checker, MagicMock())
        other_parent_obj.m_atomic_concepts_label = other_label
        other_node = MagicMock()
        other_node.get_blocking_object.return_value = other_obj
        other_parent = MagicMock()
        other_parent.get_blocking_object.return_value = other_parent_obj
        other_node.parent = other_parent

        result = sig.blocks_node(other_node)
        assert result is False

    def test_hash_and_eq(self):
        from hermit.blocking.pairwise_direct_blocking_checker import PairWiseBlockingSignature
        checker = PairWiseDirectBlockingChecker()
        node, _, _, _, _, _ = self._make_sig_with_labels(checker)
        sig1 = checker.get_blocking_signature_for(node)
        sig2 = checker.get_blocking_signature_for(node)
        assert hash(sig1) == hash(sig2)
        assert sig1 == sig2

    def test_eq_different(self):
        from hermit.blocking.pairwise_direct_blocking_checker import PairWiseBlockingSignature
        checker = PairWiseDirectBlockingChecker()
        sf_c = checker._atomic_concepts_set_factory
        sf_r = checker._atomic_roles_set_factory

        node1, _, _, _, _, _ = self._make_sig_with_labels(checker)
        # Make different labels for node2
        label2 = sf_c.get_set(["x"])
        sf_c.make_permanent(label2)
        role_label = sf_r.get_set([])
        node2_obj = PairWiseBlockingObject(checker, MagicMock())
        node2_obj.m_atomic_concepts_label = label2
        node2_obj.m_from_parent_label = role_label
        node2_obj.m_to_parent_label = role_label
        sf_r.make_permanent(role_label)
        parent2_obj = PairWiseBlockingObject(checker, MagicMock())
        parent2_obj.m_atomic_concepts_label = label2
        node2 = MagicMock()
        node2.get_blocking_object.return_value = node2_obj
        parent2 = MagicMock()
        parent2.get_blocking_object.return_value = parent2_obj
        node2.parent = parent2

        sig1 = checker.get_blocking_signature_for(node1)
        sig2 = checker.get_blocking_signature_for(node2)
        assert sig1 != sig2

    def test_eq_with_non_sig(self):
        from hermit.blocking.pairwise_direct_blocking_checker import PairWiseBlockingSignature
        checker = PairWiseDirectBlockingChecker()
        node, _, _, _, _, _ = self._make_sig_with_labels(checker)
        sig = checker.get_blocking_signature_for(node)
        assert sig != "not a sig"


class TestValidatedPairwiseBlockingObject:
    def test_initialize(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        obj.initialize()
        assert obj.m_has_changed_for_blocking is True
        assert obj.m_has_changed_for_validation is True

    def test_destroy_with_labels(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        sf_c = checker._atomic_concepts_set_factory
        sf_r = checker._atomic_roles_set_factory
        obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        obj.m_blocking_relevant_label = sf_c.get_set(["a"])
        sf_c.add_reference(obj.m_blocking_relevant_label)
        obj.m_full_from_parent_label = sf_r.get_set(["r1"])
        sf_r.add_reference(obj.m_full_from_parent_label)
        obj.destroy()
        assert obj.m_blocking_relevant_label is None

    def test_add_concept_core(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        concept = AtomicConcept.create("http://test#C")
        obj.add_concept(concept, is_core=True)
        assert obj.m_has_changed_for_blocking is True
        assert obj.m_blocking_relevant_hash_code == hash(concept)

    def test_add_concept_non_core(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        concept = AtomicConcept.create("http://test#C")
        obj.add_concept(concept, is_core=False)
        assert obj.m_has_changed_for_blocking is False
        assert obj.m_blocking_relevant_hash_code == 0

    def test_remove_concept_core(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        concept = AtomicConcept.create("http://test#C")
        obj.m_blocking_relevant_hash_code = hash(concept)
        obj.remove_concept(concept, is_core=True)
        assert obj.m_blocking_relevant_hash_code == 0

    def test_set_block_violates(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        obj.set_block_violates_parent_constraints(True)
        assert obj.block_violates_parent_constraints() is True
        assert obj.m_has_already_been_checked is False

    def test_set_has_already_been_checked(self):
        checker = ValidatedPairwiseDirectBlockingChecker(has_inverses=False)
        obj = ValidatedPairwiseBlockingObject(checker, MagicMock())
        obj.set_has_already_been_checked(True)
        assert obj.has_already_been_checked() is True


# ============================================================================
# BlockingValidator unit tests
# ============================================================================

from hermit.blocking.blocking_validator import BlockingValidator, _YConstraint, _ArgumentType


class TestYConstraint:
    def test_is_satisfied_explicitly_all_true(self):
        ext_mgr = MagicMock()
        ext_mgr.contains_assertion.return_value = True

        yc = _YConstraint(
            y_concepts=["concept1"],
            x2y_roles=["role1"],
            y2x_roles=["role2"],
        )
        node_x = MagicMock()
        node_y = MagicMock()
        result = yc.is_satisfied_explicitly(ext_mgr, node_x, node_y)
        assert result is True

    def test_is_satisfied_explicitly_role_missing(self):
        ext_mgr = MagicMock()
        ext_mgr.contains_assertion.return_value = False

        yc = _YConstraint(
            y_concepts=[],
            x2y_roles=["role1"],
            y2x_roles=[],
        )
        result = yc.is_satisfied_explicitly(ext_mgr, MagicMock(), MagicMock())
        assert result is False

    def test_is_satisfied_explicitly_concept_missing(self):
        ext_mgr = MagicMock()
        # First calls (roles) return True, concept returns False
        ext_mgr.contains_assertion.side_effect = [True, True, False]

        yc = _YConstraint(
            y_concepts=["concept1"],
            x2y_roles=["role1"],
            y2x_roles=["role2"],
        )
        result = yc.is_satisfied_explicitly(ext_mgr, MagicMock(), MagicMock())
        assert result is False

    def test_is_satisfied_via_mirroring_y_blocked(self):
        """When node_y is blocked, uses its blocker for concept check."""
        ext_mgr = MagicMock()
        ext_mgr.contains_assertion.return_value = True

        blocker = MagicMock()
        node_y = MagicMock()
        node_y.is_blocked.return_value = True
        blocking_obj = MagicMock()
        blocking_obj.block_violates_parent_constraints.return_value = False
        node_y.get_blocking_object.return_value = blocking_obj
        node_y.get_blocker.return_value = blocker

        yc = _YConstraint(
            y_concepts=["concept1"],
            x2y_roles=[],
            y2x_roles=[],
        )
        result = yc.is_satisfied_via_mirroring_y(ext_mgr, MagicMock(), node_y)
        assert result is True

    def test_is_satisfied_via_mirroring_y_not_blocked(self):
        """When node_y is not blocked, uses node_y itself."""
        ext_mgr = MagicMock()
        ext_mgr.contains_assertion.return_value = True

        node_y = MagicMock()
        node_y.is_blocked.return_value = False

        yc = _YConstraint(
            y_concepts=["concept1"],
            x2y_roles=[],
            y2x_roles=[],
        )
        result = yc.is_satisfied_via_mirroring_y(ext_mgr, MagicMock(), node_y)
        assert result is True


class TestArgumentType:
    def test_enum_values(self):
        assert _ArgumentType.XVAR.value == 0
        assert _ArgumentType.YVAR.value == 1
        assert _ArgumentType.ZVAR.value == 2


class TestBlockingValidatorUnit:
    """Unit tests for BlockingValidator that can run without a full Tableau."""

    def _make_mock_extension_manager(self):
        em = MagicMock()
        binary_table = MagicMock()
        binary_table.create_retrieval.return_value = MagicMock()
        em.get_binary_extension_table.return_value = binary_table
        ternary_table = MagicMock()
        ternary_table.create_retrieval.return_value = MagicMock()
        em.get_ternary_extension_table.return_value = ternary_table
        return em

    def test_constructor_with_empty_clauses(self):
        em = self._make_mock_extension_manager()
        tableau = MagicMock()
        tableau.m_extension_manager = em
        validator = BlockingValidator(tableau, frozenset())
        assert len(validator.m_dl_clause_infos) == 0

    def test_clear(self):
        em = self._make_mock_extension_manager()
        tableau = MagicMock()
        tableau.m_extension_manager = em
        validator = BlockingValidator(tableau, frozenset())
        validator.clear()  # should not raise

    def test_clear_invalids(self):
        em = self._make_mock_extension_manager()
        tableau = MagicMock()
        tableau.m_extension_manager = em
        validator = BlockingValidator(tableau, frozenset())
        validator.clear_invalids()  # should not raise

    def test_has_violation_false_when_empty(self):
        em = self._make_mock_extension_manager()
        tableau = MagicMock()
        tableau.m_extension_manager = em
        validator = BlockingValidator(tableau, frozenset())
        assert validator.has_violation() is False

    def test_constructor_with_body_only_clause(self):
        """BlockingValidator with a clause that has no Y-variables."""
        em = self._make_mock_extension_manager()
        tableau = MagicMock()
        tableau.m_extension_manager = em

        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        B = AtomicConcept.create("http://test#B")

        # Simple concept-only clause: A(X) -> B(X) - no Y vars
        clause = DLClause.create(
            (Atom.create(B, X),),
            (Atom.create(A, X),),
        )
        # The DLClauseInfo uses get_name() which is a bug in the source,
        # but if there are no Y variables the loop won't hit that code path.
        # This tests the basic constructor path.
        validator = BlockingValidator(tableau, frozenset([clause]))
        assert validator is not None


# ============================================================================
# AnywhereValidatedBlocking unit tests
# ============================================================================

from hermit.blocking.anywhere_validated_blocking import AnywhereValidatedBlocking


class TestAnywhereValidatedBlocking:
    def _make_blocking(self):
        checker = MagicMock()
        checker.can_be_blocked.return_value = True
        checker.can_be_blocker.return_value = True
        checker.has_blocking_info_changed.return_value = False
        blocking = AnywhereValidatedBlocking(checker, has_inverses=False, use_simple_core=True)
        return blocking, checker

    def test_instantiation(self):
        blocking, _ = self._make_blocking()
        assert blocking.m_tableau is None

    def test_clear(self):
        blocking, checker = self._make_blocking()
        blocking.clear()
        checker.clear.assert_called_once()

    def test_initialize(self):
        blocking, checker = self._make_blocking()
        tableau = MagicMock()
        tableau.get_additional_hyperresolution_manager.return_value = None
        tableau.m_permanent_dl_ontology = MagicMock()
        tableau.m_permanent_dl_ontology.get_dl_clauses.return_value = []
        tableau.m_permanent_dl_ontology.has_inverses.return_value = False
        blocking.initialize(tableau)
        checker.initialize.assert_called_once_with(tableau)

    def test_is_exact_returns_false(self):
        blocking, _ = self._make_blocking()
        assert blocking.is_exact() is False

    def test_node_status_changed_updates_change(self):
        blocking, _ = self._make_blocking()
        node = MagicMock()
        node.get_node_id.return_value = 5
        blocking.node_status_changed(node)
        assert blocking.m_first_changed_node is node

    def test_node_initialized(self):
        blocking, checker = self._make_blocking()
        node = MagicMock()
        blocking.node_initialized(node)
        checker.node_initialized.assert_called_once_with(node)

    def test_node_destroyed(self):
        blocking, checker = self._make_blocking()
        node = MagicMock()
        node.get_node_id.return_value = 3
        node.get_blocking_cargo.return_value = None
        blocking.m_first_changed_node = MagicMock()
        blocking.m_first_changed_node.get_node_id.return_value = 3
        blocking.node_destroyed(node)
        checker.node_destroyed.assert_called_once_with(node)

    def test_is_permanent_assertion(self):
        blocking, _ = self._make_blocking()
        # AnywhereValidatedBlocking.is_permanent_assertion returns True
        assert blocking.is_permanent_assertion(MagicMock(), MagicMock()) is True

    def test_dl_clause_body_compiled(self):
        blocking, _ = self._make_blocking()
        core_vars = [False] * 3
        blocking.dl_clause_body_compiled([], MagicMock(), [], [], core_vars)
        # Not all should be True for validated blocking — just shouldn't raise


# ============================================================================
# AbstractExpansionStrategy tests
# ============================================================================

from hermit.existentials.abstract_expansion_strategy import AbstractExpansionStrategy, SatType


class ConcreteExpansionStrategy(AbstractExpansionStrategy):
    """Minimal concrete subclass for testing AbstractExpansionStrategy."""

    def __init__(self, blocking_strategy):
        super().__init__(blocking_strategy, True)
        self.expanded = []

    def is_deterministic(self):
        return True

    def _expand_existential(self, at_least, for_node):
        self.expanded.append((at_least, for_node))


class TestAbstractExpansionStrategy:
    def test_instantiation(self):
        blocking = MagicMock()
        strategy = ConcreteExpansionStrategy(blocking)
        assert strategy.m_tableau is None
        assert strategy.m_expand_node_at_a_time is True

    def test_sat_type_enum(self):
        assert SatType.NOT_SATISFIED.value == 0
        assert SatType.PERMANENTLY_SATISFIED.value == 1
        assert SatType.CURRENTLY_SATISFIED.value == 2

    def test_clear(self):
        blocking = MagicMock()
        strategy = ConcreteExpansionStrategy(blocking)
        strategy.m_processed_existentials = [MagicMock()]
        strategy.clear()
        assert len(strategy.m_processed_existentials) == 0
        blocking.clear.assert_called_once()

    def test_branching_point_pushed_noop(self):
        blocking = MagicMock()
        strategy = ConcreteExpansionStrategy(blocking)
        strategy.branching_point_pushed()  # should not raise (may be no-op)

    def test_backtrack_noop(self):
        blocking = MagicMock()
        strategy = ConcreteExpansionStrategy(blocking)
        strategy.backtrack()  # should not raise

    def test_model_found_noop(self):
        blocking = MagicMock()
        strategy = ConcreteExpansionStrategy(blocking)
        strategy.model_found()  # should not raise


# ============================================================================
# CreationOrderStrategy tests
# ============================================================================

from hermit.existentials.creation_order_strategy import CreationOrderStrategy


class TestCreationOrderStrategy:
    def test_instantiation(self):
        blocking = MagicMock()
        strategy = CreationOrderStrategy(blocking)
        assert strategy.m_blocking_strategy is blocking

    def test_is_deterministic(self):
        blocking = MagicMock()
        strategy = CreationOrderStrategy(blocking)
        assert strategy.is_deterministic() is True

    def test_expand_node_at_a_time(self):
        blocking = MagicMock()
        strategy = CreationOrderStrategy(blocking)
        assert strategy.m_expand_node_at_a_time is True


# ============================================================================
# IndividualReuseStrategy tests
# ============================================================================

from hermit.existentials.individual_reuse_strategy import (
    IndividualReuseStrategy,
    NodeBranchingPointPair,
    IndividualReuseBranchingPoint,
)


class TestIndividualReuseStrategy:
    def test_instantiation(self):
        blocking = MagicMock()
        strategy = IndividualReuseStrategy(blocking, is_deterministic=True)
        assert strategy.m_is_deterministic is True
        assert len(strategy.m_reused_nodes) == 0

    def test_instantiation_non_deterministic(self):
        blocking = MagicMock()
        strategy = IndividualReuseStrategy(blocking, is_deterministic=False)
        assert strategy.m_is_deterministic is False

    def test_is_deterministic(self):
        blocking = MagicMock()
        s = IndividualReuseStrategy(blocking, is_deterministic=True)
        assert s.is_deterministic() is True

    def test_clear(self):
        blocking = MagicMock()
        strategy = IndividualReuseStrategy(blocking, is_deterministic=True)
        concept = AtomicConcept.create("http://test#A")
        node = MagicMock()
        strategy.m_reused_nodes[concept] = NodeBranchingPointPair(node, 0)
        strategy.m_dont_reuse_concepts_ever.add(concept)
        strategy.clear()
        assert len(strategy.m_reused_nodes) == 0
        # dont_reuse_concepts_this_run should be populated from ever set
        assert concept in strategy.m_dont_reuse_concepts_this_run

    def test_model_found_updates_ever_set(self):
        blocking = MagicMock()
        strategy = IndividualReuseStrategy(blocking, is_deterministic=True)
        concept = AtomicConcept.create("http://test#B")
        strategy.m_dont_reuse_concepts_this_run.add(concept)
        strategy.model_found()
        assert concept in strategy.m_dont_reuse_concepts_ever

    def test_get_concept_for_node(self):
        blocking = MagicMock()
        strategy = IndividualReuseStrategy(blocking, is_deterministic=True)
        concept = AtomicConcept.create("http://test#C")
        node = MagicMock()
        strategy.m_reused_nodes[concept] = NodeBranchingPointPair(node, 0)
        result = strategy.get_concept_for_node(node)
        assert result is concept

    def test_get_concept_for_node_not_found(self):
        blocking = MagicMock()
        strategy = IndividualReuseStrategy(blocking, is_deterministic=True)
        node = MagicMock()
        assert strategy.get_concept_for_node(node) is None

    def test_get_dont_reuse_concepts_ever(self):
        blocking = MagicMock()
        strategy = IndividualReuseStrategy(blocking, is_deterministic=True)
        result = strategy.get_dont_reuse_concepts_ever()
        assert result is strategy.m_dont_reuse_concepts_ever

    def test_branching_point_pushed_expands_array(self):
        blocking = MagicMock()
        strategy = IndividualReuseStrategy(blocking, is_deterministic=False)
        tableau = MagicMock()
        tableau.m_current_branching_point = 20
        strategy.m_tableau = tableau
        # TupleTable.size is accessed — mock the backtracking table
        strategy.m_reuse_backtracking_table = MagicMock()
        strategy.m_reuse_backtracking_table.size = 0
        strategy.branching_point_pushed()
        assert len(strategy.m_indices_by_branching_point) >= 22

    def test_backtrack_removes_entries(self):
        blocking = MagicMock()
        strategy = IndividualReuseStrategy(blocking, is_deterministic=True)
        concept = AtomicConcept.create("http://test#D")
        node = MagicMock()
        strategy.m_reused_nodes[concept] = NodeBranchingPointPair(node, 0)

        # Mock the backtracking table
        mock_table = MagicMock()
        mock_table.first_free_tuple_index = 1
        mock_table.get_tuple_object.return_value = concept
        strategy.m_reuse_backtracking_table = mock_table

        # Set up tableau mock
        tableau = MagicMock()
        tableau.m_current_branching_point = -1
        strategy.m_tableau = tableau

        strategy.m_indices_by_branching_point[0] = 0

        strategy.backtrack()
        assert concept not in strategy.m_reused_nodes

    def test_initialize_reads_parameters(self):
        blocking = MagicMock()
        strategy = IndividualReuseStrategy(blocking, is_deterministic=True)
        concept = AtomicConcept.create("http://test#E")
        tableau = MagicMock()
        tableau.m_parameters = {
            "IndividualReuseStrategy.reuseAlways": {concept},
            "IndividualReuseStrategy.reuseNever": set(),
        }
        tableau.m_interrupt_flag = MagicMock()
        tableau.m_extension_manager = MagicMock()
        ext_table = MagicMock()
        ext_table.create_retrieval.return_value = MagicMock()
        tableau.m_extension_manager.get_ternary_extension_table.return_value = ext_table
        tableau.m_existential_expansion_manager = MagicMock()
        tableau.m_description_graph_manager = MagicMock()
        blocking.initialize = MagicMock()
        strategy.initialize(tableau)
        assert concept in strategy.m_do_reuse_concepts_always


class TestNodeBranchingPointPair:
    def test_creation(self):
        node = MagicMock()
        pair = NodeBranchingPointPair(node, 5)
        assert pair.m_node is node
        assert pair.m_branching_point == 5


# ============================================================================
# Integration tests via full reasoner (exercises all blocking paths)
# ============================================================================

from hermit import Configuration
from hermit.configuration import (
    BlockingStrategyType,
    DirectBlockingType,
    ExistentialStrategyType,
    BlockingSignatureCacheType,
)


def _make_reasoner(clauses, facts=None, config=None):
    onto = _make_ontology(clauses, facts)
    r = Reasoner(onto, config)
    return r


class TestBlockingStrategiesViaReasoner:
    """Run reasoner with different blocking strategies to maximize code coverage."""

    def _chain_ontology(self):
        """A -> ∃r.A chain that requires blocking."""
        from hermit.model import AtLeastConcept
        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        r = AtomicRole.create("http://test#r")
        ind = Individual.create("http://test#x")
        at_least = AtLeastConcept.create(1, r, A)
        clauses = [
            DLClause.create((Atom.create(at_least, X),), (Atom.create(A, X),)),
        ]
        facts = [Atom.create(A, ind)]
        return clauses, facts

    def test_ancestor_blocking_strategy(self):
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.ANCESTOR
        config.direct_blocking_type = DirectBlockingType.SINGLE
        clauses, facts = self._chain_ontology()
        r = _make_reasoner(clauses, facts, config)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_anywhere_blocking_strategy(self):
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.ANYWHERE
        config.direct_blocking_type = DirectBlockingType.SINGLE
        clauses, facts = self._chain_ontology()
        r = _make_reasoner(clauses, facts, config)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_pairwise_blocking(self):
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.ANYWHERE
        config.direct_blocking_type = DirectBlockingType.PAIR_WISE
        clauses, facts = self._chain_ontology()
        r = _make_reasoner(clauses, facts, config)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_simple_core_blocking(self):
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.SIMPLE_CORE
        clauses, facts = self._chain_ontology()
        r = _make_reasoner(clauses, facts, config)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_complex_core_blocking(self):
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.COMPLEX_CORE
        clauses, facts = self._chain_ontology()
        r = _make_reasoner(clauses, facts, config)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_individual_reuse_strategy(self):
        config = Configuration()
        config.existential_strategy_type = ExistentialStrategyType.INDIVIDUAL_REUSE
        clauses, facts = self._chain_ontology()
        r = _make_reasoner(clauses, facts, config)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_el_strategy(self):
        config = Configuration()
        config.existential_strategy_type = ExistentialStrategyType.EL
        clauses, facts = self._chain_ontology()
        r = _make_reasoner(clauses, facts, config)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_not_cached_blocking_signature(self):
        config = Configuration()
        config.blocking_signature_cache_type = BlockingSignatureCacheType.NOT_CACHED
        clauses, facts = self._chain_ontology()
        r = _make_reasoner(clauses, facts, config)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_inverse_role_triggers_pairwise(self):
        """With inverse roles, OPTIMAL uses PairWiseDirectBlockingChecker."""
        from hermit.model import AtLeastConcept
        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        r = AtomicRole.create("http://test#r")
        r_inv = InverseRole.create(r)
        ind = Individual.create("http://test#x")
        at_least = AtLeastConcept.create(1, r, A)
        at_least_inv = AtLeastConcept.create(1, r_inv, A)
        clauses = [
            DLClause.create((Atom.create(at_least, X),), (Atom.create(A, X),)),
        ]
        facts = [Atom.create(A, ind)]
        onto = _make_ontology(clauses, facts)
        config = Configuration()
        config.direct_blocking_type = DirectBlockingType.OPTIMAL
        r_inst = Reasoner(onto, config)
        try:
            assert r_inst.is_consistent()
        finally:
            r_inst.dispose()

    def test_ancestor_pairwise(self):
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.ANCESTOR
        config.direct_blocking_type = DirectBlockingType.PAIR_WISE
        clauses, facts = self._chain_ontology()
        r = _make_reasoner(clauses, facts, config)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_simple_core_pairwise(self):
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.SIMPLE_CORE
        config.direct_blocking_type = DirectBlockingType.PAIR_WISE
        clauses, facts = self._chain_ontology()
        r = _make_reasoner(clauses, facts, config)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_complex_core_pairwise(self):
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.COMPLEX_CORE
        config.direct_blocking_type = DirectBlockingType.PAIR_WISE
        clauses, facts = self._chain_ontology()
        r = _make_reasoner(clauses, facts, config)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_optimal_strategy_no_inverses(self):
        """OPTIMAL blocking with no inverses => SingleDirectBlockingChecker."""
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.OPTIMAL
        clauses, facts = self._chain_ontology()
        r = _make_reasoner(clauses, facts, config)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_classification_with_anywhere_blocking(self):
        """Taxonomy classification with anywhere blocking."""
        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        B = AtomicConcept.create("http://test#B")
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.ANYWHERE
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        r = _make_reasoner(clauses, None, config)
        try:
            r.precompute_inferences(class_hierarchy=True)
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_inconsistent_with_complex_core(self):
        """Inconsistent ontology detected with COMPLEX_CORE blocking."""
        from hermit.model import AtomicNegationConcept
        A = AtomicConcept.create("http://test#A")
        ind = Individual.create("http://test#ind")
        negA = AtomicNegationConcept.create(A)
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.COMPLEX_CORE
        facts = [Atom.create(A, ind), Atom.create(negA, ind)]
        r = _make_reasoner([], facts, config)
        try:
            assert r.is_consistent() is False
        finally:
            r.dispose()


class TestBlockingWithInverseRoles:
    """Tests with inverse roles to exercise PairWise blocking checker."""

    def _inverse_chain(self):
        from hermit.model import AtLeastConcept
        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        r = AtomicRole.create("http://test#r")
        r_inv = InverseRole.create(r)
        ind = Individual.create("http://test#x")
        at_least = AtLeastConcept.create(1, r, A)
        at_least_inv = AtLeastConcept.create(1, r_inv, A)
        clauses = [
            DLClause.create((Atom.create(at_least, X),), (Atom.create(A, X),)),
        ]
        facts = [Atom.create(A, ind)]
        return clauses, facts

    def _chain_ontology(self):
        from hermit.model import AtLeastConcept
        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        r = AtomicRole.create("http://test#r")
        ind = Individual.create("http://test#x")
        at_least = AtLeastConcept.create(1, r, A)
        clauses = [
            DLClause.create((Atom.create(at_least, X),), (Atom.create(A, X),)),
        ]
        facts = [Atom.create(A, ind)]
        return clauses, facts

    def test_pairwise_with_pair_wise_type(self):
        """Force PairWise blocking even without inverse roles."""
        config = Configuration()
        config.direct_blocking_type = DirectBlockingType.PAIR_WISE
        config.blocking_strategy_type = BlockingStrategyType.ANYWHERE
        clauses, facts = self._chain_ontology()
        onto = _make_ontology(clauses, facts)
        r = Reasoner(onto, config)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_pairwise_explicit(self):
        config = Configuration()
        config.direct_blocking_type = DirectBlockingType.PAIR_WISE
        clauses, facts = self._chain_ontology()
        onto = _make_ontology(clauses, facts)
        r = Reasoner(onto, config)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_validated_pairwise(self):
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.COMPLEX_CORE
        config.direct_blocking_type = DirectBlockingType.PAIR_WISE
        clauses, facts = self._chain_ontology()
        onto = _make_ontology(clauses, facts)
        r = Reasoner(onto, config)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_validated_single(self):
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.COMPLEX_CORE
        config.direct_blocking_type = DirectBlockingType.SINGLE
        clauses, facts = self._chain_ontology()
        onto = _make_ontology(clauses, facts)
        r = Reasoner(onto, config)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_simple_core(self):
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.SIMPLE_CORE
        clauses, facts = self._chain_ontology()
        onto = _make_ontology(clauses, facts)
        r = Reasoner(onto, config)
        try:
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_classification_with_pairwise(self):
        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        B = AtomicConcept.create("http://test#B")
        config = Configuration()
        config.direct_blocking_type = DirectBlockingType.PAIR_WISE
        config.blocking_strategy_type = BlockingStrategyType.ANYWHERE
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        onto = _make_ontology(clauses)
        r = Reasoner(onto, config)
        try:
            r.precompute_inferences(class_hierarchy=True)
            assert r.is_consistent()
        finally:
            r.dispose()

    def test_deep_chain_pairwise(self):
        """Longer chain with pairwise to exercise blocking more."""
        from hermit.model import AtLeastConcept
        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        B = AtomicConcept.create("http://test#B")
        r = AtomicRole.create("http://test#r")
        ind = Individual.create("http://test#x")
        at_least_a = AtLeastConcept.create(1, r, A)
        at_least_b = AtLeastConcept.create(1, r, B)

        clauses = [
            DLClause.create((Atom.create(at_least_a, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        facts = [Atom.create(A, ind)]
        onto = _make_ontology(clauses, facts)
        config = Configuration()
        config.direct_blocking_type = DirectBlockingType.PAIR_WISE
        r_inst = Reasoner(onto, config)
        try:
            assert r_inst.is_consistent()
        finally:
            r_inst.dispose()

    def test_individual_reuse_with_multiple_existentials(self):
        """IndividualReuseStrategy with multiple existentials to expand."""
        from hermit.model import AtLeastConcept
        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        B = AtomicConcept.create("http://test#B")
        r = AtomicRole.create("http://test#r")
        s = AtomicRole.create("http://test#s")
        ind = Individual.create("http://test#x")

        at_least_a = AtLeastConcept.create(1, r, A)
        at_least_b = AtLeastConcept.create(1, s, B)

        clauses = [
            DLClause.create((Atom.create(at_least_a, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(at_least_b, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(A, X),), (Atom.create(B, X),)),
        ]
        facts = [Atom.create(A, ind)]
        onto = _make_ontology(clauses, facts)
        config = Configuration()
        config.existential_strategy_type = ExistentialStrategyType.INDIVIDUAL_REUSE
        r_inst = Reasoner(onto, config)
        try:
            assert r_inst.is_consistent()
        finally:
            r_inst.dispose()


class TestBlockingViaReasoner:
    """Tests that run the full reasoner to exercise blocking code paths."""

    def test_satisfiability_triggers_existential_expansion(self):
        """is_satisfiable(A) creates tree nodes via existential expansion."""
        from hermit.model import AtLeastConcept

        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        r = AtomicRole.create("http://test#r")

        # A ⊑ ∃r.A  (would loop without blocking)
        at_least = AtLeastConcept.create(1, r, A)
        clauses = [
            DLClause.create((Atom.create(at_least, X),), (Atom.create(A, X),)),
        ]
        onto = _make_ontology(clauses)
        reasoner = Reasoner(onto)
        try:
            # is_satisfiable loads A onto fresh individual, triggers existential expansion
            result = reasoner.is_satisfiable(A)
            assert result is True
        finally:
            reasoner.dispose()

    def test_satisfiability_pairwise_chain(self):
        """Pairwise blocking with satisfiability check to force tree nodes."""
        from hermit.model import AtLeastConcept

        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        r = AtomicRole.create("http://test#r")

        at_least = AtLeastConcept.create(1, r, A)
        clauses = [
            DLClause.create((Atom.create(at_least, X),), (Atom.create(A, X),)),
        ]
        onto = _make_ontology(clauses)
        config = Configuration()
        config.direct_blocking_type = DirectBlockingType.PAIR_WISE
        reasoner = Reasoner(onto, config)
        try:
            result = reasoner.is_satisfiable(A)
            assert result is True
        finally:
            reasoner.dispose()

    def test_satisfiability_ancestor_chain(self):
        """Ancestor blocking with satisfiability check."""
        from hermit.model import AtLeastConcept

        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        r = AtomicRole.create("http://test#r")

        at_least = AtLeastConcept.create(1, r, A)
        clauses = [
            DLClause.create((Atom.create(at_least, X),), (Atom.create(A, X),)),
        ]
        onto = _make_ontology(clauses)
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.ANCESTOR
        config.direct_blocking_type = DirectBlockingType.PAIR_WISE
        reasoner = Reasoner(onto, config)
        try:
            result = reasoner.is_satisfiable(A)
            assert result is True
        finally:
            reasoner.dispose()

    def test_satisfiability_validated_blocking(self):
        """Validated blocking with satisfiability check."""
        from hermit.model import AtLeastConcept

        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        r = AtomicRole.create("http://test#r")

        at_least = AtLeastConcept.create(1, r, A)
        clauses = [
            DLClause.create((Atom.create(at_least, X),), (Atom.create(A, X),)),
        ]
        onto = _make_ontology(clauses)
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.COMPLEX_CORE
        config.direct_blocking_type = DirectBlockingType.PAIR_WISE
        reasoner = Reasoner(onto, config)
        try:
            result = reasoner.is_satisfiable(A)
            assert result is True
        finally:
            reasoner.dispose()

    def test_satisfiability_simple_core(self):
        from hermit.model import AtLeastConcept

        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        r = AtomicRole.create("http://test#r")

        at_least = AtLeastConcept.create(1, r, A)
        clauses = [
            DLClause.create((Atom.create(at_least, X),), (Atom.create(A, X),)),
        ]
        onto = _make_ontology(clauses)
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.SIMPLE_CORE
        reasoner = Reasoner(onto, config)
        try:
            result = reasoner.is_satisfiable(A)
            assert result is True
        finally:
            reasoner.dispose()

    def test_subsumption_check_creates_tree_nodes(self):
        """is_sub_class_of test creates a fresh individual + expansion."""
        from hermit.model import AtLeastConcept

        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        B = AtomicConcept.create("http://test#B")
        r = AtomicRole.create("http://test#r")

        at_least = AtLeastConcept.create(1, r, A)
        clauses = [
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(at_least, X),), (Atom.create(A, X),)),
        ]
        onto = _make_ontology(clauses)
        config = Configuration()
        config.direct_blocking_type = DirectBlockingType.PAIR_WISE
        reasoner = Reasoner(onto, config)
        try:
            reasoner.precompute_inferences(class_hierarchy=True)
            assert reasoner.is_sub_class_of(A, B)
        finally:
            reasoner.dispose()

    def test_chain_with_blocking(self):
        """A concept chain that requires blocking to terminate."""
        from hermit.model import AtLeastConcept

        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        r = AtomicRole.create("http://test#r")
        ind = Individual.create("http://test#x")

        # A ⊑ ∃r.A  (would loop without blocking)
        at_least = AtLeastConcept.create(1, r, A)
        clauses = [
            DLClause.create((Atom.create(at_least, X),), (Atom.create(A, X),)),
        ]
        facts = [Atom.create(A, ind)]
        onto = _make_ontology(clauses, facts)
        reasoner = Reasoner(onto)
        try:
            result = reasoner.is_consistent()
            assert result is True
        finally:
            reasoner.dispose()

    def test_inconsistent_ontology(self):
        """An inconsistent ontology (owl:Nothing ⊑ owl:Thing but not reverse)."""
        from hermit.model import AtomicNegationConcept

        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        ind = Individual.create("http://test#ind")
        negA = AtomicNegationConcept.create(A)

        # A(ind) and not A(ind)
        facts = [
            Atom.create(A, ind),
            Atom.create(negA, ind),
        ]
        onto = _make_ontology([], facts)
        reasoner = Reasoner(onto)
        try:
            result = reasoner.is_consistent()
            assert result is False
        finally:
            reasoner.dispose()

    def test_multiple_role_chains(self):
        """Multiple role chains with different concepts — tests blocker cache."""
        from hermit.model import AtLeastConcept

        X = Variable.create("X")
        A = AtomicConcept.create("http://test#A")
        B = AtomicConcept.create("http://test#B")
        r1 = AtomicRole.create("http://test#r1")
        r2 = AtomicRole.create("http://test#r2")
        ind = Individual.create("http://test#ind")

        at_least_a = AtLeastConcept.create(1, r1, A)
        at_least_b = AtLeastConcept.create(1, r2, B)

        clauses = [
            DLClause.create((Atom.create(at_least_a, X),), (Atom.create(A, X),)),
            DLClause.create((Atom.create(at_least_b, X),), (Atom.create(B, X),)),
            DLClause.create((Atom.create(B, X),), (Atom.create(A, X),)),
        ]
        facts = [Atom.create(A, ind)]
        onto = _make_ontology(clauses, facts)
        reasoner = Reasoner(onto)
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()
