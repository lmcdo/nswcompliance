#!/usr/bin/env python3
# prior-art-checked: this is the PRE-INSERT gate for control rows that do not exist
# yet. Neighbours opened, not guessed from their names:
#   validate_control_source_values.py  asks the same question of rows ALREADY in
#       dcp_setback_controls, nightly. It is the model for this and is deliberately
#       NOT modified: a proposal that never reaches the table cannot be checked by
#       a script that reads the table. Same rule, one step earlier.
#   validate_controls_provenance.py    asserts served controls carry provenance;
#       again, rows already inserted.
#   dcp_review_queue / the setback review surface  the HUMAN gate. This does not
#       replace it -- it decides what is even worth a human's time.
# No DB access at all: this reads two JSON files and compares strings.
"""Would-be control rows, checked against the document they claim to come from.

THE RULE
--------
A proposed control is accepted only if BOTH hold:

  1. its quote appears VERBATIM on the source page it cites, and
  2. its number appears IN THAT QUOTE.

Everything else is rejected. Not flagged, not queued -- rejected, because a
number that cannot be traced to the words beside it is a fabricated regulatory
value, which .claude/rules/regulatory-data.md forbids outright and which is worse
than having no value at all.

Check 2 is the one that does the work. A DCP page routinely states the front
setback, the rear setback and the secondary-street setback within a few lines of
each other, so "the number is somewhere on this page" is satisfied by every wrong
answer as easily as the right one. Requiring the number inside its own quote is
what separates them.

WHY THIS IS SEPARATE FROM validate_control_source_values.py
-----------------------------------------------------------
That script asks this question of rows already in the table, every night. This
asks it BEFORE anything is written, so a bad proposal never becomes a row, never
reaches the nightly check, and never costs a human any review time.

THE INPUT MATTERS AS MUCH AS THE CHECK
--------------------------------------
This verifies a proposal against the page text it was GIVEN. If that text was
extracted badly, a correct control can be unquotable and will be rejected --
a false negative that looks like diligence.

Measured 2026-09-12. Candidate pages for the first run were pulled with a naive
`page.extract_text()`. Four councils (ashfield, marrickville, city_of_sydney,
hornsby) are in GEOMETRIC_COLUMN_COUNCILS -- their DCPs are two-column and that
extractor interleaves the columns. Real controls were lost: hornsby p9's table row
"Secondary boundary (on corner lots) = 3m" arrived interleaved with an unrelated
driveway bullet, and p57's "secondary frontage adjoins an existing laneway...
setback a minimum of 6 metres" was split across three lines with competing 8m/7m/4m
figures in between. Both were correctly rejected as unquotable, and both are real.

So: for any council in GEOMETRIC_COLUMN_COUNCILS, build candidate pages with
`dcp_extract_changed._columnar_text(page)` and fall back to `extract_text()` only
when it returns None. The extraction pipeline already does this; a harness that
does not is handing the model worse input than production uses.

WHAT THE READING FOUND THAT THIS COULD NOT (first run, 2026-09-12)
------------------------------------------------------------------
All 11 proposals passed every check here, and four still needed changing. Worth
knowing which kinds, because they recur:

  DIRECTION. Two rows stored the CONCESSION as the requirement. "10m, which can
  be reduced to 8m for a maximum of 1/3 of the building width" was stored as 8;
  "Must be 6 metres ... may, at the discretion of Council, be reduced to 4.5
  metres" was stored as 4.5. Both numbers are genuinely in their own quotes, so
  nothing here objects -- and a consumer reading value_min gets the most
  permissive figure as though it were the rule. The table's own convention is the
  opposite (strathfield: front_setback 9 with "may be reduced..." in condition):
  **value_min is the requirement, the concession goes in the condition.**

  SCOPE. Two rows came from a precinct table (Pound Road) and one applies only
  where a site adjoins a heritage conservation area. Served LGA-wide they would
  OVERRIDE the council's real general answer with a site-specific one.

  GRAIN. Two rows are upper-level massing setbacks, not ground-level. A correct
  number answering a different question from the one asked.

None of the three is visible to a verbatim-and-number test. They are visible to
reading the clause. So the reading is not optional, and it is not the reviewer's
job to find these first.

WHAT IT CANNOT DO, STATED PLAINLY
---------------------------------
It cannot tell whether a control was correctly INTERPRETED -- whether "3.5m" is
really the secondary-street setback rather than the front setback quoted beside
it. It proves only that the number is in the document and in its own quote. The
human ruling in the setback review queue remains the authority on meaning. This
exists to make that review short, not to remove it.

    python scripts/dcp_verify_extracted_controls.py proposals.json \\
        --pages candidates.json --out accepted.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

REQUIRED = ("council", "control_type", "value_min", "unit", "condition",
            "section_ref", "source_text", "source_page", "source_chapter")

ACCEPT, REJECT = "ACCEPT", "REJECT"

# A setback in metres has a plausible range. Outside it, the "value" is a clause
# number, a year or an area that happened to sit next to a unit.
MIN_PLAUSIBLE_M, MAX_PLAUSIBLE_M = 0.0, 30.0
MIN_QUOTE_CHARS = 25


def normalise(text: str) -> str:
    """Fold the differences a PDF introduces but a reader would not see.

    Ligatures, non-breaking spaces, curly quotes and the several dash characters
    all differ between what pdfplumber returns and what anyone retypes, so a raw
    comparison rejects correct quotes for typography. Only whitespace and those
    equivalences are folded -- never digits, never letters.
    """
    t = unicodedata.normalize("NFKD", text or "")
    t = (t.replace("’", "'").replace("‘", "'")
          .replace("“", '"').replace("”", '"'))
    t = re.sub(r"[‐-―−]", "-", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip().lower()


def numbers_in(text: str) -> set[str]:
    """Every number in the text, normalised so 3.50 and 3.5 compare equal."""
    out: set[str] = set()
    for raw in re.findall(r"\d+(?:\.\d+)?", text or ""):
        try:
            out.add(("%f" % float(raw)).rstrip("0").rstrip("."))
        except ValueError:
            continue
    return out


def ambiguous_quotes(proposals: list[dict]) -> dict[str, list[dict]]:
    """Proposals that share one quote while asserting DIFFERENT values.

    Found on the first real run, 2026-09-12. Two hornsby Pound Road rows carried
    the identical quote -- an interleaved table cell reading "4m, plus any ground
    floor commercial premises should be setback behind a colonnade ... (i.e. min
    setback of 7.5m)" -- and claimed 4m and 7.5m respectively. Both passed the
    per-row checks, because both numbers genuinely appear in that quote.

    That is the limit of a per-row test: the quote is evidence for the row, but
    where one quote supports two different answers it cannot be evidence for
    EITHER without the reader also trusting the condition text. Such rows are not
    rejected -- both may well be right, and a colonnade variant is a real control
    -- but they are the ones a human should read first, so they are surfaced
    rather than left to look as settled as an unambiguous row.
    """
    by_quote: dict[str, list[dict]] = {}
    for prop in proposals:
        key = normalise(str(prop.get("source_text", "")))
        by_quote.setdefault(key, []).append(prop)
    out = {}
    for quote, group in by_quote.items():
        values = {str(g.get("value_min")) + "/" + str(g.get("value_max"))
                  for g in group}
        if len(group) > 1 and len(values) > 1:
            out[quote] = group
    return out


def check(proposal: dict, page_text: str) -> tuple[str, list[str]]:
    """-> (verdict, reasons). Every reason is a checkable fact about this row."""
    reasons: list[str] = []
    for field in REQUIRED:
        if proposal.get(field) in (None, ""):
            reasons.append("missing field: " + field)
    if reasons:
        return REJECT, reasons

    quote = str(proposal["source_text"])
    if len(quote.strip()) < MIN_QUOTE_CHARS:
        reasons.append("quote too short to be evidence (" +
                       str(len(quote.strip())) + " chars)")

    if normalise(quote) not in normalise(page_text):
        reasons.append("quote does NOT appear verbatim on the cited page")

    quote_numbers = numbers_in(quote)
    for field in ("value_min", "value_max"):
        val = proposal.get(field)
        if val in (None, ""):
            continue
        try:
            norm = ("%f" % float(val)).rstrip("0").rstrip(".")
        except (TypeError, ValueError):
            reasons.append(field + " is not a number: " + repr(val))
            continue
        if norm not in quote_numbers:
            reasons.append(field + "=" + str(val) +
                           " does not appear in its own quote")
        elif proposal.get("unit") == "m" and not (
                MIN_PLAUSIBLE_M < float(val) <= MAX_PLAUSIBLE_M):
            reasons.append(field + "=" + str(val) +
                           "m is outside the plausible setback range")

    return (REJECT if reasons else ACCEPT), reasons


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("proposals", help="JSON list of proposed control rows")
    ap.add_argument("--pages", required=True,
                    help="JSON list of the candidate pages they must come from")
    ap.add_argument("--out", help="write accepted rows here (still not inserted)")
    args = ap.parse_args(argv)

    with open(args.proposals, encoding="utf-8") as fh:
        proposals = json.load(fh)
    with open(args.pages, encoding="utf-8") as fh:
        pages = json.load(fh)
    by_page = {(p["council"], p["chapter"], p["page"]): p["text"] for p in pages}

    accepted: list[dict] = []
    rejected: list[tuple[dict, list[str]]] = []
    for prop in proposals:
        key = (prop.get("council"), prop.get("source_chapter"),
               prop.get("source_page"))
        page_text = by_page.get(key)
        if page_text is None:
            rejected.append((prop, ["cites a page that was never supplied: " +
                                    str(key)]))
            continue
        verdict, reasons = check(prop, page_text)
        if verdict == ACCEPT:
            accepted.append(prop)
        else:
            rejected.append((prop, reasons))

    print("proposals: " + str(len(proposals)))
    print("  ACCEPTED: " + str(len(accepted)))
    print("  REJECTED: " + str(len(rejected)))
    if rejected:
        print()
        for prop, reasons in rejected:
            print("   REJECT  " + str(prop.get("council", "?")).ljust(16) +
                  str(prop.get("section_ref", "?"))[:26])
            for r in reasons:
                print("             " + r)
    ambiguous = ambiguous_quotes(accepted)
    if ambiguous:
        print()
        print("  AMBIGUOUS -- one quote, more than one asserted value. Accepted,")
        print("  but read these first: the quote alone does not decide the value.")
        for group in ambiguous.values():
            for g in group:
                print("     " + str(g["council"]).ljust(14) +
                      str(g["section_ref"])[:30].ljust(32) +
                      str(g["value_min"]) + str(g.get("unit", "")))
            print("       shared quote: " +
                  repr(str(group[0]["source_text"])[:90]))

    if accepted:
        print()
        for prop in accepted:
            print("   OK      " + str(prop["council"]).ljust(16) +
                  str(prop["control_type"]).ljust(26) +
                  (str(prop["value_min"]) + str(prop.get("unit", ""))).ljust(8) +
                  str(prop["section_ref"])[:26] + "  p" + str(prop["source_page"]))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(accepted, fh, indent=1)
        print()
        print("accepted rows written to " + args.out + " -- NOT inserted.")
        print("The setback review queue is still the authority on whether each "
              "one MEANS what it says.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print("FATAL: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        sys.exit(1)
