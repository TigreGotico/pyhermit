# pyhermit Project Status

## Completed ✅

- [x] **Model layer** (1,779 lines) — 30 DL classes with full type hints, interning, visitor dispatch
- [x] **Datatype handlers** (11 handlers, 32 IRIs) — owlreal (BigRational), double, float, datetime, boolean, anyURI, xml:literal, rdf:PlainLiteral, binary
- [x] **Configuration** — 5 enums, all Java defaults, clone()
- [x] **Monitors** (8 classes) — TableauMonitor, CountingMonitor, TestRecord, Timer, TimerWithPause, MemoryConsumptionMonitor, TableauMonitorFork, TableauMonitorForwarder
- [x] **Tableau engine** (15+ files) — Tableau, Node, ClashManager, MergingManager, BranchingPoint, DisjunctionBranchingPoint, DependencySet, PermanentDependencySet, UnionDependencySet, DependencySetFactory, InterruptFlag, HyperresolutionManager, DLClauseEvaluator (bytecode VM, 15 workers), DatatypeManager, DescriptionGraphManager, ExistentialExpansionManager, NominalIntroductionManager, GroundDisjunction, GroundDisjunctionHeader, ExtensionManager, ExtensionTable variants, TupleTable, TupleIndex
- [x] **Blocking strategies** (13 files) — AncestorBlocking, AnywhereBlocking, AnywhereValidatedBlocking, DirectBlockingChecker, PairWiseDirectBlockingChecker, SingleDirectBlockingChecker, ValidatedPairwiseDirectBlockingChecker, ValidatedSingleDirectBlockingChecker, BlockingSignature, BlockingSignatureCache, BlockingValidator, SetFactory
- [x] **Hierarchy classification** (12 files) — Hierarchy, HierarchyNode, HierarchySearch, DeterministicClassification (Tarjan's SCC), QuasiOrderClassification, QuasiOrderClassificationForRoles, RoleElementManager, InstanceManager, ClassificationProgressMonitor, HierarchyPrinterFSS, HierarchyDumperFSS, AtomicConceptElement
- [x] **Existentials** (4 files) — AbstractExpansionStrategy, ExistentialExpansionStrategy, CreationOrderStrategy, IndividualReuseStrategy
- [x] **Reasoner API** — 948-line Reasoner class with OWLReasoner-style interface
- [x] **Entailment checker** — batch entailment checking
- [x] **CLI** — 7 subcommands (classify, realize, consistent, entails, query, stats, dump-clauses)
- [x] **Structural data structures** (3 files) — NormalizedAxioms, OWLAxiomsExpressivity, OWLClausification (843 lines)
- [x] **Tests** — 415/425 tests passing
- [x] **CI** — GitHub Actions (ruff, mypy, pytest on Python 3.10–3.13)
- [x] **Docs** — README with EYE comparison, brainstorm.md, sprint.md, spec.md, audit.md, status.md

## Known Issues 🐛

### Critical (affecting correctness)
1. **apply_dl_clauses binary/ternary tuple confusion** — The hyperresolution manager's apply_dl_clauses treats all delta_old tuples as ternary (role assertions with 2 nodes), but binary tuples (concept assertions with 1 node) have a different structure. This prevents the DL clause fire-and-derive mechanism from working correctly.

### Minor
2. **10 failing tests** — 8 integration tests (due to #1), 2 tableau unit tests (branching point, hyperresolution)
3. **F821 ruff ignore** — TYPE_CHECKING imports for Node/Tableau need systematic cleanup across blocking/existentials/tableau modules

## Pending ⏳

- [ ] **Fix apply_dl_clauses** — Separate binary and ternary tuple processing paths
- [ ] **ExpressionManager** — NNF + simplification (~560 Java lines)
- [ ] **OWLNormalization** — OWL axioms → normalized disjunctions (~1,400 Java lines, requires OWL API parser)
- [ ] **BuiltInPropertyManager** — top/bottom property axiomatization (~270 Java lines)
- [ ] **ObjectPropertyInclusionManager** — automata for non-simple properties (~840 Java lines, depends on rationals library)
- [ ] **ReducedABoxOnlyClausification** — incremental ABox clausification (~210 Java lines)
- [ ] **OWL ontology parser** — RDF/XML or FSS reader

## Metrics

| Metric | Value |
|---|---|
| Total commits | 12 |
| Python source files | 88 |
| Test files | 7 |
| Total source lines | ~28,000 |
| Total test lines | ~4,500 |
| **Total lines** | **~32,500** |
| Tests | **415 passing, 10 failing** |
| Ruff errors | **0** |

## Dependency Chain

```
Model → Datatypes → Configuration → Monitors
  ↓         ↓           ↓              ↓
Tableau ← Blocking ← Existentials ← Graph utils
  ↓         ↓            ↓              ↓
Hierarchy → Reasoner → CLI
  ↓
Structural (NormalizedAxioms, OWLClausification, Expressivity)
  ↓
OWLNormalization → BuiltInPropertyManager → ObjectPropertyInclusionManager (pending)
```

## Next Priorities

1. **Fix apply_dl_clauses** — The critical blocker for all tableau reasoning
2. **ExpressionManager** — NNF + simplification (needed for OWLNormalization)
3. **OWLNormalization** — the largest remaining piece (~1,400 lines)
4. **OWL ontology parser** — RDF/XML or FSS reader
