# Implementation Notes: pyhermit Full Semantic Correctness (Sprint 2)

## Patterns to Use

- **Two-variable DL clause emission** — `DLClause.create(head_atoms, body_atoms)` where body uses `Variable.create("X")` and `Variable.create("Y")`. Already used in `object_property_inclusion_manager.py:121-126` for negated-property rewriting. Same pattern here for `∀R.C`.
- **`AtLeastConcept` as template for `AtMostConcept`** — same three fields (`_number`, `_on_role`, `_to_concept`), same factory `create()`, same `accept()` dispatch. Mirror exactly.
- **Pairwise inequality clausification for at-most** — for `≤n R.C`: generate n+1 fresh variables; for each pair generate a DL clause with body `[A(X), R(X,Yi), C(Yi), R(X,Yj), C(Yj)]` and head `[Yi ≠ Yj]`. For `≤0 R.C`: body `[A(X), R(X,Y), C(Y)]`, head `[⊥]` (empty head = clash).
- **NNF push-in for complement of complex** — `¬(∃R.C)` = `∀R.¬C` (all-values with negated filler); `¬(A⊓B)` = `¬A⊔¬B`; `¬(A⊔B)` = `¬A⊓¬B`; `¬(≥n R.C)` = `≤(n-1) R.C`; `¬(≤n R.C)` = `≥(n+1) R.C`.

## Gotchas

- **`AtomicNegationConcept` can ONLY wrap `AtomicConcept`** — see `model/__init__.py`. Never try to wrap a complex concept in it. Use NNF push-in instead.
- **`NormalizedAxiomClausifier` visitor** — lives in `src/hermit/structural/owl_clausification.py`. The visitor pattern means every concept type that can appear in `concept_inclusions` must have a `visit_X` method, or an `AttributeError: 'Y' object has no attribute 'accept'` crash occurs at clausification time. Adding `AtMostConcept` requires adding `visit_at_most_concept()` to this class.
- **`direct_dl_clauses` field in `NormalizedAxioms`** — add with `field(default_factory=list)` and type `list[DLClause]`. Must be consumed in `OWLClausification.clausify()` before the tableau is built.
- **`OWLObjectExactCardinality(n, R, C)`** — decompose in `_owl_expr_to_internal()` to a list `[AtLeastConcept(n,R,C), AtMostConcept(n,R,C)]`. The caller (`add_concept_inclusion()`) must handle the case where `_owl_expr_to_internal()` returns a list of concepts (intersection semantics — add each as a separate disjunct or as a conjunction inclusion).
- **Role extraction for `AtMostConcept`** — same IRI-to-internal lookup as `AtLeastConcept`. The role must be an `AtomicRole` or `InverseRole` from `hermit.model`. Use the existing `_role_from_owl_prop()` helper pattern.
- **OWL 2 conformance tests** — `tests/ontologies/koala.owl` exists. Check what reasoning queries are appropriate for it before writing assertions (it's a known benchmark). Do NOT assert facts you haven't verified by running the reasoner manually first.
- **`max_cardinality_roles` registry** — currently used by `ObjectPropertyInclusionManager` to check non-simplicity. After fixing `_owl_expr_to_internal()`, this registry should be populated with `AtMostConcept._on_role` instead of the old synthetic-concept path.

## Key Imports / APIs

- `hermit.model.AtLeastConcept` — template for `AtMostConcept` (`src/hermit/model/__init__.py`)
- `hermit.model.DLClause` — `DLClause.create(head: tuple[Atom, ...], body: tuple[Atom, ...])` 
- `hermit.model.Atom` — `Atom.create(predicate, *args)`
- `hermit.model.Variable` — `Variable.create("X")`
- `hermit.model.Inequality` — `Inequality.INSTANCE` for `Yi ≠ Yj` head atoms
- `hermit.structural.owl_clausification.NormalizedAxiomClausifier` — visitor; add `visit_at_most_concept()`
- `hermit.structural.normalized_axioms.NormalizedAxioms` — add `direct_dl_clauses: list[DLClause]`
- `hermit.structural.owl_normalization.OWLNormalization._process_sub_class_of` — detect `OWLObjectAllValuesFrom`

## Conventions

- New fields in `NormalizedAxioms`: `field(default_factory=list)`, typed precisely
- Test class names: `TestAllValuesFrom`, `TestMaxCardinality`, `TestConformance`
- Test function names: `test_<what>_<expected>`, e.g. `test_all_values_from_restricts_filler()`
- Keep owlready2 behind `pytest.importorskip("owlready2")` in conformance tests
- One commit per checklist item; commit message format from `skills/git-based-development/SKILL.md`
