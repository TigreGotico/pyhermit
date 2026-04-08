# Status: PyHermit Port — Phase 1 COMPLETE ✅, Phase 2 IN PROGRESS

## Checklist

- [x] Step 1: Fix `DataRange` NameError in `blocking/anywhere_blocking.py`
- [x] Step 2: Fix `m_last_tableau_node` AttributeError in `tableau/branching_point.py`
- [x] Step 3: Fix `apply_dl_clauses` binary/ternary tuple split + remove DEBUG prints in `tableau/hyperresolution_manager.py`
- [x] Step 4: Vendor `hermit/owl_model/` from owlapy (rewrite imports, replace pandas.Timedelta)
- [x] Step 5: Implement `structural/ExpressionManager` (NNF + simplification)
- [x] Step 6: Implement `structural/OWLNormalization` (OWL axioms → NormalizedAxioms)
- [x] Step 7: Implement `structural/BuiltInPropertyManager` (top/bottom property injection)
- [x] Step 8: Implement `structural/ObjectPropertyInclusionManager` (role chain automata)
- [x] Step 9: Implement `datalog/` — ConjunctiveQuery, DatalogEngine, QueryResultCollector
- [x] Step 10: Implement `hermit/parser.py` — owlready2-backed OWL file parser
- [x] Step 11: Wire end-to-end — update `structural/__init__.py`, `hermit/__init__.py`, and OWLNormalization wiring
- [x] Step 12: Add end-to-end integration tests for Pizza and Koala ontologies

## Phase 2: Fix Remaining Tableau Bugs

Target: Achieve 426/426 tests passing (100% parity). Currently 418/426 (98.1%).

### Phase 2a: Quick Wins (Estimate: 6 hours)

- [x] Bundle Pizza & Koala ontologies into test resources
- [ ] Fix property hierarchy classification (Bug #2: `is_sub_role_of` broken) — IN PROGRESS, BLOCKED
- [ ] Debug role inclusion in hyperresolution (Bug #8: role chains in tableau)

### Phase 2b: Critical Path (Estimate: 6-10 hours)

- [ ] Fix ABox instance type extraction (Bugs #3-4: `has_type()` returns False) — HIGHEST PRIORITY
- [ ] Fix disjointness clash detection (Bug #1: disjoint concepts don't clash)
- [ ] Fix unsatisfiable concept detection (Bug #5: contradictions not detected)

### Phase 2c: Publication Ready (Estimate: 4 hours)

- [ ] Run full test suite on Python 3.10, 3.11, 3.12
- [ ] Generate API documentation (Sphinx/MkDocs)
- [ ] Write contributor guide
- [ ] Publish to PyPI as hermit-reasoner v1.0.0

## Blockers

- **Bug #2 (property hierarchy classification)**: Role hierarchy not being computed correctly from DL clauses
  - **Root cause**: `QuasiOrderClassificationForRoles._initialise_known_subsumptions_using_told_subsumers_from_clauses()` is not properly extracting subsumption relationships from DL clauses despite correct role collection
  - **Current state**: Roles are being collected from both head and body atoms, but the hierarchy shows all roles at top level with no subsumption edges
  - **Needs**: Detailed debugging of why subsumption relationships are not being inferred during hierarchy computation
  - **Impact**: 1 test failing (TestPropertySubsumption::test_property_hierarchy)
  - **Next steps**: 
    1. Add debug logging to `_initialise_known_subsumptions_using_told_subsumers_from_clauses()` to verify DL clauses are being processed
    2. Check if `_add_known_subsumption()` is actually being called
    3. Verify mappings between roles and proxy concepts are correct
    4. Consider if issue is in QuasiOrderClassification base class instead of subclass
