"""Flood calibration: served screen vs Copernicus EMS observed 2022 extents.

Pass mark committed BEFORE this ran, in
docs/qa/flood-calibration-2022-precommit.md (commit fb0a44f7): recall >= 0.90.
"""
import glob, json, os, random, sys, time, zipfile
from pathlib import Path

import subprocess as _sp

# Resolved from this file, not hardcoded: a committed runner that only works on
# one laptop is not reproducible, and this one is cited as evidence.
WT = Path(__file__).resolve().parents[1]
ROOT = WT
sys.path.insert(0, str(WT))
sys.path.insert(0, str(WT / "services"))

# A git worktree carries no .env or data/ of its own; both sit with the main
# checkout. GIT_* is scrubbed because a hook exports GIT_DIR and it overrides
# cwd (DQ-54) — the wrong repo here would mean the wrong database.
_env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
_common = _sp.run(
    ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
    cwd=str(WT), capture_output=True, text=True, env=_env,
).stdout.strip()
if _common and (Path(_common).parent / "data").exists():
    ROOT = Path(_common).parent

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

CORP = ROOT / "data/flood_calibration/copernicus"
N = 50
SEED = 20220228  # the date the Northern Rivers flood peaked. Fixed, so the run repeats.

def polygons():
    """(aoi, activation, ring) for every observed flood polygon."""
    out = []
    for z in sorted(glob.glob(str(CORP / "*.zip"))):
        try: zf = zipfile.ZipFile(z)
        except Exception: continue
        # partition, not split()[n]: a file named without underscores would
        # IndexError and take the whole calibration down mid-run.
        parts = Path(z).name.split("_")
        act = parts[0] if parts else "?"
        aoi = parts[1] if len(parts) > 1 else "?"
        for n in zf.namelist():
            if not (n.endswith(".json") and "observedEvent" in n): continue
            try: g = json.loads(zf.read(n))
            except Exception: continue
            for f in g.get("features") or []:
                geom = f.get("geometry") or {}
                t, c = geom.get("type"), geom.get("coordinates")
                if not c: continue
                rings = [c[0]] if t == "Polygon" else [p[0] for p in c] if t == "MultiPolygon" else []
                for r in rings:
                    if r and len(r) >= 4: out.append((aoi, act, r))
    return out

def point_in_ring(x, y, ring):
    inside = False; j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]; xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside

def sample(polys, n, seed):
    rnd = random.Random(seed)
    by_aoi = {}
    for aoi, act, r in polys: by_aoi.setdefault((act, aoi), []).append(r)
    keys = sorted(by_aoi); picked = []
    # Stratified: walk the AOIs round-robin so no single activation dominates.
    while len(picked) < n and keys:
        for k in list(keys):
            if len(picked) >= n: break
            rings = by_aoi[k]
            for _ in range(200):
                ring = rnd.choice(rings)
                xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
                if max(xs) > 180 or min(xs) < 110:  # not lon/lat — skip projected products
                    break
                x = rnd.uniform(min(xs), max(xs)); y = rnd.uniform(min(ys), max(ys))
                if point_in_ring(x, y, ring):
                    picked.append((k[0], k[1], round(y, 6), round(x, 6))); break
    return picked[:n]

polys = polygons()
print(f"observed flood polygons loaded: {len(polys)}", flush=True)
pts = sample(polys, N, SEED)
print(f"sampled points: {len(pts)} across {len(set((a,b) for a,b,_,_ in pts))} activation/AOI pairs", flush=True)
if not pts:
    print("NO POINTS — cannot calibrate. UNKNOWABLE, not a pass."); raise SystemExit(2)

from flood_truth import run_flood, FloodRequest
import uuid

