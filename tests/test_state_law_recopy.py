"""state_law_recopy: unit parsing, unique-smallest-unit choice, acceptance checks a-e; apply guard."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import state_law_recopy as R  # noqa: E402
import apply_state_law_recopy as A  # noqa: E402

DASH = "—"


def clause(num, heading, body, note=""):
    return (f'<div id="sec.{num}" class="frag-clause"><div class="heading"><span class="frag-no">{num}</span>'
            f'&nbsp;&nbsp;<span id="sec.{num}-he" class="frag-heading">{heading}</span></div>'
            f'<blockquote class="children">{body}</blockquote>{note}</div>')


def sub(num, n, text, paras=()):
    ps = "".join(f'<div id="sec.{num}-ssec.{n}-para1.{k}" class="frag-li"><blockquote class="children">'
                 f'<span class="frag-no">({k})</span>&nbsp;&nbsp;{t}</blockquote></div>' for k, t in paras)
    return (f'<blockquote id="sec.{num}-ssec.{n}" class="frag-subclause"><span class="frag-no">({n})</span>'
            f'&nbsp; {text}{ps}</blockquote>')


FENCE = "A boundary fence must not be higher than 1.8 metres above ground level on a residential lot"
PAGE = ("<html><body>"
        + clause("5", "Fences", sub("5", 1, f"Development under this clause must comply with these standards{DASH}",
                                    [("a", f"{FENCE}, and"),
                                     ("b", "a retaining wall must not be more than 600 mm high measured from existing "
                                           "ground level at any point")])
                 + sub("5", 2, "A swimming pool must be fenced in accordance with the Swimming Pools Act 1992 at all "
                               "times when it is in use by any person"),
                 '<div class="frag-historynote"><div>s 5: Am 2023 (83), Sch 1</div></div>')
        + clause("6", "Signs", sub("6", 1, "A sign must not be illuminated after ten o'clock at night in a residential "
                                           "zone, unless the council consents"))
        + clause("7", "Lights", sub("7", 1, "A sign must not be illuminated after ten o'clock at night in a residential "
                                            "zone, unless the council consents"))
        + clause("8", "Tanks", sub("8", 1, "The capacity of a water tank must not exceed 10 000 litres for a "
                                           "dwelling on a lot of less than 4,000 square metres"))
        + "</body></html>")
INST = R.Instrument(PAGE)


def test_parse_units_ids_parents_text():
    u = INST.units
    assert {"sec.5", "sec.5-ssec.1", "sec.5-ssec.1-para1.a", "sec.5-ssec.2"} <= set(u)
    assert u["sec.5-ssec.1"].parent == "sec.5" and u["sec.5-ssec.1-para1.a"].parent == "sec.5-ssec.1"
    assert u["sec.5-ssec.1-para1.a"].text.startswith("(a) A boundary fence")
    assert u["sec.5-ssec.1"].text.startswith("(1) Development under this clause must comply with these standards" + DASH)
    assert "\xa0" not in u["sec.5"].text


def test_history_note_is_not_part_of_the_unit():
    assert "Am 2023" not in INST.units["sec.5"].text


def test_smallest_unique_unit_wins_over_its_parents():
    uid, why, _ = R.pick_unit(f"{FENCE}, and", INST)
    assert (uid, why) == ("sec.5-ssec.1-para1.a", "ok")


def test_row_spanning_two_subclauses_takes_the_clause():
    text = (f"(1) Development under this clause must comply with these standards{DASH} (a) {FENCE}, and "
            "(2) A swimming pool must be fenced in accordance with the Swimming Pools Act 1992 at all times when it "
            "is in use by any person")
    assert R.pick_unit(text, INST)[:2] == ("sec.5", "ok")


def test_identical_text_in_two_places_is_ambiguous():
    uid, why, cand = R.pick_unit("A sign must not be illuminated after ten o'clock at night in a residential zone, "
                                 "unless the council consents", INST)
    assert uid is None and why == "ambiguous" and set(cand) == {"sec.6-ssec.1", "sec.7-ssec.1"}


def test_text_from_nowhere_and_short_text_are_skipped():
    assert R.pick_unit("Fireworks may be sold only to persons holding a current licence issued by the regulator "
                       "for that purpose", INST)[1] == "no_unit_holds_90pct"
    assert R.pick_unit("A fence must be low", INST)[1] == "too_short"


def judge(old, uid):
    return R.judge(old, INST, uid)


def test_ellipsis_markup_and_markers_are_explained_removals():
    old = ("**(a)** A boundary fence must not be higher than ... above ground level on a residential lot, and "
           "<table><tr><td></td></tr></table>")
    j = judge(old, "sec.5-ssec.1-para1.a")
    assert j["ok"], j
    assert j["words_dropped"] == []


def test_page_furniture_is_not_a_content_word():
    old = (f"{FENCE}, and State Environmental Planning Policy (Housing) 2021 - NSW Legislation")
    assert judge(old, "sec.5-ssec.1-para1.a")["ok"]


def test_content_word_dropped_is_refused():
    old = FENCE.replace("1.8 metres", "1.8 metres or exactly 2.4 metres") + ", and"
    j = judge(old, "sec.5-ssec.1-para1.a")
    assert not j["ok"] and "b_no_content_word_dropped" in j["failed"]
    assert "exactly" in j["words_dropped"]


def test_a_number_that_vanishes_is_refused():
    # same words, but the old row carries a number the unit does not
    old = f"{FENCE}, and 2.4"
    j = judge(old, "sec.5-ssec.1-para1.a")
    assert not j["ok"] and "d_numbers_kept" in j["failed"] and j["numbers_lost"] == ["2.4"]


def test_thousands_group_spelling_is_not_a_vanished_number():
    old = ("The capacity of a water tank must not exceed 10,000 litres for a dwelling on a lot of less than "
           "4 000 square metres")
    j = judge(old, "sec.8-ssec.1")
    assert j["ok"], j


def test_length_ratio_outside_band_is_refused():
    j = judge("A swimming pool must be fenced in accordance with the Swimming Pools Act 1992", "sec.5")
    assert not j["ok"] and "c_length_ratio" in j["failed"]


def test_lost_f_ligature_is_a_repair_not_a_dropped_word():
    page = R.Instrument(PAGE.replace("fenced in accordance", "difficult affordable fenced in accordance"))
    old = ("A swimming pool must be dif cult af ordable fenced in accordance with the Swimming Pools Act 1992 at all "
           "times when it is in use by any person")
    j = R.judge(old, page, "sec.5-ssec.2")
    assert j["ok"], j
    assert j["repairs"]


def test_row_cut_off_mid_word_at_its_end_is_explained():
    old = "A swimming pool must be fenced in accordance with the Swimming Pools Act 1992 at all times when it is in us"
    assert R.judge(old, INST, "sec.5-ssec.2")["words_dropped"] == []


def test_cut_off_word_in_the_middle_is_not_forgiven():
    old = ("A swimming pool must be fenced in accordance with the Swimming Poo Act 1992 at all times when it is "
           "in use by any person")
    assert R.judge(old, INST, "sec.5-ssec.2")["words_dropped"]


def test_new_text_is_verbatim_in_the_law_by_both_provers():
    for uid in ("sec.5", "sec.5-ssec.1", "sec.5-ssec.1-para1.b", "sec.8-ssec.1"):
        assert R.verbatim(INST, INST.units[uid].text), uid
    assert not R.verbatim(INST, "A swimming pool must be fenced in accordance with the Pools Act")


# ---- amended rows (check e) -------------------------------------------------------------------------
OLD_PAGE = PAGE.replace("not be more than 600 mm high", "not be more than 900 mm high")


def test_amended_row_takes_the_same_id_path_in_todays_law():
    pit = R.Instrument(OLD_PAGE)
    old = pit.units["sec.5-ssec.1-para1.b"].text
    j, why, uid = R.judge_amended(old, INST, pit)
    assert (why, uid) == ("ok", "sec.5-ssec.1-para1.b")
    assert j["ok"] and "900" in j["words_dropped"] and "600" in j["words_added"] + ["600"]


def test_amended_refused_when_old_text_is_still_in_todays_law():
    pit = R.Instrument(PAGE)
    j, why, uid = R.judge_amended(INST.units["sec.5-ssec.2"].text, INST, pit)
    assert j is None and why == "e_old_still_in_today"


def test_amended_refused_when_old_text_was_never_in_the_pit_law():
    pit = R.Instrument(OLD_PAGE)
    j, why, _ = R.judge_amended("Fireworks may be sold only to persons holding a current licence issued by the "
                                "regulator for that purpose", INST, pit)
    assert j is None and why == "e_old_not_verbatim_in_pit"


def test_amended_refused_when_the_id_path_no_longer_exists():
    pit = R.Instrument(PAGE.replace('id="sec.7-ssec.1"', 'id="sec.9-ssec.1"').replace("Lights", "Lamps"))
    old = "A sign must not be illuminated after ten o'clock at night in a residential zone, unless the council consents"
    # two places carry it in the old law (sec.6, sec.9), so not unique -> refused before the path test
    assert R.judge_amended(old, INST, pit)[0] is None


# ---- apply guard -------------------------------------------------------------------------------------
def test_apply_refuses_changed_text_version_history_and_non_state_rows():
    plan = [{"id": 1, "md5": "a", "new_text": "x"}, {"id": 2, "md5": "b", "new_text": "y"},
            {"id": 3, "md5": "c", "new_text": "z"}, {"id": 4, "md5": "d", "new_text": "w"},
            {"id": 5, "md5": "e", "new_text": "v"}]
    db = {1: ("a", None, True, 0), 2: ("CHANGED", None, True, 0), 3: ("c", None, True, 2),
          4: ("d", "waverley", True, 0)}
    bad = A.check_plan(plan, db)
    assert not any(b.startswith("1:") for b in bad)
    assert any(b.startswith("2:") and "changed" in b for b in bad)
    assert any(b.startswith("3:") and "version" in b for b in bad)
    assert any(b.startswith("4:") and "state-law" in b for b in bad)
    assert any(b.startswith("5:") and "not in the database" in b for b in bad)


def test_apply_refuses_empty_or_replacement_char_text():
    db = {1: ("a", None, True, 0), 2: ("b", None, True, 0)}
    bad = A.check_plan([{"id": 1, "md5": "a", "new_text": ""}, {"id": 2, "md5": "b", "new_text": "a�b"}], db)
    assert len(bad) == 2
