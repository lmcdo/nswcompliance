"""Brief manifest serializer — deterministic fact table for LLM Stage-1 and the MCP agent feed.

prior-art-checked: reviewed services/intelligence_brief.py (AssessmentManifest at
:786 is the climate-disclosure coverage tracker — counts sources queried vs
successful, no field-level serialization) and the frontend brief page (renders
sections, does not serialize a fact table); no existing module produces a
stable-ID field/gap/finding table, which both ce-brief-llm-integration-concepts
§1 and ce-mcp-agent-feed-execution-plan §1.1 specify as a new shared component.

Turns an assembled intelligence brief (DevelopmentBrief / RenovationBrief, or its
``model_dump()`` dict) into a stable-ID manifest:

    FIELD | path | value | confidence | source | as_at
    F001  | planning_controls.zone | R3 | authoritative | planning_portal | 2026-07-14
    G001  | GAP environmental_constraints.coastal_hazards | reason=... | fallback=...
    X001  | FINDING marginal_lot_size | severity=warning | ...

Contract (ce-brief-llm-integration-concepts §1, Addendum):
- Deterministic: same brief content → byte-identical prompt block and data_hash.
- Three-state per the DataField contract (intelligence_brief.py:174):
  value present → FIELD; value None with no reason → FIELD marked queried-empty,
  confidence badge preserved; value None with reason → GAP with fallback source.
- Fail-closed provenance: a DataField-shaped node missing source or confidence is
  OMITTED and recorded in ``warnings`` — never served bare.
- Decision-critical lists (DCP controls, SEPP standards, eligibility forms) are
  flattened one row per record; live-validation finding 2026-07-15 showed the
  compacted "[7 records]" form hid the single most relevant field from Stage-1.

Distinct from ``AssessmentManifest`` in intelligence_brief.py, which is the climate
disclosure coverage tracker (sources queried vs successful) — not a field table.

This module deliberately does NOT import intelligence_brief: it operates on dumped
dicts so the MCP feed can reuse it without pulling FastAPI/psycopg2 dependencies.
A contract test asserts the mirrored enum values stay in sync.
"""

from __future__ import annotations

import hashlib
import logging
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Path fragments whose subtrees are never decision-relevant to a reader and
# bloat the prompt (raw geometries, service timings, internal plumbing).
EXCLUDED_PATH_TOKENS: tuple[str, ...] = (
    "geometry", "wkt", "polygon", "coordinates", "timings", "boundary",
)

# Top-level brief keys that are header/meta, handled explicitly — the walker
# must not turn them into FIELD rows.
META_TOP_LEVEL_KEYS: frozenset[str] = frozenset({
    "address", "lat", "lng", "prop_id", "run_date", "brief_type",
    "disclaimer", "narrative", "confidence_summary",
    "gaps", "compound_constraints", "sepp_lep_overrides",
    "data_currency_warnings", "scope_limitations",
})

# DataField paths whose LIST values get one manifest row per record.
# Rationale: these lists carry the standards/controls Stage-1 selects between;
# a "[N records]" summary hides them (live-validation finding #2).
FLATTEN_LIST_PATHS: frozenset[str] = frozenset({
    "dcp_controls.controls",
    "sepp_housing",
    "sepp_eligibility",
})

# DataField paths whose STRUCT value gets one row per scalar key (the capacity
# engine result — every number in it is individually decision-relevant).
EXPAND_STRUCT_PATHS: frozenset[str] = frozenset({
    "constraint_arithmetic",
})

# Value rendering budgets. Generous on purpose: over-truncation is what caused
# the Stage-1 selection miss, and 80 fields at these caps stays ~2-4K tokens.
MAX_SCALAR_CHARS = 160
MAX_RECORD_SUMMARY_CHARS = 200
# Flattened decision-critical rows (SEPP standards, DCP controls) get a wider
# budget: the live overlay clipped the secondary-dwelling standard mid-key
# ("max_tot…") at 200 chars — the one row a granny-flat reader most needs.
MAX_FLATTENED_RECORD_CHARS = 420
MAX_INLINE_LIST_CHARS = 600
MAX_UNFLATTENED_RECORDS = 8  # per-record summaries shown before "+N more"

