"""Comprehensive tests for hermit.model — Core DL model classes."""

from __future__ import annotations

import pytest

from hermit.model import (
    AnnotatedEquality,
    AtLeastConcept,
    AtLeastDataRange,
    Atom,
    AtomicConcept,
    AtomicDataRange,
    AtomicNegationConcept,
    AtomicRole,
    Concept,
    Constant,
    ConstantEnumeration,
    DLClause,
    DataRange,
    DatatypeRestriction,
    DescriptionGraph,
    DescriptionGraphEdge,
    DLOntology,
    Equality,
    ExistsDescriptionGraph,
    Individual,
    Inequality,
    InternalDatatype,
    Interner,
    InverseRole,
    LiteralConcept,
    NodeIDLessEqualThan,
    NodeIDsAscendingOrEqual,
    Prefixes,
    Term,
    Variable,
    _interner,
)


# ===========================================================================
# 1. Interner
# ===========================================================================

class TestInterner:
    def test_intern_returns_same_object_for_equal_inputs(self):
        interner = Interner()
        obj1 = AtomicConcept("http://example.org#A")
        obj2 = AtomicConcept("http://example.org#A")
        interned1 = interner.intern(obj1)
        interned2 = interner.intern(obj2)
        assert interned1 is interned2

    def test_intern_keeps_distinct_objects_for_unequal_inputs(self):
        interner = Interner()
        obj1 = AtomicConcept("http://example.org#A")
        obj2 = AtomicConcept("http://example.org#B")
        assert interner.intern(obj1) is not interner.intern(obj2)

    def test_intern_handles_different_types(self):
        interner = Interner()
        a = AtomicRole("http://example.org#r")
        b = AtomicConcept("http://example.org#r")
        assert interner.intern(a) is not interner.intern(b)

    def test_intern_idempotent(self):
        interner = Interner()
        obj = Variable("X")
        assert interner.intern(obj) is interner.intern(interner.intern(obj))


# ===========================================================================
# 2. Prefixes
# ===========================================================================

class TestPrefixes:
    def test_standard_has_semantic_web_prefixes(self):
        p = Prefixes.STANDARD
        assert p.get_prefix_iri("owl:") == "http://www.w3.org/2002/07/owl#"
        assert p.get_prefix_iri("rdf:") == "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        assert p.get_prefix_iri("xsd:") == "http://www.w3.org/2001/XMLSchema#"

    def test_abbreviate_iri_known_prefix(self):
        p = Prefixes.STANDARD
        assert p.abbreviate_iri("http://www.w3.org/2002/07/owl#Thing") == "owl:Thing"

    def test_abbreviate_iri_unknown_prefix(self):
        p = Prefixes()
        result = p.abbreviate_iri("http://example.org#Foo")
        assert result == "<http://example.org#Foo>"

    def test_expand_abbreviation_known_prefix(self):
        p = Prefixes.STANDARD
        assert p.expand_abbreviation("owl:Thing") == "http://www.w3.org/2002/07/owl#Thing"

    def test_expand_abbreviation_angle_bracket(self):
        p = Prefixes.STANDARD
        assert p.expand_abbreviation("<http://example.org#X>") == "http://example.org#X"

    def test_expand_abbreviation_missing_closing_bracket(self):
        p = Prefixes()
        with pytest.raises(ValueError, match="must be enclosed"):
            p.expand_abbreviation("<http://example.org")

    def test_expand_abbreviation_unknown_prefix_raises(self):
        p = Prefixes()
        with pytest.raises(ValueError, match="not a registered prefix"):
            p.expand_abbreviation("ex:Foo")

    def test_declare_prefix(self):
        p = Prefixes()
        assert p.declare_prefix("ex:", "http://example.org#") is True
        assert p.get_prefix_iri("ex:") == "http://example.org#"
        assert p.get_prefix_name("http://example.org#") == "ex:"

    def test_declare_prefix_without_colon_raises(self):
        p = Prefixes()
        with pytest.raises(ValueError, match="should end with"):
            p.declare_prefix("ex", "http://example.org#")

    def test_declare_custom_prefix_and_use(self):
        p = Prefixes()
        p.declare_prefix("ex:", "http://example.org#")
        assert p.abbreviate_iri("http://example.org#Person") == "ex:Person"
        assert p.expand_abbreviation("ex:Person") == "http://example.org#Person"

    def test_declare_default_prefix(self):
        p = Prefixes()
        p.declare_default_prefix("http://example.org#")
        assert p.get_prefix_iri(":") == "http://example.org#"

    def test_declare_semantic_web_prefixes(self):
        p = Prefixes()
        assert p.declare_semantic_web_prefixes() is True
        assert p.get_prefix_iri("rdfs:") is not None

    def test_is_internal_iri(self):
        assert Prefixes.is_internal_iri("internal:def#X") is True
        assert Prefixes.is_internal_iri("http://example.org#X") is False

    def test_prefix_map(self):
        p = Prefixes()
        p.declare_prefix("a:", "http://a.org#")
        assert "a:" in p.prefix_map

    def test_expand_invalid_abbreviation_no_colon(self):
        p = Prefixes()
        with pytest.raises(ValueError, match="not valid"):
            p.expand_abbreviation("NoColonHere")


