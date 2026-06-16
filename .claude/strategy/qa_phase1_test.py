"""
TIER 1 BUILD SPEC — QA Phase 1: Live-Fire Tests
Every query pattern in the spec tested against live endpoints.
"""
import requests
import json
import time
import math
import sys
from datetime import datetime

DA_URL = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/Planning_Portal_Application_Tracking/MapServer/0/query"
VG_URL = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer/5/query"
VG_SALES_URL = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer/1/query"
STRATA_URL = "https://portal.spatial.nsw.gov.au/server/rest/services/StrataHub/FeatureServer/0/query"

results = []


def test(name, fn):
    try:
        ok, detail = fn()
        status = "PASS" if ok else "FAIL"
    except Exception as e:
        status = "FAIL"
        detail = f"EXCEPTION: {type(e).__name__}: {e}"
    results.append({"name": name, "status": status, "detail": str(detail)[:500]})
    marker = "OK" if status == "PASS" else "XX"
    print(f"[{marker}] {name}")
    if status == "FAIL":
        print(f"       {detail[:200]}")


# ======================================================================
# 1. DA TRACKING MAPSERVER
# ======================================================================

def t1_1():
    """DA spatial buffer query (primary pattern)"""
    params = {
        "geometry": "151.15,-33.91",
        "geometryType": "esriGeometryPoint",
        "spatialRel": "esriSpatialRelIntersects",
        "distance": "200",
        "units": "esriSRUnit_Meter",
        "outFields": "PLANNING_PORTAL_APP_NUMBER,ASSESMENT_RESULT,PRIMARY_ADDRESS,LODGEMENT_DATE,DETERMINED_DATE,TYPE_OF_DEVELOPMENT,DWELLINGS_TO_BE_CONSTRUCTED,COST_OF_DEVELOPMENT,X,Y",
        "resultRecordCount": 10,
        "f": "json",
        "inSR": "4283",
    }
    r = requests.get(DA_URL, params=params, timeout=10)
    d = r.json()
    feats = d.get("features") or []
    if not feats:
        return False, "No features returned for Marrickville 200m buffer"
    a = feats[0]["attributes"]
    for key in ["PLANNING_PORTAL_APP_NUMBER", "ASSESMENT_RESULT", "PRIMARY_ADDRESS"]:
        if key not in a:
            return False, f"Missing field: {key}"
    return True, f"{len(feats)} DAs found"


def t1_2():
    """DA cross-reference by PAN number"""
    params = {
        "where": "PLANNING_PORTAL_APP_NUMBER='PAN-123967'",
        "outFields": "PLANNING_PORTAL_APP_NUMBER,ASSESMENT_RESULT,PRIMARY_ADDRESS,DA_NUMBER",
        "f": "json",
    }
    r = requests.get(DA_URL, params=params, timeout=10)
    d = r.json()
    feats = d.get("features") or []
    if len(feats) != 1:
        return False, f"Expected 1 result, got {len(feats)}"
    a = feats[0]["attributes"]
    if a["ASSESMENT_RESULT"] != "Approved":
        return False, f"Expected Approved, got {a['ASSESMENT_RESULT']}"
    return True, f"{a['PRIMARY_ADDRESS']} = {a['ASSESMENT_RESULT']}"


def t1_3():
    """DA date filtering (lexicographic string comparison)"""
    params = {
        "where": "LODGEMENT_DATE >= '20240101' AND LGA_NAME LIKE '%Inner West%' AND ASSESMENT_RESULT='Refused'",
        "outFields": "PLANNING_PORTAL_APP_NUMBER,LODGEMENT_DATE,ASSESMENT_RESULT",
        "resultRecordCount": 5,
        "f": "json",
    }
    r = requests.get(DA_URL, params=params, timeout=10)
    d = r.json()
    if "error" in d:
        return False, f"Date filter query failed: {d['error']}"
    feats = d.get("features") or []
    for f in feats:
        dt = f["attributes"].get("LODGEMENT_DATE") or ""
        if dt and dt[:8] < "20240101":
            return False, f"Date filter leak: {dt}"
    return True, f"{len(feats)} refused DAs since 2024 in Inner West"


