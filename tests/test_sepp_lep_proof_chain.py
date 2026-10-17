"""sepp_lep_proof.decide_chain: an excerpt of a law clause is re-copied as the smallest complete clause (DQ-145 group 3)."""
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import sepp_lep_proof as lp  # noqa: E402
import sepp_marker_blind as mb  # noqa: E402

HEAD = "development consent must not be granted to development on land in a flood planning area unless the consent"
TAIL = ("authority is satisfied the development is compatible with the flood function and behaviour on the land and "
        "will not adversely affect flood behaviour in a way that results in detrimental increases in the potential "
        "flood affectation of other development or properties within 12 metres of the lot boundary")
SHORT = "the height of a building on any land is not to exceed the maximum height shown for the land on the map"

HTML = f"""<html><body>
<div class="frag-clause" id="sec.5.21"><h3>5.21 Flood planning</h3><p>{HEAD} {TAIL}.</p></div>
<div class="frag-clause" id="sec.4.3"><h3>4.3 Height of buildings</h3><p>{SHORT}.</p></div>
</body></html>"""


@pytest.fixture()
def snap(tmp_path):
    f = tmp_path / "epi-test_2026-10-18.html"
    f.write_text(HTML, encoding="utf8")
    return mb.Snapshot(f)


def test_excerpt_is_recopied_as_the_whole_clause(snap):
    # the first 12 words of a 60-word clause: marker-blind refuses it as an excerpt (unit > 3x the row)
    row = " ".join(HEAD.split()[:12])
    assert mb.decide(row, "5.21", snap)["reason"] == "excerpt"
    stage, d = lp.decide_chain(row, "5.21", snap)
    assert stage == "complete_unit"
    assert d["verdict"] == "recopy" and d["unit"] == "sec.5.21"
    assert snap.units[d["unit"]].text.strip().endswith("lot boundary.")


def test_excerpt_under_another_clauses_label_is_refused_not_moved(snap):
    # cross-review 2026-10-18: words of 5.21 under the label 4.3 must never be re-copied as 5.21
    row = " ".join(HEAD.split()[:12])
    stage, d = lp.decide_chain(row, "4.3", snap)
    assert d["verdict"] == "refuse"   # marker-blind: ref_mismatch -> ref_fix refuses it (excerpt); never a recopy


def test_chosen_clause_outside_the_excerpts_line_is_refused(snap, monkeypatch):
    # the guard itself: if the words ever pick a clause unrelated to the excerpt's unit, refuse instead of moving the row
    row = " ".join(HEAD.split()[:12])
    monkeypatch.setattr(lp.cu, "decide_smallest_unit",
                        lambda *a, **k: {"verdict": "recopy", "unit": "sec.4.3", "n_words": 12})
    stage, d = lp.decide_chain(row, "5.21", snap)
    assert stage == "complete_unit" and d["verdict"] == "refuse" and d["reason"] == "ref_mismatch"


def test_row_marker_blind_settles_stays_with_marker_blind(snap):
    # the clause body without its heading words: marker-blind settles it itself (unit within 3x), unchanged path
    stage, d = lp.decide_chain(SHORT, "4.3", snap)
    assert stage == "marker_blind" and d["verdict"] in ("accept", "recopy") and d["unit"] == "sec.4.3"


def test_words_in_no_clause_stay_refused(snap):
    stage, d = lp.decide_chain("a dwelling must have a garage for two cars behind the building line at all times", "4.3",
                               snap)
    assert d["verdict"] == "refuse"