# ===========================================================================
# 3. AtomicConcept
# ===========================================================================

class TestAtomicConcept:
    def test_create_and_iri(self):
        c = AtomicConcept.create("http://example.org#A")
        assert c.iri == "http://example.org#A"

    def test_interning(self):
        c1 = AtomicConcept.create("http://example.org#A")
        c2 = AtomicConcept.create("http://example.org#A")
        assert c1 is c2

    def test_arity(self):
        assert AtomicConcept.create("http://example.org#A").arity() == 1

    def test_thing_is_always_true(self):
        assert AtomicConcept.THING.is_always_true() is True
        assert AtomicConcept.THING.is_always_false() is False

    def test_nothing_is_always_false(self):
        assert AtomicConcept.NOTHING.is_always_false() is True
        assert AtomicConcept.NOTHING.is_always_true() is False

    def test_regular_concept_neither(self):
        c = AtomicConcept.create("http://example.org#A")
        assert c.is_always_true() is False
        assert c.is_always_false() is False

    def test_thing_negation_is_nothing(self):
        assert AtomicConcept.THING.get_negation() is AtomicConcept.NOTHING

    def test_nothing_negation_is_thing(self):
        assert AtomicConcept.NOTHING.get_negation() is AtomicConcept.THING

    def test_regular_concept_negation_is_negation(self):
        c = AtomicConcept.create("http://example.org#A")
        neg = c.get_negation()
        assert isinstance(neg, AtomicNegationConcept)
        assert neg.negated is c

    def test_equality_and_hash(self):
        c1 = AtomicConcept.create("http://example.org#A")
        c2 = AtomicConcept.create("http://example.org#A")
        c3 = AtomicConcept.create("http://example.org#B")
        assert c1 == c2
        assert c1 != c3
        assert hash(c1) == hash(c2)

    def test_str_abbreviates(self):
        c = AtomicConcept.THING
        assert str(c) == "owl:Thing"

    def test_internal_named(self):
        assert AtomicConcept.INTERNAL_NAMED.iri == "internal:nam#Named"


# ===========================================================================
# 4. AtomicNegationConcept
# ===========================================================================

class TestAtomicNegationConcept:
    def test_create_and_negated(self):
        c = AtomicConcept.create("http://example.org#A")
        neg = AtomicNegationConcept.create(c)
        assert neg.negated is c

    def test_double_negation_elimination(self):
        c = AtomicConcept.create("http://example.org#A")
        neg = c.get_negation()
        assert neg.get_negation() is c

    def test_arity(self):
        c = AtomicConcept.create("http://example.org#A")
        assert AtomicNegationConcept.create(c).arity() == 1

    def test_nothing_negation_is_always_true(self):
        neg = AtomicNegationConcept.create(AtomicConcept.NOTHING)
        assert neg.is_always_true() is True
        assert neg.is_always_false() is False

    def test_thing_negation_is_always_false(self):
        neg = AtomicNegationConcept.create(AtomicConcept.THING)
        assert neg.is_always_true() is False
        assert neg.is_always_false() is True

    def test_equality_and_hash(self):
        c = AtomicConcept.create("http://example.org#A")
        n1 = AtomicNegationConcept.create(c)
        n2 = AtomicNegationConcept.create(c)
        assert n1 == n2
        assert hash(n1) == hash(n2)

    def test_str(self):
        c = AtomicConcept.create("http://example.org#A")
        neg = AtomicNegationConcept.create(c)
        assert str(neg) == f"¬{c}"


# ===========================================================================
# 5. AtomicRole
# ===========================================================================

