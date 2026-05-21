#!/usr/bin/env python3
"""
Convert secondary_dwelling_stats.py JSON output → TypeScript data file.

Reads JSON from stdin (or --input file), writes the TypeScript file that
frontend-nextjs/lib/lga-data/secondary-dwelling-stats.ts expects.

Usage:
    python scripts/secondary_dwelling_stats.py | python scripts/json_to_ts_stats.py
    python scripts/json_to_ts_stats.py --input stats.json
"""

import argparse
import json
import re
import sys
from datetime import date


def _slugify(council_name: str) -> str:
    """Match the slug logic used in the original TS file generation."""
    name = council_name
    for suffix in [
        " City Council",
        " Shire Council",
        " Regional Council",
        " Council",
    ]:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _short_name(council_name: str) -> str:
    for suffix in [
        " City Council",
        " Shire Council",
        " Regional Council",
        " Council",
    ]:
        if council_name.endswith(suffix):
            return council_name[: -len(suffix)]
    return council_name


def _ts_value(val: object) -> str:
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        return json.dumps(val)
    if isinstance(val, dict):
        return json.dumps(val)
    return json.dumps(val)


def convert(data: dict, output_path: str) -> None:
    metadata = data.get("metadata", {})
    councils = data.get("councils", {})

    generated_at = metadata.get("generated_at", "")
    data_as_of = generated_at[:10] if generated_at else date.today().isoformat()

    lines: list[str] = []
    lines.append("/**")
    lines.append(
        " * Secondary dwelling DA/CDC statistics by council."
    )
    lines.append(
        " * Generated from NSW Planning Portal data via scripts/secondary_dwelling_stats.py"
    )
    lines.append(
        " * Source: https://www.planningportal.nsw.gov.au/opendata/dataset/online-da-data-api"
    )
    lines.append(" */")
    lines.append("")
    lines.append(
        "/** ISO date string — when the stats were last generated from the Planning Portal */"
    )
    lines.append(f"export const DATA_AS_OF = '{data_as_of}'")
    lines.append("")
    lines.append("export interface YearlyStats {")
    lines.append("  da_count: number")
    lines.append("  cdc_count: number")
    lines.append("  total: number")
    lines.append("}")
    lines.append("")
    lines.append("export interface CouncilStats {")
    lines.append("  councilName: string")
    lines.append("  shortName: string")
    lines.append("  slug: string")
    lines.append("  totalApplications: number")
    lines.append("  daTotal: number")
    lines.append("  daDetermined: number")
    lines.append("  daMedianDays: number | null")
    lines.append("  daAvgCost: number | null")
    lines.append("  daMedianCost: number | null")
    lines.append("  cdcTotal: number")
    lines.append("  cdcMedianDays: number | null")
    lines.append("  cdcAvgCost: number | null")
    lines.append("  cdcMedianCost: number | null")
    lines.append("  cdcRatioPct: number | null")
    lines.append("  earliestDate: string | null")
    lines.append("  latestDate: string | null")
    lines.append("  yearly: Record<string, YearlyStats>")
    lines.append("}")
    lines.append("")
    lines.append("export const COUNCIL_STATS: CouncilStats[] = [")

    for council_name in sorted(councils.keys()):
        s = councils[council_name]
        slug = _slugify(council_name)
        short = _short_name(council_name)
        lines.append("  {")
        lines.append(f'    councilName: {json.dumps(council_name)},')
        lines.append(f'    shortName: {json.dumps(short)},')
        lines.append(f'    slug: {json.dumps(slug)},')
        lines.append(f'    totalApplications: {s["total_applications"]},')
        lines.append(f'    daTotal: {s["da_total"]},')
        lines.append(f'    daDetermined: {s["da_determined"]},')
        lines.append(f"    daMedianDays: {_ts_value(s['da_median_determination_days'])},")
        lines.append(f"    daAvgCost: {_ts_value(s['da_avg_cost'])},")
        lines.append(f"    daMedianCost: {_ts_value(s['da_median_cost'])},")
        lines.append(f'    cdcTotal: {s["cdc_total"]},')
        lines.append(f"    cdcMedianDays: {_ts_value(s['cdc_median_determination_days'])},")
        lines.append(f"    cdcAvgCost: {_ts_value(s['cdc_avg_cost'])},")
        lines.append(f"    cdcMedianCost: {_ts_value(s['cdc_median_cost'])},")
        lines.append(f"    cdcRatioPct: {_ts_value(s['cdc_ratio_pct'])},")
        lines.append(f"    earliestDate: {_ts_value(s['earliest_date'])},")
        lines.append(f"    latestDate: {_ts_value(s['latest_date'])},")
        lines.append(f"    yearly: {json.dumps(s.get('yearly', {}))},")
        lines.append("  },")

    lines.append("]")
    lines.append("")
    lines.append(
        "export const COUNCIL_STATS_BY_SLUG: Record<string, CouncilStats> = Object.fromEntries("
    )
    lines.append("  COUNCIL_STATS.map(c => [c.slug, c])")
    lines.append(")")
    lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(
        f"Wrote {len(councils)} councils to {output_path} (DATA_AS_OF={data_as_of})",
        file=sys.stderr,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert secondary dwelling stats JSON to TypeScript"
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Input JSON file (default: stdin)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="frontend-nextjs/lib/lga-data/secondary-dwelling-stats.ts",
        help="Output TypeScript file path",
    )
    args = parser.parse_args()

    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    convert(data, args.output)


if __name__ == "__main__":
    main()
