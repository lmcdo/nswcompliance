#!/usr/bin/env python3
# prior-art-checked: reuses dcp_extract_changed.extract_chapter for the actual commit
# (no duplicated commit logic). The guard's candidates (for-property route, DAModeCard,
# TocSidebar, blog pages) are unrelated frontend provision-display; no commit-approved
# worker exists in the repo.
"""
DCP Commit-Approved Worker — the governance commit gate.

Commits a DCP chapter to regulatory_provisions ONLY when a human has approved
every queued change for it. This is the back half of the review loop:

    detect -> extract-to-review (enqueue) -> human approves in /internal/dcp-review
    -> THIS WORKER commits the approved chapter

Commit gate (per chapter): every dcp_review_queue row for the chapter is
'approved' -- a single 'pending' / 'in_progress' / 'rejected' / 'needs_info' row
holds the whole chapter (you investigate the source instead). Re-extraction is
chapter-level, so approval is too.

Currency guard: the chapter's current dcp_chapter_registry.content_hash must
still match the source_content_hash the human approved. If the PDF changed since
review, the approval is stale -- the chapter is NOT committed (it will re-enter
the review queue on the next extract run).

Reuse: the actual commit is dcp_extract_changed.extract_chapter(..., review=False)
-- the existing atomic per-chapter path (soft-delete old, insert new, clear
needs_extraction). No commit logic is duplicated here.

Usage:
    python scripts/dcp_commit_approved.py            # DRY RUN (default -- reports only)
    python scripts/dcp_commit_approved.py --commit   # actually commit approved chapters

Exit codes:
    0 = nothing to commit (no fully-approved chapters)
    1 = a chapter was attempted and failed
    2 = at least one chapter committed (or, in dry-run, would commit)
"""

import argparse
import sys
from pathlib import Path

# dcp_extract_changed sets up R2_* / DATABASE_URL from env and pulls in enrichment.*;
# importing it requires the same env as the extractor (DATABASE_URL + R2_* creds).
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import boto3       # noqa: E402
import psycopg2    # noqa: E402

import dcp_extract_changed as dx  # noqa: E402


def find_committable_chapters(cur) -> list[dict]:
    """Chapters whose every queued change is approved (none blocking)."""
    cur.execute(
        """
        SELECT council, chapter_key,
               COUNT(*) FILTER (WHERE status = 'approved') AS approved,
               COUNT(*) FILTER (
                   WHERE status IN ('pending', 'in_progress', 'rejected', 'needs_info')
               ) AS blocking,
               MAX(source_content_hash) AS approved_hash,
               COUNT(DISTINCT source_content_hash) AS hash_variants
        FROM dcp_review_queue
        GROUP BY council, chapter_key
        HAVING COUNT(*) FILTER (WHERE status = 'approved') > 0
           AND COUNT(*) FILTER (
                   WHERE status IN ('pending', 'in_progress', 'rejected', 'needs_info')
               ) = 0
        ORDER BY council, chapter_key
        """
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def fetch_registry_chapter(cur, council: str, chapter_key: str) -> dict | None:
    """Registry row for a still-flagged chapter (needs_extraction=TRUE)."""
    cur.execute(
        """
        SELECT id, council, chapter_key, chapter_label,
               r2_current_path, r2_version_label, dcp_name, content_hash
        FROM dcp_chapter_registry
        WHERE council = %s AND chapter_key = %s
          AND needs_extraction = TRUE
          AND is_active = TRUE
          AND r2_current_path IS NOT NULL
        """,
        (council, chapter_key),
    )
    row = cur.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def main() -> int:
    parser = argparse.ArgumentParser(description="Commit human-approved DCP chapters.")
    parser.add_argument(
        "--commit", action="store_true",
        help="Actually commit. Without this flag the worker is a dry run (reports only).",
    )
    args = parser.parse_args()
    dry_run = not args.commit

    conn = psycopg2.connect(dx.DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    candidates = find_committable_chapters(cur)
    if not candidates:
        print("Nothing to commit -- no fully-approved chapters in dcp_review_queue.")
        cur.close()
        conn.close()
        return 0

    s3 = boto3.client(
        "s3",
        endpoint_url=dx.R2_ENDPOINT,
        aws_access_key_id=dx.R2_ACCESS_KEY_ID,
        aws_secret_access_key=dx.R2_SECRET_ACCESS_KEY,
    )

    print("=" * 60)
    print(f"DCP COMMIT-APPROVED {'(DRY RUN)' if dry_run else '(COMMITTING)'}")
    print("=" * 60)
    print(f"Fully-approved chapters: {len(candidates)}")

    committed = 0
    failed = 0
    skipped = 0

    for cand in candidates:
        council = cand["council"]
        chapter_key = cand["chapter_key"]
        approved_hash = cand["approved_hash"]

        chapter = fetch_registry_chapter(cur, council, chapter_key)
        if chapter is None:
            print(f"  [skip] {council}/{chapter_key} -- not flagged for extraction "
                  f"(already committed or inactive).")
            skipped += 1
            continue

        # Currency guard: don't commit a stale approval.
        if cand["hash_variants"] and cand["hash_variants"] > 1:
            print(f"  [skip] {council}/{chapter_key} -- approved rows span multiple "
                  f"source hashes; re-review required.")
            skipped += 1
            continue
        if approved_hash is not None and chapter.get("content_hash") != approved_hash:
            print(f"  [skip] {council}/{chapter_key} -- PDF changed since review "
                  f"(registry hash != approved hash). Stale approval; will re-queue.")
            skipped += 1
            continue

        if dry_run:
            print(f"  [would commit] {council}/{chapter_key}")
            committed += 1
            continue

        ok, _ = dx.extract_chapter(chapter, s3, conn, dry_run=False, review=False)
        if ok:
            print(f"  [committed] {council}/{chapter_key}")
            committed += 1
        else:
            print(f"  [FAILED] {council}/{chapter_key} -- extract_chapter rolled back; "
                  f"needs_extraction stays TRUE for retry.")
            failed += 1

    cur.close()
    conn.close()

    print("-" * 60)
    verb = "would commit" if dry_run else "committed"
    print(f"  {verb}: {committed}   failed: {failed}   skipped: {skipped}")

    if failed:
        return 1
    return 2 if committed else 0


if __name__ == "__main__":
    sys.exit(main())
