"""The doc-claim check must fire on the four incidents that motivated it.

Each of the four false premises this fortnight came from a document, not from
code. Three of them are decidable by a parser and are pinned here as fixtures
built to their exact shape:

  * a QA report naming a test file that does not exist (#887, the APRA test);
  * a doc claiming methodology_version = 1.2 when code holds 1.1 (#887);
  * a dependency declared only where nothing installs it (#880, icontract).

The fourth -- services/CLAUDE.md's "Threat Radar shares the Sentinel-2
pipeline" -- is NOT decidable by a parser, and
`test_semantic_claims_are_out_of_scope` pins that limit so nobody reads a green
run as "the docs are true".

The false positives that the first live run produced are pinned too: each of
them was a defect in the CHECK, and a regression would quietly inflate the
finding count until the check gets ignored.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_MODULE = Path(__file__).resolve().parents[1] / "scripts" / "doc_claims.py"


def _load():
    spec = importlib.util.spec_from_file_location("doc_claims_under_test", _MODULE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # @dataclass resolves through sys.modules
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def dc():
    return _load()


# A git hook exports GIT_DIR / GIT_INDEX_FILE, and they OVERRIDE cwd. Every git
# call in this file must therefore run with them stripped, or the fixture repo's
# commits land in whatever repository invoked pytest. Found by .githooks/pre-push
# refusing the push: the suite was green run directly and red run from the hook.
_GIT_ENV = {
    k: v
    for k, v in os.environ.items()
    if not k.startswith("GIT_") or k in ("GIT_ASKPASS", "GIT_SSH", "GIT_SSH_COMMAND")
}


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, env=_GIT_ENV)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A miniature tracked repo. `git ls-files` is the check's authority."""
    for cmd in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "t@t"],
        ["git", "config", "user.name", "t"],
    ):
        _git(cmd, tmp_path)

    (tmp_path / "services").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / ".github" / "workflows").mkdir(parents=True)

    (tmp_path / "services" / "scorer.py").write_text(
        'METHODOLOGY_VERSION = "1.1"\n\n\ndef score():\n    return 1\n', encoding="utf-8"
    )
    (tmp_path / "tests" / "test_scorer.py").write_text(
        "import json\nimport icontract\n", encoding="utf-8"
    )
    (tmp_path / "requirements-test.txt").write_text("pytest>=8\n", encoding="utf-8")
    (tmp_path / "services" / "requirements.txt").write_text(
        "icontract>=2.7.3\n", encoding="utf-8"
    )
    (tmp_path / ".github" / "workflows" / "gates.yml").write_text(
        "jobs:\n  t:\n    steps:\n      - run: pip install -r requirements-test.txt\n",
        encoding="utf-8",
    )
    (tmp_path / "Dockerfile.python").write_text(
        "COPY services/requirements.txt ./requirements.txt\n"
        "RUN pip install --no-cache-dir -r requirements.txt\n",
        encoding="utf-8",
    )
    _git(["git", "add", "-A"], tmp_path)
    _git(["git", "commit", "-qm", "init"], tmp_path)
    return tmp_path


def _doc(repo: Path, name: str, body: str) -> str:
    path = repo / "docs" / name
    path.write_text(body, encoding="utf-8")
    _git(["git", "add", "-A"], repo)
    return f"docs/{name}"


def _kinds(result, kind: str):
    return [v for v in result.violations if v.kind == kind]


# ── PATH: the APRA-test shape ────────────────────────────────────────────────


def test_doc_naming_a_nonexistent_test_is_reported(dc, repo):
    """#887: 'a pre-written APRA test' that existed in no branch."""
    rel = _doc(repo, "method.md", "Run `tests/test_apra_correlation.py` to verify.\n")
    result = dc.scan(repo, docs=[rel], reports=[])
    claims = [v.claim for v in _kinds(result, "path")]
    assert claims == ["tests/test_apra_correlation.py"]


def test_doc_naming_a_real_file_is_silent(dc, repo):
    rel = _doc(repo, "ok.md", "See `services/scorer.py` and `tests/test_scorer.py`.\n")
    assert _kinds(dc.scan(repo, docs=[rel], reports=[]), "path") == []


def test_qa_report_strings_are_checked_too(dc, repo):
    """The report is where a session records what it verified."""
    (repo / ".qa_report.json").write_text(
        json.dumps({"pre_impl": {"existing_data": "covered by tests/test_ghost.py"}}),
        encoding="utf-8",
    )
    _git(["git", "add", "-A"], repo)
    result = dc.scan(repo, docs=[], reports=[".qa_report.json"])
    assert [v.claim for v in _kinds(result, "path")] == ["tests/test_ghost.py"]


