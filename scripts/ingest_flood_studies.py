#!/usr/bin/env python3
"""
Multi-study flood shapefile ingest into spatial_overlays.

Downloads, inspects, and ingests flood extent shapefiles from the NSW Flood
Data Portal (flooddata.ses.nsw.gov.au) for priority Greater Sydney LGAs.

Studies covered:
  campbelltown   -- Campbelltown Design Flood Extents (Campbelltown / Camden)
  narellan       -- Narellan Creek Flood Study Extents (Camden)
  greendale      -- Greendale Creek Flood Study GIS Layers (Northern Beaches)
  south_creek_hc -- Updated South Creek Flood Study Hydraulic Categories (Penrith)

Usage:
  python scripts/ingest_flood_studies.py --inspect              # show column names only
  python scripts/ingest_flood_studies.py --study all            # ingest all studies
  python scripts/ingest_flood_studies.py --study campbelltown   # single study
  python scripts/ingest_flood_studies.py --dry-run --study all  # parse without DB insert

AEP column detection (in priority order):
  Column names containing AEP, ARI, FLOOD_CAT, SCENARIO, CATEGORY, CLASS are inspected.
  If a study has one shapefile per AEP scenario (Hawkesbury pattern), scenario is
  parsed from the filename instead.

  Campbelltown filename convention: 0p2AEP_Extent.shp (p = decimal point).

Adding new studies:
  Register a download_type="zip" entry in STUDIES with the direct /download/<file> URL
  from flooddata.ses.nsw.gov.au. Resource page URLs (without /download/) return HTML
  and require portal authentication -- only uploaded files have working direct URLs.
"""

import argparse
import os
import re
import sys
import zipfile
from datetime import date
from pathlib import Path
from typing import Optional

import geopandas as gpd
import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.extras import execute_values

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
load_dotenv()

CACHE_DIR = project_root / "data" / "flood_studies"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Study manifest
# ---------------------------------------------------------------------------
# download_type:
#   "zip"       -- single ZIP file; all .shp files inside are candidates
#   "shp_parts" -- individual SHP component files (SHP + SHX + DBF + PRJ + CPG)
#
# aep_source:
#   "column"    -- AEP scenario stored in a column (col name = aep_col)
#   "filename"  -- one shapefile per AEP scenario; parse from filename
#
# Note: only direct /download/<filename> URLs work without auth.
# Resource page URLs (no /download/) return HTML -- those studies are marked
# with a comment and will fail gracefully.
# ---------------------------------------------------------------------------
STUDIES = {
    "campbelltown": {
        "label": "Campbelltown Design Flood Extents",
        "lga_names": ["CAMPBELLTOWN", "CAMDEN"],
        "currency_date": date(2023, 9, 12),
        "instrument_prefix": "CTFS_2023",
        "download_type": "zip",
        # Direct download confirmed working (no auth required)
        "zip_url": "https://flooddata.ses.nsw.gov.au/dataset/7a412d28-4699-456c-b7d0-98b28f11ba29/resource/b5675efa-b0d0-4ac4-b8f2-173b1ef409a0/download/flood-extents.zip",
        # One shapefile per AEP: 0p2AEP_Extent.shp, 1AEP_Extent.shp, PMF_Extent.shp
        "aep_source": "filename",
        "aep_col": None,
    },
    "narellan": {
        "label": "Narellan Creek Flood Study Flood Extents (Camden)",
        "lga_names": ["CAMDEN", "CAMPBELLTOWN"],
        "currency_date": date(2023, 9, 1),
        "instrument_prefix": "NCFS_2023",
        "download_type": "zip",
        # Resource page URL -- requires portal login, will fail with HTML error
        "zip_url": "https://flooddata.ses.nsw.gov.au/dataset/14509edb-c3df-4099-8d09-af60d9930d81/resource/acd7362b-d57c-48d6-bb4e-da3b72578119",
        "aep_source": "filename",
        "aep_col": None,
    },
    "greendale": {
        "label": "Greendale Creek Flood Study GIS Layers (Northern Beaches)",
        "lga_names": ["NORTHERN BEACHES"],
        "currency_date": date(2023, 9, 1),
        "instrument_prefix": "GCFS_2023",
        "download_type": "zip",
        # Resource page URL -- requires portal login
        "zip_url": "https://flooddata.ses.nsw.gov.au/dataset/0756443e-b207-4120-9d8a-8a00cebe8820/resource/b66856ce-003a-4898-821b-892b40009a23",
        "aep_source": "filename",
        "aep_col": None,
    },
    "south_creek_hc": {
        "label": "Updated South Creek Flood Study Hydraulic Categories (Penrith)",
        "lga_names": ["PENRITH", "HAWKESBURY", "BLACKTOWN"],
        "currency_date": date(2023, 9, 12),
        "instrument_prefix": "SCFS_HC_2023",
        "download_type": "zip",
        # Resource page URL -- requires portal login
        "zip_url": "https://flooddata.ses.nsw.gov.au/dataset/b0576482-7d66-4788-b4fa-cf612cb996c8/resource/19a8343c-50d2-4cb5-978b-6131af0fff8e",
        "aep_source": "column",
        "aep_col": None,
    },
}

