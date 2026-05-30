# 08 — Codebase Map

A module-by-module guide to `src/hermit/`, tying each file to the algorithm it
implements (the chapters above) and to its Java HermiT counterpart. pyhermit is a
**structural port**: package layout, class decomposition, and even field names
(Java camelCase, `m_` prefix) are preserved, so this map doubles as a map of Java
HermiT. Java package `org.semanticweb.HermiT.*`; pyhermit package `hermit.*`.

## 1. Data flow at a glance

```
 file ──parser──▶ [OWLAxiom] ──normalize──▶ NormalizedAxioms ──clausify──▶ DLOntology
                                                                              │
                                                       Reasoner ◀─────────────┘
                                                          │ builds & drives
                                                          ▼
                                       Tableau (engine)  ──uses──▶ ExtensionManager (tables)
                                          │                        DependencySetFactory (deps)
                                          │                        HyperresolutionManager (clauses)
                                          │                        ExistentialExpansion (∃)
                                          │                        BlockingStrategy (termination)
                                          │                        DatatypeManager (data)
                                          ▼
                                   satisfiable? ──▶ hierarchy/ (classify, instances) ──▶ answers
```

## 2. Preprocessing: parse → normalize → clausify (Ch. 02)

| File | Role | Java counterpart |
|------|------|------------------|
| `parser.py` | `load_ontology` / `load_ontology_from_string`: dispatch a document by syntax to a reader. | (replaces the OWL API loader) |
| `rdfxml.py` | `parse_rdfxml` — stdlib RDF/XML → triples. | OWL API RDF parser |
| `owl_rdf.py` | `map_triples_to_axioms` — RDF triples → `OWLAxiom`s (OWL-2-from-RDF mapping). | OWL API RDF→axiom mapper |
| `fss.py` | `parse_functional_syntax` — Functional-Style Syntax reader. | OWL API FSS parser |
| `owlxml.py` | `parse_owlxml` — OWL/XML reader. | OWL API OWL/XML parser |
| `owl_model/` | The `OWLAxiom` / `OWLClassExpression` object model the readers emit. | `org.semanticweb.owlapi.model` (internalised) |
| `structural/expression_manager.py` | `ExpressionManager.get_nnf` — negation normal form. | `structural.OWLNormalization`'s NNF helpers |
| `structural/owl_normalization.py` | `OWLNormalization.normalize` — NNF + structural transformation → `NormalizedAxioms`. | `structural.OWLNormalization` |
| `structural/normalized_axioms.py` | `NormalizedAxioms` container (`concept_inclusions`, RBox, ABox, flags). | `structural.OWLAxioms` |
| `structural/owl_clausification.py` | `OWLClausification.clausify` + `NormalizedAxiomClausifier` visitor → `DLOntology` of DL-clauses. | `structural.OWLClausification` |
| `structural/object_property_inclusion_manager.py` | Detects non-simple roles; enforces OWL 2 simplicity (`ValueError`). | `structural.ObjectPropertyInclusionManager` |
| `structural/owl_axioms_expressivity.py`, `builtin_property_manager.py` | Expressivity flags; built-in (top/bottom) roles. | corresponding HermiT helpers |
| `model/__init__.py` | The internal logic: `AtomicConcept`, `AtomicRole`, `InverseRole`, `Atom`, `DLClause`, `DLOntology`, existential/cardinality concepts, `Equality`/`Inequality`. | `org.semanticweb.HermiT.model.*` |

## 3. The tableau engine (Ch. 03, 05) — `tableau/`

