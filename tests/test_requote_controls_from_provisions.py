"""A control's quote is replaced only by the council's own words from a CURRENT rule, holding the control's number, never shared across values."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import requote_controls_from_provisions as r  # noqa: E402

RULE = {"id": 1, "page": 12, "chapter": "ch-a", "text": "# 3.2 Setbacks\nA minimum 6m rear setback applies.\nSide setbacks to external walls should be a minimum of 900mm.\nMaximum 15 metres in height."}


def ctl(cid=10, vmin=None, vmax=None, text="", ct="rear_setback", dt="dwelling_house"):
    return {"id": cid, "control_type": ct, "dev_type": dt, "value_min": vmin, "value_max": vmax, "unit": "m", "condition": None, "source_text": text,
            "pdf_page": 1, "provision_id": None, "source_chapter_key": "ch-a"}


def test_an_exact_quote_holding_the_number_is_proven():
    assert r.prove("A minimum 6m rear setback applies.", RULE["text"], ctl(vmin=6)) == (True, "proven")


def test_whitespace_differences_are_ignored_but_words_are_not():
    assert r.prove("A  minimum 6m   rear setback applies.", RULE["text"], ctl(vmin=6))[0] is True
    assert r.prove("A minimum 5m rear setback applies.", RULE["text"], ctl(vmin=5))[0] is False


def test_a_number_that_is_only_inside_a_bigger_number_is_not_the_number():
    """5 must not be satisfied by the 15 in 'Maximum 15 metres in height'."""
    ok, why = r.prove("Maximum 15 metres in height.", RULE["text"], ctl(vmax=5, ct="max_height"))
    assert ok is False and "number" in why


def test_a_quote_that_does_not_hold_the_control_number_is_refused():
    ok, why = r.prove("Side setbacks to external walls should be a minimum of 900mm.", RULE["text"], ctl(vmin=1.5))
    assert ok is False and "number" in why


def test_an_objective_is_not_a_control():
    t = "To support the plan 2022-2032 minimum 29% LGA canopy target."
    ok, why = r.prove(t, t, ctl(vmin=29, ct="tree_canopy_min"))
    assert ok is False and "objective" in why


def test_an_empty_too_short_or_too_long_quote_is_refused():
    for q in (None, "", "6m", "x" * 401):
        assert r.prove(q, RULE["text"], ctl(vmin=6))[0] is False


def test_the_same_quote_for_controls_of_different_values_is_ambiguous_but_not_for_the_same_value():
    a = {"quote": "Maximum 0 0.4 0.7 1.2", "ctl": ctl(1, vmin=0)}
    b = {"quote": "Maximum 0 0.4 0.7 1.2", "ctl": ctl(2, vmin=0.4)}
    c = {"quote": "Maximum 0 0.4 0.7 1.2", "ctl": ctl(3, vmin=0)}
    assert r.ambiguous({1: a, 2: b}) == {1, 2}
    assert r.ambiguous({1: a, 3: c}) == set()


def test_plan_uses_a_reader_answer_and_drops_one_that_is_not_in_the_rule():
    good = {"control_id": 10, "provision_id": 1, "quote": "A minimum 6m rear setback applies."}
    forged = {"control_id": 11, "provision_id": 1, "quote": "A minimum 7m rear setback applies."}
    planned, rej = r.plan([ctl(10, vmin=6), ctl(11, vmin=7)], [RULE], {10: good, 11: forged})
    assert set(planned) == {10} and planned[10]["by"] == "reader" and planned[10]["page"] == 12
    assert "substring" in rej[11]


def test_a_readers_none_stands_the_program_does_not_overrule_it():
    planned, rej = r.plan([ctl(10, vmin=6)], [RULE], {10: {"control_id": 10, "provision_id": None, "quote": None}})
    assert planned == {} and rej[10] == "reader gave none"


def test_a_provision_the_reader_names_that_is_not_a_current_rule_of_the_council_is_not_used():
    answer = {"control_id": 10, "provision_id": 999, "quote": "A minimum 6m rear setback applies."}
    planned, rej = r.plan([ctl(10, vmin=6)], [RULE], {10: answer})
    assert planned == {} and rej[10] == "reader gave none"


def test_the_program_proposes_only_when_the_best_unit_clearly_wins():
    prov = {"id": 2, "page": 3, "chapter": "ch-a", "text": "A minimum 6m rear setback applies to dwelling houses.\nA minimum 6m rear setback applies to dwelling houses in zone R3."}
    planned, rej = r.plan([ctl(10, vmin=6, text="rear setback 6m dwelling houses")], [prov], {})
    assert 10 not in planned          # two near-identical candidates: no clear winner, so it asks a reader
    planned, rej = r.plan([ctl(10, vmin=6, text="minimum rear setback 6m")], [RULE], {})
    assert planned[10]["by"] == "program" and "6m rear setback" in planned[10]["quote"]


def test_a_control_with_no_number_gets_no_program_proposal():
    planned, rej = r.plan([ctl(10, text="rear setback")], [RULE], {})
    assert planned == {} and rej[10] == "no proposal"


def test_release_only_frees_holds_the_quote_check_wrote():
    ok = r.HOLD_REASON.fullmatch
    assert ok("quote not word-for-word in source PDF (whole-PDF check 2026-10-29)")
    assert ok("quote not proven word for word on the cited PDF page (wrong_page)")
    assert ok("chapter_pdf_changed")
    assert not ok("Spot check 2026-09-13 (Claude, at the owner's request): STAYS HIDDEN")
    assert not ok("")


def test_a_persons_note_that_merely_starts_like_a_machine_reason_is_not_released():
    assert not r.HOLD_REASON.fullmatch("Quote not applicable to this control; keep hidden")
    assert not r.HOLD_REASON.fullmatch("quote not word-for-word in source PDF (whole-PDF check 2026-10-29) AND keep hidden, owner")
    assert not r.HOLD_REASON.fullmatch("chapter_pdf_changed, but see Waverley note")


def test_a_labelled_objective_is_still_an_objective():
    for q in ("O1 To support the minimum 29% canopy target.", "(a) To support the minimum 29% canopy target.", "# 3.2 O1 (a) To support the minimum 29% target.",
              "3.2.1 The objectives of this part are to keep 29% canopy.", "- To keep 29% canopy."):
        assert r.prove(q, q, ctl(vmin=29, ct="tree_canopy_min"))[0] is False, q
    assert r.prove("O1 minimum 29% canopy applies", "O1 minimum 29% canopy applies", ctl(vmin=29, ct="tree_canopy_min"))[0] is True


def test_a_rule_from_another_chapter_is_not_used_even_if_the_words_and_number_match():
    other = dict(RULE, id=2, chapter="ch-b")
    answer = {"control_id": 10, "provision_id": 2, "quote": "A minimum 6m rear setback applies."}
    planned, rej = r.plan([ctl(10, vmin=6)], [other], {10: answer})
    assert planned == {} and "own chapter" in rej[10]
    planned, rej = r.plan([dict(ctl(10, vmin=6), source_chapter_key=None)], [RULE], {10: dict(answer, provision_id=1)})
    assert planned == {} and "own chapter" in rej[10]


def test_a_quote_already_held_by_another_current_control_of_a_different_value_is_not_written():
    quote = "A minimum 6m rear setback applies."
    answer = {"control_id": 10, "provision_id": 1, "quote": quote}
    already_proven = [{"id": 99, "value_min": 0.4, "value_max": None, "source_text": quote}]
    planned, rej = r.plan([ctl(10, vmin=6)], [RULE], {10: answer}, already_proven)
    assert planned == {} and "already holds this quote" in rej[10]
    same_value = [{"id": 99, "value_min": 6, "value_max": None, "source_text": quote}]
    planned, rej = r.plan([ctl(10, vmin=6)], [RULE], {10: answer}, same_value)
    assert 10 in planned


class _FakeCur:
    """A cursor holding one releasable row whose review_reason is changed by a person between planning and the update."""

    def __init__(self, reason_now):
        self.reason_now, self.rowcount, self.sql = reason_now, 0, []

    def execute(self, sql, args=()):
        self.sql.append(sql)
        if sql.lstrip().startswith("SELECT"):
            self.rows = [(7, "chapter_pdf_changed")]
        else:                                            # the guarded UPDATE only matches while the reason is still the one planned on
            guarded = "review_reason IS NOT DISTINCT FROM" in sql
            self.rowcount = 1 if (not guarded or args[-1] == self.reason_now) else 0

    def fetchall(self):
        return self.rows


class _FakeConn:
    def __init__(self, cur):
        self.c, self.committed, self.rolled = cur, False, False

    def cursor(self):
        return self.c

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled = True


class _Args:
    council, apply = "waverley", True


def test_release_aborts_and_writes_nothing_when_a_person_changed_the_reason_after_planning(tmp_path, monkeypatch):
    monkeypatch.setattr(r, "ROOT", tmp_path)
    (tmp_path / "data" / "db_rollback_backups").mkdir(parents=True)
    conn = _FakeConn(_FakeCur("Owner: keep hidden"))
    assert r._release(conn, _Args) == 1 and conn.rolled and not conn.committed


def test_release_commits_when_nothing_changed(tmp_path, monkeypatch):
    monkeypatch.setattr(r, "ROOT", tmp_path)
    (tmp_path / "data" / "db_rollback_backups").mkdir(parents=True)
    conn = _FakeConn(_FakeCur("chapter_pdf_changed"))
    assert r._release(conn, _Args) == 0 and conn.committed and not conn.rolled
