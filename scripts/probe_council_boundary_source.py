#!/usr/bin/env python3
"""
Probe a NSW council for a published DCP precinct-boundary source
================================================================
Before hand-digitising a DCP map figure in QGIS, check whether the council
already publishes the boundaries as a machine-readable GIS layer. If it does,
you can fetch it directly (see scripts/fetch_cos_dcp_boundaries.py) and skip the
figure pipeline entirely.

What this does
--------------
Given an ArcGIS REST *services root* (or a council name that has one registered
in COUNCIL_ARCGIS_ROOTS below), it:

  1. Crawls the ArcGIS REST directory (folders -> services -> layers), bounded
     depth, being polite between requests.
  2. Scores every layer name against precinct/boundary keywords.
  3. Prints a ranked candidate list with a ready-to-use `.../query` URL and the
     live feature count for each strong candidate.
  4. Classifies the council into one of three acquisition routes:
       ROUTE 1  published GIS layer found      -> fetch directly, no figure
       ROUTE 2  no layer; check address-list   -> maybe geocodable (see below)
       ROUTE 3  no layer                        -> fall back to figure pipeline

This only detects ROUTE 1 automatically. ROUTE 2 (the DCP defines a precinct by
listing addresses rather than drawing it) requires reading the DCP text; this
tool just reminds you to check. ROUTE 3 is the residual.

It never writes to the database and never downloads geometry — it only reads
REST metadata and one count per candidate. Output is advisory: a human decides
which candidate layer (if any) is the real precinct source.

prior-art-checked: reuse not viable because existing services (nsw_planning_api,
portal_constraints, council_validation_service, fetch_cos_dcp_boundaries) query
FIXED, already-known ArcGIS endpoints or DB citations; none DISCOVERS layers by
crawling an ArcGIS REST services *catalog* (folders -> services -> layers) and
scoring names to find an unknown precinct-boundary source. This is a discovery/
classification probe, not another fixed-endpoint fetcher.

Usage
-----
    # By registered council name
    python3 scripts/probe_council_boundary_source.py --council "City of Sydney"

    # By arbitrary ArcGIS REST services root
    python3 scripts/probe_council_boundary_source.py \
        --root https://services1.arcgis.com/cNVyNtjGVZybOQWZ/arcgis/rest/services

    # List everything (not just keyword matches), e.g. to eyeball an unfamiliar portal
    python3 scripts/probe_council_boundary_source.py --council "City of Sydney" --all

    # JSON output for piping into a registry
    python3 scripts/probe_council_boundary_source.py --council "City of Sydney" --json
"""

from __future__ import annotations

import argparse
import http.client
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, asdict

# Network errors we tolerate per-request: a single unreachable/malformed service
# on an unfamiliar portal must not abort the whole crawl. http.client.InvalidURL
# and other HTTPExceptions are NOT subclasses of urllib.error.URLError, hence the
# explicit union.
NET_ERRORS = (
    urllib.error.URLError, http.client.HTTPException, TimeoutError,
    OSError, ValueError, json.JSONDecodeError,
)

USER_AGENT = "Mozilla/5.0 (compliance-engine boundary-source probe)"
REQUEST_TIMEOUT = 30
POLITE_DELAY = 0.25          # seconds between REST calls
MAX_FOLDER_DEPTH = 2         # ArcGIS folders are rarely nested deeper
MIN_ROUTE1_SCORE = 3         # a candidate must score >= this to trigger ROUTE 1

# ---------------------------------------------------------------------------
# Registry of known council ArcGIS REST *service roots*.
# Grow this as you confirm each council's portal. The value is a list because
# some councils split planning layers across several ArcGIS Online orgs /
# on-prem servers.
#
# A "services root" ends at .../arcgis/rest/services (no service name after it).
# ---------------------------------------------------------------------------
COUNCIL_ARCGIS_ROOTS: dict[str, list[str]] = {
    # City of Sydney — confirmed: DCP 2012 FeatureServer lives under this org.
    "City of Sydney": [
        "https://services1.arcgis.com/cNVyNtjGVZybOQWZ/arcgis/rest/services",
    ],
    # --- add councils here as you confirm their ArcGIS roots ---
    # "Ku-ring-gai": ["https://..."],
    # "Inner West":  ["https://..."],
}

