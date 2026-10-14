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
def test_overlapping_second_rule_is_dropped_whole_never_trimmed_into_a_fragment():
    """Cross-review: trimming served the later rule without its opening words."""
    lines = L("One.", "Two.", "Three.", "Four.", "Five must be shown.", "Six must be shown.")
    out = sr.build(lines, ans(lines, [rule(0, 3), rule(2, 5)]))
    assert [(r["first"], r["last"]) for r in out["rules"]] == [(0, 3)]
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


def test_a_lead_in_far_away_or_not_ending_in_a_colon_is_rejected():
    """Cross-review: a model lead_in pointing at unrelated text must never be prepended."""
    lines = L("Unrelated background sentence.", "Other text.", "(a) Fences must be 1.2m high.")
    out = sr.build(lines, ans(lines, [rule(2, 2, lead_in=0)]))
    assert out["rules"][0]["text"] == "(a) Fences must be 1.2m high."
    assert out["report"]["lead_ins_rejected"] == 1


def test_items_with_the_same_words_but_different_labels_are_both_kept(monkeypatch):
    """Cross-review: '(a) X' and '(b) X' are two rules, not one line drawn twice."""
    class Ln:
        def __init__(self, page, text):
            self.page, self.text = page, text

    class St:
        def __init__(self, reading, cased):
            self.lines = reading
            self.text = [ln.text for ln in reading]
            self.repeated = set()

    import citation_proof as cp
    import council_quote as cq
    reading = [Ln(1, "(a) Development is prohibited."), Ln(1, "(b) Development is prohibited."),
               Ln(1, "d) A BASIX certificate shall accompany"), Ln(1, "A BASIX certificate shall accompany")]
    monkeypatch.setattr(cp, "read_raw_lines", lambda path: ([], 600))
    monkeypatch.setattr(cp, "both_orders", lambda raw, w: (reading, reading))
    monkeypatch.setattr(cq, "cased_text", lambda path: {})
    monkeypatch.setattr(cq, "Stream", St)
    out = [t for _p, t in sr.chapter_lines("x.pdf")]
    assert out == ["(a) Development is prohibited.", "(b) Development is prohibited.",
                   "d) A BASIX certificate shall accompany"]


def test_picture_pages_without_the_vision_key_refuse_the_chapter(monkeypatch):
    """Cross-review: never return a chapter with its picture pages silently unread."""
    import pytest
    monkeypatch.setattr(sr, "chapter_lines", lambda path: [(1, "Fences must be 1.2m high.")])
    monkeypatch.setattr(sr, "ask", lambda text: {"headings": [], "rules": []})
    monkeypatch.setattr(sr, "picture_pages", lambda path, pages: [1])
    monkeypatch.setattr(sr, "window_pdf", lambda path, pages: (path, 0))
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="MISTRAL_API_KEY"):
        sr.read_chapter("x.pdf", (1, 1))


def test_an_uncovered_obligation_line_is_reread_and_then_included(monkeypatch):
    """Cross-review: a rule line in no rule must not pass silently; one re-read names it, then it is in a rule."""
    lines = L("Fences must be 1.2m high.", "Driveways must be 3m wide at the boundary.")
    first = ans(lines, [rule(0, 0)])
    monkeypatch.setattr(sr, "ask", lambda text: {"headings": [], "rules": [rule(0, 0), rule(1, 1)]})
    out = sr.recover_uncovered(lines, first, sr.build(lines, first))
    assert [r["text"] for r in out["rules"]] == ["Fences must be 1.2m high.", "Driveways must be 3m wide at the boundary."]
    assert out["report"]["reread_pieces"] == 1


def test_a_labelled_rule_line_still_uncovered_after_the_reread_is_added_by_the_program(monkeypatch):
    """City of Sydney 2: '(a) Development must achieve ...' left out twice; it is copied in, not lost."""
    lines = L("Fences must be 1.2m high.", "(a) Development must achieve and satisfy the outcomes expressed in",
              "the character statement.")
    first = ans(lines, [rule(0, 0)])
    monkeypatch.setattr(sr, "ask", lambda text: {"headings": [], "rules": [rule(0, 0)]})
    out = sr.recover_uncovered(lines, first, sr.build(lines, first))
    added = [r for r in out["rules"] if r.get("source") == "added_by_program"]
    assert [r["text"] for r in added] == [
        "(a) Development must achieve and satisfy the outcomes expressed in\nthe character statement."]
    assert out["report"]["uncovered"] == 0


