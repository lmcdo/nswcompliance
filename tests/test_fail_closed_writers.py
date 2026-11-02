"""Two production writers must refuse bad input and never run on import.

scripts/procedural/import_procedural.py empties three tables and refills them;
scripts/_clean_krg_reversed.py rewrites live provision_text. Both used to write
on a plain run with no backup.
"""
import importlib.util
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def proc(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    mod = _load("scripts/procedural/import_procedural.py", "import_procedural_t")
    monkeypatch.setattr(mod, "EXTRACTED_DIR", tmp_path)
    return mod


def _write_inputs(d: Path, guidance=1, checklist_items=1, guides=1):
    (d / "pathway_guidance.json").write_text(json.dumps([{}] * guidance))
    (d / "application_checklists.json").write_text(
        json.dumps([{"items": [{}] * checklist_items}]))
    (d / "getting_started_guides.json").write_text(json.dumps([{}] * guides))


class TestImportProceduralInputs:
    def test_valid_inputs_count_checklist_items_not_checklists(self, proc, tmp_path):
        _write_inputs(tmp_path, guidance=46, checklist_items=158, guides=5)
        assert proc.planned_row_counts()[0] == {
            "procedural_guidance": 46,
            "application_checklists": 158,
            "getting_started_guides": 5,
        }

    def test_missing_file_aborts(self, proc, tmp_path):
        _write_inputs(tmp_path)
        (tmp_path / "getting_started_guides.json").unlink()
        with pytest.raises(SystemExit, match="missing"):
            proc.planned_row_counts()

    def test_empty_list_aborts(self, proc, tmp_path):
        _write_inputs(tmp_path, guidance=0)
        with pytest.raises(SystemExit, match="0 rows"):
            proc.planned_row_counts()

    def test_checklists_with_no_items_abort(self, proc, tmp_path):
        _write_inputs(tmp_path, checklist_items=0)
        with pytest.raises(SystemExit, match="0 rows"):
            proc.planned_row_counts()

    def test_truncated_json_aborts(self, proc, tmp_path):
        _write_inputs(tmp_path)
        (tmp_path / "pathway_guidance.json").write_text('[{"a": 1}, {"b"')
        with pytest.raises(SystemExit, match="could not be read"):
            proc.planned_row_counts()

    def test_non_list_aborts(self, proc, tmp_path):
        _write_inputs(tmp_path)
        (tmp_path / "pathway_guidance.json").write_text("{}")
        with pytest.raises(SystemExit, match="not a list"):
            proc.planned_row_counts()


class TestImportProceduralShrink:
    def test_shrink_over_half_is_reported(self, proc):
        msgs = proc.check_shrink({"t": 40}, {"t": 158}, allow_shrink=False)
        assert msgs == ["t: 158 rows now, import would leave 40"]

    def test_exactly_half_is_allowed(self, proc):
        assert proc.check_shrink({"t": 79}, {"t": 158}, allow_shrink=False) == []

    def test_allow_shrink_overrides(self, proc):
        assert proc.check_shrink({"t": 1}, {"t": 158}, allow_shrink=True) == []

    def test_empty_table_never_counts_as_shrink(self, proc):
        assert proc.check_shrink({"t": 5}, {"t": 0}, allow_shrink=False) == []


class TestCleanKrgReversed:
    def test_import_does_not_connect(self, monkeypatch):
        connect = mock.MagicMock(side_effect=AssertionError("connected on import"))
        monkeypatch.setitem(sys.modules, "psycopg2", mock.MagicMock(connect=connect))
        _load("scripts/_clean_krg_reversed.py", "clean_krg_t")
        connect.assert_not_called()

    def test_dry_run_reads_but_never_updates(self, monkeypatch):
        cur = mock.MagicMock()
        cur.fetchall.return_value = [(1, "Real text\nGNIKRAP\nmore text")]
        conn = mock.MagicMock(cursor=mock.MagicMock(return_value=cur))
        fake_pg = mock.MagicMock(connect=mock.MagicMock(return_value=conn))
        monkeypatch.setitem(sys.modules, "psycopg2", fake_pg)
        mod = _load("scripts/_clean_krg_reversed.py", "clean_krg_t2")
        monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://unused")
        monkeypatch.setattr(sys, "argv", ["_clean_krg_reversed.py"])
        assert mod.main() == 0
        sql = " ".join(str(c.args[0]) for c in cur.execute.call_args_list)
        assert "UPDATE" not in sql
        conn.commit.assert_not_called()

    def test_clean_text_strips_only_reversed_label_lines(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "psycopg2", mock.MagicMock())
        mod = _load("scripts/_clean_krg_reversed.py", "clean_krg_t3")
        assert mod.clean_text("Keep this\nGNIKRAP\n3A\nand this") == "Keep this\nand this"


class TestSolFindings:
    def test_checked_payload_is_the_one_returned_for_writing(self, proc, tmp_path):
        _write_inputs(tmp_path, guidance=2)
        _, payloads = proc.planned_row_counts()
        (tmp_path / "pathway_guidance.json").write_text("[]")  # changed after the check
        assert len(payloads["procedural_guidance"]) == 2

    def test_krg_concurrent_change_rolls_back(self, monkeypatch):
        cur = mock.MagicMock()
        cur.fetchall.return_value = [(1, "Real text\nGNIKRAP\nmore text")]
        cur.rowcount = 0  # the row changed after it was read
        conn = mock.MagicMock(cursor=mock.MagicMock(return_value=cur))
        monkeypatch.setitem(sys.modules, "psycopg2",
                            mock.MagicMock(connect=mock.MagicMock(return_value=conn)))
        mod = _load("scripts/_clean_krg_reversed.py", "clean_krg_t4")
        monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://unused")
        monkeypatch.setattr(sys, "argv", ["_clean_krg_reversed.py", "--apply"])
        with mock.patch.object(Path, "write_text"), mock.patch.object(Path, "mkdir"):
            assert mod.main() == 1
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()


class TestShrinkUnderLock:
    def test_table_grown_since_dry_run_aborts_before_delete(self, proc, tmp_path, monkeypatch):
        monkeypatch.setattr(proc, "BACKUP_DIR", tmp_path)
        cur = mock.MagicMock()
        cur.description = [("id",)]
        cur.fetchall.return_value = [(i,) for i in range(200)]
        with pytest.raises(SystemExit, match="under lock"):
            proc.backup_and_clear(cur, "procedural_guidance", planned_rows=60)
        sql = [str(c.args[0]) for c in cur.execute.call_args_list]
        assert not any(s.startswith("DELETE") for s in sql)
        cur.connection.rollback.assert_called_once()
