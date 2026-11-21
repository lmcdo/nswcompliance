"""Check the route pointers in a walking surface file: does following them give the walk the file says?

For every stored point the chain of pointers is followed to its end (the point the station link joins). The length of that chain
(straight segments between the stored points) is compared with the stored walk distance minus the distance stored at the chain's end.
They match when the pointers follow the shortest-walk tree the build computed; a pointer to the wrong point shows up as a large gap.

Usage: python scripts/lmr_area/check_route_pointers.py FILE_OR_FOLDER [...]     (.npz or .json.gz; exits 1 when any file fails)
Pass marks (all must hold): every chain ends (no loop, no pointer out of range), at least 99% of points are within 1 m, and no point is
more than 15 m out (the length of one street step, STEP in build_walk_surfaces.py, so a skipped busy-road copy cannot hide a wrong turn).
This is a developer check; the page and the engine never call it. It is run after every rebuild of the walking files.
"""
# prior-art-checked: 2026-11-20. Route pointers are new in this branch, so no existing script checks them. The check_*.py scripts the guard
# lists (railway cron drift, production status, rate checks) are unrelated, and the walk checks that exist (area_check_test.py,
# area_check_score.py) compare the ANSWER with an independent router, not the pointers. This reads files through services/lmr_walk_surface.py.
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from services import lmr_walk_surface as ws  # noqa: E402

WITHIN_1M_SHARE = 0.99
MAX_ERROR_M = 15.0


def chain_lengths(xy: np.ndarray, parent: np.ndarray):
    """(length along the chain to its end, row of that end) for every row; (nan, -1) for a row whose chain loops."""
    n = len(parent)
    p = parent.tolist()
    x, y = xy[:, 0].tolist(), xy[:, 1].tolist()
    state = [0] * n   # 0 = not seen, 1 = on the chain being followed, 2 = done
    acc, end = [float("nan")] * n, [-1] * n
    for start in range(n):
        if state[start] == 2:
            continue
        stack = []
        cur = start
        ok = True
        while True:
            if state[cur] == 2:
                break
            if state[cur] == 1:   # back at a point already on this chain: a loop
                ok = False
                break
            state[cur] = 1
            stack.append(cur)
            if p[cur] < 0:
                acc[cur], end[cur] = 0.0, cur
                state[cur] = 2
                stack.pop()
                break
            cur = p[cur]
        for r in reversed(stack):   # fill the chain back from its known end
            if not ok:
                acc[r], end[r] = float("nan"), -1
            else:
                q = p[r]
                acc[r] = acc[q] + ((x[r] - x[q]) ** 2 + (y[r] - y[q]) ** 2) ** 0.5
                end[r] = end[q]
            state[r] = 2
    return np.asarray(acc), np.asarray(end, dtype=np.int64)


def check_file(path: Path) -> dict:
    s = ws.load_surface(str(path))
    if s.parent is None:
        return {"file": path.name, "ok": False, "why": "no usable route pointers in this file"}
    acc, end = chain_lengths(s.xy, s.parent)
    looped = int(np.isnan(acc).sum())
    good = ~np.isnan(acc)
    err = np.abs(acc[good] - (s.dist[good] - s.dist[end[good]]))
    share1 = float((err <= 1.0).mean()) if len(err) else 0.0
    worst = float(err.max()) if len(err) else 0.0
    ok = looped == 0 and share1 >= WITHIN_1M_SHARE and worst <= MAX_ERROR_M
    ends = np.unique(end[good])
    return {"file": path.name, "ok": ok, "points": len(s.parent), "looped": looped, "within_1m": round(share1, 4),
            "within_15m": round(float((err <= MAX_ERROR_M).mean()), 4) if len(err) else 0.0,
            "median_err_m": round(float(np.median(err)), 2) if len(err) else None, "worst_err_m": round(worst, 1),
            "chain_ends": int(len(ends)), "end_dist_max_m": round(float(s.dist[ends].max()), 1) if len(ends) else None}


def main(argv: list[str]) -> int:
    files: list[Path] = []
    for a in argv:
        p = Path(a)
        files += sorted(list(p.glob("*.npz")) + list(p.glob("*.json.gz"))) if p.is_dir() else [p]
    if not files:
        print("no files given")
        return 1
    bad = 0
    for f in files:
        r = check_file(f)
        print(("PASS " if r["ok"] else "FAIL ") + ", ".join(f"{k}={v}" for k, v in r.items() if k != "ok"), flush=True)
        bad += 0 if r["ok"] else 1
    print(f"{len(files) - bad} of {len(files)} files pass")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
