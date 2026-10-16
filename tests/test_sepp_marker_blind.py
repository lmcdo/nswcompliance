"""sepp_marker_blind: rule 1 (marker-blind exact contiguous -> accept), rule 2 (dropped words -> recopy), verifier."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import sepp_marker_blind as mb  # noqa: E402
import verify_sepp_marker_blind as ver  # noqa: E402

A = "the occupier of the land must keep the access path clear of obstructions at all times"
B = "a retaining wall on the land must not exceed a height of 1 metre above ground level"
D = "the owner of the building must provide the council with a copy of the certificate on request"
E = "an awning over the footpath must be at least two and a half metres above the ground"
F = "a flagpole on the roof must be set back from every boundary of the lot by a fair distance"
C = "water tanks installed under this code must be screened from the street frontage entirely"

HTML = f"""<html><body>
<div class="frag-clause" id="sec.5"><h3>5 Access</h3>
 <div class="frag-subclause" id="sec.5-ssec.1"><p>(1) {A}</p></div>
 <div class="frag-subclause" id="sec.5-ssec.2"><p>(2) {B}.</p></div></div>
<div class="frag-clause" id="sec.6"><h3>6 Walls</h3>
 <div class="frag-subclause" id="sec.6-ssec.1"><p>(1) {C}.</p></div></div>
<div class="frag-clause" id="sch.1-sec.7"><h3>7 Tanks</h3>
 <div class="frag-subclause" id="sch.1-sec.7-ssec.1"><p>(1) {C}.</p></div></div>
<div class="frag-clause" id="sec.11"><h3>11 Flags</h3><p>{" ".join(["padding"] * 80)}</p>
 <div class="frag-subclause" id="sec.11-ssec.1"><p>(1) {F}.</p></div>
 <div class="frag-subclause" id="sec.11-ssec.2"><p>(2) {F}.</p></div></div>
<div class="frag-clause" id="sec.10"><h3>10 Awnings</h3>
 <div class="frag-subclause" id="sec.10-ssec.1"><p>(1) {E}.</p></div>
 <div class="frag-subclause" id="sec.10-ssec.2"><p>(2) {E}.</p></div></div>
