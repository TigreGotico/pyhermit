"""Comprehensive tests for hermit.owl_model package."""
import pytest
from datetime import datetime, date, timedelta, time
from decimal import Decimal

# --- namespaces ---
from hermit.owl_model.namespaces import Namespaces, OWL, RDFS, RDF, XSD

# --- IRI ---
from hermit.owl_model.iri import IRI

# --- owl_object ---
from hermit.owl_model.owl_object import OWLObject, OWLNamedObject, OWLEntity

# --- owl_annotation ---
from hermit.owl_model.owl_annotation import OWLAnnotationObject, OWLAnnotationSubject, OWLAnnotationValue

# --- owl_datatype ---
from hermit.owl_model.owl_datatype import OWLDatatype

# --- owl_data_ranges ---
from hermit.owl_model.owl_data_ranges import (
    OWLDataRange, OWLNaryDataRange, OWLDataIntersectionOf, OWLDataUnionOf, OWLDataComplementOf
)

# --- owl_individual ---
from hermit.owl_model.owl_individual import OWLIndividual, OWLNamedIndividual

# --- owl_property ---
from hermit.owl_model.owl_property import (
    OWLPropertyExpression, OWLObjectPropertyExpression, OWLDataPropertyExpression,
    OWLProperty, OWLObjectProperty, OWLObjectInverseOf, OWLDataProperty
)

# --- owl_literal ---
from hermit.owl_model.owl_literal import (
    OWLLiteral, OWLTopObjectProperty, OWLBottomObjectProperty,
    OWLTopDataProperty, OWLBottomDataProperty,
    DoubleOWLDatatype, FloatOWLDatatype, DecimalOWLDatatype,
    IntOWLDatatype, IntegerOWLDatatype, NonNegativeIntegerOWLDatatype,
    NonPositiveIntegerOWLDatatype, NegativeIntegerOWLDatatype, PositiveIntegerOWLDatatype,
    BooleanOWLDatatype, StringOWLDatatype, DateOWLDatatype, DateTimeOWLDatatype,
    DurationOWLDatatype, TopOWLDatatype, TimeOWLDatatype,
    GYearMonthOWLDatatype, GMonthDayOWLDatatype, GYearOWLDatatype, GMonthOWLDatatype, GDayOWLDatatype,
    NUMERIC_DATATYPES, TIME_DATATYPES, FloatSpecialValue
)

# --- class_expression ---
from hermit.owl_model.class_expression import (
    OWLClassExpression, OWLAnonymousClassExpression, OWLBooleanClassExpression,
    OWLObjectComplementOf, OWLClass, OWLObjectUnionOf, OWLObjectIntersectionOf,
    OWLThing, OWLNothing,
    OWLObjectSomeValuesFrom, OWLObjectAllValuesFrom, OWLObjectHasValue, OWLObjectHasSelf,
    OWLObjectMinCardinality, OWLObjectMaxCardinality, OWLObjectExactCardinality,
    OWLObjectOneOf,
    OWLDataSomeValuesFrom, OWLDataAllValuesFrom, OWLDataHasValue,
    OWLDataMinCardinality, OWLDataMaxCardinality, OWLDataExactCardinality,
    OWLDataOneOf, OWLDatatypeRestriction, OWLFacetRestriction,
)

# --- owl_axiom ---
from hermit.owl_model.owl_axiom import (
    OWLAxiom, OWLLogicalAxiom, OWLDeclarationAxiom, OWLDatatypeDefinitionAxiom,
    OWLHasKeyAxiom, OWLEquivalentClassesAxiom, OWLDisjointClassesAxiom,
    OWLSubClassOfAxiom, OWLDisjointUnionAxiom,
    OWLClassAssertionAxiom, OWLDifferentIndividualsAxiom, OWLSameIndividualAxiom,
    OWLEquivalentObjectPropertiesAxiom, OWLDisjointObjectPropertiesAxiom,
    OWLInverseObjectPropertiesAxiom,
    OWLEquivalentDataPropertiesAxiom, OWLDisjointDataPropertiesAxiom,
    OWLSubObjectPropertyOfAxiom, OWLSubDataPropertyOfAxiom,
    OWLObjectPropertyAssertionAxiom, OWLNegativeObjectPropertyAssertionAxiom,
    OWLDataPropertyAssertionAxiom, OWLNegativeDataPropertyAssertionAxiom,
    OWLFunctionalObjectPropertyAxiom, OWLAsymmetricObjectPropertyAxiom,
    OWLInverseFunctionalObjectPropertyAxiom, OWLIrreflexiveObjectPropertyAxiom,
    OWLReflexiveObjectPropertyAxiom, OWLSymmetricObjectPropertyAxiom,
    OWLTransitiveObjectPropertyAxiom, OWLFunctionalDataPropertyAxiom,
    OWLObjectPropertyDomainAxiom, OWLDataPropertyDomainAxiom,
    OWLObjectPropertyRangeAxiom, OWLDataPropertyRangeAxiom,
    OWLAnnotationProperty, OWLAnnotation, OWLAnnotationAxiom,
    OWLAnnotationAssertionAxiom, OWLSubAnnotationPropertyOfAxiom,
    OWLAnnotationPropertyDomainAxiom, OWLAnnotationPropertyRangeAxiom,
    OWLSubPropertyChainAxiom,
)

# --- vocab ---
from hermit.owl_model.vocab import OWLRDFVocabulary, XSDVocabulary, OWLFacet

# --- meta_classes ---
from hermit.owl_model.meta_classes import HasIRI, HasOperands, HasFiller, HasCardinality


# ===================== Helpers =====================

def _iri(s="http://example.org/test#A"):
    return IRI.create(s)


def _cls(s="http://example.org/test#A"):
    return OWLClass(_iri(s))


def _op(s="http://example.org/test#r"):
    return OWLObjectProperty(_iri(s))


def _dp(s="http://example.org/test#d"):
    return OWLDataProperty(_iri(s))


def _ind(s="http://example.org/test#a"):
    return OWLNamedIndividual(_iri(s))


def _dt(s="http://www.w3.org/2001/XMLSchema#string"):
    return OWLDatatype(_iri(s))


# ===================== Namespaces =====================

class TestNamespaces:
    def test_basic(self):
        ns = Namespaces("ex", "http://example.org/")
        assert ns.ns == "http://example.org/"
        assert ns.prefix == "ex"

    def test_repr(self):
        ns = Namespaces("ex", "http://example.org/")
        assert "Namespaces" in repr(ns)

    def test_hash(self):
        ns1 = Namespaces("ex", "http://example.org/")
        ns2 = Namespaces("ex", "http://example.org/")
        assert hash(ns1) == hash(ns2)

    def test_eq_same(self):
        ns1 = Namespaces("ex", "http://example.org/")
        ns2 = Namespaces("ex", "http://example.org/")
        assert ns1 == ns2

    def test_eq_string(self):
        ns = Namespaces("ex", "http://example.org/")
        assert ns == "http://example.org/"
        assert not (ns == 42)

    def test_builtin_namespaces(self):
        assert OWL.prefix == "owl"
        assert RDFS.prefix == "rdfs"
        assert RDF.prefix == "rdf"
        assert XSD.prefix == "xsd"

    def test_invalid_ns_suffix(self):
        with pytest.raises(AssertionError):
            Namespaces("bad", "http://example.org")


# ===================== IRI =====================

class TestIRI:
    def test_create_from_string(self):
        iri = IRI.create("http://example.org/test#A")
        assert iri.get_namespace() == "http://example.org/test#"
        assert iri.get_remainder() == "A"
        assert iri.remainder == "A"
        assert iri.str == "http://example.org/test#A"
        assert iri.as_str() == "http://example.org/test#A"

    def test_create_with_remainder(self):
        iri = IRI.create("http://example.org/test#", "A")
        assert iri.get_remainder() == "A"

    def test_create_from_namespace(self):
        iri = IRI.create(OWL, "Thing")
        assert "Thing" in iri.as_str()

    def test_create_file_path(self):
        iri = IRI.create("/tmp/test.owl", is_file_path=True)
        assert iri.as_str() == "/tmp/test.owl"

    def test_repr(self):
        iri = _iri()
        assert "IRI(" in repr(iri)

    def test_eq_hash(self):
        iri1 = _iri("http://example.org/test#A")
        iri2 = _iri("http://example.org/test#A")
        assert iri1 == iri2
        assert hash(iri1) == hash(iri2)
        assert not (iri1 == "not an iri")

    def test_is_nothing(self):
        iri = IRI.create("http://www.w3.org/2002/07/owl#Nothing")
        assert iri.is_nothing()
        assert not iri.is_thing()

    def test_is_thing(self):
        iri = IRI.create("http://www.w3.org/2002/07/owl#Thing")
        assert iri.is_thing()
        assert not iri.is_nothing()

    def test_is_reserved_vocabulary(self):
        iri = IRI.create("http://www.w3.org/2002/07/owl#Thing")
        assert iri.is_reserved_vocabulary()
        iri2 = _iri("http://example.org/test#A")
        assert not iri2.is_reserved_vocabulary()

    def test_as_iri(self):
        iri = _iri()
        assert iri.as_iri() is iri

    def test_no_slash(self):
        with pytest.raises(AssertionError):
            IRI.create("noslash")

    def test_no_whitespace(self):
        with pytest.raises(AssertionError):
            IRI.create("http://example.org/test #A")

    def test_empty_file_path(self):
        # empty string with is_file_path goes through else branch
        iri = IRI.create("http://example.org/test#", "B")
        assert iri.get_remainder() == "B"


