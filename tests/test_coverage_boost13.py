"""Coverage boost 13 — targeted tests for object_property_inclusion_manager.py.

Covers lines: 31, 74, 76, 86-89, 93, 97, 107, 137, 195, 237, 244, 252,
             271-274, 278-294, 305-307, 312-314, 330, 332, 343-344, 349
"""

from __future__ import annotations

import pytest

from hermit.model import AtomicRole, InverseRole
from hermit.structural.normalized_axioms import (
    ComplexObjectPropertyInclusion,
    NormalizedAxioms,
)
from hermit.structural.object_property_inclusion_manager import (
    ObjectPropertyInclusionManager,
)

NS = "http://test.org#"


def _ar(local: str) -> AtomicRole:
    return AtomicRole.create(NS + local)


def _inv(local: str) -> InverseRole:
    return InverseRole.create(_ar(local))


def _norm(**kwargs) -> NormalizedAxioms:
    norm = NormalizedAxioms()
    for k, v in kwargs.items():
        setattr(norm, k, v)
    return norm


def _transitive_inclusion(role: AtomicRole) -> ComplexObjectPropertyInclusion:
    return ComplexObjectPropertyInclusion(
        sub_object_properties=(role, role),
        super_object_property=role,
    )


class TestDetectComplexProperties:
    def test_init_with_normalized_axioms(self):
        """Line 31: __init__ with normalized_axioms triggers _detect_complex_properties."""
        r = _ar("r")
        chain_inc = _transitive_inclusion(r)
        norm = _norm(complex_object_property_inclusions=[chain_inc])
        mgr = ObjectPropertyInclusionManager(norm)
        assert r in mgr.complex_properties

    def test_transitive_role_complex(self):
        """Transitive property is directly complex."""
        r = _ar("r")
        chain_inc = _transitive_inclusion(r)
        norm = _norm(complex_object_property_inclusions=[chain_inc])
        mgr = ObjectPropertyInclusionManager(norm)
        assert r in mgr.complex_properties
        # Inverse of transitive is also complex (line 202)
        assert InverseRole.create(r) in mgr.complex_properties

    def test_inverse_role_in_complex_props(self):
        """Lines 193-194: _get_inverse with InverseRole argument."""
        r = _ar("r")
        inv_r = _inv("r")
        chain_inc = ComplexObjectPropertyInclusion(sub_object_properties=(inv_r, inv_r), super_object_property=inv_r)
        norm = _norm(complex_object_property_inclusions=[chain_inc])
        mgr = ObjectPropertyInclusionManager(norm)
        assert inv_r in mgr.complex_properties
        # Inverse of InverseRole(r) = r
        assert r in mgr.complex_properties

    def test_propagation_through_simple_inclusions(self):
        """Line 207-210: if R complex and R ⊑ P, P becomes complex."""
        r = _ar("r")
        s = _ar("s")
        chain_inc = _transitive_inclusion(r)
        # Simple inclusion: r ⊑ s
        norm = _norm(
            complex_object_property_inclusions=[chain_inc],
            simple_object_property_inclusions=[(r, s)],
        )
        mgr = ObjectPropertyInclusionManager(norm)
        assert r in mgr.complex_properties
        assert s in mgr.complex_properties

    def test_no_complex_properties(self):
        """No complex inclusions → empty complex_properties."""
        norm = _norm()
        mgr = ObjectPropertyInclusionManager(norm)
        assert len(mgr.complex_properties) == 0


