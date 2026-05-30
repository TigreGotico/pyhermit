# 03 — The Hypertableau Calculus

This is the engine. Given a `DLOntology` of DL-clauses and facts, the tableau
tries to **build a model** — a concrete interpretation in which every clause and
fact holds. If it succeeds, the ontology is consistent. If every attempt runs
into a contradiction (a **clash**), it is inconsistent. This chapter explains the
data structures, the main loop, and traces the keystone inconsistency example
step by step.

Reference: Motik, Shearer, Horrocks, *Hypertableau Reasoning for Description
Logics*, JAIR 36 (2009). pyhermit's `Tableau` (`src/hermit/tableau/tableau.py`)
is a structural port of HermiT's implementation of that calculus.

## 1. The model under construction

The tableau builds a labelled graph:

- **Nodes** (`hermit.model`/`hermit.tableau.node.Node`) are the objects of the
  interpretation. Each named individual gets a node; existentials invent fresh
  **tree nodes**. A node carries the set of concepts asserted to hold of it.
- **Edges** are role assertions `r(a, b)` between nodes.

The label of a node is stored not on the node object but in **extension tables**
(`hermit.tableau.extension_manager.ExtensionManager`): big flat tables of tuples.
A concept assertion `C(a)` is the binary tuple `(C, a)`; a role assertion
`r(a, b)` is the ternary tuple `(r, a, b)`. "Is `C(a)` asserted?" is the table
query `contains_tuple((C, a))`.

## 2. The delta ring (how new facts are scheduled)

The engine must apply each clause to every fact, but re-scanning all facts every
iteration would be quadratic. Instead each extension table partitions its tuples
into three consecutive ranges by two moving boundaries — the **delta ring**
(`ExtensionTableWithTupleIndexes` in `src/hermit/tableau/extension_manager.py`):

```
   [ EXTENSION_OLD | DELTA_OLD ("this") | DELTA_NEW ]   tuples in insertion order
   0          afterOld           afterThis        afterDeltaNew = first free slot
```

- **EXTENSION_OLD** `[0, afterOld)` — facts already fully processed.
- **DELTA_OLD / "this"** `[afterOld, afterThis)` — facts to process *this* round
  (the working set hyperresolution reads from).
- **DELTA_NEW** `[afterThis, afterDeltaNew)` — facts added since the last round,
  waiting their turn.

`add_tuple` appends a tuple and, crucially, advances `afterDeltaNew` to the new
free slot (`_after_delta_new_tuple_index = size // slot_size`, lines ~603-612).
**A freshly added tuple therefore lands inside DELTA_NEW.** This is what makes it
visible to the next round — a point so important it is the keystone fix below.

`propagate_delta_new` rotates the ring one step
(`extension_manager.py:766`), mirroring Java's `propagateDeltaNew`:

```
deltaNewNotEmpty = (afterThis != afterDeltaNew)   # was anything new added?
afterOld         = afterThis                      # old this -> old
afterThis        = afterDeltaNew                  # new      -> this
afterDeltaNew    = firstFreeSlot                  # open a fresh empty new-range
return deltaNewNotEmpty
```

So a tuple added in round *k* sits in DELTA_NEW; after the next
`propagate_delta_new` it becomes "this" and is fed to the clauses in round
*k+1*. `branching_point_pushed` (line ~548) *snapshots* the three boundaries so
backtracking can restore them; `backtrack` (line ~570) restores them and
truncates the table. (Earlier code collapsed the boundaries at a push, which
jammed disjuncts asserted after a branch into "this" so their clash never
re-entered the working set — see the keystone trace and the audit.)

## 3. Hyperresolution (firing a clause)

Given a DL-clause `H1 ∨ … ∨ Hm :- B1 ∧ … ∧ Bn`, **hyperresolution** finds an
assignment of nodes to the clause variables such that *all* body atoms `Bi` are
present in the extension tables, then acts on the head:

- **empty head (`m = 0`)** → the body is contradictory → **clash**: record the
  combined dependency set via `set_clash`. (Compiled to a `SetClash` worker,
  `dl_clause_evaluator.py:1139`.)
- **single head (`m = 1`)** → derive that atom: add `H1` to the tables
  (`DeriveUnaryFact` / `DeriveBinaryFact`, `:1146`+).