# Path leaves whose numeric values are dollar amounts — rendered with $ and
# thousands separators. Deterministic formatting, not paraphrase: digits are
# preserved exactly.
CURRENCY_LEAF_TOKENS: tuple[str, ...] = (
    "land_value", "subject_value", "median_value", "mean_value", "price", "cost",
)

QUERIED_EMPTY_MARKER = "— (queried, no result)"

# Mirrors intelligence_brief.StrataType — kept import-free on purpose (see module
# docstring). test_brief_manifest.py asserts these match the source enum.
_STRATA_NOT_STRATA = "not_strata"
_STRATA_APARTMENT = "apartment"
_STRATA_DEVELOPMENT = "development"
_STRATA_AMBIGUOUS = "ambiguous"

_BRIEF_TYPE_RENOVATION = "renovation"


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------


class EntryKind(str, Enum):
    FIELD = "field"
    GAP = "gap"
    FINDING = "finding"


class ManifestEntry(BaseModel):
    """One row of the manifest. ``value_text`` is rendered, never re-parsed."""

    id: str  # F001 / G001 / X001 — stable within one manifest
    kind: EntryKind
    path: str
    value_text: str
    confidence: Optional[str] = None
    source: Optional[str] = None
    as_at: Optional[str] = None
    reason: Optional[str] = None  # gaps only

    model_config = ConfigDict(extra="forbid")


class BriefManifest(BaseModel):
    """Deterministic manifest of one brief. Build via :func:`build_manifest`."""

    address: str
    brief_type: str
    run_date: Optional[str] = None
    entries: list[ManifestEntry]
    warnings: list[str] = []  # provenance omissions, walk errors — never silent
    data_hash: str

    model_config = ConfigDict(extra="forbid")

    @property
    def entry_ids(self) -> set[str]:
        """All valid ids (F/G/X) — the Stage-1 plan-validation universe."""
        return {e.id for e in self.entries}

    def id_map(self) -> dict[str, str]:
        return {e.id: e.path for e in self.entries}

    def to_prompt_block(self) -> str:
        """Render the pipe table Stage-1 consumes. Deterministic."""
        lines = [
            f"MANIFEST for {self.address} (brief_type={self.brief_type}, "
            f"run_date={self.run_date or '—'})",
            "FIELD | path | value | confidence | source | as_at",
        ]
        for e in self.entries:
            if e.kind == EntryKind.FIELD:
                lines.append(
                    f"{e.id} | {e.path} | {e.value_text} | "
                    f"{e.confidence} | {e.source} | {e.as_at or '—'}"
                )
            elif e.kind == EntryKind.GAP:
                lines.append(
                    f"{e.id} | GAP {e.path} | reason={e.reason or 'unspecified'} | "
                    f"fallback={e.source or '—'}"
                )
            else:
                lines.append(f"{e.id} | FINDING {e.path} | {e.value_text}")
        return "\n".join(lines)

    def approx_tokens(self) -> int:
        return len(self.to_prompt_block()) // 4


# ---------------------------------------------------------------------------
# Intent × property-type compatibility (deterministic pre-check before Stage-1)
# ---------------------------------------------------------------------------


class Intent(str, Enum):
    GRANNY_FLAT = "granny_flat"
    DUPLEX = "duplex"
    RENOVATE = "renovate"
    KNOCKDOWN_REBUILD = "knockdown_rebuild"
    BUY_AND_HOLD = "buy_and_hold"
    SUBDIVIDE = "subdivide"
    RESEARCHING = "researching"


# Intents that require the reader to control the land / build new structures.
# An apartment strata lot cannot pursue these unilaterally.
PHYSICAL_BUILD_INTENTS: frozenset[Intent] = frozenset({
    Intent.GRANNY_FLAT,
    Intent.DUPLEX,
    Intent.KNOCKDOWN_REBUILD,
    Intent.SUBDIVIDE,
})


