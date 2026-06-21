"""Consolidation P1 — live SEPP eligibility gates wired into the capacity ceiling.

The dual-occupancy prohibition layer (ePlanning 452) was fetched elsewhere but never
consumed by the capacity engine, so the brief could show a dual-occ ceiling on a lot where
dual occupancy is prohibited. These tests pin that the gate now removes the prohibited form
from the ceiling, that it is fail-safe (a query failure never over-restricts), and that the
existing ceiling logic is unchanged when no form is excluded.
"""
import pytest

import services.intelligence_brief as ib
from services.intelligence_brief import (
    _ceiling_within_tier,
    _realistic_forms,
    _eligibility_excluded_forms,
)


# --- _ceiling_within_tier with exclusions (pure) ----------------------------

def test_r2_dual_occ_excluded_falls_to_dwelling_house():
    permitted = {"dual_occupancy", "dwelling_house"}
    assert _ceiling_within_tier("R2", permitted) == "dual_occupancy"  # baseline
    assert _ceiling_within_tier("R2", permitted, {"dual_occupancy"}) == "dwelling_house"


def test_excluding_a_form_not_at_the_ceiling_is_a_noop():
    # R3 ceiling is multi_dwelling; excluding dual_occ shouldn't change it.
    permitted = {"multi_dwelling_housing", "dual_occupancy", "dwelling_house"}
    assert _ceiling_within_tier("R3", permitted, {"dual_occupancy"}) == "multi_dwelling_housing"


def test_excluding_the_ceiling_form_steps_down_to_next_permitted():
    permitted = {"multi_dwelling_housing", "attached_dwelling", "dwelling_house"}
    assert _ceiling_within_tier("R3", permitted, {"multi_dwelling_housing"}) == "attached_dwelling"


def test_none_excluded_is_unchanged_behaviour():
    permitted = {"residential_flat_building", "dwelling_house"}
    assert _ceiling_within_tier("R4", permitted) == "residential_flat_building"
    assert _ceiling_within_tier("R4", permitted, None) == "residential_flat_building"


def test_realistic_forms_threads_exclusions(monkeypatch):
    monkeypatch.setattr(ib, "_permitted_engine_forms",
                        lambda z, l: {"dual_occupancy", "dwelling_house"})
    assert _realistic_forms("R2", "Penrith") == ("dwelling_house", "dual_occupancy")
    assert _realistic_forms("R2", "Penrith", {"dual_occupancy"}) == ("dwelling_house", "dwelling_house")


def test_realistic_forms_lmr_source_flag(monkeypatch):
    # Base zone tier here tops out at dwelling_house; an LMR uplift to multi-dwelling
    # strictly raises the ceiling -> ceiling_from_lmr True.
    monkeypatch.setattr(ib, "_permitted_engine_forms", lambda z, l: {"dwelling_house"})
    assert _realistic_forms("R3", "X", uplift_form="multi_dwelling_housing", return_source=True) == \
        ("dwelling_house", "multi_dwelling_housing", True)
    # No uplift -> ceiling stays base, flag False.
    assert _realistic_forms("R3", "X", return_source=True) == \
        ("dwelling_house", "dwelling_house", False)
    # Uplift equal to the base form does NOT count as LMR-raised (base already there).
    monkeypatch.setattr(ib, "_ceiling_within_tier", lambda z, p, e=None: "multi_dwelling_housing")
    assert _realistic_forms("R3", "X", uplift_form="multi_dwelling_housing", return_source=True)[2] is False


# --- _eligibility_excluded_forms (live gate, mocked) ------------------------

def test_dual_occ_prohibited_excludes_the_form(monkeypatch):
    monkeypatch.setattr(ib, "_fetch_dual_occ_prohibition", lambda lat, lng: {"prohibited": True, "epi_name": "X LEP"})
    assert _eligibility_excluded_forms(-33.8, 151.1) == {"dual_occupancy"}


def test_dual_occ_not_prohibited_excludes_nothing(monkeypatch):
    monkeypatch.setattr(ib, "_fetch_dual_occ_prohibition", lambda lat, lng: {"prohibited": False})
    assert _eligibility_excluded_forms(-33.8, 151.1) == set()


