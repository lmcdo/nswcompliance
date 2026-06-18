"""GATE-0 — parcel-identity verification tests.

The matcher is the single source of truth that stops the NSW Portal's fuzzy
/address search binding a brief to the WRONG parcel. Cases below are anchored to
live-verified Portal behaviour (2026-06-18).
"""
from pathlib import Path

import pytest

from services.address_identity import normalize_addr_tokens, parcel_identity_match


# --- live-verified accept/reject cases --------------------------------------

@pytest.mark.parametrize("requested,candidate,expected", [
    # exact, full UI-format address
    ("29 Dalhousie Street, Haberfield NSW 2045, Australia", "29 DALHOUSIE STREET HABERFIELD 2045", True),
    # abbreviated street type + no postcode — Portal is formatting-robust
    ("29 Dalhousie St Haberfield", "29 DALHOUSIE STREET HABERFIELD 2045", True),
    # WRONG STREET — "29 Haberfield Rd" does not exist; Portal returns a different street
    ("29 Haberfield Rd, Haberfield NSW 2045", "29 STANTON ROAD HABERFIELD 2045", False),
    # WRONG NUMBER, right street — "1 Dalhousie St" -> "15 Dalhousie St"
    ("1 Dalhousie Street Haberfield", "15 DALHOUSIE STREET HABERFIELD 2045", False),
    # unit prefix reduces to the street number
    ("5/29 Dalhousie Street Haberfield", "29 DALHOUSIE STREET HABERFIELD 2045", True),
    # multi-word street name
    ("12 Old South Head Road, Vaucluse NSW 2030", "12 OLD SOUTH HEAD ROAD VAUCLUSE 2030", True),
    # request without suburb still matches on number + street
    ("29 Smith St", "29 SMITH STREET NEWTOWN 2042", True),
    # same street/suburb, different number is rejected
    ("31 Smith St Newtown", "29 SMITH STREET NEWTOWN 2042", False),
])
def test_parcel_identity_match(requested, candidate, expected):
    assert parcel_identity_match(requested, candidate) is expected


@pytest.mark.parametrize("requested,candidate", [
    ("", "29 DALHOUSIE STREET HABERFIELD 2045"),
    ("29 Dalhousie Street", ""),
    ("29", "29 DALHOUSIE STREET"),   # bare number, no street -> never matches
])
def test_empty_or_bare_inputs_never_match(requested, candidate):
    assert parcel_identity_match(requested, candidate) is False


# --- normalisation ----------------------------------------------------------

def test_normalize_expands_type_and_drops_noise():
    assert normalize_addr_tokens("29 Dalhousie St, Haberfield NSW 2045, Australia") == [
        "29", "DALHOUSIE", "STREET", "HABERFIELD",
    ]


def test_normalize_unit_reduces_to_street_number():
    assert normalize_addr_tokens("5/29 Dalhousie St")[0] == "29"


# --- wiring guard: the gate must stay applied at every production resolver ---

def test_gate_applied_at_all_production_resolvers():
    """Fail loudly if any production address resolver drops the parcel-identity
    check (the bug regresses silently otherwise)."""
    root = Path(__file__).resolve().parent.parent
    for rel in [
        "scripts/generate_conveyancing_report.py",
        "services/pre_da_history.py",
        "services/nsw_planning_api.py",
    ]:
        src = (root / rel).read_text(encoding="utf-8")
        assert "parcel_identity_match" in src, f"GATE-0 missing from {rel}"
