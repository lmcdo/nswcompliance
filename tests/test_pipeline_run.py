"""scripts/pipeline_run.py without a database: the run id and its reuse.

The database half (set_config, autocommit, the log) is tests/test_rule_write_guard_db.py.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pipeline_run  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_run(monkeypatch):
    monkeypatch.delenv(pipeline_run.ENV, raising=False)


def test_the_run_id_names_script_sha_and_one_run(monkeypatch):
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "200390e2f0e1a1b2c3")
    rid = pipeline_run.run_id("dcp_commit_approved")
    script, rest = rid.split("@")
    sha, run = rest.split(":")
    assert (script, sha, len(run)) == ("dcp_commit_approved", "200390e2f0e1", 12)
    assert pipeline_run.run_id("dcp_commit_approved") != rid      # a new run each time


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_a_blank_script_name_is_refused_not_logged_as_blank(bad):
    with pytest.raises(ValueError):
        pipeline_run.run_id(bad)


def test_one_run_id_for_the_whole_process_and_its_children(monkeypatch):
    """A reconnect and a child process must log under the same run, not a new one."""
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "abc")
    first = pipeline_run.tag(object(), "dcp_commit_approved")
    again = pipeline_run.tag(object(), "council_quote")
    import os
    assert again == first and os.environ[pipeline_run.ENV] == first


def test_an_unknown_sha_is_said_out_loud(monkeypatch, capsys):
    monkeypatch.delenv("RAILWAY_GIT_COMMIT_SHA", raising=False)
    monkeypatch.setattr(pipeline_run, "_git_sha", lambda: "unknown")
    pipeline_run.tag(object(), "r2_monitor")
    assert "no git sha" in capsys.readouterr().err


def test_a_test_double_is_not_sent_any_sql():
    class Fake:
        def cursor(self):
            raise AssertionError("tag must not query a non-psycopg2 connection")
    assert pipeline_run.tag(Fake(), "x").startswith("x@")
