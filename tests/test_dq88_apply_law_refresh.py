"""The law refresh applies a reviewed plan only to rows still holding the text it was built from, and continues a row's version history."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import pytest  # noqa: E402

import dq88_apply_law_refresh as ap  # noqa: E402
import dq88_refresh_2026_10_10 as base  # noqa: E402


class Cur:
    """A recording cursor: `row` is what the SELECT of the stored text returns, `versions` the existing history."""

    def __init__(self, row=("old text", True, True), versions=None):
        self.row, self.versions, self.sql, self._last = row, versions, [], None

    def execute(self, sql, args=()):
        self.sql.append((sql, args))
        self._last = sql

    def fetchone(self):
        q = self._last
        if "SELECT provision_text, is_current" in q:
            assert "FOR UPDATE" in q          # the guard must lock the row it checks
            return self.row
        if "SELECT provision_text, created_at" in q:
            return ("old text", None, None)
        if "FROM provision_versions" in q:
            return self.versions
        return (99,)


class Conn:
    def __init__(self, cur):
        self._c, self.committed, self.rolled = cur, 0, 0

    def cursor(self):
        return self._c

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled += 1


def plan(tmp_path, **kw):
    row = {"id": 5, "sepp": "housing", "epi": "epi-x", "baseline": "2026-09-15", "action": "REPLACE", "old_text": "old text", "new_text": "new text",
           "verbatim_in_law": True}
    row.update(kw)
    p = tmp_path / "plan.json"
    p.write_text(json.dumps([row]), encoding="utf-8")
    return str(p)


def test_a_dry_run_rolls_back_and_an_apply_commits(tmp_path):
    c = Conn(Cur())
    ap.run(c, False, plan(tmp_path))
    assert (c.rolled, c.committed) == (1, 0)
    c = Conn(Cur())
    ap.run(c, True, plan(tmp_path))
    assert (c.rolled, c.committed) == (0, 1)


def test_a_row_whose_stored_text_changed_is_refused(tmp_path):
    with pytest.raises(SystemExit):
        ap.run(Conn(Cur(row=("someone edited this", True))), True, plan(tmp_path))


def test_a_row_that_is_no_longer_current_is_refused(tmp_path):
    with pytest.raises(SystemExit):
        ap.run(Conn(Cur(row=("old text", False))), True, plan(tmp_path))


def test_an_unknown_action_and_a_replace_without_text_are_refused(tmp_path):
    with pytest.raises(SystemExit):
        ap.run(Conn(Cur()), True, plan(tmp_path, action="DELETE"))
    with pytest.raises(SystemExit):
        ap.run(Conn(Cur()), True, plan(tmp_path, new_text=""))


def test_a_row_with_earlier_history_continues_its_version_numbers():
    cur = Cur(versions=(41, 2))
    base.version(cur, 5, "new", "src", "ref", "why", __import__("datetime").datetime.now(), "note", "det")
    inserts = [a for s, a in cur.sql if "INSERT INTO provision_versions" in s]
    assert len(inserts) == 1 and inserts[0][1] == 3          # only the new version, numbered 3
    updates = [a for s, a in cur.sql if s.startswith("UPDATE regulatory_provisions")]
    assert updates[0][2] == 3                                  # version_count follows


def test_a_replacement_not_checked_against_the_law_is_refused_and_a_checked_one_is_proved(tmp_path):
    with pytest.raises(SystemExit):
        ap.run(Conn(Cur()), True, plan(tmp_path, verbatim_in_law=False))
    cur = Cur()
    ap.run(Conn(cur), True, plan(tmp_path))
    proofs = [a for s, a in cur.sql if "citation_status = 'proven'" in s]
    assert len(proofs) == 1 and proofs[0][0].endswith("#in-force-2026-11-25") and proofs[0][2] == 5
    cur = Cur()
    ap.run(Conn(cur), True, plan(tmp_path, action="RETIRE"))
    assert not [1 for s, a in cur.sql if "citation_status" in s]          # a retired row needs no proof


def test_a_row_that_belongs_to_another_instrument_is_refused(tmp_path):
    with pytest.raises(SystemExit):
        ap.run(Conn(Cur(row=("old text", True, False))), True, plan(tmp_path))
    with pytest.raises(SystemExit):
        ap.run(Conn(Cur()), True, plan(tmp_path, sepp="not_a_sepp"))


def test_continuing_history_closes_the_previous_version():
    cur = Cur(versions=(41, 2))
    base.version(cur, 5, "new", "src", "ref", "why", __import__("datetime").datetime.now(), "note", "det")
    closes = [a for s, a in cur.sql if s.startswith("UPDATE provision_versions SET effective_to")]
    assert len(closes) == 1 and closes[0][1] == 41


def test_a_row_with_no_history_gets_v1_and_v2():
    cur = Cur(versions=None)
    base.version(cur, 5, "new", "src", "ref", "why", __import__("datetime").datetime.now(), "note", "det")
    assert len([1 for s, a in cur.sql if "INSERT INTO provision_versions" in s]) == 2


def test_the_shipped_plan_is_well_formed():
    plan_rows = json.load(open(ap.PLAN, encoding="utf-8"))
    assert plan_rows and all(r["action"] in ap.ACTIONS for r in plan_rows)
    assert all(r.get("new_text") and r.get("verbatim_in_law") is True for r in plan_rows if r["action"] == "REPLACE")
    assert len({r["id"] for r in plan_rows}) == len(plan_rows)
    assert all(r["new_text"] != r["old_text"] for r in plan_rows if r["action"] == "REPLACE")
