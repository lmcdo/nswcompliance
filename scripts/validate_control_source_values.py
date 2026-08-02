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

    no_value_stored       the row records a rule with no number (nothing to check;
                          NOT a pass — it is counted separately and reported)
    exact_digit_match     the number is literally in the quote
    percentage_phrasing   '35%' stored as 35 or 0.35
    unit_conversion       '900mm' stored as 0.9 m
    ratio_or_rate         '1 space per 4 dwellings' stored as 0.25
    area_from_dimensions  '3m x 3m' stored as 9
    written_numeral       'three hours' stored as 3
    UNEXPLAINED           <- the finding

Every explanation carries the substring it matched, printed with `--show-evidence`.
A rule that could not show its evidence would be a shrug with a name on it.

WHY IT CAN FAIL
---------------
The project's standing lesson is that a check which cannot go red is not a
verification (DQ-30's "0% drift" compared the data to the code that produced it).
This one can go red two ways: a NEW unexplained row fails the baseline, and a row
whose stored number is edited to something its quote does not support becomes
unexplained on the next run. The baseline is shrink-only — fixing rows lowers the
ceiling and it never rises without an explicit --write-baseline.

WHAT IT DOES NOT PROVE
----------------------
That the number is CORRECT. It proves the number is consistent with the sentence
stored beside it. If the quote itself was mis-transcribed, both agree and this
passes — that failure mode belongs to the extraction gates, not here.
"""
from __future__ import annotations

import argparse
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


def load_baseline(repo: Path, path: str | None) -> dict:
    """The accepted unexplained rows. A missing file is an empty baseline.

    An UNREADABLE file is not: a corrupt baseline that silently became empty would
    turn every pre-existing row into a new failure, and the natural response to
    that noise is to regenerate the baseline — which is how a gate gets disarmed.
    """
    p = repo / (path or DEFAULT_BASELINE)
    if not p.exists():
        return {"ids": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: baseline {p} is unreadable ({exc}). Refusing to run rather "
              f"than treating it as empty.", file=sys.stderr)
        raise SystemExit(2)


def write_baseline(repo: Path, path: str | None, ids: list[int]) -> None:
    p = repo / (path or DEFAULT_BASELINE)
    p.write_text(
        json.dumps({
            "note": "Control ids whose stored value no named rule derives from "
                    "their own source_text. Shrink-only: fixing a row lowers this "
                    "ceiling. Adding to it requires an explicit --write-baseline "
                    "and should carry a reason in the PR.",
            "count": len(ids),
            "ids": sorted(ids),
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Baseline written to {p} ({len(ids)} unexplained rows).")


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
                    help="Rewrite the baseline from the current findings. Use once, "
                         "deliberately — it raises the accepted ceiling.")
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
    ids = [row["id"] for row in failing]
    if args.write_baseline:
        write_baseline(repo, args.baseline, ids)
        return 0

    baseline = load_baseline(repo, args.baseline)
    known = set(baseline.get("ids") or [])
    unknown = [row for row in failing if row["id"] not in known]
    # Only a CURRENT row can block. A superseded control is not served, so failing
    # CI on one would block a release over historical data — but it is still
    # reported, because silently dropping it would shrink the check's coverage
    # without saying so.
    # `is False`, not falsy: is_current is NOT NULL today, but if that ever
    # changed a NULL would read as superseded and quietly stop blocking. Fail
    # closed — anything that is not explicitly superseded can block.
    new = [row for row in unknown if row["is_current"] is not False]
    new_superseded = [row for row in unknown if row["is_current"] is False]
    fixed = sorted(known - set(ids))

    print(f"\n=== baseline ===")
    print(f"  accepted rows in the baseline : {len(known)}")
    print(f"  failing now                   : {len(ids)}  "
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

    if fixed:
        print(f"\n  {len(fixed)} baseline rows are now explained. The baseline is "
              f"shrink-only: re-run with --write-baseline to lower the ceiling.")

    print("\nPASSED: every control value is either derivable from its own source "
          "text by a named rule, or already accepted in the baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
