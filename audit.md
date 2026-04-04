# Audit: Python Port of HermiT OWL 2 DL Reasoner

## Summary

The project has scaffolded the pyhermit repository with a **complete model layer** (~1,778 lines covering 30 model classes) and **all 11 datatype handlers** (~233 lines covering 32 datatype IRIs). The code is ruff-clean and the module imports correctly. However, this is only **2 of 16 functional requirement groups** from the spec — the tableau engine, reasoner API, CLI, debugger, monitors, blocking strategies, hierarchy classification, SWRL/Datalog, structural layer, and test suite are all empty stubs. There are **50 mypy errors** in the model layer and **zero tests**.

| Metric | Value |
|---|---|
| Total source files (non-stub) | 14 (model: 1, datatypes: 10, registry: 1, __init__: 2) |
| Total source lines | ~2,011 |
| Model classes implemented | 30 / 30 (model layer complete) |
| Datatype handlers implemented | 11 / 11 (all registered) |
| Functional requirement groups done | 2 / 16 (FR1 Model, FR4 Datatypes) |
| mypy --strict errors | 50 (in model/__init__.py) |
| Test files | 0 |
| Test coverage | 0% |
| Commits | 2 |

---

## Acceptance Criteria

| Criterion from spec.md | Status | Evidence |
|---|---|---|
| `pip install hermit-reasoner` succeeds on Python 3.10+ with zero JVM dependency | **Partial** | `pyproject.toml` configured with hatchling, `uv pip install -e ".[dev]"` works locally. Not yet published on PyPI. No wheels built. |
| `from hermit import Reasoner` imports; `isConsistent()` works | **Fail** | `hermit/__init__.py` uses lazy `__getattr__` — `Reasoner` module doesn't exist yet (`reasoner.py` not created). Import succeeds but `Reasoner()` raises `ModuleNotFoundError`. |
| All 60 ported test classes pass with 100% parity | **Fail** | Zero test files exist. `tests/` directory has only subdirectories (`datatypes/`, `resources/`, `structural/`, `tableau/`) with no `.py` files. |
| Pizza ontology classification parity | **Fail** | No reasoner, no tableau, no ontology parser. |
| Wine ontology classification parity | **Fail** | Same. |
| All 11 datatype handlers produce correct value space subset ops | **Partial** | All 11 handlers registered (32 IRIs). Intersection/complement implemented but **not tested**. Facet handling in owlreal supports min/max inclusive/exclusive only; `pattern`, `length`, `totalDigits`, `fractionDigits`, `langRange` facets are **not implemented**. |
| All 3 blocking strategies produce correct tableau saturation | **Fail** | `src/hermit/blocking/__init__.py` is a 1-line stub. |
| SWRL rule evaluation | **Fail** | No SWRL code. |
| Datalog conjunctive query evaluation | **Fail** | `src/hermit/datalog/__init__.py` is a 1-line stub. |
| Entailment checking for W3C test cases | **Fail** | No entailment checker. |
| `mypy --strict` passes with zero errors | **Fail** | 50 errors in `model/__init__.py`: union-attr (4), override signature mismatch (1), no-any-return (2), missing type args (1), and ~42 more. |
| `pytest --cov=hermit` ≥ 85% | **Fail** | 0 tests, 0% coverage. |
| CLI `hermit classify <ontology>` | **Fail** | `src/hermit/cli/__init__.py` is a 1-line stub. |
| Interactive debugger | **Fail** | `src/hermit/debugger/__init__.py` is a 1-line stub. |
| Sphinx/MkDocs documentation | **Partial** | README.md has quickstart example. No API reference, architecture doc, or contributor guide. |
| GitHub Actions CI | **Fail** | No `.github/workflows/` directory. |
| Dependencies audited for LGPL compatibility | **Partial** | LICENSE and LICENSE.LESSER included. `pyproject.toml` has zero runtime dependencies (pure Python). No transitive dependency audit document. |

---

## Gaps & Issues

### Functional Requirements with No Code (14 of 16 groups)

| Spec Section | Requirement | Status |
|---|---|---|
| FR1.2 | OWL ontology parsing (RDF/XML, FSS) | **Missing** |
| FR1.3 | Programmatic ontology construction | **Partial** — `DLOntology` exists but accepts raw DL clauses, not OWL axioms |
| FR1.4 | Adapter interface for owlready2/rdflib | **Missing** |
| FR2 | OWL Normalization & Clausification | **Missing** — `structural/__init__.py` is stub |
| FR3 | Tableau Engine (3.1–3.9) | **Missing** — `tableau/__init__.py` is stub |
| FR5 | Hierarchy Classification (5.1–5.6) | **Missing** — `hierarchy/__init__.py` is stub |
| FR6 | Instance Management (6.1–6.5) | **Missing** |
| FR7 | SWRL Rule Support (7.1–7.4) | **Missing** |
| FR8 | Datalog Query Engine (8.1–8.3) | **Missing** |
| FR9 | Entailment Checking (9.1–9.4) | **Missing** |
| FR10 | Reasoner API (10.1–10.5) | **Missing** — `reasoner.py` doesn't exist |
| FR11 | CLI Interface (11.1–11.4) | **Missing** |
| FR12 | Debugger (12.1–12.3) | **Missing** |
| FR13 | Monitoring & Observability (13.1–13.3) | **Missing** |
| FR14 | Test Suite (14.1–14.5) | **Missing** — 0 test files |
| FR15.3 | Publish on PyPI | **Not done** |
| FR16.2 | API reference docs | **Missing** |
| FR16.3 | Architecture overview | **Missing** |
| FR16.4 | Contributor guide | **Missing** |
| FR16.5 | Example scripts | **Missing** |

### Code Quality Issues

