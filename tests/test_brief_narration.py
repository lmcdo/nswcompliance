"""Break-it tests for services/brief_templates.py + services/brief_narration.py.

Each test targets a silent wrong result found in the qa-break pass. The worst
class here is a GAP (failed check) rendering as an authoritative-looking fact.
"""

from pathlib import Path

import pytest

from services.brief_manifest import build_manifest
from services.brief_narration import (
    CompositionPlan,
    PlanItem,
    SelectionError,
    generate_overlay,
    overlay_enabled,
    plan_tool_schema,
    render_plan,
    select_composition,
    validate_plan,
    OVERLAY_FLAG_ENV,
)
from services.brief_templates import (
    FLAGGED_TERMS,
    STANDALONE_TEXT,
    TEMPLATES,
    assert_templates_clean,
    label_for_path,
    scan_liability,
)


# ---------------------------------------------------------------------------
# Fixtures — brief with a fact, a queried-empty pair, a gap, and a finding
# ---------------------------------------------------------------------------


def df(value, confidence="authoritative", source="planning_portal",
       as_at="2026-07-14", reason=None):
    return {"value": value, "confidence": confidence, "source": source,
            "as_at": as_at, "reason": reason}


@pytest.fixture()
def brief():
    return {
        "address": "14 Stanley Street, Concord NSW 2137",
        "brief_type": "development",
        "run_date": "2026-07-15",
        "strata": df({"is_strata": False, "strata_type": "not_strata"},
                     source="cadastre_strata"),
        "planning_controls": {
            "zone": df("R3"),
            "height": df("8.5"),
            # two legitimately-empty controls — the dedup trap
            "fsr": df(None),
            "lot_size": df(None),
        },
        "environmental_constraints": {
            "flood_epi": df(None, confidence="not_available",
                            source="postgis_overlays",
                            reason="ConnectionError: overlay query failed"),
        },
        "gaps": [],
        "compound_constraints": [
            {"id": "marginal_lot_size", "severity": "warning",
             "description": "Lot area within 10% of zone minimum.",
             "caveat": "check survey", "data_sources_used": []},
        ],
    }


@pytest.fixture()
def manifest(brief):
    return build_manifest(brief)


def ids(manifest):
    return {e.path: e.id for e in manifest.entries}


def make_plan(*items, headline="T_ZONE_CONTEXT", declined=False):
    return CompositionPlan(
        headline_template=headline,
        items=[PlanItem(**i) for i in items],
        declined=declined,
    )


class FakeClient:
    """Returns queued plan payloads; records requests for assertions."""

    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.requests = []
        outer = self

        class _Messages:
            @staticmethod
            def create(**kwargs):
                outer.requests.append(kwargs)
                payload = outer._payloads.pop(0)

                class R:
                    content = [{"type": "tool_use", "id": "toolu_test",
                                "input": payload}]
                return R()

        self.messages = _Messages()


# ---------------------------------------------------------------------------
# The false-negative class: gaps must never render as facts
# ---------------------------------------------------------------------------


class TestGapNeverRendersAsFact:
    def test_plan_citing_gap_id_under_fact_template_is_rejected(self, manifest):
        gap_id = next(e.id for e in manifest.entries if e.id.startswith("G"))
        plan = make_plan({"template": "T_CONSTRAINT_FLAG", "fields": [gap_id]})
        errors = validate_plan(plan, manifest)
        assert any("G rows" in e or "not usable as facts" in e for e in errors)

    def test_gap_route_with_fact_id_is_rejected(self, manifest):
        m = ids(manifest)
        plan = make_plan({"template": "T_GAP_ROUTE", "fields": [],
                          "gap": m["planning_controls.zone"]})
        errors = validate_plan(plan, manifest)
        assert any("not a G row" in e for e in errors)

    def test_gap_route_renders_reason_and_fallback(self, manifest):
        gap_id = next(e.id for e in manifest.entries if e.id.startswith("G"))
        plan = make_plan(
            {"template": "T_ZONE_CONTEXT",
             "fields": [ids(manifest)["planning_controls.zone"]]},
            {"template": "T_GAP_ROUTE", "fields": [], "gap": gap_id},
        )
        assert validate_plan(plan, manifest) == []
        overlay = render_plan(plan, manifest)
        gap_line = overlay.lines[1].text
        assert "Not checked" in gap_line
        assert "ConnectionError" in gap_line
        assert "NSW planning overlays" in gap_line  # the fallback source, display form


