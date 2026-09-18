"""ROWS_SQL run against the REAL database, because its shape is a load-bearing assumption.

`tests/test_controls_against_source_pdf.py` covers the pure core with hand-built pages and
never opens a connection, so nothing there notices if the query stops returning what the
caller unpacks. This run added `c.unit` to that SELECT and every consumer unpacks the row
positionally -- a column renamed, dropped, or reordered upstream turns into a silent
mis-read (the unit landing in the value slot) rather than an error, and the check would go
on reporting a rate built from the wrong field.

The unit column matters beyond arity: `explain_row` uses it to decide whether "900mm" and
0.9 are the same quantity, so a NULL-flooded or renamed unit column would quietly disable
the unit_conversion rule and start failing correct rows.

Opt-in the way this repo already does it (see tests/test_drawdown_verify_real_db.py,
tests/test_lga_coverage.py): PYTEST_REAL_DB=1 plus @pytest.mark.database, deselected by
default per pytest.ini, so the ordinary `pytest` run is untouched. Read-only -- this file
issues no write.

    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \
        tests/test_validate_controls_against_source_pdf_real_db.py -v
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dq_db import main_checkout  # noqa: E402

_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip(
            "Real-DB test. Run with: PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database "
            "tests/test_validate_controls_against_source_pdf_real_db.py"
        )
    if not os.environ.get("DATABASE_URL") and not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")


def _rows(limit=200):
    import validate_controls_against_source_pdf as v

    conn = v.connect()
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30s'")
        cur.execute(v.ROWS_SQL)
        out = cur.fetchmany(limit)
        cur.close()
        return out
    finally:
        conn.close()


class TestTheQueryStillReturnsWhatTheCallerUnpacks:
    def test_nine_columns_in_the_order_main_unpacks_them(self):
        """main() destructures `cid, lga, ct, quote, pg, _p, vmin, vmax, unit`. A row of a
        different width raises there; a row of the same width in a different order does
        not, and that is the failure this asserts against the live catalog."""
        _skip_if_no_real_db()
        rows = _rows(50)
        assert rows, "no current control cites a page -- the check would have nothing to do"
        for cid, lga, ctype, quote, page, r2_path, vmin, vmax, unit in rows:
            assert isinstance(cid, int)
            assert isinstance(lga, str) and lga == lga.lower()
            assert isinstance(ctype, str) and ctype
            assert isinstance(page, int) and page > 0
            assert isinstance(r2_path, str) and r2_path.endswith(".pdf")
            assert quote is None or isinstance(quote, str)
            assert unit is None or isinstance(unit, str)

    def test_values_are_numbers_float_accepts(self):
        """explain_value calls float() on whatever is stored. Postgres `numeric` arrives as
        Decimal, which float() takes; a text column here would raise inside the rule engine
        and be reported as an unexplained value rather than as the type error it is."""
        _skip_if_no_real_db()
        for *_head, vmin, vmax, _unit in _rows(200):
            for value in (vmin, vmax):
                if value is not None:
                    float(value)  # raises TypeError/ValueError if the column type drifted

    def test_the_scope_is_served_rows_only(self):
        """A superseded control is shown to nobody, so grading one would move the published
        rate for reasons no customer can see."""
        _skip_if_no_real_db()
        import psycopg2

        import validate_controls_against_source_pdf as v

        conn = v.connect()
        try:
            cur = conn.cursor()
            cur.execute("SET statement_timeout = '30s'")
            cur.execute(f"SELECT count(*) FROM ({v.ROWS_SQL}) q")
            scoped = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM dcp_setback_controls WHERE pdf_page IS NOT NULL")
            any_page = cur.fetchone()[0]
            cur.close()
        except psycopg2.Error as exc:  # a broken query must fail loudly, never skip
            pytest.fail(f"ROWS_SQL did not run against the live database: {exc}")
        finally:
            conn.close()
        assert 0 < scoped <= any_page

    def test_the_unit_column_is_populated_enough_for_the_conversion_rule_to_matter(self):
        """If unit went all-NULL, explain_row's unit_conversion rule would stop firing and
        correct millimetre rows would start reading as unsupported -- a regression that
        looks like a data problem and is a schema one."""
        _skip_if_no_real_db()
        units = [u for *_rest, u in [(r[:-1], r[-1]) for r in _rows(300)]]
        assert any(u for u in units), "every unit came back NULL"
