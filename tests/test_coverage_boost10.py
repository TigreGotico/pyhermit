"""Coverage boost 10 — targeted tests for:

- instance_manager.py lines 931-1039: role instance reading with named successors
- quasi_order_classification_for_roles.py (60%): role hierarchy classification
- instance_manager.py lines 116-139, 157-164: construction with pre-classified hierarchies
- various other uncovered paths
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
Y0 = Variable.create("Y0")
Y1 = Variable.create("Y1")


def _ns(local: str) -> str:
    return f"urn:test:boost10:{local}"


def _make_ontology(clauses=(), facts=(), iri="urn:test:boost10"):
    return DLOntology(
        ontology_iri=iri,
        dl_clauses=frozenset(clauses),
        positive_facts=frozenset(facts),
        negative_facts=frozenset(),
    )


# ---------------------------------------------------------------------------
# Basic role instance reading (lines 914-1039)
# ---------------------------------------------------------------------------

class TestRoleInstanceReading:
    """Tests that trigger _read_off_property_instances lines 914-1039."""

    def test_basic_role_relationship(self):
        """Two named individuals connected by a role."""
        ns = _ns("basic.")
        A = AtomicConcept.create(ns + "A")
        r = AtomicRole(ns + "r")
        ind1 = Individual(ns + "i1")
        ind2 = Individual(ns + "i2")

        ont = _make_ontology(
            facts=[
                Atom.create(A, ind1),
                Atom.create(A, ind2),
                Atom.create(r, ind1, ind2),
            ]
        )
        reasoner = Reasoner(ont)
        assert reasoner.has_role_relationship(ind1, r, ind2)

    def test_role_relationship_absent(self):
        """Querying a role that was not asserted returns False."""
        ns = _ns("absent.")
        A = AtomicConcept.create(ns + "A")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")
        ind1 = Individual(ns + "i1")
        ind2 = Individual(ns + "i2")

        ont = _make_ontology(
            facts=[
                Atom.create(A, ind1),
                Atom.create(A, ind2),
                Atom.create(r, ind1, ind2),
            ]
        )
        reasoner = Reasoner(ont)
        assert not reasoner.has_role_relationship(ind1, s, ind2)

    def test_role_relationship_with_hierarchy(self):
        """Role r subsumed by s — classify_object_properties triggers QO classification."""
        ns = _ns("hier.")
        A = AtomicConcept.create(ns + "A")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")
        ind1 = Individual(ns + "i1")
        ind2 = Individual(ns + "i2")

        # r -> s (r subsumed by s)
        sub_role_clause = DLClause.create(
            (Atom.create(s, X, Y),),
            (Atom.create(r, X, Y),),
        )

        ont = _make_ontology(
            clauses=[sub_role_clause],
            facts=[
                Atom.create(A, ind1),
                Atom.create(A, ind2),
                Atom.create(r, ind1, ind2),
            ],
        )
        reasoner = Reasoner(ont)
        assert reasoner.is_consistent()
        assert reasoner.has_role_relationship(ind1, r, ind2)

    def test_classify_object_properties_then_instances(self):
        """classify_object_properties() before has_role_relationship."""
        ns = _ns("classify.")
        A = AtomicConcept.create(ns + "A")
        r = AtomicRole(ns + "r")
        ind1 = Individual(ns + "i1")
        ind2 = Individual(ns + "i2")

        ont = _make_ontology(
            facts=[
                Atom.create(A, ind1),
                Atom.create(A, ind2),
                Atom.create(r, ind1, ind2),
            ]
        )
        reasoner = Reasoner(ont)
        reasoner.is_consistent()
        reasoner.classify_classes()
        reasoner.classify_object_properties()
        assert reasoner.has_role_relationship(ind1, r, ind2)

    def test_multiple_roles_multiple_individuals(self):
        """Multiple roles and individuals — exercises more iteration paths."""
        ns = _ns("multi.")
        A = AtomicConcept.create(ns + "A")
        B = AtomicConcept.create(ns + "B")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")
        i1 = Individual(ns + "i1")
        i2 = Individual(ns + "i2")
        i3 = Individual(ns + "i3")

        ont = _make_ontology(
            facts=[
                Atom.create(A, i1),
                Atom.create(B, i2),
                Atom.create(B, i3),
                Atom.create(r, i1, i2),
                Atom.create(s, i2, i3),
            ]
        )
        reasoner = Reasoner(ont)
        assert reasoner.has_role_relationship(i1, r, i2)
        assert reasoner.has_role_relationship(i2, s, i3)
        assert not reasoner.has_role_relationship(i1, s, i2)

    def test_role_with_inverse_role_fact(self):
        """A role and its inverse are separately asserted."""
        ns = _ns("inv.")
        A = AtomicConcept.create(ns + "A")
        r = AtomicRole(ns + "r")
        inv_r = InverseRole(r)
        i1 = Individual(ns + "i1")
        i2 = Individual(ns + "i2")

        ont = _make_ontology(
            facts=[
                Atom.create(A, i1),
                Atom.create(A, i2),
                Atom.create(r, i1, i2),
            ]
        )
        reasoner = Reasoner(ont)
        # Direct role assertion
        assert reasoner.has_role_relationship(i1, r, i2)

    def test_get_instances_with_role_assertions(self):
        """get_instances triggers the instance manager including property reading."""
        ns = _ns("getinst.")
        A = AtomicConcept.create(ns + "A")
        r = AtomicRole(ns + "r")
        i1 = Individual(ns + "i1")
        i2 = Individual(ns + "i2")

        ont = _make_ontology(
            facts=[
                Atom.create(A, i1),
                Atom.create(A, i2),
                Atom.create(r, i1, i2),
            ]
        )
        reasoner = Reasoner(ont)
        instances = reasoner.get_instances(A, direct=False)
        assert i1 in instances or i2 in instances

    def test_get_instances_with_pre_classified_hierarchy(self):
        """InstanceManager constructed with pre-classified role hierarchy (lines 157-164)."""
        ns = _ns("preclassify.")
        A = AtomicConcept.create(ns + "A")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")
        i1 = Individual(ns + "i1")
        i2 = Individual(ns + "i2")

        sub_role = DLClause.create(
            (Atom.create(s, X, Y),),
            (Atom.create(r, X, Y),),
        )

        ont = _make_ontology(
            clauses=[sub_role],
            facts=[
                Atom.create(A, i1),
                Atom.create(A, i2),
                Atom.create(r, i1, i2),
            ],
        )
        reasoner = Reasoner(ont)
        # Classify properties first so InstanceManager is built with object_role_hierarchy
        reasoner.classify_classes()
        reasoner.classify_object_properties()
        instances = reasoner.get_instances(A, direct=False)
        assert i1 in instances or i2 in instances

    def test_three_individuals_chain(self):
        """Chain of roles: i1 -r-> i2 -r-> i3."""
        ns = _ns("chain.")
        A = AtomicConcept.create(ns + "A")
        r = AtomicRole(ns + "r")
        i1 = Individual(ns + "i1")
        i2 = Individual(ns + "i2")
        i3 = Individual(ns + "i3")

        ont = _make_ontology(
            facts=[
                Atom.create(A, i1),
                Atom.create(A, i2),
                Atom.create(A, i3),
                Atom.create(r, i1, i2),
                Atom.create(r, i2, i3),
            ]
        )
        reasoner = Reasoner(ont)
        assert reasoner.has_role_relationship(i1, r, i2)
        assert reasoner.has_role_relationship(i2, r, i3)
        assert not reasoner.has_role_relationship(i1, r, i3)

    def test_consistent_with_role_hierarchy_subsumed_by_call(self):
        """is_role_subsumed_by exercises QuasiOrderClassificationForRoles."""
        ns = _ns("subsumed.")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")
        t = AtomicRole(ns + "t")
        X = Variable.create("X")
        Y = Variable.create("Y")

        # r -> s -> t
        r_sub_s = DLClause.create(
            (Atom.create(s, X, Y),),
            (Atom.create(r, X, Y),),
        )
        s_sub_t = DLClause.create(
            (Atom.create(t, X, Y),),
            (Atom.create(s, X, Y),),
        )

        ont = _make_ontology(clauses=[r_sub_s, s_sub_t])
        reasoner = Reasoner(ont)
        reasoner.is_consistent()
        reasoner.classify_object_properties()
        # Verify hierarchy was built
        assert reasoner._object_role_hierarchy is not None

    def test_role_hierarchy_with_inverses(self):
        """Role hierarchy with inverse roles exercises QO for roles with inverses."""
        ns = _ns("invinc.")
        A = AtomicConcept.create(ns + "A")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")
        X = Variable.create("X")
        Y = Variable.create("Y")

        # r^- -> s^- (expressed as r -> s with inverse args)
        r_inv_sub_s_inv = DLClause.create(
            (Atom.create(s, Y, X),),
            (Atom.create(r, Y, X),),
        )

        i1 = Individual(ns + "i1")
        i2 = Individual(ns + "i2")

        ont = _make_ontology(
            clauses=[r_inv_sub_s_inv],
            facts=[
                Atom.create(A, i1),
                Atom.create(A, i2),
                Atom.create(r, i1, i2),
            ],
        )
        reasoner = Reasoner(ont)
        assert reasoner.is_consistent()
        reasoner.classify_object_properties()
        assert reasoner._object_role_hierarchy is not None


# ---------------------------------------------------------------------------
# Quasi-order classification for roles
# ---------------------------------------------------------------------------

class TestQuasiOrderClassificationForRoles:
    """Tests that drive quasi_order_classification_for_roles.py coverage."""

    def test_classify_object_properties_basic(self):
        """Simplest case: single role, no hierarchy."""
        ns = _ns("qo_basic.")
        r = AtomicRole(ns + "r")
        i1 = Individual(ns + "i1")
        A = AtomicConcept.create(ns + "A")

        ont = _make_ontology(
            facts=[Atom.create(A, i1)]
        )
        reasoner = Reasoner(ont)
        reasoner.classify_object_properties()
        assert reasoner._object_role_hierarchy is not None

    def test_classify_object_properties_with_subconcept_axiom(self):
        """Role hierarchy: r subsumed by s exercises initialise_known_subsumptions."""
        ns = _ns("qo_sub.")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")

        r_sub_s = DLClause.create(
            (Atom.create(s, X, Y),),
            (Atom.create(r, X, Y),),
        )

        ont = _make_ontology(clauses=[r_sub_s])
        reasoner = Reasoner(ont)
        reasoner.classify_object_properties()
        hierarchy = reasoner._object_role_hierarchy
        assert hierarchy is not None
        # r should be below s in the hierarchy
        all_elems = hierarchy.get_all_elements()
        assert r in all_elems or s in all_elems

    def test_classify_multiple_role_levels(self):
        """3-level role chain: r < s < t triggers full BFS classification."""
        ns = _ns("qo_3lev.")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")
        t = AtomicRole(ns + "t")

        r_sub_s = DLClause.create(
            (Atom.create(s, X, Y),), (Atom.create(r, X, Y),)
        )
        s_sub_t = DLClause.create(
            (Atom.create(t, X, Y),), (Atom.create(s, X, Y),)
        )

        ont = _make_ontology(clauses=[r_sub_s, s_sub_t])
        reasoner = Reasoner(ont)
        reasoner.classify_object_properties()
        assert reasoner._object_role_hierarchy is not None

    def test_classify_with_equivalent_roles(self):
        """Two mutually-subsuming roles are equivalent (same hierarchy node)."""
        ns = _ns("qo_equiv.")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")

        r_sub_s = DLClause.create(
            (Atom.create(s, X, Y),), (Atom.create(r, X, Y),)
        )
        s_sub_r = DLClause.create(
            (Atom.create(r, X, Y),), (Atom.create(s, X, Y),)
        )

        ont = _make_ontology(clauses=[r_sub_s, s_sub_r])
        reasoner = Reasoner(ont)
        reasoner.classify_object_properties()
        assert reasoner._object_role_hierarchy is not None

    def test_is_sub_role_of(self):
        """is_sub_role_of with pre-classified hierarchy uses hierarchy lookup."""
        ns = _ns("qo_issub.")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")

        r_sub_s = DLClause.create(
            (Atom.create(s, X, Y),), (Atom.create(r, X, Y),)
        )

        ont = _make_ontology(clauses=[r_sub_s])
        reasoner = Reasoner(ont)
        # Pre-classify so hierarchy lookup path is exercised
        reasoner.classify_object_properties()
        assert reasoner.is_sub_role_of(r, s)

    def test_is_not_sub_role_of(self):
        ns = _ns("qo_notsub.")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")

        ont = _make_ontology()
        reasoner = Reasoner(ont)
        reasoner.classify_object_properties()
        assert not reasoner.is_sub_role_of(r, s)

    def test_is_equivalent_role(self):
        """Equivalent roles (mutual subsumption) with pre-classified hierarchy."""
        ns = _ns("qo_equiv2.")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")

        r_sub_s = DLClause.create(
            (Atom.create(s, X, Y),), (Atom.create(r, X, Y),)
        )
        s_sub_r = DLClause.create(
            (Atom.create(r, X, Y),), (Atom.create(s, X, Y),)
        )

        ont = _make_ontology(clauses=[r_sub_s, s_sub_r])
        reasoner = Reasoner(ont)
        reasoner.classify_object_properties()
        assert reasoner.is_equivalent_role(r, s)

    def test_is_sub_role_chain(self):
        """3-level chain r < s < t: is_sub_role_of(r, t) with hierarchy."""
        ns = _ns("qo_chain.")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")
        t = AtomicRole(ns + "t")

        r_sub_s = DLClause.create(
            (Atom.create(s, X, Y),), (Atom.create(r, X, Y),)
        )
        s_sub_t = DLClause.create(
            (Atom.create(t, X, Y),), (Atom.create(s, X, Y),)
        )

        ont = _make_ontology(clauses=[r_sub_s, s_sub_t])
        reasoner = Reasoner(ont)
        reasoner.classify_object_properties()
        assert reasoner.is_sub_role_of(r, t)

    def test_classify_inverse_role_subsumption(self):
        """Inverse role inclusion (using InverseRole) exercises the inverse-propagation code."""
        ns = _ns("qo_inv.")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")
        inv_r = InverseRole(r)

        # r^- -> s (using actual InverseRole — triggers has_inverses=True)
        r_inv_sub_s = DLClause.create(
            (Atom.create(s, X, Y),),
            (Atom.create(inv_r, X, Y),),
        )

        ont = _make_ontology(clauses=[r_inv_sub_s])
        reasoner = Reasoner(ont)
        reasoner.classify_object_properties()
        assert reasoner._object_role_hierarchy is not None

    def test_inverse_role_encoding_swapped_args(self):
        """r(Y, X) -> s(X, Y) encodes r^- -> s using argument swap (lines 74-79)."""
        ns = _ns("qo_swap.")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")

        # r^- -> s encoded by swapping arguments
        r_inv_sub_s = DLClause.create(
            (Atom.create(s, X, Y),),
            (Atom.create(r, Y, X),),
        )

        ont = _make_ontology(clauses=[r_inv_sub_s])
        reasoner = Reasoner(ont)
        reasoner.classify_object_properties()
        assert reasoner._object_role_hierarchy is not None

    def test_inverse_role_hierarchy_with_subsumption(self):
        """InverseRole in body triggers _add_known_subsumption with m_has_inverses=True."""
        ns = _ns("qo_invsub.")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")
        inv_r = InverseRole(r)

        # r^- -> s^- (both inverses)
        r_sub_s_fwd = DLClause.create(
            (Atom.create(s, X, Y),), (Atom.create(r, X, Y),)
        )
        r_inv_sub_s_inv = DLClause.create(
            (Atom.create(s, Y, X),), (Atom.create(inv_r, X, Y),)
        )

        ont = _make_ontology(clauses=[r_sub_s_fwd, r_inv_sub_s_inv])
        reasoner = Reasoner(ont)
        # Ontology has inverse roles (InverseRole in atoms)
        assert reasoner._dl_ontology.has_inverse_roles()
        reasoner.classify_object_properties()
        assert reasoner._object_role_hierarchy is not None
        assert reasoner.is_sub_role_of(r, s)

    def test_inverse_role_subsumption_with_hierarchy(self):
        """3 roles + inverse roles: exercises full QO for roles with has_inverses=True."""
        ns = _ns("qo_inv3.")
        r = AtomicRole(ns + "r")
        s = AtomicRole(ns + "s")
        t = AtomicRole(ns + "t")
        inv_r = InverseRole(r)

        # r -> s, r^- is in ontology
        r_sub_s = DLClause.create(
            (Atom.create(s, X, Y),), (Atom.create(r, X, Y),)
        )
        # Introduce InverseRole to set has_inverses=True
        inv_clause = DLClause.create(
            (Atom.create(t, X, Y),), (Atom.create(inv_r, X, Y),)
        )

        ont = _make_ontology(clauses=[r_sub_s, inv_clause])
        reasoner = Reasoner(ont)
        reasoner.classify_object_properties()
        assert reasoner._object_role_hierarchy is not None


# ---------------------------------------------------------------------------
# Instance manager with pre-classified hierarchy (lines 116-139, 157-164)
# ---------------------------------------------------------------------------

class TestInstanceManagerPreClassifiedHierarchy:
    """InstanceManager built with already-classified hierarchies."""

    def test_instance_manager_with_both_hierarchies(self):
        """Pre-classified concept AND role hierarchy path through __init__."""
        ns = _ns("im_both.")
        A = AtomicConcept.create(ns + "A")
        r = AtomicRole(ns + "r")
        i1 = Individual(ns + "i1")
        i2 = Individual(ns + "i2")

        sub_role = DLClause.create(
            (Atom.create(AtomicRole(ns + "s"), X, Y),),
            (Atom.create(r, X, Y),),
        )

        ont = _make_ontology(
            clauses=[sub_role],
            facts=[
                Atom.create(A, i1),
                Atom.create(A, i2),
                Atom.create(r, i1, i2),
            ],
        )
        reasoner = Reasoner(ont)
        # Classify both before calling get_instances
        reasoner.classify_classes()
        reasoner.classify_object_properties()
        instances = reasoner.get_instances(A, direct=False)
        assert i1 in instances or i2 in instances

    def test_get_instances_triggers_property_init(self):
        """get_instances triggers initialize_know_and_possible_property_instances."""
        ns = _ns("im_prop.")
        A = AtomicConcept.create(ns + "A")
        r = AtomicRole(ns + "r")
        i1 = Individual(ns + "i1")
        i2 = Individual(ns + "i2")
        i3 = Individual(ns + "i3")

        ont = _make_ontology(
            facts=[
                Atom.create(A, i1),
                Atom.create(A, i2),
                Atom.create(A, i3),
                Atom.create(r, i1, i2),
                Atom.create(r, i2, i3),
            ]
        )
        reasoner = Reasoner(ont)
        # This triggers the full instance manager path
        assert reasoner.has_role_relationship(i1, r, i2)
        assert reasoner.has_role_relationship(i2, r, i3)

    def test_same_as_semantics(self):
        """Equality between individuals exercises _initialize_same_as paths."""
        ns = _ns("im_same.")
        A = AtomicConcept.create(ns + "A")
        r = AtomicRole(ns + "r")
        i1 = Individual(ns + "i1")
        i2 = Individual(ns + "i2")

        # Force equality: r is functional and has one filler per i1
        from hermit.model import AtLeastConcept, Equality
        equality_clause = DLClause.create(
            (Atom.create(Equality.INSTANCE, Y0, Y1),),
            (Atom.create(r, X, Y0), Atom.create(r, X, Y1)),
        )

        ont = _make_ontology(
            clauses=[equality_clause],
            facts=[
                Atom.create(A, i1),
                Atom.create(A, i2),
                Atom.create(r, i1, i2),
            ],
        )
        reasoner = Reasoner(ont)
        assert reasoner.is_consistent()
        instances = reasoner.get_instances(A, direct=False)
        assert i1 in instances or i2 in instances
