"""Frontend round-trips for datatype reasoning and negative assertions.

Each test parses an ontology document (Functional-Style Syntax or RDF/XML),
runs the full normalization + clausification + tableau pipeline, and checks
that the expected (in)consistency is detected. Satisfiable controls guard
against over-eager clash detection.
"""

from __future__ import annotations

from hermit.configuration import Configuration
from hermit.parser import load_ontology_from_string
from hermit.reasoner import Reasoner
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization

FSS_HEADER = (
    "Prefix(:=<http://example.org/>)\n"
    "Prefix(xsd:=<http://www.w3.org/2001/XMLSchema#>)\n"
    "Prefix(owl:=<http://www.w3.org/2002/07/owl#>)\n"
    "Prefix(rdfs:=<http://www.w3.org/2000/01/rdf-schema#>)\n"
    "Ontology(\n"
)

RDF_HEADER = (
    '<?xml version="1.0"?>\n'
    '<rdf:RDF xml:base="http://example.org/" xmlns="http://example.org/"\n'
    '  xmlns:owl="http://www.w3.org/2002/07/owl#"\n'
    '  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n'
    '  xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"\n'
    '  xmlns:xsd="http://www.w3.org/2001/XMLSchema#">\n'
    "<owl:Ontology/>\n"
)


def _consistent_fss(body: str) -> bool:
    return _consistent(load_ontology_from_string(FSS_HEADER + body + "\n)"))


def _consistent_rdf(body: str) -> bool:
    return _consistent(
        load_ontology_from_string(RDF_HEADER + body + "\n</rdf:RDF>", suffix=".rdf")
    )


def _consistent(axioms: list) -> bool:
    config = Configuration()
    config.throw_inconsistent_ontology_exception = False
    normalized = OWLNormalization().process_ontology(axioms)
    ontology = OWLClausification().clausify(normalized, ontology_iri="urn:test:fe")
    reasoner = Reasoner(ontology, config)
    try:
        return bool(reasoner.is_consistent())
    finally:
        reasoner.dispose()


