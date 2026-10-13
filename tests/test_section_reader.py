"""Pure-function tests for scripts/section_reader.py: pieces, numbered, build.

prior-art-checked: new module section_reader; pure functions only, no model or PDF.

`lines` is a list of (page, text); `answers` is a list of ((ctx_start, start, end), model_answer_dict).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import section_reader as sr  # noqa: E402


def L(*texts, page=1):
    return [(page, t) for t in texts]


def rule(first, last, label="control", lead_in=None):
    return {"first": first, "last": last, "label": label, "lead_in": lead_in}


def ans(lines, rules, headings=()):
    d = {"headings": [{"line": n, "level": k} for n, k in headings], "rules": rules}
    return [((0, 0, len(lines)), d)]


# 1
def test_rule_text_is_exactly_the_joined_lines_first_to_last():
    lines = L("Intro line.", "Buildings must be set", "back 3m from the", "boundary.", "Other text.")
    out = sr.build(lines, ans(lines, [rule(1, 3)]))
    assert len(out["rules"]) == 1
    assert out["rules"][0]["text"] == "Buildings must be set\nback 3m from the\nboundary."


# 2
def test_rule_outside_its_piece_range_is_ignored():
    lines = L("A one.", "B two.", "C three.", "D four.", "E five.")
    answers = [((0, 1, 3), {"headings": [], "rules": [rule(0, 1), rule(2, 3), rule(1, 2)]})]
    out = sr.build(lines, answers)
    assert [(r["first"], r["last"]) for r in out["rules"]] == [(1, 2)]


def test_rule_starting_on_a_heading_line_is_ignored():
    lines = L("4.3 Parking", "Cars must park on site.")
    out = sr.build(lines, ans(lines, [rule(0, 1), rule(1, 1)], headings=[(0, 1)]))
    assert [(r["first"], r["last"]) for r in out["rules"]] == [(1, 1)]


# 3
def test_overlapping_second_rule_is_trimmed_to_start_after_the_first():
    lines = L("One.", "Two.", "Three.", "Four.", "Five.", "Six.")
    out = sr.build(lines, ans(lines, [rule(0, 3), rule(2, 5)]))
    assert [(r["first"], r["last"]) for r in out["rules"]] == [(0, 3), (4, 5)]
    assert out["rules"][1]["text"] == "Five.\nSix."
    assert out["report"]["overlaps"] == 1


def test_rule_fully_inside_an_earlier_rule_is_dropped_and_counted():
    lines = L("One.", "Two.", "Three.", "Four.", "Five.")
    out = sr.build(lines, ans(lines, [rule(0, 4), rule(1, 2)]))
    assert [(r["first"], r["last"]) for r in out["rules"]] == [(0, 4)]
    assert out["report"]["overlaps"] == 1


# 4
def test_lowercase_start_after_unfinished_rule_is_joined_to_it():
    lines = L("Buildings must provide a setback of", "at least 3m from the boundary.")
    out = sr.build(lines, ans(lines, [rule(0, 0), rule(1, 1)]))
    assert len(out["rules"]) == 1
    assert out["rules"][0]["text"] == "\n".join(t for _p, t in lines)
    assert out["rules"][0]["last"] == 1
    assert out["report"]["joined_mid_sentence"] == 1


def test_where_condition_after_unfinished_rule_is_joined_to_it():
    lines = L("Fences must be low", "Where the lot is a corner lot, 1m.")
    out = sr.build(lines, ans(lines, [rule(0, 0), rule(1, 1)]))
    assert len(out["rules"]) == 1
    assert out["report"]["joined_mid_sentence"] == 1


def test_lowercase_start_is_not_joined_when_previous_rule_ends_with_full_stop():
    lines = L("The setback is 3m.", "where the lot is a corner lot, 1m.")
    out = sr.build(lines, ans(lines, [rule(0, 0), rule(1, 1)]))
    assert len(out["rules"]) == 2
    assert out["report"]["joined_mid_sentence"] == 0


# 5
def test_lead_in_line_is_prefixed_to_each_item_rule():
    lines = L("Development must include:", "(a) a bin store", "(b) a clothes line")
    out = sr.build(lines, ans(lines, [rule(1, 1, lead_in=0), rule(2, 2, lead_in=0)]))
    assert len(out["rules"]) == 2
    for r in out["rules"]:
        assert r["text"].startswith("Development must include:\n")
    assert out["rules"][0]["text"].endswith("(a) a bin store")
    assert out["rules"][1]["text"].endswith("(b) a clothes line")
    assert out["report"]["lead_ins"] == 1


def test_lead_in_also_returned_as_its_own_one_line_rule_is_removed():
    lines = L("Development must include:", "(a) a bin store", "(b) a clothes line")
    out = sr.build(lines, ans(lines, [rule(0, 0), rule(1, 1, lead_in=0), rule(2, 2, lead_in=0)]))
    assert [(r["first"], r["last"]) for r in out["rules"]] == [(1, 1), (2, 2)]
    assert all(r["text"].startswith("Development must include:") for r in out["rules"])


def test_program_finds_lead_in_when_model_gives_null():
    lines = L("Development must include:", "(a) a bin store", "(b) a clothes line")
    out = sr.build(lines, ans(lines, [rule(1, 1), rule(2, 2)]))
    assert out["rules"][0]["lead_in"] == 0
    assert out["rules"][0]["text"].startswith("Development must include:\n(a)")


# 6
def test_section_path_joins_level_1_and_level_2_headings_and_code_uses_item_label():
    lines = L("Part 4 Residential", "4.3 Parking", "C1 Car parking must be provided on site.")
    out = sr.build(lines, ans(lines, [rule(2, 2)], headings=[(0, 1), (1, 2)]))
    r = out["rules"][0]
    assert r["section"] == "Part 4 Residential > 4.3 Parking"
    assert r["code"] == "4.3 C1"
    assert r["title"] == "4.3 Parking"


def test_new_level_2_heading_replaces_the_old_level_2_heading():
    lines = L("Part 4 Residential", "4.3 Parking", "Cars must park on site.",
              "4.4 Siting", "Buildings must be set back.")
    out = sr.build(lines, ans(lines, [rule(2, 2), rule(4, 4)], headings=[(0, 1), (1, 2), (3, 2)]))
    assert out["rules"][0]["section"] == "Part 4 Residential > 4.3 Parking"
    assert out["rules"][1]["section"] == "Part 4 Residential > 4.4 Siting"


# 7
def test_uncovered_lists_rule_worded_line_in_no_rule_and_not_a_heading():
    lines = L("4.3 Parking", "Car parking must be provided on site.",
              "Visitors must park off the street here.", "4.4 Residents must always park here ok",
              "Short must line.")
    out = sr.build(lines, ans(lines, [rule(1, 1)], headings=[(0, 2), (3, 2)]))
    idx = [i for i, _p, _t in out["uncovered"]]
    assert idx == [2]
    assert out["report"]["uncovered"] == 1


# 8
def test_pieces_cover_every_line_exactly_once_with_context_of_12():
    lines = L(*["some plain text line"] * 500)
    ps = sr.pieces(lines, 220)
    assert ps[0][1] == 0
    for (_c, _s, e), (_c2, s2, _e2) in zip(ps, ps[1:]):
        assert e == s2
    assert ps[-1][2] == 500
    covered = [i for _c, s, e in ps for i in range(s, e)]
    assert covered == list(range(500))
    for ctx, start, _e in ps:
        assert ctx == max(0, start - 12)


def test_pieces_cut_before_a_heading_like_line_in_the_last_third_of_the_window():
    texts = ["some plain text line"] * 500
    texts[180] = "5.2 Landscaping"
    ps = sr.pieces(L(*texts), 220)
    assert ps[0] == (0, 0, 180)
    assert ps[1][1] == 180


# 9
def test_numbered_marks_lines_before_start_as_already_read_and_rows_are_indexed():
    lines = [(1, "a"), (1, "b"), (2, "c"), (2, "d"), (3, "e")]
    rows = sr.numbered(lines, 1, 3, 5).split("\n")
    assert rows == ["[1] (already read) p1: b", "[2] (already read) p2: c", "[3] p2: d", "[4] p3: e"]
