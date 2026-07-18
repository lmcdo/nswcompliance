"""Stage-2 template registry + narrative renderer for the brief LLM overlay.

prior-art-checked: v2 of the module introduced in #742 — same file, upgraded
from label:value stubs to authored sentence templates with grouped narrative
flow and footnoted provenance. No other module renders manifest-cited prose.

The contract (ce-brief-llm-integration-concepts, Safety architecture) is
unchanged:
- The LLM (Stage-1) selects WHICH manifest entries matter. It never writes prose.
- Every sentence shape here is authored once and liability-scanned at import;
  slot values are copied verbatim from ManifestEntry.value_text (formatting
  like "$1,860,000" happens deterministically in the manifest, never here).
- Confidence passthrough: estimated/stale values carry their qualifier IN the
  sentence; routine authoritative provenance moves to footnotes so the prose
  stays readable without losing a single audit hop.
- Rendered VALUES are manifest data (regulatory quotations / source records —
  e.g. a DA status of "approved"): runtime liability hits on values are
  logged, never dropped. Authored text must always scan clean.
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
# Template registry (ids + reference arity — validated in brief_narration)
# ---------------------------------------------------------------------------


class TemplateArity(BaseModel):
    min_fields: int = 1
    max_fields: int = 1
    needs_gap: bool = False

    model_config = ConfigDict(extra="forbid")


class Template(BaseModel):
    id: str
    arity: TemplateArity

    model_config = ConfigDict(extra="forbid")


def _t(tid: str, min_fields: int = 1, max_fields: int = 1,
       needs_gap: bool = False) -> Template:
    return Template(id=tid, arity=TemplateArity(
        min_fields=min_fields, max_fields=max_fields, needs_gap=needs_gap,
    ))


TEMPLATES: dict[str, Template] = {t.id: t for t in [
    _t("T_ZONE_CONTEXT", min_fields=1, max_fields=4),
    _t("T_CONTROL_VALUE"),
    _t("T_ELIGIBILITY"),
    _t("T_CONSTRAINT_FLAG"),
    _t("T_CAPACITY_RESULT"),
    _t("T_NEARBY_ACTIVITY"),
    _t("T_MARKET_FACT"),
    _t("T_FINDING"),
    _t("T_GAP_ROUTE", min_fields=0, max_fields=0, needs_gap=True),
    _t("T_SCOPE_DECLINE", min_fields=0, max_fields=10),
    _t("T_CLARIFY", min_fields=0, max_fields=0),
    _t("T_NOT_COVERED", min_fields=0, max_fields=1),
]}

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

STANDALONE_TEMPLATE_IDS = frozenset(STANDALONE_TEXT.keys())

# Fact templates that may only cite authoritative/extracted planning sources.
# The live overlay dressed capacity-engine outputs as "Planning control" — a
# computed setback is not THE control. brief_narration remaps derived-source
# fields cited under these templates to T_CAPACITY_RESULT deterministically.
AUTHORITATIVE_FACT_TEMPLATES = frozenset({"T_CONTROL_VALUE", "T_ZONE_CONTEXT"})
COMPUTED_SOURCES = frozenset({"constraint_arithmetic_engine"})

# Narrative grouping: template → group, rendered in GROUP_ORDER with authored
# sub-headers. Grouping is deterministic — the model's relevance ordering is
# preserved WITHIN each group.
TEMPLATE_GROUP: dict[str, str] = {
    "T_ZONE_CONTEXT": "planning",
    "T_CONTROL_VALUE": "planning",
    "T_CONSTRAINT_FLAG": "planning",
    "T_ELIGIBILITY": "eligibility",
    "T_CAPACITY_RESULT": "capacity",
    "T_FINDING": "cautions",
    "T_GAP_ROUTE": "cautions",
    "T_NEARBY_ACTIVITY": "context",
    "T_MARKET_FACT": "context",
    "T_SCOPE_DECLINE": "lead",
    "T_CLARIFY": "lead",
    "T_NOT_COVERED": "lead",
}

GROUP_ORDER = ["lead", "planning", "eligibility", "capacity", "cautions", "context"]

GROUP_HEADERS: dict[str, str] = {
    "lead": "",
    "planning": "The planning picture",
    "eligibility": "Eligibility under state policy",
    "capacity": "What the numbers work out to",
    "cautions": "Worth checking",
    "context": "Neighbourhood and market",
}


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
# Provenance display
# ---------------------------------------------------------------------------

SOURCE_DISPLAY: dict[str, str] = {
    "planning_portal": "NSW Planning Portal",
    "lep_land_use_table": "LEP land use table",
    "housing_sepp_standards": "SEPP (Housing) 2021 standards",
    "constraint_arithmetic_engine": "capacity engine (computed)",
    "nsw_valuation_service": "NSW Valuer General",
    "nsw_valuer_general": "NSW Valuer General",
    "nsw_valuer_general_sales": "NSW Valuer General sales",
    "cadastre_strata": "NSW cadastre",
    "eplanning_da_api": "NSW ePlanning DA feed",
    "da_tracking_mapserver": "NSW DA tracking extract",
    "postgis_overlays": "NSW planning overlays",
    "postgis_heritage": "NSW heritage mapping",
    "plotdetect_dcp": "council DCP (extracted)",
    "sepp_resilience_hazards": "SEPP (Resilience and Hazards) 2021",
    "planning_portal_protection": "NSW Planning Portal protection layers",
    "shadow_detector": "shadow model (computed)",
    "epa_contaminated_sites": "NSW EPA contaminated-land register",
    "nsw_spatial_services": "NSW Spatial Services",
    "live_protection_overlay": "NSW protection overlays",
}


def source_display(source: Optional[str]) -> str:
    if not source:
        return "unrecorded source"
    return SOURCE_DISPLAY.get(source, source.replace("_", " "))


_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def display_date(as_at: Optional[str]) -> Optional[str]:
    """ISO dates → '15 Jul 2026'; anything else passes through verbatim."""
    if not as_at:
        return None
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", as_at.strip())
    if not m:
        return as_at
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not 1 <= mo <= 12:
        return as_at
    return f"{d} {_MONTHS[mo - 1]} {y}"


class Footnote(BaseModel):
    marker: int
    source: str  # display form
    as_at: Optional[str] = None  # display form
    confidence: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Rendered output models
# ---------------------------------------------------------------------------


class RenderedLine(BaseModel):
    """One sentence of the overlay. ``text`` is authored-template output with
    verbatim manifest values; never re-parsed."""

    template_id: str
    text: str
    citation_ids: list[str] = []  # manifest entry ids — the UI's jump chips
    citation_paths: list[str] = []  # matching manifest paths (section anchors)
    footnotes: list[int] = []  # markers into RenderedOverlay.footnotes
    tone: str = "fact"  # fact | warning | info
    liability_flags: list[str] = []  # runtime hits (data passthrough) — logged

    model_config = ConfigDict(extra="forbid")


class RenderedGroup(BaseModel):
    key: str
    header: str  # authored sub-header ("" for the lead group)
    lines: list[RenderedLine]

    model_config = ConfigDict(extra="forbid")


class RenderedOverlay(BaseModel):
    headline: str
    groups: list[RenderedGroup] = []
    lines: list[RenderedLine] = []  # flat, in plan order (compat + tests)
    footnotes: list[Footnote] = []
    declined: bool = False
    caution: Optional[str] = None  # deterministic pre-check note, if any

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------

_LABEL_OVERRIDES = {
    "fsr": "floor space ratio",
    "anef": "ANEF aircraft noise",
    "tod_area": "TOD area",
    "dcp": "DCP",
    "sepp": "SEPP",
    "lep": "LEP",
    "gfa": "GFA",
    "epi": "planning instrument",
}

# Whole-leaf rewrites for engine field names that read badly even after
# word-by-word humanising.
_LEAF_LABEL_OVERRIDES = {
    "lep_envelope_gfa_m2": "the maximum floor area under the LEP envelope",
    "dcp_envelope_gfa_m2": "the floor area after council DCP controls",
    "as_of_right_dwellings": "dwellings as of right",
    "realistic_dwellings": "the realistic dwelling count",
    "setback_front_m": "the front setback",
    "setback_side_m": "the side setback",
    "setback_rear_m": "the rear setback",
    "parking_spaces_required": "parking spaces required",
    "max_storeys": "the maximum storeys",
    "lot_size": "minimum lot size",
}


def label_for_path(path: str) -> str:
    """Humanize a manifest path: 'planning_controls.height' → 'height'."""
    if not path or not path.strip():
        return ""
    leaf = path.strip().split(".")[-1]
    bare = re.sub(r"\[(\d+)\]", "", leaf)
    if bare in _LEAF_LABEL_OVERRIDES:
        return _LEAF_LABEL_OVERRIDES[bare]
    leaf = re.sub(r"\[(\d+)\]", r" #\1", leaf)
    words = [
        _LABEL_OVERRIDES.get(w.lower(), w)
        for w in leaf.replace("_", " ").split()
    ]
    return " ".join(words)


# ---------------------------------------------------------------------------
# Record parsing — 'k=v; …' is OUR OWN format (brief_manifest._summarise_record),
# so parsing it back is deterministic round-tripping, not model output parsing.
# ---------------------------------------------------------------------------


def parse_record_text(value_text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in value_text.split(";"):
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        out[k.strip()] = v.strip()
    return out


def _dev_type_label(raw: str) -> str:
    words = raw.replace("_", " ").strip()
    return words[:1].upper() + words[1:] if words else raw


# A value_text still in our 'k=v; …' record format must never reach the overlay
# verbatim (the live overlay printed "is_bushfire_prone=True; category=…" raw).
_RECORD_DUMP_RE = re.compile(r"^\s*[A-Za-z_]\w*=")


def looks_like_record_dump(value_text: str) -> bool:
    """True when a value serialises as key=value pairs rather than prose."""
    return bool(value_text) and bool(_RECORD_DUMP_RE.match(value_text))


def _composite_sentence(e: ManifestEntry) -> Optional[str]:
    """Authored sentences for known composite records (bushfire, lot dimensions).

    Returns None when the record is not a known composite — callers then fall
    back to the section-card reference, never the raw dump.
    """
    if not looks_like_record_dump(e.value_text):
        return None
    rec = parse_record_text(e.value_text)
    if not rec:
        return None
    if "is_bushfire_prone" in rec:
        prone = rec.get("is_bushfire_prone")
        if prone == "True":
            category = rec.get("category") or rec.get("designation_category")
            bal = rec.get("bal_estimate") or rec.get("estimated_bal_band")
            detail_bits = [b for b in (
                category, f"indicative {bal}" if bal else None,
            ) if b]
            detail = f" ({', '.join(detail_bits)})" if detail_bits else ""
            return f"This lot is mapped bush fire prone{detail}."
        if prone == "False":
            return "The RFS mapping does not list this lot as bush fire prone."
        return None
    if rec.get("frontage_m") and rec.get("depth_m"):
        area = rec.get("area_m2") or rec.get("lot_area_m2")
        if area:
            return (f"The lot is {area} m², about {rec['frontage_m']} m × "
                    f"{rec['depth_m']} m.")
        return f"The lot is about {rec['frontage_m']} m × {rec['depth_m']} m."
    return None


def _card_reference(e: ManifestEntry) -> str:
    """Refusal line for a record-shaped value with no authored composite."""
    return (f"The full {label_for_path(e.path)} detail is in its "
            f"section card below.")


def _guard_record_dump(e: ManifestEntry, fallback: str) -> str:
    """Composite sentence if known, section-card reference if record-shaped,
    otherwise the caller's own sentence."""
    comp = _composite_sentence(e)
    if comp:
        return comp
    if looks_like_record_dump(e.value_text):
        return _card_reference(e)
    return fallback