said_something = 0; results = []
t0 = time.time()
for i, (act, aoi, lat, lng) in enumerate(pts, 1):
    try:
        r = run_flood(FloodRequest(address=f"calibration {act}/{aoi}", lat=lat, lng=lng,
                                   report_id=str(uuid.uuid4())))
        o = (r or {}).get("outputs") or {}
        sig = o.get("flood_signal"); z = o.get("in_100yr_flood_zone"); ses = o.get("ses_in_flood_planning_area")
        hit = (sig not in (None, "none")) or (z is True) or (ses is True)
        said_something += 1 if hit else 0
        results.append({"act": act, "aoi": aoi, "lat": lat, "lng": lng,
                        "flood_signal": sig, "in_100yr": z, "ses": ses, "hit": hit})
        print(f"[{i}/{len(pts)}] {act}/{aoi} {lat:.4f},{lng:.4f} signal={sig} 1pct={z} ses={ses} -> {'HIT' if hit else 'MISS'}", flush=True)
    except Exception as e:
        msg = str(e)
        # ONLY an explicit outside-NSW refusal is out of scope. Any other
        # failure is an in-scope point the product did not answer for, and
        # dropping it from the denominator would inflate recall silently —
        # 10 database errors would read as 100% recall on the 40 that worked.
        out_of_scope = "outside NSW" in msg or "outside the NSW" in msg
        results.append({"act": act, "aoi": aoi, "lat": lat, "lng": lng,
                        "error": msg[:140],
                        "hit": None if out_of_scope else False,
                        "out_of_scope": out_of_scope})
        print(f"[{i}/{len(pts)}] {act}/{aoi} ERROR {str(e)[:100]}", flush=True)

scored = [r for r in results if r.get("hit") is not None]
if not scored:
    print("=" * 74)
    print("UNKNOWABLE: every point errored, so the product was never scored.")
    print("This is NOT a fail — a harness that could not run the check has")
    print("measured nothing. Fix the harness and re-run.")
    for r in results[:3]: print("   ", r.get("error"))
    raise SystemExit(2)
recall = said_something / len(scored)
import math
# WILSON, not Wald. At p near 1 the Wald interval is invalid and reports a
# lower bound well above the truth — here 0.929 against Wilson's 0.874, which
# is exactly the difference between claiming a pass and not having earned one.
_n, _z = len(scored), 1.96
_c = _z * _z / _n
_centre = (recall + _c / 2) / (1 + _c)
_half = _z * math.sqrt(recall * (1 - recall) / _n + _c / (4 * _n)) / (1 + _c)
lo, hi = max(0.0, _centre - _half), min(1.0, _centre + _half)
print("=" * 74, flush=True)
print(f"scored points        : {len(scored)} (of {len(pts)} sampled; {len(pts)-len(scored)} errored)", flush=True)
print(f"said something       : {said_something}", flush=True)
# The pre-commit says a result within the interval of the mark is reported as
# INDISTINGUISHABLE from it, not as a pass. Applying the stricter rule I wrote
# before seeing the number, rather than the flattering one available after.
verdict = ("PASS" if lo >= 0.90 else
           "INDISTINGUISHABLE FROM THE MARK" if hi >= 0.90 else "FAIL")
oos = sum(1 for r in results if r.get("out_of_scope"))
print(f"out of scope (refused, outside NSW): {oos}", flush=True)
print(f"RECALL               : {recall:.3f}  (Wilson 95% CI {lo:.3f} - {hi:.3f})", flush=True)
print(f"PASS MARK            : 0.90, committed before the run", flush=True)
print(f"VERDICT              : {verdict}", flush=True)
print("=" * 74, flush=True)
Path(WT / "docs/qa/flood-calibration-2022-result.json").write_text(
    json.dumps({"n_sampled": len(pts), "n_scored": len(scored), "hits": said_something,
                "recall": recall, "wilson_lo": lo, "wilson_hi": hi,
                "pass_mark": 0.90, "verdict": verdict, "out_of_scope": oos,
                "seed": SEED, "results": results}, indent=2), encoding="utf-8")
print("written: docs/qa/flood-calibration-2022-result.json", flush=True)
