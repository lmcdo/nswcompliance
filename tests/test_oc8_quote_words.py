"""OC-8 goes red when a served number's sentence is not the council's words on its cited page.

prior-art-checked: new tests for scripts/oc8_quote_words.py; tests/test_outreach_claim_checks_ranges_and_citations.py
covers OC-8's citation-presence part, which a planted fake quote passes.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import oc8_quote_words as W  # noqa: E402
import outreach_claim_checks as occ  # noqa: E402

PAGE = "3.2.3 Side setbacks. The minimum side setback is 900mm for a single storey dwelling."
PAGES = ["Contents", PAGE]


def _entry(**kw):
    e = dict(value_min=0.9, value_max=None, semantic_type="side_setback", source_chapter_key="b3",
             pdf_page=2, source_text="The minimum side setback is 900mm for a single storey dwelling")
    e.update(kw)
    return e


def _run(monkeypatch, *entries, pages=PAGES):
    monkeypatch.setattr(occ, "served_entries", lambda: ([("woollahra", e, {}) for e in entries], ""))
    monkeypatch.setattr(W, "_registry_pages", lambda: (lambda lga, ck: pages))
    return W.check()


def test_the_councils_words_on_the_cited_page_pass(monkeypatch):
    status, msg = _run(monkeypatch, _entry())
    assert status == occ.PASS and "0 of 1" in msg


def test_a_planted_fake_quote_goes_red(monkeypatch):
    # Has a page, a sentence and (elsewhere) a link -- everything the old OC-8 checked.
    status, msg = _run(monkeypatch, _entry(source_text="Minimum side setback 0.9m (DCP 3.2.3)"))
    assert status == occ.FAIL and "not_found" in msg


def test_one_changed_number_goes_red(monkeypatch):
    status, _ = _run(monkeypatch, _entry(source_text="The minimum side setback is 1500mm for a single storey dwelling"))
    assert status == occ.FAIL


def test_the_right_words_on_the_wrong_page_go_red(monkeypatch):
    # Two pages away: a neighbouring page would count, because a sentence can run over a page break.
    status, msg = _run(monkeypatch, _entry(pdf_page=1), pages=["Contents", "Objectives", PAGE])
    assert status == occ.FAIL and "wrong_page" in msg


def test_an_unreadable_pdf_goes_red_not_green(monkeypatch):
    status, msg = _run(monkeypatch, _entry(), pages=None)
    assert status == occ.FAIL and "no_source" in msg


def test_a_note_with_no_number_is_not_counted(monkeypatch):
    status, msg = _run(monkeypatch, _entry(value_min=None, source_text="No maximum specified"))
    assert status == occ.PASS and "0 of 0" in msg


def test_a_serve_path_failure_is_unknown_not_pass(monkeypatch):
    monkeypatch.setattr(occ, "served_entries", lambda: (None, "serve path failed (boom)"))
    assert W.check()[0] == occ.UNKNOWN


def test_oc8_runs_the_word_check():
    names = [getattr(f, "__name__", "") for f in occ.CHECKS["OC-8"]] if hasattr(occ, "CHECKS") else []
    src = (ROOT / "scripts" / "outreach_claim_checks.py").read_text(encoding="utf-8")
    assert "oc8_quote_words" in src.split('"OC-8": [', 1)[1].split("],", 1)[0] or "oc8_quote_words" in names
