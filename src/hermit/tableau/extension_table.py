"""Extension table base types and view enumeration.

This module provides the `View` enum and re-exports the core
ExtensionTable and Retrieval types from the existing
extension_manager module for compatibility with the Java package layout.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from hermit.tableau.extension_manager import (
    ExtensionTable,
    Retrieval,
)

if TYPE_CHECKING:
    pass


class View(Enum):
    """Extension view controlling which tuples are visible during retrieval.

    The tableau distinguishes between several "views" of the extension:
    - EXTENSION_THIS: Tuples added in the current saturation step.
    - EXTENSION_OLD: Tuples that existed before the current saturation step.
    - DELTA_OLD: Tuples that were newly added in the previous saturation step.
    - TOTAL: All tuples.
    """

    EXTENSION_THIS = "EXTENSION_THIS"
    EXTENSION_OLD = "EXTENSION_OLD"
    DELTA_OLD = "DELTA_OLD"
    TOTAL = "TOTAL"


__all__ = ["View", "ExtensionTable", "Retrieval"]
