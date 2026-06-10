#!/usr/bin/env python3
"""Build the lot_search_index table.

Two-phase process:
  Phase 1: Spatial join — assign overlays (zone, height, FSR, heritage, flood,
           bushfire, acid_sulfate) from spatial_overlays to cadastre lots.
  Phase 2: Constraint arithmetic — run compute_constraint_arithmetic() for each
           lot in LGAs with DCP coverage, caching DCP/SEPP per (LGA, zone).

Usage:
  python scripts/build_lot_search_index.py                     # all LGAs
  python scripts/build_lot_search_index.py --lga "INNER WEST"  # single LGA
  python scripts/build_lot_search_index.py --phase overlays     # overlays only
  python scripts/build_lot_search_index.py --phase compute      # CA only
  python scripts/build_lot_search_index.py --dry-run            # show counts
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

load_dotenv(Path(__file__).parent.parent / ".env")

# Ensure project root + scripts on path for imports
_project_root = str(Path(__file__).resolve().parent.parent)
_scripts_dir = str(Path(__file__).resolve().parent)
for p in [_project_root, _scripts_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from conveyancing_db import fetch_dcp_setbacks, fetch_sepp_housing_standards
from services.constraint_arithmetic import compute_constraint_arithmetic
from services.constraint_models import (
    DCPControl,
    SEPPStandard,
    SeppLepOverride,
)
from services.intelligence_brief import _build_sepp_housing, _detect_sepp_lep_overrides

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL") or ""

# ---------------------------------------------------------------------------
# LGA name → DCP slug mapping
# ---------------------------------------------------------------------------
# Merged LGAs store DCP data under former council slugs.
# Other LGAs may have name mismatches (hyphens, prefixes).

LGA_TO_DCP_SLUGS: dict[str, list[str]] = {
    "INNER WEST": ["ashfield", "leichhardt", "marrickville"],
    "CANTERBURY-BANKSTOWN": ["canterbury_bankstown"],
    "SYDNEY": ["city_of_sydney"],
    "KU-RING-GAI": ["ku_ring_gai"],
    "CITY OF PARRAMATTA": ["parramatta"],
    "THE HILLS SHIRE": ["the_hills"],
}


def lga_name_to_dcp_slugs(lga_name: str, all_dcp_slugs: list[str]) -> list[str]:
    """Map an overlay LGA name to its DCP slug(s).

    Uses explicit mapping first, then falls back to simple slug conversion.
    Returns only slugs that actually exist in dcp_setback_controls.
    """
    if lga_name in LGA_TO_DCP_SLUGS:
        return [s for s in LGA_TO_DCP_SLUGS[lga_name] if s in all_dcp_slugs]
    # Fallback: simple slug conversion
    slug = lga_name.lower().replace(" ", "_").replace("-", "_")
    return [slug] if slug in all_dcp_slugs else []


# ---------------------------------------------------------------------------
# Phase 1: Overlay assignment
# ---------------------------------------------------------------------------


def get_lga_list(conn) -> list[str]:
    """Return distinct LGA names from spatial_overlays that have zone data."""
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT lga_name
        FROM spatial_overlays
        WHERE layer_type = 'zone' AND lga_name IS NOT NULL
        ORDER BY lga_name
    """)
    return [r[0] for r in cur.fetchall()]


