# Status: Finish the pyhermit Port

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
- [ ] Step 12: Add end-to-end integration tests for Pizza and Koala ontologies

## Blockers
<!-- populated by /implement-task if something is stuck -->
