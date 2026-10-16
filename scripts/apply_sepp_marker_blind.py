#!/usr/bin/env python3
"""Apply a sepp_marker_blind plan: rule 1 rows -> citation_status='proven'; rule 2 rows -> text := law unit + proven.

prior-art-checked: combines scripts/apply_state_law_proof.py (status-only write, md5 guard) and
scripts/apply_state_law_recopy.py (versioned text write via dq88_refresh_2026_10_10.version) because one plan
carries both rules; their guards are reused (check_plan from the recopy applier) and extended with
'already proven' (refuse) and a mandatory run of scripts/verify_sepp_marker_blind.py first.

DRY RUN (read-only session, nothing written) unless --apply. Refuses, writing nothing, when: the verifier finds any
mismatch; a row is no longer current / no longer state-law; its provision_text md5 differs from the plan; it is
already proven; a recopy row already has version history. --apply backs every row up to data/db_rollback_backups/
first, writes in ONE transaction, and rolls back unless every row's rowcount and resulting state match the plan.

    python scripts/apply_sepp_marker_blind.py data/sepp_marker_blind_plan_<d>.json data/sepp_marker_blind_evidence_<d>.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_law_proof import ROOT, connect  # noqa: E402
import apply_state_law_recopy as rcp  # noqa: E402
import verify_sepp_marker_blind as ver  # noqa: E402

BACKUPS = ROOT / "data" / "db_rollback_backups"
SELECT = ("SELECT id, md5(provision_text), source_council, is_current, "
          "(SELECT count(*) FROM provision_versions v WHERE v.provision_id = p.id), "
          "provision_text, citation_status, citation_source_path, citation_checked_at, version_count, "
          "current_version_id, text_hash, text_hash_current FROM regulatory_provisions p WHERE id = ANY(%s)")


def check(plan_rows: list[dict], full: dict[int, tuple]) -> list[str]:
    """Reasons to refuse. full: id -> the SELECT row."""
    bad = rcp.check_plan([dict(r, new_text=r["new_text"] or r["old_text"]) for r in plan_rows],
                         {i: (t[1], t[2], t[3], 0) for i, t in full.items()})   # recopy applier's md5/current/state-law guards
    for r in plan_rows:
        t = full.get(r["id"])
        if t is None:
            continue
        if t[6] == "proven":
            bad.append(f"{r['id']}: already proven")
        if r["rule"] == "recopy" and t[4]:
            bad.append(f"{r['id']}: already has {t[4]} version rows")
    return bad


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("evidence")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    plan = json.loads(Path(args.plan).read_text(encoding="utf8"))
    evidence = [json.loads(x) for x in Path(args.evidence).read_text(encoding="utf8").splitlines() if x.strip()]
    ok, vbad = ver.verify(plan, evidence)
    if vbad or not ok:
        print(f"REFUSING: verifier found {len(vbad)} mismatches, verified {ok}")
        print("\n".join(vbad[:10]))
        return 1
    rows = plan["rows"]
    ids = [r["id"] for r in rows]
    conn = connect()
    cur = conn.cursor()
    cur.execute("SET statement_timeout = 30000")
    cur.execute(SELECT, (ids,))
    full = {t[0]: t for t in cur.fetchall()}
    bad = check(rows, full)
    if bad:
        print(f"REFUSING: {len(bad)} problems; first 10:")
        print("\n".join(bad[:10]))
        return 1
    print(f"verifier: {ok} rows verified.  plan rows: {len(rows)}  by rule {dict(Counter(r['rule'] for r in rows))}  "
          "all md5-identical to the plan, current, state-law, not proven, no version history on recopy rows")
    if not args.apply:
        print("DRY RUN -- nothing written (read-only session). Re-run with --apply.")
        return 0

    from dq88_refresh_2026_10_10 import version  # noqa: E402  (the shared version-history writer)
    BACKUPS.mkdir(parents=True, exist_ok=True)
    back = BACKUPS / f"sepp_marker_blind_pre_{datetime.now():%Y-%m-%dT%H%M%S}.json"
    back.write_text(json.dumps(
        [{"id": t[0], "provision_text": t[5], "citation_status": t[6], "citation_source_path": t[7],
          "citation_checked_at": t[8].isoformat() if t[8] else None, "version_count": t[9],
          "current_version_id": t[10], "text_hash": t[11], "text_hash_current": t[12]}
         for t in sorted(full.values())], indent=1, default=str), encoding="utf8")
    print(f"backup: {back.relative_to(ROOT)}")
    conn.rollback()
    conn.autocommit = True
    cur.execute("SET default_transaction_read_only = off")
    conn.autocommit = False
    now = datetime.now(timezone.utc)
    for r in rows:
        cur.execute("SELECT md5(provision_text) FROM regulatory_provisions WHERE id = %s AND is_current "
                    "AND source_council IS NULL AND COALESCE(citation_status,'') <> 'proven' FOR UPDATE", (r["id"],))
        got = cur.fetchone()
        if got is None or got[0] != r["md5"]:
            conn.rollback()
            print(f"ROLLED BACK: {r['id']} changed under us")
            return 1
        want_md5 = r["md5"]
        if r["rule"] == "recopy":
            where = f"unit {r['unit_id']} of {r['epi']} in force on {r['law_date']}"
            version(cur, r["id"], r["new_text"], r["source"],
                    f"Stored text dropped words of this unit; re-copied from {where}.",
                    f"Stored text replaced by the verbatim words of {where} (deterministic, scripts/sepp_marker_blind.py).",
                    now)
            want_md5 = rcp.md5(r["new_text"])
        cur.execute("UPDATE regulatory_provisions SET citation_status = 'proven', citation_source_path = %s, "
                    "citation_checked_at = now() WHERE id = %s AND is_current AND source_council IS NULL AND md5(provision_text) = %s",
                    (r["source"], r["id"], want_md5))
        if cur.rowcount != 1:
            conn.rollback()
            print(f"ROLLED BACK: {r['id']} text is not the planned text after the write")
            return 1
    cur.execute("SELECT id, md5(provision_text), citation_status FROM regulatory_provisions WHERE id = ANY(%s) AND is_current", (ids,))
    now_rows = {i: (m, s) for i, m, s in cur.fetchall()}
    wrong = [r["id"] for r in rows
             if now_rows.get(r["id"]) != ((rcp.md5(r["new_text"]) if r["rule"] == "recopy" else r["md5"]), "proven")]
    if wrong or len(now_rows) != len(rows):
        conn.rollback()
        print(f"ROLLED BACK: {len(wrong)} rows not in the planned state (rowcount {len(now_rows)}/{len(rows)})")
        return 1
    conn.commit()
    print(f"WROTE {len(rows)} rows: citation_status='proven'; recopy rows also provision_text = law unit, version v1/v2.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
