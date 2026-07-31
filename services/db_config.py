#!/usr/bin/env python3
"""
Database Configuration Module
Provides direct database connection for the compliance engine
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import time
from typing import List

def get_connection():
    """
    Get a direct database connection to PostgreSQL

    Returns:
        psycopg2 connection object
    """
    # Direct connection to existing PostgreSQL database
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', '127.0.0.1'),
        database=os.environ.get('DB_NAME', 'nsw_planning'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', ''),  # Add password if needed
        port=int(os.environ.get('DB_PORT', 5432))
    )

def get_dict_connection():
    """
    Get a database connection that returns dictionaries

    Returns:
        psycopg2 connection with RealDictCursor
    """
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', '127.0.0.1'),
        database=os.environ.get('DB_NAME', 'nsw_planning'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', ''),
        port=int(os.environ.get('DB_PORT', 5432)),
        cursor_factory=RealDictCursor
    )

# prior-art-checked: the guard's suggested matches (intelligence_brief.py,
# flood_truth.py, granny_flat.py, the *-coverage-* frontend routes) are
# unrelated satellite-product/coverage-stat surfaces matched only on generic
# words ("coverage", "connection", "distinct"). This is the one place in the
# repo that queries lep_zone_coverage from Python — confirmed via repo-wide
# search during the DQ-30 investigation (.claude/DATA_QUALITY_TRACKER.md);
# the only existing Python reference to that table was a one-off diagnostic
# script (scripts/check_zone_coverage.py), not a reusable query function.
#
# Short-lived cache for per-LGA valid zone lists (DQ-30). lep_zone_coverage
# changes only when an LGA is (re-)scraped, not per-request, so re-querying on
# every call is wasted work — but it must stay a live query, not a committed
# constant, since which LGAs are onboarded changes independent of deploys.
_ZONE_COVERAGE_CACHE: dict = {}
_ZONE_COVERAGE_CACHE_TTL_SECONDS = 300


def get_valid_zones_for_lga(lga: str) -> List[str]:
    """Get the current, live-scraped set of valid zone codes for an LGA from
    lep_zone_coverage (DQ-30).

    Distinct from enrichment.config.zone_taxonomy's legacy/current alias map:
    this answers "what zones exist in LGA X today", not "what did this legacy
    code become".

    Args:
        lga: LGA name as stored in lep_zone_coverage (e.g. "Waverley")

    Returns:
        Current zone codes for that LGA, or [] if the LGA has no rows (not
        yet onboarded — callers should not treat this as "no zones exist",
        just "we haven't scraped it").
    """
    cached = _ZONE_COVERAGE_CACHE.get(lga)
    if cached and cached[1] > time.time():
        return cached[0]

    conn = get_connection()
    try:
        cur = conn.cursor()
        # prior-art-checked: not a new capability -- this is a one-predicate
        # fix to get_valid_zones_for_lga(), a function this same PR already
        # added earlier in this branch. It intentionally reuses (not
        # duplicates) the is_complete=TRUE gate already established in
        # app/api/lep/permissibility/route.ts and
        # app/api/permissibility/check/route.ts, matching this codebase's
        # existing lep_zone_coverage convention rather than inventing a new
        # one.
        #
        # is_complete = TRUE: an interrupted scrape must not be treated as
        # "this is the complete valid zone list for the LGA."
        cur.execute(
            "SELECT zone FROM lep_zone_coverage WHERE lga = %s AND is_complete = TRUE ORDER BY zone",
            (lga,),
        )
        zones = [row[0] for row in cur.fetchall()]
    finally:
        conn.close()

    _ZONE_COVERAGE_CACHE[lga] = (zones, time.time() + _ZONE_COVERAGE_CACHE_TTL_SECONDS)
    return zones


# For backward compatibility with old code expecting SafeConnection
class SafeConnection:
    """Compatibility wrapper that just uses direct connection"""
    def __init__(self, **kwargs):
        self.connection = get_connection()

    def cursor(self):
        return self.connection.cursor()

    def commit(self):
        return self.connection.commit()

    def rollback(self):
        return self.connection.rollback()

    def close(self):
        return self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

__all__ = ['get_connection', 'get_dict_connection', 'SafeConnection']