"""Annotation properties are non-logical in the RDF reader.

The OWL API maps triples whose predicate is a declared annotation property to
OWLAnnotationAssertionAxiom (and rdfs:subPropertyOf/domain/range on them to
the annotation-axiom forms), none of which carry logical content. The RDF
reader must therefore not turn such triples into data/object property
assertions, while genuinely logical properties keep parsing as logical
axioms.
"""

from __future__ import annotations

from hermit.owl_model.owl_axiom import (
    OWLDataPropertyAssertionAxiom,
    OWLDataPropertyRangeAxiom,
    OWLObjectPropertyAssertionAxiom,
    OWLSubDataPropertyOfAxiom,
)
from hermit.parser import load_ontology_from_string

_HEADER = """<rdf:RDF
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
    xmlns:owl="http://www.w3.org/2002/07/owl#"
    xmlns:ex="http://example.org/ns#"
    xml:base="http://example.org/ns" >
  <owl:Ontology/>
"""
_FOOTER = "</rdf:RDF>"


def _load(body: str) -> list:
    return load_ontology_from_string(_HEADER + body + _FOOTER, suffix=".rdf")


class TestAnnotationAssertionsExcluded:
    def test_literal_annotation_value_is_not_a_data_assertion(self):
        axioms = _load(
            """
  <owl:AnnotationProperty rdf:ID="note"/>
  <owl:Thing rdf:ID="a">
    <ex:note>some remark</ex:note>
  </owl:Thing>
"""
        )
        assert not any(
            isinstance(a, OWLDataPropertyAssertionAxiom) for a in axioms
        )

    def test_iri_annotation_value_is_not_an_object_assertion(self):
        axioms = _load(
            """
  <owl:AnnotationProperty rdf:ID="seeAlsoLike"/>
  <owl:Thing rdf:ID="a">
    <ex:seeAlsoLike rdf:resource="#b"/>
  </owl:Thing>
"""
        )
        assert not any(
            isinstance(a, OWLObjectPropertyAssertionAxiom) for a in axioms
        )

    def test_annotation_on_class_subject_is_excluded(self):
        # WebOnt-sameAs-001 conclusion shape: an annotation on a class IRI.
        axioms = _load(
            """
  <owl:AnnotationProperty rdf:ID="annotate"/>
  <owl:Class rdf:ID="c2">
    <ex:annotate>description of c1</ex:annotate>
  </owl:Class>
"""
        )
        assert axioms == []

    def test_sub_property_domain_range_on_annotation_props_excluded(self):
        axioms = _load(
            """
  <owl:AnnotationProperty rdf:ID="note"/>
  <owl:AnnotationProperty rdf:ID="remark">
    <rdfs:subPropertyOf rdf:resource="#note"/>
    <rdfs:domain rdf:resource="#D"/>
    <rdfs:range rdf:resource="#R"/>
  </owl:AnnotationProperty>
"""
        )
        assert axioms == []


class TestRealPropertiesStayLogical:
    def test_declared_data_property_assertion_is_logical(self):
        axioms = _load(
            """
  <owl:DatatypeProperty rdf:ID="age"/>
  <owl:Thing rdf:ID="a">
    <ex:age rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">4</ex:age>
  </owl:Thing>
"""
        )
        assert any(isinstance(a, OWLDataPropertyAssertionAxiom) for a in axioms)

    def test_undeclared_property_with_literal_is_still_logical(self):
        axioms = _load(
            """
  <owl:Thing rdf:ID="a">
    <ex:p>v</ex:p>
  </owl:Thing>
"""
        )
        assert any(isinstance(a, OWLDataPropertyAssertionAxiom) for a in axioms)

    def test_declared_object_property_assertion_is_logical(self):
        axioms = _load(
            """
  <owl:ObjectProperty rdf:ID="knows"/>
  <owl:Thing rdf:ID="a">
    <ex:knows rdf:resource="#b"/>
  </owl:Thing>
"""
        )
        assert any(isinstance(a, OWLObjectPropertyAssertionAxiom) for a in axioms)

    def test_data_property_schema_axioms_are_logical(self):
        axioms = _load(
            """
  <owl:DatatypeProperty rdf:ID="age">
    <rdfs:subPropertyOf rdf:resource="#measure"/>
    <rdfs:range
        rdf:resource="http://www.w3.org/2001/XMLSchema#integer"/>
  </owl:DatatypeProperty>
  <owl:DatatypeProperty rdf:ID="measure"/>
"""
        )
        assert any(isinstance(a, OWLSubDataPropertyOfAxiom) for a in axioms)
        assert any(isinstance(a, OWLDataPropertyRangeAxiom) for a in axioms)
