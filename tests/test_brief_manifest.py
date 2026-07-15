"""Break-it tests for services/brief_manifest.py.

Every test targets a SILENT wrong result found in the qa-break pass — not
crashes. The scenarios mirror the 2026-07-15 live-validation findings:
truncated lists hiding decision-relevant fields, legit-empty rendered as
failure, and the intent×strata guard failing open.
"""

import pytest

from services.brief_manifest import (
    BriefManifest,
    CompatibilityStatus,
    EntryKind,
    Intent,
    QUERIED_EMPTY_MARKER,
    build_manifest,
    check_intent_compatibility,
    _STRATA_AMBIGUOUS,
    _STRATA_APARTMENT,
    _STRATA_DEVELOPMENT,
    _STRATA_NOT_STRATA,
)


# ---------------------------------------------------------------------------
# Fixtures — realistic brief-shaped dicts (mirrors live Concord/Hurstville runs)
# ---------------------------------------------------------------------------


def df(value, confidence="authoritative", source="planning_portal",
       as_at="2026-07-14", reason=None):
    return {"value": value, "confidence": confidence, "source": source,
            "as_at": as_at, "reason": reason}


def house_brief(**overrides):
    brief = {
        "address": "14 Stanley Street, Concord NSW 2137",
        "brief_type": "development",
        "run_date": "2026-07-15",
        "strata": df(
            {"is_strata": False, "strata_type": "not_strata",
             "strata_plan": None, "lot_area_m2": 486.9},
            source="cadastre_strata",
        ),
        "planning_controls": {
            "zone": df("R3"),
            "height": df("8.5"),
            "heritage_items": df([]),
            "permitted_uses": df(["dwelling_houses", "dual_occupancies"],
                                 source="lep_land_use_table"),
        },
        "sepp_housing": df(
            [
                {"dev_type": "dual_occupancy", "eligible": True,
                 "min_lot_area_m2": 450.0, "max_fsr": 0.65},
                {"dev_type": "secondary_dwelling", "eligible": True,
                 "min_lot_area_m2": 450.0},
            ],
            source="housing_sepp_standards",
        ),
        "gaps": [],
        "compound_constraints": [
            {"id": "marginal_lot_size", "severity": "warning",
             "description": "Lot area within 10% of zone minimum.",
             "caveat": "verify with survey", "data_sources_used": []},
        ],
    }
    brief.update(overrides)
    return brief


def apartment_brief(**overrides):
    brief = house_brief(
        brief_type="renovation",
        strata=df(
            {"is_strata": True, "strata_type": "apartment",
             "strata_plan": "SP91614", "lot_area_m2": 1555.0},
            source="cadastre_strata",
        ),
    )
    brief.update(overrides)
    return brief


# ---------------------------------------------------------------------------
# Intent × strata guard — the live-validation S1 failure, now deterministic
# ---------------------------------------------------------------------------


