"""Tests for the pure helpers of the AI extraction engine (scripts/ai_extractor.py).

The provider calls (Haiku/Mistral) hit the network and aren't unit-tested; the
chunking, JSON parsing, dedupe, and section-shape mapping are pure and are.
"""
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ai_extractor import (  # noqa: E402
    chunk_ranges, parse_provisions, dedupe_provisions, provisions_to_sections,
    _call_with_retry, _is_retryable,
    coverage_gap, truncation_rate, COVERAGE_MIN_TOC,
)


class TestChunkRanges:
    def test_covers_all_pages(self):
        r = chunk_ranges(197, 12)
        assert r[0] == (0, 12) and r[-1] == (192, 197)
        assert sum(b - a for a, b in r) == 197

    def test_exact_multiple(self):
        assert chunk_ranges(24, 12) == [(0, 12), (12, 24)]

    def test_empty_and_degenerate(self):
        assert chunk_ranges(0, 12) == []
        assert chunk_ranges(10, 0) == []


class TestParseProvisions:
    def test_object_wrapper(self):
        out = parse_provisions('{"provisions": [{"code": "1.1", "title": "A", "text": "x"}]}')
        assert out == [{"code": "1.1", "title": "A", "text": "x"}]

    def test_bare_array(self):
        assert parse_provisions('[{"code": "1.2"}]') == [{"code": "1.2"}]

    def test_code_fenced(self):
        assert parse_provisions('```json\n{"provisions": [{"code": "2.1"}]}\n```') == [{"code": "2.1"}]

    def test_garbage_and_empty(self):
        assert parse_provisions("not json at all") == []
        assert parse_provisions("") == []
        assert parse_provisions(None) == []

    def test_filters_non_dicts(self):
        assert parse_provisions('{"provisions": [{"code":"1"}, "junk", 3]}') == [{"code": "1"}]


class TestDedupe:
    def test_dedupes_by_code_keeps_first(self):
        out = dedupe_provisions([{"code": "1.1", "title": "first"},
                                 {"code": "1.1", "title": "dup"},
                                 {"code": "1.2"}])
        assert out == [{"code": "1.1", "title": "first"}, {"code": "1.2"}]

    def test_drops_blank_codes(self):
        assert dedupe_provisions([{"code": ""}, {"title": "no code"}, {"code": "  "}]) == []


class TestToSections:
    def test_maps_to_extractor_shape(self):
        secs = provisions_to_sections([{"code": "1.1", "title": "Background", "text": "body", "page": 9}])
        s = secs[0]
        assert s["section_number"] == "1.1"
        assert s["section_title"] == "Background"
        assert s["content"] == "body"
        assert s["tables"] == [] and s["page_start"] == 9 and s["page_end"] == 9 and s["pages"] == [9]

    def test_page_defaults_and_bad_page(self):
        assert provisions_to_sections([{"code": "2"}])[0]["page_start"] == 1
        assert provisions_to_sections([{"code": "2", "page": "x"}])[0]["page_start"] == 1

    def test_drops_codeless(self):
        assert provisions_to_sections([{"title": "no code", "text": "x"}]) == []


class TestCoverageGap:
    def _toc(self, n):  # a TOC of n distinct top-level codes (>= COVERAGE_MIN_TOC)
        return {f"{i}.1" for i in range(1, n + 1)}

    def test_sub_provisions_count_as_covered(self):
        toc = self._toc(10)  # 1.1 .. 10.1
        # extracted has each section only as sub-codes (1.1.1 etc.) — still covered
        extracted = {f"{i}.1.{j}" for i in range(1, 11) for j in (1, 2)}
        ratio, missing = coverage_gap(extracted, toc)
        assert ratio == 0.0 and missing == []

    def test_missing_sections_flagged(self):
        toc = self._toc(10)
        extracted = {f"{i}.1" for i in range(1, 5)}  # only 4 of 10 covered
        ratio, missing = coverage_gap(extracted, toc)
        assert ratio == 0.6
        assert "10.1" in missing

    def test_small_toc_never_judged(self):
        # below COVERAGE_MIN_TOC -> no opinion (avoids false positives on tiny chapters)
        toc = {f"{i}.1" for i in range(1, COVERAGE_MIN_TOC)}
        assert coverage_gap(set(), toc) == (0.0, [])

    def test_section_space_subitem_codes_count_as_covered(self):
        # regression: the AI emits "<section> <objective/control>" (e.g. "C4.1 O1"),
        # which must cover TOC section "C4.1". Before the fix this false-fired 100%.
        toc = {f"C4.{i}" for i in range(1, 11)}  # C4.1 .. C4.10
        extracted = {f"C4.{i} {sub}" for i in range(1, 11) for sub in ("O1", "C1", "C2")}
        ratio, missing = coverage_gap(extracted, toc)
        assert ratio == 0.0 and missing == []

    def test_bare_subitem_codes_do_not_cover_sections(self):
        # the real leichhardt failure: controls coded as bare "C1".."C38" (section
        # attribution lost across chunks) must NOT be credited to any TOC section.
        toc = {f"C4.{i}" for i in range(1, 11)}
        extracted = {f"C{i}" for i in range(1, 39)}  # C1..C38, no section prefix
        ratio, missing = coverage_gap(extracted, toc)
        assert ratio == 1.0 and len(missing) == 10


