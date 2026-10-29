"""A DCP number rule is served only when its quote is the council's exact words on the cited page.

prior-art-checked: new tests for the new scripts/dcp_quote_status.py and migration 120;
tests/test_dcp_citation_status.py covers the clause-number verdict, a different column.
"""
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import dcp_quote_status as Q  # noqa: E402

RULE = "C2 35% of the site area is deep soil landscaped area"
PAGES = ["Contents and objectives", "Side setbacks C1 The minimum side setback is 900mm.",
         f"Landscaping {RULE} with the exception of Wolseley Road."]


def test_quote_on_its_page_is_verbatim():
    assert Q.classify(RULE, PAGES, 3) == "verbatim"


def test_case_spacing_and_curly_punctuation_do_not_matter():
    assert Q.classify("c2  35%  OF the site’ area is deep-soil landscaped area", PAGES, 3) == "verbatim"


def test_quote_split_over_a_page_break_is_verbatim():
    pages = ["... C1 The minimum rear setback", "is 6 metres. C2 ..."]  # noqa: zone-codes  (clause labels C1/C2, not zones)
    assert Q.classify("The minimum rear setback is 6 metres", pages, 1) == "verbatim"
    assert Q.classify("The minimum rear setback is 6 metres", pages, 2) == "verbatim"


def test_quote_on_another_page_is_wrong_page_not_verbatim():
    assert Q.classify(RULE, PAGES, 1) == "wrong_page"


def test_one_changed_number_is_not_found():
    # The May 2026 summaries were close to the council's words but not the same.
    assert Q.classify("C2 30% of the site area is deep soil landscaped area", PAGES, 3) == "not_found"


def test_a_summary_is_not_found():
    assert Q.classify("Minimum side setback 0.9m (DCP 3.2.3)", PAGES, 2) == "not_found"


@pytest.mark.parametrize("quote,pages,page", [
    (None, PAGES, 3), ("  ", PAGES, 3), (RULE, None, 3), (RULE, PAGES, None),
    (RULE, ["", ""], 1), ("()-", PAGES, 3),
])
def test_missing_inputs_are_no_source(quote, pages, page):
    assert Q.classify(quote, pages, page) == "no_source"


def test_a_page_past_the_end_is_not_verbatim():
    assert Q.classify(RULE, PAGES, 9) == "wrong_page"


def test_only_changed_verdicts_are_written():
    assert Q.changed([(1, "verbatim"), (2, None), (3, "not_found")],
                     {1: "verbatim", 2: "verbatim", 3: "wrong_page"}) == [(2, "verbatim"), (3, "wrong_page")]


def test_an_unknown_verdict_is_refused():
    with pytest.raises(ValueError):
        Q.changed([(1, None)], {1: "close_enough"})


# --- migration 120: the database holds every row that is not proven ----------------------

_REAL = os.environ.get("PYTEST_REAL_DB") == "1" and os.environ.get("DATABASE_URL")


@pytest.fixture
def temp_table():
    """Migration 120's trigger on a temp copy of dcp_setback_controls; always rolled back."""
    if not _REAL:
        pytest.skip("needs PYTEST_REAL_DB=1 and DATABASE_URL (runs in a rolled-back transaction)")
    import psycopg2

    conn = psycopg2.connect(os.environ["DATABASE_URL"], options="-c statement_timeout=30000")
    cur = conn.cursor()
    cur.execute("CREATE TEMP TABLE t_sb (LIKE dcp_setback_controls INCLUDING DEFAULTS) ON COMMIT DROP")
    for col in ("quote_status text", "quote_checked_at timestamptz"):
        cur.execute(f"ALTER TABLE t_sb ADD COLUMN IF NOT EXISTS {col}")
    sql = (ROOT / "migrations" / "120_setback_serve_only_verbatim.sql").read_text(encoding="utf-8")
    body = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
    body = re.sub(r"\b(ON|UPDATE) dcp_setback_controls\b", r"\1 t_sb", body)
    # Never let the migration reach the real table from a test.
    assert "dcp_setback_controls " not in body.replace("dcp_setback_controls_", "") and "UPDATE t_sb" in body
    # A row that is served and unproven BEFORE the migration runs (id 0).
    cur.execute("INSERT INTO t_sb (id, lga, control_type, applicability, is_current, source_text, "
                "pdf_page, needs_review) VALUES (0, 'x', 'front_setback', 'all', true, 'q', 3, false)")
    cur.execute(body)
    try:
        yield cur
    finally:
        conn.rollback()
        conn.close()


