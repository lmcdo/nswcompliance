#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no committed script executes this
# adjudication. The SAFETY shape (dry-run default, backup table asserting every
# planned id, per-row guard on values read at plan time, printed rollback) is
# copied from scripts/repair_camden_front_setbacks.py and
# scripts/refile_secondary_street_setbacks.py; the INSERT shape (dup-check,
# verbatim source_text + section_ref) from scripts/insert_wingecarribee_setbacks.py.
# The rulings are new and documented in docs/qa/controls-adjudication-2026-08.md.
"""Execute the MISSING_PRIMARY adjudication: 8 guarded updates + 2 inserts.

DQ-40's MISSING_PRIMARY analysis found rows standing in for controls that are
stored nowhere — invisible to every gate, because a gate cannot check a row that
does not exist. Every ruling below was made against the source PDF in
data/dcps/ (evidence STRONG), never inferred from another clause. Rule 2b: any
write that changes what a value means carries the quote supporting the new
meaning in the same statement.

RYDE (first, per authorisation) — ryde-part3.3-dwelling-houses.pdf
  * INSERT front_setback/dwelling_house 6.0 m — s2.9.1(a) printed p.25:
    "Dwellings are generally to be set back 6 m from the street front
    boundary." Ryde's general front setback was stored NOWHERE; the only
    served front row (680) carried a rear-boundary quote.
  * 680: re-filed front_setback -> rear_setback. Its own (400-char truncated)
    quote is s2.9.3(a) printed p.28 — the general rear control, whose fixed
    floor is 8 m ("25% of the length of the site or 8 m, whichever is the
    greater"). Value unchanged; quote replaced with the full clause.
  * 681 (rear 4.0): quote replaced with the exact clause its value comes from
    — s2.9.3(b), the wider-than-long exception — and conditioned so the
    exception stops reading as the rule.
  * 682 (side 4.0): needs_review=TRUE, fail closed. Its quote is a design
    PREFERENCE ("a minimum side setback of 4 m is preferred" for northerly
    aspects); the actual general side control is s2.9.2(a)/(b) 900mm one
    storey / 1.5m two storey, stored nowhere. Extraction of the general rows
    is a follow-up needing authorisation; meanwhile a preference must not be
    served as a requirement.

CAMDEN — camden-part4-residential-dwelling-controls.pdf
  * 691 (side 0.9): value matches the general control, quote was the wrong
    clause (zero-lot-line rear-yard ACCESS rule). Quote replaced with the
    Table 4-2 side-setback row (printed P4-8), same convention as rows
    1063/1064. The general side control now exists with its own evidence.

BURWOOD — burwood-part4-residential.pdf
  * INSERT side_setback/dwelling_house 0.9-1.5 m — Ch 4 s4.5 Table 3 printed
    p.221: single storey 900mm, second-storey component 1.5m. Range-row shape
    follows existing burwood row 1080 (rear 3-6). The general side control was
    stored nowhere.
  * 707 (side 0.9, P10 garage-wall quote): conditioned as the ancillary-
    structure control its own quote candidly describes. Value untouched.

FAIRFIELD — fairfield-ch5-dwelling-houses.pdf. All three secondary_dwelling
rows carried quotes from Chapter 5C "Dwelling Houses on NARROW LOTS" (printed
p.189), not Chapter 5B "Secondary Dwellings". 5B.2.3.1 (printed p.176) is
exhaustive for granny-flat setbacks: side AND rear 900mm, 1.8m separation,
corner secondary-street 1.5m — and prescribes NO front setback.
  * 714 (front 6.0): RETIRED, camden-692 model. The 6m is 5C.2.3.1(b), a
    garage setback for narrow-lot dwelling houses. Fairfield prescribes no
    numeric front setback for secondary dwellings, so there is no correct
    value to substitute.
  * 715 (side 0.9): value matches 5B.2.3.1(a); quote replaced with that
    clause (was 5C.2.3.2(a), a different chapter's control).
  * 716 (rear 6.0): needs_review=TRUE, fail closed. 5B.2.3.1(a) prescribes
    900mm rear for secondary dwellings; the stored 6.0 is 5C.2.3.3 (first-
    floor walls, narrow lots). Evidence for a 0.9 repair is STRONG but a value
    change was not authorised for this row; flagged rather than left serving.

NOT touched (documented in the adjudication doc): city_of_sydney 884 (source
prescribes no numeric side setback — nothing to add without inventing);
georges_river 229, campbelltown 256/257 (their quotes ARE the general rule —
detector heuristic false positives, fixed detector-side); cumberland 34
(corner scope is inherent in secondary_street_setback).

SAFETY: dry-run default; backup table asserting every planned update id;
per-row guards on the pre-state read at plan time (IS NULL for nullable
pre-states, never = NULL); single transaction for all writes; rollback SQL
printed, including DELETEs for the inserted rows.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

STAMP = "[adjudicated 2026-08-03]"

# --- UPDATE plan -----------------------------------------------------------
# (id, guard_sql_fragment, guard_params, set_sql_fragment, set_params,
#  review_reason, label, post_guard_sql_fragment, verify_stamp)
# Guards compare against the pre-state read during planning (recon 2026-08-03).
# post_guard proves a skipped row actually reached its intended post-state —
# "not pre-state" alone also matches a row broken a third way, and calling
# that done would be a silent failure (Sol finding, 2026-08-03).
# verify_stamp: last_verified_at is set ONLY where the stored content was
# verified against source in this pass. A needs_review flag or a retirement is
# not a verification (the camden-692 doctrine; Sol finding, 2026-08-03).

RYDE_680_QUOTE = (
    "a. The rear of the dwelling is to be set back from the rear boundary a "
    "minimum distance of 25% of the length of the site or 8 m, whichever is "
    "the greater."
)
RYDE_680_COND = (
    "General rear setback: 25% of the length of the site or 8m, whichever is "
    "the greater - 8.0 is the fixed floor; the 25% term exceeds it on sites "
    "longer than 32m. Wider-than-long allotments: 4m (s2.9.3(b), stored "
    "separately). Battle-axe allotments: 8m from the rear boundary of the "
    "front allotment (s2.9.3(c), NOT stored)."
)
RYDE_681_QUOTE = (
    "b. Allotments which are wider than they are long, and so cannot achieve "
    "the minimum rear setback requirement, are to have a minimum rear setback "
    "of 4 m."
)
CAMDEN_691_QUOTE = "Camden DCP 2019 Part 4 Table 4-2: Side setback — 0.9m"
FF_715_QUOTE = (
    "a) Secondary dwellings (granny flats) require minimum side and rear "
    "setbacks of 900mm."
)

UPDATES = [
    (
        680,
        "control_type = 'front_setback' AND value_min = 8.0 AND is_current "
        "AND length(source_text) = 400 AND source_text LIKE 'a. The rear of the dwelling%%'",
        (),
        "control_type = 'rear_setback', source_text = %s, condition = %s, "
        "section_ref = 'ryde-part3.3-dwelling-houses.pdf#2.9.3(a)', pdf_page = 28",
        (RYDE_680_QUOTE, RYDE_680_COND),
        f"{STAMP} re-filed front_setback -> rear_setback: the quote is "
        f"s2.9.3(a) (printed p.28), Ryde's general rear control; 8.0 is its "
        f"fixed floor. Ryde's actual front setback (6m, s2.9.1(a)) was stored "
        f"nowhere and is inserted separately. Quote replaced in the same "
        f"write (rule 2b).",
        "ryde 680: front -> rear, full s2.9.3(a) quote",
        "control_type = 'rear_setback' AND value_min = 8.0 AND is_current "
        "AND condition LIKE 'General rear setback%%'",
        True,
    ),
    (
        681,
        "control_type = 'rear_setback' AND value_min = 4.0 AND is_current "
        "AND length(source_text) = 400 AND condition IS NULL",
        (),
        "source_text = %s, condition = 'Allotments wider than they are long "
        "which cannot achieve the general rear setback of 25%%-of-site-length "
        "or 8m (s2.9.3(b)); the general floor is stored separately.', "
        "section_ref = 'ryde-part3.3-dwelling-houses.pdf#2.9.3(b)', pdf_page = 28",
        (RYDE_681_QUOTE,),
        f"{STAMP} quote narrowed to the exact clause the 4.0 comes from — "
        f"s2.9.3(b), the wider-than-long exception (was the truncated "
        f"a+b+c block) — and conditioned so the exception stops reading as "
        f"the rule.",
        "ryde 681: s2.9.3(b) quote + condition",
        "control_type = 'rear_setback' AND value_min = 4.0 AND is_current "
        "AND condition LIKE 'Allotments wider%%'",
        True,
    ),
    (
        682,
        "control_type = 'side_setback' AND value_min = 4.0 AND is_current "
        "AND needs_review = FALSE",
        (),
        "needs_review = TRUE",
        (),
        f"{STAMP} flagged: the quote is a design PREFERENCE ('a minimum side "
        f"setback of 4 m is preferred' where a side boundary has northerly "
        f"aspect), not a requirement. Ryde's general side control is "
        f"s2.9.2(a)/(b) printed p.26 — 900mm one storey, 1.5m two storey — "
        f"stored NOWHERE. Fail closed pending extraction of the general rows.",
        "ryde 682: needs_review (preference served as control)",
        "control_type = 'side_setback' AND value_min = 4.0 AND is_current "
        "AND needs_review = TRUE",
        False,
    ),
    (
        691,
        "control_type = 'side_setback' AND value_min = 0.9 AND is_current "
        "AND source_text LIKE '%%zero lot line%%'",
        (),
        "source_text = %s, section_ref = "
        "'camden-part4-residential-dwelling-controls.pdf#table4-2', pdf_page = 11",
        (CAMDEN_691_QUOTE,),
        f"{STAMP} quote was the zero-lot-line rear-yard ACCESS rule; the "
        f"stored 0.9 matches the general Table 4-2 side setback (printed "
        f"P4-8), now quoted directly. Same convention as rows 1063/1064. "
        f"Quote replaced in the same write (rule 2b).",
        "camden 691: Table 4-2 side-setback quote",
        "control_type = 'side_setback' AND value_min = 0.9 AND is_current "
        "AND source_text LIKE 'Camden DCP 2019 Part 4 Table 4-2%%'",
        True,
    ),
    (
        707,
        "control_type = 'side_setback' AND value_min = 0.9 AND is_current "
        "AND condition IS NULL AND source_text LIKE 'P10%%'",
        (),
        "condition = 'Garage walls attached to a single dwelling (P10); the "
        "general side setback (900mm single storey / 1.5m second-storey "
        "component, Ch 4 s4.5 Table 3) is stored separately.'",
        (),
        f"{STAMP} conditioned as the garage-wall control its own quote "
        f"describes; the general side setback row is inserted separately "
        f"from Table 3.",
        "burwood 707: garage-wall condition",
        "control_type = 'side_setback' AND value_min = 0.9 AND is_current "
        "AND condition LIKE 'Garage walls%%'",
        True,
    ),
    (
        714,
        "control_type = 'front_setback' AND value_min = 6.0 AND is_current "
        "AND source_text LIKE 'b) Garage(s)%%'",
        (),
        "is_current = FALSE",
        (),
        f"{STAMP} retired: the 6m is 5C.2.3.1(b) — a garage setback from "
        f"Chapter 5C 'Dwelling Houses on Narrow Lots' (printed p.189), not a "
        f"secondary-dwelling control. Chapter 5B.2.3.1 (printed p.176) is "
        f"exhaustive for granny-flat setbacks (side/rear 900mm, 1.8m "
        f"separation, corner secondary street 1.5m) and prescribes NO numeric "
        f"front setback, so there is no correct value to substitute "
        f"(camden-692 model).",
        "fairfield 714: retire (no front setback exists for secondary dwellings)",
        "control_type = 'front_setback' AND value_min = 6.0 "
        "AND is_current = FALSE "
        "AND review_reason LIKE '[adjudicated 2026-08-03] retired%%'",
        False,
    ),
    (
        715,
        "control_type = 'side_setback' AND value_min = 0.9 AND is_current "
        "AND source_text LIKE 'a) One side%%'",
        (),
        "source_text = %s, section_ref = "
        "'fairfield-ch5-dwelling-houses.pdf#5B.2.3.1(a)', pdf_page = 32, "
        "condition = 'Clause covers side and rear (both 900mm). Separation to "
        "principal dwelling 1.8m (5B.2.3.1(b)) and corner secondary-street "
        "setback 1.5m (5B.2.3.1(c)) are NOT stored.'",
        (FF_715_QUOTE,),
        f"{STAMP} quote was 5C.2.3.2(a) — Chapter 5C 'Dwelling Houses on "
        f"Narrow Lots', a different chapter — while the value matches the "
        f"actual secondary-dwelling control 5B.2.3.1(a) (printed p.176), now "
        f"quoted directly. Quote replaced in the same write (rule 2b).",
        "fairfield 715: 5B.2.3.1(a) quote + condition",
        "control_type = 'side_setback' AND value_min = 0.9 AND is_current "
        "AND source_text LIKE 'a) Secondary dwellings%%'",
        True,
    ),
    (
        716,
        "control_type = 'rear_setback' AND value_min = 6.0 AND is_current "
        "AND needs_review = FALSE",
        (),
        "needs_review = TRUE",
        (),
        f"{STAMP} flagged: stored 6.0 rear is 5C.2.3.3 (first-floor walls, "
        f"narrow-lot dwelling houses); 5B.2.3.1(a) prescribes 900mm rear for "
        f"secondary dwellings. Evidence for a 0.9 repair is STRONG but the "
        f"value change was not authorised in this pass; fail closed rather "
        f"than serve a 6.7x overstatement.",
        "fairfield 716: needs_review (5C value under secondary_dwelling)",
        "control_type = 'rear_setback' AND value_min = 6.0 AND is_current "
        "AND needs_review = TRUE",
        False,
    ),
]

# --- INSERT plan -----------------------------------------------------------
INSERTS = [
    {
        "lga": "ryde", "dev_type": "dwelling_house",
        "control_type": "front_setback", "value_min": 6.0, "value_max": None,
        "unit": "m",
        "condition": "General control ('generally'); corner-site secondary "
                     "street setback 2m (s2.9.1(b)) and garages minimum 1m "
                     "behind the front facade (s2.9.1(c)) are NOT stored.",
        "applicability": "universal_residential",
        "source_text": "a. Dwellings are generally to be set back 6 m from "
                       "the street front boundary.",
        "section_ref": "ryde-part3.3-dwelling-houses.pdf#2.9.1(a)",
        "pdf_page": 25,
        "dcp_version": "Ryde DCP 2014 (Part 3.3 Dwelling Houses and Dual "
                       "Occupancy (attached))",
        "review_reason": f"{STAMP} inserted: Ryde's general front setback was "
                         f"stored NOWHERE — the only served front row (680) "
                         f"carried the s2.9.3 rear-boundary quote. Read from "
                         f"s2.9.1(a), printed p.25 of the local PDF. Evidence "
                         f"STRONG.",
    },
    {
        "lga": "burwood", "dev_type": "dwelling_house",
        "control_type": "side_setback", "value_min": 0.9, "value_max": 1.5,
        "unit": "m",
        "condition": "900mm single storey; 1.5m for the second-storey "
                     "component of a two-storey dwelling. Except the common "
                     "wall of an attached or semi-detached dwelling (Ch 4 "
                     "s4.5 Table 3).",
        "applicability": "universal_residential",
        "source_text": "Table 3. Setback Requirements for Single Dwelling "
                       "Houses — Side Setback: (i) Two storey (second storey "
                       "component of the dwelling only) 1.5m; (ii) Single "
                       "storey 900mm. Except for the common wall of an "
                       "attached dwelling or semi-detached dwelling.",
        "section_ref": "burwood-part4-residential.pdf#4.5-table3",
        "pdf_page": 19,
        "dcp_version": "Burwood DCP 2013 (Chapter 4 Development in "
                       "Residential Areas)",
        "review_reason": f"{STAMP} inserted: Burwood's general side setback "
                         f"was stored NOWHERE — the only served side row "
                         f"(707) is the P10 garage-wall rule. Read from Ch 4 "
                         f"s4.5 Table 3, printed p.221 of the local PDF. "
                         f"Range-row shape follows burwood row 1080 (rear "
                         f"3-6m). Evidence STRONG.",
    },
]


def main() -> int:  # pragma: no cover - CLI entry point
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Execute. Without this nothing is written.")
    ap.add_argument("--backup-table",
                    default="dcp_setback_controls_missing_primary_20260803")
    args = ap.parse_args()

    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set — nothing was checked, which is "
              "not a pass. Exiting 2.", file=sys.stderr)
        return 2
    import psycopg2

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")
    try:
        # Plan: which updates still match their guard, which inserts are new.
        # Currency scope: every guard fragment in UPDATES pins the row's
        # is_current (or needs_review) pre-state explicitly, so the planner has
        # no blanket currency filter on purpose — it must also see rows already
        # retired by a prior run to report them as done rather than replan them.
        todo_updates, done_updates = [], []
        for spec in UPDATES:
            control_id, guard, gparams = spec[0], spec[1], spec[2]
            post_guard = spec[7]
            # {guard} pins the row's is_current / needs_review pre-state.
            cur.execute(
                f"SELECT 1 FROM dcp_setback_controls WHERE id = %s AND {guard}",
                (control_id,))
            if cur.fetchone():
                todo_updates.append(spec)
                continue
            # Not in the pre-state: it must PROVE it reached the intended
            # post-state to count as done. Anything else is a divergence, and
            # continuing would commit the rest of the adjudication around a
            # row in an unknown state (Sol finding, 2026-08-03).
            # {post_guard} pins the intended is_current / needs_review
            # post-state per row.
            cur.execute(
                f"SELECT 1 FROM dcp_setback_controls WHERE id = %s "
                f"AND {post_guard}", (control_id,))
            if cur.fetchone():
                done_updates.append(spec)
                continue
            print(f"ERROR: control {control_id} matches neither its pre-state "
                  f"nor its intended post-state — refusing to classify a "
                  f"divergence as done. Nothing written. Exiting 2.",
                  file=sys.stderr)
            return 2

        todo_inserts, done_inserts = [], []
        for r in INSERTS:
            cur.execute(
                """SELECT id, is_current FROM dcp_setback_controls
                    WHERE lga = %s AND dev_type = %s AND control_type = %s
                      AND COALESCE(condition, '') = COALESCE(%s, '')""",
                (r["lga"], r["dev_type"], r["control_type"], r["condition"]))
            matches = cur.fetchall()
            if any(m[1] for m in matches):
                # A SERVED twin exists — the control is genuinely present.
                done_inserts.append(r)
            elif matches:
                # Only RETIRED twins exist. Skipping here would report the
                # served control as present while nothing serves it; blindly
                # inserting would shadow the retired row's history. Either
                # needs a human ruling (Sol finding, 2026-08-03).
                print(f"ERROR: only RETIRED row(s) "
                      f"{[m[0] for m in matches]} match the planned insert "
                      f"for {r['lga']}/{r['control_type']}/{r['dev_type']} — "
                      f"reactivate-vs-insert needs adjudication. Nothing "
                      f"written. Exiting 2.", file=sys.stderr)
                return 2
            else:
                todo_inserts.append(r)

        print("\n=== MISSING_PRIMARY adjudication ===")
        print(f"  updates planned : {len(todo_updates)} of {len(UPDATES)}"
              f"  (proven already in post-state: "
              f"{[s[0] for s in done_updates]})")
        for spec in todo_updates:
            print(f"    {spec[6]}")
        print(f"  inserts planned : {len(todo_inserts)} of {len(INSERTS)}"
              f"  (already present: {len(done_inserts)})")
        for r in todo_inserts:
            vm = f"{r['value_min']}" + (f"-{r['value_max']}" if r["value_max"] else "")
            print(f"    ADD {r['lga']}/{r['control_type']}/{r['dev_type']} = "
                  f"{vm}{r['unit']}  [{r['section_ref']}]")

        if not args.apply:
            print("\nDRY RUN — nothing written. Re-run with --apply to execute.")
            return 0
        if not todo_updates and not todo_inserts:
            print("\nNothing to write.")
            return 0

        ids = [spec[0] for spec in todo_updates]
        if ids:
            cur.execute(
                f"CREATE TABLE IF NOT EXISTS {args.backup_table} AS "
                f"SELECT id, control_type, value_min, value_max, condition, "
                f"source_text, section_ref, pdf_page, review_reason, "
                f"reviewed_at, last_verified_at, needs_review, is_current "
                f"FROM dcp_setback_controls WHERE id = ANY(%s)", (ids,))
            cur.execute(
                f"SELECT count(*) FROM unnest(%s::int[]) AS wanted(id) "
                f"WHERE NOT EXISTS (SELECT 1 FROM {args.backup_table} b "
                f"WHERE b.id = wanted.id)", (ids,))
            missing = cur.fetchone()[0]
            conn.commit()
            if missing:
                print(f"ERROR: {missing} of {len(ids)} rows are NOT in "
                      f"{args.backup_table} — it is from an earlier run and "
                      f"cannot roll this one back. Pass a fresh "
                      f"--backup-table. Aborting before any write.",
                      file=sys.stderr)
                return 2
            print(f"  backed up {len(ids)} rows to {args.backup_table}")

        written = 0
        for (control_id, guard, gparams, set_frag, set_params, reason, label,
             _post_guard, verify_stamp) in todo_updates:
            # last_verified_at only where the stored content was verified
            # against source THIS pass — a needs_review flag or a retirement
            # is not a verification (camden-692 doctrine).
            stamp = ", last_verified_at = CURRENT_DATE" if verify_stamp else ""
            cur.execute(
                f"""UPDATE dcp_setback_controls
                       SET {set_frag}, review_reason = %s, reviewed_at = NOW()
                           {stamp}
                     WHERE id = %s AND {guard}""",
                (*set_params, reason, control_id, *gparams))
            written += cur.rowcount
            if cur.rowcount != 1:
                conn.rollback()
                print(f"ERROR: guard skipped {label!r} mid-apply — pre-state "
                      f"changed after planning. EVERYTHING rolled back; "
                      f"nothing written. Re-run to rebuild the plan.",
                      file=sys.stderr)
                return 2

        new_ids = []
        for r in todo_inserts:
            cur.execute(
                """INSERT INTO dcp_setback_controls
                     (lga, dev_type, control_type, value_min, value_max, unit,
                      condition, applicability, source_text, section_ref,
                      pdf_page, dcp_version, extraction_method, is_current,
                      needs_review, review_reason, reviewed_at, last_verified_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                           'manual_curation', TRUE, FALSE, %s, NOW(),
                           CURRENT_DATE)
                   RETURNING id""",
                (r["lga"], r["dev_type"], r["control_type"], r["value_min"],
                 r["value_max"], r["unit"], r["condition"], r["applicability"],
                 r["source_text"], r["section_ref"], r["pdf_page"],
                 r["dcp_version"], r["review_reason"]))
            new_ids.append(cur.fetchone()[0])
        conn.commit()

        print(f"  updated {written} rows (predicted {len(todo_updates)})")
        print(f"  inserted {len(new_ids)} rows (predicted {len(todo_inserts)})"
              f": ids {new_ids}")
        print(f"\nROLLBACK:")
        if ids:
            print(f"  UPDATE dcp_setback_controls t SET control_type = "
                  f"b.control_type, value_min = b.value_min, value_max = "
                  f"b.value_max, condition = b.condition, source_text = "
                  f"b.source_text, section_ref = b.section_ref, pdf_page = "
                  f"b.pdf_page, review_reason = b.review_reason, reviewed_at "
                  f"= b.reviewed_at, last_verified_at = b.last_verified_at, "
                  f"needs_review = b.needs_review, is_current = b.is_current "
                  f"FROM {args.backup_table} b WHERE t.id = b.id;")
        if new_ids:
            print(f"  DELETE FROM dcp_setback_controls WHERE id = "
                  f"ANY(ARRAY{new_ids});")

        # Post-write verify: the two primaries exist and are served; 714
        # retired; flags set.
        cur.execute(
            """SELECT id, lga, control_type, value_min, value_max, is_current,
                      needs_review
                 FROM dcp_setback_controls
                WHERE id = ANY(%s) OR id = ANY(%s)
                ORDER BY id""", (ids, new_ids))
        print("\n  post-write verify:")
        for row in cur.fetchall():
            print(f"    {row}")
        return 0
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        print(f"ERROR (rolled back): {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
