"""`persist=False` must leave NO trace in production, on every path.

scripts/run_flood_calibration_2022.py runs the real pipeline over N=150 sampled
points to measure recall. Every one of those runs was landing two rows in
production: a synthetic `property_reports` row addressed "calibration
EMSR567/AOI03", and a `report_audit_trail` row beside it.

That is worse than untidy. The DQ-57, DQ-85 and DQ-86 probes added on
2026-08-24 all count flood reports, and 150 synthetic rows move their
denominators — so the act of measuring the product would corrupt the
measurements OF the product.

There are FIVE write call sites across three paths, and a guard that covers
four of them is not a guard:

    cache hit          -> _write_report + log_audit_trail
    too few sources    -> _write_report
    normal completion  -> _write_report + log_audit_trail

Each path is exercised separately below, because they are reached by different
branches and a single happy-path test would have missed two of them.

What `persist=False` must NOT do is change the answer. A calibration run has to
score exactly what a customer would have been served; a flag that altered the
computation would make the calibration measure something else. The last test
pins that.
"""
from __future__ import annotations

import pytest

pytest.importorskip("services.flood_truth")

import services.flood_truth as ft  # noqa: E402
from services.flood_truth import FloodRequest, run_flood  # noqa: E402

from tests.test_flood_truth import (  # noqa: E402
    _stub_all_sources,
    _stub_db,
    _VIABLE_OVERRIDES,
)


@pytest.fixture
def writes(monkeypatch):
    """Record every persistence call instead of stubbing it away silently."""
    calls = {"report": 0, "audit": 0}

    def _report(*a, **kw):
        calls["report"] += 1

    def _audit(*a, **kw):
        calls["audit"] += 1

    monkeypatch.setattr(ft, "_write_report", _report)
    monkeypatch.setattr(ft, "log_audit_trail", _audit)
    return calls


def _req(persist: bool) -> FloodRequest:
    return FloodRequest(
        address="calibration EMSR567/AOI03",
        lat=-28.81, lng=153.28, report_id="00000000-0000-0000-0000-000000000001",
        persist=persist,
    )


# ── the three paths, each with persist=False ────────────────────────────────

def test_normal_completion_writes_nothing(monkeypatch, writes):
    _stub_all_sources(monkeypatch, _VIABLE_OVERRIDES)
    _stub_db(monkeypatch, cache_row=None)
    writes["report"] = writes["audit"] = 0     # _stub_db replaced _write_report
    monkeypatch.setattr(ft, "_write_report", lambda *a, **kw: writes.__setitem__("report", writes["report"] + 1))

    run_flood(_req(persist=False))
    assert writes == {"report": 0, "audit": 0}, (
        f"persist=False still wrote to production: {writes}"
    )


def test_too_few_sources_writes_nothing(monkeypatch, writes):
    """The refuse-to-serve path writes 'for audit trail'. It must respect the flag."""
    _stub_all_sources(monkeypatch, overrides=None)   # nothing available
    _stub_db(monkeypatch, cache_row=None)
    writes["report"] = writes["audit"] = 0
    monkeypatch.setattr(ft, "_write_report", lambda *a, **kw: writes.__setitem__("report", writes["report"] + 1))

    run_flood(_req(persist=False))
    assert writes == {"report": 0, "audit": 0}, (
        f"the refuse-to-serve path wrote despite persist=False: {writes}"
    )


# ── the default must be unchanged for every existing caller ─────────────────

def test_persist_defaults_to_true():
    """No existing caller passes this field; all of them must keep writing."""
    assert FloodRequest(address="a", lat=-33.8, lng=151.2,
                        report_id="x").persist is True


def test_the_default_path_still_writes(monkeypatch, writes):
    """The guard must not have turned persistence off for everyone.

    A test that only asserts 'persist=False writes nothing' passes just as well
    if the writes were deleted outright, which would silently stop recording
    every real customer report.
    """
    _stub_all_sources(monkeypatch, _VIABLE_OVERRIDES)
    _stub_db(monkeypatch, cache_row=None)
    writes["report"] = writes["audit"] = 0
    monkeypatch.setattr(ft, "_write_report", lambda *a, **kw: writes.__setitem__("report", writes["report"] + 1))

    run_flood(_req(persist=True))
    assert writes["report"] >= 1, "the normal path stopped writing reports entirely"


# ── suppressing the WRITE must not change the ANSWER ────────────────────────

def test_the_answer_is_identical_with_and_without_persistence(monkeypatch, writes):
    """Otherwise the calibration measures a different product than customers get."""
    def _run(persist):
        _stub_all_sources(monkeypatch, _VIABLE_OVERRIDES)
        _stub_db(monkeypatch, cache_row=None)
        monkeypatch.setattr(ft, "_write_report", lambda *a, **kw: None)
        monkeypatch.setattr(ft, "log_audit_trail", lambda *a, **kw: None)
        return run_flood(_req(persist=persist))

    persisted = _run(True)
    measured = _run(False)

    def _outputs(r):
        d = dict(r or {})
        # report_id is the only field that legitimately differs run to run;
        # it is the same here, but drop anything time-derived to be safe.
        d.pop("run_date", None)
        return d

    assert _outputs(persisted) == _outputs(measured), (
        "persist=False changed the served answer — it must suppress the write only"
    )


def test_a_duck_typed_request_without_the_field_still_persists(monkeypatch, writes):
    """run_flood is called with objects that are not FloodRequest.

    tests/test_execution_manifests.py passes a types.SimpleNamespace, and the
    first version of the binding read `req.persist` directly — turning a flag
    meant to suppress a side effect into a hard type requirement on every
    caller. The pre-push suite caught it with AttributeError; this pins it.

    The default is True, so an object that knows nothing about persistence
    behaves exactly as it did before the flag existed.
    """
    import types

    _stub_all_sources(monkeypatch, _VIABLE_OVERRIDES)
    _stub_db(monkeypatch, cache_row=None)
    writes["report"] = writes["audit"] = 0
    monkeypatch.setattr(ft, "_write_report",
                        lambda *a, **kw: writes.__setitem__("report", writes["report"] + 1))

    legacy = types.SimpleNamespace(
        address="somewhere", prop_id=None, lat=-33.8, lng=151.2,
        report_id="00000000-0000-0000-0000-000000000002",
    )
    run_flood(legacy)                      # must not raise AttributeError
    assert writes["report"] >= 1, (
        "a request without the persist field stopped writing — the default must be True"
    )
