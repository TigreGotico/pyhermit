"""
HermiT Python — Core DL Model Objects

This module contains the foundational model classes that represent DL
clauses, concepts, roles, individuals, and constants.  The class hierarchy
mirrors the Java original as closely as possible to preserve algorithmic
behaviour.

Class hierarchy (model)::

    Term
    ├── Individual
    ├── Variable
    └── Constant

    Concept
    ├── LiteralConcept
    │   ├── AtomicConcept          (also DLPredicate)
    │   └── AtomicNegationConcept
    ├── AtMostConcept
    └── ExistentialConcept
        └── AtLeast                (also DLPredicate)
            ├── AtLeastConcept
            └── AtLeastDataRange

    Role
    ├── AtomicRole                 (also DLPredicate)
    └── InverseRole

    DLPredicate  (protocol)
    ├── AtomicConcept, AtomicRole
    ├── Equality, Inequality
    ├── AnnotatedEquality
    ├── NodeIDLessEqualThan
    ├── NodeIDsAscendingOrEqual
    ├── AtLeast, ExistsDescriptionGraph
    ├── InternalDatatype
    └── Atom, DLClause (contain DLPredicates)

    DataRange
    ├── AtomicDataRange
    │   ├── DatatypeRestriction
    │   └── InternalDatatype       (also DLPredicate)
    └── AtomicNegationDataRange

    DescriptionGraph (+ Edge)
    ExistsDescriptionGraph
    DLOntology
"""

from __future__ import annotations

__all__ = [
    # Protocols / interfaces
    "DLPredicate",
    # Terms
    "Term",
    "Individual",
    "Variable",
    "Constant",
    # Concepts
    "Concept",
    "LiteralConcept",
    "ExistentialConcept",
    "AtomicConcept",
    "AtomicNegationConcept",
    "AtLeast",
    "AtLeastConcept",
    "AtLeastDataRange",
    "AtMostConcept",
    "ExistsDescriptionGraph",
    # Roles
    "Role",
    "AtomicRole",
    "InverseRole",
    "NegatedAtomicRole",
    # Atoms & clauses
    "Atom",
    "DLClause",
    # Equality / inequality
    "Equality",
    "Inequality",
    "AnnotatedEquality",
    "NodeIDLessEqualThan",
    "NodeIDsAscendingOrEqual",
    # Data ranges
    "DataRange",
    "AtomicDataRange",
    "AtomicNegationDataRange",
    "ConstantEnumeration",
    "DatatypeRestriction",
    "InternalDatatype",
    # Description graphs
    "DescriptionGraph",
    "DescriptionGraphEdge",
    # Ontology
    "DLOntology",
    # Helpers
    "Prefixes",
    "Interner",
]

import re
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any, ClassVar, Protocol, TypeVar, cast
from collections.abc import Collection, Mapping

_T = TypeVar("_T")

# ---------------------------------------------------------------------------
# Interner — replacement for Java's InterningManager
# ---------------------------------------------------------------------------

class Interner:
    """
    Object interner that ensures canonical instances for hash-/equality-
    based identity.  Replaces the Java ``InterningManager`` which uses
    weak-reference hash maps; here we use a plain dict because Python's
    GC will reclaim unreferenced entries when the ``Interner`` itself is
    garbage-collected.
    """

    __slots__ = ("_cache",)

    def __init__(self) -> None:
        self._cache: dict[type[Any], dict[int, Any]] = {}

    def intern(self, obj: _T) -> _T:
        key: type[Any] = type(obj)
        bucket = self._cache.get(key)
        if bucket is None:
            bucket = {}
            self._cache[key] = bucket
        h = hash(obj)
        existing: Any = bucket.get(h)
        if existing is not None and existing == obj:
            return cast(_T, existing)
        bucket[h] = obj
        return obj


# Shared interner for all model objects
_interner = Interner()


# ---------------------------------------------------------------------------
# Prefixes
# ---------------------------------------------------------------------------

class Prefixes:
    """
    Manages IRI prefix declarations for abbreviating and expanding IRIs.
    Faithful port of the Java ``Prefixes`` class.
    """

    _PN_CHARS_BASE = (
        r"[A-Za-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF"
        r"\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F"
        r"\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD]"
    )
    _PN_CHARS = (
        r"[A-Za-z0-9_\u002D\u00B7\u00C0-\u00D6\u00D8-\u00F6"
        r"\u00F8-\u02FF\u0300-\u036F\u0370-\u037D\u037F-\u1FFF"
        r"\u200C-\u200D\u203F-\u2040\u2070-\u218F\u2C00-\u2FEF"
        r"\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD]"
    )
    _LOCAL_NAME_RE = re.compile(
        rf"({_PN_CHARS_BASE}|_|[0-9])"
        rf"(({_PN_CHARS}|[.])*({_PN_CHARS}))?"
    )

    SEMANTIC_WEB_PREFIXES: ClassVar[Mapping[str, str]] = {
        "rdf:": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs:": "http://www.w3.org/2000/01/rdf-schema#",
        "owl:": "http://www.w3.org/2002/07/owl#",
        "xsd:": "http://www.w3.org/2001/XMLSchema#",
        "swrl:": "http://www.w3.org/2003/11/swrl#",
        "swrlb:": "http://www.w3.org/2003/11/swrlb#",
    }

    STANDARD: ClassVar[Prefixes]

    def __init__(self) -> None:
        self._prefix_iris_by_name: dict[str, str] = OrderedDict()
        self._prefix_names_by_iri: dict[str, str] = OrderedDict()
        self._pattern: re.Pattern[str] | None = None

    # -- public API --------------------------------------------------------

    def abbreviate_iri(self, iri: str) -> str:
        if self._pattern is not None:
            m = self._pattern.match(iri)
            if m:
                local_name = iri[m.end():]
                if self._is_valid_local_name(local_name):
                    prefix_name = self._prefix_names_by_iri[m.group(1)]
                    return prefix_name + local_name
        return f"<{iri}>"

    def expand_abbreviation(self, abbreviation: str) -> str:
        if abbreviation and abbreviation[0] == "<":
            if not abbreviation.endswith(">"):
                raise ValueError(
                    f"IRI '{abbreviation}' must be enclosed in '<' and '>'"
                )
            return abbreviation[1:-1]
        pos = abbreviation.find(":")
        if pos != -1:
            prefix = abbreviation[:pos + 1]
            prefix_iri = self._prefix_iris_by_name.get(prefix)
            if prefix_iri is None:
                if prefix == "http:":
                    raise ValueError(
                        f"IRI '{abbreviation}' must be enclosed in '<' and '>'"
                    )
                raise ValueError(f"'{prefix}' is not a registered prefix")
            return prefix_iri + abbreviation[pos + 1:]
        raise ValueError(f"Abbreviation '{abbreviation}' is not valid")

    def declare_prefix(self, prefix_name: str, prefix_iri: str) -> bool:
        if not prefix_name.endswith(":"):
            raise ValueError(f"Prefix name '{prefix_name}' should end with ':'")
        existing = self._prefix_names_by_iri.get(prefix_iri)
        if existing is not None and prefix_name != existing:
            raise ValueError(
                f"Prefix IRI '{prefix_iri}' already associated with '{existing}'"
            )
        self._prefix_names_by_iri[prefix_iri] = prefix_name
        contains = self._prefix_iris_by_name.get(prefix_name) is not None
        self._prefix_iris_by_name[prefix_name] = prefix_iri
        self._rebuild_pattern()
        return not contains

    def declare_default_prefix(self, default_iri: str) -> bool:
        return self.declare_prefix(":", default_iri)

    def declare_semantic_web_prefixes(self) -> bool:
        contains = False
        for name, iri in self.SEMANTIC_WEB_PREFIXES.items():
            if self._declare_prefix_raw(name, iri):
                contains = True
        self._rebuild_pattern()
        return contains

    def declare_internal_prefixes(
        self,
        individual_iris: Collection[str] = (),
        anon_individual_iris: Collection[str] = (),
    ) -> bool:
        contains = False
        internals = [
            ("def:", "internal:def#"),
            ("defdata:", "internal:defdata#"),
            ("nnq:", "internal:nnq#"),
            ("all:", "internal:all#"),
            ("swrl:", "internal:swrl#"),
            ("prop:", "internal:prop#"),
            ("nam:", "internal:nam#"),
        ]
        for name, iri in internals:
            if self._declare_prefix_raw(name, iri):
                contains = True

        for idx, iri in enumerate(individual_iris, 1):
            suffix = "" if idx == 1 else str(idx)
            if self._declare_prefix_raw(f"nom{suffix}:", f"internal:nom#{iri}"):
                contains = True

        for idx, iri in enumerate(anon_individual_iris, 1):
            suffix = "" if idx == 1 else str(idx)
            if self._declare_prefix_raw(f"anon{suffix}:", f"internal:anon#{iri}"):
                contains = True

        self._rebuild_pattern()
        return contains

    def get_prefix_iri(self, prefix_name: str) -> str | None:
        return self._prefix_iris_by_name.get(prefix_name)

    def get_prefix_name(self, prefix_iri: str) -> str | None:
        return self._prefix_names_by_iri.get(prefix_iri)

    @property
    def prefix_map(self) -> Mapping[str, str]:
        return dict(self._prefix_iris_by_name)

    @staticmethod
    def is_internal_iri(iri: str) -> bool:
        return iri.startswith("internal:")

    @classmethod
    def _is_valid_local_name(cls, local_name: str) -> bool:
        return cls._LOCAL_NAME_RE.fullmatch(local_name) is not None

    # -- internal helpers --------------------------------------------------

    def _declare_prefix_raw(self, prefix_name: str, prefix_iri: str) -> bool:
        if not prefix_name.endswith(":"):
            raise ValueError(f"Prefix name '{prefix_name}' should end with ':'")
        existing = self._prefix_names_by_iri.get(prefix_iri)
        if existing is not None and prefix_name != existing:
            raise ValueError(
                f"Prefix IRI '{prefix_iri}' already associated with '{existing}'"
            )
        self._prefix_names_by_iri[prefix_iri] = prefix_name
        contains = self._prefix_iris_by_name.get(prefix_name) is not None
        self._prefix_iris_by_name[prefix_name] = prefix_iri
        return not contains

    def _rebuild_pattern(self) -> None:
        if not self._prefix_names_by_iri:
            self._pattern = None
            return
        # longest IRIs first
        sorted_iris = sorted(self._prefix_names_by_iri, key=len, reverse=True)
        pattern = "|".join(re.escape(iri) for iri in sorted_iris)
        self._pattern = re.compile(f"^({pattern})")

    def __repr__(self) -> str:
        return repr(dict(self._prefix_iris_by_name))


