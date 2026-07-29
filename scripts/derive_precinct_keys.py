#!/usr/bin/env python3
"""Config-driven, idempotent precinct-keying derivation pass.

prior-art-checked: the guard's hits are all FRONTEND precinct SERVING code
(precinct-service.ts, app/api/precinct/*) — they read v2_precinct_id to match an
address to provisions. This is the inverse: a backend pass that DERIVES and writes
v2_precinct_id onto provision rows from a config rule. No existing backend keying
derivation exists (it was manual, per docs/EXTRACTION_WHY_IT_RECURS...).

WHY THIS EXISTS (docs/EXTRACTION_WHY_IT_RECURS_AND_THE_DURABLE_FIX_2026-07.md):
precinct keys (v2_precinct_id) were applied to rows BY HAND, so every re-extraction
nulled them and the manual work recurred. This makes keying a repeatable DERIVATION
from a written rule per (council, chapter): re-running reproduces the same keys, and
a re-extraction is no longer destructive — you just re-run this pass.

A keyed row is a precinct-layer row, so a derived key also sets v2_dcp_layer='precinct'
(matches how the for-property route filters). Nothing else is touched; provision_text
is never modified.

RULE STRATEGIES
  doc_regex  : capture a group from document_id, format into a template   (Marrickville)
  ref_regex  : capture group(s) from ref_number, format into a template   (Leichhardt C2 / G)
  page_range : map pdf_page to a precinct via [(precinct, lo, hi)] ranges  (Ashfield ch-D — GOING-FORWARD; current hand-patched rows won't all match, that's expected)
  constant   : one precinct_id for every row the selector matches          (Ashfield E2)
  chapter_map: precinct_id from a source_chapter_key -> id map             (KG single-site)

USAGE
  python scripts/derive_precinct_keys.py                     # dry-run ALL rules, report
  python scripts/derive_precinct_keys.py --council ku_ring_gai
  python scripts/derive_precinct_keys.py --validate         # dry-run + assert reproduction of existing keys
  python scripts/derive_precinct_keys.py --council ku_ring_gai --apply   # write (backup first)
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

REPO = Path(__file__).resolve().parent.parent
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

# ── Ashfield chapter-D Part page ranges (source-verified 2026-07-29, matches
#    COUNCIL_CHAPTER_RANGES in dcp_extract_changed.py) ────────────────────────
_ASHFIELD_D_PARTS = [
    ("Part 1", 3, 40), ("Part 2", 41, 57), ("Part 3", 58, 83), ("Part 4", 84, 95),
    ("Part 5", 96, 106), ("Part 6", 107, 155), ("Part 7", 156, 168), ("Part 8", 169, 180),
    ("Part 9", 181, 182), ("Part 10", 183, 187), ("Part 11", 188, 192),
    ("Part 12", 193, 196), ("Part 13", 197, 204),
]

# ── KG Part-14 single-site chapters → their boundary precinct_id (Turramurra
#    14b has sub-precincts T1-T4 and needs a separate sub-split — excluded here) ──
_KG_SINGLE_SITE = {
    "section-b-part-14i-killara-golf-club": "14I",
    "section-b-part-14j-holford-crescent-gordon": "14J",
    "section-b-part-14k-45-47-tennyson-avenue-and-105-eastern-road-turramurra": "14K",
    "section-b-part-14l-62-and-64-66-pacific-highway-roseville": "14L",
    "section-b-part-14n-8a-14-16-buckingham-road-killara": "14N",
    "section-b-part-14o-pymble-golf-club": "14O",
}

# ── The rule set. Each rule: a SELECTOR (which rows) + a STRATEGY (derive key). ──
# `validate`: True means --validate asserts the derived key reproduces the key
# already in the DB (deterministic councils keyed cleanly today). False means the
# rule is going-forward-correct but the current rows were hand-patched differently.
RULES: list[dict] = [
    {
        "name": "marrickville_part9",
        "council": "marrickville",
        "where": r"document_id ~ '__part9_p[0-9]+_'",
        "strategy": {"type": "doc_regex", "pattern": r"__part9_p0*([0-9]+)_", "template": "{0}_"},
        "validate": True,
    },
    {
        "name": "leichhardt_c2_urban_character",
        "council": "leichhardt",
        "where": "document_id = 'Leichhardt_DCP_2013__part_c_s2_urban_character'",
        "strategy": {"type": "ref_regex", "pattern": r"__C2((?:_[0-9]+)+)", "template": "C2{dotted}"},
        "validate": True,
    },
    {
        "name": "ashfield_e2_haberfield",
        "council": "ashfield",
        "where": "document_id = 'Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield'",
        "strategy": {"type": "constant", "precinct_id": "Haberfield"},
        "validate": True,
    },
    {
        "name": "ku_ring_gai_part14_single_site",
        "council": "ku_ring_gai",
        "where": "source_chapter_key = ANY(%(kg_keys)s)",
        "params": {"kg_keys": list(_KG_SINGLE_SITE)},
        "strategy": {"type": "chapter_map", "map": _KG_SINGLE_SITE},
        "validate": False,
    },
    {
        "name": "ashfield_chapter_d_parts",
        "council": "ashfield",
        "where": "document_id = 'Inner_West_Ashfield_DCP_2016__chapter_d_precinct_guidelines'",
        "strategy": {"type": "page_range", "ranges": _ASHFIELD_D_PARTS},
        "validate": False,
    },
]


def _derive(strategy: dict, row: dict) -> str | None:
    """Return the precinct_id this strategy derives for a row, or None."""
    t = strategy["type"]
    if t == "constant":
        return strategy["precinct_id"]
    if t == "chapter_map":
        return strategy["map"].get(row["source_chapter_key"])
    if t == "doc_regex":
        m = re.search(strategy["pattern"], row["document_id"] or "")
        return strategy["template"].format(*m.groups()) if m else None
    if t == "ref_regex":
        m = re.search(strategy["pattern"], row["ref_number"] or "")
        if not m:
            return None
        dotted = "." + ".".join(m.group(1).strip("_").split("_"))
        return strategy["template"].format(dotted=dotted)
    if t == "page_range":
        p = row["pdf_page"]
        if p is None:
            return None
        for pid, lo, hi in strategy["ranges"]:
            if lo <= p <= hi:
                return pid
        return None
    raise ValueError(f"unknown strategy {t}")


def run(council: str | None, apply: bool, validate: bool) -> int:
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
    conn.autocommit = not apply
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '60s'")
    backup_rows: list[tuple] = []
    total_new = total_changed = total_ok = total_none = 0
    validation_failures: list[str] = []

    for rule in RULES:
        if council and rule["council"] != council:
            continue
        # Footgun guard: a bulk `--apply` (no --council) must NOT touch validate:False
        # rules — those are going-forward-correct but disagree with current hand-patched
        # rows (e.g. Ashfield ch-D page-range vs text-location+duplication). Applying them
        # requires an explicit `--council <name>` so it's a deliberate act.
        if apply and not council and not rule["validate"]:
            print(f"  {rule['name']:<34} SKIPPED on bulk --apply (validate:False; pass --council to apply)")
            continue
        params = dict(rule.get("params", {}))
        cur.execute(
            f"""SELECT id, document_id, ref_number, pdf_page, source_chapter_key, v2_precinct_id, v2_dcp_layer
                FROM regulatory_provisions
                WHERE is_current = true AND source_council = %(council)s AND ({rule['where']})""",
            {"council": rule["council"], **params},
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        r_new = r_changed = r_ok = r_none = 0
        for row in rows:
            derived = _derive(rule["strategy"], row)
            current = row["v2_precinct_id"]
            if derived is None:
                r_none += 1
                continue
            if rule["validate"] and current is not None and current != derived:
                validation_failures.append(
                    f"{rule['name']} id={row['id']}: derived {derived!r} != existing {current!r}")
            if current == derived and row["v2_dcp_layer"] == "precinct":
                r_ok += 1
                continue
            if current is None:
                r_new += 1
            else:
                r_changed += 1
            if apply:
                backup_rows.append((row["id"], current or "", derived, row["v2_dcp_layer"] or "", rule["name"]))
                cur.execute(
                    "UPDATE regulatory_provisions SET v2_precinct_id=%s, v2_dcp_layer='precinct' WHERE id=%s",
                    (derived, row["id"]))
        print(f"  {rule['name']:<34} rows={len(rows):<5} new={r_new} changed={r_changed} "
              f"already-ok={r_ok} no-derivation={r_none}")
        total_new += r_new; total_changed += r_changed; total_ok += r_ok; total_none += r_none

    if validate and validation_failures:
        conn.rollback()
        print(f"\nVALIDATION FAILED — {len(validation_failures)} derived keys disagree with existing:")
        for v in validation_failures[:20]:
            print("   ", v)
        conn.close()
        return 1
    if validate:
        print("\nVALIDATION PASSED — every derived key on a validate-rule reproduces the existing key.")

    print(f"\ntotals: new={total_new} changed={total_changed} already-ok={total_ok} no-derivation={total_none}")
    if apply:
        bpath = REPO / "data" / "db_rollback_backups" / f"precinct_keying_derived_{datetime.now(timezone.utc):%Y-%m-%d}.csv"
        bpath.parent.mkdir(parents=True, exist_ok=True)
        with open(bpath, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if f.tell() == 0:
                w.writerow(["id", "precinct_id_before", "precinct_id_after", "layer_before", "rule"])
            w.writerows(backup_rows)
        conn.commit()
        print(f"APPLIED {len(backup_rows)} key updates; backup {bpath}")
    else:
        print("DRY RUN — no writes. Re-run with --apply to commit.")
    conn.close()
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Config-driven idempotent precinct-keying derivation")
    ap.add_argument("--council")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--validate", action="store_true", help="assert derived keys reproduce existing keys")
    args = ap.parse_args()
    if not DATABASE_URL:
        sys.exit("DATABASE_URL not set")
    sys.exit(run(args.council, args.apply, args.validate))


if __name__ == "__main__":
    main()