# ---------------------------------------------------------------------------
# Sentence builders — every authored fragment is liability-scanned at import.
# ---------------------------------------------------------------------------


# Machine tokens that reach a manifest value slot (observed live: the capacity
# engine's binding_constraint enum rendered raw as "lep_fsr"). Exact-match map
# first; any other lone snake_case token degrades to spaced words, never raw.
MACHINE_VALUE_LABELS: dict[str, str] = {
    "lep_height": "the LEP height limit",
    "lep_fsr": "the LEP floor space ratio",
    "dcp_setbacks": "the DCP setbacks",
    "dcp_site_coverage": "the DCP site coverage control",
    "dcp_landscaping": "the DCP landscaped area control",
    "dcp_deep_soil": "the DCP deep soil control",
    "shadow_access": "the DCP solar access control",
    "parking": "the DCP parking control",
    "lot_size": "the LEP minimum lot size",
    "sepp_override": "the SEPP development standard",
}

_SNAKE_TOKEN_RE = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+")


def humanise_value(text: str) -> str:
    mapped = MACHINE_VALUE_LABELS.get(text)
    if mapped:
        return mapped
    if _SNAKE_TOKEN_RE.fullmatch(text):
        return text.replace("_", " ")
    return text


def _confidence_qualifier(conf: Optional[str]) -> str:
    """Inline qualifier for non-clean confidence — never footnoted away."""
    if conf == "estimated":
        return " (satellite-estimated)"
    if conf == "stale":
        return " (data past its currency window)"
    return ""