def assign_overlays_for_lga(conn, lga_name: str, dry_run: bool = False) -> int:
    """Spatial-join cadastre lots with overlays for one LGA.

    Steps:
      1. Insert base lot data (lotidstring, area, urbanity, geom)
      2. Assign zone (largest intersection area wins)
      3. Assign height, FSR (max numeric value)
      4. Assign heritage, flood, bushfire, acid_sulfate (boolean flags)

    Returns the number of lots processed.
    """
    cur = conn.cursor()

    # Count lots that intersect this LGA's zone overlays
    cur.execute("""
        SELECT COUNT(DISTINCT c.lotidstring)
        FROM nsw_cadastre_lots c
        JOIN spatial_overlays so ON ST_Intersects(c.geom, so.geom)
        WHERE so.layer_type = 'zone'
          AND so.lga_name = %s
          AND c.geom IS NOT NULL
    """, (lga_name,))
    lot_count = cur.fetchone()[0]
    log.info("LGA %s: %d lots intersect zone overlays", lga_name, lot_count)

    if dry_run or lot_count == 0:
        return lot_count

    # Step 1: Insert base lot data
    log.info("  Step 1: Insert base lot data...")
    cur.execute("""
        INSERT INTO lot_search_index (lotidstring, lga_name, lot_area_m2, urbanity, geom)
        SELECT DISTINCT ON (c.lotidstring)
            c.lotidstring,
            %s,
            COALESCE(c.planlotarea, c.shape_area),
            c.urbanity,
            c.geom
        FROM nsw_cadastre_lots c
        JOIN spatial_overlays so ON ST_Intersects(c.geom, so.geom)
        WHERE so.layer_type = 'zone'
          AND so.lga_name = %s
          AND c.geom IS NOT NULL
        ON CONFLICT (lotidstring) DO UPDATE SET
            lga_name    = EXCLUDED.lga_name,
            lot_area_m2 = EXCLUDED.lot_area_m2,
            urbanity    = EXCLUDED.urbanity,
            geom        = EXCLUDED.geom
    """, (lga_name, lga_name))
    conn.commit()
    log.info("  Step 1 done: %d rows upserted", cur.rowcount)

    # Step 2: Assign zone
    # Strategy: use centroid containment (fast, correct for 95%+ of lots).
    # For the few lots that straddle zone boundaries, centroid still picks
    # the zone that contains the lot's centre — good enough for search purposes.
    log.info("  Step 2: Assign zone codes...")
    cur.execute("""
        UPDATE lot_search_index lsi
        SET zone_code = sub.value
        FROM (
            SELECT DISTINCT ON (lsi2.lotidstring)
                lsi2.lotidstring,
                so.value
            FROM lot_search_index lsi2
            JOIN spatial_overlays so ON ST_Intersects(
                ST_Centroid(lsi2.geom), so.geom
            )
            WHERE so.layer_type = 'zone'
              AND so.lga_name = %s
              AND lsi2.lga_name = %s
            ORDER BY lsi2.lotidstring
        ) sub
        WHERE lsi.lotidstring = sub.lotidstring
    """, (lga_name, lga_name))
    conn.commit()
    log.info("  Step 2 done: %d zone assignments", cur.rowcount)

    # Steps 3-8: Use centroid containment for overlay assignment.
    # Point-in-polygon via GIST index is ~100x faster than full polygon intersection.
    # For boolean flags (heritage/flood/bushfire/acid_sulfate) and numeric maxima
    # (height/FSR), centroid is accurate: if a lot's centre is in the overlay, the
    # lot is affected. Edge cases (lot straddles boundary) are negligible for search.

    # Step 3: Assign height (max value)
    log.info("  Step 3: Assign height...")
    cur.execute("""
        UPDATE lot_search_index lsi
        SET lep_height_m = sub.max_val
        FROM (
            SELECT lsi2.lotidstring, MAX(so.value_numeric) AS max_val
            FROM lot_search_index lsi2
            JOIN spatial_overlays so ON ST_Intersects(ST_Centroid(lsi2.geom), so.geom)
            WHERE so.layer_type = 'height'
              AND so.lga_name = %s
              AND lsi2.lga_name = %s
              AND so.value_numeric IS NOT NULL
            GROUP BY lsi2.lotidstring
        ) sub
        WHERE lsi.lotidstring = sub.lotidstring
    """, (lga_name, lga_name))
    conn.commit()
    log.info("  Step 3 done: %d height assignments", cur.rowcount)

    # Step 4: Assign FSR (max value)
    log.info("  Step 4: Assign FSR...")
    cur.execute("""
        UPDATE lot_search_index lsi
        SET lep_fsr = sub.max_val
        FROM (
            SELECT lsi2.lotidstring, MAX(so.value_numeric) AS max_val
            FROM lot_search_index lsi2
            JOIN spatial_overlays so ON ST_Intersects(ST_Centroid(lsi2.geom), so.geom)
            WHERE so.layer_type = 'fsr'
              AND so.lga_name = %s
              AND lsi2.lga_name = %s
              AND so.value_numeric IS NOT NULL
            GROUP BY lsi2.lotidstring
        ) sub
        WHERE lsi.lotidstring = sub.lotidstring
    """, (lga_name, lga_name))
    conn.commit()
    log.info("  Step 4 done: %d FSR assignments", cur.rowcount)

    # Step 5: Heritage flags
    log.info("  Step 5: Assign heritage...")
    cur.execute("""
        UPDATE lot_search_index lsi
        SET heritage = TRUE,
            heritage_type = sub.htype
        FROM (
            SELECT DISTINCT ON (lsi2.lotidstring)
                lsi2.lotidstring,
                CASE
                    WHEN so.value ILIKE 'Item%%' THEN 'item'
                    WHEN so.value ILIKE 'Conservation%%' THEN 'hca'
                    ELSE 'item'
                END AS htype
            FROM lot_search_index lsi2
            JOIN spatial_overlays so ON ST_Intersects(ST_Centroid(lsi2.geom), so.geom)
            WHERE so.layer_type = 'heritage'
              AND so.lga_name = %s
              AND lsi2.lga_name = %s
            ORDER BY lsi2.lotidstring,
                CASE WHEN so.value ILIKE 'Item%%' THEN 0 ELSE 1 END
        ) sub
        WHERE lsi.lotidstring = sub.lotidstring
    """, (lga_name, lga_name))
    conn.commit()
    log.info("  Step 5 done: %d heritage flags", cur.rowcount)

    # Steps 6-8: Flood/bushfire/acid overlays may be statewide (no lga_name).
    # Supabase Pro enforces a hard 2-minute statement timeout. We batch lots
    # in chunks of 5000 to stay under the limit.

    def _assign_boolean_flag_batched(
        layer_type: str, col: str, lga: str, batch_sz: int = 1000,
        category_col: Optional[str] = None,
    ) -> int:
        """Batch spatial join for boolean flag overlays.

        Uses lot centroid for point-in-polygon (fast via GIST).
        Batch size 1000 stays well under Supabase 2-min statement timeout.
        """
        total = 0
        offset = 0
        while True:
            cur.execute("""
                SELECT lotidstring FROM lot_search_index
                WHERE lga_name = %s
                ORDER BY lotidstring
                LIMIT %s OFFSET %s
            """, (lga, batch_sz, offset))
            batch = [r[0] for r in cur.fetchall()]
            if not batch:
                break

            if category_col:
                cur.execute(f"""
                    UPDATE lot_search_index lsi
                    SET {col} = TRUE,
                        {category_col} = sub.cat
                    FROM (
                        SELECT DISTINCT ON (lsi2.lotidstring)
                            lsi2.lotidstring,
                            so.value AS cat
                        FROM lot_search_index lsi2
                        JOIN spatial_overlays so
                          ON so.geom && lsi2.geom
                          AND ST_Intersects(ST_Centroid(lsi2.geom), so.geom)
                        WHERE so.layer_type = %s
                          AND lsi2.lotidstring = ANY(%s)
                        ORDER BY lsi2.lotidstring, so.value
                    ) sub
                    WHERE lsi.lotidstring = sub.lotidstring
                """, (layer_type, batch))
            else:
                cur.execute(f"""
                    UPDATE lot_search_index lsi
                    SET {col} = TRUE
                    FROM (
                        SELECT DISTINCT lsi2.lotidstring
                        FROM lot_search_index lsi2
                        JOIN spatial_overlays so
                          ON so.geom && lsi2.geom
                          AND ST_Intersects(ST_Centroid(lsi2.geom), so.geom)
                        WHERE so.layer_type = %s
                          AND lsi2.lotidstring = ANY(%s)
                    ) sub
                    WHERE lsi.lotidstring = sub.lotidstring
                """, (layer_type, batch))
            conn.commit()
            total += cur.rowcount
            offset += batch_sz
            if offset % 10000 == 0:
                log.info("    ... %d lots processed", offset)
        return total

    # Step 6: Flood flag
    log.info("  Step 6: Assign flood...")
    n = _assign_boolean_flag_batched('flood', 'flood_prone', lga_name)
    log.info("  Step 6 done: %d flood flags", n)

    # Step 7: Bushfire flag + category
    log.info("  Step 7: Assign bushfire...")
    n = _assign_boolean_flag_batched('bushfire', 'bushfire_prone', lga_name,
                                     category_col='bushfire_category')
    log.info("  Step 7 done: %d bushfire flags", n)

    # Step 8: Acid sulfate flag
    log.info("  Step 8: Assign acid sulfate...")
    n = _assign_boolean_flag_batched('acid_sulfate', 'acid_sulfate', lga_name)
    log.info("  Step 8 done: %d acid sulfate flags", n)
    conn.commit()

    # Step 9: Former council assignment (for merged LGAs)
    log.info("  Step 9: Assign former council...")
    cur.execute("""
        UPDATE lot_search_index lsi
        SET former_council = sub.former_council
        FROM (
            SELECT DISTINCT ON (lsi2.lotidstring)
                lsi2.lotidstring,
                LOWER(pb.former_council) as former_council
            FROM lot_search_index lsi2
            JOIN dcp_precinct_boundaries pb
                ON ST_Contains(pb.boundary, ST_Centroid(lsi2.geom))
            WHERE lsi2.lga_name = %s
                AND lsi2.former_council IS NULL
                AND pb.former_council IS NOT NULL
            ORDER BY lsi2.lotidstring
        ) sub
        WHERE lsi.lotidstring = sub.lotidstring
    """, (lga_name,))
    fc_count = cur.rowcount
    conn.commit()
    log.info("  Step 9 done: %d lots assigned to former councils", fc_count)

    return lot_count


