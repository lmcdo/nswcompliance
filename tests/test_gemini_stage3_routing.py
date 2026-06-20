"""Offline gate for the Gemini Stage-3 wiring in enrichment/pipeline.py.

Verifies the safety-critical wiring with mocks (no SDK, no API, no DB):
  - OFF by default (DCP_GEMINI_STAGE3 unset -> None -> regex everywhere).
  - performance-based docs route to Gemini; everything else to the regex classifier.
  - gemini=None always uses regex.
  - the cache short-circuits the API on a hit, and stores on a miss.
"""

from unittest.mock import MagicMock

from enrichment.pipeline import (
    _maybe_build_gemini,
    _classify_one,
    _gemini_classify_cached,
)


def _gemini_result():
    return MagicMock(is_actionable=True, verified=True, identified_text="x",
                     char_start=0, char_end=1, reason="r")


class TestStage3Gating:
    def test_off_by_default(self, monkeypatch):
        monkeypatch.delenv("DCP_GEMINI_STAGE3", raising=False)
        assert _maybe_build_gemini() is None

    def test_disabled_value_stays_off(self, monkeypatch):
        monkeypatch.setenv("DCP_GEMINI_STAGE3", "0")
        assert _maybe_build_gemini() is None


class TestRouting:
    def _gemini(self):
        g = MagicMock()
        g._model_name = "gemini-2.5-flash"
        g.classify.return_value = _gemini_result()
        return g

    def test_performance_based_routes_to_gemini(self):
        g = self._gemini()
        regex = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = None
        _classify_one(
            {"provision_text": "t", "document_id": "Ashfield DCP 2016", "section_header": "Controls"},
            regex, g, cur,
        )
        g.classify.assert_called_once()
        regex.classify.assert_not_called()

    def test_other_council_routes_to_regex(self):
        g = self._gemini()
        regex = MagicMock()
        regex.classify.return_value = (True, "regex")
        _classify_one(
            {"provision_text": "t", "document_id": "Marrickville DCP 2011", "section_header": "Controls"},
            regex, g, MagicMock(),
        )
        regex.classify.assert_called_once()
        g.classify.assert_not_called()

    def test_no_gemini_uses_regex_even_for_performance_doc(self):
        regex = MagicMock()
        regex.classify.return_value = (True, "regex")
        _classify_one(
            {"provision_text": "t", "document_id": "Ashfield DCP 2016", "section_header": "Controls"},
            regex, None, MagicMock(),
        )
        regex.classify.assert_called_once()


class TestCache:
    def test_cache_hit_skips_the_api(self):
        g = MagicMock()
        g._model_name = "m"
        cur = MagicMock()
        cur.fetchone.return_value = {"is_actionable": False, "reason": "cached reason"}
        actionable, _ = _gemini_classify_cached(g, "text", "doc", cur)
        assert actionable is False
        g.classify.assert_not_called()

    def test_cache_miss_calls_api_and_stores(self):
        g = MagicMock()
        g._model_name = "m"
        g.classify.return_value = _gemini_result()
        cur = MagicMock()
        cur.fetchone.return_value = None
        actionable, _ = _gemini_classify_cached(g, "text", "doc", cur)
        assert actionable is True
        g.classify.assert_called_once()
        assert any(
            "INSERT INTO gemini_classification_cache" in c.args[0]
            for c in cur.execute.call_args_list
        )
