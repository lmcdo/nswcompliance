#!/usr/bin/env python3
# prior-art-checked: reuses verify_extraction_fidelity's grounding helpers (_numbers,
# _content_words, _norm, _page_text_for_chapter, _NUM_RE) and services.extracted_data_integrity
# rather than reimplementing. That script REPORTS fidelity on committed provisions; this one
# WRITES a per-row fidelity verdict onto pending dcp_review_queue rows so the review UI can
# surface only flagged rows. Different target (queue vs live), different output (update vs report).
"""
DCP fidelity gate — grade each pending review-queue row against its source PDF so a human
reviews only what's FLAGGED and bulk-clears the source-grounded rest with evidence.

For each pending row of a chapter, against the chapter's own PDF:
  * find the real source page (the AI page number resets per chunk) — stored only on a
    CONFIDENT text match, else left NULL (never a guessed page);
  * NUMERIC fidelity — every number (excluding the row's own section code) must appear on
    that page (or, if the page is ambiguous, anywhere in the chapter);
  * TOKEN grounding — the row's distinctive words must be present;
  -> writes fidelity_status ('grounded'|'flagged'), fidelity_detail, source_page_verified.

Deterministic (no LLM), re-runnable. Does NOT approve or commit anything — it only grades,
so the human gate is untouched.

Usage:
    python scripts/dcp_fidelity_gate.py --council woollahra              # all its pending chapters
    python scripts/dcp_fidelity_gate.py --council woollahra --chapter c2 # one chapter
"""

import argparse
import sys

import re

import psycopg2

import dcp_extract_changed as dx
import verify_extraction_fidelity as vf

# A confident page match needs the best page to clearly beat the runner-up (validated live:
# ~77% of provisions clear this; the ~23% that don't are repeated/short/straddling rules).
_MIN_BEST = 0.5
_MIN_MARGIN = 0.15
_SENT_RE = re.compile(r"(?<=[.;:])\s+")


def _source_quote(ai_text: str, absent: list[str], source_text: str) -> str | None:
    """The sentence from the source PDF the reviewer should compare a flag against.

    Find the AI sentence that carries a flagged number, then the source sentence with the
    highest word overlap — that is what the council's document actually says. Lets the UI
    show 'AI wrote 2.9m / source says 0.9m' so a flag is resolvable at a glance, not by
    opening the PDF and hunting. Returns None when nothing lines up well enough (>=40%)."""
    if not absent or not source_text:
        return None
    ai_sents = _SENT_RE.split(ai_text or "")
    target = next((s for s in ai_sents if any(n in s for n in absent)), ai_text or "")
    tw = set(vf._content_words(target))
    if not tw:
        return None
    best, best_score = "", 0.0
    for s in _SENT_RE.split(source_text):
        sw = set(vf._content_words(s))
        score = len(tw & sw) / len(tw)
        if score > best_score:
            best, best_score = s, score
    if best_score < 0.4:
        return None
    return re.sub(r"\s+", " ", best).strip()[:240]


def _best_page(prov_words: set, pages: dict) -> tuple[int | None, bool]:
    """Return (page, confident). page is the best-scoring page; confident is True only when
    it clearly beats the runner-up so we never store a guessed page."""
    if not prov_words or not pages:
        return None, False
    scored = sorted(
        ((sum(1 for w in prov_words if w in pages[pg]) / len(prov_words), pg) for pg in pages),
        reverse=True,
    )
    best = scored[0]
    second = scored[1] if len(scored) > 1 else (0.0, None)
    confident = best[0] >= _MIN_BEST and (best[0] - second[0]) >= _MIN_MARGIN
    return best[1], confident


_TABLE_CAPTION_RE = re.compile(r"\*\*Table\s+(\d+)\*\*\s*\(Page\s+(\d+)\)")
_PAGE_CITATION_RE = re.compile(r"\bpage\s+(\d+)\b", re.IGNORECASE)
_FIGURE_CITATION_RE = re.compile(r"\bFigures?\s+(\d+)\b")
_FIGURE_RANGE_RE = re.compile(r"\bFigures?\s+(\d+)\s*[-–]\s*(\d+)\b")
_CLAUSE_CITATION_RE = re.compile(r"\b(?:DS|PC)\s*(\d+(?:\.\d+)*)\b")
# ku_ring_gai's running-footer stamp: "p 14-135" (section-scoped page number),
# distinct from the generic "page N" phrasing _PAGE_CITATION_RE already covers.
_FOOTER_STAMP_RE = re.compile(r"\bp\s+(\d+)-(\d+)\b")
# A property/street-address number ("no.810 Pacific Highway") cited to name a
# SITE, not a regulatory value -- the real measurement sits elsewhere in the
# same sentence (e.g. "3 metre setback ... applying to property no.810 ...").
_PROPERTY_NUMBER_RE = re.compile(r"\bno\.?\s*(\d+)\b", re.IGNORECASE)


