# 05 — Dependency-Directed Backtracking

When the tableau makes a nondeterministic choice (which disjunct of a ground
disjunction?) and later hits a clash, it must undo *some* choices and try again.
Doing this blindly (chronological backtracking) wastes enormous effort.
**Dependency-directed backtracking** (a.k.a. **backjumping**) undoes exactly the
choices that *caused* the clash and skips the irrelevant ones. The bookkeeping
that makes this possible is the **dependency set**, and it is the single most
interesting place where pyhermit diverges from Java HermiT
(see `FAITHFULNESS_AUDIT.md`).

## 1. Branching points

Every nondeterministic choice opens a **branching point**, numbered by an
increasing integer **level** (0, 1, 2, …). The tableau keeps them on a stack
(`Tableau.m_branching_points`, `m_current_branching_point`,
`src/hermit/tableau/tableau.py`). The base class is
`hermit.tableau.branching_point.BranchingPoint`; disjunction choices use
`DisjunctionBranchingPoint`
(`src/hermit/tableau/disjunction_branching_point.py`), which remembers the
sorted disjunct indexes and which one it is currently trying (`_current_index`).

A branching point snapshots enough state (the last node, last merged/pruned node,
the ground-disjunction list heads) to roll the tableau back to the instant before
the choice (`BranchingPoint.__init__`).

## 2. Dependency sets: blaming choices for facts

Every derived fact carries a **dependency set**: the *set of branching-point
levels whose choices it depends on*. Intuitively, "this fact is here because of
the choices made at branches `{1, 4}`."

- A fact loaded from the ABox or derived from facts that depend on nothing has
  the **empty** dependency set `{ }`.
- When a disjunct is asserted at branching point `b`, its dependency set
  *includes* `b` (`Tableau._do_iteration` calls
  `dependency_set_factory.add_branching_point(ds, b)` when it pushes the
  branch, `tableau.py:851`).
- When hyperresolution derives a fact from several body facts, the new fact's
  dependency set is the **union** of theirs (the `UnionDependencySet`,
  below).
- When a clash is recorded, its dependency set is the union of the dependency
  sets of the two conflicting facts (`ExtensionManager.set_clash`,
  `extension_manager.py:1021`).

### The key interface

`hermit.tableau.dependency_set.DependencySet`
(`src/hermit/tableau/dependency_set.py`) is tiny — exactly what the tableau needs:

```python
contains_branching_point(b)  -> bool      # is level b in this set?
is_empty()                   -> bool
get_maximum_branching_point() -> int       # highest level, or -1 if empty
```

That is *all* the algorithm asks of a dependency set: membership of a level, and
the maximum level. It never needs to mutate one in place. Remember this — it is
why pyhermit's representation can be immutable.

## 3. Two representations

pyhermit (like Java) uses two concrete forms:

- **`PermanentDependencySet`**
  (`src/hermit/tableau/permanent_dependency_set.py`): a singly-linked list of
  levels in **descending** order (`_branching_point`, `_rest`). The empty set is
  the node with `_branching_point == -1`. These are **interned** (see §5): two
  permanent sets with the same content are the *same object*, so equality is
  `is` and `get_maximum_branching_point()` is just reading the head field.

- **`UnionDependencySet`**
  (`src/hermit/tableau/union_dependency_set.py`): a transient, mutable
  "union-of-constituents" used *during* a single derivation, where
  hyperresolution accumulates the body facts' sets via `add_constituent`. It is
  flattened to a permanent set when the derived fact is recorded.

The `DependencySetFactory`
(`src/hermit/tableau/dependency_set_factory.py`) creates and interns permanent
sets and implements set operations the tableau needs: `add_branching_point`,
`remove_branching_point`, `union_with`, and `get_permanent` (which flattens a
`UnionDependencySet` into an interned permanent one).

## 4. Backjumping vs chronological backtracking

When a clash is detected, `Tableau._do_iteration` does
(`src/hermit/tableau/tableau.py:877`):

```python
clash_ds = extension_manager.clash_dependency_set
target = clash_ds.get_maximum_branching_point()      # highest blamed level
if target <= nonbacktrackable_branching_point:
    return False                                     # truly inconsistent
self._backtrack_to(target)                           # JUMP straight there
get_current_branching_point().start_next_choice(self, clash_ds)
```

The crucial line is `get_maximum_branching_point()`. The engine jumps directly to
the **highest branching point the clash actually depends on**, discarding
everything above it in one move — even if dozens of unrelated branches were
opened in between. That is **backjumping**. Chronological backtracking would
instead step back one branch at a time, re-exploring choices the clash never
implicated. On real ontologies this is the difference between seconds and hours.

### Why the clash's set must include the causing branch

