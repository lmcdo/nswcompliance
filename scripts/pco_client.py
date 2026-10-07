#!/usr/bin/env python3
"""
PCO (Parliamentary Counsel's Office) XML Export Client
=====================================================
Queries legislation.nsw.gov.au export API for instrument changes.

IP 149.28.176.81 whitelisted (confirmed 2026-05-19 by PCO Website Help).
Must run outside Sydney business hours (agreed condition).

Reference: https://legislation.nsw.gov.au/help/export

Endpoints:
    /export/week?format=json    — instruments updated in last 7 days
    /export/day?format=json     — instruments updated today
    /export/custom/{query}?format=json — fielded query
    /view/html/inforce/current/{id}/xml — full instrument XML

Custom query fields:
    Load Date, Last Updated, First Valid Date, End Valid Date,
    Type, Year, No, Title, Repealed, Point In Time
Operators: =, >, <, <>, >=, <=
"""

import sys
import urllib.parse
from dataclasses import dataclass, field

import requests

PCO_BASE = "https://legislation.nsw.gov.au"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; compliance-data-fetch)"
    ),
    "Accept": "application/json,*/*",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


class PCOAccessDenied(Exception):
    """Raised when PCO returns 403 — IP may not be active on this machine.
    Whitelisted IP: 149.28.176.81 (confirmed 2026-05-19).
    """
    pass


class PCOError(Exception):
    """General PCO API error."""
    pass


@dataclass
class PCOChange:
    """A single instrument change from the PCO export feed."""
    title: str = ""
    instrument_id: str = ""
    instrument_type: str = ""
    url: str = ""
    point_in_time: str = ""
    last_updated: str = ""
    raw: dict = field(default_factory=dict)


def _request(url: str, timeout: int = 30) -> requests.Response:
    """Make a request to PCO, raising typed errors."""
    resp = SESSION.get(url, timeout=timeout, allow_redirects=True)
    if resp.status_code == 403:
        raise PCOAccessDenied(
            f"HTTP 403 from PCO — this machine's IP may not be the "
            f"whitelisted IP (149.28.176.81). URL: {url}"
        )
    if resp.status_code != 200:
        raise PCOError(f"HTTP {resp.status_code}: {url}")
    return resp


def _instrument_id_from_path(path: str) -> str:
    """'/view/html/inforce/current/epi-2021-0714' -> 'epi-2021-0714'; '' if none."""
    candidate = (path or "").rstrip("/").split("/")[-1]
    return candidate if candidate.startswith(("epi-", "act-", "sl-")) else ""


def _parse_changes(data: list[dict]) -> list[PCOChange]:
    """Parse PCO export JSON into PCOChange objects.

    PCO changed its export format (seen 2026-10-08): records now carry only
    title / view / xml / images, with no URL and no point-in-time field. The old
    parser read only URL, so every instrument_id came back blank and nothing ever
    matched, which the monitor then reported as "no changes" for four months.
    The ID is now taken from whichever path field is present, and an export
    whose records yield NO instrument IDs at all raises: an unreadable export is
    a failure, never an empty result.
    """
    changes = []
    for item in data:
        title = item.get("Title") or item.get("title") or ""
        url = item.get("URL") or item.get("url") or item.get("view") or ""
        pit = item.get("Point In Time") or item.get("point_in_time") or ""
        updated = item.get("Last Updated") or item.get("last_updated") or ""
        itype = item.get("Type") or item.get("type") or ""
        instrument_id = (
            _instrument_id_from_path(url)
            or _instrument_id_from_path(item.get("xml") or "")
        )
        changes.append(PCOChange(
            title=title,
            instrument_id=instrument_id,
            instrument_type=itype,
            url=url,
            point_in_time=pit,
            last_updated=updated,
            raw=item,
        ))
    if changes and not any(c.instrument_id for c in changes):
        raise PCOError(
            f"PCO export format not recognised: {len(changes)} records, none with an "
            f"instrument ID (keys seen: {sorted(data[0].keys()) if isinstance(data[0], dict) else type(data[0]).__name__})"
        )
    return changes


def get_weekly_changes() -> list[PCOChange]:
    """Fetch all instruments updated in the last 7 days."""
    url = f"{PCO_BASE}/export/week?format=json"
    resp = _request(url)
    ct = resp.headers.get("Content-Type", "")
    if "json" not in ct:
        raise PCOError(f"Expected JSON but got Content-Type: {ct}")
    data = resp.json()
    if not isinstance(data, list):
        raise PCOError(f"Expected JSON array, got {type(data).__name__}")
    return _parse_changes(data)


def get_daily_changes() -> list[PCOChange]:
    """Fetch all instruments updated today."""
    url = f"{PCO_BASE}/export/day?format=json"
    resp = _request(url)
    return _parse_changes(resp.json())


def get_epi_changes() -> list[PCOChange]:
    """Fetch all EPI (Environmental Planning Instrument) changes in last 7 days.
    EPIs include SEPPs, LEPs, and DCPs."""
    query = '"Type"=epi'
    encoded = urllib.parse.quote(query)
    url = f"{PCO_BASE}/export/custom/{encoded}?format=json"
    resp = _request(url)
    return _parse_changes(resp.json())


def get_instrument_xml(instrument_id: str) -> str:
    """Download full XML for a specific instrument.

    Args:
        instrument_id: e.g. 'epi-2021-0714' for SEPP Housing 2021
    """
    url = f"{PCO_BASE}/view/html/inforce/current/{instrument_id}/xml"
    resp = _request(url, timeout=60)
    return resp.text


def test_access() -> bool:
    """Test whether PCO endpoint is accessible (IP whitelisted).
    Returns True if accessible, False if blocked."""
    try:
        resp = SESSION.get(
            f"{PCO_BASE}/export/week?format=json",
            timeout=15,
            allow_redirects=True,
        )
        if resp.status_code == 403:
            return False
        if "json" not in resp.headers.get("Content-Type", ""):
            return False
        return resp.status_code == 200
    except Exception:
        return False


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    print("Testing PCO access...")
    if test_access():
        print("  PCO accessible — fetching weekly changes...")
        changes = get_weekly_changes()
        print(f"  {len(changes)} instruments changed this week:")
        for c in changes[:10]:
            print(f"    {c.instrument_id or '?':<20} {c.title[:60]}")
            if c.point_in_time:
                print(f"      Point in time: {c.point_in_time}")
    else:
        print("  PCO returned 403 — this machine's IP is not the whitelisted IP.")
        print("  Whitelisted IP: 149.28.176.81 (run from that server)")
        sys.exit(1)
