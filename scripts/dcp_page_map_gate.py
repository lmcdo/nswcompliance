#!/usr/bin/env python3
# prior-art-checked: nothing checks a hardcoded page map against the document it is
# applied to. Neighbours opened, not guessed from their names:
#   dcp_extract_changed.py    DEFINES both maps (COUNCIL_PAGE_RANGES,
#                             COUNCIL_CHAPTER_RANGES) and applies them at line
#                             ~3283 without validating either. This module is
#                             imported there rather than duplicated.
#   validate_dcp_health.py    absolute invariants over stored rows; never opens a
#                             PDF, so it cannot see a range pointing past its end.
#   ai_extractor.coverage_gap the completeness guard. Blind to mislabelling by
#                             construction: waverley B15 is coded correctly and
#                             holds B17's text, and a code-presence check calls
#                             that present.
#   r2_monitor.py             detects that a PDF CHANGED. Nothing then re-checks
#                             the page map that describes it -- which is exactly
#                             how this defect survived a version bump.
#   survey_dcp.py             RECOMMENDS adding a page map when SECTION_RE hit
#                             rate is low. It creates these maps; it never
#                             re-validates one.
# Frontend sweep (app/**, app/internal, components/, hooks/): no page-map surface.
"""Three checks that would have caught Waverley the day its PDF changed.

WHAT WENT WRONG
---------------
``COUNCIL_PAGE_RANGES['waverley']`` describes a 473-page document. The PDF in R2
is 448 pages (v1.1-2026-03-16). Measured 2026-09-12:

  * F1-F5 map to pages 460-473. **They extract nothing.** That alone is 5 of the
    11 absent parts, and it is detectable with arithmetic.
  * The map has drifted away from the document, and the drift GROWS through it:
    B1 off by 0, B2-B5 by -1, B6-B7 by -10, B8-B17 by -12, C1 by -19, C2-D1 by  # noqa: zone-codes  (DCP Part codes, not NSW zone codes)
    -20, E1-E6 by -2, F1-F4 by -42. **30 of 33 ranges start on the wrong page**,
    and on **14 of 33** the pages are mostly another part's outright.
    (The plan records "22 of 33 map to the wrong pages". That number could not be
    reproduced here by either the narrow ^[A-F][0-9]{1,2}$ header regex the original
    probe used or the wider one below -- both give 14 majority-wrong and 30
    start-shifted. 22 appears to be a third count from an earlier iteration. The
    finding is unchanged and if anything worse; only the figure differs, and
    these two are the ones this file measures.)
  * B9-B13's ranges land on B14's pages, so B14 signage text is stored under
    "B9 Safety", "B10 Public Art", "B11 Design Excellence". The sub-section
    numbers (14.2.4) are right because they are read from the text; only the part
    label is invented by the map.
  * 54 of 263 checkable rows carry a part that contradicts their own page header.

Nothing tied the map to the document it describes, so a version bump silently
invalidated it. This is what .claude/rules/regulatory-data.md forbids: "a
hardcoded table is wrong within months."

THE MAP IS NOT ONE MAP
----------------------
The repair plan records ``COUNCIL_PAGE_RANGES['waverley']`` as "the only such map
in the codebase". Measured 2026-09-12: there are **32**. COUNCIL_CHAPTER_RANGES
holds 31 more, keyed by (council, chapter_key) -- ashfield 7, ku_ring_gai 24.
Every one carries the same defect class, so all three checks run over all 32.

That measurement also decided how hard check 1 could bite. Across all 32 maps,
exactly **two** point past the end of their own PDF:

  waverley                                      F1-F5   460-473 of 448 pages
  ku_ring_gai/section-a-part-9-non-residential  9c_16    34-35  of  34 pages

So check 1 can fail CLOSED today at a cost of two chapters -- both genuinely
broken -- rather than taking the corpus dark. It is the one check here that
blocks. (ku_ring_gai 9c_16 was not previously recorded anywhere; it is a new
finding from this sweep, and it means half of 9c_16's range extracts nothing.)

WHY THE OTHER TWO DO NOT BLOCK YET
----------------------------------
Checks 2 and 3 need the running header the page carries, and that header is only
readable on some councils. Where it is not, they return NO_HEADER_TRUTH -- which
is not a pass. Where it IS readable they are ratcheted against a committed
baseline, so a map that drifts further fails while the 14 already-wrong waverley
ranges do not re-fail every run. Freezing today's counts is what lets a
fail-closed check go live at all; the alternative is switching it on against
known-bad data and taking the product down.

FAIL CLOSED
-----------
Every check returns UNKNOWN rather than PASS when it cannot run, and UNKNOWN is
never folded into PASS. That is the single most important property here: the
check this replaces (``coverage_gap``) reported "all present" every time it
failed to read the document, for two and a half months.

USAGE
-----
    python scripts/dcp_page_map_gate.py --check          # all 32 maps, ratcheted
    python scripts/dcp_page_map_gate.py --check --council waverley
    python scripts/dcp_page_map_gate.py --check --record-baseline

Exit codes:
    0 = nothing worse than the committed baseline
    2 = a violation beyond the baseline -- the run itself succeeded
    1 = the check itself broke
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

BASELINE_PATH = os.path.join(_ROOT, ".claude", "dcp_page_map_baseline.json")

# A running header that is a bare part code on its own line: B15, C2, 14A, 9c.
PART_HEADER = re.compile(r"^([A-Z]{1,2}\d{1,2}[A-Za-z]?|\d{1,2}[A-Za-z])$")
HEADER_SCAN_LINES = 3
# Below this share of pages carrying a code there is no truth to compare against.
HEADER_MIN_PAGE_COVERAGE = 0.50
# A range this short cannot outvote its own noise.
RANGE_MIN_PAGES_FOR_VOTE = 1

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"


# ── check 1: no range may point past the end of the PDF ──────────────────────
def check_ranges_within_pdf(ranges, pdf_pages: int | None) -> dict:
    """Arithmetic. The only check here that can block, because it cannot be wrong.

    A range whose pages do not exist extracts nothing, every time, for as long as
    the map says so. There is no vocabulary question and no header to read.
    """
    if not pdf_pages or pdf_pages < 1:
        return {"status": UNKNOWN, "reason": "pdf page count unknown",
                "violations": []}
    bad = [{"code": c, "start": a, "end": b, "pdf_pages": pdf_pages}
           for c, _t, a, b in ranges if a > pdf_pages or b > pdf_pages]
    return {"status": FAIL if bad else PASS, "violations": bad,
            "n_ranges": len(ranges)}


# ── check 2: a range's pages must carry that part's running header ───────────
def page_part_codes(page_texts: list[str]) -> dict[int, str]:
    """{1-indexed page -> part code from its running header}, where one exists."""
    out: dict[int, str] = {}
    for i, txt in enumerate(page_texts):
        for line in (txt or "").split("\n")[:HEADER_SCAN_LINES]:
            m = PART_HEADER.match(line.strip())
            if m:
                out[i + 1] = m.group(1)
                break
    return out


# ── derivation: part boundaries from the pages themselves ────────────────────
def derive_ranges_from_headers(page_texts: list[str]) -> list[tuple[str, str, int, int]]:
    """Part page ranges read off each page's own running header, not a hardcoded map.

    WHY. Waverley's hardcoded map described a 473-page version of what is now a
    448-page document: 22 of 33 parts sat on the wrong pages and F1-F5 pointed past
    the end, so parts were missing or filed under the wrong code for months. A map
    typed in once cannot notice the document changing. The page header can.

    RULES, each measured on the waverley PDF on 2026-09-13 before it was written:
      * A header is PART_HEADER on its own line within the first HEADER_SCAN_LINES
        lines -- the SAME reading page_part_codes does, so the gate and the ranges
        cannot disagree about what a header is. A contents line such as
        "B1 Waste 4" is not a header, which is what keeps contents pages out.
      * A run is the pages from a code's first header to its last. A page with no
        header BETWEEN two pages of the same code belongs to that part (a
        figure-only page). A page with no header AFTER a part is not carried
        forward: every header-less run in waverley is annexures, a contents page
        or the definitions, and carrying the last code forward would have filed
        the Bondi Junction, Beachfront and village-centre annexures under the
        last site-specific part printed before them.
      * A code that reappears after a DIFFERENT part has begun means the header is
        not a part marker in this document. Nothing is guessed: the result is [].
      * Fewer than HEADER_MIN_PAGE_COVERAGE of pages carrying a header also gives [].
      * The title is the first non-blank line after the code line on the run's
        first page.

    [] means "cannot derive". The caller must refuse the chapter, never fall back to
    a hardcoded map -- a stale map is exactly what this replaces.

    KNOWN LIMIT: a part that begins mid-page under the previous part's header
    (waverley F5 Horticulture, inside page 431 under F4) is not separated from it.
    Page ranges cannot split a page; that text is extracted under the earlier part.
    """
    heads: dict[int, tuple[str, str]] = {}
    for i, txt in enumerate(page_texts, start=1):
        raw = (txt or "").split("\n")
        for j, line in enumerate(raw[:HEADER_SCAN_LINES]):
            m = PART_HEADER.match(line.strip())
            if m:
                title = next((l.strip() for l in raw[j + 1:j + 3] if l.strip()), "")
                heads[i] = (m.group(1), title)
                break
    if not page_texts or len(heads) / len(page_texts) < HEADER_MIN_PAGE_COVERAGE:
        return []

    ranges: list[list] = []
    finished: set[str] = set()
    for page in sorted(heads):
        code, title = heads[page]
        if ranges and ranges[-1][0] == code:
            ranges[-1][3] = page
            continue
        if code in finished:
            return []
        if ranges:
            finished.add(ranges[-1][0])
        ranges.append([code, title, page, page])
    # A part missing from INSIDE a numbered run (a 9 and an 11 with no 10) means that
    # part's pages carried no header. Coverage can stay above the floor while one small
    # part vanishes, so refuse rather than extract without it (cross-review, 2026-09-13).
    # A missing LAST part of a letter cannot be seen this way; see KNOWN LIMIT above.
    numbers_by_letter: dict[str, list[int]] = {}
    for code, _title, _start, _end in ranges:
        m = re.match(r"^([A-Z]{1,2})(\d{1,2})$", code)
        if m:
            numbers_by_letter.setdefault(m.group(1), []).append(int(m.group(2)))
    for numbers in numbers_by_letter.values():
        if sorted(numbers) != list(range(min(numbers), max(numbers) + 1)):
            return []
    return [(c, t, a, b) for c, t, a, b in ranges]


def check_ranges_match_headers(ranges, page_part: dict[int, str],
                               pdf_pages: int | None) -> dict:
    """Does each range sit on pages that say they belong to that part?

    Returns UNKNOWN when too few pages carry a header to judge -- never PASS.

    TWO MEASURES, REPORTED SEPARATELY
    ---------------------------------
    Measured on waverley 2026-09-12, these do not agree, and conflating them is
    how the repair plan came to record "22 of 33" -- a number neither measure
    produces:

      violations (14 of 33)   the MAJORITY code on a range's pages is a different
                              part. Coarse, and the one that is ratcheted: it
                              means the range is sitting on another part's
                              content outright.
      start_shifts (30 of 33) the range's first page is not where that part
                              actually begins. Far more sensitive -- a range can
                              be shifted several pages and still hold a majority
                              of its own part's pages, while silently swallowing
                              a neighbour's opening pages and dropping its own.

    A range is judged by MAJORITY so one stray header does not condemn a correct
    range. start_shifts is reported and not gated, because a one-page shift is a
    real but minor defect and gating on it would make the ratchet fire constantly
    on documents that are merely imperfectly mapped.
    """
    coverage = (len(page_part) / pdf_pages) if pdf_pages else 0.0
    if coverage < HEADER_MIN_PAGE_COVERAGE:
        return {"status": UNKNOWN,
                "reason": "only " + str(round(coverage * 100)) +
                          "% of pages carry a part header",
                "page_coverage": round(coverage, 3), "violations": [],
                "start_shifts": []}

    # Where each part ACTUALLY begins, per the pages themselves.
    real_start: dict[str, int] = {}
    for page in sorted(page_part):
        real_start.setdefault(page_part[page], page)

    bad, shifts = [], []
    for code, _title, a, b in ranges:
        seen = Counter(page_part[p] for p in range(a, b + 1) if p in page_part)
        if sum(seen.values()) >= RANGE_MIN_PAGES_FOR_VOTE:
            top, _n = seen.most_common(1)[0]
            if top != code:
                bad.append({"code": code, "start": a, "end": b, "pages_say": top,
                            "tally": dict(seen.most_common(3))})
        actual = real_start.get(code)
        if actual is not None and actual != a:
            shifts.append({"code": code, "config_start": a,
                           "real_start": actual, "shift": actual - a})
    return {"status": FAIL if bad else PASS, "violations": bad,
            "start_shifts": shifts, "page_coverage": round(coverage, 3),
            "n_ranges": len(ranges)}


# ── check 3: every stored row's part must match its source page's header ─────
LEAD_CODE = re.compile(r"^([A-Z]{1,2}\d{1,2}[A-Za-z]?)\b")
HEADER_MIN_ROWS = 10
# At or above this share disagreeing, the two sides speak different vocabularies.
# The trap this guards: "C5" in "E2.2.4 C5 Control 5" is Control 5, not part C5 --
# reading those as parts once produced a false "woollahra is 95% broken".
ROW_VOCAB_MISMATCH = 0.90


def check_rows_match_page_headers(rows, page_part: dict[int, str],
                                  pdf_pages: int | None) -> dict:
    """rows is [(pdf_page, section_header), ...]. The only check that sees
    MISLABELLED content: waverley B15 is coded correctly and holds B17's text."""
    coverage = (len(page_part) / pdf_pages) if pdf_pages else 0.0
    if coverage < HEADER_MIN_PAGE_COVERAGE:
        return {"status": UNKNOWN,
                "reason": "only " + str(round(coverage * 100)) +
                          "% of pages carry a part header",
                "rows_checked": 0, "rows_disagree": 0, "examples": []}
    agree = disagree = 0
    examples = []
    for pg, head in rows:
        if not head:
            continue
        m = LEAD_CODE.match(str(head).strip())
        if not m:
            continue
        truth = page_part.get(pg)
        if truth is None:
            continue
        if truth == m.group(1):
            agree += 1
        else:
            disagree += 1
            if len(examples) < 8:
                examples.append({"page": pg, "stored": m.group(1),
                                 "page_says": truth, "header": str(head)[:60]})
    checked = agree + disagree
    if checked < HEADER_MIN_ROWS:
        return {"status": UNKNOWN, "reason": "only " + str(checked) +
                " rows could be checked", "rows_checked": checked,
                "rows_disagree": disagree, "examples": examples}
    if disagree / checked >= ROW_VOCAB_MISMATCH:
        return {"status": UNKNOWN, "reason": "vocabulary mismatch (" +
                str(disagree) + "/" + str(checked) + " disagree) -- the stored "
                "codes and the page headers are not the same kind of code",
                "rows_checked": checked, "rows_disagree": disagree,
                "examples": examples}
    return {"status": FAIL if disagree else PASS, "rows_checked": checked,
            "rows_disagree": disagree, "examples": examples}


