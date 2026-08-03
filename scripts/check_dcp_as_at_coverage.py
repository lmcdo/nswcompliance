#!/usr/bin/env python3
# prior-art-checked: no existing check counts served DCP claims without a date
# provenance (scripts/validate_controls_provenance.py checks quotes/values, not
# dates; the campaign doc names this exact check as item 3's falsifiable check).
"""Falsifiable check: served DCP-derived claims without any as-at date.

Campaign item 3, observation mode (§7 rule: gates start observing; blocking
status is earned). Counts, per served LGA, the controls that fetch_dcp_setbacks
would render, and classifies each LGA by the SAME as-at resolution the serve
path uses (scripts/conveyancing_db._plan_as_at — imported, not reimplemented,
so this check can only pass if the real serve path resolves a date):

    portal_plan_record | stated_in_document | observed_current | NONE

The headline number is the count of served claims whose LGA resolves to NONE —
the campaign target is 0, recorded here, NOT enforced. Also reports
portal-vs-stated disagreements (recorded findings, not pick-ones).

Exit codes: 0 = ran and recorded (whatever the count); 2 = could not measure
(which is never a pass).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from conveyancing_db import _plan_as_at  # noqa: E402


def main() -> int:  # pragma: no cover - CLI entry point
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

    # Served claims = the rows fetch_dcp_setbacks renders (same filters).
    cur.execute(
        """SELECT lga, COUNT(*) FROM dcp_setback_controls
            WHERE is_current = TRUE
              AND (needs_review IS NULL OR needs_review = FALSE)
            GROUP BY lga ORDER BY lga""")
    served = dict(cur.fetchall())

    by_basis: dict[str, list[str]] = {}
    claims_by_basis: dict[str, int] = {}
    for slug, n in served.items():
        as_at = _plan_as_at(cur, slug)
        basis = (as_at or {}).get("basis") or "NONE"
        by_basis.setdefault(basis, []).append(slug)
        claims_by_basis[basis] = claims_by_basis.get(basis, 0) + n

    # Portal-vs-stated disagreements: both evidence classes present, different
    # dates. A finding to record, never silently resolved.
    cur.execute(
        """SELECT lga, portal_date::text, portal_date_evidence,
                  stated_date::text, stated_evidence
             FROM dcp_plan_as_at
            WHERE portal_date IS NOT NULL AND stated_date IS NOT NULL
              AND portal_date <> stated_date ORDER BY lga""")
    disagreements = [
        {"lga": r[0], "portal_date": r[1], "portal_evidence": r[2],
         "stated_date": r[3], "stated_evidence": r[4]}
        for r in cur.fetchall()
    ]
    conn.close()

    dateless_claims = claims_by_basis.get("NONE", 0)
    total_claims = sum(served.values())
    report = {
        "check": "dcp_as_at_coverage",
        "mode": "observation",
        "run_date": date.today().isoformat(),
        "served_lgas": len(served),
        "served_claims": total_claims,
        "claims_by_basis": claims_by_basis,
        "lgas_by_basis": {k: sorted(v) for k, v in by_basis.items()},
        "dateless_claims": dateless_claims,
        "dateless_lgas": sorted(by_basis.get("NONE") or []),
        "portal_vs_stated_disagreements": disagreements,
        "target": "dateless_claims == 0 (campaign item 3); NOT enforced — "
                  "observation mode until false-positive behaviour is known",
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
