# Divergences from Java HermiT

Reference implementation: Java HermiT (`org.semanticweb.HermiT`),
<https://github.com/phillord/hermit-reasoner>.

pyhermit is a structural port of HermiT: the module layout, the class
decomposition, the field names (Java camelCase preserved, `m_` prefix kept), and
the reasoning algorithm are carried over directly. `Tableau._do_iteration`, the
`HyperresolutionManager` / `DLClauseEvaluator` worker VM, the clausifier, and the
blocking strategies follow their Java counterparts closely.

This document records the points where pyhermit *intentionally or necessarily*
differs from Java HermiT. For each: **what Java does, what pyhermit does, why,
and the soundness / completeness / performance consequence.** It describes the
current state of the code (no history), grouped by the reason the divergence
exists. Every claim below was checked against the source.

A from-scratch explanation of the algorithms these divergences sit inside is in
[`docs/algorithms/`](docs/algorithms/) (start at `docs/README.md`); the
dependency-set divergence is developed at length in
[`docs/algorithms/05-dependency-directed-backtracking.md`](docs/algorithms/05-dependency-directed-backtracking.md).

## 1. Dependency-set management (FLAGSHIP divergence)

**Files:** `tableau/dependency_set_factory.py`,
`tableau/permanent_dependency_set.py`, `tableau/union_dependency_set.py`.

A *dependency set* is the set of branching-point levels a derived fact depends
on; it drives conflict-directed backjumping. The tableau asks a dependency set
for only three things (the `DependencySet` interface,
`tableau/dependency_set.py`): `contains_branching_point(b)`, `is_empty()`, and
`get_maximum_branching_point()`. None of these mutate the set.

**What Java does.** Java's `DependencySetFactory` interns permanent sets in a hash
table *and* hand-manages their lifetime with **manual reference counting**:
`addUsage` / `removeUsage` bump an integer usage counter on each
`PermanentDependencySet`, and `removeUnusedSets` periodically sweeps the table and
frees sets whose count reached zero. This is a JVM performance optimization — it
caps the live-set population during a hard run instead of leaning on the garbage
collector. Its cost is fragility: every code path that stores or drops a reference
to a permanent set must balance its `addUsage`/`removeUsage` calls exactly. An
imbalance either frees a set still in use (a dangling reference / effective
double-free that corrupts later reasoning, and in a tableau can manifest as
non-termination) or never frees one (a leak). A faithful Python port of that
protocol would reproduce the fragility without the benefit, since CPython already
reference-counts every object.

**What pyhermit does.** Permanent dependency sets are **immutable in content and
structurally interned**, and are reclaimed by **Python's garbage collector**:

- `PermanentDependencySet` (`tableau/permanent_dependency_set.py`) is a descending
  linked list (`_branching_point`, `_rest`); after the factory creates a set, its
  content fields are never reassigned (`_create_dependency_set`,
  `dependency_set_factory.py:290`).
- The factory's hash table (`_entries`) interns by structure
  (`_get_dependency_set`, `dependency_set_factory.py:272`): a lookup of
  `(rest, branching_point)` returns the existing object when present, so two
  structurally-equal sets are the *same* object. Equality is therefore object
  identity (`is`) and hashing is structural (`_hash`).
- `add_usage`, `remove_usage`, and `remove_unused_sets`
  (`dependency_set_factory.py:100-113`) are retained as **no-ops** so the many
  call sites ported verbatim from Java still compile; they perform no counting.
  Interned sets live for the factory's lifetime and are dropped wholesale by
  `clear()`. When a backtrack truncates the tuple table, dropped tuples release
  their references and ordinary CPython refcounting/GC reclaims any set that
  becomes unreachable. `LastObjectDependencySetManager.store_dependency_set`
  interns the (possibly transient) set and stores the permanent in the tuple slot;
  `forget_dependency_set` is a no-op for the same reason
  (`tableau/extension_manager.py:99-116`).

**Why this is sound and complete.** The calculus depends only on a dependency
set's *value* (membership of a level, maximum level), never on its being freed at
a particular moment, and never mutates one in place. An immutable interned linked
list answers both queries correctly, and interning gives the tableau the fast
`is`-equality and structural hashing that the extension tables and the
ground-disjunction header cache rely on — with no lifetime protocol to get wrong.
Replacing manual reclamation with GC changes only performance characteristics
(more transient allocation; GC instead of a hand-rolled free list), never an
answer.

**Residual no-op calls.** `Tableau.merge_node` /
`_backtrack_last_merged_or_pruned_node` (`tableau/tableau.py:1130`, `:1170`) and
`ExtensionManager.set_clash` / `clear_clash` (`tableau/extension_manager.py:1021`,
`:1015`) still *call* `add_usage`/`remove_usage` on the factory around merge and
clash dependency sets. Because those methods are no-ops, the calls are inert; they
are kept only to preserve the Java call structure and have no effect on results.

