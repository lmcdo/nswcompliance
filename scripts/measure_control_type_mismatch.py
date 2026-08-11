#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no committed script measures
# control_type-vs-quote disagreement. scripts/validate_control_source_values.py
# asks "is this NUMBER in its own quote"; this asks "is this the right KIND of
# control", which that checker structurally cannot see (camden 692 would have
# passed it if its quote had contained '4m'). scripts/validate_dcp_setbacks.py's
# FOREIGN signal is the nearest prior art and is the seed of these patterns, but
# it covers only the ~280 setback rows and has the v1 blind spot fixed here.
"""DQ-40 detector v2 + MISSING_PRIMARY analysis. READ ONLY, advisory, exit 0.

WHAT IT MEASURES
----------------
A. Rows whose `control_type` contradicts their own `source_text` — the quote is
   about a different KIND of control than the label says. This is invisible to
   the value checker: the number can match its quote exactly while describing
   the wrong control. Found 31 (28 served) on 2026-08-03; 20 were re-filed to
   `secondary_street_setback` (migration 054 + refile script), canada_bay 701
   and the MISSING_PRIMARY set were repaired against source the same day
   (scripts/repair_canada_bay_rear_setback.py,
   scripts/repair_missing_primary_controls.py).

B. Rows whose quote NARROWS to a special case (corner lot, secondary frontage,
   garage, upper storey...) while the row carries NO `condition` to scope it —
   so the exception reads as the rule. Camden 690 (3.5 m open-space exception
   served as the general front setback) was this shape.

C. MISSING_PRIMARY, per mismatched row: does the council store ANY other served
   row for the same control_type + dev_type? If not, the mismatched row is
   standing in for a control that is stored nowhere — worse than a wrong number,
   and invisible to every gate, because a gate cannot check a row that does not
   exist.

LESSONS BAKED IN (each from a real error, 2026-08)
--------------------------------------------------
* v1 required the words "side setback"; canada_bay 701's quote says "side
  BOUNDARIES", so a rear_setback row quoting the side-setback table was missed.
  Patterns now match boundary wording too.
* KNOWN FALSE POSITIVES of the foreign patterns, verified against source PDFs
  and NOT defects: georges_river 577 and blacktown 109 both read "side and rear
  boundaries" — one clause genuinely governing both. A quote may mention other
  controls and still be right; that is why this is a review list, not a gate.
* "Secondary dwelling building setback from street" is a PRIMARY street control
  for a granny flat (blacktown 107). Matching 'secondary' near 'street' is not
  enough; it must qualify the road itself.
* A quote truncated at the extractor's 400-char limit proves nothing either way
  (TRUNCATED_EVIDENCE doctrine) — those rows are listed separately, not judged.

Findings recorded in .claude/DATA_QUALITY_TRACKER.md (DQ-40) and adjudicated in
docs/qa/controls-adjudication-2026-08.md. Rulings need the PDF, not this script.
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _anchor(word: str) -> str:
    """Setback OR boundary wording — the v1 blind spot was requiring 'setback'."""
    return rf"{word}\s*(?:setbacks?|boundar(?:y|ies))"


# Per control_type: (foreign wording, own-control wording). A row is flagged when
# the quote matches FOREIGN and does not match OWN.
FOREIGN = {
    "front_setback": (
        rf"secondary\s+(?:street|frontage|road)|{_anchor('rear')}|{_anchor('side')}|"
        rf"garage|carport|driveway|crossover|fenc",
        r"front\s*setback|front\s+building|primary\s+(?:road|street|frontage)"),
    "secondary_street_setback": (
        rf"{_anchor('rear')}|garage|carport|driveway|fenc",
        r"secondary\s+(?:street|frontage|road)|corner"),
    "rear_setback": (
        rf"{_anchor('side')}|{_anchor('front')}|garage|driveway|fenc",
        r"rear\s*(?:setback|boundar|building line)"),
    "side_setback": (
        rf"{_anchor('rear')}|{_anchor('front')}|garage|driveway|fenc",
        r"side\s*(?:setback|boundar)"),
    "car_parking": (
        r"maximum of[^.]{0,40}m2|restricted to a maximum|gross floor area|\bGFA\b",
        r"\bspace|\bspaces\b|\bpark"),
}

# Wording that narrows a control to a special case. Dangerous only when the row
# has no condition — then the exception reads as the rule.
NARROWING = re.compile(
    r"corner\s+(?:lot|allotment|site)|secondary\s+(?:street|frontage|road)|"
    r"upper\s+floor|second\s+storey|battle[- ]axe|fronting\s+open\s+space|"
    r"garage|laneway|rear\s+lane|zero\s+lot", re.I)

# Narrowing wording that is INHERENT to a control type, not a special case: a
# car_parking control legitimately speaks in garage terms (georges_river 229 and
# campbelltown 256/257 all STATE the general rule as "one garage/space per
# dwelling" — adjudicated correct 2026-08-03), and a secondary_street_setback is
# by definition the corner-lot control (cumberland 34). Without the exemption
# these correct rows re-appear on every run, which is how a review list gets
# ignored. A row is still flagged if a NON-inherent narrowing term matches.
NARROWING_INHERENT = {
    "car_parking": re.compile(r"garage|carport", re.I),
    "secondary_street_setback": re.compile(
        r"corner\s+(?:lot|allotment|site)|secondary\s+(?:street|frontage|road)",
        re.I),
}


def narrowing_hits(control_type: str, text: str) -> list[str]:
    hits = [m.group(0) for m in NARROWING.finditer(text)]
    inherent = NARROWING_INHERENT.get(control_type)
    if inherent:
        hits = [h for h in hits if not inherent.search(h)]
    return hits

# Verified against source PDFs, not defects. Kept here so re-runs do not
# re-report settled rows; every entry carries its reason.
KNOWN_FALSE_POSITIVES = {
    577: "georges_river: 'side and rear boundaries' — one clause governs both; "
         "side_setback filing is correct (1500mm, laneway nil excluded).",
    109: "blacktown: s4.3.6 'Walls minimum 900mm from side and rear boundaries' — "
         "same shape, side filing correct.",
    30: "cumberland: rear 8.0m verified CORRECT against Table 1 p.B8; flagged "
        "only because its 400-char quote severs the rear row (retired anyway).",
    105: "blacktown: s3.2.5 'Side and rear boundary wall setbacks' — ground "
         "storey walls min 1.5m from any side OR rear boundary (verified "
         "against the local Part C PDF p.21, 2026-08-03); one clause governs "
         "both boundaries, so the side filing is correct. Same settled shape "
         "as 577/109.",
    707: "burwood: adjudicated 2026-08-03 — P10 is the garage-WALL side "
         "setback, now conditioned as such; the general side setback (Table "
         "3) is stored separately (row 1176). The garage mention is the "
         "control's own subject, not a foreign control.",
    715: "fairfield: adjudicated 2026-08-03 — quote is 5B.2.3.1(a), 'minimum "
         "side and rear setbacks of 900mm'; one clause governs both "
         "boundaries (577/109/105 shape), side filing correct.",
    714: "fairfield: adjudicated 2026-08-03 — RETIRED (is_current=FALSE) via "
         "repair_missing_primary_controls.py: the 6m is a Chapter 5C narrow-"
         "lot garage setback and Fairfield prescribes no numeric front "
         "setback for secondary dwellings (5B.2.3.1). Settled by retirement.",
}

TRUNCATION_LIMIT = 400


def main() -> int:  # pragma: no cover - CLI entry point
    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url or "localhost" in url:
        print("ERROR: DATABASE_URL unset or pointing at localhost — nothing was "
              "measured, which is not a pass. Run from the repo root where .env "
              "lives. Exiting 2.", file=sys.stderr)
        return 2
    import psycopg2
    from psycopg2.extras import RealDictCursor

    conn = psycopg2.connect(url)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SET statement_timeout = '60000'")
    cur.execute("""SELECT id, lga, control_type, dev_type, value_min, value_max,
                          unit, source_text, section_ref, condition, is_current
                     FROM dcp_setback_controls
                    WHERE value_min IS NOT NULL OR value_max IS NOT NULL""")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    by_key = defaultdict(list)
    for r in rows:
        by_key[(r["lga"], r["control_type"], r["dev_type"])].append(r)

    wrong_type, unconditioned, truncated = [], [], []
    for r in rows:
        text = r["source_text"] or ""
        if len(text) == TRUNCATION_LIMIT:
            truncated.append(r)          # listed, never judged — not evidence
            continue
        rule = FOREIGN.get(r["control_type"])
        if (rule and re.search(rule[0], text, re.I)
                and not re.search(rule[1], text, re.I)):
            wrong_type.append(r)
            continue
        if (narrowing_hits(r["control_type"], text)
                and not (r["condition"] or "").strip()):
            unconditioned.append(r)

    def missing_primary(r) -> bool:
        # KNOWN LIMIT (Sol, 2026-08-03, accepted): siblings are keyed by
        # (lga, control_type, dev_type) only — a served conditioned EXCEPTION
        # counts as the primary, and instrument/version is not distinguished.
        # Condition-presence cannot be the signal: verified general rows carry
        # scoping conditions too (camden 690, burwood 1176). Distinguishing
        # general from exception needs the structured condition discriminators
        # designed in ~/.claude/plans/ce-dcp-condition-structuring-2026-08.md
        # (a different lane). This is an advisory review list, exit 0.
        siblings = by_key[(r["lga"], r["control_type"], r["dev_type"])]
        return not any(s["is_current"] and s["id"] != r["id"] for s in siblings)

    print(f"scanned {len(rows)} numbered rows\n")

    print("=== A. control_type contradicts its own quote ===")
    live = [r for r in wrong_type if r["id"] not in KNOWN_FALSE_POSITIVES]
    settled = [r for r in wrong_type if r["id"] in KNOWN_FALSE_POSITIVES]
    print(f"  to review: {len(live)}  (served "
          f"{sum(1 for r in live if r['is_current'])})  |  "
          f"settled false positives suppressed: {len(settled)}")
    print(f"  by council: {Counter(r['lga'] for r in live).most_common()}")
    for r in sorted(live, key=lambda x: (not x["is_current"], x["lga"])):
        mp = "  ** MISSING_PRIMARY **" if missing_primary(r) else ""
        print(f"    id={r['id']:<5} {r['lga']}/{r['control_type']}/{r['dev_type']} "
              f"= {r['value_min']}{r['unit'] or ''} served={r['is_current']}{mp}")
        print(f"       {(r['source_text'] or '')[:105]!r}")

    print(f"\n=== B. narrowing quote with NO condition — exception reads as rule ===")
    print(f"  total {len(unconditioned)}  (served "
          f"{sum(1 for r in unconditioned if r['is_current'])})")
    for r in unconditioned:
        mp = "  ** MISSING_PRIMARY **" if missing_primary(r) else ""
        print(f"    id={r['id']:<5} {r['lga']}/{r['control_type']}/{r['dev_type']} "
              f"= {r['value_min']}{r['unit'] or ''} served={r['is_current']}{mp}")
        print(f"       {(r['source_text'] or '')[:105]!r}")

    print(f"\n=== C. truncated quotes (listed, never judged) ===")
    print(f"  {len(truncated)} rows at exactly {TRUNCATION_LIMIT} chars — "
          f"TRUNCATED_EVIDENCE doctrine: rule from the PDF, not the quote.")

    print("\nAdvisory only — exit 0. Rulings require the source PDF "
          "(data/dcps/ first, then the R2 copy pinned to r2_version_label).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