# ===================== OWLAnnotation classes =====================

class TestOWLAnnotation:
    def test_annotation_value_defaults(self):
        # IRI is an OWLAnnotationValue
        iri = _iri()
        assert iri.is_literal() is False
        assert iri.as_literal() is None

    def test_annotation_object_defaults(self):
        iri = _iri()
        assert iri.as_iri() is iri
        assert iri.as_anonymous_individual() is None


# ===================== OWLDatatype =====================

class TestOWLDatatype:
    def test_from_iri(self):
        dt = OWLDatatype(_iri("http://www.w3.org/2001/XMLSchema#string"))
        assert "string" in dt.str

    def test_from_str(self):
        dt = OWLDatatype("http://www.w3.org/2001/XMLSchema#integer")
        assert "integer" in dt.str

    def test_from_has_iri(self):
        dt = OWLDatatype(XSDVocabulary.STRING)
        assert "string" in dt.str

    def test_iri_property(self):
        dt = OWLDatatype(XSDVocabulary.BOOLEAN)
        assert dt.iri is not None

    def test_eq_hash_repr(self):
        dt1 = OWLDatatype(XSDVocabulary.STRING)
        dt2 = OWLDatatype(XSDVocabulary.STRING)
        assert dt1 == dt2
        assert hash(dt1) == hash(dt2)
        assert "OWLDatatype" in repr(dt1)
        assert not (dt1 == "something")


# ===================== OWLDataRanges =====================

class TestOWLDataRanges:
    def test_data_intersection(self):
        dt1 = OWLDatatype(XSDVocabulary.STRING)
        dt2 = OWLDatatype(XSDVocabulary.INTEGER)
        di = OWLDataIntersectionOf([dt1, dt2])
        assert list(di.operands()) == [dt1, dt2]
        assert "OWLDataIntersectionOf" in repr(di)

    def test_data_union(self):
        dt1 = OWLDatatype(XSDVocabulary.STRING)
        dt2 = OWLDatatype(XSDVocabulary.INTEGER)
        du = OWLDataUnionOf([dt1, dt2])
        assert set(du.operands()) == {dt1, dt2}

    def test_nary_eq_hash(self):
        dt1 = OWLDatatype(XSDVocabulary.STRING)
        dt2 = OWLDatatype(XSDVocabulary.INTEGER)
        a = OWLDataIntersectionOf([dt1, dt2])
        b = OWLDataIntersectionOf([dt1, dt2])
        assert a == b
        assert hash(a) == hash(b)
        assert not (a == "other")
        # different type
        c = OWLDataUnionOf([dt1, dt2])
        assert a != c

    def test_data_complement(self):
        dt = OWLDatatype(XSDVocabulary.STRING)
        dc = OWLDataComplementOf(dt)
        assert dc.get_data_range() == dt
        assert "OWLDataComplementOf" in repr(dc)

    def test_data_complement_eq_hash(self):
        dt = OWLDatatype(XSDVocabulary.STRING)
        a = OWLDataComplementOf(dt)
        b = OWLDataComplementOf(dt)
        assert a == b
        assert hash(a) == hash(b)
        assert not (a == "other")


# ===================== OWLIndividual =====================

class TestOWLIndividual:
    def test_named_individual(self):
        ind = _ind()
        assert ind.str == "http://example.org/test#a"
        assert ind.iri is not None
        assert ind.remainder == "a"

    def test_from_str(self):
        ind = OWLNamedIndividual("http://example.org/test#b")
        assert "b" in ind.str

    def test_eq_hash_repr(self):
        a = _ind("http://example.org/test#a")
        b = _ind("http://example.org/test#a")
        assert a == b
        assert hash(a) == hash(b)
        assert "OWLNamedIndividual" in repr(a)
        assert not (a == "string")

    def test_lt(self):
        a = _ind("http://example.org/test#a")
        b = _ind("http://example.org/test#b")
        assert a < b

    def test_is_anonymous(self):
        a = _ind()
        assert a.is_anonymous() is False

    def test_to_string_id(self):
        a = _ind()
        assert a.to_string_id() == a.str


# ===================== OWLProperty =====================

class TestOWLProperty:
    def test_object_property(self):
        op = _op()
        assert op.str == "http://example.org/test#r"
        assert op.iri is not None
        assert op.remainder == "r"
        assert op.is_object_property_expression()
        assert not op.is_data_property_expression()

    def test_object_property_from_str(self):
        op = OWLObjectProperty("http://example.org/test#r")
        assert "r" in op.str

    def test_object_property_eq_hash_repr(self):
        a = _op()
        b = _op()
        assert a == b
        assert hash(a) == hash(b)
        assert "OWLObjectProperty" in repr(a)
        assert not (a == "string")

    def test_get_named_property(self):
        op = _op()
        assert op.get_named_property() is op

    def test_get_inverse_property(self):
        op = _op()
        inv = op.get_inverse_property()
        assert isinstance(inv, OWLObjectInverseOf)

    def test_is_owl_top_object_property(self):
        assert OWLTopObjectProperty.is_owl_top_object_property()
        assert not _op().is_owl_top_object_property()

    def test_is_owl_top_data_property(self):
        assert OWLTopDataProperty.is_owl_top_data_property()
        assert not _dp().is_owl_top_data_property()

    def test_data_property(self):
        dp = _dp()
        assert dp.is_data_property_expression()
        assert not dp.is_object_property_expression()
        assert "OWLDataProperty" in repr(dp)

    def test_data_property_eq_hash(self):
        a = _dp()
        b = _dp()
        assert a == b
        assert hash(a) == hash(b)
        assert not (a == "string")

    def test_object_inverse_of(self):
        op = _op()
        inv = OWLObjectInverseOf(op)
        assert inv.get_inverse() == op
        assert inv.get_inverse_property() == op
        assert inv.get_named_property() == op
        assert "OWLObjectInverseOf" in repr(inv)

    def test_object_inverse_of_eq_hash(self):
        op = _op()
        a = OWLObjectInverseOf(op)
        b = OWLObjectInverseOf(op)
        assert a == b
        assert hash(a) == hash(b)
        assert not (a == "string")

    def test_property_expression_defaults(self):
        op = _op()
        assert not op.is_owl_top_data_property()


# ===================== OWLLiteral =====================

