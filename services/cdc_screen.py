"""CDC (Complying Development Certificate) preliminary screen — backend engine.

One engine for every surface that answers "can this property likely use the
CDC pathway?" (issue #820): the conveyancing PDF CDC row and the workbench
/api/cdc/preliminary-check route both consume this instead of carrying their
own copies of the rules.

Regulatory values come ONLY from cdc_eligibility_standards (migration 058),
where every row cites the regulatory_provisions ids it was extracted from.
Nothing here hardcodes a zone list, lot minimum, or height figure. When the
verified standards are absent the loader returns None and callers fail closed
("Not assessed") — the #684/#816/#819 pattern.

Verdict contract: the screen never answers "yes". It answers "no" with cited
exclusions, or "maybe" with a certifier disclaimer. Exclusion-based screening
identifies land that cannot use the pathway; it does not assess a proposal.

Two checks are deliberately map/register-driven rather than standards-table
rows, because the authoritative source is a live layer:
  - the Codes SEPP complying-development exclusion area (ePlanning layer 92)
  - dual-occupancy prohibition areas (ePlanning layer 452)
Contamination severity mapping: the Codes SEPP land-exclusion list includes
"significantly contaminated land" (regulatory_provisions id 36185) — only the
lot itself being on the EPA register maps to an exclusion; a register site
merely nearby is a warning. A mine subsidence district is NOT a Codes SEPP
exclusion: it adds a Subsidence Advisory NSW approval requirement under other
legislation, so it always maps to a warning.
"""

import logging
import math
import re
from typing import Literal, Optional

from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "This is a preliminary indicator only. It does not replace a formal CDC "
    "assessment by a registered certifier. Always check constraints with the "
    "relevant council and engage a professional for any development proposal."
)

_REQUIRED_STANDARDS = ("eligible_zones", "min_lot_size")


class CdcExclusion(BaseModel):
    reason: str
    constraint: str
    severity: Literal["definite", "likely"]
    source: str


class CdcScreenInputs(BaseModel):
    """Property facts feeding the screen. None = the fact could not be
    determined (three-state); every None surfaces as an unchecked warning,
    never as a silent pass. Non-finite numbers are coerced to None so a NaN
    from an upstream calculation surfaces as unchecked, not a silent pass."""

    zone_code: Optional[str] = None
    lot_area_m2: Optional[float] = None
    # What is proposed, when known (e.g. 'dual_occupancy', 'dwelling_house').
    # Proposal-specific prohibitions only exclude when they match this.
    development_type: Optional[str] = None
    # Whether the min-lot standard's conditionality is satisfied for this lot
    # (e.g. cl 6.4(1)(d)(ii): True = no minimum size is specified for the lot,
    # so the standard's figure applies; False = a specified minimum governs
    # instead; None = unknown).
    min_lot_condition_met: Optional[bool] = None
    heritage_item: Optional[bool] = None
    heritage_conservation_area: Optional[bool] = None
    flood_prone: Optional[bool] = None
    bushfire_prone: Optional[bool] = None
    acid_sulfate_class: Optional[int] = None
    complying_excluded: Optional[bool] = None       # ePlanning layer 92
    dual_occ_prohibited: Optional[bool] = None      # ePlanning layer 452
    dual_occ_epi_name: Optional[str] = None
    contaminated_lot_on_register: Optional[bool] = None
    contamination_within_500m: Optional[bool] = None
    mine_subsidence_district: Optional[bool] = None

    @field_validator("lot_area_m2")
    @classmethod
    def _positive_finite_or_none(cls, v):
        # Non-finite AND non-positive areas are upstream error sentinels, not
        # measurements — surface as unchecked, never as an exclusion.
        if v is not None and (not math.isfinite(v) or v <= 0):
            return None
        return v

    @field_validator("acid_sulfate_class")
    @classmethod
    def _valid_class_or_none(cls, v):
        # Acid Sulfate Soils Maps use classes 1-5; anything else is corrupt
        # upstream data and must read as unknown, not as screened-and-clear.
        if v is not None and not 1 <= v <= 5:
            return None
        return v


class CdcScreenResult(BaseModel):
    eligible: Literal["no", "maybe"]                # never "yes"
    exclusions: list[CdcExclusion]
    warnings: list[str]
    checks_performed: list[str]
    unchecked: list[str]
    disclaimer: str = DISCLAIMER