def _join_and(items: list[str]) -> str:
    if len(items) <= 1:
        return items[0] if items else ""
    return ", ".join(items[:-1]) + " and " + items[-1]


def _zone_sentence(entries: list[ManifestEntry]) -> str:
    by_leaf = {e.path.rsplit(".", 1)[-1]: e for e in entries}
    head = ""
    zone = by_leaf.get("zone")
    if zone:
        head = f"This lot is zoned {zone.value_text}"
        if by_leaf.get("zone_full"):
            head += f" — {by_leaf['zone_full'].value_text}"
        if by_leaf.get("zone_epi"):
            head += f" under the {by_leaf['zone_epi'].value_text}"
    extras: list[str] = []
    trailing: list[str] = []  # composite records render as their own sentence
    for leaf, e in by_leaf.items():
        if leaf in ("zone", "zone_full", "zone_epi"):
            continue
        if leaf == "height":
            extras.append(f"a height limit of {e.value_text}")
        elif leaf in ("fsr", "floor_space_ratio"):
            extras.append(f"a floor space ratio of {e.value_text}")
        elif leaf == "lot_size":
            extras.append(f"a minimum lot size of {e.value_text}")
        elif looks_like_record_dump(e.value_text):
            # A composite record (lot dimensions, bushfire) must never be
            # inlined as "a … of k=v; k=v" — it gets an authored sentence or
            # a section-card reference of its own.
            trailing.append(_composite_sentence(e) or _card_reference(e))
        else:
            extras.append(f"a {label_for_path(e.path)} of {e.value_text}")
    if head and extras:
        head_sentence = f"{head}, with {_join_and(extras)}."
    elif head:
        head_sentence = f"{head}."
    elif extras:
        head_sentence = f"The mapped controls set {_join_and(extras)}."
    else:
        head_sentence = ""
    return " ".join(s for s in [head_sentence, *trailing] if s)


