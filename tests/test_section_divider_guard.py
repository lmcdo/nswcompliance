"""Tests for classify_toc_or_divider_page() in dcp_extract_changed.py -- the
guard that keeps a chapter's full TOC page and a section's own "SECTION N"
mini-TOC divider page from starting a false new section.

Pure decision-logic tests (no PDF I/O), per this module's own convention:
full extraction is validated against real council PDFs out of band (see
scripts/dcp_extract_changed.py's docstring on _extract_sequential and the
sibling tests/test_dcp_toc_extraction.py). Every positive fixture below is
a VERBATIM excerpt from Canterbury-Bankstown chapter-7-5 and chapter-11-15's
real, already-downloaded source PDFs (2026-09-05 investigation), not
invented text -- this is the exact shape that produced the bug.

The function returns (suppress, discard):
  suppress -- this page must not start a new section (both the full-TOC and
    divider cases).
  discard  -- this page's text must be DROPPED, not appended to whichever
    section is currently open. Only True for the divider case. Sol cross-
    review (HIGH, confidence 0.98, 2026-09-05) caught the first version of
    this fix suppressing heading detection but still silently absorbing the
    divider text into the previously-open section -- corrupting two
    previously-CLEAN sections (chapter-7-5's 1.2 and 4.6) with unrelated
    sibling titles and page numbers. The full-TOC case keeps the existing,
    unchanged absorb behaviour (it lands harmlessly in 'preamble' in every
    observed case, which is already non-actionable).
"""
import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
           "R2_BUCKET_NAME", "R2_ENDPOINT_URL", "R2_PUBLIC_URL"):
    os.environ.setdefault(_k, "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
_STUBS = ("boto3", "botocore", "pdfplumber", "psycopg2", "dotenv", "enrichment", "enrichment.pipeline")
_saved = {k: sys.modules.get(k) for k in _STUBS}
for _k in _STUBS:
    sys.modules[_k] = MagicMock()
sys.modules["dotenv"].load_dotenv = MagicMock()
try:
    from dcp_extract_changed import DCPExtractor, classify_toc_or_divider_page  # noqa: E402
finally:
    for _k, _v in _saved.items():
        if _v is None:
            sys.modules.pop(_k, None)
        else:
            sys.modules[_k] = _v

SECTION_RE = DCPExtractor.SECTION_RE


class TestSectionDividerPagesAreSuppressedAndDiscarded:
    """Positive cases -- verbatim excerpts from the real, broken pages.
    Divider pages must both suppress (no new section) AND discard (text
    dropped, not appended elsewhere)."""

    def test_chapter_7_5_page_5_section_1_divider(self):
        # Page 5 of chapter-7-5-canterbury-local-centre.pdf, verbatim.
        text = (
            "\n\nSECTION 1\nINTRODUCTION\n1.1 Application of this DCP Chapter 6\n"
            "1.2 Vision for Canterbury Local 7\nCentre\n1.3 How to read this DCP "
            "Chapter 7\nCanterbury-Bankstown Development Control Plan 2023 "
            "Chapter 7.5 Canterbury Local Centre 5"
        )
        assert classify_toc_or_divider_page(text, SECTION_RE) == (True, True)

    def test_chapter_7_5_page_8_section_2_divider(self):
        # Page 8, verbatim. This page's text was the one Sol caught landing
        # inside section 1.2 (previously clean) before the discard fix.
        text = (
            "SECTION 2\nUNDERSTANDING\nPLACE\n2.1 Structure Plan for the Local 9\n"
            "Centre\n2.2 Character Areas and key street 11\nand lanes\n"
            "2.3 Connecting to Country 24\nCanterbury-Bankstown Development "
            "Control Plan 2023 Chapter 7.5 Canterbury Local Centre 8"
        )
        assert classify_toc_or_divider_page(text, SECTION_RE) == (True, True)

    def test_chapter_7_5_page_82_section_5_divider(self):
        # Page 82, verbatim. This page's text was the one Sol caught landing
        # inside section 4.6 (previously clean) before the discard fix.
        text = (
            "\n\nSECTION 5\nGENERAL\nPROVISIONS\n5.1 Dwelling mix and flexible "
            "housing 83\n5.2 Parking 84\n5.3 Underground floor space 87\n"
            "5.4 Sustainability 88\nCanterbury-Bankstown Development Control"
        )
        assert classify_toc_or_divider_page(text, SECTION_RE) == (True, True)

    def test_chapter_11_15_marco_avenue_section_2_divider(self):
        # Page 5 of chapter-11-15-marco-avenue.pdf, verbatim (re-fetched and
        # confirmed directly -- an earlier draft of this test used a
        # truncated snippet from a diff report's preview and got the hit
        # count wrong; this is the real, full page text). This page was
        # 100% divider text with NO real content following on the same
        # page -- confirmed live by re-running the fixed extractor and
        # diffing against the already-committed baseline: the section
        # disappears entirely rather than surviving as an empty shell,
        # which is correct (there was never any real content there).
        text = (
            "SECTION 2\nBUILT FORM AND\nDESIGN\n2.1 Objectives 8\n"
            "2.2 Principles 9\n2.3 Controls 10\nCanterbury-Bankstown "
            "Development Control Plan 2023 Chapter 11.14 - 75A, 75B & "
            "7C Marco Avenue, Revesby"
        )
        assert classify_toc_or_divider_page(text, SECTION_RE) == (True, True)


class TestConfusableNegatives:
    """A detector is only proven by what it correctly does NOT flag."""

    def test_real_content_page_is_not_suppressed(self):
        # Page 7 of chapter-7-5 -- real body prose, one section code, no
        # divider marker. Must NOT be absorbed into the previous section.
        text = (
            "1.2 Vision for Canterbury Local\nCentre\nThe Local Centre will "
            "celebrate its\nheritage, connection to the Cooks River,\nand "
            "green leafy character to create\na lively and distinctive "
            "destination."
        )
        assert classify_toc_or_divider_page(text, SECTION_RE) == (False, False)

    def test_garbled_map_page_with_one_hit_is_not_suppressed(self):
        # Page 6 of chapter-7-5 -- the REAL "1.1 Application of this
        # Chapter" heading, followed by a garbled map (a SEPARATE, deferred
        # defect this fix does not and should not touch). Only 1 section-
        # code match and no "SECTION N" line, so it correctly stays a real
        # section rather than being swallowed by this guard.
        text = (
            "1.1 Application of this Chapter\nCanterbury\nT\nD C P\no\nh\nl\nb\n"
            "C a a\ni\nn\nj\ns\nP n\ne\nt\nc\nC\n2 e 2\nt\n0 0 r\nh\ni\nb\nv"
        )
        assert classify_toc_or_divider_page(text, SECTION_RE) == (False, False)

    def test_section_mentioned_in_prose_is_not_a_divider(self):
        # "Section" appearing mid-sentence, lower case, is not the literal
        # "SECTION N" standalone-line marker this guard looks for.
        text = (
            "1.4 Compliance\nDevelopment must comply with section 5 of this "
            "chapter and clause 4.2 of the LEP, as well as any relevant "
            "state environmental planning policy."
        )
        assert classify_toc_or_divider_page(text, SECTION_RE) == (False, False)

    def test_single_hit_with_divider_marker_does_not_suppress(self):
        # A "SECTION N" line with only ONE section-code match (not 2+) is
        # below the threshold -- e.g. a genuine section-1-only chapter's
        # divider page. Named explicitly so the >=2 boundary is pinned,
        # not just the >=5 and the 3-4-hit real cases.
        text = "SECTION 9\nGENERAL REQUIREMENTS\n9.1 Application 3"
        assert classify_toc_or_divider_page(text, SECTION_RE) == (False, False)

    def test_section_divider_marker_deep_in_a_long_real_page_does_not_suppress(self):
        # A long real content page that happens to mention "SECTION 5" (as
        # its own line, mid-page, e.g. quoting another chapter's heading)
        # more than 300 characters in must not trigger the guard -- this is
        # exactly why the divider check is restricted to text[:300].
        filler = "This is real DCP body prose discussing setbacks. " * 10
        text = filler + "\nSECTION 5\nCROSS-REFERENCED CHAPTER\n5.1 Foo 1\n5.2 Bar 2"
        assert len(filler) > 300
        assert classify_toc_or_divider_page(text, SECTION_RE) == (False, False)


class TestFullTocPageGuardUnchanged:
    """Regression coverage: the pre-existing >=5-hit guard still suppresses
    (no new section) but keeps its ORIGINAL absorb behaviour (discard=False)
    -- this fix only changes the divider case, not the full-TOC case, since
    the full-TOC page has never been observed landing anywhere but the
    already-non-actionable preamble section."""

    def test_full_toc_page_with_5_plus_hits_is_suppressed_but_not_discarded(self):
        text = (
            "CONTENTS\n1.1 Application of this DCP Chapter 6\n"
            "1.2 Vision for Canterbury Local Centre 7\n"
            "1.3 How to read this DCP Chapter 7\n"
            "2.1 Structure Plan for the Local Centre 9\n"
            "2.2 Character areas and key streets and lanes 11\n"
            "2.3 Connecting to Country 24\n"
        )
        assert classify_toc_or_divider_page(text, SECTION_RE) == (True, False)

    def test_four_line_start_hits_no_divider_marker_is_not_suppressed(self):
        # 4 real line-start section-code matches (below the >=5 full-TOC
        # threshold) but with no "SECTION N" divider marker to justify the
        # lower >=2 threshold. Pins that hit-count alone, without the
        # marker, is not enough below 5 -- a page with a few numbered
        # cross-referenced clauses is not a divider page.
        text = (
            "2.1 Zone provisions for adjoining land\n"
            "3.4 Cross reference to heritage clause\n"
            "4.2 Setbacks for corner lots\n"
            "5.6 Adjoining land use buffers\n"
        )
        assert len(SECTION_RE.findall(text)) == 4
        assert classify_toc_or_divider_page(text, SECTION_RE) == (False, False)
