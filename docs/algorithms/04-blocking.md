# 04 — Blocking: Making the Tableau Terminate

The Chapter 03 loop can run forever. **Blocking** is the mechanism that detects
"we are building the same thing over and over" and stops it — turning a
potentially infinite construction into a finite one that still represents an
infinite model. This chapter shows why naive expansion loops, then how blocking
cuts the loop, with the real pyhermit classes.

## 1. Why naive tableau never stops

Recall the clausified ontology from Chapter 02:

```
Animal(X)                  :-  Dog(X)
(≥1 hasParent.Animal)(X)   :-  Animal(X)
fact:  Dog(fido)
```

Trace existential expansion without blocking:

```
n0 = fido :  Dog, Animal, (≥1 hasParent.Animal)
   existential needs a hasParent-successor that is an Animal:
n1 (fresh):  Animal, (≥1 hasParent.Animal)        edge hasParent(n0,n1)
   n1 again needs an Animal parent:
n2 (fresh):  Animal, (≥1 hasParent.Animal)        edge hasParent(n1,n2)
n3 ...  n4 ...  forever.
```

Every new node has the **same label** `{Animal, (≥1 hasParent.Animal)}` and
demands another identical successor. The graph is an infinite chain. The
ontology *is* consistent — an infinite (or cyclic) chain of animals is a perfectly
good model — but the procedure must report that in finite time.

## 2. The idea: reuse a witness

If node `n2` has the *same relevant label* as an earlier node `n1`, then anything
the tableau could build below `n2` it already built (or will build) below `n1`.
So `n2` does not need to expand its existentials — it can point at `n1` as a
**blocker** and stop. Formally, a finite tableau with blocking still has a model:
"unravel" the blocked node back to its blocker to recover the infinite structure.

A node `y` is **directly blocked** by an earlier node `y'` when their labels match
under the strategy's criterion; a node is **indirectly blocked** if its parent is
blocked. Blocked nodes are frozen — no existential expansion happens on them.

## 3. Two label-matching criteria: single vs pairwise

What counts as "same label" depends on whether the logic has **inverse roles**
(the **I** in SROIQ). Inverses let a successor constrain its predecessor, so for
soundness the match must also consider the edge to the parent.

- **Single (concept-set) blocking** — match only the node's concept label.
  Sound when there are no inverse roles.
  `src/hermit/blocking/single_direct_blocking_checker.py`
  (`SingleDirectBlockingChecker`).
- **Pairwise blocking** — match the pair *(label of node, label of its parent
  edge+parent)*. Required with inverse roles.
  `src/hermit/blocking/pairwise_direct_blocking_checker.py`
  (`PairWiseDirectBlockingChecker`).

Both implement the `DirectBlockingChecker` interface
(`src/hermit/blocking/direct_blocking_checker.py`). The choice is configurable
(`DirectBlockingType` in `src/hermit/configuration.py`: `SINGLE`, `PAIR_WISE`,
`OPTIMAL` — `OPTIMAL` picks pairwise iff the ontology uses inverses).

## 4. Two search scopes: ancestor vs anywhere

Given a criterion, *which* earlier nodes may serve as blocker?

- **Ancestor blocking** — only nodes on the path from the root to this node may
  block it. Simple, but finds fewer blockers, so models are larger.
  `src/hermit/blocking/ancestor_blocking.py` (`AncestorBlocking`).
- **Anywhere blocking** — *any* earlier node in the whole tableau with a matching
  label may block, found via a hash cache (`_BlockersCache`). Finds blockers
  sooner, yielding smaller models; this is HermiT's (and pyhermit's) default.
  `src/hermit/blocking/anywhere_blocking.py` (`AnywhereBlocking`).

`AnywhereBlocking.compute_blocking(final_chance)`
(`src/hermit/blocking/anywhere_blocking.py:82`) walks the changed nodes, looks
each up in the blockers cache, and calls `node.set_blocked(blocker, …)` to mark
it (the node stores its blocker in `m_blocking_object`,
`src/hermit/tableau/node.py`). The expansion strategy then skips existentials on
blocked nodes.

## 5. Blocking the infinite chain (worked)

Back to the chain of §1, with anywhere + single blocking:

```
n0 fido : {Dog, Animal, (≥1 hasParent.Animal)}     (root, special label)
n1      : {Animal, (≥1 hasParent.Animal)}           expand -> n2
n2      : {Animal, (≥1 hasParent.Animal)}
        compute_blocking: n2's label == n1's label, n1 is earlier
        => n2 is DIRECTLY BLOCKED by n1.   set_blocked(n1, True)
        n2's existential (≥1 hasParent.Animal) is NOT expanded.
```

```
      hasParent        hasParent
 n0 ───────────▶ n1 ───────────▶ n2[blocked by n1]   ← construction STOPS
                  ▲                    :
                  └────────── unravel ─┘  (n2 behaves like n1: infinite model)
```

The graph is now finite (3 nodes); no clash arose; the tableau reports
**consistent**. The blocked edge encodes the infinite model implicitly.

## 6. Validated blocking (the subtle part with inverses + cardinality)

Plain pairwise blocking is sound but, for the full SROIQ logic with number
restrictions and inverses, it can block too eagerly and miss a clash. HermiT uses
**validated blocking**: tentatively block, then *check* that the blocked node's
constraints (especially `≤n r.C` obligations seen through inverse roles) are
actually satisfiable at the blocker. pyhermit ports this:

- `src/hermit/blocking/blocking_validator.py` (`BlockingValidator`) accumulates,
  per blocked node, the role constraints (`_YConstraint`) and consequence atoms
  (`_ConsequenceAtom`) that must hold, and validates them — *all roles
  accumulated per Y-variable*.
- `src/hermit/blocking/anywhere_validated_blocking.py`,
  `validated_pairwise_direct_blocking_checker.py`,
  `validated_single_direct_blocking_checker.py` wire the validator into the
  anywhere/pairwise checkers.

If validation fails, the block is retracted and the node expands after all,
restoring completeness.

## 7. Where blocking sits in the loop

Blocking is a `BlockingStrategy` (`src/hermit/blocking/blocking_strategy.py`)
owned by the reasoner/tableau. `compute_blocking` is invoked during expansion so
that, before an existential is expanded on a node, the node's blocked status is
current; the existential-expansion strategy (`src/hermit/existentials/`) consults
it and skips blocked nodes. Together with backtracking (next chapter) this makes
the whole procedure a **decision** procedure: always terminating, always correct.

---

Previous: [03 — The Hypertableau Calculus](03-hypertableau-calculus.md) · Next:
[05 — Dependency-Directed Backtracking](05-dependency-directed-backtracking.md)