def test_a_rule_worded_sentence_outside_any_controls_heading_is_kept_whole(monkeypatch):
    """City of Sydney locality statements: binding prose under no Controls heading (pilot: 135 lines lost)."""
    lines = L("Fences must be 1.2m high.", "Victorian and Federation terraces and other contributory buildings",
              "are to be retained to preserve the streetscape.")
    first = ans(lines, [rule(0, 0)])
    monkeypatch.setattr(sr, "ask", lambda text: {"headings": [], "rules": [rule(0, 0)]})
    out = sr.recover_uncovered(lines, first, sr.build(lines, first))
    added = [r for r in out["rules"] if r.get("source") == "added_by_program"]
    assert [r["text"] for r in added] == ["Victorian and Federation terraces and other contributory buildings\n"
                                          "are to be retained to preserve the streetscape."]
    assert added[0]["label"] == "control"


def test_an_is_to_sentence_with_any_verb_is_kept_as_a_control(monkeypatch):
    """City of Sydney 2.x: 'The area is to maintain its low scale ...' -- 31 lines R2 caught (pilot 2026-10-14)."""
    lines = L("Fences must be 1.2m high.", "The area is to maintain its low scale residential character below",
              "the tree canopy.", "The park is to the north of the railway line and the station.")
    first = ans(lines, [rule(0, 0)])
    monkeypatch.setattr(sr, "ask", lambda text: {"headings": [], "rules": [rule(0, 0)]})
    out = sr.recover_uncovered(lines, first, sr.build(lines, first))
    added = [r for r in out["rules"] if r.get("source") == "added_by_program"]
    assert [(r["label"], r["text"]) for r in added] == [
        ("control", "The area is to maintain its low scale residential character below\nthe tree canopy.")]


def test_a_contents_page_line_is_never_added(monkeypatch):
    lines = L("Fences must be 1.2m high.", "premises - to be addressed in the POM.................................. 19")
    first = ans(lines, [rule(0, 0)])
    monkeypatch.setattr(sr, "ask", lambda text: {"headings": [], "rules": [rule(0, 0)]})
    out = sr.recover_uncovered(lines, first, sr.build(lines, first))
    assert len(out["rules"]) == 1


def test_a_label_printed_beside_the_text_becomes_the_rule_number():
    """Marrickville 9.8.5.1: 'C1' sits on its own line in the margin beside 'Development must be massed ...'."""
    lines = L("9.8.5.1 76 Wilford Street, Newtown", "C1", "Development must be massed as follows:")
    out = sr.build(lines, ans(lines, [rule(2, 2)], headings=[(0, 2)]))
    assert out["rules"][0]["code"] == "9.8.5.1 C1"


def test_a_nothing_applies_line_under_a_heading_is_kept_as_a_note():
    lines = L("9.8.3 Heritage Conservation Areas (HCAs)", "There are no Heritage Conservation Areas in the precinct.",
              "9.8.4 Precinct-specific planning controls", "Nil")
    out = sr.build(lines, ans(lines, [], headings=[(0, 2), (2, 2)]))
    assert [(r["label"], r["text"]) for r in out["rules"]] == [
        ("note", "There are no Heritage Conservation Areas in the precinct."), ("note", "Nil")]


def test_a_numbered_line_is_a_heading_even_when_the_model_misses_it():
    lines = L("9.8.5.1 76 Wilford Street, Newtown", "C4 The residential component must be no greater than 70 percent.")
    out = sr.build(lines, ans(lines, [rule(1, 1)]))
    assert out["rules"][0]["code"] == "9.8.5.1 C4"


def test_an_item_under_a_labelled_lead_in_carries_that_label():
    lines = L("9.8.5.1 76 Wilford Street, Newtown", "C2 Development must ensure:",
              "i. Any common building entries are accessed off Wilford Street;")
    out = sr.build(lines, ans(lines, [rule(2, 2, lead_in=1)]))
    assert out["rules"][0]["code"] == "9.8.5.1 C2 i"
    assert out["rules"][0]["text"].startswith("C2 Development must ensure:")


