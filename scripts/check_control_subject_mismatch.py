#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no existing check compares a
# control's SUBJECT against its control_type. Four sweeps, 2026-08-17 on
# origin/main 307c743f: (1) DB - all 18 candidate rows PASS
# validate_control_source_values, because their digits genuinely are in the
# quote; (2) python - services/extracted_data_integrity.py conflicting_values
# detects one key holding two values but never says why and cannot see a
# mis-filed control that is alone in its slot, and validate_dcp_setbacks.py is
# scoped to 280 rows with four signals that never look at the subject;
# (3) frontend - DcpSnapshotCard and DcpStructuredControls render control_type
# and condition, neither validates them; (4) plans/memory - DQ-32c is recorded
# as "needs a source lookup per row", a per-row remedy with no guard behind it.
"""A control's number must be about the thing its control_type names.

WHY
---
`dcp_setback_controls` is the moat: numbers a RAG system cannot produce because
someone had to read a PDF. An existing gate already proves each number is
derivable from its own quoted `source_text`. Every row this check flags PASSES
that gate — the digits are really there. What is wrong is the noun they attach
to.

Four found by hand, all filed as a setback of the dwelling:

    "All driveways are to be set a minimum of 0.5m from any side boundary"
        -> a DRIVEWAY setback, served as the house's side setback, and 0.5 is
           SMALLER than the real 0.9 ground-level side setback in the same slot.
    "Duplex development requires a minimum site frontage of 15 metres"
        -> a LOT WIDTH, served as a front setback. 15 m would sterilise the lot.
    "provide a minimum of 12m between front facades"
        -> a SEPARATION BETWEEN BUILDINGS, served as a boundary setback.
    "be provided within 10m of the kerb; be setback at least 3 metres from the
     front boundary; ... be designed as per Council's Waste Management Guideline"
        -> a BIN HARDSTAND setback, served as the secondary dwelling's front
           setback, and after its slot-mate was excluded it became the ONLY
           front setback served for that council and development type.

THE FIRST VERSION WAS WRONG, AND THAT IS THE DESIGN NOTE
--------------------------------------------------------
"A foreign word appears near the number" flagged 8 rows, of which the 4 that
were actually SERVED were all correct. Marrickville reads

    "Minimum side setback: a. Must be 4 metres where there is no driveway
     along the side boundary. b. Must be 7 metres where a driveway is proposed"

— the driveway is the CONDITION that distinguishes two correct setbacks, not
the subject of either. A flag list where the live entries are all false is
worse than no list, because it teaches you to skip the one real entry inside it.

So the rule is positional, not lexical:

  GOVERNS  the foreign noun sits next to the number with no conditional word
           ("where", "if", "unless", "other than", "except") between them, in
           either direction. "All driveways are to be set ... 0.5m" governs.
           "4 metres where there is no driveway" does not.
  QUOTE    the whole source_text is about a foreign subject and never names a
           building at all. Catches the bin list, whose giveaway words sit in
           sibling list items far from the number.

Measured over the 268 setback/height rows that carry a locatable number:
5 of 6 known-bad recovered, 0 false positives, 0 of 4 known-good flagged.

WHAT THIS DELIBERATELY DOES NOT CLAIM
-------------------------------------
The sixth known-bad row stores a corner-lot SIDE setback ("must have a
secondary street (side setback) of a minimum of 2m") under `front_setback`.
That is a front-vs-side confusion, not a foreign subject, and stretching this
rule to reach it is how the noise gets back in. It is out of scope and stays
recorded rather than silently covered.

Coverage is reported, not implied: only rows whose stored number can be located
in their own quote can be examined. The denominator prints on every run.

Exit 0 = ran and found none. Exit 1 = at least one mismatch. Exit 2 = could not
measure, which is never a pass.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

_reconfigure = getattr(sys.stdout, "reconfigure", None)
if callable(_reconfigure):  # a replaced stdout (io.StringIO) has none
    _reconfigure(encoding="utf-8", errors="replace")

# Subjects a setback or height can attach to that are NOT the building the
# control claims to govern. Every entry earned its place from a real row.
FOREIGN = re.compile(
    r"\bfenc(?:e|es|ing)\b"
    r"|\b(?:bin|bins|waste|garbage|refuse)\b"
    r"|\bdriveways?\b|\bcrossover\b"
    r"|\bsite frontage\b|\bminimum (?:site )?frontage\b"
    r"|\bbetween (?:front )?facades\b"
    r"|\bletterbox(?:es)?\b|\bawnings?\b|\bsignage\b"
    r"|\bhardstand\b",
    re.I,
)

# A foreign noun on the far side of one of these is qualifying the control, not
# being the control. This single guard is what removed every false positive.
CONDITIONAL = re.compile(r"\b(?:where|if|unless|other than|except)\b", re.I)

# If the quote names any of these it is at least plausibly about a building.
BUILDING = re.compile(
    r"\bdwelling|\bbuilding|\bhouse\b|\bstorey|\bresidential flat"
    r"|\bsecondary dwelling|\bgarage\b|\bcarport\b|\bdevelopment\b",
    re.I,
)

# Words that mark a quote as a waste-storage control specifically.
WASTE_QUOTE = re.compile(
    r"waste management|collect and return|\bhardstand\b|\bbins?\b"
    r"|\bgarbage\b|\brefuse\b",
    re.I,
)

GOVERN_WINDOW_BEFORE = 110
GOVERN_WINDOW_AFTER = 60

# A window must not run past the end of the sentence the number is in.
# "Minimum dwelling side setback 3m. Driveways must be 1m from the side
# boundary" puts 'driveways' inside a 60-character window, but in the NEXT
# sentence, where it governs a different number. Raised by adversarial review.
SENTENCE_END = re.compile(r"(?:[.;]\s|\n)")

# A single stray mention is not enough to call a whole quote a waste control -
# a genuine setback clause that happens to cross-reference the waste guideline
# would be condemned by one word. The bin row carries several independently
# ('hardstand', 'Waste Management', 'collect and return', 'bin').
MIN_WASTE_INDICATORS = 2

# Coverage floor. Measured at 242/250 = 97% served on 2026-08-17, so a drop
# below half means the shape of the data changed, not that it got cleaner.
MIN_COVERAGE = 0.5


def locate_value(source_text: str, value) -> re.Match | None:
    """Where the stored number appears in its own quote, in any plain form.

    Returns None when it cannot be found, which means the row is NOT checkable
    — a different state from "checked and fine", and counted separately.
    """
    if source_text is None or value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    forms = [str(value)]
    if v == int(v):
        forms.append(str(int(v)))
    forms.append(str(value).rstrip("0").rstrip("."))
    if 0 < v < 10:  # 0.9 m may be written "900mm" in the source
        forms.append(str(int(round(v * 1000))))
    for f in dict.fromkeys(x for x in forms if x):
        m = re.search(r"(?<!\d)" + re.escape(f) + r"(?!\d)", source_text)
        if m:
            return m
    return None


def subject_mismatch(source_text: str, value) -> str | None:
    """Return WHY the number is about something else, or None.

    Pure: no database, so the thing that decides whether the build goes red can
    be tested without one.
    """
    m = locate_value(source_text, value)
    if m is None:
        return None

    before = source_text[max(0, m.start() - GOVERN_WINDOW_BEFORE):m.start()]
    # Only the sentence the number belongs to. A foreign noun in the PREVIOUS
    # sentence governs that sentence's number, not this one.
    breaks = list(SENTENCE_END.finditer(before))
    if breaks:
        before = before[breaks[-1].end():]
    found = list(FOREIGN.finditer(before))
    if found and not CONDITIONAL.search(before[found[-1].end():]):
        return f"the number is governed by '{found[-1].group(0)}'"

    after = source_text[m.end():m.end() + GOVERN_WINDOW_AFTER]
    brk = SENTENCE_END.search(after)
    if brk:
        after = after[:brk.start()]
    fa = FOREIGN.search(after)
    if fa and not CONDITIONAL.search(after[:fa.start()]):
        return f"the number is qualified by '{fa.group(0)}'"

    waste_hits = {h.group(0).lower() for h in WASTE_QUOTE.finditer(source_text)}
    if len(waste_hits) >= MIN_WASTE_INDICATORS and not BUILDING.search(source_text):
        return "the whole quote is a waste-storage control and names no building"
    return None


def main() -> int:  # pragma: no cover - CLI entry point
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--all-rows", action="store_true",
                    help="include rows the served path already excludes")
    ap.add_argument("--show", type=int, default=20)
    args = ap.parse_args()

    from dotenv import load_dotenv
    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set — nothing was measured, which is "
              "not a pass. Exiting 2.", file=sys.stderr)
        return 2
    import psycopg2

    # The served filter is written literally and matches
    # scripts/conveyancing_db.py:317-319. --all-rows is a bound parameter so
    # widening the scope is deliberate rather than a variable that can hold TRUE.
    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '120000'")
        cur.execute("""
            SELECT id, lga, dev_type, control_type, value_min, unit, source_text
              FROM dcp_setback_controls
             WHERE (is_current = TRUE
                    AND (needs_review IS NULL OR needs_review = FALSE)
                    OR %(all_rows)s)
               AND source_text IS NOT NULL
               AND value_min IS NOT NULL
        """, {"all_rows": bool(args.all_rows)})
        rows = cur.fetchall()
        conn.close()
    except Exception as exc:  # noqa: BLE001 - any failure here is UNKNOWN
        print(f"ERROR: could not measure — {exc}. Exiting 2, which is not a "
              f"pass.", file=sys.stderr)
        return 2

    considered = checkable = 0
    bad = []
    for rid, lga, dev_type, control_type, value, unit, source_text in rows:
        if "setback" not in (control_type or "") and control_type != "max_height":
            continue
        considered += 1
        if locate_value(source_text, value) is None:
            continue
        checkable += 1
        why = subject_mismatch(source_text, value)
        if why:
            bad.append((rid, lga, dev_type, control_type, value, unit,
                        why, source_text))

    scope = "all rows" if args.all_rows else "served"
    print("=" * 72)
    print(f"CONTROL SUBJECT vs control_type — {scope}")
    print("=" * 72)
    print(f"setback/height rows      : {considered}")
    print(f"CHECKABLE (number locatable in its own quote): {checkable}")
    print(f"MISMATCHED               : {len(bad)}")
    print()
    print("A row is checkable only when its stored number can be found in its")
    print("own source_text. The rest are not evidence of correctness.")

    if bad:
        print()
        print("Each of these stores a number that is about something else:")
        for rid, lga, dev_type, ct, val, unit, why, src in bad[:args.show]:
            quote = re.sub(r"\s+", " ", src).strip()
            print(f"  id={rid} {lga} / {dev_type} / {ct} = {val}{unit or ''}")
            print(f"     {why}")
            print(f"     quote: {quote[:180]}")
        return 1

    # Zero is not the only way coverage collapses. If 241 of 242 rows changed
    # to a number format locate_value cannot recognise, a bare `checkable == 0`
    # test would still pass on the one remaining row while saying nothing about
    # the served set. Compare coverage against the rows actually considered, so
    # the guard needs no external baseline to notice. Raised by adversarial
    # review of the first version.
    coverage = (checkable / considered) if considered else 0.0
    if checkable == 0 or coverage < MIN_COVERAGE:
        print()
        print(f"ERROR: only {checkable} of {considered} setback/height rows "
              f"were checkable ({coverage:.0%}), below the {MIN_COVERAGE:.0%} "
              f"floor, so this run says little about the served set. That is "
              f"not a pass — exiting 2. Expect ~97%; if coverage has fallen, "
              f"source_text or value_min has changed shape.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