def _dcp_control_sentence(e: ManifestEntry) -> Optional[str]:
    """Flattened DCP control rows render as a clause sentence, not a record dump."""
    rec = parse_record_text(e.value_text)
    ctype = rec.get("control_type")
    if not ctype:
        return None
    label = ctype.replace("_", " ")
    value = rec.get("value_min") or rec.get("value_max") or rec.get("value")
    unit = rec.get("unit") or ""
    parts = f"The council DCP sets {label}"
    if value:
        if unit == "%":
            parts += f" at {value}%"
        elif unit:
            parts += f" at {value} {unit}"
        else:
            parts += f" at {value}"
    if rec.get("dev_type"):
        parts += f" for a {rec['dev_type'].replace('_', ' ')}"
    if rec.get("condition"):
        parts += f" ({rec['condition']})"
    if rec.get("source_ref"):
        ref = rec["source_ref"]
        # "clause 4.1.2" reads right; "clause Table 1" does not.
        parts += f" — clause {ref}" if ref[:1].isdigit() else f" — see {ref}"
    return parts + "."


def _control_sentence(e: ManifestEntry) -> str:
    if e.path.startswith("dcp_controls.controls["):
        dcp = _dcp_control_sentence(e)
        if dcp:
            return dcp
    return _guard_record_dump(e, (
        f"The {label_for_path(e.path)} for this lot is "
        f"{humanise_value(e.value_text)}{_confidence_qualifier(e.confidence)}."
    ))


