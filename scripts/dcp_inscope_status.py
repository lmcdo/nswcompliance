#!/usr/bin/env python3
# prior-art-checked: read-only report, no writes, no new table. Neighbours opened:
#   dcp_chapter_measure.py   MEASURES chapters against their source PDFs and writes
#                            the ledger. This READS that ledger and narrows it to
#                            what the app actually serves; it measures nothing new.
#   dcp_quality_report.py    renders current provision state, persists nothing, and
#                            has no notion of the council configs' scope keys.
#   check_council_completeness.py   per-council field fill counts; no chapter or
#                            part grain at all.
#   frontend-nextjs/lib/council-configs/*.json + loader.ts  the scope source read
#                            here. Not duplicated -- parsed.
# DB sweep: nothing joins the measurement ledger to the app's scope config.
"""Chapter status, narrowed to the parts the app is actually built to serve.

WHY THIS EXISTS
---------------
A corpus-wide count treats a definitions appendix, a precinct map and the parking
controls as equals. They are not. `docs/DCP_SCOPE_CONFIG_REFERENCE.md` and each
`council-configs/<council>.json` already record which parts must reach the
planner -- universalPartKeys (always shown) and devTypeGatedPartKeys (shown when
the development type matches). Those are the parts a user's answer depends on.

Scoring the whole registry instead of those produced a status report where 46
chapters looked "empty" when 23 were marked inert and 14 were maps: empty was
the CORRECT state for 37 of them. This narrows to what matters and says plainly
what it could not classify.

THREE WAYS A CHAPTER REACHES A USER, NOT ONE
--------------------------------------------
The config arrays are only part of the story, and treating them as the whole of
it under-reports coverage badly. DCP_SCOPE_CONFIG_REFERENCE is explicit:

    "Precinct / heritage parts -- handled by the for-property API layer system
     (v2_dcp_layer = condition / precinct). Do not put them in either array --
     they self-gate via property attributes."

So a chapter absent from both arrays may still be served, gated by the property
rather than by the development type. A first pass here called 97 chapters
"unmapped", including ashfield's precinct guidelines (641 rules, layer=precinct)
and its heritage chapter (layer=condition) -- both of which the app serves. That
was the report being wrong in the same direction as the one it replaced.

Tiers now, from the config arrays plus v2_dcp_layer on the rows themselves:

  ALWAYS      universalPartKeys -- every user of that council sees it
  DEV-GATED   devTypeGatedPartKeys -- shown when the development type matches
  PROPERTY    v2_dcp_layer precinct / condition / use_specific -- self-gating
  UNDECLARED  serves 'generic' rules but appears in no array and no gating layer.
              NOT a silent drop: this is a finding. A chapter serving
              always-applicable rules that nothing declares in scope is either a
              config gap or a mislabelled layer, and it is printed by name.

WHAT IT WILL NOT DO
-------------------
Guess. Three honesty rules, because a scope report that quietly drops what it
cannot map is worse than no report:

  * a council with NO config is reported as UNSCOPED, never assumed in-scope.
    12 of 19 councils have no config.
  * a chapter whose part cannot be derived is reported as UNMAPPED and counted,
    never silently dropped. The per-council mapping rate is printed every run.
  * waverley is excluded from the per-chapter view and reported separately. Its
    config keys are PARTS INSIDE the single waverley-dcp-2022 chapter (the B, C
    and D part series), so a chapter-level join would be meaningless.

WHY chapter_key AND NOT v2_dcp_part
-----------------------------------
v2_dcp_part is 'unknown' for all of leichhardt and marrickville, prose in
ashfield and slugs in ku-ring-gai -- it is not a usable cross-council key.
chapter_key encodes the part reliably, in a different convention per council,
which is why the normaliser below is per-council and its hit rate is measured.

    python scripts/dcp_inscope_status.py
    python scripts/dcp_inscope_status.py --council marrickville --list
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

CONFIG_DIR = os.path.join(_ROOT, "frontend-nextjs", "lib", "council-configs")

# Councils whose config keys are parts WITHIN one chapter rather than chapters.
# Listed explicitly so they are excluded loudly instead of scoring as 0% mapped.
ROW_LEVEL_COUNCILS = {"waverley"}


def load_scope() -> dict[str, dict]:
    """{council: {'universal': [...], 'gated': [...]}} from the app's own configs."""
    out = {}
    for path in sorted(glob.glob(os.path.join(CONFIG_DIR, "*.json"))):
        name = os.path.basename(path)[:-5]
        if name.startswith("_"):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                cfg = json.load(fh)
        except (OSError, ValueError):
            continue
        out[name] = {"universal": cfg.get("universalPartKeys") or [],
                     "gated": cfg.get("devTypeGatedPartKeys") or []}
    return out