def t1_4():
    """DA refusal rate aggregation (groupByFieldsForStatistics)"""
    params = {
        "where": "LGA_NAME LIKE '%Inner West%' AND LODGEMENT_DATE >= '20210101'",
        "groupByFieldsForStatistics": "ASSESMENT_RESULT",
        "outStatistics": json.dumps(
            [{"statisticType": "count", "onStatisticField": "OBJECTID", "outStatisticFieldName": "cnt"}]
        ),
        "f": "json",
    }
    r = requests.get(DA_URL, params=params, timeout=10)
    d = r.json()
    if "error" in d:
        return False, f"Stats query failed: {d['error']}"
    feats = d.get("features") or []
    counts = {(f["attributes"].get("ASSESMENT_RESULT") or "NULL"): f["attributes"]["cnt"] for f in feats}
    if "Approved" not in counts:
        return False, f"No Approved count. Got: {counts}"
    total = sum(v for k, v in counts.items() if k != "NULL")
    refused = counts.get("Refused") or 0
    rate = refused / total if total > 0 else 0
    return True, f"Inner West 2021+: {counts}, refusal rate={rate:.1%}"


def t1_5():
    """DA date format audit (inconsistent lengths)"""
    params = {
        "where": "PLANNING_PORTAL_APP_NUMBER IN ('PAN-123967','PAN-125598')",
        "outFields": "PLANNING_PORTAL_APP_NUMBER,LODGEMENT_DATE,DETERMINED_DATE",
        "f": "json",
    }
    r = requests.get(DA_URL, params=params, timeout=10)
    d = r.json()
    feats = d.get("features") or []
    formats_seen = {}
    for f in feats:
        a = f["attributes"]
        pan = a["PLANNING_PORTAL_APP_NUMBER"]
        for field in ["LODGEMENT_DATE", "DETERMINED_DATE"]:
            val = a.get(field) or ""
            if val:
                formats_seen[f"{pan}.{field}"] = f"{len(val)} chars: '{val}'"
    return True, f"Date formats: {json.dumps(formats_seen)}"


def t1_6():
    """DA X/Y string-to-float parsing"""
    params = {
        "where": "PLANNING_PORTAL_APP_NUMBER='PAN-123967'",
        "outFields": "X,Y",
        "f": "json",
    }
    r = requests.get(DA_URL, params=params, timeout=10)
    d = r.json()
    a = d["features"][0]["attributes"]
    x = float(a["X"])
    y = float(a["Y"])
    if not (140 < x < 154 and -38 < y < -28):
        return False, f"Coords out of NSW: {x},{y}"
    return True, f"X={x}, Y={y} (valid NSW)"


# ======================================================================
# 2. VG VALUATION MAPSERVER
# ======================================================================

def t1_7():
    """VG spatial query (OBJECTID fix)"""
    params = {
        "geometry": "151.13,-33.88,151.15,-33.87",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "outFields": "OBJECTID,propid,address,zone_desc,prop_area,val1_lv,val1_bd",
        "resultRecordCount": 10,
        "f": "json",
    }
    r = requests.get(VG_URL, params=params, timeout=10)
    d = r.json()
    if "error" in d:
        return False, f"VG spatial failed: {d['error']}"
    feats = d.get("features") or []
    if not feats:
        return False, "No features returned"
    return True, f"{len(feats)} properties in Haberfield bbox"


def t1_8():
    """VG spatial WITHOUT OBJECTID (expect fail — confirms the gotcha)"""
    params = {
        "geometry": "151.13,-33.88,151.15,-33.87",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "outFields": "propid,address,zone_desc,val1_lv",
        "resultRecordCount": 5,
        "f": "json",
    }
    r = requests.get(VG_URL, params=params, timeout=10)
    d = r.json()
    if "error" in d:
        return True, "Confirmed: spatial without OBJECTID fails (as expected)"
    return False, "UNEXPECTED: spatial without OBJECTID succeeded — gotcha may be intermittent!"


