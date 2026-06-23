# prior-art-checked: reuse not viable because nothing validates that an extracted
# dcp_setback_controls VALUE semantically matches its SOURCE clause. Existing
# setback code checks structure/routing/display only: migrations/031 (schema),
# migrations/051 + dcp_extract_changed.py (review queue, fires on CHANGES only),
# tests/test_setback_taxonomy.py (consuming-engine routing), scripts/verify_setback_*
# (human-readable dumps). This is the missing data-side semantic gate.
"""Deterministic semantic validator for ``dcp_setback_controls``.

Why this exists
---------------
DCP setback rules are extracted from council PDFs by a regex extractor that
labels each number with a ``control_type`` from a *context hint*, never checking
that the number actually came from a clause about that control. The initial bulk
load also never passed the human review queue (the queue only fires on later
*changes*). So a number scraped from a non-setback clause — e.g. Burwood
``front_setback`` 9 m and 15 m, lifted from clause P8 (two-storey appropriateness)
and P39 (duplex streetscape) — reached production looking authoritative.

This module is the gate that was missing: a DETERMINISTIC (no LLM — see the
project's "deterministic only, no AI interpretation of regulations" rule) check
that flags setback rows whose stored value is unlikely to be a real setback.

It is multi-signal on purpose, so a row is caught even when any single signal is
weak:

* CONFLICT      — >1 distinct value for the same (lga, control_type, dev_type)
                  with NO ``condition`` on any row to disambiguate them.
* FOREIGN       — ``source_text`` carries strong language of a *different* control
                  (duplex, streetscape, between-facades, floor space, parking,
                  solar, deep soil, site coverage) and NO setback language.
* MAGNITUDE     — an implausible distance (front > 10 m, side > 3 m, rear > 12 m).
* PLACEHOLDER   — an "assumed / verify / standard NSW" row presented as extracted.

CONFLICT and FOREIGN are HIGH severity (almost always real defects); MAGNITUDE
and PLACEHOLDER are ADVISORY (legitimate tiered/large controls exist).

The pure functions take already-fetched row dicts so they unit-test offline.
``main()`` runs one read-only ``SELECT`` over the live table and prints the
statewide list, exiting non-zero when any HIGH-severity row is found.
"""
from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from typing import Optional

# Reuse the generic, domain-agnostic integrity engine (same check runs on any
# extracted table; here configured for setbacks).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.extracted_data_integrity import fabricated_values as _generic_fabricated_values  # noqa: E402

SETBACK_TYPES = {"front_setback", "side_setback", "rear_setback"}

# Distances that read as genuine setback / boundary language.
_SETBACK_POS = re.compile(
    r"\bset\s?backs?\b|\bboundar(?:y|ies)\b|building line|street alignment|"
    r"\bfrontage\b|from the (?:front|rear|side)|primary street|secondary street|"
    r"behind the (?:front|building)",
    re.I,
)

# Strong evidence the clause is about a DIFFERENT, non-setback control. These
# tokens almost never appear in a real setback clause. (Deliberately excludes
# bare "storey" — storey-tiered setbacks legitimately mention storeys.)
_FOREIGN = re.compile(
    r"\bduplex\b|streetscape|building appearance|appearance provisions?|"
    r"between[^.]{0,40}fa[cç]ades?|separation between|"
    r"gross floor|floor space ratio|\bfsr\b|site coverage|deep soil|"
    r"landscaped? area|landscaping|private open space|\bpos\b|"
    r"car\s?park|parking space|solar access|overshadow",
    re.I,
)

_PLACEHOLDER = re.compile(r"assume|verify|standard nsw", re.I)

_MAGNITUDE_MAX = {"front_setback": 10.0, "side_setback": 3.0, "rear_setback": 12.0}