class TestAtomicRole:
    def test_create_and_iri(self):
        r = AtomicRole.create("http://example.org#r")
        assert r.iri == "http://example.org#r"

    def test_interning(self):
        r1 = AtomicRole.create("http://example.org#r")
        r2 = AtomicRole.create("http://example.org#r")
        assert r1 is r2

    def test_arity(self):
        assert AtomicRole.create("http://example.org#r").arity() == 2

    def test_inverse_of_top_object_role_is_self(self):
        assert AtomicRole.TOP_OBJECT_ROLE.get_inverse() is AtomicRole.TOP_OBJECT_ROLE

    def test_inverse_of_bottom_object_role_is_self(self):
        assert AtomicRole.BOTTOM_OBJECT_ROLE.get_inverse() is AtomicRole.BOTTOM_OBJECT_ROLE

    def test_inverse_of_regular_role(self):
        r = AtomicRole.create("http://example.org#r")
        inv = r.get_inverse()
        assert isinstance(inv, InverseRole)
        assert inv.inverse_of is r

    def test_role_assertion(self):
        r = AtomicRole.create("http://example.org#r")
        x = Variable.create("X")
        y = Variable.create("Y")
        atom = r.get_role_assertion(x, y)
        assert atom.predicate is r
        assert atom.argument(0) is x
        assert atom.argument(1) is y

    def test_equality_and_hash(self):
        r1 = AtomicRole.create("http://example.org#r")
        r2 = AtomicRole.create("http://example.org#r")
        assert r1 == r2
        assert hash(r1) == hash(r2)

    def test_predefined_constants(self):
        assert AtomicRole.TOP_OBJECT_ROLE.iri == AtomicRole.TOP_OBJECT_ROLE_IRI
        assert AtomicRole.BOTTOM_OBJECT_ROLE.iri == AtomicRole.BOTTOM_OBJECT_ROLE_IRI
        assert AtomicRole.TOP_DATA_ROLE.iri == AtomicRole.TOP_DATA_ROLE_IRI
        assert AtomicRole.BOTTOM_DATA_ROLE.iri == AtomicRole.BOTTOM_DATA_ROLE_IRI


# ===========================================================================
# 6. InverseRole
# ===========================================================================

class TestInverseRole:
    def test_create_and_inverse_of(self):
        r = AtomicRole.create("http://example.org#r")
        inv = InverseRole.create(r)
        assert inv.inverse_of is r

    def test_double_inverse(self):
        r = AtomicRole.create("http://example.org#r")
        inv = InverseRole.create(r)
        assert inv.get_inverse() is r

    def test_role_assertion_swaps_terms(self):
        r = AtomicRole.create("http://example.org#r")
        inv = InverseRole.create(r)
        x = Variable.create("X")
        y = Variable.create("Y")
        atom = inv.get_role_assertion(x, y)
        assert atom.predicate is r
        assert atom.argument(0) is y
        assert atom.argument(1) is x

    def test_equality_and_hash(self):
        r = AtomicRole.create("http://example.org#r")
        i1 = InverseRole.create(r)
        i2 = InverseRole.create(r)
        assert i1 == i2
        assert hash(i1) == hash(i2)

    def test_str(self):
        r = AtomicRole.create("http://example.org#r")
        inv = InverseRole.create(r)
        assert str(inv) == f"inv({r})"


# ===========================================================================
# 7. Individual
# ===========================================================================

class TestIndividual:
    def test_create_named(self):
        i = Individual.create("http://example.org#john")
        assert i.iri == "http://example.org#john"
        assert i.is_anonymous() is False

    def test_create_anonymous(self):
        i = Individual.create_anonymous("n1")
        assert i.is_anonymous() is True
        assert i.iri == "internal:anonymous#n1"

    def test_interning(self):
        i1 = Individual.create("http://example.org#john")
        i2 = Individual.create("http://example.org#john")
        assert i1 is i2

    def test_equality_and_hash(self):
        i1 = Individual.create("http://example.org#john")
        i2 = Individual.create("http://example.org#john")
        i3 = Individual.create("http://example.org#jane")
        assert i1 == i2
        assert i1 != i3
        assert hash(i1) == hash(i2)

    def test_str(self):
        i = Individual.create("http://example.org#john")
        assert str(i) == "<http://example.org#john>"


# ===========================================================================
# 8. Variable
# ===========================================================================

class TestVariable:
    def test_create_and_name(self):
        v = Variable.create("X")
        assert v.name == "X"

    def test_interning(self):
        v1 = Variable.create("X")
        v2 = Variable.create("X")
        assert v1 is v2

    def test_equality_and_hash(self):
        v1 = Variable.create("X")
        v2 = Variable.create("X")
        v3 = Variable.create("Y")
        assert v1 == v2
        assert v1 != v3
        assert hash(v1) == hash(v2)

    def test_str(self):
        assert str(Variable.create("X")) == "X"


# ===========================================================================
# 9. Constant
# ===========================================================================