def t1_9():
    """VG string parsing (value + area)"""
    params = {
        "where": "propid=1292273",
        "outFields": "propid,address,prop_area,val1_lv,val2_lv,val3_lv",
        "f": "json",
    }
    r = requests.get(VG_URL, params=params, timeout=10)
    d = r.json()
    a = d["features"][0]["attributes"]
    raw_val = a.get("val1_lv") or ""
    parsed = int(raw_val.strip().replace("$", "").replace(",", "").replace(" ", ""))
    if parsed < 100000 or parsed > 50000000:
        return False, f"Parsed value unreasonable: {parsed}"
    raw_area = a.get("prop_area") or ""
    area = float(raw_area.strip().split(" ")[0])
    if area < 1 or area > 100000:
        return False, f"Parsed area unreasonable: {area}"
    return True, f"val={parsed} from '{raw_val}', area={area} from '{raw_area}'"


def t1_10():
    """VG bbox + geometry check for Haversine post-filter"""
    lat, lng = -33.88, 151.14
    radius_m = 300
    lat_off = radius_m / 111000
    lng_off = radius_m / (111000 * math.cos(math.radians(lat)))
    params = {
        "geometry": f"{lng - lng_off},{lat - lat_off},{lng + lng_off},{lat + lat_off}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "outFields": "*",
        "returnGeometry": "true",
        "resultRecordCount": 20,
        "f": "json",
    }
    r = requests.get(VG_URL, params=params, timeout=15)
    d = r.json()
    feats = d.get("features") or []
    if not feats:
        return False, "No features for Haversine test"
    has_geom = "geometry" in feats[0]
    if has_geom:
        g = feats[0]["geometry"]
        return True, f"{len(feats)} features, geometry={g.get('x','?')},{g.get('y','?')}"
    # No geometry — need propid-based Haversine via address geocoding, or skip post-filter
    return True, f"{len(feats)} features, NO GEOMETRY returned — must use bbox-only (no Haversine)"


def t1_11():
    """VG Sales spatial + date parsing"""
    params = {
        "geometry": "151.13,-33.88,151.15,-33.87",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "outFields": "*",
        "resultRecordCount": 5,
        "f": "json",
    }
    r = requests.get(VG_SALES_URL, params=params, timeout=10)
    d = r.json()
    if "error" in d:
        return False, f"Sales spatial failed: {d['error']}"
    feats = d.get("features") or []
    if not feats:
        return False, "No sales features"
    a = feats[0]["attributes"]
    dt = datetime.strptime(a["sale_date"], "%d %B %Y")
    return True, f"{len(feats)} sales, first: {a['bp_address']} sold {a['sale_date']} for ${a['price']:,}"


# ======================================================================
# 3. STRATA HUB
# ======================================================================

def t1_12():
    """Strata Hub spatial point query"""
    params = {
        "geometry": "151.125,-33.89",
        "geometryType": "esriGeometryPoint",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "plannumber,planlabel,address,suburb,lga,lottotal,registrationdate",
        "f": "json",
        "inSR": "4283",
    }
    r = requests.get(STRATA_URL, params=params, timeout=10)
    d = r.json()
    feats = d.get("features") or []
    if feats:
        a = feats[0]["attributes"]
        return True, f"Strata: {a.get('planlabel')} ({a.get('lottotal')} lots) at {a.get('address')}"
    return True, "No strata at this point (valid for some locations)"


