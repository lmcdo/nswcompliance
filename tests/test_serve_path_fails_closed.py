"""Every DB fetcher on the serve path must refuse to answer when it cannot look.

WHY THIS IS ONE TEST AND NOT SIXTEEN
------------------------------------
The four-category compliance testing framework
(memory/reference-domain-compliance-testing-framework.md, designed 2026-06-01)
puts "three-state" first: a check must distinguish EXISTS / CONFIRMED-CLEAR /
COULD-NOT-LOOK, and must never render the third as the second. Written as one
test per fetcher, that is a convention -- nobody is forced to write one for the
fetcher they add next month, and the gap is invisible until it ships.

So this discovers the fetchers by REFLECTION over the module. A new `fetch_*`
on the serve path is covered the day it is written, without anyone remembering
this file exists. That is the whole point: the rule cannot be followed or not
followed, because nothing asks.

THE PROPERTY
------------
Given a connection that fails, a fetcher may raise, or may return None. It may
NOT return normally with an empty or negative payload, because the caller then
cannot tell "we looked and found nothing" from "we could not look".

That distinction is not academic here. services/conveyancing.py wraps each
fetch in try/except and sets _failed[name] = False on the success path. A
fetcher that swallows its own exception and returns a default therefore returns
NORMALLY, the caller's except never fires, and the system records a SUCCESSFUL
check that found nothing. Database down renders as "not heritage listed".

WHY A RATCHET AND NOT A HARD ZERO
---------------------------------
Four of the six fetchers fail this today. A guard that breaks the build on
pre-existing violations gets switched off within a week -- scripts/dq_check.py
says exactly this about its own caps ("A hard zero would fail on 44 pre-existing
rows and be deleted within a week"). So the known set is recorded and may only
SHRINK. A newly added fetcher that fails open is a build failure on day one,
which is the case worth stopping.
"""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))

BASELINE = _ROOT / ".claude" / "fail_closed_baseline.json"


class DeadConnection:
    """A connection that has died mid-request.

    Not a MagicMock: a MagicMock's .cursor() returns another MagicMock, every
    query "succeeds", and the fetcher takes its happy path -- so the test would
    pass while measuring nothing. This is the failure mode
    memory/feedback-qa-guardrails-honest-assessment.md records (844 tests, 13%
    mutation kill rate). It must actually break.
    """

    def cursor(self, *a, **k):
        raise RuntimeError("connection lost mid-query")

    def rollback(self):
        pass

    def close(self):
        pass


def _dummy_for(param: inspect.Parameter):
    """A plausible argument, from the annotation. Values are never used -- the
    connection dies before any of them reaches SQL."""
    ann = str(param.annotation)
    if "float" in ann:
        return -33.8688
    if "bool" in ann:
        return False
    if "int" in ann and "Optional" not in ann:
        return 1
    return "inner_west"


def serve_path_fetchers():
    """Every fetch_* defined IN conveyancing_db, found by reflection.

    Filtered on __module__ so imported helpers are not swept in, and so the set
    grows automatically with the module rather than with this file.
    """
    import conveyancing_db

    out = []
    for name, fn in inspect.getmembers(conveyancing_db, inspect.isfunction):
        if not name.startswith("fetch_"):
            continue
        if fn.__module__ != conveyancing_db.__name__:
            continue
        out.append((name, fn))
    return sorted(out)


def call_with_dead_connection(fn):
    """Return 'refused' if the fetcher declined to answer, else its payload."""
    sig = inspect.signature(fn)
    args = [DeadConnection()]
    for _, param in list(sig.parameters.items())[1:]:
        if param.default is inspect.Parameter.empty:
            args.append(_dummy_for(param))
    try:
        result = fn(*args)
    except Exception:
        return "refused"  # raising is a legitimate refusal; the caller catches
    if result is None:
        return "refused"  # so is an explicit None
    return result


def fetchers_that_answer_anyway() -> list[str]:
    """The fetchers that return a usable-looking value when they could not look."""
    return [name for name, fn in serve_path_fetchers()
            if call_with_dead_connection(fn) != "refused"]


def _baseline() -> set[str]:
    if not BASELINE.exists():
        return set()
    return set(json.loads(BASELINE.read_text(encoding="utf-8"))["fail_open"])


