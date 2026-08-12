#!/usr/bin/env python3
"""Assert what the RUNNING app tells a user, not what the code or data says.

prior-art-checked: reuse not viable because every existing check reads code or
data AT REST. Sweeps 2026-08-12 on origin/main 7fd01095: gates.yml runs jest
(mocked), tsc, linters and the schema contract; scripts/dq_probe_live.py queries
the database; scripts/doc_claims.py reads docs. `grep -rn "localhost:300" .github
.githooks scripts` finds nothing that makes an HTTP request to the app. That gap
is how all three of today's findings survived -- #929 (dev dead 20 days), #928 (a
fabricated regulatory table served with success:true), and the flood reports
crediting a source never queried.

Point it at a running server:

    npm --prefix frontend-nextjs run build && npm --prefix frontend-nextjs start &
    python scripts/check_served_output.py --base-url http://127.0.0.1:3000

Exit 0 = every contract held. 1 = a contract broke. 2 = no server (UNKNOWN,
never reported as healthy).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def _get(url: str, timeout: int = 30):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as e:
        return None, str(e)


def _json(body: str):
    try:
        return json.loads(body)
    except ValueError:
        return None


def check_pages(base: str) -> list[str]:
    """Pages a user actually lands on must render, not 404 or 500."""
    fails = []
    for path in ("/", "/granny-flat", "/reports/flood", "/site-directory",
                 "/sitemap.xml", "/sitemap/0.xml"):
        status, _ = _get(base + path)
        if status != 200:
            fails.append(f"{path} returned {status}, expected 200")
    return fails


def check_no_fabricated_zone_table(base: str) -> list[str]:
    """A zone->permitted-use answer must come from the LEP data, not a literal.

    Issue #928: /api/development-types serves ZONE_DEVELOPMENT_MAPPING, a
    hardcoded table, to the UI. Permitted uses are per-LEP and per-council, so a
    statewide R2 answer with no council in the request cannot be sourced. This
    asserts the SHAPE of the defect -- an answer returned for a bare zone with
    no council scope -- rather than the specific strings, so it keeps holding
    after the endpoint is rewritten.
    """
    status, body = _get(f"{base}/api/development-types?zone=R2")
    if status is None:
        return ["/api/development-types unreachable"]
    data = _json(body)
    if not isinstance(data, dict):
        return []
    rows = data.get("data") or []
    if rows:
        return [
            "/api/development-types?zone=R2 returned "
            f"{len(rows)} permitted-use row(s) for a bare zone with NO council. "
            "Permitted uses are per-LEP and per-council, so a statewide answer "
            "cannot be sourced from data — see issue #928 "
            "(ZONE_DEVELOPMENT_MAPPING) and .claude/rules/regulatory-data.md."
        ]
    return []


def check_empty_is_not_success(base: str) -> list[str]:
    """`success: true` with zero rows and no reason is the silent-failure shape.

    .claude/rules/pre-pr-review.md check 4: if this fails, does it fail visibly
    or silently? An empty array indistinguishable from a backend failure is the
    worst answer a report API can give.
    """
    status, body = _get(f"{base}/api/development-types")
    data = _json(body)
    if not isinstance(data, dict):
        return []
    if data.get("success") is True and not (data.get("data") or []):
        if not any(k in data for k in ("reason", "error", "message", "status")):
            return [
                "/api/development-types (no zone) returns success:true with an "
                "empty data array and no reason field — a caller cannot tell "
                "'nothing applies' from 'the lookup failed'."
            ]
    return []


CONTRACTS = [
    ("pages render", check_pages),
    ("no fabricated zone table", check_no_fabricated_zone_table),
    ("empty is not success", check_empty_is_not_success),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base-url", default="http://127.0.0.1:3000")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")

    status, _ = _get(base + "/", timeout=15)
    if status is None:
        print(f"SERVED OUTPUT: UNKNOWN — nothing answering at {base}")
        print("  Start the app first. UNKNOWN is not healthy.")
        return 2

    failures = []
    for name, fn in CONTRACTS:
        found = fn(base)
        print(f"  {'FAIL' if found else 'ok  '}  {name}")
        failures.extend(found)

    print()
    if failures:
        print(f"SERVED OUTPUT: FAILED — {len(failures)} contract(s) broken")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("SERVED OUTPUT: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
