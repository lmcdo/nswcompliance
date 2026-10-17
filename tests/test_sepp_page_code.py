"""Page-code mode (DQ-145 group 4, user 2026-10-18): a row is decided only among the places of the code the address
page shows it under (its v2_part); several places must all print the same standard, and the row cites every one."""
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import apply_sepp_marker_blind as ap  # noqa: E402
import sepp_complete_unit as cu  # noqa: E402
import sepp_marker_blind as mb  # noqa: E402
import verify_sepp_marker_blind as ver  # noqa: E402

S = ("All off-street car parking spaces and vehicle access must comply with AS/NZS 2890.1:2004, Parking facilities, "
     "Part 1: Off-street car parking")
H = "Car parking and vehicle access requirements"
ONE = "At least 1 off-street car parking space must be provided on a lot unless the lot is narrower than 8m"

HTML = f"""<html><body>
<div class="frag-clause" id="sec.3.16"><h3>3.16 {H}</h3>
 <div class="frag-subclause" id="sec.3.16-ssec.1"><p>(1) {ONE}.</p></div>
 <div class="frag-subclause" id="sec.3.16-ssec.2"><p>(2) {S}.</p></div></div>
<div class="frag-clause" id="sec.3.23"><h3>3.23 Other development standards for detached garages and carports</h3>
 <div class="frag-subclause" id="sec.3.23-ssec.1"><p>(1) {H} {S}.</p></div>
 <div class="frag-subclause" id="sec.3.23-ssec.2"><p>(2) A carport must not be higher than 3m above ground level.</p></div></div>
<div class="frag-clause" id="sec.3B.18"><h3>3B.18 {H}</h3>
 <div class="frag-subclause" id="sec.3B.18-ssec.4"><p>(4) {S}.</p></div></div>
</body></html>"""


@pytest.fixture()
def snap(tmp_path):
    f = tmp_path / "epi-test_2026-10-18.html"
    f.write_text(HTML, encoding="utf8")
    return mb.Snapshot(f)


def test_standard_in_two_places_of_the_page_code_cites_both(snap):
    d = cu.decide_smallest_unit(f"(2) {S.replace('Off-street', 'Of -street')}.", snap, None, [("page_code", "sec.3")])
    assert d["verdict"] == "recopy" and d["reason"] == cu.MODE_PAGE
    assert d["unit"] == "sec.3.16-ssec.2" and d["places"] == ["sec.3.16-ssec.2", "sec.3.23-ssec.1"]
    assert d["new_ref"] == "Section 3.16(2); same words in 3.23(1)"
    assert "sec.3B.18-ssec.4" not in d["places"]   # never leaves the code the page shows


def test_places_that_do_not_print_the_same_standard_are_refused(snap):
    # heading + standard: printed together in 3.23(1) only; 3.16 holds the words apart -> no single standard
    d = cu.decide_smallest_unit(f"(1) {H} {S}.", snap, None, [("page_code", "sec.3")])
    assert d["verdict"] == "refuse" and d["reason"] == "ambiguous_unit"


def test_without_a_page_code_the_row_stays_ambiguous(snap):
    assert cu.decide_smallest_unit(f"(2) {S}.", snap)["reason"] == "ambiguous_unit"


def test_no_place_in_the_page_code_is_refused(snap):
    d = cu.decide_smallest_unit(f"(2) {S}.", snap, None, [("page_code", "sec.3D")])
    assert d["verdict"] == "refuse" and "sec.3D" in d["detail"]


def test_page_code_branch_reads_only_a_code_tag():
    assert cu.page_code_branch("3") == "sec.3" and cu.page_code_branch("3B") == "sec.3B"
    assert cu.page_code_branch(None) is None and cu.page_code_branch("Housing") is None


def _row_and_evidence(snap, v2_part, page_code):
    old = f"(2) {S.replace('Off-street', 'Of -street')}."   # the scan's typo, as rows 37145/37202 carry it
    d = cu.decide_smallest_unit(old, snap, None, [("page_code", page_code)])
    r = {"id": 1, "rule": "recopy", "ref_number": "provision_1", "old_text": old, "new_text": snap.units[d["unit"]].text,
         "new_ref_number": d["new_ref"], "old_ref_number": "provision_1", "v2_part": v2_part}
    e = {"rule": "recopy", "mode": d["reason"], "unit_id": d["unit"], "places": d["places"], "tiebreak": d["tiebreak"],
         "page_code": page_code, "ref_number": d["new_ref"], "new_ref_number": d["new_ref"],
         "old_ref_number": "provision_1", **{k: d[k] for k in ("n_words", "unit_words", "tokens_sha256", "matched_words",
                                                                 "coverage", "size_ratio", "new_sha256")}}
    return r, e


def test_verifier_re_derives_a_page_code_row(snap):
    r, e = _row_and_evidence(snap, "3", "sec.3")
    assert ver._verify_complete_unit(r, e, snap) == ""


def test_verifier_refuses_a_page_code_that_is_not_the_rows_code(snap):
    r, e = _row_and_evidence(snap, "3B", "sec.3")
    assert "v2_part" in ver._verify_complete_unit(r, e, snap)


def test_applier_refuses_when_v2_part_changed_since_the_plan():
    r = {"id": 7, "rule": "recopy", "ref_number": "p", "document_id": "d", "old_text": "x", "new_text": "y",
         "md5": ap.rcp.md5("x"), "v2_part": "3"}
    t = (7, ap.rcp.md5("x"), None, True, 0, "x", None, None, None, 1, None, None, None, "p", "d", None, "3B")
    assert any("v2_part changed" in b for b in ap.check([r], {7: t}))
    t_same = t[:16] + ("3",)
    assert not any("v2_part" in b for b in ap.check([r], {7: t_same}))
