#!/usr/bin/env python3
"""Print the outbound IP of this machine and exit."""
import requests
import time
try:
    resp = requests.get("https://api.ipify.org", timeout=10)
    print(f"OUTBOUND_IP={resp.text}")
except Exception as e:
    print(f"ERROR: {e}")
# Keep alive for 30s so logs can be read
time.sleep(30)
