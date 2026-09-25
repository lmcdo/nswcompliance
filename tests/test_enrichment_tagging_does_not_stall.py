"""One bad config entry must not stop every other row being tagged.

2026-09-25: 45 config entries carried no "layer" (every Canterbury-Bankstown
precinct chapter among them). `entry["layer"]` raised on each of their rows,
the rows stayed NULL, and the enrichment loop -- which refetches `ORDER BY id
LIMIT n` -- fetched the same 500 failing rows seven times and tagged nothing
else. Every chapter committed after that went live without its tags.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from enrichment.config import COUNCIL_CONFIGS  # noqa: E402
from enrichment.extractors.layer_topic_tagger import LayerTopicTagger  # noqa: E402

VALID = {"generic", "use_specific", "condition", "precinct", "heritage"}


# -- the missing layer ---------------------------------------------------------------

@pytest.mark.parametrize("entry,want", [
    ({"layer": "heritage", "is_precinct_specific": True}, "heritage"),   # stated wins
    ({"applicable_zones": ["ALL"], "is_precinct_specific": True}, "precinct"),
    ({"applicable_zones": ["ALL"], "site_conditions": ["flood"]}, "condition"),
    ({"applicable_zones": ["ALL"]}, "generic"),
])
def test_a_missing_layer_is_derived_from_what_the_entry_states(entry, want):
    assert LayerTopicTagger._entry_layer(entry) == want


def test_every_config_entry_resolves_to_a_valid_layer():
    for council, cfg in COUNCIL_CONFIGS.items():
        for group in ("chapter_topics", "parts"):
            for key, entry in (cfg.get(group) or {}).items():
                if isinstance(entry, dict):
                    assert LayerTopicTagger._entry_layer(entry) in VALID, (council, key)


def test_a_canterbury_bankstown_precinct_row_now_tags():
    # The exact document that stalled the loop.
    layer, part, _topic = LayerTopicTagger().tag(
        "Canterbury-Bankstown_DCP_2023__chapter_6_2_bankstown_city_centre",
        "# 3.1 C1 Buildings must be set back 3m from the street.")
    assert layer == "precinct" and part == "chapter_6_2_bankstown_city_centre"


# -- the loop that never moved on ----------------------------------------------------

class _Cur:
    """A fake cursor over one table: a row with id in `bad` makes the tagger raise."""

    def __init__(self, rows):
        self.rows = {r["id"]: dict(r, v2_dcp_layer=None) for r in rows}
        self._res = []

    def execute(self, sql, params=None):
        if sql.strip().upper().startswith("SELECT COUNT"):
            self._res = [{"total": sum(1 for r in self.rows.values() if r["v2_dcp_layer"] is None)}]
        elif sql.strip().upper().startswith("SELECT"):
            skip, limit = (params if len(params) == 2 else ([], params[0]))
            todo = [r for i, r in sorted(self.rows.items())
                    if r["v2_dcp_layer"] is None and i not in skip]
            self._res = todo[:limit]
        elif sql.strip().upper().startswith("UPDATE"):
            layer, _part, _topic, pid = params
            self.rows[pid]["v2_dcp_layer"] = layer

    def fetchone(self):
        return self._res[0]

    def fetchall(self):
        return self._res

    def close(self):
        pass


class _Conn:
    def __init__(self, cur):
        self._cur = cur

    def cursor(self, **_kw):
        return self._cur

    def commit(self):
        pass

    def close(self):
        pass


def test_rows_after_a_failing_batch_are_still_tagged(monkeypatch):
    import enrichment.pipeline as pl

    rows = [{"id": i, "document_id": f"Doc__{i}", "provision_text": "text"} for i in range(1, 6)]
    cur = _Cur(rows)
    monkeypatch.setattr(pl, "get_connection", lambda: _Conn(cur))

    class Tagger:
        def tag(self, doc, text):
            if doc in ("Doc__1", "Doc__2"):     # the two rows whose entry has no layer
                raise KeyError("layer")
            return ("generic", "p", "general")

    monkeypatch.setattr(pl, "LayerTopicTagger", Tagger)
    pl.run_layer_tagging(batch_size=2)
    tagged = {i for i, r in cur.rows.items() if r["v2_dcp_layer"]}
    assert tagged == {3, 4, 5}, "rows after the failing ones were never reached"


# -- Leichhardt part G site keys: rebuilt on every commit, never hand-set ---------------

def test_leichhardt_part_g_site_key_comes_from_the_g_number():
    sys.path.insert(0, str(ROOT / "scripts"))
    import derive_precinct_keys as d
    rule = next(r for r in d.RULES if r["name"] == "leichhardt_g_site_specific")
    key = lambda ref: d._derive(rule["strategy"], {"ref_number": ref})  # noqa: E731
    assert key("Leichhardt_DCP_2013__part_g_s1_site_specific__G10_5_2 O3") == "G10"
    assert key("Leichhardt_DCP_2013__part_g_s1_site_specific__G6 C1") == "G6"
    assert key("Leichhardt_DCP_2013__part_g_s1_site_specific__G12") == "G12"
    # no G-number: left unkeyed, never guessed
    assert key("Leichhardt_DCP_2013__part_g_s1_site_specific__SECTION 3 C19") is None
    assert key("Leichhardt_DCP_2013__part_g_s1_site_specific__C3_1 C5") is None
