"""R: the page against facts checked by HAND for a reference address (expected.json).

C1-C6 catch a page that disagrees with itself. They cannot catch a page that agrees with itself and
is wrong. For a few reference addresses each displayed fact was checked once by a person against an
independent source (Portal map layers, the lot boundary, the DCP PDF) and saved as
`tests/fixtures/page_integrity/<slug>/expected.json`; this compares a capture to it.

prior-art-checked: no expected-value comparison exists for page captures (checks_data/checks_text
compare surfaces with each other only).

A fact the page does not show is reported by `facts_checked` as False, never as a pass.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

try:
    from scripts.page_integrity.checks_data import P_CA, P_PROP, Flag, _d, _num
    from scripts.page_integrity.load import Capture
except ImportError:  # run as a plain script from scripts/page_integrity
    from checks_data import P_CA, P_PROP, Flag, _d, _num  # type: ignore
    from load import Capture  # type: ignore

REF_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "page_integrity"


def expected_for(cap: Capture) -> Optional[dict]:
    for p in (cap.folder / "expected.json", REF_DIR / cap.folder.name / "expected.json"):
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return None


def _shown(cap: Capture) -> dict[str, Any]:
    """What the page showed, by fact name. A fact whose source route is missing is left out."""
    out: dict[str, Any] = {}
    p = cap.data(P_PROP)
    if isinstance(p, dict):
        k = _d(p.get("constraints"))
        for fact, key in (("zone", "zone"), ("height_m", "maxHeight"), ("fsr", "maxFsr"),
                          ("min_lot_m2", "minLotSize"), ("heritage", "heritage"),
                          ("flood_lep_map", "floodProne"), ("bushfire", "bushfireProne")):
            if key in k:
                out[fact] = k[key]
        if "area" in _d(p.get("lotDimensions")):
            out["lot_area_m2"] = _d(p.get("lotDimensions"))["area"]
        if "isCornerLot" in _d(p.get("cornerLot")):
            out["corner"] = _d(p.get("cornerLot"))["isCornerLot"]
        s = _d(p.get("strataInfo"))
        if "isStrata" in s:
            out["strata"] = s["isStrata"]
    ca = cap.data(P_CA)
    if isinstance(ca, dict):
        for side in ("front", "side", "rear"):
            if (v := _num(ca.get(f"setback_{side}_m"))) is not None:
                out[f"setback_{side}_m"] = v
    return out


def _agrees(want: dict, got: Any) -> bool:
    if "allowed" in want:  # a setback: the page's single figure must be one the DCP actually gives
        g = _num(got)
        return g is not None and any(abs(g - a) < 0.01 for a in want["allowed"])
    v = want.get("value")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        g = _num(got)
        if g is None:
            return False
        tol = abs(v) * (want.get("tolerance_pct") or 0) / 100 or 1e-6
        return abs(g - v) <= tol
    if isinstance(v, str):
        return isinstance(got, str) and got.strip().upper().startswith(v.upper())
    return got == v  # bool / None


def check_reference(cap: Capture) -> list[Flag]:
    exp = expected_for(cap)
    if not exp:
        return []
    shown, flags = _shown(cap), []
    for fact, want in exp["facts"].items():
        if fact not in shown or _agrees(want, shown[fact]):
            continue
        flags.append(Flag("R", f"reference:{fact}",
                          f"page shows {fact}={shown[fact]!r}; hand-checked "
                          f"{want['allowed'] if 'allowed' in want else want.get('value')!r} ({want['source']})",
                          want))
    return flags


def facts_checked(cap: Capture) -> dict[str, bool]:
    exp = expected_for(cap)
    if not exp:
        return {}
    shown = _shown(cap)
    return {f"reference:{f}": f in shown for f in exp["facts"]}
