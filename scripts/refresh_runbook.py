#!/usr/bin/env python3
"""Turn a changed planning instrument into a bulk-index refresh runbook.

When the legislation monitor detects an LEP/SEPP version change, the operator
needs to know which ``lot_search_index`` slice to rebuild and the exact commands
to run. This module maps the changed-instrument list to an actionable runbook
that is appended to the Telegram alert — the *command-in-alert* pattern. Nothing
here executes; a human still verifies the change on legislation.nsw.gov.au and
decides whether to run it.

Pure functions, no DB / no network. The ``instrument_key -> LGA`` overlay-name
map is derived from the key slug with explicit overrides for merged / renamed
councils, verified against ``DISTINCT lga_name`` in ``lot_search_index``
(2026-06-17). SEPPs apply statewide and map to ``None``.
"""
from __future__ import annotations

from typing import Optional

# instrument_key -> overlay LGA name, ONLY where the slug differs from the
# overlay name (merged / renamed / "shire" / "city of" councils). The other 19
# LEP keys resolve by the naive transform below. Verified vs lot_search_index.
_LGA_OVERRIDES = {
    "canterbury_bankstown_lep_2023": "CANTERBURY-BANKSTOWN",
    "parramatta_lep_2023": "CITY OF PARRAMATTA",
    "sutherland_lep_2015": "SUTHERLAND SHIRE",
    "the_hills_lep_2019": "THE HILLS SHIRE",
}


def instrument_lga(instrument_key: str) -> Optional[str]:
    """Overlay LGA name for an LEP key, or ``None`` for statewide / not scopable.

    LEP keys are ``<slug>_lep_<year>``; the slug maps to the overlay LGA name
    (uppercased, underscores -> spaces) unless overridden. SEPP keys (and any
    key without ``_lep_``) apply statewide, so there is no single LGA to scope
    to and this returns ``None``.

    Pure function — unit-tested; the connector's correctness hinges on it.
    """
    if "_lep_" not in instrument_key:
        return None
    if instrument_key in _LGA_OVERRIDES:
        return _LGA_OVERRIDES[instrument_key]
    slug = instrument_key.partition("_lep_")[0]
    return slug.replace("_", " ").upper()


def _lep_block(label: str, key: str, lga: str) -> str:
    """Scoped 3-command refresh chain for a single council's LEP change."""
    return (
        f"- {lga} - {label}\n"
        f"    python scripts/update_instrument_provisions.py --key {key}\n"
        f'    python scripts/ingest_spatial_overlays.py --all-layers --lga "{lga}"\n'
        f'    python scripts/build_lot_search_index.py --phase all --lga "{lga}"'
        f" --recompute --trigger legislation_change"
    )


def _sepp_block(label: str, key: str) -> str:
    """Statewide note for a SEPP change — no scoped recompute exists."""
    return (
        f"- STATEWIDE - {label}\n"
        f"    python scripts/update_instrument_provisions.py --key {key}\n"
        f"    Per-address brief reflects this live (fetched per request).\n"
        f"    Bulk index needs a full re-assign when revived, not a scoped recompute."
    )


def build_refresh_runbook(changed: list[tuple[str, str]]) -> str:
    """Build the runbook text for a list of ``(instrument_key, label)`` changes.

    Returns ``""`` when nothing changed (so callers can append unconditionally).
    Each LEP gets a scoped command chain; each SEPP a statewide note. The block
    is operator-facing and leads with a verify-first instruction.
    """
    if not changed:
        return ""
    blocks = [
        _sepp_block(label, key) if instrument_lga(key) is None
        else _lep_block(label, key, instrument_lga(key))
        for key, label in changed
    ]
    return (
        "\n\nBULK-INDEX REFRESH RUNBOOK (verify the change on "
        "legislation.nsw.gov.au first):\n" + "\n".join(blocks)
    )
