#!/usr/bin/env python3
"""Claim 7's depth half, observed where users get it: the production flood answer.

prior-art-checked: no script or test under scripts/ or tests/ calls the production flood route (grep
'pipeline/flood' and 'nswcompliance-production', 2026-09-14). scripts/run_flood_calibration_2022.py runs the
pipeline in-process, which proves the code, not that the production host holds the rasters.
scripts/verify_coverage_stats.live_flood_depth_study_count counts the has_depth entries; this reads the same
FLOOD_STUDIES block for their keys, so the points below cannot drift from the published count unnoticed.

WHY A LIVE CALL. The claim inventory (section 5.1) recorded that the raster download for the depth studies had
never been observed succeeding on the production host, so "modelled flood depth from 3" rested on configuration.
A study whose rasters are missing on the host degrades to "not assessed", which reads like a normal answer.

WHAT IT ASKS. One cell per depth study, picked on 2026-09-14 from the council's own 1% AEP depth raster where
the modelled depth lies between 0.5 m and 2.5 m, converted to lat/lng with the study's CRS from FLOOD_STUDIES.
The depth recorded beside each point is that raster cell's value read from the local copy of the file; it is a
measurement the check compares against, never a value served to anyone. Production must name the study and
return a 1% AEP depth within 5 cm of it (the route rounds to 2 dp). persist=false, so the call writes nothing.

Verdicts: PASS every depth study answered with its recorded depth; FAIL a study was not named, was named
without a finite depth, answered a different depth, the answer was not the expected shape, or the route returned
an HTTP error; UNKNOWN the route could not be reached at all, or OUTREACH_PRODUCTION_API pointed the probe at a
host other than production (answers from anywhere else cannot show delivery in production). Never PASS then.
"""
from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_PRODUCTION_API = "https://nswcompliance-production.up.railway.app"
PRODUCTION_API = os.environ.get("OUTREACH_PRODUCTION_API", CANONICAL_PRODUCTION_API)
PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"

#: (study_key, lat, lng, 1% AEP depth in metres held by the council raster at that cell)
POINTS = (
    ("tweed", -28.24539, 153.53519, 2.008),        # Tweed_001_1p_d_Max.tif row 3285 col 10500, EPSG:28356
    ("wollongong", -34.435229, 150.895453, 1.214),  # Wollongong_1pct_d_Max.asc row 1350 col 2381, EPSG:7856
    ("redbank", -33.55053, 150.703411, 1.473),      # RedbankCk_DES_1pcAEP_d_Max_ProcessedOutput.tif row 155 col 5059
)
TOLERANCE_M = 0.05
TIMEOUT_S = 150


def depth_study_keys(flood_truth_py: Path = ROOT / "services" / "flood_truth.py") -> set[str]:
    """Keys of the FLOOD_STUDIES entries that carry has_depth=True, read from the source file."""
    text = flood_truth_py.read_text(encoding="utf-8")
    start = text.find("FLOOD_STUDIES: dict[str, dict] = {")
    if start == -1:
        raise RuntimeError("FLOOD_STUDIES not found in services/flood_truth.py")
    block = text[start:text.find("\n}\n", start)]
    heads = list(re.finditer(r"^\s{4}[\"'](\w+)[\"']\s*:\s*\{", block, re.M))
    keys = set()
    for i, head in enumerate(heads):
        body = block[head.end():heads[i + 1].start() if i + 1 < len(heads) else len(block)]
        if re.search(r'"has_depth":\s*True', body):
            keys.add(head.group(1))
    return keys


def ask(study: str, lat: float, lng: float) -> tuple[dict | None, str, bool]:
    """POST one point to the production flood route. Returns (body, error, reached)."""
    payload = json.dumps({"address": f"OC-7 depth probe point ({study} 1% AEP raster cell)", "lat": lat,
                          "lng": lng, "report_id": f"oc7-depth-probe-{study}", "persist": False}).encode("utf-8")
    req = urllib.request.Request(f"{PRODUCTION_API}/pipeline/flood", data=payload, method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "outreach-claim-check"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return json.loads(resp.read().decode("utf-8")), "", True
    except urllib.error.HTTPError as exc:
        return None, f"production returned HTTP {exc.code}", True
    except ValueError as exc:
        return None, f"production returned a body that is not JSON ({exc})", True
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, f"production could not be reached ({exc})", False


def judge(study: str, expected_m: float, body: dict) -> tuple[str, str]:
    """PASS only when the answer names this study and gives its 1% AEP depth within tolerance."""
    # Every level is type-checked: valid JSON of the wrong shape is a FAIL with a reason, never an exception.
    outputs = body.get("outputs") if isinstance(body, dict) else None
    listed = outputs.get("flood_studies") if isinstance(outputs, dict) else None
    studies = [s for s in listed if isinstance(s, dict)] if isinstance(listed, list) else []
    entry = next((s for s in studies if s.get("study_key") == study), None)
    if entry is None:
        return FAIL, f"{study}: not named in the answer (studies named: {[s.get('study_key') for s in studies]})"
    design = entry.get("design")
    one_pct = design.get("1pct") if isinstance(design, dict) else None
    one_pct = one_pct if isinstance(one_pct, dict) else {}
    depth = one_pct.get("depth_m")
    # json.loads accepts NaN and Infinity, and abs(NaN - x) > tolerance is False, so a non-finite depth would pass.
    if isinstance(depth, bool) or not isinstance(depth, (int, float)) or not math.isfinite(depth):
        return FAIL, f"{study}: named without a 1% AEP depth (depth {depth!r}, level {one_pct.get('level_m_ahd')!r})"
    if abs(depth - expected_m) > TOLERANCE_M:
        return FAIL, f"{study}: 1% AEP depth {depth} m, but the raster cell holds {expected_m} m"
    return PASS, f"{study} {depth} m (raster {expected_m} m)"


def flood_depth_delivered_in_production() -> tuple[str, str]:
    try:
        keys = depth_study_keys()
    except (OSError, RuntimeError) as exc:
        return FAIL, f"depth in production: cannot read FLOOD_STUDIES ({exc})"
    pointed = {p[0] for p in POINTS}
    if keys != pointed:
        return FAIL, (f"depth in production: probe points cover {sorted(pointed)} but FLOOD_STUDIES has depth "
                      f"for {sorted(keys)}; pick a raster cell for each")
    with ThreadPoolExecutor(max_workers=len(POINTS)) as pool:
        answers = list(pool.map(lambda p: ask(p[0], p[1], p[2]), POINTS))
    verdicts = []
    for (study, _lat, _lng, expected), (body, error, reached) in zip(POINTS, answers):
        if body is None:
            verdicts.append((FAIL if reached else UNKNOWN, f"{study}: {error}"))
        else:
            verdicts.append(judge(study, expected, body))
    kinds = {v for v, _ in verdicts}
    worst = FAIL if FAIL in kinds else UNKNOWN if UNKNOWN in kinds else PASS
    detail = "; ".join(d for _, d in verdicts)
    if worst == PASS and PRODUCTION_API.rstrip("/") != CANONICAL_PRODUCTION_API:
        return UNKNOWN, (f"depth in production: answered by {PRODUCTION_API}, not the production host "
                         f"{CANONICAL_PRODUCTION_API}, so it cannot show delivery in production; {detail}")
    return worst, "depth in production: " + detail


if __name__ == "__main__":
    verdict, detail = flood_depth_delivered_in_production()
    print(f"{verdict}: {detail}")
    raise SystemExit({PASS: 0, FAIL: 1}.get(verdict, 2))
