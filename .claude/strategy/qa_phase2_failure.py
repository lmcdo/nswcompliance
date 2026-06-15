"""
Phase 2: Failure Mode Injection — test how every endpoint degrades.
Tests: timeouts, malformed responses, empty results, boundary coordinates,
invalid geometry, rate limiting simulation, partial data.
"""
import json
import math
import time
import requests
import sys
import os

DA_URL = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/Planning_Portal_Application_Tracking/MapServer/0/query"
VG_LAYER5_URL = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ValuerGeneral/ValuerGeneral_UrbanPropertyValue/MapServer/5/query"
VG_SALES_URL = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ValuerGeneral/ValuerGeneral_UrbanPropertyValue/MapServer/1/query"
STRATA_URL = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Land_Parcel_Property_Theme/FeatureServer/11/query"

results = []

def log_result(name, status, detail=""):
    tag = "[OK]" if status == "PASS" else "[XX]"
    print(f"{tag} {name}")
    if detail and status != "PASS":
        print(f"       {detail}")
    results.append({"name": name, "status": status, "detail": detail})


# ============================================================
# 2.1 — Timeout behaviour (0.001s timeout = instant timeout)
# ============================================================
def test_2_1_timeout_behaviour():
    """Verify requests.Timeout is raised with very short timeout."""
    try:
        resp = requests.get(DA_URL, params={
            "where": "1=1", "outFields": "OBJECTID", "resultRecordCount": 1, "f": "json"
        }, timeout=0.001)
        log_result("Timeout behaviour (0.001s)", "FAIL", "Request succeeded unexpectedly")
    except requests.Timeout:
        log_result("Timeout behaviour (0.001s)", "PASS", "requests.Timeout raised as expected")
    except requests.ConnectionError:
        # ConnectionError also acceptable for instant timeout
        log_result("Timeout behaviour (0.001s)", "PASS", "ConnectionError raised (acceptable for instant timeout)")
    except Exception as e:
        log_result("Timeout behaviour (0.001s)", "FAIL", f"Unexpected exception: {type(e).__name__}: {e}")


# ============================================================
# 2.2 — Invalid geometry (garbage coordinates)
# ============================================================
def test_2_2_invalid_geometry():
    """Send garbage coordinates — should get empty results or error, not crash."""
    # Coordinates in the middle of the Pacific Ocean
    params = {
        "geometry": "-170,-50,-169,-49",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "outFields": "OBJECTID,PLANNING_PORTAL_APP_NUMBER",
        "resultRecordCount": 10,
        "f": "json",
    }
    resp = requests.get(DA_URL, params=params, timeout=8)
    data = resp.json()
    features = data.get("features") or []
    if len(features) == 0:
        log_result("Invalid geometry (Pacific Ocean coords)", "PASS", "0 results as expected")
    else:
        log_result("Invalid geometry (Pacific Ocean coords)", "FAIL", f"Got {len(features)} results from ocean!")


# ============================================================
# 2.3 — Malformed WHERE clause
# ============================================================
def test_2_3_malformed_where():
    """Send SQL syntax error — should get error response, not 200 with bad data."""
    params = {
        "where": "THIS IS NOT VALID SQL @@@ ''' DROP TABLE",
        "outFields": "OBJECTID",
        "resultRecordCount": 1,
        "f": "json",
    }
    resp = requests.get(DA_URL, params=params, timeout=8)
    data = resp.json()
    if "error" in data:
        log_result("Malformed WHERE clause", "PASS", f"Server returned error: {data['error'].get('message','')[:80]}")
    elif len(data.get("features", [])) == 0:
        log_result("Malformed WHERE clause", "PASS", "Server returned 0 features (acceptable)")
    else:
        log_result("Malformed WHERE clause", "FAIL", f"Server returned data despite malformed WHERE: {len(data.get('features',[]))} features")


# ============================================================
# 2.4 — NSW boundary edge: coordinates at state border
# ============================================================
def test_2_4_nsw_boundary_edge():
    """Query at NSW-VIC border — should return results or empty, not error."""
    # Albury-Wodonga area: -36.08, 146.91
    lat, lng = -36.08, 146.91
    r = 0.005
    params = {
        "geometry": f"{lng-r},{lat-r},{lng+r},{lat+r}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "outFields": "OBJECTID,LGA_NAME,ASSESMENT_RESULT",
        "resultRecordCount": 10,
        "f": "json",
    }
    resp = requests.get(DA_URL, params=params, timeout=8)
    data = resp.json()
    if "error" not in data:
        features = data.get("features") or []
        log_result("NSW boundary edge (Albury)", "PASS", f"{len(features)} DAs near border")
    else:
        log_result("NSW boundary edge (Albury)", "FAIL", f"Error at border coords: {data['error']}")