class TestIntentCompatibility:
    def test_apartment_strata_build_intent_is_incompatible(self):
        r = check_intent_compatibility(apartment_brief(), Intent.GRANNY_FLAT)
        assert r.status == CompatibilityStatus.INCOMPATIBLE
        assert r.strata_type == "apartment"
        assert "strata" in (r.reason or "").lower()

    def test_contradictory_strata_record_fails_toward_guard(self):
        # is_strata=False but strata_type says apartment: the guard must win.
        # With the old is_strata-first ordering this returned COMPATIBLE.
        brief = house_brief(strata=df(
            {"is_strata": False, "strata_type": "apartment"},
            source="cadastre_strata",
        ))
        r = check_intent_compatibility(brief, Intent.DUPLEX)
        assert r.status == CompatibilityStatus.INCOMPATIBLE

    def test_enum_strata_type_from_model_dump_still_blocks(self):
        # model_dump() (python mode) keeps StrataType as an enum member; on
        # py3.11+ str(member) is "StrataType.APARTMENT", which used to dodge
        # the string comparison and downgrade the guard to REVIEW.
        from services.intelligence_brief import StrataType
        brief = house_brief(strata=df(
            {"is_strata": True, "strata_type": StrataType.APARTMENT},
            source="cadastre_strata",
        ))
        r = check_intent_compatibility(brief, Intent.GRANNY_FLAT)
        assert r.status == CompatibilityStatus.INCOMPATIBLE

    def test_unknown_strata_classification_is_review_not_compatible(self):
        brief = house_brief(strata=df(
            {"is_strata": True, "strata_type": "community_title"},
            source="cadastre_strata",
        ))
        r = check_intent_compatibility(brief, Intent.SUBDIVIDE)
        assert r.status == CompatibilityStatus.REVIEW

    def test_strata_townhouse_is_review(self):
        brief = house_brief(strata=df(
            {"is_strata": True, "strata_type": "development"},
            source="cadastre_strata",
        ))
        r = check_intent_compatibility(brief, Intent.GRANNY_FLAT)
        assert r.status == CompatibilityStatus.REVIEW

    def test_missing_strata_is_unknown_never_compatible(self):
        brief = house_brief()
        del brief["strata"]
        r = check_intent_compatibility(brief, Intent.KNOCKDOWN_REBUILD)
        assert r.status == CompatibilityStatus.UNKNOWN

    def test_failed_strata_lookup_is_unknown_with_reason(self):
        brief = house_brief(strata=df(
            None, confidence="not_available", source="cadastre_strata",
            reason="TimeoutError: strata lookup did not complete",
        ))
        r = check_intent_compatibility(brief, Intent.GRANNY_FLAT)
        assert r.status == CompatibilityStatus.UNKNOWN
        assert "TimeoutError" in (r.reason or "")

    def test_renovation_brief_without_usable_strata_is_incompatible(self):
        brief = apartment_brief(strata=df(
            None, confidence="not_available", source="cadastre_strata",
            reason="lookup failed",
        ))
        r = check_intent_compatibility(brief, Intent.DUPLEX)
        assert r.status == CompatibilityStatus.INCOMPATIBLE

    def test_non_build_intents_compatible_even_on_apartment(self):
        for intent in (Intent.RENOVATE, Intent.BUY_AND_HOLD, Intent.RESEARCHING):
            r = check_intent_compatibility(apartment_brief(), intent)
            assert r.status == CompatibilityStatus.COMPATIBLE, intent

    def test_freestanding_house_build_intent_compatible(self):
        r = check_intent_compatibility(house_brief(), Intent.GRANNY_FLAT)
        assert r.status == CompatibilityStatus.COMPATIBLE
        assert r.strata_type == "not_strata"

    def test_unknown_intent_raises_value_error(self):
        with pytest.raises(ValueError):
            check_intent_compatibility(house_brief(), "build_a_castle")


# ---------------------------------------------------------------------------
# Three-state mapping — failed vs legit-empty vs present
# ---------------------------------------------------------------------------


class TestThreeState:
    def test_failed_fetch_becomes_gap_not_field(self):
        brief = house_brief()
        brief["environmental_constraints"] = {
            "flood_epi": df(None, confidence="not_available",
                            source="postgis_overlays",
                            reason="ConnectionError: overlay query failed"),
        }
        m = build_manifest(brief)
        gap = [e for e in m.entries
               if e.kind == EntryKind.GAP
               and e.path == "environmental_constraints.flood_epi"]
        assert len(gap) == 1
        assert "ConnectionError" in gap[0].reason
        # And it must NOT also appear as a field (would read as checked-clear).
        assert not any(e.kind == EntryKind.FIELD
                       and e.path == "environmental_constraints.flood_epi"
                       for e in m.entries)

    def test_queried_empty_keeps_confidence_badge(self):
        # value=None with NO reason is the documented legit-empty state — it
        # must render as a FIELD with the original confidence, never as a gap.
        brief = house_brief()
        brief["planning_controls"]["height"] = df(None)
        m = build_manifest(brief)
        row = [e for e in m.entries if e.path == "planning_controls.height"]
        assert len(row) == 1
        assert row[0].kind == EntryKind.FIELD
        assert row[0].value_text == QUERIED_EMPTY_MARKER
        assert row[0].confidence == "authoritative"

    def test_empty_flattened_list_renders_visible_row(self):
        brief = house_brief(sepp_housing=df([], source="housing_sepp_standards"))
        m = build_manifest(brief)
        row = [e for e in m.entries if e.path == "sepp_housing"]
        assert len(row) == 1
        assert "empty" in row[0].value_text

    def test_missing_provenance_omitted_and_warned(self):
        brief = house_brief()
        brief["planning_controls"]["zone"] = {
            "value": "R3", "confidence": None, "source": None,
            "as_at": None, "reason": None,
        }
        m = build_manifest(brief)
        assert not any(e.path == "planning_controls.zone" for e in m.entries)
        assert any("planning_controls.zone" in w for w in m.warnings)


