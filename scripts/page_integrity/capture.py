"""Capture what the live assessment page shows for one address — every API call it makes and the
text of every tab — into one folder that the page-integrity checks read offline.

The page is driven in a real browser and its own network traffic is RECORDED, not re-implemented:
a replay would copy the frontend's param logic and drift from it (35 call types, several repeated,
see docs/page_integrity/ASSESSMENT_PAGE_INVENTORY.md). Only this script touches the network.

prior-art-checked: extends ~/.claude/plans/evidence/winston-hills-2026-10-19/capture.py (rendered text
only, no network record, no identity check) and differs from served_answer_audit.page_params (replays
one route by copying its params); neither records the page's own calls, which the cross-surface checks need.

Output folder (the capture format every check reads):
    meta.json       requested address, suggestion picked, timings, identity verdict, exit code
    calls.jsonl.gz  one line per /api/ response: method, url, path, query, request body, status, json
    rendered/<tab>.txt + .png   body text and screenshot per tab (sepp, planning, dcp)
    errors.json     anything that went wrong; non-empty -> exit 2

Exit codes: 0 captured, 2 could not capture faithfully (never a pass). This script judges nothing.

Usage:
    python scripts/page_integrity/capture.py OUTDIR "6 Berrigan Street, Winston Hills" \
        --number 6 --street "BERRIGAN STREET" --suburb "WINSTON HILLS"
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dq_probe_app_defects import _number_matches  # noqa: E402  (shared address-identity rule)

BASE_URL = os.environ.get("PAGE_INTEGRITY_URL", "https://verify.plotdetect.com.au")
TABS = (("sepp", "SEPP"), ("planning", "Planning Controls"), ("dcp", "DCP"))
QUIET_S = 6.0        # no /api/ request in flight for this long = the tab has settled
SETTLE_MAX_S = 120.0


def _json_or_none(resp: Any) -> Optional[Any]:
    try:
        return resp.json()
    except Exception:
        return None


def identity_ok(property_json: Any, number: str, street: str, suburb: str) -> tuple[bool, str]:
    """The property the page loaded must be the address asked for (the Portal's top hit can be a
    different house). Returns (ok, the address the page resolved)."""
    if not isinstance(property_json, dict):
        return False, ""
    data = property_json.get("data") if isinstance(property_json.get("data"), dict) else property_json
    got = str(data.get("address") or data.get("formattedAddress") or "").upper()
    ok = bool(got) and _number_matches(number, got) and street.upper() in got and suburb.upper() in got
    return ok, got


class Recorder:
    """Records every /api/ response the page receives, and how many requests are in flight."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.in_flight = 0
        self.last_activity = time.monotonic()

    def _is_api(self, url: str) -> bool:
        # The site's own routes only — Google Maps also serves under /maps/api/.
        u = urlparse(url)
        return u.netloc == urlparse(BASE_URL).netloc and u.path.startswith("/api/")

    def on_request(self, req: Any) -> None:
        if self._is_api(req.url):
            self.in_flight += 1
            self.last_activity = time.monotonic()

    def on_done(self, req: Any) -> None:
        if self._is_api(req.url):
            self.in_flight = max(0, self.in_flight - 1)
            self.last_activity = time.monotonic()

    def on_response(self, resp: Any) -> None:
        if not self._is_api(resp.url):
            return
        req = resp.request
        u = urlparse(resp.url)
        body = req.post_data
        try:
            body = json.loads(body) if body else None
        except ValueError:
            pass
        self.calls.append({
            "t": round(time.monotonic(), 3),
            "method": req.method,
            "url": resp.url,
            "path": u.path,
            "query": {k: v if len(v) > 1 else v[0] for k, v in parse_qs(u.query).items()},
            "request_body": body,
            "status": resp.status,
            "json": _json_or_none(resp),
        })

    def settle(self, page: Any) -> bool:
        """Wait until no /api/ request has been in flight for QUIET_S. False on timeout."""
        start = time.monotonic()
        while time.monotonic() - start < SETTLE_MAX_S:
            page.wait_for_timeout(500)
            if self.in_flight == 0 and time.monotonic() - self.last_activity >= QUIET_S:
                return True
        return False