def test_an_item_whose_lead_in_has_a_margin_label_carries_it():
    lines = L("9.8.5.1 76 Wilford Street, Newtown", "C1", "Development must be massed as follows:",
              "i. Basement mass may cover the full site area.")
    out = sr.build(lines, ans(lines, [rule(3, 3, lead_in=2)]))
    assert out["rules"][0]["code"] == "9.8.5.1 C1 i"


def test_a_rule_started_on_its_heading_title_and_label_starts_after_them():
    """Marrickville 9.8.5.1 read 3: the model began C1 at '9.8.5.1 76 Wilford Street, Newtown'."""
    lines = L("9.8.5.1 76 Wilford Street, Newtown", "Massing", "C1", "Development must be massed as follows:",
              "i. Basement mass may cover the full site area.")
    out = sr.build(lines, ans(lines, [rule(0, 4)]))
    r = out["rules"][0]
    assert r["code"] == "9.8.5.1 C1"
    assert r["title"] == "Massing"
    assert r["text"] == "Development must be massed as follows:\ni. Basement mass may cover the full site area."


def test_a_control_returned_whole_is_split_at_its_items_the_same_as_when_returned_split():
    lines = L("9.8.5.1 76 Wilford Street, Newtown", "C2", "Development must ensure:",
              "i. Any common building entries are accessed off Wilford Street;",
              "ii. Basement car parking has car access from Phillip Lane;", "a. which is sealed; and",
              "iii. There is no entry off Gladstone Lane.")
    whole = sr.build(lines, ans(lines, [rule(2, 6)]))
    split = sr.build(lines, ans(lines, [rule(3, 3, lead_in=2), rule(4, 5, lead_in=2), rule(6, 6, lead_in=2)]))
    for out in (whole, split):
        assert [r["code"] for r in out["rules"]] == ["9.8.5.1 C2 i", "9.8.5.1 C2 ii", "9.8.5.1 C2 iii"]
        assert out["rules"][1]["text"] == ("Development must ensure:\nii. Basement car parking has car access from "
                                           "Phillip Lane;\na. which is sealed; and")


def test_a_letter_prefixed_section_number_is_a_heading_and_files_the_rule():
    """Leichhardt C2: 'C2.2.1.4 Booth Street ...' numbers the precinct its rules are linked to."""
    lines = L("C2.2.1.4 Booth Street Distinctive Neighbourhood", "Controls",
              "C11 The development to a primary street frontage must respect the existing character.")
    out = sr.build(lines, ans(lines, [rule(2, 2)]))
    assert out["rules"][0]["code"] == "C2.2.1.4 C11"


def test_a_plain_instruction_under_a_controls_heading_left_out_is_added(monkeypatch):
    """Leichhardt C2 p21: 'Contain upper floors within the roof form ...' has no must/shall."""
    lines = L("C2.2.1.4 Booth Street", "Controls", "C1 Fences must be 1.2m high.",  # noqa: zone-codes (DCP Part codes, not zones)
              "Contain upper floors within the roof form, so as not to be visible from the street frontage.")
    first = ans(lines, [rule(2, 2)])
    monkeypatch.setattr(sr, "ask", lambda text: {"headings": [], "rules": [rule(2, 2)]})
    out = sr.recover_uncovered(lines, first, sr.build(lines, first))
    assert any(r["text"].startswith("Contain upper floors") for r in out["rules"])


def test_background_text_under_a_character_heading_is_not_added(monkeypatch):
    lines = L("C2.2.1.4 Booth Street", "Existing Character",
              "The area retains a strong industrial character with many warehouses.", "Controls",
              "C1 Fences must be 1.2m high.")
    first = ans(lines, [rule(4, 4)])
    monkeypatch.setattr(sr, "ask", lambda text: {"headings": [], "rules": [rule(4, 4)]})
    out = sr.recover_uncovered(lines, first, sr.build(lines, first))
    assert [r["text"] for r in out["rules"]] == ["C1 Fences must be 1.2m high."]


def test_a_part_code_in_a_running_header_is_recognised():
    """Waverley DCP pages carry 'Bondi Junction      E1' at the top; the Part is nowhere else on the page."""
    assert sr._HEADER_PART.match("Bondi Junction      E1 ").group("b") == "E1"
    assert sr._HEADER_PART.match("WAVERLEY DEVELOPMENT CONTROL PLAN 2022") is None
