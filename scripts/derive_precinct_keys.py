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

FINGERPRINT GATE (page_range rules): a page->precinct map only holds while the source
PDF's pagination is unchanged. pdf_page is the physical page a heading sits on, so a
byte-identical PDF reproduces the ranges exactly; a re-paginated/replaced amendment
would shift pages and silently mis-key. Rules carrying a `fingerprint` (max_page +
min_coverage) re-check the structure on every run and FAIL CLOSED on mismatch — keys
are left un-written so rows serve council-wide + precinct_warning (the safe failure)
instead of confident wrong-precinct keys. Regenerate the ranges, then re-run.

RULE STRATEGIES
  doc_regex  : capture a group from document_id, format into a template   (Marrickville)
  ref_regex  : capture group(s) from ref_number, format into a template   (Leichhardt C2 / G)
  page_range : map pdf_page to a precinct via [(precinct, lo, hi)] ranges  (City of Sydney 2/5/6 — reproduces exactly; Ashfield ch-D — going-forward, current hand-patched rows won't all match)
  text_heading: the precinct number in the provision's own leading markdown heading, trimmed to `components` (CONTENT anchor — survives re-pagination; the durable default when refs are garbled but headings are clean)
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
import json
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

# ── City of Sydney sections 2/5/6: page ranges derived 2026-07-29 directly from
#    the existing keyed rows (min..max pdf_page per precinct, gaps folded forward
#    so ranges are contiguous and non-overlapping). CoS refs are garbled (only
#    101/152/128 encode the key) but pdf_page is clean: these ranges reproduce all
#    462 keys exactly, so the CoS rules are validate:True. Sidecar JSON keeps the
#    159 ranges out of the rule body; regenerate with scripts/cos_build_ranges
#    logic if the CoS DCP is re-paginated. ──────────────────────────────────────
with open(REPO / "data" / "cos_precinct_page_ranges.json", encoding="utf-8") as _f:
    _COS_RANGES: dict = json.load(_f)


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
    {   # Waverley Part E: the extraction already sets v2_dcp_part='E1'..'E7';
        # keying = copy that into v2_precinct_id. Added 2026-07-29 after the daily
        # re-extraction cron superseded the 07-28 keyed generation and lost the keys
        # (the exact churn this pass fixes — Waverley now has a rule so it self-heals).
        "name": "waverley_part_e",
        "council": "waverley",
        "where": r"v2_dcp_part ~ '^E[0-9]'",
        "strategy": {"type": "column_copy", "column": "v2_dcp_part", "match": r"^E[0-9]$"},
        "validate": False,
    },
    # City of Sydney (biggest keyed council: 462 rows). CoS has no precinct
    # boundaries yet, so these keys drive the for-property EXCLUSION + precinct_warning
    # (task 1, 2026-07-29). Keyed from page footers/refs by hand originally; these
    # page_range rules reproduce all 462 exactly, so re-extraction now self-heals
    # instead of un-keying CoS (it was EXPOSED per audit_precinct_keying_coverage.py).
    {
        "name": "city_of_sydney_section_2_locality",
        "council": "city_of_sydney",
        "where": "source_chapter_key = 'section-2-locality-statements'",
        "strategy": {"type": "page_range", "ranges": _COS_RANGES["Sydney_DCP_2012__section_2_locality_statements"]},
        "validate": True,
        "fingerprint": {"max_page": 169, "min_coverage": 0.95},
    },
    {
        "name": "city_of_sydney_section_5_areas",
        "council": "city_of_sydney",
        "where": "source_chapter_key = 'section-5-specific-areas'",
        "strategy": {"type": "page_range", "ranges": _COS_RANGES["Sydney_DCP_2012__section_5_specific_areas"]},
        "validate": True,
        "fingerprint": {"max_page": 366, "min_coverage": 0.95},
    },
    {
        "name": "city_of_sydney_section_6_sites",
        "council": "city_of_sydney",
        "where": "source_chapter_key = 'section-6-specific-sites'",
        "strategy": {"type": "page_range", "ranges": _COS_RANGES["Sydney_DCP_2012__section_6_specific_sites"]},
        "validate": True,
        "fingerprint": {"max_page": 265, "min_coverage": 0.95},
    },
    # Parramatta (532 rows, hand-keyed by a parallel session 2026-07-29 with no
    # reproducible rule — audit_precinct_keying_coverage.py flags it EXPOSED). Its
    # refs carry the precinct number at mixed depth per top-level part; ref_components
    # reproduces 525/532 exactly (validated against every live keyed row), the other
    # 7 are chunk-counter/zone-prefixed refs with no derivable structure and correctly
    # return None (matches the other session's note of ~8 page-evidence exceptions).
    {
        "name": "parramatta_ref_components",
        "council": "parramatta",
        "where": "document_id = 'Parramatta_DCP_2023_(Amendment_4)__parramatta_dcp_2023_full'",
        "strategy": {
            "type": "ref_components",
            "components_map": {"7": 3, "8": 3, "9.10": 3, "9": 1},
            "max_top_digits": 1,
        },
        "validate": True,
    },
]