class CompatibilityStatus(str, Enum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"  # deterministic: route to scope-decline template
    REVIEW = "review"  # strata townhouse / ambiguous — surface caution, don't block
    UNKNOWN = "unknown"  # strata lookup failed — never assume buildable


class IntentCompatibility(BaseModel):
    status: CompatibilityStatus
    reason: Optional[str] = None
    strata_type: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


def check_intent_compatibility(
    brief: Union[BaseModel, dict],
    intent: Union[Intent, str],
) -> IntentCompatibility:
    """Deterministic guard run BEFORE Stage-1 selection.

    Live-validation finding 2026-07-15: given a granny-flat intent on a strata
    apartment (manifest plainly said is_strata=True), the selection model still
    composed a build-feasibility plan. Property-type applicability is not the
    LLM's call — it is decided here, in code.

    Raises ValueError for an unrecognised intent (programming error at the
    caller, not a data condition).
    """
    intent = Intent(intent)  # ValueError on unknown — validate at the gate
    dump = _as_dict(brief)

    if intent not in PHYSICAL_BUILD_INTENTS:
        return IntentCompatibility(status=CompatibilityStatus.COMPATIBLE)

    strata_df = dump.get("strata")
    strata_value: Optional[dict] = None
    strata_failed_reason: Optional[str] = None
    if _is_datafield(strata_df):
        raw_value = strata_df.get("value")
        if raw_value is not None:
            strata_value = raw_value if isinstance(raw_value, dict) else None
        elif strata_df.get("reason"):
            strata_failed_reason = str(strata_df.get("reason"))

    brief_type = str(dump.get("brief_type") or "")

    if strata_value is None:
        if brief_type == _BRIEF_TYPE_RENOVATION:
            # Renovation briefs only exist for apartment strata.
            return IntentCompatibility(
                status=CompatibilityStatus.INCOMPATIBLE,
                reason="This is an apartment strata lot (renovation brief); "
                       f"a {intent.value} project applies to the whole site, "
                       "not an individual strata lot.",
                strata_type=_STRATA_APARTMENT,
            )
        # No strata classification at all → UNKNOWN, never a silent COMPATIBLE.
        return IntentCompatibility(
            status=CompatibilityStatus.UNKNOWN,
            reason="Strata classification unavailable"
                   + (f": {strata_failed_reason}" if strata_failed_reason else "")
                   + " — property type could not be confirmed.",
        )

    raw_type = _enum_value(strata_value.get("strata_type"))
    strata_type = str(raw_type) if raw_type else ""
    is_strata = bool(strata_value.get("is_strata"))

    # strata_type outranks the is_strata flag: a contradictory record
    # (is_strata=False, strata_type="apartment") must fail toward the guard,
    # not toward COMPATIBLE.
    if strata_type == _STRATA_APARTMENT:
        return IntentCompatibility(
            status=CompatibilityStatus.INCOMPATIBLE,
            reason=f"This lot is an apartment in a strata scheme; a {intent.value} "
                   "project applies to the whole site, not an individual lot.",
            strata_type=strata_type,
        )
    if strata_type in (_STRATA_DEVELOPMENT, _STRATA_AMBIGUOUS):
        # Strata townhouse / ambiguous: physically conceivable but constrained
        # by common property and by-laws — surface caution, don't block.
        return IntentCompatibility(
            status=CompatibilityStatus.REVIEW,
            reason="Strata-titled property (non-apartment); works involving common "
                   "property require owners-corporation consent.",
            strata_type=strata_type,
        )
    if strata_type == _STRATA_NOT_STRATA or not is_strata:
        return IntentCompatibility(
            status=CompatibilityStatus.COMPATIBLE, strata_type=strata_type or None
        )
    # is_strata=True with an unrecognised strata_type string → REVIEW, not
    # COMPATIBLE: an unknown classification must not read as a green light.
    return IntentCompatibility(
        status=CompatibilityStatus.REVIEW,
        reason=f"Strata-titled property with unrecognised classification "
               f"'{strata_type}' — verify property type before proceeding.",
        strata_type=strata_type,
    )


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_manifest(brief: Union[BaseModel, dict]) -> BriefManifest:
    """Serialize a brief into a :class:`BriefManifest`.

    Never raises on malformed section content: a section that cannot be walked
    is skipped with a warning (error isolation — one bad section must not take
    down the manifest). Raises TypeError only for a wholly unusable input.
    """
    dump = _as_dict(brief)
    if not isinstance(dump, dict):
        raise TypeError(f"build_manifest expects a pydantic model or dict, got {type(brief)!r}")

    warnings: list[str] = []
    raw_fields: list[dict] = []
    raw_gaps: list[dict] = []

    for key in _ordered_keys(dump):
        if key in META_TOP_LEVEL_KEYS:
            continue
        try:
            _walk(dump[key], key, raw_fields, raw_gaps, warnings)
        except Exception as exc:  # error isolation per section
            logger.warning("Manifest walk failed for section %s: %s", key, exc)
            warnings.append(f"section '{key}' skipped: {type(exc).__name__}: {exc}")

    # De-dup by path, keep the outermost (first-seen) row.
    raw_fields = _dedup_by_path(raw_fields)
    raw_gaps = _dedup_by_path(raw_gaps)

    # Brief-level gap register (collect_gaps output) — merge, walker rows win.
    walked_gap_paths = {g["path"] for g in raw_gaps}  # noqa: bracket-access — rows built by this module, key guaranteed
    for g in dump.get("gaps") or []:
        if not isinstance(g, dict):
            continue
        field = str(g.get("field") or "").strip()
        if not field or field in walked_gap_paths:
            continue
        walked_gap_paths.add(field)
        raw_gaps.append({
            "path": field,
            "reason": _clip(str(g.get("reason") or "unspecified"), MAX_SCALAR_CHARS),
            "source": g.get("verify_url") or None,
        })

    findings = _collect_findings(dump)

    entries: list[ManifestEntry] = []
    for i, f in enumerate(raw_fields, start=1):
        entries.append(ManifestEntry(id=f"F{i:03d}", kind=EntryKind.FIELD, **f))
    for i, g in enumerate(raw_gaps, start=1):
        entries.append(ManifestEntry(
            id=f"G{i:03d}", kind=EntryKind.GAP, path=g["path"],  # noqa: bracket-access — rows built by this module
            value_text="", reason=g.get("reason"), source=g.get("source"),
        ))
    for i, x in enumerate(findings, start=1):
        entries.append(ManifestEntry(
            id=f"X{i:03d}", kind=EntryKind.FINDING,
            path=x["path"], value_text=x["value_text"],  # noqa: bracket-access — rows built by this module
        ))

    return BriefManifest(
        address=str(dump.get("address") or "unknown address"),
        brief_type=str(dump.get("brief_type") or "unknown"),
        run_date=dump.get("run_date"),
        entries=entries,
        warnings=warnings,
        data_hash=_data_hash(entries),
    )


# ---------------------------------------------------------------------------
# Walk internals
# ---------------------------------------------------------------------------


def _as_dict(brief: Union[BaseModel, dict]) -> Any:
    if isinstance(brief, BaseModel):
        return brief.model_dump()
    return brief


def _ordered_keys(dump: dict) -> list[str]:
    """Deterministic section order regardless of input dict ordering."""
    return sorted(dump.keys())


def _enum_value(v: Any) -> Any:
    """Unwrap str-Enum members to their value.

    model_dump() in default (python) mode keeps enums as members, and on
    Python 3.11+ str(StrEnumMixin.X) renders "Class.X" — which would silently
    corrupt confidence badges and defeat strata_type comparisons.
    """
    if isinstance(v, Enum):
        return v.value
    return v


def _is_datafield(node: Any) -> bool:
    """Strict DataField shape: all provenance keys present.

    DataField.model_dump() always emits value+confidence+source. Requiring all
    three prevents look-alike domain records (e.g. a control row with 'value'
    and 'reason' keys) from fabricating phantom gaps or provenance warnings.
    """
    return isinstance(node, dict) and (
        "value" in node and "confidence" in node and "source" in node
    )


def _path_excluded(path: str) -> bool:
    lowered = path.lower()
    return any(token in lowered for token in EXCLUDED_PATH_TOKENS)


def _walk(
    node: Any,
    path: str,
    fields: list[dict],
    gaps: list[dict],
    warnings: list[str],
    unit: Optional[str] = None,
) -> None:
    if _path_excluded(path):
        return

    if _is_datafield(node):
        _emit_datafield(node, path, fields, gaps, warnings, unit=unit)
        return

    if isinstance(node, dict):
        # Sibling "<field>_units" scalars decorate their field's value, the
        # same merge the brief page does — "8.5" must read "8.5 m".
        unit_for: dict[str, str] = {
            k[:-6]: v for k, v in node.items()
            if k.endswith("_units") and isinstance(v, str) and v
        }
        for key, child in node.items():
            if _path_excluded(key) or key.endswith("_units"):
                continue
            if isinstance(child, (dict, list)):
                _walk(child, f"{path}.{key}", fields, gaps, warnings,
                      unit=unit_for.get(key))
        return

    if isinstance(node, list):
        for i, child in enumerate(node):
            if isinstance(child, (dict, list)):
                _walk(child, f"{path}[{i}]", fields, gaps, warnings)


def _fmt_leaf_value(path: str, value: Any) -> Optional[str]:
    """Path-aware deterministic formatting: currency and unit suffixes.

    Returns None when no special formatting applies (caller falls back to the
    generic renderer). Digits are never altered — only presentation.
    """
    leaf = path.rsplit(".", 1)[-1].lower()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if any(tok in leaf for tok in CURRENCY_LEAF_TOKENS) and abs(value) >= 100:
            return f"${value:,.0f}"
    return None


# Field names that carry their unit as a name suffix (max_gfa_m2) get the unit
# in the rendered value — otherwise "345.2" ships unitless (observed live).
# Longest suffix first so "_m" never shadows "_m2"/"_km".
_UNIT_LEAF_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("_m2", "m²"),
    ("_sqm", "m²"),
    ("_km", "km"),
    ("_ha", "ha"),
    ("_m", "m"),
)


