"""Page proof: each matcher must FAIL on a broken input, and the verifier on a tampered proof."""
import copy
import sys
from pathlib import Path

import pytest

fitz = pytest.importorskip("fitz")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import apply_page_evidence as ape  # noqa: E402
import page_evidence as pe  # noqa: E402
import verify_page_evidence as vpe  # noqa: E402


def make_pdf(path, pages):
    """pages: list of ('text', [lines]) or ('table', [[cell,...],...]) -> ruled/plain PDF."""
    doc = fitz.open()
    for kind, content in pages:
        page = doc.new_page()
        if kind == "text":
            y = 80
            for ln in content:
                page.insert_text((72, y), ln, fontsize=11)
                y += 16
        else:
            x0, y0, w, h = 72, 100, 120, 24
            for r, row in enumerate(content):
                for c, cell in enumerate(row):
                    rect = fitz.Rect(x0 + c * w, y0 + r * h, x0 + (c + 1) * w, y0 + (r + 1) * h)
                    page.draw_rect(rect, color=(0, 0, 0), width=1)
                    if cell:
                        page.insert_text((rect.x0 + 4, rect.y0 + 16), cell, fontsize=9)
        pass
    doc.save(str(path))
    doc.close()


def read(path):
    out = {}
    with fitz.open(str(path)) as doc:
        for n, p in enumerate(doc, 1):
            out[n] = (pe.page_texts(p), pe.prepare(pe.page_tables(p)))
    return out


def page_of(path, n):
    return fitz.open(str(path))[n - 1]


# -- normaliser --------------------------------------------------------------------

def test_normalise_folds_ligatures_units_bullets_hyphenation():
    assert pe.normalise("oﬃce area 20 m 2") == "office area 20m2"
    assert pe.normalise("• Setback 4 m") == "setback 4m"
    assert pe.normalise("devel-\nopment control") == "development control"
    assert pe.normalise("a­b") == "ab"


def test_normalise_does_not_invent_equivalence():
    assert pe.normalise("Arts & Crafts") != pe.normalise("Arts and Crafts")
    assert pe.normalise("4 storeys") != pe.normalise("5 storeys")


# -- text-run -----------------------------------------------------------------------

def test_text_run_proven_on_exactly_one_page(tmp_path):
    f = tmp_path / "a.pdf"
    make_pdf(f, [("text", ["Intro page about nothing."]),
                 ("text", ["The upper level setback must be 4m above street wall."])])
    v, ev, _ = pe.prove("upper level setback must be 4m above street wall", read(f))
    assert v == "proven" and ev["page"] == 2 and ev["matcher"] == "text-run"
    assert vpe.check_evidence(ev, page_of(f, 2)) == []


def test_text_run_one_changed_word_is_not_found(tmp_path):
    f = tmp_path / "a.pdf"
    make_pdf(f, [("text", ["The upper level setback must be 4m above street wall."])])
    v, ev, _ = pe.prove("upper level setback must be 5m above street wall", read(f))
    assert v == "not_found" and ev is None


def test_text_run_reordered_words_not_found(tmp_path):
    f = tmp_path / "a.pdf"
    make_pdf(f, [("text", ["upper level setback must be 4m above street wall"])])
    assert pe.prove("setback upper level must be 4m above street wall", read(f))[0] == "not_found"


def test_text_run_on_two_pages_is_unresolved(tmp_path):
    f = tmp_path / "a.pdf"
    line = "The upper level setback must be 4m above street wall."
    make_pdf(f, [("text", [line]), ("text", [line])])
    v, ev, info = pe.prove("upper level setback must be 4m above street wall", read(f))
    assert v == "unresolved" and ev is None and info["pages"] == [1, 2]


def test_partial_word_is_not_a_match(tmp_path):
    f = tmp_path / "a.pdf"
    make_pdf(f, [("text", ["the upper level setbacks apply here"])])
    assert pe.prove("upper level setback apply here", read(f))[0] == "not_found"


