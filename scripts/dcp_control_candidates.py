#!/usr/bin/env python3
# prior-art-checked: neighbours opened, not guessed from their names.
#   dcp_verify_extracted_controls.py  the other half of this pair -- it checks what
#       a model proposes FROM these candidates. Its page-key contract
#       (council, chapter, page) is matched here exactly rather than re-invented.
#   dcp_extract_changed.py            the production extractor. Its _columnar_text
#       and GEOMETRIC_COLUMN_COUNCILS are IMPORTED, not copied: the first run of
#       this harness used a naive extractor and handed the model worse text than
#       production uses, which cost real controls.
#   dcp_chapter_measure.py            measures chapters; does not select passages.
#   ai_extractor.py                   extracts WHOLE CHAPTERS via a model inside the
#       pipeline. This is the opposite shape: one control type, narrow candidates,
#       human-gated, and it needs no council API credit.
# DB sweep: nothing selects candidate passages for a named control type.
"""Narrow a corpus down to the passages that could state ONE numeric control.

WHY NARROW FIRST
----------------
A model handed a 300-page DCP can cite anything. A model handed 60 pages selected
deterministically can only cite those, and the verifier rejects a citation to
anything else. The narrowing is what makes the output checkable, so it happens
here and not in a prompt.

WHICH TOPICS ARE WORTH IT -- MEASURED, WITH THE QUERY
-----------------------------------------------------
Re-measure rather than quote this. A number without its query is how the earlier
version of this table was wrong (see the correction below).

    SELECT v2_topic, count(*),
           count(*) FILTER (WHERE provision_text ~* '\\d+(\\.\\d+)?\\s*(m\\y|mm\\y|metre|m2|sqm|storey)')
    FROM regulatory_provisions WHERE is_current AND v2_topic IS NOT NULL
    GROUP BY 1 ORDER BY 2 DESC;

Share of live provisions carrying a LENGTH or AREA (19,758 rows, 2026-09-12):

    height 52% · setbacks 39% · stormwater 20% · flooding 13%
    heritage 10% · building_form 8%

A CORRECTION THAT CHANGED A DECISION
------------------------------------
An earlier version of this table read "flooding 47%, stormwater 37%" and ranked
flood as the next control type to mine. Measured on 2026-09-12 it is **13% and
20%** -- the same band as heritage, which is excluded.

Two things inflated it. The denominator was the `v2_is_actionable` subset (which
lifts flooding to 22%), and the test counted any number-plus-unit. Most numbers in
flood clauses are **event labels** -- "1% AEP", "1 in 100 year", "20 year ARI" --
which name the event a control is measured against and are not themselves
controls. On the stricter length-or-area test the flooding share falls by a third.

Reading 24 real flood passages confirmed it from the other end: an FPL is a
per-property datum off a flood map (parramatta states "RL 17.0" for one creek),
and most DCP mentions of it are cross-references to a separate floodplain policy
with no number at all. What IS stated LGA-wide is the freeboard, so that is the
control type mined -- see CONTROL_PATTERNS["flood_freeboard_min"].

Heritage remains the trap: the LARGEST topic in the corpus (2,684 live rows) and
among the least numeric. Mining it yields least and costs most, so the exclusion
is enforced here rather than left to whoever writes the next prompt -- and pinned
by tests/test_dcp_control_candidates.py so it cannot be undone silently.

TWO SOURCES
-----------
--from-provisions   text already committed to regulatory_provisions. Better
                    provenance: an accepted quote must appear in the row the
                    product actually serves, not merely somewhere in a PDF.
--from-pdf          R2 pages, for councils whose text is not extracted. Uses the
                    council-aware columnar reader where one applies.

    python scripts/dcp_control_candidates.py --control secondary_street_setback \\
        --councils parramatta,city_of_sydney --from-provisions --out cands.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Topics measured to be numeric-poor. Excluded so a later prompt cannot quietly
# spend a run on them. heritage is the largest topic in the corpus AND among the
# least numeric -- the single worst yield-per-effort trade available.
NUMERIC_POOR_TOPICS = {"heritage", "building_form", "site_analysis", "waste",
                       "environmental", "untagged", "None"}

# Excluded for a DIFFERENT reason, and the distinction matters: precinct clauses
# are often RICH in numbers, and those numbers are correct. They are excluded
# because their SCOPE is wrong -- a precinct control served LGA-wide overrides the
# council's real general answer with a site-specific one. Measured 2026-09-12: two
# accepted hornsby rows came from the Pound Road precinct table and had to be
# re-scoped by hand. Mining precincts needs a precinct key on the row first.
SCOPE_RISK_TOPICS = {"precinct"}

EXCLUDED_TOPICS = NUMERIC_POOR_TOPICS | SCOPE_RISK_TOPICS

# A provision states a measurable requirement when it carries a number AND a unit.
MEASURABLE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:m\b|metre|mm\b|m2|m²|sqm|%|per\s*cent|degree|hour|space|storey)",
    re.I)

# What each control type looks like in the text. The model still decides; this
# only decides what it is allowed to look at.
CONTROL_PATTERNS: dict[str, str] = {
    "secondary_street_setback":
        r"secondary\s+(street|road|frontage|boundary)|corner\s+(lot|site|allotment)",
    "private_open_space":
        r"private\s+open\s+space|\bPOS\b|principal\s+private\s+open",
    "max_height":
        r"(maximum|max\.?)\s+(building\s+)?height|height\s+(limit|control|of\s+buildings)",
    # NOT "flood planning level". Read 24 real candidates on 2026-09-12: an FPL is
    # a per-property datum read off a flood map (parramatta states "RL 17.0" for
    # one creek), and most DCP mentions of it are cross-references to a separate
    # floodplain policy with no number at all. The thing a DCP states LGA-wide,
    # and that a consumer can act on, is the FREEBOARD -- a height above the
    # mapped flood level. So that is what is mined.
    "flood_freeboard_min":
        r"freeboard|(?:minimum|habitable)\s+(?:finished\s+)?floor\s+level",
    "landscaping_min":
        r"landscap(ed|ing)\s+(area|treatment)|soft\s+landscap",
    "deep_soil_min": r"deep\s+soil",
    "site_coverage": r"site\s+coverage|building\s+footprint\s+(area|ratio)",
}
# A setback clause must also say "setback"; a POS clause need not. Only the
# control types where the bare keyword is too loose carry a second requirement.
#
# max_height wants a LENGTH, not merely any number: "the maximum height of any
# sign is 50% of the facade" states no height at all. The requirement is a number
# bound to a height unit, written the way DCPs actually write it.
#
# It was first written `\bm\b|metre|storey`, which cannot match "8.5m" -- the
# commonest notation in the corpus -- because there is no word boundary between
# the digit and the m. It silently suppressed real height candidates and the run
# still returned 97 of them, so the count looked healthy. Only a test asserting
# the most obvious possible case found it.
SECOND_REQUIREMENT: dict[str, str] = {
    "secondary_street_setback": r"setback|building\s+line",
    "max_height": r"\d+(?:\.\d+)?\s*(?:m\b|metre|storey)",
    # A freeboard is a LENGTH above a mapped level. Without this the filter
    # returns every page whose only number is "1% AEP" or "1 in 100 year" -- a
    # flood-event label, which names the event a control is measured against and
    # is not itself a control. Measured across all 19,758 live provisions: the
    # `flooding` topic is 18% "measurable" but only 13% carries a length or an
    # area, and that gap is almost entirely AEP/ARI labels.
    "flood_freeboard_min": r"\d+(?:\.\d+)?\s*(?:mm\b|m\b|metre)",
}


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
    cur.execute("SET statement_timeout='180s'")
    return conn, cur


def wanted(text: str, control: str) -> bool:
    """Could this text state the named control?"""
    if not MEASURABLE.search(text or ""):
        return False
    if not re.search(CONTROL_PATTERNS[control], text, re.I):
        return False
    second = SECOND_REQUIREMENT.get(control)
    return not second or bool(re.search(second, text, re.I))


# How much text to keep either side of a keyword hit, and the hard ceiling on one
# candidate. See window_around() for why a flat head-truncation is not an option.
WINDOW_CHARS = 2000
WIDE_WINDOW_CHARS = 6000
MAX_CANDIDATE_CHARS = 12000
ELISION = "\n\n[... omitted: no mention of this control ...]\n\n"


def _windows(text: str, control: str, width: int) -> str | None:
    spans = [(max(0, m.start() - width), min(len(text), m.end() + width))
             for m in re.finditer(CONTROL_PATTERNS[control], text, re.I)]
    if not spans:
        return None
    merged = [spans[0]]
    for start, end in spans[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    kept, total = [], 0
    for start, end in merged:
        chunk = text[start:min(end, start + MAX_CANDIDATE_CHARS - total)]
        kept.append(chunk)
        total += len(chunk)
        if total >= MAX_CANDIDATE_CHARS:
            break
    return ELISION.join(kept)


def window_around(text: str, control: str) -> str | None:
    """Keep the parts of a long provision that actually mention the control.

    WHY THIS EXISTS -- a measured failure, not a precaution
    -------------------------------------------------------
    The first version capped each candidate at a flat 6000 characters. For
    parramatta and city_of_sydney that silently destroyed the evidence:
    `provision_text` there is not clause-sized (median 2,786 chars, p95 10,590,
    **max 49,322**), and one provision is one candidate -- measured 2026-09-12,
    the maximum number of provisions sharing a (council, chapter, pdf_page) key
    is 1, so nothing is aggregated and the cap fell on single provisions.

    Result: 38 of 100 `deep_soil_min` candidates hit the cap, and **10 arrived
    with no mention of deep soil at all** -- the keyword that made the page a
    candidate had been cut off. Those 10 were noise handed to a model as
    evidence, and any control they held was lost without a word in the log.

    Windowing rather than head-truncating keeps the text AROUND each mention.
    ±2000 characters is roughly 700 words either side, far more than a value and
    its qualifier are ever separated by -- and the elision marker is explicit, so
    a reader can see that something was dropped.

    DIRECTION OF THE REMAINING RISK
    -------------------------------
    The verifier requires an accepted quote to appear in THIS text. Windowing can
    therefore only reject a quote that straddles an elision -- a false negative.
    It cannot let a fabricated one through. That is the safe direction, and it is
    the reason the window is generous rather than tight.
    """
    narrow = _windows(text, control, WINDOW_CHARS)
    if narrow is not None and wanted(narrow, control):
        return narrow
    # The keyword and the evidence are far apart. Widen once before giving up: at
    # more than 6000 characters of separation they are almost certainly not the
    # same rule, and the caller counts what is dropped rather than dropping quietly.
    #
    # The test here is the FULL wanted() predicate, not just "is there a number".
    # Measured 2026-09-12: checking only MEASURABLE let two max_height windows
    # through that kept a number but lost the unit token the control requires
    # ("maximum height ... 50%" satisfies MEASURABLE and states no height). The
    # post-condition in main() caught both. A window must satisfy exactly the
    # test that selected the provision -- anything weaker re-opens the same hole
    # one layer down.
    wide = _windows(text, control, WIDE_WINDOW_CHARS)
    if wide is not None and wanted(wide, control):
        return wide
    return None


def from_provisions(cur, councils, control, log):
    """Candidates from text already committed -- the strongest provenance.

    Provisions sharing a pdf_page are aggregated into one block so the
    (council, chapter, page) key stays unique, which is the contract
    dcp_verify_extracted_controls already expects.
    """
    cur.execute(
        "SELECT source_council, source_chapter_key, pdf_page, section_header, "
        "       provision_text, v2_topic "
        "FROM regulatory_provisions "
        "WHERE is_current AND source_council = ANY(%s) "
        "  AND provision_text IS NOT NULL AND source_chapter_key IS NOT NULL "
        "ORDER BY source_council, source_chapter_key, pdf_page", (councils,))
    grouped: dict[tuple, list[str]] = defaultdict(list)
    skipped_poor = skipped_scope = dropped_far = 0
    for council, chapter, page, header, text, topic in cur.fetchall():
        if str(topic) in NUMERIC_POOR_TOPICS:
            skipped_poor += 1
            continue
        if str(topic) in SCOPE_RISK_TOPICS:
            skipped_scope += 1
            continue
        if not wanted(text, control):
            continue
        kept = window_around(str(text).strip(), control)
        if kept is None:
            dropped_far += 1
            continue
        head = (str(header).strip() + "\n") if header else ""
        grouped[(council, chapter, page or 0)].append(head + kept)
    log("  skipped, topic measured numeric-poor:  " + str(skipped_poor))
    log("  skipped, precinct-scoped (wrong grain): " + str(skipped_scope))
    log("  dropped, number >6000 chars from the keyword: " + str(dropped_far))
    return [{"council": c, "chapter": ch, "page": pg,
             "text": ("\n\n" + ELISION).join(v)}
            for (c, ch, pg), v in sorted(grouped.items())]


def from_pdf(cur, councils, control, log):
    """Candidates from R2 pages, for councils whose text is not extracted."""
    import boto3
    import pdfplumber
    from scripts.dcp_extract_changed import (
        GEOMETRIC_COLUMN_COUNCILS, _columnar_text)

    s3 = boto3.client(
        "s3",
        endpoint_url="https://" + os.environ["R2_ACCOUNT_ID"] + ".r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
    cur.execute(
        "SELECT council, chapter_key, r2_current_path FROM dcp_chapter_registry "
        "WHERE is_active AND r2_current_path IS NOT NULL AND NOT is_spatial "
        "  AND NOT is_inert AND council = ANY(%s) ORDER BY council, chapter_key",
        (councils,))
    chapters = cur.fetchall()
    log("  chapters to scan: " + str(len(chapters)))
    out = []
    for council, chapter, path in chapters:
        columnar = council in GEOMETRIC_COLUMN_COUNCILS
        try:
            with tempfile.TemporaryDirectory() as td:
                local = os.path.join(td, "c.pdf")
                s3.download_file(os.environ["R2_BUCKET_NAME"], path, local)
                with pdfplumber.open(local) as pdf:
                    for pno, page in enumerate(pdf.pages, 1):
                        # The council-aware reader where one applies. Skipping
                        # this cost real controls on the first run.
                        text = (_columnar_text(page) if columnar else None)
                        if text is None:
                            text = page.extract_text() or ""
                        if wanted(text, control):
                            # A real PDF page is a few thousand characters, so
                            # this keeps it WHOLE -- which is what you want: a
                            # value and the condition it depends on are routinely
                            # several lines apart. Only the provisions path needs
                            # windowing, because a "provision" there can be 49k.
                            out.append({"council": council, "chapter": chapter,
                                        "page": pno,
                                        "text": text[:MAX_CANDIDATE_CHARS]})
        except Exception as exc:
            log("  ERROR " + council + "/" + chapter[:26] + ": " + str(exc)[:60])
    return out


def broken_candidates(found: list[dict], control: str) -> list[dict]:
    """Candidates that no longer pass the test that selected them.

    THE POST-CONDITION. This is the guard that would have caught the truncation
    bug of 2026-09-12, where 10 of 100 `deep_soil_min` candidates reached the
    model with the keyword cut off -- noise presented as evidence, and any control
    they held lost without a line in the log.

    It has fired on real data since: two `max_height` windows kept a number but
    lost the unit token the control requires, because the windowing step was
    testing "is there a number" instead of the full predicate. Silence from this
    function only means something because it has been shown to speak.
    """
    return [f for f in found if not wanted(f["text"], control)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("--control", required=True, choices=sorted(CONTROL_PATTERNS))
    ap.add_argument("--councils", required=True, help="comma-separated slugs")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--from-provisions", action="store_true")
    src.add_argument("--from-pdf", action="store_true")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    councils = [c.strip() for c in args.councils.split(",") if c.strip()]

    def log(s):
        print(s, flush=True)

    log("control: " + args.control)
    log("councils: " + ", ".join(councils))
    conn, cur = _connect()
    found = (from_provisions(cur, councils, args.control, log) if args.from_provisions
             else from_pdf(cur, councils, args.control, log))
    conn.close()

    broken = broken_candidates(found, args.control)
    if broken:
        for f in broken[:5]:
            log("  BROKEN CANDIDATE " + f["council"] + "/" + f["chapter"] +
                " p" + str(f["page"]) + " no longer matches after assembly")
        raise SystemExit("FATAL: " + str(len(broken)) + " of " + str(len(found)) +
                         " candidates do not satisfy the filter that selected "
                         "them. Refusing to write a candidate file a model would "
                         "read as evidence.")

    per = defaultdict(int)
    for f in found:
        per[f["council"]] += 1
    log("")
    for c in councils:
        log("  " + c.ljust(22) + str(per.get(c, 0)) + " candidate passages")
    log("  " + "-" * 40)
    log("  " + "TOTAL".ljust(22) + str(len(found)))
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(found, fh, indent=1)
    log("")
    log("wrote " + args.out)
    log("Next: a model proposes rows from THESE PAGES ONLY, then")
    log("  python scripts/dcp_verify_extracted_controls.py <proposals> --pages " +
        args.out)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print("FATAL: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        sys.exit(1)
