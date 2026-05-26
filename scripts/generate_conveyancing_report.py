#!/usr/bin/env python3
"""
Generate a conveyancing planning disclosure report.

Data sources:
  1. NSW Planning Portal layerintersect — zone, height, FSR, lot size, acid sulfate,
     heritage, key sites, special provisions (SEPP), legislative clauses.
  2. PostGIS spatial_overlays — biodiversity, riparian, wetlands, landslide, flood.
     These are NOT in the portal layerintersect. They come from NSW ePlanning's
     Protection and Hazard ArcGIS services. Standard title/s10.7 searches return
     "contact council" or nothing for these layers.
  3. NSW ePlanning DA API — nearby development applications.

Usage:
    python scripts/generate_conveyancing_report.py \\
        --address "3 Flood St, Leichhardt NSW 2040" \\
        --output report.pdf

    # --lat / --lng are optional overrides; address geocoding is automatic.

Requires (local venv, NOT services/requirements.txt):
    pip install reportlab psycopg2-binary requests python-dotenv
"""

import argparse
import json
import math
import os
import re
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=project_root / ".env")

# DB helpers — pre-fetched before generate_pdf (no DB connection inside renderer)
sys.path.insert(0, str(Path(__file__).parent))
from conveyancing_db import fetch_dcp_setbacks, fetch_heritage_postgis, fetch_lep_clauses, interpret_sepp  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PORTAL_BASE = "https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi"
PORTAL_HEADERS = {
    "Origin": "https://www.planningportal.nsw.gov.au",
    "Referer": "https://www.planningportal.nsw.gov.au/",
    "User-Agent": "Mozilla/5.0",
}
DA_URL = "https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineDA"

# Acid sulfate class descriptions (Class 1 = highest risk, Class 5 = subaqueous)
ASS_DESCRIPTIONS = {
    "Class 1": "High risk — works within 500m of CLASS 1 land require acid sulfate soils management plan.",
    "Class 2": "Moderate risk — works within 1km require acid sulfate soils management plan.",
    "Class 3": "Lower risk — relevant if works drain or disturb below 5m AHD.",
    "Class 4": "Low risk — relevant if works drain below 1m AHD.",
    "Class 5": "Subaqueous — applies to tidal wetlands/waterways. Works may still require management plan.",
}

# Biodiversity significance note
BIO_NOTE = (
    "Biodiversity Sensitivity — any development application on this property will likely "
    "require a Biodiversity Development Assessment Report (BDAR) under the Biodiversity "
    "Conservation Act 2016. Cost: $15,000–$50,000+. Timeline impact: 4–12 months."
)

RIPARIAN_NOTE = (
    "Riparian Land — property adjoins or includes a waterway corridor. Development setbacks "
    "apply under the LEP and Water Management Act 2000. Check council's riparian mapping."
)

WETLANDS_NOTE = (
    "Wetlands — identified wetland area. Development highly restricted. "
    "State Environmental Planning Policy (Resilience and Hazards) 2021 applies."
)

LANDSLIDE_NOTE = (
    "Landslide Risk — earthworks, excavation and building work subject to geotechnical "
    "investigation requirements. Confirm with council's hazard mapping."
)

FLOOD_NOTE = (
    "Flood Planning Area — this property is within council's flood planning area. "
    "The flood planning level (minimum floor height for development) is set by council and confirmed "
    "via a Section 733 Certificate (order from council, ~$50–150). "
    "Flood insurance cost should be confirmed with a broker before exchange. "
    "Source: council flood mapping."
)

FORESHORE_NOTE = (
    "Foreshore Building Line — property is within a foreshore area subject to a mapped "
    "building line under the LEP. Development between the building line and the water is "
    "prohibited or severely restricted. Confirm exact building line position with Council "
    "before any development or purchase decision."
)

# Bushfire: BFPL category labels and construction implications
BUSHFIRE_CATEGORIES = {
    "Flame Zone": (
        "Flame Zone (most severe) — development other than minor alterations is generally "
        "prohibited. Any works require a Bushfire Attack Level (BAL) assessment. CDC is not "
        "available — all development requires a DA with bushfire assessment report. "
        "Asset Protection Zone (APZ) of up to 100 m required."
    ),
    "1": (
        "Bushfire Protection Level Category 1 — significant construction requirements under "
        "AS 3959. CDC may be restricted. BAL assessment and bushfire-compliant construction "
        "specification required for any DA. APZ setback requirements apply."
    ),
    "2": (
        "Bushfire Protection Level Category 2 — construction requirements under AS 3959. "
        "BAL assessment required for development applications. APZ setback may apply."
    ),
    "3": (
        "Bushfire Protection Level Category 3 — moderate risk. BAL assessment required. "
        "Construction standard determined by BAL rating from site assessment."
    ),
    "4": (
        "Bushfire Protection Level Category 4 — lowest mapped risk. BAL assessment "
        "advisable. Construction standard determined by site-specific BAL rating."
    ),
}
BUSHFIRE_NOTE_DEFAULT = (
    "Bushfire Prone Land — this property is mapped as bushfire prone. A Bushfire Attack "
    "Level (BAL) assessment is required before any development application. Construction "
    "must meet AS 3959 standards for the applicable BAL rating. CDC eligibility may be "
    "restricted. Source: NSW Rural Fire Service BFPL mapping."
)

ANEF_NOTE = (
    "Aircraft Noise Contour — this property falls within an Australian Noise Exposure "
    "Forecast (ANEF) contour. Under SEPP (Transport and Infrastructure) 2021 and AS 2021, "
    "residential development within ANEF contours may require acoustic attenuation design "
    "and an acoustic report from an accredited acoustic consultant. The specific restrictions "
    "depend on the contour value — obtain the ANEF value from the relevant airport authority "
    "and confirm development requirements with council or a qualified acoustic consultant. "
    "Source: NSW Government ArcGIS spatial overlay (ANEF mapping)."
)

TOD_NOTE = (
    "Transport Oriented Development (TOD) Precinct — this property is within a TOD "
    "precinct under SEPP (Housing) 2021. In accelerated precincts, height and density "
    "uplift above the base LEP controls is available for residential development. "
    "Confirm applicable uplift and precinct type with the current SEPP Housing maps."
)

COASTAL_LAND_APP_NOTE = (
    "Coastal Land Application Area — this property is within a mapped coastal management "
    "area under SEPP (Resilience and Hazards) 2021. Development consent may require a "
    "coastal management assessment. Source: NSW Government SEPP R&H 2021 mapping."
)
COASTAL_WETLANDS_NOTE = (
    "Coastal Wetlands — this property is within or adjacent to a mapped coastal wetland "
    "under SEPP (Resilience and Hazards) 2021. Development within the proximity area "
    "requires assessment of potential impacts on the wetland. Source: NSW SEPP R&H 2021."
)
LITTORAL_RAINFOREST_NOTE = (
    "Littoral Rainforest — this property is within or adjacent to mapped littoral "
    "rainforest under SEPP (Resilience and Hazards) 2021. Development may require "
    "ecological assessment. Source: NSW SEPP R&H 2021."
)
COASTAL_ENV_AREA_NOTE = (
    "Coastal Environment Area — this property is within a mapped coastal environment "
    "area under SEPP (Resilience and Hazards) 2021. Development must demonstrate it "
    "will not adversely impact the coastal environment. Source: NSW SEPP R&H 2021."
)
COASTAL_USE_AREA_NOTE = (
    "Coastal Use Area — this property is within a mapped coastal use area under SEPP "
    "(Resilience and Hazards) 2021. Development must maintain public access and amenity "
    "of the coast. Source: NSW SEPP R&H 2021."
)
FIRE_HISTORY_NOTE = (
    "NPWS Fire History — this property has been affected by recorded fire events. "
    "Historical fire frequency is an indicator of ongoing bushfire risk beyond the "
    "current BFPL mapping. Source: NSW NPWS Fire History dataset."
)

CLASSIFIED_ROAD_NOTE = (
    "Classified Road Frontage — a statutory minimum setback of 9 metres applies to any "
    "dwelling house or attached development on a boundary with a classified road "
    "(SEPP Housing 2021). This is a hard LEP/SEPP number, independent of the DCP. "
    "Applies to Parramatta Road, Pacific Highway, Victoria Road and other state roads."
)

# Land tax fallbacks — used only when DB is unreachable.
# Authoritative source: tax_thresholds table (migration 046).
_LT_FALLBACK = {
    "tax_year": 2025,
    "threshold_dollars": 1_075_000,
    "rate": 0.016,
    "base_amount_dollars": 100,
}

# Secondary dwelling SEPP fallbacks — used only when DB is unreachable.
# Authoritative source: housing_sepp_standards table (migration 045).
_SD_FALLBACK_MIN_LOT = 450
_SD_FALLBACK_ZONES = {"R1", "R2", "R3", "R4"}

# ZONE_PERMITTED lookup table intentionally removed.
# Permitted uses are LEP-specific and vary per council. Use the zone_full (objectives text)
# and legislation_url fields returned by the portal layerintersect call.
# Do NOT re-add a hardcoded lookup here — it will be wrong within months of any LEP amendment.

# EPI name substring (uppercase) → lga slug for dcp_setback_controls.
# Inner West is multi-council — suburb disambiguation returns marrickville/leichhardt/ashfield.
# All other entries return the slug directly.
# Add new LGAs here as DCP setback rows are confirmed in dcp_setback_controls.
ZONE_EPI_TO_LGA_SLUG: dict[str, str] = {
    "INNER WEST LOCAL ENVIRONMENTAL PLAN":           "inner_west",
    "CANTERBURY-BANKSTOWN LOCAL ENVIRONMENTAL PLAN": "canterbury_bankstown",
    "BLACKTOWN LOCAL ENVIRONMENTAL PLAN":            "blacktown",
    "CAMPBELLTOWN":                                  "campbelltown",
    "LIVERPOOL LOCAL ENVIRONMENTAL PLAN":            "liverpool",
    "HORNSBY LOCAL ENVIRONMENTAL PLAN":              "hornsby",
    "NORTHERN BEACHES LOCAL ENVIRONMENTAL PLAN":     "northern_beaches",
    "PENRITH LOCAL ENVIRONMENTAL PLAN":              "penrith",
    "WAVERLEY LOCAL ENVIRONMENTAL PLAN":             "waverley",
    "WOOLLAHRA LOCAL ENVIRONMENTAL PLAN":            "woollahra",
    "KU-RING-GAI LOCAL ENVIRONMENTAL PLAN":          "ku_ring_gai",
    # Parramatta and Cumberland: registry entries exist but setback rows not yet complete.
    # "PARRAMATTA LOCAL ENVIRONMENTAL PLAN":         "parramatta",
    # "CUMBERLAND LOCAL ENVIRONMENTAL PLAN":         "cumberland",
}

# Suburb → former-council slug (Inner West LGA post-2016 amalgamation).
# Used only when ZONE_EPI_TO_LGA_SLUG returns "inner_west".
SUBURB_TO_FORMER_COUNCIL: dict[str, str] = {
    # Marrickville precincts
    "marrickville": "marrickville", "sydenham": "marrickville", "tempe": "marrickville",
    "dulwich hill": "marrickville", "st peters": "marrickville", "newtown": "marrickville",
    "erskineville": "marrickville", "alexandria": "marrickville", "enmore": "marrickville",
    "stanmore": "marrickville", "petersham": "marrickville", "lewisham": "marrickville",
    "camperdown": "marrickville", "glebe": "marrickville",
    # Leichhardt precincts
    "leichhardt": "leichhardt", "annandale": "leichhardt", "balmain": "leichhardt",
    "rozelle": "leichhardt", "lilyfield": "leichhardt", "forest lodge": "leichhardt",
    "birchgrove": "leichhardt", "balmain east": "leichhardt",
    # Ashfield precincts
    "ashfield": "ashfield", "summer hill": "ashfield", "haberfield": "ashfield",
    "croydon": "ashfield", "croydon park": "ashfield",
}


CADASTRE_URL = (
    "https://maps.six.nsw.gov.au/arcgis/rest/services/public/"
    "NSW_Cadastre/MapServer/9/query"
)
STRATA_HUB_URL = "https://www.fairtrading.nsw.gov.au/housing-and-property/strata-living/strata-schemes-register"


def get_cadastral_info(lat: float, lng: float) -> dict:
    """
    Query NSW Cadastre (maps.six.nsw.gov.au) for the lot at lat/lng.

    Returns:
        is_strata        bool   — True if classsubtype=3 (SP lot) found within buffer
        strata_plan      str    — "SP56913" if strata confirmed, else None
        parent_has_strata bool  — True if any lot within buffer has hasstratum=2
        plan_label       str    — planlabel of primary lot (e.g. "DP605756")
        lot_number       str    — lotnumber of primary lot
    """
    try:
        import json as _json
        r = requests.get(
            CADASTRE_URL,
            params={
                "geometry": _json.dumps({"x": lng, "y": lat, "spatialReference": {"wkid": 4283}}),
                "geometryType": "esriGeometryPoint",
                "inSR": "4283",
                "distance": 20,
                "units": "esriSRUnit_Meter",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "plannumber,planlabel,lotnumber,classsubtype,hasstratum",
                "returnGeometry": "false",
                "f": "json",
            },
            timeout=10,
        )
        r.raise_for_status()
        features = r.json().get("features") or []
        attrs_list = [f["attributes"] for f in features]

        # classsubtype=3 = strata lot (SP plan)
        # classsubtype=4 = community title lot (CP plan) — treated same as strata
        # Also catch by planlabel prefix in case classsubtype differs across datasets
        sp_lots = [
            a for a in attrs_list
            if a.get("classsubtype") in (3, 4)
            or str(a.get("planlabel") or "").startswith(("SP", "CP"))
        ]
        parent_strata = any(a.get("hasstratum") == 2 for a in attrs_list)

        if sp_lots:
            plan = sp_lots[0].get("planlabel", "")
            plan_type = "community" if str(plan).startswith("CP") else "strata"
            return {
                "is_strata": True,
                "strata_plan": plan,
                "plan_type": plan_type,       # "strata" | "community"
                "parent_has_strata": True,
                "plan_label": plan,
                "lot_number": sp_lots[0].get("lotnumber"),
            }

        # No SP/CP lot, but parent DP has strata built on it — ambiguous
        if attrs_list:
            primary = attrs_list[0]
            return {
                "is_strata": False,
                "strata_plan": None,
                "plan_type": None,
                "parent_has_strata": parent_strata,
                "plan_label": primary.get("planlabel"),
                "lot_number": primary.get("lotnumber"),
            }
    except Exception as e:
        print(f"  [warn] cadastral query: {e}")

    return {
        "is_strata": False,
        "strata_plan": None,
        "plan_type": None,
        "parent_has_strata": False,
        "plan_label": None,
        "lot_number": None,
    }


def _addr_has_unit_prefix(address: str) -> bool:
    a = address.strip()
    return bool(
        re.match(r"^\d+\s*/\s*\d+", a)
        or re.match(r"^(Unit|U|Apt|Apartment|Flat|F|Suite|Level|Shop|Studio)\s+\w+", a, re.IGNORECASE)
    )


def detect_strata(address: str, lat: Optional[float] = None, lng: Optional[float] = None) -> dict:
    """
    Detect strata title using a two-signal approach:

    Signal A — NSW Cadastre (free, public):
      classsubtype=3 in buffer → strata lot confirmed, SP number returned.
      hasstratum=2 on parent DP → strata scheme exists on this parcel.

    Signal B — address format:
      "5/3 ...", "Unit N ...", "Apt N ..." → likely strata.

    Decision logic:
      classsubtype=3 found              → strata confirmed (cadastre)
      parent_has_strata=True + addr A   → strata confirmed (combined)
      parent_has_strata=True alone      → ambiguous — note in report
      addr A alone (no cadastre result) → strata likely (heuristic fallback)
    """
    addr_unit = _addr_has_unit_prefix(address)

    if lat is not None and lng is not None:
        cad = get_cadastral_info(lat, lng)

        # Definitive: SP/CP lot found in cadastre
        if cad["is_strata"]:
            return {
                "is_strata": True,
                "strata_plan": cad["strata_plan"],
                "plan_type": cad.get("plan_type", "strata"),
                "source": "cadastre",
                "parent_has_strata": True,
                "plan_label": cad["plan_label"],
            }

        # Combined: parent has strata AND address looks like a unit
        if cad["parent_has_strata"] and addr_unit:
            return {
                "is_strata": True,
                "strata_plan": None,
                "plan_type": "strata",
                "source": "cadastre+address",
                "parent_has_strata": True,
                "plan_label": cad["plan_label"],
            }

        # Parent has strata but no unit prefix — whole-building query by planner
        if cad["parent_has_strata"]:
            return {
                "is_strata": False,
                "strata_plan": None,
                "plan_type": None,
                "source": "cadastre",
                "parent_has_strata": True,
                "plan_label": cad["plan_label"],
            }

        # Torrens cadastre result + unit prefix — portal stripped the unit, address wins
        if cad["plan_label"] and addr_unit:
            return {
                "is_strata": True,
                "strata_plan": None,
                "plan_type": "strata_or_company",   # can't confirm SP vs company title
                "source": "cadastre+address",
                "parent_has_strata": False,
                "plan_label": cad["plan_label"],
            }

        # Torrens, no unit prefix — confirmed Torrens title
        if cad["plan_label"]:
            return {
                "is_strata": False,
                "strata_plan": None,
                "plan_type": None,
                "source": "cadastre",
                "parent_has_strata": False,
                "plan_label": cad["plan_label"],
            }

    # Fallback: address heuristic only — could be strata or company title
    return {
        "is_strata": addr_unit,
        "strata_plan": None,
        "plan_type": "strata_or_company" if addr_unit else None,
        "source": "address_heuristic",
        "parent_has_strata": False,
        "plan_label": None,
    }


def detect_former_council(address: str, zone_epi: str = "") -> Optional[str]:
    """Return lga slug for dcp_setback_controls, or None if LGA not yet onboarded.

    Looks up ZONE_EPI_TO_LGA_SLUG using the EPI name from the planning portal.
    - No match → None (LGA not yet onboarded for DCP setbacks)
    - Most LGAs → slug returned directly
    - Inner West → suburb disambiguation returns marrickville / leichhardt / ashfield

    Extend ZONE_EPI_TO_LGA_SLUG (not this function) when onboarding new LGAs.
    """
    epi_upper = zone_epi.upper()
    slug = None
    for epi_key, lga_slug in ZONE_EPI_TO_LGA_SLUG.items():
        if epi_key in epi_upper or epi_upper in epi_key:
            slug = lga_slug
            break
    if not slug:
        return None
    # Inner West: disambiguate to former-council precinct by suburb
    if slug == "inner_west":
        addr_lower = address.lower()
        for suburb in sorted(SUBURB_TO_FORMER_COUNCIL, key=len, reverse=True):
            if suburb in addr_lower:
                return SUBURB_TO_FORMER_COUNCIL[suburb]
        return None  # IW address but suburb not mapped — no setback data
    return slug