# ── PATH: a report naming a file it deletes in the same diff ────────────────
# 2026-09-05: a branch that deleted 13 files and documented every one of them
# by name (fix/fabricated-compliance-fallback) hit this for real. The report
# is not lying -- it is describing its own diff -- but until deleted_in_diff()
# existed, the check could not tell that apart from a hallucinated path.


def _branch_that_deletes_a_file(repo: Path) -> tuple[str, str]:
    """Commits a file, brands that commit `main`, then deletes the file on
    top. `main` must be cut AFTER the file exists -- branching first and
    adding+removing the file entirely within the range would make git's own
    diff report NO change for it (both trees agree it is absent), which is
    not the scenario this exists to cover. Returns (relative path deleted,
    repo-relative report path naming it)."""
    target = repo / "services" / "to_delete.py"
    target.write_text("def f():\n    return 1\n", encoding="utf-8")
    _git(["git", "add", "-A"], repo)
    _git(["git", "commit", "-qm", "add file that will be deleted"], repo)
    _git(["git", "branch", "main", "HEAD"], repo)
    target.unlink()
    _git(["git", "add", "-A"], repo)
    _git(["git", "commit", "-qm", "delete it"], repo)
    report_rel = ".qa/reports/fix__delete-a-file.json"
    (repo / ".qa").mkdir(exist_ok=True)
    (repo / ".qa" / "reports").mkdir(exist_ok=True)
    (repo / report_rel).write_text(
        json.dumps({"files": ["services/to_delete.py"]}), encoding="utf-8"
    )
    _git(["git", "add", "-A"], repo)
    _git(["git", "commit", "-qm", "report the deletion"], repo)
    return "services/to_delete.py", report_rel


def test_a_report_naming_a_file_it_deletes_this_branch_is_silent(dc, repo):
    _, report_rel = _branch_that_deletes_a_file(repo)
    result = dc.scan(repo, docs=[], reports=[report_rel])
    assert _kinds(result, "path") == [], (
        "a report describing its OWN diff's deletion was flagged as if it "
        "hallucinated the path"
    )


def test_a_report_naming_a_file_never_in_this_diff_is_still_reported(dc, repo):
    """The leniency must not swallow a genuinely bogus path just because
    SOME file was deleted somewhere in the branch."""
    _branch_that_deletes_a_file(repo)
    (repo / ".qa" / "reports" / "fix__bogus.json").write_text(
        json.dumps({"files": ["services/never_existed_at_all.py"]}), encoding="utf-8"
    )
    _git(["git", "add", "-A"], repo)
    _git(["git", "commit", "-qm", "bogus report"], repo)
    result = dc.scan(repo, docs=[], reports=[".qa/reports/fix__bogus.json"])
    assert [v.claim for v in _kinds(result, "path")] == ["services/never_existed_at_all.py"]


def test_a_prose_doc_naming_a_deleted_file_is_still_reported(dc, repo):
    """The leniency is scoped to reports (which describe THIS diff) -- a
    hand-written doc claiming a path is a claim about the current tree
    regardless of what any branch happened to delete."""
    deleted_path, _ = _branch_that_deletes_a_file(repo)
    rel = _doc(repo, "mentions_deleted.md", f"See `{deleted_path}`.\n")
    _git(["git", "commit", "-qm", "doc mentions the deleted file"], repo)
    result = dc.scan(repo, docs=[rel], reports=[])
    assert [v.claim for v in _kinds(result, "path")] == [deleted_path]


def test_a_staged_but_uncommitted_deletion_is_still_recognised(dc, repo):
    """Sol cross-review (2026-09-05): the first version diffed base..HEAD,
    which misses a deletion that is staged (or merely removed on disk) but
    not yet committed -- a developer running this check before committing
    their own true, in-progress deletion would see it rejected as if it
    hallucinated the path."""
    target = repo / "services" / "not_yet_committed.py"
    target.write_text("def f():\n    return 1\n", encoding="utf-8")
    _git(["git", "add", "-A"], repo)
    _git(["git", "commit", "-qm", "add file"], repo)
    _git(["git", "branch", "main", "HEAD"], repo)
    target.unlink()
    _git(["git", "add", "-A"], repo)  # staged, deliberately NOT committed
    (repo / "report_uncommitted.json").write_text(
        json.dumps({"files": ["services/not_yet_committed.py"]}), encoding="utf-8"
    )
    result = dc.scan(repo, docs=[], reports=["report_uncommitted.json"])
    assert _kinds(result, "path") == [], (
        "a deletion staged but not yet committed was rejected as a "
        "hallucinated path"
    )