def _put(cur, rid, status, needs_review=False):
    cur.execute("INSERT INTO t_sb (id, lga, control_type, applicability, is_current, source_text, "
                "pdf_page, quote_status, needs_review) "
                "VALUES (%s, 'x', 'front_setback', 'all', true, 'q', 3, %s, %s)",
                (rid, status, needs_review))


def _held(cur, rid):
    cur.execute("SELECT needs_review, quote_status, review_reason FROM t_sb WHERE id = %s", (rid,))
    return cur.fetchone()


@pytest.mark.database
def test_an_unproven_row_is_not_served(temp_table):
    for rid, status in [(1, None), (2, "not_found"), (3, "wrong_page"), (4, "no_source")]:
        _put(temp_table, rid, status)
        held, _, why = _held(temp_table, rid)
        assert held is True and "not proven" in why


@pytest.mark.database
def test_a_proven_row_is_served(temp_table):
    _put(temp_table, 5, "verbatim")
    assert _held(temp_table, 5)[0] is False


@pytest.mark.database
def test_changing_the_quote_wipes_the_proof_and_hides_the_row(temp_table):
    _put(temp_table, 6, "verbatim")
    temp_table.execute("UPDATE t_sb SET source_text = 'a summary' WHERE id = 6")
    held, status, _ = _held(temp_table, 6)
    assert (held, status) == (True, None)


@pytest.mark.database
def test_moving_the_page_wipes_the_proof(temp_table):
    _put(temp_table, 7, "verbatim")
    temp_table.execute("UPDATE t_sb SET pdf_page = 4 WHERE id = 7")
    assert _held(temp_table, 7)[:2] == (True, None)


@pytest.mark.database
def test_releasing_an_unproven_row_is_undone(temp_table):
    _put(temp_table, 8, "not_found", needs_review=True)
    temp_table.execute("UPDATE t_sb SET needs_review = false WHERE id = 8")
    assert _held(temp_table, 8)[0] is True


@pytest.mark.database
def test_proving_a_row_does_not_release_it(temp_table):
    _put(temp_table, 9, "not_found", needs_review=True)
    temp_table.execute("UPDATE t_sb SET quote_status = 'verbatim' WHERE id = 9")
    assert _held(temp_table, 9)[0] is True


@pytest.mark.database
def test_restating_an_old_proof_with_a_new_page_does_not_count(temp_table):
    # Writing the same 'verbatim' alongside a page move cannot be told apart from not
    # re-checking at all, so the row is held until dcp_quote_status.py proves the new page.
    _put(temp_table, 10, "verbatim")
    temp_table.execute("UPDATE t_sb SET pdf_page = 4, quote_status = 'verbatim' WHERE id = 10")
    assert _held(temp_table, 10)[:2] == (True, None)


@pytest.mark.database
def test_a_row_served_before_the_migration_is_held_by_it(temp_table):
    held, _, why = _held(temp_table, 0)
    assert held is True and "unchecked" in why


@pytest.mark.database
def test_a_new_quote_cannot_carry_a_proof_in_the_same_statement(temp_table):
    _put(temp_table, 11, "not_found", needs_review=True)
    temp_table.execute("UPDATE t_sb SET source_text = 'a summary', quote_status = 'verbatim', "
                       "needs_review = false WHERE id = 11")
    assert _held(temp_table, 11)[:2] == (True, None)


@pytest.mark.database
def test_moving_a_rule_to_another_council_wipes_the_proof(temp_table):
    _put(temp_table, 12, "verbatim")
    temp_table.execute("UPDATE t_sb SET lga = 'y' WHERE id = 12")
    assert _held(temp_table, 12)[:2] == (True, None)
