# Decisions: pyhermit Full Semantic Correctness (Sprint 2)

| Decision | Alternatives Considered | Rationale |
| :--- | :--- | :--- |
| Emit two-variable DL clauses directly for `∀R.C` in OWLNormalization rather than adding an `AllValuesConcept` node type | Add `AllValuesConcept` to model + visitor (symmetric with `AtLeastConcept`) | The tableau already handles universal semantics via DL clauses with two-variable body atoms. Adding a concept node type would require tableau rule changes; clause emission reuses existing hyperresolution machinery with zero risk. |
| Add `AtMostConcept` as a first-class model node | Continue synthetic approximation | Max-cardinality is OWL 2's most common cardinality operator. Approximation silently produces wrong answers. Must be correct. |
| At-most clausification: pairwise inequality clauses | Automaton-based approach (HermiT Java) | Automaton approach is required only for complex role chains. Simple max-cardinality over a simple property needs only pairwise inequality generation — standard textbook DL clausification. |
| Fix `¬(complex)` via NNF push-in rather than introducing a complement concept | Add `AtomicNegationConcept` wrapping complex args | `AtomicNegationConcept` can only wrap `AtomicConcept` by design (see model.py comment). NNF push-in is the correct DL approach and avoids structural unsoundness. |
| Only fix `hermit.structural.*` mypy errors in sprint 2; leave tableau/blocking under quarantine | Fix all 1217 errors at once | The tableau/blocking code is a verbatim Java port with hundreds of `object`-typed collections. Typing it correctly requires understanding each algorithm. Fixing structural/ is highest-value (most-modified, most-tested) and low-risk. |
| Remove `TestUniversalRestrictionLimitation` tests after the bug is fixed | Keep them as regression tests | They were documentation of a bug, not specification of desired behaviour. After the fix, the `TestAllValuesFrom` tests supersede them. |
| Do NOT touch the tableau engine internals | Refactor for type safety | The tableau is ~45K lines of correct Java-ported code. Risk of regression far outweighs benefit. Leave it. |
