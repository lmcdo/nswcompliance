"""The CI plan-line check and the plan-line-gate hook must guard the same files."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_pr_plan_line as ci  # noqa: E402


def _hook():
    spec = importlib.util.spec_from_file_location("plan_hook", ROOT / ".claude" / "hooks" / "plan-line-gate.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_hook_and_ci_guard_the_same_pipeline_files():
    assert tuple(ci.PIPELINE) == tuple(_hook().PIPELINE)


def test_a_pipeline_pr_without_a_plan_line_fails():
    assert ci.pipeline_changes(["scripts/dcp_extract_changed.py", "README.md"]) == ["scripts/dcp_extract_changed.py"]
    assert not ci.has_plan_line("## What\nfaster reads\n\n## Why\nslow")


def test_plan_lines_that_count():
    assert ci.has_plan_line("Plan: ce-dcp-section-updater-PLAN-2026-10-26.md -- step 3")
    assert ci.has_plan_line("**Plan:** none -- guardrails")


def test_a_sentence_mentioning_a_plan_is_not_a_plan_line():
    assert not ci.has_plan_line("We should follow the plan: carefully.")
    assert not ci.has_plan_line("Plan: soon")              # names neither a .md nor none


def test_a_pr_touching_no_pipeline_file_needs_nothing():
    assert ci.pipeline_changes(["frontend-nextjs/lib/coverage.ts", "tests/x.py"]) == []


def test_the_plan_line_needs_a_section_not_just_a_file_like_word():
    assert not ci.has_plan_line("Plan: invented.mdXYZ")
    assert not ci.has_plan_line("Plan: ce-x-PLAN.md")                    # no section
    assert ci.has_plan_line("Plan: ce-x-PLAN.md -- step 3 section reader")
