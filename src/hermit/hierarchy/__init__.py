"""Hierarchy classification and instance management.

Ports the HermiT Java hierarchy package:
- Hierarchy, HierarchyNode, HierarchySearch
- DeterministicClassification, QuasiOrderClassification
- InstanceManager, RoleElementManager
- HierarchyPrinterFSS, HierarchyDumperFSS
"""

from __future__ import annotations

from hermit.hierarchy.atomic_concept_element import AtomicConceptElement
from hermit.hierarchy.classification_progress_monitor import (
    ClassificationProgressMonitor,
)
from hermit.hierarchy.deterministic_classification import (
    DeterministicClassification,
    GraphNode,
)
from hermit.hierarchy.hierarchy import Hierarchy, Transformer
from hermit.hierarchy.hierarchy_dumper_fss import HierarchyDumperFSS
from hermit.hierarchy.hierarchy_node import HierarchyNode
from hermit.hierarchy.hierarchy_printer_fss import HierarchyPrinterFSS
from hermit.hierarchy.hierarchy_search import (
    HierarchySearch,
    Relation,
    SearchPredicate,
)
from hermit.hierarchy.instance_manager import InstanceManager
from hermit.hierarchy.quasi_order_classification import QuasiOrderClassification
from hermit.hierarchy.quasi_order_classification_for_roles import (
    QuasiOrderClassificationForRoles,
)
from hermit.hierarchy.role_element_manager import RoleElement, RoleElementManager

__all__ = [
    "AtomicConceptElement",
    "ClassificationProgressMonitor",
    "DeterministicClassification",
    "GraphNode",
    "Hierarchy",
    "HierarchyDumperFSS",
    "HierarchyNode",
    "HierarchyPrinterFSS",
    "HierarchySearch",
    "InstanceManager",
    "QuasiOrderClassification",
    "QuasiOrderClassificationForRoles",
    "Relation",
    "RoleElement",
    "RoleElementManager",
    "SearchPredicate",
    "Transformer",
]