# ---------------------------------------------------------------------------
# Phase 2: Batch constraint arithmetic compute
# ---------------------------------------------------------------------------


def get_lgas_with_dcp(conn) -> list[str]:
    """Return LGA slugs that have DCP setback controls in the DB."""
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT lga FROM dcp_setback_controls
        WHERE lga IS NOT NULL AND is_current = TRUE
        ORDER BY lga
    """)
    return [r[0] for r in cur.fetchall()]


# Reverse mapping: DCP slug → overlay LGA name (built from LGA_TO_DCP_SLUGS)
_DCP_SLUG_TO_LGA: dict[str, str] = {}
for _lga, _slugs in LGA_TO_DCP_SLUGS.items():
    for _s in _slugs:
        _DCP_SLUG_TO_LGA[_s] = _lga


def _lga_slug_to_overlay_name(slug: str) -> str:
    """Convert DCP lga slug to spatial_overlays lga_name.

    Handles former-council slugs (ashfield → INNER WEST) via explicit mapping,
    falls back to simple underscore→space conversion.
    """
    if slug in _DCP_SLUG_TO_LGA:
        return _DCP_SLUG_TO_LGA[slug]
    return slug.replace("_", " ").upper()


def _parse_numeric(val: any) -> Optional[float]:
    """Extract a numeric value from a string like '4.0 m minimum' or a raw number."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    import re
    m = re.search(r'\d+\.?\d*', str(val))
    return float(m.group()) if m else None


