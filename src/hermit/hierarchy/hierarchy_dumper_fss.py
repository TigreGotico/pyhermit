"""Hierarchy dumper in Functional-Style Syntax.

Faithful port of ``org.semanticweb.HermiT.hierarchy.HierarchyDumperFSS``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TextIO

from hermit.model import AtomicConcept, AtomicRole, Role

if TYPE_CHECKING:
    from hermit.hierarchy.hierarchy import Hierarchy


class HierarchyDumperFSS:
    """Dumps hierarchies in OWL Functional-Style Syntax to a text stream."""

    def __init__(self, out: TextIO) -> None:
        self.m_out = out

    def print_atomic_concept_hierarchy(
        self, atomic_concept_hierarchy: Hierarchy[AtomicConcept]
    ) -> None:
        for node in atomic_concept_hierarchy.get_all_nodes_set():
            equivs = sorted(
                node.get_equivalent_elements(),
                key=lambda ac: (
                    0 if ac == AtomicConcept.NOTHING
                    else 1 if ac == AtomicConcept.THING
                    else 2,
                    ac.iri,
                ),
            )
            representative = equivs[0]
            if len(equivs) > 1:
                first = True
                for equiv in equivs:
                    if first:
                        self.m_out.write(f"EquivalentClasses( <{representative.iri}>")
                        first = False
                    else:
                        self.m_out.write(f" <{equiv.iri}>")
                self.m_out.write(" )\n")
            if representative != AtomicConcept.THING:
                for sub in node.m_child_nodes:
                    sub_representative = sub.m_representative
                    if sub_representative != AtomicConcept.NOTHING:
                        self.m_out.write(
                            f"SubClassOf( <{sub_representative.iri}> "
                            f"<{representative.iri}> )\n"
                        )
        self.m_out.write("\n")

    def print_object_property_hierarchy(
        self, object_role_hierarchy: Hierarchy[Role]
    ) -> None:
        for node in object_role_hierarchy.get_all_nodes_set():
            equivs = sorted(
                node.get_equivalent_elements(),
                key=self._role_sort_key,
            )
            representative = equivs[0]
            if len(equivs) > 1:
                first = True
                for equiv in equivs:
                    if first:
                        self.m_out.write("EquivalentObjectProperties( ")
                        self._print_role(representative)
                        first = False
                    else:
                        self.m_out.write(" ")
                        self._print_role(equiv)
                self.m_out.write(" )\n")
            if representative != AtomicRole.TOP_OBJECT_ROLE:
                for sub in node.m_child_nodes:
                    sub_representative = sub.m_representative
                    if sub_representative != AtomicRole.BOTTOM_OBJECT_ROLE:
                        self.m_out.write("SubObjectPropertyOf( ")
                        self._print_role(sub_representative)
                        self.m_out.write(" ")
                        self._print_role(representative)
                        self.m_out.write(" )\n")
        self.m_out.write("\n")

    def print_data_property_hierarchy(
        self, data_role_hierarchy: Hierarchy[AtomicRole]
    ) -> None:
        for node in data_role_hierarchy.get_all_nodes_set():
            equivs = sorted(
                node.get_equivalent_elements(),
                key=lambda ar: (
                    0 if ar == AtomicRole.BOTTOM_DATA_ROLE
                    else 1 if ar == AtomicRole.TOP_DATA_ROLE
                    else 2,
                    ar.iri,
                ),
            )
            representative = equivs[0]
            if len(equivs) > 1:
                first = True
                for equiv in equivs:
                    if first:
                        self.m_out.write(f"EquivalentDataProperties( <{representative.iri}>")
                        first = False
                    else:
                        self.m_out.write(f" <{equiv.iri}>")
                self.m_out.write(" )\n")
            if representative != AtomicRole.TOP_DATA_ROLE:
                for sub in node.m_child_nodes:
                    sub_representative = sub.m_representative
                    if sub_representative != AtomicRole.BOTTOM_DATA_ROLE:
                        self.m_out.write(
                            f"SubDataPropertyOf( <{sub_representative.iri}> "
                            f"<{representative.iri}> )\n"
                        )
        self.m_out.write("\n")

    # -- internal helpers --------------------------------------------------

    def _print_role(self, role: Role) -> None:
        if isinstance(role, AtomicRole):
            self.m_out.write(f"<{role.iri}>")
        else:
            self.m_out.write("ObjectInverseOf( ")
            self.m_out.write(f"<{role.inverse_of.iri}>")  # type: ignore[union-attr]
            self.m_out.write(" )")

    def _role_sort_key(self, role: Role) -> tuple[int, int, str]:
        role_class = self._get_role_class(role)
        role_direction = 0 if isinstance(role, AtomicRole) else 1
        inner: AtomicRole = role if isinstance(role, AtomicRole) else role.inverse_of  # type: ignore[assignment]
        return (role_class, role_direction, inner.iri)

    @staticmethod
    def _get_role_class(role: Role) -> int:
        if role == AtomicRole.BOTTOM_OBJECT_ROLE:
            return 0
        if role == AtomicRole.TOP_OBJECT_ROLE:
            return 1
        return 2