# ---------------------------------------------------------------------------
# Render dedup — cited-entry keying, not text keying
# ---------------------------------------------------------------------------


class TestRenderDedup:
    def test_same_entry_under_two_templates_renders_once(self, manifest):
        zone = ids(manifest)["planning_controls.zone"]
        plan = make_plan(
            {"template": "T_ZONE_CONTEXT", "fields": [zone]},
            {"template": "T_CONTROL_VALUE", "fields": [zone]},
        )
        overlay = render_plan(plan, manifest)
        assert len(overlay.lines) == 1

    def test_two_queried_empty_fields_both_render(self, manifest):
        # Both values render the identical empty marker — text-keyed dedup
        # silently dropped the second field. Key must be the citation set.
        m = ids(manifest)
        plan = make_plan(
            {"template": "T_CONTROL_VALUE", "fields": [m["planning_controls.fsr"]]},
            {"template": "T_CONTROL_VALUE", "fields": [m["planning_controls.lot_size"]]},
        )
        overlay = render_plan(plan, manifest)
        assert len(overlay.lines) == 2
        assert "floor space ratio" in overlay.lines[0].text
        assert "lot size" in overlay.lines[1].text


# ---------------------------------------------------------------------------
# Plan validation contract
# ---------------------------------------------------------------------------


class TestValidatePlan:
    def test_valid_plan_passes(self, manifest):
        m = ids(manifest)
        plan = make_plan(
            {"template": "T_ZONE_CONTEXT",
             "fields": [m["planning_controls.zone"], m["planning_controls.height"]]},
            {"template": "T_FINDING", "fields": [
                next(e.id for e in manifest.entries if e.id.startswith("X"))]},
        )
        assert validate_plan(plan, manifest) == []

    def test_unknown_field_id_rejected(self, manifest):
        plan = make_plan({"template": "T_CONTROL_VALUE", "fields": ["F999"]})
        assert any("F999" in e for e in validate_plan(plan, manifest))

    def test_declined_plan_with_factual_headline_rejected(self, manifest):
        zone = ids(manifest)["planning_controls.zone"]
        plan = make_plan({"template": "T_ZONE_CONTEXT", "fields": [zone]},
                         headline="T_ZONE_CONTEXT", declined=True)
        errors = validate_plan(plan, manifest)
        assert any("declined" in e for e in errors)

    def test_declined_plan_with_scope_decline_headline_passes(self, manifest):
        zone = ids(manifest)["planning_controls.zone"]
        plan = make_plan({"template": "T_ZONE_CONTEXT", "fields": [zone]},
                         headline="T_SCOPE_DECLINE", declined=True)
        assert validate_plan(plan, manifest) == []

    def test_item_count_ceiling_applies_to_declined_plans_too(self, manifest):
        zone = ids(manifest)["planning_controls.zone"]
        items = [{"template": "T_CONTROL_VALUE", "fields": [zone]}] * 11
        plan = make_plan(*items, headline="T_SCOPE_DECLINE", declined=True)
        assert any("1-10 items" in e for e in validate_plan(plan, manifest))

    def test_arity_violation_rejected(self, manifest):
        m = ids(manifest)
        plan = make_plan({"template": "T_CONTROL_VALUE",
                          "fields": [m["planning_controls.zone"],
                                     m["planning_controls.height"]]})
        assert any("takes 1-1" in e for e in validate_plan(plan, manifest))

    def test_tool_schema_enum_constrains_templates(self):
        schema = plan_tool_schema()["input_schema"]
        enum = schema["properties"]["headline_template"]["enum"]
        assert set(enum) == set(TEMPLATES.keys())
        item_enum = schema["properties"]["items"]["items"]["properties"]["template"]["enum"]
        assert set(item_enum) == set(TEMPLATES.keys())


