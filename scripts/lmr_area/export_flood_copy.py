# prior-art-checked: four sweeps 2026-11-22. (1) DB: spatial_overlays holds the 2024 Hawkesbury-Nepean River Flood Study extents (instrument_key HNRFS_2024_PMF / _500AEP / _100AEP,
# loaded earlier by a retired ingest script); this READS them, writes nothing to the database. (2) Frontend: no reader. (3) Python: scripts/lmr_area/download_map_layers.py saves
# live state map layers to data/law/maps but cannot save these (they are not on a state map service); services/lmr_map_copy.py reads that folder. (4) Plans:
# ~/.claude/plans/ce-evidence-flood-pmf-and-pipeline-SCOPE-2026-11-22.md (owner approved 2026-11-22).
"""Save our copy of the 2024 Hawkesbury-Nepean River Flood Study flood areas as committed map files, so the area check can say how far a lot is from the flood.

    python scripts/lmr_area/export_flood_copy.py            # dry run: counts, sizes, a few checks; writes nothing
    python scripts/lmr_area/export_flood_copy.py --apply    # writes data/law/maps/hn_pmf.geojson.gz, hn_500aep.geojson.gz and hn_100aep.geojson.gz and adds the three layers to manifest.json

After every --apply, run the two checks that prove the new copy (this is the refresh procedure; the area check must not be trusted on a copy that has not passed them):
    python scripts/lmr_area/check_flood_copy.py 600          # the copy against the full-detail database rows: 0 lots inside the source but clear in the copy
    python scripts/lmr_area/compare_flood_rule.py 70         # the flood rule before and after on random points: 0 lots moved to clear while inside or near a flood area

Read-only on the database (a read-only session, 25 s per query, batches of 100 polygons). Each polygon is simplified to a tolerance in degrees (about 10 m for the Probable Maximum
Flood, about 30 m for the two flood-frequency layers, which are context only) so the files stay under the 2 MB repo limit; the manifest records that tolerance and the services
module keeps a 100 m margin well above it. The other layers in the manifest are left exactly as they are, and each flood layer carries its OWN read_on date and age limit: it is a dated
study (May 2024), not a legal map that changes monthly.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Optional

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "data" / "law" / "maps"
REPO_FILE_LIMIT = 2 * 1024 * 1024
BATCH = 100
STATEMENT_TIMEOUT_MS = 25000
MAX_AGE_DAYS = 400   # noqa: regulatory-number -- age limit for a dated study copy (re-export when the study is reissued), not a planning figure
STUDY = "Hawkesbury-Nepean River Flood Study, May 2024 (NSW Reconstruction Authority), flood-extents.zip at data.nsw.gov.au/data/dataset/2024-hawkesbury-nepean-river-flood-study"
# manifest name -> (instrument_key, simplify tolerance in degrees, what it is)
LAYERS = {
    "hn_pmf": ("HNRFS_2024_PMF", 0.0001, "Probable Maximum Flood extent (s164(1)(f))"),
    "hn_500aep": ("HNRFS_2024_500AEP", 0.0003, "1-in-500 year flood extent (context)"),
    "hn_100aep": ("HNRFS_2024_100AEP", 0.0003, "1-in-100 year flood extent (context)"),
}


def database_url() -> Optional[str]:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    for d in [REPO, *REPO.parents]:
        f = d / ".env"
        if f.is_file():
            for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.strip().startswith("DATABASE_URL"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def round_coords(x: Any) -> Any:
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return round(float(x), 6)
    return [round_coords(v) for v in x] if isinstance(x, list) else x


def read_layer(cur: Any, key: str, tol: float) -> Optional[list[dict]]:
    """Every polygon of one instrument key, simplified. None if the count read back differs from the count in the table (a partial copy is never saved)."""
    cur.execute("SELECT source_oid FROM spatial_overlays WHERE instrument_key = %s ORDER BY source_oid", (key,))
    ids = [r[0] for r in cur.fetchall()]
    feats: list[dict] = []
    for i in range(0, len(ids), BATCH):
        part = ids[i:i + BATCH]
        cur.execute("SELECT source_oid, value, ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, %s), 6) FROM spatial_overlays "
                    "WHERE instrument_key = %s AND source_oid = ANY(%s) ORDER BY source_oid", (tol, key, part))
        for oid, value, gj in cur.fetchall():
            g = json.loads(gj) if gj else None
            if not g or not g.get("coordinates"):
                print(f"    FAILED: polygon {oid} has no geometry after simplifying")
                return None
            g["coordinates"] = round_coords(g["coordinates"])
            feats.append({"type": "Feature", "properties": {"scenario": value, "source_oid": oid}, "geometry": g})
        print(f"    {len(feats)}/{len(ids)}", flush=True)
    return feats if len(feats) == len(ids) and ids else None


def pack(name: str, feats: list[dict]) -> Optional[tuple[list[str], list[bytes], list[int]]]:
    n_parts = 1
    while True:   # split into equal parts until every part is under the repo limit
        size = -(-len(feats) // n_parts)
        chunks = [feats[k:k + size] for k in range(0, len(feats), size)]
        gzs = [gzip.compress(json.dumps({"type": "FeatureCollection", "features": c}, separators=(",", ":"), ensure_ascii=False).encode("utf-8"), 9, mtime=0) for c in chunks]
        if all(len(g) < REPO_FILE_LIMIT for g in gzs) or n_parts >= 8 or len(feats) <= n_parts:
            break
        n_parts += 1
    if any(len(g) >= REPO_FILE_LIMIT for g in gzs):
        return None
    names = [f"{name}.geojson.gz"] if len(gzs) == 1 else [f"{name}.part{k + 1}of{len(gzs)}.geojson.gz" for k in range(len(gzs))]
    return names, gzs, [len(c) for c in chunks]


def main(argv: list[str]) -> int:
    apply = "--apply" in argv
    url = database_url()
    if not url:
        print("no DATABASE_URL (environment or a .env above this folder)")
        return 2
    import psycopg2

    conn = psycopg2.connect(url, connect_timeout=15)
    conn.set_session(readonly=True, autocommit=True)   # a read-only session: nothing here can write to the database
    cur = conn.cursor()
    cur.execute(f"SET statement_timeout = {STATEMENT_TIMEOUT_MS}")
    today = date.today().isoformat()
    new_layers: dict[str, Any] = {}
    pending: list[tuple[str, bytes]] = []
    failed: list[str] = []
    for name, (key, tol, use) in LAYERS.items():
        print(f"{name}: {use} ({key}, tolerance {tol} deg)", flush=True)
        feats = read_layer(cur, key, tol)
        packed = pack(name, feats) if feats else None
        if not feats or packed is None:
            print("  FAILED: not saved")
            failed.append(name)
            continue
        names, gzs, counts = packed
        pts = sum(len(json.dumps(f["geometry"]["coordinates"])) for f in feats)
        print(f"  {len(feats)} polygons, {sum(len(g) for g in gzs):,} bytes gzipped in {len(gzs)} file(s); coordinate text {pts:,} chars")
        new_layers[name] = {"source": f"spatial_overlays instrument_key {key}, ingested from: {STUDY}", "use": use, "features": len(feats), "read_on": today,
                            "max_age_days": MAX_AGE_DAYS, "simplified_to_deg": tol, "study_date": "2024-05",
                            "files": [{"file": nm, "features": c, "bytes": len(g), "sha256": hashlib.sha256(g).hexdigest()} for nm, c, g in zip(names, counts, gzs)]}
        pending += list(zip(names, gzs))
    conn.close()
    if failed:
        print(f"NOT COMPLETE: {failed}; nothing written")
        return 1
    if apply:
        mf = OUT_DIR / "manifest.json"
        manifest = json.loads(mf.read_text(encoding="utf-8"))
        manifest["layers"] = {**manifest.get("layers", {}), **new_layers}   # every other layer and the file-wide read_on stay exactly as they were
        for nm, g in pending:
            (OUT_DIR / nm).write_bytes(g)
        mf.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {len(pending)} file(s) and updated manifest.json with {list(new_layers)}")
        print("NEXT: python scripts/lmr_area/check_flood_copy.py 600   then   python scripts/lmr_area/compare_flood_rule.py 70   (both must exit 0 before this copy is committed)")
    else:
        print("DRY RUN: nothing written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