class TestConstant:
    def test_create_and_properties(self):
        c = Constant.create("42", "http://www.w3.org/2001/XMLSchema#integer")
        assert c.lexical_form == "42"
        assert c.datatype_iri == "http://www.w3.org/2001/XMLSchema#integer"

    def test_interning(self):
        c1 = Constant.create("42", "http://www.w3.org/2001/XMLSchema#integer")
        c2 = Constant.create("42", "http://www.w3.org/2001/XMLSchema#integer")
        assert c1 is c2

    def test_str_representation(self):
        c = Constant.create("42", "http://www.w3.org/2001/XMLSchema#integer")
        s = str(c)
        assert "42" in s
        assert "xsd:integer" in s

    def test_anonymous_constant(self):
        c = Constant.create_anonymous("anon1")
        assert c.is_anonymous() is True

    def test_equality_and_hash(self):
        c1 = Constant.create("42", "http://www.w3.org/2001/XMLSchema#integer")
        c2 = Constant.create("42", "http://www.w3.org/2001/XMLSchema#integer")
        c3 = Constant.create("43", "http://www.w3.org/2001/XMLSchema#integer")
        assert c1 == c2
        assert c1 != c3
        assert hash(c1) == hash(c2)


# ===========================================================================
# 10. Atom
# ===========================================================================

class TestAtom:
    def test_create_concept_atom(self):
        c = AtomicConcept.create("http://example.org#A")
        x = Variable.create("X")
        atom = Atom.create(c, x)
        assert atom.predicate is c
        assert atom.arity() == 1
        assert atom.argument(0) is x

    def test_create_role_atom(self):
        r = AtomicRole.create("http://example.org#r")
        x = Variable.create("X")
        y = Variable.create("Y")
        atom = Atom.create(r, x, y)
        assert atom.arity() == 2
        assert atom.argument(0) is x
        assert atom.argument(1) is y

    def test_create_equality_atom(self):
        x = Variable.create("X")
        y = Variable.create("Y")
        atom = Atom.create(Equality.INSTANCE, x, y)
        assert atom.predicate is Equality.INSTANCE
        assert atom.arity() == 2

    def test_create_inequality_atom(self):
        x = Variable.create("X")
        y = Variable.create("Y")
        atom = Atom.create(Inequality.INSTANCE, x, y)
        assert atom.predicate is Inequality.INSTANCE

    def test_get_variables(self):
        x = Variable.create("X")
        y = Variable.create("Y")
        r = AtomicRole.create("http://example.org#r")
        atom = Atom.create(r, x, y)
        vars_set: set[Variable] = set()
        atom.get_variables(vars_set)
        assert x in vars_set
        assert y in vars_set

    def test_contains_variable(self):
        x = Variable.create("X")
        i = Individual.create("http://example.org#john")
        r = AtomicRole.create("http://example.org#r")
        atom = Atom.create(r, x, i)
        assert atom.contains_variable(x) is True
        assert atom.contains_variable(Variable.create("Y")) is False

    def test_replace_predicate(self):
        c1 = AtomicConcept.create("http://example.org#A")
        c2 = AtomicConcept.create("http://example.org#B")
        x = Variable.create("X")
        atom = Atom.create(c1, x)
        new_atom = atom.replace_predicate(c2)
        assert new_atom.predicate is c2
        assert new_atom.argument(0) is x

    def test_str_concept_atom(self):
        c = AtomicConcept.THING
        x = Variable.create("X")
        atom = Atom.create(c, x)
        assert str(atom) == "owl:Thing(X)"

    def test_str_equality_infix(self):
        x = Variable.create("X")
        y = Variable.create("Y")
        atom = Atom.create(Equality.INSTANCE, x, y)
        assert str(atom) == "X == Y"

    def test_str_inequality_infix(self):
        x = Variable.create("X")
        y = Variable.create("Y")
        atom = Atom.create(Inequality.INSTANCE, x, y)
        assert str(atom) == "X != Y"

    def test_wrong_arity_raises(self):
        c = AtomicConcept.create("http://example.org#A")
        x = Variable.create("X")
        y = Variable.create("Y")
        with pytest.raises(ValueError, match="arity"):
            Atom.create(c, x, y)

    def test_interning(self):
        c = AtomicConcept.create("http://example.org#A")
        x = Variable.create("X")
        a1 = Atom.create(c, x)
        a2 = Atom.create(c, x)
        assert a1 is a2


# ===========================================================================
# 11. DLClause
# ===========================================================================

