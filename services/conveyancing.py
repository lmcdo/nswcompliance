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

try:
    from services.cdc_screen import run_cdc_screen_for_report  # Docker (PYTHONPATH=/app)
except ImportError:
    from cdc_screen import run_cdc_screen_for_report  # noqa: E402 — local

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


def _nearby_da_count(
    council_name: Optional[str], lat: float, lng: float,
) -> tuple[Optional[int], bool]:
    """Return (da_count, fetch_failed) for the 200 m nearby-DA lookup.

    prior-art-checked: not a new data source. Extracts the EXISTING inline
    nearby-DA lookup already in this function into a helper so its false-zero
    (da_count=0 on failure) becomes three-state. Reuses fetch_nearby_das and
    mirrors intelligence_brief.py's DataField[Optional[int]] convention.

    Three-state (CONVEYANCING_QA_ADVERSARIAL.md S1 / R6): da_count is None — never
    0 — whenever the check could not be completed: council unresolved, DATABASE_URL
    absent, or the query raised. A genuine "0 DAs within 200 m" returns (0, False)
    and is therefore never confused with "not assessed". fetch_failed is True in
    every not-completed case; callers use it to withhold the DA data source and to
    render "could not be checked" instead of a false "none nearby".

    council_name only gates whether we attempt the lookup; the query itself passes
    council_name=None because the DB stores a different council-name vocabulary than
    the LEP-derived name (see tests/test_conveyancing_nearby_da_council).
    """
    if not council_name:
        return None, True
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None, True
    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        try:
            das = fetch_nearby_das(conn, lat, lng, council_name=None)
            return len(das), False
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"DA fetch failed: {e}")
        return None, True


def _load_regulatory_configs() -> tuple[Optional[dict], Optional[dict]]:
    """Load SEPP Housing + tax thresholds from DB for calc_feasibility.

    Returns (sepp_standards, tax_config) — both None if DB unavailable.
    Implementation moved to conveyancing_db.load_regulatory_configs so the CLI
    report path injects the same configs (a None tax_config renders "Not
    assessed", never hardcoded figures).
    """
    return load_regulatory_configs(os.getenv("DATABASE_URL"))


