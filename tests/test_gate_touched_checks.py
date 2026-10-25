"""gate_touched_checks: a PR runs a live-data gate step only when it changes that step's files.

Real cases from 2026-10-23..25: PR #1494 (monitor probe) touched no ledger file and was blocked by DQ-104/105;
PR #1472 marked DQ-79 fixed and so MUST run the ledger.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import gate_touched_checks as g  # noqa: E402

PR_1494 = ["Dockerfile.monitors", "scripts/run_monitors.py", "scripts/probe_blocked_councils.py",
           "scripts/requirements-monitor.txt", "tests/test_verifyops_deploy_check.py",
           ".qa/reports/feat__dcp-monitor-blocked-council-probe.json"]
PR_1472 = [".claude/DATA_QUALITY_TRACKER.md", ".claude/dq_checks.json", ".qa/reports/chore__dq79-fixed-size-fix.json"]


def test_monitor_pr_runs_no_live_data_check():
    assert not any(g.decide(PR_1494).values())


def test_marking_a_row_fixed_runs_the_ledger_and_outreach():
    d = g.decide(PR_1472)
    assert d["LEDGER"] and d["OUTREACH"]
    assert not d["SERVED_ANSWER"] and not d["RAILWAY_CRON"]


def test_changing_a_probe_runs_the_ledger():
    assert g.decide(["scripts/dq_probe_unchecked_rows.py"])["LEDGER"]


def test_each_check_runs_when_its_own_files_change():
    assert g.decide(["scripts/check_served_answer_quality.py"])["SERVED_ANSWER"]
    assert g.decide([".claude/served_answer_quality_baseline.json"])["SERVED_ANSWER"]
    assert g.decide(["scripts/control_source_values_baseline.json"])["CONTROL_VALUES"]
    assert g.decide(["railway.dcp-monitor.toml"])["RAILWAY_CRON"]
    assert g.decide(["scripts/dcp_page_map_gate.py"])["PAGE_MAPS"]


def test_wiring_change_or_unreadable_diff_runs_everything():
    assert all(g.decide([".github/workflows/gates.yml"]).values())
    assert all(g.decide(["scripts/gate_touched_checks.py"]).values())
    assert all(g.decide(None).values())


def test_every_key_maps_to_a_gate_step():
    src = (ROOT / ".github" / "workflows" / "gates.yml").read_text(encoding="utf-8")
    for key in g.CHECKS:
        assert f"env.RUN_{key} == '1'" in src, key
    assert "check_data_watch_freshness.py" not in src


def test_the_nightly_job_is_still_watched_from_outside():
    fa = (ROOT / ".github" / "workflows" / "freshness-alarm.yml").read_text(encoding="utf-8")
    assert "python scripts/check_data_watch_freshness.py" in fa
    assert '--rc "datawatch=${{ steps.datawatch.outputs.rc }}"' in fa


def test_a_database_timeout_is_unknown_not_red():
    import dq_probe_applicability_config as a
    import dq_probe_unchecked_rows as u

    class OperationalError(Exception): ...
    class QueryCanceledError(OperationalError): ...
    for mod in (u, a):
        assert mod._db_gave_up(QueryCanceledError("canceling statement due to statement timeout"))
        assert mod._db_gave_up(OperationalError("SSL connection has been closed unexpectedly"))
        assert not mod._db_gave_up(ValueError("a real bug"))