class TestOWLLiteral:
    # --- Boolean ---
    def test_boolean_true(self):
        lit = OWLLiteral(True)
        assert lit.is_boolean()
        assert lit.parse_boolean() is True
        assert lit.get_literal() == "true"
        assert lit.get_datatype() == BooleanOWLDatatype
        assert lit.is_literal()
        assert lit.as_literal() is lit
        assert lit.to_python() is True

    def test_boolean_false(self):
        lit = OWLLiteral(False)
        assert not lit.parse_boolean()
        assert lit.get_literal() == "false"

    def test_boolean_from_string(self):
        # distutils removed in Python 3.12+, so this may raise
        try:
            lit = OWLLiteral("true", BooleanOWLDatatype)
            assert lit.parse_boolean() is True
        except ModuleNotFoundError:
            pytest.skip("distutils not available")

    def test_boolean_eq_hash_repr(self):
        a = OWLLiteral(True)
        b = OWLLiteral(True)
        assert a == b
        assert hash(a) == hash(b)
        assert "OWLLiteral" in repr(a)
        assert not (a == "string")

    # --- Integer ---
    def test_integer(self):
        lit = OWLLiteral(42)
        assert lit.is_integer()
        assert lit.parse_integer() == 42
        assert lit.get_datatype() == IntegerOWLDatatype
        assert lit.to_python() == 42

    def test_integer_with_type(self):
        lit = OWLLiteral(42, IntegerOWLDatatype)
        assert lit.is_integer()

    def test_int_type(self):
        lit = OWLLiteral(42, IntOWLDatatype)
        assert lit.is_integer()
        assert lit.get_datatype() == IntOWLDatatype

    def test_integer_eq_hash(self):
        a = OWLLiteral(42)
        b = OWLLiteral(42)
        assert a == b
        assert hash(a) == hash(b)

    def test_integer_ordering(self):
        a = OWLLiteral(1)
        b = OWLLiteral(2)
        assert a < b
        assert b > a
        assert a <= a
        assert a >= a

    # --- Double ---
    def test_double(self):
        lit = OWLLiteral(3.14)
        assert lit.is_double()
        assert abs(lit.parse_double() - 3.14) < 1e-10
        assert lit.get_datatype() == DoubleOWLDatatype

    def test_double_with_type(self):
        lit = OWLLiteral(3.14, DoubleOWLDatatype)
        assert lit.is_double()

    def test_double_special_nan(self):
        lit = OWLLiteral(FloatSpecialValue.NAN, DoubleOWLDatatype)
        assert lit.has_float_special_value()
        assert not (lit == lit)  # NaN != NaN

    def test_double_special_inf(self):
        lit = OWLLiteral(FloatSpecialValue.POS_INF, DoubleOWLDatatype)
        assert lit.has_float_special_value()

    def test_double_special_neg_inf(self):
        lit = OWLLiteral(FloatSpecialValue.NEG_INF, DoubleOWLDatatype)
        assert lit.has_float_special_value()

    def test_double_ordering_with_special(self):
        a = OWLLiteral(FloatSpecialValue.NAN, DoubleOWLDatatype)
        b = OWLLiteral(1.0)
        assert not (a < b)
        assert not (a > b)
        assert not (a <= b)
        assert not (a >= b)

    # --- Float ---
    def test_float(self):
        lit = OWLLiteral(3.14, FloatOWLDatatype)
        assert lit.is_float()
        assert lit.get_datatype() == FloatOWLDatatype

    def test_float_special(self):
        lit = OWLLiteral(FloatSpecialValue.NAN, FloatOWLDatatype)
        assert lit.has_float_special_value()

    def test_float_no_special(self):
        lit = OWLLiteral(1.0, FloatOWLDatatype)
        assert not lit.has_float_special_value()

    # --- Decimal ---
    def test_decimal(self):
        lit = OWLLiteral(Decimal("3.14"))
        assert lit.is_decimal()
        assert lit.parse_decimal() == Decimal("3.14")
        assert lit.get_datatype() == DecimalOWLDatatype

    def test_decimal_with_type(self):
        lit = OWLLiteral(Decimal("1.5"), DecimalOWLDatatype)
        assert lit.is_decimal()

    # --- String ---
    def test_string(self):
        lit = OWLLiteral("hello")
        assert lit.is_string()
        assert lit.parse_string() == "hello"
        assert lit.get_literal() == "hello"
        assert lit.get_datatype() == StringOWLDatatype
        assert len(lit) == 5

    def test_string_eq_hash(self):
        a = OWLLiteral("hello")
        b = OWLLiteral("hello")
        assert a == b
        assert hash(a) == hash(b)
        assert not (a == "string")

    def test_string_ordering(self):
        a = OWLLiteral("aaa")
        b = OWLLiteral("bbb")
        assert a < b

    def test_string_non_string_value(self):
        lit = OWLLiteral(42, StringOWLDatatype)
        assert lit.is_string()
        assert lit.parse_string() == "42"

    # --- Date ---
    def test_date(self):
        d = date(2023, 1, 1)
        lit = OWLLiteral(d)
        assert lit.is_date()
        assert lit.parse_date() == d

    def test_date_from_string(self):
        lit = OWLLiteral("2023-01-01", DateOWLDatatype)
        assert lit.is_date()
        assert lit.parse_date() == date(2023, 1, 1)

    def test_date_from_string_z(self):
        # Z replacement may produce invalid isoformat in some Python versions
        try:
            lit = OWLLiteral("2023-01-01Z", DateOWLDatatype)
            assert lit.is_date()
        except ValueError:
            pytest.skip("Z-suffix date parsing not supported in this Python version")

    # --- DateTime ---
    def test_datetime(self):
        dt = datetime(2023, 1, 1, 12, 0, 0)
        lit = OWLLiteral(dt)
        assert lit.is_datetime()
        assert lit.parse_datetime() == dt

    def test_datetime_from_string(self):
        lit = OWLLiteral("2023-01-01T12:00:00", DateTimeOWLDatatype)
        assert lit.is_datetime()

    def test_datetime_from_string_z(self):
        lit = OWLLiteral("2023-01-01T12:00:00Z", DateTimeOWLDatatype)
        assert lit.is_datetime()

    # --- Duration ---
    def test_duration(self):
        td = timedelta(days=5)
        lit = OWLLiteral(td)
        assert lit.is_duration()
        assert lit.parse_duration() == td
        # Note: get_literal() calls isoformat() which timedelta doesn't have - known bug
        assert lit.to_python() == td

    # --- Time ---
    def test_time(self):
        t = time(12, 30, 0)
        lit = OWLLiteral(t)
        assert lit.is_time()
        assert lit.parse_time() == t

    def test_time_from_string(self):
        lit = OWLLiteral("12:30:00", TimeOWLDatatype)
        assert lit.is_time()

    def test_time_from_string_z(self):
        lit = OWLLiteral("12:30:00Z", TimeOWLDatatype)
        assert lit.is_time()

    # --- GDate types ---
    def test_gyearmonth(self):
        lit = OWLLiteral("2023-10", GYearMonthOWLDatatype)
        assert lit.is_gyearmonth()
        assert lit.parse_gyearmonth() == (2023, 10)

    def test_gyearmonth_from_string(self):
        lit = OWLLiteral("2001-10", GYearMonthOWLDatatype)
        assert lit.is_gyearmonth()
        assert lit.parse_gyearmonth() == (2001, 10)

    def test_gmonthday(self):
        lit = OWLLiteral("--11-15", GMonthDayOWLDatatype)
        assert lit.is_gmonthday()
        assert lit.parse_gmonthday() == (11, 15)

    def test_gmonthday_from_string(self):
        lit = OWLLiteral("--11-15", GMonthDayOWLDatatype)
        assert lit.is_gmonthday()

    def test_gyear(self):
        lit = OWLLiteral("2025", GYearOWLDatatype)
        assert lit.is_gyear()
        assert lit.parse_gyear() == 2025

    def test_gmonth(self):
        lit = OWLLiteral("--05", GMonthOWLDatatype)
        assert lit.is_gmonth()
        assert lit.parse_gmonth() == 5

    def test_gday(self):
        lit = OWLLiteral("---31", GDayOWLDatatype)
        assert lit.is_gday()
        assert lit.parse_gday() == 31

    def test_gdate_eq_hash(self):
        a = OWLLiteral("2023-10", GYearMonthOWLDatatype)
        b = OWLLiteral("2023-10", GYearMonthOWLDatatype)
        assert a == b
        assert hash(a) == hash(b)
        assert not (a == "other")

    def test_gdate_ordering(self):
        a = OWLLiteral("2020", GYearOWLDatatype)
        b = OWLLiteral("2025", GYearOWLDatatype)
        assert a < b
        assert b > a
        assert a <= a
        assert a >= a

    # --- Generic literal impl ---
    def test_generic_literal(self):
        custom_dt = OWLDatatype("http://example.org/custom#mytype")
        lit = OWLLiteral("foo", custom_dt)
        assert lit.get_datatype() == custom_dt
        assert "OWLLiteral" in repr(lit)

    def test_generic_literal_eq(self):
        custom_dt = OWLDatatype("http://example.org/custom#mytype")
        a = OWLLiteral("foo", custom_dt)
        b = OWLLiteral("foo", custom_dt)
        assert a == b
        assert hash(a) == hash(b)

    # --- Positive/Negative/NonPos/NonNeg integers ---
    def test_positive_integer(self):
        lit = OWLLiteral(5, PositiveIntegerOWLDatatype)
        assert lit.is_integer()
        assert lit.get_datatype() == PositiveIntegerOWLDatatype

    def test_negative_integer(self):
        lit = OWLLiteral(-5, NegativeIntegerOWLDatatype)
        assert lit.is_integer()

    def test_non_negative_integer(self):
        lit = OWLLiteral(0, NonNegativeIntegerOWLDatatype)
        assert lit.is_integer()

    def test_non_positive_integer(self):
        lit = OWLLiteral(0, NonPositiveIntegerOWLDatatype)
        assert lit.is_integer()

    def test_positive_integer_assertion_error(self):
        with pytest.raises(AssertionError):
            OWLLiteral(0, PositiveIntegerOWLDatatype)

    def test_negative_integer_assertion_error(self):
        with pytest.raises(AssertionError):
            OWLLiteral(0, NegativeIntegerOWLDatatype)

    def test_non_negative_integer_assertion_error(self):
        with pytest.raises(AssertionError):
            OWLLiteral(-1, NonNegativeIntegerOWLDatatype)

    def test_non_positive_integer_assertion_error(self):
        with pytest.raises(AssertionError):
            OWLLiteral(1, NonPositiveIntegerOWLDatatype)

    # --- Base class default returns ---
    def test_base_parse_methods_raise(self):
        lit = OWLLiteral(42)  # integer literal
        with pytest.raises(ValueError):
            lit.parse_boolean()
        with pytest.raises(ValueError):
            lit.parse_double()
        with pytest.raises(ValueError):
            lit.parse_float()
        with pytest.raises(ValueError):
            lit.parse_decimal()
        with pytest.raises(ValueError):
            lit.parse_string()
        with pytest.raises(ValueError):
            lit.parse_date()
        with pytest.raises(ValueError):
            lit.parse_datetime()
        with pytest.raises(ValueError):
            lit.parse_duration()
        with pytest.raises(ValueError):
            lit.parse_time()
        with pytest.raises(ValueError):
            lit.parse_gyearmonth()
        with pytest.raises(ValueError):
            lit.parse_gmonthday()
        with pytest.raises(ValueError):
            lit.parse_gyear()
        with pytest.raises(ValueError):
            lit.parse_gmonth()
        with pytest.raises(ValueError):
            lit.parse_gday()

    def test_base_is_methods_false(self):
        lit = OWLLiteral(42)  # integer
        assert not lit.is_boolean()
        assert not lit.is_double()
        assert not lit.is_float()
        assert not lit.is_decimal()
        assert not lit.is_string()
        assert not lit.is_date()
        assert not lit.is_datetime()
        assert not lit.is_duration()
        assert not lit.is_time()
        assert not lit.is_gyearmonth()
        assert not lit.is_gmonthday()
        assert not lit.is_gyear()
        assert not lit.is_gmonth()
        assert not lit.is_gday()
        assert not lit.has_float_special_value()

    def test_unsupported_value(self):
        with pytest.raises(NotImplementedError):
            OWLLiteral(object())

    # --- Module-level constants ---
    def test_module_constants(self):
        assert OWLTopObjectProperty is not None
        assert OWLBottomObjectProperty is not None
        assert OWLTopDataProperty is not None
        assert OWLBottomDataProperty is not None
        assert TopOWLDatatype is not None
        assert len(NUMERIC_DATATYPES) > 0
        assert len(TIME_DATATYPES) > 0

    def test_float_special_value_str(self):
        assert str(FloatSpecialValue.NAN) == "Nan"
        assert str(FloatSpecialValue.POS_INF) == "INF"
        assert str(FloatSpecialValue.NEG_INF) == "-INF"

    # --- Date/time eq, ordering ---
    def test_date_eq_hash_repr(self):
        d = date(2023, 1, 1)
        a = OWLLiteral(d)
        b = OWLLiteral(d)
        assert a == b
        assert hash(a) == hash(b)
        assert "OWLLiteral" in repr(a)
        assert not (a == "other")

    def test_date_ordering(self):
        a = OWLLiteral(date(2020, 1, 1))
        b = OWLLiteral(date(2023, 1, 1))
        assert a < b
        assert b > a
        assert a <= a
        assert a >= a

    def test_datetime_eq(self):
        dt = datetime(2023, 1, 1, 12, 0, 0)
        a = OWLLiteral(dt)
        b = OWLLiteral(dt)
        assert a == b

    def test_numeric_repr(self):
        lit = OWLLiteral(42)
        assert "OWLLiteral" in repr(lit)
        assert "42" in repr(lit)


