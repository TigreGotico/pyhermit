# 00 — Overview: What a DL Reasoner Does

This chapter gives you the whole picture in one read, so the later detailed
chapters have a frame to hang on. Nothing here is assumed; everything is
re-explained more carefully later.

## 1. The one-sentence summary

> A **reasoner** takes an **ontology** (a set of logical statements about a domain)
> and answers questions that follow *logically* from it — even questions whose
> answers were never written down explicitly.

pyhermit is such a reasoner for the **OWL 2 DL** language. OWL ("Web Ontology
Language") is a W3C standard for writing ontologies. "DL" means it is the
**Description-Logic** profile of OWL: a fragment carefully designed so that the
questions below are *decidable* (a program is guaranteed to terminate with a
correct yes/no answer).

## 2. What is an ontology, concretely?

An ontology is built from three kinds of building block. (Chapter 01 defines
each precisely; here is the intuition.)

- **Concepts** (a.k.a. *classes*): sets of things. `Dog`, `Animal`, `Person`.
- **Roles** (a.k.a. *properties*, *relations*): binary relationships between
  things. `hasOwner`, `hasParent`.
- **Individuals**: specific named things. `fido`, `john`.

And three kinds of statement:

- **TBox** ("terminology"): general rules. *"Every Dog is an Animal"* —
  written `Dog ⊑ Animal` (read "Dog is a subclass of Animal").
- **ABox** ("assertions"): facts about individuals. *"fido is a Dog"*,
  *"fido hasOwner john"*.
- **RBox** ("roles"): rules about the roles themselves. *"hasParent is
  transitive"*, *"hasChild is the inverse of hasParent"*.

A complete tiny ontology:

```
TBox:  Dog ⊑ Animal
ABox:  Dog(fido)
       hasOwner(fido, john)
```

## 3. The questions a reasoner answers

Given an ontology *O*, the four core tasks are:

1. **Consistency** — *Is O even self-consistent?* Could there be a world
   (a "model") in which every statement is true at once? If `Penguin ⊑ Bird`,
   `Bird ⊑ CanFly`, `Penguin ⊑ ¬CanFly`, and `Penguin(pingu)`, then *no* such
   world exists: the ontology is **inconsistent**. An inconsistent ontology
   entails *everything* and is useless, so this is checked first.

2. **Classification** — *For every pair of named concepts, is one a subclass of
   the other?* The result is the **class hierarchy**: a graph of all the
   `⊑` relationships that follow from *O*, including ones not stated directly.
   From `Dog ⊑ Animal` alone we also learn `Dog ⊑ Animal` is the only edge; but
   adding `Puppy ⊑ Dog` lets the reasoner *derive* `Puppy ⊑ Animal`.

3. **Instance retrieval** — *Which individuals belong to a given concept?*
   From `Dog(fido)` and `Dog ⊑ Animal`, the reasoner answers "is fido an
   Animal?" with **yes**, even though `Animal(fido)` was never written.

4. **Entailment** — the general form of all the above: *does statement S
   follow from O?* Subsumption, instance, and consistency questions are all
   special cases.

The deep idea that unifies them (Chapter 01 develops it): **every one of these
questions reduces to a consistency check.** "Does `Dog ⊑ Animal` follow?" is
answered by asking "is it *inconsistent* to have a Dog that is *not* an
Animal?" If yes, the subsumption holds. This reduction is why the heart of
pyhermit is a single consistency procedure — the **tableau**.

## 4. The pipeline

pyhermit transforms an ontology through five stages. Each stage is a chapter.

```
  OWL ontology file (RDF/XML, OWL/XML, or Functional-Style Syntax)
        |
        |   (1) PARSE                         src/hermit/parser.py + readers
        v
  list[OWLAxiom]   -- in-memory objects, one per logical statement
        |
        |   (2) NORMALIZE                     src/hermit/structural/owl_normalization.py
        v
  NormalizedAxioms -- axioms in a uniform "negation normal form",
        |              complex subexpressions named by fresh concepts
        |
        |   (3) CLAUSIFY                       src/hermit/structural/owl_clausification.py
        v
  DLOntology       -- a set of DL-clauses (logical implications) + facts.
        |              This is the form the reasoning engine consumes.
        |
        |   (4) TABLEAU (the engine)           src/hermit/tableau/tableau.py
        v
  satisfiable? (yes/no)  -- builds a candidate model; reports clash or success
        |
        |   (5) CLASSIFY / QUERY               src/hermit/hierarchy/, reasoner.py
        v
  class hierarchy, instances, entailments      src/hermit/reasoner.py  (Reasoner)
```

Stages 1-3 are *preprocessing*: they translate human-facing OWL into a clean
internal logic. Stage 4 is the *decision procedure*: the hypertableau calculus,
the algorithmic core and the hardest part. Stage 5 *orchestrates* many tableau
calls to answer high-level queries.

### Where each stage lives

| Stage | Entry point | Chapter |
|-------|-------------|---------|
| Parse | `hermit.parser.load_ontology` | 08 (loader), audit |
| Normalize | `hermit.structural.owl_normalization.OWLNormalization.normalize` | 02 |
| Clausify | `hermit.structural.owl_clausification.OWLClausification.clausify` | 02 |
| Tableau | `hermit.tableau.tableau.Tableau.is_satisfiable` | 03, 04, 05, 06 |
| Classify / query | `hermit.reasoner.Reasoner` | 07 |

## 5. A worked end-to-end trace (high level)

Take the tiny ontology from §2 and ask: **is `fido` an `Animal`?**

1. **Parse / normalize / clausify** turn `Dog ⊑ Animal` into the DL-clause
   `Animal(X) :- Dog(X)` (read: "for all X, if Dog(X) then Animal(X)"), and the
   ABox into the facts `Dog(fido)`, `hasOwner(fido, john)`.

2. The `Reasoner` reduces the query. "Is fido an Animal?" becomes:
   *"Is the ontology together with `¬Animal(fido)` inconsistent?"* If adding
   "fido is **not** an Animal" produces a contradiction, the answer is yes.

3. The **tableau** loads the facts onto tableau **nodes** (one per individual),
   then fires the clause: `Dog(fido)` is present, so it derives `Animal(fido)`.
   But we also asserted `¬Animal(fido)`. Both `Animal(fido)` and `¬Animal(fido)`
   on the same node is a **clash** (contradiction).

4. Clash -> the augmented ontology is inconsistent -> the original entailment
   **holds**. The reasoner answers **yes, fido is an Animal.**

That single derive-and-clash loop, generalized to handle existentials,
disjunctions, equalities, datatypes, and infinite models, is the whole engine.
The next chapters unpack it.

## 6. Why "hyper" tableau?

A classic DL tableau processes one concept at a time. The **hypertableau**
calculus (Motik, Shearer, Horrocks, *Hypertableau Reasoning for Description
Logics*, JAIR 2009) instead works with **DL-clauses** — implications with
several atoms in the body — and fires a whole clause in one step via
**hyperresolution** (Chapter 03). This produces far less nondeterministic
branching, which is the main reason HermiT (and pyhermit) scales. pyhermit is a
structural port of HermiT, so its engine implements exactly this calculus.

---

Next: [01 — Description Logic](01-description-logic.md).