# ── the fail-closed hook the extractor calls ─────────────────────────────────
class PageMapUnusable(Exception):
    """A hardcoded page map does not fit the PDF it is about to be applied to."""


def assert_map_usable(council: str, chapter_key: str | None, ranges,
                      pdf_pages: int | None) -> None:
    """Raise before a stale map is used. Called by dcp_extract_changed.

    ONLY check 1 blocks. It is arithmetic -- a range past the end of the document
    extracts nothing, with no vocabulary question and no header to read -- and it
    fires on exactly 2 of the 32 maps today, both genuinely broken. Checks 2 and 3
    need a running header that only some councils carry, so they are reported by
    --check and ratcheted, never raised here.

    A map whose PDF page count is unknown is NOT waved through: pdf_pages is
    always known at the call site (the extractor has the PDF open), so None means
    something upstream changed, and that is a stop, not a pass.
    """
    res = check_ranges_within_pdf(ranges, pdf_pages)
    if res["status"] == UNKNOWN:
        raise PageMapUnusable(
            council + "/" + str(chapter_key) + ": page map cannot be validated "
            "(" + str(res.get("reason")) + "). Refusing to apply it -- an "
            "unvalidated map is how waverley lost 11 parts.")
    if res["status"] == FAIL:
        v = res["violations"]
        detail = ", ".join(x["code"] + " " + str(x["start"]) + "-" + str(x["end"])
                           for x in v[:6])
        raise PageMapUnusable(
            council + "/" + str(chapter_key) + ": " + str(len(v)) + " of " +
            str(res["n_ranges"]) + " page ranges point past the end of a " +
            str(pdf_pages) + "-page PDF (" + detail + "). These extract NOTHING. "
            "The map describes a different version of this document; fix the map "
            "or derive parts from the running header.")


