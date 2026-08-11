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
# A flat absolute tolerance is wrong in both directions here. Too loose and it
# dominates small values — a stored 0.005 against a quoted "1 space per 1000
# dwellings" (0.001) sat inside a flat 0.005, so a rate five times too large
# passed as derived. Too tight and it rejects honest rounding — the table stores
# 2/3 as 0.67 and 1/3 as both 0.33 and 0.333, so the precision is not uniform.
#
# So the tolerance comes from the STORED value's own precision (half of its last
# decimal place) AND is capped by a relative bound, so a whole number cannot
# absorb a large absolute gap. Both must hold.
_DERIVED_REL_TOL = 0.05

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

# What ends the lead-in to a rate. A full stop counts only when it is NOT between
# two digits, so "0.5 spaces per 4 dwellings" keeps its 0.5 instead of being cut
# down to "5 spaces".
_LEAD_BREAK_RE = re.compile(r"(?<!\d)\.(?!\d)|[;|\n]")

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

# A written numeral that is actually COUNTING something. "one" is a common English
# word: without this, "Objective one: provide a minimum 6m front setback" explains
# a stored 1 m setback. The numeral must be followed, within two words, by a noun
# the control could be measured in.
_COUNTED_NOUN = (r"spaces?|cars?|garages?|parking|bays?|metres?|meters?|m|m2|"
                 r"hours?|storeys?|storys?|stories|dwellings?|units?|bedrooms?|"
                 r"beds?|trees?|zones?|lots?|rooms?|percent")
_COUNTED_NUMERAL_RE = re.compile(
    rf"\b(?P<word>{_WORD_NUMBER_ALT})\b(?:\s+[a-z-]+){{0,2}}?\s+"
    rf"(?P<noun>{_COUNTED_NOUN})\b", re.I)

# The unwritten "one" in "AN additional car parking SPACE for every 4 dwellings".
# Without it there is no numerator at all, written or implied — "Visitor parking
# must be considered for every 4 dwellings" states no quantity, and deriving 1/4
# from it invents the numerator outright.
_SINGULAR_ARTICLE_RE = re.compile(
    rf"\b(?:a|an)\b(?:\s+[a-z-]+){{0,4}}?\s+(?:{_COUNTED_NOUN})\b", re.I)


# A numbered-list marker: "2. Front fences and walls are not to impede..." at the
# start of a line or a table cell. These are ordinals, not quantities, and they
# are the single largest false-explanation channel in the whole check — a 400-char
# quote listing points 1., 2., 3. will "contain" almost any small stored value.
# Found on Camden control 693: a front_setback of 2.0 m was explained by the '2'
# of a list item in a clause about front FENCE height.
_LIST_ORDINAL_RE = re.compile(r"(?:^|\n|\|)\s*(\d+)\.\s+(?=[A-Za-z])")

# A SECTION HEADING at the start of a line: "2.1 Objectives", "4.1A.3 Building
# Setbacks". The list-ordinal pattern needs a trailing dot and so missed these,
# and a heading number is no more a quantity than a clause reference is — a 2.1 m
# control whose quote opens "2.1 Objectives" was reading as an exact match on its
# own heading. The following word must be Capitalised, which is what distinguishes
# a heading from a measurement ("6 metres minimum" is untouched).
_SECTION_HEADING_RE = re.compile(
    r"(?:^|\n|\|)\s*(\d+(?:\.\d+)+[A-Za-z]?(?:\.\d+)*)\.?\s+(?=[A-Z])")

# A number that is a CITATION, not a quantity: "Clause 4.3:", "Part 6", "Table 2",
# "Control 12", "Figure 5A", "Objective 3". The lookbehind on the number token
# only catches a label glued to it ('s4.3.6', 'DS9.2'); a labelled number with a
# space survived, so a stored 4.3 was explained by 'Clause 4.3: minimum setback
# is 6m' — a citation explaining the value it is supposed to be evidence against.
_CLAUSE_LABEL_RE = re.compile(
    r"\b(?:clause|clauses|section|sections|part|parts|table|tables|figure|"
    r"figures|control|controls|objective|objectives|item|items|chapter|schedule|"
    r"appendix|diagram|note|paragraph|subclause)\s+(\d+(?:\.\d+)*)", re.I)


