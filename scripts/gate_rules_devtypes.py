#!/usr/bin/env python3
"""Project-type limits: council rules that are for ONE kind of project, tagged for every type.

prior-art-checked: gate_rules.py (525 lines, over the 500 limit) sets gate columns from a SQL `where` and cannot hold
v2_applicable_dev_types; enrichment/config/*_config.py sets that column from a council's config and re-applies "ALL" on every
publish (v2_dev_type_source = 'config_all'). Sweeps 2026-11-20 on origin/main 8795a4ee: scripts/ gate_rules*, never_serve,
enrichment/ -- no step narrows dev types after a publish. This is that step, kept beside gate_rules.py and called from the end of
gate_rules.apply_gate_rules, so derive_precinct_keys re-applies it after every publish like the gate rules.
Plan: ~/.claude/plans/ce-wrong-land-FINITE-PLAN-2026-11-20.md

Data: data/chapter_scope/dev_type_limits.json -- entries of (council, chapter_key, tags, text fingerprints). A row is matched by
council + chapter + never_serve.text_key(provision_text), so a re-extraction that mints new ids keeps the limit. A rule whose
text changes in an amendment loses the limit and goes back to "every type" (the safe direction).

SAFETY: only a row that is current, tagged exactly ['ALL'] and has v2_dev_type_source = 'config_all' is changed. config_declined
(ALL's third meaning, migration 081), text_regex, config_specific, no_config, already-specific and never-serve rows are skipped.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import never_serve

PATH = Path(__file__).resolve().parent.parent / "data" / "chapter_scope" / "dev_type_limits.json"
RULE_NAME = "dev_type_limits"


@lru_cache(maxsize=1)
def entries() -> tuple[dict, ...]:
    """The reviewed entries. A missing or miscounted file RAISES: a guard that silently reads empty limits nothing."""
    out = tuple(json.loads(PATH.read_text(encoding="utf-8"))["entries"])
    for e in out:
        if len(e["text_sha256_16"]) != e["expect"] or not e["tags"]:
            raise ValueError(f"dev_type_limits.json {e['council']}/{e['chapter_key']}: {len(e['text_sha256_16'])} fingerprints, expect {e['expect']}")
    return out


def apply_dev_type_limits(cur, council: str | None, apply: bool, only: set[str] | None = None) -> list[tuple]:
    """Narrow listed rows from ['ALL'] to their project types. Returns (id, column, before, after, rule) per change, for the
    backup (same shape as gate_rules.apply_gate_rules). Idempotent: a row already narrowed no longer matches."""
    if only and RULE_NAME not in only:
        return []
    never = never_serve.ids()
    changes: list[tuple] = []
    for e in entries():
        if council and e["council"] != council:
            continue
        fps = set(e["text_sha256_16"])
        cur.execute(
            "SELECT id, provision_text, v2_applicable_dev_types FROM regulatory_provisions"
            " WHERE is_current = true AND source_council = %s AND source_chapter_key IS NOT DISTINCT FROM %s"
            "   AND v2_dev_type_source = 'config_all'",
            (e["council"], e["chapter_key"] or None))
        for rid, text, tags in cur.fetchall():
            if rid in never or tags is None or list(tags) != ["ALL"]:
                continue
            if never_serve.text_key(text) not in fps:
                continue
            changes.append((rid, "v2_applicable_dev_types", list(tags), list(e["tags"]), RULE_NAME))
            if apply:
                cur.execute("UPDATE regulatory_provisions SET v2_applicable_dev_types = %s WHERE id = %s",
                            (list(e["tags"]), rid))
    print(f"  gate {RULE_NAME:<29} to-change={len(changes)}")
    return changes
