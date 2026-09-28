"""A stage with no dead-man's switch must say so. It used to say nothing at all.

Rule 4 of the June design -- `docs/DCP_PIPELINE_ARCHITECTURE_2026-06.md` §5.2
invariant 8, *"external dead-man's-switch per stage. Silence trips an alarm."* --
is the only one of the four rules that was never wired, and it is the one whose
job is to make the other three's failures visible. The line where it was lost:

    def ping_healthcheck(url, failed=False):
        if not url:
            return          # <-- no URL configured = silently no switch

MEASURED ON THE LIVE RAILWAY FLEET, 2026-09-28
----------------------------------------------
Not "one shared URL" -- no switch anywhere, in three different ways at once:

    dcp-monitor        HC_PING_URL = https://hc-ping.com/placeholder-satellite
    dcp-extract        HC_PING_URL = https://hc-ping.com/placeholder-satellite
    dcp-extract-all    HC_PING_URL = https://hc-ping.com/placeholder-satellite
    dcp-commit         HC_PING_URL = https://hc-ping.com/placeholder-satellite
    maintenance-mutation                    (same value)
    monitor-satellite                       (same value)
    monitor-watchdog   HC_PING_URL ABSENT   <- the 2026-09-16 `Env missing` alert
    maintenance-security                    ABSENT
    property-alerts                         ABSENT
    brief-drift-check                       ABSENT

`placeholder-satellite` is not a check. Measured against the live service
2026-09-28: a bare slug with no ping key answers `400 invalid url format`, and --
the part that had to be measured rather than assumed -- a well-formed ping to a
UUID that is not a check answers **200 with the body `OK (not found)`**. So a
status-code check alone is NOT sufficient, and the first version of this guard had
that hole. `requests.get` raises on neither. Six services reported a heartbeat to
nothing and four reported nothing at all, and all ten looked exactly like services
that were being watched.

WHY EACH ASSERTION BELOW IS THE ONE THAT MATTERS
------------------------------------------------
A dead-man's switch nobody has forced to trip is not a dead-man's switch
(`memory/feedback-a-check-must-call-the-machine-it-checks.md`,
`memory/feedback-detect-a-guard-by-forcing-its-failure.md`). So every broken
state below is constructed deliberately and asserted to produce BOTH a named
alert and a non-zero exit -- and the healthy state is asserted to produce
neither, because a check that fires on everything is the same as one that fires
on nothing.

The exit code carries it, not Telegram. Telegram is in-band: same container,
same env, same network as the job it reports on, and `send_telegram` swallows its
own failures twice over, so a dead job and a dead alert channel are
indistinguishable from outside. The exit code does not depend on the alert
channel working.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_monitors as rm  # noqa: E402

#: The exact value found on six Railway services on 2026-09-28.
LIVE_PLACEHOLDER = "https://hc-ping.com/placeholder-satellite"

#: A well-formed switch for the dcp-monitor stage, in healthchecks.io's slug form.
GOOD = "https://hc-ping.com/pingkey/dcp-monitor"


class _Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _Response:
    def __init__(self, status_code=200, text="OK"):
        self.status_code = status_code
        #: healthchecks.io signals an unknown check in the BODY, not the status.
        self.text = text


@pytest.fixture
def harness(monkeypatch):
    """Run main() with the monitor, Telegram and healthchecks.io all replaced.

    Returns a dict the test reads afterwards: the Telegram messages that were
    sent and the URLs that were pinged. Nothing leaves the process.
    """
    sent: list[str] = []
    pinged: list[str] = []
    state = {"child_exit": 0, "ping_status": 200, "ping_body": "OK",
             "sent": sent, "pinged": pinged}

    monkeypatch.setenv("MONITOR_NAME", "dcp-monitor")
    monkeypatch.delenv("HC_PING_URL", raising=False)
    monkeypatch.setattr(rm, "send_telegram", lambda msg: sent.append(msg))
    monkeypatch.setattr(
        rm.subprocess, "run",
        lambda *a, **k: _Result(returncode=state["child_exit"]),
    )
    monkeypatch.setattr(
        rm.requests, "get",
        lambda url, **k: pinged.append(url) or _Response(state["ping_status"],
                                                        state["ping_body"]),
    )
    state["env"] = monkeypatch
    return state


def _alerts_about_the_switch(sent: list[str]) -> list[str]:
    return [m for m in sent if "dead-man" in m or "did not land" in m]


class TestAMissingSwitchIsLoud:
    """The state `ping_healthcheck` used to return silently on."""

    def test_no_url_exits_nonzero(self, harness):
        assert rm.main() == rm.EXIT_NO_DEADMAN_SWITCH

    def test_no_url_alerts(self, harness):
        rm.main()
        assert _alerts_about_the_switch(harness["sent"]), (
            "a stage with no dead-man's switch sent no alert -- which is the exact "
            "silence this test exists to remove"
        )

    def test_the_alert_names_the_service(self, harness):
        rm.main()
        assert any("dcp-monitor" in m for m in harness["sent"]), (
            "an alert that does not name the stage cannot be acted on: ten services "
            "share this runner"
        )

    def test_it_alerts_before_running_the_monitor(self, harness, monkeypatch):
        """A stage that dies mid-run may never reach the end of main(), and the one
        thing a reader needs to know is that this run is not being watched."""
        order: list[str] = []
        monkeypatch.setattr(rm, "send_telegram", lambda m: order.append("alert"))
        monkeypatch.setattr(rm.subprocess, "run",
                            lambda *a, **k: order.append("child") or _Result())
        rm.main()
        assert order[:2] == ["alert", "child"]

    def test_the_monitor_still_runs(self, harness, monkeypatch):
        """It must not refuse to work. Stopping the stage to report that the stage is
        unmonitored trades a data outage for a monitoring outage."""
        ran: list[int] = []
        monkeypatch.setattr(rm.subprocess, "run",
                            lambda *a, **k: ran.append(1) or _Result())
        rm.main()
        assert ran == [1]


class TestThePlaceholderThatWasLiveOnSixServices:
    def test_the_measured_value_is_rejected(self, harness):
        harness["env"].setenv("HC_PING_URL", LIVE_PLACEHOLDER)
        assert rm.main() == rm.EXIT_NO_DEADMAN_SWITCH

    def test_it_is_not_pinged(self, harness):
        """Pinging another stage's check holds THAT stage's alarm green, so a wrong
        value is worse than no value: it silences a switch that was working."""
        harness["env"].setenv("HC_PING_URL", LIVE_PLACEHOLDER)
        rm.main()
        assert harness["pinged"] == []

    def test_the_alert_quotes_the_value(self, harness):
        harness["env"].setenv("HC_PING_URL", LIVE_PLACEHOLDER)
        rm.main()
        assert any("placeholder-satellite" in m for m in harness["sent"])


class TestAnotherStagesCheckIsRejected:
    """One URL shared across stages means any single surviving stage keeps the
    check green while the rest are dead -- item 2a's whole point."""

    def test_a_different_stages_slug_is_rejected(self, harness):
        harness["env"].setenv("HC_PING_URL",
                              "https://hc-ping.com/pingkey/satellite-freshness")
        assert rm.main() == rm.EXIT_NO_DEADMAN_SWITCH

    def test_a_prefix_of_this_stages_name_is_rejected(self):
        """`dcp-extract` is a prefix of `dcp-extract-all`, so plain substring
        containment passes the wrong check. Found by forcing this function to fail."""
        problem = rm.deadman_switch_problem(
            "dcp-extract", "https://hc-ping.com/pingkey/dcp-extract-all")
        assert problem and "dcp-extract-all" in problem

    def test_the_reverse_direction_is_also_rejected(self):
        problem = rm.deadman_switch_problem(
            "dcp-extract-all", "https://hc-ping.com/pingkey/dcp-extract")
        assert problem

    def test_a_slug_naming_no_stage_is_rejected(self):
        problem = rm.deadman_switch_problem(
            "dcp-monitor", "https://hc-ping.com/pingkey/wibble")
        assert problem and "no known stage" in problem


