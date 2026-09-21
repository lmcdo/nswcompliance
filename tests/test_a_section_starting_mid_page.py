"""A section that begins partway down a page was handed the WHOLE page.

Measured 2026-09-20 on northern_beaches/warringah-dcp-2011-full. Page 34 carries the
tail of the parking Part at the top and the heading of the stormwater Part 44% of the
way down. The splitter gave the whole page to the latter, so the stormwater control
opened with "End of trip facilities are not required for schools" -- a parking rule
served as a stormwater rule. Seven of that run's eleven failed rows were this defect, at 20%, 44%,
48%, 53%, 55%, 89% and 91% down their pages.

The text was not merely misfiled. The previous section was closed at `page_num - 1`, so
that same text was DROPPED from the section it belonged to as well as prepended to the
next one. One page of source produced two wrong rules.

The before/after, from the live queue:
    09-18  # C4 Stormwater Applies to Land | required for the additional floor area
                                             only. End of trip f...        <- C3's tail
    09-20  # C4 Stormwater Applies to Land | This control applies to land to which
                                             Warringah...                  <- correct

Fixing it exposed a second, older defect: the heading line was in the body as well as in
section_title, printing "C4 Stormwater Applies to Land C4 Stormwater Applies to Land
This control applies...". That had always been true; it was invisible only because the
body used to open with the previous section's tail, so the repeat sat too far down to
notice.

Councils in MULTI_HEADING_COUNCILS are pre-split by split_page_at_headings and reach
this code one heading per segment, where match.start() is 0 and the behaviour below is
unchanged. That list is deliberately one council wide and is not widened here.
"""
import os
import sys
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")

# This file exercises the regex/geometry reader, not the LLM one. AI_EXTRACTION
# became opt-out on 2026-09-21, so extract() now routes to the LLM unless a caller
# says otherwise -- these tests began trying to open a real PDF and phone a real
# provider (HTTP 429). Saying which reader is under test is the honest fix; turning
# the default off globally in conftest would hide the production behaviour from
# every other test in the suite.
os.environ["AI_EXTRACTION"] = "0"

