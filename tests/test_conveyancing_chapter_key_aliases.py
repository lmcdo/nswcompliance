"""apply_chapter_key_aliases / CHAPTER_KEY_ALIASES — stale chapter_key rename map.

Two things this must prove, per ce-citation-wiring-and-cleanup-PROMPT.md follow-up:
 (a) the 27 manually-verified aliases resolve once their canonical key has a URL
 (b) the merge never invents a URL for a canonical key that isn't present, and
     never overwrites a key the registry already resolved directly.

No DB connection needed — pure dict logic only.
"""

import importlib.util
import os

_spec = importlib.util.spec_from_file_location(
    "conveyancing_db",
    os.path.join(os.path.dirname(__file__), "..", "scripts", "conveyancing_db.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

apply_chapter_key_aliases = _mod.apply_chapter_key_aliases
CHAPTER_KEY_ALIASES = _mod.CHAPTER_KEY_ALIASES


class TestChapterKeyAliasesShape:
    def test_covers_exactly_the_verified_councils(self):
        assert set(CHAPTER_KEY_ALIASES.keys()) == {
            "ashfield", "blacktown", "camden", "campbelltown", "city_of_sydney",
            "fairfield", "hornsby", "leichhardt", "marrickville", "randwick",
            "ryde", "woollahra",
        }

    def test_54_rows_worth_of_aliases_24_distinct_keys(self):
        # 54 blocked dcp_setback_controls rows recovered (measured live), from
        # 24 distinct (lga, source_chapter_key) alias entries across 12 councils.
        total_aliases = sum(len(v) for v in CHAPTER_KEY_ALIASES.values())
        assert total_aliases == 24

    def test_thin_registry_councils_are_absent(self):
        # the_hills and camden's missing parking chapter are missing DATA, not
        # a rename -- must never appear here, or a made-up URL would ship.
        assert "the_hills" not in CHAPTER_KEY_ALIASES
        assert "parking-controls" not in CHAPTER_KEY_ALIASES.get("camden", {})

    def test_ambiguous_multi_candidate_keys_are_absent(self):
        # canterbury_bankstown 'cb-dcp-2023-ch5' could mean ch5-1 or ch5-2 --
        # this council already shipped a wrong-citation defect once
        # (dcp-citation-links.test.ts); never auto-resolve an ambiguous key.
        assert "canterbury_bankstown" not in CHAPTER_KEY_ALIASES
        assert "ku_ring_gai" not in CHAPTER_KEY_ALIASES

    def test_precinct_specific_splits_are_absent(self):
        leichhardt = CHAPTER_KEY_ALIASES.get("leichhardt", {})
        assert "part_c_section_2_balmain" not in leichhardt
        assert "part_c_section_2_birchgrove" not in leichhardt


class TestApplyChapterKeyAliases:
    def test_alias_resolves_when_canonical_has_a_url(self):
        registry = {"part4-s2-multi-dwelling": "https://council.example/x.pdf"}
        result = apply_chapter_key_aliases(registry, "marrickville")
        assert result["part4_s2_mdh_rfb"] == "https://council.example/x.pdf"
        # canonical key itself is untouched
        assert result["part4-s2-multi-dwelling"] == "https://council.example/x.pdf"

    def test_alias_absent_when_canonical_has_no_url(self):
        # Simulates the canonical chapter existing in the registry but with
        # no url at all (all three fallback fields null) -- must NOT invent one.
        registry = {}
        result = apply_chapter_key_aliases(registry, "marrickville")
        assert "part4_s2_mdh_rfb" not in result
        assert "s4.1-low-density-residential" not in result

    def test_never_overwrites_a_key_the_registry_already_resolved(self):
        registry = {
            "part4-s2-multi-dwelling": "CANONICAL_URL",
            "part4_s2_mdh_rfb": "ALREADY_DIRECT_URL",
        }
        result = apply_chapter_key_aliases(registry, "marrickville")
        assert result["part4_s2_mdh_rfb"] == "ALREADY_DIRECT_URL"

    def test_unrelated_council_untouched(self):
        registry = {"some-chapter": "url"}
        assert apply_chapter_key_aliases(registry, "not_a_real_council") == registry

    def test_all_27_aliases_resolve_given_their_canonical_present(self):
        for lga, aliases in CHAPTER_KEY_ALIASES.items():
            canonicals = set(aliases.values())
            registry = {c: f"https://example/{c}.pdf" for c in canonicals}
            result = apply_chapter_key_aliases(registry, lga)
            for alias, canonical in aliases.items():
                assert result[alias] == f"https://example/{canonical}.pdf", (
                    f"{lga}: {alias} -> {canonical} did not resolve"
                )

    def test_original_dict_not_mutated(self):
        registry = {"part4-s2-multi-dwelling": "url"}
        original_keys = set(registry.keys())
        apply_chapter_key_aliases(registry, "marrickville")
        assert set(registry.keys()) == original_keys