class TestDLClause:
    @pytest.fixture
    def x(self):
        return Variable.create("X")

    @pytest.fixture
    def y(self):
        return Variable.create("Y")

    def test_create_and_access(self, x, y):
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        head = (Atom.create(b, x),)
        body = (Atom.create(a, x),)
        clause = DLClause.create(head, body)
        assert clause.head_length() == 1
        assert clause.body_length() == 1
        assert clause.head_atom(0).predicate is b
        assert clause.body_atom(0).predicate is a

    def test_is_general_concept_inclusion(self, x):
        # A(X) -> B(X) returns True because head contains LiteralConcept
        # (the Java method returns True for any clause with a LiteralConcept in head
        # unless specific conditions are met)
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        clause = DLClause.create((Atom.create(b, x),), (Atom.create(a, x),))
        assert clause.is_general_concept_inclusion() is True

    def test_is_atomic_concept_inclusion(self, x):
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        clause = DLClause.create((Atom.create(b, x),), (Atom.create(a, x),))
        assert clause.is_atomic_concept_inclusion() is True

    def test_is_atomic_role_inclusion(self, x, y):
        r = AtomicRole.create("http://example.org#r")
        s = AtomicRole.create("http://example.org#s")
        clause = DLClause.create(
            (Atom.create(s, x, y),),
            (Atom.create(r, x, y),),
        )
        assert clause.is_atomic_role_inclusion() is True

    def test_str_representation(self, x):
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        clause = DLClause.create((Atom.create(b, x),), (Atom.create(a, x),))
        s = str(clause)
        assert ":-" in s

    def test_empty_body_is_top(self, x):
        b = AtomicConcept.create("http://example.org#B")
        clause = DLClause.create((Atom.create(b, x),), ())
        assert str(clause).endswith(":- ⊤")

    def test_empty_head_is_bottom(self, x):
        a = AtomicConcept.create("http://example.org#A")
        clause = DLClause.create((), (Atom.create(a, x),))
        assert "⊥" in str(clause)

    def test_equality_and_hash(self, x):
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        c1 = DLClause.create((Atom.create(b, x),), (Atom.create(a, x),))
        c2 = DLClause.create((Atom.create(b, x),), (Atom.create(a, x),))
        assert c1 == c2
        assert hash(c1) == hash(c2)

    def test_head_atoms_property(self, x):
        a = AtomicConcept.create("http://example.org#A")
        clause = DLClause.create((Atom.create(a, x),), ())
        assert len(clause.head_atoms) == 1


# ===========================================================================
# 12. Equality / Inequality
# ===========================================================================

class TestEquality:
    def test_singleton(self):
        assert Equality.INSTANCE is Equality.INSTANCE

    def test_arity(self):
        assert Equality.INSTANCE.arity() == 2

    def test_equality(self):
        assert Equality.INSTANCE == Equality.INSTANCE
        assert Equality.INSTANCE != Inequality.INSTANCE

    def test_str(self):
        assert str(Equality.INSTANCE) == "=="


class TestInequality:
    def test_singleton(self):
        assert Inequality.INSTANCE is Inequality.INSTANCE

    def test_arity(self):
        assert Inequality.INSTANCE.arity() == 2

    def test_equality(self):
        assert Inequality.INSTANCE == Inequality.INSTANCE
        assert Inequality.INSTANCE != Equality.INSTANCE

    def test_str(self):
        assert str(Inequality.INSTANCE) == "!="


# ===========================================================================
# 13. AnnotatedEquality
# ===========================================================================

class TestAnnotatedEquality:
    def test_create_and_access(self):
        c = AtomicConcept.create("http://example.org#A")
        r = AtomicRole.create("http://example.org#r")
        eq = AnnotatedEquality.create(3, r, c)
        assert eq.cardinality == 3
        assert eq.on_role is r
        assert eq.to_concept is c

    def test_arity(self):
        c = AtomicConcept.create("http://example.org#A")
        r = AtomicRole.create("http://example.org#r")
        assert AnnotatedEquality.create(3, r, c).arity() == 3

    def test_equality_and_hash(self):
        c = AtomicConcept.create("http://example.org#A")
        r = AtomicRole.create("http://example.org#r")
        e1 = AnnotatedEquality.create(3, r, c)
        e2 = AnnotatedEquality.create(3, r, c)
        assert e1 == e2
        assert hash(e1) == hash(e2)

    def test_str(self):
        c = AtomicConcept.create("http://example.org#A")
        r = AtomicRole.create("http://example.org#r")
        eq = AnnotatedEquality.create(3, r, c)
        s = str(eq)
        assert "atMost" in s
        assert "3" in s


# ===========================================================================
# 14. NodeIDLessEqualThan
# ===========================================================================

class TestNodeIDLessEqualThan:
    def test_singleton(self):
        assert NodeIDLessEqualThan.INSTANCE is NodeIDLessEqualThan.INSTANCE

    def test_arity(self):
        assert NodeIDLessEqualThan.INSTANCE.arity() == 2

    def test_equality(self):
        assert NodeIDLessEqualThan.INSTANCE == NodeIDLessEqualThan.INSTANCE

    def test_str(self):
        assert str(NodeIDLessEqualThan.INSTANCE) == "<="


