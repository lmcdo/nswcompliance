#!/usr/bin/env python3
# prior-art-checked: the safety shape (dry run by default, full backup table,
# identity-collision check before writing, printed UNDO) is copied from
# scripts/dcp_restore_section_codes.py, which repaired section_header in place
# the same way. The proof and the derivation are scripts/citation_proof.py and
# scripts/citation_derive.py, reused. Page lines come from the DQ-111 probe's
# own cached reader (dq_probe_section_code_not_in_source.chapter_lines).
"""Correct served clause numbers from the council's own page. No model calls.

WHAT IT CHANGES
---------------
For a served rule whose citation is NOT proven on its source page (DQ-111), it
reads the citation printed directly above the rule (citation_derive) and, only
if that citation PROVES and is the only answer, rewrites the same row in place:

    provision_text   first line "# <old code> <title>" -> "# <new code> <title>"
    section_header   recomputed the way a commit computes it
    ref_number       <document_id>__<new code>

The row keeps its id, so everything linked by provision id (setback controls,
applicability, versions) stays linked.

WHAT IT REFUSES
---------------
* Any citation that does not prove, or where two places or two labels prove.
* A row whose first line does not start with its stored code -- the rewrite
  would be a guess about where the code ends.
* A write that would collide with another current row's identity
  (uq_provisions_current_identity: document_id, ref_number, section_header,
  md5(provision_text)). Skipped and reported, never forced.

SAFETY
------
* Dry run by default; --apply writes. Single production database.
* --apply backs up every affected row to its own timestamped table first,
  checks the count, and refuses to write otherwise. UNDO is printed.
* Each UPDATE is pinned to the old ref_number, so a row changed since the dry
  run is left alone.
* After writing, every corrected row is proven again from the page.
* A random share (--audit-share, default 5%) is written to a CSV for a person
  to check by eye -- user decision 2026-09-24.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import random
import re
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import citation_derive as cd  # noqa: E402
import citation_proof as cp  # noqa: E402
import dq_probe_section_code_not_in_source as probe  # noqa: E402


def _norm(s: str) -> str:
    return re.sub(r"[._\s]+", " ", s or "").strip().lower()


def rewrite_heading(text: str, old_tail: str, new_code: str) -> str | None:
    """Swap the stored code at the start of '# <code> <title>' for new_code.

    None when the first line does not start with the stored code, compared with
    '.', '_' and spaces made equal ("C4_9 C5" matches "# C4.9 C5 ...").
    """
    if not text or not text.startswith("#"):
        return None
    first, sep, rest = text.partition("\n")
    heading = first.lstrip("#").strip()
    want = _norm(old_tail)
    if not want:
        return None
    for idx in range(1, len(heading) + 1):
        if _norm(heading[:idx]) == want and (idx == len(heading) or heading[idx] == " "):
            return f"# {new_code}{heading[idx:]}{sep}{rest}"
    return None


def section_header_for(new_text: str, new_ref: str, document_id: str) -> str | None:
    from scripts.dcp_commit_approved import _section_header_from_text
    return _section_header_from_text(new_text, new_ref, document_id)


def plan_council(conn, s3, bucket, cache_dir: Path, council: str | None):
    """Every planned write, plus a tally of why rows were left alone. Read-only."""
    cur = conn.cursor()
    cur.execute(probe.SERVED_SQL.replace(
        "SELECT rp.id,", "SELECT rp.document_id, rp.section_header, rp.id,")
        + (" AND rp.source_council = %s" if council else ""), (council,) if council else ())
    rows = cur.fetchall()
    by_pdf = defaultdict(list)
    for r in rows:
        by_pdf[r[6]].append(r)
    plans, tally = [], Counter()
    for r2_path, prow in by_pdf.items():
        readings = probe.chapter_lines(s3, bucket, r2_path, cache_dir)
        status = {r[2]: cp.prove_citation_any(r[5], r[7], readings, (r[8] or [None])[0])["status"]
                  for r in prow}
        lead = cd.chapter_leading([r[5].split("__")[-1].replace("_", ".")
                                   for r in prow if status[r[2]] == "proven"])
        for doc_id, header, rid, cncl, chapter, ref, _p, text, pages in prow:
            hint = (pages or [None])[0]
            now = status[rid]
            if now in ("proven", "unjudged", "text_not_found"):
                tally[f"left: {now}"] += 1
                continue
            d = cd.derive_citation(ref, text, readings, hint, lead)
            if d["status"] != "derived":
                tally[f"left: {d['status']}"] += 1
                continue
            old_tail = (ref or "").split("__")[-1]
            new_text = rewrite_heading(text, old_tail, d["code"])
            if new_text is None or not (ref or "").startswith(f"{doc_id}__"):
                tally["left: first line does not start with the stored code"] += 1
                continue
            new_ref = f"{doc_id}__{d['code'].replace('.', '_')}"
            new_header = section_header_for(new_text, new_ref, doc_id)
            plans.append({"id": rid, "council": cncl, "chapter": chapter, "document_id": doc_id,
                          "old_ref": ref, "new_ref": new_ref, "old_header": header,
                          "new_header": new_header, "new_text": new_text, "r2_path": r2_path,
                          "page": hint})
            tally["planned"] += 1
    return plans, tally


def drop_collisions(conn, plans):
    """Remove planned writes that would collide with another current row's
    identity, or with each other. Returns (kept, collisions)."""
    cur = conn.cursor()
    seen, kept, clashes = set(), [], []
    for p in plans:
        key = (p["document_id"], p["new_ref"], p["new_header"] or "",
               hashlib.md5(p["new_text"].encode()).hexdigest())
        cur.execute(
            "SELECT id FROM regulatory_provisions WHERE is_current AND id <> %s "
            "AND COALESCE(document_id,'') = %s AND COALESCE(ref_number,'') = %s "
            "AND COALESCE(section_header,'') = %s AND md5(provision_text) = %s LIMIT 1",
            (p["id"], key[0], key[1], key[2], key[3]))
        if cur.fetchone() or key in seen:
            clashes.append(p)
            continue
        seen.add(key)
        kept.append(p)
    return kept, clashes


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().splitlines()[0])
    ap.add_argument("--council", help="Limit to one council (the pilot).")
    ap.add_argument("--apply", action="store_true", help="Write. Without it nothing changes.")
    ap.add_argument("--audit-share", type=float, default=0.05)
    ap.add_argument("--cache-dir", default=str(Path(tempfile.gettempdir()) / "dq111_lines"))
    args = ap.parse_args()

    import boto3
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30000'")
        s3 = boto3.client(
            "s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
        cache_dir = Path(args.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        plans, tally = plan_council(conn, s3, os.environ["R2_BUCKET_NAME"], cache_dir, args.council)
        plans, clashes = drop_collisions(conn, plans)
        print(f"scope: {args.council or 'all councils'}")
        for k, n in tally.most_common():
            print(f"  {n:6}  {k}")
        print(f"  {len(clashes):6}  left: would collide with another current row")
        print(f"  {len(plans):6}  WILL CORRECT")
        for p in plans[:12]:
            print(f"    {p['old_ref'].split('__')[-1]:>22}  ->  {p['new_ref'].split('__')[-1]}")
        if not args.apply:
            print("\nDRY RUN -- nothing written. Re-run with --apply to write.")
            return 0
        if not plans:
            print("Nothing to write.")
            return 0

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = f"regulatory_provisions_citation_backup_{stamp}"
        ids = [p["id"] for p in plans]
        cur.execute(f"CREATE TABLE {backup} AS SELECT id, ref_number, section_header, provision_text "
                    f"FROM regulatory_provisions WHERE id = ANY(%s)", (ids,))
        cur.execute(f"SELECT count(*) FROM {backup}")
        if cur.fetchone()[0] != len(ids):
            conn.rollback()
            print("FATAL: backup count does not match the planned rows; nothing written.")
            return 2
        written = 0
        for p in plans:
            cur.execute("UPDATE regulatory_provisions SET ref_number = %s, section_header = %s, "
                        "provision_text = %s WHERE id = %s AND is_current AND ref_number = %s",
                        (p["new_ref"], p["new_header"], p["new_text"], p["id"], p["old_ref"]))
            written += cur.rowcount
        conn.commit()
        print(f"\nWROTE {written} of {len(plans)} rows.  backup: {backup}")
        print(f"UNDO:  UPDATE regulatory_provisions p SET ref_number = b.ref_number, "
              f"section_header = b.section_header, provision_text = b.provision_text "
              f"FROM {backup} b WHERE p.id = b.id;")

        # Prove every corrected row again, from the page, as served now.
        still = 0
        by_pdf = defaultdict(list)
        for p in plans:
            by_pdf[p["r2_path"]].append(p)
        for r2_path, ps in by_pdf.items():
            readings = probe.chapter_lines(s3, os.environ["R2_BUCKET_NAME"], r2_path, cache_dir)
            for p in ps:
                if cp.prove_citation_any(p["new_ref"], p["new_text"], readings,
                                         p["page"])["status"] != "proven":
                    still += 1
        print(f"re-proven after write: {len(plans) - still} of {len(plans)}"
              + ("" if not still else f"  -- {still} NOT proven, investigate before continuing"))

        sample = random.Random(stamp).sample(plans, max(1, round(len(plans) * args.audit_share)))
        out = ROOT / "data" / f"citation_fix_audit_{stamp}.csv"
        out.parent.mkdir(exist_ok=True)
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "council", "chapter", "old_citation", "new_citation", "page", "source"])
            for p in sample:
                w.writerow([p["id"], p["council"], p["chapter"], p["old_ref"].split("__")[-1],
                            p["new_ref"].split("__")[-1], p["page"], p["r2_path"]])
        print(f"AUDIT: {len(sample)} rows for a person to check by eye -> {out}")
        return 0 if not still else 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
