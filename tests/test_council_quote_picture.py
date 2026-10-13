"""A rule printed inside a picture is proven only when every word and number is read there (council_quote_picture).

prior-art-checked: new module; the OCR engine is injected so tests need no model. Shapes from the Hornsby precinct
plans ("Promote access from Baldwin Avenue") and a setback diagram ("3 / 8m").
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import fitz  # noqa: E402
import council_quote_picture as cqp  # noqa: E402


def pdf_with_picture(tmp_path, pages=2, picture_on=(1,)):
    doc = fitz.open()
    for n in range(1, pages + 1):
        page = doc.new_page()
        if n in picture_on:
            pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 20, 20), 0)
            pix.clear_with(200)
            page.insert_image(fitz.Rect(50, 50, 150, 150), pixmap=pix)
    path = tmp_path / "plan.pdf"
    doc.save(str(path))
    return str(path)


def fake_ocr(lines):
    return lambda png: [(None, t, 0.95) for t in lines]


def setup_function(_):
    cqp._cache.clear()


def test_a_rule_whose_every_word_is_in_the_picture_is_proven(tmp_path):
    pdf = pdf_with_picture(tmp_path)
    ocr = fake_ocr(["Promote access from", "Baldwin Avenue", "Rear setback 8m"])
    out = cqp.prove("Promote access from Baldwin Avenue.", pdf, 1, ocr)
    assert out == {"quote": "Promote access from Baldwin Avenue.", "quote_page": 1}


def test_one_missing_word_leaves_it_unproven(tmp_path):
    pdf = pdf_with_picture(tmp_path)
    out = cqp.prove("Promote vehicle access from Baldwin Avenue.", pdf, 1, fake_ocr(["Promote access from Baldwin Avenue"]))
    assert out is None


def test_a_number_not_in_the_picture_leaves_it_unproven(tmp_path):
    pdf = pdf_with_picture(tmp_path)
    out = cqp.prove("Rear setback of at least 9m applies", pdf, 1, fake_ocr(["Rear setback of at least 8m applies"]))
    assert out is None


def test_a_page_without_a_picture_is_never_ocr_proven(tmp_path):
    pdf = pdf_with_picture(tmp_path, pages=3, picture_on=())
    assert cqp.prove("Promote access from Baldwin Avenue.", pdf, 2, fake_ocr(["Promote access from Baldwin Avenue"])) is None


def test_too_few_words_prove_nothing(tmp_path):
    pdf = pdf_with_picture(tmp_path)
    assert cqp.prove("Rear boundary", pdf, 1, fake_ocr(["Rear boundary"])) is None


def test_the_picture_may_be_on_the_next_page(tmp_path):
    pdf = pdf_with_picture(tmp_path, pages=3, picture_on=(3,))
    out = cqp.prove("Install traffic signals at the Galston Road intersection", pdf, 2,
                    fake_ocr(["Install traffic signals at the", "Galston Road intersection"]))
    assert out and out["quote_page"] == 3
