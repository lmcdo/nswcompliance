"""Scratchpad, efficient version: ONE footpath download per area for ALL its anchors, one multi-source Dijkstra, one surface file.
(The per-anchor version downloaded 84 overlapping networks; this downloads about 5.)
Overpass 'around' with a polyline of points returns every way within RADIUS of any anchor point, in a single request.
Output: walk_surfaces/<area>.json.gz in the format services/lmr_walk_surface.Surface reads.
Usage: python -u -I build_lmr_walk_surfaces2.py --bbox=S,W,N,E --name=area-slug"""
# prior-art-checked: 2026-11-07. A grep of scripts/ and services/ for station entrance, walking surface, valhalla and gtfs finds no
# existing builder or test of this data; this script is part of the low-and-mid-rise area-check data pipeline
# (see ~/.claude/plans/ce-NEXT-PROMPT-2026-11-07b-lmr-area-check-build.md). Working files go to data/lmr_area_work/ (not committed).
import argparse
import gzip
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # the builder is run with -I, which does not add its own folder
import safe_crossings as sc  # noqa: E402  (the walking graph and its safe-crossing rule; see that module's docstring)
import networkx as nx
import numpy as np
from pyproj import Transformer
from shapely.geometry import Point, Polygon
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__import__("os").environ.get("LMR_WORK", REPO / "data" / "lmr_area_work"))  # working folder, not committed
HERE.mkdir(parents=True, exist_ok=True)
import os
OUTDIR = HERE / os.environ.get("LMR_SURF_DIR", "walk_surfaces")
OUTDIR.mkdir(exist_ok=True)
STATIONS = json.loads((HERE / os.environ.get("LMR_STATIONS", "lmr_station_entrances_final.json")).read_text(encoding="utf-8"))
UA = {"User-Agent": "plotdetect-lmr-walk/1.0"}
CUTOFF_M = 1100
SAFE_STORE_M = 2000   # how far a safe-crossing build stores walks (see STORE_M below)
RADIUS_M = 1500
SNAP_MAX_M = 80
TC_BUFFER_M = 15


def post(url, data, timeout=420):
    r = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), headers=UA)
    return json.load(urllib.request.urlopen(r, timeout=timeout))


OVERPASS_SERVERS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]   # tried in turn when one is down


def overpass(q):
    for i in range(5):
        try:
            j = post(OVERPASS_SERVERS[i % len(OVERPASS_SERVERS)], {"data": q})
            # Overpass answers a query it could not finish (time or memory limit) with HTTP 200, no elements and a "remark".
            # Accepting that gave "graph nodes 0": a failure that looked like an empty map.
            if j.get("remark") or not j.get("elements"):
                raise RuntimeError(f"empty or incomplete reply: {str(j.get('remark'))[:120]}")
            return j
        except Exception as e:
            print("  overpass retry", i, str(e)[:80], flush=True)
            time.sleep(10 * (i + 1))
    return None


def town_centres():
    j = post("https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ePlanning/Planning_Portal_SEPP/MapServer/766/query",
             {"where": "1=1", "outFields": "LABEL", "returnGeometry": "true", "outSR": "4326", "f": "json", "resultRecordCount": 500})
    return [{"label": str(f["attributes"].get("LABEL")), "rings": f["geometry"]["rings"]} for f in j["features"] if f.get("geometry")]


ap = argparse.ArgumentParser()
ap.add_argument("--bbox", required=True)
ap.add_argument("--name", required=True)
ap.add_argument("--safe", action="store_true",
                help="apply the safe-crossing rule (scripts/lmr_area/safe_crossings.py). Must write to its own folder: set LMR_SURF_DIR")
ap.add_argument("--from-file", help="read a saved Overpass download (a JSON list of elements, or {'elements': [...]}) instead of calling Overpass. "
                "The file must have been downloaded with node tags; the result only covers where the file covers")
