"""Stage-1 selection + orchestration for the brief LLM overlay.

prior-art-checked: services/ has no LLM-selection or narration module (grep
template|narrat|render 2026-07-15 — only HTML/model-docstring hits); the one
existing Anthropic call site is lec_collector.py (LEC judgment extraction),
whose lazy-client pattern this module reuses. The `narrative` field on the
brief (intelligence_brief.py:947) is declared but has never been populated by
any code path.

Architecture (ce-brief-llm-integration-concepts §3 + 2026-07-15 decisions):
- Stage-1: Haiku-class model receives the cached manifest block + capabilities
  and emits a CompositionPlan (template ids + manifest entry ids) via a
  tool-forced, enum-constrained schema. It cannot write prose.
- Stage-2: brief_templates renders the plan from actual manifest values.
- Deterministic pre-check: check_intent_compatibility runs BEFORE any LLM
  call; an apartment×build-intent mismatch renders a scope-decline overlay
  with zero model involvement.
- HARD RULES (user-confirmed 2026-07-15): the overlay is feature-flagged
  DEFAULT OFF (BRIEF_LLM_OVERLAY_ENABLED) and only ever ADDS content — any
  failure here returns None and the base brief is untouched.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, ValidationError

from services.brief_manifest import (
    BriefManifest,
    CompatibilityStatus,
    EntryKind,
    Intent,
    build_manifest,
    check_intent_compatibility,
)
from services.brief_templates import (
    AUTHORITATIVE_FACT_TEMPLATES,
    COMPUTED_SOURCES,
    TEMPLATES,
    RenderedLine,
    RenderedOverlay,
    assemble_groups,
    assign_footnotes,
    capabilities_block,
    render_line,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Feature flag — DEFAULT OFF (user decision 2026-07-15). Only "true"/"1"
# enables; anything else, including unset, keeps the overlay dark.
OVERLAY_FLAG_ENV = "BRIEF_LLM_OVERLAY_ENABLED"

# Haiku-class per the extraction ladder (ce-ai-extraction-decision): Stage-1
# is a small-context structured-output task, sub-cent per call.
MODEL_ENV = "BRIEF_NARRATION_MODEL"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"

MAX_OUTPUT_TOKENS = 1500
REQUEST_TIMEOUT_S = 60.0
# One retry with the validation errors fed back — invalid plans are cheap to
# regenerate and usually a one-off slip.
MAX_PLAN_ATTEMPTS = 2
MIN_PLAN_ITEMS = 1
MAX_PLAN_ITEMS = 10

PERSONAS = frozenset({
    "homeowner", "buyers_agent", "conveyancer", "architect", "developer",
    "planner",
})


def overlay_enabled(enabled: Optional[bool] = None) -> bool:
    """Explicit argument wins; else the env flag; else OFF."""
    if enabled is not None:
        return enabled
    return os.environ.get(OVERLAY_FLAG_ENV, "").strip().lower() in ("true", "1")


# ---------------------------------------------------------------------------
# CompositionPlan
# ---------------------------------------------------------------------------


class PlanItem(BaseModel):
    template: str
    fields: list[str] = []
    gap: Optional[str] = None
    why: Optional[str] = None  # audit only — never rendered to the user

    model_config = ConfigDict(extra="forbid")


class CompositionPlan(BaseModel):
    headline_template: str
    items: list[PlanItem]
    declined: bool = False
    clarify_intents: list[str] = []

    model_config = ConfigDict(extra="forbid")


def plan_tool_schema() -> dict:
    """Tool schema with template ids enum-constrained (live finding #5:
    free-text headline_template came back as prose without this)."""
    template_ids = sorted(TEMPLATES.keys())
    return {
        "name": "emit_composition_plan",
        "description": "Emit the composition plan for the deterministic renderer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "headline_template": {"type": "string", "enum": template_ids},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "template": {"type": "string", "enum": template_ids},
                            "fields": {"type": "array", "items": {"type": "string"}},
                            "gap": {"type": ["string", "null"]},
                            "why": {"type": "string"},
                        },
                        "required": ["template", "fields"],
                    },
                },
                "declined": {"type": "boolean"},
                "clarify_intents": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["headline_template", "items", "declined"],
        },
    }


def normalize_plan(plan: CompositionPlan, manifest: BriefManifest) -> CompositionPlan:
    """Deterministic corrections that don't need a model retry.

    Live finding (polish audit): the model dressed capacity-engine outputs as
    "Planning control" — a computed setback is not THE control. Any
    authoritative-fact template citing a computed-source field is remapped to
    T_CAPACITY_RESULT here, in code.
    """
    by_id = {e.id: e for e in manifest.entries}
    for item in plan.items:
        if item.template in AUTHORITATIVE_FACT_TEMPLATES and len(item.fields) == 1:
            entry = by_id.get(item.fields[0])
            if entry is not None and entry.source in COMPUTED_SOURCES:
                logger.info("normalize_plan: %s on computed source %s → "
                            "T_CAPACITY_RESULT", item.template, entry.source)
                item.template = "T_CAPACITY_RESULT"
        # A verified finding cited under any fact template renders its raw
        # 'severity=…' payload (observed live) — findings have ONE renderer.
        if (item.template != "T_FINDING" and len(item.fields) == 1
                and item.fields[0].startswith("X")):
            logger.info("normalize_plan: X id under %s → T_FINDING", item.template)
            item.template = "T_FINDING"
        # The reverse mismatch also occurred live: a plain fact row cited under
        # T_FINDING has no 'severity=…' payload, so the caution renders its raw
        # value ("True"). Fact rows get a fact renderer.
        if (item.template == "T_FINDING" and len(item.fields) == 1
                and item.fields[0].startswith("F")):
            logger.info("normalize_plan: F id under T_FINDING → T_CONSTRAINT_FLAG")
            item.template = "T_CONSTRAINT_FLAG"
    return plan


def validate_plan(plan: CompositionPlan, manifest: BriefManifest) -> list[str]:
    """Return a list of contract violations (empty = valid).

    Never raises: callers decide whether to retry or fail closed.
    """
    errors: list[str] = []
    gap_ids = {e.id for e in manifest.entries if e.kind == EntryKind.GAP}
    # Fact templates may only cite F/X rows. A gap rendered through a fact
    # template would show an empty value under an authoritative-looking
    # provenance suffix — a failed check masquerading as checked-clear.
    fact_ids = manifest.entry_ids - gap_ids

    if plan.headline_template not in TEMPLATES:
        errors.append(f"unknown headline_template {plan.headline_template!r}")
    if plan.declined and plan.headline_template not in (
            "T_SCOPE_DECLINE", "T_CLARIFY", "T_NOT_COVERED"):
        errors.append("a declined plan must use T_SCOPE_DECLINE, T_CLARIFY or "
                      "T_NOT_COVERED as headline_template so the reader sees "
                      "why it declined")
    if not (MIN_PLAN_ITEMS <= len(plan.items) <= MAX_PLAN_ITEMS):
        errors.append(f"plan must have {MIN_PLAN_ITEMS}-{MAX_PLAN_ITEMS} items, "
                      f"got {len(plan.items)}")

    for i, item in enumerate(plan.items):
        template = TEMPLATES.get(item.template)
        if template is None:
            errors.append(f"items[{i}]: unknown template {item.template!r}")
            continue
        unknown = [f for f in item.fields if f not in fact_ids]
        if unknown:
            errors.append(f"items[{i}]: ids not usable as facts (unknown or "
                          f"G rows — gaps go via T_GAP_ROUTE): {unknown}")
            continue
        if template.arity.needs_gap:
            if not item.gap:
                errors.append(f"items[{i}]: {item.template} requires a gap id")
            elif item.gap not in gap_ids:
                errors.append(f"items[{i}]: gap id {item.gap!r} is not a G row")
        elif item.gap:
            errors.append(f"items[{i}]: {item.template} does not take a gap id")
        else:
            n = len(item.fields)
            if not (template.arity.min_fields <= n <= template.arity.max_fields):
                errors.append(
                    f"items[{i}]: {item.template} takes "
                    f"{template.arity.min_fields}-{template.arity.max_fields} "
                    f"field ids, got {n}"
                )
    return errors


# ---------------------------------------------------------------------------
# Stage-1 prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the selection engine for a property intelligence brief. You do not write
prose. You do not state facts. You select WHICH already-verified facts matter for
this reader, and HOW to order them, by emitting a composition plan via the
emit_composition_plan tool. Nothing else.

INPUT you receive:
- MANIFEST: every verified data field of this brief (id, path, value,
  confidence, source), every data gap (G ids, with reason and fallback source),
  every verified finding (X ids).
- CAPABILITIES: legal template ids with their reference signatures.
- REQUEST: the reader's persona, stated intent, and (optionally) one question.

HARD RULES
1. Reference only ids that exist in MANIFEST and template ids that exist in
   CAPABILITIES. Anything else is a validation failure and will be rejected.
2. You cannot introduce, restate, round, convert, or combine values. Values
   are rendered by the system from the manifest, never by you.
3. Confidence is immutable — the renderer prints each field's own confidence.
4. If decision-relevant information for the request is a GAP (G id), you MUST
   include it via T_GAP_ROUTE. Silence about a relevant gap is a failure.
5. No predictions, recommendations, likelihoods, approval prospects, or
   suitability judgements exist in the template set. If the request asks for
   one, set declined=true, use T_SCOPE_DECLINE as the headline, and select the
   field ids that show what the brief CAN factually offer instead.
6. If the request is ambiguous, use T_CLARIFY and list 2-3 candidate intents
   in clarify_intents. Do not guess.
7. Select 5-10 items ordered by decision-relevance to the stated intent, not
   by section order. A relevant X finding outranks a routine control.
8. If a question is asked and no combination of manifest ids answers it, use
   T_NOT_COVERED with the nearest relevant field id (for its source).

EXAMPLES (abbreviated manifests)

Example A — rule 4 (gap surfacing). Manifest contains:
  F001 | planning_controls.zone | R2 | authoritative | planning_portal
  F002 | planning_controls.height | 8.5 | authoritative | planning_portal
  G001 | GAP dcp_controls.landscaping | reason=council_not_extracted | fallback=council DCP ch 3
Request: persona=architect intent=renovate
A correct plan includes the gap, e.g.:
  {"headline_template": "T_ZONE_CONTEXT",
   "items": [
     {"template": "T_ZONE_CONTEXT", "fields": ["F001"]},
     {"template": "T_CONTROL_VALUE", "fields": ["F002"]},
     {"template": "T_GAP_ROUTE", "fields": [], "gap": "G001"}],
   "declined": false}

Example B — rule 5 (scope decline). Request asks: "Will council approve my
duplex?" A correct plan declines and still shows the facts:
  {"headline_template": "T_SCOPE_DECLINE",
   "items": [
     {"template": "T_ZONE_CONTEXT", "fields": ["F001"]},
     {"template": "T_CONTROL_VALUE", "fields": ["F002"]}],
   "declined": true}"""


