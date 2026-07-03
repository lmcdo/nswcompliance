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
    """Registry row for an active chapter. Not gated on needs_extraction: an approved
    chapter is committed whether the monitor flagged it or it was extracted on-demand
    (e.g. an initial AI baseline swap).
    prior-art-checked: reuse not viable because this is the existing DCP commit worker's
    own registry lookup (this file); the flagged matches are unrelated SEPP/legislation
    extraction modules, not the DCP review-queue commit path."""
    cur.execute(
        """
        SELECT id, council, chapter_key, chapter_label,
               r2_current_path, r2_version_label, dcp_name, content_hash
        FROM dcp_chapter_registry
        WHERE council = %s AND chapter_key = %s
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


def _section_header_from_text(new_text: str) -> str | None:
    """The reviewed new_text starts with '# <code> <title>' (build_provision_text);
    recover that heading line for section_header. None for preamble/headerless text."""
    if new_text and new_text.startswith("#"):
        head = new_text.partition("\n")[0].lstrip("# ").strip()
        return head or None
    return None


def commit_reviewed_from_queue(cur, council: str, chapter_key: str) -> tuple[int, int]:
    """Make the HUMAN-APPROVED review-queue text the live provisions — verbatim, no
    re-extraction (which for non-deterministic AI would commit different, unreviewed
    text). Soft-delete is reversible (is_current=FALSE keeps the old rows).

    Two modes, from is_full_replace stored at enqueue:
      * FULL REPLACE (restructure / empty baseline, or legacy NULL) — the queue holds the
        whole chapter, so blanket soft-delete the chapter's current provisions, then
        insert every approved non-removed row.
      * TARGETED (an amendment where only some provisions changed) — the queue holds only
        the changes, so supersede ONLY the refs that are changed/removed/re-added and leave
        every unchanged provision intact. A blanket delete here would drop the unchanged
        rules.
    Returns (superseded, inserted)."""
    cur.execute(
        """
        SELECT bool_or(is_full_replace) FROM dcp_review_queue
        WHERE council = %s AND chapter_key = %s AND status = 'approved'
        """,
        (council, chapter_key),
    )
    row = cur.fetchone()
    # NULL (legacy rows) -> full replace: the pre-054 baseline is all full re-extractions.
    full_replace = True if (row is None or row[0] is None) else bool(row[0])

    superseded = 0
    if full_replace:
        cur.execute(
            """
            UPDATE regulatory_provisions
            SET is_current = FALSE
            WHERE source_council = %s AND source_chapter_key = %s AND is_current = TRUE
            """,
            (council, chapter_key),
        )
        superseded = cur.rowcount

    cur.execute(
        """
        SELECT document_id, ref_number, new_text, new_page, change_type
        FROM dcp_review_queue
        WHERE council = %s AND chapter_key = %s AND status = 'approved'
        ORDER BY id
        """,
        (council, chapter_key),
    )
    rows = cur.fetchall()
    inserted = 0
    for document_id, ref_number, new_text, new_page, change_type in rows:
        if not full_replace:
            # Targeted: supersede ONLY this ref's current version (changed / removed /
            # re-added). Unchanged provisions are never named here, so they stay live.
            cur.execute(
                """
                UPDATE regulatory_provisions SET is_current = FALSE
                WHERE source_council = %s AND source_chapter_key = %s
                  AND ref_number = %s AND is_current = TRUE
                """,
                (council, chapter_key, ref_number),
            )
            superseded += cur.rowcount
        if change_type == "removed" or not new_text:
            continue
        v2_actionable = False if str(ref_number).endswith("preamble") else None
        page_range = [new_page] if new_page is not None else None
        cur.execute(
            """
            INSERT INTO regulatory_provisions (
                document_id, ref_number, section_header, provision_text, pdf_page,
                pdf_source_file, page_range, extraction_method,
                source_chapter_key, source_council, is_current, v2_is_actionable
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,'ai-reviewed',%s,%s,TRUE,%s)
            """,
            (
                document_id, ref_number, _section_header_from_text(new_text),
                new_text, new_page, chapter_key, page_range,
                chapter_key, council, v2_actionable,
            ),
        )
        inserted += 1
    return superseded, inserted


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
            cur.execute(
                "SELECT COUNT(*) FROM dcp_review_queue WHERE council=%s AND chapter_key=%s "
                "AND status='approved' AND change_type <> 'removed' AND new_text IS NOT NULL",
                (council, chapter_key),
            )
            n = cur.fetchone()[0]
            print(f"  [would commit] {council}/{chapter_key} -- {n} reviewed provisions")
            committed += 1
            continue

        try:
            # prior-art-checked: reuse not viable because the flagged matches are the
            # separate SEPP full-text import scripts; this is the DCP review-queue commit
            # path, writing dcp_review_queue-approved rows into regulatory_provisions.
            superseded, inserted = commit_reviewed_from_queue(cur, council, chapter_key)
            # Resolve the worklist: the reviewed provisions are now live. The status
            # enum has no 'committed', so the resolved rows are deleted (the permanent
            # record is regulatory_provisions, extraction_method='ai-reviewed').
            cur.execute(
                "DELETE FROM dcp_review_queue WHERE council=%s AND chapter_key=%s AND status='approved'",
                (council, chapter_key),
            )
            cur.execute(
                "UPDATE dcp_chapter_registry SET needs_extraction=FALSE WHERE council=%s AND chapter_key=%s",
                (council, chapter_key),
            )
            conn.commit()
            print(f"  [committed] {council}/{chapter_key} -- {inserted} reviewed provisions "
                  f"live ({superseded} superseded)")
            committed += 1
        except Exception as exc:
            conn.rollback()
            print(f"  [FAILED] {council}/{chapter_key} -- {exc}; rolled back, approval kept.")
            failed += 1

    cur.close()
    conn.close()

    # Enrichment: reviewed provisions are inserted with v2_is_actionable / v2_topic /
    # v2_applicable_dev_types UNSET. The end-user UI filters and groups by exactly those
    # tags, so a committed-but-unenriched council is effectively invisible in the UI. Run
    # the same three-phase enrichment the extraction path runs (dcp_extract_changed) so a
    # published council is immediately usable. The phases process only v2_is_actionable
    # IS NULL rows, so they touch just the freshly committed provisions and are idempotent.
    # Wrapped: an enrichment error must NOT fail the already-committed provisions — they can
    # be re-enriched — so it degrades to a loud warning, not a rollback.
    if committed and not dry_run:
        print("Enriching newly committed provisions (actionability -> topics -> applicability)...")
        try:
            from enrichment.pipeline import (
                run_actionability_classification,
                run_layer_tagging,
                run_applicability_tagging,
            )
            run_actionability_classification(batch_size=500)
            run_layer_tagging(batch_size=500)
            run_applicability_tagging(batch_size=500)
            print("  enrichment complete.")
        except Exception as exc:  # noqa: BLE001 — never fail a committed provision on enrichment
            print(f"  [warn] enrichment failed: {exc}. Provisions ARE committed but untagged; "
                  f"re-run enrichment (they will not show correctly in the UI until you do).")

    print("-" * 60)
    verb = "would commit" if dry_run else "committed"
    print(f"  {verb}: {committed}   failed: {failed}   skipped: {skipped}")

    if failed:
        return 1
    return 2 if committed else 0


if __name__ == "__main__":
    sys.exit(main())
