"""Stage-2 template registry + renderer for the brief LLM overlay.

prior-art-checked: reviewed services/brief_manifest.py (serializes facts, does
not render prose), services/conveyancing.py + pdf paths (render the PDF report
surface, not manifest-cited overlay lines), and the frontend brief page (renders
section cards from JSON); no existing module renders manifest entries through a
pre-approved sentence-template set, which ce-brief-llm-integration-concepts §
Safety architecture specifies as the new Stage-2 half of the two-stage design.

The contract (ce-brief-llm-integration-concepts, Safety architecture):
- The LLM (Stage-1) selects WHICH manifest entries matter and WHICH template
  renders each. It never writes prose.
- This module owns every word the user reads. A fact can only appear if it
  exists in the manifest; a number can never be paraphrased — values are
  copied verbatim from ManifestEntry.value_text.
- Confidence language passthrough: every fact line carries the entry's own
  confidence and source; templates cannot upgrade or soften them.
- Liability: template text is authored here and scanned against the same
  FLAGGED_TERMS list the pre-push hook uses (mirrored below with a sync test).
  Rendered VALUES are manifest data (regulatory quotations / source records —
  e.g. a DA status of "approved"), which the language-audit policy classes as
  factual passthrough, so runtime hits on values are logged, not dropped.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from pydantic import BaseModel, ConfigDict

from services.brief_manifest import BriefManifest, EntryKind, ManifestEntry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Liability gate — mirror of scripts/liability_language_check.py FLAGGED_TERMS.
# Kept import-free (scripts/ is not a package); a sync test asserts the two
# patterns stay byte-identical.
# ---------------------------------------------------------------------------

FLAGGED_TERMS = re.compile(
    r'\b('
    r'safe|feasible|compliant|(?<!should_)should(?!_)|recommend|suitable|'
    r'adequate|sufficient|approved|guaranteed|certified|confirmed|verified|'
    r'ensure|assure|accurate|definitive|comprehensive|reliable'
    r')\b',
    re.IGNORECASE,
)


def scan_liability(text: str) -> list[str]:
    """Return flagged advisory terms found in text (empty list = clean)."""
    if not text:
        return []
    return [m.group(0) for m in FLAGGED_TERMS.finditer(text)]


# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------


class TemplateArity(BaseModel):
    """How many manifest references a template consumes."""

    min_fields: int = 1
    max_fields: int = 1
    needs_gap: bool = False

    model_config = ConfigDict(extra="forbid")


class Template(BaseModel):
    id: str
    lead_in: str  # authored phrase that opens the line — liability-scanned
    arity: TemplateArity

    model_config = ConfigDict(extra="forbid")


def _t(tid: str, lead_in: str, min_fields: int = 1, max_fields: int = 1,
       needs_gap: bool = False) -> Template:
    return Template(id=tid, lead_in=lead_in, arity=TemplateArity(
        min_fields=min_fields, max_fields=max_fields, needs_gap=needs_gap,
    ))


# Standalone templates carry their full authored sentence here; per-field
# templates carry only a lead-in — the body is always the entry's own data.
STANDALONE_TEXT: dict[str, str] = {
    "T_SCOPE_DECLINE": (
        "This brief presents factual planning data only. It does not weigh "
        "approval prospects, project outcomes, or fitness for a purpose — "
        "those are matters for a qualified town planner. The facts it can "
        "show for this question are below."
    ),
    "T_CLARIFY": (
        "This view can be focused once an intent is chosen. Candidate "
        "intents: {options}."
    ),
    "T_NOT_COVERED": (
        "This brief does not cover that topic. Nearest related source: "
        "{options}."
    ),
}

TEMPLATES: dict[str, Template] = {t.id: t for t in [
    _t("T_ZONE_CONTEXT", "Zoning context", min_fields=1, max_fields=4),
    _t("T_CONTROL_VALUE", "Planning control"),
    _t("T_ELIGIBILITY", "Eligibility data"),
    _t("T_CONSTRAINT_FLAG", "Constraint check"),
    _t("T_CAPACITY_RESULT", "Computed envelope"),
    _t("T_NEARBY_ACTIVITY", "Nearby activity"),
    _t("T_MARKET_FACT", "Market data"),
    _t("T_FINDING", "Finding"),
    _t("T_GAP_ROUTE", "Not checked", min_fields=0, max_fields=0, needs_gap=True),
    _t("T_SCOPE_DECLINE", "", min_fields=0, max_fields=10),
    _t("T_CLARIFY", "", min_fields=0, max_fields=0),
    _t("T_NOT_COVERED", "", min_fields=0, max_fields=1),
]}

# Templates whose authored text lives in STANDALONE_TEXT.
STANDALONE_TEMPLATE_IDS = frozenset(STANDALONE_TEXT.keys())


def capabilities_block() -> str:
    """Deterministic CAPABILITIES text for the Stage-1 prompt."""
    lines = ["CAPABILITIES", "templates:"]
    for tid in sorted(TEMPLATES):
        t = TEMPLATES[tid]
        if t.arity.needs_gap:
            sig = "gap: 1 G id"
        elif t.arity.max_fields == 0:
            sig = "no manifest refs"
        else:
            sig = f"fields: {t.arity.min_fields}-{t.arity.max_fields} F/X ids"
        lines.append(f"  {tid}({sig})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


class RenderedLine(BaseModel):
    template_id: str
    text: str
    citation_ids: list[str] = []  # manifest entry ids — the UI's citation chips
    liability_flags: list[str] = []  # runtime hits (data passthrough) — logged

    model_config = ConfigDict(extra="forbid")


class RenderedOverlay(BaseModel):
    headline: str
    lines: list[RenderedLine]
    declined: bool = False
    caution: Optional[str] = None  # deterministic pre-check note, if any

    model_config = ConfigDict(extra="forbid")


_LABEL_OVERRIDES = {
    "fsr": "floor space ratio (FSR)",
    "anef": "ANEF aircraft noise",
    "tod_area": "TOD area",
    "dcp": "DCP",
    "sepp": "SEPP",
    "lep": "LEP",
}


def label_for_path(path: str) -> str:
    """Humanize a manifest path: 'planning_controls.height' → 'height'."""
    if not path or not path.strip():
        return ""
    leaf = path.strip().split(".")[-1]
    leaf = re.sub(r"\[(\d+)\]", r" #\1", leaf)
    words = [
        _LABEL_OVERRIDES.get(w.lower(), w)
        for w in leaf.replace("_", " ").split()
    ]
    return " ".join(words)


def _provenance_suffix(entry: ManifestEntry) -> str:
    parts = []
    if entry.confidence:
        parts.append(entry.confidence)
    if entry.source:
        parts.append(f"source: {entry.source}")
    if entry.as_at:
        parts.append(f"as at {entry.as_at}")
    return f" ({'; '.join(parts)})" if parts else ""


def render_field_line(template: Template, entries: list[ManifestEntry]) -> str:
    """One fact line: authored lead-in + verbatim entry data + provenance."""
    bodies = []
    for e in entries:
        if e.kind == EntryKind.FINDING:
            bodies.append(f"{label_for_path(e.path)}: {e.value_text}")
        else:
            bodies.append(
                f"{label_for_path(e.path)}: {e.value_text}{_provenance_suffix(e)}"
            )
    joined = "; ".join(bodies)
    return f"{template.lead_in} — {joined}" if template.lead_in else joined


def render_gap_line(entry: ManifestEntry) -> str:
    reason = entry.reason or "no reason recorded"
    fallback = entry.source or "no fallback source recorded"
    return (f"Not checked — {label_for_path(entry.path)}: {reason}. "
            f"Where to look instead: {fallback}.")


def render_standalone(template_id: str, options: list[str]) -> str:
    text = STANDALONE_TEXT[template_id]
    return text.format(options=", ".join(options) if options else "none listed")


def render_line(
    template_id: str,
    manifest: BriefManifest,
    field_ids: list[str],
    gap_id: Optional[str] = None,
    options: Optional[list[str]] = None,
) -> RenderedLine:
    """Render one plan item. Raises KeyError/ValueError on contract breaches —
    callers must validate the plan first (brief_narration.validate_plan)."""
    template = TEMPLATES[template_id]  # KeyError = unvalidated plan, a bug
    by_id = {e.id: e for e in manifest.entries}

    if template.arity.needs_gap:
        if not gap_id:
            raise ValueError(f"{template_id} requires a gap id")
        entry = by_id[gap_id]
        if entry.kind != EntryKind.GAP:
            raise ValueError(f"{template_id} given non-gap id {gap_id}")
        text = render_gap_line(entry)
        citations = [gap_id]
    elif template_id in STANDALONE_TEMPLATE_IDS:
        text = render_standalone(template_id, options or [])
        citations = list(field_ids)
        if citations:
            entries = [by_id[fid] for fid in citations]
            text = text + " " + render_field_line(
                _t("_facts", "Relevant facts", 1, len(entries)), entries
            )
    else:
        entries = [by_id[fid] for fid in field_ids]
        if not (template.arity.min_fields <= len(entries) <= template.arity.max_fields):
            raise ValueError(
                f"{template_id} takes {template.arity.min_fields}-"
                f"{template.arity.max_fields} fields, got {len(entries)}"
            )
        text = render_field_line(template, entries)
        citations = list(field_ids)

    flags = scan_liability(text)
    if flags:
        # Values are manifest data (factual passthrough — e.g. DA status
        # "approved"); authored template text is proven clean by tests. Log,
        # never silently drop a fact line.
        logger.warning("Liability terms in rendered data for %s: %s",
                       template_id, flags)
    return RenderedLine(template_id=template_id, text=text,
                        citation_ids=citations, liability_flags=flags)


def assert_templates_clean() -> None:
    """Authored template text must never contain advisory language.

    Called at import in tests; raising here (not warn) is correct because a
    flagged authored phrase is a build error, not a data condition.
    """
    for tid, t in TEMPLATES.items():
        flags = scan_liability(t.lead_in)
        if flags:
            raise ValueError(f"Template {tid} lead-in contains flagged terms: {flags}")
    for tid, text in STANDALONE_TEXT.items():
        flags = scan_liability(text.replace("{options}", ""))
        if flags:
            raise ValueError(f"Template {tid} text contains flagged terms: {flags}")


assert_templates_clean()
