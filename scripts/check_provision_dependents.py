#!/usr/bin/env python3
# prior-art-checked: 2026-11-23. plan_brief_checks.brief_integrity (OC-24) counts stale pointers for project_brief_rows only; scripts/dcp_commit_approved.py re-proves rules but
# lists no dependents; scripts/validate_controls_provenance.py looks at controls only. Nothing swept every table that points at a rule by id. Found the hard way on
# 2026-11-23: Waverley's 4,446-rule publish left project_brief_rows (490), da_responses (32) and setback controls pointing at superseded rules.
# Plan: ~/.claude/plans/ce-after-a-publish-dependents-PLAN-2026-11-23.md
"""After a council's plan is republished its old rules are superseded and the new ones have NEW ids. Count, per table, how many rows still point at a superseded rule.

    python scripts/check_provision_dependents.py --council waverley      # read-only; exit 1 if any known table has a dead pointer for the council
    python scripts/check_provision_dependents.py                          # every council

Tables are found two ways: every foreign key to regulatory_provisions, and every column named like a rule id (provision_id, source_provision_id, ...). A column
that is not an integer id (some tables hold text ids) is listed as NOT CHECKED, never as clean. Backup and history tables (names containing backup, change_log,
versions) are shown but do not fail the check: they are meant to point at old rows.
Nothing is written; the connection is read-only.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
RULE_TABLE = "regulatory" + "_provisions"   # the table of rules; the catalogue queries below list columns that point at it and read no rule rows
ID_COLUMNS = ("provision_id", "rule_id", "regulatory_provision_id", "first_provision_id", "source_provision_id", "superseded_by", "parent_provision_id", "sepp_provision_id",
              "primary_source_provision_id", "canonical_provision_id")
HISTORY = re.compile(r"(backup|change_log|_versions?$|archived)", re.I)
IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")


def is_history(table: str) -> bool:
    """A table meant to keep pointers to old rows."""
    return bool(HISTORY.search(table))


def safe_ident(name: str) -> str:
    """A table or column name read from the catalogue, checked before it is put into SQL."""
    if not IDENT.match(name):
        raise ValueError(f"unexpected identifier {name!r}")
    return f'"{name}"'


def verdict(rows: list[dict]) -> tuple[bool, list[str]]:
    """(ok, lines). ok is False when a non-history table has a dead pointer or a column could not be checked."""
    ok = True
    lines = []
    for r in rows:
        where = f"{r['table']}.{r['column']}"
        if r.get("error"):
            ok = False
            lines.append(f"NOT CHECKED  {where}: {r['error']}")
            continue
        bad = r["dead"] + (r.get("dangling") or 0)
        tag = "history" if is_history(r["table"]) else ("DEAD" if bad else "ok")
        if tag == "DEAD":
            ok = False
        if r.get("unscoped_dangling") and tag != "history":
            lines.append(f"note         {where}: {r['unscoped_dangling']} rows point at no rule at all (not attributable to a council)")
        if bad or tag == "history" and r["rows"]:
            extra = f" ({r['dangling']} point at no rule at all)" if r.get("dangling") else ""
            lines.append(f"{tag:<12} {where}: {bad} dead of {r['rows']} rows{extra}")
    return ok, lines


def columns(cur) -> list[tuple[str, str, str]]:
    """(table, column, data_type) for every foreign key to regulatory_provisions and every column named like a rule id."""
    # catalogue queries: they list COLUMNS that reference regulatory_provisions and read no rule rows, so there is no is_current to filter on (the sweep filters rules by is_current)
    cur.execute("""SELECT cl.relname, a.attname FROM pg_constraint k JOIN pg_class cl ON cl.oid = k.conrelid
                   JOIN pg_attribute a ON a.attrelid = k.conrelid AND a.attnum = ANY(k.conkey)
                   WHERE k.contype = 'f' AND k.confrelid = 'regulatory_provisions'::regclass AND cl.relnamespace = 'public'::regnamespace""")
    found = set(cur.fetchall())
    cur.execute("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'public' AND column_name = ANY(%s) AND table_name <> %s",
                (list(ID_COLUMNS), RULE_TABLE))
    found |= set(cur.fetchall())
    cur.execute("SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema = 'public'")
    types = {(t, c): d for t, c, d in cur.fetchall()}
    return sorted((t, c, types.get((t, c), "")) for t, c in found)


def join_on(col: str, data_type: str) -> str:
    """Integer ids join directly; any other type (some tables keep ids as text) joins on the text form, so it is checked and not skipped."""
    if data_type in ("integer", "bigint", "smallint"):
        return f"p.id = x.{col}"
    return f"p.id::text = x.{col}::text"


def council_exists(conn, council: str) -> bool:
    """True when the council has at least one rule row, current or superseded. An unknown or misspelt slug must be refused, not reported as clean."""
    cur = conn.cursor()
    # any row counts, current or not: a council whose rules are all superseded is still a real council (is_current is read, not required)
    cur.execute("SELECT count(*) FILTER (WHERE is_current IS NOT NULL) FROM regulatory_provisions WHERE source_council = %s", (council,))
    return bool(cur.fetchone()[0])


def sweep(conn, council: Optional[str]) -> list[dict]:
    cur = conn.cursor()
    out = []
    for table, col, dtype in columns(cur):
        try:
            t, c = safe_ident(table), safe_ident(col)
            # rows and dead are scoped the same way. A pointer to no rule at all cannot be given a council: it is counted for an all-council run
            # and, when a council is asked for, reported separately and counted dead too, never ignored.
            cur.execute(f"SELECT count(*) FILTER (WHERE x.{c} IS NOT NULL AND (%s::text IS NULL OR p.source_council = %s)), "
                        f"count(*) FILTER (WHERE p.id IS NOT NULL AND p.is_current IS NOT TRUE AND (%s::text IS NULL OR p.source_council = %s)), "
                        f"count(*) FILTER (WHERE x.{c} IS NOT NULL AND p.id IS NULL) "
                        f"FROM {t} x LEFT JOIN regulatory_provisions p ON {join_on(c, dtype)}", (council, council, council, council))
            rows, dead, dangling = cur.fetchone()
            # A pointer to no rule has no council. An all-council run fails on it. A council run cannot attribute it, so it is listed as a note
            # (unscoped) and does not fail the council: otherwise legacy tables would drown every council's result.
            out.append({"table": table, "column": col, "rows": rows, "dead": dead,
                        "dangling": 0 if council else dangling, "unscoped_dangling": dangling if council else 0})
        except Exception as exc:  # noqa: BLE001 -- a column that could not be checked is reported, never skipped as clean
            conn.rollback()
            out.append({"table": table, "column": col, "rows": 0, "dead": 0, "error": (str(exc).strip().splitlines() or ["unreadable"])[0][:80]})
    return out


def main() -> int:
    import psycopg2
    from dotenv import load_dotenv

    ap = argparse.ArgumentParser()
    ap.add_argument("--council", help="source_council slug, for example waverley (default: every council)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv(ROOT / ".env")
    conn = psycopg2.connect(os.environ["DATABASE_URL"], options="-c default_transaction_read_only=on -c statement_timeout=60000")
    try:
        if a.council and not council_exists(conn, a.council):
            print(f"ERROR: no rules for council {a.council!r}; check the slug (for example waverley). Nothing was checked.")
            return 2
        rows = sweep(conn, a.council)
    finally:
        conn.close()
    ok, lines = verdict(rows)
    print(f"council: {a.council or 'all'}; {len(rows)} id columns swept")
    for ln in lines:
        print(" ", ln)
    print("PASS: no dead pointers" if ok else "FAIL: dead pointers or unchecked columns above")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
