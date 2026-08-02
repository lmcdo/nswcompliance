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


def value_absent_from_source(
    rows: Iterable[dict],
    *,
    value_field: str,
    source_field: str,
) -> list[dict]:
    """Advisory catcher for SILENT guesses: a numeric value whose digits do not
    appear anywhere in its own ``source_field`` text was probably not extracted
    from it.

    ADVISORY only — it has real false positives (e.g. a 9 m2 POS expressed in the
    source as "3m x 3m", or unit conversions like 900mm vs 0.9), so it routes a
    row to human review rather than hard-blocking it. Skips non-numeric values and
    rows with empty source text.
    """
    out: list[dict] = []
    for r in rows:
        raw = r.get(value_field)
        src = r.get(source_field)
        if raw is None or not str(src or "").strip():
            continue
        try:
            num = float(raw)
        except (TypeError, ValueError):
            continue
        # Render the number both as written and as an int when whole (24.0 -> "24").
        forms = {str(raw).strip(), str(num)}
        if num.is_integer():
            forms.add(str(int(num)))
        if not any(f and f in str(src) for f in forms):
            out.append(r)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Named derivation rules — WHY a stored number differs from its own source text
#
# ``value_absent_from_source`` says a number's digits are not in its quote. That
# is a flag, not an answer: most flags are legitimate derivations ("900mm" stored
# as 0.9; "one space per 3 dwellings" stored as 0.333). A flag nobody can resolve
# gets ignored, which is how a real mismatch survives in a list of 142.
#
# So each rule below NAMES a transformation and returns the evidence it matched.
# A row is "explained" only when a named rule can point at the substring it used.
# Anything left over is the finding — and because every rule must produce evidence,
# an explanation cannot be a shrug.
#
# Direction of risk: a FALSE explanation hides a real mismatch, so every rule is
# written to under-claim. Percentages must sit against a literal '%'; unit
# conversions must sit against a literal unit token; ratios must sit against an
# explicit "per"/"for every". No rule fires on a bare number found anywhere in the
# text.
# ─────────────────────────────────────────────────────────────────────────────

# Stored values are rounded (1/3 is stored as 0.333), so derived rules need a
# rounding tolerance. Exact matching does not and must not use one — 0.9 and 0.899
# are different numbers, and letting them match would silently accept a typo.
_EXACT_TOL = 1e-9
_DERIVED_ABS_TOL = 0.005
_DERIVED_REL_TOL = 0.005

_WORD_NUMBERS = {
    "nil": 0.0, "zero": 0.0, "none": 0.0, "half": 0.5,
    "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0, "six": 6.0,
    "seven": 7.0, "eight": 8.0, "nine": 9.0, "ten": 10.0, "eleven": 11.0,
    "twelve": 12.0, "fifteen": 15.0, "twenty": 20.0,
}
_WORD_NUMBER_ALT = "|".join(sorted(_WORD_NUMBERS, key=len, reverse=True))

# A standalone number, NOT one embedded in a clause reference. The lookarounds
# are load-bearing: without them 's4.3.6' yields 4.3 and 'DS9.2' yields 9.2, and a
# stored 4.3 would then be "explained" by its own section number — a false pass
# manufactured out of a citation.
# The trailing lookahead is `(?!\.\d)`, NOT `(?![.\d])`: the latter also rejected
# a number ending a sentence ("Maximum: up to 3.") and silently un-explained rows
# that were fine.
_NUMBER_TOKEN = r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?(?!\.?\d)"
_NUMBER_RE = re.compile(_NUMBER_TOKEN)

# A number that is explicitly a percentage. Requiring the literal '%' (or the
# words) is what stops "3500" from explaining a stored 35 via a /100 that nobody
# wrote.
_PERCENT_RE = re.compile(rf"({_NUMBER_TOKEN})\s*(?:%|per\s?cent)", re.I)

# A number carrying an explicit length unit. Same principle: no bare number is
# ever treated as millimetres.
_LENGTH_RE = re.compile(
    rf"({_NUMBER_TOKEN})\s*(mm|millimetres?|millimeters?|cm|centimetres?|"
    rf"centimeters?|m|metres?|meters?)\b", re.I)
_TO_METRES = {"mm": 0.001, "millimetre": 0.001, "millimetres": 0.001,
              "millimeter": 0.001, "millimeters": 0.001,
              "cm": 0.01, "centimetre": 0.01, "centimetres": 0.01,
              "centimeter": 0.01, "centimeters": 0.01,
              "m": 1.0, "metre": 1.0, "metres": 1.0, "meter": 1.0, "meters": 1.0}

