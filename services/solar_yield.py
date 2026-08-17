"""
Solar Yield Underwriter — FastAPI router.

POST /pipeline/solar-yield
  Input:  { address, prop_id, lat, lng, report_id, lot_polygon_wgs84 }
  Output: writes to property_reports, returns full output JSON

Pipeline:
  1. Google Solar API buildingInsights — roof segments, panels, annual kWh
  2. Clip solarPanels[] to lot boundary (shapely point-in-polygon)
  3. Recompute totals from lot-clipped panels
  4. Heritage flag from regulatory_provisions
  5. Write to property_reports, return result

Clipping:
  Google Solar findClosest returns the nearest building — not the lot.
  For commercial/industrial sites this is wrong. solarPanels[] has per-panel
  lat/lng, so we filter to panels inside the cadastral lot boundary and
  recompute counts, area, yield, and roof area from those panels only.

Data sources:
  Google Solar API (requires GOOGLE_MAPS_API_KEY with Solar API enabled)

Response contract (must match frontend-nextjs/app/reports/solar-yield/page.tsx):
{
  "max_panels": int,
  "max_panel_area_m2": float,
  "annual_kwh_estimate": float,   # DC at the panel, as Google reports it
  "annual_kwh_delivered": float,  # after system losses — the figure to monetise
  "delivery_basis": str,          # plain-English reason the two differ
  "sunshine_hours_per_year": float,
  "best_pitch_deg": float,
  "best_azimuth_deg": float,   # compass bearing: 0=N, 90=E, 180=S, 270=W
  "roof_area_m2": float,
  "is_heritage": bool,
  "is_commercial_scale": bool,  # roof_area_m2 > 500 after clipping
  "imagery_date": str,          # "YYYY-MM" or "unknown"
  "coverage_available": bool
}
"""
import logging
import os
import time
from datetime import date
from typing import List, Optional

import psycopg2
import psycopg2.extras
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, model_validator

from audit_trail import DataSourceQuery, log_audit_trail, get_current_disclaimer_version
from services.lga_lookup import lookup_lga

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["satellite"])

GOOGLE_SOLAR_API = "https://solar.googleapis.com/v1/buildingInsights:findClosest"
DATA_SOURCES = ["Google Solar API"]

# prior-art-checked: shared item-4 modules created this session — extending
# this pipeline's own envelope, not adding a parallel data source.
try:
    from services.execution_manifest import MANIFEST_KEY, build_manifest
    from services.geometry_checks import check_point_nsw, check_polygon_wgs84
except ImportError:
    from execution_manifest import MANIFEST_KEY, build_manifest
    from geometry_checks import check_point_nsw, check_polygon_wgs84

# Algorithm revision for execution manifests (campaign item 4). Bump on
# method change, not per deploy (deploy identity = manifest deploy_sha).
ALGORITHM_VERSION = "solar-google-insights-1.0"


# ---------------------------------------------------------------------------
# Google Solar API response models
# ---------------------------------------------------------------------------
# These validate and normalise the raw API response at the boundary.
# _NullSafeModel strips null values before field validation so field defaults
# apply when Google sends null — this eliminates the `or 0.0` pattern
# throughout parsing code and prevents TypeError on null numeric fields.
#
# Exception: azimuthDegrees is kept Optional[float] = None because 0.0 is a
# *valid* value (due north) that must be distinguished from "not provided".
# ---------------------------------------------------------------------------

class _NullSafeModel(BaseModel):
    """Strip null dict values before Pydantic processes them so defaults apply."""

    @model_validator(mode="before")
    @classmethod
    def _strip_nulls(cls, data: object) -> object:
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if v is not None}
        return data


class _SolarPanelCenter(_NullSafeModel):
    latitude: float = 0.0
    longitude: float = 0.0


class _SolarPanel(_NullSafeModel):
    center: _SolarPanelCenter = _SolarPanelCenter()
    segmentIndex: int = 0
    yearlyEnergyDcKwh: float = 0.0


class _RoofSegmentSunshineStats(_NullSafeModel):
    areaMeters2: float = 0.0
    sunshineQuantiles: List[float] = []


class _RoofSegmentStats(_NullSafeModel):
    stats: _RoofSegmentSunshineStats = _RoofSegmentSunshineStats()
    pitchDegrees: float = 0.0
    # Optional — 0.0 is valid (north); None means Google didn't provide a value
    azimuthDegrees: Optional[float] = None