def _num(v) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def conflict_groups(rows: list[dict]) -> list[dict]:
    """Setback groups with >1 distinct value and NO condition to disambiguate."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        if r.get("control_type") in SETBACK_TYPES and _num(r.get("value_min")) is not None:
            groups[(r.get("lga"), r.get("control_type"), r.get("dev_type"))].append(r)
    out: list[dict] = []
    for (lga, ct, dt), grp in groups.items():
        vals = sorted({_num(r.get("value_min")) for r in grp})
        if len(vals) < 2:
            continue
        if any((r.get("condition") or "").strip() for r in grp):
            continue  # tiered controls with conditions — the engine can disambiguate
        out.append({
            "lga": lga, "control_type": ct, "dev_type": dt,
            "value": vals, "signal": "CONFLICT", "severity": "high",
            "detail": f"{len(vals)} values {[f'{v:g}m' for v in vals]} with no condition to choose between",
        })
    return out


def foreign_language(rows: list[dict]) -> list[dict]:
    """Setback rows whose source_text reads as a different control (no setback language)."""
    out: list[dict] = []
    for r in rows:
        if r.get("control_type") not in SETBACK_TYPES:
            continue
        src = (r.get("source_text") or "").strip()
        if not src:
            continue
        if _FOREIGN.search(src) and not _SETBACK_POS.search(src):
            out.append({
                "lga": r.get("lga"), "control_type": r.get("control_type"),
                "dev_type": r.get("dev_type"), "value": _num(r.get("value_min")),
                "signal": "FOREIGN", "severity": "high",
                "detail": f"source reads as another control, no setback language: {src[:90]!r}",
            })
    return out


def implausible_magnitude(rows: list[dict]) -> list[dict]:
    """Setback distances beyond a plausible ceiling (advisory — tiered highs exist)."""
    out: list[dict] = []
    for r in rows:
        ct = r.get("control_type")
        v = _num(r.get("value_min"))
        cap = _MAGNITUDE_MAX.get(ct)
        if cap is not None and v is not None and v > cap:
            out.append({
                "lga": r.get("lga"), "control_type": ct, "dev_type": r.get("dev_type"),
                "value": v, "signal": "MAGNITUDE", "severity": "advisory",
                "detail": f"{v:g}m exceeds the plausible {ct} ceiling ({cap:g}m)",
            })
    return out


def placeholder_rows(rows: list[dict]) -> list[dict]:
    """Rows whose own condition says they are assumed/unverified (advisory)."""
    out: list[dict] = []
    for r in rows:
        cond = r.get("condition") or ""
        if _PLACEHOLDER.search(cond):
            out.append({
                "lga": r.get("lga"), "control_type": r.get("control_type"),
                "dev_type": r.get("dev_type"), "value": _num(r.get("value_min")),
                "signal": "PLACEHOLDER", "severity": "advisory",
                "detail": f"assumed/unverified: {cond[:90]!r}",
            })
    return out


_FABRICATED_MARKER = re.compile(
    r"standard.{0,3}pattern.{0,3}assumed|assumed standard|standard nsw pattern|"
    r"assumed[^.]{0,30}pattern",
    re.I,
)


def fabricated_value_rows(rows: list[dict]) -> list[dict]:
    """The hard invariant: a row must NEVER store a number it admits is a guess.

    Setback-specific wrapper over the reusable
    :func:`services.extracted_data_integrity.fabricated_values` engine — same
    check that runs on any extracted table, here keyed to value_min and the
    setback marker fields. After the insert-script fix an unverified row stores
    ``value_min = NULL`` (rule exists, value unknown), so this set must be empty;
    any non-empty result is fabricated data presented as fact and fails the build.
    """
    flagged = _generic_fabricated_values(
        rows, value_field="value_min",
        marker_fields=["review_reason", "condition"],
        marker_pattern=_FABRICATED_MARKER,
    )
    out: list[dict] = []
    for r in flagged:
        if _num(r.get("value_min")) is None:  # guard: only numeric value_min counts
            continue
        marker = f"{r.get('review_reason') or ''} {r.get('condition') or ''}"
        out.append({
            "lga": r.get("lga"), "control_type": r.get("control_type"),
            "value": _num(r.get("value_min")), "signal": "FABRICATED",
            "severity": "high",
            "detail": f"stores a number but marks it assumed: {marker[:90]!r}",
        })
    return out


def audit_setback_controls(rows: list[dict]) -> list[dict]:
    """Run all signals and return a flat list of flagged rows/groups."""
    return (
        conflict_groups(rows)
        + foreign_language(rows)
        + implausible_magnitude(rows)
        + placeholder_rows(rows)
    )


def high_severity(findings: list[dict]) -> list[dict]:
    return [f for f in findings if f.get("severity") == "high"]


def _fetch_rows():  # pragma: no cover - thin DB shim, exercised by main()
    import psycopg2
    from psycopg2.extras import RealDictCursor

    url = os.environ.get("DATABASE_URL")
    if not url:
        env = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env):
            for line in open(env, encoding="utf-8", errors="replace"):
                if line.startswith("DATABASE_URL="):
                    url = line.partition("=")[2].strip().strip('"')
                    break
    if not url:
        raise SystemExit("DATABASE_URL not set")
    conn = psycopg2.connect(url)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT lga, control_type, dev_type, value_min, value_max,
               unit, condition, source_text, section_ref, review_reason
        FROM dcp_setback_controls
        WHERE is_current = TRUE
        """
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def main():  # pragma: no cover - manual / cron entry point
    rows = _fetch_rows()
    findings = audit_setback_controls(rows)
    highs = high_severity(findings)
    by_sig: dict[str, int] = defaultdict(int)
    for f in findings:
        by_sig[f["signal"]] += 1
    print(f"Scanned {len(rows)} current setback rows.")
    print("Signal counts:", dict(by_sig))
    print(f"\nHIGH-severity findings ({len(highs)}):")
    for f in sorted(highs, key=lambda x: (x["lga"] or "", x["control_type"] or "")):
        print(f"  [{f['signal']:8}] {f['lga']:22} {f['control_type']:14} {f['dev_type']:18} {f['detail']}")
    print(f"\nADVISORY findings ({len(findings) - len(highs)}):")
    for f in sorted((f for f in findings if f["severity"] != "high"), key=lambda x: (x["lga"] or "", x["control_type"] or "")):
        print(f"  [{f['signal']:8}] {f['lga']:22} {f['control_type']:14} {f['detail']}")
    sys.exit(1 if highs else 0)


if __name__ == "__main__":
    main()
