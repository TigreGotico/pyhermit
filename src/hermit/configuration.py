"""Configuration for the HermiT reasoner.

Faithful port of ``org.semanticweb.HermiT.Configuration`` from the Java
HermiT OWL reasoner.  All enums, fields, methods, and default values are
preserved.
"""

from __future__ import annotations

__all__ = [
    "Configuration",
    "TableauMonitorType",
    "DirectBlockingType",
    "BlockingStrategyType",
    "BlockingSignatureCacheType",
    "ExistentialStrategyType",
    "WarningMonitor",
]

import copy
from collections.abc import MutableMapping
from enum import Enum
from os import PathLike
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from hermit.model import AtomicConcept
    from hermit.monitor import TableauMonitor


# ---------------------------------------------------------------------------
# Enums — mirror the Java nested enums
# ---------------------------------------------------------------------------

class TableauMonitorType(Enum):
    """Determines which tableau monitor HermiT uses during reasoning."""

    #: No monitor — no information is recorded or printed.
    NONE = "NONE"
    #: Prints tableau information (number of nodes, etc.) at time intervals.
    TIMING = "TIMING"
    #: Like :data:`TIMING` but pauses for a keystroke at certain points.
    TIMING_WITH_PAUSE = "TIMING_WITH_PAUSE"
    #: Opens a debugging application without derivation history.
    DEBUGGER_NO_HISTORY = "DEBUGGER_NO_HISTORY"
    #: Opens a debugging application with full derivation history.
    DEBUGGER_HISTORY_ON = "DEBUGGER_HISTORY_ON"


class DirectBlockingType(Enum):
    """Determines the blocking type used by HermiT."""

    #: Force single blocking even with inverse roles.
    SINGLE = "SINGLE"
    #: Force pairwise blocking even without inverses.
    PAIR_WISE = "PAIR_WISE"
    #: Choose optimal blocking automatically.
    OPTIMAL = "OPTIMAL"


class BlockingStrategyType(Enum):
    """Determines which nodes HermiT considers for blockers."""

    #: Anywhere blocking — usually creates smaller models.
    ANYWHERE = "ANYWHERE"
    #: Ancestor blocking — can be faster in some cases.
    ANCESTOR = "ANCESTOR"
    #: Approximate blocking using complex core concepts.
    COMPLEX_CORE = "COMPLEX_CORE"
    #: Approximate blocking using only simple core concepts.
    SIMPLE_CORE = "SIMPLE_CORE"
    #: Choose optimal strategy automatically.
    OPTIMAL = "OPTIMAL"


class BlockingSignatureCacheType(Enum):
    """Determines whether HermiT caches blockers."""

    #: Use caching if compatible with the ontology.
    CACHED = "CACHED"
    #: Disable caching.
    NOT_CACHED = "NOT_CACHED"


class ExistentialStrategyType(Enum):
    """Determines how HermiT expands the model."""

    #: Expand existentials on the oldest node (breadth-first approximation).
    CREATION_ORDER = "CREATION_ORDER"
    #: Reuse existing individuals before creating fresh successors.
    INDIVIDUAL_REUSE = "INDIVIDUAL_REUSE"
    #: Deterministic individual reuse for EL ontologies.
    EL = "EL"


# ---------------------------------------------------------------------------
# WarningMonitor protocol
# ---------------------------------------------------------------------------

class WarningMonitor(Protocol):
    """Callback interface for warnings emitted by HermiT.

    Users can implement this protocol and assign it to
    :attr:`Configuration.warning_monitor` to receive warning messages
    (for example, when an unsupported datatype is encountered).
    """

    def warning(self, warning: str) -> None:
        """Called when HermiT emits a warning."""
        ...


# ---------------------------------------------------------------------------
# PrepareReasonerInferences
# ---------------------------------------------------------------------------

class PrepareReasonerInferences:
    """Specifies which inferences the reasoner should prepare.

    Mirrors the Java ``Configuration.PrepareReasonerInferences`` inner class.
    """

    def __init__(self) -> None:
        self.class_classification_required: bool = True
        self.object_property_classification_required: bool = True
        self.data_property_classification_required: bool = True
        self.object_property_domains_required: bool = True
        self.object_property_ranges_required: bool = True
        self.realisation_required: bool = True
        self.object_property_realisation_required: bool = True
        self.data_property_realisation_required: bool = True
        self.same_as: bool = True


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Forward-reference types that are not yet ported.
try:
    from owlapi_reasoner_stub import (  # type: ignore[import-not-found]
        FreshEntityPolicy,
        IndividualNodeSetPolicy,
        OWLReasonerConfiguration,
        ReasonerProgressMonitor,
    )
except ImportError:
    # Minimal stand-ins so the module imports without the OWL API.
    from enum import Enum as _Enum

    class FreshEntityPolicy(_Enum):  # type: ignore[no-redef]
        ALLOW = "ALLOW"
        DISALLOW = "DISALLOW"

    class IndividualNodeSetPolicy(_Enum):  # type: ignore[no-redef]
        BY_NAME = "BY_NAME"
        BY_SAME_AS = "BY_SAME_AS"

    class ReasonerProgressMonitor(Protocol):  # type: ignore[no-redef]
        def reasonerTaskStarted(self, task_name: str) -> None: ...
        def reasonerTaskProgressed(self, percentage: int) -> None: ...
        def reasonerTaskStopped(self) -> None: ...

    class OWLReasonerConfiguration(Protocol):  # type: ignore[no-redef]
        @property
        def getFreshEntityPolicy(self) -> FreshEntityPolicy: ...
        @property
        def getIndividualNodeSetPolicy(self) -> IndividualNodeSetPolicy: ...
        @property
        def getProgressMonitor(self) -> ReasonerProgressMonitor | None: ...
        def getTimeOut(self) -> int: ...