# ---------------------------------------------------------------------------
# Stage-1 retry loop (fake client)
# ---------------------------------------------------------------------------


class TestSelectComposition:
    def test_invalid_first_plan_retried_with_tool_result(self, manifest):
        zone = ids(manifest)["planning_controls.zone"]
        bad = {"headline_template": "T_ZONE_CONTEXT",
               "items": [{"template": "T_CONTROL_VALUE", "fields": ["F999"]}],
               "declined": False}
        good = {"headline_template": "T_ZONE_CONTEXT",
                "items": [{"template": "T_ZONE_CONTEXT", "fields": [zone]}],
                "declined": False}
        client = FakeClient([bad, good])
        plan = select_composition(manifest, persona="homeowner",
                                  intent="renovate", client=client)
        assert plan.items[0].fields == [zone]
        assert len(client.requests) == 2
        # The retry must answer the tool_use with a tool_result (API contract
        # — the live run 400'd without it).
        retry_msgs = client.requests[1]["messages"]
        tool_results = [b for m in retry_msgs if isinstance(m.get("content"), list)
                        for b in m["content"]
                        if isinstance(b, dict) and b.get("type") == "tool_result"]
        assert tool_results and tool_results[0]["is_error"] is True
        assert "F999" in str(tool_results[0]["content"])

    def test_two_invalid_plans_raise_selection_error(self, manifest):
        bad = {"headline_template": "T_ZONE_CONTEXT",
               "items": [{"template": "T_CONTROL_VALUE", "fields": ["F999"]}],
               "declined": False}
        client = FakeClient([bad, bad])
        with pytest.raises(SelectionError):
            select_composition(manifest, persona="homeowner", client=client)

    def test_schema_invalid_payload_retried_then_recovers(self, manifest):
        zone = ids(manifest)["planning_controls.zone"]
        not_even_a_plan = {"totally": "wrong"}
        good = {"headline_template": "T_ZONE_CONTEXT",
                "items": [{"template": "T_ZONE_CONTEXT", "fields": [zone]}],
                "declined": False}
        client = FakeClient([not_even_a_plan, good])
        plan = select_composition(manifest, persona="homeowner", client=client)
        assert plan.items[0].fields == [zone]
        assert len(client.requests) == 2

    def test_response_without_tool_use_raises_selection_error(self, manifest):
        class NoToolClient:
            class messages:
                @staticmethod
                def create(**kw):
                    class R:
                        content = [{"type": "text", "text": "I think..."}]
                    return R()
        with pytest.raises(SelectionError, match="no tool_use"):
            select_composition(manifest, persona="homeowner",
                               client=NoToolClient())

    def test_llm_declined_plan_renders_scope_decline_headline(self, manifest):
        zone = ids(manifest)["planning_controls.zone"]
        plan = make_plan({"template": "T_ZONE_CONTEXT", "fields": [zone]},
                         headline="T_SCOPE_DECLINE", declined=True)
        overlay = render_plan(plan, manifest)
        assert overlay.declined is True
        assert "factual planning data only" in overlay.headline

    def test_unknown_persona_raises_before_any_api_call(self, manifest):
        client = FakeClient([])
        with pytest.raises(SelectionError):
            select_composition(manifest, persona="influencer", client=client)
        assert client.requests == []

    def test_manifest_block_carries_cache_control(self, manifest):
        zone = ids(manifest)["planning_controls.zone"]
        good = {"headline_template": "T_ZONE_CONTEXT",
                "items": [{"template": "T_ZONE_CONTEXT", "fields": [zone]}],
                "declined": False}
        client = FakeClient([good])
        select_composition(manifest, persona="homeowner", client=client)
        system = client.requests[0]["system"]
        assert system[1].get("cache_control") == {"type": "ephemeral"}
        assert manifest.to_prompt_block() in system[1]["text"]


# ---------------------------------------------------------------------------
# Orchestrator — flag, additive-only failure, deterministic mismatch
# ---------------------------------------------------------------------------


