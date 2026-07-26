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
from typing import Literal, Optional

from pydantic import BaseModel

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
    never as a silent pass."""

    zone_code: Optional[str] = None
    lot_area_m2: Optional[float] = None
    is_heritage: Optional[bool] = None
    flood_prone: Optional[bool] = None
    bushfire_prone: Optional[bool] = None
    acid_sulfate_class: Optional[int] = None
    complying_excluded: Optional[bool] = None       # ePlanning layer 92
    dual_occ_prohibited: Optional[bool] = None      # ePlanning layer 452
    dual_occ_epi_name: Optional[str] = None
    contaminated_lot_on_register: Optional[bool] = None
    contamination_within_500m: Optional[bool] = None
    mine_subsidence_district: Optional[bool] = None


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
            SELECT standard_type, numeric_value, applicable_zones, conditionality, ref_number
            FROM cdc_eligibility_standards
            WHERE code_name = %s AND manual_verified = TRUE
            """,
            (code_name,),
        )
        rows = {r[0]: {"numeric_value": r[1], "applicable_zones": r[2],
                       "conditionality": r[3], "ref_number": r[4]}
                for r in cur.fetchall()}
        cur.close()
    except Exception as e:
        logger.warning("CDC standards: query failed — screen unavailable, callers fail closed: %s", e)
        return None

    if any(t not in rows for t in _REQUIRED_STANDARDS):
        logger.warning(
            "CDC standards: no verified %s rows for %s — screen unavailable, callers fail closed",
            "/".join(t for t in _REQUIRED_STANDARDS if t not in rows), code_name,
        )
        return None

    candidate = {
        "eligible_zones": rows["eligible_zones"]["applicable_zones"],  # noqa: bracket-access — key guaranteed by guard above
        "min_lot_size": rows["min_lot_size"]["numeric_value"],  # noqa: bracket-access — key guaranteed by guard above
        "min_lot_conditionality": rows["min_lot_size"]["conditionality"],  # noqa: bracket-access — key guaranteed by guard above
        "acid_sulfate_max_class": None,
        "refs": {t: v["ref_number"] for t, v in rows.items()},  # noqa: bracket-access — key guaranteed by guard above
    }
    ass = rows.get("acid_sulfate_max_class")
    if ass and ass["numeric_value"] is not None:  # noqa: bracket-access — key guaranteed by guard above
        try:
            candidate["acid_sulfate_max_class"] = int(ass["numeric_value"])  # noqa: bracket-access — key guaranteed by guard above
        except (TypeError, ValueError):
            pass
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

    # 2. Lot size
    checks.append("Lot size")
    if inputs.lot_area_m2 is None:
        unchecked.append("lot size")
    elif inputs.lot_area_m2 < standards["min_lot_size"]:  # noqa: bracket-access — key guaranteed by guard above
        cond = standards.get("min_lot_conditionality")
        exclusions.append(CdcExclusion(
            reason=(
                f"Lot area {round(inputs.lot_area_m2):,} m² is below the "
                f"{standards['min_lot_size']:g} m² minimum"
                + (f" ({cond})" if cond else "")
            ),
            constraint="lot_size", severity="definite", source=_cite("min_lot_size"),
        ))

    # 3-5. Overlay exclusions (heritage / flood / bushfire)
    for field, label, constraint in (
        ("is_heritage", "Heritage", "heritage"),
        ("flood_prone", "Flood risk", "flood"),
        ("bushfire_prone", "Bushfire risk", "bushfire"),
    ):
        checks.append(label)
        value = getattr(inputs, field)
        if value is None:
            unchecked.append(label.lower())
        elif value:
            exclusions.append(CdcExclusion(
                reason=f"{label} constraint mapped on this land",
                constraint=constraint, severity="definite", source="NSW Planning Portal",
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

    # 8. Dual-occupancy prohibition — authoritative live layer.
    checks.append("Dual occupancy prohibition")
    if inputs.dual_occ_prohibited is None:
        unchecked.append("dual occupancy prohibition")
    elif inputs.dual_occ_prohibited:
        exclusions.append(CdcExclusion(
            reason="Dual occupancy development is prohibited on this land",
            constraint="dual_occ_prohibition", severity="definite",
            source=inputs.dual_occ_epi_name or "NSW ePlanning MapServer",
        ))

    # 9. Contamination — exclusion only when the LOT is on the register
    # ("significantly contaminated land" is on the Codes SEPP land-exclusion
    # list); a register site nearby is a warning, never an exclusion.
    checks.append("Contaminated land")
    if inputs.contaminated_lot_on_register is None and inputs.contamination_within_500m is None:
        unchecked.append("contaminated land")
    else:
        if inputs.contaminated_lot_on_register:
            exclusions.append(CdcExclusion(
                reason="Lot is on the EPA contaminated-land record (significantly contaminated land is excluded from complying development)",
                constraint="contamination", severity="definite",
                source="EPA Contaminated Land Record + SEPP (Exempt and Complying Development Codes) 2008",
            ))
        elif inputs.contamination_within_500m:
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