for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
    os.environ.setdefault(_k, "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
_STUBS = ("boto3", "botocore", "pdfplumber", "psycopg2", "dotenv",
          "enrichment", "enrichment.pipeline")
_saved = {k: sys.modules.get(k) for k in _STUBS}
for _k in _STUBS:
    sys.modules[_k] = MagicMock()
try:
    import dcp_extract_changed as dx  # noqa: E402
finally:
    for _k, _v in _saved.items():
        if _v is None:
            sys.modules.pop(_k, None)
        else:
            sys.modules[_k] = _v


# Modelled on the real pages. C3 runs from p33, C4's heading sits partway down p34.
C3_TAIL = "End of trip facilities are not required for schools."
C4_BODY = "This control applies to land to which Warringah DCP applies."

PAGES = {
    33: "C3 Parking Facilities\nParking must be provided at the rates in Table 1.",
    34: f"{C3_TAIL}\nC4 Stormwater\n{C4_BODY}",
    35: "Stormwater must be disposed of to the street.",
}


def _extract(monkeypatch, pages=None, council="northern_beaches"):
    pages = PAGES if pages is None else pages
    n = max(pages) if pages else 0

    class _Pdf:
        def __init__(self):
            self.pages = [MagicMock() for _ in range(n)]

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(dx.pdfplumber, "open", lambda *a, **k: _Pdf())
    ex = dx.DCPExtractor(dx.Path("nb.pdf"), "doc", council=council)
    monkeypatch.setattr(ex, "_maybe_route_via_ocr", lambda: None)
    monkeypatch.setattr(ex, "_page_text", lambda page, num: pages.get(num, ""))
    monkeypatch.setattr(ex, "_page_tables", lambda page: [], raising=False)
    return {s["section_number"]: s for s in ex.extract()}


class TestTheTextAboveTheHeadingStaysWithThePreviousSection:
    def test_the_new_section_does_not_open_with_the_previous_ones_tail(self, monkeypatch):
        got = _extract(monkeypatch)
        c4 = next(v for k, v in got.items() if k.startswith("C4"))
        assert C3_TAIL not in c4["content"], (
            "C4 Stormwater is serving a C3 Parking rule -- the whole page was "  # noqa: zone-codes
            "handed to the section that starts partway down it")

    def test_that_tail_is_not_dropped_either(self, monkeypatch):
        """Misfiling and losing are different failures and the old code did both."""
        got = _extract(monkeypatch)
        c3 = next(v for k, v in got.items() if k.startswith("C3"))
        assert C3_TAIL in c3["content"], (
            "the text above the heading vanished -- it belongs to the section that was "
            "already open")

    def test_the_previous_section_is_credited_with_the_shared_page(self, monkeypatch):
        """It has content on page 34, so a citation must open the PDF there."""
        got = _extract(monkeypatch)
        c3 = next(v for k, v in got.items() if k.startswith("C3"))
        assert c3["page_end"] == 34 and 34 in c3["pages"]

    def test_the_new_section_still_starts_on_the_page_its_heading_is_on(self, monkeypatch):
        got = _extract(monkeypatch)
        c4 = next(v for k, v in got.items() if k.startswith("C4"))
        assert c4["page_start"] == 34


class TestTheHeadingIsNotPrintedTwice:
    def test_the_body_does_not_repeat_the_section_title(self, monkeypatch):
        got = _extract(monkeypatch)
        c4 = next(v for k, v in got.items() if k.startswith("C4"))
        assert "C4 Stormwater" not in c4["content"], (
            "the heading is carried by section_title; keeping it in the body too prints "
            "it twice")
        assert C4_BODY in c4["content"], "the body itself must survive"

    def test_the_title_is_still_captured(self, monkeypatch):
        got = _extract(monkeypatch)
        c4 = next(v for k, v in got.items() if k.startswith("C4"))
        assert "Stormwater" in (c4["section_title"] or ""), (
            "dropping the heading from the body must not drop it from the title")


class TestAPageThatOpensOnItsHeadingIsUnchanged:
    """The common case, and the one every other council relies on. A fix aimed at the
    mid-page case that moved this would be a far bigger regression than the bug."""

    def test_no_leading_text_means_the_previous_section_ends_on_the_previous_page(
            self, monkeypatch):
        pages = {
            10: "C1 Introduction\nThis plan applies to the whole area.",
            11: "C2 Setbacks\nThe front setback is 6m.",
        }
        got = _extract(monkeypatch, pages)
        c1 = next(v for k, v in got.items() if k.startswith("C1"))
        c2 = next(v for k, v in got.items() if k.startswith("C2"))
        assert c1["page_end"] == 10, "C1 has nothing on page 11 and must not claim it"
        assert c2["page_start"] == 11
        assert "The front setback is 6m." in c2["content"]
        assert "6m" not in c1["content"]

    def test_a_short_first_sentence_is_not_swallowed_by_the_title(self, monkeypatch):
        """Caught by this test while writing it. The title-continuation loop folds any
        following line under 50 characters into the heading, and a first attempt at the
        fix cut the body past everything the loop had absorbed -- so "C2 Setbacks" /
        "The front setback is 6m." kept the title and LOST the control. Repeating a
        title fragment in the body is untidy; deleting a setback is a wrong answer
        served as regulation. Only the matched heading is removed."""
        pages = {10: "C1 Introduction\nThis plan applies to the whole area.",
                 11: "C2 Setbacks\nThe front setback is 6m."}
        got = _extract(monkeypatch, pages)
        c2 = next(v for k, v in got.items() if k.startswith("C2"))
        assert "The front setback is 6m." in c2["content"], (
            "the control was absorbed into the section title and dropped from the body")

    @pytest.mark.parametrize("first_line", [
        "6m.",                                   # very short
        "The front setback is 6m.",              # under the 50-char continuation cap
        "Development must provide a front setback of at least 6 metres from the "
        "boundary.",                             # over it
    ])
    def test_the_first_line_survives_whatever_its_length(self, monkeypatch, first_line):
        """The continuation loop branches on length, so the body must be checked at
        both sides of its cap rather than at one convenient value."""
        got = _extract(monkeypatch, {10: "C1 Intro\nSomething.",
                                     11: f"C2 Setbacks\n{first_line}"})
        c2 = next(v for k, v in got.items() if k.startswith("C2"))
        assert first_line in c2["content"], f"lost the body for {first_line!r}"

    def test_a_page_with_no_heading_extends_the_open_section(self, monkeypatch):
        got = _extract(monkeypatch)
        c4 = next(v for k, v in got.items() if k.startswith("C4"))
        assert "disposed of to the street" in c4["content"]
        assert c4["page_end"] == 35