# Initialise standard prefixes
_PREFIXES_STANDARD = Prefixes()
_PREFIXES_STANDARD.declare_semantic_web_prefixes()
Prefixes.STANDARD = _PREFIXES_STANDARD


# ---------------------------------------------------------------------------
# DLPredicate protocol
# ---------------------------------------------------------------------------

class DLPredicate(Protocol):
    """Interface for DL predicates (concepts, roles, equality, etc.)."""

    def arity(self) -> int: ...
    def __str__(self) -> str: ...


# ---------------------------------------------------------------------------
# Term hierarchy
# ---------------------------------------------------------------------------

class Term(ABC):
    """Base class for terms in DL clauses."""

    __slots__ = ()

    @abstractmethod
    def __str__(self) -> str: ...


class Individual(Term):
    """Represents an individual (named or anonymous) in a DL clause."""

    __slots__ = ("_uri",)

    def __init__(self, uri: str) -> None:
        self._uri = uri

    @property
    def iri(self) -> str:
        return self._uri

    def is_anonymous(self) -> bool:
        return self._uri.startswith("internal:anonymous#")

    def __str__(self) -> str:
        return Prefixes.STANDARD.abbreviate_iri(self._uri)

    def __repr__(self) -> str:
        return f"Individual({self._uri!r})"

    def __hash__(self) -> int:
        return hash(self._uri)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Individual):
            return self._uri == other._uri
        return False

    @classmethod
    def create(cls, uri: str) -> Individual:
        return _interner.intern(cls(uri))

    @classmethod
    def create_anonymous(cls, id: str) -> Individual:
        return cls.create(cls._anonymous_uri(id))

    @staticmethod
    def _anonymous_uri(id: str) -> str:
        return f"internal:anonymous#{id}"


class Variable(Term):
    """Represents a variable in DL clauses."""

    __slots__ = ("_name",)

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return f"Variable({self._name!r})"

    def __hash__(self) -> int:
        return hash(self._name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Variable):
            return self._name == other._name
        return False

    @classmethod
    def create(cls, name: str) -> Variable:
        return _interner.intern(cls(name))


class Constant(Term):
    """Represents a data constant (literal value)."""

    __slots__ = ("_lexical_form", "_datatype_iri", "_data_value")

    def __init__(self, lexical_form: str, datatype_iri: str, data_value: Any) -> None:
        self._lexical_form = lexical_form
        self._datatype_iri = datatype_iri
        self._data_value = data_value

    @property
    def lexical_form(self) -> str:
        return self._lexical_form

    @property
    def datatype_iri(self) -> str:
        return self._datatype_iri

    @property
    def data_value(self) -> Any:
        return self._data_value

    def is_anonymous(self) -> bool:
        return self._datatype_iri == "internal:anonymous-constants"

    def __str__(self) -> str:
        escaped = self._lexical_form.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"^^{Prefixes.STANDARD.abbreviate_iri(self._datatype_iri)}'

    def __repr__(self) -> str:
        return f"Constant({self._lexical_form!r}, {self._datatype_iri!r})"

    def __hash__(self) -> int:
        return hash(self._lexical_form) + hash(self._datatype_iri)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Constant):
            return (
                self._lexical_form == other._lexical_form
                and self._datatype_iri == other._datatype_iri
            )
        return False

    @classmethod
    def create(cls, lexical_form: str, datatype_iri: str) -> Constant:
        # Deferred import to avoid circular dependency
        from hermit.datatypes.registry import DatatypeRegistry

        try:
            data_value = DatatypeRegistry.parse_literal(lexical_form, datatype_iri)
        except Exception:
            # If registry not yet fully initialised, store None
            data_value = None
        return _interner.intern(cls(lexical_form, datatype_iri, data_value))

    @classmethod
    def create_anonymous(cls, id: str) -> Constant:
        return cls.create(id, "internal:anonymous-constants")


# ---------------------------------------------------------------------------
# Concept hierarchy
# ---------------------------------------------------------------------------

class Concept(ABC):
    """Base class for (complex) concepts."""

    __slots__ = ()

    @abstractmethod
    def is_always_true(self) -> bool: ...

    @abstractmethod
    def is_always_false(self) -> bool: ...

    def accept(self, visitor: Any) -> None:
        """Dispatch to the appropriate visitor method on *visitor*."""
        if isinstance(self, AtomicConcept):
            visitor.visit_atomic_concept(self)
        elif isinstance(self, AtomicNegationConcept):
            visitor.visit_atomic_negation_concept(self)
        elif isinstance(self, AtLeastConcept):
            visitor.visit_at_least_concept(self)
        elif isinstance(self, AtLeastDataRange):
            visitor.visit_at_least_data_range(self)
        elif isinstance(self, ExistsDescriptionGraph):
            visitor.visit_exists_description_graph(self)
        else:
            visitor.visit_other_concept(self)

    def __str__(self) -> str:
        return str(self)


class LiteralConcept(Concept):
    """A literal concept — atomic or negated atomic."""

    __slots__ = ()

    @abstractmethod
    def get_negation(self) -> LiteralConcept: ...


