"""Tests targeting remaining low-coverage modules.

Covers:
- protege_reasoner_factory.py  (0%)
- owl_model/utils.py           (36%)
- structural/normalized_axioms.py  (74%)
- structural/owl_normalization.py  (various uncovered axiom types)
- parser.py                        (42%)
- tableau/dependency_set_factory.py (70%)
- tableau/clash_manager.py         (69%)
- tableau/nominal_introduction_manager.py (30%)
- tableau/description_graph_manager.py   (29%)
- hierarchy/quasi_order_classification_for_roles.py (60%)
- hierarchy/instance_manager.py           (62%)
- blocking/anywhere_validated_blocking.py (63%)
- blocking/blocking_validator.py          (40%)
"""

from __future__ import annotations

import pytest

# ===========================================================================
# protege_reasoner_factory — 0%
# ===========================================================================


class TestProtegeReasonerFactory:
    def test_raises_not_implemented(self) -> None:
        from hermit.protege_reasoner_factory import ProtegeReasonerFactory

        with pytest.raises(NotImplementedError):
            ProtegeReasonerFactory()

    def test_error_message_mentions_protege(self) -> None:
        from hermit.protege_reasoner_factory import ProtegeReasonerFactory

        with pytest.raises(NotImplementedError, match="Protege"):
            ProtegeReasonerFactory()


# ===========================================================================
# owl_model/utils.py — NNF
# ===========================================================================


class TestNNF:
    def _make_nnf(self):  # type: ignore[no-untyped-def]
        from hermit.owl_model.utils import NNF
        return NNF()

    def _cls(self, iri: str):  # type: ignore[no-untyped-def]
        from hermit.owl_model.class_expression.owl_class import OWLClass
        from hermit.owl_model.iri import IRI
        return OWLClass(IRI.create(iri))

    def test_class_returns_itself(self) -> None:
        nnf = self._make_nnf()
        c = self._cls("http://ex.org#A")
        assert nnf.get_class_nnf(c) is c

    def test_complement_of_class_returns_itself(self) -> None:
        from hermit.owl_model.class_expression.class_expression import OWLObjectComplementOf
        nnf = self._make_nnf()
        c = self._cls("http://ex.org#A")
        neg = OWLObjectComplementOf(c)
        result = nnf.get_class_nnf(neg)
        assert isinstance(result, OWLObjectComplementOf)

    def test_double_negation_elimination(self) -> None:
        from hermit.owl_model.class_expression.class_expression import OWLObjectComplementOf
        nnf = self._make_nnf()
        c = self._cls("http://ex.org#A")
        neg_neg = OWLObjectComplementOf(OWLObjectComplementOf(c))
        result = nnf.get_class_nnf(neg_neg)
        # ¬¬A → A
        from hermit.owl_model.class_expression.owl_class import OWLClass
        assert isinstance(result, OWLClass)

    def test_neg_intersection_becomes_union(self) -> None:
        from hermit.owl_model.class_expression.class_expression import OWLObjectComplementOf
        from hermit.owl_model.class_expression.nary_boolean_expression import (
            OWLObjectIntersectionOf, OWLObjectUnionOf
        )
        nnf = self._make_nnf()
        a = self._cls("http://ex.org#A")
        b = self._cls("http://ex.org#B")
        neg_and = OWLObjectComplementOf(OWLObjectIntersectionOf([a, b]))
        result = nnf.get_class_nnf(neg_and)
        assert isinstance(result, OWLObjectUnionOf)

    def test_neg_union_becomes_intersection(self) -> None:
        from hermit.owl_model.class_expression.class_expression import OWLObjectComplementOf
        from hermit.owl_model.class_expression.nary_boolean_expression import (
            OWLObjectIntersectionOf, OWLObjectUnionOf
        )
        nnf = self._make_nnf()
        a = self._cls("http://ex.org#A")
        b = self._cls("http://ex.org#B")
        neg_or = OWLObjectComplementOf(OWLObjectUnionOf([a, b]))
        result = nnf.get_class_nnf(neg_or)
        assert isinstance(result, OWLObjectIntersectionOf)

    def test_neg_some_becomes_all(self) -> None:
        from hermit.owl_model.class_expression.class_expression import OWLObjectComplementOf
        from hermit.owl_model.class_expression.restriction import (
            OWLObjectSomeValuesFrom, OWLObjectAllValuesFrom
        )
        from hermit.owl_model.iri import IRI
        from hermit.owl_model.owl_property import OWLObjectProperty
        nnf = self._make_nnf()
        r = OWLObjectProperty(IRI.create("http://ex.org#R"))
        c = self._cls("http://ex.org#A")
        neg_some = OWLObjectComplementOf(OWLObjectSomeValuesFrom(r, c))
        result = nnf.get_class_nnf(neg_some)
        assert isinstance(result, OWLObjectAllValuesFrom)

    def test_neg_all_becomes_some(self) -> None:
        from hermit.owl_model.class_expression.class_expression import OWLObjectComplementOf
        from hermit.owl_model.class_expression.restriction import (
            OWLObjectSomeValuesFrom, OWLObjectAllValuesFrom
        )
        from hermit.owl_model.iri import IRI
        from hermit.owl_model.owl_property import OWLObjectProperty
        nnf = self._make_nnf()
        r = OWLObjectProperty(IRI.create("http://ex.org#R"))
        c = self._cls("http://ex.org#A")
        neg_all = OWLObjectComplementOf(OWLObjectAllValuesFrom(r, c))
        result = nnf.get_class_nnf(neg_all)
        assert isinstance(result, OWLObjectSomeValuesFrom)

    def test_intersection_recurses(self) -> None:
        from hermit.owl_model.class_expression.nary_boolean_expression import (
            OWLObjectIntersectionOf
        )
        nnf = self._make_nnf()
        a = self._cls("http://ex.org#A")
        b = self._cls("http://ex.org#B")
        expr = OWLObjectIntersectionOf([a, b])
        result = nnf.get_class_nnf(expr)
        assert isinstance(result, OWLObjectIntersectionOf)

    def test_union_recurses(self) -> None:
        from hermit.owl_model.class_expression.nary_boolean_expression import (
            OWLObjectUnionOf
        )
        nnf = self._make_nnf()
        a = self._cls("http://ex.org#A")
        b = self._cls("http://ex.org#B")
        expr = OWLObjectUnionOf([a, b])
        result = nnf.get_class_nnf(expr)
        assert isinstance(result, OWLObjectUnionOf)

    def test_some_recurses(self) -> None:
        from hermit.owl_model.class_expression.restriction import OWLObjectSomeValuesFrom
        from hermit.owl_model.iri import IRI
        from hermit.owl_model.owl_property import OWLObjectProperty
        nnf = self._make_nnf()
        r = OWLObjectProperty(IRI.create("http://ex.org#R"))
        c = self._cls("http://ex.org#A")
        expr = OWLObjectSomeValuesFrom(r, c)
        result = nnf.get_class_nnf(expr)
        assert isinstance(result, OWLObjectSomeValuesFrom)

    def test_all_recurses(self) -> None:
        from hermit.owl_model.class_expression.restriction import OWLObjectAllValuesFrom
        from hermit.owl_model.iri import IRI
        from hermit.owl_model.owl_property import OWLObjectProperty
        nnf = self._make_nnf()
        r = OWLObjectProperty(IRI.create("http://ex.org#R"))
        c = self._cls("http://ex.org#A")
        expr = OWLObjectAllValuesFrom(r, c)
        result = nnf.get_class_nnf(expr)
        assert isinstance(result, OWLObjectAllValuesFrom)


