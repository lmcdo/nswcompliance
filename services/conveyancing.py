"""
Conveyancing Planning Disclosure — FastAPI router.

POST /pipeline/conveyancing        -- on-demand: LEP controls, overlays, feasibility
POST /pipeline/conveyancing/pdf    -- generate full PDF report (paid tier)

Data sources:
  NSW Planning Portal layerintersect    (zone, height, FSR, lot size, heritage, SEPP overlays)
  NSW Valuation Service                 (lot area, land value, 5-year history)
  PostGIS spatial_overlays              (biodiversity, riparian, wetlands, landslide, flood, bushfire, ANEF)
  NSW ePlanning DA API                  (nearby DAs within 200m)
  PlotDetect compliance DB              (DCP setbacks, LEP clauses, heritage)
  Shadow risk model                     (geometric shadow from LEP height envelope)

Response contract (free tier — /pipeline/conveyancing):
{
  "address": str,
  "lat": float,
  "lng": float,
  "prop_id": int | null,
  "run_date": str,
  "outputs": {
    "zone": str | null,
    "zone_full": str | null,
    "zone_epi": str | null,
    "legislation_url": str | null,
    "height": str | null,
    "fsr": str | null,
    "lot_size": str | null,
    "ass_class": str | null,
    "heritage_items": list[str],
    "heritage_hca": list[str],
    "sepp_overlays": list[dict],
    "housing_sepp": bool,
    "tod_area": bool,
    "flood_epi": bool,
    "riparian_epi": bool,
    "unique_overlays": list[dict],
    "covered_layers": list[str],
    "strata_info": dict,
    "valuation": dict,
    "headroom": dict,
    "feasibility": list[dict],
    "da_count": int,
    "dcp_available": bool
  },
  "confidence": str,
  "data_sources": list[str]
}
"""
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Import from the conveyancing script — path setup for both Docker and local
_project_root = Path(__file__).parent.parent
_scripts_dir = _project_root / "scripts"
sys.path.insert(0, str(_scripts_dir))
sys.path.insert(0, str(_project_root))

from generate_conveyancing_report import (  # noqa: E402
    resolve_address,
    get_raw_controls,
    parse_controls,
    get_valuation,
    get_unique_overlays,
    calc_feasibility,
    calc_development_headroom,
    detect_strata,
    detect_former_council,
    get_shadow_risk,
    _council_from_zone_epi,
)
from conveyancing_db import (  # noqa: E402
    fetch_dcp_setbacks,
    fetch_heritage_postgis,
    fetch_lep_clauses,
    fetch_nearby_das,
    fetch_sepp_housing_standards,
    fetch_tax_thresholds,
)

router = APIRouter(prefix="/pipeline", tags=["satellite"])

_DATA_SOURCES = [
    "NSW Planning Portal",
    "NSW Valuation Service",
    "PostGIS spatial overlays (ePlanning MapServer)",
    "NSW ePlanning DA API",
]


def _load_regulatory_configs() -> tuple[Optional[dict], Optional[dict]]:
    """Load SEPP Housing + tax thresholds from DB for calc_feasibility.

    Returns (sepp_standards, tax_config) — both None if DB unavailable.
    """
    import psycopg2
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.warning("Regulatory configs: DATABASE_URL not set, using fallback values for SEPP + tax")
        return None, None
    conn = None
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        # SEPP secondary dwelling standards
        sd_rows = fetch_sepp_housing_standards(conn, development_type="secondary_dwelling")
        sepp_standards = None
        if sd_rows:
            sd_by_type = {r["standard_type"]: r for r in sd_rows}
            min_lot_row = sd_by_type.get("min_lot_size")
            sepp_standards = {
                "sd_min_lot": min_lot_row["numeric_value"] if min_lot_row else 450,
                "sd_zones": set(min_lot_row["applicable_zones"]) if min_lot_row else {"R1", "R2", "R3", "R4"},
            }
        else:
            logger.warning("Regulatory configs: no secondary_dwelling rows in housing_sepp_standards — using fallback")
        # Tax thresholds
        tax_config = fetch_tax_thresholds(conn)
        if tax_config is None:
            logger.warning("Regulatory configs: no tax_thresholds row for current year — using fallback")
        return sepp_standards, tax_config
    except Exception as e:
        logger.warning(f"Failed to load regulatory configs from DB: {e}")
        return None, None
    finally:
        if conn:
            conn.close()


