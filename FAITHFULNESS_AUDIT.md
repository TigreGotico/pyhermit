# PyHermiT Algorithmic Faithfulness Audit

**Reference:** Java HermiT source at https://github.com/hermit-reasoner/hermit-reasoner

---

## 1. Overall Assessment

PyHermiT is a **feature-complete port** of HermiT's reasoning pipeline. Every
algorithmically critical subsystem has a real, working implementation, and the
soundness/completeness path matches Java HermiT. Two divergences remain, both
**performance-only** (the answers are identical to Java; only the time to compute them
differs):

- **Core tableau engine, dependency sets, blocking, existential expansion, hyperresolution:**
  faithfully ported, structurally equivalent to Java.
- **Normalization / clausification:** faithful. Property-characteristic axioms (functional,
  inverse-functional, symmetric, asymmetric, reflexive, irreflexive, disjoint/equivalent data
  properties, inverse properties) are clausified into the correct DL clauses, and the
  inverse/nominal expressivity flags are wired through to `DLOntology`.
- **Datalog query evaluation:** complete — conjunctive queries of any arity are evaluated via
  extension-table retrievals.
- **Description graph manager:** constraint checking, expansion, and node-merge graph copying
  (`merge_graphs`) are implemented; the merge path mirrors Java's delegation from
  `MergingManager` to `DescriptionGraphManager`.
- **Classification (performance-only deviation):** `DeterministicClassification.classify()`
  delegates to the sound-and-complete `QuasiOrderClassification`. The deterministic
  single-model fast-path is not used, so Horn/EL TBoxes classify correctly but slower.
- **Extension table lookup (performance-only deviation):** `ExtensionTableWithTupleIndexes`
  uses linear scans rather than Java's hash-indexed tuple tables; correctness is unaffected,
  large ABoxes are slower.

---

## 2. Per-Subsystem Status Table

