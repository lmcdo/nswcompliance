#!/usr/bin/env python3
"""DQ-142: turn verified DCP control findings into one migration.

prior-art-checked: reuse not viable because the insert_<council>_*.py scripts
each hard-code one council's rows; this reads a reviewed spec covering many
councils and refuses any row whose quote is not in the stored DCP text.

Input: data/dq142_controls_2026-10-10.json -- a list of findings, each
  {lga, dev_type, control_type, value_min|null, unit, condition|null,
   quotes: [[provision_id, "verbatim fragment"], ...], pdf_page, section_ref}
A control with no fixed figure (a formula, or 'match the neighbours') has
value_min null and a condition beginning 'NO FIGURE:'.

Every fragment must occur (whitespace-normalised) in the named current
regulatory_provisions row, and value_min must appear in one of the fragments,
or the row is refused and named. Nothing is written to the database: the output
is a migration file to dry-run and apply with scripts/apply_migration_dry_run.py.

    python scripts/dq142_build_controls_migration.py SPEC.json OUT.sql [--allow-refused]
"""
from __future__ import annotations

import json
import os
import re
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"))
load_dotenv()

CAP_TYPES = {"max_site_coverage", "landscaping_min", "deep_soil_min"}


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").replace(" ", " ")).strip().lower()


def shown(v: float) -> str:
    if v is None:
        raise ValueError("shown() needs a figure; a NO FIGURE control has none")
    return str(int(v)) if float(v) == int(v) else f"{v:g}"


def value_in_quotes(v: float, unit: str | None, frags: list[str]) -> bool:
    """True if figure v appears as a whole number in the quotes (metres also as mm)."""
    joined = " ".join(norm(f) for f in frags)
    # Not inside a larger number: 5 must not match "5.5m" or "15%".
    pat = rf"(?<![\d.]){re.escape(shown(v))}(?![\d]|\.\d)(?:\s?(?:m|metres|mm|%)|\b)"
    mm = rf"(?<![\d.]){re.escape(shown(v * 1000))}\s?mm" if unit == "m" else None
    return bool(re.search(pat, joined) or (mm and re.search(mm, joined)))


SECOND_LIMB = re.compile(r"whichever is (?:the )?greater|on the other|average of|prevailing|designated road|per dwelling|of the lot width")


def single_figure_rule(condition: str | None, frags: list[str]) -> bool:
    """False if the rule's figure is only one limb of a larger rule.

    The buildable-area sum uses value_min and deducts it on both sides, so a
    greater-of rule, a neighbour average, or a different figure for each side
    stored as its floor overstates the footprint (cross-review, 093).
    """
    return not SECOND_LIMB.search(norm(" ".join([condition or ""] + frags)))


def sq(s) -> str:
    return "NULL" if s is None else "'" + str(s).replace("'", "''") + "'"


def main(spec_path: str, out_path: str) -> int:
    spec = json.load(open(spec_path, encoding="utf-8"))
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    rows, refused = [], []
    for f in spec:
        tag = f"{f['lga']}/{f['dev_type']}/{f['control_type']}"
        texts, chapters = {}, []
        for pid, _ in f["quotes"]:
            cur.execute("SELECT provision_text, source_chapter_key FROM regulatory_provisions "
                        "WHERE id = %s AND is_current", (pid,))
            r = cur.fetchone()
            texts[pid] = norm(r[0]) if r else None
            chapters.append(r[1] if r else None)
        missing = [frag for pid, frag in f["quotes"] if not texts[pid] or norm(frag) not in texts[pid]]
        if missing:
            refused.append(f"{tag}: quote not in stored text: {missing[0][:80]!r}")
            continue
        v = f.get("value_min")
        if v is None and not (f.get("condition") or "").startswith("NO FIGURE:"):
            refused.append(f"{tag}: no value and no 'NO FIGURE:' condition")
            continue
        if v is not None and not single_figure_rule(f.get("condition"), [frag for _, frag in f["quotes"]]):
            refused.append(f"{tag}: rule has a second limb (greater-of / per-side); store as NO FIGURE")
            continue
        if v is not None and not value_in_quotes(v, f.get("unit"), [frag for _, frag in f["quotes"]]):
            refused.append(f"{tag}: value {shown(v)} not in its quote")
            continue
        # The chapter is the one the quote comes from (cross-review: taking the
        # council's most common chapter labelled Woollahra setbacks as parking).
        chapter = chapters[0]
        cur.execute(
            "SELECT source_chapter_key, dcp_version, applicability, count(*) FROM dcp_setback_controls "
            "WHERE lga = %s AND source_chapter_key = %s AND is_current GROUP BY 1, 2, 3 "
            "ORDER BY (bool_or(dev_type = %s)) DESC, count(*) DESC LIMIT 1", (f["lga"], chapter, f["dev_type"]))
        sib = cur.fetchone()
        if not chapter or not sib:
            refused.append(f"{tag}: no existing rows in the quoted chapter {chapter!r} to take a version from")
            continue
        cur.execute(
            "SELECT 1 FROM dcp_setback_controls WHERE lga = %s AND dev_type = %s AND control_type = %s "
            "AND is_current AND NOT needs_review AND (COALESCE(value_min, value_max) IS NOT NULL "
            "OR condition LIKE 'NO FIGURE:%%')", (f["lga"], f["dev_type"], f["control_type"]))
        if cur.fetchone():
            refused.append(f"{tag}: already has a decided row; not duplicating")
            continue
        source_text = " ... ".join(frag for _, frag in f["quotes"])
        rows.append(
            f"  ({sq(f['lga'])}, {sq(f['dev_type'])}, {sq(f['control_type'])}, "
            f"{'NULL' if v is None else shown(v)}, NULL, {sq(f.get('unit'))}, {sq(f.get('condition'))}, "
            f"{sq(sib[2])}, {sq(source_text)}, {sq(f['section_ref'])}, {sq(sib[1])}, TRUE, 'manual_curation', "
            f"{sq(sib[0])}, {int(f['pdf_page']) if f.get('pdf_page') else 'NULL'}, 'unjudged', FALSE)")
    conn.close()
    for r in refused:
        print("REFUSED", r)
    print(f"{len(rows)} row(s) verified, {len(refused)} refused")
    if not rows:
        return 1
    if refused and "--allow-refused" not in sys.argv:
        # A refused finding is a data question, not noise: writing the rest
        # silently would ship a partial repair that looks complete (cross-review).
        print("refusing to write a partial migration; fix the findings or pass --allow-refused")
        return 1
    values = ",\n".join(rows)
    sql = f"""-- DQ-142: building-area controls quoted from stored DCP text ({len(rows)} rows).
-- Generated by scripts/dq142_build_controls_migration.py from {os.path.basename(spec_path)}:
-- every quote was found verbatim in its named, current stored provision and
-- every figure inside its quote before this file was written. Controls with no
-- fixed figure (a formula, or 'match the neighbours') store the DCP's words with
-- condition 'NO FIGURE: ...'. Where a rule rises with storeys or site width the
-- MINIMUM is stored and the rest is in condition, as existing rows do; the
-- buildable-area arithmetic is an upper bound and the minimum keeps it one.
-- VERIFY: python scripts/dq_probe_live.py --id DQ-142

BEGIN;

INSERT INTO dcp_setback_controls
  (lga, dev_type, control_type, value_min, value_max, unit, condition, applicability,
   source_text, section_ref, dcp_version, is_current, extraction_method, source_chapter_key,
   pdf_page, citation_status, needs_review)
VALUES
{values};

COMMIT;
"""
    open(out_path, "w", encoding="utf-8", newline="\n").write(sql)
    print("written", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
