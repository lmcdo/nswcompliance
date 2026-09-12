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

# ── the method ───────────────────────────────────────────────────────────────
# A chapter is in scope when it answers a question the product will ask about a
# REAL PROPERTY in that council. Two kinds of question, and only the first is the
# same everywhere:
#
#   UNIVERSAL   every property has a zone, a lot and a development intent, so
#               every property raises general / residential / RFB / parking /
#               landscaping. Fixed, five buckets.
#   CONDITIONAL a property raises a hazard question only when it CARRIES that
#               overlay. Heritage, flood, acid sulfate, bushfire, riparian,
#               biodiversity, landslide. Per council, derived from
#               spatial_overlays -- not from a template.
#
# WHY THE FIXED SIX WAS WRONG
# Measured 2026-09-12: our own spatial data puts flood across 72 LGAs, acid
# sulfate across 51, riparian 66, landslide 6 -- and every council's mix differs
# (Bayside acid sulfate + flood, Bega Valley acid sulfate only, Campbelltown
# flood only). Yet only 4 of 29 councils have ANY hazard chapter registered,
# because nothing asked for one.
#
# The scope doc made this argument for heritage and did not generalise it:
# "the spatial layer already answers WHETHER a property sits in a conservation
# area. What the DCP adds is what that means for a design." That is exactly the
# flood case. We tell a user across 72 LGAs that their site is flood-affected and
# hold no DCP flood control to say what that means for their floor level.
#
# WHAT "USER VALUE" MEANS HERE, HONESTLY
# It is inferred from what the product can ASK and ANSWER, not from usage data.
# There is no traffic to learn from (the prospector funnel was shelved empty), so
# any claim resting on "users want X" would be invented. What is real: the
# constraints the frontend surfaces, and the overlays a council's properties
# actually carry.

# The five universal buckets. Patterns match the council's own chapter naming,
# which differs per council, so they are deliberately broad -- a chapter matching
# no bucket is reported rather than silently treated as out of scope.
BUCKETS: list[tuple[str, str]] = [
    ("general", r"general|introduc|statutory|site.?(analysis|context)|prelim|miscell|admin"),
    ("residential", r"low.?(and|&)?.?med|low.?density|dwelling.?house|residential(?!.?flat)"
                    r"|dual.?occup|multi.?dwelling|secondary.?dwell"),
    ("rfb_mixed", r"residential.?flat|rfb|apartment|mixed.?use"),
    ("parking", r"park|transport|access.?and.?mobility|traffic"),
    ("landscape", r"landscap|tree|vegetation|green"),
]

# Conditional buckets: required for a council ONLY when its properties carry the
# matching overlay. layer_type values are spatial_overlays' own vocabulary.
HAZARD_BUCKETS: list[tuple[str, str, tuple[str, ...]]] = [
    ("heritage", r"heritage|conservation|hca", ("heritage",)),
    ("flood", r"flood|stormwater|drainage|overland.?flow", ("flood",)),
    ("acid_sulfate", r"acid.?sulfate|acid.?sulphate", ("acid_sulfate",)),
    ("bushfire", r"bush.?fire", ("bushfire",)),
    ("riparian", r"riparian|watercourse|foreshore", ("riparian", "foreshore_building_line")),
    # Deliberately NARROW. An earlier version matched 'vegetation|tree', which
    # claimed ku_ring_gai's "Part 13 Trees" and every other ordinary landscaping
    # chapter -- reporting landscaping as MISSING and biodiversity as held, both
    # wrong, from one over-broad pattern. Biodiversity is a distinct control set
    # (habitat, corridors, threatened species), not a synonym for trees.
    ("biodiversity", r"biodivers|habitat|threatened.?species|wildlife.?corridor",
     ("biodiversity",)),
    ("landslide", r"landslip|landslide|slope.?stab|geotech", ("landslide",)),
]

# council slug -> spatial_overlays.lga_name, for the ones a normalised compare
# cannot reach. The first three are pre-2016 councils merged into Inner West:
# their DCPs are still separate documents but their PROPERTIES are Inner West's,
# so their overlay profile has to come from the merged LGA. Getting this wrong
# silently gives a council an empty hazard profile and marks it complete.
LGA_OVERRIDES = {
    "ashfield": "INNER WEST",
    "leichhardt": "INNER WEST",
    "marrickville": "INNER WEST",
    "inner_west": "INNER WEST",
    "city_of_sydney": "SYDNEY",
    "parramatta": "CITY OF PARRAMATTA",
}
# Not an LGA at all -- statewide instruments. Excluded rather than reported as
# a council with no overlays.
NOT_A_COUNCIL = {"state"}

MIRRORED, HAVE_URL, HAVE_PAGE, NO_URL = (
    "MIRRORED", "NO_PDF_HAVE_URL", "NO_PDF_HAVE_PAGE", "NO_PDF_NO_URL")
# Better states win when several chapters map to the same bucket.
RANK = {"": 0, NO_URL: 1, HAVE_PAGE: 2, HAVE_URL: 3, "NOT_EXTRACTED": 4, "SERVING": 5}


