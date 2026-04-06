"""Unit tests for the structural layer: OWLClausification and NormalizedAxioms.

These tests verify that:
- ``NormalizedAxioms`` can be built with various axiom types.
- ``OWLClausification`` produces correct DL clauses from normalized axioms.
- Expressivity detection works correctly.
"""

from __future__ import annotations

import pytest

from hermit.model import (
    Atom,
    AtomicConcept,
    AtomicNegationConcept,
    AtomicRole,
    Constant,
    DLClause,
    Equality,
    Individual,
    Inequality,
    InverseRole,
    Variable,
)
from hermit.structural import (
    ComplexObjectPropertyInclusion,
    DisjunctiveRule,
    NormalizedAxioms,
    OWLAxiomsExpressivity,
    OWLClausification,
)


def _count_clauses_with_body_length(clauses: frozenset[DLClause], length: int) -> int:
    """Count how many clauses have the given body length."""
    return sum(1 for c in clauses if c.body_length() == length)


def _find_clause_by_body_head(
    clauses: frozenset[DLClause],
    body_predicates: list,
    head_predicates: list,
) -> DLClause | None:
    """Find a clause whose body and head predicates match the given lists."""
    for c in clauses:
        body_preds = [a.predicate for a in c.body_atoms]
        head_preds = [a.predicate for a in c.head_atoms]
        if body_preds == body_predicates and head_preds == head_predicates:
            return c
    return None


# ===========================================================================
# NormalizedAxioms construction
# ===========================================================================

class TestNormalizedAxiomsConstruction:
    """Test building NormalizedAxioms with various axiom types."""

    def test_empty_axioms(self):
        """Empty NormalizedAxioms has no entities."""
        axioms = NormalizedAxioms()
        assert len(axioms.concept_inclusions) == 0
        assert len(axioms.rules) == 0
        assert len(axioms.named_individuals) == 0

    def test_concept_inclusion_added(self):
        """Concept inclusions are stored correctly."""
        axioms = NormalizedAxioms()
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        # A ⊑ B in NNF: (¬A, B)
        axioms.concept_inclusions.append((AtomicNegationConcept.create(a), b))
        assert len(axioms.concept_inclusions) == 1

    def test_positive_concept_fact(self):
        """Positive concept fact A(i) is stored."""
        axioms = NormalizedAxioms()
        a = AtomicConcept.create("http://example.org#A")
        i = Individual.create("http://example.org#john")
        axioms.positive_concept_facts.append((i, a))
        assert len(axioms.positive_concept_facts) == 1

    def test_positive_role_fact(self):
        """Positive role fact R(i, j) is stored."""
        axioms = NormalizedAxioms()
        r = AtomicRole.create("http://example.org#r")
        i = Individual.create("http://example.org#i")
        j = Individual.create("http://example.org#j")
        axioms.positive_role_facts.append((i, r, j))
        assert len(axioms.positive_role_facts) == 1


# ===========================================================================
# Clausification: concept inclusions
# ===========================================================================

class TestClausifyConceptInclusions:
    """Test clausification of concept inclusion axioms."""

    def test_simple_subsumption(self):
        """A ⊑ B clausifies to B(X) :- A(X)."""
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        axioms = NormalizedAxioms()
        axioms.concept_inclusions.append((AtomicNegationConcept.create(a), b))

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        # Should produce clause: B(X) :- A(X)
        matching = [
            c for c in ontology.dl_clauses
            if c.body_length() == 1
            and c.head_length() == 1
            and isinstance(c.body_atoms[0].predicate, AtomicConcept)
            and isinstance(c.head_atoms[0].predicate, AtomicConcept)
        ]
        assert len(matching) >= 1

    def test_disjunction_in_head(self):
        """A ⊑ B ⊔ C clausifies to B(X) ∨ C(X) :- A(X)."""
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        c = AtomicConcept.create("http://example.org#C")
        axioms = NormalizedAxioms()
        axioms.concept_inclusions.append(
            (AtomicNegationConcept.create(a), b, c)
        )

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        # Should produce clause: B(X) ∨ C(X) :- A(X)
        matching = [
            c for c in ontology.dl_clauses
            if c.body_length() == 1
            and c.head_length() == 2
            and isinstance(c.body_atoms[0].predicate, AtomicConcept)
        ]
        assert len(matching) >= 1

    def test_contradiction_axiom(self):
        """A ⊑ ⊥ clausifies to ⊥ :- A(X)."""
        a = AtomicConcept.create("http://example.org#A")
        axioms = NormalizedAxioms()
        # A ⊑ ⊥ in NNF: (¬A)  -- nothing in head
        axioms.concept_inclusions.append((AtomicNegationConcept.create(a),))

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        # Should produce empty-head clause
        empty_head = [c for c in ontology.dl_clauses if c.head_length() == 0]
        assert len(empty_head) >= 1


