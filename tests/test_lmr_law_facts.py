"""data/law/housing_sepp_lmr_facts.json must agree with the saved law text, and must fail when it does not.

Figures typed in this file are the INDEPENDENT second reading of the text (a human-judged read of the
23 Oct 2026 version on 2026-11-07, with PDF pages). They are there so a regression in the extractor cannot
quietly change both sides. Each mutation below must make the comparison fail, or the check proves nothing.
"""

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import extract_lmr_law_facts as law  # noqa: E402

TEXT = law.DEFAULT_TEXT.read_text(encoding="utf-8")
STORED = json.loads(law.FACTS_PATH.read_text(encoding="utf-8"))
VERSION = law.version_date_of(law.DEFAULT_TEXT)
REL = law.DEFAULT_TEXT.relative_to(ROOT).as_posix()


def fresh(text: str = TEXT) -> dict:
    return law.extract(text, REL, VERSION)


# ---- the stored facts belong to this exact text ----------------------------------------------


def test_stored_facts_match_the_saved_text():
    assert law.differences(STORED, fresh()) == []


def test_stored_hash_is_the_hash_of_the_saved_text():
    assert STORED["text_sha256"] == law.text_sha256(TEXT)


def test_hash_ignores_line_ending_style():
    """Git may check the file out with CRLF or LF; the fingerprint must not depend on it."""
    assert law.text_sha256(TEXT.replace("\n", "\r\n")) == law.text_sha256(TEXT)


def test_version_date_comes_from_the_file_name():
    assert STORED["law_version_date"] == "2026-10-23"


# ---- the independent second reading ----------------------------------------------------------


def test_distances_and_their_pages():
    f = STORED["facts"]
    assert (f["lmr_outer_distance"]["value"], f["lmr_outer_distance"]["page"]) == (800, 77)
    assert (f["lmr_inner_distance"]["value"], f["lmr_inner_distance"]["page"]) == (400, 78)
    assert (f["s164_k_distance"]["value"], f["s164_k_distance"]["page"]) == (800, 80)
    assert "not stated" in f["s164_k_distance"]["measured"]
    assert f["lmr_outer_distance"]["measured"] == "walking distance"


def test_lists_and_counts():
    f = STORED["facts"]
    assert f["schedule_11_stations"]["count"] == 59 == len(f["schedule_11_stations"]["value"])
    assert (f["schedule_11_stations"]["page"], f["schedule_11_stations"]["pages_to"]) == (128, 130)
    assert f["schedule_12_stations"]["value"] == ["Cockle Creek station", "Punchbowl station", "Wiley Park station"]
    assert f["tod_lgas"]["count"] == 12 == len(f["tod_lgas"]["value"])
    assert "City of Wollongong" in f["tod_lgas"]["value"] and "Sydney" not in f["tod_lgas"]["value"]
    assert f["s164"]["live_count"] == 13 and len(f["s164"]["paragraphs"]) == 14
    assert [p["para"] for p in f["s164"]["paragraphs"] if p["repealed"]] == ["j"]


def test_light_rail_stations_are_in_schedule_11():
    names = STORED["facts"]["schedule_11_stations"]["value"]
    assert "UNSW Anzac Parade light rail station" in names
    assert sum("light rail" in n for n in names) == 4


def test_tod_standards():
    f = STORED["facts"]
    assert f["tod_height_residential_flat_building_m"]["value"] == 22
    assert f["tod_height_seniors_or_shop_top_m"]["value"] == 24
    assert f["tod_fsr"]["value"] == "2.5:1"
    assert f["tod_affordable_share_percent"]["value"] == 2
    assert f["tod_affordable_gfa_threshold"]["value"] == 2000
    assert f["tod_affordable_gfa_threshold"]["unit_verified"] is False  # superscript lost in the saved text
    assert (f["tod_affordable_parking_1_bed"]["value"], f["tod_affordable_parking_2_bed"]["value"]) == (0.4, 0.5)
    assert f["tod_affordable_parking_3_plus_bed"]["value"] == 1.0
    assert f["tod_min_lot_width_m"]["value"] == 21


def test_site_area_wording_is_the_laws_not_any_part():
    q = STORED["facts"]["lmr_site_area_rule"]["quote"]
    assert "if a site area contains land identified in paragraph (a)" in q and "any part" not in q


# ---- every fact is traceable ------------------------------------------------------------------


def _collapsed(text: str) -> str:
    kept = [ln for ln in law.normalise(text).split("\n") if not law._noise(ln)]
    return re.sub(r"\s+", " ", " ".join(kept))


