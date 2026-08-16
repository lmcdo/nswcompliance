import requests, json, sys

dr = requests.get(
    "https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineDA",
    headers={
        "filters": json.dumps({"CouncilName": "Inner West Council", "LodgementDateFrom": "2023-01-01"}),
        "PageSize": "1", "PageNumber": "1", "Cache-Control": "no-cache",
    },
    timeout=15)

print(f"Status: {dr.status_code}")
data = dr.json()
apps = data.get("Application") or data.get("ApplicationList") or []
if apps:
    print("Full first record:")
    print(json.dumps(apps[0], indent=2))
else:
    print("No apps. Full response:")
    print(json.dumps(data, indent=2)[:1000])
sys.stdout.flush()
