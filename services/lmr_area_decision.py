# prior-art-checked: four sweeps 2026-11-07 on feat/lmr-clean-law (origin/main eaa9964d). (1) DB: reads no
# database (law facts come from data/law/housing_sepp_lmr_facts.json, which scripts/load_law_facts.py
# proves equal to the law_facts table). (2) Frontend: no surface decides the area from a lot outline; the
# gates route returns point answers only. (3) Python: services/housing_sepp_gates_api.lmr_gates (point,
# straight 800 m circle, folds TOD into the area answer -- the errors this module replaces),
# services/housing_sepp_eligibility._gate_inputs (folds a failed query into False). (4) Plans:
# ce-eligible-homes-GATE-FIX-DESIGN-2026-11-07.md and ce-NEXT-PROMPT-2026-11-07b-lmr-area-check-build.md.
"""Low and mid-rise housing area + Transport Oriented Development: the decision rules, and nothing else.

PURE FUNCTION. No network, no database. Every fact about the lot is passed in as a measurement; every
figure and clause comes from the saved law (data/law/housing_sepp_lmr_facts.json). The inputs module
(services/lmr_area_inputs.py) makes the measurements; this module only decides, so each rule can be
tested with a hand-made lot.

Answers are three-valued: "yes", "no", "cant_tell". Three rules keep the answer from being silently wrong:
  1. A measurement that did not come back is None, never False. None can only ever lead to "cant_tell".
  2. A "no" is final: any rule that excludes the lot gives "no" whatever else did not answer, because an
     exclusion cannot be undone by a missing measurement. A "yes" needs EVERY rule clear and the walk
     clearly under the limit.
  3. Near the walking limit the answer is "cant_tell" with the figure shown. No dataset reproduces the
     law's "route that may be safely walked", so a forced yes or no there would be a guess.

Measurement shapes (all optional; a key that is ABSENT means "not wired", a key that is None means
"asked and it did not answer"):
  layer       {"point": bool|None, "lot": bool|None}   -- address point / lot outline hits the map layer
  tod_map     layer for the TOD Sites Map
  accelerated layer for the Accelerated TOD Precinct map
  exclusion   layer for the Low and Mid Rise Housing Exclusion Map
  heritage    {"item": bool|None, "conservation_area": bool|None, "state_register": bool|None}
              (item / state_register are for the LOT outline; conservation area is a note only)
  bushfire    layer
  lga         str|None                                    -- the lot's council area
  sched12_straight_m   float|None   nearest straight distance, lot outline to a Schedule 12 entrance
  straight_m           float|None   nearest straight distance, lot outline to any anchor
  walk        {"m": float|None, "anchor": str, "entrance_id": str, "valid": bool,
               "margin_factor": float, "reason": str}      -- walking distance from any part of the lot
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
FACTS_PATH = REPO_ROOT / "data" / "law" / "housing_sepp_lmr_facts.json"

YES, NO, CANT, BORDER = "yes", "no", "cant_tell", "borderline"
# yes / no: the whole walking range is on one side of the limit. borderline: the range straddles the limit; the answer then
# SHOWS the range and which way the best estimate leans. cant_tell is kept only for a measurement that did not come back.

# Engineering tolerance, NOT a planning figure: two independent walking routers disagreed by a median
# of 38 m (p90 150 m, max 214 m) on the 48 lots of the 2026-11-06 test; at this margin the simulated rule
# made 0 wrong-side answers and left 5 of 48 undecided (ce-eligible-homes-GATE-FIX-DESIGN-2026-11-07 s4).
# Re-measure when the test sample changes.
#
# 2026-11-07 re-measurement, three sets of 100 lots (248 lots with both walks; 64 stations and town centres, 20+ councils; judge =
# OpenStreetMap Valhalla pedestrian service): the judge's walk minus ours had median +29 m, 2.5th percentile -62 m, 95th percentile
# +204 m, 97.5th percentile +231 m. Our walk is usually the shorter one, because our footpath map allows every mapped path while the
# judge follows its own rules for crossings and access. A range of the same size on both sides covered only 88% (150 m each way);
# 75 m below and 225 m above covers about 94% with a smaller total width. The first 150 m margin was set on one sample and covered
# only 86% of two fresh samples, so these two numbers are set on all three samples and must be checked on lots drawn with new seeds.
WALK_MARGIN_LOW_M = 75    # noqa: regulatory-number -- measured router disagreement, not a planning figure
WALK_MARGIN_HIGH_M = 225  # noqa: regulatory-number -- measured router disagreement, not a planning figure


# What a reader is told when a check could not be completed. The machine value stays "cant_tell"; the words a person sees never are.
NOT_DETERMINED_NEXT_STEP = ". Check this lot on the NSW Planning Portal Spatial Viewer or ask the council for a planning certificate."


WALK_HEURISTIC = (
    f"How the range is worked out: we measure the walk along public footpaths, then allow {WALK_MARGIN_LOW_M} m shorter and {WALK_MARGIN_HIGH_M} m longer. "
    "The allowance is bigger on the longer side because, on test lots, our footpath map gave a shorter walk than a second walking-route "
    "service more often than a longer one. If the station entrance is not mapped, the length of the station outline is added. "
    "The law's route is the shortest one that may be walked using footpaths and crossings. When the limit falls inside the range, "
    "every walk length in the range is treated as equally likely, and the share shown is the part of the range under the limit."
)


class LawFactsError(Exception):
    """The saved law facts are missing, unreadable or lack a fact this module needs."""


class LawFacts:
    """Read-only view of the saved law facts. Every number, name and clause is read, never typed here."""

    def __init__(self, doc: dict):
        try:
            self.version_date: str = doc["law_version_date"]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
            self._facts: dict = doc["facts"]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        except (KeyError, TypeError) as exc:
            raise LawFactsError(f"facts document malformed: {exc}") from exc

    @classmethod
    def load(cls, path: Path = FACTS_PATH) -> "LawFacts":
        try:
            return cls(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            raise LawFactsError(f"cannot read {path}: {exc}") from exc

    def fact(self, key: str) -> dict:
        f = self._facts.get(key)
        if not isinstance(f, dict):
            raise LawFactsError(f"law fact missing: {key}")
        return f

    def number(self, key: str) -> float:
        v = self.fact(key).get("value")
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise LawFactsError(f"law fact {key} has no numeric value")
        return float(v)  # qa-ignore: v is type-checked (int or float, not bool) three lines above

    def names(self, key: str) -> list[str]:
        v = self.fact(key).get("value")
        if not isinstance(v, list) or not v:
            raise LawFactsError(f"law fact {key} has no list value")
        return [str(x) for x in v]

    def cite(self, key: str) -> dict:
        f = self.fact(key)
        return {"clause": f.get("clause"), "page": f.get("page"), "law_version_date": self.version_date}

    def noise_thresholds(self) -> tuple[float, float]:
        """(ANEF level, ANEC level) at or above which s164(1)(h) excludes land, read from the saved law."""
        return self.number("s164_h_anef_min"), self.number("s164_h_anec_min")

    def council_names(self, para: str, style: str = "roman") -> list[str]:
        """The councils a paragraph of s164(1) names, read from its saved wording.

        style "roman" is (i) (ii) ...; style "letter" is (A) (B) ... (used by (f1), whose first two items are not councils).
        An empty list is an error, never "no councils".
        """
        pattern = r"\((?:[ivx]+)\)\s*([^,(.]+?)\s*(?:,|\.|$)" if style == "roman" else r"\((?:[A-Z])\)\s*([^,(.]+?)\s*(?:,|\.|$)"
        names = [n.strip() for n in re.findall(pattern, self.paragraph(para)["words"])]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        if not names:
            raise LawFactsError(f"s164(1)({para}) council list could not be read from the saved law")
        return names

    def paragraph(self, para: str) -> dict:
        for p in (self.fact("s164").get("paragraphs") or []):
            if p.get("para") == para:
                if p.get("repealed"):
                    raise LawFactsError(f"s164(1)({para}) is repealed in this version")
                return {"clause": p["clause"], "page": p["page"], "words": p["words"],  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
                        "law_version_date": self.version_date}
        raise LawFactsError(f"s164(1)({para}) not in the saved law")


def norm_lga(name: Optional[str]) -> Optional[str]:
    """Council name -> comparison key. 'CITY OF BLUE MOUNTAINS', 'Blue Mountains' and 'blue mountains council' match."""
    if not isinstance(name, str) or not name.strip():
        return None
    s = name.lower().replace("&", " and ")
    s = re.sub(r"\b(city of|municipality of|shire of|council|city|shire|regional council)\b", " ", s)
    s = re.sub(r"[^a-z]+", " ", s).strip()
    return s or None


def _in_names(lga: str, names: list[str]) -> bool:
    keys = {norm_lga(n) for n in names}
    return norm_lga(lga) in keys


def _bool(v: Any) -> Optional[bool]:
    return v if isinstance(v, bool) else None


def layer_state(layer: Any) -> str:
    """'hit' (point is in it), 'part' (lot overlaps, point is not in it), 'clear', or 'unknown'."""
    if not isinstance(layer, dict):
        return "unknown"
    pt, lot = _bool(layer.get("point")), _bool(layer.get("lot"))
    if pt is True:
        return "hit"
    if lot is True:
        return "part"
    if lot is False and pt is not True:
        return "clear"
    if lot is None and pt is False:
        return "unknown"  # point clear, lot outline missing: a part of the lot could still be in it
    return "unknown"


def _rule(code: str, clause: dict, outcome: str, detail: str, **figures: Any) -> dict:
    """outcome: 'excludes' | 'clear' | 'unknown'."""
    return {"rule": code, "outcome": outcome, "detail": detail, **clause, "figures": figures}


def _tod_chapter5(m: dict, facts: LawFacts) -> dict:
    """Does Chapter 5 apply? s152(1) map + council list; s152(2) whole lot if any part; s152(4) heritage carve-out."""
    cite = facts.cite("tod_lgas")
    lga = m.get("lga")
    tod = layer_state(m.get("tod_map")) if "tod_map" in m else "unknown"
    heritage_item = _bool((m.get("heritage") or {}).get("item"))
    if tod == "unknown":
        return _rule("chapter5", cite, "unknown", "the TOD Sites Map did not answer for this lot")
    if tod == "clear":
        return _rule("chapter5", cite, "clear", "lot outline is not on the TOD Sites Map")
    if not isinstance(lga, str) or not norm_lga(lga):
        return _rule("chapter5", cite, "unknown", "on the TOD Sites Map but the council area did not answer",
                     lga=None)
    if not _in_names(lga, facts.names("tod_lgas")):
        return _rule("chapter5", cite, "clear", f"on the TOD Sites Map but {lga} is not one of the councils in s152(1)",
                     lga=lga)
    if tod == "part":
        # s152(2) extends Chapter 5 to a lot when part of it is in; s152(4) switches that extension off for a heritage-item lot.
        if heritage_item is True:
            return _rule("chapter5", cite, "unknown",
                         "only part of the lot is on the TOD Sites Map and a heritage item is on it (s152(4) removes the whole-lot rule)",
                         lga=lga)
        if heritage_item is None:
            return _rule("chapter5", cite, "unknown",
                         "only part of the lot is on the TOD Sites Map and the heritage-item check did not answer", lga=lga)
        return _rule("chapter5", cite, "excludes", "part of the lot is on the TOD Sites Map; s152(2) applies Chapter 5 to the whole lot",
                     lga=lga, whole_lot_rule=True)
    return _rule("chapter5", cite, "excludes", "address point is on the TOD Sites Map", lga=lga)


def _lmr_rules(m: dict, facts: LawFacts) -> list[dict]:
    rules: list[dict] = []
    # (c) Chapter 5 land is not low and mid-rise land.
    c5 = _tod_chapter5(m, facts)
    c5.update({k: v for k, v in facts.paragraph("c").items() if k in ("clause", "page")})
    rules.append(c5)

    # (e) four councils excluded by name.
    p = facts.paragraph("e")
    lga = m.get("lga")
    excluded_lgas = re.findall(r"\(([ivx]+)\)\s*([^,(]+?)\s*(?:,|$)", p["words"])  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    names = [n.strip() for _, n in excluded_lgas]
    if not names:
        raise LawFactsError("s164(1)(e) council list could not be read from the saved law")
    if not isinstance(lga, str) or not norm_lga(lga):
        rules.append(_rule("excluded_councils", p, "unknown", "council area did not answer"))
    elif _in_names(lga, names):
        rules.append(_rule("excluded_councils", p, "excludes", f"{lga} is named in s164(1)(e)", lga=lga))
    else:
        rules.append(_rule("excluded_councils", p, "clear", f"{lga} is not named in s164(1)(e)", lga=lga))

    # (m) exclusion map, (l) accelerated precinct map.
    for code, para, key, label in (("exclusion_map", "m", "exclusion", "Low and Mid Rise Housing Exclusion Map"),
                                   ("accelerated_tod", "l", "accelerated", "Accelerated TOD Precinct map")):
        cl = facts.paragraph(para)
        st = layer_state(m.get(key)) if key in m else "unknown"
        if st == "hit":
            rules.append(_rule(code, cl, "excludes", f"address point is on the {label}"))
        elif st == "part":
            rules.append(_rule(code, cl, "unknown", f"part of the lot is on the {label}; the text does not say how a part-covered lot is treated"))
        elif st == "clear":
            rules.append(_rule(code, cl, "clear", f"lot outline is not on the {label}"))
        else:
            rules.append(_rule(code, cl, "unknown", f"the {label} did not answer"))

    # (k) Schedule 12 stations: 800 m, the paragraph does not say walking.
    pk = facts.paragraph("k")
    lim_k = facts.number("s164_k_distance")
    d12 = m.get("sched12_straight_m")
    if not isinstance(d12, (int, float)) or isinstance(d12, bool):
        rules.append(_rule("schedule_12_stations", pk, "unknown", "distance to the Schedule 12 stations did not answer"))
    elif d12 > lim_k:
        rules.append(_rule("schedule_12_stations", pk, "clear", "beyond the straight-line limit from every Schedule 12 entrance",
                           straight_m=round(d12), limit_m=lim_k))
    else:
        rules.append(_rule("schedule_12_stations", pk, "unknown",
                           "inside the straight-line distance of a Schedule 12 station; the paragraph states no method so a walk was not substituted",
                           straight_m=round(d12), limit_m=lim_k))

    # (d) heritage item on the lot outline. A conservation area is NOT an exclusion (note only).
    pd_ = facts.paragraph("d")
    h = m.get("heritage") if isinstance(m.get("heritage"), dict) else None
    item = _bool(h.get("item")) if h else None
    wired_reg = bool(h) and "state_register" in h
    reg = _bool(h.get("state_register")) if h else None
    if item is True:
        rules.append(_rule("heritage_item", pd_, "excludes", "a heritage item is mapped on the lot outline"))
    elif item is None:
        rules.append(_rule("heritage_item", pd_, "unknown", "the heritage-item check did not answer"))
    elif wired_reg and reg is not False:
        why = ("the State Heritage Register did not answer" if reg is None else
               "the lot is on the State Heritage Register; whether that makes it a 'heritage item' in s164(1)(d) was not decided from the text")
        rules.append(_rule("heritage_item", pd_, "unknown", why))
    else:
        rules.append(_rule("heritage_item", pd_, "clear", "no heritage item mapped on the lot outline"))

    # (a) bush fire prone land, only if the caller wired it.
    if "bushfire" in m:
        pa = facts.paragraph("a")
        st = layer_state(m.get("bushfire"))
        if st == "hit":
            rules.append(_rule("bush_fire_prone", pa, "excludes", "address point is on bush fire prone land"))
        elif st == "part":
            rules.append(_rule("bush_fire_prone", pa, "unknown", "part of the lot is bush fire prone; the text does not say how a part-covered lot is treated"))
        elif st == "clear":
            rules.append(_rule("bush_fire_prone", pa, "clear", "lot outline is not on bush fire prone land"))
        else:
            rules.append(_rule("bush_fire_prone", pa, "unknown", "the bush fire prone land map did not answer"))

    # (b) coastal vulnerability area, or coastal wetlands and littoral rainforests area: three maps, only if all three were wired.
    coastal_keys = ("coastal_vuln", "coastal_wetlands", "littoral")
    if all(k in m for k in coastal_keys):
        pb = facts.paragraph("b")
        states = [layer_state(m.get(k)) for k in coastal_keys]
        if "hit" in states:
            rules.append(_rule("coastal", pb, "excludes", "address point is on one of the coastal maps named in (b)"))
        elif "part" in states or "unknown" in states:
            why = "part of the lot is on a coastal map named in (b)" if "part" in states else "a coastal map named in (b) did not answer"
            rules.append(_rule("coastal", pb, "unknown", why))
        else:
            rules.append(_rule("coastal", pb, "clear", "lot outline is on none of the three coastal maps named in (b)"))

    # (g) flood planning areas, but only in the 23 councils the paragraph names. Everywhere else it cannot apply.
    pg = facts.paragraph("g")
    g_names = facts.council_names("g", "roman")
    if not isinstance(lga, str) or not norm_lga(lga):
        rules.append(_rule("flood_planning_area", pg, "unknown", "council area did not answer"))
    elif not _in_names(lga, g_names):
        rules.append(_rule("flood_planning_area", pg, "clear", f"{lga} is not one of the {len(g_names)} councils named in (g)", lga=lga))
    else:
        # A named council and no flood answer supplied is NOT a yes: flood planning areas are exactly what (g) excludes there.
        fv = _bool((m.get("flood_planning") or {}).get("value")) if isinstance(m.get("flood_planning"), dict) else None
        if fv is True:
            rules.append(_rule("flood_planning_area", pg, "excludes", "the lot is on the council's flood planning map", lga=lga))
        elif fv is False:
            rules.append(_rule("flood_planning_area", pg, "clear", "the lot is not on the council's flood planning map", lga=lga))
        else:
            rules.append(_rule("flood_planning_area", pg, "unknown",
                               "the council's flood planning map is not held, did not answer, or was not supplied", lga=lga))

    # (f1) Georges River catchment Probable Maximum Flood, and only in the 6 councils named. We do not hold the flood map itself:
    # outside the catchment or the councils the paragraph cannot apply; inside both, the lot gets a specific warning, not a block.
    pf1 = facts.paragraph("f1")
    f1_names = facts.council_names("f1", "letter")
    if not isinstance(lga, str) or not norm_lga(lga):
        rules.append(_rule("pmf_georges_river", pf1, "unknown", "council area did not answer"))
    elif not _in_names(lga, f1_names):
        rules.append(_rule("pmf_georges_river", pf1, "clear", f"{lga} is not one of the {len(f1_names)} councils named in (f1)", lga=lga))
    elif "georges_catchment" in m:
        st = layer_state(m.get("georges_catchment"))
        if st == "clear":
            rules.append(_rule("pmf_georges_river", pf1, "clear", "the lot is outside the Georges River Catchment", lga=lga))
        elif st in ("hit", "part"):
            rules.append(_rule("pmf_georges_river", pf1, "warn",
                               "the lot is in the Georges River Catchment and a named council: land that floods in the Probable Maximum Flood "
                               "is excluded, and the flood extent was not checked", lga=lga))
        else:
            rules.append(_rule("pmf_georges_river", pf1, "unknown", "the Georges River Catchment map did not answer"))

    # (f) Hawkesbury-Nepean Probable Maximum Flood. The paragraph names a flood-study figure, not a catchment; the study area lies inside
    # the river's catchment, so a lot outside the catchment cannot be on it. That inference is ours, and it is printed with the answer.
    if "hn_catchment" in m:
        pf = facts.paragraph("f")
        st = layer_state(m.get("hn_catchment"))
        if st == "clear":
            rules.append(_rule("pmf_hawkesbury_nepean", pf, "clear",
                               "the lot is outside the Hawkesbury-Nepean Catchment (our inference: the flood study area lies inside the catchment)"))
        elif st in ("hit", "part"):
            rules.append(_rule("pmf_hawkesbury_nepean", pf, "warn",
                               "the lot is in the Hawkesbury-Nepean Catchment: land on the Probable Maximum Flood map in the study is excluded, "
                               "and the flood extent was not checked"))
        else:
            rules.append(_rule("pmf_hawkesbury_nepean", pf, "unknown", "the Hawkesbury-Nepean Catchment map did not answer"))

    # (h) aircraft noise, from the contour bands NSW publishes on the planning portal (Western Sydney Airport and a few council areas). A band whose
    # lower level is at or above the law's level excludes; the law's level for an ANEC (concept) map differs from its level for an ANEF map.
    if "airport_noise" in m:
        ph = facts.paragraph("h")
        anef_min, anec_min = facts.noise_thresholds()
        bands = m.get("airport_noise")
        if not isinstance(bands, list):
            rules.append(_rule("aircraft_noise", ph, "unknown", "the planning portal's airport noise map did not answer"))
        else:
            verdict, why = "clear", "the lot is on none of the airport noise contour bands this map holds"
            for b in bands:
                code, name = str((b or {}).get("code") or ""), str((b or {}).get("name") or "")
                low = re.match(r"^\s*(\d+)", code)
                level = anec_min if "concept" in name.lower() else anef_min
                kind = "ANEC" if "concept" in name.lower() else "ANEF"
                if not low:
                    verdict, why = "unknown", f"the lot is on a noise band called '{code}', which cannot be compared with the law's {kind} level"
                    continue
                if int(low.group(1)) >= level:
                    verdict, why = "excludes", f"the lot is on the {kind} {code} band; the law excludes {kind} {level:g} or greater"
                    break
            rules.append(_rule("aircraft_noise", ph, verdict, why))

    # (i) pipelines within the law's distance. Only gas pipelines on Geoscience Australia's national map are held, and whether one is a "relevant
    # pipeline" named in section 2.77(3) of the Transport and Infrastructure SEPP was not checked, so a hit is a warning and a miss clears nothing.
    pl = m.get("pipeline")
    if isinstance(pl, dict) and pl.get("hit") is True:
        pi = facts.paragraph("i")
        rules.append(_rule("pipeline", pi, "warn",
                           f"a gas pipeline on Geoscience Australia's national map is within {facts.number('s164_i_distance'):g} m of the lot; whether it is one of the "
                           "relevant pipelines the law means (section 2.77(3) of the Transport and Infrastructure SEPP) was not checked"))
    return rules


def _distance_step(m: dict, facts: LawFacts) -> tuple[str, dict]:
    """Returns (answer, detail) for the distance test alone: yes / no / cant_tell."""
    outer, inner = facts.number("lmr_outer_distance"), facts.number("lmr_inner_distance")
    cite = facts.cite("lmr_outer_distance")
    straight = m.get("straight_m")
    walk = m.get("walk") if isinstance(m.get("walk"), dict) else {}
    base = {**cite, "limit_m": outer, "straight_m": None if straight is None else round(straight)}
    if not isinstance(straight, (int, float)) or isinstance(straight, bool) or straight < 0:
        return CANT, {**base, "reason_code": "no_straight_distance", "detail": "the distance to the nearest station or town centre did not come back"}
    if straight > outer:
        # A walk can never be shorter than the straight line, so this "no" does not depend on the walking measure.
        return NO, {**base, "reason_code": "beyond_straight_line", "detail": "the straight line to the nearest station or town centre is longer than the walking limit"}
    wm = walk.get("m")
    if walk.get("valid") is not True or not isinstance(wm, (int, float)) or isinstance(wm, bool):
        return CANT, {**base, "reason_code": "walking_measure_unavailable",
                      "detail": walk.get("reason") or "no valid walking measure for this lot"}
    # The walk is a RANGE, not a point. Low end: the measured walk less the measurement margin. High end: the measured walk plus
    # the margin, plus `optimistic_by_m` when the walk was measured to a station building outline instead of a mapped entrance
    # (the entrance is somewhere on that outline, so the real walk can be longer by up to the outline's length).
    opt = walk.get("optimistic_by_m") or 0
    opt = float(opt) if isinstance(opt, (int, float)) and not isinstance(opt, bool) and opt >= 0 else 0.0  # qa-ignore: opt is type-checked on this same line
    lo_m, hi_m = max(0.0, wm - WALK_MARGIN_LOW_M), wm + opt + WALK_MARGIN_HIGH_M
    best = wm + opt / 2
    base.update({"walk_m": round(wm), "walk_low_m": round(lo_m), "walk_high_m": round(hi_m), "walk_best_m": round(best),
                 "margin_low_m": WALK_MARGIN_LOW_M, "margin_high_m": WALK_MARGIN_HIGH_M, "entrance_unmapped_extra_m": round(opt),
                 "anchor": walk.get("anchor"), "entrance_id": walk.get("entrance_id")})
    if hi_m <= outer:
        band = "inner" if hi_m <= inner else ("outer" if lo_m >= inner else "straddles_inner_limit")
        return YES, {**base, "reason_code": "walk_range_under_limit", "band": band, "inner_limit_m": inner,
                     "detail": f"walking range {round(lo_m)}-{round(hi_m)} m is under the {round(outer)} m limit"}
    if lo_m >= outer:
        return NO, {**base, "reason_code": "walk_range_over_limit",
                    "detail": f"walking range {round(lo_m)}-{round(hi_m)} m is over the {round(outer)} m limit"}
    # Transparent heuristic: treat the true walk as equally likely anywhere in [lo, hi]; the share of that range under the
    # limit is the lean. It is an assumption, stated on every borderline answer so a reader can judge it.
    p_inside = (outer - lo_m) / (hi_m - lo_m) if hi_m > lo_m else 0.5
    lean = "inside" if p_inside >= 0.5 else "outside"
    return BORDER, {**base, "reason_code": "walk_range_straddles_limit", "lean": lean, "share_of_range_inside": round(p_inside, 2),
                    "heuristic": WALK_HEURISTIC,
                    "detail": f"the walk is probably between {round(lo_m)} and {round(hi_m)} m, and the limit is {round(outer)} m. "
                              f"About {round(100 * p_inside)}% of that range is under the limit, so it is "
                              f"{'more likely within the limit than not' if p_inside >= 0.5 else 'more likely over the limit than not'}"}


# Every live exclusion that is not a rule above is printed as "not checked". A paragraph is "handled" when a rule above covers it
# (the rule's clause is s164(1)(<para>)); h and i have no rule yet, so they are always printed.
PARTLY_CHECKED = {   # paragraphs a rule covers only in part: still printed, with what the rule could not see
    "h": "aircraft noise outside the contours the planning portal holds (Sydney Airport's own ANEF and other airports are not held)",
    "i": "pipelines other than the gas pipelines on Geoscience Australia's national map, and whether a mapped pipeline is a relevant pipeline",
}
EXCLUSION_LABELS = {
    "a": "bush fire prone land",
    "b": "coastal vulnerability area, coastal wetlands and littoral rainforests area",
    "f": "Probable Maximum Flood, Hawkesbury-Nepean",
    "f1": "Probable Maximum Flood, Georges River catchment (6 councils)",
    "g": "flood planning areas in the 23 councils the paragraph names",
    "h": "ANEF 25 / ANEC 20 aircraft noise contour",
    "i": "land within 200 m of a relevant pipeline",
}


def decide(m: dict, facts: Optional[LawFacts] = None) -> dict:
    """The area answer for one lot. Never raises: a failure is reported as cant_tell with the reason."""
    try:
        facts = facts or LawFacts.load()
        return _decide(m or {}, facts)
    except LawFactsError as exc:
        return _failed(f"law facts unavailable: {exc}")
    except Exception as exc:  # noqa: BLE001 -- the contract is never-raise, never-silent
        return _failed(f"unexpected failure: {type(exc).__name__}: {exc}")


def _failed(reason: str) -> dict:
    return {"pathway": "unknown", "headline": "Not determined: " + reason + NOT_DETERMINED_NEXT_STEP,
            "lmr": {"answer": CANT, "reason_code": "safety_check_failed", "detail": reason, "rules": []},
            "tod": {"answer": CANT, "reason_code": "safety_check_failed", "detail": reason},
            "not_checked": [], "notes": [], "law_version_date": None, "measured": {}}


def _decide(m: dict, facts: LawFacts) -> dict:
    rules = _lmr_rules(m, facts)
    excluding = [r for r in rules if r["outcome"] == "excludes"]
    unknown = [r for r in rules if r["outcome"] == "unknown"]
    warned = [r for r in rules if r["outcome"] == "warn"]   # does not change the answer; printed with it
    dist_answer, dist = _distance_step(m, facts)

    # --- low and mid-rise answer ---
    if excluding:
        r = excluding[0]
        lmr = {"answer": NO, "reason_code": r["rule"], "clause": r["clause"], "page": r["page"],
               "law_version_date": facts.version_date, "detail": r["detail"], "figures": r["figures"]}
    elif dist_answer == NO:
        lmr = {"answer": NO, **dist, "figures": {k: dist.get(k) for k in ("straight_m", "limit_m", "walk_m", "walk_low_m", "walk_high_m")}}
    elif unknown:
        r = unknown[0]
        lmr = {"answer": CANT, "reason_code": r["rule"], "clause": r["clause"], "page": r["page"],
               "law_version_date": facts.version_date,
               "detail": "; ".join(f'{u["clause"]}: {u["detail"]}' for u in unknown), "figures": r["figures"]}  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    elif dist_answer == YES:
        lmr = {"answer": YES, **dist,
               "figures": {k: dist.get(k) for k in ("straight_m", "limit_m", "walk_m", "walk_low_m", "walk_high_m", "walk_best_m",
                                                    "margin_low_m", "margin_high_m", "entrance_unmapped_extra_m", "anchor", "entrance_id")}}
    else:
        lmr = {"answer": dist_answer, **dist,
               "figures": {k: dist.get(k) for k in ("straight_m", "limit_m", "walk_m", "walk_low_m", "walk_high_m", "walk_best_m",
                                                    "margin_low_m", "margin_high_m", "entrance_unmapped_extra_m", "anchor", "entrance_id")}}
    lmr["rules"] = [{k: r[k] for k in ("rule", "clause", "page", "outcome", "detail")} for r in rules]

    # --- TOD answer: its own question, its own clause ---
    c5 = rules[0]
    tod = {"clause": c5["clause"], "page": c5["page"], "law_version_date": facts.version_date, "detail": c5["detail"],  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
           "figures": c5["figures"],  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
           "answer": {"excludes": YES, "clear": NO, "unknown": CANT}[c5["outcome"]],  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
           "reason_code": {"excludes": "on_map_and_council_listed", "clear": "not_in_chapter_5", "unknown": "chapter_5_unclear"}[c5["outcome"]]}  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    if tod["answer"] == YES:  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        tod["standards"] = {k: {"value": facts.fact(k).get("value"), **facts.cite(k)} for k in (
            "tod_height_residential_flat_building_m", "tod_height_seniors_or_shop_top_m", "tod_fsr",
            "tod_affordable_gfa_threshold", "tod_affordable_share_percent", "tod_affordable_parking_1_bed",
            "tod_affordable_parking_2_bed", "tod_affordable_parking_3_plus_bed", "tod_min_lot_width_m")}
        tod["not_read"] = "Chapter 5 sections after s152 were read for their figures only, not for further exclusions"

    pathway = ("tod" if tod["answer"] == YES else  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
               "lmr" if lmr["answer"] == YES else  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
               "unknown" if CANT in (tod["answer"], lmr["answer"]) else  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
               "borderline" if lmr["answer"] == BORDER else "neither")  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)

    handled = {r["clause"] for r in rules}  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    nc = [{"para": para, "what": what, "clause": facts.paragraph(para)["clause"], "page": facts.paragraph(para)["page"]}  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
          for para, what in EXCLUSION_LABELS.items() if f"s164(1)({para})" not in handled]
    nc += [{"para": para, "what": what, "clause": facts.paragraph(para)["clause"], "page": facts.paragraph(para)["page"]}  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
           for para, what in PARTLY_CHECKED.items() if f"s164(1)({para})" in handled]
    warnings = [{"clause": r["clause"], "page": r["page"], "detail": r["detail"]} for r in warned]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    lmr["warnings"] = warnings
    notes: list[str] = []
    h = m.get("heritage") if isinstance(m.get("heritage"), dict) else {}
    if h.get("conservation_area") is True:
        notes.append("The lot is in a heritage conservation area. s164(1)(d) names heritage items, not conservation areas, so this is not counted as an exclusion.")
    if lmr["answer"] == YES:  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        notes.append("A council plan may set a maximum car parking rate; the parking standards of Chapter 6 apply only if none does. Check the council's own plan.")
    return {"pathway": pathway, "headline": _headline(pathway, lmr, tod), "lmr": lmr, "tod": tod,
            "not_checked": nc, "warnings": warnings,
            "notes": notes, "law_version_date": facts.version_date,
            "measured": {k: m.get(k) for k in ("lga", "straight_m", "sched12_straight_m", "walk") if k in m}}


def _headline(pathway: str, lmr: dict, tod: dict) -> str:
    if pathway == "tod":
        return f"Chapter 5 (Transport Oriented Development) applies to this lot ({tod['clause']}, p{tod['page']}). Chapter 6 does not."
    if pathway == "lmr":
        f = lmr["figures"]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        return (f"Within the Chapter 6 walking limit: walking range {f.get('walk_low_m')}-{f.get('walk_high_m')} m from {f.get('anchor')}, "
                f"limit {f.get('limit_m')} m ({lmr['clause']}, p{lmr['page']}). Not every exclusion was checked; see the list.")
    if pathway == "borderline":
        return (f"Borderline: {lmr['detail']} ({lmr['clause']}, p{lmr['page']}). The walking route is measured from public footpath "
                f"data; the law's route is the shortest one that may be walked using footpaths and crossings.")
    if pathway == "neither":
        return f"Neither pathway: Chapter 6: {lmr['detail']} ({lmr['clause']}, p{lmr['page']})."
    return "Not determined: " + (lmr["detail"] if lmr["answer"] == CANT else tod["detail"]) + NOT_DETERMINED_NEXT_STEP  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