class TestGenerateOverlay:
    def test_flag_default_off_returns_none_without_api_call(self, brief, monkeypatch):
        monkeypatch.delenv(OVERLAY_FLAG_ENV, raising=False)
        client = FakeClient([])
        assert generate_overlay(brief, persona="homeowner", intent="renovate",
                                client=client) is None
        assert client.requests == []

    def test_flag_env_true_enables(self, monkeypatch):
        monkeypatch.setenv(OVERLAY_FLAG_ENV, "TRUE")
        assert overlay_enabled() is True
        monkeypatch.setenv(OVERLAY_FLAG_ENV, "yes")  # anything else = off
        assert overlay_enabled() is False

    def test_apartment_build_intent_never_reaches_llm(self, brief):
        brief["brief_type"] = "renovation"
        brief["strata"] = df({"is_strata": True, "strata_type": "apartment"},
                             source="cadastre_strata")
        client = FakeClient([])
        overlay = generate_overlay(brief, persona="homeowner",
                                   intent="granny_flat", enabled=True,
                                   client=client)
        assert overlay is not None and overlay.declined is True
        assert "apartment" in overlay.headline
        assert client.requests == []  # zero LLM calls — the guard is code

    def test_incompatible_overlay_cites_field_not_gap(self, brief):
        # Renovation brief with FAILED strata: incompatible path must not
        # cite the strata GAP row as a fact.
        brief["brief_type"] = "renovation"
        brief["strata"] = df(None, confidence="not_available",
                             source="cadastre_strata", reason="lookup timeout")
        overlay = generate_overlay(brief, persona="homeowner",
                                   intent="duplex", enabled=True,
                                   client=FakeClient([]))
        assert overlay is not None and overlay.declined is True
        assert all(not c.startswith("G") for line in overlay.lines
                   for c in line.citation_ids)

    def test_selection_failure_returns_none_not_error(self, brief):
        class ExplodingClient:
            class messages:
                @staticmethod
                def create(**kw):
                    raise RuntimeError("api down")
        overlay = generate_overlay(brief, persona="homeowner", intent="renovate",
                                   enabled=True, client=ExplodingClient())
        assert overlay is None  # additive-only: brief unaffected, no raise

    def test_unwalkable_brief_returns_none_not_typeerror(self):
        # build_manifest raises TypeError for a wholly unusable input — the
        # orchestrator's last-resort handler must convert it to no-overlay.
        assert generate_overlay("not a brief at all", persona="homeowner",
                                enabled=True, client=FakeClient([])) is None

    def test_review_status_carries_caution(self, brief):
        brief["strata"] = df({"is_strata": True, "strata_type": "development"},
                             source="cadastre_strata")
        m = build_manifest(brief)
        zone = ids(m)["planning_controls.zone"]
        good = {"headline_template": "T_ZONE_CONTEXT",
                "items": [{"template": "T_ZONE_CONTEXT", "fields": [zone]}],
                "declined": False}
        overlay = generate_overlay(brief, persona="homeowner",
                                   intent="granny_flat", enabled=True,
                                   client=FakeClient([good]))
        assert overlay is not None
        assert overlay.caution and "owners-corporation" in overlay.caution


# ---------------------------------------------------------------------------
# Templates — liability and mirror contracts
# ---------------------------------------------------------------------------


