# Phase 2 Roadmap: PyHermit Path to 100% Feature Parity

**Current Status:** 418/426 tests passing (98.1%)  
**Target:** 426/426 tests passing (100%)  
**Estimated Effort:** 15-20 hours (2-3 days of focused work)  
**Next Milestone:** PyPI publication as `hermit-reasoner` v1.0

---

## Critical Path Analysis

### Priority 1: ABox Instance Type Extraction (BLOCKER) ⚠️

**Bug #3-4:** `has_type(individual, concept)` returns False; `get_instances(concept)` returns empty  
**Tests Affected:** 3 + 1 = 4 failing tests  
**Root Cause:** Type extraction from extension tables not finding asserted facts  
**Effort:** 4-6 hours (longest, highest impact)

**Debugging Approach:**
1. Instrument `_read_off_types()` in `instance_manager.py` to log retrieval queries
2. Verify facts are being added to `m_ternary_extension_table` during tableau saturation
3. Check retrieval parametrization (binding constraints)
4. Trace individual-to-node mapping pipeline

**Why This Matters:**
- Blocks 4 tests (10% of failing tests)
- Core functionality for downstream users (instance retrieval is primary use case)
- Once fixed, likely unblocks indirect debugging of other issues

---

### Priority 2: Property Hierarchy Classification ⚠️

**Bug #2:** `is_sub_role_of(r, s)` returns False when should be True  
**Tests Affected:** 1 failing test  
**Root Cause:** Property hierarchy not computed; likely missing QuasiOrderClassification for roles  
**Effort:** 3 hours

**Implementation Approach:**
1. Check if role hierarchy computation exists in `hierarchy/` module
2. If missing, apply same pattern as class hierarchy: delegate to `QuasiOrderClassification`
3. Wire role hierarchy into `Reasoner.get_object_property_hierarchy()` and `is_sub_role_of()` API

**Parallelize with:** Priority 1 (independent fix)

---

### Priority 3: Disjointness Clash Detection ⚠️

**Bug #1:** Concepts marked `disjoint(A, B)` don't trigger clash when both asserted  
**Tests Affected:** 1 failing test  
**Root Cause:** Clash detection missing disjointness axiom check during tableau expansion  
**Effort:** 3-4 hours

**Implementation Approach:**
1. Examine `ClashManager.tuple_added()` — how does it detect clashes?
2. Add new clash type: if asserting *C(x)* and A is disjoint from C, check for *A(x)* in node
3. Update `tableau_monitor` callbacks if needed
4. Test on `TestDisjointClasses::test_disjointness`

---

### Priority 4: Unsatisfiable Concept Detection ⚠️

**Bugs #5-7:** Concepts that should be unsatisfiable (implying contradictions) not detected  
**Tests Affected:** 2 failing tests  
**Root Cause:** Clash detection during model building incomplete; some contradictions not surfaced  
**Effort:** 2-3 hours

**Implementation Approach:**
1. Analyze test cases: what contradictions should be detected? (e.g., A ⊑ B ∧ A ⊑ ¬B)
2. Enhance clash detection to catch all contradiction patterns
3. Verify dependency tracking propagates correctly

---

### Priority 5: Role Inclusion in Hyperresolution ⚠️

**Bug #8:** `test_hyperresolution_with_role_inclusion` fails  
**Tests Affected:** 1 failing test  
**Root Cause:** Role inclusion axioms (complex role chains) not properly integrated into hyperresolution worker dispatch  
**Effort:** 2-3 hours

**Parallelize with:** Priorities 2-4 (independent, lower impact)

---

## Phase 2a: Quick Wins (Days 1-2)

**Timeline:** Morning of Day 1

- [ ] Bundle Pizza & Koala ontologies into test resources
  - Remove optional `owlready2` requirement for end-to-end tests
  - Effort: 1 hour
  - **Payoff:** Eliminates 8 test errors (makes test suite green except for known 8 failures)

