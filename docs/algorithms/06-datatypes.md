# 06 — Datatypes (Concrete Domains)

So far every object in a model has been *abstract* — a node standing for "some
thing." OWL also lets individuals carry **concrete data values**: ages, names,
dates. `John hasAge 42`, `42 ≥ 18`. Reasoning about these values is the
**datatype** (or **concrete-domain**) part of the calculus. This chapter explains
what changes and how pyhermit checks it.

## 1. Data properties, literals, and data ranges

Three new ingredients (all in `hermit.model` / `hermit.datatypes`):

- **Data properties** relate an abstract individual to a **literal** value:
  `hasAge(john, 42)`. (Object properties relate two individuals; data properties
  relate an individual to data.)
- **Literals / constants** are typed values: `"42"^^xsd:integer`,
  `"true"^^xsd:boolean`. pyhermit: `hermit.model.Constant`.
- **Data ranges** are sets of literals, the data-world analogue of concepts:
  - a bare **datatype** like `xsd:integer` (all integers);
  - a **datatype restriction**: a datatype narrowed by **facets**, e.g.
    `xsd:integer[≥ 18]` ("integers at least 18"). pyhermit:
    `hermit.model.DatatypeRestriction`, holding `_datatype_iri`, `_facet_uris`,
    `_facet_values` (`src/hermit/model/__init__.py:1751`);
  - an **enumeration** of explicit values `{1, 2, 3}`:
    `hermit.model.ConstantEnumeration` (`:1395`);
  - complements / intersections of the above.

A **facet** is a named constraint with a value: `minInclusive 18`,
`maxExclusive 100`, `length 5`, `pattern "[A-Z]+"`. Restricting a datatype by
facets carves out a subset of its **value space** (the set of values the datatype
denotes).

## 2. The concrete-domain nodes

In the tableau, literals live on their own kind of node. `Tableau`
distinguishes node types (`hermit.tableau.node_type.NodeType`): abstract nodes
(`NAMED_NODE`, `NI_NODE`, `TREE_NODE`) versus **`CONCRETE_NODE`** and
`ROOT_CONSTANT_NODE` for data values. A data-property assertion `hasAge(john, v)`
links the abstract node for `john` to a concrete node `v`, and a data-range
assertion `xsd:integer[≥18](v)` labels the concrete node — exactly parallel to
concept assertions on abstract nodes, stored in the same binary extension table.

When a fresh concrete node is created it is seeded with the universal data range
`rdfs:Literal` (`InternalDatatype.RDFS_LITERAL`), just as a fresh abstract node is
seeded with `⊤` (`Tableau._create_new_node_raw`, `src/hermit/tableau/tableau.py`).

## 3. The datatype manager

Clause firing alone cannot decide whether `xsd:integer[≥18]` and
`xsd:integer[≤10]` on the *same* concrete node are jointly satisfiable — that
needs value-space arithmetic. The `DatatypeManager`
(`src/hermit/tableau/datatype_manager.py`) does it. The main loop calls it each
iteration (guarded by the cached flag `m_check_datatypes`, set when the ontology
has datatypes):

- **`check_datatype_constraints()`** (`datatype_manager.py:188`): for each
  concrete node, gather all data ranges asserted on it into a **D-conjunction**
  (`DConjunction`, `:672`) — the conjunction of all the constraints the node must
  satisfy — and test whether their value spaces have a **common value**. If the
  intersection is empty, no literal can satisfy the node: **datatype clash**
  (`_set_clash_for`, `:617`), recorded with the union of the contributing
  dependency sets, after which normal backjumping (Chapter 05) takes over.
- **`apply_unknown_datatype_restriction_semantics()`** (`:105`): handles
  restrictions over datatypes whose value space pyhermit does not fully model, by
  generating the inequalities needed to stay sound (guarded by
  `m_check_unknown_datatype_restrictions`).

Number restrictions on data properties also generate distinctness obligations
between concrete nodes; the manager threads those through the same
`DConjunction` machinery.

## 4. Value spaces and handlers

The actual "do these constraints share a value?" arithmetic is delegated to
per-datatype **handlers** in the datatype registry
(`src/hermit/datatypes/registry.py`). Each OWL 2 datatype — `xsd:string`,
`xsd:decimal`, `xsd:integer`, `xsd:float`, `xsd:double`, `xsd:boolean`,
`xsd:anyURI`, `xsd:dateTime`, `rdf:PlainLiteral`, `xsd:base64Binary`,
`xsd:hexBinary`, … — is a `DatatypeHandler` (`:90`) that knows how to:

- parse a lexical form into a value (`parse_literal`),
- build a **`ValueSpaceSubset`** (`:40`) for a datatype-plus-facets, and
- intersect/complement value-space subsets and test emptiness or
  `has_cardinality_at_least(n)` (needed for `≥n p.range` over data).

The clash test is then: intersect all the asserted subsets for a node; if the
result `is_empty()`, clash.

## 5. Worked example

```
ABox:  hasAge(john, v)
TBox:  Adult ≡ ∃hasAge.xsd:integer[≥ 18]
       Adult(john)
       ∀hasAge.xsd:integer[≤ 10] (john)      # contrived second constraint
```

Tracing the concrete node `v`:

```
v : rdfs:Literal                       (seeded on creation)
    xsd:integer[≥18]                   (from Adult ≡ ∃hasAge.…, via john)
    xsd:integer[≤10]                   (from the ∀hasAge constraint)

DatatypeManager.check_datatype_constraints:
    D-conjunction on v = { integer[≥18] , integer[≤10] }
    value-space intersection:  {n : n≥18} ∩ {n : n≤10}  =  ∅
    => is_empty()  => DATATYPE CLASH on v.
```

The clash propagates; since the constraints trace back (through `john` and
`Adult`) to the facts with empty dependency sets, no branch can repair it, and the
ontology is **inconsistent**. If instead the second facet had been `[≤ 30]`, the
intersection `{18..30}` would be non-empty and `v` could be, say, `20` — no clash,
**consistent**.

## 6. Scope note

The datatype *machinery* (D-conjunction handling, value-space intersection,
unknown-restriction inequality generation) is a faithful port. The breadth of the
OWL 2 datatype map that pyhermit fully models is narrower than Java's: it is exact
for the implemented datatypes and conservative elsewhere. See
`FAITHFULNESS_AUDIT.md` for the precise current coverage.

---

Previous: [05 — Dependency-Directed Backtracking](05-dependency-directed-backtracking.md)
· Next: [07 — Classification & Queries](07-classification-and-queries.md)
