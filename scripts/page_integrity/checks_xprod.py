"""C7: the same fact on the assessment page and in the Site Report must agree.

Both products are served from the same database for the same lot, yet on 2026-10-19 they disagreed
on lot area, setbacks and corner status for the same address. Reads `site_report.jsonl.gz` in the
capture folder (written by site_report.py). No Site Report = nothing compared, and
`facts_checked` says so; it is never a pass.

prior-art-checked: logic from the 2026-10-19 evidence script compare.py; no in-repo
cross-product check exists.
"""
from __future__ import annotations

import gzip
import json
from typing import Any, Optional

try:
    from scripts.page_integrity.checks_data import P_CA, P_PROP, Flag, _d, _num
    from scripts.page_integrity.load import Capture
except ImportError:  # run as a plain script from scripts/page_integrity
    from checks_data import P_CA, P_PROP, Flag, _d, _num  # type: ignore
    from load import Capture  # type: ignore

FACTS = ("zone", "lot_area", "height", "fsr", "min_lot", "homes", "front", "side", "rear",
         "heritage", "flood", "corner")


def _v(x: Any) -> Any:
    return x.get("value") if isinstance(x, dict) and "value" in x else x


def site_report(cap: Capture) -> Optional[dict[str, dict]]:
    p = cap.folder / "site_report.jsonl.gz"
    if not p.exists():
        return None
    with gzip.open(p, "rt", encoding="utf-8") as f:
        evs = [json.loads(ln) for ln in f if ln.strip()]
    if not evs or evs[-1].get("event") != "complete":
        return None  # a report that did not finish is not an answer
    return {_d(e.get("data")).get("section"): _d(_d(e.get("data")).get("data"))
            for e in evs if e.get("event") == "section"}


def report_facts(sec: dict[str, dict]) -> dict[str, Any]:
    pc, env = sec.get("planning_controls", {}), sec.get("environmental_constraints", {})
    ca = _d(_v(sec.get("constraint_arithmetic", {})))
    ld = _d(_v(pc.get("lot_dimensions")))
    has_her = "heritage_items" in pc or "heritage_hca" in pc
    return {"zone": _v(pc.get("zone")), "lot_area": ld.get("area_m2"), "height": _v(pc.get("height")),
            "fsr": _v(pc.get("fsr")), "min_lot": _v(pc.get("lot_size")), "homes": ca.get("realistic_dwellings"),
            "front": ca.get("setback_front_m"), "side": ca.get("setback_side_m"), "rear": ca.get("setback_rear_m"),
            "heritage": (bool(_v(pc.get("heritage_items"))) or bool(_v(pc.get("heritage_hca")))) if has_her else None,
            "flood": _v(env.get("flood_epi")), "corner": ld.get("is_corner")}


def page_facts(cap: Capture) -> dict[str, Any]:
    p, ca = _d(cap.data(P_PROP)), _d(cap.data(P_CA))
    k = _d(p.get("constraints"))
    return {"zone": k.get("zone"), "lot_area": _d(p.get("lotDimensions")).get("area"), "height": k.get("maxHeight"),
            "fsr": k.get("maxFsr"), "min_lot": k.get("minLotSize"), "homes": ca.get("realistic_dwellings"),
            "front": ca.get("setback_front_m"), "side": ca.get("setback_side_m"), "rear": ca.get("setback_rear_m"),
            "heritage": _d(p.get("heritage")).get("isHeritage"), "flood": k.get("floodProne"),
            "corner": _d(p.get("cornerLot")).get("isCornerLot")}


def _norm(v: Any) -> Any:
    if v in (None, "", [], {}):
        return None
    if isinstance(v, bool):
        return v
    if (n := _num(v)) is not None:
        return round(n, 2)
    s = str(v).strip().lower().removesuffix("m").removesuffix(":1").strip()
    s = s or None
    if s is None:
        return None
    try:
        return round(float(s), 2)
    except ValueError:
        return s.partition(":")[0].strip() or None  # 'R2: Low Density Residential' -> 'r2'


def _both(cap: Capture) -> Optional[tuple[dict, dict]]:
    sec = site_report(cap)
    if sec is None or cap.data(P_PROP) is None:
        return None
    return page_facts(cap), report_facts(sec)


def check_cross_product(cap: Capture) -> list[Flag]:
    pair = _both(cap)
    if pair is None:
        return []
    page, rep = pair
    flags = []
    for f in FACTS:
        a, b = _norm(page[f]), _norm(rep[f])
        if a is None or b is None or a == b:
            continue
        flags.append(Flag("C7", f, f"assessment page {f}={page[f]!r}; Site Report {f}={rep[f]!r}",
                          {"page": page[f], "site_report": rep[f]}))
    return flags


def facts_checked(cap: Capture) -> dict[str, bool]:
    pair = _both(cap)
    if pair is None:
        return {"site_report": False}
    page, rep = pair
    return {f"xprod:{f}": _norm(page[f]) is not None and _norm(rep[f]) is not None for f in FACTS}
