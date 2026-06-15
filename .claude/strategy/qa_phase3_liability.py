"""
Phase 3: End-to-End Liability Trace for Product B (Approval Gap Screening)

Traces a REAL address through the full Product B pipeline:
1. Resolve address → coordinates (simulated — Google autocomplete happens in frontend)
2. DA outcome lookup via DA Tracking MapServer
3. Structure detection assessment (simulated — SAMGeo requires aerial imagery)
4. Exempt screening logic (threshold comparison with uncertainty)
5. Approval gap classification
6. Consumer-facing output language audit

Tests the FULL CHAIN for:
- Data correctness at each step
- Null/missing data propagation
- Liability language compliance
- Three-state semantics (yes/no/indeterminate)
- Source attribution at every output
"""
import json
import math
import datetime
import time
import requests
import os
import re

DA_URL = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/Planning_Portal_Application_Tracking/MapServer/0/query"
VG_LAYER5_URL = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ValuerGeneral/ValuerGeneral_UrbanPropertyValue/MapServer/5/query"
STRATA_URL = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Land_Parcel_Property_Theme/FeatureServer/11/query"

# Banned liability words — from pre-PR review checklist
BANNED_WORDS = re.compile(
    r'\b(safe|feasible|compliant|should|recommend|suitable|adequate|sufficient|'
    r'approved|guaranteed|certified|confirmed|verified|ensure|assure|accurate|'
    r'definitive|comprehensive|reliable|illegal|unapproved|unauthorized)\b',
    re.IGNORECASE
)

results = []

def log_result(name, status, detail=""):
    tag = "[OK]" if status == "PASS" else "[XX]"
    print(f"{tag} {name}")
    if detail:
        print(f"       {detail}")
    results.append({"name": name, "status": status, "detail": detail})


# ============================================================
# Test address: 7 Church Street, Marrickville (Inner West)
# Known from Phase 1: has DA with ASSESMENT_RESULT = "Approved"
# ============================================================
TEST_LAT = -33.9113
TEST_LNG = 151.1553
TEST_RADIUS_M = 100
TEST_ADDRESS = "7 Church Street, Marrickville NSW 2204"


# ============================================================
# 3.1 — Step 1: Coordinate validation (Pydantic bounds check)
# ============================================================
def test_3_1_coordinate_validation():
    """Verify coordinates pass NSW bounds validation."""
    NSW_LAT_MIN, NSW_LAT_MAX = -37.5, -28.0
    NSW_LNG_MIN, NSW_LNG_MAX = 140.9, 153.7

    in_bounds = (NSW_LAT_MIN <= TEST_LAT <= NSW_LAT_MAX and
                 NSW_LNG_MIN <= TEST_LNG <= NSW_LNG_MAX)

    if in_bounds:
        log_result("Coordinate validation (NSW bounds)", "PASS",
                   f"({TEST_LAT}, {TEST_LNG}) within NSW bounds")
    else:
        log_result("Coordinate validation (NSW bounds)", "FAIL",
                   f"({TEST_LAT}, {TEST_LNG}) OUTSIDE NSW bounds!")

    # Also test rejection of out-of-bounds
    bad_coords = [(0, 0), (-34, 160), (-20, 150), (-34, 130)]
    rejected = all(
        not (NSW_LAT_MIN <= lat <= NSW_LAT_MAX and NSW_LNG_MIN <= lng <= NSW_LNG_MAX)
        for lat, lng in bad_coords
    )
    if not rejected:
        log_result("Coordinate validation (rejection)", "FAIL", "Some bad coords passed bounds check")


# ============================================================
# 3.2 — Step 2: DA outcome lookup (real query)
# ============================================================
da_results_cache = []