# ============================================================
# 2.5 — VG Layer 5: very large bbox (should be capped by server)
# ============================================================
def test_2_5_vg_large_bbox():
    """Query entire Sydney metro — server should cap at MaxRecordCount."""
    params = {
        "geometry": "150.5,-34.2,151.5,-33.5",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "outFields": "OBJECTID,propid",
        "resultRecordCount": 1000,
        "f": "json",
    }
    resp = requests.get(VG_LAYER5_URL, params=params, timeout=15)
    data = resp.json()
    features = data.get("features") or []
    exceeded = data.get("exceededTransferLimit", False)
    if len(features) > 0:
        log_result("VG large bbox (all Sydney)", "PASS",
                   f"{len(features)} results, exceededTransferLimit={exceeded}")
    else:
        log_result("VG large bbox (all Sydney)", "FAIL", f"0 results for all of Sydney")


# ============================================================
# 2.6 — Empty result set handling (remote location in NSW)
# ============================================================
def test_2_6_empty_results():
    """Query remote NSW outback — expect 0 results, clean empty list."""
    # Tibooburra area: -29.43, 142.01
    lat, lng = -29.43, 142.01
    r = 0.002
    params = {
        "geometry": f"{lng-r},{lat-r},{lng+r},{lat+r}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "outFields": "OBJECTID,propid,address,val1_lv",
        "resultRecordCount": 100,
        "f": "json",
    }
    resp = requests.get(VG_LAYER5_URL, params=params, timeout=8)
    data = resp.json()
    features = data.get("features") or []
    if len(features) == 0 and "error" not in data:
        log_result("Empty results (outback NSW)", "PASS", "Clean empty features list")
    elif len(features) > 0:
        log_result("Empty results (outback NSW)", "PASS", f"Surprisingly got {len(features)} — outback has VG data")
    else:
        log_result("Empty results (outback NSW)", "FAIL", f"Error response: {data.get('error')}")


# ============================================================
# 2.7 — Null/missing field handling in DA outcomes
# ============================================================
def test_2_7_null_fields_da():
    """Query DAs and check how null fields appear — None vs missing key."""
    params = {
        "where": "ASSESMENT_RESULT IS NULL AND LGA_NAME LIKE '%Inner West%'",
        "outFields": "OBJECTID,PLANNING_PORTAL_APP_NUMBER,ASSESMENT_RESULT,DETERMINED_DATE,COST_OF_DEVELOPMENT,X,Y",
        "resultRecordCount": 5,
        "f": "json",
    }
    resp = requests.get(DA_URL, params=params, timeout=8)
    data = resp.json()
    features = data.get("features") or []
    if len(features) == 0:
        log_result("Null field handling (DA outcomes)", "FAIL", "No null-outcome DAs found")
        return

    # Check what null looks like in the response
    attrs = features[0].get("attributes", {})
    null_fields = {k: v for k, v in attrs.items() if v is None}
    missing_fields = [f for f in ["ASSESMENT_RESULT", "DETERMINED_DATE", "COST_OF_DEVELOPMENT"] if f not in attrs]

    detail = f"Null fields: {list(null_fields.keys())}, Missing keys: {missing_fields}"
    log_result("Null field handling (DA outcomes)", "PASS", detail)


# ============================================================
# 2.8 — VG string parsing edge cases (null/zero/empty values)
# ============================================================
def test_2_8_vg_string_edge_cases():
    """Find VG records with edge-case values: null, $0, empty string."""
    params = {
        "where": "val1_lv IS NULL OR val1_lv = '' OR val1_lv LIKE '%$0%'",
        "outFields": "OBJECTID,propid,address,val1_lv,prop_area",
        "resultRecordCount": 5,
        "f": "json",
    }
    resp = requests.get(VG_LAYER5_URL, params=params, timeout=8)
    data = resp.json()
    if "error" in data:
        # Try simpler query
        params["where"] = "val1_lv IS NULL"
        resp = requests.get(VG_LAYER5_URL, params=params, timeout=8)
        data = resp.json()

    features = data.get("features") or []
    if len(features) > 0:
        samples = []
        for f in features[:3]:
            a = f.get("attributes", {})
            samples.append(f"val1_lv={repr(a.get('val1_lv'))}, prop_area={repr(a.get('prop_area'))}")
        log_result("VG string edge cases (null/zero)", "PASS", "; ".join(samples))
    else:
        log_result("VG string edge cases (null/zero)", "PASS", "No null/zero/empty val1_lv records found in sample")


