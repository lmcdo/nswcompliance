"""Page-proof fallbacks (DQ-145, user 2026-10-18): each must FAIL on a broken input, and the verifier on a tampered proof."""
import copy
import sys
from pathlib import Path

import pytest

fitz = pytest.importorskip("fitz")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import page_evidence as pe  # noqa: E402
import verify_page_evidence as vpe  # noqa: E402
from test_page_evidence import make_pdf, page_of, read  # noqa: E402

# a table that prints a rule's words out of order, with its label above it
TABLE = [["Setback", "Town houses", "Flats"], ["Front", "6m", "10m"], ["Side", "1.5m", "3m"]]
TABLE_ROW = "# 3.2.3\n\nTable 3.2.4-a: Minimum Setbacks\nSetback Town houses Front 6m Side 1.5m Flats 10m 3m"


def _table_pdf(f, label="Table 3.2.4-a: Minimum Setbacks", other=("text", ["Unrelated page about stormwater."])):
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((72, 70), label, fontsize=11)
    x0, y0, w, h = 72, 100, 120, 24
    for r, row in enumerate(TABLE):
        for c, cell in enumerate(row):
            rect = fitz.Rect(x0 + c * w, y0 + r * h, x0 + (c + 1) * w, y0 + (r + 1) * h)
            p.draw_rect(rect, color=(0, 0, 0), width=1)
            p.insert_text((rect.x0 + 4, rect.y0 + 16), cell, fontsize=9)
    doc.save(str(f))
    doc.close()
    if other:
        tmp = f.with_suffix(".2.pdf")
        make_pdf(tmp, [other])
        a, b = fitz.open(str(f)), fitz.open(str(tmp))
        b.insert_pdf(a)
        b.save(str(f.with_suffix(".x.pdf")))
        return f.with_suffix(".x.pdf")
    return f


def test_row_labels_reads_table_figure_and_control_codes():
    assert pe.row_labels(TABLE_ROW) == ["table 3 2 4 a"]
    assert pe.row_labels("# 8.1 e Vehicle access\nC.48 Driveways should be: e) Separated") == ["c 48"]
    assert pe.row_labels("# 4.8 Figure 57. Design guidance\n1 Sun and wind") == ["figure 57"]
    assert pe.row_labels("# 9.8.2 Desired future character\nThe desired character is to facilitate renewal") == []


def test_every_word_and_label_proves_a_jumbled_table(tmp_path):
    f = _table_pdf(tmp_path / "t.pdf")
    v, ev, info = pe.prove_fallback(TABLE_ROW, read(f), held={1}, primary=1)
    assert v == "proven" and ev["matcher"] == "all-words+label" and ev["page"] == 2
    assert ev["labels"] == ["table 3 2 4 a"]
    assert vpe.check_evidence(ev, page_of(f, 2)) == []


def test_every_word_without_the_label_is_not_proven(tmp_path):
    # the label sits only in our heading line; the page prints every body word but not the label
    row = "# 3.2.3 Table 3.2.4-a\n\nSetback Town houses Front 6m Side 1.5m Flats 10m 3m"
    f = _table_pdf(tmp_path / "t.pdf", label="Minimum Setbacks")
    assert pe.row_labels(row) == ["table 3 2 4 a"]
    assert pe.prove_fallback(row, read(f))[0] == "not_found"
    g = _table_pdf(tmp_path / "u.pdf")                       # same page with the label printed: proven
    assert pe.prove_fallback(row, read(g))[0] == "proven"


def test_a_missing_word_is_not_proven(tmp_path):
    f = _table_pdf(tmp_path / "t.pdf")
    assert pe.prove_fallback(TABLE_ROW.replace("1.5m", "2.5m"), read(f))[0] == "not_found"


def test_a_row_with_no_label_is_never_proven_by_words_alone(tmp_path):
    f = tmp_path / "a.pdf"
    make_pdf(f, [("text", ["renewal to facilitate the desired character is the future area of locations appropriate"])])
    row = "# 9.8.2\n\nthe desired future character of the area is to facilitate renewal in appropriate locations"
    assert pe.prove_fallback(row, read(f))[0] == "not_found"


def test_full_text_proves_a_rule_the_extractor_put_in_the_heading_line(tmp_path):
    f = tmp_path / "a.pdf"
    make_pdf(f, [("text", ["Intro."]),
                 ("text", ["O1 To maintain the supply of affordable accommodation for people on very low income"])])
    row = "# preamble O1 To Maintain The Supply Of Affordable Accommodation For People On Very\n\nlow income"
    assert pe.prove(pe.rule_words(row), read(f))[0] == "too_short"
    v, ev, _ = pe.prove_fallback(row, read(f))
    assert v == "proven" and ev["fallback"] == "full_text" and ev["page"] == 2 and ev["dropped_head_words"] == 1
    assert vpe.check_evidence(ev, page_of(f, 2)) == []


def test_full_text_never_drops_body_words(tmp_path):
    f = tmp_path / "a.pdf"
    make_pdf(f, [("text", ["minimum lot width must be twelve metres at the building line"])])
    row = "# 4.1 Lot width\n\nThe minimum lot width must be twelve metres at the building line"   # body adds 'The'
    v, _, _ = pe.prove_fallback(row, read(f))
    assert v == "not_found"


