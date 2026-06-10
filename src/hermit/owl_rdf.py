"""Map an RDF graph (list of triples) to OWL 2 logical axioms.

Implements the reverse of the OWL 2 Mapping to RDF Graphs
(https://www.w3.org/TR/owl2-mapping-to-rdf/) for the fragment HermiT reasons
over: class expressions, object/data property expressions, and the logical
axioms that :class:`hermit.structural.OWLNormalization` consumes.

The emitted objects are the same :mod:`hermit.owl_model` types the rest of the
pipeline already clausifies, so every produced class expression round-trips
through ``_owl_expr_to_internal`` and the clausifier visitor.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hermit.rdfxml import RDF, RDFS, BNode, Literal, Term, Triple

if TYPE_CHECKING:
    from hermit.owl_model.class_expression import OWLClassExpression
    from hermit.owl_model.owl_axiom import OWLAxiom
    from hermit.owl_model.owl_property import OWLObjectPropertyExpression

OWL = "http://www.w3.org/2002/07/owl#"
XSD = "http://www.w3.org/2001/XMLSchema#"

#: IRI prefix under which blank nodes are skolemized into named individuals.
#: Consumers (e.g. the entailment harness) detect anonymous individuals by it.
ANONYMOUS_INDIVIDUAL_PREFIX = "http://pyhermit.invalid/anon/"

RDF_TYPE = RDF + "type"
RDF_FIRST = RDF + "first"
RDF_REST = RDF + "rest"
RDF_NIL = RDF + "nil"


class _Graph:
    """Indexed view over a triple list for the RDF→OWL mapping."""

    def __init__(self, triples: list[Triple]) -> None:
        self.triples = triples
        self._spo: dict[Term, dict[str, list[Term]]] = {}
        for s, p, o in triples:
            self._spo.setdefault(s, {}).setdefault(p, []).append(o)

    def objects(self, subj: Term, pred: str) -> list[Term]:
        return self._spo.get(subj, {}).get(pred, [])

    def value(self, subj: Term, pred: str) -> Term | None:
        vals = self.objects(subj, pred)
        return vals[0] if vals else None

    def types(self, subj: Term) -> set[str]:
        return {o for o in self.objects(subj, RDF_TYPE) if isinstance(o, str)}

    def has(self, subj: Term, pred: str) -> bool:
        return bool(self.objects(subj, pred))

    def subjects(self, pred: str, obj: Term) -> list[Term]:
        out: list[Term] = []
        for s, p, o in self.triples:
            if p == pred and o == obj:
                out.append(s)
        return out

    def predicate_objects(self, subj: Term) -> list[tuple[str, Term]]:
        return [
            (pred, obj)
            for pred, objs in self._spo.get(subj, {}).items()
            for obj in objs
        ]


def map_triples_to_axioms(triples: list[Triple]) -> list[OWLAxiom]:
    """Convert RDF triples into OWL axioms."""
    return _Mapper(_Graph(triples)).run()


class _Mapper:
    def __init__(self, graph: _Graph) -> None:
        self.g = graph
        self.axioms: list[OWLAxiom] = []
        # IRIs declared as object vs data properties (best-effort typing).
        self._data_props: set[str] = set()
        self._object_props: set[str] = set()
        # Declared annotation properties: their assertions are non-logical
        # (the OWL API maps them to OWLAnnotationAssertionAxiom etc., which
        # carry no logical content for reasoning).
        self._annotation_props: set[str] = set()
        self._classify_properties()

    # ------------------------------------------------------------------
    # property typing
    # ------------------------------------------------------------------

    def _classify_properties(self) -> None:
        for s, p, o in self.g.triples:
            if p == RDF_TYPE and isinstance(o, str) and isinstance(s, str):
                if o in (OWL + "DatatypeProperty",):
                    self._data_props.add(s)
                elif o == OWL + "AnnotationProperty":
                    self._annotation_props.add(s)
                elif o in (
                    OWL + "ObjectProperty",
                    OWL + "TransitiveProperty",
                    OWL + "SymmetricProperty",
                    OWL + "AsymmetricProperty",
                    OWL + "ReflexiveProperty",
                    OWL + "IrreflexiveProperty",
                    OWL + "InverseFunctionalProperty",
                ):
                    self._object_props.add(s)

    def _is_data_prop(self, iri: Term) -> bool:
        if not isinstance(iri, str):
            return False
        if iri in (OWL + "topDataProperty", OWL + "bottomDataProperty"):
            return True
        return iri in self._data_props

    def _is_annotation_prop(self, iri: Term) -> bool:
        return isinstance(iri, str) and iri in self._annotation_props

    # ------------------------------------------------------------------
    # entry
    # ------------------------------------------------------------------

    def run(self) -> list[OWLAxiom]:
        for s, p, o in self.g.triples:
            self._dispatch(s, p, o)
        return self.axioms

    def _dispatch(self, s: Term, p: str, o: Term) -> None:  # noqa: C901
        from hermit.owl_model.owl_axiom import (
            OWLDisjointClassesAxiom,
            OWLEquivalentClassesAxiom,
            OWLInverseObjectPropertiesAxiom,
            OWLObjectPropertyDomainAxiom,
            OWLObjectPropertyRangeAxiom,
            OWLSubClassOfAxiom,
        )

        # Skip list-internal and parse-helper triples.
        if p in (RDF_FIRST, RDF_REST):
            return

        if p == RDFS + "subClassOf":
            sub = self._class_expr(s)
            sup = self._class_expr(o)
            if sub is not None and sup is not None:
                self._add(OWLSubClassOfAxiom(sub, sup))
            return

        if p == OWL + "equivalentClass":
            a = self._class_expr(s)
            b = self._class_expr(o)
            if a is not None and b is not None:
                self._add(OWLEquivalentClassesAxiom([a, b]))
            return

        if p == OWL + "disjointWith":
            a = self._class_expr(s)
            b = self._class_expr(o)
            if a is not None and b is not None:
                self._add(OWLDisjointClassesAxiom([a, b]))
            return

        if p in (
            OWL + "intersectionOf",
            OWL + "unionOf",
            OWL + "complementOf",
        ):
            # On a blank node these define an anonymous class expression that is
            # consumed when the node is referenced. On a named class they form a
            # class definition: C ≡ <expr>.
            if isinstance(s, str):
                expr = self._boolean_expr(p, o)
                if expr is not None:
                    from hermit.owl_model.class_expression import OWLClass
                    from hermit.owl_model.owl_axiom import (
                        OWLEquivalentClassesAxiom,
                    )
                    self._add(OWLEquivalentClassesAxiom([OWLClass(s), expr]))
            return
        if p == OWL + "oneOf":
            # A named-class enumeration C ≡ {a, ...}.
            if isinstance(s, str):
                expr = self._boolean_expr(p, o)
                if expr is not None:
                    from hermit.owl_model.class_expression import OWLClass
                    from hermit.owl_model.owl_axiom import (
                        OWLEquivalentClassesAxiom,
                    )
                    self._add(OWLEquivalentClassesAxiom([OWLClass(s), expr]))
            return

        if p == OWL + "propertyChainAxiom":
            from hermit.owl_model.owl_axiom import OWLSubPropertyChainAxiom
            chain_props = [
                self._object_prop_expr(m) for m in self._rdf_list(o)
            ]
            super_prop = self._object_prop_expr(s)
            if super_prop is not None and all(
                c is not None for c in chain_props
            ):
                self._add(
                    OWLSubPropertyChainAxiom(
                        [c for c in chain_props if c is not None], super_prop
                    )
                )
            return

        if p == OWL + "disjointUnionOf":
            from hermit.owl_model.class_expression import OWLObjectUnionOf
            from hermit.owl_model.owl_axiom import (
                OWLDisjointClassesAxiom,
                OWLEquivalentClassesAxiom,
            )
            cls = self._class_expr(s)
            members = self._class_list(o)
            if cls is not None and len(members) >= 2:
                self._add(OWLEquivalentClassesAxiom([cls, OWLObjectUnionOf(members)]))
                self._add(OWLDisjointClassesAxiom(members))
            return

        if p == OWL + "propertyDisjointWith" and isinstance(s, str) and isinstance(
            o, str
        ):
            from hermit.owl_model.owl_axiom import (
                OWLDisjointObjectPropertiesAxiom,
            )
            self._add(
                OWLDisjointObjectPropertiesAxiom(
                    [self._object_prop(s), self._object_prop(o)]
                )
            )
            return

        if p == OWL + "hasKey" and isinstance(s, str):
            self._has_key(s, o)
            return

        if p == RDFS + "subPropertyOf":
            self._sub_property(s, o)
            return

        if p == OWL + "equivalentProperty":
            self._equivalent_property(s, o)
            return

        if p == OWL + "inverseOf" and isinstance(s, str) and isinstance(o, str):
            self._add(
                OWLInverseObjectPropertiesAxiom(
                    self._object_prop(s), self._object_prop(o)
                )
            )
            return

        if p == RDFS + "domain" and isinstance(s, str):
            if self._is_annotation_prop(s):
                return  # AnnotationPropertyDomain is non-logical
            dom = self._class_expr(o)
            if dom is not None:
                if self._is_data_prop(s):
                    self._data_domain(s, dom)
                else:
                    self._add(OWLObjectPropertyDomainAxiom(self._object_prop(s), dom))
            return

        if p == RDFS + "range" and isinstance(s, str):
            if self._is_annotation_prop(s):
                return  # AnnotationPropertyRange is non-logical
            if self._is_data_prop(s):
                from hermit.owl_model.owl_axiom import OWLDataPropertyRangeAxiom
                dr = self._data_range(o)
                if dr is not None:
                    self._add(
                        OWLDataPropertyRangeAxiom(self._data_prop(s), dr)
                    )
                return
            rng = self._class_expr(o)
            if rng is not None:
                self._add(OWLObjectPropertyRangeAxiom(self._object_prop(s), rng))
            return

        if p == OWL + "sameAs" and isinstance(s, str) and isinstance(o, str):
            from hermit.owl_model.owl_axiom import OWLSameIndividualAxiom
            from hermit.owl_model.owl_individual import OWLNamedIndividual
            self._add(
                OWLSameIndividualAxiom(
                    [OWLNamedIndividual(s), OWLNamedIndividual(o)]
                )
            )
            return

        if p == OWL + "differentFrom" and isinstance(s, str) and isinstance(o, str):
            from hermit.owl_model.owl_axiom import OWLDifferentIndividualsAxiom
            from hermit.owl_model.owl_individual import OWLNamedIndividual
            self._add(
                OWLDifferentIndividualsAxiom(
                    [OWLNamedIndividual(s), OWLNamedIndividual(o)]
                )
            )
            return

        if p == RDF_TYPE and isinstance(o, str):
            self._handle_type(s, o)
            return

        if p == RDF_TYPE and isinstance(o, BNode):
            # ClassAssertion with an anonymous class expression.
            from hermit.owl_model.owl_axiom import OWLClassAssertionAxiom
            if self._is_class_structure(s):
                return
            ce = self._class_expr(o)
            if ce is not None:
                ind = self._individual(s)
                if ind is not None:
                    self._add(OWLClassAssertionAxiom(ind, ce))
            return

        # Property assertions: subject p object where p is a user property.
        if isinstance(p, str) and not p.startswith((RDF, RDFS, OWL, XSD)):
            self._assertion(s, p, o)
            return

    # ------------------------------------------------------------------
    # rdf:type
    # ------------------------------------------------------------------

    def _handle_type(self, s: Term, o: str) -> None:  # noqa: C901
        from hermit.owl_model.owl_axiom import (
            OWLAsymmetricObjectPropertyAxiom,
            OWLClassAssertionAxiom,
            OWLFunctionalDataPropertyAxiom,
            OWLFunctionalObjectPropertyAxiom,
            OWLInverseFunctionalObjectPropertyAxiom,
            OWLIrreflexiveObjectPropertyAxiom,
            OWLReflexiveObjectPropertyAxiom,
            OWLSymmetricObjectPropertyAxiom,
            OWLTransitiveObjectPropertyAxiom,
        )

        if o == OWL + "TransitiveProperty":
            self._add(OWLTransitiveObjectPropertyAxiom(self._object_prop(s)))
            return
        if o == OWL + "SymmetricProperty":
            self._add(OWLSymmetricObjectPropertyAxiom(self._object_prop(s)))
            return
        if o == OWL + "AsymmetricProperty":
            self._add(OWLAsymmetricObjectPropertyAxiom(self._object_prop(s)))
            return
        if o == OWL + "ReflexiveProperty":
            self._add(OWLReflexiveObjectPropertyAxiom(self._object_prop(s)))
            return
        if o == OWL + "IrreflexiveProperty":
            self._add(OWLIrreflexiveObjectPropertyAxiom(self._object_prop(s)))
            return
        if o == OWL + "FunctionalProperty":
            if self._is_data_prop(s):
                self._add(OWLFunctionalDataPropertyAxiom(self._data_prop(s)))
            else:
                self._add(OWLFunctionalObjectPropertyAxiom(self._object_prop(s)))
            return
        if o == OWL + "InverseFunctionalProperty":
            self._add(
                OWLInverseFunctionalObjectPropertyAxiom(self._object_prop(s))
            )
            return

        if o == OWL + "NegativePropertyAssertion":
            self._negative_property_assertion(s)
            return

        if o == OWL + "AllDifferent":
            from hermit.owl_model.owl_axiom import OWLDifferentIndividualsAxiom
            members = self._rdf_list_or_value(s, OWL + "distinctMembers") or \
                self._rdf_list_or_value(s, OWL + "members")
            inds = [
                i for i in (self._individual(m) for m in members)
                if i is not None
            ]
            if len(inds) >= 2:
                self._add(OWLDifferentIndividualsAxiom(inds))
            return
        if o == OWL + "AllDisjointClasses":
            from hermit.owl_model.owl_axiom import OWLDisjointClassesAxiom
            members = self._rdf_list_or_value(s, OWL + "members")
            classes = [
                c for c in (self._class_expr(m) for m in members)
                if c is not None
            ]
            if len(classes) >= 2:
                self._add(OWLDisjointClassesAxiom(classes))
            return
        if o == OWL + "AllDisjointProperties":
            from hermit.owl_model.owl_axiom import (
                OWLDisjointObjectPropertiesAxiom,
            )
            members = self._rdf_list_or_value(s, OWL + "members")
            props = [
                pp for pp in (self._object_prop_expr(m) for m in members)
                if pp is not None
            ]
            if len(props) >= 2:
                self._add(OWLDisjointObjectPropertiesAxiom(props))
            return

        # Built-in / structural types are not class assertions.
        if o in _STRUCTURAL_TYPES or o.startswith((RDF, RDFS)):
            return
        if o in (
            OWL + "Class",
            OWL + "ObjectProperty",
            OWL + "DatatypeProperty",
            OWL + "AnnotationProperty",
            OWL + "Ontology",
            OWL + "NamedIndividual",
            OWL + "Thing",
        ):
            return

        # ClassAssertion: the object is a class (named or anonymous) and s is an
        # individual. A blank-node subject that is itself a class expression or
        # structural node (restriction, boolean combinator, list cell) is not an
        # individual and must not yield a class assertion.
        if self._is_class_structure(s):
            return
        ce = self._class_expr(o)
        if ce is not None:
            ind = self._individual(s)
            if ind is not None:
                self._add(OWLClassAssertionAxiom(ind, ce))

    def _is_class_structure(self, s: Term) -> bool:
        if not isinstance(s, BNode):
            return False
        for pred in (
            OWL + "intersectionOf",
            OWL + "unionOf",
            OWL + "complementOf",
            OWL + "oneOf",
            OWL + "onProperty",
            OWL + "onClass",
            OWL + "onDataRange",
            OWL + "someValuesFrom",
            OWL + "allValuesFrom",
            OWL + "hasValue",
            OWL + "hasSelf",
            OWL + "inverseOf",
            RDF_FIRST,
            RDF_REST,
        ):
            if self.g.has(s, pred):
                return True
        t = self.g.types(s)
        return bool(t & {OWL + "Restriction", OWL + "Class", RDF + "List"})

    # ------------------------------------------------------------------
    # property axioms
    # ------------------------------------------------------------------

    def _sub_property(self, s: Term, o: Term) -> None:
        from hermit.owl_model.owl_axiom import (
            OWLSubDataPropertyOfAxiom,
            OWLSubObjectPropertyOfAxiom,
            OWLSubPropertyChainAxiom,
        )

        if self._is_annotation_prop(s) or self._is_annotation_prop(o):
            return  # SubAnnotationPropertyOf is non-logical

        # Property chain axiom: subject is a bnode with owl:propertyChain /
        # rdf:List, super-property is o.
        chain = self.g.value(s, OWL + "propertyChain")
        if chain is None and isinstance(s, BNode):
            chain = s if self.g.has(s, RDF_FIRST) else None
        if isinstance(s, str) and isinstance(o, str):
            if self._is_data_prop(s) or self._is_data_prop(o):
                self._add(
                    OWLSubDataPropertyOfAxiom(
                        self._data_prop(s), self._data_prop(o)
                    )
                )
            else:
                self._add(
                    OWLSubObjectPropertyOfAxiom(
                        self._object_prop(s), self._object_prop(o)
                    )
                )
            return
        # s is a property expression (e.g. inverse) or chain.
        sup = self._object_prop_expr(o)
        if sup is None:
            return
        if isinstance(s, BNode) and self.g.has(s, RDF_FIRST):
            members = self._rdf_list(s)
            props = [self._object_prop_expr(m) for m in members]
            if all(pp is not None for pp in props):
                self._add(OWLSubPropertyChainAxiom([pp for pp in props if pp], sup))
            return
        sub = self._object_prop_expr(s)
        if sub is not None:
            self._add(OWLSubObjectPropertyOfAxiom(sub, sup))

    def _equivalent_property(self, s: Term, o: Term) -> None:
        from hermit.owl_model.owl_axiom import (
            OWLEquivalentDataPropertiesAxiom,
            OWLEquivalentObjectPropertiesAxiom,
        )

        if self._is_annotation_prop(s) or self._is_annotation_prop(o):
            return
        if isinstance(s, str) and isinstance(o, str):
            if self._is_data_prop(s) or self._is_data_prop(o):
                self._add(
                    OWLEquivalentDataPropertiesAxiom(
                        [self._data_prop(s), self._data_prop(o)]
                    )
                )
            else:
                self._add(
                    OWLEquivalentObjectPropertiesAxiom(
                        [self._object_prop(s), self._object_prop(o)]
                    )
                )

    def _has_key(self, s: str, o: Term) -> None:
        from hermit.owl_model.owl_axiom import OWLHasKeyAxiom
        cls = self._class_expr(s)
        if cls is None:
            return
        props = []
        for m in self._rdf_list(o):
            if isinstance(m, str):
                if self._is_data_prop(m):
                    props.append(self._data_prop(m))
                else:
                    props.append(self._object_prop(m))
        if props:
            self._add(OWLHasKeyAxiom(cls, props))

    def _rdf_list_or_value(self, subj: Term, pred: str) -> list[Term]:
        v = self.g.value(subj, pred)
        if v is None:
            return []
        return self._rdf_list(v)

    def _data_domain(self, s: str, dom: OWLClassExpression) -> None:
        from hermit.owl_model.owl_axiom import OWLDataPropertyDomainAxiom
        self._add(OWLDataPropertyDomainAxiom(self._data_prop(s), dom))

    def _assertion(self, s: Term, p: str, o: Term) -> None:
        from hermit.owl_model.owl_axiom import (
            OWLDataPropertyAssertionAxiom,
            OWLObjectPropertyAssertionAxiom,
        )

        if self._is_annotation_prop(p):
            return  # AnnotationAssertion is non-logical
        subj = self._individual(s)
        if subj is None:
            return
        if isinstance(o, Literal) or self._is_data_prop(p):
            if isinstance(o, Literal):
                self._add(
                    OWLDataPropertyAssertionAxiom(
                        subj, self._data_prop(p), self._literal(o)
                    )
                )
            return
        obj = self._individual(o)
        if obj is not None:
            self._add(
                OWLObjectPropertyAssertionAxiom(
                    subj, self._object_prop(p), obj
                )
            )

    def _negative_property_assertion(self, s: Term) -> None:
        """Map an owl:NegativePropertyAssertion reification node."""
        from hermit.owl_model.owl_axiom import (
            OWLNegativeDataPropertyAssertionAxiom,
            OWLNegativeObjectPropertyAssertionAxiom,
        )

        source = self.g.value(s, OWL + "sourceIndividual")
        prop = self.g.value(s, OWL + "assertionProperty")
        if source is None or prop is None:
            return
        subj = self._individual(source)
        if subj is None:
            return
        target_value = self.g.value(s, OWL + "targetValue")
        if isinstance(target_value, Literal):
            self._add(
                OWLNegativeDataPropertyAssertionAxiom(
                    subj, self._data_prop(prop), self._literal(target_value)
                )
            )
            return
        target = self.g.value(s, OWL + "targetIndividual")
        if target is None:
            return
        obj = self._individual(target)
        if obj is not None:
            self._add(
                OWLNegativeObjectPropertyAssertionAxiom(
                    subj, self._object_prop(prop), obj
                )
            )

    # ------------------------------------------------------------------
    # class expressions
    # ------------------------------------------------------------------

    def _class_expr(self, term: Term) -> OWLClassExpression | None:  # noqa: C901
        from hermit.owl_model.class_expression import (
            OWLClass,
        )

        if isinstance(term, str):
            return OWLClass(term)
        if isinstance(term, Literal):
            return None

        # Blank node: boolean combinator, restriction, or enumeration.
        for pred in (
            OWL + "intersectionOf",
            OWL + "unionOf",
            OWL + "complementOf",
            OWL + "oneOf",
        ):
            val = self.g.value(term, pred)
            if val is not None:
                return self._boolean_expr(pred, val)

        # Restriction.
        if OWL + "Restriction" in self.g.types(term) or self.g.has(
            term, OWL + "onProperty"
        ):
            return self._restriction(term)

        # A bnode declared as owl:Class with no structure: anonymous class —
        # treat as a fresh atomic class keyed by the bnode id.
        if OWL + "Class" in self.g.types(term):
            return OWLClass(_anon_iri(term))
        return None

    def _boolean_expr(self, pred: str, val: Term) -> OWLClassExpression | None:
        from hermit.owl_model.class_expression import (
            OWLObjectComplementOf,
            OWLObjectIntersectionOf,
            OWLObjectOneOf,
            OWLObjectUnionOf,
        )

        if pred == OWL + "intersectionOf":
            ops = self._class_list(val)
            if len(ops) >= 2:
                return OWLObjectIntersectionOf(ops)
            return ops[0] if ops else None
        if pred == OWL + "unionOf":
            ops = self._class_list(val)
            if len(ops) >= 2:
                return OWLObjectUnionOf(ops)
            return ops[0] if ops else None
        if pred == OWL + "complementOf":
            inner = self._class_expr(val)
            return OWLObjectComplementOf(inner) if inner is not None else None
        if pred == OWL + "oneOf":
            inds = [self._individual(m) for m in self._rdf_list(val)]
            inds = [i for i in inds if i is not None]
            return OWLObjectOneOf(inds) if inds else None
        return None

    def _restriction(self, term: Term) -> OWLClassExpression | None:  # noqa: C901
        from hermit.owl_model.class_expression import (
            OWLObjectAllValuesFrom,
            OWLObjectHasValue,
            OWLObjectSomeValuesFrom,
        )

        prop = self.g.value(term, OWL + "onProperty")
        if prop is None:
            return None

        if self._is_data_prop(prop) or self.g.has(term, OWL + "onDataRange"):
            return self._data_restriction(term, prop)

        some = self.g.value(term, OWL + "someValuesFrom")
        if some is not None:
            filler = self._class_expr(some)
            pe = self._object_prop_expr(prop)
            if filler is not None and pe is not None:
                return OWLObjectSomeValuesFrom(pe, filler)
            return None

        allv = self.g.value(term, OWL + "allValuesFrom")
        if allv is not None:
            filler = self._class_expr(allv)
            pe = self._object_prop_expr(prop)
            if filler is not None and pe is not None:
                return OWLObjectAllValuesFrom(pe, filler)
            return None

        hasv = self.g.value(term, OWL + "hasValue")
        if hasv is not None:
            if isinstance(hasv, Literal):
                return None  # data hasValue not reasoned over
            pe = self._object_prop_expr(prop)
            ind = self._individual(hasv)
            if pe is not None and ind is not None:
                return OWLObjectHasValue(pe, ind)
            return None

        hasself = self.g.value(term, OWL + "hasSelf")
        if hasself is not None:
            from hermit.owl_model.class_expression import OWLObjectHasSelf
            pe = self._object_prop_expr(prop)
            if pe is not None:
                return OWLObjectHasSelf(pe)
            return None

        return self._cardinality(term, prop)

    def _data_restriction(self, term: Term, prop: Term) -> OWLClassExpression | None:
        """Map a restriction on a data property to an OWL data restriction."""
        from hermit.owl_model.class_expression.restriction import (
            OWLDataAllValuesFrom,
            OWLDataExactCardinality,
            OWLDataHasValue,
            OWLDataMaxCardinality,
            OWLDataMinCardinality,
            OWLDataSomeValuesFrom,
        )
        from hermit.owl_model.owl_data_ranges import OWLDataRange
        from hermit.owl_model.owl_literal import TopOWLDatatype

        pe = self._data_prop(prop)

        some = self.g.value(term, OWL + "someValuesFrom")
        if some is not None:
            dr = self._data_range(some)
            return OWLDataSomeValuesFrom(pe, dr) if dr is not None else None

        allv = self.g.value(term, OWL + "allValuesFrom")
        if allv is not None:
            dr = self._data_range(allv)
            return OWLDataAllValuesFrom(pe, dr) if dr is not None else None

        hasv = self.g.value(term, OWL + "hasValue")
        if hasv is not None:
            if isinstance(hasv, Literal):
                return OWLDataHasValue(pe, self._literal(hasv))
            return None

        for pred, ctor, qual in (
            (OWL + "minCardinality", OWLDataMinCardinality, None),
            (
                OWL + "minQualifiedCardinality",
                OWLDataMinCardinality,
                OWL + "onDataRange",
            ),
            (OWL + "maxCardinality", OWLDataMaxCardinality, None),
            (
                OWL + "maxQualifiedCardinality",
                OWLDataMaxCardinality,
                OWL + "onDataRange",
            ),
            (OWL + "cardinality", OWLDataExactCardinality, None),
            (
                OWL + "qualifiedCardinality",
                OWLDataExactCardinality,
                OWL + "onDataRange",
            ),
        ):
            val = self.g.value(term, pred)
            if val is None:
                continue
            n = _int_literal(val)
            if n is None:
                return None
            filler: OWLDataRange = TopOWLDatatype
            if qual is not None:
                qv = self.g.value(term, qual)
                if qv is not None:
                    qdr = self._data_range(qv)
                    if qdr is None:
                        return None
                    filler = qdr
            return ctor(n, pe, filler)
        return None

    def _data_range(self, term: Term):  # type: ignore[no-untyped-def]
        """Map an RDF term to an OWL data range.

        Supports named datatypes, literal enumerations (owl:oneOf), facet
        restrictions (owl:onDatatype + owl:withRestrictions), complements
        (owl:datatypeComplementOf), and intersections/unions of data ranges.
        """
        from hermit.owl_model.class_expression.restriction import (
            OWLDataOneOf,
            OWLDatatypeRestriction,
        )
        from hermit.owl_model.owl_data_ranges import (
            OWLDataComplementOf,
            OWLDataIntersectionOf,
            OWLDataUnionOf,
        )
        from hermit.owl_model.owl_datatype import OWLDatatype

        if isinstance(term, str):
            return OWLDatatype(term)
        if isinstance(term, BNode):
            one_of = self.g.value(term, OWL + "oneOf")
            if one_of is not None:
                literals = [
                    self._literal(m)
                    for m in self._rdf_list(one_of)
                    if isinstance(m, Literal)
                ]
                if literals:
                    return OWLDataOneOf(literals)
            on_datatype = self.g.value(term, OWL + "onDatatype")
            if isinstance(on_datatype, str):
                with_restrictions = self.g.value(term, OWL + "withRestrictions")
                if with_restrictions is None:
                    return OWLDatatype(on_datatype)
                facets = self._facet_restrictions(with_restrictions)
                if facets is None:
                    return None
                return OWLDatatypeRestriction(OWLDatatype(on_datatype), facets)
            complement = self.g.value(term, OWL + "datatypeComplementOf")
            if complement is not None:
                inner = self._data_range(complement)
                return OWLDataComplementOf(inner) if inner is not None else None
            for pred, ctor in (
                (OWL + "intersectionOf", OWLDataIntersectionOf),
                (OWL + "unionOf", OWLDataUnionOf),
            ):
                members = self.g.value(term, pred)
                if members is not None:
                    operands = [
                        self._data_range(m) for m in self._rdf_list(members)
                    ]
                    if any(op is None for op in operands):
                        return None
                    return ctor(operands)
        return None

    def _facet_restrictions(self, term: Term):  # type: ignore[no-untyped-def]
        """Map an owl:withRestrictions list to OWLFacetRestriction objects."""
        from hermit.owl_model.class_expression.restriction import (
            OWLFacetRestriction,
        )
        from hermit.owl_model.vocab import OWLFacet

        facets_by_iri = {f.iri.as_str(): f for f in OWLFacet}
        restrictions = []
        for member in self._rdf_list(term):
            for pred, obj in self.g.predicate_objects(member):
                if not isinstance(obj, Literal):
                    continue
                facet = facets_by_iri.get(pred)
                if facet is None:
                    return None
                restrictions.append(OWLFacetRestriction(facet, self._literal(obj)))
        return restrictions if restrictions else None

    def _cardinality(self, term: Term, prop: Term) -> OWLClassExpression | None:
        from hermit.owl_model.class_expression import (
            OWLObjectExactCardinality,
            OWLObjectMaxCardinality,
            OWLObjectMinCardinality,
        )

        pe = self._object_prop_expr(prop)
        if pe is None:
            return None
        from hermit.owl_model.class_expression import OWLClass
        thing = OWLClass(OWL + "Thing")

        for pred, ctor, qual in (
            (OWL + "minCardinality", OWLObjectMinCardinality, None),
            (OWL + "minQualifiedCardinality", OWLObjectMinCardinality, OWL + "onClass"),
            (OWL + "maxCardinality", OWLObjectMaxCardinality, None),
            (OWL + "maxQualifiedCardinality", OWLObjectMaxCardinality, OWL + "onClass"),
            (OWL + "cardinality", OWLObjectExactCardinality, None),
            (OWL + "qualifiedCardinality", OWLObjectExactCardinality, OWL + "onClass"),
        ):
            val = self.g.value(term, pred)
            if val is None:
                continue
            n = _int_literal(val)
            if n is None:
                return None
            filler: OWLClassExpression = thing
            if qual is not None:
                qv = self.g.value(term, qual)
                if qv is not None:
                    fc = self._class_expr(qv)
                    if fc is not None:
                        filler = fc
            return ctor(n, pe, filler)
        return None

    # ------------------------------------------------------------------
    # lists / helpers
    # ------------------------------------------------------------------

    def _rdf_list(self, term: Term) -> list[Term]:
        out: list[Term] = []
        node: Term | None = term
        seen: set[int] = set()
        while node is not None and node != RDF_NIL:
            if id(node) in seen:
                break
            seen.add(id(node))
            first = self.g.value(node, RDF_FIRST)
            if first is not None:
                out.append(first)
            node = self.g.value(node, RDF_REST)
        return out

    def _class_list(self, term: Term) -> list[OWLClassExpression]:
        out: list[OWLClassExpression] = []
        for m in self._rdf_list(term):
            ce = self._class_expr(m)
            if ce is not None:
                out.append(ce)
        return out

    def _object_prop(self, iri: Term):  # type: ignore[no-untyped-def]
        from hermit.owl_model.owl_property import OWLObjectProperty
        return OWLObjectProperty(iri if isinstance(iri, str) else _anon_iri(iri))

    def _object_prop_expr(self, term: Term) -> OWLObjectPropertyExpression | None:
        from hermit.owl_model.owl_property import (
            OWLObjectInverseOf,
            OWLObjectProperty,
        )

        if isinstance(term, str):
            return OWLObjectProperty(term)
        if isinstance(term, BNode):
            inv = self.g.value(term, OWL + "inverseOf")
            if inv is not None and isinstance(inv, str):
                return OWLObjectInverseOf(OWLObjectProperty(inv))
        return None

    def _data_prop(self, iri: Term):  # type: ignore[no-untyped-def]
        from hermit.owl_model.owl_property import OWLDataProperty
        return OWLDataProperty(iri if isinstance(iri, str) else _anon_iri(iri))

    def _individual(self, term: Term):  # type: ignore[no-untyped-def]
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        if isinstance(term, str):
            return OWLNamedIndividual(term)
        if isinstance(term, BNode):
            return OWLNamedIndividual(_anon_iri(term))
        return None

    def _literal(self, lit: Literal):  # type: ignore[no-untyped-def]
        from hermit.owl_model.owl_datatype import OWLDatatype
        from hermit.owl_model.owl_literal import OWLLiteral
        dt = lit.datatype or (XSD + "string")
        try:
            return OWLLiteral(lit.value, OWLDatatype(dt))  # type: ignore[abstract]
        except Exception:
            return OWLLiteral(  # type: ignore[abstract]
                lit.value, OWLDatatype(XSD + "string")
            )

    def _add(self, axiom: OWLAxiom) -> None:
        self.axioms.append(axiom)


_STRUCTURAL_TYPES = {
    OWL + "Restriction",
    RDF + "List",
    RDF + "Statement",
    OWL + "AllDifferent",
    OWL + "AllDisjointClasses",
    OWL + "AllDisjointProperties",
}


def _anon_iri(term: Term) -> str:
    if isinstance(term, BNode):
        return f"{ANONYMOUS_INDIVIDUAL_PREFIX}{term.id}"
    return str(term)


def _int_literal(term: Term) -> int | None:
    if isinstance(term, Literal):
        try:
            return int(term.value.strip())
        except ValueError:
            return None
    if isinstance(term, str):
        try:
            return int(term)
        except ValueError:
            return None
    return None
