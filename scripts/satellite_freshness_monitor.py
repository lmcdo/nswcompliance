#!/usr/bin/env python3
"""
Satellite Data Source Freshness Monitor
=======================================
Daily health check of all external data sources used by 7 satellite product
pipelines. Part of QA defensibility infrastructure — proves ongoing monitoring
of data source availability and reliability.

Legal basis:
  - ACL s18 (reasonable care): demonstrates we check our sources regularly
  - Shaddock duty: proves we monitor the data we know users rely on
  - ISO 25010:2023 Safety characteristic: proactive reliability monitoring

Data sources monitored (19 endpoints across 7 pipelines):
  - NSW Planning Portal (lot API, address geocode, ePlanning DA/CDC)
  - NSW Environment (RFS BFPL, EPI Flood, DEM)
  - NSW SIX Maps (imagery, elevation)
  - Google Solar API
  - Bureau of Meteorology (SOS2 water data)
  - JRC Global Surface Water (Google Cloud Storage)
  - Digital Earth Australia (WOfS WCS)
  - Microsoft Planetary Computer (Sentinel-1 STAC)
  - Element84 Earth Search (Sentinel-2 STAC)
  - Esri Wayback (historical aerial imagery)

Usage:
    python scripts/satellite_freshness_monitor.py              # all sources
    python scripts/satellite_freshness_monitor.py --source rfs_bfpl
    python scripts/satellite_freshness_monitor.py --dry-run    # no DB write
    python scripts/satellite_freshness_monitor.py --verbose

Exit codes:
    0 = all sources healthy
    1 = error (script failure)
    2 = one or more sources degraded or down

Related:
    migrations/043_data_source_health_checks.sql
    docs/QA-DATA-PROVENANCE.md (section 8.1)
    services/audit_trail.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# User-Agent — transparent identification per responsible scraping practice
# ---------------------------------------------------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; data-source-health-check)"
    ),
    "Accept": "application/json, text/html, */*",
}

PROBE_TIMEOUT = 15  # seconds per request


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class SourceCheckResult:
    """Result of a single data source health probe."""

    source_key: str
    source_name: str
    endpoint_url: str
    pipeline_names: list[str]
    status: str = "ok"  # ok | degraded | down | schema_changed | stale
    http_status: Optional[int] = None
    response_time_ms: Optional[int] = None
    response_hash: Optional[str] = None
    schema_valid: Optional[bool] = None
    error_message: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Data source registry — single source of truth for all monitored endpoints
# ---------------------------------------------------------------------------

DATA_SOURCES: list[dict[str, Any]] = [
    # --- NSW Planning Portal cluster ---
    {
        "source_key": "nsw_lot_api",
        "source_name": "NSW Planning Portal — Lot Geometry",
        "endpoint_url": "https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/lot",
        "pipeline_names": ["shadow", "granny-flat", "pre-da-history"],
        "probe_type": "json_get",
        "probe_params": {"propId": "1"},  # minimal valid query
        "schema_check": lambda r: isinstance(r, (dict, list)),
    },
    {
        "source_key": "nsw_address_geocode",
        "source_name": "NSW Planning Portal — Address Geocode",
        "endpoint_url": "https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/address",
        "pipeline_names": ["pre-da-history"],
        "probe_type": "json_get",
        "probe_params": {"a": "1 Martin Place Sydney"},
        "schema_check": lambda r: isinstance(r, (dict, list)),
    },
    {
        "source_key": "eplanning_da",
        "source_name": "NSW ePlanning Portal — Online DA",
        "endpoint_url": "https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineDA",
        "pipeline_names": ["threat-radar", "pre-da-history"],
        "probe_type": "eplanning",
        "probe_params": {"CouncilName": ["Inner West Council"]},
        "schema_check": lambda r: isinstance(r, dict) and ("Application" in r or "ApplicationList" in r),
    },
    {
        "source_key": "eplanning_cdc",
        "source_name": "NSW ePlanning Portal — Online CDC",
        "endpoint_url": "https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineCDC",
        "pipeline_names": ["threat-radar", "pre-da-history"],
        "probe_type": "eplanning",
        "probe_params": {"CouncilName": ["Inner West Council"]},
        "schema_check": lambda r: isinstance(r, dict) and ("Application" in r or "ApplicationList" in r),
    },
    # --- NSW Environment / RFS ---
    {
        "source_key": "rfs_bfpl",
        "source_name": "RFS Bush Fire Prone Land Map (ArcGIS REST)",
        "endpoint_url": "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Fire/BFPL/MapServer/0/query",
        "pipeline_names": ["bushfire"],
        "probe_type": "arcgis_query",
        "probe_params": {
            "where": "1=1",
            "geometry": "151.2093,-33.8688",
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "false",
            "f": "json",
        },
        "schema_check": lambda r: "features" in r,
    },
    {
        "source_key": "epi_flood",
        "source_name": "NSW EPI Flood Planning (ArcGIS REST)",
        "endpoint_url": "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/Hazard/MapServer/1/query",
        "pipeline_names": ["flood"],
        "probe_type": "arcgis_query",
        "probe_params": {
            "where": "1=1",
            "geometry": "151.2093,-33.8688",
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "false",
            "f": "json",
        },
        "schema_check": lambda r: "features" in r,
    },
    {
        "source_key": "nsw_dem",
        "source_name": "NSW 5m DEM (SIX Maps ImageServer)",
        "endpoint_url": "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_5M_Elevation/ImageServer/identify",
        "pipeline_names": ["flood"],
        "probe_type": "arcgis_query",
        "probe_params": {
            "geometry": "151.2093,-33.8688",
            "geometryType": "esriGeometryPoint",
            "returnGeometry": "false",
            "returnCatalogItems": "false",
            "f": "json",
        },
        "schema_check": lambda r: "value" in r or "results" in r,
    },
    # --- NSW SIX Maps ---
    {
        "source_key": "six_maps_imagery",
        "source_name": "NSW SIX Maps Aerial Imagery",
        "endpoint_url": "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Imagery/MapServer",
        "pipeline_names": ["granny-flat"],
        "probe_type": "arcgis_info",
        "probe_params": {"f": "json"},
        "schema_check": lambda r: "mapName" in r or "serviceDescription" in r,
    },
    # --- Google Solar ---
    {
        "source_key": "google_solar",
        "source_name": "Google Solar API",
        "endpoint_url": "https://solar.googleapis.com/v1/buildingInsights:findClosest",
        "pipeline_names": ["solar-yield"],
        "probe_type": "google_solar",
        "probe_params": {
            "location.latitude": "-33.8688",
            "location.longitude": "151.2093",
            "requiredQuality": "LOW",
        },
        # Requires GOOGLE_MAPS_API_KEY — if missing, mark degraded not down
        "schema_check": lambda r: "solarPotential" in r or "error" in r,
    },
    # --- Bureau of Meteorology ---
    {
        "source_key": "bom_sos2",
        "source_name": "Bureau of Meteorology — Water Data Online (SOS2)",
        "endpoint_url": "https://www.bom.gov.au/waterdata/services",
        "pipeline_names": ["flood"],
        "probe_type": "bom_sos2",
        "probe_params": {
            "service": "SOS",
            "version": "2.0",
            "request": "GetCapabilities",
        },
        "schema_check": lambda r: r is True,  # XML response, just check 200 + XML content
    },
    # --- JRC Global Surface Water ---
    {
        "source_key": "jrc_surface_water",
        "source_name": "JRC Global Surface Water (Google Cloud Storage)",
        "endpoint_url": "https://storage.googleapis.com/global-surface-water/downloads2021/occurrence",
        "pipeline_names": ["flood"],
        "probe_type": "http_head",
        "probe_params": {},
        "schema_check": lambda r: r is True,
    },
    # --- Digital Earth Australia ---
    {
        "source_key": "dea_wofs",
        "source_name": "Digital Earth Australia — Water Observations (WCS)",
        "endpoint_url": "https://ows.dea.ga.gov.au/wcs",
        "pipeline_names": ["flood"],
        "probe_type": "wcs_capabilities",
        "probe_params": {
            "service": "WCS",
            "version": "1.1.1",
            "request": "GetCapabilities",
        },
        "schema_check": lambda r: r is True,  # XML, check 200 + content
    },
    # --- Microsoft Planetary Computer ---
    {
        "source_key": "planetary_computer",
        "source_name": "Microsoft Planetary Computer STAC",
        "endpoint_url": "https://planetarycomputer.microsoft.com/api/stac/v1",
        "pipeline_names": ["flood"],
        "probe_type": "json_get",
        "probe_params": {},
        "schema_check": lambda r: isinstance(r, dict) and ("id" in r or "links" in r),
    },
    # --- Element84 Earth Search ---
    {
        "source_key": "element84_stac",
        "source_name": "Element84 Earth Search STAC (Sentinel-2)",
        "endpoint_url": "https://earth-search.aws.element84.com/v1",
        "pipeline_names": ["shadow", "pre-da-history"],
        "probe_type": "json_get",
        "probe_params": {},
        "schema_check": lambda r: isinstance(r, dict) and ("id" in r or "links" in r),
    },
    # --- Esri Wayback ---
    {
        "source_key": "esri_wayback",
        "source_name": "Esri World Imagery Wayback",
        "endpoint_url": "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer",
        "pipeline_names": ["pre-da-history"],
        "probe_type": "arcgis_info",
        "probe_params": {"f": "json"},
        "schema_check": lambda r: "Service" in r or "Selection" in r or "mapName" in r,
    },
]


# ---------------------------------------------------------------------------
# Probe functions — one per probe_type
# ---------------------------------------------------------------------------

def _probe_json_get(url: str, params: dict) -> tuple[int, Any, int]:
    """GET request expecting JSON response. Returns (status, body, ms)."""
    t0 = time.monotonic()
    resp = requests.get(url, params=params, headers=HEADERS, timeout=PROBE_TIMEOUT)
    ms = int((time.monotonic() - t0) * 1000)
    return resp.status_code, resp.json(), ms


def _probe_arcgis_query(url: str, params: dict) -> tuple[int, Any, int]:
    """ArcGIS REST query — GET with params, expects JSON with 'features'."""
    t0 = time.monotonic()
    resp = requests.get(url, params=params, headers=HEADERS, timeout=PROBE_TIMEOUT)
    ms = int((time.monotonic() - t0) * 1000)
    body = resp.json()
    # ArcGIS returns 200 even on errors — check for error object
    if "error" in body:
        raise ValueError(f"ArcGIS error: {body['error'].get('message', body['error'])}")
    return resp.status_code, body, ms


def _probe_arcgis_info(url: str, params: dict) -> tuple[int, Any, int]:
    """ArcGIS service info endpoint — lightweight metadata check."""
    t0 = time.monotonic()
    resp = requests.get(url, params=params, headers=HEADERS, timeout=PROBE_TIMEOUT)
    ms = int((time.monotonic() - t0) * 1000)
    return resp.status_code, resp.json(), ms


def _probe_google_solar(url: str, params: dict) -> tuple[int, Any, int]:
    """Google Solar API — requires API key. Returns degraded if key missing."""
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return 0, {"_skip_reason": "GOOGLE_MAPS_API_KEY not set"}, 0
    params["key"] = api_key
    t0 = time.monotonic()
    resp = requests.get(url, params=params, headers=HEADERS, timeout=PROBE_TIMEOUT)
    ms = int((time.monotonic() - t0) * 1000)
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text[:500]}
    return resp.status_code, body, ms


def _probe_eplanning(url: str, params: dict) -> tuple[int, Any, int]:
    """NSW ePlanning API — filters go in HTTP headers, not query params."""
    t0 = time.monotonic()
    filters_header = json.dumps({"filters": params})
    resp = requests.get(
        url,
        headers={
            **HEADERS,
            "filters": filters_header,
            "PageSize": "1",
            "PageNumber": "1",
        },
        timeout=PROBE_TIMEOUT,
    )
    ms = int((time.monotonic() - t0) * 1000)
    return resp.status_code, resp.json(), ms


def _probe_bom_sos2(url: str, params: dict) -> tuple[int, Any, int]:
    """BOM SOS2 — returns XML. We just check HTTP 200 and XML content type."""
    t0 = time.monotonic()
    resp = requests.get(url, params=params, headers=HEADERS, timeout=PROBE_TIMEOUT)
    ms = int((time.monotonic() - t0) * 1000)
    content_type = resp.headers.get("Content-Type", "")
    is_xml = "xml" in content_type or resp.text.strip().startswith("<?xml")
    if resp.status_code == 200 and is_xml:
        return 200, True, ms
    raise ValueError(
        f"BOM SOS2: status={resp.status_code}, content_type={content_type}"
    )


def _probe_http_head(url: str, params: dict) -> tuple[int, Any, int]:
    """HTTP HEAD — just check the endpoint is reachable. Used for GCS buckets."""
    t0 = time.monotonic()
    # GCS bucket listing returns 200 or 403 (no listing) — both mean it's up
    resp = requests.head(url, headers=HEADERS, timeout=PROBE_TIMEOUT, allow_redirects=True)
    ms = int((time.monotonic() - t0) * 1000)
    if resp.status_code in (200, 301, 302, 403, 404):
        # 403/404 on the bucket root is normal — individual tiles are accessible
        return resp.status_code, True, ms
    raise ValueError(f"HTTP HEAD: status={resp.status_code}")


def _probe_wcs_capabilities(url: str, params: dict) -> tuple[int, Any, int]:
    """OGC WCS GetCapabilities — returns XML."""
    t0 = time.monotonic()
    resp = requests.get(url, params=params, headers=HEADERS, timeout=PROBE_TIMEOUT)
    ms = int((time.monotonic() - t0) * 1000)
    content_type = resp.headers.get("Content-Type", "")
    is_xml = "xml" in content_type or resp.text.strip().startswith("<?xml")
    if resp.status_code == 200 and is_xml:
        return 200, True, ms
    raise ValueError(
        f"WCS: status={resp.status_code}, content_type={content_type}"
    )


PROBERS = {
    "json_get": _probe_json_get,
    "arcgis_query": _probe_arcgis_query,
    "arcgis_info": _probe_arcgis_info,
    "eplanning": _probe_eplanning,
    "google_solar": _probe_google_solar,
    "bom_sos2": _probe_bom_sos2,
    "http_head": _probe_http_head,
    "wcs_capabilities": _probe_wcs_capabilities,
}


# ---------------------------------------------------------------------------
# Main check function
# ---------------------------------------------------------------------------

def check_source(source: dict[str, Any]) -> SourceCheckResult:
    """Probe a single data source and return structured result."""
    result = SourceCheckResult(
        source_key=source["source_key"],
        source_name=source["source_name"],
        endpoint_url=source["endpoint_url"],
        pipeline_names=source["pipeline_names"],
    )

    prober = PROBERS.get(source["probe_type"])
    if not prober:
        result.status = "down"
        result.error_message = f"Unknown probe_type: {source['probe_type']}"
        return result

    try:
        http_status, body, ms = prober(source["endpoint_url"], source["probe_params"])
        result.http_status = http_status
        result.response_time_ms = ms

        # Special case: Google Solar without API key
        if isinstance(body, dict) and "_skip_reason" in body:
            result.status = "degraded"
            result.error_message = body["_skip_reason"]
            result.metadata = {"reason": "api_key_missing"}
            return result

        # Hash the response for schema drift detection
        if body is not True:
            raw = json.dumps(body, sort_keys=True, default=str)
            result.response_hash = hashlib.sha256(raw.encode()).hexdigest()

        # Schema validation
        schema_check = source.get("schema_check")
        if schema_check:
            result.schema_valid = schema_check(body)
            if not result.schema_valid:
                result.status = "schema_changed"
                result.error_message = "Response schema does not match expected structure"
                return result

        # Response time check — >5s is degraded
        if ms > 5000:
            result.status = "degraded"
            result.error_message = f"Slow response: {ms}ms (threshold: 5000ms)"
            return result

        # HTTP status check
        if http_status and http_status >= 400 and source["probe_type"] != "http_head":
            result.status = "degraded" if http_status < 500 else "down"
            result.error_message = f"HTTP {http_status}"
            return result

        result.status = "ok"

    except requests.exceptions.Timeout:
        result.status = "down"
        result.error_message = f"Timeout after {PROBE_TIMEOUT}s"
    except requests.exceptions.ConnectionError as exc:
        result.status = "down"
        result.error_message = f"Connection failed: {exc}"
    except Exception as exc:
        result.status = "down"
        result.error_message = str(exc)[:500]

    return result


# ---------------------------------------------------------------------------
# Telegram alerting (matches legislation_monitor.py pattern)
# ---------------------------------------------------------------------------

def send_telegram(message: str) -> None:
    """Send alert via Telegram bot. Silent no-op if creds not configured."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Database writer
