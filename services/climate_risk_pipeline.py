"""
NSW Climate Risk Score Pipeline -- FastAPI router.

POST /pipeline/climate-risk  -- on-demand: composite climate risk score

Data sources:
  PostGIS spatial_overlays          (flood, bushfire, coastal, fire_history)
  NARCliM 2.0 NetCDF rasters       (TXge35, prAdjust, tas — AdaptNSW)

NOT in the response: the composite score, its band, the interaction bonus, and the
per-hazard weight arithmetic. The composite cannot be validated against any
available reference (docs/CLIMATE_RISK_METHODOLOGY.md → Validation status) and
#699 bars it from every customer-facing surface. It reached this response only
because the handler spreads ``**result.to_dict()``; ``to_dict`` now excludes it,
which is the boundary that keeps it out. If it is not fit to render, it is not
fit to serve. Per-hazard ``weight``/``weighted_score`` go with it — they make the
composite reconstructible, so dropping only score/band would be a half-measure.

Response contract (must match frontend ClimateRiskResult):
{
  "address": str,
  "lat": float,
  "lng": float,
  "run_date": str,
  "outputs": {
    "hazards": [
      {
        "hazard": str,
        "present": bool,
        "detail": str,
        "confidence": str,
        "confidence_reason": str,
        "data_source": str,
        "available": bool    # False = source unavailable, NOT "no risk"
      }
    ],
    "methodology_version": str,
    "data_date": str,
    "disclaimer": str,
    "narclim_summary": dict | null
  },
  "confidence": "high" | "medium" | "low",
  "data_sources": list[str]
}
"""
import logging
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["satellite"])


class ClimateRiskRequest(BaseModel):
    address: str
    lat: float
    lng: float
    report_id: str | None = None


@router.post("/climate-risk")
async def climate_risk_endpoint(req: ClimateRiskRequest):
    """Run composite climate risk score for a single property."""
    try:
        from services.climate_risk_score import climate_risk_score
    except ImportError:
        from climate_risk_score import climate_risk_score

    try:
        from services.climate_risk_raster import query_narclim_summary
    except ImportError:
        from climate_risk_raster import query_narclim_summary

    try:
        result = climate_risk_score(req.lat, req.lng)
    except EnvironmentError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Climate risk score failed for (%s, %s)", req.lat, req.lng)
        raise HTTPException(status_code=500, detail=f"Scoring failed: {e}")

    # Get NARCliM summary for frontend display (trajectory data)
    narclim_summary = None
    try:
        narclim_summary = query_narclim_summary(req.lat, req.lng)
    except (ValueError, FileNotFoundError):
        pass  # Outside domain or files not present

    # Determine overall confidence from per-hazard confidence levels
    hazard_confidences = [h.confidence for h in result.hazards]
    if all(c == "high" for c in hazard_confidences):
        overall_confidence = "high"
    elif any(c == "low" for c in hazard_confidences):
        overall_confidence = "low"
    else:
        overall_confidence = "medium"

    # Collect unique data sources from hazards
    data_sources = list(dict.fromkeys(
        h.data_source for h in result.hazards if h.data_source
    ))

    return {
        "address": req.address,
        "lat": req.lat,
        "lng": req.lng,
        "run_date": date.today().isoformat(),
        "outputs": {
            **result.to_dict(),
            "narclim_summary": narclim_summary,
        },
        "confidence": overall_confidence,
        "data_sources": data_sources,
    }