def test_every_fact_has_clause_page_and_a_quote_that_is_in_the_law_text():
    body = _collapsed(TEXT)
    checked = 0
    for name, fact in STORED["facts"].items():
        items = fact["paragraphs"] if name == "s164" else [fact]
        for it in items:
            assert it["clause"] and isinstance(it["page"], int) and 1 <= it["page"] <= 130, (name, it.get("clause"))
            quote = it.get("quote") or it.get("words")
            assert quote, name
            if name.startswith("schedule_"):
                continue  # the quote is a count statement; the names are checked below
            probe = quote[:200] if it.get("words") else quote
            assert probe in body, (name, probe[:80])
            checked += 1
    # 15 plain facts (18 minus the 2 station lists minus the s164 block) + 14 s164 paragraphs
    assert checked == 29


def test_every_station_name_is_a_line_of_the_law_text():
    lines = {ln.strip() for ln in law.normalise(TEXT).split("\n")}
    for key in ("schedule_11_stations", "schedule_12_stations"):
        for n in STORED["facts"][key]["value"]:
            assert n in lines, n


# ---- break-it: each change to the law text must make the comparison fail --------------------


def mutate(old: str, new: str, count: int = 1) -> str:
    assert old in TEXT, old
    return TEXT.replace(old, new, count)


def test_dropping_a_station_is_detected():
    broken = mutate("Waitara station\n", "", 1) if "Waitara station\n" in TEXT else mutate("Waitara station\r\n", "", 1)
    d = law.differences(STORED, fresh(broken))
    assert "facts.schedule_11_stations" in d and "text_sha256" in d


def test_renaming_a_station_is_detected():
    d = law.differences(STORED, fresh(mutate("Artarmon station", "Artarmon Central station")))
    assert "facts.schedule_11_stations" in d


def test_changing_a_distance_is_detected():
    d = law.differences(STORED, fresh(mutate("land within 800m walking distance of", "land within 900m walking distance of")))
    assert "facts.lmr_outer_distance" in d


def test_changing_a_tod_height_is_detected():
    d = law.differences(
        STORED,
        fresh(mutate("residential flat building in a Transport Oriented Development Area is 22m.", "residential flat building in a Transport Oriented Development Area is 25m.")),
    )
    assert "facts.tod_height_residential_flat_building_m" in d


def test_adding_a_council_to_the_tod_list_is_detected():
    d = law.differences(STORED, fresh(mutate("(m)  City of Wollongong.", "(m)  City of Wollongong,\n(n)  Parramatta.")))
    assert "facts.tod_lgas" in d


def test_shifting_a_page_marker_changes_the_pages():
    d = law.differences(STORED, fresh(mutate("=====PAGE 77", "=====PAGE 78")))
    assert any(k.startswith("facts.") for k in d)


def test_a_missing_schedule_heading_raises_rather_than_returning_nothing():
    with pytest.raises(law.AnchorError):
        fresh(mutate("Schedule 11 Low and mid rise housing area stations", "Schedule 11 renamed"))


def test_a_missing_distance_raises():
    """If the definition no longer states a walking distance, the extractor must stop, not guess."""
    with pytest.raises(law.AnchorError):
        fresh(
            mutate(
                "low and mid rise housing area means—\n(a)  land within 800m walking distance of",
                "low and mid rise housing area means—\n(a)  land near",
            )
        )


def test_empty_text_raises():
    with pytest.raises(law.AnchorError):
        fresh("")


def test_identical_text_has_no_differences():
    assert law.differences(STORED, fresh(TEXT)) == []


def test_command_line_check_passes_on_the_repo_text(capsys):
    assert law.main(["--check"]) == 0
    assert "match the saved text" in capsys.readouterr().out


def test_s164_council_lists_are_complete_not_cut_off():
    """Paragraph (g) names 23 councils and (f1) names 6 (lettered). A length cap once cut (g) mid-word after 17."""
    import re
    paras = {p["para"]: p["words"] for p in STORED["facts"]["s164"]["paragraphs"]}
    g = re.findall(r"\((?:[ivx]+)\)\s*([^,(.]+?)\s*(?:,|$)", paras["g"])
    assert len(g) == 23 and g[0] == "Armidale Regional" and g[-1] == "Walcha"
    f1 = re.findall(r"\(([A-F])\)\s*([^,(.]+?)\s*(?:,|\.|$)", paras["f1"])
    assert [n for _, n in f1] == ["Canterbury-Bankstown", "Cumberland", "City of Fairfield", "Georges River", "City of Liverpool", "Sutherland Shire"]
    assert not paras["g"].endswith(("Qu", "(xvii)")) and len(paras["g"]) > 400
