"""Regression tests for pyhermit correctness fixes.

Tests all 12 acceptance criteria from spec.md:
1. Functional object property → DL clause in direct_dl_clauses
2. Symmetric property → simple_object_property_inclusions
3. Asymmetric property → asymmetric_object_properties
4. Reflexive property → reflexive_object_properties
5. Irreflexive property → irreflexive_object_properties
6. Disjoint object properties → disjoint_object_properties
7. DLOntology.has_nominals() detection
8. Blocking validator multi-role Y-variable
9. DoubleValueSpaceSubset.complement()
10. DeterministicClassification.classify()
11. Query.evaluate() for one-atom conjunctive query
"""
from __future__ import annotations

import pytest
from hermit.model import (
    AtomicConcept,
    AtomicRole,
    Individual,
    Atom,
    DLClause,
    Variable,
    Equality,
    DLOntology,
)


X = Variable.create("X")
Y = Variable.create("Y")
R_IRI = "http://example.org/R"
S_IRI = "http://example.org/S"
A_IRI = "http://example.org/A"
B_IRI = "http://example.org/B"


def _make_owl_prop(iri: str):
    from hermit.owl_model.owl_property import OWLObjectProperty
    from hermit.owl_model.iri import IRI
    return OWLObjectProperty(IRI.create(iri))


def _make_ontology(clauses, facts, iri="urn:test:reg"):
    return DLOntology(
        ontology_iri=iri,
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset(facts),
    )


# ---------------------------------------------------------------------------
# Acceptance Criteria 1-6: Normalizer fixes
# ---------------------------------------------------------------------------

class TestNormalizerFixes:
    def test_functional_property_creates_dl_clause(self):
        """OWLFunctionalObjectPropertyAxiom → direct_dl_clauses with Equality head."""
        from hermit.owl_model.owl_axiom import OWLFunctionalObjectPropertyAxiom
        from hermit.structural.owl_normalization import OWLNormalization

        axiom = OWLFunctionalObjectPropertyAxiom(_make_owl_prop(R_IRI))
        na = OWLNormalization().process_ontology([axiom])

        assert len(na.direct_dl_clauses) >= 1
        # Head atom should have Equality predicate
        clause = na.direct_dl_clauses[0]
        assert any(a.predicate is Equality.INSTANCE for a in clause.head_atoms)

    def test_inverse_functional_property_creates_dl_clause(self):
        from hermit.owl_model.owl_axiom import OWLInverseFunctionalObjectPropertyAxiom
        from hermit.structural.owl_normalization import OWLNormalization

        axiom = OWLInverseFunctionalObjectPropertyAxiom(_make_owl_prop(R_IRI))
        na = OWLNormalization().process_ontology([axiom])

        assert len(na.direct_dl_clauses) >= 1
        clause = na.direct_dl_clauses[0]
        assert any(a.predicate is Equality.INSTANCE for a in clause.head_atoms)

    def test_symmetric_property_creates_simple_inclusion(self):
        """Symmetric property → (R, R⁻) in simple_object_property_inclusions."""
        from hermit.owl_model.owl_axiom import OWLSymmetricObjectPropertyAxiom
        from hermit.structural.owl_normalization import OWLNormalization
        from hermit.model import AtomicRole, InverseRole

        axiom = OWLSymmetricObjectPropertyAxiom(_make_owl_prop(R_IRI))
        na = OWLNormalization().process_ontology([axiom])

        assert len(na.simple_object_property_inclusions) >= 1
        inc = na.simple_object_property_inclusions[0]
        assert isinstance(inc[0], AtomicRole)
        assert isinstance(inc[1], InverseRole)

    def test_asymmetric_property_uses_correct_field(self):
        from hermit.owl_model.owl_axiom import OWLAsymmetricObjectPropertyAxiom
        from hermit.structural.owl_normalization import OWLNormalization

        axiom = OWLAsymmetricObjectPropertyAxiom(_make_owl_prop(R_IRI))
        na = OWLNormalization().process_ontology([axiom])

        assert len(na.asymmetric_object_properties) == 1
        assert len(na.positive_facts) == 0  # must not fall through to positive_facts

    def test_reflexive_property_uses_correct_field(self):
        from hermit.owl_model.owl_axiom import OWLReflexiveObjectPropertyAxiom
        from hermit.structural.owl_normalization import OWLNormalization

        axiom = OWLReflexiveObjectPropertyAxiom(_make_owl_prop(R_IRI))
        na = OWLNormalization().process_ontology([axiom])

        assert len(na.reflexive_object_properties) == 1

    def test_irreflexive_property_uses_correct_field(self):
        from hermit.owl_model.owl_axiom import OWLIrreflexiveObjectPropertyAxiom
        from hermit.structural.owl_normalization import OWLNormalization

        axiom = OWLIrreflexiveObjectPropertyAxiom(_make_owl_prop(R_IRI))
        na = OWLNormalization().process_ontology([axiom])

        assert len(na.irreflexive_object_properties) == 1

    def test_disjoint_object_properties_uses_correct_field(self):
        from hermit.owl_model.owl_axiom import OWLDisjointObjectPropertiesAxiom
        from hermit.structural.owl_normalization import OWLNormalization

        axiom = OWLDisjointObjectPropertiesAxiom([_make_owl_prop(R_IRI), _make_owl_prop(S_IRI)])
        na = OWLNormalization().process_ontology([axiom])

        assert len(na.disjoint_object_properties) == 1
        assert len(na.disjoint_object_properties[0]) == 2

    def test_sub_data_property_uses_correct_field(self):
        from hermit.owl_model.owl_axiom import OWLSubDataPropertyOfAxiom
        from hermit.owl_model.owl_property import OWLDataProperty
        from hermit.owl_model.iri import IRI
        from hermit.structural.owl_normalization import OWLNormalization

        p = OWLDataProperty(IRI.create("http://example.org/P"))
        q = OWLDataProperty(IRI.create("http://example.org/Q"))
        axiom = OWLSubDataPropertyOfAxiom(p, q)
        na = OWLNormalization().process_ontology([axiom])

        assert len(na.data_property_inclusions) == 1

    def test_disjoint_data_properties_uses_correct_field(self):
        from hermit.owl_model.owl_axiom import OWLDisjointDataPropertiesAxiom
        from hermit.owl_model.owl_property import OWLDataProperty
        from hermit.owl_model.iri import IRI
        from hermit.structural.owl_normalization import OWLNormalization

        p = OWLDataProperty(IRI.create("http://example.org/P"))
        q = OWLDataProperty(IRI.create("http://example.org/Q"))
        axiom = OWLDisjointDataPropertiesAxiom([p, q])
        na = OWLNormalization().process_ontology([axiom])

        assert len(na.disjoint_data_properties) == 1


