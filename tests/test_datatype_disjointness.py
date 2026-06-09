"""Cross-datatype disjointness and value-kind tests.

Datatypes managed by different handlers have pairwise disjoint value spaces
(string vs numeric, float vs owl:real, dateTime vs anything else, ...);
within one handler family the handler decides.
"""

from __future__ import annotations

from hermit.configuration import Configuration
from hermit.datatypes.registry import DatatypeRegistry
from hermit.model import (
    Atom,
    AtLeastDataRange,
    AtomicConcept,
    AtomicRole,
    Constant,
    ConstantEnumeration,
    DatatypeRestriction,
    DLClause,
    DLOntology,
    Individual,
    Inequality,
    Variable,
)
from hermit.reasoner import Reasoner

XSD = "http://www.w3.org/2001/XMLSchema#"
OWL = "http://www.w3.org/2002/07/owl#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

X = Variable.create("X")
Y = Variable.create("Y")


def _is_consistent(clauses: list[DLClause], facts: list[Atom]) -> bool:
    onto = DLOntology(
        "urn:test:disjoint", frozenset(clauses), frozenset(facts), frozenset()
    )
    config = Configuration()
    config.throw_inconsistent_ontology_exception = False
    reasoner = Reasoner(onto, config)
    try:
        return bool(reasoner.is_consistent())
    finally:
        reasoner.dispose()


def _plain(datatype_iri: str) -> DatatypeRestriction:
    return DatatypeRestriction.create(datatype_iri, (), ())


def _all_vs_some(all_iri: str, some_iri: str) -> tuple[list[DLClause], list[Atom]]:
    a_concept = AtomicConcept.create("urn:test:A")
    dp = AtomicRole.create("urn:test:dp")
    individual = Individual.create("urn:test:a")
    clauses = [
        DLClause.create(
            (Atom.create(_plain(all_iri), Y),),
            (Atom.create(a_concept, X), Atom.create(dp, X, Y)),
        ),
        DLClause.create(
            (Atom.create(AtLeastDataRange.create(1, dp, _plain(some_iri)), X),),
            (Atom.create(a_concept, X),),
        ),
    ]
    facts = [Atom.create(a_concept, individual)]
    return clauses, facts


class TestCrossFamilyDisjointness:
    def test_string_vs_integer_is_inconsistent(self):
        clauses, facts = _all_vs_some(XSD + "string", XSD + "integer")
        assert not _is_consistent(clauses, facts)

    def test_string_vs_string_is_consistent(self):
        clauses, facts = _all_vs_some(XSD + "string", XSD + "string")
        assert _is_consistent(clauses, facts)

    def test_float_vs_owl_real_is_inconsistent(self):
        clauses, facts = _all_vs_some(OWL + "real", XSD + "float")
        assert not _is_consistent(clauses, facts)

    def test_float_vs_double_is_inconsistent(self):
        clauses, facts = _all_vs_some(XSD + "double", XSD + "float")
        assert not _is_consistent(clauses, facts)

    def test_integer_vs_decimal_is_consistent(self):
        clauses, facts = _all_vs_some(XSD + "decimal", XSD + "integer")
        assert _is_consistent(clauses, facts)

    def test_date_time_vs_integer_is_inconsistent(self):
        clauses, facts = _all_vs_some(XSD + "dateTime", XSD + "integer")
        assert not _is_consistent(clauses, facts)

    def test_string_typed_value_outside_integer_range(self):
        # ∀dp.integer ⊓ ∃dp.{"aString"^^xsd:string} is unsatisfiable.
        a_concept = AtomicConcept.create("urn:test:A")
        dp = AtomicRole.create("urn:test:dp")
        individual = Individual.create("urn:test:a")
        string_value = ConstantEnumeration.create(
            [Constant.create("aString", XSD + "string")]
        )
        clauses = [
            DLClause.create(
                (Atom.create(_plain(XSD + "integer"), Y),),
                (Atom.create(a_concept, X), Atom.create(dp, X, Y)),
            ),
            DLClause.create(
                (Atom.create(AtLeastDataRange.create(1, dp, string_value), X),),
                (Atom.create(a_concept, X),),
            ),
        ]
        facts = [Atom.create(a_concept, individual)]
        assert not _is_consistent(clauses, facts)