def _quantity_spans(source: str) -> list[tuple[float, int, int]]:
    """(value, start, end) for every number that is a QUANTITY.

    Excludes numbered-list ordinals and clause citations. Both are numbers that
    identify a piece of text rather than measure anything, and both were observed
    explaining stored values they had nothing to do with.
    """
    skip = {m.start(1) for m in _LIST_ORDINAL_RE.finditer(source)}
    skip |= {m.start(1) for m in _CLAUSE_LABEL_RE.finditer(source)}
    out: list[tuple[float, int, int]] = []
    for match in _NUMBER_RE.finditer(source):
        if match.start() in skip:
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


def _decimal_places(value) -> int:
    """How precisely the value was stored. repr() gives the shortest round-trip
    form, so 0.67 reports 2 and 0.333 reports 3 — the precision a writer chose.

    A None or unparseable value returns 9, the tightest bucket, so an unknown
    precision can never widen the tolerance. Callers reach this with a float
    today; failing closed costs nothing and stops that becoming an assumption.
    """
    if value is None:
        return 9
    try:
        text = repr(float(value))
    except (TypeError, ValueError):
        return 9
    if "e" in text or "E" in text:
        return 9
    return len(text.split(".")[1].rstrip("0")) if "." in text else 0


def _close(stored: float, derived: float) -> bool:
    """Equal within the rounding a person applies when storing a derived value.

    Both bounds must hold. The absolute bound is half of the stored value's last
    decimal place, so 0.67 accepts 2/3 while 0.005 rejects 0.001. The relative
    bound stops a large value absorbing a large absolute gap.

    A stored WHOLE number must match exactly. Half of its last decimal place is
    0.5, which let "24 spaces per 25 dwellings" (0.96) explain a stored 1 —
    rounding a rate to a whole number is a judgement someone made, not a
    derivation the text states. All five whole-number derived rows in the table
    are exact products ("3m x 3m" -> 9), so this costs nothing and closes the gap.
    """
    gap = abs(stored - derived)
    places = _decimal_places(stored)
    if places == 0:
        return gap <= _EXACT_TOL
    absolute = 0.5 * (10.0 ** -places)
    return gap <= absolute and gap <= max(_EXACT_TOL, _DERIVED_REL_TOL * abs(derived))


# What a number is measured in, when the text says so right after it. A quantity
# carrying an explicit unit cannot explain a value stored in an incompatible one:
# "a minimum of 3 hours of sunlight" must not explain a 3 metre setback.
_TRAILING_UNIT_RE = re.compile(
    r"\s*(mm|cm|m2|m²|sqm|square\s+metres?|metres?|meters?|m|%|per\s?cent|hours?|storeys?|"
    r"stories|spaces?|dwellings?|units?|beds?|bedrooms?|trees?|days?|years?)"
    r"(?![a-z0-9])", re.I)

# Units that measure the same KIND of thing. A quantity whose trailing unit is in
# a different family from the row's unit cannot explain it.
_UNIT_FAMILY = {
    "mm": "length", "cm": "length", "m": "length", "metre": "length",
    "metres": "length", "meter": "length", "meters": "length",
    # 'm²' must be listed BOTH here and in the trailing-unit alternation ahead of
    # bare 'm', or "3m²" matches only the 'm' and a landscaped AREA reads as a
    # length — the row's own square-metre marker disappearing into a substring.
    "m2": "area", "m²": "area", "sqm": "area",
    "square metre": "area", "square metres": "area",
    "%": "ratio", "per cent": "ratio", "percent": "ratio",
    "hour": "time", "hours": "time", "day": "time", "days": "time",
    "year": "time", "years": "time",
    "storey": "count", "storeys": "count", "stories": "count",
    "space": "count", "spaces": "count", "dwelling": "count",
    "dwellings": "count", "unit": "count", "units": "count",
    "bed": "count", "beds": "count", "bedroom": "count", "bedrooms": "count",
    "tree": "count", "trees": "count",
}
_STORED_UNIT_EXACT = {"m": "length", "m2": "area", "sqm": "area",
                      "hours": "time", "storeys": "count"}


