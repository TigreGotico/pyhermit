"""Unit tests for the WG conformance runner's harness-level reductions.

Covers the pieces that mirror the Java harness around the reasoner:

* rolling up anonymous individuals in conclusion ABoxes
  (EntailmentChecker$AnonymousIndividualForestBuilder),
* data property assertion conclusions checked by refutation
  (EntailmentChecker.visit(OWLDataPropertyAssertionAxiom)),
* owl:imports resolution against the registry's local copies
  (AbstractTest.registerImportedReosurces).
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

from hermit.owl_model.class_expression import (
    OWLClass,
    OWLObjectComplementOf,
    OWLObjectIntersectionOf,
    OWLObjectSomeValuesFrom,
)
from hermit.owl_model.owl_axiom import (
    OWLClassAssertionAxiom,
    OWLObjectPropertyAssertionAxiom,
    OWLSubClassOfAxiom,
)
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_property import OWLObjectProperty
from hermit.owl_rdf import ANONYMOUS_INDIVIDUAL_PREFIX

_WG_DIR = Path(__file__).parent / "wg_conformance"
_PKG = "_pyhermit_wg_conformance"
if _PKG not in sys.modules:
    _spec = importlib.util.spec_from_file_location(
        _PKG, _WG_DIR / "__init__.py", submodule_search_locations=[str(_WG_DIR)]
    )
    assert _spec is not None and _spec.loader is not None
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_PKG] = _module
    _spec.loader.exec_module(_module)

_runner = importlib.import_module(f"{_PKG}.runner")

EX = "http://example.org/ns#"
OWL_THING = "http://www.w3.org/2002/07/owl#Thing"


def _anon(name: str) -> OWLNamedIndividual:
    return OWLNamedIndividual(f"{ANONYMOUS_INDIVIDUAL_PREFIX}{name}")


def _expr_str(expr) -> str:
    return repr(expr)


class TestRollUpAnonymous:
    def test_edge_to_anonymous_rolls_to_existential(self):
        # p(a, _:x)  ==>  a : exists p.Thing
        a = OWLNamedIndividual(EX + "a")
        p = OWLObjectProperty(EX + "p")
        assertions, no_named = _runner._roll_up_anonymous(
            [OWLObjectPropertyAssertionAxiom(a, p, _anon("x"))]
        )
        assert no_named == []
        assert len(assertions) == 1
        ax = assertions[0]
        assert isinstance(ax, OWLClassAssertionAxiom)
        assert _runner._ind_iri(ax.get_individual()) == EX + "a"
        ce = ax.get_class_expression()
        assert isinstance(ce, OWLObjectSomeValuesFrom)

    def test_chain_rolls_to_nested_existential(self):
        # p(a, _:x), q(_:x, _:y), C(_:y)  ==>  a : exists p.(exists q.C)
        a = OWLNamedIndividual(EX + "a")
        p = OWLObjectProperty(EX + "p")
        q = OWLObjectProperty(EX + "q")
        c = OWLClass(EX + "C")
        x, y = _anon("x"), _anon("y")
        assertions, no_named = _runner._roll_up_anonymous(
            [
                OWLObjectPropertyAssertionAxiom(a, p, x),
                OWLObjectPropertyAssertionAxiom(x, q, y),
                OWLClassAssertionAxiom(y, c),
            ]
        )
        assert no_named == []
        assert len(assertions) == 1
        text = _expr_str(assertions[0].get_class_expression())
        assert "p" in text and "q" in text and "C" in text

    def test_no_named_component_becomes_subclass_refutation_axiom(self):
        # p(_:x, _:y)  ==>  SubClassOf(Thing, not(exists p.Thing))
        p = OWLObjectProperty(EX + "p")
        assertions, no_named = _runner._roll_up_anonymous(
            [OWLObjectPropertyAssertionAxiom(_anon("x"), p, _anon("y"))]
        )
        assert assertions == []
        assert len(no_named) == 1
        ax = no_named[0]
        assert isinstance(ax, OWLSubClassOfAxiom)
        assert isinstance(ax.super_class, OWLObjectComplementOf)

    def test_labels_and_branches_are_conjoined(self):
        # p(a, _:x), C(_:x), q(_:x, _:y)  ==>  a : exists p.(C and exists q.Thing)
        a = OWLNamedIndividual(EX + "a")
        p = OWLObjectProperty(EX + "p")
        q = OWLObjectProperty(EX + "q")
        c = OWLClass(EX + "C")
        x, y = _anon("x"), _anon("y")
        assertions, _ = _runner._roll_up_anonymous(
            [
                OWLObjectPropertyAssertionAxiom(a, p, x),
                OWLClassAssertionAxiom(x, c),
                OWLObjectPropertyAssertionAxiom(x, q, y),
            ]
        )
        (ax,) = assertions
        ce = ax.get_class_expression()
        assert isinstance(ce, OWLObjectSomeValuesFrom)
        assert isinstance(ce.get_filler(), OWLObjectIntersectionOf)

    def test_owl_thing_labels_are_dropped(self):
        a = OWLNamedIndividual(EX + "a")
        p = OWLObjectProperty(EX + "p")
        x = _anon("x")
        assertions, _ = _runner._roll_up_anonymous(
            [
                OWLObjectPropertyAssertionAxiom(a, p, x),
                OWLClassAssertionAxiom(x, OWLClass(OWL_THING)),
            ]
        )
        (ax,) = assertions
        filler = ax.get_class_expression().get_filler()
        assert isinstance(filler, OWLClass)
        assert _runner._name(filler) == OWL_THING


class TestEntailmentReductions:
    def test_data_property_assertion_entailed_by_value_pinning(self):
        # range(p) = oneOf(4); a : exists p.TOP   |=   p(a, 4)
        from hermit.owl_model.class_expression.restriction import (
            OWLDataOneOf,
            OWLDataSomeValuesFrom,
        )
        from hermit.owl_model.owl_axiom import (
            OWLDataPropertyAssertionAxiom,
            OWLDataPropertyRangeAxiom,
        )
        from hermit.owl_model.owl_datatype import OWLDatatype
        from hermit.owl_model.owl_literal import OWLLiteral, TopOWLDatatype
        from hermit.owl_model.owl_property import OWLDataProperty

        xsd_int = OWLDatatype("http://www.w3.org/2001/XMLSchema#integer")
        four = OWLLiteral("4", xsd_int)
        five = OWLLiteral("5", xsd_int)
        p = OWLDataProperty(EX + "p")
        a = OWLNamedIndividual(EX + "a")
        premise = [
            OWLDataPropertyRangeAxiom(p, OWLDataOneOf([four])),
            OWLClassAssertionAxiom(a, OWLDataSomeValuesFrom(p, TopOWLDatatype)),
        ]
        assert _runner._entails_axiom(
            premise, OWLDataPropertyAssertionAxiom(a, p, four), True
        )
        assert not _runner._entails_axiom(
            premise, OWLDataPropertyAssertionAxiom(a, p, five), True
        )


class TestImportResolution:
    def test_rdfxml_import_iris_extracted(self):
        doc = """<rdf:RDF
    xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'
    xmlns:owl='http://www.w3.org/2002/07/owl#'
    xml:base='http://example.org/base' >
    <owl:Ontology rdf:about=''>
        <owl:imports rdf:resource="http://example.org/imported"/>
    </owl:Ontology>
</rdf:RDF>"""
        assert _runner._import_iris(doc, "RDFXML") == [
            "http://example.org/imported"
        ]

    def test_functional_import_iris_extracted(self):
        doc = "Ontology(<http://example.org/o>\nImport(<http://example.org/i>)\n)"
        assert _runner._import_iris(doc, "FUNCTIONAL") == ["http://example.org/i"]

    def test_cyclic_registry_imports_terminate(self):
        # consistent001 and consistent002 import each other; loading either
        # must terminate and include axioms from both documents.
        registry = importlib.import_module(f"{_PKG}.registry")
        iri = "http://www.w3.org/2002/03owlt/miscellaneous/consistent001"
        path = registry.IMPORT_MAP[iri]
        if not path.exists():
            import pytest

            pytest.skip("WG test data not checked out")
        text = path.read_text(encoding="utf-8")
        axioms = _runner._load_axioms(text, "RDFXML")
        assert axioms
