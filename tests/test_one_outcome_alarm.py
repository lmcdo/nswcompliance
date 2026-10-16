"""One alarm on the outcome, instead of nine heartbeats on the processes.

WHY THE NINE WENT
-----------------
`run_monitors.py` can give every Railway stage its own healthchecks.io URL. Measured on
the live fleet 2026-09-28 that arrangement was misconfigured NINE TIMES OUT OF NINE: six
services shared the literal `https://hc-ping.com/placeholder-satellite`, which is not a
check, and three had none. Nine config points, one operator.

Worse, a per-stage heartbeat answers the wrong question. It says a process started, not
that it did anything — `dcp-monitor` can sweep, be refused by every council's WAF, skip
all of them and exit 0, and its ping goes out green.

So the failure moved to the one place it cannot be faked: `.github/workflows/
freshness-alarm.yml` runs the DQ ledger daily from outside Railway and pings ONE check
only when the ledger is green. Data stale -> no ping -> alert. Workflow dead -> no ping
-> alert. It cannot read green while what we serve is stale, because what it reports on
IS what we serve.

AND THE WINDOW WAS WRONG
------------------------
DQ-117 shipped with a 10-day window, on the opening prompt's assertion that the cron was
"weekly Mon 02:00 UTC". `railway.dcp-monitor.toml` in this repo says:

    cronSchedule = "0 2 1,15 * *"   # fortnightly: 1st and 15th, 02:00 UTC

A 10-day window on a 14-to-17-day cycle is RED WHILE NOTHING IS WRONG, every cycle, for
ever — which destroys the one thing a ledger row is for. Corrected to 17 days, the
longest healthy gap (15 Jan -> 1 Feb).

What is NOT touched is the median-versus-max statistic. That was a real defect in the
drafted query and is independent of the window: six wollongong chapters first checked on
2026-09-24 moved a fleet `max()` to four days ago while 499 chapters sat 13 days old, so
`max()` reads green mid-outage at ANY window.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MONITOR = (ROOT / "scripts" / "run_monitors.py").read_text(encoding="utf-8")
PROBE = (ROOT / "scripts" / "dq_probe_live.py").read_text(encoding="utf-8")
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "freshness-alarm.yml"
TOML = ROOT / "railway.dcp-monitor.toml"


def _dq117_sql(code_only: bool = False) -> str:
    """The DQ-117 probe entry. code_only strips comment lines.

    Needed because the entry EXPLAINS what it rejected: its comment names
    `max(url_last_checked)` while saying why the median replaced it. A source scan that
    reads prose as code cannot tell a fix from a description of the fix -- the same trap
    that failed two tests in tests/test_an_alert_carries_its_own_cause.py.
    """
    i = PROBE.index('"DQ-117"')
    j = PROBE.index('"DQ-69"', i)
    block = PROBE[i:j]
    if not code_only:
        return block
    return "\n".join(l for l in block.splitlines() if not l.strip().startswith("#"))


class TestTheWindowMatchesTheRealSchedule:
    def test_the_declared_cron_is_fortnightly(self):
        """The fact the window is derived from. If the schedule file changes, this test
        fails and the window has to be revisited rather than silently drifting."""
        assert TOML.exists(), "railway.dcp-monitor.toml is gone; the window's basis is"
        text = TOML.read_text(encoding="utf-8")
        m = re.search(r'cronSchedule\s*=\s*"([^"]+)"', text)
        assert m, "dcp-monitor declares no cronSchedule"
        assert m.group(1).strip() == "0 2 1,15 * *", (
            f"the sweep's schedule changed to {m.group(1)!r}. DQ-117's 17-day window "
            f"was derived from a fortnightly 1st-and-15th cron; re-derive it."
        )

    def test_the_window_is_seventeen_days(self):
        assert "INTERVAL '17 days'" in _dq117_sql()

    def test_the_ten_day_window_is_gone(self):
        """10 days on a 14-to-17-day cycle is red while nothing is wrong."""
        assert "INTERVAL '10 days'" not in _dq117_sql(), (
            "the 10-day window is back, so DQ-117 will read red on a healthy "
            "fortnightly schedule every cycle"
        )

    def test_seventeen_covers_the_longest_healthy_gap(self):
        """15 Jan -> 1 Feb is 17 days, the widest gap a 1st-and-15th cron produces.
        Computed, not asserted, so a leap year or a month length cannot surprise it."""
        from datetime import date
        gaps = []
        for year in (2025, 2026, 2027, 2028):
            for month in range(1, 13):
                nxt = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
                gaps.append((nxt - date(year, month, 15)).days)
                gaps.append((date(year, month, 15) - date(year, month, 1)).days)
        assert max(gaps) == 17, f"the widest 1st/15th gap is {max(gaps)}, not 17"
        assert "INTERVAL '17 days'" in _dq117_sql()

    def test_the_wrong_premise_is_recorded_not_quietly_fixed(self):
        """A window changed with no reason recorded is a window someone changes back."""
        sql = _dq117_sql()
        assert "fortnightly" in sql.lower()
        assert "weekly" in sql.lower(), (
            "the comment no longer says what the window was wrongly based on, so the "
            "next reader cannot tell the 10 was a mistake rather than a choice"
        )


class TestTheMedianSurvivedTheCorrection:
    """The window was wrong; the statistic was not. Keep them separable."""

    def test_it_still_uses_the_median(self):
        assert "percentile_disc(0.5)" in _dq117_sql()

    def test_it_does_not_use_max(self):
        assert "max(url_last_checked)" not in _dq117_sql(code_only=True), (
            "back to a fleet max(), which reads green as soon as any one council is "
            "touched — six wollongong chapters did exactly that on 2026-09-24"
        )

    def test_nulls_still_sort_as_maximally_stale(self):
        assert "'-infinity'::timestamptz" in _dq117_sql()

    def test_an_empty_population_still_reads_one(self):
        """percentile_disc over zero rows is NULL, and a NULL count prints CLEAN."""
        assert "COALESCE(percentile_disc" in _dq117_sql()


class TestAMissingStageHeartbeatIsAWarningNotAFailure:
    def test_the_exit_code_is_no_longer_returned(self):
        """Seven of nine live stages have no usable URL. Failing on that meant seven
        red jobs per cycle for a configuration gap, which teaches an operator to ignore
        the channel — the same end state as no alarm, reached faster."""
        tail = MONITOR[MONITOR.index("resolved = 0 if exit_code == 2"):]
        assert "return EXIT_NO_DEADMAN_SWITCH" not in tail, (
            "a stage without its own heartbeat fails its run again"
        )

    def test_it_still_warns_by_name(self):
        tail = MONITOR[MONITOR.index("resolved = 0 if exit_code == 2"):]
        assert "WARNING" in tail and "not being" in tail
        assert "{monitor_name}" in tail, "the warning must name the stage"

    def test_the_detection_is_untouched(self):
        """Only the consequence changed. The four states must still be detected, or the
        diagnostic is gone as well as the failure."""
        assert "def deadman_switch_problem(" in MONITOR
        assert "switch_problem = deadman_switch_problem(monitor_name, hc_url)" in MONITOR

    def test_a_misconfigured_url_is_still_never_pinged(self):
        """Pinging another stage's check holds THAT stage's alarm green. A bad value
        stays worse than no value, regardless of what the exit code does."""
        assert "not pinging" in MONITOR

    def test_a_real_crash_still_fails(self):
        """The step back must not have swallowed genuine failures."""
        tail = MONITOR[MONITOR.index("resolved = 0 if exit_code == 2"):]
        assert "return resolved" in tail

    def test_the_constant_says_it_is_no_longer_returned(self):
        """It is kept for the tests and for a future re-tightening. A constant that
        looks live but is not is how someone re-adds the seven alerts by accident."""
        head = MONITOR[:MONITOR.index("EXIT_NO_DEADMAN_SWITCH = 3")]
        assert "NO LONGER RETURNED" in head


class TestTheOutcomeAlarmExists:
    """The failure had to land somewhere before it was taken off the stages."""

    def test_the_workflow_exists(self):
        assert WORKFLOW_PATH.exists(), (
            "the per-stage failure was removed and nothing replaced it, which leaves "
            "no alarm at all"
        )

    def test_it_runs_on_a_schedule_not_only_by_hand(self):
        y = WORKFLOW_PATH.read_text(encoding="utf-8")
        assert "schedule:" in y and "cron:" in y

    def test_it_asks_the_freshness_rows(self):
        y = WORKFLOW_PATH.read_text(encoding="utf-8")
        assert "DQ-117" in y and "DQ-70" in y

    def test_it_pings_only_on_success(self):
        """A ping sent regardless of the result is a heartbeat, and a heartbeat is what
        this replaces."""
        y = WORKFLOW_PATH.read_text(encoding="utf-8")
        i = y.index("Tell the watchdog we are current")
        assert "if: success()" in y[i - 200:i + 200]

    def test_a_missing_ping_secret_fails_loudly(self):
        """A workflow that skips its own ping when unconfigured is the silent-no-switch
        defect again, one layer out."""
        y = WORKFLOW_PATH.read_text(encoding="utf-8")
        assert "HC_PING_FRESHNESS is not set" in y
        assert y.count("exit 1") >= 3

    def test_it_reads_the_ping_response_body(self):
        """healthchecks.io answers 200 with "OK (not found)" for a URL naming no check,
        measured 2026-09-28. A 2xx is not proof the ping landed.

        Asserted on the shell CASE PATTERN, not on the words: the workflow explains
        this behaviour in a comment, so "not found" appears whether or not the check
        exists. A mutation that changed only the pattern survived a looser version of
        this test -- the same comment-versus-code trap as elsewhere in this branch."""
        y = WORKFLOW_PATH.read_text(encoding="utf-8")
        code = chr(10).join(l for l in y.splitlines()
                            if not l.strip().startswith("#"))
        assert '*"not found"*' in code, (
            "the ping response body is no longer matched against 'not found', so a URL "
            "naming no check reports a successful heartbeat")
        assert 'case "$body" in' in code

    def test_a_missing_database_url_fails_rather_than_skips(self):
        y = WORKFLOW_PATH.read_text(encoding="utf-8")
        assert "DATABASE_URL secret is not set" in y

    def test_it_runs_outside_railway(self):
        """§5.2 invariant 8: an alarm inside the thing it watches cannot report that
        thing's silence."""
        y = WORKFLOW_PATH.read_text(encoding="utf-8")
        assert "runs-on: ubuntu-latest" in y


