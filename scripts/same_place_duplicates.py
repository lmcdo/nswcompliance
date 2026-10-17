#!/usr/bin/env python3
"""List served rows that repeat another served row of the SAME place in the SAME document (DQ-145 step 1).

prior-art-checked: the 2026-10-17 duplicate lists (data/sepp_duplicate_withhold_*.json) were built inline for
SEPP rows only; this is the same rule for every served row, written down so it can be re-run.

Two served rows are one rule shown twice when ALL hold:
  * same document_id and the same text after lower-casing and collapsing non-word characters;
  * the same applicability key (precinct, zones, dev types, site condition, land condition, heritage fields);
  * the same place: the same clause label once "Clause"/"Section", spaces and the "~N" suffix are dropped,
    OR the same non-null pdf_page.
Same words at a DIFFERENT place (another code, another page, another precinct) are kept: they are the
document repeating itself, and each place is its own citation (step 2 handles SEPP codes).

Kept per group: a proven row first, then a clause-shaped label over a topic/provision_NNN label, then the
lowest id. The rest go to the output list for scripts/withhold_state_paraphrase.py --list (it withholds by
setting v2_is_actionable = FALSE, backup first, never deletes).

    python scripts/same_place_duplicates.py --out data/same_place_duplicates_<date>.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_law_proof import connect  # noqa: E402

SERVED = "is_current AND v2_is_actionable AND (v2_provision_type IS NULL OR v2_provision_type <> 'TOC')"
PROVEN = ("(COALESCE(citation_status, '') IN ('proven', 'imprecise') "
          "OR COALESCE(page_check, '') IN ('on_page', 'moved'))")
CLAUSE_SHAPED = re.compile(r"^\s*(clause|section|schedule)?\s*\d", re.I)
WHOLE_PART = re.compile(r"(^|__)part\d+$")   # "..__Part 8": a whole Part is not one place


def norm_text(t: str | None) -> str:
    return re.sub(r"\W+", " ", (t or "").lower()).strip()


def norm_ref(r: str | None) -> str:
    r = re.sub(r"~\d+$", "", (r or "").strip())
    r = re.sub(r"^(clause|section)\s+", "", r, flags=re.I)
    return re.sub(r"\s+", "", r).lower()


def keep_order(row: dict) -> tuple:
    return (not row["proven"], not CLAUSE_SHAPED.match(row["ref"] or ""), row["id"])


def same_place_groups(rows: list[dict]) -> list[list[dict]]:
    """Group rows by (doc, text, key), then join rows sharing a ref or a page (union-find)."""
    by_text: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        by_text[(r["document_id"], norm_text(r["text"]), r["key"])].append(r)
    out = []
    for grp in by_text.values():
        if len(grp) < 2:
            continue
        parent = list(range(len(grp)))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        for i in range(len(grp)):
            for j in range(i + 1, len(grp)):
                a, b = grp[i], grp[j]
                ra, rb = norm_ref(a["ref"]), norm_ref(b["ref"])
                if (ra and ra == rb and not WHOLE_PART.search(ra)) or (a["page"] is not None and a["page"] == b["page"]):
                    parent[find(i)] = find(j)
        comps: dict[int, list[dict]] = defaultdict(list)
        for i, r in enumerate(grp):
            comps[find(i)].append(r)
        out += [c for c in comps.values() if len(c) > 1]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cur = connect().cursor()
    cur.execute(f"""SELECT id, document_id, source_council, ref_number, provision_text, pdf_page, {PROVEN},
        v2_precinct_id, v2_applicable_zones::text, v2_applicable_dev_types::text, v2_site_condition_required::text,
        v2_land_condition::text, v2_heritage_hca, v2_heritage_type, v2_heritage_element
        FROM regulatory_provisions WHERE {SERVED}""")
    rows = [{"id": r[0], "document_id": r[1], "council": r[2], "ref": r[3], "text": r[4], "page": r[5],
             "proven": r[6], "key": tuple(r[7:])} for r in cur.fetchall()]
    groups = same_place_groups(rows)
    listed = []
    for g in groups:
        g.sort(key=keep_order)
        keep = g[0]
        for r in g[1:]:
            listed.append({"id": r["id"], "council": r["council"], "kept": keep["id"], "ref": r["ref"],
                           "kept_ref": keep["ref"], "proven": r["proven"],
                           "reason": f"duplicate: same words, same place and same applicability as {keep['id']}"})
    Path(a.out).write_text(json.dumps(listed, indent=1), encoding="utf-8")
    unproven = sum(1 for r in listed if not r["proven"])
    print(f"{len(groups)} same-place groups; {len(listed)} rows listed ({unproven} unproven) -> {a.out}")
    for r in listed:
        print(f"  {r['council'] or 'state'}: withhold {r['id']} ({r['ref']}) keep {r['kept']} ({r['kept_ref']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
