"""Fetch real Construction Certificate records from NSW Planning Portal."""
import urllib.request
import json

ENDPOINTS = [
    # Try OnlinePCC first
    "https://api.onlineplanningportal.nsw.gov.au/OnlinePCC/1.0/search?applicationTypes=CC&councilNames=Inner%20West%20Council&lodgementDateFrom=2022-01-01&lodgementDateTo=2023-12-31&pageSize=10",
    # Try the open data API
    "https://api.planningportal.nsw.gov.au/eplanning/data/v0/OnlineDA?ApplicationType=CC&CouncilName=Inner+West+Council&LodgementDateFrom=2022-01-01&LodgementDateTo=2023-12-31&PageSize=10",
    # Try with different base
    "https://prodapim.planningportal.nsw.gov.au/eplanning/data/v0/OnlineDA?ApplicationType=CC&CouncilName=Inner%20West%20Council&LodgementDateFrom=2022-01-01&LodgementDateTo=2023-12-31&PageSize=10",
]

headers = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
}

for url in ENDPOINTS:
    print(f"\nTrying: {url[:80]}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            status = r.status
            body = r.read().decode("utf-8", errors="replace")
            print(f"  Status: {status}")
            print(f"  Response (first 1000 chars):\n{body[:1000]}")
            break
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.reason}")
    except Exception as e:
        print(f"  Error: {type(e).__name__}: {e}")

print("\nDone.")
