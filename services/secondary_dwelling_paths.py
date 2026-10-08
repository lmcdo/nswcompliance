"""Secondary dwelling (granny flat): the CDC and DA answers, each from its own clause.

prior-art-checked: reuse not viable because services/granny_flat.py and
scripts/conveyancing_db.py read one `min_lot_size` row (450, cited "53(1)(b)")
as a yes/no gate for every granny flat, which the SEPP (Housing) 2021 does not
say: the 450 m2 figure is s 53(2)(a), a non-discretionary site-area standard for
DETACHED secondary dwellings on the DA path, while the CDC path (Schedule 1
cl 2(1)(b)) sets a road frontage by lot-area band. This module reads the
per-clause rows added by migration 083 and keeps the two paths apart.

Fail closed: any missing, stale, malformed or self-inconsistent rule makes
load_rules() return no rules and named failures; callers report UNAVAILABLE.
A missing property fact makes that path UNKNOWN. Nothing defaults to a pass.
Every number (thresholds and lot-area band limits) comes from the database row
and must appear in that row's own quote of the law.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Literal, Optional

AUTHORITATIVE_URL_PREFIX = "https://legislation.nsw.gov.au/"
FRONTAGE_PREFIX = "cdc_min_road_frontage_"
WORDING_RULES = ("cdc_parking_rule", "da_non_discretionary_note", "da_parking_rule")
NUMERIC_RULES = ("da_detached_min_site_area",)

CdcOutcome = Literal["PASS", "FAIL", "UNKNOWN"]
DaOutcome = Literal["MEETS", "BELOW", "NOT_APPLICABLE", "UNKNOWN"]


@dataclass(frozen=True)
class Rule:
    id: int
    standard_type: str
    pathway: str
    value: Optional[float]
    unit: Optional[str]
    area_min: Optional[float]
    area_min_inclusive: Optional[bool]
    area_max: Optional[float]
    clause: str
    url: str
    quote: str


@dataclass(frozen=True)
class Rules:
    frontage_bands: tuple  # tuple[Rule, ...], ordered by lot-area band
    by_type: dict          # standard_type -> Rule (wording + numeric rules)


@dataclass(frozen=True)
class RulesOutcome:
    rules: Optional[Rules]
    failures: tuple


def _num(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _shown(n: float) -> str:
    return str(int(n)) if n == int(n) else f"{n:g}"


def _flat(text: str) -> str:
    """Collapse whitespace and the superscript split ("450m 2" / "450m2")."""
    return re.sub(r"\s+", " ", (text or "")).replace("m 2", "m2")


def _check_row(r: dict) -> tuple[Optional[Rule], list[str]]:
    st = r.get("standard_type") or "?"
    errs: list[str] = []
    quote = _flat(r.get("source_quote") or "").strip()
    url = (r.get("legislation_url") or "").strip()
    clause = (r.get("source_clause") or "").strip()
    if r.get("stale_since"):
        errs.append(f"{st}: marked stale ({r.get('stale_reason') or 'source amended'})")
    if not quote:
        errs.append(f"{st}: no quote of the law")
    if not clause:
        errs.append(f"{st}: no clause reference")
    if not url.startswith(AUTHORITATIVE_URL_PREFIX) or re.search(r"\s", url):
        errs.append(f"{st}: legislation link missing, not legislation.nsw.gov.au, or broken by whitespace")
    if r.get("approval_pathway") not in ("cdc", "da"):
        errs.append(f"{st}: approval path is not cdc or da")
    value = _num(r.get("numeric_value"))
    a_min, a_max = _num(r.get("lot_area_min_m2")), _num(r.get("lot_area_max_m2"))
    if st.startswith(FRONTAGE_PREFIX) or st in NUMERIC_RULES:
        if value is None or value <= 0:
            errs.append(f"{st}: value is not a finite positive number")
        elif not re.search(rf"(?<![\d.]){re.escape(_shown(value))}\s?m(?:2|²)?\b", quote):
            errs.append(f"{st}: value {_shown(value)} does not appear in its quote")
    elif r.get("numeric_value") is not None:
        errs.append(f"{st}: a wording rule must not carry a number")
    if st.startswith(FRONTAGE_PREFIX):
        if a_min is None or r.get("lot_area_min_inclusive") is None:
            errs.append(f"{st}: lot-area band has no lower limit")
        else:
            word = "at least" if r.get("lot_area_min_inclusive") else "more than"
            if f"{word} {_shown(a_min)}m2" not in quote:
                errs.append(f"{st}: band lower limit '{word} {_shown(a_min)}m2' not in its quote")
        if a_max is not None and f"not more than {_shown(a_max)}m2" not in quote:
            errs.append(f"{st}: band upper limit 'not more than {_shown(a_max)}m2' not in its quote")
    if errs:
        return None, errs
    return Rule(int(r.get("id")), st, r.get("approval_pathway"), value, r.get("unit"),
                a_min, r.get("lot_area_min_inclusive"), a_max, clause, url, quote), []


def validate_rules(rows: list[dict]) -> RulesOutcome:
    """Pure validation of housing_sepp_standards rows with an approval_pathway."""
    failures: list[str] = []
    rules: dict = {}
    for r in rows:
        rule, errs = _check_row(r)
        failures += errs
        if rule:
            rules[rule.standard_type] = rule
    for needed in WORDING_RULES + NUMERIC_RULES:
        if needed not in rules and not any(f.startswith(needed + ":") for f in failures):
            failures.append(f"{needed}: rule missing")
    bands = sorted((r for r in rules.values() if r.standard_type.startswith(FRONTAGE_PREFIX)),
                   key=lambda b: b.area_min)
    if not bands and not any(f.startswith(FRONTAGE_PREFIX) for f in failures):
        failures.append("cdc frontage bands: none found")
    for i, b in enumerate(bands):
        if i == 0 and not b.area_min_inclusive:
            failures.append(f"{b.standard_type}: the lowest band must include its lower limit")
        if i > 0:
            prev = bands[i - 1]
            if prev.area_max is None or prev.area_max != b.area_min or b.area_min_inclusive:
                failures.append(f"{prev.standard_type} / {b.standard_type}: lot-area bands leave a gap or overlap")
        if i < len(bands) - 1 and b.area_max is None:
            failures.append(f"{b.standard_type}: only the top band may be open-ended")
    if bands and bands[-1].area_max is not None:
        failures.append(f"{bands[-1].standard_type}: the top band must be open-ended")
    if failures:
        return RulesOutcome(None, tuple(failures))
    return RulesOutcome(Rules(tuple(bands), {k: v for k, v in rules.items()
                                             if not k.startswith(FRONTAGE_PREFIX)}), ())


def load_rules(conn) -> RulesOutcome:
    """Fetch and validate. A database error is a failure, never an empty rule set."""
    if conn is None:
        return RulesOutcome(None, ("no database connection",))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, standard_type, approval_pathway, numeric_value, unit,
                   lot_area_min_m2, lot_area_min_inclusive, lot_area_max_m2,
                   source_clause, legislation_url, source_quote, stale_since, stale_reason
            FROM housing_sepp_standards
            WHERE development_type = 'secondary_dwelling' AND approval_pathway IS NOT NULL
            """
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
    except Exception as e:  # noqa: BLE001 — reported as unavailable rules
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            pass
        return RulesOutcome(None, (f"rules query failed: {type(e).__name__}",))
    return validate_rules(rows)