# ===========================================================================
# Clausification: property inclusions
# ===========================================================================

class TestClausifyPropertyInclusions:
    """Test clausification of property inclusion axioms."""

    def test_simple_object_property_inclusion(self):
        """R ⊑ S clausifies to S(X,Y) :- R(X,Y)."""
        r = AtomicRole.create("http://example.org#r")
        s = AtomicRole.create("http://example.org#s")
        axioms = NormalizedAxioms()
        axioms.simple_object_property_inclusions.append((r, s))

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        matching = [
            c for c in ontology.dl_clauses
            if c.body_length() == 1
            and c.head_length() == 1
            and isinstance(c.body_atoms[0].predicate, AtomicRole)
            and isinstance(c.head_atoms[0].predicate, AtomicRole)
        ]
        assert len(matching) >= 1

    def test_data_property_inclusion(self):
        """P ⊑ Q clausifies to Q(X,Y) :- P(X,Y)."""
        p = AtomicRole.create("http://example.org#p")
        q = AtomicRole.create("http://example.org#q")
        axioms = NormalizedAxioms()
        axioms.data_property_inclusions.append((p, q))

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        matching = [
            c for c in ontology.dl_clauses
            if c.body_length() == 1
            and c.head_length() == 1
            and isinstance(c.body_atoms[0].predicate, AtomicRole)
            and isinstance(c.head_atoms[0].predicate, AtomicRole)
        ]
        assert len(matching) >= 1


# ===========================================================================
# Clausification: property characteristics
# ===========================================================================

class TestClausifyPropertyCharacteristics:
    """Test clausification of property characteristics."""

    def test_asymmetric_property(self):
        """Asymmetric R: R(X,Y) ∧ R(Y,X) → ⊥."""
        r = AtomicRole.create("http://example.org#r")
        axioms = NormalizedAxioms()
        axioms.asymmetric_object_properties.add(r)

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        # Should produce empty-head clause with two body atoms
        empty_head_two_body = [
            c for c in ontology.dl_clauses
            if c.head_length() == 0 and c.body_length() == 2
        ]
        assert len(empty_head_two_body) >= 1

    def test_irreflexive_property(self):
        """Irreflexive R: R(X,X) → ⊥."""
        r = AtomicRole.create("http://example.org#r")
        axioms = NormalizedAxioms()
        axioms.irreflexive_object_properties.add(r)

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        # Should produce empty-head clause with one body atom
        empty_head = [c for c in ontology.dl_clauses if c.head_length() == 0]
        assert len(empty_head) >= 1

    def test_reflexive_property(self):
        """Reflexive R: ⊤ → R(X,X)."""
        r = AtomicRole.create("http://example.org#r")
        axioms = NormalizedAxioms()
        axioms.reflexive_object_properties.add(r)

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        # Should produce clause with Thing(X) in body and R(X,X) in head
        reflexive_clauses = [
            c for c in ontology.dl_clauses
            if c.head_length() == 1
            and c.body_length() == 1
            and isinstance(c.head_atoms[0].predicate, AtomicRole)
        ]
        assert len(reflexive_clauses) >= 1

    def test_disjoint_object_properties(self):
        """Disjoint R, S: R(X,Y) ∧ S(X,Y) → ⊥."""
        r = AtomicRole.create("http://example.org#r")
        s = AtomicRole.create("http://example.org#s")
        axioms = NormalizedAxioms()
        axioms.disjoint_object_properties.append((r, s))

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        # Should produce empty-head clause with two body atoms
        empty_head = [c for c in ontology.dl_clauses if c.head_length() == 0]
        assert len(empty_head) >= 1


# ===========================================================================
# Clausification: ABox facts
# ===========================================================================

