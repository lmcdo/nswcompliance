#!/usr/bin/env python3
"""
FastAPI HTTP Server for Enhanced Compliance API
Wraps the existing enhanced_compliance_api.py for reliable Node.js access
"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
try:
    from services.solar_yield import router as solar_yield_router  # Docker (PYTHONPATH=/app)
    from services.shadow_detector import router as shadow_router
    from services.threat_radar import router as threat_radar_router
    from services.flood_truth import router as flood_router
    from services.granny_flat import router as granny_flat_router
    from services.lec_collector import router as lec_router
    from services.drawdown_verify import router as drawdown_verify_router
    from services.rss_proxy import router as rss_proxy_router
    from services.pre_da_history import router as pre_da_history_router
    from services.bushfire_prescreen import router as bushfire_router
    from services.conveyancing import router as conveyancing_router
    from services.climate_risk_pipeline import router as climate_risk_router
    from services.intelligence_brief import router as intelligence_brief_router
    from services.terrain_analysis import router as terrain_router
    from services.constraint_arithmetic import router as constraint_arithmetic_router
    from services.lot_search import router as lot_search_router
    from services.upzoning_check import router as upzoning_router
    from services.brief_overlay_api import router as brief_overlay_router
    from services.cdc_screen_api import router as cdc_screen_router
    from services.dcp_controls_api import router as dcp_controls_router
except ImportError:
    from solar_yield import router as solar_yield_router  # Local (run from services/)
    from shadow_detector import router as shadow_router
    from threat_radar import router as threat_radar_router
    from flood_truth import router as flood_router
    from granny_flat import router as granny_flat_router
    from lec_collector import router as lec_router
    from drawdown_verify import router as drawdown_verify_router
    from rss_proxy import router as rss_proxy_router
    from pre_da_history import router as pre_da_history_router
    from bushfire_prescreen import router as bushfire_router
    from conveyancing import router as conveyancing_router
    from climate_risk_pipeline import router as climate_risk_router
    from intelligence_brief import router as intelligence_brief_router
    from terrain_analysis import router as terrain_router
    from constraint_arithmetic import router as constraint_arithmetic_router
    from lot_search import router as lot_search_router
    from upzoning_check import router as upzoning_router
    from brief_overlay_api import router as brief_overlay_router
    from cdc_screen_api import router as cdc_screen_router
    from dcp_controls_api import router as dcp_controls_router

app = FastAPI(title="NSW Compliance API", version="1.0.0")

# CORS — allow localhost in dev, production Vercel origin in prod.
# Set ALLOWED_ORIGINS on Railway as a comma-separated list, e.g.:
#   https://your-app.vercel.app,https://verify.yourdomain.com
_default_origins = "http://localhost:3000,http://localhost:3003,http://localhost:3007"
_allowed_origins = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Satellite pipeline routes
app.include_router(solar_yield_router)
app.include_router(shadow_router)
app.include_router(threat_radar_router)
app.include_router(flood_router)
app.include_router(granny_flat_router)
app.include_router(lec_router)
app.include_router(drawdown_verify_router)
app.include_router(rss_proxy_router)
app.include_router(pre_da_history_router)
app.include_router(bushfire_router)
app.include_router(conveyancing_router)
app.include_router(climate_risk_router)
app.include_router(intelligence_brief_router)
app.include_router(terrain_router)
app.include_router(constraint_arithmetic_router)
app.include_router(lot_search_router)
app.include_router(upzoning_router)
app.include_router(brief_overlay_router)
app.include_router(cdc_screen_router)
app.include_router(dcp_controls_router)

# /compliance (EnhancedComplianceAPI, basix_compliance_checker.py,
# special_provisions_processor.py) was removed 2026-09-05: it queried
# basix_provisions / sepp_provisions / special_provisions_registry, none of
# which have ever existed in the database. Every real call to it either
# fabricated a plausible-looking "BASIX requirements apply" result with a
# hardcoded 90% confidence, or silently dropped hazard/heritage/SEPP checks
# with no error -- CLAUDE.md's own CRITICAL data-integrity rule, on a live,
# unauthenticated page (/authoritative, also removed). No path to a real fix
# existed without sourcing real BASIX/SEPP regulatory data, which is a much
# larger, separate undertaking -- deleted rather than left fabricating.
# See fix/fabricated-compliance-fallback.

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "NSW Compliance API"}

@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "service": "NSW Planning Compliance API",
        "version": "1.0.0",
        "endpoints": {
            "POST /pipeline/solar-yield": "Satellite: Solar Yield Underwriter pipeline",
            "POST /pipeline/shadow": "Satellite: Shadow Detector pipeline",
            "POST /pipeline/threat-radar/subscribe": "Satellite: Threat Radar — subscribe address",
            "POST /pipeline/threat-radar/check": "Satellite: Threat Radar — run weekly check",
            "GET /pipeline/threat-radar/subscriptions": "Satellite: Threat Radar — list active subscriptions",
            "POST /pipeline/flood": "Satellite: Flood Truth — on-demand EPI + SAR check",
            "POST /pipeline/flood/batch": "Satellite: Flood Truth — batch LGA processing (cron)",
            "POST /pipeline/granny-flat/detect": "Satellite: Granny Flat — detect structures",
            "POST /pipeline/granny-flat/confirm": "Satellite: Granny Flat — confirm and calculate yield",
            "POST /pipeline/bushfire": "Satellite: Bushfire Pre-Screen — RFS BFPL + PostGIS overlays",
            "POST /pipeline/conveyancing": "Satellite: Conveyancing Planning Disclosure — LEP controls, overlays, feasibility",
            "POST /pipeline/conveyancing/pdf": "Satellite: Conveyancing — generate full PDF report (paid tier)",
            "POST /pipeline/climate-risk": "Climate Risk — composite score (flood + bushfire + coastal + fire history + NARCliM heat)",
            "GET /health": "Health check",
            "GET /docs": "API documentation"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("Starting NSW Compliance API Server...")
    print("API Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    uvicorn.run(app, host="0.0.0.0", port=8000)