def _norm(s: str) -> str:
    """Lowercase, strip every separator. 'Part 1' / 'part1' / 'part_1' all match."""
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def chapter_part(council: str, chapter_key: str, scope_keys: list[str]) -> str | None:
    """Which configured part key this chapter belongs to, or None if undecidable.

    Matching is on the NORMALISED key as a prefix of the normalised chapter_key,
    longest first so 'part4_1_secondary' wins over 'part4'. The longest-first rule
    is not cosmetic: ku_ring_gai has both part_4_dwelling_houses and
    part_4_1_secondary_dwellings, and shortest-first would file the second under
    the first and report a chapter as in-scope that the app gates differently.
    """
    ck = _norm(chapter_key)
    best = None
    for key in sorted(scope_keys, key=lambda k: -len(_norm(k))):
        nk = _norm(key)
        if not nk:
            continue
        # 'chaptera' must match 'chapteramiscellaneous' but NOT 'chapterb...'.
        if ck.startswith(nk) or nk in ck:
            if best is None or len(nk) > len(_norm(best)):
                best = key
    return best


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


def classify(row) -> str:
    """One word for what is wrong with this chapter, or GOOD."""
    (_c, _k, measured, contents, header, attribution, live_rows, _missing) = row
    if (live_rows or 0) == 0:
        return "NOTHING"
    if attribution == "COLLAPSED" or header == "MISLABELLED":
        return "FILED_WRONG"
    if contents == "INCOMPLETE":
        return "PARTIAL"
    if contents == "OK":
        return "GOOD"
    return "UNVERIFIED"


