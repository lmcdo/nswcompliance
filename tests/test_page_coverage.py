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
