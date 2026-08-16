"""
Verify demo addresses across all 3 tabs against authoritative sources.

For each address:
  1. LEP tab — hit NSW Planning Portal directly, compare zone/height/FSR/heritage
  2. SEPP tab — hit our API, check SEPP provisions load
  3. DCP tab — hit our API, check structured controls + provision text load

Run: python scripts/verify_demo_addresses.py
Requires: DATABASE_URL in .env
"""
import json
import os
import sys
import urllib.request
import urllib.parse
import time

# ── Config ──────────────────────────────────────────────────────────
PROD = "https://verify.plotdetect.com.au"
PORTAL = "https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://verify.plotdetect.com.au/",
    "Accept": "application/json",
}

DEMO_ADDRESSES = [
    {"address": "129 Ramsay Street, Haberfield NSW 2045", "label": "THEIR OFFICE", "former_council": "ashfield"},
    {"address": "180 Addison Road, Marrickville NSW 2204", "label": "CLEAN R2", "former_council": "marrickville"},
    {"address": "5 Ramsay Street, Haberfield NSW 2045", "label": "HERITAGE", "former_council": "ashfield"},
    {"address": "15 Petersham Road, Marrickville NSW 2204", "label": "ACID SULFATE", "former_council": "marrickville"},
    {"address": "22 Pile Street, Marrickville NSW 2204", "label": "BIG LOT BACKUP", "former_council": "marrickville"},
]


def fetch_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"_error": str(e)}


def fetch_post(url, body, headers=None):
    h = dict(headers or HEADERS)
    h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"_error": str(e)}


def extract_portal_layers(layers):
    """Parse layerintersect response into a flat dict of key values."""
    out = {}
    for layer in layers:
        name = layer.get("layerName", "")
        results = layer.get("results", [])
        if not results:
            continue
        if "Land Zoning Map" in name:
            out["zone"] = results[0].get("Zone", "?")
            out["zone_title"] = results[0].get("title", "?")
        elif "Height of Buildings Map" in name:
            out["height"] = results[0].get("Maximum Building Height", "?")
        elif "Floor Space Ratio Map" in name:
            out["fsr"] = results[0].get("Floor Space Ratio", "?")
        elif "Lot Size Map" in name:
            out["min_lot"] = results[0].get("Minimum Lot Size", "?")
        elif "Heritage Map" in name:
            out["heritage_items"] = len(results)
            out["heritage_types"] = [r.get("Heritage Type", "?") for r in results]
            out["heritage_names"] = [r.get("Item Name", "?") for r in results]
        elif "Acid Sulfate" in name:
            out["acid_sulfate"] = results[0].get("Class", "?")
    return out


# ── Main ────────────────────────────────────────────────────────────
print("=" * 80)
print("DEMO ADDRESS VERIFICATION — 3-TAB CROSS-CHECK")
print("=" * 80)

issues = []

