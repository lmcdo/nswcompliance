"""sepp_complete_unit: smallest complete law unit re-copy mode; decide()/decide_recopy() behaviour is unchanged."""
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import sepp_complete_unit as cu  # noqa: E402
import sepp_marker_blind as mb  # noqa: E402
import verify_sepp_marker_blind as ver  # noqa: E402

S1 = "the owner of the land must keep every drain and gutter clear of debris and leaves at all times"
S2 = "a council may require the owner to repair any damaged drain within 28 days of written notice"
T1 = "the occupier must not store flammable liquids within 3 metres of the boundary fence of the lot"
T2 = "a retaining wall on the lot must be built by a qualified person and inspected before backfilling"
NOTE = "this note explains how the certifier may inspect a drain and gutter before the certificate issues"
LONG = " ".join(f"word{i}" for i in range(700))

HTML = f"""<html><body>
<div class="frag-clause" id="sec.7"><h3>7 Drains</h3>
 <div class="frag-subclause" id="sec.7-ssec.1"><p>(1) {S1}.</p></div>
 <div class="frag-subclause" id="sec.7-ssec.2"><p>(2) {S2}.</p></div></div>
<div class="frag-clause" id="sch.1-sec.9"><h3>9 Fences</h3><p>{T1}.</p></div>
<div class="frag-clause" id="sch.2-sec.9"><h3>9 Fences</h3><p>{T1}.</p></div>
<div class="frag-note" id="sch.4-note"><p>{NOTE}.</p></div>
<div class="frag-clause" id="sec.20"><h3>20 Long</h3>
 <div class="frag-subclause" id="sec.20-ssec.1"><p>(1) {LONG}.</p></div></div>
<div class="frag-clause" id="sec.30"><h3>30 Walls</h3><p>{T2}.</p></div>
</body></html>"""


@pytest.fixture()
def snap(tmp_path):
    f = tmp_path / "epi-test_2026-10-17.html"
    f.write_text(HTML, encoding="utf8")
    return mb.Snapshot(f)


def drop(text, n=1):
    w = text.split()
    return " ".join(w[:3] + w[3 + n:])   # a row with n words dropped from the unit


def test_one_smallest_unit_is_picked_and_labelled(snap):
    d = cu.decide_smallest_unit(drop(S1, 2), snap)
    assert d["verdict"] == "recopy" and d["unit"] == "sec.7-ssec.1" and d["new_ref"] == "Section 7(1)"
    assert d["reason"] == cu.MODE and d["coverage"] >= mb.COVERAGE_MIN


def test_smallest_unit_wins_over_covering_parent(snap):
    # sec.7 contains the words too (it holds both subclauses) but ssec.1 is the smallest complete unit
    row = drop(S1, 2)
    assert "sec.7" in cu.covering_units(mb.norm_tokens(row), snap)
    assert cu.decide_smallest_unit(row, snap)["unit"] == "sec.7-ssec.1"


def test_two_unrelated_covering_units_refused(snap):
    d = cu.decide_smallest_unit(drop(T1, 2), snap)
    assert d["verdict"] == "refuse" and d["reason"] == "ambiguous_unit"
    assert set(d["candidates"]) >= {"sch.1-sec.9", "sch.2-sec.9"}


def test_non_clause_unit_refused(snap):
    d = cu.decide_smallest_unit(drop(NOTE, 2), snap)
    assert d["verdict"] == "refuse" and d["reason"] == "unit_not_a_clause" and d["unit"] == "sch.4-note"


def test_unit_over_600_words_refused(snap):
    row = " ".join(LONG.split()[:300])
    d = cu.decide_smallest_unit(row, snap)
    assert d["verdict"] == "refuse" and d["reason"] == "unit_over_600_words" and d["unit_words"] >= 700


def test_number_missing_refused(snap):
    row = drop(T2, 1) + " for 45 days"
    d = cu.decide_smallest_unit(row, snap)
    assert d["verdict"] == "refuse" and d["reason"] in ("number_missing", "no_unit_covers_90pct")
    row = drop(T2, 1).replace("qualified", "qualified 45")
    d = cu.decide_smallest_unit(row, snap)
    assert d["verdict"] == "refuse" and d["reason"] == "number_missing" and "45" in d["numbers_lost"]


