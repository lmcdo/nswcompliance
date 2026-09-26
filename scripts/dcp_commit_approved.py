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
# Refuses a swap that would lose most of a chapter's sections. See the module docstring.
from scripts.dcp_supersede_guard import enforce as enforce_section_loss  # noqa: E402
from scripts.dcp_supersede_guard import snapshot as section_snapshot  # noqa: E402
from scripts.dcp_supersede_guard import enforce_fidelity, enforce_legibility  # noqa: E402


def find_committable_chapters(cur) -> list[dict]:
    """Chapters whose every queued change is approved (none blocking).

    'rejected' blocks ONLY while it belongs to the chapter's CURRENT content
    hash. Historically any rejected row blocked its chapter forever: the
    re-extract refresh deletes pending rows only, so one rejection of a bad
    extraction would have wedged the chapter permanently even after a clean
    re-extraction superseded it (2026-07 triage finding). Superseded rejected
    rows stay in the table as audit history; they just stop blocking.
    """
    # approved_hash and hash_variants describe the APPROVED rows only. Until 2026-09-15 both
    # were taken over every queue row, so a chapter's superseded or rejected history from an
    # earlier PDF counted as a second version of its approval: every Woollahra chapter then had
    # 2-3 hashes across its queue and 1 among its approved rows, and would have been skipped as
    # "approved rows span multiple source hashes" (or as stale, when MAX picked the old hash)
    # however carefully its current rows were reviewed. Mixed approvals are still caught.
    cur.execute(
        """
        SELECT q.council, q.chapter_key,
               COUNT(*) FILTER (WHERE q.status = 'approved') AS approved,
               COUNT(*) FILTER (
                   WHERE q.status IN ('pending', 'in_progress', 'needs_info')
                      OR (q.status = 'rejected'
                          AND q.source_content_hash = r.content_hash)
               ) AS blocking,
               MAX(q.source_content_hash) FILTER (WHERE q.status = 'approved') AS approved_hash,
               COUNT(DISTINCT q.source_content_hash) FILTER (WHERE q.status = 'approved') AS hash_variants
        FROM dcp_review_queue q
        JOIN dcp_chapter_registry r
          ON r.council = q.council AND r.chapter_key = q.chapter_key
         AND r.is_active = TRUE
        GROUP BY q.council, q.chapter_key
        HAVING COUNT(*) FILTER (WHERE q.status = 'approved') > 0
           AND COUNT(*) FILTER (
                   WHERE q.status IN ('pending', 'in_progress', 'needs_info')
                      OR (q.status = 'rejected'
                          AND q.source_content_hash = r.content_hash)
               ) = 0
        ORDER BY q.council, q.chapter_key
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


def _section_header_from_text(new_text: str, ref_number: str | None = None,
                             document_id: str | None = None) -> str | None:
    """The reviewed new_text starts with '# <code> <title>' (build_provision_text);
    recover that heading line for section_header. None for preamble/headerless text.

    WHY ref_number IS A FALLBACK HERE (2026-09-12)
    ----------------------------------------------
    The heading line does not always carry the section code. Measured over the
    12,124 live rows, 3,501 section_headers hold no code at all -- "Residential
    parking generation rates", "Local Character and Streetscape" -- and a
    provision with no code cannot be looked up by section, which is how the
    product is asked for it.

    The code was not lost. It is in ref_number (E1_4_2, 4a_1, 1_1) and was simply
    never copied across. 2,330 of those rows are recoverable.

    This fallback is what makes that repair DURABLE. Without it this function
    recomputes section_header on EVERY commit from the heading line alone, so
    scripts/dcp_restore_section_codes.py would be undone the next time each
    chapter was committed -- the same shape as
    project-precinct-keys-nulled-on-every-commit-2026-09, where a derived field
    was silently reset by the pipeline that should have preserved it.

    The heading line still WINS wherever it carries a code: that came from the
    document, while the ref_number code is an inference. The fallback only fills
    a gap, and returns None rather than inventing a code it cannot read.
    """
    head = None
    if new_text and new_text.startswith("#"):
        head = new_text.partition("\n")[0].lstrip("# ").strip() or None
    try:
        from scripts.dcp_section_code import repaired_header
    except ImportError:  # running from inside scripts/
        try:
            from dcp_section_code import repaired_header
        except ImportError:
            return head
    return repaired_header(head, ref_number, document_id) or head


def latest_approved_batch(cur, council: str, chapter_key: str):
    """The created_at of the most recent extraction run whose rows are approved.

    A run is exactly one timestamp. dcp_review_queue.created_at DEFAULTs to now(), which
    in PostgreSQL is TRANSACTION time, and dcp_extract_changed.py enqueues a chapter's
    rows inside one transaction, so every row of a run carries the same created_at to the
    microsecond. Measured 2026-09-19: city_of_sydney/section-3-general-provisions holds
    312 approved rows under 3 stamps, canterbury_bankstown/chapter-6-2 118 under 2, and
    every single-run chapter 1; across all statuses there are 117 (chapter, timestamp)
    groups averaging 89 rows and peaking at 1,573.

    Why a run and not a ref: approved rows accumulate across repeated reviews of an
    UNCHANGED document, and every batch was being inserted, so the second copy of a
    provision hit uq_provisions_current_identity and rolled the whole chapter back.
    Deduplicating by ref_number instead would be wrong in the other direction -- that
    index is (document_id, ref_number, section_header, md5(provision_text)), so two live
    provisions may legitimately share a ref_number, and five such pairs exist today. A run
    is the only boundary that separates a re-read from a second provision.

    Returns (timestamp, rows_in_batch) and (None, 0) when nothing is approved.
    """
    cur.execute(
        """
        SELECT created_at, COUNT(*) FROM dcp_review_queue
        WHERE council = %s AND chapter_key = %s AND status = 'approved'
        GROUP BY created_at ORDER BY created_at DESC
        """,
        (council, chapter_key),
    )
    batches = cur.fetchall()
    if not batches:
        return None, 0
    # If created_at ever stops being transaction time -- a writer switching to
    # clock_timestamp(), or rows enqueued one transaction each -- every "run" becomes a
    # single row, and taking the newest would commit one provision while reporting the
    # chapter committed. That is the silent version of this bug, so refuse instead.
    #
    # The test is the SHAPE of the distribution, not its mean. An average would be dragged
    # above the threshold by one large historical batch: 100 rows from July beside a single
    # stray row stamped today averages 50, passes, and commits the stray row alone. What
    # actually distinguishes per-row stamping is that most timestamps hold one row --
    # whereas a targeted amendment, legitimately one changed rule enqueued after a full
    # read, is one single among a majority that are not.
    singles = sum(1 for _ts, n in batches if n < 2)
    if len(batches) > 1 and singles * 2 > len(batches):
        total = sum(n for _ts, n in batches)
        raise RuntimeError(
            f"{council}/{chapter_key}: {total} approved row(s) under {len(batches)} "
            f"created_at values, {singles} of them holding a single row. A run should be "
            f"one transaction and one timestamp, so the newest run cannot be identified "
            f"and committing it would commit a fragment. Re-queue the chapter.")
    return batches[0][0], batches[0][1]


def commit_reviewed_from_queue(cur, council: str, chapter_key: str,
                               allow_unqueued: bool = False) -> tuple[int, int]:
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
    # One run, read once, and used by every query below. The mode, the section-loss guard
    # and the insert must all judge the SAME rows: a guard that reads the whole approved
    # history while the insert reads one run would pass a chapter whose live rule is only
    # in an older run, then not insert it -- a silent loss, which is the failure this
    # function exists to prevent.
    batch_ts, _batch_rows = latest_approved_batch(cur, council, chapter_key)
    if batch_ts is None:
        # Nothing approved. Returning here rather than falling through is the whole point:
        # every query below is scoped to batch_ts, so with NULL they match nothing --
        # bool_or over no rows is NULL, which this function reads as a FULL REPLACE, and a
        # caller holding --allow-section-loss would then blanket-supersede a live chapter
        # and insert nothing in its place. Refusing to act on an empty queue costs nothing;
        # the caller counts zero inserted, which is the truth.
        return 0, 0

    cur.execute(
        """
        SELECT bool_or(is_full_replace) FROM dcp_review_queue
        WHERE council = %s AND chapter_key = %s AND status = 'approved'
          AND created_at = %s
        """,
        (council, chapter_key, batch_ts),
    )
    row = cur.fetchone()
    # NULL (legacy rows) -> full replace: the pre-054 baseline is all full re-extractions.
    full_replace = True if (row is None or row[0] is None) else bool(row[0])

    superseded = 0
    if full_replace:
        # A full replace drops every live rule the approved queue does not name. Queues
        # built before 2026-09-13 never held unchanged or renumbered rules: measured then,
        # 5 open chapters would have lost 92 live rules (waverley 84). Refuse instead; the
        # caller rolls back and keeps the approval. Allowed only for a chapter a person has
        # checked, via the same --allow-section-loss override as the section-loss guard.
        # Counted per ref, not merely matched. A ref does not identify a provision -- the
        # live set holds five refs carrying two current provisions each (woollahra
        # C1_4_10, D5_4, D5_6, D1_10, D6_6_7) -- so an EXISTS test calls a ref covered
        # when the run replaces only one of the two, and the blanket supersede below then
        # drops the other with nothing reporting it. Comparing counts refuses instead.
        # IS NOT DISTINCT FROM so a NULL ref on both sides matches; ref_number is nullable.
        cur.execute(
            """
            SELECT ref_number, live_n, queued_n FROM (
                SELECT p.ref_number AS ref_number, COUNT(*) AS live_n,
                       (SELECT COUNT(*) FROM dcp_review_queue q
                        WHERE q.council = %s AND q.chapter_key = %s
                          AND q.status = 'approved' AND q.created_at = %s
                          AND q.ref_number IS NOT DISTINCT FROM p.ref_number) AS queued_n
                FROM regulatory_provisions p
                WHERE p.source_council = %s AND p.source_chapter_key = %s
                  AND p.is_current = TRUE
                GROUP BY p.ref_number
            ) t WHERE live_n > queued_n
            """,
            (council, chapter_key, batch_ts, council, chapter_key),
        )
        short = cur.fetchall()
        unqueued = [r[0] for r in short]
        if unqueued and not allow_unqueued:
            lost = sum(live_n - queued_n for _ref, live_n, queued_n in short)
            eg = ", ".join(f"{ref} ({live_n} live, {queued_n} queued)"
                           for ref, live_n, queued_n in short[:3])
            raise RuntimeError(
                f"{lost} live rule(s) of {council}/{chapter_key} across {len(unqueued)} "
                f"ref(s) are not replaced by the approved run, and a full replace would "
                f"drop them (e.g. {eg}). Re-queue the chapter from current code, or pass "
                f"--allow-section-loss {council}/{chapter_key} after checking the loss "
                f"against the source document.")
        cur.execute(
            """
            UPDATE regulatory_provisions
            SET is_current = FALSE
            WHERE source_council = %s AND source_chapter_key = %s AND is_current = TRUE
            """,
            (council, chapter_key),
        )
        superseded = cur.rowcount

    # The latest extraction RUN of this chapter, whole -- not every approved row ever left
    # here.
    #
    # Approved rows accumulate across repeated runs over an UNCHANGED PDF. Measured
    # 2026-09-19: hornsby/part-1-general carried three approved batches — 24 from
    # 2026-07-28, 26 from 2026-09-02, 27 from 2026-09-18 — and blacktown/part-a-car-parking
    # and both georges_river chapters the same. Every batch was inserted, so the second
    # copy of a provision hit uq_provisions_current_identity (document_id, ref_number,
    # section_header, md5(provision_text)) and the whole chapter rolled back. Ten chapters
    # failed that way in one run.
    #
    # The existing currency guard cannot catch this: it skips a chapter whose approved rows
    # span MORE THAN ONE source hash, and these all share one, because the council's
    # document genuinely has not changed since July. It separates document VERSIONS; these
    # are repeated READS of one version.
    #
    # Taking the whole run, rather than the newest row per ref_number, is deliberate. Two
    # live provisions may legitimately share a ref_number — the unique index keys on
    # section_header and the text as well — and five such pairs exist today, so a per-ref
    # dedupe would drop one of each without reporting it. Within a run ref_number IS
    # unique (zero exceptions, measured across every approved batch), so the run collapses
    # repeated reads exactly; and if a future run ever does hold a colliding pair, the
    # index rejects it and the chapter rolls back loudly rather than losing a rule quietly.
    # A ref that an older run produced and the newest one did not is correctly left behind:
    # both such rows today are garbage the newest read stopped emitting (a two-column
    # interleave, and a zone name mistaken for a clause number).
    cur.execute(
        """
        SELECT document_id, ref_number, new_text, new_page, change_type
        FROM dcp_review_queue
        WHERE council = %s AND chapter_key = %s AND status = 'approved'
          AND created_at = %s
        ORDER BY ref_number
        """,
        (council, chapter_key, batch_ts),
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
                document_id, ref_number,
                _section_header_from_text(new_text, ref_number, document_id),
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
    parser.add_argument(
        "--allow-section-loss", action="append", default=[], metavar="COUNCIL/CHAPTER",
        help=("Let ONE named chapter through the section-loss guard. Repeatable. Only for "
              "a loss a person has checked against the council's source document."),
    )
    parser.add_argument(
        "--allow-garble", action="append", default=[], metavar="COUNCIL/CHAPTER",
        help=("Let ONE named chapter through the legibility guard. Repeatable. Separate "
              "from --allow-section-loss on purpose: an override should permit exactly "
              "what it names, and allowing a chapter to shed sections is not a decision "
              "to publish text a two-column read has scrambled."),
    )
    parser.add_argument(
        "--allow-fidelity", action="append", default=[], metavar="COUNCIL/CHAPTER",
        help=("Let ONE named chapter through the fidelity guard. Repeatable. Separate "
              "from the other two again: deciding that a chapter may shed sections, or "
              "that its text is legible, is not deciding that rows the source-page "
              "check rejected may be published."),
    )
    args = parser.parse_args()
    dry_run = not args.commit
    allowed_loss = frozenset(args.allow_section_loss)
    allowed_garble = frozenset(args.allow_garble)
    allowed_fidelity = frozenset(args.allow_fidelity)

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
    # Councils that actually had provisions inserted this run. The precinct
    # re-derivation at the bottom is scoped to exactly these -- never bulk. See the
    # comment on that block for why the scoping is load-bearing, not tidiness.
    committed_councils: set[str] = set()

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

        # Which extraction RUN this chapter would commit. Resolved ONCE, above the
        # dry-run split, because both branches need it and asking twice would be a
        # second query for an answer already in hand.
        batch_ts, _ = latest_approved_batch(cur, council, chapter_key)

        if dry_run:
            # Count the rows the real commit would insert -- the latest run only. Counting
            # every approved row reported three re-reads of one chapter as three times the
            # provisions, which is how the duplicate-key failure looked like success here.
            # prior-art-checked: reuse not viable because this is the existing dry-run
            # branch of this same worker, narrowed by the latest_approved_batch helper
            # added directly above it; the flagged matches are the frontend review API and
            # the provisions read paths, which do not decide what a commit inserts.
            cur.execute(
                "SELECT COUNT(*) FROM dcp_review_queue WHERE council=%s AND chapter_key=%s "
                "AND status='approved' AND created_at=%s "
                "AND change_type <> 'removed' AND new_text IS NOT NULL",
                (council, chapter_key, batch_ts),
            )
            n = cur.fetchone()[0]
            print(f"  [would commit] {council}/{chapter_key} -- {n} reviewed provisions")
            committed += 1
            continue

        try:
            # prior-art-checked: reuse not viable because the flagged matches are the
            # separate SEPP full-text import scripts; this is the DCP review-queue commit
            # path, writing dcp_review_queue-approved rows into regulatory_provisions.
            # The live chapter is measured BEFORE the swap and judged AFTER it, in the
            # same uncommitted transaction. A version missing most of the chapter's
            # sections raises here, lands in the except below, and is rolled back --
            # the approval is kept, so it is refused again every day until a person
            # decides. 2026-09-13: this swap took marrickville low-density 215 -> 26.
            before = section_snapshot(cur, council, chapter_key)
            # Before the writes, because this one reads the QUEUE: dcp_fidelity_gate has
            # already graded these rows against the council's own PDF and, until now,
            # nothing on this path looked at the verdict. Raising here rolls the
            # transaction back and keeps the approval, like the two guards below.
            #
            # batch_ts is resolved above the dry-run split, not inside it. Read from
            # inside that branch it would be either undefined (first chapter) or left
            # over from a PREVIOUS chapter, which would scope this guard to another
            # chapter's run and grade nothing while appearing to run.
            enforce_fidelity(cur, council, chapter_key, batch_ts, allowed_fidelity)
            superseded, inserted = commit_reviewed_from_queue(
                cur, council, chapter_key,
                allow_unqueued=f"{council}/{chapter_key}" in allowed_loss)
            enforce_section_loss(cur, council, chapter_key, before, allowed_loss)
            # Sections and rule counts can both survive a version that is unreadable.
            # Judged on the same before/after snapshot, inside the same uncommitted
            # transaction, so a refusal rolls the chapter back and keeps the approval.
            enforce_legibility(cur, council, chapter_key, before, allowed_garble)
            # Resolve the worklist: the reviewed provisions are now live. The status
            # enum has no 'committed', so the resolved rows are deleted (the permanent
            # record is regulatory_provisions, extraction_method='ai-reviewed').
            cur.execute(
                "DELETE FROM dcp_review_queue WHERE council=%s AND chapter_key=%s AND status='approved'",
                (council, chapter_key),
            )
            # Record WHICH version of the PDF the now-live rules came from, as the direct
            # extraction path already does (dcp_extract_changed.py, "Mark chapter extracted").
            # This line used to clear the flag and record nothing, so the registry kept the
            # pre-change fingerprint: on 2026-09-14, 110 served rules written here after their
            # PDF changed still read as stale in DQ-70, indistinguishable from stale ones.
            # approved_hash is the source_content_hash every approved row was reviewed against,
            # and the currency guard above has already required it to equal the registry's
            # content_hash. It holds for a targeted commit too: its queue carries every
            # difference the direct path applies (changed, added, removed, and renumbered
            # rules under both numbers -- enqueue_review_changes), so the rules it leaves
            # untouched are the ones whose text matched the new PDF. A legacy approval with no
            # recorded hash cannot say which version it reflects, so it clears the flag and
            # leaves the recorded fingerprint as it was.
            cur.execute(
                "UPDATE dcp_chapter_registry SET needs_extraction=FALSE, "
                "provisions_extracted_from_hash = COALESCE(%s, provisions_extracted_from_hash) "
                "WHERE council=%s AND chapter_key=%s",
                (approved_hash, council, chapter_key),
            )
            conn.commit()
            print(f"  [committed] {council}/{chapter_key} -- {inserted} reviewed provisions "
                  f"live ({superseded} superseded)")
            committed += 1
            committed_councils.add(council)
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
        print("Enriching newly committed provisions...")
        try:
            # The phase LIST and its order live in enrichment.pipeline, not here.
            # They used to be three lines copied into this file and into
            # dcp_extract_changed.py, and three further phases that exist and work
            # were wired into neither copy -- 3,216 served rows with no
            # v2_provision_type, 3,216 with no v2_site_condition_required, 1,142
            # with no v2_dev_type_source (measured 2026-09-11).
            from enrichment.pipeline import phase_failures, run_standard_enrichment

            results = run_standard_enrichment(batch_size=500)
            # phase_failures, not a local comprehension: a phase can fail by
            # returning {'errors': 12} without raising, and "what counts as
            # failed" living in two places is how the phase list itself came to
            # be wrong in two files at once.
            broken = phase_failures(results)
            if broken:
                # Partial enrichment is reported, never rounded up to "complete".
                # run_standard_enrichment isolates each phase so the rest still
                # ran; saying so is what stops a half-tagged council looking done.
                print(f"  [warn] enrichment finished with {len(broken)} failed phase(s): "
                      f"{', '.join(broken)}. Provisions ARE committed; the remaining "
                      f"phases did run. Re-run `python enrichment/pipeline.py --phase status`.")
            else:
                print("  enrichment complete.")
        except Exception as exc:  # noqa: BLE001 — never fail a committed provision on enrichment
            print(f"  [warn] enrichment failed: {exc}. Provisions ARE committed but untagged; "
                  f"re-run enrichment (they will not show correctly in the UI until you do).")

    # Precinct keys are the FOURTH field inserted UNSET, and the block above was written
    # for exactly this class of field -- v2_precinct_id was simply left off its list.
    # Measured 2026-09-10: a commit run nulled the keys for four councils at once and the
    # only thing that put them back was a human remembering to run the derivation by hand.
    # Ashfield fell to 118 keyed rows of 2,041 and Marrickville to 37 of 2,403, which is
    # what a precinct lookup returning nothing looks like from the outside.
    # derive_precinct_keys' own docstring names the cause: keys "were applied to rows BY
    # HAND, so every re-extraction nulled them and the manual work recurred."
    #
    # THREE THINGS HERE ARE LOAD-BEARING, not style:
    #   1. It runs AFTER the enrichment phases. A derived key also sets
    #      v2_dcp_layer='precinct'; run_layer_tagging would overwrite that if it ran last.
    #   2. It is SCOPED PER COUNCIL. run() deliberately refuses validate:False rules on a
    #      bulk apply and honours them only when a council is named -- so the bulk path
    #      would silently leave Ashfield's 641 chapter-D rows unkeyed. Committing a
    #      council IS the deliberate per-council act that guard asks for.
    #   3. It is wrapped. A derivation error must not fail provisions that are already
    #      committed -- they can be re-derived -- so it degrades to a loud warning.
    # A council with no rule derives nothing and returns 0; it is not an error.
    if committed_councils and not dry_run:
        print(f"Re-deriving precinct keys for {len(committed_councils)} committed council(s)...")
        # The IMPORT is inside the guard too, and catches Exception rather than
        # ImportError. derive_precinct_keys reads data/cos_precinct_page_ranges.json at
        # MODULE level, so a missing data file raises FileNotFoundError -- which an
        # `except ImportError` would not catch, crashing a run whose provisions are
        # already live. Dockerfile.monitors COPYs both the module and that json; this
        # guard is what stops a future packaging slip taking the commit down with it.
        derive_precinct_keys = None
        try:
            try:
                from scripts.derive_precinct_keys import run as derive_precinct_keys
            except ImportError:  # invoked as `python scripts/dcp_commit_approved.py`
                from derive_precinct_keys import run as derive_precinct_keys
        except Exception as exc:  # noqa: BLE001 — module-level file reads raise anything
            print(f"  [warn] could not load the precinct derivation: {exc}. Provisions ARE "
                  f"committed but unkeyed; check Dockerfile.monitors COPYs "
                  f"scripts/derive_precinct_keys.py AND data/cos_precinct_page_ranges.json.")
        for council in sorted(committed_councils if derive_precinct_keys else ()):
            try:
                rc = derive_precinct_keys(council=council, apply=True, validate=False)
            except Exception as exc:  # noqa: BLE001 — never fail a committed provision
                print(f"  [warn] precinct re-derivation failed for {council}: {exc}. "
                      f"Provisions ARE committed but unkeyed; run "
                      f"`python scripts/derive_precinct_keys.py --council {council} --apply`. "
                      f"Until then a precinct lookup for {council} serves council-wide only.")
                continue
            # run() signals failure by RETURN VALUE as well as by raising, and a
            # non-zero return would otherwise slide past the except and let the job
            # print its normal success summary over an unkeyed council. Raised by
            # cross-review on the pre-push run.
            #
            # Verified rather than assumed: today run() returns 1 on exactly one path
            # (`if validate and validation_failures`), which this call cannot reach
            # because it passes validate=False. So this branch is forward-looking --
            # it costs nothing and stops the next non-zero path being silent.
            #
            # It is NOT the fix for the genuinely silent case, and saying so here so
            # nobody reads it as one: a page_range rule whose PDF has been re-paginated
            # FAILS CLOSED, writes no keys, and returns 0. That is correct behaviour
            # (better council-wide than confidently wrong-precinct) but it is invisible
            # from this side. Detecting it needs a coverage assertion over the corpus --
            # see scripts/audit_precinct_keying_coverage.py, which is itself unwired.
            if rc:
                print(f"  [warn] precinct re-derivation reported failure (exit {rc}) for "
                      f"{council}. Provisions ARE committed but may be unkeyed; run "
                      f"`python scripts/derive_precinct_keys.py --council {council} --apply` "
                      f"and read its output.")

    # Citation verdicts: a publish changes clause numbers, and the site shows a number
    # only where regulatory_provisions.citation_status says the page proves it
    # (migration 076). Re-check the councils just committed so a fixed number shows
    # and a new unproven one does not. A failure never undoes a committed provision.
    for council in sorted(committed_councils if not dry_run else ()):   # a dry run writes nothing
        import subprocess
        try:
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "dcp_citation_status.py"),
                                "--council", council, "--apply", "--workers", "2"],
                               cwd=str(ROOT), capture_output=True, text=True, timeout=1800)
            print(f"  citation verdicts for {council}: "
                  f"{(r.stdout.strip().splitlines() or ['no output'])[-1]}")
            if r.returncode:
                print(f"  [warn] citation re-check failed for {council} (exit {r.returncode}): "
                      f"{r.stderr.strip()[-300:]}. Run `python scripts/dcp_citation_status.py "
                      f"--council {council} --apply`; until then new numbers keep their old verdict.")
        except Exception as exc:  # noqa: BLE001 -- never fail a committed provision
            print(f"  [warn] citation re-check could not run for {council}: {exc}")
        # The same for the council's setback controls, which the reports print (migration 077).
        try:
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "dcp_setback_citation_status.py"),
                                "--council", council, "--apply"],
                               cwd=str(ROOT), capture_output=True, text=True, timeout=1800)
            print(f"  setback clause verdicts for {council}: "
                  f"{(r.stdout.strip().splitlines() or ['no output'])[-1]}")
            if r.returncode:
                print(f"  [warn] setback clause re-check failed for {council} (exit {r.returncode}): "
                      f"{r.stderr.strip()[-300:]}. Run `python scripts/dcp_setback_citation_status.py "
                      f"--council {council} --apply`; until then changed labels stay hidden.")
        except Exception as exc:  # noqa: BLE001 -- never fail a committed provision
            print(f"  [warn] setback clause re-check could not run for {council}: {exc}")
        # Page links: a publish writes each rule's page, and the reader's page was the first page
        # of its chunk for 45% of rules (2026-09-26). Check every committed rule's page against its
        # PDF and correct it (migration 079). A rule left unchecked fails dcp_page_repair --check.
        try:
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "dcp_page_repair.py"),
                                "--council", council, "--apply", "--workers", "2"],
                               cwd=str(ROOT), capture_output=True, text=True, timeout=1800)
            print(f"  page links for {council}: "
                  f"{(r.stdout.strip().splitlines() or ['no output'])[-1]}")
            if r.returncode:
                print(f"  [warn] page-link check failed for {council} (exit {r.returncode}): "
                      f"{r.stderr.strip()[-300:]}. Run `python scripts/dcp_page_repair.py "
                      f"--council {council} --apply`; until then its links stay unchecked.")
        except Exception as exc:  # noqa: BLE001 -- never fail a committed provision
            print(f"  [warn] page-link check could not run for {council}: {exc}")

    # Completeness: did anything a council carries go BACKWARDS?
    #
    # The three fixes of 2026-09-10 (#1079 repealed source, #1080 precinct keys,
    # #1081 retired zone codes) were one defect in three fields, and the two that
    # were caught were the only two with a check watching them. Every block above
    # protects a field somebody already thought of. This one compares the council
    # against its own last recording, which is answerable for a field nobody has
    # thought of yet.
    #
    # RECORD ONLY WHEN SOMETHING WAS COMMITTED. This is the load-bearing part.
    # If the daily run recorded a new baseline every day, a field bleeding a few
    # percent per day would walk the baseline along with it and never trip the
    # threshold. Recording on commit only means the baseline is the last known
    # state a human approved, and the daily no-record run compares today against
    # THAT, however many days ago it was.
    #
    # Wrapped, like the two blocks above it: provisions are already live and a
    # measurement failing must not roll them back or fail the job.
    completeness_rc = 0
    if not dry_run:
        try:
            try:
                from scripts.check_council_completeness import run as completeness
            except ImportError:  # invoked as `python scripts/dcp_commit_approved.py`
                from check_council_completeness import run as completeness
            completeness_rc = rc = completeness(
                trigger_source="commit" if committed else "monitor",
                record=bool(committed),
            )
            if rc == 2:
                print("  [completeness] a field went backwards -- see the alert above.")
            elif rc:
                print(f"  [warn] completeness check could not run (exit {rc}). "
                      f"Provisions ARE committed; run "
                      f"`python scripts/check_council_completeness.py` and read its output.")
        except Exception as exc:  # noqa: BLE001 — never fail a committed provision
            completeness_rc = 1
            print(f"  [warn] completeness check failed: {exc}. Provisions ARE committed; "
                  f"nothing compared this run.")
            # ALERT ON THE CHECK'S OWN ABSENCE. On a day that did commit, the exit
            # code stays 2 (see below), so without this the fact that nothing was
            # verified would reach no one -- a monitoring job whose monitoring
            # silently stopped, which is the shape of every bug on this branch.
            try:
                from scripts.check_council_completeness import send_telegram
            except ImportError:
                try:
                    from check_council_completeness import send_telegram
                except ImportError:
                    send_telegram = None
            if send_telegram:
                send_telegram(
                    "DCP commit: the completeness check did NOT run\n\n"
                    f"{type(exc).__name__}: {exc}\n\n"
                    "Provisions are committed and unaffected, but nothing was compared "
                    "against the last recording. Run "
                    "`python scripts/check_council_completeness.py` and read its output."
                )

    print("-" * 60)
    verb = "would commit" if dry_run else "committed"
    print(f"  {verb}: {committed}   failed: {failed}   skipped: {skipped}")

    if failed:
        return 1
    # A check that could not RUN is not a clean day -- but only when there is
    # nothing else to report. The invariant from #1080 still holds and is tested:
    # a post-commit step failing must NOT turn a successful commit into a failure,
    # so on a day that committed, this stays 2 and the Telegram sent above is the
    # signal. On a day with nothing to commit, 0 would be indistinguishable from a
    # verified-clean run, which is the silence this whole branch exists to remove.
    if completeness_rc == 1 and not committed:
        return 1
    # 2 is "ran fine, found something" throughout this pipeline. A completeness
    # finding on a day with nothing to commit is still a finding, so it must not
    # exit 0.
    return 2 if (committed or completeness_rc == 2) else 0


if __name__ == "__main__":
    sys.exit(main())
