"""Tests to boost coverage of builtin_property_manager._BuiltInPropertyChecker._check_axiom
and related helpers.

Targets: lines 221-245, 315-316, 321, 330-331, 334, 336
"""

from __future__ import annotations

import pytest

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
from hermit.owl_model.class_expression import OWLClass
from hermit.structural.builtin_property_manager import (
    BuiltInPropertyManager,
    _BuiltInPropertyChecker,
)
from hermit.structural.normalized_axioms import NormalizedAxioms

# Helpers
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


def _checker(positive_facts: list) -> _BuiltInPropertyChecker:
    norm = NormalizedAxioms()
    norm.positive_facts = positive_facts
    return _BuiltInPropertyChecker(norm)


class TestCheckAxiomBranches:
    """Tests for _BuiltInPropertyChecker._check_axiom branches (lines 221-245)."""

    def test_object_property_assertion_normal_prop(self):
        """OWLObjectPropertyAssertionAxiom with a normal property — no builtin flags set."""
        axiom = OWLObjectPropertyAssertionAxiom(_ind("a"), _obj_prop("r"), _ind("b"))
        checker = _checker([axiom])
        assert not checker.uses_top_object
        assert not checker.uses_bottom_object

    def test_data_property_assertion_normal_prop(self):
        """OWLDataPropertyAssertionAxiom with a normal data property."""
        axiom = OWLDataPropertyAssertionAxiom(
            _ind("a"), _data_prop("d"), OWLStringLiteral("hello")
        )
        checker = _checker([axiom])
        assert not checker.uses_top_data
        assert not checker.uses_bottom_data

    def test_sub_object_property_normal(self):
        """OWLSubObjectPropertyOfAxiom with two normal properties."""
        axiom = OWLSubObjectPropertyOfAxiom(_obj_prop("r"), _obj_prop("s"))
        checker = _checker([axiom])
        assert not checker.uses_top_object
        assert not checker.uses_bottom_object

    def test_object_property_domain_normal(self):
        """OWLObjectPropertyDomainAxiom does not trigger builtin flags."""
        axiom = OWLObjectPropertyDomainAxiom(
            _obj_prop("r"), OWLClass(IRI.create(NS + "A"))
        )
        checker = _checker([axiom])
        assert not checker.uses_top_object

    def test_object_property_range_normal(self):
        """OWLObjectPropertyRangeAxiom does not trigger builtin flags."""
        axiom = OWLObjectPropertyRangeAxiom(
            _obj_prop("r"), OWLClass(IRI.create(NS + "A"))
        )
        checker = _checker([axiom])
        assert not checker.uses_top_object

    def test_sub_data_property_normal(self):
        """OWLSubDataPropertyOfAxiom with two normal data properties."""
        axiom = OWLSubDataPropertyOfAxiom(_data_prop("d1"), _data_prop("d2"))
        checker = _checker([axiom])
        assert not checker.uses_top_data
        assert not checker.uses_bottom_data

    def test_object_property_assertion_top_object(self):
        """OWLObjectPropertyAssertionAxiom using owl:topObjectProperty sets uses_top_object."""
        top_prop = OWLObjectProperty(IRI.create(TOP_OBJ_IRI))
        axiom = OWLObjectPropertyAssertionAxiom(_ind("a"), top_prop, _ind("b"))
        checker = _checker([axiom])
        assert checker.uses_top_object

    def test_object_property_assertion_bottom_object(self):
        """OWLObjectPropertyAssertionAxiom with owl:bottomObjectProperty sets uses_bottom_object."""
        bot_prop = OWLObjectProperty(IRI.create(BOT_OBJ_IRI))
        axiom = OWLObjectPropertyAssertionAxiom(_ind("a"), bot_prop, _ind("b"))
        checker = _checker([axiom])
        assert checker.uses_bottom_object

    def test_data_property_assertion_top_data(self):
        """OWLDataPropertyAssertionAxiom with owl:topDataProperty sets uses_top_data."""
        top_dp = OWLDataProperty(IRI.create(TOP_DATA_IRI))
        axiom = OWLDataPropertyAssertionAxiom(
            _ind("a"), top_dp, OWLStringLiteral("v")
        )
        checker = _checker([axiom])
        assert checker.uses_top_data

    def test_data_property_assertion_bottom_data(self):
        """OWLDataPropertyAssertionAxiom with owl:bottomDataProperty sets uses_bottom_data."""
        bot_dp = OWLDataProperty(IRI.create(BOT_DATA_IRI))
        axiom = OWLDataPropertyAssertionAxiom(
            _ind("a"), bot_dp, OWLStringLiteral("v")
        )
        checker = _checker([axiom])
        assert checker.uses_bottom_data

    def test_sub_object_property_uses_top(self):
        """OWLSubObjectPropertyOfAxiom with owl:topObjectProperty as super."""
        top_prop = OWLObjectProperty(IRI.create(TOP_OBJ_IRI))
        axiom = OWLSubObjectPropertyOfAxiom(_obj_prop("r"), top_prop)
        checker = _checker([axiom])
        assert checker.uses_top_object

    def test_sub_object_property_uses_bottom_sub(self):
        """OWLSubObjectPropertyOfAxiom with owl:bottomObjectProperty as sub."""
        bot_prop = OWLObjectProperty(IRI.create(BOT_OBJ_IRI))
        axiom = OWLSubObjectPropertyOfAxiom(bot_prop, _obj_prop("s"))
        checker = _checker([axiom])
        assert checker.uses_bottom_object

    def test_domain_axiom_uses_top(self):
        """OWLObjectPropertyDomainAxiom with owl:topObjectProperty sets uses_top_object."""
        top_prop = OWLObjectProperty(IRI.create(TOP_OBJ_IRI))
        axiom = OWLObjectPropertyDomainAxiom(
            top_prop, OWLClass(IRI.create(NS + "A"))
        )
        checker = _checker([axiom])
        assert checker.uses_top_object

    def test_range_axiom_uses_top(self):
        """OWLObjectPropertyRangeAxiom with owl:topObjectProperty sets uses_top_object."""
        top_prop = OWLObjectProperty(IRI.create(TOP_OBJ_IRI))
        axiom = OWLObjectPropertyRangeAxiom(
            top_prop, OWLClass(IRI.create(NS + "A"))
        )
        checker = _checker([axiom])
        assert checker.uses_top_object

    def test_sub_data_property_uses_top(self):
        """OWLSubDataPropertyOfAxiom with owl:topDataProperty sets uses_top_data."""
        top_dp = OWLDataProperty(IRI.create(TOP_DATA_IRI))
        axiom = OWLSubDataPropertyOfAxiom(_data_prop("d"), top_dp)
        checker = _checker([axiom])
        assert checker.uses_top_data

    def test_sub_data_property_uses_bottom(self):
        """OWLSubDataPropertyOfAxiom with owl:bottomDataProperty sets uses_bottom_data."""
        bot_dp = OWLDataProperty(IRI.create(BOT_DATA_IRI))
        axiom = OWLSubDataPropertyOfAxiom(bot_dp, _data_prop("d"))
        checker = _checker([axiom])
        assert checker.uses_bottom_data

    def test_check_object_property_none(self):
        """_check_object_property(None) is a no-op."""
        norm = NormalizedAxioms()
        checker = _BuiltInPropertyChecker(norm)
        checker._check_object_property(None)  # should not raise
        assert not checker.uses_top_object

    def test_check_data_property_none(self):
        """_check_data_property(None) is a no-op."""
        norm = NormalizedAxioms()
        checker = _BuiltInPropertyChecker(norm)
        checker._check_data_property(None)  # should not raise
        assert not checker.uses_top_data

    def test_check_object_property_bad_object(self):
        """_check_object_property with an object that raises on iri access is a no-op."""
        class BadProp:
            @property
            def iri(self):
                raise RuntimeError("no iri")

        norm = NormalizedAxioms()
        checker = _BuiltInPropertyChecker(norm)
        checker._check_object_property(BadProp())
        assert not checker.uses_top_object

    def test_multiple_facts_mixed(self):
        """Multiple axioms in positive_facts — top_object and bottom_data both set."""
        top_prop = OWLObjectProperty(IRI.create(TOP_OBJ_IRI))
        bot_dp = OWLDataProperty(IRI.create(BOT_DATA_IRI))
        facts = [
            OWLObjectPropertyAssertionAxiom(_ind("a"), top_prop, _ind("b")),
            OWLDataPropertyAssertionAxiom(_ind("a"), bot_dp, OWLStringLiteral("x")),
        ]
        checker = _checker(facts)
        assert checker.uses_top_object
        assert checker.uses_bottom_data
        assert not checker.uses_bottom_object
        assert not checker.uses_top_data
