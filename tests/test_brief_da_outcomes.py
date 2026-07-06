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

import services.da_outcome as da_outcome_mod
import services.intelligence_brief as ib
from services.intelligence_brief import ConfidenceLevel, DataField, _build_neighbourhood
from services.da_outcome import get_refusal_rate, query_da_outcomes_near

GOLDEN = Path(__file__).parent / "fixtures" / "brief_golden"
NA = ConfidenceLevel.NOT_AVAILABLE
AUTH = ConfidenceLevel.AUTHORITATIVE

# Valid currency-probe response — the first ArcGIS call get_refusal_rate makes.
_CURRENCY_RESPONSE = {
    "features": [{"attributes": {"LODGEMENT_DATE": "20230429151817.89"}}],
}


@pytest.fixture(autouse=True)
def _clear_currency_cache():
    da_outcome_mod._currency_cache.clear()
    yield
    da_outcome_mod._currency_cache.clear()


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


@patch("services.da_outcome.arcgis_get_with_retry")
def test_failed_count_query_raises_never_a_fabricated_rate(mock_get):
    mock_get.side_effect = [_CURRENCY_RESPONSE, {}]
    with pytest.raises(RuntimeError, match="count query failed"):
        get_refusal_rate("CANADA BAY", years=8)


@patch("services.da_outcome.arcgis_get_with_retry", return_value={})
def test_failed_currency_probe_fails_the_stats_closed(mock_get):
    # Counts without a stated data window would render as if current — the
    # frozen-extract defect this PR fixes.
    with pytest.raises(RuntimeError, match="currency query failed"):
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
    mock_get.side_effect = [_CURRENCY_RESPONSE, {"count": 0}, {"count": 0}, {"count": 0}]
    get_refusal_rate("Canada Bay", years=8)
    # call 0 is the currency probe; call 1 is the first outcome count
    where = mock_get.call_args_list[1][0][1]["where"]
    assert "UPPER(LGA_NAME) LIKE '%CANADA BAY%'" in where


# ── real captured shapes round-trip the wiring ───────────────────────────────

def test_real_outcomes_capture_has_recorded_results():
    payload = _golden("da_outcomes")
    assert payload["radius_m"] == 200 and payload["years_back"] == 8
    rows = payload["outcomes"]
    assert len(rows) >= 1  # Concord capture: real determinations near the lot
    assert any(r["outcome"] == "Approved" for r in rows)
    assert all("dev_type" in r for r in rows)


def test_real_outcomes_capture_carries_the_data_window():
    # The tracking layer is a frozen extract (newest lodgement 2023-04-29,
    # verified live 2026-07-06); the payload must state the window so the
    # renderer never implies currency.
    payload = _golden("da_outcomes")
    assert payload["data_currency"] == "2023-04-29"
    assert payload["window_start"] <= payload["window_end"]
    assert payload["window_end"] <= payload["data_currency"]


def test_real_refusal_capture_carries_counts_and_period():
    r = _golden("da_refusal_stats")
    assert r["total_determined"] == r["approved"] + r["refused"] + r["deferred_commencement"]
    assert r["period_years"] == 8
    assert 0.0 <= r["refusal_rate"] <= 1.0
    assert r["data_currency"] == "2023-04-29"
    assert r["window_start"] < r["data_currency"]


# ── _fetch_da_outcomes derives the window from the data, not years_back ─────

def _da_row(pan: str, lodgement: str):
    from services.da_outcome import DAOutcome
    return DAOutcome(
        planning_portal_number=pan, status="Determined", outcome="Approved",
        address="1 Test St", suburb="TESTVILLE", lodgement_date=lodgement,
    )


@patch("services.da_outcome.get_data_currency", return_value="2023-04-29")
@patch("services.da_outcome.query_da_outcomes_near")
def test_fetch_da_outcomes_window_is_data_derived(mock_query, mock_currency):
    mock_query.return_value = [
        _da_row("PAN-1", "2021-03-15"), _da_row("PAN-2", "2019-08-02"),
        _da_row("PAN-3", "2022-11-30"),
    ]
    payload = ib._fetch_da_outcomes(151.1, -33.86)
    assert payload["window_start"] == "2019-08-02"
    assert payload["window_end"] == "2022-11-30"
    assert payload["data_currency"] == "2023-04-29"
    # existing keys stay — additive change only
    assert payload["radius_m"] == ib.CONFIG.da_outcomes_radius_m
    assert payload["years_back"] == ib.CONFIG.da_outcomes_years_back


@patch("services.da_outcome.get_data_currency", return_value="2023-04-29")
@patch("services.da_outcome.query_da_outcomes_near", return_value=[])
def test_fetch_da_outcomes_empty_still_states_layer_currency(mock_query, mock_currency):
    payload = ib._fetch_da_outcomes(151.1, -33.86)
    assert payload["outcomes"] == []
    assert payload["window_start"] is None and payload["window_end"] is None
    assert payload["data_currency"] == "2023-04-29"


@patch("services.da_outcome.get_data_currency",
       side_effect=RuntimeError("DA tracking currency query failed"))
@patch("services.da_outcome.query_da_outcomes_near", return_value=[])
def test_fetch_da_outcomes_fails_closed_without_a_window(mock_query, mock_currency):
    # A windowless outcome list would render as if current — fail the field.
    with pytest.raises(RuntimeError, match="currency query failed"):
        ib._fetch_da_outcomes(151.1, -33.86)


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
