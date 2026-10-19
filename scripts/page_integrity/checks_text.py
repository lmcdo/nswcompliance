"""Rendered-text and derivation checks for one captured address page.

prior-art-checked: rendered-text checks per address; scripts/liability_language_check.py and lint_fabricated_verdicts.py scan source diffs, not rendered pages

C2 engines_agree, C5 words_on_page, C6 derivations. Each is a pure function (cap) -> list[Flag].
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from scripts.page_integrity.load import Capture

try:  # reuse the repo's word list; import has no side effects (main() is guarded)
    from scripts.liability_language_check import FLAGGED_TERMS
except Exception:  # pragma: no cover
    FLAGGED_TERMS = None


@dataclass
class Flag:
    check: str
    fact: str
    detail: str
    evidence: Any = field(default_factory=dict)


# Residential forms denser than a dwelling house, as they appear (normalised) in the LEP table.
# This names forms only; whether a form is permitted in a zone is read from the capture.
DENSER_FORMS = (
    "dual_occupanc", "semi_detached", "attached_dwelling", "multi_dwelling_housing",
    "manor_house", "residential_flat_building", "shop_top_housing",
)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")


def _num(v: Any) -> Optional[float]:
    if v is None or isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v)


def _lot_area(cap: Capture) -> Optional[float]:
    prop = cap.data("/api/property")
    if isinstance(prop, dict):
        a = _num((prop.get("lotDimensions") or {}).get("area"))
        if a:
            return a
    ca = cap.data("/api/constraint-arithmetic")
    return _num(ca.get("lot_area_m2")) if isinstance(ca, dict) else None


# ---------------------------------------------------------------- C2
def check_engines_agree(cap: Capture) -> list[Flag]:
    ca = cap.data("/api/constraint-arithmetic")
    perm = cap.data("/api/lep/permissibility")
    if not isinstance(ca, dict) or not isinstance(perm, dict) or not perm.get("covered"):
        return []
    # A form at house density (e.g. 'dwelling_house') disagrees just as much as None does.
    shown = ca.get("max_permitted_form")
    if shown is not None and _norm(str(shown)).startswith(DENSER_FORMS):
        return []
    rows = [e for e in perm.get("entries") or []
            if isinstance(e, dict) and _norm(e.get("permissibility") or "") == "permitted"
            and _norm(e.get("development_type") or "").startswith(DENSER_FORMS)]
    if not rows:
        return []
    forms = ", ".join(str(r.get("development_type") or "") for r in rows)
    return [Flag("C2", "engines-agree",
                 f"yield box shows a single-number yield (max_permitted_form {shown!r}, as_of_right_form="
                 f"{ca.get('as_of_right_form')!r}) but the permissibility table lists as permitted in "
                 f"zone {perm.get('zone')}: {forms}",
                 {"permissibility_rows": rows, "as_of_right_form": ca.get("as_of_right_form"),
                  "zone": perm.get("zone")})]


# ---------------------------------------------------------------- C5
_ASOFRIGHT = re.compile(r"as[-\s]of[-\s]right", re.I)
_DA = re.compile(r"development application|subject to a DA", re.I)
_JUNK_WORDS = re.compile(r"(?<![\w-])(undefined|NaN|null)(?![\w-])|\[object")
_CLASS = re.compile(r"\bClass Class\b")
_DOUBLED = re.compile(r"\b(\w{3,})[ \t]+\1\b", re.I)
_DOUBLE_YEAR = re.compile(r"\b(?:19|20)\d\d/(?:19|20)\d\d\b")


def scan_text(tab: str, text: str) -> list[Flag]:
    out: list[Flag] = []
    lines = text.splitlines()
    for m in _ASOFRIGHT.finditer(text):
        ln = text.count("\n", 0, m.start()) + 1
        out.append(Flag("C5", "as-of-right", f"{tab}:{ln} term of art/verdict {m.group(0)!r}",
                        {"tab": tab, "line": ln, "text": lines[ln - 1][:240]}))
        win = text[max(0, m.start() - 200): m.end() + 200]
        d = _DA.search(win)
        if d:
            out.append(Flag("C5", "contradiction",
                            f"{tab}:{ln} 'as-of-right' within 200 chars of {d.group(0)!r}",
                            {"tab": tab, "line": ln, "window": win}))
    for ln, line in enumerate(lines, 1):
        ev = {"tab": tab, "line": ln, "text": line[:240]}
        for m in _JUNK_WORDS.finditer(line):
            out.append(Flag("C5", "render-junk", f"{tab}:{ln} {m.group(0)!r}", ev))
        for _ in _CLASS.finditer(line):
            out.append(Flag("C5", "render-junk", f"{tab}:{ln} 'Class Class'", ev))
        for m in _DOUBLED.finditer(line):
            if not m.group(1).isdigit():
                out.append(Flag("C5", "render-junk", f"{tab}:{ln} doubled word {m.group(0)!r}", ev))
        for m in _DOUBLE_YEAR.finditer(line):
            out.append(Flag("C5", "render-junk", f"{tab}:{ln} double year {m.group(0)!r}", ev))
        if FLAGGED_TERMS is not None:
            for m in FLAGGED_TERMS.finditer(line):
                out.append(Flag("C5", "liability-word",
                                f"severity=info {tab}:{ln} {m.group(0)!r} (may be quoted regulatory text)", ev))
    return out


def check_words_on_page(cap: Capture) -> list[Flag]:
    out: list[Flag] = []
    for tab, text in cap.rendered.items():
        out.extend(scan_text(tab, text))
    return out


# ---------------------------------------------------------------- C6
_FOOTPRINT = re.compile(r"Buildable footprint:\s*([\d,.]+)\s*m²\s*\(\s*([\d.]+)\s*%\s*of lot\s*\)")


def check_derivations(cap: Capture) -> list[Flag]:
    out: list[Flag] = []
    ca = cap.data("/api/constraint-arithmetic")
    lot = _lot_area(cap)
    for tab, text in cap.rendered.items():
        for m in _FOOTPRINT.finditer(text):
            pct = float(m.group(2))
            if pct > 100:
                out.append(Flag("C6", "footprint-pct",
                                f"{tab}: footprint {m.group(1)}m² shown as {pct:g}% of lot (>100)",
                                {"tab": tab, "text": m.group(0), "lot_area_m2": lot}))
    if isinstance(ca, dict) and lot:
        fp = _num(ca.get("buildable_footprint_m2"))
        if fp is not None and fp > lot * 1.0005:
            out.append(Flag("C6", "footprint-pct",
                            f"buildable_footprint_m2 {fp} exceeds lot area {lot} ({fp / lot * 100:.0f}%)",
                            {"buildable_footprint_m2": fp, "lot_area_m2": lot}))
        if "FSR is the binding control" in str(ca.get("binding_constraint_label") or ""):
            fsr = _num(ca.get("lep_fsr"))
            if fsr:
                expect = fsr * lot
                for key in ("lep_max_gfa_from_fsr_m2", "lep_envelope_gfa_m2"):
                    v = _num(ca.get(key))
                    if v is not None and abs(v - expect) > 0.02 * expect:
                        out.append(Flag("C6", "fsr-gfa",
                                        f"{key} {v} != FSR {fsr} x lot {lot} = {expect:.1f} (>2%)",
                                        {"field": key, "value": v, "expected": expect}))
    return out


def facts_checked(cap: Capture) -> dict[str, bool]:
    ca = cap.data("/api/constraint-arithmetic")
    perm = cap.data("/api/lep/permissibility")
    lot = _lot_area(cap)
    ca_ok = isinstance(ca, dict)
    tabs = all(k in cap.rendered for k in ("sepp", "planning", "dcp"))
    fsr_binding = bool(ca_ok and "FSR is the binding control" in str(ca.get("binding_constraint_label") or "")
                       and _num(ca.get("lep_fsr")))
    return {
        "engines-agree": bool(ca_ok and isinstance(perm, dict) and perm.get("covered")),
        "as-of-right": tabs,
        "contradiction": tabs,
        "render-junk": tabs,
        "liability-word": FLAGGED_TERMS is not None,
        "footprint-pct": bool(lot and (ca_ok or any(_FOOTPRINT.search(t) for t in cap.rendered.values()))),
        "fsr-gfa": bool(lot and fsr_binding),
    }


def run_all(cap: Capture) -> list[Flag]:
    return check_engines_agree(cap) + check_words_on_page(cap) + check_derivations(cap)
