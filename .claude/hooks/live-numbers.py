#!/usr/bin/env python3
# prior-art-checked: four sweeps 2026-10-09 on this branch. (1) DB content: N/A,
# this hook defines no query of its own - it imports PROBES from
# scripts/dq_probe_live.py so there is exactly one definition of each SQL and a
# hook copy cannot drift from the ledger. (2) Frontend: grep over
# frontend-nextjs/{app,components,hooks} finds no surface that briefs a terminal
# session, and a web page could not. (3) Python: .claude/hooks/ holds 13 hooks.
# The two UserPromptSubmit ones are capability-audit-trigger.py, which WALKS THE
# CODEBASE to list what exists and reads no database, and done-when-template.py,
# which injects text. The two SessionStart ones are session-capability-index.py
# (static walk) and session-applicability-status.py, which DOES run live probes -
# but once per session, and it shells out one subprocess per probe, which is the
# thing that cannot be done per prompt. This is that hook's measurement habit at
# prompt cadence, with one connection and a cache. Deliberately a separate file
# for the same reason that one is separate from the capability index: a static
# banner must not fail when Supabase is slow. (4) Plans + memory: MEMORY.md and
# ~/.claude/plans/INDEX.md record no per-prompt data banner.
"""Put the provenance numbers in front of every prompt, so a claim that
contradicts them is visible in the same breath as the claim.

WHY THIS EXISTS
---------------
Asked on 2026-10-09 what data verification runs automatically with each prompt,
the answer was: nothing. Of the two UserPromptSubmit hooks, one prints a static
inventory of what exists and the other injects a reporting rule. Neither touches
the database.

That matters because of where the errors actually happen. Over 2026-10-08/09,
eight wrong claims about this data were made IN CONVERSATION - "the 900 m2
minimum is not in the database" (wrong table searched), "Cumberland has no 6 m
front setback" (a LIMIT 20 hid it), "the DCP tab reports Cumberland as
uncovered" (a site-wide banner misread). Every one was caught at commit time, at
push time, or because a query happened to get run. Nothing in the per-prompt
path could have caught any of them, because nothing in the per-prompt path looks
at data.

So this prints four readings, measured, with the command that produced each.

WHAT IT DOES NOT DO
-------------------
It does not run the ledger. dq_check.py covers 158 rows and takes minutes; a
banner that slow gets switched off, and a hook that is switched off measures
nothing. These four are the provenance family - is a number traceable, is it
scoped, can the public write it, is a control missing - and they total ~60 ms of
query time.

It does not connect on every prompt either. The readings are cached for
CACHE_TTL_S and only re-measured when stale, so a conversation costs at most one
connection per ten minutes. A stale cache is printed WITH ITS AGE rather than
silently refreshed, because a number whose age is hidden is the problem this
whole campaign exists to fix.

UNKNOWN IS NOT ZERO
-------------------
If the database cannot be reached the hook says so in those words. Printing
nothing, or printing 0, would read as "all clear" - which is exactly how
`feedback-a-check-can-watch-the-field-the-fix-abandoned` happened.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
CACHE = ROOT / ".claude" / ".live-numbers-cache.json"
CACHE_TTL_S = 600          # ten minutes
CONNECT_TIMEOUT_S = 6      # a prompt must never wait longer than this

#: (DQ id, what a non-zero reading means). Kept to the provenance family and to
#: probes measured at 13-16 ms each on 2026-10-09.
WATCHED: list[tuple[str, str]] = [
    ("DQ-136", "statewide rules whose number no machine can trace to its clause"),
    ("DQ-137", "figures scoped ALL, so a determination picks among them"),
    ("DQ-138", "rule tables the public browser key can write"),
    ("DQ-139", "council/dev-type pairs whose setback arithmetic lacks a control"),
]


def _load(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ImportError(relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _measure() -> dict:
    """One connection, every watched probe. Raises on failure; the caller
    decides what an unreachable database means."""
    sys.path.insert(0, str(ROOT / "scripts"))
    probes = _load("_ln_probes", "scripts/dq_probe_live.py").PROBES
    db = _load("_ln_db", "scripts/dq_db.py")

    conn = db.connect()
    try:
        cur = conn.cursor()
        readings = {}
        for dq_id, _ in WATCHED:
            entry = probes.get(dq_id)
            if entry is None:
                readings[dq_id] = None
                continue
            _, sql, params, _ = entry
            cur.execute(sql, params)
            readings[dq_id] = cur.fetchone()[0]
    finally:
        conn.close()
    return {"at": time.time(), "readings": readings}


def _cached() -> dict | None:
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - absent or corrupt is the same here
        return None


def _save(payload: dict) -> None:
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(payload), encoding="utf-8")
    except Exception:  # noqa: BLE001 - a cache that cannot be written is not fatal
        pass


def _render(payload: dict, age_s: float, note: str = "") -> str:
    freshness = "measured now" if age_s < 2 else f"measured {int(age_s)}s ago"
    lines = [f"PROVENANCE NUMBERS ({freshness}, read-only){note}"]
    readings = payload.get("readings") or {}
    for dq_id, means in WATCHED:
        value = readings.get(dq_id)
        shown = "UNKNOWN" if value is None else f"{value:,}"
        lines.append(f"  {dq_id}  {shown:>9}  {means}")
    lines.append("  target for all four: 0. Re-run any of them:")
    lines.append("    python scripts/dq_probe_live.py --id DQ-136   # and 137, 138, 139")
    lines.append("  A reading above is a FLOOR, not a ceiling: DQ-137 and DQ-139 each")
    lines.append("  carry a recorded scope limit, so the real figure is at least this.")
    return "\n".join(lines)


def main() -> int:
    cached = _cached()
    now = time.time()

    if cached and (now - float(cached.get("at", 0))) < CACHE_TTL_S:
        print(_render(cached, now - float(cached["at"])))
        return 0

    try:
        os.environ.setdefault("PGCONNECT_TIMEOUT", str(CONNECT_TIMEOUT_S))
        fresh = _measure()
    except Exception as exc:  # noqa: BLE001
        first = str(exc).splitlines()[0][:90]
        if cached:
            age = now - float(cached.get("at", 0))
            print(_render(
                cached, age,
                note=f"\n  ! could not refresh ({first}); the figures below are "
                     f"{int(age)}s old, which is NOT the same as current",
            ))
        else:
            print("PROVENANCE NUMBERS: UNKNOWN - the database could not be reached "
                  f"({first}).\n  UNKNOWN is not zero. Run "
                  "`python scripts/dq_probe_live.py --id DQ-136` when it is back.")
        return 0

    _save(fresh)
    print(_render(fresh, 0))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # A banner must never stop a prompt from being answered.
        print(f"PROVENANCE NUMBERS: unavailable ({exc}). "
              "Run `python scripts/dq_check.py` by hand.")
        sys.exit(0)