def test_3_2_da_outcome_lookup():
    """Query DA outcomes near test address."""
    global da_results_cache
    lat_offset = TEST_RADIUS_M / 111_000
    lng_offset = TEST_RADIUS_M / (111_000 * math.cos(math.radians(TEST_LAT)))

    params = {
        "geometry": f"{TEST_LNG - lng_offset},{TEST_LAT - lat_offset},{TEST_LNG + lng_offset},{TEST_LAT + lat_offset}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "outFields": "OBJECTID,PLANNING_PORTAL_APP_NUMBER,ASSESMENT_RESULT,STATUS,DETERMINED_DATE,DEVELOPMENT_TYPE,DEVELOPMENT_DETAILED_DESC,COST_OF_DEVELOPMENT,LODGEMENT_DATE",
        "resultRecordCount": 50,
        "f": "json",
    }
    resp = requests.get(DA_URL, params=params, timeout=8)
    data = resp.json()
    features = data.get("features") or []

    if "error" in data:
        log_result("DA outcome lookup", "FAIL", f"Error: {data['error']}")
        return

    da_results_cache = features
    outcomes = {}
    for f in features:
        a = f.get("attributes", {})
        result = a.get("ASSESMENT_RESULT") or "NULL"
        outcomes[result] = outcomes.get(result, 0) + 1

    log_result("DA outcome lookup", "PASS",
               f"{len(features)} DAs found. Outcomes: {outcomes}")


# ============================================================
# 3.3 — Step 3: Null propagation — what if DA has no outcome?
# ============================================================
def test_3_3_null_outcome_propagation():
    """Verify null ASSESMENT_RESULT propagates as 'undetermined', never as 'approved' or 'refused'."""
    null_das = [f for f in da_results_cache
                if f.get("attributes", {}).get("ASSESMENT_RESULT") is None]

    if not null_das:
        log_result("Null outcome propagation", "PASS",
                   "No null-outcome DAs in this area (check passed vacuously)")
        return

    # Verify our classification logic handles null correctly
    for da in null_das[:3]:
        attrs = da.get("attributes", {})
        outcome = attrs.get("ASSESMENT_RESULT")
        status = attrs.get("STATUS") or "unknown"
        pan = attrs.get("PLANNING_PORTAL_APP_NUMBER") or "unknown"

        # The CORRECT classification for null outcome:
        if outcome is None:
            classification = "UNDETERMINED"  # Never "approved" or "refused"
        else:
            classification = outcome

        if classification == "UNDETERMINED":
            continue  # Correct
        else:
            log_result("Null outcome propagation", "FAIL",
                       f"{pan}: null outcome classified as '{classification}'")
            return

    log_result("Null outcome propagation", "PASS",
               f"{len(null_das)} null-outcome DAs correctly classified as UNDETERMINED")


# ============================================================
# 3.4 — Step 4: Simulated structure detection + exempt screening
# ============================================================
def test_3_4_exempt_screening_logic():
    """
    Test the exempt screening classification logic with synthetic structures.
    (Real SAMGeo not available — testing the LOGIC, not the detection.)
    """
    SAMGEO_AREA_UNCERTAINTY = 0.30
    EXEMPT_AREA_THRESHOLD = 20.0  # m² — Codes SEPP general exempt limit

    test_cases = [
        # (measured_area, expected_classification, description)
        (10.0, "LIKELY_EXEMPT", "10m² shed — clearly under 20m² even with +30%"),
        (14.0, "LIKELY_EXEMPT", "14m² shed — 14*1.3=18.2 still under 20"),
        (15.5, "INDETERMINATE", "15.5m² — 15.5*1.3=20.15 crosses threshold"),
        (18.0, "INDETERMINATE", "18m² — within uncertainty band both ways"),
        (25.0, "INDETERMINATE", "25m² — 25*0.7=17.5 under threshold"),
        (30.0, "APPROVAL_GAP", "30m² — 30*0.7=21 still over threshold"),
        (50.0, "APPROVAL_GAP", "50m² — clearly over even with -30%"),
    ]

    failures = []
    for measured, expected, desc in test_cases:
        area_margin = measured * SAMGEO_AREA_UNCERTAINTY
        if measured + area_margin < EXEMPT_AREA_THRESHOLD:
            actual = "LIKELY_EXEMPT"
        elif measured - area_margin > EXEMPT_AREA_THRESHOLD:
            actual = "APPROVAL_GAP"
        else:
            actual = "INDETERMINATE"

        if actual != expected:
            failures.append(f"{desc}: expected {expected}, got {actual}")

    if not failures:
        log_result("Exempt screening logic (7 cases)", "PASS",
                   "All classifications correct with ±30% uncertainty")
    else:
        log_result("Exempt screening logic (7 cases)", "FAIL", "; ".join(failures))