class TestSectionThreading:
    def test_build_prompt_without_section_is_base(self):
        from ai_extractor import PROMPT, _build_prompt
        assert _build_prompt(None) == PROMPT
        assert _build_prompt("") == PROMPT

    def test_build_prompt_carries_section(self):
        from ai_extractor import PROMPT, _build_prompt
        p = _build_prompt("C4.9")
        assert p != PROMPT and "C4.9" in p

    def test_section_regex_matches_real_sections_not_bare_items(self):
        from ai_extractor import _SECTION_RE
        for good in ("C4.9", "3.1", "A2.10.1", "C1.0"):
            assert _SECTION_RE.match(good), good
        for bad in ("C1", "O1", "C44", "C7", ""):
            assert not _SECTION_RE.match(bad), bad

    def test_prompt_requires_section_qualified_codes(self):
        from ai_extractor import PROMPT
        # regression: the prompt must explicitly forbid bare codes
        assert "section-qualified" in PROMPT.lower()
        assert "never a bare" in PROMPT.lower()


class TestTruncationRate:
    def test_ellipsis_flagged(self):
        rate, n = truncation_rate([
            "A full, complete provision that clearly is not truncated at all here.",
            "This one is cut off mid sentence and ends with...",
            "…",
        ])
        assert n == 2 and rate == 2 / 3

    def test_short_text_flagged_but_bare_refs_exempt(self):
        rate, n = truncation_rate([
            "See clause 3.2 for details",                    # bare ref -> exempt
            "x",                                             # too short -> flagged
            "A perfectly reasonable length provision body here that is fine.",
        ])
        assert n == 1

    def test_empty(self):
        assert truncation_rate([]) == (0.0, 0)


_STUBS = ("boto3", "botocore", "pdfplumber", "psycopg2", "dotenv", "enrichment", "enrichment.pipeline")


class TestSuspectReasonNewGuards:
    """suspect_reason lives in dcp_extract_changed; import it with heavy deps stubbed."""

    def test_coverage_and_truncation_surface(self):
        # import suspect_reason under the heavy-dep stubs
        _saved = {k: sys.modules.get(k) for k in _STUBS}
        for k in _STUBS:
            sys.modules[k] = MagicMock()
        sys.modules["dotenv"].load_dotenv = MagicMock()
        os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
        for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
            os.environ.setdefault(_k, "x")
        try:
            from dcp_extract_changed import suspect_reason
        finally:
            for k, v in _saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        cov = {"diff": {"status": "ok"}, "schema_fail": False,
               "coverage_fail": True, "coverage_missing": 8, "coverage_toc": 27}
        trunc = {"diff": {"status": "ok"}, "schema_fail": False, "coverage_fail": False,
                 "truncation_fail": True, "truncation_flagged": 5, "total_provisions": 30}
        assert suspect_reason(cov).startswith("coverage_fail")
        assert suspect_reason(trunc).startswith("truncation_fail")
        assert suspect_reason({"diff": {"status": "ok"}, "schema_fail": False}) is None


