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
- Rate limited: the model call costs money per request and this endpoint takes
  no credential, so a loop is a billing incident. See RATE LIMIT below.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.brief_narration import (
    PERSONAS,
    generate_overlay,
    overlay_enabled,
    overlay_to_dict,
)
from services.brief_manifest import Intent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- RATE LIMIT
# prior-art-checked: `grep -rln "slowapi|RateLimit|rate_limit|Limiter" services/`
# returns NOTHING - no rate limiting exists anywhere in services/, so there is
# nothing to reuse and no house pattern to follow. Written here rather than as a
# shared module because this is the only endpoint that needs it today; lift it
# out when a second caller appears, not before.
#
# WHY IT EXISTS. This endpoint takes no credential and calls a paid model on
# every request. Sub-cent per call is fine for a person reading a brief and is
# not fine for a script, so the flag that exposes it to production must not be
# turned on without a cap. Two limits, because they answer different questions:
#
#   PER CLIENT  stops one caller monopolising the endpoint.
#   GLOBAL      caps the BILL no matter how many clients appear. A per-IP limit
#               alone is no protection at all against a spread of addresses,
#               which is the shape an abusive caller actually has.
#
# ⚠ HONEST LIMITATION: this is in-process. Railway can run more than one
# instance, and each keeps its own counters, so the true ceiling is
# GLOBAL_MAX x instances. It is a cost guardrail, not an access control. If this
# endpoint stays public long term it wants a real credential and a shared store;
# that is recorded rather than implied.
_RATE_WINDOW_S = 60.0
_PER_CLIENT_MAX = 12      # a reading session taps a few chips; 12/min is roomy
_GLOBAL_MAX = 120         # ceiling on spend per minute, all callers together
_MAX_TRACKED_CLIENTS = 4096   # bounded memory: never grow the map without limit

_rate_lock = threading.Lock()
_client_hits: "OrderedDict[str, list]" = OrderedDict()
_global_hits: list = []


def _client_key(request: Request) -> str:
    """The caller, as well as it can be known behind a proxy.

    X-Forwarded-For is client-controlled, so it is a courtesy key for separating
    ordinary callers, NOT a security boundary - which is exactly why the global
    limit exists and does not depend on it.
    """
    fwd = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if fwd:
        return fwd
    return request.client.host if request.client else "unknown"


def _prune(hits: list, now: float) -> None:
    cutoff = now - _RATE_WINDOW_S
    while hits and hits[0] < cutoff:
        hits.pop(0)


def _rate_limit_check(request: Request) -> Optional[int]:
    """None when the call may proceed, else the Retry-After seconds to send.

    Monotonic clock: a wall-clock jump backwards would otherwise hand out free
    quota, and NTP steps are not hypothetical on a cloud host.
    """
    now = time.monotonic()
    key = _client_key(request)
    with _rate_lock:
        _prune(_global_hits, now)
        if len(_global_hits) >= _GLOBAL_MAX:
            return max(1, int(_RATE_WINDOW_S - (now - _global_hits[0])) + 1)

        hits = _client_hits.get(key)
        if hits is None:
            if len(_client_hits) >= _MAX_TRACKED_CLIENTS:
                _client_hits.popitem(last=False)   # evict the least recent
            hits = _client_hits[key] = []
        _prune(hits, now)
        if len(hits) >= _PER_CLIENT_MAX:
            return max(1, int(_RATE_WINDOW_S - (now - hits[0])) + 1)

        hits.append(now)
        _client_hits.move_to_end(key)
        _global_hits.append(now)
    return None


def _reset_rate_limit_for_tests() -> None:
    """Tests need a clean slate; nothing in the request path calls this."""
    with _rate_lock:
        _client_hits.clear()
        del _global_hits[:]


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
def brief_overlay(req: OverlayRequest, request: Request) -> OverlayResponse:
    """Generate the intent overlay for an assembled brief.

    Returns enabled=false with no overlay when the feature flag is off —
    the UI treats that identically to "nothing to show".
    """
    # Flag first, THEN the limit. When the flag is off nothing is spent and the
    # honest answer is "disabled" - answering 429 there would be a lie about why
    # there is no overlay, and the cost this guards does not exist on that path.
    if not overlay_enabled():
        return OverlayResponse(enabled=False, overlay=None)

    retry_after = _rate_limit_check(request)
    if retry_after is not None:
        logger.warning("brief-overlay rate limited: client=%s", _client_key(request))
        raise HTTPException(
            status_code=429,
            detail="Too many overlay requests. Try again shortly.",
            headers={"Retry-After": str(retry_after)},
        )

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
