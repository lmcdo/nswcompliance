"""Reader input for PDFs that print every line twice at the same spot (Campbelltown Part 3 page 41, 2026-10-18)."""
import sys
from pathlib import Path

import pytest

fitz = pytest.importorskip("fitz")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import ai_extractor as ax  # noqa: E402

LINES = [f"C{i} Development must be set back {i} metres from the side boundary." for i in range(1, 15)]


def _pdf(doubled: bool, lines=LINES) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    for n, ln in enumerate(lines):
        y = 60 + 16 * n
        page.insert_text((72, y), ln, fontsize=10, color=(0, 0, 0))
        if doubled:   # the hidden copy: same text, same spot, white
            page.insert_text((72, y), ln, fontsize=10, color=(1, 1, 1))
    data = doc.tobytes()
    doc.close()
    return data


def test_doubled_page_text_keeps_each_line_once():
    twins, pages = ax.doubled_text(_pdf(True))
    assert twins >= len(LINES)
    for ln in LINES:
        assert pages[0].count(ln) == 1


def test_normal_page_is_sent_unchanged():
    raw = _pdf(False)
    pdf, prompt = ax.reader_input(raw, "PROMPT")
    assert pdf == raw and prompt == "PROMPT"


def test_doubled_chunk_becomes_pictures_plus_clean_text():
    raw = _pdf(True)
    pdf, prompt = ax.reader_input(raw, "PROMPT")
    assert pdf != raw and prompt.startswith("PROMPT") and ax.DOUBLED_NOTE.strip() in prompt
    with fitz.open(stream=pdf, filetype="pdf") as doc:
        assert doc.page_count == 1 and doc[0].get_text().strip() == ""     # pictures: no text layer to stutter
        assert doc[0].get_images()
    for ln in LINES:
        assert prompt.count(ln) == 1                                      # the clean text, each line once


def test_a_few_twins_do_not_switch_the_reader_input():
    raw = _pdf(True, LINES[: ax.DOUBLED_MIN_SPANS - 1])
    assert ax.doubled_text(raw)[0] < ax.DOUBLED_MIN_SPANS
    assert ax.reader_input(raw, "PROMPT") == (raw, "PROMPT")


def test_same_text_at_a_different_spot_is_not_a_twin():
    doc = fitz.open()
    page = doc.new_page()
    for n in range(12):
        page.insert_text((72, 60 + 16 * n), "Refer to Figure 3.", fontsize=10)   # repeated on purpose, new spots
    raw = doc.tobytes()
    doc.close()
    assert ax.doubled_text(raw)[0] == 0


def test_deepseek_gets_the_de_doubled_text(monkeypatch):
    sent = {}

    def fake_urlopen(req, timeout=0):
        import json as _j
        sent["body"] = _j.loads(req.data.decode())
        raise RuntimeError("stop after capture")

    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    monkeypatch.setattr(ax.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(Exception):
        ax._call_deepseek(_pdf(True), "PROMPT")
    content = sent["body"]["messages"][0]["content"]
    for ln in LINES:
        assert content.count(ln) == 1
