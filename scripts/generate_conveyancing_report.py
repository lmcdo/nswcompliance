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
import logging
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

logger = logging.getLogger(__name__)

# DB helpers — pre-fetched before generate_pdf (no DB connection inside renderer)
sys.path.insert(0, str(Path(__file__).parent))
from conveyancing_db import clause_or_page, fetch_dcp_setbacks, fetch_heritage_postgis, fetch_lep_clauses, interpret_sepp, load_regulatory_configs  # noqa: E402
from services.address_identity import parcel_identity_match  # noqa: E402  GATE-0

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PORTAL_BASE = "https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi"
PORTAL_HEADERS = {
    "Origin": "https://www.planningportal.nsw.gov.au",
    "Referer": "https://www.planningportal.nsw.gov.au/",
    "User-Agent": "Mozilla/5.0",
}
# prior-art-checked: reuse not viable because the existing cadastre/property
# fetchers are all frontend TypeScript (nsw-planning-portal.ts, spatial-boundary-
# service.ts, app/api/property/*) and the existing Python point queries
# (portal_constraints.py, strata_lookup.py) return overlays/strata, NOT a propId.
# This is the only Python coordinate->propId resolver; it sits next to the text
# resolve_address so both share _portal_get/_lot_centroid_wkt/parcel_identity_match.
# NSW cadastre "Property" layer — point-in-polygon returns the propId that matches
# the Planning Portal, plus the parcel's cadastre address for the GATE-0 check.
PROPERTY_LAYER_URL = (
    "https://portal.spatial.nsw.gov.au/server/rest/services/"
    "NSW_Land_Parcel_Property_Theme/FeatureServer/12/query"
)
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

# Split so the value-known variant (build_anef_note) reuses the liability-audited
# AS 2021 / TI-SEPP wording verbatim; ANEF_NOTE itself is byte-identical to the
# pre-split constant (golden fallback for when no contour value resolves).
_ANEF_NOTE_BASE = (
    "Aircraft Noise Contour — this property falls within an Australian Noise Exposure "
    "Forecast (ANEF) contour. Under SEPP (Transport and Infrastructure) 2021 and AS 2021, "
    "residential development within ANEF contours may require acoustic attenuation design "
    "and an acoustic report from an accredited acoustic consultant. "
)
ANEF_NOTE = _ANEF_NOTE_BASE + (
    "The specific restrictions "
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

# source_ref: SEPP (Transport and Infrastructure) 2021 s2.120 (development with
# frontage to a classified road — consent authority considerations); Codes SEPP
# (Exempt and Complying Development Codes) 2008 Housing Code (classified road
# setback for complying development). The 9 m figure is a Codes SEPP CDC
# standard — it is NOT a TI SEPP or Housing SEPP control (D5).
CLASSIFIED_ROAD_NOTE = (
    "Classified Road Frontage — this lot adjoins a classified road. Under SEPP (Transport and "
    "Infrastructure) 2021 s2.120, development with frontage to a classified road requires the "
    "consent authority to be satisfied on access arrangements and road safety. Under the Codes "
    "SEPP Housing Code, complying development for a dwelling house is subject to a 9 m setback "
    "from the classified road boundary. Confirm the applicable pathway and setback with a "
    "certifier or town planner."
)

# Land tax: NO hardcoded fallback. The only source is the tax_thresholds table
# (migration 046) — a fallback constant IS a hardcoded regulatory value, and it
# rendered silently-stale figures in a legal document (PR #674 D1/D3 defect
# class). When no config is injected the section renders "Not assessed".

# Secondary dwelling SEPP fallback constants intentionally removed (#684) —
# same defect class as the land-tax fallback above. Authoritative source:
# housing_sepp_standards table (migration 045); when no config is injected the
# secondary-dwelling row renders "Not assessed".

# Display labels for CDC screen constraint keys (#820) — presentation only,
# never regulatory data: the verdicts and figures come from the engine.
_CDC_CONSTRAINT_LABELS = {
    "zone": "zone",
    "lot_size": "lot size",
    "heritage": "heritage",
    "flood": "flood risk",
    "bushfire": "bushfire risk",
    "acid_sulfate": "acid sulfate soils",
    "complying_exclusion": "mapped exclusion area",
    "dual_occ_prohibition": "dual-occupancy prohibition",
    "contamination": "contaminated land",
}

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
    # Special case: the City of Sydney's instrument is "Sydney LEP", so the slug
    # derived from the EPI name ("sydney") does not equal the DCP slug. Map it explicitly.
    "SYDNEY LOCAL ENVIRONMENTAL PLAN":               "city_of_sydney",
    # All other onboarded LGAs are resolved generically: detect_former_council derives the
    # slug from the EPI name and accepts it only if it is in DCP_ONBOARDED_SLUGS (below).
}

# LGAs whose DCP setback data in dcp_setback_controls is complete and current enough to
# use in the brief. Verified 2026-06-19 (all rows is_current, needs_review=0, control-type
# and dev-type coverage at parity with the LGAs that were already mapped). This is the
# completeness gate: an LGA's setbacks only go live once its slug is listed here, so a
# partially-extracted council cannot leak into the brief. The matching EPI string is not
# hand-maintained — _slug_from_epi() derives the slug from the portal's EPI name and is
# validated against this set. Add a slug here when onboarding a new LGA's DCP data.
# nsw_statewide is deliberately excluded: it is a fallback layer, not an address-resolvable EPI.
DCP_ONBOARDED_SLUGS: frozenset[str] = frozenset({
    "ashfield", "bayside", "blacktown", "burwood", "camden", "campbelltown",
    "canada_bay", "canterbury_bankstown", "city_of_sydney", "cumberland", "fairfield",
    "georges_river", "hornsby", "inner_west", "ku_ring_gai", "leichhardt", "liverpool",
    "marrickville", "northern_beaches", "parramatta", "penrith", "randwick", "ryde",
    "strathfield", "sutherland_shire", "the_hills", "waverley", "woollahra",
    # Wingecarribee: numeric controls from the Bowral/Mittagong/Moss Vale town
    # plans (identical Part C template, Phase-0 verified) — see
    # scripts/insert_wingecarribee_setbacks.py.
    "wingecarribee",
})

