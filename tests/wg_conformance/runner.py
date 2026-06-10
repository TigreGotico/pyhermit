"""Runs a single WG conformance subtest through pyhermit.

This mirrors the upstream JUnit test classes:

  * ``ConsistencyTest.doTest()``  -> ``assertEquals(positive, reasoner.isConsistent())``
  * ``EntailmentTest.doTest()``   -> ``EntailmentChecker.entails(conclusion.getLogicalAxioms())``

The premise / conclusion ontologies are the strings embedded in ``all.rdf``;
they are written to a temp file and loaded with pyhermit's owlready2-backed
parser (same role the OWL API plays for the Java harness).

Entailment is reduced to reasoner queries exactly like the Java
``EntailmentChecker`` (an ``OWLAxiomVisitorEx``): each conclusion axiom is
turned into subsumption / satisfiability / instance queries. Because pyhermit's
``Reasoner`` answers subsumption only between *atomic* concepts, complex class
expressions are handled the way HermiT itself does -- by adding definitorial
axioms ``Q == expr`` to the premise and querying the fresh atomic ``Q``.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass

from hermit.configuration import Configuration
from hermit.model import AtomicConcept, AtomicRole, Individual
from hermit.owl_model.class_expression import (
    OWLClass,
    OWLClassExpression,
    OWLObjectAllValuesFrom,
    OWLObjectComplementOf,
)
from hermit.owl_model.class_expression.restriction import OWLDataSomeValuesFrom
from hermit.owl_model.owl_axiom import (
    OWLClassAssertionAxiom,
    OWLDataPropertyAssertionAxiom,
    OWLDataPropertyRangeAxiom,
    OWLDifferentIndividualsAxiom,
    OWLDisjointClassesAxiom,
    OWLEquivalentClassesAxiom,
    OWLEquivalentObjectPropertiesAxiom,
    OWLObjectPropertyAssertionAxiom,
    OWLObjectPropertyDomainAxiom,
    OWLObjectPropertyRangeAxiom,
    OWLSameIndividualAxiom,
    OWLSubClassOfAxiom,
    OWLSubDataPropertyOfAxiom,
    OWLSubObjectPropertyOfAxiom,
    OWLSymmetricObjectPropertyAxiom,
    OWLTransitiveObjectPropertyAxiom,
)
from hermit.owl_model.owl_individual import OWLNamedIndividual
from hermit.parser import load_ontology
from hermit.reasoner import Reasoner
from hermit.structural.owl_clausification import OWLClausification
from hermit.structural.owl_normalization import OWLNormalization

from .registry import Subtest, TestType, format_extension

_AUX = "http://pyhermit.invalid/wg/aux#"


class UnsupportedConclusion(Exception):
    """Raised when a conclusion axiom form is not yet faithfully checkable."""


@dataclass
class Outcome:
    passed: bool
    detail: str


def _load_axioms(text: str, fmt: str) -> list:
    ext = format_extension(fmt)
    fd, path = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        return load_ontology(path)
    finally:
        os.unlink(path)


def _build_reasoner(axioms: list, use_disjunction_learning: bool) -> Reasoner:
    config = Configuration()
    config.throw_inconsistent_ontology_exception = False
    config.use_disjunction_learning = use_disjunction_learning
    norm = OWLNormalization().process_ontology(axioms)
    onto = OWLClausification().clausify(norm, ontology_iri="urn:test:wg")
    return Reasoner(onto, config)


# ---------------------------------------------------------------------------
# Consistency / Inconsistency
# ---------------------------------------------------------------------------

def run_consistency(subtest: Subtest) -> Outcome:
    res = subtest.descriptor.premise_string()
    if res is None:
        axioms: list = []
    else:
        fmt, text = res
        axioms = _load_axioms(text, fmt)
    reasoner = _build_reasoner(axioms, subtest.use_disjunction_learning)
    try:
        consistent = reasoner.is_consistent()
        expected = subtest.positive  # True => ConsistencyTest, False => Inconsistency
        return Outcome(consistent == expected, f"isConsistent={consistent} expected={expected}")
    finally:
        reasoner.dispose()


# ---------------------------------------------------------------------------
# Entailment / NonEntailment
# ---------------------------------------------------------------------------

def _name(c: OWLClass) -> str:
    iri = getattr(c, "iri", None)
    if iri is None:
        return str(c)
    return iri.as_str() if hasattr(iri, "as_str") else str(iri)


def _atomic(expr: OWLClassExpression) -> AtomicConcept | None:
    """Return the AtomicConcept for a named class, else None for complex."""
    if isinstance(expr, OWLClass):
        return AtomicConcept.create(_name(expr))
    return None


def _entails_subclass(
    premise_axioms: list,
    sub: OWLClassExpression,
    sup: OWLClassExpression,
    udl: bool,
) -> bool:
    """premise |= sub <= sup, realized faithfully via definitorial atoms."""
    sub_atomic = _atomic(sub)
    sup_atomic = _atomic(sup)
    extra: list = []
    if sub_atomic is None:
        q_sub = OWLClass(_AUX + "Sub")
        extra.append(OWLEquivalentClassesAxiom([q_sub, sub]))
        sub_atomic = AtomicConcept.create(_AUX + "Sub")
    if sup_atomic is None:
        q_sup = OWLClass(_AUX + "Sup")
        extra.append(OWLEquivalentClassesAxiom([q_sup, sup]))
        sup_atomic = AtomicConcept.create(_AUX + "Sup")
    reasoner = _build_reasoner(premise_axioms + extra, udl)
    try:
        if not reasoner.is_consistent():
            # inconsistent premise entails everything
            return True
        return reasoner.is_sub_class_of(sub_atomic, sup_atomic)
    finally:
        reasoner.dispose()


def _entails_instance(
    premise_axioms: list, individual, expr: OWLClassExpression, udl: bool
) -> bool:
    """premise |= ClassAssertion(expr, individual), via reasoner.has_type."""
    ind = _individual_internal(individual)
    if ind is None:
        return False
    concept = _atomic(expr)
    extra: list = []
    if concept is None:
        q = OWLClass(_AUX + "Inst")
        extra.append(OWLEquivalentClassesAxiom([q, expr]))
        concept = AtomicConcept.create(_AUX + "Inst")
    reasoner = _build_reasoner(premise_axioms + extra, udl)
    try:
        if not reasoner.is_consistent():
            return True
        return reasoner.has_type(ind, concept)
    finally:
        reasoner.dispose()


def _individual_internal(individual):  # type: ignore[no-untyped-def]
    iri = getattr(individual, "iri", None)
    if iri is None:
        return None
    return Individual.create(iri.as_str() if hasattr(iri, "as_str") else str(iri))


def _entails_disjoint(
    premise_axioms: list, classes: list[OWLClassExpression], udl: bool
) -> bool:
    # Disjoint(c_i, c_j) iff c_i <= not c_j for all pairs (Java EntailmentChecker)
    for i in range(len(classes) - 1):
        for j in range(i + 1, len(classes)):
            if not _entails_subclass(
                premise_axioms, classes[i], OWLObjectComplementOf(classes[j]), udl
            ):
                return False
    return True


def _fresh_individuals(n: int) -> list[OWLNamedIndividual]:
    """Fresh ABox individuals in the aux namespace (disjoint from test data)."""
    return [OWLNamedIndividual(f"{_AUX}fresh{i}") for i in range(n)]


def _refutes(premise_axioms: list, counterexample: list, udl: bool) -> bool:
    """premise + counterexample axioms is inconsistent.

    Standard reduction: premise |= alpha iff premise plus a counterexample
    ABox for alpha (on fresh individuals) has no model.
    """
    reasoner = _build_reasoner(premise_axioms + counterexample, udl)
    try:
        return not reasoner.is_consistent()
    finally:
        reasoner.dispose()


def _denied_edge(x, prop, y) -> list:  # type: ignore[no-untyped-def]
    """Axioms whose models are exactly those where ``prop(x, y)`` is false.

    Pseudo-nominal encoding: a fresh marker class holds only ``y`` among
    relevant individuals, and ``x`` is asserted to reach no marker via
    ``prop``. The combination clashes iff every model connects x to y by
    prop.
    """
    marker = OWLClass(_AUX + "EdgeMarker")
    source = OWLClass(_AUX + "EdgeSource")
    return [
        OWLClassAssertionAxiom(y, marker),
        OWLClassAssertionAxiom(x, source),
        OWLSubClassOfAxiom(
            source, OWLObjectAllValuesFrom(prop, OWLObjectComplementOf(marker))
        ),
    ]


def _entails_subproperty(premise_axioms: list, sub, sup, udl: bool) -> bool:
    """premise |= SubObjectPropertyOf(sub sup): assert sub(a,b) and deny
    sup(a,b) on fresh individuals; entailed iff inconsistent."""
    a, b = _fresh_individuals(2)
    return _refutes(
        premise_axioms,
        [OWLObjectPropertyAssertionAxiom(a, sub, b), *_denied_edge(a, sup, b)],
        udl,
    )


def _entails_axiom(premise_axioms: list, axiom, udl: bool) -> bool:
    """Faithful per-axiom entailment, mirroring EntailmentChecker.visit(...)."""
    if isinstance(axiom, OWLSubClassOfAxiom):
        return _entails_subclass(
            premise_axioms, axiom.sub_class, axiom.super_class, udl
        )
    if isinstance(axiom, OWLEquivalentClassesAxiom):
        exprs = list(axiom.class_expressions())
        first = exprs[0]
        for nxt in exprs[1:]:
            if not _entails_subclass(premise_axioms, first, nxt, udl):
                return False
            if not _entails_subclass(premise_axioms, nxt, first, udl):
                return False
        return True
    if isinstance(axiom, OWLDisjointClassesAxiom):
        return _entails_disjoint(premise_axioms, list(axiom.class_expressions()), udl)
    if isinstance(axiom, OWLClassAssertionAxiom):
        # hasType(ind, C): mirrors EntailmentChecker.visit(ClassAssertion) ->
        # reasoner.isInstanceOf(ind, C). Complex C is named via a definitorial
        # equivalence and the instance check runs against the fresh atomic class.
        ind = axiom.get_individual()
        c = axiom.get_class_expression()
        return _entails_instance(premise_axioms, ind, c, udl)
    if isinstance(axiom, OWLSubObjectPropertyOfAxiom):
        # Same reduction as EquivalentObjectProperties conclusions: assert
        # sub(a,b) on fresh individuals and deny sup(a,b) by refutation.
        return _entails_subproperty(
            premise_axioms, axiom.get_sub_property(), axiom.get_super_property(), udl
        )
    if isinstance(axiom, OWLSubDataPropertyOfAxiom):
        sub = _role_name(axiom.get_sub_property())
        sup = _role_name(axiom.get_super_property())
        if sub is None or sup is None:
            raise UnsupportedConclusion(f"complex data property in {axiom!r}")
        reasoner = _build_reasoner(premise_axioms, udl)
        try:
            return reasoner.is_sub_role_of(AtomicRole.create(sub), AtomicRole.create(sup))
        finally:
            reasoner.dispose()
    if isinstance(axiom, OWLObjectPropertyAssertionAxiom):
        # Mirrors EntailmentChecker.visit(ObjectPropertyAssertion): entailed
        # iff denying the edge refutes the premise. The denial is expressed
        # as ∀p.¬marker, so non-simple p is unfolded through its automaton
        # (chains/transitivity never materialize edges in a single model).
        return _refutes(
            premise_axioms,
            _denied_edge(
                axiom.get_subject(), axiom.get_property(), axiom.get_object()
            ),
            udl,
        )
    if isinstance(axiom, OWLSameIndividualAxiom):
        inds = list(axiom.individuals())
        reasoner = _build_reasoner(premise_axioms, udl)
        try:
            if not reasoner.is_consistent():
                return True
            for i in range(len(inds) - 1):
                a = _individual_internal(inds[i])
                b = _individual_internal(inds[i + 1])
                if a is None or b is None or not reasoner.is_same_individual(a, b):
                    return False
            return True
        finally:
            reasoner.dispose()
    if isinstance(axiom, OWLDifferentIndividualsAxiom):
        from hermit.owl_model.owl_axiom import OWLSameIndividualAxiom as _Same
        inds = list(axiom.individuals())
        # Different(a, b) holds iff asserting SameIndividual(a, b) makes the
        # premise inconsistent (mirrors EntailmentChecker via the reasoner).
        for i in range(len(inds) - 1):
            for j in range(i + 1, len(inds)):
                same = _Same([inds[i], inds[j]])
                reasoner = _build_reasoner(premise_axioms + [same], udl)
                try:
                    if reasoner.is_consistent():
                        return False
                finally:
                    reasoner.dispose()
        return True
    if isinstance(axiom, OWLDataPropertyAssertionAxiom):
        # No direct data-fact entailment query; reduce to consistency of the
        # premise plus the negation is not expressible without nominals/values.
        # Mirror EntailmentChecker: a data property assertion is entailed iff
        # adding its negative form makes the ontology inconsistent.
        from hermit.owl_model.owl_axiom import (
            OWLNegativeDataPropertyAssertionAxiom,
        )
        neg = OWLNegativeDataPropertyAssertionAxiom(
            axiom.get_subject(), axiom.get_property(), axiom.get_object()
        )
        reasoner = _build_reasoner(premise_axioms + [neg], udl)
        try:
            return not reasoner.is_consistent()
        finally:
            reasoner.dispose()
    if isinstance(axiom, OWLSymmetricObjectPropertyAxiom):
        # SymmetricObjectProperty(p) == SubObjectPropertyOf(p ObjectInverseOf(p)):
        # assert p(a,b) and deny p(b,a) on fresh individuals.
        p = axiom.get_property()
        a, b = _fresh_individuals(2)
        return _refutes(
            premise_axioms,
            [OWLObjectPropertyAssertionAxiom(a, p, b), *_denied_edge(b, p, a)],
            udl,
        )
    if isinstance(axiom, OWLTransitiveObjectPropertyAxiom):
        # assert p(a,b), p(b,c) and deny p(a,c) on fresh individuals.
        p = axiom.get_property()
        a, b, c = _fresh_individuals(3)
        return _refutes(
            premise_axioms,
            [
                OWLObjectPropertyAssertionAxiom(a, p, b),
                OWLObjectPropertyAssertionAxiom(b, p, c),
                *_denied_edge(a, p, c),
            ],
            udl,
        )
    if isinstance(axiom, OWLEquivalentObjectPropertiesAxiom):
        # mutual sub-property checks along the chain (covers all pairs by
        # transitivity of entailed sub-property inclusions)
        props = list(axiom.properties())
        first = props[0]
        for nxt in props[1:]:
            if not _entails_subproperty(premise_axioms, first, nxt, udl):
                return False
            if not _entails_subproperty(premise_axioms, nxt, first, udl):
                return False
        return True
    if isinstance(axiom, OWLObjectPropertyRangeAxiom):
        # assert p(a,b) and put b under a fresh class disjoint from C.
        p = axiom.get_property()
        a, b = _fresh_individuals(2)
        q = OWLClass(_AUX + "NotRange")
        return _refutes(
            premise_axioms,
            [
                OWLObjectPropertyAssertionAxiom(a, p, b),
                OWLSubClassOfAxiom(q, OWLObjectComplementOf(axiom.get_range())),
                OWLClassAssertionAxiom(b, q),
            ],
            udl,
        )
    if isinstance(axiom, OWLDataPropertyRangeAxiom):
        # entailed iff some individual may carry a p-value outside the range:
        # assert ∃p.(¬DR) on a fresh individual and check for refutation.
        from hermit.owl_model.owl_data_ranges import OWLDataComplementOf
        p = axiom.get_property()
        (a,) = _fresh_individuals(1)
        witness = OWLDataSomeValuesFrom(p, OWLDataComplementOf(axiom.get_range()))
        return _refutes(
            premise_axioms,
            [OWLClassAssertionAxiom(a, witness)],
            udl,
        )
    if isinstance(axiom, OWLObjectPropertyDomainAxiom):
        # assert p(a,b) and put a under a fresh class disjoint from C.
        p = axiom.get_property()
        a, b = _fresh_individuals(2)
        q = OWLClass(_AUX + "NotDomain")
        return _refutes(
            premise_axioms,
            [
                OWLObjectPropertyAssertionAxiom(a, p, b),
                OWLSubClassOfAxiom(q, OWLObjectComplementOf(axiom.get_domain())),
                OWLClassAssertionAxiom(a, q),
            ],
            udl,
        )
    raise UnsupportedConclusion(f"{type(axiom).__name__}")


def _role_name(prop) -> str | None:
    iri = getattr(prop, "iri", None)
    if iri is None:
        return None
    return iri.as_str() if hasattr(iri, "as_str") else str(iri)


def run_entailment(subtest: Subtest) -> Outcome:
    res = subtest.descriptor.conclusion_string(subtest.positive)
    if res is None:
        raise UnsupportedConclusion("no conclusion ontology in a parsable format")
    fmt, text = res
    conclusion_axioms = _load_axioms(text, fmt)

    pres = subtest.descriptor.premise_string()
    premise_axioms = _load_axioms(pres[1], pres[0]) if pres is not None else []

    logical = [
        a
        for a in conclusion_axioms
        if a.__class__.__name__ not in ("OWLDeclarationAxiom",)
        and "Annotation" not in a.__class__.__name__
    ]

    all_entailed = True
    for ax in logical:
        if not _entails_axiom(premise_axioms, ax, subtest.use_disjunction_learning):
            all_entailed = False
            break

    expected = subtest.positive  # positive entailment => should be entailed
    return Outcome(
        all_entailed == expected, f"entailed={all_entailed} expected={expected}"
    )


def run_subtest(subtest: Subtest) -> Outcome:
    if subtest.test_type in (TestType.CONSISTENCY, TestType.INCONSISTENCY):
        return run_consistency(subtest)
    return run_entailment(subtest)