def _unit_from_leaf(path: str) -> Optional[str]:
    leaf = path.rsplit(".", 1)[-1].lower()
    for suffix, unit in _UNIT_LEAF_SUFFIXES:
        if leaf.endswith(suffix):
            return unit
    return None


def _emit_datafield(
    node: dict,
    path: str,
    fields: list[dict],
    gaps: list[dict],
    warnings: list[str],
    unit: Optional[str] = None,
) -> None:
    value = node.get("value")
    reason = node.get("reason")
    confidence = _enum_value(node.get("confidence"))
    source = _enum_value(node.get("source"))
    as_at = _enum_value(node.get("as_at"))

    # Fail-closed provenance: no source or no confidence → omit, never serve bare.
    if not confidence or not source:
        warnings.append(f"omitted '{path}': missing provenance "
                        f"(confidence={confidence!r}, source={source!r})")
        logger.warning("Manifest omitted %s: missing provenance", path)
        return

    confidence = str(confidence)
    source = str(source)
    as_at = str(as_at) if as_at else None

    # Three-state mapping (DataField contract).
    if value is None:
        if reason:
            gaps.append({
                "path": path,
                "reason": _clip(str(reason), MAX_SCALAR_CHARS),
                "source": source,
            })
        else:
            fields.append({
                "path": path, "value_text": QUERIED_EMPTY_MARKER,
                "confidence": confidence, "source": source, "as_at": as_at,
            })
        return

    provenance = {"confidence": confidence, "source": source, "as_at": as_at}

    if path in EXPAND_STRUCT_PATHS and isinstance(value, dict):
        emitted = False
        for key in sorted(value.keys()):
            v = value[key]
            if v is None or isinstance(v, (dict, list)):
                continue
            fields.append({
                "path": f"{path}.{key}", "value_text": _render_scalar(v), **provenance,
            })
            emitted = True
        if not emitted:  # struct held nothing scalar — keep a summary row
            fields.append({
                "path": path, "value_text": _summarise_record(value), **provenance,
            })
        return

    if path in FLATTEN_LIST_PATHS and isinstance(value, list):
        if not value:
            fields.append({
                "path": path, "value_text": "[] (queried, empty list)", **provenance,
            })
            return
        for i, record in enumerate(value):
            fields.append({
                "path": f"{path}[{i}]",
                "value_text": _summarise_record(record, limit=MAX_FLATTENED_RECORD_CHARS)
                if isinstance(record, dict) else _render_scalar(record),
                **provenance,
            })
        return

    formatted = _fmt_leaf_value(path, value)
    if formatted is None:
        formatted = _render_value(value)
        if (unit is None and isinstance(value, (int, float))
                and not isinstance(value, bool)):
            unit = _unit_from_leaf(path)
        if unit and not isinstance(value, (dict, list)) and value is not None:
            formatted = f"{formatted} {unit}"
    fields.append({
        "path": path, "value_text": formatted, **provenance,
    })

    # Structured values may hold nested DataFields (e.g. detail objects) —
    # surface them as their own rows; path de-dup keeps the outermost first.
    if isinstance(value, (dict, list)):
        _walk(value, path, fields, gaps, warnings)


