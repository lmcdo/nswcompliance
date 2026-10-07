"""CDC Housing Code lot-requirements screen: the deterministic evaluation.

prior-art-checked: reuse not viable because services/cdc_screen.py is a 10-check
screen whose heritage/flood/bushfire/contamination mappings are coded judgement
with no provision binding; this module evaluates ONLY the four lot requirements
below, from a ValidatedAuthority (services/cdc_lot_authority.py). The legacy
screen and the other CDC surfaces are untouched and are NOT covered by this
authority boundary.

Question answered: "Does this lot fail any of the Housing Code lot requirements
that this screen can determine?"  It does not assess CDC eligibility.

  zone            Codes SEPP cl 3.1(3)(a)
  lot_area        Codes SEPP cl 3.1(3)(b)
  lot_width       Codes SEPP cl 3.1(3)(c) (width measured at the building line)
  acid_sulfate    Codes SEPP cl 1.19(1)(c)

Results:
  EXCLUDED                          at least one criterion positively fails
  NOT_EXCLUDED_BY_CHECKED_CRITERIA  every criterion was evaluated and none failed
  UNKNOWN                           no failure, and at least one criterion could not
                                    be evaluated from the property data
  UNAVAILABLE                       the authority could not be established; no
                                    criterion is evaluated (built by the API layer)

evaluate() is a pure function: thresholds come only from the ValidatedAuthority,
facts only from LotInputs, and nothing calls a model, the network or a clock.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal, Optional

from pydantic import BaseModel

try:
    from services.cdc_lot_authority import StandardAuthority, ValidatedAuthority
except ImportError:  # local (non-Docker) import path
    from cdc_lot_authority import StandardAuthority, ValidatedAuthority  # type: ignore

ENGINE_VERSION = "cdc-lot-requirements/1"

SCOPE_NOTE = (
    "This screen checks four Housing Code lot requirements only: Codes SEPP "
    "cl 3.1(3)(a) zone, (b) lot area, (c) lot width at the building line, and "
    "cl 1.19(1)(c) acid sulfate soils class. It does not assess whether "
    "complying development is available for a proposal. A registered certifier "
    "makes that assessment."
)

# Data-agreement tolerances. These are NOT regulatory values: they decide when
# two measurements of the same lot agree well enough to be used at all.
# Two lot-area sources that differ by more than 5% are treated as conflicting.
AREA_AGREEMENT_RATIO = 1.05
# Mapped acid sulfate polygons and cadastre lots come from different surveys, so a
# lot wholly inside a Class 1/2 polygon can compute fractionally short of 100%.
# Below this fraction only PART of the lot is shown as excluded land, and
# cl 1.19(6) allows complying development on the part that is not.
WHOLE_LOT_FRACTION = 0.995

Outcome = Literal["FAIL", "PASS", "UNKNOWN"]
Result = Literal["EXCLUDED", "NOT_EXCLUDED_BY_CHECKED_CRITERIA", "UNKNOWN", "UNAVAILABLE"]


@dataclass(frozen=True)
class AreaReading:
    source: str
    value_m2: float


@dataclass(frozen=True)
class LotInputs:
    """Property facts, each three-state. None means "could not be established"
    and always carries a reason; it is never read as a pass."""

    zones: Optional[frozenset] = None
    zone_source: str = ""
    zone_reason: Optional[str] = None
    areas: tuple = ()  # tuple[AreaReading, ...]
    area_reason: Optional[str] = None
    # (smallest, largest) width the lot can have at ANY building line; None = unknown.
    width_range_m: Optional[tuple] = None
    width_source: str = ""
    width_reason: Optional[str] = None
    # Acid sulfate: frozenset of mapped classes intersecting the lot; an EMPTY set
    # means the lot is not identified on an Acid Sulfate Soils Map.
    ass_classes: Optional[frozenset] = None
    ass_source: str = ""
    ass_reason: Optional[str] = None
    # Fraction of the lot covered by mapped classes at or below the excluded class.
    ass_excluded_fraction: Optional[float] = None
    notes: tuple = field(default_factory=tuple)


class AuthorityEvidence(BaseModel):
    standard_id: int
    clause: str
    source_quote: str
    provision_ids: list[int]
    pdf_pages: list[int]
    pdf_url: str
    source_url: str
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None


class CriterionResult(BaseModel):
    criterion: Literal["zone", "lot_area", "lot_width", "acid_sulfate"]
    clause: str
    outcome: Outcome
    input: Optional[object] = None
    input_source: str
    rule: str
    comparison: str
    authority: AuthorityEvidence


class LotRequirementsResult(BaseModel):
    result: Result
    criteria: list[CriterionResult]
    authority_failures: list[str] = []
    property: dict = {}
    notes: list[str] = []
    scope: str = SCOPE_NOTE
    engine_version: str = ENGINE_VERSION


def _evidence(a: StandardAuthority) -> AuthorityEvidence:
    return AuthorityEvidence(
        standard_id=a.standard_id, clause=a.clause, source_quote=a.source_quote,
        provision_ids=[p.provision_id for p in a.provisions],
        pdf_pages=[p.pdf_page for p in a.provisions],
        pdf_url=a.pdf_url, source_url=a.source_url,
        verified_by=a.verified_by, verified_at=a.verified_at,
    )


def _positive_finite(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0


def _zone(a: StandardAuthority, inp: LotInputs) -> CriterionResult:
    allowed = a.value
    rule = f"lot must be in Zone {', '.join(sorted(allowed))}"
    zones = inp.zones
    if not zones:
        return CriterionResult(criterion="zone", clause=a.clause, outcome="UNKNOWN", input=None,
                               input_source=inp.zone_source, rule=rule,
                               comparison=inp.zone_reason or "zone could not be established",
                               authority=_evidence(a))
    shown = sorted(zones)
    if zones <= allowed:
        outcome, cmp = "PASS", f"zone(s) {', '.join(shown)} all within the listed zones"
    elif not (zones & allowed):
        outcome, cmp = "FAIL", f"zone(s) {', '.join(shown)} not among the listed zones"
    else:
        outcome = "UNKNOWN"
        cmp = (f"lot is split across zones {', '.join(shown)}, only some of which are listed; "
               "this screen does not determine which part a development would occupy")
    return CriterionResult(criterion="zone", clause=a.clause, outcome=outcome, input=shown,
                           input_source=inp.zone_source, rule=rule, comparison=cmp,
                           authority=_evidence(a))


def _area(a: StandardAuthority, inp: LotInputs) -> CriterionResult:
    minimum = float(a.value)  # type: ignore[arg-type]
    rule = f"lot area must not be less than {minimum:g} m²"
    readings = [r for r in inp.areas if isinstance(r, AreaReading)]
    shown = [{"source": r.source, "value_m2": r.value_m2} for r in readings]
    src = ", ".join(r.source for r in readings) or "none"

    def unknown(why: str) -> CriterionResult:
        return CriterionResult(criterion="lot_area", clause=a.clause, outcome="UNKNOWN",
                               input=shown or None, input_source=src, rule=rule,
                               comparison=why, authority=_evidence(a))

    if inp.area_reason:
        return unknown(inp.area_reason)
    if not readings:
        return unknown("lot area could not be established")
    if not all(_positive_finite(r.value_m2) for r in readings):
        return unknown("a lot area reading is not a finite positive number")
    lo, hi = min(r.value_m2 for r in readings), max(r.value_m2 for r in readings)
    if hi / lo > AREA_AGREEMENT_RATIO:
        return unknown(f"lot area sources disagree ({lo:g} m² vs {hi:g} m²)")
    below = [r.value_m2 < minimum for r in readings]
    if all(below):
        return CriterionResult(criterion="lot_area", clause=a.clause, outcome="FAIL", input=shown,
                               input_source=src, rule=rule,
                               comparison=f"{hi:g} m² < {minimum:g} m²" if len(readings) == 1
                               else f"every source below {minimum:g} m² (max {hi:g} m²)",
                               authority=_evidence(a))
    if not any(below):
        return CriterionResult(criterion="lot_area", clause=a.clause, outcome="PASS", input=shown,
                               input_source=src, rule=rule,
                               comparison=f"{lo:g} m² ≥ {minimum:g} m²" if len(readings) == 1
                               else f"every source at or above {minimum:g} m² (min {lo:g} m²)",
                               authority=_evidence(a))
    return unknown(f"lot area sources fall either side of {minimum:g} m² ({lo:g} vs {hi:g} m²)")


def _width(a: StandardAuthority, inp: LotInputs) -> CriterionResult:
    """PASS only when every possible building-line width meets the minimum, FAIL
    only when none can; otherwise the answer depends on where the building line
    falls (or which boundary faces the road) and is UNKNOWN."""
    minimum = float(a.value)  # type: ignore[arg-type]
    rule = f"lot width measured at the building line must be at least {minimum:g} m"

    def res(outcome: Outcome, cmp: str, value=None) -> CriterionResult:
        return CriterionResult(criterion="lot_width", clause=a.clause, outcome=outcome, input=value,
                               input_source=inp.width_source or "none", rule=rule,
                               comparison=cmp, authority=_evidence(a))

    rng = inp.width_range_m
    if (not isinstance(rng, tuple) or len(rng) != 2
            or not all(_positive_finite(v) for v in rng) or rng[0] > rng[1]):
        return res("UNKNOWN", inp.width_reason or "width at the building line could not be established")
    lo, hi = float(rng[0]), float(rng[1])
    shown = {"min_m": lo, "max_m": hi}
    if lo >= minimum:
        return res("PASS", f"every building-line width is at least {lo:g} m ≥ {minimum:g} m", shown)
    if hi < minimum:
        return res("FAIL", f"every building-line width is at most {hi:g} m < {minimum:g} m", shown)
    return res("UNKNOWN", f"building-line width lies between {lo:g} m and {hi:g} m depending on which "
               f"boundary faces the road; not determinable against {minimum:g} m", shown)


def _acid_sulfate(a: StandardAuthority, inp: LotInputs) -> CriterionResult:
    max_class = int(a.value)  # type: ignore[arg-type]
    excluded = set(range(1, max_class + 1))
    rule = (f"land identified on an Acid Sulfate Soils Map as Class "
            f"{' or Class '.join(str(c) for c in sorted(excluded))} is excluded")
    classes = inp.ass_classes

    def res(outcome: Outcome, cmp: str, value=None) -> CriterionResult:
        return CriterionResult(criterion="acid_sulfate", clause=a.clause, outcome=outcome,
                               input=value, input_source=inp.ass_source, rule=rule,
                               comparison=cmp, authority=_evidence(a))

    if classes is None:
        return res("UNKNOWN", inp.ass_reason or "acid sulfate class could not be established")
    if not all(isinstance(c, int) and not isinstance(c, bool) and 1 <= c <= 5 for c in classes):
        return res("UNKNOWN", "an acid sulfate class reading is invalid")
    shown = sorted(classes)
    if not (set(classes) & excluded):
        return res("PASS", "not identified on an Acid Sulfate Soils Map" if not classes
                   else f"mapped class(es) {shown} not among the excluded classes", shown)
    frac = inp.ass_excluded_fraction
    if set(classes) <= excluded and frac is not None and math.isfinite(frac) and frac >= WHOLE_LOT_FRACTION:
        return res("FAIL", f"lot mapped as Class {shown} over {frac:.1%} of its area", shown)
    return res("UNKNOWN",
               f"mapped class(es) {shown} include an excluded class on part of the lot only "
               f"(excluded-class coverage {'unknown' if frac is None else f'{frac:.1%}'}); "
               "cl 1.19(6) allows complying development on the part that is not excluded land", shown)


def evaluate(authority: ValidatedAuthority, inputs: LotInputs) -> list[CriterionResult]:
    """Evaluate the four criteria. Requires a ValidatedAuthority — there is no
    code path that evaluates without one."""
    if not isinstance(authority, ValidatedAuthority):
        raise TypeError("evaluate() requires a ValidatedAuthority; return UNAVAILABLE instead")
    return [
        _zone(authority.get("eligible_zones"), inputs),
        _area(authority.get("min_lot_size"), inputs),
        _width(authority.get("min_lot_width"), inputs),
        _acid_sulfate(authority.get("acid_sulfate_max_class"), inputs),
    ]


def overall(criteria: list[CriterionResult]) -> Result:
    outcomes = [c.outcome for c in criteria]
    if len(outcomes) != 4:
        return "UNKNOWN"
    if "FAIL" in outcomes:
        return "EXCLUDED"
    if all(o == "PASS" for o in outcomes):
        return "NOT_EXCLUDED_BY_CHECKED_CRITERIA"
    return "UNKNOWN"