class AtomicConcept(LiteralConcept):
    """
    An atomic concept (class name).  Also serves as a ``DLPredicate``
    with arity 1.
    """

    __slots__ = ("_iri",)

    THING_IRI = "http://www.w3.org/2002/07/owl#Thing"
    NOTHING_IRI = "http://www.w3.org/2002/07/owl#Nothing"
    INTERNAL_NAMED_IRI = "internal:nam#Named"

    THING: ClassVar[AtomicConcept]
    NOTHING: ClassVar[AtomicConcept]
    INTERNAL_NAMED: ClassVar[AtomicConcept]

    def __init__(self, iri: str) -> None:
        self._iri = iri

    @property
    def iri(self) -> str:
        return self._iri

    def arity(self) -> int:
        return 1


    def get_negation(self) -> LiteralConcept:
        if self is self.THING:
            return self.NOTHING
        if self is self.NOTHING:
            return self.THING
        return AtomicNegationConcept.create(self)

    def is_always_true(self) -> bool:
        return self is self.THING

    def is_always_false(self) -> bool:
        return self is self.NOTHING

    def __str__(self) -> str:
        return Prefixes.STANDARD.abbreviate_iri(self._iri)

    def __repr__(self) -> str:
        return f"AtomicConcept({self._iri!r})"

    def __hash__(self) -> int:
        return hash(self._iri)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AtomicConcept):
            return self._iri == other._iri
        return False

    def equals(self, other: object) -> bool:
        """Java-compatible equality check."""
        return self.__eq__(other)

    @classmethod
    def create(cls, uri: str) -> AtomicConcept:
        return _interner.intern(cls(uri))

    @classmethod
    def _predefined(cls) -> tuple[AtomicConcept, AtomicConcept, AtomicConcept]:
        thing: AtomicConcept = _interner.intern(cls(cls.THING_IRI))
        nothing: AtomicConcept = _interner.intern(cls(cls.NOTHING_IRI))
        internal_named: AtomicConcept = _interner.intern(cls(cls.INTERNAL_NAMED_IRI))
        return thing, nothing, internal_named


# Pre-create canonical instances
AtomicConcept.THING, AtomicConcept.NOTHING, AtomicConcept.INTERNAL_NAMED = AtomicConcept._predefined()


class AtomicNegationConcept(LiteralConcept):
    """Negation of an atomic concept."""

    __slots__ = ("_negated",)

    def __init__(self, negated: AtomicConcept) -> None:
        self._negated = negated

    @property
    def negated(self) -> AtomicConcept:
        return self._negated

    def arity(self) -> int:
        return 1


    def get_negation(self) -> LiteralConcept:
        return self._negated

    def is_always_true(self) -> bool:
        return self._negated is AtomicConcept.NOTHING

    def is_always_false(self) -> bool:
        return self._negated is AtomicConcept.THING

    def __str__(self) -> str:
        return f"¬{self._negated}"

    def __repr__(self) -> str:
        return f"AtomicNegationConcept({self._negated!r})"

    def __hash__(self) -> int:
        return -hash(self._negated)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AtomicNegationConcept):
            return self._negated == other._negated
        return False

    @classmethod
    def create(cls, negated: AtomicConcept) -> AtomicNegationConcept:
        return _interner.intern(cls(negated))


# ---------------------------------------------------------------------------
# Role hierarchy
# ---------------------------------------------------------------------------

class Role(ABC):
    """Base class for roles (object/data properties)."""

    __slots__ = ()

    @abstractmethod
    def get_inverse(self) -> Role: ...

    @abstractmethod
    def get_role_assertion(self, term0: Term, term1: Term) -> Atom: ...

    def __str__(self) -> str:
        return str(self)


class AtomicRole(Role):
    """An atomic role (property name).  Also a ``DLPredicate`` with arity 2."""

    __slots__ = ("_iri",)

    TOP_OBJECT_ROLE_IRI = "http://www.w3.org/2002/07/owl#topObjectProperty"
    BOTTOM_OBJECT_ROLE_IRI = "http://www.w3.org/2002/07/owl#bottomObjectProperty"
    TOP_DATA_ROLE_IRI = "http://www.w3.org/2002/07/owl#topDataProperty"
    BOTTOM_DATA_ROLE_IRI = "http://www.w3.org/2002/07/owl#bottomDataProperty"

    TOP_OBJECT_ROLE: ClassVar[AtomicRole]
    BOTTOM_OBJECT_ROLE: ClassVar[AtomicRole]
    TOP_DATA_ROLE: ClassVar[AtomicRole]
    BOTTOM_DATA_ROLE: ClassVar[AtomicRole]

    def __init__(self, iri: str) -> None:
        self._iri = iri

    @property
    def iri(self) -> str:
        return self._iri

    def arity(self) -> int:
        return 2


    def get_inverse(self) -> Role:
        if self in (self.TOP_OBJECT_ROLE, self.BOTTOM_OBJECT_ROLE):
            return self
        return InverseRole.create(self)

    def get_role_assertion(self, term0: Term, term1: Term) -> Atom:
        return Atom.create(self, term0, term1)

    def __str__(self) -> str:
        return Prefixes.STANDARD.abbreviate_iri(self._iri)

    def __repr__(self) -> str:
        return f"AtomicRole({self._iri!r})"

    def __hash__(self) -> int:
        return hash(self._iri)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AtomicRole):
            return self._iri == other._iri
        return False

    def equals(self, other: object) -> bool:
        """Java-compatible equality check."""
        return self.__eq__(other)

    @classmethod
    def create(cls, iri: str) -> AtomicRole:
        return _interner.intern(cls(iri))

    @classmethod
    def _predefined(
        cls,
    ) -> tuple[AtomicRole, AtomicRole, AtomicRole, AtomicRole]:
        top_obj: AtomicRole = _interner.intern(cls(cls.TOP_OBJECT_ROLE_IRI))
        bot_obj: AtomicRole = _interner.intern(cls(cls.BOTTOM_OBJECT_ROLE_IRI))
        top_data: AtomicRole = _interner.intern(cls(cls.TOP_DATA_ROLE_IRI))
        bot_data: AtomicRole = _interner.intern(cls(cls.BOTTOM_DATA_ROLE_IRI))
        return top_obj, bot_obj, top_data, bot_data


(
    AtomicRole.TOP_OBJECT_ROLE,
    AtomicRole.BOTTOM_OBJECT_ROLE,
    AtomicRole.TOP_DATA_ROLE,
    AtomicRole.BOTTOM_DATA_ROLE,
) = AtomicRole._predefined()


class InverseRole(Role):
    """Inverse of an atomic role."""

    __slots__ = ("_inverse_of",)

    def __init__(self, inverse_of: AtomicRole) -> None:
        self._inverse_of = inverse_of

    @property
    def inverse_of(self) -> AtomicRole:
        return self._inverse_of

    def get_inverse(self) -> Role:
        return self._inverse_of

    def arity(self) -> int:
        return 2


    def get_role_assertion(self, term0: Term, term1: Term) -> Atom:
        return Atom.create(self._inverse_of, term1, term0)

    def __str__(self) -> str:
        return f"inv({self._inverse_of})"

    def __repr__(self) -> str:
        return f"InverseRole({self._inverse_of!r})"

    def __hash__(self) -> int:
        return -hash(self._inverse_of)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, InverseRole):
            return self._inverse_of == other._inverse_of
        return False

    def equals(self, other: object) -> bool:
        return self.__eq__(other)

    @classmethod
    def create(cls, inverse_of: AtomicRole) -> InverseRole:
        return _interner.intern(cls(inverse_of))


# ---------------------------------------------------------------------------
# NegatedAtomicRole
# ---------------------------------------------------------------------------

class NegatedAtomicRole:
    """Represents a negated atomic role (not(R))."""

    __slots__ = ("_negated_atomic_role",)

    def __init__(self, negated_atomic_role: AtomicRole) -> None:
        self._negated_atomic_role = negated_atomic_role

    @property
    def negated_atomic_role(self) -> AtomicRole:
        return self._negated_atomic_role

    def __str__(self) -> str:
        return f"not({self._negated_atomic_role})"

    def __repr__(self) -> str:
        return f"NegatedAtomicRole({self._negated_atomic_role!r})"

    def __hash__(self) -> int:
        return -hash(self._negated_atomic_role)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, NegatedAtomicRole):
            return self._negated_atomic_role == other._negated_atomic_role
        return False

    @classmethod
    def create(cls, negated_atomic_role: AtomicRole) -> NegatedAtomicRole:
        return _interner.intern(cls(negated_atomic_role))


# ---------------------------------------------------------------------------
# Equality / Inequality sentinels
# ---------------------------------------------------------------------------

class Equality:
    """Equality predicate (==) in DL clauses."""

    __slots__ = ()

    INSTANCE: ClassVar[Equality]

    def __init__(self) -> None:
        pass

    def arity(self) -> int:
        return 2


    def __str__(self) -> str:
        return "=="

    def __repr__(self) -> str:
        return "Equality"

    def __hash__(self) -> int:
        return 1

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Equality)


Equality.INSTANCE = Equality()