def test_no_resolvable_base_ref_is_empty_not_a_crash(dc, repo):
    """A shallow CI checkout (fetch-depth: 1, the frontend-tests job's
    default before 2026-09-05) has no origin/main, origin/master or main --
    only the single fetched commit. deleted_in_diff() must degrade to an
    empty set, not raise, and a report naming a genuinely nonexistent path
    must still be reported exactly as before -- the leniency simply cannot
    activate without SOME base to diff against, and that must fail closed
    (stay strict), not open."""
    assert dc.deleted_in_diff(repo) == set()
    (repo / "report_no_base.json").write_text(
        json.dumps({"files": ["services/genuinely_never_existed.py"]}),
        encoding="utf-8",
    )
    result = dc.scan(repo, docs=[], reports=["report_no_base.json"])
    assert [v.claim for v in _kinds(result, "path")] == ["services/genuinely_never_existed.py"]


def test_line_citation_past_end_of_file_is_reported(dc, repo):
    """The tracker cited landing/data/shadow.ts:57 for a 55-line file."""
    rel = _doc(repo, "cite.md", "The bug is at `services/scorer.py:900`.\n")
    result = dc.scan(repo, docs=[rel], reports=[])
    assert len(_kinds(result, "path")) == 1
    assert "has only 5 lines" in _kinds(result, "path")[0].detail


def test_line_citation_against_an_ambiguous_basename_is_not_reported(dc, repo):
    """A bare `route.ts:548` names one of many files -- checking an arbitrary
    one would invent a finding, which is worse than missing one."""
    for sub in ("a", "b"):
        (repo / sub).mkdir()
        (repo / sub / "route.ts").write_text("x\n", encoding="utf-8")
    rel = _doc(repo, "amb.md", "See `route.ts:900`.\n")
    _git(["git", "add", "-A"], repo)
    assert _kinds(dc.scan(repo, docs=[rel], reports=[]), "path") == []


# ── PATH: false positives the first live run produced. Each was a check bug. ──


@pytest.mark.parametrize(
    "text, why",
    [
        ("Built with Next.js and Node.js.", "product names shaped like files"),
        ("Call `shapely.geometry.shape(x)`.", "a dotted attribute is not a .sh file"),
        ("Write `enrichment/config/<council>_config.py`.", "placeholder tail"),
        ("Run `scripts/insert_*_parking.py`.", "glob tail"),
        ("See https://example.com/a/b/setup.py for the upstream.", "a URL"),
        ("Create `migrations/XXX_add_thing.sql`.", "an XXX placeholder"),
    ],
)
def test_known_false_positive_shapes_stay_silent(dc, repo, text, why):
    rel = _doc(repo, "fp.md", text + "\n")
    found = _kinds(dc.scan(repo, docs=[rel], reports=[]), "path")
    assert found == [], f"{why}: unexpectedly reported {[v.claim for v in found]}"


def test_a_hyphenated_filename_is_captured_whole(dc, repo):
    """The first run reported `-paywall.test.ts`: a markdown table cell had
    absorbed a leading dash and truncated the real name, so the finding named
    a file nobody had written."""
    rel = _doc(repo, "hyphen.md", "| 77 | `granny-paywall.test.ts` | pending |\n")
    found = _kinds(dc.scan(repo, docs=[rel], reports=[]), "path")
    assert [v.claim for v in found] == ["granny-paywall.test.ts"]


def test_tsx_is_not_truncated_to_ts(dc, repo):
    """The ext alternation is first-match, so `ts` beat `tsx` without a
    trailing boundary -- inventing a finding for every correct .tsx reference."""
    (repo / "Widget.tsx").write_text("x\n", encoding="utf-8")
    rel = _doc(repo, "tsx.md", "See `Widget.tsx`.\n")
    _git(["git", "add", "-A"], repo)
    assert _kinds(dc.scan(repo, docs=[rel], reports=[]), "path") == []


def test_wrong_extension_says_which_one_is_right(dc, repo):
    (repo / "Widget.tsx").write_text("x\n", encoding="utf-8")
    rel = _doc(repo, "ext.md", "See `Widget.ts`.\n")
    _git(["git", "add", "-A"], repo)
    found = _kinds(dc.scan(repo, docs=[rel], reports=[]), "path")
    assert len(found) == 1
    assert "the real path is Widget.tsx" in found[0].detail


def test_relative_path_resolves_against_the_doc(dc, repo):
    (repo / "docs" / "sub").mkdir()
    rel = "docs/sub/deep.md"
    (repo / rel).write_text("See `../../services/scorer.py`.\n", encoding="utf-8")
    _git(["git", "add", "-A"], repo)
    assert _kinds(dc.scan(repo, docs=[rel], reports=[]), "path") == []


# ── VERSION: the v1.2 shape ──────────────────────────────────────────────────


