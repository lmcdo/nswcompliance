#!/usr/bin/env python3
# prior-art-checked: reuse not viable because all six surfaces the guard names
# are CONSUMERS that render or filter a stored confidence value; none reads the
# distribution of the underlying evidence fields. scripts/lint_hardcoded_
# confidence.py is a source-text lint, not a DB measurement. This asks a
# question no existing script asks: given a stored row, which of the four
# candidate badge states can actually be told apart?
"""Measure which granny-flat report states are DISTINGUISHABLE in production data.

Read-only. Supports the badge-wording change (calibration plan §4e item 3):
the four candidate states are only worth serving if the stored row can tell
them apart. Prints the evidence for each row so a claim can cite a query.

Candidate states:
  A  reviewed   — a person classified every detected secondary structure and
                  the resulting total matches the detector
  B  scan-only, structures found — detector found secondary structures,
                  nobody classified them
  C  scan-only, nothing found    — detector ran and found no secondary structure
  D  not assessed                — the scan did not run, failed, or the detect
                  record could not be resolved

Usage:  python scripts/measure_granny_confidence_states.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from dotenv import load_dotenv  # noqa: E402

# A git worktree has no .env of its own; creds live in the main checkout root.
# Explicit paths only — a bare load_dotenv() silently picks up whichever .env
# is nearest the CWD, which is how a worktree run ends up on the wrong DB.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _candidate in (
    os.path.join(_HERE, "..", ".env"),                      # normal checkout
    os.path.join(_HERE, "..", "..", "..", "..", ".env"),    # .claude/worktrees/<n>/
):
    if os.path.exists(_candidate):
        load_dotenv(_candidate)
        print(f"[env] loaded {os.path.normpath(_candidate)}")
        break
else:
    raise SystemExit("No .env found — refusing to fall back to localhost defaults.")

for _pg, _db in (
    ("PGHOST", "DB_HOST"), ("PGUSER", "DB_USER"), ("PGPASSWORD", "DB_PASSWORD"),
    ("PGDATABASE", "DB_NAME"), ("PGPORT", "DB_PORT"),
):
    if os.environ.get(_pg) and not os.environ.get(_db):
        os.environ[_db] = os.environ[_pg]
os.environ.setdefault("PGSSLMODE", "require")

from db_config import get_connection  # noqa: E402


def main() -> None:
    conn = get_connection()
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()

    print("=== 1. Row census by stored `confidence` value ===")
    cur.execute("""
        SELECT COALESCE(confidence, '<NULL>') AS confidence, COUNT(*)
        FROM granny_flat_reports
        GROUP BY 1 ORDER BY 2 DESC
    """)
    for conf, n in cur.fetchall():
        print(f"  {conf:<18} {n}")

    print("\n=== 2. Completed rows — the fields that would drive a state ===")
    cur.execute("""
        SELECT id, run_date, confidence,
               inputs->>'confirmed_count_source'        AS count_source,
               inputs->>'confirmed_count_source_note'   AS note,
               inputs->>'detect_id'                     AS detect_id,
               jsonb_array_length(COALESCE(inputs->'structure_types', '[]'::jsonb))     AS n_answers,
               jsonb_array_length(COALESCE(inputs->'detected_structures', '[]'::jsonb)) AS n_detected_in,
               inputs ? 'detected_structures'           AS has_detected_key,
               -- NOTE: the counts live in `inputs`, NOT `outputs`. Reading them
               -- from outputs returns NULL for every row and makes it look like
               -- no report ever carried a count. Verified 2026-08-06.
               inputs->>'samgeo_structure_count'        AS samgeo_count,
               inputs->>'confirmed_structure_count'     AS confirmed_count,
               outputs->>'samgeo_validated'             AS validated,
               jsonb_array_length(COALESCE(outputs->'detected_structures', '[]'::jsonb)) AS n_detected_out
        FROM granny_flat_reports
        WHERE confidence IN ('high', 'medium', 'low')
        ORDER BY run_date DESC, id
    """)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    print(f"  {len(rows)} completed rows")
    for r in rows:
        d = dict(zip(cols, r))
        print(
            f"  {str(d['id'])[:8]} {d['run_date']} conf={d['confidence']:<6} "
            f"src={str(d['count_source']):<32} answers={d['n_answers']} "
            f"det_in={d['n_detected_in']}(key={d['has_detected_key']}) "
            f"det_out={d['n_detected_out']} samgeo={d['samgeo_count']} "
            f"confirmed={d['confirmed_count']} validated={d['validated']}"
        )
        if d["note"]:
            print(f"           note: {d['note']}")

    print("\n=== 3. Is `samgeo_structure_count` a TOTAL or a SECONDARY count? ===")
    print("    (compare it against the detected_structures array + is_main_dwelling flags)")
    cur.execute("""
        SELECT id, confidence,
               outputs->>'samgeo_structure_count' AS samgeo_count,
               outputs->'detected_structures'     AS det_out,
               inputs->'detected_structures'      AS det_in
        FROM granny_flat_reports
        WHERE outputs ? 'detected_structures' OR inputs ? 'detected_structures'
        ORDER BY run_date DESC
        LIMIT 25
    """)
    for rid, conf, samgeo, det_out, det_in in cur.fetchall():
        det = det_out or det_in or []
        mains = sum(1 for s in det if isinstance(s, dict) and s.get("is_main_dwelling"))
        print(f"  {str(rid)[:8]} conf={str(conf):<14} samgeo_count={samgeo} "
              f"len(detected)={len(det)} is_main_dwelling=True count={mains} "
              f"secondary={len(det) - mains}")

    print("\n=== 4. pending_confirm / error / NULL rows — what state D looks like ===")
    cur.execute("""
        SELECT COALESCE(confidence, '<NULL>') AS confidence, COUNT(*),
               COUNT(*) FILTER (WHERE outputs IS NULL) AS outputs_null,
               COUNT(*) FILTER (WHERE outputs ? 'detected_structures') AS has_det,
               COUNT(*) FILTER (WHERE outputs ? 'error') AS has_error
        FROM granny_flat_reports
        WHERE confidence IS NULL OR confidence NOT IN ('high', 'medium', 'low')
        GROUP BY 1 ORDER BY 2 DESC
    """)
    for row in cur.fetchall():
        print(f"  {row[0]:<18} n={row[1]} outputs_null={row[2]} "
              f"has_detected_structures={row[3]} has_error={row[4]}")

    print("\n=== 5. DISTINGUISHABILITY: can C (found nothing) be told from D (no record)? ===")
    cur.execute("""
        SELECT
          COUNT(*) FILTER (WHERE inputs->>'samgeo_structure_count' IS NULL)  AS samgeo_null,
          COUNT(*) FILTER (WHERE inputs->>'samgeo_structure_count' = '0')    AS samgeo_zero,
          COUNT(*) FILTER (WHERE inputs->>'samgeo_structure_count' = '1')    AS samgeo_one,
          COUNT(*) FILTER (WHERE (outputs->>'samgeo_validated') = 'false')   AS not_validated,
          COUNT(*) FILTER (WHERE NOT (outputs ? 'detected_structures')
                             AND NOT (inputs ? 'detected_structures'))       AS no_detected_key,
          COUNT(*) FILTER (WHERE inputs ? 'confirmed_count_source')          AS has_count_source,
          COUNT(*)                                                           AS total
        FROM granny_flat_reports
        WHERE confidence IN ('high', 'medium', 'low')
    """)
    (samgeo_null, samgeo_zero, samgeo_one, not_validated,
     no_det_key, has_src, total) = cur.fetchone()
    print(f"  completed rows: {total}")
    print(f"    samgeo_structure_count IS NULL        : {samgeo_null}")
    print(f"    samgeo_structure_count = 0            : {samgeo_zero}")
    print(f"    samgeo_structure_count = 1 (main only): {samgeo_one}")
    print(f"    samgeo_validated = false              : {not_validated}")
    print(f"    NO detected_structures key anywhere   : {no_det_key}")
    print(f"    HAS confirmed_count_source (post-#878): {has_src}")

    print("\n=== 5b. Frozen reason strings — what a re-pulled PDF serves TODAY ===")
    cur.execute("""
        SELECT COUNT(*) FILTER (WHERE outputs->>'confidence_reason' ILIKE '%you confirmed%'),
               COUNT(*) FILTER (WHERE outputs->>'confidence_reason' ILIKE '%counts agree%'),
               COUNT(*) FILTER (WHERE outputs->>'confidence_reason' ILIKE '%AI detected%'),
               COUNT(*)
        FROM granny_flat_reports WHERE confidence IN ('high', 'medium', 'low')
    """)
    you_conf, agree, ai_det, tot = cur.fetchone()
    print(f"  of {tot} completed rows, stored confidence_reason contains:")
    print(f"    'you confirmed' : {you_conf}")
    print(f"    'counts agree'  : {agree}")
    print(f"    'AI detected'   : {ai_det}")

    print("\n=== 6. The nearby-comparables filter — how many rows does confidence='high' gate? ===")
    cur.execute("""
        SELECT COUNT(*) FROM granny_flat_reports
        WHERE confidence = 'high'
          AND (outputs->>'granny_flat_buildable')::boolean IS TRUE
    """)
    print(f"  rows currently servable to /api/reports/granny-flat/nearby: {cur.fetchone()[0]}")

    print("\n=== 7. property_reports (the [report_id] shared surface reads THIS table) ===")
    cur.execute("""
        SELECT COALESCE(confidence, '<NULL>'), COUNT(*)
        FROM property_reports WHERE product = 'granny-flat'
        GROUP BY 1 ORDER BY 2 DESC
    """)
    pr = cur.fetchall()
    if not pr:
        print("  0 rows with product='granny-flat'")
    for conf, n in pr:
        print(f"  {conf:<18} {n}")

    print("\n=== 8. BLAST RADIUS: what every existing report says, before -> after ===")
    print("    (applies the shipped _review_state to each stored row)")
    sys.path.insert(0, os.path.join(_HERE, ".."))
    from services.granny_flat import _review_state  # noqa: E402

    cur.execute("""
        SELECT id, confidence,
               inputs->>'confirmed_count_source' AS count_source,
               inputs->>'samgeo_structure_count' AS samgeo_count,
               COALESCE(outputs->'detected_structures', inputs->'detected_structures') AS det,
               outputs->>'confidence_reason' AS reason
        FROM granny_flat_reports
        WHERE confidence IN ('high', 'medium', 'low')
        ORDER BY confidence, id
    """)
    from collections import Counter
    before = Counter()
    after = Counter()
    pairs = Counter()
    for _rid, conf, src, samgeo, det, _reason in cur.fetchall():
        machine = int(samgeo) if samgeo is not None else None
        state, label, _detail = _review_state(
            validated=True,
            count_source=src or "unrecorded",
            detected_structures=det if isinstance(det, list) else None,
            machine_count=machine,
        )
        before[f"{conf} confidence"] += 1
        after[label] += 1
        pairs[(conf, state)] += 1

    print("  BEFORE (the grade a customer saw):")
    for k, n in before.most_common():
        print(f"    {n:>3}  {k}")
    print("  AFTER (what the report will say happened):")
    for k, n in after.most_common():
        print(f"    {n:>3}  {k}")
    print("  transitions:")
    for (conf, state), n in sorted(pairs.items()):
        print(f"    {n:>3}  {conf:<7} -> {state}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
