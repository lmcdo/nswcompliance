"""A chapter the LLM reader FIXED was still marked suspect, forever, for being two-column.

`preflight_two_column` is measured from the PDF BEFORE anything is read. It says "this
source has two columns" — a warning about the regex reader, whose left-to-right sort
interleaves them. The LLM reader was adopted precisely to read a two-column body
(`ce-ai-extraction-decision-2026-07`), so applying that flag to its output marks every
chapter it repairs as suspect and NOTHING CAN EVER CLEAR IT. Doing a better job does not
change the source's column count.

Measured 2026-09-22 on canterbury_bankstown/chapter-7-6-belmore-and-lakemba, the chapter
that timed out entirely on the regex reader, re-read by sol:

    431 sections   0 serious artifacts   0 rows tripping the DQ-78 scramble signature
    worst single-letter token ratio 0.047 against a 0.20 threshold
    (the served version of this chapter carries 10 scrambled rows)

and its ONLY complaint was `preflight_two_column (67/141 text pages)`. Every content-based
check had already passed. So the good extraction and a failed one were indistinguishable,
which is why the hard chapters never landed.

THE RISK THIS CARRIES, AND THE TESTS THAT BOUND IT
--------------------------------------------------
Exempting a reader from a guard is the shape of change that goes wrong quietly. The LLM
has its own failure modes — dropping whole TOC sections, truncating mid-provision,
collapsing sub-sections — and `coverage_fail`, `truncation_fail` and
`attribution_collapsed` exist SPECIFICALLY to police it. If this change let those slide
too, it would trade a false block for a silent hole, which is strictly worse.

So `TestTheLlmIsStillPoliced` is the real test here, not `TestTheFlagIsSuppressed`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

dx = pytest.importorskip("scripts.dcp_extract_changed")

#: The real preflight from the 2026-09-22 sol run of chapter-7-6.
TWO_COLUMN_PREFLIGHT = {
    "text_pages": 141,
    "two_column_pages": 67,
    "rotated_pages": 0,
    "garbled_pages": 0,
    "empty_text_pages": 2,
    "total_pages": 143,
    "two_column_fail": True,
}


def review(reader: str | None, **over) -> dict:
    """A review_data dict that passes every CONTENT check, as the sol run did."""
    data = {
        "preflight": dict(TWO_COLUMN_PREFLIGHT),
        "diff": {"status": "ok", "total_new": 431, "total_old": 52},
        "schema_fail": False,
        "coverage_fail": False,
        "coverage_unknown": False,
        "truncation_fail": False,
        "attribution_fail": False,
        "total_provisions": 431,
    }
    if reader is not None:
        data["reader_used"] = reader
    data.update(over)
    return data


class TestTheFlagIsSuppressedOnlyForTheReaderItCannotDescribe:
    def test_the_llm_reader_is_not_suspect_for_a_two_column_source(self):
        assert dx.suspect_reason(review("llm:sol")) is None, (
            "a chapter the LLM read cleanly is still blocked by a measurement of the "
            "SOURCE's column count, which no amount of correctness can change")

    @pytest.mark.parametrize("model", ["llm:sol", "llm:sonnet", "llm:haiku", "llm:mistral"])
    def test_any_llm_model_qualifies(self, model):
        assert dx.suspect_reason(review(model)) is None

    def test_the_regex_reader_IS_still_suspect(self):
        """The flag is not removed. It still means what it always meant, for the reader
        it was written about — the one whose left-to-right sort interleaves columns."""
        got = dx.suspect_reason(review("regex"))
        assert got is not None and got.startswith("preflight_two_column"), got

    def test_an_unknown_reader_is_treated_as_regex(self):
        """Absent/None must be conservative. An unknown reader getting the LLM's
        exemption is how a guard silently stops applying to anything."""
        got = dx.suspect_reason(review(None))
        assert got is not None and got.startswith("preflight_two_column"), got

    @pytest.mark.parametrize("reader", [
        "geometric-columnar",
        # These CONTAIN "llm" but are not the LLM reader. A substring match would hand
        # each of them the exemption, which is the mutation that survived the first
        # round of this test: "geometric-columnar" alone could not tell prefix-matching
        # from substring-matching, because it contains no "llm" at all.
        "regex-after-llm-fallback",
        "regex(no-llm-key)",
        "ocr+llm-disabled",
    ])
    def test_a_non_llm_reader_does_not_get_the_exemption_by_accident(self, reader):
        """Matching must be on the `llm:` PREFIX, not a substring anywhere.

        The fallback path's own log line says "AI_EXTRACTION is DISABLED", so a future
        reader label recording that fact is likely to contain the letters `llm` while
        meaning the exact opposite.
        """
        got = dx.suspect_reason(review(reader))
        assert got is not None and got.startswith("preflight_two_column"), (
            f"reader {reader!r} was exempted from the two-column flag; only a reader "
            f"whose label STARTS WITH 'llm:' may be")


class TestTheLlmIsStillPoliced:
    """The point of the change is to remove ONE source-shape heuristic, not to trust the
    LLM. Each check below is evidence about the OUTPUT and must still fire."""

    def test_missing_toc_sections_still_flag(self):
        got = dx.suspect_reason(review("llm:sol", coverage_fail=True,
                                       coverage_missing=43, coverage_toc=54))
        assert got is not None and got.startswith("coverage_fail"), got

    def test_truncated_provisions_still_flag(self):
        got = dx.suspect_reason(review("llm:sol", truncation_fail=True,
                                       truncation_flagged=20))
        assert got is not None and got.startswith("truncation_fail"), got

    def test_collapsed_subsections_still_flag(self):
        got = dx.suspect_reason(review("llm:sol", attribution_fail=True,
                                       attribution_sections=3, attribution_listed=54))
        assert got is not None and got.startswith("attribution_collapsed"), got

    def test_serious_artifacts_still_flag(self):
        got = dx.suspect_reason(review("llm:sol", schema_fail=True,
                                       serious_artifact_provisions=12))
        assert got is not None and got.startswith("schema_fail"), got

    def test_a_count_drop_still_flags(self):
        got = dx.suspect_reason(review(
            "llm:sol", diff={"status": "count_drop", "total_new": 12, "total_old": 52}))
        assert got is not None and got.startswith("count_drop"), got

    def test_an_unreadable_contents_page_still_flags(self):
        got = dx.suspect_reason(review("llm:sol", coverage_unknown=True, coverage_toc=1))
        assert got is not None and got.startswith("coverage_unknown"), got

    def test_a_scanned_source_still_flags_for_the_llm_too(self):
        """`empty_layer` is NOT exempted. A page with no text layer has nothing for any
        text reader to read, LLM included — unlike two columns, which is only a problem
        for a reader that sorts left to right."""
        pf = dict(TWO_COLUMN_PREFLIGHT)
        pf.update({"two_column_fail": False, "empty_layer_fail": True,
                   "empty_text_pages": 120})
        got = dx.suspect_reason(review("llm:sol", preflight=pf))
        assert got is not None and got.startswith("preflight_empty_layer"), got


class TestTheRunNamesTheReaderItActuallyUsed:
    """A run with AI_MODEL=sol printed '(sonnet)' while Anthropic had no credit at all —
    the line reported the DEFAULT, not the model that produced the chapter. A
    misattributed reader makes any later regression impossible to trace to its cause."""

    def test_an_explicit_model_is_reported_not_the_default(self):
        src = (ROOT / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")
        assert 'os.getenv("AI_MODEL")' in src, (
            "the reader label still asks configured_model() alone, so an explicit "
            "AI_MODEL is announced as whichever provider key happens to be present")

    def test_the_reader_is_recorded_on_the_extractor(self):
        src = (ROOT / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")
        assert "reader_used" in src
        assert 'self.reader_used = "regex"' in src, (
            "the fallback path must record itself, or an unknown reader could inherit "
            "the LLM's exemption")
