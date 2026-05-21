#!/usr/bin/env python3
"""
Secondary Dwelling DA/CDC Statistics by LGA
============================================

Queries the DA Supabase (nsw-planning-etl) for secondary dwelling applications
across all NSW councils. Produces per-LGA statistics for blog content and
granny flat SEO pages.

Data source: NSW Planning Portal Online DA/CDC data
  - https://www.planningportal.nsw.gov.au/opendata/dataset/online-da-data-api
  - Mandatory for all councils from 1 July 2021
  - Updated daily via nsw-planning-etl GitHub Actions

IMPORTANT — Defensibility notes:
  - All statistics are derived from publicly available NSW Planning Portal data
  - DA ApplicationStatus in the portal is ONLY "Determined" — no approved/refused
    distinction is available from this dataset. We report DA volumes and processing
    times but CANNOT report DA approval rates.
  - CDC ApplicationStatus is "Approved" — all CDCs in the dataset are issued
    certificates. CDCs that were rejected never appear in the portal data.
  - DevelopmentType matching uses the exact NSW Planning Portal taxonomy values,
    stored as JSON text: [{"DevelopmentType": "Secondary dwelling"}]
  - Description-text matching is used as fallback for applications where the
    DevelopmentType field doesn't contain a secondary dwelling keyword but the
    description does. These are counted separately for transparency.
  - Results should be presented as "observed application volumes and processing
    times" — NOT as "approval likelihood" or "council friendliness"
  - Cost figures are self-reported by applicants at lodgement

Usage:
    python scripts/secondary_dwelling_stats.py [--output csv|json] [--council "Council Name"]
"""

import argparse
import csv
import io
import json
import os
import sys
from datetime import datetime
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DA_SUPABASE_URL = os.environ.get(
    "DA_SUPABASE_URL",
    "https://yfzvvghmywbhhwdhhbjo.supabase.co",
)
DA_SUPABASE_KEY = os.environ.get(
    "DA_SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlmenZ2Z2hteXdiaGh3ZGhoYmpvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY0NDUzMjgsImV4cCI6MjA2MjAyMTMyOH0.U_0Wj-7lwtjLeWmSf2wG9iHjrTBirHTqc7Om18mx5BE",
)

# NSW Planning Portal DevelopmentType taxonomy values for secondary dwellings.
# Stored as JSON text arrays: [{"DevelopmentType": "Secondary dwelling"}]
# "Dual occupancy" is EXCLUDED — separate SEPP provisions, not a granny flat.
SECONDARY_DWELLING_KEYWORDS = [
    "secondary dwelling",
    "granny flat",
    "ancillary dwelling",
]

# Description-level fallback keywords (only used when DevelopmentType doesn't match)
DESCRIPTION_KEYWORDS = [
    "granny flat",
    "secondary dwelling",
    "ancillary dwelling",
    "dependent person",  # "dependent person's unit" — SEPP Housing term
]

SUPABASE_REST = f"{DA_SUPABASE_URL}/rest/v1"
PAGE_SIZE = 1000


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def _headers() -> dict[str, str]:
    return {
        "apikey": DA_SUPABASE_KEY,
        "Authorization": f"Bearer {DA_SUPABASE_KEY}",
    }


def fetch_council_list(client: httpx.Client) -> list[str]:
    """Get all unique council names from the DA table."""
    councils: set[str] = set()
    offset = 0
    while True:
        r = client.get(f"{SUPABASE_REST}/development_applications", params={
            "select": "council_name",
            "limit": str(PAGE_SIZE),
            "offset": str(offset),
            "order": "council_name",
        })
        r.raise_for_status()
        rows = r.json()
        for row in rows:
            councils.add(row["council_name"])
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return sorted(councils)


