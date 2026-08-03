#!/usr/bin/env python3
# prior-art-checked: no existing script extracts commencement/adoption dates
# from the data/dcps PDFs (repo grep for 'came into effect'/'In Force'/
# commencement extractors, 2026-08-03; scripts/backfill_effective_date.py is
# the RETIRED version-label parser and must not be extended — campaign item 3
# explicitly bans it). This reads the documents' own statements verbatim.
"""Extract each DCP's own commencement/amendment statement into dcp_plan_as_at.

Output-grounding campaign item 3, evidence class 2 (``stated_*``). For every
local plan PDF in ``data/dcps/`` mapped below, scan its opening pages for an
explicit dated statement — "In Force 6 May 2022", "came into effect on
22 August 2024", a LIST OF AMENDMENTS "Date in Force" column — and store the
date, its precision, its kind and the VERBATIM line (with file + page) in
``dcp_plan_as_at.stated_*``.

Precision honesty: only explicit dated phrases are parsed. A file whose
statement pattern no longer matches is SKIPPED and reported — never guessed.
The 2026-08-03 survey of all 30 PDFs found statements in exactly the files
mapped below; the other files were scanned in full and carry none (their LGAs
fall back to the portal record or the registry observation).

SAFETY: dry-run by default; ``--apply`` writes stated_* columns only, via
UPDATE-or-INSERT per LGA with predicted counts. No serving table is touched.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from typing import Optional

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DCP_DIR = os.path.join(REPO_ROOT, "data", "dcps")

MONTHS = {
    m.lower(): i
    for i, m in enumerate(
        ["January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"], start=1)
}
_MONTH_RE = "|".join(MONTHS)

# Statement patterns, strongest kind first. 'effective' covers "in force" /
# "came into effect" — the date the plan text operates from; 'adopted' is the
# council resolution date and is only used when nothing stronger exists.
_STATEMENTS: list[tuple[re.Pattern, str]] = [
    (re.compile(rf"came into effect(?:\s+on|:)?\s+(\d{{1,2}})\s+({_MONTH_RE})\s+(\d{{4}})", re.I),
     "effective"),
    (re.compile(rf"in force:?\s+(\d{{1,2}})\s+({_MONTH_RE})\s+(\d{{4}})", re.I),
     "effective"),
    (re.compile(rf"effective:?\s*(\d{{1,2}})\s+({_MONTH_RE})\s+(\d{{4}})", re.I),
     "effective"),
    (re.compile(r"effective:?\s*(\d{1,2})/(\d{1,2})/(\d{2,4})", re.I),
     "effective"),
    (re.compile(rf"adopted(?: by council)?(?:\s+on|:)?\s+(\d{{1,2}})\s+({_MONTH_RE})\s+(\d{{4}})", re.I),
     "adopted"),
]

# file (relative to data/dcps) -> served lga slug. File-identity mapping only.
FILE_TO_SLUG: dict[str, str] = {
    "burwood-dcp.pdf": "burwood",
    "campbelltown-part3-low-medium-density.pdf": "campbelltown",
    "hills-shire-part-b-section2-residential.pdf": "the_hills",
    "northern-beaches-warringah-dcp-2011.pdf": "northern_beaches",
    "strathfield-part-a-dwelling-houses.pdf": "strathfield",
    "fairfield-citywide-dcp-2013.pdf": "fairfield",
    os.path.join("randwick", "volume-1-parts-a-c.pdf"): "randwick",
}
# Parramatta states no whole-plan commencement; its LIST OF AMENDMENTS table
# (page 3) carries per-amendment "Date in Force" values — the latest is the
# plan's most recent stated in-force date.
AMENDMENT_TABLE_FILE = ("parramatta-dcp-2023.pdf", "parramatta")
MAX_SCAN_PAGES = 12


@dataclass
class Stated:
    slug: str
    date_iso: str
    precision: str
    kind: str
    evidence: str


def _to_year(y: int) -> int:
    return y if y >= 100 else 2000 + y


def scan_statement(path: str, rel: str) -> Optional[Stated]:
    import fitz  # PyMuPDF

    slug = FILE_TO_SLUG[rel]
    doc = fitz.open(path)
    try:
        best: Optional[Stated] = None
        for pno in range(min(MAX_SCAN_PAGES, len(doc))):
            for raw_line in doc[pno].get_text("text").splitlines():
                line = " ".join(raw_line.split())
                for pat, kind in _STATEMENTS:
                    m = pat.search(line)
                    if not m:
                        continue
                    g = m.groups()
                    try:
                        if g[1].lower() in MONTHS:
                            d = date(int(g[2]), MONTHS[g[1].lower()], int(g[0]))
                        else:
                            d = date(_to_year(int(g[2])), int(g[1]), int(g[0]))
                    except (ValueError, KeyError):
                        continue
                    hit = Stated(slug, d.isoformat(), "day", kind,
                                 f"{rel} p{pno + 1}: \"{line[:160]}\"")
                    # 'effective' beats 'adopted'; the first statement of the
                    # winning kind stands.
                    if best is None or (best.kind == "adopted" and kind == "effective"):
                        best = hit
        return best
    finally:
        doc.close()


def scan_amendment_table(path: str, rel: str, slug: str) -> Optional[Stated]:
    """Parramatta: take the MAX dd/mm/yyyy on the LIST OF AMENDMENTS page.
    On that layout every listed date is either 'Date Approved' or 'Date in
    Force' and in-force follows approval, so the maximum is the latest stated
    in-force date."""
    import fitz

    doc = fitz.open(path)
    try:
        for pno in range(min(MAX_SCAN_PAGES, len(doc))):
            text = doc[pno].get_text("text")
            if "LIST OF AMENDMENTS" not in text.upper():
                continue
            found: list[tuple[date, str]] = []
            for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", text):
                try:
                    found.append((date(int(m.group(3)), int(m.group(2)),
                                       int(m.group(1))), m.group(0)))
                except ValueError:
                    continue
            if not found:
                return None
            latest, verbatim = max(found)
            return Stated(slug, latest.isoformat(), "day", "amended",
                          f"{rel} p{pno + 1} LIST OF AMENDMENTS: latest Date in "
                          f"Force {verbatim} of {len(found)} listed dates")
        return None
    finally:
        doc.close()


def main() -> int:  # pragma: no cover - CLI entry point
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Write stated_* columns. Default: dry run.")
    ap.add_argument("--dcp-dir", default=DCP_DIR,
                    help="Location of the plan PDFs (data/dcps is git-ignored, "
                         "so a worktree run must point at the main checkout).")
    args = ap.parse_args()

    dcp_dir = args.dcp_dir
    if not os.path.isdir(dcp_dir):
        print(f"ERROR: {dcp_dir} not found — nothing was scanned, which is not "
              f"a pass. Exiting 2.", file=sys.stderr)
        return 2

    results: list[Stated] = []
    skipped: list[str] = []
    for rel in sorted(FILE_TO_SLUG):
        path = os.path.join(dcp_dir, rel)
        if not os.path.isfile(path):
            skipped.append(f"{rel}: file missing")
            continue
        hit = scan_statement(path, rel)
        if hit:
            results.append(hit)
        else:
            skipped.append(f"{rel}: mapped but no statement matched — file "
                           f"changed since the 2026-08-03 survey?")

    rel, slug = AMENDMENT_TABLE_FILE
    path = os.path.join(dcp_dir, rel)
    if os.path.isfile(path):
        hit = scan_amendment_table(path, rel, slug)
        if hit:
            results.append(hit)
        else:
            skipped.append(f"{rel}: LIST OF AMENDMENTS not found/undated")
    else:
        skipped.append(f"{rel}: file missing")

    print(f"stated dates extracted: {len(results)}")
    for r in results:
        print(f"  {r.slug:18s} {r.date_iso} ({r.precision}, {r.kind})  <- {r.evidence}")
    for s in skipped:
        print(f"  SKIPPED {s}")

    if not args.apply:
        print(f"\nDRY RUN — nothing written. --apply would upsert "
              f"{len(results)} rows' stated_* columns.")
        return 0

    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set — nothing written. Exiting 2.",
              file=sys.stderr)
        return 2
    # prior-art-checked: connection shape follows the house repair-script
    # pattern (repair_canada_bay_rear_setback.py) — DATABASE_URL + 30s timeout.
    import psycopg2

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")
    print(f"\npredicted writes: {len(results)} upserts (stated_* columns only)")
    written = 0
    try:
        for r in results:
            cur.execute(
                """
                INSERT INTO dcp_plan_as_at
                    (lga, stated_date, stated_date_precision, stated_date_kind,
                     stated_evidence, updated_at)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (lga) DO UPDATE SET
                    stated_date = EXCLUDED.stated_date,
                    stated_date_precision = EXCLUDED.stated_date_precision,
                    stated_date_kind = EXCLUDED.stated_date_kind,
                    stated_evidence = EXCLUDED.stated_evidence,
                    updated_at = now()
                """,
                (r.slug, r.date_iso, r.precision, r.kind, r.evidence),
            )
            written += cur.rowcount
        conn.commit()
        print(f"wrote {written} rows (predicted {len(results)})")
        cur.execute("SELECT COUNT(*), COUNT(stated_date) FROM dcp_plan_as_at")
        total, with_stated = cur.fetchone()
        print(f"post-write verify: dcp_plan_as_at rows={total}, stated_date set={with_stated}")
        return 0 if written == len(results) else 2
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(f"ERROR (rolled back): {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
