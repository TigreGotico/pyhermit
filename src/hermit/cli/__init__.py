"""Command-line interface for HermiT.

Ports the Java ``org.semanticweb.HermiT.cli.CommandLine`` to Python using
``argparse`` with subcommands.

Because the Python port does not yet include an OWL API parser, the CLI
accepts **pre-compiled DL clause files** (pickled or JSON-serialised
``DLOntology`` objects).  A ``--explain`` flag on any command will print
a message explaining that full OWL parsing is planned but not yet
implemented.
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path
from typing import Any

from hermit.configuration import Configuration
from hermit.entailment_checker import EntailmentChecker
from hermit.model import (
    AtomicConcept,
    DLOntology,
    Individual,
    Prefixes,
)


# ---------------------------------------------------------------------------
# Ontology loading
# ---------------------------------------------------------------------------

def _load_dl_ontology(path: str) -> DLOntology:
    """Load a ``DLOntology`` from a file.

    Supported formats (detected by extension):
    - ``.pkl``, ``.pickle`` -- Python pickle
    - ``.json`` -- JSON with known schema
    - ``.txt``, ``.clauses`` -- plain-text clause dump (future)
    """
    p = Path(path)
    if not p.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    suffix = p.suffix.lower()
    if suffix in (".pkl", ".pickle"):
        with open(p, "rb") as f:
            obj = pickle.load(f)  # noqa: S301
        if not isinstance(obj, DLOntology):
            print("Error: pickle does not contain a DLOntology", file=sys.stderr)
            sys.exit(1)
        return obj

    if suffix == ".json":
        with open(p) as f:
            data = json.load(f)
        return _dl_ontology_from_json(data)

    print(
        f"Error: unsupported file extension '{suffix}'.\n"
        f"Supported: .pkl, .pickle, .json",
        file=sys.stderr,
    )
    sys.exit(1)


def _dl_ontology_from_json(data: dict[str, Any]) -> DLOntology:
    """Deserialize a DLOntology from its JSON representation.

    JSON schema::

        {
          "ontology_iri": "urn:example",
          "dl_clauses": [
            {"head": [<atom>, ...], "body": [<atom>, ...]}
          ],
          "positive_facts": [<atom>, ...],
          "negative_facts": [<atom>, ...]
        }

    Atom::  {"predicate": <predicate>, "args": [<term>, ...]}

    Predicate (one of):
        {"type": "concept", "iri": "..."}
        {"type": "neg_concept", "iri": "..."}
        {"type": "role", "iri": "..."}
        {"type": "inv_role", "iri": "..."}
        {"type": "equality"}
        {"type": "inequality"}

    Term (one of):
        {"type": "var", "name": "X"}
        {"type": "individual", "iri": "..."}
    """
    from hermit.model import (
        Atom,
        AtomicConcept,
        AtomicNegationConcept,
        AtomicRole,
        DLClause,
        Equality,
        Individual,
        Inequality,
        InverseRole,
        Variable,
    )

    def _parse_predicate(p: dict[str, Any]) -> Any:
        t = p["type"]
        if t == "concept":
            return AtomicConcept.create(p["iri"])
        if t == "neg_concept":
            return AtomicNegationConcept.create(AtomicConcept.create(p["iri"]))
        if t == "role":
            return AtomicRole.create(p["iri"])
        if t == "inv_role":
            return InverseRole.create(AtomicRole.create(p["iri"]))
        if t == "equality":
            return Equality.INSTANCE
        if t == "inequality":
            return Inequality.INSTANCE
        raise ValueError(f"Unknown predicate type: {t!r}")

    def _parse_term(t: dict[str, Any]) -> Any:
        kind = t["type"]
        if kind == "var":
            return Variable.create(t["name"])
        if kind == "individual":
            return Individual.create(t["iri"])
        raise ValueError(f"Unknown term type: {kind!r}")

    def _parse_atom(a: dict[str, Any]) -> Atom:
        pred = _parse_predicate(a["predicate"])
        args = tuple(_parse_term(t) for t in a["args"])
        return Atom.create(pred, *args)

    def _parse_clause(c: dict[str, Any]) -> DLClause:
        head = tuple(_parse_atom(a) for a in c.get("head", []))
        body = tuple(_parse_atom(a) for a in c.get("body", []))
        return DLClause.create(head, body)

    ontology_iri = data.get("ontology_iri")
    dl_clauses = frozenset(_parse_clause(c) for c in data.get("dl_clauses", []))
    positive_facts = frozenset(_parse_atom(a) for a in data.get("positive_facts", []))
    negative_facts = frozenset(_parse_atom(a) for a in data.get("negative_facts", []))
    return DLOntology(
        ontology_iri=ontology_iri,
        dl_clauses=dl_clauses,
        positive_facts=positive_facts,
        negative_facts=negative_facts,
    )


def _dl_ontology_to_json(ontology: DLOntology) -> dict[str, Any]:
    """Serialize a DLOntology to its JSON representation.

    See :func:`_dl_ontology_from_json` for the schema.
    """
    from hermit.model import (
        AtomicConcept,
        AtomicNegationConcept,
        AtomicRole,
        Equality,
        Individual,
        Inequality,
        InverseRole,
        Variable,
    )

    def _serial_predicate(p: Any) -> dict[str, Any]:
        if isinstance(p, AtomicNegationConcept):
            return {"type": "neg_concept", "iri": p.negated.iri}
        if isinstance(p, AtomicConcept):
            return {"type": "concept", "iri": p.iri}
        if isinstance(p, InverseRole):
            return {"type": "inv_role", "iri": p.get_inverse().iri}
        if isinstance(p, AtomicRole):
            return {"type": "role", "iri": p.iri}
        if p is Equality.INSTANCE:
            return {"type": "equality"}
        if p is Inequality.INSTANCE:
            return {"type": "inequality"}
        raise ValueError(f"Cannot serialize predicate: {p!r}")

    def _serial_term(t: Any) -> dict[str, Any]:
        if isinstance(t, Variable):
            return {"type": "var", "name": t.name}
        if isinstance(t, Individual):
            return {"type": "individual", "iri": t.iri}
        raise ValueError(f"Cannot serialize term: {t!r}")

    def _serial_atom(a: Any) -> dict[str, Any]:
        return {
            "predicate": _serial_predicate(a.predicate),
            "args": [_serial_term(a.argument(i)) for i in range(a.arity())],
        }

    def _serial_clause(c: Any) -> dict[str, Any]:
        return {
            "head": [_serial_atom(a) for a in c.head_atoms],
            "body": [_serial_atom(a) for a in c.body_atoms],
        }

    return {
        "ontology_iri": ontology.ontology_iri,
        "dl_clauses": [_serial_clause(c) for c in sorted(ontology.dl_clauses, key=str)],
        "positive_facts": [_serial_atom(a) for a in sorted(ontology.positive_facts, key=str)],
        "negative_facts": [_serial_atom(a) for a in sorted(ontology.negative_facts, key=str)],
    }


# ---------------------------------------------------------------------------
# Parsing explanation
# ---------------------------------------------------------------------------

def _explain_parsing() -> None:
    print(
        "NOTE: Full OWL API parsing (OWL/XML, RDF/XML, Manchester, FSS)\n"
        "is not yet implemented in the Python port.\n\n"
        "To use the CLI, provide a pre-compiled DLOntology in pickle (.pkl)\n"
        "or JSON (.json) format.\n\n"
        "Example (Python):\n"
        "    from hermit.model import DLOntology\n"
        "    import pickle\n"
        "    with open('ontology.pkl', 'wb') as f:\n"
        "        pickle.dump(my_dl_ontology, f)\n\n"
        "    hermit classify ontology.pkl",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------

def _cmd_stats(args: argparse.Namespace) -> None:
    dl = _load_dl_ontology(args.ontology)
    from hermit.reasoner import Reasoner

    config = _build_config(args)
    reasoner = Reasoner(dl, config)
    stats = reasoner.stats
    for key, value in stats.items():
        print(f"{key}: {value}")
    reasoner.dispose()


def _cmd_consistent(args: argparse.Namespace) -> None:
    dl = _load_dl_ontology(args.ontology)
    from hermit.reasoner import Reasoner

    config = _build_config(args)
    reasoner = Reasoner(dl, config)
    consistent = reasoner.is_consistent()
    print("CONSISTENT" if consistent else "INCONSISTENT")
    if args.verbose:
        print(f"Ontology: {dl.ontology_iri or '(anonymous)'}")
        print(f"Clauses: {len(dl.dl_clauses)}")
        print(f"Concepts: {len(dl.all_atomic_concepts)}")
        print(f"Individuals: {len(dl.all_individuals)}")
    reasoner.dispose()


def _cmd_classify(args: argparse.Namespace) -> None:
    dl = _load_dl_ontology(args.ontology)
    from hermit.reasoner import Reasoner

    config = _build_config(args)
    reasoner = Reasoner(dl, config)

    if args.explain:
        _explain_parsing()

    out = sys.stdout
    if args.output:
        out = open(args.output, "w")

    reasoner.precompute_inferences(
        class_hierarchy=args.classes or not args.object_properties and not args.data_properties,
        object_property_hierarchy=args.object_properties,
        data_property_hierarchy=args.data_properties,
    )

    if args.pretty:
        reasoner.print_hierarchies(
            out,
            classes=args.classes or not args.object_properties and not args.data_properties,
            object_properties=args.object_properties,
            data_properties=args.data_properties,
        )
    else:
        reasoner.dump_hierarchies(
            out,
            classes=args.classes or not args.object_properties and not args.data_properties,
            object_properties=args.object_properties,
            data_properties=args.data_properties,
        )

    if args.output:
        out.close()
    reasoner.dispose()


def _cmd_realize(args: argparse.Namespace) -> None:
    dl = _load_dl_ontology(args.ontology)
    from hermit.reasoner import Reasoner

    config = _build_config(args)
    reasoner = Reasoner(dl, config)

    if args.explain:
        _explain_parsing()

    reasoner.precompute_inferences(class_hierarchy=True)
    instances = reasoner.get_instances(AtomicConcept.THING, direct=args.direct)
    for ind in sorted(instances, key=lambda i: i.iri):
        types = reasoner.get_types(ind, direct=args.direct)
        type_strs = [str(t) for t in types]
        print(f"{ind}: {', '.join(type_strs)}")
    reasoner.dispose()


def _cmd_entails(args: argparse.Namespace) -> None:
    dl = _load_dl_ontology(args.ontology)
    from hermit.reasoner import Reasoner

    config = _build_config(args)
    reasoner = Reasoner(dl, config)

    if args.explain:
        _explain_parsing()

    checker = EntailmentChecker(reasoner)

    # Parse entailment specifications from the command line.
    # Format: --sub=A,B for subsumption, --equiv=A,B for equivalence,
    # --disjoint=A,B, --type=I:C, --role=I:R:J
    result = True
    for spec in args.sub or []:
        parts = spec.split(",")
        if len(parts) != 2:
            print(f"Error: --sub expects A,B got: {spec}", file=sys.stderr)
            result = False
            continue
        sub = _parse_concept(parts[0], reasoner.prefixes)
        sup = _parse_concept(parts[1], reasoner.prefixes)
        if not checker.entails_sub_class_of(sub, sup):
            print(f"NOT entailed: {sub} <= {sup}")
            result = False
        elif args.verbose:
            print(f"Entailed: {sub} <= {sup}")

    for spec in args.equiv or []:
        parts = spec.split(",")
        if len(parts) != 2:
            print(f"Error: --equiv expects A,B got: {spec}", file=sys.stderr)
            result = False
            continue
        c1 = _parse_concept(parts[0], reasoner.prefixes)
        c2 = _parse_concept(parts[1], reasoner.prefixes)
        if not checker.entails_equivalent(c1, c2):
            print(f"NOT entailed: {c1} == {c2}")
            result = False
        elif args.verbose:
            print(f"Entailed: {c1} == {c2}")

    for spec in args.disjoint or []:
        parts = spec.split(",")
        if len(parts) != 2:
            print(f"Error: --disjoint expects A,B got: {spec}", file=sys.stderr)
            result = False
            continue
        c1 = _parse_concept(parts[0], reasoner.prefixes)
        c2 = _parse_concept(parts[1], reasoner.prefixes)
        if not checker.entails_disjoint(c1, c2):
            print(f"NOT entailed: {c1} disjoint {c2}")
            result = False
        elif args.verbose:
            print(f"Entailed: {c1} disjoint {c2}")

    for spec in args.type_assert or []:
        parts = spec.split(":")
        if len(parts) != 2:
            print(f"Error: --type expects I:C got: {spec}", file=sys.stderr)
            result = False
            continue
        ind = _parse_individual(parts[0], reasoner.prefixes)
        concept = _parse_concept(parts[1], reasoner.prefixes)
        if not checker.entails_type(ind, concept):
            print(f"NOT entailed: {concept}({ind})")
            result = False
        elif args.verbose:
            print(f"Entailed: {concept}({ind})")

    reasoner.dispose()
    sys.exit(0 if result else 1)


def _cmd_query(args: argparse.Namespace) -> None:
    dl = _load_dl_ontology(args.ontology)
    from hermit.reasoner import Reasoner

    config = _build_config(args)
    reasoner = Reasoner(dl, config)

    if args.explain:
        _explain_parsing()

    concept_str = args.concept
    prefixes = reasoner.prefixes
    concept_iri = _resolve_name(concept_str, prefixes)
    concept = AtomicConcept.create(concept_iri)

    if args.satisfiable:
        sat = reasoner.is_satisfiable(concept)
        print(f"{concept_str} is {'satisfiable' if sat else 'unsatisfiable'}")

    if args.subs:
        reasoner.classify_classes()
        reasoner.precompute_inferences(class_hierarchy=True)
        # Find all sub-classes
        all_concepts = {
            c for c in dl.all_atomic_concepts
            if not Prefixes.is_internal_iri(c.iri)
        }
        subs = {
            c for c in all_concepts
            if c is not concept and reasoner.is_sub_class_of(c, concept)
        }
        if args.direct:
            # Filter to only direct subs
            direct_subs = set()
            for sub in subs:
                is_direct = True
                for other in subs:
                    if other is not sub and reasoner.is_sub_class_of(sub, other):
                        is_direct = False
                        break
                if is_direct:
                    direct_subs.add(sub)
            subs = direct_subs
        print(f"Sub-classes of {concept_str}:")
        for c in sorted(subs, key=lambda x: x.iri):
            print(f"  {prefixes.abbreviate_iri(c.iri)}")

    if args.supers:
        reasoner.classify_classes()
        reasoner.precompute_inferences(class_hierarchy=True)
        all_concepts = {
            c for c in dl.all_atomic_concepts
            if not Prefixes.is_internal_iri(c.iri)
        }
        supers = {
            c for c in all_concepts
            if c is not concept and reasoner.is_sub_class_of(concept, c)
        }
        if args.direct:
            direct_supers = set()
            for sup in supers:
                is_direct = True
                for other in supers:
                    if other is not sup and reasoner.is_sub_class_of(other, sup):
                        is_direct = False
                        break
                if is_direct:
                    direct_supers.add(sup)
            supers = direct_supers
        print(f"Super-classes of {concept_str}:")
        for c in sorted(supers, key=lambda x: x.iri):
            print(f"  {prefixes.abbreviate_iri(c.iri)}")

    if args.instances:
        direct = args.direct
        instances = reasoner.get_instances(concept, direct=direct)
        label = "Direct" if direct else "All"
        print(f"{label} instances of {concept_str}:")
        for ind in sorted(instances, key=lambda i: i.iri):
            print(f"  {ind}")

    reasoner.dispose()


def _cmd_dump_clauses(args: argparse.Namespace) -> None:
    dl = _load_dl_ontology(args.ontology)
    from hermit.reasoner import Reasoner

    config = _build_config(args)
    reasoner = Reasoner(dl, config)

    out_file: Any
    if args.output:
        out_file = open(args.output, "w")
    else:
        out_file = sys.stdout

    # Print clauses in a readable form
    print(f"# Ontology: {dl.ontology_iri or '(anonymous)'}", file=out_file)
    print(f"# Clauses: {len(dl.dl_clauses)}", file=out_file)
    print(f"# Positive facts: {len(dl.positive_facts)}", file=out_file)
    print(f"# Negative facts: {len(dl.negative_facts)}", file=out_file)
    print(file=out_file)

    for clause in sorted(dl.dl_clauses, key=str):
        print(str(clause), file=out_file)

    if dl.positive_facts:
        print("\n# Positive facts:", file=out_file)
        for fact in sorted(dl.positive_facts, key=str):
            print(f"  {fact}", file=out_file)

    if dl.negative_facts:
        print("\n# Negative facts:", file=out_file)
        for fact in sorted(dl.negative_facts, key=str):
            print(f"  {fact}", file=out_file)

    if args.output:
        out_file.close()
    reasoner.dispose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_config(args: argparse.Namespace) -> Configuration:
    config = Configuration()
    if args.ignore_unsupported_datatypes:
        config.ignore_unsupported_datatypes = True
    if args.no_inconsistent_exception:
        config.throw_inconsistent_ontology_exception = False
    if args.quiet:
        config.tableau_monitor_type = config.tableau_monitor_type.NONE
    if args.verbose:
        from hermit.configuration import TableauMonitorType
        config.tableau_monitor_type = TableauMonitorType.TIMING
    return config


def _resolve_name(name: str, prefixes: Prefixes) -> str:
    """Resolve a possibly-prefixed name to a full IRI."""
    if name.startswith("<") and name.endswith(">"):
        return name[1:-1]
    if prefixes.can_be_expanded(name) if hasattr(prefixes, "can_be_expanded") else False:
        return prefixes.expand_abbreviation(name)
    # Try to expand as prefix:local
    if ":" in name:
        prefix_part = name.split(":")[0] + ":"
        iri = prefixes.get_prefix_iri(prefix_part)
        if iri:
            local = name[len(prefix_part):]
            return iri + local
    return name


def _parse_concept(name: str, prefixes: Prefixes) -> AtomicConcept:
    iri = _resolve_name(name, prefixes)
    return AtomicConcept.create(iri)


def _parse_individual(name: str, prefixes: Prefixes) -> Individual:
    iri = _resolve_name(name, prefixes)
    return Individual.create(iri)


# ---------------------------------------------------------------------------
# Argument parser construction
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hermit",
        description="HermiT -- A conformant OWL 2 DL tableau reasoner (Python port)",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version="HermiT 0.1.0 (Python port)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress output",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--ignore-unsupported-datatypes",
        action="store_true",
        help="Ignore axioms with unsupported datatypes",
    )
    parser.add_argument(
        "--no-inconsistent-exception",
        action="store_true",
        help="Do not throw on inconsistent ontology",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- stats ---
    p_stats = subparsers.add_parser("stats", help="Show ontology statistics")
    p_stats.add_argument("ontology", help="Path to pre-compiled DLOntology file (.pkl, .json)")

    # --- consistent ---
    p_cons = subparsers.add_parser("consistent", help="Check ontology consistency")
    p_cons.add_argument("ontology", help="Path to pre-compiled DLOntology file")

    # --- classify ---
    p_class = subparsers.add_parser("classify", help="Classify concept hierarchy")
    p_class.add_argument("ontology", help="Path to pre-compiled DLOntology file")
    p_class.add_argument("-o", "--output", help="Write output to FILE instead of stdout")
    p_class.add_argument(
        "-P", "--pretty", action="store_true",
        help="Pretty-print as Functional-Style Syntax ontology",
    )
    p_class.add_argument(
        "-C", "--classes", action="store_true",
        help="Classify concept hierarchy (default when no other flag given)",
    )
    p_class.add_argument(
        "-O", "--object-properties", action="store_true",
        help="Also classify object properties",
    )
    p_class.add_argument(
        "-D", "--data-properties", action="store_true",
        help="Also classify data properties",
    )
    p_class.add_argument("--explain", action="store_true", help="Explain parsing limitations")

    # --- realize ---
    p_real = subparsers.add_parser("realize", help="Realize individual types")
    p_real.add_argument("ontology", help="Path to pre-compiled DLOntology file")
    p_real.add_argument(
        "--direct", action="store_true",
        help="Only show direct types",
    )
    p_real.add_argument("--explain", action="store_true", help="Explain parsing limitations")

    # --- entails ---
    p_ent = subparsers.add_parser("entails", help="Check entailments")
    p_ent.add_argument("ontology", help="Path to pre-compiled DLOntology file")
    p_ent.add_argument(
        "--sub", action="append", metavar="A,B",
        help="Check subsumption A <= B",
    )
    p_ent.add_argument(
        "--equiv", action="append", metavar="A,B",
        help="Check equivalence A == B",
    )
    p_ent.add_argument(
        "--disjoint", action="append", metavar="A,B",
        help="Check disjointness A disjoint B",
    )
    p_ent.add_argument(
        "--type", dest="type_assert", action="append", metavar="I:C",
        help="Check type assertion C(I)",
    )
    p_ent.add_argument("--explain", action="store_true", help="Explain parsing limitations")

    # --- query ---
    p_query = subparsers.add_parser("query", help="Query concepts")
    p_query.add_argument("ontology", help="Path to pre-compiled DLOntology file")
    p_query.add_argument("concept", help="Concept name (full IRI or prefix:local)")
    p_query.add_argument(
        "--satisfiable", action="store_true",
        help="Check satisfiability",
    )
    p_query.add_argument(
        "--subs", action="store_true",
        help="Find sub-classes",
    )
    p_query.add_argument(
        "--supers", action="store_true",
        help="Find super-classes",
    )
    p_query.add_argument(
        "--instances", action="store_true",
        help="Find instances",
    )
    p_query.add_argument(
        "--direct", action="store_true",
        help="Only direct subs/supers/instances",
    )
    p_query.add_argument("--explain", action="store_true", help="Explain parsing limitations")

    # --- dump-clauses ---
    p_dump = subparsers.add_parser("dump-clauses", help="Dump DL clauses")
    p_dump.add_argument("ontology", help="Path to pre-compiled DLOntology file")
    p_dump.add_argument("-o", "--output", help="Write to FILE instead of stdout")
    p_dump.add_argument(
        "--ignore-prefixes", action="store_true",
        help="Do not use ontology prefixes in output",
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    command_map: dict[str, Any] = {
        "stats": _cmd_stats,
        "consistent": _cmd_consistent,
        "classify": _cmd_classify,
        "realize": _cmd_realize,
        "entails": _cmd_entails,
        "query": _cmd_query,
        "dump-clauses": _cmd_dump_clauses,
    }

    handler = command_map.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    try:
        handler(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if getattr(args, "verbose", False):
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
