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

    if "--baseline" in sys.argv:
        # Ratchet WITHOUT_manifest per product. Historical rows can never gain
        # one - a manifest is derivable only at computation time - so a falling
        # count is not the goal here. The goal is that it never RISES, which is
        # exactly "every NEW report carries a manifest". A product that starts
        # emitting them stays flat; one that regresses fails the build.
        per_product = {k: v["without_manifest"]
                       for k, v in (report.get("per_product") or {}).items()}
        return _ratchet(".claude/manifest_coverage_baseline.json",
                        "Satellite manifests", per_product, "--update" in sys.argv)
    return 0



# --- shrink-only ratchet -----------------------------------------------------
# Same mechanism as scripts/lint_hardcoded_zone_codes.py --baseline, already in
# CI. Progress on this campaign lived in a plan file that nothing executed, so
# each session re-derived where it had got to. A recorded baseline makes the
# remaining work MEASURED rather than remembered: the count may fall, never
# rise, and a fall prints the command to lower it.
def _ratchet(path: str, label: str, current: dict, update: bool) -> int:
    import json
    import os

    if update:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"_note": ("Shrink-only. Each value may fall, never rise. "
                                 "Lower it with --baseline --update when work lands."),
                       "per_key": dict(sorted(current.items()))}, f, indent=2)
            f.write("\n")
        print(f"{label} baseline updated: {sum(current.values())} across "
              f"{len(current)} key(s).")
        return 0

    try:
        with open(path, encoding="utf-8") as f:
            baseline = json.load(f)["per_key"]
    except (OSError, ValueError, KeyError):
        print(f"{label} baseline: cannot read {path} - refusing to pass.")
        return 1

    worse, better, new = [], [], []
    for k, n in sorted(current.items()):
        was = baseline.get(k)
        if was is None:
            new.append((k, n))
        elif n > was:
            worse.append((k, was, n))
        elif n < was:
            better.append((k, was, n))

    if better:
        print(f"{label}: IMPROVED - lower the baseline and commit")
        for k, was, now in better:
            print(f"  {k}: {was} -> {now}")

    if worse or new:
        print(f"{label}: FAILED - a count rose, which means new work regressed it.")
        for k, was, now in worse:
            print(f"  {k}: {was} -> {now}")
        for k, n in new:
            print(f"  {k}: NEW, {n} (not in the baseline)")
        return 1

    print(f"{label} baseline: OK - {sum(current.values())}, none increased.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