def test_span_ending_mid_word_is_not_a_match(tmp_path):
    f = tmp_path / "a.pdf"
    make_pdf(f, [("text", ["the upper level setbacks apply here"])])
    assert pe.prove("the upper level setback", read(f))[0] == "not_found"
    assert pe.prove("he upper level setbacks", read(f))[0] == "not_found"


def test_too_short(tmp_path):
    f = tmp_path / "a.pdf"
    make_pdf(f, [("text", ["See above."])])
    assert pe.prove("see above", read(f))[0] == "too_short"


# -- table-cells ---------------------------------------------------------------------

TABLE = [["Street", "Side", "Style"],
         ["Croydon Road", "S", "Queen Anne"],
         ["Croydon Road", "S", "California Bungalow"],
         ["Alt Street", "N", "Queen Anne"]]


def _table_hits(f, words):
    texts, streams = read(f)[1]
    return [m for m in pe.match_page(words, texts, streams) if m["matcher"] == "table-cells"]


def test_table_column_proven_cell_by_cell(tmp_path):
    f = tmp_path / "t.pdf"
    make_pdf(f, [("text", ["Heritage"]), ("table", TABLE)])
    v, ev, _ = pe.prove("queen anne california bungalow queen anne", read(f))
    assert v == "proven" and ev["matcher"] == "table-cells" and ev["reading"] == "col"
    assert ev["cells"] == [[1, 2], [2, 2], [3, 2]]
    assert vpe.check_evidence(ev, page_of(f, 2)) == []


def test_table_row_and_header_plus_row(tmp_path):
    f = tmp_path / "t.pdf"
    make_pdf(f, [("table", TABLE)])
    texts, streams = read(f)[1]
    ms = [m for m in pe.match_page("croydon road s california bungalow", texts, streams)
          if m["matcher"] == "table-cells"]
    assert ms and ms[0]["reading"] == "row" and ms[0]["cells"] == [[2, 0], [2, 1], [2, 2]]
    h = _table_hits(f, "style alt street n")   # header cell + ONE data row's cells
    assert h and h[0]["reading"] == "header+row" and h[0]["cells"] == [[0, 2], [3, 0], [3, 1]]
    assert not _table_hits(f, "style croydon road alt street")   # header + cells of TWO rows


def test_table_wrong_cell_order_not_found(tmp_path):
    f = tmp_path / "t.pdf"
    make_pdf(f, [("table", TABLE)])
    assert pe.prove("california bungalow queen anne queen anne", read(f))[0] == "not_found"


def test_table_cells_of_different_rows_do_not_join_as_a_row(tmp_path):
    f = tmp_path / "t.pdf"
    make_pdf(f, [("table", TABLE)])
    # last cell of row 1 + first cell of row 2 are adjacent in reading order but in no row/col
    assert not _table_hits(f, "queen anne croydon road s")


def test_merged_cell_is_never_used():
    grid = [["a b c", None], ["d e f", "g h i"]]
    kinds = {k: c for k, c in pe.table_streams(grid)}
    assert (0, 1) not in kinds["row"] and (0, 1) not in kinds["col"]


# -- verifier catches tampering ------------------------------------------------------

@pytest.fixture
def proven(tmp_path):
    f = tmp_path / "t.pdf"
    make_pdf(f, [("text", ["The upper level setback must be 4m above street wall."]), ("table", TABLE)])
    pages = read(f)
    return f, pe.prove("upper level setback must be 4m above street wall", pages)[1], \
        pe.prove("queen anne california bungalow queen anne", pages)[1]


def test_verifier_rejects_tampered_text_evidence(proven):
    f, ev, _ = proven
    assert vpe.check_evidence(ev, page_of(f, ev["page"])) == []
    for key, val in (("start", ev["start"] + 1), ("end", ev["end"] - 1), ("order", "bogus"),
                     ("span", ev["span"].replace("4m", "5m")), ("span_sha256", "0" * 64)):
        t = copy.deepcopy(ev)
        t[key] = val
        assert vpe.check_evidence(t, page_of(f, ev["page"])), key
    assert vpe.check_evidence(ev, page_of(f, 2))      # wrong page holds no such span