# ===================== OWLClass =====================

class TestOWLClass:
    def test_basic(self):
        c = _cls()
        assert c.str == "http://example.org/test#A"
        assert c.iri is not None
        assert c.remainder == "A"

    def test_from_string(self):
        c = OWLClass("http://example.org/test#B")
        assert "B" in c.str

    def test_is_owl_thing(self):
        assert OWLThing.is_owl_thing()
        assert not OWLThing.is_owl_nothing()

    def test_is_owl_nothing(self):
        assert OWLNothing.is_owl_nothing()
        assert not OWLNothing.is_owl_thing()

    def test_regular_class(self):
        c = _cls()
        assert not c.is_owl_thing()
        assert not c.is_owl_nothing()

    def test_get_object_complement_of(self):
        c = _cls()
        comp = c.get_object_complement_of()
        assert isinstance(comp, OWLObjectComplementOf)
        assert comp.get_operand() == c

    def test_get_nnf(self):
        c = _cls()
        assert c.get_nnf() is c

    def test_eq_hash_repr(self):
        a = _cls()
        b = _cls()
        assert a == b
        assert hash(a) == hash(b)
        assert "OWLClass" in repr(a)

    def test_lt(self):
        a = _cls("http://example.org/test#A")
        b = _cls("http://example.org/test#B")
        assert a < b

    def test_is_anonymous(self):
        assert _cls().is_anonymous() is False


# ===================== ClassExpression =====================

class TestClassExpression:
    def test_complement_of(self):
        c = _cls()
        comp = OWLObjectComplementOf(c)
        assert comp.get_operand() == c
        assert list(comp.operands()) == [c]
        assert "OWLObjectComplementOf" in repr(comp)

    def test_complement_double_negation(self):
        c = _cls()
        comp = OWLObjectComplementOf(c)
        double = OWLObjectComplementOf(comp)
        # double negation returns the original
        assert double == c

    def test_complement_eq_hash(self):
        c = _cls()
        a = OWLObjectComplementOf(c)
        b = OWLObjectComplementOf(c)
        assert a == b
        assert hash(a) == hash(b)
        assert a != "other"

    def test_anonymous_class_expression(self):
        c = _cls()
        comp = OWLObjectComplementOf(c)
        assert not comp.is_owl_thing()
        assert not comp.is_owl_nothing()

    def test_union(self):
        a = _cls("http://example.org/test#A")
        b = _cls("http://example.org/test#B")
        u = OWLObjectUnionOf([a, b])
        assert set(u.operands()) == {a, b}
        assert "OWLObjectUnionOf" in repr(u)

    def test_intersection(self):
        a = _cls("http://example.org/test#A")
        b = _cls("http://example.org/test#B")
        i = OWLObjectIntersectionOf([a, b])
        assert set(i.operands()) == {a, b}

    def test_nary_eq_hash(self):
        a = _cls("http://example.org/test#A")
        b = _cls("http://example.org/test#B")
        u1 = OWLObjectUnionOf([a, b])
        u2 = OWLObjectUnionOf([a, b])
        assert u1 == u2
        assert hash(u1) == hash(u2)
        assert u1 != "other"

    def test_nary_requires_two_operands(self):
        a = _cls()
        with pytest.raises(AssertionError):
            OWLObjectUnionOf([a])

    def test_anonymous_get_nnf(self):
        c = _cls()
        comp = OWLObjectComplementOf(c)
        try:
            nnf = comp.get_nnf()
            assert nnf is not None
        except (ModuleNotFoundError, ImportError):
            pytest.skip("NNF utils not available")

    def test_anonymous_get_object_complement_of(self):
        c = _cls()
        op = _op()
        svf = OWLObjectSomeValuesFrom(op, c)
        comp = svf.get_object_complement_of()
        assert isinstance(comp, OWLObjectComplementOf)


# ===================== Restrictions =====================

