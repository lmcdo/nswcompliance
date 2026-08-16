import sys; sys.stdout.reconfigure(encoding='utf-8')
import json, requests
from datetime import date, timedelta

DA_URL = "https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineDA"
since = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")

r = requests.get(
    DA_URL,
    headers={
        "filters": json.dumps({"filters": {"CouncilName": ["Inner West Council"], "LodgementDateFrom": since}}),
        "PageSize": "3",
        "PageNumber": "1",
        "Cache-Control": "no-cache",
    },
    timeout=25,
)
r.raise_for_status()
apps = r.json().get("Application", [])
if apps:
    print("All keys in first app:")
    for k, v in apps[0].items():
        print(f"  {k}: {repr(v)[:120]}")
