"""
Shared audit trail logging for satellite product pipelines.

Every report generation must call log_audit_trail() AFTER the report is
successfully written to property_reports / pre_da_history_reports.

The audit trail is append-only — no UPDATE or DELETE.  This is a legal
requirement for defensibility under ACL s18 and Shaddock negligence.

See: docs/qa/language-audit-2026-05-18.md
     ~/.claude/plans/ce-satellite-qa-validation-plan.md
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pipeline version — set by Railway at deploy time, falls back to "dev"
# ---------------------------------------------------------------------------
PIPELINE_VERSION: str = os.environ.get(
    "RAILWAY_GIT_COMMIT_SHA",
    os.environ.get("GIT_COMMIT_SHA", "dev"),
)


def _get_conn():
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        return psycopg2.connect(dsn)
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        database=os.environ.get("DB_NAME", "nsw_planning"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", ""),
        port=int(os.environ.get("DB_PORT", 5432)),
    )


# ---------------------------------------------------------------------------
# Data source tracking helper
# ---------------------------------------------------------------------------

class DataSourceQuery:
    """Record of a single data source query for the audit trail."""

    def __init__(
        self,
        source_name: str,
        url: str,
        query_params: Optional[dict] = None,
    ):
        self.source_name = source_name
        self.url = url
        self.query_params = query_params or {}
        self.query_timestamp = datetime.now(timezone.utc).isoformat()
        self.response_hash: Optional[str] = None
        self.features_returned: Optional[int] = None
        self.cache_hit: bool = False
        self.error: Optional[str] = None
        self._start_time = time.monotonic()
        self.duration_ms: Optional[int] = None

    def record_response(
        self,
        response_body: Any,
        features_returned: Optional[int] = None,
        cache_hit: bool = False,
    ) -> "DataSourceQuery":
        """Call after receiving a successful response."""
        self.duration_ms = int((time.monotonic() - self._start_time) * 1000)
        if response_body is not None:
            raw = json.dumps(response_body, sort_keys=True, default=str)
            self.response_hash = hashlib.sha256(raw.encode()).hexdigest()
        self.features_returned = features_returned
        self.cache_hit = cache_hit
        return self

    def record_error(self, error: str) -> "DataSourceQuery":
        """Call if the query failed."""
        self.duration_ms = int((time.monotonic() - self._start_time) * 1000)
        self.error = error
        return self

    def to_dict(self) -> dict:
        d = {
            "source_name": self.source_name,
            "url": self.url,
            "query_params": self.query_params,
            "query_timestamp": self.query_timestamp,
            "response_hash": self.response_hash,
            "features_returned": self.features_returned,
            "cache_hit": self.cache_hit,
            "duration_ms": self.duration_ms,
        }
        if self.error:
            d["error"] = self.error
        return d


# ---------------------------------------------------------------------------
# Main audit trail writer
# ---------------------------------------------------------------------------

def log_audit_trail(
    report_id: str,
    pipeline_name: str,
    input_params: dict,
    data_sources: list[DataSourceQuery],
    output_summary: dict,
    disclaimer_version: str,
    intermediate_calculations: Optional[dict] = None,
) -> None:
    """
    Write an immutable audit record for a generated report.

    This MUST be called after every successful report write.  It is
    non-blocking on failure — if the audit write fails, we log the error
    but do not prevent the report from being returned to the user.
    The alternative (blocking) would mean audit infrastructure issues
    break the product, which is worse for users.

    Args:
        report_id: UUID of the report in property_reports / pre_da_history_reports
        pipeline_name: e.g. 'bushfire', 'solar-yield', 'flood'
        input_params: address, lat, lng, lot_geometry, etc.
        data_sources: list of DataSourceQuery objects from the pipeline run
        output_summary: the outputs JSON written to the report table
        disclaimer_version: version string (e.g. 'bushfire-v1')
        intermediate_calculations: optional key calc steps for traceability
    """
    sql = """
        INSERT INTO report_audit_trail
            (report_id, pipeline_name, pipeline_version,
             input_params, data_sources_queried, intermediate_calculations,
             output_summary, disclaimer_version)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    sources_json = [ds.to_dict() for ds in data_sources]

    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(sql, (
                report_id,
                pipeline_name,
                PIPELINE_VERSION,
                psycopg2.extras.Json(input_params),
                psycopg2.extras.Json(sources_json),
                psycopg2.extras.Json(intermediate_calculations) if intermediate_calculations else None,
                psycopg2.extras.Json(output_summary),
                disclaimer_version,
            ))
        conn.commit()
        logger.info(f"Audit trail logged for {pipeline_name} report {report_id}")
    except Exception as exc:
        # Non-blocking: log error but don't prevent report delivery
        logger.error(f"Audit trail write failed for {pipeline_name} report {report_id}: {exc}")
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Disclaimer version lookup
# ---------------------------------------------------------------------------

def get_current_disclaimer_version(pipeline_name: str) -> str:
    """
    Return the current active disclaimer version string for a pipeline.
    Falls back to '{pipeline_name}-v1' if no disclaimer is seeded yet.
    """
    sql = """
        SELECT version FROM disclaimer_versions
        WHERE pipeline_name = %s AND superseded_at IS NULL
        ORDER BY effective_from DESC
        LIMIT 1
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(sql, (pipeline_name,))
            row = cur.fetchone()
            if row:
                return row[0]
    except Exception as exc:
        logger.warning(f"Disclaimer version lookup failed for {pipeline_name}: {exc}")
    finally:
        if conn:
            conn.close()
    return f"{pipeline_name}-v1"
