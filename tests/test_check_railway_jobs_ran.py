"""check_railway_jobs_ran.judge: red on a crashed run, a failed deploy, an overdue run,
or a status it does not know.

prior-art-checked: tests/test_railway_cron_drift.py covers schedules, not outcomes.

The SNAPSHOT rows are copied from `railway status --json` for production on
2026-10-21 (~07:30 UTC), trimmed to the fields judge reads. That day the two
maintenance jobs' latest deployments were FAILED with no build.
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from check_railway_jobs_ran import judge  # noqa: E402

NOW = datetime(2026, 10, 21, 7, 30, tzinfo=timezone.utc)


def _job(name, status, nxt, cron="0 3 * * *"):
    return {"name": name, "cronSchedule": cron, "nextCronRunAt": nxt,
            "latestDeployment": {"status": status} if status is not None else None}


SNAPSHOT = [
    _job("maintenance-mutation", "FAILED", "2026-11-01T06:00:00Z", "0 6 1 * *"),
    _job("dcp-commit", "SUCCESS", "2026-10-21T09:00:00Z", "0 9 * * *"),
    _job("dcp-extract", "SUCCESS", "2026-10-22T03:00:00Z", "0 3 * * *"),
    _job("maintenance-security", "FAILED", "2026-10-26T09:00:00Z", "0 9 * * 1"),
    _job("monitor-satellite", "SUCCESS", "2026-10-26T06:00:00Z", "0 6 * * 1"),
    _job("dcp-monitor", "SUCCESS", "2026-11-01T02:00:00Z", "0 2 1,15 * *"),
    _job("brief-drift-check", "SUCCESS", "2026-10-26T03:00:00Z", "0 3 * * 1"),
    _job("monitor-watchdog", "SUCCESS", "2026-10-21T10:00:00Z", "0 10 * * 3"),
    _job("nswcompliance", "SUCCESS", None, None),
    _job("dcp-extract-all", "SUCCESS", None, None),
    _job("property-alerts", "SUCCESS", None, None),
]


def test_the_real_snapshot_flags_exactly_the_two_failed_deploys():
    problems, checked = judge(SNAPSHOT, NOW)
    assert checked == 8  # the three with no schedule are not judged
    assert [p.split(":")[0].strip() for p in problems] == ["maintenance-mutation", "maintenance-security"]


def test_a_crashed_run_is_red():
    """The 2026-10-21 incident: dcp-extract crashing on every run."""
    problems, _ = judge([_job("dcp-extract", "CRASHED", "2026-10-22T03:00:00Z")], NOW)
    assert problems and "exited with an error" in problems[0]


def test_an_overdue_run_is_red_after_the_grace():
    late, _ = judge([_job("dcp-commit", "SUCCESS", "2026-10-21T05:00:00Z")], NOW)
    on_time, _ = judge([_job("dcp-commit", "SUCCESS", "2026-10-21T06:00:00Z")], NOW)
    assert late and "scheduler stopped" in late[0]
    assert on_time == []


def test_unknown_or_missing_state_is_red():
    for status in (None, "", "SOMETHING_NEW"):
        problems, _ = judge([_job("dcp-extract", status, "2026-10-22T03:00:00Z")], NOW)
        assert problems, status
    problems, _ = judge([_job("dcp-extract", "SUCCESS", None)], NOW)
    assert problems and "no next run" in problems[0]


def test_healthy_jobs_pass():
    problems, checked = judge([j for j in SNAPSHOT if not j["name"].startswith("maintenance")], NOW)
    assert problems == [] and checked == 6