def test_gate_query_returns_none_is_failsafe(monkeypatch):
    monkeypatch.setattr(ib, "_fetch_dual_occ_prohibition", lambda lat, lng: None)
    assert _eligibility_excluded_forms(-33.8, 151.1) == set()


def test_gate_query_raises_is_failsafe(monkeypatch):
    def _boom(lat, lng):
        raise RuntimeError("ArcGIS down")
    monkeypatch.setattr(ib, "_fetch_dual_occ_prohibition", _boom)
    assert _eligibility_excluded_forms(-33.8, 151.1) == set()  # never over-restrict on failure


def test_missing_coordinates_skip_the_gate():
    assert _eligibility_excluded_forms(None, 151.1) == set()
    assert _eligibility_excluded_forms(-33.8, None) == set()


# --- LMR citation gate (no clause -> no claim) ------------------------------

from types import SimpleNamespace  # noqa: E402

from services.intelligence_brief import _apply_lmr_attribution, _lmr_uplift_form  # noqa: E402


def test_apply_lmr_attribution_sets_citation_when_present():
    r = SimpleNamespace(ceiling_from_lmr=False, lmr_source_clause=None,
                        lmr_source_document=None, lmr_legislation_url=None, lmr_effective_date=None)
    _apply_lmr_attribution(r, True, {
        "source_clause": "172(2)(a)", "source_document": "SEPP (Housing) 2021 - LMR Amendment",
        "legislation_url": "https://legislation.nsw.gov.au/x", "effective_date": "2025-02-28",
    })
    assert r.ceiling_from_lmr is True
    assert r.lmr_source_clause == "172(2)(a)"
    assert r.lmr_legislation_url.startswith("https://")


def test_apply_lmr_attribution_no_clause_makes_no_claim():
    # LMR raised the ceiling geometrically but there's no citation -> NO claim.
    r = SimpleNamespace(ceiling_from_lmr=False, lmr_source_clause=None,
                        lmr_source_document=None, lmr_legislation_url=None, lmr_effective_date=None)
    _apply_lmr_attribution(r, True, None)
    assert r.ceiling_from_lmr is False
    assert r.lmr_source_clause is None
    _apply_lmr_attribution(r, True, {"source_clause": None})
    assert r.ceiling_from_lmr is False


def test_apply_lmr_attribution_flag_false_no_claim():
    r = SimpleNamespace(ceiling_from_lmr=True, lmr_source_clause=None,
                        lmr_source_document=None, lmr_legislation_url=None, lmr_effective_date=None)
    _apply_lmr_attribution(r, False, {"source_clause": "172(2)(a)"})
    assert r.ceiling_from_lmr is False


def test_lmr_uplift_form_returns_citation(monkeypatch):
    elig = SimpleNamespace(
        development_type="multi_dwelling", eligible=True, source_clause="172(2)(a)",
        source_document="SEPP (Housing) 2021 - LMR Amendment",
        legislation_url="https://legislation.nsw.gov.au/x", effective_date="2025-02-28")
    monkeypatch.setattr(ib, "_SEPP_FORM_TO_ENGINE", {"multi_dwelling": "multi_dwelling_housing"})
    import services.housing_sepp_eligibility as he
    monkeypatch.setattr(he, "evaluate_eligibility", lambda *a, **k: [elig])
    form, cite = _lmr_uplift_form("R3", -33.8, 151.1, 600.0, 15.0, False)
    assert form == "multi_dwelling_housing"
    assert cite["source_clause"] == "172(2)(a)"


def test_lmr_uplift_form_no_clause_returns_no_citation(monkeypatch):
    elig = SimpleNamespace(development_type="multi_dwelling", eligible=True,
                           source_clause=None, source_document=None,
                           legislation_url=None, effective_date=None)
    monkeypatch.setattr(ib, "_SEPP_FORM_TO_ENGINE", {"multi_dwelling": "multi_dwelling_housing"})
    import services.housing_sepp_eligibility as he
    monkeypatch.setattr(he, "evaluate_eligibility", lambda *a, **k: [elig])
    form, cite = _lmr_uplift_form("R3", -33.8, 151.1, 600.0, 15.0, False)
    assert form == "multi_dwelling_housing"
    assert cite is None
