"""Tests for the pure helpers of the AI extraction engine (scripts/ai_extractor.py).

The provider calls (Haiku/Mistral) hit the network and aren't unit-tested; the
chunking, JSON parsing, dedupe, and section-shape mapping are pure and are.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ai_extractor import (  # noqa: E402
    chunk_ranges, parse_provisions, dedupe_provisions, provisions_to_sections,
    _call_with_retry, _is_retryable,
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