def _evidence(rule: Rule) -> dict:
    return {"rule_id": rule.id, "clause": rule.clause, "quote": rule.quote, "url": rule.url}


def _band_for(bands: tuple, area: float) -> Optional[Rule]:
    for b in bands:
        above_min = area >= b.area_min if b.area_min_inclusive else area > b.area_min
        below_max = b.area_max is None or area <= b.area_max
        if above_min and below_max:
            return b
    return None


def _positive(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0


def evaluate_cdc(rules: Rules, lot_area_m2, frontage_range_m, battle_axe: Optional[bool]) -> dict:
    """CDC (Schedule 1 cl 2(1)(b)) road-frontage test only. frontage_range_m is
    (smallest, largest) width the lot can have at the building line."""
    out = {"path": "cdc", "test": "road frontage at the building line",
           "parking": _evidence(rules.by_type["cdc_parking_rule"])}  # noqa: bracket-access — validated
    if battle_axe is None:
        return {**out, "outcome": "UNKNOWN", "reason": "whether the lot is a battle-axe lot is not known"}
    if battle_axe:
        return {**out, "outcome": "UNKNOWN",
                "reason": "battle-axe lot: the Schedule 1 cl 2(1)(c) access-laneway and lot-size test is not measured here"}
    if not _positive(lot_area_m2):
        return {**out, "outcome": "UNKNOWN", "reason": "lot area not established"}
    band = _band_for(rules.frontage_bands, float(lot_area_m2))
    if band is None:
        low = rules.frontage_bands[0]  # noqa: bracket-access — validated non-empty
        return {**out, "outcome": "UNKNOWN", "evidence": _evidence(low),
                "reason": f"Schedule 1 cl 2(1)(b) sets no frontage for a lot of {lot_area_m2:g} m²; a certifier decides"}
    out["evidence"] = _evidence(band)
    out["required_m"] = band.value
    rng = frontage_range_m
    if not (isinstance(rng, tuple) and len(rng) == 2 and all(_positive(v) for v in rng) and rng[0] <= rng[1]):
        return {**out, "outcome": "UNKNOWN", "reason": "road frontage at the building line not measured"}
    lo, hi = float(rng[0]), float(rng[1])
    if lo >= band.value:
        return {**out, "outcome": "PASS", "reason": f"frontage at least {lo:g} m ≥ {band.value:g} m"}
    if hi < band.value:
        return {**out, "outcome": "FAIL", "reason": f"frontage at most {hi:g} m < {band.value:g} m"}
    return {**out, "outcome": "UNKNOWN",
            "reason": f"frontage between {lo:g} m and {hi:g} m depending on which boundary faces the road"}


def evaluate_da(rules: Rules, lot_area_m2, detached: Optional[bool]) -> dict:
    """DA s 53(2)(a): a non-discretionary site-area standard for detached granny
    flats. Being below it is reported with the law's own note; never as a ban."""
    std = rules.by_type["da_detached_min_site_area"]  # noqa: bracket-access — validated
    out = {"path": "da", "evidence": _evidence(std),
           "parking": _evidence(rules.by_type["da_parking_rule"])}  # noqa: bracket-access — validated
    if detached is None:
        return {**out, "outcome": "UNKNOWN", "reason": "whether the granny flat is detached is not known"}
    if not detached:
        return {**out, "outcome": "NOT_APPLICABLE", "reason": "s 53(2)(a) applies to detached secondary dwellings only"}
    if not _positive(lot_area_m2):
        return {**out, "outcome": "UNKNOWN", "reason": "lot area not established"}
    if float(lot_area_m2) >= std.value:
        return {**out, "outcome": "MEETS", "reason": f"lot {lot_area_m2:g} m² ≥ {std.value:g} m² site area"}
    return {**out, "outcome": "BELOW", "reason": f"lot {lot_area_m2:g} m² < {std.value:g} m² site area",
            "note": _evidence(rules.by_type["da_non_discretionary_note"])}  # noqa: bracket-access — validated