class TestAPingThatDoesNotLandIsNotAPing:
    """The silence that survives even after somebody sets a URL.

    `requests.get` does not raise on 4xx, and this runner used to ignore the
    response entirely. A deleted, renamed or mistyped check answers 404 and the run
    reported success -- so the heartbeat and its absence read identically.
    """

    def test_a_200_that_says_not_found_is_not_a_heartbeat(self, harness):
        """The hole the real-layer test found. healthchecks.io answers 200 with the
        body `OK (not found)` for a UUID that is not a check, so a deleted, renamed or
        mistyped check would have been recorded as a live heartbeat by a status-code
        check alone. See tests/test_run_monitors_deadman_switch_real.py."""
        harness["env"].setenv("HC_PING_URL", GOOD)
        harness["ping_body"] = "OK (not found)"
        assert rm.main() == rm.EXIT_NO_DEADMAN_SWITCH

    def test_a_plain_ok_body_is_a_heartbeat(self, harness):
        """The other side of it: a real ping answers `OK` and must be accepted, or the
        guard fires on every healthy run and gets switched off."""
        harness["env"].setenv("HC_PING_URL", GOOD)
        harness["ping_body"] = "OK"
        assert rm.main() == 0

    def test_a_404_ping_exits_nonzero(self, harness):
        harness["env"].setenv("HC_PING_URL", GOOD)
        harness["ping_status"] = 404
        assert rm.main() == rm.EXIT_NO_DEADMAN_SWITCH

    def test_a_404_ping_alerts(self, harness):
        harness["env"].setenv("HC_PING_URL", GOOD)
        harness["ping_status"] = 404
        rm.main()
        assert _alerts_about_the_switch(harness["sent"])

    def test_a_transport_failure_exits_nonzero(self, harness, monkeypatch):
        harness["env"].setenv("HC_PING_URL", GOOD)

        def _boom(url, **k):
            raise OSError("connection reset")

        monkeypatch.setattr(rm.requests, "get", _boom)
        assert rm.main() == rm.EXIT_NO_DEADMAN_SWITCH

    def test_a_500_from_healthchecks_is_not_a_heartbeat(self, harness):
        harness["env"].setenv("HC_PING_URL", GOOD)
        harness["ping_status"] = 503
        assert rm.main() == rm.EXIT_NO_DEADMAN_SWITCH