class TestValidateConstraints:
    def test_asymmetric_complex_raises(self):
        """Line 237: asymmetric complex property raises ValueError."""
        r = _ar("r")
        chain_inc = _transitive_inclusion(r)
        norm = _norm(
            complex_object_property_inclusions=[chain_inc],
            asymmetric_object_properties={r},
        )
        mgr = ObjectPropertyInclusionManager()
        mgr.complex_properties.add(r)
        norm2 = _norm(asymmetric_object_properties={r})
        mgr2 = ObjectPropertyInclusionManager()
        mgr2.complex_properties.add(r)
        with pytest.raises(ValueError, match="asymmetric"):
            mgr2._validate_complex_property_constraints(norm2)

    def test_irreflexive_complex_raises(self):
        """Line 244: irreflexive complex property raises ValueError."""
        r = _ar("r")
        mgr = ObjectPropertyInclusionManager()
        mgr.complex_properties.add(r)
        norm = _norm(irreflexive_object_properties={r})
        with pytest.raises(ValueError, match="irreflexive"):
            mgr._validate_complex_property_constraints(norm)

    def test_disjoint_complex_raises(self):
        """Line 252: disjoint complex property raises ValueError."""
        r = _ar("r")
        mgr = ObjectPropertyInclusionManager()
        mgr.complex_properties.add(r)
        norm = _norm(disjoint_object_properties=[(r, _ar("s"))])
        with pytest.raises(ValueError, match="disjoint"):
            mgr._validate_complex_property_constraints(norm)

    def test_max_cardinality_complex_raises(self):
        """Line 349: max_cardinality_roles with complex role raises ValueError."""
        r = _ar("r")
        mgr = ObjectPropertyInclusionManager()
        mgr.complex_properties.add(r)
        norm = _norm(max_cardinality_roles=[r])
        with pytest.raises(ValueError, match="max-cardinality"):
            mgr._validate_complex_property_constraints(norm)

    def test_no_violations_ok(self):
        """No violations — validate_complex_property_constraints returns normally."""
        r = _ar("r")
        s = _ar("s")  # s is not complex
        mgr = ObjectPropertyInclusionManager()
        mgr.complex_properties.add(r)
        norm = _norm(
            asymmetric_object_properties={s},
            irreflexive_object_properties={s},
            disjoint_object_properties=[(s, _ar("t"))],
            max_cardinality_roles=[s],
        )
        mgr._validate_complex_property_constraints(norm)  # no raise


class TestCheckConceptInclusionsForNonSimple:
    def test_cardinality_restriction_with_complex_role(self):
        """Lines 305-307: OWLObjectCardinalityRestriction with complex role raises."""
        from hermit.owl_model.class_expression.restriction import (
            OWLObjectMinCardinality,
        )
        from hermit.owl_model.owl_property import OWLObjectProperty
        from hermit.owl_model.iri import IRI

        r = _ar("r")
        owl_r = OWLObjectProperty(IRI(NS, "r"))
        from hermit.owl_model.class_expression import OWLClass
        from hermit.owl_model.iri import IRI as _IRI
        filler = OWLClass(_IRI(NS, "A"))
        restriction = OWLObjectMinCardinality(1, owl_r, filler)
        complex_props = {r}
        norm = _norm(concept_inclusions=[[restriction]])
        with pytest.raises(ValueError, match="cardinality"):
            ObjectPropertyInclusionManager._check_concept_inclusions_for_non_simple(
                norm, complex_props
            )

    def test_has_self_restriction_with_complex_role(self):
        """Lines 312-314: OWLObjectHasSelf with complex role raises."""
        from hermit.owl_model.class_expression import OWLObjectHasSelf
        from hermit.owl_model.owl_property import OWLObjectProperty
        from hermit.owl_model.iri import IRI

        r = _ar("r")
        owl_r = OWLObjectProperty(IRI(NS, "r"))
        self_restriction = OWLObjectHasSelf(owl_r)
        complex_props = {r}
        norm = _norm(concept_inclusions=[[self_restriction]])
        with pytest.raises(ValueError, match="Self"):
            ObjectPropertyInclusionManager._check_concept_inclusions_for_non_simple(
                norm, complex_props
            )

    def test_no_violations_in_concept_inclusions(self):
        """Non-complex role in cardinality restriction → no raise."""
        from hermit.owl_model.class_expression.restriction import (
            OWLObjectMinCardinality,
        )
        from hermit.owl_model.owl_property import OWLObjectProperty
        from hermit.owl_model.iri import IRI
        from hermit.owl_model.class_expression import OWLClass

        r = _ar("r")
        s = _ar("s")  # only r is complex
        owl_r = OWLObjectProperty(IRI(NS, "r"))
        filler = OWLClass(IRI(NS, "A"))
        restriction = OWLObjectMinCardinality(1, owl_r, filler)
        complex_props = {s}  # r not complex
        norm = _norm(concept_inclusions=[[restriction]])
        # Should not raise
        ObjectPropertyInclusionManager._check_concept_inclusions_for_non_simple(
            norm, complex_props
        )