<div class="frag-clause" id="sec.9"><h3>9 Twice</h3><p>{D}. Later, {D}.</p></div>
<div class="frag-clause" id="sec.8"><h3>8 Big</h3><p>{B} and then a great deal of other unrelated text follows here, {" ".join(["filler"] * 60)}</p></div>
</body></html>"""
EPI = "epi-test"


@pytest.fixture()
def snap(tmp_path):
    f = tmp_path / f"{EPI}_2026-10-16.html"
    f.write_text(HTML, encoding="utf8")
    return mb.Snapshot(f)


def drop(text, word):
    return text.replace(f" {word} ", " ", 1)


# ------------------------------------------------------------------------------- normaliser
def test_markers_dashes_bullets_vanish():
    assert mb.norm_tokens("(a) the - cat–dog; (ii) sat") == mb.norm_tokens("• the cat dog sat")


def test_marker_attached_to_a_word_is_kept():
    assert mb.norm_tokens("section 5(2) applies") == ["section", "5", "2", "applies"]


def test_a_dropped_word_is_not_hidden_by_the_normaliser():
    assert mb.norm_tokens("the cat sat") != mb.norm_tokens("the sat")


# ------------------------------------------------------------------------------- rule 1
def test_rule1_marker_only_difference_is_accepted(snap):
    row = "- " + A.replace(" must ", " must; ", 1)   # dash bullet + added punctuation, no marker, no word change
    d = mb.decide(row, "Section 5(1)", snap)
    assert d["verdict"] == "accept" and d["unit"] == "sec.5-ssec.1"
    assert d["word_end"] - d["word_start"] == len(mb.norm_tokens(row))


def test_rule1_row_with_its_own_markers_accepted(snap):
    d = mb.decide("(1) (a) " + A, "Section 5(1)", snap)
    assert d["verdict"] == "accept"


def test_rule1_one_dropped_word_is_not_accepted(snap):
    row = drop(A, "keep")
    d = mb.decide(row, "Section 5(1)", snap, allow_recopy=False)
    assert d["verdict"] == "refuse" and d["reason"] == "not_contiguous"
    assert mb.decide(row, "Section 5(1)", snap)["verdict"] == "recopy"   # ... it goes to rule 2 instead


def test_rule1_changed_word_is_not_accepted(snap):
    d = mb.decide(A.replace("clear", "free"), None, snap, allow_recopy=False)
    assert d["verdict"] == "refuse"


def test_rule1_ambiguous_unit_refused(snap):
    d = mb.decide(E, "Section 10", snap)   # the same words fill sec.10-ssec.1 and sec.10-ssec.2; the ref names neither
    assert d["verdict"] == "refuse" and d["reason"] == "ambiguous_unit"


def test_rule1_ref_number_picks_between_equal_units(snap):
    d = mb.decide(C, "Section 6(1)", snap)
    assert d["verdict"] == "accept" and d["unit"] == "sec.6-ssec.1" and d["reason"] == "ref_number_unit"


def test_rule1_run_that_repeats_inside_the_unit_is_refused(snap):
    d = mb.decide(D, "Section 9", snap)
    assert d["verdict"] == "refuse" and d["reason"] == "repeated_in_unit"


def test_ref_mismatch_refused_even_when_text_is_verbatim(snap):
    for ref in ("provision_9", "Section 6(1)", None, "Earthworks"):   # text is only in sec.5-ssec.1
        d = mb.decide(A, ref, snap)
        assert d["verdict"] == "refuse" and d["reason"] == "ref_mismatch" and "sec.5-ssec.1" in d["candidates"]
    assert mb.decide(A, "Section 5", snap)["verdict"] == "accept"   # parent of the unit counts as related


def test_ref_mismatch_refused_for_recopy_too(snap):
    d = mb.decide(drop(A, "keep"), "Section 6(1)", snap)
    assert d["verdict"] == "refuse" and d["reason"] == "ref_mismatch" and d["unit"].startswith("sec.5")


def test_excerpt_short_of_the_clause_is_recopied_not_accepted(snap):
    row = " ".join(A.split()[:14])   # first 14 of 16 words: contiguous, but only 87 percent of the unit
    d = mb.decide(row, "Section 5(1)", snap)
    assert d["verdict"] == "recopy" and d["unit"] == "sec.5-ssec.1" and d["excerpt"] is True
    assert mb.decide(row, "Section 5(1)", snap, allow_recopy=False)["reason"] == "excerpt"


def test_excerpt_refused_when_the_whole_unit_is_too_big_to_recopy(snap):
    d = mb.decide(B, "Section 8", snap)   # 16 words of an 80-word unit
    assert d["verdict"] == "refuse" and d["reason"] == "excerpt" and d["detail"] == "ref_mismatch"


def test_rule1_too_short_refused(snap):
    assert mb.decide("the occupier of the land", None, snap)["reason"] == "too_short"


# ------------------------------------------------------------------------------- rule 2
def test_rule2_recopies_the_full_unit_text(snap):
    d = mb.decide(drop(A, "keep"), "Section 5(1)", snap)
    assert d["verdict"] == "recopy" and d["unit"] == "sec.5-ssec.1" and d["coverage"] >= 0.9
    assert d["size_ratio"] <= 3.0


def test_rule2_unit_more_than_3x_the_row_refused(snap):
    row = drop(B, "exceed") + " and then a great deal of other unrelated text follows here"
    d = mb.decide(row, "Section 8", snap)
    assert d["verdict"] == "refuse" and d["reason"] == "unit_too_big"


def test_rule2_missing_number_refused(snap):
    assert mb.decide(drop(B, "must"), "Section 5(2)", snap)["verdict"] == "recopy"   # control: same row, number kept
    row = drop(B, "must").replace("1 metre", "7 metre")
    d = mb.decide(row, "Section 5(2)", snap)
    assert d["verdict"] == "refuse" and d["reason"] == "number_missing"


def test_rule2_eighty_percent_coverage_refused(snap):
    w = A.split()
    row = " ".join(w[:3] + ["zzz1", "zzz2"] + w[5:])   # 2 of 16 words replaced -> 0.875 ordered coverage
    d = mb.decide(row, "Section 5(1)", snap)
    assert d["verdict"] == "refuse" and d["reason"] == "no_unit_covers_90pct"


def test_rule2_low_coverage_refused(snap):
    d = mb.decide("the occupier of the land will keep paths free of any junk at every moment", "Section 5(1)", snap)
    assert d["verdict"] == "refuse"


def test_rule2_ambiguous_refused(snap):
    d = mb.decide(drop(F, "fair"), "Section 11", snap)
    assert d["verdict"] == "refuse" and d["reason"] == "ambiguous_unit"


# ------------------------------------------------------------------------------- verifier
def build(snap, tmp_path, rows):
    plan_rows, ev = [], []
    for rid, text, ref in rows:
        d = mb.decide(text, ref, snap)
        assert d["verdict"] in ("accept", "recopy"), d
        rule = d["verdict"]
        plan_rows.append({"id": rid, "md5": mb.md5(text), "rule": rule, "epi": EPI, "unit_id": d["unit"],
                          "ref_number": ref, "old_text": text, "law_date": "2026-10-16",
                          "source": f"{mb.p1.LAW_URL.format(epi=EPI)}#{d['unit']}",
                          "new_text": snap.units[d["unit"]].text if rule == "recopy" else None})
        e = {"id": rid, "rule": rule, "epi": EPI, "snapshot_file": snap.file, "snapshot_sha256": snap.sha256,
             "unit_id": d["unit"], "law_date": "2026-10-16", "norm_version": mb.NORM_VERSION, "match_version": mb.MATCH_VERSION,
             "old_md5": mb.md5(text)}
        e.update({k: d[k] for k in ("word_start", "word_end", "n_words", "unit_words", "tokens_sha256", "matched_words",
                                    "coverage", "size_ratio", "new_sha256") if k in d})
        ev.append(e)
    (tmp_path / "manifest.json").write_text(json.dumps({EPI: {"sha256": snap.sha256}}), encoding="utf8")
    return {"manifest": {EPI: {"sha256": snap.sha256}}, "rows": plan_rows}, ev


def good(snap, tmp_path):
    return build(snap, tmp_path, [(1, "- " + A, "Section 5(1)"), (2, drop(B, "exceed"), "Section 5(2)")])


def test_verifier_passes_untouched(snap, tmp_path):
    plan, ev = good(snap, tmp_path)
    assert {e["rule"] for e in ev} == {"accept", "recopy"}
    ok, bad = ver.verify(plan, ev, tmp_path)
    assert (ok, bad) == (2, [])


def test_verifier_fails_on_tampered_offsets(snap, tmp_path):
    plan, ev = good(snap, tmp_path)
    ev[0]["word_start"] += 1
    ev[0]["word_end"] += 1
    ok, bad = ver.verify(plan, ev, tmp_path)
    assert bad and ok == 1


def test_verifier_fails_on_tampered_new_text(snap, tmp_path):
    plan, ev = good(snap, tmp_path)
    plan["rows"][1]["new_text"] += " and more"
    assert ver.verify(plan, ev, tmp_path)[1]


def test_verifier_fails_on_snapshot_sha_mismatch(snap, tmp_path):
    plan, ev = good(snap, tmp_path)
    ev[0]["snapshot_sha256"] = hashlib.sha256(b"x").hexdigest()
    assert ver.verify(plan, ev, tmp_path)[1]


def test_verifier_fails_when_old_text_changed(snap, tmp_path):
    plan, ev = good(snap, tmp_path)
    plan["rows"][0]["old_text"] = drop(plan["rows"][0]["old_text"], "keep")
    assert ver.verify(plan, ev, tmp_path)[1]


def test_verifier_fails_when_old_text_differs_only_by_a_marker(snap, tmp_path):
    plan, ev = good(snap, tmp_path)
    plan["rows"][0]["old_text"] = "(1) " + plan["rows"][0]["old_text"]   # same words, different bytes
    assert ver.verify(plan, ev, tmp_path)[1]


def test_verifier_fails_when_source_url_points_elsewhere(snap, tmp_path):
    plan, ev = good(snap, tmp_path)
    plan["rows"][0]["source"] = plan["rows"][0]["source"].replace("sec.5-ssec.1", "sec.6-ssec.1")
    assert ver.verify(plan, ev, tmp_path)[1]


def test_verifier_fails_when_law_date_differs(snap, tmp_path):
    plan, ev = good(snap, tmp_path)
    plan["rows"][1]["law_date"] = "2020-01-01"
    assert ver.verify(plan, ev, tmp_path)[1]


def test_verifier_fails_on_wrong_rule(snap, tmp_path):
    plan, ev = good(snap, tmp_path)
    ev2 = copy.deepcopy(ev)
    ev2[1]["rule"] = "accept"
    plan["rows"][1]["rule"] = "accept"
    assert ver.verify(plan, ev2, tmp_path)[1]


def test_verifier_exit_codes(snap, tmp_path):
    plan, ev = good(snap, tmp_path)
    ok, bad = ver.verify({"manifest": plan["manifest"], "rows": []}, [], tmp_path)
    assert ok == 0 and not bad   # main() turns this into exit 2