class TestClausifyFacts:
    """Test clausification of ABox facts."""

    def test_positive_concept_fact(self):
        """A(i) becomes a positive fact atom."""
        a = AtomicConcept.create("http://example.org#A")
        i = Individual.create("http://example.org#john")
        axioms = NormalizedAxioms()
        axioms.positive_concept_facts.append((i, a))

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        assert Atom.create(a, i) in ontology.positive_facts

    def test_negative_concept_fact(self):
        """¬A(i) becomes a negative fact atom."""
        a = AtomicConcept.create("http://example.org#A")
        i = Individual.create("http://example.org#john")
        axioms = NormalizedAxioms()
        axioms.negative_concept_facts.append((i, a))

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        assert Atom.create(a, i) in ontology.negative_facts

    def test_role_fact(self):
        """R(i, j) becomes a positive role fact."""
        r = AtomicRole.create("http://example.org#r")
        i = Individual.create("http://example.org#i")
        j = Individual.create("http://example.org#j")
        axioms = NormalizedAxioms()
        axioms.positive_role_facts.append((i, r, j))

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        assert Atom.create(r, i, j) in ontology.positive_facts

    def test_same_individual_fact(self):
        """i == j becomes an equality fact."""
        i = Individual.create("http://example.org#i")
        j = Individual.create("http://example.org#j")
        axioms = NormalizedAxioms()
        axioms.same_individual_facts.append((i, j))

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        assert Atom.create(Equality.INSTANCE, i, j) in ontology.positive_facts

    def test_different_individuals_fact(self):
        """i != j becomes an inequality fact."""
        i = Individual.create("http://example.org#i")
        j = Individual.create("http://example.org#j")
        axioms = NormalizedAxioms()
        axioms.different_individuals_facts.append((i, j))

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        assert Atom.create(Inequality.INSTANCE, i, j) in ontology.positive_facts


# ===========================================================================
# Clausification: SWRL-like rules
# ===========================================================================

class TestClausifyRules:
    """Test clausification of disjunctive rules."""

    def test_simple_rule(self):
        """Rule: A(X) ∧ B(X) → C(X) produces a DL clause."""
        X = Variable.create("X")
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        c = AtomicConcept.create("http://example.org#C")

        rule = DisjunctiveRule(
            body=(Atom.create(a, X), Atom.create(b, X)),
            head=(Atom.create(c, X),),
        )
        axioms = NormalizedAxioms()
        axioms.rules.append(rule)

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        # Should produce a clause
        assert len(ontology.dl_clauses) >= 1

    def test_rule_with_role_body(self):
        """Rule: Person(X) ∧ hasParent(X,Y) → hasRelative(X,Y)."""
        X = Variable.create("X")
        Y = Variable.create("Y")
        person = AtomicConcept.create("http://example.org#Person")
        has_parent = AtomicRole.create("http://example.org#hasParent")
        has_relative = AtomicRole.create("http://example.org#hasRelative")

        rule = DisjunctiveRule(
            body=(
                Atom.create(person, X),
                Atom.create(has_parent, X, Y),
            ),
            head=(Atom.create(has_relative, X, Y),),
        )
        axioms = NormalizedAxioms()
        axioms.object_roles_in_owl_axioms.add(has_parent)
        axioms.rules.append(rule)

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        assert len(ontology.dl_clauses) >= 1


# ===========================================================================
# Expressivity detection
# ===========================================================================

