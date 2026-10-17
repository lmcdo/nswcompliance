"""sepp_ref_fix: label grammar, label-blind unit search, label must name exactly the decided unit, verifier, ref forms."""
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import sepp_marker_blind as mb  # noqa: E402
import sepp_ref_fix as rf  # noqa: E402
import verify_sepp_marker_blind as ver  # noqa: E402

A = "the occupier of the land must keep the access path clear of obstructions at all times"
B = "a retaining wall on the land must not exceed a height of 1 metre above ground level"
C = "water tanks installed under this code must be screened from the street frontage entirely"
G = "the gate must open outwards and be fitted with a self closing latch at all times"
H = "the following requirements apply to every pool fence installed under this code"
G2 = "the hatch must close inwards and be fitted with a spring loaded bolt whenever unattended"
N = "this note explains how a council may inspect the pool fence before the certificate issues"
EPI = "epi-test"

HTML = f"""<html><body>
<div class="frag-clause" id="sec.5"><h3>5 Access</h3>
 <div class="frag-subclause" id="sec.5-ssec.1"><p>(1) {A}</p></div>
 <div class="frag-subclause" id="sec.5-ssec.2"><p>(2) {B}.</p></div></div>
<div class="frag-clause" id="sch.1-sec.2"><h3>2 Tanks</h3><p>{C}.</p></div>
<div class="frag-clause" id="sch.2-sec.2"><h3>2 Tanks</h3><p>{C}.</p></div>
<div class="frag-clause" id="sec.12"><h3>12 Gates</h3>
 <div class="frag-subclause" id="sec.12-ssec.1"><p>(1) {H}:</p>
  <div class="frag-li" id="sec.12-ssec.1-para1.a"><p>(a) {G};</p></div></div></div>
<div class="frag-clause" id="sch.3-sec.141R"><h3>141R Pools</h3>
 <div class="frag-subclause" id="sch.3-sec.141R-ssec.1"><p>(1) {H}:</p>
  <div class="frag-li" id="sch.3-sec.141R-ssec.1-para1.c"><p>(c) {G2};</p></div></div></div>
<div class="frag-note" id="sch.3-note"><p>{N}</p></div>
</body></html>"""


@pytest.fixture()
def snap(tmp_path):
    f = tmp_path / f"{EPI}_2026-10-16.html"
    f.write_text(HTML, encoding="utf8")
    return mb.Snapshot(f)


# ------------------------------------------------------------------------------------------ label grammar
@pytest.mark.parametrize("uid,label", [
    ("sec.158", "Section 158"),
    ("sec.5A.20", "Section 5A.20"),
    ("sec.3.4-ssec.2", "Section 3.4(2)"),
    ("sec.3.4-ssec.2-para1.e", "Section 3.4(2)(e)"),
    ("sec.5A.20-para1.a", "Section 5A.20(a)"),
    ("sec.86-ssec.2-para1.d-para2.iv", "Section 86(2)(d)(iv)"),
    ("sec.86-ssec.2-para1.d-para2.iv-para3.B", "Section 86(2)(d)(iv)(B)"),
    ("sch.11-sec.4", "Schedule 11, section 4"),
    ("sch.2A-sec.141R-ssec.1-para1.c", "Schedule 2A, section 141R(1)(c)"),
])
def test_label_grammar(uid, label):
    assert rf.unit_label(uid) == label
    assert rf.state_clause_label(label) == label            # passes the site's display check
    assert mb.ref_full(label)[0] == uid                     # and names exactly this unit


@pytest.mark.parametrize("uid", ["sch.10-note", "sch.6", "sec.5-tbl", "pt.1-tbl", "sec.5-oc.3", "sec.5-para2.i",
                                 "sec.5-ssec.1-para1.a-para3.A", "", None, "sec.", "sch.1-sec.2-extra"])
def test_non_clause_units_have_no_label(uid):
    assert rf.unit_label(uid) is None


def test_display_check_rejects_internal_ids():
    for bad in ("provision_2344", "Earthworks", "Part 1, Division 2, Clause four", "2344", None):
        assert rf.state_clause_label(bad) is None


# ----------------------------------------------------------------------------------- ref_unit / ref_full forms
def test_schedule_section_form():
    assert mb.ref_unit("Schedule 2A, section 141R(1)(c)") == "sch.2A-sec.141R-ssec.1"
    assert mb.ref_full("Schedule 2A, section 141R(1)(c)") == ("sch.2A-sec.141R-ssec.1-para1.c", True)
    assert mb.ref_full("Schedule 11, section 4") == ("sch.11-sec.4", False)
    assert mb.ref_unit("Schedule 11, section 4") == "sch.11-sec.4"
    assert mb.ref_unit("Schedule 3 cl 6(2)") == "sch.3-sec.6-ssec.2"