# Suburb → former-council slug (Inner West LGA post-2016 amalgamation).
# Used only when ZONE_EPI_TO_LGA_SLUG returns "inner_west".
SUBURB_TO_FORMER_COUNCIL: dict[str, str] = {
    # Marrickville precincts
    "marrickville": "marrickville", "sydenham": "marrickville", "tempe": "marrickville",
    "dulwich hill": "marrickville", "enmore": "marrickville",
    "petersham": "marrickville", "lewisham": "marrickville",
    # Boundary suburbs (partially IW, partially City of Sydney) — removed from
    # text matching to prevent misclassification.  PostGIS cross-validation in
    # conveyancing.py resolves these via geometry instead.
    # Removed: glebe (City of Sydney), alexandria (City of Sydney),
    #          erskineville (City of Sydney), camperdown (split IW / CoS),
    #          stanmore (split IW / CoS), newtown (split IW / CoS),
    #          st peters (split IW / CoS)
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


# prior-art-checked: not a new capability — refactor of the existing cadastre query
# in THIS file (extracted helper + containment flag) to fix strata misdetection.
def _query_cadastre_lots(lat: float, lng: float, buffer_m: int = 0) -> list[dict]:
    """Return attribute dicts for cadastre lots at (or within ``buffer_m`` of) a point.

    ``buffer_m=0`` is a strict point-in-polygon query: only lots whose geometry
    contains the point are returned.
    """
    import json as _json
    params = {
        "geometry": _json.dumps({"x": lng, "y": lat, "spatialReference": {"wkid": 4283}}),
        "geometryType": "esriGeometryPoint",
        "inSR": "4283",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "plannumber,planlabel,lotnumber,sectionnumber,classsubtype,hasstratum",
        "returnGeometry": "false",
        "f": "json",
    }
    if buffer_m:
        params["distance"] = buffer_m
        params["units"] = "esriSRUnit_Meter"
    r = requests.get(CADASTRE_URL, params=params, timeout=10)
    r.raise_for_status()
    features = r.json().get("features") or []
    return [f["attributes"] for f in features]


def get_cadastral_info(lat: float, lng: float) -> dict:
    """
    Query NSW Cadastre (maps.six.nsw.gov.au) for the lot at lat/lng.

    Point-in-polygon first: only lots that CONTAIN the point are classified. A
    20 m buffer is used solely as a fallback when the point lands in no lot
    (imprecise geocode on a road/verge). The old always-20 m buffer captured
    neighbouring strata schemes and misreported adjacent Torrens lots as strata
    (38 Park Rd Bowral: DP lot correct at 0 m, neighbour's SP returned at 20 m).

    Returns:
        is_strata        bool   — True if an SP/CP lot (classsubtype 3/4) was found
        strata_plan      str    — "SP56913" if strata found, else None
        parent_has_strata bool  — True if any returned lot has hasstratum=2
        plan_label       str    — planlabel of primary lot (e.g. "DP605756")
        lot_number       str    — lotnumber of primary lot
        containment      bool   — True if the lots CONTAIN the point (authoritative);
                                  False if they only came from the 20 m fallback buffer
    """
    try:
        containment = True
        attrs_list = _query_cadastre_lots(lat, lng, buffer_m=0)
        if not attrs_list:
            # Point hit no lot polygon — geocode likely on road/water. Widen the
            # search, but flag the result as non-containing so callers do not
            # treat a neighbouring lot as authoritative.
            containment = False
            attrs_list = _query_cadastre_lots(lat, lng, buffer_m=20)

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
            top = sp_lots[0]
            plan = top.get("planlabel") or ""
            # classsubtype 4 = community-title lot (Community Land Development Act).
            # Derive plan_type from classsubtype, not the planlabel prefix alone — a
            # community lot can carry a DP-style label, and the CP-prefix-only rule
            # mislabelled it "strata", burying a developable lot in the AMBIGUOUS band
            # (capacity card hidden). classify_strata routes community -> DEVELOPMENT
            # (ground-level subdivision), so this only un-hides genuine developable
            # lots; classsubtype 3 (true strata) is unchanged and never promoted.
            is_community = top.get("classsubtype") == 4 or str(plan).startswith("CP")
            plan_type = "community" if is_community else "strata"
            return {
                "is_strata": True,
                "strata_plan": plan,
                "plan_type": plan_type,       # "strata" | "community"
                "parent_has_strata": True,
                "plan_label": plan,
                "lot_number": sp_lots[0].get("lotnumber"),
                "section_number": sp_lots[0].get("sectionnumber"),
                "containment": containment,
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
                "section_number": primary.get("sectionnumber"),
                "containment": containment,
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
        "section_number": None,
        "containment": False,
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
      SP/CP lot CONTAINS the point       -> strata (source: cadastre)
      SP/CP lot in 20m fallback + addr A -> strata (source: combined) — the
        point itself hit no lot, so a nearby SP alone is NOT proof: it may be
        the neighbour's scheme (38 Park Rd Bowral was misreported this way)
      SP/CP lot in 20m fallback alone    -> ambiguous — treated as parent_has_strata
      parent_has_strata=True + addr A    -> strata (source: combined)
      parent_has_strata=True alone       -> ambiguous — note in report
      addr A alone (no cadastre result)  -> strata likely (heuristic fallback)
    """
    addr_unit = _addr_has_unit_prefix(address)

    if lat is not None and lng is not None:
        cad = get_cadastral_info(lat, lng)

        # Definitive: SP/CP lot found in cadastre, containing the point
        if cad["is_strata"] and cad.get("containment", True):
            return {
                "is_strata": True,
                "strata_plan": cad["strata_plan"],
                "plan_type": cad.get("plan_type", "strata"),
                "source": "cadastre",
                "parent_has_strata": True,
                "plan_label": cad["plan_label"],
                "lot_number": cad.get("lot_number"),
                "section_number": cad.get("section_number"),
            }

        # SP/CP lot only within the fallback buffer (point contained in no lot):
        # confirm only with the corroborating unit-style address; otherwise
        # downgrade to the ambiguous parent_has_strata path below.
        if cad["is_strata"] and not cad.get("containment", True):
            if addr_unit:
                return {
                    "is_strata": True,
                    "strata_plan": cad["strata_plan"],
                    "plan_type": cad.get("plan_type", "strata"),
                    "source": "cadastre+address",
                    "parent_has_strata": True,
                    "plan_label": cad["plan_label"],
                "lot_number": cad.get("lot_number"),
                "section_number": cad.get("section_number"),
                }
            return {
                "is_strata": False,
                "strata_plan": None,
                "plan_type": None,
                "source": "cadastre",
                "parent_has_strata": True,
                "plan_label": cad["plan_label"],
                "lot_number": cad.get("lot_number"),
                "section_number": cad.get("section_number"),
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
                "lot_number": cad.get("lot_number"),
                "section_number": cad.get("section_number"),
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
                "lot_number": cad.get("lot_number"),
                "section_number": cad.get("section_number"),
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
                "lot_number": cad.get("lot_number"),
                "section_number": cad.get("section_number"),
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
                "lot_number": cad.get("lot_number"),
                "section_number": cad.get("section_number"),
            }

    # Fallback: address heuristic only — could be strata or company title
    return {
        "is_strata": addr_unit,
        "strata_plan": None,
        "plan_type": "strata_or_company" if addr_unit else None,
        "source": "address_heuristic",
        "parent_has_strata": False,
        "plan_label": None,
        "lot_number": None,
        "section_number": None,
    }


def _slug_from_epi(zone_epi: str) -> Optional[str]:
    """Derive an LGA slug from a Standard Instrument EPI name.

    "Canada Bay Local Environmental Plan 2013" -> "canada_bay"
    "Sutherland Shire LEP 2015"                -> "sutherland_shire"

    Strips the instrument-type phrase and trailing year, then slugifies the council
    name. Returns None if no instrument phrase is present (so a non-LEP string cannot
    accidentally resolve). The result is only trusted when it is in DCP_ONBOARDED_SLUGS.
    """
    s = (zone_epi or "").upper()
    cut = -1
    for marker in ("LOCAL ENVIRONMENTAL PLAN", " LEP"):
        idx = s.find(marker)
        if idx > 0:
            cut = idx
            break
    if cut < 0:
        return None
    name = s[:cut].strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
    return slug or None


def detect_former_council(address: str, zone_epi: str = "") -> Optional[str]:
    """Return lga slug for dcp_setback_controls, or None if LGA not yet onboarded.

    Resolution order:
    1. ZONE_EPI_TO_LGA_SLUG — explicit overrides + special cases (Inner West, City of Sydney).
    2. Generic: derive the slug from the EPI name and accept it only if it is in
       DCP_ONBOARDED_SLUGS (the curated completeness gate). This covers every onboarded
       LGA without a hand-maintained EPI string per council.
    - No match → None (LGA not yet onboarded for DCP setbacks)
    - Inner West → suburb disambiguation returns marrickville / leichhardt / ashfield

    To onboard a new LGA, add its slug to DCP_ONBOARDED_SLUGS (special EPI names only
    need an entry in ZONE_EPI_TO_LGA_SLUG).
    """
    epi_upper = zone_epi.upper()
    slug = None
    for epi_key, lga_slug in ZONE_EPI_TO_LGA_SLUG.items():
        if epi_key in epi_upper or epi_upper in epi_key:
            slug = lga_slug
            break
    if not slug:
        derived = _slug_from_epi(zone_epi)
        if derived and derived in DCP_ONBOARDED_SLUGS:
            slug = derived
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
                     tax_config: Optional[dict] = None,
                     cdc_result=None) -> list[dict]:
    """
    Answer the questions buyers actually ask their conveyancer.
    Returns list of {question, answer, flag (ok/warn/alert), basis}.

    sepp_standards: pre-loaded from housing_sepp_standards table. Keys:
        sd_min_lot (float), sd_zones (set[str]).
        NO fallback: when absent the secondary-dwelling row renders
        "Not assessed" — a stale or hardcoded regulatory figure never
        renders silently (#684, same rule as tax_config below).
    tax_config: pre-loaded from tax_thresholds table. Keys:
        tax_year, threshold_dollars, rate, base_amount_dollars.
        NO fallback: when absent the land-tax section renders "Not assessed"
        — a stale or hardcoded regulatory figure never renders silently.
    cdc_result: a services.cdc_screen.CdcScreenResult run by the caller
        (#820 PR-2) — the CDC row renders from the engine's verdict, which is
        driven by founder-reviewed cdc_eligibility_standards rows. NO fallback:
        when None the CDC row renders "Not assessed"; the row never screens
        against the secondary-dwelling zone set again.
    """
    results = []
    lot_area = valuation.get("lot_area_m2")
    _zone_parts = (controls.get("zone") or "").split()
    zone = _zone_parts[0].upper() if _zone_parts else ""

    # 1. Secondary dwelling (granny flat)
    # Source: the per-path CDC/DA rules in housing_sepp_standards (migrations
    # 083/084), answered by services/secondary_dwelling_paths.assess(). The SEPP
    # (Housing) 2021 sets no single minimum lot size for a granny flat, so lot
    # area alone never makes this row "too small". NO fallback (#684): absent or
    # invalid rules render "Not assessed" -- fail-visible, never a figure.
    _sd_rules = (sepp_standards or {}).get("sd_rules")
    # services/ is always importable here: line 51 imports services.address_identity.
    from services.secondary_dwelling_paths import Rules as _SdRules, assess as _sd_assess
    if not isinstance(_sd_rules, _SdRules):
        # A direct caller injecting anything but validate_rules() output gets the
        # fail-visible row, never a crash mid-report (cross-review).
        _sd_rules = None
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
    elif _sd_rules is None:
        print("  [warn] calc_feasibility: SEPP Housing granny-flat rules unavailable — secondary dwelling renders 'Not assessed'")
        results.append({
            "question": "Secondary dwelling (granny flat)",
            "answer": "Not assessed",
            "flag": "warn",
            "basis": (
                "The SEPP (Housing) 2021 secondary-dwelling rules (the CDC road-frontage bands "
                "and the DA site-area standard) were unavailable at report generation, so no "
                "lot-area outcome is stated. Obtain the current Chapter 3 rules from the SEPP "
                "(Housing) 2021 or council before relying on secondary-dwelling potential."
            )
        })
    elif lot_area is None:
        results.append({
            "question": "Secondary dwelling (granny flat)",
            "answer": "Lot area unavailable",
            "flag": "warn",
            "basis": (
                "Lot area data not available from NSW Valuation Service. The CDC road-frontage "
                "band (SEPP (Housing) 2021 Schedule 1 cl 2(1)(b)) and the DA site-area standard "
                "for a detached granny flat (s 53(2)(a)) both depend on lot area. Confirm lot "
                "dimensions with council or a surveyor."
            )
        })
    else:
        _paths = _sd_assess(_sd_rules, zone, lot_area)
        _outside = (_paths["cdc"]["outcome"] == "NOT_APPLICABLE"  # noqa: bracket-access — assess() always sets both
                    and _paths["da"]["outcome"] == "NOT_APPLICABLE"  # noqa: bracket-access
                    and "outside this path's zones" in (_paths["da"].get("reason") or ""))  # noqa: bracket-access
        results.append({
            "question": "Secondary dwelling (granny flat)",
            "answer": ("Outside the SEPP granny-flat zones" if _outside
                       else "Depends on approval path — not ruled out by lot area"),
            "flag": "warn",
            "basis": (
                _paths["summary"]  # noqa: bracket-access — assess() always sets it
                + (" A council LEP can separately permit secondary dwellings — check the zone's "
                   "land-use table." if _outside else
                   " Subject to DCP setback and height controls.")
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
    elif lot_area is None and not is_strata:
        results.append({
            "question": "Torrens title subdivision",
            "answer": "Lot area unavailable",
            "flag": "warn",
            "basis": (
                "Lot area data not available from NSW Valuation Service. "
                "Subdivision feasibility requires comparison against LEP minimum lot size. "
                "Confirm lot dimensions with council or a surveyor."
            )
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
    elif cdc_result is None:
        # Screen unavailable (#820): standards unverified or DB unreachable —
        # fail visible, never a zone-list guess. The old secondary-dwelling
        # zone screen is gone for good.
        results.append({
            "question": "Complying Development Certificate (CDC)",
            "answer": "Not assessed",
            "flag": "warn",
            "basis": (
                "The complying-development screening standards were unavailable at "
                "report generation, so the CDC pathway was not evaluated. Confirm CDC "
                "availability with a certifier."
            )
        })
    else:
        # Render the engine's verdict (services/cdc_screen.py): exclusions are
        # clause-cited from cdc_eligibility_standards; the engine never says
        # "yes", so this row never claims eligibility either.
        _definite = [e for e in cdc_result.exclusions if e.severity == "definite"]
        _likely = [e for e in cdc_result.exclusions if e.severity == "likely"]
        _notes = [f"{e.reason} ({e.source})." for e in _definite + _likely]
        _notes.extend(cdc_result.warnings)   # includes the not-screened summary
        _labels = lambda excs: ", ".join(dict.fromkeys(  # noqa: E731
            _CDC_CONSTRAINT_LABELS.get(e.constraint, e.constraint.replace("_", " "))
            for e in excs))
        # Scope honesty (Sol review of #829): the standards screened are the
        # Housing Code's — a negative here must not rule out other complying-
        # development codes the screen never assessed.
        _scope_note = (
            " This screen assesses the Housing Code standards; other complying "
            "development pathways were not assessed — a certifier can determine "
            "the available approval pathway."
        )
        if cdc_result.eligible == "no":
            results.append({
                "question": "Complying Development Certificate (CDC)",
                "answer": f"Excluded (Housing Code) — {_labels(_definite)}",
                "flag": "alert",
                "basis": " ".join(_notes) + _scope_note
            })
        elif _likely:
            results.append({
                "question": "Complying Development Certificate (CDC)",
                "answer": f"Restricted — {_labels(_likely)}",
                "flag": "warn",
                "basis": " ".join(_notes) + _scope_note
            })
        else:
            results.append({
                "question": "Complying Development Certificate (CDC)",
                "answer": "No exclusions identified in screened constraints",
                "flag": "ok",
                "basis": (
                    f"Screened: {', '.join(cdc_result.checks_performed)}. "
                    + (" ".join(_notes) + " " if _notes else "")
                    + "CDC availability remains subject to the applicable complying "
                      "development provisions — confirm with a certifier."
                )
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
    # Source: tax_thresholds table (migration 046) ONLY — no hardcoded fallback
    # (invariant: a legal document never renders a regulatory figure the DB did
    # not supply). Absent config renders fail-visible as "Not assessed".
    # Suppress for strata: VG returns whole-lot land value (building site), not unit value
    lv = valuation.get("land_value")
    if lv and not is_strata:
        results.extend(build_land_tax_rows(int(lv), tax_config))

    return results


def build_land_tax_rows(lv_int: int, tax_config: Optional[dict]) -> list[dict]:
    """Land-tax feasibility rows — pure sentence builder, golden-tested.

    tax_config absent → "Not assessed" with the expected year named; figures are
    NEVER computed from constants (fail-visible, invariant 7). A stale-year row
    renders with its own tax_year visible plus a WARNING log.
    """
    if tax_config is None:
        _expected_year = date.today().year
        logger.warning(
            "calc_feasibility: land tax config unavailable for the %s year — "
            "rendering 'Not assessed' (no figures computed)", _expected_year,
        )
        return [{
            "question": "Land tax (investment property)",
            "answer": "Not assessed",
            "flag": "warn",
            "basis": (
                f"Land tax configuration unavailable for the {_expected_year} land tax "
                f"year — no threshold or liability figures were computed for this report. "
                f"Current thresholds and rates: revenue.nsw.gov.au."
            )
        }]

    lt_year = tax_config["tax_year"]
    lt_threshold = tax_config["threshold_dollars"]
    lt_rate = tax_config["rate"]
    lt_base = tax_config["base_amount_dollars"]
    if lt_year < date.today().year:
        # Stale-year config renders anyway — the sentence carries its own year
        # verbatim, which keeps it honest — but loudly.
        logger.warning(
            "calc_feasibility: tax_thresholds row is for %s but the current land tax "
            "year is %s — rendering the %s figures with their year visible",
            lt_year, date.today().year, lt_year,
        )

    if lv_int > lt_threshold:
        annual_lt = lt_base + (lv_int - lt_threshold) * lt_rate
        return [{
            "question": f"Land tax (investment, {lt_year} thresholds)",
            "answer": f"${round(annual_lt):,}/year",
            "flag": "warn",
            "basis": (
                f"Land value ${lv_int:,} exceeds {lt_year} threshold ${lt_threshold:,}. "
                f"${lt_base} + {lt_rate * 100:.1f}% × ${lv_int - lt_threshold:,} = ${round(annual_lt):,}/year. "
                f"PPOR exempt. Investment property, trust, and company holdings are taxable. "
                f"Verify current thresholds at revenue.nsw.gov.au."
            )
        }]
    return [{
        "question": f"Land tax (investment, {lt_year} thresholds)",
        "answer": "Below threshold — nil",
        "flag": "ok",
        "basis": (
            f"Land value ${lv_int:,} is below {lt_year} threshold ${lt_threshold:,}. "
            "No land tax payable on investment property. PPOR always exempt. "
            "Verify current thresholds at revenue.nsw.gov.au."
        )
    }]


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
            if fsr_val <= 15:  # ratio, not sqm (NSW CBD can reach ~15:1)
                max_gfa = lot_area * fsr_val
                out["max_gfa_m2"] = round(max_gfa)
                out["max_gfa_display"] = f"{round(max_gfa):,} m²"
                out["fsr_numeric"] = fsr_val
        except ValueError:
            pass

    if lot_area and min_lot_str:
        try:
            _clean = re.sub(r"[mM²].*$", "", min_lot_str.strip().replace(",", "").replace(" ", ""))
            min_lot = float(re.sub(r"[^\d.]", "", _clean)) if _clean else 0
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

    # GATE-0 (parcel identity): the Portal /address search is fuzzy — refuse a
    # resolved parcel whose street number/name does not match the request rather
    # than silently returning a neighbouring property as AUTHORITATIVE.
    resolved_label = data[0].get("address") or ""
    if not parcel_identity_match(address, resolved_label):
        print(
            f"  [GATE-0] address identity mismatch — requested {address!r} "
            f"resolved to {resolved_label!r}; suppressing (fail-closed)"
        )
        return None, None, None, None

    lat, lng, lot_wkt = _lot_centroid_wkt(prop_id)
    return prop_id, lat, lng, lot_wkt


def _lot_centroid_wkt(
    prop_id: int,
) -> tuple[Optional[float], Optional[float], Optional[str]]:
    """Fetch the lot polygon for ``prop_id`` → (lat, lng, lot_wkt) in WGS84.

    Shared by the text resolver and the coordinate resolver so both derive the
    centroid + PostGIS polygon identically. Returns (None, None, None) on failure.
    """
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
                return lat, lng, f"POLYGON(({coords_str}))"
    except Exception as e:
        print(f"  [warn] lot geometry: {e}")
    return None, None, None


def resolve_propid_by_point(
    lat: float, lng: float, requested_address: str,
) -> Optional[tuple[int, float, float, Optional[str]]]:
    """Coordinate-first parcel resolution: resolve the propId from a trusted pin
    (e.g. Google Places) via point-in-cadastre instead of the fuzzy text search.

    prior-art-checked: reuse not viable because no existing resolver maps a
    coordinate to a Planning-Portal propId — intelligence_brief.py consumes this,
    hierarchy_resolver/dcp-resolver resolve provisions not parcels, and the Python
    cadastre point queries (portal_constraints, strata_lookup) return
    overlays/strata not a propId. This is the single coordinate->propId resolver.

    GATE-0 is RETAINED, not bypassed: the cadastre Property layer returns each
    parcel's own address, and we keep only parcels whose address passes
    :func:`parcel_identity_match` against the request. We resolve **iff** exactly
    one distinct propId survives — a pin that lands on a neighbouring parcel (whose
    address won't match) yields no result, so the caller falls back to the text
    resolver rather than serving the wrong parcel.

    Returns ``(prop_id, lat, lng, lot_wkt)`` on a confident match, else ``None``.
    """
    try:
        geometry = json.dumps({"x": lng, "y": lat, "spatialReference": {"wkid": 4326}})
        r = requests.get(
            PROPERTY_LAYER_URL,
            params={
                "geometry": geometry,
                "geometryType": "esriGeometryPoint",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "propid,address",
                "returnGeometry": "false",
                "f": "json",
            },
            timeout=15,
        )
        r.raise_for_status()
        features = r.json().get("features") or []
    except Exception as e:
        print(f"  [warn] point->propid: {e}")
        return None

    # GATE-0 cross-check: keep only parcels whose cadastre address matches the
    # request; a strata/apartment block returns many address points sharing one
    # propId, which collapses to a single id here.
    matched_propids = {
        attrs["propid"]
        for f in features
        for attrs in (f.get("attributes") or {},)
        if attrs.get("propid") and attrs.get("address")
        and parcel_identity_match(requested_address, attrs["address"])
    }
    if len(matched_propids) != 1:
        return None  # no confident match, or ambiguous -> caller falls back to text

    prop_id = int(matched_propids.pop())
    c_lat, c_lng, lot_wkt = _lot_centroid_wkt(prop_id)
    # Prefer the authoritative lot centroid; fall back to the input pin.
    return prop_id, (c_lat if c_lat is not None else lat), (c_lng if c_lng is not None else lng), lot_wkt


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

            # Build 5-year history: val5 = oldest, val1 = most recent.
            # VG land values are whole dollars — keep them int so no rendering
            # path can produce a "$1,610,000.0" float artifact (D7).
            history = []
            for i in range(5, 0, -1):
                lv_i = _num(attrs.get(f"val{i}_lv"))
                bd_i = (attrs.get(f"val{i}_bd") or "").strip() or None
                if lv_i:
                    history.append({"year": bd_i or f"val{i}", "value": int(lv_i)})

            lv = _num(attrs.get("val1_lv"))
            return {
                "lot_area_m2": _num(area),
                "land_value": int(lv) if lv is not None else None,
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
        # Sydney Drinking Water Catchment — a named DA constraint (B&C SEPP 2021
        # Pt 6.2/6.5 neutral-or-beneficial-effect test + s171A EP&A Reg 2021).
        "sdwc": None,
        # Fail-open capture: every layerintersect group this parser does not
        # recognise, verbatim. Rendered as "Other planning instruments" — never
        # silently dropped (Bowral SDWC regression, 2026-07).
        "other_instruments": [],
    }

    for block in raw:
        raw_layer_name = block.get("layerName", "")
        layer = raw_layer_name.lower()
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
                # Class carries the actual standard value (e.g. Water Use "40%",
                # Climate Zone "6"); title names the specific SEPP map. Both are
                # needed to render the row meaningfully instead of a bare
                # postcode/LGA Label.
                class_ = res.get("Class") or ""
                map_title = res.get("title") or ""
                if epi or type_:
                    out["sepp_overlays"].append({
                        "name": epi, "type": type_, "label": label,
                        "class": class_, "map_title": map_title,
                    })
                if "housing" in epi.lower() or "housing" in type_.lower():
                    out["housing_sepp"] = True
                if "transport" in epi.lower() and "tod" in str(type_).lower():
                    out["tod_area"] = True
                if "basix" in epi.lower() or "climate" in str(type_).lower():
                    out["basix_zone"] = label or type_

        elif "drinking water catchment" in layer:
            # Sydney Drinking Water Catchment Map — portal result carries the
            # statutory citation in Label/title; extract verbatim, no interpretation.
            _sdwc_label = None
            for res in results:
                _sdwc_label = res.get("Label") or res.get("title")
                if _sdwc_label:
                    break
            out["sdwc"] = {
                "layer": raw_layer_name,
                "label": _sdwc_label or raw_layer_name,
            }

        else:
            # Fail-open: capture unrecognised groups verbatim so a new portal
            # layer surfaces in the report and in logs instead of vanishing.
            titles = []
            for res in results:
                t = res.get("title") or res.get("EPI Name") or res.get("Label")
                if t and str(t).strip():
                    titles.append(str(t).strip())
            titles = list(dict.fromkeys(titles))
            out["other_instruments"].append({
                "layer": raw_layer_name,
                "titles": titles,
            })
            logger.warning(
                "parse_controls: unrecognised layerintersect group %r captured as other_instruments (titles=%s)",
                raw_layer_name, titles,
            )

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


# prior-art-checked: reuse not viable because _normalize_coastal in
# services/climate_risk_score.py returns a HazardScore for the scoring pipeline;
# this is a row-level filter for the overlay list this file already produces.
def _drop_jurisdictional_overlays(results: list[dict]) -> list[dict]:
    """Drop overlay rows that mark a policy's jurisdiction, not a hazard.

    SEPP R&H 2021 "Land Application" polygons cover ALL of NSW — a
    jurisdictional boundary, not a hazard. Only "Subject Land" marks a specific
    coastal designation. Without this filter every NSW property (including
    inland LGAs) shows a false coastal overlay in the free check and the PDF.
    Mirrors _normalize_coastal in services/climate_risk_score.py.
    """
    return [
        o for o in results
        if not (
            o.get("layer_type") == "coastal_land_application"
            and (o.get("value") or "").strip() != "Subject Land"
        )
    ]


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

        results = _drop_jurisdictional_overlays(results)

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
        # flood added (brief Slice 2): a "No" flood row carrying the measured distance to the
        # nearest mapped flood polygon — same covered-not-hit ST_Distance mechanism, never an estimate.
        PROXIMITY_LAYERS = frozenset({"biodiversity", "riparian", "wetlands", "landslide", "flood"})
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
        "canada bay": "City of Canada Bay Council",
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
        # Propagate so callers can distinguish a FAILED lookup from a genuine
        # zero result. A swallowed failure returned as [] gets served downstream
        # as an authoritative "0 nearby DAs" — a silent false negative.
        raise RuntimeError(f"Nearby-DA lookup failed: {e}") from e

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
    report_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Call the Railway shadow pipeline.
    height_m: pass the LEP height already fetched from Planning Portal so
    Railway doesn't need to re-query (avoids spatial_overlays coverage gaps).
    report_id: caller-supplied id for the row written by the shadow service
    (the brief passes a per-product derived id, issue #762); defaults to a
    fresh uuid4 for CLI/standalone callers.
    prior-art-checked: no new capability — this IS the existing shadow fetcher
    gaining an optional passthrough parameter; no new data source or surface.
    Returns the `outputs` dict on success (with the envelope's run-level
    `confidence` merged in — the outputs dict itself carries no confidence key,
    and downstream consumers render run confidence from this merged value),
    None if Railway unreachable or call fails.
    Graceful degradation — shadow section is omitted rather than crashing the report.
    """
    api_url = os.environ.get("PYTHON_API_URL", "http://localhost:8000")
    payload = {
        "address": address,
        "prop_id": str(prop_id),
        "lat": lat,
        "lng": lng,
        "report_id": report_id or str(uuid.uuid4()),
    }
    if height_m:
        payload["height_m"] = height_m
    try:
        r = requests.post(f"{api_url}/pipeline/shadow", json=payload, timeout=60)
        r.raise_for_status()
        # prior-art-checked: this IS the existing shadow fetcher being extended
        # in place (no new data source) — it previously discarded the envelope's
        # run-level confidence; merging it here is the minimal passthrough.
        body = r.json()
        outputs = body.get("outputs")
        if isinstance(outputs, dict) and "confidence" not in outputs:
            return {**outputs, "confidence": body.get("confidence")}
        return outputs
    except Exception as e:
        print(f"  [warn] Shadow pipeline unavailable — section will be omitted: {e}")
        return None


# prior-art-checked: reuse not viable because the honest shadow-provenance
# wording exists only in TypeScript (intelligence-brief/page.tsx, ShadowTool.tsx)
# and cannot be imported into this Python renderer; get_bushfire_live wraps and
# REUSES the existing prod client services/bushfire_prescreen._query_rfs_bfpl
# rather than reimplementing it. These pure builders exist so the PDF's exact
# sentences are golden-tested (tests/test_conveyancing_truth.py, guardrail G1).
def get_bushfire_live(lat: float, lng: float) -> Optional[dict]:
    """Live NSW RFS BFPL point query for the conveyancing report.

    Wraps services.bushfire_prescreen._query_rfs_bfpl (the existing prod client).
    Returns its result dict, or None when the client cannot be imported/run —
    build_bushfire_row treats None as "Not assessed", never "Clear".
    """
    try:
        try:
            from bushfire_prescreen import _query_rfs_bfpl
        except ImportError:
            # CLI context: services/ is not on sys.path (its modules import
            # siblings as top-level, e.g. `from audit_trail import ...`).
            _services_dir = str(project_root / "services")
            if _services_dir not in sys.path:
                sys.path.insert(0, _services_dir)
            from bushfire_prescreen import _query_rfs_bfpl
        return _query_rfs_bfpl(lat, lng)
    except Exception as e:
        print(f"  [warn] Live RFS BFPL query unavailable: {e}")
        return None


def get_mine_subsidence_live(lat: float, lng: float) -> dict:
    """Mine subsidence district lookup, wrapped to a three-state status dict.

    prior-art-checked: wraps services/portal_constraints.fetch_mine_subsidence
    (the Site Report's fetcher) — no new client. The fetcher returns None for
    "outside every district" and raises on failure, so this wrapper is where
    clear and failed are kept apart: {"status": "empty"} is a checked clear;
    {"status": "failed"} renders "Not assessed", never "Clear".
    """
    try:
        try:
            from portal_constraints import fetch_mine_subsidence
        except ImportError:
            _services_dir = str(project_root / "services")
            if _services_dir not in sys.path:
                sys.path.insert(0, _services_dir)
            from portal_constraints import fetch_mine_subsidence
        result = fetch_mine_subsidence(lat, lng)
        if result is None:
            return {"status": "empty"}
        return {"status": "found", "data": result}
    except Exception as e:
        print(f"  [warn] Mine subsidence lookup unavailable: {e}")
        return {"status": "failed"}


def get_contaminated_live(lat: float, lng: float) -> dict:
    """EPA contaminated-land register lookup (500 m buffer), three-state.

    prior-art-checked: wraps services/portal_constraints.fetch_contaminated_land
    (the Site Report's fetcher) — same wrapper contract as
    get_mine_subsidence_live; a failure must never render as a clear register.
    """
    try:
        try:
            from portal_constraints import fetch_contaminated_land
        except ImportError:
            _services_dir = str(project_root / "services")
            if _services_dir not in sys.path:
                sys.path.insert(0, _services_dir)
            from portal_constraints import fetch_contaminated_land
        result = fetch_contaminated_land(lat, lng)
        if result is None:
            return {"status": "empty"}
        return {"status": "found", "data": result}
    except Exception as e:
        print(f"  [warn] Contaminated land lookup unavailable: {e}")
        return {"status": "failed"}


def get_servicing_live(lat: float, lng: float) -> dict:
    """Sydney Water GSP servicing lookup, three-state.

    prior-art-checked: wraps services/gsp_servicing.fetch_gsp_servicing (the reusable
    DB point-in-polygon lookup over sydney_water_gsp_servicing, migration 058). Same
    wrapper contract as get_mine_subsidence_live: it already returns the three-state
    dict, so pass it through and fail closed to {"status": "failed"}.
    """
    try:
        try:
            from gsp_servicing import fetch_gsp_servicing
        except ImportError:
            _services_dir = str(project_root / "services")
            if _services_dir not in sys.path:
                sys.path.insert(0, _services_dir)
            from gsp_servicing import fetch_gsp_servicing
        return fetch_gsp_servicing(lat, lng)
    except Exception as e:
        print(f"  [warn] Sydney Water servicing lookup unavailable: {e}")
        return {"status": "failed"}


# instrument_key pattern written by scripts/ingest_coastal_inundation.py:
# estuary_inund_2025_s370_y{2050|2100}_{f1..f4}
_COASTAL_IK_RE = re.compile(r"_y(\d{4})_f\d$")
# Exact publication/scenario this renderer's source line cites. The query is
# scoped to it so a future load under the same layer_type (new publication or
# scenario) can never be rendered under the 2025 SSP3-7.0 attribution.
_COASTAL_INSTRUMENT_PREFIX = "estuary_inund_2025_s370_"
# LIKE pattern with '_' escaped (it is a LIKE wildcard).
_COASTAL_IK_LIKE = _COASTAL_INSTRUMENT_PREFIX.replace("_", r"\_") + "%"


def get_coastal_inundation_live(
    lat: float, lng: float, lot_wkt: Optional[str] = None,
) -> dict:
    """Estuarine tidal inundation extent check (spatial_overlays), three-state.

    prior-art-checked: same spatial_overlays intersection mechanics as
    get_unique_overlays (lot polygon preferred, point fallback) against the
    layer loaded by scripts/ingest_coastal_inundation.py — no new client, no
    new geometry logic. Kept out of get_unique_overlays because this layer is
    statewide + multi-row-per-lot (one row per year×tier), not a per-LGA
    unique overlay, and it must never feed the cover CONSTRAINTS tile.

    Returns:
      {"status": "failed"}                       — DB unavailable/errored → "Not assessed"
      {"status": "outside", "query_basis": ...}  — checked, no intersection
      {"status": "intersects", "query_basis": ..., "years": {2050: {...}, 2100: {...}}}
        each year dict: {"days_per_year": float, "value": str} — the MOST
        FREQUENT mapped tier (max days/year) whose polygon intersects the lot;
        tiers are nested so the most frequent is the informative one. Every
        figure is READ from the stored row (loader-written `value` string +
        `value_numeric`), never composed here.
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return {"status": "failed"}
    conn = None
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        if lot_wkt:
            cur.execute(
                r"""
                SELECT instrument_key, value, value_numeric
                FROM spatial_overlays
                WHERE layer_type = 'coastal_inundation'
                  AND instrument_key LIKE %s ESCAPE '\'
                  AND ST_Intersects(geom, ST_SetSRID(ST_GeomFromText(%s), 4326))
                """,
                (_COASTAL_IK_LIKE, lot_wkt),
            )
            query_basis = "lot"
        else:
            cur.execute(
                r"""
                SELECT instrument_key, value, value_numeric
                FROM spatial_overlays
                WHERE layer_type = 'coastal_inundation'
                  AND instrument_key LIKE %s ESCAPE '\'
                  AND ST_Intersects(geom, ST_SetSRID(ST_Point(%s, %s), 4326))
                """,
                (_COASTAL_IK_LIKE, lng, lat),
            )
            query_basis = "point"
        rows = cur.fetchall()
        if not rows:
            # Zero intersections is only a checked "outside" if the layer is
            # actually present — a deleted/never-loaded layer must read as
            # "not assessed", never a universal all-clear.
            cur.execute(
                r"""
                SELECT 1 FROM spatial_overlays
                WHERE layer_type = 'coastal_inundation'
                  AND instrument_key LIKE %s ESCAPE '\'
                LIMIT 1
                """,
                (_COASTAL_IK_LIKE,),
            )
            layer_present = cur.fetchone() is not None
            cur.close()
            if not layer_present:
                return {"status": "failed"}
            return {"status": "outside", "query_basis": query_basis}
        cur.close()
        years: dict[int, dict] = {}
        for instrument_key, value, value_numeric in rows:
            m = _COASTAL_IK_RE.search(instrument_key or "")
            if not m:
                continue  # malformed row — never invent a year or frequency for it
            if value_numeric is None:
                continue  # frequency missing from the row — never compose one
            year = int(m.group(1))
            days = float(value_numeric)
            if year not in years or days > years[year]["days_per_year"]:
                years[year] = {"days_per_year": days, "value": value}
        if not years:
            # Rows intersected but none were parseable — a data defect, not a
            # checked clear. Fail closed to "Not assessed".
            return {"status": "failed"}
        return {"status": "intersects", "query_basis": query_basis, "years": years}
    except Exception as e:
        print(f"  [warn] Estuarine inundation query unavailable: {e}")
        return {"status": "failed"}
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Risk-row sentence builders — pure functions (golden-sentence tested in
# tests/test_conveyancing_truth.py). Keep these free of reportlab so the exact
# user-visible wording is testable without rendering a PDF.
# ---------------------------------------------------------------------------

# Source labels for the shadow row. "NSW LEP" may ONLY be claimed when the
# height actually came from an LEP control (portal/spatial_overlays/provisions).
_SHADOW_SOURCE_LEP = "NSW LEP · shadow model"
_SHADOW_SOURCE_ASSUMED = "assumed envelope · shadow model"
# height_source values that genuinely trace to an LEP control — anything else
# (default, None, unrecognised) must fail closed to the assumed-envelope label.
_LEP_HEIGHT_SOURCES = frozenset({"spatial_overlays", "regulatory_provisions", "planning_portal"})


def build_shadow_row(shadow_result: Optional[dict]) -> tuple[str, str, str]:
    """Build the Risk Summary shadow row: (text, style_key, source_label).

    style_key ∈ {"ok", "warn", "alert", "note"} — maps to PDF paragraph styles.

    When height_source == "default" the 9 m figure is an assumption
    (shadow_detector.DEFAULT_HEIGHT_M), not an LEP control: the row must not
    claim "LEP maximum height", must not assert "Clear", and must carry the
    assumed-envelope source label. Mirrors the Intelligence Brief wording
    (frontend-nextjs/app/reports/intelligence-brief/page.tsx).
    """
    if shadow_result is None:
        return ("Not assessed", "note", "shadow model")

    jun21 = [s for s in (shadow_result.get("scenarios") or [])
             if s.get("scenario") in {"jun21_9am", "jun21_12pm", "jun21_3pm"}]
    overlap_count = sum(1 for s in jun21 if s.get("overlaps_subject_lot"))
    height_m = shadow_result.get("height_m") or "?"
    adg_ok = shadow_result.get("adg_compliant", True)
    noon = next((s for s in jun21 if s.get("scenario") == "jun21_12pm"), None)
    noon_pct = round((noon.get("shadow_overlap_fraction") or 0) * 100) if noon else 0
    height_source = shadow_result.get("height_source")

    if adg_ok is None:
        # Three-state (output-grounding fix 1): the noon scenario was missing,
        # errored, or its overlap unknown — the model issued NO verdict. Checked
        # BEFORE the height-provenance branches so no numeric noon-shadow claim
        # (a noon_pct of 0 here would be an errored scenario, not a measurement)
        # is made either. The old fallthrough rendered this as "ADG concern".
        text = (
            "Not assessed — the shadow model could not compute the Jun 21 noon "
            "scenario for this lot, so the ADG solar-access test was not run. "
            "No shadow verdict is made in this report."
        )
        return (text, "note", "shadow model")

    if height_source == "default":
        # Assumed envelope — no LEP height limit is mapped for this lot.
        text = (
            f"Not determinable from LEP controls — no LEP height limit is mapped for this lot, "
            f"so the analysis uses a standard two-storey height ({height_m} m assumed envelope). "
            f"A {height_m} m building on the northern adjacent lot would shadow {noon_pct}% of "
            f"this property at Jun 21 noon. A taller merit-assessed build is possible and is not "
            f"modelled here."
        )
        return (text, "warn", _SHADOW_SOURCE_ASSUMED)

    if height_source not in _LEP_HEIGHT_SOURCES:
        # Unknown provenance (missing/unrecognised height_source) — fail closed:
        # never attribute an unverified height to the LEP.
        text = (
            f"Modelled with a {height_m} m building envelope whose height provenance was not "
            f"recorded — not attributed to LEP controls. A {height_m} m building on the northern "
            f"adjacent lot would shadow {noon_pct}% of this property at Jun 21 noon."
        )
        return (text, "warn", _SHADOW_SOURCE_ASSUMED)

    hob_note = f" (LEP maximum height of buildings: {height_m} m)"
    if adg_ok and overlap_count == 0:
        text = (
            f"Clear — a {height_m} m building on the northern adjacent lot would not "
            f"significantly shadow this property on any Jun 21 scenario.{hob_note}"
        )
        return (text, "ok", _SHADOW_SOURCE_LEP)
    if adg_ok:
        text = (
            f"Low risk — a {height_m} m building on the northern adjacent lot would shadow "
            f"{noon_pct}% of this property at Jun 21 noon. ADG solar access requirement met.{hob_note}"
        )
        return (text, "warn", _SHADOW_SOURCE_LEP)
    text = (
        f"ADG concern — a {height_m} m building on the northern adjacent lot would shadow "
        f"{noon_pct}% of this property at Jun 21 noon. Solar access may not meet the "
        f"2-hour ADG requirement.{hob_note}"
    )
    return (text, "alert", _SHADOW_SOURCE_LEP)


def build_bushfire_row(
    bushfire_live: Optional[dict],
    postgis_hit: Optional[dict],
) -> tuple[str, str, str]:
    """Build the Risk Summary bushfire row: (text, style_key, source_label).

    Semantics (D3): the live NSW RFS BFPL query governs.
      live prone       → alert row with the RFS category
      live not prone   → "Clear" citing the live RFS query
      live failed/None → fall back to the ingested PostGIS hit if present
                         (alert), otherwise "Not assessed" — NEVER "Clear"
                         from a failed query.
    """
    live_prone = (bushfire_live or {}).get("is_bushfire_prone")
    if live_prone is True:
        category = (bushfire_live.get("designation_category") or "").strip()
        cat_str = f" — {category}" if category else ""
        return (
            f"Bushfire Prone Land{cat_str}. BAL assessment required before any development application.",
            "alert",
            "NSW RFS BFPL (live query)",
        )
    if live_prone is False:
        return (
            "Clear — not mapped as bushfire prone (NSW RFS BFPL, live query)",
            "ok",
            "NSW RFS BFPL (live query)",
        )
    # Live query failed or was not run
    if postgis_hit:
        val = (postgis_hit.get("value") or "").strip()
        val_str = f" — {val}" if val else ""
        return (
            f"Bushfire Prone Land{val_str}. BAL assessment required before any development application. "
            f"(Live RFS check unavailable — showing ingested NSW RFS BFPL data.)",
            "alert",
            "PostGIS (ingested NSW RFS BFPL)",
        )
    return (
        "Not assessed — RFS service unavailable. Confirm bushfire-prone status via a s10.7(2) "
        "certificate or the NSW RFS BFPL map.",
        "note",
        "NSW RFS BFPL",
    )


# prior-art-checked: mirrors build_bushfire_row above (same file) — pure,
# golden-testable row builders over the three-state payloads the orchestrator
# wraps around portal_constraints.fetch_mine_subsidence / fetch_contaminated_land
# (the Site Report's own fetchers) — no new client, no reimplementation.
def build_mine_subsidence_row(mine_subsidence: Optional[dict]) -> tuple[str, str, str]:
    """Build the Risk Summary mine subsidence row: (text, style_key, source_label).

    Payload contract (services/conveyancing.py _fetch_mine_subsidence):
      {"status": "found", "data": {...}} → in a proclaimed district (warn)
      {"status": "empty"}               → checked clear (ok)
      {"status": "failed"} / None / any other shape → "Not assessed" (note) —
      NEVER "Clear" from a failed or missing lookup.
    """
    status = (mine_subsidence or {}).get("status")
    if status == "found":
        data = mine_subsidence.get("data") or {}
        name = (data.get("district_name") or "").strip()
        name_str = f"{name} Mine Subsidence District" if name else "a proclaimed mine subsidence district"
        return (
            f"Within the {name_str}. Building and subdivision work in a district is regulated "
            f"under the Coal Mine Subsidence Compensation Act 2017 — development consent from "
            f"Subsidence Advisory NSW may be required.",
            "warn",
            "NSW Spatial Services mine subsidence districts (live query)",
        )
    if status == "empty":
        return (
            "Clear — not within a proclaimed mine subsidence district (NSW Spatial Services, live query)",
            "ok",
            "NSW Spatial Services (live query)",
        )
    return (
        "Not assessed — mine subsidence district lookup unavailable at report generation. "
        "Confirm via a s10.7 certificate or Subsidence Advisory NSW.",
        "note",
        "NSW Spatial Services",
    )


def build_contaminated_land_row(contaminated: Optional[dict]) -> tuple[str, str, str]:
    """Build the Risk Summary contaminated land row: (text, style_key, source_label).

    The underlying query is a 500 m BUFFER around the lot, not a lot-boundary
    test — every sentence states the radius, and a hit is worded as proximity,
    never as contamination of the subject property. Same three-state contract
    as build_mine_subsidence_row: only {"status": "empty"} may render clear.
    """
    status = (contaminated or {}).get("status")
    if status == "found":
        data = contaminated.get("data") or {}
        count = data.get("site_count") or 1
        site = data.get("nearest_site") or {}
        name = (site.get("name") or "").strip()
        suburb = (site.get("suburb") or "").strip()
        mgmt = (site.get("management_class") or "").strip()
        dist = site.get("distance_m")
        parts = [p for p in (name, suburb) if p]
        nearest_str = f" Nearest: {', '.join(parts)}" if parts else ""
        dist_str = f" (~{dist} m away)" if dist is not None else ""
        mgmt_str = f" — EPA management class: {mgmt}." if mgmt else "."
        plural = "sites" if count != 1 else "site"
        return (
            f"{count} notified {plural} on the EPA contaminated land register within 500 m of this "
            f"property.{nearest_str}{dist_str}{mgmt_str} This records proximity to a notified site, "
            f"not contamination of the subject lot.",
            "warn",
            "NSW EPA contaminated land register (live query, 500 m radius)",
        )
    if status == "empty":
        return (
            "Clear — no notified sites on the EPA contaminated land register within 500 m "
            "(live query). The register lists notified sites only; it is not a complete record "
            "of land contamination.",
            "ok",
            "NSW EPA contaminated land register (live query, 500 m radius)",
        )
    return (
        "Not assessed — EPA contaminated land register lookup unavailable at report generation. "
        "Confirm via a s10.7(5) certificate and an EPA public register search.",
        "note",
        "NSW EPA contaminated land register",
    )


# Sydney Water Growth Servicing Plan row. Source is © Sydney Water, "guide only" —
# every rendered surface attributes and links (GSP page), and the DSP figure is stated
# as a CPI-excluded BASE charge, never the live charge.
_SERVICING_STAGE_HUMAN = {
    "IN_DELIVERY": "trunk servicing in delivery",
    "PLANNED": "servicing planned",
    "NO_CURRENT_PROJECT": "no current servicing project",
    "UNKNOWN_STAGE": "servicing stage not stated",
}


def _servicing_product_phrase(label: str, d: Optional[dict]) -> Optional[str]:
    if not d:
        return None
    human = _SERVICING_STAGE_HUMAN.get(d.get("status_code"), "servicing stage not stated")
    tf = (d.get("timeframe") or "").strip()
    tf_str = f", indicative {tf}" if tf and tf.lower() != "no timeframe noted." else ""
    price = d.get("dsp_price_per_et")
    price_str = f", base DSP ~${price:,.0f}/ET" if price is not None else ""
    return f"{label}: {human}{tf_str}{price_str}"


def build_servicing_row(servicing: Optional[dict]) -> tuple[str, str, str]:
    """Build the Risk Summary servicing row: (text, style_key, source_label).

    Three-state (services/gsp_servicing.fetch_gsp_servicing):
      {"status": "found", "data": {"ww":..,"dw":..}} → in a growth-servicing area
      {"status": "empty"}  → NOT in a GSP precinct — established-suburb gap, "note"
                              (never "clear"; capacity is a Section 73 question)
      {"status": "failed"} / None / other → "Not assessed", never a clear result.
    DSP figures are stated as CPI-excluded base charges; wording never says the site
    is "serviceable" or "ready" — trunk capacity is not service-readiness.
    """
    try:
        from gsp_servicing import GSP_SOURCE
    except ImportError:
        from services.gsp_servicing import GSP_SOURCE

    status = (servicing or {}).get("status")
    if status == "found":
        data = servicing.get("data") or {}
        ww, dw = data.get("ww"), data.get("dw")
        area = ((ww or dw or {}).get("growth_area") or "").strip()
        area_str = f" ({area})" if area else ""
        phrases = [p for p in (_servicing_product_phrase("Wastewater", ww),
                               _servicing_product_phrase("drinking water", dw)) if p]
        constrained = bool((ww or {}).get("constrained") or (dw or {}).get("constrained"))
        constraint_str = (
            " Sydney Water notes capacity and timescale constraints in this area that may "
            "affect servicing your development."
        ) if constrained else ""
        text = (
            f"Within a Sydney Water growth-servicing area{area_str}. "
            + "; ".join(phrases) + ". "
            + "Trunk capacity indicated does not make a site service-ready — feasibility and "
            "connection works are still required."
            + constraint_str
            + " DSP figures are indicative base charges (exclude CPI) — confirm the current "
            f"charge with Sydney Water. Source: {GSP_SOURCE} (guide only)."
        )
        return (text, "warn" if constrained else "note", GSP_SOURCE)
    if status == "empty":
        return (
            "Not within a Sydney Water growth-servicing precinct. Servicing capacity for an "
            "established-area site is determined individually via a Section 73 application "
            "(Notice of Requirements) and is not published in the Growth Servicing Plan. "
            f"Source: {GSP_SOURCE}.",
            "note",
            GSP_SOURCE,
        )
    return (
        "Not assessed — Sydney Water Growth Servicing Plan lookup unavailable at report "
        f"generation. Confirm servicing directly with Sydney Water. Source: {GSP_SOURCE}.",
        "note",
        GSP_SOURCE,
    )


# prior-art-checked: mirrors build_bushfire_row above (same file) — a pure,
# golden-tested row builder; the value RESOLUTION reuses the existing
# portal_constraints.resolve_anef_value (lifted anef_zones query + existing
# fetch_anef), nothing reimplemented.
def _anef_value_display(anef_live: dict) -> str:
    """Verbatim contour value for display: the source's code (e.g. "25-30")
    when present, else the numeric level."""
    code = anef_live.get("anef_code")
    if code:
        return str(code)
    return str(anef_live.get("anef_level"))


def _anef_source_label(anef_live: dict) -> str:
    """Human-readable provenance for a resolved ANEF value — names the mapping
    instrument the government layer attributes the contour to (EPI_NAME),
    never an implied 'current' (PR #678 precedent)."""
    epi = anef_live.get("epi_name")
    epi_str = f"{epi} airport-noise mapping, " if epi else ""
    return f"{epi_str}NSW ePlanning Protection ANEF layer, live query at report generation"


def build_anef_row(
    anef_live: Optional[dict],
    postgis_hit: Optional[dict],
) -> Optional[tuple[str, str, str]]:
    """Build the Risk Summary ANEF row: (text, style_key, source_label) or None.

    Semantics (three-state, bushfire-row precedent):
      no ingested ANEF overlay        → None (row omitted — Bowral regression)
      overlay + value resolved        → row states the contour value + provenance
      overlay + lookup ran, no value  → today's wording (honest fallback)
      overlay + lookup FAILED         → value explicitly "not assessed",
                                        never a silent omission
    """
    status = (anef_live or {}).get("status")
    if postgis_hit is None:
        if status == "found":
            # The curated/live value source governs over the ingest (bushfire
            # D3 precedent) — a resolved contour is a TRUE constraint and must
            # not vanish because our ingest lacks the polygon (Mascot gap,
            # verified 2026-07-06: anef_zones=35, spatial_overlays=no hit).
            logger.warning(
                "ANEF value resolved (%s) but no ingested anef overlay hit — "
                "rendering from the value lookup; check spatial_overlays anef ingest",
                _anef_value_display(anef_live),
            )
            return (
                f"Aircraft noise contour — ANEF {_anef_value_display(anef_live)} "
                f"({_anef_source_label(anef_live)})",
                "warn",
                "ANEF value lookup",
            )
        # No ingest hit and no resolved value → no contour claim (row omitted);
        # a failed lookup on a lot with no mapped contour is a non-event.
        return None
    if status == "found":
        # A synthesized hit (ingest missed the contour; overlay added from the
        # value lookup) must not be attributed to PostGIS.
        _synthetic = (postgis_hit or {}).get("instrument") == "ANEF_VALUE_LOOKUP"
        return (
            f"Aircraft noise contour — ANEF {_anef_value_display(anef_live)} "
            f"({_anef_source_label(anef_live)})",
            "warn",
            "ANEF value lookup" if _synthetic else "PostGIS + ANEF value lookup",
        )
    if status == "failed":
        return (
            "Aircraft noise contour — ANEF applies. Contour value not assessed — "
            "value lookup unavailable at report generation.",
            "warn",
            "PostGIS",
        )
    # status "empty", or the lookup was not run: today's exact wording
    return (
        "Aircraft noise contour — ANEF applies",
        "warn",
        "PostGIS",
    )


def build_anef_note(anef_live: Optional[dict]) -> Optional[str]:
    """Section 5 note override when the contour value is known or the lookup
    failed; None keeps the static ANEF_NOTE (the honest no-value fallback)."""
    status = (anef_live or {}).get("status")
    if status == "found":
        return _ANEF_NOTE_BASE + (
            f"ANEF contour value at this location: {_anef_value_display(anef_live)} "
            f"(source: {_anef_source_label(anef_live)}). The specific restrictions "
            f"depend on the contour value — confirm development requirements with "
            f"council or a qualified acoustic consultant."
        )
    if status == "failed":
        return ANEF_NOTE + (
            " The contour value lookup was unavailable when this report was "
            "generated — the contour value is not assessed in this report."
        )
    return None


def get_anef_live(lat: float, lng: float) -> dict:
    """ANEF contour value lookup for the CLI report path — three-state.

    Wraps services.portal_constraints.resolve_anef_value (the shared resolver).
    Import or runtime failure returns {"status": "failed"} — build_anef_row
    renders that as not-assessed wording, never silence.
    """
    try:
        try:
            from portal_constraints import resolve_anef_value
        except ImportError:
            _services_dir = str(project_root / "services")
            if _services_dir not in sys.path:
                sys.path.insert(0, _services_dir)
            from portal_constraints import resolve_anef_value
        return resolve_anef_value(lat, lng)
    except Exception as e:
        print(f"  [warn] ANEF value lookup unavailable: {e}")
        return {"status": "failed"}


# prior-art-checked: reuses services/portal_constraints.fetch_contributions_plans
# / fetch_corridors_reservations (added alongside this change) via the same thin
# get_*_live wrapper pattern as get_anef_live/get_bushfire_live above; the /cp
# parse lives in portal_constraints and mirrors intelligence_brief.
# _fetch_contributions (PR #460) re-wrapped with three-state semantics because
# the brief fetcher collapses queried-empty and transport failure into one None.
# The sentence builders below are new PDF wording (no existing renderer covers
# contributions or LRA/corridor checks — grep-verified 2026-07-07).
def get_contributions_live(prop_id: Optional[int]) -> dict:
    """Development contributions (/cp) lookup — three-state.

    Wraps services.portal_constraints.fetch_contributions_plans. Import or
    runtime failure (and a missing propId) returns {"status": "failed"} —
    build_contributions_lines renders that as "Not assessed", never silence.
    """
    if not prop_id:
        print("  [warn] contributions lookup skipped — no propId resolved")
        return {"status": "failed"}
    try:
        try:
            from portal_constraints import fetch_contributions_plans
        except ImportError:
            _services_dir = str(project_root / "services")
            if _services_dir not in sys.path:
                sys.path.insert(0, _services_dir)
            from portal_constraints import fetch_contributions_plans
        return fetch_contributions_plans(int(prop_id))
    except Exception as e:
        print(f"  [warn] contributions lookup unavailable: {e}")
        return {"status": "failed"}


def get_corridors_live(
    lat: float, lng: float,
    lot_wkt: Optional[str] = None,
    prop_id: Optional[int] = None,
) -> Optional[dict]:
    """Corridors / land-reservation-acquisition / portal warnings — three-state
    per sub-check (services.portal_constraints.fetch_corridors_reservations).

    Returns None when the module itself cannot be imported/run —
    build_corridors_lines renders None as every sub-check "Not assessed".
    """
    try:
        try:
            from portal_constraints import fetch_corridors_reservations
        except ImportError:
            _services_dir = str(project_root / "services")
            if _services_dir not in sys.path:
                sys.path.insert(0, _services_dir)
            from portal_constraints import fetch_corridors_reservations
        return fetch_corridors_reservations(lat, lng, lot_wkt=lot_wkt, prop_id=prop_id)
    except Exception as e:
        print(f"  [warn] corridors/reservations check unavailable: {e}")
        return None


def get_tod_uplift_live(
    lat: float, lng: float, controls: dict, valuation: dict,
    lot_dimensions=None, dcp_controls=None,
):
    """TOD catchment + FLOOR-ONLY capacity baseline for the PDF.

    prior-art-checked: REUSES services.housing_sepp_eligibility.fetch_tod_catchment
    (live SEPP layers 752/759) and services.constraint_arithmetic.compute_constraint_
    arithmetic (the gated capacity engine) — no new catchment logic and no new
    capacity math. The engine is called with ceiling_dev_type=None so it never
    computes the held-back ceiling (floor-only scope decision).

    Returns ``(tod_dict_or_None, capacity_result_or_None)``:
      - tod_dict: fetch_tod_catchment result, or None if both layers failed.
      - capacity: ConstraintArithmeticResult (floor), or None if not in a TOD
        catchment (engine not run) or the engine call failed.
    """
    def _imp():
        try:
            from portal_constraints import fetch_tod_catchment
            from constraint_arithmetic import compute_constraint_arithmetic
        except ImportError:
            _services_dir = str(project_root / "services")
            if _services_dir not in sys.path:
                sys.path.insert(0, _services_dir)
            from portal_constraints import fetch_tod_catchment
            from constraint_arithmetic import compute_constraint_arithmetic
        return fetch_tod_catchment, compute_constraint_arithmetic

    try:
        fetch_tod_catchment, compute_constraint_arithmetic = _imp()
    except Exception as e:
        print(f"  [warn] TOD uplift check unavailable (import): {e}")
        return None, None

    try:
        tod = fetch_tod_catchment(lat, lng)
    except Exception as e:
        print(f"  [warn] TOD catchment lookup failed: {e}")
        return None, None

    # Only run the capacity engine when the lot is actually in a catchment —
    # the block does not render otherwise, so the compute would be wasted.
    if not tod or not tod.get("in_tod"):
        return tod, None

    lot_area = valuation.get("lot_area_m2")
    if not lot_area or lot_area <= 0:
        # No lot area → the engine cannot compute an envelope; the disclosure
        # still renders, the baseline states Not assessed (capacity None).
        return tod, None

    try:
        capacity = compute_constraint_arithmetic(
            lot_area_m2=lot_area,
            dev_type="dwelling_house",   # conservative floor
            ceiling_dev_type=None,       # FLOOR ONLY — never compute the ceiling
            lep_height_str=controls.get("height"),
            lep_fsr_str=controls.get("fsr"),
            lot_dimensions=lot_dimensions,
            dcp_controls=dcp_controls or [],
        )
        return tod, capacity
    except Exception as e:
        print(f"  [warn] capacity baseline computation failed: {e}")
        return tod, None


def _council_recognised_by_eplanning(council: str) -> bool:
    """Validate a council name against the ePlanning API's OWN vocabulary.

    The council-name string OnlineDA/OnlineCDC accepts is API-SPECIFIC (e.g. it
    wants "City of Canada Bay Council" where the LEP/spatial layers say "Canada
    Bay"), and hardcoded maps drift. Rather than trust a map, probe the API: a
    recognised CouncilName returns rows for the whole council; an unrecognised
    string returns zero. A True here means a later zero-at-this-address result is
    a GENUINE absence, not a name mismatch — the difference between an honest
    "no applications" and a false one.
    """
    from pre_da_history import _fetch_eplanning_page
    try:
        page = _fetch_eplanning_page(
            "OnlineDA", {"CouncilName": [council], "ApplicationType": "Development Application"}, 1,
        )
        return bool(page)
    except Exception:
        return False


def get_structures_records_live(council_name: Optional[str], address: str):
    """Subject-lot DA + CDC application records for the Stage-1 reconciliation.

    prior-art-checked: REUSES services.pre_da_history.get_da_events /
    get_pcc_events / _fetch_eplanning_page (live OnlineDA/OnlineCDC fetchers) and
    the generator's own _normalise_council (the fullest ePlanning-name map, used
    by get_nearby_das) — no new fetcher, no new council map. Stage 1 runs NO
    imagery/detection call.

    ROBUSTNESS (council names are API-specific and maps drift): the council name
    is validated against the API's OWN vocabulary before any result is trusted.
    An unrecognised council returns (None, "failed") -> "Not assessed", so a
    name mismatch can never print a FALSE "no applications on record".

    Returns ``(records, status)``:
      - (list, "ok"): DA+CDC records for the lot (possibly empty when the council
        is recognised but no application matches the address — a GENUINE absence).
      - (None, "failed"): missing / unrecognised council, or a fetch error — the
        section renders "Not assessed", never an implied absence of applications.
    """
    council = (council_name or "").strip()
    if not council:
        print("  [warn] structures/records skipped — no council derived (fail-closed)")
        return None, "failed"
    try:
        try:
            from pre_da_history import get_da_events, get_pcc_events  # noqa: F401
        except ImportError:
            _services_dir = str(project_root / "services")
            if _services_dir not in sys.path:
                sys.path.insert(0, _services_dir)
            from pre_da_history import get_da_events, get_pcc_events  # noqa: F401
        # Validate against the API's vocabulary — an unrecognised name would
        # return zero and read as a false "no records".
        if not _council_recognised_by_eplanning(council):
            print(f"  [warn] structures/records: council {council!r} not recognised by "
                  f"the ePlanning API — rendering 'Not assessed' (fail-closed)")
            return None, "failed"
        frag = address.split(",")[0].strip() if address else address
        records = list(get_da_events(council, frag)) + list(get_pcc_events(council, frag))
        return records, "ok"
    except Exception as e:
        print(f"  [warn] structures/records lookup failed: {e}")
        return None, "failed"


# ---------------------------------------------------------------------------
# Contributions + corridors sentence builders — pure functions (golden-sentence
# tested in tests/test_conveyancing_corridors.py). Free of reportlab so the
# exact user-visible wording is testable without rendering a PDF.
# ---------------------------------------------------------------------------

_CONTRIB_INTRO = (
    "The following contributions plans apply to development in this location, as "
    "returned by the NSW Planning Portal contributions lookup. Charge amounts are "
    "set out in the plan documents linked — this report does not calculate "
    "contribution amounts."
)
_CONTRIB_EMPTY = (
    "No contributions plans returned for this location by the NSW Planning Portal."
)
_CONTRIB_FAILED = (
    "Not assessed — contributions lookup unavailable at report generation. "
    "Contributions plans for this council can be checked on the NSW Planning "
    "Portal or with the council directly."
)


def build_contributions_lines(contributions: Optional[dict]) -> dict:
    """Section 10 content from the three-state /cp result.

    Returns {"state": "found"|"empty"|"failed", "intro": str|None,
             "plan_lines": [{"name", "url"}], "hpc_line": str|None,
             "hpc_url": str|None, "status_line": str|None}.
    Plan and HPC names render verbatim; a failed (or never-run) lookup states
    "Not assessed", never an implied absence of plans.
    """
    status = (contributions or {}).get("status")
    out = {"state": "failed", "intro": None, "plan_lines": [],
           "hpc_line": None, "hpc_url": None, "status_line": None}

    if status == "found":
        out["state"] = "found"
        out["plan_lines"] = [
            {"name": p.get("plan_name") or "(unnamed plan in portal response)",
             "url": p.get("plan_url")}
            for p in (contributions.get("plans") or [])
        ]
        if out["plan_lines"]:
            out["intro"] = _CONTRIB_INTRO
        else:
            # HPC-only response: don't announce a plan list that isn't there —
            # state the queried-empty plans fact, then the HPC line renders.
            out["status_line"] = _CONTRIB_EMPTY
        hpc = contributions.get("hpc")
        if hpc:
            line = "Housing and Productivity Contribution: " + (
                hpc.get("name") or "mapped at this location"
            )
            if hpc.get("component"):
                line += f" — component {hpc['component']}"
            if hpc.get("commenced_date"):
                line += f", commenced {hpc['commenced_date']}"
            out["hpc_line"] = line + "."
            out["hpc_url"] = hpc.get("ministerial_order_url")
        return out

    if status == "empty":
        out["state"] = "empty"
        out["status_line"] = _CONTRIB_EMPTY
        return out

    out["status_line"] = _CONTRIB_FAILED
    return out


_CORRIDORS_ALL_CLEAR = (
    "No land-reservation-acquisition areas, mapped rail corridor zones, or portal "
    "property warnings were returned for this lot."
)
# (sub-check key, phrase used in the clean sentence, phrase used in "Not assessed")
_CORRIDOR_CHECKS = (
    ("lra", "land-reservation-acquisition areas", "land-reservation-acquisition map"),
    ("rail_corridors", "mapped rail corridor zones", "rail corridor mapping"),
    ("warnings", "portal property warnings", "portal property warnings"),
)
_CORRIDORS_BASIS_NOTE = (
    "Spatial checks in this section used a 30 m radius around the lot centroid — "
    "the lot boundary geometry was unavailable at report generation."
)
_CORRIDORS_SOURCE_LINE = (
    "Sources: NSW ePlanning Land Reservation Acquisition layer (LEP acquisition "
    "mapping); Sydney Trains corridor protection mapping (SEPP Transport and "
    "Infrastructure 2021); NSW Planning Portal property warnings."
)


def _lra_alert_text(item: dict, query_basis: str) -> str:
    """One LRA alert sentence — LABEL/AUTHORITY/EPI_NAME verbatim, currency
    date from the feature's own CURRENCY_DATE. States map presence only —
    never acquisition intent."""
    label = item.get("LABEL") or item.get("LRA_TYPE") or "type not stated in the mapping layer"
    authority = item.get("AUTHORITY") or "not stated in the mapping layer"
    epi = item.get("EPI_NAME") or "instrument not stated in the mapping layer"
    currency = item.get("currency_date")
    provenance = f"({epi}, map current to {currency})" if currency else f"({epi})"
    if query_basis == "lot_polygon":
        prefix = "Part of this lot is within a Land Reservation Acquisition area"
    else:
        prefix = "A Land Reservation Acquisition area is mapped within 30 m of the lot centroid"
    return (
        f"{prefix}: {label} — acquiring authority: {authority} {provenance}. "
        "A s10.7 certificate and the LEP acquisition clause state the effect."
    )


def build_corridors_lines(corridors: Optional[dict]) -> dict:
    """Section 11 content from the three-state corridors payload.

    Returns {"tile_flip": bool, "alert_rows": [str], "note_rows": [str],
             "not_assessed_rows": [str], "clean_line": str|None,
             "basis_note": str|None, "source_line": str}.

    Only an LRA hit flips the cover CONSTRAINTS tile. A failed sub-check
    renders "Not assessed" while the others still render; the clean sentence
    is only built from sub-checks that actually ran and returned empty.
    """
    co = corridors or {}
    basis = co.get("query_basis")
    out = {
        "tile_flip": False, "alert_rows": [], "note_rows": [],
        "not_assessed_rows": [], "clean_line": None,
        "basis_note": _CORRIDORS_BASIS_NOTE if basis == "centroid_30m" else None,
        "source_line": _CORRIDORS_SOURCE_LINE,
    }

    empty_phrases = []
    for key, clean_phrase, na_phrase in _CORRIDOR_CHECKS:
        sub = co.get(key) or {}
        status = sub.get("status")
        items = sub.get("items") or []
        if status == "found" and items:
            if key == "lra":
                out["tile_flip"] = True
                for it in items:
                    out["alert_rows"].append(_lra_alert_text(it, basis))
            elif key == "rail_corridors":
                for it in items:
                    zone = it.get("zone") or "Rail corridor zone"
                    agency = it.get("agency") or "not stated in the mapping layer"
                    leg = it.get("defining_legislation") or "not stated in the mapping layer"
                    out["note_rows"].append(
                        f"{zone} mapped at this location — agency: {agency}; "
                        f"defining legislation: {leg} (Sydney Trains corridor mapping)."
                    )
            else:
                for it in items:
                    out["note_rows"].append(
                        f"NSW Planning Portal property warning: {it.get('title')}."
                    )
        elif status == "empty" or (status == "found" and not items):
            empty_phrases.append(clean_phrase)
        else:
            out["not_assessed_rows"].append(
                f"Not assessed — {na_phrase} lookup unavailable at report generation."
            )

    if len(empty_phrases) == len(_CORRIDOR_CHECKS):
        out["clean_line"] = _CORRIDORS_ALL_CLEAR
    elif empty_phrases:
        joined = empty_phrases[0] if len(empty_phrases) == 1 else (
            " or ".join([", ".join(empty_phrases[:-1]), empty_phrases[-1]])
        )
        out["clean_line"] = f"No {joined} were returned for this lot."

    return out


# ---------------------------------------------------------------------------
# TOD-catchment uplift disclosure (Section 12) — FLOOR ONLY.
#
# Deliberate scope decision (2026-07-07): the paid conveyancing PDF renders the
# TOD catchment disclosure + instrument attribution + the conservative
# as-of-right baseline from the capacity engine. It does NOT quantify the
# uplift CEILING (the "up to N dwellings" figure) — that dwelling-count claim in
# a legal document is held back pending a legal wording review. The block is
# suppressed on strata lots (a single strata lot is not independently
# redevelopable) and on non-TOD lots. All figures come from the engine result
# object — no dwelling number is ever composed in this builder.
# ---------------------------------------------------------------------------

_TOD_SCOPE_LINE = (
    "This is an arithmetic baseline computed from mapped planning controls — not "
    "a development approval outcome. Development outcomes are determined by the "
    "consent authority on the merits of a development application."
)
_TOD_UPLIFT_HELD = (
    "A Transport Oriented Development catchment can enable higher-density "
    "residential development above this baseline, subject to a development "
    "application under State Environmental Planning Policy (Housing) 2021. This "
    "report does not quantify that upper limit."
)

# Human-readable engine form labels (engine dev_type -> plain English).
_TOD_FORM_LABELS = {
    "dwelling_house": "detached dwelling",
    "dual_occupancy": "dual occupancy",
    "attached_dwelling": "attached dwellings (terraces)",
    "manor_house": "manor house",
    "multi_dwelling_housing": "multi-dwelling housing",
    "residential_flat_building": "residential flat building",
    "shop_top_housing": "shop-top housing",
}


def _tod_form_label(form: Optional[str]) -> str:
    if not form:
        return "the mapped residential form"
    return _TOD_FORM_LABELS.get(form, form.replace("_", " "))


def build_tod_uplift_lines(
    tod: Optional[dict],
    capacity,
    is_strata: bool,
    lot_area_source: Optional[str] = None,
) -> dict:
    """Section 12 content — floor-only TOD-catchment disclosure.

    Args:
        tod: fetch_tod_catchment result ({"in_tod", "epi_name", ...}) or None
             when both catchment-layer queries failed.
        capacity: ConstraintArithmeticResult from the capacity engine (floor
             computed with ceiling_dev_type=None), or None when the engine call
             failed / was not run.
        is_strata: True suppresses the block (a single strata lot is not
             independently redevelopable).
        lot_area_source: provenance label for the lot area input (ledger).

    Returns {"render": bool, "not_assessed": bool, "epi_name": str|None,
             "disclosure": str|None, "baseline": str|None, "held_line": str|None,
             "ledger": [str], "scope": str|None}.

    Four-state (output-grounding fix 4, 2026-08-03):
      - strata → render False (a single strata lot is not independently
        redevelopable; suppressed whatever the catchment status).
      - catchment lookup FAILED (tod is None) → render True + not_assessed
        with an explicit could-not-be-completed disclosure. Previously this
        rendered False — the section vanished, indistinguishable from
        "checked, not in a catchment" (DQ-36's silent-omission twin).
      - checked and NOT in a catchment → render False (genuinely not
        applicable; the opportunity block stays silent).
      - in a TOD catchment but the engine baseline failed
        → render True + not_assessed (the catchment IS disclosed; the baseline
          states "Not assessed", never a fabricated figure).
      - in a TOD catchment with an engine result
        → full floor-only block.
    """
    out = {"render": False, "not_assessed": False, "epi_name": None,
           "disclosure": None, "baseline": None, "held_line": None,
           "ledger": [], "scope": None}

    if is_strata:
        # A single strata lot is not independently redevelopable — the block
        # is suppressed whatever the catchment status (unchanged behaviour).
        return out

    # tod is None ⇔ both catchment-layer queries failed. The section must
    # RENDER saying so (output-grounding fix 4): a vanished section is
    # indistinguishable from "checked, not in a catchment" — DQ-36's
    # silent-omission twin. The earlier doctrine ("absence is not a false
    # safety claim, so stay silent") conflated the two absence states.
    if tod is None:
        out["render"] = True
        out["not_assessed"] = True
        out["disclosure"] = (
            "Not assessed — the Transport Oriented Development (TOD) catchment "
            "check could not be completed at report generation. This report "
            "makes no claim about TOD status either way; the catchment layers "
            "can be checked directly on the NSW Planning Portal spatial viewer."
        )
        out["baseline"] = (
            "No development baseline is computed while the catchment status "
            "is unknown."
        )
        return out

    # Checked and NOT in a catchment — genuinely not applicable; the
    # opportunity block stays silent (unchanged behaviour).
    if not tod.get("in_tod"):
        return out

    epi = tod.get("epi_name") or "State Environmental Planning Policy (Housing) 2021"
    out["render"] = True
    out["epi_name"] = epi
    out["disclosure"] = (
        f"This lot is within a Transport Oriented Development (TOD) catchment "
        f"mapped under {epi}."
    )
    out["scope"] = _TOD_SCOPE_LINE
    out["held_line"] = _TOD_UPLIFT_HELD

    if capacity is None:
        out["not_assessed"] = True
        out["baseline"] = (
            "Not assessed — the development-baseline computation was unavailable "
            "at report generation."
        )
        return out

    # Every figure below is READ from the engine result object — never composed.
    form = getattr(capacity, "as_of_right_form", None) or getattr(capacity, "dev_type", None)
    dwellings = getattr(capacity, "as_of_right_dwellings", None)
    if dwellings is None:
        dwellings = getattr(capacity, "realistic_dwellings", None)
    gfa = getattr(capacity, "realistic_gfa_m2", None)
    if gfa is None:
        gfa = getattr(capacity, "lep_envelope_gfa_m2", None)
    binding = getattr(capacity, "binding_constraint_label", None)

    form_label = _tod_form_label(form)
    if dwellings is not None:
        _dw = f"{dwellings} dwelling" + ("s" if dwellings != 1 else "")
        baseline = (
            f"The as-of-right residential baseline from the mapped controls is "
            f"{_dw} ({form_label}), subject to a development application."
        )
    else:
        baseline = (
            f"The as-of-right residential baseline from the mapped controls is a "
            f"{form_label}, subject to a development application."
        )
    if gfa is not None:
        baseline += (
            f" The LEP building envelope from these controls is approximately "
            f"{int(round(gfa)):,} m² gross floor area."
        )
        if binding:
            baseline += f" {binding}."
    out["baseline"] = baseline

    # Input ledger — the figures that fed the baseline, and the engine's own
    # named gaps (a baseline without its inputs named is the D1 defect class).
    ledger = []
    lot_area = getattr(capacity, "lot_area_m2", None)
    if lot_area is not None:
        _src = f" ({lot_area_source})" if lot_area_source else ""
        ledger.append(f"Lot area: {int(round(lot_area)):,} m²{_src}")
    lep_h = getattr(capacity, "lep_height_m", None)
    ledger.append(f"LEP height limit: {lep_h} m" if lep_h is not None
                  else "LEP height limit: not available")
    lep_f = getattr(capacity, "lep_fsr", None)
    ledger.append(f"LEP floor space ratio: {lep_f}" if lep_f is not None
                  else "LEP floor space ratio: not available")
    for gap in (getattr(capacity, "gaps", None) or []):
        ledger.append(str(gap))
    out["ledger"] = ledger
    return out


# ---------------------------------------------------------------------------
# Structures & records reconciliation (Section 13) — STAGE 1 (records-only).
#
# THE CORE LIABILITY RULE: this section NEVER states, implies, or lets a reader
# infer that a structure is unapproved / illegal / unauthorised / non-compliant
# / a breach / without consent. It states a FACTUAL reconciliation gap and turns
# it into a QUESTION for the vendor. Every no-match sentence carries three
# hedges — the ~2019 record window, the exempt-development possibility, and the
# question-for-vendor + s10.7/council-records direction. The exhaustive
# no-verdict-word test in tests/test_conveyancing_structures.py renders every
# branch and fails if any forbidden framing appears on ANY path.
#
# Stage 1 uses ONLY the application records the pipeline can already fetch
# (pre_da_history OnlineDA/OnlineCDC) — no imagery/detection call. Structure
# detection is a Stage 2 capability; until it runs, the section says so plainly
# rather than implying "no unauthorised structures".
# ---------------------------------------------------------------------------

# Minimum detection confidence before a structure may generate a reconciliation
# gap line (risk #3: SAM can mis-segment shadow/roof/vegetation). Below this,
# a detection is dropped, never rendered as a gap.
_STRUCT_CONFIDENCE_FLOOR = 0.55

_STRUCT_INTRO = (
    "This section lists development and complying-development applications on "
    "record for the property. Where structure detection from aerial imagery has "
    "been performed, a structure that does not match a record is flagged for you "
    "to check with the vendor and against council records. It does not draw a "
    "conclusion about any structure — the records available to us begin around "
    "2019, and many structures are exempt development that require no application."
)
_STRUCT_NO_RECORDS = (
    "No development or complying-development applications for this property "
    "appear in the NSW Planning Portal records available to us (which begin "
    "around 2019). This is common for established properties: earlier approvals "
    "are held by council, and a structure that is exempt development leaves no "
    "record here. The absence of a record here is not, on its own, a finding "
    "about any structure on the lot."
)
_STRUCT_MATCH_CAVEAT = (
    "Records are matched to the property by address text (the NSW Planning "
    "Portal does not key applications to a lot identifier), so this list may "
    "include nearby properties on the same street — check each application "
    "number against the property before relying on it."
)
_STRUCT_DETECTION_NOT_RUN = (
    "Structure detection from aerial imagery was not performed for this report, "
    "so a visible-structure reconciliation is not included here. The applications "
    "on record above are the development history available to us for this property."
)
_STRUCT_RECORDS_FAILED = (
    "Not assessed — the application-records lookup was unavailable at report "
    "generation. Check the NSW Planning Portal and council records for the "
    "development history of this property."
)
# The hedged no-match sentence — the CEILING of what may ever be said, and the
# feature's highest-liability string. Restructured after an adversarial legal
# red-team (2026-07-07): it LEADS with the data-window limitation (not the
# "visible structure / no record" pairing that builds the imputation), states
# the innocent causes as the EXPECTED result, carries an explicit non-imputation
# line, and drops the "question for the vendor" framing (which presupposes a
# problem). Every clause is load-bearing (the test asserts 2019 + exempt +
# vendor + non-imputation + s10.7 tokens; deleting any fails). This string is
# DORMANT in Stage 1 (no detections) — it needs legal sign-off before Stage 2
# ever renders it to a reader.
_STRUCT_GAP_SENTENCE = (
    "The application records available to us begin around 2019 and do not "
    "include a lodged application matching this structure. That is the expected "
    "result for a structure that is exempt development and needs no application, "
    "one predating the record window, or one held only in council's own records "
    "rather than the Portal — none of which appear in this dataset. The absence "
    "of a matching record here is not, on its own, a finding about the structure. "
    "To see the full development history, ask the vendor and check a current "
    "Section 10.7 planning certificate and council records."
)


def _struct_record_line(rec: dict) -> str:
    """One application-record line — values rendered verbatim from the record."""
    app_type = rec.get("app_type") or "Application"
    detail = rec.get("dev_type") or rec.get("description") or "type not stated in the record"
    date = rec.get("date") or rec.get("date_updated") or "date not stated"
    status = rec.get("status") or "status not stated"
    pan = rec.get("pan") or "PAN not stated"
    return f"{app_type} — {detail} ({date}, {status}). {pan}."


def _struct_detection_matches_record(detection: dict, records: list) -> bool:
    """Conservative keyword match: a detected structure is 'matched' when a
    record's development type / description references its label. Deliberately
    simple — a false NON-match only produces a hedged question, never a claim."""
    label = str(detection.get("label") or "").lower().strip()
    if not label:
        return False
    for rec in records or []:
        hay = f"{rec.get('dev_type') or ''} {rec.get('description') or ''}".lower()
        if label and label in hay:
            return True
    return False


def build_structures_records_lines(
    records,
    detections=None,
    records_status: Optional[str] = None,
) -> dict:
    """Section 13 content — structure-vs-records reconciliation (Stage 1).

    Args:
        records: list of subject-lot DA/CDC record dicts (pan/app_type/dev_type/
            date/status), [] when the lookup ran and found none, or None when it
            was not run.
        detections: list of visible-structure dicts (label/confidence/imagery_date)
            or None when detection was not performed (Stage 1: always None live).
        records_status: "failed" when the records lookup errored (renders
            "Not assessed", never an implied absence of applications).

    Returns {"render", "not_assessed", "intro", "record_lines" [str],
             "status_line" str|None, "gap_lines" [str], "detection_note" str|None}.

    NEVER emits a verdict word on any path — a no-match is always the hedged
    question sentence, and detection-not-run is stated plainly.
    """
    out = {"render": True, "not_assessed": False, "intro": _STRUCT_INTRO,
           "record_lines": [], "status_line": None, "gap_lines": [],
           "detection_note": None}

    # A failed lookup (or no list at all) is fail-visible "Not assessed" — never
    # an implied "no applications exist". [] (ran, found none) is distinct.
    if records_status == "failed" or records is None:
        out["not_assessed"] = True
        out["status_line"] = _STRUCT_RECORDS_FAILED
        return out

    if records:
        out["record_lines"] = [_struct_record_line(r) for r in records]
    else:
        out["status_line"] = _STRUCT_NO_RECORDS

    # Reconciliation against detections (Stage 1: detections is None -> not run).
    if detections is None:
        out["detection_note"] = _STRUCT_DETECTION_NOT_RUN
        return out

    usable = [d for d in detections
              if (d.get("confidence") is None or d.get("confidence") >= _STRUCT_CONFIDENCE_FLOOR)]
    for det in usable:
        if not _struct_detection_matches_record(det, records):
            out["gap_lines"].append(_STRUCT_GAP_SENTENCE)
    if not usable:
        out["detection_note"] = _STRUCT_DETECTION_NOT_RUN
    return out


# ── Climate & hazard-exposure projection layer (Section 13 / 12) ────────────
# NARCliM 2.0 regional downscaled projections. The dataset attribution mirrors
# services/climate_risk_score.py so the PDF and the composite scorer cite the
# projection source identically. Framing is factual-metrics-only per the legal
# assessment: NO composite score, NO band/verdict, NO insurability/safety/value
# claims — modelled projection numbers with scenario + epoch labels only.
_NARCLIM_SOURCE_LINE = (
    "Source: NARCliM 2.0 regional climate projections (NSW Government / AdaptNSW), "
    "ACCESS-ESM1.5 global model downscaled to approximately 4 km. Epochs: baseline "
    "2015–2024, mid-century 2050–2069, late-century 2080–2099. Emissions "
    "scenarios: SSP2-4.5 and SSP3-7.0. Retrieved for this report on {date}."
)
_CLIMATE_FRAMING_LINE = (
    "The figures below are modelled regional climate projections for this location "
    "under two emissions scenarios. They describe modelled future climate variables "
    "— not current hazard mapping, not a forecast of any individual event, and not "
    "a statement about this property's value or its insurance cover. Current flood "
    "and bushfire status for this property is set out in the Risk Summary (Section 1) "
    "above; the projections here are a separate, forward-looking layer and do not "
    "change that mapping."
)
_CLIMATE_UNAVAILABLE = (
    "Climate projections are not included in this report — the NARCliM 2.0 "
    "projection dataset was not available at report generation."
)
_CLIMATE_OUT_OF_DOMAIN = (
    "This location is outside the NARCliM 2.0 regional projection domain "
    "(south-east Australia), so modelled climate projections are not provided "
    "for this address."
)
_CLIMATE_NO_COVERAGE = (
    "No NARCliM 2.0 projection grid cell was returned for this location, so "
    "modelled climate projections are not provided for this address."
)


def _climate_metric_rows(summary: dict) -> list[str]:
    """One factual sentence per variable, every number READ from the summary
    (never composed). A variable whose baseline or late-century values are
    absent is skipped — a partial grid response names only what it returned.
    Scenario (SSP2-4.5 / SSP3-7.0) and epoch labels ride with every number so a
    late-century figure can never read as current (SPEC CORRECTIONS C5/C6)."""
    rows: list[str] = []

    def _fmt(prefix: str, label: str, unit: str, dp: int) -> Optional[str]:
        base = summary.get(f"{prefix}_baseline")
        mc_lo = summary.get(f"{prefix}_mid_century_mid")
        mc_hi = summary.get(f"{prefix}_mid_century_high")
        lc_lo = summary.get(f"{prefix}_late_century_mid")
        lc_hi = summary.get(f"{prefix}_late_century_high")
        if base is None or lc_lo is None or lc_hi is None:
            return None
        parts = [f"{label}: {base:.{dp}f}{unit} in the baseline period (2015–2024)"]
        if mc_lo is not None and mc_hi is not None:
            parts.append(
                f"{mc_lo:.{dp}f}{unit} (SSP2-4.5) or {mc_hi:.{dp}f}{unit} "
                f"(SSP3-7.0) by 2050–2069"
            )
        parts.append(
            f"{lc_lo:.{dp}f}{unit} (SSP2-4.5) or {lc_hi:.{dp}f}{unit} "
            f"(SSP3-7.0) by 2080–2099"
        )
        return "; ".join(parts) + "."

    for prefix, label, unit, dp in (
        ("hot_days", "Days at or above 35°C (per year)", "", 0),
        ("temp", "Mean annual temperature", "°C", 1),
        ("precip", "Mean daily rainfall", " mm", 2),
    ):
        r = _fmt(prefix, label, unit, dp)
        if r:
            rows.append(r)
    return rows


def build_climate_lines(
    climate: Optional[dict],
    report_date: Optional[str] = None,
) -> dict:
    """Section content for the NARCliM 2.0 climate-projection layer.

    prior-art-checked: consumes climate_risk_raster.query_narclim_summary output
    (fetched in services/conveyancing.py); this builder adds NO hazard logic and
    computes NO score — it renders the projection numbers the raster returned,
    with scenario + epoch labels, per SPEC CORRECTIONS C1/C3/C5.

    Four fetcher states in ``climate["state"]``:
      present       → per-variable rows + framing + source (render True)
      no_coverage   → honest "no grid cell" line, no number (render True)
      out_of_domain → honest "outside domain" line, no number (render True)
      unavailable   → honest "not available" line, no number (render True)
      None/absent   → render False (section omitted; never a false claim)

    Returns {"render", "state", "rows", "framing", "source_line",
             "status_line", "grid_note"}. A projection NUMBER is emitted only in
    the "present" state — states b/c/d carry status_line text and no figure.
    """
    out = {"render": False, "state": "absent", "rows": [], "framing": None,
           "source_line": None, "status_line": None, "grid_note": None}
    state = (climate or {}).get("state")
    if not state:
        return out

    if state == "present":
        summary = (climate or {}).get("summary") or {}
        rows = _climate_metric_rows(summary)
        if not rows:
            # Payload claimed present but no renderable variable — degrade to the
            # honest no-coverage line rather than emit an empty section.
            out.update(render=True, state="no_coverage",
                       status_line=_CLIMATE_NO_COVERAGE)
            return out
        out["render"] = True
        out["state"] = "present"
        out["rows"] = rows
        out["framing"] = _CLIMATE_FRAMING_LINE
        out["source_line"] = _NARCLIM_SOURCE_LINE.format(
            date=report_date or "the date of generation"
        )
        gd = summary.get("grid_distance_km")
        if gd is not None:
            out["grid_note"] = (
                f"Nearest NARCliM projection grid cell: {gd:g} km from the "
                f"property centroid."
            )
        return out

    out["render"] = True
    out["state"] = state
    if state == "out_of_domain":
        out["status_line"] = _CLIMATE_OUT_OF_DOMAIN
    elif state == "no_coverage":
        out["status_line"] = _CLIMATE_NO_COVERAGE
    else:  # "unavailable" or any unrecognised non-present state
        out["state"] = "unavailable"
        out["status_line"] = _CLIMATE_UNAVAILABLE
    return out


# ── Estuarine tidal inundation layer (mapped-extent disclosure) ─────────────
# NSW Estuarine Inundation 2025 (SEED, CC BY 4.0). Terminology rule: the
# anchor term in every factual claim is "estuarine tidal inundation" — never
# "coastal" as a coverage word (a beachfront non-estuary buyer would wrongly
# assume open-coast coverage). Factual mapped-extent statements only: NO
# verdict, NO "at risk", NO safety/value/insurance claim, and the section
# never flips the cover CONSTRAINTS tile.
_COASTAL_SCOPE_LINE = (
    "Scope: this mapping covers estuarine (river, lake, bay and tidal-inlet) "
    "tidal inundation only. It does NOT cover open-coast/surf inundation or "
    "coastal erosion, and it does NOT cover rainfall-driven river flooding — "
    "current flood mapping for this property is set out in the Risk Summary."
)
_COASTAL_FRAMING_LINE = (
    "The NSW Government's 2025 estuarine inundation dataset maps how often "
    "low-lying land near estuaries is under tidal water, modelled under the "
    "SSP3-7.0 emissions scenario at 2050 and 2100. The lines below state "
    "whether this property intersects that mapped extent. This is modelled "
    "future tidal mapping — not current hazard mapping, not a forecast of any "
    "individual event, and not a statement about this property's value or its "
    "insurance cover."
)
_COASTAL_SOURCE_LINE = (
    "Source: NSW Estuarine Inundation — 2025 (NSW Department of Climate "
    "Change, Energy, the Environment and Water; SEED portal; CC BY 4.0; "
    "published 24 November 2025). Scenario SSP3-7.0 at 2050 and 2100; mapped "
    "extents held at the source's ~5 m resolution. Retrieved for this report "
    "on {date}."
)
_COASTAL_OUTSIDE_LINE = (
    "This property is outside the mapped estuarine tidal inundation extent "
    "for both 2050 and 2100 (SSP3-7.0)."
)
_COASTAL_UNAVAILABLE = (
    "Estuarine tidal inundation was not assessed — the mapped-extent layer "
    "was not available at report generation."
)
_COASTAL_POINT_BASIS_NOTE = (
    "Checked against the property point — the lot polygon was unavailable for "
    "this query. A lot-boundary check can differ where the mapped extent "
    "crosses only part of the lot."
)


def _coastal_year_row(year: int, tier: dict) -> Optional[str]:
    """One factual sentence per mapped year — every figure READ from the row.

    A tier whose days_per_year is absent is skipped (never composed); the raw
    loader-written `value` string rides along so the stored row is quotable.
    """
    days = tier.get("days_per_year")
    if days is None:
        return None
    pct = None
    m = re.search(r"\(([\d.]+%)\)", tier.get("value") or "")
    if m:
        pct = m.group(1)
    freq = f"exceeded {days:g} days per year"
    if pct:
        freq += f" ({pct} of days)"
    return (
        f"{year}: intersects the mapped extent — most frequent mapped tier at "
        f"this property: tidal inundation {freq}, under SSP3-7.0."
    )


def build_coastal_inundation_lines(
    coastal: Optional[dict],
    report_date: Optional[str] = None,
) -> dict:
    """Section content for the estuarine tidal inundation mapped-extent layer.

    prior-art-checked: consumes get_coastal_inundation_live output; same
    render-state contract as build_climate_lines (its sibling forward-looking
    disclosure layer). This builder adds NO hazard logic and computes NO
    figure — it renders what the stored rows state, with the scope sentence on
    every rendered state so "estuarine" can never read as general coastal
    coverage.

    States in ``coastal["status"]``:
      intersects → framing + per-year rows + scope + source (render True)
      outside    → honest outside-mapped-extent line + scope + source (render True)
      failed     → "not assessed" line, no extent claim (render True)
      None/absent/unrecognised → render False (section omitted; never a false claim)

    Returns {"render", "state", "rows", "framing", "scope_line",
             "source_line", "status_line", "basis_note"}.
    """
    out = {"render": False, "state": "absent", "rows": [], "framing": None,
           "scope_line": None, "source_line": None, "status_line": None,
           "basis_note": None}
    status = (coastal or {}).get("status")
    if status not in ("intersects", "outside", "failed"):
        return out

    out["render"] = True
    out["state"] = status
    if status == "failed":
        out["status_line"] = _COASTAL_UNAVAILABLE
        return out

    out["scope_line"] = _COASTAL_SCOPE_LINE
    out["source_line"] = _COASTAL_SOURCE_LINE.format(
        date=report_date or "the date of generation"
    )
    if coastal.get("query_basis") == "point":
        out["basis_note"] = _COASTAL_POINT_BASIS_NOTE

    if status == "outside":
        out["status_line"] = _COASTAL_OUTSIDE_LINE
        return out

    rows = []
    for year in sorted((coastal.get("years") or {}).keys(), key=str):
        if year is None:
            continue
        row = _coastal_year_row(int(year), coastal["years"][year] or {})
        if row:
            rows.append(row)
    if not rows:
        # Claimed intersects but nothing renderable — fail closed to the
        # honest not-assessed line rather than an empty extent claim.
        out.update(state="failed", rows=[], scope_line=None, source_line=None,
                   basis_note=None, status_line=_COASTAL_UNAVAILABLE)
        return out
    out["state"] = "intersects"
    out["rows"] = rows
    out["framing"] = _COASTAL_FRAMING_LINE
    return out


# Layers the unmapped-coverage footnote reports on. Bushfire is deliberately
# absent: it is checked live against the NSW RFS BFPL service, not our ingest.
_UNMAPPED_NOTE_LAYERS = (
    ("flood", "flood"), ("riparian", "riparian"),
    ("wetlands", "wetlands"), ("landslide", "landslide"),
    ("biodiversity", "biodiversity"),
)


def build_unmapped_note(covered_layers: Optional[set]) -> Optional[str]:
    """Coverage footnote for PostGIS layers with no ingested data for this LGA.

    The wording owns the gap as OURS ("PlotDetect's ingested…") — absence from
    our ingest is not a statement about the NSW state layer or the council's
    own mapping (D3 regression: the old text blamed the NSW state layer).
    Returns None when everything is covered or coverage is unknown.
    """
    if covered_layers is None:
        return None
    unmapped = [lbl for lbl, lt in _UNMAPPED_NOTE_LAYERS if lt not in covered_layers]
    if not unmapped:
        return None
    return (
        f"<i>Not present in PlotDetect's ingested state-layer data for this LGA:</i> "
        f"{', '.join(unmapped)}. "
        "These layers are ingested from NSW Government ArcGIS services; absence here means our "
        "ingestion has no features for this council — it is not a statement about the council's "
        "own mapping. Confirm with council or a Section 10.7 planning certificate."
    )


def _check_reportlab():
    try:
        import reportlab  # noqa
    except ImportError:
        print("ERROR: reportlab not installed — run: pip install reportlab")
        sys.exit(1)


def _flag_cell(text: str, style_name: str, styles_map: dict):
    from reportlab.platypus import Paragraph
    return Paragraph(text, styles_map[style_name])


def _xml_escape(text) -> str:
    """Escape &, <, > for reportlab Paragraph markup — external values (plan
    names, layer labels, warning titles) render verbatim, never as markup."""
    from xml.sax.saxutils import escape
    return escape(str(text))


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
    # Per-fetch DB-failure map from _fetch_db_data (output-grounding fix 3):
    # {"das","lep","dcp","heritage"} → True when that check could not be
    # completed. A failed check renders "could not be determined", never a
    # clean absence. None (older callers) = nothing reported failed.
    db_fetch_failed: Optional[dict] = None,
    proximity_m: Optional[dict] = None,
    bushfire_live: Optional[dict] = None,
    anef_live: Optional[dict] = None,
    contributions: Optional[dict] = None,
    corridors: Optional[dict] = None,
    tod: Optional[dict] = None,
    capacity=None,
    structures_records=None,
    structures_records_status: Optional[str] = None,
    climate: Optional[dict] = None,
    mine_subsidence: Optional[dict] = None,
    contaminated: Optional[dict] = None,
    servicing: Optional[dict] = None,
    coastal: Optional[dict] = None,
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

    # ------------------------------------------------------------------
    # Bushfire: the live NSW RFS BFPL result governs (D3). The ingested
    # PostGIS copy can be stale or missing for an LGA — reconcile before any
    # rendering so the cover tile, risk row, Section 5 note and consultant
    # table all agree with the live answer.
    # ------------------------------------------------------------------
    _bf_live_prone = (bushfire_live or {}).get("is_bushfire_prone")
    _bf_postgis_hit = next((o for o in unique_overlays if o["layer_type"] == "bushfire"), None)
    if _bf_live_prone is True and _bf_postgis_hit is None:
        _live_bf_overlay = {
            "layer_type": "bushfire",
            "value": (bushfire_live or {}).get("designation_category") or "Bushfire Prone Land",
            "instrument": "RFS_BFPL_LIVE",
            "lga": None,
        }
        unique_overlays = list(unique_overlays) + [_live_bf_overlay]
    elif _bf_live_prone is False and _bf_postgis_hit is not None:
        logger.warning(
            "Live RFS BFPL says not prone but ingested PostGIS has a bushfire hit (%s) — live wins",
            _bf_postgis_hit.get("value"),
        )
        unique_overlays = [o for o in unique_overlays if o["layer_type"] != "bushfire"]

    # ------------------------------------------------------------------
    # ANEF: a resolved contour value (curated anef_zones / live ePlanning)
    # governs over the ingest, same as bushfire above — synthesize the overlay
    # when the ingest missed it so the cover tile, delta callout, risk row,
    # Section 5 note and consultant table all state the contour. A lookup that
    # found nothing never REMOVES an ingested hit (the ingest polygon may
    # still be right — the note wording stays the honest fallback).
    # ------------------------------------------------------------------
    if (anef_live or {}).get("status") == "found" and not any(
        o["layer_type"] == "anef" for o in unique_overlays
    ):
        unique_overlays = list(unique_overlays) + [{
            "layer_type": "anef",
            "value": f"ANEF {_anef_value_display(anef_live)}",
            "instrument": "ANEF_VALUE_LOOKUP",
            "lga": None,
        }]

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
    # Sydney Drinking Water Catchment is a DA constraint (B&C SEPP 2021 Pt 6.2/6.5)
    # — it must flip the cover tile, not vanish (Bowral regression).
    if controls.get("sdwc"):
        _n_constraints += 1
    # Land Reservation Acquisition is a genuine planning constraint (SDWC
    # precedent) — an LRA hit flips the tile; rail/warn notes do NOT.
    _corridor_lines = build_corridors_lines(corridors)
    if _corridor_lines["tile_flip"]:
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
        # Normalise: "Category 1" / "Vegetation Category 1" → "1", "CAT 2" → "2",
        # "Flame Zone" stays as-is. Live RFS d_Category uses the "Vegetation" prefix.
        _bf_key = re.sub(r"(?i)^(?:vegetation\s+)?cat(?:egory)?\s*", "", _bf_val).strip()
        _bf_specific = BUSHFIRE_CATEGORIES.get(_bf_key) or BUSHFIRE_CATEGORIES.get(_bf_val)
        if _bf_specific:
            _bushfire_note_dynamic = _bf_specific
        # else fall back to BUSHFIRE_NOTE_DEFAULT (via static POSTGIS_NOTES entry)

    # ANEF — note carries the resolved contour value (or the explicit lookup
    # failure); None falls back to the static ANEF_NOTE.
    _anef_note_dynamic: str | None = None
    if "anef" in unique_by_type:
        _anef_note_dynamic = build_anef_note(anef_live)

    DELTA_CHECKS = [
        ("Biodiversity Values Map (BDAR trigger)", "biodiversity"),
        ("Riparian Land",            "riparian"),
        ("Wetlands",                 "wetlands"),
        ("Landslide Risk",           "landslide"),
        ("Flood Planning Area",      "flood"),
        ("Bushfire Prone Land",      "bushfire"),
        ("Aircraft Noise (ANEF)",    "anef"),
        ("Sydney Drinking Water Catchment", "sdwc"),
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
        if lt == "sdwc":              # portal layerintersect group, not a PostGIS layer
            return bool(controls.get("sdwc"))
        return lt in unique_by_type

    flagged = [label for label, lt in DELTA_CHECKS if _delta_hit(lt)]
    delta_lines = []
    for label, lt in DELTA_CHECKS:
        if _delta_hit(lt):
            delta_lines.append(f"<b>▲ {label}</b>")
        else:
            delta_lines.append(label)
    delta_body_text = "  ·  ".join(delta_lines)

    # s10.7(2) claim (D4): bushfire-prone status and flood-related development
    # controls ARE prescribed certificate matters (EP&A Reg 2021 Sch 2) — the
    # header must not claim otherwise. source_ref: EP&A Regulation 2021, Sch 2.
    callout_header = Paragraph(
        "Constraint screening — this report checks all of the following. Most are not itemised "
        "in a standard s10.7(2) certificate or title search; for bushfire and flood, the "
        "certificate states whether they apply and this report adds the mapped category and "
        "extent detail:",
        S("ch", fontSize=9, textColor=WHITE, fontName="Helvetica-Bold", leading=13),
    )
    # Three states, not two (DQ-36 class).
    #
    # `get_unique_overlays` catches every exception and returns ([], set(), {}), so a
    # PostGIS outage produces exactly the same empty `flagged` list as a genuinely
    # unconstrained property. This line then printed "No constraints identified for
    # this property" — a clean bill of health on a paid conveyancing report, off the
    # back of a query that never ran. Flood, bushfire, biodiversity and landslide are
    # precisely what the report is bought for.
    #
    # `covered_layers` is the discriminator: non-empty means the screen actually ran.
    _screen_ran = bool(covered_layers)
    if flagged:
        alert_suffix = (
            f"  <b>{len(flagged)} constraint(s) identified at this property — "
            f"see Risk Summary.</b>"
        )
    elif _screen_ran:
        alert_suffix = "  No constraints identified for this property."
    else:
        alert_suffix = (
            "  <b>Constraint screening did not complete — this is not a finding that "
            "the property is unconstrained. Re-run before relying on this section.</b>"
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
    _db_failed = db_fetch_failed or {}
    if dcp_setbacks_db:
        dcp_note = dcp_setbacks_db["dcp_name"]
    elif _db_failed.get("dcp"):
        # The query failed — say so; the old fallthrough claimed coverage facts
        # ("not extracted for this LGA") about a check that never ran (fix 3).
        dcp_note = "DCP setback controls: could not be retrieved this run (not assessed)"
    elif dcp_former_council:
        # DB fetch succeeded during main() but was not passed in — fallback
        dcp_note = dcp_former_council.replace("_", " ").title() + " DCP controls"
    else:
        dcp_note = "DCP setback controls: contact council for your LGA"

    _failed_check_labels = [label for key, label in (
        ("das", "nearby development applications"),
        ("lep", "Key Sites clause summaries"),
        ("dcp", "DCP setback controls"),
        ("heritage", "PostGIS heritage supplement"),
    ) if _db_failed.get(key)]

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
        "Utility (water/sewer) certificate — Sydney Water s73 in Sydney Water's area of operations; "
        "certificate from the local water utility (council) elsewhere (allow 1–4 weeks)",
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
    if _failed_check_labels:
        # Typed absence, one honest line for the whole report (fix 3): these
        # checks did not run to completion — "not assessed" is a different
        # state to "checked, none found", and this is where the reader learns
        # which one they got.
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            "<b>Checks that could not be completed for this report</b> (data "
            "unavailable at generation — not assessed, not clear): "
            + "; ".join(_failed_check_labels) + ".",
            ss["warn"],
        ))
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
        # 3. Layer not in our ingested coverage for this LGA — omit the row; the
        #    coverage footnote owns the gap. Absence of a portal layerintersect
        #    group is NOT evidence of absence (the portal does not return these
        #    layers for every LGA), so no "Clear — NSW Planning Portal" row is
        #    asserted from it (D7 semantics alignment).
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

    # Bushfire row — live NSW RFS BFPL query governs, never our ingest coverage (D3)
    _bf_text, _bf_style, _bf_source = build_bushfire_row(
        bushfire_live, unique_by_type.get("bushfire"),
    )

    risk_rows = [
        ["Constraint", "Finding", "Source"],
        # Portal-sourced planning designations
        ["Heritage Listing",                          heritage_flag,   "NSW Planning Portal"],
        ["Acid Sulfate Soils",                        ass_flag,        "NSW Planning Portal"],
        # Sydney Drinking Water Catchment — statutory citation rendered verbatim
        # from the portal Label (B&C SEPP 2021 Pt 6.2/6.5 + s171A EP&A Reg 2021)
        *([["Sydney Drinking Water Catchment",
            Paragraph(controls["sdwc"]["label"], ss["warn"]),
            "NSW Planning Portal"]]
          if controls.get("sdwc") else []),
        # Portal key site row suppressed when PostGIS already shows a hit (avoids duplicate rows)
        *([["LEP Key Site or Special Provision",      key_sites_flag,  "NSW Planning Portal"]]
          if not _postgis_key_site_hit else []),
        ["Additional Permitted Uses (LEP Sch. 1)",    apu_flag,        "PostGIS"],
        # PostGIS-sourced environmental overlays
        # flag() returns None when the layer is not mapped for this LGA — omit those rows
        flag("biodiversity", "Biodiversity Values Map (BDAR trigger)", "warn"),
        flag("riparian",     "Riparian Land",                          "warn"),
        flag("wetlands",     "Wetlands",                               "warn"),
        flag("landslide",    "Landslide Risk"),
        flag("flood",        "Flood Planning Area"),
        # PostGIS-sourced LEP constraints
        flag("key_sites",               "Key Site (site-specific LEP clause)", "warn"),
        flag("foreshore_building_line", "Foreshore Building Line", "warn"),
        flag("classified_road",         "Classified Road Frontage", "warn"),
        ["Bushfire Prone Land (BAL assessment)", Paragraph(_bf_text, ss[_bf_style]), _bf_source],
    ]
    # Mine subsidence + contaminated land — three-state builders; a failed
    # lookup renders "Not assessed", never "Clear" (WO-2 class).
    _ms_text, _ms_style, _ms_source = build_mine_subsidence_row(mine_subsidence)
    risk_rows.append([
        "Mine Subsidence District",
        Paragraph(_ms_text, ss[_ms_style]),
        _ms_source,
    ])
    _cl_text, _cl_style, _cl_source = build_contaminated_land_row(contaminated)
    risk_rows.append([
        "Contaminated Land (EPA register, 500 m)",
        Paragraph(_cl_text, ss[_cl_style]),
        _cl_source,
    ])
    # Sydney Water servicing — three-state; the Source cell is a live link back to the
    # Sydney Water GSP page (attribution required — data is © Sydney Water, guide only).
    _sv_text, _sv_style, _sv_source = build_servicing_row(servicing)
    try:
        from gsp_servicing import GSP_URL
    except ImportError:
        from services.gsp_servicing import GSP_URL
    risk_rows.append([
        "Water/Sewer Servicing (Sydney Water GSP)",
        Paragraph(_sv_text, ss[_sv_style]),
        Paragraph(f'<a href="{GSP_URL}" color="#2563EB">{_sv_source}</a>', ss["note"]),
    ])
    # ANEF row — three-state builder: contour value when resolved, honest
    # fallback when empty, explicit not-assessed on lookup failure. None when
    # the lot has no ingested ANEF overlay (row omitted, Bowral regression).
    _anef_row = build_anef_row(anef_live, unique_by_type.get("anef"))
    if _anef_row is not None:
        _an_text, _an_style, _an_source = _anef_row
        risk_rows.append([
            "Aircraft Noise Contour (ANEF)",
            Paragraph(_an_text, ss[_an_style]),
            _an_source,
        ])
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

    # Shadow risk row — build_shadow_row threads height_source so an assumed
    # 9 m envelope is never attributed to the LEP (D1)
    _sh_text, _sh_style, _sh_source = build_shadow_row(shadow_result)
    risk_rows.append([
        "Northern Development Shadow Risk",
        Paragraph(_sh_text, ss[_sh_style]),
        _sh_source,
    ])

    c1, c2, c3 = 65 * mm, 70 * mm, CW - 135 * mm
    story.append(table(risk_rows, [c1, c2, c3]))

    # Coverage footnote — owns the gap as ours; bushfire excluded (live-checked)
    _unmapped_note = build_unmapped_note(covered_layers)
    if _unmapped_note:
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(_unmapped_note, ss["note"]))

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
    # s10.7(2) claim (D4): only the layers genuinely absent from certificates are
    # named; bushfire/flood are prescribed matters (EP&A Reg 2021 Sch 2).
    story.append(Paragraph(
        "Sources: Heritage, ASS, Key Site, SEPP overlays, drinking water catchment — NSW Planning "
        "Portal layerintersect (live query). Bushfire Prone Land — NSW RFS BFPL (live query at "
        "report generation). Environmental and spatial overlays (biodiversity, riparian, wetlands, "
        "landslide, flood, ANEF, TOD, APU) — PostGIS spatial database ingested from NSW Government "
        "ArcGIS services. Coverage: 128 NSW councils. Biodiversity Values (BDAR trigger), ANEF "
        "contours, TOD precinct status and APU spatial footprints are not itemised in a standard "
        "s10.7(2) certificate or title search. Bushfire-prone status and flood-related development "
        "controls are prescribed s10.7(2) certificate matters — the certificate states whether they "
        "apply; this report adds the mapped category and extent detail.",
        ss["note"]
    ))
    # `is False` (not falsy): adg_compliant None means NOT ASSESSED — the ADG
    # methodology paragraph must not imply a concern verdict for it (fix 1).
    if shadow_result is not None and shadow_result.get("adg_compliant") is False:
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            "<b>Northern Development Shadow Risk</b> — modelled using the NSW Apartment Design Guide (ADG) "
            "standard: 5 key dates/times including the three Jun 21 (winter solstice) snapshots that determine "
            "ADG compliance. The model assumes a building at the modelled height — the LEP height limit where "
            "one is mapped for the lot, otherwise a standard two-storey (9 m) assumed envelope as labelled in "
            "the row above — on the lot immediately to the north, using the subject lot's own cadastral "
            "footprint as a symmetric proxy. "
            "This modelled risk is not part of a standard s10.7 certificate, title search, or conveyancing "
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
    _zc_parts = (controls.get("zone") or "").split()
    zone_code = _zc_parts[0].upper() if _zc_parts else ""
    zone_full = controls.get("zone_full") or ""
    zone_epi = controls.get("zone_epi") or ""
    legislation_url = controls.get("legislation_url") or ""
    if zone_full:
        # zone_full is the portal's zone NAME (e.g. "Medium Density Residential"),
        # not the LEP objectives text — label it as the zone (D7).
        story.append(Paragraph(
            f"<b>Zone ({zone_code}):</b> {zone_full}",
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
        # lep_clauses not pre-fetched (non-Inner West council) or the lookup
        # failed (fix 3) — show the raw ref either way, and say which it was.
        story.append(Paragraph("<b>Key Sites provisions:</b>", ss["body"]))
        _ks_suffix = (" (clause summaries could not be retrieved this run — "
                      "not assessed)") if _db_failed.get("lep") else ""
        story.append(Paragraph(
            f"• {_ks_clause} — refer to {legislation_url or 'the applicable LEP'}."
            f"{_ks_suffix}",
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
        _pz_parts = (controls.get("zone") or "").split()
        prop_zone = _pz_parts[0].upper() if _pz_parts else ""
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
        # Per-source "as at" line (output-grounding item 3). Three states:
        # a dated line with its basis; or nothing at all when no defensible
        # date exists — an undated claim is visible-by-absence and counted by
        # scripts/check_dcp_as_at_coverage.py, never papered over with the
        # generation date.
        if dcp_data.get("as_at_line"):
            story.append(Paragraph(dcp_data["as_at_line"], ss["note"]))
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
                        Paragraph(clause_or_page(sb["clause"], sb.get("pdf_page")) or "—", ss["note"]),
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
                        Paragraph(clause_or_page(sb["clause"], sb.get("pdf_page")) or "—", ss["note"]),
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

    elif _db_failed.get("dcp"):
        # The DCP query failed — a coverage claim ("not extracted for this
        # LGA") about a check that never ran is the fix-3 collapse. Say what
        # actually happened.
        story.append(Paragraph(
            "DCP setback controls could not be retrieved for this report — "
            "not assessed. This is a data-availability condition at report "
            "generation, not a statement about the council's DCP. Obtain the "
            "applicable DCP chapter directly from Council or the NSW Planning "
            "Portal.",
            ss["warn"]
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
            elif layer_type == "anef" and _anef_note_dynamic:
                display_note = _anef_note_dynamic
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
        # Bushfire is deliberately not claimed here — its status (including a
        # failed live check) is reported in the Section 1 risk row.
        story.append(Paragraph(
            "No acid sulfate soils, biodiversity, riparian, wetland, landslide, flood, "
            "aircraft noise, coastal hazard, or fire history overlays identified at this location. "
            "Bushfire-prone status is reported in Section 1 (live NSW RFS check).",
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
            class_ = ov.get("class") or ""
            # Class is part of the dedupe key: two Climate Zones rows with
            # different class values (e.g. BASIX Alterations 6 vs Buildings 24)
            # are distinct standards, not duplicates.
            key = (name, type_, class_)
            if key in seen:
                continue
            seen.add(key)
            plain = interpret_sepp(
                name, type_, ov.get("label") or "", "",
                class_=class_, map_title=ov.get("map_title") or "",
            )
            if plain is None:
                continue  # dedicated report section covers this overlay type
            sepp_rows.append([
                Paragraph(name or "—", ss["body"]),
                Paragraph(plain, ss["note"]),
            ])
        story.append(table(sepp_rows, [85 * mm, CW - 85 * mm]))
    else:
        story.append(Paragraph("No SEPP special provisions identified at this location.", ss["body"]))

    # Other planning instruments — fail-open capture from parse_controls (D2).
    # Titles are rendered verbatim from the portal response; no interpretation.
    _sdwc = controls.get("sdwc")
    _other_instruments = controls.get("other_instruments") or []
    # An LRA group captured here by the fail-open else is superseded by the
    # named Section 11 check — suppress it ONLY when that check found the hit
    # itself (a failed/empty Section 11 must not eat the fail-open capture).
    if _corridor_lines["tile_flip"]:
        _other_instruments = [
            oi for oi in _other_instruments
            if "land reservation acquisition" not in (oi.get("layer") or "").lower()
        ]
    if _sdwc or _other_instruments:
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(
            "<b>Other planning instruments mapped at this location</b> — returned by the NSW "
            "Planning Portal for this property:",
            ss["body"]
        ))
        story.append(Spacer(1, 1 * mm))
        if _sdwc:
            story.append(Paragraph(
                f"• <b>{_sdwc['layer']}:</b> {_sdwc['label']}",
                ss["note"]
            ))
        for oi in _other_instruments:
            _titles = "; ".join(oi.get("titles") or []) or "mapped at this location"
            story.append(Paragraph(
                f"• <b>{oi['layer']}:</b> {_titles}",
                ss["note"]
            ))
        story.append(Spacer(1, 2 * mm))

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

    _zs_parts = (controls.get("zone") or "").split()
    zone_code_sepp = _zs_parts[0].upper() if _zs_parts else ""
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
            # source_ref: SEPP (Housing) 2021 s53 — non-discretionary development
            # standards for secondary dwellings. The site-area figure is NOT
            # stated here (#684): the feasibility row above renders it from the
            # housing_sepp_standards table; this cell only cites the clause.
            "SEPP (Housing) 2021",
            "Residential zones — dual occ, secondary dwellings, complying dev",
            "Enables secondary dwellings, dual occupancy, and low-rise medium density "
            "housing pathways in eligible zones. Sets non-discretionary standards, "
            "including a site-area standard for secondary dwellings (s53), that a "
            "consent authority cannot use as refusal grounds when met.",
        ],
        [
            # source_ref: SEPP (Transport and Infrastructure) 2021 s2.120
            # (frontage to classified roads — consent authority considerations),
            # Division 17 (rail corridors — noise/vibration). The former 9 m
            # setback claim was a Codes SEPP Housing Code CDC standard wrongly
            # attributed to this instrument (D5) — do not reintroduce it here.
            "SEPP (Transport and Infrastructure) 2021",
            "Land adjoining classified roads and rail corridors",
            (
                "Development with frontage to a classified road requires the consent authority "
                "to be satisfied on access arrangements and road safety (s2.120). Residential "
                "development near rail corridors may require noise and vibration assessment. "
                + ("Classified road frontage identified at this property — applies." if has_classified_road
                   else "No classified road frontage identified at this property.")
            ),
        ],
        [
            # source_ref: SEPP (Resilience and Hazards) 2021 Ch 4 (remediation of
            # land, s4.6 consent authority considerations), Ch 2 (coastal
            # management — mapped areas only). Flood planning is an LEP control
            # (Standard Instrument cl 5.21), not this SEPP — former text wrongly
            # claimed statewide flood provisions here.
            "SEPP (Resilience and Hazards) 2021",
            "Contaminated land (all land); coastal management (mapped areas)",
            "The consent authority must consider whether land is contaminated and, if so, "
            "whether remediation is required before the land can be used for the proposed "
            "purpose (Ch 4). Coastal management provisions apply only within mapped coastal "
            "areas — see the spatial overlays in this report. Flood planning controls sit in "
            "the LEP (cl 5.21), not this SEPP.",
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
    elif das is None:
        # DA search failed or was not run — say so; an empty-looking section
        # must never read as "no DAs" when the records were not checked.
        story.append(Paragraph(
            "Not assessed — DA records could not be retrieved at report generation. "
            "Check the NSW Planning Portal DA tracker for applications near this property.",
            ss["note"]
        ))
    else:
        story.append(Paragraph(
            "No development applications lodged within 200m in the past 12 months "
            "(NSW ePlanning DA records at report date).",
            ss["ok"]
        ))

    # ------------------------------------------------------------------
    # SECTION 10 — Development Contributions Plans (s7.11 / s7.12)
    # ------------------------------------------------------------------
    h2("10. Development Contributions Plans (s7.11 / s7.12)")

    _contrib_lines = build_contributions_lines(contributions)
    if _contrib_lines["state"] == "found":
        # intro when plans were returned; the queried-empty plans sentence
        # when the portal returned only the HPC block (status_line).
        if _contrib_lines["intro"]:
            story.append(Paragraph(_contrib_lines["intro"], ss["body"]))
        elif _contrib_lines["status_line"]:
            story.append(Paragraph(_contrib_lines["status_line"], ss["body"]))
        story.append(Spacer(1, 1 * mm))
        for pl in _contrib_lines["plan_lines"]:
            _name = _xml_escape(pl["name"])
            if pl.get("url"):
                _href = _xml_escape(str(pl["url"]).replace(" ", "%20"))
                story.append(Paragraph(
                    f"• <b>{_name}</b> — <link href=\"{_href}\" color=\"#1E5FAD\">plan document</link>",
                    ss["note"],
                ))
            else:
                story.append(Paragraph(f"• <b>{_name}</b>", ss["note"]))
        if _contrib_lines["hpc_line"]:
            story.append(Spacer(1, 1 * mm))
            _hpc_text = _xml_escape(_contrib_lines["hpc_line"])
            if _contrib_lines.get("hpc_url"):
                _hpc_href = _xml_escape(str(_contrib_lines["hpc_url"]).replace(" ", "%20"))
                _hpc_text += f" <link href=\"{_hpc_href}\" color=\"#1E5FAD\">Ministerial Order</link>"
            story.append(Paragraph(_hpc_text, ss["body"]))
    elif _contrib_lines["state"] == "empty":
        story.append(Paragraph(_contrib_lines["status_line"], ss["body"]))
    else:
        story.append(Paragraph(_contrib_lines["status_line"], ss["note"]))

    # ------------------------------------------------------------------
    # SECTION 11 — Corridors, Reservations and Infrastructure Interests
    # ------------------------------------------------------------------
    h2("11. Corridors, Reservations and Infrastructure Interests")

    for _txt in _corridor_lines["alert_rows"]:
        story.append(Paragraph(_xml_escape(_txt), ss["alert"]))
        story.append(Spacer(1, 1 * mm))
    for _txt in _corridor_lines["note_rows"]:
        story.append(Paragraph(_xml_escape(_txt), ss["body"]))
        story.append(Spacer(1, 1 * mm))
    if _corridor_lines["clean_line"]:
        _clean_style = "ok" if _corridor_lines["clean_line"] == _CORRIDORS_ALL_CLEAR else "body"
        story.append(Paragraph(_xml_escape(_corridor_lines["clean_line"]), ss[_clean_style]))
        story.append(Spacer(1, 1 * mm))
    for _txt in _corridor_lines["not_assessed_rows"]:
        story.append(Paragraph(_xml_escape(_txt), ss["note"]))
        story.append(Spacer(1, 1 * mm))
    if _corridor_lines["basis_note"]:
        story.append(Paragraph(_xml_escape(_corridor_lines["basis_note"]), ss["caveat"]))
        story.append(Spacer(1, 1 * mm))
    story.append(Paragraph(_xml_escape(_corridor_lines["source_line"]), ss["caveat"]))

    # ------------------------------------------------------------------
    # SECTION 12 — Transport Oriented Development (TOD) Catchment
    # Floor-only disclosure: catchment + instrument + as-of-right baseline;
    # the uplift ceiling is deliberately NOT quantified. Renders only for a
    # non-strata lot inside a mapped TOD catchment.
    # ------------------------------------------------------------------
    _lot_area_source = "NSW Valuer General" if valuation.get("lot_area_m2") else None
    _tod_lines = build_tod_uplift_lines(
        tod, capacity, bool((strata_info or {}).get("is_strata")),
        lot_area_source=_lot_area_source,
    )
    # Running section counter — TOD is conditional, so tail sections number
    # dynamically rather than with brittle hard-coded integers.
    _sec_no = 12
    if _tod_lines["render"]:
        h2(f"{_sec_no}. Transport Oriented Development (TOD) Catchment")
        _sec_no += 1
        story.append(Paragraph(_xml_escape(_tod_lines["disclosure"]), ss["warn"]))
        story.append(Spacer(1, 1 * mm))
        if _tod_lines["baseline"]:
            style = ss["note"] if _tod_lines["not_assessed"] else ss["body"]
            story.append(Paragraph(_xml_escape(_tod_lines["baseline"]), style))
            story.append(Spacer(1, 1 * mm))
        # held_line/scope are None in the failed-check variant (fix 4) —
        # nothing about held-back uplift applies to an unknown catchment.
        if _tod_lines["held_line"]:
            story.append(Paragraph(_xml_escape(_tod_lines["held_line"]), ss["body"]))
        if _tod_lines["ledger"]:
            story.append(Spacer(1, 1 * mm))
            story.append(Paragraph("<b>Inputs used for this baseline:</b>", ss["note"]))
            for _row in _tod_lines["ledger"]:
                story.append(Paragraph(f"• {_xml_escape(_row)}", ss["note"]))
        if _tod_lines["scope"]:
            story.append(Spacer(1, 1 * mm))
            story.append(Paragraph(_xml_escape(_tod_lines["scope"]), ss["caveat"]))

    # ------------------------------------------------------------------
    # SECTION — Structures & records reconciliation (Stage 1, records-only).
    # NEVER states a structure is unauthorised — factual records + hedged
    # question only (see build_structures_records_lines' liability rule).
    # ------------------------------------------------------------------
    _struct_lines = build_structures_records_lines(
        structures_records, detections=None, records_status=structures_records_status,
    )
    h2(f"{_sec_no}. Structures & Records")
    _sec_no += 1
    story.append(Paragraph(_xml_escape(_struct_lines["intro"]), ss["body"]))
    story.append(Spacer(1, 1 * mm))
    if _struct_lines["not_assessed"]:
        story.append(Paragraph(_xml_escape(_struct_lines["status_line"]), ss["note"]))
    else:
        if _struct_lines["record_lines"]:
            story.append(Paragraph(
                "<b>Applications matched to this address</b> "
                "(NSW Planning Portal, records available to us begin around 2019):",
                ss["body"]))
            for _row in _struct_lines["record_lines"]:
                story.append(Paragraph(f"• {_xml_escape(_row)}", ss["note"]))
            story.append(Paragraph(_xml_escape(_STRUCT_MATCH_CAVEAT), ss["caveat"]))
        elif _struct_lines["status_line"]:
            story.append(Paragraph(_xml_escape(_struct_lines["status_line"]), ss["body"]))
        for _gap in _struct_lines["gap_lines"]:
            story.append(Spacer(1, 1 * mm))
            story.append(Paragraph(_xml_escape(_gap), ss["warn"]))
        if _struct_lines["detection_note"]:
            story.append(Spacer(1, 1 * mm))
            story.append(Paragraph(_xml_escape(_struct_lines["detection_note"]), ss["caveat"]))

    # ------------------------------------------------------------------
    # SECTION — Climate & Hazard Exposure (modelled projections)
    # Forward-looking NARCliM 2.0 layer, factual metrics only: NO composite
    # score, NO band/verdict, NO insurability/safety/value claim (legal
    # assessment + #699). Renders the fetcher's present state OR an honest
    # not-available state; it is disclosure, so it does NOT flip the cover
    # CONSTRAINTS tile. Feature-flagged so a legal hold can disable it live.
    # ------------------------------------------------------------------
    if os.environ.get("CONVEYANCING_CLIMATE_ENABLED", "true").lower() in ("1", "true", "yes"):
        _climate_lines = build_climate_lines(
            climate, report_date=date.today().strftime("%d %B %Y")
        )
        if _climate_lines["render"]:
            h2(f"{_sec_no}. Climate & Hazard Exposure — Modelled Projections")
            _sec_no += 1
            if _climate_lines["state"] == "present":
                story.append(Paragraph(_xml_escape(_climate_lines["framing"]), ss["body"]))
                story.append(Spacer(1, 1 * mm))
                for _row in _climate_lines["rows"]:
                    story.append(Paragraph(f"• {_xml_escape(_row)}", ss["note"]))
                if _climate_lines["grid_note"]:
                    story.append(Spacer(1, 1 * mm))
                    story.append(Paragraph(_xml_escape(_climate_lines["grid_note"]), ss["caveat"]))
                story.append(Spacer(1, 1 * mm))
                story.append(Paragraph(_xml_escape(_climate_lines["source_line"]), ss["caveat"]))
            else:
                story.append(Paragraph(_xml_escape(_climate_lines["status_line"]), ss["note"]))

    # ------------------------------------------------------------------
    # SECTION — Estuarine Tidal Inundation (mapped extent, modelled scenario)
    # NSW Estuarine Inundation 2025 layer, factual mapped-extent statements
    # only: NO verdict, NO "at risk", NO safety/value/insurance claim (#699
    # discipline, terminology rule: "estuarine", never "coastal" as a coverage
    # word). Disclosure layer — it does NOT flip the cover CONSTRAINTS tile.
    # Feature-flagged so a legal hold can disable it live.
    # ------------------------------------------------------------------
    if os.environ.get("CONVEYANCING_COASTAL_ENABLED", "true").lower() in ("1", "true", "yes"):
        _coastal_lines = build_coastal_inundation_lines(
            coastal, report_date=date.today().strftime("%d %B %Y")
        )
        if _coastal_lines["render"]:
            h2(f"{_sec_no}. Estuarine Tidal Inundation — Mapped Extent")
            _sec_no += 1
            if _coastal_lines["state"] == "intersects":
                story.append(Paragraph(_xml_escape(_coastal_lines["framing"]), ss["body"]))
                story.append(Spacer(1, 1 * mm))
                for _row in _coastal_lines["rows"]:
                    story.append(Paragraph(f"• {_xml_escape(_row)}", ss["note"]))
            else:
                story.append(Paragraph(_xml_escape(_coastal_lines["status_line"]), ss["note"]))
            if _coastal_lines["basis_note"]:
                story.append(Spacer(1, 1 * mm))
                story.append(Paragraph(_xml_escape(_coastal_lines["basis_note"]), ss["caveat"]))
            if _coastal_lines["scope_line"]:
                story.append(Spacer(1, 1 * mm))
                story.append(Paragraph(_xml_escape(_coastal_lines["scope_line"]), ss["caveat"]))
            if _coastal_lines["source_line"]:
                story.append(Spacer(1, 1 * mm))
                story.append(Paragraph(_xml_escape(_coastal_lines["source_line"]), ss["caveat"]))

    # ------------------------------------------------------------------
    # SECTION (final) — Disclosure Notes
    # ------------------------------------------------------------------
    h2(f"{_sec_no}. Disclosure Notes")

    notes = [
        ("s10.7 Planning Certificate",
         "This report is <b>NOT a substitute</b> for a <b>Section 10.7 Planning Certificate</b> issued under the "
         "Environmental Planning and Assessment Act 1979. A s10.7(5) certificate from council is the "
         "<b>authoritative statutory disclosure document</b> for conveyancing. This report <b>supplements — "
         "it does not replace</b> — that certificate."),
        ("Environmental and spatial overlays",
         # s10.7(2) claim (D4): bushfire and flood are prescribed certificate
         # matters (EP&A Reg 2021 Sch 2) — only the genuinely absent layers are
         # named below.
         "<b>Biodiversity, riparian, wetlands, landslide, flood, aircraft noise "
         "(ANEF), TOD precinct status,</b> and Additional Permitted Uses data are sourced from PostGIS spatial "
         "overlays ingested from NSW Government ArcGIS services (128 NSW councils). <b>Bushfire prone land "
         "(BFPL)</b> is queried live from the NSW RFS BFPL service at report generation. "
         "<b>Biodiversity Values (BDAR trigger), ANEF contours, TOD precinct status and APU spatial footprints "
         "are not itemised in a standard s10.7(2) certificate or title search.</b> Bushfire-prone status and "
         "flood-related development controls are prescribed s10.7(2) certificate matters — the certificate "
         "states whether they apply; this report adds the mapped category and extent detail. "
         "Ingested data reflects the last ingestion date — accuracy is subject to NSW Government mapping precision. "
         "Verify with council for site-specific confirmation."),
        ("Title classification",
         "<b>Strata and community title</b> identification sourced from NSW Planning Portal cadastral data. "
         "<b>Company title</b> properties return as Torrens in the land register and <b>may not be automatically "
         "identified</b> — confirm via title search for older inner Sydney apartment buildings."),
        ("DCP provisions",
         "DCP setback controls are shown where extracted for the property's LGA — Section 4 names "
         "the applicable DCP when populated. Where Section 4 is not populated for this property, "
         "obtain DCP controls directly from council or via a town planning consultant."),
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
         "(Height of Buildings, HOB)</b> from the applicable Local Environmental Plan where one is mapped "
         "for the lot. HOB is the LEP control that sets the tallest structure a neighbour could legally "
         "build — <b>it is not the height of any existing building.</b> <b>Where no LEP height limit is "
         "mapped for the lot, the model uses a standard two-storey (9 m) assumed envelope instead — the "
         "Risk Summary row is labelled accordingly, and a taller merit-assessed build is possible.</b> "
         "The model tests whether a worst-case neighbour build at the modelled height would shadow this "
         "property on the <b>NSW Apartment Design Guide (ADG)</b> test dates "
         "(21 June winter solstice, 9 am / 12 pm / 3 pm). ADG compliance requires <b>at least 2 hours "
         "of direct sunlight between 9 am and 3 pm on 21 June</b> for living areas and private open space. "
         "This is a <b>conservative envelope model</b> — not a site-specific shadow study. A formal shadow "
         "impact assessment by a qualified architect is required for DA submission."),
        ("Infrastructure contributions (S7.11 / S7.12)",
         "This report <b>does not include infrastructure contribution liability estimates.</b> "
         "Development applications for new dwellings or subdivision require a <b>Section 7.11 or 7.12 "
         "Contributions Plan levy</b> — typically <b>$10,000–$50,000+ per dwelling</b> in Greater Sydney. "
         "Section 10 names the contributions plans the NSW Planning Portal returns for this location; "
         "the charge rates are set out in the council's contributions plan documents and must be "
         "checked directly before any development feasibility assessment is relied upon."),
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
    # DB-loaded regulatory configs (SEPP standards + land tax thresholds) —
    # same loader the API path uses; a None tax_config renders "Not assessed".
    _sepp_standards, _tax_config = load_regulatory_configs(os.getenv("DATABASE_URL"))
    if _tax_config is None:
        print("  [warn] land tax config unavailable — land tax section renders 'Not assessed'")
    if _sepp_standards is None:
        print("  [warn] SEPP Housing standards unavailable — secondary dwelling renders 'Not assessed'")
    # CDC screen (#820): verdict from the backend engine + verified Codes SEPP
    # standards; None renders "Not assessed" — never a zone-list guess.
    from services.cdc_screen import run_cdc_screen_for_report
    _cdc_result = run_cdc_screen_for_report(
        os.getenv("DATABASE_URL"), controls.get("zone"), valuation.get("lot_area_m2"),
        controls.get("heritage_items"), controls.get("heritage_hca"),
        unique_overlays, covered_layers,
    )
    if _cdc_result is None:
        print("  [warn] CDC screen unavailable — CDC row renders 'Not assessed'")
    feasibility = calc_feasibility(
        controls, valuation, unique_overlays, is_strata=strata,
        sepp_standards=_sepp_standards, tax_config=_tax_config,
        cdc_result=_cdc_result,
    )

    raw_council = args.council or _council_from_zone_epi(controls.get("zone_epi", ""))
    council_name = _normalise_council(raw_council) if args.council else raw_council
    if council_name:
        print(f"\nFetching nearby DAs (council: {council_name}) ...")
        try:
            das = get_nearby_das(lat, lng, council_name=council_name)
        except Exception as e:
            print(f"  [warn] DA search failed: {e}")
            das = None  # failed fetch renders as "Not assessed", never "No DAs"
    else:
        print("\nSkipping DA search — council could not be derived from LEP")
        das = None
    print(f"  {len(das)} DAs within 200m" if das is not None else "  DA search not run")

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
            _adg_val = shadow_result.get("adg_compliant")
            adg = ("ADG not assessed" if _adg_val is None
                   else "ADG concern" if _adg_val is False
                   else "ADG solar access test met")
            print(f"  {adg}  height: {shadow_result.get('height_m')} m ({shadow_result.get('height_source')})")
        else:
            print("  Shadow model unavailable — section omitted from PDF")

    print("\nQuerying NSW RFS BFPL (live) ...")
    bushfire_live = get_bushfire_live(lat, lng)
    if bushfire_live is None or bushfire_live.get("is_bushfire_prone") is None:
        print("  RFS BFPL unavailable — bushfire row will show 'Not assessed'")
    else:
        print(f"  Bushfire prone: {bushfire_live.get('is_bushfire_prone')} "
              f"{bushfire_live.get('designation_category') or ''}")

    print("\nResolving ANEF contour value ...")
    anef_live = get_anef_live(lat, lng)
    if anef_live.get("status") == "found":
        print(f"  ANEF value: {_anef_value_display(anef_live)} ({_anef_source_label(anef_live)})")
    elif anef_live.get("status") == "failed":
        print("  ANEF value lookup failed — row will state 'not assessed' if an ANEF overlay applies")
    else:
        print("  No ANEF contour value at this point")

    print("\nFetching development contributions plans (/cp) ...")
    contributions = get_contributions_live(prop_id)
    if contributions.get("status") == "found":
        print(f"  {len(contributions.get('plans') or [])} plan(s)"
              f"{' + HPC' if contributions.get('hpc') else ''}")
    elif contributions.get("status") == "empty":
        print("  No contributions plans returned")
    else:
        print("  Contributions lookup failed — section will state 'Not assessed'")

    print("\nChecking corridors / land-reservation-acquisition / portal warnings ...")
    corridors = get_corridors_live(lat, lng, lot_wkt=lot_wkt, prop_id=prop_id)
    if corridors:
        print(f"  basis: {corridors.get('query_basis')}")
        for _k in ("lra", "rail_corridors", "warnings"):
            _sub = corridors.get(_k) or {}
            print(f"  {_k}: {_sub.get('status')} ({len(_sub.get('items') or [])})")
    else:
        print("  Corridors check unavailable — section will state 'Not assessed'")

    print("\nChecking TOD catchment + floor-only capacity baseline ...")
    _lot_dims_for_tod = None
    tod, capacity = get_tod_uplift_live(
        lat, lng, controls, valuation, lot_dimensions=_lot_dims_for_tod,
        dcp_controls=None,
    )
    if tod and tod.get("in_tod"):
        _strata_here = bool((strata_info or {}).get("is_strata"))
        print(f"  in TOD catchment ({tod.get('epi_name')}); strata={_strata_here}; "
              f"baseline={'computed' if capacity is not None else 'not assessed'}")
    elif tod is None:
        print("  TOD catchment lookup unavailable — section omitted")
    else:
        print("  Not in a TOD catchment — section omitted")

    print("\nFetching subject-lot application records (structures & records, Stage 1) ...")
    structures_records, structures_records_status = get_structures_records_live(
        council_name, args.address,
    )
    if structures_records_status == "ok":
        print(f"  {len(structures_records)} DA/CDC record(s) on file for this lot")
    else:
        print("  application-records lookup unavailable — section will state 'Not assessed'")

    print("\nQuerying NARCliM 2.0 climate projections ...")
    try:
        from climate_risk_raster import query_narclim_state
    except ImportError:
        from services.climate_risk_raster import query_narclim_state
    climate = query_narclim_state(lat, lng)
    print(f"  climate projection state: {climate.get('state')}")

    print("\nChecking mine subsidence district (live) ...")
    mine_subsidence = get_mine_subsidence_live(lat, lng)
    print(f"  mine subsidence: {mine_subsidence.get('status')}")

    print("\nChecking EPA contaminated land register within 500 m (live) ...")
    contaminated = get_contaminated_live(lat, lng)
    if contaminated.get("status") == "found":
        _cl_data = contaminated.get("data") or {}
        print(f"  {_cl_data.get('site_count')} notified site(s) within 500 m")
    else:
        print(f"  contaminated land: {contaminated.get('status')}")

    print("\nChecking Sydney Water Growth Servicing Plan (live) ...")
    servicing = get_servicing_live(lat, lng)
    print(f"  servicing: {servicing.get('status')}")

    print("\nChecking estuarine tidal inundation mapped extent (PostGIS) ...")
    coastal = get_coastal_inundation_live(lat, lng, lot_wkt=lot_wkt)
    if coastal.get("status") == "intersects":
        _yrs = coastal.get("years") or {}
        print(f"  intersects ({coastal.get('query_basis')}): "
              + "; ".join(f"{y}: {t.get('days_per_year')} d/yr" for y, t in sorted(_yrs.items())))
    else:
        print(f"  estuarine inundation: {coastal.get('status')} "
              f"({coastal.get('query_basis') or 'query not run'})")

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
            bushfire_live=bushfire_live,
            anef_live=anef_live,
            contributions=contributions,
            corridors=corridors,
            tod=tod,
            capacity=capacity,
            structures_records=structures_records,
            structures_records_status=structures_records_status,
            climate=climate,
            mine_subsidence=mine_subsidence,
            contaminated=contaminated,
            servicing=servicing,
            coastal=coastal,
        )


if __name__ == "__main__":
    main()
