"""Composite Climate Risk Awareness Score — V1.1 (equal-weight, additive).

Methodology:
    - Each hazard is normalized to 0-1 using documented scale endpoints
    - Equal weighting (~0.167 per hazard, 6 hazards) — documented simplifying assumption
    - Composite = weighted sum x 100, clamped to 1-100
    - Interaction bonus for documented compound hazard pairs
    - Deterministic: same inputs always produce same output

Data sources (all government-authoritative):
    - Flood: spatial_overlays (NSW Planning Portal EPI layers)
    - Bushfire: spatial_overlays (NSW RFS Bushfire Prone Land)
    - Coastal hazard: spatial_overlays (SEPP Resilience & Hazards 2021)
    - Landslide: spatial_overlays (NSW Planning Portal EPI Landslide Risk)
    - Fire history: spatial_overlays (NPWS Fire History)
    - Heat trajectory: NARCliM 2.0 (AdaptNSW, 4km resolution)
    - Precipitation trend: NARCliM 2.0 (AdaptNSW)

Limitations (V1.1):
    - Equal weighting does not reflect relative loss severity per hazard
    - No property-specific vulnerability (building type, floor height, materials)
    - No adaptation offset (flood levees, bushfire mitigation works)
    - NARCliM projections are model-dependent (single GCM: ACCESS-ESM1.5)
    - Score reflects hazard exposure, not probability of loss

Version: 1.1
Date: 2026-05-18

Changelog:
    1.2 (2026-08-03): Every HazardScore carries confidence_reason (a displayed
        badge is a representation; output-grounding item 1). Bushfire no-data
        path fixed: an RFS live-fallback failure now yields available=False /
        confidence "low" / "could not be determined" instead of a confident
        "No" at "high" — the composite excludes it from the denominator, the
        same treatment _normalize_heat already gave missing NARCliM data.
    1.1 (2026-05-18): Added landslide as 6th hazard. Weights redistributed
        from 0.20x5 to ~0.167x6. Landslide data was already ingested in
        spatial_overlays but not wired into scoring.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

import logging

from services.bushfire_prescreen import _query_rfs_bfpl
from services.climate_risk_raster import query_narclim_summary, DATA_DIR, NARCLIM_FILES

logger = logging.getLogger(__name__)


# ── Configuration ─────────────────────────────────────────────────────────────

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Hazard weights (V1.1: equal at ~0.167 each = 1.0 total, 6 hazards)
WEIGHTS = {
    "flood": 0.167,
    "bushfire": 0.167,
    "coastal": 0.167,
    "fire_history": 0.167,
    "heat": 0.167,
    "landslide": 0.165,
}

# Interaction bonuses for documented compound hazard pathways
# Cite: IPCC AR6 WGII Ch11 — "climate impacts are cascading and compounding"
INTERACTION_PAIRS = {
    ("bushfire", "fire_history"): 0.05,   # Repeated fire = higher structural risk
    ("flood", "coastal"): 0.05,           # Riverine + tidal compound inundation
    ("bushfire", "heat"): 0.05,           # Heat dries vegetation → fire intensity
    ("flood", "heat"): 0.03,             # Flash flood from intense convective storms
}

# Scale endpoints for normalization (what maps to 0 and what maps to 1)
# Derived from NARCliM statewide data range, not arbitrary
HEAT_SCALE = {
    "min_delta": 0.0,    # No change from baseline = 0 risk
    "max_delta": 45.0,   # Penrith-level increase (~41 days) = near-max
}

# Precipitation: drying trend increases risk (negative delta = bad for flood flash intensity)
PRECIP_SCALE = {
    "neutral": 0.0,      # No change = no additional risk
    "max_drying": -1.0,  # mm/day reduction that maps to max precip risk component
}


# ── Types ─────────────────────────────────────────────────────────────────────

@dataclass
class HazardScore:
    """Individual hazard assessment."""
    hazard: str
    raw_score: float          # 0-1 normalized
    weight: float
    weighted_score: float     # raw_score × weight
    present: bool             # Whether any exposure detected
    detail: str               # Human-readable explanation
    confidence: str           # "high" / "medium" / "low"
    data_source: str
    available: bool = True    # False when data source unavailable (not same as no-risk)
    # Every confidence value must carry its reason — a displayed badge is a
    # representation, and a badge without a stated basis cannot be told apart
    # from a hardcoded one (granny_flat's confidence_reason pattern; output-
    # grounding item 1, 2026-08-03). Never leave this empty.
    confidence_reason: str = ""


# ── Version — ONE source of truth ─────────────────────────────────────────────
# The version was previously stated twice with two different values: this
# dataclass said methodology_version = "1.1" while the disclaimer string opened
# "Climate Risk Awareness Score v1.0". The tool card renders both on one screen
# (ClimateRiskResultCard.tsx), so a customer saw "v1.1" beside a "v1.0"
# disclaimer. Anything that needs the version reads METHODOLOGY_VERSION; the
# disclaimer is built from it, so the two cannot drift apart again.
#
# Note: docs/CLIMATE_RISK_METHODOLOGY.md carries its own "Version: 1.0" — that is
# the DOCUMENT's version and is legitimately independent of the code's.
METHODOLOGY_VERSION = "1.1"
DATA_DATE = "2026-05-18"


def build_disclaimer(version: str = METHODOLOGY_VERSION) -> str:
    """The served disclaimer, with the version interpolated from one constant."""
    return (
        f"Climate Risk Awareness Score v{version}. Based on government-authoritative "
        "spatial data and NARCliM 2.0 climate projections. This is not financial, "
        "insurance, or property advice. Does not account for property-specific "
        "construction, mitigation works, or individual vulnerability. Not a "
        "guarantee of future conditions."
    )


@dataclass
class ClimateRiskResult:
    """Complete climate risk assessment for a property.

    ``score``, ``band`` and ``interaction_bonus`` are the composite model. They
    are computed here and deliberately NOT serialised — see ``to_dict``.
    """
    score: int                          # 1-100 composite — not serialised
    band: str                           # Low/Moderate/High/Very High/Extreme — not serialised
    lat: float
    lng: float
    hazards: list[HazardScore] = field(default_factory=list)
    interaction_bonus: float = 0.0      # not serialised
    methodology_version: str = METHODOLOGY_VERSION
    data_date: str = DATA_DATE
    disclaimer: str = ""

    def __post_init__(self) -> None:
        # Derive the disclaimer from this instance's version rather than a second
        # hardcoded literal. An explicitly supplied disclaimer is left alone.
        if not self.disclaimer:
            self.disclaimer = build_disclaimer(self.methodology_version)

    def to_dict(self) -> dict:
        """Serialise for transport. Excludes the composite model deliberately.

        ``score``, ``band``, ``interaction_bonus`` and the per-hazard weight
        arithmetic (``raw_score``, ``weight``, ``weighted_score``) stay on the
        dataclass — they ARE the computation and the unit tests still assert on
        them there. They are not serialised.

        Why the exclusion lives here and not at the endpoint: the composite
        cannot be validated against any available reference (see
        ``docs/CLIMATE_RISK_METHODOLOGY.md`` → Validation status) and #699 bars it
        from every customer-facing surface. It nevertheless reached the API
        response, because ``climate_risk_pipeline`` spreads ``**to_dict()``. This
        method is the serialisation boundary, so excluding it here is what stops
        the next consumer that spreads the dict from re-opening the leak.

        Per-hazard weights go too: nothing renders them, and ``weight`` plus
        ``weighted_score`` make the composite trivially reconstructible, so
        dropping only ``score``/``band`` would be a half-measure.

        Absence is pinned by ``tests/test_climate_risk_score.py`` — if you are
        adding a field back, that test is the one telling you not to.
        """
        return {
            "lat": self.lat,
            "lng": self.lng,
            "hazards": [
                {
                    "hazard": h.hazard,
                    "present": h.present,
                    "detail": h.detail,
                    "confidence": h.confidence,
                    "confidence_reason": h.confidence_reason,
                    "data_source": h.data_source,
                    "available": h.available,
                }
                for h in self.hazards
            ],
            "methodology_version": self.methodology_version,
            "data_date": self.data_date,
            "disclaimer": self.disclaimer,
        }


# ── Score bands ───────────────────────────────────────────────────────────────

def _score_to_band(score: int) -> str:
    if score <= 20:
        return "Low"
    elif score <= 40:
        return "Moderate"
    elif score <= 60:
        return "High"
    elif score <= 80:
        return "Very High"
    else:
        return "Extreme"


# ── Spatial overlay queries ───────────────────────────────────────────────────

def _query_spatial_overlays(lat: float, lng: float) -> dict[str, list[dict]]:
    """Query PostGIS for hazard layers at a point. Returns {layer_type: [rows]}."""
    if not DATABASE_URL:
        raise EnvironmentError("DATABASE_URL not set — cannot query spatial_overlays")

    HAZARD_LAYERS = (
        "flood", "bushfire",
        "coastal_land_application", "coastal_wetlands", "littoral_rainforest",
        "coastal_environment_area", "coastal_use_area",
        "fire_history",
        "landslide",
    )

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT layer_type, value
                FROM spatial_overlays
                WHERE layer_type = ANY(%s)
                  AND ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
            """, (list(HAZARD_LAYERS), lng, lat))
            rows = cur.fetchall()
    finally:
        conn.close()

    result: dict[str, list[dict]] = {}
    for row in rows:
        result.setdefault(row["layer_type"], []).append(dict(row))
    return result