- [ ] Fix property hierarchy classification (Bug #2)
  - Apply QuasiOrderClassification to roles
  - Effort: 3 hours
  - **Payoff:** +1 test passing (426 → 425)

- [ ] Debug role inclusion in hyperresolution (Bug #8)
  - Effort: 2 hours
  - **Payoff:** +1 test passing (425 → 424)

**Expected Status After 2a:** 422/426 passing (99.1%), 4 failures remaining in ABox/disjointness/unsatisfiability

---

## Phase 2b: Critical Path (Days 2-3)

**Timeline:** Afternoon of Day 1 through Day 2

- [ ] **Fix ABox instance type extraction (Bugs #3-4)** ← **CRITICAL**
  - Debug `_read_off_types()` retrieval queries
  - Trace individual-to-node mapping
  - Effort: 4-6 hours
  - **Payoff:** +4 tests passing (422 → 418 currently, but 422 → 418 after bugfixes)

- [ ] Fix disjointness clash detection (Bug #1)
  - Enhance ClashManager for disjointness axioms
  - Effort: 3-4 hours
  - **Payoff:** +1 test passing

- [ ] Fix unsatisfiable concept detection (Bugs #5-7)
  - Enhance contradiction detection
  - Effort: 2-3 hours
  - **Payoff:** +2 tests passing

**Expected Status After 2b:** 425-426/426 passing (99.5-100%)

---

## Phase 2c: Publication Ready (Day 3)

**Timeline:** Morning of Day 3

- [ ] Run full test suite on clean Python 3.10, 3.11, 3.12 environments
  - Use GitHub Actions for matrix testing (setup for CI/CD)
  - Effort: 1 hour

- [ ] Generate API documentation
  - Auto-generate Sphinx/MkDocs from docstrings
  - Effort: 1 hour

- [ ] Write contributor guide
  - Extract from sprint.md, decisions.md, implementation-notes.md
  - Include: "how to run tests", "how to add a new feature", "coding conventions"
  - Effort: 1 hour

- [ ] Publish to PyPI
  - Create `hermit-reasoner` package on PyPI (if not already done)
  - Upload source distribution + wheels
  - Effort: 1 hour

- [ ] Set up GitHub Actions CI/CD
  - Matrix test on Python 3.10, 3.11, 3.12
  - Coverage reporting (CodeCov integration)
  - Effort: 1 hour

**Expected Final Status:** v1.0.0 on PyPI, 426/426 tests passing, CI/CD pipeline operational

---

## Stretch Goals (If Time Permits)

If phase 2a-2c complete ahead of schedule (unlikely but possible):

- [ ] Interactive tableau debugger (REPL-based stepper)
  - Commands: `step`, `continue`, `show-node`, `show-model`
  - Effort: 8+ hours
  - Priority: **Low** (post-1.0 feature)

- [ ] OWL/N3 proof generation
  - Expose dependency sets as minimal axiom subsets
  - Format as OWL or N3 proofs
  - Effort: 6+ hours
  - Priority: **Low** (post-1.0 feature)

- [ ] Alternative ontology backends
  - Pluggable adapter for rdflib, owl-django, etc.
  - Effort: 4+ hours
  - Priority: **Low** (post-1.0 feature)

---

## Debugging Checklist for Each Bug

### Bug #3-4 (ABox Types) — Debug Script

```python
# In a test or REPL, trace the issue:
from hermit import Reasoner
from hermit.model import AtomicConcept, Individual

# Create simple ontology with instance
individual = Individual.create("http://example.org#fido")
dog_concept = AtomicConcept.create("http://example.org#Dog")
# ... wire ontology ...

reasoner = Reasoner(ontology)
print("Instance manager nodes:", reasoner._instance_manager.m_nodes_for_individuals)
print("Tableau first node:", reasoner.get_tableau().m_first_tableau_node)

# Try to get types
types = reasoner.get_types(individual)
print(f"Types of fido: {types}")  # Should be non-empty, currently empty

# Instrument _read_off_types to see what's happening
# Add logging to:
# - instance_manager.py:650-685 (_read_off_types)
# - Check if binary_retrieval_1_bound is being called
# - Check if extension table contains the facts
```

### Bug #2 (Property Hierarchy) — Debug Script

```python
# Check if role hierarchy exists
reasoner = Reasoner(ontology_with_role_subsumption)
print("Has get_object_property_hierarchy?", hasattr(reasoner, 'get_object_property_hierarchy'))

# Check if is_sub_object_property is implemented
role_r = AtomicRole.create("http://example.org#r")
role_s = AtomicRole.create("http://example.org#s")
print(f"is_sub_object_property(r, s): {reasoner.is_sub_object_property(role_r, role_s)}")

# Expected: True if ontology says r ⊑ s
# Actual: False (bug)
```

---

## Success Metrics

| Milestone | Metric | Target | Status |
|---|---|---|---|
| **Phase 2a** | Tests passing | 424/426 (99.1%) | To be verified |
| **Phase 2a** | Publication ready | Blocking bugs identified | ✅ Done |
| **Phase 2b** | Critical path fixed | Bugs #1-7 resolved | To be verified |
| **Phase 2b** | Tests passing | 426/426 (100%) | To be verified |
| **Phase 2c** | PyPI published | `pip install hermit-reasoner` works | To be verified |
| **Phase 2c** | CI/CD operational | GitHub Actions matrix testing | To be verified |
| **Phase 2c** | Documentation complete | Quickstart + API docs + contributor guide | To be verified |

---

## Communication Plan

After each phase, provide:

1. **Test execution summary** (`pytest --tb=short -q`)
2. **Code changes** (list of files modified, git log)
3. **Blockers or discoveries** (new issues found during debugging)
4. **Next phase readiness** (what's needed to proceed)

---

## References

- [FEATURE_PARITY.md](FEATURE_PARITY.md) — Detailed feature matrix and bug descriptions
- [audit.md](audit.md) — Phase 1 completion audit
- [sprint.md](sprint.md) — Sprint goals and milestones
- [spec.md](spec.md) — Acceptance criteria and functional requirements
- [decisions.md](decisions.md) — Architectural decisions (includes Phase 1 bug fixes)

---

**Next Step:** Begin Phase 2a with ontology bundling and property hierarchy fix. Target completion: 2-3 days from now.
