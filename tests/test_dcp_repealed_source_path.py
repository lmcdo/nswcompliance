"""A council can declare a repeal in the FILE PATH, where no page reader sees it.

REAL FINDING, measured 2026-09-10. Woollahra moved its superseded DCP chapters
into a `/repealed-dcps/` folder and left the registry pointing at them:

    .../development-control-plans/repealed-dcps/
        woollahra_dcp_2015_repealed_12_october_2020_chapter_c1_paddington_hca.pdf

19 of Woollahra's 27 active chapters point in there, 357 of its 739 served
provisions trace to those chapters, and that day's run queued 478 more rows
from them. The existing guard, `detect_repealed_stamp`, reads the first four
PAGES for a line beginning "repealed by" -- and passed all 19, because the
council never writes it on the page. The word only ever appears in the path.

WHAT THESE TESTS PROTECT, in the order the guard has to get right:

1. The word must be matched as a path TOKEN, not a substring. A council whose
   slug merely mentions repealed instruments ('notrepealedstuff') must not be
   rejected -- that is the confusable negative, and a guard without one is a
   guard that rejects the corpus.
2. BOTH columns are checked. The mirrored R2 key is a tidy path with no marker
   in it, so checking it alone catches nothing; the council URL alone misses a
   file already mirrored under a repealed prefix.
3. The reject happens BEFORE the download, and does not live inside the
   preflight block. `preflight_layout` returns {} on any error it hits, which
   makes that whole block a no-op exactly when the source file is unreadable --
   the case where a repealed-source check matters most.
4. It is a REJECT, not a flag: needs_extraction stays TRUE, so the only way to
   clear it is to re-point the registry at the in-force chapter. There is no
   path where a human approval makes repealed text live.

Pure-logic tests: no real DB, no real R2, no real PDF.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import dcp_extract_changed as dx  # noqa: E402


# The genuine article, copied from the registry rather than invented.
REAL_REPEALED_URL = (
    "https://www.woollahra.nsw.gov.au/__data/assets/pdf_file/0020/"
    "development-control-plans/repealed-dcps/"
    "woollahra_dcp_2015_repealed_12_october_2020_chapter_c1_paddington_hca.pdf"
)
# The same chapter published from the in-force folder.
CLEAN_URL = (
    "https://www.woollahra.nsw.gov.au/__data/assets/pdf_file/0020/"
    "development-control-plans/"
    "woollahra_dcp_2015_chapter_c1_paddington_hca.pdf"
)
CLEAN_R2_KEY = "dcp/woollahra/chapter-c1-paddington-hca.pdf"


def _chapter(**overrides) -> dict:
    base = {
        "council": "woollahra",
        "chapter_key": "chapter-c1-paddington-hca",
        "id": 1,
        "r2_current_path": CLEAN_R2_KEY,
        "r2_version_label": "v1",
        "dcp_name": "Woollahra DCP 2015",
        "council_url": CLEAN_URL,
    }
    base.update(overrides)
    return base


class _RecordingS3:
    """Records whether R2 was ever asked for the file."""

    def __init__(self):
        self.downloads = []

    def download_file(self, bucket, key, local_path):
        self.downloads.append(key)
        with open(local_path, "wb") as fh:
            fh.write(b"%PDF-1.4\n")


# ---------------------------------------------------------------------------
# 1. The detector itself, forced both ways
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url", [
    REAL_REPEALED_URL,
    "https://council.example/development-control-plans/repealed-dcps/ch.pdf",
    "https://council.example/plans/dcp_repealed_2020_chapter_c1.pdf",
    "https://council.example/plans/chapter-a1.repealed.pdf",
    "https://council.example/REPEALED/chapter.pdf",          # case
    "https://council.example/plans/dcps-repealed",           # no extension
])
def test_a_repealed_location_is_detected(url):
    """Every shape a council actually uses to say 'archive' in a path."""
    assert dx.detect_repealed_source(url, None), url


@pytest.mark.parametrize("url", [
    "https://council.example/plans/repealed%20dcps/chapter-a1.pdf",   # encoded space
    "https://council.example/plans/repealed dcps/chapter-a1.pdf",     # literal space
    "https://council.example/plans/dcp%5Frepealed%5F2020.pdf",        # encoded _
    "https://council.example/plans/repealed%2Ddcps/chapter.pdf",      # encoded -
])
def test_an_encoded_or_spaced_separator_is_still_a_repealed_location(url):
    """Sol cross-review, 2026-09-10. An explicit delimiter set kept missing cases.

    This is not hypothetical for this corpus: 197 of the 564 active registry
    rows already carry a '%' or a literal space in one of the two columns, so
    a pattern that only understands / _ - . would go quietly blind on a real
    council the day one of them publishes an archive folder with a space in it.
    The boundary is now 'not a letter or digit', and unquote runs first.
    """
    assert dx.detect_repealed_source(url, None), url


@pytest.mark.parametrize("url", [
    CLEAN_URL,
    "https://council.example/plans/notrepealedstuff/chapter-a1.pdf",
    "https://council.example/plans/unrepealed-dcps/chapter-a1.pdf",
    "https://council.example/plans/repealedish/chapter-a1.pdf",
    "https://council.example/plans/prerepealed/chapter-a1.pdf",
    "https://council.example/plans/NotRepealedStuff/chapter-a1.pdf",   # mixed case
    "https://council.example/plans/chapter-c1-paddington-hca.pdf",
])
def test_the_word_inside_a_longer_token_is_not_a_repealed_location(url):
    """THE CONFUSABLE NEGATIVE.

    A substring match would reject all of these. The guard has to survive a
    council that names a folder after the instruments it superseded, or the
    first false positive turns the guard off for everyone.
    """
    assert dx.detect_repealed_source(url, None) is None, url


def test_both_columns_are_checked_because_either_alone_misses_a_real_case():
    """A registry re-point fixes the URL while R2 keeps serving the old file.

    So checking the URL alone lets the stale mirror through, and checking the
    mirrored key alone catches nothing at all -- Woollahra's R2 keys are tidy
    slugs with no marker in them. This is bug #3 of the three the first pass
    of this guard shipped with.
    """
    assert dx.detect_repealed_source(REAL_REPEALED_URL, CLEAN_R2_KEY)
    assert dx.detect_repealed_source(CLEAN_URL, "dcp/woollahra/repealed/c1.pdf")
    assert dx.detect_repealed_source(CLEAN_URL, CLEAN_R2_KEY) is None


def test_the_message_names_the_column_and_quotes_the_evidence():
    """An operator has to know WHICH field to re-point, from the log line alone."""
    from_url = dx.detect_repealed_source(REAL_REPEALED_URL, CLEAN_R2_KEY)
    assert "source URL" in from_url
    assert "repealed" in from_url

    from_r2 = dx.detect_repealed_source(CLEAN_URL, "dcp/woollahra/repealed/c1.pdf")
    assert "mirrored file" in from_r2


@pytest.mark.parametrize("args", [(None, None), ("", ""), (None, ""), ("", None)])
def test_missing_values_are_not_a_repealed_source(args):
    """A NULL council_url is a registry gap, not an archive document.

    Rejecting on absent evidence would stall every chapter that has not been
    given a source URL yet.
    """
    assert dx.detect_repealed_source(*args) is None


# ---------------------------------------------------------------------------
# 1b. A narrow check must not read as a clean one
# ---------------------------------------------------------------------------

def test_a_missing_council_url_is_reported_rather_than_passed_silently():
    """Sol cross-review, 2026-09-10, accepted in part.

    Sol's finding was right: with no council_url the check reads only the
    mirrored key, and that is the column a council's archive marker never
    reaches -- so the chapter passes on evidence that was never there.

    Sol's prescribed fix was to reject. Measured against production before
    accepting it: 36 of 564 active rows have no council_url, across 17
    councils. Rejecting them would stall a corpus over a blank field, which is
    the exact 'guard rejects the corpus' failure the confusable negatives above
    exist to prevent. So it stays a pass -- but a LOUD one.
    """
    assert dx.repealed_check_coverage(None, CLEAN_R2_KEY)
    assert dx.repealed_check_coverage("", CLEAN_R2_KEY)
    assert dx.repealed_check_coverage("   ", CLEAN_R2_KEY)
    assert dx.repealed_check_coverage(None, None)
    # a populated URL is full coverage and must stay quiet, or the warning
    # becomes noise on 528 of 564 rows and stops being read at all
    assert dx.repealed_check_coverage(CLEAN_URL, CLEAN_R2_KEY) is None
    assert dx.repealed_check_coverage(REAL_REPEALED_URL, CLEAN_R2_KEY) is None


def test_the_narrow_warning_names_which_column_was_missing():
    """Two different gaps, two different messages -- 'nothing was read at all'
    is a worse state than 'only one location was read', and an operator
    triaging a log has to be able to tell them apart."""
    one_column = dx.repealed_check_coverage(None, CLEAN_R2_KEY)
    neither = dx.repealed_check_coverage(None, None)
    assert "council_url" in one_column
    assert one_column != neither
    assert "nothing" in neither.lower()


def test_a_missing_mirrored_path_is_reported_too_not_only_a_missing_url():
    """Sol cross-review round 2, 2026-09-10. Accepted.

    The first version returned 'full coverage' whenever council_url was
    populated, which describes a one-column check as a clean two-column one.
    39 active rows have no r2_current_path, 5 of them with a URL. Today the
    pending query filters them out with r2_current_path IS NOT NULL, so they
    never reach the caller -- but a function whose whole job is reporting
    coverage honestly must not depend on a caller's WHERE clause to stay true,
    and there is separate in-flight work on exactly that filter.
    """
    warning = dx.repealed_check_coverage(CLEAN_URL, None)
    assert warning, (
        "a chapter with no mirrored path reported full coverage -- the check "
        "read one location and the log said it read both"
    )
    assert "r2_current_path" in warning
    assert dx.repealed_check_coverage(CLEAN_URL, "   ") is not None
    # and the two one-column gaps are still distinguishable from each other
    assert warning != dx.repealed_check_coverage(None, CLEAN_R2_KEY)


def test_a_missing_council_url_does_not_stop_the_chapter_extracting(capsys):
    """The warning is a warning. It must print, and it must not reject."""
    s3 = _RecordingS3()
    real = dx.extract_pdf_isolated
    real_resolve = dx.resolve_document_id
    dx.extract_pdf_isolated = lambda *a, **kw: (None, "stopped here on purpose")
    dx.resolve_document_id = lambda *a, **kw: 1
    try:
        dx.extract_chapter(_chapter(council_url=None), s3, MagicMock(),
                           dry_run=True, review=True)
    finally:
        dx.extract_pdf_isolated = real
        dx.resolve_document_id = real_resolve

    assert s3.downloads == [CLEAN_R2_KEY], (
        "a chapter with no council_url was rejected -- 36 active rows across 17 "
        "councils would stall on a blank field"
    )
    assert "NARROW" in capsys.readouterr().out, (
        "the reduced check passed silently, which is how a coverage gap reads "
        "as a clean result"
    )


# ---------------------------------------------------------------------------
# 2. The reject, wired into extract_chapter
# ---------------------------------------------------------------------------

def test_a_repealed_chapter_is_rejected_without_touching_r2_or_the_database():
    """The evidence is in the registry row, so there is nothing to download.

    conn is None on purpose: if the guard ever moves back below the point
    where a cursor is opened, this raises AttributeError instead of passing.
    """
    s3 = _RecordingS3()

    ok, review_data = dx.extract_chapter(
        _chapter(council_url=REAL_REPEALED_URL), s3, None,
        dry_run=True, review=True)

    assert (ok, review_data) == (False, None)
    assert s3.downloads == [], (
        "a repealed chapter was downloaded before being rejected -- the guard "
        "is running after the fetch"
    )


def test_a_clean_chapter_is_not_rejected_and_does_reach_the_download():
    """THE OTHER DIRECTION.

    Without this, a guard that rejected every chapter would pass the test
    above and look correct.
    """
    s3 = _RecordingS3()
    monkey = {}

    def _fake_isolated(*args, **kwargs):
        monkey["reached"] = True
        return None, "stopped here on purpose"

    real = dx.extract_pdf_isolated
    real_resolve = dx.resolve_document_id
    dx.extract_pdf_isolated = _fake_isolated
    dx.resolve_document_id = lambda *a, **kw: 1
    try:
        ok, review_data = dx.extract_chapter(
            _chapter(), s3, MagicMock(), dry_run=True, review=True)
    finally:
        dx.extract_pdf_isolated = real
        dx.resolve_document_id = real_resolve

    assert s3.downloads == [CLEAN_R2_KEY], (
        "a clean chapter never reached R2 -- the guard is rejecting everything"
    )
    assert monkey.get("reached"), "a clean chapter never reached extraction"
    assert (ok, review_data) == (False, None)  # stopped at the fake, as arranged


def test_a_chapter_mirrored_under_a_repealed_prefix_is_rejected_too():
    """The URL can be re-pointed while R2 still holds the archive copy."""
    s3 = _RecordingS3()

    ok, _ = dx.extract_chapter(
        _chapter(council_url=CLEAN_URL,
                 r2_current_path="dcp/woollahra/repealed/chapter-c1.pdf"),
        s3, None, dry_run=True, review=True)

    assert ok is False
    assert s3.downloads == []


# ---------------------------------------------------------------------------
# 3. The guard must not be reachable only through the preflight block
# ---------------------------------------------------------------------------

def test_the_guard_survives_a_preflight_that_returned_nothing():
    """preflight_layout swallows every error and returns {}.

    That makes `if preflight:` false and skips the whole block -- which is
    where an earlier draft of this guard lived. A repealed chapter whose PDF
    also fails to parse is the single most likely combination there is, and
    that draft waved it straight through.

    The same draft also wrote a key INTO that empty dict, which flipped it
    truthy and then raised KeyError on the first line inside the block,
    killing the entire nightly batch rather than one chapter. Both failures
    are excluded by the guard sitting above the download.
    """
    s3 = _RecordingS3()
    real = dx.extract_pdf_isolated
    real_resolve = dx.resolve_document_id
    dx.extract_pdf_isolated = lambda *a, **kw: (
        {"preflight": {}, "sections": [], "page_count": 0, "ranged": False}, None)
    dx.resolve_document_id = lambda *a, **kw: 1
    try:
        # repealed + unparseable: must still reject, and must not download
        ok, _ = dx.extract_chapter(
            _chapter(council_url=REAL_REPEALED_URL), s3, None,
            dry_run=True, review=True)
        assert ok is False
        assert s3.downloads == []

        # clean + unparseable: must be a contained per-chapter outcome, never
        # an exception that takes the batch loop down with it
        ok, _ = dx.extract_chapter(
            _chapter(), s3, MagicMock(), dry_run=True, review=True)
        assert ok is False
    finally:
        dx.extract_pdf_isolated = real
        dx.resolve_document_id = real_resolve


def test_the_extractor_actually_selects_the_column_the_guard_reads():
    """Bug #2 of the first pass: the guard read a column the query never fetched.

    `council_url` is the only place the evidence lives, so if it drops out of
    the SELECT the guard silently stops finding anything -- every chapter
    passes and nothing looks wrong.
    """
    query, _ = dx._pending_chapters_sql(None)
    assert "council_url" in query

    # and the row really arrives under that key
    cur = MagicMock()
    cur.description = [("id",), ("council",), ("chapter_key",), ("chapter_label",),
                       ("r2_current_path",), ("r2_version_label",), ("dcp_name",),
                       ("content_hash",), ("council_url",)]
    cur.fetchall.return_value = [(1, "woollahra", "chapter-c1", "C1", CLEAN_R2_KEY,
                                  "v1", "DCP", "hash", REAL_REPEALED_URL)]
    rows = dx.fetch_pending_chapters(cur, None)
    assert rows[0]["council_url"] == REAL_REPEALED_URL


def test_rejection_leaves_needs_extraction_alone_so_the_fix_must_be_a_re_point():
    """No approval path may ever make repealed text live.

    The reject returns before any DB write, so the chapter keeps surfacing in
    the pending query every run until someone re-points council_url. Asserted
    against the source because the property is an ABSENCE of a write, and an
    absence is what silently comes back in a later refactor.
    """
    src = (Path(__file__).resolve().parent.parent
           / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")
    guard = src.split("repealed_source = detect_repealed_source", 1)[1]
    guard = guard.split("with tempfile.TemporaryDirectory", 1)[0]
    assert "return False, None" in guard
    assert "needs_extraction" not in guard, (
        "the reject touches needs_extraction -- it must leave the flag TRUE"
    )
    assert "UPDATE" not in guard.upper()