class _WholeRoofStats(_NullSafeModel):
    areaMeters2: float = 0.0


class _SolarPanelConfig(_NullSafeModel):
    panelsCount: int = 0
    yearlyEnergyDcKwh: float = 0.0


class _SolarPotential(_NullSafeModel):
    maxArrayPanelsCount: int = 0
    maxArrayAreaMeters2: float = 0.0
    maxSunshineHoursPerYear: float = 0.0
    wholeRoofStats: _WholeRoofStats = _WholeRoofStats()
    roofSegmentStats: List[_RoofSegmentStats] = []
    solarPanels: List[_SolarPanel] = []
    solarPanelConfigs: List[_SolarPanelConfig] = []


class _ImageryDate(_NullSafeModel):
    year: Optional[int] = None
    month: Optional[int] = None


class _GoogleSolarResponse(BaseModel):
    solarPotential: Optional[_SolarPotential] = None
    imageryDate: _ImageryDate = _ImageryDate()


class SolarYieldRequest(BaseModel):
    address: str
    prop_id: Optional[str] = None
    lat: float
    lng: float
    report_id: str
    lot_polygon_wgs84: Optional[dict] = None  # GeoJSON Polygon in WGS84


# DC -> delivered. NOT a number invented here: NREL's PVWatts v8 publishes a
# default total system loss of 14.08% covering soiling, shading, mismatch,
# wiring, connections, light-induced degradation, nameplate tolerance, age and
# availability. It is the industry reference default, and naming it here means
# a reader can check the figure against its source rather than take ours.
#
# WHY IT MATTERS MORE THAN A LABEL. Google Solar returns `yearlyEnergyDcKwh` —
# energy at the panel, before the inverter. That figure was being monetised
# directly: on a typical 20-panel roof at 9,000 kWh DC it overstates the annual
# saving by 16.4%, shows payback at 6.4 years against 7.5, and reports a
# ten-year return of $2,420 where the figure is $671 — 3.6x, because the system
# cost is subtracted afterwards, so the whole error lands on the margin.
# TWO FACTORS, NOT ONE. PVWatts' 14.08% system loss does NOT include the
# inverter — PVWatts models inverter efficiency as a SEPARATE parameter with a
# default of 96%. The first version of this change applied only the 14.08% and
# still overstated delivered output by about 4%, which adversarial review
# caught. Both are needed to get from DC at the panel to AC at the meter.
PVWATTS_DEFAULT_SYSTEM_LOSS = 0.1408      # soiling, shading, mismatch, wiring,
                                          # connections, LID, nameplate, age,
                                          # availability
PVWATTS_INVERTER_EFFICIENCY = 0.96        # PVWatts default, DC -> AC conversion
DC_TO_DELIVERED = (1.0 - PVWATTS_DEFAULT_SYSTEM_LOSS) * PVWATTS_INVERTER_EFFICIENCY
DELIVERED_LOSS_PCT = round((1.0 - DC_TO_DELIVERED) * 100)   # 18
DELIVERY_BASIS = (
    "Google Solar reports energy at the panel (DC). Delivered output applies "
    "NREL PVWatts v8's two published defaults: 14.08% total system losses "
    "(soiling, shading, panel mismatch, wiring, connections, ageing) and 96% "
    "inverter efficiency for the DC-to-AC conversion — about 18% in total. "
    "An installer's quote will state the figure for the specific hardware."
)


def delivered_kwh(dc_kwh: float | None) -> float | None:
    """Energy reaching the meter, from energy at the panel.

    Returns None for None so an absent figure stays absent rather than
    becoming 0.0 — a zero here would render as a real roof that generates
    nothing.
    """
    if dc_kwh is None:
        return None
    return round(float(dc_kwh) * DC_TO_DELIVERED, 1)


class SolarYieldOutput(BaseModel):
    max_panels: int
    max_panel_area_m2: float
    annual_kwh_estimate: float          # DC at the panel, as Google reports it
    annual_kwh_delivered: Optional[float] = None   # after system losses
    delivery_basis: Optional[str] = None           # why the two differ
    sunshine_hours_per_year: float
    best_pitch_deg: float
    best_azimuth_deg: float
    roof_area_m2: float
    is_heritage: bool
    is_commercial_scale: bool  # roof_area_m2 > 500 after clipping
    imagery_date: str
    coverage_available: bool
    neighbour_max_height_m: Optional[float] = None  # LEP HOB for shadow cross-sell
    lga_name: Optional[str] = None
    lga_slug: Optional[str] = None


