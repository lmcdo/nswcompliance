"""Site evidence statement, step 1: the data behind a printable page for one lot.

Pure shaping, no new regulatory figure and no new source. Every clause wording and page comes from the saved law
(data/law/housing_sepp_lmr_facts.json via lmr_area_decision.LawFacts); every result comes from the area check
(lmr_area_inputs.area_check output). The council controls and the council files held are read by the caller
(services/evidence_council.py) and passed in, so this module is testable with fake dicts.

prior-art-checked: no services/evidence_statement.py on main (2026-11-20); report_evidence.py is the satellite-report
evidence log, a different thing; /housing-sepp/area-check returns the rules but not the law wording per paragraph or a
row for every paragraph, which the printed page needs.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Optional

from services import lmr_area_decision as dec

# What each area-check rule looked at, in plain words. Descriptive labels only; no planning figure.
SOURCE_CHECKED = {
    "chapter5": "NSW Planning Portal: Transport Oriented Development Sites Map, with the council list in the law",
    "excluded_councils": "the council the lot is in, against the councils the paragraph names",
    "exclusion_map": "NSW Planning Portal: Low and Mid Rise Housing Exclusion Map",
    "accelerated_tod": "NSW Planning Portal: Accelerated Transport Oriented Development Precinct map",
    "schedule_12_stations": "straight-line distance to the Schedule 12 station entrances",
    "heritage_item": "heritage items mapped on the lot outline, and the State Heritage Register",
    "bush_fire_prone": "NSW bush fire prone land map, checked against the lot outline",
    "coastal": "NSW coastal vulnerability, coastal wetlands and littoral rainforests maps",
    "flood_planning_area": "the council's flood planning map, if the council is named in the paragraph",
    "pmf_georges_river": "Georges River Catchment map, if the council is named in the paragraph",
    "pmf_hawkesbury_nepean": "Hawkesbury-Nepean Catchment map",
    "aircraft_noise": "NSW Planning Portal airport noise contour bands",
    "aircraft_noise_sydney": "Sydney Airport's endorsed 2045 aircraft noise chart",
    "pipeline": "gas pipelines on Geoscience Australia's national map",
}

NOT_CHECKED_SOURCE = "not checked by this tool"
NOT_RUN_SOURCE = "this check was not run for this lot"

# Worst first: a paragraph with several rules (h has two) shows the result that matters most.
_SEVERITY = {"excludes": 4, "unknown": 3, "warn": 2, "clear": 1}

RESULT_WORDS = {
    "excludes": "The lot is excluded under this paragraph",
    "unknown": "Could not be determined",
    "warn": "A possible exclusion was identified; this tool could not determine whether it applies",
    "clear": "No exclusion found",
    "not_checked": "Not checked by this tool",
}


def _para_of(rule: dict) -> Optional[str]:
    """'s164(1)(f1)' -> 'f1'. None for a clause that is not an s164(1) paragraph."""
    clause = rule.get("clause")
    if not isinstance(clause, str) or not clause.startswith("s164(1)(") or not clause.endswith(")"):
        return None
    return clause[len("s164(1)("):-1]


PIPELINE_COVERAGE_PATH = Path(__file__).resolve().parent.parent / "data" / "law" / "pipeline_route_coverage.json"


def pipeline_coverage(path: Path = PIPELINE_COVERAGE_PATH) -> Optional[dict]:
    """Which of the law's named pipelines have no published route we could find, from the saved coverage file, or None when it cannot be read or is malformed.
    None means the page says nothing about coverage; it is never read as 'all pipelines covered'."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    lic = doc.get("licences_with_no_published_route") if isinstance(doc, dict) else None
    named = doc.get("named_in_law") if isinstance(doc, dict) else None
    if not (isinstance(lic, list) and lic and all(isinstance(x, int) and not isinstance(x, bool) and x > 0 for x in lic) and len(set(lic)) == len(lic)
            and isinstance(named, int) and not isinstance(named, bool) and named > 0 and isinstance(doc.get("checked_on"), str)):
        return None
    other = doc.get("other_named_pipeline_with_no_published_route")
    if len(lic) + (1 if isinstance(other, str) and other else 0) > named:   # more pipelines without a route than the law names is a malformed file
        return None
    return {"licences": lic, "other": other if isinstance(other, str) and other else None, "named_in_law": doc.get("named_in_law"),
            "no_route_count": len(lic) + (1 if isinstance(other, str) and other else 0), "checked_on": doc.get("checked_on"), "verified": False}


