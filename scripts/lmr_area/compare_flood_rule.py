# prior-art-checked: four sweeps 2026-11-22. (1) DB: none (runs on the committed map copies only). (2) Frontend: none. (3) Python: scripts/lmr_area/area_check_test.py runs the whole area check on
# lots over the network; this runs only the s164(1)(f) rule, old rule against new, on the saved copies, so it needs no network. (4) Plans: ce-evidence-flood-pmf-and-pipeline-SCOPE-2026-11-22.md
# (proof step 5: the same points before and after, every change counted by direction).
"""Compare the s164(1)(f) flood rule BEFORE (catchment only) and AFTER (the flood-study copy decides inside its box) on random points.

    python scripts/lmr_area/compare_flood_rule.py [N_PER_GROUP]      # default 200 per group, fixed seed; exits 1 if any lot moves to "clear" while inside or near a flood area

Each point gets a 20 m square lot outline. Groups: in the Hawkesbury-Nepean catchment inside the flood study's box; outside the catchment but inside the box; within 300 m of a flood
edge; in the catchment but outside the box. Prints every old -> new change, by direction, with examples. No network, no database.
"""
from __future__ import annotations

import math
import random
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from services import lmr_area_decision as dec   # noqa: E402
from services import lmr_area_inputs as inp   # noqa: E402
from services import lmr_map_copy as mc   # noqa: E402


def square(lat: float, lng: float, half_m: float = 10.0) -> list:
    dx, dy = half_m / (111320 * math.cos(math.radians(lat))), half_m / 110540
    return [[lng - dx, lat - dy], [lng + dx, lat - dy], [lng + dx, lat + dy], [lng - dx, lat + dy], [lng - dx, lat - dy]]


def rule_f(m: dict, facts: "dec.LawFacts") -> dict | None:
    for r in dec._lmr_rules(m, facts):
        if r.get("rule") == "pmf_hawkesbury_nepean":
            return r
    return None


def main(argv: list[str]) -> int:
    n = int(argv[0]) if argv else 200
    rnd = random.Random(20261122)
    facts = dec.LawFacts.load()
    lay = mc.MapCopy().layer("hn_pmf", mc.date.today() if hasattr(mc, "date") else None)
    if lay is None:
        print("FAIL: the flood copy did not load")
        return 1
    minx, miny, maxx, maxy = lay.bounds
    verts = [c for g in lay.geoms for poly in getattr(g, "geoms", [g]) for c in poly.exterior.coords][::7]

    def pts_random(box, k):
        return [(rnd.uniform(box[1], box[3]), rnd.uniform(box[0], box[2])) for _ in range(k)]

    wide = (minx - 0.6, miny - 0.6, maxx + 0.6, maxy + 0.6)
    groups: dict[str, list] = {"in box (random)": pts_random((minx, miny, maxx, maxy), n * 3), "near a flood edge": [], "outside the box (random, wide)": pts_random(wide, n * 3)}
    for _ in range(n):
        x, y = rnd.choice(verts)
        d, a = rnd.uniform(0, 300), rnd.uniform(0, 2 * math.pi)
        groups["near a flood edge"].append((y + d * math.sin(a) / 110540, x + d * math.cos(a) / (111320 * math.cos(math.radians(y)))))
    trans: Counter = Counter()
    examples: dict = {}
    skipped = 0
    bad = []
    for gname, pts in groups.items():
        for lat, lng in pts:
            rings = square(lat, lng)
            cat = inp._copy_answer("hn_catchment", lat, lng, rings, mc.check)
            if cat is None:
                skipped += 1   # near a catchment edge or unprovable: the live map decides in production, so it is not part of this comparison
                continue
            m_old = {"hn_catchment": cat}
            m_new = {**m_old, "flood_study": inp._flood_study(lat, lng, rings, mc.flood_distance)}
            old, new = rule_f(m_old, facts), rule_f(m_new, facts)
            o = old.get("outcome") if old else "no rule"
            nw = new.get("outcome") if new else "no rule"
            state = (new or {}).get("figures", {}).get("flood_state")
            key = (gname, f"{o} -> {nw}" + (f" ({state})" if state else ""))
            trans[key] += 1
            examples.setdefault(key, (round(lat, 5), round(lng, 5)))
            if nw == "clear" and state != "outside" and o != "clear":
                bad.append((gname, lat, lng, o, nw, state))
            if nw == "clear" and state == "outside":
                f = (new or {}).get("figures", {})
                if f.get("inside") or (f.get("edge_m") is not None and f.get("edge_m") <= dec.FLOOD_EDGE_M):
                    bad.append((gname, lat, lng, "clear while inside/near", nw, f))
    total = sum(trans.values())
    print(f"points compared {total}; skipped (catchment copy gave no answer) {skipped}")
    for (g, t), c in sorted(trans.items()):
        print(f"  {g:34s} {t:42s} {c:4d}   e.g. {examples[(g, t)]}")
    print(f"moved to clear while inside or near a flood area: {len(bad)}  <- must be 0")
    for b in bad[:6]:
        print("   ", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
