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


# prior-art-checked: no existing as-at formatter or plan-date lookup exists
# (dcp_plan_as_at is new in migration 063; repo grep for as_at rendering found
# only the brief's DataField.as_at, which stamps the QUERY date, not the plan
# date). This is the single shared wording source so every surface renders the
# same basis-appropriate sentence.
_MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December"]


def _format_as_at_date(iso_date: str, precision: str) -> Optional[str]:
    """Render an ISO date at ONLY the precision the source stated.

    A month-precision date stored as the 1st must render "March 2026", never
    "1 March 2026" (precision-honesty rule).
    """
    if not iso_date:
        return None
    try:
        year_s, month_s, day_s = iso_date.split("-")
        y, m, d = int(year_s), int(month_s), int(day_s)  # qa-ignore: split parts are str, never None; bad numerics land in the except arm
        month = _MONTH_NAMES[m - 1]
    except (ValueError, IndexError, AttributeError):
        return None
    if precision == "day":
        return f"{d} {month} {y}"
    if precision == "month":
        return f"{month} {y}"
    if precision == "year":
        return str(y)
    return None


def format_as_at_line(as_at: Optional[dict]) -> Optional[str]:
    """The one wording source for DCP as-at lines (language-ladder compliant:
    'stated'/'observed', never 'verified'/'confirmed'/'current law')."""
    if not as_at or not as_at.get("date"):
        return None
    shown = _format_as_at_date(as_at["date"], as_at.get("precision") or "day")
    if not shown:
        return None
    basis = as_at.get("basis")
    kind = as_at.get("kind")
    if basis == "portal_plan_record":
        where = "date stated in the NSW Planning Portal plan record"
    elif basis == "stated_in_document":
        where = "date stated in the plan document"
    elif basis == "observed_current":
        return (f"Observed as the current published version on {shown}; "
                f"an in-force date is not available for this plan")
    else:
        return None
    if kind == "amended":
        return f"As amended {shown} ({where})"
    if kind == "adopted":
        return f"Adopted {shown} ({where})"
    return f"In force from {shown} ({where})"


