#!/usr/bin/env python3
# prior-art-checked: four sweeps 2026-11-07 on origin/main eaa9964d. (1) DB content: housing_sepp_standards
# is filled by hand-typed SQL migrations (045, 047, 084, 090, 114), carries no law-version or text-hash
# column, and holds no Chapter 5 figures. (2) Frontend: Chapter 5 figures are typed as prose in
# components/compliance/StateLevelControls.tsx; __tests__/lib/tod-no-fabricated-standards.test.ts checks
# wording only, never the figures against the law. (3) Python: scripts/provenance_check.py checks row
# quotes against the LIVE law weekly in production, not in CI; legislation_monitor.py stamps rows stale.
# None parses Schedule 11/12, the s163 distances or s164 from the saved text. (4) Plans:
# ce-lmr-tod-clean-state-law-PLAN-2026-11-07.md sections 2c/2e/2g.
"""Extract the law facts the low-and-mid-rise / TOD feature rests on, from the SAVED law text.

Reads `data/law/sepp-housing-2021-as-at-<date>.txt` and writes `data/law/housing_sepp_lmr_facts.json`.
Every fact carries its value, the clause, the PDF page (footer N/130 of the saved file) and the
sentence it came from, so no planning figure in the feature is typed by hand. The file also carries a
SHA-256 of the law text (line endings normalised), so the stored facts can be proven to belong to one
exact text.

Modes (no database, no network):
  (default / --check)  regenerate from the repo copy of the text and compare with the stored JSON;
                       exit 1 if they differ.
  --write              regenerate and write the JSON.
  --text PATH          extract from a newly saved law text and print what changed against the stored
                       JSON (the monthly routine: save the page, run this, read the diff).

A missing anchor raises; the extractor never returns an empty answer for something it could not find.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LAW_DIR = REPO_ROOT / "data" / "law"
FACTS_PATH = LAW_DIR / "housing_sepp_lmr_facts.json"
DEFAULT_TEXT = LAW_DIR / "sepp-housing-2021-as-at-2026-10-23.txt"

_MARKER = re.compile(r"^=====PAGE (\d+)\s*$")
_FOOTER = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}, \d{1,2}:\d{2} [AP]M |^https://legislation\.nsw\.gov\.au/")
_ORDER = ["a", "b", "c", "d", "e", "f", "f1", "g", "h", "i", "j", "k", "l", "m"]


class AnchorError(ValueError):
    """The saved text does not contain something the extractor needs."""


def normalise(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def text_sha256(text: str) -> str:
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()


def _noise(line: str) -> bool:
    return bool(_MARKER.match(line) or _FOOTER.match(line))


def _pages(lines: list[str]) -> list[int]:
    page, out = 1, []
    for line in lines:
        m = _MARKER.match(line)
        if m:
            page = int(m.group(1))
        out.append(page)
    return out


def _last(lines: list[str], pattern: str, what: str, start: int = 0) -> int:
    rx = re.compile(pattern)
    hits = [i for i in range(start, len(lines)) if rx.match(lines[i].strip())]
    if not hits:
        raise AnchorError(f"anchor not found: {what} ({pattern})")
    return hits[-1]


def _first(lines: list[str], pattern: str, what: str, start: int = 0, stop: int | None = None) -> int:
    rx = re.compile(pattern)
    for i in range(start, len(lines) if stop is None else stop):
        if rx.match(lines[i].strip()):
            return i
    raise AnchorError(f"anchor not found: {what} ({pattern})")


def _joined(lines: list[str], a: int, b: int) -> str:
    return re.sub(r"\s+", " ", " ".join(s.strip() for s in lines[a:b] if not _noise(s))).strip()


def _fact(value, clause: str, page: int, quote: str, **extra) -> dict:
    return {"value": value, "clause": clause, "page": page, "quote": quote, **extra}


def _num(pattern: str, text: str, what: str) -> tuple[str, str]:
    m = re.search(pattern, text)
    if not m:
        raise AnchorError(f"figure not found: {what} ({pattern})")
    return (m.group(1) if m.re.groups else m.group(0)), m.group(0)


def _walk_distance(lines, pages, heading: str, clause: str) -> dict:
    i = _last(lines, rf"^{re.escape(heading)} means—$", clause)
    chunk = _joined(lines, i, i + 6)
    value, quote = _num(r"within (\d+)m walking distance of", chunk, clause)
    return _fact(int(value), clause, pages[i], quote, unit="m", measured="walking distance")


def _stations(lines, pages, header: str, stop_pattern: str | None, clause: str) -> dict:
    start = _last(lines, rf"^{re.escape(header)}", clause)
    stop = _first(lines, stop_pattern, f"end of {clause}", start + 1) if stop_pattern else len(lines)
    names = [s.strip() for s in lines[start + 1 : stop] if not _noise(s) and re.match(r"^.+ station$", s.strip())]
    if not names:
        raise AnchorError(f"no stations found: {clause}")
    last_idx = max(i for i in range(start + 1, stop) if lines[i].strip() == names[-1])
    return _fact(names, clause, pages[start], f"{len(names)} station names listed", pages_to=pages[last_idx], count=len(names))


def _lgas(lines, pages) -> dict:
    start = _last(lines, r"^\(1\)\s+This chapter applies to land in the following local government areas", "s152(1)")
    stop = _first(lines, r"^Note—$", "end of s152(1) list", start + 1)
    names = []
    for s in lines[start + 1 : stop]:
        m = re.match(r"^\(([a-z])\)\s+(.*?)[,.]?$", s.strip())
        if m and "Repealed" not in m.group(2):
            names.append(m.group(2))
    if not names:
        raise AnchorError("no LGAs found: s152(1)")
    return _fact(names, "s152(1)", pages[start], _joined(lines, start, start + 2), count=len(names))


def _accessible_area(lines, pages) -> dict:
    """The dictionary meaning of "accessible area": walking distances to a station / light rail platform / wharf and to a regular bus stop.

    These (not s163) are the distances the parking-rate paragraphs use ("0.2 parking spaces ... on land within an accessible area").
    """
    i = _last(lines, r"^accessible area means land within", "accessible area definition")
    chunk = _joined(lines, i, i + 14)
    rail, q_rail = _num(r"\(a\)\s*(\d+)m walking distance of.{0,260}?(?:wharf from which a Sydney Ferries ferry service operates)", chunk, "accessible area (a)")
    bus, q_bus = _num(r"\(c\)\s*(\d+)m walking distance of a bus stop used by a regular bus service", chunk, "accessible area (c)")
    per_hour, q_hour = _num(r"has at least (\d+) bus per hour servicing the bus stop", chunk, "accessible area bus frequency")
    return {
        "accessible_area_rail_distance": _fact(int(rail), "Schedule 10 dictionary, accessible area (a)", pages[i], q_rail, unit="m", measured="walking distance"),  # qa-ignore: _num raises AnchorError when the figure is missing, so rail is never None
        "accessible_area_bus_distance": _fact(int(bus), "Schedule 10 dictionary, accessible area (c)", pages[i], q_bus, unit="m", measured="walking distance"),  # qa-ignore: _num raises AnchorError when the figure is missing, so bus is never None
        "accessible_area_bus_min_per_hour": _fact(int(per_hour), "Schedule 10 dictionary, accessible area (c)", pages[i], q_hour, unit="buses per hour"),
    }


def _parking_minimums(lines, pages) -> dict:
    """Every Chapter 6 non-discretionary parking minimum, one fact per (section, subsection), read from the text.

    Each such standard has the shape: "(c) if no environmental planning instrument or development control plan that applies to the land
    specifies a maximum number of car parking spaces per dwelling-a minimum of N car parking space(s) per dwelling". The section heading and the
    subsection opener say which development form and zone it belongs to; both are kept in `extra`. A section with no such sentence (s180 has none in the 23 October 2026 text)
    simply yields no fact; nothing is invented for it.
    """
    start = _last(lines, r"^165\s+Non-discretionary development standards", "s165")
    stop = _first(lines, r"^Chapter 7 ", "end of Chapter 6", start + 1)
    out: dict = {}
    section, heading, sub, applies = None, "", None, ""
    for i in range(start, stop):
        t = lines[i].strip()
        m = re.match(r"^(\d{3})\s+(Non-discretionary development standards.*)$", t)
        if m:
            section, heading, sub, applies = m.group(1), m.group(2), None, ""
            nxt = lines[i + 1].strip() if i + 1 < stop else ""
            if nxt and not re.match(r"^\(", nxt) and not _noise(lines[i + 1]):
                heading = f"{heading} {nxt}"
            continue
        m = re.match(r"^\((\d+)\)\s+(.*)$", t)
        if m and section:
            sub, applies = m.group(1), _joined(lines, i, i + 2)
            continue
        m = re.match(r"^\(([a-z])\)\s+if no environmental planning instrument or development control plan that applies to the land specifies a$", t)
        if m and section and sub:
            text = _joined(lines, i, i + 3)
            v, q = _num(
                r"if no environmental planning instrument or development control plan that applies to the land specifies a maximum number of car "
                r"parking spaces per dwelling—a minimum of (\d+(?:\.\d+)?) car parking spaces? per dwelling",
                text, f"s{section}({sub})({m.group(1)}) parking minimum")
            out[f"parking_min_s{section}_{sub}"] = _fact(
                float(v) if "." in v else int(v), f"s{section}({sub})({m.group(1)})", pages[i], q, unit="spaces per dwelling",
                section_heading=heading, applies_to=applies)
    if not out:
        raise AnchorError("no Chapter 6 parking minimums found")
    return out


def _s164(lines, pages) -> dict:
    s164 = _last(lines, r"^164\s+Land to which chapter applies$", "s164 heading")
    start = _first(lines, r"^\(1\)\s+This chapter applies to the whole of the State, other than the following—$", "s164(1)", s164)
    stop = _first(lines, r"^\((2|3)\)\s", "end of s164(1)", start + 1)
    paras: list[dict] = []
    idx = 0
    for i in range(start + 1, stop):
        s = lines[i].strip()
        m = re.match(r"^\((\w+)\)\s+(.*)$", s)
        if idx < len(_ORDER) and m and m.group(1) == _ORDER[idx]:
            paras.append({"para": _ORDER[idx], "_i": i, "_text": [m.group(2)]})
            idx += 1
        elif paras and not _noise(lines[i]) and s:
            paras[-1]["_text"].append(s)
    if idx != len(_ORDER):
        raise AnchorError(f"s164(1) paragraphs: expected {len(_ORDER)}, found {idx}")
    out = []
    for p in paras:
        words = re.sub(r"\s+", " ", " ".join(p["_text"])).strip()
        out.append(
            {
                "para": p["para"],
                "clause": f"s164(1)({p['para']})",
                "page": pages[p["_i"]],
                "repealed": words.startswith("(Repealed)"),
                # Full wording. A cap here once cut paragraph (g) mid-word after 17 of its 23 councils.
                "words": words,
            }
        )
    return {"clause": "s164(1)", "page": pages[start], "paragraphs": out, "live_count": sum(1 for p in out if not p["repealed"])}


def _section(lines, heading: str, next_heading: str) -> tuple[int, int]:
    a = _last(lines, heading, heading)
    b = _first(lines, next_heading, next_heading, a + 1)
    return a, b


def _tod_standards(lines, pages) -> dict:
    out: dict = {}
    a, b = _section(lines, r"^155\s+Maximum building height", r"^156\s+Affordable housing")
    t = _joined(lines, a, b)

    def at(label: str, start: int, end: int) -> int:
        return pages[_first(lines, rf"^\({label}\)\s", f"s155({label})", start, end)]

    v, q = _num(r"\(2\) The maximum building height for a residential flat building in a Transport Oriented Development Area is (\d+)m\.", t, "s155(2)")
    out["tod_height_residential_flat_building_m"] = _fact(int(v), "s155(2)", at("2", a, b), q, unit="m")
    v, q = _num(r"\(3\) The maximum building height for a building containing seniors housing or shop top housing in a Transport Oriented Development Area is (\d+)m\.", t, "s155(3)")
    out["tod_height_seniors_or_shop_top_m"] = _fact(int(v), "s155(3)", at("3", a, b), q, unit="m")
    v, q = _num(r"\(4\) The maximum floor space ratio .{0,200}? is (\d+(?:\.\d+)?:\d+)—", t, "s155(4)")
    out["tod_fsr"] = _fact(v, "s155(4)", at("4", a, b), q)

    a, b = _section(lines, r"^156\s+Affordable housing", r"^157\s+Affordable housing parking spaces")
    t = _joined(lines, a, b)
    v, q = _num(r"gross floor area of at least (\d+)m", t, "s156(1)")
    out["tod_affordable_gfa_threshold"] = _fact(
        int(v), "s156(1)", pages[a], q, unit="m2 (the superscript 2 is lost in the saved text: confirm against the PDF)", unit_verified=False
    )
    v, q = _num(r"at least (\d+)% of the gross floor area", t, "s156(2)(a)")
    out["tod_affordable_share_percent"] = _fact(int(v), "s156(2)(a)", pages[a], q, unit="%")

    a, b = _section(lines, r"^157\s+Affordable housing parking spaces", r"^158\s+Exception to minimum lot size")
    t = _joined(lines, a, b)
    for key, label, clause in (
        ("tod_affordable_parking_1_bed", r"for each dwelling containing 1 bedroom—([\d.]+) parking space", "s157(2)(a)"),
        ("tod_affordable_parking_2_bed", r"for each dwelling containing 2 bedrooms—([\d.]+) parking space", "s157(2)(b)"),
        ("tod_affordable_parking_3_plus_bed", r"for each dwelling containing 3 or more bedrooms—([\d.]+) parking space", "s157(2)(c)"),
    ):
        v, q = _num(label, t, clause)
        out[key] = _fact(float(v), clause, pages[a], q, unit="spaces per dwelling")

    a, b = _section(lines, r"^159\s+Minimum lot width", r"^160\s+Active street frontages")
    v, q = _num(r"the lot is at least (\d+)m wide at the front building line", _joined(lines, a, b), "s159")
    out["tod_min_lot_width_m"] = _fact(int(v), "s159", pages[a], q, unit="m")
    return out


def extract(text: str, text_file: str, version_date: str) -> dict:
    lines = normalise(text).split("\n")
    pages = _pages(lines)
    facts: dict = {}

    facts["lmr_outer_distance"] = _walk_distance(lines, pages, "low and mid rise housing area", "s163 low and mid rise housing area (a)")
    facts["lmr_inner_distance"] = _walk_distance(lines, pages, "low and mid rise housing inner area", "s163 low and mid rise housing inner area (a)")

    i = _last(lines, r"^walking distance means", "walking distance definition")
    facts["walking_distance_definition"] = _fact(None, "Schedule 10 dictionary, walking distance", pages[i], _joined(lines, i, i + 2))

    facts.update(_accessible_area(lines, pages))

    j = _last(lines, r"^low and mid rise housing area means—$", "s163 outer definition")
    whole = _joined(lines, j, j + 12)
    _, q = _num(r"\(b\) if a site area contains land identified in paragraph \(a\)—the site area", whole, "s163 site-area wording")
    facts["lmr_site_area_rule"] = _fact(None, "s163 low and mid rise housing area (b)", pages[j], q)

    facts["schedule_11_stations"] = _stations(lines, pages, "Schedule 11 Low and mid rise housing area stations", r"^Schedule 12 ", "Schedule 11")
    facts["schedule_12_stations"] = _stations(lines, pages, "Schedule 12 Deferred Transport Oriented Development stations", None, "Schedule 12")
    facts["tod_lgas"] = _lgas(lines, pages)
    facts["s164"] = _s164(lines, pages)

    k = next(p for p in facts["s164"]["paragraphs"] if p["para"] == "k")
    v, q = _num(r"land within (\d+)m of a public entrance to a railway, metro or light rail station listed in Schedule 12", k["words"], "s164(1)(k)")
    facts["s164_k_distance"] = _fact(int(v), "s164(1)(k)", k["page"], q, unit="m", measured="not stated (the paragraph does not say walking)")

    facts.update(_parking_minimums(lines, pages))

    h_par = next(p for p in facts["s164"]["paragraphs"] if p["para"] == "h")
    v, q = _num(r"land in an ANEF contour of (\d+) or greater or ANEC contour of (\d+) or greater", h_par["words"], "s164(1)(h)")
    anef, anec = re.search(r"ANEF contour of (\d+) or greater or ANEC contour of (\d+) or greater", h_par["words"]).groups()
    facts["s164_h_anef_min"] = _fact(int(anef), "s164(1)(h)", h_par["page"], q, unit="ANEF", measured="contour level")
    facts["s164_h_anec_min"] = _fact(int(anec), "s164(1)(h)", h_par["page"], q, unit="ANEC", measured="contour level")  # qa-ignore: the search above must match or .groups() raises; anec is never None

    i_par = next(p for p in facts["s164"]["paragraphs"] if p["para"] == "i")
    v, q = _num(r"land within (\d+)m of a relevant pipeline within the meaning of (.+?), section (\d+\.\d+)", i_par["words"], "s164(1)(i)")
    facts["s164_i_distance"] = _fact(int(v), "s164(1)(i)", i_par["page"], q, unit="m",
                                     measured="not stated (the paragraph does not say walking)",
                                     defined_in="State Environmental Planning Policy (Transport and Infrastructure) 2021, section 2.77")

    facts.update(_tod_standards(lines, pages))

    return {
        "instrument": "State Environmental Planning Policy (Housing) 2021",
        "law_version_date": version_date,
        "text_file": text_file,
        "text_sha256": text_sha256(text),
        "page_note": "page = PDF page of the saved file (the footer N/130); text before a PAGE marker belongs to the previous page",
        "facts": facts,
    }


def version_date_of(path: Path) -> str:
    m = re.search(r"as-at-(\d{4}-\d{2}-\d{2})", path.name)
    if not m:
        raise AnchorError(f"cannot read the law version date from the file name: {path.name}")
    return m.group(1)


def differences(stored: dict, fresh: dict) -> list[str]:
    """Names of the facts (and top-level fields) that differ. Empty list = identical."""
    diff = [k for k in ("instrument", "law_version_date", "text_file", "text_sha256") if stored.get(k) != fresh.get(k)]
    stored_facts, fresh_facts = (stored.get("facts") or {}), (fresh.get("facts") or {})
    keys = set(stored_facts) | set(fresh_facts)
    diff += [f"facts.{k}" for k in sorted(keys) if stored_facts.get(k) != fresh_facts.get(k)]
    return diff


def build(text_path: Path) -> dict:
    text = text_path.read_text(encoding="utf-8")
    try:
        rel = text_path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        rel = text_path.name
    return extract(text, rel, version_date_of(text_path))


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("--write", action="store_true", help="regenerate and write the JSON")
    ap.add_argument("--check", action="store_true", help="compare the repo text with the stored JSON (default)")
    ap.add_argument("--text", type=Path, help="a newly saved law text: print what changed against the stored JSON")
    args = ap.parse_args(argv)

    try:
        fresh = build(args.text or DEFAULT_TEXT)
    except (AnchorError, OSError) as exc:
        print(f"FAIL: {exc}")
        return 2
    if args.write and not args.text:
        FACTS_PATH.write_text(json.dumps(fresh, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {FACTS_PATH.relative_to(REPO_ROOT)}: {len(fresh['facts'])} facts, text sha256 {fresh['text_sha256'][:12]}")
        return 0
    stored = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    diff = differences(stored, fresh)
    if args.text:
        print(f"{len(diff)} difference(s) between the stored facts and {args.text.name}")
    for d in diff:
        print("  differs:", d)
    if not args.text:
        print("law facts match the saved text" if not diff else f"FAIL: {len(diff)} fact(s) disagree with the saved text")
    return 1 if diff and not args.text else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