def _derive(strategy: dict, row: dict) -> str | None:
    """Return the precinct_id this strategy derives for a row, or None."""
    t = strategy["type"]
    if t == "constant":
        return strategy["precinct_id"]
    if t == "chapter_map":
        return strategy["map"].get(row["source_chapter_key"])
    if t == "column_copy":
        val = row.get(strategy["column"])
        return val if val and re.search(strategy["match"], val) else None
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
    if t == "ref_components":
        # Content anchor for refs that carry a dotted/underscored precinct number in
        # their FINAL "__"-delimited segment, at MIXED depth per top-level part
        # (Parramatta: Part 7/8 = 3 components; Part 9 = 1, except its 9.10 sub-group
        # = 3). `components_map` picks the depth by the longest matching dotted prefix
        # — but only if the ref actually HAS that many components (a bare "9_10"
        # section-overview heading has 2, not 3, so it correctly falls back to the
        # shorter "9" prefix instead of deriving the invalid id "9.10").
        # `max_top_digits` rejects bare chunk-counter refs (e.g. tail "387") that
        # would otherwise be silently misread as a real (wrong) precinct number.
        tail = (row.get("ref_number") or "").split("__")[-1]
        m = re.match(r"([0-9]+[A-Z]?)((?:_[0-9]+)*)", tail)
        if not m:
            return None
        head, rest = m.group(1), m.group(2)
        dm = re.match(r"([0-9]+)([A-Z]?)", head)
        top_digits, letter = dm.group(1), dm.group(2)
        if len(top_digits) > strategy.get("max_top_digits", 1):
            return None
        # The map ALSO decides eligibility, not just depth: a top-level part with no
        # matching key (e.g. Parramatta Part 3 "Residential Development" — a general
        # topic chapter, not a precinct) must derive None, never fall back to the raw
        # untrimmed number — otherwise a topic chapter's own heading number ("3",
        # "2.3") would be mistaken for a precinct id.
        comps = [top_digits] + [c for c in rest.split("_") if c]
        joined = ".".join(comps)
        cmap = strategy.get("components_map") or {}
        match = None
        for key in sorted(cmap, key=len, reverse=True):
            depth = cmap[key]
            if (joined == key or joined.startswith(key + ".")) and len(comps) >= depth:
                match = depth
                break
        if match is None:
            return None
        # The letter belongs to the TOP-LEVEL part (e.g. Part "9B"), so it must attach
        # to the first kept component, not be appended after the last one — otherwise
        # a hypothetical letter-suffixed part with depth>1 (none exist in Parramatta's
        # corpus today, but the map is general) would derive "7.10.1B" instead of the
        # correct "7B.10.1".
        trimmed = comps[:match]
        return trimmed[0] + letter + ("." + ".".join(trimmed[1:]) if len(trimmed) > 1 else "")
    if t == "text_heading":
        # Content anchor: the precinct number in the provision's own leading markdown
        # heading (e.g. "# 5.1.1.4 ..."). Travels WITH the text, so it survives
        # re-pagination — unlike page_range. `components` trims the dotted number to the
        # precinct granularity (2 -> "5.1" area; 3 -> "6.1.4" site; None -> full "2.1.1").
        m = re.match(r"\s*#\s*([0-9]+(?:\.[0-9]+)*)", row.get("provision_text") or "")
        if not m:
            return None
        num = m.group(1)
        n = strategy.get("components")
        if n is None:
            return num
        parts = num.split(".")   # regex guarantees ≥1 numeric part; slice is empty-safe
        return ".".join(parts[:n])
    raise ValueError(f"unknown strategy {t}")