# ── Normalization functions ───────────────────────────────────────────────────

def _normalize_flood(overlays: dict[str, list[dict]]) -> HazardScore:
    """Flood: binary presence in flood planning layer."""
    hits = overlays.get("flood", [])
    present = len(hits) > 0
    raw = 1.0 if present else 0.0
    return HazardScore(
        hazard="flood",
        raw_score=raw,
        weight=WEIGHTS["flood"],
        weighted_score=raw * WEIGHTS["flood"],
        present=present,
        detail=f"Flood planning layer: {'Yes' if present else 'No'}",
        confidence="high",
        confidence_reason=(
            "Point intersects the ingested EPI flood overlay."
            if present else
            "No intersection in the ingested EPI flood overlay. Overlay "
            "ingest is geographically partial, so absence here does not "
            "distinguish unmapped-at-point from layer-not-ingested (absence "
            "census S1/S3); no secondary source disambiguates flood."
        ),
        data_source="NSW Planning Portal EPI Flood layers via spatial_overlays",
    )


def _normalize_bushfire(
    overlays: dict[str, list[dict]],
    lat: float | None = None,
    lng: float | None = None,
) -> HazardScore:
    """Bushfire: binary presence in bushfire prone land.

    Falls back to RFS BFPL live API when spatial_overlays has no bushfire data
    (historical ingest was bbox-limited to Greater Sydney). The fallback OUTCOME
    decides the confidence: an empty overlay alone cannot distinguish "not
    prone" from "not ingested here" (absence census S1/S3), so the live RFS
    check is the disambiguator — and when it fails or cannot run, nothing
    disambiguates, and the honest state is unavailable (the _normalize_heat
    shape), never a confident "No".

    Before 2026-08-03 the no-data path was `confidence="high" if hits else
    ("medium" if present else "high")` — an RFS failure was swallowed and the
    hazard served "Bushfire Prone Land: No" at "high" (output-grounding item 1;
    the DQ-36 class: a verdict about data the check never received).
    """
    hits = overlays.get("bushfire", [])
    present = len(hits) > 0
    source = "NSW RFS Bushfire Prone Land Map via spatial_overlays"

    # rfs_state: "not_needed" (overlay hit) | "prone" | "clear" | "failed" |
    # "skipped" (no coords to query with)
    rfs_state = "not_needed" if present else "skipped"
    if not present and lat is not None and lng is not None:
        try:
            rfs_result = _query_rfs_bfpl(lat, lng)
            if rfs_result and rfs_result.get("is_bushfire_prone") is True:
                present = True
                rfs_state = "prone"
                source = "NSW RFS Bushfire Prone Land Map (live API fallback)"
                logger.info(
                    "Bushfire: spatial_overlays empty, RFS live API returned prone "
                    "for (%.4f, %.4f)", lat, lng,
                )
            else:
                rfs_state = "clear"
        except Exception:
            rfs_state = "failed"
            logger.warning(
                "Bushfire RFS live API fallback failed for (%.4f, %.4f)",
                lat, lng, exc_info=True,
            )

    if rfs_state == "not_needed":
        confidence, reason, available = "high", (
            "Point intersects the ingested RFS Bushfire Prone Land overlay."
        ), True
        detail = "Bushfire Prone Land: Yes"
    elif rfs_state == "prone":
        confidence, reason, available = "medium", (
            "Live RFS point query returned prone; the point is outside our "
            "ingested overlay extent."
        ), True
        detail = "Bushfire Prone Land: Yes"
    elif rfs_state == "clear":
        confidence, reason, available = "high", (
            "Ingested overlay has no intersection and the live RFS point "
            "query agrees: not mapped as bushfire prone."
        ), True
        detail = "Bushfire Prone Land: No"
    else:  # "failed" or "skipped" — nothing disambiguates the empty overlay
        confidence, reason, available = "low", (
            "Ingested overlay has no intersection here, and the live RFS "
            "check "
            + ("failed" if rfs_state == "failed" else "could not run (no coordinates)")
            + " — bushfire exposure could not be determined (overlay ingest "
            "is geographically partial)."
        ), False
        detail = "Bushfire Prone Land: could not be determined"
        source = "NSW RFS Bushfire Prone Land Map — unavailable"

    raw = 1.0 if present else 0.0
    return HazardScore(
        hazard="bushfire",
        raw_score=raw,
        weight=WEIGHTS["bushfire"],
        weighted_score=raw * WEIGHTS["bushfire"],
        present=present,
        detail=detail,
        confidence=confidence,
        confidence_reason=reason,
        data_source=source,
        available=available,
    )