def test_identical_text_refused_and_short_refused(snap):
    assert cu.decide_smallest_unit("too short", snap)["reason"] == "too_short"
    assert cu.decide_smallest_unit(snap.units["sec.30"].text, snap)["reason"] == "already_identical"


def test_existing_behaviour_unchanged(snap):
    # the 3x size cap still applies to decide_recopy; the new mode is separate
    assert mb.SIZE_MAX == 3.0 and cu.MAX_WORDS == 600
    row = drop(T2, 1)
    d = mb.decide(row, "Section 30", snap)
    assert d["verdict"] == "recopy" and d["unit"] == "sec.30"
    big = mb.decide_recopy(" ".join(LONG.split()[:100]), mb.norm_tokens(" ".join(LONG.split()[:100])), None, snap)
    assert big["verdict"] in ("refuse", "recopy")


def test_verifier_rederives_mode_rows_and_catches_tampering(snap, tmp_path):
    old = drop(S1, 2)
    d = cu.decide_smallest_unit(old, snap)
    uid = d["unit"]
    ev = {"id": 1, "rule": "recopy", "mode": cu.MODE, "epi": "epi-test", "snapshot_file": snap.file,
          "snapshot_sha256": snap.sha256, "law_date": "2026-10-17", "unit_id": uid, "norm_version": mb.NORM_VERSION,
          "match_version": mb.MATCH_VERSION, "old_md5": mb.md5(old), "ref_number": d["new_ref"],
          "old_ref_number": "Clause 7", "new_ref_number": d["new_ref"], "pick": cu.MODE}
    ev.update({k: d[k] for k in ("n_words", "unit_words", "tokens_sha256", "matched_words", "coverage", "size_ratio",
                                 "new_sha256")})
    row = {"id": 1, "md5": mb.md5(old), "rule": "recopy", "kind": "complete_unit_recopy", "epi": "epi-test",
           "document_id": "x", "ref_number": "Clause 7", "old_ref_number": "Clause 7", "new_ref_number": d["new_ref"],
           "unit_id": uid, "source": f"{mb.p1.LAW_URL.format(epi='epi-test')}#{uid}", "law_date": "2026-10-17",
           "old_text": old, "new_text": snap.units[uid].text}
    plan = {"manifest": {"epi-test": {"sha256": snap.sha256}}, "rows": [row]}
    (tmp_path / "manifest.json").write_text('{"epi-test": {"sha256": "%s"}}' % snap.sha256)
    ok, bad = ver.verify(plan, [ev], tmp_path)
    assert (ok, bad) == (1, [])
    for tamper in ({"new_ref_number": "Section 7(2)"}, {"new_text": snap.units[uid].text + " x"}):
        r2 = dict(row, **tamper)
        e2 = dict(ev, new_ref_number=tamper.get("new_ref_number", ev["new_ref_number"]))
        ok, bad = ver.verify({"manifest": plan["manifest"], "rows": [r2]}, [e2], tmp_path)
        assert ok == 0 and bad


# --- context tie-break (user 2026-10-17: "surely we can establish via context") ----------------------------------
def test_branch_of_units():
    assert cu.branch("sch.6A-sec.4-ssec.2") == "sch.6A"
    assert cu.branch("sec.3D.61-ssec.2") == "sec.3D"
    assert cu.branch(None) is None


def test_own_label_breaks_a_tie_between_schedules(snap):
    # T1's words are in sch.1-sec.9 AND sch.2-sec.9; a label naming Schedule 2 picks sch.2-sec.9
    ctx = cu.tiebreaks("Schedule 2, section 9", (None, None))
    d = cu.decide_smallest_unit(drop(T1, 2), snap, None, ctx)
    assert d["verdict"] == "recopy" and d["unit"] == "sch.2-sec.9" and d["tiebreak"]["by"] == "own_label_unit"


def test_neighbour_labels_are_not_used(snap):
    # withdrawn 2026-10-17: row id order is not document order, so agreeing neighbours settle nothing
    agree = cu.tiebreaks("Fences", ("Schedule 1, section 8", "Schedule 1, section 10"))
    assert cu.decide_smallest_unit(drop(T1, 2), snap, None, agree)["reason"] == "ambiguous_unit"


def test_no_context_still_refuses(snap):
    assert cu.decide_smallest_unit(drop(T1, 2), snap, None, cu.tiebreaks("Fences", (None, None)))["reason"] == "ambiguous_unit"