- **multi head (`m > 1`)** → a **ground disjunction**: at least one of the `Hj`
  must hold, but we do not yet know which. Record a `GroundDisjunction`
  (`dl_clause_evaluator.py:587`, `tableau.add_ground_disjunction`) to be resolved
  later by branching.

Clauses are compiled once into a little bytecode of **Worker** instructions by
`HyperresolutionManager` (`src/hermit/tableau/hyperresolution_manager.py`) and
`DLClauseEvaluator` (`src/hermit/tableau/dl_clause_evaluator.py`) — a faithful
port of HermiT's worker VM. `apply_dl_clauses` runs them against the DELTA_OLD
range.

## 4. Existential expansion

A head atom `(≥n r.C)(a)` says node `a` needs `n` distinct `r`-successors in `C`.
If they are not already present, **existential expansion** invents fresh tree
nodes and the edges/labels to satisfy it (`existentials/` package, driven from
`Tableau._do_iteration` via `expand_existentials`). This is where the OWA "invent
unnamed objects" happens. New nodes and tuples land in DELTA_NEW and feed the
next round.

## 5. Ground-disjunction branching

When a `GroundDisjunction` `H1 ∨ … ∨ Hm` is processed and not already satisfied,
the engine must **choose** a disjunct. It pushes a `DisjunctionBranchingPoint`
(`src/hermit/tableau/disjunction_branching_point.py`), records the choice in the
branching-point stack, and asserts the first disjunct `H1` with a dependency set
that *includes the new branching point* (Chapter 05). If that leads to a clash,
backtracking returns here and `start_next_choice` tries `H2`, adding `¬H1` so the
exhausted branch is not revisited.

## 6. The main loop: `Tableau._do_iteration`

`Tableau.is_satisfiable` loads the facts and calls `_run_calculus`, which spins
`_do_iteration` until no work remains (`src/hermit/tableau/tableau.py:736`,
`:784`). One iteration, in order:

1. **Saturate (the inner `while`)**: while `propagate_delta_new()` reports new
   tuples *and* there is no clash — apply description-graph constraints,
   `apply_dl_clauses()` for the permanent (and additional) ontology, datatype
   checks, and nominal processing. This fires every clause against every
   freshly-arrived fact. (lines ~793-815)
2. **Existential expansion**: if no clash, `expand_existentials(False)` — invent
   successors for one pending existential. (lines ~820-822)
3. **Ground-disjunction branching**: if no clash, take the next unprocessed
   `GroundDisjunction`; if unsatisfied, push a branching point and assert its
   first disjunct. (lines ~825-868)
4. **Backtracking**: if there *is* a clash, read the clash's dependency set,
   compute the highest branching point it blames, and `_backtrack_to` that level,
   then `start_next_choice`. If the blamed level is below the
   non-backtrackable floor, return `False` — **inconsistent**. (lines ~877-898)

If a full pass makes no change and there is no clash, the model is complete:
**consistent**.

## 7. Clashes

A **clash** is a recorded contradiction. The most direct source is a zero-head
clause firing (`set_clash`), but the `ClashManager`
(`src/hermit/tableau/clash_manager.py`) also detects e.g. `C(a)` together with
`¬C(a)`, or `r(a,b)` with `¬r(a,b)`, the moment the second tuple is added.
A clash stores the **union of the dependency sets** of the two conflicting facts
— the branching points blamed for it (Chapter 05).

## 8. Keystone example, fully traced

This is pyhermit's regression touchstone
(`tests/test_tableau.py::TestHeadDisjunctionExpansion`). Clauses and one fact:

```
fact :  U(a)
C1   :  A(X) ∨ B(X)  :-  U(X)      # whatever is a U is an A or a B
C2   :       ⊥       :-  A(X)      # nothing may be an A   (empty head)
C3   :       ⊥       :-  B(X)      # nothing may be a B    (empty head)
```

Intuitively `a` is a `U`, so `a` is an `A` or a `B`; but neither is allowed, so
**no model exists — INCONSISTENT.** Here is how the engine reaches that.

