"""dcp_commit_approved runs the council-words copier once per committed chapter, after publish.

prior-art-checked: extends the commit-worker tests; the post-publish re-checks are skipped under
pytest (they would write to production), so the runner itself is tested with a fake subprocess.
"""
import os
import sys
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "postgresql://x")
for k in ("R2_BUCKET_NAME", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_ACCOUNT_ID"):
    os.environ.setdefault(k, "x")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import dcp_commit_approved as dca  # noqa: E402


def test_it_runs_the_copier_on_exactly_that_chapter_and_stores(capsys):
    calls = []

    def fake(cmd, **kw):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="rules: 12\nstored: 12 of 12 rules (0 not judged)\n", stderr="")

    assert dca.run_council_quote("hornsby", "part-3", run=fake) == 0
    (cmd,) = calls
    assert cmd[1].endswith("council_quote.py")
    assert "--apply" in cmd and "--dry-run" not in cmd
    assert cmd[cmd.index("--council") + 1] == "hornsby"
    assert cmd[cmd.index("--chapter") + 1] == "part-3"
    assert "stored: 12 of 12" in capsys.readouterr().out


def test_a_failure_is_reported_with_the_rerun_command_not_raised(capsys):
    def fake(cmd, **kw):
        return SimpleNamespace(returncode=1, stdout="", stderr="boom")

    assert dca.run_council_quote("hornsby", "part-3", run=fake) == 1
    out = capsys.readouterr().out
    assert "[warn]" in out and "--chapter part-3" in out


def test_a_crash_is_reported_not_raised(capsys):
    def fake(cmd, **kw):
        raise TimeoutError("1800s")

    assert dca.run_council_quote("hornsby", "part-3", run=fake) == 1
    assert "could not run" in capsys.readouterr().out


def test_the_publish_loop_calls_it_per_committed_chapter():
    """The call site is in main()'s post-publish block, keyed by the committed (council, chapter)."""
    import inspect
    src = inspect.getsource(dca.main)
    assert "committed_chapters.add((council, chapter_key))" in src
    assert "run_council_quote(council, chapter_key)" in src


def test_the_sweep_runs_the_unchecked_flag_fleet_wide(capsys):
    calls = []

    def fake(cmd, **kw):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="unchecked rules selected: 4\nstored: 4 of 4 rules\n", stderr="")

    assert dca.run_unchecked_council_quote_sweep(run=fake) == 0
    (cmd,) = calls
    assert cmd[1].endswith("council_quote.py")
    assert "--apply" in cmd and "--unchecked" in cmd and "--council" not in cmd
    assert "stored: 4 of 4" in capsys.readouterr().out


def test_a_sweep_failure_is_reported_not_swallowed(capsys):
    def fake(cmd, **kw):
        return SimpleNamespace(returncode=1, stdout="", stderr="boom")

    assert dca.run_unchecked_council_quote_sweep(run=fake) == 1
    assert "[warn]" in capsys.readouterr().out

    def crash(cmd, **kw):
        raise TimeoutError("3300s")

    assert dca.run_unchecked_council_quote_sweep(run=crash) == 1
    assert "could not run" in capsys.readouterr().out


def test_main_calls_the_sweep_once_after_commits_and_alerts_on_failure():
    import inspect
    src = inspect.getsource(dca.main)
    assert src.count("run_unchecked_council_quote_sweep(") == 2   # idle-night early return + after commits
    assert src.index("run_council_quote(council, chapter_key)") < src.rindex("run_unchecked_council_quote_sweep(")
    assert "if sweep_rc:" in src and "send(" in src
    assert "(completeness_rc == 1 or sweep_rc) and not committed" in src
