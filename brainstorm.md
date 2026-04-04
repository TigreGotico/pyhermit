# Brainstorm: Python Port of HermiT OWL 2 DL Reasoner

## Problem Statement
HermiT is a mature, conformant OWL 2 DL reasoner written in Java, last updated in 2014. There is no modern, actively-maintained Python OWL 2 DL reasoner with full feature parity. The Python ecosystem (knowledge graphs, LLM tooling, semantic web libraries) lacks a native, high-performance OWL 2 DL tableau reasoner without JVM dependencies.

## Ideas & Approaches
- **Direct algorithm-faithful port** — Translate HermiT's Java source line-by-line into Python, preserving tableau expansion rules, blocking strategies, and hierarchy classification exactly. Safest route to correctness parity.
- **From-scratch Python rewrite** — Re-implement OWL 2 DL reasoning algorithms using Python idioms (dataclasses, type hints, NumPy). Higher long-term maintainability but much higher risk of correctness divergence.
- **Hybrid approach** — Faithfully port the core tableau engine and datatype handlers, but redesign public APIs, CLI, and packaging with modern Python conventions.
- **Incremental port with Java interop bridge** — Start with a thin Python wrapper around HermiT's JAR via JPype, then progressively replace Java modules with Python equivalents. Low risk but introduces JVM dependency initially.
- **Modular port with pluggable backends** — Port HermiT in layers (datatype engine → tableau → hierarchy → SWRL → Datalog), allowing each layer to be tested and released independently.
- **Rust core + Python bindings** — Port the performance-critical tableau engine to Rust, expose via PyO3. Highest performance but dramatically increases complexity and contributor barrier.

## Constraints
- **Full feature parity** with HermiT 1.3.8: all OWL 2 DL constructs, datatype handlers, hierarchy classification, SWRL rules, Datalog queries, CLI, incremental ABox updates, entailment checking
- **Algorithm-faithful translation** — preserve HermiT's exact algorithms and data structures as closely as Python allows
- **PyPI packaging** — standard `pyproject.toml`, type hints, pytest test suite, no JVM dependency
- **199 Java source files** (~50-80K lines of Java) to translate
- **60 test classes** (~12.5K lines) to port and adapt
- **LGPL 3.0 license** — HermiT is LGPL 3.0; the port must remain LGPL 3.0 compatible
- **OWL API 3.x dependency** — HermiT depends on the Java OWL API; the Python port needs an OWL ontology abstraction layer (e.g., `owlready2`, `rdflib`, or a custom lightweight model)

## Open Questions
- What OWL ontology abstraction layer should the Python port use? (owlready2, rdflib, owl-django-style custom, or a minimal internal model?)
- Should the port target Python 3.10+ (modern features like structural pattern matching, `|` union types) or be more backward-compatible (3.8+)?
- How to handle HermiT's use of Java-specific features (enums, generics, iterators, synchronized collections) in Python?
- What is the strategy for the ~130K lines of combined source + test code? Full port in one sweep or phased release?
- Should the port preserve HermiT's internal class naming (`AtomicConcept`, `DataRange`, `Tableau`) or rename to Pythonic conventions?
- Performance expectations — HermiT is known for good performance; pure Python may be 10-100x slower. Is Cython/Rust for hot paths acceptable later?
- How to handle HermiT's dependency on external libraries (dk.brics.automaton, JAutomata, Apache Axiom)? Are there Python equivalents?

## Risks
- **Performance degradation** — Pure Python tableau expansion may be orders of magnitude slower than Java. *Mitigation:* Profile early, identify hot paths, consider Cython/Numba/Rust for critical loops.
- **Correctness divergence** — Faithful translation doesn't guarantee identical results on edge cases. *Mitigation:* Run the full HermiT test suite (60 classes, 12.5K lines) against the Python port; every test must pass.
- **Scope explosion** — 199 files + full OWL 2 DL conformance is a massive undertaking. *Mitigation:* Phase the release (core tableau → datatypes → hierarchy → SWRL → Datalog → CLI) with clear milestones.
- **Maintainer burnout** — This is a multi-thousand-hour project. *Mitigation:* Design for community contribution — clean code, extensive docs, good first issues, contributor guide.
- **License incompatibility** — Chosen dependencies must be LGPL 3.0 compatible. *Mitigation:* Audit all transitive dependencies before adoption.
- **OWL API replacement gap** — No Python library fully replicates the OWL API 3.x abstraction. *Mitigation:* Build a thin, HermiT-specific ontology model layer rather than depending on a general-purpose library.