def _plan_as_at(cur, lga_slug: str) -> Optional[dict]:
    """Plan-level as-at with basis, by the settled authority order:
    portal plan record > the document's own statement > registry observation.
    Returns None when nothing defensible exists (a claim rendered with no date
    is counted by scripts/check_dcp_as_at_coverage.py, never papered over).
    Raises on DB errors — the caller's except turns that into 'source
    unavailable' (no as-at), which is distinct from 'checked, none exists'.
    """
    cur.execute(
        """
        SELECT p.portal_date::text, p.portal_date_precision, p.portal_date_kind,
               p.stated_date::text, p.stated_date_precision, p.stated_date_kind,
               obs.observed::date::text
          FROM (SELECT MAX(url_last_checked) AS observed
                  FROM dcp_chapter_registry
                 WHERE council = %s AND is_active = TRUE) obs
          LEFT JOIN dcp_plan_as_at p ON p.lga = %s
        """,
        (lga_slug, lga_slug),
    )
    row = cur.fetchone()
    if not row or len(row) != 7:
        return None
    (portal_d, portal_p, portal_k, stated_d, stated_p, stated_k, observed) = row
    if portal_d:
        return {"date": portal_d, "precision": portal_p, "kind": portal_k,
                "basis": "portal_plan_record"}
    if stated_d:
        return {"date": stated_d, "precision": stated_p, "kind": stated_k,
                "basis": "stated_in_document"}
    if observed:
        return {"date": observed, "precision": "day", "kind": None,
                "basis": "observed_current"}
    return None


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
                   condition, source_text, section_ref, applicability,
                   needs_review
            FROM dcp_setback_controls
            WHERE lga = %s AND is_current = TRUE
              AND (needs_review IS NULL OR needs_review = FALSE)
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

        # Plan-level "as at" (campaign item 3). A failure here must not take
        # the controls down with it: the as-at is provenance FOR the controls,
        # so it degrades to None ("source unavailable" — no date line renders)
        # while the controls still serve.
        try:
            as_at = _plan_as_at(cur, lga_slug)
        except Exception as e:
            logger.warning("fetch_dcp_setbacks as-at lookup: %s", e)
            as_at = None
            try:
                conn.rollback()
            except Exception:
                pass
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

    for dev_type, ctrl_type, vmin, vmax, unit, condition, source_text, section_ref, applicability, needs_review in rows:
        # Fail-closed on currency (mirrors the web route /api/dcp/structured-controls):
        # a control flagged for human review after a DCP amendment must never render
        # as an authoritative number in the PDF. The SQL WHERE already excludes
        # needs_review rows; this per-row guard keeps the exclusion even if that SQL
        # filter is ever changed. Under-review controls are suppressed and treated as
        # "not available", consistent with how the report omits controls a council
        # has no data for.
        if needs_review:
            continue
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
            # The real development form — WITHOUT this, the capacity engine's
            # dev_type filter defaults every row to dwelling_house and pools
            # townhouse/flat setbacks into the dwelling envelope (Bowral brief
            # regression: front pool (4.5, 6.5, 8, 15) mixed two forms).
            "dev_type":     dev_type,
            "control_type": control_kind,
            "semantic_type": ctrl_type,
            "requirement":  requirement,
            "value_min":    float(vmin) if vmin is not None else None,
            "value_max":    float(vmax) if vmax is not None else None,
            "unit":         unit or "m",
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

    # Cite a clause that SURVIVED the filters above, never rows[0].
    #
    # Two `continue` guards drop rows before they reach the report: a control
    # flagged needs_review after a DCP amendment, and a zone_specific control whose
    # condition names zones that exclude this property's zone. rows[0] is the raw
    # query's first row, so it can be one of those — meaning `clause_ref`, the
    # citation a conveyancer reads, could point at a control this very function
    # decided NOT to show, including one for a different zone entirely.
    #
    # Citing the source is the product's core claim, so a citation that does not
    # match the rendered controls is worse than no citation. If everything was
    # filtered out, return "" and let the caller render nothing rather than
    # inventing a reference.
    # Both lists are searched, not `dh_setbacks or sd_setbacks`: a dwelling-house
    # control can be rendered with a blank section_ref while a secondary-dwelling
    # control alongside it carries a real one. The `or` form would stop at the
    # non-empty dh list and silently emit no citation even though a shown control
    # had one.
    first_ref = next(
        (e["clause"] for e in [*dh_setbacks, *sd_setbacks] if e.get("clause")),
        "",
    )

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
        # Three states: dict = date with basis; None = no defensible date
        # (either none exists or the lookup failed — the check script counts
        # both). The line is preformatted HERE so every surface words it
        # identically.
        "as_at":            as_at,
        "as_at_line":       format_as_at_line(as_at),
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
    class_: str = "",
    map_title: str = "",
) -> Optional[str]:
    """Return display text for a SEPP overlay hit, or None to suppress.

    None   → this overlay type has a dedicated report section; suppress from SEPP table.
    str    → display this text in the Practical Implication column.

    Primary source: portal Type + Class + title fields (already specific).
    Class carries the actual standard value (e.g. Water Use "40%", Climate Zone
    "6"); without it the row degrades to a bare postcode/LGA Label. map_title
    names the specific SEPP map, distinguishing e.g. the BASIX Alterations and
    BASIX Buildings climate zone maps.
    No hardcoded descriptions. No fallback keyword dict.
    """
    if type_ and any(t in type_.lower() for t in _SUPPRESS_TYPES):
        return None

    parts: list[str] = []
    if type_ and class_ and class_.lower() != type_.lower():
        parts.append(f"{type_}: {class_}")
    elif type_:
        parts.append(type_)
    if map_title and (not type_ or map_title.lower() != type_.lower()):
        parts.append(map_title)
    elif label and (not type_ or label.lower() != type_.lower()):
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
                   legislation_url, effective_date, stale_since, stale_reason
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
            # Auto-stale (W3): set by the legislation monitor on a source
            # instrument version change; values still serve, with a notice.
            "stale_since": r[9],
            "stale_reason": r[10],
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
    returns the stored numeric value for that standard

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


