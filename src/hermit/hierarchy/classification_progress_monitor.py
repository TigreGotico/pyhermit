"""Progress monitor interface for classification.

Faithful port of
``org.semanticweb.HermiT.hierarchy.ClassificationProgressMonitor``.
"""

from __future__ import annotations

from typing import Protocol

from hermit.model import AtomicConcept


class ClassificationProgressMonitor(Protocol):
    """Receives progress notifications during classification."""

    def element_classified(self, element: AtomicConcept) -> None:
        """Called when *element* has been classified."""
        ...
