# Audit: Fix pyhermit — Complete Faithful Port of HermiT

## Summary

All 14 functional requirements from spec.md have been implemented and checked off in status.md. The normalizer, `DLOntology`, blocking validator, double complement, merging manager, `DeterministicClassification`, and `Query.evaluate()` are all fixed or completed. The primary gap is that the regression tests for AC1–AC6 validate only normalizer output fields, not end-to-end reasoner entailments as the acceptance criteria literally specify; AC12 (zero regressions across 3050 tests) cannot be confirmed from source inspection alone.

---

## Acceptance Criteria

| Criterion | Status | Evidence |
| :--- | :--- | :--- |
| AC1 — `owl:FunctionalProperty R` produces `R(a,b) ∧ R(a,c) → b=c` (merged nodes) as entailment | Partial | `owl_normalization.py:204–214` generates correct DL clause with Equality head; `test_correctness.py:268` tests inconsistency via DL clause directly but no OWL-axiom-level end-to-end entailment test exists in the regression suite |
| AC2 — `owl:SymmetricProperty R` and `R(a,b)` entails `R(b,a)` | Partial | `owl_normalization.py:226–234` stores `(R, R⁻)` in `simple_object_property_inclusions`; regression test checks field population only (`test_correctness_regression.py:82–94`), no entailment assertion via reasoner |
| AC3 — `owl:AsymmetricProperty R` with `R(a,b)` and `R(b,a)` reports inconsistency | Partial | `owl_normalization.py:235–238` stores in `asymmetric_object_properties`; regression test checks field (`test_correctness_regression.py:96–104`); no end-to-end clash test with two role assertions |
| AC4 — `owl:ReflexiveProperty R` entails `R(a,a)` for every individual | Partial | `owl_normalization.py:247–250` stores in `reflexive_object_properties`; regression test checks field (`test_correctness_regression.py:106–113`); no end-to-end reflexive entailment test |
| AC5 — `owl:IrreflexiveProperty R` and `R(a,a)` reports inconsistency | Partial | `owl_normalization.py:251–254` stores in `irreflexive_object_properties`; regression test checks field (`test_correctness_regression.py:115–122`); no end-to-end self-loop clash test |
| AC6 — `owl:DisjointObjectProperties(R,S)` with `R(a,b)` and `S(a,b)` reports inconsistency | Partial | `owl_normalization.py:163–167` stores roles in `disjoint_object_properties`; regression test checks field (`test_correctness_regression.py:124–132`); no end-to-end inconsistency test with actual role assertions |
| AC7 — `DLOntology.has_nominals()` returns `True` for ontology containing a nominal | Pass | `model/__init__.py:2005,2134–2144` — `_check_nominals` scans `internal:nom#` prefix in clauses and facts; covered by three regression tests (`test_correctness_regression.py:165–185`) |
| AC8 — Blocking validation with two distinct roles on same Y-variable does not accept invalid block | Pass | `blocking_validator.py:265–291` — iterates all roles via `for role in xy_roles/yx_roles`, one retrieval per role; regression test asserts `len(info.m_x2y_roles) == 2` (`test_correctness_regression.py:193–224`) |
| AC9 — `DoubleValueSpaceSubset(values=frozenset({1.0})).complement()` does not return empty | Pass | `doublenum/__init__.py:57–66` — finite-set complement returns `_negated=True` subset; seven regression tests cover complement semantics (`test_correctness_regression.py:231–276`) |
| AC10 — `DeterministicClassification.classify()` returns same `Hierarchy` as `QuasiOrderClassification` for EL ontology | Pass | `deterministic_classification.py:45–54` — delegates to `QuasiOrderClassification`; regression test confirms hierarchy non-null and B node reachable (`test_correctness_regression.py:283–304`) |
| AC11 — `Query.evaluate()` returns results for a one-atom conjunctive query `C(x)` against materialized ABox | Pass | `datalog/__init__.py:172–309` — nested-loop join over extension tables; three regression tests including derived-concept case (`test_correctness_regression.py:311–373`) |
| AC12 — All existing `pytest tests/` pass after all changes (3050 tests, zero failures) | Unknown | Cannot confirm from static analysis alone; no CI artifact or run log was provided for review |

---

## Gaps & Issues

| Severity | Location | Description |
| :--- | :--- | :--- |
| Major | `tests/test_correctness_regression.py:57–158` | AC1–AC6 regression tests validate normalizer field population only, not end-to-end reasoner entailments. The acceptance criteria require that "a reasoner loaded with …" produces specific entailments or detects inconsistency. These tests should be augmented with full Reasoner-level assertions (clausify → tableau → `is_consistent()` / role-entailment check) matching the style of `test_correctness.py:268`. |
| Minor | `src/hermit/structural/owl_normalization.py:233` | The `else` branch of the symmetric-property normaliser calls `get_named_role()` if available, otherwise uses the role as-is. If the property is already an `InverseRole`, this produces an inclusion with the role as both sub and super rather than `(R, R⁻)`, silently generating a no-op inclusion instead of the correct symmetry axiom. |
| Minor | `src/hermit/structural/owl_normalization.py:181` | `OWLEquivalentDataPropertiesAxiom` falls through to `positive_facts` unchanged rather than being expanded into symmetric `data_property_inclusions` pairs. This means equivalent data properties are silently ignored by the clausifier. |
| Minor | `src/hermit/hierarchy/deterministic_classification.py:45–54` | `DeterministicClassification.classify()` is a pure delegation to `QuasiOrderClassification`. FR13 specified implementing the deterministic fast-path reading subsumptions directly from the deterministic model. The delegation satisfies AC10 but not the stated algorithmic intent. |
| Minor | `src/hermit/datalog/__init__.py:209–224` | In the bound unary-atom branch, `retrieval.open()` is called and then `after_last()` is checked without an intervening `next()` call. If the extension table contract requires at least one `next()` after `open()` before `after_last()` is meaningful, bound-variable concept checks will silently return false negatives. The extension table contract should be verified and a comment added. |

---

## Suggestions

- Add end-to-end OWL-axiom-level regression tests for AC1–AC6 that construct a full `Reasoner` via the OWL clausification pipeline and assert entailments or inconsistency, mirroring `test_correctness.py:268`. The existing unit-level field checks remain valuable but are insufficient to satisfy the literal AC wording.
- Guard or assert in `owl_normalization.py:226–234` that the symmetric inclusion always yields an `InverseRole` as the second element; add a test with an `InverseRole` property to exercise the else branch.
- Verify the extension table `open()`/`after_last()` contract and either add a `next()` call or document why it is not needed in `Query._evaluate_recursive`.
- Document `DeterministicClassification.classify()` delegation as a deliberate decision, or open a follow-up item to implement the actual deterministic fast-path when performance profiling motivates it.
