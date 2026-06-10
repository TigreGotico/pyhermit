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

from .registry import IMPORT_MAP, Subtest, TestType, format_extension

_AUX = "http://pyhermit.invalid/wg/aux#"
_OWL = "http://www.w3.org/2002/07/owl#"


class UnsupportedConclusion(Exception):
    """Raised when a conclusion axiom form is not yet faithfully checkable."""


@dataclass
class Outcome:
    passed: bool
    detail: str


def _parse_document(text: str, fmt: str) -> list:
    ext = format_extension(fmt)
    fd, path = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        return load_ontology(path)
    finally:
        os.unlink(path)


def _import_iris(text: str, fmt: str) -> list[str]:
    """owl:imports targets of an ontology document (any of the WG formats)."""
    if fmt == "RDFXML":
        from hermit.rdfxml import parse_rdfxml
        try:
            triples = parse_rdfxml(text)
        except Exception:  # noqa: BLE001
            return []
        return [
            o for _s, p, o in triples if p == _OWL + "imports" and isinstance(o, str)
        ]
    if fmt == "FUNCTIONAL":
        import re
        return re.findall(r"Import\(\s*<([^>]+)>\s*\)", text)
    if fmt == "OWLXML":
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            return []
        return [
            (el.text or "").strip()
            for el in root.iter()
            if el.tag.rsplit("}", 1)[-1] == "Import"
        ]
    return []


def _load_axioms(text: str, fmt: str) -> list:
    """Parse an embedded ontology string and resolve its imports closure.

    Mirrors the Java harness, where AbstractTest.registerImportedReosurces()
    maps the import IRIs the WG suite uses onto the local copies shipped with
    the test data and the OWL API loads the closure.
    """
    axioms = _parse_document(text, fmt)
    pending = _import_iris(text, fmt)
    seen: set[str] = set()
    while pending:
        iri = pending.pop()
        if iri in seen:
            continue
        seen.add(iri)
        path = IMPORT_MAP.get(iri)
        if path is None or not path.exists():
            continue
        imported_text = path.read_text(encoding="utf-8")
        axioms.extend(_parse_document(imported_text, "RDFXML"))
        pending.extend(_import_iris(imported_text, "RDFXML"))
    return axioms


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
        # Mirrors EntailmentChecker.visit(DataPropertyAssertion):
        # hasType(subject, DataHasValue(p, lit)), realized by refutation --
        # the premise plus ``subject : forall p.not({lit})`` has no model iff
        # every model gives subject the p-value lit.
        from hermit.owl_model.class_expression.restriction import (
            OWLDataAllValuesFrom,
            OWLDataOneOf,
        )
        from hermit.owl_model.owl_data_ranges import OWLDataComplementOf
        denial = OWLClassAssertionAxiom(
            axiom.get_subject(),
            OWLDataAllValuesFrom(
                axiom.get_property(),
                OWLDataComplementOf(OWLDataOneOf([axiom.get_object()])),
            ),
        )
        return _refutes(premise_axioms, [denial], udl)
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


# ---------------------------------------------------------------------------
# Anonymous individuals in conclusion ABoxes (rolling-up)
# ---------------------------------------------------------------------------
#
# Mirrors EntailmentChecker$AnonymousIndividualForestBuilder: a blank node in
# a conclusion is an existential variable (OWL 2 Structural Specification,
# Sec. 11.2), so the assertions touching anonymous individuals are arranged
# into a forest and rolled up into class expressions. A tree hanging off a
# named individual ``a`` by an edge ``p`` becomes ``a : exists p.C``; a tree
# with no named neighbour becomes ``SubClassOf(owl:Thing, not C)``, entailed
# iff adding it to the premise is inconsistent.

def _ind_iri(individual) -> str | None:  # type: ignore[no-untyped-def]
    iri = getattr(individual, "iri", None)
    if iri is None:
        return None
    return iri.as_str() if hasattr(iri, "as_str") else str(iri)


def _is_anon_individual(individual) -> bool:  # type: ignore[no-untyped-def]
    from hermit.owl_rdf import ANONYMOUS_INDIVIDUAL_PREFIX
    s = _ind_iri(individual)
    return s is not None and s.startswith(ANONYMOUS_INDIVIDUAL_PREFIX)


