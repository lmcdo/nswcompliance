#!/usr/bin/env python3
"""Brief field-coverage ratchet (S3) — a brief layer may gain fields, never lose them.

prior-art-checked: new gate; complements (does not duplicate) the existing
brief tooling: lint_brief_failsoft.py guards the fail-soft anti-pattern,
brief_contract_drift.py guards the INPUT seam (service output vs S2 contract).
This locks the OUTPUT surface — the set of fields each brief layer/model
exposes to the UI. A refactor that drops a field (the "brief silently stopped
surfacing X" class this whole plan exists to kill) fails pre-push here instead
of shipping as a quietly thinner card.

How it works:
  - Recursively walks every Pydantic model reachable from the two brief roots
    (DevelopmentBrief / RenovationBrief) plus the S2 service contracts, and
    records {model name: sorted field names}.
  - --check (default): compares against the checked-in baseline. A model or
    field present in the baseline but missing now = FAIL (ratchet violated).
    New models/fields = OK but reported, with a hint to --regen so the ratchet
    covers them too.
  - --regen: rewrites the baseline from current code (do this in the same PR
    that intentionally adds fields; removals require editing the baseline by
    hand, which is the point — a removal must be a visible, deliberate act).

Runs under tests/conftest_mocks so no native deps (psycopg2/rasterio) are
needed — pure model introspection, no I/O.

Usage:
  python scripts/brief_field_coverage_ratchet.py            # check (exit 1 on loss)
  python scripts/brief_field_coverage_ratchet.py --regen    # rewrite baseline
"""
from __future__ import annotations

import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_PATH = os.path.join(REPO, "scripts", "brief_field_coverage_baseline.json")


def collect_from_roots(roots) -> dict[str, list[str]]:
    """{model name: sorted field names} for every Pydantic model reachable from roots.

    Raises RuntimeError on a class-name collision with DIFFERENT field sets —
    silently keeping first-seen would leave the second model unlocked (a hole
    in the ratchet), so a collision must be resolved by renaming a model.
    """
    import typing as _typing

    from pydantic import BaseModel

    seen: dict[str, list[str]] = {}
    recorded_cls: dict[str, type] = {}

    def _iter_models(annotation) -> list[type[BaseModel]]:
        found: list[type[BaseModel]] = []
        stack = [annotation]
        while stack:
            ann = stack.pop()
            if isinstance(ann, type) and issubclass(ann, BaseModel):
                found.append(ann)
            else:
                stack.extend(_typing.get_args(ann))
        return found

    def _walk(model: type[BaseModel]) -> None:
        name = model.__name__
        # Parametrised generics (DataField[Optional[X]]) all share DataField's
        # envelope — recorded once under the bare name; still recurse into X.
        record = "[" not in name
        if record:
            if name in seen:
                if recorded_cls[name] is not model and seen[name] != sorted(model.model_fields.keys()):
                    raise RuntimeError(
                        f"Ratchet name collision: two models named {name!r} with different "
                        f"fields ({recorded_cls[name].__module__} vs {model.__module__}) — "
                        f"rename one, or the second's fields are never locked."
                    )
                return
            seen[name] = sorted(model.model_fields.keys())
            recorded_cls[name] = model
        for field in model.model_fields.values():
            for sub in _iter_models(field.annotation):
                if sub.__name__ != name:
                    _walk(sub)

    for root in roots:
        _walk(root)
    return seen


def _collect_field_map() -> dict[str, list[str]]:
    """Collect the field map from the brief's real roots."""
    if REPO not in sys.path:
        sys.path.insert(0, REPO)
    # Stub native deps (psycopg2/requests/pyproj/rasterio-if-missing) exactly the
    # way the test suite does, so this runs identically on dev, hook, and CI.
    import tests.conftest_mocks  # noqa: F401

    from pydantic import BaseModel

    import services.intelligence_brief as ib
    from services.vg_comparables import ComparableAnalysis, PropertySale

    roots: list[type[BaseModel]] = [
        # Brief output roots — walking these reaches every section/layer model.
        ib.DevelopmentBrief,
        ib.RenovationBrief,
        # The DataField envelope itself (parametrised variants are skipped below).
        ib.DataField,
        # S2 service contracts (input seam) — their key sets must not shrink either.
        ib.FloodServiceOutput,
        ib.BushfireServiceOutput,
        ib.ShadowServiceOutput,
        ib.StrataServiceOutput,
        ib.ClimateRiskServiceOutput,
        ib.HousingSeppFormOutput,
        ib.LepLandUseRow,
        ComparableAnalysis,
        PropertySale,
        # Explicit root: SatelliteData.terrain's annotation is a ForwardRef
        # (TerrainAnalysisDetail is imported AFTER SatelliteData is defined),
        # which typing.get_args() cannot see through — walk it directly.
        ib.TerrainAnalysisDetail,
    ]

    return collect_from_roots(roots)


def check(current: dict[str, list[str]], baseline: dict[str, list[str]]) -> int:
    losses: list[str] = []
    additions: list[str] = []
    for model, fields in baseline.items():
        if model not in current:
            losses.append(f"MODEL LOST: {model} (was surfacing {len(fields)} fields)")
            continue
        missing = sorted(set(fields) - set(current[model]))
        for f in missing:
            losses.append(f"FIELD LOST: {model}.{f}")
        for f in sorted(set(current[model]) - set(fields)):
            additions.append(f"{model}.{f}")
    for model in sorted(set(current) - set(baseline)):
        additions.append(f"{model} (new model, {len(current[model])} fields)")

    if additions:
        print(f"FIELD-COVERAGE: {len(additions)} new field(s)/model(s) not in baseline "
              f"(run --regen in this PR so the ratchet covers them):")
        for a in additions:
            print(f"  + {a}")
    if losses:
        print("\nFIELD-COVERAGE RATCHET: FAILED — a brief layer stopped surfacing "
              "field(s) it used to:\n")
        for loss in losses:
            print(f"  - {loss}")
        print("\nIf the removal is deliberate, edit scripts/brief_field_coverage_baseline.json "
              "in the same PR and say why in the PR body.")
        return 1
    print(f"FIELD-COVERAGE RATCHET: PASSED ({len(current)} models locked)")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regen", action="store_true", help="rewrite the baseline from current code")
    args = parser.parse_args(argv[1:])

    current = _collect_field_map()

    if args.regen:
        with open(BASELINE_PATH, "w", encoding="utf-8") as fh:
            json.dump(current, fh, indent=2, sort_keys=True)
            fh.write("\n")
        print(f"Baseline regenerated: {BASELINE_PATH} ({len(current)} models)")
        return 0

    if not os.path.exists(BASELINE_PATH):
        print(f"FIELD-COVERAGE RATCHET: no baseline at {BASELINE_PATH} — run --regen first.")
        return 1
    with open(BASELINE_PATH, encoding="utf-8") as fh:
        baseline = json.load(fh)
    return check(current, baseline)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
