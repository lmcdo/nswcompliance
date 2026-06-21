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