# ── sweep ────────────────────────────────────────────────────────────────────
def _load_env() -> None:
    """prior-art-checked: delegates to check_council_completeness._load_env for the
    same reason scripts/dcp_chapter_measure.py does -- it resolves .env from inside
    a worktree, strips GIT_DIR/GIT_INDEX_FILE so a hook cannot redirect the lookup,
    and ships in Dockerfile.monitors (line 61). dq_db.main_checkout() is the other
    candidate and is NOT in that image."""
    try:
        from scripts.check_council_completeness import _load_env as shared
    except ImportError:
        try:
            from check_council_completeness import _load_env as shared
        except ImportError:
            from dotenv import load_dotenv
            load_dotenv(os.path.join(_ROOT, ".env"))
            return
    shared()


def all_page_maps():
    """Every hardcoded page map in the codebase, as (council, chapter_key, ranges).

    chapter_key is None for a council-level map, which applies to that council's
    whole-DCP chapter.
    """
    from scripts.dcp_extract_changed import (
        COUNCIL_CHAPTER_RANGES, COUNCIL_PAGE_RANGES)
    out = [(council, None, ranges) for council, ranges in COUNCIL_PAGE_RANGES.items()]
    out += [(council, chapter, ranges)
            for (council, chapter), ranges in COUNCIL_CHAPTER_RANGES.items()]
    return out