class Inequality:
    """Inequality predicate (!=) in DL clauses."""

    __slots__ = ()

    INSTANCE: ClassVar[Inequality]

    def __init__(self) -> None:
        pass

    def arity(self) -> int:
        return 2


    def __str__(self) -> str:
        return "!="

    def __repr__(self) -> str:
        return "Inequality"

    def __hash__(self) -> int:
        return 2

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Inequality)

    def equals(self, other: object) -> bool:
        """Java-compatible equality check."""
        return self.__eq__(other)


Inequality.INSTANCE = Inequality()


# ---------------------------------------------------------------------------
# Atom
# ---------------------------------------------------------------------------

# Forward references for Atom
_INFIX_PREDICATES: set[DLPredicate] = set()


class Atom:
    """
    An atom in a DL clause: a DL predicate applied to a sequence of terms.

    E.g., ``C(X)``, ``R(X, Y)``, ``X == Y``.
    """

    __slots__ = ("_predicate", "_arguments")

    def __init__(self, predicate: DLPredicate, arguments: tuple[Term, ...]) -> None:
        self._predicate = predicate
        self._arguments = arguments
        if predicate.arity() != len(arguments):
            raise ValueError(
                f"Predicate arity {predicate.arity()} != number of arguments {len(arguments)}"
            )

    @property
    def predicate(self) -> DLPredicate:
        return self._predicate

    def arity(self) -> int:
        return len(self._arguments)


    def argument(self, index: int) -> Term:
        return self._arguments[index]

    def get_argument(self, index: int) -> Term:
        """Java-compatible alias for :meth:`argument`."""
        return self.argument(index)

    def argument_variable(self, index: int) -> Variable | None:
        arg = self._arguments[index]
        if isinstance(arg, Variable):
            return arg
        return None

    def get_argument_variable(self, index: int) -> Variable | None:
        """Java-compatible alias for :meth:`argument_variable`."""
        return self.argument_variable(index)

    def get_variables(self, variables: set[Variable]) -> None:
        for arg in self._arguments:
            if isinstance(arg, Variable):
                variables.add(arg)

    def get_individuals(self, individuals: set[Individual]) -> None:
        for arg in self._arguments:
            if isinstance(arg, Individual):
                individuals.add(arg)

    def contains_variable(self, variable: Variable) -> bool:
        return variable in self._arguments

    def replace_predicate(self, new_predicate: DLPredicate) -> Atom:
        return Atom.create(new_predicate, *self._arguments)

    def get_dl_predicate(self) -> DLPredicate:
        """Java-compatible alias for :attr:`predicate`."""
        return self._predicate

    def equals(self, other: object) -> bool:
        """Java-compatible equality check."""
        return self.__eq__(other)

    def __str__(self) -> str:
        pred = self._predicate
        args = self._arguments
        if pred in _INFIX_PREDICATES:
            return f"{args[0]} {pred} {args[1]}"
        arg_strs = ",".join(str(a) for a in args)
        return f"{pred}({arg_strs})"

    def __repr__(self) -> str:
        return f"Atom({self._predicate}, {self._arguments})"

    def __hash__(self) -> int:
        h = hash(self._predicate)
        for arg in self._arguments:
            h += hash(arg)
        return h

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Atom):
            return (
                self._predicate == other._predicate
                and self._arguments == other._arguments
            )
        return False

    @classmethod
    def create(cls, predicate: DLPredicate, *arguments: Term) -> Atom:
        return _interner.intern(cls(predicate, arguments))


# Register infix predicates
_INFIX_PREDICATES.add(Equality.INSTANCE)
_INFIX_PREDICATES.add(Inequality.INSTANCE)


# ---------------------------------------------------------------------------
# DLClause
# ---------------------------------------------------------------------------