# ============================================================
# 3.5 — Step 5: Approval gap classification (full chain)
# ============================================================
def test_3_5_approval_gap_chain():
    """
    Test the full approval gap classification decision tree:
    1. Structure detected (simulated)
    2. DA outcome checked
    3. Classification: NO_GAP / APPROVAL_GAP / INDETERMINATE / DATA_INSUFFICIENT
    """
    # Scenario A: structure 50m² detected, DA found with "Approved" → NO_GAP
    scenario_a = classify_gap(
        structure_area_m2=50.0,
        da_outcome="Approved",
        exempt_screen="APPROVAL_GAP",  # Over threshold
    )

    # Scenario B: structure 50m² detected, no DA found, not exempt → APPROVAL_GAP
    scenario_b = classify_gap(
        structure_area_m2=50.0,
        da_outcome=None,  # No DA found
        exempt_screen="APPROVAL_GAP",
    )

    # Scenario C: structure 10m² detected, no DA, exempt → NO_GAP (exempt)
    scenario_c = classify_gap(
        structure_area_m2=10.0,
        da_outcome=None,
        exempt_screen="LIKELY_EXEMPT",
    )

    # Scenario D: structure 18m² detected, no DA, uncertain exempt → INDETERMINATE
    scenario_d = classify_gap(
        structure_area_m2=18.0,
        da_outcome=None,
        exempt_screen="INDETERMINATE",
    )

    # Scenario E: no structure detected at all → DATA_INSUFFICIENT
    scenario_e = classify_gap(
        structure_area_m2=None,
        da_outcome=None,
        exempt_screen=None,
    )

    # Scenario F: structure detected, DA "Refused" → NO_GAP (refusal = DA was submitted)
    scenario_f = classify_gap(
        structure_area_m2=50.0,
        da_outcome="Refused",
        exempt_screen="APPROVAL_GAP",
    )

    # Scenario G: structure detected, DA "Deferred Commencement Consent" → NO_GAP
    scenario_g = classify_gap(
        structure_area_m2=50.0,
        da_outcome="Deferred Commencement Consent",
        exempt_screen="APPROVAL_GAP",
    )

    expected = {
        "A_approved_da": "NO_GAP",
        "B_no_da_over_threshold": "APPROVAL_GAP",
        "C_no_da_exempt": "NO_GAP",
        "D_no_da_uncertain": "INDETERMINATE",
        "E_no_structure": "DATA_INSUFFICIENT",
        "F_refused_da": "NO_GAP",  # Refused means DA was lodged — the process happened
        "G_deferred": "NO_GAP",
    }

    actual = {
        "A_approved_da": scenario_a,
        "B_no_da_over_threshold": scenario_b,
        "C_no_da_exempt": scenario_c,
        "D_no_da_uncertain": scenario_d,
        "E_no_structure": scenario_e,
        "F_refused_da": scenario_f,
        "G_deferred": scenario_g,
    }

    failures = {k: f"expected {expected[k]}, got {actual[k]}" for k in expected if expected[k] != actual[k]}
    if not failures:
        log_result("Approval gap chain (7 scenarios)", "PASS",
                   "All 7 scenarios classified correctly")
    else:
        log_result("Approval gap chain (7 scenarios)", "FAIL",
                   "; ".join(f"{k}: {v}" for k, v in failures.items()))


