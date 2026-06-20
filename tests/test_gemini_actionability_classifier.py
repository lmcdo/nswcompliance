"""Tests for GeminiActionabilityClassifier.

Two tiers (per docs/DCP_PIPELINE_ARCHITECTURE_2026-06.md §5.3):

  Tier 1 — OFFLINE, deterministic, runs in pre-push pytest. No SDK, no API key.
    The classifier's genai import is lazy (inside __init__), so we construct
    instances with __new__ to exercise the pure verification/parse/fallback
    logic — the actual defensibility gate — without any network or google-genai.

  Tier 2 — LIVE smoke against the real Gemini API. Skipped unless RUN_LIVE_GEMINI
    is set, so it never runs in CI/pre-push. Proves the SDK + model + JSON mode +
    the verbatim-verification contract end-to-end.

The single invariant under test everywhere: Gemini output is a *proposal*. A
result is only trusted (verified=True) when the identified span is a verbatim
substring of the source. Every other path falls back to is_actionable=True —
the model can never silently mark a provision non-actionable.
"""

import json
import os

import pytest

from enrichment.extractors.gemini_actionability_classifier import (
    GeminiActionabilityClassifier,
    GeminiClassificationResult,
    is_performance_based_dcp,
)


# ── helpers ─────────────────────────────────────────────────────────────────

def _bare_classifier() -> GeminiActionabilityClassifier:
    """Construct without __init__ — no google-genai, no API key required.

    Valid because the SDK import lives in __init__; _parse_and_verify / classify
    only need _model_name (+ a _call_gemini we patch per test).
    """
    clf = GeminiActionabilityClassifier.__new__(GeminiActionabilityClassifier)
    clf._model_name = "test-model"
    clf._temperature = 0.0
    return clf


def _resp(**kwargs) -> str:
    return json.dumps(kwargs)


# ── Tier 1a: the verbatim-verification gate (_parse_and_verify) ──────────────


class TestParseAndVerifyGate:
    """The verbatim-substring gate is the core defensibility mechanism (ADR-001)."""

    def test_actionable_span_present_is_verified_with_correct_offsets(self):
        corpus = "Clause 4.2: The minimum front setback is 6 metres to the street."
        span = "The minimum front setback is 6 metres"
        clf = _bare_classifier()
        r = clf._parse_and_verify(_resp(is_actionable=True, identified_text=span, reason="control"), corpus)
        assert r.verified is True
        assert r.is_actionable is True
        assert r.identified_text == span
        # ADR-001 contract: the stored offsets reconstruct the span exactly.
        assert corpus[r.char_start:r.char_end] == span

    def test_actionable_span_not_in_corpus_falls_back_unverified(self):
        clf = _bare_classifier()
        r = clf._parse_and_verify(
            _resp(is_actionable=True, identified_text="a setback the document never stated", reason="x"),
            corpus="Some unrelated source text about landscaping.",
        )
        assert r.verified is False
        assert r.is_actionable is True  # conservative fallback, never dropped
        assert r.char_start is None and r.char_end is None

    def test_non_actionable_with_no_span_is_verified_non_actionable(self):
        clf = _bare_classifier()
        r = clf._parse_and_verify(_resp(is_actionable=False, identified_text=None, reason="narrative"), corpus="History of the area.")
        assert r.verified is True
        assert r.is_actionable is False
        assert r.identified_text is None

    def test_non_actionable_but_span_provided_is_ambiguous_fallback(self):
        """is_actionable=false WITH a span = contradictory → conservative fallback."""
        clf = _bare_classifier()
        r = clf._parse_and_verify(
            _resp(is_actionable=False, identified_text="must not exceed 8.5 metres", reason="?"),
            corpus="Buildings must not exceed 8.5 metres in height.",
        )
        assert r.verified is False
        assert r.is_actionable is True

    def test_actionable_but_no_span_falls_back(self):
        clf = _bare_classifier()
        r = clf._parse_and_verify(_resp(is_actionable=True, identified_text=None, reason="x"), corpus="text")
        assert r.verified is False
        assert r.is_actionable is True

    def test_malformed_json_falls_back(self):
        clf = _bare_classifier()
        r = clf._parse_and_verify("not json at all { ", corpus="text")
        assert r.verified is False
        assert r.is_actionable is True

    def test_markdown_fenced_json_is_parsed(self):
        corpus = "The deep soil zone must be at least 15% of the site."
        span = "at least 15% of the site"
        clf = _bare_classifier()
        fenced = "```json\n" + _resp(is_actionable=True, identified_text=span, reason="control") + "\n```"
        r = clf._parse_and_verify(fenced, corpus)
        assert r.verified is True
        assert r.identified_text == span

    def test_string_false_is_not_read_as_truthy(self):
        """A model emitting the string 'false' must not be treated as actionable."""
        clf = _bare_classifier()
        r = clf._parse_and_verify('{"is_actionable": "false", "identified_text": null, "reason": "x"}', corpus="text")
        assert r.is_actionable is False
        assert r.verified is True

    def test_empty_response_falls_back(self):
        clf = _bare_classifier()
        r = clf._parse_and_verify("", corpus="text")
        assert r.verified is False
        assert r.is_actionable is True


