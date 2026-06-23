# prior-art-checked: reuse not viable because no module performs data-integrity
# checks (fabricated-value / conflicting-value detection) over extracted tables.
# The flagged files (formatter.ts, full_clause_extractor.py, granny_flat.py, UI
# panels) format or extract content; none validate that a stored value is real.
# This generalises the setback-only logic in scripts/validate_dcp_setbacks.py.
"""Generic integrity checks for any table of values EXTRACTED from source text.

The setback work (scripts/validate_dcp_setbacks.py) showed a bug class that is
NOT setback-specific: a value gets stored that was never really in the source —
either invented to fill a gap ("assumed standard NSW...") or scraped from the
wrong clause, or two contradictory values are stored for the same thing with
nothing to choose between them. The same risk exists in every table populated by
extraction (DCP controls, LEP land-use permissibility, SEPP standards, ...).

This module is the reusable engine. It is domain-agnostic — callers pass a small
config (which column holds the value, which form the key, which note disambiguates)
so the SAME checks run against any such table. Deterministic, no LLM (the project's
"deterministic processing only — no AI interpretation of regulations" rule).

Two checks + one gate:
  * ``fabricated_values``  — a value is stored while a marker field admits it is
    assumed/guessed. (Catches HONEST fabrication that self-labels.)
  * ``conflicting_values`` — one key holds >1 distinct value with no condition to
    disambiguate. (Catches contradictory extractions.)
  * ``assert_clean_row``   — WRITE-TIME gate: raises before an INSERT so a
    fabricated value is blocked at entry, not merely detected later.

Limitation (be honest): ``fabricated_values`` relies on the writer self-labelling
("assumed"). A SILENT guess with no marker is not caught here — that needs the
source-vs-value semantic check (a per-domain config, see validate_dcp_setbacks).
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable, Optional

# Words a writer uses when it knows it is guessing / filling a gap.
DEFAULT_FABRICATION_MARKER = re.compile(
    r"\bassumed\b|standard.{0,3}pattern.{0,3}assumed|assumed standard|standard nsw pattern|"
    r"\bplaceholder\b|\bguess(?:ed)?\b|default value|to be verified|\btbd\b|made up",
    re.I,
)


def _present(v) -> bool:
    return v is not None and str(v).strip() != ""


def _hashable(v):
    """Coerce a key component to something hashable — array/json columns (e.g.
    Postgres text[] like applicable_zones) arrive as lists and can't key a dict."""
    if isinstance(v, (list, set)):
        return tuple(_hashable(x) for x in v)
    if isinstance(v, dict):
        return repr(sorted(v.items()))
    return v


def fabricated_values(
    rows: Iterable[dict],
    *,
    value_field: str,
    marker_fields: list[str],
    marker_pattern: re.Pattern = DEFAULT_FABRICATION_MARKER,
) -> list[dict]:
    """Rows that store a value while a marker field admits it is assumed/guessed.

    ``marker_fields`` are the columns where a writer would confess (condition,
    review_reason, notes, source_text). A row is flagged only when it BOTH carries
    a value and matches the marker — an unverified row that correctly stores no
    value (the fixed state) is clean.
    """
    out: list[dict] = []
    for r in rows:
        if not _present(r.get(value_field)):
            continue
        blob = " ".join(str(r.get(f) or "") for f in marker_fields)
        if marker_pattern.search(blob):
            out.append(r)
    return out


def conflicting_values(
    rows: Iterable[dict],
    *,
    key_fields: list[str],
    value_field: str,
    condition_field: Optional[str] = None,
) -> list[dict]:
    """Groups sharing ``key_fields`` that hold >1 distinct ``value_field`` with no
    ``condition_field`` text on any row to disambiguate them.

    Values are compared case-insensitively as trimmed strings so "Permitted" and
    "permitted" are one value, but "Permitted" vs "Prohibited" is a real conflict.
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        if not _present(r.get(value_field)):
            continue
        key = tuple(_hashable(r.get(k)) for k in key_fields)
        groups[key].append(r)

    out: list[dict] = []
    for key, grp in groups.items():
        values = sorted({str(r.get(value_field)).strip().lower() for r in grp})
        if len(values) < 2:
            continue
        if condition_field and any((r.get(condition_field) or "").strip() for r in grp):
            continue
        out.append({
            "key": dict(zip(key_fields, key)),
            "values": values,
            "n_rows": len(grp),
        })
    return out


def assert_clean_row(
    row: dict,
    *,
    value_field: str,
    marker_fields: list[str],
    marker_pattern: re.Pattern = DEFAULT_FABRICATION_MARKER,
) -> None:
    """WRITE-TIME gate. Raise ``ValueError`` if ``row`` would store a fabricated
    value. Call this in every insert path BEFORE writing, so a guessed value can
    never enter the table — instead of being caught by a later sweep.

    Honest unverified rows pass by storing no value (``value_field`` empty) and a
    marker explaining why; this gate rejects only value-present-AND-marked rows.
    """
    if fabricated_values([row], value_field=value_field, marker_fields=marker_fields,
                         marker_pattern=marker_pattern):
        raise ValueError(
            f"Refusing to store a fabricated {value_field}={row.get(value_field)!r}: "
            f"a marker field {marker_fields} admits it is assumed/guessed. Store the "
            f"value as NULL (rule exists, value unknown) rather than a guess."
        )