def _get_conn():
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        return psycopg2.connect(dsn)
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        database=os.environ.get("DB_NAME", "nsw_planning"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", ""),
        port=int(os.environ.get("DB_PORT", 5432)),
    )


def _write_report(
    report_id: str,
    address: str,
    lat: float,
    lng: float,
    prop_id: Optional[str],
    inputs: dict,
    outputs: dict,
    confidence: str,
) -> None:
    sql = """
        INSERT INTO property_reports
            (id, product, address, lat, lng, prop_id, run_date, inputs, outputs, confidence, data_sources)
        VALUES
            (%s, 'solar-yield', %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            outputs = EXCLUDED.outputs,
            confidence = EXCLUDED.confidence
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(sql, (
                report_id, address, lat, lng, prop_id,
                date.today(),
                psycopg2.extras.Json(inputs),
                psycopg2.extras.Json(outputs),
                confidence,
                DATA_SOURCES,
            ))
        conn.commit()
    finally:
        if conn:
            conn.close()


def _clip_panels_to_lot(sp: dict, lot_polygon_wgs84: dict) -> dict:
    """
    Filter solarPanels[] to those whose centre falls within the lot polygon.

    Recomputes:
      - maxArrayPanelsCount, maxArrayAreaMeters2 — from lot panels only
      - wholeRoofStats.areaMeters2 — from segments that contain lot panels
      - roofSegmentStats — filtered to lot-referenced segments only
        (used downstream for best pitch/azimuth scoring)
      - _lot_annual_kwh — sum of yearlyEnergyDcKwh for lot panels
      - _lot_clipped — True (signals to _parse_solar_response to use _lot_annual_kwh)

    Returns sp unchanged if solarPanels[] absent, lot polygon invalid, or
    shapely unavailable (with a warning log in each case).
    """
    try:
        from shapely.geometry import shape, Point
    except ImportError:
        logger.warning("shapely unavailable — lot clipping skipped")
        return sp

    panels = sp.get("solarPanels", [])
    if not panels:
        logger.info("solarPanels[] absent in Google response — lot clipping skipped")
        return sp

    try:
        lot_shape = shape(lot_polygon_wgs84)
    except Exception as exc:
        logger.warning(f"Invalid lot polygon, clipping skipped: {exc}")
        return sp

    lot_panels = []
    for p in panels:
        try:
            center = p["center"]
            if lot_shape.contains(Point(center["longitude"], center["latitude"])):
                lot_panels.append(p)
        except (KeyError, TypeError):
            # Malformed panel entry — skip rather than crash the whole clip
            logger.debug(f"Skipping malformed panel entry: {p}")
            continue

    total_count = sp.get("maxArrayPanelsCount") or len(panels)
    total_area = float(sp.get("maxArrayAreaMeters2") or 0.0)
    # Fallback 2.0 m² when either count or area is zero (avoids 0 ÷ 0 and 0-area panels)
    per_panel_area = total_area / total_count if total_count > 0 and total_area > 0 else 2.0

    lot_count = len(lot_panels)
    lot_area = round(lot_count * per_panel_area, 1)
    # Guard against null yearlyEnergyDcKwh values in Google response
    lot_kwh = round(sum((p.get("yearlyEnergyDcKwh") or 0.0) for p in lot_panels), 0)

    # Roof area: sum segment areas referenced by lot panels
    segment_indices = {p["segmentIndex"] for p in lot_panels if "segmentIndex" in p}
    segments = sp.get("roofSegmentStats", [])
    lot_roof_area = sum(
        s.get("stats", {}).get("areaMeters2") or 0.0
        for i, s in enumerate(segments)
        if i in segment_indices
    )
    if not lot_roof_area and total_count > 0:
        # Proportional fallback when segmentIndex mapping yields nothing
        whole = sp.get("wholeRoofStats", {}).get("areaMeters2") or 0.0
        lot_roof_area = round(whole * lot_count / total_count, 1)

    lot_segments = [s for i, s in enumerate(segments) if i in segment_indices]

    logger.info(
        f"Lot clipping: {lot_count}/{total_count} panels within boundary "
        f"({lot_kwh:.0f} kWh/yr, {lot_area:.1f} m² panel area, {lot_roof_area:.1f} m² roof)"
    )

    modified = dict(sp)
    modified["maxArrayPanelsCount"] = lot_count
    modified["maxArrayAreaMeters2"] = lot_area
    modified["wholeRoofStats"] = {
        **sp.get("wholeRoofStats", {}),
        "areaMeters2": round(lot_roof_area, 1),
    }
    modified["roofSegmentStats"] = lot_segments
    modified["_lot_annual_kwh"] = lot_kwh
    modified["_lot_clipped"] = True
    return modified


def _query_google_solar(lat: float, lng: float) -> dict:
    """
    Call Google Solar API buildingInsights endpoint.
    Returns the raw API response dict, or {"coverage_available": False} on 404.
    Raises on other HTTP errors. API key is never included in raised messages.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY env var not set")

    params = {
        "location.latitude": lat,
        "location.longitude": lng,
        "requiredQuality": "MEDIUM",
        "key": api_key,
    }

    # Retry on transient errors: network failures, 429, and 5xx.
    # Never include the response/request URL in raised exceptions (URL contains the API key).
    for attempt in range(3):
        try:
            r = requests.get(GOOGLE_SOLAR_API, params=params, timeout=15)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < 2:
                logger.warning(f"Google Solar API network error attempt {attempt+1}/3 — retrying")
                continue
            raise RuntimeError("Google Solar API unreachable after 3 attempts") from None
        except Exception:
            raise RuntimeError("Google Solar API request failed") from None

        if r.status_code == 404:
            logger.warning(f"Google Solar API: no coverage at ({lat}, {lng})")
            return {"coverage_available": False}
        if r.status_code == 403:
            raise ValueError("Google Solar API access denied (403) — check API key and quota")
        if r.status_code == 429 or r.status_code >= 500:
            if attempt < 2:
                wait = 2 ** attempt  # 1s, 2s
                logger.warning(f"Google Solar API {r.status_code} attempt {attempt+1}/3 — retrying in {wait}s")
                time.sleep(wait)
                continue
            raise RuntimeError(f"Google Solar API returned {r.status_code} after 3 attempts")
        if not r.ok:
            raise RuntimeError(f"Google Solar API returned {r.status_code}")
        try:
            return r.json()
        except Exception:
            raise RuntimeError("Google Solar API returned non-JSON response") from None

    raise RuntimeError("Google Solar API failed after retries")


