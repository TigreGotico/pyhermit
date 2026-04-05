"""Extension table with full index -- compatibility shim.

Re-exports ExtensionTableWithFullIndex from the extension_manager module.
The actual implementation lives in extension_manager.py.
"""

from __future__ import annotations

from hermit.tableau.extension_manager import (
    ExtensionTableWithFullIndex,
)

__all__ = ["ExtensionTableWithFullIndex"]
