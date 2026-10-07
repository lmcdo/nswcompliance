"""POST /pipeline/cdc/lot-requirements: the CDC Housing Code lot-requirements screen.

prior-art-checked: reuse not viable because /pipeline/cdc/screen (cdc_screen_api.py)
accepts the property facts from the caller and returns the legacy 10-check
screen; this endpoint accepts ONLY an address, fetches every fact server-side and
returns the four-criterion result with its authority evidence.

Order (each step is an input to the next; there is no other path to a result):
    1. load_authority      -> UNAVAILABLE (HTTP 503) on any failure, nothing evaluated
    2. load_lot_inputs     -> server-side facts, three-state
    3. evaluate            -> pure deterministic comparison
    4. result + evidence
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

try:
    from services.cdc_lot_authority import load_authority
    from services.cdc_lot_inputs import PropertyNotIdentified, load_lot_inputs
    from services.cdc_lot_requirements import LotInputs, LotRequirementsResult, evaluate, overall
except ImportError:  # local (non-Docker) import path
    from cdc_lot_authority import load_authority  # type: ignore
    from cdc_lot_inputs import PropertyNotIdentified, load_lot_inputs  # type: ignore
    from cdc_lot_requirements import LotInputs, LotRequirementsResult, evaluate, overall  # type: ignore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["cdc"])


class LotRequirementsRequest(BaseModel):
    """Only the property identifier. Any other field (zone, area, a verdict...)
    is rejected with HTTP 422 rather than ignored."""

    model_config = ConfigDict(extra="forbid")
    address: str = Field(min_length=5, max_length=300)


def _connect():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        return None
    import psycopg2

    conn = psycopg2.connect(db_url, options="-c statement_timeout=30000")
    conn.autocommit = True
    return conn


def _unidentified(reason: str) -> LotInputs:
    return LotInputs(zone_reason=reason, area_reason=reason, width_reason=reason, ass_reason=reason)


def run_lot_requirements(address: str, conn) -> LotRequirementsResult:
    """The whole pipeline, injectable for tests (conn may be a fake)."""
    outcome = load_authority(conn)
    if outcome.authority is None:
        return LotRequirementsResult(result="UNAVAILABLE", criteria=[],
                                     authority_failures=list(outcome.failures),
                                     property={"address": address})
    authority = outcome.authority
    max_class = int(authority.get("acid_sulfate_max_class").value)  # type: ignore[arg-type]
    try:
        prop, inputs = load_lot_inputs(address, conn, max_class)
    except PropertyNotIdentified:
        prop, inputs = {"address": address}, _unidentified(
            "the address did not resolve to exactly one parcel")
    except Exception as e:  # noqa: BLE001 — an upstream outage is UNKNOWN, never a pass
        logger.warning("cdc lot requirements: property lookup failed: %s", e)
        prop, inputs = {"address": address}, _unidentified("the property lookup failed")
    criteria = evaluate(authority, inputs)
    return LotRequirementsResult(result=overall(criteria), criteria=criteria, property=prop)


@router.post("/cdc/lot-requirements", response_model=LotRequirementsResult)
def cdc_lot_requirements(req: LotRequirementsRequest):
    conn = None
    try:
        try:
            conn = _connect()
        except Exception as e:  # noqa: BLE001
            logger.warning("cdc lot requirements: database connection failed: %s", e)
        result = run_lot_requirements(req.address, conn)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
    status = 503 if result.result == "UNAVAILABLE" else 200
    return JSONResponse(status_code=status, content=result.model_dump(mode="json"))
