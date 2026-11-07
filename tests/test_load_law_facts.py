"""scripts/load_law_facts.py: what it would write, how it compares, and that it refuses to write wrongly.

No database is touched: the connection is a recorder. Every refusal and every difference the ledger
check relies on has a case that must trip it.
"""

import json
import sys
import types
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dq_db  # noqa: E402
import extract_lmr_law_facts as law  # noqa: E402
import load_law_facts as lf  # noqa: E402

DOC = json.loads(law.FACTS_PATH.read_text(encoding="utf-8"))
ROWS = lf.build_rows(DOC)
N_FACTS = len(ROWS)


def as_db(rows, current=True):
    """What the database would hand back: Decimal numbers, date objects, is_current."""
    out = []
    for r in rows:
        d = dict(r)
        d["law_version_date"] = date.fromisoformat(d["law_version_date"])
        if d["value_number"] is not None:
            d["value_number"] = Decimal(str(d["value_number"]))
        d["is_current"] = current
        out.append(d)
    return out


# ---- the rows ---------------------------------------------------------------------------------


def test_one_row_per_fact_with_clause_page_quote_and_hash():
    assert [r["fact_key"] for r in ROWS] == list(DOC["facts"])
    assert len(ROWS) == N_FACTS == 28   # 18 + 3 'accessible area' facts + 4 parking minimums + the s164(1)(i) distance + 2 s164(1)(h) levels (2026-11-07)
    for r in ROWS:
        assert r["clause"] and r["quote"] and isinstance(r["pdf_page"], int)
        assert r["text_sha256"] == DOC["text_sha256"] and r["law_version_date"] == "2026-10-23"
        assert r["instrument_key"] == "sepp_housing_2021"


def test_scalar_numbers_are_queryable_and_structures_are_not():
    by = {r["fact_key"]: r for r in ROWS}
    assert by["lmr_outer_distance"]["value_number"] == 800 and by["lmr_outer_distance"]["unit"] == "m"
    assert by["tod_fsr"]["value"] == "2.5:1" and by["tod_fsr"]["value_number"] is None
    assert by["schedule_11_stations"]["value_number"] is None and len(by["schedule_11_stations"]["value"]) == 59
    assert len(by["s164"]["value"]["paragraphs"]) == 14 and by["s164"]["value"]["live_count"] == 13
    assert by["tod_affordable_gfa_threshold"]["extra"]["unit_verified"] is False


# ---- comparing database with JSON ------------------------------------------------------------


def test_identical_rows_have_no_difference_even_with_database_types():
    assert lf.diff_rows(ROWS, as_db(ROWS)) == []


@pytest.mark.parametrize(
    "mutate,expect",
    [
        (lambda r: r.update(value_number=Decimal("900")) if r["fact_key"] == "lmr_outer_distance" else None, "lmr_outer_distance"),
        (lambda r: r.update(pdf_page=99) if r["fact_key"] == "tod_fsr" else None, "tod_fsr"),
        (lambda r: r.update(text_sha256="0" * 64) if r["fact_key"] == "s164" else None, "s164"),
        (lambda r: r.update(quote="changed") if r["fact_key"] == "tod_min_lot_width_m" else None, "tod_min_lot_width_m"),
        (lambda r: r.update(value=r["value"][:-1]) if r["fact_key"] == "schedule_11_stations" else None, "schedule_11_stations"),
    ],
)
def test_each_kind_of_drift_is_reported(mutate, expect):
    db = as_db(ROWS)
    for r in db:
        mutate(r)
    problems = lf.diff_rows(ROWS, db)
    assert any(expect in p for p in problems), problems


def test_missing_and_extra_rows_are_reported():
    db = as_db(ROWS)
    gone = db.pop(0)
    db.append({**db[0], "fact_key": "invented"})
    problems = lf.diff_rows(ROWS, db)
    assert f"missing in database: {gone['fact_key']}" in problems and "not in the JSON: invented" in problems


# ---- the plan --------------------------------------------------------------------------------


def test_empty_database_inserts_everything():
    p = lf.plan_changes(ROWS, [])
    assert (len(p["insert"]), p["supersede"], p["unchanged"], p["conflicts"]) == (N_FACTS, [], 0, [])