def _collect_findings(dump: dict) -> list[dict]:
    findings: list[dict] = []
    for cc in dump.get("compound_constraints") or []:
        if not isinstance(cc, dict):
            continue
        severity = _enum_value(cc.get("severity")) or "unspecified"
        findings.append({
            "path": str(cc.get("id") or "compound_constraint"),
            "value_text": f"severity={severity}; "
                          + _clip(str(cc.get("description") or ""), MAX_RECORD_SUMMARY_CHARS),
        })
    for ov in dump.get("sepp_lep_overrides") or []:
        if not isinstance(ov, dict):
            continue
        findings.append({
            "path": "sepp_lep_override",
            "value_text": "severity=info; " + _summarise_record(ov),
        })
    return findings


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _clip(text: str, limit: int) -> str:
    # Collapse newlines (one manifest row per line) and strip pipes (the table
    # column delimiter — a '|' inside data would shift columns and let data
    # masquerade as confidence/source).
    text = " ".join(text.replace("|", "/").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _render_scalar(value: Any) -> str:
    value = _enum_value(value)
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (int, float)):
        return str(value)
    return _clip(str(value), MAX_SCALAR_CHARS)


def _summarise_record(record: Any, limit: int = MAX_RECORD_SUMMARY_CHARS) -> str:
    """Compact one record into 'k=v; …' over its scalar entries."""
    if not isinstance(record, dict):
        return _render_scalar(record)
    parts = [
        f"{k}={_fmt_leaf_value(k, v) or _render_scalar(v)}"
        for k, v in record.items()
        if v is not None and not isinstance(v, (dict, list)) and not _path_excluded(k)
    ]
    if not parts:
        return "{no scalar detail}"
    return _clip("; ".join(parts), limit)


