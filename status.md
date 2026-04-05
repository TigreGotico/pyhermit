# pyhermit Project Status

## Completed ✅

- [x] **Model layer** (1,779 lines) — 30 DL classes: Term, Individual, Variable, Constant, Concept, LiteralConcept, AtomicConcept, AtomicNegationConcept, ExistentialConcept, AtLeast, AtLeastConcept, AtLeastDataRange, ExistsDescriptionGraph, Role, AtomicRole, InverseRole, Atom, DLClause, Equality, Inequality, AnnotatedEquality, NodeIDLessEqualThan, NodeIDsAscendingOrEqual, DataRange, AtomicDataRange, AtomicNegationDataRange, DatatypeRestriction, InternalDatatype, DescriptionGraph, DLOntology
- [x] **Datatype handlers** (11 handlers, 32 IRIs) — owlreal/decimal/integer (BigRational), double, float, datetime, boolean, anyURI, xml:literal, rdf:PlainLiteral, base64Binary, hexBinary
- [x] **Configuration** — 5 enums, all defaults matching Java, clone()
- [x] **Monitors** (8 classes) — TableauMonitor, CountingMonitor, TestRecord, Timer, TimerWithPause, MemoryConsumptionMonitor, TableauMonitorFork, TableauMonitorForwarder
- [x] **Tableau engine** (15 files) — Tableau, Node, NodeType, ExtensionManager, ClashManager, MergingManager, BranchingPoint, DisjunctionBranchingPoint, DependencySet, PermanentDependencySet, UnionDependencySet, DependencySetFactory, InterruptFlag, InterruptCurrentTaskException, ReasoningTaskDescription
- [x] **Tableau sub-modules** (14 files) — HyperresolutionManager, DLClauseEvaluator (bytecode VM, 15 workers), DatatypeManager, DescriptionGraphManager, ExistentialExpansionManager, NominalIntroductionManager, GroundDisjunction, GroundDisjunctionHeader, ExtensionTable variants, TupleTable, TupleIndex
- [x] **Blocking strategies** (13 files) — AncestorBlocking, AnywhereBlocking, AnywhereValidatedBlocking, BlockingSignature, BlockingSignatureCache, BlockingValidator, DirectBlockingChecker, PairWiseDirectBlockingChecker, SingleDirectBlockingChecker, ValidatedPairwiseDirectBlockingChecker, ValidatedSingleDirectBlockingChecker, SetFactory
- [x] **Hierarchy classification** (12 files) — Hierarchy, HierarchyNode, HierarchySearch, DeterministicClassification (Tarjan's SCC), QuasiOrderClassification, QuasiOrderClassificationForRoles, RoleElementManager, InstanceManager, ClassificationProgressMonitor, HierarchyPrinterFSS, HierarchyDumperFSS, AtomicConceptElement
- [x] **Existentials** (4 files) — AbstractExpansionStrategy, ExistentialExpansionStrategy, CreationOrderStrategy, IndividualReuseStrategy
- [x] **Reasoner API** — 948-line Reasoner class with OWLReasoner-style interface
- [x] **Entailment checker** — batch entailment checking
- [x] **CLI** — 7 subcommands (classify, realize, consistent, entails, query, stats, dump-clauses)
- [x] **Structural data structures** (3 files) — NormalizedAxioms, OWLAxiomsExpressivity, OWLClausification
- [x] **Tests** — 350 tests (test_model.py: 149, test_datatypes.py: 86, test_configuration.py: 40, test_monitor.py: 75)
- [x] **CI** — GitHub Actions (ruff, mypy, pytest on Python 3.10–3.13)
- [x] **Docs** — README with EYE comparison, brainstorm.md, sprint.md, spec.md, audit.md

## In Progress 🔄

- [ ] **ExpressionManager** — NNF (negation normal form) and structural simplification for class expressions and data ranges

## Pending ⏳

- [ ] **OWLNormalization** — converts OWL axioms to normalized disjunctions (~1,400 Java lines). Requires OWL API parser or equivalent.
- [ ] **BuiltInPropertyManager** — axiomatizes top/bottom properties (~270 Java lines)
- [ ] **ObjectPropertyInclusionManager** — builds automata for non-simple properties (~840 Java lines, depends on rationals library)
- [ ] **ReducedABoxOnlyClausification** — incremental ABox clausification (~210 Java lines)
- [ ] **Integration tests** — end-to-end tableau + classification tests with real ontologies
- [ ] **OWL ontology parser** — RDF/XML and FSS parser for input ontologies

## Metrics

| Metric | Value |
|---|---|
| Total commits | 6 |
| Python source files | 88 |
| Test files | 4 |
| Total source lines | ~28,000 |
| Total test lines | ~2,700 |
| Tests | 350 (all passing) |
| Ruff errors | 0 |
| Mypy strict (model) | 0 |

## Dependency Chain

```
Model → Datatypes → Configuration → Monitors
  ↓         ↓           ↓              ↓
Tableau ← Blocking ← Existentials ← Graph utils
  ↓
Hierarchy → Reasoner → CLI
  ↓
Structural (NormalizedAxioms, OWLClausification, Expressivity) ← in progress
  ↓
OWLNormalization → BuiltInPropertyManager → ObjectPropertyInclusionManager (pending)
```

## Next Priorities

1. **Integration tests** — Build DLOntology manually from DLClause + facts, run Reasoner, verify classification
2. **ExpressionManager** — NNF + simplification (needed for OWLNormalization)
3. **OWLNormalization** — the largest remaining piece (~1,400 lines)
4. **OWL ontology parser** — RDF/XML or FSS reader to feed into normalization