| File | Role | Chapter |
|------|------|---------|
| `tableau.py` | `Tableau`: the engine. `is_satisfiable`, `_run_calculus`, `_do_iteration` (saturate → expand → branch → backtrack), node creation, `_backtrack_to`, `merge_node`. | 03, 05 |
| `extension_manager.py` | `ExtensionManager` + `ExtensionTableWithTupleIndexes` + `TupleTable`: the assertion tables, the **delta ring** (`propagate_delta_new`, `branching_point_pushed`, `backtrack`), `add_tuple`, `contains_tuple`, clash recording (`set_clash`). | 03 |
| `clash_manager.py` | `ClashManager`: detects `C/¬C`, `r/¬r` clashes as tuples are added. | 03 |
| `hyperresolution_manager.py` | `HyperresolutionManager`: compiles DL-clauses to worker bytecode; `apply_dl_clauses`. | 03 |
| `dl_clause_evaluator.py` | `DLClauseEvaluator` + `Worker` VM: matches clause bodies, derives heads (`DeriveUnary/BinaryFact`), records `SetClash` (empty head) or a `GroundDisjunction` (multi head). | 03 |
| `ground_disjunction.py`, `ground_disjunction_header.py` | A pending head disjunction and its cached header (`is_satisfied`, `add_disjunct_to_tableau`, sorted disjunct indexes). | 03 |
| `branching_point.py`, `disjunction_branching_point.py` | `BranchingPoint` snapshot; `DisjunctionBranchingPoint.start_next_choice` (try next disjunct, negate tried ones). | 05 |
| `dependency_set.py` | `DependencySet` interface (`contains_branching_point`, `is_empty`, `get_maximum_branching_point`). | 05 |
| `permanent_dependency_set.py` | `PermanentDependencySet`: immutable interned descending linked list; `is`-equality. | 05 |
| `union_dependency_set.py` | `UnionDependencySet`: transient union-of-constituents during a derivation. | 05 |
| `dependency_set_factory.py` | `DependencySetFactory`: interns permanent sets; `add_branching_point`, `union_with`, `get_permanent`; `add_usage`/`remove_usage`/`remove_unused_sets` are **no-ops** (GC reclaims). | 05 |
| `merging_manager.py` | `MergingManager`: the merge rule — when `a ≈ b` is derived, merge nodes (copy labels, pick survivor by node type). | 03 |
| `nominal_introduction_manager.py` | `NominalIntroductionManager`: the NI rule for nominals `{a}` / annotated equalities. | 01 (O), 03 |
| `description_graph_manager.py` | `DescriptionGraphManager`: description-graph (structured-object) constraints. | — |
| `datatype_manager.py` | `DatatypeManager`: D-conjunctions, value-space intersection, datatype clashes. | 06 |
| `node.py`, `node_type.py` | `Node` (label counters, parent, `m_blocking_object`, `get_canonical_node`) and `NodeType` (named / NI / tree / concrete / root-constant / graph). | 03, 04 |
| `interrupt_flag.py`, `interrupt_current_task_exception.py` | Cooperative cancellation of long runs. | `monitor`/`Tableau` interrupts |
| `reasoning_task_description.py` | Human-readable labels for the current task (monitoring/logging). | `tableau.ReasoningTaskDescription` |
| `tuple_index.py`, `tuple_table.py`, `tuple_table_full_index.py`, `extension_table.py`, `extension_table_with_tuple_indexes.py`, `extension_table_with_full_index.py` | Standalone/index helpers and re-export shims. The **active** extension-table implementation is inline in `extension_manager.py`; `contains_tuple` there is a **linear scan** (see audit §2.1). | `tableau.ExtensionTable*` |

## 4. Existential expansion (Ch. 03) — `existentials/`

| File | Role |
|------|------|
| `existential_expansion_strategy.py` | `ExistentialExpansionStrategy` interface (order + node introduction). |
| `abstract_expansion_strategy.py` | `AbstractExpansionStrategy` shared machinery. |
| `creation_order_strategy.py` | `CreationOrderStrategy` — expand in creation order (default). |
| `individual_reuse_strategy.py` | `IndividualReuseStrategy` — reuse individuals to shrink models. |

## 5. Blocking (Ch. 04) — `blocking/`