def _page_window(page: int, pages: dict, text: str = "") -> str:
    """Text of the anchor page, its immediate neighbours, and any page this row's
    own '**Table N** (Page P)' captions name explicitly.

    The +-1 neighbours catch a clause that opens near the bottom of one page and
    finishes on the next (footer stamps like '2.1-4' / '2.1-5' are the tell). The
    caption pages catch something +-1 can miss: a row built from several stitched
    tables (dcp_extract_changed.py's enqueue_review_changes) can legitimately span
    MORE than 3 consecutive pages, and each caption already states -- as fact, not
    a word-overlap guess -- exactly which page its table came from. Neither widening
    falls all the way back to the whole chapter, which is a much weaker check (used
    only when the page itself is ambiguous) because almost any word appears
    somewhere in a multi-page chapter."""
    window_pages = {p for p in (page - 1, page, page + 1) if p in pages}
    for m in _TABLE_CAPTION_RE.finditer(text or ""):
        cap_page = int(m.group(2))
        if cap_page in pages:
            window_pages.add(cap_page)
    return " ".join(pages[p] for p in sorted(window_pages))


def _citation_numbers(text: str) -> set:
    """Numbers that only ever appear as a page/table/figure/clause CITATION --
    pointing at content elsewhere in the document -- not as a regulatory value in
    this row's own content. All four sources are structurally guaranteed rather
    than guessed:

      * '**Table N** (Page P)' -- a caption dcp_extract_changed.py stamps itself when
        stitching an extracted table into the provision text (see enqueue_review_changes);
        P is the real pdfplumber page the table came from, known by construction, never
        an AI guess.
      * 'page N' / 'Figure N' / 'Figures N-M' in body prose -- the AI faithfully
        transcribing a cross-reference to a different page/figure elsewhere in the same
        DCP (e.g. 'see Figures 8-11', 'Comprehensive Inner West DCP 2016 page 123').
        A checker anchored on ONE page can never meaningfully validate a pointer to a
        DIFFERENT one -- the citation might be correct or wrong, but 'is N a real page
        somewhere in this multi-page chapter' answers nothing either way, so these are
        excluded from fidelity checking rather than produce a false alarm.
      * 'DS N.N' / 'PC N' -- a cross-reference to a DIFFERENT provision's own Design
        Solution / Performance Criteria code within the same DCP numbering convention
        (e.g. 'pursuant to clauses PC2 and DS 2.6') -- the same idea as excluding this
        row's OWN ref_number digits (code_nums in ground_row), just for a citation to
        someone else's code instead of this row's own.
      * 'p 14-135' -- ku_ring_gai's own running-footer stamp (section-scoped page
        number; measured live: chapter section-b-part-14d, ref 14d_9), distinct
        formatting from the 'page N' case but the same underlying thing.
      * 'no.810 Pacific Highway' -- a property/street-address number naming a SITE,
        not a regulatory value (the real measurement is elsewhere in the same
        sentence, e.g. '3 metre setback ... applying to property no.810 ...')."""
    text = text or ""
    nums: set = set()
    for m in _TABLE_CAPTION_RE.finditer(text):
        nums.add(m.group(1))  # table index
        nums.add(m.group(2))  # page number
    for m in _PAGE_CITATION_RE.finditer(text):
        nums.add(m.group(1))
    for m in _FIGURE_RANGE_RE.finditer(text):
        lo, hi = int(m.group(1)), int(m.group(2))
        if 0 <= hi - lo <= 20:  # sane range guard against a stray "Figure 3-99999" match
            nums.update(str(n) for n in range(lo, hi + 1))
    for m in _FIGURE_CITATION_RE.finditer(text):
        nums.add(m.group(1))
    for m in _CLAUSE_CITATION_RE.finditer(text):
        nums.add(m.group(1))
    for m in _FOOTER_STAMP_RE.finditer(text):
        nums.add(m.group(1))
        nums.add(m.group(2))
    for m in _PROPERTY_NUMBER_RE.finditer(text):
        nums.add(m.group(1))
    return nums


