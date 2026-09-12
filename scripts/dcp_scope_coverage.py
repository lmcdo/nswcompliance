#!/usr/bin/env python3
# prior-art-checked: nothing measures a council against the DEFAULT SCOPE. Neighbours
# opened, not guessed from their names:
#   dcp_inscope_status.py   scores chapters we ALREADY HOLD against each council's
#                           frontend config. It cannot see a chapter that was never
#                           mirrored, because it starts from the measurement ledger,
#                           and a chapter with no PDF never reaches the ledger. That
#                           blind spot is the entire reason this file exists.
#   dcp_chapter_measure.py  measures a chapter against its own source PDF -- needs a
#                           PDF to exist.
#   r2_monitor.py           MIRRORS pdfs, and is the remediation tool this check
#                           grades. It is not duplicated here; it is measured.
#   verify_lga_capability_flags.py   asserts a council's advertised flags match the
#                           database. Complementary: that guards the CLAIM, this
#                           measures the CONTENT behind it.
# DB sweep: no table records default-scope coverage.
"""Does each council have the six chapters the product actually needs?

THE SCOPE THIS MEASURES AGAINST
-------------------------------
Decided 2026-09-10, merged as PR #1077, in docs/DCP_SCOPE_CONFIG_REFERENCE.md:
a new council needs roughly SIX chapters, not the whole DCP.

  1 general / introductory      4 parking and transport
  2 low and medium density      5 landscaping and trees
  3 residential flat / mixed    6 heritage (second priority, not skipped)

The justification is measured, not assumed: every numeric control the product
renders is residential (all 1,071 rows of dcp_setback_controls), while a full DCP
extraction is 19.9% heritage and 7.5% signage. The four topics the product renders
are about a fifth of the text.

WHY THIS EXISTS SEPARATELY FROM dcp_inscope_status
--------------------------------------------------
That report starts from the measurement ledger, so it can only see chapters that
have a PDF to measure. A council that never had its documents mirrored is
invisible to it -- and that is the majority case. Measured 2026-09-12:

    3 councils have all six chapters serving. SIXTEEN have none.
    Of 37 in-scope chapters not serving, 33 have no mirrored PDF and only
    4 have a PDF that was never extracted.

So 89% of the gap is a missing FILE, not extraction quality. A status report that
cannot say that sends the next session to fix the wrong thing -- which is exactly
what happened before this file was written.

THE THREE LANES, WHICH NEED DIFFERENT WORK
------------------------------------------
  MIRRORED      the PDF is in R2. Serving or extractable.
  NO_PDF_HAVE_URL   council_url is recorded, so r2_monitor can fetch it now.
  NO_PDF_HAVE_PAGE  only a council PAGE url. Needs a hub scraper to find the PDF
                    link before r2_monitor can see it -- r2_monitor selects on
                    `council_url IS NOT NULL`, so these are invisible to it.
  NO_PDF_NO_URL     neither. A person must find the document.

HONESTY
-------
Bucket matching is on chapter_key + chapter_label text, so chapters that match no
bucket are COUNTED AND NAMED, never dropped. is_spatial and is_inert chapters are
excluded -- City of Sydney alone carries 233 map sheets that can never produce a
provision and would otherwise dominate every count.

    python scripts/dcp_scope_coverage.py
    python scripts/dcp_scope_coverage.py --gaps      # only what is missing
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# The six default-scope buckets. Patterns match the council's own chapter naming,
# which differs per council, so they are deliberately broad -- a chapter matching
# no bucket is reported rather than silently treated as out of scope.
BUCKETS: list[tuple[str, str]] = [
    ("general", r"general|introduc|statutory|site.?(analysis|context)|prelim|miscell|admin"),
    ("residential", r"low.?(and|&)?.?med|low.?density|dwelling.?house|residential(?!.?flat)"
                    r"|dual.?occup|multi.?dwelling|secondary.?dwell"),
    ("rfb_mixed", r"residential.?flat|rfb|apartment|mixed.?use"),
    ("parking", r"park|transport|access.?and.?mobility|traffic"),
    ("landscape", r"landscap|tree|vegetation|green"),
    ("heritage", r"heritage|conservation|hca"),
]

MIRRORED, HAVE_URL, HAVE_PAGE, NO_URL = (
    "MIRRORED", "NO_PDF_HAVE_URL", "NO_PDF_HAVE_PAGE", "NO_PDF_NO_URL")
# Better states win when several chapters map to the same bucket.
RANK = {"": 0, NO_URL: 1, HAVE_PAGE: 2, HAVE_URL: 3, "NOT_EXTRACTED": 4, "SERVING": 5}


def bucket_for(chapter_key: str, label: str) -> str | None:
    """Which of the six this chapter is, or None when it matches none of them."""
    text = ((chapter_key or "") + " " + (label or "")).lower()
    for name, pattern in BUCKETS:
        if re.search(pattern, text):
            return name
    return None


def chapter_state(r2_path, council_url, page_url, serving: bool) -> str:
    """What stands between this chapter and a user seeing it."""
    if serving:
        return "SERVING"
    if r2_path:
        return "NOT_EXTRACTED"
    if council_url:
        return HAVE_URL
    if page_url:
        return HAVE_PAGE
    return NO_URL


def _connect():
    try:
        from scripts.check_council_completeness import _load_env as shared
    except ImportError:
        from check_council_completeness import _load_env as shared
    shared()
    import psycopg2
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise SystemExit("FATAL: no DATABASE_URL / SUPABASE_DB_URL")
    conn = psycopg2.connect(url, connect_timeout=20)
    cur = conn.cursor()
    cur.execute("SET statement_timeout='120s'")
    return conn, cur


def collect():
    conn, cur = _connect()
    cur.execute("""SELECT council, chapter_key, chapter_label, r2_current_path,
                          council_url, council_page_url
                   FROM dcp_chapter_registry
                   WHERE is_active AND NOT is_spatial AND NOT is_inert""")
    registry = cur.fetchall()
    cur.execute("""SELECT source_council, source_chapter_key
                   FROM regulatory_provisions
                   WHERE is_current AND source_chapter_key IS NOT NULL
                   GROUP BY 1, 2""")
    serving = {(c, k) for c, k in cur.fetchall()}
    conn.close()

    per = defaultdict(lambda: {name: "" for name, _ in BUCKETS})
    blockers = defaultdict(list)
    unbucketed = defaultdict(list)
    for council, key, label, r2_path, url, page in registry:
        bucket = bucket_for(key, label)
        if bucket is None:
            unbucketed[council].append(key)
            continue
        state = chapter_state(r2_path, url, page, (council, key) in serving)
        if RANK[state] > RANK[per[council][bucket]]:
            per[council][bucket] = state
        if state != "SERVING":
            blockers[state].append((council, key, url or page or ""))
    return per, blockers, unbucketed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--gaps", action="store_true", help="only the missing work")
    args = ap.parse_args(argv)
    per, blockers, unbucketed = collect()

    short = {"SERVING": "yes", "NOT_EXTRACTED": "not extr", HAVE_URL: "url only",
             HAVE_PAGE: "page only", NO_URL: "NO URL", "": "-"}
    if not args.gaps:
        head = ("  council".ljust(24) +
                "".join(n[:9].rjust(11) for n, _ in BUCKETS) + "have".rjust(7))
        print("DEFAULT-SCOPE COVERAGE -- the six chapters the product needs")
        print("(PR #1077, docs/DCP_SCOPE_CONFIG_REFERENCE.md)")
        print()
        print(head)
        print("  " + "-" * (len(head) - 2))
        for council in sorted(per, key=lambda c: -sum(
                1 for n, _ in BUCKETS if per[c][n] == "SERVING")):
            got = sum(1 for n, _ in BUCKETS if per[council][n] == "SERVING")
            print("  " + council.ljust(22) +
                  "".join(short[per[council][n]].rjust(11) for n, _ in BUCKETS) +
                  (str(got) + "/6").rjust(7))
        done = sum(1 for c in per if all(
            per[c][n] == "SERVING" for n, _ in BUCKETS))
        none = sum(1 for c in per if not any(
            per[c][n] == "SERVING" for n, _ in BUCKETS))
        print("  " + "-" * (len(head) - 2))
        print("  councils with all six: " + str(done) +
              "    with none: " + str(none) +
              "    total: " + str(len(per)))

    print()
    print("WHAT STANDS IN THE WAY (in-scope chapters not serving)")
    order = [HAVE_URL, HAVE_PAGE, NO_URL, "NOT_EXTRACTED"]
    why = {HAVE_URL: "r2_monitor can fetch these NOW",
           HAVE_PAGE: "need a hub scraper to find the PDF link first -- "
                      "r2_monitor selects on council_url IS NOT NULL and cannot see them",
           NO_URL: "a person must find the document",
           "NOT_EXTRACTED": "PDF is mirrored; extraction never ran"}
    for state in order:
        items = blockers.get(state) or []
        print()
        print("  " + state + "  (" + str(len(items)) + ")  -- " + why[state])
        for council, key, ref in sorted(items):
            print("     " + council.ljust(19) + key[:34].ljust(36) + str(ref)[:52])

    if unbucketed:
        n = sum(len(v) for v in unbucketed.values())
        print()
        print("  matched none of the six buckets (" + str(n) +
              " chapters, counted not dropped):")
        for council, keys in sorted(unbucketed.items())[:8]:
            print("     " + council.ljust(19) + str(len(keys)) + "  e.g. " +
                  ", ".join(keys[:2]))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print("FATAL: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        sys.exit(1)