def test_version_literal_not_held_by_the_named_constant_is_reported(dc, repo):
    rel = _doc(repo, "v.md", "The changelog documents METHODOLOGY_VERSION v1.2.\n")
    found = _kinds(dc.scan(repo, docs=[rel], reports=[]), "version")
    assert len(found) == 1
    assert found[0].claim == "methodology_version = 1.2"
    assert "['1.1']" in found[0].detail


def test_matching_version_is_silent(dc, repo):
    rel = _doc(repo, "v_ok.md", "METHODOLOGY_VERSION is 1.1.\n")
    assert _kinds(dc.scan(repo, docs=[rel], reports=[]), "version") == []


def test_a_documents_own_version_is_not_a_claim_about_code(dc, repo):
    """No identifier named, so nothing is being asserted about the code."""
    rel = _doc(repo, "own.md", "**Version:** 1.0 (this document)\n")
    assert _kinds(dc.scan(repo, docs=[rel], reports=[]), "version") == []


def test_a_distant_number_is_not_pulled_into_a_version_claim(dc, repo):
    """A QA report stores a paragraph as ONE JSON string. Without a proximity
    window the correlation threshold 0.7 was reported as a bad version."""
    filler = "x" * 200
    rel = _doc(repo, "far.md", f"METHODOLOGY_VERSION is 1.1. {filler} rho > 0.7 strict\n")
    assert _kinds(dc.scan(repo, docs=[rel], reports=[]), "version") == []


# ── DEPENDENCY: the icontract shape ──────────────────────────────────────────


def test_package_tests_import_but_ci_never_installs_is_reported(dc, repo):
    """#880 exactly: icontract lived only where CI does not look, so five
    tests skipped -- and a skip renders green."""
    found = _kinds(dc.scan(repo, docs=[], reports=[]), "dependency")
    claims = {v.claim for v in found}
    assert "icontract" in claims
    hit = next(v for v in found if v.claim == "icontract")
    assert "services/requirements.txt" in hit.detail
    assert "a skip is green" in hit.detail


def test_requirements_file_nothing_installs_is_reported(dc, repo):
    (repo / "requirements-orphan.txt").write_text("lonely>=1\n", encoding="utf-8")
    _git(["git", "add", "-A"], repo)
    found = _kinds(dc.scan(repo, docs=[], reports=[]), "dependency")
    assert any(v.claim == "requirements-orphan.txt" for v in found)


def test_installed_requirements_file_is_silent(dc, repo):
    found = _kinds(dc.scan(repo, docs=[], reports=[]), "dependency")
    assert not any(v.claim == "requirements-test.txt" for v in found)


# ── Three states: what it cannot decide is never a pass ──────────────────────


def test_git_hook_env_does_not_redirect_the_file_list(dc, repo, tmp_path, monkeypatch):
    """GIT_DIR overrides cwd, so the check would answer about the WRONG repo.

    Not hypothetical: .githooks/pre-push runs pytest, git exports GIT_DIR and
    GIT_INDEX_FILE to its hooks, and on the first push attempt this suite's own
    fixture wrote its commit into the real worktree's branch -- the tests were
    green run directly and red run from the hook. A check whose authority is
    `git ls-files` must pin that its authority is the directory it was pointed
    at, not an inherited variable.
    """
    other = tmp_path / "elsewhere"
    other.mkdir()
    _git(["git", "init", "-q"], other)
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(other / ".git" / "index"))

    tracked = dc.tracked_files(repo)
    assert tracked and "services/scorer.py" in tracked, (
        "the file list came from GIT_DIR instead of the scanned directory"
    )


def test_no_git_index_is_unknowable_not_clean(dc, tmp_path):
    (tmp_path / "d.md").write_text("`tests/test_ghost.py`\n", encoding="utf-8")
    result = dc.scan(tmp_path, docs=["d.md"], reports=[])
    assert result.violations == []
    assert any("unknowable" in n and "not a pass" in n for n in result.notes)


def test_unreadable_doc_is_a_note_not_a_pass(dc, repo):
    result = dc.scan(repo, docs=["docs/does_not_exist.md"], reports=[])
    # Dependency findings are repo-wide, not doc-scoped, so only the two
    # doc-derived kinds can be asserted empty here.
    assert _kinds(result, "path") == [] and _kinds(result, "version") == []
    assert any("could not be read" in n for n in result.notes)


def test_unmappable_test_import_is_a_note_not_a_violation(dc, repo):
    (repo / "tests" / "test_x.py").write_text(
        "import some_unlisted_package\n", encoding="utf-8"
    )
    _git(["git", "add", "-A"], repo)
    result = dc.scan(repo, docs=[], reports=[])
    assert not any(v.claim == "some-unlisted-package" for v in result.violations)
    assert any("could not be mapped" in n for n in result.notes)


