"""Committing an unchanged chapter twice must not insert the provision twice.

Approved rows accumulate. A chapter re-read on 28 July, 2 September and 18 September — with
the council's PDF unchanged throughout — carries three approved batches, all with the SAME
source_content_hash. The commit inserted every one, so the second copy of a provision hit

    uq_provisions_current_identity
    ON (COALESCE(document_id,''), COALESCE(ref_number,''),
        COALESCE(section_header,''), md5(provision_text)) WHERE is_current

and the whole chapter rolled back. Ten chapters failed that way in the 2026-09-18 run:
blacktown, five canterbury_bankstown, both georges_river, hornsby.

The currency guard already in the script cannot see it. That guard skips a chapter whose
approved rows span more than one source hash — it separates different VERSIONS of a
document, and these are repeated READS of one.

The unit taken is the extraction RUN, not the ref_number, and that distinction is the
substance of these tests. A ref_number does not identify a provision: the unique index
keys on section_header and the text as well, so two live provisions may share a ref, and
five such pairs exist (woollahra C1_4_10 on pages 22 and 94, D5_4 on 8 and 20, D5_6 on 60
and 107, D1_10 on 6 and 55, D6_6_7 on 4 and 64). Deduplicating by ref would drop one of
each silently. Within a run ref_number IS unique — measured across every approved batch,
zero exceptions — so the run collapses repeated reads exactly, and a future run holding a
genuine colliding pair is rejected by the index rather than quietly halved.

Source-shape tests: no database, no clock. They read the queries the script actually issues.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "scripts" / "dcp_commit_approved.py").read_text(encoding="utf-8")


def _insert_fetch() -> str:
    """The SELECT whose rows are looped over and inserted as provisions.

    Anchored on its select list, not on 'FROM dcp_review_queue' — several queries in this
    file read that table, and matching the wrong one would test the wrong thing.
    """
    m = re.search(r"SELECT document_id, ref_number, new_text, new_page, change_type\s*\n"
                  r"\s*FROM dcp_review_queue[^\"]*?ORDER BY [^\"]*", SRC, re.S)
    assert m, "the insert-site fetch could not be located in dcp_commit_approved.py"
    return " ".join(m.group(0).split())


def _batch_fn() -> str:
    """The helper that resolves which run to commit."""
    m = re.search(r"def latest_approved_batch\(.*?\n(?=\n\ndef |\n\nclass )", SRC, re.S)
    assert m, "latest_approved_batch is gone — the run boundary is no longer computed"
    return m.group(0)


class TestOnlyTheLatestRunIsCommitted:
    def test_the_insert_fetch_is_scoped_to_one_run(self):
        """Without this the commit inserts every approved row ever queued, which is the
        duplicate-key failure that took ten chapters down in one night."""
        fetch = _insert_fetch()
        assert "created_at = %s" in fetch, fetch

    def test_it_does_NOT_deduplicate_by_ref_number(self):
        """A per-ref dedupe passes the same duplicate-key symptom but loses data: two live
        provisions may legitimately share a ref_number, and five pairs do today. The run is
        the only boundary that separates a re-read from a second provision."""
        fetch = _insert_fetch()
        assert "DISTINCT ON" not in fetch, (
            "the insert fetch deduplicates by ref_number. That drops one of every "
            "legitimately repeated ref (woollahra C1_4_10, D5_4, D5_6, D1_10, D6_6_7) "
            "without reporting it. Scope to created_at instead.")

    def test_it_takes_the_NEWEST_run(self):
        """DESC, not ASC: the newest run is the one reviewed against the current document.
        Ascending would commit July's reading and discard September's."""
        fn = _batch_fn()
        assert re.search(r"ORDER BY created_at DESC", fn), fn
        assert re.search(r"return batches\[0\]", fn), \
            "the helper no longer returns the first (newest) batch"

    def test_the_run_is_a_transaction_not_a_guess(self):
        """No time window, no date truncation. created_at DEFAULTs to now() — transaction
        time — so a run is one exact timestamp. A tolerance window here would silently
        merge two runs back together and restore the duplicate insert."""
        fetch = _insert_fetch()
        fn = _batch_fn()
        for fuzzy in ("interval", "date_trunc", "::date", ">="):
            assert fuzzy not in fetch, f"the insert fetch infers the run with {fuzzy!r}"
            assert fuzzy not in fn, f"the run boundary is inferred with {fuzzy!r}"

    def test_a_fragmented_queue_is_REFUSED_not_committed(self):
        """If created_at ever stops being transaction time, every run becomes one row and
        the newest run is one provision. Committing that would report success while
        publishing a fragment, so the helper raises instead."""
        fn = _batch_fn()
        assert "raise RuntimeError" in fn, \
            "the fragmented-queue refusal is gone; a per-row timestamp would commit one row"
        # The distribution, not the mean: an average is dragged over any threshold by one
        # large historical batch, so a single stray row stamped today would pass as a run.
        assert re.search(r"singles\s*=\s*sum\(1 for _ts, n in batches if n < 2\)", fn), fn
        assert re.search(r"len\(batches\)\s*>\s*1\s+and\s+singles\s*\*\s*2\s*>\s*len\(batches\)", fn), fn
        assert "total / len(batches) <" not in fn, \
            "the refusal is back on the mean, which one large old batch masks"

    def test_the_fetch_still_selects_what_the_insert_loop_unpacks(self):
        """Guards the guard: the loop unpacks five columns positionally."""
        fetch = _insert_fetch()
        for col in ("document_id", "ref_number", "new_text", "new_page", "change_type"):
            assert col in fetch, col
        loop = re.search(r"for document_id, ref_number, new_text, new_page, change_type in rows",
                         SRC)
        assert loop, "the insert loop no longer unpacks five columns — re-check the fetch"


class TestTheGuardsJudgeTheRowsTheInsertWrites:
    """A guard reading a wider set than the insert is worse than no guard: it reports the
    chapter safe on evidence the commit will not act on."""

    def test_the_section_loss_guard_is_scoped_to_the_same_run(self):
        """It asks which live rules the approved run does not replace. Asking that of every
        approved row ever queued would clear a live rule that exists only in an older run —
        and then not insert it."""
        m = re.search(r"SELECT ref_number, live_n, queued_n FROM.*?\"\"\"", SRC, re.S)
        assert m, "the counting section-loss query could not be located"
        assert "q.created_at = %s" in m.group(0), m.group(0)

    def test_the_section_loss_guard_compares_counts_not_mere_existence(self):
        """A ref does not identify a provision: five refs carry two current provisions
        each. An EXISTS test calls such a ref covered when the run replaces one of the two,
        and the blanket supersede then drops the other silently."""
        m = re.search(r"SELECT ref_number, live_n, queued_n FROM.*?\"\"\"", SRC, re.S)
        assert m, "the counting section-loss query could not be located"
        q = m.group(0)
        assert "live_n > queued_n" in q, q
        assert "NOT EXISTS" not in q, "the guard is back to mere existence"
        assert "IS NOT DISTINCT FROM" in q, \
            "ref_number is nullable; = would never match a NULL ref on either side"

    def test_the_full_replace_mode_is_read_from_the_same_run(self):
        """is_full_replace decides whether the chapter is blanket-superseded. Reading it
        from an older run would apply July's mode to September's rows."""
        m = re.search(r"SELECT bool_or\(is_full_replace\).*?\"\"\"", SRC, re.S)
        assert m, "the is_full_replace fetch could not be located"
        assert "created_at = %s" in m.group(0), m.group(0)

    def test_the_dry_run_counts_the_rows_the_commit_would_insert(self):
        """The dry run is the only thing a person sees before approving a commit. Counting
        every approved row reported three re-reads as three times the provisions."""
        m = re.search(r"if dry_run:.*?n = cur\.fetchone\(\)\[0\]", SRC, re.S)
        assert m, "the dry-run count could not be located"
        assert "created_at=%s" in m.group(0) or "created_at = %s" in m.group(0), m.group(0)


class TestTheOtherGuardsSurvive:
    def test_the_multi_hash_guard_is_still_there(self):
        """This fix is not a replacement for the currency guard. That one stops a STALE
        approval (the PDF changed since review); this one stops a REPEATED one (the PDF did
        not). Removing either brings back a different failure."""
        assert "hash_variants" in SRC
        assert re.search(r"hash_variants\W+.{0,40}>\s*1", SRC, re.S), \
            "the >1 hash-variants skip is gone"

    def test_the_post_swap_section_snapshot_is_still_enforced(self):
        """The independent net: sections are counted before the swap and judged after it,
        inside the same uncommitted transaction. It is what catches a run that is short."""
        assert "enforce_section_loss" in SRC
        assert "section_snapshot" in SRC