def sweep(only_council: str | None, log):
    import boto3
    import pdfplumber
    import psycopg2

    _load_env()
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise SystemExit("FATAL: no DATABASE_URL / SUPABASE_DB_URL")
    conn = psycopg2.connect(url, connect_timeout=20)
    cur = conn.cursor()
    cur.execute("SET statement_timeout='120s'")
    endpoint = "https://" + os.environ["R2_ACCOUNT_ID"] + ".r2.cloudflarestorage.com"
    s3 = boto3.client("s3", endpoint_url=endpoint,
                      aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                      aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
                      region_name="auto")
    bucket = os.environ["R2_BUCKET_NAME"]

    cur.execute("SELECT council, chapter_key, r2_current_path FROM dcp_chapter_registry "
                "WHERE is_active AND r2_current_path IS NOT NULL")
    paths = {(c, k): p for c, k, p in cur.fetchall()}
    cur.execute("SELECT source_council, source_chapter_key, pdf_page, section_header "
                "FROM regulatory_provisions WHERE is_current AND pdf_page IS NOT NULL")
    rows_by: dict[tuple, list] = {}
    for c, k, pg, head in cur.fetchall():
        rows_by.setdefault((c, k), []).append((pg, head))

    results = []
    maps = all_page_maps()
    if only_council:
        maps = [m for m in maps if m[0] == only_council]
    log("hardcoded page maps to check: " + str(len(maps)))

    for council, chapter_key, ranges in maps:
        key = (council, chapter_key)
        if chapter_key is None:
            cands = [k for k in paths if k[0] == council]
            key = cands[0] if len(cands) == 1 else None
            if key is None:
                cur.execute(
                    "SELECT council, chapter_key FROM dcp_chapter_registry "
                    "WHERE council=%s AND is_active AND r2_current_path IS NOT NULL "
                    "ORDER BY (page_end IS NOT NULL) DESC, id LIMIT 1", (council,))
                row = cur.fetchone()
                key = tuple(row) if row else None
        label = council + ("/" + chapter_key if chapter_key else "")
        rec = {"council": council, "chapter_key": chapter_key, "label": label,
               "n_ranges": len(ranges)}
        if key is None or key not in paths:
            rec["error"] = "no active registry PDF for this map"
            rec["check1"] = {"status": UNKNOWN, "reason": rec["error"],
                             "violations": []}
            rec["check2"] = dict(rec["check1"])
            rec["check3"] = dict(rec["check1"])
            results.append(rec)
            log("  " + label[:56].ljust(58) + "UNKNOWN  no registry PDF")
            continue
        try:
            with tempfile.TemporaryDirectory() as td:
                local = os.path.join(td, "c.pdf")
                s3.download_file(bucket, paths[key], local)
                with pdfplumber.open(local) as pdf:
                    pdf_pages = len(pdf.pages)
                    page_texts = [(p.extract_text() or "") for p in pdf.pages]
        except Exception as exc:
            rec["error"] = str(exc)[:160]
            for c in ("check1", "check2", "check3"):
                rec[c] = {"status": UNKNOWN, "reason": rec["error"], "violations": []}
            results.append(rec)
            log("  " + label[:56].ljust(58) + "UNKNOWN  " + rec["error"][:40])
            continue

        page_part = page_part_codes(page_texts)
        rec["pdf_pages"] = pdf_pages
        rec["resolved_chapter"] = key[1]
        rec["check1"] = check_ranges_within_pdf(ranges, pdf_pages)
        rec["check2"] = check_ranges_match_headers(ranges, page_part, pdf_pages)
        rec["check3"] = check_rows_match_page_headers(
            rows_by.get(key, []), page_part, pdf_pages)
        results.append(rec)
        log("  " + label[:56].ljust(58) +
            "1:" + rec["check1"]["status"][:4].ljust(5) +
            "2:" + rec["check2"]["status"][:4].ljust(5) +
            "3:" + rec["check3"]["status"][:4].ljust(5) +
            "  past-end=" + str(len(rec["check1"].get("violations") or [])) +
            " wrong-pages=" + str(len(rec["check2"].get("violations") or [])) +
            " bad-rows=" + str(rec["check3"].get("rows_disagree") or 0))
    conn.close()
    return results


