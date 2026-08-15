#!/usr/bin/env python3
# prior-art-checked: reuse not viable because nothing compares the EXTRACTED-FROM
# version against the CURRENT one. r2_monitor.py runs is_reexport at fetch time
# only, against the version it is replacing, and never retrospectively — which is
# why these 9 chapters have never been asked the question. pdf_text_hash.py is the
# detector this reuses rather than reimplements. dq_probe_live.py counts DQ-70 but
# is read-only by design and takes SQL, not S3 reads. dcp_extract_changed.py has a
# _normalize_for_diff but is coupled to the heavy extraction path (boto3 +
# enrichment), which is the documented reason pdf_text_hash was split out at all.
"""DQ-70 step 1: is the source change REAL, or just a re-export?

WHY THIS EXISTS
---------------
DQ-70 says 595 served controls were read from a version of the document we no
longer hold. The obvious response is to re-extract the 9 affected chapters. That
is the dangerous option, for two recorded reasons:

  * the DCP review queue already holds 8,693 pending rows and is itself a bug
    report from two extractor bugs; re-extraction feeds it, and approving that
    queue would soft-delete ~4,950 live provisions;
  * re-extraction is whole-chapter, so it would regenerate all 333 Ashfield
    provisions to fix however many actually changed.

Before any of that, the cheap question: did the TEXT change at all? A council
re-exporting a PDF changes every byte while leaving the wording identical.
r2_monitor already knows this and runs is_reexport at fetch time -- but only
against the version it is replacing, and never retrospectively. These 9 chapters
have therefore never been asked.

WHAT IT COMPARES
----------------
The version the provisions were EXTRACTED FROM (last_extracted_version) against
the version we hold NOW (r2_version_label), both read from R2. Not the live URL:
the question is whether OUR extraction is stale relative to what we hold, and
introducing a third fetch would confuse that with a network problem.

Read-only. Touches no database row and writes nothing to R2.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

QUERY = """
SELECT p.source_council            AS council,
       r.chapter_key               AS chapter_key,
       r.chapter_label             AS chapter_label,
       count(*)                    AS served,
       r.r2_current_path           AS current_path,
       r.r2_version_label          AS current_version,
       r.last_extracted_version    AS extracted_version,
       r.url_last_changed::date    AS changed_on,
       r.last_extracted_at::date   AS extracted_on
  FROM regulatory_provisions p
  JOIN dcp_chapter_registry r
    ON r.council = p.source_council
   AND r.chapter_key = p.source_chapter_key
 WHERE p.is_current AND p.v2_is_actionable AND r.is_active
   AND r.provisions_extracted_from_hash IS NOT NULL
   AND r.content_hash IS NOT NULL
   AND r.content_hash <> r.provisions_extracted_from_hash
 GROUP BY 1,2,3,5,6,7,8,9
 ORDER BY 4 DESC
"""


def _connect():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    try:
        from dotenv import load_dotenv
        load_dotenv(REPO / ".env")
    except ImportError:
        pass
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL is not set.", file=sys.stderr)
        raise SystemExit(2)
    conn = psycopg2.connect(url)
    conn.cursor().execute("SET statement_timeout = '30000'")
    return conn, RealDictCursor


def _s3():
    import boto3
    account = os.environ["R2_ACCOUNT_ID"]
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--council", help="limit to one council")
    args = ap.parse_args()

    from pdf_text_hash import text_content_hash
    from r2_monitor import r2_path_for_version

    conn, RealDictCursor = _connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(QUERY)
    rows = [r for r in cur.fetchall()
            if not args.council or r["council"] == args.council]
    conn.close()

    s3 = _s3()
    bucket = os.environ["R2_BUCKET_NAME"]

    print(f"{len(rows)} chapters carrying DQ-70 provisions\n")
    reexport, real, unknown = [], [], []

    for r in rows:
        served = r["served"]
        label = f"{r['council']}/{r['chapter_key']}"
        old_ver, new_ver = r["extracted_version"], r["current_version"]
        print(f"{label}  ({served} served)")
        print(f"    extracted from {old_ver}  ->  now holding {new_ver}")

        if not old_ver or not r["current_path"]:
            print("    UNKNOWN: no extracted_version or no stored path recorded")
            unknown.append((r, "no version recorded"))
            continue
        if old_ver == new_ver:
            print("    UNKNOWN: extracted version EQUALS current version — the hash "
                  "differs but the labels do not, so the version bookkeeping is off")
            unknown.append((r, "version labels identical"))
            continue

        old_path = r2_path_for_version(r["current_path"], old_ver)
        try:
            old_bytes = s3.get_object(Bucket=bucket, Key=old_path)["Body"].read()
            new_bytes = s3.get_object(Bucket=bucket, Key=r["current_path"])["Body"].read()
        except Exception as exc:                                    # noqa: BLE001
            print(f"    UNKNOWN: could not read both versions from R2 ({exc.__class__.__name__})")
            unknown.append((r, f"R2 read failed: {exc}"))
            continue

        old_hash = text_content_hash(old_bytes)
        new_hash = text_content_hash(new_bytes)
        if not old_hash or not new_hash:
            print("    UNKNOWN: text could not be extracted from one or both versions")
            unknown.append((r, "no text signal"))
            continue

        same = old_hash == new_hash
        print(f"    bytes {len(old_bytes):,} -> {len(new_bytes):,}   "
              f"text {'IDENTICAL' if same else 'DIFFERS'}")
        (reexport if same else real).append(r)

    def total(group):
        return sum(x["served"] for x in group)

    print("\n" + "=" * 66)
    print(f"RE-EXPORT ONLY  (text identical) : {len(reexport):2} chapters, "
          f"{total(reexport):3} served provisions")
    print(f"REAL TEXT CHANGE                 : {len(real):2} chapters, "
          f"{total(real):3} served provisions")
    print(f"UNKNOWN (not a pass)             : {len(unknown):2} chapters, "
          f"{sum(x['served'] for x, _ in unknown):3} served provisions")
    if reexport:
        print("\nRe-exports need NO re-extraction. The provisions are current; only "
              "the recorded extraction hash is stale.")
    for r, why in unknown:
        print(f"  unknown: {r['council']}/{r['chapter_key']} — {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