class ConveyancingRequest(BaseModel):
    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    prop_id: Optional[str] = None
    report_id: Optional[str] = None


class ConveyancingPdfRequest(BaseModel):
    address: str
    lat: float
    lng: float
    prop_id: Optional[str] = None
    report_id: str


@router.post("/conveyancing")
def run_conveyancing(req: ConveyancingRequest):
    """
    On-demand conveyancing disclosure analysis.
    Returns structured data for the free tier frontend display.
    PDF generation is a separate paid endpoint.
    """
    # Resolve address if lat/lng not provided
    resolved_prop_id = None
    lot_wkt = None

    if req.lat and req.lng and req.prop_id:
        lat, lng = req.lat, req.lng
        resolved_prop_id = int(req.prop_id)
    else:
        try:
            resolved_prop_id, lat, lng, lot_wkt = resolve_address(req.address)
        except Exception as e:
            logger.error(f"Address resolution failed: {e}")
            raise HTTPException(status_code=422, detail=f"Could not resolve address: {req.address}")

        if not lat or not lng:
            raise HTTPException(status_code=422, detail=f"Could not determine coordinates for: {req.address}")

    # Fetch controls and valuation in parallel
    controls = {}
    valuation = {"lot_area_m2": None, "land_value": None, "val_base_date": None, "val_history": []}

    if resolved_prop_id:
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_controls = pool.submit(lambda: parse_controls(get_raw_controls(resolved_prop_id)))
            f_valuation = pool.submit(get_valuation, resolved_prop_id)
            controls = f_controls.result(timeout=50)
            valuation = f_valuation.result(timeout=50)
    else:
        controls = parse_controls([])

    # Parallel: overlays, strata detection
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_overlays = pool.submit(get_unique_overlays, lat, lng, lot_wkt)
        f_strata = pool.submit(detect_strata, req.address, lat, lng)
        unique_overlays, covered_layers, proximity_m = f_overlays.result(timeout=50)
        strata_info = f_strata.result(timeout=50)

    # PostGIS fallbacks — use spatial data when Planning Portal returned nothing
    ov_by_type = {o["layer_type"]: o for o in unique_overlays}
    if not controls.get("ass_class") and "acid_sulfate" in ov_by_type:
        controls["ass_class"] = ov_by_type["acid_sulfate"].get("value") or "Present"
    if not controls.get("lot_size") and "lot_size" in ov_by_type:
        controls["lot_size"] = ov_by_type["lot_size"].get("value")
        controls["lot_size_units"] = "m\u00b2"

    # Calculate derived data
    headroom = calc_development_headroom(controls, valuation)
    sepp_standards, tax_config = _load_regulatory_configs()
    feasibility = calc_feasibility(
        controls, valuation, unique_overlays,
        is_strata=strata_info["is_strata"],
        sepp_standards=sepp_standards,
        tax_config=tax_config,
    )

    # DA count (quick — no full details in free tier)
    zone_epi = controls.get("zone_epi", "")
    council_name = _council_from_zone_epi(zone_epi)
    da_count = 0
    if council_name:
        try:
            das = get_nearby_das(lat, lng, council_name=council_name)
            da_count = len(das)
        except Exception as e:
            logger.warning(f"DA fetch failed: {e}")

    # Check DCP availability
    dcp_former_council = detect_former_council(req.address, zone_epi)

    data_sources = list(_DATA_SOURCES)
    if dcp_former_council:
        data_sources.append("PlotDetect DCP controls database")

    # Cache pipeline results so the PDF endpoint can reuse them
    if req.report_id:
        _save_pipeline_cache(req.report_id, {
            "address": req.address,
            "lat": lat,
            "lng": lng,
            "prop_id": resolved_prop_id,
            "lot_wkt": lot_wkt,
            "controls": controls,
            "valuation": valuation,
            "unique_overlays": unique_overlays,
            "covered_layers": list(covered_layers),
            "proximity_m": proximity_m,
            "strata_info": strata_info,
            "headroom": headroom,
            "feasibility": feasibility,
            "dcp_former_council": dcp_former_council,
            "council_name": council_name,
        })

    return {
        "address": req.address,
        "lat": lat,
        "lng": lng,
        "prop_id": resolved_prop_id,
        "run_date": date.today().isoformat(),
        "outputs": {
            # LEP controls
            "zone": controls.get("zone"),
            "zone_full": controls.get("zone_full"),
            "zone_epi": controls.get("zone_epi"),
            "legislation_url": controls.get("legislation_url"),
            "height": controls.get("height"),
            "height_units": controls.get("height_units", "m"),
            "fsr": controls.get("fsr"),
            "lot_size": controls.get("lot_size"),
            "lot_size_units": controls.get("lot_size_units", "m\u00b2"),
            "ass_class": controls.get("ass_class"),
            "heritage_items": controls.get("heritage_items", []),
            "heritage_hca": controls.get("heritage_hca", []),
            "sepp_overlays": controls.get("sepp_overlays", []),
            "housing_sepp": controls.get("housing_sepp", False),
            "tod_area": controls.get("tod_area", False),
            "flood_epi": controls.get("flood_epi", False),
            "riparian_epi": controls.get("riparian_epi", False),
            # Spatial overlays
            "unique_overlays": unique_overlays,
            "covered_layers": list(covered_layers),
            # Strata
            "strata_info": strata_info,
            # Valuation
            "valuation": {
                "lot_area_m2": valuation.get("lot_area_m2"),
                "land_value": valuation.get("land_value"),
                "val_base_date": valuation.get("val_base_date"),
            },
            # Derived
            "headroom": headroom,
            "feasibility": feasibility,
            # Summary counts
            "da_count": da_count,
            "dcp_available": bool(dcp_former_council),
        },
        "confidence": _compute_confidence(controls, unique_overlays, valuation),
        "data_sources": data_sources,
    }