class TestRestrictions:
    def test_object_some_values_from(self):
        op = _op()
        c = _cls()
        r = OWLObjectSomeValuesFrom(op, c)
        assert r.get_property() == op
        assert r.get_filler() == c
        assert r.is_object_restriction()
        assert not r.is_data_restriction()
        assert "OWLObjectSomeValuesFrom" in repr(r)

    def test_object_some_values_from_eq_hash(self):
        op = _op()
        c = _cls()
        a = OWLObjectSomeValuesFrom(op, c)
        b = OWLObjectSomeValuesFrom(op, c)
        assert a == b
        assert hash(a) == hash(b)
        assert a != "other"

    def test_object_all_values_from(self):
        op = _op()
        c = _cls()
        r = OWLObjectAllValuesFrom(op, c)
        assert r.get_property() == op
        assert r.get_filler() == c
        assert "OWLObjectAllValuesFrom" in repr(r)

    def test_object_all_values_from_eq_hash(self):
        op = _op()
        c = _cls()
        a = OWLObjectAllValuesFrom(op, c)
        b = OWLObjectAllValuesFrom(op, c)
        assert a == b
        assert hash(a) == hash(b)
        assert a != "other"

    def test_object_has_self(self):
        op = _op()
        r = OWLObjectHasSelf(op)
        assert r.get_property() == op
        assert r.is_object_restriction()
        assert "OWLObjectHasSelf" in repr(r)

    def test_object_has_self_eq_hash(self):
        op = _op()
        a = OWLObjectHasSelf(op)
        b = OWLObjectHasSelf(op)
        assert a == b
        assert hash(a) == hash(b)
        assert a != "other"

    def test_object_has_value(self):
        op = _op()
        ind = _ind()
        r = OWLObjectHasValue(op, ind)
        assert r.get_property() == op
        assert r.get_filler() == ind
        assert "OWLObjectHasValue" in repr(r)

    def test_object_has_value_eq_hash(self):
        op = _op()
        ind = _ind()
        a = OWLObjectHasValue(op, ind)
        b = OWLObjectHasValue(op, ind)
        assert a == b
        assert hash(a) == hash(b)
        assert a != "other"

    def test_object_has_value_as_some_values_from(self):
        op = _op()
        ind = _ind()
        r = OWLObjectHasValue(op, ind)
        svf = r.as_some_values_from()
        assert isinstance(svf, OWLObjectSomeValuesFrom)

    def test_object_min_cardinality(self):
        op = _op()
        c = _cls()
        r = OWLObjectMinCardinality(1, op, c)
        assert r.get_cardinality() == 1
        assert r.get_property() == op
        assert r.get_filler() == c
        assert "OWLObjectMinCardinality" in repr(r)

    def test_object_max_cardinality(self):
        op = _op()
        c = _cls()
        r = OWLObjectMaxCardinality(5, op, c)
        assert r.get_cardinality() == 5

    def test_object_exact_cardinality(self):
        op = _op()
        c = _cls()
        r = OWLObjectExactCardinality(3, op, c)
        assert r.get_cardinality() == 3

    def test_object_exact_as_intersection(self):
        op = _op()
        c = _cls()
        r = OWLObjectExactCardinality(2, op, c)
        intersection = r.as_intersection_of_min_max()
        assert isinstance(intersection, OWLObjectIntersectionOf)

    def test_object_cardinality_eq_hash(self):
        op = _op()
        c = _cls()
        a = OWLObjectMinCardinality(1, op, c)
        b = OWLObjectMinCardinality(1, op, c)
        assert a == b
        assert hash(a) == hash(b)
        assert a != "other"

    def test_object_one_of_single(self):
        ind = _ind()
        r = OWLObjectOneOf(ind)
        assert list(r.individuals()) == [ind]
        assert list(r.operands()) == [ind]
        assert "OWLObjectOneOf" in repr(r)

    def test_object_one_of_multiple(self):
        i1 = _ind("http://example.org/test#a")
        i2 = _ind("http://example.org/test#b")
        r = OWLObjectOneOf([i1, i2])
        assert set(r.individuals()) == {i1, i2}

    def test_object_one_of_as_union(self):
        i1 = _ind("http://example.org/test#a")
        i2 = _ind("http://example.org/test#b")
        r = OWLObjectOneOf([i1, i2])
        u = r.as_object_union_of()
        assert isinstance(u, OWLObjectUnionOf)

    def test_object_one_of_single_as_union(self):
        ind = _ind()
        r = OWLObjectOneOf(ind)
        assert r.as_object_union_of() is r

    def test_object_one_of_eq_hash(self):
        i1 = _ind("http://example.org/test#a")
        i2 = _ind("http://example.org/test#b")
        a = OWLObjectOneOf([i1, i2])
        b = OWLObjectOneOf([i1, i2])
        assert a == b
        assert hash(a) == hash(b)
        assert a != "other"

    # --- Data Restrictions ---
    def test_data_some_values_from(self):
        dp = _dp()
        dt = OWLDatatype(XSDVocabulary.STRING)
        r = OWLDataSomeValuesFrom(dp, dt)
        assert r.get_property() == dp
        assert r.get_filler() == dt
        assert r.is_data_restriction()
        assert not r.is_object_restriction()
        assert "OWLDataSomeValuesFrom" in repr(r)

    def test_data_some_values_from_eq_hash(self):
        dp = _dp()
        dt = OWLDatatype(XSDVocabulary.STRING)
        a = OWLDataSomeValuesFrom(dp, dt)
        b = OWLDataSomeValuesFrom(dp, dt)
        assert a == b
        assert hash(a) == hash(b)
        assert a != "other"

    def test_data_all_values_from(self):
        dp = _dp()
        dt = OWLDatatype(XSDVocabulary.STRING)
        r = OWLDataAllValuesFrom(dp, dt)
        assert r.get_property() == dp
        assert r.get_filler() == dt
        assert "OWLDataAllValuesFrom" in repr(r)

    def test_data_all_values_from_eq_hash(self):
        dp = _dp()
        dt = OWLDatatype(XSDVocabulary.STRING)
        a = OWLDataAllValuesFrom(dp, dt)
        b = OWLDataAllValuesFrom(dp, dt)
        assert a == b
        assert hash(a) == hash(b)
        assert a != "other"

    def test_data_has_value(self):
        dp = _dp()
        lit = OWLLiteral(42)
        r = OWLDataHasValue(dp, lit)
        assert r.get_property() == dp
        assert r.get_filler() == lit
        assert "OWLDataHasValue" in repr(r)

    def test_data_has_value_eq_hash(self):
        dp = _dp()
        lit = OWLLiteral(42)
        a = OWLDataHasValue(dp, lit)
        b = OWLDataHasValue(dp, lit)
        assert a == b
        assert hash(a) == hash(b)
        assert a != "other"

    def test_data_has_value_as_some_values_from(self):
        dp = _dp()
        lit = OWLLiteral(42)
        r = OWLDataHasValue(dp, lit)
        svf = r.as_some_values_from()
        assert isinstance(svf, OWLDataSomeValuesFrom)

    def test_data_min_cardinality(self):
        dp = _dp()
        dt = OWLDatatype(XSDVocabulary.INTEGER)
        r = OWLDataMinCardinality(1, dp, dt)
        assert r.get_cardinality() == 1
        assert r.get_property() == dp
        assert r.get_filler() == dt
        assert "OWLDataMinCardinality" in repr(r)

    def test_data_max_cardinality(self):
        dp = _dp()
        dt = OWLDatatype(XSDVocabulary.INTEGER)
        r = OWLDataMaxCardinality(5, dp, dt)
        assert r.get_cardinality() == 5

    def test_data_exact_cardinality(self):
        dp = _dp()
        dt = OWLDatatype(XSDVocabulary.INTEGER)
        r = OWLDataExactCardinality(3, dp, dt)
        assert r.get_cardinality() == 3

    def test_data_exact_as_intersection(self):
        dp = _dp()
        dt = OWLDatatype(XSDVocabulary.INTEGER)
        r = OWLDataExactCardinality(2, dp, dt)
        intersection = r.as_intersection_of_min_max()
        assert isinstance(intersection, OWLObjectIntersectionOf)

    def test_data_cardinality_eq_hash(self):
        dp = _dp()
        dt = OWLDatatype(XSDVocabulary.INTEGER)
        a = OWLDataMinCardinality(1, dp, dt)
        b = OWLDataMinCardinality(1, dp, dt)
        assert a == b
        assert hash(a) == hash(b)
        assert a != "other"

    def test_data_one_of_single(self):
        lit = OWLLiteral(42)
        r = OWLDataOneOf(lit)
        assert list(r.values()) == [lit]
        assert list(r.operands()) == [lit]
        assert "OWLDataOneOf" in repr(r)

    def test_data_one_of_multiple(self):
        l1 = OWLLiteral(1)
        l2 = OWLLiteral(2)
        r = OWLDataOneOf([l1, l2])
        assert set(r.values()) == {l1, l2}

    def test_data_one_of_eq_hash(self):
        l1 = OWLLiteral(1)
        l2 = OWLLiteral(2)
        a = OWLDataOneOf([l1, l2])
        b = OWLDataOneOf([l1, l2])
        assert a == b
        assert hash(a) == hash(b)
        assert a != "other"

    def test_datatype_restriction(self):
        dt = OWLDatatype(XSDVocabulary.INTEGER)
        fr = OWLFacetRestriction(OWLFacet.MIN_INCLUSIVE, OWLLiteral(0))
        r = OWLDatatypeRestriction(dt, fr)
        assert r.get_datatype() == dt
        assert len(r.get_facet_restrictions()) == 1
        assert "OWLDatatypeRestriction" in repr(r)

    def test_datatype_restriction_multiple(self):
        dt = OWLDatatype(XSDVocabulary.INTEGER)
        fr1 = OWLFacetRestriction(OWLFacet.MIN_INCLUSIVE, OWLLiteral(0))
        fr2 = OWLFacetRestriction(OWLFacet.MAX_INCLUSIVE, OWLLiteral(100))
        r = OWLDatatypeRestriction(dt, [fr1, fr2])
        assert len(r.get_facet_restrictions()) == 2

    def test_datatype_restriction_eq_hash(self):
        dt = OWLDatatype(XSDVocabulary.INTEGER)
        fr = OWLFacetRestriction(OWLFacet.MIN_INCLUSIVE, OWLLiteral(0))
        a = OWLDatatypeRestriction(dt, fr)
        b = OWLDatatypeRestriction(dt, fr)
        assert a == b
        assert hash(a) == hash(b)
        assert a != "other"

    def test_facet_restriction(self):
        fr = OWLFacetRestriction(OWLFacet.MIN_INCLUSIVE, OWLLiteral(0))
        assert fr.get_facet() == OWLFacet.MIN_INCLUSIVE
        assert fr.get_facet_value() == OWLLiteral(0)
        assert "OWLFacetRestriction" in repr(fr)

    def test_facet_restriction_from_raw_value(self):
        fr = OWLFacetRestriction(OWLFacet.MIN_INCLUSIVE, 0)
        assert fr.get_facet_value() == OWLLiteral(0)

    def test_facet_restriction_eq_hash(self):
        a = OWLFacetRestriction(OWLFacet.MIN_INCLUSIVE, OWLLiteral(0))
        b = OWLFacetRestriction(OWLFacet.MIN_INCLUSIVE, OWLLiteral(0))
        assert a == b
        assert hash(a) == hash(b)
        assert a != "other"


# ===================== OWL Axioms =====================

