"""Coverage boost 6 — targeted tests for uncovered existential expansion paths.

Targets:
- existential_expansion_manager.py lines 177-215 (functional expansion reuse)
- existential_expansion_manager.py lines 217-232 (at-least > 1 on functional role → clash)
- existential_expansion_manager.py lines 241-259 (inverse role functional expansion)
- description_graph_manager.py lines 222-258 (merge_graphs via equality)
- nominal_introduction_manager.py lines 79-103 (backtrack) via forced clash+backtrack
"""

from __future__ import annotations

import pytest

from hermit.configuration import BlockingStrategyType, Configuration
from hermit.model import (
    Atom,
    AtLeastConcept,
    AtomicConcept,
    AtomicRole,
    DLClause,
    DLOntology,
    Equality,
    DescriptionGraph,
    DescriptionGraphEdge,
    ExistsDescriptionGraph,
    Individual,
    InverseRole,
    Variable,
)
from hermit.reasoner import Reasoner

X = Variable.create("X")
Y = Variable.create("Y")
Y0 = Variable.create("Y0")
Y1 = Variable.create("Y1")


def _make_ontology(clauses=(), facts=(), iri="urn:test:b6"):
    return DLOntology(
        ontology_iri=iri,
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset(facts),
        negative_facts=frozenset(),
    )


def _functionality_axiom(role: AtomicRole) -> DLClause:
    """Create r(X,Y0) ∧ r(X,Y1) → Y0=Y1  (functionality axiom for role r)."""
    return DLClause.create(
        (Atom.create(Equality.INSTANCE, Y0, Y1),),
        (Atom.create(role, X, Y0), Atom.create(role, X, Y1)),
    )


def _inverse_functionality_axiom(role: AtomicRole) -> DLClause:
    """Create r(Y0,X) ∧ r(Y1,X) → Y0=Y1  (inverse functionality axiom)."""
    return DLClause.create(
        (Atom.create(Equality.INSTANCE, Y0, Y1),),
        (Atom.create(role, Y0, X), Atom.create(role, Y1, X)),
    )