@router.post("/conveyancing/pdf")
def generate_conveyancing_pdf(req: ConveyancingPdfRequest):
    """
    Generate the full conveyancing PDF report (paid tier).
    Loads cached free-tier pipeline results when available, then fetches
    PDF-exclusive extras (DAs, DCP setbacks, LEP clauses, heritage, shadow).
    Falls back to a full pipeline run if cache is missing.
    """
    import psycopg2
    import re
    import tempfile
    from generate_conveyancing_report import generate_pdf

    cached = _load_pipeline_cache(req.report_id)

    if cached:
        # ---------- cache hit: unpack free-tier results ----------
        resolved_prop_id = cached.get("prop_id")
        if resolved_prop_id is not None:
            resolved_prop_id = int(resolved_prop_id)
        lot_wkt = cached.get("lot_wkt")
        controls = cached.get("controls") or {}
        valuation = cached.get("valuation") or {}
        unique_overlays = cached.get("unique_overlays") or []
        covered_layers = cached.get("covered_layers") or []
        proximity_m = cached.get("proximity_m")
        strata_info = cached.get("strata_info") or {"is_strata": False}
        headroom = cached.get("headroom") or {}
        feasibility = cached.get("feasibility") or []
        dcp_former_council = cached.get("dcp_former_council")
        council_name = cached.get("council_name")
    else:
        # ---------- cache miss: full pipeline re-run ----------
        logger.info(f"Cache miss for {req.report_id} — running full pipeline")
        resolved_prop_id = int(req.prop_id) if req.prop_id else None
        lot_wkt = None

        if not resolved_prop_id:
            resolved_prop_id, _, _, lot_wkt = resolve_address(req.address)

        controls = {}
        valuation = {"lot_area_m2": None, "land_value": None, "val_base_date": None, "val_history": []}
        if resolved_prop_id:
            controls = parse_controls(get_raw_controls(resolved_prop_id))
            valuation = get_valuation(resolved_prop_id)

        unique_overlays, covered_layers, proximity_m = get_unique_overlays(req.lat, req.lng, lot_wkt)
        strata_info = detect_strata(req.address, req.lat, req.lng)

        # PostGIS fallbacks
        ov_by_type = {o["layer_type"]: o for o in unique_overlays}
        if not controls.get("ass_class") and "acid_sulfate" in ov_by_type:
            controls["ass_class"] = ov_by_type["acid_sulfate"].get("value") or "Present"
        if not controls.get("lot_size") and "lot_size" in ov_by_type:
            controls["lot_size"] = ov_by_type["lot_size"].get("value")
            controls["lot_size_units"] = "m\u00b2"

        headroom = calc_development_headroom(controls, valuation)
        sepp_standards, tax_config = _load_regulatory_configs()
        feasibility = calc_feasibility(
            controls, valuation, unique_overlays,
            is_strata=strata_info["is_strata"],
            sepp_standards=sepp_standards,
            tax_config=tax_config,
        )

        zone_epi = controls.get("zone_epi") or ""
        council_name = _council_from_zone_epi(zone_epi)
        dcp_former_council = detect_former_council(req.address, zone_epi)

    # ---------- PDF-exclusive data (parallelised) ----------
    # DAs, shadow, and DB queries are independent — run concurrently.
    das = []
    lep_clauses = []
    dcp_setbacks_db = None
    postgis_heritage = {"hca": [], "items": [], "has_heritage": False, "raw": []}
    shadow_result = None
    db_url = os.getenv("DATABASE_URL")

    def _fetch_db_data():
        """DB queries: DAs (local), LEP clauses, DCP setbacks, heritage."""
        _das = []
        _lep = []
        _dcp = None
        _heritage = {"hca": [], "items": [], "has_heritage": False, "raw": []}
        if not db_url:
            return _das, _lep, _dcp, _heritage
        conn = None
        try:
            conn = psycopg2.connect(db_url)
            conn.autocommit = True
            # Nearby DAs from local DB (replaces live ePlanning API)
            _das = fetch_nearby_das(conn, req.lat, req.lng, council_name=council_name)
            key_sites_clause = controls.get("key_sites_clause")
            epi_name = controls.get("zone_epi", "")
            prop_zone = controls.get("zone", "")
            if key_sites_clause:
                _lep = fetch_lep_clauses(conn, key_sites_clause, epi_name)
            if dcp_former_council:
                _dcp = fetch_dcp_setbacks(conn, dcp_former_council, prop_zone)
            _heritage = fetch_heritage_postgis(conn, req.lat, req.lng, lot_wkt=lot_wkt)
        except Exception as e:
            logger.warning("DB pre-fetch failed: %s", e)
        finally:
            if conn:
                conn.close()
        return _das, _lep, _dcp, _heritage

    def _fetch_shadow():
        """Shadow risk — calls Railway geometric model (~17s)."""
        if not resolved_prop_id:
            return None
        lep_height = None
        raw_h = controls.get("height")
        if raw_h:
            m = re.search(r"(\d+(?:\.\d+)?)", str(raw_h))
            if m:
                lep_height = float(m.group(1))
        return get_shadow_risk(req.address, str(resolved_prop_id), req.lat, req.lng, height_m=lep_height)

    with ThreadPoolExecutor(max_workers=2) as executor:
        db_future = executor.submit(_fetch_db_data)
        shadow_future = executor.submit(_fetch_shadow)
        das, lep_clauses, dcp_setbacks_db, postgis_heritage = db_future.result()
        shadow_result = shadow_future.result()

    # Merge PostGIS heritage
    if postgis_heritage["hca"]:
        if controls.get("heritage_items") and not controls.get("heritage_hca"):
            controls["heritage_hca"] = controls["heritage_items"][:]
        elif not controls.get("heritage_hca"):
            controls.setdefault("heritage_items", []).extend(postgis_heritage["hca"])
            controls["heritage_hca"] = postgis_heritage["hca"][:]
    elif postgis_heritage["items"] and not controls.get("heritage_items"):
        controls["heritage_items"] = postgis_heritage["items"][:]

    # Generate PDF
    pdf_path = os.path.join(tempfile.gettempdir(), f"conveyancing_{req.report_id}.pdf")
    generate_pdf(
        pdf_path, req.address, req.lat, req.lng, controls, valuation,
        headroom, feasibility, unique_overlays, das,
        dcp_former_council=dcp_former_council,
        strata_info=strata_info,
        covered_layers=covered_layers,
        shadow_result=shadow_result,
        lep_clauses=lep_clauses,
        dcp_setbacks_db=dcp_setbacks_db,
        proximity_m=proximity_m,
    )

    # Upload to R2
    pdf_url = _upload_to_r2(pdf_path, req.report_id)
    if not pdf_url:
        raise HTTPException(status_code=503, detail="PDF upload failed")

    return {
        "report_id": req.report_id,
        "pdf_url": pdf_url,
        "address": req.address,
    }