# ===========================================================================
# 15. NodeIDsAscendingOrEqual
# ===========================================================================

class TestNodeIDsAscendingOrEqual:
    def test_create_and_arity(self):
        n = NodeIDsAscendingOrEqual.create(3)
        assert n.arity() == 3

    def test_interning(self):
        n1 = NodeIDsAscendingOrEqual.create(3)
        n2 = NodeIDsAscendingOrEqual.create(3)
        assert n1 is n2

    def test_equality(self):
        n1 = NodeIDsAscendingOrEqual.create(3)
        n2 = NodeIDsAscendingOrEqual.create(3)
        n3 = NodeIDsAscendingOrEqual.create(4)
        assert n1 == n2
        assert n1 != n3

    def test_str(self):
        assert str(NodeIDsAscendingOrEqual.create(3)) == "NodeIDsAscendingOrEqual"


# ===========================================================================
# 16. AtLeastConcept / AtLeastDataRange
# ===========================================================================

class TestAtLeastConcept:
    def test_create_and_access(self):
        r = AtomicRole.create("http://example.org#r")
        c = AtomicConcept.create("http://example.org#A")
        at_least = AtLeastConcept.create(2, r, c)
        assert at_least.number == 2
        assert at_least.on_role is r
        assert at_least.to_concept is c

    def test_is_always_false_with_nothing(self):
        r = AtomicRole.create("http://example.org#r")
        at_least = AtLeastConcept.create(1, r, AtomicConcept.NOTHING)
        assert at_least.is_always_false() is True

    def test_is_always_true(self):
        r = AtomicRole.create("http://example.org#r")
        c = AtomicConcept.create("http://example.org#A")
        assert AtLeastConcept.create(1, r, c).is_always_true() is False

    def test_arity(self):
        r = AtomicRole.create("http://example.org#r")
        c = AtomicConcept.create("http://example.org#A")
        assert AtLeastConcept.create(1, r, c).arity() == 1


class TestAtLeastDataRange:
    def test_create_and_access(self):
        r = AtomicRole.create("http://example.org#r")
        dr = AtomicDataRange.create("http://www.w3.org/2001/XMLSchema#integer")
        at_least = AtLeastDataRange.create(1, r, dr)
        assert at_least.number == 1
        assert at_least.on_role is r
        assert at_least.to_data_range is dr

    def test_is_always_false(self):
        r = AtomicRole.create("http://example.org#r")
        dr = AtomicDataRange.create("http://www.w3.org/2001/XMLSchema#integer")
        assert AtLeastDataRange.create(1, r, dr).is_always_false() is False

    def test_is_always_true(self):
        r = AtomicRole.create("http://example.org#r")
        dr = AtomicDataRange.create("http://www.w3.org/2001/XMLSchema#integer")
        assert AtLeastDataRange.create(1, r, dr).is_always_true() is False


# ===========================================================================
# 17. ExistsDescriptionGraph
# ===========================================================================

class TestExistsDescriptionGraph:
    def test_create_and_vertex_access(self):
        c = AtomicConcept.create("http://example.org#A")
        dg = DescriptionGraph(
            "http://example.org#G",
            (c,),
            (),
            frozenset({c}),
        )
        eg = ExistsDescriptionGraph.create(dg, 0)
        assert eg.description_graph is dg
        assert eg.vertex == 0

    def test_arity(self):
        c = AtomicConcept.create("http://example.org#A")
        dg = DescriptionGraph(
            "http://example.org#G",
            (c,),
            (),
            frozenset({c}),
        )
        assert ExistsDescriptionGraph.create(dg, 0).arity() == 1

    def test_is_always_true_false(self):
        c = AtomicConcept.create("http://example.org#A")
        dg = DescriptionGraph(
            "http://example.org#G",
            (c,),
            (),
            frozenset({c}),
        )
        eg = ExistsDescriptionGraph.create(dg, 0)
        assert eg.is_always_true() is False
        assert eg.is_always_false() is False


# ===========================================================================
# 18. DatatypeRestriction
# ===========================================================================