def _normalize_coastal(overlays: dict[str, list[dict]]) -> HazardScore:
    """Coastal hazard: presence in specific SEPP R&H 2021 coastal hazard layers.

    Note: coastal_land_application "Land Application" value covers all of NSW
    (jurisdictional boundary, not a hazard). Only "Subject Land" is a specific
    coastal hazard designation. Other layers (wetlands, littoral rainforest,
    environment area, use area) are genuine hazard polygons.
    """
    # Layers that are always hazard-specific (not jurisdictional)
    hazard_layers = ["coastal_wetlands", "littoral_rainforest",
                     "coastal_environment_area", "coastal_use_area"]
    hit_layers = []
    for layer in hazard_layers:
        if layer in overlays:
            hit_layers.append(layer)

    # coastal_land_application: only count "Subject Land" (specific sites),
    # NOT "Land Application" (covers all NSW)
    cla_hits = overlays.get("coastal_land_application", [])
    for hit in cla_hits:
        if hit.get("value", "").strip() == "Subject Land":
            hit_layers.append("coastal_land_application")
            break

    present = len(hit_layers) > 0
    # More coastal layers hit = higher exposure (max 1.0 at 3+ layers)
    raw = min(len(hit_layers) / 3.0, 1.0) if present else 0.0
    detail_layers = ", ".join(hit_layers) if hit_layers else "None"
    return HazardScore(
        hazard="coastal",
        raw_score=round(raw, 3),
        weight=WEIGHTS["coastal"],
        weighted_score=round(raw * WEIGHTS["coastal"], 4),
        present=present,
        detail=f"Coastal hazard layers: {detail_layers}",
        confidence="high",
        confidence_reason=(
            "Point intersects ingested SEPP R&H coastal hazard layer(s): "
            f"{detail_layers}."
            if present else
            "No intersection in the ingested SEPP R&H coastal layers; ingest "
            "is geographically partial (absence census S1/S3)."
        ),
        data_source="SEPP (Resilience and Hazards) 2021 via spatial_overlays",
    )


