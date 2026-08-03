#!/usr/bin/env python3
# prior-art-checked: no existing caller of the Planning Portal /dcp endpoint
# anywhere in the repo (repo-wide grep for ePlanningApi/dcp and dcpResults,
# 2026-08-03; memory/reference-planning-portal-undiscovered-endpoints.md lists
# it as unused). The coordinate->propId step reuses the cadastre Property-layer
# query shape from scripts/generate_conveyancing_report.py::resolve_propid_by_point
# but drops the address-identity gate: this script does not care WHICH parcel it
# resolves, only that the parcel is inside the target LGA, and that is verified
# against the /dcp response's own lgaName echo instead.
"""Fetch official DCP plan records (name, URL, amendment date) per served LGA.

Output-grounding campaign item 3 (Layer 2 "as at" dates). For every LGA slug
served from ``dcp_setback_controls`` this script:

  1. picks up to three residential-lot centroids for the LGA from
     ``lot_search_index`` (real cadastre parcels — nothing is guessed),
  2. resolves one centroid to a Planning-Portal propId via the NSW cadastre
     Property layer (point-in-polygon),
  3. calls the zero-auth Planning Portal ``/dcp`` endpoint ONCE for that propId,
  4. verifies the response's ``lgaName`` echo against the expected LGA before
     trusting anything,
  5. extracts an explicit amendment/effective date from the official planName /
     planURL — ONLY from an explicit dated phrase ("as amended 9 September
     2022"). A bare year in a plan name is a label, not a date, and is never
     parsed (precision-honesty rule; the retired version-string parser stays
     retired),
  6. upserts one row per LGA into ``dcp_plan_as_at`` with the verbatim evidence.

Politeness: one /dcp call per LGA (~28 total), >=1s between portal calls.

SAFETY: dry-run by default; ``--apply`` writes. Predicted row counts printed
before any write. The table is additive provenance — no serving table is
touched. Rows whose portal check fails are NOT written (a failed check is
"source unavailable", never "checked, none found").
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PORTAL_BASE = "https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi"
PORTAL_HEADERS = {
    "Referer": "https://www.planningportal.nsw.gov.au/",
    "User-Agent": "Mozilla/5.0",
}
PROPERTY_LAYER_URL = (
    "https://portal.spatial.nsw.gov.au/server/rest/services/"
    "NSW_Land_Parcel_Property_Theme/FeatureServer/12/query"
)

# lot_search_index.lga_name spellings that differ from slug.replace('_',' ').
# Administrative naming only (verified against live lot_search_index values,
# 2026-08-03) — no regulatory data.
SLUG_TO_INDEX_LGA: dict[str, str] = {
    "canterbury_bankstown": "CANTERBURY-BANKSTOWN",
    "city_of_sydney": "SYDNEY",
    "ku_ring_gai": "KU-RING-GAI",
    "parramatta": "CITY OF PARRAMATTA",
    "the_hills": "THE HILLS SHIRE",
}
# Former Inner West councils: lot_search_index keys them via former_council and
# the portal echoes lgaName 'INNER WEST' for all three.
FORMER_COUNCIL_SLUGS = {"ashfield", "leichhardt", "marrickville"}

MONTHS = {
    m.lower(): i
    for i, m in enumerate(
        ["January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"], start=1)
}
_MONTH_RE = "|".join(MONTHS)

# Explicit dated phrases only. Order matters: day precision before month.
_DATED_PHRASES: list[tuple[re.Pattern, str, str]] = [
    (re.compile(rf"(?:as\s+)?amended\s+(\d{{1,2}})\s+({_MONTH_RE})\s+(\d{{4}})", re.I),
     "day", "amended"),
    (re.compile(r"(?:as\s+)?amended\s+(\d{1,2})[/.](\d{1,2})[/.](\d{4})"),
     "day_numeric", "amended"),
    (re.compile(rf"(?:as\s+)?amended\s+({_MONTH_RE})\s+(\d{{4}})", re.I),
     "month", "amended"),
    (re.compile(rf"effective\s+(\d{{1,2}})\s+({_MONTH_RE})\s+(\d{{4}})", re.I),
     "day", "effective"),
    (re.compile(rf"effective\s+({_MONTH_RE})\s+(\d{{4}})", re.I),
     "month", "effective"),
]


@dataclass
class PortalResult:
    slug: str
    prop_id: Optional[int] = None
    lga_name: Optional[str] = None
    plan_name: Optional[str] = None
    plan_url: Optional[str] = None
    date_iso: Optional[str] = None
    precision: Optional[str] = None
    kind: Optional[str] = None
    evidence: Optional[str] = None
    raw: Optional[list] = None
    failure: Optional[str] = None
    # True when the portal WAS reached and echo-verified but no entry could
    # attach (identity mismatch / ambiguity). Distinct from infrastructure
    # failure: this state CLEARS any previously stored portal date, because a
    # date attached under an older identity must not keep serving (Sol
    # finding, 2026-08-03 — the Hornsby drift scenario).
    checked_unattached: bool = False
    notes: list[str] = field(default_factory=list)


def parse_dated_phrase(text: str) -> Optional[tuple[str, str, str, str]]:
    """Return (iso_date, precision, kind, evidence_substring) from an explicit
    dated phrase, or None. Never parses a bare year."""
    if not text:
        return None
    for pat, shape, kind in _DATED_PHRASES:
        m = pat.search(text)
        if not m:
            continue
        try:
            if shape == "day":
                d, mon, y = int(m.group(1)), MONTHS[m.group(2).lower()], int(m.group(3))
                return date(y, mon, d).isoformat(), "day", kind, m.group(0)
            if shape == "day_numeric":  # dd/mm/yyyy (AU ordering)
                d, mon, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
                return date(y, mon, d).isoformat(), "day", kind, m.group(0)
            if shape == "month":
                mon, y = MONTHS[m.group(1).lower()], int(m.group(2))
                return date(y, mon, 1).isoformat(), "month", kind, m.group(0)
        except (ValueError, KeyError):
            continue
    return None


def _get(url: str, params: dict, headers: Optional[dict] = None, timeout: int = 20):
    import requests

    r = requests.get(url, params=params, headers=headers or {}, timeout=timeout)
    r.raise_for_status()
    return r.json()


def resolve_prop_id(lat: float, lng: float) -> Optional[int]:
    """Point-in-cadastre propId (no identity gate — LGA is verified downstream
    against the /dcp lgaName echo instead)."""
    try:
        geometry = json.dumps({"x": lng, "y": lat, "spatialReference": {"wkid": 4326}})
        data = _get(
            PROPERTY_LAYER_URL,
            params={
                "geometry": geometry,
                "geometryType": "esriGeometryPoint",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "propid",
                "returnGeometry": "false",
                "f": "json",
            },
            timeout=15,
        )
        feats = data.get("features") or []
        ids = {(f.get("attributes") or {}).get("propid") for f in feats
               if (f.get("attributes") or {}).get("propid")}
        if len(ids) == 1:
            return int(ids.pop())
        return None  # 0 or ambiguous — try the next centroid
    except Exception:
        return None


def _norm(name: str) -> str:
    return re.sub(r"[^A-Z]", "", (name or "").upper())


def expected_portal_lga(slug: str) -> str:
    if slug in FORMER_COUNCIL_SLUGS:
        return "INNER WEST"
    return SLUG_TO_INDEX_LGA.get(slug, slug.replace("_", " ").upper())


_STOPWORDS = {"dcp", "development", "control", "plan", "comprehensive", "the"}


def _name_tokens(name: str) -> set[str]:
    toks = set()
    for t in re.split(r"[^a-z0-9]+", (name or "").lower()):
        if not t or t in _STOPWORDS:
            continue
        # 'Sustainable Cities' (portal) vs '(Sustainable City)' (registry):
        # normalise the ies/y variant only — no broader stemming.
        if t.endswith("ies"):
            t = t[:-3] + "y"
        toks.add(t)
    return toks


def pick_dcp_result(registry_names: list[str],
                    dcp_results: list[dict]) -> tuple[Optional[dict], Optional[str]]:
    """Anchor selection to the plan WE serve: a portal entry is eligible only
    if every identity token of a registry dcp_name (e.g. {'sydney','2012'})
    appears in its planName. Site-specific DCPs listed alongside the principal
    plan fail the subset test; a portal list in which NOTHING matches the
    served plan is an identity mismatch — a finding, and no date may attach
    across it (Hornsby class: portal still lists the 2013 plan, we serve the
    2024 one).

    Returns (chosen, failure_reason) — exactly one is non-None.
    """
    if not dcp_results:
        return None, "empty dcpResults"
    matches: list[tuple[bool, int, dict]] = []  # (exact, registry year or 0, entry)
    for entry in dcp_results:
        cand = _name_tokens(entry.get("planName") or "")
        for reg in registry_names:
            toks = _name_tokens(reg)
            if toks and toks <= cand:
                year = max((int(t) for t in toks if t.isdigit() and len(t) == 4),
                           default=0)
                matches.append((toks == cand, year, entry))
                break
    if not matches:
        names = "; ".join((r.get("planName") or "?")[:60] for r in dcp_results[:4])
        return None, (f"IDENTITY MISMATCH — none of {len(dcp_results)} portal "
                      f"plans match the served plan ({names}…)")
    # Exact token-set equality beats superset matches ('Sydney DCP 2012' is a
    # subset of every site-specific 'Sydney DCP 2012 — <precinct>' name too);
    # then prefer the latest-year registry identity (Waverley serves the 2022
    # plan while the 2012 one is still registered).
    exact = [m for m in matches if m[0]]
    pool = exact or matches
    pool.sort(key=lambda p: p[1], reverse=True)
    top = [e for ex, y, e in pool if y == pool[0][1]]
    if len(top) > 1 and len({id(e) for e in top}) > 1:
        # Multi-volume/multi-chapter plans (Campbelltown Volumes 1-3,
        # Sutherland's per-chapter entries) all match the one served identity.
        # If EVERY matched entry states the identical dated phrase, the date is
        # plan-level and the volume choice cannot change it — accept the date
        # and note the multiplicity. Differing (or missing) dates stay
        # ambiguous and nothing is written.
        phrases = {
            parse_dated_phrase(
                f"{e.get('planName') or ''} "
                + urllib.parse.unquote((e.get('planURL') or '').replace('+', ' ')))
            for e in top
        }
        if len(phrases) == 1 and None not in phrases:
            chosen = min(top, key=lambda e: len(e.get("planName") or ""))
            return ({**chosen, "_shared_phrase_count": len(top)}), None
        return None, f"{len(top)} portal plans match the served identity — ambiguous"
    return top[0], None


# prior-art-checked: this is the same file's own resolve/echo loop being
# restructured (retry the NEXT centroid on an LGA-echo mismatch instead of
# giving up); the module-header prior-art note covers why the cadastre point
# query is not reusable from services/* (those return overlays/strata, not a
# propId, per resolve_propid_by_point's own note in generate_conveyancing_report.py).
def fetch_one(slug: str, centroids: list[tuple[float, float]],
              registry_names: list[str]) -> PortalResult:
    res = PortalResult(slug=slug)
    expect = expected_portal_lga(slug)
    rec = None
    for lat, lng in centroids:
        pid = resolve_prop_id(lat, lng)
        if not pid:
            time.sleep(1.0)
            continue
        try:
            data = _get(f"{PORTAL_BASE}/dcp", params={"id": pid, "type": "property"},
                        headers=PORTAL_HEADERS)
        except Exception as e:
            res.failure = f"/dcp call failed: {e}"
            time.sleep(1.0)
            continue
        if not isinstance(data, list) or not data:
            res.failure = f"/dcp returned no records ({type(data).__name__})"
            time.sleep(1.0)
            continue
        got = data[0].get("lgaName")
        got_n, want_n = _norm(got or ""), _norm(expect)
        # Containment, not equality: the portal may say 'CITY OF SYDNEY' where
        # the cadastre index says 'SYDNEY'. A centroid can also land on a
        # parcel just across the LGA boundary — that is a wrong PARCEL, not a
        # wrong LGA, so the next centroid is tried rather than giving up.
        if not got_n or (got_n not in want_n and want_n not in got_n):
            res.failure = (f"lgaName mismatch: portal says {got!r}, "
                           f"expected {expect!r}")
            time.sleep(1.0)
            continue
        res.prop_id, res.lga_name, res.raw, rec = pid, got, data, data[0]
        res.failure = None
        break
    if rec is None:
        res.failure = res.failure or "no propId resolved from any centroid"
        return res

    chosen, why_not = pick_dcp_result(registry_names, rec.get("dcpResults") or [])
    if chosen is None:
        res.failure = why_not
        res.checked_unattached = True
        return res
    res.plan_name = chosen.get("planName")
    res.plan_url = chosen.get("planURL")

    # Date extraction: planName first, then the URL-decoded planURL.
    for text, where in ((res.plan_name, "planName"),
                       (urllib.parse.unquote((res.plan_url or "").replace("+", " ")), "planURL")):
        hit = parse_dated_phrase(text or "")
        if hit:
            res.date_iso, res.precision, res.kind, sub = hit
            res.evidence = f"{where}: …{sub}…"
            break
    if res.date_iso and chosen.get("_shared_phrase_count"):
        res.evidence += (f" [identical dated phrase across "
                         f"{chosen['_shared_phrase_count']} matched plan entries]")
    if not res.date_iso:
        res.notes.append("plan record carries no explicit dated phrase (Goulburn class)")
    return res


def main() -> int:  # pragma: no cover - CLI entry point
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="Write results to dcp_plan_as_at. Default: dry run.")
    ap.add_argument("--slug", action="append",
                    help="Limit to specific slug(s); default = every served LGA.")
    args = ap.parse_args()

    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set — nothing was checked, which is not "
              "a pass. Exiting 2.", file=sys.stderr)
        return 2
    import psycopg2

    # prior-art-checked: connection shape follows scripts/repair_canada_bay_rear_setback.py
    # (DATABASE_URL + 30s statement_timeout); a service-module import is not viable
    # for a one-shot ops script per the house repair-script pattern.
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")
    conn.commit()

    cur.execute(
        """SELECT DISTINCT lga FROM dcp_setback_controls
            WHERE is_current = TRUE AND lga <> 'nsw_statewide' ORDER BY lga""")
    slugs = [r[0] for r in cur.fetchall()]
    if args.slug:
        unknown = set(args.slug) - set(slugs)
        if unknown:
            print(f"ERROR: not served slugs: {sorted(unknown)}", file=sys.stderr)
            return 2
        slugs = [s for s in slugs if s in args.slug]
    print(f"{len(slugs)} served LGAs to check (nsw_statewide excluded — no "
          f"portal geography for statewide instruments)")

    # Per-slug centroid lookups: LIMIT 3 with an equality filter short-circuits
    # the 3.1M-row scan as soon as three matches are found (every served slug
    # verified to have matches, 2026-08-03), keeping each query inside the 30s
    # statement_timeout.
    centroids: dict[str, list[tuple[float, float]]] = {}
    for slug in slugs:
        if slug in FORMER_COUNCIL_SLUGS:
            where, param = "former_council = %s", slug
            key = slug
        else:
            key = SLUG_TO_INDEX_LGA.get(slug, slug.replace("_", " ").upper())
            where, param = "lga_name = %s", key
        # Sampling filter only: ANY residential lot serves as a portal probe
        # point; no regulatory meaning attaches to the zone values and no
        # served output depends on them.
        probe_zones = ("R2", "R3")  # noqa: zone-codes
        cur.execute(
            f"""SELECT ST_Y(ST_Centroid(geom))::float, ST_X(ST_Centroid(geom))::float
                  FROM lot_search_index
                 WHERE {where} AND zone_code IN %s
                   AND lot_area_m2 BETWEEN 300 AND 900 AND geom IS NOT NULL
                 LIMIT 3""",
            (param, probe_zones),
        )
        centroids[key] = [(lat, lng) for lat, lng in cur.fetchall()]

    # Served-plan identities to anchor portal selection to (see pick_dcp_result).
    cur.execute(
        """SELECT council, ARRAY_AGG(DISTINCT dcp_name)
             FROM dcp_chapter_registry
            WHERE is_active = TRUE AND dcp_name IS NOT NULL
            GROUP BY council""")
    registry_names = dict(cur.fetchall())

    results: list[PortalResult] = []
    for slug in slugs:
        key = slug if slug in FORMER_COUNCIL_SLUGS else (
            SLUG_TO_INDEX_LGA.get(slug, slug.replace("_", " ").upper()))
        cands = centroids.get(key) or []
        if not cands:
            r = PortalResult(slug=slug, failure=f"no lot_search_index centroid under key {key!r}")
        else:
            r = fetch_one(slug, cands, registry_names.get(slug) or [])
        results.append(r)
        status = r.failure or (f"{r.date_iso} ({r.precision}, {r.kind})" if r.date_iso
                               else "record found, no dated phrase")
        print(f"  {slug:22s} propId={r.prop_id!s:9s} {status}")
        time.sleep(1.2)  # politeness between portal round-trips

    # prior-art-checked: this is the same script's own upsert loop being
    # extended with the clear-on-checked-unattached rule (Sol finding 1,
    # 2026-08-03); no other module writes dcp_plan_as_at.
    ok = [r for r in results if not r.failure]
    unattached = [r for r in results if r.failure and r.checked_unattached]
    dated = [r for r in ok if r.date_iso]
    print(f"\nportal records: {len(ok)}/{len(results)}; with explicit dated "
          f"phrase: {len(dated)}; checked-but-unattached (portal date cleared): "
          f"{len(unattached)}; infrastructure failures (untouched): "
          f"{len(results) - len(ok) - len(unattached)}")

    if not args.apply:
        print(f"\nDRY RUN — nothing written. --apply would upsert {len(ok)} "
              f"attached rows and clear the portal date on {len(unattached)} "
              f"checked-but-unattached rows.")
        return 0

    print(f"\npredicted writes: {len(ok)} attach-upserts + {len(unattached)} "
          f"clear-upserts (infrastructure failures never touch a row)")
    written = 0
    # A checked-but-unattached result stores WHAT was checked and WHY nothing
    # attached, and nulls any previously attached portal date — an old date
    # must not keep serving under a changed plan identity.
    for r in results:
        if r.failure and not r.checked_unattached:
            continue
        raw_payload = None
        if r.raw is not None:
            payload = {"response": r.raw}
            if r.checked_unattached:
                payload["unattached_reason"] = r.failure
            raw_payload = json.dumps(payload)
        attach = not r.failure
        cur.execute(
            """
            INSERT INTO dcp_plan_as_at
                (lga, portal_prop_id, portal_lga_name, portal_plan_name,
                 portal_plan_url, portal_date, portal_date_precision,
                 portal_date_kind, portal_date_evidence, portal_checked_at,
                 portal_raw, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now(), %s, now())
            ON CONFLICT (lga) DO UPDATE SET
                portal_prop_id = EXCLUDED.portal_prop_id,
                portal_lga_name = EXCLUDED.portal_lga_name,
                portal_plan_name = EXCLUDED.portal_plan_name,
                portal_plan_url = EXCLUDED.portal_plan_url,
                portal_date = EXCLUDED.portal_date,
                portal_date_precision = EXCLUDED.portal_date_precision,
                portal_date_kind = EXCLUDED.portal_date_kind,
                portal_date_evidence = EXCLUDED.portal_date_evidence,
                portal_checked_at = EXCLUDED.portal_checked_at,
                portal_raw = EXCLUDED.portal_raw,
                updated_at = now()
            """,
            (r.slug, r.prop_id, r.lga_name,
             r.plan_name if attach else None,
             r.plan_url if attach else None,
             r.date_iso if attach else None,
             r.precision if attach else None,
             r.kind if attach else None,
             r.evidence if attach else None,
             raw_payload),
        )
        written += cur.rowcount
    conn.commit()
    predicted = len(ok) + len(unattached)
    print(f"wrote {written} rows (predicted {predicted})")

    cur.execute("SELECT COUNT(*), COUNT(portal_date), COUNT(portal_checked_at) "
                "FROM dcp_plan_as_at")
    total, with_date, checked = cur.fetchone()
    print(f"post-write verify: dcp_plan_as_at rows={total}, portal_date "
          f"set={with_date}, portal_checked_at set={checked}")
    conn.close()
    return 0 if written == predicted else 2


if __name__ == "__main__":
    sys.exit(main())
