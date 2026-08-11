"""Offline tests for the schema-contract gate's SQL reader.

The gate is only worth having if its reader is trustworthy in BOTH directions:
it must find a reference to a table that does not exist, and it must not invent
one that was never written. The second half matters as much as the first — the
first version of this reader produced 60 findings, 34 of which were phantoms
(`set` from `DO UPDATE SET`, `the` from an LLM prompt, `for` from a log line),
and a check that cries wolf gets switched off.

No database. `validate_schema_contract` keeps psycopg2/dotenv inside functions
precisely so this file can import it in the mocked pre-push environment.

Mutation note: replacing `analyse_sql` with a stub that returns empty results
fails the DETECTS tests; replacing it with one that returns every word fails the
IGNORES tests. Neither direction can pass by accident.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pytest  # noqa: E402

from validate_schema_contract import (  # noqa: E402
    analyse_sql,
    iter_sql_literals,
    load_baseline,
    load_catalog,
)


def _tables(sql: str, extra_ctes=frozenset()):
    return analyse_sql(sql, extra_ctes)[0]


def _literals(name: str, src: str):
    return [s for s, _ in iter_sql_literals(Path(name), src)]


# --------------------------------------------------------------------------- #
# DETECTS — the gate must be able to go red
# --------------------------------------------------------------------------- #
class TestDetectsTableReferences:
    def test_from_clause(self):
        assert "regulatory_provisions" in _tables("SELECT id FROM regulatory_provisions")

    def test_join_clause(self):
        t = _tables("SELECT 1 FROM a_table LEFT JOIN other_table o ON o.id = a_table.id")
        assert "other_table" in t

    def test_update_and_insert_and_delete(self):
        assert "t_upd" in _tables("UPDATE t_upd SET x = 1")
        assert "t_ins" in _tables("INSERT INTO t_ins (a) VALUES (1)")
        assert "t_del" in _tables("DELETE FROM t_del WHERE id = 1")

    def test_the_real_regression_dcp_complete_shape(self):
        """The exact shape that shipped broken: a renamed table behind an alias."""
        sql = """
            SELECT DISTINCT ON (dgr.id) dgr.id, dgr.category
            FROM dcp_general_requirements dgr
            LEFT JOIN dcp_general_provisions dgp ON dgp.id = dgr.source_provision_ids[1]
            WHERE dgr.lga = $1
        """
        tables, alias_map, _, quals, _ = analyse_sql(sql)
        assert "dcp_general_requirements" in tables
        assert "dcp_general_provisions" in tables
        # and the alias must bind, or no column could ever be checked
        assert alias_map["dgr"] == "dcp_general_requirements"
        assert ("dgr", "category") in quals

    def test_runtime_built_table_name_is_surfaced_not_swallowed(self):
        assert "${}" in _tables("SELECT * FROM ${tableName} WHERE id = 1")


# --------------------------------------------------------------------------- #
# IGNORES — the gate must not invent findings
# --------------------------------------------------------------------------- #
class TestIgnoresNonTables:
    def test_cte_is_not_a_base_table(self):
        sql = "WITH ranked AS (SELECT 1) SELECT * FROM ranked"
        tables, _, ctes, _, _ = analyse_sql(sql)
        assert "ranked" in ctes
        assert "ranked" not in [t for t in tables if t != "${}"] or "ranked" in ctes

    def test_materialized_cte_is_recognised(self):
        sql = "WITH document_filtered AS MATERIALIZED (SELECT 1) SELECT * FROM document_filtered"
        assert "document_filtered" in analyse_sql(sql)[2]

    def test_cte_defined_in_another_fragment(self):
        """Queries assembled from several template literals still resolve."""
        sql = "SELECT * FROM document_filtered"
        _, _, ctes, _, _ = analyse_sql(sql, frozenset({"document_filtered"}))
        assert "document_filtered" in ctes

    def test_derived_table(self):
        assert _tables("SELECT * FROM (SELECT 1 AS x) sub") == []

    def test_set_returning_function(self):
        assert _tables("SELECT * FROM unnest(ARRAY[1,2]) AS v") == []
        assert _tables("SELECT * FROM regexp_replace(a, 'b', 'c')") == []

    def test_do_update_set_is_not_a_table(self):
        sql = "INSERT INTO leads (id) VALUES (1) ON CONFLICT (id) DO UPDATE SET id = 1"
        assert "set" not in [t.lower() for t in _tables(sql)]

    def test_sql_comments_do_not_contribute(self):
        sql = "SELECT 1 FROM real_table -- FROM commented_table\n/* FROM blocked_table */"
        t = _tables(sql)
        assert "real_table" in t
        assert "commented_table" not in t and "blocked_table" not in t


# --------------------------------------------------------------------------- #
# PROSE — the false-positive class that made v1 untrustworthy
# --------------------------------------------------------------------------- #
class TestProseIsNotSql:
    def test_python_docstring_is_skipped(self):
        src = '"""Update the record from the queue when selected."""\nx = 1\n'
        assert _literals("m.py", src) == []

    def test_log_line_containing_a_sql_verb_is_skipped(self):
        src = 'logger.warning(f"Skipping last_checked update for {sub_id} — API down")\n'
        assert _literals("m.py", src) == []

    def test_llm_prompt_is_skipped(self):
        src = 'PROMPT = """You select WHICH facts matter, from the verified set."""\n'
        assert _literals("m.py", src) == []

    def test_real_python_sql_is_still_found(self):
        src = 'q = """SELECT id FROM regulatory_provisions WHERE is_current"""\n'
        got = _literals("m.py", src)
        assert len(got) == 1 and "regulatory_provisions" in got[0]

    def test_ts_template_literal_sql_is_found(self):
        src = "const q = `SELECT id FROM dcp_setback_controls WHERE lga = $1`;"
        got = _literals("r.ts", src)
        assert len(got) == 1 and "dcp_setback_controls" in got[0]

    def test_ts_commented_out_query_is_skipped(self):
        src = "// const old = `SELECT 1 FROM removed_table`;\nconst q = `SELECT 1 FROM kept_table`;"
        joined = " ".join(_literals("r.ts", src))
        assert "kept_table" in joined and "removed_table" not in joined


# --------------------------------------------------------------------------- #
# COLUMN BINDING — three-state, never two
# --------------------------------------------------------------------------- #
class TestColumnBinding:
    def test_alias_bound_to_cte_is_unverifiable_not_valid(self):
        """A CTE column has no catalog entry; calling it VALID is the DQ-30 error."""
        sql = "WITH c AS (SELECT 1 AS x) SELECT c.x FROM c"
        _, alias_map, _, quals, _ = analyse_sql(sql)
        assert alias_map.get("c") is None
        assert ("c", "x") in quals

    def test_schema_qualifier_is_not_read_as_a_column(self):
        sql = "SELECT id FROM public.regulatory_provisions"
        assert ("public", "regulatory_provisions") not in analyse_sql(sql)[3]

    def test_js_interpolation_is_not_read_as_a_column(self):
        sql = "SELECT * FROM t WHERE id = ${row.id}"
        assert ("row", "id") not in analyse_sql(sql)[3]

    def test_unaliased_table_still_binds_its_own_columns(self):
        sql = "SELECT regulatory_provisions.id FROM regulatory_provisions"
        _, alias_map, _, quals, _ = analyse_sql(sql)
        assert alias_map["regulatory_provisions"] == "regulatory_provisions"
        assert ("regulatory_provisions", "id") in quals


# --------------------------------------------------------------------------- #
# CANNOT-CHECK IS NOT A PASS — the failure mode the whole gate exists to avoid
# --------------------------------------------------------------------------- #
class TestSilenceIsNeverSuccess:
    def test_no_database_url_exits_2_rather_than_passing(self, monkeypatch):
        """No catalog means nothing was verified. Exit 2, never exit 0."""
        import validate_schema_contract as vsc

        monkeypatch.setattr(vsc, "_load_env", lambda: None)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
        with pytest.raises(SystemExit) as exc:
            load_catalog()
        assert exc.value.code == 2

    def test_missing_baseline_suppresses_nothing(self, tmp_path):
        """An absent baseline must mean zero suppressions, not blanket amnesty."""
        assert load_baseline(tmp_path, "does_not_exist.json") == {"entries": []}

    def test_corrupt_baseline_exits_2_rather_than_suppressing(self, tmp_path):
        (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
        with pytest.raises(SystemExit) as exc:
            load_baseline(tmp_path, "bad.json")
        assert exc.value.code == 2