def _normalize_landslide(overlays: dict[str, list[dict]]) -> HazardScore:
    """Landslide: presence in EPI landslide risk layer."""
    hits = overlays.get("landslide", [])
    present = len(hits) > 0
    raw = 1.0 if present else 0.0
    return HazardScore(
        hazard="landslide",
        raw_score=raw,
        weight=WEIGHTS["landslide"],
        weighted_score=raw * WEIGHTS["landslide"],
        present=present,
        detail=f"Landslide risk area: {'Yes' if present else 'No'}",
        confidence="high",
        confidence_reason=(
            "Point intersects the ingested EPI landslide overlay."
            if present else
            "No intersection in the ingested EPI landslide overlay; ingest "
            "is geographically partial (absence census S1/S3)."
        ),
        data_source="NSW Planning Portal EPI Landslide Risk via spatial_overlays",
    )


def _normalize_fire_history(overlays: dict[str, list[dict]]) -> HazardScore:
    """Fire history: number of distinct fire events at location."""
    hits = overlays.get("fire_history", [])
    present = len(hits) > 0
    # Scale: 0 fires = 0, 1 fire = 0.3, 2 fires = 0.6, 3+ fires = 1.0
    raw = min(len(hits) * 0.3, 1.0) if present else 0.0
    return HazardScore(
        hazard="fire_history",
        raw_score=round(raw, 3),
        weight=WEIGHTS["fire_history"],
        weighted_score=round(raw * WEIGHTS["fire_history"], 4),
        present=present,
        detail=f"Historical fire events at location: {len(hits)}",
        confidence="high",
        confidence_reason=(
            f"{len(hits)} fire-history polygon(s) intersect the point in the "
            "ingested NPWS layer."
            if present else
            "No fire-history intersection in the ingested NPWS layer; ingest "
            "is geographically partial (absence census S1/S3)."
        ),
        data_source="NPWS Fire History via spatial_overlays",
    )