def test_malformed_qa_report_is_a_note_not_a_crash(dc, repo):
    (repo / ".qa_report.json").write_text("{not json", encoding="utf-8")
    _git(["git", "add", "-A"], repo)
    result = dc.scan(repo, docs=[], reports=[".qa_report.json"])
    assert any("not valid JSON" in n for n in result.notes)


# ── The stated limit ─────────────────────────────────────────────────────────


def test_semantic_claims_are_out_of_scope(dc, repo):
    """services/CLAUDE.md's Threat Radar claim -- the one that misled three
    sessions -- is NOT caught, and must not be advertised as if it were.

    Every path in the fixture resolves and no version is claimed, so the check
    is silent about a sentence that is entirely false. If this ever starts
    failing, the scope statement in the module docstring and the PR body have
    to change with it.
    """
    rel = _doc(
        repo,
        "semantic.md",
        "`services/scorer.py` shares the imagery pipeline with the radar "
        "product, and 13 of 16 rows were confirmed by a person.\n",
    )
    result = dc.scan(repo, docs=[rel], reports=[])
    assert _kinds(result, "path") == []
    assert _kinds(result, "version") == []


# ── Baseline plumbing ────────────────────────────────────────────────────────


def test_fingerprint_is_stable_across_line_moves(dc, repo):
    rel = _doc(repo, "fp1.md", "`tests/test_ghost.py`\n")
    first = dc.scan(repo, docs=[rel], reports=[]).violations[0]
    _doc(repo, "fp1.md", "padding\npadding\n`tests/test_ghost.py`\n")
    second = dc.scan(repo, docs=[rel], reports=[]).violations[0]
    assert second.line != first.line
    assert second.fingerprint() == first.fingerprint()


def test_observation_mode_exits_zero_with_findings(dc, repo, capsys):
    _doc(repo, "obs.md", "`tests/test_ghost.py`\n")
    assert dc.main(["--project-dir", str(repo)]) == 0
    assert "observation mode" in capsys.readouterr().out


def test_strict_mode_exits_one(dc, repo):
    _doc(repo, "obs2.md", "`tests/test_ghost.py`\n")
    assert dc.main(["--project-dir", str(repo), "--strict"]) == 1


def test_the_qa_report_is_never_baselined(dc, repo):
    """The report is rewritten every PR, so a fingerprint taken from one
    report would suppress the SAME false claim when a later report makes it
    for real. Docs are corpus state; the report is not."""
    _doc(repo, "corpus.md", "`tests/test_ghost.py`\n")
    (repo / ".qa_report.json").write_text(
        json.dumps({"residual_risk": "see tests/test_phantom.py"}), encoding="utf-8"
    )
    _git(["git", "add", "-A"], repo)
    dc.main(["--project-dir", str(repo), "--init"])
    payload = json.loads(
        (repo / dc.BASELINE_PATH).read_text(encoding="utf-8")
    )
    assert any("corpus.md" in f for f in payload["fingerprints"])
    assert not any(".qa_report.json" in f for f in payload["fingerprints"])


# ── Findings raised by the Sol cross-review, each pinned ─────────────────────


def test_strict_mode_is_red_when_the_scan_could_not_run(dc, tmp_path):
    """An exported tree with no .git checked nothing, and --strict exited 0."""
    (tmp_path / "d.md").write_text("`tests/test_ghost.py`\n", encoding="utf-8")
    assert dc.main(["--project-dir", str(tmp_path), "--strict"]) == 2


def test_a_file_reached_through_an_include_counts_as_installed(dc, repo):
    """pip follows `-r other.txt`; without that the included file reads as an
    orphan nothing installs, and its packages as unavailable to CI."""
    (repo / "requirements-test.txt").write_text(
        "pytest>=8\n-r services/requirements.txt\n", encoding="utf-8"
    )
    _git(["git", "add", "-A"], repo)
    found = _kinds(dc.scan(repo, docs=[], reports=[]), "dependency")
    claims = {v.claim for v in found}
    assert "requirements.txt" not in claims, "reached through an include"
    assert "icontract" not in claims, "pip installs it transitively"


def test_include_cycle_terminates(dc, repo):
    (repo / "requirements-a.txt").write_text("-r requirements-b.txt\n", encoding="utf-8")
    (repo / "requirements-b.txt").write_text("-r requirements-a.txt\nzz>=1\n", encoding="utf-8")
    _git(["git", "add", "-A"], repo)
    assert "zz" in dc._declared_packages(repo, "requirements-a.txt")


