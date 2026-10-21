"""check_railway_jobs_ran.judge: red on a crashed run, a missed run, a stuck run or
deploy, a failed deploy, or anything it does not know.

prior-art-checked: tests/test_railway_cron_drift.py covers schedules, not runs.

SNAPSHOT is copied from Railway's API for production on 2026-10-21 (~07:40 UTC):
each job's schedule, latest deployment, and its newest run (deploymentInstanceExecutions).
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from check_railway_jobs_ran import judge, last_due  # noqa: E402

NOW = datetime(2026, 10, 21, 7, 40, tzinfo=timezone.utc)


def _job(name, cron, run_at, run_status, deploy="SUCCESS", deploy_at="2026-10-21T06:22:08Z"):
    runs = [{"createdAt": run_at, "status": run_status}] if run_at else []
    return {"name": name, "cronSchedule": cron, "runs": runs,
            "latestDeployment": {"status": deploy, "createdAt": deploy_at} if deploy else None}


SNAPSHOT = [
    _job("maintenance-mutation", "0 6 1 * *", "2026-10-01T06:01:00Z", "CRASHED", "FAILED"),
    _job("dcp-commit", "0 9 * * *", "2026-10-20T09:03:00Z", "CRASHED"),
    _job("dcp-extract", "0 3 * * *", "2026-10-21T03:02:56Z", "CRASHED"),
    _job("maintenance-security", "0 9 * * 1", "2026-10-19T09:02:00Z", "EXITED", "FAILED"),
    _job("monitor-satellite", "0 6 * * 1", "2026-10-19T06:03:00Z", "EXITED"),
    _job("dcp-monitor", "0 2 1,15 * *", "2026-10-15T02:00:00Z", "CRASHED"),
    _job("brief-drift-check", "0 3 * * 1", "2026-10-19T03:00:00Z", "EXITED"),
    _job("monitor-watchdog", "0 10 * * 3", "2026-10-14T10:02:00Z", "EXITED"),
    _job("nswcompliance", None, None, None),
]


def _names(problems):
    return sorted({p.split(":")[0].strip() for p in problems})


def test_the_real_snapshot_flags_exactly_the_five_bad_jobs():
    problems, checked = judge(SNAPSHOT, NOW)
    assert checked == 8  # the web app has no schedule and is not judged
    assert _names(problems) == ["dcp-commit", "dcp-extract", "dcp-monitor",
                                "maintenance-mutation", "maintenance-security"]


def test_healthy_jobs_pass():
    healthy = [j for j in SNAPSHOT if j["name"] in ("monitor-satellite", "brief-drift-check", "monitor-watchdog")]
    assert judge(healthy, NOW) == ([], 3)


def test_a_missed_run_is_red_even_when_everything_says_success():
    """Cross-review: status SUCCESS and a future next run, but the 03:00 run never started."""
    problems, _ = judge([_job("dcp-extract", "0 3 * * *", "2026-10-20T03:02:00Z", "EXITED")], NOW)
    assert problems and "none happened" in problems[0]


def test_a_job_that_has_never_run_is_red():
    problems, _ = judge([_job("new-job", "0 3 * * *", None, None)], NOW)
    assert problems and "last run: never" in problems[0]


def test_a_run_within_the_grace_is_not_yet_missed():
    # due 07:00, now 07:40, grace 2h: not judged missed yet; yesterday's run is fine
    assert judge([_job("j", "0 7 * * *", "2026-10-20T07:01:00Z", "EXITED")], NOW) == ([], 1)


def test_stuck_runs_and_deploys_are_red():
    run, _ = judge([_job("j", "0 1 * * *", "2026-10-21T01:00:00Z", "RUNNING")], NOW)  # 6h40 ago
    dep, _ = judge([_job("j", "0 3 * * *", "2026-10-21T03:00:00Z", "EXITED", "BUILDING", "2026-10-20T20:00:00Z")], NOW)
    assert run and "stuck" in run[0]
    assert dep and "stuck" in dep[0]


def test_unfinished_or_unknown_outcomes_are_red():
    for status in ("SKIPPED", "REMOVED", "", "SOMETHING_NEW"):
        problems, _ = judge([_job("j", "0 3 * * *", "2026-10-21T03:00:00Z", status)], NOW)
        assert problems, status
    problems, _ = judge([_job("j", "0 3 * * *", "2026-10-21T03:00:00Z", "EXITED", None)], NOW)
    assert problems and "unknown" in problems[0]


def test_last_due_for_every_schedule_in_use():
    at = datetime(2026, 10, 21, 5, 40, tzinfo=timezone.utc)  # a Wednesday
    assert last_due("0 3 * * *", at) == datetime(2026, 10, 21, 3, 0, tzinfo=timezone.utc)
    assert last_due("0 2 1,15 * *", at) == datetime(2026, 10, 15, 2, 0, tzinfo=timezone.utc)
    assert last_due("0 9 * * 1", at) == datetime(2026, 10, 19, 9, 0, tzinfo=timezone.utc)
    assert last_due("0 6 1 * *", at) == datetime(2026, 10, 1, 6, 0, tzinfo=timezone.utc)
    assert last_due("0 10 * * 3", at) == datetime(2026, 10, 14, 10, 0, tzinfo=timezone.utc)


def test_the_alert_says_what_happened():
    """The line is what a person reads at 6am: it must name the failure, not just 'unknown'."""
    problems, _ = judge(SNAPSHOT, NOW)
    text = "\n".join(problems)
    assert "dcp-extract: last run (2026-10-21T03:02) exited with an error" in text
    assert "maintenance-security: latest deploy FAILED" in text
