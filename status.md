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
- [x] **Tests** — 419 tests passing (350 unit + 69 integration/tableau)
- [x] **CI** — GitHub Actions (ruff, mypy, pytest on Python 3.10–3.13)
- [x] **Docs** — README with EYE comparison, brainstorm.md, sprint.md, spec.md, audit.md, status.md

## In Progress 🔄

- [ ] **Integration test fixes** — 6 tests failing:
  - `TestPropertySubsumption::test_property_hierarchy` — KeyError in Hierarchy.transform
  - `TestABoxReasoning::test_fido_not_cat` — incorrect type inference
  - `TestBottomDetection::*` — A reported satisfiable when A ⊑ B and A ⊑ ¬B
  - `TestBranchingPoint::test_branching_point_creation` — tableau API mismatch

## Pending ⏳

- [ ] **ExpressionManager** — NNF + simplification (~560 Java lines)
- [ ] **OWLNormalization** — OWL axioms → normalized disjunctions (~1,400 Java lines, requires OWL API parser)
- [ ] **BuiltInPropertyManager** — top/bottom property axiomatization (~270 Java lines)
- [ ] **ObjectPropertyInclusionManager** — automata for non-simple properties (~840 Java lines, depends on rationals library)
- [ ] **ReducedABoxOnlyClausification** — incremental ABox clausification (~210 Java lines)
- [ ] **OWL ontology parser** — RDF/XML or FSS reader

## Metrics

| Metric | Value |
|---|---|
| Total commits | 8 |
| Python source files | 88 |
| Test files | 7 |
| Total source lines | 27,963 |
| Total test lines | 4,467 |
| **Total lines** | **32,430** |
| Tests | **419 passing, 6 failing** |
| Ruff errors | **0** |
| Mypy strict (model) | **0** |

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

1. **Fix 6 failing integration tests** — semantic bugs in tableau reasoning
2. **ExpressionManager** — NNF + simplification (needed for OWLNormalization)
3. **OWLNormalization** — the largest remaining piece (~1,400 lines)
4. **OWL ontology parser** — RDF/XML or FSS reader