def capture(outdir: Path, address: str, number: str, street: str, suburb: str) -> int:
    from playwright.sync_api import sync_playwright

    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "rendered").mkdir(exist_ok=True)
    rec = Recorder()
    errors: list[str] = []
    meta: dict[str, Any] = {
        "requested_address": address, "number": number, "street": street, "suburb": suburb,
        "base_url": BASE_URL, "captured_at": datetime.now(timezone.utc).isoformat(),
    }

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.on("request", rec.on_request)
        page.on("requestfinished", rec.on_done)
        page.on("requestfailed", rec.on_done)
        page.on("response", rec.on_response)
        try:
            page.goto(f"{BASE_URL}/assessment", wait_until="domcontentloaded", timeout=60000)
            inp = page.get_by_placeholder("Start typing an address...")
            inp.wait_for(timeout=30000)
            inp.click()
            inp.type(address, delay=60)
            page.wait_for_timeout(4000)
            # Google's first suggestion is sometimes the STREET, not the house — choose the first
            # suggestion that starts with the house number, by position in the list.
            items = page.locator(".pac-item")
            texts = [items.nth(i).inner_text().replace("\n", " ") for i in range(items.count())]
            meta["suggestions"] = texts
            pick = next((i for i, t in enumerate(texts) if t.strip().startswith(f"{number} ")), None)
            if pick is None:
                raise RuntimeError(f"no suggestion starts with house number {number!r}: {texts}")
            for _ in range(pick + 1):
                inp.press("ArrowDown")
            meta["suggestion_picked"] = inp.input_value()
            inp.press("Enter")
            page.wait_for_timeout(2000)
            page.get_by_role("button", name="Analyze Property").click()
            if not rec.settle(page):
                errors.append("overview did not settle within %ss" % SETTLE_MAX_S)

            prop = [c for c in rec.calls if c["path"] == "/api/property" and c["status"] == 200]
            ok, got = identity_ok(prop[-1]["json"] if prop else None, number, street, suburb)
            meta["resolved_address"] = got
            meta["identity_ok"] = ok
            if not ok:
                errors.append(f"page loaded {got!r}, not the address asked for")

            for key, label in TABS:
                tab = page.get_by_role("tab", name=label)
                if not tab.count():
                    errors.append(f"tab {label!r} not found")
                    continue
                tab.first.click()
                if not rec.settle(page):
                    errors.append(f"tab {label!r} did not settle within {SETTLE_MAX_S}s")
                page.mouse.wheel(0, 500)
                page.wait_for_timeout(1000)
                page.screenshot(path=str(outdir / "rendered" / f"{key}.png"), full_page=True)
                (outdir / "rendered" / f"{key}.txt").write_text(page.inner_text("body"), encoding="utf-8")
        except Exception as e:  # any failure is recorded and makes the capture unusable (exit 2)
            errors.append(f"{type(e).__name__}: {e}")
        finally:
            browser.close()

    bad = [c for c in rec.calls if c["status"] >= 400]
    meta["calls"] = len(rec.calls)
    meta["calls_failed"] = [f'{c["method"]} {c["path"]} {c["status"]}' for c in bad]
    meta["exit"] = 2 if errors else 0
    # gzip: /api/provisions/for-property alone is ~9 MB raw, ~0.8 MB compressed.
    with gzip.open(outdir / "calls.jsonl.gz", "wt", encoding="utf-8") as f:
        for c in rec.calls:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    (outdir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    (outdir / "errors.json").write_text(json.dumps(errors, indent=2), encoding="utf-8")
    return meta["exit"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("outdir")
    ap.add_argument("address")
    ap.add_argument("--number", required=True)
    ap.add_argument("--street", required=True)
    ap.add_argument("--suburb", required=True)
    a = ap.parse_args()
    code = capture(Path(a.outdir), a.address, a.number, a.street, a.suburb)
    print(json.dumps(json.loads((Path(a.outdir) / "meta.json").read_text(encoding="utf-8")), indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main())
