#!/usr/bin/env python3
# prior-art-checked: reuse not viable because the three existing pieces answer
# "is this VALUE right?" and this answers "can this ROW be regenerated or
# re-checked at all?" — a different question with a different failure mode.
#   * services/extracted_data_integrity.py — fabricated/conflicting/absent VALUE
#     checks. Imported and reused here (value_absent_from_source) rather than
#     reimplemented; it cannot answer provenance because it never looks at the repo.
#   * scripts/validate_dcp_setbacks.py — setback SEMANTICS (conflict, foreign
#     language, magnitude, placeholder). Complementary: a row can pass every
#     semantic check and still be unattributable.
#   * scripts/validate_zone_code_validity.py — the ground-truth-set pattern this
#     follows (load truth from outside the row, never parse the row's own claim).
# No migration and no new column: every state is DERIVED from columns that already
# exist, so it cannot go stale the way a stored flag would. `needs_review` was
# considered and rejected — it is already consumed by four production routes
# (dcp/structured-controls, capacity/calculate, tod/parking-rates,
# internal/setback-review) and repurposing it would change served output.
"""Provenance status for every row in ``dcp_setback_controls``.

WHY THIS EXISTS
---------------
The 1,069 numeric controls are the part of the corpus that organised retrieval
cannot produce. That makes them the asset — and an asset nobody can audit is
indistinguishable from a guess. If a DCP is amended you must be able to say, per
row, "this one a script regenerates" or "this one was typed by a human, here is
the clause to re-check it against". A row that supports neither statement is
unattributed, and unattributed is the state this exists to make impossible.

THE THREE STATES — every row lands in exactly one
-------------------------------------------------
(a) REPRODUCIBLE  — the row's ``source_text`` appears verbatim as a string literal
                    in a committed file that writes this table. Re-running that
                    file regenerates the row, so the value is reproducible from
                    the repository alone.
(b) TRACEABLE     — no committed literal, but the row carries both ``source_text``
                    and ``section_ref``, so it can be re-checked against its
                    clause when the DCP changes.
(c) UNVERIFIABLE  — neither. Nothing in the database or the repo says where the
                    number came from. This is the only state that FAILS.

WHY (a) IS NOT "extraction_method SAYS pipeline"
------------------------------------------------
Measured 2026-08-02: ``extraction_method`` and actual reproducibility are close to
uncorrelated. 330 rows labelled ``text_extraction``/``mistral_ocr`` have no
committed literal, while 177 rows labelled ``manual``/``manual_curation`` do. The
label is what a writer *claimed*, and one writer (insert_inner_west_landscaping.py)
stamps ``text_extraction`` onto hand-typed dict literals while
update_needs_review_controls.py overwrites the column outright. So the label is
read and REPORTED, never trusted as the state. Ground truth is the repo.

Note carefully what (a) does and does not prove. A verbatim literal proves the row
is regenerable. Its ABSENCE does not prove a row is unreproducible — a genuine
PDF-extraction pipeline holds no hardcoded text — which is exactly why a
label/reality mismatch is advisory output and not a failure. Confirming those rows
would mean re-running extraction over council PDFs, which
docs/EXTRACTION_WHY_IT_RECURS_AND_THE_DURABLE_FIX_2026-07.md exists to stop.

EXIT CODES — three states here too
----------------------------------
0 = every row carries a provenance state.
1 = at least one row is UNVERIFIABLE (state c).
2 = the check could not run (no DATABASE_URL, table missing, no writer files
    found). Nothing was verified, which is reported as a failure and never a pass.
"""
from __future__ import annotations

import argparse
import ast
import glob
import json
import os
import sys
from collections import Counter, defaultdict
from typing import Iterable

# Files that may legitimately hold a row's source text as a literal. Kept as globs
# rather than a hand-listed set so a new insert_*.py is picked up automatically —
# a list would silently go stale and quietly demote rows to state (b).
WRITER_GLOBS = ("scripts/*.py", "enrichment/extractors/*.py", "enrichment/*.py")

# A literal shorter than this matches too loosely to prove anything ("Table 4",
# "6.0m"). Set from the observed minimum real source_text length (30 chars) less a
# small margin; raising it costs recall, lowering it invents attribution.
MIN_LITERAL_CHARS = 25

STATE_REPRODUCIBLE = "reproducible"
STATE_TRACEABLE = "traceable"
STATE_UNVERIFIABLE = "unverifiable"
STATES = (STATE_REPRODUCIBLE, STATE_TRACEABLE, STATE_UNVERIFIABLE)


def _present(value) -> bool:
    """True only for a non-empty, non-whitespace string."""
    return bool(str(value or "").strip())