def build_request_suffix(persona: str, intent: Optional[str],
                         question: Optional[str]) -> str:
    return (f"REQUEST\npersona: {persona}\nintent: {intent or 'null'}\n"
            f"question: {question or 'null'}\n"
            "emit the CompositionPlan now via the tool")


# ---------------------------------------------------------------------------
# Stage-1 call
# ---------------------------------------------------------------------------


class SelectionError(Exception):
    """Stage-1 could not produce a valid plan. Callers fail closed (no overlay)."""


def _get_client():  # pragma: no cover — thin wiring, exercised in live E2E
    from anthropic import Anthropic  # lazy: keeps module importable without SDK
    return Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def select_composition(
    manifest: BriefManifest,
    persona: str,
    intent: Optional[str] = None,
    question: Optional[str] = None,
    client: Any = None,
) -> CompositionPlan:
    """Run Stage-1 selection. Raises SelectionError on any failure —
    the orchestrator converts that to 'no overlay', never a broken brief."""
    if persona not in PERSONAS:
        raise SelectionError(f"unknown persona {persona!r}")

    if client is None:
        client = _get_client()

    system_blocks = [
        {"type": "text", "text": SYSTEM_PROMPT},
        {
            "type": "text",
            "text": manifest.to_prompt_block() + "\n\n" + capabilities_block(),
            # The manifest block is stable per (address, data_hash) — cache it
            # so every chip tap / question in a reading session hits cache.
            "cache_control": {"type": "ephemeral"},
        },
    ]
    messages = [{
        "role": "user",
        "content": build_request_suffix(persona, intent, question),
    }]

    last_errors: list[str] = []
    for attempt in range(MAX_PLAN_ATTEMPTS):
        try:
            response = client.messages.create(
                model=os.environ.get(MODEL_ENV, DEFAULT_MODEL),
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system_blocks,
                tools=[plan_tool_schema()],
                tool_choice={"type": "tool", "name": "emit_composition_plan"},
                messages=messages,
                timeout=REQUEST_TIMEOUT_S,
            )
        except Exception as exc:
            raise SelectionError(f"Stage-1 API call failed: {exc}") from exc

        raw, tool_use_id = _extract_tool_input(response)
        if raw is None:
            raise SelectionError("Stage-1 response contained no tool_use block")

        try:
            plan = CompositionPlan.model_validate(raw)
        except ValidationError as exc:
            last_errors = [f"schema: {exc.errors()[:3]}"]
        else:
            plan = normalize_plan(plan, manifest)
            last_errors = validate_plan(plan, manifest)
            if not last_errors:
                return plan

        if attempt + 1 < MAX_PLAN_ATTEMPTS:
            # Feed the violations back once. The echoed tool_use turn MUST be
            # answered with a tool_result block (API contract), carrying the
            # validation errors as an error result.
            messages = messages + [
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_use_id or "unknown",
                    "is_error": True,
                    "content": (
                        "Plan failed validation:\n- "
                        + "\n- ".join(str(e) for e in last_errors)
                        + "\nEmit a corrected CompositionPlan via the tool."
                    ),
                }]},
            ]

    raise SelectionError(f"plan invalid after {MAX_PLAN_ATTEMPTS} attempts: "
                         f"{last_errors}")


