"""The AI reader must record the page a rule is on, not the first page of the chunk it read.

scripts/ai_extractor.py stored `a + 1` (the chunk's first page) for every rule: measured
2026-09-26, 45% of 17,489 served rules linked to a page that does not hold them. These tests
build a real 12-page PDF so the reader's own pypdf text extraction is what gets located.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
fitz = pytest.importorskip("fitz")
pypdf = pytest.importorskip("pypdf")

import ai_extractor as ai  # noqa: E402

RULE = ("Buildings are to be set back from the front boundary consistent with the "
        "prevailing setback of adjoining dwellings in the street.")
OTHER = "Landscaped area provisions apply to the rear of the site and include deep soil zones."


def _pdf(tmp_path, pages: dict[int, str], n: int = 12):
    doc = fitz.open()
    for i in range(1, n + 1):
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(50, 80, 550, 700), pages.get(i, OTHER), fontsize=10)
    path = tmp_path / "chapter.pdf"
    doc.save(str(path))
    return pypdf.PdfReader(str(path))


def test_a_rule_is_placed_on_the_page_it_is_printed_on(tmp_path):
    reader = _pdf(tmp_path, {7: RULE})
    provs = [{"code": "C3", "text": RULE}]
    ai._place_on_pages(provs, reader, 1, 12)
    assert provs[0]["page"] == 7


def test_the_models_own_page_number_is_not_trusted(tmp_path):
    """The model counts from the start of the chunk it was sent: page 3 of chunk 13-24 is 15."""
    reader = _pdf(tmp_path, {15: RULE}, n=24)
    provs = [{"code": "C3", "text": RULE, "page": 3}]
    ai._place_on_pages(provs, reader, 13, 24)
    assert provs[0]["page"] == 15


def test_a_rule_that_cannot_be_placed_keeps_the_chunk_start(tmp_path):
    """Printed on two pages: no guess. The repair step then records it as unresolved."""
    reader = _pdf(tmp_path, {4: RULE, 9: RULE})
    provs = [{"code": "C3", "text": RULE}]
    ai._place_on_pages(provs, reader, 1, 12)
    assert provs[0]["page"] == 1


def test_a_page_outside_the_chunk_is_never_chosen(tmp_path):
    reader = _pdf(tmp_path, {20: RULE}, n=24)
    provs = [{"code": "C3", "text": RULE}]
    ai._place_on_pages(provs, reader, 1, 12)
    assert provs[0]["page"] == 1