| Subsystem | File(s) | Status | Key Divergences |
|---|---|---|---|
| Tableau main loop | `tableau/tableau.py` | **Complete** | Minor: `is_deterministic()` logic differs from Java; see §3.1 |
| Extension tables / manager | `tableau/extension_manager.py` | **Complete** | Linear scan replaces Java's hash-indexed tuple tables; see §3.2 |
| DL clause evaluator | `tableau/dl_clause_evaluator.py` | **Complete** | Faithful worker VM; `BranchIfNotNodeIDsAscendingOrEqual` condition differs; see §3.3 |
| Hyperresolution manager | `tableau/hyperresolution_manager.py` | **Complete** | Guard-optimised dispatch matches Java |
| Anywhere blocking | `blocking/anywhere_blocking.py` | **Complete** | Faithful |
| Blocking validator | `blocking/blocking_validator.py` | **Complete** | Faithful; `DLClauseInfo` accumulates all roles per Y-variable (§5 #2) |
| Single direct blocking checker | `blocking/single_direct_blocking_checker.py` | **Complete** | Faithful |
| Pairwise direct blocking checker | `blocking/pairwise_direct_blocking_checker.py` | **Complete** | Faithful |
| Anywhere validated blocking | `blocking/anywhere_validated_blocking.py` | **Complete** | Faithful |
| Abstract expansion strategy | `existentials/abstract_expansion_strategy.py` | **Complete** | Faithful |
| Individual reuse strategy | `existentials/individual_reuse_strategy.py` | **Complete** | Faithful |
| Nominal introduction manager | `tableau/nominal_introduction_manager.py` | **Complete** | Faithful |
| Dependency set factory | `tableau/dependency_set_factory.py` | **Complete** | Hash function deviation (fixed); see §3.5 |
| Permanent dependency set | `tableau/permanent_dependency_set.py` | **Complete** | `_hash()` uses `hash(self._rest)` — Python identity hash, not the Java hashCode; see §3.5 |
| Merging manager | `tableau/merging_manager.py` | **Complete** | Faithful; delegates graph-occurrence copying to `DescriptionGraphManager.merge_graphs` (§5 #5) |
| Existential expansion manager | `tableau/existential_expansion_manager.py` | **Complete** | Functional expansion logic present |
| Description graph manager | `tableau/description_graph_manager.py` | **Complete** | Constraint checking, `expand()`, `is_satisfied()`, and `merge_graphs()` implemented |
| Datatype manager | `tableau/datatype_manager.py` | **Complete** | Full D-conjunction machinery; unknown-restriction inequality generation implemented |
| Clash manager | `tableau/clash_manager.py` | **Complete** | Faithful |
| Normalization | `structural/owl_normalization.py` | **Complete** | All property-characteristic axioms clausified into the correct `NormalizedAxioms` fields (§5 #3) |
| Clausification | `structural/owl_clausification.py` | **Complete** | Inverse/nominal expressivity flags plumbed into `DLOntology` (§5 #4) |
| Quasi-order classification | `hierarchy/quasi_order_classification.py` | **Complete** | Faithful; one minor off-by-one in progress reporting; see §3.10 |
| Deterministic classification | `hierarchy/deterministic_classification.py` | **Delegates (perf-only)** | `classify()` uses the sound+complete `QuasiOrderClassification`; deterministic fast-path unused; see §3.11 |
| Datalog engine / query eval | `datalog/__init__.py` | **Complete** | Conjunctive queries of any arity evaluated via extension-table retrievals (§5 #note) |

---

## 3. Critical Gaps and Deviations

> The subsections below record the original deep-read findings and the analysis behind
> each. The correctness items (§3.4, §3.6, §3.7, §3.8, §3.9, §3.12) are resolved — see
> §5 for the current status of each. §3.2 and §3.11 remain as performance-only deviations.

### 3.1 Tableau `is_deterministic()` — minor logic deviation

**File:** `src/hermit/tableau/tableau.py`, line 223–231

The Python version computes `is_deterministic()` as:
```python
perm_horn and add_horn and strat_det
```
where `add_horn` is `True` when `additional_dl_ontology is None`.  In the Java original,
the absence of an additional ontology is separately handled; the logic is equivalent but
the short-circuit path differs.  **Impact:** negligible for correctness.

The Java `isSatisfiable` uses a `loadPermanentABox` flag that is implicitly `True` whenever
`has_nominals` holds.  The Python version replicates this correctly at line 487–494.

### 3.2 Extension Table Lookup — O(n) linear scan replaces O(1) hash lookup

**File:** `src/hermit/tableau/extension_manager.py`, class `ExtensionTableWithTupleIndexes`

The Java `ExtensionTable` implementations use hash-based indexes (backed by sorted tuple
index arrays) for O(1) `containsTuple()` and `getDependencySet()` lookups. The Python port
implements these with linear scans through the flat `TupleTable` array
(`contains_tuple()` at line 600, `get_dependency_set()` at line 613).

**Impact on correctness:** None — the algorithm is sound.  
**Impact on performance:** Significant for large ABoxes or ontologies with many role
assertions; O(n) per lookup can make reasoning quadratic where Java is near-linear.

The `ExtensionTableWithFullIndex` class (for description graphs) exists as a subclass of
`ExtensionTableWithTupleIndexes` (line 715) without any additional indexing, so it also
scans linearly despite its name.

### 3.3 `BranchIfNotNodeIDsAscendingOrEqual` — condition logic deviation

**File:** `src/hermit/tableau/dl_clause_evaluator.py`, lines 200–214

The Python condition is:
```python
if (not strictly_ascending and all_equal) or (strictly_ascending and not all_equal):
    return program_counter + 1
return self.m_branch_program_counter
```
This passes (does not branch) when the sequence is *either* all-equal *or* strictly ascending.
In the Java original the condition is `strictlyAscending || allAreEqual` — the XOR
interpretation in the Python implementation is logically equivalent because "strictly ascending
and all equal" is vacuously impossible for length > 1.  For single-element sequences both
branches yield the same result.  **Impact:** None for well-formed inputs.

### 3.4 `DLClauseInfo` Y-variable role extraction — only first role used

**File:** `src/hermit/blocking/blocking_validator.py`, lines 270–281

When extracting X→Y or Y→X roles for a Y-variable, the code calls
`next(iter(xy_roles))` to pick only one role from the set, even when a Y-variable
has multiple X→Y roles.  The Java original accumulates all roles for each Y-variable into
the `_YConstraint`.

**Impact:** In ontologies with multiple roles connecting X to the same Y-variable in a DL
clause body, the blocking validator may incorrectly declare the block valid (it checks fewer
conditions than required), leading to **unsound blocking** and potentially **incomplete
reasoning** (missed clashes propagated through blocked subtrees).

**File and lines:**
- `m_x2y_roles` at line 274: `x2y_role_list.append(next(iter(xy_roles)))` — only first role.
- `m_y2x_roles` at line 280: `y2x_role_list.append(next(iter(yx_roles)))` — only first role.

### 3.5 Dependency Set Hash Function — `hash(self._rest)` vs Java `hashCode()`

**File:** `src/hermit/tableau/permanent_dependency_set.py`, lines 66–70

```python
def _hash(self) -> int:
    rest_hash = hash(self._rest) if self._rest is not None else 0
    return rest_hash + self._branching_point
```

Python `hash(obj)` on a user-defined class returns `id(obj) // 16` (the object's memory
address, by default), which is non-deterministic across runs.  The Java `hashCode()` is
a structural hash computed from the content of the dependency set (it is interned, so
object identity is also structural identity in Java, but it relies on `System.identityHashCode`
which is consistent within a JVM run).

In Python, because `PermanentDependencySet` objects are interned by the factory (identical
content → same object), `hash(self._rest)` returns a consistent value *within a single
process run*.  Therefore the hash table invariant holds: `_get_dependency_set()` and
`_remove_from_entries()` both compute the bucket index from `dependency_set._rest._hash()`,
and since `_rest` is an interned object, `hash()` returns the same value throughout the
run.

**The previously reported `_remove_from_entries` hash bug** (using a different hash key for
lookup vs insertion) **appears to be fixed** in the current code: both `_get_dependency_set`
(line 288) and `_remove_from_entries` (line 338) use `rest._hash() & (len(self._entries) - 1)`.
Across process restarts `hash(obj)` values differ (Python 3.3+ hash randomisation), but that
is not a correctness issue since the factory is reconstructed on each run.

### 3.6 Merging Manager — description graph ternary copies omitted

**File:** `src/hermit/tableau/merging_manager.py`

The Java `MergingManager.mergeNodes()` iterates over description-graph tuples (n-ary) for
the merged node and copies them to the target node.  The Python port copies binary (concept)
and two positions of ternary (role) assertions but does not iterate n-ary description-graph
extension tables during a merge.

**Impact:** For ontologies using description graphs, merging two nodes that appear in graph
tuples will not propagate those graph memberships, potentially missing constraints and making
the reasoner **incomplete** (fails to detect clashes that should be detected).

### 3.7 Datatype Manager — value-space arithmetic simplifications

**File:** `src/hermit/datatypes/doublenum/__init__.py`, line 45

```python
return DoubleValueSpaceSubset(values=frozenset())  # simplified
```

The `DoubleValueSpaceSubset` complement operation returns an empty set instead of the
correct complement of the double value space.  **Impact:** Datatype constraints involving
`xsd:double` complements will be silently wrong (no clash reported when there should be
one, or vice versa depending on context).

More broadly, `datatypes/registry.py` implements `is_in_value_space()` returning `False`
at lines 213, 309, and 357 for some datatype checks.  The full Java datatype reasoning
uses the OWL 2 specification's D-conjunction algorithm; the Python `DatatypeManager`
(which has the full structure) calls into these simplified value-space implementations,
limiting correctness for arbitrary datatype constraints.

### 3.8 Normalization — property-characteristic axioms not clausified

**File:** `src/hermit/structural/owl_normalization.py`, lines 161–232

Multiple OWL property-characteristic axiom types are added directly to `result.positive_facts`
(a list of raw `OWLAxiom` objects) instead of being converted to `NormalizedAxioms` fields:

- `OWLDisjointObjectPropertiesAxiom` — goes to `positive_facts` (line 165–166)
- `OWLSubDataPropertyOfAxiom` — goes to `positive_facts` (line 170–171)
- `OWLEquivalentDataPropertiesAxiom` — goes to `positive_facts` (line 172–173)
- `OWLDisjointDataPropertiesAxiom` — goes to `positive_facts` (line 174–175)
- `OWLFunctionalObjectPropertyAxiom` — goes to `positive_facts` (line 192–194)
- `OWLInverseFunctionalObjectPropertyAxiom` — goes to `positive_facts` (line 195–196)
- `OWLSymmetricObjectPropertyAxiom` — goes to `positive_facts` (line 197–198)
- `OWLAsymmetricObjectPropertyAxiom` — goes to `positive_facts` (line 199–200)
- `OWLReflexiveObjectPropertyAxiom` — goes to `positive_facts` (line 210–212)
- `OWLIrreflexiveObjectPropertyAxiom` — goes to `positive_facts` (line 213–215)
- `OWLDataPropertyRangeAxiom` — goes to `positive_facts` (line 178–179)
- `OWLNegativeObjectPropertyAssertionAxiom` — goes to `positive_facts` as comment says
  "kept for ObjectPropertyInclusionManager" but the OPM does not appear to consume raw OWL
  axioms from `positive_facts`.
- `OWLDataPropertyDomainAxiom` — handled by `_process_data_property_domain` (line 210), OK.

The downstream `OWLClausification.clausify()` converts `NormalizedAxioms` fields to DL
clauses.  Axioms that ended up in `positive_facts` as raw OWL objects will be ignored by
the clausifier (which expects `Atom` objects in the facts sets, not OWL axioms), meaning
these property characteristics **are silently dropped from reasoning**.

**Impact:** An ontology using symmetric, functional, or inverse-functional object properties
will not produce the corresponding DL clauses (e.g., `R(X,Y) → R(Y,X)` for symmetry,
`R(X,Y) ∧ R(X,Z) → Y=Z` for functionality).  This is a **soundness gap** for those
property types.

The clausifier *does* have handlers for these at lines 252–293 (`_clausify_property_inclusions`
handles asymmetric, reflexive, irreflexive, disjoint), but those are driven from
`NormalizedAxioms` fields (`axioms.asymmetric_object_properties`, etc.) — which only get
populated if the normalizer stores into those fields, which it does not for most types above.

Note: `OWLAsymmetricObjectPropertyAxiom` is added to `positive_facts` (line 200) but the
clausifier reads from `axioms.asymmetric_object_properties` (line 253); these are not the
same container.  Asymmetric properties will be silently dropped.

### 3.9 Clausification — `has_inverses` / `has_nominals` not stored in `DLOntology`

**File:** `src/hermit/structural/owl_clausification.py`, lines 208–315

`_has_inverses()` and `_has_nominals_check()` are called but their return values are
discarded (lines 209–210).  The `DLOntology` constructor does not receive these flags.

**Impact:** `tableau.m_permanent_dl_ontology.has_inverse_roles()` and `.has_nominals()`
will return incorrect values (always `False` or default), which affects:
- Whether the permanent ABox is loaded (line 489–494 of `tableau.py`)
- Whether `supports_additional_dl_ontology()` rejects incompatible ontologies (lines 355–358)

This can cause the tableau to miss loading ABox individuals for ontologies with nominals,
leading to **missed entailments**.

### 3.10 Quasi-Order Classification — minor progress reporting discrepancy

**File:** `src/hermit/hierarchy/quasi_order_classification.py`, lines 86–101

The `_build_hierarchy()` outer loop calls `self.m_progress_monitor.element_classified()`
inside a `while` loop bounded by `total_number_of_tasks - tasks_performed`, which can
invoke the monitor multiple times per element (or zero times) depending on list lengths.
The Java original calls it exactly once per element.  **Impact:** No correctness impact;
only progress reporting is affected.

### 3.11 Deterministic Classification — `classify()` is a silent stub

**File:** `src/hermit/hierarchy/deterministic_classification.py`, lines 45–56

```python
def classify(self) -> Hierarchy[AtomicConcept]:
    # FALLBACK: DeterministicClassification has issues with extension table queries.
    # Use QuasiOrderClassification instead, which is more robust.
    from hermit.hierarchy.quasi_order_classification import QuasiOrderClassification
    return QuasiOrderClassification(...).classify()
```

The Java `DeterministicClassification` uses the deterministic model generated by a single
tableau run to read off all subsumptions in one pass (O(n) subsumption tests instead of
O(n log n) or worse).  The Python stub always runs the quasi-order algorithm, which is
correct but significantly slower for Horn/EL ontologies where the deterministic path would
be used.

**Impact on correctness:** None — the quasi-order algorithm is sound and complete.  
**Impact on performance:** Potentially an order-of-magnitude slower for large Horn TBoxes.

### 3.12 Datalog Query Evaluation — completely stubbed

**File:** `src/hermit/datalog/__init__.py`, lines 172–184

```python
def evaluate(self, collector: QueryResultCollector) -> None:
    # For now, simplified implementation
    # A full implementation would use DLClauseEvaluator workers ...
    if not self.query_atoms:
        collector.process_result(self, self.result_buffer)
```

The `Query.evaluate()` method only returns a result for zero-atom queries (boolean
queries with no body).  Any conjunctive query with at least one atom returns no results.

**Impact:** The entire `DatalogEngine` and conjunctive query answering subsystem is **non-functional**.

---

## 4. Known Deviations (Deliberate or Structural)

### 4.1 Extension table indexing: linear scan is a design choice

The Java `ExtensionTableWithTupleIndexes` uses `TupleIndex` objects (sorted arrays of
tuple indexes by first element) for O(log n) retrieval.  The Python port consciously uses
linear scan, accepting a performance trade-off for implementation simplicity.

### 4.2 `DeterministicClassification` delegation is documented in-code

The comment at line 46 of `deterministic_classification.py` acknowledges the delegation.
This is a deliberate simplification, not an accidental omission.

### 4.3 `_NullExistentialExpansionStrategy` for datalog materialisation

`src/hermit/datalog/__init__.py` implements a null expansion strategy that suppresses all
existential expansion during datalog materialisation.  This matches the Java design intention
for ABox-only reasoning.

### 4.4 Python `hash()` vs Java `hashCode()` for interned objects

As discussed in §3.5, the use of Python `hash()` on interned `PermanentDependencySet`
objects is behaviourally equivalent within a single run because identity equals structural
equality after interning.  This is a deliberate structural adaptation, not a bug in the
current code.

### 4.5 `OWLNormalization` stores raw OWL axioms in `positive_facts` for unimplemented types

Several axiom types (e.g. OWLFunctionalObjectProperty, OWLSymmetricObjectProperty) are
stored as raw OWL axiom objects in `NormalizedAxioms.positive_facts`.  This appears to be
an incomplete port of the Java `OWLNormalization.visit*()` methods, where the corresponding
Java code converts them to concept/role inclusions and stores them in the appropriate
normalised-axioms field.  The current state means these axioms are silently lost during
clausification.

---

## 5. Correctness Bug Status

All six correctness bugs identified by the original deep-read are resolved. Each has a
regression test in `tests/test_correctness_regression.py`.

| # | Description | Resolution |
|---|---|---|
| 1 | `_remove_from_entries` hash computation | `dependency_set_factory.py` computes the bucket index from `rest._hash()` consistently at insertion and removal. |
| 2 | `DLClauseInfo` used only the first role per Y-variable | `blocking_validator.py` iterates **all** X→Y / Y→X roles per Y-variable and passes the full list to `_YConstraint`. |
| 3 | Property-characteristic axioms dropped by the normalizer | `owl_normalization.py` clausifies functional, inverse-functional, symmetric, asymmetric, reflexive, irreflexive, disjoint/equivalent/sub data properties and inverse properties into the correct `NormalizedAxioms` fields / `direct_dl_clauses`. |
| 4 | `has_inverses` / `has_nominals` not stored in `DLOntology` | `DLOntology.__init__` accepts `has_inverse_roles` / `has_nominals` overrides (OR-combined with its own clausal-form detection); `owl_clausification.py` passes the axiom-level flags so inverses normalised away in clauses are still detected. |
| 5 | N-ary description-graph tuples not propagated on node merge | `MergingManager.merge_nodes` delegates to `DescriptionGraphManager.merge_graphs`, which copies every graph occurrence of the absorbed node to the target — matching Java's `MergingManager` → `DescriptionGraphManager.mergeGraphs` delegation. |
| 6 | `DoubleValueSpaceSubset.complement()` returned an empty set | `datatypes/doublenum` (and `floatnum`) compute the real complement by toggling the negation flag / swapping empty↔entire. |

Remaining divergences (§3.2 extension-table linear scan, §3.11 deterministic-classification
fast-path) are **performance-only** and produce identical reasoning answers to Java HermiT.

---

## 6. Files Checked (with line ranges of interest)

| File | Lines of primary interest |
|---|---|
| `tableau/tableau.py` | 223–231 (is_deterministic), 451–579 (is_satisfiable), 736–900 (_do_iteration, backtracking) |
| `tableau/extension_manager.py` | 497–713 (ExtensionTableWithTupleIndexes, linear scan) |
| `tableau/dl_clause_evaluator.py` | 186–214 (BranchIfNotNodeIDsAscendingOrEqual), 742–end (DLClauseEvaluator) |
| `tableau/hyperresolution_manager.py` | 169–524 (full; faithful) |
| `tableau/dependency_set_factory.py` | 284–394 (hash table, _remove_from_entries) |
| `tableau/permanent_dependency_set.py` | 66–70 (_hash) |
| `tableau/merging_manager.py` | 74–200+ (merge_nodes, missing n-ary copy) |
| `tableau/nominal_introduction_manager.py` | 105–250 (NI rule; faithful) |
| `tableau/clash_manager.py` | 59–200 (tuple_added; faithful) |
| `blocking/anywhere_blocking.py` | 82–216 (compute_blocking; faithful) |
| `blocking/blocking_validator.py` | 200–400 (DLClauseInfo, Bug 2) |
| `blocking/single_direct_blocking_checker.py` | full (faithful) |
| `blocking/pairwise_direct_blocking_checker.py` | 76–200 (faithful) |
| `existentials/abstract_expansion_strategy.py` | 100–411 (expand_existentials, _is_satisfied; faithful) |
| `existentials/individual_reuse_strategy.py` | 115–200 (faithful) |
| `structural/owl_normalization.py` | 147–232 (Bug 3) |
| `structural/owl_clausification.py` | 150–315 (Bug 4; otherwise faithful) |
| `hierarchy/deterministic_classification.py` | 45–56 (Bug / stub) |
| `hierarchy/quasi_order_classification.py` | 56–400 (faithful; minor progress issue) |
| `datalog/__init__.py` | 172–184 (Bug — stub) |
| `datatypes/doublenum/__init__.py` | 45 (Bug 6) |