class DLClause:
    """
    A DL clause: a disjunction of head atoms implied by a conjunction of body atoms.

    Represented as:  headAtoms :- bodyAtoms

    I.e.,  bodyAtoms → headAtoms
    """

    __slots__ = ("_head_atoms", "_body_atoms")

    def __init__(
        self,
        head_atoms: tuple[Atom, ...],
        body_atoms: tuple[Atom, ...],
    ) -> None:
        self._head_atoms = head_atoms
        self._body_atoms = body_atoms

    @property
    def head_atoms(self) -> tuple[Atom, ...]:
        return self._head_atoms

    @property
    def body_atoms(self) -> tuple[Atom, ...]:
        return self._body_atoms

    def head_length(self) -> int:
        return len(self._head_atoms)

    def get_head_length(self) -> int:
        """Java-compatible alias for :meth:`head_length`."""
        return self.head_length()

    def head_atom(self, index: int) -> Atom:
        return self._head_atoms[index]

    def body_length(self) -> int:
        return len(self._body_atoms)

    def get_body_length(self) -> int:
        """Java-compatible alias for :meth:`body_length`."""
        return self.body_length()

    def body_atom(self, index: int) -> Atom:
        return self._body_atoms[index]

    def get_body_atom(self, index: int) -> Atom:
        """Java-compatible alias for :meth:`body_atom`."""
        return self.body_atom(index)

    def get_body_atoms(self) -> tuple[Atom, ...]:
        """Java-compatible alias for :attr:`body_atoms`."""
        return self._body_atoms

    def get_head_atoms(self) -> tuple[Atom, ...]:
        """Java-compatible alias for :attr:`head_atoms`."""
        return self._head_atoms

    # -- clause classification methods (ported from Java) -------------------

    def is_general_concept_inclusion(self) -> bool:
        """Check if this clause represents a GCI."""
        if self.head_length() == 0:
            if (
                self.body_length() == 2
                and self._body_atoms[0].arity() == 2
                and self._body_atoms[1].arity() == 2
            ):
                return False
            for body_atom in self._body_atoms:
                if body_atom.arity() != 1 or not isinstance(
                    body_atom.predicate, AtomicDataRange
                ):
                    return True
        for head_atom in self._head_atoms:
            pred = head_atom.predicate
            if isinstance(pred, AtLeast):
                return True
            if isinstance(pred, LiteralConcept):
                return True
            if isinstance(pred, AnnotatedEquality):
                return True
            if pred is NodeIDLessEqualThan.INSTANCE:
                return True
            if isinstance(pred, NodeIDsAscendingOrEqual):
                return True
            if isinstance(pred, DatatypeRestriction):
                return True
            if isinstance(pred, Equality):
                for body_atom in self._body_atoms:
                    if (
                        body_atom.arity() == 1
                        and isinstance(body_atom.predicate, AtomicConcept)
                        and body_atom.predicate is AtomicConcept.INTERNAL_NAMED
                    ):
                        return False
            if isinstance(pred, DataRange):
                for body_atom in self._body_atoms:
                    if body_atom.arity() == 2:
                        return True
                return False
            if isinstance(pred, Role):
                return False
        return False

    def is_atomic_concept_inclusion(self) -> bool:
        """Check if this is A(X) -> B(X)."""
        if self.body_length() == 1 and self.head_length() == 1:
            body = self._body_atoms[0]
            head = self._head_atoms[0]
            if (
                body.arity() == 1
                and head.arity() == 1
                and isinstance(body.predicate, AtomicConcept)
                and isinstance(head.predicate, AtomicConcept)
            ):
                arg = body.argument(0)
                return isinstance(arg, Variable) and arg == head.argument(0)
        return False

    def is_atomic_role_inclusion(self) -> bool:
        """Check if this is R(X,Y) -> S(X,Y)."""
        if self.body_length() == 1 and self.head_length() == 1:
            body = self._body_atoms[0]
            head = self._head_atoms[0]
            if (
                body.arity() == 2
                and head.arity() == 2
                and isinstance(body.predicate, AtomicRole)
                and isinstance(head.predicate, AtomicRole)
            ):
                arg0 = body.argument(0)
                arg1 = body.argument(1)
                return (
                    isinstance(arg0, Variable)
                    and isinstance(arg1, Variable)
                    and arg0 != arg1
                    and arg0 == head.argument(0)
                    and arg1 == head.argument(1)
                )
        return False

    def is_atomic_role_inverse_inclusion(self) -> bool:
        """Check if this is R(X,Y) -> S(Y,X) (inverse role inclusion)."""
        if self.body_length() == 1 and self.head_length() == 1:
            body = self._body_atoms[0]
            head = self._head_atoms[0]
            if (
                body.arity() == 2
                and head.arity() == 2
                and isinstance(body.predicate, AtomicRole)
                and isinstance(head.predicate, AtomicRole)
            ):
                arg0 = body.argument(0)
                arg1 = body.argument(1)
                return (
                    isinstance(arg0, Variable)
                    and isinstance(arg1, Variable)
                    and arg0 != arg1
                    and arg0 == head.argument(1)
                    and arg1 == head.argument(0)
                )
        return False

    def is_functionality_axiom(self) -> bool:
        """Check if this is a functionality axiom (at-most-1 restriction)."""
        # R(X,Y1) ∧ R(X,Y2) → Y1 == Y2
        if self.head_length() == 1 and self.body_length() == 2:
            head = self._head_atoms[0]
            if head.predicate is Equality.INSTANCE:
                body0 = self._body_atoms[0]
                body1 = self._body_atoms[1]
                if (
                    isinstance(body0.predicate, AtomicRole)
                    and isinstance(body1.predicate, AtomicRole)
                    and body0.predicate == body1.predicate
                ):
                    # Same first argument, different second arguments
                    if (body0.argument(0) == body1.argument(0)
                            and body0.argument(1) != body1.argument(1)
                            and head.argument(0) == body0.argument(1)
                            and head.argument(1) == body1.argument(1)):
                        return True
        return False

    def is_inverse_functionality_axiom(self) -> bool:
        """Check if this is an inverse functionality axiom."""
        # R(Y1,X) ∧ R(Y2,X) → Y1 == Y2
        if self.head_length() == 1 and self.body_length() == 2:
            head = self._head_atoms[0]
            if head.predicate is Equality.INSTANCE:
                body0 = self._body_atoms[0]
                body1 = self._body_atoms[1]
                if (
                    isinstance(body0.predicate, AtomicRole)
                    and isinstance(body1.predicate, AtomicRole)
                    and body0.predicate == body1.predicate
                ):
                    if (body0.argument(1) == body1.argument(1)
                            and body0.argument(0) != body1.argument(0)
                            and head.argument(0) == body0.argument(0)
                            and head.argument(1) == body1.argument(0)):
                        return True
        return False

    def get_head_atom(self, index: int) -> Atom:
        """Java-compatible alias for :meth:`head_atom`."""
        return self.head_atom(index)

    def get_changed_dl_clause(
        self,
        new_head_atoms: list[Atom] | None,
        new_body_atoms: list[Atom],
    ) -> DLClause:
        """Create a new DL clause with the given body atoms (and optionally new head atoms).

        Java-compatible method for creating reordered/cloned clauses.
        """
        head = tuple(new_head_atoms) if new_head_atoms is not None else self._head_atoms
        return DLClause.create(head, tuple(new_body_atoms))

    def __str__(self) -> str:
        head = " v ".join(str(a) for a in self._head_atoms) if self._head_atoms else "⊥"
        body = ", ".join(str(a) for a in self._body_atoms) if self._body_atoms else "⊤"
        return f"{head} :- {body}"

    def __repr__(self) -> str:
        return f"DLClause(head={self._head_atoms}, body={self._body_atoms})"

    def __hash__(self) -> int:
        h = 0
        for a in self._body_atoms:
            h += hash(a)
        for a in self._head_atoms:
            h += hash(a)
        return h

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DLClause):
            return (
                self._head_atoms == other._head_atoms
                and self._body_atoms == other._body_atoms
            )
        return False

    @classmethod
    def create(cls, head_atoms: tuple[Atom, ...], body_atoms: tuple[Atom, ...]) -> DLClause:
        return _interner.intern(cls(head_atoms, body_atoms))

    def get_safe_version(self, safe_making_predicate: DLPredicate) -> DLClause:
        """
        Return a "safe" version of this clause where all "unsafe" variables
        (those appearing only in the head, not in the body) are constrained
        by adding a body atom with the given safe-making predicate.

        This replaces tautological concepts (Thing -> always true, Nothing
        -> always false) by ensuring every head-only variable appears in a
        body atom like Thing(X), making the clause safe for evaluation.
        """
        variables: set[Variable] = set()
        # Collect all variables that occur in the head
        for atom in self._head_atoms:
            for i in range(atom.arity()):
                arg = atom.argument(i)
                if isinstance(arg, Variable):
                    variables.add(arg)
        # Remove those that also appear in the body
        for atom in self._body_atoms:
            for i in range(atom.arity()):
                arg = atom.argument(i)
                if isinstance(arg, Variable):
                    variables.discard(arg)
        # If clause is empty, add X as unsafe
        if not self._head_atoms and not self._body_atoms:
            variables.add(Variable.create("X"))
        # If no unsafe variables, return self
        if not variables:
            return self
        # Add body atoms for each unsafe variable
        new_body_atoms: list[Atom] = list(self._body_atoms)
        for variable in variables:
            new_body_atoms.append(Atom.create(safe_making_predicate, variable))
        return DLClause.create(self._head_atoms, tuple(new_body_atoms))


# ---------------------------------------------------------------------------
# DataRange hierarchy
# ---------------------------------------------------------------------------

class DataRange(ABC):
    """Base class for data ranges in DL clauses."""

    __slots__ = ()

    @abstractmethod
    def is_always_true(self) -> bool: ...

    @abstractmethod
    def is_always_false(self) -> bool: ...

    def arity(self) -> int:
        return 1

    def accept(self, visitor: Any) -> None:
        """Dispatch to the appropriate visitor method on *visitor*."""
        if isinstance(self, DatatypeRestriction):
            visitor.visit_datatype_restriction(self)
        elif isinstance(self, InternalDatatype):
            visitor.visit_internal_datatype(self)
        elif isinstance(self, ConstantEnumeration):
            visitor.visit_constant_enumeration(self)
        else:
            visitor.visit_other_data_range(self)

    def __str__(self) -> str:
        return str(self)


class AtomicDataRange(DataRange):
    """An atomic data range (datatype URI)."""

    __slots__ = ("_datatype_iri",)

    def __init__(self, datatype_iri: str) -> None:
        self._datatype_iri = datatype_iri

    @property
    def datatype_iri(self) -> str:
        return self._datatype_iri

    def is_always_true(self) -> bool:
        return False

    def is_always_false(self) -> bool:
        return False

    def __str__(self) -> str:
        return Prefixes.STANDARD.abbreviate_iri(self._datatype_iri)

    def __repr__(self) -> str:
        return f"AtomicDataRange({self._datatype_iri!r})"

    def __hash__(self) -> int:
        return hash(self._datatype_iri)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AtomicDataRange):
            return self._datatype_iri == other._datatype_iri
        return False

    @staticmethod
    def create(datatype_iri: str) -> AtomicDataRange:
        return _interner.intern(AtomicDataRange(datatype_iri))


class AtomicNegationDataRange(DataRange):
    """Negation of an atomic data range."""

    __slots__ = ("_negated",)

    def __init__(self, negated: AtomicDataRange) -> None:
        self._negated = negated

    @property
    def negated(self) -> AtomicDataRange:
        return self._negated

    @staticmethod
    def create(negated: AtomicDataRange) -> AtomicNegationDataRange:
        return _interner.intern(AtomicNegationDataRange(negated))

    def is_always_true(self) -> bool:
        return False

    def is_always_false(self) -> bool:
        return False

    def __str__(self) -> str:
        return f"¬{self._negated}"

    def __repr__(self) -> str:
        return f"AtomicNegationDataRange({self._negated!r})"

    def __hash__(self) -> int:
        return -hash(self._negated)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AtomicNegationDataRange):
            return self._negated == other._negated
        return False