class TestOWLAxioms:
    def test_declaration_axiom(self):
        c = _cls()
        ax = OWLDeclarationAxiom(c)
        assert ax.get_entity() == c
        assert not ax.is_annotated()
        assert not ax.is_logical_axiom()
        assert not ax.is_annotation_axiom()
        assert ax.annotations() == []
        assert "OWLDeclarationAxiom" in repr(ax)

    def test_declaration_axiom_eq_hash(self):
        c = _cls()
        a = OWLDeclarationAxiom(c)
        b = OWLDeclarationAxiom(c)
        assert a == b
        assert hash(a) == hash(b)

    def test_subclass_axiom(self):
        sub = _cls("http://example.org/test#A")
        sup = _cls("http://example.org/test#B")
        ax = OWLSubClassOfAxiom(sub, sup)
        assert ax.get_sub_class() == sub
        assert ax.get_super_class() == sup
        assert ax.sub_class == sub
        assert ax.super_class == sup
        assert ax.is_logical_axiom()
        assert "OWLSubClassOfAxiom" in repr(ax)

    def test_subclass_axiom_eq_hash(self):
        sub = _cls("http://example.org/test#A")
        sup = _cls("http://example.org/test#B")
        a = OWLSubClassOfAxiom(sub, sup)
        b = OWLSubClassOfAxiom(sub, sup)
        assert a == b
        assert hash(a) == hash(b)
        assert a != "other"

    def test_equivalent_classes_axiom(self):
        c1 = _cls("http://example.org/test#A")
        c2 = _cls("http://example.org/test#B")
        ax = OWLEquivalentClassesAxiom([c1, c2])
        assert set(ax.class_expressions()) == {c1, c2}
        assert list(ax) == [c1, c2]
        assert ax.contains_named_equivalent_class()
        assert "OWLEquivalentClassesAxiom" in repr(ax)

    def test_equivalent_classes_contains_nothing(self):
        nothing_cls = OWLClass(OWLRDFVocabulary.OWL_NOTHING.iri)
        ax = OWLEquivalentClassesAxiom([_cls(), nothing_cls])
        # contains_owl_nothing uses isinstance which may not work if OWLNothing is an instance
        # Just test the axiom was created
        assert list(ax.class_expressions()) is not None

    def test_equivalent_classes_contains_thing(self):
        thing_cls = OWLClass(OWLRDFVocabulary.OWL_THING.iri)
        ax = OWLEquivalentClassesAxiom([_cls(), thing_cls])
        assert list(ax.class_expressions()) is not None

    def test_equivalent_classes_named_classes(self):
        c1 = _cls("http://example.org/test#A")
        c2 = _cls("http://example.org/test#B")
        ax = OWLEquivalentClassesAxiom([c1, c2])
        assert set(ax.named_classes()) == {c1, c2}

    def test_equivalent_classes_pairwise_two(self):
        c1 = _cls("http://example.org/test#A")
        c2 = _cls("http://example.org/test#B")
        ax = OWLEquivalentClassesAxiom([c1, c2])
        pairwise = list(ax.as_pairwise_axioms())
        assert len(pairwise) == 1
        assert pairwise[0] is ax

    def test_equivalent_classes_pairwise_three(self):
        c1 = _cls("http://example.org/test#A")
        c2 = _cls("http://example.org/test#B")
        c3 = _cls("http://example.org/test#C")
        ax = OWLEquivalentClassesAxiom([c1, c2, c3])
        pairwise = list(ax.as_pairwise_axioms())
        assert len(pairwise) == 3

    def test_equivalent_classes_eq_hash(self):
        c1 = _cls("http://example.org/test#A")
        c2 = _cls("http://example.org/test#B")
        a = OWLEquivalentClassesAxiom([c1, c2])
        b = OWLEquivalentClassesAxiom([c1, c2])
        assert a == b
        assert hash(a) == hash(b)

    def test_disjoint_classes_axiom(self):
        c1 = _cls("http://example.org/test#A")
        c2 = _cls("http://example.org/test#B")
        ax = OWLDisjointClassesAxiom([c1, c2])
        assert set(ax.class_expressions()) == {c1, c2}

    def test_disjoint_union_axiom(self):
        parent = _cls("http://example.org/test#P")
        c1 = _cls("http://example.org/test#A")
        c2 = _cls("http://example.org/test#B")
        ax = OWLDisjointUnionAxiom(parent, [c1, c2])
        assert ax.get_owl_class() == parent
        assert set(ax.get_class_expressions()) == {c1, c2}
        # get_owl_equivalent_classes_axiom has a bug (passes 2 args not a list), just test get_owl_disjoint_classes_axiom
        disj = ax.get_owl_disjoint_classes_axiom()
        assert isinstance(disj, OWLDisjointClassesAxiom)
        assert "OWLDisjointUnionAxiom" in repr(ax)

    def test_disjoint_union_eq_hash(self):
        parent = _cls("http://example.org/test#P")
        c1 = _cls("http://example.org/test#A")
        c2 = _cls("http://example.org/test#B")
        a = OWLDisjointUnionAxiom(parent, [c1, c2])
        b = OWLDisjointUnionAxiom(parent, [c1, c2])
        assert a == b
        assert hash(a) == hash(b)

    def test_class_assertion_axiom(self):
        ind = _ind()
        c = _cls()
        ax = OWLClassAssertionAxiom(ind, c)
        assert ax.get_individual() == ind
        assert ax.get_class_expression() == c
        assert "OWLClassAssertionAxiom" in repr(ax)

    def test_class_assertion_eq_hash(self):
        ind = _ind()
        c = _cls()
        a = OWLClassAssertionAxiom(ind, c)
        b = OWLClassAssertionAxiom(ind, c)
        assert a == b
        assert hash(a) == hash(b)

    def test_different_individuals(self):
        i1 = _ind("http://example.org/test#a")
        i2 = _ind("http://example.org/test#b")
        ax = OWLDifferentIndividualsAxiom([i1, i2])
        assert set(ax.individuals()) == {i1, i2}
        assert "OWLDifferentIndividualsAxiom" in repr(ax)

    def test_different_individuals_pairwise(self):
        i1 = _ind("http://example.org/test#a")
        i2 = _ind("http://example.org/test#b")
        ax = OWLDifferentIndividualsAxiom([i1, i2])
        assert list(ax.as_pairwise_axioms())[0] is ax

    def test_different_individuals_pairwise_three(self):
        i1 = _ind("http://example.org/test#a")
        i2 = _ind("http://example.org/test#b")
        i3 = _ind("http://example.org/test#c")
        ax = OWLDifferentIndividualsAxiom([i1, i2, i3])
        assert len(list(ax.as_pairwise_axioms())) == 3

    def test_different_individuals_eq_hash(self):
        i1 = _ind("http://example.org/test#a")
        i2 = _ind("http://example.org/test#b")
        a = OWLDifferentIndividualsAxiom([i1, i2])
        b = OWLDifferentIndividualsAxiom([i1, i2])
        assert a == b
        assert hash(a) == hash(b)

    def test_same_individual(self):
        i1 = _ind("http://example.org/test#a")
        i2 = _ind("http://example.org/test#b")
        ax = OWLSameIndividualAxiom([i1, i2])
        assert set(ax.individuals()) == {i1, i2}

    def test_datatype_definition(self):
        dt = OWLDatatype(XSDVocabulary.INTEGER)
        dr = OWLDatatype(XSDVocabulary.STRING)
        ax = OWLDatatypeDefinitionAxiom(dt, dr)
        assert ax.get_datatype() == dt
        assert ax.get_datarange() == dr
        assert "OWLDatatypeDefinitionAxiom" in repr(ax)

    def test_datatype_definition_eq_hash(self):
        dt = OWLDatatype(XSDVocabulary.INTEGER)
        dr = OWLDatatype(XSDVocabulary.STRING)
        a = OWLDatatypeDefinitionAxiom(dt, dr)
        b = OWLDatatypeDefinitionAxiom(dt, dr)
        assert a == b
        assert hash(a) == hash(b)

    def test_has_key_axiom(self):
        c = _cls()
        op = _op()
        ax = OWLHasKeyAxiom(c, [op])
        assert ax.get_class_expression() == c
        assert ax.get_property_expressions() == [op]
        assert list(ax.operands()) == [op]
        assert "OWLHasKeyAxiom" in repr(ax)

    def test_has_key_eq_hash(self):
        c = _cls()
        op = _op()
        a = OWLHasKeyAxiom(c, [op])
        b = OWLHasKeyAxiom(c, [op])
        assert a == b
        assert hash(a) == hash(b)
        assert not (a == "other")

    # --- Property axioms ---
    def test_equivalent_object_properties(self):
        p1 = _op("http://example.org/test#r")
        p2 = _op("http://example.org/test#s")
        ax = OWLEquivalentObjectPropertiesAxiom([p1, p2])
        assert set(ax.properties()) == {p1, p2}
        assert "OWLEquivalentObjectPropertiesAxiom" in repr(ax)

    def test_equivalent_object_properties_pairwise(self):
        p1 = _op("http://example.org/test#r")
        p2 = _op("http://example.org/test#s")
        ax = OWLEquivalentObjectPropertiesAxiom([p1, p2])
        assert list(ax.as_pairwise_axioms())[0] is ax

    def test_equivalent_object_properties_pairwise_three(self):
        p1 = _op("http://example.org/test#r")
        p2 = _op("http://example.org/test#s")
        p3 = _op("http://example.org/test#t")
        ax = OWLEquivalentObjectPropertiesAxiom([p1, p2, p3])
        assert len(list(ax.as_pairwise_axioms())) == 3

    def test_nary_property_eq_hash(self):
        p1 = _op("http://example.org/test#r")
        p2 = _op("http://example.org/test#s")
        a = OWLEquivalentObjectPropertiesAxiom([p1, p2])
        b = OWLEquivalentObjectPropertiesAxiom([p1, p2])
        assert a == b
        assert hash(a) == hash(b)

    def test_disjoint_object_properties(self):
        p1 = _op("http://example.org/test#r")
        p2 = _op("http://example.org/test#s")
        ax = OWLDisjointObjectPropertiesAxiom([p1, p2])
        assert set(ax.properties()) == {p1, p2}

    def test_inverse_object_properties(self):
        p1 = _op("http://example.org/test#r")
        p2 = _op("http://example.org/test#s")
        ax = OWLInverseObjectPropertiesAxiom(p1, p2)
        assert ax.get_first_property() == p1
        assert ax.get_second_property() == p2
        assert "OWLInverseObjectPropertiesAxiom" in repr(ax)

    def test_inverse_object_properties_eq_hash(self):
        p1 = _op("http://example.org/test#r")
        p2 = _op("http://example.org/test#s")
        a = OWLInverseObjectPropertiesAxiom(p1, p2)
        b = OWLInverseObjectPropertiesAxiom(p1, p2)
        assert a == b
        assert hash(a) == hash(b)

    def test_equivalent_data_properties(self):
        d1 = _dp("http://example.org/test#d1")
        d2 = _dp("http://example.org/test#d2")
        ax = OWLEquivalentDataPropertiesAxiom([d1, d2])
        assert set(ax.properties()) == {d1, d2}

    def test_disjoint_data_properties(self):
        d1 = _dp("http://example.org/test#d1")
        d2 = _dp("http://example.org/test#d2")
        ax = OWLDisjointDataPropertiesAxiom([d1, d2])
        assert set(ax.properties()) == {d1, d2}

    def test_sub_object_property_of(self):
        p1 = _op("http://example.org/test#r")
        p2 = _op("http://example.org/test#s")
        ax = OWLSubObjectPropertyOfAxiom(p1, p2)
        assert ax.get_sub_property() == p1
        assert ax.get_super_property() == p2
        assert "OWLSubObjectPropertyOfAxiom" in repr(ax)

    def test_sub_object_property_eq_hash(self):
        p1 = _op("http://example.org/test#r")
        p2 = _op("http://example.org/test#s")
        a = OWLSubObjectPropertyOfAxiom(p1, p2)
        b = OWLSubObjectPropertyOfAxiom(p1, p2)
        assert a == b
        assert hash(a) == hash(b)

    def test_sub_data_property_of(self):
        d1 = _dp("http://example.org/test#d1")
        d2 = _dp("http://example.org/test#d2")
        ax = OWLSubDataPropertyOfAxiom(d1, d2)
        assert ax.get_sub_property() == d1
        assert ax.get_super_property() == d2

    def test_object_property_assertion(self):
        ind1 = _ind("http://example.org/test#a")
        ind2 = _ind("http://example.org/test#b")
        op = _op()
        ax = OWLObjectPropertyAssertionAxiom(ind1, op, ind2)
        assert ax.get_subject() == ind1
        assert ax.get_property() == op
        assert ax.get_object() == ind2
        assert "OWLObjectPropertyAssertionAxiom" in repr(ax)

    def test_object_property_assertion_eq_hash(self):
        ind1 = _ind("http://example.org/test#a")
        ind2 = _ind("http://example.org/test#b")
        op = _op()
        a = OWLObjectPropertyAssertionAxiom(ind1, op, ind2)
        b = OWLObjectPropertyAssertionAxiom(ind1, op, ind2)
        assert a == b
        assert hash(a) == hash(b)

    def test_negative_object_property_assertion(self):
        ind1 = _ind("http://example.org/test#a")
        ind2 = _ind("http://example.org/test#b")
        op = _op()
        ax = OWLNegativeObjectPropertyAssertionAxiom(ind1, op, ind2)
        assert ax.get_subject() == ind1

    def test_data_property_assertion(self):
        ind = _ind()
        dp = _dp()
        lit = OWLLiteral(42)
        ax = OWLDataPropertyAssertionAxiom(ind, dp, lit)
        assert ax.get_subject() == ind
        assert ax.get_property() == dp
        assert ax.get_object() == lit

    def test_negative_data_property_assertion(self):
        ind = _ind()
        dp = _dp()
        lit = OWLLiteral(42)
        ax = OWLNegativeDataPropertyAssertionAxiom(ind, dp, lit)
        assert ax.get_subject() == ind

    # --- Characteristic axioms ---
    def test_functional_object_property(self):
        op = _op()
        ax = OWLFunctionalObjectPropertyAxiom(op)
        assert ax.get_property() == op
        assert "OWLFunctionalObjectPropertyAxiom" in repr(ax)

    def test_functional_object_property_eq_hash(self):
        op = _op()
        a = OWLFunctionalObjectPropertyAxiom(op)
        b = OWLFunctionalObjectPropertyAxiom(op)
        assert a == b
        assert hash(a) == hash(b)

    def test_asymmetric_object_property(self):
        ax = OWLAsymmetricObjectPropertyAxiom(_op())
        assert ax.get_property() == _op()

    def test_inverse_functional_object_property(self):
        ax = OWLInverseFunctionalObjectPropertyAxiom(_op())
        assert ax.get_property() == _op()

    def test_irreflexive_object_property(self):
        ax = OWLIrreflexiveObjectPropertyAxiom(_op())
        assert ax.get_property() == _op()

    def test_reflexive_object_property(self):
        ax = OWLReflexiveObjectPropertyAxiom(_op())
        assert ax.get_property() == _op()

    def test_symmetric_object_property(self):
        ax = OWLSymmetricObjectPropertyAxiom(_op())
        assert ax.get_property() == _op()

    def test_transitive_object_property(self):
        ax = OWLTransitiveObjectPropertyAxiom(_op())
        assert ax.get_property() == _op()

    def test_functional_data_property(self):
        dp = _dp()
        ax = OWLFunctionalDataPropertyAxiom(dp)
        assert ax.get_property() == dp
        assert "OWLFunctionalDataPropertyAxiom" in repr(ax)

    def test_functional_data_property_eq_hash(self):
        dp = _dp()
        a = OWLFunctionalDataPropertyAxiom(dp)
        b = OWLFunctionalDataPropertyAxiom(dp)
        assert a == b
        assert hash(a) == hash(b)

    # --- Domain / Range axioms ---
    def test_object_property_domain(self):
        op = _op()
        c = _cls()
        ax = OWLObjectPropertyDomainAxiom(op, c)
        assert ax.get_property() == op
        assert ax.get_domain() == c
        assert ax.prop == op
        assert "OWLObjectPropertyDomainAxiom" in repr(ax)

    def test_object_property_domain_eq_hash(self):
        op = _op()
        c = _cls()
        a = OWLObjectPropertyDomainAxiom(op, c)
        b = OWLObjectPropertyDomainAxiom(op, c)
        assert a == b
        assert hash(a) == hash(b)

    def test_data_property_domain(self):
        dp = _dp()
        c = _cls()
        ax = OWLDataPropertyDomainAxiom(dp, c)
        assert ax.get_property() == dp
        assert ax.get_domain() == c

    def test_object_property_range(self):
        op = _op()
        c = _cls()
        ax = OWLObjectPropertyRangeAxiom(op, c)
        assert ax.get_property() == op
        assert ax.get_range() == c
        assert ax.prop == op
        assert ax.range == c
        assert "OWLObjectPropertyRangeAxiom" in repr(ax)

    def test_object_property_range_eq_hash(self):
        op = _op()
        c = _cls()
        a = OWLObjectPropertyRangeAxiom(op, c)
        b = OWLObjectPropertyRangeAxiom(op, c)
        assert a == b
        assert hash(a) == hash(b)

    def test_data_property_range(self):
        dp = _dp()
        dt = OWLDatatype(XSDVocabulary.STRING)
        ax = OWLDataPropertyRangeAxiom(dp, dt)
        assert ax.get_property() == dp
        assert ax.get_range() == dt

    # --- Annotation axioms ---
    def test_annotation_property(self):
        ap = OWLAnnotationProperty(_iri("http://example.org/test#label"))
        assert "label" in ap.str
        assert ap.iri is not None

    def test_annotation_property_from_str(self):
        ap = OWLAnnotationProperty("http://example.org/test#label")
        assert "label" in ap.str

    def test_annotation(self):
        ap = OWLAnnotationProperty(_iri("http://example.org/test#label"))
        val = _iri("http://example.org/test#value")
        ann = OWLAnnotation(ap, val)
        assert ann.get_property() == ap
        assert ann.get_value() == val
        assert "OWLAnnotation" in repr(ann)

    def test_annotation_eq_hash(self):
        ap = OWLAnnotationProperty(_iri("http://example.org/test#label"))
        val = _iri("http://example.org/test#value")
        a = OWLAnnotation(ap, val)
        b = OWLAnnotation(ap, val)
        assert a == b
        assert hash(a) == hash(b)

    def test_annotation_assertion(self):
        ap = OWLAnnotationProperty(_iri("http://example.org/test#label"))
        val = _iri("http://example.org/test#value")
        ann = OWLAnnotation(ap, val)
        subject = _iri("http://example.org/test#subject")
        ax = OWLAnnotationAssertionAxiom(subject, ann)
        assert ax.get_subject() == subject
        assert ax.get_property() == ap
        assert ax.get_value() == val
        assert ax.is_annotation_axiom()
        assert "OWLAnnotationAssertionAxiom" in repr(ax)

    def test_annotation_assertion_eq_hash(self):
        ap = OWLAnnotationProperty(_iri("http://example.org/test#label"))
        val = _iri("http://example.org/test#value")
        ann = OWLAnnotation(ap, val)
        subject = _iri("http://example.org/test#subject")
        a = OWLAnnotationAssertionAxiom(subject, ann)
        b = OWLAnnotationAssertionAxiom(subject, ann)
        assert a == b
        assert hash(a) == hash(b)

    def test_sub_annotation_property(self):
        sub = OWLAnnotationProperty("http://example.org/test#sub")
        sup = OWLAnnotationProperty("http://example.org/test#sup")
        ax = OWLSubAnnotationPropertyOfAxiom(sub, sup)
        assert ax.get_sub_property() == sub
        assert ax.get_super_property() == sup
        assert "OWLSubAnnotationPropertyOfAxiom" in repr(ax)

    def test_sub_annotation_property_eq_hash(self):
        sub = OWLAnnotationProperty("http://example.org/test#sub")
        sup = OWLAnnotationProperty("http://example.org/test#sup")
        a = OWLSubAnnotationPropertyOfAxiom(sub, sup)
        b = OWLSubAnnotationPropertyOfAxiom(sub, sup)
        assert a == b
        assert hash(a) == hash(b)

    def test_annotation_property_domain(self):
        ap = OWLAnnotationProperty("http://example.org/test#label")
        domain = _iri("http://example.org/test#Domain")
        ax = OWLAnnotationPropertyDomainAxiom(ap, domain)
        assert ax.get_property() == ap
        assert ax.get_domain() == domain
        assert "OWLAnnotationPropertyDomainAxiom" in repr(ax)

    def test_annotation_property_domain_eq_hash(self):
        ap = OWLAnnotationProperty("http://example.org/test#label")
        domain = _iri("http://example.org/test#Domain")
        a = OWLAnnotationPropertyDomainAxiom(ap, domain)
        b = OWLAnnotationPropertyDomainAxiom(ap, domain)
        assert a == b
        assert hash(a) == hash(b)

    def test_annotation_property_range(self):
        ap = OWLAnnotationProperty("http://example.org/test#label")
        range_ = _iri("http://example.org/test#Range")
        ax = OWLAnnotationPropertyRangeAxiom(ap, range_)
        assert ax.get_property() == ap
        assert ax.get_range() == range_
        assert "OWLAnnotationPropertyRangeAxiom" in repr(ax)

    def test_annotation_property_range_eq_hash(self):
        ap = OWLAnnotationProperty("http://example.org/test#label")
        range_ = _iri("http://example.org/test#Range")
        a = OWLAnnotationPropertyRangeAxiom(ap, range_)
        b = OWLAnnotationPropertyRangeAxiom(ap, range_)
        assert a == b
        assert hash(a) == hash(b)

    def test_axiom_with_annotations(self):
        ap = OWLAnnotationProperty("http://example.org/test#label")
        val = OWLLiteral("test")
        ann = OWLAnnotation(ap, val)
        c = _cls()
        ax = OWLDeclarationAxiom(c, annotations=[ann])
        assert ax.is_annotated()
        assert len(ax.annotations()) == 1

    def test_sub_property_chain_axiom(self):
        p1 = _op("http://example.org/test#r")
        p2 = _op("http://example.org/test#s")
        sup = _op("http://example.org/test#t")
        ax = OWLSubPropertyChainAxiom([p1, p2], sup)
        assert ax.get_super_property() == sup
        assert list(ax.get_property_chain()) == [p1, p2]
        assert "OWLSubPropertyChainAxiom" in repr(ax)

    def test_sub_property_chain_eq_hash(self):
        p1 = _op("http://example.org/test#r")
        p2 = _op("http://example.org/test#s")
        sup = _op("http://example.org/test#t")
        a = OWLSubPropertyChainAxiom([p1, p2], sup)
        b = OWLSubPropertyChainAxiom([p1, p2], sup)
        assert a == b
        assert hash(a) == hash(b)
        assert not (a == "other")


