# Divergences from Java HermiT

Reference implementation: Java HermiT (`org.semanticweb.HermiT`),
<https://github.com/phillord/hermit-reasoner>.

pyhermit is a structural port of HermiT: the module layout, the class
decomposition, the field names (Java camelCase preserved, `m_` prefix kept), and
the reasoning algorithm are carried over directly. `Tableau._do_iteration`,
`HyperresolutionManager`, the clausifier, and the blocking strategies are
line-for-line equivalent to their Java counterparts.

This document records the points where pyhermit *intentionally or necessarily*
differs from Java HermiT, so the two can be compared without re-deriving the
correspondence each time. It describes the current state of the code, grouped by
the reason the divergence exists.

## 1. Faithful core (no behavioural divergence)

The soundness/completeness path matches Java HermiT:

- **Normalization → clausification**: OWL axioms → negation normal form →
  DL clauses, including property-characteristic axioms (functional,
  inverse-functional, symmetric, asymmetric, reflexive, irreflexive,
  disjoint/equivalent object and data properties, inverses) clausified into the
  matching `NormalizedAxioms` fields, with inverse/nominal expressivity flags
  plumbed into `DLOntology`.
- **Tableau engine**: the `propagate δ-new → hyperresolution → existential
  expansion → ground-disjunction branching → dependency-directed backtracking`
  loop, branching points, the delta ring (`old`/`this`/`δ-new` boundaries), and
  clash handling.
- **Dependency sets**: interned `PermanentDependencySet` (linked-list, structural
  interning via the factory) plus the transient `UnionDependencySet`. The union
  is grown through `add_constituent`; the factory flattens it into a permanent set
  when a clash or derived fact is recorded.
- **Blocking**: anywhere / ancestor / single- and pairwise-direct / validated
  strategies and the blocking validator (all roles accumulated per Y-variable).
- **Backtracking**: `branching_point_pushed` records the δ-this / δ-new boundary at
  the push; `backtrack` truncates the tuple table back to the saved extension-old
  boundary and resets the δ boundaries.

## 2. Performance-only deviations (sound, deliberate)

These produce identical answers to Java; only running time differs.

### 2.1 Extension-table lookup is a linear scan

**File:** `tableau/extension_manager.py`, `ExtensionTableWithTupleIndexes`.

Java backs `containsTuple` / `getDependencySet` with hash-based tuple indexes for
O(1) lookup. pyhermit scans the flat `TupleTable` array (O(n)). The result is
sound; reasoning is quadratic where Java is near-linear on large ABoxes or
assertion-heavy ontologies. `ExtensionTableWithFullIndex` (description graphs)
subclasses `ExtensionTableWithTupleIndexes` without adding an index, so it scans
linearly as well.

### 2.2 Deterministic classification delegates to the quasi-order algorithm

**File:** `hierarchy/deterministic_classification.py`.

Java's `DeterministicClassification` reads all subsumptions off a single
deterministic model in one pass. pyhermit's `classify()` delegates to
`QuasiOrderClassification`, which is sound and complete but runs the full
quasi-order procedure even for Horn/EL TBoxes where the deterministic fast-path
would apply — potentially an order of magnitude slower on large Horn TBoxes.

## 3. Representation differences forced by the language

These are correct but change the shape of the code; they matter to anyone
cross-reading the two sources.

### 3.1 Tuple indices are element offsets, not tuple indices

**File:** `tableau/extension_manager.py`, `TupleTable`.

Java addresses tuples by tuple index and stores the dependency set in a parallel
structure. pyhermit stores each tuple inline as `arity + 1` flat slots (the extra
slot holds the dependency set) and addresses them by **element offset**. The
boundary fields (`_after_extension_old/this_tuple_index`, `_after_delta_new_…`)
remain *tuple* counts, so the code converts with `* slot_size` / `// slot_size`
at the table/retrieval boundary. `propagate_delta_new` rotates the boundaries so a
freshly asserted tuple in the DELTA_NEW range is promoted into the apply range on
the next iteration.

### 3.2 Abstract base classes / idioms

Abstract base classes (`ABC`) replace Java interfaces and abstract classes; list
growth replaces `System.arraycopy`; relative imports replace package references.
No behavioural effect.

