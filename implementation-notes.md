# Implementation Notes: Finish the pyhermit Port

## Patterns to Use

- **`isinstance` dispatch** — used throughout (see `owl_axioms_expressivity.py`); prefer over `singledispatch` for consistency. Pattern: `if isinstance(x, FooClass): ... elif isinstance(x, BarClass): ...`
- **`hermit.model.Interner`** — used for interning DL model objects (`AtomicConcept`, `AtomicRole`, etc.). Use a plain `dict` cache keyed on `(type, *args)` for ExpressionManager results — Interner is for the DL model layer, not OWL expressions.
- **`@dataclass(frozen=True)`** — used for all value-typed structures in `normalized_axioms.py`. New structural types should follow the same pattern.
- **Module-level variable singletons** — `X, Y, Z = Variable.create("X"), ...` in `owl_clausification.py`; follow same pattern for any fresh variables needed in normalization.
- **`__slots__`** — used on hot-path objects (Node, DependencySet, etc.). Use on ExpressionManager visitor state if it holds mutable working state.

## Gotchas

- **`anywhere_blocking.py` DataRange import** — `DataRange` is from `hermit.model`, not `hermit.datatypes`. Check the exact import path before fixing.
- **`branching_point.py` attribute name** — `tableau.last_tableau_node` is a `@property`; accessing `tableau.m_last_tableau_node` raises `AttributeError`. Verify the property name in `tableau/tableau.py` before changing.
- **tuple buffer arity in hyperresolution** — the tuple buffer is `[predicate, *nodes, dep_set]`. Binary = 3 elements total (concept + 1 node + dep_set). Ternary = 4 elements total (role + 2 nodes + dep_set). The extension table's `m_tuple_arity` is 2 for binary, 3 for ternary (does NOT include dep_set slot in the count). Confirm by inspecting `ExtensionTable.__init__`.
- **Vendored file import rewriting** — owlapy uses both absolute (`from owlapy.X import Y`) and relative (`from .X import Y`) imports internally. Relative imports within `hermit/owl_model/` do NOT need changing. Only cross-package absolute `owlapy.*` imports need to become `hermit.owl_model.*`.
- **`owl_literal.py` Timedelta replacement** — `pandas.Timedelta` and `datetime.timedelta` have different string parsing. The ISO 8601 duration format (`P1Y2M3DT4H5M6S`) is NOT natively supported by `datetime.timedelta`. Either (a) implement a minimal ISO 8601 duration parser or (b) use `isodate` library (if already available) or (c) store durations as strings and parse lazily. Check what `parse_duration()` actually does before deciding.
- **ExpressionManager result caching** — Java uses `HashMap` keyed on OWL API objects (which have proper `.equals()`). Python OWL model objects from owlapy use `__eq__` but may not be hashable. Test before using them as dict keys; may need `id()`-based caching or `__hash__` inspection.
- **OWLNormalization fresh concept names** — Java uses `m_firstReplacementIndex` (an int counter passed in) to generate IRIs like `internal:def#0`, `internal:def#1`. Use a `_replacement_counter` instance field starting at the passed-in `first_replacement_index`.
- **OWLNormalization structural transformation** — the key step is `_normalize_inclusions()` which repeatedly applies the structural transformation until no new definitions are added. This is a fixed-point loop — exit condition is "no new entries added to `_definitions` in this pass."
- **ObjectPropertyInclusionManager `rewrite_axioms` polarity tracking** — a class expression appearing in positive polarity (LHS of SubClassOf) needs its automaton states mapped to one set of fresh concepts; negative polarity needs separate fresh concepts. Java tracks this via two separate `Map<OWLObjectPropertyExpression, OWLClass>` maps. Implement the same way.
- **DatalogEngine `materialize()` node mapping** — after `tableau.is_satisfiable()`, walk `tableau.m_first_tableau_node` linked list (via `node.m_next_tableau_node`) to build `_nodes_to_terms`. Only `NAMED` nodes (canonical nodes for individuals) should be mapped; skip tree nodes and blocked nodes.
- **ConjunctiveQuery worker compilation** — reuses `DLClauseEvaluator.ConjunctionCompiler` from `tableau/dl_clause_evaluator.py`. Check that class is accessible (not private) before relying on it; if it is private, extract or duplicate.
- **Remove DEBUG prints** — `hyperresolution_manager.py` has many `print(f"[DEBUG ...")` statements added during development. Remove all of them as part of step 3.

## Key Imports / APIs

- `hermit.model.AtomicConcept` — `AtomicConcept.create(iri: str)`, `AtomicConcept.THING`, `AtomicConcept.NOTHING`
- `hermit.model.AtomicRole` — `AtomicRole.create(iri: str)`, `AtomicRole.TOP_OBJECT_ROLE`, `AtomicRole.BOTTOM_OBJECT_ROLE`
- `hermit.model.Individual` — `Individual.create(iri: str)`
- `hermit.model.Variable` — `Variable.create(name: str)` — X, Y, Z already defined in `owl_clausification.py`
- `hermit.model.Interner` — `Interner()`, `.intern(obj)` returns canonical instance
- `hermit.structural.NormalizedAxioms` — dataclass; mutate in place from BuiltInPropertyManager / ObjectPropertyInclusionManager
- `hermit.structural.ComplexObjectPropertyInclusion` — frozen dataclass `(sub_property_chain: tuple[Role,...], super_property: Role)`
- `hermit.tableau.dl_clause_evaluator.DLClauseEvaluator` — check if `ConjunctionCompiler` is an accessible inner class
- `hermit.tableau.tableau.Tableau` — `is_satisfiable(load_permanent_abox, ...)`, `m_first_tableau_node`, `m_extension_manager`
- `hermit.existentials.abstract_expansion_strategy.AbstractExpansionStrategy` — base for `NullExistentialExpansionStrategy`
- `owlready2.get_ontology(iri).load()` — returns `owlready2.Ontology`; iterate `.axioms()` or use `.general_class_axioms`, `.classes()`, etc.

## Conventions

- **camelCase method names** — existing code uses Java-style camelCase (`get_nnf` in snake_case is fine; be consistent with existing structural files which use `snake_case`). The `ruff N802` ignore means camelCase methods are tolerated but new code should use `snake_case`.
- **Type hints everywhere** — `mypy --strict` is enforced; all new public methods need full annotations.
- **`from __future__ import annotations`** — use in every new file (existing files all do this for forward references).
- **`__slots__`** — required on any class that will be instantiated many times per reasoning run (automaton states, NFA transitions, worker objects).
- **One commit per checklist item** — never batch; commit message format from `git-based-development` skill.
- **Test before committing** — `uv run pytest` must be green before each commit; never commit with known failures introduced by your change.
- **`ruff check` and `mypy`** — run both after each step; the CI will reject anything that breaks them.
