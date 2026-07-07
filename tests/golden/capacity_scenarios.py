"""Representative input scenarios for the capacity engine golden/snapshot test.

WHAT THIS IS
------------
``compute_constraint_arithmetic`` is a PURE function (no DB, no API, no I/O). That
lets us freeze its logic against a fixed set of representative inputs and fail the
build whenever a code change alters the output. This is a REGRESSION guard ("did a
change move a number that used to be stable?"), not a correctness oracle — the
frozen answer is whatever the engine currently produces, not a human-certified
truth. To certify truth we run LIVE addresses + the data-integrity checker; those
are separate mechanisms.

WHY ~20 AND NOT 3 MILLION
-------------------------
Every real address flows through the SAME engine code. What varies between
addresses is the *shape* of the inputs (zone tier, missing controls, an override
that does/doesn't apply, tiered/conflicting DCP rows, lot geometry present/absent).
There are only a handful of distinct shapes; one scenario per shape exercises the
same branch three million addresses would. Adding more addresses of the same shape
re-tests an identical code path and tells us nothing new.

INPUTS ARE TEST FIXTURES, OUTPUTS ARE GENERATED
-----------------------------------------------
The numbers below are plausible NSW-shaped test inputs (mirroring the style of
tests/test_setback_conflict_resolution.py) — they are NOT regulatory data served to
users, and no expected OUTPUT is hand-written here. The golden JSON is produced by
running the real engine (see tests/test_capacity_golden.py, UPDATE_GOLDEN=1).

Scenarios tagged (LIVE) mirror an address verified in production; see
memory/project-verified-demo-addresses-2026-06.md.
"""
from __future__ import annotations

from services.constraint_models import (
    DCPControl,
    LotDimensions,
    SEPPStandard,
    SeppLepOverride,
    ShadowResult,
    ShadowScenario,
)


def _dcp(control_type, *, value_min=None, value_max=None,
         dev_type="dwelling_house", unit="m", condition=None):
    return DCPControl(
        control_type=control_type, dev_type=dev_type,
        value_min=value_min, value_max=value_max, unit=unit, condition=condition,
    )