def _row_facts(para: str, area: dict, rule_figures: dict, facts: dec.LawFacts) -> Optional[dict]:
    """The distances behind a paragraph, for the page: the flood rule's own figures plus the two flood-frequency distances (paragraph f), or the nearest mapped gas
    pipeline and the named gap (paragraph i). Read from what the area check measured; nothing is computed or filled in here."""
    measured = area.get("measured") or {}
    if para == "f":
        out = dict(rule_figures) if isinstance(rule_figures, dict) and rule_figures else {}
        fs = measured.get("flood_study") if isinstance(measured.get("flood_study"), dict) else {}
        for k, label in (("aep500", "nearest_500_year_m"), ("aep100", "nearest_100_year_m")):
            layer = fs.get(k) if isinstance(fs.get(k), dict) else None
            if layer is not None and layer.get("nearest_m") is not None:
                out[label] = layer.get("nearest_m")
        return out or None
    if para == "i":
        pl = measured.get("pipeline") if isinstance(measured.get("pipeline"), dict) else None
        if pl is None:
            return None
        out = {"limit_m": facts.number("s164_i_distance"), "map": "Geoscience Australia national gas pipeline map", "hit": pl.get("hit"), "names": pl.get("names")}
        if "nearest_m" in pl:
            out.update(nearest_m=pl.get("nearest_m"), nearest_name=pl.get("nearest_name"), searched_m=pl.get("searched_m"))
        cov = pipeline_coverage()
        if cov is not None:
            out["gap"] = cov
        return out
    return None


def exclusions(area: dict, facts: dec.LawFacts) -> list[dict]:
    """One row per live paragraph of s164(1), in the law's order. j (repealed) has no row."""
    by_para: dict[str, list[dict]] = {}
    for r in ((area.get("lmr") or {}).get("rules") or []):
        p = _para_of(r)
        if p:
            by_para.setdefault(p, []).append(r)
    not_checked = {n.get("para"): n for n in (area.get("not_checked") or [])}

    rows = []
    for p in (facts.fact("s164").get("paragraphs") or []):
        para = p.get("para")
        if p.get("repealed"):
            continue
        law = facts.paragraph(para)
        rules = by_para.get(para) or []
        row: dict[str, Any] = {"para": para, "clause": law["clause"], "page": law["page"], "law_words": law["words"],  # noqa: bracket-access -- paragraph() builds these keys itself
                               "law_version_date": law["law_version_date"]}  # noqa: bracket-access -- paragraph() builds these keys itself
        if rules:
            worst = max(rules, key=lambda r: _SEVERITY.get(r.get("outcome"), 0))
            row.update(result=worst.get("outcome"), detail=worst.get("detail"),
                       source_checked="; ".join(dict.fromkeys(SOURCE_CHECKED.get(r.get("rule"), str(r.get("rule"))) for r in rules)))
            nc = not_checked.get(para)
            if nc:  # a rule covers it only in part: say what it could not see
                row["not_seen"] = nc.get("what")
        elif para in not_checked:
            row.update(result="not_checked", detail=not_checked[para].get("what"), source_checked=NOT_CHECKED_SOURCE)  # noqa: bracket-access -- membership tested on the line above
        else:
            row.update(result="not_checked", detail="no check was run for this paragraph", source_checked=NOT_RUN_SOURCE)
        row["result_words"] = RESULT_WORDS.get(row["result"], row["result"])  # noqa: bracket-access -- set by the branches above
        extra = _row_facts(para, area, (worst.get("figures") if rules else None) or {}, facts)
        if extra:
            row["facts"] = extra
        rows.append(row)
    return rows


