"""Thin API over the CDC screen engine (#820 PR-2).

The workbench route (/api/cdc/preliminary-check) keeps its data plumbing on
the Next.js side and POSTs the property facts here; this endpoint owns the
regulatory logic: it loads the verified standards and runs the engine. Fails
closed (503) when the standards cannot be loaded — mirrors the granny-flat
endpoints (#817/#819): a screen must never run against absent or hardcoded
standards.
"""

import logging
import os

from fastapi import APIRouter, HTTPException

try:
    from services.cdc_screen import (
        CdcScreenInputs,
        CdcScreenResult,
        load_cdc_standards_from_url,
        run_cdc_screen,
    )
except ImportError:  # local (non-Docker) import path
    from cdc_screen import (
        CdcScreenInputs,
        CdcScreenResult,
        load_cdc_standards_from_url,
        run_cdc_screen,
    )

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["cdc"])

_STANDARDS_UNAVAILABLE_DETAIL = (
    "The complying-development screening standards could not be loaded from "
    "the database, so the CDC screen cannot run. Retry later, or obtain the "
    "current standards from the SEPP (Exempt and Complying Development "
    "Codes) 2008."
)


@router.post("/cdc/screen", response_model=CdcScreenResult)
def cdc_screen(inputs: CdcScreenInputs) -> CdcScreenResult:
    """Run the CDC preliminary screen over caller-supplied property facts.

    The caller fetches the facts (zone, lot, overlays, layers); this endpoint
    supplies the regulatory standards and the verdict logic. Never answers
    "yes" — "no" with cited exclusions, or "maybe" with a certifier
    disclaimer.
    """
    standards = load_cdc_standards_from_url(os.getenv("DATABASE_URL"))
    if standards is None:
        raise HTTPException(status_code=503, detail=_STANDARDS_UNAVAILABLE_DETAIL)
    return run_cdc_screen(standards, inputs)