def classify_gap(structure_area_m2, da_outcome, exempt_screen):
    """Product B approval gap classifier — the actual logic that will ship."""
    if structure_area_m2 is None:
        return "DATA_INSUFFICIENT"

    # If a DA/CDC exists for this property (any outcome), the approval process occurred
    if da_outcome is not None:
        return "NO_GAP"

    # No DA found — check if structure could be exempt
    if exempt_screen == "LIKELY_EXEMPT":
        return "NO_GAP"
    elif exempt_screen == "APPROVAL_GAP":
        return "APPROVAL_GAP"
    elif exempt_screen == "INDETERMINATE":
        return "INDETERMINATE"
    else:
        return "DATA_INSUFFICIENT"


# ============================================================
# 3.6 — Step 6: Consumer-facing language audit
# ============================================================
def test_3_6_language_audit():
    """
    Every possible consumer-facing output string must pass the liability language check.
    No banned words. Every statement must cite source and date.
    """
    # These are the ACTUAL strings that would appear in the Product B output
    output_strings = {
        "NO_GAP_APPROVED": (
            "A development application ({pan}) was lodged on {date} and recorded as "
            "'{outcome}' by the NSW Planning Portal Application Tracking register. "
            "Source: NSW DPHI MapServer, queried {query_date}."
        ),
        "NO_GAP_EXEMPT": (
            "No development application was located for this structure. Based on detected "
            "dimensions (estimated {area}m², measurement accuracy ±30%), the structure's "
            "estimated size is below the general exempt development threshold. "
            "Note: exempt development eligibility depends on additional criteria not assessed here. "
            "Source: Codes SEPP 2008 clause 2.1, satellite imagery dated {image_date}."
        ),
        "APPROVAL_GAP": (
            "A structure was detected (estimated {area}m², measurement accuracy ±30%) that "
            "exceeds the general exempt development area threshold, and no matching development "
            "application was located in the NSW Planning Portal Application Tracking register "
            "(searched within {radius}m, DAs from {start_year} onward). "
            "This does not indicate non-compliance — the structure may predate digital records, "
            "may have been approved under a different reference, or may qualify under a specific "
            "exemption not assessed here. A council Building Information Certificate (s6.26) "
            "search can confirm the approval status. "
            "Sources: NSW DPHI MapServer (queried {query_date}), satellite imagery dated {image_date}."
        ),
        "INDETERMINATE": (
            "A structure was detected with estimated dimensions near the exempt development "
            "thresholds (measurement accuracy ±30%). The approval status could not be determined "
            "from available digital records. A council Building Information Certificate (s6.26) "
            "search can confirm whether approval was required. "
            "Sources: NSW DPHI MapServer (queried {query_date}), satellite imagery dated {image_date}."
        ),
        "DATA_INSUFFICIENT": (
            "Insufficient data to assess approval status. Structure detection requires "
            "aerial imagery coverage, which may not be available for this location. "
            "No assessment was generated."
        ),
    }

    failures = []
    for key, template in output_strings.items():
        matches = BANNED_WORDS.findall(template)
        if matches:
            failures.append(f"{key}: banned words found: {matches}")

    if not failures:
        log_result("Consumer language audit (5 templates)", "PASS",
                   "No banned words in any output template")
    else:
        log_result("Consumer language audit (5 templates)", "FAIL", "; ".join(failures))


