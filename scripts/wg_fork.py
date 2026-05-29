"""Fork-isolated WG conformance driver.

Runs each subtest in a forked child so a hung case (e.g. blocked on a reasoner
timer thread, which SIGALRM cannot interrupt) can be hard-killed by the parent.
The child inherits already-imported modules, so per-case overhead is just fork.

Usage: python tools_wg_fork.py [approved|approved_proposed] [--timeout=N] [--list-fails] [filter]
"""

from __future__ import annotations

import os
import select
import signal
import sys
import time
from collections import Counter

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "tests"))

from wg_conformance.registry import Status, generate_subtests  # noqa: E402
from wg_conformance.runner import UnsupportedConclusion, run_subtest  # noqa: E402

_STATUS = {"approved": {Status.APPROVED}, "approved_proposed": {Status.APPROVED, Status.PROPOSED}}


def run_child(subtest, w: int) -> None:
    try:
        outcome = run_subtest(subtest)
        msg = ("P:" if outcome.passed else "F:") + (outcome.detail or "")
    except UnsupportedConclusion as e:
        msg = "S:" + str(e)
    except Exception as e:  # noqa: BLE001
        msg = "E:" + f"{type(e).__name__}: {e}"
    try:
        os.write(w, msg[:300].encode("utf-8", "replace"))
    except OSError:
        pass
    os._exit(0)


def main() -> None:
    args = sys.argv[1:]
    list_fails = "--list-fails" in args
    timeout = 10.0
    for a in args:
        if a.startswith("--timeout="):
            timeout = float(a.split("=", 1)[1])
    status_key = next((a for a in args if a in _STATUS), "approved")
    filt = next((a for a in args if not a.startswith("--") and a not in _STATUS), None)

    subs = generate_subtests(_STATUS[status_key])
    if filt:
        subs = [s for s in subs if filt in s.name]

    passed = failed = skipped = errored = timed_out = 0
    by_type_total: Counter = Counter()
    by_type_pass: Counter = Counter()
    fails: list[tuple[str, str]] = []
    t0 = time.time()

    for s in subs:
        by_type_total[s.test_type.value] += 1
        r, w = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(r)
            run_child(s, w)
            return  # unreachable
        os.close(w)
        buf = b""
        deadline = time.time() + timeout
        killed = False
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                os.kill(pid, signal.SIGKILL)
                killed = True
                break
            ready, _, _ = select.select([r], [], [], remaining)
            if ready:
                chunk = os.read(r, 4096)
                if not chunk:
                    break
                buf += chunk
            else:
                os.kill(pid, signal.SIGKILL)
                killed = True
                break
        os.close(r)
        os.waitpid(pid, 0)

        if killed:
            timed_out += 1
            fails.append((s.name, f"TIMEOUT >{timeout:g}s"))
            continue
        msg = buf.decode("utf-8", "replace")
        tag, _, detail = msg.partition(":")
        if tag == "P":
            passed += 1
            by_type_pass[s.test_type.value] += 1
        elif tag == "F":
            failed += 1
            if list_fails:
                fails.append((s.name, detail))
        elif tag == "S":
            skipped += 1
        else:
            errored += 1
            fails.append((s.name, "ERROR: " + detail))

    dt = time.time() - t0
    total = len(subs)
    print(f"\n=== WG conformance ({status_key}) ===")
    print(f"total={total} passed={passed} failed={failed} errored={errored} "
          f"timed_out={timed_out} skipped={skipped}  ({dt:.1f}s)")
    print("by type (passed/total):")
    for t in sorted(by_type_total):
        print(f"  {t:24s} {by_type_pass[t]}/{by_type_total[t]}")
    if list_fails:
        print("\n--- non-passing ---")
        for name, detail in fails:
            print(f"  {name}: {detail.replace(chr(10), ' ')[:150]}")


if __name__ == "__main__":
    main()