def stored_family(unit) -> Optional[str]:
    """Which KIND of thing the row's own column measures, or None if unknown.

    Prefix rules because the column is free text: every real value is one of
    'm', 'm2', 'hours', 'storeys', something starting '%' (200+ rows, including
    '% of landscaped area' and '% impervious'), or something containing
    'spaces/' (450+ rows across spaces/dwelling, visitor_spaces/dwelling,
    spaces/room, spaces/bed and five more). Leaving those unrecognised is what
    let a 'spaces/dwelling' row be explained by '3 hours of sunlight'.
    """
    text = (unit or "").strip().lower()
    if not text:
        return None
    if text in _STORED_UNIT_EXACT:
        return _STORED_UNIT_EXACT[text]
    if text.startswith("%"):
        return "ratio"
    if "spaces/" in text or text.startswith("spaces"):
        return "rate"
    return None


def _family_conflict(source: str, end: int, unit) -> bool:
    """True when the text labels this quantity as a different KIND of thing.

    Only fires when BOTH sides are known: an unlabelled number, or a stored unit
    this does not recognise, is never rejected on these grounds. Rejecting on a
    guess would manufacture findings, which is the mirror of the failure the rule
    exists to prevent.

    'rate' is deliberately compatible with 'count': a `spaces/dwelling` value is
    genuinely written as "1 space per 4 dwellings", so counted nouns beside it are
    the expected phrasing, not a conflict.
    """
    family = stored_family(unit)
    if not family:
        return False
    match = _TRAILING_UNIT_RE.match(source, end)
    if not match:
        return False
    text_family = _UNIT_FAMILY.get(re.sub(r"\s+", " ", match.group(1).lower()))
    if not text_family:
        return False
    if {family, text_family} == {"rate", "count"}:
        return False
    return text_family != family


def _rule_exact_digit_match(value: float, source: str, unit) -> Optional[str]:
    """The number appears literally in the text.

    Compares numeric TOKENS, not substrings: a substring test would let a stored
    5 be 'found' inside '15', which is the loosest possible way to declare a row
    clean and would hide exactly the mismatches this exists to surface. Numbered-
    list ordinals are excluded for the same reason.
    """
    for parsed, start, end in _quantity_spans(source):
        if abs(parsed - value) > _EXACT_TOL:
            continue
        # "a minimum of 3 hours of sunlight" must not explain a 3 metre setback.
        if _family_conflict(source, end, unit):
            continue
        return f"{source[start:end]!r} appears in the source text"
    return None


def _rule_percentage_phrasing(value: float, source: str, unit) -> Optional[str]:
    """A percentage written as '35%' stored as the fraction 0.35.

    Only that direction. Multiplying a quoted percentage BY 100 was also accepted
    once, which let a stored 3500 be "explained" by a quoted 35% — nobody stores a
    percentage that way, and the rule existed only to manufacture matches.

    Gated on the stored column measuring a ratio (or being unlabelled): without
    that, a quoted "Minimum 35% landscaped area" explained a 0.35 METRE setback.
    """
    if stored_family(unit) not in (None, "ratio"):
        return None
    for token in _PERCENT_RE.findall(source):
        pct = _as_float(token)
        if pct is None:
            continue
        if _close(value, pct / 100.0):
            return f"'{token}%' stored as a fraction"
    return None


def _rule_unit_conversion(value: float, source: str, unit) -> Optional[str]:
    """A length quoted in mm or cm and stored in metres (or the reverse).

    LENGTH only. 'm2' was allowed too, so a quoted "900mm" explained a 0.9 square
    metre value — a different kind of thing. An unlabelled unit is also refused
    here rather than assumed to be metres, because a conversion is a claim about
    what the number measures and 49 rows carry no unit at all.

    One direction only: dividing BY the factor was accepted once, so a quoted
    "0.9mm" explained a stored 900 m. Nothing is quoted in millimetres and stored
    in kilometres.
    """
    if stored_family(unit) != "length":
        return None
    for token, raw_unit in _LENGTH_RE.findall(source):
        parsed = _as_float(token)
        factor = _TO_METRES.get(raw_unit.lower())
        if parsed is None or factor is None or factor == 1.0:
            continue
        if _close(value, parsed * factor):
            return f"'{token}{raw_unit}' converted to {parsed * factor:g} m"
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
        # of it belongs to a different control. Cutting on a bare "." also split
        # DECIMALS — "0.5 spaces per 4 dwellings" left "5 spaces" as the lead and
        # produced 5/4, so a stored 1.25 passed against a quote stating 0.125.
        cut = _LEAD_BREAK_RE.search(lead)
        while cut:
            lead = lead[cut.end():]
            cut = _LEAD_BREAK_RE.search(lead)
        numerators = _ANY_NUMBER_RE.findall(lead)
        if not numerators:
            yield None, b, match.group(0).strip(), lead
            continue
        # ONLY the nearest numerator. Offering every number in the lead meant a
        # quote reading "Minimum setback 6m and provide 1 space per 4 dwellings"
        # could explain a stored 1.5 as 6/4 — a rate assembled from two unrelated
        # clauses. The number attached to a rate is the one immediately before it.
        for token in reversed(numerators):
            a = _as_float(token)
            if a is not None:
                yield a, b, f"{token} ... {match.group(0).strip()}", lead
                break