def _fetch_pdf_db_data(db_url, lat, lng, lot_wkt, controls, dcp_former_council):
    """DB queries for the paid PDF: DAs (local), LEP clauses, DCP setbacks,
    heritage.

    prior-art-checked: this IS the existing inline `_fetch_db_data` closure
    from generate_conveyancing_pdf, extracted to module level and split — no
    new data source; the four queries are unchanged. The extraction follows
    the _nearby_da_count precedent (extracted so its false-zero became a
    testable three-state). One try-block previously covered all four fetches,
    so an exception mid-way left the later results empty and the PDF rendered
    empty-as-absent (absence census row 1; output-grounding fix 3). Each fetch
    now fails independently and reports itself in `failed`: a failed check
    renders "could not be determined", never a clean absence.

    Returns (das, lep, dcp, heritage, failed) where failed maps each fetch key
    (das / lep / dcp / heritage) to True when it could not be completed:
      das      — None=not fetched (failed), list otherwise.
      lep      — [] means no key_sites_clause (N/A) or none found; a failed
                 query keeps [] but sets the lep flag.
      dcp      — None means council not covered (N/A, not queried) OR failed;
                 the dcp flag distinguishes the two.
      heritage — empty shape on failure with the heritage flag set, so an
                 unchecked supplement is never read as no-heritage.
    A connection failure fails every applicable fetch.
    """
    import psycopg2

    _das = None
    _lep = []
    _dcp = None
    _heritage = {"hca": [], "items": [], "has_heritage": False, "raw": []}
    _failed = {"das": True, "lep": False, "dcp": False, "heritage": True}
    key_sites_clause = controls.get("key_sites_clause")
    if key_sites_clause:
        _failed["lep"] = True
    if dcp_former_council:
        _failed["dcp"] = True
    if not db_url:
        return _das, _lep, _dcp, _heritage, _failed
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
    except Exception as e:
        logger.warning("DB pre-fetch: connection failed — all four checks "
                       "not assessed: %s", e)
        return _das, _lep, _dcp, _heritage, _failed
    try:
        try:
            # Nearby DAs from local DB (replaces live ePlanning API).
            # council_name=None: the 200m Haversine radius filter scopes the
            # search; the council filter is buggy because the DB uses a
            # different council-name vocabulary than the LEP-derived name,
            # so filtering silently returned zero → a false "no DAs".
            _das = fetch_nearby_das(conn, lat, lng, council_name=None)
            _failed["das"] = False
        except Exception as e:
            logger.warning("DB pre-fetch: nearby-DA query failed: %s", e)
        epi_name = controls.get("zone_epi", "")
        prop_zone = controls.get("zone", "")
        if key_sites_clause:
            try:
                _lep = fetch_lep_clauses(conn, key_sites_clause, epi_name)
                _failed["lep"] = False
            except Exception as e:
                logger.warning("DB pre-fetch: LEP-clause query failed: %s", e)
        if dcp_former_council:
            try:
                # raise_on_error=True (DQ-82): without it this fetcher returns
                # None on a query failure AND on a genuine absence of controls,
                # so it returns NORMALLY either way and _failed["dcp"] is set
                # False below — recording a completed check that found nothing.
                # The other three fetchers now raise; this one already had the
                # flag for it and simply was not being asked.
                _dcp = fetch_dcp_setbacks(conn, dcp_former_council, prop_zone,
                                          raise_on_error=True)
                _failed["dcp"] = False
            except Exception as e:
                logger.warning("DB pre-fetch: DCP-setback query failed: %s", e)
        try:
            _heritage = fetch_heritage_postgis(conn, lat, lng, lot_wkt=lot_wkt)
            _failed["heritage"] = False
        except Exception as e:
            logger.warning("DB pre-fetch: heritage query failed: %s", e)
    finally:
        conn.close()
    return _das, _lep, _dcp, _heritage, _failed


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


def _resolve_property(req: ConveyancingRequest) -> tuple[int, float, float, Optional[str]]:
    """Resolve (prop_id, lat, lng, lot_wkt) authoritatively from req.address.

    prior-art-checked: not a new data source. Replaces the inline caller-triple
    fast path already in run_conveyancing; reuses the existing resolve_address.

    All four values come from the SAME address resolution, so prop_id-keyed data
    (LEP controls, valuation) and coordinate-keyed data (spatial overlays, strata,
    nearby DAs) can never describe two different properties. The removed fast path
    trusted a caller-supplied (prop_id, lat, lng) triple without binding them: a
    mismatched triple produced a report mixing one property's controls with another's
    overlays under a single address label. resolve_address also enforces GATE-0
    parcel identity (fail-closed) and returns lot_wkt, which the fast path left None
    (so overlay point-queries missed layers intersecting only the parcel edge).

    A caller-supplied prop_id is accepted only as advisory: the address is
    authoritative, so a disagreement is logged and the resolved prop_id wins.

    Failure contract: 422 when the address resolves to no parcel (not found or
    GATE-0 identity mismatch — resolve_address returns None, a client-fixable
    input problem); 503 when resolve_address itself raises (Portal unreachable /
    upstream 5xx — a retryable operational failure, not a claim that a valid
    address is invalid).
    """
    try:
        prop_id, lat, lng, lot_wkt = resolve_address(req.address)
    except Exception:
        logger.exception("Address resolution failed (operational) for %r", req.address)
        raise HTTPException(
            status_code=503,
            detail="Address service temporarily unavailable; please retry.",
        )

    if not prop_id or not lat or not lng:
        raise HTTPException(
            status_code=422, detail=f"Could not resolve address to a parcel: {req.address}",
        )

    if req.prop_id and str(req.prop_id) != str(prop_id):
        logger.warning(
            "conveyancing: caller prop_id %s disagrees with resolved %s for %r; "
            "using resolved (address is authoritative)",
            req.prop_id, prop_id, req.address,
        )
    return int(prop_id), lat, lng, lot_wkt