def test_identical_current_rows_are_left_alone():
    p = lf.plan_changes(ROWS, as_db(ROWS))
    assert (p["insert"], p["unchanged"], p["conflicts"]) == ([], N_FACTS, [])


def test_a_newer_law_version_supersedes_and_keeps_history():
    old = as_db(ROWS)
    for r in old:
        r["law_version_date"] = date(2026, 2, 6)
    p = lf.plan_changes(ROWS, old)
    assert len(p["insert"]) == N_FACTS and len(p["supersede"]) == N_FACTS and p["conflicts"] == []


def test_same_version_different_content_is_a_conflict_not_an_overwrite():
    db = as_db(ROWS)
    db[0]["quote"] = "someone edited this"
    p = lf.plan_changes(ROWS, db)
    assert len(p["conflicts"]) == 1 and "same law version" in p["conflicts"][0] and len(p["insert"]) == 0


def test_correct_updates_only_the_named_fact_under_the_same_version():
    db = as_db(ROWS)
    db[0]["quote"] = "wording that was wrong"
    key = db[0]["fact_key"]
    p = lf.plan_changes(ROWS, db, frozenset({key}))
    assert [r["fact_key"] for r in p["update"]] == [key] and p["conflicts"] == [] and p["insert"] == [] and p["supersede"] == []
    # naming a DIFFERENT fact does not fix this one, and naming a fact with no difference is reported, never ignored
    other = next(r["fact_key"] for r in ROWS if r["fact_key"] != key)
    p2 = lf.plan_changes(ROWS, db, frozenset({other}))
    assert any("same law version" in c for c in p2["conflicts"]) and any(f"--correct {other}" in c for c in p2["conflicts"])


def test_correct_cannot_override_a_newer_law_version_in_the_database():
    db = as_db(ROWS)
    db[0]["law_version_date"] = date(2027, 1, 1)
    assert any("NEWER" in c for c in lf.plan_changes(ROWS, db, frozenset({db[0]["fact_key"]}))["conflicts"])


def test_a_newer_version_in_the_database_is_a_conflict():
    db = as_db(ROWS)
    db[0]["law_version_date"] = date(2027, 1, 1)
    assert any("NEWER" in c for c in lf.plan_changes(ROWS, db)["conflicts"])


def test_history_rows_are_ignored_by_the_plan():
    hist = as_db(ROWS, current=False)
    assert len(lf.plan_changes(ROWS, hist)["insert"]) == N_FACTS


# ---- a recorder in place of the database -----------------------------------------------------


class Cur:
    def __init__(self, log):
        self.log, self.description = log, None

    def execute(self, sql, params=None):
        self.log.append((" ".join(sql.split()), params))

    def fetchone(self):
        return ("postgres",)


class Conn:
    def __init__(self):
        self.log, self.events = [], []

    def cursor(self):
        return Cur(self.log)

    def rollback(self):
        self.events.append("rollback")

    def commit(self):
        self.events.append("commit")

    def set_session(self, readonly):
        self.events.append(f"readonly={readonly}")

    def close(self):
        self.events.append("close")