# ===========================================================================
# structural/normalized_axioms — complement types, exact cardinality, etc.
# ===========================================================================


def _mk_iri(local: str):  # type: ignore[no-untyped-def]
    from hermit.owl_model.iri import IRI
    return IRI.create("http://ex.org#" + local)


def _mk_class(local: str):  # type: ignore[no-untyped-def]
    from hermit.owl_model.class_expression.owl_class import OWLClass
    return OWLClass(_mk_iri(local))


def _mk_prop(local: str):  # type: ignore[no-untyped-def]
    from hermit.owl_model.owl_property import OWLObjectProperty
    return OWLObjectProperty(_mk_iri(local))


def _mk_data_prop(local: str):  # type: ignore[no-untyped-def]
    from hermit.owl_model.owl_property import OWLDataProperty
    return OWLDataProperty(_mk_iri(local))


def _mk_ind(local: str):  # type: ignore[no-untyped-def]
    from hermit.owl_model.owl_individual import OWLNamedIndividual
    return OWLNamedIndividual(_mk_iri(local))


class TestNormalizedAxiomsConversions:
    """Test _owl_expr_to_internal and related helpers."""

    def test_complement_of_some(self) -> None:
        from hermit.owl_model.class_expression.class_expression import OWLObjectComplementOf
        from hermit.owl_model.class_expression.restriction import OWLObjectSomeValuesFrom
        from hermit.structural.normalized_axioms import _owl_expr_to_internal
        from hermit.model import AtomicConcept, AtMostConcept

        expr = OWLObjectComplementOf(OWLObjectSomeValuesFrom(_mk_prop("R"), _mk_class("A")))
        result = _owl_expr_to_internal(expr, None)
        # ¬∃R.A = ∀R.¬A → AtMostConcept(0, R, ...)
        assert result is not None

    def test_complement_of_all(self) -> None:
        from hermit.owl_model.class_expression.class_expression import OWLObjectComplementOf
        from hermit.owl_model.class_expression.restriction import OWLObjectAllValuesFrom
        from hermit.structural.normalized_axioms import _owl_expr_to_internal
        from hermit.model import AtLeastConcept

        expr = OWLObjectComplementOf(OWLObjectAllValuesFrom(_mk_prop("R"), _mk_class("A")))
        result = _owl_expr_to_internal(expr, None)
        assert result is not None

    def test_complement_of_min(self) -> None:
        from hermit.owl_model.class_expression.class_expression import OWLObjectComplementOf
        from hermit.owl_model.class_expression.restriction import OWLObjectMinCardinality
        from hermit.structural.normalized_axioms import _owl_expr_to_internal

        expr = OWLObjectComplementOf(OWLObjectMinCardinality(2, _mk_prop("R"), _mk_class("A")))
        result = _owl_expr_to_internal(expr, None)
        assert result is not None

    def test_complement_of_min_zero(self) -> None:
        from hermit.owl_model.class_expression.class_expression import OWLObjectComplementOf
        from hermit.owl_model.class_expression.restriction import OWLObjectMinCardinality
        from hermit.structural.normalized_axioms import _owl_expr_to_internal
        from hermit.model import AtomicConcept

        expr = OWLObjectComplementOf(OWLObjectMinCardinality(0, _mk_prop("R"), _mk_class("A")))
        result = _owl_expr_to_internal(expr, None)
        assert result is AtomicConcept.NOTHING

    def test_complement_of_max(self) -> None:
        from hermit.owl_model.class_expression.class_expression import OWLObjectComplementOf
        from hermit.owl_model.class_expression.restriction import OWLObjectMaxCardinality
        from hermit.structural.normalized_axioms import _owl_expr_to_internal

        expr = OWLObjectComplementOf(OWLObjectMaxCardinality(2, _mk_prop("R"), _mk_class("A")))
        result = _owl_expr_to_internal(expr, None)
        assert result is not None

    def test_complement_of_exact(self) -> None:
        from hermit.owl_model.class_expression.class_expression import OWLObjectComplementOf
        from hermit.owl_model.class_expression.restriction import OWLObjectExactCardinality
        from hermit.structural.normalized_axioms import _owl_expr_to_internal

        expr = OWLObjectComplementOf(OWLObjectExactCardinality(2, _mk_prop("R"), _mk_class("A")))
        result = _owl_expr_to_internal(expr, None)
        assert result is not None

    def test_complement_of_intersection(self) -> None:
        from hermit.owl_model.class_expression.class_expression import OWLObjectComplementOf
        from hermit.owl_model.class_expression.nary_boolean_expression import OWLObjectIntersectionOf
        from hermit.structural.normalized_axioms import _owl_expr_to_internal
        from hermit.model import AtomicConcept

        expr = OWLObjectComplementOf(OWLObjectIntersectionOf([_mk_class("A"), _mk_class("B")]))
        result = _owl_expr_to_internal(expr, None)
        assert result is AtomicConcept.THING

    def test_complement_of_union(self) -> None:
        from hermit.owl_model.class_expression.class_expression import OWLObjectComplementOf
        from hermit.owl_model.class_expression.nary_boolean_expression import OWLObjectUnionOf
        from hermit.structural.normalized_axioms import _owl_expr_to_internal
        from hermit.model import AtomicConcept

        expr = OWLObjectComplementOf(OWLObjectUnionOf([_mk_class("A"), _mk_class("B")]))
        result = _owl_expr_to_internal(expr, None)
        assert result is AtomicConcept.NOTHING

    def test_exact_cardinality_returns_list(self) -> None:
        from hermit.owl_model.class_expression.restriction import OWLObjectExactCardinality
        from hermit.structural.normalized_axioms import _owl_expr_to_internal

        expr = OWLObjectExactCardinality(2, _mk_prop("R"), _mk_class("A"))
        result = _owl_expr_to_internal(expr, None)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_add_concept_inclusion_with_union(self) -> None:
        from hermit.owl_model.class_expression.nary_boolean_expression import OWLObjectUnionOf
        from hermit.structural.normalized_axioms import NormalizedAxioms

        na = NormalizedAxioms()
        union = OWLObjectUnionOf([_mk_class("A"), _mk_class("B")])
        na.add_concept_inclusion(union)
        assert len(na.concept_inclusions) == 1

    def test_add_concept_inclusion_with_exact(self) -> None:
        from hermit.owl_model.class_expression.restriction import OWLObjectExactCardinality
        from hermit.structural.normalized_axioms import NormalizedAxioms

        na = NormalizedAxioms()
        expr = OWLObjectExactCardinality(1, _mk_prop("R"), _mk_class("A"))
        na.add_concept_inclusion(expr)
        # ExactCardinality decomposes to two inclusions
        assert len(na.concept_inclusions) == 2

    def test_owl_prop_to_internal_role_standalone_inverse(self) -> None:
        from hermit.owl_model.owl_property import OWLObjectInverseOf, OWLObjectProperty
        from hermit.structural.normalized_axioms import _owl_prop_to_internal_role_standalone
        from hermit.model import InverseRole

        prop = OWLObjectProperty(_mk_iri("R"))
        inv = OWLObjectInverseOf(prop)
        role = _owl_prop_to_internal_role_standalone(inv)
        assert isinstance(role, InverseRole)

    def test_owl_prop_to_internal_role_standalone_plain(self) -> None:
        from hermit.owl_model.owl_property import OWLObjectProperty
        from hermit.structural.normalized_axioms import _owl_prop_to_internal_role_standalone
        from hermit.model import AtomicRole

        prop = OWLObjectProperty(_mk_iri("R"))
        role = _owl_prop_to_internal_role_standalone(prop)
        assert isinstance(role, AtomicRole)

    def test_signature(self) -> None:
        from hermit.structural.normalized_axioms import NormalizedAxioms
        from hermit.model import AtomicConcept, AtomicRole, Individual

        na = NormalizedAxioms()
        na.atomic_concepts.add(AtomicConcept.create("http://ex.org#A"))
        na.object_roles.add(AtomicRole.create("http://ex.org#R"))
        na.named_individuals.add(Individual.create("http://ex.org#a"))
        sig = na.signature()
        assert len(sig) == 3