def _axiom_individuals(axiom) -> list:  # type: ignore[no-untyped-def]
    """Individuals named directly by an ABox conclusion axiom."""
    if isinstance(axiom, OWLClassAssertionAxiom):
        return [axiom.get_individual()]
    if isinstance(axiom, OWLObjectPropertyAssertionAxiom):
        return [axiom.get_subject(), axiom.get_object()]
    if isinstance(axiom, OWLDataPropertyAssertionAxiom):
        return [axiom.get_subject()]
    if isinstance(axiom, (OWLSameIndividualAxiom, OWLDifferentIndividualsAxiom)):
        return list(axiom.individuals())
    return []


def _ope_key(ope) -> tuple[str, bool]:  # type: ignore[no-untyped-def]
    from hermit.owl_model.owl_property import OWLObjectInverseOf
    if isinstance(ope, OWLObjectInverseOf):
        inner = ope.get_inverse()
        return (_role_name(inner) or "", True)
    return (_role_name(ope) or "", False)


def _inverse_ope(ope):  # type: ignore[no-untyped-def]
    from hermit.owl_model.owl_property import OWLObjectInverseOf
    if isinstance(ope, OWLObjectInverseOf):
        return ope.get_inverse()
    return ope.get_inverse_property()


def _is_owl_thing(expr) -> bool:  # type: ignore[no-untyped-def]
    return isinstance(expr, OWLClass) and _name(expr) == _OWL + "Thing"


