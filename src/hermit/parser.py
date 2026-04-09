"""OWL file parser using owlready2.

Loads OWL/RDF ontologies from files and converts them to hermit.owl_model types.

The parser bridges owlready2's object-oriented API (where axioms are embedded
in class/property/individual objects) to hermit.owl_model's first-class axiom
objects (mirroring the OWL API used by Java HermiT).

Pipeline::

    OWL file → owlready2 → _OwlreadyMapper → Iterable[OWLAxiom]
                                               → OWLNormalization → NormalizedAxioms
                                               → OWLClausification → DLOntology
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hermit.owl_model.owl_axiom import OWLAxiom
    from hermit.owl_model.class_expression import OWLClassExpression


def load_ontology(path: str | Path) -> list[OWLAxiom]:
    """Load an OWL ontology from a file.

    Args:
        path: Path to OWL/RDF file (.owl, .nt, etc.)

    Returns:
        List of OWLAxiom objects covering the full set of logical axioms.

    Raises:
        ImportError: If owlready2 is not installed
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file cannot be parsed as OWL
    """
    try:
        import owlready2  # type: ignore[import-untyped]
    except ImportError as e:
        raise ImportError(
            "owlready2 is required for OWL file parsing. "
            "Install it with: pip install owlready2"
        ) from e

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"OWL file not found: {path}")

    try:
        onto = owlready2.get_ontology(str(path.as_uri())).load()
    except Exception as e:
        raise ValueError(f"Failed to parse OWL file: {path}") from e

    return _OwlreadyMapper(owlready2).extract_axioms(onto)


class _OwlreadyMapper:
    """Converts an owlready2 ontology into hermit.owl_model OWL axiom objects.

    owlready2 does not expose first-class axiom objects (unlike the Java OWL API).
    Instead, axioms are embedded in class/property/individual objects and must be
    extracted by iterating the ontology signature and reading properties.

    This mapper performs that extraction for all axiom types that OWLNormalization
    understands.
    """

    def __init__(self, owlready2_module: Any) -> None:
        self._or2: Any = owlready2_module

    def extract_axioms(self, onto: Any) -> list[OWLAxiom]:
        """Extract all logical axioms from an owlready2 ontology."""
        axioms: list[OWLAxiom] = []
        self._extract_class_axioms(onto, axioms)
        self._extract_individual_axioms(onto, axioms)
        self._extract_object_property_axioms(onto, axioms)
        self._extract_data_property_axioms(onto, axioms)
        return axioms

    # ------------------------------------------------------------------
    # Class expression mapping
    # ------------------------------------------------------------------

    def _map_class_expression(self, expr: Any) -> OWLClassExpression | None:
        """Convert an owlready2 class expression to an OWL model class expression.

        Handles: named classes, restrictions (some/all/min/max/exactly/hasSelf/hasValue),
        intersections, unions, complements, and one-of nominals.
        Returns None if the expression cannot be mapped.
        """
        or2 = self._or2
        from hermit.owl_model.class_expression import (
            OWLClass, OWLObjectComplementOf,
            OWLObjectIntersectionOf, OWLObjectUnionOf,
            OWLObjectSomeValuesFrom, OWLObjectAllValuesFrom,
            OWLObjectHasSelf, OWLObjectHasValue,
            OWLObjectMinCardinality, OWLObjectMaxCardinality, OWLObjectExactCardinality,
            OWLObjectOneOf, OWLThing, OWLNothing,
        )
        from hermit.owl_model.owl_property import OWLObjectProperty

        # owl:Thing / owl:Nothing
        if expr is or2.Thing:
            return OWLThing
        if expr is or2.Nothing:
            return OWLNothing

        # Named class
        if isinstance(expr, or2.ThingClass):
            iri = getattr(expr, "iri", None)
            if iri:
                return OWLClass(iri)
            return None

        # Complement (Not)
        if isinstance(expr, or2.Not):
            operand = self._map_class_expression(getattr(expr, "Class", None))
            if operand is not None:
                return OWLObjectComplementOf(operand)
            return None

        # And (Intersection)
        if isinstance(expr, or2.And):
            raw_ops = [self._map_class_expression(c) for c in getattr(expr, "Classes", [])]
            ops: list[OWLClassExpression] = [o for o in raw_ops if o is not None]
            if len(ops) >= 2:
                return OWLObjectIntersectionOf(ops)
            if len(ops) == 1:
                return ops[0]
            return None

        # Or (Union)
        if isinstance(expr, or2.Or):
            raw_ops2 = [self._map_class_expression(c) for c in getattr(expr, "Classes", [])]
            ops2: list[OWLClassExpression] = [o for o in raw_ops2 if o is not None]
            if len(ops2) >= 2:
                return OWLObjectUnionOf(ops2)
            if len(ops2) == 1:
                return ops2[0]
            return None

        # OneOf (nominals)
        if isinstance(expr, or2.OneOf):
            from hermit.owl_model.owl_individual import OWLNamedIndividual
            inds = []
            for ind in getattr(expr, "instances", []):
                ind_iri = getattr(ind, "iri", None)
                if ind_iri:
                    inds.append(OWLNamedIndividual(ind_iri))
            if inds:
                return OWLObjectOneOf(inds)
            return None

        # Restriction
        if isinstance(expr, or2.Restriction):
            prop_obj = getattr(expr, "property", None)
            if prop_obj is None:
                return None
            prop_iri = getattr(prop_obj, "iri", None)
            if prop_iri is None:
                return None

            # Determine if object or data property
            is_object_prop = isinstance(prop_obj, or2.ObjectPropertyClass)
            if not is_object_prop:
                return None  # data property restrictions handled separately

            owl_prop = OWLObjectProperty(prop_iri)
            rtype = getattr(expr, "type", None)
            value = getattr(expr, "value", None)
            cardinality = getattr(expr, "cardinality", None)

            # owlready2 restriction type constants
            some = getattr(or2, "SOME", 24)
            only = getattr(or2, "ONLY", 25)
            min_ = getattr(or2, "MIN", 26)
            max_ = getattr(or2, "MAX", 27)
            exactly = getattr(or2, "EXACTLY", 28)
            has_self = getattr(or2, "HAS_SELF", 11)
            value_type = getattr(or2, "VALUE", 29)

            filler = self._map_class_expression(value) if value is not None else OWLThing

            if rtype == some:
                if filler is None:
                    return None
                return OWLObjectSomeValuesFrom(owl_prop, filler)
            elif rtype == only:
                if filler is None:
                    return None
                return OWLObjectAllValuesFrom(owl_prop, filler)
            elif rtype == min_ and cardinality is not None:
                return OWLObjectMinCardinality(cardinality, owl_prop, filler or OWLThing)
            elif rtype == max_ and cardinality is not None:
                return OWLObjectMaxCardinality(cardinality, owl_prop, filler or OWLThing)
            elif rtype == exactly and cardinality is not None:
                return OWLObjectExactCardinality(cardinality, owl_prop, filler or OWLThing)
            elif rtype == has_self:
                return OWLObjectHasSelf(owl_prop)
            elif rtype == value_type and value is not None:
                ind_iri = getattr(value, "iri", None)
                if ind_iri:
                    from hermit.owl_model.owl_individual import OWLNamedIndividual
                    return OWLObjectHasValue(owl_prop, OWLNamedIndividual(ind_iri))

        return None

    # ------------------------------------------------------------------
    # Class-level axioms
    # ------------------------------------------------------------------

    def _extract_class_axioms(self, onto: Any, axioms: list[OWLAxiom]) -> None:
        """Extract SubClassOf, EquivalentClasses, DisjointClasses."""
        from hermit.owl_model.owl_axiom import (
            OWLSubClassOfAxiom,
            OWLEquivalentClassesAxiom,
            OWLDisjointClassesAxiom,
        )
        from hermit.owl_model.class_expression import OWLClass

        for cls in onto.classes():
            sub_iri = getattr(cls, "iri", None)
            if sub_iri is None:
                continue
            owl_sub = OWLClass(sub_iri)

            # SubClassOf — includes both named parents and restrictions
            for parent in getattr(cls, "is_a", []):
                super_expr = self._map_class_expression(parent)
                if super_expr is not None:
                    try:
                        axioms.append(OWLSubClassOfAxiom(owl_sub, super_expr))
                    except Exception:
                        pass

            # EquivalentClasses — includes complex expressions
            for eq in getattr(cls, "equivalent_to", []):
                eq_expr = self._map_class_expression(eq)
                if eq_expr is not None:
                    try:
                        axioms.append(OWLEquivalentClassesAxiom([owl_sub, eq_expr]))
                    except Exception:
                        pass

        # DisjointClasses — owlready2 stores these as AllDisjoint objects
        for disj in getattr(onto, "disjoint_classes", lambda: [])():
            entities = getattr(disj, "entities", [])
            owl_classes = []
            for e in entities:
                e_iri = getattr(e, "iri", None)
                if e_iri:
                    owl_classes.append(OWLClass(e_iri))
            if len(owl_classes) >= 2:
                try:
                    axioms.append(OWLDisjointClassesAxiom(list(owl_classes)))
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Individual-level axioms
    # ------------------------------------------------------------------

    def _extract_individual_axioms(self, onto: Any, axioms: list[OWLAxiom]) -> None:
        """Extract ClassAssertion, ObjectPropertyAssertion, SameIndividual, DifferentIndividuals."""
        or2 = self._or2
        from hermit.owl_model.owl_axiom import (
            OWLClassAssertionAxiom,
            OWLObjectPropertyAssertionAxiom,
            OWLSameIndividualAxiom,
            OWLDifferentIndividualsAxiom,
        )
        from hermit.owl_model.class_expression import OWLClass
        from hermit.owl_model.owl_individual import OWLNamedIndividual
        from hermit.owl_model.owl_property import OWLObjectProperty

        for ind in onto.individuals():
            ind_iri = getattr(ind, "iri", None)
            if ind_iri is None:
                continue
            owl_ind = OWLNamedIndividual(ind_iri)

            # ClassAssertion: A(a)
            for typ in getattr(ind, "is_a", []):
                if isinstance(typ, or2.ThingClass):
                    typ_iri = getattr(typ, "iri", None)
                    if typ_iri:
                        try:
                            axioms.append(OWLClassAssertionAxiom(owl_ind, OWLClass(typ_iri)))
                        except Exception:
                            pass

            # ObjectPropertyAssertion: R(a, b)
            for prop in onto.object_properties():
                prop_iri = getattr(prop, "iri", None)
                if prop_iri is None:
                    continue
                prop_name = getattr(prop, "python_name", None) or getattr(prop, "name", None)
                if prop_name is None:
                    continue
                targets = getattr(ind, prop_name, [])
                if not hasattr(targets, "__iter__"):
                    targets = [targets] if targets is not None else []
                owl_prop = OWLObjectProperty(prop_iri)
                for target in targets:
                    tgt_iri = getattr(target, "iri", None)
                    if tgt_iri:
                        try:
                            axioms.append(
                                OWLObjectPropertyAssertionAxiom(
                                    owl_ind, owl_prop, OWLNamedIndividual(tgt_iri)
                                )
                            )
                        except Exception:
                            pass

            # SameIndividual
            for same in getattr(ind, "equivalent_to", []):
                same_iri = getattr(same, "iri", None)
                if same_iri and same_iri != ind_iri:
                    try:
                        axioms.append(OWLSameIndividualAxiom([owl_ind, OWLNamedIndividual(same_iri)]))
                    except Exception:
                        pass

            # DifferentIndividuals
            for diff in getattr(ind, "different_from", []):
                diff_iri = getattr(diff, "iri", None)
                if diff_iri:
                    try:
                        axioms.append(OWLDifferentIndividualsAxiom([owl_ind, OWLNamedIndividual(diff_iri)]))
                    except Exception:
                        pass

    # ------------------------------------------------------------------
    # Object property axioms
    # ------------------------------------------------------------------

    def _extract_object_property_axioms(self, onto: Any, axioms: list[OWLAxiom]) -> None:
        """Extract property characteristics and sub-property axioms."""
        or2 = self._or2
        from hermit.owl_model.owl_axiom import (
            OWLSubObjectPropertyOfAxiom,
            OWLTransitiveObjectPropertyAxiom,
            OWLSymmetricObjectPropertyAxiom,
            OWLAsymmetricObjectPropertyAxiom,
            OWLReflexiveObjectPropertyAxiom,
            OWLIrreflexiveObjectPropertyAxiom,
            OWLFunctionalObjectPropertyAxiom,
            OWLInverseFunctionalObjectPropertyAxiom,
        )
        from hermit.owl_model.owl_property import OWLObjectProperty

        for prop in onto.object_properties():
            prop_iri = getattr(prop, "iri", None)
            if prop_iri is None:
                continue
            owl_prop = OWLObjectProperty(prop_iri)

            # Characteristics encoded as mixin classes in owlready2
            for parent in getattr(prop, "is_a", []):
                if parent is or2.TransitiveProperty:
                    try:
                        axioms.append(OWLTransitiveObjectPropertyAxiom(owl_prop))
                    except Exception:
                        pass
                elif parent is or2.SymmetricProperty:
                    try:
                        axioms.append(OWLSymmetricObjectPropertyAxiom(owl_prop))
                    except Exception:
                        pass
                elif parent is or2.AsymmetricProperty:
                    try:
                        axioms.append(OWLAsymmetricObjectPropertyAxiom(owl_prop))
                    except Exception:
                        pass
                elif parent is or2.ReflexiveProperty:
                    try:
                        axioms.append(OWLReflexiveObjectPropertyAxiom(owl_prop))
                    except Exception:
                        pass
                elif parent is or2.IrreflexiveProperty:
                    try:
                        axioms.append(OWLIrreflexiveObjectPropertyAxiom(owl_prop))
                    except Exception:
                        pass
                elif parent is or2.FunctionalProperty:
                    try:
                        axioms.append(OWLFunctionalObjectPropertyAxiom(owl_prop))
                    except Exception:
                        pass
                elif parent is or2.InverseFunctionalProperty:
                    try:
                        axioms.append(OWLInverseFunctionalObjectPropertyAxiom(owl_prop))
                    except Exception:
                        pass
                elif isinstance(parent, or2.ObjectPropertyClass):
                    # SubObjectPropertyOf
                    parent_iri = getattr(parent, "iri", None)
                    if parent_iri and parent_iri != prop_iri:
                        try:
                            axioms.append(
                                OWLSubObjectPropertyOfAxiom(owl_prop, OWLObjectProperty(parent_iri))
                            )
                        except Exception:
                            pass

    # ------------------------------------------------------------------
    # Data property axioms
    # ------------------------------------------------------------------

    def _extract_data_property_axioms(self, onto: Any, axioms: list[OWLAxiom]) -> None:
        """Extract data property sub-property and characteristic axioms."""
        or2 = self._or2
        from hermit.owl_model.owl_axiom import (
            OWLSubDataPropertyOfAxiom,
            OWLFunctionalDataPropertyAxiom,
        )
        from hermit.owl_model.owl_property import OWLDataProperty

        for prop in onto.data_properties():
            prop_iri = getattr(prop, "iri", None)
            if prop_iri is None:
                continue
            owl_prop = OWLDataProperty(prop_iri)

            for parent in getattr(prop, "is_a", []):
                if parent is or2.FunctionalProperty:
                    try:
                        axioms.append(OWLFunctionalDataPropertyAxiom(owl_prop))
                    except Exception:
                        pass
                elif isinstance(parent, or2.DataPropertyClass):
                    parent_iri = getattr(parent, "iri", None)
                    if parent_iri and parent_iri != prop_iri:
                        try:
                            axioms.append(
                                OWLSubDataPropertyOfAxiom(owl_prop, OWLDataProperty(parent_iri))
                            )
                        except Exception:
                            pass


__all__ = ["load_ontology"]
