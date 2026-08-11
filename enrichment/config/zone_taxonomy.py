"""NSW zone taxonomy — Python accessor for the shared legacy/current zone
alias map (DQ-30).

prior-art-checked: no existing Python module maps legacy (B1-B8, IN1-IN4) zone
codes to current (E1-E5, MU1) codes — confirmed during the DQ-30 investigation
(.claude/DATA_QUALITY_TRACKER.md) via repo-wide search; the only prior art was
the TypeScript-only `frontend-nextjs/lib/zone-translation.ts`, which this
module and its shared JSON source now back both languages with.

Loads `frontend-nextjs/shared/zone-taxonomy.json` — the single authored source
(see `scripts/generate_zone_taxonomy.py`) — so Python and TypeScript can never
independently drift on the legacy/current mapping again. Deliberately has no
database dependency: `enrichment/config/*.py` is imported by offline/batch
tagging code that must stay deterministic and reproducible without a live
connection. For the separate question of "what zones currently exist in LGA X"
(which does need a live query, since it changes as LGAs get onboarded), see
`services/db_config.get_valid_zones_for_lga()`.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

_TAXONOMY_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "frontend-nextjs" / "shared" / "zone-taxonomy.json"
)


def _load_taxonomy() -> dict:
    if not _TAXONOMY_PATH.exists():
        raise FileNotFoundError(
            f"{_TAXONOMY_PATH} not found — run "
            "`python scripts/generate_zone_taxonomy.py` to generate it"
        )
    with open(_TAXONOMY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_TAXONOMY = _load_taxonomy()

ZONE_TRANSLATION_MAP: Dict[str, List[str]] = _TAXONOMY["legacyToCurrentAliases"]
LEGACY_ZONES: List[str] = _TAXONOMY["legacyZones"]


def get_zone_aliases(zone: str) -> List[str]:
    """Get all zone code aliases (current + legacy) for a given zone.

    Mirrors frontend-nextjs/lib/zone-translation.ts's getZoneAliases() exactly
    — same semantics, same shared data source.

    Args:
        zone: A zone code, either current (e.g. "E1") or legacy (e.g. "B1").

    Returns:
        [current_code, *legacy_aliases] if zone is known, else [zone] as-is.
    """
    if zone in ZONE_TRANSLATION_MAP:
        return ZONE_TRANSLATION_MAP[zone]

    if zone in LEGACY_ZONES:
        for current_zone, aliases in ZONE_TRANSLATION_MAP.items():
            if zone in aliases:
                return aliases

    return [zone]


def is_legacy_zone(zone: str) -> bool:
    """Check if a zone code is legacy (pre-26 April 2023)."""
    return zone in LEGACY_ZONES


def get_current_zone(legacy_zone: str) -> Optional[str]:
    """Get the current zone code equivalent for a legacy zone code.

    Args:
        legacy_zone: A legacy zone code, e.g. "B1".

    Returns:
        The current zone code, e.g. "E1", or None if not a known legacy zone.
    """
    for current_zone, aliases in ZONE_TRANSLATION_MAP.items():
        if legacy_zone in aliases and current_zone != legacy_zone:
            return current_zone
    return None