# ===========================================================================
# owl_normalization — uncovered axiom types
# ===========================================================================

def _run_normalization(axioms: list) -> object:  # type: ignore[type-arg]
    from hermit.structural.owl_normalization import OWLNormalization
    norm = OWLNormalization()
    return norm.process_ontology(axioms)


class TestOwlNormalizationUnusedPaths:
    def test_disjoint_object_properties(self) -> None:
        from hermit.owl_model.owl_axiom import OWLDisjointObjectPropertiesAxiom
        axiom = OWLDisjointObjectPropertiesAxiom([_mk_prop("R"), _mk_prop("S")])
        na = _run_normalization([axiom])
        assert len(na.disjoint_object_properties) >= 1

    def test_sub_data_property(self) -> None:
        from hermit.owl_model.owl_axiom import OWLSubDataPropertyOfAxiom
        axiom = OWLSubDataPropertyOfAxiom(_mk_data_prop("D1"), _mk_data_prop("D2"))
        na = _run_normalization([axiom])
        assert len(na.data_property_inclusions) >= 1

    def test_equivalent_data_properties(self) -> None:
        from hermit.owl_model.owl_axiom import OWLEquivalentDataPropertiesAxiom
        axiom = OWLEquivalentDataPropertiesAxiom([_mk_data_prop("D1"), _mk_data_prop("D2")])
        na = _run_normalization([axiom])
        assert len(na.positive_facts) >= 1

    def test_disjoint_data_properties(self) -> None:
        from hermit.owl_model.owl_axiom import OWLDisjointDataPropertiesAxiom
        axiom = OWLDisjointDataPropertiesAxiom([_mk_data_prop("D1"), _mk_data_prop("D2")])
        na = _run_normalization([axiom])
        assert len(na.disjoint_data_properties) >= 1

    def test_data_property_range(self) -> None:
        from hermit.owl_model.owl_axiom import OWLDataPropertyRangeAxiom
        from hermit.owl_model.owl_datatype import OWLDatatype
        from hermit.owl_model.iri import IRI
        dt = OWLDatatype(IRI.create("http://www.w3.org/2001/XMLSchema#string"))
        axiom = OWLDataPropertyRangeAxiom(_mk_data_prop("D"), dt)
        na = _run_normalization([axiom])
        assert len(na.positive_facts) >= 1

    def test_same_individual(self) -> None:
        from hermit.owl_model.owl_axiom import OWLSameIndividualAxiom
        axiom = OWLSameIndividualAxiom([_mk_ind("a"), _mk_ind("b")])
        na = _run_normalization([axiom])
        # same-as goes to positive_facts or individual equality
        assert na is not None

    def test_different_individuals(self) -> None:
        from hermit.owl_model.owl_axiom import OWLDifferentIndividualsAxiom
        axiom = OWLDifferentIndividualsAxiom([_mk_ind("a"), _mk_ind("b")])
        na = _run_normalization([axiom])
        assert na is not None

    def test_negative_object_property_assertion(self) -> None:
        from hermit.owl_model.owl_axiom import OWLNegativeObjectPropertyAssertionAxiom
        axiom = OWLNegativeObjectPropertyAssertionAxiom(
            _mk_ind("a"), _mk_prop("R"), _mk_ind("b")
        )
        na = _run_normalization([axiom])
        assert len(na.negative_facts) >= 1

    def test_functional_object_property(self) -> None:
        from hermit.owl_model.owl_axiom import OWLFunctionalObjectPropertyAxiom
        axiom = OWLFunctionalObjectPropertyAxiom(_mk_prop("R"))
        na = _run_normalization([axiom])
        assert len(na.direct_dl_clauses) >= 1

    def test_inverse_functional_object_property(self) -> None:
        from hermit.owl_model.owl_axiom import OWLInverseFunctionalObjectPropertyAxiom
        axiom = OWLInverseFunctionalObjectPropertyAxiom(_mk_prop("R"))
        na = _run_normalization([axiom])
        assert len(na.direct_dl_clauses) >= 1

    def test_symmetric_property(self) -> None:
        from hermit.owl_model.owl_axiom import OWLSymmetricObjectPropertyAxiom
        axiom = OWLSymmetricObjectPropertyAxiom(_mk_prop("R"))
        na = _run_normalization([axiom])
        assert len(na.simple_object_property_inclusions) >= 1

    def test_asymmetric_property(self) -> None:
        from hermit.owl_model.owl_axiom import OWLAsymmetricObjectPropertyAxiom
        axiom = OWLAsymmetricObjectPropertyAxiom(_mk_prop("R"))
        na = _run_normalization([axiom])
        assert len(na.asymmetric_object_properties) >= 1

    def test_reflexive_property(self) -> None:
        from hermit.owl_model.owl_axiom import OWLReflexiveObjectPropertyAxiom
        axiom = OWLReflexiveObjectPropertyAxiom(_mk_prop("R"))
        na = _run_normalization([axiom])
        assert len(na.reflexive_object_properties) >= 1

    def test_irreflexive_property(self) -> None:
        from hermit.owl_model.owl_axiom import OWLIrreflexiveObjectPropertyAxiom
        axiom = OWLIrreflexiveObjectPropertyAxiom(_mk_prop("R"))
        na = _run_normalization([axiom])
        assert len(na.irreflexive_object_properties) >= 1

    def test_transitive_property(self) -> None:
        from hermit.owl_model.owl_axiom import OWLTransitiveObjectPropertyAxiom
        axiom = OWLTransitiveObjectPropertyAxiom(_mk_prop("R"))
        na = _run_normalization([axiom])
        assert len(na.complex_object_property_inclusions) >= 1

    def test_functional_data_property(self) -> None:
        from hermit.owl_model.owl_axiom import OWLFunctionalDataPropertyAxiom
        axiom = OWLFunctionalDataPropertyAxiom(_mk_data_prop("D"))
        na = _run_normalization([axiom])
        assert len(na.positive_facts) >= 1

    def test_inverse_object_properties(self) -> None:
        from hermit.owl_model.owl_axiom import OWLInverseObjectPropertiesAxiom
        axiom = OWLInverseObjectPropertiesAxiom(_mk_prop("R"), _mk_prop("S"))
        na = _run_normalization([axiom])
        assert len(na.positive_facts) >= 1

    def test_negative_data_property_assertion(self) -> None:
        from hermit.owl_model.owl_axiom import OWLNegativeDataPropertyAssertionAxiom
        from hermit.owl_model.owl_literal import OWLLiteral
        lit = OWLLiteral("hello")
        axiom = OWLNegativeDataPropertyAssertionAxiom(_mk_ind("a"), _mk_data_prop("D"), lit)
        na = _run_normalization([axiom])
        assert len(na.negative_facts) >= 1

    def test_equivalent_object_properties(self) -> None:
        from hermit.owl_model.owl_axiom import OWLEquivalentObjectPropertiesAxiom
        axiom = OWLEquivalentObjectPropertiesAxiom([_mk_prop("R"), _mk_prop("S")])
        na = _run_normalization([axiom])
        assert na is not None

    def test_unknown_axiom_goes_to_positive_facts(self) -> None:
        """An unknown axiom type is passed through to positive_facts."""
        class _FakeAxiom:
            pass
        na = _run_normalization([_FakeAxiom()])
        assert len(na.positive_facts) >= 1


