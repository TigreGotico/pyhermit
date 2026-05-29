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

import os

import pytest

from tests.wg_conformance.registry import Status, generate_subtests
from tests.wg_conformance.runner import UnsupportedConclusion, run_subtest

_STATUS_SETS = {
    "approved": {Status.APPROVED},
    "approved_proposed": {Status.APPROVED, Status.PROPOSED},
}
_SELECTED = _STATUS_SETS[os.environ.get("PYHERMIT_WG_STATUS", "approved")]

_SUBTESTS = generate_subtests(_SELECTED)


@pytest.mark.parametrize("subtest", _SUBTESTS, ids=[s.name for s in _SUBTESTS])
def test_wg(subtest):
    try:
        outcome = run_subtest(subtest)
    except UnsupportedConclusion as e:
        pytest.skip(f"conclusion form not yet checkable: {e}")
    assert outcome.passed, outcome.detail