a = ap.parse_args()
if a.safe and OUTDIR.name == "walk_surfaces":
    # A safe-crossing surface mixed into the default folder would be packed and loaded next to the original one for the same
    # anchors. Refuse, so the two versions can never be confused.
    sys.exit("--safe needs its own output folder: set LMR_SURF_DIR=walk_surfaces_safe")
S, W, N, E = (float(v) for v in a.bbox.split(","))
if (OUTDIR / f"{a.name}.json.gz").exists() or (OUTDIR / f"{a.name}.lock").exists():
    sys.exit(f"{a.name}: already built or being built by another loop; skipping")
(OUTDIR / f"{a.name}.lock").write_text("building")

# anchors in this area: station entrances (or the station point) and Town Centre polygons whose first vertex is inside the box
anchor_pts = []   # (lat, lon, anchor_index)
anchors = []
tc_polys = []     # (anchor_index, [rings])
fp_polys = []     # (anchor_index, hull lon/lat ring) for stations with no mapped entrance
for st in STATIONS["stations"]:
    if not (S <= st["lat"] <= N and W <= st["lon"] <= E):
        continue
    if not st["entrances"] and st.get("footprint"):
        # No mapped entrance: the walk is measured to the station building/platform outline (nodes within 25 m of it). The
        # entrance is somewhere on that outline, so the walk can be too short by up to the outline's longest dimension.
        anchors.append({"name": st["name"], "kind": "station", "entrance_id": "station outline (entrance not mapped)",
                        "optimistic_by_m": st["footprint"]["span_m"], "footprint_anchor": True})
        fp_polys.append((len(anchors) - 1, st["footprint"]["hull_lonlat"]))
        anchor_pts.append((st["lat"], st["lon"], len(anchors) - 1))
        continue
    ents = st["entrances"] or [{"id": "station node", "lat": st["lat"], "lon": st["lon"]}]
    for e in ents:
        anchors.append({"name": st["name"], "kind": "station", "entrance_id": e["id"], "no_mapped_entrance": st["no_mapped_entrance"]})
        if e.get("estimated"):  # found by rule H, not mapped: carry the measured error of that rule as extra uncertainty
            anchors[-1]["optimistic_by_m"] = st.get("entrance_estimate_extra_m", 40)
            anchors[-1]["estimated"] = True
        anchor_pts.append((e["lat"], e["lon"], len(anchors) - 1))
for tc in town_centres():
    p0 = tc["rings"][0][0]
    if S <= p0[1] <= N and W <= p0[0] <= E:
        anchors.append({"name": tc["label"], "kind": "town_centre", "entrance_id": "town centre edge", "no_mapped_entrance": False})
        tc_polys.append((len(anchors) - 1, tc["rings"]))
        for r in tc["rings"]:
            for p in r[::4]:
                anchor_pts.append((p[1], p[0], len(anchors) - 1))
