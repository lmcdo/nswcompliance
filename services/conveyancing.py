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
    load_regulatory_configs,
)
from lga_lookup import lookup_lga  # noqa: E402

router = APIRouter(prefix="/pipeline", tags=["satellite"])


def _validate_former_council_postgis(
    text_slug: Optional[str],
    lat: float,
    lng: float,
    address: str,
    zone_epi: str,
) -> Optional[str]:
    """Cross-validate text-based former council against PostGIS LGA geometry.

    For Inner West boundary suburbs (Stanmore, Newtown, Camperdown, St Peters,
    Alexandria, Erskineville, Glebe) the text-based detect_former_council
    cannot determine which side of the LGA boundary the property falls on.
    This function uses the spatial_overlays height layer to confirm the LGA.

    Returns:
        Validated lga_slug, or None if the property is not in the expected LGA.
    """
    import psycopg2

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return text_slug  # can't validate — trust text match

    conn = None
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        lga_result = lookup_lga(lat, lng, conn, address=address)
    except Exception as e:
        logger.warning("PostGIS LGA validation failed: %s — falling back to text match", e)
        return text_slug
    finally:
        if conn:
            conn.close()

    postgis_lga = (lga_result.get("lga_name") or "").lower()

    # If PostGIS says this is NOT Inner West, the text match was wrong
    # (e.g. Glebe resolving to marrickville when it's actually City of Sydney)
    if text_slug and text_slug in ("marrickville", "leichhardt", "ashfield"):
        if postgis_lga and postgis_lga != "inner west":
            logger.info(
                "PostGIS overrode text match: %s is in '%s', not Inner West (text said '%s')",
                address, postgis_lga, text_slug,
            )
            return None  # not Inner West — no DCP setback data for this LGA

    # If text match returned None but PostGIS says Inner West, resolve via PostGIS
    if text_slug is None and postgis_lga == "inner west":
        postgis_slug = lga_result.get("lga_slug")
        if postgis_slug and postgis_slug not in ("inner_west",):
            # lookup_lga already did suburb disambiguation
            logger.info(
                "PostGIS resolved unmapped IW suburb: %s → %s", address, postgis_slug,
            )
            return postgis_slug

    return text_slug


_DATA_SOURCES = [
    "NSW Planning Portal",
    "NSW Valuation Service",
    "PostGIS spatial overlays (ePlanning MapServer)",
    "NSW ePlanning DA API",
]