def fetch_council_das(
    client: httpx.Client,
    council: str,
    since: str,
) -> list[dict[str, Any]]:
    """Fetch all DAs for a single council since a given date."""
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        r = client.get(f"{SUPABASE_REST}/development_applications", params={
            "select": "development_type,description,application_status,"
                      "lodgement_date,determination_date,cost_of_development",
            "council_name": f"eq.{council}",
            "lodgement_date": f"gte.{since}",
            "limit": str(PAGE_SIZE),
            "offset": str(offset),
        })
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def fetch_council_cdcs(
    client: httpx.Client,
    council: str,
    since: str,
) -> list[dict[str, Any]]:
    """Fetch all CDCs for a single council since a given date."""
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        r = client.get(f"{SUPABASE_REST}/complying_development_certificates", params={
            "select": "development_type,description,application_status,"
                      "submission_date,determination_date,cost_of_development",
            "council_name": f"eq.{council}",
            "submission_date": f"gte.{since}",
            "limit": str(PAGE_SIZE),
            "offset": str(offset),
        })
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def _is_secondary_dwelling(row: dict[str, Any]) -> tuple[bool, str]:
    """Check if a row is a secondary dwelling application.

    Returns (matched, method) where method is 'type' or 'description'.
    """
    dt_raw = row.get("development_type") or ""
    if isinstance(dt_raw, str):
        dt_lower = dt_raw.lower()
        if any(kw in dt_lower for kw in SECONDARY_DWELLING_KEYWORDS):
            return True, "type"

    desc = (row.get("description") or "").lower()
    if any(kw in desc for kw in DESCRIPTION_KEYWORDS):
        return True, "description"

    return False, ""


def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        pass
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _median(values: list[int | float]) -> int | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return round((s[mid - 1] + s[mid]) / 2)
    return round(s[mid])


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _year_from_date(date_str: str | None) -> int | None:
    """Extract year from a date string. Returns None if unparseable."""
    d = _parse_date(date_str)
    return d.year if d else None