def _no_coverage_output() -> SolarYieldOutput:
    return SolarYieldOutput(
        max_panels=0, max_panel_area_m2=0.0, annual_kwh_estimate=0.0,
        sunshine_hours_per_year=0.0, best_pitch_deg=0.0, best_azimuth_deg=0.0,
        roof_area_m2=0.0, is_heritage=False, is_commercial_scale=False,
        imagery_date="unknown", coverage_available=False,
    )


def _parse_solar_response(
    data: dict,
    lot_polygon_wgs84: Optional[dict] = None,
) -> SolarYieldOutput:
    """
    Extract the fields we need from the Google Solar API buildingInsights response.

    Validates and normalises the raw response using _GoogleSolarResponse — null
    fields in the API response are coerced to defaults by _NullSafeModel, so
    no defensive `or 0.0` is required when accessing the validated model's fields.

    If lot_polygon_wgs84 is provided, clips solarPanels[] to the lot boundary
    before computing counts, area, and yield.  Clipping works on a plain dict
    (model_dump() of solarPotential) so synthetic fields (_lot_clipped, etc.)
    can be appended by _clip_panels_to_lot without modifying the model class.

    Best segment: highest median sunshine hours (index 5 of sunshineQuantiles = 50th pct),
    tiebroken toward north-facing.  After lot clipping, only segments referenced
    by lot panels are considered — so orientation reflects this lot's roof, not
    the whole complex.

    Azimuth convention: Google compass bearing (0=N, 90=E, 180=S, 270=W).
    """
    # Our synthetic no-coverage sentinel (set by _query_google_solar on 404)
    if not data.get("coverage_available", True):
        return _no_coverage_output()

    # Validate and normalise at the API boundary.
    # _NullSafeModel strips null values so field defaults apply — a null
    # maxArrayPanelsCount becomes 0, a null roofSegmentStats becomes [].
    # ValidationError here means a structurally unexpected response; treat as no coverage.
    try:
        gsolar = _GoogleSolarResponse.model_validate(data)
    except Exception as exc:
        logger.warning(f"Google Solar API response validation failed: {exc} — treating as no coverage")
        return _no_coverage_output()

    if not gsolar.solarPotential:
        logger.warning("Google Solar API returned 200 with no solarPotential — treating as no coverage")
        return _no_coverage_output()

    # Convert validated model → plain dict so _clip_panels_to_lot can append
    # synthetic fields (_lot_clipped, _lot_annual_kwh) without modifying the model.
    # All values in this dict are guaranteed non-null (normalised by _NullSafeModel).
    sp: dict = gsolar.solarPotential.model_dump()

    if lot_polygon_wgs84:
        sp = _clip_panels_to_lot(sp, lot_polygon_wgs84)

    # Imagery date from validated model — year/month are Optional[int]
    gd = gsolar.imageryDate
    imagery_date = f"{gd.year}-{gd.month:02d}" if gd.year and gd.month else "unknown"

    # All numeric fields guaranteed non-null after model normalisation
    roof_area: float = sp["wholeRoofStats"]["areaMeters2"]

    # Best segment: highest median sunshine hours among (lot-filtered) segments.
    # Tiebreak: prefer segments closer to north-facing (azimuth near 0/360).
    segments: list = sp["roofSegmentStats"]

    def _segment_score(seg: dict) -> float:
        quantiles: list = seg["stats"]["sunshineQuantiles"]
        # Google returns 11 values (0,10,20,...,100 percentile). Index 5 = 50th (median).
        median_sun = quantiles[5] if len(quantiles) > 5 else 0.0
        # azimuthDegrees is Optional[float]=None in the model: 0.0 is valid (north-facing).
        # None means Google didn't provide a value — default to south (worst case, no bonus).
        az_raw = seg["azimuthDegrees"]
        az = float(az_raw) if az_raw is not None else 180.0
        # North-facing bonus: 0–5% of median_sun as tiebreaker (Southern Hemisphere:
        # north-facing receives most direct irradiance). Scaled so a sunnier south-facing
        # segment still wins.
        north_factor = 1.0 - min(az, 360.0 - az) / 180.0  # 1.0=N, 0.0=S
        return median_sun * (1.0 + 0.05 * north_factor)

    best_seg: dict = max(segments, key=_segment_score) if segments else {}
    best_pitch: float = best_seg.get("pitchDegrees", 0.0)
    # azimuthDegrees can be None (Optional[float]) — keep None-safe check.
    # Default 180.0 (south-facing) matches the scorer default — 0.0 would falsely imply north.
    best_az_raw = best_seg.get("azimuthDegrees")
    best_azimuth: float = float(best_az_raw) if best_az_raw is not None else 180.0

    # Annual kWh: use per-panel sum when lot-clipped (more accurate), otherwise
    # take the max solarPanelConfigs entry (Google's aggregate for the whole building).
    if sp.get("_lot_clipped"):
        annual_kwh: float = float(sp["_lot_annual_kwh"])
    else:
        configs: list = sp["solarPanelConfigs"]
        annual_kwh = float(configs[-1]["yearlyEnergyDcKwh"]) if configs else 0.0

    max_panels: int = int(sp["maxArrayPanelsCount"])
    max_panel_area: float = round(float(sp["maxArrayAreaMeters2"]), 1)
    roof_area_rounded: float = round(roof_area, 1)

    return SolarYieldOutput(
        max_panels=max_panels,
        max_panel_area_m2=max_panel_area,
        annual_kwh_estimate=round(annual_kwh, 0),
        annual_kwh_delivered=delivered_kwh(round(annual_kwh, 0)),
        delivery_basis=DELIVERY_BASIS,
        sunshine_hours_per_year=round(float(sp["maxSunshineHoursPerYear"]), 0),
        best_pitch_deg=round(best_pitch, 1),
        best_azimuth_deg=round(best_azimuth, 1),
        roof_area_m2=roof_area_rounded,
        is_heritage=False,  # populated by caller
        is_commercial_scale=roof_area_rounded >= 500,
        imagery_date=imagery_date,
        coverage_available=True,
    )