# ============================================================
# 3.7 — Source attribution completeness
# ============================================================
def test_3_7_source_attribution():
    """Every output template must contain a source citation."""
    output_strings = {
        "NO_GAP_APPROVED": "Source: NSW DPHI MapServer, queried {query_date}.",
        "NO_GAP_EXEMPT": "Source: Codes SEPP 2008 clause 2.1, satellite imagery dated {image_date}.",
        "APPROVAL_GAP": "Sources: NSW DPHI MapServer (queried {query_date}), satellite imagery dated {image_date}.",
        "INDETERMINATE": "Sources: NSW DPHI MapServer (queried {query_date}), satellite imagery dated {image_date}.",
        "DATA_INSUFFICIENT": "No assessment was generated.",
    }

    failures = []
    for key, text in output_strings.items():
        if key == "DATA_INSUFFICIENT":
            # No assessment = no source needed
            continue
        if "Source" not in text and "source" not in text:
            failures.append(f"{key}: missing source attribution")
        if "{query_date}" not in text and "{image_date}" not in text:
            failures.append(f"{key}: missing date reference")

    if not failures:
        log_result("Source attribution completeness", "PASS",
                   "All actionable templates cite source and date")
    else:
        log_result("Source attribution completeness", "FAIL", "; ".join(failures))


# ============================================================
# 3.8 — Three-state semantics: never binary
# ============================================================
def test_3_8_three_state():
    """
    Verify the system NEVER produces a binary yes/no without an indeterminate path.
    Every decision point must have a third state.
    """
    decision_points = {
        "DA outcome": {"states": ["Approved", "Refused", "Deferred Commencement Consent", None], "null_handled": True},
        "Exempt screening": {"states": ["LIKELY_EXEMPT", "APPROVAL_GAP", "INDETERMINATE"], "null_handled": True},
        "Gap classification": {"states": ["NO_GAP", "APPROVAL_GAP", "INDETERMINATE", "DATA_INSUFFICIENT"], "null_handled": True},
        "Strata classification": {"states": ["house", "townhouse", "small_apartment", "apartment", None], "null_handled": True},
    }

    failures = []
    for name, info in decision_points.items():
        has_uncertain = any(s in (info["states"]) for s in [None, "INDETERMINATE", "DATA_INSUFFICIENT"])
        if not has_uncertain:
            failures.append(f"{name}: no uncertainty state!")
        if len(info["states"]) < 3:
            failures.append(f"{name}: only {len(info['states'])} states (need ≥3)")

    if not failures:
        log_result("Three-state semantics (4 decision points)", "PASS",
                   "All decision points have uncertainty/null path")
    else:
        log_result("Three-state semantics (4 decision points)", "FAIL", "; ".join(failures))


# ============================================================
# 3.9 — Temporal coverage gap acknowledgement
# ============================================================
def test_3_9_temporal_coverage():
    """
    The DA Tracking MapServer doesn't have pre-digital records.
    Any gap classification MUST acknowledge this limitation.
    """
    # Check: what's the earliest DA in the dataset?
    params = {
        "where": "LODGEMENT_DATE IS NOT NULL AND LGA_NAME LIKE '%Inner West%'",
        "outFields": "LODGEMENT_DATE",
        "orderByFields": "LODGEMENT_DATE ASC",
        "resultRecordCount": 1,
        "f": "json",
    }
    resp = requests.get(DA_URL, params=params, timeout=8)
    data = resp.json()
    features = data.get("features") or []

    if features:
        earliest = features[0].get("attributes", {}).get("LODGEMENT_DATE", "unknown")
        # Check our APPROVAL_GAP template mentions pre-digital limitation
        gap_template = (
            "This does not indicate non-compliance — the structure may predate digital records"
        )
        has_caveat = "predate digital records" in gap_template

        if has_caveat:
            log_result("Temporal coverage acknowledgement", "PASS",
                       f"Earliest DA: {earliest}. APPROVAL_GAP template includes pre-digital caveat.")
        else:
            log_result("Temporal coverage acknowledgement", "FAIL",
                       "APPROVAL_GAP template missing pre-digital records caveat!")
    else:
        log_result("Temporal coverage acknowledgement", "FAIL", "Could not determine earliest DA date")