def walk(area: dict) -> dict:
    """The walking range as the area check measured it. Missing parts stay None; nothing is filled in.

    The margins say why the walk is a range. The crossings-only walk (and its next-to-a-busy-road note) sits beside the normal
    walk; it never changes the answer. It is absent when an exclusion decided the answer before any walk was measured."""
    lmr = area.get("lmr") or {}
    f = lmr.get("figures") or {}

    def fig(key: str) -> Any:
        """From figures; the answer 'no' keeps only five figures there, so fall back to the same key on the result itself."""
        return f.get(key) if f.get(key) is not None else lmr.get(key)

    return {"answer": lmr.get("answer"), "clause": lmr.get("clause"), "page": lmr.get("page"),
            "anchor": f.get("anchor"), "straight_m": f.get("straight_m"), "limit_m": f.get("limit_m"),
            "walk_low_m": f.get("walk_low_m"), "walk_best_m": fig("walk_best_m"), "walk_high_m": f.get("walk_high_m"),
            "margin_low_m": fig("margin_low_m"), "margin_high_m": fig("margin_high_m"),
            "entrance_unmapped_extra_m": fig("entrance_unmapped_extra_m"),
            "share_of_range_inside": lmr.get("share_of_range_inside"), "detail": lmr.get("detail"),
            "heuristic": lmr.get("heuristic"),
            "crossings_only_walk_m": lmr.get("crossings_only_walk_m"), "crossings_only_note": lmr.get("crossings_only_note")}


# Short forms of RESULT_WORDS for the one-line count at the top of the page. Order = how the line reads.
SUMMARY_WORDS = (
    ("excludes", "excluded"),
    ("warn", "possible exclusion, not determined"),
    ("unknown", "could not be determined"),
    ("not_checked", "not checked by this tool"),
    ("clear", "no exclusion found"),
)


def summary(rows: list[dict]) -> dict:
    """A count of the exclusion rows by result, and the one line the page prints from it. An unrecognised result is counted
    as 'unknown' so the counts always add up to the number of rows."""
    known = {k for k, _ in SUMMARY_WORDS}
    counts = {k: 0 for k, _ in SUMMARY_WORDS}
    for r in rows:
        res = r.get("result")
        counts[res if res in known else "unknown"] += 1
    parts = [f"{counts[k]} {words}" for k, words in SUMMARY_WORDS if counts[k]]
    n = len(rows)
    line = f"{n} paragraphs of section 164(1): " + "; ".join(parts) + "." if n and parts else ""
    return {"total": n, "counts": counts, "line": line}


# A paragraph needs no hand check when the tool found no exclusion or found an exclusion. Everything else, including a result word
# this module does not know yet, needs a person, so the list matches the 'could not be determined' count in summary().
_NO_HAND_CHECK = ("clear", "excludes")


def manual_checks(rows: list[dict]) -> list[dict]:
    """The paragraphs this tool did not clear, so a person has to look: could not be determined, possible exclusion,
    not checked, or any result this module does not recognise. Taken from the rows, so the list cannot drift from the table."""
    return [{"clause": r.get("clause"), "page": r.get("page"), "law_words": r.get("law_words"),
             "result_words": r.get("result_words"), "detail": r.get("detail"), "not_seen": r.get("not_seen")}
            for r in rows if r.get("result") not in _NO_HAND_CHECK]


REPO_ROOT = Path(__file__).resolve().parent.parent
ROAD_RULES_PATH = REPO_ROOT / "data" / "law" / "road_rules_2014_pedestrian_facts.json"


