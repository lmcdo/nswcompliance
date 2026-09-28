"""The real-layer half: does healthchecks.io actually REFUSE a ping we made up?

Everything in tests/test_silence_is_an_alarm.py patches `requests.get`. That proves
`ping_healthcheck` reacts correctly to a 404 it was handed — it cannot prove that
healthchecks.io answers 404 in the first place. The whole fix rests on that
assumption, because the bug was:

    requests.get(target, timeout=10)     # response discarded

`requests` does not raise on 4xx. So a deleted, renamed or mistyped check answered
and the run reported a heartbeat. Measured 2026-09-28: six Railway services were
pinging the literal string `https://hc-ping.com/placeholder-satellite`, which is not
a check, and all six looked healthy.

If healthchecks.io instead answered 200 to an unknown id, the entire guard would be
decorative and the mocked tests would still pass. That is the assumption this file
tests, against the real service. `memory/feedback-a-check-must-call-the-machine-it-checks.md`.

WHY THIS CANNOT TOUCH PRODUCTION MONITORING
-------------------------------------------
It pings a randomly generated UUID that belongs to no check. That is deliberate and
it is the only shape of real-layer test that is safe here: a test that pinged a REAL
check would register a heartbeat, which would make a dead stage look alive and
satisfy the dead-man's switch from CI. That is exactly the failure recorded in
`memory/feedback-tests-reached-production-via-post-publish-subprocess.md` — a test
reaching production — and it would be worse than having no test, because it would
defeat the mechanism this branch exists to build.

So: the negative path is tested against the real service, and the positive path
stays mocked. There is no safe real-layer test of a SUCCESSFUL ping.

Deselected by default (`pytest.ini` addopts excludes `integration`). Run with:

    pytest -m integration tests/test_run_monitors_deadman_switch_real.py
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_monitors as rm  # noqa: E402

pytestmark = pytest.mark.integration

#: An id that belongs to no check, generated per run so a cached answer cannot
#: make this pass.
UNKNOWN_CHECK = f"https://hc-ping.com/{uuid.uuid4()}"


def _why_it_cannot_run() -> str | None:
    """The reason this cannot test the real layer, or None when it can.

    THREE states, not two, and the middle one is the trap: `requests` STUBBED is not
    the same as the network being down. tests/conftest_mocks.py replaces requests with
    a MagicMock by default, and a MagicMock answers every call happily -- so a naive
    reachability probe returns True and the test then asserts against a mock while
    claiming to have tested the real service. That is a test that proves nothing while
    reporting success, which is the whole shape this branch exists to remove.
    """
    import requests
    from unittest.mock import MagicMock
    if isinstance(requests, MagicMock) or isinstance(getattr(requests, "get", None), MagicMock):
        return ("requests is STUBBED by tests/conftest_mocks.py, so nothing here would "
                "touch the real service. Re-run with PYTEST_REAL_HTTP=1.")
    try:
        requests.get("https://hc-ping.com/", timeout=10)
    except Exception as exc:  # noqa: BLE001 - offline, DNS, proxy: same answer here
        return f"hc-ping.com is not reachable from here ({type(exc).__name__}), so the "
    return None


@pytest.fixture(scope="module", autouse=True)
def _needs_real_network():
    reason = _why_it_cannot_run()
    if reason:
        pytest.skip(reason + " real-layer assumption is UNTESTED. This is a SKIP, "
                             "not a pass.")


class TestHealthchecksRefusesAPingWeInvented:
    def test_an_unknown_check_is_reported_as_not_landed(self):
        """The load-bearing assumption. If this ever returns True, every mocked test
        in test_silence_is_an_alarm.py is still green while the guard does nothing."""
        assert rm.ping_healthcheck(UNKNOWN_CHECK) is False, (
            "healthchecks.io ACCEPTED a ping for a check that does not exist. The "
            "status-code check in ping_healthcheck cannot distinguish a real heartbeat "
            "from a mistyped URL, and the dead-man's switch is decorative."
        )

    def test_the_fail_endpoint_is_also_refused(self):
        """run_monitors pings `<url>/fail` when the monitor failed. That path has to
        reject an unknown check too, or a failing stage reports a heartbeat."""
        assert rm.ping_healthcheck(UNKNOWN_CHECK, failed=True) is False

    def test_the_host_is_the_one_the_guard_accepts(self):
        """Ties the two halves together: the URL proven to be refused here is a URL
        deadman_switch_problem would have allowed through as well-formed, so the
        status check is genuinely the last line of defence and not dead code behind
        an earlier rejection."""
        assert rm.deadman_switch_problem("dcp-monitor", UNKNOWN_CHECK) is None

    def test_a_placeholder_never_reaches_the_network(self):
        """The measured production value. It must be rejected by shape BEFORE any
        request is made, so it is never pinged even once."""
        problem = rm.deadman_switch_problem(
            "dcp-monitor", "https://hc-ping.com/placeholder-satellite")
        assert problem and "placeholder" in problem