def _capacity_sentence(e: ManifestEntry) -> str:
    return _guard_record_dump(e, (
        f"Computed from the planning controls, "
        f"{label_for_path(e.path)} works out to {humanise_value(e.value_text)}."
    ))


_FALSY_VALUE_TEXTS = frozenset({"False", "No", "—", "None", "none"})


def _overlays_sentence(e: ManifestEntry) -> Optional[str]:
    if not e.path.rsplit(".", 1)[-1].startswith("overlays"):
        return None
    bits: list[str] = []
    for chunk in e.value_text.split("//"):
        rec = parse_record_text(chunk)
        if rec.get("layer_type"):
            bit = rec["layer_type"].replace("_", " ")
            if rec.get("value"):
                bit += f" ({rec['value']})"
            bits.append(bit)
    if not bits:
        return None
    return f"Mapped planning overlays on this lot: {_join_and(bits)}."


def _constraint_sentence(e: ManifestEntry) -> str:
    overlays = _overlays_sentence(e)
    if overlays:
        return overlays
    if e.value_text in _FALSY_VALUE_TEXTS:
        return f"The {label_for_path(e.path)} check found none recorded."
    if e.value_text == "True":
        return (f"A {label_for_path(e.path)} designation is recorded — "
                f"see the full card below.")
    return _guard_record_dump(e, (
        f"{label_for_path(e.path).capitalize()}: "
        f"{humanise_value(e.value_text)}{_confidence_qualifier(e.confidence)}."
    ))


def _eligibility_sentence(e: ManifestEntry) -> str:
    rec = parse_record_text(e.value_text)
    dev = rec.get("dev_type")
    if not dev:
        return _guard_record_dump(
            e, f"{label_for_path(e.path).capitalize()}: {e.value_text}.")
    label = _dev_type_label(dev)
    standards: list[str] = []
    if rec.get("min_lot_area_m2"):
        standards.append(f"minimum lot area {rec['min_lot_area_m2']} m²")
    if rec.get("min_lot_width_m"):
        standards.append(f"minimum width {rec['min_lot_width_m']} m")
    caps: list[str] = []
    if rec.get("max_gfa_m2"):
        caps.append(f"{rec['max_gfa_m2']} m² of floor area")
    if rec.get("max_height_m"):
        caps.append(f"{rec['max_height_m']} m in height")
    if rec.get("max_fsr"):
        caps.append(f"a floor space ratio of {rec['max_fsr']}")
    if rec.get("min_private_open_space_m2"):
        caps.append(f"{rec['min_private_open_space_m2']} m² of private open space")
    eligible = rec.get("eligible")
    if eligible == "True":
        status = "the dataset lists this lot as meeting the lot standard"
    elif eligible == "False":
        status = "the dataset lists this lot as not meeting the lot standard"
    else:
        status = "the dataset does not state a lot-standard outcome for this lot"
    sentence = f"{label} under SEPP (Housing) 2021: {status}"
    if standards:
        sentence += f" ({_join_and(standards)})"
    sentence += "."
    if caps:
        sentence += f" The form itself is limited to {_join_and(caps)}."
    return sentence


def _finding_line(e: ManifestEntry) -> tuple[str, str]:
    """Returns (text, tone). Finding value_text is 'severity=…; description'."""
    sev = "info"
    text = e.value_text
    m = re.match(r"severity=(\w+);\s*(.*)", e.value_text, re.DOTALL)
    if m:
        sev = m.group(1)
        text = m.group(2).strip() or e.value_text
    if looks_like_record_dump(text):
        # A record-shaped remainder (e.g. a summarised override dict) never
        # renders raw — point at the section card instead.
        text = _card_reference(e)
    return text, ("warning" if sev == "warning" else "info")