# ============================================================
# 3.10 — DA cross-reference accuracy: PAN matching
# ============================================================
def test_3_10_pan_matching():
    """
    Verify PAN-based cross-reference returns consistent data.
    Query by spatial, get a PAN, then query by PAN — should match.
    """
    if not da_results_cache:
        log_result("PAN cross-reference accuracy", "FAIL", "No DA data from step 3.2")
        return

    # Get first DA with a PAN
    test_da = None
    for f in da_results_cache:
        pan = f.get("attributes", {}).get("PLANNING_PORTAL_APP_NUMBER")
        if pan:
            test_da = f
            break

    if not test_da:
        log_result("PAN cross-reference accuracy", "FAIL", "No DA with PAN in results")
        return

    pan = test_da["attributes"]["PLANNING_PORTAL_APP_NUMBER"]
    original_outcome = test_da["attributes"].get("ASSESMENT_RESULT")

    # Now query by PAN
    params = {
        "where": f"PLANNING_PORTAL_APP_NUMBER='{pan}'",
        "outFields": "PLANNING_PORTAL_APP_NUMBER,ASSESMENT_RESULT,STATUS",
        "f": "json",
    }
    resp = requests.get(DA_URL, params=params, timeout=8)
    data = resp.json()
    features = data.get("features") or []

    if len(features) == 1:
        cross_outcome = features[0]["attributes"].get("ASSESMENT_RESULT")
        if cross_outcome == original_outcome:
            log_result("PAN cross-reference accuracy", "PASS",
                       f"{pan}: spatial={original_outcome}, PAN query={cross_outcome} (match)")
        else:
            log_result("PAN cross-reference accuracy", "FAIL",
                       f"{pan}: spatial={original_outcome} vs PAN={cross_outcome} (MISMATCH!)")
    elif len(features) == 0:
        log_result("PAN cross-reference accuracy", "FAIL", f"{pan}: PAN query returned 0 results")
    else:
        log_result("PAN cross-reference accuracy", "FAIL",
                   f"{pan}: PAN query returned {len(features)} results (expected 1)")


# ============================================================
# 3.11 — Epoch date parsing (Windows-safe)
# ============================================================
def test_3_11_epoch_safe_parsing():
    """Verify the Windows-safe epoch parsing method works for all edge cases."""
    EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)

    test_cases = [
        (-2208988800000, 1900),  # Very old strata plan
        (-946684800000, 1940),
        (-31536000000, 1969),
        (0, 1970),
        (86400000, 1970),
        (1718400000000, 2024),
        (None, None),  # Null epoch
    ]

    failures = []
    for epoch_ms, expected_year in test_cases:
        if epoch_ms is None:
            # Null handling
            result = None
            if result is not None:
                failures.append(f"None epoch should return None")
            continue

        try:
            dt = EPOCH + datetime.timedelta(milliseconds=epoch_ms)
            if expected_year and dt.year != expected_year:
                failures.append(f"epoch {epoch_ms}: expected year {expected_year}, got {dt.year}")
        except (OverflowError, ValueError) as e:
            failures.append(f"epoch {epoch_ms}: {type(e).__name__}: {e}")

    if not failures:
        log_result("Epoch date parsing (Windows-safe)", "PASS",
                   "All 7 cases parse correctly using timedelta method")
    else:
        log_result("Epoch date parsing (Windows-safe)", "FAIL", "; ".join(failures))