print(f"area {a.name}: {len(anchors)} anchors, {len(anchor_pts)} anchor points", flush=True)
to_m_q = Transformer.from_crs(4326, 28300 + int((((W + E) / 2) + 180) // 6) + 1, always_xy=True).transform
kept_ll = []
if not anchors:
    sys.exit("no anchors in this box")

kept = []  # thin the query points: one per 500 m is plenty when each reaches 1500 m (was ~960 points for one area)
for la, lo, _ in anchor_pts:
    x, y = to_m_q(lo, la)
    if all(math.hypot(x - kx, y - ky) > 500 for kx, ky in kept):
        kept.append((x, y))
        kept_ll.append((la, lo))
poly = ",".join(f"{la:.5f},{lo:.5f}" for la, lo in kept_ll)
print("query points:", len(kept_ll), flush=True)
NODE_OUT = "body" if a.safe else "skel"   # the safe rule needs node tags (crossings, signals); the original needs coordinates only
q = (f'[out:json][timeout:400];way["highway"]["highway"!~"motorway|motorway_link|proposed|construction|raceway|bus_guideway|escape|corridor|elevator"]'
     f'["foot"!="no"]["access"!="private"]["access"!="no"](around:{RADIUS_M},{poly});out body;>;out {NODE_OUT} qt;')
# prior-art-checked: reuse not viable: this is the same Overpass download as overpass() above, only split into pieces and merged; nothing else in
# the repo downloads OpenStreetMap roads (dcp_extract_changed.py and generate_conveyancing_report.py share only generic words with it).
def fetch_in_pieces(points, per=3):
    """A safe build asks for node tags too, which makes one request per area too big for the public server (502 or an empty reply).
    Ask for a few anchor points at a time and merge. If any piece fails the whole build fails: a missing piece would silently drop roads."""
    merged, stamp = {}, ""
    pieces = [points[i:i + per] for i in range(0, len(points), per)]
    for n_, piece in enumerate(pieces, 1):
        qp = (f'[out:json][timeout:200];way["highway"]["highway"!~"motorway|motorway_link|proposed|construction|raceway|bus_guideway|escape|corridor|elevator"]'
              f'["foot"!="no"]["access"!="private"]["access"!="no"](around:{RADIUS_M},{",".join(f"{la:.5f},{lo:.5f}" for la, lo in piece)});out body;>;out body qt;')
        jp = overpass(qp)
        if not jp:
            print(f"  piece {n_}/{len(pieces)} failed: the whole download is abandoned", flush=True)
            return None
        for e in jp["elements"]:
            merged[(e["type"], e["id"])] = e
        stamp = stamp or (jp.get("osm3s") or {}).get("timestamp_osm_base", "")
        print(f"  piece {n_}/{len(pieces)}: {len(merged)} elements so far", flush=True)
    return {"elements": list(merged.values()), "osm3s": {"timestamp_osm_base": stamp}}


t0 = time.time()
if a.from_file:
    saved = json.loads(Path(a.from_file).read_text(encoding="utf-8"))
    j = saved if isinstance(saved, dict) else {"elements": saved}
    j.setdefault("osm3s", {"timestamp_osm_base": f"saved file {Path(a.from_file).name}"})
elif a.safe:
    j = fetch_in_pieces(kept_ll)
else:
    j = overpass(q)
if a.safe and j and not any(e.get("tags") for e in j.get("elements", []) if e.get("type") == "node"):
    # Crossings and signals are tags on nodes. Without them every busy road is uncrossable and the build looks fine.
    sys.exit("--safe needs node tags, and this download has none on any node (was it fetched with 'out skel'?)")
if not j or not j.get("elements"):
    sys.exit("overpass failed")
print(f"downloaded {len(j['elements'])} elements in {time.time()-t0:.0f}s", flush=True)
lon_mid = (W + E) / 2
epsg = 28300 + int((lon_mid + 180) // 6) + 1
to_m = Transformer.from_crs(4326, epsg, always_xy=True).transform
els = j["elements"]
build = sc.build_graph(els, to_m, a.safe)
if build.error:
    sys.exit(f"graph build failed (rule {build.rule}): {build.error}")   # no silent fallback to the other rule
G, nodes = build.graph, build.coords
rule_stats = {k: v for k, v in build.stats.items() if k != "skip_notes"}
print("walk rule:", build.rule, rule_stats, flush=True)
if build.stats.get("skip_notes"):
    print("skipped elements, first reasons:", build.stats["skip_notes"], flush=True)
print("graph nodes", G.number_of_nodes(), "edges", G.number_of_edges(), flush=True)
if G.number_of_nodes() < 200:
    sys.exit("thin graph")
ids = list(G.nodes)
xy = np.array([nodes[k] for k in ids])
tree = STRtree([Point(*p) for p in xy])

src = []  # (node, gap, anchor_idx)
done_station = set()
for la, lo, ai in anchor_pts:
    if anchors[ai]["kind"] != "station" or anchors[ai].get("footprint_anchor"):
        continue
    x, y = to_m(lo, la)
    i = int(tree.nearest(Point(x, y)))
    gap = float(np.hypot(xy[i][0] - x, xy[i][1] - y))
    if gap <= SNAP_MAX_M:
        for kk in sc.physical_group(build, ids[i]):   # an entrance on a barrier node reaches every copy: standing there is not crossing
            src.append((kk, gap, ai))
for ai, rings in tc_polys:
    pg = transform(to_m, unary_union([Polygon(r).buffer(0) for r in rings])).buffer(TC_BUFFER_M)
    import shapely
    inside = shapely.contains_xy(pg, xy[:, 0], xy[:, 1])  # vectorised: same test, far faster than one Point at a time
    for idx in np.nonzero(inside)[0]:
        src.append((ids[int(idx)], 0.0, ai))
import shapely
for ai, hull in fp_polys:
    pg = transform(to_m, Polygon(hull).buffer(0)).buffer(25)
    inside = shapely.contains_xy(pg, xy[:, 0], xy[:, 1])
    for idx in np.nonzero(inside)[0]:
        src.append((ids[int(idx)], 0.0, ai))
print("sources snapped:", len(src), "of", len(anchor_pts), "station points + town-centre nodes", flush=True)
unsnapped = sorted({anchors[ai]["name"] for la, lo, ai in anchor_pts} - {anchors[ai]["name"] for _, _, ai in src})
print("anchors with NO snapped source (will be missing from the surface):", unsnapped, flush=True)

G.add_node("S")
for k, gap, ai in src:
    if not G.has_edge("S", k) or G["S"][k]["w"] > gap:
        G.add_edge("S", k, w=gap)
best_ai = {}
for k, gap, ai in src:
    if k not in best_ai or gap < best_ai[k][0]:
        best_ai[k] = (gap, ai)
# A safe-crossing walk is often a long detour. Stored only to 1100 m, a lot whose safe walk is 1300 m has no stored point and the
# engine can only say "can't tell". Stored to 2000 m it gets its real number and a plain "over the limit". The old rule keeps 1100.
STORE_M = SAFE_STORE_M if a.safe else CUTOFF_M
dist, paths = nx.single_source_dijkstra(G, "S", cutoff=STORE_M, weight="w")
rows = []
for k, d in dist.items():
    if k == "S" or sc.GraphBuild.is_line_copy(k):
        continue   # a busy-road side copy shares its coordinates with the other side's copy: the lookup could take the wrong side's distance
    rows.append([round(nodes[k][0], 1), round(nodes[k][1], 1), round(d, 1), best_ai[paths[k][1]][1]])
# Points along the streets, not only at junctions. A lot on a long street can be 70 m from the nearest junction; with junction points
# only, the lookup let it jump sideways to a junction on another street (found on 2/87 Dunmore St, South Bexley: 485 m against a
# real walk of about 850 m). Every edge gets a point about every STEP metres; its distance is the shorter way round: from either end.
STEP = 15.0
node_info = {k: (d, best_ai[paths[k][1]][1]) for k, d in dist.items() if k != "S"}
extra = 0
for p, q2, dat in G.edges(data=True):
    if p == "S" or q2 == "S":
        continue
    if sc.GraphBuild.is_line_copy(p) and sc.GraphBuild.is_line_copy(q2):
        continue   # along a busy road: no street points on the road line itself (same reason as above)
    ia, ib = node_info.get(p), node_info.get(q2)
    if ia is None and ib is None:
        continue
    L = dat["w"]
    n = int(L // STEP)
    if n < 2:
        continue
    xa, ya = nodes[p]
    xb, yb = nodes[q2]
    for i in range(1, n):
        s = L * i / n
        c = []
        if ia:
            c.append((ia[0] + s, ia[1]))
        if ib:
            c.append((ib[0] + (L - s), ib[1]))
        d, ai = min(c)
        if d <= STORE_M:
            rows.append([round(xa + (xb - xa) * i / n, 1), round(ya + (yb - ya) * i / n, 1), round(d, 1), ai])
            extra += 1
print("street points added between junctions:", extra, flush=True)
# Footpath that exists but has NO walk to any station within STORE_M (a safe-crossing build: the street is cut off by a busy road with no
# formal crossing in the map). Stored with no distance, so the lookup can tell "footpath here, no safe route" from "no footpath here".
stranded = []
# "no route at all" = not connected to any station, however far. A point merely farther than STORE_M is connected: it is over the
# limit, not stranded, and must not get the "no route" reason.
connected = nx.node_connected_component(G, "S") if a.safe else set()
# Keep only footpath that the SAFE rule cuts off. Footpath with no route to a station under the ordinary rule either (an isolated
# fragment: private land, a park path, the edge of the map) is not "cut off by a crossing", and saying so would mislead. Measured on the
# saved Bankstown and Woollahra data: 96% and 92% of the unconnected points were isolated under both rules.
cut_by_rule = set()
if a.safe:
    og = sc.build_graph(els, to_m, False)
    if og.error:
        sys.exit(f"ordinary-rule graph failed: {og.error}")
    O = og.graph
    O.add_node("S")
    for k, gap, ai in src:
        base = k[0] if sc.GraphBuild.is_line_copy(k) else k
        if base in O:
            O.add_edge("S", base, w=gap)
    cut_by_rule = nx.node_connected_component(O, "S")
    print("stranded filter: ordinary-rule graph", O.number_of_nodes() - 1, "nodes,", len(cut_by_rule) - 1, "reach a station", flush=True)
isolated_anyway = 0
for p, q2, dat in (G.edges(data=True) if a.safe else ()):
    if p == "S" or q2 == "S" or p in connected or q2 in connected:
        continue
    if sc.GraphBuild.is_line_copy(p) or sc.GraphBuild.is_line_copy(q2):
        continue
    if p not in cut_by_rule and q2 not in cut_by_rule:
        isolated_anyway += 1   # edges, not points; counted so the log shows what was left out
        continue
    L = dat["w"]
    n = max(1, int(L // STEP))
    xa, ya = nodes[p]
    xb, yb = nodes[q2]
    for i in range(n + 1):
        stranded.append([round(xa + (xb - xa) * i / n, 1), round(ya + (yb - ya) * i / n, 1)])
print("footpath points the safe rule cuts off (route exists under the ordinary rule):", len(stranded),
      "| footpath edges isolated under both rules, left out:", isolated_anyway, flush=True)
x0, y0 = to_m(W, S)
x1, y1 = to_m(E, N)
doc = {"schema": 1, "built": date.today().isoformat(), "osm_extract": (j.get("osm3s") or {}).get("timestamp_osm_base", ""), "epsg": epsg,
       "bbox_m": [x0 - 1000, y0 - 1000, x1 + 1000, y1 + 1000], "cutoff_m": STORE_M, "graph_nodes": G.number_of_nodes() - 1,
       "walk_rule": build.rule, "walk_rule_stats": rule_stats, "anchors": anchors, "nodes": rows}
if a.safe:
    doc["stranded"] = stranded   # only a safe build carries the list; an old-rule file must not claim "nothing is stranded"
with gzip.open(OUTDIR / f"{a.name}.json.gz", "wt", encoding="utf-8") as fh:
    json.dump(doc, fh, separators=(",", ":"))
(OUTDIR / f"{a.name}.lock").unlink(missing_ok=True)
print(f"DONE {a.name}: stored {len(rows)} nodes within {STORE_M} m of an anchor; file {(OUTDIR / (a.name + '.json.gz')).stat().st_size // 1024} KB", flush=True)