# ---------------------------------------------------------------------------
# Walker correctness
# ---------------------------------------------------------------------------


class TestWalker:
    def test_flattened_sepp_rows_expose_each_standard(self):
        m = build_manifest(house_brief())
        rows = [e for e in m.entries if e.path.startswith("sepp_housing[")]
        assert len(rows) == 2
        assert "dev_type=dual_occupancy" in rows[0].value_text
        assert "dev_type=secondary_dwelling" in rows[1].value_text

    def test_lookalike_record_does_not_fabricate_gap(self):
        # A domain record with 'value' and 'reason' keys is NOT a DataField;
        # the loose shape check used to turn it into a phantom gap.
        brief = house_brief()
        brief["planning_controls"]["notes"] = {
            "value": None, "reason": "varies by lot frontage",
        }
        m = build_manifest(brief)
        assert not any(e.kind == EntryKind.GAP and "notes" in e.path
                       for e in m.entries)

    def test_pipe_in_value_cannot_shift_columns(self):
        brief = house_brief()
        brief["planning_controls"]["height"] = df("6m | 9m corner lots")
        m = build_manifest(brief)
        line = next(l for l in m.to_prompt_block().splitlines()
                    if "planning_controls.height" in l)
        # id | path | value | confidence | source | as_at = exactly 6 cells
        assert len(line.split("|")) == 6
        assert "6m / 9m corner lots" in line

    def test_geometry_paths_excluded(self):
        brief = house_brief()
        brief["planning_controls"]["lot_geometry"] = df("POLYGON((151.1 -33.8, ...))")
        m = build_manifest(brief)
        assert not any("lot_geometry" in e.path for e in m.entries)

    def test_finding_rows_from_compound_constraints(self):
        m = build_manifest(house_brief())
        finds = [e for e in m.entries if e.kind == EntryKind.FINDING]
        assert len(finds) == 1
        assert finds[0].path == "marginal_lot_size"
        assert "severity=warning" in finds[0].value_text
        assert finds[0].id == "X001"

    def test_gap_register_merges_without_duplicates(self):
        # The live Concord run showed the same gap arriving from both the
        # walked DataField and the brief-level register — one row must win.
        brief = house_brief()
        brief["environmental_constraints"] = {
            "coastal_hazards": df(None, confidence="authoritative",
                                  source="sepp_resilience_hazards",
                                  reason="No coastal hazard overlays here"),
        }
        brief["gaps"] = [
            {"field": "environmental_constraints.coastal_hazards",
             "reason": "No coastal hazard overlays here", "verify_url": None},
            {"field": "dcp_controls.landscaping",
             "reason": "council_not_extracted", "verify_url": "https://example.com"},
        ]
        m = build_manifest(brief)
        gaps = [e for e in m.entries if e.kind == EntryKind.GAP]
        paths = [g.path for g in gaps]
        assert paths.count("environmental_constraints.coastal_hazards") == 1
        assert "dcp_controls.landscaping" in paths

    def test_raising_section_isolated_and_warned(self):
        # A section whose traversal raises must be skipped WITH a warning,
        # and every other section must still serialize.
        class Boom(dict):
            def items(self):
                raise RuntimeError("corrupt section payload")

        brief = house_brief()
        brief["economics"] = Boom()
        m = build_manifest(brief)
        assert any(e.path == "planning_controls.zone" for e in m.entries)
        assert any("economics" in w and "RuntimeError" in w for w in m.warnings)

    def test_constraint_arithmetic_struct_expands_per_scalar(self):
        brief = house_brief()
        brief["constraint_arithmetic"] = df(
            {"lot_area_m2": 486.9, "lep_height_m": 8.5, "lep_fsr": 0.5,
             "dev_type": "dwelling_house", "internal_detail": {"x": 1},
             "note": None},
            confidence="derived", source="constraint_arithmetic_engine",
        )
        m = build_manifest(brief)
        rows = {e.path: e.value_text for e in m.entries
                if e.path.startswith("constraint_arithmetic.")}
        # One row per scalar; None and nested-struct keys excluded.
        assert rows == {
            "constraint_arithmetic.dev_type": "dwelling_house",
            "constraint_arithmetic.lep_fsr": "0.5",
            "constraint_arithmetic.lep_height_m": "8.5",
            "constraint_arithmetic.lot_area_m2": "486.9",
        }

    def test_long_unflattened_record_list_shows_overflow_count(self):
        # Non-critical record lists summarise the first N and must SAY how
        # many were held back — silent truncation is the failure mode.
        records = [{"number": f"DA-{i}", "status": "approved"} for i in range(10)]
        brief = house_brief()
        brief["neighbourhood"] = {"nearby_das": df(records, source="eplanning_da_api")}
        m = build_manifest(brief)
        row = next(e for e in m.entries if e.path == "neighbourhood.nearby_das")
        assert row.value_text.startswith("[10 records]")
        assert "+2 more" in row.value_text

    def test_nested_datafield_inside_value_gets_own_row(self):
        # market_context is a DataField whose value struct contains further
        # DataFields — both levels must be visible, outer row first.
        brief = house_brief()
        brief["market_context"] = df(
            {"radius_m": 500,
             "comparables": df({"median_value": 1690000, "comparable_count": 117},
                               confidence="derived", source="nsw_valuer_general")},
            confidence="derived", source="nsw_valuer_general",
        )
        m = build_manifest(brief)
        paths = [e.path for e in m.entries if e.path.startswith("market_context")]
        assert "market_context" in paths
        assert "market_context.comparables" in paths
        assert paths.index("market_context") < paths.index("market_context.comparables")
        inner = next(e for e in m.entries if e.path == "market_context.comparables")
        # money leaves get deterministic $-formatting (digits preserved)
        assert "median_value=$1,690,000" in inner.value_text


