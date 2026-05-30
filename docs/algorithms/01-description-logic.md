# 01 — Description Logic from Scratch

This chapter builds the logical vocabulary you need. We assume only sets and
basic propositional logic (`∧` and, `∨` or, `¬` not, `→` implies, `∀` for-all,
`∃` exists). By the end you will be able to read every formula in this guide and
state precisely what "consistent", "entails", "subsumes", and "classify" mean.

## 1. The three kinds of thing

A **Description Logic** (DL) describes a *domain* — a set of objects — using
three kinds of name:

- **Individuals** name single objects: `fido`, `john`. In pyhermit an individual
  is `hermit.model.Individual` (`src/hermit/model/__init__.py`).
- **Atomic concepts** name *sets* of objects (classes): `Dog`, `Animal`. In
  pyhermit, `hermit.model.AtomicConcept`. The two special concepts are
  `⊤` ("Thing", everything; `AtomicConcept.THING`) and `⊥` ("Nothing", the empty
  set; `AtomicConcept.NOTHING`).
- **Atomic roles** name *binary relations* (sets of ordered pairs): `hasOwner`,
  `hasParent`. In pyhermit, `hermit.model.AtomicRole`.

### Interpretations (the meaning of names)

To say what a formula *means*, fix an **interpretation** `I`:

- a non-empty set `ΔI` — the **domain** of objects;
- for each individual `a`, an object `aI ∈ ΔI`;
- for each atomic concept `A`, a subset `AI ⊆ ΔI`;
- for each atomic role `r`, a set of pairs `rI ⊆ ΔI × ΔI`.

An interpretation is just one concrete "possible world." Reasoning asks what is
true in *all* such worlds.

## 2. Building complex concepts (the SROIQ constructs)

OWL 2 DL corresponds to the description logic **SROIQ**. The name is an acronym
for the features it bundles; we introduce each construct with its syntax,
meaning, and a pyhermit class where one exists. `C`, `D` are concepts; `r` a
role; `a` an individual; `n` a non-negative integer.

| Construct | Syntax | Meaning (`·I`) | OWL keyword |
|-----------|--------|----------------|-------------|
| Conjunction | `C ⊓ D` | `CI ∩ DI` | `ObjectIntersectionOf` |
| Disjunction | `C ⊔ D` | `CI ∪ DI` | `ObjectUnionOf` |
| Negation | `¬C` | `ΔI \ CI` | `ObjectComplementOf` |
| Existential | `∃r.C` | objects with *some* `r`-successor in `C` | `ObjectSomeValuesFrom` |
| Universal | `∀r.C` | objects *all* of whose `r`-successors are in `C` | `ObjectAllValuesFrom` |
| At-least (Q) | `≥n r.C` | objects with `≥ n` distinct `r`-successors in `C` | `ObjectMinCardinality` |
| At-most (Q) | `≤n r.C` | objects with `≤ n` distinct `r`-successors in `C` | `ObjectMaxCardinality` |
| Nominal (O) | `{a}` | the singleton `{aI}` | `ObjectOneOf` |
| Self | `∃r.Self` | objects `r`-related to themselves | `ObjectHasSelf` |

The letters of **SROIQ**: **S** = the base logic ALC plus transitive roles;
**R** = role hierarchies and complex role inclusions (role chains); **O** =
nominals `{a}`; **I** = inverse roles `r⁻`; **Q** = qualified number
restrictions `≥n r.C`. pyhermit represents these internal concept forms as
`ExistentialConcept`, `AtLeastConcept`, `AtMostConcept`, `AtomicNegationConcept`,
`InverseRole`, etc. (all in `hermit.model`). Note: `∀r.C` and `≤n r.C` are
*defined away* during clausification (Chapter 02), so you will not see a separate
"ForAll" tableau concept — `∀r.C` becomes `≤0 r.¬C`-style clauses.

### Worked meaning

Let `ΔI = {1, 2, 3}`, `DogI = {1}`, `AnimalI = {1, 2}`,
`hasOwnerI = {(1, 3)}`. Then:

- `(∃hasOwner.⊤)I` = objects with some owner = `{1}` (only object 1 has an
  outgoing `hasOwner` pair).
- `(Dog ⊓ Animal)I` = `{1} ∩ {1,2}` = `{1}`.
- `(¬Animal)I` = `{1,2,3} \ {1,2}` = `{3}`.

## 3. Axioms: TBox, RBox, ABox

An **ontology** is a set of axioms in three groups.

### TBox — terminological axioms (rules about concepts)

- **Concept inclusion** (GCI, "general concept inclusion"): `C ⊑ D`, true in `I`
  iff `CI ⊆ DI`. Read "every C is a D." OWL `SubClassOf`.
- **Equivalence**: `C ≡ D` abbreviates `C ⊑ D` and `D ⊑ C`. OWL
  `EquivalentClasses`.
- **Disjointness**: `C ⊓ D ⊑ ⊥` ("no object is both"). OWL `DisjointClasses`.

### RBox — role axioms (rules about roles)

- **Role inclusion**: `r ⊑ s` (every `r`-pair is an `s`-pair).
- **Role chain**: `r ∘ s ⊑ t` (if `r(x,y)` and `s(y,z)` then `t(x,z)`).
  Transitivity is the special case `r ∘ r ⊑ r`.
- **Inverse**: `s ≡ r⁻` (`s(x,y)` iff `r(y,x)`).
- **Characteristics**: functional, inverse-functional, symmetric, asymmetric,
  reflexive, irreflexive. Each is sugar for an inclusion or a clause.