# "per", "for every", "per every" — councils write the same rate every way.
_RATE_WORDS = r"(?:per\s+every|per|for\s+every|for\s+each|to\s+every|in\s+every)"

# The DENOMINATOR half of a rate: "per 4 dwellings", "for every three (3) units".
# Numerators are found by looking backwards from here rather than by one big
# regex — a single pattern matched leftmost-first and its non-overlapping runs
# swallowed the real rate. On 'DS9.2 ... 1 space for every 4 dwellings' it locked
# onto 9.2 as the numerator and the row lost an explanation it genuinely had.
_RATE_TAIL_RE = re.compile(
    rf"{_RATE_WORDS}\s+(?P<b>{_NUMBER_TOKEN}|{_WORD_NUMBER_ALT})\b", re.I)

# How far back a numerator may sit from its "per". Long enough for "One (1)
# external additional visitor car parking space shall be provided for every ...".
_RATE_LOOKBACK_CHARS = 80

# A number or written numeral, for scanning the lead-in text of a rate.
_ANY_NUMBER_RE = re.compile(rf"{_NUMBER_TOKEN}|\b(?:{_WORD_NUMBER_ALT})\b", re.I)

# "min 1/3", "1/11" — a fraction written as a fraction.
_FRACTION_RE = re.compile(rf"({_NUMBER_TOKEN})\s*/\s*({_NUMBER_TOKEN})\b")

# "no additional parking is required" -> 0. Deliberately requires the word
# "required": City of Sydney's "where no front setback is shown on the map" says
# the map is silent, NOT that the setback is zero, and matching that would invent
# a control out of a sentence about cartography.
_NIL_REQUIRED_RE = re.compile(
    r"\b(?:no|nil|zero)\s+(?:\w+\s+){0,3}?"
    r"(?:parking|space|spaces|setback|setbacks|requirement)\b"
    r"(?:\s+\w+){0,3}?\s+(?:is\s+|are\s+)?requir(?:ed|ement)\b", re.I)

# "the building may be built to the rear boundary" -> a setback of 0.
_BUILT_TO_BOUNDARY_RE = re.compile(
    r"built\s+to\s+(?:the\s+)?(?:rear|side|front|street|primary|secondary)?\s*"
    r"boundar(?:y|ies)", re.I)

# "3m x 3m" -> 9 m2. Areas are routinely quoted as dimensions.
_DIMENSIONS_RE = re.compile(
    rf"({_NUMBER_TOKEN})\s*m?\s*[x×*]\s*({_NUMBER_TOKEN})\s*m?", re.I)

_WORD_NUMBER_RE = re.compile(rf"\b({_WORD_NUMBER_ALT})\b", re.I)


# A numbered-list marker: "2. Front fences and walls are not to impede..." at the
# start of a line or a table cell. These are ordinals, not quantities, and they
# are the single largest false-explanation channel in the whole check — a 400-char
# quote listing points 1., 2., 3. will "contain" almost any small stored value.
# Found on Camden control 693: a front_setback of 2.0 m was explained by the '2'
# of a list item in a clause about front FENCE height.
_LIST_ORDINAL_RE = re.compile(r"(?:^|\n|\|)\s*(\d+)\.\s+(?=[A-Za-z])")


def _quantity_spans(source: str) -> list[tuple[float, int, int]]:
    """(value, start, end) for every number that is a QUANTITY, not an ordinal."""
    ordinals = {m.start(1) for m in _LIST_ORDINAL_RE.finditer(source)}
    out: list[tuple[float, int, int]] = []
    for match in _NUMBER_RE.finditer(source):
        if match.start() in ordinals:
            continue
        parsed = _as_float(match.group(0))
        if parsed is not None:
            out.append((parsed, match.start(), match.end()))
    return out


def _as_float(token: str) -> Optional[float]:
    """A numeric or written-numeral token as a float, or None if it is neither."""
    token = token.strip().lower()
    if token in _WORD_NUMBERS:
        return _WORD_NUMBERS[token]
    try:
        return float(token.replace(",", ""))
    except ValueError:
        return None


def _close(a: float, b: float) -> bool:
    """Equal within the rounding a person applies when storing a derived value."""
    return abs(a - b) <= max(_DERIVED_ABS_TOL, _DERIVED_REL_TOL * abs(b))