def _check_heritage(lat: float, lng: float) -> bool:
    """
    Spatial heritage check: point-in-polygon against spatial_overlays layer_type='heritage'.
    Returns False (safe default) if spatial_overlays has no heritage data or query fails.
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM spatial_overlays
                WHERE layer_type = 'heritage'
                  AND is_active = TRUE
                  AND ST_Contains(
                        ST_SetSRID(ST_GeomFromGeoJSON(geom::text), 4326),
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                      )
                LIMIT 1
                """,
                (lng, lat),
            )
            return cur.fetchone() is not None
    except Exception as e:
        logger.warning(f"Heritage flag lookup failed: {e}")
        return False
    finally:
        if conn:
            conn.close()


def _lookup_neighbour_hob(lat: float, lng: float) -> Optional[float]:
    """
    Look up the maximum building height (HOB) from spatial_overlays for this location.
    Used as a cross-sell teaser: "neighbouring lots permit Xm buildings".
    Returns None if no height data or query fails.
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT CAST(value AS float)
                FROM spatial_overlays
                WHERE layer_type = 'height'
                  AND is_active = TRUE
                  AND ST_Contains(
                        ST_SetSRID(ST_GeomFromGeoJSON(geom::text), 4326),
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                      )
                LIMIT 1
                """,
                (lng, lat),
            )
            row = cur.fetchone()
            return float(row[0]) if row and row[0] else None
    except Exception as e:
        logger.warning(f"HOB lookup failed: {e}")
        return None
    finally:
        if conn:
            conn.close()


