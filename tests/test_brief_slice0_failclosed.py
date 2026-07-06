"""Slice 0 S1/S2 fail-closed tests — failure can never masquerade as authority.

Break-it scenarios covered (silent wrong results, not crashes):
  1. An errored fetch copied into a DataField at AUTHORITATIVE renders as a
     confident empty answer → the S1 validator must coerce it to NOT_AVAILABLE.
  2. The S1 validator must NOT over-coerce the documented legitimately-empty
     state (value=None, no reason) — that would visibly flip honest empties
     (e.g. "no height control for this zone") into "couldn't retrieve".
  3. A fully-failed brief assembly must contain ZERO authoritative fields with
     a null value anywhere in any emitted section (the plan's S1 test).
  4. A cadastre strata output with type-junk (contract violation) must route
     fail-closed to the renovation brief with a NOT_AVAILABLE strata card —
     never silently classify via the weak lot-area heuristic into a
     DevelopmentBrief with capacity claims.
"""
import json

import pytest

import services.intelligence_brief as ib
from services.intelligence_brief import (
    ConfidenceLevel,
    DataField,
    IntelligenceBriefRequest,
    StrataCoreOutput,
    StrataServiceOutput,
)

NA = ConfidenceLevel.NOT_AVAILABLE
AUTH = ConfidenceLevel.AUTHORITATIVE


# ── S1 validator ─────────────────────────────────────────────────────────────

def test_errored_fetch_at_authoritative_is_coerced_to_not_available():
    # The copy-through mistake: a failed upstream df's (value=None, reason=err)
    # restamped AUTHORITATIVE. Without S1 this renders as a confident blank.
    df = DataField(
        value=None, confidence=AUTH, source="planning_portal",
        reason="TimeoutError: read timed out",
    )
    assert df.confidence == NA
    assert df.reason == "TimeoutError: read timed out"  # failure reason preserved


def test_legitimately_empty_authoritative_is_not_coerced():
    # value=None + reason=None is the documented queried-and-empty state
    # (e.g. a zone with no height control). Coercing it would visibly change
    # honest empty cards — this pin prevents a future "stricter" regression.
    df = DataField(value=None, confidence=AUTH, source="planning_portal")
    assert df.confidence == AUTH


def test_populated_authoritative_with_note_is_not_coerced():
    df = DataField(value="R3", confidence=AUTH, source="planning_portal", reason=None)
    assert df.confidence == AUTH
    assert df.value == "R3"


def test_non_authoritative_errored_fields_unchanged():
    df = DataField(value=None, confidence=ConfidenceLevel.ESTIMATED,
                   source="flood_truth", reason="refused")
    assert df.confidence == ConfidenceLevel.ESTIMATED  # S1 targets AUTHORITATIVE only


# ── all-failed assembly walk (the plan's S1 assembled-brief test) ────────────

_TORRENS = {
    "is_strata": False, "strata_plan": None, "plan_type": None,
    "source": "cadastre", "parent_has_strata": False, "plan_label": "1/DP12345",
}


def _boom(*args, **kwargs):
    raise RuntimeError("source down")


def _run_generator(monkeypatch, strata_fetch):
    """Run the single SSE assembly path with every source failing except strata."""
    for fetch in [
        "_fetch_controls", "_fetch_valuation", "_fetch_contributions",
        "_fetch_overlays", "_fetch_heritage_postgis", "_fetch_mine_subsidence",
        "_fetch_contaminated_land", "_fetch_drinking_water_catchment",
        "_fetch_nearby_das", "_fetch_shadow", "_fetch_dcp_controls",
        "_fetch_sepp_housing", "_fetch_market_context", "_fetch_land_use_lists",
    ]:
        monkeypatch.setattr(ib, fetch, _boom)
    monkeypatch.setattr(ib, "fetch_lot_geometry", _boom)
    monkeypatch.setattr(ib, "_fetch_strata", strata_fetch)
    # ANEF's live fallbacks are called INSIDE the environmental builder (not a
    # pooled fetch) — fail them explicitly so the run is deterministic.
    monkeypatch.setattr(ib, "fetch_anef_zone", _boom)
    import services.portal_constraints as pc
    monkeypatch.setattr(pc, "fetch_anef", _boom)
    # DB-dependent helpers inside the generator (not fetches) — deterministic no-ops.
    monkeypatch.setattr(ib, "_sepp_eligibility_results", lambda *a, **k: None)
    monkeypatch.setattr(ib, "detect_former_council", lambda addr, epi: None)
    monkeypatch.setattr(ib, "_validate_former_council_postgis",
                        lambda slug, lat, lng, addr: (slug, None))
    monkeypatch.setattr(ib, "_eligibility_excluded_forms", lambda lat, lng: set())
    monkeypatch.setattr(ib, "enrich_gaps_with_verify_url", lambda gaps, slug: gaps)

    req = IntelligenceBriefRequest(address="14 Stanley Street, Concord")
    events = []
    for chunk in ib._generate_brief_sse(req, 1456609, -33.86382, 151.10586, None):
        lines = [l for l in chunk.strip().splitlines() if l]
        name = lines[0].removeprefix("event: ")
        data = json.loads(lines[1].removeprefix("data: "))
        events.append((name, data))
    return events


