"""Pages a reading left out, counted by code. Each case from a real PDF, 2026-09-25."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import page_coverage as pc  # noqa: E402

S = ["development must keep the landscaped front setback clear of structures",
     "the maximum building height is measured from existing ground level",
     "car parking must not dominate the street frontage of the site",
     "private open space is to be located behind the front building line",
     "side setbacks must allow solar access to neighbouring living rooms",
     "fences forward of the building line must not exceed one metre"]


def test_a_page_whose_sentences_are_in_the_output_is_not_skipped():
    assert pc.skipped_pages({1: S}, [" ".join(S)]) == []


def test_a_page_whose_sentences_are_absent_is_skipped():
    assert pc.skipped_pages({1: S, 2: S[:1]}, ["unrelated words only here today"]) == [1]


def test_lines_drawn_twice_count_once():
    # Campbelltown draws every line twice. Doubled, a page read in full must
    # still read as read -- and a page of 3 sentences drawn twice is still 3.
    assert len(pc.sentence_lines(S[:3] * 2)) == 3
    assert pc.skipped_pages({1: S * 2}, [" ".join(S)]) == []


def test_letter_spaced_map_labels_are_not_sentences():
    # Canterbury-Bankstown maps: "S a l t  P a n  C r e e k".
    labels = ["S a l t  P a n  C r e e k", "R e m e m b r a n c e  D r i v e w a y"] * 5
    assert pc.sentence_lines(labels) == []
    assert pc.skipped_pages({1: labels}, [""]) == []


def test_a_figure_page_with_few_sentences_is_not_judged():
    assert pc.skipped_pages({1: S[:4]}, [""]) == []


def test_half_read_page_is_not_skipped_but_a_mostly_unread_one_is():
    assert pc.skipped_pages({1: S}, [" ".join(S[:2])]) == []     # 2 of 6 read
    assert pc.skipped_pages({1: S}, [" ".join(S[:1])]) == [1]    # 1 of 6 read


def test_runs_group_consecutive_pages_up_to_a_limit():
    assert pc.runs([5, 3, 4, 9], 12) == [(3, 5), (9, 9)]
    assert pc.runs([1, 2, 3], 2) == [(1, 2), (3, 3)]


def test_rule_words_separate_a_rule_page_from_history_and_definitions():
    assert pc.holds_rules(["buildings must be set back 6m", "the maximum height is 8.5m"])
    assert not pc.holds_rules(["in 1818 the first land grant was made", "riparian zone means land"])
    assert not pc.holds_rules(["a single must on a page is not enough"])


def test_the_probe_counts_only_left_out_pages_that_hold_rules():
    import dq_probe_pages_left_out as probe
    rules = [s + " and must comply with the maximum" for s in S]
    history = [f"in {1800 + i} the estate was subdivided into small lots near the wharf {i}"
               for i in range(6)]
    assert probe.chapter_gaps({1: rules, 2: history}, ["nothing read here at all today"]) == [1]
    assert probe.chapter_gaps({1: rules}, [" ".join(rules)]) == []


# -- the denominator is the rule-bearing lines, not every sentence -------------

#: City of Sydney `schedules` page 65 in miniature: one control, then commentary.
#: The real page prints clause 11.2(10)(a)-(d) and 30 lines of "Resources/Notes"
#: about AS 4282-1997 -- 47 sentence lines, 7 rule-bearing.
_CONTROL = [
    "the calculation of illuminance luminance and threshold increment is to be determined",
    "a maintenance factor of one is to be used for all of the calculations",
    "calculations of threshold increment are to be a series of points in both directions",
    "the grids are to be in the centre of the lane with maximum five metre spacing",
]
_COMMENTARY = [
    "the standard covers lighting schemes for roads pedestrians and outdoor public spaces",
    "the series provides recommendations on the illuminance of pedestrian road lighting",
    "however the objective of road lighting is a lit environment conducive to safe movement",
    "the standard includes recommended benchmarks for the amount of luminous flux arriving",
    "lighting on nearby residents of dwellings such as houses hotels and hospitals",
    "users of adjacent roads including vehicle drivers pedestrians and cyclists are affected",
    "transport signalling systems for air marine and rail are also within its scope",
    "on astronomical observations the night time environment is a further consideration",
    "the brightness limitation of exterior light sources is detailed in the same series",
    "internally illuminated signage sits outside the scope of that particular standard",
    "in the absence of any other specific regulation the standard is applied as practice",
    "care is taken that glare to pedestrians and motorists is reduced where practicable",
    "the illuminance target in this series was never written for advertising signs",
]
#: The real page is 7 rule-bearing lines of 47, with the all-lines score landing on
#: 14/47 = 0.2979. This fixture keeps that shape rather than its size: 4 of 17,
#: which is 0.2353 all-lines and 4 of 5 once commentary is out of the denominator.
#: Only one commentary line here carries a rule word ("objective"), on purpose --
#: a fixture where none did would make the narrowing look cleaner than it is.


def test_commentary_the_reader_rightly_skipped_does_not_count_against_the_page():
    """Refused by ONE line, four times across two sessions, for returning exactly
    what it should: a provision reader is not contracted to transcribe commentary.
    Scoring every sentence line gave 14/47 = 0.2979 against PAGE_HIT 0.3 while
    missing none of the page's 7 rule-bearing lines.
    """
    page = _CONTROL + _COMMENTARY
    # the reader returned every control and none of the commentary
    assert pc.skipped_pages({1: page}, [" ".join(_CONTROL)]) == []
    # and the old all-lines denominator is what refused it
    lines = pc.sentence_lines(page)
    out = set()
    for t in [" ".join(_CONTROL)]:
        out |= pc._grams(pc._WORD.findall(t.lower()))
    hit = [len(pc._grams(w) & out) / len(pc._grams(w)) >= pc.LINE_HIT for w in lines]
    assert sum(hit) / len(lines) < pc.PAGE_HIT      # refused when commentary counts
    assert len(pc.rule_lines(lines)) < len(lines)   # the commentary IS excluded


def test_a_page_whose_controls_are_missing_is_still_skipped():
    """The confusable half. Narrowing the denominator must not make a page of
    controls pass because its commentary came back -- that is the Warringah loss,
    21 pages and 172 printed rules, which this guard exists for.
    """
    page = _CONTROL + _COMMENTARY
    # the reader returned the commentary and dropped every control
    assert pc.skipped_pages({1: page}, [" ".join(_COMMENTARY)]) == [1]
    # all four controls back: read
    assert pc.skipped_pages({1: page}, [" ".join(_CONTROL)]) == []
    # one of four: still skipped, as before
    assert pc.skipped_pages({1: page}, [" ".join(_CONTROL[:1])]) == [1]


def test_a_page_with_no_rule_words_falls_back_to_every_sentence():
    """A page of pure narrative keeps the old scoring, so the re-read trigger is
    no less sensitive there. Such a page cannot refuse a chapter anyway --
    ai_extractor gates the refusal on holds_rules -- but it should still be
    re-read when its text is absent.
    """
    history = ["the subdivision plan was prepared for the auction held in march of that year",
               "the allotments were created from the rear portions of the deeper holdings",
               "a property sales notice appeared in the newspaper on the twentieth of february",
               "the arrangement is recorded in the collection held by the historical society",
               "the original owner is named in the tenders accepted column of the journal"]
    assert pc.rule_lines(pc.sentence_lines(history)) == pc.sentence_lines(history)
    assert pc.skipped_pages({1: history}, ["nothing of the kind appears in this output"]) == [1]
    assert pc.skipped_pages({1: history}, [" ".join(history)]) == []


def test_one_rule_words_definition_serves_both_modules():
    """ai_extractor._rule_bearing_pages and skipped_pages must agree on what a
    rule-bearing line is; two copies would drift."""
    import ai_extractor
    assert ai_extractor._RULE_WORDS is pc.RULE_WORDS
