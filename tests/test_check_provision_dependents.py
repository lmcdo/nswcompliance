"""The dependents check fails on a dead pointer in a live table, ignores history tables, and never treats a column it could not check as clean."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import pytest  # noqa: E402

import check_provision_dependents as c  # noqa: E402


def row(table="project_brief_rows", col="provision_id", rows=100, dead=0, error=None):
    r = {"table": table, "column": col, "rows": rows, "dead": dead}
    if error:
        r["error"] = error
    return r


def test_a_dead_pointer_in_a_live_table_fails():
    ok, lines = c.verdict([row(dead=3)])
    assert ok is False and "DEAD" in lines[0] and "3 dead of 100" in lines[0]


def test_no_dead_pointers_passes():
    ok, lines = c.verdict([row(dead=0), row(table="da_responses", dead=0)])
    assert ok is True and lines == []


def test_a_history_table_with_dead_pointers_is_shown_but_does_not_fail():
    ok, lines = c.verdict([row(table="dcp_setback_controls_backup_20260803_item3", dead=5), row(table="provision_versions", dead=9)])
    assert ok is True and all(ln.startswith("history") for ln in lines)


def test_a_column_that_could_not_be_checked_fails_never_reads_as_clean():
    ok, lines = c.verdict([row(error="operator does not exist")])
    assert ok is False and lines[0].startswith("NOT CHECKED")


def test_a_live_table_with_a_dead_pointer_still_fails_when_history_tables_are_clean():
    ok, _ = c.verdict([row(table="provision_versions", dead=0), row(dead=1)])
    assert ok is False


def test_history_table_names():
    for t in ("x_backup_2026", "provision_change_log", "provision_versions", "foo_archived"):
        assert c.is_history(t), t
    for t in ("project_brief_rows", "da_responses", "dcp_setback_controls"):
        assert not c.is_history(t), t


def test_integer_ids_join_directly_and_text_ids_join_on_text():
    assert c.join_on('"provision_id"', "integer") == 'p.id = x."provision_id"'
    assert c.join_on('"provision_id"', "bigint") == 'p.id = x."provision_id"'
    assert c.join_on('"provision_id"', "text") == 'p.id::text = x."provision_id"::text'
    assert c.join_on('"rule_id"', "character varying") == 'p.id::text = x."rule_id"::text'


def test_a_catalogue_name_that_is_not_a_plain_identifier_is_refused():
    for bad in ('x"; drop table y; --', "Robert'); DROP", "a b", ""):
        with pytest.raises(ValueError):
            c.safe_ident(bad)
    assert c.safe_ident("project_brief_rows") == '"project_brief_rows"'


class _Cur:
    def __init__(self, fail_on):
        self.fail_on, self.sql, self.i = fail_on, [], 0

    def execute(self, sql, args=()):
        self.sql.append(sql)
        if self.fail_on and self.fail_on in sql:
            raise RuntimeError("boom")

    def fetchone(self):
        return (10, 2)


class _Conn:
    def __init__(self, cur):
        self._c, self.rolled = cur, 0

    def cursor(self):
        return self._c

    def rollback(self):
        self.rolled += 1


def test_sweep_reports_a_failing_column_as_an_error_row_and_carries_on(monkeypatch):
    monkeypatch.setattr(c, "columns", lambda cur: [("good_table", "provision_id", "integer"), ("bad_table", "provision_id", "integer")])
    conn = _Conn(_Cur(fail_on='"bad_table"'))
    rows = c.sweep(conn, "waverley")
    assert [r["table"] for r in rows] == ["good_table", "bad_table"]
    assert rows[0]["dead"] == 2 and "error" in rows[1] and conn.rolled == 1


def test_sweep_never_writes():
    cur = _Cur(None)
    monkeypatch_cols = [("t", "provision_id", "integer")]
    orig = c.columns
    c.columns = lambda cur: monkeypatch_cols
    try:
        c.sweep(_Conn(cur), None)
    finally:
        c.columns = orig
    assert all(s.lstrip().upper().startswith("SELECT") for s in cur.sql)