def _load_regulatory_configs() -> tuple[Optional[dict], Optional[dict]]:
    """Load SEPP Housing + tax thresholds from DB for calc_feasibility.

    Returns (sepp_standards, tax_config) — both None if DB unavailable.
    Implementation moved to conveyancing_db.load_regulatory_configs so the CLI
    report path injects the same configs (a None tax_config renders "Not
    assessed", never hardcoded figures).
    """
    return load_regulatory_configs(os.getenv("DATABASE_URL"))


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
            import psycopg2
            _db_url = os.getenv("DATABASE_URL")
            if _db_url:
                _conn = psycopg2.connect(_db_url)
                _conn.autocommit = True
                try:
                    # council_name=None: the 200m Haversine radius filter in
                    # fetch_nearby_das already scopes the search precisely. The
                    # council filter is redundant AND buggy — the DB stores a
                    # different council-name vocabulary than the LEP-derived name
                    # (e.g. "The Council of the Shire of Hornsby" vs "Hornsby
                    # Shire Council"), so filtering silently returned zero and
                    # printed a false "no DAs nearby". Matches intelligence_brief
                    # _fetch_nearby_das, which passes None for the same reason.
                    das = fetch_nearby_das(_conn, lat, lng, council_name=None)
                    da_count = len(das)
                finally:
                    _conn.close()
        except Exception as e:
            logger.warning(f"DA fetch failed: {e}")

    # Check DCP availability — text match then PostGIS cross-validation
    dcp_former_council = detect_former_council(req.address, zone_epi)
    dcp_former_council = _validate_former_council_postgis(
        dcp_former_council, lat, lng, req.address, zone_epi,
    )

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
        "confidence": _compute_confidence(
            controls, unique_overlays, valuation, covered_layers=covered_layers,
            tax_config_missing=tax_config is None,
        ),
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
        dcp_former_council = _validate_former_council_postgis(
            dcp_former_council, req.lat, req.lng, req.address, zone_epi,
        )

    # ---------- PDF-exclusive data (parallelised) ----------
    # DAs, shadow, and DB queries are independent — run concurrently.
    das = []
    lep_clauses = []
    dcp_setbacks_db = None
    postgis_heritage = {"hca": [], "items": [], "has_heritage": False, "raw": []}
    shadow_result = None
    db_url = os.getenv("DATABASE_URL")

    def _fetch_db_data():
        """DB queries: DAs (local), LEP clauses, DCP setbacks, heritage.

        _das is None until fetched: a DB failure renders as "Not assessed" in
        the PDF DA section, never as "No development applications lodged".
        """
        _das = None
        _lep = []
        _dcp = None
        _heritage = {"hca": [], "items": [], "has_heritage": False, "raw": []}
        if not db_url:
            return _das, _lep, _dcp, _heritage
        conn = None
        try:
            conn = psycopg2.connect(db_url)
            conn.autocommit = True
            # Nearby DAs from local DB (replaces live ePlanning API).
            # prior-art-checked: aligns this call with services/intelligence_brief.py
            # _fetch_nearby_das, which already passes council_name=None — no new
            # capability, this REMOVES a redundant/buggy filter to match it.
            # council_name=None: the 200m Haversine radius filter scopes the
            # search; the council filter is buggy because the DB uses a different
            # council-name vocabulary than the LEP-derived name, so filtering
            # silently returned zero → a false "no DAs" in the Nearby Development
            # Activity section.
            _das = fetch_nearby_das(conn, req.lat, req.lng, council_name=None)
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

    def _fetch_bushfire():
        """Live NSW RFS BFPL point query (~1-2s) — governs the PDF bushfire row.

        Returns None on failure; the renderer shows "Not assessed", never "Clear".
        """
        try:
            # Plain import first: services modules import siblings top-level
            # (e.g. `from audit_trail import ...`), so the package-qualified
            # form fails unless the runtime happens to have both paths set up.
            try:
                from bushfire_prescreen import _query_rfs_bfpl
            except ImportError:
                from services.bushfire_prescreen import _query_rfs_bfpl
            return _query_rfs_bfpl(req.lat, req.lng)
        except Exception as e:
            logger.warning("Live RFS BFPL query failed: %s", e)
            return None

    def _fetch_anef():
        """ANEF contour value (anef_zones + live ePlanning fallback) — three-state.

        A {"status": "failed"} result renders "not assessed" wording in the
        ANEF row, never a silent omission (RFS-future pattern from #674).
        """
        try:
            try:
                from portal_constraints import resolve_anef_value
            except ImportError:
                from services.portal_constraints import resolve_anef_value
            return resolve_anef_value(req.lat, req.lng)
        except Exception as e:
            logger.warning("ANEF value lookup failed: %s", e)
            return {"status": "failed"}

    def _fetch_contributions():
        """Development contributions plans (/cp) — three-state.

        prior-art-checked: wraps portal_constraints.fetch_contributions_plans
        (which mirrors intelligence_brief._fetch_contributions, PR #460, with
        three-state semantics). A {"status": "failed"} result renders
        "Not assessed", never an implied absence of plans.
        """
        if not resolved_prop_id:
            return {"status": "failed"}
        try:
            try:
                from portal_constraints import fetch_contributions_plans
            except ImportError:
                from services.portal_constraints import fetch_contributions_plans
            return fetch_contributions_plans(resolved_prop_id)
        except Exception as e:
            logger.warning("contributions lookup failed: %s", e)
            return {"status": "failed"}

    def _fetch_corridors():
        """Corridors / land-reservation-acquisition / portal warnings —
        three-state per sub-check. None renders every sub-check "Not assessed".
        """
        try:
            try:
                from portal_constraints import fetch_corridors_reservations
            except ImportError:
                from services.portal_constraints import fetch_corridors_reservations
            return fetch_corridors_reservations(
                req.lat, req.lng, lot_wkt=lot_wkt, prop_id=resolved_prop_id,
            )
        except Exception as e:
            logger.warning("corridors/reservations check failed: %s", e)
            return None

    def _fetch_tod():
        """TOD catchment + floor-only capacity baseline.

        prior-art-checked: reuses generate_conveyancing_report.get_tod_uplift_live
        (which wraps portal_constraints.fetch_tod_catchment + constraint_arithmetic)
        — no new catchment or capacity logic. Returns (tod, capacity); (None, None)
        on failure renders the section as omitted, never a false "not in TOD".
        """
        try:
            from generate_conveyancing_report import get_tod_uplift_live
            return get_tod_uplift_live(req.lat, req.lng, controls, valuation)
        except Exception as e:
            logger.warning("TOD uplift check failed: %s", e)
            return None, None

    with ThreadPoolExecutor(max_workers=7) as executor:
        db_future = executor.submit(_fetch_db_data)
        shadow_future = executor.submit(_fetch_shadow)
        bushfire_future = executor.submit(_fetch_bushfire)
        anef_future = executor.submit(_fetch_anef)
        contributions_future = executor.submit(_fetch_contributions)
        corridors_future = executor.submit(_fetch_corridors)
        tod_future = executor.submit(_fetch_tod)
        das, lep_clauses, dcp_setbacks_db, postgis_heritage = db_future.result()
        shadow_result = shadow_future.result()
        bushfire_live = bushfire_future.result()
        anef_live = anef_future.result()
        contributions_result = contributions_future.result()
        corridors_result = corridors_future.result()
        tod_result, capacity_result = tod_future.result()

    # Merge PostGIS heritage — keep HCA and individual items separate.
    # PostGIS HCA entries go into heritage_hca only (never reclassify portal items).
    # PostGIS individual items merge into heritage_items (deduplicated).
    if postgis_heritage["hca"]:
        existing_hca = controls.get("heritage_hca") or []
        merged_hca = list(dict.fromkeys(existing_hca + postgis_heritage["hca"]))
        controls["heritage_hca"] = merged_hca
        # Also ensure HCA entries appear in the combined heritage_items list
        existing_items = controls.get("heritage_items") or []
        controls["heritage_items"] = list(dict.fromkeys(existing_items + postgis_heritage["hca"]))
    if postgis_heritage["items"]:
        existing_items = controls.get("heritage_items") or []
        controls["heritage_items"] = list(dict.fromkeys(existing_items + postgis_heritage["items"]))

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
        bushfire_live=bushfire_live,
        anef_live=anef_live,
        contributions=contributions_result,
        corridors=corridors_result,
        tod=tod_result,
        capacity=capacity_result,
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