def calc_feasibility(controls: dict, valuation: dict, unique_overlays: list[dict],
                     is_strata: bool = False,
                     sepp_standards: Optional[dict] = None,
                     tax_config: Optional[dict] = None) -> list[dict]:
    """
    Answer the questions buyers actually ask their conveyancer.
    Returns list of {question, answer, flag (ok/warn/alert), basis}.

    sepp_standards: pre-loaded from housing_sepp_standards table. Keys:
        sd_min_lot (float), sd_zones (set[str]).
    tax_config: pre-loaded from tax_thresholds table. Keys:
        tax_year, threshold_dollars, rate, base_amount_dollars.
    Both fall back to hardcoded values if not provided or if DB was unreachable.
    """
    results = []
    lot_area = valuation.get("lot_area_m2")
    zone = (controls.get("zone") or "").split()[0].upper()
    has_heritage = bool(controls.get("heritage_items"))
    has_biodiversity = any(o["layer_type"] == "biodiversity" for o in unique_overlays)
    has_flood = any(o["layer_type"] == "flood" for o in unique_overlays)

    # 1. Secondary dwelling (granny flat)
    # Source: housing_sepp_standards table (migration 045), fallback to hardcoded.
    _sd = sepp_standards or {}
    _SD_MIN_LOT = _sd.get("sd_min_lot", _SD_FALLBACK_MIN_LOT)
    _SD_ZONES = _sd.get("sd_zones", _SD_FALLBACK_ZONES)
    if is_strata:
        results.append({
            "question": "Secondary dwelling (granny flat)",
            "answer": "Not applicable — strata lot",
            "flag": "warn",
            "basis": (
                "Secondary dwellings cannot be erected on strata lots. Any works to common property "
                "require a unanimous special resolution of the owners corporation. Strata Plan "
                "and by-laws govern permissible alterations."
            )
        })
    elif lot_area is not None:
        if zone in _SD_ZONES:
            if lot_area >= _SD_MIN_LOT:
                results.append({
                    "question": "Secondary dwelling (granny flat)",
                    "answer": "Likely permissible",
                    "flag": "ok",
                    "basis": (
                        f"Zone {zone} + lot area {round(lot_area):,} m² ≥ {_SD_MIN_LOT} m² minimum "
                        f"(SEPP Housing 2021, Cl 53). Subject to DCP setback and height controls. "
                        f"Some councils have excluded dual occupancy CDC — confirm DA vs CDC pathway."
                    )
                })
            else:
                results.append({
                    "question": "Secondary dwelling (granny flat)",
                    "answer": "Unlikely — lot too small",
                    "flag": "warn",
                    "basis": (
                        f"Lot area {round(lot_area):,} m² is below the {_SD_MIN_LOT} m² minimum "
                        f"(SEPP Housing 2021, Cl 53(1)(b)). Confirm current SEPP standards."
                    )
                })
        else:
            results.append({
                "question": "Secondary dwelling (granny flat)",
                "answer": "Zone check required",
                "flag": "warn",
                "basis": (
                    f"Zone {zone} — secondary dwelling permissibility depends on the specific LEP "
                    f"zone objectives and SEPP Housing 2021 zone eligibility. Confirm with council."
                )
            })

    # 2. Subdivision
    min_lot_str = controls.get("lot_size")
    if is_strata:
        results.append({
            "question": "Torrens title subdivision",
            "answer": "Not applicable — strata lot",
            "flag": "warn",
            "basis": (
                "Strata lots cannot be Torrens-title subdivided. Strata plan consolidation or "
                "stratum lot creation requires owners corporation resolution and Council approval."
            )
        })
    elif lot_area is not None and min_lot_str:
        try:
            min_lot = float(re.sub(r"[^\d.]", "", min_lot_str.strip().split("m")[0]))
            if lot_area >= min_lot * 2:
                results.append({
                    "question": "Torrens title subdivision",
                    "answer": "Potentially feasible",
                    "flag": "ok",
                    "basis": f"Lot area {round(lot_area):,} m² ≥ 2 × {round(min_lot):,} m² minimum. Subject to DA, DCP controls and Council assessment."
                })
            else:
                results.append({
                    "question": "Torrens title subdivision",
                    "answer": "Not feasible — lot too small",
                    "flag": "warn",
                    "basis": f"Lot area {round(lot_area):,} m² < 2 × {round(min_lot):,} m² LEP minimum."
                })
        except (ValueError, AttributeError):
            results.append({
                "question": "Torrens title subdivision",
                "answer": "Check with council",
                "flag": "warn",
                "basis": f"Minimum lot size value could not be parsed ({min_lot_str!r}). Confirm subdivision feasibility directly with council.",
            })

    # 3. CDC eligibility (exempt/complying — no DA required)
    if is_strata:
        results.append({
            "question": "Complying Development Certificate (CDC)",
            "answer": "Unit alterations only — strata by-laws apply",
            "flag": "warn",
            "basis": (
                "CDC for whole-dwelling works is not applicable to individual strata units. "
                "Internal alterations may proceed under SEPP (Housing) 2021 exempt development provisions, "
                "subject to the strata by-laws and owners corporation consent for any works affecting "
                "common property."
            )
        })
    elif zone in _SD_ZONES:  # SEPP Housing 2021 CDC zones — same zone set as secondary dwelling
        blockers = []
        if has_heritage:
            blockers.append("heritage listing")
        if has_biodiversity:
            blockers.append("biodiversity sensitivity overlay")
        if has_flood:
            blockers.append("flood planning area")
        if not blockers:
            results.append({
                "question": "Complying Development Certificate (CDC)",
                "answer": "Potentially eligible",
                "flag": "ok",
                "basis": "No heritage, biodiversity or flood constraints identified. CDC may be available for dwelling alterations and additions subject to SEPP (Housing) 2021 controls."
            })
        else:
            results.append({
                "question": "Complying Development Certificate (CDC)",
                "answer": f"Restricted — {', '.join(blockers)}",
                "flag": "alert",
                "basis": f"CDC eligibility affected by: {', '.join(blockers)}. Development will likely require a full DA."
            })
    else:
        results.append({
            "question": "Complying Development Certificate (CDC)",
            "answer": "Not applicable to this zone",
            "flag": "warn",
            "basis": f"Zone {zone} — CDC pathway applies to residential zones R1–R4."
        })

    # 4. Development potential (suppress for strata — whole-lot area × FSR is meaningless for a unit)
    headroom = calc_development_headroom(controls, valuation)
    if headroom.get("max_gfa_m2") and not is_strata:
        results.append({
            "question": "Development potential (max permissible GFA)",
            "answer": headroom["max_gfa_display"],
            "flag": "ok",
            "basis": f"Lot {headroom['lot_area_display']} × FSR {headroom['fsr_numeric']}:1. Existing improvements reduce available headroom — compare against current dwelling footprint."
        })

    # 5. Land tax (investment property)
    # Source: tax_thresholds table (migration 046), fallback to hardcoded.
    # Suppress for strata: VG returns whole-lot land value (building site), not unit value
    _lt = tax_config or _LT_FALLBACK
    lt_year = _lt["tax_year"]
    lt_threshold = _lt["threshold_dollars"]
    lt_rate = _lt["rate"]
    lt_base = _lt["base_amount_dollars"]

    lv = valuation.get("land_value")
    if lv and not is_strata:
        lv_int = int(lv)
        if lv_int > lt_threshold:
            annual_lt = lt_base + (lv_int - lt_threshold) * lt_rate
            results.append({
                "question": f"Land tax (investment, {lt_year} thresholds)",
                "answer": f"${round(annual_lt):,}/year",
                "flag": "warn",
                "basis": (
                    f"Land value ${lv_int:,} exceeds {lt_year} threshold ${lt_threshold:,}. "
                    f"${lt_base} + {lt_rate * 100:.1f}% × ${lv_int - lt_threshold:,} = ${round(annual_lt):,}/year. "
                    f"PPOR exempt. Investment property, trust, and company holdings are taxable. "
                    f"Verify current thresholds at revenue.nsw.gov.au."
                )
            })
        else:
            results.append({
                "question": f"Land tax (investment, {lt_year} thresholds)",
                "answer": "Below threshold — nil",
                "flag": "ok",
                "basis": (
                    f"Land value ${lv_int:,} is below {lt_year} threshold ${lt_threshold:,}. "
                    "No land tax payable on investment property. PPOR always exempt. "
                    "Verify current thresholds at revenue.nsw.gov.au."
                )
            })

    return results


def calc_development_headroom(controls: dict, valuation: dict) -> dict:
    """
    Calculate development potential from known data points.
    Returns a dict of calculated metrics with plain-English interpretations.
    """
    out = {}
    lot_area = valuation.get("lot_area_m2")
    fsr_str = controls.get("fsr")
    height_str = controls.get("height")
    min_lot_str = controls.get("lot_size")

    if lot_area:
        out["lot_area_m2"] = round(lot_area)
        out["lot_area_display"] = f"{round(lot_area):,} m²"

    if lot_area and fsr_str:
        try:
            # FSR may be "0.5:1" or "0.5" or "84" (sqm — rare)
            fsr_val = float(fsr_str.strip().split(":")[0]) if ":" in fsr_str else float(fsr_str.strip())
            if fsr_val < 10:  # ratio, not sqm
                max_gfa = lot_area * fsr_val
                out["max_gfa_m2"] = round(max_gfa)
                out["max_gfa_display"] = f"{round(max_gfa):,} m²"
                out["fsr_numeric"] = fsr_val
        except ValueError:
            pass

    if lot_area and min_lot_str:
        try:
            _clean = min_lot_str.strip().replace(",", "").replace(" ", "")
            min_lot = float(re.sub(r"[^\d.]", "", _clean.split("m")[0])) if _clean else 0
            if min_lot > 0 and lot_area >= min_lot * 2:
                out["subdivision_feasible"] = True
                out["subdivision_note"] = (
                    f"Lot area ({round(lot_area):,} m²) is ≥ 2× minimum lot size ({round(min_lot):,} m²). "
                    "Subdivision may be feasible subject to DA and detailed assessment."
                )
            else:
                out["subdivision_feasible"] = False
                out["subdivision_note"] = (
                    f"Lot area ({round(lot_area):,} m²) is less than 2× minimum lot size ({round(min_lot):,} m²). "
                    "Subdivision unlikely without variation."
                )
        except (ValueError, AttributeError):
            pass

    if valuation.get("land_value"):
        out["land_value"] = valuation["land_value"]
        base_date = valuation.get("val_base_date")
        out["land_value_display"] = (
            f"${valuation['land_value']:,} (as at {base_date})" if base_date
            else f"${valuation['land_value']:,}"
        )
        if lot_area and lot_area > 0:
            lv_per_m2 = valuation["land_value"] / lot_area
            out["land_value_per_m2"] = round(lv_per_m2)
            out["land_value_per_m2_display"] = f"${round(lv_per_m2):,}/m²"

    return out


# ---------------------------------------------------------------------------
# NSW Planning Portal — sync helpers
# ---------------------------------------------------------------------------

