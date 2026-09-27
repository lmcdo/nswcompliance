"""The brief-overlay endpoint takes no credential and calls a paid model.

These tests exist because the production flag was about to be turned on without
a cap. They FORCE the limit to fire rather than asserting it exists — a guard
nobody has watched reject something is not a guard
([[feedback-detect-a-guard-by-forcing-its-failure]]).

Mutation-resistant by design: each of these must fail if the limiter is deleted,
if only the per-client limit is kept, if only the global one is kept, or if the
flag check is moved after the limit.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services import brief_overlay_api as api  # noqa: E402


class _Req:
    """Enough of starlette's Request for _rate_limit_check: headers + client."""

    class _Client:
        def __init__(self, host):
            self.host = host

    def __init__(self, ip="1.2.3.4", forwarded=None):
        self.headers = {"x-forwarded-for": forwarded} if forwarded else {}
        self.client = self._Client(ip)


@pytest.fixture(autouse=True)
def clean():
    api._reset_rate_limit_for_tests()
    yield
    api._reset_rate_limit_for_tests()


class TestItActuallyRejects:
    def test_one_client_is_cut_off_at_the_limit(self):
        r = _Req("10.0.0.1")
        allowed = sum(1 for _ in range(api._PER_CLIENT_MAX)
                      if api._rate_limit_check(r) is None)
        assert allowed == api._PER_CLIENT_MAX, "the limit refused a call inside quota"
        assert api._rate_limit_check(r) is not None, (
            "the %dth call was allowed — the per-client limit does not fire"
            % (api._PER_CLIENT_MAX + 1))

    def test_a_rejected_call_says_when_to_come_back(self):
        r = _Req("10.0.0.2")
        for _ in range(api._PER_CLIENT_MAX):
            api._rate_limit_check(r)
        wait = api._rate_limit_check(r)
        assert isinstance(wait, int) and 1 <= wait <= int(api._RATE_WINDOW_S) + 1

    def test_a_second_client_is_not_punished_for_the_first(self):
        a, b = _Req("10.0.0.3"), _Req("10.0.0.4")
        for _ in range(api._PER_CLIENT_MAX):
            api._rate_limit_check(a)
        assert api._rate_limit_check(a) is not None
        assert api._rate_limit_check(b) is None, "one noisy caller blocked everyone"


class TestTheGlobalCapIsTheOneThatGuardsTheBill:
    def test_many_clients_still_hit_a_ceiling(self):
        """A per-IP limit alone is no protection against a spread of addresses,
        which is the shape an abusive caller actually has. This is the test that
        fails if the global cap is removed."""
        allowed = 0
        for i in range(api._GLOBAL_MAX + 50):
            if api._rate_limit_check(_Req("10.1.%d.%d" % (i // 256, i % 256))) is None:
                allowed += 1
        assert allowed == api._GLOBAL_MAX, (
            "%d calls got through a global cap of %d — spend is uncapped"
            % (allowed, api._GLOBAL_MAX))

    def test_the_global_cap_is_the_smaller_ceiling(self):
        assert api._GLOBAL_MAX < api._PER_CLIENT_MAX * api._MAX_TRACKED_CLIENTS


class TestKeying:
    def test_forwarded_for_separates_callers_behind_a_proxy(self):
        one = _Req("172.16.0.1", forwarded="203.0.113.7")
        two = _Req("172.16.0.1", forwarded="203.0.113.8")
        assert api._client_key(one) != api._client_key(two), (
            "behind a proxy every caller would share one bucket")

    def test_first_hop_wins_in_a_forwarded_chain(self):
        r = _Req("172.16.0.1", forwarded="203.0.113.7, 10.0.0.9, 10.0.0.10")
        assert api._client_key(r) == "203.0.113.7"

    def test_no_client_does_not_raise(self):
        r = _Req()
        r.client = None
        assert api._client_key(r) == "unknown"


class TestItCannotEatMemory:
    def test_the_client_map_is_bounded(self):
        """⚠ The global cap must be held OUT of the way for this one.

        The first version of this test looped over _MAX_TRACKED_CLIENTS + 200
        distinct addresses and asserted the map stayed bounded — and it passed
        with the eviction DELETED, because the global cap refuses after
        _GLOBAL_MAX calls and no further entries are ever created. The
        assertion was true for a reason that had nothing to do with what it
        claimed to test. Caught by mutation, not by reading it.

        So the global counter is cleared each iteration: this test is about the
        map's own bound, and the other tests own the global cap.
        """
        for i in range(api._MAX_TRACKED_CLIENTS + 200):
            api._rate_limit_check(_Req("10.2.%d.%d" % (i // 256, i % 256)))
            with api._rate_lock:
                del api._global_hits[:]
        assert len(api._client_hits) <= api._MAX_TRACKED_CLIENTS, (
            "the per-client map grows without limit — a spray of addresses is "
            "then a memory leak as well as a bill")


class TestWiring:
    def test_the_handler_takes_a_request_and_checks_the_limit(self):
        import inspect
        src = inspect.getsource(api.brief_overlay)
        assert "_rate_limit_check" in src, "the handler does not call the limiter"
        assert "429" in src, "a refused call must answer 429, not 500"
        assert "Retry-After" in src

    def test_the_flag_is_checked_before_the_limit(self):
        """When the flag is off nothing is spent, so the honest answer is
        'disabled'. Answering 429 there would misstate why there is no overlay."""
        import inspect
        src = inspect.getsource(api.brief_overlay)
        assert src.index("overlay_enabled") < src.index("_rate_limit_check")

    def test_the_reset_helper_is_not_used_by_the_request_path(self):
        import inspect
        assert "_reset_rate_limit_for_tests" not in inspect.getsource(api.brief_overlay)
