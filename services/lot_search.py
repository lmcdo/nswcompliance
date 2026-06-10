"""Lot search API — query the pre-computed lot_search_index.

Provides two endpoints:
  POST /lot-search          — paginated lot list with filters
  POST /lot-search/summary  — aggregate stats for the same filters
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

# Whitelist of columns that can be used for ORDER BY — prevents SQL injection.
_ALLOWED_ORDER_COLS = frozenset({
    "ca_realistic_gfa_m2",
    "ca_realistic_dwellings",
    "lot_area_m2",
    "lep_height_m",
    "lep_fsr",
    "ca_buildable_footprint_m2",
    "ca_lep_envelope_gfa_m2",
    "zone_code",
    "lga_name",
})


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class LotSearchRequest(BaseModel):
    lga_name: Optional[str] = None
    zone_codes: Optional[list[str]] = None
    min_area_m2: Optional[float] = None
    max_area_m2: Optional[float] = None
    min_gfa_m2: Optional[float] = None
    max_gfa_m2: Optional[float] = None
    min_dwellings: Optional[int] = None
    heritage: Optional[bool] = None
    flood_prone: Optional[bool] = None
    bushfire_prone: Optional[bool] = None
    min_confidence: Optional[str] = None
    binding_constraint: Optional[list[str]] = None
    bbox: Optional[list[float]] = Field(
        None,
        description="Bounding box [min_lng, min_lat, max_lng, max_lat]",
        min_length=4,
        max_length=4,
    )
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)
    order_by: str = "ca_realistic_gfa_m2"
    order_dir: str = Field("desc", pattern="^(asc|desc)$")


class LotSearchResult(BaseModel):
    lotidstring: str
    lga_name: Optional[str] = None
    former_council: Optional[str] = None
    zone_code: Optional[str] = None
    lot_area_m2: Optional[float] = None
    lep_height_m: Optional[float] = None
    lep_fsr: Optional[float] = None
    heritage: bool = False
    flood_prone: bool = False
    bushfire_prone: bool = False
    bushfire_category: Optional[str] = None
    ca_realistic_gfa_m2: Optional[float] = None
    ca_realistic_dwellings: Optional[int] = None
    ca_binding_constraint: Optional[str] = None
    ca_confidence: Optional[str] = None
    ca_effective_height_m: Optional[float] = None
    ca_effective_fsr: Optional[float] = None
    ca_buildable_footprint_m2: Optional[float] = None
    ca_setback_front_m: Optional[float] = None
    ca_setback_rear_m: Optional[float] = None
    ca_setback_side_m: Optional[float] = None
    ca_gaps: Optional[list[str]] = None


class LotSearchResponse(BaseModel):
    lots: list[LotSearchResult]
    total_count: int
    query_ms: float


class ZoneDistribution(BaseModel):
    zone_code: str
    count: int


class BindingDistribution(BaseModel):
    binding_constraint: Optional[str]
    count: int


class LotSearchSummary(BaseModel):
    total_lots: int
    lots_with_ca: int
    avg_area_m2: Optional[float] = None
    avg_gfa_m2: Optional[float] = None
    median_gfa_m2: Optional[float] = None
    p25_gfa_m2: Optional[float] = None
    p75_gfa_m2: Optional[float] = None
    avg_dwellings: Optional[float] = None
    heritage_count: int = 0
    flood_count: int = 0
    bushfire_count: int = 0
    zone_distribution: list[ZoneDistribution] = []
    binding_distribution: list[BindingDistribution] = []
    confidence_high: int = 0
    confidence_medium: int = 0
    confidence_low: int = 0
    query_ms: float = 0


# ---------------------------------------------------------------------------
# Query builder
# ---------------------------------------------------------------------------

# Confidence ordering for >= filter
_CONFIDENCE_LEVELS = {"low": 0, "medium": 1, "high": 2}


def _build_where(req: LotSearchRequest) -> tuple[str, list]:
    """Build parameterised WHERE clause from request filters.

    Returns (where_sql, params).
    """
    conditions: list[str] = []
    params: list = []

    if req.lga_name:
        conditions.append("lga_name = %s")
        params.append(req.lga_name.upper())
    if req.zone_codes:
        conditions.append("zone_code = ANY(%s)")
        params.append(req.zone_codes)
    if req.min_area_m2 is not None:
        conditions.append("lot_area_m2 >= %s")
        params.append(req.min_area_m2)
    if req.max_area_m2 is not None:
        conditions.append("lot_area_m2 <= %s")
        params.append(req.max_area_m2)
    if req.min_gfa_m2 is not None:
        conditions.append("ca_realistic_gfa_m2 >= %s")
        params.append(req.min_gfa_m2)
    if req.max_gfa_m2 is not None:
        conditions.append("ca_realistic_gfa_m2 <= %s")
        params.append(req.max_gfa_m2)
    if req.min_dwellings is not None:
        conditions.append("ca_realistic_dwellings >= %s")
        params.append(req.min_dwellings)
    if req.heritage is not None:
        conditions.append("heritage = %s")
        params.append(req.heritage)
    if req.flood_prone is not None:
        conditions.append("flood_prone = %s")
        params.append(req.flood_prone)
    if req.bushfire_prone is not None:
        conditions.append("bushfire_prone = %s")
        params.append(req.bushfire_prone)
    if req.min_confidence:
        min_level = _CONFIDENCE_LEVELS.get(req.min_confidence, 0)
        valid = [k for k, v in _CONFIDENCE_LEVELS.items() if v >= min_level]
        if valid:
            conditions.append("ca_confidence = ANY(%s)")
            params.append(valid)
    if req.binding_constraint:
        conditions.append("ca_binding_constraint = ANY(%s)")
        params.append(req.binding_constraint)
    if req.bbox and len(req.bbox) == 4:
        conditions.append(
            "ST_Intersects(geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))"
        )
        params.extend(req.bbox)

    where = " AND ".join(conditions) if conditions else "TRUE"
    return where, params


# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------


def _get_conn():
    """Get a database connection. Raises HTTPException if unavailable."""
    import psycopg2

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(status_code=503, detail="Database not configured")
    try:
        conn = psycopg2.connect(db_url, options="-c statement_timeout=30000")
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error("lot-search DB connection failed: %s", e)
        raise HTTPException(status_code=503, detail="Database unavailable")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/lot-search", response_model=LotSearchResponse)
async def lot_search(req: LotSearchRequest):
    """Search the lot index with filters. Returns paginated results."""
    order_col = req.order_by if req.order_by in _ALLOWED_ORDER_COLS else "ca_realistic_gfa_m2"
    order_dir = "DESC" if req.order_dir == "desc" else "ASC"

    where, params = _build_where(req)

    conn = _get_conn()
    try:
        cur = conn.cursor()
        t0 = time.time()

        # Count total matching rows
        cur.execute(f"SELECT COUNT(*) FROM lot_search_index WHERE {where}", params)
        total_count = cur.fetchone()[0]

        # Fetch page — NULLS LAST so lots with data sort first
        cur.execute(
            f"""
            SELECT lotidstring, lga_name, former_council, zone_code, lot_area_m2,
                   lep_height_m, lep_fsr, heritage, flood_prone,
                   bushfire_prone, bushfire_category,
                   ca_realistic_gfa_m2, ca_realistic_dwellings,
                   ca_binding_constraint, ca_confidence,
                   ca_effective_height_m, ca_effective_fsr,
                   ca_buildable_footprint_m2,
                   ca_setback_front_m, ca_setback_rear_m, ca_setback_side_m,
                   ca_gaps
            FROM lot_search_index
            WHERE {where}
            ORDER BY {order_col} {order_dir} NULLS LAST
            LIMIT %s OFFSET %s
            """,
            params + [req.limit, req.offset],
        )
        rows = cur.fetchall()
        query_ms = (time.time() - t0) * 1000

        lots = [
            LotSearchResult(
                lotidstring=r[0],
                lga_name=r[1],
                former_council=r[2],
                zone_code=r[3],
                lot_area_m2=r[4],
                lep_height_m=r[5],
                lep_fsr=r[6],
                heritage=r[7] or False,
                flood_prone=r[8] or False,
                bushfire_prone=r[9] or False,
                bushfire_category=r[10],
                ca_realistic_gfa_m2=r[11],
                ca_realistic_dwellings=r[12],
                ca_binding_constraint=r[13],
                ca_confidence=r[14],
                ca_effective_height_m=r[15],
                ca_effective_fsr=r[16],
                ca_buildable_footprint_m2=r[17],
                ca_setback_front_m=r[18],
                ca_setback_rear_m=r[19],
                ca_setback_side_m=r[20],
                ca_gaps=r[21],
            )
            for r in rows
        ]

        return LotSearchResponse(
            lots=lots,
            total_count=total_count,
            query_ms=round(query_ms, 1),
        )
    finally:
        conn.close()


@router.post("/lot-search/summary", response_model=LotSearchSummary)
async def lot_search_summary(req: LotSearchRequest):
    """Aggregate stats for the matching lots — powers the overview dashboard."""
    where, params = _build_where(req)

    conn = _get_conn()
    try:
        cur = conn.cursor()
        t0 = time.time()

        # Scalar aggregates
        cur.execute(f"""
            SELECT
                COUNT(*),
                COUNT(ca_realistic_gfa_m2),
                AVG(lot_area_m2)::double precision,
                AVG(ca_realistic_gfa_m2)::double precision,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ca_realistic_gfa_m2),
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY ca_realistic_gfa_m2),
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY ca_realistic_gfa_m2),
                AVG(ca_realistic_dwellings)::double precision,
                COUNT(*) FILTER (WHERE heritage = TRUE),
                COUNT(*) FILTER (WHERE flood_prone = TRUE),
                COUNT(*) FILTER (WHERE bushfire_prone = TRUE),
                COUNT(*) FILTER (WHERE ca_confidence = 'high'),
                COUNT(*) FILTER (WHERE ca_confidence = 'medium'),
                COUNT(*) FILTER (WHERE ca_confidence = 'low')
            FROM lot_search_index
            WHERE {where}
        """, params)
        row = cur.fetchone()

        # Zone distribution
        cur.execute(f"""
            SELECT zone_code, COUNT(*) AS cnt
            FROM lot_search_index
            WHERE {where} AND zone_code IS NOT NULL
            GROUP BY zone_code
            ORDER BY cnt DESC
            LIMIT 20
        """, params)
        zone_dist = [ZoneDistribution(zone_code=r[0], count=r[1]) for r in cur.fetchall()]

        # Binding constraint distribution
        cur.execute(f"""
            SELECT ca_binding_constraint, COUNT(*) AS cnt
            FROM lot_search_index
            WHERE {where} AND ca_binding_constraint IS NOT NULL
            GROUP BY ca_binding_constraint
            ORDER BY cnt DESC
        """, params)
        binding_dist = [
            BindingDistribution(binding_constraint=r[0], count=r[1])
            for r in cur.fetchall()
        ]

        query_ms = (time.time() - t0) * 1000

        return LotSearchSummary(
            total_lots=row[0],
            lots_with_ca=row[1],
            avg_area_m2=round(row[2], 1) if row[2] else None,
            avg_gfa_m2=round(row[3], 1) if row[3] else None,
            median_gfa_m2=round(row[4], 1) if row[4] else None,
            p25_gfa_m2=round(row[5], 1) if row[5] else None,
            p75_gfa_m2=round(row[6], 1) if row[6] else None,
            avg_dwellings=round(row[7], 1) if row[7] else None,
            heritage_count=row[8],
            flood_count=row[9],
            bushfire_count=row[10],
            confidence_high=row[11],
            confidence_medium=row[12],
            confidence_low=row[13],
            zone_distribution=zone_dist,
            binding_distribution=binding_dist,
            query_ms=round(query_ms, 1),
        )
    finally:
        conn.close()