def bucket_for(chapter_key: str, label: str) -> str | None:
    """Which bucket this chapter is, or None when it matches none.

    Hazard patterns are tried FIRST. A chapter called "Flood and Stormwater
    Management" contains neither 'residential' nor 'parking', but woollahra's
    "Stormwater and Flood Risk" would otherwise be claimed by the landscape
    pattern via 'water'. Specific before general.
    """
    text = ((chapter_key or "") + " " + (label or "")).lower()
    for name, pattern, _layers in HAZARD_BUCKETS:
        if re.search(pattern, text):
            return name
    for name, pattern in BUCKETS:
        if re.search(pattern, text):
            return name
    return None


def normalise_lga(name: str) -> str:
    return re.sub(r"[^a-z]", "", str(name or "").lower())


def council_lga(council: str, overlay_lgas: set[str]) -> str | None:
    """The spatial_overlays LGA whose properties this council's DCP governs."""
    if council in NOT_A_COUNCIL:
        return None
    if council in LGA_OVERRIDES:
        return LGA_OVERRIDES[council]
    by_norm = {normalise_lga(l): l for l in overlay_lgas}
    n = normalise_lga(council)
    if n in by_norm:
        return by_norm[n]
    for norm, original in by_norm.items():
        if norm.startswith(n) or n.startswith(norm):
            return original
    return None


def required_buckets(layers_present: set[str]) -> list[str]:
    """The buckets this council must hold: five universal, plus a hazard bucket
    for every overlay its properties actually carry."""
    required = [name for name, _ in BUCKETS]
    for name, _pattern, layers in HAZARD_BUCKETS:
        if layers_present & set(layers):
            required.append(name)
    return required


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
    # Which overlays each LGA's properties actually carry. This is what makes the
    # target per-council instead of a template.
    cur.execute("""SELECT lga_name, layer_type FROM spatial_overlays
                   WHERE lga_name IS NOT NULL GROUP BY 1, 2""")
    lga_layers: dict[str, set[str]] = defaultdict(set)
    for lga, layer in cur.fetchall():
        lga_layers[lga].add(layer)
    conn.close()

    all_names = [n for n, _ in BUCKETS] + [n for n, _, _ in HAZARD_BUCKETS]
    per = defaultdict(lambda: {name: "" for name in all_names})
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

    # The per-council target, derived rather than templated.
    required: dict[str, list[str]] = {}
    lga_of: dict[str, str | None] = {}
    for council in list(per) + [c for c, *_ in registry]:
        if council in required or council in NOT_A_COUNCIL:
            continue
        lga = council_lga(council, set(lga_layers))
        lga_of[council] = lga
        required[council] = required_buckets(lga_layers.get(lga or "", set()))
    return per, blockers, unbucketed, required, lga_of


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("--gaps", action="store_true", help="only the missing work")
    args = ap.parse_args(argv)
    per, blockers, unbucketed, required, lga_of = collect()

    short = {"SERVING": "yes", "NOT_EXTRACTED": "not extr", HAVE_URL: "url only",
             HAVE_PAGE: "page only", NO_URL: "NO URL", "": "-"}
    def score(council):
        req = required.get(council) or [n for n, _ in BUCKETS]
        got = sum(1 for n in req if per[council][n] == "SERVING")
        return got, len(req)

    if not args.gaps:
        cols = [n for n, _ in BUCKETS] + [n for n, _, _ in HAZARD_BUCKETS]
        head = ("  council".ljust(20) +
                "".join(n[:8].rjust(10) for n in cols) + "have".rjust(8))
        print("SCOPE COVERAGE -- five universal chapters plus a hazard chapter for")
        print("every overlay THIS council's properties actually carry.")
        print("A blank cell means that hazard does not apply here; '-' means it")
        print("applies and we hold nothing.")
        print()
        print(head)
        print("  " + "-" * (len(head) - 2))
        for council in sorted(per, key=lambda c: -score(c)[0] / max(score(c)[1], 1)):
            if council in NOT_A_COUNCIL:
                continue
            req = set(required.get(council) or [])
            cells = []
            for n in cols:
                if n not in req:
                    cells.append("".rjust(10))          # not applicable here
                else:
                    cells.append(short[per[council][n]].rjust(10))
            got, need = score(council)
            print("  " + council.ljust(18) + "".join(cells) +
                  (str(got) + "/" + str(need)).rjust(8))
        done = sum(1 for c in per if c not in NOT_A_COUNCIL
                   and score(c)[0] == score(c)[1])
        none = sum(1 for c in per if c not in NOT_A_COUNCIL and score(c)[0] == 0)
        print("  " + "-" * (len(head) - 2))
        print("  councils meeting their OWN target: " + str(done) +
              "    with none: " + str(none) +
              "    total: " + str(len([c for c in per if c not in NOT_A_COUNCIL])))
        print()
        print("  hazard chapters REQUIRED but not held (the gap the fixed six hid):")
        for council in sorted(per):
            req = set(required.get(council) or [])
            miss = [n for n, _, _ in HAZARD_BUCKETS
                    if n in req and per[council][n] != "SERVING"]
            if miss:
                print("   " + council.ljust(20) + ", ".join(miss))

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