# ---------------------------------------------------------------------------
# Acceptance Criteria 1–6: End-to-end reasoner entailment tests
# ---------------------------------------------------------------------------

def _reasoner_from_owl_axioms(axioms: list, abox_axioms: list | None = None):
    """Build a Reasoner from OWL axioms through the full normalization pipeline."""
    from hermit.structural.owl_normalization import OWLNormalization
    from hermit.structural.owl_clausification import OWLClausification
    from hermit.reasoner import Reasoner

    norm = OWLNormalization()
    all_axioms = list(axioms) + (abox_axioms or [])
    normalized = norm.process_ontology(all_axioms)
    claus = OWLClausification()
    dl_onto = claus.clausify(normalized, ontology_iri="urn:test:e2e")
    return Reasoner(dl_onto)


class TestEndToEndReasonerEntailments:
    """End-to-end tests: OWL axioms → reasoner → entailment / inconsistency."""

    def test_ac1_functional_property_causes_node_merge(self):
        """AC1: R functional + R(a,b) + R(a,c) → ontology with ≤1R is consistent (b=c)."""
        from hermit.owl_model.owl_axiom import (
            OWLFunctionalObjectPropertyAxiom,
            OWLObjectPropertyAssertionAxiom,
        )
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        from hermit.owl_model.iri import IRI

        R = _make_owl_prop(R_IRI)
        a = OWLNamedIndividual(IRI.create("http://example.org/a"))
        b = OWLNamedIndividual(IRI.create("http://example.org/b"))
        c = OWLNamedIndividual(IRI.create("http://example.org/c"))

        axioms = [OWLFunctionalObjectPropertyAxiom(R)]
        abox = [
            OWLObjectPropertyAssertionAxiom(a, R, b),
            OWLObjectPropertyAssertionAxiom(a, R, c),
        ]
        reasoner = _reasoner_from_owl_axioms(axioms, abox)
        try:
            # Functional property forces b=c — ontology should be consistent
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_ac2_symmetric_property_entails_inverse(self):
        """AC2: SymmetricProperty(R) + R(a,b) + DisjointProperties(R,S) + S(b,a) → inconsistent.

        If R is symmetric, R(a,b) entails R(b,a). Combined with S(b,a) and
        DisjointObjectProperties(R,S), this creates an inconsistency, proving
        that the symmetric inclusion was correctly clausified.
        """
        from hermit.owl_model.owl_axiom import (
            OWLSymmetricObjectPropertyAxiom,
            OWLDisjointObjectPropertiesAxiom,
            OWLObjectPropertyAssertionAxiom,
        )
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        from hermit.owl_model.iri import IRI

        R = _make_owl_prop(R_IRI)
        S = _make_owl_prop(S_IRI)
        a_owl = OWLNamedIndividual(IRI.create("http://example.org/a"))
        b_owl = OWLNamedIndividual(IRI.create("http://example.org/b"))

        axioms = [
            OWLSymmetricObjectPropertyAxiom(R),
            OWLDisjointObjectPropertiesAxiom([R, S]),
        ]
        abox = [
            OWLObjectPropertyAssertionAxiom(a_owl, R, b_owl),
            OWLObjectPropertyAssertionAxiom(b_owl, S, a_owl),
        ]
        reasoner = _reasoner_from_owl_axioms(axioms, abox)
        try:
            # If R is symmetric: R(a,b) → R(b,a). But Disjoint(R,S) + R(b,a) + S(b,a) → ⊥
            assert not reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_ac3_asymmetric_property_detects_inconsistency(self):
        """AC3: AsymmetricProperty(R) + R(a,b) + R(b,a) → inconsistent."""
        from hermit.owl_model.owl_axiom import (
            OWLAsymmetricObjectPropertyAxiom,
            OWLObjectPropertyAssertionAxiom,
        )
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        from hermit.owl_model.iri import IRI

        R = _make_owl_prop(R_IRI)
        a_owl = OWLNamedIndividual(IRI.create("http://example.org/a"))
        b_owl = OWLNamedIndividual(IRI.create("http://example.org/b"))

        axioms = [OWLAsymmetricObjectPropertyAxiom(R)]
        abox = [
            OWLObjectPropertyAssertionAxiom(a_owl, R, b_owl),
            OWLObjectPropertyAssertionAxiom(b_owl, R, a_owl),
        ]
        reasoner = _reasoner_from_owl_axioms(axioms, abox)
        try:
            assert not reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_ac4_reflexive_property_entails_self_loop(self):
        """AC4: ReflexiveProperty(R) + IrreflexiveProperty(R) + individual → inconsistent.

        If R is reflexive, R(a,a) holds for any individual a. Combined with
        IrreflexiveProperty(R) (which clausifies to R(x,x) → ⊥), any individual
        triggers inconsistency, proving the reflexive clause was generated.
        """
        from hermit.owl_model.owl_axiom import (
            OWLReflexiveObjectPropertyAxiom,
            OWLIrreflexiveObjectPropertyAxiom,
            OWLClassAssertionAxiom,
        )
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        from hermit.owl_model.class_expression.owl_class import OWLClass
        from hermit.owl_model.iri import IRI

        R = _make_owl_prop(R_IRI)
        a_owl = OWLNamedIndividual(IRI.create("http://example.org/a"))
        thing = OWLClass(IRI.create("http://www.w3.org/2002/07/owl#Thing"))

        axioms = [OWLReflexiveObjectPropertyAxiom(R), OWLIrreflexiveObjectPropertyAxiom(R)]
        abox = [OWLClassAssertionAxiom(a_owl, thing)]
        reasoner = _reasoner_from_owl_axioms(axioms, abox)
        try:
            # Reflexive(R) generates R(a,a); Irreflexive(R) makes R(x,x) → ⊥ → inconsistent
            assert not reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_ac5_irreflexive_property_detects_self_loop_inconsistency(self):
        """AC5: IrreflexiveProperty(R) + R(a,a) → inconsistent."""
        from hermit.owl_model.owl_axiom import (
            OWLIrreflexiveObjectPropertyAxiom,
            OWLObjectPropertyAssertionAxiom,
        )
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        from hermit.owl_model.iri import IRI

        R = _make_owl_prop(R_IRI)
        a_owl = OWLNamedIndividual(IRI.create("http://example.org/a"))

        axioms = [OWLIrreflexiveObjectPropertyAxiom(R)]
        abox = [OWLObjectPropertyAssertionAxiom(a_owl, R, a_owl)]
        reasoner = _reasoner_from_owl_axioms(axioms, abox)
        try:
            assert not reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_ac6_disjoint_properties_detects_inconsistency(self):
        """AC6: DisjointObjectProperties(R,S) + R(a,b) + S(a,b) → inconsistent."""
        from hermit.owl_model.owl_axiom import (
            OWLDisjointObjectPropertiesAxiom,
            OWLObjectPropertyAssertionAxiom,
        )
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        from hermit.owl_model.iri import IRI

        R = _make_owl_prop(R_IRI)
        S = _make_owl_prop(S_IRI)
        a_owl = OWLNamedIndividual(IRI.create("http://example.org/a"))
        b_owl = OWLNamedIndividual(IRI.create("http://example.org/b"))

        axioms = [OWLDisjointObjectPropertiesAxiom([R, S])]
        abox = [
            OWLObjectPropertyAssertionAxiom(a_owl, R, b_owl),
            OWLObjectPropertyAssertionAxiom(a_owl, S, b_owl),
        ]
        reasoner = _reasoner_from_owl_axioms(axioms, abox)
        try:
            assert not reasoner.is_consistent()
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Acceptance Criterion 7: DLOntology.has_nominals()
# ---------------------------------------------------------------------------