def _activity_sentence(e: ManifestEntry) -> str:
    leaf = re.sub(r"\[(\d+)\]", "", e.path.rsplit(".", 1)[-1])
    if leaf == "land_value":
        return (f"The NSW Valuer General's land value for this lot is "
                f"{e.value_text} (land only — it excludes buildings).")
    if leaf == "comparables":
        rec = parse_record_text(e.value_text)
        if rec.get("comparable_count") and rec.get("median_value"):
            text = (f"Within the comparison radius, {rec['comparable_count']} "
                    f"comparable lots have a median land value of "
                    f"{rec['median_value']}")
            if rec.get("subject_value"):
                text += f"; this lot's is {rec['subject_value']}"
            if rec.get("percentile_rank"):
                text += (f", at the {rec['percentile_rank']} percentile of "
                         f"the comparable set")
            return text + "."
    if leaf in ("nearby_das", "recent_sales"):
        m = re.match(r"\[(\d+) records?\]", e.value_text)
        if m:
            noun = ("development applications lodged nearby"
                    if leaf == "nearby_das" else "recorded sales nearby")
            return (f"There are {m.group(1)} {noun} — the full list is in "
                    f"the section card below.")
    return _guard_record_dump(e, (
        f"Recorded {label_for_path(e.path)}: "
        f"{e.value_text}{_confidence_qualifier(e.confidence)}."
    ))


def render_gap_line(entry: ManifestEntry) -> str:
    reason = entry.reason or "no reason recorded"
    fallback = source_display(entry.source) if entry.source else "no fallback source recorded"
    return (f"Not checked — {label_for_path(entry.path)}: {reason}. "
            f"Where to look instead: {fallback}.")


def render_standalone(template_id: str, options: list[str]) -> str:
    text = STANDALONE_TEXT[template_id]
    return text.format(options=", ".join(options) if options else "none listed")


# ---------------------------------------------------------------------------
# render_line — one plan item → one RenderedLine
# ---------------------------------------------------------------------------


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
    tone = "fact"

    if template.arity.needs_gap:
        if not gap_id:
            raise ValueError(f"{template_id} requires a gap id")
        entry = by_id[gap_id]
        if entry.kind != EntryKind.GAP:
            raise ValueError(f"{template_id} given non-gap id {gap_id}")
        text = render_gap_line(entry)
        citations = [gap_id]
        tone = "warning"
    elif template_id in STANDALONE_TEMPLATE_IDS:
        text = render_standalone(template_id, options or [])
        citations = list(field_ids)
        if citations:
            facts = [_activity_sentence(by_id[fid]) for fid in citations]
            text = text + " " + " ".join(facts)
    else:
        entries = [by_id[fid] for fid in field_ids]
        if not (template.arity.min_fields <= len(entries) <= template.arity.max_fields):
            raise ValueError(
                f"{template_id} takes {template.arity.min_fields}-"
                f"{template.arity.max_fields} fields, got {len(entries)}"
            )
        citations = list(field_ids)
        if template_id == "T_ZONE_CONTEXT":
            text = _zone_sentence(entries)
        elif template_id == "T_CONTROL_VALUE":
            text = _control_sentence(entries[0])
        elif template_id == "T_CAPACITY_RESULT":
            text = _capacity_sentence(entries[0])
        elif template_id == "T_CONSTRAINT_FLAG":
            text = _constraint_sentence(entries[0])
        elif template_id == "T_ELIGIBILITY":
            text = _eligibility_sentence(entries[0])
        elif template_id == "T_FINDING":
            text, tone = _finding_line(entries[0])
        else:  # T_NEARBY_ACTIVITY, T_MARKET_FACT
            text = _activity_sentence(entries[0])

    flags = scan_liability(text)
    if flags:
        # Values are manifest data (factual passthrough — e.g. a DA status of
        # "approved"); authored template text is proven clean by tests. Log,
        # never silently drop a fact line.
        logger.warning("Liability terms in rendered data for %s: %s",
                       template_id, flags)
    citation_paths = [by_id[c].path for c in citations if c in by_id]
    return RenderedLine(template_id=template_id, text=text,
                        citation_ids=citations, citation_paths=citation_paths,
                        tone=tone, liability_flags=flags)