# ── check 1 without R2: the page count the ledger already recorded ───────────
def sweep_from_ledger(only_council: str | None, log):
    """Run CHECK 1 ONLY, using pdf_pages from dcp_chapter_measurement.

    WHY THIS MODE EXISTS
    --------------------
    The full --check downloads 32 PDFs and takes over ten minutes, which is too
    slow to sit on every pull request. This reads the page count the last
    measurement sweep already recorded, so it needs DATABASE_URL and nothing
    else, and finishes in seconds.

    WHAT IT GIVES UP, SAID PLAINLY
    ------------------------------
    The page count is as fresh as the last sweep. If a council republishes a
    shorter PDF and no sweep has run since, this compares the map against the
    OLD page count and can miss a range that has just gone out of bounds. That
    is precisely the waverley failure mode, so this mode does not replace the
    full check -- the full one runs nightly in data-watch against R2, where ten
    minutes costs nothing.

    A chapter with NO ledger row is UNKNOWN, never a pass, and the caller fails
    on it: an unmeasured chapter is exactly what this whole exercise is about.
    """
    import psycopg2

    _load_env()
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise SystemExit("FATAL: no DATABASE_URL / SUPABASE_DB_URL")
    conn = psycopg2.connect(url, connect_timeout=20)
    cur = conn.cursor()
    cur.execute("SET statement_timeout='60s'")
    cur.execute("SELECT to_regclass('dcp_chapter_measurement')")
    if cur.fetchone()[0] is None:
        conn.close()
        raise SystemExit(
            "FATAL: dcp_chapter_measurement does not exist. Apply "
            "migrations/069 and run dcp_chapter_measure.py --sweep --write, or "
            "use the full --check against R2. Refusing to report a pass from a "
            "table that is not there.")
    # The newest measurement per chapter.
    cur.execute("""
        SELECT DISTINCT ON (council, chapter_key) council, chapter_key,
               pdf_pages, measured_at
        FROM dcp_chapter_measurement
        ORDER BY council, chapter_key, measured_at DESC""")
    pages, seen_at = {}, {}
    for council, chapter, n, at in cur.fetchall():
        pages[(council, chapter)] = n
        seen_at[(council, chapter)] = at
    cur.execute("""SELECT council, chapter_key FROM dcp_chapter_registry
                   WHERE is_active AND r2_current_path IS NOT NULL""")
    registry = [tuple(r) for r in cur.fetchall()]

    results = []
    maps = all_page_maps()
    if only_council:
        maps = [m for m in maps if m[0] == only_council]
    log("page maps to check against the ledger: " + str(len(maps)))

    for council, chapter_key, ranges in maps:
        key = (council, chapter_key)
        if chapter_key is None:
            # Same resolution as the full sweep. An earlier draft used
            # `cands[0] if len(cands) == 1 else None`, which returned None for
            # waverley (2 registry chapters) -- so its page count was unknown,
            # its counts were reported as 0, and the ratchet called that a
            # 5 -> 0 IMPROVEMENT. An unknown scored as a fix is the exact
            # failure this gate exists to stop.
            cands = [k for k in registry if k[0] == council]
            if len(cands) == 1:
                key = cands[0]
            else:
                cur.execute(
                    "SELECT council, chapter_key FROM dcp_chapter_registry "
                    "WHERE council=%s AND is_active AND r2_current_path IS NOT NULL "
                    "ORDER BY (page_end IS NOT NULL) DESC, id LIMIT 1", (council,))
                row = cur.fetchone()
                key = tuple(row) if row else None
        label = council + ("/" + chapter_key if chapter_key else "")
        rec = {"council": council, "chapter_key": chapter_key, "label": label,
               "n_ranges": len(ranges), "source": "ledger"}
        n = pages.get(key) if key else None
        rec["pdf_pages"] = n
        rec["measured_at"] = str(seen_at.get(key)) if key in seen_at else None
        rec["check1"] = check_ranges_within_pdf(ranges, n)
        # Checks 2 and 3 need page TEXT, which the ledger does not store.
        for c in ("check2", "check3"):
            rec[c] = {"status": UNKNOWN,
                      "reason": "needs page text; run the full --check",
                      "violations": []}
        results.append(rec)
        log("  " + label[:56].ljust(58) + "1:" + rec["check1"]["status"][:4].ljust(6) +
            "pdf=" + str(n) + "  past-end=" +
            str(len(rec["check1"].get("violations") or [])))
    conn.close()
    return results