def _rule_exact_digit_match(value: float, source: str, unit) -> Optional[str]:
    """The number appears literally in the text.

    Compares numeric TOKENS, not substrings: a substring test would let a stored
    5 be 'found' inside '15', which is the loosest possible way to declare a row
    clean and would hide exactly the mismatches this exists to surface. Numbered-
    list ordinals are excluded for the same reason.
    """
    for parsed, start, end in _quantity_spans(source):
        if abs(parsed - value) <= _EXACT_TOL:
            return f"{source[start:end]!r} appears in the source text"
    return None


def _rule_percentage_phrasing(value: float, source: str, unit) -> Optional[str]:
    """A percentage written as '35%' stored as 35 or as 0.35 (or the reverse)."""
    for token in _PERCENT_RE.findall(source):
        pct = _as_float(token)
        if pct is None:
            continue
        if _close(value, pct / 100.0):
            return f"'{token}%' stored as a fraction"
        if _close(value, pct * 100.0):
            return f"'{token}%' stored scaled by 100"
    return None


def _rule_unit_conversion(value: float, source: str, unit) -> Optional[str]:
    """A length quoted in mm or cm and stored in metres (or the reverse).

    Only fires when the stored unit is metres or unrecorded — converting a value
    whose column says 'spaces/dwelling' would be nonsense.
    """
    if unit not in (None, "", "m", "m2"):
        return None
    for token, raw_unit in _LENGTH_RE.findall(source):
        parsed = _as_float(token)
        factor = _TO_METRES.get(raw_unit.lower())
        if parsed is None or factor is None or factor == 1.0:
            continue
        if _close(value, parsed * factor):
            return f"'{token}{raw_unit}' converted to {parsed * factor:g} m"
        if _close(value, parsed / factor):
            return f"'{token}{raw_unit}' converted from {parsed / factor:g}"
    return None


def _rate_candidates(source: str):
    """Yield (numerator, denominator, evidence) for every 'A per B' in the text.

    Every number in the lead-in is offered as a numerator, nearest first, because
    a council writes the same rate as '1 space per 4 dwellings' and as 'One (1)
    external additional visitor car parking space ... for every three (3) units'.
    A denominator with NO numerator before it yields ``None`` as the numerator, so
    the implied-unity rule can decide separately whether to trust it.
    """
    for match in _RATE_TAIL_RE.finditer(source):
        b = _as_float(match.group("b"))
        if b in (None, 0):
            continue
        start = max(0, match.start() - _RATE_LOOKBACK_CHARS)
        lead = source[start:match.start()]
        # A sentence or table-cell break ends the lead: a number on the other side
        # of it belongs to a different control.
        for separator in (".", ";", "|", "\n"):
            cut = lead.rfind(separator)
            if cut != -1:
                lead = lead[cut + 1:]
        numerators = _ANY_NUMBER_RE.findall(lead)
        if not numerators:
            yield None, b, match.group(0).strip(), lead
            continue
        for token in reversed(numerators):
            a = _as_float(token)
            if a is not None:
                yield a, b, f"{token} ... {match.group(0).strip()}", lead


def _rule_ratio_or_rate(value: float, source: str, unit) -> Optional[str]:
    """A rate written as 'A per B' stored as the quotient A/B."""
    for a, b, evidence, _lead in _rate_candidates(source):
        if a is None:
            continue
        if _close(value, a / b):
            return f"{evidence!r} -> {a / b:.4g}"
    return None


def _rule_implied_single_unit_rate(value: float, source: str, unit) -> Optional[str]:
    """'a space for every N dwellings' — an unwritten numerator of one.

    Fires ONLY where no numerator was written. If the text says '2 spaces per 5
    dwellings' and the row stores 0.2, assuming a numerator of 1 would explain a
    value the text contradicts — the exact false pass this check exists to catch.
    """
    for a, b, evidence, _lead in _rate_candidates(source):
        if a is not None:
            continue
        if _close(value, 1.0 / b):
            return f"{evidence!r} with an implied numerator of 1"
    return None


def _rule_fraction_literal(value: float, source: str, unit) -> Optional[str]:
    """A fraction written as a fraction: 'min 1/3' stored as 0.333."""
    for numerator, denominator in _FRACTION_RE.findall(source):
        a, b = _as_float(numerator), _as_float(denominator)
        if a is None or b in (None, 0):
            continue
        if _close(value, a / b):
            return f"'{numerator}/{denominator}' -> {a / b:.4g}"
    return None


