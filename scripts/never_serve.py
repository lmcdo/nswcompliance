"""Council DCP rules that must never be served in a property's main rule list.

The list is data/chapter_scope/never_serve.json (user-approved reviews). Every job that can re-key, re-layer or
switch a rule back on skips these ids: derive_precinct_keys, gate_rules, enrichment/pipeline.py,
dcp_extract_changed, fixes/rerun_actionable_classifier and sync_v2_to_supabase. DQ-148
(scripts/dq_probe_live.py) fails if one is served, by id or -- after a re-read that minted new ids -- by text.

Why a separate list: frontend-nextjs/shared/may-apply-areas.json also names rows that ARE served inside their
mapped outline, so it cannot be the "never" list. Why a file in data/chapter_scope/: Dockerfile.monitors copies
that folder; it does not copy frontend-nextjs/.

prior-art-checked: reuse not viable because data/chapter_scope/not_covered_2026-10-15.json lists ids that are
deliberately keyed and served (Warringah G8/G9, C-B 8.3), so guarding it would un-key good rules.
"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "data" / "chapter_scope" / "never_serve.json"


@lru_cache(maxsize=1)
def entries() -> tuple[dict, ...]:
    """The reviewed entries. A missing or unreadable file RAISES: a guard that silently reads empty guards nothing."""
    doc = json.loads(PATH.read_text(encoding="utf-8"))
    out = tuple(doc["entries"])
    for e in out:
        if len(e["ids"]) != e["expect"]:
            raise ValueError(f"never_serve.json {e['name']}: {len(e['ids'])} ids, expect {e['expect']}")
    return out


def ids() -> frozenset[int]:
    """Every listed row id."""
    return frozenset(i for e in entries() for i in e["ids"])


def text_keys(council: str, chapter_key: str) -> frozenset[str]:
    """Text fingerprints of the listed rules in one chapter: a re-read that mints new ids keeps the same text."""
    return frozenset(h for e in entries() if e["council"] == council and e["chapter_key"] == chapter_key
                     for h in e["text_sha256_16"])


def text_key(text: str | None) -> str:
    """The fingerprint stored in text_sha256_16: lower-case, whitespace collapsed, first 16 hex of sha256."""
    norm = re.sub(r"\s+", " ", text or "").strip().lower()
    return hashlib.sha256(norm.encode()).hexdigest()[:16]