def _upload_to_r2(pdf_path: str, report_id: str) -> Optional[str]:
    """Upload PDF to Cloudflare R2 and return public URL."""
    try:
        import boto3
        r2_account = os.getenv("R2_ACCOUNT_ID", "")
        r2_access = os.getenv("R2_ACCESS_KEY_ID")
        r2_secret = os.getenv("R2_SECRET_ACCESS_KEY")
        r2_bucket = os.getenv("R2_BUCKET_NAME") or os.getenv("R2_BUCKET", "plotdetect-reports")
        r2_public = os.getenv("R2_PUBLIC_URL", "https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev")
        r2_endpoint = os.getenv("R2_ENDPOINT") or (f"https://{r2_account}.r2.cloudflarestorage.com" if r2_account else "")

        if not all([r2_endpoint, r2_access, r2_secret]):
            logger.warning("R2 credentials not configured — returning local path")
            return None

        s3 = boto3.client(
            "s3",
            endpoint_url=r2_endpoint,
            aws_access_key_id=r2_access,
            aws_secret_access_key=r2_secret,
        )
        key = f"conveyancing/{report_id}.pdf"
        s3.upload_file(
            pdf_path, r2_bucket, key,
            ExtraArgs={"ContentType": "application/pdf"},
        )
        return f"{r2_public}/{key}" if r2_public else key
    except Exception as e:
        logger.error(f"R2 upload failed: {e}")
        return None