def _portal_get(endpoint: str, params: dict) -> dict | list | None:
    try:
        r = requests.get(
            f"{PORTAL_BASE}/{endpoint}",
            params=params,
            headers=PORTAL_HEADERS,
            timeout=20,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  [warn] portal {endpoint}: {e}")
        return None


def _epsg3857_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """Convert Web Mercator (EPSG:3857) metres to WGS84 lat/lng."""
    import math
    R = 6378137.0
    lng = x / R * (180.0 / math.pi)
    lat = (2.0 * math.atan(math.exp(y / R)) - math.pi / 2.0) * (180.0 / math.pi)
    return lat, lng


def resolve_address(address: str) -> tuple[Optional[int], Optional[float], Optional[float], Optional[str]]:
    """
    Single call that returns (prop_id, lat, lng, lot_wkt).

    Strategy:
      1. /address  → propId
      2. /lot      → EPSG:3857 rings → centroid (lat/lng) + WGS84 polygon WKT
    lot_wkt is a POLYGON WKT in EPSG:4326 for use in ST_Intersects queries.
    """
    data = _portal_get("address", {"a": address, "noOfRecords": 1})
    if not data or not isinstance(data, list):
        return None, None, None, None

    prop_id = data[0].get("propId")
    if not prop_id:
        return None, None, None, None

    lat, lng, lot_wkt = None, None, None
    try:
        lot_data = _portal_get("lot", {"propId": prop_id})
        if lot_data and isinstance(lot_data, list) and lot_data[0].get("geometry"):
            rings = lot_data[0]["geometry"].get("rings") or []
            if rings and rings[0]:
                ring = rings[0]
                cx = sum(p[0] for p in ring) / len(ring)
                cy = sum(p[1] for p in ring) / len(ring)
                lat, lng = _epsg3857_to_wgs84(cx, cy)
                # Convert outer ring to WGS84 for PostGIS polygon query
                wgs84_pts = [_epsg3857_to_wgs84(p[0], p[1]) for p in ring]
                coords_str = ", ".join(f"{pt[1]} {pt[0]}" for pt in wgs84_pts)
                lot_wkt = f"POLYGON(({coords_str}))"
    except Exception as e:
        print(f"  [warn] lot geometry: {e}")

    return prop_id, lat, lng, lot_wkt


# Keep these thin wrappers for any callers that use them directly
def geocode_address(address: str) -> Optional[tuple[float, float]]:
    _, lat, lng, _ = resolve_address(address)
    return (lat, lng) if lat and lng else None


def get_prop_id(address: str) -> Optional[int]:
    prop_id, _, _, _ = resolve_address(address)
    return prop_id


def get_raw_controls(prop_id: int) -> list[dict]:
    data = _portal_get("layerintersect", {"type": "property", "id": prop_id, "layers": "epi"})
    return data if isinstance(data, list) else []


def get_valuation(prop_id: int) -> dict:
    """
    NSW Valuation service — returns actual lot area (m²) and land value ($).
    Source: maps.six.nsw.gov.au (public, no auth).
    """
    try:
        r = requests.get(
            "https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer/5/query",
            params={
                "where": f"propid={prop_id}",
                "outFields": (
                    "propid,prop_area,address,"
                    "val1_lv,val1_bd,val2_lv,val2_bd,val3_lv,val3_bd,"
                    "val4_lv,val4_bd,val5_lv,val5_bd"
                ),
                "f": "json",
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        features = data.get("features", [])
        if features:
            attrs = features[0].get("attributes", {})
            area = attrs.get("prop_area")

            def _num(v):
                if v is None:
                    return None
                if isinstance(v, (int, float)):
                    return float(v)
                import re
                m = re.search(r"[\d,]+\.?\d*", str(v).replace(",", ""))
                return float(m.group().replace(",", "")) if m else None

            # Build 5-year history: val5 = oldest, val1 = most recent
            history = []
            for i in range(5, 0, -1):
                lv_i = _num(attrs.get(f"val{i}_lv"))
                bd_i = (attrs.get(f"val{i}_bd") or "").strip() or None
                if lv_i:
                    history.append({"year": bd_i or f"val{i}", "value": lv_i})

            lv = _num(attrs.get("val1_lv"))
            return {
                "lot_area_m2": _num(area),
                "land_value": lv,
                "val_base_date": (attrs.get("val1_bd") or "").strip() or None,
                "val_history": history,
            }
    except Exception as e:
        print(f"  [warn] valuation API: {e}")
    return {"lot_area_m2": None, "land_value": None, "val_base_date": None, "val_history": []}


def parse_controls(raw: list[dict]) -> dict:
    """
    Extract the fields a conveyancer cares about from layerintersect response.
    Searches all results per block, not just the first.
    """

    def find(results, *keys):
        for res in results:
            for k in keys:
                v = res.get(k)
                if v is not None and str(v).strip() not in ("", "None"):
                    return str(v)
        return None

    def find_all(results, *keys):
        vals = []
        for res in results:
            for k in keys:
                v = res.get(k)
                if v and str(v).strip() not in ("None", ""):
                    vals.append(str(v))
                    break
        return list(dict.fromkeys(vals))  # dedup preserving order

    out = {
        "zone": None, "zone_full": None, "zone_epi": None, "legislation_url": None,
        "height": None, "height_units": "m", "height_clause": None,
        "fsr": None, "fsr_clause": None,
        "lot_size": None, "lot_size_units": "m\u00b2", "lot_size_clause": None,
        "ass_class": None,
        "key_sites_clause": None,
        "heritage_items": [],
        "heritage_hca": [],    # conservation area entries (subset of heritage_items)
        "sepp_overlays": [],   # list of {"name": ..., "type": ...}
        "housing_sepp": False,
        "tod_area": False,
        "basix_zone": None,
        "riparian_epi": False,
        "flood_epi": False,
    }

    for block in raw:
        layer = block.get("layerName", "").lower()
        results = block.get("results", [])
        if not results:
            continue

        if "zoning" in layer or ("zone" in layer and "canopy" not in layer and "timezone" not in layer):
            out["zone"] = find(results, "Zone") or find(results, "title", "Value")
            out["zone_full"] = find(results, "Land Use")
            out["zone_epi"] = results[0].get("EPI Name", "")
            out["legislation_url"] = results[0].get("legislationUrl", "")

        elif "height of buildings" in layer or ("height" in layer and "canopy" not in layer):
            out["height"] = find(results, "Maximum Building Height", "Height", "title")
            out["height_units"] = results[0].get("Units", "m")
            out["height_clause"] = find(results, "Legislative Clause")

        elif "floor space" in layer or "fsr" in layer:
            out["fsr"] = find(results, "Floor Space Ratio", "FSR", "title")
            out["fsr_clause"] = find(results, "Legislative Clause")

        elif "lot size" in layer:
            out["lot_size"] = find(results, "Lot Size", "Minimum Lot Size", "title")
            out["lot_size_units"] = results[0].get("Units", "m\u00b2")
            out["lot_size_clause"] = find(results, "Legislative Clause")

        elif "acid sulfate" in layer:
            out["ass_class"] = find(results, "Class", "title")

        elif "key sites" in layer:
            out["key_sites_clause"] = find(results, "Legislative Clause", "Class", "Label")

        elif "heritage" in layer:
            items = find_all(results, "Heritage Item", "Heritage Significance", "title")
            out["heritage_items"].extend(items)
            # Tag conservation area entries for downstream distinction
            for r in results:
                significance = (r.get("Heritage Significance") or r.get("title") or "").lower()
                if "conservation area" in significance or "hca" in significance:
                    out.setdefault("heritage_hca", []).append(
                        r.get("Heritage Item") or r.get("title") or significance
                    )

        elif "riparian" in layer:
            out["riparian_epi"] = True

        elif "flood" in layer and "plain" not in layer:
            out["flood_epi"] = True

        elif "special provisions" in layer:
            for res in results:
                epi = res.get("EPI Name") or ""
                type_ = res.get("Type") or res.get("Class") or res.get("title") or ""
                label = res.get("Label") or ""
                if epi or type_:
                    out["sepp_overlays"].append({"name": epi, "type": type_, "label": label})
                if "housing" in epi.lower() or "housing" in type_.lower():
                    out["housing_sepp"] = True
                if "transport" in epi.lower() and "tod" in str(type_).lower():
                    out["tod_area"] = True
                if "basix" in epi.lower() or "climate" in str(type_).lower():
                    out["basix_zone"] = label or type_

    out["heritage_items"] = list(dict.fromkeys(out["heritage_items"]))
    return out


# ---------------------------------------------------------------------------
# PostGIS — unique overlays (NOT in portal layerintersect)
# ---------------------------------------------------------------------------

_CLIMATE_LAYERS = {"coastal_land_application", "coastal_wetlands", "littoral_rainforest",
                   "coastal_environment_area", "coastal_use_area", "fire_history"}
_CLIMATE_ENABLED = os.environ.get("CLIMATE_LAYERS_ENABLED", "false").lower() in ("1", "true", "yes")

POSTGIS_UNIQUE_LAYERS = {"biodiversity", "riparian", "wetlands", "landslide", "flood", "acid_sulfate", "lot_size", "bushfire", "anef"}
if _CLIMATE_ENABLED:
    POSTGIS_UNIQUE_LAYERS |= _CLIMATE_LAYERS

# Layers ingested globally (bbox or filter_mode='all') — one 'ALL' coverage row, no per-LGA rows.
# covered_layers for these is determined by the 'ALL' row, not per-LGA rows.
GLOBAL_INGEST_LAYERS = frozenset({"bushfire", "anef"} | (_CLIMATE_LAYERS if _CLIMATE_ENABLED else set()))
POSTGIS_NOTES = {
    "biodiversity": BIO_NOTE,
    "riparian": RIPARIAN_NOTE,
    "wetlands": WETLANDS_NOTE,
    "landslide": LANDSLIDE_NOTE,
    "flood": FLOOD_NOTE,
    "foreshore_building_line": FORESHORE_NOTE,
    "classified_road": CLASSIFIED_ROAD_NOTE,
    "bushfire": BUSHFIRE_NOTE_DEFAULT,
    "anef": ANEF_NOTE,
    "tod_precinct": TOD_NOTE,
    "coastal_land_application": COASTAL_LAND_APP_NOTE,
    "coastal_wetlands": COASTAL_WETLANDS_NOTE,
    "littoral_rainforest": LITTORAL_RAINFOREST_NOTE,
    "coastal_environment_area": COASTAL_ENV_AREA_NOTE,
    "coastal_use_area": COASTAL_USE_AREA_NOTE,
    "fire_history": FIRE_HISTORY_NOTE,
}


def get_unique_overlays(lat: float, lng: float, lot_wkt: Optional[str] = None) -> tuple[list[dict], set[str], dict[str, float]]:
    """
    Query PostGIS for overlays not (or unreliably) returned by the portal:
      - Environmental: biodiversity, riparian, wetlands, landslide, flood
      - LEP constraints: foreshore_building_line (point-in-polygon)
      - Statutory setback trigger: classified road within 30m of the property point

    When lot_wkt is provided (WGS84 POLYGON WKT), uses ST_Intersects against the full
    lot polygon so overlays covering only part of the lot are not missed. Falls back to
    ST_Contains on the centroid point when lot_wkt is unavailable.

    Returns (results, covered_layers, proximity_m) where proximity_m maps layer_type →
    nearest-feature distance in metres for layers that are covered but not intersecting.
    """
    db_url = os.getenv("DATABASE_URL") or (
        f"host={os.getenv('DB_HOST','localhost')} "
        f"dbname={os.getenv('DB_NAME','postgres')} "
        f"user={os.getenv('DB_USER','postgres')} "
        f"password={os.getenv('DB_PASSWORD','')} "
        f"port={os.getenv('DB_PORT','5432')}"
    )
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        # Environmental + foreshore: lot polygon intersection (preferred) or centroid fallback
        env_layers = POSTGIS_UNIQUE_LAYERS | {"foreshore_building_line"}
        placeholders = ", ".join(f"'{l}'" for l in env_layers)
        if lot_wkt:
            cur.execute(
                f"""
                SELECT layer_type, value, instrument_key, lga_name
                FROM spatial_overlays
                WHERE layer_type IN ({placeholders})
                  AND ST_Intersects(geom, ST_SetSRID(ST_GeomFromText(%s), 4326))
                ORDER BY layer_type
                """,
                (lot_wkt,),
            )
        else:
            cur.execute(
                f"""
                SELECT layer_type, value, instrument_key, lga_name
                FROM spatial_overlays
                WHERE layer_type IN ({placeholders})
                  AND ST_Contains(geom, ST_SetSRID(ST_Point(%s, %s), 4326))
                ORDER BY layer_type
                """,
                (lng, lat),
            )
        rows = cur.fetchall()
        # Dedup: overlapping polygons can return the same (layer_type, value, instrument) twice
        seen = set()
        results = []
        for r in rows:
            key = (r[0], r[1], r[2])
            if key not in seen:
                seen.add(key)
                results.append({"layer_type": r[0], "value": r[1], "instrument": r[2], "lga": r[3]})

        # Classified road: any land_reservation with "Classified Road" value within 30m
        # (property point may sit just inside the lot, road reservation is adjacent)
        cur.execute(
            """
            SELECT layer_type, value, instrument_key, lga_name
            FROM spatial_overlays
            WHERE layer_type = 'land_reservation'
              AND value ILIKE '%%Classified Road%%'
              AND ST_DWithin(
                    geom::geography,
                    ST_SetSRID(ST_Point(%s, %s), 4326)::geography,
                    30
              )
            LIMIT 1
            """,
            (lng, lat),
        )
        road_row = cur.fetchone()
        if road_row:
            results.append({
                "layer_type": "classified_road",
                "value": road_row[1],
                "instrument": road_row[2],
                "lga": road_row[3],
            })

        # TOD precincts — statewide, no LGA filter needed
        cur.execute(
            """
            SELECT layer_type, value, instrument_key, lga_name
            FROM spatial_overlays
            WHERE layer_type IN ('tod_precinct', 'tod_accelerated', 'tod_deferred')
              AND ST_Contains(geom, ST_SetSRID(ST_Point(%s, %s), 4326))
            ORDER BY layer_type
            """,
            (lng, lat),
        )
        tod_rows = cur.fetchall()
        for r in tod_rows:
            results.append({"layer_type": r[0], "value": r[1], "instrument": r[2], "lga": r[3]})

        # Additional Permitted Uses (APU) — LEP Schedule 1 site-specific permissions
        # Point-in-polygon: an APU polygon covers exactly the lots it applies to
        cur.execute(
            """
            SELECT layer_type, value, instrument_key, lga_name
            FROM spatial_overlays
            WHERE layer_type = 'additional_permitted_uses'
              AND ST_Contains(geom, ST_SetSRID(ST_Point(%s, %s), 4326))
            ORDER BY value
            """,
            (lng, lat),
        )
        apu_rows = cur.fetchall()
        for r in apu_rows:
            results.append({"layer_type": r[0], "value": r[1], "instrument": r[2], "lga": r[3]})

        # Key Sites — LEP Schedule 1 / site-specific clause designations
        # value = LAY_CLASS field, e.g. "Schedule 1, Clause 1 (1)" or "Clause 4.2A (a) Area 1"
        # instrument_key = LEP name, e.g. "Blacktown Local Environmental Plan 2015"
        cur.execute(
            """
            SELECT layer_type, value, instrument_key, lga_name
            FROM spatial_overlays
            WHERE layer_type = 'key_sites'
              AND ST_Contains(geom, ST_SetSRID(ST_Point(%s, %s), 4326))
            ORDER BY value
            """,
            (lng, lat),
        )
        for r in cur.fetchall():
            results.append({"layer_type": r[0], "value": r[1], "instrument": r[2], "lga": r[3]})

        # Which of the unique layers have ANY data for this LGA?
        # Used by callers to distinguish "clear" from "not mapped".
        if rows:
            lga_name = rows[0][3]  # lga_name from first result
        else:
            # Derive LGA from any overlay at this point
            cur.execute(
                "SELECT lga_name FROM spatial_overlays WHERE ST_Contains(geom, ST_SetSRID(ST_Point(%s, %s), 4326)) LIMIT 1",
                (lng, lat),
            )
            lga_row = cur.fetchone()
            lga_name = lga_row[0] if lga_row else None

        covered_layers: set[str] = set()
        if lga_name:
            # Per-LGA layers: only "covered" when the ingest actually produced rows (feature_count > 0).
            # feature_count=0 means the ingest ran but the LGA genuinely has no features for that
            # layer — or the layer doesn't have data for that council in the state ArcGIS service.
            # Either way, showing "Clear" would be misleading; we omit the row and show an unmapped note.
            cur.execute(
                """
                SELECT layer_type FROM spatial_overlays_coverage
                WHERE lga_name = %s AND feature_count > 0
                """,
                (lga_name,),
            )
            covered_layers = {r[0] for r in cur.fetchall()}

            # Global layers (bushfire, anef) are ingested statewide via bbox/all — a single 'ALL'
            # coverage row is written, not per-LGA rows. Include them if the global ingest ran.
            cur.execute(
                """
                SELECT layer_type FROM spatial_overlays_coverage
                WHERE lga_name = 'ALL' AND feature_count > 0
                """,
            )
            covered_layers |= {r[0] for r in cur.fetchall()}

            if not covered_layers:
                # Coverage table not yet populated (pre-migration data) — fall back to inferring
                # from spatial_overlays presence (original behaviour)
                all_checked = POSTGIS_UNIQUE_LAYERS | {"foreshore_building_line", "land_reservation", "key_sites", "additional_permitted_uses"}
                env_placeholders = ", ".join(f"'{l}'" for l in all_checked)
                cur.execute(
                    f"""
                    SELECT DISTINCT layer_type FROM spatial_overlays
                    WHERE layer_type IN ({env_placeholders})
                      AND lga_name = %s
                    LIMIT 20
                    """,
                    (lga_name,),
                )
                covered_layers = {r[0] for r in cur.fetchall()}

            # classified_road results are built from land_reservation rows; alias so flag() finds it
            if "land_reservation" in covered_layers:
                covered_layers.add("classified_road")

        # Proximity distances — for layers that are covered but not intersecting at this property,
        # find the nearest feature distance (metres). Helps distinguish "1.5km away" from "50m away".
        # Only queried for ecologically sensitive layers where proximity is actionable.
        PROXIMITY_LAYERS = frozenset({"biodiversity", "riparian", "wetlands", "landslide"})
        hit_types = {r["layer_type"] for r in results}
        proximity_m: dict[str, float] = {}
        prox_candidates = PROXIMITY_LAYERS & covered_layers - hit_types
        if prox_candidates and lga_name:
            ph = ", ".join(f"'{lt}'" for lt in prox_candidates)
            cur.execute(
                f"""
                SELECT layer_type,
                       MIN(ST_Distance(geom::geography,
                                       ST_SetSRID(ST_Point(%s, %s), 4326)::geography)) AS dist_m
                FROM spatial_overlays
                WHERE layer_type IN ({ph})
                  AND lga_name = %s
                GROUP BY layer_type
                """,
                (lng, lat, lga_name),
            )
            for row in cur.fetchall():
                proximity_m[row[0]] = round(row[1])

        cur.close()
        conn.close()
        return results, covered_layers, proximity_m
    except Exception as e:
        print(f"  [warn] PostGIS query: {e}")
        return [], set(), {}


# ---------------------------------------------------------------------------
# NSW ePlanning DA search
# ---------------------------------------------------------------------------

def _haversine_m(lat1, lng1, lat2, lng2) -> float:
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _normalise_council(lga_name: str) -> Optional[str]:
    # Keys match the LGA prefix as it appears in zone_epi (after stripping "Local Environmental Plan YYYY")
    MAP = {
        # Greater Sydney — amalgamated councils
        "inner west": "Inner West Council",
        "sydney": "Council of the City of Sydney",
        "city of sydney": "Council of the City of Sydney",
        "waverley": "Waverley Council",
        "woollahra": "Woollahra Municipal Council",
        "randwick": "Randwick City Council",
        "ku-ring-gai": "Ku-ring-gai Council",
        "northern beaches": "Northern Beaches Council",
        "warringah": "Northern Beaches Council",  # pre-amalgamation LEP prefix still used
        "manly": "Northern Beaches Council",
        "pittwater": "Northern Beaches Council",
        "bayside": "Bayside Council",
        "botany bay": "Bayside Council",
        "rockdale": "Bayside Council",
        "georges river": "Georges River Council",
        "hurstville": "Georges River Council",
        "kogarah": "Georges River Council",
        "canterbury-bankstown": "Canterbury-Bankstown Council",
        "canterbury": "Canterbury-Bankstown Council",
        "bankstown": "Canterbury-Bankstown Council",
        "north sydney": "North Sydney Council",
        "lane cove": "Lane Cove Municipal Council",
        "mosman": "Mosman Municipal Council",
        "hunters hill": "Hunters Hill Council",
        "ryde": "City of Ryde Council",
        "canada bay": "Canada Bay Council",
        "strathfield": "Strathfield Municipal Council",
        "burwood": "Burwood Council",
        "cumberland": "Cumberland Council",
        "auburn": "Cumberland Council",
        "holroyd": "Cumberland Council",
        "parramatta": "City of Parramatta Council",
        "city of parramatta": "City of Parramatta Council",
        "blacktown": "Blacktown City Council",
        "hornsby": "Hornsby Shire Council",
        "the hills": "The Hills Shire Council",
        "baulkham hills": "The Hills Shire Council",
        "hawkesbury": "Hawkesbury City Council",
        "penrith": "Penrith City Council",
        "blue mountains": "Blue Mountains City Council",
        "liverpool": "Liverpool City Council",
        "fairfield": "Fairfield City Council",
        "camden": "Camden Council",
        "campbelltown": "Campbelltown City Council",
        "sutherland": "Sutherland Shire Council",
        "wollondilly": "Wollondilly Shire Council",
        # Greater Sydney fringe
        "wingecarribee": "Wingecarribee Shire Council",
        # Hunter / Newcastle
        "newcastle": "Newcastle City Council",
        "city of newcastle": "Newcastle City Council",
        "lake macquarie": "Lake Macquarie City Council",
        "maitland": "Maitland City Council",
        "port stephens": "Port Stephens Council",
        "cessnock": "Cessnock City Council",
        "singleton": "Singleton Council",
        "muswellbrook": "Muswellbrook Shire Council",
        "upper hunter": "Upper Hunter Shire Council",
        "dungog": "Dungog Shire Council",
        # Illawarra / South Coast
        "wollongong": "Wollongong City Council",
        "city of wollongong": "Wollongong City Council",
        "shellharbour": "Shellharbour City Council",
        "kiama": "Kiama Municipal Council",
        "shoalhaven": "Shoalhaven City Council",
        "eurobodalla": "Eurobodalla Shire Council",
        "bega valley": "Bega Valley Shire Council",
        # Central Coast / Mid North Coast
        "central coast": "Central Coast Council",
        "wyong": "Central Coast Council",  # pre-amalgamation
        "gosford": "Central Coast Council",  # pre-amalgamation
        "port macquarie-hastings": "Port Macquarie-Hastings Council",
        "mid-coast": "MidCoast Council",
        "great lakes": "MidCoast Council",
        "gloucester": "MidCoast Council",
        "nambucca valley": "Nambucca Valley Council",
        "nambucca": "Nambucca Valley Council",
        "kempsey": "Kempsey Shire Council",
        "bellingen": "Bellingen Shire Council",
        # Northern NSW
        "coffs harbour": "Coffs Harbour City Council",
        "clarence valley": "Clarence Valley Council",
        "richmond valley": "Richmond Valley Council",
        "lismore": "Lismore City Council",
        "ballina": "Ballina Shire Council",
        "byron": "Byron Shire Council",
        "kyogle": "Kyogle Council",
        "tweed": "Tweed Shire Council",
        "glen innes severn": "Glen Innes Severn Council",
        "inverell": "Inverell Shire Council",
        "moree plains": "Moree Plains Shire Council",
        "narrabri": "Narrabri Shire Council",
        "gwydir": "Gwydir Shire Council",
        # New England / Northwest
        "tamworth regional": "Tamworth Regional Council",
        "tamworth": "Tamworth Regional Council",
        "armidale": "Armidale Regional Council",
        "armidale regional": "Armidale Regional Council",
        "uralla": "Uralla Shire Council",
        "walcha": "Walcha Council",
        "tenterfield": "Tenterfield Shire Council",
        # Western / Far West
        "dubbo regional": "Dubbo Regional Council",
        "dubbo": "Dubbo Regional Council",
        "orange": "Orange City Council",
        "bathurst regional": "Bathurst Regional Council",
        "bathurst": "Bathurst Regional Council",
        "lithgow": "Lithgow City Council",
        "cabonne": "Cabonne Shire Council",
        "blayney": "Blayney Shire Council",
        "oberon": "Oberon Council",
        "mid-western regional": "Mid-Western Regional Council",
        "mid-western": "Mid-Western Regional Council",
        "cowra": "Cowra Shire Council",
        "forbes": "Forbes Shire Council",
        "lachlan": "Lachlan Shire Council",
        "parkes": "Parkes Shire Council",
        "narromine": "Narromine Shire Council",
        "gilgandra": "Gilgandra Shire Council",
        "warren": "Warren Shire Council",
        "coonamble": "Coonamble Shire Council",
        "walgett": "Walgett Shire Council",
        "brewarrina": "Brewarrina Shire Council",
        "bourke": "Bourke Shire Council",
        "bogan": "Bogan Shire Council",
        "cobar": "Cobar Shire Council",
        "broken hill": "City of Broken Hill",
        "central darling": "Central Darling Shire Council",
        "unincorporated far west": None,  # no council
        # Riverina / Murray
        "wagga wagga": "Wagga Wagga City Council",
        "griffith": "Griffith City Council",
        "murrumbidgee": "Murrumbidgee Council",
        "narrandera": "Narrandera Shire Council",
        "leeton": "Leeton Shire Council",
        "coolamon": "Coolamon Shire Council",
        "junee": "Junee Shire Council",
        "temora": "Temora Shire Council",
        "cootamundra-gundagai regional": "Cootamundra-Gundagai Regional Council",
        "cootamundra-gundagai": "Cootamundra-Gundagai Regional Council",
        "snowy valleys": "Snowy Valleys Council",
        "tumut": "Snowy Valleys Council",
        "tumbarumba": "Snowy Valleys Council",
        "hilltops": "Hilltops Council",
        "young": "Hilltops Council",
        "harden": "Hilltops Council",
        "boorowa": "Hilltops Council",
        "hay": "Hay Shire Council",
        "edward river": "Edward River Council",
        "deniliquin": "Edward River Council",
        "murray river": "Murray River Council",
        "murray": "Murray River Council",
        "berrigan": "Berrigan Shire Council",
        "federation": "Federation Council",
        "corowa": "Federation Council",
        "urana": "Federation Council",
        "greater hume": "Greater Hume Shire Council",
        "greater hume shire": "Greater Hume Shire Council",
        "albury": "Albury City Council",
        "snowy monaro regional": "Snowy Monaro Regional Council",
        "snowy monaro": "Snowy Monaro Regional Council",
        "cooma-monaro": "Snowy Monaro Regional Council",
        "bombala": "Snowy Monaro Regional Council",
        "queanbeyan-palerang regional": "Queanbeyan-Palerang Regional Council",
        "queanbeyan-palerang": "Queanbeyan-Palerang Regional Council",
        "queanbeyan": "Queanbeyan-Palerang Regional Council",
        "palerang": "Queanbeyan-Palerang Regional Council",
        "yass valley": "Yass Valley Council",
        "upper lachlan": "Upper Lachlan Shire Council",
        "goulburn mulwaree": "Goulburn Mulwaree Council",
        # ACT border / South
        "capital region": None,  # not a NSW council
    }
    key = lga_name.lower()
    if key in MAP:
        return MAP[key]
    print(f"  [warn] council name not mapped: {lga_name!r} — DA search skipped")
    return None


def _council_from_zone_epi(zone_epi: str) -> Optional[str]:
    """Derive council name from LEP EPI name, e.g. 'Ku-ring-gai Local Environmental Plan 2015' → 'Ku-ring-gai Council'."""
    if not zone_epi:
        return None
    # Strip the " Local Environmental Plan YYYY" suffix
    lga = re.sub(r"\s+Local Environmental Plan\s+\d{4}.*", "", zone_epi, flags=re.IGNORECASE).strip()
    if not lga:
        return None
    return _normalise_council(lga)


def get_nearby_das(lat: float, lng: float, council_name: Optional[str],
                   radius_m: int = 200, days: int = 365) -> list[dict]:
    """Fetch nearby DAs. council_name must already be normalised (use _normalise_council before calling)."""
    since = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    filters_header = json.dumps({
        "filters": {"CouncilName": [council_name], "LodgementDateFrom": since}
    })
    try:
        apps: list[dict] = []
        page = 1
        page_size = 200
        while True:
            r = requests.get(
                DA_URL,
                headers={
                    "filters": filters_header,
                    "PageSize": str(page_size),
                    "PageNumber": str(page),
                    "Cache-Control": "no-cache",
                },
                timeout=25,
            )
            r.raise_for_status()
            body = r.json()
            batch = body.get("Application") or []
            apps.extend(batch)
            total = int(body.get("TotalCount") or r.headers.get("TotalCount") or 0)
            if len(apps) >= total or len(batch) < page_size:
                break
            page += 1
            if page > 10:   # safety cap — 2,000 DAs max per council per year
                break
    except Exception as e:
        print(f"  [warn] DA API: {e}")
        return []

    nearby = []
    for app in apps:
        # Coordinates are inside Location[0].X / Location[0].Y, not top-level fields
        location = app.get("Location")
        loc0 = (location[0] if isinstance(location, list) and location else {})
        app_lat = loc0.get("Y") or app.get("CoordinatesY")
        app_lng = loc0.get("X") or app.get("CoordinatesX")
        address = loc0.get("FullAddress") or (str(location) if location else "")
        if app_lat and app_lng:
            dist = _haversine_m(lat, lng, float(app_lat), float(app_lng))
            if dist <= radius_m:
                nearby.append({
                    "number": app.get("PlanningPortalApplicationNumber") or "",
                    "address": address,
                    "description": ", ".join(
                        (dt.get("DevelopmentType") or "") for dt in (app.get("DevelopmentType") or [])
                    )[:120],
                    "status": app.get("ApplicationStatus") or "",
                    "lodged": (app.get("LodgementDate") or "")[:10],
                    "distance_m": round(dist),
                })
    nearby.sort(key=lambda x: x["distance_m"])
    return nearby[:10]


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

def get_shadow_risk(
    address: str,
    prop_id: int,
    lat: float,
    lng: float,
    height_m: Optional[float] = None,
) -> Optional[dict]:
    """
    Call the Railway shadow pipeline.
    height_m: pass the LEP height already fetched from Planning Portal so
    Railway doesn't need to re-query (avoids spatial_overlays coverage gaps).
    Returns the `outputs` dict on success, None if Railway unreachable or call fails.
    Graceful degradation — shadow section is omitted rather than crashing the report.
    """
    api_url = os.environ.get("PYTHON_API_URL", "http://localhost:8000")
    payload = {
        "address": address,
        "prop_id": str(prop_id),
        "lat": lat,
        "lng": lng,
        "report_id": str(uuid.uuid4()),
    }
    if height_m:
        payload["height_m"] = height_m
    try:
        r = requests.post(f"{api_url}/pipeline/shadow", json=payload, timeout=60)
        r.raise_for_status()
        return r.json().get("outputs")
    except Exception as e:
        print(f"  [warn] Shadow pipeline unavailable — section will be omitted: {e}")
        return None


def _check_reportlab():
    try:
        import reportlab  # noqa
    except ImportError:
        print("ERROR: reportlab not installed — run: pip install reportlab")
        sys.exit(1)


def _flag_cell(text: str, style_name: str, styles_map: dict):
    from reportlab.platypus import Paragraph
    return Paragraph(text, styles_map[style_name])


def generate_pdf(
    output_path: str,
    address: str,
    lat: float,
    lng: float,
    controls: dict,
    valuation: dict,
    headroom: dict,
    feasibility: list[dict],
    unique_overlays: list[dict],
    das: list[dict],
    dcp_former_council: Optional[str] = None,
    strata_info: Optional[dict] = None,
    covered_layers: Optional[set] = None,
    shadow_result: Optional[dict] = None,
    lep_clauses: Optional[list] = None,
    dcp_setbacks_db: Optional[dict] = None,
    proximity_m: Optional[dict] = None,
):
    _check_reportlab()

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable, PageBreak, Paragraph, SimpleDocTemplate,
        Spacer, Table, TableStyle,
    )

    W, _H = A4
    MARGIN = 18 * mm

    INK      = colors.HexColor("#0F172A")   # near-black for body text / headings
    NAVY     = INK                           # alias kept for callout boxes
    TEAL     = colors.HexColor("#0D7A6B")   # primary brand accent
    TEAL_DK  = colors.HexColor("#085F54")   # darker teal for table headers
    GREEN_BG = colors.HexColor("#F0FDF4")   # light green row tint
    AMBER    = colors.HexColor("#D97706")
    AMBER_BG = colors.HexColor("#FFFBEB")   # light amber row tint
    RED      = colors.HexColor("#B91C1C")
    RED_BG   = colors.HexColor("#FEF2F2")   # light red row tint
    GREEN    = colors.HexColor("#166534")
    LGREY    = colors.HexColor("#F3F4F6")
    MGREY    = colors.HexColor("#9CA3AF")
    BORDER   = colors.HexColor("#CBD5E1")   # subtle divider lines
    WHITE    = colors.white

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=22 * mm,
    )
    styles = getSampleStyleSheet()

    def S(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    ss = {
        "title":    S("t",  fontSize=20, textColor=WHITE, leading=26, fontName="Helvetica-Bold"),
        "addr":     S("a",  fontSize=10, textColor=colors.HexColor("#CBD5E1"), leading=15),
        "meta":     S("m",  fontSize=8,  textColor=MGREY, leading=12),
        "h2":       S("h2", fontSize=12, textColor=INK, leading=17, fontName="Helvetica-Bold", spaceBefore=6),
        "body":     S("bd", fontSize=9,  textColor=colors.HexColor("#374151"), leading=13),
        "note":     S("nt", fontSize=8,  textColor=colors.HexColor("#6B7280"), leading=12, leftIndent=4),
        "ok":       S("ok", fontSize=9,  textColor=GREEN, fontName="Helvetica-Bold", leading=13),
        "warn":     S("wn", fontSize=9,  textColor=AMBER, fontName="Helvetica-Bold", leading=13),
        "alert":    S("al", fontSize=9,  textColor=RED,   fontName="Helvetica-Bold", leading=13),
        "caveat":   S("cv", fontSize=8,  textColor=MGREY, leading=12),
    }

    story = []
    CW = W - 2 * MARGIN  # content width

    def hr():
        story.append(HRFlowable(width="100%", thickness=0.8, color=TEAL))

    def h2(text):
        story.append(Spacer(1, 5 * mm))
        accent = Table(
            [[Paragraph(text, ss["h2"])]],
            colWidths=[CW],
        )
        accent.setStyle(TableStyle([
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBEFORE",    (0, 0), (0, -1),  3, TEAL),
            ("LINEBELOW",     (0, -1), (-1, -1), 0.4, BORDER),
        ]))
        story.append(accent)
        story.append(Spacer(1, 3 * mm))

    def table(rows, col_widths, header_bg=TEAL_DK, row_statuses=None):
        """
        Build a styled table.
        row_statuses: list of ('ok'|'warn'|'alert'|None) per data row (index 0 = first data row).
        """
        t = Table(rows, colWidths=col_widths)
        cmds = [
            ("BACKGROUND",    (0, 0), (-1, 0),  header_bg),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LGREY]),
            ("GRID",          (0, 0), (-1, -1), 0.3, BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]
        if row_statuses:
            _bg_map = {"ok": GREEN_BG, "warn": AMBER_BG, "alert": RED_BG}
            for i, status in enumerate(row_statuses):
                if status and status in _bg_map:
                    cmds.append(("BACKGROUND", (0, i + 1), (-1, i + 1), _bg_map[status]))
        t.setStyle(TableStyle(cmds))
        return t

    # ------------------------------------------------------------------
    # COVER PAGE
    # ------------------------------------------------------------------
    cover_hdr = Table(
        [
            [Paragraph("PLANNING DISCLOSURE REPORT", ss["title"])],
            [Paragraph(address, ss["addr"])],
            [Spacer(1, 2 * mm)],
            [Paragraph(
                f"Prepared {date.today().strftime('%d %B %Y')}  ·  "
                f"PlotDetect NSW Property Intelligence",
                S("cmeta", fontSize=8, textColor=colors.HexColor("#A7C4BC"), leading=12),
            )],
        ],
        colWidths=[CW],
    )
    cover_hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), TEAL),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
    ]))
    story.append(cover_hdr)
    story.append(Spacer(1, 5 * mm))

    # 4-card summary row: Zone / Lot Area / Land Value / Constraints
    _zone_val  = controls.get("zone") or "—"
    _area_val  = (
        f"{int(valuation['lot_area_m2']):,} m²"
        if valuation.get("lot_area_m2") else "—"
    )
    _lv_val    = (
        f"${int(valuation['land_value']):,}"
        if valuation.get("land_value") else "—"
    )
    # Count unique constraint types — use layer_type set to avoid double-counting
    # (heritage is portal-sourced; PostGIS heritage row unlikely but guard against it)
    _constraint_layer_types = {o["layer_type"] for o in unique_overlays
                                if o["layer_type"] in ("biodiversity", "riparian", "wetlands",
                                   "landslide", "flood", "bushfire", "anef")}
    _n_constraints = len(_constraint_layer_types)
    if controls.get("heritage_items"):
        _n_constraints += 1
    if controls.get("ass_class"):
        _n_constraints += 1
    _constr_val = str(_n_constraints) if _n_constraints else "None"
    _constr_hex = "#B91C1C" if _n_constraints else "#166534"

    _card_label = S("cl", fontSize=7.5, textColor=MGREY, leading=10, fontName="Helvetica-Bold")
    _card_val   = S("cv2", fontSize=14, textColor=INK, leading=18, fontName="Helvetica-Bold")

    def _card(label, value, val_hex="#0F172A"):
        # Two rows: label on top, value below — each in its own row
        return [
            [Paragraph(label.upper(), _card_label)],
            [Paragraph(f"<font color='{val_hex}'>{value}</font>", _card_val)],
        ]

    _card_w = CW / 4
    cards_tbl = Table(
        [[
            Table(_card("Zone", _zone_val),              colWidths=[_card_w - 4]),
            Table(_card("Lot Area", _area_val),          colWidths=[_card_w - 4]),
            Table(_card("Land Value", _lv_val),          colWidths=[_card_w - 4]),
            Table(_card("Constraints", _constr_val, _constr_hex), colWidths=[_card_w - 4]),
        ]],
        colWidths=[_card_w, _card_w, _card_w, _card_w],
    )
    cards_tbl.setStyle(TableStyle([
        ("BOX",          (0, 0), (-1, -1), 0.5, BORDER),
        ("LINEBEFORE",   (1, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("BACKGROUND",   (0, 0), (-1, -1), WHITE),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(cards_tbl)
    if valuation.get("land_value") and valuation.get("val_base_date"):
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            f"Land value as at {valuation['val_base_date']} (NSW Valuer General — updated annually, "
            f"typically published 6–12 months after base date). Current market value may differ materially.",
            ss["caveat"],
        ))
    story.append(Spacer(1, 6 * mm))

    # ------------------------------------------------------------------
    # s10.7 DELTA CALLOUT — what this report surfaces that standard
    # searches do NOT disclose
    # ------------------------------------------------------------------
    unique_by_type = {o["layer_type"]: o for o in unique_overlays}

    # Flood: collect ALL scenarios (multiple rows per property), build range label.
    # Value formats in spatial_overlays:
    #   "100AEP"            -- Hawkesbury ARI-based: number is ARI in years
    #   "1.0%AEP"           -- Campbelltown AEP%-based: number is annual exceedance probability %
    #   "PMF"               -- Probable Maximum Flood
    #   "Flood Planning Area" -- binary designation (no return period); treat as generic
    def _parse_ari(scenario_key: str) -> float:
        import re as _re
        if "pmf" in str(scenario_key).lower():
            return 999999.0
        # AEP%-based: "1.0%AEP", "0.2%AEP" -- ARI = 100 / AEP%
        m = _re.match(r"^(\d+(?:\.\d+)?)%AEP$", str(scenario_key), _re.IGNORECASE)
        if m:
            pct = float(m.group(1))
            return round(100.0 / pct, 1) if pct > 0 else 999999.0
        # ARI-based: "100AEP" -- number is already ARI in years
        m = _re.match(r"^(\d+(?:\.\d+)?)AEP$", str(scenario_key), _re.IGNORECASE)
        if m:
            return float(m.group(1))
        # Non-numeric designation (e.g. "Flood Planning Area") — return None to signal generic
        return None  # type: ignore[return-value]

    def _ari_str(ari: float) -> str:
        return str(int(ari)) if ari == int(ari) else f"{ari:.1f}"

    _flood_rows = [o for o in unique_overlays if o["layer_type"] == "flood"]
    # Separate ARI-quantified rows from generic binary designations
    _ari_rows = sorted(
        [o for o in _flood_rows if _parse_ari(o["value"]) is not None],
        key=lambda o: _parse_ari(o["value"]),
    )
    _generic_flood_rows = [o for o in _flood_rows if _parse_ari(o["value"]) is None]
    _flood_note_dynamic: str | None = None
    if _flood_rows:
        _instrument = _flood_rows[0].get("instrument") or ""
        _is_hnrfs = "HNRFS_2024" in _instrument
        _is_ctfs = "CTFS_2023" in _instrument
        _source_citation = (
            "2024 Hawkesbury-Nepean River Flood Study, NSW SES/INSW (May 2024) — data.nsw.gov.au"
            if _is_hnrfs
            else "Campbelltown Flood Study 2023, NSW SES — flooddata.ses.nsw.gov.au"
            if _is_ctfs
            else "council flood mapping"
        )
        _base_action = (
            "The flood planning level (minimum floor height for any future development or renovation) "
            "is set by council — it is NOT stated in this report. "
            "Order a Section 733 Certificate from council (~$50–150) to confirm the applicable "
            "flood planning level. Check flood insurance cost with a broker before exchange — "
            "premiums in flood-affected areas can be substantial."
        )

        if _ari_rows:
            # High-precision path: ARI/AEP scenarios available
            _has_pmf = any("pmf" in str(o["value"]).lower() for o in _ari_rows)
            _n = len(_ari_rows) + len(_generic_flood_rows)
            _min_ari = _parse_ari(_ari_rows[0]["value"])
            if _has_pmf:
                _flood_display = f"1-in-{_ari_str(_min_ari)}-year flood extent through to PMF ({_n} scenarios)"
            else:
                _max_ari = _parse_ari(_ari_rows[-1]["value"])
                _flood_display = f"1-in-{_ari_str(_min_ari)}-year through to 1-in-{_ari_str(_max_ari)}-year flood extent ({_n} scenarios)"
            unique_by_type["flood"]["value"] = _flood_display

            _pmf_suffix = " through to PMF" if _has_pmf else f" through to the 1-in-{_ari_str(_parse_ari(_ari_rows[-1]['value']))}-year extent"
            _pmf_explanation = (
                " PMF (Probable Maximum Flood) is the theoretical upper physical limit of flooding — "
                "the result of the most extreme meteorological conditions possible. "
                "It carries no return period; it is used for emergency management and represents "
                "the absolute worst-case inundation extent."
                if _has_pmf else ""
            )
            _flood_note_dynamic = (
                f"Flood Planning Area — this property is within the 1-in-{_ari_str(_min_ari)}-year flood extent"
                f"{_pmf_suffix}.{_pmf_explanation} "
                f"Source: {_source_citation}. {_base_action}"
            )
        else:
            # Generic path: council designates flood affectation without return period detail
            _flood_display = "Flood Planning Area"
            unique_by_type["flood"]["value"] = _flood_display
            _flood_note_dynamic = (
                f"Flood Planning Area — this property is within the council's flood planning area. "
                f"The specific return period (1-in-X-year extent) is not published in the state mapping layer for this council. "
                f"Source: {_source_citation}. {_base_action}"
            )

    # Bushfire — use category-specific note if category value is available
    _bushfire_note_dynamic: str | None = None
    if "bushfire" in unique_by_type:
        _bf_val = (unique_by_type["bushfire"].get("value") or "").strip()
        # Normalise: "Category 1" → "1", "CAT 2" → "2", "Flame Zone" stays as-is
        _bf_key = re.sub(r"(?i)^cat(?:egory)?\s*", "", _bf_val).strip()
        _bf_specific = BUSHFIRE_CATEGORIES.get(_bf_key) or BUSHFIRE_CATEGORIES.get(_bf_val)
        if _bf_specific:
            _bushfire_note_dynamic = _bf_specific
        # else fall back to BUSHFIRE_NOTE_DEFAULT (via static POSTGIS_NOTES entry)

    DELTA_CHECKS = [
        ("Biodiversity Values Map (BDAR trigger)", "biodiversity"),
        ("Riparian Land",            "riparian"),
        ("Wetlands",                 "wetlands"),
        ("Landslide Risk",           "landslide"),
        ("Flood Planning Area",      "flood"),
        ("Bushfire Prone Land",      "bushfire"),
        ("Aircraft Noise (ANEF)",    "anef"),
        ("Key Site (LEP clause)",    "key_sites"),
        ("TOD Development Uplift",   "tod_accelerated"),  # catches accelerated first; tod_precinct/tod_deferred checked separately
        ("Additional Permitted Uses","additional_permitted_uses"),
        ("DCP Setbacks (with clause citations)", None),
    ]
    _tod_hit = any(t in unique_by_type for t in ("tod_accelerated", "tod_precinct", "tod_deferred"))
    _apu_hit = any(o["layer_type"] == "additional_permitted_uses" for o in unique_overlays)

    def _delta_hit(lt: Optional[str]) -> bool:
        if lt is None:
            return False
        if lt == "tod_accelerated":   # proxy for any TOD type
            return _tod_hit
        if lt == "additional_permitted_uses":
            return _apu_hit
        return lt in unique_by_type

    flagged = [label for label, lt in DELTA_CHECKS if _delta_hit(lt)]
    delta_lines = []
    for label, lt in DELTA_CHECKS:
        if _delta_hit(lt):
            delta_lines.append(f"<b>▲ {label}</b>")
        else:
            delta_lines.append(label)
    delta_body_text = "  ·  ".join(delta_lines)

    callout_header = Paragraph(
        "The following are NOT disclosed in a standard s10.7(2) certificate or title search "
        "— this report checks all of them:",
        S("ch", fontSize=9, textColor=WHITE, fontName="Helvetica-Bold", leading=13),
    )
    alert_suffix = (
        f"  <b>{len(flagged)} constraint(s) identified at this property — see Risk Summary.</b>"
        if flagged else "  No constraints identified for this property."
    )
    callout_body = Paragraph(
        delta_body_text + alert_suffix,
        S("cb", fontSize=8, textColor=colors.HexColor("#134E4A"), leading=12),
    )
    callout_tbl = Table([[callout_header], [callout_body]], colWidths=[CW])
    callout_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  TEAL),
        ("BACKGROUND",    (0, 1), (-1, -1), colors.HexColor("#F0FDF9")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("BOX",           (0, 0), (-1, -1), 0.5, TEAL),
    ]))
    story.append(callout_tbl)
    story.append(Spacer(1, 5 * mm))

    # ------------------------------------------------------------------
    # COVERAGE PANEL
    # ------------------------------------------------------------------
    if dcp_setbacks_db:
        dcp_note = dcp_setbacks_db["dcp_name"]
    elif dcp_former_council:
        # DB fetch succeeded during main() but was not passed in — fallback
        dcp_note = dcp_former_council.replace("_", " ").title() + " DCP controls"
    else:
        dcp_note = "DCP setback controls: contact council for your LGA"

    included_items = [
        "Zone, height limit, FSR, minimum lot size — all 128 NSW councils",
        "Heritage listing: individual items and conservation areas (distinguished)",
        "Acid sulfate soils classification",
        "SEPP overlays (spatial footprint + statewide applicability)",
        "Environmental constraints: biodiversity, riparian, wetlands, landslide, flood",
        "Bushfire Prone Land (BFPL) + BAL category where available",
        "Aircraft Noise Exposure Forecast (ANEF) contour",
        "TOD precinct status (accelerated / core / deferred)",
        "Additional Permitted Uses (LEP Schedule 1)",
        "Development feasibility snapshot: secondary dwelling, dual occ, CDC eligibility, GFA headroom",
        "Strata and community title detection",
        f"DCP setback controls with clause citations — {dcp_note}",
        "Required consultant reports with indicative cost and lead time",
        "Nearby DA activity (200 m, 12 months)",
        "VG land value and 5-year trend",
    ]
    not_included = [
        "Section 10.7 Planning Certificate (order from council)",
        "Section 73 Sydney Water Certificate (allow 1–4 weeks; physical inspection possible if built over pressure main)",
        "Title search (order via InfoTrack or equivalent)",
        "Land tax clearance certificate (order via Revenue NSW)",
        "Building certificate / OC gap check (order from council)",
        "BYDA utility search (Before You Dig Australia — free, site-specific)",
        "Strata inspection report (order via strata inspector)",
        "Survey or identification report",
    ]

    inc_text = "<br/>".join(f"✓  {i}" for i in included_items)
    not_text = "<br/>".join(f"–  {i}" for i in not_included)

    inc_style = S("ci", fontSize=7.5, textColor=colors.HexColor("#166534"), leading=11)
    not_style = S("cn", fontSize=7.5, textColor=colors.HexColor("#6B7280"), leading=11)
    hdr_style = S("ch2", fontSize=8, textColor=NAVY, fontName="Helvetica-Bold", leading=11)

    cov_tbl = Table(
        [
            [Paragraph("This report covers", hdr_style), Paragraph("Not included — order separately", hdr_style)],
            [Paragraph(inc_text, inc_style),              Paragraph(not_text, not_style)],
        ],
        colWidths=[CW * 0.58, CW * 0.42],
    )
    cov_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#F8FAFC")),
        ("BACKGROUND",    (0, 1), (-1, -1), colors.white),
        ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("LINEAFTER",     (0, 0), (0, -1),  0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(cov_tbl)
    story.append(Spacer(1, 5 * mm))

    # ------------------------------------------------------------------
    # SECTION 1 — Risk Summary (traffic lights)
    # ------------------------------------------------------------------
    h2("1. Risk Summary")

    _HIT_LABELS: dict[str, str] = {
        "biodiversity":            "Trigger risk — BDAR may apply",
        "riparian":                "Riparian corridor present",
        "wetlands":                "Wetland area present",
        "landslide":               "Landslide risk area",
        "flood":                   "Flood planning area",
        "foreshore_building_line": "Foreshore building line applies",
        "classified_road":         "Classified road frontage — 9 m setback",
        "bushfire":                "Bushfire prone land — BAL assessment required",
        "anef":                    "Aircraft noise contour — ANEF applies",
        "tod_precinct":            "TOD precinct — density uplift available",
        "tod_accelerated":         "TOD accelerated precinct — increased FSR/height",
        "tod_deferred":            "TOD deferred precinct — future uplift likely",
        "key_sites":               "Key site — site-specific LEP clause applies",
        "coastal_land_application": "Coastal management area — SEPP R&H 2021",
        "coastal_wetlands":        "Coastal wetland or proximity area — SEPP R&H 2021",
        "littoral_rainforest":     "Littoral rainforest or proximity area — SEPP R&H 2021",
        "coastal_environment_area": "Coastal environment area — SEPP R&H 2021",
        "coastal_use_area":        "Coastal use area — SEPP R&H 2021",
        "fire_history":            "Historical fire events recorded at this location",
    }
    # EPI-confirmed layers: absence from layerintersect = confirmed clear (not just missing data)
    _EPI_CONFIRMED: dict[str, str] = {
        "riparian": "riparian_epi",
        "flood":    "flood_epi",
    }
    # Layers where the PostGIS value field contains meaningful category text
    _VALUE_DISPLAY_LAYERS = frozenset({"biodiversity", "riparian", "wetlands", "landslide"})
    _prox = proximity_m or {}

    _leg_url = controls.get("legislation_url") or ""

    def flag(layer_type: str, label: str, present_style: str = "alert"):
        # 1. PostGIS hit (detailed spatial data)
        if layer_type in unique_by_type:
            base_label = _HIT_LABELS.get(layer_type, "Present")
            if layer_type == "key_sites":
                # value = clause reference from LAY_CLASS (e.g. "Schedule 1, Clause 1 (1)")
                clause_ref = unique_by_type[layer_type].get("value") or ""
                instrument = unique_by_type[layer_type].get("instrument") or ""
                if clause_ref and _leg_url:
                    hit_label = (
                        f'Key site — <a href="{_leg_url}" color="#1D4ED8">'
                        f"{clause_ref}</a> ({instrument or 'LEP'})"
                    )
                elif clause_ref:
                    hit_label = f"Key site — {clause_ref} ({instrument or 'LEP'})"
                else:
                    hit_label = base_label
                return [label, Paragraph(hit_label, ss[present_style]), "PostGIS"]
            if layer_type in _VALUE_DISPLAY_LAYERS:
                val = unique_by_type[layer_type].get("value") or ""
                # Append value as category qualifier when it adds info beyond the base label
                if val and val.lower() not in base_label.lower():
                    hit_label = f"{base_label} — {val}"
                else:
                    hit_label = base_label
            else:
                hit_label = base_label
            return [label, Paragraph(hit_label, ss[present_style]), "PostGIS"]
        # 2. EPI hit (Planning Portal confirms constraint via layerintersect)
        epi_key = _EPI_CONFIRMED.get(layer_type)
        if epi_key and controls.get(epi_key):
            hit_label = _HIT_LABELS.get(layer_type, "Present")
            return [label, Paragraph(hit_label, ss[present_style]), "NSW Planning Portal"]
        # 3. EPI confirmed absence (layerintersect ran, nothing found)
        if epi_key:
            return [label, Paragraph("Clear", ss["ok"]), "NSW Planning Portal"]
        # 4. PostGIS layer not mapped for this LGA — omit row entirely
        if covered_layers is not None and layer_type not in covered_layers:
            return None
        # 5. Covered but not intersecting — show "Clear" with proximity note if close
        if layer_type in _VALUE_DISPLAY_LAYERS and layer_type in _prox:
            dist = _prox[layer_type]
            if dist <= 500:
                prox_label = f"Clear — nearest {layer_type} buffer {dist:,}m"
                return [label, Paragraph(prox_label, ss["warn"]), "PostGIS"]
        return [label, Paragraph("Clear", ss["ok"]), "PostGIS"]

    # Portal-derived flags
    _h_hca = controls.get("heritage_hca") or []
    _h_indiv = [
        h for h in controls["heritage_items"]
        if h.lower() not in {x.lower() for x in _h_hca}
        and "conservation area" not in h.lower()
        and " hca" not in h.lower()
    ]
    if _h_indiv:
        _h_label = f"Individually listed — {_h_indiv[0]}" if len(_h_indiv) == 1 else f"Individually listed ({len(_h_indiv)} items)"
        heritage_flag = Paragraph(_h_label, ss["alert"])
    elif _h_hca:
        _h_label = f"Heritage Conservation Area — {_h_hca[0]}" if len(_h_hca) == 1 else f"Heritage Conservation Area ({len(_h_hca)} areas)"
        heritage_flag = Paragraph(_h_label, ss["warn"])
    elif controls["heritage_items"]:
        heritage_flag = Paragraph(controls["heritage_items"][0], ss["warn"])
    else:
        heritage_flag = Paragraph("Clear", ss["ok"])
    ass_flag = (
        Paragraph(controls["ass_class"], ss["warn"])
        if controls["ass_class"]
        else Paragraph("Clear", ss["ok"])
    )
    # Key sites: PostGIS is preferred (clause ref + hyperlink). Portal row only shown when
    # PostGIS has no hit — avoids duplicating a "Clear" row when both sources agree.
    _postgis_key_site_hit = "key_sites" in unique_by_type
    key_sites_flag = (
        Paragraph(f"Yes — {controls['key_sites_clause']}", ss["warn"])
        if controls["key_sites_clause"]
        else Paragraph("Clear", ss["ok"])
    )
    _apu_present = any(o["layer_type"] == "additional_permitted_uses" for o in unique_overlays)
    apu_flag = (
        Paragraph("Yes — additional uses permitted beyond zone table (see Section 3)", ss["ok"])
        if _apu_present
        else Paragraph("None identified", ss["ok"])
    )

    risk_rows = [
        ["Constraint", "Finding", "Source"],
        # Portal-sourced planning designations
        ["Heritage Listing",                          heritage_flag,   "NSW Planning Portal"],
        ["Acid Sulfate Soils",                        ass_flag,        "NSW Planning Portal"],
        # Portal key site row suppressed when PostGIS already shows a hit (avoids duplicate rows)
        *([["LEP Key Site or Special Provision",      key_sites_flag,  "NSW Planning Portal"]]
          if not _postgis_key_site_hit else []),
        ["Additional Permitted Uses (LEP Sch. 1)",    apu_flag,        "PostGIS"],
        # PostGIS-sourced environmental overlays (not in s10.7 or title search)
        # flag() returns None when the layer is not mapped for this LGA — omit those rows
        flag("biodiversity", "Biodiversity Values Map (BDAR trigger)", "warn"),
        flag("riparian",     "Riparian Land",                          "warn"),
        flag("wetlands",     "Wetlands",                               "warn"),
        flag("landslide",    "Landslide Risk"),
        flag("flood",        "Flood Planning Area"),
        # PostGIS-sourced LEP constraints
        flag("key_sites",               "Key Site (site-specific LEP clause)", "warn"),
        flag("foreshore_building_line", "Foreshore Building Line", "warn"),
        flag("classified_road",         "Classified Road Frontage (9 m setback)", "warn"),
        flag("bushfire",                "Bushfire Prone Land (BAL assessment)", "alert"),
        flag("anef",                    "Aircraft Noise Contour (ANEF)", "warn"),
    ]
    # TOD — opportunity signal (green/ok style), not a risk
    tod_type = next((t for t in ("tod_accelerated", "tod_precinct", "tod_deferred")
                     if t in unique_by_type), None)
    if tod_type is not None:
        tod_val = unique_by_type[tod_type].get("value") or ""
        tod_label = _HIT_LABELS.get(tod_type, "TOD precinct applies")
        risk_rows.append([
            "TOD Development Uplift",
            Paragraph(f"{tod_label}{f' ({tod_val})' if tod_val else ''}", ss["ok"]),
            "PostGIS",
        ])
    risk_rows = [r for r in risk_rows if r is not None]

    # Shadow risk row — derived from shadow pipeline
    if shadow_result is not None:
        jun21 = [s for s in (shadow_result.get("scenarios") or [])
                 if s["scenario"] in {"jun21_9am", "jun21_12pm", "jun21_3pm"}]
        overlap_count = sum(1 for s in jun21 if s.get("overlaps_subject_lot"))
        height_m = shadow_result.get("height_m") or "?"
        adg_ok = shadow_result.get("adg_compliant", True)
        # Worst Jun 21 overlap fraction for context (noon is usually most readable)
        jun21_fractions = [
            round((s.get("shadow_overlap_fraction") or 0) * 100)
            for s in jun21
        ]
        noon = next((s for s in jun21 if s["scenario"] == "jun21_12pm"), None)
        noon_pct = round((noon.get("shadow_overlap_fraction") or 0) * 100) if noon else 0

        _hob_note = f" (LEP maximum height of buildings: {height_m} m)"
        if adg_ok and overlap_count == 0:
            shadow_flag = Paragraph(
                f"Clear — a {height_m} m building on the northern adjacent lot would not "
                f"significantly shadow this property on any Jun 21 scenario.{_hob_note}",
                ss["ok"])
        elif adg_ok:
            shadow_flag = Paragraph(
                f"Low risk — a {height_m} m building on the northern adjacent lot would shadow "
                f"{noon_pct}% of this property at Jun 21 noon. ADG solar access requirement met.{_hob_note}",
                ss["warn"])
        else:
            shadow_flag = Paragraph(
                f"ADG concern — a {height_m} m building on the northern adjacent lot would shadow "
                f"{noon_pct}% of this property at Jun 21 noon. Solar access may not meet the "
                f"2-hour ADG requirement.{_hob_note}",
                ss["alert"])
        risk_rows.append(["Northern Development Shadow Risk", shadow_flag, "NSW LEP · shadow model"])
    else:
        risk_rows.append([
            "Northern Development Shadow Risk",
            Paragraph("Not assessed", ss["note"]),
            "NSW LEP · shadow model",
        ])

    c1, c2, c3 = 65 * mm, 70 * mm, CW - 135 * mm
    story.append(table(risk_rows, [c1, c2, c3]))

    # Show "not mapped" note only when covered_layers is populated but missing key layers
    _unmapped = [
        lbl for lbl, lt in [
            ("flood", "flood"), ("riparian", "riparian"),
            ("wetlands", "wetlands"), ("landslide", "landslide"),
            ("bushfire", "bushfire"), ("biodiversity", "biodiversity"),
        ]
        if covered_layers is not None and lt not in covered_layers
    ]
    if _unmapped:
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            f"<i>Not mapped in NSW state layer for this LGA:</i> {', '.join(_unmapped)}. "
            "These overlays are sourced from NSW Government ArcGIS services. Where a layer is absent, "
            "the council may not have uploaded data to the state layer, or the hazard may genuinely not "
            "apply to this LGA. Confirm with council or obtain a Section 10.7 planning certificate "
            "for authoritative disclosure.",
            ss["note"],
        ))

    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "<b>LEP Key Site or Special Provision</b> — a planning designation under the Local Environmental Plan "
        "identifying the parcel for strategic development or applying special development controls. Unrelated to environmental sensitivity. "
        "<b>Biodiversity Values Map (BDAR trigger)</b> — whether the land is mapped under the Biodiversity "
        "Conservation Act 2016. A positive result triggers a Biodiversity Development Assessment Report (BDAR), "
        "typically $15,000–$50,000 and 4–12 months. Not disclosed in a s10.7 certificate. "
        "<b>Bushfire Prone Land (BFPL)</b> — mapped under the Rural Fires Act 1997. A positive result triggers "
        "AS 3959 construction requirements and a Bushfire Attack Level (BAL) assessment. "
        "<b>ANEF</b> — Aircraft Noise Exposure Forecast contour. Requires acoustic report for sensitive land uses. "
        "<b>TOD</b> — Transport-Oriented Development precinct under SEPP (Housing) 2021 Part 3A. "
        "Precinct type determines whether density uplift is in force (accelerated), approved (core), or pending (deferred).",
        ss["note"]
    ))
    story.append(Spacer(1, 1 * mm))
    story.append(Paragraph(
        "Sources: Heritage, ASS, Key Site, SEPP overlays — NSW Planning Portal layerintersect (live query). "
        "Environmental and spatial overlays (biodiversity, riparian, wetlands, landslide, flood, bushfire, ANEF, TOD, APU) — "
        "PostGIS spatial database ingested from NSW Government ArcGIS services. Coverage: 128 NSW councils. "
        "None of these layers are disclosed in a standard s10.7(2) certificate or title search.",
        ss["note"]
    ))
    if shadow_result is not None and not shadow_result.get("adg_compliant", True):
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            "<b>Northern Development Shadow Risk</b> — modelled using the NSW Apartment Design Guide (ADG) "
            "standard: 5 key dates/times including the three Jun 21 (winter solstice) snapshots that determine "
            "ADG compliance. The model assumes a max-height building (per LEP) on the lot immediately to the "
            "north, using the subject lot's own cadastral footprint as a symmetric proxy. "
            "This risk is not disclosed in a standard s10.7 certificate, title search, or conveyancing "
            "inspection. A formal shadow impact assessment prepared by a qualified town planner is required "
            "for Development Application submission.",
            ss["note"]
        ))

    # ------------------------------------------------------------------
    # SECTION 2 — Development Feasibility Snapshot
    # ------------------------------------------------------------------
    h2("2. Settlement Risk Flags")
    story.append(Paragraph(
        "Planning constraints relevant to pre-settlement due diligence. Based on LEP controls, "
        "valuation data and environmental overlays. Each finding requires professional "
        "planning advice before acting.",
        ss["note"]
    ))
    story.append(Spacer(1, 3 * mm))

    if feasibility:
        feas_rows = [["Question", "Finding", "Basis"]]
        for item in feasibility:
            flag = item["flag"]
            ans_style = "ok" if flag == "ok" else ("warn" if flag == "warn" else "alert")
            feas_rows.append([
                Paragraph(item["question"], ss["body"]),
                Paragraph(item["answer"], ss[ans_style]),
                Paragraph(item["basis"], ss["note"]),
            ])
        story.append(table(feas_rows, [55 * mm, 40 * mm, CW - 95 * mm]))
    else:
        story.append(Paragraph("Feasibility assessment unavailable — lot area data not returned.", ss["note"]))

    story.append(Spacer(1, 4 * mm))

    # ------------------------------------------------------------------
    # STRATA PANEL (shown when strata lot detected)
    # ------------------------------------------------------------------
    _si = strata_info or {}
    if _si.get("is_strata"):
        sp_num = _si.get("strata_plan") or ""
        sp_src = _si.get("source", "address_heuristic")
        plan_type = _si.get("plan_type", "strata")

        # Title line only — source attribution goes in footnote below section
        if sp_num:
            title_label = f"Community Title — {sp_num}" if plan_type == "community" else f"Strata Title — {sp_num}"
        elif plan_type == "strata_or_company":
            title_label = "Strata or Company Title"
        else:
            title_label = "Strata Title"

        strata_hdr = Paragraph(
            title_label,
            S("sh", fontSize=9, textColor=WHITE, fontName="Helvetica-Bold", leading=13),
        )

        # Source note for below the section
        if plan_type == "strata_or_company":
            strata_src_note = (
                "Title classification: Detected from address format. "
                "Company title properties return as Torrens in the land register — confirm title type via title search."
            )
        elif sp_src in ("cadastre", "cadastre+address"):
            strata_src_note = "Title classification: NSW Planning Portal."
        else:
            strata_src_note = "Title classification: Detected from address format — confirm via title search."

        company_note = (
            "<b>Note — company title possible:</b> Company title is most common in older apartment "
            "buildings in inner Sydney (Potts Point, Elizabeth Bay, Kirribilli, Darlinghurst, Paddington) "
            "that predate or were never converted to strata. In company title, the building is owned by "
            "a company — buyers acquire shares, not land. Company title returns as Torrens in the land "
            "register (the company holds the DP lot), so standard title searches do not flag it. "
            "Obtain a company title inspection report if in doubt.<br/><br/>"
            if plan_type == "strata_or_company" else ""
        )

        strata_body_lines = [
            "<b>Development feasibility:</b> Secondary dwelling and Torrens title subdivision are not available "
            "on strata lots. Any works to common property require a unanimous special resolution of the owners "
            "corporation. Unit-specific alterations are subject to by-laws.",
            "",
            "<b>Valuation data:</b> NSW Valuation Service records land value and lot area for the whole building "
            "parcel, not the individual unit. These figures are not shown — they reflect the building site, "
            "not what the purchaser is acquiring.",
            "",
            "<b>Planning constraints remain fully applicable:</b> Environmental overlays (biodiversity, riparian, "
            "flood), heritage, LEP controls, and SEPP instruments apply to the land and building regardless of "
            "title type. The s10.7(2) disclosure gap in this report is equally relevant for strata purchasers.",
            "",
            company_note + "<b>Strata-specific due diligence — obtain separately:</b>",
            f"· NSW Strata Hub — scheme registration, managing agent, lot entitlement: {STRATA_HUB_URL}",
            "· Strata inspection report — by-laws, financial statements, 10-year capital works fund forecast",
            "· Active strata renewal applications — NCAT register (ncat.nsw.gov.au)",
            "· Owners corporation levy schedule — confirm sinking fund health and any special levies outstanding",
        ]
        strata_body = Paragraph(
            "<br/>".join(strata_body_lines),
            S("sb", fontSize=8, textColor=colors.HexColor("#1E3A5F"), leading=12),
        )
        strata_tbl = Table([[strata_hdr], [strata_body]], colWidths=[CW])
        strata_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
            ("BACKGROUND",    (0, 1), (-1, -1), colors.HexColor("#EFF6FF")),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 9),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 9),
            ("BOX",           (0, 0), (-1, -1), 0.5, NAVY),
        ]))
        story.append(strata_tbl)
        story.append(Spacer(1, 1 * mm))
        story.append(Paragraph(strata_src_note, ss["note"]))
        story.append(Spacer(1, 4 * mm))
    elif _si.get("parent_has_strata"):
        story.append(Paragraph(
            f"<b>Note — Strata scheme on this parcel ({_si.get('plan_label', '')}):</b> "
            "The title search for this property should confirm whether the subject lot is Torrens title "
            "or forms part of a strata scheme. Environmental constraints and LEP controls in this report "
            "apply regardless of title type.",
            ss["warn"]
        ))
        story.append(Spacer(1, 4 * mm))

    # ------------------------------------------------------------------
    # SECTION 3 — Property & Development Rights
    # ------------------------------------------------------------------
    h2("3. Property & Development Rights")

    # Zone description in table: code only — full objectives text rendered below as narrative
    zone_str = controls["zone"] or "—"

    lep_rows = [
        ["Control", "Value", "Reference"],
        ["Zone",
         Paragraph(zone_str, ss["body"]),
         controls["zone_epi"] or "—"],
        ["Max Building Height",
         f"{controls['height']} {controls['height_units']}".strip() if controls["height"] else "No LEP height limit",
         controls["height_clause"] or ""],
        ["Floor Space Ratio",
         controls["fsr"] or "Not specified",
         controls["fsr_clause"] or ""],
        ["Min Lot Size (LEP)",
         f"{controls['lot_size']} {controls['lot_size_units']}".strip() if controls["lot_size"] else "Not specified",
         controls["lot_size_clause"] or ""],
    ]

    # Valuation data rows — whole-parcel figures not shown for strata (see strata panel above)
    _is_strata = (_si or {}).get("is_strata", False)
    if not _is_strata:
        if headroom.get("lot_area_m2"):
            lep_rows.append(["Actual Lot Area", headroom["lot_area_display"], "NSW Valuation Service"])
        if headroom.get("land_value"):
            lv_line = headroom["land_value_display"]
            if headroom.get("land_value_per_m2"):
                lv_line += f"  ({headroom['land_value_per_m2_display']})"
            lep_rows.append(["Land Value (excl. buildings)", lv_line, "NSW Valuation Service"])
    else:
        lep_rows.append(["Land Value", Paragraph("See Strata Title note above", ss["note"]), "NSW Valuation Service"])

    story.append(table(lep_rows, [50 * mm, 68 * mm, CW - 118 * mm]))
    story.append(Spacer(1, 3 * mm))

    # Development headroom + subdivision — suppressed for strata
    if not _is_strata:
        if headroom.get("max_gfa_m2"):
            story.append(Paragraph(
                f"<b>Maximum permissible GFA: {headroom['max_gfa_display']}</b> "
                f"(lot area {headroom['lot_area_display']} × FSR {headroom['fsr_numeric']}:1). "
                "Actual achievable GFA subject to setbacks, height plane, and DCP controls.",
                ss["body"]
            ))
            story.append(Spacer(1, 2 * mm))

        if "subdivision_note" in headroom:
            style_key = "warn" if headroom.get("subdivision_feasible") else "note"
            story.append(Paragraph(f"<b>Subdivision:</b> {headroom['subdivision_note']}", ss[style_key]))
            story.append(Spacer(1, 2 * mm))

    # VG 5-year land value trend — suppressed for strata (whole-lot value, not unit)
    val_history = [] if _is_strata else (valuation.get("val_history") or [])
    if len(val_history) >= 2:
        story.append(Paragraph("<b>Land Value Trend (excl. buildings — NSW Valuation Service):</b>", ss["body"]))
        story.append(Spacer(1, 1 * mm))
        trend_rows = [["Valuation Date", "Land Value", "Change"]]
        for i, entry in enumerate(val_history):
            if i == 0:
                trend_rows.append([entry["year"] or "—", f"${entry['value']:,.0f}", "—"])
            else:
                prev_val = val_history[i - 1]["value"]
                delta = entry["value"] - prev_val
                pct = (delta / prev_val * 100) if prev_val else 0
                sign = "+" if delta >= 0 else ""
                delta_str = f"{sign}${abs(delta):,.0f} ({sign}{pct:.1f}%)"
                trend_rows.append([
                    entry["year"] or "—",
                    f"${entry['value']:,.0f}",
                    Paragraph(delta_str, ss["ok"] if delta >= 0 else ss["warn"]),
                ])
        story.append(table(trend_rows, [48 * mm, 45 * mm, CW - 93 * mm]))
        story.append(Spacer(1, 2 * mm))

    # Zone objectives — from actual LEP (layerintersect "Land Use" field), not a lookup table.
    # Permitted/prohibited uses table: refer to the LEP instrument directly.
    zone_code = (controls.get("zone") or "").split()[0].upper()
    zone_full = controls.get("zone_full") or ""
    zone_epi = controls.get("zone_epi") or ""
    legislation_url = controls.get("legislation_url") or ""
    if zone_full:
        story.append(Paragraph(
            f"<b>Zone objectives ({zone_code}):</b> {zone_full}",
            ss["body"]
        ))
        story.append(Spacer(1, 1 * mm))
    if zone_epi or legislation_url:
        ref_text = f"Permitted and prohibited uses: see {zone_epi} — Zone {zone_code} land use table"
        if legislation_url:
            ref_text += f" at {legislation_url}"
        story.append(Paragraph(ref_text, ss["note"]))
        story.append(Spacer(1, 2 * mm))

    # Key Sites clause plain English — sourced from lep_clauses DB table
    _ks_clause = controls.get("key_sites_clause")
    _ks_items = lep_clauses or []
    if _ks_clause and _ks_items:
        story.append(Paragraph("<b>Key Sites provisions:</b>", ss["body"]))
        for cl in _ks_items:
            if cl["summary"]:
                story.append(Paragraph(
                    f"• <b>Cl {cl['number']}:</b> {cl['summary']}",
                    ss["note"],
                ))
            else:
                # No DB row — show raw ref + legislation link so nothing is lost
                story.append(Paragraph(
                    f"• <b>Cl {cl['number']}:</b> {_ks_clause} — refer to {legislation_url or 'the applicable LEP'}.",
                    ss["note"],
                ))
        story.append(Spacer(1, 2 * mm))
    elif _ks_clause:
        # lep_clauses not pre-fetched (e.g., non-Inner West council) — show raw ref
        story.append(Paragraph("<b>Key Sites provisions:</b>", ss["body"]))
        story.append(Paragraph(
            f"• {_ks_clause} — refer to {legislation_url or 'the applicable LEP'}.",
            ss["note"],
        ))
        story.append(Spacer(1, 2 * mm))

    # Additional Permitted Uses — LEP Schedule 1 site-specific permissions
    # Data: PostGIS spatial_overlays, layer_type = 'additional_permitted_uses'
    # These are real spatial features from the LEP — only shown when PostGIS confirms a hit.
    _apu_overlays = [o for o in unique_overlays if o["layer_type"] == "additional_permitted_uses"]
    if _apu_overlays:
        story.append(Paragraph("<b>Additional Permitted Uses (LEP Schedule 1)</b>", ss["body"]))
        for apu in _apu_overlays:
            apu_val = apu.get("value") or "Refer to LEP Schedule 1"
            apu_inst = apu.get("instrument") or ""
            story.append(Paragraph(f"• {apu_val}", ss["body"]))
        story.append(Spacer(1, 1 * mm))
        story.append(Paragraph(
            "This lot has been identified as having Additional Permitted Uses under the Local "
            "Environmental Plan (Schedule 1). These are site-specific permissions granted by the "
            "LEP that allow development types not otherwise permitted in the zone. "
            "Verify the current instrument via the NSW Planning Portal or the relevant LEP "
            "before relying on these permissions — they may be subject to development standards "
            "or conditions set out in Schedule 1.",
            ss["note"]
        ))
        story.append(Spacer(1, 2 * mm))

    # ------------------------------------------------------------------
    # SECTION 4 — DCP Development Controls (setbacks)
    # ------------------------------------------------------------------
    h2("4. DCP Development Controls — Setbacks")

    if _is_strata:
        story.append(Paragraph(
            "DCP setback controls are not applicable to individual strata units. "
            "Setback requirements govern building works on the land parcel and apply to the "
            "building as a whole — any alterations or additions to common property require "
            "owners corporation approval. Unit-specific works (internal alterations) are "
            "governed by the strata by-laws, not DCP setbacks.",
            ss["note"]
        ))
        story.append(Spacer(1, 4 * mm))

    if not _is_strata:
        prop_zone = (controls.get("zone") or "").split()[0].upper()
        dcp_data = dcp_setbacks_db
        # Only flag mismatch when zones_applicable is explicitly populated AND zone is not in it.
        # Empty list means "applies to all residential zones" — no mismatch.
        zone_mismatch = bool(
            dcp_data
            and dcp_data.get("zones_applicable")
            and prop_zone
            and prop_zone not in dcp_data["zones_applicable"]
        )
    else:
        dcp_data = None
        zone_mismatch = False
        prop_zone = ""

    if dcp_data and not zone_mismatch:
        story.append(Paragraph(
            f"<b>{dcp_data['dcp_name']}</b> — {dcp_data['section']}",
            ss["body"]
        ))
        story.append(Paragraph(
            "Controls below apply to the DA (Development Application) pathway. "
            "If construction meets SEPP (Housing) 2021 CDC standards, complying development "
            "certification applies different minimum setbacks — consult a certifier.",
            ss["note"]
        ))
        story.append(Spacer(1, 3 * mm))

        c1b, c2b, c3b, c4b = 52 * mm, 40 * mm, 28 * mm, CW - 120 * mm

        def _render_setback_group(setback_list: list[dict], label: str) -> None:
            if not setback_list:
                return
            story.append(Paragraph(f"<b>{label}</b>", ss["body"]))
            story.append(Spacer(1, 1 * mm))

            prescribed_rows = [sb for sb in setback_list if sb["control_type"] == "prescribed"]
            site_derived_rows = [sb for sb in setback_list if sb["control_type"] == "site_derived"]

            if prescribed_rows:
                story.append(Paragraph(
                    "Prescribed minimums — fixed numbers in the DCP text:",
                    ss["note"]
                ))
                story.append(Spacer(1, 1 * mm))
                tbl_rows = [["Setback", "Minimum", "Clause", "Notes"]]
                for sb in prescribed_rows:
                    tbl_rows.append([
                        Paragraph(sb["type"], ss["body"]),
                        Paragraph(sb["requirement"], ss["ok"]),
                        Paragraph(sb["clause"], ss["note"]),
                        Paragraph(sb["notes"], ss["note"]),
                    ])
                story.append(table(tbl_rows, [c1b, c2b, c3b, c4b]))
                story.append(Spacer(1, 2 * mm))

            if site_derived_rows:
                story.append(Paragraph(
                    "Site-derived controls — no fixed number; assessed from site context:",
                    ss["note"]
                ))
                story.append(Spacer(1, 1 * mm))
                tbl_rows2 = [["Setback", "Method / Basis", "Clause", "Notes"]]
                for sb in site_derived_rows:
                    tbl_rows2.append([
                        Paragraph(sb["type"], ss["body"]),
                        Paragraph(sb["requirement"], ss["warn"]),
                        Paragraph(sb["clause"], ss["note"]),
                        Paragraph(sb["notes"], ss["note"]),
                    ])
                story.append(table(tbl_rows2, [c1b, c2b, c3b, c4b]))
                story.append(Spacer(1, 2 * mm))

        # ── Dwelling house controls ──
        _render_setback_group(dcp_data.get("setbacks") or [], "Dwelling house")

        # ── Secondary dwelling (granny flat) controls ──
        sd_rows = dcp_data.get("sd_setbacks") or []
        if sd_rows:
            story.append(Paragraph(
                "Secondary dwelling (granny flat) setbacks are DCP controls for the DA pathway. "
                "The CDC pathway via SEPP (Housing) 2021 applies minimum standards independent of "
                "these DCP requirements — a certifier can advise on which path applies.",
                ss["note"]
            ))
            story.append(Spacer(1, 1 * mm))
            _render_setback_group(sd_rows, "Secondary dwelling (granny flat)")
        else:
            story.append(Paragraph(
                "Secondary dwelling setbacks: no LGA-specific DCP controls extracted. "
                "CDC pathway uses SEPP (Housing) 2021 minimum standards.",
                ss["note"]
            ))

        story.append(Spacer(1, 1 * mm))

        # Dual-regime caveat (Canterbury-Bankstown) or other area-specific notes
        if dcp_data.get("caveat"):
            story.append(Paragraph(
                f"<b>Important:</b> {dcp_data['caveat']}",
                ss["warn"]
            ))
            story.append(Spacer(1, 2 * mm))

        story.append(Paragraph(
            "These controls apply to the identified development types in residential zones. "
            "Other development types (dual occupancy, multi-dwelling, residential flat buildings) "
            "trigger different DCP chapters. Heritage listings or HCA status add further controls. "
            "A town planner is required to determine applicable setbacks for any specific proposal.",
            ss["note"]
        ))
        if any(sb["control_type"] == "site_derived" for sb in (dcp_data.get("setbacks") or []) + (dcp_data.get("sd_setbacks") or [])):
            story.append(Spacer(1, 1 * mm))
            story.append(Paragraph(
                "<b>Site-derived controls require a site visit:</b> Where setbacks are determined by "
                "prevailing character or site-specific analysis, the actual number cannot be "
                "established without a site inspection and pre-DA assessment.",
                ss["note"]
            ))

    elif dcp_data and zone_mismatch:
        story.append(Paragraph(
            f"Zone {prop_zone} — DCP setback data extracted for low density residential zones (R1/R2) only. "
            f"Controls for {prop_zone} zones in {dcp_data['dcp_name']} have not been extracted. "
            "Obtain the applicable DCP chapter from Council.",
            ss["note"]
        ))

    else:
        story.append(Paragraph(
            "DCP setback controls have not been extracted for this LGA. "
            "Obtain the applicable DCP chapter directly from Council or the NSW Planning Portal.",
            ss["note"]
        ))

    story.append(Spacer(1, 4 * mm))

    # ------------------------------------------------------------------
    # SECTION 5 — Environmental Constraints (detail)
    # ------------------------------------------------------------------
    h2("5. Environmental Constraints")

    # 3a — Acid sulfate (from portal)
    if controls["ass_class"]:
        story.append(Paragraph(f"<b>Acid Sulfate Soils: {controls['ass_class']}</b>", ss["body"]))
        story.append(Paragraph(
            ASS_DESCRIPTIONS.get(controls["ass_class"], "Acid sulfate soils management plan may be required."),
            ss["note"]
        ))
        story.append(Spacer(1, 2 * mm))

    # 3b — PostGIS unique overlays
    for layer_type, note_text in POSTGIS_NOTES.items():
        if layer_type in unique_by_type:
            ov = unique_by_type[layer_type]
            label = layer_type.replace("_", " ").title()
            val = ov.get("value") or "Present"
            story.append(Paragraph(f"<b>{label}: {val}</b>", ss["warn"]))
            # Use dynamic flood note if available; fall back to static for other layers
            if layer_type == "flood" and _flood_note_dynamic:
                display_note = _flood_note_dynamic
            elif layer_type == "bushfire" and _bushfire_note_dynamic:
                display_note = _bushfire_note_dynamic
            else:
                display_note = note_text
            story.append(Paragraph(display_note, ss["note"]))
            story.append(Spacer(1, 2 * mm))

            # Flood: multi-AEP scenario table — one row per ingested flood extent
            # Only render when at least one ARI-quantified row exists; generic-only floods
            # show the note text instead (no table to build).
            if layer_type == "flood" and len(_ari_rows) > 1:
                _aep_hdr_style = S("fth", fontSize=7.5, textColor=WHITE, fontName="Helvetica-Bold", leading=11)
                _aep_rows = [[Paragraph(h, _aep_hdr_style) for h in ["Flood Scenario", "AEP", "Return Period", "Source"]]]
                for fr in _ari_rows:
                    val = fr.get("value") or ""
                    ari = _parse_ari(val)
                    if "pmf" in val.lower():
                        aep_str = "< 0.01%"
                        rp_str = "PMF (extreme upper bound)"
                    else:
                        aep_pct = (100.0 / ari) if ari and ari < 999999 else 0
                        aep_str = f"{aep_pct:.1f}%" if aep_pct >= 0.1 else f"{aep_pct:.2f}%"
                        rp_str = f"1-in-{_ari_str(ari)}-year"
                    _aep_rows.append([
                        Paragraph(val, ss["note"]),
                        Paragraph(aep_str, ss["note"]),
                        Paragraph(rp_str, ss["note"]),
                        Paragraph((fr.get("instrument") or "").replace("_", " "), ss["note"]),
                    ])
                _aep_tbl = Table(_aep_rows, colWidths=[38 * mm, 20 * mm, 45 * mm, CW - 103 * mm])
                _aep_tbl.setStyle(TableStyle([
                    ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#1E3A5F")),
                    ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
                    ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
                    ("FONTSIZE",      (0, 0), (-1, -1), 7.5),
                    ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, colors.HexColor("#EFF6FF")]),
                    ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#BFDBFE")),
                    ("TOPPADDING",    (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING",   (0, 0), (-1, -1), 5),
                    ("VALIGN",        (0, 0), (-1, -1), "TOP"),
                ]))
                story.append(Spacer(1, 1 * mm))
                story.append(_aep_tbl)
                story.append(Spacer(1, 2 * mm))

            # Flood: add a "Next Steps" action callout
            if layer_type == "flood" and _flood_rows:
                _lga_display = (_flood_rows[0].get("lga") or "council").title()
                _steps = [
                    f"<b>1. Order a Section 733 Certificate</b> from {_lga_display} Council — this is the official "
                    "confirmation of flood affectation, any recorded flood history, and the applicable flood "
                    "planning level. Cost ~$50–150, turnaround 5–10 business days. Ask your client to allow for "
                    "this before exchange.",
                    "<b>2. Check flood insurance cost</b> before exchange — obtain a quote from the buyer's insurer "
                    "or via the Insurance Council of Australia's flood tool (understandinsurance.com.au). "
                    "Premiums in flood-affected areas can be $10,000–$30,000+/year. This is a material "
                    "transaction consideration.",
                    "<b>3. Ask the vendor</b>: Has a flood report been commissioned? Has the property flooded "
                    "before? Any prior flood damage claims? These are legitimate pre-exchange requisitions.",
                    "<b>4. Check council's flood planning maps</b> if the Section 733 does not state a floor level — "
                    f"{_lga_display} Council's website may publish online flood check tools or DCP flood mapping.",
                ]
                ns_header = Paragraph(
                    "Next Steps — Flood Affected Property",
                    S("nsh", fontSize=8, textColor=WHITE, fontName="Helvetica-Bold", leading=11),
                )
                ns_body = Paragraph(
                    "<br/><br/>".join(_steps),
                    S("nsb", fontSize=7.5, textColor=colors.HexColor("#1E3A5F"), leading=11),
                )
                ns_tbl = Table([[ns_header], [ns_body]], colWidths=[CW])
                ns_tbl.setStyle(TableStyle([
                    ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
                    ("BACKGROUND",    (0, 1), (-1, -1), colors.HexColor("#EFF6FF")),
                    ("TOPPADDING",    (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING",   (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
                    ("BOX",           (0, 0), (-1, -1), 0.5, NAVY),
                ]))
                story.append(ns_tbl)
                story.append(Spacer(1, 2 * mm))

    no_constraints = not controls["ass_class"] and not any(
        lt in unique_by_type
        for lt in POSTGIS_UNIQUE_LAYERS | {"foreshore_building_line", "classified_road", "bushfire", "anef"}
    )
    if no_constraints:
        story.append(Paragraph(
            "No acid sulfate soils, biodiversity, riparian, wetland, landslide, flood, bushfire, "
            "aircraft noise, coastal hazard, or fire history overlays identified at this location.",
            ss["body"]
        ))

    # ------------------------------------------------------------------
    # SECTION 4 — Heritage
    # ------------------------------------------------------------------
    h2("6. Heritage")

    _hca_items = controls.get("heritage_hca") or []
    # Heritage items = individual listings (exclude anything already captured as HCA)
    _hca_lower = {h.lower() for h in _hca_items}
    _individual_items = [
        h for h in controls["heritage_items"]
        if h.lower() not in _hca_lower
        and "conservation area" not in h.lower()
        and " hca" not in h.lower()
    ]

    if _individual_items:
        story.append(Paragraph("<b>Individual Heritage Listing</b>", ss["body"]))
        for item in _individual_items:
            story.append(Paragraph(f"• {item}", ss["body"]))
        story.append(Spacer(1, 1 * mm))
        story.append(Paragraph(
            "This property is individually listed on the LEP heritage register. "
            "All development — including minor alterations, new structures, and demolition — "
            "requires a Heritage Impact Statement (HIS). Substantial works require Council "
            "heritage advisor review. Buyer to engage a heritage consultant prior to any "
            "development application.",
            ss["note"]
        ))
        story.append(Spacer(1, 2 * mm))

    if _hca_items:
        story.append(Paragraph("<b>Heritage Conservation Area (HCA)</b>", ss["body"]))
        for item in _hca_items:
            story.append(Paragraph(f"• {item}", ss["body"]))
        story.append(Spacer(1, 1 * mm))
        story.append(Paragraph(
            "This property is within a Heritage Conservation Area. The property itself is not "
            "individually listed, but is subject to HCA controls under the LEP and DCP. "
            "Development that would affect the character of the area — including new structures, "
            "alterations to the facade, and demolition — requires Council approval and may require "
            "a Heritage Impact Statement.",
            ss["note"]
        ))
        story.append(Spacer(1, 2 * mm))

    if not _individual_items and not _hca_items:
        if controls["heritage_items"]:
            # Portal returned items but could not classify — show raw
            for item in controls["heritage_items"]:
                story.append(Paragraph(f"• {item}", ss["body"]))
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph(
                "Heritage listing confirmed. Buyer to verify whether this is an individual listing "
                "or Heritage Conservation Area via Council heritage maps.",
                ss["note"]
            ))
        else:
            story.append(Paragraph("No heritage listing identified via NSW Planning Portal.", ss["body"]))

    # ------------------------------------------------------------------
    # SECTION 5 — SEPP and Special Provisions
    # ------------------------------------------------------------------
    h2("7. State Environmental Planning Policy (SEPP) Overlays")

    if controls["sepp_overlays"]:
        sepp_rows = [["SEPP / Instrument", "Practical Implication"]]
        seen: set[tuple] = set()
        for ov in controls["sepp_overlays"]:
            name = ov["name"] or ""
            type_ = ov.get("type") or ""
            key = (name, type_)
            if key in seen:
                continue
            seen.add(key)
            plain = interpret_sepp(name, type_, ov.get("label") or "", "")
            if plain is None:
                continue  # dedicated report section covers this overlay type
            sepp_rows.append([
                Paragraph(name or "—", ss["body"]),
                Paragraph(plain, ss["note"]),
            ])
        story.append(table(sepp_rows, [85 * mm, CW - 85 * mm]))
    else:
        story.append(Paragraph("No SEPP special provisions identified at this location.", ss["body"]))

    if controls["housing_sepp"]:
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            "Housing SEPP applies — may permit additional residential development types "
            "or increased density above LEP controls. Verify current Housing SEPP provisions.",
            ss["warn"]
        ))
    # TOD — prefer PostGIS data (accurate spatial boundary), fall back to portal SEPP flag
    _tod_postgis_type = next(
        (t for t in ("tod_accelerated", "tod_precinct", "tod_deferred") if t in unique_by_type), None
    )
    if _tod_postgis_type or controls["tod_area"]:
        story.append(Spacer(1, 2 * mm))
        if _tod_postgis_type:
            _tod_ov = unique_by_type[_tod_postgis_type]
            _tod_val = _tod_ov.get("value") or ""
            _tod_type_label = {
                "tod_accelerated": "TOD Accelerated Precinct",
                "tod_precinct":    "TOD Core Precinct",
                "tod_deferred":    "TOD Deferred Precinct",
            }.get(_tod_postgis_type, "TOD Precinct")
            _tod_implications = {
                "tod_accelerated": (
                    "Accelerated precincts have already had uplift applied via LEP amendment — "
                    "check the current LEP for the applicable FSR and height controls at this address. "
                    "Higher density residential development (including mid-rise) may already be permissible."
                ),
                "tod_precinct": (
                    "Core TOD precincts are subject to increased FSR and height under SEPP (Housing) 2021 "
                    "Part 3A — typically 2:1 FSR and 22 m height within 400 m of the station, "
                    "stepping down at 800 m. Development assessment uses a low-rise to mid-rise pathway."
                ),
                "tod_deferred": (
                    "This precinct is in a deferred TOD area — planning uplift has not yet been applied. "
                    "Monitor NSW Planning Portal for gazettal of the applicable LEP amendment. "
                    "Uplift is expected but is not yet in force."
                ),
            }.get(_tod_postgis_type, TOD_NOTE)
            story.append(Paragraph(f"<b>{_tod_type_label}{f': {_tod_val}' if _tod_val else ''}</b>", ss["ok"]))
            story.append(Paragraph(_tod_implications, ss["note"]))
        else:
            story.append(Paragraph(
                "Transport-Oriented Development (TOD) area — significantly increased FSR and height "
                "limits may apply within 400 m of eligible station. Confirm current controls via "
                "NSW Planning Portal or LEP maps.",
                ss["warn"]
            ))

    # Statewide SEPPs — always applicable, no spatial footprint
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "<b>Statewide SEPP applicability</b> — the following instruments apply across NSW "
        "regardless of property location and do not appear as spatial overlays:",
        ss["body"]
    ))
    story.append(Spacer(1, 2 * mm))

    zone_code_sepp = (controls.get("zone") or "").split()[0].upper()
    has_classified_road = "classified_road" in unique_by_type

    statewide_rows = [["Instrument", "When it applies", "Key implication"]]
    statewide_rows.extend([
        [
            "SEPP (Sustainable Buildings) 2022",
            "All residential development",
            "BASIX certificate required for new dwellings and alterations/additions "
            "exceeding $50,000. Must demonstrate energy, water and thermal comfort targets.",
        ],
        [
            "SEPP (Housing) 2021",
            "Residential zones — dual occ, secondary dwellings, complying dev",
            "Enables secondary dwellings (450 m² lot min), dual occupancy, and "
            "low-rise medium density housing as complying development in eligible zones. "
            "Sets minimum site standards that override some LEP controls.",
        ],
        [
            "SEPP (Transport and Infrastructure) 2021",
            "Land adjoining classified roads and rail corridors",
            (
                "9 m minimum setback from classified road boundary for new dwellings. "
                "Noise and vibration assessment required for development near rail. "
                + ("Classified road frontage identified at this property — applies." if has_classified_road
                   else "No classified road frontage identified at this property.")
            ),
        ],
        [
            "SEPP (Resilience and Hazards) 2021",
            "All land — flood, coastal hazard, contaminated land",
            "Overrides local controls for land affected by natural hazards. "
            "Flood provisions apply statewide — council must have regard to flood planning levels. "
            "Contaminated land requires remediation before sensitive uses.",
        ],
    ])

    statewide_col_w = [58 * mm, 45 * mm, CW - 103 * mm]
    hdr_s = S("sw_h", fontSize=8, textColor=WHITE, fontName="Helvetica-Bold", leading=11)
    body_s = S("sw_b", fontSize=8, textColor=colors.HexColor("#374151"), leading=11)
    note_s = S("sw_n", fontSize=7, textColor=colors.HexColor("#6B7280"), leading=11)

    def _sw_row(row, is_header=False):
        style = hdr_s if is_header else body_s
        return [Paragraph(cell, style) for cell in row]

    def _sw_data_row(instrument, when, impl):
        return [
            Paragraph(instrument, body_s),
            Paragraph(when, note_s),
            Paragraph(impl, note_s),
        ]

    sw_pdf_rows = [_sw_row(statewide_rows[0], is_header=True)]
    for row in statewide_rows[1:]:
        sw_pdf_rows.append(_sw_data_row(*row))

    statewide_tbl = Table(sw_pdf_rows, colWidths=statewide_col_w)
    statewide_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  TEAL_DK),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, colors.HexColor("#F3F4F6")]),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(statewide_tbl)
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "PropCode and standard s10.7 certificates list some statewide instruments but do not "
        "assess applicability to the specific property. The spatial SEPP overlays above (Section 7 table) "
        "identify instruments with a geographic footprint at this location.",
        ss["note"]
    ))

    # ------------------------------------------------------------------
    # SECTION 7a — Required Consultant Reports
    # ------------------------------------------------------------------
    h2("8. Required Consultant Reports")

    _consultant_rows = [["Report", "Trigger", "Typical Cost", "Typical Lead Time"]]
    # Always required
    _consultant_rows.append([
        "BASIX Certificate",
        "All new dwellings; alterations/additions > $50,000",
        "$300–600",
        "1–3 days",
    ])
    # Conditional on flags
    if _individual_items:
        _consultant_rows.append([
            "Heritage Impact Statement (HIS)",
            "Individually heritage-listed property",
            "$3,000–10,000",
            "2–4 weeks",
        ])
    if _h_hca:
        _consultant_rows.append([
            "Heritage Impact Statement (HIS) — HCA",
            "Property within Heritage Conservation Area",
            "$2,000–6,000",
            "1–3 weeks",
        ])
    if "bushfire" in unique_by_type:
        _consultant_rows.append([
            "Bushfire Attack Level (BAL) Assessment",
            "Bushfire prone land — required before any DA",
            "$800–2,500",
            "1–2 weeks",
        ])
    if "anef" in unique_by_type:
        _consultant_rows.append([
            "Acoustic Report (Aircraft Noise)",
            "Property within ANEF contour",
            "$2,000–5,000",
            "1–3 weeks",
        ])
    if "biodiversity" in unique_by_type:
        _consultant_rows.append([
            "Biodiversity Development Assessment Report (BDAR)",
            "Biodiversity Values Map trigger",
            "$15,000–50,000",
            "4–12 months",
        ])
    if "flood" in unique_by_type:
        _consultant_rows.append([
            "Section 733 Flood Certificate",
            "Flood planning area",
            "$50–150",
            "5–10 business days",
        ])
    if "riparian" in unique_by_type:
        _consultant_rows.append([
            "Riparian / Vegetation Management Report",
            "Riparian corridor present",
            "$2,000–8,000",
            "2–6 weeks",
        ])
    if controls.get("ass_class"):
        _consultant_rows.append([
            "Acid Sulfate Soils Management Plan",
            f"ASS Class {controls['ass_class']} — earthworks or drainage works",
            "$3,000–15,000",
            "2–6 weeks",
        ])

    c_cols = [62 * mm, 52 * mm, 22 * mm, CW - 136 * mm]  # last col = 38mm — fits "5–10 business days"
    _hdr_style = S("th", fontSize=7.5, textColor=WHITE, fontName="Helvetica-Bold", leading=11)
    _cons_data = []
    for ri, row in enumerate(_consultant_rows):
        if ri == 0:
            _cons_data.append([Paragraph(str(cell), _hdr_style) for cell in row])
        else:
            _cons_data.append([
                Paragraph(str(cell), ss["body"] if ci == 0 else ss["note"])
                for ci, cell in enumerate(row)
            ])
    _cons_tbl = Table(_cons_data, colWidths=c_cols)
    _cons_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 7.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, colors.HexColor("#F3F4F6")]),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(_cons_tbl)
    story.append(Spacer(1, 1 * mm))
    story.append(Paragraph(
        "Costs and lead times are indicative ranges only. Reports may be required as conditions "
        "of consent — buyer to confirm with a town planner before exchange if development is intended.",
        ss["note"]
    ))

    # ------------------------------------------------------------------
    # SECTION 6 — Nearby Development Activity
    # ------------------------------------------------------------------
    h2("9. Nearby Development Activity (200m, 12 months)")

    if das:
        da_rows = [["DA Number", "Dist.", "Lodged", "Status", "Description"]]
        for da in das:
            da_rows.append([
                da["number"],
                f"{da['distance_m']}m",
                da["lodged"],
                da["status"],
                Paragraph(da["description"], ss["body"]),
            ])
        story.append(table(da_rows, [38 * mm, 16 * mm, 22 * mm, 28 * mm, CW - 104 * mm]))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            f"{len(das)} development application(s) lodged within 200m in the past 12 months. "
            "Review descriptions above for potential amenity, overshadowing or construction impacts.",
            ss["note"]
        ))
    else:
        story.append(Paragraph(
            "No development applications lodged within 200m in the past 12 months. "
            "Low immediate construction disruption risk from neighbouring properties.",
            ss["ok"]
        ))

    # ------------------------------------------------------------------
    # SECTION 8 — Disclosure Notes
    # ------------------------------------------------------------------
    h2("10. Disclosure Notes")

    notes = [
        ("s10.7 Planning Certificate",
         "This report is <b>NOT a substitute</b> for a <b>Section 10.7 Planning Certificate</b> issued under the "
         "Environmental Planning and Assessment Act 1979. A s10.7(5) certificate from council is the "
         "<b>authoritative statutory disclosure document</b> for conveyancing. This report <b>supplements — "
         "it does not replace</b> — that certificate."),
        ("Environmental and spatial overlays",
         "<b>Biodiversity, riparian, wetlands, landslide, flood, bushfire prone land (BFPL), aircraft noise "
         "(ANEF), TOD precinct status,</b> and Additional Permitted Uses data are sourced from PostGIS spatial "
         "overlays ingested from NSW Government ArcGIS services (128 NSW councils). "
         "<b>None of these layers appear in a standard s10.7(2) certificate or title search.</b> "
         "Data reflects the last ingestion date — accuracy is subject to NSW Government mapping precision. "
         "Verify with council for site-specific confirmation."),
        ("Title classification",
         "<b>Strata and community title</b> identification sourced from NSW Planning Portal cadastral data. "
         "<b>Company title</b> properties return as Torrens in the land register and <b>may not be automatically "
         "identified</b> — confirm via title search for older inner Sydney apartment buildings."),
        ("DCP provisions",
         f"DCP setback controls are currently available for: <b>Inner West LGA</b> (Marrickville, Leichhardt, "
         f"Ashfield precincts). For all other councils, Section 4 of this report is not populated — "
         f"obtain DCP controls directly from council or via a town planning consultant."),
        ("Permitted and prohibited uses",
         "Zone permitted and prohibited uses are derived from the <b>NSW Planning Portal LEP Land Use</b> "
         "field, which follows the standard instrument LEP format across all NSW councils. "
         "Uses are parsed from the authoritative portal response — not from a static lookup. "
         "Always verify the current LEP land use table via the <b>legislation link</b> provided."),
        ("Data sources and currency",
         f"<b>NSW Planning Portal:</b> live query as at {date.today().strftime('%d %B %Y')}. "
         "<b>NSW Valuation Service</b> land values: most recently published base date (shown in report). "
         "<b>PostGIS spatial overlays:</b> last ingestion from NSW Government ArcGIS services. "
         "<b>DA activity:</b> NSW ePlanning Portal API, past 12 months. "
         "No representation is made as to the completeness or accuracy of any data source."),
        ("Shadow risk methodology",
         "Northern development shadow risk is modelled using the <b>maximum permissible building height "
         "(Height of Buildings, HOB)</b> from the applicable Local Environmental Plan. HOB is the LEP "
         "control that sets the tallest structure a neighbour could legally build — <b>it is not the "
         "height of any existing building.</b> The model tests whether a worst-case neighbour build at "
         "the HOB limit would shadow this property on the <b>NSW Apartment Design Guide (ADG)</b> test dates "
         "(21 June winter solstice, 9 am / 12 pm / 3 pm). ADG compliance requires <b>at least 2 hours "
         "of direct sunlight between 9 am and 3 pm on 21 June</b> for living areas and private open space. "
         "This is a <b>conservative envelope model</b> — not a site-specific shadow study. A formal shadow "
         "impact assessment by a qualified architect is required for DA submission."),
        ("Infrastructure contributions (S7.11 / S7.12)",
         "This report <b>does not include infrastructure contribution liability estimates.</b> "
         "Development applications for new dwellings or subdivision require a <b>Section 7.11 or 7.12 "
         "Contributions Plan levy</b> — typically <b>$10,000–$50,000+ per dwelling</b> in Greater Sydney. "
         "Contribution rates must be confirmed directly with the relevant council's contributions "
         "plan before any development feasibility assessment can be relied upon."),
        ("Easements and covenants on title",
         "This report <b>does not assess easements, covenants, restrictions on use,</b> or positive "
         "covenants registered on the title. A <b>stormwater easement, drainage reserve,</b> or "
         "positive covenant can <b>significantly affect the buildable area</b> on a lot — in some cases "
         "more than any planning control. "
         "These are disclosed in the <b>title search (DP plan diagram)</b> and must be reviewed "
         "before any development feasibility assessment. Obtain a <b>full title search</b> and review "
         "the deposited plan before exchange."),
        ("Existing floor area and building footprint",
         "<b>FSR headroom calculations</b> in this report are based on the LEP maximum FSR applied to lot area. "
         "They <b>do not account for the gross floor area (GFA) of existing buildings</b> on the lot. "
         "Actual development potential depends on existing GFA — which must be calculated from "
         "building plans, approved DAs, or a building surveyor's assessment. "
         "<b>Do not use FSR data as a standalone feasibility basis</b> without first quantifying existing GFA."),
        ("Liability",
         "This report provides <b>planning intelligence for due diligence review only.</b> "
         "It <b>does not constitute planning, legal, environmental or conveyancing advice.</b> "
         "Do not rely on this report as the sole basis for any decision to enter into a contract "
         "or proceed with a transaction. <b>Independent professional advice should be obtained</b> as "
         "appropriate for each matter. To the maximum extent permitted by law, the report "
         "provider <b>accepts no liability</b> for any loss or damage arising from reliance on this report."),
    ]
    for heading, body in notes:
        story.append(Paragraph(f"<b>{heading}:</b> {body}", ss["body"]))
        story.append(Spacer(1, 2 * mm))

    story.append(Spacer(1, 4 * mm))

    # Bulk teaser callout
    bulk_tbl = Table(
        [[Paragraph(
            "<b>Running a settlement pipeline?</b>  These reports can be generated in bulk for your current "
            "matters — one request covers your entire pipeline. Contact "
            "<font color='#1E5FAD'>info@plotdetect.com.au</font> to discuss.",
            S("bt", fontSize=8, textColor=colors.HexColor("#1E3A5F"), leading=12)
        )]],
        colWidths=[CW]
    )
    bulk_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
        ("BOX",           (0, 0), (-1, -1), 0.5, NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(bulk_tbl)

    story.append(Spacer(1, 3 * mm))
    hr()
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        f"PlotDetect — NSW Property Intelligence  |  "
        f"Report generated {datetime.now().strftime('%Y-%m-%d %H:%M')} AEST",
        ss["caveat"]
    ))

    def _footer(canvas, doc_obj):
        canvas.saveState()
        page_w, _ = A4
        footer_y = 10 * mm
        canvas.setFillColor(BORDER)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(MARGIN, footer_y,
            f"PlotDetect — NSW Property Intelligence  ·  {address}")
        canvas.drawRightString(page_w - MARGIN, footer_y,
            f"Page {doc_obj.page}")
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.4)
        canvas.line(MARGIN, footer_y + 3.5 * mm, page_w - MARGIN, footer_y + 3.5 * mm)
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    print(f"\n  PDF written: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="PlotDetect conveyancing planning report")
    parser.add_argument("--address", required=True, help="Full property address")
    parser.add_argument("--lat", type=float, help="Latitude (geocoded if omitted)")
    parser.add_argument("--lng", type=float, help="Longitude (geocoded if omitted)")
    parser.add_argument("--council", default="",
                        help="Council name for DA search (auto-derived from LEP if omitted)")
    parser.add_argument("--output", default=str(project_root / "reports" / "conveyancing" / "verify_report.pdf"), help="Output PDF path")
    parser.add_argument("--no-pdf", action="store_true", help="Print data only")
    args = parser.parse_args()

    print(f"\n=== PlotDetect Conveyancing Report ===")
    print(f"Address: {args.address}")

    print("\nResolving address ...")
    prop_id, resolved_lat, resolved_lng, lot_wkt = resolve_address(args.address)

    lat = args.lat if args.lat else resolved_lat
    lng = args.lng if args.lng else resolved_lng
    if args.lat or args.lng:
        lot_wkt = None  # manual coords — lot polygon unknown

    if not lat or not lng:
        print("  ERROR: could not derive coordinates — check the address or provide --lat and --lng")
        sys.exit(1)

    print(f"  {lat:.6f}, {lng:.6f}")

    print("\nFetching LEP controls from NSW Planning Portal ...")
    controls = {}
    valuation = {"lot_area_m2": None, "land_value": None}
    if prop_id:
        print(f"  propId: {prop_id}")
        raw = get_raw_controls(prop_id)
        controls = parse_controls(raw)
        print(f"  Zone: {controls.get('zone')}  Height: {controls.get('height')}  FSR: {controls.get('fsr')}")
        print(f"  ASS: {controls.get('ass_class')}  Heritage items: {len(controls.get('heritage_items') or [])}")
        print(f"  SEPP overlays: {len(controls.get('sepp_overlays') or [])}")
        print(f"  Key sites: {controls.get('key_sites_clause')}")
        print("\nFetching valuation data ...")
        valuation = get_valuation(prop_id)
        print(f"  Lot area: {valuation.get('lot_area_m2')} m²  Land value: {valuation.get('land_value')}")
    else:
        print("  WARN: no propId — controls will be empty")
        controls = parse_controls([])

    headroom = calc_development_headroom(controls, valuation)

    print("\nQuerying PostGIS for unique overlays (biodiversity, riparian, wetlands, landslide, flood) ...")
    unique_overlays, covered_layers, proximity_m = get_unique_overlays(lat, lng, lot_wkt=lot_wkt)
    if lot_wkt:
        print("  (using lot polygon — partial overlays detected)")
    else:
        print("  (using centroid point — lot polygon unavailable)")
    if unique_overlays:
        for ov in unique_overlays:
            print(f"  {ov['layer_type']:15s} {ov['value'] or 'present'}")
    else:
        print("  None found at this location")

    # PostGIS fallbacks — use spatial data when Planning Portal returned nothing
    _ov_by_type = {o["layer_type"]: o for o in unique_overlays}
    if not controls.get("ass_class") and "acid_sulfate" in _ov_by_type:
        controls["ass_class"] = _ov_by_type["acid_sulfate"].get("value") or "Present"
        print(f"  [PostGIS fallback] acid_sulfate → ass_class={controls['ass_class']}")
    if not controls.get("lot_size") and "lot_size" in _ov_by_type:
        controls["lot_size"] = _ov_by_type["lot_size"].get("value")
        controls["lot_size_units"] = "m²"
        print(f"  [PostGIS fallback] lot_size → {controls['lot_size']}")

    print("\nDetecting title type ...")
    strata_info = detect_strata(args.address, lat, lng)
    strata = strata_info["is_strata"]
    if strata:
        sp = strata_info.get("strata_plan") or "detected"
        src = strata_info["source"]
        print(f"  Strata lot: {sp} (source: {src}) — feasibility gated")
    elif strata_info.get("parent_has_strata"):
        print(f"  Torrens title — but strata scheme exists on this parcel ({strata_info.get('plan_label')})")
    else:
        print(f"  Torrens title — {strata_info.get('plan_label', 'plan unknown')}")
    feasibility = calc_feasibility(controls, valuation, unique_overlays, is_strata=strata)

    raw_council = args.council or _council_from_zone_epi(controls.get("zone_epi", ""))
    council_name = _normalise_council(raw_council) if args.council else raw_council
    if council_name:
        print(f"\nFetching nearby DAs (council: {council_name}) ...")
        das = get_nearby_das(lat, lng, council_name=council_name)
    else:
        print("\nSkipping DA search — council could not be derived from LEP")
        das = []
    print(f"  {len(das)} DAs within 200m")

    # Detect Inner West former council for DCP setback lookup
    zone_epi = controls.get("zone_epi", "") if controls else ""
    dcp_former_council = detect_former_council(args.address, zone_epi)
    if dcp_former_council:
        print(f"  DCP controls: lga_slug={dcp_former_council}")
    else:
        print("  DCP controls: not available for this LGA")

    # Pre-fetch DB data (single connection, closed before PDF render)
    lep_clauses: list = []
    dcp_setbacks_db: Optional[dict] = None
    postgis_heritage: dict = {"hca": [], "items": [], "has_heritage": False, "raw": []}
    _db_url = os.getenv("DATABASE_URL")
    if _db_url and lat and lng:
        try:
            _db_conn = psycopg2.connect(_db_url)
            key_sites_clause = (controls or {}).get("key_sites_clause")
            epi_name = (controls or {}).get("zone_epi") or ""
            prop_zone_for_fetch = (controls or {}).get("zone") or ""
            # Only fetch LEP clauses and DCP setbacks when there's something to look up
            if key_sites_clause:
                lep_clauses = fetch_lep_clauses(_db_conn, key_sites_clause, epi_name)
            if dcp_former_council:
                dcp_setbacks_db = fetch_dcp_setbacks(_db_conn, dcp_former_council, prop_zone_for_fetch)
            # Heritage: always fetch (applies to all LGAs, data now populated)
            postgis_heritage = fetch_heritage_postgis(_db_conn, lat, lng, lot_wkt=lot_wkt)
            _db_conn.close()
            if dcp_setbacks_db:
                _dh = len(dcp_setbacks_db['setbacks']); _sd = len(dcp_setbacks_db.get('sd_setbacks') or [])
                print(f"  DCP setbacks: {_dh} DH + {_sd} SD rows from DB")
            if lep_clauses:
                print(f"  LEP clauses: {len(lep_clauses)} rows")
            if postgis_heritage["has_heritage"]:
                hca_n = len(postgis_heritage["hca"])
                item_n = len(postgis_heritage["items"])
                print(f"  Heritage (PostGIS): {hca_n} HCA, {item_n} item(s)")
            else:
                print("  Heritage (PostGIS): clear")
        except Exception as _e:
            print(f"  [warn] DB pre-fetch failed: {_e}")
    elif not _db_url:
        print("  [warn] DATABASE_URL not set — DB lookups skipped")

    # Merge PostGIS heritage into controls (reliable spatial classification)
    # Portal Heritage Significance field is fragile; PostGIS value field is authoritative
    if postgis_heritage["hca"]:
        if controls.get("heritage_items") and not controls.get("heritage_hca"):
            # Portal found items but didn't classify as HCA — PostGIS corrects this
            controls["heritage_hca"] = controls["heritage_items"][:]
        elif not controls.get("heritage_hca"):
            # Portal found nothing — use PostGIS description as display text
            controls.setdefault("heritage_items", []).extend(postgis_heritage["hca"])
            controls["heritage_hca"] = postgis_heritage["hca"][:]
    elif postgis_heritage["items"] and not controls.get("heritage_items"):
        # PostGIS found individual items portal missed
        controls["heritage_items"] = postgis_heritage["items"][:]

    shadow_result = None
    if prop_id and lat and lng:
        print("\nRunning shadow risk model ...")
        # Parse LEP height from controls (e.g. "9.5" or "9.5m") and pass to pipeline
        lep_height: Optional[float] = None
        raw_h = controls.get("height")
        if raw_h:
            import re as _re
            m = _re.search(r"(\d+(?:\.\d+)?)", str(raw_h))
            if m:
                lep_height = float(m.group(1))
        shadow_result = get_shadow_risk(args.address, prop_id, lat, lng, height_m=lep_height)
        if shadow_result:
            adg = "ADG concern" if not shadow_result.get("adg_compliant") else "ADG compliant"
            print(f"  {adg}  height: {shadow_result.get('height_m')} m")
        else:
            print("  Shadow model unavailable — section omitted from PDF")

    if not args.no_pdf:
        print(f"\nGenerating PDF -> {args.output}")
        generate_pdf(
            args.output, args.address, lat, lng, controls, valuation,
            headroom, feasibility, unique_overlays, das,
            dcp_former_council=dcp_former_council,
            strata_info=strata_info,
            covered_layers=covered_layers,
            shadow_result=shadow_result,
            lep_clauses=lep_clauses,
            dcp_setbacks_db=dcp_setbacks_db,
            proximity_m=proximity_m,
        )


if __name__ == "__main__":
    main()