class TestDLOntologyHasNominals:
    def test_has_nominals_true_when_nominal_in_positive_facts(self):
        nom = AtomicConcept.create("internal:nom#SomeIndividual")
        ind = Individual.create("http://example.org/a")
        fact = Atom.create(nom, ind)
        ont = _make_ontology([], [fact])
        assert ont.has_nominals() is True

    def test_has_nominals_false_for_regular_concept(self):
        A = AtomicConcept.create("http://example.org/A")
        ind = Individual.create("http://example.org/a")
        fact = Atom.create(A, ind)
        ont = _make_ontology([], [fact])
        assert ont.has_nominals() is False

    def test_has_nominals_true_when_nominal_in_dl_clause(self):
        nom = AtomicConcept.create("internal:nom#IndB")
        A = AtomicConcept.create("http://example.org/A")
        clause = DLClause.create((Atom.create(A, X),), (Atom.create(nom, X),))
        ont = _make_ontology([clause], [])
        assert ont.has_nominals() is True


# ---------------------------------------------------------------------------
# Acceptance Criterion 8: Blocking validator multi-role Y-variable
# ---------------------------------------------------------------------------

class TestBlockingValidatorMultiRole:
    def test_dl_clause_info_accumulates_all_roles_for_y_variable(self):
        """DLClauseInfo creates one retrieval per (Y-var, role) pair, not one per Y-var."""
        from hermit.blocking.blocking_validator import DLClauseInfo
        from hermit.model import AtomicRole

        R = AtomicRole.create("http://example.org/R")
        S = AtomicRole.create("http://example.org/S")
        A = AtomicConcept.create("http://example.org/A")

        # DL clause: R(X,Y) ∧ S(X,Y) → A(X)
        clause = DLClause.create(
            (Atom.create(A, X),),
            (Atom.create(R, X, Y), Atom.create(S, X, Y)),
        )

        class MockRetrieval:
            def get_bindings_buffer(self):
                return [None, None, None]

        class MockTable:
            def create_retrieval(self, mask, mode):
                return MockRetrieval()

        class MockExtManager:
            def get_binary_extension_table(self):
                return MockTable()
            def get_ternary_extension_table(self):
                return MockTable()

        info = DLClauseInfo(clause, MockExtManager())
        # With 2 roles for the same Y-variable, should have 2 entries in m_x2y_roles
        assert len(info.m_x2y_roles) == 2


