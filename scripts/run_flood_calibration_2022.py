"""Flood calibration: served screen vs Copernicus EMS observed 2022 extents.

Pass mark committed BEFORE this ran, in
docs/qa/flood-calibration-2022-precommit.md (commit fb0a44f7): recall >= 0.90.
"""
import glob, hashlib, json, os, random, sys, time, zipfile
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
# 150 RAW DRAWS, per docs/qa/flood-calibration-2022-amendment-01.md (committed
# 2026-08-10, BEFORE the re-run). The original protocol at fb0a44f7 said 50, and
# this had drifted to 150 without the protocol following — a deviation that
# moved the published recall from 0.800 to 0.895, so it is amended on the record
# rather than absorbed.
#
# The underlying defect was a UNITS error: the protocol specified raw DRAWS
# while reasoning about SCORED points. 50 draws yield ~15 scored, an interval of
# 0.548-0.930 — from one-in-two to almost-always, which decides nothing.
#
# The pass mark (recall >= 0.90) has NOT moved and never will by this route.
N = 150

# The floor that actually matters, and the one the original protocol lacked.
# Below this the interval is too wide to separate a working product from a
# broken one, so the run reports UNKNOWABLE rather than a figure. A number from
# too few points is worse than no number: it looks like evidence.
MIN_SCORED = 30
SEED = 20220228  # the date the Northern Rivers flood peaked. Fixed, so the run repeats.

MANIFEST = WT / "docs/qa/flood-calibration-2022-reference-manifest.json"


def check_reference_complete():
    """Abort unless EVERY expected reference archive is present and unchanged.

    The integrity check below only inspects archives the glob actually found,
    so an archive that is entirely ABSENT was invisible: the glob simply
    returns fewer files, the run still yields enough points, and it publishes a
    valid-looking recall from an incomplete reference set.

    That is not hypothetical here. All four misses in the published run came
    from a single AOI, so losing one archive would remove them and RAISE the
    score. A reference set that can quietly shrink is not a reference.
    """
    if not MANIFEST.exists():
        print(f"REFERENCE MANIFEST MISSING: {MANIFEST}", flush=True)
        print("Cannot establish the reference set is complete. Refusing to run.", flush=True)
        raise SystemExit(2)
    expected = json.loads(MANIFEST.read_text(encoding="utf-8"))["archives"]
    present = {Path(z).name for z in glob.glob(str(CORP / "*.zip"))}
    missing = sorted(set(expected) - present)
    extra = sorted(present - set(expected))
    changed = []
    for name, want in expected.items():
        f = CORP / name
        if not f.exists():
            continue
        got = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
        if got != want:
            changed.append(f"{name} ({want} -> {got})")
    if missing or changed:
        print("REFERENCE SET INCOMPLETE OR ALTERED — calibration aborted:", flush=True)
        for m in missing[:10]: print(f"   MISSING: {m}", flush=True)
        for c in changed[:10]: print(f"   CHANGED: {c}", flush=True)
        print("A recall figure from a shrunken reference set can only flatter.", flush=True)
        raise SystemExit(2)
    if extra:
        # Reported, and NOT relied on. An earlier version called this safe on
        # the reasoning that widening the reference cannot flatter — wrong: an
        # extra archive full of easily-detected locations raises recall under
        # the same seed. polygons() now reads only the manifest, so these files
        # are ignored entirely; the note exists so the manifest gets updated
        # deliberately rather than the set drifting.
        print(f"note: {len(extra)} archive(s) on disk are NOT in the manifest "
              f"(e.g. {extra[0]}) and are being IGNORED. Add them to the "
              f"manifest if they belong in the reference set.", flush=True)
    print(f"reference set complete: {len(expected)} archives verified", flush=True)