class TestAWorkingSwitchIsSilent:
    """A check that fires on everything is the same as one that fires on nothing."""

    def test_a_good_url_exits_zero(self, harness):
        harness["env"].setenv("HC_PING_URL", GOOD)
        assert rm.main() == 0

    def test_a_good_url_is_pinged(self, harness):
        harness["env"].setenv("HC_PING_URL", GOOD)
        rm.main()
        assert harness["pinged"] == [GOOD]

    def test_a_good_url_sends_no_switch_alert(self, harness):
        harness["env"].setenv("HC_PING_URL", GOOD)
        rm.main()
        assert _alerts_about_the_switch(harness["sent"]) == []

    def test_the_opaque_uuid_form_is_accepted(self, harness):
        """healthchecks.io's other ping form carries no stage name. It is accepted,
        and the docstring says plainly that two services sharing one UUID cannot be
        caught from inside a single process -- a guard that overclaims is worse than
        one that does not exist."""
        harness["env"].setenv(
            "HC_PING_URL", "https://hc-ping.com/f618072c-7b6a-4d6f-9b0f-9f0f1a2b3c4d")
        assert rm.main() == 0


class TestTheMonitorsOwnVerdictStillWins:
    """A crash is the more urgent fact and must not be relabelled."""

    def test_a_crash_keeps_exit_1_even_with_no_switch(self, harness):
        harness["child_exit"] = 1
        assert rm.main() == 1

    def test_a_findings_run_with_a_good_switch_still_maps_to_0(self, harness):
        """Exit 2 means "ran fine and found something" -- a healthy outcome that must
        not show red on the dashboard."""
        harness["env"].setenv("HC_PING_URL", GOOD)
        harness["child_exit"] = 2
        assert rm.main() == 0

    def test_a_findings_run_with_no_switch_reports_the_switch(self, harness):
        harness["child_exit"] = 2
        assert rm.main() == rm.EXIT_NO_DEADMAN_SWITCH

    def test_a_failing_run_pings_the_fail_endpoint(self, harness):
        harness["env"].setenv("HC_PING_URL", GOOD)
        harness["child_exit"] = 1
        rm.main()
        assert harness["pinged"] == [GOOD + "/fail"]


