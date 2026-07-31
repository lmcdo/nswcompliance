#!/usr/bin/env python3
"""Audit: which LGAs have a REPRODUCIBLE precinct-keying rule, and which are exposed.

prior-art-checked: the guard's hits are the marketing coverage page and the
frontend dcp/coverage API (they count councils/provisions for display) and
src/processing/rule_generator.py (generates extraction rules, unrelated). None
audits precinct-keying-rule coverage vs re-extraction risk — this is new.

A council whose provisions are precinct-keyed but has NO rule in
scripts/derive_precinct_keys.py (RULES) will be SILENTLY UN-KEYED the next time its
chapters are re-extracted (docs/EXTRACTION_WHY_IT_RECURS...). This report finds those.

Run: python scripts/audit_precinct_keying_coverage.py
Reads RULES from derive_precinct_keys.py so it stays in sync automatically.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

# map dcp_precinct_boundaries.lga -> the source_council slug(s) whose provisions key to it
LGA_COUNCILS = {
    "Inner West": ["marrickville", "leichhardt", "ashfield"],
    "Ku-ring-gai": ["ku_ring_gai"],
    "Waverley": ["waverley"],
    "Sydney": ["city_of_sydney"],
    "Woollahra": ["woollahra"],
    "Parramatta": ["parramatta"],
}


def _rule_councils() -> set[str]:
    spec = importlib.util.spec_from_file_location(
        "derive_precinct_keys", str(Path(__file__).with_name("derive_precinct_keys.py")))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {r["council"] for r in mod.RULES}


def main() -> None:
    rule_councils = _rule_councils()
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30s'")
    cur.execute("""
        SELECT b.lga, COUNT(*) tot, COUNT(*) FILTER (WHERE n>0) connected FROM (
          SELECT b.lga, b.precinct_id, (SELECT COUNT(*) FROM regulatory_provisions rp
            WHERE rp.is_current=true AND rp.v2_precinct_id=b.precinct_id) n
          FROM dcp_precinct_boundaries b) b GROUP BY 1 ORDER BY 1""")
    print(f"{'LGA':<20} {'bounds':>7} {'conn':>5}  {'keyed councils':<32} rule?  status")
    print("-" * 90)
    exposed = []
    for lga, tot, conn_ct in cur.fetchall():
        base = lga.replace("-staged", "")
        councils = LGA_COUNCILS.get(base, [base.lower().replace(" ", "_")])
        keyed = []
        for c in councils:
            cur.execute("""SELECT 1 FROM regulatory_provisions WHERE source_council=%s
                AND is_current=true AND v2_precinct_id IS NOT NULL LIMIT 1""", (c,))
            if cur.fetchone():
                keyed.append(c)
        has_rule = any(c in rule_councils for c in councils)
        if keyed and not has_rule:
            status = "EXPOSED - re-extract un-keys it (add a rule)"
            exposed.append(lga)
        elif not keyed:
            status = "not keyed yet (needs content + rule)"
        else:
            status = "protected"
        print(f"{lga:<20} {tot:>7} {conn_ct:>5}  {(','.join(keyed) or '-'):<32} "
              f"{'YES' if has_rule else 'NO ':<5}  {status}")
    conn.close()
    if exposed:
        print(f"\n>>> {len(exposed)} LGA(s) EXPOSED (keyed, no reproducible rule): {', '.join(exposed)}")
        print(">>> Add a rule to scripts/derive_precinct_keys.py RULES, or do not re-extract them.")
    else:
        print("\nAll keyed LGAs have a reproducible rule.")


if __name__ == "__main__":
    main()