def _validate_sepp_sd_config(min_lot_row: Optional[dict]) -> Optional[dict]:
    """Validate the min_lot_size row into calc_feasibility's sepp_standards shape.

    Returns {"sd_min_lot": float, "sd_zones": set[str]} only when the minimum
    is a finite positive number and every zone entry is a non-empty string.
    A zero/NaN minimum would silently pass every lot, and a null zone entry
    would crash sorted() mid-render — corrupt rows fail closed to None, which
    renders "Not assessed" downstream.
    """
    if not min_lot_row:
        return None
    try:
        min_lot = float(min_lot_row.get("numeric_value"))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(min_lot) or min_lot <= 0:
        return None
    raw_zones = min_lot_row.get("applicable_zones")
    if not isinstance(raw_zones, (list, tuple, set)):
        return None
    zones = set()
    for z in raw_zones:
        if not isinstance(z, str) or not z.strip():
            return None
        zones.add(z.strip())
    if not zones:
        return None
    out = {"sd_min_lot": min_lot, "sd_zones": zones}
    # Auto-stale passthrough (W3): the caller renders a notice when present.
    if min_lot_row.get("stale_since"):
        out["stale_since"] = min_lot_row.get("stale_since")
        out["stale_reason"] = min_lot_row.get("stale_reason")
    return out


# prior-art-checked: MOVED from services/conveyancing.py._load_regulatory_configs
# (not a fork — that module now imports this) so the CLI report path can inject
# the same DB-loaded configs instead of silently rendering without them.
def load_regulatory_configs(db_url: Optional[str]) -> tuple[Optional[dict], Optional[dict]]:
    """Load SEPP Housing + tax thresholds from DB for calc_feasibility.

    Returns (sepp_standards, tax_config) — both None if DB unavailable.
    A None element renders fail-visible as "Not assessed" downstream.
    """
    if not db_url:
        logger.warning("Regulatory configs: DATABASE_URL not set — secondary dwelling and land tax render 'Not assessed'")
        return None, None
    conn = None
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        # SEPP secondary dwelling standards — NO fallback (#684): a missing or
        # incomplete min_lot_size row returns None, and the secondary-dwelling
        # feasibility row renders "Not assessed" downstream. A hardcoded
        # regulatory figure must never render silently.
        sd_rows = fetch_sepp_housing_standards(conn, development_type="secondary_dwelling")
        min_lot_row = None
        if sd_rows:
            sd_by_type = {r["standard_type"]: r for r in sd_rows}
            min_lot_row = sd_by_type.get("min_lot_size")
        sepp_standards = _validate_sepp_sd_config(min_lot_row)
        if sepp_standards is None:
            logger.warning(
                "Regulatory configs: no valid min_lot_size row for secondary_dwelling — "
                "secondary-dwelling feasibility renders 'Not assessed'"
            )
        # Tax thresholds — no fallback; None renders "Not assessed"
        tax_config = fetch_tax_thresholds(conn)
        if tax_config is None:
            logger.warning("Regulatory configs: no tax_thresholds row for current year — land tax renders 'Not assessed'")
        return sepp_standards, tax_config
    except Exception as e:
        logger.warning(f"Failed to load regulatory configs from DB: {e}")
        return None, None
    finally:
        if conn:
            conn.close()


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
                "cost_of_development": cost,  # WO-4: selected + unpacked but was omitted -> NearbyDA.cost always null
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
            warnings.append("SEPP: missing min_lot_size for secondary_dwelling — feasibility row renders 'Not assessed'")
        if "max_floor_area" not in rows:
            warnings.append("SEPP: missing max_floor_area for secondary_dwelling")
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