@pytest.fixture
def db(monkeypatch, tmp_path):
    conn = Conn()
    monkeypatch.setattr(dq_db, "connect", lambda: conn)
    monkeypatch.setattr(lf, "BACKUP_DIR", tmp_path)
    monkeypatch.setattr(lf, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(lf, "_table_exists", lambda cur: True)
    extras = types.ModuleType("psycopg2.extras")
    extras.Json = lambda v: ("JSON", v)
    monkeypatch.setitem(sys.modules, "psycopg2", types.ModuleType("psycopg2"))
    monkeypatch.setitem(sys.modules, "psycopg2.extras", extras)
    conn.tmp = tmp_path
    return conn


def writes(conn):
    return [sql for sql, _ in conn.log if sql.startswith(("INSERT", "UPDATE"))]


def test_dry_run_writes_nothing_and_makes_no_backup(db, monkeypatch, capsys):
    monkeypatch.setattr(lf, "_fetch", lambda cur, where="": [])
    assert lf.run(apply=False) == 0
    assert writes(db) == [] and "commit" not in db.events and list(db.tmp.glob("*.json")) == []
    assert "dry run: nothing written" in capsys.readouterr().out


def test_apply_backs_up_writes_verifies_and_commits(db, monkeypatch):
    calls = []

    def fetch(cur, where=""):
        calls.append(where)
        return [] if len(calls) == 1 else as_db(ROWS)

    monkeypatch.setattr(lf, "_fetch", fetch)
    assert lf.run(apply=True) == 0
    assert len([w for w in writes(db) if w.startswith("INSERT")]) == N_FACTS
    assert db.events.count("commit") == 1 and "readonly=False" in db.events
    assert len(list(db.tmp.glob("law_facts_pre_*.json"))) == 1
    assert any(sql.startswith("SET LOCAL statement_timeout") for sql, _ in db.log)


def test_apply_rolls_back_if_the_database_would_not_equal_the_json(db, monkeypatch, capsys):
    monkeypatch.setattr(lf, "_fetch", lambda cur, where="": [])  # post-write read comes back empty
    assert lf.run(apply=True) == 1
    assert "commit" not in db.events and db.events.count("rollback") >= 1
    assert "ROLLED BACK" in capsys.readouterr().out


def test_apply_refuses_on_a_conflict_and_writes_nothing(db, monkeypatch):
    bad = as_db(ROWS)
    bad[0]["quote"] = "edited"
    monkeypatch.setattr(lf, "_fetch", lambda cur, where="": bad)
    assert lf.run(apply=True) == 1
    assert writes(db) == [] and "commit" not in db.events


def test_apply_does_nothing_when_already_loaded(db, monkeypatch, capsys):
    monkeypatch.setattr(lf, "_fetch", lambda cur, where="": as_db(ROWS))
    assert lf.run(apply=True) == 0
    assert writes(db) == [] and "nothing to do" in capsys.readouterr().out


def test_missing_table_means_nothing_is_written(db, monkeypatch):
    monkeypatch.setattr(lf, "_table_exists", lambda cur: False)
    assert lf.run(apply=True) == 1 and writes(db) == []


def test_apply_refuses_when_the_json_no_longer_matches_the_law_text(db, monkeypatch):
    monkeypatch.setattr(law, "differences", lambda stored, fresh: ["facts.tod_fsr"])
    with pytest.raises(SystemExit) as e:
        lf.run(apply=True)
    assert "REFUSED" in str(e.value) and writes(db) == []


# ---- the ledger check --------------------------------------------------------------------------


class Session:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, *a):
        return False


def test_check_is_unknown_not_clean_without_a_database(monkeypatch, capsys):
    def boom():
        raise RuntimeError("No DATABASE_URL")

    monkeypatch.setattr(dq_db, "session", boom)
    assert lf.check() == 2
    assert "UNKNOWN is not CLEAN" in capsys.readouterr().out


def test_check_is_unknown_on_any_connection_error(monkeypatch):
    def boom():
        raise OSError("network down")

    monkeypatch.setattr(dq_db, "session", boom)
    assert lf.check() == 2


def test_check_says_not_loaded_when_the_table_is_missing(monkeypatch, capsys):
    monkeypatch.setattr(dq_db, "session", lambda: Session(Conn()))
    monkeypatch.setattr(lf, "_table_exists", lambda cur: False)
    assert lf.check() == 1 and "NOT LOADED" in capsys.readouterr().out


def test_check_passes_only_when_the_database_equals_the_json(monkeypatch):
    monkeypatch.setattr(dq_db, "session", lambda: Session(Conn()))
    monkeypatch.setattr(lf, "_table_exists", lambda cur: True)
    monkeypatch.setattr(lf, "_fetch", lambda cur, where="": as_db(ROWS))
    assert lf.check() == 0
    drifted = as_db(ROWS)
    drifted[3]["pdf_page"] = 1
    monkeypatch.setattr(lf, "_fetch", lambda cur, where="": drifted)
    assert lf.check() == 1
    monkeypatch.setattr(lf, "_fetch", lambda cur, where="": as_db(ROWS)[:-1])
    assert lf.check() == 1


@pytest.mark.database
@pytest.mark.skipif(not __import__("os").environ.get("PYTEST_REAL_DB"), reason="opt in with PYTEST_REAL_DB=1 and DATABASE_URL")
def test_real_database_equals_the_saved_json():
    """Real layer: the stored law_facts rows in the live database equal data/law/housing_sepp_lmr_facts.json (read-only check, exit 0)."""
    import subprocess
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "load_law_facts.py"), "--check"], capture_output=True, text=True, timeout=120, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
