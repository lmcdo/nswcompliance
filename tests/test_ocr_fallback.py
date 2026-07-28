"""OCR extraction fallback (#832 integration).

Contract:
  - the trigger fires only on a garbled text layer
  - OCR output normalises to splitter-ready plain text (tags gone, tables
    flattened to pipe-rows)
  - the fetch fails visible: missing env, non-200, junk payload, and network
    errors ALL return None so extraction proceeds on the text layer unchanged
"""

import importlib.util
import os
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SRC = (ROOT / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")


def _extract_def(name: str) -> str:
    start = SRC.index(f"def {name}(")
    nxt = re.search(r"\n(?:def |class |# ── )", SRC[start + 10:])
    end = start + 10 + nxt.start() if nxt else len(SRC)
    return SRC[start:end]


def _load_funcs():
    ns: dict = {"re": re, "os": os}
    # exec the whole module-level constants block (regexes may span lines)
    start = SRC.index("_GARBLE_RUN = ")
    end = SRC.index("def strip_garbled_header_lines")
    exec(SRC[start:end], ns)
    exec(_extract_def("_garble_evidence"), ns)
    exec(_extract_def("normalise_ocr_page"), ns)
    exec(_extract_def("text_layer_garbled"), ns)
    exec(_extract_def("fetch_ocr_page_texts"), ns)
    return ns


NS = _load_funcs()
normalise_ocr_page = NS["normalise_ocr_page"]
text_layer_garbled = NS["text_layer_garbled"]
fetch_ocr_page_texts = NS["fetch_ocr_page_texts"]


class TestNormaliseOcrPage:
    def test_detection_tags_stripped(self):
        raw = "<|det|>text [384, 748, 885, 791]<|/det|>Setback is 6m from the boundary."
        out = normalise_ocr_page(raw)
        assert "det" not in out and "[384" not in out
        assert "Setback is 6m from the boundary." in out

    def test_table_markup_flattens_to_pipe_rows(self):
        raw = "<table><tr><td>Dwelling house</td><td>2 spaces</td></tr><tr><td>Visitor</td><td>0.25 spaces</td></tr></table>"
        out = normalise_ocr_page(raw)
        assert "<table>" not in out and "<td>" not in out
        assert "<tr" not in out.lower()          # Sol #836: opening row tags must go too
        assert "Dwelling house | 2 spaces" in out
        assert "Visitor | 0.25 spaces" in out

    def test_empty_cells_preserved_as_column_placeholders(self):
        """Sol #836: collapsing empty cells shifts a value into the wrong
        column — a setback under Zone B must not read as Zone A's."""
        raw = "<table><tr><td>Control</td><td>Zone A</td><td>Zone B</td></tr><tr><td>Setback</td><td></td><td>3m</td></tr></table>"
        out = normalise_ocr_page(raw)
        setback_row = next(l for l in out.splitlines() if "Setback" in l)
        assert re.search(r"Setback \|\s+\| 3m", setback_row), setback_row  # empty Zone A slot kept

    def test_empty_and_none_safe(self):
        assert normalise_ocr_page("") == ""
        assert normalise_ocr_page(None) == ""


class TestTrigger:
    def test_fires_on_doubled_glyph_layer(self):
        assert text_layer_garbled(["clean page", "Section 3 GGEENNEERRAALL PPRROOVVIISSIIOONNSS"])

    def test_fires_on_interleave(self):
        assert text_layer_garbled(["nneeww ddwweelllliinngg new dwelling"])

    def test_silent_on_clean_layer(self):
        assert not text_layer_garbled(["Lloyd Street setback is 3m.", "Attachment III applies."])

    def test_legitimate_double_letter_words_do_not_fire(self):
        """Sol #836: 'bookkeeping' (oo·kk·ee) matches the bare pattern — one
        short run must never route a clean chapter through OCR."""
        assert not text_layer_garbled(["The bookkeeping records and the bookkeeper's fees."])

    def test_long_single_run_fires(self):
        assert text_layer_garbled(["Section 3 GGEENNEERRAALL heading"])

    def test_empty_pages_do_not_fire(self):
        assert not text_layer_garbled(["", None])


class TestFetchFailsVisible:
    def test_missing_env_returns_none(self, monkeypatch):
        monkeypatch.delenv("MODAL_OCR_URL", raising=False)
        monkeypatch.delenv("MODAL_OCR_TOKEN", raising=False)
        assert fetch_ocr_page_texts(__file__, 1) is None

    def _env(self, monkeypatch):
        monkeypatch.setenv("MODAL_OCR_URL", "https://example.invalid/ocr")
        monkeypatch.setenv("MODAL_OCR_TOKEN", "t")

    def test_non_200_returns_none(self, monkeypatch):
        self._env(monkeypatch)
        fake = MagicMock()
        fake.post.return_value = MagicMock(status_code=503)
        with patch.dict(sys.modules, {"requests": fake}):
            assert fetch_ocr_page_texts(__file__, 1) is None

    def test_junk_payload_returns_none(self, monkeypatch):
        self._env(monkeypatch)
        fake = MagicMock()
        fake.post.return_value = MagicMock(status_code=200, json=lambda: {"pages": "not-a-list"})
        with patch.dict(sys.modules, {"requests": fake}):
            assert fetch_ocr_page_texts(__file__, 1) is None

    def test_page_count_mismatch_returns_none(self, monkeypatch):
        """Sol #836: 19 pages back for a 20-page PDF would serve OCR text for
        the wrong source pages — reject the whole response."""
        self._env(monkeypatch)
        fake = MagicMock()
        fake.post.return_value = MagicMock(status_code=200, json=lambda: {"pages": ["a", "b"]})
        with patch.dict(sys.modules, {"requests": fake}):
            assert fetch_ocr_page_texts(__file__, 3) is None

    def test_network_error_returns_none(self, monkeypatch):
        self._env(monkeypatch)
        fake = MagicMock()
        fake.post.side_effect = RuntimeError("boom")
        with patch.dict(sys.modules, {"requests": fake}):
            assert fetch_ocr_page_texts(__file__, 1) is None

    def test_success_returns_normalised_pages(self, monkeypatch):
        self._env(monkeypatch)
        fake = MagicMock()
        fake.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"pages": ["<|det|>text [1, 2, 3, 4]<|/det|>Objectives 1 To ensure"]},
        )
        with patch.dict(sys.modules, {"requests": fake}):
            out = fetch_ocr_page_texts(__file__, 1)
        assert out == ["Objectives 1 To ensure"]


class TestSeamSourcePins:
    def test_page_reads_route_through_page_text_helper(self):
        """All three read sites must use the ocr-aware helper, and pdfplumber
        table extraction must be skipped in OCR mode."""
        assert SRC.count("self._page_text(") >= 3
        assert "page_tables = [] if self.ocr_pages else" in SRC
        assert "if not self.ocr_pages:" in SRC

    def test_trigger_gated_on_env_and_garble(self):
        assert 'os.getenv("MODAL_OCR_URL", "").strip()' in SRC
        assert "text_layer_garbled(_raw)" in SRC
