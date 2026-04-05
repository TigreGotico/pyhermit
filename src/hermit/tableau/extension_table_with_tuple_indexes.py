"""Extension table with tuple indexes -- compatibility shim.

Re-exports ExtensionTableWithTupleIndexes from the extension_manager module.
The actual implementation lives in extension_manager.py.
"""

from __future__ import annotations

from hermit.tableau.extension_manager import (
    ExtensionTableWithTupleIndexes,
)

__all__ = ["ExtensionTableWithTupleIndexes"]