def scenarios() -> list[dict]:
    """Return the ordered list of golden scenarios.

    Each entry: {"name", "description", "kwargs"} where kwargs is passed verbatim
    to compute_constraint_arithmetic(**kwargs).
    """
    out: list[dict] = []

    def add(name, description, **kwargs):
        out.append({"name": name, "description": description, "kwargs": kwargs})

    # 1. Baseline R2 dwelling with full geometry and standard setbacks.
    add(
        "r2_dwelling_basic",
        "R2 dwelling_house, height+FSR present, lot with dims, standard setbacks.",
        lot_area_m2=600.0, dev_type="dwelling_house",
        lep_height_str="8.5m", lep_fsr_str="0.5:1",
        lot_dimensions=LotDimensions(area_m2=600.0, frontage_m=15.0, depth_m=40.0),
        dcp_controls=[
            _dcp("front_setback", value_min=6.0),
            _dcp("rear_setback", value_min=6.0),
            _dcp("side_setback", value_min=0.9),
        ],
    )

    # 2. (LIVE) R3 multi-dwelling — 14 Stanley St, Concord. Range model: a low
    #    as-of-right floor with a higher permitted ceiling form.
    add(
        "r3_multi_dwelling_concord_live",
        "(LIVE 14 Stanley St Concord) R3 multi-dwelling, ceiling form supplied.",
        lot_area_m2=696.0, dev_type="dwelling_house",
        ceiling_dev_type="multi_dwelling_housing",
        lep_height_str="11m", lep_fsr_str="0.6:1",
        lot_dimensions=LotDimensions(area_m2=696.0, frontage_m=15.2, depth_m=45.8),
        dcp_controls=[
            _dcp("front_setback", value_min=6.0),
            _dcp("rear_setback", value_min=6.0),
        ],
    )

    # 3. (LIVE) R2 dual-occ — 17 Corden Ave class. GATE-2b: a dual_occupancy 9.5m
    #    height bonus must NOT inflate a dwelling_house (dev_type mismatch => not
    #    applied). Regression lock on the #519 fix.
    add(
        "gate2b_override_form_mismatch_not_applied",
        "(LIVE 17 Corden class) dual_occupancy 9.5m override must NOT lift a "
        "dwelling_house's height (GATE-2b / PR #519).",
        lot_area_m2=580.0, dev_type="dwelling_house",
        lep_height_str="8.5m", lep_fsr_str="0.5:1",
        lot_dimensions=LotDimensions(area_m2=580.0, frontage_m=14.0, depth_m=41.0),
        sepp_lep_overrides=[
            SeppLepOverride(dev_type="dual_occupancy", control="height",
                            lep_value=8.5, sepp_value=9.5),
        ],
    )

    # 4. Same override, matching dev_type => applied (effective height lifts).
    add(
        "override_form_match_applied",
        "dual_occupancy override applied when dev_type matches (height 8.5 -> 9.5).",
        lot_area_m2=580.0, dev_type="dual_occupancy",
        lep_height_str="8.5m", lep_fsr_str="0.5:1",
        lot_dimensions=LotDimensions(area_m2=580.0, frontage_m=14.0, depth_m=41.0),
        sepp_lep_overrides=[
            SeppLepOverride(dev_type="dual_occupancy", control="height",
                            lep_value=8.5, sepp_value=9.5),
        ],
    )

    # 5. Missing FSR -> height-only envelope + a data gap.
    add(
        "missing_fsr_gap",
        "Height present, FSR absent -> gap surfaced, no FSR envelope.",
        lot_area_m2=600.0, dev_type="dwelling_house",
        lep_height_str="8.5m", lep_fsr_str=None,
        lot_dimensions=LotDimensions(area_m2=600.0, frontage_m=15.0, depth_m=40.0),
    )

    # 6. Missing height -> FSR-only envelope + a data gap.
    add(
        "missing_height_gap",
        "FSR present, height absent -> gap surfaced, no height envelope.",
        lot_area_m2=600.0, dev_type="dwelling_house",
        lep_height_str=None, lep_fsr_str="0.5:1",
        lot_dimensions=LotDimensions(area_m2=600.0, frontage_m=15.0, depth_m=40.0),
    )

    # 7. Missing both LEP controls -> low confidence, two gaps.
    add(
        "missing_both_low_confidence",
        "No LEP height or FSR -> low confidence, both gaps present.",
        lot_area_m2=600.0, dev_type="dwelling_house",
        lep_height_str=None, lep_fsr_str=None,
    )

    # 8. Site-coverage cap (GATE-3) — value_max on max_site_coverage constrains
    #    the footprint.
    add(
        "site_coverage_cap",
        "DCP max_site_coverage cap (GATE-3) applied against lot footprint.",
        lot_area_m2=600.0, dev_type="dwelling_house",
        lep_height_str="8.5m", lep_fsr_str="0.5:1",
        lot_dimensions=LotDimensions(area_m2=600.0, frontage_m=15.0, depth_m=40.0),
        dcp_controls=[
            _dcp("front_setback", value_min=6.0),
            _dcp("max_site_coverage", value_max=50.0, unit="%"),
        ],
    )

    # 9. Conflicting/tiered front setbacks (Burwood 9m AND 15m class) -> the
    #    conservative (largest min) value is chosen AND a gap is flagged.
    add(
        "conflicting_setbacks_conservative",
        "Two front_setback rows (9m, 15m) -> pick 15m (conservative) + flag gap.",
        lot_area_m2=600.0, dev_type="dwelling_house",
        lep_height_str="8.5m", lep_fsr_str="0.5:1",
        lot_dimensions=LotDimensions(area_m2=600.0, frontage_m=15.0, depth_m=40.0),
        dcp_controls=[
            _dcp("front_setback", value_min=9.0),
            _dcp("front_setback", value_min=15.0),
            _dcp("rear_setback", value_min=6.0),
        ],
    )

    # 10. Secondary dwelling (granny flat) with a SEPP GFA cap.
    add(
        "secondary_dwelling_granny",
        "secondary_dwelling with SEPP max_gfa 60m^2 on a small lot.",
        lot_area_m2=450.0, dev_type="secondary_dwelling",
        lep_height_str="8.5m", lep_fsr_str="0.5:1",
        lot_dimensions=LotDimensions(area_m2=450.0, frontage_m=12.0, depth_m=37.5),
        sepp_standards=[
            SEPPStandard(dev_type="secondary_dwelling", eligible=True,
                         min_lot_area_m2=450.0, max_gfa_m2=60.0),
        ],
    )

    # 11. Heritage: SEPP standard present but ineligible (suppressed).
    add(
        "heritage_sepp_ineligible",
        "SEPP standard eligible=False (heritage) -> suppressed, reason carried.",
        lot_area_m2=600.0, dev_type="dwelling_house",
        lep_height_str="8.5m", lep_fsr_str="0.5:1",
        lot_dimensions=LotDimensions(area_m2=600.0, frontage_m=15.0, depth_m=40.0),
        sepp_standards=[
            SEPPStandard(dev_type="secondary_dwelling", eligible=False,
                         reason_ineligible="Heritage item — SEPP pathway excluded"),
        ],
    )

    # 12. Landscaping / deep-soil reduction present.
    add(
        "landscaping_reduction",
        "DCP min_landscaped_area reduction applied to the envelope.",
        lot_area_m2=600.0, dev_type="dwelling_house",
        lep_height_str="8.5m", lep_fsr_str="0.5:1",
        lot_dimensions=LotDimensions(area_m2=600.0, frontage_m=15.0, depth_m=40.0),
        dcp_controls=[
            _dcp("front_setback", value_min=6.0),
            _dcp("min_landscaped_area", value_min=30.0, unit="%"),
        ],
    )

    # 13. Shadow overlap -> storey reduction path.
    add(
        "shadow_storey_reduction",
        "Shadow scenario overlapping the subject lot -> storey reduction path.",
        lot_area_m2=600.0, dev_type="dwelling_house",
        lep_height_str="11m", lep_fsr_str="0.8:1",
        lot_dimensions=LotDimensions(area_m2=600.0, frontage_m=15.0, depth_m=40.0),
        shadow_result=ShadowResult(
            height_m=11.0, height_source="lep",
            scenarios=[
                ShadowScenario(date_label="Jun 21 (winter solstice)",
                               time_label="12:00 PM", shadow_length_m=18.0,
                               overlap_pct=40.0, overlaps_subject_lot=True),
            ],
            worst_case_scenario="Jun 21 12:00 PM",
        ),
    )

    # 14. Parking demand consumes GFA.
    add(
        "parking_consumption",
        "DCP parking requirement consumes buildable GFA.",
        lot_area_m2=800.0, dev_type="multi_dwelling_housing",
        lep_height_str="11m", lep_fsr_str="0.9:1",
        lot_dimensions=LotDimensions(area_m2=800.0, frontage_m=18.0, depth_m=44.0),
        dcp_controls=[
            _dcp("front_setback", value_min=6.0),
            _dcp("parking_spaces", value_min=4.0, unit="spaces"),
        ],
    )

    # 15. Full geometry -> buildable footprint + dcp_adjusted populated.
    add(
        "full_dims_footprint",
        "Lot with frontage+depth -> footprint computed, dcp_adjusted populated.",
        lot_area_m2=700.0, dev_type="dwelling_house",
        lep_height_str="9.5m", lep_fsr_str="0.6:1",
        lot_dimensions=LotDimensions(area_m2=700.0, frontage_m=17.5, depth_m=40.0),
        dcp_controls=[
            _dcp("front_setback", value_min=6.0),
            _dcp("rear_setback", value_min=6.0),
            _dcp("side_setback", value_min=1.0),
        ],
    )

    # 16. Area only, no dims -> dcp_adjusted NOT populated (geometry unreliable).
    add(
        "area_only_no_dims",
        "Lot area but no frontage/depth -> LEP envelope only, no dcp_adjusted.",
        lot_area_m2=700.0, dev_type="dwelling_house",
        lep_height_str="9.5m", lep_fsr_str="0.6:1",
        dcp_controls=[
            _dcp("front_setback", value_min=6.0),
            _dcp("rear_setback", value_min=6.0),
        ],
    )

    # 17. Large lot, high FSR — FSR path vs height path both large.
    add(
        "large_lot_high_fsr",
        "2000m^2 lot, FSR 2:1, height 21m -> large envelope, min(FSR,height).",
        lot_area_m2=2000.0, dev_type="residential_flat_building",
        lep_height_str="21m", lep_fsr_str="2:1",
        lot_dimensions=LotDimensions(area_m2=2000.0, frontage_m=40.0, depth_m=50.0),
        dcp_controls=[_dcp("front_setback", value_min=7.5)],
    )

    # 18. Small tight lot.
    add(
        "small_lot_tight",
        "250m^2 lot, standard R2 controls -> small envelope.",
        lot_area_m2=250.0, dev_type="dwelling_house",
        lep_height_str="8.5m", lep_fsr_str="0.5:1",
        lot_dimensions=LotDimensions(area_m2=250.0, frontage_m=10.0, depth_m=25.0),
        dcp_controls=[
            _dcp("front_setback", value_min=4.5),
            _dcp("rear_setback", value_min=3.0),
        ],
    )

    # 19. Height binds instead of FSR (low height, high FSR).
    add(
        "height_binding_not_fsr",
        "Low height (6m) + high FSR (2:1) -> height path binds, not FSR.",
        lot_area_m2=600.0, dev_type="dwelling_house",
        lep_height_str="6m", lep_fsr_str="2:1",
        lot_dimensions=LotDimensions(area_m2=600.0, frontage_m=15.0, depth_m=40.0),
    )

    # 20. LEP only, no DCP controls at all -> envelope from LEP, no DCP erosion.
    add(
        "lep_only_no_dcp",
        "No DCP controls supplied -> realistic_gfa from LEP, no DCP adjustment.",
        lot_area_m2=600.0, dev_type="dwelling_house",
        lep_height_str="8.5m", lep_fsr_str="0.5:1",
        lot_dimensions=LotDimensions(area_m2=600.0, frontage_m=15.0, depth_m=40.0),
    )

    return out