class TestEveryStageCanBeConfigured:
    def test_each_monitor_name_has_a_slug_that_would_pass(self):
        """The convention this guard enforces has to be satisfiable for every stage,
        or it is a rule that cannot be followed."""
        for name in rm.MONITORS:
            url = f"https://hc-ping.com/pingkey/{name}"
            assert rm.deadman_switch_problem(name, url) is None, (
                f"{name} cannot be configured under its own name"
            )

    def test_no_two_stages_accept_each_others_slug(self):
        """The whole failure mode is one URL serving several stages."""
        for name in rm.MONITORS:
            for other in rm.MONITORS:
                if other == name:
                    continue
                url = f"https://hc-ping.com/pingkey/{other}"
                assert rm.deadman_switch_problem(name, url) is not None, (
                    f"{name} accepts {other}'s check, so {other}'s alarm can be held "
                    f"green by {name}"
                )


class TestTheSilentReturnIsGone:
    def test_ping_healthcheck_reports_whether_it_landed(self):
        """It returned None on every path, so no caller could tell."""
        src = (ROOT / "scripts" / "run_monitors.py").read_text(encoding="utf-8")
        assert "def ping_healthcheck(url: str, failed: bool = False) -> bool:" in src
        assert "if not url:\n        return\n" not in src, (
            "the silent early return is back"
        )


def _requests_installed_for_a_subprocess() -> bool:
    """Can a FRESH interpreter import requests?

    Not the same question as whether this process can. tests/conftest_mocks.py puts a
    MagicMock in sys.modules, so the suite always "has" requests while the environment
    may not: requirements-test.txt does not install it, and CI runs on exactly that.
    A child process gets the real import path and fails with ModuleNotFoundError.

    This is the assumption the subprocess test below got wrong -- it passed locally,
    where requests happens to be installed, and failed in CI with
    `ModuleNotFoundError: No module named 'requests'` at run_monitors.py:23. Asked
    directly, in a child, rather than inferred from this process.
    """
    return subprocess.run([sys.executable, "-c", "import requests"],
                          capture_output=True).returncode == 0


@pytest.mark.skipif(
    not _requests_installed_for_a_subprocess(),
    reason="requests is not installed in this environment (the suite's copy is a "
           "MagicMock from conftest_mocks), so a child process cannot import "
           "run_monitors. The in-process tests above still cover the exit code; this "
           "one additionally proves it survives as a real process.")
class TestItRunsAsAScript:
    """The tests above import the module. Railway runs it as a process, and an
    exit code that only exists in-process is not an exit code."""

    def test_a_missing_switch_exits_nonzero_from_the_shell(self, tmp_path):
        env = {
            "MONITOR_NAME": "dcp-monitor",
            "PATH": __import__("os").environ.get("PATH", ""),
            "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", ""),
            # A command that succeeds everywhere, so the only non-zero source is
            # the missing switch.
            "PYTHONIOENCODING": "utf-8",
        }
        script = ROOT / "scripts" / "run_monitors.py"
        patched = tmp_path / "probe.py"
        patched.write_text(
            "import sys\n"
            f"sys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
            "import run_monitors as rm\n"
            "rm.MONITORS['dcp-monitor']['cmd'] = [sys.executable, '-c', 'pass']\n"
            "rm.send_telegram = lambda m: None\n"
            "sys.exit(rm.main())\n",
            encoding="utf-8",
        )
        assert script.exists()
        proc = subprocess.run([sys.executable, str(patched)], env=env,
                              capture_output=True, text=True, timeout=120)
        assert proc.returncode == rm.EXIT_NO_DEADMAN_SWITCH, proc.stderr[-2000:]
