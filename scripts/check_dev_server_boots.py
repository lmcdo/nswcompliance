#!/usr/bin/env python3
"""Does `next dev` actually start? Nothing checked, so it was dead for 20 days.

prior-art-checked: reuse not viable because no boot check exists. Sweeps
2026-08-12 on origin/main 7fd01095: .github/workflows/gates.yml runs jest and
`next build` but never `next dev`; .githooks/* run tests and linters only;
`grep -rn "next dev" .github .githooks` returns nothing. The two are NOT
interchangeable -- issue #929 is a route collision that `next build` tolerates
and `next dev` refuses, which is exactly why a passing build hid it.

WHAT THIS CATCHES
-----------------
`app/sitemap.ts` (metadata route) and `app/sitemap.xml/route.ts` both claim
/sitemap.xml. Dev's route sorter rejects the collision and the process exits;
build sorts it and ships. Introduced 2026-07-23 in #799 and unnoticed until
someone tried to run the app on 2026-08-12.

Exit 0 = the server reached "Ready". Exit 1 = it exited or timed out first.
Exit 2 = could not run at all (no node_modules) -- UNKNOWN, never reported as
healthy.
"""
from __future__ import annotations

import argparse
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_APP = _ROOT / "frontend-nextjs"

# ONLY "Ready in". Not "- Local: http", and this is the whole lesson: Next
# prints the Local URL BEFORE it sorts routes, so the first version of this
# check matched that line and returned OK against an app that then died on the
# #929 route collision two lines later. A check that passes on the broken thing
# is worse than no check. Even "Ready in" is not trusted alone -- the port is
# probed over HTTP below.
_READY = re.compile(r"Ready in", re.I)
_FATAL = re.compile(
    r"(Error:|error occurred|EADDRINUSE|Cannot find module|"
    r"same specificity as a optional catch-all)", re.I
)


def _say(line: str) -> None:
    """Print a captured line safely.

    Next's banner contains U+25B2 and friends, and a Windows console on cp1252
    raises UnicodeEncodeError printing them -- which crashed the FAILURE path
    of this very check, turning a clean diagnosis into a traceback.
    """
    safe = line.encode("ascii", "replace").decode("ascii")
    print(f"  {safe}")


def _probe(port: int) -> int | None:
    """HTTP status from the dev server, or None if it will not answer."""
    import urllib.error
    import urllib.request

    for _ in range(10):
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/", timeout=10
            ) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            return exc.code  # a 404/500 still means it is SERVING
        except (urllib.error.URLError, OSError):
            time.sleep(2)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--port", type=int, default=3099,
                    help="deliberately not 3003 — never fight a real dev server")
    args = ap.parse_args()

    if not (_APP / "node_modules").exists():
        print("BOOT CHECK: UNKNOWN — frontend-nextjs/node_modules absent.")
        print("  Cannot answer, so not answering. Run npm ci first.")
        return 2

    env = dict(os.environ, PORT=str(args.port), NEXT_TELEMETRY_DISABLED="1")
    # start_new_session puts the child in its OWN process group. Without it the
    # child shares the runner's group, and the killpg in the finally block below
    # takes out this script AND the CI step along with the server -- observed as
    # "Process completed with exit code 143" (SIGTERM) four seconds in, with no
    # output at all. Windows hid it, because there the cleanup is a taskkill on
    # a specific PID rather than a group signal.
    proc = subprocess.Popen(
        ["npx", "next", "dev", "--port", str(args.port)],
        cwd=_APP, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", env=env,
        shell=(os.name == "nt"),
        start_new_session=(os.name != "nt"),
    )

    deadline = time.time() + args.timeout
    captured: list[str] = []
    try:
        while time.time() < deadline:
            line = proc.stdout.readline() if proc.stdout else ""
            if line:
                captured.append(line.rstrip())
                # FATAL is tested BEFORE ready, deliberately. A line can carry
                # both, and an error must win: with a stale process on the port
                # this reported "said Ready but the port refused" while the real
                # cause, EADDRINUSE, sat two lines below. Right verdict, wrong
                # diagnosis — and a wrong diagnosis sends the next person hunting
                # the wrong bug.
                if _FATAL.search(line):
                    print("BOOT CHECK: FAILED — dev server reported a fatal error.")
                    for l in captured[-15:]:
                        _say(l)
                    return 1
                if _READY.search(line):
                    # Announced ready. Now make it prove it: a process can print
                    # Ready and still be unable to serve. Belt and braces because
                    # this check already fooled itself once.
                    code = _probe(args.port)
                    if code is None:
                        print("BOOT CHECK: FAILED — said Ready but the port "
                              "refused an HTTP request.")
                        for l in captured[-15:]:
                            _say(l)
                        return 1
                    print(f"BOOT CHECK: OK — dev server ready on :{args.port}, "
                          f"HTTP {code}")
                    return 0
            elif proc.poll() is not None:
                print(f"BOOT CHECK: FAILED — dev server exited "
                      f"(code {proc.returncode}) before serving.")
                for l in captured[-15:]:
                    _say(l)
                return 1
        print(f"BOOT CHECK: FAILED — no ready signal within {args.timeout}s.")
        for l in captured[-15:]:
            _say(l)
        return 1
    finally:
        # Kill by the handle we own. Never by process name: this repo's CLAUDE.md
        # records that killing node by image name takes out unrelated services.
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                               capture_output=True)
            else:
                # Only safe because Popen used start_new_session: the child has
                # its own group, so this cannot reach back and kill this script
                # or the CI step running it. Guarded anyway — if the child is
                # somehow in OUR group, signal the process alone.
                pgid = os.getpgid(proc.pid)
                if pgid != os.getpgid(0):
                    os.killpg(pgid, signal.SIGTERM)
                else:
                    proc.terminate()
        except (OSError, subprocess.SubprocessError, ProcessLookupError):
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
