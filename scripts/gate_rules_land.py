#!/usr/bin/env python3
"""Land limits: council rules whose OWN words limit them to part of the land, served to every house.

prior-art-checked: gate_rules.py (over its 500-line limit) sets gate columns from a SQL `where` and cannot match a row by its
text; gate_rules_devtypes.py (merged #1655) is the same re-applied, fingerprint-keyed step for project types. Sweeps
2026-11-20 on origin/main 8bb97c98: scripts/ gate_rules*, never_serve, derive_precinct_keys; frontend for-property route reads
v2_applicable_zones, v2_marker and v2_dcp_layer already -- no new column, no frontend change. Plan:
~/.claude/plans/ce-wrong-land-FINITE-PLAN-2026-11-20.md

Data: data/chapter_scope/land_limits.json -- entries of (council, chapter_key, kind, zones, text fingerprints).
  kind "zones"     sets v2_applicable_zones to the listed zone codes (each must be in the council's LEP land-use table, DQ-30)
  kind "heritage"  sets v2_marker = 'heritage' (served to heritage houses only)
  kind "precinct"  sets v2_dcp_layer = 'precinct' with no precinct key: the rule is for a named place/street/site that has no
                   outline in our data, so it is shown to no house (same end state as hide_unmapped_area_rules.py)
A row is matched by council + chapter + never_serve.text_key(provision_text), so a re-extraction that mints new ids keeps the
limit. Only a row with no value yet is changed; never-serve rows, heritage-marked rows and rows with a precinct key are skipped.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import never_serve

PATH = Path(__file__).resolve().parent.parent / "data" / "chapter_scope" / "land_limits.json"
RULE_NAME = "land_limits"
KINDS = ("zones", "heritage", "precinct")


@lru_cache(maxsize=1)
def entries() -> tuple[dict, ...]:
    """The reviewed entries. A missing or miscounted file RAISES: a guard that silently reads empty limits nothing."""
    out = tuple(json.loads(PATH.read_text(encoding="utf-8"))["entries"])
    for e in out:
        if e["kind"] not in KINDS or len(e["text_sha256_16"]) != e["expect"] or (e["kind"] == "zones") != bool(e["zones"]):
            raise ValueError(f"land_limits.json {e['council']}/{e['chapter_key']} {e['kind']}: malformed entry")
    return out


def _zones_ok(cur, council: str, zones: list[str]) -> bool:
    """DQ-30: a zone this council's LEP does not have would reach no house."""
    try:
        from validate_zone_code_validity import load_ground_truth, load_slug_resolution
    except ImportError:                                   # imported as scripts.gate_rules_land
        from scripts.validate_zone_code_validity import load_ground_truth, load_slug_resolution
    truth = load_ground_truth(cur)
    key = load_slug_resolution(cur, truth).get(council)
    return key is not None and set(zones) <= truth.get(key, set())


def apply_land_limits(cur, council: str | None, apply: bool, only: set[str] | None = None) -> list[tuple]:
    """Set the limit columns on listed rows. Returns (id, column, before, after, rule) per change, for the backup (same
    shape as gate_rules.apply_gate_rules). Idempotent: a row that already holds a value no longer matches."""
    if only and RULE_NAME not in only:
        return []
    never = never_serve.ids()
    changes: list[tuple] = []
    for e in entries():
        if council and e["council"] != council:
            continue
        zones_checked = e["kind"] != "zones"          # checked once, only when a row of this entry is about to change
        fps = set(e["text_sha256_16"])
        cur.execute(
            "SELECT id, provision_text, v2_marker, v2_applicable_zones, v2_dcp_layer, v2_precinct_id, v2_heritage_hca"
            " FROM regulatory_provisions WHERE is_current = true AND source_council = %s"
            "   AND source_chapter_key IS NOT DISTINCT FROM %s",
            (e["council"], e["chapter_key"] or None))
        for rid, text, marker, zones, layer, pid, hca in cur.fetchall():
            if rid in never or never_serve.text_key(text) not in fps:
                continue
            if e["kind"] == "heritage" and marker is None:
                col, before, after = "v2_marker", marker, "heritage"
            elif e["kind"] == "zones" and (not zones or "ALL" in zones):
                if not zones_checked:
                    if not _zones_ok(cur, e["council"], e["zones"]):
                        raise ValueError(f"{RULE_NAME}: zones {e['zones']} are not in {e['council']}'s LEP land-use table")
                    zones_checked = True
                col, before, after = "v2_applicable_zones", zones, list(e["zones"])
            elif (e["kind"] == "precinct" and pid is None and hca is None and marker != "heritage"
                  and layer not in ("precinct", "condition")):
                col, before, after = "v2_dcp_layer", layer, "precinct"
            else:
                continue
            changes.append((rid, col, before, after, RULE_NAME))
            if apply:
                cur.execute(f"UPDATE regulatory_provisions SET {col} = %s WHERE id = %s", (after, rid))
    print(f"  gate {RULE_NAME:<29} to-change={len(changes)}")
    return changes