def _build_dcp_controls_from_raw(dcp_raw: Optional[dict]) -> list[DCPControl]:
    """Convert conveyancing_db.fetch_dcp_setbacks() result to DCPControl list.

    Mirrors the conversion in constraint_arithmetic._fetch_constraint_data_from_db().
    """
    if not dcp_raw:
        return []
    controls: list[DCPControl] = []
    all_setbacks = (dcp_raw.get("setbacks") or []) + (dcp_raw.get("sd_setbacks") or [])
    for s in all_setbacks:
        # Prefer semantic_type (e.g. "front_setback") over control_type ("prescribed")
        sem_type = s.get("semantic_type") or s.get("control_type") or s.get("type") or ""
        # Prefer raw numeric value_min over parsing formatted requirement string
        vmin = s.get("value_min")
        if vmin is None:
            vmin = _parse_numeric(s.get("requirement"))
        vmax = s.get("value_max")
        if vmax is None:
            vmax = _parse_numeric(s.get("value_max"))
        controls.append(DCPControl(
            control_type=sem_type,
            dev_type=s.get("dev_type", "dwelling_house"),
            value_min=vmin,
            value_max=vmax,
            unit=s.get("unit", "m"),
            condition=s.get("notes") or s.get("condition"),
            source_ref=s.get("clause") or dcp_raw.get("clause_ref"),
        ))
    return controls