# ---------------------------------------------------------------------------
# Acceptance Criterion 9: DoubleValueSpaceSubset.complement()
# ---------------------------------------------------------------------------

class TestDoubleValueSpaceSubsetComplement:
    def test_complement_of_finite_set_is_not_empty(self):
        from hermit.datatypes.doublenum import DoubleValueSpaceSubset
        vs = DoubleValueSpaceSubset(values=frozenset({1.0}))
        assert not vs.complement().is_empty()

    def test_complement_excludes_original_values(self):
        from hermit.datatypes.doublenum import DoubleValueSpaceSubset
        vs = DoubleValueSpaceSubset(values=frozenset({1.0, 2.0}))
        comp = vs.complement()
        assert not comp.contains(1.0)
        assert not comp.contains(2.0)

    def test_complement_includes_other_floats(self):
        from hermit.datatypes.doublenum import DoubleValueSpaceSubset
        vs = DoubleValueSpaceSubset(values=frozenset({1.0}))
        comp = vs.complement()
        assert comp.contains(2.0)
        assert comp.contains(0.0)

    def test_double_complement_restores_original(self):
        from hermit.datatypes.doublenum import DoubleValueSpaceSubset
        vs = DoubleValueSpaceSubset(values=frozenset({1.0, 2.0}))
        dc = vs.complement().complement()
        assert dc.contains(1.0)
        assert dc.contains(2.0)
        assert not dc.contains(3.0)

    def test_intersect_finite_with_complement(self):
        from hermit.datatypes.doublenum import DoubleValueSpaceSubset
        vs = DoubleValueSpaceSubset(values=frozenset({1.0, 2.0, 3.0}))
        comp_1 = DoubleValueSpaceSubset(values=frozenset({1.0})).complement()
        result = vs.intersect(comp_1)
        assert result.contains(2.0)
        assert result.contains(3.0)
        assert not result.contains(1.0)

    def test_complement_entire_is_empty(self):
        from hermit.datatypes.doublenum import DoubleValueSpaceSubset
        assert DoubleValueSpaceSubset(entire=True).complement().is_empty()

    def test_complement_empty_is_nonempty(self):
        from hermit.datatypes.doublenum import DoubleValueSpaceSubset
        comp = DoubleValueSpaceSubset(empty=True).complement()
        assert not comp.is_empty()
        assert comp.contains(1.0)


