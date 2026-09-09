"""A config file that reads like configuration but changes nothing.

On 2026-09-10 six of eight Railway services ran a schedule different from
their own railway.*.toml. Railway applies config-as-code only where no
dashboard value is set, so once someone types a value in the dashboard the
file is decoration forever after, and nothing says so. The visible cost:
extraction had been demoted from nightly to weekly, so council chapters
flagged as changed sat unprocessed for days while the watchdog reported them
as "stuck >48h" every week.

These tests cover the comparison logic only -- no network, no token. The
network path is exercised by running the script, and all four of its failure
modes were forced by hand before it was wired into CI (no token locally
skips; no token in CI fails; a bad token fails; an injected file/live mismatch
fails naming both values).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_railway_cron_drift as drift  # noqa: E402


def test_matching_schedules_are_clean():
    assert drift.compare({"dcp-extract": "0 3 * * *"}, {"dcp-extract": "0 3 * * *"}) == []


def test_whitespace_is_not_a_difference():
    """Cron fields are whitespace-separated; the file aligns them with padding.

    railway.dcp-monitor.toml writes its value with trailing spaces before the
    comment. Reporting that as drift would be a false alarm that trains people
    to ignore the check, which is exactly the failure this whole change is
    about.
    """
    assert drift.compare({"s": "0  3 * * *"}, {"s": "0 3 * * *"}) == []


def test_a_different_schedule_is_reported_with_both_values():
    out = drift.compare({"dcp-extract": "0 3 * * *"}, {"dcp-extract": "0 3 * * 1"})
    assert len(out) == 1
    assert "0 3 * * *" in out[0] and "0 3 * * 1" in out[0]


def test_no_cron_at_all_says_the_job_never_runs():
    """The worst case and the least visible: four services were in this state.

    A wrong schedule at least runs something. None means the job has never
    executed, and the file claiming a schedule is what stops anyone looking.
    """
    out = drift.compare({"maintenance-security": "0 9 * * 1"}, {"maintenance-security": None})
    assert len(out) == 1
    assert "never runs" in out[0]


def test_a_service_the_file_names_but_railway_does_not_have_is_reported():
    """A rename or deletion must not read as clean.

    The confusable negative for the whole check: if an absent service were
    skipped rather than reported, deleting a service would silently make its
    drift undetectable -- the check would pass hardest exactly when the job
    stopped existing.
    """
    out = drift.compare({"ghost": "0 1 * * *"}, {"dcp-extract": "0 3 * * *"})
    assert len(out) == 1
    assert "NO SUCH SERVICE" in out[0]


def test_an_intentionally_disabled_service_with_no_cron_is_clean():
    assert drift.compare({"property-alerts": "0 22 * * 0"}, {"property-alerts": None}) == []


def test_an_intentionally_disabled_service_that_gained_a_cron_FAILS():
    """The exception list runs both ways, or it rots.

    An exception that only ever suppresses failures agrees with whatever
    happens to be true. If property-alerts is switched on and the entry is left
    behind, the next person reads 'intentionally off' about a job that is
    running and emailing subscribers.
    """
    out = drift.compare({"property-alerts": "0 22 * * 0"}, {"property-alerts": "0 22 * * 0"})
    assert len(out) == 1
    assert "intentionally disabled" in out[0]
    assert "Remove it from INTENTIONALLY_DISABLED" in out[0]


def test_every_disabled_service_carries_a_reason():
    for service, reason in drift.INTENTIONALLY_DISABLED.items():
        assert len(reason) > 40, f"{service} is excepted without a real reason"


def test_the_declared_map_covers_every_railway_toml():
    """No file may be silently ignored.

    Either it declares a cron and is checked, or it is listed as uncheckable
    with a reason. A file that falls through both is a schedule nobody watches,
    which is the state this check exists to end.
    """
    declared, skipped = drift.declared_schedules()
    on_disk = {p.name for p in ROOT.glob("railway*.toml")}
    accounted = len(declared) + len(skipped)
    assert accounted == len(on_disk), (
        f"{len(on_disk)} railway toml files on disk, {accounted} accounted for. "
        f"declared={sorted(declared)} skipped={skipped}"
    )


@pytest.mark.parametrize("service", ["dcp-extract", "dcp-monitor", "dcp-extract-all",
                                     "dcp-commit", "property-alerts", "brief-drift-check"])
def test_the_real_files_map_to_real_service_names(service):
    """The filename-to-service guess must hold for the services that matter.

    railway.alerts.toml is property-alerts and railway.brief-drift.toml is
    brief-drift-check -- two cases where the filename does not match the
    service. If the derivation silently produced 'alerts', the check would
    report NO SUCH SERVICE forever and be switched off as broken.
    """
    declared, _ = drift.declared_schedules()
    assert service in declared, f"{service} is not covered by any railway toml"