class TestNegativeDataPropertyAssertion:
    def test_asserted_and_negated_same_value_clash(self):
        # dp(a, "5"^^integer) together with ¬dp(a, "5"^^integer).
        dp = AtomicRole.create("urn:test:dp")
        individual = Individual.create("urn:test:a")
        five = Constant.create("5", XSD + "integer")
        onto = DLOntology(
            "urn:test:negdp",
            frozenset(),
            frozenset({Atom.create(dp, individual, five)}),
            frozenset({Atom.create(dp, individual, five)}),
        )
        config = Configuration()
        config.throw_inconsistent_ontology_exception = False
        reasoner = Reasoner(onto, config)
        try:
            assert not reasoner.is_consistent()
        finally:
            reasoner.dispose()

    def test_asserted_and_negated_different_values_consistent(self):
        dp = AtomicRole.create("urn:test:dp")
        individual = Individual.create("urn:test:a")
        five = Constant.create("5", XSD + "integer")
        six = Constant.create("6", XSD + "integer")
        onto = DLOntology(
            "urn:test:negdp2",
            frozenset(),
            frozenset({Atom.create(dp, individual, five)}),
            frozenset({Atom.create(dp, individual, six)}),
        )
        config = Configuration()
        config.throw_inconsistent_ontology_exception = False
        reasoner = Reasoner(onto, config)
        try:
            assert reasoner.is_consistent()
        finally:
            reasoner.dispose()


class TestDisjointDataProperties:
    def _case(self, lexical1: str, lexical2: str) -> bool:
        # dp1(a, v1), A ⊑ ∃dp2.{v2}, dp1 disjoint dp2 (encoded as the
        # DL clause dp1(X,Y) ∧ dp2(X,Z) → Y ≠ Z applied pairwise).
        a_concept = AtomicConcept.create("urn:test:A")
        dp1 = AtomicRole.create("urn:test:dp1")
        dp2 = AtomicRole.create("urn:test:dp2")
        individual = Individual.create("urn:test:a")
        value1 = Constant.create(lexical1, XSD + "integer")
        value2 = ConstantEnumeration.create(
            [Constant.create(lexical2, XSD + "integer")]
        )
        z_var = Variable.create("Z")
        clauses = [
            DLClause.create(
                (Atom.create(AtLeastDataRange.create(1, dp2, value2), X),),
                (Atom.create(a_concept, X),),
            ),
            DLClause.create(
                (Atom.create(Inequality.INSTANCE, Y, z_var),),
                (Atom.create(dp1, X, Y), Atom.create(dp2, X, z_var)),
            ),
        ]
        facts = [
            Atom.create(a_concept, individual),
            Atom.create(dp1, individual, value1),
        ]
        return _is_consistent(clauses, facts)

    def test_same_value_in_disjoint_properties_is_inconsistent(self):
        assert not self._case("10", "10")

    def test_different_values_in_disjoint_properties_is_consistent(self):
        assert self._case("10", "11")


class TestValueKinds:
    def test_anyuri_value_distinct_from_string(self):
        uri_value = DatatypeRegistry.parse_literal("http://x", XSD + "anyURI")
        string_value = DatatypeRegistry.parse_literal("http://x", XSD + "string")
        assert uri_value != string_value
        assert string_value != uri_value

    def test_xml_literal_value_distinct_from_string(self):
        xml_value = DatatypeRegistry.parse_literal("<x/>", RDF + "XMLLiteral")
        string_value = DatatypeRegistry.parse_literal("<x/>", XSD + "string")
        assert xml_value != string_value

    def test_hex_and_base64_values_distinct(self):
        hex_value = DatatypeRegistry.parse_literal("0102", XSD + "hexBinary")
        base64_value = DatatypeRegistry.parse_literal("AQI=", XSD + "base64Binary")
        # Same octets but distinct binary datatypes.
        assert hex_value != base64_value

    def test_boolean_not_equal_to_integer_one(self):
        bool_value = DatatypeRegistry.parse_literal("true", XSD + "boolean")
        int_value = DatatypeRegistry.parse_literal("1", XSD + "integer")
        assert bool_value != int_value

    def test_registry_disjointness_matrix(self):
        assert DatatypeRegistry.is_disjoint_with(XSD + "string", XSD + "anyURI")
        assert DatatypeRegistry.is_disjoint_with(XSD + "float", XSD + "double")
        assert DatatypeRegistry.is_disjoint_with(XSD + "float", OWL + "real")
        assert DatatypeRegistry.is_disjoint_with(XSD + "hexBinary", XSD + "base64Binary")
        assert not DatatypeRegistry.is_disjoint_with(XSD + "string", RDF + "PlainLiteral")
        assert not DatatypeRegistry.is_disjoint_with(XSD + "byte", XSD + "unsignedByte")
        assert DatatypeRegistry.is_disjoint_with(
            XSD + "negativeInteger", XSD + "positiveInteger"
        )

    def test_registry_subset_matrix(self):
        assert DatatypeRegistry.is_subset_of(XSD + "string", RDF + "PlainLiteral")
        assert DatatypeRegistry.is_subset_of(XSD + "NCName", XSD + "Name")
        assert DatatypeRegistry.is_subset_of(XSD + "dateTimeStamp", XSD + "dateTime")
        assert not DatatypeRegistry.is_subset_of(XSD + "dateTime", XSD + "dateTimeStamp")
        assert DatatypeRegistry.is_subset_of(XSD + "unsignedByte", XSD + "unsignedShort")
        assert not DatatypeRegistry.is_subset_of(XSD + "integer", XSD + "string")
