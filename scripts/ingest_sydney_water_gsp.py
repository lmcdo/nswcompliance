#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no existing module ingests the Sydney Water
#   Growth Servicing Plan — grep for growth.servicing|GSP_WW|sydney_water_gsp across
#   services/ scripts/ frontend returns nothing. Flagged files (portal_constraints,
#   pre_da_history, flood_truth) are unrelated pipelines sharing only generic tokens
#   (parse/geom/status/water). This is a new data source + new table (migration 058).
"""
Ingest Sydney Water Growth Servicing Plan (GSP) polygons into
`sydney_water_gsp_servicing` (migration 058).

Ingests the two SERVICING GeoJSON files (GSP_WW = wastewater, GSP_DW = drinking
water). The third public file, GSP_AdditionalComments.json (4 broad advisory
link-out polygons with no stage/timeframe/price), is intentionally NOT ingested here
— it carries no serviceability status and does not fit this table; treat it as a
separate advisory layer if ever needed. Refresh is idempotent: upsert on
(product, swc_id) then delete any rows no longer in the source (snapshot replace).

Data-handling rules baked in (see docs/servicing/gsp-smoketest-findings.md):
  * DSP price: parse the leading $ out of the HTML blob → dsp_price_per_et (nullable;
    $0 valid). Keep the HTML-stripped source string in dsp_price_raw. It is a CPI-
    excluded BASE snapshot — the reader layer must show the caveat + link, never present
    it as the live charge.
  * Existing_Servicing_Information is NOT ingested — identical dead PDF pointer on every row.
  * status_code is derived (IN_DELIVERY|PLANNED|NO_CURRENT_PROJECT|UNKNOWN_STAGE);
    the capacity-constraint note sets the separate `constrained` boolean.

Usage:
    python scripts/ingest_sydney_water_gsp.py --dry-run     # validate only, no DB
    python scripts/ingest_sydney_water_gsp.py --apply       # upsert into live DB
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import requests
from shapely import make_valid
from shapely.geometry import MultiPolygon, Polygon, shape

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "sydney_water_gsp"
CDN = "https://www.sydneywater.com.au/content/dam/sydneywater/applications/gsp/"
# Only the two servicing layers. GSP_AdditionalComments.json is deliberately excluded
# (see module docstring) — advisory link-outs, no serviceability status.
FILES = {"WW": "GSP_WW.json", "DW": "GSP_DW.json"}
EXPECTED_ROWS = 397  # baseline snapshot (205 WW + 192 DW) — soft check; refresh may differ

_HTML = re.compile(r"<[^>]+>")
_PRICE = re.compile(r"\$\s*([\d,]+(?:\.\d+)?)")

# Sydney Water project-stage ladder → derived base status.
_STAGE_BASE = {
    "Design & Deliver": "IN_DELIVERY",
    "Concept Planning": "PLANNED",
    "Option Planning": "PLANNED",
    "Strategic Planning": "PLANNED",
}
_VALID_STATUS = {"IN_DELIVERY", "PLANNED", "NO_CURRENT_PROJECT", "UNKNOWN_STAGE"}


def clean(text: str | None) -> str | None:
    if not text:
        return None
    stripped = _HTML.sub("", text).strip()
    return stripped or None


def parse_dsp_price(raw: str | None) -> float | None:
    if not raw:
        return None
    m = _PRICE.match(raw.strip())
    return float(m.group(1).replace(",", "")) if m else None


def derive_status(stage: str | None, special: str | None) -> tuple[str, bool]:
    """Return (base_status_code, constrained). Never merges the two."""
    stage = (stage or "").strip()
    constrained = "capacity and timescale constraints" in (special or "").lower()
    if stage.startswith("Growth precinct boundary"):
        base = "NO_CURRENT_PROJECT"
    else:
        base = _STAGE_BASE.get(stage, "UNKNOWN_STAGE")
    return base, constrained


def _polygonal_parts(geom) -> list[Polygon]:
    """Every Polygon component of a geometry, flattening MultiPolygon/GeometryCollection.

    make_valid can return a GeometryCollection mixing polygons with stray lines/points;
    we keep only the polygonal area and drop the degenerate bits.
    """
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    parts: list[Polygon] = []
    for g in getattr(geom, "geoms", []):
        parts.extend(_polygonal_parts(g))
    return parts


def geom_to_multipolygon_wkt(geojson_geom: dict) -> str:
    geom = shape(geojson_geom)
    # Repair with make_valid (NOT buffer(0), which can silently discard a lobe of a
    # multi-part polygon). Then keep ALL polygonal parts so no footprint is lost.
    if not geom.is_valid:
        geom = make_valid(geom)
    parts = _polygonal_parts(geom)
    # Single guard: empty input, a degenerate repair, or a non-polygonal geometry all
    # land here as zero parts and fail loudly rather than storing junk.
    if not parts:
        raise ValueError(f"no polygonal geometry (got {geom.geom_type})")
    return MultiPolygon(parts).wkt


def download_if_missing() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    hdr = {"User-Agent": "Mozilla/5.0 (compatible; PlotDetect-ingest/1.0)"}
    for fn in FILES.values():
        path = DATA_DIR / fn
        if path.exists():
            continue
        print(f"  downloading {fn} ...")
        r = requests.get(CDN + fn, headers=hdr, timeout=60)
        r.raise_for_status()
        path.write_bytes(r.content)


def transform() -> list[dict]:
    rows: list[dict] = []
    for product, fn in FILES.items():
        data = json.loads((DATA_DIR / fn).read_text(encoding="utf-8"))
        for feat in data["features"]:
            p = feat["properties"]
            swc_id = (p.get("SWC_Unique_Identifier") or "").strip()
            if not swc_id:
                raise ValueError(f"{product}: feature with no SWC_Unique_Identifier")
            special = p.get("Special_Comments")  # DW file has no such key → None
            status, constrained = derive_status(
                p.get("SWC_Planning_Project_Stage"), special
            )
            # Store every real note (both the 4 "capacity constraints" and the 8
            # "under investigation by DPHI"), not just the constrained ones — dropping
            # the DPHI caveat would lose real signal. `constrained` stays narrow.
            note = clean(special)
            if note and note.lower() == "none":
                note = None
            raw_price = p.get("Indicative_DSP_Full_Prices_(per_ET)")
            rows.append(
                {
                    "product": product,
                    "swc_id": swc_id,
                    "polygon_name": clean(p.get("Growth_Polygon_Name")),
                    "growth_area": clean(p.get("Growth_Area")),
                    "status_code": status,
                    "stage": clean(p.get("SWC_Planning_Project_Stage")),
                    "timeframe": clean(p.get("Indicative_Timeframe_by_Financial_Year(FY)")),
                    "dsp_price_per_et": parse_dsp_price(raw_price),
                    "dsp_price_raw": clean(raw_price),
                    "dsp_area": clean(p.get("Development_Servicing_Plan_(DSP)_Area")),
                    "constrained": constrained,
                    "special_comments": note,
                    "commentary": clean(p.get("GSP_Commentary")),
                    "wkt": geom_to_multipolygon_wkt(feat["geometry"]),
                }
            )
    return rows


def _require(cond: bool, msg: str) -> None:
    """Integrity guard that survives python -O (unlike assert)."""
    if not cond:
        raise RuntimeError(f"integrity check failed: {msg}")


def summarize(rows: list[dict]) -> None:
    print(f"\nTransformed {len(rows)} rows total")
    for product in ("WW", "DW"):
        sub = [r for r in rows if r["product"] == product]
        statuses = Counter(r["status_code"] for r in sub)
        constrained = sum(r["constrained"] for r in sub)
        priced = sum(r["dsp_price_per_et"] is not None for r in sub)
        print(f"  {product}: {len(sub)} rows · statuses={dict(statuses)} · "
              f"constrained={constrained} · with_price={priced}/{len(sub)}")
    # Row count is a soft check — a GSP refresh legitimately changes the total. Warn on
    # drift from the known baseline but don't block (structural checks below stay hard).
    if len(rows) != EXPECTED_ROWS:
        print(f"  [WARN] source has {len(rows)} rows (baseline {EXPECTED_ROWS}) — GSP may "
              "have been updated; review the diff before ingesting.")
    # Integrity checks — explicit raises, NOT assert (assert is stripped under python -O,
    # which would let bad data through silently).
    _require(all(r["status_code"] in _VALID_STATUS for r in rows), "unexpected status_code")
    _require(all(r["swc_id"] for r in rows), "blank swc_id")
    _require(all(r["wkt"].startswith("MULTIPOLYGON") for r in rows), "geom not multipolygon")
    keys = [(r["product"], r["swc_id"]) for r in rows]
    _require(len(keys) == len(set(keys)), "duplicate (product, swc_id)")
    unknown = [r["swc_id"] for r in rows if r["status_code"] == "UNKNOWN_STAGE"]
    if unknown:
        print(f"  [WARN] {len(unknown)} UNKNOWN_STAGE rows (unmapped stage): {unknown[:8]}")
    print("  integrity assertions: OK")


def apply(rows: list[dict]) -> None:
    import os

    from dotenv import load_dotenv
    import psycopg2
    from psycopg2.extras import execute_values

    load_dotenv(str(PROJECT_ROOT / ".env"))
    conn = psycopg2.connect(
        connect_timeout=15,
        host=os.getenv("PGHOST"), port=os.getenv("PGPORT"),
        dbname=os.getenv("PGDATABASE"), user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
    )
    conn.autocommit = False
    try:
        cur = conn.cursor()
        # Guard: table must exist (migration 058 applied) before we touch anything.
        cur.execute("SELECT to_regclass('public.sydney_water_gsp_servicing')")
        if cur.fetchone()[0] is None:
            raise RuntimeError(
                "Table sydney_water_gsp_servicing does not exist — apply migration "
                "058_sydney_water_gsp_servicing.sql first."
            )
        cur.execute("SELECT count(*) FROM sydney_water_gsp_servicing")
        before = cur.fetchone()[0]

        template = (
            "(%(product)s,%(swc_id)s,%(polygon_name)s,%(growth_area)s,%(status_code)s,"
            "%(stage)s,%(timeframe)s,%(dsp_price_per_et)s,%(dsp_price_raw)s,%(dsp_area)s,"
            "%(constrained)s,%(special_comments)s,%(commentary)s,"
            "ST_Multi(ST_GeomFromText(%(wkt)s,4326)))"
        )
        execute_values(
            cur,
            """
            INSERT INTO sydney_water_gsp_servicing
                (product, swc_id, polygon_name, growth_area, status_code, stage,
                 timeframe, dsp_price_per_et, dsp_price_raw, dsp_area, constrained,
                 special_comments, commentary, geom)
            VALUES %s
            ON CONFLICT (product, swc_id) DO UPDATE SET
                polygon_name=EXCLUDED.polygon_name, growth_area=EXCLUDED.growth_area,
                status_code=EXCLUDED.status_code, stage=EXCLUDED.stage,
                timeframe=EXCLUDED.timeframe, dsp_price_per_et=EXCLUDED.dsp_price_per_et,
                dsp_price_raw=EXCLUDED.dsp_price_raw, dsp_area=EXCLUDED.dsp_area,
                constrained=EXCLUDED.constrained, special_comments=EXCLUDED.special_comments,
                commentary=EXCLUDED.commentary, geom=EXCLUDED.geom, synced_at=now()
            """,
            rows,
            template=template,
            page_size=100,
        )
        # prior-art-checked: reuse not viable — snapshot-replace of the GSP servicing
        # table added inline to its own ingest (no shared ingest module deletes rows by
        # source-key set; flagged files are unrelated pipelines sharing generic tokens).
        # Snapshot replacement: remove any rows whose (product, swc_id) is no longer in
        # the current source, so a GSP refresh that retires a polygon doesn't leave a
        # stale row (which would also break an exact row-count gate). Today this deletes
        # 0 (fresh load); it matters on future refreshes.
        execute_values(
            cur,
            """
            DELETE FROM sydney_water_gsp_servicing t
            WHERE NOT EXISTS (
                SELECT 1 FROM (VALUES %s) AS s(product, swc_id)
                WHERE s.product = t.product AND s.swc_id = t.swc_id
            )
            """,
            [(r["product"], r["swc_id"]) for r in rows],
            page_size=1000,
            fetch=False,
        )
        cur.execute("SELECT count(*) FROM sydney_water_gsp_servicing")
        after = cur.fetchone()[0]
        # Gate on the source count, not a hard-coded number — the table must exactly
        # mirror the source snapshot after upsert + delete-absent.
        if after != len(rows):
            raise RuntimeError(
                f"expected {len(rows)} rows (source count) after refresh, found {after} "
                "— rolling back"
            )
        conn.commit()
        print(f"\nCOMMITTED. rows before={before}, after={after} "
              f"(+{after - before} net; source={len(rows)}).")
    except Exception:
        conn.rollback()
        print("\nROLLED BACK — no changes written.")
        raise
    finally:
        conn.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true", help="validate only, no DB")
    g.add_argument("--apply", action="store_true", help="upsert into the live DB")
    args = ap.parse_args()

    download_if_missing()
    rows = transform()
    summarize(rows)

    if args.apply:
        apply(rows)
    else:
        print("\nDRY RUN — no DB writes. Re-run with --apply to ingest.")


if __name__ == "__main__":
    main()