## 4. External dependency substitution — the parser

**File:** `parser.py`.

Java HermiT loads ontologies through the **OWL API**. There is no OWL API in
Python, so `load_ontology` bridges through **owlready2**, a different OWL library
with different parsing behaviour. This is the least faithful component: it is an
adapter, not a port. Known consequences, relative to the OWL API:

- Functional-Style Syntax and OWL/XML inputs are not parsed.
- Custom / unrecognised datatypes raise during load.
- Class assertions on anonymous individuals are silently dropped.
- Cyclic `EquivalentClasses` / `EquivalentProperties` axioms are mangled
  (owlready2 emits a cyclic-subclass warning and discards an edge).

The reasoning core is independent of this; replacing the loader (a faithful
RDF/FSS reader, or porting the OWL API loading path) is what unblocks the
WebOnt-description-logic conformance family.

## 5. Partial subsystems

### 5.1 Datalog / DL-safe rules

**File:** `datalog/__init__.py`.

Conjunctive query answering is implemented as a recursive nested-loop join over
the materialized extension tables (`Query.evaluate`), rather than via Java's
compiled `DLClauseEvaluator` worker VM. It answers ground/atomic and multi-atom
conjunctive queries against the saturated model; broader DL-safe rule
materialization is not the full Java pipeline.

### 5.2 Datatype value-space coverage

**File:** `datatypes/`.

The `DatatypeManager` machinery (D-conjunction handling, unknown-restriction
inequality generation) is ported. Coverage of the OWL 2 datatype map across the
full set of facet/value-space combinations is narrower than Java's; datatype
reasoning is faithful for the implemented datatypes and conservative elsewhere.

### 5.3 Head-disjunction inconsistency (open)

**File:** `tableau/extension_manager.py`, `tableau/dl_clause_evaluator.py`.

A ground disjunction asserted at a branching point — e.g. `U(X) → A(X) ∨ B(X)`
with `A → ⊥` and `B → ⊥` over `U(a)` — is not always promoted into the apply
range before the iteration completes, so the resulting clash never fires and the
ontology is reported consistent when it is inconsistent. Satisfiable disjunctions
and disjunctions where one branch clashes and another is satisfiable backtrack
correctly. The defect is in the Python δ-ring / dependency-set interaction, not
in the (byte-faithful) `propagate_delta_new`. The regression case is captured as
a strict `xfail` in `tests/test_tableau.py::TestHeadDisjunctionExpansion`.

## 6. Per-subsystem summary

| Subsystem | File(s) | Status vs Java |
|---|---|---|
| Tableau main loop | `tableau/tableau.py` | Faithful |
| Extension tables | `tableau/extension_manager.py` | Faithful algorithm; element-offset indexing (§3.1); linear scan (§2.1) |
| Branching / backtracking | `tableau/extension_manager.py`, `tableau/tableau.py` | Faithful; head-disjunction inconsistency open (§5.3) |
| Dependency sets (permanent / union) | `tableau/permanent_dependency_set.py`, `tableau/union_dependency_set.py` | Faithful |
| Hyperresolution / clause evaluator | `tableau/hyperresolution_manager.py`, `tableau/dl_clause_evaluator.py` | Faithful worker VM |
| Blocking (all strategies + validator) | `blocking/` | Faithful |
| Existential expansion | `existentials/` | Faithful |
| Merging / nominal introduction | `tableau/merging_manager.py`, `tableau/nominal_introduction_manager.py` | Faithful |
| Description graphs | `tableau/description_graph_manager.py` | Faithful; full-index table scans linearly (§2.1) |
| Datatype manager | `tableau/datatype_manager.py`, `datatypes/` | Faithful machinery; narrower value-space coverage (§5.2) |
| Normalization / clausification | `structural/` | Faithful |
| Quasi-order classification | `hierarchy/quasi_order_classification.py` | Faithful |
| Deterministic classification | `hierarchy/deterministic_classification.py` | Delegates to quasi-order (§2.2) |
| Datalog / query evaluation | `datalog/` | Nested-loop join (§5.1) |
| Ontology loading | `parser.py` | owlready2 adapter, not OWL API (§4) |