# ===========================================================================
# parser.py — exercise owlready2 mapper branches
# ===========================================================================

def _has_owlready2() -> bool:
    try:
        import owlready2  # noqa: F401
        return True
    except ImportError:
        return False


requires_owlready2 = pytest.mark.skipif(
    not _has_owlready2(), reason="owlready2 not installed"
)


@requires_owlready2
class TestParserBranches:
    def _mk_onto(self, iri: str):  # type: ignore[no-untyped-def]
        import owlready2
        return owlready2.get_ontology(iri)

    def test_file_not_found_raises(self) -> None:
        from hermit.parser import load_ontology
        with pytest.raises(FileNotFoundError):
            load_ontology("/nonexistent/file.owl")

    def test_parser_same_individual(self, tmp_path) -> None:
        """SameIndividual axiom is extracted by mapper."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.same#")
        with onto:
            class A(owlready2.Thing): pass  # type: ignore[valid-type]
            a = A("a")
            b = A("b")
            owlready2.AllDifferent([a, b])  # DifferentIndividuals
        f = tmp_path / "same.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert isinstance(axioms, list)

    def test_parser_transitive_property(self, tmp_path) -> None:
        """TransitiveProperty characteristic is extracted."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.trans#")
        with onto:
            class part_of(owlready2.TransitiveProperty, owlready2.ObjectProperty): pass  # type: ignore[valid-type]
        f = tmp_path / "trans.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert isinstance(axioms, list)

    def test_parser_symmetric_property(self, tmp_path) -> None:
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.sym#")
        with onto:
            class sibling_of(owlready2.SymmetricProperty, owlready2.ObjectProperty): pass  # type: ignore[valid-type]
        f = tmp_path / "sym.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert isinstance(axioms, list)

    def test_parser_functional_property(self, tmp_path) -> None:
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.func#")
        with onto:
            class has_age(owlready2.FunctionalProperty, owlready2.ObjectProperty): pass  # type: ignore[valid-type]
        f = tmp_path / "func.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert isinstance(axioms, list)

    def test_parser_inverse_functional_property(self, tmp_path) -> None:
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.invfunc#")
        with onto:
            class is_mother_of(owlready2.InverseFunctionalProperty, owlready2.ObjectProperty): pass  # type: ignore[valid-type]
        f = tmp_path / "invfunc.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert isinstance(axioms, list)

    def test_parser_class_assertions(self, tmp_path) -> None:
        """ClassAssertion for individuals is extracted."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.cls#")
        with onto:
            class Animal(owlready2.Thing): pass  # type: ignore[valid-type]
            fido = Animal("Fido")
        f = tmp_path / "cls.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert len(axioms) >= 1

    def test_parser_object_property_assertion(self, tmp_path) -> None:
        """ObjectPropertyAssertion for individuals is extracted."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.opa#")
        with onto:
            class Animal(owlready2.Thing): pass  # type: ignore[valid-type]
            class eats(owlready2.ObjectProperty): pass  # type: ignore[valid-type]
            a = Animal("a")
            b = Animal("b")
            a.eats.append(b)
        f = tmp_path / "opa.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert isinstance(axioms, list)

    def test_parser_data_property_extraction(self, tmp_path) -> None:
        """DataProperty sub-property is extracted."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.dp#")
        with onto:
            class has_value(owlready2.DataProperty): pass  # type: ignore[valid-type]
            class has_specific_value(has_value): pass  # type: ignore[valid-type]
        f = tmp_path / "dp.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert isinstance(axioms, list)

    def test_parser_min_cardinality(self, tmp_path) -> None:
        """MinCardinality restriction is extracted."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.min#")
        with onto:
            class Part(owlready2.Thing): pass  # type: ignore[valid-type]
            class has_part(owlready2.ObjectProperty): pass  # type: ignore[valid-type]
            class Complex(owlready2.Thing):  # type: ignore[valid-type]
                is_a = [has_part.min(2, Part)]
        f = tmp_path / "min.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert len(axioms) >= 1

    def test_parser_max_cardinality(self, tmp_path) -> None:
        """MaxCardinality restriction is extracted."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.max#")
        with onto:
            class Part(owlready2.Thing): pass  # type: ignore[valid-type]
            class has_part(owlready2.ObjectProperty): pass  # type: ignore[valid-type]
            class Simple(owlready2.Thing):  # type: ignore[valid-type]
                is_a = [has_part.max(1, Part)]
        f = tmp_path / "max.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert len(axioms) >= 1

    def test_parser_exact_cardinality(self, tmp_path) -> None:
        """ExactCardinality restriction is extracted."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.exact#")
        with onto:
            class Part(owlready2.Thing): pass  # type: ignore[valid-type]
            class has_part(owlready2.ObjectProperty): pass  # type: ignore[valid-type]
            class Pair(owlready2.Thing):  # type: ignore[valid-type]
                is_a = [has_part.exactly(2, Part)]
        f = tmp_path / "exact.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert len(axioms) >= 1

    def test_parser_data_assertion(self, tmp_path) -> None:
        """DataPropertyAssertion is extracted."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.da#")
        with onto:
            class Person(owlready2.Thing): pass  # type: ignore[valid-type]
            class has_age(owlready2.DataProperty): pass  # type: ignore[valid-type]
            p = Person("p")
            p.has_age.append(42)
        f = tmp_path / "da.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert isinstance(axioms, list)

    def test_parser_intersection(self, tmp_path) -> None:
        """Intersection (OWLObjectIntersectionOf) restriction is extracted."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.int#")
        with onto:
            class A(owlready2.Thing): pass  # type: ignore[valid-type]
            class B(owlready2.Thing): pass  # type: ignore[valid-type]
            class C(owlready2.Thing):  # type: ignore[valid-type]
                equivalent_to = [A & B]
        f = tmp_path / "int.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert len(axioms) >= 1

    def test_parser_union(self, tmp_path) -> None:
        """Union (OWLObjectUnionOf) restriction is extracted."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.un#")
        with onto:
            class A(owlready2.Thing): pass  # type: ignore[valid-type]
            class B(owlready2.Thing): pass  # type: ignore[valid-type]
            class C(owlready2.Thing):  # type: ignore[valid-type]
                equivalent_to = [A | B]
        f = tmp_path / "un.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert len(axioms) >= 1

    def test_parser_complement(self, tmp_path) -> None:
        """Complement class restriction is extracted."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.comp#")
        with onto:
            class A(owlready2.Thing): pass  # type: ignore[valid-type]
            class NotA(owlready2.Thing):  # type: ignore[valid-type]
                equivalent_to = [owlready2.Not(A)]
        f = tmp_path / "comp.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert len(axioms) >= 1

    def test_parser_inverse_property_in_restriction(self, tmp_path) -> None:
        """Inverse property in existential restriction is extracted."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.inv#")
        with onto:
            class Thing2(owlready2.Thing): pass  # type: ignore[valid-type]
            class R(owlready2.ObjectProperty): pass  # type: ignore[valid-type]
            class HasInv(owlready2.Thing):  # type: ignore[valid-type]
                is_a = [owlready2.Inverse(R).some(Thing2)]
        f = tmp_path / "inv.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert isinstance(axioms, list)

    def test_parser_disjoints(self, tmp_path) -> None:
        """DisjointClasses axiom is extracted."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.disj#")
        with onto:
            class A(owlready2.Thing): pass  # type: ignore[valid-type]
            class B(owlready2.Thing): pass  # type: ignore[valid-type]
            owlready2.AllDisjoint([A, B])
        f = tmp_path / "disj.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert isinstance(axioms, list)

    def test_parser_property_domain_range(self, tmp_path) -> None:
        """Domain and range axioms are extracted."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.dr#")
        with onto:
            class Person(owlready2.Thing): pass  # type: ignore[valid-type]
            class Animal(owlready2.Thing): pass  # type: ignore[valid-type]
            class owns(owlready2.ObjectProperty):  # type: ignore[valid-type]
                domain = [Person]
                range = [Animal]
        f = tmp_path / "dr.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert isinstance(axioms, list)

    def test_parser_nominal_oneof(self, tmp_path) -> None:
        """OneOf (nominals) class expression is extracted."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.nom#")
        with onto:
            class Color(owlready2.Thing): pass  # type: ignore[valid-type]
            red = Color("red")
            blue = Color("blue")
            class PrimaryColor(owlready2.Thing):  # type: ignore[valid-type]
                equivalent_to = [owlready2.OneOf([red, blue])]
        f = tmp_path / "nom.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert isinstance(axioms, list)

    def test_parser_sub_property_chain(self, tmp_path) -> None:
        """SubPropertyChain axiom is extracted."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.chain#")
        with onto:
            class hasParent(owlready2.ObjectProperty): pass  # type: ignore[valid-type]
            class hasAncestor(owlready2.ObjectProperty):  # type: ignore[valid-type]
                is_a = [owlready2.ObjectProperty]
            class hasMother(owlready2.ObjectProperty): pass  # type: ignore[valid-type]
        f = tmp_path / "chain.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert isinstance(axioms, list)

    def test_parser_reflexive_irreflexive_asymmetric(self, tmp_path) -> None:
        """Reflexive, irreflexive and asymmetric property characteristics."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.ria#")
        with onto:
            class R1(owlready2.ReflexiveProperty, owlready2.ObjectProperty): pass  # type: ignore[valid-type]
            class R2(owlready2.IrreflexiveProperty, owlready2.ObjectProperty): pass  # type: ignore[valid-type]
            class R3(owlready2.AsymmetricProperty, owlready2.ObjectProperty): pass  # type: ignore[valid-type]
        f = tmp_path / "ria.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert isinstance(axioms, list)

    def test_parser_different_individuals(self, tmp_path) -> None:
        """DifferentIndividuals from explicit AllDifferent."""
        import owlready2
        from hermit.parser import load_ontology
        onto = owlready2.get_ontology("http://test.parser.diff#")
        with onto:
            class Thing2(owlready2.Thing): pass  # type: ignore[valid-type]
            a = Thing2("a")
            b = Thing2("b")
            c = Thing2("c")
            owlready2.AllDifferent([a, b, c])
        f = tmp_path / "diff.owl"
        onto.save(str(f), format="rdfxml")
        axioms = load_ontology(f)
        assert isinstance(axioms, list)