ORDER = ["GOOD", "PARTIAL", "FILED_WRONG", "UNVERIFIED", "NOTHING"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--council")
    ap.add_argument("--list", action="store_true",
                    help="name every in-scope chapter and its state")
    args = ap.parse_args(argv)

    scope = load_scope()
    conn, cur = _connect()
    cur.execute("""
        WITH latest AS (
          SELECT DISTINCT ON (council, chapter_key) *
          FROM dcp_chapter_measurement
          ORDER BY council, chapter_key, measured_at DESC)
        SELECT l.council, l.chapter_key, l.measured, l.contents_verdict,
               l.header_verdict, l.attribution_verdict, l.live_rows, l.missing_codes
        FROM latest l
        JOIN dcp_chapter_registry r
          ON r.council = l.council AND r.chapter_key = l.chapter_key
        WHERE NOT r.is_inert AND NOT r.is_spatial""")
    rows = cur.fetchall()
    # The gating layer each chapter's rows actually carry. A chapter is
    # property-gated when most of its rules are.
    cur.execute("""SELECT source_council, source_chapter_key, v2_dcp_layer, count(*)
                   FROM regulatory_provisions
                   WHERE is_current AND source_chapter_key IS NOT NULL
                   GROUP BY 1, 2, 3""")
    layers: dict[tuple, dict] = defaultdict(dict)
    for council, chapter, layer, n in cur.fetchall():
        layers[(council, chapter)][layer] = n
    conn.close()

    def gating_layer(council, chapter):
        counts = layers.get((council, chapter)) or {}
        if not counts:
            return None
        return max(counts, key=counts.get)

    per = defaultdict(lambda: defaultdict(int))
    listing = defaultdict(list)
    unmapped = defaultdict(list)
    for row in rows:
        council, chapter = row[0], row[1]
        if args.council and council != args.council:
            continue
        if council in ROW_LEVEL_COUNCILS or council not in scope:
            continue
        keys = scope[council]["universal"] + scope[council]["gated"]
        part = chapter_part(council, chapter, keys)
        p = per[council]
        p["measured_chapters"] += 1
        layer = gating_layer(council, chapter)
        if part is not None:
            tier = "ALWAYS" if part in scope[council]["universal"] else "DEV-GATED"
        elif layer in ("precinct", "condition", "use_specific"):
            tier = "PROPERTY"
        else:
            # Serves generic rules but nothing declares it in scope. Reported by
            # name rather than dropped -- it is a config gap or a bad layer.
            p["undeclared"] += 1
            unmapped[council].append(chapter + " (" + str(layer) + ", " +
                                     str(row[6] or 0) + " rules)")
            continue
        state = classify(row)
        p["in_scope"] += 1
        p[state] += 1
        p["rules"] += row[6] or 0
        p["missing"] += row[7] or 0
        p["tier_" + tier] += 1
        if tier == "ALWAYS":
            p["universal"] += 1
            if state == "GOOD":
                p["universal_good"] += 1
        listing[council].append((part, tier, chapter, state, row[6], row[7]))

    print("IN-SCOPE CHAPTER STATUS -- only the parts each council's config says")
    print("must reach the planner (universalPartKeys + devTypeGatedPartKeys).")
    print()
    head = ("  council".ljust(22) + "in scope".rjust(9) + "rules".rjust(7) +
            "GOOD".rjust(6) + "partial".rjust(8) + "filed wrong".rjust(12) +
            "unverified".rjust(11) + "nothing".rjust(8) + "undeclared".rjust(11))
    print(head)
    print("  " + "-" * (len(head) - 2))
    tot = defaultdict(int)
    for council in sorted(per, key=lambda c: -per[c]["rules"]):
        p = per[council]
        print("  " + council.ljust(20) + str(p["in_scope"]).rjust(9) +
              str(p["rules"]).rjust(7) + str(p["GOOD"]).rjust(6) +
              str(p["PARTIAL"]).rjust(8) + str(p["FILED_WRONG"]).rjust(12) +
              str(p["UNVERIFIED"]).rjust(11) + str(p["NOTHING"]).rjust(8) +
              str(p["undeclared"]).rjust(11))
        for k, v in p.items():
            tot[k] += v
    print("  " + "-" * (len(head) - 2))
    print("  " + "TOTAL".ljust(20) + str(tot["in_scope"]).rjust(9) +
          str(tot["rules"]).rjust(7) + str(tot["GOOD"]).rjust(6) +
          str(tot["PARTIAL"]).rjust(8) + str(tot["FILED_WRONG"]).rjust(12) +
          str(tot["UNVERIFIED"]).rjust(11) + str(tot["NOTHING"]).rjust(8) +
          str(tot["undeclared"]).rjust(11))

    print()
    print("  how in-scope chapters are reached:")
    for council in sorted(per, key=lambda c: -per[c]["in_scope"]):
        p = per[council]
        print("   " + council.ljust(20) +
              "always " + str(p["tier_ALWAYS"]).rjust(3) +
              "   dev-gated " + str(p["tier_DEV-GATED"]).rjust(3) +
              "   property-gated " + str(p["tier_PROPERTY"]).rjust(3))
    print()
    print("  ALWAYS-SHOWN parts only (universalPartKeys) -- what every user hits:")
    for council in sorted(per, key=lambda c: -per[c]["universal"]):
        p = per[council]
        if not p["universal"]:
            continue
        print("   " + council.ljust(20) + str(p["universal_good"]).rjust(3) +
              " of " + str(p["universal"]).rjust(3) + " verified good")

    if unmapped:
        print()
        print("  UNDECLARED -- serves always-applicable rules, but no config array")
        print("  and no gating layer claims it. A config gap or a mislabelled layer:")
        for council, chs in sorted(unmapped.items()):
            print("   " + council.ljust(20) + str(len(chs)))
            for ch in chs[:4]:
                print("        " + ch)

    missing_cfg = sorted({r[0] for r in rows} - set(scope) - ROW_LEVEL_COUNCILS)
    if missing_cfg:
        print()
        print("  UNSCOPED -- no council config exists, so nothing here says which")
        print("  of their chapters the app is meant to serve:")
        print("   " + ", ".join(missing_cfg))
    if ROW_LEVEL_COUNCILS & {r[0] for r in rows}:
        print()
        print("  REPORTED SEPARATELY: " + ", ".join(sorted(ROW_LEVEL_COUNCILS)) +
              " -- its config keys are parts INSIDE one chapter, so a")
        print("  chapter-level join would be meaningless.")

    if args.list:
        print()
        for council in sorted(listing):
            print("  " + council)
            for part, tier, chapter, state, rules, miss in sorted(listing[council]):
                flag = "" if state == "GOOD" else "   <<<"
                print("     " + str(part)[:26].ljust(28) + tier.ljust(11) +
                      chapter[:34].ljust(36) + state.ljust(12) +
                      str(rules or 0).rjust(5) + " rules" +
                      ("  -" + str(miss) + " sections" if miss else "") + flag)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print("FATAL: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        sys.exit(1)