def polygons():
    """(aoi, activation, ring) for every observed flood polygon."""
    out = []
    bad = []
    # Iterate the MANIFEST, not the glob. An earlier version globbed and merely
    # NOTED unmanifested archives, on the reasoning that "widening the reference
    # cannot flatter". That reasoning was wrong: an extra archive full of
    # easily-detected locations raises recall under the same seed and the same
    # manifest. The reference set is fixed, so read exactly the fixed list.
    _expected = json.loads(MANIFEST.read_text(encoding="utf-8"))["archives"]
    for z in [str(CORP / name) for name in sorted(_expected)]:
        try: zf = zipfile.ZipFile(z)
        except Exception as e:
            bad.append((Path(z).name, f"zip: {e}")); continue
        # partition, not split()[n]: a file named without underscores would
        # IndexError and take the whole calibration down mid-run.
        parts = Path(z).name.split("_")
        act = parts[0] if parts else "?"
        aoi = parts[1] if len(parts) > 1 else "?"
        for n in zf.namelist():
            if not (n.endswith(".json") and "observedEvent" in n): continue
            try: g = json.loads(zf.read(n))
            except Exception as e:
                bad.append((n, f"json: {e}")); continue
            for f in g.get("features") or []:
                geom = f.get("geometry") or {}
                t, c = geom.get("type"), geom.get("coordinates")
                if not c: continue
                # (exterior, holes). Only c[0] was taken before, discarding
                # interior rings — so a dry island inside an inundation polygon
                # was sampled as observed flooding, and the product correctly
                # answering "no flood" there was recorded as a MISS. That
                # direction understates the product rather than flattering it,
                # which is why it survived review, but it is still a wrong
                # reference.
                if t == "Polygon":
                    shapes = [(c[0], list(c[1:]))]
                elif t == "MultiPolygon":
                    shapes = [(poly[0], list(poly[1:])) for poly in c]
                else:
                    shapes = []
                for r, holes in shapes:
                    if not (r and len(r) >= 4): continue
                    # Cheap pre-filter to the NSW side. EMSR567 mapped the
                    # south-east Queensland floods too, and without this the
                    # stratified walk spends most of its draws there — the
                    # first corrected run got 7 NSW points out of 50, an
                    # interval of 0.49-0.97, which says nothing. The
                    # authoritative test is still lookup_lga below; this only
                    # stops the sample being wasted.
                    lats = [q[1] for q in r if len(q) > 1]
                    if not lats or (sum(lats) / len(lats)) > -28.1: continue
                    out.append((aoi, act, r, holes))
    if bad:
        # A reference archive that will not open is a hole in the AUTHORITY, and
        # an AOI silently missing from the sample can only flatter the result.
        print("REFERENCE DATA UNREADABLE — calibration aborted:", flush=True)
        for name, err in bad[:10]: print(f"   {name}: {err}", flush=True)
        raise SystemExit(2)
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
    for aoi, act, r, holes in polys: by_aoi.setdefault((act, aoi), []).append((r, holes))
    keys = sorted(by_aoi); picked = []
    # Stratified: walk the AOIs round-robin so no single activation dominates.
    # `keys` MUST shrink. Previously an AOI that can never yield a lon/lat point
    # (a projected product, say) stayed in the list forever, so if no AOI could
    # produce one the outer while looped indefinitely making no progress — a
    # calibration that hangs rather than reports.
    while len(picked) < n and keys:
        progressed = False
        for k in list(keys):
            if len(picked) >= n: break
            rings = by_aoi[k]
            got_one = False
            for _ in range(200):
                ring, holes = rnd.choice(rings)
                xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
                if max(xs) > 180 or min(xs) < 110:  # not lon/lat — skip projected products
                    break
                x = rnd.uniform(min(xs), max(xs)); y = rnd.uniform(min(ys), max(ys))
                # Inside the exterior AND outside every hole. A point in a dry
                # island is not observed flooding.
                if point_in_ring(x, y, ring) and not any(
                    point_in_ring(x, y, h) for h in holes if h and len(h) >= 4
                ):
                    picked.append((k[0], k[1], round(y, 6), round(x, 6)))
                    got_one = True; progressed = True; break
            if not got_one:
                keys.remove(k)   # exhausted — never ask it again
        if not progressed:
            break                # nothing left can yield a point
    return picked[:n]