class ConstantEnumeration(AtomicDataRange):
    """A data range consisting of a given set of constants."""

    __slots__ = ("_constants",)

    def __init__(self, constants: tuple[Constant, ...]) -> None:
        super().__init__("")  # placeholder -- arity handled by constants
        self._constants = constants

    @property
    def constants(self) -> tuple[Constant, ...]:
        return self._constants

    def get_number_of_constants(self) -> int:
        return len(self._constants)

    def get_constant(self, index: int) -> Constant:
        return self._constants[index]

    def get_negation(self) -> AtomicNegationDataRange:
        return AtomicNegationDataRange.create(self)

    def is_always_true(self) -> bool:
        return False

    def is_always_false(self) -> bool:
        return len(self._constants) == 0

    def __str__(self) -> str:
        parts = " ".join(str(c) for c in self._constants)
        return f"{{ {parts} }}"

    def __repr__(self) -> str:
        return f"ConstantEnumeration({self._constants!r})"

    def __hash__(self) -> int:
        return hash(self._constants)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ConstantEnumeration):
            return self._constants == other._constants
        return False

    @classmethod
    def create(cls, constants: list[Constant] | tuple[Constant, ...]) -> ConstantEnumeration:  # type: ignore[override]
        if isinstance(constants, list):
            constants = tuple(constants)
        return _interner.intern(cls(constants))


# ===========================================================================
# Remaining model classes (referenced by DLClause.is_general_concept_inclusion)
# ===========================================================================

# --- ExistentialConcept ---

class ExistentialConcept(Concept):
    """Marker base class for existential concepts."""
    __slots__ = ()


# --- AtLeast ---

class AtLeast(ExistentialConcept):
    """Abstract base for at-least restrictions."""
    __slots__ = ("_number", "_on_role")

    def __init__(self, number: int, on_role: Role) -> None:
        self._number = number
        self._on_role = on_role

    @property
    def number(self) -> int:
        return self._number

    @property
    def on_role(self) -> Role:
        return self._on_role

    def arity(self) -> int:
        return 1


    def is_always_true(self) -> bool:
        return False


class AtLeastConcept(AtLeast):
    """≥ n R.C"""
    __slots__ = ("_to_concept",)

    def __init__(self, number: int, on_role: Role, to_concept: LiteralConcept) -> None:
        super().__init__(number, on_role)
        self._to_concept = to_concept

    @property
    def to_concept(self) -> LiteralConcept:
        return self._to_concept

    def is_always_false(self) -> bool:
        return self._to_concept.is_always_false()

    def __str__(self) -> str:
        return f"atLeast({self._number} {self._on_role} {self._to_concept})"

    def __hash__(self) -> int:
        return (self._number * 7 + hash(self._on_role)) * 7 + hash(self._to_concept)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AtLeastConcept):
            return (self._number == other._number and self._on_role == other._on_role
                    and self._to_concept == other._to_concept)
        return False

    @classmethod
    def create(cls, number: int, on_role: Role, to_concept: LiteralConcept) -> AtLeastConcept:
        return _interner.intern(cls(number, on_role, to_concept))


class AtLeastDataRange(AtLeast):
    """≥ n R.DR"""
    __slots__ = ("_to_data_range",)

    def __init__(self, number: int, on_role: Role, to_data_range: DataRange) -> None:
        super().__init__(number, on_role)
        self._to_data_range = to_data_range

    @property
    def to_data_range(self) -> DataRange:
        return self._to_data_range

    def is_always_false(self) -> bool:
        return self._to_data_range.is_always_false()

    def __hash__(self) -> int:
        return (self._number * 7 + hash(self._on_role)) * 7 + hash(self._to_data_range)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AtLeastDataRange):
            return (self._number == other._number and self._on_role == other._on_role
                    and self._to_data_range == other._to_data_range)
        return False

    @classmethod
    def create(cls, number: int, on_role: Role, to_data_range: DataRange) -> AtLeastDataRange:
        return _interner.intern(cls(number, on_role, to_data_range))


class AtMostConcept(Concept):
    """≤ n R.C  (at-most cardinality restriction)."""
    __slots__ = ("_number", "_on_role", "_to_concept")

    def __init__(self, number: int, on_role: Role, to_concept: LiteralConcept) -> None:
        self._number = number
        self._on_role = on_role
        self._to_concept = to_concept

    @property
    def number(self) -> int:
        return self._number

    @property
    def on_role(self) -> Role:
        return self._on_role

    @property
    def to_concept(self) -> LiteralConcept:
        return self._to_concept

    def is_always_false(self) -> bool:
        return False

    def is_always_true(self) -> bool:
        return False

    def accept(self, visitor: Any) -> None:
        visit = getattr(visitor, "visit_at_most_concept", None)
        if visit is None:
            raise AttributeError(
                f"{type(visitor).__name__} has no visit_at_most_concept()"
            )
        visit(self)

    def __str__(self) -> str:
        return f"atMost({self._number} {self._on_role} {self._to_concept})"

    def __hash__(self) -> int:
        return (self._number * 13 + hash(self._on_role)) * 13 + hash(self._to_concept)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AtMostConcept):
            return (self._number == other._number and self._on_role == other._on_role
                    and self._to_concept == other._to_concept)
        return False

    @classmethod
    def create(cls, number: int, on_role: Role, to_concept: LiteralConcept) -> AtMostConcept:
        return _interner.intern(cls(number, on_role, to_concept))


# --- ExistsDescriptionGraph ---

class ExistsDescriptionGraph(ExistentialConcept):
    """Existential concept from a description graph."""
    __slots__ = ("_description_graph", "_vertex")

    def __init__(self, description_graph: DescriptionGraph, vertex: int) -> None:
        self._description_graph = description_graph
        self._vertex = vertex

    @property
    def description_graph(self) -> DescriptionGraph:
        return self._description_graph

    @property
    def vertex(self) -> int:
        return self._vertex

    def arity(self) -> int:
        return 1


    def is_always_true(self) -> bool:
        return False

    def is_always_false(self) -> bool:
        return False

    def __str__(self) -> str:
        return f"existsDG({self._description_graph},{self._vertex})"

    def __hash__(self) -> int:
        return hash(self._description_graph) * 31 + self._vertex

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ExistsDescriptionGraph):
            return (self._description_graph == other._description_graph
                    and self._vertex == other._vertex)
        return False

    @classmethod
    def create(cls, description_graph: DescriptionGraph, vertex: int) -> ExistsDescriptionGraph:
        return _interner.intern(cls(description_graph, vertex))


# --- AnnotatedEquality ---

class AnnotatedEquality:
    """Annotated equality for at-most restrictions."""
    __slots__ = ("_cardinality", "_on_role", "_to_concept")

    def __init__(self, cardinality: int, on_role: Role, to_concept: LiteralConcept) -> None:
        self._cardinality = cardinality
        self._on_role = on_role
        self._to_concept = to_concept

    @property
    def cardinality(self) -> int:
        return self._cardinality

    @property
    def on_role(self) -> Role:
        return self._on_role

    @property
    def to_concept(self) -> LiteralConcept:
        return self._to_concept

    def arity(self) -> int:
        return 3


    def __str__(self) -> str:
        return f"==@atMost({self._cardinality} {self._on_role} {self._to_concept})"

    def __hash__(self) -> int:
        return self._cardinality + hash(self._on_role) + hash(self._to_concept)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AnnotatedEquality):
            return (self._cardinality == other._cardinality
                    and self._on_role == other._on_role
                    and self._to_concept == other._to_concept)
        return False

    @classmethod
    def create(cls, cardinality: int, on_role: Role, to_concept: LiteralConcept) -> AnnotatedEquality:
        return _interner.intern(cls(cardinality, on_role, to_concept))


# --- NodeIDLessEqualThan ---

class NodeIDLessEqualThan:
    """Built-in predicate for node ordering in at-most translation."""
    __slots__ = ()
    INSTANCE: ClassVar[NodeIDLessEqualThan]

    def arity(self) -> int:
        return 2


    def __str__(self) -> str:
        return "<="

    def __hash__(self) -> int:
        return 10

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NodeIDLessEqualThan)

    def equals(self, other: object) -> bool:
        """Java-compatible equality check."""
        return self.__eq__(other)

    @classmethod
    def create(cls) -> NodeIDLessEqualThan:
        if cls.INSTANCE is None:
            cls.INSTANCE = cls()
        return cls.INSTANCE

NodeIDLessEqualThan.INSTANCE = NodeIDLessEqualThan()


# --- NodeIDsAscendingOrEqual ---

class NodeIDsAscendingOrEqual:
    """Predicate: node IDs are strictly ascending or all equal."""
    __slots__ = ("_arity",)

    def __init__(self, arity: int) -> None:
        self._arity = arity

    def arity(self) -> int:
        return self._arity


    def __str__(self) -> str:
        return "NodeIDsAscendingOrEqual"

    def __hash__(self) -> int:
        return self._arity

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NodeIDsAscendingOrEqual) and self._arity == other._arity

    def equals(self, other: object) -> bool:
        """Java-compatible equality check."""
        return self.__eq__(other)

    @classmethod
    def create(cls, arity: int) -> NodeIDsAscendingOrEqual:
        return _interner.intern(cls(arity))


