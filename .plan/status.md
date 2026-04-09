# Status: pyhermit Production Readiness

## Checklist

- [x] **Step 1a** — Add `positive_concept_facts`, `positive_role_facts`, `positive_data_facts` to `NormalizedAxioms` (`src/hermit/structural/normalized_axioms.py`) — already existed
- [x] **Step 1b** — Update `OWLNormalization._process_axiom()` to route axioms to typed fact lists (`src/hermit/structural/owl_normalization.py`)
- [x] **Step 1c** — Update `OWLClausification.clausify()` to consume typed fact lists where appropriate — already reading typed lists; fixed by 1b
- [x] **Step 2** — Remove `# mypy: ignore-errors` from `owl_normalization.py`; confirm `mypy` clean
- [x] **Step 3** — Remove `# mypy: ignore-errors` from `expression_manager.py`
- [x] **Step 4** — Fix or integrate `builtin_property_manager.py` — cleaned up, removed all stale type: ignore comments, mypy clean
- [x] **Step 5** — Remove `# mypy: ignore-errors` from `object_property_inclusion_manager.py`; mypy --strict clean
- [x] **Step 6** — Enhance owlready2 parser: add `_map_class_expression()` recursion; extract restrictions, cardinalities, unions, intersections, complements, nominals from owlready2 objects
- [x] **Step 7** — Investigated `datatype_manager.py:360`: both `pass` statements are correct behaviour (skip internal datatypes like rdfs:Literal). No actual stub to fix.
- [x] **Step 8** — Add `tests/test_correctness.py` with ≥20 reasoning-answer tests covering subsumption via restrictions, cardinality constraints, transitivity, nominals, datatypes; both SAT and UNSAT cases
- [x] **Step 9** — Bump version to `0.2.0`, update `pyproject.toml` classifier to `4 - Beta`, pin owlready2 in optional extras
- [x] **Step 10** — `ruff check` clean (0 errors), `pytest` 0 failures (2274 passed); mypy has 1217 pre-existing errors in 76 files (unchanged from baseline — not regressed by our work)

## Blockers

<!-- populated if something is stuck -->