def test_verifier_rejects_tampered_table_evidence(proven):
    f, _, ev = proven
    pg = page_of(f, ev["page"])
    assert vpe.check_evidence(ev, pg) == []
    for key, val in (("table", 7), ("cells", [[-1, 2], [3, 2]]), ("cells", [[3, 2], [2, 2], [1, 2]]),
                     ("cells", [[1, 2], [1, 2], [2, 2]]), ("cells", [[1, 2], [3, 2]]), ("cells", [[1, 2], [2, 2], [3, 1]]),
                     ("cells", [[0, 0], [9, 9]]), ("reading", "row"), ("start", 1)):
        t = copy.deepcopy(ev)
        t[key] = val
        assert vpe.check_evidence(t, pg), (key, val)


# -- apply gate ------------------------------------------------------------------------

def test_apply_preflight_refuses_changed_text_and_taken_rows():
    rec = {"id": 1, "provision_text_md5": "aaa", "pdf_path": "p.pdf", "plan": {"id": 1}}
    ok = {"md5": "aaa", "page_check": "not_found", "r2_current_path": "p.pdf"}
    assert ape.preflight([rec], {1: ok}) == []
    assert ape.preflight([rec], {1: {**ok, "md5": "bbb"}})
    assert ape.preflight([rec], {1: {**ok, "page_check": "on_page"}})
    assert ape.preflight([rec], {1: {**ok, "r2_current_path": "q.pdf"}})
    assert ape.preflight([rec], {})
    assert ape.preflight([{**rec, "plan": {"id": 2}}], {1: ok})     # plan would write another row


# -- span on several pages: proven only where the row's stored page is one of them -------

LINE = "The upper level setback must be 4m above the street wall height."
WORDS = "upper level setback must be 4m above the street wall height"
OLD = {"pdf_page": 3, "page_range": [3]}


def _three_pages(tmp_path):
    f = tmp_path / "m.pdf"
    make_pdf(f, [("text", [LINE]), ("text", ["Other text only."]), ("text", [LINE])])
    return f, read(f)


def test_several_pages_stored_page_among_them_is_on_page(tmp_path):
    _f, pages = _three_pages(tmp_path)
    v, ev, info = pe.prove(WORDS, pages, {3})
    assert v == "proven" and ev["page"] == 3 and ev["all_pages"] == [1, 3]
    assert ev["matcher_version"] == pe.MATCHER_VERSION and info["pages"] == [1, 3]
    v, ev, _ = pe.prove(WORDS, pages, {2, 1})            # a page_range member counts too
    assert v == "proven" and ev["page"] == 1 and ev["all_pages"] == [1, 3]


def test_several_pages_stored_page_not_among_them_is_unresolved(tmp_path):
    _f, pages = _three_pages(tmp_path)
    for held in ({2}, set(), None):
        v, ev, info = pe.prove(WORDS, pages, held)
        assert v == "unresolved" and ev is None and info["pages"] == [1, 3]


def test_several_held_pages_prefer_primary_and_never_pick_a_range_member(tmp_path):
    _f, pages = _three_pages(tmp_path)
    v, ev, _ = pe.prove(WORDS, pages, {1, 3}, 3)
    assert v == "proven" and ev["page"] == 3                 # primary kept, not min()
    assert pe.prove(WORDS, pages, {1, 3}, 2)[0] == "unresolved"   # two range members, no primary


def test_verifier_accepts_honest_all_pages_and_rejects_tampered(tmp_path):
    _f, pages = _three_pages(tmp_path)
    ev = pe.prove(WORDS, pages, {3})[1]
    assert vpe.check_uniqueness(ev, OLD, "on_page", pages) == []
    for tamper in ({"all_pages": [3]}, {"all_pages": [1, 2, 3]}, {"all_pages": [1, 3, 4]}):
        assert vpe.check_uniqueness({**ev, **tamper}, OLD, "on_page", pages), tamper
    # stored page not among all_pages (row points at page 2)
    assert vpe.check_uniqueness(ev, {"pdf_page": 2, "page_range": [2]}, "on_page", pages)
    # an ambiguous span can never be a 'moved'
    assert vpe.check_uniqueness(ev, OLD, "moved", pages)