# --- DatatypeRestriction ---

class DatatypeRestriction(AtomicDataRange):
    """Data range with datatype URI and facet restrictions."""
    __slots__ = ("_datatype_iri", "_facet_uris", "_facet_values")

    NO_FACET_URIS: ClassVar[tuple[str, ...]] = ()
    NO_FACET_VALUES: ClassVar[tuple[Constant, ...]] = ()

    def __init__(self, datatype_iri: str, facet_uris: tuple[str, ...],
                 facet_values: tuple[Constant, ...]) -> None:
        # Note: we don't call super().__init__ because AtomicDataRange also
        # stores _datatype_iri.  We keep our own copy for facet access.
        self._datatype_iri = datatype_iri
        self._facet_uris = facet_uris
        self._facet_values = facet_values

    @property
    def datatype_iri(self) -> str:
        return self._datatype_iri

    def number_of_facet_restrictions(self) -> int:
        return len(self._facet_uris)

    def facet_uri(self, index: int) -> str:
        return self._facet_uris[index]

    def facet_value(self, index: int) -> Constant:
        return self._facet_values[index]

    def is_always_true(self) -> bool:
        return False

    def is_always_false(self) -> bool:
        return False

    def __str__(self) -> str:
        result = Prefixes.STANDARD.abbreviate_iri(self._datatype_iri)
        if self._facet_uris:
            parts = []
            for furi, fval in zip(self._facet_uris, self._facet_values, strict=False):
                parts.append(f"{Prefixes.STANDARD.abbreviate_iri(furi)}={fval}")
            result += "[" + ",".join(parts) + "]"
        return result

    def __hash__(self) -> int:
        h = hash(self._datatype_iri)
        for furi, fval in zip(self._facet_uris, self._facet_values, strict=False):
            h += hash(furi) + hash(fval)
        return h

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DatatypeRestriction):
            if self._datatype_iri != other._datatype_iri:
                return False
            if len(self._facet_uris) != len(other._facet_uris):
                return False
            for furi, fval in zip(self._facet_uris, self._facet_values, strict=False):
                if not self._facet_in(other, furi, fval):
                    return False
            return True
        return False

    @staticmethod
    def _facet_in(restriction: DatatypeRestriction, uri: str, val: Constant) -> bool:
        for u, v in zip(restriction._facet_uris, restriction._facet_values, strict=False):
            if u == uri and v == val:
                return True
        return False

    def get_negation(self) -> AtomicNegationDataRange:
        """Return the negation of this datatype restriction."""
        return AtomicNegationDataRange.create(self)

    @classmethod
    def create(  # type: ignore[override]
        cls, datatype_iri: str, facet_uris: tuple[str, ...],
        facet_values: tuple[Constant, ...],
    ) -> DatatypeRestriction:
        return _interner.intern(cls(datatype_iri, facet_uris, facet_values))


# --- InternalDatatype ---

class InternalDatatype(AtomicDataRange):
    """Internal datatype for DL clauses (ignored by datatype manager)."""
    __slots__ = ("_iri",)
    RDFS_LITERAL_IRI = "http://www.w3.org/2000/01/rdf-schema#Literal"
    RDFS_LITERAL: ClassVar[InternalDatatype]

    def __init__(self, iri: str) -> None:
        self._iri = iri

    @property
    def iri(self) -> str:
        return self._iri

    def arity(self) -> int:
        return 1

    def is_always_true(self) -> bool:
        return self is self.RDFS_LITERAL

    def is_always_false(self) -> bool:
        return False

    def get_negation(self) -> AtomicNegationDataRange:
        """Return the negation of this datatype."""
        return AtomicNegationDataRange.create(self)

    def is_internal_datatype(self) -> bool:
        return True

    def __str__(self) -> str:
        return Prefixes.STANDARD.abbreviate_iri(self._iri)

    def __hash__(self) -> int:
        return hash(self._iri)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, InternalDatatype) and self._iri == other._iri

    @classmethod
    def create(cls, uri: str) -> InternalDatatype:
        return _interner.intern(cls(uri))

InternalDatatype.RDFS_LITERAL = InternalDatatype.create(InternalDatatype.RDFS_LITERAL_IRI)


# --- LiteralDataRange (semantic alias for DataRange in Java hierarchy) ---

class LiteralDataRange(DataRange):
    """A literal data range — atomic or negated atomic. Semantic alias."""
    __slots__ = ()


# --- DescriptionGraph ---

class DescriptionGraphEdge:
    """Edge in a description graph."""
    __slots__ = ("_atomic_role", "_from_vertex", "_to_vertex")

    def __init__(self, atomic_role: AtomicRole, from_vertex: int, to_vertex: int) -> None:
        self._atomic_role = atomic_role
        self._from_vertex = from_vertex
        self._to_vertex = to_vertex

    @property
    def atomic_role(self) -> AtomicRole:
        return self._atomic_role

    @property
    def from_vertex(self) -> int:
        return self._from_vertex

    @property
    def to_vertex(self) -> int:
        return self._to_vertex

    def __hash__(self) -> int:
        return self._from_vertex + 7 * self._to_vertex + 11 * hash(self._atomic_role)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DescriptionGraphEdge):
            return (self._atomic_role == other._atomic_role
                    and self._from_vertex == other._from_vertex
                    and self._to_vertex == other._to_vertex)
        return False


class DescriptionGraph:
    """Description graph for existential restrictions."""
    __slots__ = ("_name", "_concepts_by_vertex", "_edges", "_start_concepts")

    def __init__(self, name: str, concepts_by_vertex: tuple[AtomicConcept, ...],
                 edges: tuple[DescriptionGraphEdge, ...],
                 start_concepts: frozenset[AtomicConcept]) -> None:
        self._name = name
        self._concepts_by_vertex = concepts_by_vertex
        self._edges = edges
        self._start_concepts = start_concepts

    @property
    def name(self) -> str:
        return self._name

    def arity(self) -> int:
        return len(self._concepts_by_vertex)

    def atomic_concept_for_vertex(self, vertex: int) -> AtomicConcept:
        return self._concepts_by_vertex[vertex]

    def number_of_vertices(self) -> int:
        return len(self._concepts_by_vertex)

    def number_of_edges(self) -> int:
        return len(self._edges)

    def edge(self, index: int) -> DescriptionGraphEdge:
        return self._edges[index]

    @property
    def start_concepts(self) -> frozenset[AtomicConcept]:
        return self._start_concepts

    def produce_start_dl_clauses(self, result: set[DLClause]) -> None:
        x = Variable.create("X")
        for sc in self._start_concepts:
            antecedent = (Atom.create(sc, x),)
            consequent = [
                Atom.create(ExistsDescriptionGraph.create(self, v), x)
                for v, c in enumerate(self._concepts_by_vertex) if c == sc
            ]
            result.add(DLClause.create(tuple(consequent), antecedent))

    def __str__(self) -> str:
        return Prefixes.STANDARD.abbreviate_iri(self._name)

    def __repr__(self) -> str:
        return f"DescriptionGraph({self._name!r}, {self.number_of_vertices()}v, {self.number_of_edges()}e)"


# --- DLOntology ---