class TestRewriteNegativeObjectPropertyAssertions:
    """Tests for rewrite_negative_object_property_assertions — covers lines 74, 76, 86-89, 93, 97, 107, 137."""

    def test_rewrite_with_inverse_role_complex_prop(self):
        """Lines 86-89: InverseRole in complex_properties triggers the elif branch."""
        from hermit.owl_model.owl_axiom import OWLNegativeObjectPropertyAssertionAxiom
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        from hermit.owl_model.owl_property import OWLObjectProperty
        from hermit.owl_model.iri import IRI

        r = _ar("r")
        inv_r = InverseRole.create(r)

        ind_a = OWLNamedIndividual(IRI(NS, "a"))
        ind_b = OWLNamedIndividual(IRI(NS, "b"))
        owl_r = OWLObjectProperty(IRI(NS, "r"))
        neg_assertion = OWLNegativeObjectPropertyAssertionAxiom(ind_a, owl_r, ind_b)

        mgr = ObjectPropertyInclusionManager()
        mgr.complex_properties.add(inv_r)  # InverseRole is complex

        norm = _norm(negative_facts=[neg_assertion])
        # Should process without error; the owl_r IRI matches inv_r's base
        mgr.rewrite_negative_object_property_assertions(norm)

    def test_rewrite_with_atomic_role_complex_prop(self):
        """AtomicRole complex prop — rewrite changes the negative fact into DL clause."""
        from hermit.owl_model.owl_axiom import OWLNegativeObjectPropertyAssertionAxiom
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        from hermit.owl_model.owl_property import OWLObjectProperty
        from hermit.owl_model.iri import IRI

        r = _ar("r")

        ind_a = OWLNamedIndividual(IRI(NS, "a"))
        ind_b = OWLNamedIndividual(IRI(NS, "b"))
        owl_r = OWLObjectProperty(IRI(NS, "r"))
        neg_assertion = OWLNegativeObjectPropertyAssertionAxiom(ind_a, owl_r, ind_b)

        mgr = ObjectPropertyInclusionManager()
        mgr.complex_properties.add(r)

        norm = _norm(negative_facts=[neg_assertion])
        idx = mgr.rewrite_negative_object_property_assertions(norm)
        assert idx == 1  # one replacement was made
        assert neg_assertion not in norm.negative_facts

    def test_rewrite_fact_not_negative_obj_prop_axiom(self):
        """Line 93: non-OWLNegativeObjectPropertyAssertionAxiom in negative_facts is skipped."""
        mgr = ObjectPropertyInclusionManager()
        mgr.complex_properties.add(_ar("r"))
        norm = _norm(negative_facts=["not_an_axiom"])
        idx = mgr.rewrite_negative_object_property_assertions(norm)
        assert idx == 0

    def test_rewrite_with_dl_clauses_attr(self):
        """Line 137: when normalized_axioms has dl_clauses attribute, new clauses go there."""
        from hermit.owl_model.owl_axiom import OWLNegativeObjectPropertyAssertionAxiom
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        from hermit.owl_model.owl_property import OWLObjectProperty
        from hermit.owl_model.iri import IRI

        r = _ar("r")
        ind_a = OWLNamedIndividual(IRI(NS, "a"))
        ind_b = OWLNamedIndividual(IRI(NS, "b"))
        owl_r = OWLObjectProperty(IRI(NS, "r"))
        neg_assertion = OWLNegativeObjectPropertyAssertionAxiom(ind_a, owl_r, ind_b)

        mgr = ObjectPropertyInclusionManager()
        mgr.complex_properties.add(r)

        norm = _norm(negative_facts=[neg_assertion])
        norm.dl_clauses = []  # add dl_clauses attribute
        mgr.rewrite_negative_object_property_assertions(norm)
        assert len(norm.dl_clauses) == 1  # new clause was added here

    def test_rewrite_no_negative_facts(self):
        """No negative facts → no-op, returns first_replacement_index."""
        mgr = ObjectPropertyInclusionManager()
        norm = _norm()
        idx = mgr.rewrite_negative_object_property_assertions(norm, first_replacement_index=5)
        assert idx == 5

    def test_rewrite_non_matching_negative_fact(self):
        """OWLNegativeObjectPropertyAssertionAxiom with non-complex role → skipped."""
        from hermit.owl_model.owl_axiom import OWLNegativeObjectPropertyAssertionAxiom
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        from hermit.owl_model.owl_property import OWLObjectProperty
        from hermit.owl_model.iri import IRI

        r = _ar("r")
        s = _ar("s")  # only r is complex, not s

        ind_a = OWLNamedIndividual(IRI(NS, "a"))
        ind_b = OWLNamedIndividual(IRI(NS, "b"))
        owl_s = OWLObjectProperty(IRI(NS, "s"))
        neg_assertion = OWLNegativeObjectPropertyAssertionAxiom(ind_a, owl_s, ind_b)

        mgr = ObjectPropertyInclusionManager()
        mgr.complex_properties.add(r)  # s is not complex

        norm = _norm(negative_facts=[neg_assertion])
        idx = mgr.rewrite_negative_object_property_assertions(norm)
        assert idx == 0  # nothing replaced
        assert neg_assertion in norm.negative_facts


    def test_check_concept_inclusions_union_recurse(self):
        """Lines 330-332: recursion into OWLObjectUnionOf operands."""
        from hermit.owl_model.class_expression import OWLObjectUnionOf
        from hermit.owl_model.class_expression.restriction import OWLObjectMinCardinality
        from hermit.owl_model.owl_property import OWLObjectProperty
        from hermit.owl_model.iri import IRI
        from hermit.owl_model.class_expression import OWLClass

        r = _ar("r")
        owl_r = OWLObjectProperty(IRI(NS, "r"))
        filler = OWLClass(IRI(NS, "A"))
        restriction = OWLObjectMinCardinality(1, owl_r, filler)
        filler2 = OWLClass(IRI(NS, "B"))
        # OWLObjectUnionOf requires at least 2 operands
        restriction2 = OWLObjectMinCardinality(1, owl_r, filler2)
        union = OWLObjectUnionOf([restriction, restriction2])
        complex_props = {r}
        norm = _norm(concept_inclusions=[[union]])
        with pytest.raises(ValueError, match="cardinality"):
            ObjectPropertyInclusionManager._check_concept_inclusions_for_non_simple(
                norm, complex_props
            )

    def test_check_union_in_positive_facts(self):
        """Lines 343-344: OWLObjectUnionOf in positive_facts is checked."""
        from hermit.owl_model.class_expression import OWLObjectUnionOf
        from hermit.owl_model.class_expression.restriction import OWLObjectMinCardinality
        from hermit.owl_model.owl_property import OWLObjectProperty
        from hermit.owl_model.iri import IRI
        from hermit.owl_model.class_expression import OWLClass

        r = _ar("r")
        owl_r = OWLObjectProperty(IRI(NS, "r"))
        filler = OWLClass(IRI(NS, "A"))
        filler2 = OWLClass(IRI(NS, "B"))
        restriction = OWLObjectMinCardinality(1, owl_r, filler)
        restriction2 = OWLObjectMinCardinality(1, owl_r, filler2)
        union = OWLObjectUnionOf([restriction, restriction2])
        complex_props = {r}
        norm = _norm(positive_facts=[union])
        with pytest.raises(ValueError, match="cardinality"):
            ObjectPropertyInclusionManager._check_concept_inclusions_for_non_simple(
                norm, complex_props
            )


class TestRewriteAxioms:
    def test_rewrite_axioms_detects_then_validates(self):
        """rewrite_axioms calls _detect then _validate — no violation → ok."""
        r = _ar("r")
        chain_inc = _transitive_inclusion(r)
        norm = _norm(complex_object_property_inclusions=[chain_inc])
        mgr = ObjectPropertyInclusionManager()
        mgr.rewrite_axioms(norm)  # should not raise
        assert r in mgr.complex_properties