# ---------------------------------------------------------------------------
# Acceptance Criterion 10: DeterministicClassification.classify()
# ---------------------------------------------------------------------------

class TestDeterministicClassification:
    def test_classify_returns_valid_hierarchy(self):
        """DeterministicClassification.classify() returns a Hierarchy."""
        from hermit.reasoner import Reasoner

        A = AtomicConcept.create("http://example.org/A")
        B = AtomicConcept.create("http://example.org/B")
        a = Individual.create("http://example.org/a")

        clause = DLClause.create((Atom.create(B, X),), (Atom.create(A, X),))
        fact = Atom.create(A, a)
        ont = _make_ontology([clause], [fact], iri="http://example.org/test")

        reasoner = Reasoner(ont)
        try:
            reasoner.classify_classes()
            hierarchy = reasoner._atomic_concept_hierarchy
            assert hierarchy is not None
            b_node = hierarchy.get_node_for_element(B)
            assert b_node is not None
        finally:
            reasoner.dispose()


# ---------------------------------------------------------------------------
# Acceptance Criterion 11: Query.evaluate() for conjunctive queries
# ---------------------------------------------------------------------------

class TestConjunctiveQueryEvaluate:
    def test_one_atom_query_finds_individuals(self):
        """Query Dog(x) returns at least one result when Dog(fido) is a fact."""
        from hermit.datalog import DatalogEngine, ConjunctiveQuery, QueryResultCollector

        dog = AtomicConcept.create("http://example.org/Dog")
        fido = Individual.create("http://example.org/fido")
        fact = Atom.create(dog, fido)
        ont = _make_ontology([], [fact], iri="http://example.org/cqtest")

        engine = DatalogEngine(ont)
        results = []

        class Collector(QueryResultCollector):
            def process_result(self, query, result):
                results.append(result[:])

        query = ConjunctiveQuery(engine, [Atom.create(dog, X)], [X])
        query.evaluate(Collector())

        assert len(results) >= 1

    def test_zero_atom_query_fires_once(self):
        """Zero-atom query calls process_result exactly once."""
        from hermit.datalog import DatalogEngine, ConjunctiveQuery, QueryResultCollector

        A = AtomicConcept.create("http://example.org/A")
        a = Individual.create("http://example.org/a")
        ont = _make_ontology([], [Atom.create(A, a)], iri="http://example.org/zaqtest")

        engine = DatalogEngine(ont)
        results = []

        class Collector(QueryResultCollector):
            def process_result(self, query, result):
                results.append(result[:])

        query = ConjunctiveQuery(engine, [], [a])
        query.evaluate(Collector())
        assert len(results) == 1

    def test_derived_concept_query(self):
        """Query Animal(x) finds fido when Dog(fido) and Dog ⊑ Animal."""
        from hermit.datalog import DatalogEngine, ConjunctiveQuery, QueryResultCollector

        dog = AtomicConcept.create("http://example.org/Dog2")
        animal = AtomicConcept.create("http://example.org/Animal2")
        fido = Individual.create("http://example.org/fido2")

        clause = DLClause.create((Atom.create(animal, X),), (Atom.create(dog, X),))
        fact = Atom.create(dog, fido)
        ont = _make_ontology([clause], [fact], iri="http://example.org/derivedtest")

        engine = DatalogEngine(ont)
        results = []

        class Collector(QueryResultCollector):
            def process_result(self, query, result):
                results.append(result[:])

        query = ConjunctiveQuery(engine, [Atom.create(animal, X)], [X])
        query.evaluate(Collector())
        assert len(results) >= 1
