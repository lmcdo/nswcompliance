"""A code commit counts as reviewed only if a FINISHED Sol review read it.

Incident replays:
  * 2026-10-11: five PRs merged after the review hit a 429 and `|| true` let
    the push through — no finished review row.
  * 2026-10-18 on: OpenAI out of credits, every push reviewed by DeepSeek —
    a finished row, but not Sol.
Built on real temporary git repos, because patch-id and ranges are the logic.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import review_coverage as rc  # noqa: E402

SOL = "gpt-5.6"


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True,
                          text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@t")
    git(tmp_path, "config", "user.name", "t")
    git(tmp_path, "config", "core.autocrlf", "false")
    commit(tmp_path, "README.md", "x", "base")
    return tmp_path


def commit(repo, path, text, msg):
    f = repo / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    git(repo, "add", path)
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD")


def row(base, head, model=SOL, outcome=rc.OUTCOME_REVIEWED):
    return {"base": base, "head": head, "model": model, "outcome": outcome}


def test_fully_reviewed_branch_has_no_gap(repo):
    base = git(repo, "rev-parse", "HEAD")
    head = commit(repo, "services/a.py", "a=1\n", "code")
    assert rc.uncovered(repo, base, head, [row(base, head)]) == []


def test_no_ledger_at_all_fails_closed(repo):
    base = git(repo, "rev-parse", "HEAD")
    head = commit(repo, "services/a.py", "a=1\n", "code")
    assert rc.uncovered(repo, base, head, []) == [head]


def test_incident_429_did_not_finish_is_not_reviewed(repo):
    base = git(repo, "rev-parse", "HEAD")
    head = commit(repo, "services/a.py", "a=1\n", "code")
    rows = [row(base, head, model=None, outcome=rc.OUTCOME_UNFINISHED)]
    assert rc.uncovered(repo, base, head, rows) == [head]


def test_incident_deepseek_fallback_is_not_sol(repo):
    base = git(repo, "rev-parse", "HEAD")
    head = commit(repo, "services/a.py", "a=1\n", "code")
    rows = [row(base, head, model="deepseek/deepseek-v3.2")]
    assert rc.uncovered(repo, base, head, rows) == [head]


def test_skipped_push_between_reviewed_pushes_is_caught(repo):
    """The incremental base moves on PUSH, so a skipped review is never re-read."""
    base = git(repo, "rev-parse", "HEAD")
    c1 = commit(repo, "services/a.py", "a=1\n", "push 1")
    c2 = commit(repo, "services/b.py", "b=1\n", "push 2 - review skipped")
    c3 = commit(repo, "services/c.py", "c=1\n", "push 3")
    rows = [row(base, c1), row(c2, c3)]
    assert rc.uncovered(repo, base, c3, rows) == [c2]


def test_docs_and_tests_only_need_no_review(repo):
    base = git(repo, "rev-parse", "HEAD")
    commit(repo, "docs/x.md", "d\n", "docs")
    head = commit(repo, "tests/test_x.py", "t\n", "tests")
    assert rc.uncovered(repo, base, head, []) == []


def test_clean_rebase_keeps_coverage(repo):
    git(repo, "checkout", "-q", "-b", "feat")
    base = git(repo, "rev-parse", "main")
    head = commit(repo, "services/a.py", "a=1\n", "code")
    rows = [row(base, head)]
    git(repo, "checkout", "-q", "main")
    commit(repo, "other.txt", "o\n", "main moves")
    git(repo, "checkout", "-q", "feat")
    git(repo, "rebase", "-q", "main")
    new_head = git(repo, "rev-parse", "HEAD")
    assert new_head != head
    assert rc.uncovered(repo, git(repo, "rev-parse", "main"), new_head, rows) == []


def test_amended_commit_loses_coverage(repo):
    base = git(repo, "rev-parse", "HEAD")
    head = commit(repo, "services/a.py", "a=1\n", "code")
    rows = [row(base, head)]
    (repo / "services/a.py").write_text("a=2\n", encoding="utf-8")
    git(repo, "commit", "-q", "-a", "--amend", "-m", "code")
    amended = git(repo, "rev-parse", "HEAD")
    assert rc.uncovered(repo, base, amended, rows) == [amended]


def test_row_with_unknown_objects_proves_nothing(repo):
    base = git(repo, "rev-parse", "HEAD")
    head = commit(repo, "services/a.py", "a=1\n", "code")
    rows = [row("0" * 40, "1" * 40)]
    assert rc.uncovered(repo, base, head, rows) == [head]


def test_torn_ledger_line_is_ignored(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text('{"outcome": "reviewed"\n{"outcome": "did-not-finish"}\n', encoding="utf-8")
    assert rc.read_rows(p) == [{"outcome": "did-not-finish"}]


@pytest.mark.parametrize("model, ok", [
    ("gpt-5.6", True), ("deepseek/deepseek-v3.2", False), (None, False), ("", False), ("  ", False),
])
def test_is_sol(model, ok):
    assert rc.is_sol(model) is ok


def test_slug_matches_the_pre_push_hook():
    ref = "feat/merge-review-gates"
    # The ref goes in as $1, not an env var: on Windows `bash` can resolve to
    # WSL, which does not inherit the caller's environment.
    script = ("R=\"$1\"; H=$(printf '%s' \"$R\" | sha1sum | cut -c1-10); "
              "echo \"$(printf '%s' \"$R\" | tr '/' '-')-$H\"")
    bash = shutil.which("bash") or pytest.skip("no bash")
    out = subprocess.run([bash, "-c", script, "_", ref],
                         capture_output=True, text=True, check=True).stdout.strip()
    assert rc.branch_slug(ref) == out


def test_override_is_bound_to_one_head():
    rows = [{"outcome": rc.OUTCOME_OVERRIDE, "head": "abc", "reason": "r" * 20}]
    assert rc.has_override(rows, "abc") == "r" * 20
    assert rc.has_override(rows, "def") is None


def test_cross_review_writes_did_not_finish_when_the_model_call_dies(repo, tmp_path):
    """The exit-handler row: a crash before the model answers must not read as reviewed."""
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    log = tmp_path / "log.jsonl"
    base = git(repo, "rev-parse", "HEAD")
    commit(repo, "services/a.py", "a=1\n", "code")
    probe = (
        "import sys; sys.path.insert(0, r'%s'); import cross_review, sol_common;"
        "cross_review._REPO_ROOT = __import__('pathlib').Path(r'%s');"
        "sol_common.load_api_key = lambda root: 'k';"
        "cross_review.call_model = lambda *a: sys.exit('429 Too Many Requests');"
        "sys.argv = ['x', '--base', '%s', '--review-log', r'%s']; cross_review.main()"
    ) % (scripts, repo, base, log)
    subprocess.run([sys.executable, "-c", probe], cwd=repo, capture_output=True, text=True)
    rows = rc.read_rows(log)
    assert len(rows) == 1 and rows[0]["outcome"] == rc.OUTCOME_UNFINISHED


def test_cross_review_records_the_model_that_actually_answered(repo, tmp_path):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    log = tmp_path / "log.jsonl"
    base = git(repo, "rev-parse", "HEAD")
    commit(repo, "services/a.py", "a=1\n", "code")
    probe = (
        "import sys; sys.path.insert(0, r'%s'); import cross_review, sol_common;"
        "cross_review._REPO_ROOT = __import__('pathlib').Path(r'%s');"
        "sol_common.load_api_key = lambda root: 'k';"
        "cross_review.call_model = lambda *a: (setattr(sol_common, 'LAST_MODEL',"
        " 'deepseek/deepseek-v3.2'), {'findings': []})[1];"
        "sys.argv = ['x', '--base', '%s', '--review-log', r'%s']; cross_review.main()"
    ) % (scripts, repo, base, log)
    out = subprocess.run([sys.executable, "-c", probe], cwd=repo, capture_output=True, text=True)
    rows = rc.read_rows(log)
    assert rows, out.stderr
    assert rows[0]["outcome"] == rc.OUTCOME_REVIEWED
    assert rows[0]["model"] == "deepseek/deepseek-v3.2"
    assert rc.uncovered(repo, base, git(repo, "rev-parse", "HEAD"), rows) != []


# ── End to end through check_pr_gates.review_gap, against a real origin ──────
def _clone_with_pr(tmp_path):
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "-q", "-b", "main")
    for k, v in (("user.email", "t@t"), ("user.name", "t"), ("core.autocrlf", "false")):
        git(work, "config", k, v)
    commit(work, "README.md", "x", "base")
    git(work, "remote", "add", "origin", str(origin))
    git(work, "push", "-q", "origin", "main")
    git(work, "checkout", "-q", "-b", "feat/x")
    head = commit(work, "services/a.py", "a=1\n", "code")
    git(work, "push", "-q", "origin", "feat/x")
    return work, git(work, "rev-parse", "main"), head


def _gates(monkeypatch, work, head):
    import check_pr_gates as g
    monkeypatch.setattr(g, "REPO", work)
    monkeypatch.setattr(g, "pr_view", lambda pr: {
        "headRefOid": head, "headRefName": "feat/x", "baseRefName": "main",
        "state": "OPEN", "mergeable": "MERGEABLE"})
    return g


def test_gate_refuses_a_branch_whose_review_fell_back(tmp_path, monkeypatch):
    work, base, head = _clone_with_pr(tmp_path)
    g = _gates(monkeypatch, work, head)
    log = rc.log_path(work, "feat/x")
    rc.append_row(log, row(base, head, model="deepseek/deepseek-v3.2"))
    verdict, msg = g.review_gap(1, None)
    assert verdict == "NOT-REVIEWED" and head[:8] in msg


def test_gate_passes_a_branch_sol_reviewed(tmp_path, monkeypatch):
    work, base, head = _clone_with_pr(tmp_path)
    g = _gates(monkeypatch, work, head)
    rc.append_row(rc.log_path(work, "feat/x"), row(base, head))
    assert g.review_gap(1, None)[0] == "READY"


def test_gate_override_needs_a_reason_and_is_recorded(tmp_path, monkeypatch):
    work, base, head = _clone_with_pr(tmp_path)
    g = _gates(monkeypatch, work, head)
    assert g.review_gap(1, "short")[0] == "NOT-REVIEWED"
    assert g.review_gap(1, "OpenAI down all day, reviewed by hand")[0] == "READY"
    rows = rc.read_rows(rc.log_path(work, "feat/x"))
    assert rows[-1]["outcome"] == rc.OUTCOME_OVERRIDE and rows[-1]["uncovered"] == [head]
    # Bound to this head: a new commit needs a new decision.
    new_head = commit(work, "services/b.py", "b=1\n", "more")
    git(work, "push", "-q", "origin", "feat/x")
    g = _gates(monkeypatch, work, new_head)
    assert g.review_gap(1, None)[0] == "NOT-REVIEWED"


def test_unfinished_row_never_counts_even_when_it_names_sol(repo):
    """The outcome decides, not the model: a row can name Sol and still not have finished."""
    base = git(repo, "rev-parse", "HEAD")
    head = commit(repo, "services/a.py", "a=1\n", "code")
    rows = [row(base, head, model=SOL, outcome=rc.OUTCOME_UNFINISHED)]
    assert rc.uncovered(repo, base, head, rows) == [head]