class TestTemplates:
    def test_authored_template_text_is_liability_clean(self):
        assert_templates_clean()  # raises on any flagged authored phrase

    def test_flagged_terms_mirror_matches_hook_scanner(self):
        # Load the hook scanner as a module and compare compiled patterns —
        # drift means the overlay gate and the pre-push gate disagree.
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "liability_language_check",
            Path("scripts/liability_language_check.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert FLAGGED_TERMS.pattern == mod.FLAGGED_TERMS.pattern
        assert FLAGGED_TERMS.flags == mod.FLAGGED_TERMS.flags

    def test_scan_liability_catches_advisory_words(self):
        assert scan_liability("this lot is suitable and compliant") == [
            "suitable", "compliant"]
        assert scan_liability("zone R3; height 8.5m") == []

    def test_data_passthrough_flags_logged_not_dropped(self, manifest, brief):
        # A DA status of "approved" is factual source data — the line must
        # render, with the hit recorded on liability_flags. (Scalar value: a
        # dict here would serialise to 'k=v; …' and the record-dump guard
        # now routes those to the section card instead of rendering raw.)
        brief2 = dict(brief)
        brief2["neighbourhood"] = {
            "da_outcomes": df("4 approved of 5 determined",
                              source="da_tracking_mapserver"),
        }
        m2 = build_manifest(brief2)
        da_id = ids(m2)["neighbourhood.da_outcomes"]
        plan = make_plan({"template": "T_NEARBY_ACTIVITY", "fields": [da_id]})
        overlay = render_plan(plan, m2)
        assert "approved" in overlay.lines[0].text
        assert overlay.lines[0].liability_flags == ["approved"]

    def test_record_shaped_value_never_renders_raw(self, manifest, brief):
        # A composite that reaches a generic template as 'k=v; …' must render
        # as the section-card reference, never the raw dump.
        brief2 = dict(brief)
        brief2["neighbourhood"] = {
            "da_outcomes": df({"total": 5, "status_note": "4 approved"},
                              source="da_tracking_mapserver"),
        }
        m2 = build_manifest(brief2)
        da_id = ids(m2)["neighbourhood.da_outcomes"]
        plan = make_plan({"template": "T_NEARBY_ACTIVITY", "fields": [da_id]})
        overlay = render_plan(plan, m2)
        assert "total=" not in overlay.lines[0].text
        assert "status_note=" not in overlay.lines[0].text
        assert "section card below" in overlay.lines[0].text

    def test_label_for_path_humanizes(self):
        assert label_for_path("planning_controls.fsr") == "floor space ratio"
        assert label_for_path("constraint_arithmetic.setback_front_m") == "the front setback"
        assert label_for_path("sepp_housing[3]") == "SEPP housing #3"

    def test_standalone_texts_have_no_unbound_slots(self):
        for tid, text in STANDALONE_TEXT.items():
            # only {options} may appear; a stray slot would KeyError at render
            assert not [s for s in ("{value}", "{label}", "{source}")
                        if s in text], tid


# ---------------------------------------------------------------------------
# Narrative polish (v2 renderer): groups, footnotes, headline, remap
# ---------------------------------------------------------------------------


class TestNarrativePolish:
    def test_fact_plan_headline_empty_no_duplication(self, manifest):
        # Live polish finding: lines[0] used as headline rendered the first
        # sentence twice (header AND body).
        zone = ids(manifest)["planning_controls.zone"]
        plan = make_plan({"template": "T_ZONE_CONTEXT", "fields": [zone]})
        overlay = render_plan(plan, manifest)
        assert overlay.headline == ""
        assert len(overlay.lines) == 1

    def test_computed_source_remapped_from_control_template(self, brief, manifest):
        # A capacity-engine output dressed as "Planning control" must be
        # remapped deterministically, without a model retry.
        brief2 = dict(brief)
        brief2["constraint_arithmetic"] = df(
            {"lep_envelope_gfa_m2": 243.4}, confidence="derived",
            source="constraint_arithmetic_engine")
        from services.brief_manifest import build_manifest as _bm
        m2 = _bm(brief2)
        gfa_id = next(e.id for e in m2.entries
                      if e.path == "constraint_arithmetic.lep_envelope_gfa_m2")
        good = {"headline_template": "T_ZONE_CONTEXT",
                "items": [{"template": "T_CONTROL_VALUE", "fields": [gfa_id]}],
                "declined": False}
        client = FakeClient([good])
        plan = select_composition(m2, persona="homeowner", client=client)
        assert plan.items[0].template == "T_CAPACITY_RESULT"
        overlay = render_plan(plan, m2)
        assert "Computed from the planning controls" in overlay.lines[0].text
        assert "maximum floor area under the LEP envelope" in overlay.lines[0].text

    def test_zone_sentence_reads_as_prose(self, manifest):
        m = ids(manifest)
        plan = make_plan({"template": "T_ZONE_CONTEXT",
                          "fields": [m["planning_controls.zone"],
                                     m["planning_controls.height"]]})
        overlay = render_plan(plan, manifest)
        text = overlay.lines[0].text
        assert text.startswith("This lot is zoned R3")
        assert "a height limit of 8.5" in text
        # provenance moved to footnotes, not inline
        assert "planning_portal" not in text
        assert overlay.lines[0].footnotes == [1]
        assert overlay.footnotes[0].source == "NSW Planning Portal"
        assert overlay.footnotes[0].as_at == "14 Jul 2026"

    def test_footnotes_dedupe_identical_provenance(self, manifest):
        m = ids(manifest)
        plan = make_plan(
            {"template": "T_ZONE_CONTEXT", "fields": [m["planning_controls.zone"]]},
            {"template": "T_CONTROL_VALUE", "fields": [m["planning_controls.height"]]},
        )
        overlay = render_plan(plan, manifest)
        # same (source, as_at, confidence) → ONE footnote shared by both lines
        assert len(overlay.footnotes) == 1
        assert all(line.footnotes == [1] for line in overlay.lines)

    def test_groups_ordered_with_authored_headers(self, manifest):
        m = ids(manifest)
        gap_id = next(e.id for e in manifest.entries if e.id.startswith("G"))
        x_id = next(e.id for e in manifest.entries if e.id.startswith("X"))
        plan = make_plan(
            {"template": "T_FINDING", "fields": [x_id]},
            {"template": "T_ZONE_CONTEXT", "fields": [m["planning_controls.zone"]]},
            {"template": "T_GAP_ROUTE", "fields": [], "gap": gap_id},
        )
        overlay = render_plan(plan, manifest)
        keys = [g.key for g in overlay.groups]
        # deterministic narrative order regardless of plan order
        assert keys == ["planning", "cautions"]
        cautions = overlay.groups[1]
        assert cautions.header == "Worth checking"
        assert len(cautions.lines) == 2  # finding + gap together

    def test_finding_renders_description_with_tone(self, manifest):
        x_id = next(e.id for e in manifest.entries if e.id.startswith("X"))
        plan = make_plan({"template": "T_FINDING", "fields": [x_id]})
        overlay = render_plan(plan, manifest)
        line = overlay.lines[0]
        assert line.tone == "warning"
        assert line.text.startswith("Lot area within 10%")
        assert "severity=" not in line.text

    def test_sepp_record_renders_as_sentence(self, brief):
        from services.brief_manifest import build_manifest as _bm
        brief2 = dict(brief)
        brief2["sepp_housing"] = df(
            [{"dev_type": "secondary_dwelling", "eligible": True,
              "min_lot_area_m2": 450.0, "min_lot_width_m": 12.0,
              "max_gfa_m2": 60.0, "max_height_m": 3.8}],
            source="housing_sepp_standards")
        m = _bm(brief2)
        sepp_id = next(e.id for e in m.entries
                       if e.path == "sepp_housing[0]")
        plan = make_plan({"template": "T_ELIGIBILITY", "fields": [sepp_id]})
        overlay = render_plan(plan, m)
        text = overlay.lines[0].text
        assert text.startswith("Secondary dwelling under SEPP (Housing) 2021")
        assert "meeting the lot standard" in text
        assert "minimum lot area 450.0 m²" in text
        assert "dev_type=" not in text  # no raw record dump

    def test_estimated_confidence_stays_inline(self, brief):
        brief2 = dict(brief)
        brief2["neighbourhood"] = {"shadow_overlap": df(
            "22.2", confidence="estimated", source="shadow_detector")}
        from services.brief_manifest import build_manifest as _bm
        m = _bm(brief2)
        sid = next(e.id for e in m.entries if "shadow_overlap" in e.path)
        plan = make_plan({"template": "T_NEARBY_ACTIVITY", "fields": [sid]})
        overlay = render_plan(plan, m)
        # the qualifier must be IN the sentence, not only in the footnote
        assert "(satellite-estimated)" in overlay.lines[0].text


# ---------------------------------------------------------------------------
# Composite records — authored sentences, never raw 'k=v; …' dumps (#751 batch)
# ---------------------------------------------------------------------------


class TestCompositeRecordSentences:
    def _manifest_with(self, brief, section, key, value, source="postgis_overlays"):
        from services.brief_manifest import build_manifest as _bm
        brief2 = dict(brief)
        brief2[section] = {key: df(value, source=source)}
        return _bm(brief2)

    def test_bushfire_composite_renders_sentence(self, brief):
        m = self._manifest_with(brief, "environmental_constraints", "bushfire", {
            "is_bushfire_prone": True, "category": "Vegetation Buffer",
            "bal_estimate": "BAL-12.5",
        })
        bid = next(e.id for e in m.entries
                   if e.path == "environmental_constraints.bushfire")
        plan = make_plan({"template": "T_CONSTRAINT_FLAG", "fields": [bid]})
        overlay = render_plan(plan, m)
        text = overlay.lines[0].text
        assert "This lot is mapped bush fire prone" in text
        assert "Vegetation Buffer" in text
        assert "indicative BAL-12.5" in text
        assert "is_bushfire_prone=" not in text

    def test_bushfire_not_prone_composite(self, brief):
        m = self._manifest_with(brief, "environmental_constraints", "bushfire", {
            "is_bushfire_prone": False,
        })
        bid = next(e.id for e in m.entries
                   if e.path == "environmental_constraints.bushfire")
        plan = make_plan({"template": "T_CONSTRAINT_FLAG", "fields": [bid]})
        overlay = render_plan(plan, m)
        text = overlay.lines[0].text
        assert "does not list this lot as bush fire prone" in text
        assert "=" not in text

    def test_lot_dimensions_composite_renders_sentence(self, brief):
        m = self._manifest_with(brief, "planning_controls", "lot_dimensions", {
            "area_m2": 8467.2, "frontage_m": 71.3, "depth_m": 121.0,
        }, source="nsw_spatial_services")
        did = next(e.id for e in m.entries
                   if e.path == "planning_controls.lot_dimensions")
        plan = make_plan({"template": "T_CONTROL_VALUE", "fields": [did]})
        overlay = render_plan(plan, m)
        text = overlay.lines[0].text
        assert "The lot is" in text
        assert "×" in text
        assert "area_m2=" not in text
        assert "frontage_m=" not in text

    def test_unknown_record_shape_refuses_raw_render(self, brief):
        m = self._manifest_with(brief, "neighbourhood", "strata_detail", {
            "lottotal": 12, "plan_label": "SP12345",
        }, source="cadastre_strata")
        sid = next(e.id for e in m.entries
                   if e.path == "neighbourhood.strata_detail")
        plan = make_plan({"template": "T_NEARBY_ACTIVITY", "fields": [sid]})
        overlay = render_plan(plan, m)
        text = overlay.lines[0].text
        assert "lottotal=" not in text
        assert "section card below" in text


# ---------------------------------------------------------------------------
# Overlay render defects observed live 2026-07-18 (fused units, raw enum
# tokens, unitless capacity numbers, boolean cautions)
# ---------------------------------------------------------------------------


from services.brief_manifest import EntryKind, ManifestEntry
from services.brief_narration import normalize_plan
from services.brief_templates import (
    _constraint_sentence,
    _dcp_control_sentence,
    humanise_value,
)


def entry(path, value_text, **kw):
    return ManifestEntry(id=kw.pop("id", "F001"), kind=EntryKind.FIELD,
                         path=path, value_text=value_text,
                         confidence=kw.pop("confidence", "authoritative"),
                         source=kw.pop("source", "plotdetect_dcp"), **kw)


class TestDcpControlSentenceUnits:
    def test_unit_gets_a_space(self):
        e = entry("dcp_controls.controls[0]",
                  "control_type=car_parking; value=1; unit=spaces/dwelling; "
                  "dev_type=dwelling_house")
        text = _dcp_control_sentence(e)
        assert "at 1 spaces/dwelling" in text
        assert "1spaces" not in text

    def test_percent_stays_tight(self):
        e = entry("dcp_controls.controls[0]",
                  "control_type=site_coverage; value=50; unit=%")
        assert "at 50%" in _dcp_control_sentence(e)

    def test_no_unit_no_trailing_space(self):
        e = entry("dcp_controls.controls[0]",
                  "control_type=storeys; value=2")
        assert "at 2." in _dcp_control_sentence(e)

    def test_non_numeric_source_ref_says_see_not_clause(self):
        e = entry("dcp_controls.controls[0]",
                  "control_type=car_parking; value=1; unit=spaces/dwelling; "
                  "source_ref=Table 1")
        text = _dcp_control_sentence(e)
        assert "— see Table 1" in text
        assert "clause Table" not in text

    def test_numeric_source_ref_keeps_clause(self):
        e = entry("dcp_controls.controls[0]",
                  "control_type=car_parking; value=1; unit=spaces/dwelling; "
                  "source_ref=4.1.2")
        assert "— clause 4.1.2" in _dcp_control_sentence(e)


class TestMachineTokenHumanisation:
    def test_binding_constraint_enum_never_renders_raw(self):
        e = entry("constraint_arithmetic.binding_constraint", "lep_fsr",
                  source="constraint_arithmetic_engine")
        text = _constraint_sentence(e)
        assert "lep_fsr" not in text
        assert "the LEP floor space ratio" in text

    def test_unknown_snake_token_degrades_to_spaced_words(self):
        assert humanise_value("dcp_rear_lane_width") == "dcp rear lane width"

    def test_ordinary_prose_and_numbers_pass_through(self):
        assert humanise_value("0.6:1") == "0.6:1"
        assert humanise_value("Deferred commencement") == "Deferred commencement"


class TestManifestUnitInference:
    def _manifest(self, key, value):
        return build_manifest({
            "address": "x", "brief_type": "development",
            "constraint_arithmetic": {key: df(
                value, source="constraint_arithmetic_engine",
                confidence="derived")},
        })

    def _value_text(self, m, key):
        return next(e.value_text for e in m.entries
                    if e.path == f"constraint_arithmetic.{key}")

    def test_m2_suffix_field_carries_unit(self):
        assert self._value_text(
            self._manifest("max_gfa_m2", 345.2), "max_gfa_m2") == "345.2 m²"

    def test_m_suffix_field_carries_unit(self):
        assert self._value_text(
            self._manifest("front_setback_m", 6.0),
            "front_setback_m") == "6.0 m"

    def test_unsuffixed_field_stays_bare(self):
        assert self._value_text(
            self._manifest("realistic_dwelling_count", 1),
            "realistic_dwelling_count") == "1"

    def test_string_value_never_gets_a_unit(self):
        assert self._value_text(
            self._manifest("max_gfa_m2", "not computed"),
            "max_gfa_m2") == "not computed"


class TestFactRowUnderFindingTemplate:
    def test_f_id_under_t_finding_remaps_to_fact_renderer(self, manifest):
        fid = next(e.id for e in manifest.entries
                   if e.id.startswith("F"))
        plan = make_plan({"template": "T_FINDING", "fields": [fid]})
        normalize_plan(plan, manifest)
        assert plan.items[0].template == "T_CONSTRAINT_FLAG"

    def test_x_id_under_t_finding_is_untouched(self, manifest):
        xid = next(e.id for e in manifest.entries if e.id.startswith("X"))
        plan = make_plan({"template": "T_FINDING", "fields": [xid]})
        normalize_plan(plan, manifest)
        assert plan.items[0].template == "T_FINDING"

    def test_boolean_fact_renders_as_designation_not_true(self, brief):
        brief["environmental_constraints"]["contaminated_land"] = df(
            True, source="postgis_overlays")
        m = build_manifest(brief)
        cid = next(e.id for e in m.entries
                   if e.path.endswith("contaminated_land"))
        plan = make_plan({"template": "T_FINDING", "fields": [cid]})
        plan = normalize_plan(plan, m)
        overlay = render_plan(plan, m)
        texts = [ln.text for ln in overlay.lines]
        assert not any(t.strip() == "True" for t in texts)
        assert any("designation is recorded" in t for t in texts)
