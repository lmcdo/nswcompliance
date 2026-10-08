"""Secondary dwelling (granny flat): the CDC and DA answers, each from its own clause.

prior-art-checked: reuse not viable because services/granny_flat.py and
scripts/conveyancing_db.py read one `min_lot_size` row (450, cited "53(1)(b)")
as a yes/no gate for every granny flat, which the SEPP (Housing) 2021 does not
say: the 450 m2 figure is s 53(2)(a), a non-discretionary site-area standard for
DETACHED secondary dwellings on the DA path, while the CDC path (Schedule 1
cl 2(1)(b)) sets a road frontage by lot-area band. This module reads the
per-clause rows added by migration 083 and keeps the two paths apart.

Fail closed: any missing, malformed or self-inconsistent rule makes
load_rules() return no rules and named failures; callers report UNAVAILABLE.
A rule marked stale (its instrument was amended after it was checked) is still
served, with a notice -- the W3 (#839) contract every other SEPP surface uses --
so an amendment does not blank every granny-flat answer; the weekly
provenance check proves each quote is still in the law in force.
A missing property fact makes that path UNKNOWN. Nothing defaults to a pass.
Every number (thresholds and lot-area band limits) comes from the database row
and must appear in that row's own quote of the law.
"""

from __future__ import annotations

import math
import re
from decimal import Decimal
from dataclasses import dataclass
from typing import Literal, Optional

AUTHORITATIVE_URL_PREFIX = "https://legislation.nsw.gov.au/"
FRONTAGE_PREFIX = "cdc_min_road_frontage_"
WORDING_RULES = ("cdc_parking_rule", "da_non_discretionary_note", "da_parking_rule")
ZONE_SCOPE_RULES = ("cdc_zone_scope", "da_zone_scope")
NUMERIC_RULES = ("da_detached_min_site_area",)

CdcOutcome = Literal["PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"]
DaOutcome = Literal["MEETS", "BELOW", "NOT_APPLICABLE", "UNKNOWN"]

# A Standard Instrument zone code (R2, RU1, E4, MU1, SP2...). A zone outside this
# pattern may be an "equivalent land use zone" (s 49), so it is UNKNOWN, not out of scope.
_SI_ZONE_RE = re.compile(r"^[A-Z]{1,2}[0-9]{1,2}[A-Z]?$")


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
    zones: frozenset = frozenset()
    stale: Optional[str] = None  # why the rule awaits a re-check, when it does


@dataclass(frozen=True)
class Rules:
    frontage_bands: tuple  # tuple[Rule, ...], ordered by lot-area band
    by_type: dict          # standard_type -> Rule (wording + numeric rules)


@dataclass(frozen=True)
class RulesOutcome:
    rules: Optional[Rules]
    failures: tuple


def _num(v) -> Optional[float]:
    if v is None:
        return None
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
    stale = (r.get("stale_reason") or "the source instrument was amended") if r.get("stale_since") else None
    if not quote:
        errs.append(f"{st}: no quote of the law")
    if not clause:
        errs.append(f"{st}: no clause reference")
    if not url.startswith(AUTHORITATIVE_URL_PREFIX) or re.search(r"\s", url):
        errs.append(f"{st}: legislation link missing, not legislation.nsw.gov.au, or broken by whitespace")
    if r.get("approval_pathway") not in ("cdc", "da"):
        errs.append(f"{st}: approval path is not cdc or da")
    elif not st.startswith(r.get("approval_pathway") + "_"):
        errs.append(f"{st}: tagged '{r.get('approval_pathway')}' but its name says another path")
    value = _num(r.get("numeric_value"))
    a_min, a_max = _num(r.get("lot_area_min_m2")), _num(r.get("lot_area_max_m2"))
    if st.startswith(FRONTAGE_PREFIX) or st in NUMERIC_RULES:
        if value is None or value <= 0:
            errs.append(f"{st}: value is not a finite positive number")
        else:
            area = st in NUMERIC_RULES  # site area in m2; frontage in metres
            unit_ok = (r.get("unit") in ("m²", "m2")) if area else (r.get("unit") == "m")
            pattern = (rf"(?<![\d.]){re.escape(_shown(value))}\s?m(?:2|²)" if area
                       else rf"(?<![\d.]){re.escape(_shown(value))}\s?m(?![2²\w])")
            if not unit_ok:
                errs.append(f"{st}: unit {r.get('unit')!r} is wrong for this rule")
            elif not re.search(pattern, quote):
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
    zones = frozenset(z.strip() for z in (r.get("applicable_zones") or []) if isinstance(z, str))
    if st in ZONE_SCOPE_RULES:
        if not zones:
            errs.append(f"{st}: no zones listed")
        excluded = set(re.findall(r"other than Zone ([A-Z]{1,2}[0-9]{1,2}[A-Z]?)\b", quote))
        named = set(re.findall(r"\bZone ([A-Z]{1,2}[0-9]{1,2}[A-Z]?)\b", quote))
        for z in sorted(zones):
            if z not in named:
                errs.append(f"{st}: zone {z} does not appear in its quote")
            if z in excluded:
                errs.append(f"{st}: zone {z} is listed but its quote excludes it")
        for z in sorted(named - excluded - zones):
            errs.append(f"{st}: its quote covers zone {z} but the rule does not list it")
    if errs:
        return None, errs
    return Rule(int(r.get("id")), st, r.get("approval_pathway"), value, r.get("unit"),
                a_min, r.get("lot_area_min_inclusive"), a_max, clause, url, quote, zones, stale), []