class Configuration:
    """Reasoner configuration mirroring the Java ``Configuration`` class.

    Implements the same fields, defaults, and helper methods as the Java
    original.  When the OWL API reasoner interfaces are available the class
    satisfies ``OWLReasonerConfiguration``; otherwise it works stand-alone.
    """

    # ------------------------------------------------------------------
    # Constructor
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        #: Warning monitor callback (``WarningMonitor`` protocol or ``None``).
        self.warning_monitor: WarningMonitor | None = None
        #: Progress monitor reported to the OWL API (or ``None``).
        self.reasoner_progress_monitor: ReasonerProgressMonitor | None = None
        #: Which tableau monitor to use.
        self.tableau_monitor_type: TableauMonitorType = TableauMonitorType.NONE
        #: Blocking type.
        self.direct_blocking_type: DirectBlockingType = DirectBlockingType.OPTIMAL
        #: Blocking strategy.
        self.blocking_strategy_type: BlockingStrategyType = BlockingStrategyType.OPTIMAL
        #: Blocking signature cache.
        self.blocking_signature_cache_type: BlockingSignatureCacheType = (
            BlockingSignatureCacheType.CACHED
        )
        #: Existential expansion strategy.
        self.existential_strategy_type: ExistentialStrategyType = (
            ExistentialStrategyType.CREATION_ORDER
        )
        #: If ``True``, axioms with unsupported datatypes are silently ignored.
        self.ignore_unsupported_datatypes: bool = False
        #: Custom tableau monitor instance (overrides ``tableau_monitor_type``).
        self.monitor: TableauMonitor | None = None
        #: Arbitrary parameters passed to the Tableau class.
        self.parameters: MutableMapping[str, Any] = {}
        #: Timeout in ms for individual reasoning tasks (``-1`` = no timeout).
        self.individual_task_timeout: int = -1
        #: Policy for handling fresh entities.
        self.fresh_entity_policy: FreshEntityPolicy = FreshEntityPolicy.ALLOW
        #: Policy for individual node sets.
        self.individual_node_set_policy: IndividualNodeSetPolicy = (
            IndividualNodeSetPolicy.BY_NAME
        )
        #: If ``True``, disjunction learning with punish factors is enabled.
        self.use_disjunction_learning: bool = True
        #: If ``True``, axiom additions/removals are buffered until ``flush()``.
        self.buffer_changes: bool = True
        #: If ``True``, throw an exception for inconsistent ontologies.
        self.throw_inconsistent_ontology_exception: bool = True
        #: Which inferences to prepare (``None`` = all).
        self.prepare_reasoner_inferences: PrepareReasonerInferences | None = None
        #: If ``True``, always use quasi-order classification.
        self.force_quasi_order_classification: bool = False

    # ------------------------------------------------------------------
    # File-loading helpers for individual reuse strategy
    # ------------------------------------------------------------------

    def _set_individual_reuse_strategy_reuse_always(
        self, concepts: set[AtomicConcept],
    ) -> None:
        """Set concepts that should always be reused."""
        self.parameters["IndividualReuseStrategy.reuseAlways"] = concepts

    def load_individual_reuse_strategy_reuse_always(
        self, file: str | PathLike[str],
    ) -> None:
        """Load reuse-always concepts from a file (one IRI per line)."""
        concepts = self._load_concepts_from_file(file)
        self._set_individual_reuse_strategy_reuse_always(concepts)

    def _set_individual_reuse_strategy_reuse_never(
        self, concepts: set[AtomicConcept],
    ) -> None:
        """Set concepts that should never be reused."""
        self.parameters["IndividualReuseStrategy.reuseNever"] = concepts

    def load_individual_reuse_strategy_reuse_never(
        self, file: str | PathLike[str],
    ) -> None:
        """Load reuse-never concepts from a file (one IRI per line)."""
        concepts = self._load_concepts_from_file(file)
        self._set_individual_reuse_strategy_reuse_never(concepts)

    @staticmethod
    def _load_concepts_from_file(
        file: str | PathLike[str],
    ) -> set[AtomicConcept]:
        from hermit.model import AtomicConcept

        result: set[AtomicConcept] = set()
        with open(file, encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n").rstrip("\r")
                result.add(AtomicConcept.create(line))
        return result

    # ------------------------------------------------------------------
    # Clone
    # ------------------------------------------------------------------

    def clone(self) -> Configuration:
        """Return a shallow copy with a fresh ``parameters`` dict."""
        result = copy.copy(self)
        result.parameters = dict(self.parameters)
        return result

    # ------------------------------------------------------------------
    # OWLReasonerConfiguration compatibility methods
    # ------------------------------------------------------------------

    def getTimeOut(self) -> int:
        """Return the individual task timeout in milliseconds."""
        return self.individual_task_timeout

    def getIndividualNodeSetPolicy(self) -> IndividualNodeSetPolicy:
        """Return the individual node set policy."""
        return self.individual_node_set_policy

    def getProgressMonitor(self) -> ReasonerProgressMonitor | None:
        """Return the reasoner progress monitor."""
        return self.reasoner_progress_monitor

    def getFreshEntityPolicy(self) -> FreshEntityPolicy:
        """Return the fresh entity policy."""
        return self.fresh_entity_policy