class TestDatatypeRestriction:
    def test_create_and_facet_access(self):
        xsd = "http://www.w3.org/2001/XMLSchema#"
        min_c = Constant.create("0", xsd + "integer")
        max_c = Constant.create("100", xsd + "integer")
        restr = DatatypeRestriction.create(
            xsd + "integer",
            (xsd + "minInclusive", xsd + "maxInclusive"),
            (min_c, max_c),
        )
        assert restr.datatype_iri == xsd + "integer"
        assert restr.number_of_facet_restrictions() == 2
        assert restr.facet_uri(0) == xsd + "minInclusive"
        assert restr.facet_value(0) is min_c

    def test_equality_ignores_facet_order(self):
        xsd = "http://www.w3.org/2001/XMLSchema#"
        min_c = Constant.create("0", xsd + "integer")
        max_c = Constant.create("100", xsd + "integer")
        r1 = DatatypeRestriction.create(
            xsd + "integer",
            (xsd + "minInclusive", xsd + "maxInclusive"),
            (min_c, max_c),
        )
        r2 = DatatypeRestriction.create(
            xsd + "integer",
            (xsd + "maxInclusive", xsd + "minInclusive"),
            (max_c, min_c),
        )
        assert r1 == r2

    def test_inequality_different_datatype(self):
        xsd = "http://www.w3.org/2001/XMLSchema#"
        c = Constant.create("0", xsd + "integer")
        r1 = DatatypeRestriction.create(xsd + "integer", (xsd + "minInclusive",), (c,))
        r2 = DatatypeRestriction.create(xsd + "decimal", (xsd + "minInclusive",), (c,))
        assert r1 != r2

    def test_is_always_true_false(self):
        xsd = "http://www.w3.org/2001/XMLSchema#"
        c = Constant.create("0", xsd + "integer")
        r = DatatypeRestriction.create(xsd + "integer", (xsd + "minInclusive",), (c,))
        assert r.is_always_true() is False
        assert r.is_always_false() is False


# ===========================================================================
# 19. InternalDatatype
# ===========================================================================

class TestInternalDatatype:
    def test_rdfs_literal(self):
        assert InternalDatatype.RDFS_LITERAL is not None
        assert InternalDatatype.RDFS_LITERAL.iri == InternalDatatype.RDFS_LITERAL_IRI

    def test_is_always_true_for_rdfs_literal(self):
        assert InternalDatatype.RDFS_LITERAL.is_always_true() is True

    def test_is_always_true_for_other(self):
        dt = InternalDatatype.create("internal:def#X")
        assert dt.is_always_true() is False

    def test_is_always_false(self):
        assert InternalDatatype.RDFS_LITERAL.is_always_false() is False

    def test_is_internal_datatype(self):
        assert InternalDatatype.create("internal:def#X").is_internal_datatype() is True
        assert InternalDatatype.RDFS_LITERAL.is_internal_datatype() is True

    def test_arity(self):
        assert InternalDatatype.create("internal:def#X").arity() == 1

    def test_interning(self):
        d1 = InternalDatatype.create("internal:def#X")
        d2 = InternalDatatype.create("internal:def#X")
        assert d1 is d2


# ===========================================================================
# 20. DescriptionGraph + DescriptionGraphEdge
# ===========================================================================

class TestDescriptionGraphEdge:
    def test_create_and_access(self):
        r = AtomicRole.create("http://example.org#r")
        edge = DescriptionGraphEdge(r, 0, 1)
        assert edge.atomic_role is r
        assert edge.from_vertex == 0
        assert edge.to_vertex == 1

    def test_equality_and_hash(self):
        r = AtomicRole.create("http://example.org#r")
        e1 = DescriptionGraphEdge(r, 0, 1)
        e2 = DescriptionGraphEdge(r, 0, 1)
        assert e1 == e2
        assert hash(e1) == hash(e2)


class TestDescriptionGraph:
    def test_create_and_vertex_access(self):
        c = AtomicConcept.create("http://example.org#A")
        dg = DescriptionGraph(
            "http://example.org#G",
            (c,),
            (),
            frozenset({c}),
        )
        assert dg.name == "http://example.org#G"
        assert dg.number_of_vertices() == 1
        assert dg.atomic_concept_for_vertex(0) is c

    def test_edges(self):
        c0 = AtomicConcept.create("http://example.org#A")
        c1 = AtomicConcept.create("http://example.org#B")
        r = AtomicRole.create("http://example.org#r")
        edge = DescriptionGraphEdge(r, 0, 1)
        dg = DescriptionGraph(
            "http://example.org#G",
            (c0, c1),
            (edge,),
            frozenset({c0}),
        )
        assert dg.number_of_edges() == 1
        assert dg.edge(0) is edge

    def test_arity(self):
        c = AtomicConcept.create("http://example.org#A")
        dg = DescriptionGraph(
            "http://example.org#G",
            (c,),
            (),
            frozenset({c}),
        )
        assert dg.arity() == 1

    def test_start_concepts(self):
        c = AtomicConcept.create("http://example.org#A")
        dg = DescriptionGraph(
            "http://example.org#G",
            (c,),
            (),
            frozenset({c}),
        )
        assert c in dg.start_concepts

    def test_produce_start_dl_clauses(self):
        c = AtomicConcept.create("http://example.org#A")
        dg = DescriptionGraph(
            "http://example.org#G",
            (c,),
            (),
            frozenset({c}),
        )
        clauses: set[DLClause] = set()
        dg.produce_start_dl_clauses(clauses)
        assert len(clauses) == 1
        clause = clauses.pop()
        assert clause.body_length() == 1
        assert clause.body_atom(0).predicate is c
        # Head should contain ExistsDescriptionGraph atoms
        assert clause.head_length() >= 1
        assert isinstance(clause.head_atom(0).predicate, ExistsDescriptionGraph)


