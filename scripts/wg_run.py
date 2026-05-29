"""Standalone WG conformance driver.

Bypasses the shared-venv top-level ``tests`` package collision by importing the
local ``tests/wg_conformance`` package directly as ``wg_conformance``. Tallies
pass/fail/skip with a breakdown by test type and prints failing identifiers.

Usage: python tools_wg_run.py [approved|approved_proposed] [--list-fails] [filter]
"""

from __future__ import annotations

import os
import signal
import sys
import time
from collections import Counter


class _Timeout(Exception):
    pass


def _alarm(signum, frame):  # noqa: ANN001
    raise _Timeout()

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "tests"))  # make wg_conformance importable

from wg_conformance.registry import Status, generate_subtests  # noqa: E402
from wg_conformance.runner import UnsupportedConclusion, run_subtest  # noqa: E402

_STATUS_SETS = {
    "approved": {Status.APPROVED},
    "approved_proposed": {Status.APPROVED, Status.PROPOSED},
}


def main() -> None:
    args = sys.argv[1:]
    list_fails = "--list-fails" in args
    args = [a for a in args if a != "--list-fails"]
    status_key = args[0] if args and args[0] in _STATUS_SETS else "approved"
    filt = None
    rest = [a for a in args if a not in _STATUS_SETS and not a.startswith("--")]
    if rest:
        filt = rest[0]

    subtests = generate_subtests(_STATUS_SETS[status_key])
    if filt:
        subtests = [s for s in subtests if filt in s.name]

    per_case_timeout = 0
    for a in list(args):
        if a.startswith("--timeout="):
            per_case_timeout = int(a.split("=", 1)[1])
    if per_case_timeout:
        signal.signal(signal.SIGALRM, _alarm)

    passed = failed = skipped = errored = timed_out = 0
    by_type_total: Counter = Counter()
    by_type_pass: Counter = Counter()
    fails: list[tuple[str, str]] = []
    t0 = time.time()
    for s in subtests:
        ttype = s.test_type.value
        by_type_total[ttype] += 1
        if per_case_timeout:
            signal.alarm(per_case_timeout)
        try:
            outcome = run_subtest(s)
        except _Timeout:
            timed_out += 1
            fails.append((s.name, f"TIMEOUT >{per_case_timeout}s"))
            continue
        except UnsupportedConclusion as e:
            skipped += 1
            if list_fails:
                fails.append((s.name, f"SKIP: {e}"))
            continue
        except Exception as e:  # noqa: BLE001
            errored += 1
            fails.append((s.name, f"ERROR: {type(e).__name__}: {e}"))
            continue
        if outcome.passed:
            passed += 1
            by_type_pass[ttype] += 1
        else:
            failed += 1
            if list_fails:
                fails.append((s.name, outcome.detail))
    if per_case_timeout:
        signal.alarm(0)
    dt = time.time() - t0

    total = len(subtests)
    print(f"\n=== WG conformance ({status_key}) ===")
    print(f"total={total} passed={passed} failed={failed} "
          f"errored={errored} timed_out={timed_out} skipped={skipped}  ({dt:.1f}s)")
    print("by type (passed/total):")
    for t in sorted(by_type_total):
        print(f"  {t:24s} {by_type_pass[t]}/{by_type_total[t]}")
    if list_fails:
        print("\n--- non-passing ---")
        for name, detail in fails:
            d = detail.replace("\n", " ")[:160]
            print(f"  {name}: {d}")


if __name__ == "__main__":
    main()