def validate_rules(rows: list[dict]) -> RulesOutcome:
    """Pure validation of housing_sepp_standards rows with an approval_pathway."""
    failures: list[str] = []
    rules: dict = {}
    for r in rows:
        rule, errs = _check_row(r)
        failures += errs
        if rule:
            rules[rule.standard_type] = rule
    for needed in WORDING_RULES + NUMERIC_RULES + ZONE_SCOPE_RULES:
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
                   source_clause, legislation_url, source_quote, stale_since, stale_reason,
                   applicable_zones
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


def _zone_gate(rules: Rules, scope_rule: str, zone: Optional[str]) -> Optional[dict]:
    """None when the zone is in this path's scope; else an UNKNOWN/NOT_APPLICABLE answer."""
    scope = rules.by_type[scope_rule]  # noqa: bracket-access — validated
    z = (zone or "").strip().split(" ")[0].upper()
    if not z:
        return {"outcome": "UNKNOWN", "reason": "zone not established", "scope": _evidence(scope)}
    if z in scope.zones:
        return None
    if not _SI_ZONE_RE.match(z):
        return {"outcome": "UNKNOWN", "scope": _evidence(scope),
                "reason": f"zone {z} may be an equivalent land use zone; not determined here"}
    return {"outcome": "NOT_APPLICABLE", "scope": _evidence(scope),
            "reason": f"zone {z} is outside this path's zones ({', '.join(sorted(scope.zones))})"}


def _positive(v) -> bool:
    """A finite positive number. Accepts Decimal (PostgreSQL numeric); rejects bool."""
    if isinstance(v, bool) or not isinstance(v, (int, float, Decimal)):
        return False
    f = _num(v)
    return f is not None and f > 0


def evaluate_cdc(rules: Rules, zone: Optional[str], lot_area_m2, frontage_range_m,
                 battle_axe: Optional[bool]) -> dict:
    """CDC (Schedule 1 cl 2(1)(b)) road-frontage test only. frontage_range_m is
    (smallest, largest) width the lot can have at the building line."""
    out = {"path": "cdc", "test": "road frontage at the building line",
           "parking": _evidence(rules.by_type["cdc_parking_rule"])}  # noqa: bracket-access — validated
    gate = _zone_gate(rules, "cdc_zone_scope", zone)
    if gate:
        return {**out, **gate}
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
    if not (isinstance(rng, tuple) and len(rng) == 2 and all(_positive(v) for v in rng)):
        return {**out, "outcome": "UNKNOWN", "reason": "road frontage at the building line not measured"}
    lo, hi = float(rng[0]), float(rng[1])
    if lo > hi:
        return {**out, "outcome": "UNKNOWN", "reason": "frontage range is inverted"}
    if lo >= band.value:
        return {**out, "outcome": "PASS", "reason": f"frontage at least {lo:g} m ≥ {band.value:g} m"}
    if hi < band.value:
        return {**out, "outcome": "FAIL", "reason": f"frontage at most {hi:g} m < {band.value:g} m"}
    return {**out, "outcome": "UNKNOWN",
            "reason": f"frontage between {lo:g} m and {hi:g} m depending on which boundary faces the road"}


