#!/usr/bin/env python3
"""
Precompute Amenity Cache — populates precinct_amenity_cache table.

For each precinct in dcp_precinct_boundaries, computes centroid and calls
the city2graph /amenity endpoint, storing the result in precinct_amenity_cache.

Avoids 10-15s live Overpass API calls at query time for supported LGAs.

Usage:
    # Dry run — show what would be computed, no writes
    python enrichment/precompute_amenity.py --dry-run

    # Full run — all precincts
    python enrichment/precompute_amenity.py

    # Single council
    python enrichment/precompute_amenity.py --council leichhardt

    # Force refresh stale entries (>90 days old)
    python enrichment/precompute_amenity.py --refresh-stale

    # Single precinct for testing
    python enrichment/precompute_amenity.py --precinct-id C2.2.1.1
"""

import argparse
import json
import logging
import os
import time

import psycopg2
import requests
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SPATIAL_API_URL = os.getenv("SPATIAL_API_URL", "https://city2graph-production.up.railway.app")
AMENITY_TIMEOUT_S = 90       # per-request timeout — Overpass API can be slow under load
INTER_REQUEST_SLEEP_S = 3    # courtesy delay between Overpass calls
STALE_DAYS = 90


def get_connection():
    return psycopg2.connect(os.getenv("SUPABASE_DB_URL"))


def fetch_precincts(conn, council: str | None = None) -> list[dict]:
    """Return precincts with pre-computed centroids from PostGIS geometry column."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if council:
            cur.execute(
                """
                SELECT precinct_id, former_council,
                       ST_Y(centroid) AS centroid_lat,
                       ST_X(centroid) AS centroid_lng
                FROM dcp_precinct_boundaries
                WHERE former_council = %s
                  AND centroid IS NOT NULL
                ORDER BY former_council, precinct_id
                """,
                (council,),
            )
        else:
            cur.execute(
                """
                SELECT precinct_id, former_council,
                       ST_Y(centroid) AS centroid_lat,
                       ST_X(centroid) AS centroid_lng
                FROM dcp_precinct_boundaries
                WHERE centroid IS NOT NULL
                ORDER BY former_council, precinct_id
                """
            )
        return cur.fetchall()


def fetch_cached_ids(conn) -> set[str]:
    """Return precinct_ids already in cache."""
    with conn.cursor() as cur:
        cur.execute("SELECT precinct_id FROM precinct_amenity_cache")
        return {row[0] for row in cur.fetchall()}


def fetch_stale_ids(conn) -> set[str]:
    """Return precinct_ids where computed_at is older than STALE_DAYS."""
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT precinct_id FROM precinct_amenity_cache "
            f"WHERE computed_at < now() - interval '{STALE_DAYS} days'"
        )
        return {row[0] for row in cur.fetchall()}


def call_amenity(lat: float, lng: float) -> dict | None:
    """Call city2graph /amenity. Returns parsed response or None on failure."""
    try:
        resp = requests.post(
            f"{SPATIAL_API_URL}/amenity",
            json={"lat": lat, "lng": lng, "radius_m": 1000},
            timeout=AMENITY_TIMEOUT_S,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        logger.warning(f"  Timeout after {AMENITY_TIMEOUT_S}s")
        return None
    except Exception as e:
        logger.warning(f"  Request failed: {e}")
        return None


def upsert_cache(conn, precinct_id: str, former_council: str,
                 amenity: dict, lat: float, lng: float) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO precinct_amenity_cache
                (precinct_id, former_council, amenity_jsonb, centroid_lat, centroid_lng, computed_at)
            VALUES (%s, %s, %s, %s, %s, now())
            ON CONFLICT (precinct_id) DO UPDATE SET
                amenity_jsonb  = EXCLUDED.amenity_jsonb,
                centroid_lat   = EXCLUDED.centroid_lat,
                centroid_lng   = EXCLUDED.centroid_lng,
                computed_at    = now()
            """,
            (precinct_id, former_council, json.dumps(amenity), lat, lng),
        )
    conn.commit()


def run(args: argparse.Namespace) -> None:
    conn = get_connection()
    precincts = fetch_precincts(conn, council=args.council)
    logger.info(f"Found {len(precincts)} precincts to process")

    cached_ids = fetch_cached_ids(conn)
    stale_ids = fetch_stale_ids(conn) if args.refresh_stale else set()

    if args.precinct_id:
        precincts = [p for p in precincts if p["precinct_id"] == args.precinct_id]
        if not precincts:
            logger.error(f"Precinct '{args.precinct_id}' not found")
            return

    to_process = []
    for p in precincts:
        pid = p["precinct_id"]
        if pid in cached_ids and pid not in stale_ids and not args.force:
            logger.debug(f"  Skipping {pid} (cached)")
            continue
        to_process.append(p)

    logger.info(f"{len(to_process)} precincts to compute "
                f"({len(precincts) - len(to_process)} already cached)")

    if args.dry_run:
        for p in to_process:
            logger.info(f"  DRY RUN: would compute {p['precinct_id']} ({p['former_council']})")
        return

    ok = 0
    failed = 0
    for i, p in enumerate(to_process, 1):
        pid = p["precinct_id"]
        council = p["former_council"]
        logger.info(f"[{i}/{len(to_process)}] {pid} ({council})")

        lat = p["centroid_lat"]
        lng = p["centroid_lng"]
        logger.info(f"  centroid: {lat:.4f}, {lng:.4f}")
        amenity = call_amenity(lat, lng)

        if amenity is None:
            logger.warning(f"  Failed — skipping {pid}")
            failed += 1
        else:
            upsert_cache(conn, pid, council, amenity, lat, lng)
            score = amenity.get("walkability_score", "?")
            logger.info(f"  OK — walkability {score}/5")
            ok += 1

        if i < len(to_process):
            time.sleep(INTER_REQUEST_SLEEP_S)

    conn.close()
    logger.info(f"Done. {ok} computed, {failed} failed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Precompute amenity cache per DCP precinct")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run, no writes")
    parser.add_argument("--council", help="Filter to a single former_council slug")
    parser.add_argument("--precinct-id", help="Process a single precinct by ID")
    parser.add_argument("--refresh-stale", action="store_true",
                        help=f"Re-compute entries older than {STALE_DAYS} days")
    parser.add_argument("--force", action="store_true",
                        help="Re-compute all, even if already cached")
    args = parser.parse_args()
    run(args)
