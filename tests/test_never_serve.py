"""Reviewed never-serve rules (data/chapter_scope/never_serve.json) are never re-keyed, re-layered or switched on.

Found 2026-10-22: the page-range rule cb_2_2_flood_by_former_council re-keyed 97 Carinya Road (Picnic Point only)
flood rules to 'C-B former Bankstown' and they were served to every house in former Bankstown.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import never_serve  # noqa: E402

LISTED = sorted(never_serve.ids())[0]
UNLISTED = 1


class FakeCursor:
    """Answers the derive/gate SELECTs with the given rows; records every statement."""

    def __init__(self, rows_by_marker: dict[str, list[dict]]):
        self.rows_by_marker = rows_by_marker
        self.statements: list[tuple[str, object]] = []
        self.description = []
        self._rows: list[tuple] = []

    def execute(self, sql, params=None):
        self.statements.append((sql, params))
        self._rows, self.description = [], []
        if sql.lstrip().upper().startswith("SELECT"):
            for marker, rows in self.rows_by_marker.items():
                if marker in sql and rows:
                    cols = list(rows[0].keys())
                    self.description = [(c,) for c in cols]
                    self._rows = [tuple(r[c] for c in cols) for r in rows]

    def fetchall(self):
        return self._rows

    def updated_ids(self) -> set:
        return {p[-1] for s, p in self.statements if s.lstrip().upper().startswith("UPDATE") and p}


class FakeConn:
    def __init__(self, cur):
        self.cur, self.autocommit = cur, False

    def cursor(self):
        return self.cur

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


def _row(i: int, page: int) -> dict:
    return {"id": i, "document_id": "d", "ref_number": "r", "pdf_page": page,
            "source_chapter_key": "chapter-2-2-flood-risk-management", "v2_precinct_id": None,
            "v2_dcp_layer": "precinct", "v2_dcp_part": None, "provision_text": "x"}


def test_derive_never_keys_a_listed_row(monkeypatch, tmp_path, capsys):
    import derive_precinct_keys as dpk
    rule = next(r for r in dpk.RULES if r["name"] == "cb_2_2_flood_by_former_council")
    pages = [25, 25, rule.get("fingerprint", {}).get("max_page", 65)]
    rows = [_row(LISTED, pages[0]), _row(UNLISTED, pages[1]), _row(2, pages[2])]
    cur = FakeCursor({"chapter-2-2-flood-risk-management": rows})
    monkeypatch.setattr(dpk.psycopg2, "connect", lambda *a, **k: FakeConn(cur))
    monkeypatch.setattr(dpk, "REPO", tmp_path)
    (tmp_path / "data" / "db_rollback_backups").mkdir(parents=True)
    rc = dpk.run(council="canterbury_bankstown", apply=True, validate=False, only={rule["name"]})
    out = capsys.readouterr().out
    assert rc == 0, out
    assert LISTED not in cur.updated_ids(), "a never-serve row was re-keyed"
    assert UNLISTED in cur.updated_ids(), "the ordinary row next to it must still be keyed (skip is not a blanket stop)"
    assert "never-serve-skipped=1" in out


def test_derive_never_keys_a_reread_copy_with_a_new_id(monkeypatch, tmp_path):
    """A re-read mints new ids; a row with a listed rule's text must still be skipped."""
    import derive_precinct_keys as dpk
    probe = "carinya road rule text as re-read under a new id"
    monkeypatch.setattr(never_serve, "text_keys", lambda council, chapter: frozenset({never_serve.text_key(probe)}))
    rule = next(r for r in dpk.RULES if r["name"] == "cb_2_2_flood_by_former_council")
    # Same words, different case and spacing: the fingerprint normalises both.
    copy = dict(_row(999999001, 25), provision_text="  Carinya ROAD rule text as re-read\n under a new id ")
    rows = [copy, _row(UNLISTED, 25), _row(2, rule.get("fingerprint", {}).get("max_page", 65))]
    cur = FakeCursor({"chapter-2-2-flood-risk-management": rows})
    monkeypatch.setattr(dpk.psycopg2, "connect", lambda *a, **k: FakeConn(cur))
    monkeypatch.setattr(dpk, "REPO", tmp_path)
    (tmp_path / "data" / "db_rollback_backups").mkdir(parents=True)
    assert dpk.run(council="canterbury_bankstown", apply=True, validate=False, only={rule["name"]}) == 0
    assert 999999001 not in cur.updated_ids(), "a re-read copy of a never-serve rule was keyed"
    assert UNLISTED in cur.updated_ids()


def test_gate_rules_never_relayer_a_listed_row(monkeypatch):
    import gate_rules as gr
    rule = {"name": "t", "council": "canterbury_bankstown", "where": "source_chapter_key = 'chapter-x'",
            "set": {"v2_dcp_layer": "generic"}}
    monkeypatch.setattr(gr, "GATE_RULES", [rule])
    rows = [{"id": LISTED, "v2_dcp_layer": "precinct"}, {"id": UNLISTED, "v2_dcp_layer": "precinct"}]
    cur = FakeCursor({"chapter-x": rows})
    gr.apply_gate_rules(cur, "canterbury_bankstown", apply=True)
    assert LISTED not in cur.updated_ids()
    assert UNLISTED in cur.updated_ids()


def test_list_loads_and_counts_match():
    es = never_serve.entries()
    assert es and all(len(e["ids"]) == e["expect"] == len(e["text_sha256_16"]) for e in es)


def test_a_miscounted_list_raises(monkeypatch, tmp_path):
    bad = json.loads(never_serve.PATH.read_text(encoding="utf-8"))
    bad["entries"][0]["expect"] += 1
    p = tmp_path / "never_serve.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    monkeypatch.setattr(never_serve, "PATH", p)
    never_serve.entries.cache_clear()
    try:
        with pytest.raises(ValueError):
            never_serve.entries()
    finally:
        never_serve.entries.cache_clear()


def test_a_missing_list_raises_not_reads_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(never_serve, "PATH", tmp_path / "missing.json")
    never_serve.entries.cache_clear()
    try:
        with pytest.raises(FileNotFoundError):
            never_serve.ids()
    finally:
        never_serve.entries.cache_clear()


@pytest.mark.parametrize("path, needle", [
    ("enrichment/pipeline.py", "if prov_id in never:"),
    ("scripts/dcp_extract_changed.py", "CASE WHEN id = ANY(%s) THEN v2_is_actionable ELSE NULL END"),
    ("scripts/fixes/rerun_actionable_classifier.py", "id not in _never"),
    ("scripts/sync_v2_to_supabase.py", "if row['id'] in never:"),
])
def test_other_writers_consult_the_list(path, needle):
    """Wiring check only (these four are not driven end to end here): each writer that can switch a rule on or
    overwrite its key consults the list. DQ-148 is the behavioural backstop on the live database."""
    assert needle in (ROOT / path).read_text(encoding="utf-8")


@pytest.mark.database
@pytest.mark.skipif(os.environ.get("PYTEST_REAL_DB") != "1", reason="set PYTEST_REAL_DB=1 and DATABASE_URL")
def test_sql_fingerprint_matches_python():
    import dq_db
    import dq_probe_live as d
    e = never_serve.entries()[0]
    with dq_db.connect() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT {d._TEXT_KEY_SQL.format(col='provision_text')}, provision_text "
                    "FROM regulatory_provisions WHERE id = ANY(%s)", (e["ids"],))
        rows = cur.fetchall()
    assert len(rows) == e["expect"]
    assert {k for k, _ in rows} == {never_serve.text_key(t) for _, t in rows} == set(e["text_sha256_16"])