# ============================================================
# 2.9 — Strata: query in area with no strata plans
# ============================================================
def test_2_9_strata_empty_area():
    """Rural area — should return clean empty, not error."""
    # Mudgee area: -32.59, 149.59
    lat, lng = -32.59, 149.59
    params = {
        "geometry": f"{lng},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "outFields": "*",
        "resultRecordCount": 10,
        "f": "json",
    }
    resp = requests.get(STRATA_URL, params=params, timeout=8)
    data = resp.json()
    features = data.get("features") or []
    if "error" not in data:
        log_result("Strata empty area (rural)", "PASS", f"{len(features)} strata plans (expected 0)")
    else:
        log_result("Strata empty area (rural)", "FAIL", f"Error: {data['error']}")


# ============================================================
# 2.10 — DA: WHERE injection attempt via field value
# ============================================================
def test_2_10_injection_attempt():
    """Simulate what would happen if user input reached WHERE clause (it shouldn't, but verify server rejects)."""
    # This tests the ArcGIS server's own defences
    payloads = [
        "LGA_NAME = ''; DROP TABLE--'",
        "LGA_NAME = 'Inner West' OR 1=1",
        "LGA_NAME = 'Inner West'; SELECT * FROM sys.tables--",
    ]
    for payload in payloads:
        params = {
            "where": payload,
            "outFields": "OBJECTID",
            "resultRecordCount": 1,
            "f": "json",
        }
        resp = requests.get(DA_URL, params=params, timeout=8)
        data = resp.json()
        if "error" in data:
            continue  # Good — server rejected it
        features = data.get("features") or []
        if payload == "LGA_NAME = 'Inner West' OR 1=1" and len(features) > 0:
            # OR 1=1 is expected to return results — it's valid SQL, just wider
            continue
        if len(features) > 0 and "DROP" in payload:
            log_result("SQL injection attempt", "FAIL", f"Server accepted dangerous payload: {payload[:50]}")
            return

    log_result("SQL injection attempt", "PASS", "Server rejected/handled all injection payloads")


# ============================================================
# 2.11 — DA date filtering: future date
# ============================================================
def test_2_11_future_date():
    """Filter by a date in the future — should return 0 results."""
    params = {
        "where": "LODGEMENT_DATE >= '20990101' AND LGA_NAME LIKE '%Sydney%'",
        "outFields": "OBJECTID",
        "resultRecordCount": 1,
        "f": "json",
    }
    resp = requests.get(DA_URL, params=params, timeout=8)
    data = resp.json()
    features = data.get("features") or []
    if len(features) == 0:
        log_result("Future date filter", "PASS", "0 results for 2099 as expected")
    else:
        log_result("Future date filter", "FAIL", f"{len(features)} results from the future!")


# ============================================================
# 2.12 — VG: what happens with resultRecordCount=0
# ============================================================
def test_2_12_zero_record_count():
    """Request 0 records — should return empty or error, not default."""
    params = {
        "where": "1=1",
        "outFields": "OBJECTID",
        "resultRecordCount": 0,
        "f": "json",
    }
    resp = requests.get(VG_LAYER5_URL, params=params, timeout=8)
    data = resp.json()
    features = data.get("features") or []
    log_result("Zero resultRecordCount", "PASS",
               f"{len(features)} results (server behaviour documented)")


# ============================================================
# 2.13 — DA aggregation: groupBy with non-existent field
# ============================================================
def test_2_13_invalid_groupby():
    """groupByFieldsForStatistics with fake field — should error cleanly."""
    params = {
        "where": "LGA_NAME LIKE '%Inner West%'",
        "groupByFieldsForStatistics": "FAKE_FIELD_NOT_REAL",
        "outStatistics": json.dumps([{
            "statisticType": "count",
            "onStatisticField": "OBJECTID",
            "outStatisticFieldName": "count"
        }]),
        "f": "json",
    }
    resp = requests.get(DA_URL, params=params, timeout=8)
    data = resp.json()
    if "error" in data:
        log_result("Invalid groupBy field", "PASS", f"Error: {data['error'].get('message','')[:60]}")
    else:
        features = data.get("features") or []
        log_result("Invalid groupBy field", "FAIL", f"Server accepted fake field, {len(features)} groups returned")


