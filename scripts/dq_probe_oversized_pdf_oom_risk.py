#!/usr/bin/env python3
# prior-art-checked: reuses dq_db.session() (this project's one shared read-only
# DB connection helper) and dcp_chapter_registry.url_content_length (already
# populated by the existing dcp-monitor HTTP-HEAD check) -- no new data source,
# no live R2 call, no new size-tracking mechanism.
"""DQ-98 probe: how many currently-active DCP chapter PDFs are large enough to
carry the same OOM risk that killed the real 2026-09-06 production dcp-extract
run (Railway, exit code -9) on canterbury_bankstown/chapter-7-6-belmore-and-
lakemba (139,006,750 bytes).

THIS COUNT CANNOT REACH 0 BY DESIGN until the split-PDF fix (DQ-98) is built --
see .claude/DATA_QUALITY_TRACKER.md. It exists to make the risk visible and
falsifiable, not to gate anything: a genuinely large council DCP is real
content, not a defect, and the fix is to chunk it before extraction, not to
shrink the PDF.

Threshold (30 MB) is a rough heuristic from the only data points measured so
far, not a precisely calibrated cutoff:
  - CONFIRMED CRASHED (exit -9, production, 2026-09-06): 139,006,750 bytes
  - CONFIRMED SAME COUNCIL, not yet re-extracted since (same risk, unconfirmed):
    canterbury_bankstown/chapter-6-2-bankstown-city-centre, 117,829,367 bytes
  - CONFIRMED PATHOLOGICALLY SLOW (2 independent timeout attempts, 90s and
    300s, same session): ku_ring_gai/section-b-part-14e-lindfield-local-centre,
    35,405,674 bytes (also 14a/14d, sizes not yet pulled)
  - CONFIRMED FINE (graded successfully, no timeout, same session):
    ashfield/chapter-d-precinct-guidelines, 20,607,908 bytes
30 MB sits in the gap between the largest CONFIRMED-FINE chapter and the
smallest CONFIRMED-TROUBLED one. It will mis-classify some genuinely-fine
large PDFs and may miss a genuinely-troubled small one (page count, two-column
layout, and embedded raster images likely matter more than raw byte size) --
a coarse triage signal, not a diagnosis, same caveat DQ-97's symptom probe
carries for its own regex.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dq_db  # noqa: E402

_THRESHOLD_BYTES = 30 * 1024 * 1024


def run() -> int:
    with dq_db.session() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT council, chapter_key, url_content_length "
            "FROM dcp_chapter_registry "
            "WHERE is_active AND url_content_length > %s "
            "ORDER BY url_content_length DESC",
            (_THRESHOLD_BYTES,),
        )
        rows = cur.fetchall()
    if not rows:
        print(f"PASSED: no active chapter PDF exceeds {_THRESHOLD_BYTES:,} bytes.")
        return 0
    print(f"{len(rows)} active chapter PDF(s) exceed the {_THRESHOLD_BYTES:,}-byte "
          f"OOM-risk threshold (DQ-98, not yet fixed -- split-PDF extraction):")
    for council, chapter_key, size in rows:
        print(f"  {council}/{chapter_key}: {size:,} bytes")
    return 1


if __name__ == "__main__":
    sys.exit(run())