def test_existing_ref_forms_parse_as_before():
    assert mb.ref_unit("Schedule 2") == "sch.2" and mb.ref_full("Schedule 2") == (None, False)
    assert mb.ref_unit("Schedule 1 Part 2") == "sch.1"
    assert mb.ref_unit("Clause 3C.24") == "sec.3C.24"
    assert mb.ref_unit("Section 86(2)") == "sec.86-ssec.2"
    assert mb.ref_full("Section 107(2)(d)") == ("sec.107-ssec.2-para1.d", True)
    assert mb.ref_full("Clause 5A.20(a)") == ("sec.5A.20-para1.a", True)
    assert mb.ref_full("Section 5(1) (Access)") == ("sec.5-ssec.1", False)
    assert mb.ref_unit("Earthworks") is None and mb.ref_full("provision_9") == (None, False)


# --------------------------------------------------------------------------------------------- the search
def test_wrong_label_is_replaced_by_the_unit_found(snap):
    d = rf.fix_row(A, snap)
    assert d["verdict"] == "accept" and d["unit"] == "sec.5-ssec.1" and d["new_ref"] == "Section 5(1)"
    assert mb.ref_full(d["new_ref"])[0] == d["unit"]


def test_label_names_exactly_the_decided_unit_in_a_schedule(snap):
    d = rf.fix_row(G2, snap)
    assert d["verdict"] == "accept" and d["unit"] == "sch.3-sec.141R-ssec.1-para1.c"
    assert d["new_ref"] == "Schedule 3, section 141R(1)(c)" and mb.ref_full(d["new_ref"])[0] == d["unit"]


def test_same_words_in_two_schedules_is_ambiguous(snap):
    d = rf.fix_row(C, snap)
    assert d["verdict"] == "refuse" and d["reason"] == "ambiguous_unit"
    assert set(d["candidates"]) == {"sch.1-sec.2", "sch.2-sec.2"}


def test_non_clause_unit_is_refused(snap):
    d = rf.fix_row(N, snap)
    assert d["verdict"] == "refuse" and d["reason"] == "unit_not_a_clause" and d["unit"] == "sch.3-note"


def test_dropped_word_is_recopied_with_the_unit_label(snap):
    row = A.replace(" clear ", " ", 1)
    d = rf.fix_row(row, snap)
    assert d["verdict"] == "recopy" and d["unit"] == "sec.5-ssec.1" and d["new_ref"] == "Section 5(1)"


def test_schedule_unit_gets_a_schedule_label(snap):
    t = f"{H}: (c) {G2};"   # intro + paragraph: only the schedule subclause holds both
    d = rf.fix_row(t, snap)
    assert d["verdict"] in ("accept", "recopy") and d["unit"] == "sch.3-sec.141R-ssec.1"
    assert d["new_ref"] == "Schedule 3, section 141R(1)"


def test_too_short_refused(snap):
    assert rf.fix_row("access path clear", snap)["reason"] == "too_short"


def test_decide_recopy_default_is_unchanged(snap):
    row = mb.norm_tokens(A.replace(" clear ", " ", 1))
    assert mb.decide_recopy(A.replace(" clear ", " ", 1), row, "sec.6", snap)["reason"] == "ref_mismatch"
    assert mb.decide_recopy(A.replace(" clear ", " ", 1), row, "sec.6", snap, ignore_ref=True)["verdict"] == "recopy"


# ---------------------------------------------------------------------------------------------- verifier
def build(snap, tmp_path, text, old_ref):
    d = rf.fix_row(text, snap)
    assert d["verdict"] in ("accept", "recopy"), d
    uid, new = d["unit"], d["new_ref"]
    plan_row = {"id": 1, "md5": mb.md5(text), "rule": d["verdict"], "epi": EPI, "document_id": "x", "ref_number": old_ref,
                "old_ref_number": old_ref, "new_ref_number": new, "unit_id": uid, "law_date": "2026-10-16",
                "source": f"{mb.p1.LAW_URL.format(epi=EPI)}#{uid}", "old_text": text,
                "new_text": snap.units[uid].text if d["verdict"] == "recopy" else None}
    e = {"id": 1, "rule": d["verdict"], "epi": EPI, "snapshot_file": snap.file, "snapshot_sha256": snap.sha256,
         "law_date": "2026-10-16", "unit_id": uid, "norm_version": mb.NORM_VERSION, "match_version": mb.MATCH_VERSION,
         "old_md5": mb.md5(text), "ref_number": new, "old_ref_number": old_ref, "new_ref_number": new}
    e.update({k: d[k] for k in ("word_start", "word_end", "n_words", "unit_words", "tokens_sha256", "matched_words",
                                "coverage", "size_ratio", "new_sha256") if k in d})
    (tmp_path / "manifest.json").write_text(json.dumps({EPI: {"sha256": snap.sha256}}), encoding="utf8")
    return {"manifest": {EPI: {"sha256": snap.sha256}}, "rows": [plan_row]}, [e]


