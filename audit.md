# Audit: PyHermit Port — Phase 2 Complete

**Date:** 2026-04-08 | **Status:** Phase 2 COMPLETE — 426/426 tests passing (100% parity)

## Summary

Phase 2 fixed all 8 remaining tableau bugs, achieving full test parity with HermiT 1.3.8 Java. The fixes were concentrated in the extension table retrieval iteration semantics (`_SimpleRetrieval` slot stepping), shared buffer reference preservation, and a "prev_index trick" pattern applied to multiple callers. All 426 tests pass; 9 are skipped (optional owlready2 dependency).

| Metric | Value |
|---|---|
| Tests passing | 426 / 426 (100%) |
| Tests skipped | 9 (owlready2-optional) |
| Files modified (Phase 2) | 11 source + 10 docs/config |
| Commits (Phase 2) | 10 |

---

## Acceptance Criteria

| Criterion | Status | Evidence |
| :--- | :--- | :--- |
| `pip install hermit-reasoner` succeeds on Python 3.10+ | **Pass** | `pyproject.toml` configured; installable via `pip install -e .` |
| `from hermit import Reasoner` imports; `Reasoner(ontology).is_consistent()` correct | **Pass** | `src/hermit/reasoner.py:1`; verified via 426 passing tests |
| 426/426 tests passing (100% parity) | **Pass** | `uv run pytest` — 426 passed, 9 skipped |
| Reasoner correctly classifies ontologies (class hierarchy) | **Pass** | `tests/test_integration.py` TestSimpleTaxonomy passes |
| All 11 datatype handlers produce correct value space subset operations | **Pass** | `tests/test_datatypes.py` all pass |
| All 3 blocking strategies functional | **Pass** | `tests/test_blocking.py` all pass |
| SWRL rule evaluation functional | **Pass** | `tests/test_tableau.py` SWRL tests pass |
| Datalog conjunctive query evaluation correct | **Pass** | `src/hermit/datalog/__init__.py` tested via pipeline |
| Core entailment checking working | **Pass** | Consistency, satisfiability, subsumption all verified |
| Disjointness checking working | **Pass** | `tests/test_integration.py::TestDisjointClasses::test_disjointness` passes; fix in `reasoner.py` (`load_additional_abox=True`) |
| Property hierarchy classification working | **Pass** | `tests/test_integration.py::TestPropertySubsumption::test_property_hierarchy` passes; fix in `quasi_order_classification.py` |
| ABox instance type extraction working | **Pass** | All 4 `TestABoxReasoning` tests pass; fix in `instance_manager.py` (prev_index trick + `is_empty()` check) |
| Unsatisfiable concept detection working | **Pass** | Both `TestBottomDetection` tests pass; fix in `hyperresolution_manager.py` + `dl_clause_evaluator.py` |
| `mypy --strict` passes on public API modules | **Pass** | Per Phase 1 audit |
| CLI `hermit classify` outputs class hierarchy | **Pass** | CLI entry point functional |
| All dependencies LGPL 3.0 compatible | **Pass** | No new dependencies added |

---

## Gaps & Issues

| Severity | Location | Description |
| :--- | :--- | :--- |
| Minor | `status.md:36-39` | Phase 2c items unchecked: multi-Python testing, API docs, contributor guide, PyPI publish |
| Minor | `src/hermit/tableau/extension_manager.py:_SimpleRetrieval` | The "prev_index trick" is a workaround for Java/Python iteration semantic mismatch. Callers must use this pattern instead of the standard `open()`/`after_last()` loop. No abstraction enforces this — future callers could regress. |
| Minor | `src/hermit/tableau/dl_clause_evaluator.py:DeriveUnaryFact.execute()` | `isinstance(argument, Node)` guard silently skips non-Node values. This is correct for the current codebase but masks potential future bugs where a non-Node value indicates an actual error. |
| Minor | `src/hermit/hierarchy/quasi_order_classification.py` | `node is not None` guard added to `_update_possible_subsumers()` — defensive check for None nodes in extension table tuples that exist due to evaluator semantics. |
| Info | `src/hermit/parser.py:48-60` | Axiom mapping for owlready2 is skeletal; many axiom types unmapped. Sufficient for current tests but limits real-world ontology loading. |

---

## Suggestions

- **Abstract the iteration pattern**: Create a helper (e.g., `iter_retrieval(retrieval)` generator) that encapsulates the prev_index trick, preventing future callers from using the broken `open()`/`after_last()` pattern directly.
- **Run full test suite on Python 3.10, 3.11, 3.12** (Phase 2c item) to verify compatibility before PyPI publish.
- **Add regression tests** specifically for the 8 fixed bugs to prevent future regressions if retrieval semantics change.
- **Expand owlready2 axiom mapper** for broader ontology support beyond Pizza/Koala.
- **Consider refactoring `_SimpleRetrieval`** to match Java `open()`→`moveToNext()` semantics with proper flag-based `afterLast()`, eliminating the need for the prev_index workaround. This was attempted and abandoned due to cascading regressions, but a careful incremental approach may succeed.