def _walk_datafields(node, found):
    """Collect every DataField-shaped dict in an emitted payload."""
    if isinstance(node, dict):
        if {"value", "confidence", "source"} <= set(node.keys()):
            found.append(node)
        for v in node.values():
            _walk_datafields(v, found)
    elif isinstance(node, list):
        for item in node:
            _walk_datafields(item, found)
    return found


def _assert_no_authoritative_null(events):
    fields = []
    for _, data in events:
        _walk_datafields(data, fields)
    assert len(fields) > 10, "walk found too few DataFields — harness broken?"
    offenders = [
        f for f in fields
        if f["confidence"] == "authoritative" and f["value"] is None
    ]
    assert offenders == [], f"AUTHORITATIVE fields with null value leaked: {offenders}"


def test_all_sources_failed_brief_has_no_authoritative_null_field(monkeypatch):
    events = _run_generator(monkeypatch, _boom)
    names = [n for n, _ in events]
    assert "error" not in names, f"assembly crashed instead of degrading: {events[-1]}"
    assert names.count("section") >= 4
    assert names[-1] == "complete"
    _assert_no_authoritative_null(events)
    # Unknown strata routes fail-closed to the renovation template.
    strata_events = [d for n, d in events if n == "section" and d.get("section") == "strata"]
    assert strata_events[0]["brief_type"] == "renovation"
    assert strata_events[0]["data"]["confidence"] == "not_available"


def test_development_route_with_all_other_sources_failed_no_authoritative_null(monkeypatch):
    # Torrens strata succeeds → development template → dcp/sepp/neighbourhood
    # sections are also emitted and must obey the same invariant.
    events = _run_generator(monkeypatch, lambda *a, **k: dict(_TORRENS))
    names = [n for n, _ in events]
    assert "error" not in names
    sections = {d.get("section") for n, d in events if n == "section"}
    assert {"dcp_controls", "neighbourhood"} <= sections
    _assert_no_authoritative_null(events)
    # Failed DA lookup must be NOT_AVAILABLE, never authoritative 0 (the #582 class).
    nb = next(d for n, d in events if n == "section" and d.get("section") == "neighbourhood")
    assert nb["data"]["nearby_das"]["confidence"] == "not_available"
    assert nb["data"]["nearby_das"]["value"] is None


# ── S2 strata contract violation routes fail-closed ─────────────────────────

def test_strata_type_junk_routes_to_renovation_not_silent_development(monkeypatch):
    """lot_total='many units' would have skipped the count check and fallen to
    the weak lot-area heuristic (silently DEVELOPMENT on a big apartment lot).
    The contract violation must instead take the fail-closed AMBIGUOUS route."""
    junk = {**_TORRENS, "is_strata": True, "strata_plan": "SP91614",
            "lot_total": "many units"}
    events = _run_generator(monkeypatch, lambda *a, **k: junk)
    strata_ev = next(d for n, d in events if n == "section" and d.get("section") == "strata")
    assert strata_ev["brief_type"] == "renovation"
    assert strata_ev["data"]["confidence"] == "not_available"
    assert strata_ev["data"]["value"]["strata_type"] == "ambiguous"


def test_strata_renamed_key_is_visible_drift_not_clean():
    """A renamed service key parses fine (defaults) — validation alone cannot
    catch it. The drift check MUST flag it so the S3 tripwire/test fails."""
    from brief_contract_drift import check_drift

    renamed = {k: v for k, v in _TORRENS.items() if k != "is_strata"}
    renamed["strata"] = False
    result = check_drift(StrataCoreOutput, renamed)
    assert result["drift"] is True
    assert "is_strata" in result["missing"]
    # and the real (on-contract) shape is clean
    assert check_drift(StrataCoreOutput, _TORRENS)["drift"] is False


def test_strata_contract_accepts_strata_hub_enrichment():
    out = StrataServiceOutput.model_validate({**_TORRENS, "is_strata": True,
                                              "lot_total": 77, "dwelling_type": "apartment"})
    assert out.lot_total == 77
    with pytest.raises(Exception):
        StrataServiceOutput.model_validate({**_TORRENS, "lot_total": "many units"})
