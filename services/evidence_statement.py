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
    "warn": "Possible exclusion, not confirmed",
    "clear": "No exclusion found",
    "not_checked": "Not checked by this tool",
}


def _para_of(rule: dict) -> Optional[str]:
    """'s164(1)(f1)' -> 'f1'. None for a clause that is not an s164(1) paragraph."""
    clause = rule.get("clause")
    if not isinstance(clause, str) or not clause.startswith("s164(1)(") or not clause.endswith(")"):
        return None
    return clause[len("s164(1)("):-1]


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
        rows.append(row)
    return rows


def walk(area: dict) -> dict:
    """The walking range as the area check measured it. Missing parts stay None; nothing is filled in."""
    lmr = area.get("lmr") or {}
    f = lmr.get("figures") or {}
    return {"answer": lmr.get("answer"), "clause": lmr.get("clause"), "page": lmr.get("page"),
            "anchor": f.get("anchor"), "straight_m": f.get("straight_m"), "limit_m": f.get("limit_m"),
            "walk_low_m": f.get("walk_low_m"), "walk_best_m": f.get("walk_best_m"), "walk_high_m": f.get("walk_high_m"),
            "share_of_range_inside": lmr.get("share_of_range_inside"), "detail": lmr.get("detail"),
            "heuristic": lmr.get("heuristic") or dec.WALK_HEURISTIC}


def build(area: dict, controls: dict, files: dict, facts: Optional[dec.LawFacts] = None) -> dict:
    """The evidence structure. `controls` and `files` are read by the caller; each carries its own 'status' so an unreadable
    source is shown as unreadable, never as empty."""
    facts = facts or dec.LawFacts.load()
    return {
        "law_version_date": area.get("law_version_date") or facts.version_date,
        "headline": area.get("headline"),
        "pathway": area.get("pathway"),
        "lga": (area.get("measured") or {}).get("lga"),
        "exclusions": exclusions(area, facts),
        "walk": walk(area),
        "notes": area.get("notes") or [],
        "council_controls": controls,
        "council_files": files,
    }