check_reference_complete()
polys = polygons()
print(f"observed flood polygons loaded: {len(polys)}", flush=True)
pts = sample(polys, N, SEED)
print(f"sampled points: {len(pts)} across {len(set((a,b) for a,b,_,_ in pts))} activation/AOI pairs", flush=True)
if not pts:
    print("NO POINTS — cannot calibrate. UNKNOWABLE, not a pass."); raise SystemExit(2)

from flood_truth import run_flood, FloodRequest, _get_conn
from lga_lookup import lookup_lga
import uuid

def in_nsw(lat, lng, _cache={}):
    """Authoritative-for-this-product scope test: does NSW LGA coverage
    contain the point? The pipeline's latitude envelope is coarse and admits
    south-east Queensland — EMSR567 mapped both states, and scoring a Brisbane
    point as NSW recall is measuring the wrong thing."""
    key = (round(lat, 4), round(lng, 4))
    if key in _cache: return _cache[key]
    conn = None
    try:
        conn = _get_conn()
        got = bool((lookup_lga(lat, lng, conn) or {}).get("lga_name"))
    except Exception:
        got = None          # unknown scope, not "in scope"
    finally:
        if conn: conn.close()
    _cache[key] = got
    return got

# Three states, recorded separately. The artifact previously wrote only the
# POST-scope count as n_sampled and out_of_scope: 0, so a run that drew 150 and
# kept 38 published "38 of 38, no exclusions" — the attrition, and any
# lookup failures inside it, were invisible. That is the absence-as-answer
# pattern committed inside the instrument built to measure it.
n_raw_draws = len(pts)
scoped, n_out_of_scope, n_scope_unknown = [], 0, 0
for act, aoi, lat, lng in pts:
    ok = in_nsw(lat, lng)
    if ok is True:
        scoped.append((act, aoi, lat, lng))
    elif ok is False:
        n_out_of_scope += 1      # resolved, and genuinely outside coverage
    else:
        n_scope_unknown += 1     # lookup FAILED — not the same thing
print(f"raw draws: {n_raw_draws} -> in NSW LGA coverage {len(scoped)}, "
      f"outside {n_out_of_scope}, scope unresolved {n_scope_unknown}", flush=True)
if n_scope_unknown:
    # An unresolved lookup is a hole in the scope test, not a clean exclusion.
    print(f"  ! {n_scope_unknown} draws could not be resolved to an LGA — "
          f"excluded, but they are unknown scope, not known-outside.", flush=True)
pts = scoped

