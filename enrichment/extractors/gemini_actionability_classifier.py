#!/usr/bin/env python3
"""
Gemini Actionability Classifier — Stage 3 of the three-stage hybrid.

Handles performance-based DCP formats (Ashfield Purpose/Performance Criteria/
Design Solutions structure, and future LGAs with similar formats) where regex
cannot reliably distinguish regulatory language from narrative or procedural text.

Classification contract (ADR-001):
- Output is accepted ONLY if the identified span is a verbatim substring of the
  source provision text (source[char_start:char_end] == identified_text).
- Output that fails verification is REJECTED. The provision falls back to
  actionable=True (conservative default per ADR-001 Stage 2).
- This eliminates hallucination risk and produces a machine-verifiable audit trail.

Usage:
    classifier = GeminiActionabilityClassifier()
    result = classifier.classify(provision_text, document_id, source_text)
    if result.verified:
        is_actionable = result.is_actionable
    else:
        is_actionable = True  # conservative fallback

NOT YET WIRED INTO pipeline.py. This module locks the interface contract so the
pipeline integration can be added without architectural rework. Triggered by
document format detection (performance-based DCP flag), not by LGA name.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class GeminiClassificationResult:
    """Result of a Gemini-based actionability classification.

    Attributes:
        is_actionable: Whether the provision contains a regulatory control.
            Always True when verified=False (conservative fallback).
        verified: True if identified_text was confirmed as a verbatim substring
            of the source provision. False means Gemini output could not be
            mechanically verified — caller must use conservative fallback.
        identified_text: The exact text span Gemini identified as the regulatory
            content. None if Gemini returned no span or verification failed.
        char_start: Start index of identified_text within source_text. None if
            unverified.
        char_end: End index (exclusive) of identified_text within source_text.
            None if unverified.
        reason: Human-readable explanation of the classification decision.
        model: Gemini model ID used for this classification.
    """
    is_actionable: bool
    verified: bool
    identified_text: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    reason: str = ""
    model: str = ""


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

class GeminiActionabilityClassifier:
    """Classify provisions using Gemini Flash with substring verification.

    Intended for performance-based DCPs where regex classification is unreliable.
    Every classification is verified by confirming that the model's identified
    text span exists verbatim in the source provision. Unverified results are
    discarded and the provision defaults to actionable (conservative per ADR-001).

    Args:
        model_name: Gemini model ID. Defaults to gemini-2.5-flash for cost
            efficiency. Change to gemini-2.5-pro for higher accuracy if needed.
        temperature: Sampling temperature. Low values (0.0–0.1) maximise
            determinism. Default 0.1.
        api_key: Gemini API key. Reads GEMINI_API_KEY (then GOOGLE_API_KEY)
            from environment if None.
        timeout_s: Per-request timeout in seconds. Default 30.

    Raises:
        ImportError: If google-genai is not installed.
        ValueError: If no API key is available.
    """

    DEFAULT_MODEL = "gemini-2.5-flash"
    DEFAULT_TEMPERATURE = 0.1
    DEFAULT_TIMEOUT_S = 30

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        api_key: Optional[str] = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        """Initialise the classifier and configure the Gemini client."""
        try:
            from google import genai  # type: ignore[import]
            from google.genai import types as genai_types  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "google-genai is required for GeminiActionabilityClassifier. "
                "Install with: pip install google-genai"
            ) from exc

        resolved_key = (
            api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        )
        if not resolved_key:
            raise ValueError(
                "Gemini API key required. Set GEMINI_API_KEY environment variable "
                "or pass api_key= to GeminiActionabilityClassifier()."
            )

        # timeout is milliseconds in google-genai HttpOptions.
        self._client = genai.Client(
            api_key=resolved_key,
            http_options=genai_types.HttpOptions(timeout=int(timeout_s * 1000)),
        )
        self._types = genai_types
        self._model_name = model_name
        self._temperature = temperature

    def classify(
        self,
        provision_text: str,
        document_id: str,
        source_text: Optional[str] = None,
    ) -> GeminiClassificationResult:
        """Classify a single provision using Gemini with substring verification.

        The model is asked to identify the specific span of text that constitutes
        a regulatory requirement, if one exists. The identified span is then
        verified as a verbatim substring of source_text (or provision_text if
        source_text is not provided). Classification is accepted only when
        verification passes.

        Args:
            provision_text: The provision text to classify.
            document_id: Document identifier for context (e.g. council name,
                DCP section). Included in the prompt to help the model understand
                the regulatory context.
            source_text: The raw source text from which provision_text was
                extracted. Used as the verification corpus. Falls back to
                provision_text if None.

        Returns:
            GeminiClassificationResult. If verified=False, caller must use
            the conservative fallback (is_actionable=True per ADR-001).
        """
        corpus = source_text if source_text is not None else provision_text

        prompt = self._build_prompt(provision_text, document_id)

        # Any failure to obtain a usable response — network error, rate limit,
        # safety block, empty/blocked candidate — collapses to the conservative
        # fallback (is_actionable=True, verified=False) per ADR-001. The model
        # never causes a crash and never silently marks a provision non-actionable.
        try:
            response_text = self._call_gemini(prompt)
        except Exception as exc:
            return GeminiClassificationResult(
                is_actionable=True,
                verified=False,
                reason=f"Gemini API error — conservative fallback: {exc}",
                model=self._model_name,
            )

        return self._parse_and_verify(response_text, corpus)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini and return the raw response text.

        Raises on any failure (network, rate limit, safety block, or an empty/
        blocked candidate where ``response.text`` would be None or raise). The
        caller treats every exception as the conservative fallback.
        """
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=self._types.GenerateContentConfig(
                max_output_tokens=800,
                temperature=self._temperature,
                candidate_count=1,
                # Force structured JSON so parsing can't be derailed by prose or
                # markdown fences.
                response_mime_type="application/json",
            ),
        )
        # response.text raises in some SDK versions when the candidate was blocked
        # or empty; getattr keeps that from escaping as an unhandled crash.
        text = getattr(response, "text", None)
        if not text:
            raise ValueError("Gemini returned an empty or blocked response (no text)")
        return text

    def _build_prompt(self, provision_text: str, document_id: str) -> str:
        """Build the classification prompt.

        Args:
            provision_text: Text of the provision to classify.
            document_id: Document context identifier.

        Returns:
            Prompt string for Gemini.
        """
        return f"""You are classifying text from an Australian planning document.

Document: {document_id}

Determine whether the following text contains a REGULATORY REQUIREMENT — a binding
obligation, prohibition, standard, or performance criterion that a development
application must address. Do NOT treat historical narrative, background explanation,
application scope statements, or aspirational objectives as regulatory requirements.

If a regulatory requirement exists, identify the EXACT span of text that expresses
it. The span must be copied verbatim from the text below — do not paraphrase or
summarise.

If no regulatory requirement exists, return is_actionable: false with no span.

Respond in JSON only:
{{
  "is_actionable": true | false,
  "identified_text": "<exact verbatim span from source, or null>",
  "reason": "<one sentence explanation>"
}}

TEXT TO CLASSIFY:
{provision_text}"""

    def _parse_and_verify(
        self, response_text: str, corpus: str
    ) -> GeminiClassificationResult:
        """Parse Gemini JSON response and verify the identified span.

        Args:
            response_text: Raw text response from Gemini.
            corpus: The source text to verify the identified span against.

        Returns:
            GeminiClassificationResult with verified=True only if the identified
            span exists verbatim in corpus.
        """
        import json
        import re

        # Strip markdown code fences if present
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", response_text.strip())

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return GeminiClassificationResult(
                is_actionable=True,
                verified=False,
                reason="Could not parse Gemini response as JSON — conservative fallback",
                model=self._model_name,
            )

        # Coerce defensively: JSON mode returns a real bool, but a model that
        # emits the string "false" must not be read as truthy. Unknown/missing →
        # conservative True.
        raw_actionable = data.get("is_actionable", True)
        if isinstance(raw_actionable, str):
            is_actionable = raw_actionable.strip().lower() not in ("false", "0", "no", "")
        else:
            is_actionable = bool(raw_actionable)
        identified_text: Optional[str] = data.get("identified_text") or None
        reason: str = data.get("reason", "")

        if not is_actionable:
            # Model says not actionable. Only accept if no span was identified
            # (model is confident it's boilerplate). Conservative: if model
            # returns identified_text alongside is_actionable=false, treat as
            # ambiguous and fall back to actionable.
            if identified_text:
                return GeminiClassificationResult(
                    is_actionable=True,
                    verified=False,
                    reason=(
                        "Model returned is_actionable=false but also provided "
                        "identified_text — ambiguous response, conservative fallback"
                    ),
                    model=self._model_name,
                )
            return GeminiClassificationResult(
                is_actionable=False,
                verified=True,
                identified_text=None,
                reason=reason,
                model=self._model_name,
            )

        # Model says actionable. Verify the identified span.
        if not identified_text:
            return GeminiClassificationResult(
                is_actionable=True,
                verified=False,
                reason="Model returned is_actionable=true but no identified_text — conservative fallback",
                model=self._model_name,
            )

        pos = corpus.find(identified_text)
        if pos == -1:
            return GeminiClassificationResult(
                is_actionable=True,
                verified=False,
                identified_text=identified_text,
                reason=(
                    "identified_text not found verbatim in source — possible hallucination, "
                    "conservative fallback (still actionable)"
                ),
                model=self._model_name,
            )

        return GeminiClassificationResult(
            is_actionable=True,
            verified=True,
            identified_text=identified_text,
            char_start=pos,
            char_end=pos + len(identified_text),
            reason=reason,
            model=self._model_name,
        )


# ---------------------------------------------------------------------------
# Document format detection (stub — triggers Stage 3)
# ---------------------------------------------------------------------------

PERFORMANCE_BASED_DOC_SIGNALS: tuple[str, ...] = (
    "Ashfield",
    # Add future performance-based LGA signals here as they are onboarded.
    # Detection is by document_id substring, not LGA name, so it works for
    # any document naming convention that includes the council name.
)


def is_performance_based_dcp(document_id: str) -> bool:
    """Return True if document_id indicates a performance-based DCP format.

    Performance-based DCPs use Purpose/Performance Criteria/Design Solutions
    structure rather than numbered controls, making regex classification unreliable.
    These documents should be routed to GeminiActionabilityClassifier (Stage 3).

    Args:
        document_id: The document_id value from regulatory_provisions.

    Returns:
        True if the document should use Stage 3 classification.
    """
    return any(signal in document_id for signal in PERFORMANCE_BASED_DOC_SIGNALS)