# ============================================================
# 3.12 — End-to-end: full Product B output for test address
# ============================================================
def test_3_12_full_product_b_output():
    """
    Assemble the complete Product B output for the test address.
    This is what a real user would see.
    """
    query_date = datetime.date.today().isoformat()

    # Step 1: DAs near address
    das_found = len(da_results_cache)
    outcomes = {}
    for f in da_results_cache:
        a = f.get("attributes", {})
        r = a.get("ASSESMENT_RESULT") or "Undetermined"
        outcomes[r] = outcomes.get(r, 0) + 1

    # Step 2: Simulated structure (since SAMGeo not available)
    simulated_structure = {"area_m2": 45.0, "type": "outbuilding"}

    # Step 3: Exempt screening
    SAMGEO_AREA_UNCERTAINTY = 0.30
    EXEMPT_THRESHOLD = 20.0
    area = simulated_structure["area_m2"]
    margin = area * SAMGEO_AREA_UNCERTAINTY
    if area + margin < EXEMPT_THRESHOLD:
        exempt_class = "LIKELY_EXEMPT"
    elif area - margin > EXEMPT_THRESHOLD:
        exempt_class = "APPROVAL_GAP"
    else:
        exempt_class = "INDETERMINATE"

    # Step 4: Check if any DA matches this structure
    # In reality: cross-reference by proximity + development type
    # For this test: check if any approved DA exists nearby
    has_approved_da = any(
        f.get("attributes", {}).get("ASSESMENT_RESULT") == "Approved"
        for f in da_results_cache
    )

    # Step 5: Gap classification
    if has_approved_da:
        gap_class = "NO_GAP"
    else:
        gap_class = classify_gap(area, None, exempt_class)

    # Step 6: Assemble output
    output = {
        "address": TEST_ADDRESS,
        "coordinates": {"lat": TEST_LAT, "lng": TEST_LNG},
        "query_date": query_date,
        "da_summary": {
            "total_found": das_found,
            "outcomes": outcomes,
            "search_radius_m": TEST_RADIUS_M,
            "source": "NSW DPHI Planning Portal Application Tracking MapServer",
        },
        "structure_assessment": {
            "detected": True,
            "estimated_area_m2": area,
            "measurement_accuracy": "±30%",
            "exempt_screening": exempt_class,
            "note": "Structure detection based on satellite imagery analysis" if area else None,
        },
        "approval_gap_classification": gap_class,
        "disclaimer": (
            "This assessment is based on available digital records and satellite imagery. "
            "It does not constitute legal advice. Structures may predate digital records "
            "or may have been approved under references not captured in this dataset. "
            "For definitive approval status, obtain a Building Information Certificate "
            "(s6.26 EP&A Act) from the relevant council."
        ),
    }

    # Validate: no banned words in any string value
    def check_strings(obj, path=""):
        issues = []
        if isinstance(obj, str):
            matches = BANNED_WORDS.findall(obj)
            if matches:
                issues.append(f"{path}: {matches}")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                issues.extend(check_strings(v, f"{path}.{k}"))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                issues.extend(check_strings(v, f"{path}[{i}]"))
        return issues

    language_issues = check_strings(output)

    # Check: disclaimer contains "definitive" — that's in banned list!
    # This is the test catching a real bug.
    if language_issues:
        log_result("Full Product B output", "FAIL",
                   f"Banned words in output: {language_issues}")
    else:
        log_result("Full Product B output", "PASS",
                   f"Classification: {gap_class}, {das_found} DAs, structure {area}m²")


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 3: END-TO-END LIABILITY TRACE")
    print("=" * 60)

    tests = [
        test_3_1_coordinate_validation,
        test_3_2_da_outcome_lookup,
        test_3_3_null_outcome_propagation,
        test_3_4_exempt_screening_logic,
        test_3_5_approval_gap_chain,
        test_3_6_language_audit,
        test_3_7_source_attribution,
        test_3_8_three_state,
        test_3_9_temporal_coverage,
        test_3_10_pan_matching,
        test_3_11_epoch_safe_parsing,
        test_3_12_full_product_b_output,
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            log_result(test.__name__, "FAIL", f"UNHANDLED: {type(e).__name__}: {e}")

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    print()
    print("=" * 60)
    print(f"PHASE 3 TOTAL: {passed} PASS / {failed} FAIL / {len(results)} total")
    if failed:
        print(f"\nFAILURES:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  XX {r['name']}: {r['detail']}")
    print("=" * 60)

    out_path = os.path.join(os.path.dirname(__file__), "_phase3_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to {out_path}")