def _rule_explicit_nil_requirement(value: float, source: str, unit) -> Optional[str]:
    """'no additional parking is required' stored as 0."""
    if abs(value) > _EXACT_TOL:
        return None
    match = _NIL_REQUIRED_RE.search(source)
    return f"explicit nil requirement: {match.group(0).strip()!r}" if match else None


def _rule_built_to_boundary(value: float, source: str, unit) -> Optional[str]:
    """'may be built to the rear boundary' stored as a setback of 0."""
    if abs(value) > _EXACT_TOL or unit not in (None, "", "m"):
        return None
    match = _BUILT_TO_BOUNDARY_RE.search(source)
    return f"built to the boundary: {match.group(0).strip()!r}" if match else None


def _rule_area_from_dimensions(value: float, source: str, unit) -> Optional[str]:
    """An area quoted as dimensions ('3m x 3m') stored as the product."""
    for first, second in _DIMENSIONS_RE.findall(source):
        a, b = _as_float(first), _as_float(second)
        if a is None or b is None:
            continue
        if _close(value, a * b):
            return f"'{first} x {second}' -> {a * b:g}"
    return None


def _rule_written_numeral(value: float, source: str, unit) -> Optional[str]:
    """The number is spelled out ('three hours', 'nil parking').

    Last in the order on purpose. Common words like 'one' appear in text that has
    nothing to do with the value, so this rule is the most likely to explain a row
    for the wrong reason — anything it catches should be read with that in mind.
    """
    for token in _WORD_NUMBER_RE.findall(source):
        parsed = _WORD_NUMBERS[token.lower()]
        if abs(parsed - value) <= _EXACT_TOL:
            return f"written numeral {token.lower()!r}"
    return None


# Ordered most-direct to most-derived. The order is the semantics: a row's state
# is the LAST rule any of its values needed, so a row explained only by the
# weakest rule is not reported as an exact match.
DERIVATION_RULES = (
    ("exact_digit_match", _rule_exact_digit_match),
    ("percentage_phrasing", _rule_percentage_phrasing),
    ("unit_conversion", _rule_unit_conversion),
    ("fraction_literal", _rule_fraction_literal),
    ("ratio_or_rate", _rule_ratio_or_rate),
    ("implied_single_unit_rate", _rule_implied_single_unit_rate),
    ("area_from_dimensions", _rule_area_from_dimensions),
    ("written_numeral", _rule_written_numeral),
    ("explicit_nil_requirement", _rule_explicit_nil_requirement),
    ("built_to_boundary_zero", _rule_built_to_boundary),
)
RULE_NAMES = tuple(name for name, _ in DERIVATION_RULES)
UNEXPLAINED = "UNEXPLAINED"
NO_VALUE_STORED = "no_value_stored"


def explain_value(value, source_text, unit=None) -> tuple[str, Optional[str]]:
    """Name the rule that derives ``value`` from ``source_text``, with evidence.

    Returns ``(rule_name, evidence)``; ``(UNEXPLAINED, None)`` when no rule fires.
    A non-numeric or absent value returns ``(NO_VALUE_STORED, None)`` — there is
    nothing to check, which is deliberately NOT the same as passing.
    """
    if value is None or not str(source_text or "").strip():
        return NO_VALUE_STORED, None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return NO_VALUE_STORED, None
    source = str(source_text)
    for name, rule in DERIVATION_RULES:
        evidence = rule(number, source, unit)
        if evidence:
            return name, evidence
    return UNEXPLAINED, None


def explain_row(row: dict, *, value_fields: list[str], source_field: str,
                unit_field: Optional[str] = None) -> dict:
    """Put ONE row in exactly one state across all of its stored values.

    A row with both a min and a max must have BOTH explained; one unexplained end
    makes the row unexplained, because a range whose upper bound came from nowhere
    is not a verified range. When every value is explained, the row's state is the
    most-derived rule any of them needed — so a row that needed the weakest rule
    cannot present as an exact match.
    """
    unit = row.get(unit_field) if unit_field else None
    per_field: dict[str, dict] = {}
    for field in value_fields:
        name, evidence = explain_value(row.get(field), row.get(source_field), unit)
        per_field[field] = {"rule": name, "evidence": evidence}

    checked = {f: r for f, r in per_field.items() if r["rule"] != NO_VALUE_STORED}
    if not checked:
        state = NO_VALUE_STORED
    elif any(r["rule"] == UNEXPLAINED for r in checked.values()):
        state = UNEXPLAINED
    else:
        state = max((r["rule"] for r in checked.values()), key=RULE_NAMES.index)
    return {"state": state, "fields": per_field}


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