# AEP numeric (%) -> ARI (years) lookup for value_numeric field
AEP_TO_ARI = {
    "50": 2, "20": 5, "10": 10, "5": 20,
    "2": 50, "1": 100, "0.5": 200, "0.2": 500,
    "0.1": 1000,
}

# Column name patterns indicating AEP scenario (checked case-insensitively)
AEP_COL_PATTERNS = ["aep", "ari", "flood_cat", "scenario", "category", "class", "rp", "recurrence"]

_AEP_CLEAN = re.compile(r"(\d+(?:\.\d+)?)\s*%?\s*(?:AEP|aep)?", re.IGNORECASE)


def _normalise_aep(raw: str) -> tuple[str, Optional[float]]:
    """
    Normalise AEP raw value to (label, ari_years).

    Input forms:
      "PMF"        -> ("PMF", None)
      "100AEP"     -> ARI=100yr -> ("1.0%AEP", 100)   [Hawkesbury: ARI-based]
      "1AEP"       -> AEP%=1%  -> ("1%AEP", 100)       [Campbelltown: already AEP%]
      "0.2AEP"     -> ("0.2%AEP", 500)
      "1% AEP"     -> ("1%AEP", 100)

    Disambiguation: values >= 50 treated as ARI; values < 50 as AEP%.
    """
    raw = str(raw).strip()
    if "pmf" in raw.lower() or "probable" in raw.lower():
        return "PMF", None
    # Match XAEp or X.XAEP (normalised internal form from filename parsing)
    m = re.match(r"^(\d+(?:\.\d+)?)AEP$", raw, re.IGNORECASE)
    if m:
        val = float(m.group(1))
        if val >= 50:
            # ARI-based (Hawkesbury): ARI=val, pct=100/val
            ari = val
            pct = round(100.0 / ari, 4)
        else:
            # AEP%-based (Campbelltown): pct=val, ARI=100/val
            pct = val
            ari = round(100.0 / pct, 1) if pct > 0 else None
        return f"{pct}%AEP", ari
    # Handle "1% AEP", "1%AEP", "1 AEP" (column values)
    m = _AEP_CLEAN.match(raw)
    if m:
        pct = m.group(1)
        ari = AEP_TO_ARI.get(pct)
        return f"{pct}%AEP", float(ari) if ari else None
    return raw, None


def _detect_aep_col(gdf) -> Optional[str]:
    cols = [c for c in gdf.columns if c.lower() != "geometry"]
    for pat in AEP_COL_PATTERNS:
        for col in cols:
            if pat in col.lower():
                return col
    return None


def _download_file(url: str, dest: Path, label: str = "") -> None:
    if dest.exists():
        print(f"  [cache] {dest.name}")
        return
    print(f"  [dl] {label or dest.name} ...")
    r = requests.get(url, timeout=120, stream=True, allow_redirects=True)
    r.raise_for_status()
    content_type = r.headers.get("content-type", "")
    if "html" in content_type.lower():
        raise RuntimeError(
            f"Got HTML response (auth required?) for {url}\n"
            f"Content-Type: {content_type}"
        )
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)
    print(f"  [dl] done ({dest.stat().st_size // 1024} KiB)")