@router.post("/conveyancing")
def run_conveyancing(req: ConveyancingRequest):
    """
    On-demand conveyancing disclosure analysis.
    Returns structured data for the free tier frontend display.
    PDF generation is a separate paid endpoint.
    """
    # Resolve prop_id, coordinates AND lot geometry from the one address so
    # prop_id-keyed data and coordinate-keyed data always describe the same
    # property (see _resolve_property). A caller-supplied triple is never trusted.
    resolved_prop_id, lat, lng, lot_wkt = _resolve_property(req)

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
    # CDC screen (#820): engine verdict from verified Codes SEPP standards;
    # None renders "Not assessed" — never a zone-list guess.
    cdc_result = run_cdc_screen_for_report(
        os.getenv("DATABASE_URL"), controls.get("zone"), valuation.get("lot_area_m2"),
        controls.get("heritage_items"), controls.get("heritage_hca"),
        unique_overlays, covered_layers,
    )
    feasibility = calc_feasibility(
        controls, valuation, unique_overlays,
        is_strata=strata_info["is_strata"],
        sepp_standards=sepp_standards,
        tax_config=tax_config,
        cdc_result=cdc_result,
    )

    # DA count (quick — no full details in free tier). Three-state: da_count is
    # None + da_fetch_failed True when the check could not run, so a failure is
    # never served as a false "0 DAs nearby" (see _nearby_da_count).
    zone_epi = controls.get("zone_epi", "")
    council_name = _council_from_zone_epi(zone_epi)
    da_count, da_fetch_failed = _nearby_da_count(council_name, lat, lng)

    # Check DCP availability — text match then PostGIS cross-validation
    dcp_former_council = detect_former_council(req.address, zone_epi)
    dcp_former_council = _validate_former_council_postgis(
        dcp_former_council, lat, lng, req.address, zone_epi,
    )

    data_sources = list(_DATA_SOURCES)
    if da_fetch_failed:
        # Don't claim the DA API as a source when the nearby-DA check never ran —
        # otherwise da_count None/absent reads as an authoritative "none nearby".
        data_sources = [s for s in data_sources if s != "NSW ePlanning DA API"]
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
            # Summary counts. da_count is None (not 0) when da_fetch_failed —
            # "not assessed", distinct from a genuine 0 DAs within 200 m.
            "da_count": da_count,
            "da_fetch_failed": da_fetch_failed,
            "dcp_available": bool(dcp_former_council),
        },
        "confidence": _compute_confidence(
            controls, unique_overlays, valuation, covered_layers=covered_layers,
            tax_config_missing=tax_config is None,
            sepp_config_missing=sepp_standards is None,
            # The badge must see this response's own absence state (output-
            # grounding fix 3): a failed nearby-DA check renders "could not be
            # checked", and a report carrying a not-assessed section must not
            # claim high confidence. No caller passed live_query_failures
            # before this.
            live_query_failures=1 if da_fetch_failed else 0,
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

    # A usable cache entry must carry its own authoritative coordinates AND address
    # (all written together by the free-tier run). An entry missing any of them is
    # treated as a miss so the whole property is re-resolved below — cached data is
    # never paired with coordinates or an address resolved/supplied separately.
    if (cached and cached.get("lat") is not None and cached.get("lng") is not None
            and cached.get("address")):
        # ---------- cache hit: unpack authoritative free-tier results ----------
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
        # Non-None by the branch condition; part of the same authoritative cache
        # entry as prop_id/controls/valuation, so everything is one property.
        lat = cached.get("lat")
        lng = cached.get("lng")
        # The report's identity is the cached (report_id) entry, so the address
        # label and address-derived lookups come from the cache, not the caller
        # (guaranteed present by the branch condition). A caller can't render this
        # property's data under a different address.
        address = cached.get("address")
    else:
        # ---------- cache miss: full pipeline re-run ----------
        # Resolve prop_id, coordinates AND lot_wkt from the one address (same
        # binding as the free-tier /conveyancing path) instead of trusting the
        # caller's (prop_id, lat, lng). Without this a direct /pdf caller could mix
        # one property's controls/valuation with another's overlays. The cache-hit
        # branch above is already authoritative (coords written by the free-tier
        # run). ConveyancingPdfRequest carries .address and .prop_id, which is all
        # _resolve_property reads.
        logger.info(f"Cache miss for {req.report_id} — running full pipeline")
        resolved_prop_id, lat, lng, lot_wkt = _resolve_property(req)
        address = req.address  # resolution key on a miss; kept as one local for both paths

        controls = parse_controls(get_raw_controls(resolved_prop_id))
        valuation = get_valuation(resolved_prop_id)

        unique_overlays, covered_layers, proximity_m = get_unique_overlays(lat, lng, lot_wkt)
        strata_info = detect_strata(address, lat, lng)

        # PostGIS fallbacks
        ov_by_type = {o["layer_type"]: o for o in unique_overlays}
        if not controls.get("ass_class") and "acid_sulfate" in ov_by_type:
            controls["ass_class"] = ov_by_type["acid_sulfate"].get("value") or "Present"
        if not controls.get("lot_size") and "lot_size" in ov_by_type:
            controls["lot_size"] = ov_by_type["lot_size"].get("value")
            controls["lot_size_units"] = "m\u00b2"

        headroom = calc_development_headroom(controls, valuation)
        sepp_standards, tax_config = _load_regulatory_configs()
        cdc_result = run_cdc_screen_for_report(
            os.getenv("DATABASE_URL"), controls.get("zone"), valuation.get("lot_area_m2"),
            controls.get("heritage_items"), controls.get("heritage_hca"),
            unique_overlays, covered_layers,
        )
        feasibility = calc_feasibility(
            controls, valuation, unique_overlays,
            is_strata=strata_info["is_strata"],
            sepp_standards=sepp_standards,
            tax_config=tax_config,
            cdc_result=cdc_result,
        )

        zone_epi = controls.get("zone_epi") or ""
        council_name = _council_from_zone_epi(zone_epi)
        dcp_former_council = detect_former_council(address, zone_epi)
        dcp_former_council = _validate_former_council_postgis(
            dcp_former_council, lat, lng, address, zone_epi,
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
        return _fetch_pdf_db_data(
            db_url, lat, lng, lot_wkt, controls, dcp_former_council,
        )

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
        return get_shadow_risk(address, str(resolved_prop_id), lat, lng, height_m=lep_height)

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
            return _query_rfs_bfpl(lat, lng)
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
            return resolve_anef_value(lat, lng)
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
                lat, lng, lot_wkt=lot_wkt, prop_id=resolved_prop_id,
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
            return get_tod_uplift_live(lat, lng, controls, valuation)
        except Exception as e:
            logger.warning("TOD uplift check failed: %s", e)
            return None, None

    def _fetch_structures_records():
        """Subject-lot DA+CDC application records (structures & records Stage 1).

        prior-art-checked: reuses generate_conveyancing_report.get_structures_records_live
        (which wraps pre_da_history.get_da_events/get_pcc_events) — no new fetcher,
        no imagery/detection call. Returns (records, status); (None, "failed")
        renders "Not assessed", never an implied absence of applications.
        """
        try:
            from generate_conveyancing_report import get_structures_records_live
            return get_structures_records_live(council_name, address)
        except Exception as e:
            logger.warning("structures/records lookup failed: %s", e)
            return None, "failed"

    def _fetch_climate():
        """NARCliM 2.0 projection state — the four data states kept DISTINCT.

        prior-art-checked: reuses climate_risk_raster.query_narclim_state (thin
        wrapper over query_narclim_summary) — NO new hazard scoring, NO composite
        score (barred by the legal assessment; #699). out_of_domain (permanent
        geographic limit) and unavailable (fixable infra gap) are NOT collapsed;
        that is why this calls query_narclim_state directly instead of the brief's
        _fetch_climate_risk (which flattens both to None). The renderer shows
        factual projection metrics only, never a number in a non-present state.
        """
        try:
            try:
                from climate_risk_raster import query_narclim_state
            except ImportError:
                from services.climate_risk_raster import query_narclim_state
            return query_narclim_state(lat, lng)
        except Exception as e:
            logger.warning("NARCliM projection lookup failed: %s", e)
            return {"state": "unavailable"}

    def _fetch_mine_subsidence():
        """Mine subsidence district — three-state.

        prior-art-checked: reuses generate_conveyancing_report.get_mine_subsidence_live
        (which wraps portal_constraints.fetch_mine_subsidence, the Site Report's
        fetcher) — no new client. {"status": "empty"} is a checked clear;
        {"status": "failed"} renders "Not assessed", never "Clear".
        """
        try:
            from generate_conveyancing_report import get_mine_subsidence_live
            return get_mine_subsidence_live(lat, lng)
        except Exception as e:
            logger.warning("mine subsidence lookup failed: %s", e)
            return {"status": "failed"}

    def _fetch_contaminated():
        """EPA contaminated-land notified sites within 500 m — three-state.

        prior-art-checked: reuses generate_conveyancing_report.get_contaminated_live
        (which wraps portal_constraints.fetch_contaminated_land, the Site
        Report's fetcher). A failed lookup must never render as a clear
        register on the one row conveyancers read for legal exposure.
        """
        try:
            from generate_conveyancing_report import get_contaminated_live
            return get_contaminated_live(lat, lng)
        except Exception as e:
            logger.warning("contaminated land lookup failed: %s", e)
            return {"status": "failed"}

    def _fetch_servicing():
        """Sydney Water Growth Servicing Plan servicing status — three-state.

        prior-art-checked: reuses generate_conveyancing_report.get_servicing_live
        (which wraps services.gsp_servicing.fetch_gsp_servicing, the reusable DB
        lookup). A failed lookup renders "Not assessed", never a clear/serviceable
        result. Data is © Sydney Water — the row attributes + links to the GSP page.
        """
        try:
            from generate_conveyancing_report import get_servicing_live
            # Resolved, property-bound coordinates (#818 binding contract).
            return get_servicing_live(lat, lng)
        except Exception as e:
            logger.warning("Sydney Water servicing lookup failed: %s", e)
            return {"status": "failed"}

    def _fetch_coastal():
        """Estuarine tidal inundation mapped-extent check — three-state.

        prior-art-checked: reuses generate_conveyancing_report
        .get_coastal_inundation_live (spatial_overlays coastal_inundation
        layer, lot-polygon intersection with point fallback) — no new client.
        {"status": "outside"} is a checked non-intersection; {"status":
        "failed"} renders "not assessed", never an outside-extent claim.
        """
        try:
            from generate_conveyancing_report import get_coastal_inundation_live
            # Resolved, property-bound coordinates (#818 binding contract) —
            # never req.lat/req.lng, which may belong to a different address.
            return get_coastal_inundation_live(lat, lng, lot_wkt=lot_wkt)
        except Exception as e:
            logger.warning("estuarine inundation lookup failed: %s", e)
            return {"status": "failed"}

    with ThreadPoolExecutor(max_workers=12) as executor:
        db_future = executor.submit(_fetch_db_data)
        shadow_future = executor.submit(_fetch_shadow)
        bushfire_future = executor.submit(_fetch_bushfire)
        anef_future = executor.submit(_fetch_anef)
        contributions_future = executor.submit(_fetch_contributions)
        corridors_future = executor.submit(_fetch_corridors)
        tod_future = executor.submit(_fetch_tod)
        structures_future = executor.submit(_fetch_structures_records)
        climate_future = executor.submit(_fetch_climate)
        mine_future = executor.submit(_fetch_mine_subsidence)
        contam_future = executor.submit(_fetch_contaminated)
        servicing_future = executor.submit(_fetch_servicing)
        coastal_future = executor.submit(_fetch_coastal)
        das, lep_clauses, dcp_setbacks_db, postgis_heritage, db_fetch_failed = db_future.result()
        shadow_result = shadow_future.result()
        bushfire_live = bushfire_future.result()
        anef_live = anef_future.result()
        contributions_result = contributions_future.result()
        corridors_result = corridors_future.result()
        tod_result, capacity_result = tod_future.result()
        structures_records_result, structures_records_status = structures_future.result()
        climate_result = climate_future.result()
        mine_subsidence_result = mine_future.result()
        contaminated_result = contam_future.result()
        servicing_result = servicing_future.result()
        coastal_result = coastal_future.result()

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
        pdf_path, address, lat, lng, controls, valuation,
        headroom, feasibility, unique_overlays, das,
        dcp_former_council=dcp_former_council,
        strata_info=strata_info,
        covered_layers=covered_layers,
        shadow_result=shadow_result,
        lep_clauses=lep_clauses,
        dcp_setbacks_db=dcp_setbacks_db,
        db_fetch_failed=db_fetch_failed,
        proximity_m=proximity_m,
        bushfire_live=bushfire_live,
        anef_live=anef_live,
        contributions=contributions_result,
        corridors=corridors_result,
        tod=tod_result,
        capacity=capacity_result,
        structures_records=structures_records_result,
        structures_records_status=structures_records_status,
        climate=climate_result,
        mine_subsidence=mine_subsidence_result,
        contaminated=contaminated_result,
        servicing=servicing_result,
        coastal=coastal_result,
    )

    # Upload to R2
    pdf_url = _upload_to_r2(pdf_path, req.report_id)
    if not pdf_url:
        raise HTTPException(status_code=503, detail="PDF upload failed")

    return {
        "report_id": req.report_id,
        "pdf_url": pdf_url,
        "address": address,
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


# prior-art-checked: reuse not viable — this IS the existing cache reader in
# this file gaining an age policy; no new data source or capability.
# Max cache age for PDF assembly (output-grounding fix 2). The cache exists so
# the PAID PDF can reuse the free-tier run from the same purchase session; the
# sources beneath it (Portal controls, valuation, overlays) change on external
# schedules, so its legitimate lifetime is the purchase-decision window, not
# archival. 24h covers an overnight decision while bounding staleness to one
# day; an older entry is a MISS and the PDF endpoint re-runs the full pipeline
# (its existing fallback), so expiry costs latency, never correctness.
_PIPELINE_CACHE_MAX_AGE_HOURS = 24


def _load_pipeline_cache(report_id: str) -> Optional[dict]:
    """Load cached free-tier pipeline results. Returns None on miss, expiry,
    or error — expiry is logged distinctly from absence so a stale entry is
    visible as such, not as a mystery miss."""
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
                # COALESCE(..., TRUE): a NULL created_at (legacy/imported row)
                # must EXPIRE, not slip past the age bound as NULL-is-falsy
                # freshness (Sol round 1 on this fix).
                "SELECT pipeline_data, "
                "       COALESCE(created_at < NOW() - make_interval(hours => %s), TRUE) AS expired "
                "FROM conveyancing_cache WHERE report_id = %s",
                (_PIPELINE_CACHE_MAX_AGE_HOURS, report_id),
            )
            row = cur.fetchone()
        if row and row[1]:
            logger.info(
                "Pipeline cache for %s EXPIRED (older than %sh) — full re-run",
                report_id, _PIPELINE_CACHE_MAX_AGE_HOURS,
            )
            return None
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
    sepp_config_missing: bool = False,
) -> str:
    """Rate confidence on data completeness AND data integrity (QA-S7).

    Field presence builds the base score; integrity gaps cap it:
      - any coverage-footnote layer unmapped for this LGA → at most "medium"
      - shadow height from the assumed default envelope   → at most "medium"
      - 1 live-query failure → at most "medium"; ≥2 → "low"
      - land-tax config absent (section rendered "Not assessed") → at most "medium"
      - SEPP Housing config absent (secondary-dwelling row "Not assessed", #684)
        → at most "medium"
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
    if sepp_config_missing:
        rating = _cap_confidence(rating, "medium")
    if live_query_failures >= 2:
        rating = _cap_confidence(rating, "low")
    elif live_query_failures == 1:
        rating = _cap_confidence(rating, "medium")

    return rating