def _extract_tool_input(response: Any) -> tuple[Optional[dict], Optional[str]]:
    """Pull (tool input, tool_use id) from an SDK response or dict-shaped fake."""
    content = getattr(response, "content", None)
    if content is None and isinstance(response, dict):
        content = response.get("content")
    for block in content or []:
        is_dict = isinstance(block, dict)
        btype = block.get("type") if is_dict else getattr(block, "type", None)
        if btype == "tool_use":
            binput = block.get("input") if is_dict else getattr(block, "input", None)
            bid = block.get("id") if is_dict else getattr(block, "id", None)
            return (binput if isinstance(binput, dict) else None), bid
    return None, None


# ---------------------------------------------------------------------------
# Stage-2 render + orchestrator
# ---------------------------------------------------------------------------


def render_plan(plan: CompositionPlan, manifest: BriefManifest,
                caution: Optional[str] = None) -> RenderedOverlay:
    """Render a VALIDATED plan. Raises on contract breaches (caller bug)."""
    lines: list[RenderedLine] = []
    seen_bodies: set[tuple] = set()
    for item in plan.items:
        line = render_line(
            template_id=item.template,
            manifest=manifest,
            field_ids=item.fields,
            gap_id=item.gap,
            options=plan.clarify_intents or None,
        )
        # The model may select the same entry under two templates (observed
        # live 2026-07-15) — dedup on the cited entry set, never on text
        # (values can legitimately repeat, e.g. two queried-empty markers).
        key = ("cites",) + tuple(sorted(line.citation_ids)) \
            if line.citation_ids else ("text", line.text)
        if key in seen_bodies:
            continue
        seen_bodies.add(key)
        lines.append(line)

    # Headline: ONLY standalone templates render one (they explain a decline /
    # clarify). Fact plans get headline="" — the UI's own header covers it.
    # (Live polish finding: using lines[0] as headline duplicated the first
    # sentence in header AND body.)
    if plan.headline_template in ("T_SCOPE_DECLINE", "T_CLARIFY", "T_NOT_COVERED"):
        headline_text = render_line(
            template_id=plan.headline_template, manifest=manifest,
            field_ids=[], gap_id=None, options=plan.clarify_intents or None,
        ).text
    else:
        headline_text = ""

    footnotes = assign_footnotes(lines, manifest)
    groups = assemble_groups(lines)
    return RenderedOverlay(headline=headline_text, groups=groups, lines=lines,
                           footnotes=footnotes, declined=plan.declined,
                           caution=caution)