def test_an_identifier_with_two_values_is_flagged_as_unknowable(dc, repo):
    """Two modules both defining METHODOLOGY_VERSION means a doc can name the
    other one's value and be accepted. That is reported, not hidden."""
    (repo / "services" / "other.py").write_text(
        'METHODOLOGY_VERSION = "2.0"\n', encoding="utf-8"
    )
    rel = _doc(repo, "amb_v.md", "METHODOLOGY_VERSION is 2.0.\n")
    _git(["git", "add", "-A"], repo)
    result = dc.scan(repo, docs=[rel], reports=[])
    assert _kinds(result, "version") == [], "2.0 does exist somewhere in code"
    assert any("hold different values" in n for n in result.notes)


def test_a_value_no_module_holds_is_still_reported_when_ambiguous(dc, repo):
    """The ambiguity note must not swallow the v1.2 case."""
    (repo / "services" / "other.py").write_text(
        'METHODOLOGY_VERSION = "2.0"\n', encoding="utf-8"
    )
    rel = _doc(repo, "amb_v2.md", "METHODOLOGY_VERSION is 1.2.\n")
    _git(["git", "add", "-A"], repo)
    found = _kinds(dc.scan(repo, docs=[rel], reports=[]), "version")
    assert [v.claim for v in found] == ["methodology_version = 1.2"]


def test_a_readme_is_not_evidence_that_something_is_installed(dc, repo):
    """A doc SAYING `pip install -r x.txt` was accepted as proof that x.txt is
    installed. Believing a document about what the code does is the exact error
    this module exists to catch, and it was suppressing orphan findings."""
    (repo / "requirements-doconly.txt").write_text("lonely>=1\n", encoding="utf-8")
    (repo / "README.md").write_text(
        "Set up with `pip install -r requirements-doconly.txt`.\n", encoding="utf-8"
    )
    _git(["git", "add", "-A"], repo)
    found = _kinds(dc.scan(repo, docs=[], reports=[]), "dependency")
    assert any(v.claim == "requirements-doconly.txt" for v in found)


def test_a_commented_out_install_line_is_not_an_installer(dc, repo):
    (repo / "requirements-old.txt").write_text("gone>=1\n", encoding="utf-8")
    (repo / "install.sh").write_text(
        "# previously: pip install -r requirements-old.txt\necho done\n",
        encoding="utf-8",
    )
    _git(["git", "add", "-A"], repo)
    found = _kinds(dc.scan(repo, docs=[], reports=[]), "dependency")
    assert any(v.claim == "requirements-old.txt" for v in found)


def test_two_correct_constants_on_one_line_produce_no_finding(dc, repo):
    """Binding every literal to every nearby identifier fabricated a mismatch
    from two claims that are both right. A fabricated finding is worse than a
    missed one -- it is the defect this whole campaign is about."""
    (repo / "services" / "api.py").write_text('API_VERSION = "2.0"\n', encoding="utf-8")
    rel = _doc(repo, "two.md", "API_VERSION 2.0 and METHODOLOGY_VERSION 1.1 today.\n")
    _git(["git", "add", "-A"], repo)
    found = _kinds(dc.scan(repo, docs=[rel], reports=[]), "version")
    assert found == [], f"fabricated: {[v.claim for v in found]}"


def test_two_identifiers_on_one_line_is_undecidable_not_guessed(dc, repo):
    """Nearest-wins was itself a fabrication risk: "API_VERSION and
    METHODOLOGY_VERSION are 2.0 and 1.1" pairs them in reading order and
    nearest-wins pairs them backwards. Which number belongs to which is English,
    not syntax, so the line is reported as undecidable and checked not at all --
    a missed finding is recoverable, a fabricated one is what this campaign is
    about."""
    (repo / "services" / "api.py").write_text('API_VERSION = "2.0"\n', encoding="utf-8")
    rel = _doc(
        repo, "two_bad.md", "API_VERSION and METHODOLOGY_VERSION are 2.0 and 1.1.\n"
    )
    _git(["git", "add", "-A"], repo)
    result = dc.scan(repo, docs=[rel], reports=[])
    assert _kinds(result, "version") == []
    assert any("version identifiers on one line" in n for n in result.notes)


def test_a_single_identifier_line_is_still_checked(dc, repo):
    """The undecidable rule must not swallow the v1.2 case, which is one
    identifier on its own line -- the shape every real instance has had."""
    (repo / "services" / "api.py").write_text('API_VERSION = "2.0"\n', encoding="utf-8")
    rel = _doc(repo, "one_bad.md", "Scoring follows METHODOLOGY_VERSION 9.9 now.\n")
    _git(["git", "add", "-A"], repo)
    found = _kinds(dc.scan(repo, docs=[rel], reports=[]), "version")
    assert [v.claim for v in found] == ["methodology_version = 9.9"]