said_something = 0; results = []
t0 = time.time()
for i, (act, aoi, lat, lng) in enumerate(pts, 1):
    try:
        r = run_flood(FloodRequest(address=f"calibration {act}/{aoi}", lat=lat, lng=lng,
                                   report_id=str(uuid.uuid4())))
        o = (r or {}).get("outputs") or {}
        sig = o.get("flood_signal"); z = o.get("in_100yr_flood_zone"); ses = o.get("ses_in_flood_planning_area")
        # ALLOWLIST. `unavailable` means the sources could not be consulted —
        # the product supplied no flood indicator, so it is not a hit. Counting
        # it as one is exactly the absence-as-answer error being hunted.
        hit = (sig in ("low", "moderate", "elevated")) or (z is True) or (ses is True)
        said_something += 1 if hit else 0
        results.append({"act": act, "aoi": aoi, "lat": lat, "lng": lng,
                        "flood_signal": sig, "in_100yr": z, "ses": ses, "hit": hit})
        print(f"[{i}/{len(pts)}] {act}/{aoi} {lat:.4f},{lng:.4f} signal={sig} 1pct={z} ses={ses} -> {'HIT' if hit else 'MISS'}", flush=True)
    except Exception as e:
        msg = str(e)
        # EVERY exception here is a failure to answer, scored as a miss.
        #
        # This used to treat an "outside NSW" message as out-of-scope and drop
        # the point from the denominator. But in_nsw() has ALREADY ruled this
        # point inside coverage, using the authoritative lookup — so run_flood
        # saying otherwise is two components CONTRADICTING each other, not new
        # information about scope. Silently believing the second one removed
        # in-scope points from the denominator and inflated recall.
        #
        # Scope is decided once, before scoring, by the authoritative test.
        # Nothing after that point may re-decide it from an exception string.
        contradiction = "outside NSW" in msg or "outside the NSW" in msg
        if contradiction:
            print(f"   ! SCOPE CONTRADICTION at {lat:.4f},{lng:.4f}: lookup_lga "
                  f"placed this point IN coverage but run_flood refused it as "
                  f"outside. Scored as a miss, not excluded.", flush=True)
        results.append({"act": act, "aoi": aoi, "lat": lat, "lng": lng,
                        "error": msg[:140],
                        "hit": False,
                        "scope_contradiction": contradiction})
        print(f"[{i}/{len(pts)}] {act}/{aoi} ERROR {str(e)[:100]}", flush=True)

scored = [r for r in results if r.get("hit") is not None]
if not scored:
    print("=" * 74)
    print("UNKNOWABLE: every point errored, so the product was never scored.")
    print("This is NOT a fail — a harness that could not run the check has")
    print("measured nothing. Fix the harness and re-run.")
    for r in results[:3]: print("   ", r.get("error"))
    raise SystemExit(2)
# The floor from amendment-01, ENFORCED rather than merely declared. Stated in
# scored points, which is the unit that governs the interval — the original
# protocol specified raw draws and that units slip is what produced a 15-point
# run whose interval (0.548-0.930) could not separate a working product from a
# broken one. Reported BEFORE the recall figure is computed, so an undersized
# run cannot print a number that gets quoted.
if len(scored) < MIN_SCORED:
    print("=" * 74)
    print(f"UNKNOWABLE: {len(scored)} scored points, {MIN_SCORED} required "
          f"(docs/qa/flood-calibration-2022-amendment-01.md).")
    print("Not a pass and not a fail. At this sample size the confidence")
    print("interval is too wide to distinguish a working product from a")
    print("broken one, so no recall figure is published.")
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
# Nothing is out-of-scope at scoring time any more: scope is settled BEFORE
# the loop by the authoritative test, and every exception after it is a miss.
# What is worth counting is how often the two components disagreed.
contradictions = sum(1 for r in results if r.get("scope_contradiction"))
oos = 0
print(f"scope contradictions (lookup said in, run_flood said out): {contradictions}", flush=True)
print(f"RECALL               : {recall:.3f}  (Wilson 95% CI {lo:.3f} - {hi:.3f})", flush=True)
print(f"PASS MARK            : 0.90, committed before the run", flush=True)
print(f"VERDICT              : {verdict}", flush=True)
print("=" * 74, flush=True)
Path(WT / "docs/qa/flood-calibration-2022-result.json").write_text(
    json.dumps({"n_raw_draws": n_raw_draws, "n_in_scope": len(pts),
                "n_out_of_scope_at_scope_test": n_out_of_scope,
                "n_scope_unresolved": n_scope_unknown,
                "n_sampled": len(pts), "n_scored": len(scored), "hits": said_something,
                "recall": recall, "wilson_lo": lo, "wilson_hi": hi,
                "pass_mark": 0.90, "verdict": verdict, "out_of_scope_at_scoring": oos,
                "scope_contradictions": contradictions,
                "seed": SEED, "results": results}, indent=2), encoding="utf-8")
print("written: docs/qa/flood-calibration-2022-result.json", flush=True)
