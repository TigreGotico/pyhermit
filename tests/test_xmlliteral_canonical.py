"""rdf:XMLLiteral canonicalization tests (WebOnt-miscellaneous-202 repro).

Java HermiT parses rdf:XMLLiteral lexical forms through XML canonicalization
(``XMLLiteral.parse``), so two literals that differ only in attribute order or
empty-element syntax denote the same data value. A functional data property
with two such values must therefore be satisfiable.
"""

from __future__ import annotations

import pytest

from hermit import Configuration, Reasoner
from hermit.datatypes.registry import DatatypeRegistry, MalformedLiteralException
from hermit.datatypes.xmlliteral import XMLLiteralValue
from hermit.model import Constant
from hermit.owl_model.iri import IRI
from hermit.owl_model.owl_axiom import (
    OWLDataPropertyAssertionAxiom,
    OWLFunctionalDataPropertyAxiom,
)
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.owl_model.owl_literal import OWLDatatype, OWLLiteral
from hermit.owl_model.owl_property import OWLDataProperty
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization

NS = "http://test.org#"
XML_LITERAL = "http://www.w3.org/1999/02/22-rdf-syntax-ns#XMLLiteral"

# Same canonical XML, written with different attribute order and
# empty-element syntax.
XML_A = '<img src="vn.png" alt="Venn diagram" longdesc="vn.html" title="Venn"></img>'
XML_B = '<img src="vn.png" title="Venn" alt="Venn diagram" longdesc="vn.html" />'
XML_OTHER = '<img src="other.png" />'


def _xml_literal(lexical: str) -> OWLLiteral:
    return OWLLiteral(lexical, OWLDatatype(IRI.create(XML_LITERAL)))  # type: ignore[abstract]


def _reasoner(axioms: list) -> Reasoner:
    config = Configuration()
    config.throw_inconsistent_ontology_exception = False
    norm = OWLNormalization().process_ontology(axioms)
    onto = OWLClausification().clausify(norm, ontology_iri="urn:test:xmlliteral")
    return Reasoner(onto, config)


class TestCanonicalization:
    def test_attribute_order_is_canonicalized(self):
        v1 = DatatypeRegistry.parse_literal(XML_A, XML_LITERAL)
        v2 = DatatypeRegistry.parse_literal(XML_B, XML_LITERAL)
        assert isinstance(v1, XMLLiteralValue)
        assert v1 == v2

    def test_different_content_stays_different(self):
        v1 = DatatypeRegistry.parse_literal(XML_A, XML_LITERAL)
        v2 = DatatypeRegistry.parse_literal(XML_OTHER, XML_LITERAL)
        assert v1 != v2

    def test_constants_share_data_value(self):
        c1 = Constant.create(XML_A, XML_LITERAL)
        c2 = Constant.create(XML_B, XML_LITERAL)
        assert c1.data_value == c2.data_value

    def test_malformed_literal_raises(self):
        with pytest.raises(MalformedLiteralException):
            DatatypeRegistry.parse_literal("<unclosed", XML_LITERAL)

    def test_fragment_with_multiple_roots_and_text(self):
        v1 = DatatypeRegistry.parse_literal('<br></br>\n<b a="1" b="2">x</b>', XML_LITERAL)
        v2 = DatatypeRegistry.parse_literal('<br/>\n<b b="2" a="1">x</b>', XML_LITERAL)
        assert v1 == v2


class TestFunctionalPropertyOnXMLLiterals:
    """Minimal WebOnt-miscellaneous-202 repro."""

    def _axioms(self, lex1: str, lex2: str) -> list:
        fp = OWLDataProperty(IRI.create(NS + "fp"))
        ind = OWLNamedIndividual(IRI.create(NS + "a"))
        return [
            OWLFunctionalDataPropertyAxiom(fp),
            OWLDataPropertyAssertionAxiom(ind, fp, _xml_literal(lex1)),
            OWLDataPropertyAssertionAxiom(ind, fp, _xml_literal(lex2)),
        ]

    def test_canonically_equal_values_are_consistent(self):
        reasoner = _reasoner(self._axioms(XML_A, XML_B))
        assert reasoner.is_consistent()

    def test_truly_different_values_are_inconsistent(self):
        reasoner = _reasoner(self._axioms(XML_A, XML_OTHER))
        assert not reasoner.is_consistent()