Soundness of backjumping rests on a discipline: *a clash's dependency set must
contain the branching point of every choice that contributed to it.* This is
maintained automatically because (a) the asserted disjunct's set includes its
branch level, (b) unions propagate that level to every fact derived from it, and
(c) the clash unions the sets of both conflicting facts. So if a wrong disjunct
choice at level `b` led (through any chain of derivations) to the clash, `b` is in
the clash's set, `get_maximum_branching_point()` is `≥ b`, and backjumping lands
at or above `b` — never skipping the choice it must revise. Conversely, branches
*not* in the set provably did not matter, so skipping them is safe.

After jumping, `DisjunctionBranchingPoint.start_next_choice`
(`disjunction_branching_point.py:49`) advances to the next disjunct, asserts the
negations of the already-tried ones (so they are never retried), and — when only
the *last* disjunct remains — calls `remove_branching_point` to drop `b` from the
carried dependency set (the choice is now forced, not a real branch).

## 5. The flagship divergence: interning + GC instead of manual refcounting

**This is the headline difference from Java HermiT.** It is documented in full in
`FAITHFULNESS_AUDIT.md`; here is the algorithmic essence.

Java's `DependencySetFactory` hand-manages the lifetime of every permanent set
with **manual reference counting**: `addUsage` / `removeUsage` bump an integer
`m_usageCounter` on each set, and `removeUnusedSets` periodically sweeps and frees
sets whose count hit zero. This is a JVM performance optimization — it avoids GC
pressure from millions of short-lived sets during a hard reasoning run. But it is
*fragile*: every code path that stores or drops a reference to a permanent set
must balance its `addUsage`/`removeUsage` perfectly. An imbalance frees a set that
is still referenced (a dangling pointer / "double-free", corrupting later
reasoning) or never frees one (a leak); a faithful Python port of that protocol
would be a constant source of subtle, hard-to-reproduce bugs.

pyhermit instead makes permanent sets **immutable and structurally interned** and
lets **Python's garbage collector** reclaim them:

- A `PermanentDependencySet`'s content (`_rest`, `_branching_point`) is never
  reassigned after the factory creates it
  (`permanent_dependency_set.py`, and `_create_dependency_set` in the factory).
- The factory's hash table (`_entries`) interns by structure: `_get_dependency_set`
  (`dependency_set_factory.py:272`) looks up `(rest, branching_point)` and returns
  the existing object if present, so structurally-equal sets are *identical*
  objects. Equality is `is`; hashing is structural (`_hash`).
- `add_usage`, `remove_usage`, and `remove_unused_sets` are retained as **no-ops**
  purely so the many call sites ported verbatim from Java still compile
  (`dependency_set_factory.py:100-113`). They do no counting. When a backtrack
  truncates the tuple table, the dropped tuples stop referencing their permanent
  sets, and ordinary Python refcounting/GC reclaims any that become unreachable;
  `factory.clear()` drops the whole table at once.

**Why this is sound.** The tableau only ever asks a dependency set for two things
(§2): "do you contain level `b`?" and "what is your maximum level?" Neither
mutates the set, and both are answered correctly by an immutable interned linked
list. Interning additionally gives the tableau fast `is`-equality and structural
hashing of dependency sets — which is exactly what the extension tables and the
ground-disjunction header cache rely on — without any lifetime protocol to get
wrong. Nothing in the calculus depends on a set being *freed at a particular
moment*; it only depends on the set's *value*. So replacing manual reclamation
with GC changes performance characteristics (more transient allocation, GC
instead of a hand-rolled free list) but **cannot change any answer**: the port is
sound and complete on this axis.

(One residual: `Tableau.merge_node` /
`_backtrack_last_merged_or_pruned_node` and `ExtensionManager.set_clash` /
`clear_clash` still *call* `add_usage`/`remove_usage` around merge and clash
dependency sets. Because those are no-ops, the calls are inert — they neither
help nor harm — and are kept only to mirror the Java call structure.)

## 6. Tracing the blame in the keystone example

In the Chapter 03 keystone trace, the disjunct `A(n0)` was asserted with
dependency set `{ bp0 }` (it depends on the level-0 disjunction choice). The
`⊥ :- A` clash unioned `A(n0)`'s set with the (empty) set from the zero-head
clause, giving clash set `{ bp0 }`. `get_maximum_branching_point()` returned `0`,
so backjumping went to level 0 and tried the next disjunct `B(n0)` — precisely
the choice it needed to revise. When `B(n0)` also clashed and bp0 had no further
disjuncts, the maximum blamed level was no longer above the floor, and the engine
correctly declared the ontology inconsistent.

---

Previous: [04 — Blocking](04-blocking.md) · Next: [06 — Datatypes](06-datatypes.md)
