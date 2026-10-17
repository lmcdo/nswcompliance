"""visible_text_repair: the PDF's invisible white copy of a line is dropped; real repeats stay (2026-10-17)."""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import visible_text_repair as vt  # noqa: E402

DARK = 2301728


def page(*lines):
    """A PyMuPDF get_text('dict')-shaped page: each line is a list of (text, colour) spans."""
    return {"blocks": [{"type": 0, "lines": [{"spans": [{"text": t, "color": c} for t, c in ln]} for ln in lines]}]}


def test_white_span_is_dropped_dark_kept():
    p = page([("land with an average width", vt.WHITE)], [("land with an average width", DARK)])
    assert vt._lines(p) == ["land with an average width"]


def test_collapse_keeps_the_copy_with_the_marker():
    t = "A dwelling house shall not be erected on\na)\t A dwelling house shall not be erected on\nland with an average width\nland with an average width"
    assert vt.collapse(t) == "a)\t A dwelling house shall not be erected on\nland with an average width"


def test_real_repeat_printed_twice_on_the_page_stays():
    t = "Butcher\n240L/100m2 of floor area/day\n240L/100m2 of floor area/day"
    assert vt.collapse(t, printed_twice=lambda w: True) == t


def test_refused_when_the_collapsed_text_is_not_on_the_visible_page():
    row = {"id": 1, "provision_text": "one two three four five six seven eight\none two three four five six seven eight",
           "pdf_page": 3, "page_range": None}
    vis = {3: {"raw": "something else entirely on this page", "sorted": "something else entirely on this page"}}
    d = vt.plan_row(row, vis)
    assert d["verdict"] == "refused"


def test_fix_when_the_collapsed_text_is_on_the_visible_page():
    words = "one two three four five six seven eight nine ten"
    row = {"id": 1, "provision_text": words + "\n" + words, "pdf_page": 3, "page_range": None}
    vis = {3: {"raw": "intro " + words + " outro", "sorted": "intro " + words + " outro"}}
    d = vt.plan_row(row, vis)
    assert d["verdict"] == "fix" and d["new_text"] == words and d["evidence"]["page"] == 3


def test_unreadable_rules_count_as_at_risk():
    assert vt.rules_lost('{"rules": [ broken', "any text") == 1
    assert vt.rules_lost(None, "any text") == 0
    assert vt.rules_lost([{"compliance_type": "numeric_check", "raw_match": "3m wide"}], "at least 3m wide") == 0
    assert vt.rules_lost([{"compliance_type": "numeric_check", "raw_match": "3 m wide"}], "at least 3m wide") == 1