class TestFunctionalSyntaxDataRestrictions:
    def test_min_max_facet_clash(self):
        assert not _consistent_fss(
            "SubClassOf(:A DataSomeValuesFrom(:dp"
            ' DatatypeRestriction(xsd:integer xsd:minInclusive "18"^^xsd:integer)))'
            " SubClassOf(:A DataAllValuesFrom(:dp"
            ' DatatypeRestriction(xsd:integer xsd:maxInclusive "10"^^xsd:integer)))'
            " ClassAssertion(:A :a)"
        )

    def test_min_max_facet_satisfiable(self):
        assert _consistent_fss(
            "SubClassOf(:A DataSomeValuesFrom(:dp"
            ' DatatypeRestriction(xsd:integer xsd:minInclusive "8"^^xsd:integer)))'
            " SubClassOf(:A DataAllValuesFrom(:dp"
            ' DatatypeRestriction(xsd:integer xsd:maxInclusive "10"^^xsd:integer)))'
            " ClassAssertion(:A :a)"
        )

    def test_one_of_outside_byte_range_clash(self):
        assert not _consistent_fss(
            "SubClassOf(:A DataAllValuesFrom(:dp xsd:byte))"
            " ClassAssertion(:A :a)"
            ' ClassAssertion(DataSomeValuesFrom(:dp DataOneOf("6542145"^^xsd:integer)) :a)'
        )

    def test_one_of_inside_byte_range_satisfiable(self):
        assert _consistent_fss(
            "SubClassOf(:A DataAllValuesFrom(:dp xsd:byte))"
            " ClassAssertion(:A :a)"
            ' ClassAssertion(DataSomeValuesFrom(:dp DataOneOf("42"^^xsd:integer)) :a)'
        )

    def test_data_complement_of_one_of_clash(self):
        assert not _consistent_fss(
            'SubClassOf(:A DataAllValuesFrom(:dp DataOneOf("3"^^xsd:integer "4"^^xsd:integer)))'
            ' SubClassOf(:A DataAllValuesFrom(:dp DataOneOf("2"^^xsd:integer "3"^^xsd:integer)))'
            " ClassAssertion(:A :a)"
            " ClassAssertion(DataSomeValuesFrom(:dp"
            ' DataComplementOf(DataOneOf("3"^^xsd:integer))) :a)'
        )

    def test_datetime_facet_clash(self):
        assert not _consistent_fss(
            'SubClassOf(:A DataHasValue(:dp "2007-10-08T20:44:11.656+01:00"^^xsd:dateTime))'
            " SubClassOf(:A DataAllValuesFrom(:dp DatatypeRestriction(xsd:dateTime"
            ' xsd:minInclusive "2008-07-08T20:44:11.656+01:00"^^xsd:dateTime'
            ' xsd:maxInclusive "2008-10-08T20:44:11.656+01:00"^^xsd:dateTime)))'
            " ClassAssertion(:A :a)"
        )

    def test_datetime_facet_satisfiable(self):
        assert _consistent_fss(
            'SubClassOf(:A DataHasValue(:dp "2008-08-08T20:44:11.656+01:00"^^xsd:dateTime))'
            " SubClassOf(:A DataAllValuesFrom(:dp DatatypeRestriction(xsd:dateTime"
            ' xsd:minInclusive "2008-07-08T20:44:11.656+01:00"^^xsd:dateTime'
            ' xsd:maxInclusive "2008-10-08T20:44:11.656+01:00"^^xsd:dateTime)))'
            " ClassAssertion(:A :a)"
        )

    def test_data_property_range_clash(self):
        assert not _consistent_fss(
            "DataPropertyRange(:hasAge xsd:integer)"
            ' ClassAssertion(DataHasValue(:hasAge "aString"^^xsd:string) :a)'
        )

    def test_data_property_range_satisfiable(self):
        assert _consistent_fss(
            "DataPropertyRange(:hasAge xsd:integer)"
            ' ClassAssertion(DataHasValue(:hasAge "18"^^xsd:integer) :a)'
        )

    def test_functional_data_property_clash(self):
        assert not _consistent_fss(
            "FunctionalDataProperty(:hasAge)"
            ' ClassAssertion(DataHasValue(:hasAge "18"^^xsd:integer) :a)'
            ' ClassAssertion(DataHasValue(:hasAge "19"^^xsd:integer) :a)'
        )

    def test_functional_data_property_same_value_satisfiable(self):
        assert _consistent_fss(
            "FunctionalDataProperty(:hasAge)"
            ' ClassAssertion(DataHasValue(:hasAge "18"^^xsd:integer) :a)'
            ' ClassAssertion(DataHasValue(:hasAge "18"^^xsd:integer) :a)'
        )

    def test_disjoint_data_properties_clash(self):
        assert not _consistent_fss(
            "DisjointDataProperties(:dp1 :dp2)"
            ' DataPropertyAssertion(:dp1 :a "10"^^xsd:integer)'
            " SubClassOf(:A DataSomeValuesFrom(:dp2 DatatypeRestriction(xsd:integer"
            ' xsd:minInclusive "10"^^xsd:integer xsd:maxInclusive "10"^^xsd:integer)))'
            " ClassAssertion(:A :a)"
        )

    def test_string_vs_integer_all_values_clash(self):
        assert not _consistent_fss(
            "SubClassOf(:A DataAllValuesFrom(:dp xsd:string))"
            " SubClassOf(:A DataSomeValuesFrom(:dp xsd:integer))"
            " ClassAssertion(:A :a)"
        )

    def test_data_min_cardinality_over_singleton_clash(self):
        assert not _consistent_fss(
            'SubClassOf(:A DataAllValuesFrom(:dp DataOneOf("3"^^xsd:integer)))'
            " SubClassOf(:A DataMinCardinality(2 :dp))"
            " ClassAssertion(:A :a)"
        )

    def test_data_has_value_subclass_clash(self):
        # DataHasValue in negative polarity: ¬DataHasValue(R, v) = ∀R.¬{v}.
        assert not _consistent_fss(
            'SubClassOf(DataHasValue(:hasAge "18"^^xsd:integer) :Eighteen)'
            ' ClassAssertion(DataHasValue(:hasAge "18"^^xsd:integer) :a)'
            " ClassAssertion(ObjectComplementOf(:Eighteen) :a)"
        )

    def test_data_has_value_subclass_satisfiable(self):
        assert _consistent_fss(
            'SubClassOf(DataHasValue(:hasAge "18"^^xsd:integer) :Eighteen)'
            ' ClassAssertion(DataHasValue(:hasAge "19"^^xsd:integer) :a)'
            " ClassAssertion(ObjectComplementOf(:Eighteen) :a)"
        )