def harvest_committed_literals(root: str = ".") -> dict[str, set[str]]:
    """Map every long string literal in a table-writing file -> the files holding it.

    Parsed with ``ast`` rather than grepped: a regex over source picks up the same
    text inside comments and docstrings, which would attribute a row to a file
    that only *mentions* it. Only real ``ast.Constant`` strings count.
    """
    out: dict[str, set[str]] = defaultdict(set)
    seen: set[str] = set()
    for pattern in WRITER_GLOBS:
        for path in glob.glob(os.path.join(root, pattern)):
            real = os.path.realpath(path)
            if real in seen:
                continue
            seen.add(real)
            try:
                src = open(path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if TABLE not in src:
                continue
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            for node in ast.walk(tree):
                if (isinstance(node, ast.Constant)
                        and isinstance(node.value, str)
                        and len(node.value) >= MIN_LITERAL_CHARS):
                    out[node.value.strip()].add(rel)
    return out


def classify_rows(rows: Iterable[dict],
                  literals: dict[str, set[str]]) -> list[dict]:
    """Assign exactly one provenance state to every row.

    Pure logic and DB-free so the failing case can be exercised directly: pass a
    row with no source_text and no section_ref and it must come back
    ``unverifiable``.
    """
    results: list[dict] = []
    for row in rows:
        source = (row.get("source_text") or "").strip()
        files = literals.get(source) if source else None
        if files:
            state, evidence = STATE_REPRODUCIBLE, sorted(files)[0]
        elif _present(source) and _present(row.get("section_ref")):
            state, evidence = STATE_TRACEABLE, str(row.get("section_ref")).strip()
        else:
            state = STATE_UNVERIFIABLE
            missing = [name for name in ("source_text", "section_ref")
                       if not _present(row.get(name))]
            evidence = "missing: " + ", ".join(missing or ["committed literal"])
        results.append({
            "id": row.get("id"),
            "lga": row.get("lga"),
            "control_type": row.get("control_type"),
            "claimed_method": row.get("extraction_method"),
            "is_current": row.get("is_current"),
            "state": state,
            "evidence": evidence,
        })
    return results


def label_reality_mismatches(classified: list[dict]) -> dict[str, int]:
    """Rows whose ``extraction_method`` disagrees with the derived state.

    ADVISORY. Reported so the gap between the label and reality stays visible
    instead of being quietly absorbed by the pass/fail line.
    """
    pipeline = {"text_extraction", "mistral_ocr"}
    handmade = {"manual", "manual_curation"}
    counts = Counter()
    for row in classified:
        method = row["claimed_method"] or "(NULL)"
        if method in pipeline and row["state"] != STATE_REPRODUCIBLE:
            counts["labelled_pipeline_but_no_committed_literal"] += 1
        elif method in handmade and row["state"] == STATE_REPRODUCIBLE:
            counts["labelled_manual_but_a_script_regenerates_it"] += 1
    return dict(counts)


def _connect():  # pragma: no cover - thin DB shim, exercised by main()
    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set — nothing was checked, which is not a "
              "pass. Exiting 2.", file=sys.stderr)
        sys.exit(2)
    import psycopg2

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")
    return conn, cur


# Declared beside the query that uses it. The SELECT below carries `is_current` so
# the report can say whether an unattributed row is served now or merely held; it
# is deliberately NOT filtered on, because a superseded row still needs a state.
TABLE = "dcp_setback_controls"


def _fetch_rows(cur) -> list[dict]:  # pragma: no cover - exercised by main()
    # Read-only. `is_current` is SELECTed but deliberately not filtered on: a
    # superseded row still needs a provenance state, or it comes back unattributed
    # the moment it is reinstated. It is carried so the report can say whether an
    # unattributed row is being served right now or merely held.
    cur.execute(
        f"""SELECT id, lga, dev_type, control_type, value_min, value_max, unit,
                   source_text, section_ref, extraction_method, is_current
            FROM {TABLE}"""
    )
    columns = [d[0] for d in cur.description]
    return [dict(zip(columns, r)) for r in cur.fetchall()]


def main() -> int:  # pragma: no cover - CLI entry point
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true",
                        help="Summary lines only; omit the per-row listing.")
    parser.add_argument("--json", action="store_true",
                        help="Emit the full classification as JSON.")
    parser.add_argument("--root", default=".",
                        help="Repository root to harvest committed literals from.")
    args = parser.parse_args()

    literals = harvest_committed_literals(args.root)
    if not literals:
        print(f"ERROR: no writer files found under {args.root!r} — every row would "
              f"be misreported as unattributable. Nothing was verified. Exiting 2.",
              file=sys.stderr)
        return 2

    conn, cur = _connect()
    try:
        rows = _fetch_rows(cur)
    finally:
        conn.close()
    if not rows:
        print(f"ERROR: {TABLE} returned no rows — the check cannot pass on an "
              f"empty read. Exiting 2.", file=sys.stderr)
        return 2

    classified = classify_rows(rows, literals)
    counts = Counter(r["state"] for r in classified)
    unverifiable = [r for r in classified if r["state"] == STATE_UNVERIFIABLE]

    if args.json:
        print(json.dumps({"counts": dict(counts), "rows": classified}, indent=2))
    else:
        print(f"\n=== {TABLE} provenance ({len(rows):,} rows) ===")
        for state in STATES:
            print(f"  {state:<14} {counts[state]:>5}")
        mismatches = label_reality_mismatches(classified)
        if mismatches:
            print("\n  advisory — extraction_method vs derived state:")
            for key, n in sorted(mismatches.items()):
                print(f"    {key:<48} {n:>5}")
            print("    (a label is what a writer claimed; the state is what the "
                  "repo and the row can prove)")
        if unverifiable and not args.quiet:
            print(f"\n  UNVERIFIABLE rows — no provenance of any kind:")
            served = sum(1 for r in unverifiable if r.get("is_current"))
            print(f"    of these, {served} are is_current (served now) and "
                  f"{len(unverifiable) - served} are superseded — both must still "
                  f"carry a state")
            for row in unverifiable[:50]:
                print(f"    id={row['id']} {row['lga']}/{row['control_type']} "
                      f"method={row['claimed_method']} "
                      f"current={row.get('is_current')} — {row['evidence']}")
            if len(unverifiable) > 50:
                print(f"    ... and {len(unverifiable) - 50} more")

    if unverifiable:
        print(f"\nFAILED: {len(unverifiable)} row(s) carry no provenance state.",
              file=sys.stderr)
        return 1
    print(f"\nPASSED: every one of {len(rows):,} rows carries a provenance state.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
