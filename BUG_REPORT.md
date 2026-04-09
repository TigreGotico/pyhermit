# PyHermit Tableau Bugs — Comprehensive Report

## Summary

While attempting to fix examples with existential restrictions, **4-5 interconnected bugs** were discovered in the tableau reasoning engine:

---

## Bug #1: Variable Collection in DL Clause Compiler

**File:** `src/hermit/tableau/dl_clause_evaluator.py`, lines 844-875

**Issue:** Variables in body atoms are only added to `self.m_variables` if they occur LATER in the body. Variables that only appear in the head are not collected until after body compilation starts.

**Impact:** When compiling rules like:
```
(has_owner, X, Y), (person, Y) → (dog_with_owner, X)
```
Variable X and Y might not be properly tracked, causing IndexError in later compilation.

**Fix Applied:** 
Collect ALL variables from body and head upfront before code generation.

**Status:** ✅ FIXED (lines 844-874 rewritten)

---

## Bug #2: Empty Merge Sets in Dependency Factory

**File:** `src/hermit/tableau/dependency_set_factory.py`, line 237

**Issue:** The `get_permanent()` method assumes `self._merge_sets` is non-empty when it enters the while loop. If it's empty, `first_set = self._merge_sets[0]` raises IndexError.

**Impact:** Causes crash when processing certain dependency set patterns.

**Fix Applied:**
Check if `num_sets == 0` and return `self.empty_set` early.

**Status:** ✅ FIXED (lines 236-238 added guard)

---

## Bug #3: Missing Method in Ground Disjunction

**File:** `src/hermit/tableau/ground_disjunction.py`, lines 119, 127

**Issue:** Code calls non-existent `extension_manager.contains_assertion()` method. The actual methods are `contains_assertion_binary()` and `contains_assertion_ternary()`.

**Impact:** AttributeError when checking if disjuncts are satisfied.

**Fix Applied:**
Changed generic `contains_assertion()` calls to specific `contains_assertion_binary()` and `contains_assertion_ternary()`.

**Status:** ✅ FIXED (lines 119-133 updated)

---

## Bug #4: Type Mismatch in Ground Disjunction

**File:** `src/hermit/tableau/ground_disjunction.py`, line 122

**Issue:** Code assumes all arguments are nodes with `.get_canonical_node()` method, but they can be concepts or other types that don't have this method.

**Impact:** AttributeError: 'AtomicConcept' object has no attribute 'get_canonical_node'

**Severity:** CRITICAL — This requires understanding what types of arguments ground_disjunction should handle.

**Status:** ❌ NOT YET FIXED (requires further investigation)

---

## Root Cause Analysis

These bugs stem from a **fundamental issue in how the tableau code handles atoms with mixed arguments** (some nodes, some concepts, some roles). The DL clause compiler and ground disjunction handler were written assuming a specific argument structure that doesn't always hold.

---

## Recommended Fixes

### Immediate (Already Applied)
- ✅ Fix variable collection in compiler
- ✅ Fix empty merge sets handling
- ✅ Fix method names in ground disjunction

### Next Steps (Required Before Publishing)
- [ ] Fix type handling in ground_disjunction for concept/role/node arguments
- [ ] Review all `contains_assertion*` calls for correct arity
- [ ] Test with existential restriction examples

### Testing Strategy
```bash
# Test each fix incrementally
python examples/03_object_properties.py  # Has existential restrictions
python examples/07_advanced_reasoning.py  # Complex rules
python examples/10_complete_example_semantic_web.py  # Multiple rules
```

---

## Examples That Should Pass After Fixes

| Example | Requires Fix | Status |
|---------|-------------|--------|
| 01_hello_world.py | None | ✅ Already works |
| 02_class_hierarchy.py | None | ✅ Already works |
| 03_object_properties.py | Bug #4 | ⏳ Partially fixed |
| 04_instance_retrieval.py | is_same_individual API | ⚠️ Documented workaround |
| 05_cardinality_restrictions.py | None | ✅ Already works |
| 06_disjointness_and_negation.py | None | ✅ Already works |
| 07_advanced_reasoning.py | Bug #4 | ⏳ Partially fixed |
| 08_loading_owl_files.py | None | ⏭️ Requires external files |
| 09_configuration_and_performance.py | None | ✅ Already works |
| 10_complete_example_semantic_web.py | Bug #4 | ⏳ Partially fixed |

---

## Conclusion

**3 out of 4 major bugs have been fixed.** Bug #4 requires deeper understanding of ground_disjunction's argument handling. The fixes applied so far have improved error handling and corrected API mismatches, but the complete solution requires addressing how mixed-type arguments are processed.

