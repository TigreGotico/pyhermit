# Plan: Finish the pyhermit Port

## Approach

Work in dependency order: fix blocking bugs first so the existing test suite is green, then
layer in the new components bottom-up (owl_model vendor → ExpressionManager →
OWLNormalization → BuiltInPropertyManager → ObjectPropertyInclusionManager → datalog → parser →
end-to-end wiring). Each step is independently testable and committed before moving on.

The vendored owl_model layer is treated as a read-only copy of owlapy's pure-Python model files
with two mechanical changes: `from owlapy.X` → `from hermit.owl_model.X` and
`pandas.Timedelta` → `datetime.timedelta`. No logic is altered.

For ObjectPropertyInclusionManager a small inline NFA class (`_Automaton`) is
implemented directly in the module — avoids any external automata dependency and keeps
the port self-contained; the Java `rationals.Automaton` API surface needed here is tiny
(add states, add transitions, accepts, initial state).

## Architecture / Data Flow

```
.owl / .ttl file
      │
      ▼
hermit.parser.load_ontology()        ← owlready2 (optional dep)
      │  yields hermit.owl_model.OWLAxiom objects
      ▼
OWLNormalization.processOntology()   ← consumes hermit.owl_model axioms
      │  uses ExpressionManager for NNF/simplification
      │  uses BuiltInPropertyManager to inject top/bottom property axioms
      │  uses ObjectPropertyInclusionManager to axiomatize role chains
      │  produces NormalizedAxioms (hermit.structural types)
      ▼
OWLClausification.clausify()         ← already implemented
      │  produces DLOntology (hermit.model types)
      ▼
Reasoner / Tableau                   ← already implemented
      │
      ├─ Hierarchy classification    ← already implemented
      ├─ Instance management         ← already implemented
      └─ DatalogEngine.materialize() ← new: materializes the ABox
              │
              ▼
         ConjunctiveQuery.evaluate() ← new: query evaluation
```

## Implementation Steps

1. **Fix `DataRange` NameError in `blocking/anywhere_blocking.py`**
   Add missing `from hermit.model import DataRange` import. One-line fix; unblocks
   the 6 ABox/role integration tests and the hyperresolution unit test.

2. **Fix `m_last_tableau_node` AttributeError in `tableau/branching_point.py`**
   Change `tableau.m_last_tableau_node` → `tableau.last_tableau_node` (the property
   already exists under that name). Unblocks `TestBranchingPoint`.

3. **Fix `apply_dl_clauses` binary/ternary tuple split in `tableau/hyperresolution_manager.py`**
   The tuple buffer layout differs by arity:
   - binary tuple (concept assertion): `[predicate, node, dep_set]` — node is at index 1
   - ternary tuple (role assertion): `[predicate, node1, node2, dep_set]` — nodes at 1 & 2
   Dispatch on `delta_old_retrieval._extension_table.m_tuple_arity` (2 vs 3) before
   extracting node positions. Remove all DEBUG print statements.

4. **Vendor `hermit/owl_model/`**
   Copy verbatim from `/mnt/homelab/Workspace/external repos/owlapy/owlapy/`:
   `iri.py`, `owl_object.py`, `meta_classes.py`, `owl_annotation.py`, `owl_datatype.py`,
   `owl_individual.py`, `owl_property.py`, `owl_data_ranges.py`, `owl_axiom.py`,
   `class_expression/__init__.py`, `class_expression/class_expression.py`,
   `class_expression/owl_class.py`, `class_expression/nary_boolean_expression.py`,
   `class_expression/restriction.py`.
   Mechanical changes only:
   - All `from owlapy.` → `from hermit.owl_model.`
   - `owl_literal.py`: `from pandas import Timedelta` removed; all `Timedelta` uses
     replaced with `datetime.timedelta`; `parse_duration` updated accordingly.
   - Add `# vendored from owlapy 1.6.4 — MIT License` header to each file.
   - Write `src/hermit/owl_model/__init__.py` that re-exports the main public symbols.

5. **Implement `structural/ExpressionManager`**
   Port `ExpressionManager.java` (559 lines) to
   `src/hermit/structural/expression_manager.py`.
   Java visitor pattern → Python `singledispatch` functions or `isinstance` dispatch
   (consistent with existing codebase style — inspect `owl_axioms_expressivity.py`
   which already uses `isinstance` dispatch).
   Three public methods: `get_nnf(expr)`, `get_complement_nnf(expr)`,
   `get_simplified(expr)` — each accepting either `OWLClassExpression` or `OWLDataRange`
   from `hermit.owl_model`. Results interned via a `dict` cache keyed by `(type, args)`.
   Add to `hermit.structural.__init__.__all__`.