class TestSuspectAlertDedup:
    """The same two chapters alerted byte-identically every day 1–13 Aug 2026.

    An alert with no memory cannot tell "this is new" from "this is still true",
    so the channel stopped being read — and the numeric-value-change alerts
    sharing it went unactioned for weeks.
    """

    @staticmethod
    def _load():
        _saved = {k: sys.modules.get(k) for k in _STUBS}
        for k in _STUBS:
            sys.modules[k] = MagicMock()
        sys.modules["dotenv"].load_dotenv = MagicMock()
        os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
        for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
            os.environ.setdefault(_k, "x")
        try:
            from dcp_extract_changed import suspect_alert_key, unalerted_suspects
        finally:
            for k, v in _saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        return suspect_alert_key, unalerted_suspects

    @staticmethod
    def _ch(council, key, content_hash, missing=8):
        return {"council": council, "chapter_key": key, "content_hash": content_hash,
                "diff": {"status": "ok"}, "schema_fail": False,
                "coverage_fail": True, "coverage_missing": missing, "coverage_toc": 27}

    def test_an_unchanged_condition_alerts_once_then_never_again(self):
        key_of, unalerted = self._load()
        ch = self._ch("hornsby", "part-1-general", "aaa")
        assert unalerted([ch], {}) == [ch], "first sighting must alert"
        seen = {("hornsby", "part-1-general"): key_of(ch)}
        assert unalerted([ch], seen) == [], "an unchanged condition must not re-alert"

    def test_a_changed_pdf_re_alerts(self):
        key_of, unalerted = self._load()
        old = self._ch("hornsby", "part-1-general", "aaa")
        new = self._ch("hornsby", "part-1-general", "bbb")
        seen = {("hornsby", "part-1-general"): key_of(old)}
        assert unalerted([new], seen) == [new], "a new content_hash is new information"

    def test_a_changed_FAILURE_MODE_re_alerts_on_the_same_pdf(self):
        """Hash-only keying would silence this, and it is the case that matters:
        same document, now failing worse."""
        key_of, unalerted = self._load()
        old = self._ch("hornsby", "part-1-general", "aaa", missing=8)
        worse = self._ch("hornsby", "part-1-general", "aaa", missing=99)
        assert key_of(old) != key_of(worse)
        seen = {("hornsby", "part-1-general"): key_of(old)}
        assert unalerted([worse], seen) == [worse]

    def test_suppression_is_per_chapter_not_global(self):
        key_of, unalerted = self._load()
        a = self._ch("hornsby", "part-1-general", "aaa")
        b = self._ch("city_of_sydney", "section-3", "ccc")
        seen = {("hornsby", "part-1-general"): key_of(a)}
        assert unalerted([a, b], seen) == [b], "one chapter's silence must not mute another"

    def test_an_IDENTICAL_condition_on_a_DIFFERENT_chapter_still_alerts(self):
        """The discriminator between per-chapter and global suppression.

        Two chapters can carry the same content_hash (duplicate source PDFs are
        real in dcp_chapter_registry) and the same reason, hence the same key.
        Looking the key up globally instead of per (council, chapter_key) would
        silence the second chapter, which has never been alerted about. The
        weaker version of this test passed against exactly that mutation.
        """
        key_of, unalerted = self._load()
        a = self._ch("hornsby", "part-1-general", "same-pdf-hash")
        b = self._ch("blacktown", "part-a-car-parking", "same-pdf-hash")
        assert key_of(a) == key_of(b), "same hash + same reason => same key, by construction"
        seen = {("hornsby", "part-1-general"): key_of(a)}
        assert unalerted([a, b], seen) == [b], (
            "a chapter nobody has been told about must alert, even when an "
            "identical condition elsewhere has already been reported"
        )

    def test_a_non_suspect_chapter_has_no_key_and_never_alerts(self):
        key_of, unalerted = self._load()
        clean = {"council": "x", "chapter_key": "y", "content_hash": "h",
                 "diff": {"status": "ok"}, "schema_fail": False}
        assert key_of(clean) is None
        assert unalerted([clean], {}) == []


class TestRetry:
    def test_unknown_model_raises(self):
        try:
            _call_with_retry("does-not-exist", b"%PDF")
            assert False, "should have raised"
        except ValueError as e:
            assert "Unknown AI_MODEL" in str(e)

    def test_retryable_classification(self):
        import urllib.error
        err429 = urllib.error.HTTPError("u", 429, "rate", {}, None)
        err400 = urllib.error.HTTPError("u", 400, "bad", {}, None)
        assert _is_retryable(err429) is True
        assert _is_retryable(err400) is False
        assert _is_retryable(ValueError("x")) is False


class TestRetryableTimeouts:
    def test_read_timeout_is_retryable(self):
        import urllib.error
        from ai_extractor import _is_retryable
        # the chapter-d failure mode: a socket read timeout
        assert _is_retryable(TimeoutError("read timed out")) is True
        assert _is_retryable(urllib.error.URLError("timed out")) is True

    def test_http_500_retryable_400_not(self):
        import urllib.error
        from ai_extractor import _is_retryable
        e500 = urllib.error.HTTPError("u", 503, "x", {}, None)
        e400 = urllib.error.HTTPError("u", 400, "x", {}, None)
        assert _is_retryable(e500) is True
        assert _is_retryable(e400) is False
