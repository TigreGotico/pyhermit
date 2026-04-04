# Sprint: Python Port of HermiT OWL 2 DL Reasoner

## Sprint Goal
A fully functional, algorithm-faithful Python port of HermiT 1.3.8 is published on PyPI, passing all 60 HermiT test classes with full OWL 2 DL conformance, installable via `pip install hermit-reasoner`.

## In Scope
- Direct, algorithm-faithful translation of all 199 Java source files to Python
- Port of all 60 test classes (~12.5K lines) with equivalent assertions
- Full OWL 2 DL construct support (classes, properties, datatypes, restrictions, axioms)
- All datatype handlers (float, double, decimal, integer, dateTime, boolean, anyURI, xml:literal, rdf:PlainLiteral, binary)
- Tableau engine with HermiT's blocking strategy (single, double, anywhere blocking)
- Hierarchy classification (class, object property, data property)
- Instance manager (instance retrieval, realization)
- Incremental ABox loading/unloading
- SWRL rule support (DL-safe rules)
- Datalog conjunctive query engine
- Entailment checking
- CLI interface (classify, realize, test consistency, entailment)
- PyPI packaging with `pyproject.toml`, type hints, pytest suite
- Comprehensive documentation (API docs, usage examples, contributor guide)
- CI pipeline (GitHub Actions) with test matrix

## Out of Scope
- Protégé plugin / GUI components
- Java-specific build artifacts (Ant, Eclipse project files)
- JPype / JVM interop layer
- Rust/Cython performance optimizations (deferred to future sprints)
- Extensions beyond HermiT 1.3.8 feature set
- Integration with LLM frameworks or knowledge graph libraries (downstream consumers, not in-scope)

## Success Criteria
- [ ] `pip install hermit-reasoner` works on Python 3.10+ (Linux, macOS, Windows)
- [ ] All 60 ported test classes pass with 100% parity against HermiT's Java test results
- [ ] Reasoner correctly classifies at least 5 standard OWL 2 DL ontologies (e.g., Wine, Pizza, Koala, Gene Ontology fragment, FORTH ontology)
- [ ] Full OWL 2 DL conformance verified against the OWL 2 DL test cases from W3C
- [ ] Public API has type hints on all public functions/classes, passes `mypy --strict`
- [ ] Package installs with zero JVM dependency
- [ ] Documentation includes: quickstart guide, API reference, architecture overview, contributing guide
- [ ] CI runs full test suite on push, publishes coverage report, blocks merge on failure
- [ ] LGPL 3.0 license applied, all dependencies audited for license compatibility