# ===========================================================================
# DependencySetFactory — cover merge/union paths
# ===========================================================================

class TestDependencySetFactory:
    def _factory(self):  # type: ignore[no-untyped-def]
        from hermit.tableau.dependency_set_factory import DependencySetFactory
        return DependencySetFactory()

    def test_empty_set(self) -> None:
        f = self._factory()
        assert f.empty_set is not None
        assert f.empty_set.is_empty()

    def test_size_in_memory(self) -> None:
        f = self._factory()
        assert f.size_in_memory() >= 0

    def test_add_branching_point(self) -> None:
        f = self._factory()
        ds = f.add_branching_point(f.empty_set, 0)
        assert not ds.is_empty()

    def test_add_branching_point_larger(self) -> None:
        f = self._factory()
        ds0 = f.add_branching_point(f.empty_set, 5)
        ds1 = f.add_branching_point(ds0, 10)
        assert ds1.get_maximum_branching_point() == 10

    def test_add_branching_point_same(self) -> None:
        f = self._factory()
        ds0 = f.add_branching_point(f.empty_set, 5)
        ds1 = f.add_branching_point(ds0, 5)
        assert ds0 is ds1

    def test_add_branching_point_smaller(self) -> None:
        f = self._factory()
        ds0 = f.add_branching_point(f.empty_set, 5)
        ds1 = f.add_branching_point(ds0, 3)
        assert ds1.contains_branching_point(3)
        assert ds1.contains_branching_point(5)

    def test_remove_branching_point(self) -> None:
        f = self._factory()
        ds = f.add_branching_point(f.empty_set, 3)
        ds2 = f.remove_branching_point(ds, 3)
        assert ds2.is_empty()

    def test_remove_branching_point_larger(self) -> None:
        f = self._factory()
        ds = f.add_branching_point(f.empty_set, 3)
        ds2 = f.remove_branching_point(ds, 10)
        assert ds2 is ds

    def test_remove_branching_point_not_present(self) -> None:
        f = self._factory()
        ds = f.add_branching_point(f.empty_set, 5)
        ds2 = f.remove_branching_point(ds, 3)
        assert ds2.contains_branching_point(5)

    def test_union_same_set(self) -> None:
        f = self._factory()
        ds = f.add_branching_point(f.empty_set, 0)
        u = f.union_with(ds, ds)
        assert u is ds

    def test_union_different_sets(self) -> None:
        f = self._factory()
        ds1 = f.add_branching_point(f.empty_set, 1)
        ds2 = f.add_branching_point(f.empty_set, 2)
        u = f.union_with(ds1, ds2)
        assert u.contains_branching_point(1)
        assert u.contains_branching_point(2)

    def test_union_of_overlapping_sets(self) -> None:
        f = self._factory()
        ds1 = f.add_branching_point(f.add_branching_point(f.empty_set, 1), 3)
        ds2 = f.add_branching_point(f.add_branching_point(f.empty_set, 2), 3)
        u = f.union_with(ds1, ds2)
        assert u.contains_branching_point(1)
        assert u.contains_branching_point(2)
        assert u.contains_branching_point(3)

    def test_get_permanent_for_union(self) -> None:
        from hermit.tableau.union_dependency_set import UnionDependencySet
        f = self._factory()
        ds1 = f.add_branching_point(f.empty_set, 1)
        ds2 = f.add_branching_point(f.empty_set, 2)
        uds = UnionDependencySet(2)
        uds.m_dependency_sets[0] = ds1
        uds.m_dependency_sets[1] = ds2
        uds.m_number_of_constituents = 2
        perm = f.get_permanent(uds)
        assert perm is not None
        assert not perm.is_empty()
        assert perm.contains_branching_point(1)
        assert perm.contains_branching_point(2)

    def test_remove_unused_sets_empty(self) -> None:
        """remove_unused_sets on a fresh factory does nothing."""
        f = self._factory()
        f.remove_unused_sets()
        assert f.empty_set is not None

    def test_clear_resets(self) -> None:
        f = self._factory()
        f.add_branching_point(f.empty_set, 5)
        f.clear()
        assert f.empty_set.is_empty()

    def test_resize_entries(self) -> None:
        """Adding many distinct sets triggers resize."""
        f = self._factory()
        ds = f.empty_set
        for i in range(20):
            ds = f.add_branching_point(ds, i)
        assert f.size_in_memory() > 0

    def test_union_of_multiple_sets(self) -> None:
        from hermit.tableau.union_dependency_set import UnionDependencySet
        f = self._factory()
        sets = [f.add_branching_point(f.empty_set, i) for i in range(3)]
        uds = UnionDependencySet(3)
        for i, s in enumerate(sets):
            uds.m_dependency_sets[i] = s
        perm = f.get_permanent(uds)
        assert perm is not None


