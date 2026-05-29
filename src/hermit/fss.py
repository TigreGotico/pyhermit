"""Functional-Style Syntax (FSS) reader.

Parses OWL 2 Functional-Style Syntax documents
(https://www.w3.org/TR/owl2-syntax/) into :mod:`hermit.owl_model` axioms,
covering the constructs HermiT reasons over. Annotations and declarations that
carry no logical content are accepted and ignored.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hermit.owl_model.class_expression import OWLClassExpression
    from hermit.owl_model.owl_axiom import OWLAxiom
    from hermit.owl_model.owl_property import OWLObjectPropertyExpression

OWL = "http://www.w3.org/2002/07/owl#"
XSD = "http://www.w3.org/2001/XMLSchema#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"

_TOKEN = re.compile(
    r"""
      \s+
    | \#[^\n]*                       # comment
    | (?P<lparen>\()
    | (?P<rparen>\))
    | (?P<eq>=)
    | (?P<carot>\^\^)
    | (?P<iri><[^>]*>)
    | (?P<str>"(?:\\.|[^"\\])*")
    | (?P<at>@[A-Za-z\-0-9]+)
    | (?P<word>[^\s()"=^]+)
    """,
    re.VERBOSE,
)


class _Tokenizer:
    def __init__(self, text: str) -> None:
        self.tokens: list[tuple[str, str]] = []
        pos = 0
        n = len(text)
        while pos < n:
            m = _TOKEN.match(text, pos)
            if not m or m.end() == pos:
                pos += 1
                continue
            pos = m.end()
            kind = m.lastgroup
            if kind is None:
                continue
            self.tokens.append((kind, m.group()))
        self.i = 0

    def peek(self) -> tuple[str, str] | None:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def next(self) -> tuple[str, str]:
        tok = self.tokens[self.i]
        self.i += 1
        return tok


class _Parser:
    def __init__(self, text: str) -> None:
        self.tk = _Tokenizer(text)
        self.prefixes: dict[str, str] = {
            "owl:": OWL,
            "rdf:": RDF,
            "rdfs:": RDFS,
            "xsd:": XSD,
            ":": "",
        }
        self.base = ""
        self.axioms: list[OWLAxiom] = []

    # -- IRI / literal resolution ------------------------------------

    def _resolve(self, raw: str) -> str:
        if raw.startswith("<") and raw.endswith(">"):
            return raw[1:-1]
        if ":" in raw:
            prefix, _, local = raw.partition(":")
            pfx = prefix + ":"
            if pfx in self.prefixes:
                return self.prefixes[pfx] + local
        return self.base + raw

    # -- parsing -----------------------------------------------------

    def parse(self) -> list[OWLAxiom]:
        while self.tk.peek() is not None:
            tok = self.tk.peek()
            assert tok is not None
            if tok[0] == "word":
                head = tok[1]
                if head == "Prefix":
                    self._prefix_decl()
                    continue
                if head in ("Ontology",):
                    self.tk.next()  # 'Ontology'
                    self._expect("lparen")
                    self._ontology_body()
                    continue
                # Bare top-level axiom keyword.
                self._statement()
            else:
                self.tk.next()
        return self.axioms

    def _prefix_decl(self) -> None:
        self.tk.next()  # 'Prefix'
        self._expect("lparen")
        name = self.tk.next()[1]
        self._expect("eq")
        iri = self.tk.next()[1]
        iri = iri[1:-1] if iri.startswith("<") else iri
        if not name.endswith(":"):
            name += ":"
        self.prefixes[name] = iri
        self._expect("rparen")

    def _ontology_body(self) -> None:
        # Optional ontology IRI / version IRI as bare IRIs.
        while True:
            tok = self.tk.peek()
            if tok is None:
                return
            if tok[0] == "rparen":
                self.tk.next()
                return
            if tok[0] == "iri":
                self.tk.next()
                continue
            if tok[0] == "word" and tok[1] == "Import":
                self._skip_balanced()
                continue
            self._statement()

    def _statement(self) -> None:
        tok = self.tk.peek()
        if tok is None:
            return
        if tok[0] != "word":
            self.tk.next()
            return
        kw = tok[1]
        self.tk.next()
        self._expect("lparen")
        args = self._args()
        self._build(kw, args)

    def _args(self) -> list[object]:
        """Parse a parenthesised argument list (already consumed '(')."""
        args: list[object] = []
        while True:
            tok = self.tk.peek()
            if tok is None:
                return args
            if tok[0] == "rparen":
                self.tk.next()
                return args
            args.append(self._term())

    def _term(self) -> object:
        tok = self.tk.peek()
        assert tok is not None
        if tok[0] in ("iri",):
            self.tk.next()
            return _IRI(self._resolve(tok[1]))
        if tok[0] == "str":
            return self._literal()
        if tok[0] == "word":
            # Could be a constructor keyword (followed by '(') or a prefixed IRI.
            nxt = self.tk.tokens[self.tk.i + 1] if self.tk.i + 1 < len(
                self.tk.tokens
            ) else None
            if nxt is not None and nxt[0] == "lparen" and tok[1][0].isupper() and (
                ":" not in tok[1]
            ):
                self.tk.next()  # keyword
                self._expect("lparen")
                inner = self._args()
                return _Expr(tok[1], inner)
            self.tk.next()
            return _IRI(self._resolve(tok[1]))
        if tok[0] == "lparen":
            self.tk.next()
            return _List(self._args())
        # annotation tokens etc.
        self.tk.next()
        return _IRI(tok[1])

    def _literal(self) -> _Lit:
        s = self.tk.next()[1]
        value = _unescape(s[1:-1])
        lang = None
        dt = None
        nxt = self.tk.peek()
        if nxt is not None and nxt[0] == "at":
            lang = self.tk.next()[1][1:]
        elif nxt is not None and nxt[0] == "carot":
            self.tk.next()
            dtok = self.tk.next()
            dt = self._resolve(dtok[1])
        return _Lit(value, dt, lang)

    # -- helpers -----------------------------------------------------

    def _expect(self, kind: str) -> None:
        tok = self.tk.peek()
        if tok is not None and tok[0] == kind:
            self.tk.next()

    def _skip_balanced(self) -> None:
        self.tk.next()  # keyword
        self._expect("lparen")
        depth = 1
        while depth and self.tk.peek() is not None:
            t = self.tk.next()
            if t[0] == "lparen":
                depth += 1
            elif t[0] == "rparen":
                depth -= 1

    # -- axiom builders ----------------------------------------------

    def _build(self, kw: str, args: list[object]) -> None:  # noqa: C901
        from hermit.owl_model.owl_axiom import OWLAxiom

        # Strip leading annotation arguments.
        args = [a for a in args if not _is_annotation(a)]
        b = _Builder(self)
        try:
            axiom = b.build(kw, args)
        except Exception:
            axiom = None
        if axiom is not None:
            if isinstance(axiom, list):
                self.axioms.extend(axiom)
            elif isinstance(axiom, OWLAxiom):
                self.axioms.append(axiom)


# --------------------------------------------------------------------
# parsed-term value objects
# --------------------------------------------------------------------


class _IRI:
    __slots__ = ("v",)

    def __init__(self, v: str) -> None:
        self.v = v


class _Lit:
    __slots__ = ("value", "dt", "lang")

    def __init__(self, value: str, dt: str | None, lang: str | None) -> None:
        self.value = value
        self.dt = dt
        self.lang = lang


class _Expr:
    __slots__ = ("op", "args")

    def __init__(self, op: str, args: list[object]) -> None:
        self.op = op
        self.args = args


class _List:
    __slots__ = ("items",)

    def __init__(self, items: list[object]) -> None:
        self.items = items


def _is_annotation(arg: object) -> bool:
    return isinstance(arg, _Expr) and arg.op == "Annotation"


def _unescape(s: str) -> str:
    return s.replace('\\"', '"').replace("\\\\", "\\").replace("\\n", "\n")


# --------------------------------------------------------------------
# term → owl_model
# --------------------------------------------------------------------


class _Builder:
    def __init__(self, parser: _Parser) -> None:
        self.p = parser

    def build(self, kw: str, args: list[object]) -> object:  # noqa: C901
        from hermit.owl_model.owl_axiom import (
            OWLAsymmetricObjectPropertyAxiom,
            OWLClassAssertionAxiom,
            OWLDataPropertyAssertionAxiom,
            OWLDataPropertyDomainAxiom,
            OWLDifferentIndividualsAxiom,
            OWLDisjointClassesAxiom,
            OWLEquivalentClassesAxiom,
            OWLEquivalentDataPropertiesAxiom,
            OWLEquivalentObjectPropertiesAxiom,
            OWLFunctionalDataPropertyAxiom,
            OWLFunctionalObjectPropertyAxiom,
            OWLInverseFunctionalObjectPropertyAxiom,
            OWLInverseObjectPropertiesAxiom,
            OWLIrreflexiveObjectPropertyAxiom,
            OWLObjectPropertyAssertionAxiom,
            OWLObjectPropertyDomainAxiom,
            OWLObjectPropertyRangeAxiom,
            OWLReflexiveObjectPropertyAxiom,
            OWLSameIndividualAxiom,
            OWLSubClassOfAxiom,
            OWLSubDataPropertyOfAxiom,
            OWLSubObjectPropertyOfAxiom,
            OWLSubPropertyChainAxiom,
            OWLSymmetricObjectPropertyAxiom,
            OWLTransitiveObjectPropertyAxiom,
        )

        if kw == "Declaration":
            return None
        if kw == "SubClassOf":
            return OWLSubClassOfAxiom(self.ce(args[0]), self.ce(args[1]))
        if kw == "EquivalentClasses":
            return OWLEquivalentClassesAxiom([self.ce(a) for a in args])
        if kw == "DisjointClasses":
            return OWLDisjointClassesAxiom([self.ce(a) for a in args])
        if kw == "DisjointUnion":
            cls = self.ce(args[0])
            rest = [self.ce(a) for a in args[1:]]
            from hermit.owl_model.class_expression import OWLObjectUnionOf
            return OWLEquivalentClassesAxiom([cls, OWLObjectUnionOf(rest)])
        if kw == "ClassAssertion":
            return OWLClassAssertionAxiom(self.ind(args[1]), self.ce(args[0]))
        if kw == "ObjectPropertyAssertion":
            return OWLObjectPropertyAssertionAxiom(
                self.ind(args[1]), self.ope(args[0]), self.ind(args[2])
            )
        if kw == "DataPropertyAssertion":
            return OWLDataPropertyAssertionAxiom(
                self.ind(args[1]), self.dpe(args[0]), self.lit(args[2])
            )
        if kw == "SameIndividual":
            return OWLSameIndividualAxiom([self.ind(a) for a in args])
        if kw == "DifferentIndividuals":
            return OWLDifferentIndividualsAxiom([self.ind(a) for a in args])
        if kw == "SubObjectPropertyOf":
            if isinstance(args[0], _Expr) and args[0].op == "ObjectPropertyChain":
                chain = [self.ope(a) for a in args[0].args]
                return OWLSubPropertyChainAxiom(chain, self.ope(args[1]))
            return OWLSubObjectPropertyOfAxiom(self.ope(args[0]), self.ope(args[1]))
        if kw == "EquivalentObjectProperties":
            return OWLEquivalentObjectPropertiesAxiom([self.ope(a) for a in args])
        if kw == "InverseObjectProperties":
            return OWLInverseObjectPropertiesAxiom(
                self.ope(args[0]), self.ope(args[1])
            )
        if kw == "ObjectPropertyDomain":
            return OWLObjectPropertyDomainAxiom(self.ope(args[0]), self.ce(args[1]))
        if kw == "ObjectPropertyRange":
            return OWLObjectPropertyRangeAxiom(self.ope(args[0]), self.ce(args[1]))
        if kw == "TransitiveObjectProperty":
            return OWLTransitiveObjectPropertyAxiom(self.ope(args[0]))
        if kw == "SymmetricObjectProperty":
            return OWLSymmetricObjectPropertyAxiom(self.ope(args[0]))
        if kw == "AsymmetricObjectProperty":
            return OWLAsymmetricObjectPropertyAxiom(self.ope(args[0]))
        if kw == "ReflexiveObjectProperty":
            return OWLReflexiveObjectPropertyAxiom(self.ope(args[0]))
        if kw == "IrreflexiveObjectProperty":
            return OWLIrreflexiveObjectPropertyAxiom(self.ope(args[0]))
        if kw == "FunctionalObjectProperty":
            return OWLFunctionalObjectPropertyAxiom(self.ope(args[0]))
        if kw == "InverseFunctionalObjectProperty":
            return OWLInverseFunctionalObjectPropertyAxiom(self.ope(args[0]))
        if kw == "SubDataPropertyOf":
            return OWLSubDataPropertyOfAxiom(self.dpe(args[0]), self.dpe(args[1]))
        if kw == "EquivalentDataProperties":
            return OWLEquivalentDataPropertiesAxiom([self.dpe(a) for a in args])
        if kw == "DataPropertyDomain":
            return OWLDataPropertyDomainAxiom(self.dpe(args[0]), self.ce(args[1]))
        if kw == "FunctionalDataProperty":
            return OWLFunctionalDataPropertyAxiom(self.dpe(args[0]))
        return None

    # -- term converters ---------------------------------------------

    def ce(self, t: object) -> OWLClassExpression:  # noqa: C901
        from hermit.owl_model.class_expression import (
            OWLClass,
            OWLObjectAllValuesFrom,
            OWLObjectComplementOf,
            OWLObjectExactCardinality,
            OWLObjectHasSelf,
            OWLObjectHasValue,
            OWLObjectIntersectionOf,
            OWLObjectMaxCardinality,
            OWLObjectMinCardinality,
            OWLObjectOneOf,
            OWLObjectSomeValuesFrom,
            OWLObjectUnionOf,
        )

        if isinstance(t, _IRI):
            return OWLClass(t.v)
        if not isinstance(t, _Expr):
            return OWLClass(OWL + "Thing")
        op, a = t.op, t.args
        if op == "ObjectIntersectionOf":
            return OWLObjectIntersectionOf([self.ce(x) for x in a])
        if op == "ObjectUnionOf":
            return OWLObjectUnionOf([self.ce(x) for x in a])
        if op == "ObjectComplementOf":
            return OWLObjectComplementOf(self.ce(a[0]))
        if op == "ObjectOneOf":
            return OWLObjectOneOf([self.ind(x) for x in a])
        if op == "ObjectSomeValuesFrom":
            return OWLObjectSomeValuesFrom(self.ope(a[0]), self.ce(a[1]))
        if op == "ObjectAllValuesFrom":
            return OWLObjectAllValuesFrom(self.ope(a[0]), self.ce(a[1]))
        if op == "ObjectHasValue":
            return OWLObjectHasValue(self.ope(a[0]), self.ind(a[1]))
        if op == "ObjectHasSelf":
            return OWLObjectHasSelf(self.ope(a[0]))
        if op == "ObjectMinCardinality":
            return OWLObjectMinCardinality(
                int(_iri_str(a[0])), self.ope(a[1]),
                self.ce(a[2]) if len(a) > 2 else OWLClass(OWL + "Thing"),
            )
        if op == "ObjectMaxCardinality":
            return OWLObjectMaxCardinality(
                int(_iri_str(a[0])), self.ope(a[1]),
                self.ce(a[2]) if len(a) > 2 else OWLClass(OWL + "Thing"),
            )
        if op == "ObjectExactCardinality":
            return OWLObjectExactCardinality(
                int(_iri_str(a[0])), self.ope(a[1]),
                self.ce(a[2]) if len(a) > 2 else OWLClass(OWL + "Thing"),
            )
        # Data-range restrictions exercise datatype reasoning the clausifier
        # does not support; over-approximate to owl:Thing rather than emit an
        # expression the clausifier cannot accept.
        return OWLClass(OWL + "Thing")

    def ope(self, t: object) -> OWLObjectPropertyExpression:
        from hermit.owl_model.owl_property import (
            OWLObjectInverseOf,
            OWLObjectProperty,
        )
        if isinstance(t, _Expr) and t.op in ("ObjectInverseOf", "InverseOf"):
            return OWLObjectInverseOf(OWLObjectProperty(_iri_str(t.args[0])))
        return OWLObjectProperty(_iri_str(t))

    def dpe(self, t: object):  # type: ignore[no-untyped-def]
        from hermit.owl_model.owl_property import OWLDataProperty
        return OWLDataProperty(_iri_str(t))

    def ind(self, t: object):  # type: ignore[no-untyped-def]
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        if isinstance(t, _Expr):
            return OWLNamedIndividual(OWL + "Nothing")
        return OWLNamedIndividual(_iri_str(t))

    def lit(self, t: object):  # type: ignore[no-untyped-def]
        from hermit.owl_model.owl_datatype import OWLDatatype
        from hermit.owl_model.owl_literal import OWLLiteral
        if isinstance(t, _Lit):
            dt = t.dt or (XSD + "string")
            try:
                return OWLLiteral(t.value, OWLDatatype(dt))  # type: ignore[abstract]
            except Exception:
                return OWLLiteral(  # type: ignore[abstract]
                    t.value, OWLDatatype(XSD + "string")
                )
        return OWLLiteral(  # type: ignore[abstract]
            _iri_str(t), OWLDatatype(XSD + "string")
        )

def _iri_str(t: object) -> str:
    if isinstance(t, _IRI):
        return t.v
    if isinstance(t, _Lit):
        return t.value
    return str(t)


def parse_functional_syntax(text: str) -> list[OWLAxiom]:
    """Parse an OWL 2 Functional-Style Syntax document into OWL axioms."""
    return _Parser(text).parse()
