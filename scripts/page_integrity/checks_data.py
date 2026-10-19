"""Cross-surface data checks over one capture folder (C1 same fact agrees, C3 honest absence,  # noqa: zone-codes (check ids)
C4 row fits the lot). Pure functions over `Capture`; offline; no DB, no network.

prior-art-checked: new offline checks over capture folders; no existing cross-surface checker (see docs/page_integrity/PRODUCER_MAP.md)

A route that is missing from the capture NEVER produces a pass: the fact is simply not examined
and `facts_checked(cap)` reports it as False so the runner can say what could not be checked.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

try:
    from scripts.page_integrity.load import Capture
except ImportError:  # run as a plain script from scripts/page_integrity
    from load import Capture  # type: ignore

P_PROP = "/api/property"
P_CA = "/api/constraint-arithmetic"
P_SC = "/api/dcp/structured-controls"
P_CAP = "/api/capacity/calculate"
P_PROV = "/api/provisions/for-property"
P_CURR = "/api/instrument-currency"

SETBACKS = ("front", "side", "rear")


@dataclass
class Flag:
    check: str
    fact: str
    detail: str
    evidence: str


# ---------------------------------------------------------------- helpers
def _num(v: Any) -> Optional[float]:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*(?:m|m2)?\s*", v)
        return float(m.group(1)) if m else None
    return None


def _d(x: Any) -> dict:
    return x if isinstance(x, dict) else {}


def _req(cap: Capture, path: str) -> dict:
    c = cap.last(path)
    return _d(c.get("request_body")) if c else {}


def _query(cap: Capture, path: str) -> dict:
    c = cap.last(path)
    return _d(c.get("query")) if c else {}


def _prop(cap: Capture) -> Optional[dict]:
    p = cap.data(P_PROP)
    return p if isinstance(p, dict) else None


def _ca(cap: Capture) -> Optional[dict]:
    p = cap.data(P_CA)
    return p if isinstance(p, dict) else None


def _controls(cap: Capture) -> Optional[list[dict]]:
    d = cap.data(P_SC)
    if not isinstance(d, dict) or not isinstance(d.get("categories"), list):
        return None
    out: list[dict] = []
    for cat in d["categories"]:
        for c in _d(cat).get("controls") or []:
            if isinstance(c, dict):
                out.append(c)
    return out


def _ctl_value(c: dict) -> Optional[float]:
    v = _num(c.get("value_min"))
    return v if v is not None else _num(c.get("value_max"))


def _row_text(c: dict) -> str:
    return " ".join(str(c.get(k) or "") for k in ("condition", "notes"))


def _sc_values(controls: list[dict], kind: str) -> list[float]:
    return [v for c in controls if c.get("control_type") == f"{kind}_setback"
            if (v := _ctl_value(c)) is not None]


def _close(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(a - b) <= tol


def _zone_code(v: Any) -> Optional[str]:
    if not isinstance(v, str):
        return None
    m = re.match(r"\s*([A-Za-z0-9]+)", v)
    return m.group(1).upper() if m else None


def _council_key(v: Any) -> Optional[str]:
    if not isinstance(v, str) or not v.strip():
        return None
    return re.sub(r"[\s\-]+", "_", v.strip().lower())


def _ca_setback(ca: dict, kind: str) -> Optional[float]:
    return _num(ca.get(f"setback_{kind}_m"))


def _ca_options(ca: dict, kind: str) -> list[float]:
    """Figures the yield box LISTS for a side whose rows disagree (setback_<kind>_options)."""
    return [v for o in (ca.get(f"setback_{kind}_options") or [])
            if isinstance(o, dict) and (v := _num(o.get("value_m"))) is not None]


def _has_route(cap: Capture, path: str) -> bool:
    return cap.last(path) is not None


# ---------------------------------------------------------------- C1
def _lot_areas(cap: Capture) -> dict[str, float]:
    out: dict[str, float] = {}
    p = _prop(cap)
    if p is not None and (v := _num(_d(p.get("lotDimensions")).get("area"))) is not None:
        out[f"{P_PROP}.lotDimensions.area"] = v
    if (v := _num(_req(cap, P_CA).get("lot_area_m2"))) is not None:
        out[f"{P_CA} lot_area_m2"] = v
    if (v := _num(_req(cap, P_CAP).get("lotSize"))) is not None:
        out[f"{P_CAP} lotSize"] = v
    return out


def _zones(cap: Capture) -> dict[str, str]:
    out: dict[str, str] = {}
    p = _prop(cap)
    for k, raw in ((f"{P_PROP}.constraints.zone", _d(p.get("constraints")).get("zone") if p else None),
                   (f"{P_CA} zone", _req(cap, P_CA).get("zone")),
                   (f"{P_PROV} zone", _query(cap, P_PROV).get("zone"))):
        if (z := _zone_code(raw)):
            out[k] = z
    return out


def same_fact_agrees(cap: Capture) -> list[Flag]:
    flags: list[Flag] = []
    ca, ctl = _ca(cap), _controls(cap)

    if ca is not None and ctl is not None:
        for k in SETBACKS:
            sc, v, opts = _sc_values(ctl, k), _ca_setback(ca, k), _ca_options(ca, k)
            if v is None and opts:
                # A listed side agrees only if it lists exactly the DCP tab's figures.
                extra = [o for o in opts if not any(_close(o, s) for s in sc)]
                left_out = [s for s in sc if not any(_close(s, o) for o in opts)]
                if extra or left_out:
                    flags.append(Flag("C1", f"{k}_setback",
                                      f"yield box lists {k} setbacks {sorted(set(opts))} but the DCP tab lists "
                                      f"{sorted(set(sc))}",
                                      f"{P_CA}.setback_{k}_options={opts}; {P_SC} {k}_setback={sc}"))
            elif sc and v is None:
                flags.append(Flag("C1", f"{k}_setback",
                                  f"constraint-arithmetic has no {k} setback but the DCP tab lists {sorted(set(sc))}",
                                  f"{P_CA}.setback_{k}_m=None; {P_SC} {k}_setback={sc}"))
            elif v is not None and not any(_close(v, s) for s in sc):
                flags.append(Flag("C1", f"{k}_setback",
                                  f"constraint-arithmetic {k} setback {v} is not among DCP tab values {sorted(set(sc))}",
                                  f"{P_CA}.setback_{k}_m={v}; {P_SC} {k}_setback={sc}"))

    areas = _lot_areas(cap)
    if len(areas) >= 2 and max(areas.values()) - min(areas.values()) > 0.01:
        flags.append(Flag("C1", "lot_area", f"lot area differs between surfaces: {areas}",
                          "; ".join(f"{k}={v}" for k, v in areas.items())))

    zones = _zones(cap)
    if len(set(zones.values())) > 1:
        flags.append(Flag("C1", "zone", f"zone code differs between surfaces: {zones}",
                          "; ".join(f"{k}={v}" for k, v in zones.items())))

    p = _prop(cap)
    if p is not None and _has_route(cap, P_CA):
        for fact, key in (("fsr", "maxFsr"), ("height", "maxHeight")):
            a = _num(_d(p.get("constraints")).get(key))
            b = _num(_req(cap, P_CA).get(key))
            if (a is None) != (b is None) or (a is not None and b is not None and not _close(a, b, 1e-6)):
                flags.append(Flag("C1", fact, f"{fact} differs: property={a}, constraint-arithmetic request={b}",
                                  f"{P_PROP}.constraints.{key}={a}; {P_CA} request {key}={b}"))
    return flags


# ---------------------------------------------------------------- C3
def _council_keys(cap: Capture) -> dict[str, str]:
    ca = _req(cap, P_CA)
    cands = {
        P_CA: ca.get("formerCouncil") or ca.get("lga"),
        P_SC: _query(cap, P_SC).get("council"),
        P_PROV: _query(cap, P_PROV).get("former_council"),
        P_CURR: _query(cap, P_CURR).get("council"),
    }
    return {r: k for r, v in cands.items() if (k := _council_key(v))}


def honest_absence(cap: Capture) -> list[Flag]:
    flags: list[Flag] = []
    ca, ctl = _ca(cap), _controls(cap)
    if ca is not None and ctl is not None:
        gaps = [g for g in (ca.get("gaps") or []) if isinstance(g, str)]
        says_none = any("No DCP setback controls" in g for g in gaps)
        all_none = all(_ca_setback(ca, k) is None and not _ca_options(ca, k) for k in SETBACKS)
        rows = {k: _sc_values(ctl, k) for k in SETBACKS}
        if (says_none or all_none) and any(rows.values()):
            flags.append(Flag("C3", "setbacks_absent",
                              "constraint-arithmetic reports no DCP setbacks while the DCP tab holds numeric rows "
                              + str({k: v for k, v in rows.items() if v}),
                              f"{P_CA}.gaps={gaps}; setbacks={[_ca_setback(ca, k) for k in SETBACKS]}"))
    keys = _council_keys(cap)
    if len(set(keys.values())) > 1:
        flags.append(Flag("C3", "council_key", f"different council keys sent to different routes: {keys}",
                          "; ".join(f"{r}={k}" for r, k in keys.items())))
    return flags


# ---------------------------------------------------------------- C4
_HOUSING = re.compile(r"terrace|dual occupanc|duplex|semi-detached|multi[- ]dwelling|residential flat|"
                      r"secondary dwelling|boarding|seniors|attached dwelling|townhouse", re.I)
_GROUP = [("terrace", "terrace"), ("dual", "dual"), ("duplex", "dual"), ("semi", "semi"), ("multi", "multi"),
          ("townhouse", "multi"), ("residential flat", "flat"), ("secondary", "secondary"),
          ("boarding", "boarding"), ("senior", "senior"), ("attached", "attached")]
_COND = re.compile(r"upper floor|upper level|first floor|two[- ]storey|second storey|single storey|corner|"
                   r"secondary street|state and regional road|classified road|arterial|"
                   r"lot.{0,20}(>|greater|over|exceeding)|where .*exceeds", re.I)
# a base-case row (ground / single storey) is a legitimate alternative answer even though it matches _COND
_BASE = re.compile(r"single storey|ground (level|floor)", re.I)
_CORNER = re.compile(r"corner", re.I)
# The DCP tab hides an extraction note from the reader (DcpStructuredControls / publicCondition),
# so the check judges only the words the reader sees.
_INTERNAL_TAIL = re.compile(r"NOT yet stored:.*$", re.I | re.S)
_EXCLUDED = re.compile(r"\b(?:excludes?|excluding|except|other than|not for)\b[^.;]*", re.I)


def _group(term: str) -> Optional[str]:
    t = term.lower()
    return next((g for k, g in _GROUP if t.startswith(k)), None)


def _is_alt(c: dict) -> bool:
    t = _row_text(c)
    return not t.strip() or not _COND.search(t) or bool(_BASE.search(t))


def row_fits_lot(cap: Capture) -> list[Flag]:
    flags: list[Flag] = []
    ctl = _controls(cap)
    if ctl is None:
        return flags
    dev = str(_query(cap, P_SC).get("dev_type") or "").lower()

    for c in ctl:  # (a)
        # "excludes outbuildings and secondary dwellings" names a type the row is NOT for: a
        # house rule, not a secondary-dwelling one (false positive on 9 Concord pages, 2026-10-19).
        m = _HOUSING.search(_EXCLUDED.sub(" ", _INTERNAL_TAIL.sub("", _row_text(c))))
        if not m:
            continue
        g = _group(m.group(0))
        if g and g not in dev:
            flags.append(Flag("C4", "row_dev_type",
                              f"row under dev_type '{dev}' names '{m.group(0)}': {c.get('control_type')} "
                              f"{_ctl_value(c)} p.{c.get('pdf_page')} [{_row_text(c).strip()[:90]}]",
                              f"{P_SC} {c.get('control_type')} pdf_page={c.get('pdf_page')}"))

    ca = _ca(cap)
    if ca is not None:  # (b)
        for k in SETBACKS:
            v = _ca_setback(ca, k)
            if v is None:
                continue
            rows = [(c, _ctl_value(c)) for c in ctl if c.get("control_type") == f"{k}_setback"]
            rows = [(c, x) for c, x in rows if x is not None]
            chosen = [c for c, x in rows if _close(x, v)]
            if not chosen or any(not _COND.search(_row_text(c)) for c in chosen):
                continue
            alts = [(c, x) for c, x in rows if not _close(x, v) and _is_alt(c)]
            if alts:
                a, ax = alts[0]
                flags.append(Flag("C4", f"{k}_setback_conditional",
                                  f"{k} setback {v} m comes only from conditional row(s) "
                                  f"[{_row_text(chosen[0]).strip()[:80]}] while p.{a.get('pdf_page')} gives {ax} m "
                                  f"[{_row_text(a).strip()[:40] or 'no condition'}]",
                                  f"{P_CA}.setback_{k}_m={v}; {P_SC} {k}_setback={[x for _, x in rows]}"))

    p = _prop(cap)  # (c)
    corner = _d(_d(p).get("cornerLot")).get("isCornerLot") if p else None
    # The DCP tab marks a corner-only row on a measured non-corner lot with this sentence; a row
    # marked that way is shown honestly, so it is not a fault. A failed road check (error set)
    # is not a measured "no".
    marked = "Applies only to corner lots — this lot is not on a corner" in (cap.rendered.get("dcp") or "")
    measured = p is not None and not _d(p.get("cornerLot")).get("error")
    if corner is False and measured and not marked:
        for c in ctl:
            t = _row_text(c)
            if _CORNER.search(t) and not re.search(r"applies only if", t, re.I):
                flags.append(Flag("C4", "corner_lot",
                                  f"corner-lot row shown but property is not a corner lot: {c.get('control_type')} "
                                  f"{_ctl_value(c)} p.{c.get('pdf_page')} [{t.strip()[:70]}]",
                                  f"{P_PROP}.cornerLot.isCornerLot=False; {P_SC} pdf_page={c.get('pdf_page')}"))
    return flags


# ---------------------------------------------------------------- coverage
def facts_checked(cap: Capture) -> dict[str, bool]:
    """Which facts the checks could actually examine. False = a route/field was missing, NOT a pass."""
    ca, ctl, p = _ca(cap), _controls(cap), _prop(cap)
    both = ca is not None and ctl is not None
    out = {f"setback_{k}": both for k in SETBACKS}
    out["lot_area"] = len(_lot_areas(cap)) >= 2
    out["zone"] = len(_zones(cap)) >= 2
    for fact in ("fsr", "height"):
        out[fact] = p is not None and _has_route(cap, P_CA)
    out["absence_setbacks"] = both
    out["council_key"] = len(_council_keys(cap)) >= 2
    out["row_dev_type"] = ctl is not None
    out["conditional_choice"] = both
    out["corner_lot"] = ctl is not None and p is not None and "isCornerLot" in _d(p.get("cornerLot"))
    return out