def summarise(results):
    """Per-map counts for the ratchet.

    A check whose status is UNKNOWN contributes NO count at all -- not 0. This
    is the single most important line in this function. An earlier draft emitted
    0 for an unrunnable check, and the ratchet duly reported waverley going from
    5 violations to 0 as a RATCHET DOWN (good) when in truth its page count was
    simply missing. "Could not measure" scoring as "fixed" is the same defect as
    coverage_gap returning a clean pass for a document it never read.

    ratchet() treats an absent key as NO_BASELINE, which is reported and never
    counted as an improvement.
    """
    per = {}
    for r in results:
        counts = {
            "check1_status": r["check1"]["status"],
            "check2_status": r["check2"]["status"],
            "check3_status": r["check3"]["status"],
        }
        if r["check1"]["status"] != UNKNOWN:
            counts["check1_violations"] = len(r["check1"].get("violations") or [])
        if r["check2"]["status"] != UNKNOWN:
            counts["check2_violations"] = len(r["check2"].get("violations") or [])
        if r["check3"]["status"] != UNKNOWN:
            counts["check3_rows_disagree"] = r["check3"].get("rows_disagree", 0)
        per[r["label"]] = counts
    return per


RATCHET_KEYS = ("check1_violations", "check2_violations", "check3_rows_disagree")


