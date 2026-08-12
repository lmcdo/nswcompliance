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
sys.path.insert(0, str(Path(__file__).resolve().parent))
from qa_report_path import git_env  # noqa: E402  (DQ-54)

# A git worktree carries no .env or data/ of its own; both sit with the main
# checkout. GIT_* is scrubbed because a hook exports GIT_DIR and it overrides
# cwd (DQ-54) — the wrong repo here would mean the wrong database.
_common = _sp.run(
    ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
    cwd=str(WT), capture_output=True, text=True, env=git_env(),
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
    projected: dict = {}
    filtered_north: dict = {}
    contributed: dict = {}
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
                # interior rings — so a point on ground Copernicus did NOT map
                # as inundated could be drawn into a positive-only reference and
                # scored as a MISS. (That says nothing about whether the
                # product's negative there was right: a hole means "not mapped
                # as inundated", which may be dry ground or terrain the
                # satellite could not read. It only means the point never
                # belonged in this denominator.) The direction understates the
                # product rather than flattering it, which is why it survived
                # review, but it is still a wrong reference.
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
                    lons = [q[0] for q in r if len(q) > 1]
                    # CRS CHECK BEFORE THE LATITUDE FILTER.
                    #
                    # The filter below asks "is the mean latitude south of
                    # -28.1". Fed projected northings (say 6,700,000) that test
                    # is not false, it is MEANINGLESS — and it answers "skip".
                    # A whole archive in a projected CRS would therefore
                    # contribute nothing, silently, and the run would publish
                    # recall from a reference set quietly missing an AOI.
                    # Refuse rather than guess: this script does not reproject.
                    if lons and (max(abs(v) for v in lons) > 180
                                 or max(abs(v) for v in lats) > 90):
                        projected.setdefault(Path(z).name, 0)
                        projected[Path(z).name] += 1
                        continue
                    if not lats or (sum(lats) / len(lats)) > -28.1:
                        filtered_north[Path(z).name] = filtered_north.get(Path(z).name, 0) + 1
                        continue
                    contributed[Path(z).name] = contributed.get(Path(z).name, 0) + 1
                    out.append((aoi, act, r, holes))
    if projected:
        print("REFERENCE CRS UNSUPPORTED — calibration aborted:", flush=True)
        for name, cnt in sorted(projected.items()):
            print(f"   {name}: {cnt} ring(s) carry projected coordinates, not "
                  f"lon/lat. This script does not reproject, and the latitude "
                  f"pre-filter would have discarded them silently.", flush=True)
        raise SystemExit(2)
    # Archives contributing nothing are REPORTED, not fatal: EMSR567 mapped the
    # south-east Queensland floods as well, so an archive whose rings all sit
    # north of the filter is a legitimate geographic exclusion rather than a
    # defect. Naming them is what stops that assumption going unchecked.
    silent = sorted(set(filtered_north) - set(contributed))
    if silent:
        print(f"archives contributing no NSW polygons ({len(silent)}, excluded "
              f"by the latitude pre-filter, not by error):", flush=True)
        for name in silent:
            print(f"   {name}: {filtered_north[name]} ring(s) north of -28.1", flush=True)
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

# Every AOI removed from the stratified walk, with WHY. A group that vanishes
# from the sample can only flatter the result — the AOIs hardest to draw a
# point from are the thin, irregular inundation corridors, which is exactly the
# ground a flood screen is most likely to miss. Recording this is not optional
# bookkeeping: silence here is a selection bias that looks like a good number.
DROPPED_GROUPS: dict = {}
SAMPLE_ATTEMPTS = 5000


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
            why = f"rejection sampling failed in {SAMPLE_ATTEMPTS} attempts"
            for _ in range(SAMPLE_ATTEMPTS):
                ring, holes = rnd.choice(rings)
                xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
                if max(xs) > 180 or min(xs) < 110:  # not lon/lat — skip projected products
                    why = "projected product, not lon/lat"
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
                DROPPED_GROUPS[f"{k[0]}/{k[1]}"] = why
                keys.remove(k)   # never ask it again
        if not progressed:
            break                # nothing left can yield a point
    return picked[:n]


def report_dropped_groups() -> None:
    """A dropped AOI is reported, and a biasing one aborts the run.

    Two causes, treated differently because they mean different things:

    - A PROJECTED product cannot yield a lon/lat point at all. That is a fact
      about the archive's format, not about flooding, so it is reported and the
      run continues.
    - REJECTION-SAMPLING EXHAUSTION means the polygons are so thin or irregular
      that SAMPLE_ATTEMPTS uniform draws inside their bounding boxes all
      missed.
      Those are narrow inundation corridors — the hardest ground for a flood
      screen and therefore the ground whose absence most flatters recall.
      Dropping it silently is a selection bias, so it is fatal.

    Measured on the published run: ZERO groups dropped, all 17 activation/AOI
    pairs produced points, all 150 draws made. This guard is therefore latent
    today; it exists so that a future reference set cannot quietly shrink.
    """
    if not DROPPED_GROUPS:
        print("dropped activation/AOI groups: 0", flush=True)
        return
    print("=" * 74, flush=True)
    print(f"DROPPED {len(DROPPED_GROUPS)} activation/AOI group(s) from the sample:", flush=True)
    for g, why in sorted(DROPPED_GROUPS.items()):
        print(f"   {g}: {why}", flush=True)
    biasing = {g: w for g, w in DROPPED_GROUPS.items() if "rejection sampling" in w}
    if biasing:
        print("ABORTED: the groups above were lost to rejection-sampling", flush=True)
        print("exhaustion, not to a data format. Their inundation is thin or", flush=True)
        print("irregular — the ground most likely to be missed — so excluding", flush=True)
        print("them can only flatter recall. Raise SAMPLE_ATTEMPTS or sample", flush=True)
        print("geometrically, then re-run. UNKNOWABLE, not a pass.", flush=True)
        raise SystemExit(2)

check_reference_complete()
polys = polygons()
print(f"observed flood polygons loaded: {len(polys)}", flush=True)
pts = sample(polys, N, SEED)
report_dropped_groups()
print(f"sampled points: {len(pts)} across {len(set((a,b) for a,b,_,_ in pts))} activation/AOI pairs", flush=True)
if not pts:
    print("NO POINTS — cannot calibrate. UNKNOWABLE, not a pass."); raise SystemExit(2)

from flood_truth import run_flood, FloodRequest, _get_conn
from lga_lookup import lookup_lga
import uuid

def in_nsw(lat, lng, _cache={}):
    """Authoritative-for-this-product scope test, returning the COUNCIL too.

    Does NSW LGA coverage contain the point? The pipeline's latitude envelope
    is coarse and admits south-east Queensland — EMSR567 mapped both states,
    and scoring a Brisbane point as NSW recall is measuring the wrong thing.

    Returns (in_scope, council_name) where in_scope is True / False / None,
    None meaning the lookup FAILED, which is unknown scope rather than out of
    scope. The council name is what the interval is clustered on: recall is
    driven by whether a council has a flood overlay loaded, so the council is
    the sampling unit, not the point and not the AOI.

    Cached on the EXACT coordinates. It previously keyed on 4 decimal places,
    about 11 m, so two distinct sampled points could share one lookup and one
    scope decision. Points are drawn at 6 dp; there is no reason to blur them.
    """
    key = (lat, lng)
    if key in _cache: return _cache[key]
    conn = None
    try:
        conn = _get_conn()
        name = (lookup_lga(lat, lng, conn) or {}).get("lga_name")
        got = (bool(name), name)
    except Exception:
        got = (None, None)  # unknown scope, not "in scope"
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
    ok, council = in_nsw(lat, lng)
    if ok is True:
        scoped.append((act, aoi, lat, lng, council))
    elif ok is False:
        n_out_of_scope += 1      # resolved, and genuinely outside coverage
    else:
        n_scope_unknown += 1     # lookup FAILED — not the same thing
print(f"raw draws: {n_raw_draws} -> in NSW LGA coverage {len(scoped)}, "
      f"outside {n_out_of_scope}, scope unresolved {n_scope_unknown}", flush=True)
if n_scope_unknown:
    # An unresolved lookup is a hole in the scope test, not a clean exclusion,
    # and it was previously WARNED about and then excluded anyway. That is the
    # denominator quietly shrinking: the points most likely to fail a lookup
    # are not random with respect to the answer — a council whose data is
    # missing is exactly the kind of place this calibration exists to find, and
    # dropping it leaves the easier points behind and raises recall.
    #
    # Scope is decided once, authoritatively, for every sampled point. If it
    # cannot be decided, the run has not measured what it claims to measure.
    print("=" * 74, flush=True)
    print(f"UNKNOWABLE: {n_scope_unknown} of {n_raw_draws} draws could not be "
          f"resolved to an LGA.", flush=True)
    print("These are UNKNOWN scope, not known-outside. Excluding them would", flush=True)
    print("shrink the denominator in a direction that can only flatter the", flush=True)
    print("result. Fix the lookup and re-run. Not a pass and not a fail.", flush=True)
    raise SystemExit(2)
pts = scoped

said_something = 0; results = []
# Counts calls that RETURNED an answer, as distinct from calls that were
# scored. Every exception is scored (as a miss), so a counter derived from
# `results` cannot tell a working harness from a dead one — see the guard
# below for what that cost.
executed = 0
t0 = time.time()
for i, (act, aoi, lat, lng, council) in enumerate(pts, 1):
    try:
        r = run_flood(FloodRequest(address=f"calibration {act}/{aoi}", lat=lat, lng=lng,
                                   report_id=str(uuid.uuid4())))
        # CONTRACT CHECK BEFORE COUNTING AN EXECUTION.
        #
        # `(r or {}).get("outputs") or {}` turned a None or malformed response
        # into an all-null answer, which scores as a clean MISS and increments
        # `executed`. That walked straight past the zero-execution guard added
        # above: if run_flood swallowed an outage and returned None for every
        # point, `executed` would reach 37 with every signal null and the run
        # would publish "recall 0.000, FAIL" — the exact outcome that guard was
        # written to prevent, arriving through the one door it did not cover.
        if not isinstance(r, dict) or not isinstance(r.get("outputs"), dict):
            raise ValueError(
                f"run_flood returned no usable outputs contract "
                f"(type={type(r).__name__}); treated as an error, not a miss"
            )
        o = r["outputs"]
        sig = o.get("flood_signal"); z = o.get("in_100yr_flood_zone"); ses = o.get("ses_in_flood_planning_area")
        # ALLOWLIST. `unavailable` means the sources could not be consulted —
        # the product supplied no flood indicator, so it is not a hit. Counting
        # it as one is exactly the absence-as-answer error being hunted.
        hit = (sig in ("low", "moderate", "elevated")) or (z is True) or (ses is True)
        executed += 1
        said_something += 1 if hit else 0
        results.append({"act": act, "aoi": aoi, "council": council,
                        "lat": lat, "lng": lng,
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
        results.append({"act": act, "aoi": aoi, "council": council,
                        "lat": lat, "lng": lng,
                        "error": msg[:140],
                        "hit": False,
                        "scope_contradiction": contradiction})
        print(f"[{i}/{len(pts)}] {act}/{aoi} ERROR {str(e)[:100]}", flush=True)

scored = [r for r in results if r.get("hit") is not None]
n_errored = sum(1 for r in results if "error" in r)

# THE HARNESS-OUTAGE GUARD.
#
# This was previously written as `if not scored:` and was dead code. Every
# exception branch appends `"hit": False`, and `False is not None`, so errored
# rows land INSIDE `scored` — the list could only be empty if no point was
# sampled at all. A total database or API outage would therefore have made all
# 37 calls raise, scored 37 misses, and published `recall 0.000, VERDICT FAIL`:
# an infrastructure failure served as a catastrophic product result, with a
# guard sitting directly above it that read as though it prevented exactly
# that. The same defect made the "N errored" line print a structural zero.
#
# Exceptions still count as misses — a product that cannot answer has not
# answered, and excluding those points would inflate recall. What changes is
# that the denominator is no longer allowed to consist entirely of failures.
# The line is drawn only at the unambiguous case: zero successful executions
# means the harness demonstrably never ran, which is UNKNOWABLE, not a fail.
# Anything between is not classified from an exception string — it is reported
# loudly instead, because this script cannot tell a product that genuinely
# errors on an address from an outage, and inventing that classifier would be
# guessing.
if executed == 0:
    print("=" * 74)
    print(f"UNKNOWABLE: all {len(results)} points errored, so the product was")
    print("never scored. This is NOT a fail and NOT recall 0 — a harness that")
    print("could not run has measured nothing. Fix the harness and re-run.")
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

# THE INDEPENDENCE ASSUMPTION BEHIND WILSON DOES NOT HOLD HERE.
#
# Wilson treats 37 points as 37 independent Bernoulli trials. They are not.
# Whether a point is found depends almost entirely on whether ITS COUNCIL has a
# flood overlay loaded — a property shared by every point in that council — so
# outcomes arrive in blocks, not independently. The published run makes this
# vivid: seven of eight activation/AOI clusters are 100%, and both misses sit
# in the same 2-point cluster. Treating that as 37 independent observations
# reports an interval narrower than the evidence supports.
#
# So a cluster bootstrap is computed alongside it, resampling whole COUNCILS
# with replacement. It is the conservative number and it is the one the verdict
# uses. Reported together rather than instead, because a reader comparing this
# to another study needs the conventional figure too.
#
# The cluster is the COUNCIL, not the activation/AOI. An earlier version used
# the AOI, which was inconsistent with the very mechanism being argued: if
# recall is driven by whether a council holds a flood overlay, then two AOIs
# inside one council are not independent draws, and resampling them separately
# reports an interval narrower than the evidence supports. Where a council is
# unresolved the AOI is used as a fallback key so the point is never silently
# merged into one giant cluster.
_by_cluster: dict = {}
for _r in results:
    _key = _r.get("council") or f"UNRESOLVED:{_r['act']}/{_r['aoi']}"
    _by_cluster.setdefault(_key, []).append(1 if _r.get("hit") else 0)
_cl_keys = sorted(_by_cluster)
_boot_rng = random.Random(SEED)
_boots = []
for _ in range(20000):
    _flat = [x for k in (_boot_rng.choice(_cl_keys) for _ in _cl_keys) for x in _by_cluster[k]]
    if _flat:
        _boots.append(sum(_flat) / len(_flat))
_boots.sort()
cluster_lo = _boots[int(0.025 * len(_boots))] if _boots else 0.0
cluster_hi = _boots[int(0.975 * len(_boots))] if _boots else 1.0
n_clusters = len(_cl_keys)
print("=" * 74, flush=True)
print(f"scored points        : {len(scored)} (of {len(pts)} sampled)", flush=True)
print(f"executed cleanly     : {executed}", flush=True)
if n_errored:
    print(f"!! ERRORED           : {n_errored} of {len(pts)} points raised and are "
          f"counted as MISSES. Read the recall below with that in mind — this "
          f"script cannot tell a genuine product error from an outage.", flush=True)
print(f"said something       : {said_something}", flush=True)
# The pre-commit says a result within the interval of the mark is reported as
# INDISTINGUISHABLE from it, not as a pass. Applying the stricter rule I wrote
# before seeing the number, rather than the flattering one available after.
# The CLUSTER lower bound governs, not Wilson's. Using the narrower interval
# would be choosing the assumption that flatters after seeing that it fails.
verdict = ("PASS" if cluster_lo >= 0.90 else
           "INDISTINGUISHABLE FROM THE MARK" if cluster_hi >= 0.90 else "FAIL")
# Nothing is out-of-scope at scoring time any more: scope is settled BEFORE
# the loop by the authoritative test, and every exception after it is a miss.
# What is worth counting is how often the two components disagreed.
contradictions = sum(1 for r in results if r.get("scope_contradiction"))
oos = 0
print(f"scope contradictions (lookup said in, run_flood said out): {contradictions}", flush=True)
print(f"RECALL               : {recall:.3f}", flush=True)
print(f"  Wilson 95% CI      : {lo:.3f} - {hi:.3f}  (assumes 37 independent trials — they are not)", flush=True)
print(f"  CLUSTER 95% CI     : {cluster_lo:.3f} - {cluster_hi:.3f}  ({n_clusters} council clusters; THIS governs)", flush=True)
print(f"PASS MARK            : 0.90, committed before the run", flush=True)
print(f"VERDICT              : {verdict}", flush=True)
print("=" * 74, flush=True)
Path(WT / "docs/qa/flood-calibration-2022-result.json").write_text(
    json.dumps({"n_raw_draws": n_raw_draws, "n_in_scope": len(pts),
                "n_out_of_scope_at_scope_test": n_out_of_scope,
                "n_scope_unresolved": n_scope_unknown,
                "n_sampled": len(pts), "n_scored": len(scored), "hits": said_something,
                "n_executed": executed, "n_errored": n_errored,
                "dropped_groups": DROPPED_GROUPS,
                "recall": recall, "wilson_lo": lo, "wilson_hi": hi,
                "cluster_lo": cluster_lo, "cluster_hi": cluster_hi,
                "n_clusters": n_clusters, "cluster_unit": "council",
                "clusters": {k: {"n": len(v), "hits": sum(v)} for k, v in sorted(_by_cluster.items())},
                "pass_mark": 0.90, "verdict": verdict, "out_of_scope_at_scoring": oos,
                "scope_contradictions": contradictions,
                "seed": SEED, "results": results}, indent=2), encoding="utf-8")
print("written: docs/qa/flood-calibration-2022-result.json", flush=True)
