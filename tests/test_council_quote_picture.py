"""A rule printed inside a picture is proven only when the whole rule appears, in order, in one picture's OCR text
(council_quote_picture). Shapes from the Hornsby precinct plans and the 2026-10-14 cross-review scenarios.

prior-art-checked: new module; the OCR engine is injected so tests need no model.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import fitz  # noqa: E402
import council_quote_picture as cqp  # noqa: E402


def pdf(tmp_path, pages=2, picture_on=(1,), size=100, text=None):
    doc = fitz.open()
    for n in range(1, pages + 1):
        page = doc.new_page()
        if text:
            page.insert_text((50, 400), text)
        if n in picture_on:
            pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 20, 20), 0)
            pix.clear_with(200)
            page.insert_image(fitz.Rect(50, 50, 50 + size, 50 + size), pixmap=pix)
    path = tmp_path / "plan.pdf"
    doc.save(str(path))
    return str(path)


def ocr(*lines):
    return lambda png: [(None, t, 0.95) for t in lines]


def setup_function(_):
    cqp._cache.clear()


def test_a_rule_printed_in_order_in_the_picture_is_proven(tmp_path):
    out = cqp.prove("Promote access from Baldwin Avenue.", pdf(tmp_path), 1, ocr("Promote access from", "Baldwin Avenue."))
    assert out == {"quote": "Promote access from Baldwin Avenue.", "quote_page": 1}


def test_words_present_but_scattered_or_reordered_are_not_proven(tmp_path):
    """Cross-review: 'development must exceed 9 metres' + 'height not applicable' must not prove the stored rule."""
    out = cqp.prove("Development height must not exceed 9 metres", pdf(tmp_path), 1,
                    ocr("development must exceed 9 metres", "height not applicable"))
    assert out is None


def test_a_missing_short_word_such_as_no_is_not_proven(tmp_path):
    out = cqp.prove("No parking areas are permitted beside residential buildings", pdf(tmp_path), 1,
                    ocr("Parking areas are permitted beside residential buildings"))
    assert out is None


def test_a_different_comparison_symbol_is_not_proven(tmp_path):
    out = cqp.prove("The floor area must be < 50% of the site area", pdf(tmp_path), 1,
                    ocr("The floor area must be > 50% of the site area"))
    assert out is None


def test_a_number_not_in_the_picture_is_not_proven(tmp_path):
    out = cqp.prove("Rear setback of at least 9m applies", pdf(tmp_path), 1, ocr("Rear setback of at least 8m applies"))
    assert out is None


def test_a_page_with_only_a_small_logo_is_never_ocr_read(tmp_path):
    """Cross-review: ordinary text beside a logo must not be proven through the logo's page."""
    path = pdf(tmp_path, size=20, text="Promote access from Baldwin Avenue.")
    assert cqp.prove("Promote access from Baldwin Avenue.", path, 1, ocr("Promote access from Baldwin Avenue.")) is None


def test_a_page_without_a_picture_is_never_ocr_proven(tmp_path):
    path = pdf(tmp_path, pages=3, picture_on=())
    assert cqp.prove("Promote access from Baldwin Avenue.", path, 2, ocr("Promote access from Baldwin Avenue.")) is None


def test_too_few_words_prove_nothing(tmp_path):
    assert cqp.prove("Rear boundary", pdf(tmp_path), 1, ocr("Rear boundary")) is None


def test_the_picture_may_be_on_the_next_page(tmp_path):
    out = cqp.prove("Install traffic signals at the Galston Road intersection", pdf(tmp_path, pages=3, picture_on=(3,)), 2,
                    ocr("Install traffic signals at the", "Galston Road intersection"))
    assert out and out["quote_page"] == 3


def test_word_boundaries_and_slashes_count(tmp_path):
    """Cross-review: 'not in' must not match 'no tin'; '1/2' must not match '12'."""
    assert cqp.prove("Fences are not in front of the building", pdf(tmp_path), 1,
                     ocr("Fences are no tin front of the building")) is None
    cqp._cache.clear()
    assert cqp.prove("Limit the height to 1/2 of the wall length", pdf(tmp_path), 1,
                     ocr("Limit the height to 12 of the wall length")) is None