# ============================================================
# 2.14 — Concurrent requests to same endpoint
# ============================================================
def test_2_14_concurrent_requests():
    """Fire 5 concurrent requests — all should succeed (tests rate limiting)."""
    import concurrent.futures

    def do_query(i):
        lat_offset = i * 0.001
        params = {
            "geometry": f"151.15,{-33.88 + lat_offset},151.16,{-33.87 + lat_offset}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": 4326,
            "outFields": "OBJECTID",
            "resultRecordCount": 1,
            "f": "json",
        }
        resp = requests.get(DA_URL, params=params, timeout=8)
        return resp.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(do_query, i) for i in range(5)]
        statuses = [f.result() for f in concurrent.futures.as_completed(futures)]

    ok_count = sum(1 for s in statuses if s == 200)
    if ok_count == 5:
        log_result("Concurrent requests (5 parallel)", "PASS", "All 5 returned 200")
    else:
        log_result("Concurrent requests (5 parallel)", "FAIL", f"Only {ok_count}/5 returned 200, statuses: {statuses}")


# ============================================================
# 2.15 — VG: geometry in Web Mercator (3857) coordinates
# ============================================================
def test_2_15_wrong_srid():
    """Send WGS84 coords but claim inSR=3857 — should get 0 results or error."""
    params = {
        "geometry": "151.15,-33.88,151.16,-33.87",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 3857,  # WRONG — these are WGS84 coords
        "outFields": "OBJECTID,propid",
        "resultRecordCount": 10,
        "f": "json",
    }
    resp = requests.get(VG_LAYER5_URL, params=params, timeout=8)
    data = resp.json()
    features = data.get("features") or []
    if len(features) == 0:
        log_result("Wrong SRID (3857 for WGS84 coords)", "PASS", "0 results — server projected to wrong location")
    else:
        log_result("Wrong SRID (3857 for WGS84 coords)", "FAIL",
                   f"Got {len(features)} results despite wrong SRID — dangerous!")


# ============================================================
# 2.16 — Strata: negative epoch timestamp platform safety
# ============================================================
def test_2_16_negative_epoch_platform():
    """Test Python's ability to handle negative epoch timestamps on this platform."""
    import datetime
    test_values = [
        (-31536000000, "Pre-1970"),   # ~1969
        (-946684800000, "1940"),       # 1940
        (0, "Epoch zero"),             # 1970-01-01
        (1718400000000, "2024"),        # Recent
    ]
    failures = []
    for epoch_ms, label in test_values:
        try:
            dt = datetime.datetime.fromtimestamp(epoch_ms / 1000, tz=datetime.timezone.utc)
            if dt.year < 1900 or dt.year > 2100:
                failures.append(f"{label}: {dt} (out of range)")
        except (OSError, OverflowError, ValueError) as e:
            failures.append(f"{label}: {type(e).__name__}: {e}")

    if not failures:
        log_result("Negative epoch platform safety", "PASS", "All epoch values parse correctly on this platform")
    else:
        log_result("Negative epoch platform safety", "FAIL", "; ".join(failures))


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 2: FAILURE MODE INJECTION")
    print("=" * 60)

    tests = [
        test_2_1_timeout_behaviour,
        test_2_2_invalid_geometry,
        test_2_3_malformed_where,
        test_2_4_nsw_boundary_edge,
        test_2_5_vg_large_bbox,
        test_2_6_empty_results,
        test_2_7_null_fields_da,
        test_2_8_vg_string_edge_cases,
        test_2_9_strata_empty_area,
        test_2_10_injection_attempt,
        test_2_11_future_date,
        test_2_12_zero_record_count,
        test_2_13_invalid_groupby,
        test_2_14_concurrent_requests,
        test_2_15_wrong_srid,
        test_2_16_negative_epoch_platform,
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
    print(f"PHASE 2 TOTAL: {passed} PASS / {failed} FAIL / {len(results)} total")
    if failed:
        print(f"\nFAILURES:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  XX {r['name']}: {r['detail']}")
    print("=" * 60)

    out_path = os.path.join(os.path.dirname(__file__), "_phase2_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults written to {out_path}")