# ---------------------------------------------------------------------------
# Overlay assembly — footnotes + grouped narrative
# ---------------------------------------------------------------------------


def assign_footnotes(
    lines: list[RenderedLine], manifest: BriefManifest,
) -> list[Footnote]:
    """Attach numbered footnote markers per unique (source, as_at, confidence).

    Estimated/stale values ALSO carry an inline qualifier from the sentence
    builders, so a footnote can never launder a satellite guess into a stated
    fact — only routine provenance bookkeeping moves out of the prose.
    """
    by_id = {e.id: e for e in manifest.entries}
    table: dict[tuple, int] = {}
    footnotes: list[Footnote] = []
    for line in lines:
        marks: list[int] = []
        for cid in line.citation_ids:
            entry = by_id.get(cid)
            if entry is None or not entry.source:
                continue
            key = (entry.source, entry.as_at, entry.confidence)
            if key not in table:
                table[key] = len(table) + 1
                footnotes.append(Footnote(
                    marker=table[key],
                    source=source_display(entry.source),
                    as_at=display_date(entry.as_at),
                    confidence=entry.confidence,
                ))
            if table[key] not in marks:
                marks.append(table[key])
        line.footnotes = marks
    return footnotes


def assemble_groups(lines: list[RenderedLine]) -> list[RenderedGroup]:
    """Deterministic narrative grouping; plan (relevance) order kept in-group."""
    buckets: dict[str, list[RenderedLine]] = {}
    for line in lines:
        group = TEMPLATE_GROUP.get(line.template_id, "context")
        buckets.setdefault(group, []).append(line)
    return [
        RenderedGroup(key=g, header=GROUP_HEADERS[g], lines=buckets[g])
        for g in GROUP_ORDER if buckets.get(g)
    ]


# ---------------------------------------------------------------------------
# Authored-text liability audit (import-time)
# ---------------------------------------------------------------------------

_AUTHORED_FRAGMENTS = [
    *STANDALONE_TEXT.values(),
    *GROUP_HEADERS.values(),
    *_LEAF_LABEL_OVERRIDES.values(),
    "This lot is zoned — under the , with a height limit of a floor space "
    "ratio of a minimum lot size of and The mapped controls set",
    "The for this lot is Computed from the planning controls, works out to",
    "The check found none recorded. A designation is recorded — see the full "
    "card below.",
    "under SEPP (Housing) 2021: the dataset lists this lot as meeting the lot "
    "standard the dataset lists this lot as not meeting the lot standard "
    "the dataset does not state a lot-standard outcome for this lot "
    "minimum lot area minimum width The form itself is limited to "
    "of floor area in height a floor space ratio of of private open space",
    "The NSW Valuer General's land value for this lot is (land only — it "
    "excludes buildings). Recorded",
    "The council DCP sets at for a — clause",
    "Within the comparison radius, comparable lots have a median land value "
    "of this lot's is at the percentile of the comparable set",
    "There are development applications lodged nearby recorded sales nearby "
    "— the full list is in the section card below.",
    "Not checked — Where to look instead: no reason recorded no fallback "
    "source recorded",
    "Mapped planning overlays on this lot:",
    "(satellite-estimated) (data past its currency window)",
    # Composite-record sentences + the record-dump refusal line
    "This lot is mapped bush fire prone (, indicative ) "
    "The RFS mapping does not list this lot as bush fire prone.",
    "The lot is m², about m × m. The lot is about m × m.",
    "The full detail is in its section card below.",
]


def assert_templates_clean() -> None:
    """Authored sentence fragments must never contain advisory language."""
    for fragment in _AUTHORED_FRAGMENTS:
        flags = scan_liability(fragment.replace("{options}", ""))
        if flags:
            raise ValueError(f"Authored template text contains flagged terms "
                             f"{flags}: {fragment[:80]!r}")


assert_templates_clean()