def test_verifier_passes_a_ref_fix_row(snap, tmp_path):
    plan, ev = build(snap, tmp_path, A, "Earthworks")
    assert ver.verify(plan, ev, tmp_path) == (1, [])


def test_verifier_fails_when_the_label_is_not_the_units(snap, tmp_path):
    plan, ev = build(snap, tmp_path, A, "Earthworks")
    plan["rows"][0]["new_ref_number"] = ev[0]["new_ref_number"] = ev[0]["ref_number"] = "Section 5(2)"
    assert ver.verify(plan, ev, tmp_path)[1]


def test_verifier_fails_when_the_label_fails_the_display_check(snap, tmp_path):
    plan, ev = build(snap, tmp_path, A, "Earthworks")
    plan["rows"][0]["new_ref_number"] = ev[0]["new_ref_number"] = ev[0]["ref_number"] = "Section 5(1) (Access)"
    assert ver.verify(plan, ev, tmp_path)[1]


def test_verifier_fails_when_the_unit_was_ambiguous(snap, tmp_path):
    plan, ev = build(snap, tmp_path, A, "Earthworks")
    plan["rows"][0]["old_text"] = C
    assert ver.verify(plan, ev, tmp_path)[1]


# --- cross-review 2026-10-17 ------------------------------------------------------------------------------------
S = "the consent authority may grant consent if it is satisfied that the plan applied to the land"
L = "before the plan was made the council held a hearing and " + S + " and then published notice widely"
HTML2 = f"""<html><body>
<div class="frag-clause" id="sec.2.18"><h3>2.18 Plans</h3><p>{S}.</p></div>
<h2>Part 2.4 Principal development standards</h2>
<div class="frag-clause" id="sec.2.19"><h3>2.19 Height</h3><p>the height of a building must not exceed the maximum shown.</p></div>
<h2>Part 3.1 Other matters</h2>
<div class="frag-clause" id="sec.9.1"><h3>9.1 Notices</h3><p>{L}.</p></div>
</body></html>"""


@pytest.fixture()
def snap2(tmp_path):
    f = tmp_path / f"{EPI}_2026-10-17.html"
    f.write_text(HTML2, encoding="utf8")
    return mb.Snapshot(f)


def test_heading_printed_in_law_and_not_in_unit_is_left_out(snap2):
    old = S + ".\nPart 2.4 Principal development standards"
    assert "2.4" not in mb.numbers_for_check(old, snap2, "sec.2.18")


def test_heading_not_printed_in_law_keeps_its_numbers(snap2):
    old = S + ".\nPart 7.9 Something the law does not have"
    assert "7.9" in mb.numbers_for_check(old, snap2, "sec.2.18")


def test_words_also_inside_an_unrelated_longer_unit_are_ambiguous(snap2):
    # S fills sec.2.18 but also sits verbatim inside sec.9.1: the unit is not decided
    d = rf.find_unit(S, snap2)
    assert d.get("reason") == "ambiguous_unit" and "sec.9.1" in d["candidates"]


def test_heading_printed_elsewhere_in_law_keeps_its_numbers(snap2):
    # 'Part 3.1' is a real heading, but not the one right after sec.2.18
    old = S + ".\nPart 3.1 Standards for 9 metre buildings"
    nums = mb.numbers_for_check(old, snap2, "sec.2.18")
    assert "3.1" in nums and "9" in nums


def test_number_in_an_adjacent_headings_title_still_counts(snap2):
    # 'Part 2.4' IS the heading after sec.2.18, but its title here carries a 9: only the label's 2.4 leaves the check
    old = S + ".\nPart 2.4 Standards for 9 metre buildings"
    nums = mb.numbers_for_check(old, snap2, "sec.2.18")
    assert "2.4" not in nums and "9" in nums


def test_same_words_label_passes_the_display_check():
    lab = rf.same_words_label(["Section 3.29(3)", "Section 3C.32(3)", "Section 3D.53(4)"])
    assert lab == "Section 3.29(3); same words in 3C.32(3), 3D.53(4)" and rf.state_clause_label(lab) == lab
    sch = rf.same_words_label(["Schedule 6, section 13(3)", "Schedule 7, section 15(3)"])
    assert rf.state_clause_label(sch) == sch
    for bad in ["provision_12; same words in 3.1", "Section 3.1; same words in banana",
                "Section 3.1; same words in 3.2, provision_9", "Section 3.1; same words in "]:
        assert rf.state_clause_label(bad) is None
