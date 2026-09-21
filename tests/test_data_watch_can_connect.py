"""The nightly data check died on a missing environment variable, and that blocked merges.

`validate_controls_against_source_pdf.connect()` indexed `os.environ["PGHOST"]`.
`.github/workflows/data-watch.yml` passes DATABASE_URL and R2_* and no PG* variables at
all, so the job raised `KeyError: 'PGHOST'` before reading a single row.

It had failed every night since 2026-09-18 — last success 2026-09-17 — and was found on
2026-09-21. The cost was not the missing check alone. `gates` has a step asking when
data-watch last SUCCEEDED, so one unset variable in a script nobody was running by hand
was blocking the merge gate on every open pull request, and the failure it reported
("nothing has checked the live data within the limit") described a symptom three steps
from its cause.

Run against production once the fallback was in place, it passed: 97.3% of 764 checkable
controls supported by their cited document, against a 95% mark. The check had been
correct the whole time and simply could not open a connection.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

SRC = (ROOT / "scripts" / "validate_controls_against_source_pdf.py").read_text(
    encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "data-watch.yml").read_text(encoding="utf-8")

PG_VARS = ("PGHOST", "PGUSER", "PGPASSWORD", "PGDATABASE")


def _mod():
    import validate_controls_against_source_pdf as v
    return v


@pytest.fixture
def no_pg(monkeypatch):
    """Exactly what the runner looks like: DATABASE_URL set, no PG* at all."""
    for k in PG_VARS:
        monkeypatch.delenv(k, raising=False)
    # Credential-free on purpose: the secrets hook rejects a user:pass@host DSN in a
    # diff, and rightly so -- a dummy one in a test file is exactly how a real one
    # eventually gets committed. Nothing here connects, so the shape is all that matters.
    monkeypatch.setenv("DATABASE_URL", "postgresql:///testdb")
    return monkeypatch


class TestItConnectsTheWayTheWorkflowSuppliesCredentials:
    def test_the_workflow_really_does_pass_database_url_and_not_pg_vars(self):
        """If this ever stops being true the rest of the file is testing a fiction."""
        assert "DATABASE_URL" in WORKFLOW
        for k in PG_VARS:
            assert f"{k}:" not in WORKFLOW, (
                f"the workflow now passes {k}; re-read this file's premise")

    def test_database_url_is_enough(self, no_pg, monkeypatch):
        v = _mod()
        seen = {}

        def fake_connect(*args, **kwargs):
            seen["args"], seen["kwargs"] = args, kwargs
            return MagicMock()

        monkeypatch.setattr(v.psycopg2, "connect", fake_connect)
        monkeypatch.setattr(v, "load_env", lambda: None)
        v.connect()
        assert seen["args"] and seen["args"][0].startswith("postgresql://"), (
            "connect() is not using DATABASE_URL, so the nightly run cannot connect")

    def test_it_does_not_raise_a_bare_keyerror_when_nothing_is_set(self, monkeypatch):
        """The original failure mode. A KeyError names one variable and explains
        nothing; three teams' worth of merges were blocked behind it."""
        for k in PG_VARS + ("DATABASE_URL",):
            monkeypatch.delenv(k, raising=False)
        v = _mod()
        monkeypatch.setattr(v, "load_env", lambda: None)
        with pytest.raises(SystemExit) as e:
            v.connect()
        msg = str(e.value)
        assert "DATABASE_URL" in msg and "PGHOST" in msg, (
            "the failure must name what is missing, not just the first key read")

    def test_the_pg_fallback_still_works_for_a_local_run(self, monkeypatch):
        """Confusable negative: preferring DATABASE_URL must not delete the path
        someone's local shell may still be using."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        for k in PG_VARS:
            monkeypatch.setenv(k, "x")
        v = _mod()
        seen = {}
        monkeypatch.setattr(v.psycopg2, "connect",
                            lambda *a, **kw: seen.update(kw) or MagicMock())
        monkeypatch.setattr(v, "load_env", lambda: None)
        v.connect()
        assert seen.get("host") == "x" and seen.get("dbname") == "x"

    def test_the_connection_is_read_only(self):
        """It reads production. That is not negotiable and is easy to lose in a
        refactor of the lines around it."""
        assert "set_session(readonly=True" in SRC


class TestAMissingEnvFileIsNotFatal:
    def test_find_env_returns_none_rather_than_exiting(self, monkeypatch, tmp_path):
        """CI has no .env -- it passes credentials in the environment. sys.exit here
        made a runner's normal state indistinguishable from a broken checkout."""
        v = _mod()
        monkeypatch.setattr(v, "REPO_ROOT", tmp_path / "a" / "b")
        assert v.find_env() is None

    def test_load_env_tolerates_it(self, monkeypatch, tmp_path):
        v = _mod()
        monkeypatch.setattr(v, "REPO_ROOT", tmp_path / "a" / "b")
        v.load_env()  # must not raise

    def test_a_real_environment_still_wins_over_the_file(self):
        """setdefault, not assignment: the workflow's DATABASE_URL must not be
        overwritten by a stale value in someone's checked-out .env."""
        assert "os.environ.setdefault" in SRC