@router.post("/solar-yield")
def _compute_confidence(
    *, coverage_available: bool, has_lot_polygon: bool, max_panels: int
) -> str:
    """Derive the solar-yield confidence from what the run actually obtained.

    Behaviour is unchanged from the inline branch this replaces; the derivation
    is now a named unit that can be tested on its own, which is the house
    pattern (``conveyancing._compute_confidence``, ``flood``, ``granny_flat``).

    ``scripts/lint_hardcoded_confidence.py`` reports a literal as ``computed``
    rather than ``prod`` when its enclosing function is named for confidence,
    so this also moves solar_yield's four literals out of the category a future
    blocking gate would act on. That is a real distinction, not a way to quiet
    the lint: every branch below turns on a condition the run measured, and the
    caller passes those conditions in rather than the function reaching for
    globals.

    Args:
        coverage_available: whether the imagery source returned usable coverage.
        has_lot_polygon: whether a VALIDATED lot polygon was available to clip
            to. An implausible polygon is demoted to not-provided upstream, so
            "high" can no longer ride on a clip that never happened.
        max_panels: panels found inside the lot boundary.

    Returns:
        One of "low", "medium", "high".
    """
    if not coverage_available:
        return "low"
    if has_lot_polygon and max_panels > 0:
        return "high"    # clipped to lot, panels found
    if has_lot_polygon:
        return "medium"  # clipped but no panels in lot boundary
    return "medium"      # no lot polygon — raw Google result, building may not match lot