def _incompatible_overlay(reason: str, manifest: BriefManifest) -> RenderedOverlay:
    """Deterministic scope-decline for an intent the property type rules out.

    Live finding #1: the LLM composed a granny-flat plan for an apartment.
    This path never calls the model — the mismatch screen is code."""
    # FIELD rows only: on a renovation brief with a failed strata lookup the
    # strata row is a GAP, which must not render as an empty "fact".
    strata_ids = [e.id for e in manifest.entries
                  if e.path.startswith("strata") and e.kind == EntryKind.FIELD][:1]
    line = render_line("T_SCOPE_DECLINE", manifest, field_ids=strata_ids)
    return RenderedOverlay(
        headline=reason,
        lines=[line],
        declined=True,
        caution=None,
    )


def generate_overlay(
    brief: Union[BaseModel, dict],
    persona: str,
    intent: Optional[str] = None,
    question: Optional[str] = None,
    enabled: Optional[bool] = None,
    client: Any = None,
) -> Optional[RenderedOverlay]:
    """The single entry point. Returns None whenever the overlay should not
    (flag off) or cannot (any failure) be shown — the base brief is never
    affected. This is the additive-only rule in code.
    """
    if not overlay_enabled(enabled):
        return None

    try:
        manifest = build_manifest(brief)

        caution: Optional[str] = None
        if intent is not None:
            compat = check_intent_compatibility(brief, intent)
            if compat.status == CompatibilityStatus.INCOMPATIBLE:
                return _incompatible_overlay(
                    compat.reason or "This intent does not apply to this "
                    "property type.", manifest)
            if compat.status in (CompatibilityStatus.REVIEW,
                                 CompatibilityStatus.UNKNOWN):
                caution = compat.reason

        plan = select_composition(manifest, persona=persona, intent=intent,
                                  question=question, client=client)
        return render_plan(plan, manifest, caution=caution)
    except SelectionError as exc:
        logger.warning("Overlay unavailable (stage-1): %s", exc)
        return None
    except ValueError as exc:
        # Unknown intent string or a render contract breach — log loudly;
        # still additive-only, so the brief itself is unaffected.
        logger.error("Overlay unavailable (contract): %s", exc)
        return None
    except Exception as exc:  # error isolation: overlay must never 500 a brief
        logger.error("Overlay unavailable (unexpected): %s", exc, exc_info=True)
        return None


def overlay_to_dict(overlay: Optional[RenderedOverlay]) -> Optional[dict]:
    """JSON-safe form for API responses; None passes through."""
    return json.loads(overlay.model_dump_json()) if overlay else None
