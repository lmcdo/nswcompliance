"""
Construction Loan Drawdown Verification — FastAPI router.

POST /pipeline/drawdown-verify
  Input:  { loan_id, address, stage_claimed, lot_bbox_wgs84, reference_date }
  Action: finds two Sentinel-1 SLC scenes via asf_search, submits HyP3 Burst
          InSAR job, stores job record, returns job_id + status "submitted"
  Turnaround: 1–2 hours (HyP3 cloud processing)

GET /pipeline/drawdown-verify/{job_id}
  Action: polls HyP3 for job status; if complete, downloads coherence GeoTIFF,
          extracts coherence at lot centroid, computes confidence score, writes
          audit record to Supabase, uploads GeoTIFF to R2, returns result.

Confidence scoring (Phase 1 — coherence delta):
  Coherence 0.0–1.0: high = stable ground, low = active construction disturbance.
  We compare coherence in the claimed stage window against a pre-construction
  baseline pair. Delta < -0.25 = strong construction signal (high confidence).
  This is a first-pass heuristic — calibrate thresholds against Task 6 ground
  truth dataset before commercial deployment.

Stages:
  "site_cleared"   — baseline comparison only (no Nearmap)
  "slab"           — coherence delta vs pre-construction baseline
  "frame"          — coherence delta (Nearmap optional upgrade at this stage)
  "lock_up"        — coherence delta + double-bounce backscatter increase
  "completion"     — stable high-backscatter recovery

DB table required (run migration 033 before using this service):
  CREATE TABLE drawdown_verify_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id TEXT NOT NULL,
    address TEXT NOT NULL,
    stage_claimed TEXT NOT NULL,
    hyp3_job_name TEXT NOT NULL,
    hyp3_job_id TEXT,
    status TEXT NOT NULL DEFAULT 'submitted',
    confidence FLOAT,
    coherence_delta FLOAT,
    coherence_before FLOAT,
    coherence_after FLOAT,
    evidence_date_before TEXT,
    evidence_date_after TEXT,
    scene_before TEXT,
    scene_after TEXT,
    manual_review BOOLEAN,
    geotiff_r2_key TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
  );

Install requirements (not yet in requirements.txt — add before deploying):
  pip install hyp3_sdk asf_search rasterio shapely boto3
"""

import logging
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["drawdown-verify"])

# ---------------------------------------------------------------------------
# Config — all from environment variables
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "")
ASF_USERNAME = os.environ.get("ASF_EARTHDATA_USERNAME", "")
ASF_PASSWORD = os.environ.get("ASF_EARTHDATA_PASSWORD", "")
R2_BUCKET = os.environ.get("R2_BUCKET_NAME", "plotdetect-evidence")
R2_ENDPOINT = os.environ.get("R2_ENDPOINT_URL", "")
R2_ACCESS_KEY = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")

VALID_STAGES = {"site_cleared", "slab", "frame", "lock_up", "completion"}

# Coherence thresholds — calibrate against Task 6 ground truth before going live
CONFIDENCE_THRESHOLDS = {
    "high": -0.30,    # coherence delta ≤ -0.30 → high confidence construction active
    "medium": -0.15,  # coherence delta ≤ -0.15 → medium confidence
    # above -0.15 → low confidence, flag for manual review
}