```
ASCII state.  Node n0 = individual a.  Tables hold (Predicate, node) tuples.
Boundaries shown as [old | this | new].

(0) Load fact.  Add U(a).  It lands in DELTA_NEW.
    binary table:  (⊤,n0)(U,n0)            boundaries: [ |  | ⊤,U ]

(1) propagate_delta_new  -> "this" now = {⊤(n0), U(n0)}, returns True.
    apply_dl_clauses: C1 body U(X) matches X=n0, head length 2
        -> record GroundDisjunction  GD = A(n0) ∨ B(n0).
    C2,C3 bodies (A,B) not present yet -> no clash. No more delta. while ends.

(2) No clash, no existentials.  Ground-disjunction phase:
    GD is unsatisfied (neither A(n0) nor B(n0) present).
    Push DisjunctionBranchingPoint bp0  (current_branching_point: -1 -> 0).
        branching_point_pushed snapshots the delta boundaries for level 0.
    Assert first disjunct A(n0) with dependency set { bp0 }.
        add_tuple(A,n0) -> lands in DELTA_NEW; afterDeltaNew advances.   *** the fix ***
    Tables:  ...(A,n0)            return True (more work).

(3) Next iteration.  propagate_delta_new -> "this" = { A(n0) }, returns True.
    apply_dl_clauses: C2 body A(X) matches X=n0, HEAD LENGTH 0
        -> SetClash with dependency set { bp0 }.   CLASH.

(4) Backtracking phase.  clash_dependency_set = { bp0 }.
    max branching point = bp0 (level 0).  0 > nonbacktrackable floor (-1).
    _backtrack_to(0): truncate tables back to the level-0 snapshot
        (drops A(n0) and the clash), restore boundaries.
    bp0.start_next_choice: current_index 0 -> 1.
        Add ¬A(n0) (so branch 1 is excluded) and assert second disjunct B(n0),
        with the dependency set carried from the clash.  B(n0) lands in DELTA_NEW.
    return True.

(5) Next iteration.  propagate_delta_new -> "this" = { ¬A(n0), B(n0) }.
    apply_dl_clauses: C3 body B(X) matches X=n0, HEAD LENGTH 0
        -> SetClash with dependency set { bp0 }.   CLASH again.

(6) Backtracking phase.  clash blames bp0 (level 0) again, but bp0 has no
    further disjuncts.  start_next_choice exhausted -> the clash's max
    branching point (0) is now <= the floor for this exhausted point:
    _do_iteration returns False.

    RESULT: _run_calculus sees contains_clash() and returns False.
            is_satisfiable -> False.   ONTOLOGY INCONSISTENT.  Correct.
```

### Why step (2)'s "the fix" matters

If a disjunct asserted right after pushing a branching point were **not** placed
into DELTA_NEW — if `add_tuple` left `afterDeltaNew` where it was, or if a push
collapsed the boundaries so the new tuple counted as already-"this" — then in
step (3) `propagate_delta_new` would report DELTA_NEW *empty*, the inner
`while` would not run, `apply_dl_clauses` would never see `A(n0)`, and the
`⊥ :- A` clash would never fire. The engine would wrongly conclude the branch is
clash-free and report the ontology **consistent**. The two collaborating
guarantees that prevent this are:

- `add_tuple` advances `afterDeltaNew` so every freshly added tuple is in
  DELTA_NEW (`extension_manager.py:603-612`); and
- `branching_point_pushed` only *snapshots* the boundaries, it does not collapse
  them (`extension_manager.py:548-568`).

At this commit both hold, and the four `TestHeadDisjunctionExpansion` cases —
both-clash (inconsistent), both-satisfiable (consistent), first-clash-then-B
(consistent via backtrack), and a recursive satisfiable chain (terminates) — all
pass.

## 9. Connecting the pieces

The loop interleaves four mechanisms: **hyperresolution** derives facts and
clashes deterministically; **existential expansion** grows the graph;
**ground-disjunction branching** makes nondeterministic choices; **backtracking**
(next-but-one chapter) undoes bad choices. Two problems remain: the graph can
grow forever (Chapter 04, blocking), and blind retry of choices is wasteful
(Chapter 05, dependency-directed backtracking).

---

Previous: [02 — Normalization & Clausification](02-normalization-clausification.md)
· Next: [04 — Blocking](04-blocking.md)
