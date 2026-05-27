"""
DB fetch functions for the conveyancing planning disclosure report.

These replace hardcoded dicts (DCP_SETBACKS, KEY_SITES_PLAIN, SEPP_PLAIN) with
live DB queries. All functions return shape-compatible replacements so render
code in generate_conveyancing_report.py requires zero structural changes.

Callers pre-fetch before calling generate_pdf() — no DB connection inside the
PDF renderer.

Heritage value taxonomy (spatial_overlays.value for layer_type='heritage'):
  'Conservation Area - General'        → HCA
  'Conservation Area - Landscape'      → HCA
  'Conservation Area - Archaeological' → HCA
  'Conservation Area - Aboriginal'     → HCA
  'Item - General'                     → individual listed item
  'Item - Landscape'                   → individual listed item
  'Item - Archaeological'              → individual listed item
  'Item - Aboriginal'                  → individual listed item
"""
from __future__ import annotations

import json
import logging
import math
import re
from datetime import date, timedelta
from typing import Optional

import psycopg2

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Clause normalisation
# ---------------------------------------------------------------------------

def normalise_clauses(raw: str) -> list[str]:
    """Parse portal Legislative Clause field into individual clause numbers.

    Handles:
      "Clause 4.3C"           → ["4.3C"]
      "Clauses 4.3C, 4.4"     → ["4.3C", "4.4"]
      "Clauses 4.3C and 4.4"  → ["4.3C", "4.4"]
      "Clause 6.14, 6.15"     → ["6.14", "6.15"]
      "cl. 4.3C"              → ["4.3C"]
    """
    if not raw:
        return []
    # Strip "Clause", "Clauses", "cl." prefix variants
    raw = re.sub(r"(?i)\bclauses?\b\.?\s*|\bcl\.\s*", "", raw)
    parts = re.split(r"[,;]|\band\b", raw, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# LEP key sites clause lookup
# ---------------------------------------------------------------------------

def fetch_lep_clauses(
    conn,
    key_sites_clause: Optional[str],
    epi_name: Optional[str],
) -> list[dict]:
    """Return lep_clauses rows for the given portal key sites clause + EPI name.

    Returns list of dicts: {number, heading, summary, source}
      summary=None → no DB row for this clause; caller shows raw ref + legislation link.

    Never raises — returns empty list on any failure.
    """
    if not key_sites_clause or not epi_name:
        return []
    clause_numbers = normalise_clauses(key_sites_clause)
    if not clause_numbers:
        return []

    results = []
    try:
        cur = conn.cursor()
        for cn in clause_numbers:
            cur.execute(
                """
                SELECT clause_number, clause_heading, plain_summary, source_ref
                FROM lep_clauses
                WHERE epi_name ILIKE %s AND clause_number = %s
                """,
                (epi_name, cn),
            )
            row = cur.fetchone()
            results.append({
                "number":  cn,
                "heading": row[1] if row else None,
                "summary": row[2] if row else None,
                "source":  row[3] if row else None,
            })
        cur.close()
    except Exception as e:
        logger.warning("fetch_lep_clauses: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
    return results


# ---------------------------------------------------------------------------
# DCP setback lookup — queries dcp_setback_controls table
# ---------------------------------------------------------------------------

# Human-readable labels for dcp_setback_controls.control_type values
_CONTROL_TYPE_LABELS: dict[str, str] = {
    "front_setback": "Front setback",
    "side_setback":  "Side setback",
    "rear_setback":  "Rear setback",
    "max_height":    "Maximum building height",
    "wall_height":   "Wall height",
}

# Canonical DCP name for each lga slug
_LGA_SLUG_TO_DCP_NAME: dict[str, str] = {
    "marrickville":         "Inner West DCP 2022 (Marrickville precinct)",
    "leichhardt":           "Inner West DCP 2022 (Leichhardt precinct)",
    "ashfield":             "Inner West DCP 2022 (Ashfield precinct)",
    "waverley":             "Waverley DCP 2022",
    "woollahra":            "Woollahra DCP",
    "ku_ring_gai":          "Ku-ring-gai DCP",
    "canterbury_bankstown": "Canterbury-Bankstown DCP 2023",
    "blacktown":            "Blacktown DCP 2015",
    "campbelltown":         "Campbelltown (Sustainable City) DCP 2015",
    "liverpool":            "Liverpool DCP 2008",
    "hornsby":              "Hornsby DCP 2024",
    "northern_beaches":     "Warringah (Northern Beaches) DCP 2011",
    "penrith":              "Penrith DCP 2014",
    "cumberland":           "Cumberland DCP 2021",
}


def fetch_dcp_setbacks(
    conn,
    lga_slug: Optional[str],
    zone_code: Optional[str] = None,
) -> Optional[dict]:
    """Return DCP setback data from dcp_setback_controls.

    Shape returned:
      {
        dcp_name, section, clause_ref,
        zones_applicable, dev_type_scope, caveat,
        setbacks:    [{type, control_type, requirement, clause, notes}],  # DH rows
        sd_setbacks: [{type, control_type, requirement, clause, notes}],  # SD rows (may be [])
        is_da_path:  True,
        dcp_url:     str | None,
      }

    'zones_applicable' is always [] — controls apply to all residential zones unless
    condition text restricts otherwise.

    Returns None if no current rows for this lga_slug.
    Never raises.
    """
    if not lga_slug:
        return None

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT dev_type, control_type, value_min, value_max, unit,
                   condition, source_text, section_ref, applicability
            FROM dcp_setback_controls
            WHERE lga = %s AND is_current = TRUE
            ORDER BY
                CASE dev_type WHEN 'dwelling_house' THEN 0 ELSE 1 END,
                CASE control_type
                    WHEN 'front_setback' THEN 0
                    WHEN 'side_setback'  THEN 1
                    WHEN 'rear_setback'  THEN 2
                    WHEN 'max_height'    THEN 3
                    ELSE 4
                END,
                value_min NULLS LAST
            """,
            (lga_slug,),
        )
        rows = cur.fetchall()

        # Best available DCP URL from chapter registry
        cur.execute(
            """
            SELECT COALESCE(council_url, council_page_url)
            FROM dcp_chapter_registry
            WHERE council = %s AND is_active = TRUE
            ORDER BY updated_at DESC NULLS LAST
            LIMIT 1
            """,
            (lga_slug,),
        )
        reg = cur.fetchone()
        cur.close()
    except Exception as e:
        logger.warning("fetch_dcp_setbacks: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
        return None

    if not rows:
        return None

    dcp_url = reg[0] if reg else None
    dcp_name = _LGA_SLUG_TO_DCP_NAME.get(
        lga_slug, lga_slug.replace("_", " ").title() + " DCP"
    )

    dh_setbacks: list[dict] = []
    sd_setbacks: list[dict] = []

    # Zone advisory: strip prefix digit from zone code (e.g. "R2" from "R2 Low Density")
    zone_prefix = (zone_code.strip().split()[0].upper() if zone_code and zone_code.strip() else "")

    for dev_type, ctrl_type, vmin, vmax, unit, condition, source_text, section_ref, applicability in rows:
        # Skip zone-specific controls that explicitly reference a DIFFERENT zone.
        # Conservative: only skip when condition names zones AND our zone isn't among them.
        if zone_prefix and applicability == "zone_specific" and condition:
            cond_upper = condition.upper()
            # Check if condition mentions specific zone codes (R1, R2, R3, etc.)
            if any(z in cond_upper for z in ("R1", "R2", "R3", "R4", "R5", "E1", "B1", "B2", "MU1", "C2")) \
               and zone_prefix not in cond_upper:
                continue
        base_label = _CONTROL_TYPE_LABELS.get(
            ctrl_type, ctrl_type.replace("_", " ").title()
        )

        if vmin is not None or vmax is not None:
            control_kind = "prescribed"
            parts: list[str] = []
            if vmin is not None:
                parts.append(f"{vmin:g} m minimum")
            if vmax is not None and vmax != vmin:
                parts.append(f"{vmax:g} m maximum")
            requirement = "; ".join(parts) if parts else f"{vmin or vmax:g} m"
        else:
            control_kind = "site_derived"
            requirement = source_text or "Merit-based assessment — refer to DCP"

        entry = {
            "type":         base_label,
            "control_type": control_kind,
            "requirement":  requirement,
            "clause":       section_ref or "",
            "notes":        condition or "",
        }

        is_sd = (
            applicability == "secondary_dwelling_specific"
            or dev_type == "secondary_dwelling"
        )
        if is_sd:
            sd_setbacks.append(entry)
        else:
            dh_setbacks.append(entry)

    first_ref = rows[0][7] or ""

    # Canterbury-Bankstown: two former regimes stored together — flag for render
    caveat: Optional[str] = None
    if lga_slug == "canterbury_bankstown":
        caveat = (
            "Canterbury-Bankstown covers two former council areas with different setback "
            "requirements. Check the Notes column: 'former Bankstown' = Chapter 5.1; "
            "'former Canterbury' = Chapter 5.2. Confirm the applicable regime from your "
            "Section 10.7 certificate or the Canterbury-Bankstown planning maps."
        )

    return {
        "dcp_name":         dcp_name,
        "section":          "Residential Development Controls",
        "clause_ref":       first_ref,
        "zones_applicable": [],
        "zone_filter_applied": zone_prefix or None,
        "dev_type_scope":   "Dwelling house — DA pathway",
        "caveat":           caveat,
        "setbacks":         dh_setbacks,
        "sd_setbacks":      sd_setbacks,
        "is_da_path":       True,
        "dcp_url":          dcp_url,
    }


# ---------------------------------------------------------------------------
# SEPP overlay interpretation — replaces SEPP_PLAIN dict
# ---------------------------------------------------------------------------

# Types that have dedicated report sections — suppress from the SEPP table
# to avoid duplicating information already shown elsewhere.
_SUPPRESS_TYPES = frozenset({
    "transport oriented development",
    "tod",
    "bushfire",
    "aircraft noise",
    "anef",
    "bushfire prone land",
})


def interpret_sepp(
    epi_name: str,
    type_: str,
    label: str,
    legislation_url: str,
) -> Optional[str]:
    """Return display text for a SEPP overlay hit, or None to suppress.

    None   → this overlay type has a dedicated report section; suppress from SEPP table.
    str    → display this text in the Practical Implication column.

    Primary source: portal Type + Label fields (already specific).
    No hardcoded descriptions. No fallback keyword dict.
    """
    if type_ and any(t in type_.lower() for t in _SUPPRESS_TYPES):
        return None

    parts: list[str] = []
    if type_:
        parts.append(type_)
    if label and (not type_ or label.lower() != type_.lower()):
        parts.append(label)

    detail = " — ".join(parts) if parts else (epi_name or "SEPP overlay")
    suffix = f" See {legislation_url}." if legislation_url else ""
    return f"{detail}.{suffix}"


# ---------------------------------------------------------------------------
# PostGIS heritage lookup — classifies portal items as HCA vs individual
# ---------------------------------------------------------------------------

_HCA_VALUES = frozenset({
    "conservation area - general",
    "conservation area - landscape",
    "conservation area - archaeological",
    "conservation area - aboriginal",
})
_ITEM_VALUES = frozenset({
    "item - general",
    "item - landscape",
    "item - archaeological",
    "item - aboriginal",
    "aboriginal place of heritage significance",
    "aboriginal object",
})


def fetch_heritage_postgis(
    conn,
    lat: float,
    lng: float,
    lot_wkt: Optional[str] = None,
) -> dict:
    """Query PostGIS for heritage overlays at this point/lot.

    Uses ST_Intersects against the lot polygon when lot_wkt is supplied
    (catches overlays covering only part of the lot). Falls back to
    ST_Contains on the centroid point.

    Returns:
      {
        "hca":         list[str],  # display strings for HCA hits
        "items":       list[str],  # display strings for individual item hits
        "has_heritage": bool,
        "raw":         list[dict], # [{value, instrument_key}] all hits
      }

    Never raises — returns empty result on any failure.
    """
    empty: dict = {"hca": [], "items": [], "has_heritage": False, "raw": []}
    try:
        cur = conn.cursor()
        if lot_wkt:
            cur.execute(
                """
                SELECT value, instrument_key
                FROM spatial_overlays
                WHERE layer_type = 'heritage'
                  AND ST_Intersects(geom, ST_SetSRID(ST_GeomFromText(%s), 4326))
                """,
                (lot_wkt,),
            )
        else:
            cur.execute(
                """
                SELECT value, instrument_key
                FROM spatial_overlays
                WHERE layer_type = 'heritage'
                  AND ST_Contains(geom, ST_SetSRID(ST_Point(%s, %s), 4326))
                """,
                (lng, lat),
            )
        rows = cur.fetchall()
        cur.close()
    except Exception as e:
        logger.warning("fetch_heritage_postgis: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
        return empty

    if not rows:
        return empty

    hca: list[str] = []
    items: list[str] = []
    raw: list[dict] = []

    for value, instrument_key in rows:
        raw.append({"value": value, "instrument_key": instrument_key})
        v_lower = (value or "").lower()
        inst = instrument_key or "refer to council heritage maps"
        if v_lower in _HCA_VALUES:
            hca.append(f"Heritage Conservation Area ({inst})")
        elif v_lower in _ITEM_VALUES:
            items.append(f"Heritage Item ({inst})")

    # Deduplicate (same HCA polygon may intersect lot multiple times)
    hca = list(dict.fromkeys(hca))
    items = list(dict.fromkeys(items))

    return {
        "hca": hca,
        "items": items,
        "has_heritage": bool(hca or items),
        "raw": raw,
    }


# ---------------------------------------------------------------------------
# SEPP Housing standards — queries housing_sepp_standards table
# ---------------------------------------------------------------------------

def fetch_sepp_housing_standards(
    conn,
    zone_code: Optional[str] = None,
    development_type: Optional[str] = None,
) -> list[dict]:
    """Return SEPP Housing standards from the DB, optionally filtered by zone and dev type.

    Returns list of dicts:
      {development_type, standard_type, numeric_value, unit,
       applicable_zones, source_clause, source_document, effective_date}

    zone_code: e.g. "R2" — filters to standards whose applicable_zones include this zone.
    development_type: e.g. "secondary_dwelling" — filters to a specific dev type.

    Never raises — returns empty list on any failure.
    """
    try:
        cur = conn.cursor()
        conditions = []
        params: list = []

        if development_type:
            conditions.append("development_type = %s")
            params.append(development_type)

        if zone_code:
            zone_prefix = zone_code.strip().split()[0].upper()
            conditions.append("%s = ANY(applicable_zones)")
            params.append(zone_prefix)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        cur.execute(
            f"""
            SELECT development_type, standard_type, numeric_value, unit,
                   applicable_zones, source_clause, source_document,
                   legislation_url, effective_date
            FROM housing_sepp_standards
            {where}
            ORDER BY development_type, standard_type
            """,
            params,
        )
        rows = cur.fetchall()
        cur.close()
    except Exception as e:
        logger.warning("fetch_sepp_housing_standards: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
        return []

    return [
        {
            "development_type": r[0],
            "standard_type": r[1],
            "numeric_value": float(r[2]),
            "unit": r[3],
            "applicable_zones": r[4] or [],
            "source_clause": r[5],
            "source_document": r[6],
            "legislation_url": r[7],
            "effective_date": str(r[8]) if r[8] else None,
        }
        for r in rows
    ]


def get_sepp_standard_value(
    conn,
    development_type: str,
    standard_type: str,
    zone_code: Optional[str] = None,
) -> Optional[float]:
    """Convenience: return a single numeric value for a specific standard.

    E.g. get_sepp_standard_value(conn, "secondary_dwelling", "min_lot_size", "R2")
    returns 450.0

    Returns None if not found. Never raises.
    """
    standards = fetch_sepp_housing_standards(conn, zone_code, development_type)
    for s in standards:
        if s["standard_type"] == standard_type:
            return s["numeric_value"]
    return None


# ---------------------------------------------------------------------------
# Tax thresholds — queries tax_thresholds table
# ---------------------------------------------------------------------------

def fetch_tax_thresholds(
    conn,
    tax_year: Optional[int] = None,
    jurisdiction: str = "NSW",
    tax_type: str = "land_tax",
) -> Optional[dict]:
    """Return tax thresholds for the given year (defaults to current year).

    Returns dict:
      {tax_year, threshold_dollars, rate, base_amount_dollars,
       premium_threshold_dollars, premium_rate, source_url}

    Returns None if no row found. Never raises.
    """
    if tax_year is None:
        tax_year = date.today().year

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT tax_year, threshold_dollars, rate, base_amount_dollars,
                   premium_threshold_dollars, premium_rate, source_url
            FROM tax_thresholds
            WHERE jurisdiction = %s AND tax_type = %s AND tax_year = %s
            """,
            (jurisdiction, tax_type, tax_year),
        )
        row = cur.fetchone()
        cur.close()
    except Exception as e:
        logger.warning("fetch_tax_thresholds: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
        return None

    if not row:
        return None

    return {
        "tax_year": row[0],
        "threshold_dollars": row[1],
        "rate": float(row[2]),
        "base_amount_dollars": row[3],
        "premium_threshold_dollars": row[4],
        "premium_rate": float(row[5]) if row[5] else None,
        "source_url": row[6],
    }


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance in metres between two lat/lng points."""
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def fetch_nearby_das(
    conn,
    lat: float,
    lng: float,
    council_name: Optional[str] = None,
    radius_m: int = 200,
    days: int = 365,
    limit: int = 10,
) -> list[dict]:
    """Query development_applications table for nearby DAs.

    Uses a lat/lon bounding box for indexed pre-filter, then Haversine for
    precise distance. Returns shape-compatible output with get_nearby_das().

    Never raises — returns empty list on any failure.
    """
    since = date.today() - timedelta(days=days)
    delta = radius_m / 111_000 * 1.2  # degree delta with safety margin

    try:
        cur = conn.cursor()
        sql = """
            SELECT planning_portal_id, address, suburb, application_status,
                   latitude, longitude, lodgement_date, determination_date,
                   development_type, cost_of_development
            FROM development_applications
            WHERE latitude BETWEEN %s AND %s
              AND longitude BETWEEN %s AND %s
              AND (lodgement_date >= %s OR determination_date >= %s)
        """
        params: list = [
            lat - delta, lat + delta,
            lng - delta, lng + delta,
            since, since,
        ]
        if council_name:
            sql += " AND council_name = %s"
            params.append(council_name)

        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
    except Exception as e:
        logger.warning("fetch_nearby_das: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
        return []

    nearby = []
    for row in rows:
        pid, addr, suburb, status, da_lat, da_lng, lodged, det, dev_type, cost = row
        if da_lat is None or da_lng is None:
            continue
        dist = _haversine_m(lat, lng, float(da_lat), float(da_lng))
        if dist <= radius_m:
            # Parse development_type — stored as JSONB array or string
            desc = ""
            if dev_type:
                if isinstance(dev_type, list):
                    desc = ", ".join(
                        ((dt.get("DevelopmentType") or "") if isinstance(dt, dict) else str(dt))
                        for dt in dev_type
                    )[:120]
                elif isinstance(dev_type, str):
                    try:
                        parsed = json.loads(dev_type)
                        if isinstance(parsed, list):
                            desc = ", ".join(
                                ((dt.get("DevelopmentType") or "") if isinstance(dt, dict) else str(dt))
                                for dt in parsed
                            )[:120]
                    except (json.JSONDecodeError, TypeError):
                        desc = dev_type[:120]

            nearby.append({
                "number": pid or "",
                "address": addr or "",
                "description": desc,
                "status": status or "",
                "lodged": str(lodged)[:10] if lodged else "",
                "distance_m": round(dist),
            })

    nearby.sort(key=lambda x: x["distance_m"])
    return nearby[:limit]


def check_regulatory_freshness(conn) -> list[str]:
    """Check that DB-sourced regulatory constants are present and current.

    Returns a list of warning strings. Empty list = all checks pass.
    Called by the regulatory-freshness monitor (run_monitors.py).
    """
    warnings = []
    if conn is None:
        return ["CRITICAL: no DB connection — all regulatory values will use hardcoded fallbacks"]

    # 1. Check housing_sepp_standards has secondary_dwelling rows
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT standard_type, numeric_value
            FROM housing_sepp_standards
            WHERE development_type = 'secondary_dwelling'
              AND standard_type IN ('min_lot_size', 'max_floor_area')
            """,
        )
        rows = {r[0]: float(r[1]) for r in cur.fetchall()}
        cur.close()
        if "min_lot_size" not in rows:
            warnings.append("SEPP: missing min_lot_size for secondary_dwelling — fallback 450m² in use")
        if "max_floor_area" not in rows:
            warnings.append("SEPP: missing max_floor_area for secondary_dwelling — fallback 60m² in use")
    except Exception as e:
        warnings.append(f"SEPP: query failed — {e}")
        try:
            conn.rollback()
        except Exception:
            pass

    # 2. Check tax_thresholds has a row for the current year
    current_year = date.today().year
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT tax_year FROM tax_thresholds
            WHERE jurisdiction = 'NSW' AND tax_type = 'land_tax'
            ORDER BY tax_year DESC LIMIT 1
            """,
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            warnings.append(f"TAX: no tax_thresholds rows at all — fallback 2025 values in use")
        elif row[0] < current_year:
            warnings.append(
                f"TAX: latest tax_thresholds year is {row[0]}, current year is {current_year} "
                f"— thresholds may be stale. Insert {current_year} row when Revenue NSW publishes new rates."
            )
    except Exception as e:
        warnings.append(f"TAX: query failed — {e}")
        try:
            conn.rollback()
        except Exception:
            pass

    return warnings
