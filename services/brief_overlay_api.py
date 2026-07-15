"""API endpoint for the brief LLM overlay (PR-3 wiring).

prior-art-checked: no existing endpoint serves the overlay; the engine
(services/brief_narration.py, merged #742) has zero callers. This router is
the single thin entry the frontend proxy hits.

Contract:
- Flag-gated server-side: when BRIEF_LLM_OVERLAY_ENABLED is off the endpoint
  answers {"enabled": false, "overlay": null} — it never errors, never calls
  the model, and the UI simply shows nothing.
- Stateless: the frontend already holds the streamed brief sections, so it
  POSTs the assembled brief back. No storage, no session.
- Additive-only: any engine failure is already converted to overlay=null by
  generate_overlay; this layer adds request validation only.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.brief_narration import (
    PERSONAS,
    generate_overlay,
    overlay_enabled,
    overlay_to_dict,
)
from services.brief_manifest import Intent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["intelligence"])

MAX_QUESTION_CHARS = 300  # free-text is deferred (C7); cap defensively anyway

VALID_INTENTS = {i.value for i in Intent}


class OverlayRequest(BaseModel):
    """The assembled brief plus the reader's context."""

    brief: dict = Field(..., description="Assembled brief dict (metadata + sections + complete)")
    persona: str = "homeowner"
    intent: Optional[str] = None
    question: Optional[str] = Field(None, max_length=MAX_QUESTION_CHARS)

    model_config = ConfigDict(extra="forbid")

    @field_validator("persona")
    @classmethod
    def _persona_known(cls, v: str) -> str:
        if v not in PERSONAS:
            raise ValueError(f"unknown persona {v!r}")
        return v

    @field_validator("intent")
    @classmethod
    def _intent_known(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_INTENTS:
            raise ValueError(f"unknown intent {v!r}")
        return v

    @field_validator("brief")
    @classmethod
    def _brief_not_empty(cls, v: dict) -> dict:
        if not isinstance(v, dict) or not v.get("address"):
            raise ValueError("brief must be the assembled brief dict with an address")
        return v


class OverlayResponse(BaseModel):
    enabled: bool
    overlay: Optional[dict] = None

    model_config = ConfigDict(extra="forbid")


@router.post("/brief-overlay", response_model=OverlayResponse)
def brief_overlay(req: OverlayRequest) -> OverlayResponse:
    """Generate the intent overlay for an assembled brief.

    Returns enabled=false with no overlay when the feature flag is off —
    the UI treats that identically to "nothing to show".
    """
    if not overlay_enabled():
        return OverlayResponse(enabled=False, overlay=None)

    try:
        overlay = generate_overlay(
            req.brief,
            persona=req.persona,
            intent=req.intent,
            question=req.question,
            enabled=True,  # flag already checked above, once
        )
    except Exception as exc:  # generate_overlay shouldn't raise; belt+braces
        logger.error("brief-overlay endpoint failure: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="overlay generation failed")

    return OverlayResponse(enabled=True, overlay=overlay_to_dict(overlay))
