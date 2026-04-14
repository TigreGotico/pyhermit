# Status: Fix pyhermit — Complete Faithful Port of HermiT

## Checklist

- [x] Step 1 — Fix normalizer: asymmetric, reflexive, irreflexive, disjoint-object-properties → correct `NormalizedAxioms` fields (`src/hermit/structural/owl_normalization.py`)
- [x] Step 2 — Fix normalizer: sub-data-property and disjoint-data-property → `data_property_inclusions` / `disjoint_data_properties` (`src/hermit/structural/owl_normalization.py`)
- [x] Step 3 — Fix normalizer: symmetric object property → simple inclusion `(R, R⁻)` in `simple_object_property_inclusions` (`src/hermit/structural/owl_normalization.py`)
- [x] Step 4 — Fix normalizer: functional and inverse-functional object properties → DL clauses in `direct_dl_clauses` (`src/hermit/structural/owl_normalization.py`)
- [x] Step 5 — Fix `DLOntology._has_nominals`: detect nominals from `positive_facts` and `dl_clauses` content (`src/hermit/model/__init__.py:2005`)
- [x] Step 6 — Fix blocking validator: accumulate all roles per Y-variable in `DLClauseInfo.__init__` (`src/hermit/blocking/blocking_validator.py:274,280`)
- [x] Step 7 — Fix `DoubleValueSpaceSubset.complement()`: return correct complement for finite value sets (`src/hermit/datatypes/doublenum/__init__.py:45`)
- [x] Step 8 — Fix merging manager: copy n-ary description-graph tuples during node merge (`src/hermit/tableau/merging_manager.py`) — already implemented via `DescriptionGraphManager.merge_graphs`
- [x] Step 9 — Implement `DeterministicClassification.classify()`: delegates to QuasiOrderClassification (correct fallback) (`src/hermit/hierarchy/deterministic_classification.py:45–56`)
- [x] Step 10 — Implement `Query.evaluate()`: conjunctive query answering with nested-loop join (`src/hermit/datalog/__init__.py:172–184`)
- [x] Step 11 — Write regression tests for all 12 acceptance criteria in `spec.md`

## Blockers
<!-- populated by /implement-task if something is stuck -->
