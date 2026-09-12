#!/usr/bin/env python3
# prior-art-checked: neighbours opened, not guessed from their names.
#   dcp_verify_extracted_controls.py  the MECHANICAL gate. Quote verbatim on the
#       cited page, number inside its own quote. It cannot read. This is the
#       reading, and it runs AFTER that gate and re-invokes it.
#   dcp_control_candidates.py         selects what a model may look at.
#   the setback review surface (/internal/dcp-review)  the human authority on
#       whether a row is served. Not replaced: this is the reviewer's own work
#       recorded as a file, so what was decided and why is checkable later.
#   scripts/validate_control_source_values.py  the same question nightly, on rows
#       already in the table.
# DB sweep: nothing records a per-row semantic verdict for PROPOSED rows.
# No DB access: reads two JSON files and writes a third.
"""The reading that a verbatim-and-number check cannot do.

WHY THIS IS A FILE AND NOT A CONVERSATION
-----------------------------------------
The mechanical verifier proves a number is in the document and inside its own
quote. On the first real run all 11 proposals passed every mechanical check and
**four still had to be changed**. Those four were found by reading the clause. A
reading that lives only in a chat message cannot be re-run, diffed, or checked by
anyone else, so it is written here instead.

THE THREE WAYS A MECHANICALLY PERFECT ROW IS STILL WRONG
--------------------------------------------------------
Each of these was found in real proposals, and none is visible to the verifier.

  DIRECTION. "10m, which can be reduced to 8m for a maximum of 1/3 of the
  building width" stored as value_min=8. "Must be 6 metres ... may, at the
  discretion of Council, be reduced to 4.5 metres" stored as 4.5. Both numbers
  are genuinely in their own quotes. Both hand a consumer the CONCESSION as
  though it were the rule -- the dangerous direction for a compliance product.
  The table's own convention settles it: strathfield stores front_setback min 9
  with "may be reduced if predominant setback in street block is less" in the
  condition. **value_min is the requirement; the concession goes in condition.**

  SCOPE. Two rows came from a named precinct table and one applied only where a
  site adjoins a heritage conservation area. Served LGA-wide they would OVERRIDE
  the council's real general answer with a site-specific one.

  GRAIN. Two rows were upper-level massing setbacks, not ground-level street
  setbacks. A correct number answering a different question from the one asked.

FAIL-CLOSED, AND THE CORRECTION IS RE-CHECKED
---------------------------------------------
Two rules, both learned from the previous run:

1. A proposal with no recorded verdict does not pass. It is reported as
   UNREVIEWED and excluded. "I did not get to it" must never read as "fine".

2. A verdict that CHANGES a value re-runs the mechanical check against the same
   page text. The previous review changed 8 -> 10 and 4.5 -> 6 by hand and never
   re-checked, so a corrected value could have left its own quote unnoticed --
   the reviewer introducing exactly the defect the verifier exists to catch.

    python scripts/dcp_review_proposals.py accepted.json \\
        --verdicts review.json --pages candidates.json --out reviewed.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from scripts.dcp_verify_extracted_controls import ACCEPT, check
except ImportError:  # running from inside scripts/
    from dcp_verify_extracted_controls import ACCEPT, check

# SERVE means the row may go to the human review surface. Everything else stops
# here. HOLD exists so a row can be kept with its reason instead of vanishing.
SERVE_VERDICTS = {"ACCEPT", "ACCEPT_QUALIFIED", "CORRECT_AND_ACCEPT"}
STOP_VERDICTS = {"REJECT", "HOLD", "DUPLICATE"}
VALID_VERDICTS = SERVE_VERDICTS | STOP_VERDICTS

# A verdict's note is not decoration. An unexplained ACCEPT is indistinguishable
# from an unread one, which is the state this file exists to make impossible.
MIN_NOTE_CHARS = 40


KEY_FIELDS = ("council", "control_type", "dev_type", "section_ref",
              "source_page", "value_min")


def row_key(row: dict) -> str:
    """How a verdict names the row it judges.

    `value_min` and `dev_type` are in the key, and they have to be. The first
    version keyed on council|control_type|section_ref|source_page, and parramatta
    states three different minimums under ONE clause label -- "C.04 a) 8m2 for
    1-bedroom, b) 12m2 for 2-bedroom, c) 16m2 for 3 or more" -- all on page 100.
    Three rows collapsed onto one key, so a single verdict written about one of
    them would silently have governed all three, and two of the three would never
    have been read at all while the run reported zero problems.
    """
    return "|".join(str(row.get(f, "")) for f in KEY_FIELDS)


def apply_review(proposals: list[dict], verdicts: dict, pages: dict
                 ) -> tuple[list[dict], list[dict], list[str]]:
    """-> (to_serve, stopped, problems). Every problem names a specific row."""
    to_serve: list[dict] = []
    stopped: list[dict] = []
    problems: list[str] = []

    # Even with value_min in the key, two proposals can still collide -- and then
    # one verdict silently governs both. Identical rows may well deserve the same
    # ruling, but that has to be a stated decision, not an accident of keying.
    seen = Counter(row_key(p) for p in proposals)
    for key, n in sorted(seen.items()):
        if n > 1:
            problems.append("KEY COLLISION x" + str(n) + " (one verdict would "
                            "govern " + str(n) + " rows)  " + key)

    for prop in proposals:
        key = row_key(prop)
        entry = verdicts.get(key)
        if entry is None:
            problems.append("UNREVIEWED  " + key)
            continue

        verdict = str(entry.get("verdict", "")).upper()
        note = str(entry.get("note", ""))
        if verdict not in VALID_VERDICTS:
            problems.append("BAD VERDICT " + repr(verdict) + "  " + key)
            continue
        if len(note.strip()) < MIN_NOTE_CHARS:
            problems.append("NOTE TOO SHORT (an unexplained verdict is an "
                            "unread one)  " + key)
            continue

        row = dict(prop)
        row.update(entry.get("corrections", {}))
        row["review_verdict"] = verdict
        row["review_note"] = note.strip()

        changed = {f: (prop.get(f), row.get(f))
                   for f in ("value_min", "value_max")
                   if prop.get(f) != row.get(f)}
        row["review_changed_values"] = changed or None

        if verdict not in SERVE_VERDICTS:
            stopped.append(row)
            continue

        # A corrected value must still satisfy the mechanical rule. The reviewer
        # is not exempt from the check the reviewer is enforcing.
        page_text = pages.get((row.get("council"), row.get("source_chapter"),
                               row.get("source_page")))
        if page_text is None:
            problems.append("CORRECTED ROW CITES A PAGE NOT SUPPLIED  " + key)
            continue
        verdict_again, reasons = check(row, page_text)
        if verdict_again != ACCEPT:
            problems.append("REVIEW BROKE THE ROW  " + key + "  -> " +
                            "; ".join(reasons))
            continue
        to_serve.append(row)

    return to_serve, stopped, problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("proposals", help="rows the mechanical verifier ACCEPTED")
    ap.add_argument("--verdicts", required=True,
                    help="JSON object: row_key -> {verdict, note, corrections}")
    ap.add_argument("--pages", required=True,
                    help="the candidate pages, to re-check corrected values")
    ap.add_argument("--out", help="write reviewed rows here (still not inserted)")
    args = ap.parse_args(argv)

    with open(args.proposals, encoding="utf-8") as fh:
        proposals = json.load(fh)
    with open(args.verdicts, encoding="utf-8") as fh:
        verdicts = json.load(fh)
    with open(args.pages, encoding="utf-8") as fh:
        pages = {(p["council"], p["chapter"], p["page"]): p["text"]
                 for p in json.load(fh)}

    to_serve, stopped, problems = apply_review(proposals, verdicts, pages)

    print("proposals reviewed: " + str(len(proposals)))
    print("  cleared to the human review surface: " + str(len(to_serve)))
    print("  stopped here:                        " + str(len(stopped)))
    print("  PROBLEMS:                            " + str(len(problems)))
    if problems:
        print()
        for p in problems:
            print("   " + p)
    print()
    print("  " + "council".ljust(16) + "section".ljust(34) +
          "verdict".ljust(20) + "was".rjust(7) + "now".rjust(7))
    for row in to_serve + stopped:
        changed = row.get("review_changed_values") or {}
        was, now = changed.get("value_min", (row.get("value_min"),) * 2)
        flag = "   <== VALUE CHANGED" if changed else ""
        print("  " + str(row.get("council", "?")).ljust(16) +
              str(row.get("section_ref", "?"))[:32].ljust(34) +
              row["review_verdict"].ljust(20) +
              str(was).rjust(7) + str(now).rjust(7) + flag)
    print()
    print("  " + str(dict(Counter(r["review_verdict"]
                                  for r in to_serve + stopped))))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(to_serve, fh, indent=1)
        print()
        print("cleared rows written to " + args.out + " -- NOT inserted.")
        print("The human review surface remains the authority on whether each "
              "one is served.")
    # Fail-closed: an unreviewed or broken row must not read as a clean run.
    return 1 if problems else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print("FATAL: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        sys.exit(1)
