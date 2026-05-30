# 02 — Normalization and Clausification

The tableau engine does not consume OWL directly. It consumes a uniform logical
form called **DL-clauses**. Getting there is two preprocessing stages:
**normalization** (tidy the concepts) and **clausification** (turn axioms into
implications). This chapter explains both and traces a full example.

## 1. Why preprocess at all?

OWL lets you nest constructs arbitrarily: `Dog ⊑ ∃hasOwner.(Person ⊓ ¬Child)`.
A tableau rule for every possible nesting would be unmanageable. Instead we

1. push negations inward to a canonical **negation normal form** (NNF),
2. give every complex subexpression its own **fresh name** (structural
   transformation), so each axiom mentions only shallow pieces, and
3. rewrite each shallow axiom as one or more **DL-clauses**, a single rule
   format the engine understands.

The result is logically *equisatisfiable* with the input: the transformed
ontology is consistent exactly when the original is. (Fresh names are
existentially harmless — they only abbreviate.)

## 2. Negation normal form (NNF)

A concept is in **NNF** if negation (`¬`) appears only directly in front of
atomic concepts. You reach NNF by repeatedly applying De Morgan-style rewrites:

```
¬(C ⊓ D)  ⇒  ¬C ⊔ ¬D            ¬(∃r.C)  ⇒  ∀r.¬C
¬(C ⊔ D)  ⇒  ¬C ⊓ ¬D            ¬(∀r.C)  ⇒  ∃r.¬C
¬¬C       ⇒  C                  ¬(≥n r.C) ⇒ ≤(n-1) r.C    (and dually)
```

In pyhermit this is `ExpressionManager.get_nnf` and its complement helper
`get_complement_nnf` (`src/hermit/structural/expression_manager.py`). The
visitor methods `to_nnf` / `complement_to_nnf` implement the table above for
class expressions and data ranges.

> Example: `¬(Person ⊓ ¬Child)` becomes `¬Person ⊔ Child`. Now the only
> negation is on the atomic `Person`.

## 3. Structural transformation (naming subexpressions)

After NNF, the **normalization** phase
(`OWLNormalization.normalize`, `src/hermit/structural/owl_normalization.py`)
walks each axiom and replaces every *complex* subconcept with a freshly invented
atomic concept `Q`, while emitting an axiom that *defines* `Q`. This keeps each
emitted inclusion shallow.

> `Dog ⊑ ∃hasOwner.(Person ⊓ Adult)` becomes two axioms:
>
> - `Dog ⊑ ∃hasOwner.Q`
> - `Q ≡ Person ⊓ Adult`   (defining the fresh `Q`)

The output is a `NormalizedAxioms` object
(`src/hermit/structural/normalized_axioms.py`). Its central field is

```python
concept_inclusions: list[tuple[AtomicConcept, ...]]
```

Each tuple is read as a **disjunction of concepts that must cover ⊤** — i.e. the
GCI `⊤ ⊑ D1 ⊔ D2 ⊔ … ⊔ Dk`. Every TBox inclusion is massaged into this
"one big disjunction" shape. The trick: `A ⊑ B` is logically `⊤ ⊑ ¬A ⊔ B`, so it
becomes the tuple `(¬A, B)` — a disjunction containing one negated atom and one
positive atom. `NormalizedAxioms.add_concept_inclusion` builds these tuples.

`NormalizedAxioms` also holds the RBox (object/data property inclusions,
characteristics) and ABox (facts), each in its own typed field, plus expressivity
flags (`has_nominals`, `has_inverse_roles`, …) the tableau reads later.

## 4. Clausification: disjunction-of-concepts → DL-clause

A **DL-clause** is an implication

```
H1 ∨ H2 ∨ … ∨ Hm   :-   B1 ∧ B2 ∧ … ∧ Bn
```

