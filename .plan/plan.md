# Plan: pyhermit Full Semantic Correctness (Sprint 2)

## Approach

Sprint 1 fixed structural completeness (parser, typed fact lists, non-simplicity validation, test suite).
Sprint 2 fixes **semantic correctness** — the remaining issues that make published answers wrong:

1. `∀R.C` (OWLObjectAllValuesFrom) is approximated with a synthetic concept disconnected from the role.
2. `≤n R.C` / `=n R.C` (MaxCardinality / ExactCardinality) are approximated the same way.
3. The mypy quarantine in `pyproject.toml` hides 1217 real errors; new code should be clean from day one.
4. No end-to-end test loads an actual `.owl` file and asks a reasoning question.

Strategy: add `AtMostConcept` to the model, wire it through clausification, implement universal/max-cardinality DL clause emission, add real `.owl` conformance tests, then surgically fix the quarantined files most worth fixing (leaving the pre-existing Java-port debt under explicit overrides but reducing the quarantine surface).

Do NOT touch the core tableau engine internals. Generate correct DL clauses and let the existing hyperresolution machinery handle them.

## Architecture / Data Flow

```
OWL SubClassOf(A, ∀R.B)
  └─► OWLNormalization._process_sub_class_of()
        └─► detect OWLObjectAllValuesFrom super
        └─► emit DLClause: A(X) ∧ R(X,Y) → B(Y)   [direct_dl_clauses]
              └─► OWLClausification.clausify()
                    └─► DLOntology.add_dl_clause()
                          └─► Tableau hyperresolution (existing, unchanged)

OWL SubClassOf(A, ≤n R.B)
  └─► _owl_expr_to_internal() → AtMostConcept(n, R, B)
        └─► NormalizedAxiomClausifier.visit_at_most_concept()
              └─► emit pairwise inequality DL clauses
                    └─► Tableau (existing, unchanged)
```

## Implementation Steps

1. **Add `AtMostConcept` to `src/hermit/model/__init__.py`**
   - Class `AtMostConcept` with fields `_number: int`, `_on_role: Role`, `_to_concept: LiteralConcept`
   - Factory `create(number, on_role, to_concept)` mirroring `AtLeastConcept`
   - `accept(visitor)` dispatch to `visitor.visit_at_most_concept(self)`
   - Export from `hermit.model`

2. **Add `visit_at_most_concept()` to `NormalizedAxiomClausifier`**
   - Location: `src/hermit/structural/owl_clausification.py`
   - For `≤n R.C`: emit n+1 fresh variables X, Y_0…Y_n; for each pair (Y_i, Y_j) with i<j add body atoms `R(X,Y_i)`, `R(X,Y_j)`, `C(Y_i)`, `C(Y_j)` and head atom `Y_i ≠ Y_j` — standard at-most clausification.
   - For `≤0 R.C`: emit `R(X,Y) ∧ C(Y) → ⊥` (clash).

3. **Fix `_owl_expr_to_internal()` for MaxCardinality and AllValuesFrom**
   - `OWLObjectMaxCardinality(n, R, C)` → `AtMostConcept.create(n, role, filler)` instead of synthetic approximation
   - `OWLObjectExactCardinality(n, R, C)` → intersection of `AtLeastConcept(n,…)` + `AtMostConcept(n,…)` — return a pair and let the inclusion expand to two disjuncts
   - `OWLObjectAllValuesFrom` — remove synthetic approximation; handled via step 4 instead

4. **Emit two-variable DL clauses for `∀R.C` in `OWLNormalization`**
   - In `_process_sub_class_of()`: when `super_class` is `OWLObjectAllValuesFrom(R, C)`, emit `DLClause([C_internal(Y)], [A_internal(X), R_internal(X,Y)])` directly into `normalized_axioms.direct_dl_clauses`
   - Add `direct_dl_clauses: list[DLClause]` field to `NormalizedAxioms`
   - In `OWLClausification.clausify()`: iterate `direct_dl_clauses` and add each to `DLOntology`

5. **Handle `OWLObjectComplementOf` wrapping complex concepts correctly**
   - Current: `¬(∃R.C)` → random-hash synthetic `AtomicConcept`
   - Fix: push complement inward via NNF: `¬(∃R.C)` = `∀R.¬C` (use step 4 path), `¬(A⊓B)` = `¬A⊔¬B`, etc.
   - Add `_nnf(expr)` helper to `normalized_axioms.py` that recurses using OWL model's `get_nnf_class_expression` if available, else manual rules

6. **Add `AtMostConcept` support to `ObjectPropertyInclusionManager`**
   - In `_check_concept_inclusions_for_non_simple()`: detect `AtMostConcept` and check its role for non-simplicity (mirrors current `AtLeastConcept` check)

7. **Add OWL 2 conformance tests using real ontology files**
   - Create `tests/test_conformance.py`
   - Load `tests/ontologies/koala.owl`: assert `KoalaWithPhD ⊑ Koala`, assert `Koala` satisfiable, assert `Pizza` not a subclass of `Koala`
   - Load `tests/ontologies/pizza.owl` if present: assert known subsumption/satisfiability facts
   - Guard each with `pytest.importorskip("owlready2")`
   - Add at least 6 tests total

8. **Add correctness tests for `∀R.C` and `≤n R.C` reasoning**
   - Extend `tests/test_correctness.py` with `TestAllValuesFrom` class (≥4 tests)
   - Extend with `TestMaxCardinality` class (≥4 tests)
   - Remove the `TestUniversalRestrictionLimitation` class (those were documenting the bug — delete after fix)
   - Tests must assert actual True/False answers, not just "no exception"

9. **Fix mypy quarantine: `hermit.structural.*` files**
   - Files: `normalized_axioms.py`, `owl_normalization.py`, `owl_clausification.py`, `builtin_property_manager.py`, `object_property_inclusion_manager.py`
   - These are the files most-modified by sprint 1; they should be clean under `--strict`
   - Remove their entries from `[[tool.mypy.overrides]]` in `pyproject.toml`
   - Fix remaining type errors (expected: modest, since sprint 1 already cleaned most)

10. **Run full validation and bump to 0.3.0**
    - `mypy --strict src/hermit/structural/` exits 0
    - `ruff check src/hermit` exits 0
    - `pytest` 0 failures, 0 skips
    - Bump `pyproject.toml` version `0.2.0` → `0.3.0`