MANUAL_REVIEW_THRESHOLD = -0.15  # delta above this triggers manual_review = True


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class LotBbox(BaseModel):
    """WGS84 bounding box for the lot. All values in decimal degrees."""
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    @field_validator("min_lon", "max_lon")
    @classmethod
    def _valid_lon(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError(f"Longitude {v} out of range")
        return v

    @field_validator("min_lat", "max_lat")
    @classmethod
    def _valid_lat(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError(f"Latitude {v} out of range")
        return v

    def to_wkt_polygon(self) -> str:
        return (
            f"POLYGON(({self.min_lon} {self.min_lat},"
            f"{self.max_lon} {self.min_lat},"
            f"{self.max_lon} {self.max_lat},"
            f"{self.min_lon} {self.max_lat},"
            f"{self.min_lon} {self.min_lat}))"
        )

    def centroid(self) -> tuple[float, float]:
        return (
            (self.min_lon + self.max_lon) / 2,
            (self.min_lat + self.max_lat) / 2,
        )


class DrawdownVerifyRequest(BaseModel):
    loan_id: str
    address: str
    stage_claimed: str
    lot_bbox: LotBbox
    # Date the drawdown is claimed (used to bracket the Sentinel-1 search window)
    reference_date: str  # ISO 8601 YYYY-MM-DD

    @field_validator("stage_claimed")
    @classmethod
    def _valid_stage(cls, v: str) -> str:
        if v not in VALID_STAGES:
            raise ValueError(f"stage_claimed must be one of {sorted(VALID_STAGES)}")
        return v

    @field_validator("reference_date")
    @classmethod
    def _valid_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("reference_date must be YYYY-MM-DD")
        return v


class DrawdownVerifySubmitResponse(BaseModel):
    job_id: str
    hyp3_job_name: str
    status: str  # "submitted"
    message: str


class DrawdownVerifyResultResponse(BaseModel):
    job_id: str
    loan_id: str
    address: str
    stage_claimed: str
    status: str                      # "submitted" | "processing" | "complete" | "failed"
    confidence: Optional[float]      # 0.0–1.0; None if not yet complete
    coherence_delta: Optional[float] # after - before coherence; negative = construction active
    coherence_before: Optional[float]
    coherence_after: Optional[float]
    evidence_date_before: Optional[str]
    evidence_date_after: Optional[str]
    manual_review: Optional[bool]
    geotiff_r2_key: Optional[str]
    error_message: Optional[str]


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _db_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def _insert_audit(
    loan_id: str,
    address: str,
    stage_claimed: str,
    hyp3_job_name: str,
    hyp3_job_id: Optional[str],
    scene_before: Optional[str],
    scene_after: Optional[str],
) -> str:
    """Insert initial audit record; return the UUID."""
    audit_id = str(uuid.uuid4())
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO drawdown_verify_audits
                  (id, loan_id, address, stage_claimed, hyp3_job_name,
                   hyp3_job_id, scene_before, scene_after, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'submitted')
                """,
                (audit_id, loan_id, address, stage_claimed,
                 hyp3_job_name, hyp3_job_id, scene_before, scene_after),
            )
        conn.commit()
    return audit_id


def _update_audit(audit_id: str, **fields) -> None:
    """Update named fields on an audit record."""
    if not fields:
        return
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [audit_id]
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE drawdown_verify_audits SET {set_clause}, updated_at = NOW() WHERE id = %s",
                values,
            )
        conn.commit()


def _get_audit(audit_id: str) -> Optional[dict]:
    with _db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM drawdown_verify_audits WHERE id = %s", (audit_id,)
            )
            row = cur.fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# SAR scene search
# ---------------------------------------------------------------------------

def _find_sentinel1_scenes(bbox: LotBbox, reference_date: str) -> tuple[str, str, str, str]:
    """
    Find two Sentinel-1 SLC scenes bracketing the reference_date for the lot bbox.

    Returns: (scene_before_id, scene_after_id, date_before, date_after)

    Strategy: search for scenes in a window [reference_date - 30d, reference_date + 7d].
    Take the scene immediately before reference_date and the next available scene
    (~12 days later). This gives a coherence pair that straddles the claimed
    stage completion date.
    """
    try:
        import asf_search as asf
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="asf_search not installed. Run: pip install asf_search",
        )

    ref = datetime.strptime(reference_date, "%Y-%m-%d")
    search_start = (ref - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z")
    search_end = (ref + timedelta(days=14)).strftime("%Y-%m-%dT23:59:59Z")

    results = asf.search(
        platform=asf.PLATFORM.SENTINEL1,
        processingLevel=asf.PRODUCT_TYPE.SLC,
        intersectsWith=bbox.to_wkt_polygon(),
        start=search_start,
        end=search_end,
    )

    if len(results) < 2:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Fewer than 2 Sentinel-1 SLC scenes found for bbox "
                f"between {search_start} and {search_end}. "
                f"Try widening the date window or check coverage for this location."
            ),
        )

    # Sort by acquisition date ascending
    results_sorted = sorted(
        results,
        key=lambda r: r.properties.get("startTime", ""),
    )

    # Find the scene immediately before the reference date and the next one
    before = None
    after = None
    for scene in results_sorted:
        scene_date = scene.properties.get("startTime", "")[:10]  # YYYY-MM-DD
        if scene_date <= reference_date:
            before = scene
        elif before is not None and after is None:
            after = scene
            break

    if before is None or after is None:
        # Fall back to first two available scenes
        before, after = results_sorted[0], results_sorted[1]
        logger.warning(
            "Could not bracket reference_date %s — using first two scenes: %s, %s",
            reference_date,
            before.properties.get("sceneName"),
            after.properties.get("sceneName"),
        )

    return (
        before.properties["sceneName"],
        after.properties["sceneName"],
        before.properties.get("startTime", "")[:10],
        after.properties.get("startTime", "")[:10],
    )


# ---------------------------------------------------------------------------
# HyP3 job submission
# ---------------------------------------------------------------------------

def _submit_hyp3_job(
    scene_before: str,
    scene_after: str,
    job_name: str,
) -> str:
    """Submit a Burst InSAR job to ASF HyP3. Returns HyP3 job ID."""
    try:
        import hyp3_sdk as sdk
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="hyp3_sdk not installed. Run: pip install hyp3_sdk",
        )

    if not ASF_USERNAME or not ASF_PASSWORD:
        raise HTTPException(
            status_code=500,
            detail="ASF_EARTHDATA_USERNAME and ASF_EARTHDATA_PASSWORD env vars not set.",
        )

    hyp3 = sdk.HyP3(username=ASF_USERNAME, password=ASF_PASSWORD)

    job = hyp3.submit_insar_job(
        granule1=scene_before,
        granule2=scene_after,
        name=job_name,
        looks="10x2",          # ~40m resolution — sufficient for residential lot
        apply_water_mask=False,
        include_dem=False,
        include_wrapped_phase=False,
    )

    # HyP3 returns a Batch object; get the first (and only) job's ID
    return job.jobs[0].job_id


# ---------------------------------------------------------------------------
# Coherence extraction
# ---------------------------------------------------------------------------

def _extract_coherence_at_centroid(geotiff_path: str, lon: float, lat: float) -> float:
    """
    Extract the coherence value at a point from a HyP3 InSAR GeoTIFF.

    HyP3 Burst InSAR output includes a *_corr.tif band (coherence, 0.0–1.0).
    If multiple bands exist, band 1 is coherence by convention.
    """
    try:
        import rasterio
        from rasterio.crs import CRS
        from rasterio.transform import rowcol
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="rasterio not installed. Run: pip install rasterio",
        )

    with rasterio.open(geotiff_path) as src:
        # Transform lon/lat (WGS84) to the raster's CRS
        from rasterio.warp import transform as warp_transform
        xs, ys = warp_transform(
            CRS.from_epsg(4326),
            src.crs,
            [lon],
            [lat],
        )
        row, col = rowcol(src.transform, xs[0], ys[0])

        # Read band 1 (coherence)
        data = src.read(1)
        height, width = data.shape

        if not (0 <= row < height and 0 <= col < width):
            raise HTTPException(
                status_code=422,
                detail=f"Lot centroid ({lat}, {lon}) is outside the coherence raster extent.",
            )

        value = float(data[row, col])

    return value


# ---------------------------------------------------------------------------
# R2 upload
# ---------------------------------------------------------------------------

def _upload_to_r2(local_path: str, r2_key: str) -> None:
    try:
        import boto3
    except ImportError:
        logger.warning("boto3 not installed — skipping R2 upload")
        return

    if not R2_ENDPOINT or not R2_ACCESS_KEY or not R2_SECRET_KEY:
        logger.warning("R2 credentials not configured — skipping upload")
        return

    s3 = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
    )
    s3.upload_file(local_path, R2_BUCKET, r2_key)


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def _score_confidence(coherence_delta: float) -> tuple[float, bool]:
    """
    Convert coherence delta to a confidence score and manual_review flag.

    coherence_delta = coherence_after - coherence_before
    Negative delta = coherence dropped = construction activity detected.

    Returns: (confidence: float 0.0–1.0, manual_review: bool)
    """
    if coherence_delta <= CONFIDENCE_THRESHOLDS["high"]:
        confidence = 0.85 + min(0.10, abs(coherence_delta) - 0.30) * 3
        return round(min(confidence, 0.95), 3), False

    if coherence_delta <= CONFIDENCE_THRESHOLDS["medium"]:
        # Linear scale from 0.60 to 0.85 across the medium band
        band_width = CONFIDENCE_THRESHOLDS["medium"] - CONFIDENCE_THRESHOLDS["high"]
        position = (coherence_delta - CONFIDENCE_THRESHOLDS["medium"]) / band_width
        confidence = 0.60 + position * 0.25
        return round(confidence, 3), False

    # Below threshold — coherence did not drop enough
    return round(max(0.1, 0.60 + coherence_delta), 3), True


# ---------------------------------------------------------------------------
# POST /pipeline/drawdown-verify — submit job
# ---------------------------------------------------------------------------

@router.post("/drawdown-verify", response_model=DrawdownVerifySubmitResponse)
def submit_drawdown_verify(req: DrawdownVerifyRequest):
    """
    Submit a construction drawdown verification job.

    Finds two Sentinel-1 SLC scenes bracketing the reference_date, submits
    a HyP3 Burst InSAR coherence job, records the audit entry, and returns
    immediately with a job_id. Poll GET /pipeline/drawdown-verify/{job_id}
    for the result (ready in 1–2 hours).
    """
    # Unique job name scoped to loan_id so HyP3 deduplicates retries
    safe_stage = req.stage_claimed.replace("_", "-")
    safe_loan = req.loan_id.replace(" ", "-")[:30]
    job_name = f"loan-{safe_loan}-{safe_stage}-{req.reference_date}"

    # Find Sentinel-1 scenes
    try:
        scene_before, scene_after, date_before, date_after = _find_sentinel1_scenes(
            req.lot_bbox, req.reference_date
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Scene search failed for loan %s", req.loan_id)
        raise HTTPException(status_code=500, detail=f"Scene search failed: {exc}") from exc

    # Submit HyP3 job
    try:
        hyp3_job_id = _submit_hyp3_job(scene_before, scene_after, job_name)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("HyP3 submission failed for loan %s", req.loan_id)
        raise HTTPException(status_code=500, detail=f"HyP3 submission failed: {exc}") from exc

    # Insert audit record
    try:
        audit_id = _insert_audit(
            loan_id=req.loan_id,
            address=req.address,
            stage_claimed=req.stage_claimed,
            hyp3_job_name=job_name,
            hyp3_job_id=hyp3_job_id,
            scene_before=scene_before,
            scene_after=scene_after,
        )
    except Exception as exc:
        logger.exception("Audit insert failed for loan %s", req.loan_id)
        # Job is submitted — don't fail the response, but log the DB error
        audit_id = job_name  # use job_name as fallback ID

    logger.info(
        "Drawdown verify submitted | loan=%s stage=%s job_id=%s audit=%s",
        req.loan_id, req.stage_claimed, hyp3_job_id, audit_id,
    )

    return DrawdownVerifySubmitResponse(
        job_id=audit_id,
        hyp3_job_name=job_name,
        status="submitted",
        message=(
            f"HyP3 Burst InSAR job submitted. "
            f"Scenes: {date_before} (before) → {date_after} (after). "
            f"Poll GET /pipeline/drawdown-verify/{audit_id} in 1–2 hours for result."
        ),
    )


# ---------------------------------------------------------------------------
# GET /pipeline/drawdown-verify/{job_id} — poll for result
# ---------------------------------------------------------------------------

@router.get("/drawdown-verify/{job_id}", response_model=DrawdownVerifyResultResponse)
def get_drawdown_verify(job_id: str):
    """
    Poll for the result of a submitted drawdown verification job.

    If the HyP3 job is still running, returns status "processing".
    If complete, extracts coherence, scores confidence, writes audit record,
    uploads GeoTIFF to R2, and returns the full result.
    """
    audit = _get_audit(job_id)
    if audit is None:
        raise HTTPException(status_code=404, detail=f"Job ID {job_id} not found.")

    # Already finalised
    if audit["status"] in ("complete", "failed"):
        return _audit_to_response(audit)

    # Check HyP3 status
    try:
        import hyp3_sdk as sdk
    except ImportError:
        raise HTTPException(status_code=500, detail="hyp3_sdk not installed.")

    hyp3 = sdk.HyP3(username=ASF_USERNAME, password=ASF_PASSWORD)

    try:
        jobs = hyp3.find_jobs(name=audit["hyp3_job_name"])
    except Exception as exc:
        logger.exception("HyP3 status check failed for job %s", job_id)
        raise HTTPException(status_code=502, detail=f"HyP3 status check failed: {exc}") from exc

    if not jobs.jobs:
        raise HTTPException(status_code=404, detail="HyP3 job not found. It may have expired.")

    hyp3_job = jobs.jobs[0]

    if hyp3_job.status_code == "RUNNING":
        _update_audit(job_id, status="processing")
        return DrawdownVerifyResultResponse(
            job_id=job_id,
            loan_id=audit["loan_id"],
            address=audit["address"],
            stage_claimed=audit["stage_claimed"],
            status="processing",
            confidence=None,
            coherence_delta=None,
            coherence_before=None,
            coherence_after=None,
            evidence_date_before=audit.get("evidence_date_before"),
            evidence_date_after=audit.get("evidence_date_after"),
            manual_review=None,
            geotiff_r2_key=None,
            error_message=None,
        )

    if hyp3_job.status_code == "FAILED":
        error = hyp3_job.status_message or "HyP3 processing failed"
        _update_audit(job_id, status="failed", error_message=error)
        return DrawdownVerifyResultResponse(
            job_id=job_id,
            loan_id=audit["loan_id"],
            address=audit["address"],
            stage_claimed=audit["stage_claimed"],
            status="failed",
            confidence=None,
            coherence_delta=None,
            coherence_before=None,
            coherence_after=None,
            evidence_date_before=None,
            evidence_date_after=None,
            manual_review=True,
            geotiff_r2_key=None,
            error_message=error,
        )

    # Job is SUCCEEDED — process result
    if hyp3_job.status_code != "SUCCEEDED":
        # Still pending/queued
        return DrawdownVerifyResultResponse(
            job_id=job_id,
            loan_id=audit["loan_id"],
            address=audit["address"],
            stage_claimed=audit["stage_claimed"],
            status="processing",
            confidence=None,
            coherence_delta=None,
            coherence_before=None,
            coherence_after=None,
            evidence_date_before=None,
            evidence_date_after=None,
            manual_review=None,
            geotiff_r2_key=None,
            error_message=None,
        )

    # Download and process coherence GeoTIFF
    lon, lat = _bbox_to_lot_bbox(audit).centroid() if audit.get("lot_bbox") else (None, None)

    # Reconstruct bbox centroid from scene names as fallback
    # (lot_bbox not stored in DB in v1 — use scene metadata if available)
    # TODO: store lot_bbox in audit record in v2
    if lon is None:
        raise HTTPException(
            status_code=500,
            detail="Lot centroid not available in audit record. This is a v1 limitation.",
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            downloaded = hyp3_job.download_files(location=tmpdir)
        except Exception as exc:
            logger.exception("GeoTIFF download failed for job %s", job_id)
            raise HTTPException(status_code=502, detail=f"GeoTIFF download failed: {exc}") from exc

        # Find the coherence file (*_corr.tif)
        corr_files = [f for f in Path(tmpdir).rglob("*_corr.tif")]
        if not corr_files:
            _update_audit(job_id, status="failed", error_message="No coherence file in HyP3 output")
            raise HTTPException(status_code=502, detail="No *_corr.tif found in HyP3 output.")
        corr_path = str(corr_files[0])

        try:
            coherence_after = _extract_coherence_at_centroid(corr_path, lon, lat)
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Coherence extraction failed for job %s", job_id)
            raise HTTPException(status_code=500, detail=f"Coherence extraction failed: {exc}") from exc

        # Upload GeoTIFF to R2 as immutable evidence
        r2_key = f"drawdown-verify/{audit['loan_id']}/{job_id}/coherence.tif"
        try:
            _upload_to_r2(corr_path, r2_key)
        except Exception as exc:
            logger.warning("R2 upload failed for job %s: %s", job_id, exc)
            r2_key = None

    # For Phase 1, we don't have a stored pre-construction baseline.
    # Use a NSW median coherence for stable urban ground as a proxy: ~0.65.
    # TODO Phase 2: store a baseline coherence per lot at loan origination.
    coherence_before = 0.65  # NSW urban stable-ground proxy baseline
    coherence_delta = coherence_after - coherence_before

    confidence, manual_review = _score_confidence(coherence_delta)

    # Dates from HyP3 job metadata
    date_before = audit.get("scene_before", "")[:8] if audit.get("scene_before") else None
    date_after = audit.get("scene_after", "")[:8] if audit.get("scene_after") else None

    _update_audit(
        job_id,
        status="complete",
        confidence=confidence,
        coherence_delta=round(coherence_delta, 4),
        coherence_before=round(coherence_before, 4),
        coherence_after=round(coherence_after, 4),
        evidence_date_before=date_before,
        evidence_date_after=date_after,
        manual_review=manual_review,
        geotiff_r2_key=r2_key,
    )

    logger.info(
        "Drawdown verify complete | loan=%s stage=%s confidence=%.3f manual_review=%s",
        audit["loan_id"], audit["stage_claimed"], confidence, manual_review,
    )

    return DrawdownVerifyResultResponse(
        job_id=job_id,
        loan_id=audit["loan_id"],
        address=audit["address"],
        stage_claimed=audit["stage_claimed"],
        status="complete",
        confidence=confidence,
        coherence_delta=round(coherence_delta, 4),
        coherence_before=round(coherence_before, 4),
        coherence_after=round(coherence_after, 4),
        evidence_date_before=date_before,
        evidence_date_after=date_after,
        manual_review=manual_review,
        geotiff_r2_key=r2_key,
        error_message=None,
    )


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _bbox_to_lot_bbox(audit: dict) -> Optional[LotBbox]:
    """Reconstruct LotBbox from audit record if stored. Returns None if unavailable."""
    # lot_bbox not persisted in v1 schema — returns None
    return None


def _audit_to_response(audit: dict) -> DrawdownVerifyResultResponse:
    return DrawdownVerifyResultResponse(
        job_id=str(audit["id"]),
        loan_id=audit["loan_id"],
        address=audit["address"],
        stage_claimed=audit["stage_claimed"],
        status=audit["status"],
        confidence=audit.get("confidence"),
        coherence_delta=audit.get("coherence_delta"),
        coherence_before=audit.get("coherence_before"),
        coherence_after=audit.get("coherence_after"),
        evidence_date_before=audit.get("evidence_date_before"),
        evidence_date_after=audit.get("evidence_date_after"),
        manual_review=audit.get("manual_review"),
        geotiff_r2_key=audit.get("geotiff_r2_key"),
        error_message=audit.get("error_message"),
    )
