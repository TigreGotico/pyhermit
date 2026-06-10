"""Tests for builtin_property_manager: usage detection and axiomatization.

Covers _collect_property_iris traversal over the axiom forms the manager
must see through, and the per-property axiomatizations returned by
BuiltInPropertyManager.axioms_for_builtin_properties.
"""

from __future__ import annotations

from hermit.owl_model.class_expression import OWLClass
from hermit.owl_model.iri import IRI
from hermit.owl_model.owl_axiom import (
    OWLDataPropertyAssertionAxiom,
    OWLObjectPropertyAssertionAxiom,
    OWLObjectPropertyDomainAxiom,
    OWLObjectPropertyRangeAxiom,
    OWLSubDataPropertyOfAxiom,
    OWLSubObjectPropertyOfAxiom,
)
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_literal import _OWLLiteralImplString as OWLStringLiteral
from hermit.owl_model.owl_property import OWLDataProperty, OWLObjectProperty
from hermit.structural.builtin_property_manager import (
    BuiltInPropertyManager,
    _collect_property_iris,
)

TOP_OBJ_IRI = BuiltInPropertyManager.TOP_OBJECT_PROPERTY_IRI
BOT_OBJ_IRI = BuiltInPropertyManager.BOTTOM_OBJECT_PROPERTY_IRI
TOP_DATA_IRI = BuiltInPropertyManager.TOP_DATA_PROPERTY_IRI
BOT_DATA_IRI = BuiltInPropertyManager.BOTTOM_DATA_PROPERTY_IRI

NS = "http://test.org#"


def _ind(local: str) -> OWLNamedIndividual:
    return OWLNamedIndividual(IRI.create(NS + local))


def _obj_prop(local: str) -> OWLObjectProperty:
    return OWLObjectProperty(IRI.create(NS + local))


def _data_prop(local: str) -> OWLDataProperty:
    return OWLDataProperty(IRI.create(NS + local))


def _used(axioms: list) -> set[str]:
    used: set[str] = set()
    for axiom in axioms:
        _collect_property_iris(axiom, used)
    return used


class TestCollectPropertyIris:
    def test_object_property_assertion(self):
        axiom = OWLObjectPropertyAssertionAxiom(_ind("a"), _obj_prop("r"), _ind("b"))
        assert NS + "r" in _used([axiom])

    def test_data_property_assertion(self):
        axiom = OWLDataPropertyAssertionAxiom(
            _ind("a"), _data_prop("d"), OWLStringLiteral("hello")
        )
        assert NS + "d" in _used([axiom])

    def test_sub_object_property(self):
        axiom = OWLSubObjectPropertyOfAxiom(_obj_prop("r"), _obj_prop("s"))
        used = _used([axiom])
        assert NS + "r" in used and NS + "s" in used

    def test_object_property_domain_and_range(self):
        domain = OWLObjectPropertyDomainAxiom(
            _obj_prop("r"), OWLClass(IRI.create(NS + "A"))
        )
        range_ = OWLObjectPropertyRangeAxiom(
            _obj_prop("s"), OWLClass(IRI.create(NS + "B"))
        )
        used = _used([domain, range_])
        assert NS + "r" in used and NS + "s" in used

    def test_sub_data_property(self):
        axiom = OWLSubDataPropertyOfAxiom(_data_prop("d1"), _data_prop("d2"))
        used = _used([axiom])
        assert NS + "d1" in used and NS + "d2" in used

    def test_property_in_class_expression(self):
        from hermit.owl_model.class_expression import OWLObjectSomeValuesFrom
        from hermit.owl_model.owl_axiom import OWLSubClassOfAxiom

        a = OWLClass(IRI.create(NS + "A"))
        top_prop = OWLObjectProperty(IRI.create(TOP_OBJ_IRI))
        axiom = OWLSubClassOfAxiom(a, OWLObjectSomeValuesFrom(top_prop, a))
        assert TOP_OBJ_IRI in _used([axiom])

    def test_inverse_property_expression(self):
        from hermit.owl_model.owl_property import OWLObjectInverseOf

        inv = OWLObjectInverseOf(_obj_prop("r"))
        axiom = OWLObjectPropertyAssertionAxiom(_ind("a"), inv, _ind("b"))
        assert NS + "r" in _used([axiom])

    def test_normal_properties_do_not_trigger_builtins(self):
        axioms = [
            OWLObjectPropertyAssertionAxiom(_ind("a"), _obj_prop("r"), _ind("b")),
            OWLDataPropertyAssertionAxiom(
                _ind("a"), _data_prop("d"), OWLStringLiteral("v")
            ),
        ]
        used = _used(axioms)
        assert TOP_OBJ_IRI not in used
        assert BOT_OBJ_IRI not in used
        assert TOP_DATA_IRI not in used
        assert BOT_DATA_IRI not in used


class TestAxiomatization:
    def test_no_builtins_no_axioms(self):
        axioms = [
            OWLObjectPropertyAssertionAxiom(_ind("a"), _obj_prop("r"), _ind("b"))
        ]
        assert BuiltInPropertyManager().axioms_for_builtin_properties(axioms) == []

    def test_top_object_property(self):
        top_prop = OWLObjectProperty(IRI.create(TOP_OBJ_IRI))
        axioms = [OWLObjectPropertyAssertionAxiom(_ind("a"), top_prop, _ind("b"))]
        extra = BuiltInPropertyManager().axioms_for_builtin_properties(axioms)
        # transitivity + symmetry + universality
        assert len(extra) == 3

    def test_bottom_object_property(self):
        bot_prop = OWLObjectProperty(IRI.create(BOT_OBJ_IRI))
        axioms = [OWLSubObjectPropertyOfAxiom(bot_prop, _obj_prop("s"))]
        extra = BuiltInPropertyManager().axioms_for_builtin_properties(axioms)
        assert len(extra) == 1

    def test_top_data_property(self):
        top_dp = OWLDataProperty(IRI.create(TOP_DATA_IRI))
        axioms = [
            OWLDataPropertyAssertionAxiom(_ind("a"), top_dp, OWLStringLiteral("v"))
        ]
        extra = BuiltInPropertyManager().axioms_for_builtin_properties(axioms)
        assert len(extra) == 1

    def test_bottom_data_property(self):
        bot_dp = OWLDataProperty(IRI.create(BOT_DATA_IRI))
        axioms = [OWLSubDataPropertyOfAxiom(bot_dp, _data_prop("d"))]
        extra = BuiltInPropertyManager().axioms_for_builtin_properties(axioms)
        assert len(extra) == 1

    def test_multiple_builtins(self):
        top_prop = OWLObjectProperty(IRI.create(TOP_OBJ_IRI))
        bot_dp = OWLDataProperty(IRI.create(BOT_DATA_IRI))
        axioms = [
            OWLObjectPropertyAssertionAxiom(_ind("a"), top_prop, _ind("b")),
            OWLDataPropertyAssertionAxiom(_ind("a"), bot_dp, OWLStringLiteral("x")),
        ]
        extra = BuiltInPropertyManager().axioms_for_builtin_properties(axioms)
        assert len(extra) == 4
