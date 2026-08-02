#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no gate checks a control's stored
# NUMBER against its own quoted source_text across the whole table. Opened and
# rejected on scope: scripts/validate_dcp_setbacks.py covers only the 280 setback
# rows and its four signals (CONFLICT/FOREIGN/MAGNITUDE/PLACEHOLDER) never compare
# the value to the quote; scripts/validate_controls_provenance.py (#866) classifies
# provenance from the REPO, never the row's text; scripts/link_controls_to_provisions.py
# (#867) matches quotes against the CORPUS, which is capped at 42 rows by ingestion
# coverage; scripts/numeric_control_review.py diffs against a re-downloaded PDF, not
# the stored quote; scripts/verify_setback_source_texts.py prints text for a human.
# services/extracted_data_integrity.py:value_absent_from_source is the flagger this
# builds on and is extended in place rather than copied.
"""Every stored control value must be derivable from its own quoted source text.

WHY THIS EXISTS
---------------
`dcp_setback_controls` is the product: 1,069 numbers a RAG system cannot produce,
because someone had to read a PDF and decide what the number is. Only 42 of them
can be checked against the provisions corpus — 14 of 30 councils have no
provisions ingested at all (DQ-38), so 450 rows have nothing to point at.

But every row already carries `source_text`, the sentence its number was taken
from. Checking a number against its OWN quote needs no corpus, no PDF and no
ingestion work, so it covers all 1,069 instead of 42. That is the whole idea.

WHAT IT ACTUALLY CHECKS
-----------------------
`value_absent_from_source` already flagged rows whose digits do not appear in
their quote. That flag is not an answer: most of them are legitimate derivations
("900mm" stored as 0.9, "one space per 3 dwellings" stored as 0.333). A list of
flags where most entries are fine trains you to ignore the list, which is how a
real mismatch survives inside it.

So this separates derivation from mismatch. Every row lands in EXACTLY ONE state:

    exact_digit_match        the number is literally in the quote
    percentage_phrasing      '35%' stored as the fraction 0.35
    unit_conversion          '900mm' stored as 0.9 m
    fraction_literal         'min 1/3' stored as 0.333
    ratio_or_rate            '1 space per 4 dwellings' stored as 0.25
    implied_single_unit_rate 'a space for every 4 dwellings' stored as 0.25
    area_from_dimensions     '3m x 3m' stored as 9
    written_numeral          'three hours' stored as 3
    explicit_nil_requirement 'no additional parking is required' stored as 0
    built_to_boundary_zero   'may be built to the rear boundary' stored as 0
    UNEXPLAINED              <- the finding
    MISSING_SOURCE_TEXT      a number with no quote at all <- also the finding
    no_value_stored          a control with no number (nothing to check; NOT a
                             pass — counted and reported separately)

Every explanation carries the substring it matched, printed with `--show-evidence`.
A rule that could not show its evidence would be a shrug with a name on it.

WHY IT CAN FAIL
---------------
The project's standing lesson is that a check which cannot go red is not a
verification (DQ-30's "0% drift" compared the data to the code that produced it).
This one goes red four ways:

  * a control that no named rule explains is not in the baseline;
  * a control that IS in the baseline has since had its value, unit or quote
    changed — the baseline stores a digest of those, not just the id, so swapping
    one unsupported number for a different one does not stay accepted;
  * a baselined row has become explained and was not removed from the baseline —
    leaving it there would keep it accepted forever, so restoring its old value
    later would not fail;
  * a number is stored with no source_text at all.

Only `is_current` rows block; superseded ones are reported, never dropped.
`--write-baseline` refuses to ADD rows without `--allow-growth`, so the command
offered to fix a shrink failure cannot double as the bypass.

WHAT IT DOES NOT PROVE
----------------------
That the number is CORRECT. It proves the number is consistent with the sentence
stored beside it. If the quote itself was mis-transcribed, both agree and this
passes — that failure mode belongs to the extraction gates, not here.

And consistency is weaker than it sounds where a quote holds several numbers:
571 of the 839 exact matches (68.1%) sit in a quote carrying more than one
distinct quantity, so the stored value appears in its source but is not pinned by
it. That split is printed. Closing it means reading clauses rather than matching
numbers, which is a different tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from services.extracted_data_integrity import (  # noqa: E402
    FAILING_STATES,
    MISSING_SOURCE_TEXT,
    NO_VALUE_STORED,
    RULE_NAMES,
    UNEXPLAINED,
    explain_row,
)

VALUE_FIELDS = ["value_min", "value_max"]
DEFAULT_BASELINE = "scripts/control_source_values_baseline.json"
STATES = (*RULE_NAMES, UNEXPLAINED, MISSING_SOURCE_TEXT, NO_VALUE_STORED)


def fingerprint(row: dict) -> str:
    """What was accepted, not merely which row was accepted.

    prior-art-checked: reuse not viable because no existing baseline in this repo
    is content-addressed. scripts/schema_contract_baseline.json keys on
    (file, ref) string pairs and scripts/check_test_baselines.py compares a plain
    integer floor; neither carries a digest of the accepted content, which is the
    whole point here.

    Keying the baseline on `id` alone meant a baselined control could change its
    stored value from one unsupported number to a DIFFERENT unsupported number —
    or lose its quote entirely — and stay accepted, because the id had not moved.
    The digest covers exactly the inputs the check reads, so any change to them
    makes the row new again.

    `is_current` is part of it too: only current rows block, so a superseded row
    flipping to current is the moment an accepted-but-unsupported value starts
    being served. Without it the digest still matched and the flip passed.
    """
    payload = "|".join(str(row.get(f)) for f in
                       (*VALUE_FIELDS, "unit", "source_text", "is_current"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def load_baseline(repo: Path, path: str | None) -> dict:
    """The accepted unexplained rows. A missing file is an empty baseline.

    An UNREADABLE file is not: a corrupt baseline that silently became empty would
    turn every pre-existing row into a new failure, and the natural response to
    that noise is to regenerate the baseline — which is how a gate gets disarmed.
    """
    p = repo / (path or DEFAULT_BASELINE)
    if not p.exists():
        return {"accepted": {}}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: baseline {p} is unreadable ({exc}). Refusing to run rather "
              f"than treating it as empty.", file=sys.stderr)
        raise SystemExit(2)


def write_baseline(repo: Path, path: str | None, accepted: dict,
                   valueless: set) -> None:
    p = repo / (path or DEFAULT_BASELINE)
    p.write_text(
        json.dumps({
            "note": "Controls whose stored value no named rule derives from their "
                    "own source_text. Keyed id -> digest of the value, unit and "
                    "quote, so editing an accepted row to a DIFFERENT unsupported "
                    "value makes it a new finding rather than leaving it accepted. "
                    "Shrink-only: a row that becomes explained must be removed, and "
                    "--write-baseline refuses to add ids without --allow-growth.",
            "count": len(accepted),
            "accepted": {str(k): v for k, v in sorted(accepted.items())},
            "valueless_rows": sorted(valueless),
            "valueless_note": "Ids of controls that record a rule with no number "
                              "at all. Tracked as a SET, not a count: control A "
                              "losing its value while control B gains one leaves "
                              "the count at 83 and hides A entirely. A migration "
                              "that NULLs a real value moves the row here and "
                              "would otherwise pass as 'nothing to check' — the "
                              "check cannot tell an intentional blank from a lost "
                              "value, so it watches which rows are blank.",
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Baseline written to {p} ({len(accepted)} unexplained rows).")


def classify_rows(rows: list[dict]) -> tuple[Counter, dict, list[dict]]:
    """State counts, per-council counts, and the failing rows themselves."""
    counts: Counter = Counter()
    per_lga: dict[str, Counter] = defaultdict(Counter)
    failing: list[dict] = []
    for row in rows:
        result = explain_row(row, value_fields=VALUE_FIELDS,
                            source_field="source_text", unit_field="unit")
        counts[result["state"]] += 1
        per_lga[row.get("lga")][result["state"]] += 1
        row["_result"] = result
        if result["state"] == "exact_digit_match":
            counts["exact_uniquely_attributable" if result["uniquely_attributable"]
                   else "exact_among_several_quantities"] += 1
        if result["state"] in FAILING_STATES:
            failing.append(row)
    return counts, per_lga, failing


def fetch_rows(cur) -> list[dict]:
    """Every control, with the quote its number came from.

    DELIBERATELY UNFILTERED on is_current: a superseded row's number was still
    stored against a quote, and a check that skipped them would shrink its own
    denominator. is_current is selected and reported so the split is visible.
    """
    cur.execute(
        """SELECT id, lga, control_type, dev_type, value_min, value_max, unit,
                  source_text, section_ref, condition, extraction_method, is_current
           FROM dcp_setback_controls
           ORDER BY lga, control_type, id"""
    )
    columns = [d[0] for d in cur.description]
    return [dict(zip(columns, record)) for record in cur.fetchall()]


def main() -> int:  # pragma: no cover - CLI entry point
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", default=None)
    ap.add_argument("--write-baseline", action="store_true",
                    help="Rewrite the baseline from the current findings. Refuses to "
                         "ADD ids unless --allow-growth is also passed.")
    ap.add_argument("--allow-growth", action="store_true",
                    help="Permit --write-baseline to accept rows that were not "
                         "previously in the baseline. Requires a reason in the PR.")
    ap.add_argument("--show-evidence", action="store_true",
                    help="Print the substring each rule matched, so an explanation "
                         "can be audited rather than trusted.")
    ap.add_argument("--limit-print", type=int, default=40)
    args = ap.parse_args()

    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set — nothing was checked, which is not a "
              "pass. Exiting 2.", file=sys.stderr)
        return 2
    import psycopg2

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '60000'")
    try:
        rows = fetch_rows(cur)
    finally:
        conn.close()

    counts, per_lga, failing = classify_rows(rows)
    total = len(rows)

    print(f"\n=== every control value vs its own source_text ({total:,} rows) ===")
    for state in STATES:
        marker = "  <- the finding" if state in FAILING_STATES else ""
        share = 100.0 * counts[state] / max(1, total)
        print(f"  {state:<22}: {counts[state]:>5}  ({share:5.1f}%){marker}")
    print(f"  {'TOTAL':<22}: {sum(counts[s] for s in STATES):>5}   "
          f"(states are exhaustive — every row is in exactly one)")

    checked = total - counts[NO_VALUE_STORED]
    explained = checked - sum(counts[s] for s in FAILING_STATES)
    print(f"\n  rows carrying a number      : {checked:,}")
    print(f"  derivable from their own quote: {explained:,} "
          f"({100.0 * explained / max(1, checked):.1f}% of those)")
    print(f"  current / superseded          : "
          f"{sum(1 for r in rows if r['is_current'])} / "
          f"{sum(1 for r in rows if not r['is_current'])}")

    # How strong is an exact match, really? A quote holding one quantity pins the
    # value; a quote holding six is merely CONSISTENT with it. Reported because
    # "exact_digit_match" otherwise reads as stronger evidence than it is.
    unique = counts["exact_uniquely_attributable"]
    among = counts["exact_among_several_quantities"]
    print(f"\n  of the {unique + among:,} exact matches:")
    print(f"    quote holds ONE quantity — uniquely attributable : {unique:>5}")
    print(f"    quote holds several — consistent, not pinned     : {among:>5}  "
          f"({100.0 * among / max(1, unique + among):.1f}%)")
    print("    The second group is not a defect list. It is the honest ceiling of a")
    print("    check that matches numbers rather than reading clauses: the stored")
    print("    value appears in its source, but so do others.")

    if args.show_evidence:
        print("\n=== evidence for a sample of derived rows (audit these) ===")
        shown: Counter = Counter()
        for row in rows:
            state = row["_result"]["state"]
            if state in (UNEXPLAINED, NO_VALUE_STORED, "exact_digit_match"):
                continue
            if shown[state] >= 5:
                continue
            shown[state] += 1
            evidence = next((f["evidence"] for f in row["_result"]["fields"].values()
                             if f["evidence"]), None)
            text = (row["source_text"] or "")[:90].encode("ascii", "replace").decode()
            print(f"  [{state}] id={row['id']} {row['lga']}/{row['control_type']} "
                  f"min={row['value_min']} max={row['value_max']} {row['unit']}")
            print(f"      matched: {evidence}")
            print(f"      quote  : {text!r}")

    repo = Path(__file__).resolve().parents[1]
    current = {row["id"]: fingerprint(row) for row in failing}
    valueless_ids = {row["id"] for row in rows
                     if row["_result"]["state"] == NO_VALUE_STORED}
    baseline = load_baseline(repo, args.baseline)
    known = {int(k): v for k, v in (baseline.get("accepted") or {}).items()}

    if args.write_baseline:
        # Without this, the one command offered to fix a shrink failure would also
        # silently absorb any NEW finding present at the same moment — turning the
        # remedy into the bypass.
        growth = sorted(cid for cid, digest in current.items()
                        if known.get(cid) != digest)
        if growth and not args.allow_growth:
            print(f"ERROR: --write-baseline would ACCEPT {len(growth)} rows that are "
                  f"not in the baseline, or whose value or quote has changed since "
                  f"they were accepted: {growth}. That is not a ratchet, it is a "
                  f"bypass. Fix the data or add the rule; pass --allow-growth only "
                  f"with a reason recorded in the PR.", file=sys.stderr)
            return 2
        write_baseline(repo, args.baseline, current,
                       valueless_ids)
        return 0
    # A row is unknown when its id is absent from the baseline OR its value, unit
    # or quote has changed since it was accepted there.
    unknown = [row for row in failing if known.get(row["id"]) != current[row["id"]]]
    # Only a CURRENT row can block. A superseded control is not served, so failing
    # CI on one would block a release over historical data — but it is still
    # reported, because silently dropping it would shrink the check's coverage
    # without saying so.
    # `is False`, not falsy: is_current is NOT NULL today, but if that ever
    # changed a NULL would read as superseded and quietly stop blocking. Fail
    # closed — anything that is not explicitly superseded can block.
    new = [row for row in unknown if row["is_current"] is not False]
    new_superseded = [row for row in unknown if row["is_current"] is False]
    fixed = sorted(set(known) - set(current))

    print(f"\n=== baseline ===")
    print(f"  accepted rows in the baseline : {len(known)}")
    print(f"  failing now                   : {len(current)}  "
          f"({sum(1 for r in failing if r['is_current'])} current, "
          f"{sum(1 for r in failing if not r['is_current'])} superseded)")
    print(f"  NEW and current — BLOCKING    : {len(new)}")
    print(f"  NEW but superseded — advisory : {len(new_superseded)}")
    print(f"  fixed since the baseline      : {len(fixed)}")

    if new_superseded:
        print(f"\n  advisory: {len(new_superseded)} superseded rows are unsupported "
              f"by their own quote — {[r['id'] for r in new_superseded]}. Not "
              f"blocking, because they are not served.")

    if new:
        print(f"\n=== NEW unexplained rows (first {args.limit_print}) ===")
        for row in new[:args.limit_print]:
            text = (row["source_text"] or "")[:110].encode("ascii", "replace").decode()
            print(f"  id={row['id']} {row['lga']}/{row['control_type']} "
                  f"min={row['value_min']} max={row['value_max']} unit={row['unit']}")
            print(f"      {text!r}")
        print(f"\nFAILED: {len(new)} CURRENT control values are not derivable from "
              f"their own source text and are not in the baseline.\nEither correct "
              f"the value, correct the quote, or — if this is a derivation the rules "
              f"do not yet name — add the rule. Do NOT widen the baseline to make "
              f"this pass.", file=sys.stderr)
        return 1

    # A control that used to carry a number and now carries none is not "nothing
    # to check" — it is a lost value. Compared as a SET: a count would sit still
    # while one row lost its value and another gained one, hiding the loss.
    accepted_valueless = baseline.get("valueless_rows")
    if accepted_valueless is not None:
        newly_blank = sorted(valueless_ids - set(accepted_valueless))
        if newly_blank:
            print(f"\nFAILED: {len(newly_blank)} controls now record no number at "
                  f"all that previously did — {newly_blank}.\nA value that "
                  f"disappeared reads as 'nothing to check' and would otherwise "
                  f"pass silently. Confirm the blanks are intentional, then re-run "
                  f"with --write-baseline.", file=sys.stderr)
            return 1

    if fixed:
        # This FAILS rather than advising. A baseline that is never made to shrink
        # is not a ratchet: a repaired row stays permanently accepted, so if its
        # old value is ever restored the gate stays green. Recording the shrink in
        # the same change that earned it is the point.
        print(f"\nFAILED: {len(fixed)} rows in the baseline are now explained and "
              f"must be removed from it — {fixed}.\nThe baseline is shrink-only: a "
              f"row left in it stays accepted forever, so restoring its old value "
              f"later would not fail.\nRun: python scripts/"
              f"validate_control_source_values.py --write-baseline",
              file=sys.stderr)
        return 1

    print("\nPASSED: every control value is either derivable from its own source "
          "text by a named rule, or already accepted in the baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