def compute_constraints_for_lga(
    conn,
    lga_slug: str,
    batch_size: int = 2000,
    dry_run: bool = False,
) -> int:
    """Run constraint arithmetic for all lots in an LGA.

    DCP/SEPP data is cached per (lga, zone) to avoid repeated DB queries.
    Returns the number of lots computed.
    """
    lga_overlay_name = _lga_slug_to_overlay_name(lga_slug)
    cur = conn.cursor()

    # Count lots that need computation
    cur.execute("""
        SELECT COUNT(*)
        FROM lot_search_index
        WHERE lga_name = %s
          AND zone_code IS NOT NULL
          AND lot_area_m2 > 0
          AND computed_at IS NULL
    """, (lga_overlay_name,))
    pending = cur.fetchone()[0]
    log.info("LGA %s (%s): %d lots pending CA compute", lga_slug, lga_overlay_name, pending)

    if dry_run or pending == 0:
        return pending

    # Caches: DCP per (lga, zone), SEPP raw per zone — avoids N identical queries
    # SEPP raw is cached, but _build_sepp_housing is called per-lot (uses lot_area_m2
    # for eligibility checks and lot-size bands — caching the built result would give
    # wrong eligibility for lots with different areas in the same zone).
    dcp_cache: dict[str, list[DCPControl]] = {}
    sepp_raw_cache: dict[str, list[dict]] = {}

    def _get_dcp(zone: str, former_council: Optional[str] = None) -> list[DCPControl]:
        # Use former_council slug for DCP lookup when available (merged LGAs)
        dcp_slug = former_council or lga_slug
        cache_key = f"{dcp_slug}:{zone}"
        if cache_key not in dcp_cache:
            raw = fetch_dcp_setbacks(conn, dcp_slug, zone)
            # Also include council-wide controls (e.g. inner_west applies to all)
            if former_council and former_council != lga_slug:
                raw_wide = fetch_dcp_setbacks(conn, lga_slug, zone)
                if raw_wide and raw:
                    # Merge: council-wide setbacks + former-council-specific setbacks
                    raw["setbacks"] = (raw.get("setbacks") or []) + (raw_wide.get("setbacks") or [])
                    raw["sd_setbacks"] = (raw.get("sd_setbacks") or []) + (raw_wide.get("sd_setbacks") or [])
                elif raw_wide and not raw:
                    raw = raw_wide
            dcp_cache[cache_key] = _build_dcp_controls_from_raw(raw)
        return dcp_cache[cache_key]

    def _get_sepp(zone: str, area: float) -> list[SEPPStandard]:
        """Get SEPP standards with per-lot eligibility based on actual area."""
        if zone not in sepp_raw_cache:
            sepp_raw_cache[zone] = fetch_sepp_housing_standards(conn, zone_code=zone)
        return _build_sepp_housing(sepp_raw_cache[zone], zone, area)

    def _get_overrides(
        sepp: list[SEPPStandard],
        height_m: Optional[float],
        fsr: Optional[float],
    ) -> list[SeppLepOverride]:
        return _detect_sepp_lep_overrides(sepp, height_m, fsr)

    # Dev type priority: highest-density first. When multiple SEPP dev_types are
    # eligible for a lot (zone permits it + lot area meets min_lot_size), we
    # compute CA for the most permissive one to show realistic maximum yield.
    _DEV_TYPE_PRIORITY = [
        "residential_flat_r3r4_inner",
        "residential_flat_r3r4_outer",
        "residential_flat_r1r2",
        "multi_dwelling",
        "terraces",
        "manor_house",
        "dual_occupancy",
    ]

    def _best_dev_type(sepp_standards: list[SEPPStandard]) -> str:
        """Pick the most permissive eligible SEPP dev_type, fallback to dwelling_house."""
        eligible = [s.dev_type for s in sepp_standards if s.eligible]
        for dt in _DEV_TYPE_PRIORITY:
            if dt in eligible:
                return dt
        return "dwelling_house"

    total_computed = 0
    offset = 0

    while True:
        cur.execute("""
            SELECT lotidstring, lot_area_m2, zone_code, lep_height_m, lep_fsr, former_council
            FROM lot_search_index
            WHERE lga_name = %s
              AND zone_code IS NOT NULL
              AND lot_area_m2 > 0
              AND computed_at IS NULL
            ORDER BY lotidstring
            LIMIT %s
        """, (lga_overlay_name, batch_size))

        rows = cur.fetchall()
        if not rows:
            break

        updates = []
        for lotid, area, zone, height_m, fsr, former_council in rows:
            dcp = _get_dcp(zone, former_council)
            sepp = _get_sepp(zone, area)
            dev_type = _best_dev_type(sepp)
            overrides = _get_overrides(sepp, height_m, fsr)

            height_str = str(height_m) if height_m is not None else None
            fsr_str = str(fsr) if fsr is not None else None

            result = compute_constraint_arithmetic(
                lot_area_m2=area,
                dev_type=dev_type,
                lep_height_str=height_str,
                lep_fsr_str=fsr_str,
                dcp_controls=dcp,
                sepp_standards=sepp,
                sepp_lep_overrides=overrides,
            )

            updates.append((
                result.realistic_gfa_m2,
                result.realistic_dwellings,
                result.binding_constraint.value if result.binding_constraint else None,
                result.effective_height_m,
                result.effective_fsr,
                result.confidence,
                result.setback_front_m,
                result.setback_rear_m,
                result.setback_side_m,
                result.buildable_footprint_m2,
                result.lep_envelope_gfa_m2,
                result.gaps if result.gaps else None,
                dev_type,
                lotid,
            ))

        if updates:
            execute_values(
                cur,
                """
                UPDATE lot_search_index AS lsi SET
                    ca_realistic_gfa_m2       = v.gfa,
                    ca_realistic_dwellings    = v.dwellings,
                    ca_binding_constraint     = v.binding,
                    ca_effective_height_m     = v.eff_height,
                    ca_effective_fsr          = v.eff_fsr,
                    ca_confidence             = v.confidence,
                    ca_setback_front_m        = v.sb_front,
                    ca_setback_rear_m         = v.sb_rear,
                    ca_setback_side_m         = v.sb_side,
                    ca_buildable_footprint_m2 = v.footprint,
                    ca_lep_envelope_gfa_m2    = v.envelope,
                    ca_gaps                   = v.gaps,
                    ca_dev_type               = v.dev_type,
                    computed_at               = NOW()
                FROM (VALUES %s) AS v(
                    gfa, dwellings, binding, eff_height, eff_fsr, confidence,
                    sb_front, sb_rear, sb_side, footprint, envelope, gaps,
                    dev_type, lotidstring
                )
                WHERE lsi.lotidstring = v.lotidstring
                """,
                updates,
                template=(
                    "(%s::double precision, %s::int, %s, %s::double precision,"
                    " %s::double precision, %s, %s::double precision,"
                    " %s::double precision, %s::double precision,"
                    " %s::double precision, %s::double precision, %s::text[],"
                    " %s, %s)"
                ),
            )
            conn.commit()

        total_computed += len(updates)
        log.info("  Computed %d / %d lots (batch of %d)", total_computed, pending, len(rows))

    log.info("LGA %s: %d lots computed", lga_slug, total_computed)
    return total_computed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Build lot_search_index")
    parser.add_argument("--lga", help="Process single LGA (overlay name, e.g. 'INNER WEST')")
    parser.add_argument("--phase", choices=["overlays", "compute", "all"], default="all",
                        help="Which phase to run (default: all)")
    parser.add_argument("--batch-size", type=int, default=2000, help="Batch size for CA compute")
    parser.add_argument("--dry-run", action="store_true", help="Show counts only, no writes")
    args = parser.parse_args()

    if not DATABASE_URL:
        log.error("DATABASE_URL or SUPABASE_DB_URL not set")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL, options="-c statement_timeout=600000")
    conn.autocommit = False

    t0 = time.time()

    if args.phase in ("overlays", "all"):
        log.info("=== Phase 1: Overlay assignment ===")
        if args.lga:
            lgas = [args.lga]
        else:
            lgas = get_lga_list(conn)
        log.info("Processing %d LGAs", len(lgas))

        total_lots = 0
        for lga in lgas:
            n = assign_overlays_for_lga(conn, lga, dry_run=args.dry_run)
            total_lots += n
        log.info("Phase 1 complete: %d total lots across %d LGAs (%.1fs)",
                 total_lots, len(lgas), time.time() - t0)

    if args.phase in ("compute", "all"):
        log.info("=== Phase 2: Constraint arithmetic compute ===")
        t1 = time.time()
        dcp_lgas = get_lgas_with_dcp(conn)
        log.info("Found %d LGAs with DCP data", len(dcp_lgas))

        if args.lga:
            # Map overlay LGA name to DCP slug(s)
            target_slugs = lga_name_to_dcp_slugs(args.lga, dcp_lgas)
            if target_slugs:
                log.info("LGA %s maps to DCP slugs: %s", args.lga, target_slugs)
                dcp_lgas = target_slugs
            else:
                log.warning("LGA %s has no DCP data, skipping CA compute", args.lga)
                dcp_lgas = []

        total_computed = 0
        for slug in dcp_lgas:
            n = compute_constraints_for_lga(
                conn, slug, batch_size=args.batch_size, dry_run=args.dry_run,
            )
            total_computed += n
        log.info("Phase 2 complete: %d lots computed across %d LGAs (%.1fs)",
                 total_computed, len(dcp_lgas), time.time() - t1)

    # Summary
    if not args.dry_run:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM lot_search_index")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM lot_search_index WHERE ca_realistic_gfa_m2 IS NOT NULL")
        with_ca = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT lga_name) FROM lot_search_index")
        n_lgas = cur.fetchone()[0]
        log.info("=== Summary ===")
        log.info("  Total indexed lots: %d", total)
        log.info("  Lots with CA results: %d", with_ca)
        log.info("  LGAs covered: %d", n_lgas)
        log.info("  Total time: %.1fs", time.time() - t0)

    conn.close()


if __name__ == "__main__":
    main()