6. **Implement `structural/OWLNormalization`**
   Port `OWLNormalization.java` (1,388 lines) to
   `src/hermit/structural/owl_normalization.py`.
   Entry point: `OWLNormalization(config, prefixes).process_ontology(axioms)` returning
   `NormalizedAxioms`. The `axioms` parameter is `Iterable[hermit.owl_model.OWLAxiom]`.
   Structural transformation produces fresh `AtomicConcept` definitions when needed
   (tracked in a `_definitions: dict` mapping complex expressions to their definiendum).
   SWRL rules passed through `_RuleNormalizer` (Lloyd-Topor multi-head splitting).
   Uses `ExpressionManager` throughout for NNF rewriting.
   Add to `hermit.structural.__init__.__all__`.

7. **Implement `structural/BuiltInPropertyManager`**
   Port `BuiltInPropertyManager.java` (273 lines) to
   `src/hermit/structural/builtin_property_manager.py`.
   Single public function:
   `axiomatize_builtin_properties(normalized_axioms, skip_top_obj, skip_top_data,
    skip_bot_obj, skip_bot_data) -> None`
   Mutates `normalized_axioms` in-place. Uses an `isinstance`-based `_Checker` to walk
   all concept inclusions, property axioms, and facts to determine which of the four
   built-in properties are actually referenced before injecting axioms.
   Called from `OWLNormalization.process_ontology()` after `_normalize_inclusions()`.
   Add to `hermit.structural.__init__.__all__`.

8. **Implement `structural/ObjectPropertyInclusionManager`**
   Port `ObjectPropertyInclusionManager.java` (844 lines) to
   `src/hermit/structural/object_property_inclusion_manager.py`.
   Implement a minimal `_Automaton` class in the same file: states (int ids), alphabet
   (role expressions), transitions dict, initial/final states, `accepts(word)`.
   Main class: `ObjectPropertyInclusionManager(normalized_axioms, prefixes)`.
   Key methods:
   - `rewrite_negative_object_property_assertions()` — converts negative assertions over
     complex properties to concept assertions with `∀r.¬{b}` fillers.
   - `rewrite_axioms(first_replacement_index)` — validates simple-property constraints,
     replaces `AllValuesFrom` over complex roles with fresh named concepts, builds
     automata for all complex property chains, emits DL clauses from automaton transitions.
   Called from `OWLNormalization.process_ontology()` before final clausification.
   Add to `hermit.structural.__init__.__all__`.

9. **Implement `datalog/` — ConjunctiveQuery, DatalogEngine, QueryResultCollector**
   Port all three Java classes into `src/hermit/datalog/__init__.py`.
   `QueryResultCollector`: abstract base class with `process_result(query, result)`.
   `DatalogEngine(dl_ontology, config)`: lazy `materialize()` builds a `Tableau` with a
   no-op existential strategy; populates `_nodes_to_terms` and `_extension_manager`.
   `ConjunctiveQuery(datalog_engine, body_atoms, answer_terms)`: constructor reorders
   body atoms via `BodyAtomsSwapper`, compiles workers via `DLClauseEvaluator`'s
   `ConjunctionCompiler`; `evaluate(collector)` runs the worker loop.
   `NullExistentialExpansionStrategy`: inner class, no-op expansion, `is_exact=True`.

10. **Implement `hermit/parser.py` — owlready2-backed OWL file parser**
    `load_ontology(path) -> list[OWLAxiom]` in `src/hermit/parser.py`.
    Uses `owlready2.get_ontology(str(path)).load()` to parse `.owl` / `.ttl` files.
    Maps owlready2 class expressions and axioms to `hermit.owl_model` types via a
    `_OwlreadyMapper` class with `isinstance`-dispatch on owlready2 constructs.
    Import guard: `try: import owlready2 except ImportError: raise ImportError(...)`.
    Does not import from `hermit.structural` — pure mapping only.

11. **Wire end-to-end and update `structural/__init__.py`**
    Add `ExpressionManager`, `OWLNormalization`, `BuiltInPropertyManager`,
    `ObjectPropertyInclusionManager` to `hermit.structural.__all__`.
    Add a `load_ontology` convenience re-export to `hermit/__init__.py`.
    Ensure `OWLClausification.clausify()` calls `BuiltInPropertyManager` and
    `ObjectPropertyInclusionManager` before the main clausification loop
    (currently it receives `NormalizedAxioms` directly — this wiring belongs in
    `OWLNormalization.process_ontology()`, not `OWLClausification`).

12. **Add end-to-end integration tests for Pizza and Koala ontologies**
    Download the Pizza and Koala OWL ontologies to `tests/ontologies/`.
    Add `tests/test_end_to_end.py` with tests:
    - `test_pizza_consistent` — `load_ontology("pizza.owl")` → `Reasoner.is_consistent()` is True
    - `test_pizza_subclasses` — `get_sub_classes(owl:Thing)` returns ≥ 100 classes
    - `test_koala_consistent` — same pattern for Koala
    - `test_pizza_instances` — `get_instances(PizzaTopping)` is non-empty
