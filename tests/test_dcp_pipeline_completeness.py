"""Pipeline-completeness gate — the #506-catcher.

Migration #506 silently deleted the extract-to-review and commit stages of the
DCP pipeline; nothing failed, so it went unnoticed until the watchdog screamed
days later. This test asserts every intended DCP stage has a registered monitor
and a backing script. Deleting a stage (or its script) fails the push.

Source-inspection only — no imports, so it runs in the mocked pre-push env.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# The intended DCP pipeline stages. If a stage is genuinely retired, remove it
# here *deliberately* — that edit is the audit trail.
REQUIRED_MONITORS = ("dcp-monitor", "dcp-extract", "dcp-commit", "dcp-watchdog")

REQUIRED_SCRIPTS = (
    "scripts/r2_monitor.py",            # detect
    "scripts/dcp_extract_changed.py",   # extract-to-review (enqueue)
    "scripts/dcp_commit_approved.py",   # commit-on-approve
    "scripts/dcp_watchdog.py",          # stuck-chapter alarm
)


def _src(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class TestDcpPipelineCompleteness:
    def test_every_stage_has_a_monitor(self):
        src = _src("scripts/run_monitors.py")
        for name in REQUIRED_MONITORS:
            assert f'"{name}"' in src, (
                f"DCP pipeline stage '{name}' is missing from run_monitors.MONITORS. "
                f"A pipeline stage was dropped — this is the #506 regression class. "
                f"If retiring it is intentional, remove it from REQUIRED_MONITORS too."
            )

    def test_every_stage_script_exists(self):
        for rel in REQUIRED_SCRIPTS:
            assert (ROOT / rel).exists(), f"Pipeline script {rel} is missing."

    def test_commit_monitor_actually_commits(self):
        """A dcp-commit monitor that forgets --commit is a silent no-op."""
        src = _src("scripts/run_monitors.py")
        # The commit worker defaults to dry-run; the monitor must pass --commit.
        assert "dcp_commit_approved.py" in src
        assert "--commit" in src, (
            "dcp-commit monitor must invoke dcp_commit_approved.py with --commit, "
            "otherwise it dry-runs and never commits approved chapters."
        )

    def test_commit_worker_defaults_to_dry_run(self):
        """The worker must require --commit to write — accidental runs stay safe."""
        src = _src("scripts/dcp_commit_approved.py")
        assert 'add_argument(' in src and '"--commit"' in src
        assert "dry_run = not args.commit" in src, (
            "dcp_commit_approved.py must default to dry-run (commit only with --commit)."
        )

    @pytest.mark.parametrize("rel", REQUIRED_SCRIPTS + ("scripts/run_monitors.py",))
    def test_scripts_are_whitelisted_in_gitignore(self, rel):
        """scripts/ is gitignored; each pipeline script needs a ! whitelist or it
        silently drops from commits (the bug that lost dcp_commit_approved.py once)."""
        if rel == "scripts/run_monitors.py":
            return  # already tracked long-term; the DCP scripts are the risk
        gi = _src(".gitignore")
        assert f"!{rel}" in gi, (
            f"{rel} is not whitelisted in .gitignore — a new commit could silently "
            f"exclude it (scripts/ is ignored)."
        )