class TestExpressivityDetection:
    """Test OWLAxiomsExpressivity with various axiom sets."""

    def test_no_expressivity_flags_for_simple_taxonomy(self):
        """Simple taxonomy has no special expressivity features."""
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        axioms = NormalizedAxioms()
        axioms.concept_inclusions.append((AtomicNegationConcept.create(a), b))

        exp = OWLAxiomsExpressivity(axioms)
        assert not exp.has_inverse_roles
        assert not exp.has_at_most_restrictions
        assert not exp.has_nominals
        assert not exp.has_datatypes
        assert not exp.has_swrl_rules

    def test_inverse_roles_detected(self):
        """Inverse roles in axioms are detected."""
        r = AtomicRole.create("http://example.org#r")
        inv_r = InverseRole.create(r)
        s = AtomicRole.create("http://example.org#s")
        axioms = NormalizedAxioms()
        axioms.simple_object_property_inclusions.append((inv_r, s))
        axioms.complex_object_roles.add(inv_r)

        exp = OWLAxiomsExpressivity(axioms)
        assert exp.has_inverse_roles

    def test_swrl_rules_detected(self):
        """Presence of SWRL rules is detected."""
        X = Variable.create("X")
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        rule = DisjunctiveRule(
            body=(Atom.create(a, X),),
            head=(Atom.create(b, X),),
        )
        axioms = NormalizedAxioms()
        axioms.rules.append(rule)

        exp = OWLAxiomsExpressivity(axioms)
        assert exp.has_swrl_rules

    def test_datatypes_detected_from_data_facts(self):
        """Data property facts trigger datatype detection."""
        p = AtomicRole.create("http://example.org#p")
        i = Individual.create("http://example.org#i")
        v = Constant.create("42", "http://www.w3.org/2001/XMLSchema#integer")
        axioms = NormalizedAxioms()
        axioms.positive_data_facts.append((i, p, v))

        exp = OWLAxiomsExpressivity(axioms)
        assert exp.has_datatypes


# ===========================================================================
# Clausification: full pipeline
# ===========================================================================

class TestFullClausificationPipeline:
    """Test the complete normalization → clausification → DLOntology pipeline."""

    def test_combined_axioms(self):
        """Clausify a mix of TBox, ABox, and property axioms together."""
        X = Variable.create("X")
        Y = Variable.create("Y")

        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        r = AtomicRole.create("http://example.org#r")
        s = AtomicRole.create("http://example.org#s")
        i = Individual.create("http://example.org#john")

        axioms = NormalizedAxioms()
        # TBox: A ⊑ B
        axioms.concept_inclusions.append((AtomicNegationConcept.create(a), b))
        # Property: r ⊑ s
        axioms.simple_object_property_inclusions.append((r, s))
        # ABox: A(john)
        axioms.positive_concept_facts.append((i, a))
        # ABox: r(john, john)
        axioms.positive_role_facts.append((i, r, i))

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        assert len(ontology.dl_clauses) > 0
        assert len(ontology.positive_facts) > 0
        assert ontology.ontology_iri is not None

    def test_ontology_is_horn(self):
        """Horn ontology (at most one positive literal per clause)."""
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        axioms = NormalizedAxioms()
        axioms.concept_inclusions.append((AtomicNegationConcept.create(a), b))

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        assert ontology.is_horn()

    def test_ontology_not_horn_with_disjunction(self):
        """Non-Horn ontology (disjunction in head)."""
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        c = AtomicConcept.create("http://example.org#C")
        axioms = NormalizedAxioms()
        # A ⊑ B ⊔ C  =>  ¬A ⊔ B ⊔ C
        axioms.concept_inclusions.append(
            (AtomicNegationConcept.create(a), b, c)
        )

        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms)

        # The clause will have head_length > 1, so not Horn
        non_horn = [c for c in ontology.dl_clauses if c.head_length() > 1]
        assert len(non_horn) >= 1


# ===========================================================================
# Clausification: description graphs
# ===========================================================================

class TestClausifyDescriptionGraphs:
    """Test clausification with description graphs."""

    def test_description_graph_produces_clauses(self):
        """Description graphs produce start DL clauses."""
        from hermit.model import (
            DescriptionGraph,
            DescriptionGraphEdge,
            ExistsDescriptionGraph,
        )

        v0 = AtomicConcept.create("http://example.org#V0")
        v1 = AtomicConcept.create("http://example.org#V1")
        r = AtomicRole.create("http://example.org#r")

        edge = DescriptionGraphEdge(r, 0, 1)
        dg = DescriptionGraph(
            name="http://example.org#MyGraph",
            concepts_by_vertex=(v0, v1),
            edges=(edge,),
            start_concepts=frozenset({v0}),
        )

        axioms = NormalizedAxioms()
        clausifier = OWLClausification()
        ontology = clausifier.clausify(axioms, description_graphs=[dg])

        # Should produce description graph start clauses
        graph_clauses = [
            c for c in ontology.dl_clauses
            if any(
                isinstance(a.predicate, ExistsDescriptionGraph)
                for a in c.head_atoms
            )
        ]
        assert len(graph_clauses) >= 1