| Severity | Location | Description |
|---|---|---|
| **Major** | `model/__init__.py:1462` | `DatatypeRestriction.create()` signature incompatible with `AtomicDataRange.create()` (Liskov violation). `DatatypeRestriction` extends `AtomicDataRange` but has a different `create()` signature. This is a design issue — in Java, `DatatypeRestriction` extends `AtomicDataRange` but the factory methods are static, not inherited. In Python, `@classmethod` is inherited. |
| **Major** | `model/__init__.py:171` | `Prefixes.STANDARD` initialized as `None` then set later. All uses of `Prefixes.STANDARD.abbreviate_iri()` trigger mypy `union-attr` errors. Should be a class property or initialized eagerly. |
| **Major** | `model/__init__.py:468-473` | `Constant.create()` silently swallows `DatatypeRegistry.parse_literal` exceptions and stores `None` as `data_value`. This masks datatype errors and will cause downstream failures. |
| **Major** | `datatypes/owlreal/__init__.py:37` | `BigRational.__init__` catches `ValueError` and `ZeroDivisionError` but `Fraction()` can also raise `TypeError` for unhashable types. |
| **Major** | `datatypes/registry.py:118` | `DatatypeRegistry` uses class-level mutable dicts (`_handlers_by_iri`, `_handlers`). These persist across test runs and are not thread-safe. |
| **Minor** | `model/__init__.py:1639` | `DLOntology._data_prop_assertions` typed as bare `dict` instead of `dict[AtomicRole, dict[Individual, set[Constant]]]`. |
| **Minor** | `datatypes/doublenum/__init__.py:36` | `DoubleValueSpaceSubset.complement()` returns `frozenset()` — incorrect semantics (complement of a non-empty set should not be the entire space). |
| **Minor** | `datatypes/floatnum/__init__.py:38` | Same complement issue as double. |
| **Minor** | `datatypes/datetime/__init__.py:38` | `DateTimeValueSpaceSubset.complement()` returns `empty=not self._empty` — incorrect (complement of entire is not just empty/non-empty flip). |
| **Minor** | `model/__init__.py:1` | Model `__init__.py` is 1,778 lines — exceeds recommended module size. Should be split into submodules (`terms.py`, `concepts.py`, `roles.py`, `clauses.py`, `dataranges.py`, `graphs.py`, `ontology.py`). |
| **Minor** | All datatype handlers | `create_value_space_subset()` implementations return "entire space" unconditionally — facet restrictions are ignored for all handlers except owlreal. |
| **Minor** | `datatypes/bool/__init__.py` | `BooleanValueSpaceSubset` stores `frozenset[bool]` but boolean value space is just `{True, False}` — subset operations are correct but the representation is trivial and untested. |
| **Minor** | `model/__init__.py:983` | `DLClause.is_general_concept_inclusion()` has a long conditional chain that's hard to test. The Java version has the same complexity but benefits from Java's pattern matching. Consider extracting to predicate functions. |

### Documentation Gaps

| Gap | Detail |
|---|---|
| No `ARCHITECTURE.md` | The README references it but it doesn't exist. The tableau calculus, blocking strategies, and description graph algorithm need documentation. |
| No `CONTRIBUTING.md` | Essential for a FOSS project — how to port a Java file, run tests, coding conventions. |
| No docstrings on package `__init__.py` stubs | All 9 empty package `__init__.py` files have 1-line docstrings. Should explain what will go there. |
| No inline API docstrings | The model classes have class-level docstrings but no method-level docstrings (e.g., `DLClause.is_general_concept_inclusion()` has no explanation of what constitutes a GCI). |
| No CHANGELOG | The README promises version history tracking. |

---

## Suggestions

1. **Split `model/__init__.py`** into logical submodules (`terms.py`, `concepts.py`, `roles.py`, `clauses.py`, `dataranges.py`, `graphs.py`, `ontology.py`) before it grows further. At 1,778 lines it's already hard to navigate.

2. **Fix `Prefixes.STANDARD`** — Use `__init_subclass__` or a module-level eager initialization so mypy stops flagging union-attr errors.

3. **Write first tests before proceeding** — The datatype handlers (especially `owlreal` with `BigRational` interval arithmetic) are the most testable component right now. Write tests for parsing, subset intersection/complement, and facet handling. This establishes the testing pattern for the rest of the port.

4. **Decide on `Constant.create()` error handling** — Swallowing exceptions silently is dangerous. Either require the caller to handle `MalformedLiteralException`, or provide a `create_unchecked()` fallback.

5. **Create a `status.md`** — Track which of the 16 FR groups are in progress, done, or blocked. This is essential for a multi-thousand-line port.

6. **Port `OWLNormalization` next** — This is the critical path blocker for the reasoner. Without normalization → clausification, the tableau engine has nothing to operate on. The Java `OWLClausification.java` (~2,000 lines) is the single most complex file to port.

7. **Consider `dataclass` for immutable model objects** — `__slots__` + manual `__init__` + `__eq__` + `__hash__` + `__repr__` for each class is verbose and error-prone. Python `@dataclass(frozen=True, slots=True)` (3.10+) generates all of this automatically. This would reduce the model module by ~30% and improve maintainability.

8. **Add `__all__` to all `__init__.py` files** — Currently only `model/__init__.py` and `datatypes/__init__.py` export symbols. The stub packages should declare their intended public API even if empty.

9. **Set up GitHub Actions** — Even with no tests yet, a CI that runs `ruff check`, `mypy --strict`, and `pytest` on every push prevents regression and sets expectations for contributors.

10. **Port test ontologies** — Copy `owl_wg_tests/ontologies/` and `res/` directories from the Java repo into `tests/resources/` so test infrastructure is ready before tests are written.