def ratchet(now: dict, baseline: dict):
    """-> (regressions, improvements, no_baseline, not_measured). Four states.

    A key ABSENT from `counts` means that check could not run this time, and is
    returned as not_measured. It is never compared: comparing a check that did
    not run against a baseline of 5 would report a 5 -> 0 improvement, which is
    how an unknown becomes a "fix".
    """
    base = ((baseline or {}).get("per_map") or {})
    regressions, improvements, no_baseline, not_measured = [], [], [], []
    for label, counts in now.items():
        b = base.get(label)
        for key in RATCHET_KEYS:
            if key not in counts:
                not_measured.append({"map": label, "key": key,
                                     "was": (b or {}).get(key)})
                continue
            n = counts[key]
            if b is None or key not in b:
                no_baseline.append({"map": label, "key": key, "now": n})
                continue
            if n > b[key]:
                regressions.append({"map": label, "key": key, "was": b[key], "now": n})
            elif n < b[key]:
                improvements.append({"map": label, "key": key, "was": b[key], "now": n})
    return regressions, improvements, no_baseline, not_measured


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("--check", action="store_true", help="sweep every page map")
    ap.add_argument("--from-ledger", action="store_true",
                    help="CHECK 1 ONLY, from dcp_chapter_measurement.pdf_pages. "
                         "Seconds instead of ten minutes, no R2. The page count "
                         "is only as fresh as the last sweep -- the full --check "
                         "still runs nightly against R2.")
    ap.add_argument("--council", help="restrict to one council")
    ap.add_argument("--out", default="dcp_page_map_check.json")
    ap.add_argument("--record-baseline", action="store_true",
                    help="freeze the current counts as the ratchet floor")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    if not args.check:
        ap.error("--check is required")

    lines = []

    def log(s):
        lines.append(s)
        if not args.quiet:
            print(s, flush=True)

    baseline = {}
    if os.path.exists(BASELINE_PATH):
        with open(BASELINE_PATH, encoding="utf-8") as fh:
            baseline = json.load(fh)

    results = (sweep_from_ledger(args.council, log) if args.from_ledger
               else sweep(args.council, log))
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"checked_at": datetime.now(timezone.utc).isoformat(),
                   "results": results}, fh, indent=1)
    now = summarise(results)

    blocking = [r for r in results if r["check1"]["status"] == FAIL]
    unknown1 = [r for r in results if r["check1"]["status"] == UNKNOWN]
    log("")
    log("CHECK 1  ranges past the end of the PDF  -- THIS ONE BLOCKS EXTRACTION")
    for r in blocking:
        v = r["check1"]["violations"]
        log("   FAIL  " + r["label"][:50].ljust(52) + str(len(v)) + " of " +
            str(r["n_ranges"]) + " ranges past page " + str(r.get("pdf_pages")))
        for x in v[:6]:
            log("            " + x["code"].ljust(10) + str(x["start"]) + "-" +
                str(x["end"]))
    if unknown1:
        log("   UNKNOWN (not a pass) on " + str(len(unknown1)) + " maps")
    if not blocking and not unknown1:
        log("   PASS on all " + str(len(results)) + " maps")

    log("")
    log("CHECK 2  ranges whose pages carry a different part's header")
    for r in results:
        n = len(r["check2"].get("violations") or [])
        sh = len(r["check2"].get("start_shifts") or [])
        if n or sh:
            log("   " + r["label"][:50].ljust(52) +
                str(n) + " of " + str(r["n_ranges"]) + " on another part's pages" +
                "   (" + str(sh) + " start pages shifted)")
    log("")
    log("CHECK 3  stored rows contradicting their own page's header")
    for r in results:
        n = r["check3"].get("rows_disagree") or 0
        if n:
            log("   " + r["label"][:50].ljust(52) + str(n) + " of " +
                str(r["check3"].get("rows_checked") or 0) + " rows mislabelled")

    unknown_pages = [r for r in results
                     if r.get("source") == "ledger"
                     and r["check1"]["status"] == UNKNOWN]
    if unknown_pages:
        log("")
        log("*** " + str(len(unknown_pages)) + " page map(s) have NO ledger row -- "
            "their page count is unknown and check 1 could not run ***")
        for r in unknown_pages:
            log("   " + r["label"][:60])
        log("Run: python scripts/dcp_chapter_measure.py --sweep --write")

    regressions, improvements, no_baseline, not_measured = ratchet(now, baseline)
    log("")
    if improvements:
        log("RATCHET DOWN (good): " + str(len(improvements)) + " counts fell")
        for r in improvements[:20]:
            log("   " + r["map"][:44].ljust(46) + r["key"].ljust(24) +
                str(r["was"]) + " -> " + str(r["now"]))
    if no_baseline:
        log("NO BASELINE for " + str(len(no_baseline)) +
            " (map, key) pairs -- the floor is being set, this is not a pass.")
    if not_measured:
        still_bad = [r for r in not_measured if r["was"]]
        log("NOT MEASURED this run: " + str(len(not_measured)) +
            " (map, key) pairs -- these checks did not run, so their baseline "
            "still stands. NOT an improvement.")
        for r in still_bad[:10]:
            log("   " + r["map"][:44].ljust(46) + r["key"].ljust(24) +
                "baseline " + str(r["was"]) + " UNVERIFIED")
    if regressions:
        log("")
        log("*** GATE FAIL -- " + str(len(regressions)) + " counts rose ***")
        for r in regressions:
            log("   " + r["map"][:44].ljust(46) + r["key"].ljust(24) +
                str(r["was"]) + " -> " + str(r["now"]))

    if args.record_baseline:
        # Never let a run that could not measure something erase that thing's
        # recorded floor. Keys absent from this run keep their previous value.
        merged = {k: dict(v) for k, v in (baseline.get("per_map") or {}).items()}
        for label, counts in now.items():
            merged.setdefault(label, {}).update(counts)
        with open(BASELINE_PATH, "w", encoding="utf-8") as fh:
            json.dump({
                "_comment": (
                    "Ratchet floor for scripts/dcp_page_map_gate.py. These counts "
                    "may go DOWN, never UP. Freezing them is what lets a "
                    "fail-closed check go live without failing on defects that "
                    "already exist and are already recorded. It is not an "
                    "acceptance of them."),
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "per_map": merged,
            }, fh, indent=2)
        log("")
        log("baseline recorded into " + BASELINE_PATH)
        return 0

    return 2 if (regressions or unknown_pages) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print("FATAL: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        sys.exit(1)
