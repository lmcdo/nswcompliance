#!/usr/bin/env python3
"""Apply data/campbelltown_visible_text_plan_<date>.json: provision_text := the text without the PDF's invisible white copy. DRY RUN by default.

prior-art-checked: write path = scripts/dq88_refresh_2026_10_10.version (the shared version-history writer; its
fixed v1 change_summary / extraction_method wording is about the law refresh -- the v2 `why` carries ours);
guards and DQ-108 before/after in one transaction mirror scripts/apply_sepp_marker_blind.py. The plan is
re-derived, not trusted: every row's new_text is re-proven against the VISIBLE-only text of the pinned PDF
(scripts/visible_text_repair.on_visible) before anything is written.

Refuses, writing nothing, when: the PDF sha256 differs from the plan; a row is not current/served, its md5
differs from the plan, it already has version history, or its new text no longer proves on the visible page.
--apply backs the rows up to data/db_rollback_backups/ first, locks each row FOR UPDATE, writes in ONE
transaction, and rolls back if any rowcount/state differs or DQ-108 rises. page_check is not touched: a fix
row's new text proves on a page it already points at, so an on_page row stays on_page.

    python scripts/apply_visible_text_repair.py data/campbelltown_visible_text_plan_2026-10-17.json PDF [--apply]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import page_evidence as pe  # noqa: E402
import visible_text_repair as vtr  # noqa: E402
from state_law_proof import ROOT, connect  # noqa: E402
from dq_probe_unchecked_rows import probe_108  # noqa: E402

BACKUPS = ROOT / "data" / "db_rollback_backups"
SELECT = ("SELECT id, md5(provision_text), is_current, v2_is_actionable, source_chapter_key, provision_text, pdf_page, "
          "page_range, page_check, citation_status, version_count, current_version_id, text_hash, text_hash_current, "
          "(SELECT count(*) FROM provision_versions v WHERE v.provision_id = p.id) "
          "FROM regulatory_provisions p WHERE source_council = 'campbelltown' AND id = ANY(%s)")


def check(rows: list[dict], full: dict, vis: dict) -> list[str]:
    """Reasons to refuse. Pure."""
    bad = []
    for r in rows:
        t = full.get(r["id"])
        if t is None:
            bad.append(f"{r['id']}: not a Campbelltown row any more")
            continue
        if not (t[2] and t[3]) or t[4] != vtr.CHAPTER:
            bad.append(f"{r['id']}: no longer current/served in {vtr.CHAPTER}")
        if t[1] != r["md5"]:
            bad.append(f"{r['id']}: provision_text md5 changed since the plan")
        if t[14]:
            bad.append(f"{r['id']}: already has {t[14]} version rows")
        # Re-derive the fix from the stored text, never trust the plan's new_text (cross-review 2026-10-17)
        d = vtr.plan_row({"id": t[0], "provision_text": t[5], "pdf_page": t[6], "page_range": t[7]}, vis)
        if d.get("verdict") != "fix" or d.get("new_text") != r["new_text"]:
            bad.append(f"{r['id']}: re-derived {d.get('verdict')} ({d.get('reason')}), not the plan's new text")
    return bad


R2 = "https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/"


def registry_pdf_sha() -> str | None:
    """sha256 of the chapter PDF dcp_chapter_registry says is in force (is_active, exactly one row), fetched from R2."""
    import hashlib as _h
    import urllib.request
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = 30000")
        cur.execute("SELECT r2_current_path FROM dcp_chapter_registry WHERE is_active AND council = 'campbelltown' "
                    "AND chapter_key = %s", (vtr.CHAPTER,))
        paths = [x[0] for x in cur.fetchall()]
    finally:
        conn.close()
    if len(paths) != 1 or not paths[0]:
        return None
    req = urllib.request.Request(R2 + paths[0], headers={"User-Agent": "Mozilla/5.0 (compliance-engine)"})
    with urllib.request.urlopen(req, timeout=60) as f:
        return _h.sha256(f.read()).hexdigest()


def reprove(conn, rows: list[dict], vis: dict, apply: bool) -> int:
    """After the write: the page_check trigger (migration 079) clears page_check when provision_text changes. Re-record
    'on_page' for each repaired row whose CURRENT text is one run of the visible text of its held page, through
    dcp_page_repair.write (the page proof's own writer, which also checks the PDF is the chapter's current one).
    prior-art-checked: REUSES dcp_page_repair.write for the write; the suggested files (provisions routes, orphan
    cleanup, enrichment pipeline) neither prove a page nor read visible-only text."""
    import dcp_page_repair as dpr
    cur = conn.cursor()
    cur.execute("SELECT id, provision_text, md5(provision_text), pdf_page, page_range, printed_page_label, "
                "page_source_path, page_check FROM regulatory_provisions WHERE id = ANY(%s) AND is_current "
                "AND source_council = 'campbelltown'", ([r["id"] for r in rows],))
    now = {t[0]: t for t in cur.fetchall()}
    # the trigger clears page_source_path too: the chapter's PDF in force is the registry's (dpr.write re-checks it)
    cur.execute("SELECT r2_current_path FROM dcp_chapter_registry WHERE is_active AND council = 'campbelltown' "
                "AND chapter_key = %s", (vtr.CHAPTER,))
    reg = [x[0] for x in cur.fetchall()]
    src_now = reg[0] if len(reg) == 1 else None
    todo, skipped = [], []
    for r in rows:
        t = now.get(r["id"])
        if t is None or t[2] != hashlib.md5(r["new_text"].encode("utf-8")).hexdigest():
            skipped.append((r["id"], "text is not the repaired text"))
            continue
        if t[7] in ("on_page", "moved"):
            continue
        held = set(t[4] or []) | ({t[3]} if t[3] else set())
        ev = vtr.on_visible(pe.rule_words(t[1]), vis, held, t[3])
        src = t[6] or src_now
        if ev is None or not src:
            skipped.append((r["id"], "not on the visible page of its held page" if ev is None else "no chapter PDF path"))
            continue
        todo.append({"id": t[0], "pdf_page": ev["page"], "page_range": t[4], "printed_page_label": t[5],
                     "page_check": "on_page", "page_source_path": src})
    print(f"re-prove: {len(todo)} rows on the visible page; skipped {len(skipped)} {skipped[:5]}")
    if skipped:   # a repaired row left without a page proof is a failure, not a partial success (cross-review)
        print("REFUSING: every repaired row must re-prove on its visible page")
        return 1
    if not apply or not todo:
        return 0
    n = dpr.write(conn, todo)
    print(f"re-proved {n} of {len(todo)} (page_check = on_page)")
    return 0 if n == len(todo) else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("pdf")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--reprove", action="store_true",
                    help="after the repair: re-record page_check on_page for repaired rows proven on the visible page")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text(encoding="utf8"))
    sha = pe.sha256_file(a.pdf)
    if sha != plan["pdf_sha256"]:
        print(f"REFUSING: PDF sha256 {sha[:12]} != plan {plan['pdf_sha256'][:12]}")
        return 1
    reg_sha = registry_pdf_sha()
    if reg_sha != sha:
        print(f"REFUSING: the PDF is not the chapter's PDF in force (registry file sha256 {str(reg_sha)[:12]}, given {sha[:12]})")
        return 1
    import fitz
    with fitz.open(a.pdf) as doc:
        vis = {n: vtr.visible_texts(p) for n, p in enumerate(doc, 1)}
    rows = plan["rows"]
    ids = [r["id"] for r in rows]
    conn = connect()
    cur = conn.cursor()
    cur.execute("SET statement_timeout = 30000")
    if a.reprove:
        if a.apply:
            conn.rollback()
            conn.autocommit = True
            cur.execute("SET default_transaction_read_only = off")
            conn.autocommit = False
        return reprove(conn, rows, vis, a.apply)
    cur.execute(SELECT, (ids,))
    full = {t[0]: t for t in cur.fetchall()}
    bad = check(rows, full, vis)
    if bad:
        print(f"REFUSING: {len(bad)} problems; first 10:")
        print("\n".join(bad[:10]))
        return 1
    print(f"{len(rows)} rows verified: current, md5 = plan, no version history, new text on the visible page.")
    if not a.apply:
        print("DRY RUN -- nothing written. Re-run with --apply.")
        return 0

    from dq88_refresh_2026_10_10 import version  # shared version-history writer
    BACKUPS.mkdir(parents=True, exist_ok=True)
    back = BACKUPS / f"campbelltown_visible_text_pre_{datetime.now():%Y-%m-%dT%H%M%S}.json"
    back.write_text(json.dumps([{"id": t[0], "provision_text": t[5], "pdf_page": t[6], "page_range": t[7],
                                 "page_check": t[8], "citation_status": t[9], "version_count": t[10],
                                 "current_version_id": t[11], "text_hash": t[12], "text_hash_current": t[13]}
                                for t in sorted(full.values())], indent=1, default=str), encoding="utf8")
    print(f"backup: {back.relative_to(ROOT)}")
    conn.rollback()
    conn.autocommit = True
    cur.execute("SET default_transaction_read_only = off")
    conn.autocommit = False
    before = probe_108(cur)[0]
    now = datetime.now(timezone.utc)
    src = "campbelltown-dcp-part3-low-medium.pdf sha256 " + sha
    for r in rows:
        cur.execute("SELECT md5(provision_text), (SELECT count(*) FROM provision_versions v WHERE v.provision_id = p.id) "
                    "FROM regulatory_provisions p WHERE id = %s AND is_current AND v2_is_actionable AND source_council = 'campbelltown' "
                    "FOR UPDATE", (r["id"],))
        got = cur.fetchone()
        if got is None or got[0] != r["md5"] or got[1]:
            conn.rollback()
            print(f"ROLLED BACK: {r['id']} changed under us")
            return 1
        version(cur, r["id"], r["new_text"], src, "visible-text repair 2026-10-17",
                "Stored text carried the PDF's invisible white copy of each line; replaced by the visible text "
                "only (deterministic, scripts/visible_text_repair.py).", now)
    cur.execute("SELECT id, md5(provision_text) FROM regulatory_provisions WHERE id = ANY(%s) AND is_current", (ids,))
    now_rows = dict(cur.fetchall())
    wrong = [r["id"] for r in rows if now_rows.get(r["id"]) != hashlib.md5(r["new_text"].encode("utf-8")).hexdigest()]
    if wrong or len(now_rows) != len(rows):
        conn.rollback()
        print(f"ROLLED BACK: {len(wrong)} rows not in the planned state")
        return 1
    after, hits = probe_108(cur)
    if after > before:
        conn.rollback()
        print(f"ROLLED BACK: DQ-108 {before} -> {after}: {list(hits)[:5]}")
        return 1
    conn.commit()
    print(f"WROTE {len(rows)} rows (version history v1/v2); DQ-108 {before} -> {after}.")
    # migration 079's trigger cleared page_check on every changed row: re-prove them now, not as an optional step
    conn.autocommit = False
    return reprove(conn, rows, vis, True)


if __name__ == "__main__":
    sys.exit(main())
