# Status: pyhermit Full Semantic Correctness (Sprint 2)

## Checklist

- [x] **Step 1** — Add `AtMostConcept` to `src/hermit/model/__init__.py` with `accept()`, `create()`, exported from `hermit.model`
- [x] **Step 2** — Add `visit_at_most_concept()` to `NormalizedAxiomClausifier` in `src/hermit/structural/owl_clausification.py`; emit pairwise inequality DL clauses
- [x] **Step 3** — Fix `_owl_expr_to_internal()` in `normalized_axioms.py`: `OWLObjectMaxCardinality` → `AtMostConcept`; `OWLObjectExactCardinality` → `[AtLeastConcept, AtMostConcept]`; remove synthetic approximations
- [x] **Step 4** — Emit two-variable DL clauses for `∀R.C` in `OWLNormalization._process_sub_class_of()`; add `direct_dl_clauses: list[DLClause]` to `NormalizedAxioms`; consume in `OWLClausification.clausify()`
- [x] **Step 5** — Fix `¬(complex)` via NNF push-in: `OWLObjectComplementOf(complex)` → correct NNF expansion instead of synthetic hash concept
- [x] **Step 6** — Add `AtMostConcept` non-simplicity check to `ObjectPropertyInclusionManager._check_concept_inclusions_for_non_simple()`
- [x] **Step 7** — Add OWL 2 conformance tests in `tests/test_conformance.py` using `koala.owl` (≥6 tests, guarded by `pytest.importorskip("owlready2")`)
- [x] **Step 8** — Add `TestAllValuesFrom` (≥4 tests) and `TestMaxCardinality` (≥4 tests) to `tests/test_correctness.py`; remove `TestUniversalRestrictionLimitation`
- [ ] **Step 9** — Fix mypy errors in `src/hermit/structural/` files; remove their entries from `[[tool.mypy.overrides]]` in `pyproject.toml`
- [ ] **Step 10** — Full validation: `mypy --strict src/hermit/structural/` exits 0, `ruff check` exits 0, `pytest` 0 failures; bump version `0.2.0` → `0.3.0`

## Blockers

<!-- populated if something is stuck -->