def _render_value(value: Any) -> str:
    if isinstance(value, list):
        if not value:
            return "[] (queried, empty list)"
        if all(not isinstance(v, (dict, list)) for v in value):
            joined = ", ".join(_render_scalar(v) for v in value)
            return _clip(f"[{len(value)}] {joined}", MAX_INLINE_LIST_CHARS)
        shown = [
            _summarise_record(v) for v in value[:MAX_UNFLATTENED_RECORDS]
        ]
        suffix = (
            f" … +{len(value) - MAX_UNFLATTENED_RECORDS} more"
            if len(value) > MAX_UNFLATTENED_RECORDS else ""
        )
        return _clip(
            f"[{len(value)} records] " + " || ".join(shown) + suffix,
            MAX_INLINE_LIST_CHARS,
        )
    if isinstance(value, dict):
        return _summarise_record(value)
    return _render_scalar(value)


# ---------------------------------------------------------------------------
# Hashing / de-dup
# ---------------------------------------------------------------------------


def _dedup_by_path(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        if row["path"] in seen:
            continue
        seen.add(row["path"])
        out.append(row)
    return out


def _data_hash(entries: list[ManifestEntry]) -> str:
    """SHA-256 over content rows, EXCLUDING as_at.

    as_at is stamped with the fetch date on every brief run, so including it
    would change the hash daily with identical data. Excluding it makes the
    hash a true did-the-data-change key (cache key now, C2 delta input later).
    """
    canonical = "\n".join(
        f"{e.kind.value}|{e.path}|{e.value_text}|{e.confidence}|{e.source}|{e.reason}"
        for e in entries
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