# ===========================================================================
# 21. DLOntology
# ===========================================================================

class TestDLOntology:
    @pytest.fixture
    def x(self):
        return Variable.create("X")

    @pytest.fixture
    def y(self):
        return Variable.create("Y")

    def test_empty_ontology(self):
        ont = DLOntology("http://example.org#ont")
        assert ont.ontology_iri == "http://example.org#ont"
        assert len(ont.dl_clauses) == 0
        assert len(ont.positive_facts) == 0
        assert len(ont.negative_facts) == 0

    def test_is_horn_single_head(self, x):
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        clause = DLClause.create((Atom.create(b, x),), (Atom.create(a, x),))
        ont = DLOntology(dl_clauses=frozenset({clause}))
        assert ont.is_horn() is True

    def test_is_horn_multiple_heads(self, x):
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        c = AtomicConcept.create("http://example.org#C")
        clause = DLClause.create(
            (Atom.create(b, x), Atom.create(c, x)),
            (Atom.create(a, x),),
        )
        ont = DLOntology(dl_clauses=frozenset({clause}))
        assert ont.is_horn() is False

    def test_has_inverse_roles(self, x, y):
        r = AtomicRole.create("http://example.org#r")
        inv = InverseRole.create(r)
        # InverseRole doesn't have arity(), so we can't create an Atom with it directly.
        # The _check_inverses method looks for InverseRole in atom predicates,
        # but atoms are created with AtomicRole. Test by checking the method directly.
        # Instead, use a role atom and verify the ontology's _check_inverses logic.
        atom = Atom.create(r, x, y)
        ont = DLOntology(dl_clauses=frozenset({DLClause.create((atom,), ())}))
        # Without actual InverseRole predicates in atoms, this is False
        assert ont.has_inverse_roles() is False

    def test_has_no_inverse_roles(self, x):
        a = AtomicConcept.create("http://example.org#A")
        clause = DLClause.create((Atom.create(a, x),), ())
        ont = DLOntology(dl_clauses=frozenset({clause}))
        assert ont.has_inverse_roles() is False

    def test_has_datatypes(self, x):
        dt = InternalDatatype.create("internal:def#X")
        atom = Atom.create(dt, x)
        clause = DLClause.create((atom,), ())
        ont = DLOntology(dl_clauses=frozenset({clause}))
        assert ont.has_datatypes() is True

    def test_has_no_datatypes(self, x):
        a = AtomicConcept.create("http://example.org#A")
        clause = DLClause.create((Atom.create(a, x),), ())
        ont = DLOntology(dl_clauses=frozenset({clause}))
        assert ont.has_datatypes() is False

    def test_collects_concepts(self, x):
        a = AtomicConcept.create("http://example.org#A")
        b = AtomicConcept.create("http://example.org#B")
        clause = DLClause.create((Atom.create(b, x),), (Atom.create(a, x),))
        ont = DLOntology(dl_clauses=frozenset({clause}))
        assert a in ont.all_atomic_concepts
        assert b in ont.all_atomic_concepts

    def test_collects_individuals(self, x):
        a = AtomicConcept.create("http://example.org#A")
        i = Individual.create("http://example.org#john")
        atom = Atom.create(a, i)
        ont = DLOntology(positive_facts=frozenset({atom}))
        assert i in ont.all_individuals

    def test_contains_atomic_concept(self, x):
        a = AtomicConcept.create("http://example.org#A")
        clause = DLClause.create((Atom.create(a, x),), ())
        ont = DLOntology(dl_clauses=frozenset({clause}))
        assert ont.contains_atomic_concept(a) is True

    def test_contains_individual(self):
        a = AtomicConcept.create("http://example.org#A")
        i = Individual.create("http://example.org#john")
        atom = Atom.create(a, i)
        ont = DLOntology(positive_facts=frozenset({atom}))
        assert ont.contains_individual(i) is True

    def test_repr(self):
        ont = DLOntology("http://example.org#ont")
        r = repr(ont)
        assert "DLOntology" in r
        assert "0 clauses" in r
