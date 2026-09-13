"""Page-range extraction must not emit empty rules, and must not lose a rule to a
repeated section number.

Measured on waverley 2026-09-13 once its parts came from the page headers:
  * 29 "Controls" sections had no text -- the controls sat in the next numbered
    sub-section. They would have been served as empty rules.
  * 3 section numbers appeared twice with different text. diff_provisions keys
    sections by ref_number in a dict, so the second overwrote the first and a rule
    vanished without a trace.

The text fragments below are copied from that extraction.
"""
import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
    os.environ.setdefault(_k, "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
_STUBS = ("boto3", "botocore", "pdfplumber", "psycopg2", "dotenv", "enrichment", "enrichment.pipeline")
_saved = {k: sys.modules.get(k) for k in _STUBS}
for _k in _STUBS:
    sys.modules[_k] = MagicMock()
try:
    from dcp_extract_changed import DCPExtractor, build_ref_number  # noqa: E402
finally:
    for _k, _v in _saved.items():
        if _v is None:
            sys.modules.pop(_k, None)
        else:
            sys.modules[_k] = _v

finalise = DCPExtractor.finalise_ranged_sections


def sec(number, content, tables=None):
    return {"section_number": number, "section_title": "t", "content": content,
            "tables": tables or [], "page_start": 167, "page_end": 198, "pages": [167]}


def test_a_heading_only_shell_is_dropped_and_its_sibling_kept():
    out = finalise([
        sec("C1_1_8_objectives", "(a) To provide convenient and accessible parking."),
        sec("C1_1_8_controls", ""),
        sec("C1_1_8_1_8_1", "(a) Approval for on-site parking will only be granted where..."),
    ])
    assert [s["section_number"] for s in out] == ["C1_1_8_objectives", "C1_1_8_1_8_1"]


def test_a_section_with_no_text_but_a_table_is_kept():
    table = [{"html": "<table><tr><td>1 space per dwelling</td></tr></table>", "page": 60}]
    out = finalise([sec("B7_7_2_2_controls", "", tables=table)])
    assert len(out) == 1


def test_a_short_real_rule_is_not_mistaken_for_a_shell():
    out = finalise([sec("B13", "B13 Excavation B13 EXCAVATION")])
    assert len(out) == 1


def test_different_text_under_one_number_keeps_both():
    out = finalise([
        sec("B14_14_1_14_1_1", "(a) Signage is to relate to the use of the building on which it appears"),
        sec("B14_14_1_14_1_1", "(a) Advertising on garbage bins, telegraph posts and other surfaces"),
        sec("B14_14_1_14_1_1", "(a) A third distinct block under the same number"),
    ])
    assert [s["section_number"] for s in out] == [
        "B14_14_1_14_1_1", "B14_14_1_14_1_1_2", "B14_14_1_14_1_1_3"]
    assert out[1]["content"].startswith("(a) Advertising")


def test_an_exact_repeat_is_kept_once():
    out = finalise([sec("F4_4_6_controls", "(a) same"), sec("F4_4_6_controls", "(a) same")])
    assert len(out) == 1


def test_no_rule_is_lost_in_the_diff_map():
    """The failure itself: the ref_number dict must hold every section that survives."""
    raw = [
        sec("F4_4_6_controls", "(a) A development application for a place of public worship"),
        sec("F4_4_6_controls", "(a) The horticulture operation must be conducted in a controlled manner"),
    ]
    assert len({build_ref_number("doc", s["section_number"]) for s in raw}) == 1   # the bug
    out = finalise(raw)
    assert len({build_ref_number("doc", s["section_number"]) for s in out}) == len(out) == 2


def test_two_table_only_sections_with_different_tables_are_both_kept():
    """Cross-review: identity by text alone treats two empty-text sections as repeats
    and drops the second table -- a different parking rate table, silently gone."""
    first = [{"html": "<table><tr><td>1 space per dwelling</td></tr></table>", "page": 60}]
    second = [{"html": "<table><tr><td>1 space per 40 square metres</td></tr></table>", "page": 61}]
    out = finalise([sec("B7_7_2_2_controls", "", tables=first),
                    sec("B7_7_2_2_controls", "", tables=second)])
    assert len(out) == 2
    assert out[1]["tables"] == second


def test_a_suffix_never_collides_with_a_genuine_section_number():
    """Cross-review: renaming the second "A" to "A_2" would collide with a real "A_2"
    and the diff map would overwrite one of them."""
    out = finalise([sec("A", "first"), sec("A", "second"), sec("A_2", "a genuine A_2")])
    numbers = [s["section_number"] for s in out]
    assert len(set(numbers)) == 3
    assert out[2]["section_number"] == "A_2" and out[2]["content"] == "a genuine A_2"
    assert out[1]["section_number"] == "A_3"


def test_clean_input_is_returned_unchanged():
    clean = [sec("B1_1_1", "(a) one"), sec("B1_1_2", "(a) two")]
    assert finalise(clean) == clean