**Transient sets.** `UnionDependencySet` (`tableau/union_dependency_set.py`) is the
one mutable form: a union-of-constituents grown via `add_constituent` *during* a
single derivation (hyperresolution accumulating the body facts' sets), flattened
to an interned permanent set by `DependencySetFactory.get_permanent` when the
derived fact or clash is recorded. This matches Java.

## 2. Tableau core: head-disjunction expansion (verified working)

**Files:** `tableau/extension_manager.py`, `tableau/tableau.py`.

A ground head-disjunction asserted at a branching point — e.g. `U(X) → A(X) ∨
B(X)` with `A → ⊥` and `B → ⊥` over `U(a)` — must drive the engine to
inconsistency. The disjunct asserted after the branching-point push must enter the
δ-new range so the next `propagate_delta_new` promotes it into the working set,
hyperresolution sees it, and the `⊥ :- A` / `⊥ :- B` clauses fire.

At this commit this works. Two guarantees collaborate:

- `ExtensionTableWithTupleIndexes.add_tuple` advances the δ-new boundary to the
  new free slot, so every freshly added tuple lands inside
  `DELTA_NEW = [afterExtensionThis, afterDeltaNew)`
  (`extension_manager.py:603-612`), mirroring Java's `addTuple`.
- `branching_point_pushed` only *snapshots* the three δ boundaries for the level;
  it does not collapse them (`extension_manager.py:548-568`). `backtrack` restores
  the snapshot and truncates the table (`:570`).

Consequence: **sound and complete** on head disjunctions. The regression suite
`tests/test_tableau.py::TestHeadDisjunctionExpansion` covers all four cases —
both-disjuncts-clash (inconsistent), both-satisfiable (consistent),
first-clash-then-second (consistent via backjump), and a recursive satisfiable
disjunction chain (terminates) — and all pass. A full step-by-step trace of the
both-clash case is in
[`docs/algorithms/03-hypertableau-calculus.md`](docs/algorithms/03-hypertableau-calculus.md).

## 3. Performance-only deviations (sound, deliberate)

These produce identical answers to Java; only running time differs.

### 3.1 Extension-table membership is a linear scan

**File:** `tableau/extension_manager.py`,
`ExtensionTableWithTupleIndexes.contains_tuple` / `get_dependency_set` / `is_core`.

Java backs `containsTuple` / `getDependencySet` with hash-based tuple indexes for
near-O(1) lookup. In the **active** implementation here (the inline
`ExtensionTableWithTupleIndexes` in `extension_manager.py`), `contains_tuple`
(`:727`), `get_dependency_set` (`:740`), and `is_core` (`:753`) iterate the flat
`TupleTable` array element-by-element — an **O(n) linear scan**. The result is
sound; reasoning is quadratic where Java is near-linear on large ABoxes or
assertion-heavy ontologies. `ExtensionTableWithFullIndex` (description graphs)
subclasses `ExtensionTableWithTupleIndexes` without adding an index, so it scans
linearly too.

Note: the package also contains standalone `tuple_index.py`, `tuple_table.py`,
`tuple_table_full_index.py`, and `extension_table*.py` files. `tuple_index.py`
provides an index structure, but the table classes the tableau actually
instantiates (built in `ExtensionManager.__init__`,
`extension_manager.py:888-919`) are the inline `extension_manager.py` ones, which
do not use it; the separate `extension_table*.py` modules are largely re-export
shims (`extension_table_with_tuple_indexes.py` re-exports the inline class). If an
indexed lookup is being introduced, it would replace these linear scans; what the
code does **at this commit** is the linear-scan baseline described above.

### 3.2 Deterministic classification delegates to the quasi-order algorithm

**File:** `hierarchy/deterministic_classification.py`.

Java's `DeterministicClassification` reads all subsumptions off a single
deterministic model in one pass. pyhermit's `DeterministicClassification.classify()`
delegates to `QuasiOrderClassification` (`deterministic_classification.py:45`),
which is sound and complete but runs the full quasi-order procedure even for
Horn/EL TBoxes where the deterministic fast-path would apply — potentially an
order of magnitude slower on large Horn TBoxes. (The Tarjan-SCC
`build_hierarchy`/`_visit` helpers in this file *are* used, by the quasi-order
classifier.)

## 4. Representation differences forced by the language

Correct, but they change the shape of the code; relevant to anyone cross-reading
the two sources.

### 4.1 Tuple slots are element offsets, not tuple indices

**File:** `tableau/extension_manager.py`, `TupleTable`.

Java addresses tuples by tuple index and stores the dependency set in a parallel
structure. pyhermit stores each tuple inline as `arity + 1` flat slots (the extra
slot holds the dependency set) and addresses them by **element offset**
(`TupleTable.add_tuple` / `get_tuple_object`, `:43`, `:65`). The boundary fields
(`_after_extension_old/this_tuple_index`, `_after_delta_new_tuple_index`) remain
*tuple* counts, so the code converts with `* slot_size` / `// slot_size` at the
table/retrieval boundary (e.g. `propagate_delta_new`, `:766`; retrieval `open`,
`:346`). No behavioural effect.

### 4.2 Abstract base classes / idioms

`abc.ABC` replaces Java interfaces and abstract classes; list growth (`* 3 // 2`)
replaces `System.arraycopy`; relative imports and deferred (in-method) imports
replace Java package references and break import cycles. No behavioural effect.

## 5. The ontology loader

**Files:** `parser.py`, `rdfxml.py`, `owl_rdf.py`, `fss.py`, `owlxml.py`.

Java HermiT loads ontologies through the **OWL API**. pyhermit's loader is a
self-contained, standard-library reader that produces the same `hermit.owl_model`
axiom objects the OWL API would. `parser.load_ontology` /
`load_ontology_from_string` dispatch by syntax (`parser.py:24`, `:45`):

- **Functional-Style Syntax** → `fss.parse_functional_syntax` (`fss.py:497`);
- **OWL/XML** → `owlxml.parse_owlxml` (`owlxml.py:42`);
- **RDF/XML** → `rdfxml.parse_rdfxml` (`rdfxml.py:119`) producing triples, mapped
  to axioms by `owl_rdf.map_triples_to_axioms` (`owl_rdf.py:63`).

There is **no third-party OWL stack (no owlready2) on the load path** — it is
pure stdlib. The reader accepts custom and relative datatype IRIs, retains class
assertions on anonymous individuals, and preserves cyclic `EquivalentClasses` /
`EquivalentProperties` axioms. Constructs the reasoning core does not yet support
(datatype restrictions on data properties in some positions; named-class nominal
enumerations requiring nominal closure) are over-approximated or omitted rather
than emitted as expressions the clausifier cannot accept.

(The repository `README.md` and `docs/index.md` still mention loading "via
owlready2"; that is stale prose, not the code path. The code path is the stdlib
readers above.)

## 6. Partial subsystems

### 6.1 Datalog / DL-safe rules

**File:** `datalog/__init__.py`.

Conjunctive-query answering is a recursive nested-loop join over the materialized
extension tables (`Query.evaluate`, `:172`), rather than Java's compiled
`DLClauseEvaluator` worker VM. It answers ground/atomic and multi-atom conjunctive
queries against the saturated model; broader DL-safe rule materialization is not
the full Java pipeline.

### 6.2 Datatype value-space coverage

**File:** `datatypes/`, `tableau/datatype_manager.py`.

The `DatatypeManager` machinery (D-conjunction handling, value-space intersection,
unknown-restriction inequality generation) is ported. Coverage of the OWL 2
datatype map across the full set of facet/value-space combinations is narrower
than Java's: datatype reasoning is exact for the implemented datatypes
(`datatypes/registry.py`: xsd string/decimal/integer/float/double/boolean/anyURI/
dateTime, rdf:PlainLiteral, base64Binary, hexBinary, …) and conservative
elsewhere.

## 7. Per-subsystem summary

| Subsystem | File(s) | Status vs Java |
|---|---|---|
| Tableau main loop | `tableau/tableau.py` | Faithful |
| Extension tables / delta ring | `tableau/extension_manager.py` | Faithful algorithm; element-offset slots (§4.1); membership is linear scan (§3.1) |
| Head-disjunction expansion / backtracking | `tableau/extension_manager.py`, `tableau/tableau.py` | Faithful; verified working (§2) |
| Dependency sets | `tableau/dependency_set_factory.py`, `permanent_dependency_set.py`, `union_dependency_set.py` | Interned + GC instead of manual refcounting (§1); sound/complete |
| Hyperresolution / clause evaluator | `tableau/hyperresolution_manager.py`, `tableau/dl_clause_evaluator.py` | Faithful worker VM |
| Blocking (all strategies + validator) | `blocking/` | Faithful |
| Existential expansion | `existentials/` | Faithful |
| Merging / nominal introduction | `tableau/merging_manager.py`, `tableau/nominal_introduction_manager.py` | Faithful |
| Description graphs | `tableau/description_graph_manager.py` | Faithful; full-index table scans linearly (§3.1) |
| Datatype manager | `tableau/datatype_manager.py`, `datatypes/` | Faithful machinery; narrower value-space coverage (§6.2) |
| Normalization / clausification | `structural/` | Faithful |
| Quasi-order classification | `hierarchy/quasi_order_classification.py` | Faithful |
| Deterministic classification | `hierarchy/deterministic_classification.py` | Delegates to quasi-order (§3.2) |
| Datalog / query evaluation | `datalog/` | Nested-loop join (§6.1) |
| Ontology loading | `parser.py`, `rdfxml.py`, `owl_rdf.py`, `fss.py`, `owlxml.py` | Stdlib RDF/XML + OWL/XML + FSS reader; no owlready2 (§5) |