| File | Role |
|------|------|
| `blocking_strategy.py` | `BlockingStrategy` interface (`compute_blocking`). |
| `anywhere_blocking.py` | `AnywhereBlocking` (default scope) + `_BlockersCache`. |
| `ancestor_blocking.py` | `AncestorBlocking` (ancestors-only scope). |
| `direct_blocking_checker.py` | `DirectBlockingChecker` interface (label-match criterion). |
| `single_direct_blocking_checker.py` | `SingleDirectBlockingChecker` (no inverses). |
| `pairwise_direct_blocking_checker.py` | `PairWiseDirectBlockingChecker` (with inverses). |
| `validated_*`, `anywhere_validated_blocking.py`, `blocking_validator.py` | Validated blocking for SROIQ (`BlockingValidator` checks `≤n`/inverse obligations per Y-variable). |
| `blocking_signature.py`, `blocking_signature_cache.py`, `set_factory.py` | Signature caching support. |

## 6. Classification & queries (Ch. 07) — `hierarchy/`, `datalog/`

| File | Role |
|------|------|
| `hierarchy/quasi_order_classification.py` | `QuasiOrderClassification` — known/possible subsumption graphs, enhanced-traversal, model reuse. |
| `hierarchy/quasi_order_classification_for_roles.py` | Same for roles. |
| `hierarchy/deterministic_classification.py` | `DeterministicClassification` — Tarjan SCC `build_hierarchy`; `classify()` delegates to quasi-order (audit §2.2). |
| `hierarchy/hierarchy.py`, `hierarchy_node.py`, `hierarchy_search.py` | The class/role `Hierarchy`, its nodes, search. |
| `hierarchy/instance_manager.py` | `InstanceManager` — instance realization via saturated model + hierarchy propagation. |
| `hierarchy/atomic_concept_element.py`, `role_element_manager.py`, `classification_progress_monitor.py`, `hierarchy_printer_fss.py`, `hierarchy_dumper_fss.py` | Element wrappers, progress, FSS dump/print. |
| `datalog/__init__.py` | `Query.evaluate` — nested-loop join for conjunctive queries (audit §5.1). |
| `graph/__init__.py` | `Graph` used by the classifier. |

## 7. Top-level orchestration & support

| File | Role |
|------|------|
| `reasoner.py` | `Reasoner` — public API: `is_consistent`, `is_sub_class_of`, `has_type`, `get_instances`, `classify_*`, `precompute_inferences`. (Java `Reasoner`, minus the OWL API.) |
| `entailment_checker.py` | `EntailmentChecker.entails(...)` — reduces axiom-entailment to a tableau run. |
| `configuration.py` | `Configuration` — blocking type/strategy, signature cache, etc. |
| `protege_reasoner_factory.py` | Protégé plugin factory hook. |
| `datatypes/registry.py` | `DatatypeRegistry`, `DatatypeHandler`, `ValueSpaceSubset` per OWL 2 datatype. |
| `monitor/`, `debugger/` | Tableau monitoring/debugging hooks. |
| `cli/` | Command-line entry. |

## 8. How to read the code alongside the chapters

Start at `Reasoner.is_consistent` (`reasoner.py:333`) → `Tableau.is_satisfiable`
(`tableau.py:451`) → `_do_iteration` (`tableau.py:784`). From there branch into
whichever mechanism you are studying: `apply_dl_clauses`
(`hyperresolution_manager.py`) for derivation, `propagate_delta_new` /
`add_tuple` (`extension_manager.py`) for the delta ring, `start_next_choice`
(`disjunction_branching_point.py`) and `get_maximum_branching_point`
(`permanent_dependency_set.py`) for backjumping, `compute_blocking`
(`anywhere_blocking.py`) for termination. Every claim in chapters 03-07 cites the
exact method; open them side by side.

For where pyhermit's code intentionally differs from Java HermiT, read
[`FAITHFULNESS_AUDIT.md`](../../FAITHFULNESS_AUDIT.md).

---

Previous: [07 — Classification & Queries](07-classification-and-queries.md) ·
Back to the [series index](../README.md).