def road_rules(facts_path: Path = ROAD_RULES_PATH, repo: Path = REPO_ROOT) -> dict:
    """The NSW Road Rules 2014 wording shown beside the crossings-only walk, word for word from the saved text.

    Nothing is paraphrased here. The quotes are cut from data/law/road-rules-2014-regs-231-232-234-copied-2026-11-20.txt; this refuses
    to serve any quote that is not found word for word in that file, or a file whose fingerprint has changed, and says
    'unreadable' instead of showing something that may differ from the law. A quote must also sit inside the subrule its clause names
    (for example 'reg 234(4)'), and its source address must be the page for that regulation, so wording or a citation for another
    regulation or subrule cannot be shown under the wrong clause."""
    try:
        doc = json.loads(Path(facts_path).read_text(encoding="utf-8"))
        stored = doc.get("facts") if isinstance(doc, dict) else None
        if not isinstance(doc, dict) or not isinstance(stored, dict):
            return {"status": "unreadable", "reason": "the road-rules file is not in the expected form"}
        text = (Path(repo) / str(doc.get("text_file"))).read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != doc.get("text_sha256"):
            return {"status": "unreadable", "reason": "the saved road-rules text does not match its fingerprint"}
        # The saved text is one section per regulation, each opened by a '==== REG nnn ====' line.
        sections = dict(re.findall(r"==== REG (\d+) ====\n(.*?)(?=\n==== REG |\Z)", text, re.S))
        rules = []
        for key, f in stored.items():
            if not isinstance(f, dict):
                return {"status": "unreadable", "reason": f"road rule {key} is incomplete"}
            quote, clause, url = f.get("quote"), f.get("clause"), f.get("source_url")
            if not (isinstance(quote, str) and quote and isinstance(clause, str) and isinstance(url, str)):
                return {"status": "unreadable", "reason": f"road rule {key} is incomplete"}
            reg = re.fullmatch(r"reg (\d+)\((\d+[A-Z]?)\)", clause)
            if not reg:
                return {"status": "unreadable", "reason": f"the clause '{clause}' is not in the form 'reg 234(1)'"}
            # Subrules are the lines that open with a number in brackets, such as (1) or (3A); sub-paragraphs (a), (b) belong to the subrule above them.
            subrules = {m.group(1): m.group(0) for m in re.finditer(r"^\((\d+[A-Z]?)\) .*?(?=^\(\d+[A-Z]?\) |\Z)", sections.get(reg.group(1), ""), re.M | re.S)}
            if quote not in subrules.get(reg.group(2), ""):
                return {"status": "unreadable", "reason": f"the quote for {clause} is not found word for word in that subrule of the saved text"}
            if not url.endswith(f"/s{reg.group(1)}.html"):
                return {"status": "unreadable", "reason": f"the source address for {clause} is not the page for regulation {reg.group(1)}"}
            rules.append({"clause": clause, "heading": f.get("heading"), "quote": quote, "source_url": url})
        if not rules:
            return {"status": "unreadable", "reason": "no road rules are stored"}
        return {"status": "ok", "instrument": doc.get("instrument"), "copied_on": doc.get("copied_on"), "note": doc.get("note"), "rules": rules}
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        return {"status": "unreadable", "reason": f"the road-rules file could not be read: {exc}"}


def build(area: dict, controls: dict, files: dict, facts: Optional[dec.LawFacts] = None) -> dict:
    """The evidence structure. `controls` and `files` are read by the caller; each carries its own 'status' so an unreadable
    source is shown as unreadable, never as empty."""
    facts = facts or dec.LawFacts.load()
    rows = exclusions(area, facts)
    return {
        "road_rules": road_rules(),
        "law_version_date": area.get("law_version_date") or facts.version_date,
        "headline": area.get("headline"),
        "pathway": area.get("pathway"),
        "lga": (area.get("measured") or {}).get("lga"),
        "exclusions": rows,
        "summary": summary(rows),
        "manual_checks": manual_checks(rows),
        "walk": walk(area),
        "route_map": area.get("route_map"),   # built by lmr_route_map when the evidence endpoint asked for it; None otherwise (never invented here)
        "notes": area.get("notes") or [],
        "council_controls": controls,
        "council_files": files,
    }