def evaluate_da(rules: Rules, zone: Optional[str], lot_area_m2, detached: Optional[bool],
                dwelling_house_permissible: Optional[bool]) -> dict:
    """DA s 53(2)(a): a non-discretionary site-area standard for detached granny
    flats. Being below it is reported with the law's own note; never as a ban."""
    std = rules.by_type["da_detached_min_site_area"]  # noqa: bracket-access — validated
    out = {"path": "da", "evidence": _evidence(std),
           "parking": _evidence(rules.by_type["da_parking_rule"]),  # noqa: bracket-access — validated
           "scope": _evidence(rules.by_type["da_zone_scope"])}  # noqa: bracket-access — validated
    gate = _zone_gate(rules, "da_zone_scope", zone)
    if gate:
        return {**out, **gate}
    # s 50: the Part applies only "if development for the purposes of a dwelling
    # house is permissible on the land under another environmental planning
    # instrument" — a fact the caller must establish (e.g. from the LEP land use
    # table); never assumed.
    if dwelling_house_permissible is None:
        return {**out, "outcome": "UNKNOWN",
                "reason": "whether a dwelling house is permissible on the land (s 50) is not established"}
    if not dwelling_house_permissible:
        return {**out, "outcome": "NOT_APPLICABLE",
                "reason": "s 50: a dwelling house is not permissible on the land, so this Part does not apply"}
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


# The development_type whose lot tests are owned by this module. Generic per-form
# readers skip their own lot-size logic for it and call assess() instead.
PATH_RULED_DEV_TYPE = "secondary_dwelling"

_CDC_LABEL = {"PASS": "meets the road-frontage test", "FAIL": "does not meet the road-frontage test",
              "UNKNOWN": "not determined", "NOT_APPLICABLE": "does not apply"}
_DA_LABEL = {"MEETS": "meets the site-area standard", "BELOW": "below the site-area standard",
             "UNKNOWN": "not determined", "NOT_APPLICABLE": "does not apply"}


def assess(rules: Rules, zone: Optional[str], lot_area_m2, *, frontage_range_m=None,
           battle_axe: Optional[bool] = None, detached: Optional[bool] = None,
           dwelling_house_permissible: Optional[bool] = None) -> dict:
    """Both approval paths for one lot, plus one plain-English summary.

    Every surface that talks about granny flats calls this, so they say the same
    thing. Lot area on its own never rules a granny flat out here: the SEPP sets a
    frontage by lot-area band on the CDC path and a non-discretionary site area for
    DETACHED granny flats on the DA path, not one minimum for every granny flat.
    """
    cdc = evaluate_cdc(rules, zone, lot_area_m2, frontage_range_m, battle_axe)
    da = evaluate_da(rules, zone, lot_area_m2, detached, dwelling_house_permissible)
    area = float(lot_area_m2) if lot_area_m2 is not None and _positive(lot_area_m2) else None
    band = _band_for(rules.frontage_bands, area) if area is not None else None
    cdc_line = f"Complying development (CDC): {_CDC_LABEL[cdc['outcome']]} — {cdc['reason']}."
    if band is not None and cdc["outcome"] == "UNKNOWN" and "required_m" not in cdc:  # noqa: bracket-access — evaluate_* always sets outcome
        cdc_line += (f" For a lot of {area:g} m² the road frontage required at the "
                     f"building line is {band.value:g} m ({band.clause}).")
    da_line = f"Development application (DA): {_DA_LABEL[da['outcome']]} — {da['reason']}."
    if da["outcome"] == "BELOW":  # noqa: bracket-access — evaluate_* always sets outcome
        da_line += f" {da['note']['clause']}: \"{da['note']['quote']}\""
    site = rules.by_type["da_detached_min_site_area"]  # noqa: bracket-access — validated
    if da["outcome"] == "UNKNOWN" and area is not None and area < site.value:  # noqa: bracket-access — evaluate_* always sets outcome
        note = rules.by_type["da_non_discretionary_note"]  # noqa: bracket-access — validated
        da_line += (f" If the granny flat is detached, this lot of {area:g} m² is below the "
                    f"{site.value:g} m² site area ({site.clause}); {note.clause}: \"{note.quote}\"")
    summary = ("The SEPP (Housing) 2021 sets no single minimum lot size for a granny flat; "
               "the test depends on the approval path. " + cdc_line + " " + da_line)
    stale = sorted({r.stale for r in (*rules.frontage_bands, *rules.by_type.values()) if r.stale})
    if stale:
        summary += (f" Note: {'; '.join(stale)} after these rules were last checked; "
                    "a re-check against the amended instrument is pending.")
    return {"cdc": cdc, "da": da,
            "cdc_frontage_required_m": band.value if band is not None else None,
            "cdc_frontage_rule": _evidence(band) if band is not None else None,
            "summary": summary, "stale": stale}