def t1_13():
    """Strata epoch date parsing (negative timestamps for pre-1970)"""
    params = {
        "where": "lga='INNER WEST' AND registrationdate < 0",
        "outFields": "planlabel,registrationdate,lottotal",
        "resultRecordCount": 3,
        "f": "json",
    }
    r = requests.get(STRATA_URL, params=params, timeout=10)
    d = r.json()
    feats = d.get("features") or []
    if not feats:
        return False, "No pre-1970 strata plans found"
    for f in feats:
        epoch_ms = f["attributes"]["registrationdate"]
        try:
            dt = datetime.fromtimestamp(epoch_ms / 1000)
            if dt.year > 1970:
                return False, f"Negative epoch gave year {dt.year}"
        except (OSError, ValueError, OverflowError) as e:
            return False, f"Negative epoch {epoch_ms} failed: {e}"
    return True, f"{len(feats)} pre-1970 plans parsed OK"


def t1_14():
    """Dwelling type classification boundaries"""
    def classify(n):
        if n <= 2: return "duplex"
        if n <= 4: return "townhouse"
        if n <= 8: return "small_apartment"
        return "apartment"

    tests = [(1, "duplex"), (2, "duplex"), (3, "townhouse"), (4, "townhouse"),
             (5, "small_apartment"), (8, "small_apartment"), (9, "apartment"), (27, "apartment")]
    for val, expected in tests:
        got = classify(val)
        if got != expected:
            return False, f"classify({val})={got}, expected {expected}"
    return True, "All classification boundaries correct"


def t1_15():
    """DA pagination (resultOffset)"""
    params = {
        "where": "LGA_NAME LIKE '%Sydney%' AND ASSESMENT_RESULT='Approved'",
        "outFields": "OBJECTID,PLANNING_PORTAL_APP_NUMBER",
        "resultRecordCount": 2,
        "resultOffset": 0,
        "f": "json",
    }
    r1 = requests.get(DA_URL, params=params, timeout=10)
    d1 = r1.json()
    ids1 = [f["attributes"]["OBJECTID"] for f in d1.get("features") or []]

    params["resultOffset"] = 2
    r2 = requests.get(DA_URL, params=params, timeout=10)
    d2 = r2.json()
    ids2 = [f["attributes"]["OBJECTID"] for f in d2.get("features") or []]

    overlap = set(ids1) & set(ids2)
    if overlap:
        return False, f"Pagination overlap: {overlap}"
    if not ids1 or not ids2:
        return False, f"Empty pages: p1={len(ids1)}, p2={len(ids2)}"
    return True, f"Page 1: {ids1}, Page 2: {ids2} (no overlap)"


def t1_16():
    """VG comparable zone diversity check"""
    params = {
        "geometry": "151.13,-33.88,151.15,-33.87",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "outFields": "*",
        "resultRecordCount": 50,
        "f": "json",
    }
    r = requests.get(VG_URL, params=params, timeout=15)
    d = r.json()
    feats = d.get("features") or []
    zones = set()
    for f in feats:
        z = f["attributes"].get("zone_desc") or ""
        zones.add(z)
    r2_count = sum(1 for f in feats if "R2" in (f["attributes"].get("zone_desc") or ""))
    return True, f"{len(feats)} total, {r2_count} R2. Zones: {zones}"


# ======================================================================
# RUN ALL
# ======================================================================

print("=" * 60)
print("PHASE 1: LIVE-FIRE TESTS")
print("=" * 60)

for fn in [t1_1, t1_2, t1_3, t1_4, t1_5, t1_6, t1_7, t1_8, t1_9, t1_10,
           t1_11, t1_12, t1_13, t1_14, t1_15, t1_16]:
    test(fn.__doc__ or fn.__name__, fn)

print()
print("=" * 60)
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
print(f"PHASE 1 TOTAL: {passed} PASS / {failed} FAIL / {len(results)} total")
if failed:
    print("\nFAILURES:")
    for r in results:
        if r["status"] == "FAIL":
            print(f"  XX {r['name']}: {r['detail'][:200]}")
print("=" * 60)

with open(".claude/strategy/_phase1_results.json", "w") as fh:
    json.dump(results, fh, indent=2)
print("\nResults written to .claude/strategy/_phase1_results.json")