def _roll_up_anonymous(axioms: list) -> tuple[list, list]:
    """Build the anonymous-individual forest and roll it up.

    Returns ``(assertions, no_named_axioms)``: class assertions on named
    individuals that must be entailed, and SubClassOf axioms whose addition
    to the premise must be inconsistent for the entailment to hold.
    """
    from hermit.owl_model.class_expression import (
        OWLObjectIntersectionOf,
        OWLObjectSomeValuesFrom,
        OWLThing,
    )
    from hermit.owl_model.class_expression.restriction import OWLDataHasValue

    nodes: set[str] = set()
    edges: dict[str, set[str]] = {}
    # anon node -> named individual iri -> object property expressions
    # pointing from the anonymous node to the named individual
    special: dict[str, dict[str, list]] = {}
    labels: dict[str, list] = {}
    edge_labels: dict[tuple[str, str], object] = {}
    named_objs: dict[str, object] = {}

    for axiom in axioms:
        if isinstance(axiom, OWLClassAssertionAxiom):
            expr = axiom.get_class_expression()
            if _is_owl_thing(expr):
                continue
            ind = axiom.get_individual()
            key = _ind_iri(ind)
            if key is None or not _is_anon_individual(ind):
                continue
            nodes.add(key)
            labels.setdefault(key, []).append(expr)
        elif isinstance(axiom, OWLObjectPropertyAssertionAxiom):
            sub, obj = axiom.get_subject(), axiom.get_object()
            ope = axiom.get_property()
            sub_anon, obj_anon = _is_anon_individual(sub), _is_anon_individual(obj)
            if not sub_anon and not obj_anon:
                continue
            if sub_anon != obj_anon:
                if not sub_anon:
                    sub, obj = obj, sub
                    ope = _inverse_ope(ope)
                anon_key, named_key = _ind_iri(sub), _ind_iri(obj)
                assert anon_key is not None and named_key is not None
                nodes.add(anon_key)
                named_objs[named_key] = obj
                special.setdefault(anon_key, {}).setdefault(named_key, []).append(
                    ope
                )
            else:
                from hermit.owl_model.owl_property import OWLObjectInverseOf
                if isinstance(ope, OWLObjectInverseOf):
                    ope = ope.get_inverse()
                    sub, obj = obj, sub
                sub_key, obj_key = _ind_iri(sub), _ind_iri(obj)
                assert sub_key is not None and obj_key is not None
                nodes.add(sub_key)
                nodes.add(obj_key)
                if obj_key in edges.get(sub_key, set()) or sub_key in edges.get(
                    obj_key, set()
                ):
                    raise UnsupportedConclusion(
                        "two object property assertions between the same "
                        "anonymous individuals (OWL 2 Syntax Sec 11.2)"
                    )
                edges.setdefault(sub_key, set()).add(obj_key)
                edges.setdefault(obj_key, set()).add(sub_key)
                edge_labels[(sub_key, obj_key)] = ope
        elif isinstance(axiom, OWLDataPropertyAssertionAxiom):
            sub = axiom.get_subject()
            key = _ind_iri(sub)
            if key is None or not _is_anon_individual(sub):
                continue
            nodes.add(key)
            labels.setdefault(key, []).append(
                OWLDataHasValue(axiom.get_property(), axiom.get_object())
            )

    def class_expr_for(node: str, predecessor: str | None):  # type: ignore[no-untyped-def]
        own = labels.get(node, [])
        children = [s for s in edges.get(node, set()) if s != predecessor]
        concepts = list(own)
        for child in sorted(children):
            ope = edge_labels.get((node, child))
            if ope is None:
                inv = edge_labels.get((child, node))
                if inv is None:
                    raise UnsupportedConclusion(
                        "anonymous individual forest edge without a label"
                    )
                ope = _inverse_ope(inv)
            concepts.append(
                OWLObjectSomeValuesFrom(ope, class_expr_for(child, node))
            )
        if not concepts:
            return OWLThing
        if len(concepts) == 1:
            return concepts[0]
        return OWLObjectIntersectionOf(concepts)

    # Components of the (undirected) anonymous forest, with cycle detection.
    components: list[set[str]] = []
    unvisited = set(nodes)
    while unvisited:
        start = next(iter(unvisited))
        component: set[str] = set()
        queue: list[tuple[str, str | None]] = [(start, None)]
        while queue:
            current, pred = queue.pop(0)
            if current in component:
                raise UnsupportedConclusion(
                    "anonymous individuals form a cycle, not a forest "
                    "(OWL 2 Syntax Sec 11.2)"
                )
            component.add(current)
            for nxt in edges.get(current, set()):
                if nxt != pred:
                    queue.append((nxt, current))
        components.append(component)
        unvisited -= component

    assertions: list = []
    no_named: list = []
    for component in components:
        root = None
        root_with_one_named = None
        for ind in sorted(component):
            if ind in special:
                if len(special[ind]) < 2:
                    root_with_one_named = ind
            else:
                root = ind
        chosen = root_with_one_named if root_with_one_named is not None else root
        if chosen is None:
            raise UnsupportedConclusion(
                "no valid root in the anonymous individual forest "
                "(OWL 2 Syntax Sec 11.2)"
            )
        expr = class_expr_for(chosen, None)
        if chosen not in special:
            no_named.append(
                OWLSubClassOfAxiom(OWLThing, OWLObjectComplementOf(expr))
            )
        else:
            ind2op = special[chosen]
            (named_key, opes), = ind2op.items()
            if len({_ope_key(o) for o in opes}) != 1:
                raise UnsupportedConclusion(
                    "anonymous root with multiple relationships to a named "
                    "individual (OWL 2 Syntax Sec 11.2)"
                )
            op = _inverse_ope(opes[0])
            assertions.append(
                OWLClassAssertionAxiom(
                    named_objs[named_key], OWLObjectSomeValuesFrom(op, expr)
                )
            )
    return assertions, no_named


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

    # Conclusion axioms naming anonymous individuals are deferred and rolled
    # up into class expressions (EntailmentChecker.checkAnonymousIndividuals).
    regular: list = []
    anon_abox: list = []
    for a in logical:
        if any(_is_anon_individual(i) for i in _axiom_individuals(a)):
            if isinstance(
                a, (OWLSameIndividualAxiom, OWLDifferentIndividualsAxiom)
            ):
                raise UnsupportedConclusion(
                    "anonymous individuals in SameIndividual/"
                    "DifferentIndividuals (OWL 2 Syntax Sec 11.2)"
                )
            anon_abox.append(a)
        else:
            regular.append(a)

    udl = subtest.use_disjunction_learning
    all_entailed = True
    for ax in regular:
        if not _entails_axiom(premise_axioms, ax, udl):
            all_entailed = False
            break
    if all_entailed and anon_abox:
        assertions, no_named = _roll_up_anonymous(anon_abox)
        for ax in assertions:
            if not _entails_axiom(premise_axioms, ax, udl):
                all_entailed = False
                break
        if all_entailed:
            for sub_ax in no_named:
                if not _refutes(premise_axioms, [sub_ax], udl):
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
