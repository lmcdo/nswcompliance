"""Tests for the quarantine ratchet.

The ratchet's whole value is the SECOND rule — that a fixed test cannot stay
quarantined. Rule one (no new debt) is the obvious half and every baseline has
it. Rule two is what stops the baseline becoming the thing it replaced: a list
where entries go to be forgotten.

So the load-bearing test here is
test_a_baseline_entry_that_now_passes_is_an_error.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "quarantine_mod",
    Path(__file__).parent.parent / "scripts" / "check_test_quarantine.py",
)
q = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(q)


# --- reading the real repo state -----------------------------------------

def test_reads_the_quarantine_list_from_conftest():
    files = q.quarantined_test_files()
    assert isinstance(files, list)
    # Only test files count as debt. conftest also ignores utility scripts
    # (check_*.py, verify_*.py, analyze_*.py); treating those as debt would
    # inflate the number and make it meaningless.
    assert all(f.startswith("test_") for f in files)


def test_utility_scripts_are_not_counted_as_debt():
    files = q.quarantined_test_files()
    for noise in ("check_pdf_urls.py", "analyze_dcp_general_structure.py",
                  "quick_test.py", "processing", "root_tests"):
        assert noise not in files


def test_every_quarantined_file_has_a_baseline_entry():
    """Rule one, asserted against the real repo rather than a fixture.

    If someone adds a file to collect_ignore without recording why, this fails
    here as well as in CI.
    """
    files = set(q.quarantined_test_files())
    baseline = set(q.load_baseline())
    undocumented = files - baseline
    assert not undocumented, (
        f"quarantined with no recorded reason: {sorted(undocumented)}"
    )


def test_no_baseline_entry_for_a_file_that_is_not_quarantined():
    """Rule three: stale bookkeeping is also an error."""
    files = set(q.quarantined_test_files())
    baseline = set(q.load_baseline())
    orphans = baseline - files
    assert not orphans, f"baseline lists non-quarantined files: {sorted(orphans)}"


def test_every_baseline_entry_records_a_measured_error():
    """An entry saying only 'broken' would recreate the original problem.

    The point of the baseline over collect_ignore is that it carries evidence.
    An entry without a measured error and a cause is just a longer ignore list.
    """
    for name, entry in q.load_baseline().items():
        assert entry.get("error"), f"{name}: no error recorded"
        assert entry.get("cause"), f"{name}: no cause recorded"
        assert entry.get("measured"), f"{name}: no measurement recorded"
        # The vocabulary is closed on purpose. A free-text status would let
        # "flaky" or "wontfix" creep in, and those are the words debt hides
        # behind. Each value here names a DIFFERENT next action:
        #   broken            — a real defect in the test; fix it
        #   partial           — some tests pass; split the file to release them
        #   needs-live-server — a genuine integration test; needs a skip guard
        #                       and an integration marker, not repair
        #   blocked-by-mock   — the test is fine; the shared test environment
        #                       prevents it running
        #   not-a-test        — contains no test functions; delete or convert
        assert entry.get("status") in {
            "broken", "partial", "needs-live-server", "blocked-by-mock", "not-a-test",
        }, f"{name}: unknown status {entry.get('status')!r}"


# --- the pass/fail decision ----------------------------------------------

def test_a_file_that_passes_is_reported_as_clean(tmp_path, monkeypatch):
    """A green file must be detected so the ratchet can demand its release."""
    t = tmp_path / "tests"
    t.mkdir()
    (t / "test_green.py").write_text("def test_ok():\n    assert True\n")
    monkeypatch.setattr(q, "REPO", tmp_path)
    clean, summary = q.run_one("test_green.py")
    assert clean is True
    assert "passed" in summary


def test_a_file_that_fails_is_not_clean(tmp_path, monkeypatch):
    t = tmp_path / "tests"
    t.mkdir()
    (t / "test_red.py").write_text("def test_no():\n    assert False\n")
    monkeypatch.setattr(q, "REPO", tmp_path)
    clean, summary = q.run_one("test_red.py")
    assert clean is False
    assert "failed" in summary


def test_a_file_that_only_skips_is_not_treated_as_clean(tmp_path, monkeypatch):
    """The subtle one.

    A file whose every test skips reports success and exit code 0. Promoting it
    out of quarantine on that basis would mean congratulating ourselves for a
    test that protects nothing — the same self-deception, one layer up. It must
    stay quarantined until it actually runs.
    """
    t = tmp_path / "tests"
    t.mkdir()
    (t / "test_skipper.py").write_text(
        "import pytest\n"
        "@pytest.mark.skip(reason='needs a server')\n"
        "def test_nope():\n    assert True\n"
    )
    monkeypatch.setattr(q, "REPO", tmp_path)
    clean, summary = q.run_one("test_skipper.py")
    assert clean is False, "an all-skipped file must not count as passing"
    assert "skipped" in summary


def test_a_file_with_no_tests_is_not_clean(tmp_path, monkeypatch):
    """Five of the quarantined files are scripts with no test functions.

    pytest exits 5 with 'no tests ran'. That is not a pass.
    """
    t = tmp_path / "tests"
    t.mkdir()
    (t / "test_empty.py").write_text("x = 1\n")
    monkeypatch.setattr(q, "REPO", tmp_path)
    clean, summary = q.run_one("test_empty.py")
    assert clean is False
    assert "no tests ran" in summary


def test_a_file_that_errors_on_collection_is_not_clean(tmp_path, monkeypatch):
    t = tmp_path / "tests"
    t.mkdir()
    (t / "test_boom.py").write_text("import nonexistent_module_xyz\n")
    monkeypatch.setattr(q, "REPO", tmp_path)
    clean, summary = q.run_one("test_boom.py")
    assert clean is False


def test_the_marker_cannot_hide_a_result_from_the_check(tmp_path, monkeypatch):
    """run_one clears addopts, so `-m "not stale"` cannot deselect the file.

    Without `-o addopts=`, a file carrying pytest.mark.stale would report
    'no tests ran' regardless of its real state — the marker would be hiding
    the file from the very check written to look at it.
    """
    t = tmp_path / "tests"
    t.mkdir()
    (tmp_path / "pytest.ini").write_text(
        "[pytest]\naddopts = -m \"not stale\"\nmarkers =\n    stale: x\n"
    )
    (t / "test_marked.py").write_text(
        "import pytest\npytestmark = pytest.mark.stale\n"
        "def test_ok():\n    assert True\n"
    )
    monkeypatch.setattr(q, "REPO", tmp_path)
    clean, summary = q.run_one("test_marked.py")
    assert clean is True, "the stale marker must not hide the result from the ratchet"
