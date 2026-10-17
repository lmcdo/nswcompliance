#!/usr/bin/env python3
"""Apply a sepp_marker_blind or sepp_ref_fix plan (rows with new_ref_number also set ref_number): rule 1 -> proven; rule 2 -> text := law unit + proven.

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
from dq_probe_unchecked_rows import probe_108  # noqa: E402

BACKUPS = ROOT / "data" / "db_rollback_backups"
SELECT = ("SELECT id, md5(provision_text), source_council, is_current, "
          "(SELECT count(*) FROM provision_versions v WHERE v.provision_id = p.id), "
          "provision_text, citation_status, citation_source_path, citation_checked_at, version_count, "
          "current_version_id, text_hash, text_hash_current, ref_number, document_id, section_header "
          "FROM regulatory_provisions p WHERE id = ANY(%s)")
LEP_COUNCIL = "inner_west"   # the only council scope 'registry_lep' may write (scripts/lep_law_proof.py's Inner West LEP)


def final_key(r: dict, header: str | None) -> tuple[str, str, str, str]:
    """The uq_provisions_current_identity key the row will have after the write (COALESCEd like the index)."""
    text = r["new_text"] if r.get("rule") == "recopy" and r.get("new_text") else r["old_text"]
    return (r["document_id"] or "", r.get("new_ref_number") or r["ref_number"] or "", header or "", rcp.md5(text))


def duplicate_problems(plan_rows: list[dict], headers: dict[int, str | None],
                       others: list[tuple]) -> list[str]:
    """Pure. Refusals when two plan rows would end with the same final key, or a plan row's final key equals an
    existing current row OUTSIDE the plan (others: (id, document_id, ref_number, section_header, md5(text)[, v2_is_actionable])); a SERVED outside row with
    the same document and text under another label is refused too (the same rule shown twice)."""
    bad, seen, same_text = [], {}, {}
    for r in plan_rows:
        k = final_key(r, headers.get(r["id"]))
        if k in seen:
            bad.append(f"{seen[k]} and {r['id']}: would end with the same (document_id, ref_number, section_header, "
                       f"md5(text)) = {k[0]!r}, {k[1]!r}, {k[2]!r}, {k[3]}")
        else:
            seen[k] = r["id"]
        # Same document and same final text under DIFFERENT labels is the same rule shown twice -- and the text is
        # written before the label, so the unique index can also trip mid-write (8759/8760, 2026-10-17).
        t = (k[0], k[3])
        if t in same_text and same_text[t] != r["id"] and seen.get(k) == r["id"]:
            bad.append(f"{same_text[t]} and {r['id']}: would hold the same text in document {k[0]!r} (a duplicate rule)")
        same_text.setdefault(t, r["id"])
    in_plan = {r["id"] for r in plan_rows}
    for oid, doc, ref, hdr, m5, *rest in others:
        served = rest[0] if rest else True
        if oid in in_plan:
            continue
        k = (doc or "", ref or "", hdr or "", m5)
        if k in seen:
            bad.append(f"{seen[k]}: final key equals existing current row {oid} outside the plan")
        elif served and (doc or "", m5) in same_text:   # same document, same text, other label: the same rule shown twice
            bad.append(f"{same_text[(doc or '', m5)]}: would hold the same text as existing current row {oid} "
                       f"in document {doc!r} (a duplicate rule)")
    return bad


def duplicate_guard(cur, plan_rows: list[dict], full: dict[int, tuple]) -> list[str]:
    """Reads the database (no write): existing current rows that share a plan row's document and final text."""
    headers = {i: t[15] for i, t in full.items()}
    keys = {r["id"]: final_key(r, headers.get(r["id"])) for r in plan_rows}
    cur.execute("SELECT id, document_id, ref_number, section_header, md5(provision_text), v2_is_actionable FROM regulatory_provisions "
                "WHERE is_current AND document_id = ANY(%s) AND md5(provision_text) = ANY(%s) AND id <> ALL(%s)",
                (sorted({k[0] for k in keys.values()}), sorted({k[3] for k in keys.values()}), list(keys)))
    return duplicate_problems(plan_rows, headers, cur.fetchall())