def test_verifier_accepts_single_page_move_with_all_pages(tmp_path):
    f = tmp_path / "s.pdf"
    make_pdf(f, [("text", ["Intro."]), ("text", [LINE])])
    pages = read(f)
    ev = pe.prove(WORDS, pages, {1})[1]
    assert ev["page"] == 2 and ev["all_pages"] == [2]
    assert vpe.check_uniqueness(ev, {"pdf_page": 1, "page_range": [1]}, "moved", pages) == []
    assert vpe.check_uniqueness({**ev, "page": 1}, {"pdf_page": 1, "page_range": [1]}, "moved", pages)


def test_verifier_still_checks_old_evidence_without_all_pages(tmp_path):
    _f, pages = _three_pages(tmp_path)
    ev = pe.prove(WORDS, pages, {3})[1]
    del ev["all_pages"]
    assert vpe.check_uniqueness(ev, OLD, "on_page", pages)   # old rule: two pages -> fail


def test_shared_page_label_or_repeated_cells_stay_unresolved(tmp_path):
    """A label or a run of repeated table cells on several pages proves nothing, even on the held page."""
    f = tmp_path / "l.pdf"
    label = "3 2 3 height"
    cells = "queen anne bungalow queen anne bungalow queen anne bungalow queen anne"
    make_pdf(f, [("text", [label, cells]), ("text", ["Other."]), ("text", [label, cells])])
    pages = read(f)
    for words in (label, cells):
        v, ev, info = pe.prove(words, pages, {3}, 3)
        assert v == "unresolved" and ev is None and info["pages"] == [1, 3], words


# -- DQ-145 step 3: the page that holds both the words and the row's own section number --------------
def _key_sites(tmp_path):
    f = tmp_path / "k.pdf"
    make_pdf(f, [("text", ["6.4 KS4 Compass Centre", LINE]), ("text", ["6.5 KS5 Sports Club", LINE]),
                 ("text", ["Intro to 6.4 and 6.5", "no rule here"])])
    return read(f)


def test_row_heading_is_the_dotted_section_number():
    assert pe.row_heading("# 6.4 e) Design principle\n\nWords") == "6 4"
    assert pe.row_heading("# 10.2 (v) For any\n\nWords") == "10 2"
    assert pe.row_heading("# Part 6\n\nWords") is None and pe.row_heading("No heading") is None
    assert pe.row_heading("# 6.45 x\n\nW") == "6 45"   # never a prefix of a longer number


def test_heading_picks_the_one_page_with_words_and_heading(tmp_path):
    pages = _key_sites(tmp_path)
    v, ev, _ = pe.prove(WORDS, pages, {9}, 9, "6 5")
    assert v == "proven" and ev["page"] == 2 and ev["by_heading"] == "6 5" and ev["all_pages"] == [1, 2]
    assert vpe.check_uniqueness(ev, {"pdf_page": 9, "page_range": [9]}, "moved", pages) == []
    # a tampered heading re-derives to another page (or none) and fails
    assert vpe.check_uniqueness({**ev, "by_heading": "6 4"}, {"pdf_page": 9, "page_range": [9]}, "moved", pages)


def test_heading_absent_or_on_several_word_pages_stays_unresolved(tmp_path):
    pages = _key_sites(tmp_path)
    assert pe.prove(WORDS, pages, {9}, 9, "7 1")[0] == "unresolved"      # heading on no word page
    assert pe.prove(WORDS, pages, {9}, 9, None)[0] == "unresolved"       # no heading: unchanged
    assert "by_heading" not in pe.prove(WORDS, pages, {1}, 1, "6 5")[1]  # a held page still wins first


def test_heading_on_two_word_pages_stays_unresolved(tmp_path):
    f = tmp_path / "k2.pdf"
    make_pdf(f, [("text", ["6.4 KS4 Compass Centre", LINE]), ("text", ["6.4 KS4 continued", LINE])])
    assert pe.prove(WORDS, read(f), {9}, 9, "6 4")[0] == "unresolved"
