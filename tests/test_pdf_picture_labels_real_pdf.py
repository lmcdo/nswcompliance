"""The picture-label reader against a real PDF, not fakes.

Builds a page the way Leichhardt's is built -- a "Controls" heading, then each
control's label drawn as a small image whose glyph is in its soft mask -- and
reads it through citation_proof.read_raw_lines. The fakes in
test_pdf_picture_labels.py cannot catch PyMuPDF reporting every label as the
same image (it matches by base pixels), which is what the draw-order pairing
exists for.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

fitz = pytest.importorskip("fitz")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import citation_proof as C  # noqa: E402


def _label_image(seed: int):
    """A 12x8 black box whose alpha (the mask) differs by `seed`: same base
    pixels for every label, as in the council's PDF."""
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 12, 8), True)
    pix.clear_with(0)
    for x in range(12):
        for y in range(8):
            pix.set_pixel(x, y, (0, 0, 0, 255 if (x * 7 + y * 3 + seed) % 5 == 0 else 0))
    return pix


def _pdf(tmp_path, labels_per_row, icon=False):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 80), "Controls", fontsize=10)
    if icon:     # a smaller margin icon between the heading and the first label
        page.insert_image(fitz.Rect(72, 88, 78, 93), pixmap=_label_image(9))
    y = 110
    rows = []
    for text, seed in labels_per_row:
        page.insert_image(fitz.Rect(72, y - 8, 84, y), pixmap=_label_image(seed))
        page.insert_text((108, y), text, fontsize=10)
        rows.append(text.lower())
        y += 20
    path = tmp_path / "labels.pdf"
    doc.save(str(path))
    return str(path), rows


def test_each_label_picture_is_read_in_front_of_its_rule(tmp_path):
    path, rows = _pdf(tmp_path, [("First rule words here", 1),
                                 ("Second rule words here", 2),
                                 ("Third rule words here", 3)])
    raw, _width = C.read_raw_lines(path)
    texts = [ln.text for ln in raw]
    for label, row in zip(["c1", "c2", "c3"], rows):
        assert texts.index(label) == texts.index(row) - 1, texts


def test_the_same_picture_twice_under_one_run_names_nothing(tmp_path):
    # Picture 1 counted as C1 and again as C3: the counting cannot be trusted,
    # so no label is invented -- the proof refuses as it did before.
    path, _ = _pdf(tmp_path, [("First rule words here", 1),
                              ("Second rule words here", 2),
                              ("Third rule words here", 1)])
    raw, _width = C.read_raw_lines(path)
    assert not any(ln.text in {"c1", "c2", "c3"} for ln in raw)


def test_a_margin_icon_of_another_size_does_not_shift_the_labels(tmp_path):
    # Cross-review: an icon after "Controls" in every run would be counted as
    # C1, consistently, and every real label would read one too high.
    path, rows = _pdf(tmp_path, [("First rule words here", 1),
                                 ("Second rule words here", 2),
                                 ("Third rule words here", 3)], icon=True)
    raw, _width = C.read_raw_lines(path)
    texts = [ln.text for ln in raw]
    for label, row in zip(["c1", "c2", "c3"], rows):
        assert texts.index(label) == texts.index(row) - 1, texts
    assert "c4" not in texts
