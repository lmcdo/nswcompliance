"""DA outcomes fix + wiring tests (the separate-PR item of Slice 3).

Break-it scenarios covered:
  1. The root cause: outFields naming a nonexistent column (DEVELOPMENT_TYPE)
     made ArcGIS error and the empty-dict client response rendered as a silent
     "0 nearby determinations". A failed query must now RAISE.
  2. A refusal RATE built on a silently-zero count is a fabricated statistic —
     a missing 'count' key must raise, never default to 0.
  3. The layer has no zone column; a zone filter must refuse loudly instead of
     silently zeroing the cohort.
  4. Mixed-case LGA names must match the layer's uppercase LGA_NAME values.
  5. Wiring three states: populated / queried-empty / failed must render
     distinctly on the Neighbourhood card.
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

import services.intelligence_brief as ib
from services.intelligence_brief import ConfidenceLevel, DataField, _build_neighbourhood
from services.da_outcome import get_refusal_rate, query_da_outcomes_near

GOLDEN = Path(__file__).parent / "fixtures" / "brief_golden"
NA = ConfidenceLevel.NOT_AVAILABLE
AUTH = ConfidenceLevel.AUTHORITATIVE


def _golden(name: str):
    with open(GOLDEN / f"{name}.json", encoding="utf-8") as fh:
        return json.load(fh)["output"]


# ── 1/2/3. fail-loud guards on the fixed queries ─────────────────────────────

@patch("services.da_outcome.arcgis_get_with_retry", return_value={})
def test_failed_outcomes_query_raises_instead_of_silent_zero(mock_get):
    with pytest.raises(RuntimeError, match="failed"):
        query_da_outcomes_near(151.1, -33.86, radius_m=200)


@patch("services.da_outcome.arcgis_get_with_retry", return_value={"features": []})
def test_genuinely_no_determinations_is_empty_not_error(mock_get):
    assert query_da_outcomes_near(151.1, -33.86, radius_m=200) == []


@patch("services.da_outcome.arcgis_get_with_retry", return_value={})
def test_failed_count_query_raises_never_a_fabricated_rate(mock_get):
    with pytest.raises(RuntimeError, match="count query failed"):
        get_refusal_rate("CANADA BAY", years=8)


def test_zone_filter_refuses_loudly():
    # The layer has no zone column (verified live) — silently zeroing the
    # cohort was the old behaviour.
    with pytest.raises(ValueError, match="zone"):
        get_refusal_rate("CANADA BAY", years=8, zone="R2")


@patch("services.da_outcome.arcgis_get_with_retry")
def test_out_fields_use_the_layers_real_column_names(mock_get):
    mock_get.return_value = {"features": []}
    query_da_outcomes_near(151.1, -33.86)
    params = mock_get.call_args[0][1]
    assert "TYPE_OF_DEVELOPMENT" in params["outFields"]
    assert "DEVELOPMENT_TYPE," not in params["outFields"]  # the nonexistent column


@patch("services.da_outcome.arcgis_get_with_retry")
def test_lga_match_is_case_insensitive(mock_get):
    mock_get.return_value = {"count": 0}
    get_refusal_rate("Canada Bay", years=8)
    where = mock_get.call_args_list[0][0][1]["where"]
    assert "UPPER(LGA_NAME) LIKE '%CANADA BAY%'" in where


# ── real captured shapes round-trip the wiring ───────────────────────────────

def test_real_outcomes_capture_has_recorded_results():
    payload = _golden("da_outcomes")
    assert payload["radius_m"] == 200 and payload["years_back"] == 8
    rows = payload["outcomes"]
    assert len(rows) >= 1  # Concord capture: real determinations near the lot
    assert any(r["outcome"] == "Approved" for r in rows)
    assert all("dev_type" in r for r in rows)


def test_real_refusal_capture_carries_counts_and_period():
    r = _golden("da_refusal_stats")
    assert r["total_determined"] == r["approved"] + r["refused"] + r["deferred_commencement"]
    assert r["period_years"] == 8
    assert 0.0 <= r["refusal_rate"] <= 1.0


# ── wiring three states ──────────────────────────────────────────────────────

def _df(value=None, conf=AUTH, reason=None):
    return DataField(value=value, confidence=conf, source="da_tracking_mapserver", reason=reason)


def test_neighbourhood_outcomes_populated_from_real_capture():
    das = _df(value=[])
    nb = _build_neighbourhood(das, None,
                              da_outcomes_df=_df(value=_golden("da_outcomes")),
                              refusal_df=_df(value=_golden("da_refusal_stats")))
    assert nb.da_outcomes.confidence == AUTH
    assert len(nb.da_outcomes.value["outcomes"]) >= 1
    assert nb.da_refusal_stats.value["refused"] >= 0


def test_neighbourhood_outcomes_failed_is_not_available_with_reason():
    nb = _build_neighbourhood(_df(value=[]), None,
                              da_outcomes_df=_df(value=None, conf=NA, reason="RuntimeError: DA tracking query failed"),
                              refusal_df=_df(value=None, conf=NA, reason="Timeout after 15.0s"))
    assert nb.da_outcomes.confidence == NA
    assert "failed" in nb.da_outcomes.reason
    assert nb.da_refusal_stats.confidence == NA


def test_neighbourhood_outcomes_not_queried_renders_distinctly():
    nb = _build_neighbourhood(_df(value=[]), None)  # renovation path passes nothing
    assert nb.da_outcomes.confidence == NA
    assert "not queried" in nb.da_outcomes.reason


def test_refusal_queried_empty_lga_stays_authoritative_none():
    # get_refusal_rate returns None when the layer holds no determined rows for
    # the LGA — a checked empty, not a failure.
    nb = _build_neighbourhood(_df(value=[]), None,
                              da_outcomes_df=_df(value={"outcomes": [], "radius_m": 200, "years_back": 8}),
                              refusal_df=_df(value=None, conf=AUTH))
    assert nb.da_refusal_stats.confidence == AUTH
    assert nb.da_refusal_stats.value is None
    assert nb.da_outcomes.value["outcomes"] == []