read right-to-left: *if all body atoms `Bi` hold, then at least one head atom
`Hj` holds.* With an empty head it means "the body is contradictory"
(`… :- B` with no head = `B → ⊥`). With an empty body it is an unconditional
disjunction. pyhermit's class is `hermit.model.DLClause`, with
`head_atoms` and `body_atoms` (`src/hermit/model/__init__.py:1002`); construct
with `DLClause.create(head, body)`. The atoms are `hermit.model.Atom`s over a
shared variable `X` (and fresh `Y`, `Z` for successors).

`OWLClausification.clausify` (`src/hermit/structural/owl_clausification.py:102`)
loops over `concept_inclusions` and hands each disjunction tuple to a
`NormalizedAxiomClausifier` visitor. The visitor's rule (read its docstring at
`:432` and methods at `:519`+) is the crux:

- a **positive** atomic concept `D` in the disjunction → a **head** atom `D(X)`
  (`visit_atomic_concept`, `:521`);
- a **negated** atomic concept `¬A` → a **body** atom `A(X)`
  (`visit_atomic_negation_concept`, `:525`) — negation in the head flips to a
  positive premise in the body;
- an `AtLeastConcept` (`≥n r.C`, i.e. an existential) → a **head** atom
  `(≥n r.C)(X)` (`visit_at_least_concept`, `:532`); the tableau expands it later;
- equalities / inequalities (from keys, functionality) land in head as
  `Equality.INSTANCE` / `Inequality.INSTANCE` atoms.

So the disjunction `¬A ⊔ B` (which is `A ⊑ B`) clausifies to **`B(X) :- A(X)`**.
Exactly the "if A then B" rule we want.

### Properties and characteristics

RBox axioms clausify directly: `r ⊑ s` → `s(X,Y) :- r(X,Y)`; transitivity
`r ∘ r ⊑ r` → `r(X,Z) :- r(X,Y) ∧ r(Y,Z)`; functionality → an equality-head
clause `X ≈ Y :- r(Z,X) ∧ r(Z,Y)`. `HasKey` clausification is visible at
`_clausify_object_key` / `_clausify_data_key`
(`src/hermit/structural/owl_clausification.py:347`, `:380`). Non-simple-property
misuse is rejected here (`ObjectPropertyInclusionManager`).

### Facts

ABox assertions become ground `Atom`s in `positive_facts` / `negative_facts` of
the resulting `DLOntology` (`clausify_facts`, `:826`).

## 5. Full worked example

Input ontology:

```
Dog ⊑ Animal
Animal ⊑ ∃hasParent.Animal
Dog(fido)
```

**Normalize.** `∃hasParent.Animal` is already shallow (its filler is atomic), so
no fresh concept is needed. The two GCIs become the inclusion tuples

```
(¬Dog, Animal)                         # Dog ⊑ Animal
(¬Animal, (≥1 hasParent.Animal))       # Animal ⊑ ∃hasParent.Animal
```

**Clausify.** Applying the visitor rules:

```
Animal(X)              :-  Dog(X)            # from (¬Dog, Animal)
(≥1 hasParent.Animal)(X) :- Animal(X)        # from (¬Animal, ≥1 …)
```

plus the fact `Dog(fido)`. This is the `DLOntology` the tableau receives
(`DLOntology.get_dl_clauses()`, `get_positive_facts()`,
`src/hermit/model/__init__.py:2186`).

When the tableau runs (Chapter 03) it will: load `Dog(fido)`; fire clause 1 to
derive `Animal(fido)`; fire clause 2 to derive `(≥1 hasParent.Animal)(fido)`;
then *existential expansion* invents an anonymous parent node that is itself an
`Animal`, which fires clause 2 again… forever, unless **blocking** (Chapter 04)
stops it. That non-termination risk is exactly why blocking exists.

## 6. What you now have

After this stage the ontology is a flat set of DL-clauses plus ground facts —
the input contract of `Tableau.is_satisfiable`. Everything OWL-specific (RDF
parsing, nested concepts, sugar axioms) is behind us. The engine from here on
manipulates only clauses, atoms, nodes, and dependency sets.

---

Previous: [01 — Description Logic](01-description-logic.md) · Next:
[03 — The Hypertableau Calculus](03-hypertableau-calculus.md)
