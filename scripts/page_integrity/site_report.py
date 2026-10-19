"""Fetch the Site Report for an address into a capture folder, so C7 can compare it with the page.

Read-only. Two hops: POST /api/intelligence-brief returns a trigger.dev run id + public token; the
report then streams as server-sent events. The events are saved as `site_report.jsonl.gz` (one event
per line). The access token is used for the stream only and is never written.

The production route allows ~12 reports per hour, so run_captures.sh fetches these one at a time
with a pause between them, and only when SITE_REPORT=1.

prior-art-checked: logic lifted from the 2026-10-19 evidence script (plans/evidence/.../fetch.py);
no in-repo fetcher for the Site Report stream exists.

Usage:
    python scripts/page_integrity/site_report.py <capture_folder> "<address>"
"""
from __future__ import annotations

import gzip
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://verify.plotdetect.com.au"
UA = "Mozilla/5.0 (page-integrity site-report)"


def _post(url: str, body: dict, timeout: int = 90) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"User-Agent": UA, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def fetch(address: str) -> list[dict]:
    t = _post(f"{BASE_URL}/api/intelligence-brief", {"address": address, "include_satellite": True})
    url = f"https://api.trigger.dev/realtime/v1/streams/{t['runId']}/intelligence-brief"
    hdr = {"Authorization": f"Bearer {t['publicAccessToken']}", "Accept": "text/event-stream", "User-Agent": UA}
    resp = None
    for _ in range(30):  # the stream 404s until the run has started
        try:
            resp = urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=300)
            break
        except urllib.error.HTTPError as e:
            if e.code not in (400, 404):
                raise
            time.sleep(2)
    if resp is None:
        raise RuntimeError("site report stream never opened")
    events: list[dict] = []
    buf = ""
    for raw in resp:
        line = raw.decode("utf-8", "replace").rstrip("\n").rstrip("\r")
        if line.startswith("data:"):
            buf += line[5:].strip()
        elif line == "" and buf:
            ev = json.loads(buf)
            ev = json.loads(ev) if isinstance(ev, str) else ev
            events.append(ev)
            buf = ""
            if ev.get("event") in ("complete", "error"):
                break
    return events


def main(argv: list[str]) -> int:
    folder, address = Path(argv[0]), argv[1]
    events = fetch(address)
    with gzip.open(folder / "site_report.jsonl.gz", "wt", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
    last = events[-1].get("event") if events else None
    print(f"{folder.name}: {len(events)} events, last={last}")
    return 0 if last == "complete" else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