def _rule_ratio_or_rate(value: float, source: str, unit) -> Optional[str]:
    """A rate written as 'A per B' stored as the quotient A/B.

    Refused on a length, area or time column: a quote reading "1 visitor space per
    4 dwellings" must not explain a stored 0.25 METRE setback that someone attached
    the wrong source_text to. No live row relies on it — 0 of the 90 rate-explained
    rows sit on such a column — so this only closes a future path.
    """
    if stored_family(unit) in ("length", "area", "time"):
        return None
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
    Same column gate as ``_rule_ratio_or_rate``.
    """
    if stored_family(unit) in ("length", "area", "time"):
        return None
    for a, b, evidence, lead in _rate_candidates(source):
        if a is not None:
            continue
        # The implied "one" has to be written as SOMETHING. "An additional car
        # parking space for every 4 dwellings" says one space; "Visitor parking
        # must be considered for every 4 dwellings" states no quantity at all,
        # and deriving 1/4 from it invents the numerator outright.
        if not _SINGULAR_ARTICLE_RE.search(lead):
            continue
        if _close(value, 1.0 / b):
            return f"{evidence!r} with an implied numerator of 1"
    return None


def _rule_fraction_literal(value: float, source: str, unit) -> Optional[str]:
    """A fraction written as a fraction: 'min 1/3' stored as 0.333.

    Refused on a length, area or time column, like the rate rules: "At least 1/3
    of the landscaped area must be deep soil" must not explain a stored 0.333
    METRE setback on a row whose source_text was attached to the wrong control.
    """
    if stored_family(unit) in ("length", "area", "time"):
        return None
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
    """An area quoted as dimensions ('3m x 3m') stored as the product.

    Gated on an area unit: without it, '9' in a `spaces/dwelling` column would be
    explained by a 3 m x 3 m parking bay — a number that happens to match an area
    the row is not measuring.
    """
    # An explicit area unit is REQUIRED — a NULL unit is not good enough. 49 rows
    # carry no unit, and reading one of those as square metres would let a 3m x 3m
    # bay explain a value that is actually a count. All 5 real matches carry 'm2'.
    if unit not in ("m2", "m²", "sqm"):
        return None
    for first, second in _DIMENSIONS_RE.findall(source):
        a, b = _as_float(first), _as_float(second)
        if a is None or b is None:
            continue
        if _close(value, a * b):
            return f"'{first} x {second}' -> {a * b:g}"
    return None


def _rule_written_numeral(value: float, source: str, unit) -> Optional[str]:
    """The number is spelled out ('three hours', 'nil parking').

    Last in the order on purpose, and the numeral must be COUNTING something:
    'one' is an ordinary English word, and without that requirement 'Objective
    one: provide a minimum 6m front setback' explains a stored 1 m setback.
    """
    for match in _COUNTED_NUMERAL_RE.finditer(source):
        parsed = _WORD_NUMBERS[match.group("word").lower()]
        if abs(parsed - value) > _EXACT_TOL:
            continue
        # Same guard the exact rule carries: "a minimum of three hours of
        # sunlight" must not explain a 3 metre setback just because it spells
        # the number out instead of writing it.
        #
        # Checked against the NOUN the regex matched, not the position after the
        # numeral: "three full hours" put the word 'full' where the unit would be,
        # so the trailing-unit scan saw nothing and the conflict went undetected.
        family = stored_family(unit)
        noun_family = _UNIT_FAMILY.get(match.group("noun").lower())
        if (family and noun_family and noun_family != family
                and {family, noun_family} != {"rate", "count"}):
            continue
        return f"written numeral in {match.group(0).strip()!r}"
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
# A number stored with NO quote at all. Distinct from both of the above and
# treated as a failure, not a skip: folding it into NO_VALUE_STORED would let a
# served number with nothing behind it pass as "nothing to check". No row is in
# this state today (0 of 1,069), which is exactly why it needs a state — the
# check would otherwise wave through the first one that appears.
MISSING_SOURCE_TEXT = "MISSING_SOURCE_TEXT"
# The quote was cut off by the extractor, so it is not evidence either way. 23
# rows carry a source_text of exactly 400 characters, every one ending mid-word.
# Both failure directions were observed in the same council: cumberland 30 (rear
# 8m, CORRECT) was FALSELY FLAGGED because "Minimum 8m" fell outside the cut,
# and cumberland 28 (front 6m, served) FALSELY PASSES because "Minimum 6m"
# happened to fall inside it. A verdict from a severed quote is not a verdict.
TRUNCATED_EVIDENCE = "TRUNCATED_EVIDENCE"
FAILING_STATES = (UNEXPLAINED, MISSING_SOURCE_TEXT, TRUNCATED_EVIDENCE)

# The extractor's hard limit. Anything at exactly this length is treated as a
# cut. An earlier version exempted quotes ending in punctuation ("a complete
# quote would end in a full stop") — but a cut can land immediately AFTER
# punctuation, so a terminal '.' at the cap separates nothing: at exactly the
# limit a complete quote is indistinguishable from a severed one, and evidence
# that cannot be told from severed evidence is not evidence. (All 21 at-limit
# rows measured 2026-08-03 end mid-word, so closing the escape changed no
# verdict; it closes the hole for the next extraction.)
TRUNCATION_LIMIT = 400


def evidence_is_truncated(source_text) -> bool:
    """True when the quote sits at the extractor's hard limit — cut, or
    indistinguishable from one."""
    return len(str(source_text or "")) == TRUNCATION_LIMIT


def explain_value(value, source_text, unit=None) -> tuple[str, Optional[str]]:
    """Name the rule that derives ``value`` from ``source_text``, with evidence.

    Returns ``(rule_name, evidence)``; ``(UNEXPLAINED, None)`` when no rule fires,
    and ``(MISSING_SOURCE_TEXT, None)`` when a real number carries no quote at all.
    An absent or non-numeric value returns ``(NO_VALUE_STORED, None)`` — there is
    nothing to check, which is deliberately NOT the same as passing.
    """
    if value is None:
        return NO_VALUE_STORED, None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return NO_VALUE_STORED, None
    # Postgres `numeric` accepts NaN, and every comparison against NaN is False —
    # so `abs(parsed - value) > tolerance` was False and a NaN row fell straight
    # through the exact rule's `continue` into an "explained" verdict.
    if number != number or number in (float("inf"), float("-inf")):
        return UNEXPLAINED, None
    if not str(source_text or "").strip():
        return MISSING_SOURCE_TEXT, None
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
    elif evidence_is_truncated(row.get(source_field)):
        # Checked BEFORE the rules are consulted. Whether a rule happens to fire
        # depends on which side of the cut the number landed on, so an explained
        # verdict here would be luck reported as verification.
        state = TRUNCATED_EVIDENCE
    elif any(r["rule"] == MISSING_SOURCE_TEXT for r in checked.values()):
        state = MISSING_SOURCE_TEXT
    elif any(r["rule"] == UNEXPLAINED for r in checked.values()):
        state = UNEXPLAINED
    else:
        state = max((r["rule"] for r in checked.values()), key=RULE_NAMES.index)

    # How many DISTINCT quantities the quote holds. An exact match against a quote
    # carrying one number is uniquely attributable; against a quote carrying six,
    # the stored value is consistent with the text but so might a different number
    # be. 68% of exact matches are in the second case, so reporting the split
    # stops "exact_digit_match" reading as stronger evidence than it is.
    quantities = len({v for v, _, _ in _quantity_spans(str(row.get(source_field) or ""))})
    return {"state": state, "fields": per_field,
            "quote_quantity_count": quantities,
            "uniquely_attributable": quantities == 1}


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