# ---------------------------------------------------------------------------
# Layer-name scoring. Positive keywords suggest a precinct/character/locality
# boundary layer; negative keywords suppress obvious non-planning layers so the
# ranked list stays readable.
# ---------------------------------------------------------------------------
POSITIVE_KEYWORDS: dict[str, int] = {
    "precinct": 4,
    "locality": 3,
    "character": 3,
    "dcp": 3,
    "development control": 3,
    "specific area": 3,
    "specific site": 2,
    "planning area": 2,
    "neighbourhood": 2,
    "neighborhood": 2,
    "area": 1,
    "zone": 1,
    "boundary": 1,
}
NEGATIVE_KEYWORDS: dict[str, int] = {
    "flood": -3,
    "bushfire": -3,
    "tree": -3,
    "bin": -3,
    "waste": -3,
    "road": -2,
    "aerial": -2,
    "imagery": -2,
    "contour": -2,
    "cadastre": -1,
    "parcel": -1,
    "lot": -1,
}


@dataclass
class LayerCandidate:
    """One ArcGIS layer that might be a precinct-boundary source."""

    service_url: str
    layer_id: int
    name: str
    geometry_type: str
    score: int
    feature_count: int | None = None

    @property
    def query_url(self) -> str:
        """A ready-to-run GeoJSON query URL (all features, WGS84)."""
        params = urllib.parse.urlencode({
            "where": "1=1", "outFields": "*", "outSR": "4326", "f": "geojson",
        })
        return f"{self.service_url}/{self.layer_id}/query?{params}"


@dataclass
class ProbeResult:
    council: str | None
    roots: list[str]
    candidates: list[LayerCandidate] = field(default_factory=list)
    services_seen: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def route(self) -> int:
        strong = [c for c in self.candidates if c.score >= MIN_ROUTE1_SCORE
                  and (c.feature_count is None or c.feature_count > 0)]
        return 1 if strong else 3


def _get_json(url: str) -> dict:
    """GET a URL and parse JSON, appending f=json if no format specified."""
    if "f=" not in url:
        url += ("&" if "?" in url else "?") + "f=json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read())


def _score_name(name: str) -> int:
    """Score a layer name by keyword presence (case-insensitive substring)."""
    low = name.lower()
    score = 0
    for kw, pts in POSITIVE_KEYWORDS.items():
        if kw in low:
            score += pts
    for kw, pts in NEGATIVE_KEYWORDS.items():
        if kw in low:
            score += pts
    return score


def _feature_count(service_url: str, layer_id: int) -> int | None:
    """Return the feature count for a layer, or None if the count call fails."""
    params = urllib.parse.urlencode({
        "where": "1=1", "returnCountOnly": "true", "f": "json",
    })
    url = f"{service_url}/{layer_id}/query?{params}"
    try:
        return int(_get_json(url).get("count", 0))
    except (*NET_ERRORS, KeyError):
        return None


def _crawl_service(service_url: str, result: ProbeResult, keep_all: bool) -> None:
    """List a Feature/Map service's layers and collect scored candidates."""
    try:
        meta = _get_json(service_url)
    except NET_ERRORS as exc:
        result.errors.append(f"service {service_url}: {exc}")
        return
    result.services_seen += 1
    time.sleep(POLITE_DELAY)

    for layer in meta.get("layers", []) or []:
        name = layer.get("name", "")
        score = _score_name(name)
        if score <= 0 and not keep_all:
            continue
        result.candidates.append(LayerCandidate(
            service_url=service_url,
            layer_id=layer.get("id", -1),
            name=name,
            geometry_type=layer.get("geometryType", "") or "",
            score=score,
        ))


def _crawl_root(root: str, result: ProbeResult, keep_all: bool,
                depth: int = 0) -> None:
    """Recursively crawl an ArcGIS REST services root (folders + services)."""
    root = root.rstrip("/")
    try:
        catalog = _get_json(root)
    except NET_ERRORS as exc:
        result.errors.append(f"root {root}: {exc}")
        return
    time.sleep(POLITE_DELAY)

    services_base = root.rsplit("/services", 1)[0] + "/services"
    for svc in catalog.get("services", []) or []:
        stype = svc.get("type", "")
        if stype not in ("FeatureServer", "MapServer"):
            continue
        # svc["name"] can include a folder prefix; quote each path segment so an
        # embedded space/unicode char can't produce an InvalidURL request line.
        name_path = "/".join(urllib.parse.quote(seg)
                             for seg in str(svc.get("name", "")).split("/"))
        svc_url = f"{services_base}/{name_path}/{stype}"
        _crawl_service(svc_url, result, keep_all)

    if depth < MAX_FOLDER_DEPTH:
        for folder in catalog.get("folders", []) or []:
            _crawl_root(f"{root}/{folder}", result, keep_all, depth + 1)