A role used in a number restriction (`≥n r.C`), `Self`, or a disjointness must be
**simple** — not transitive and not implied by a chain. pyhermit enforces this at
clausification and raises `ValueError`; see
`structural/object_property_inclusion_manager.py`.

### ABox — assertional axioms (facts about individuals)

- **Concept assertion**: `C(a)` ("a is a C"). OWL `ClassAssertion`.
- **Role assertion**: `r(a, b)`. OWL `ObjectPropertyAssertion`.
- **(In)equality**: `a ≈ b` (same), `a ≉ b` (different). OWL
  `SameIndividual` / `DifferentIndividuals`. pyhermit: `Equality.INSTANCE`,
  `Inequality.INSTANCE`.

In pyhermit's internal form a fact is an `Atom` (`hermit.model.Atom`) whose
`predicate` is the concept/role and whose arguments are the individuals. The
clausified ontology stores them as `DLOntology.get_positive_facts()` and
`get_negative_facts()` (`src/hermit/model/__init__.py`).

## 4. Models and the open-world assumption

An interpretation `I` is a **model** of an ontology `O` if **every** axiom of `O`
is true in `I`. Write `I ⊨ O`.

DL uses the **open-world assumption (OWA)**: a statement not entailed is *not*
therefore false — it is merely *unknown*. This is the opposite of a database
(closed world). Example: from `hasOwner(fido, john)` alone you may **not**
conclude "fido has no other owner." Some model might give fido a second,
unnamed owner. The reasoner only commits to what holds in *all* models.

This is why `∃hasOwner.Person` can be satisfied by inventing a fresh, anonymous
owner: the OWA permits objects the ontology never named. The tableau (Chapter 03)
literally creates such anonymous **tree nodes**.

## 5. The four reasoning tasks, defined precisely

Let `O` be an ontology.

### Consistency (a.k.a. satisfiability of the ontology)

`O` is **consistent** iff it has at least one model. If no interpretation makes
every axiom true, `O` is **inconsistent**.

> Tiny inconsistent ontology:
> `Penguin ⊑ Bird`, `Bird ⊑ CanFly`, `Penguin ⊑ ¬CanFly`, `Penguin(pingu)`.
> Any model must put `pingu` in `Penguin`, hence `Bird`, hence `CanFly`; but also
> in `¬CanFly`. No object can be in both `CanFly` and its complement. No model
> exists. **Inconsistent.**

pyhermit entry point: `Reasoner.is_consistent()` (`src/hermit/reasoner.py`),
which calls the tableau via `Tableau.is_satisfiable(...)`.

### Entailment

`O` **entails** an axiom `α`, written `O ⊨ α`, iff `α` is true in *every* model
of `O`. This is the master notion. pyhermit: `hermit.entailment_checker.
EntailmentChecker.entails(...)`.

**The reduction to consistency.** `O ⊨ α` iff `O ∪ {¬α}` is inconsistent.
Negate the thing you want to prove; if that explodes, the original held. This
single trick turns every task below into a consistency check, which is why the
tableau is the whole engine.

### Subsumption

Concept `C` is **subsumed by** `D` w.r.t. `O` (`O ⊨ C ⊑ D`) iff in every model
`CI ⊆ DI`. By the reduction: test whether `O ∪ {(C ⊓ ¬D)(x)}` is inconsistent
for a fresh individual `x` — i.e., whether it is *impossible* to be a `C` that is
not a `D`.

> Worked: does `Dog ⊑ Animal` follow from `O = {Dog ⊑ Animal}`? Add a fresh `x`
> with `Dog(x)` and `¬Animal(x)`. The TBox rule forces `Animal(x)`. Now `x` is in
> both `Animal` and `¬Animal` — clash. So `O ∪ {(Dog ⊓ ¬Animal)(x)}` is
> inconsistent, hence `O ⊨ Dog ⊑ Animal`. **Yes.**

pyhermit: `Reasoner.is_sub_class_of(sub, sup)` (`src/hermit/reasoner.py:362`).
Read it and you will see exactly this: build a fresh anonymous individual, assert
`sub(x)` and `sup.get_negation()(x)`, and return `not is_satisfiable(...)`.

### Classification

**Classification** computes the *entire* subsumption hierarchy: for every pair of
named atomic concepts, decide `⊑`, and arrange the results into a directed graph
(the **class hierarchy**) with `⊤` at the top and `⊥` at the bottom. Equivalent
concepts collapse into one node. Done naively this is one subsumption test per
ordered pair (`O(n²)` tableau calls); Chapter 07 shows the quasi-order
optimisation pyhermit uses to do far fewer. Entry: `Reasoner.classify_classes()`
(`src/hermit/reasoner.py:608`), result type `Hierarchy`
(`src/hermit/hierarchy/hierarchy.py`).

### Instance retrieval

The ABox analogue of classification: which individuals are provably instances of
a concept `C`? `O ⊨ C(a)` iff `O ∪ {¬C(a)}` is inconsistent. pyhermit:
`Reasoner.has_type(individual, concept)` and `Reasoner.get_instances(concept)`
(`src/hermit/reasoner.py:467`, `:524`), with bulk retrieval optimised by
`hierarchy/instance_manager.py`.

## 6. Putting it together

Every high-level question becomes "is *this* ontology consistent?", and
consistency is decided by constructing a model with the tableau. Before the
tableau can run, OWL's rich syntax must be flattened into a uniform clause form.
That translation is the next chapter.

---

Previous: [00 — Overview](00-overview.md) · Next:
[02 — Normalization & Clausification](02-normalization-clausification.md)