def _save_pipeline_cache(report_id: str, data: dict) -> None:
    """Save free-tier pipeline results so the PDF endpoint can skip re-fetching."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url or not report_id:
        return
    import psycopg2
    conn = None
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO conveyancing_cache (report_id, pipeline_data, created_at)
                   VALUES (%s, %s, NOW())
                   ON CONFLICT (report_id)
                   DO UPDATE SET pipeline_data = EXCLUDED.pipeline_data,
                                 created_at = NOW()""",
                (report_id, json.dumps(data, default=str)),
            )
    except Exception as e:
        logger.warning(f"Failed to save pipeline cache: {e}")
    finally:
        if conn:
            conn.close()


def _load_pipeline_cache(report_id: str) -> Optional[dict]:
    """Load cached free-tier pipeline results. Returns None on miss or error."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url or not report_id:
        return None
    import psycopg2
    conn = None
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pipeline_data FROM conveyancing_cache WHERE report_id = %s",
                (report_id,),
            )
            row = cur.fetchone()
        if row and row[0]:
            return row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return None
    except Exception as e:
        logger.warning(f"Failed to load pipeline cache: {e}")
        return None
    finally:
        if conn:
            conn.close()


def _compute_confidence(controls: dict, overlays: list, valuation: dict) -> str:
    """Rate confidence based on data completeness."""
    score = 0
    if controls.get("zone"):
        score += 2
    if controls.get("height"):
        score += 1
    if controls.get("fsr"):
        score += 1
    if valuation.get("lot_area_m2"):
        score += 2
    if overlays:
        score += 1
    if score >= 5:
        return "high"
    if score >= 3:
        return "medium"
    return "low"
