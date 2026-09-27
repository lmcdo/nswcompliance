"""DQ-115's probe: does a declared scope carry the council's own words as DATA?

These are written to be MUTATION-RESISTANT, which for this probe means three
specific wrong answers must each fail a test:

  * `return 0, {}`                  -> a probe that always reads clean
  * ignoring `scope_evidence`       -> counting declarations instead of gaps
  * counting keys that are OMITTED  -> stealing DQ-114's population, so both
                                       rows would move on one fix

It needs no database: the probe reads COUNCIL_CONFIGS, which is a Python dict,
so every case below is a real end-to-end run of the function the ledger calls.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

probe_mod = importlib.import_module("dq_probe_applicability_config")


def count(configs) -> int:
    """Run the real probe over a stand-in COUNCIL_CONFIGS."""
    original = probe_mod.COUNCIL_CONFIGS
    probe_mod.COUNCIL_CONFIGS = configs
    try:
        n, _ = probe_mod.probe_115(None, None)
        return n
    finally:
        probe_mod.COUNCIL_CONFIGS = original


def entry(**kw):
    e = {"layer": "generic"}
    e.update(kw)
    return e


class TestWhatCounts:
    def test_declared_without_evidence_counts(self):
        """The whole point: a scope declared on nobody's recorded authority."""
        assert count({"x": {"chapter_topics": {
            "ch1": entry(applicable_dev_types=["dwelling_house"])}}}) == 1

    def test_both_keys_declared_without_evidence_count_twice(self):
        """Per KEY, not per entry - the same reason DQ-114 counts per key."""
        assert count({"x": {"chapter_topics": {"ch1": entry(
            applicable_dev_types=["ALL"], applicable_zones=["R2"])}}}) == 2  # noqa: zone-codes - test fixture, not a regulatory lookup

    def test_evidence_present_does_not_count(self):
        """Kills the mutant that ignores scope_evidence and counts declarations."""
        assert count({"x": {"chapter_topics": {"ch1": entry(
            applicable_dev_types=["ALL"],
            scope_evidence={"applicable_dev_types":
                            "E3 s1.1.2: 'applies to any development requiring "
                            "development consent under Part 4'"})}}}) == 0

    def test_evidence_for_the_other_key_does_not_excuse_this_one(self):
        """scope_evidence is keyed BY FIELD, so proving zones does not prove
        dev types. An entry-level flag would let one sentence launder both."""
        assert count({"x": {"chapter_topics": {"ch1": entry(
            applicable_dev_types=["ALL"], applicable_zones=["ALL"],
            scope_evidence={"applicable_zones": "A1 s5: 'all lands within the LGA'"},
        )}}}) == 1

    def test_omitted_key_is_not_counted_here(self):
        """An undeclared key is DQ-114's population. Counting it here would put
        one defect under two ids, so a single fix would move both rows and
        neither number would mean anything."""
        assert count({"x": {"chapter_topics": {"ch1": entry()}}}) == 0

    @pytest.mark.parametrize("empty", ["", "   ", None])
    def test_blank_evidence_is_not_evidence(self, empty):
        """A present-but-empty field is the shape that turns a gate into a
        formality - the key exists, so a naive `in` check passes."""
        assert count({"x": {"chapter_topics": {"ch1": entry(
            applicable_zones=["ALL"],
            scope_evidence={"applicable_zones": empty})}}}) == 1


class TestShapeOfTheConfigs:
    def test_aliases_to_the_same_dict_count_once(self):
        """ku_ring_gai/ku-ring-gai, city_of_sydney/sydney_dcp and
        canterbury_bankstown/canterbury-bankstown are separate KEYS pointing at
        ONE dict. Counting by name would report one missing sentence twice, and
        the number would move when an alias was added rather than when the data
        changed."""
        shared = {"chapter_topics": {"ch1": entry(applicable_dev_types=["ALL"])}}
        assert count({"a": shared, "a-hyphenated": shared, "a_third": shared}) == 1

    def test_distinct_dicts_with_equal_content_both_count(self):
        """Identity de-duplication must not collapse two councils that happen to
        be configured the same way - that would hide a real second gap."""
        def make():
            return {"chapter_topics": {"ch1": entry(applicable_dev_types=["ALL"])}}
        assert count({"a": make(), "b": make()}) == 2

    def test_all_three_buckets_are_read(self):
        """`sections` is read although no config uses it YET. Wollongong B1
        states no scope of its own while its sections 4/5/6 each cover a
        different development type, so those entries are covered from the first
        one written rather than after someone remembers to widen this."""
        for bucket in ("chapter_topics", "parts", "sections"):
            assert count({"x": {bucket: {
                "k": entry(applicable_zones=["ALL"])}}}) == 1, bucket

    def test_unknown_bucket_is_ignored(self):
        assert count({"x": {"something_else": {
            "k": entry(applicable_zones=["ALL"])}}}) == 0


class TestItCannotCrashTheLedger:
    """dq_check.py runs this probe. A config being edited must not turn a
    measurement into a traceback, which reads as 'unrunnable' rather than as a
    count."""

    def test_non_dict_entry_is_skipped(self):
        assert count({"x": {"chapter_topics": {
            "ok": entry(applicable_zones=["ALL"]),
            "junk": ["not", "a", "dict"],
            "none": None}}}) == 1

    def test_missing_and_empty_buckets(self):
        assert count({"x": {}}) == 0
        assert count({"x": {"chapter_topics": None}}) == 0
        assert count({}) == 0

    def test_scope_evidence_of_the_wrong_type_is_not_evidence(self):
        """A list or a bare string is not the keyed dict the format specifies,
        so it proves nothing and must still count."""
        for bad in (["a sentence"], "a sentence", 7):
            assert count({"x": {"chapter_topics": {"ch1": entry(
                applicable_zones=["ALL"], scope_evidence=bad)}}}) == 1, bad


class TestRegisteredCorrectly:
    def test_probe_is_registered_as_needing_no_database(self):
        """If DQ-115 were marked needs_db, an unreachable database would make it
        exit 2 - UNKNOWN - on a question the database is never asked."""
        needs_db, fn, headline, means = probe_mod.PROBES["DQ-115"]
        assert needs_db is False
        assert fn is probe_mod.probe_115
        assert headline and means

    def test_the_db_probes_are_still_marked_as_needing_one(self):
        """The 4-tuple was introduced for DQ-115; DQ-102 and DQ-103 must not
        have been silently switched to the no-DB path, which would call them
        with (None, None) and crash."""
        for pid in ("DQ-102", "DQ-103"):
            assert probe_mod.PROBES[pid][0] is True, pid

    def test_real_configs_are_reachable_and_declare_something(self):
        """Guards against the probe reading an empty structure and reporting a
        clean 0 - the 'connected but blind' failure, in config form."""
        n, by_entry = probe_mod.probe_115(None, None)
        declared = sum(
            1
            for cfg in {id(c): c for c in probe_mod.COUNCIL_CONFIGS.values()}.values()
            for bucket in ("chapter_topics", "parts", "sections")
            for e in (cfg.get(bucket) or {}).values()
            if isinstance(e, dict)
            for f in ("applicable_dev_types", "applicable_zones")
            if f in e
        )
        assert declared > 0, "no config declares any scope - probe would read 0"
        assert 0 <= n <= declared
        assert len(by_entry) <= declared