# ── Tier 1b: classify() orchestration + API-failure fallback ─────────────────


class TestClassifyOrchestration:
    def test_valid_response_flows_through_to_verified(self):
        corpus = "Side setbacks must be a minimum of 900mm."
        span = "minimum of 900mm"
        clf = _bare_classifier()
        clf._call_gemini = lambda prompt: _resp(is_actionable=True, identified_text=span, reason="control")
        r = clf.classify(corpus, "Ashfield DCP 2016", source_text=corpus)
        assert r.verified is True
        assert r.identified_text == span

    def test_api_exception_is_conservative_fallback(self):
        clf = _bare_classifier()
        def boom(prompt):
            raise RuntimeError("429 rate limited")
        clf._call_gemini = boom
        r = clf.classify("anything", "Ashfield DCP", source_text="anything")
        assert r.verified is False
        assert r.is_actionable is True
        assert "conservative fallback" in r.reason

    def test_source_text_defaults_to_provision_text(self):
        text = "Landscaped area must be 30% minimum."
        clf = _bare_classifier()
        clf._call_gemini = lambda prompt: _resp(is_actionable=True, identified_text="30% minimum", reason="c")
        r = clf.classify(text, "Ashfield DCP")  # no source_text
        assert r.verified is True


# ── Tier 1c: the proposal-only invariant (cannot silently drop) ──────────────


class TestProposalOnlyInvariant:
    """No unverified Gemini output may ever yield is_actionable=False."""

    @pytest.mark.parametrize("payload", [
        '{"is_actionable": true, "identified_text": "ghost span not in source"}',
        '{"is_actionable": true, "identified_text": null}',
        '{"is_actionable": false, "identified_text": "span present in source"}',
        "garbage not json",
        "",
        '{"is_actionable": "false", "identified_text": "span present in source"}',
    ])
    def test_unverified_is_never_non_actionable(self, payload):
        corpus = "span present in source — and other regulatory text here."
        clf = _bare_classifier()
        r = clf._parse_and_verify(payload, corpus)
        if not r.verified:
            assert r.is_actionable is True, "unverified output must default to actionable"


# ── Tier 1d: document routing ────────────────────────────────────────────────


class TestPerformanceBasedRouting:
    def test_ashfield_routes_to_stage3(self):
        assert is_performance_based_dcp("Ashfield_DCP_2016__chapter-f") is True

    def test_other_council_does_not_route(self):
        assert is_performance_based_dcp("Marrickville DCP 2011 part 4") is False

    def test_empty_document_id_does_not_route(self):
        assert is_performance_based_dcp("") is False


# ── Tier 2: LIVE smoke against the real Gemini API ──────────────────────────


@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_GEMINI"),
    reason="live Gemini smoke — set RUN_LIVE_GEMINI=1 (and GEMINI_API_KEY) to run",
)
class TestLiveGeminiSmoke:
    """Proves SDK + model + JSON mode + verbatim contract against the real API.

    Not run in pre-push (no flag). Run with:
        RUN_LIVE_GEMINI=1 python -m pytest tests/test_gemini_actionability_classifier.py -k Live -v
    """

    @pytest.fixture(autouse=True)
    def _real_requests(self):
        """conftest_mocks stubs `requests` with a MagicMock for offline tests;
        the live Gemini client needs the real package. Restore it for this class."""
        import sys
        import importlib
        import unittest.mock as _mock
        if isinstance(sys.modules.get("requests"), _mock.MagicMock):
            for name in [m for m in list(sys.modules) if m == "requests" or m.startswith("requests.")]:
                del sys.modules[name]
            importlib.invalidate_caches()
            importlib.import_module("requests")
        yield

    def test_actionable_provision_verifies_with_real_offsets(self):
        clf = GeminiActionabilityClassifier()
        prov = "The minimum front setback to the street boundary is 6 metres."
        r = clf.classify(prov, "Ashfield DCP 2016", source_text=prov)
        assert r.model == clf._model_name
        # If trusted, the ADR-001 contract must hold against the live output.
        if r.verified and r.identified_text is not None:
            assert prov[r.char_start:r.char_end] == r.identified_text

    def test_call_never_raises_and_returns_result(self):
        clf = GeminiActionabilityClassifier()
        boilerplate = "This chapter outlines the historical background of the local area."
        r = clf.classify(boilerplate, "Ashfield DCP 2016", source_text=boilerplate)
        assert isinstance(r, GeminiClassificationResult)
        # Whatever the model decides, the verbatim contract is never violated.
        if r.verified and r.identified_text is not None:
            assert boilerplate[r.char_start:r.char_end] == r.identified_text