def _normalize_heat(narclim_summary: dict) -> HazardScore:
    """Heat trajectory: NARCliM hot days delta from baseline to 2090 (worst scenario)."""
    delta = narclim_summary.get("hot_days_delta_2090")
    if delta is None:
        # NARCliM data not available (outside domain or files missing)
        return HazardScore(
            hazard="heat",
            raw_score=0.0,
            weight=WEIGHTS["heat"],
            weighted_score=0.0,
            present=False,
            detail="NARCliM data not available for this location",
            confidence="low",
            confidence_reason=(
                "NARCliM raster returned no value — outside the model domain "
                "or grid files not present; heat trajectory could not be "
                "determined."
            ),
            data_source="NARCliM 2.0 (AdaptNSW) — unavailable",
            available=False,
        )

    # Normalize: 0 delta = 0, max_delta = 1.0
    raw = max(0.0, min(delta / HEAT_SCALE["max_delta"], 1.0))
    baseline = narclim_summary.get("hot_days_baseline", "?")
    late = narclim_summary.get("hot_days_late_century_high", "?")
    return HazardScore(
        hazard="heat",
        raw_score=round(raw, 3),
        weight=WEIGHTS["heat"],
        weighted_score=round(raw * WEIGHTS["heat"], 4),
        present=delta > 0,
        detail=f"Hot days (>=35°C): {baseline}/yr baseline → {late}/yr by 2090 (SSP3-7.0), Δ={delta:+.1f} days",
        confidence="medium",
        confidence_reason=(
            "Value read from the NARCliM 2.0 projection raster — a single-GCM "
            "model projection, not an observation."
        ),
        data_source="NARCliM 2.0 (AdaptNSW), ACCESS-ESM1.5, SSP3-7.0, 4km resolution",
    )


# ── Interaction bonus ─────────────────────────────────────────────────────────

def _compute_interaction_bonus(hazards: list[HazardScore]) -> float:
    """Add bonus for documented compound hazard pathways."""
    present_hazards = {h.hazard for h in hazards if h.present}
    bonus = 0.0
    for (h1, h2), value in INTERACTION_PAIRS.items():
        if h1 in present_hazards and h2 in present_hazards:
            bonus += value
    return round(bonus, 3)


# ── Main entry point ──────────────────────────────────────────────────────────

def climate_risk_score(lat: float, lng: float) -> ClimateRiskResult:
    """Compute composite climate risk awareness score for a property.

    Args:
        lat: Latitude (WGS84)
        lng: Longitude (WGS84)

    Returns:
        ClimateRiskResult with composite score, band, per-hazard breakdown.
    """
    # 1. Query spatial overlays
    overlays = _query_spatial_overlays(lat, lng)

    # 2. Query NARCliM rasters
    narclim = {}
    try:
        narclim = query_narclim_summary(lat, lng)
    except (ValueError, FileNotFoundError):
        pass  # Outside domain or files not present — heat score will be 0

    # 3. Normalize each hazard
    hazards = [
        _normalize_flood(overlays),
        _normalize_bushfire(overlays, lat=lat, lng=lng),
        _normalize_coastal(overlays),
        _normalize_landslide(overlays),
        _normalize_fire_history(overlays),
        _normalize_heat(narclim),
    ]

    # 4. Compute composite — exclude unavailable hazards from denominator
    #    Unavailable = data source missing (not same as "queried, no risk").
    #    Rescale so available hazards span the full 0-1 range.
    available_hazards = [h for h in hazards if h.available]
    if available_hazards:
        total_available_weight = sum(h.weight for h in available_hazards)
        weighted_sum = sum(h.weighted_score for h in available_hazards)
        # Rescale: e.g. 5 of 6 hazards → total_weight=0.835, scale by 1/0.835
        if total_available_weight > 0:
            weighted_sum = weighted_sum / total_available_weight
    else:
        weighted_sum = 0.0
    interaction = _compute_interaction_bonus(hazards)
    raw_composite = weighted_sum + interaction

    # 5. Scale to 1-100 (clamped)
    score = max(1, min(100, round(raw_composite * 100)))

    return ClimateRiskResult(
        score=score,
        band=_score_to_band(score),
        lat=lat,
        lng=lng,
        hazards=hazards,
        interaction_bonus=interaction,
    )


# ── CLI test (requires DATABASE_URL) ─────────────────────────────────────────

if __name__ == "__main__":
    import json
    import sys

    test_lat = float(sys.argv[1]) if len(sys.argv) > 1 else -33.8688
    test_lng = float(sys.argv[2]) if len(sys.argv) > 2 else 151.2093

    print(f"Climate Risk Score for ({test_lat}, {test_lng})\n")
    result = climate_risk_score(test_lat, test_lng)
    print(json.dumps(result.to_dict(), indent=2))