def test_a_bare_dash_r_without_pip_install_is_not_an_installer(dc, repo):
    """`test -r requirements-extra.txt` checks readability and installs
    nothing; counting it suppressed the orphan finding for that file."""
    (repo / "requirements-extra.txt").write_text("nobody>=1\n", encoding="utf-8")
    (repo / "check.sh").write_text(
        "test -r requirements-extra.txt && echo present\n", encoding="utf-8"
    )
    _git(["git", "add", "-A"], repo)
    found = _kinds(dc.scan(repo, docs=[], reports=[]), "dependency")
    assert any(v.claim == "requirements-extra.txt" for v in found)


def test_long_form_requirement_flag_counts_as_an_installer(dc, repo):
    (repo / "requirements-prod.txt").write_text("prodpkg>=1\n", encoding="utf-8")
    (repo / "deploy.sh").write_text(
        "python -m pip install --requirement requirements-prod.txt\n", encoding="utf-8"
    )
    _git(["git", "add", "-A"], repo)
    found = _kinds(dc.scan(repo, docs=[], reports=[]), "dependency")
    assert not any(v.claim == "requirements-prod.txt" for v in found)


def test_backslash_continued_install_is_recognised(dc, repo):
    """Dockerfile.maintenance writes `RUN pip install --no-cache-dir \\` and
    puts each -r on its own line. Requiring pip install on the same PHYSICAL
    line turned two genuinely installed files into orphan findings."""
    (repo / "requirements-a.txt").write_text("apkg>=1\n", encoding="utf-8")
    (repo / "requirements-b.txt").write_text("bpkg>=1\n", encoding="utf-8")
    (repo / "Dockerfile.multi").write_text(
        "RUN pip install --no-cache-dir \\\n"
        "    -r requirements-a.txt \\\n"
        "    -r requirements-b.txt\n",
        encoding="utf-8",
    )
    _git(["git", "add", "-A"], repo)
    claims = {v.claim for v in _kinds(dc.scan(repo, docs=[], reports=[]), "dependency")}
    assert "requirements-a.txt" not in claims
    assert "requirements-b.txt" not in claims


def test_importorskip_counts_as_a_test_dependency(dc, repo):
    """The form this repo's dependency skips actually use. A line regex saw
    none of them, so the checker was blind to exactly the packages most likely
    to be missing from CI."""
    (repo / "tests" / "test_geo.py").write_text(
        'import pytest\n\nshapely = pytest.importorskip("shapely")\n', encoding="utf-8"
    )
    (repo / "services" / "requirements.txt").write_text(
        "icontract>=2.7.3\nshapely>=2\n", encoding="utf-8"
    )
    _git(["git", "add", "-A"], repo)
    found = _kinds(dc.scan(repo, docs=[], reports=[]), "dependency")
    assert any(v.claim == "shapely" for v in found)


def test_comma_separated_imports_are_all_seen(dc, repo):
    (repo / "tests" / "test_multi.py").write_text(
        "import json, icontract\n", encoding="utf-8"
    )
    _git(["git", "add", "-A"], repo)
    assert "icontract" in dc._test_imports(repo, dc.tracked_files(repo))


def test_baseline_counts_match_what_it_wrote(dc, repo):
    _doc(repo, "c1.md", "`tests/test_ghost.py`\n")
    (repo / ".qa_report.json").write_text(
        json.dumps({"residual_risk": "see tests/test_phantom.py"}), encoding="utf-8"
    )
    _git(["git", "add", "-A"], repo)
    dc.main(["--project-dir", str(repo), "--init"])
    payload = json.loads((repo / dc.BASELINE_PATH).read_text(encoding="utf-8"))
    assert sum(payload["counts"].values()) == len(payload["findings"])
    assert payload["excluded_report_findings"] == 1


def test_a_version_inside_a_comment_is_not_a_live_value(dc, repo):
    """A raw-text regex read `# was METHODOLOGY_VERSION = "1.2"` as a value the
    code holds, which silently accepted a document claiming 1.2."""
    (repo / "services" / "scorer.py").write_text(
        'METHODOLOGY_VERSION = "1.1"\n'
        '# historical: METHODOLOGY_VERSION = "1.2"\n'
        'EXAMPLE = \'METHODOLOGY_VERSION = "1.3"\'\n',
        encoding="utf-8",
    )
    rel = _doc(repo, "cmt.md", "METHODOLOGY_VERSION is 1.2.\n")
    _git(["git", "add", "-A"], repo)
    constants = dc.code_version_constants(repo, dc.tracked_files(repo))
    assert constants["methodology_version"] == {"1.1"}
    assert [v.claim for v in _kinds(dc.scan(repo, docs=[rel], reports=[]), "version")] == [
        "methodology_version = 1.2"
    ]