def aggregate_stats(
    since: str = "2021-07-01",
    council_filter: str | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Aggregate secondary dwelling DA and CDC stats by council.

    Per council:
      DA metrics:
        - da_total: total secondary dwelling DAs lodged
        - da_determined: DAs with "Determined" status (= decided, outcome unknown)
        - da_median_determination_days: median lodgement→determination (determined DAs)
        - da_avg_cost, da_median_cost: self-reported cost of development
        - da_description_match: count matched by description text, not DevelopmentType

      CDC metrics:
        - cdc_total: total secondary dwelling CDCs issued (all "Approved" in portal)
        - cdc_median_determination_days: median submission→determination
        - cdc_avg_cost, cdc_median_cost

      Combined:
        - total_applications: da_total + cdc_total
        - cdc_ratio_pct: % of applications that used the CDC pathway
        - earliest_date, latest_date: data coverage

      Yearly breakdown:
        - yearly: dict[year] → {da_count, cdc_count, total}
    """
    stats: dict[str, dict[str, Any]] = {}

    with httpx.Client(headers=_headers(), timeout=60.0) as client:
        if council_filter:
            councils = [council_filter]
        else:
            print("Fetching council list...", file=sys.stderr)
            councils = fetch_council_list(client)
            print(f"  {len(councils)} councils found", file=sys.stderr)

        total_da_fetched = 0
        total_cdc_fetched = 0
        total_da_matched = 0
        total_cdc_matched = 0

        for i, council in enumerate(councils):
            if (i + 1) % 20 == 0 or i == 0:
                print(
                    f"  Processing {i+1}/{len(councils)}: {council}...",
                    file=sys.stderr,
                )

            # ---- DAs ----
            da_rows = fetch_council_das(client, council, since)
            total_da_fetched += len(da_rows)

            da_det_days: list[int] = []
            da_costs: list[float] = []
            da_total = 0
            da_determined = 0
            da_desc_match = 0
            earliest: str | None = None
            latest: str | None = None
            yearly_da: dict[int, int] = {}

            for row in da_rows:
                matched, method = _is_secondary_dwelling(row)
                if not matched:
                    continue

                da_total += 1
                total_da_matched += 1
                if method == "description":
                    da_desc_match += 1

                # Yearly count
                yr = _year_from_date(row.get("lodgement_date"))
                if yr:
                    yearly_da[yr] = yearly_da.get(yr, 0) + 1

                status = (row.get("application_status") or "").lower()
                if "determined" in status:
                    da_determined += 1
                    lodged = _parse_date(row.get("lodgement_date"))
                    determined = _parse_date(row.get("determination_date"))
                    if lodged and determined and determined >= lodged:
                        days = (determined - lodged).days
                        if 0 <= days <= 730:
                            da_det_days.append(days)

                cost = _safe_float(row.get("cost_of_development"))
                if cost and cost > 0:
                    da_costs.append(cost)

                lodged = _parse_date(row.get("lodgement_date"))
                if lodged:
                    d = lodged.strftime("%Y-%m-%d")
                    if not earliest or d < earliest:
                        earliest = d
                    if not latest or d > latest:
                        latest = d

            # ---- CDCs ----
            cdc_rows = fetch_council_cdcs(client, council, since)
            total_cdc_fetched += len(cdc_rows)

            cdc_det_days: list[int] = []
            cdc_costs: list[float] = []
            cdc_total = 0
            yearly_cdc: dict[int, int] = {}

            for row in cdc_rows:
                matched, _ = _is_secondary_dwelling(row)
                if not matched:
                    continue

                cdc_total += 1
                total_cdc_matched += 1

                # Yearly count
                yr = _year_from_date(row.get("submission_date"))
                if yr:
                    yearly_cdc[yr] = yearly_cdc.get(yr, 0) + 1

                cost = _safe_float(row.get("cost_of_development"))
                if cost and cost > 0:
                    cdc_costs.append(cost)

                submitted = _parse_date(row.get("submission_date"))
                determined = _parse_date(row.get("determination_date"))
                if submitted and determined and determined >= submitted:
                    days = (determined - submitted).days
                    if 0 <= days <= 365:
                        cdc_det_days.append(days)

                if submitted:
                    d = submitted.strftime("%Y-%m-%d")
                    if not earliest or d < earliest:
                        earliest = d
                    if not latest or d > latest:
                        latest = d

            # ---- Skip councils with zero secondary dwelling applications ----
            if da_total == 0 and cdc_total == 0:
                continue

            # Build yearly breakdown
            all_years = sorted(set(list(yearly_da.keys()) + list(yearly_cdc.keys())))
            yearly = {}
            for yr in all_years:
                da_yr = yearly_da.get(yr, 0)
                cdc_yr = yearly_cdc.get(yr, 0)
                yearly[str(yr)] = {
                    "da_count": da_yr,
                    "cdc_count": cdc_yr,
                    "total": da_yr + cdc_yr,
                }

            total = da_total + cdc_total
            stats[council] = {
                "total_applications": total,
                # DA metrics
                "da_total": da_total,
                "da_determined": da_determined,
                "da_median_determination_days": _median(da_det_days),
                "da_avg_cost": round(sum(da_costs) / len(da_costs)) if da_costs else None,
                "da_median_cost": _median(da_costs),
                "da_description_match": da_desc_match,
                # CDC metrics
                "cdc_total": cdc_total,
                "cdc_median_determination_days": _median(cdc_det_days),
                "cdc_avg_cost": round(sum(cdc_costs) / len(cdc_costs)) if cdc_costs else None,
                "cdc_median_cost": _median(cdc_costs),
                # Combined
                "cdc_ratio_pct": round(cdc_total / total * 100, 1) if total > 0 else None,
                # Date range
                "earliest_date": earliest,
                "latest_date": latest,
                # Yearly breakdown
                "yearly": yearly,
            }

    print(
        f"\n  Fetched {total_da_fetched} DAs + {total_cdc_fetched} CDCs",
        file=sys.stderr,
    )
    print(
        f"  Matched {total_da_matched} secondary dwelling DAs + "
        f"{total_cdc_matched} CDCs",
        file=sys.stderr,
    )

    return stats


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    "council_name",
    "total_applications",
    "da_total",
    "da_determined",
    "da_median_determination_days",
    "da_avg_cost",
    "da_median_cost",
    "da_description_match",
    "cdc_total",
    "cdc_median_determination_days",
    "cdc_avg_cost",
    "cdc_median_cost",
    "cdc_ratio_pct",
    "earliest_date",
    "latest_date",
]


def output_csv(stats: dict[str, dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for council in sorted(stats.keys()):
        row = {"council_name": council, **stats[council]}
        writer.writerow({k: row.get(k) for k in CSV_COLUMNS})
    return buf.getvalue()


def output_json(stats: dict[str, dict[str, Any]]) -> str:
    output = {
        "metadata": {
            "source": "NSW Planning Portal — Online DA/CDC open data",
            "source_url": "https://www.planningportal.nsw.gov.au/opendata/dataset/online-da-data-api",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "methodology": {
                "da_matching": (
                    "DAs are matched by DevelopmentType JSON field containing "
                    "'Secondary dwelling', 'Granny flat', or 'Ancillary dwelling'. "
                    "Fallback: description text containing these terms plus "
                    "'Dependent person' (SEPP Housing 2021 terminology). "
                    "Description-only matches are counted separately."
                ),
                "cdc_matching": "Same keywords applied to CDC DevelopmentType and description fields.",
                "da_status_note": (
                    "The NSW Planning Portal records ALL decided DAs as 'Determined' — "
                    "there is no approved/refused distinction in the OnlineDA dataset. "
                    "DA approval rates CANNOT be derived from this data. "
                    "da_determined counts DAs that have been decided, not DAs that were approved."
                ),
                "cdc_status_note": (
                    "All CDCs in the portal dataset have status 'Approved'. "
                    "Rejected CDC applications are not published. "
                    "cdc_total therefore represents issued certificates only."
                ),
                "cost_note": "Cost of development is self-reported by applicants at lodgement and may not reflect actual construction costs.",
                "determination_days": "Calculated as calendar days from lodgement/submission to determination date. Outliers >730 days (DA) or >365 days (CDC) are excluded.",
                "minimum_date": "Data mandatory for all councils from 1 July 2021. Earlier records exist for some councils.",
            },
            "exclusions": [
                "Dual occupancy applications (separate SEPP provisions, not secondary dwellings)",
                "Boarding houses, group homes, seniors housing (separate development types)",
                "Modification applications to existing secondary dwelling approvals (captured under original DA type)",
            ],
            "disclaimer": (
                "This data is sourced from the NSW Planning Portal and reflects "
                "recorded application volumes and processing times. It does not "
                "constitute planning advice, does not indicate approval likelihood, "
                "and does not predict future application outcomes. Individual "
                "application outcomes depend on site-specific conditions, applicable "
                "planning controls, and the merits of each proposal."
            ),
        },
        "councils": {
            council: stats[council]
            for council in sorted(stats.keys())
        },
    }
    return json.dumps(output, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Secondary dwelling DA/CDC statistics by LGA"
    )
    parser.add_argument(
        "--output", choices=["csv", "json"], default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--council", type=str, default=None,
        help="Filter to a single council name (exact match)",
    )
    parser.add_argument(
        "--since", type=str, default="2021-07-01",
        help="Start date (default: 2021-07-01, when reporting became mandatory)",
    )
    args = parser.parse_args()

    stats = aggregate_stats(since=args.since, council_filter=args.council)

    if not stats:
        print("No secondary dwelling applications found.", file=sys.stderr)
        sys.exit(0)

    if args.output == "csv":
        print(output_csv(stats))
    else:
        print(output_json(stats))

    # Summary to stderr
    total_councils = len(stats)
    total_das = sum(s["da_total"] for s in stats.values())
    total_cdcs = sum(s["cdc_total"] for s in stats.values())
    print(
        f"\nSummary: {total_councils} councils, "
        f"{total_das} DAs, {total_cdcs} CDCs, "
        f"{total_das + total_cdcs} total secondary dwelling applications",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