def test_no_new_fetcher_answers_when_it_cannot_look():
    """The ratchet. A NEW fail-open fetcher fails the build on day one."""
    actual = set(fetchers_that_answer_anyway())
    new = sorted(actual - _baseline())
    assert not new, (
        f"{new} return a value when the database is unreachable, so a caller "
        f"cannot tell 'we looked and found nothing' from 'we could not look'. "
        f"Raise, or return None. Do not add to "
        f"{BASELINE.name} -- it may only shrink."
    )


def test_baseline_may_only_shrink():
    """A fetcher that has been repaired must be REMOVED from the baseline, not
    left as standing amnesty. Same rule as check_test_quarantine.py: a listed
    item that starts passing fails the check until it is released."""
    fixed = sorted(_baseline() - set(fetchers_that_answer_anyway()))
    assert not fixed, (
        f"{fixed} now refuse correctly but are still listed in "
        f"{BASELINE.name}. Remove them; the list may only shrink."
    )


def test_the_probe_can_actually_detect_a_failure():
    """The control case.

    Without this, a bug in DeadConnection or in the reflection would empty the
    result set and every assertion above would pass over a dead guard -- green
    on zero fetchers examined. So: the module must expose fetchers at all, and a
    deliberately fail-open function must be caught by the same machinery.
    """
    assert serve_path_fetchers(), "no fetchers discovered - the reflection broke"

    def fetch_pretend(conn, lga: str):
        try:
            conn.cursor()
        except Exception:
            return []  # the exact defect: swallow, answer anyway
        return ["unreachable"]

    assert call_with_dead_connection(fetch_pretend) == [], (
        "the probe failed to notice a fetcher that answers with [] on a dead "
        "connection, so a green run above would prove nothing"
    )


def test_the_real_caller_records_every_check_as_failed():
    """The property that actually matters, tested where it actually matters.

    Everything above asks whether a fetcher REFUSES. That is necessary and not
    sufficient: services/conveyancing.py sets _failed[name] = False after a
    normal return, so a fetcher that refuses by returning None still leaves the
    caller believing the check completed. fetch_dcp_setbacks did exactly that
    -- honest fetcher, misinformed caller -- and no test above could see it,
    because it looks at the fetchers in isolation.

    So this drives the real _fetch_pdf_db_data with a database that fails on
    every query, using the REAL fetchers, and requires all four flags to stay
    True. It is the end-to-end statement of "a dead database must not produce a
    completed check".
    """
    # Same import route as tests/test_typed_absence_fixes.py: services/ on the
    # path and imported bare. `import services.conveyancing` fails on its
    # sibling imports (lga_lookup), which resolve relative to services/.
    sys.path.insert(0, str(_ROOT / "services"))
    sys.path.insert(0, str(_ROOT))

    import psycopg2

    import conveyancing

    class _DeadCursor:
        def execute(self, *a, **k):
            raise RuntimeError("connection lost mid-query")

        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class _Conn:
        autocommit = False

        def cursor(self, *a, **k):
            return _DeadCursor()

        def rollback(self):
            pass

        def close(self):
            pass

    real_connect = psycopg2.connect
    psycopg2.connect = lambda *a, **k: _Conn()
    try:
        _das, _lep, _dcp, _heritage, failed = conveyancing._fetch_pdf_db_data(
            "postgresql://unused", -33.8, 151.2, None,
            {"key_sites_clause": "cl 6.15", "zone_epi": "X LEP 2013", "zone": "R2"},
            "inner_west",
        )
    finally:
        psycopg2.connect = real_connect

    still_believed_ok = sorted(k for k, v in failed.items() if not v)
    assert not still_believed_ok, (
        f"every query failed, but {still_believed_ok} are recorded as having "
        f"completed. Those checks will render as a clean absence rather than "
        f"'could not be determined'."
    )


@pytest.mark.parametrize("name", [n for n, _ in serve_path_fetchers()])
def test_each_fetcher_reported(name):
    """Visibility, not enforcement: prints the current verdict per fetcher so a
    reader sees which are refusing and which are on the baseline."""
    refuses = call_with_dead_connection(dict(serve_path_fetchers())[name]) == "refused"
    if not refuses:
        assert name in _baseline(), f"{name} is fail-open and unlisted"