def test_basename_only_installer_match_is_reported_as_unknowable(dc, repo):
    """Two files named requirements.txt and an install line that names neither
    path unambiguously -- the check must not silently pick one."""
    (repo / "sub").mkdir(exist_ok=True)
    (repo / "sub" / "requirements.txt").write_text("subpkg>=1\n", encoding="utf-8")
    (repo / "requirements.txt").write_text("rootpkg>=1\n", encoding="utf-8")
    (repo / "Dockerfile.copyrename").write_text(
        "COPY sub/requirements.txt ./requirements.txt\n"
        "RUN pip install -r requirements.txt\n",
        encoding="utf-8",
    )
    _git(["git", "add", "-A"], repo)
    result = dc.scan(repo, docs=[], reports=[])
    assert any("BASENAME only" in n for n in result.notes)


def test_untracked_file_on_disk_is_reported_not_accepted(dc, repo):
    """A doc pointing at a file only this machine has is a broken instruction
    for everyone else, and accepting it makes the result machine-dependent."""
    rel = _doc(repo, "untracked.md", "Run `scripts/local_only.sh` first.\n")
    # Written AFTER the fixture's `git add -A`, so it exists on disk and is
    # genuinely untracked -- the state that made the result machine-dependent.
    (repo / "scripts").mkdir(exist_ok=True)
    (repo / "scripts" / "local_only.sh").write_text("echo hi\n", encoding="utf-8")
    found = _kinds(dc.scan(repo, docs=[rel], reports=[]), "path")
    assert len(found) == 1
    assert "NOT tracked" in found[0].detail


# ── The proof, on the real repo, through the Part 1 helper ───────────────────
#
# Everything above runs against a synthetic fixture, which proves the logic and
# nothing about this repository. These two plant into a REAL tracked document
# and run the REAL checker over it. They are also the first production use of
# scripts/falsifiability.py: the plant is hash-verified before the assertion
# runs, and the restore is hash-verified in a finally block, so a test that dies
# mid-run cannot leave the mutation behind (and if the process is killed outright,
# the sidecar it leaves blocks the next push).

_ROOT = Path(__file__).resolve().parents[1]
_VICTIM = _ROOT / "docs" / "QA-DATA-PROVENANCE.md"


@pytest.fixture(scope="module")
def fz():
    spec = importlib.util.spec_from_file_location(
        "falsifiability_for_doc_claims", _ROOT / "scripts" / "falsifiability.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.skipif(not _VICTIM.is_file(), reason="doc not present in this checkout")
def test_planting_a_nonexistent_test_path_goes_red(dc, fz):
    rel = _VICTIM.relative_to(_ROOT).as_posix()
    anchor = "# QA & Data Provenance"

    clean = [v.claim for v in dc.scan(_ROOT, docs=[rel], reports=[]).violations]
    assert "tests/test_apra_sa3_correlation.py" not in clean

    with fz.planted(
        _VICTIM,
        anchor,
        anchor + "\n\nVerified by `tests/test_apra_sa3_correlation.py`.",
        label="doc-claim proof: phantom test path",
    ):
        found = [
            v.claim
            for v in dc.scan(_ROOT, docs=[rel], reports=[]).violations
            if v.kind == "path"
        ]
        assert "tests/test_apra_sa3_correlation.py" in found, (
            "the check stayed green with a phantom test path planted -- it "
            "cannot catch the #887 defect it was written for"
        )

    after = [v.claim for v in dc.scan(_ROOT, docs=[rel], reports=[]).violations]
    assert after == clean, "the finding must disappear once the plant is undone"


@pytest.mark.skipif(not _VICTIM.is_file(), reason="doc not present in this checkout")
def test_planting_a_mismatched_version_goes_red(dc, fz):
    rel = _VICTIM.relative_to(_ROOT).as_posix()
    anchor = "# QA & Data Provenance"

    constants = dc.code_version_constants(_ROOT, dc.tracked_files(_ROOT))
    assert "methodology_version" in constants, "no code constant to disagree with"
    bogus = "9.9"
    assert bogus not in constants["methodology_version"]

    with fz.planted(
        _VICTIM,
        anchor,
        anchor + f"\n\nScoring follows methodology_version {bogus}.",
        label="doc-claim proof: mismatched version",
    ):
        found = [
            v.claim
            for v in dc.scan(_ROOT, docs=[rel], reports=[]).violations
            if v.kind == "version"
        ]
        assert f"methodology_version = {bogus}" in found, (
            "the check stayed green with a version the code does not hold -- it "
            "cannot catch the v1.2 defect it was written for"
        )

    residual = [
        v for v in dc.scan(_ROOT, docs=[rel], reports=[]).violations
        if v.kind == "version"
    ]
    assert residual == [], "the finding must disappear once the plant is undone"