class TestFunctionalSyntaxNegativeAssertions:
    def test_negative_data_property_assertion_clash(self):
        assert not _consistent_fss(
            'NegativeDataPropertyAssertion(:dp :a "5"^^xsd:integer)'
            ' DataPropertyAssertion(:dp :a "5"^^xsd:integer)'
        )

    def test_negative_data_property_assertion_satisfiable(self):
        assert _consistent_fss(
            'NegativeDataPropertyAssertion(:dp :a "5"^^xsd:integer)'
            ' DataPropertyAssertion(:dp :a "6"^^xsd:integer)'
        )

    def test_negative_object_property_assertion_clash(self):
        assert not _consistent_fss(
            "NegativeObjectPropertyAssertion(:r :a :b)"
            " ObjectPropertyAssertion(:r :a :b)"
        )

    def test_negative_object_property_assertion_satisfiable(self):
        assert _consistent_fss(
            "NegativeObjectPropertyAssertion(:r :a :b)"
            " ObjectPropertyAssertion(:r :a :c)"
        )

    def test_negative_assertion_with_forced_value_clash(self):
        # The dp filler must be 0 (the only enumerated owl:real member), but
        # the negative assertion forbids dp(a, 0).
        assert not _consistent_fss(
            "SubClassOf(:A DataAllValuesFrom(:dp owl:real))"
            " SubClassOf(:A"
            ' DataSomeValuesFrom(:dp DataOneOf("-INF"^^xsd:float "-0"^^xsd:integer)))'
            " ClassAssertion(:A :a)"
            ' NegativeDataPropertyAssertion(:dp :a "0"^^xsd:unsignedInt)'
        )


class TestRdfXmlDataRanges:
    def test_facet_restricted_float_clash(self):
        # No float exists strictly between 0.0 and the smallest positive float.
        assert not _consistent_rdf(
            '<owl:DatatypeProperty rdf:about="dp"/>'
            '<rdf:Description rdf:about="a"><rdf:type><owl:Restriction>'
            '<owl:onProperty rdf:resource="dp"/>'
            "<owl:someValuesFrom><rdfs:Datatype>"
            '<owl:onDatatype rdf:resource="http://www.w3.org/2001/XMLSchema#float"/>'
            '<owl:withRestrictions rdf:parseType="Collection">'
            "<rdf:Description>"
            '<xsd:minExclusive rdf:datatype="http://www.w3.org/2001/XMLSchema#float">0.0</xsd:minExclusive>'
            "</rdf:Description>"
            "<rdf:Description>"
            '<xsd:maxExclusive rdf:datatype="http://www.w3.org/2001/XMLSchema#float">1.401298464324817e-45</xsd:maxExclusive>'
            "</rdf:Description>"
            "</owl:withRestrictions>"
            "</rdfs:Datatype></owl:someValuesFrom>"
            "</owl:Restriction></rdf:type></rdf:Description>"
        )

    def test_facet_restricted_float_satisfiable(self):
        assert _consistent_rdf(
            '<owl:DatatypeProperty rdf:about="dp"/>'
            '<rdf:Description rdf:about="a"><rdf:type><owl:Restriction>'
            '<owl:onProperty rdf:resource="dp"/>'
            "<owl:someValuesFrom><rdfs:Datatype>"
            '<owl:onDatatype rdf:resource="http://www.w3.org/2001/XMLSchema#float"/>'
            '<owl:withRestrictions rdf:parseType="Collection">'
            "<rdf:Description>"
            '<xsd:minExclusive rdf:datatype="http://www.w3.org/2001/XMLSchema#float">0.0</xsd:minExclusive>'
            "</rdf:Description>"
            "<rdf:Description>"
            '<xsd:maxExclusive rdf:datatype="http://www.w3.org/2001/XMLSchema#float">2.0</xsd:maxExclusive>'
            "</rdf:Description>"
            "</owl:withRestrictions>"
            "</rdfs:Datatype></owl:someValuesFrom>"
            "</owl:Restriction></rdf:type></rdf:Description>"
        )