def _validate_standards(standards: Optional[dict]) -> Optional[dict]:
    """Boundary validation shared by loader and engine (Sol #816 lesson: the
    engine re-validates whatever it is handed). Returns the dict only when the
    minimum is a finite positive number and every zone is a non-empty string."""
    if not standards:
        return None
    try:
        min_lot = float(standards.get("min_lot_size"))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(min_lot) or min_lot <= 0:
        return None
    raw_zones = standards.get("eligible_zones")
    if not isinstance(raw_zones, (list, tuple, set)):
        return None
    zones = set()
    for z in raw_zones:
        if not isinstance(z, str) or not z.strip():
            return None
        zones.add(z.strip())
    if not zones:
        return None
    validated = dict(standards)
    validated["min_lot_size"] = min_lot
    validated["eligible_zones"] = zones
    return validated


def load_cdc_standards(conn, code_name: str = "housing_code") -> Optional[dict]:
    """Load verified CDC standards for one code. NO fallback: missing table,
    missing rows, unverified rows, or invalid values all return None and the
    caller renders "Not assessed". Never raises.

    Returns {"eligible_zones": set[str], "min_lot_size": float,
             "min_lot_conditionality": Optional[str],
             "acid_sulfate_max_class": Optional[int],
             "refs": {standard_type: ref_number}} or None.
    """
    if conn is None:
        logger.warning("CDC standards: no DB connection — screen unavailable, callers fail closed")
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT standard_type, numeric_value, applicable_zones, conditionality, ref_number,
                   stale_since, stale_reason
            FROM cdc_eligibility_standards
            WHERE code_name = %s AND manual_verified = TRUE AND is_active = TRUE
            """,
            (code_name,),
        )
        fetched = cur.fetchall()
        cur.close()
    except Exception as e:
        logger.warning("CDC standards: query failed — screen unavailable, callers fail closed: %s", e)
        try:
            conn.rollback()   # don't leave a shared connection in an aborted transaction
        except Exception:
            pass
        return None

    rows = {r[0]: {"numeric_value": r[1], "applicable_zones": r[2],
                   "conditionality": r[3], "ref_number": r[4],
                   "stale_since": r[5], "stale_reason": r[6]}
            for r in fetched}
    if len(rows) != len(fetched):
        # Two active rows for one standard type (index dropped or bypassed):
        # picking either would be nondeterministic — fail closed instead.
        logger.warning("CDC standards: duplicate active rows for %s — screen unavailable, callers fail closed", code_name)
        return None

    if any(t not in rows for t in _REQUIRED_STANDARDS):
        logger.warning(
            "CDC standards: no verified %s rows for %s — screen unavailable, callers fail closed",
            "/".join(t for t in _REQUIRED_STANDARDS if t not in rows), code_name,
        )
        return None

    # Auto-stale (W3): a version change of the source instrument marks rows
    # stale — values still serve, but consumers surface a notice.
    # The date and reason must come from the SAME row (Sol #839: independent
    # max()/next() could pair amendment A's reason with amendment B's date).
    _stale = sorted(
        ((v.get("stale_since"), v.get("stale_reason")) for v in rows.values()
         if v.get("stale_since")),
        key=lambda x: x[0],
    )
    _latest = _stale[-1] if _stale else (None, None)
    candidate = {
        "eligible_zones": rows["eligible_zones"]["applicable_zones"],  # noqa: bracket-access — key guaranteed by guard above
        "min_lot_size": rows["min_lot_size"]["numeric_value"],  # noqa: bracket-access — key guaranteed by guard above
        "min_lot_conditionality": rows["min_lot_size"]["conditionality"],  # noqa: bracket-access — key guaranteed by guard above
        "acid_sulfate_max_class": None,
        "refs": {t: v["ref_number"] for t, v in rows.items()},  # noqa: bracket-access — key guaranteed by guard above
        "stale_since": _latest[0],
        "stale_reason": _latest[1],
    }
    ass = rows.get("acid_sulfate_max_class")
    if ass is not None:
        # A PRESENT threshold must be a whole number in the map's class range;
        # an invalid value fails the whole load — silently dropping the check
        # would screen with incomplete standards (Sol review of PR #824).
        try:
            raw = float(ass["numeric_value"])  # noqa: bracket-access — key guaranteed by guard above
        except (TypeError, ValueError):
            raw = None
        if raw is None or not math.isfinite(raw) or raw != int(raw) or not 1 <= int(raw) <= 5:
            logger.warning("CDC standards: invalid acid_sulfate_max_class for %s — screen unavailable, callers fail closed", code_name)
            return None
        candidate["acid_sulfate_max_class"] = int(raw)
    validated = _validate_standards(candidate)
    if validated is None:
        logger.warning("CDC standards: verified rows failed validation for %s — callers fail closed", code_name)
    return validated


def run_cdc_screen(standards: dict, inputs: CdcScreenInputs) -> CdcScreenResult:
    """Run the exclusion screen. `standards` must be a loaded standards dict;
    it is re-validated here and a ValueError raised on garbage — callers decide
    'Not assessed' BEFORE calling, they never get a screen from bad standards."""
    standards = _validate_standards(standards)
    if standards is None:
        raise ValueError("run_cdc_screen requires validated standards; caller must fail closed on None")

    exclusions: list[CdcExclusion] = []
    warnings: list[str] = []
    checks: list[str] = []
    unchecked: list[str] = []
    refs = standards.get("refs") or {}

    # Auto-stale notice (W3): last-reviewed values keep serving, with the
    # change stated plainly — never a silent stale figure.
    if standards.get("stale_since"):
        _since = standards.get("stale_since")
        _date = _since.date().isoformat() if hasattr(_since, "date") else str(_since)
        warnings.append(
            f"Note: {standards.get('stale_reason') or 'the source instrument was amended'} "
            f"(detected {_date}) after these standards were last reviewed. Figures shown "
            f"reflect the last review; a re-check against the amended instrument is pending."
        )

    def _cite(standard_type: str) -> str:
        ref = refs.get(standard_type)
        return f"SEPP (Exempt and Complying Development Codes) 2008{f', {ref}' if ref else ''}"

    # 1. Zone
    checks.append("Zone")
    if inputs.zone_code is None:
        unchecked.append("zone")
    elif inputs.zone_code.strip() not in standards["eligible_zones"]:  # noqa: bracket-access — key guaranteed by guard above
        exclusions.append(CdcExclusion(
            reason=f"Zone {inputs.zone_code.strip()} is not in the zones this code applies to",
            constraint="zone", severity="definite", source=_cite("eligible_zones"),
        ))

    # 2. Lot size. The standard may be conditional (e.g. cl 6.4(1)(d)(ii)'s
    # figure applies only when no minimum size is specified for the lot) — the
    # condition is EVALUATED, not just quoted (Sol review of PR #824):
    #   condition met / unconditional → below-threshold = definite exclusion
    #   condition NOT met → the standard's figure does not govern → unchecked
    #   condition unknown → below-threshold = 'likely', with the condition quoted
    checks.append("Lot size")
    cond = standards.get("min_lot_conditionality")
    if cond and inputs.min_lot_condition_met is False:
        unchecked.append("lot size (a specified minimum applies; this standard's figure does not govern)")
    elif inputs.lot_area_m2 is None:
        unchecked.append("lot size")
    elif inputs.lot_area_m2 < standards["min_lot_size"]:  # noqa: bracket-access — key guaranteed by guard above
        conditional = bool(cond) and inputs.min_lot_condition_met is not True
        exclusions.append(CdcExclusion(
            reason=(
                f"Lot area {inputs.lot_area_m2:,.10g} m² is below the "
                f"{standards['min_lot_size']:g} m² minimum"
                + (f" — applies only where: {cond}" if conditional else "")
            ),
            constraint="lot_size",
            severity="likely" if conditional else "definite",
            source=_cite("min_lot_size"),
        ))

    # 3. Heritage: a heritage ITEM maps to a definite exclusion; a conservation
    # area is conditional in the instrument, so it stays a 'likely' flag. The
    # two facts are independent — an unknown item status is NOT cleared by a
    # known-false conservation-area status (Sol review round 2).
    checks.append("Heritage")
    if inputs.heritage_item is None:
        unchecked.append("heritage item")
    elif inputs.heritage_item:
        exclusions.append(CdcExclusion(
            reason="Heritage item mapped on this land",
            constraint="heritage", severity="definite", source="NSW Planning Portal",
        ))
    if inputs.heritage_conservation_area is None:
        unchecked.append("heritage conservation area")
    elif inputs.heritage_conservation_area and not inputs.heritage_item:
        exclusions.append(CdcExclusion(
            reason="In a heritage conservation area — complying development is restricted; a certifier must assess which works remain available",
            constraint="heritage", severity="likely", source="NSW Planning Portal",
        ))

    # 4-5. Flood / bushfire mapping alone does not establish a Codes SEPP
    # exclusion — the instrument applies category-specific tests and additional
    # development standards. 'likely' flags, never a definite 'no' from the
    # broad overlay boolean (Sol review of PR #824).
    for field, label, constraint in (
        ("flood_prone", "Flood risk", "flood"),
        ("bushfire_prone", "Bushfire risk", "bushfire"),
    ):
        checks.append(label)
        value = getattr(inputs, field)
        if value is None:
            unchecked.append(label.lower())
        elif value:
            exclusions.append(CdcExclusion(
                reason=(
                    f"{label} constraint mapped on this land — the CDC pathway applies "
                    f"category-specific tests and additional development standards here; "
                    f"a certifier must assess which apply"
                ),
                constraint=constraint, severity="likely", source="NSW Planning Portal",
            ))

    # 6. Acid sulfate soils — only when the standards carry the class threshold;
    # no hardcoded class cutoff.
    if standards.get("acid_sulfate_max_class") is not None:
        checks.append("Acid sulfate soils")
        if inputs.acid_sulfate_class is None:
            unchecked.append("acid sulfate soils")
        elif inputs.acid_sulfate_class <= standards["acid_sulfate_max_class"]:  # noqa: bracket-access — key guaranteed by guard above
            exclusions.append(CdcExclusion(
                reason=f"Acid sulfate soils Class {inputs.acid_sulfate_class}",
                constraint="acid_sulfate", severity="likely",
                source=_cite("acid_sulfate_max_class"),
            ))

    # 7. Complying-development exclusion area — authoritative live layer.
    checks.append("Complying development exclusion area")
    if inputs.complying_excluded is None:
        unchecked.append("complying development exclusion area")
    elif inputs.complying_excluded:
        exclusions.append(CdcExclusion(
            reason="In a mapped complying development exclusion area",
            constraint="complying_exclusion", severity="definite",
            source="NSW ePlanning MapServer (SEPP Exempt & Complying Codes 2008)",
        ))

    # 8. Dual-occupancy prohibition — authoritative live layer, but it only
    # excludes DUAL-OCC proposals; for any other (or unknown) proposal it is a
    # warning, not a pathway rejection (Sol review of PR #824).
    checks.append("Dual occupancy prohibition")
    if inputs.dual_occ_prohibited is None:
        unchecked.append("dual occupancy prohibition")
    elif inputs.dual_occ_prohibited:
        if inputs.development_type == "dual_occupancy":
            exclusions.append(CdcExclusion(
                reason="Dual occupancy development is prohibited on this land",
                constraint="dual_occ_prohibition", severity="definite",
                source=inputs.dual_occ_epi_name or "NSW ePlanning MapServer",
            ))
        elif inputs.development_type is None:
            # A definite prohibition exists here but whether it governs is
            # unknowable without the proposal type — surface that, don't
            # quietly downgrade (Sol review round 2).
            unchecked.append("development type (a dual-occupancy prohibition applies here; whether it governs this proposal could not be determined)")
            warnings.append(
                "This land is in a mapped dual-occupancy prohibition area. It "
                "excludes dual-occupancy proposals; the proposal type was not "
                "determined, so whether it applies here was not assessed."
            )
        else:
            warnings.append(
                "This land is in a mapped dual-occupancy prohibition area. That "
                "affects dual-occupancy proposals only; other development types "
                "are not excluded by it."
            )

    # 9. Contamination — exclusion only when the LOT is on the register
    # ("significantly contaminated land" is on the Codes SEPP land-exclusion
    # list); a register site nearby is a warning, never an exclusion.
    checks.append("Contaminated land")
    # The subject-lot register status and the proximity result are independent
    # facts: an unknown lot status is NOT cleared by a known-false proximity
    # result (Sol review round 2).
    if inputs.contaminated_lot_on_register is None:
        unchecked.append("contaminated land (subject-lot register status)")
    elif inputs.contaminated_lot_on_register:
        exclusions.append(CdcExclusion(
            reason="Lot is on the EPA contaminated-land record (significantly contaminated land is excluded from complying development)",
            constraint="contamination", severity="definite",
            source="EPA Contaminated Land Record + SEPP (Exempt and Complying Development Codes) 2008",
        ))
    if inputs.contamination_within_500m and not inputs.contaminated_lot_on_register:
        warnings.append(
            "An EPA contaminated-land record site lies within 500 m. That does not "
            "exclude this lot from complying development; check the lot's own status."
        )

    # 10. Mine subsidence district — warning only: an approval requirement
    # under other legislation, not a Codes SEPP exclusion.
    checks.append("Mine subsidence district")
    if inputs.mine_subsidence_district is None:
        unchecked.append("mine subsidence district")
    elif inputs.mine_subsidence_district:
        warnings.append(
            "In a mine subsidence district — building work requires Subsidence "
            "Advisory NSW approval in addition to any CDC."
        )

    if unchecked:
        warnings.append(
            "Not screened (data unavailable): " + ", ".join(unchecked) + ". "
            "These constraints may still exclude the CDC pathway."
        )

    eligible: Literal["no", "maybe"] = (
        "no" if any(e.severity == "definite" for e in exclusions) else "maybe"
    )
    return CdcScreenResult(
        eligible=eligible, exclusions=exclusions, warnings=warnings,
        checks_performed=checks, unchecked=unchecked,
    )


def load_cdc_standards_from_url(db_url: Optional[str], code_name: str = "housing_code") -> Optional[dict]:
    """Open a connection, load verified standards, close. Never raises —
    any failure returns None and the caller renders "Not assessed"."""
    if not db_url:
        logger.warning("CDC standards: DATABASE_URL not set — screen unavailable, callers fail closed")
        return None
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        return load_cdc_standards(conn, code_name=code_name)
    except Exception as e:
        logger.warning("CDC standards: connection failed — screen unavailable, callers fail closed: %s", e)
        return None
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


_ACID_CLASS_RE = re.compile(r"class\s*([1-5])", re.IGNORECASE)


def build_cdc_inputs(
    zone: Optional[str],
    lot_area_m2: Optional[float],
    heritage_items,
    heritage_hca,
    unique_overlays: Optional[list],
    covered_layers,
) -> CdcScreenInputs:
    """Map conveyancing-report data (controls/overlays shapes) to CdcScreenInputs.

    Three-state everywhere: an overlay ABSENT from unique_overlays reads False
    only when its layer is in covered_layers (the layer was queried and found
    nothing); otherwise None (never checked). heritage lists follow the portal
    controls shape: a list (possibly empty) is a known answer, None is unknown.
    Facts this report path never fetches (exclusion-area layer, dual-occ
    prohibition, contamination register, subsidence district at this stage)
    are simply omitted — they surface in the result's unchecked list.
    """
    _zone_parts = (zone or "").split()
    zone_code = _zone_parts[0].upper() if _zone_parts else None

    overlays = unique_overlays or []
    covered = covered_layers or set()

    def _overlay_state(layer: str) -> Optional[bool]:
        if any(o.get("layer_type") == layer for o in overlays):
            return True
        return False if layer in covered else None

    acid_class = None
    for o in overlays:
        if o.get("layer_type") == "acid_sulfate":
            m = _ACID_CLASS_RE.search(str(o.get("value") or ""))
            if m:
                acid_class = int(m.group(1))
            break

    return CdcScreenInputs(
        zone_code=zone_code,
        lot_area_m2=lot_area_m2,
        heritage_item=None if heritage_items is None else bool(heritage_items),
        heritage_conservation_area=None if heritage_hca is None else bool(heritage_hca),
        flood_prone=_overlay_state("flood"),
        bushfire_prone=_overlay_state("bushfire"),
        acid_sulfate_class=acid_class,
    )


def run_cdc_screen_for_report(
    db_url: Optional[str],
    zone: Optional[str],
    lot_area_m2: Optional[float],
    heritage_items,
    heritage_hca,
    unique_overlays: Optional[list],
    covered_layers,
) -> Optional[CdcScreenResult]:
    """One-call convenience for the conveyancing report paths: load verified
    standards, build inputs from report-shaped data, run the screen. Returns
    None whenever the screen cannot run — the caller renders "Not assessed".
    Never raises: a crashed screen must degrade to fail-visible, not abort a
    paid report."""
    try:
        standards = load_cdc_standards_from_url(db_url)
        if standards is None:
            return None
        return run_cdc_screen(standards, build_cdc_inputs(
            zone, lot_area_m2, heritage_items, heritage_hca,
            unique_overlays, covered_layers,
        ))
    except Exception as e:
        logger.warning("CDC screen failed — caller renders 'Not assessed': %s", e)
        return None
