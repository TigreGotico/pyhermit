# 07 — Classification and Queries

Chapters 03-06 built the consistency procedure. This chapter shows how the
`Reasoner` (`src/hermit/reasoner.py`) orchestrates *many* consistency checks to
answer the high-level questions from Chapter 01: subsumption, the full class
hierarchy, instance retrieval, and conjunctive queries.

## 1. One subsumption test

`O ⊨ C ⊑ D` is decided by the reduction from Chapter 01: it holds iff
`O ∪ {(C ⊓ ¬D)(x)}` is inconsistent for a fresh `x`. In code,
`Reasoner.is_sub_class_of(sub, sup)` (`src/hermit/reasoner.py:362`):

```python
fresh = Individual.create_anonymous("fresh-individual")
pos = { Atom.create(sub, fresh) }            # sub(x)
neg = { Atom.create(sup.get_negation(), fresh) }   # ¬sup(x)
return not self._get_tableau_with_facts(pos | neg).is_satisfiable(...)
```

If the tableau finds **no** model (`is_satisfiable` returns `False`), the
subsumption holds. `is_satisfiable(concept)`, `is_equivalent`, and `is_disjoint`
(`:346`, `:384`, `:388`) are the same idea with different fresh-individual
assertions. Each is one full tableau run.

## 2. Classification — and why not n² tests

Naively, classifying `n` atomic concepts is `n²` subsumption tests (every ordered
pair), each a tableau run. Real ontologies have thousands of concepts, so this is
ruinous. The fix is the **quasi-order / Enhanced-Traversal** algorithm
(Baader et al.; HermiT's classifier), ported as
`hermit.hierarchy.quasi_order_classification.QuasiOrderClassification`
(`src/hermit/hierarchy/quasi_order_classification.py`).

The idea: maintain two graphs as classification proceeds
(`quasi_order_classification.py:53`):

- **`m_known_subsumptions`** — subsumptions proven to hold;
- **`m_possible_subsumptions`** — subsumptions not yet ruled out.

and exploit two facts to avoid most tableau calls:

1. **Told subsumers** — subsumptions stated *syntactically* in the ontology
   (e.g. `Dog ⊑ Animal` is right there) are seeded into the known graph for free
   (`_initialise_known_subsumptions_using_told_subsumers`, `:69`).
2. **Transitivity / model reuse** — `⊑` is transitive, so once `A ⊑ B` and
   `B ⊑ C` are known, `A ⊑ C` is inferred without a test. And a single
   satisfiability model can refute *many* candidate subsumptions at once: if the
   model built while testing `A` shows an object that is `A` but not `C`, then
   `A ⊑ C` is impossible — prune it from the possible graph
   (`difference_update`, `:78`). This is the "enhanced traversal / leaf-node"
   strategy: explore concepts in an order that maximises reuse, doing a real
   tableau test only when known and possible graphs disagree.

Finally `_build_hierarchy` (`:64`) turns the resulting subsumption graph into a
`Hierarchy` of `HierarchyNode`s. Cycles of mutually-subsuming concepts (i.e.
equivalent concepts) are collapsed into one node using **Tarjan's
strongly-connected-components** algorithm, implemented in
`DeterministicClassification.build_hierarchy` /`_visit`
(`src/hermit/hierarchy/deterministic_classification.py:57`, `:112`), which the
quasi-order classifier reuses.

> **Divergence note.** Java has a separate `DeterministicClassification` fast path
> that reads *all* subsumptions off one deterministic model in a single pass (sound
> for Horn/EL TBoxes). pyhermit's `DeterministicClassification.classify()`
> currently *delegates* to `QuasiOrderClassification`
> (`deterministic_classification.py:45`) — sound and complete, but it runs the full
> quasi-order procedure even where the one-pass shortcut would apply. See
> `FAITHFULNESS_AUDIT.md`.

The reasoner entry points are `Reasoner.classify_classes()` (`:608`),
`classify_object_properties()` (`:635`), and `classify_data_properties()`
(`:726`); roles use the analogous `QuasiOrderClassificationForRoles`.

## 3. Instance retrieval

"Is `a` an instance of `C`?" is `O ⊨ C(a)`, i.e. `O ∪ {¬C(a)}` inconsistent.
`Reasoner.has_type(individual, concept)` (`:467`) does exactly that. "Give me
*all* instances of `C`" (`Reasoner.get_instances`, `:524`) would be one test per
individual — again too many — so the `InstanceManager`
(`src/hermit/hierarchy/instance_manager.py`) optimises it:

- it reads **known** instance relationships directly off a saturated model
  (positive facts that survived: if `C(a)` is in the model and the model is
  deterministic, `a` is a known instance), and
- it uses the already-computed **class hierarchy** to propagate: an instance of a
  subclass is an instance of all its superclasses
  (`set_to_classified_concept_hierarchy`, `:361`), so most memberships need no
  per-individual tableau call. Only genuinely uncertain cases fall back to a
  tableau test.

## 4. Conjunctive queries

A **conjunctive query** asks for variable bindings satisfying a conjunction of
atoms, e.g. *"find all `?x, ?y` with `Person(?x) ∧ hasParent(?x, ?y) ∧
Doctor(?y)`."* pyhermit answers these over the **saturated model** in
`hermit.datalog` (`src/hermit/datalog/__init__.py`): `Query.evaluate(collector)`
(`:172`) performs a recursive **nested-loop join** — bind the first atom from the
extension tables, recurse to bind the next under those bindings, and report each
complete tuple to a `QueryResultCollector` (`:19`). It handles ground/atomic and
multi-atom conjunctive queries against the materialized tables.

> **Divergence note.** Java compiles DL-safe rules into the same
> `DLClauseEvaluator` worker VM used for the tableau; pyhermit's datalog layer is
> a straightforward nested-loop join over the materialized extensions rather than
> the full compiled pipeline. Adequate for conjunctive queries; broader DL-safe
> rule materialization is narrower than Java. See `FAITHFULNESS_AUDIT.md`.

## 5. Putting the orchestration together

```
Reasoner.precompute_inferences()
    |
    +-- is_consistent()                 (1 tableau run; everything else assumes it)
    +-- classify_classes()              (quasi-order: few tableau runs + Tarjan SCC)
    +-- classify_object_properties()
    +-- realise instances               (InstanceManager: model read + hierarchy)
    |
queries afterwards:
    has_type / get_instances            (hierarchy lookups, tableau only if unsure)
    EntailmentChecker.entails(...)      (reduces each query to a tableau run)
    Query.evaluate(...)                 (nested-loop join over the model)
```

Every box ultimately rests on the Chapter 03 tableau; classification and instance
realization exist to call it as *few* times as possible.

---

Previous: [06 — Datatypes](06-datatypes.md) · Next:
[08 — Codebase Map](08-codebase-map.md)