# ---------------------------------------------------------------------------
# Determinism and hashing
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_content_different_key_order_same_output(self):
        a = house_brief()
        b = dict(reversed(list(a.items())))
        ma, mb = build_manifest(a), build_manifest(b)
        assert ma.to_prompt_block() == mb.to_prompt_block()
        assert ma.data_hash == mb.data_hash

    def test_hash_ignores_as_at_but_not_values(self):
        base = build_manifest(house_brief())

        redated = house_brief()
        redated["planning_controls"]["zone"] = df("R3", as_at="2026-08-01")
        assert build_manifest(redated).data_hash == base.data_hash

        changed = house_brief()
        changed["planning_controls"]["zone"] = df("R4")
        assert build_manifest(changed).data_hash != base.data_hash

    def test_ids_are_sequential_and_unique(self):
        m = build_manifest(house_brief())
        ids = [e.id for e in m.entries]
        assert len(ids) == len(set(ids))
        fields = [e for e in m.entries if e.kind == EntryKind.FIELD]
        assert fields[0].id == "F001"
        assert m.entry_ids == set(ids)

    def test_prompt_block_has_one_line_per_entry_plus_header(self):
        m = build_manifest(house_brief())
        assert len(m.to_prompt_block().splitlines()) == len(m.entries) + 2


# ---------------------------------------------------------------------------
# Pydantic-model input path (enum handling) + enum mirror contract
# ---------------------------------------------------------------------------


class TestModelInput:
    def test_enum_confidence_renders_value_not_member_repr(self):
        from services.intelligence_brief import ConfidenceLevel, DataField
        brief = house_brief()
        brief["planning_controls"]["zone"] = DataField(
            value="R3", confidence=ConfidenceLevel.AUTHORITATIVE,
            source="planning_portal", as_at="2026-07-14",
        ).model_dump()
        m = build_manifest(brief)
        row = next(e for e in m.entries if e.path == "planning_controls.zone")
        assert row.confidence == "authoritative"
        assert "ConfidenceLevel" not in m.to_prompt_block()

    def test_strata_constant_mirror_matches_source_enum(self):
        from services.intelligence_brief import StrataType
        assert _STRATA_NOT_STRATA == StrataType.NOT_STRATA.value
        assert _STRATA_APARTMENT == StrataType.APARTMENT.value
        assert _STRATA_DEVELOPMENT == StrataType.DEVELOPMENT.value
        assert _STRATA_AMBIGUOUS == StrataType.AMBIGUOUS.value

    def test_build_manifest_rejects_unusable_input(self):
        with pytest.raises(TypeError):
            build_manifest("not a brief")