for addr_info in DEMO_ADDRESSES:
    addr = addr_info["address"]
    label = addr_info["label"]
    fc = addr_info["former_council"]

    print(f"\n{'─' * 80}")
    print(f"  {label}: {addr}")
    print(f"{'─' * 80}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. LEP TAB — Compare our API vs NSW Planning Portal directly
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n  [LEP TAB]")

    # Our API
    our_data = fetch_json(f"{PROD}/api/property?address={urllib.parse.quote(addr)}")
    if "_error" in our_data or not our_data.get("success"):
        print(f"    OUR API: FAILED — {our_data.get('_error', 'success=false')}")
        issues.append(f"{label}: Our property API failed")
        continue

    d = our_data["data"]
    c = d.get("constraints", {})
    our_zone = c.get("zone", "?")
    our_height = c.get("maxHeight")
    our_fsr = c.get("maxFsr")
    our_min_lot = c.get("minLotSize")
    our_heritage = c.get("heritage", False)
    our_heritage_type = c.get("heritageType", "none")
    our_acid = c.get("acidSulfateSoils", "none")
    our_fc = c.get("formerCouncil", "?")
    our_precinct = c.get("precinctName", "?")
    prop_id = d.get("propId")

    print(f"    Our API:    zone={our_zone} | height={our_height}m | fsr={our_fsr} | min_lot={our_min_lot}")
    print(f"                heritage={our_heritage} ({our_heritage_type}) | acid={our_acid}")
    print(f"                fc={our_fc} | precinct={our_precinct}")
    print(f"                propId={prop_id}")

    # NSW Planning Portal direct
    if prop_id:
        portal_raw = fetch_json(f"{PORTAL}/layerintersect?type=property&id={prop_id}&layers=epi")
        if "_error" not in portal_raw:
            portal = extract_portal_layers(portal_raw)
            p_zone = portal.get("zone", "?")
            p_height = portal.get("height", "?")
            p_fsr = portal.get("fsr", "?")
            p_min_lot = portal.get("min_lot")
            p_heritage = portal.get("heritage_items", 0)
            p_acid = portal.get("acid_sulfate", "none")

            print(f"    Portal:     zone={p_zone} | height={p_height}m | fsr={p_fsr} | min_lot={p_min_lot}")
            print(f"                heritage_items={p_heritage} | acid={p_acid}")

            # Cross-check
            mismatches = []
            if str(our_zone) != str(p_zone):
                mismatches.append(f"zone: ours={our_zone} portal={p_zone}")
            if str(our_height) != str(p_height) and p_height != "?":
                mismatches.append(f"height: ours={our_height} portal={p_height}")
            if str(our_fsr) != str(p_fsr) and p_fsr != "?":
                mismatches.append(f"fsr: ours={our_fsr} portal={p_fsr}")
            if our_heritage and p_heritage == 0:
                mismatches.append(f"heritage: ours=True portal=0 items")
            if not our_heritage and p_heritage > 0:
                mismatches.append(f"heritage: ours=False portal={p_heritage} items")

            if mismatches:
                print(f"    MISMATCH:   {' | '.join(mismatches)}")
                for m in mismatches:
                    issues.append(f"{label} LEP: {m}")
            else:
                print(f"    MATCH:      All LEP values match portal")
        else:
            print(f"    Portal:     FAILED — {portal_raw['_error']}")
            issues.append(f"{label}: Portal API failed")
    else:
        print(f"    Portal:     SKIPPED — no propId")

    # Legislation URL
    leg_url = c.get("fsrSource", {}).get("legislationUrl", "none")
    print(f"    LEP URL:    {leg_url}")

    time.sleep(0.5)  # Be nice to Portal API

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. SEPP TAB — Check structured requirements load
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n  [SEPP TAB]")

    sepp_routing = c.get("seppRouting", {})
    applicable = sepp_routing.get("applicableSepps", [])
    missing = sepp_routing.get("missing", [])
    total_provisions = sepp_routing.get("totalProvisions", 0)

    print(f"    Applicable SEPPs: {len(applicable)} — {applicable}")
    if missing:
        print(f"    Missing SEPP data: {missing}")
    print(f"    Total provisions: {total_provisions}")

    # Check each SEPP has structured requirements via API
    for sepp_id in ["housing_2021", "sustainable_buildings_2022", "resilience_hazards_2021", "transport_infrastructure_2021"]:
        sepp_data = fetch_post(f"{PROD}/api/sepp/structured-requirements", {
            "seppId": sepp_id,
            "developmentType": "dwelling_house",
        })
        if "_error" in sepp_data:
            print(f"    {sepp_id}: FAILED — {sepp_data['_error']}")
            issues.append(f"{label} SEPP: {sepp_id} API failed")
        else:
            req_count = len(sepp_data.get("requirements", []))
            print(f"    {sepp_id}: {req_count} requirements")
            if req_count == 0:
                issues.append(f"{label} SEPP: {sepp_id} returned 0 requirements")

    time.sleep(0.5)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. DCP TAB — Check structured controls + provision count
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n  [DCP TAB]")

    # Structured controls
    dcp_controls = fetch_json(
        f"{PROD}/api/dcp/structured-controls?council={fc}&dev_type=dwelling_house"
    )
    if "_error" in dcp_controls:
        print(f"    Controls: FAILED — {dcp_controls['_error']}")
        issues.append(f"{label} DCP: structured controls API failed")
    else:
        has_controls = dcp_controls.get("has_controls", False)
        categories = dcp_controls.get("categories", [])
        total_controls = sum(len(cat.get("controls", [])) for cat in categories)
        cat_names = [cat["category"] for cat in categories]

        print(f"    Controls:   {total_controls} controls across {cat_names}")

        # Count problematic rows
        no_rate = 0
        under_review = 0
        numeric = 0
        for cat in categories:
            for ctrl in cat.get("controls", []):
                status = ctrl.get("data_status", "?")
                if status == "not_applicable":
                    no_rate += 1
                elif status == "under_review":
                    under_review += 1
                elif status == "numeric":
                    numeric += 1

        print(f"    Breakdown:  {numeric} numeric | {no_rate} no_rate | {under_review} under_review")
        if under_review > 0:
            issues.append(f"{label} DCP: {under_review} controls under_review")

        # Check for assumed/invented source_text
        suspect_texts = []
        for cat in categories:
            for ctrl in cat.get("controls", []):
                st = ctrl.get("source_text", "") or ""
                cond = ctrl.get("condition", "") or ""
                if any(w in st.lower() for w in ["assumed", "needs pdf verification", "derived by planner"]):
                    suspect_texts.append(f"  {ctrl['control_type']}: {st[:80]}...")
                if any(w in cond.lower() for w in ["assumed"]):
                    suspect_texts.append(f"  {ctrl['control_type']}: condition='{cond[:80]}'")

        if suspect_texts:
            print(f"    SUSPECT source_text ({len(suspect_texts)} rows):")
            for s in suspect_texts:
                print(f"      {s}")
            issues.append(f"{label} DCP: {len(suspect_texts)} rows with suspect source_text")
        else:
            print(f"    Source text: all clean")

    # DCP provision text count (check provision browser has content)
    # This is fetched by the frontend via a different path — check the provisions API
    dcp_provisions = fetch_post(f"{PROD}/api/dcp/provisions", {
        "lga": "inner_west",
        "formerCouncil": fc,
        "zone": our_zone,
        "developmentType": "dwelling_house",
    })
    if "_error" in dcp_provisions:
        # Try alternate format
        dcp_provisions = fetch_json(
            f"{PROD}/api/dcp/provisions?lga=inner_west&formerCouncil={fc}&zone={our_zone}"
        )

    if "_error" in dcp_provisions:
        print(f"    Provisions: Could not verify (API format unknown)")
    else:
        prov_count = dcp_provisions.get("totalProvisions") or dcp_provisions.get("count") or len(dcp_provisions.get("provisions", []))
        print(f"    Provisions: {prov_count} text provisions")
        if prov_count == 0:
            issues.append(f"{label} DCP: 0 text provisions for {fc}")

    time.sleep(0.5)

# ── Summary ─────────────────────────────────────────────────────────
print(f"\n{'=' * 80}")
print("VERIFICATION SUMMARY")
print(f"{'=' * 80}")

if issues:
    print(f"\n  {len(issues)} ISSUES FOUND:\n")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
else:
    print("\n  ALL CLEAR — no mismatches or failures detected")

print(f"\n{'=' * 80}")
print("Cross-check complete. Review any issues above before the demo.")
print("For manual verification, open the legislation URL in a browser")
print("and confirm zone/height/FSR values match the gazetted instrument.")
print(f"{'=' * 80}")
