#!/usr/bin/env python3
"""Find Georges River parking chapter from scraper results."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, ".")
from scripts.hub_scrapers.generic import scrape_georges_river

results = scrape_georges_river(
    "https://www.georgesriver.nsw.gov.au/Development/Planning-Controls/Development-Control-Plans",
    expected_keys=set(), timeout=30,
)
for r in results:
    flag = ""
    label_lower = r["label"].lower()
    if any(k in label_lower for k in ["parking", "traffic", "transport", "access", "vehicle"]):
        flag = " *** PARKING ***"
    print(f"{r['label'][:65]:65s} {r['url'][-60:]}{flag}")
