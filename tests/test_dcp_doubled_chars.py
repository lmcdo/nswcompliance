"""dcp_extract_changed._drop_doubled_chars: a glyph printed twice over itself is read once (Campbelltown Part 3)."""
import sys
from pathlib import Path

import pytest

fitz = pytest.importorskip("fitz")
pdfplumber = pytest.importorskip("pdfplumber")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import dcp_extract_changed as dx  # noqa: E402

LINE = "Pool pumps shall not exceed 5 dBA above background levels"


def _pdf(path, twice: bool):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), LINE, fontsize=11)
    if twice:   # the second copy exactly over the first, white, as the council's PDF does
        page.insert_text((72, 100), LINE, fontsize=11, color=(1, 1, 1))
    page.insert_text((72, 140), "Second rule line", fontsize=11)
    doc.save(str(path))
    doc.close()


def test_doubled_line_is_read_once(tmp_path):
    f = tmp_path / "d.pdf"
    _pdf(f, twice=True)
    with pdfplumber.open(str(f)) as pdf:
        page = pdf.pages[0]
        assert LINE not in (page.extract_text() or "")          # the defect: characters interleaved twice
        text = dx._extract_page_text(page, "campbelltown")
    assert LINE in text and text.count("Pool") == 1 and "Second rule line" in text


def test_ordinary_page_is_unchanged(tmp_path):
    f = tmp_path / "s.pdf"
    _pdf(f, twice=False)
    with pdfplumber.open(str(f)) as pdf:
        page = pdf.pages[0]
        assert dx._extract_page_text(page, "campbelltown") == (page.extract_text() or "")


def test_a_page_object_without_dedupe_is_left_alone():
    f = object()
    assert dx._drop_doubled_chars(f) is f


def test_a_real_dedupe_failure_is_not_swallowed():
    class Broken:
        def dedupe_chars(self, **_):
            raise AttributeError("bad char record")
    with pytest.raises(AttributeError):
        dx._drop_doubled_chars(Broken())