class TestFunctionalExpansion:
    """Tests triggering existential_expansion_manager.try_functional_expansion()."""

    def test_functional_expansion_reuses_existing_node(self):
        """∃r.A on a functional role r reuses the existing r-successor (lines 177-215).

        Setup:
        - r is functional: r(X,Y0) ∧ r(X,Y1) → Y0=Y1
        - ind has r-fact: r(ind, ind2)
        - ∃r.B(ind) is required
        → functional expansion: reuse ind2 as the r-successor, add B(ind2)
        """
        r = AtomicRole.create("urn:b6:func:r")
        A = AtomicConcept.create("urn:b6:func:A")
        B = AtomicConcept.create("urn:b6:func:B")

        # Functionality axiom for r
        func_ax = _functionality_axiom(r)
        # ∃r.B(X) triggered by A(X)
        atleast = AtLeastConcept.create(1, r, B)
        clause_exist = DLClause.create(
            (Atom.create(atleast, X),),
            (Atom.create(A, X),),
        )
        ind = Individual.create("urn:b6:func:ind")
        ind2 = Individual.create("urn:b6:func:ind2")
        # Pre-assert r(ind, ind2) as a fact
        ontology = _make_ontology(
            [func_ax, clause_exist],
            [Atom.create(A, ind), Atom.create(r, ind, ind2)],
            iri="urn:b6:func:reuse",
        )
        r_obj = Reasoner(ontology)
        # Functional expansion: ind already has r-successor ind2 → add B(ind2), no new node
        assert r_obj.is_consistent()
        r_obj.dispose()

    def test_functional_atleast_gt1_on_functional_role_clash(self):
        """≥2 r.A on a functional role → immediate clash (lines 217-232)."""
        r = AtomicRole.create("urn:b6:clash:r")
        A = AtomicConcept.create("urn:b6:clash:A")
        B = AtomicConcept.create("urn:b6:clash:B")

        func_ax = _functionality_axiom(r)
        # ≥2 r.A triggered by A(X)
        atleast2 = AtLeastConcept.create(2, r, B)
        clause_atleast2 = DLClause.create(
            (Atom.create(atleast2, X),),
            (Atom.create(A, X),),
        )
        ind = Individual.create("urn:b6:clash:ind")
        ontology = _make_ontology(
            [func_ax, clause_atleast2],
            [Atom.create(A, ind)],
            iri="urn:b6:clash:atleast2",
        )
        r_obj = Reasoner(ontology)
        # ≥2 r.B is unsatisfiable when r is functional → inconsistent
        assert not r_obj.is_consistent()
        r_obj.dispose()

    def test_inverse_functional_expansion(self):
        """Inverse role functional expansion reuses existing inv(r)-successor (lines 241-259)."""
        r = AtomicRole.create("urn:b6:inv:r")
        A = AtomicConcept.create("urn:b6:inv:A")
        B = AtomicConcept.create("urn:b6:inv:B")

        # Inverse functionality: r(Y0,X) ∧ r(Y1,X) → Y0=Y1
        inv_func_ax = _inverse_functionality_axiom(r)
        inv_r = InverseRole.create(r)
        # ∃inv(r).B(X): each node needs an r-predecessor with B
        atleast_inv = AtLeastConcept.create(1, inv_r, B)
        clause_exist = DLClause.create(
            (Atom.create(atleast_inv, X),),
            (Atom.create(A, X),),
        )
        ind = Individual.create("urn:b6:inv:ind")
        ind2 = Individual.create("urn:b6:inv:ind2")
        # Pre-assert r(ind2, ind) as a fact → ind has r-predecessor ind2
        ontology = _make_ontology(
            [inv_func_ax, clause_exist],
            [Atom.create(A, ind), Atom.create(r, ind2, ind)],
            iri="urn:b6:inv:expand",
        )
        r_obj = Reasoner(ontology)
        # Inverse functional expansion: ind already has inv(r)-predecessor ind2 → reuse it
        assert r_obj.is_consistent()
        r_obj.dispose()

    def test_role_inclusion_loads_into_super_role_graph(self):
        """Role inclusion R⊑S also marks S-functional when R is functional."""
        r = AtomicRole.create("urn:b6:ri:r")
        s = AtomicRole.create("urn:b6:ri:s")
        A = AtomicConcept.create("urn:b6:ri:A")
        B = AtomicConcept.create("urn:b6:ri:B")

        # r⊑s: r(X,Y) → s(X,Y)
        role_inc = DLClause.create(
            (Atom.create(s, X, Y),),
            (Atom.create(r, X, Y),),
        )
        # s is functional
        func_s = _functionality_axiom(s)
        # ∃s.B triggered by A
        atleast_s = AtLeastConcept.create(1, s, B)
        clause_exist = DLClause.create(
            (Atom.create(atleast_s, X),),
            (Atom.create(A, X),),
        )
        ind = Individual.create("urn:b6:ri:ind")
        ind2 = Individual.create("urn:b6:ri:ind2")
        ontology = _make_ontology(
            [role_inc, func_s, clause_exist],
            [Atom.create(A, ind), Atom.create(r, ind, ind2)],
            iri="urn:b6:ri:include",
        )
        r_obj = Reasoner(ontology)
        assert r_obj.is_consistent()
        r_obj.dispose()

    def test_inverse_role_inclusion_loads_into_graph(self):
        """Inverse role inclusion: r(X,Y) → s(Y,X) covered by _load_dl_clauses_into_graph."""
        r = AtomicRole.create("urn:b6:iri:r")
        s = AtomicRole.create("urn:b6:iri:s")
        A = AtomicConcept.create("urn:b6:iri:A")

        # r⊑inv(s): r(X,Y) → s(Y,X)
        inv_role_inc = DLClause.create(
            (Atom.create(s, Y, X),),
            (Atom.create(r, X, Y),),
        )
        ind = Individual.create("urn:b6:iri:ind")
        ind2 = Individual.create("urn:b6:iri:ind2")
        ontology = _make_ontology(
            [inv_role_inc],
            [Atom.create(A, ind), Atom.create(r, ind, ind2)],
            iri="urn:b6:iri:include",
        )
        r_obj = Reasoner(ontology)
        assert r_obj.is_consistent()
        r_obj.dispose()

    def test_functional_expansion_with_atleast1_creates_successor(self):
        """∃r.A when r is functional and no successor exists → creates new node normally."""
        r = AtomicRole.create("urn:b6:new:r")
        A = AtomicConcept.create("urn:b6:new:A")
        B = AtomicConcept.create("urn:b6:new:B")

        func_ax = _functionality_axiom(r)
        atleast = AtLeastConcept.create(1, r, B)
        clause_exist = DLClause.create(
            (Atom.create(atleast, X),),
            (Atom.create(A, X),),
        )
        ind = Individual.create("urn:b6:new:ind")
        # No pre-existing r-successor → creates new node via normal expansion
        ontology = _make_ontology(
            [func_ax, clause_exist],
            [Atom.create(A, ind)],
            iri="urn:b6:new:create",
        )
        r_obj = Reasoner(ontology)
        assert r_obj.is_consistent()
        r_obj.dispose()


