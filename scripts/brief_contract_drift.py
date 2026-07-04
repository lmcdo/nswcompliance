#!/usr/bin/env python3
"""S3 contract drift check — the live tripwire on the S2 typed boundary.

prior-art-checked: new tool; no existing check validates service output against
the brief's S2 contracts. Complements (does not duplicate) the failsoft lint and
the per-build contract tests.

The S2 contracts (FloodServiceOutput / BushfireServiceOutput / ShadowServiceOutput)
TOLERATE a missing key (it parses to None), so a service that RENAMES or DROPS a
key silently nulls the brief card — the exact #589 class. This check closes that
gap by comparing a real service output's keys to the contract's expected fields:

  - a contract field MISSING from the output  -> a rename/drop (DRIFT — dangerous,
    the brief reads it and gets None)
  - an output key NOT in the contract          -> a new service field (informational)

Two modes, same core:
  - CI / regression: validate captured baseline outputs (tests + the JSON below).
  - Live (Railway cron / local with DB+network): capture each service's real output
    for a demo address, dump to JSON, then run this to fail on drift BEFORE a user
    hits a blank card. "Test the context ahead."

Usage:
  python scripts/brief_contract_drift.py <captured_outputs.json>
where the JSON is {"flood": {...outputs...}, "bushfire": {...outputs...},
"shadow": {...output...}}.  Exit 0 = no drift, 1 = drift found.
"""
from __future__ import annotations

import json
import sys

# Imported lazily inside functions so the pure check + tests don't drag heavy deps.


def check_drift(contract_cls, raw: dict | None) -> dict:
    """Compare one service output's top-level keys to its contract's fields.

    Returns {service, missing, extra, drift}. ``missing`` (a contract field absent
    from the output) is real drift — the brief would read it as None.
    """
    expected = set(contract_cls.model_fields.keys())
    present = set((raw or {}).keys())
    missing = sorted(expected - present)
    extra = sorted(present - expected)
    return {
        "service": contract_cls.__name__,
        "missing": missing,   # rename/drop -> the #589 silent-null
        "extra": extra,        # new service field (contract ignores it)
        "drift": bool(missing),
    }


def _registry():
    """service name -> (contract class, the sub-key holding the output dict or None)."""
    from services.intelligence_brief import (
        FloodServiceOutput,
        BushfireServiceOutput,
        ShadowServiceOutput,
        StrataCoreOutput,
        ClimateRiskServiceOutput,
    )
    from services.terrain_analysis import TerrainAnalysisDetail

    return {
        "flood": (FloodServiceOutput, "outputs"),
        "bushfire": (BushfireServiceOutput, "outputs"),
        "shadow": (ShadowServiceOutput, None),  # shadow has no 'outputs' wrapper
        # Slice-0 additions — no 'outputs' wrapper on any of these:
        # strata drift checks the always-emitted core keys only (StrataHub
        # enrichment keys are conditionally present by design).
        "strata": (StrataCoreOutput, None),
        "terrain": (TerrainAnalysisDetail, None),
        "climate": (ClimateRiskServiceOutput, None),
    }


def check_outputs(captured: dict[str, dict]) -> tuple[list[dict], bool]:
    """Run check_drift for every captured service output. Returns (findings, has_drift)."""
    reg = _registry()
    findings: list[dict] = []
    for service, raw in captured.items():
        if service not in reg:
            findings.append({"service": service, "missing": [], "extra": [], "drift": False,
                             "note": "unknown service (no contract)"})
            continue
        contract_cls, subkey = reg[service]
        out = (raw.get(subkey) if subkey else raw) or {}
        findings.append(check_drift(contract_cls, out))
    has_drift = any(f["drift"] for f in findings)
    return findings, has_drift


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: brief_contract_drift.py <captured_outputs.json>")
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        captured = json.load(fh)
    findings, has_drift = check_outputs(captured)
    for f in findings:
        status = "DRIFT" if f["drift"] else "ok"
        line = f"[{status}] {f['service']}"
        if f["missing"]:
            line += f" — MISSING contract keys (rename/drop): {f['missing']}"
        if f["extra"]:
            line += f" — new service keys: {f['extra']}"
        if f.get("note"):
            line += f" — {f['note']}"
        print(line)
    if has_drift:
        print("\nCONTRACT-DRIFT: FAILED — a service renamed/dropped a key the brief reads. "
              "Update the S2 contract (and the brief read) to the new key.")
        return 1
    print("\nCONTRACT-DRIFT: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
