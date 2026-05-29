"""Standalone WG conformance baseline runner.

Runs each subtest in a forked child process with a hard timeout (mirrors the
upstream 300s InterruptTimer; a timeout counts as a failure, as it does in the
Java harness). Reports pass/fail/error/timeout/skip counts broken down by test
type and status.

Usage:
    python -m tests.wg_conformance.baseline [approved|approved_proposed] [timeout_s]
"""

from __future__ import annotations

import multiprocessing as mp
import sys
import traceback
from collections import Counter

from .registry import Status, generate_subtests
from .runner import UnsupportedConclusion, run_subtest


def _worker(subtest, q):
    try:
        outcome = run_subtest(subtest)
        q.put(("pass" if outcome.passed else "fail", outcome.detail))
    except UnsupportedConclusion as e:
        q.put(("skip", str(e)))
    except Exception as e:  # noqa: BLE001
        q.put(("error", f"{type(e).__name__}: {e}\n{traceback.format_exc()[-500:]}"))


def run(status_key: str, timeout_s: float) -> None:
    sel = {
        "approved": {Status.APPROVED},
        "approved_proposed": {Status.APPROVED, Status.PROPOSED},
    }[status_key]
    subtests = generate_subtests(sel)
    ctx = mp.get_context("fork")

    by_cat: dict[str, Counter] = {}
    failures: list[tuple[str, str, str]] = []
    total = Counter()

    for i, st in enumerate(subtests, 1):
        q = ctx.Queue()
        p = ctx.Process(target=_worker, args=(st, q))
        p.start()
        p.join(timeout_s)
        if p.is_alive():
            p.terminate()
            p.join()
            result, detail = "timeout", f">{timeout_s}s"
        else:
            try:
                result, detail = q.get_nowait()
            except Exception:  # noqa: BLE001
                result, detail = "error", "child died without result"
        cat = st.test_type.value
        by_cat.setdefault(cat, Counter())[result] += 1
        total[result] += 1
        if result in ("fail", "error", "timeout"):
            failures.append((st.name, result, detail))
        marker = {"pass": ".", "fail": "F", "error": "E", "timeout": "T", "skip": "s"}[result]
        sys.stdout.write(marker)
        sys.stdout.flush()
        if i % 80 == 0:
            sys.stdout.write(f"  {i}/{len(subtests)}\n")
    print()
    print("=" * 70)
    print(f"WG conformance baseline ({status_key}), timeout={timeout_s}s")
    print(f"Total subtests: {len(subtests)}")
    print(f"Overall: {dict(total)}")
    print("-" * 70)
    for cat in sorted(by_cat):
        print(f"  {cat:22s} {dict(by_cat[cat])}")
    print("-" * 70)
    print(f"FAILURES / ERRORS / TIMEOUTS ({len(failures)}):")
    fcounter = Counter(d.split(':')[0] if r == 'error' else r for n, r, d in failures)
    print(f"  cluster summary: {dict(fcounter)}")
    for name, result, detail in failures:
        print(f"  [{result}] {name}: {detail[:120]}")


if __name__ == "__main__":
    status_key = sys.argv[1] if len(sys.argv) > 1 else "approved"
    timeout_s = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    run(status_key, timeout_s)