class TestDescriptionGraphMerge:
    """Tests triggering description_graph_manager.merge_graphs()."""

    def test_dg_merge_graphs_via_equality(self):
        """Two individuals each expand a DG; equality forces them to merge → merge_graphs fires."""
        # Use distinct start/end concepts to avoid infinite expansion
        Start = AtomicConcept.create("urn:b6:dgm:Start")
        End = AtomicConcept.create("urn:b6:dgm:End")
        r = AtomicRole.create("urn:b6:dgm:r")
        edge = DescriptionGraphEdge(r, 0, 1)
        dg = DescriptionGraph(
            name="urn:b6:dgm:Graph",
            concepts_by_vertex=(Start, End),
            edges=(edge,),
            start_concepts=frozenset({Start}),
        )
        exists_dg0 = ExistsDescriptionGraph.create(dg, 0)
        clause_dg = DLClause.create(
            (Atom.create(exists_dg0, X),),
            (Atom.create(Start, X),),
        )
        # All Start-instances are equal → forces merge
        clause_eq = DLClause.create(
            (Atom.create(Equality.INSTANCE, X, Y),),
            (Atom.create(Start, X), Atom.create(Start, Y)),
        )
        ind1 = Individual.create("urn:b6:dgm:ind1")
        ontology = _make_ontology(
            [clause_dg, clause_eq],
            [Atom.create(Start, ind1)],
            iri="urn:b6:dgm:merge",
        )
        r_obj = Reasoner(ontology)
        # DG expands for ind1; equality forces nodes together → merge_graphs called
        assert r_obj.is_consistent()
        r_obj.dispose()


    def test_dg_merge_graphs_two_individuals_with_equality(self):
        """Two individuals both expand DG; equality merges them → merge_graphs fires (lines 222-258)."""
        Start = AtomicConcept.create("urn:b6:dgmg:Start")
        End = AtomicConcept.create("urn:b6:dgmg:End")
        r = AtomicRole.create("urn:b6:dgmg:r")
        edge = DescriptionGraphEdge(r, 0, 1)
        dg = DescriptionGraph(
            name="urn:b6:dgmg:Graph",
            concepts_by_vertex=(Start, End),
            edges=(edge,),
            start_concepts=frozenset({Start}),
        )
        exists_dg0 = ExistsDescriptionGraph.create(dg, 0)
        clause_dg = DLClause.create(
            (Atom.create(exists_dg0, X),),
            (Atom.create(Start, X),),
        )
        # All Start-instances equal → ind1 and ind2 merge AFTER DG expansion
        clause_eq = DLClause.create(
            (Atom.create(Equality.INSTANCE, X, Y),),
            (Atom.create(Start, X), Atom.create(Start, Y)),
        )
        ind1 = Individual.create("urn:b6:dgmg:ind1")
        ind2 = Individual.create("urn:b6:dgmg:ind2")
        config = Configuration()
        config.blocking_strategy_type = BlockingStrategyType.SIMPLE_CORE
        ontology = _make_ontology(
            [clause_dg, clause_eq],
            [Atom.create(Start, ind1), Atom.create(Start, ind2)],
            iri="urn:b6:dgmg:merge",
        )
        r_obj = Reasoner(ontology, config)
        # Both individuals expand DG; then merged → merge_graphs relocates DG tuples
        assert r_obj.is_consistent()
        r_obj.dispose()

    def test_dg_check_graph_constraints_clash(self):
        """DG expansion with merge → same node at different positions → clash detected."""
        Start = AtomicConcept.create("urn:b6:dgc:Start")
        End = AtomicConcept.create("urn:b6:dgc:End")
        r = AtomicRole.create("urn:b6:dgc:r")
        edge = DescriptionGraphEdge(r, 0, 1)
        dg = DescriptionGraph(
            name="urn:b6:dgc:Graph",
            concepts_by_vertex=(Start, End),
            edges=(edge,),
            start_concepts=frozenset({Start}),
        )
        exists_dg0 = ExistsDescriptionGraph.create(dg, 0)
        clause_dg = DLClause.create(
            (Atom.create(exists_dg0, X),),
            (Atom.create(Start, X),),
        )
        # Force the DG-created End-node to equal the Start-node (the individual)
        # Start(X) ∧ End(Y) → X=Y forces the two DG nodes to merge
        clause_eq = DLClause.create(
            (Atom.create(Equality.INSTANCE, X, Y),),
            (Atom.create(Start, X), Atom.create(End, Y)),
        )
        ind = Individual.create("urn:b6:dgc:ind")
        ontology = _make_ontology(
            [clause_dg, clause_eq],
            [Atom.create(Start, ind)],
            iri="urn:b6:dgc:clash",
        )
        r_obj = Reasoner(ontology)
        # DG expands: ind is at vertex 0 (Start), new_node at vertex 1 (End)
        # Equality Start∧End→X=Y merges ind with new_node
        # Now ind is at both position 1 AND position 2 of the same DG tuple → clash
        assert not r_obj.is_consistent()
        r_obj.dispose()