def test_verifier_rejects_a_tampered_label(tmp_path):
    f = _table_pdf(tmp_path / "t.pdf")
    v, ev, _ = pe.prove_fallback(TABLE_ROW, read(f))
    bad = copy.deepcopy(ev)
    bad["labels"] = ["table 9 9"]
    assert vpe.check_evidence(bad, page_of(f, 2))


def test_verifier_uniqueness_re_derives_the_pages(tmp_path):
    f = _table_pdf(tmp_path / "t.pdf")
    pages = read(f)
    v, ev, _ = pe.prove_fallback(TABLE_ROW, pages)
    assert vpe.check_uniqueness(ev, {"pdf_page": 2, "page_range": []}, "on_page", pages) == []
    moved = copy.deepcopy(ev)
    moved["all_pages"] = [1, 2]
    assert vpe.check_uniqueness(moved, {"pdf_page": 2, "page_range": []}, "on_page", pages)


def test_verifier_rejects_a_changed_number(tmp_path):
    f = _table_pdf(tmp_path / "t.pdf")
    v, ev, _ = pe.prove_fallback(TABLE_ROW, read(f))
    bad = copy.deepcopy(ev)
    bad["span"] = ev["span"].replace("1 5m", "2 5m")
    bad["end"] = len(bad["span"])
    assert any("whole number" in b or "span_sha256" in b for b in vpe.check_evidence(bad, page_of(f, 2)))


def test_a_word_needed_twice_must_be_printed_twice(tmp_path):
    # cross-review 2026-10-18 (Sol, HIGH): a set of words lost multiplicity
    f = tmp_path / "a.pdf"
    make_pdf(f, [("text", ["Table 4.1 C9 front setback 6m rear setback side boundary garage door width"])])
    once = "# 4.1 Setbacks\n\nC9 front setback 6m rear setback side boundary garage door width"
    twice = "# 4.1 Setbacks\n\nC9 front setback 6m rear setback side boundary garage door width door"   # 'door' twice
    assert pe.prove_fallback(once, read(f))[0] == "proven"
    assert pe.prove_fallback(twice, read(f))[0] == "not_found"


def test_verifier_re_makes_the_page_choice(tmp_path):
    # cross-review 2026-10-18 (Sol, MEDIUM): with two matching pages the stored page wins, never another held one
    f = tmp_path / "a.pdf"
    line = "C9 front setback 6m rear setback side boundary garage door width"
    jumbled = "Table 4.1 width door garage boundary side setback rear 6m setback front C9"   # every word, no span: bag rule only
    make_pdf(f, [("text", [jumbled]), ("text", [jumbled])])
    pages = read(f)
    row = "# 4.1 Table 4.1 Setbacks\n\n" + line
    v, ev, _ = pe.prove_fallback(row, pages, held={1, 2}, primary=1)
    assert v == "proven" and ev["page"] == 1 and ev["matcher"] == "all-words+label"
    assert vpe.check_uniqueness(ev, {"pdf_page": 1, "page_range": [1, 2]}, "on_page", pages) == []
    stale = copy.deepcopy(ev)
    stale["page"] = 2
    assert vpe.check_uniqueness(stale, {"pdf_page": 1, "page_range": [1, 2]}, "on_page", pages)


def test_swapped_values_are_not_proven(tmp_path):
    # cross-review 2026-10-18 (Sol, HIGH): same words and counts, values swapped between fields
    f = tmp_path / "a.pdf"
    make_pdf(f, [("text", ["Table 4.1 C9 front setback 3m side setback 6m garage door width rear boundary"])])
    right = "# 4.1 Table 4.1 Setbacks\n\nC9 rear boundary garage door width front setback 3m side setback 6m"
    swapped = "# 4.1 Table 4.1 Setbacks\n\nC9 rear boundary garage door width front setback 6m side setback 3m"
    assert pe.prove_fallback(right, read(f))[0] == "proven"
    assert pe.prove_fallback(swapped, read(f))[0] == "not_found"


def test_full_text_never_drops_a_word_that_changes_the_rule(tmp_path):
    # cross-review 2026-10-18 (Sol, HIGH): dropping 'must not' from the heading line would prove the opposite rule
    f = tmp_path / "a.pdf"
    make_pdf(f, [("text", ["be parked within the front setback at any time during construction"])])
    row = "# Vehicles must not\n\nbe parked within the front setback at any time during construction"
    assert pe.prove_fallback(row, read(f))[0] != "proven"


def test_verifier_rejects_a_matcher_fallback_mismatch(tmp_path):
    # cross-review 2026-10-18 (Sol, MEDIUM)
    f = _table_pdf(tmp_path / "t.pdf")
    v, ev, _ = pe.prove_fallback(TABLE_ROW, read(f))
    bad = copy.deepcopy(ev)
    bad["fallback"] = "full_text"
    assert any("does not go with" in b for b in vpe.check_evidence(bad, page_of(f, 2)))


def test_prose_cannot_use_the_every_word_rule(tmp_path):
    # user 2026-10-18: every-word proofs only for tables and figures; prose proves by exact words
    f = tmp_path / "a.pdf"
    make_pdf(f, [("text", ["width door garage boundary side setback rear 6m setback front C9"])])
    row = "# 4.1 Setbacks\n\nC9 front setback 6m rear setback side boundary garage door width"
    assert pe.prove_fallback(row, read(f))[0] == "not_found"
