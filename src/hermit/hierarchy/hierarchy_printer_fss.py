"""Hierarchy printer in Functional-Style Syntax with prefix management.

Faithful port of ``org.semanticweb.HermiT.hierarchy.HierarchyPrinterFSS``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TextIO, TypeVar, cast

from hermit.hierarchy.hierarchy import Hierarchy, HierarchyNodeVisitor, Transformer
from hermit.hierarchy.hierarchy_node import HierarchyNode
from hermit.model import AtomicConcept, AtomicRole, InverseRole, Prefixes, Role

if TYPE_CHECKING:
    from collections.abc import Collection


class HierarchyPrinterFSS:
    """Prints hierarchies in OWL Functional-Style Syntax with IRI prefixes."""

    def __init__(self, out: TextIO, default_prefix_iri: str) -> None:
        self.m_out = out
        self.m_default_prefix_iri = default_prefix_iri
        self.m_prefix_iris: set[str] = {
            default_prefix_iri,
            Prefixes.SEMANTIC_WEB_PREFIXES["owl:"],
        }
        self.m_prefixes: Prefixes | None = None

    def load_atomic_concept_prefix_iris(
        self, atomic_concepts: Collection[AtomicConcept]
    ) -> None:
        for atomic_concept in atomic_concepts:
            uri = atomic_concept.iri
            hash_index = uri.find("#")
            if hash_index != -1:
                prefix_iri = uri[: hash_index + 1]
                local_name = uri[hash_index + 1 :]
                if self._is_valid_local_name(local_name):
                    self.m_prefix_iris.add(prefix_iri)

    def load_atomic_role_prefix_iris(
        self, atomic_roles: Collection[AtomicRole]
    ) -> None:
        for atomic_role in atomic_roles:
            uri = atomic_role.iri
            hash_index = uri.find("#")
            if hash_index != -1:
                prefix_iri = uri[: hash_index + 1]
                local_name = uri[hash_index + 1 :]
                if self._is_valid_local_name(local_name):
                    self.m_prefix_iris.add(prefix_iri)

    def start_printing(self) -> None:
        owl_prefix_iri = Prefixes.SEMANTIC_WEB_PREFIXES["owl:"]
        self.m_prefixes = Prefixes()
        self.m_prefixes.declare_default_prefix(self.m_default_prefix_iri)
        self.m_prefixes.declare_prefix("owl:", owl_prefix_iri)
        index = 1
        for prefix_iri in sorted(self.m_prefix_iris):
            if (
                prefix_iri != self.m_default_prefix_iri
                and prefix_iri != owl_prefix_iri
            ):
                prefix_name = f"a{index}:"
                self.m_prefixes.declare_prefix(prefix_name, prefix_iri)
                index += 1
        for prefix_name, prefix_iri in self.m_prefixes.prefix_map.items():
            if prefix_name != "owl:":
                self.m_out.write(f"Prefix({prefix_name}=<{prefix_iri}>)\n")
        self.m_out.write("\n")
        default_iri = self.m_prefixes.prefix_map.get(
            ":", self.m_default_prefix_iri
        )
        self.m_out.write(f"Ontology(<{default_iri}>\n")
        self.m_out.write("\n")

    def print_atomic_concept_hierarchy(
        self, atomic_concept_hierarchy: Hierarchy[AtomicConcept]
    ) -> None:
        sorted_hierarchy = atomic_concept_hierarchy.transform(
            _IdentityTransformer[AtomicConcept](), _AtomicConceptComparator()
        )
        printer = _AtomicConceptPrinter(
            self, sorted_hierarchy.get_bottom_node()
        )
        sorted_hierarchy.traverse_depth_first(printer)
        printer.print_node(
            0, sorted_hierarchy.get_bottom_node(), None, True
        )

    def print_role_hierarchy(
        self,
        role_hierarchy: Hierarchy[Role],
        object_properties: bool,
    ) -> None:
        sorted_role_hierarchy = role_hierarchy.transform(
            _IdentityTransformer[Role](), _RoleComparator()
        )
        printer = _RolePrinter(self, sorted_role_hierarchy, object_properties)
        sorted_role_hierarchy.traverse_depth_first(printer)
        printer.print_node(
            0, sorted_role_hierarchy.get_bottom_node(), None, True
        )

    def end_printing(self) -> None:
        self.m_out.write("\n)\n")
        self.m_out.flush()

    # -- internal helpers --------------------------------------------------

    @staticmethod
    def _is_valid_local_name(local_name: str) -> bool:
        return Prefixes._is_valid_local_name(local_name)

    def _abbreviate(self, iri: str) -> str:
        if self.m_prefixes is not None:
            return self.m_prefixes.abbreviate_iri(iri)
        return f"<{iri}>"


class _AtomicConceptPrinter(HierarchyNodeVisitor[AtomicConcept]):
    def __init__(
        self, printer: HierarchyPrinterFSS, bottom_node: HierarchyNode[AtomicConcept]
    ) -> None:
        self._printer = printer
        self.m_bottom_node = bottom_node

    def redirect(self, nodes: list[HierarchyNode[AtomicConcept]]) -> bool:
        return True

    def visit(
        self,
        level: int,
        node: HierarchyNode[AtomicConcept],
        parent_node: HierarchyNode[AtomicConcept] | None,
        first_visit: bool,
    ) -> None:
        if node != self.m_bottom_node:
            self.print_node(level, node, parent_node, first_visit)

    def print_node(
        self,
        level: int,
        node: HierarchyNode[AtomicConcept],
        parent_node: HierarchyNode[AtomicConcept] | None,
        first_visit: bool,
    ) -> None:
        equivalences = node.get_equivalent_elements()
        print_sub_class_of = parent_node is not None
        print_equivalences = first_visit and len(equivalences) > 1
        print_declarations = False
        if first_visit:
            for ac in equivalences:
                if self._needs_declaration(ac):
                    print_declarations = True
                    break
        if print_sub_class_of or print_equivalences or print_declarations:
            out = self._printer.m_out
            out.write("  " * level)
            after_ws = True
            if print_sub_class_of:
                out.write("SubClassOf( ")
                self._print_ac(node.m_representative)
                out.write(" ")
                self._print_ac(parent_node.m_representative)  # type: ignore[union-attr]
                out.write(" )")
                after_ws = False
            if print_equivalences:
                if not after_ws:
                    out.write(" ")
                out.write("EquivalentClasses(")
                for ac in equivalences:
                    out.write(" ")
                    self._print_ac(ac)
                out.write(" )")
                after_ws = False
            if print_declarations:
                for ac in equivalences:
                    if self._needs_declaration(ac):
                        if not after_ws:
                            out.write(" ")
                        out.write("Declaration( Class( ")
                        self._print_ac(ac)
                        out.write(" ) )")
                        after_ws = False
            out.write("\n")

    def _print_ac(self, atomic_concept: AtomicConcept) -> None:
        self._printer.m_out.write(self._printer._abbreviate(atomic_concept.iri))

    @staticmethod
    def _needs_declaration(atomic_concept: AtomicConcept) -> bool:
        return (
            atomic_concept != AtomicConcept.NOTHING
            and atomic_concept != AtomicConcept.THING
        )


class _RolePrinter(HierarchyNodeVisitor[Role]):
    def __init__(
        self,
        printer: HierarchyPrinterFSS,
        hierarchy: Hierarchy[Role],
        object_properties: bool,
    ) -> None:
        self._printer = printer
        self.m_hierarchy = hierarchy
        self.m_object_properties = object_properties

    def redirect(self, nodes: list[HierarchyNode[Role]]) -> bool:
        return True

    def visit(
        self,
        level: int,
        node: HierarchyNode[Role],
        parent_node: HierarchyNode[Role] | None,
        first_visit: bool,
    ) -> None:
        if node != self.m_hierarchy.get_bottom_node():
            self.print_node(level, node, parent_node, first_visit)

    def print_node(
        self,
        level: int,
        node: HierarchyNode[Role],
        parent_node: HierarchyNode[Role] | None,
        first_visit: bool,
    ) -> None:
        equivalences = node.get_equivalent_elements()
        print_sub_property_of = parent_node is not None
        print_equivalences = first_visit and len(equivalences) > 1
        print_declarations = False
        if first_visit:
            for role in equivalences:
                if self._needs_declaration(role):
                    print_declarations = True
                    break
        if print_sub_property_of or print_equivalences or print_declarations:
            out = self._printer.m_out
            out.write("  " * level)
            after_ws = True
            if print_sub_property_of:
                if self.m_object_properties:
                    out.write("SubObjectPropertyOf( ")
                else:
                    out.write("SubDataPropertyOf( ")
                self._print_role(node.m_representative)
                out.write(" ")
                self._print_role(parent_node.m_representative)  # type: ignore[union-attr]
                out.write(" )")
                after_ws = False
            if print_equivalences:
                if not after_ws:
                    out.write(" ")
                if self.m_object_properties:
                    out.write("EquivalentObjectProperties(")
                else:
                    out.write("EquivalentDataProperties(")
                for role in equivalences:
                    out.write(" ")
                    self._print_role(role)
                out.write(" )")
                after_ws = False
            if print_declarations:
                for role in equivalences:
                    if self._needs_declaration(role):
                        if not after_ws:
                            out.write(" ")
                        out.write("Declaration( ")
                        if self.m_object_properties:
                            out.write("ObjectProperty( ")
                        else:
                            out.write("DataProperty( ")
                        self._print_role(role)
                        out.write(" ) )")
                        after_ws = False
            out.write("\n")

    def _print_role(self, role: Role) -> None:
        out = self._printer.m_out
        if isinstance(role, AtomicRole):
            out.write(self._printer._abbreviate(role.iri))
        elif isinstance(role, InverseRole):
            out.write("ObjectInverseOf( ")
            self._print_role(role.inverse_of)
            out.write(" )")

    @staticmethod
    def _needs_declaration(role: Role) -> bool:
        return (
            role != AtomicRole.BOTTOM_OBJECT_ROLE
            and role != AtomicRole.TOP_OBJECT_ROLE
            and role != AtomicRole.BOTTOM_DATA_ROLE
            and role != AtomicRole.TOP_DATA_ROLE
            and isinstance(role, AtomicRole)
        )


class _RoleComparator:
    """Comparator for sorting roles."""

    @staticmethod
    def compare(role1: Role, role2: Role) -> int:
        comparison = _RoleComparator._get_role_class(role1) - _RoleComparator._get_role_class(role2)
        if comparison != 0:
            return comparison
        comparison = _RoleComparator._get_role_direction(role1) - _RoleComparator._get_role_direction(role2)
        if comparison != 0:
            return comparison
        inner1: AtomicRole = role1 if isinstance(role1, AtomicRole) else cast(InverseRole, role1).inverse_of
        inner2: AtomicRole = role2 if isinstance(role2, AtomicRole) else cast(InverseRole, role2).inverse_of
        return inner1.iri > inner2.iri and 1 or (inner1.iri < inner2.iri and -1 or 0)

    @staticmethod
    def _get_role_class(role: Role) -> int:
        if role == AtomicRole.BOTTOM_OBJECT_ROLE:
            return 0
        if role == AtomicRole.TOP_OBJECT_ROLE:
            return 1
        if role == AtomicRole.BOTTOM_DATA_ROLE:
            return 2
        if role == AtomicRole.TOP_DATA_ROLE:
            return 3
        return 4

    @staticmethod
    def _get_role_direction(role: Role) -> int:
        return 0 if isinstance(role, AtomicRole) else 1


class _AtomicConceptComparator:
    """Comparator for sorting atomic concepts."""

    @staticmethod
    def compare(ac1: AtomicConcept, ac2: AtomicConcept) -> int:
        comparison = _AtomicConceptComparator._get_ac_class(ac1) - _AtomicConceptComparator._get_ac_class(ac2)
        if comparison != 0:
            return comparison
        return ac1.iri > ac2.iri and 1 or (ac1.iri < ac2.iri and -1 or 0)

    @staticmethod
    def _get_ac_class(ac: AtomicConcept) -> int:
        if ac == AtomicConcept.NOTHING:
            return 0
        if ac == AtomicConcept.THING:
            return 1
        return 2


_IT = TypeVar("_IT")


class _IdentityTransformer(Transformer[_IT, _IT]):
    """Identity transformer that preserves element types."""

    def transform(self, obj: _IT) -> _IT:
        return obj

    def determine_representative(
        self, old_representative: _IT, new_equivalent_elements: set[_IT]
    ) -> _IT:
        # Sort and pick first (mimics TreeSet.first())
        return sorted(new_equivalent_elements, key=str)[0]