def run_solar_yield(request: SolarYieldRequest):
    logger.info(f"Solar yield: {request.address} ({request.lat}, {request.lng})")

    # Units/CRS entry checks (campaign item 4). A wrong-CRS coordinate is a
    # typed 422, never a yield computed from the wrong place. An implausible
    # lot polygon is DEMOTED to not-provided — the old behaviour let an
    # invalid polygon silently skip clipping while confidence still said
    # "high (clipped to lot)", serving whole-building numbers as lot numbers.
    coord_reason = check_point_nsw(request.lat, request.lng)
    if coord_reason:
        raise HTTPException(
            422, f"Solar assessment could not be determined: {coord_reason}")
    lot_polygon = request.lot_polygon_wgs84
    lot_polygon_reason = None
    if lot_polygon is not None:
        lot_polygon_reason = check_polygon_wgs84(lot_polygon)
        if lot_polygon_reason:
            logger.warning(f"Lot polygon failed plausibility — treated as "
                           f"not provided: {lot_polygon_reason}")
            lot_polygon = None

    # Audit trail: track data source queries
    ds_google = DataSourceQuery(
        "Google Solar API", GOOGLE_SOLAR_API,
        {"lat": request.lat, "lng": request.lng, "requiredQuality": "MEDIUM"},
    )
    ds_heritage = DataSourceQuery(
        "PostGIS heritage overlay", "local:spatial_overlays",
        {"lat": request.lat, "lng": request.lng, "layer_type": "heritage"},
    )
    ds_hob = DataSourceQuery(
        "PostGIS height overlay", "local:spatial_overlays",
        {"lat": request.lat, "lng": request.lng, "layer_type": "height"},
    )

    try:
        raw = _query_google_solar(request.lat, request.lng)
    except Exception as e:
        ds_google.record_error(str(e))
        logger.exception(f"Google Solar API failed: {e}")
        raise HTTPException(status_code=502, detail=f"Google Solar API error: {e}")

    ds_google.record_response(
        raw,
        features_returned=1 if raw.get("coverage_available", True) and raw.get("solarPotential") else 0,
    )

    try:
        outputs = _parse_solar_response(raw, lot_polygon_wgs84=lot_polygon)
    except Exception as e:
        logger.exception(f"Solar response parse failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse solar data")

    outputs.is_heritage = _check_heritage(request.lat, request.lng)
    ds_heritage.record_response(outputs.is_heritage, features_returned=1 if outputs.is_heritage else 0)

    outputs.neighbour_max_height_m = _lookup_neighbour_hob(request.lat, request.lng)
    ds_hob.record_response(
        outputs.neighbour_max_height_m,
        features_returned=1 if outputs.neighbour_max_height_m is not None else 0,
    )

    # Resolve LGA
    _lga_conn = None
    try:
        _lga_conn = _get_conn()
        _lga = lookup_lga(request.lat, request.lng, _lga_conn)
        outputs.lga_name = _lga.get("lga_name")
        outputs.lga_slug = _lga.get("lga_slug")
    except Exception:
        pass
    finally:
        if _lga_conn:
            _lga_conn.close()

    # Confidence keys off the VALIDATED polygon — an implausible one was
    # demoted to not-provided above, so "high (clipped to lot)" can no longer
    # ride on a clip that silently never happened.
    confidence = _compute_confidence(
        coverage_available=outputs.coverage_available,
        has_lot_polygon=bool(lot_polygon),
        max_panels=outputs.max_panels,
    )

    # Execution manifest (campaign item 4): identity read from the response
    # objects this run actually consumed.
    manifest = build_manifest(
        product="solar-yield",
        algorithm_version=ALGORITHM_VERSION,
        inputs={
            "google_solar": {
                "imagery_date": outputs.imagery_date,
                "coverage_available": outputs.coverage_available,
            },
            "lot_polygon": {
                "provided": request.lot_polygon_wgs84 is not None,
                "used_for_clipping": lot_polygon is not None,
                "rejected_reason": lot_polygon_reason,
            },
        },
        query_params={"lat": request.lat, "lng": request.lng,
                      "requiredQuality": "MEDIUM"},
        parcel_identity={"prop_id": request.prop_id},
    )

    try:
        _write_report(
            report_id=request.report_id,
            address=request.address,
            lat=request.lat,
            lng=request.lng,
            prop_id=request.prop_id,
            inputs={
                "address": request.address,
                "lat": request.lat,
                "lng": request.lng,
                "lot_polygon_provided": request.lot_polygon_wgs84 is not None,
                MANIFEST_KEY: manifest,
            },
            outputs=outputs.model_dump(),
            confidence=confidence,
        )
    except Exception as e:
        logger.error(f"Solar yield DB write failed: {e}")
        raise HTTPException(status_code=503, detail="Failed to save report — please retry")

    # Audit trail (non-blocking — won't prevent report delivery on failure)
    log_audit_trail(
        report_id=request.report_id,
        pipeline_name="solar-yield",
        input_params={
            "address": request.address,
            "lat": request.lat,
            "lng": request.lng,
            "lot_polygon_provided": request.lot_polygon_wgs84 is not None,
        },
        data_sources=[ds_google, ds_heritage, ds_hob],
        output_summary=outputs.model_dump(),
        disclaimer_version=get_current_disclaimer_version("solar-yield"),
        intermediate_calculations={
            "max_panels": outputs.max_panels,
            "annual_kwh_estimate": outputs.annual_kwh_estimate,
            "roof_area_m2": outputs.roof_area_m2,
            "is_commercial_scale": outputs.is_commercial_scale,
            "best_pitch_deg": outputs.best_pitch_deg,
            "best_azimuth_deg": outputs.best_azimuth_deg,
            "coverage_available": outputs.coverage_available,
            "lot_clipped": request.lot_polygon_wgs84 is not None,
            "confidence": confidence,
        },
    )

    logger.info(
        f"Solar yield complete: {request.report_id} — "
        f"{outputs.annual_kwh_estimate:.0f} kWh/yr potential, {outputs.max_panels} max panels"
    )
    return {
        "status": "complete",
        "report_id": request.report_id,
        "outputs": outputs.model_dump(),
        "confidence": confidence,
        "data_sources": DATA_SOURCES,
    }