def ground_row(text: str, ref_number: str, pages: dict) -> dict:
    """Grade one row. Returns dict(status, detail, verified_page)."""
    prov_words = set(vf._content_words(text))
    page, confident = _best_page(prov_words, pages)
    verified_page = page if confident else None
    # Ground numbers/words against the confident page +- 1 (plus any page this row's
    # own table captions name), else the whole chapter.
    source = _page_window(page, pages, text) if confident else " ".join(pages.values())

    code_nums = set(vf._NUM_RE.findall((ref_number or "").split("__")[-1].replace("_", ".")))
    # A provision's own markdown heading (e.g. "# D-Part12 55-63 Smith Street") carries
    # street-address/precinct numbers that are structural labels, not content to verify.
    # dcp_extract_changed.py always builds new_text as "# {heading}\n\n{content}"
    # (enqueue_review_changes / the table-stitching helper), so requiring the first
    # line to actually start with '#' is what keeps this from swallowing a genuine
    # single-line/no-heading row's own numbers into a bogus "heading" exclusion.
    first_line = (text or "").splitlines()[0] if text else ""
    heading_nums = set(vf._NUM_RE.findall(first_line)) if first_line.lstrip().startswith("#") else set()
    excluded_nums = code_nums | heading_nums | _citation_numbers(text)
    nums = [n for n in vf._numbers(text) if n not in excluded_nums]
    absent = [r["v"] for r in vf.value_absent_from_source(
        [{"v": n, "src": source} for n in nums], value_field="v", source_field="src")]
    grounded_words = sum(1 for w in prov_words if w in source)
    ground_ratio = grounded_words / len(prov_words) if prov_words else 1.0

    if absent or ground_ratio < 0.75:
        detail = []
        if absent:
            detail.append(f"numbers not in source: {', '.join(absent)}")
        if ground_ratio < 0.75:
            detail.append(f"only {int(ground_ratio*100)}% of words found in source")
        quote = _source_quote(text, absent, source) if absent else None
        return {"status": "flagged", "detail": "; ".join(detail),
                "verified_page": verified_page, "source_quote": quote}
    return {"status": "grounded", "detail": None, "verified_page": verified_page,
            "source_quote": None}


def gate_chapter(cur, s3, council: str, chapter_key: str, r2_path: str) -> tuple[int, int]:
    """Grade every pending row of one chapter; return (grounded, flagged)."""
    try:
        pages = vf._page_text_for_chapter(s3, r2_path, council)
    except Exception as exc:  # noqa: BLE001 — a bad PDF shouldn't abort the run
        print(f"    [warn] {council}/{chapter_key}: cannot read PDF ({exc}); left unchecked.")
        return 0, 0
    cur.execute(
        "SELECT id, ref_number, new_text FROM dcp_review_queue "
        "WHERE council=%s AND chapter_key=%s AND status IN ('pending','in_progress') "
        "AND change_type <> 'removed' AND new_text IS NOT NULL",
        (council, chapter_key),
    )
    grounded = flagged = 0
    for row_id, ref_number, new_text in cur.fetchall():
        r = ground_row(new_text, ref_number, pages)
        cur.execute(
            "UPDATE dcp_review_queue SET fidelity_status=%s, fidelity_detail=%s, "
            "source_page_verified=%s, fidelity_source_quote=%s WHERE id=%s",
            (r["status"], r["detail"], r["verified_page"], r["source_quote"], row_id),
        )
        if r["status"] == "grounded":
            grounded += 1
        else:
            flagged += 1
    return grounded, flagged


def main() -> int:
    ap = argparse.ArgumentParser(description="Grade pending DCP review rows against source PDFs.")
    ap.add_argument("--council", required=True)
    ap.add_argument("--chapter", help="Limit to one chapter_key (default: all pending chapters).")
    args = ap.parse_args()

    s3 = dx.boto3.client(
        "s3", endpoint_url=dx.R2_ENDPOINT, aws_access_key_id=dx.R2_ACCESS_KEY_ID,
        aws_secret_access_key=dx.R2_SECRET_ACCESS_KEY, region_name="auto",
    )
    conn = psycopg2.connect(dx.DATABASE_URL)
    cur = conn.cursor()
    sql = ("SELECT DISTINCT q.chapter_key, reg.r2_current_path FROM dcp_review_queue q "
           "JOIN dcp_chapter_registry reg ON reg.council=q.council AND reg.chapter_key=q.chapter_key "
           "WHERE q.council=%s AND q.status IN ('pending','in_progress') "
           "AND reg.r2_current_path IS NOT NULL")
    params = [args.council]
    if args.chapter:
        sql += " AND q.chapter_key=%s"
        params.append(args.chapter)
    cur.execute(sql, params)
    chapters = cur.fetchall()
    if not chapters:
        print("No pending chapters with a source PDF.")
        return 0

    tot_g = tot_f = 0
    for chapter_key, r2_path in chapters:
        g, f = gate_chapter(cur, s3, args.council, chapter_key, r2_path)
        conn.commit()
        tot_g += g
        tot_f += f
        print(f"  {chapter_key:<40} grounded={g:>4}  flagged={f:>3}")

    total = tot_g + tot_f
    pct = 100 * tot_g / total if total else 0
    print("-" * 60)
    print(f"graded {total} rows: {tot_g} grounded ({pct:.0f}%), {tot_f} flagged for human review.")
    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