# Layers whose ingest coverage caps confidence when absent for the LGA —
# matches the layers the PDF's coverage footnote reports on (bushfire excluded:
# it is live-checked against NSW RFS, not our ingest).
_CONFIDENCE_COVERAGE_LAYERS = frozenset({
    "flood", "riparian", "wetlands", "landslide", "biodiversity",
})

_CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


def _cap_confidence(current: str, ceiling: str) -> str:
    """Return the lower of two confidence ratings."""
    return current if _CONFIDENCE_ORDER[current] <= _CONFIDENCE_ORDER[ceiling] else ceiling


def _compute_confidence(
    controls: dict,
    overlays: list,
    valuation: dict,
    covered_layers=None,
    shadow_height_source: Optional[str] = None,
    live_query_failures: int = 0,
    tax_config_missing: bool = False,
) -> str:
    """Rate confidence on data completeness AND data integrity (QA-S7).

    Field presence builds the base score; integrity gaps cap it:
      - any coverage-footnote layer unmapped for this LGA → at most "medium"
      - shadow height from the assumed default envelope   → at most "medium"
      - 1 live-query failure → at most "medium"; ≥2 → "low"
      - land-tax config absent (section rendered "Not assessed") → at most "medium"
    A report that had to assume, or whose coverage has holes, must not claim
    "high" confidence regardless of how many fields are populated.
    """
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
        rating = "high"
    elif score >= 3:
        rating = "medium"
    else:
        rating = "low"

    if covered_layers is not None:
        covered = set(covered_layers)
        if _CONFIDENCE_COVERAGE_LAYERS - covered:
            rating = _cap_confidence(rating, "medium")
    if shadow_height_source == "default":
        rating = _cap_confidence(rating, "medium")
    if tax_config_missing:
        rating = _cap_confidence(rating, "medium")
    if live_query_failures >= 2:
        rating = _cap_confidence(rating, "low")
    elif live_query_failures == 1:
        rating = _cap_confidence(rating, "medium")

    return rating