def check(plan_rows: list[dict], full: dict[int, tuple], scope: str | None = None) -> list[str]:
    """Reasons to refuse. full: id -> the SELECT row. scope None = state law (source_council IS NULL);
    'registry_lep' = source_council LEP_COUNCIL (the recopy applier's state-law guard is fed None when it matches)."""
    want = LEP_COUNCIL if scope == "registry_lep" else None
    bad = rcp.check_plan([dict(r, new_text=r["new_text"] or r["old_text"]) for r in plan_rows],
                         {i: (t[1], None if t[2] == want else (t[2] or "state-law"), t[3], 0)
                          for i, t in full.items()})   # recopy applier's md5/current/scope guards
    for r in plan_rows:
        t = full.get(r["id"])
        if t is None:
            continue
        if t[13] != r["ref_number"] or t[14] != r["document_id"]:
            bad.append(f"{r['id']}: ref_number or document_id changed since the plan")
        if scope == "registry_lep" and r.get("source_council") != LEP_COUNCIL:
            bad.append(f"{r['id']}: plan row source_council {r.get('source_council')!r} is not {LEP_COUNCIL!r}")
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
    ap.add_argument("--scope", choices=["registry_lep"], default=None,
                    help="allow a registry_lep plan (Inner West LEP rows, source_council = 'inner_west'); default is state law only")
    args = ap.parse_args(argv)
    plan = json.loads(Path(args.plan).read_text(encoding="utf8"))
    if (plan.get("scope") or None) != args.scope:   # neither direction widens the default
        print(f"REFUSING: plan scope {plan.get('scope')!r} but --scope {args.scope!r}")
        return 1
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
    bad = check(rows, full, args.scope) + duplicate_guard(cur, rows, full)
    if bad:
        print(f"REFUSING: {len(bad)} problems; first 10:")
        print("\n".join(bad[:10]))
        return 1
    print(f"verifier: {ok} rows verified.  plan rows: {len(rows)}  by rule {dict(Counter(r['rule'] for r in rows))}  "
          f"all md5-identical to the plan, current, {'council ' + LEP_COUNCIL if args.scope else 'state-law'}, not proven, "
          "no version history on recopy rows, no duplicate (document, ref, header, text) key")
    if not args.apply:
        print("DRY RUN -- nothing written (read-only session). Re-run with --apply.")
        return 0

    guard = f"source_council = '{LEP_COUNCIL}'" if args.scope else "source_council IS NULL"
    from dq88_refresh_2026_10_10 import version  # noqa: E402  (the shared version-history writer)
    BACKUPS.mkdir(parents=True, exist_ok=True)
    back = BACKUPS / f"sepp_marker_blind_pre_{datetime.now():%Y-%m-%dT%H%M%S}.json"
    back.write_text(json.dumps(
        [{"id": t[0], "ref_number": t[13], "provision_text": t[5], "citation_status": t[6], "citation_source_path": t[7],
          "citation_checked_at": t[8].isoformat() if t[8] else None, "version_count": t[9],
          "current_version_id": t[10], "text_hash": t[11], "text_hash_current": t[12]}
         for t in sorted(full.values())], indent=1, default=str), encoding="utf8")
    print(f"backup: {back.relative_to(ROOT)}")
    conn.rollback()
    conn.autocommit = True
    cur.execute("SET default_transaction_read_only = off")
    conn.autocommit = False
    dq108_before = probe_108(cur)[0]   # rules quoting a phrase their text lacks; a re-copy must not add any
    now = datetime.now(timezone.utc)
    for r in rows:
        # prior-art-checked: extends this file's own existing lock query (same table, same guards); adds ref_number and a version recount
        # prior-art-checked: same lock query as above in this file; document_id added (cross-review finding)
        cur.execute("SELECT md5(provision_text), ref_number, document_id, "
                    "(SELECT count(*) FROM provision_versions v WHERE v.provision_id = p.id) "
                    "FROM regulatory_provisions p WHERE id = %s AND is_current "
                    f"AND {guard} AND COALESCE(citation_status,'') <> 'proven' FOR UPDATE", (r["id"],))
        got = cur.fetchone()
        # the ref_number was part of what was verified (proven shows it as a checked clause); versions re-counted under the lock
        if got is None or got[0] != r["md5"] or got[1] != r["ref_number"] or got[2] != r["document_id"] \
                or (r["rule"] == "recopy" and got[3]):
            conn.rollback()
            print(f"ROLLED BACK: {r['id']} changed under us (text, ref_number or version history)")
            return 1
        want_md5 = r["md5"]
        if r["rule"] == "recopy":
            where = f"unit {r['unit_id']} of {r['epi']} in force on {r['law_date']}"
            version(cur, r["id"], r["new_text"], r["source"],
                    f"Stored text dropped words of this unit; re-copied from {where}.",
                    f"Stored text replaced by the verbatim words of {where} (deterministic, scripts/sepp_marker_blind.py).",
                    now)
            want_md5 = rcp.md5(r["new_text"])
        new_ref = r.get("new_ref_number")   # ref-fix rows (scripts/sepp_ref_fix.py) also replace the label
        cur.execute("UPDATE regulatory_provisions SET citation_status = 'proven', citation_source_path = %s, "
                    "citation_checked_at = now(), ref_number = COALESCE(%s, ref_number) "
                    f"WHERE id = %s AND is_current AND {guard} AND md5(provision_text) = %s AND ref_number IS NOT DISTINCT FROM %s",
                    (r["source"], new_ref, r["id"], want_md5, r["ref_number"]))
        if cur.rowcount != 1:
            conn.rollback()
            print(f"ROLLED BACK: {r['id']} text is not the planned text after the write")
            return 1
    cur.execute("SELECT id, md5(provision_text), citation_status, ref_number FROM regulatory_provisions WHERE id = ANY(%s) AND is_current", (ids,))
    now_rows = {i: (m, s, rn) for i, m, s, rn in cur.fetchall()}
    wrong = [r["id"] for r in rows
             if now_rows.get(r["id"]) != ((rcp.md5(r["new_text"]) if r["rule"] == "recopy" else r["md5"]), "proven",
                                          r.get("new_ref_number") or r["ref_number"])]
    if wrong or len(now_rows) != len(rows):
        conn.rollback()
        print(f"ROLLED BACK: {len(wrong)} rows not in the planned state (rowcount {len(now_rows)}/{len(rows)})")
        return 1
    # DQ-108: re-copied text can drop the phrase a structured numeric rule quotes (2026-10-17: 2 rows went red).
    dq108_after, hits = probe_108(cur)
    if dq108_after > dq108_before:
        conn.rollback()
        print(f"ROLLED BACK: DQ-108 {dq108_before} -> {dq108_after}; fix the rules' raw_match first: {list(hits)[:5]}")
        return 1
    conn.commit()
    print(f"WROTE {len(rows)} rows: citation_status='proven' (ref-fix rows also ref_number := new label); recopy rows also provision_text = law unit, version v1/v2.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