def _prepare_study(study_key: str, study: dict) -> list[Path]:
    study_dir = CACHE_DIR / study_key
    study_dir.mkdir(exist_ok=True)

    dl_type = study["download_type"]

    if dl_type == "shp_parts":
        stem = None
        for ext, url in study["shp_urls"].items():
            fname = url.split("/download/")[-1]
            if ext == ".shp":
                stem = fname[: -len(".shp")]
            dest = study_dir / fname
            _download_file(url, dest, label=fname)
        if not stem:
            raise RuntimeError("No .shp URL found in study config")
        return [study_dir / f"{stem}.shp"]

    elif dl_type == "zip":
        zip_url = study["zip_url"]
        zip_name = zip_url.split("/download/")[-1] if "/download/" in zip_url else f"{study_key}.zip"
        zip_path = study_dir / zip_name
        _download_file(zip_url, zip_path, label=zip_name)
        extract_dir = study_dir / "extracted"
        if not extract_dir.exists():
            print(f"  [extract] {zip_name} ...")
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(extract_dir)
        return sorted(extract_dir.rglob("*.shp"))

    else:
        raise NotImplementedError(f"Unknown download_type: {dl_type}")


def _ingest_study(study_key: str, study: dict, shp_paths: list[Path], conn, dry_run: bool) -> int:
    cur = conn.cursor()
    total = 0
    instrument_prefix = study["instrument_prefix"]
    lga_primary = study["lga_names"][0]
    currency_date = study["currency_date"]

    for shp_path in shp_paths:
        print(f"\n  [shp] {shp_path.name}")
        try:
            gdf = gpd.read_file(shp_path)
        except Exception as e:
            print(f"  [skip] cannot read: {e}")
            continue

        if len(gdf) == 0:
            print(f"  [skip] empty")
            continue

        print(f"  rows={len(gdf)}, CRS={gdf.crs}")
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")

        aep_col = study.get("aep_col") or _detect_aep_col(gdf)
        print(f"  columns={list(gdf.columns)}")

        aep_source = study.get("aep_source", "column")
        if aep_source == "filename":
            stem = shp_path.stem
            if re.search(r"PMF", stem, re.IGNORECASE):
                scenario_raw = "PMF"
            else:
                # Hawkesbury: DesignXXXAEP
                m = re.search(r"Design(\d+(?:p\d+)?AEP)", stem, re.IGNORECASE)
                if not m:
                    # Campbelltown: 0p2AEP, 1AEP, 20AEP
                    m = re.search(r"(\d+(?:p\d+)?)AEP", stem, re.IGNORECASE)
                if m:
                    raw = m.group(1).replace("p", ".")
                    scenario_raw = f"{raw}AEP"
                else:
                    scenario_raw = "UNKNOWN"
            unique_scenarios = [scenario_raw]
        elif aep_col and aep_col in gdf.columns:
            unique_scenarios = sorted(gdf[aep_col].dropna().unique().tolist())
            print(f"  aep_col={aep_col}, unique_values={unique_scenarios[:10]}")
        else:
            print(f"  [warn] no AEP column found -- ingesting as 'FLOOD_EXTENT'")
            aep_col = None
            unique_scenarios = ["FLOOD_EXTENT"]

        rows_to_insert = []
        for scenario_raw in unique_scenarios:
            subset = gdf[gdf[aep_col] == scenario_raw] if aep_col else gdf
            if len(subset) == 0:
                continue
            norm_label, ari = _normalise_aep(str(scenario_raw))
            instrument_key = f"{instrument_prefix}_{norm_label.replace('%', 'pct').replace('.', '_')}"

            for idx, row in subset.iterrows():
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue
                rows_to_insert.append((
                    instrument_key,
                    lga_primary,
                    "flood",
                    norm_label,
                    float(ari) if ari is not None else None,
                    currency_date,
                    int(idx) + 1,
                    geom.wkt,
                ))

        if not rows_to_insert:
            print(f"  [skip] no valid rows")
            continue

        print(f"  Prepared {len(rows_to_insert)} features")

        if dry_run:
            print(f"  [dry-run] would upsert {len(rows_to_insert)} features")
            total += len(rows_to_insert)
            continue

        execute_values(
            cur,
            """
            INSERT INTO spatial_overlays
                (instrument_key, lga_name, layer_type, value, value_numeric, currency_date, source_oid, geom, synced_at)
            VALUES %s
            ON CONFLICT (instrument_key, layer_type, source_oid) DO UPDATE
                SET value = EXCLUDED.value,
                    value_numeric = EXCLUDED.value_numeric,
                    currency_date = EXCLUDED.currency_date,
                    geom = EXCLUDED.geom,
                    synced_at = now()
            """,
            rows_to_insert,
            template="(%s, %s, %s, %s, %s, %s, %s, ST_Multi(ST_GeomFromText(%s, 4326)), now())",
        )
        conn.commit()
        print(f"  Upserted {len(rows_to_insert)} features")
        total += len(rows_to_insert)

    cur.close()
    return total


