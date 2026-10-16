#!/usr/bin/env python3
"""Apply a state_law_recopy plan: set a state-law row's text to the law's own unit text, with version history.

prior-art-checked: reuse not viable as a whole -- apply_state_law_proof.py only flips citation_status and never
touches text; dq88_refresh_2026_10_10.py edits text with history but for a fixed hand-written list. This reuses
the latter's version() writer (provision_versions v1 old / v2 new, provision_change_log, current_version_id,
version_count, text hashes) and the former's guards.

For each plan row (scripts/state_law_recopy.py): provision_text := new_text (verbatim law, one unit),
citation_status := 'proven', citation_source_path := the unit's URL, citation_checked_at := now().

Safety: DRY RUN (read-only session, nothing written) unless --apply. Refuses, writing nothing, if any planned row
is no longer current / no longer state-law, its provision_text md5 differs from the plan, it already has version
history (version() assumes none), or the plan's text is empty / contains U+FFFD. --apply backs up every row to
data/db_rollback_backups/ first, writes in ONE transaction, verifies each row's md5 equals the plan's new text and
the rowcount equals the plan, and rolls back otherwise.

    python scripts/apply_state_law_recopy.py data/state_law_recopy_plan_<date>.json            # dry run
    python scripts/apply_state_law_recopy.py data/state_law_recopy_plan_<date>.json --apply
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_law_proof import ROOT, connect  # noqa: E402

BACKUPS = ROOT / "data" / "db_rollback_backups"
SELECT = ("SELECT id, md5(provision_text), source_council, is_current, "
          "(SELECT count(*) FROM provision_versions v WHERE v.provision_id = p.id), "
          "provision_text, citation_status, citation_source_path, citation_checked_at, version_count, "
          "current_version_id, text_hash, text_hash_current FROM regulatory_provisions p WHERE id = ANY(%s)")


def md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def check_plan(plan_rows: list[dict], db_rows: dict[int, tuple]) -> list[str]:
    """Reasons to refuse; empty when every planned row is still the row that was checked.
    db_rows: id -> (md5, source_council, is_current, n_versions)."""
    bad = []
    seen = set()
    for r in plan_rows:
        if r["id"] in seen:
            bad.append(f"{r['id']}: listed twice in the plan")
        seen.add(r["id"])
        if not r.get("new_text") or "�" in r["new_text"]:
            bad.append(f"{r['id']}: plan text empty or holds U+FFFD")
        cur = db_rows.get(r["id"])
        if cur is None:
            bad.append(f"{r['id']}: not in the database")
            continue
        if not cur[2] or cur[1] is not None:
            bad.append(f"{r['id']}: not current / not state-law any more")
        elif cur[0] != r["md5"]:
            bad.append(f"{r['id']}: provision_text changed since the plan")
        elif cur[3]:
            bad.append(f"{r['id']}: already has {cur[3]} version rows")
    return bad


def reason(r: dict) -> tuple[str, str]:
    """(amendment_reference, change summary) for provision_change_log / provision_versions."""
    where = f"unit {r['unit_id']} of {r['epi']} in force on {r['law_date']}"
    if r["kind"] == "amended":
        return (f"Wording amended since the stored text (in force {r['pit_date']}); now {where}.",
                f"Stored text replaced by the law's current words, {where}.")
    return (f"Stored text was this unit's words imperfectly copied; re-copied from {where}.",
            f"Stored text replaced by the verbatim words of {where} (deterministic, scripts/state_law_recopy.py).")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    plan = json.loads(Path(args.plan).read_text(encoding="utf8"))
    rows = plan["rows"]
    ids = [r["id"] for r in rows]
    conn = connect()
    cur = conn.cursor()
    cur.execute(SELECT, (ids,))
    full = {t[0]: t for t in cur.fetchall()}
    bad = check_plan(rows, {i: (t[1], t[2], t[3], t[4]) for i, t in full.items()})
    if bad:
        print(f"REFUSING: {len(bad)} problems; first 10:")
        print("\n".join(bad[:10]))
        return 1
    print(f"plan rows: {len(rows)}  by kind {dict(__import__('collections').Counter(r['kind'] for r in rows))}  "
          "all md5-identical to the plan, current, state-law, no version history")
    if not args.apply:
        print("DRY RUN -- nothing written (read-only session). Re-run with --apply.")
        return 0

    from dq88_refresh_2026_10_10 import version  # noqa: E402  (the shared version-history writer)
    BACKUPS.mkdir(parents=True, exist_ok=True)
    back = BACKUPS / f"state_law_recopy_pre_{datetime.now():%Y-%m-%dT%H%M%S}.json"
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
                    "AND source_council IS NULL FOR UPDATE", (r["id"],))
        got = cur.fetchone()
        if got is None or got[0] != r["md5"]:
            conn.rollback()
            print(f"ROLLED BACK: {r['id']} changed under us")
            return 1
        ref, why = reason(r)
        version(cur, r["id"], r["new_text"], r["source"], ref, why, now)
        cur.execute("UPDATE regulatory_provisions SET citation_status = 'proven', citation_source_path = %s, "
                    "citation_checked_at = now() WHERE id = %s AND md5(provision_text) = %s",
                    (r["source"], r["id"], md5(r["new_text"])))
        if cur.rowcount != 1:
            conn.rollback()
            print(f"ROLLED BACK: {r['id']} text is not the planned text after the write")
            return 1
    cur.execute("SELECT id, md5(provision_text) FROM regulatory_provisions WHERE id = ANY(%s)", (ids,))
    now_md5 = dict(cur.fetchall())
    wrong = [r["id"] for r in rows if now_md5.get(r["id"]) != md5(r["new_text"])]
    if wrong or len(now_md5) != len(rows):
        conn.rollback()
        print(f"ROLLED BACK: {len(wrong)} rows do not hold the planned text (rowcount {len(now_md5)}/{len(rows)})")
        return 1
    conn.commit()
    print(f"WROTE {len(rows)} rows: provision_text = law unit text, citation_status='proven', version history v1/v2.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
