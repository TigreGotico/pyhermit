"""Blocking strategies for tableau termination.

This package contains the blocking machinery used by the HermiT tableau
calculus to ensure termination.  Blocking detects when a node in the
completion graph has a label that is subsumed by (or equivalent to) another
node, allowing the reasoner to stop expanding that branch.

Public API
----------
BlockingStrategy
    Abstract interface for all blocking strategies.
AncestorBlocking
    Blocks a node only against its ancestors in the tableau tree.
AnywhereBlocking
    Blocks a node against any other node in the tableau.
AnywhereValidatedBlocking
    Anywhere blocking with validation of block soundness.
BlockingSignature
    Abstract base for blocking signatures used in caches.
BlockingSignatureCache
    Hash-based cache of blocking signatures.
BlockingValidator
    Validates that blocks are sound with respect to DL clause applicability.
DirectBlockingChecker
    Abstract interface for direct blocking checks.
SingleDirectBlockingChecker
    Checks blocking based solely on atomic concept labels.
PairWiseDirectBlockingChecker
    Checks blocking based on node+parent labels and role edges.
ValidatedSingleDirectBlockingChecker
    Single blocking with validation tracking.
ValidatedPairwiseDirectBlockingChecker
    Pairwise blocking with validation tracking.
ValidatedBlockingObject
    Protocol for blocking objects that support validation.
SetFactory
    Factory that canonicalises immutable sets for identity comparison.
"""

from __future__ import annotations

__all__ = [
    # Strategies
    "AncestorBlocking",
    "AnywhereBlocking",
    "AnywhereValidatedBlocking",
    "BlockingStrategy",
    # Core interfaces
    "DirectBlockingChecker",
    "BlockingSignature",
    "ValidatedBlockingObject",
    # Checkers
    "SingleDirectBlockingChecker",
    "SingleBlockingObject",
    "SingleBlockingSignature",
    "PairWiseDirectBlockingChecker",
    "PairWiseBlockingObject",
    "PairWiseBlockingSignature",
    "ValidatedSingleDirectBlockingChecker",
    "ValidatedSingleBlockingObject",
    "ValidatedSingleBlockingSignature",
    "ValidatedPairwiseDirectBlockingChecker",
    "ValidatedPairwiseBlockingObject",
    "ValidatedPairwiseBlockingSignature",
    # Caches and validators
    "BlockingSignatureCache",
    "BlockingValidator",
    "DLClauseInfo",
    # Utilities
    "SetFactory",
    "Entry",
]

# -- Strategy classes -------------------------------------------------------
from .ancestor_blocking import AncestorBlocking
from .anywhere_blocking import AnywhereBlocking
from .anywhere_validated_blocking import AnywhereValidatedBlocking
from .blocking_strategy import BlockingStrategy

# -- Core interfaces --------------------------------------------------------
from .blocking_signature import BlockingSignature
from .blocking_validator import BlockingValidator, DLClauseInfo
from .direct_blocking_checker import DirectBlockingChecker
from .set_factory import Entry, SetFactory

# -- Concrete checkers ------------------------------------------------------
from .pairwise_direct_blocking_checker import (
    PairWiseBlockingObject,
    PairWiseBlockingSignature,
    PairWiseDirectBlockingChecker,
)
from .single_direct_blocking_checker import (
    SingleBlockingObject,
    SingleBlockingSignature,
    SingleDirectBlockingChecker,
)
from .validated_pairwise_direct_blocking_checker import (
    ValidatedPairwiseBlockingObject,
    ValidatedPairwiseBlockingSignature,
    ValidatedPairwiseDirectBlockingChecker,
)
from .validated_single_direct_blocking_checker import (
    ValidatedBlockingObject,
    ValidatedSingleBlockingObject,
    ValidatedSingleBlockingSignature,
    ValidatedSingleDirectBlockingChecker,
)
