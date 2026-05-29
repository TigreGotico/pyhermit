"""W3C OWL WG conformance suite, run through pyhermit.

Faithful Python mirror of the upstream Java harness in
``org.semanticweb.HermiT.owl_wg_tests`` (WGTestRegistry / WGTestDescriptor /
AllApprovedWGTests / TstDescriptorForMaven). Each DL test case of the selected
status is expanded -- exactly as the Java harness does -- into per-type
subtests (consistency, inconsistency, positive/negative entailment), and each
subtest is parametrized so pass/fail is reported per case.

Set ``PYHERMIT_WG_STATUS=approved_proposed`` to additionally include PROPOSED
DL tests (the maven/quick parametrisation). Default is ``approved``.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

# Load the local ``wg_conformance`` package directly by path. A bare
# ``import tests.wg_conformance`` is unreliable: the top-level ``tests`` name can
# be claimed by another installed package in the active environment, shadowing
# this repo's test directory. Registering the package under a private name keeps
# its internal relative imports working regardless of what owns ``tests``.
_WG_DIR = Path(__file__).parent / "wg_conformance"
_PKG = "_pyhermit_wg_conformance"
if _PKG not in sys.modules:
    _spec = importlib.util.spec_from_file_location(
        _PKG, _WG_DIR / "__init__.py", submodule_search_locations=[str(_WG_DIR)]
    )
    assert _spec is not None and _spec.loader is not None
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_PKG] = _module
    _spec.loader.exec_module(_module)

_registry = importlib.import_module(f"{_PKG}.registry")
_runner = importlib.import_module(f"{_PKG}.runner")
Status = _registry.Status
generate_subtests = _registry.generate_subtests
UnsupportedConclusion = _runner.UnsupportedConclusion
run_subtest = _runner.run_subtest

_STATUS_SETS = {
    "approved": {Status.APPROVED},
    "approved_proposed": {Status.APPROVED, Status.PROPOSED},
}
_SELECTED = _STATUS_SETS[os.environ.get("PYHERMIT_WG_STATUS", "approved")]

_SUBTESTS = generate_subtests(_SELECTED)


@pytest.mark.slow
@pytest.mark.parametrize("subtest", _SUBTESTS, ids=[s.name for s in _SUBTESTS])
def test_wg(subtest):
    try:
        outcome = run_subtest(subtest)
    except UnsupportedConclusion as e:
        pytest.skip(f"conclusion form not yet checkable: {e}")
    assert outcome.passed, outcome.detail
