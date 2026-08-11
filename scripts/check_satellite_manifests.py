#!/usr/bin/env python3
# prior-art-checked: no existing check counts satellite reports without an
# execution manifest (scripts/check_dcp_as_at_coverage.py is the DCP-lane
# analogue this mirrors; the campaign §7 item 4 names this as its falsifiable
# check). Read-only.
"""Falsifiable check: satellite reports lacking an execution manifest.

Campaign item 4, observation mode (§7 rule: gates start observing; blocking
status is earned). Counts, per product, the stored report envelopes that do
NOT carry ``inputs.execution_manifest`` (granny-flat detect rows store it in
``outputs``). Historical rows are counted honestly, never backfilled — a
manifest can only be derived at computation time, so a backfill would be the
parallel-lookup anti-pattern by definition.

Exit codes: 0 = ran and recorded (whatever the count); 2 = could not measure
(zero rows found is a wrong-database signal, never a satisfied target).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


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

    cur.execute(
        """SELECT product,
                  COUNT(*) AS total,
                  COUNT(*) FILTER (WHERE inputs ? 'execution_manifest') AS with_manifest
             FROM property_reports
            WHERE product IN ('flood', 'shadow', 'solar-yield', 'bushfire')
            GROUP BY product ORDER BY product""")
    rows = cur.fetchall()

    cur.execute(
        """SELECT COUNT(*) AS total,
                  COUNT(*) FILTER (WHERE inputs ? 'execution_manifest'
                                      OR outputs ? 'execution_manifest') AS with_manifest
             FROM granny_flat_reports""")
    g_total, g_with = cur.fetchone()
    conn.close()

    per_product = {p: {"total": t, "with_manifest": w, "without_manifest": t - w}
                   for p, t, w in rows}
    per_product["granny-flat"] = {"total": g_total, "with_manifest": g_with,
                                  "without_manifest": g_total - g_with}

    total = sum(v["total"] for v in per_product.values())
    if total == 0:
        print("ERROR: zero satellite reports found — the production claim set "
              "was not measured (wrong database?). Exiting 2.", file=sys.stderr)
        return 2

    without = sum(v["without_manifest"] for v in per_product.values())
    report = {
        "check": "satellite_execution_manifests",
        "mode": "observation",
        "run_date": date.today().isoformat(),
        "reports_total": total,
        "reports_without_manifest": without,
        "per_product": per_product,
        "note": "Historical rows predate the manifest and are counted, not "
                "backfilled — a manifest is derivable only at computation time.",
        "target": "every NEW report carries a manifest; NOT enforced — "
                  "observation mode until false-positive behaviour is known",
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