class DLOntology:
    """
    A DL ontology: set of DL clauses, facts, and metadata.
    Core data structure for the tableau reasoner.
    """
    __slots__ = (
        "_ontology_iri", "_dl_clauses", "_positive_facts", "_negative_facts",
        "_has_inverse_roles", "_has_at_most", "_has_nominals", "_has_datatypes",
        "_is_horn", "_all_concepts", "_all_individuals", "_all_obj_roles",
        "_all_data_roles", "_all_desc_graphs", "_data_prop_assertions",
    )

    def __init__(
        self,
        ontology_iri: str | None = None,
        dl_clauses: frozenset[DLClause] = frozenset(),
        positive_facts: frozenset[Atom] = frozenset(),
        negative_facts: frozenset[Atom] = frozenset(),
        has_inverse_roles: bool | None = None,
        has_nominals: bool | None = None,
    ) -> None:
        self._ontology_iri = ontology_iri
        self._dl_clauses = dl_clauses
        self._positive_facts = positive_facts
        self._negative_facts = negative_facts

        # Collect entities from clauses and facts
        self._all_concepts = self._collect_concepts(dl_clauses, positive_facts, negative_facts)
        self._all_individuals = self._collect_individuals(dl_clauses, positive_facts, negative_facts)
        self._all_obj_roles, self._all_data_roles = self._collect_roles(dl_clauses, positive_facts, negative_facts)
        # Detect expressivity from the clausal form; OR in caller-supplied flags
        # (the clausifier sees inverses/nominals at the axiom level, before they may
        # be normalised away in the clauses, so its detection can only add coverage).
        self._has_inverse_roles = self._check_inverses(dl_clauses, positive_facts, negative_facts)
        if has_inverse_roles is not None:
            self._has_inverse_roles = self._has_inverse_roles or has_inverse_roles
        self._has_datatypes = self._check_datatypes(dl_clauses)
        self._is_horn = all(c.head_length() <= 1 for c in dl_clauses)
        self._has_at_most = False
        self._has_nominals = self._check_nominals(dl_clauses, positive_facts)
        if has_nominals is not None:
            self._has_nominals = self._has_nominals or has_nominals
        self._all_desc_graphs = self._collect_graphs(dl_clauses)
        self._data_prop_assertions: dict[AtomicRole, dict[Individual, set[Constant]]] = {}

    @property
    def ontology_iri(self) -> str | None:
        return self._ontology_iri

    @property
    def dl_clauses(self) -> frozenset[DLClause]:
        return self._dl_clauses

    @property
    def positive_facts(self) -> frozenset[Atom]:
        return self._positive_facts

    @property
    def negative_facts(self) -> frozenset[Atom]:
        return self._negative_facts

    @property
    def all_atomic_concepts(self) -> frozenset[AtomicConcept]:
        return self._all_concepts

    @property
    def all_individuals(self) -> frozenset[Individual]:
        return self._all_individuals

    def get_all_individuals(self) -> frozenset[Individual]:
        """Return all individuals (Java-compatible alias)."""
        return self._all_individuals

    def get_all_complex_object_roles(self) -> frozenset[Role]:
        """Return all complex object property roles (empty in current implementation)."""
        return frozenset()

    def get_all_atomic_object_roles(self) -> frozenset[AtomicRole]:
        """Return all atomic object property roles."""
        return self._all_obj_roles

    @property
    def all_description_graphs(self) -> frozenset[DescriptionGraph]:
        return self._all_desc_graphs

    def has_inverse_roles(self) -> bool:
        return self._has_inverse_roles

    def has_at_most_restrictions(self) -> bool:
        return self._has_at_most

    def has_nominals(self) -> bool:
        return self._has_nominals

    def has_datatypes(self) -> bool:
        return self._has_datatypes

    def is_horn(self) -> bool:
        return self._is_horn

    def contains_atomic_concept(self, c: AtomicConcept) -> bool:
        return c in self._all_concepts

    def contains_individual(self, i: Individual) -> bool:
        return i in self._all_individuals

    # -- collection helpers --------------------------------------------------

    @staticmethod
    def _atoms_from_clauses(clauses: frozenset[DLClause]) -> list[Atom]:
        atoms: list[Atom] = []
        for cl in clauses:
            atoms.extend(cl.head_atoms)
            atoms.extend(cl.body_atoms)
        return atoms

    @staticmethod
    def _collect_concepts(
        clauses: frozenset[DLClause],
        pos: frozenset[Atom],
        neg: frozenset[Atom],
    ) -> frozenset[AtomicConcept]:
        concepts: set[AtomicConcept] = set()
        for atom in DLOntology._atoms_from_clauses(clauses):
            if isinstance(atom.predicate, AtomicConcept):
                concepts.add(atom.predicate)
        for atom in pos | neg:
            if isinstance(atom.predicate, AtomicConcept):
                concepts.add(atom.predicate)
        return frozenset(sorted(concepts, key=lambda c: c.iri))

    @staticmethod
    def _collect_individuals(
        clauses: frozenset[DLClause],
        pos: frozenset[Atom],
        neg: frozenset[Atom],
    ) -> frozenset[Individual]:
        indivs: set[Individual] = set()
        for atom in DLOntology._atoms_from_clauses(clauses):
            for i in range(atom.arity()):
                arg = atom.argument(i)
                if isinstance(arg, Individual):
                    indivs.add(arg)
        for atom in pos | neg:
            for i in range(atom.arity()):
                arg = atom.argument(i)
                if isinstance(arg, Individual):
                    indivs.add(arg)
        return frozenset(sorted(indivs, key=lambda x: x.iri))

    @staticmethod
    def _collect_roles(
        clauses: frozenset[DLClause],
        pos: frozenset[Atom],
        neg: frozenset[Atom],
    ) -> tuple[frozenset[AtomicRole], frozenset[AtomicRole]]:
        obj: set[AtomicRole] = set()
        data: set[AtomicRole] = set()
        for atom in DLOntology._atoms_from_clauses(clauses):
            if isinstance(atom.predicate, AtomicRole):
                obj.add(atom.predicate)
        for atom in pos:
            if isinstance(atom.predicate, AtomicRole) and atom.predicate.arity() == 2:
                obj.add(atom.predicate)
        for atom in neg:
            if isinstance(atom.predicate, AtomicRole) and atom.predicate.arity() == 2:
                obj.add(atom.predicate)
        return frozenset(obj), frozenset(data)

    @staticmethod
    def _check_nominals(
        clauses: frozenset[DLClause],
        pos: frozenset[Atom],
    ) -> bool:
        for atom in DLOntology._atoms_from_clauses(clauses):
            if isinstance(atom.predicate, AtomicConcept) and atom.predicate.iri.startswith("internal:nom#"):
                return True
        for atom in pos:
            if isinstance(atom.predicate, AtomicConcept) and atom.predicate.iri.startswith("internal:nom#"):
                return True
        return False

    @staticmethod
    def _check_inverses(
        clauses: frozenset[DLClause],
        pos: frozenset[Atom],
        neg: frozenset[Atom],
    ) -> bool:
        for atom in DLOntology._atoms_from_clauses(clauses):
            if isinstance(atom.predicate, InverseRole):
                return True
        return False

    @staticmethod
    def _check_datatypes(clauses: frozenset[DLClause]) -> bool:
        for atom in DLOntology._atoms_from_clauses(clauses):
            if isinstance(atom.predicate, (AtomicDataRange, DatatypeRestriction, InternalDatatype)):
                return True
        return False

    @staticmethod
    def _collect_graphs(clauses: frozenset[DLClause]) -> frozenset[DescriptionGraph]:
        graphs: dict[str, DescriptionGraph] = {}
        for atom in DLOntology._atoms_from_clauses(clauses):
            if isinstance(atom.predicate, ExistsDescriptionGraph):
                dg = atom.predicate.description_graph
                graphs[dg.name] = dg
        return frozenset(graphs.values())

    def get_all_description_graphs(self) -> frozenset[DescriptionGraph]:
        """Return all description graphs referenced in this ontology's clauses."""
        return self._all_desc_graphs

    def get_dl_clauses(self) -> frozenset[DLClause]:
        """Return the DL clauses."""
        return self._dl_clauses

    def get_positive_facts(self) -> frozenset[Atom]:
        """Return the positive facts."""
        return self._positive_facts

    def get_negative_facts(self) -> frozenset[Atom]:
        """Return the negative facts."""
        return self._negative_facts

    def contains_object_role(self, role: AtomicRole) -> bool:
        """Check whether the ontology contains the given object role."""
        return role in self._all_obj_roles

    def has_unknown_datatype_restrictions(self) -> bool:
        """Check whether the ontology has unknown datatype restrictions."""
        return False

    def get_all_unknown_datatype_restrictions(self) -> frozenset[DatatypeRestriction]:
        """Return all unknown datatype restrictions (empty set by default)."""
        return frozenset()

    def __repr__(self) -> str:
        return (f"DLOntology({self._ontology_iri!r}, "
                f"{len(self._dl_clauses)} clauses, "
                f"{len(self._all_concepts)} concepts, "
                f"{len(self._all_individuals)} individuals)")