class TestTheManifestDescribesWhatTheGuardNowDoes:
    def test_the_guard_entry_no_longer_promises_an_exit_code(self):
        import json
        m = json.loads((ROOT / ".claude" / "dcp_pipeline_manifest.json")
                       .read_text(encoding="utf-8"))
        g = next(x for x in m["guards"] if x["id"] == "deadman_switch_is_loud")
        assert "REPORTS" in g["purpose"], (
            "the manifest still says stages refuse to look healthy, which is no longer "
            "what the code does"
        )
        assert "freshness-alarm" in g["purpose"], (
            "the manifest does not say where the failure went, so a reader concludes it "
            "was simply dropped"
        )


class TestEverythingStillParses:
    def test_run_monitors_parses(self):
        ast.parse(MONITOR)

    def test_the_probe_parses(self):
        ast.parse(PROBE)

    def test_the_workflow_is_valid_yaml(self):
        import importlib.util
        if importlib.util.find_spec("yaml") is None:
            # PyYAML is in requirements-test.txt; if absent, assert structurally
            # rather than skipping silently.
            y = WORKFLOW_PATH.read_text(encoding="utf-8")
            assert y.lstrip().startswith("#") or y.lstrip().startswith("name:")
            assert "\t" not in y, "a tab in YAML is a parse error"
            return
        import yaml
        doc = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
        assert doc["name"] == "freshness-alarm"
        assert "freshness" in doc["jobs"]
