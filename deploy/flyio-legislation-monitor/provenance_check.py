#!/usr/bin/env python3
"""Weekly provenance check: every served rule with a quote traces to its clause.

prior-art-checked: reuse not viable because legislation_monitor.py checks an
instrument's VERSION date, not that a stored rule's words are in the clause its
link names; scripts/dq_check.py probes do not fetch the law. This is the single
implementation: tests/test_secondary_dwelling_provenance_live.py imports it, and
the Fly app runs it weekly after the monitor (deploy/flyio-legislation-monitor/
run_loop.sh), from the IP legislation.nsw.gov.au accepts.

For every housing_sepp_standards row that carries a source_quote:
  1. its legislation_url is legislation.nsw.gov.au and names a clause anchor;
  2. that anchor exists on the current page;
  3. the last part of the quote (the part carrying the rule) is word for word
     inside that clause; earlier parts (lead-in, definitions) are in the law;
  4. secondary-dwelling path rules also pass validate_rules (number and band
     limits are in the quote; bands tile; zones are in the quote).

Exit 0 only when every row traces. Any break, fetch failure or empty result
exits 1 and (unless --dry-run) sends a Telegram alert naming each rule. Nothing
is written to the database.

Usage:
    python scripts/provenance_check.py            # check + alert on failure
    python scripts/provenance_check.py --dry-run  # check, print, no alert
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from services.secondary_dwelling_paths import validate_rules
except ImportError:  # Fly container: sibling module
    from secondary_dwelling_paths import validate_rules  # type: ignore

OFFICIAL_PREFIX = "https://legislation.nsw.gov.au/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "Chrome/128 Safari/537.36"}
PAUSE_BETWEEN_PAGES_S = 5  # politeness between instrument pages, as the monitor does


def norm(text: str) -> str:
    """Lowercase alphanumerics only: words and numbers must match exactly."""
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def clause_text(page: str, anchor: str) -> str:
    """Visible text of one anchored clause and its sub-clauses. Raises KeyError
    when the anchor is not on the page."""
    anchors = [(m.start(), m.group(1)) for m in re.finditer(r'id="((?:sec|sch|pt)\.[^"]+)"', page)]
    ids = [a for _, a in anchors]
    if anchor not in ids:
        raise KeyError(f"anchor #{anchor} not found on the current page")
    k = ids.index(anchor)
    start = page.find(">", anchors[k][0]) + 1  # noqa: bracket-access — k from index()
    end = len(page)
    for pos, a in anchors[k + 1:]:
        if not a.startswith(anchor + "-"):
            end = page.rfind("<", 0, pos)
            break
    return html.unescape(re.sub(r"<[^>]+>", " ", page[start:end]))


def trace_row(row: dict, page: str) -> list[str]:
    """Problems for one row against its fetched page; [] when it traces."""
    st = row.get("standard_type") or f"id {row.get('id')}"
    url = (row.get("legislation_url") or "").strip()
    base, _, anchor = url.partition("#")
    if not base.startswith(OFFICIAL_PREFIX) or not anchor or re.search(r"\s", url):
        return [f"{st}: link is not an anchored legislation.nsw.gov.au URL"]
    parts = [p for p in (row.get("source_quote") or "").split("...") if norm(p)]
    if not parts:
        return [f"{st}: no quote"]
    try:
        clause = norm(clause_text(page, anchor))
    except KeyError as e:
        return [f"{st}: {e.args[0] if e.args else e}"]
    problems = []
    if norm(parts[-1]) not in clause:
        problems.append(f"{st}: quote not inside clause #{anchor}")
    whole = norm(html.unescape(re.sub(r"<[^>]+>", " ", page)))
    for p in parts[:-1]:
        if norm(p) not in whole:
            problems.append(f"{st}: quote part not in the law in force: {p.strip()[:50]}")
    return problems


def served_rows(conn) -> list[dict]:
    cur = conn.cursor()
    cur.execute(
        "SELECT id, development_type, standard_type, approval_pathway, numeric_value, unit, "
        "lot_area_min_m2, lot_area_min_inclusive, lot_area_max_m2, applicable_zones, "
        "source_clause, legislation_url, source_quote, stale_since, stale_reason "
        "FROM housing_sepp_standards WHERE source_quote IS NOT NULL"
    )
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    return rows


def fetch_page(url: str) -> str:
    import requests

    r = requests.get(url, headers=HEADERS, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} for {url}")
    return r.text


def run(rows: list[dict], fetch=fetch_page, pause_s: float = PAUSE_BETWEEN_PAGES_S) -> tuple[int, list[str]]:
    """(rules traced, problems). Pure apart from `fetch`, so it is testable."""
    if not rows:
        return 0, ["no rules with a quote were found to check"]
    problems: list[str] = []
    path_rows = [r for r in rows if r.get("development_type") == "secondary_dwelling"
                 and r.get("approval_pathway")]
    # Always validated: with no path rules at all, validate_rules names each
    # missing rule, so deleting them cannot pass behind other rules that trace.
    outcome = validate_rules(path_rows)
    problems += [f"validation: {f}" for f in outcome.failures]
    pages: dict = {}
    # Keyed by row, not standard_type: 53 rows share 28 types, and a type key
    # made a page nobody could fetch read "25/53 traced" (2026-10-09).
    broken: set = set()
    for i, r in enumerate(rows):
        base = (r.get("legislation_url") or "").partition("#")[0]
        if base.startswith(OFFICIAL_PREFIX) and base not in pages:
            if pages:
                time.sleep(pause_s)
            try:
                pages[base] = fetch(base)
            except Exception as e:  # noqa: BLE001 — a failed fetch is a named problem
                pages[base] = None
                problems.append(f"fetch failed for {base}: {e}")
        if base.startswith(OFFICIAL_PREFIX) and pages.get(base) is None:
            broken.add(i)
            continue
        row_problems = trace_row(r, pages.get(base) or "")
        if row_problems:
            broken.add(i)
            problems += row_problems
    return len(rows) - len(broken), problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Trace served rules to their clause in the law in force")
    parser.add_argument("--dry-run", action="store_true", help="print only; no Telegram alert")
    args = parser.parse_args()
    import psycopg2
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    rows: list = []
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"],
                                options="-c statement_timeout=30000 -c default_transaction_read_only=on")
        try:
            rows = served_rows(conn)
        finally:
            conn.close()
        traced, problems = run(rows)
    except Exception as e:  # noqa: BLE001 — the check itself failing is reported, never silent
        traced, problems = 0, [f"provenance check could not run: {e}"]
    print(f"provenance: {traced}/{len(rows)} rules traced to their clause in the law in force")
    for p in problems:
        print(f"  BROKEN: {p}")
    if problems and not args.dry_run:
        try:
            from legislation_monitor import send_telegram
        except ImportError:
            from scripts.legislation_monitor import send_telegram  # type: ignore
        try:
            delivered = send_telegram("Provenance check FAILED\n"
                                      f"{traced}/{len(rows)} rules traced\n"
                                      + "\n".join(f"  {p}" for p in problems[:15]))
        except Exception as e:  # noqa: BLE001 — undelivered alert is its own exit status
            print(f"  ALERT NOT DELIVERED: {e}")
            return 2
        if not delivered:
            print("  ALERT NOT DELIVERED")
            return 2
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