def _inspect_study(study_key: str, study: dict, shp_paths: list[Path]) -> None:
    print(f"\n{'=' * 60}")
    print(f"STUDY: {study_key} -- {study['label']}")
    for shp_path in shp_paths:
        print(f"\n  SHP: {shp_path.name}")
        try:
            gdf = gpd.read_file(shp_path)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
        print(f"  rows={len(gdf)}, CRS={gdf.crs}")
        print(f"  columns: {[c for c in gdf.columns if c != 'geometry']}")
        for col in gdf.columns:
            if col.lower() == "geometry":
                continue
            if any(pat in col.lower() for pat in AEP_COL_PATTERNS):
                unique_vals = gdf[col].dropna().unique().tolist()[:20]
                print(f"  >>> {col}: {unique_vals}")


def _verify_db(conn, study_key: str, instrument_prefix: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT value, COUNT(*) FROM spatial_overlays "
            "WHERE layer_type='flood' AND instrument_key LIKE %s "
            "GROUP BY value ORDER BY value",
            (f"{instrument_prefix}%",),
        )
        rows = cur.fetchall()
        print(f"\n[{study_key}] flood rows in DB:")
        for r in rows:
            print(f"  {r[0]}: {r[1]} polygons")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", default="all",
                        help="Study key: all | campbelltown | narellan | greendale | south_creek_hc")
    parser.add_argument("--inspect", action="store_true",
                        help="Print column info only -- no DB insert")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and validate but skip DB insert")
    args = parser.parse_args()

    target_keys = list(STUDIES.keys()) if args.study == "all" else [args.study]
    for k in target_keys:
        if k not in STUDIES:
            print(f"ERROR: unknown study '{k}'. Valid: {list(STUDIES.keys())}")
            sys.exit(1)

    database_url = os.getenv("DATABASE_URL")
    if not database_url and not args.inspect and not args.dry_run:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    for study_key in target_keys:
        study = STUDIES[study_key]
        print(f"\n{'=' * 60}")
        print(f"Processing: {study_key} -- {study['label']}")

        try:
            shp_paths = _prepare_study(study_key, study)
        except Exception as e:
            print(f"  ERROR preparing study: {e}")
            continue

        if not shp_paths:
            print(f"  ERROR: no shapefiles found after download")
            continue

        print(f"  Found {len(shp_paths)} shapefile(s)")

        if args.inspect:
            _inspect_study(study_key, study, shp_paths)
            continue

        conn = psycopg2.connect(database_url)
        try:
            total = _ingest_study(study_key, study, shp_paths, conn, dry_run=args.dry_run)
            if not args.dry_run:
                _verify_db(conn, study_key, study["instrument_prefix"])
            print(f"\n[{study_key}] Total features: {total}")
        except Exception as e:
            conn.rollback()
            print(f"  ERROR: {e}")
            raise
        finally:
            conn.close()

    print("\n[DONE]")


if __name__ == "__main__":
    main()
