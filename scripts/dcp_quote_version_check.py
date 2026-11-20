#!/usr/bin/env python3
# prior-art-checked: scripts/dcp_quote_status.py decides, for the CURRENT chapter PDF only, whether a stored quote is printed word for word
# on its cited page (classify). This script asks the same question of each EARLIER stored version, using that same classify, so the verdict
# means the same thing. Without --apply it is read-only. With --apply it writes ONLY dcp_quote_version_check (migration 127), after a backup file.
"""Is each current control's quote on its cited page in each stored version of its chapter?

Prints one line per (control, version). A version older than the control's own file can repaginate, so 'wrong_page' there
means the words are in that file but not on the page the control cites, not that the control is wrong.

USAGE
  python scripts/dcp_quote_version_check.py --council penrith
  python scripts/dcp_quote_version_check.py --all          # every council, dry run
  python scripts/dcp_quote_version_check.py --all --apply  # back up, then upsert the verdicts into dcp_quote_version_check
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dcp_quote_status as q  # noqa: E402  (the one matcher)

ROOT = Path(__file__).resolve().parents[1]

CONTROLS_SQL = """
SELECT s.id, s.lga, s.source_chapter_key, s.control_type, s.source_text, s.pdf_page
FROM dcp_setback_controls s
WHERE s.is_current AND COALESCE(s.needs_review, false) = false AND s.dev_type = 'dwelling_house'
  AND (%(council)s::text IS NULL OR s.lga = %(council)s)
ORDER BY s.lga, s.source_chapter_key, s.id
"""
VERSIONS_SQL = """
SELECT council, chapter_key, version_label, r2_key, captured_at::date
FROM dcp_source_versions WHERE event = 'stored' AND (%(council)s::text IS NULL OR council = %(council)s)
ORDER BY council, chapter_key, captured_at
"""
# The file each active chapter is SERVED from, with its ledger row. The ledger files a PDF under the chapter named in its file name, which
# can differ from the registry chapter (Blacktown Part C is served from a file named part-4-secondary-dwellings.pdf, 2026-11-20), so a
# chapter's own list can miss the file its controls were read from.
SERVED_SQL = """
SELECT r.council, r.chapter_key, v.version_label, v.r2_key, v.captured_at::date
FROM dcp_chapter_registry r JOIN dcp_source_versions v ON v.r2_key = r.r2_current_path AND v.event = 'stored' AND v.council = r.council
WHERE r.is_active AND (%(council)s::text IS NULL OR r.council = %(council)s)
"""


def main() -> int:
    import psycopg2
    from dotenv import load_dotenv

    ap = argparse.ArgumentParser()
    ap.add_argument("--council")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if not a.council and not a.all:
        ap.error("give --council or --all")
    load_dotenv(ROOT / ".env")
    conn = psycopg2.connect(os.environ["DATABASE_URL"],
                            options="-c statement_timeout=30000" + ("" if a.apply else " -c default_transaction_read_only=on"))
    try:
        cur = conn.cursor()
        cur.execute(CONTROLS_SQL, {"council": a.council})
        controls = cur.fetchall()
        cur.execute(VERSIONS_SQL, {"council": a.council})
        versions: dict[tuple[str, str], list[tuple]] = {}
        for council, chapter, label, key, day in cur.fetchall():
            versions.setdefault((council, chapter), []).append((label, key, day))
        cur.execute(SERVED_SQL, {"council": a.council})
        for council, chapter, label, key, day in cur.fetchall():
            have = versions.setdefault((council, chapter), [])
            if key not in {k for _, k, _ in have}:
                have.append((label, key, day))
        out = _check(controls, versions)
        if not a.apply:
            print("dry run: nothing written")
            return 0
        return _write(conn, out, a.council)
    finally:
        conn.close()


def _check(controls, versions):
    s3, bucket = q._r2()
    cache: dict[str, list[str] | None] = {}
    tally: Counter = Counter()
    out: list[tuple] = []
    total = sum(len(versions.get((c[1], c[2]), [])) for c in controls)
    done = 0
    for cid, lga, chapter, ctype, quote, page in controls:
        for label, key, day in versions.get((lga, chapter), []):
            if key not in cache:
                cache[key] = q._page_texts(s3, bucket, key)
            verdict = q.classify(quote, cache[key], page)
            tally[verdict] += 1
            done += 1
            out.append((cid, key, lga, chapter, label, page, verdict, hashlib.sha256((quote or "").encode("utf-8")).hexdigest()))
            print(f"{lga}\t{chapter}\t{ctype}\tcontrol {cid}\tp{page}\t{label}\t{verdict}", flush=True)
            if done % 50 == 0:
                print(f"DONE {done}/{total}", flush=True)
    print("TOTAL", done, dict(tally))
    return out


def _write(conn, out, council) -> int:
    cur = conn.cursor()
    cur.execute("SELECT to_regclass('public.dcp_quote_version_check')")
    if cur.fetchone()[0] is None:
        print("ABORTED: table dcp_quote_version_check does not exist; apply migration 127 first.")
        return 1
    cur.execute("SELECT control_id, r2_key, verdict, quote_sha256, checked_at FROM dcp_quote_version_check"
                " WHERE (%s::text IS NULL OR council = %s)", (council, council))
    stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S")
    back = ROOT / "data" / "db_rollback_backups" / f"dcp_quote_version_check_pre_{stamp}.json"
    back.parent.mkdir(parents=True, exist_ok=True)
    back.write_text(json.dumps([[r[0], r[1], r[2], r[3], str(r[4])] for r in cur.fetchall()]))
    print("backup", back)
    ids = sorted({r[0] for r in out})
    cur.execute("SELECT count(*) FROM dcp_setback_controls WHERE id = ANY(%s) AND is_current", (ids,))
    if cur.fetchone()[0] != len(ids):
        conn.rollback()
        print("ABORTED: a control changed or was removed while checking; nothing written. Re-run.")
        return 1
    for cid, key, lga, chapter, label, page, verdict, sha in out:
        cur.execute(
            "INSERT INTO dcp_quote_version_check (control_id, r2_key, council, chapter_key, version_label, pdf_page, verdict, quote_sha256) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (control_id, r2_key) DO UPDATE SET "
            "council = EXCLUDED.council, chapter_key = EXCLUDED.chapter_key, version_label = EXCLUDED.version_label, "
            "verdict = EXCLUDED.verdict, pdf_page = EXCLUDED.pdf_page, quote_sha256 = EXCLUDED.quote_sha256, checked_at = now()",
            (cid, key, lga, chapter, label, page, verdict, sha))
    conn.commit()
    cur.execute("SELECT verdict, count(*) FROM dcp_quote_version_check GROUP BY 1")
    print("WROTE", len(out), "verdicts; table now", dict(cur.fetchall()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
