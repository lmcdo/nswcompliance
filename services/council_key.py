"""Council key: Planning Portal LGA name or former-council slug -> the key the DCP tables use.

The Python twin of frontend-nextjs/lib/lga-slug.ts (toLgaSlug), reading the SAME rename list
(frontend-nextjs/lib/lga-slug-renames.json). The yield box sent the raw key 'city_of_parramatta'
to dcp_setback_controls, which stores 'parramatta', and found 0 rows on 8 of 20 test addresses
while the DCP tab, which normalised, showed them (page integrity checks, 2026-10-19).

prior-art-checked: extraction of the existing TS mapper; intelligence_brief._norm_lga is a
different job (fuzzy LGA match for the LEP land-use table) and is left alone.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

_RENAMES_PATH = Path(__file__).resolve().parents[1] / "frontend-nextjs" / "lib" / "lga-slug-renames.json"


@lru_cache(maxsize=1)
def _renames() -> dict[str, str]:
    data = json.loads(_RENAMES_PATH.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def to_council_key(name: Optional[str]) -> Optional[str]:
    """Same rules as toLgaSlug: trim, lower-case, runs of '-'/space -> '_', drop other
    punctuation, then apply the rename list. None for empty input, never '' (a query for ''
    reads back as 'this council has no controls')."""
    raw = (name or "").strip()
    if not raw:
        return None
    norm = re.sub(r"[^a-z0-9_]", "", re.sub(r"[-\s]+", "_", raw.lower()))
    if not norm:
        return None
    return _renames().get(norm, norm)