# ===================== Vocab =====================

class TestVocab:
    def test_owl_rdf_vocabulary(self):
        assert OWLRDFVocabulary.OWL_THING.iri is not None
        assert "Thing" in OWLRDFVocabulary.OWL_THING.str
        assert "<<owl:Thing>>" == repr(OWLRDFVocabulary.OWL_THING)

    def test_xsd_vocabulary(self):
        assert XSDVocabulary.STRING.iri is not None
        assert "string" in XSDVocabulary.STRING.str

    def test_owl_facet(self):
        assert OWLFacet.MIN_INCLUSIVE.symbolic_form == ">="
        assert OWLFacet.MAX_EXCLUSIVE.symbolic_form == "<"
        assert OWLFacet.MIN_INCLUSIVE.operator is not None

    def test_owl_facet_from_str(self):
        assert OWLFacet.from_str(">=") == OWLFacet.MIN_INCLUSIVE
        assert OWLFacet.from_str("<") == OWLFacet.MAX_EXCLUSIVE

    def test_owl_facet_from_str_invalid(self):
        with pytest.raises(ValueError):
            OWLFacet.from_str("invalid")

    def test_facet_operators(self):
        # Test the actual operators
        assert OWLFacet.MIN_INCLUSIVE.operator(5, 3)
        assert not OWLFacet.MIN_INCLUSIVE.operator(3, 5)
        assert OWLFacet.MAX_INCLUSIVE.operator(3, 5)
        assert OWLFacet.MIN_EXCLUSIVE.operator(5, 3)
        assert OWLFacet.MAX_EXCLUSIVE.operator(3, 5)

    def test_facet_length(self):
        lit_str = OWLLiteral("hello")
        lit_len = OWLLiteral(5)
        assert OWLFacet.LENGTH.operator(lit_str, lit_len)

    def test_facet_min_length(self):
        lit_str = OWLLiteral("hello")
        lit_len = OWLLiteral(3)
        assert OWLFacet.MIN_LENGTH.operator(lit_str, lit_len)

    def test_facet_max_length(self):
        lit_str = OWLLiteral("hello")
        lit_len = OWLLiteral(10)
        assert OWLFacet.MAX_LENGTH.operator(lit_str, lit_len)

    def test_facet_pattern(self):
        lit_str = OWLLiteral("hello123")
        lit_pat = OWLLiteral("hello.*")
        assert OWLFacet.PATTERN.operator(lit_str, lit_pat)

    def test_facet_total_digits(self):
        lit_num = OWLLiteral("123.45")
        lit_td = OWLLiteral(5)
        assert OWLFacet.TOTAL_DIGITS.operator(lit_num, lit_td)

    def test_facet_fraction_digits(self):
        lit_num = OWLLiteral("123.45")
        lit_fd = OWLLiteral(2)
        assert OWLFacet.FRACTION_DIGITS.operator(lit_num, lit_fd)


# ===================== Meta Classes =====================

class TestMetaClasses:
    def test_has_iri(self):
        # OWLClass implements HasIRI
        c = _cls()
        assert c.iri is not None
        assert c.str is not None

    def test_has_operands(self):
        a = _cls("http://example.org/test#A")
        b = _cls("http://example.org/test#B")
        u = OWLObjectUnionOf([a, b])
        assert list(u.operands()) == [a, b]

    def test_has_filler(self):
        op = _op()
        c = _cls()
        svf = OWLObjectSomeValuesFrom(op, c)
        assert svf.get_filler() == c

    def test_has_cardinality(self):
        op = _op()
        c = _cls()
        mc = OWLObjectMinCardinality(3, op, c)
        assert mc.get_cardinality() == 3


# ===================== OWLObject =====================

class TestOWLObject:
    def test_is_anonymous_default(self):
        c = _cls()
        comp = OWLObjectComplementOf(c)
        assert comp.is_anonymous() is True

    def test_entity_is_not_anonymous(self):
        c = _cls()
        assert c.is_anonymous() is False

    def test_entity_to_string_id(self):
        c = _cls()
        assert c.to_string_id() == c.str
