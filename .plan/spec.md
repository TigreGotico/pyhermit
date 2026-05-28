# Spec: pyhermit Production Readiness

## Objective

pyhermit is a Python port of the Java HermiT OWL 2 DL tableau reasoner. The core tableau engine is correct and complete, but four issues block production use: (1) the owlready2 parser silently discards complex class expressions, causing wrong answers without any error; (2) four source files disable mypy entirely due to a type-system mismatch in `NormalizedAxioms`; (3) a stub in the datatype manager causes unsound handling of unknown XSD facets; (4) the test suite verifies pipeline structure but not reasoning correctness. This spec defines what must be true for pyhermit to be dependably usable by external consumers.

## Functional Requirements

1. **Parser preserves complex class expressions.** `load_ontology()` must extract `OWLObjectSomeValuesFrom`, `OWLObjectAllValuesFrom`, `OWLObjectMinCardinality`, `OWLObjectMaxCardinality`, `OWLObjectExactCardinality`, `OWLObjectHasSelf`, `OWLObjectHasValue`, `OWLObjectOneOf`, `OWLObjectUnionOf`, `OWLObjectIntersectionOf`, and `OWLObjectComplementOf` from owlready2 class definitions. No class expression that owlready2 encodes in `is_a` or `equivalent_to` may be silently dropped.

2. **`NormalizedAxioms` exposes typed fact lists.** The class must provide `positive_concept_facts`, `positive_role_facts`, and `positive_data_facts` as distinct typed lists in addition to the existing `positive_facts` catch-all. `OWLNormalization._process_axiom()` must route each axiom type to the correct typed list.

3. **`OWLClausification.clausify()` consumes typed fact lists.** Clausification must read from typed lists where it currently reads from the untyped `positive_facts`, ensuring correct handling of ABox assertions and property axioms.

4. **mypy runs clean on all source files.** `mypy --strict src/hermit` must exit 0. The four files currently carrying `# mypy: ignore-errors` (`owl_normalization.py`, `expression_manager.py`, `object_property_inclusion_manager.py`, `builtin_property_manager.py`) must either be fixed or, in the case of `builtin_property_manager.py`, integrated or deleted.

5. **Unknown datatype restriction handling is sound.** `datatype_manager.py` must not contain stub `pass` statements in any method on the reasoning path. Unknown XSD facets must generate pairwise inequality constraints between ABox individuals, matching Java HermiT's behaviour.

6. **Reasoning correctness is verified by tests.** `tests/test_correctness.py` must contain at least 20 tests that assert specific boolean answers from `is_satisfiable()`, `is_sub_class_of()`, or `is_consistent()` on ontologies involving: object property restrictions, cardinality constraints, transitive roles, nominal individuals, and datatype constraints. Each test must include a comment explaining the expected answer.

7. **ruff reports no violations.** `ruff check src/hermit` must exit 0 after all changes.

8. **Package version reflects beta status.** `pyproject.toml` version must be `0.2.0`, classifier must include `Development Status :: 4 - Beta`.

## Non-Goals

- Rewriting or modifying the tableau engine (`src/hermit/tableau/`). It is correct and complex; changes risk regressions without proportional benefit.
- Implementing OWL 2 profiles (EL, QL, RL) as distinct reasoner modes. Profile-optimised reasoning is a future concern.
- Switching from owlready2 to OWLAPI or another parser library.
- Full support for SWRL built-ins beyond what is already implemented.
- GUI, REST API, or any interface beyond the existing Python API and CLI.
- Performance optimisation, benchmarking, or profiling.
- Publishing to PyPI — that follows once this spec is met, but is not part of this work.

## Interfaces & Contracts

- **`hermit.parser.load_ontology(path) → list[OWLAxiom]`** — must return all logical axioms including those with complex class expressions; owlready2 is an optional dependency, import guarded.
- **`NormalizedAxioms.positive_concept_facts: list[OWLClassAssertionAxiom]`** — new field; populated by `OWLNormalization`.
- **`NormalizedAxioms.positive_role_facts: list[OWLObjectPropertyAssertionAxiom | OWLDataPropertyAssertionAxiom]`** — new field.
- **`NormalizedAxioms.positive_data_facts: list`** — new field for data-property-related facts.
- **`NormalizedAxioms.positive_facts: list`** — retained as catch-all for unrecognised axiom types; callers that don't need the split continue to work.
- **mypy contract** — `mypy --strict src/hermit` exits 0; no `type: ignore` comments added as workarounds.
- **Test contract** — `pytest tests/test_correctness.py` exits 0; all 20+ tests pass; no `xfail` marks on correctness tests.

## Acceptance Criteria

- [ ] `python -c "from hermit.parser import load_ontology"` succeeds (owlready2 present) and returns axioms including `OWLObjectSomeValuesFrom` for an ontology that uses existential restrictions
- [ ] `mypy --strict src/hermit` exits with code 0 and prints no errors
- [ ] `ruff check src/hermit` exits with code 0
- [ ] `pytest` exits 0 with 0 failures and 0 skips (excluding any pre-existing `xfail` on unrelated features)
- [ ] `pytest tests/test_correctness.py -v` shows ≥ 20 passing tests, each asserting a specific True/False reasoning answer
- [ ] `grep -r "mypy: ignore-errors" src/hermit/` returns no results
- [ ] `grep -r "^    pass$" src/hermit/structural/builtin_property_manager.py` returns no results (file integrated or deleted)
- [ ] `grep -rn "pass  # stub\|pass  # Skip\|pass  # Description graph" src/hermit/tableau/` returns no results in reasoning-path methods (description-graph pass stubs resolved or explicitly `raise NotImplementedError`)
- [ ] `python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); assert d['project']['version']=='0.2.0'"` passes
- [ ] A `NormalizedAxioms` instance has attributes `positive_concept_facts`, `positive_role_facts`, `positive_data_facts` and they are non-overlapping with each other for a typical ontology load