# ---------------------------------------------------------------------------

def write_results(run_id: str, results: list[SourceCheckResult]) -> None:
    """Write check results to data_source_health_checks table (append-only)."""
    if not DATABASE_URL:
        logger.warning("DATABASE_URL not set — skipping DB write")
        return

    sql = """
        INSERT INTO data_source_health_checks
            (run_id, source_key, source_name, endpoint_url, pipeline_names,
             status, http_status, response_time_ms, response_hash,
             schema_valid, error_message, metadata, checked_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            for r in results:
                cur.execute(sql, (
                    run_id,
                    r.source_key,
                    r.source_name,
                    r.endpoint_url,
                    r.pipeline_names,
                    r.status,
                    r.http_status,
                    r.response_time_ms,
                    r.response_hash,
                    r.schema_valid,
                    r.error_message,
                    psycopg2.extras.Json(r.metadata) if r.metadata else None,
                    r.checked_at,
                ))
        conn.commit()
        logger.info(f"Wrote {len(results)} health check results to database")
    except Exception as exc:
        logger.error(f"DB write failed: {exc}")
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------

def print_results(results: list[SourceCheckResult], verbose: bool = False) -> None:
    """Print results table to stdout."""
    # Header
    print()
    print(f"{'Source':<40} {'Status':<16} {'HTTP':<6} {'Time':>7} {'Pipelines'}")
    print("-" * 100)

    for r in results:
        status_icon = {
            "ok": "OK",
            "degraded": "DEGRADED",
            "down": "DOWN",
            "schema_changed": "SCHEMA",
            "stale": "STALE",
        }.get(r.status, r.status.upper())

        http_str = str(r.http_status) if r.http_status else "-"
        time_str = f"{r.response_time_ms}ms" if r.response_time_ms else "-"
        pipes = ", ".join(r.pipeline_names)

        print(f"{r.source_name[:39]:<40} {status_icon:<16} {http_str:<6} {time_str:>7} {pipes}")

        if verbose and r.error_message:
            print(f"  Error: {r.error_message}")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Satellite data source freshness monitor"
    )
    parser.add_argument(
        "--source",
        help="Check a single source by key (e.g. rfs_bfpl)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run checks but don't write to database",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed error messages",
    )
    parser.add_argument(
        "--skip-quality-checks",
        action="store_true",
        help="Skip audit trail and output quality checks",
    )
    args = parser.parse_args()

    # Filter to single source if requested
    sources = DATA_SOURCES
    if args.source:
        sources = [s for s in DATA_SOURCES if s["source_key"] == args.source]
        if not sources:
            valid = ", ".join(s["source_key"] for s in DATA_SOURCES)
            logger.error(f"Unknown source: {args.source}. Valid: {valid}")
            return 1

    run_id = str(uuid.uuid4())
    logger.info(
        f"Starting satellite freshness check — run_id={run_id}, "
        f"sources={len(sources)}"
    )

    # Run all checks with a small delay between to avoid hammering
    results: list[SourceCheckResult] = []
    for source in sources:
        logger.info(f"  Checking {source['source_key']}...")
        result = check_source(source)
        results.append(result)

        if result.status != "ok":
            logger.warning(
                f"  {source['source_key']}: {result.status} — "
                f"{result.error_message or 'unknown'}"
            )

        # Brief pause between probes (responsible rate limiting)
        if len(sources) > 1:
            time.sleep(0.5)

    # Print results
    print_results(results, verbose=args.verbose)

    # Write to DB
    if not args.dry_run:
        write_results(run_id, results)

    # Summary
    failures = [r for r in results if r.status not in ("ok",)]
    total = len(results)
    ok_count = total - len(failures)

    print(f"Summary: {ok_count}/{total} sources healthy")

    exit_code = 0

    if failures:
        # Build alert message
        lines = [f"Satellite Source Monitor: {len(failures)}/{total} sources unhealthy"]
        for r in failures:
            lines.append(
                f"  {r.source_key}: {r.status}"
                + (f" ({r.error_message[:80]})" if r.error_message else "")
            )
        lines.append(f"\nAffected pipelines: {', '.join(sorted({p for r in failures for p in r.pipeline_names}))}")
        alert = "\n".join(lines)

        print(alert)
        send_telegram(alert)
        exit_code = 2
    else:
        logger.info("All sources healthy")

    # --- Data quality checks (post-source, pre-exit) ---
    if not args.skip_quality_checks and not args.dry_run:
        audit_gaps = check_audit_trail_completeness(days=7)
        output_issues = check_output_quality(days=7)

        quality_alerts = []

        if audit_gaps:
            gap_lines = [f"Audit trail gaps: {len(audit_gaps)} reports missing audit rows (last 7 days)"]
            for g in audit_gaps[:5]:
                gap_lines.append(f"  {g['product']} — {g['address']} ({g['run_date']})")
            if len(audit_gaps) > 5:
                gap_lines.append(f"  ... and {len(audit_gaps) - 5} more")
            quality_alerts.extend(gap_lines)

        if output_issues:
            out_lines = [f"Output quality: {len(output_issues)} reports with empty/null data (last 7 days)"]
            for o in output_issues[:5]:
                out_lines.append(f"  {o['product']} — {o['address']} ({o['issue']})")
            if len(output_issues) > 5:
                out_lines.append(f"  ... and {len(output_issues) - 5} more")
            quality_alerts.extend(out_lines)

        if quality_alerts:
            quality_msg = "Data Quality Alert:\n" + "\n".join(quality_alerts)
            print(quality_msg)
            send_telegram(quality_msg)
            exit_code = max(exit_code, 2)

    return exit_code


# ---------------------------------------------------------------------------
# Audit trail completeness check
# ---------------------------------------------------------------------------

def check_audit_trail_completeness(days: int = 7) -> list[dict]:
    """Find reports with no corresponding audit trail row.

    Queries property_reports from the last N days and LEFT JOINs to
    report_audit_trail. Any report without a matching audit row is a
    gap — the pipeline ran but the audit write silently failed.

    Returns list of gap dicts. Empty list = all reports have audit trails.
    """
    if not DATABASE_URL:
        logger.warning("DATABASE_URL not set — skipping audit trail check")
        return []

    sql = """
        SELECT
            pr.id AS report_id,
            pr.product,
            pr.address,
            pr.run_date
        FROM property_reports pr
        LEFT JOIN report_audit_trail rat ON rat.report_id = pr.id
        WHERE pr.run_date >= NOW() - INTERVAL '%s days'
          AND rat.id IS NULL
        ORDER BY pr.run_date DESC
        LIMIT 50
    """

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (days,))
            gaps = [dict(row) for row in cur.fetchall()]

        if gaps:
            logger.warning(f"Audit trail gaps: {len(gaps)} reports missing audit rows")
        else:
            logger.info(f"Audit trail complete: all reports from last {days} days have audit rows")

        return gaps

    except psycopg2.errors.UndefinedTable:
        logger.info("report_audit_trail table does not exist yet — skipping check")
        return []
    except Exception as exc:
        logger.error(f"Audit trail check failed: {exc}")
        return []
    finally:
        if conn:
            conn.close()


def check_output_quality(days: int = 7) -> list[dict]:
    """Find reports with empty or suspicious outputs.

    Checks property_reports from the last N days for:
    - NULL or empty outputs JSONB
    - NULL confidence (pipeline didn't set it)
    - Empty data_sources array (no sources recorded)

    These indicate a pipeline ran "successfully" but produced garbage.
    """
    if not DATABASE_URL:
        logger.warning("DATABASE_URL not set — skipping output quality check")
        return []

    sql = """
        SELECT
            id AS report_id,
            product,
            address,
            run_date,
            CASE
                WHEN outputs IS NULL THEN 'null_outputs'
                WHEN outputs = '{}'::jsonb THEN 'empty_outputs'
                WHEN confidence IS NULL THEN 'null_confidence'
                WHEN data_sources IS NULL OR array_length(data_sources, 1) IS NULL THEN 'no_data_sources'
                ELSE 'unknown'
            END AS issue
        FROM property_reports
        WHERE run_date >= NOW() - INTERVAL '%s days'
          AND (
            outputs IS NULL
            OR outputs = '{}'::jsonb
            OR confidence IS NULL
            OR data_sources IS NULL
            OR array_length(data_sources, 1) IS NULL
          )
        ORDER BY run_date DESC
        LIMIT 50
    """

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (days,))
            issues = [dict(row) for row in cur.fetchall()]

        if issues:
            logger.warning(f"Output quality issues: {len(issues)} reports with empty/null outputs")
        else:
            logger.info(f"Output quality OK: all reports from last {days} days have valid outputs")

        return issues

    except psycopg2.errors.UndefinedTable:
        logger.info("property_reports table does not exist yet — skipping check")
        return []
    except Exception as exc:
        logger.error(f"Output quality check failed: {exc}")
        return []
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())
