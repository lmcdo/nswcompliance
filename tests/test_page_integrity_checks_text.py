"""Tests for scripts/page_integrity/checks_text.py (fixtures only, no network)."""
from pathlib import Path

import pytest

from scripts.page_integrity import checks_text as ct
from scripts.page_integrity.load import load

FIX = Path(__file__).parent / "fixtures" / "page_integrity"
NAMES = ["winston_hills_6_berrigan", "cabramatta_west_24_yvonne", "mount_annan_3_egret"]


@pytest.fixture(params=NAMES)
def cap(request):
    return load(FIX / request.param)


def facts(flags):
    return {f.fact for f in flags}


def test_c5_red_all(cap):
    f = facts(ct.check_words_on_page(cap))
    assert "as-of-right" in f and "contradiction" in f


def test_c2_winston_not_evaluable():
    c = load(FIX / NAMES[0])
    assert ct.check_engines_agree(c) == []
    assert ct.facts_checked(c)["engines-agree"] is False  # permissibility covered=false, no entries


@pytest.mark.parametrize("n", NAMES[1:])
def test_c2_red(n):
    fl = ct.check_engines_agree(load(FIX / n))
    assert len(fl) == 1 and fl[0].fact == "engines-agree"
    assert any(r["development_type"] == "dual_occupancies" for r in fl[0].evidence["permissibility_rows"])


def test_c2_green_when_max_form_present():
    c = load(FIX / NAMES[1])
    c.last("/api/constraint-arithmetic")["json"]["data"]["max_permitted_form"] = "dual_occupancy"
    assert ct.check_engines_agree(c) == []


def test_c2_green_when_not_permitted():
    c = load(FIX / NAMES[1])
    for e in c.data("/api/lep/permissibility")["entries"]:  # same dict object as the capture
        if e["permissibility"] == "permitted" and ct._norm(e["development_type"]).startswith(ct.DENSER_FORMS):
            e["permissibility"] = "prohibited"
    assert ct.check_engines_agree(c) == []


def test_c6_footprint():
    assert "footprint-pct" in facts(ct.check_derivations(load(FIX / NAMES[2])))
    for n in NAMES[:2]:
        assert ct.check_derivations(load(FIX / n)) == []


def test_c6_fsr_rule_checked_and_green():
    c = load(FIX / NAMES[0])
    assert ct.facts_checked(c)["fsr-gfa"] is True
    assert ct.check_derivations(c) == []


def test_c6_fsr_mutation():
    c = load(FIX / NAMES[0])
    c.last("/api/constraint-arithmetic")["json"]["data"]["lep_max_gfa_from_fsr_m2"] = 400
    assert "fsr-gfa" in facts(ct.check_derivations(c))


def test_c6_footprint_text_over_100():
    c = load(FIX / NAMES[1])
    c.rendered["planning"] += "\nBuildable footprint: 700m² (120% of lot)\n"
    assert "footprint-pct" in facts(ct.check_derivations(c))


def test_as_of_right_removed_is_green():
    c = load(FIX / NAMES[0])
    c.rendered["planning"] = "\n".join(
        ln for ln in c.rendered["planning"].splitlines() if "as-of-right" not in ln.lower())
    f = facts(ct.check_words_on_page(c))
    assert "as-of-right" not in f and "contradiction" not in f


def scan(t):
    return ct.scan_text("t", t)


@pytest.mark.parametrize("t", [
    "value is undefined here", "got NaN m2", "owner: null", "[object Object]",
    "Class Class 5", "the the rule", "SEPP 2022/2021 applies",
])
def test_junk_positive(t):
    assert "render-junk" in facts(scan(t))


@pytest.mark.parametrize("t", [
    "an undefinedness", "nullify the NaNometer", "Class 5 land", "Class A", "10 10 lots",
    "bathe the lot", "SEPP 2021", "a nullable field", "pre-null",
])
def test_junk_negative(t):
    assert not [f for f in scan(t) if f.fact == "render-junk"]


def test_as_of_right_variants_and_contradiction():
    assert "as-of-right" in facts(scan("An as of right yield"))
    assert {"as-of-right", "contradiction"} <= facts(scan("as-of-right yield, subject to a development application."))
    far = "as-of-right x" + " " * 400 + "development application"
    assert "contradiction" not in facts(scan(far))
    assert "contradiction" not in facts(scan("development application only"))


def test_liability_word_separate():
    f = scan("This is a safe and sufficient design")
    assert {x.fact for x in f} == {"liability-word"}
    assert len(f) == 2 and "severity=info" in f[0].detail
    assert not scan("Plain factual text")


def test_facts_checked_keys(cap):
    fc = ct.facts_checked(cap)
    assert set(fc) == {"engines-agree", "as-of-right", "contradiction", "render-junk",
                       "liability-word", "footprint-pct", "fsr-gfa"}
    assert fc["as-of-right"] and fc["render-junk"]


def test_internal_note_shown_to_reader_is_flagged():
    f = ct.scan_text("dcp", "Rear setbacks; excludes secondary dwellings. NOT yet stored: upper-floor 9.0m (C10)")
    assert "internal-note" in {x.fact for x in f}


def test_c6_strata_lot_showing_whole_lot_homes_is_red():
    c = load(FIX / "concord_14_gale")
    c.data("/api/property")["strataInfo"] = {"isStrata": True, "strataPlan": "SP9807"}
    assert "strata-yield" in facts(ct.check_derivations(c))  # the old capture shows "Homes you could build"
    c.rendered["planning"] = c.rendered["planning"].replace("Homes you could build", "")
    assert "strata-yield" not in facts(ct.check_derivations(c))
