#!/usr/bin/env python3
# prior-art-checked: reuse not viable because every existing ratchet measures
# our PROCESS, not the answer. dq_check.py asks whether a defect has a check;
# check_dcp_as_at_coverage.py asks whether a council has ANY date, and answers
# 0 today; validate_controls_provenance.py checks that a quote and a value are
# present, not whether the reader can reach the page or whether the plan is
# still in force. Sweeps 2026-08-14 on origin/main 8cccbf2a found nothing that
# scores the served answer itself. The shrink-only `_ratchet` is IMPORTED from
# check_dcp_as_at_coverage rather than copied — a second copy of a ratchet is
# how two baselines start disagreeing about what "worse" means.
"""Score the answer we actually serve, not our habits around it.

A regulatory number can be wrong in exactly three ways, and this counts the
served rows exposed to each:

  PROVENANCE    can the reader reach the source? A verbatim quote with no page
                number is a claim you cannot check in a 300-page plan.
  CURRENCY      is that plan still in force? A date obtained by noticing the
                council's URL still loads is not the same fact as a date the
                document states, and today they are indistinguishable in the
                headline "0 councils without a date".
  APPLICABILITY does the rule govern THIS address? A control from a plan
                covering one town, served to a whole council area, is right in
                the wrong place.

WHY IT MEASURES THROUGH THE SERVE PATH. Every count comes from
``conveyancing_db.fetch_dcp_setbacks`` — the same function the product calls —
rather than from a query of its own against dcp_setback_controls. A parallel
query can pass while the serve path does something else entirely, which is the
failure mode this repo already hit when a gate read a file git would never
carry. Measuring the real output means this check cannot be green while the
thing it describes is broken.

Counts are of DEFICIENT rows, per council, so the ratchet direction is obvious:
every number may fall and none may rise. Percentages are printed for reading,
never ratcheted — a percentage moves when the denominator changes, which is not
progress.

Exit codes: 0 = ran and the baseline held; 1 = a count rose; 2 = could not
measure, which is never a pass.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from check_dcp_as_at_coverage import _ratchet  # noqa: E402
from conveyancing_db import clause_or_page, fetch_dcp_setbacks  # noqa: E402

BASELINE = ".claude/served_answer_quality_baseline.json"

#: Bases that mean the date came from a DOCUMENT — the plan's own commencement
#: clause, or the Planning Portal's plan record. Anything else is us observing
#: that a URL still resolved, which says nothing about the plan being current.
DOCUMENTED_BASES = {"portal_plan_record", "stated_in_document"}


def _place_scoped_chapters(cur) -> set:
    """(council, chapter_key) for plans that cover PART of a council area.

    Same label test as the DQ-66 probe: it matches 3 of 655 registry rows, all
    of them Wingecarribee town plans. Kept as a query rather than a hardcoded
    list because a council that splits its plan next year should be caught
    without anyone remembering to edit this file.
    """
    cur.execute(
        """SELECT council, chapter_key FROM dcp_chapter_registry
            WHERE is_active
              AND chapter_label ~* '(town|village|locality|precinct)[[:space:]]+plan'"""
    )
    return {(c, k) for c, k in cur.fetchall()}


def main() -> int:  # pragma: no cover - CLI entry point
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", action="store_true",
                    help="Compare against the recorded baseline and fail on a rise.")
    ap.add_argument("--update", action="store_true",
                    help="With --baseline, rewrite it to today's counts.")
    args = ap.parse_args()

    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set — nothing was measured, which is "
              "not a pass. Exiting 2.", file=sys.stderr)
        return 2

    import psycopg2

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")

    cur.execute(
        """SELECT DISTINCT lga FROM dcp_setback_controls
            WHERE is_current = TRUE
              AND (needs_review IS NULL OR needs_review = FALSE)
            ORDER BY lga""")
    slugs = [r[0] for r in cur.fetchall()]
    if not slugs:
        # An empty serving set means the production data was NOT measured —
        # wrong database, emptied table — and must never read as "nothing
        # deficient" (the DQ-30 lesson: a completion check must be able to
        # fail).
        print("ERROR: zero served councils found — nothing was measured, "
              "which is not a pass. Exiting 2.", file=sys.stderr)
        conn.close()
        return 2

    place_scoped = _place_scoped_chapters(cur)

    served = 0
    no_locator: dict = {}
    no_page: dict = {}
    observation_only: dict = {}
    ungated_locality: dict = {}

    for slug in slugs:
        data = fetch_dcp_setbacks(conn, slug, None)
        if not data:
            # The council has rows but the serve path returns nothing for it.
            # That is a serving failure, not a quality score, and it must not
            # be silently skipped — skipping would shrink every count and read
            # as improvement.
            print(f"ERROR: {slug} has served rows but fetch_dcp_setbacks "
                  f"returned nothing. Exiting 2 rather than scoring a set the "
                  f"product cannot render.", file=sys.stderr)
            conn.close()
            return 2

        entries = list(data.get("setbacks") or []) + list(data.get("sd_setbacks") or [])
        served += len(entries)

        basis = (data.get("as_at") or {}).get("basis")
        documented = basis in DOCUMENTED_BASES

        for e in entries:
            # THE CITATION IS `clause`, NOT `pdf_page`. fetch_dcp_setbacks
            # returns "clause": section_ref or "" (conveyancing_db.py:473) and
            # carries pdf_page as a separate convenience field. This check
            # originally counted missing pages and reported 780 of 968 as
            # unciteable, which described the wrong thing: all 968 rows carry
            # BOTH a section_ref and a verbatim source_text.
            #
            # A ref must point somewhere to be a citation, so the test is
            # whether it carries a locator at all. Anything with a digit does --
            # part-c-s2.4, table-6.2.1, lep-cl-6-12 are all real locations in
            # slug form, and an earlier strict clause-number regex wrongly
            # graded those as junk. What is left is refs naming an instrument
            # or an unnumbered part and nothing more: LEP, ADG,
            # part-c-residential. 75 of 968, and none of those 75 has a page
            # number either.
            clause = (e.get("clause") or "").strip()
            # A clause withheld as unproven (migration 077) is cited by its page instead:
            # the served citation is then "p. N", which is a locator.
            if e.get("clause_shown") is False:
                clause = clause_or_page("", e.get("pdf_page"))
            if not clause or not any(ch.isdigit() for ch in clause):
                no_locator[slug] = no_locator.get(slug, 0) + 1
            if e.get("pdf_page") is None:
                no_page[slug] = no_page.get(slug, 0) + 1
            if not documented:
                observation_only[slug] = observation_only.get(slug, 0) + 1
            if (slug, e.get("source_chapter_key")) in place_scoped:
                ungated_locality[slug] = ungated_locality.get(slug, 0) + 1

    conn.close()

    def pct(n: int) -> str:
        return f"{100 * n / served:.1f}%" if served else "n/a"

    print("=" * 72)
    print("SERVED-ANSWER QUALITY — the answer itself, not the process around it")
    print("=" * 72)
    print(f"served control rows (via fetch_dcp_setbacks): {served}")
    print(f"  run_date: {date.today().isoformat()}")
    print()
    print(f"PROVENANCE    ref carries no locator    : {sum(no_locator.values()):5d}  "
          f"({pct(sum(no_locator.values()))})")
    print("                the citation names an instrument or an unnumbered")
    print("                part and nothing more (LEP, ADG, part-c-residential),")
    print("                so a reader cannot turn to it. All served rows carry")
    print("                a section_ref AND a verbatim quote; this counts the")
    print("                ones that do not point anywhere.")
    print()
    print(f"  (convenience) no page number           : {sum(no_page.values()):5d}  "
          f"({pct(sum(no_page.values()))})")
    print("                NOT the citation — the serve path renders `clause`")
    print("                from section_ref and carries pdf_page separately.")
    print("                Ratcheted too, so it cannot rot, but a missing page")
    print("                is an inconvenience where a missing locator is a")
    print("                citation that does not resolve.")
    print()
    print(f"CURRENCY      date from a URL check only: {sum(observation_only.values()):5d}  "
          f"({pct(sum(observation_only.values()))})")
    print("                NOT the same fact as a date the document states. The")
    print("                as-at coverage check reports 0 councils WITHOUT a")
    print("                date; this splits that by evidence quality.")
    print()
    print(f"APPLICABILITY served with no locality gate: {sum(ungated_locality.values()):5d}  "
          f"({pct(sum(ungated_locality.values()))})")
    print("                from a plan covering one town, served council-wide.")
    print()

    # One flat map so a single baseline file holds all three, keyed by
    # dimension and council. Per-council because a 4-row council and a 90-row
    # council regressing are not the same event.
    current = {f"provenance_no_locator/{k}": v for k, v in no_locator.items()}
    current.update({f"provenance_no_page/{k}": v for k, v in no_page.items()})
    current.update({f"currency_observation_only/{k}": v
                    for k, v in observation_only.items()})
    current.update({f"applicability_ungated/{k}": v
                    for k, v in ungated_locality.items()})

    if args.baseline:
        return _ratchet(BASELINE, "Served-answer quality", current, args.update)

    print("Recorded only — pass --baseline to enforce the ratchet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