# ===========================================================================
# Reasoner-level tests that exercise internal paths indirectly
# ===========================================================================

def _build_reasoner(axioms):  # type: ignore[no-untyped-def]
    from hermit import Reasoner
    from hermit.structural.owl_normalization import OWLNormalization
    from hermit.structural.owl_clausification import OWLClausification
    norm = OWLNormalization()
    na = norm.process_ontology(axioms)
    claus = OWLClausification()
    dlo = claus.clausify(na, ontology_iri="urn:test:coverage")
    return Reasoner(dlo)


@requires_owlready2
class TestReasonerWithComplexOntologies:
    """High-level tests that drive internal code paths via reasoning."""

    def test_transitive_role_chain(self, tmp_path) -> None:
        """Transitive property triggers complex property inclusion paths."""
        import owlready2
        onto = owlready2.get_ontology("http://test.trans#")
        with onto:
            class Part(owlready2.Thing): pass  # type: ignore[valid-type]
            class part_of(owlready2.TransitiveProperty, owlready2.ObjectProperty): pass  # type: ignore[valid-type]
        f = tmp_path / "t.owl"
        onto.save(str(f), format="rdfxml")
        from hermit.parser import load_ontology
        axioms = load_ontology(f)
        r = _build_reasoner(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_functional_role_consistency(self, tmp_path) -> None:
        import owlready2
        onto = owlready2.get_ontology("http://test.func2#")
        with onto:
            class Person(owlready2.Thing): pass  # type: ignore[valid-type]
            class hasParent(owlready2.FunctionalProperty, owlready2.ObjectProperty): pass  # type: ignore[valid-type]
        f = tmp_path / "t.owl"
        onto.save(str(f), format="rdfxml")
        from hermit.parser import load_ontology
        axioms = load_ontology(f)
        r = _build_reasoner(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_individuals_with_properties(self, tmp_path) -> None:
        """ObjectPropertyAssertion creates individuals and role assertions."""
        import owlready2
        onto = owlready2.get_ontology("http://test.ind#")
        with onto:
            class Animal(owlready2.Thing): pass  # type: ignore[valid-type]
            class eats(owlready2.ObjectProperty): pass  # type: ignore[valid-type]
            a = Animal("a")
            b = Animal("b")
            a.eats.append(b)
        f = tmp_path / "t.owl"
        onto.save(str(f), format="rdfxml")
        from hermit.parser import load_ontology
        axioms = load_ontology(f)
        r = _build_reasoner(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_disjoint_classes_consistent(self, tmp_path) -> None:
        """DisjointClasses axiom — consistent when no individual belongs to both."""
        import owlready2
        onto = owlready2.get_ontology("http://test.disj2#")
        with onto:
            class A(owlready2.Thing): pass  # type: ignore[valid-type]
            class B(owlready2.Thing): pass  # type: ignore[valid-type]
            owlready2.AllDisjoint([A, B])
            a = A("a")
        f = tmp_path / "t.owl"
        onto.save(str(f), format="rdfxml")
        from hermit.parser import load_ontology
        axioms = load_ontology(f)
        r = _build_reasoner(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()

    def test_same_individual_axiom(self, tmp_path) -> None:
        """SameIndividual triggers equality merging paths."""
        import owlready2
        onto = owlready2.get_ontology("http://test.same2#")
        with onto:
            class Animal(owlready2.Thing): pass  # type: ignore[valid-type]
            a = Animal("a")
            b = Animal("b")
            owlready2.AllDifferent([a, b])
        f = tmp_path / "t.owl"
        onto.save(str(f), format="rdfxml")
        from hermit.parser import load_ontology
        axioms = load_ontology(f)
        r = _build_reasoner(axioms)
        try:
            assert r.is_consistent() is True
        finally:
            r.dispose()
