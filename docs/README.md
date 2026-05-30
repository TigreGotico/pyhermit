# pyhermit — Learning Guide

This is a from-scratch course in **OWL 2 DL reasoning** and a tour of how
**pyhermit** (a Python port of the Java [HermiT](https://github.com/phillord/hermit-reasoner)
reasoner) implements it. It assumes you know basic logic, sets, and Python, but
**no** description logic or tableau reasoning. Every term is defined on first use.

Read the chapters in order. Each one builds on the last, traces small worked
examples step by step, and cross-references the real source files in
`src/hermit/` so you can read code alongside theory.

## Reading order

| # | Chapter | What you learn |
|---|---------|----------------|
| 00 | [Overview](algorithms/00-overview.md) | The big picture: ontology in -> consistency / classification / entailment out. The five-stage pipeline. |
| 01 | [Description Logic](algorithms/01-description-logic.md) | Concepts, roles, individuals; SROIQ constructs; TBox / ABox / RBox; open-world semantics; consistency, entailment, subsumption, classification. |
| 02 | [Normalization & Clausification](algorithms/02-normalization-clausification.md) | Negation normal form, structural transformation, turning OWL axioms into DL-clauses. |
| 03 | [The Hypertableau Calculus](algorithms/03-hypertableau-calculus.md) | Model construction by hyperresolution; the delta ring; existential expansion; ground-disjunction branching; clashes. The keystone inconsistency example, traced. |
| 04 | [Blocking](algorithms/04-blocking.md) | Why naive tableau never stops, and how blocking forces termination. |
| 05 | [Dependency-Directed Backtracking](algorithms/05-dependency-directed-backtracking.md) | Dependency sets, branching points, and backjumping instead of blind retry. |
| 06 | [Datatypes](algorithms/06-datatypes.md) | Concrete domains, datatype restrictions, and datatype clashes. |
| 07 | [Classification & Queries](algorithms/07-classification-and-queries.md) | Subsumption testing, the quasi-order classifier, instance retrieval, conjunctive queries. |
| 08 | [Codebase Map](algorithms/08-codebase-map.md) | Module-by-module: which file implements which algorithm, the data flow, and the Java counterparts. |

## Companion documents

- [`FAITHFULNESS_AUDIT.md`](../FAITHFULNESS_AUDIT.md) — where and *why* pyhermit
  diverges from Java HermiT, with the soundness/completeness/performance
  consequence of each divergence.
- The end-user docs (tutorials, recipes, API) start at [`index.md`](index.md).

## Literature

The algorithms here come from two primary sources, cited inline throughout:

- Motik, Shearer, Horrocks, *Hypertableau Reasoning for Description Logics*,
  Journal of Artificial Intelligence Research 36 (2009), 165-228. (The
  "hypertableau paper". Defines the calculus pyhermit's `Tableau` implements.)
- W3C, *OWL 2 Web Ontology Language: Structural Specification and
  Functional-Style Syntax* (2nd ed., 2012). (Defines the language pyhermit reads.)
