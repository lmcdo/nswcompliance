import requests, json, sys

dr=requests.get(
    "https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineDA",
    headers={"filters":json.dumps({"CouncilName":"Inner West Council","LodgementDateFrom":"2023-01-01"}),"PageSize":"3","PageNumber":"1","Cache-Control":"no-cache"},
    timeout=15)
print(f"Status: {dr.status_code}")
apps=dr.json().get("Application") or dr.json().get("ApplicationList") or []
print(f"Apps returned: {len(apps)}")
if apps:
    a=apps[0]
    print(f"Fields: {list(a.keys())}")
    print(f"Has X/Y: {'X' in a and 'Y' in a}")
    print(f"Address: {a.get('Address')}")
    print(f"LodgementDate: {a.get('LodgementDate')}")
    print(f"DevelopmentType: {a.get('DevelopmentType')}")
else:
    print(dr.text[:300])
sys.stdout.flush()