def probe(council: str | None, roots: list[str], keep_all: bool,
          count: bool) -> ProbeResult:
    """Crawl the given roots and return scored precinct-layer candidates."""
    result = ProbeResult(council=council, roots=roots)
    for root in roots:
        _crawl_root(root, result, keep_all)

    result.candidates.sort(key=lambda c: c.score, reverse=True)

    if count:
        # Only count the plausibly-real candidates to stay polite.
        for c in result.candidates:
            if c.score >= 1:
                c.feature_count = _feature_count(c.service_url, c.layer_id)
                time.sleep(POLITE_DELAY)
    return result


def _resolve_roots(args: argparse.Namespace) -> tuple[str | None, list[str]]:
    if args.root:
        return None, [args.root]
    if args.council:
        roots = COUNCIL_ARCGIS_ROOTS.get(args.council)
        if not roots:
            known = ", ".join(sorted(COUNCIL_ARCGIS_ROOTS)) or "(none registered)"
            sys.exit(
                f"No ArcGIS root registered for '{args.council}'.\n"
                f"Registered councils: {known}\n"
                f"Pass --root <services-url> instead, and add it to "
                f"COUNCIL_ARCGIS_ROOTS once confirmed."
            )
        return args.council, roots
    sys.exit("Provide either --council <name> or --root <arcgis-services-url>.")


def _print_human(result: ProbeResult) -> None:
    title = result.council or result.roots[0]
    print(f"\n=== Boundary-source probe: {title} ===")
    print(f"Roots crawled : {len(result.roots)}")
    print(f"Services seen : {result.services_seen}")
    if result.errors:
        print(f"Errors        : {len(result.errors)} (see --json for detail)")

    strong = [c for c in result.candidates if c.score >= MIN_ROUTE1_SCORE]
    weak = [c for c in result.candidates
            if 1 <= c.score < MIN_ROUTE1_SCORE]

    if strong:
        print(f"\n-- Strong candidates (score >= {MIN_ROUTE1_SCORE}) --")
        for c in strong:
            cnt = "" if c.feature_count is None else f"  [{c.feature_count} features]"
            print(f"  [{c.score:>2}] {c.name}  ({c.geometry_type}){cnt}")
            print(f"       {c.query_url}")
    if weak:
        print("\n-- Weaker candidates (worth a glance) --")
        for c in weak:
            print(f"  [{c.score:>2}] {c.name}  ({c.geometry_type})")

    route = result.route
    print("\n-- Verdict --")
    if route == 1:
        print("  ROUTE 1: published GIS layer(s) found. Fetch directly — model")
        print("           scripts/fetch_cos_dcp_boundaries.py on the URL(s) above.")
        print("           No figure digitising needed. Verify the layer is the")
        print("           DCP precinct source (not zoning/LEP) before trusting it.")
    else:
        print("  ROUTE 2/3: no published precinct layer found on the crawled root(s).")
        print("           ROUTE 2 — read the DCP: if it defines precincts by LISTING")
        print("           ADDRESSES, geocode them (see import_krg_site_boundaries.py).")
        print("           ROUTE 3 — if it only shows a DRAWN MAP FIGURE, fall back to")
        print("           the georeference -> vectorise pipeline. Also double-check the")
        print("           council has no OTHER ArcGIS root not yet registered.")
    print()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Probe a NSW council for a published DCP precinct-boundary layer.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--council", help="Council name registered in COUNCIL_ARCGIS_ROOTS")
    g.add_argument("--root", help="ArcGIS REST services root URL to crawl directly")
    ap.add_argument("--all", action="store_true", dest="keep_all",
                    help="List every layer, not just keyword matches")
    ap.add_argument("--no-count", action="store_true",
                    help="Skip live feature-count calls (faster, metadata only)")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="Emit the raw result as JSON")
    args = ap.parse_args()

    council, roots = _resolve_roots(args)
    result = probe(council, roots, keep_all=args.keep_all, count=not args.no_count)

    if args.as_json:
        payload = asdict(result)
        payload["route"] = result.route
        for c, raw in zip(result.candidates, payload["candidates"]):
            raw["query_url"] = c.query_url
        print(json.dumps(payload, indent=2))
    else:
        _print_human(result)


if __name__ == "__main__":
    main()
