#!/usr/bin/env python3
"""Apply a state_law_proof plan: set citation_status='proven' on state-law rules proven verbatim.

prior-art-checked: reuse not viable -- dcp_citation_status.py writes the same columns but only for
council DCP rows judged against a PDF (it joins dcp_chapter_registry); state rows have none.

Safety: dry run unless --apply; backs up every row it will change to data/db_rollback_backups/;
refuses if any planned row's provision_text md5 differs from the plan (text changed since the proof)
or the row is no longer current / no longer state-law (source_council IS NULL); verifies rowcount.

    python scripts/apply_state_law_proof.py data/state_law_proof_plan_<date>.json            # dry run
    python scripts/apply_state_law_proof.py data/state_law_proof_plan_<date>.json --apply
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_law_proof import ROOT, connect  # noqa: E402

BACKUPS = ROOT / "data" / "db_rollback_backups"
COLS = ["citation_status", "citation_source_path", "citation_checked_at"]


def scope_clause(plan: dict, include_registry_lep: bool) -> str:
    """SQL guard on which rows the plan may touch. Default: state-law only (source_council IS NULL).

    A plan with scope 'registry_lep' (scripts/lep_law_proof.py) names council-tagged LEP rows; it is refused
    unless --include-registry-lep is given, and the flag does not widen a state-law plan. The default is not loosened.
    """
    scope = plan.get("scope")
    if scope == "registry_lep":
        if not include_registry_lep:
            raise SystemExit("REFUSING: plan scope is registry_lep; re-run with --include-registry-lep")
        return "source_council IS NOT NULL"
    if include_registry_lep:
        raise SystemExit("REFUSING: --include-registry-lep given but the plan is not scope registry_lep")
    return "source_council IS NULL"


def check_plan(plan_rows: list[dict], db_rows: dict[int, tuple]) -> list[str]:
    """Reasons to refuse; empty when every planned row is still the row that was proven."""
    bad = []
    for r in plan_rows:
        cur = db_rows.get(r["id"])
        if cur is None:
            bad.append(f"{r['id']}: not current / not state-law any more")
        elif cur[0] != r["md5"]:
            bad.append(f"{r['id']}: provision_text changed since the plan")
    return bad


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--include-registry-lep", action="store_true",
                    help="allow a registry_lep plan (council-tagged LEP rows); default is source_council IS NULL only")
    args = ap.parse_args(argv)
    plan = json.loads(Path(args.plan).read_text(encoding="utf8"))
    rows = plan["rows"]
    ids = [r["id"] for r in rows]
    guard = scope_clause(plan, args.include_registry_lep)
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, md5(provision_text), citation_status, citation_source_path, citation_checked_at "
                f"FROM regulatory_provisions WHERE id = ANY(%s) AND is_current AND {guard}", (ids,))
    db = {i: (m, s, p, c) for i, m, s, p, c in cur.fetchall()}
    bad = check_plan(rows, db)
    if bad:
        print(f"REFUSING: {len(bad)} planned rows no longer match; first 10:")
        print("\n".join(bad[:10]))
        return 1
    print(f"plan rows: {len(rows)}  all md5-identical to the proof  already proven: "
          f"{sum(1 for v in db.values() if v[1] == 'proven')}")
    if not args.apply:
        print("DRY RUN -- nothing written. Re-run with --apply.")
        return 0
    BACKUPS.mkdir(parents=True, exist_ok=True)
    back = BACKUPS / f"state_law_proof_pre_{datetime.now():%Y-%m-%dT%H%M%S}.json"
    back.write_text(json.dumps([{"id": i, "citation_status": v[1], "citation_source_path": v[2],
                                 "citation_checked_at": v[3].isoformat() if v[3] else None}
                                for i, v in sorted(db.items())], indent=1), encoding="utf8")
    print(f"backup: {back.relative_to(ROOT)}")
    conn.rollback()
    cur.execute("SET default_transaction_read_only = off")
    cur.execute("UPDATE regulatory_provisions p SET citation_status = 'proven', citation_source_path = v.src, "
                "citation_checked_at = now() FROM unnest(%s::bigint[], %s::text[], %s::text[]) AS v(id, md5, src) "
                f"WHERE p.id = v.id AND p.is_current AND p.{guard} "
                "AND md5(p.provision_text) = v.md5",
                (ids, [r["md5"] for r in rows], [r["source"] for r in rows]))
    n = cur.rowcount
    if n != len(rows):
        conn.rollback()
        print(f"ROLLED BACK: updated {n}, expected {len(rows)}")
        return 1
    conn.commit()
    print(f"WROTE {n} rows (citation_status='proven').")
    return 0


if __name__ == "__main__":
    sys.exit(main())
