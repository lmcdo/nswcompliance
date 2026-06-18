"""GATE-0 — parcel-identity verification (single source of truth).

The NSW Planning Portal ``/address`` search is FUZZY. With ``noOfRecords:1`` and
no identity check, a request for a number/street not present in the cadastre
returns the nearest match on a DIFFERENT street or number, which then gets
stamped AUTHORITATIVE and poisons every downstream figure with the WRONG parcel.

Verified live (2026-06-18):
    "29 Haberfield Rd"  -> "29 STANTON ROAD"   (street does not exist)
    "1 Dalhousie St"    -> "15 DALHOUSIE STREET" (wrong number, right street)
    "29 Dalhousie St"   -> "29 DALHOUSIE STREET" (correct)

Every address->propId resolver must call :func:`parcel_identity_match` on the
resolved label and FAIL CLOSED on a mismatch (return no propId / skip the row),
never silently accept a neighbouring property. This module is the single source
of truth for that check so the three production resolvers stay consistent.
"""
from __future__ import annotations

# Street-type abbreviation -> canonical form, so "Rd" matches "ROAD".
_STREET_TYPE_SYNONYMS = {
    "RD": "ROAD", "ST": "STREET", "AVE": "AVENUE", "AV": "AVENUE", "PL": "PLACE",
    "CR": "CRESCENT", "CRES": "CRESCENT", "DR": "DRIVE", "DRV": "DRIVE", "LN": "LANE",
    "PDE": "PARADE", "CCT": "CIRCUIT", "HWY": "HIGHWAY", "TCE": "TERRACE", "CT": "COURT",
    "GR": "GROVE", "CL": "CLOSE", "WY": "WAY", "BVD": "BOULEVARD", "ESP": "ESPLANADE",
    "SQ": "SQUARE", "PKWY": "PARKWAY",
}
# State/country tokens dropped before comparison (present in the request, absent
# from the Portal label).
_ADDR_DROP_TOKENS = {"NSW", "ACT", "VIC", "QLD", "SA", "WA", "TAS", "NT", "AUSTRALIA"}


def normalize_addr_tokens(s: str) -> list[str]:
    """Normalise an address to comparable tokens.

    Uppercases, expands street-type abbreviations, drops state/country tokens and
    4-digit postcodes, and reduces a unit prefix (``5/29``) to the street number
    (``29``). Returns the ordered token list (street number, street words, suburb).
    """
    if not s:
        return []
    out: list[str] = []
    for raw in s.upper().replace(",", " ").split():
        t = raw.strip(".")
        # unit prefix "5/29" -> street number "29"; rpartition is index-safe and
        # a no-op when there is no slash.
        t = t.rpartition("/")[-1]
        if not t:
            continue
        t = _STREET_TYPE_SYNONYMS.get(t, t)
        if t in _ADDR_DROP_TOKENS:
            continue
        if t.isdigit() and len(t) == 4:  # postcode
            continue
        out.append(t)
    return out


def parcel_identity_match(requested: str, candidate: str) -> bool:
    """True only if the resolved ``candidate`` matches the ``requested`` address
    on street number AND street name.

    The requested tokens (number + street [+ suburb]) must be an exact prefix of
    the candidate's. A bare street number or an empty side never matches.
    """
    req = normalize_addr_tokens(requested)
    cand = normalize_addr_tokens(candidate)
    if len(req) < 2 or len(cand) < len(req):
        return False
    if req[0] != cand[0]:  # street number must match exactly
        return False
    return cand[: len(req)] == req