class TestRdfXmlNegativeAssertions:
    def test_negative_data_property_assertion_clash(self):
        assert not _consistent_rdf(
            '<owl:DatatypeProperty rdf:about="hasAge"/>'
            "<owl:NegativePropertyAssertion>"
            '<owl:sourceIndividual rdf:resource="Meg"/>'
            '<owl:assertionProperty rdf:resource="hasAge"/>'
            '<owl:targetValue rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">5</owl:targetValue>'
            "</owl:NegativePropertyAssertion>"
            '<rdf:Description rdf:about="Meg">'
            '<hasAge rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">5</hasAge>'
            "</rdf:Description>"
        )

    def test_negative_data_property_assertion_satisfiable(self):
        assert _consistent_rdf(
            '<owl:DatatypeProperty rdf:about="hasAge"/>'
            "<owl:NegativePropertyAssertion>"
            '<owl:sourceIndividual rdf:resource="Meg"/>'
            '<owl:assertionProperty rdf:resource="hasAge"/>'
            '<owl:targetValue rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">5</owl:targetValue>'
            "</owl:NegativePropertyAssertion>"
            '<rdf:Description rdf:about="Meg">'
            '<hasAge rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">6</hasAge>'
            "</rdf:Description>"
        )

    def test_negative_object_property_assertion_clash(self):
        assert not _consistent_rdf(
            '<owl:ObjectProperty rdf:about="hasSon"/>'
            "<owl:NegativePropertyAssertion>"
            '<owl:sourceIndividual rdf:resource="Peter"/>'
            '<owl:assertionProperty rdf:resource="hasSon"/>'
            '<owl:targetIndividual rdf:resource="Meg"/>'
            "</owl:NegativePropertyAssertion>"
            '<rdf:Description rdf:about="Peter"><hasSon rdf:resource="Meg"/></rdf:Description>'
        )


class TestBuiltInProperties:
    def test_bottom_data_property_clash(self):
        assert not _consistent_rdf(
            '<rdf:Description rdf:about="i"><rdf:type><owl:Restriction>'
            '<owl:onProperty rdf:resource="http://www.w3.org/2002/07/owl#bottomDataProperty"/>'
            '<owl:someValuesFrom rdf:resource="http://www.w3.org/2000/01/rdf-schema#Literal"/>'
            "</owl:Restriction></rdf:type></rdf:Description>"
        )

    def test_bottom_object_property_clash(self):
        assert not _consistent_rdf(
            '<rdf:Description rdf:about="i"><rdf:type><owl:Restriction>'
            '<owl:onProperty rdf:resource="http://www.w3.org/2002/07/owl#bottomObjectProperty"/>'
            '<owl:someValuesFrom rdf:resource="http://www.w3.org/2002/07/owl#Thing"/>'
            "</owl:Restriction></rdf:type></rdf:Description>"
        )

    def test_top_object_property_negated_existential_clash(self):
        assert not _consistent_rdf(
            '<rdf:Description rdf:about="i"><rdf:type><owl:Class><owl:complementOf>'
            "<owl:Restriction>"
            '<owl:onProperty rdf:resource="http://www.w3.org/2002/07/owl#topObjectProperty"/>'
            '<owl:someValuesFrom rdf:resource="http://www.w3.org/2002/07/owl#Thing"/>'
            "</owl:Restriction>"
            "</owl:complementOf></owl:Class></rdf:type></rdf:Description>"
        )

    def test_ordinary_existential_satisfiable(self):
        assert _consistent_rdf(
            '<owl:ObjectProperty rdf:about="r"/>'
            '<rdf:Description rdf:about="i"><rdf:type><owl:Restriction>'
            '<owl:onProperty rdf:resource="r"/>'
            '<owl:someValuesFrom rdf:resource="http://www.w3.org/2002/07/owl#Thing"/>'
            "</owl:Restriction></rdf:type></rdf:Description>"
        )

    def test_fss_bottom_object_property_clash(self):
        assert not _consistent_fss(
            "ClassAssertion(ObjectSomeValuesFrom(owl:bottomObjectProperty owl:Thing) :i)"
        )

    def test_fss_top_data_property_satisfiable(self):
        assert _consistent_fss(
            "ClassAssertion(DataSomeValuesFrom(owl:topDataProperty rdfs:Literal) :i)"
        )