def _fingerprint_reasons(fp: dict, pdf_pages: list, n_none: int, n_total: int) -> list:
    """Why a page_range rule's structural fingerprint fails (empty list = passes).

    A page->precinct map is only valid while the source PDF's pagination is
    unchanged. Two cheap signals catch a re-paginated / replaced PDF before the
    rule can mis-key: the last keyed page must still match, and almost every row
    must still fall inside a span (coverage). Pure so it can be unit-tested."""
    reasons: list = []
    actual_max = max(pdf_pages) if pdf_pages else None
    coverage = (n_total - n_none) / n_total if n_total else 0.0
    if actual_max != fp["max_page"]:
        reasons.append(f"last page {actual_max} != expected {fp['max_page']} (PDF re-paginated?)")
    if coverage < fp["min_coverage"]:
        reasons.append(f"coverage {coverage:.1%} < {fp['min_coverage']:.0%} (rows fell outside every span)")
    return reasons


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
            f"""SELECT id, document_id, ref_number, pdf_page, source_chapter_key, v2_precinct_id, v2_dcp_layer, v2_dcp_part, provision_text
                FROM regulatory_provisions
                WHERE is_current = true AND source_council = %(council)s AND ({rule['where']})""",
            {"council": rule["council"], **params},
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        r_new = r_changed = r_ok = r_none = 0
        pending: list[tuple] = []  # (row_id, current, derived, layer) — buffered so the
        # fingerprint gate below can decide to write them or fail closed as a batch.
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
            pending.append((row["id"], current, derived, row["v2_dcp_layer"]))

        # ── Fingerprint gate (page_range rules over a re-extractable PDF) ──────────
        # A page->precinct map only holds while the source PDF's pagination is
        # unchanged. pdf_page is the physical page a section's heading sits on, so a
        # byte-identical PDF reproduces it exactly — but a new amendment / re-pagination
        # shifts every page and would make these ranges key the WRONG area. So re-check
        # the structure on EVERY run: the last keyed page must still match, and the vast
        # majority of rows must still fall inside a span. On mismatch FAIL CLOSED — skip
        # the writes, leaving rows un-keyed (council-wide + precinct_warning, the safe
        # failure) rather than writing confident wrong-precinct keys. Regenerate the
        # ranges (scripts/cos_build_ranges) against the new PDF, then re-run.
        fp = rule.get("fingerprint")
        fp_ok = True
        if fp and rows:
            pages = [r["pdf_page"] for r in rows if r["pdf_page"] is not None]
            reasons = _fingerprint_reasons(fp, pages, r_none, len(rows))
            if reasons:
                fp_ok = False
                msg = f"{rule['name']} FINGERPRINT MISMATCH — " + "; ".join(reasons)
                print(f"  ⚠ {msg}")
                print(f"     -> keys NOT written (fail-closed); rows stay council-wide + warned. "
                      f"Regenerate ranges against the new PDF, then re-run.")
                if validate:
                    validation_failures.append(msg)

        if apply and fp_ok:
            for row_id, current, derived, layer in pending:
                backup_rows.append((row_id, current or "", derived, layer or "", rule["name"]))
                cur.execute(
                    "UPDATE regulatory_provisions SET v2_precinct_id=%s, v2_dcp_layer='precinct' WHERE id=%s",
                    (derived, row_id))
        gate = "" if fp_ok else "  [FAIL-CLOSED: not written]"
        print(f"  {rule['name']:<34} rows={len(rows):<5} new={r_new} changed={r_changed} "
              f"already-ok={r_ok} no-derivation={r_none}{gate}")
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
