#!/usr/bin/env python3
"""DQ-87: is the flood screen's recall actually established, or only measured?

prior-art-checked: no ledger row tracked flood calibration status. Four sweeps
2026-08-25 against origin/main 08d4f222: (1) not a data source — this reads a
committed JSON result file, no table involved; (2) frontend — grep for
calibration|recall over frontend-nextjs/{app,lib,components} returns nothing
about flood recall; (3) python — scripts/run_flood_calibration_2022.py PRODUCES
the measurement but asserts nothing about whether it settles anything, and
dq_probe_live.py's flood rows (DQ-57/85/86) are about council scoping, not
recall; (4) .claude/dq_checks.json had no row mentioning calibration except
DQ-47, which is the pvlib method claim. Nothing to extend.

WHY THIS EXISTS
---------------
`~/.claude/plans/ce-product-assurance-position-2026-08.md` records flood as
"indistinguishable from the mark. Not a pass." That is a sentence in a plan
file, and this repo's standing lesson is that a status written by hand decays
silently. The measurement itself is committed at
docs/qa/flood-calibration-2022-result.json; this makes the CONCLUSION drawn
from it executable.

WHAT IT ASSERTS, and what it deliberately does not
--------------------------------------------------
It does NOT assert a recall figure. Recall moving is not a defect — it is the
result of a rerun, and pinning it would make an honest remeasurement look like
a regression.

It asserts the thing that would make the "uncalibrated" claim WRONG: that the
governing interval clears the pass mark. The cluster interval governs, not
Wilson, because the sampled points are not independent — they come from a
handful of council clusters, and Wilson assumes otherwise. Measured 2026-08-25,
corrected 2026-09-01 (see DQ-87 in DATA_QUALITY_TRACKER.md — the script's own
live network calls to maps.six.nsw.gov.au and www.bom.gov.au are not stable
run-to-run):
recall 0.946 over 37 in-scope points in 7 clusters, cluster 95% CI
0.727-1.000, mark 0.90 committed before the first run. The interval straddles
the mark, so the row is OPEN and this exits non-zero.

It closes when cluster_lo >= pass_mark: at that point the floor of the honest
interval is above the mark and "uncalibrated" stops being true. More points
from the SAME seven councils will not do that — the binding constraint is
cluster diversity, not sample size.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_RESULT = _ROOT / "docs" / "qa" / "flood-calibration-2022-result.json"


def main() -> int:
    if not _RESULT.exists():
        print(f"DQ-87 UNKNOWN: {_RESULT.relative_to(_ROOT)} is missing.")
        print("  UNKNOWN is not CLEAN. Exit 2.")
        return 2
    try:
        d = json.loads(_RESULT.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        print(f"DQ-87 UNKNOWN: cannot read the result file: {exc}")
        return 2

    for key in ("recall", "pass_mark", "cluster_lo", "cluster_hi", "n_clusters",
                "n_in_scope"):
        if d.get(key) is None:
            print(f"DQ-87 UNKNOWN: result file has no {key!r}.")
            print("  A result that cannot be read is not a pass. Exit 2.")
            return 2

    recall, mark = d["recall"], d["pass_mark"]
    lo, hi, clusters, n = (d["cluster_lo"], d["cluster_hi"],
                           d["n_clusters"], d["n_in_scope"])
    settled = lo >= mark

    print("DQ-87: Is the flood screen's recall ESTABLISHED, or only measured?")
    print(f"  recall            : {recall:.3f} over {n} in-scope points")
    print(f"  cluster 95% CI    : {lo:.3f} - {hi:.3f}  ({clusters} council clusters)")
    print(f"  pass mark         : {mark}  (committed before the first run)")
    print(f"  query             : cluster_lo >= pass_mark  ->  {lo:.3f} >= {mark} is {settled}")
    if settled:
        print("  CLEAN — the floor of the governing interval clears the mark.")
        return 0
    print("  means : the interval STRADDLES the mark, so recall is measured and not")
    print("          established. Flood remains uncalibrated and every customer-facing")
    print("          surface must keep saying so. The cluster interval governs because")
    print("          the points are not independent; Wilson assumes they are and reads")
    print(f"          narrower. More points from the same {clusters} councils will not")
    print("          close this — the binding constraint is cluster diversity.")
    print("  NOTE  : no specificity figure exists at all. Recall says it finds real")
    print("          floods; nothing here says it does not cry wolf.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