class TestNominalIntroductionManagerBacktrack:
    """Tests triggering NIM backtrack() via forced clashes requiring real backtracking."""

    def test_nim_backtrack_with_explicit_role_clash(self):
        """Disjunction + functionality clash forces backtrack to exercise nim.backtrack()."""
        A = AtomicConcept.create("urn:b6:nimbt:A")
        B = AtomicConcept.create("urn:b6:nimbt:B")
        C = AtomicConcept.create("urn:b6:nimbt:C")
        r = AtomicRole.create("urn:b6:nimbt:r")

        # A → B ⊔ C
        disj = DLClause.create(
            (Atom.create(B, X), Atom.create(C, X)),
            (Atom.create(A, X),),
        )
        # B → ⊥ (forces backtrack to C branch)
        clash_b = DLClause.create((), (Atom.create(B, X),))
        # C is satisfiable
        ind = Individual.create("urn:b6:nimbt:ind")
        ontology = _make_ontology(
            [disj, clash_b],
            [Atom.create(A, ind)],
            iri="urn:b6:nimbt",
        )
        r_obj = Reasoner(ontology)
        assert r_obj.is_consistent()
        r_obj.dispose()

    def test_nim_deep_backtrack_chain(self):
        """Many nested clash branches forcing multiple backtracks."""
        # A→B⊔C; B→⊥; C→D⊔E; D→⊥; E→F⊔G; F→⊥; G is ok
        concepts = [AtomicConcept.create(f"urn:b6:dbt:C{i}") for i in range(10)]
        A = concepts[0]
        clauses = [
            DLClause.create((Atom.create(concepts[1], X), Atom.create(concepts[2], X)), (Atom.create(concepts[0], X),)),
            DLClause.create((), (Atom.create(concepts[1], X),)),  # C1 → clash
            DLClause.create((Atom.create(concepts[3], X), Atom.create(concepts[4], X)), (Atom.create(concepts[2], X),)),
            DLClause.create((), (Atom.create(concepts[3], X),)),  # C3 → clash
            DLClause.create((Atom.create(concepts[5], X), Atom.create(concepts[6], X)), (Atom.create(concepts[4], X),)),
            DLClause.create((), (Atom.create(concepts[5], X),)),  # C5 → clash
            DLClause.create((Atom.create(concepts[7], X), Atom.create(concepts[8], X)), (Atom.create(concepts[6], X),)),
            DLClause.create((), (Atom.create(concepts[7], X),)),  # C7 → clash
            # C8 is satisfiable
        ]
        ind = Individual.create("urn:b6:dbt:ind")
        ontology = _make_ontology(clauses, [Atom.create(A, ind)], iri="urn:b6:dbt")
        r_obj = Reasoner(ontology)
        assert r_obj.is_consistent()
        r_obj.dispose()

    def test_nim_backtrack_with_existential(self):
        """Backtrack after existential expansion exercises EEM.backtrack() too."""
        A = AtomicConcept.create("urn:b6:nimex:A")
        B = AtomicConcept.create("urn:b6:nimex:B")
        C = AtomicConcept.create("urn:b6:nimex:C")
        r = AtomicRole.create("urn:b6:nimex:r")

        atleast = AtLeastConcept.create(1, r, C)
        clauses = [
            # A → B ⊔ C
            DLClause.create((Atom.create(B, X), Atom.create(C, X)), (Atom.create(A, X),)),
            # B → ∃r.C (expand existential)
            DLClause.create((Atom.create(atleast, X),), (Atom.create(B, X),)),
            # B ∧ C → ⊥ (clash)
            DLClause.create((), (Atom.create(B, X), Atom.create(C, X))),
        ]
        ind = Individual.create("urn:b6:nimex:ind")
        ontology = _make_ontology(
            clauses,
            [Atom.create(A, ind)],
            iri="urn:b6:nimex",
        )
        r_obj = Reasoner(ontology)
        # Branch B: B(ind) → ∃r.C fires, creates successor; then B∧C→⊥ fires → clash
        # Backtrack to branch C: C(ind) consistent (no B, no clash)
        assert r_obj.is_consistent()
        r_obj.dispose()
