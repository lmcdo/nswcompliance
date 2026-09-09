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
# dcp_extract_changed already inserts the repo root onto sys.path for its own
# `from enrichment.pipeline import ...` -- this import relies on that having
# already run (it has, via the `import dcp_extract_changed as dx` above).
from enrichment.extractors.actionable_classifier import classify_provision

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


def _number_window(page: int, pages: dict, text: str) -> str:
    """Numbers are checked against a NARROWER source than words: the anchor page
    plus only pages this row's own table captions explicitly name -- NOT the +-1
    neighbours _page_window adds for word-straddling. Sol cross-review (HIGH 0.98):
    grounding numbers against a full neighbour-page window let an unrelated,
    coincidentally-identical value on the ADJACENT provision mask a genuinely wrong
    one on THIS page (anchor page 11 says '4.5 metres', unrelated page 12 happens to
    say '9.9 metres' about something else, and a hallucinated '9.9' on page 11 would
    wrongly ground). Caption pages stay in: unlike a neighbour, a caption page is
    this row's OWN table, known by construction, not a coincidence of proximity.

    ACCEPTED RESIDUAL, other direction (Sol cross-review MEDIUM 0.96, on push): a
    provision that genuinely straddles an ordinary page break -- its distinctive
    words make page 11 the confident anchor, but its final sentence and number
    continue onto page 12 with no table caption -- will have that number fall
    outside this window and get wrongly flagged, even though word_source's +-1
    window (_page_window) correctly grounds the surrounding words. Deliberately
    NOT widened back to +-1 for numbers: doing so is exactly what caused the
    masking regression this function's own docstring documents above, and
    dcp_review_queue is a human-gated staging table where a wrongly-flagged
    correct row costs a human's review time while a wrongly-grounded wrong
    number ships a false 'this is correct' signal -- see this file's module
    docstring and the QA report's tier justification for why that asymmetry is
    the deciding factor. Same shape as the citation-masking residual documented
    in _blank_verified_references's break_it entry -- named, accepted, not
    silently hidden."""
    window_pages = {page} if page in pages else set()
    for m in _TABLE_CAPTION_RE.finditer(text or ""):
        cap_page = int(m.group(2))
        if cap_page in pages:
            window_pages.add(cap_page)
    return " ".join(pages[p] for p in sorted(window_pages))


def _phrase_verified(phrase: str, whole_chapter: str) -> bool:
    """Is `phrase` (a matched citation/heading) real, not hallucinated?

    Checks its distinctive WORDS (>=4 letters, same _content_words extraction
    the word-grounding check already uses) and its DIGIT substrings each appear
    SOMEWHERE in whole_chapter -- independently, not as one exact contiguous
    substring. Word-by-word rather than exact-phrase is deliberate: a real PDF
    running header repeats with different line-wrapping/whitespace across
    pages, so an exact-substring check fails genuinely correct content (see
    _blank_verified_references's docstring for the live regression this caused).
    Still catches a hallucinated citation (source says '2.7', extraction says
    '2.6' -- '2.6' is not a substring of the source anywhere, contiguous or
    not) while tolerating real-world formatting noise. Requires at least one
    word or digit to check -- an empty/punctuation-only phrase verifies nothing."""
    words = vf._content_words(phrase)
    digits = vf._NUM_RE.findall(phrase)
    if not words and not digits:
        return False
    return (all(w in whole_chapter for w in words)
            and all(d in whole_chapter for d in digits))


def _blank_verified_references(text: str, whole_chapter: str) -> str:
    """Copy of `text` with each citation/footer/property-reference OCCURRENCE
    blanked out of the SPAN it actually matched -- but only when that exact
    phrase is independently verified present somewhere in the chapter's real
    text (table captions are the one exception, verified by construction, see
    below). Two failure modes this closes (Sol cross-review, both HIGH):

      * VALUE-based exclusion (the earlier version of this function) removed
        every occurrence of a citation's digit STRING from consideration, not
        just the citation's own occurrence -- so a legitimate 'Figure 10' could
        mask a completely different, genuinely wrong '10 m' elsewhere in the
        same row (confidence 1.0). Blanking the matched SPAN only removes that
        one occurrence; every other occurrence of '10' is still checked.
      * The citation's own digits were trusted unconditionally, so a
        hallucinated citation (source says 'DS 2.6', extraction says 'DS 2.7')
        was excluded with no check that it even corresponds to anything real
        (confidence 0.99). Verifying the matched phrase's WORDS and DIGITS
        against the WHOLE CHAPTER (not just the local page window -- a real
        citation routinely points elsewhere in the document, which is why it
        was being excluded in the first place) catches a citation that
        corresponds to nothing in the real document at all, while still
        accepting one that genuinely points to a distant page.

    Verification is WORD-BY-WORD-AND-DIGIT, not one exact contiguous phrase
    (regression, caught live re-running the batch after shipping exact-phrase
    matching: ashfield D-Part12's real running header repeats '55-63 Smith
    Street Summer Hill' with different line-wrapping/whitespace on every real
    page, so an exact-substring check on the whole phrase failed even though
    the heading is genuinely correct, sending 3->23 flagged the wrong way).
    _content_words() + a digit scan is the same word-by-word convention the
    pre-existing WORD-grounding check already uses elsewhere in this file --
    it still catches Sol's exact scenario (source says '2.7', extraction says
    '2.6' -- '2.6' is simply not a substring of the source anywhere, contiguous
    or not) while tolerating the whitespace/line-wrap noise real PDF extraction
    produces.

    Table-caption numbers are verified by construction, not by text matching:
    dcp_extract_changed.py stamps '**Table N** (Page P)' itself from the real
    pdfplumber page as it stitches the table in (enqueue_review_changes) -- P
    is never an AI guess, so there is nothing to look up in whole_chapter."""
    text = text or ""
    whole_chapter = (whole_chapter or "").lower()
    spans: list[tuple[int, int]] = []
    for m in _TABLE_CAPTION_RE.finditer(text):
        spans.append((m.start(), m.end()))
    for rx in (_PAGE_CITATION_RE, _FIGURE_RANGE_RE, _FIGURE_CITATION_RE,
               _CLAUSE_CITATION_RE, _FOOTER_STAMP_RE, _PROPERTY_NUMBER_RE):
        for m in rx.finditer(text):
            if _phrase_verified(m.group(0), whole_chapter):
                spans.append((m.start(), m.end()))
    # A provision's own markdown heading (e.g. "# D-Part12 55-63 Smith Street")
    # carries street-address/precinct numbers that are structural labels, not
    # content to verify locally -- but (Sol HIGH 0.98) only once the heading
    # itself is confirmed to be the real one, not a hallucinated address/site
    # range. dcp_extract_changed.py always builds new_text as
    # "# {heading}\n\n{content}", so requiring the line to start with '#' is
    # what keeps a genuine single-line/no-heading row's own numbers from being
    # swallowed by a bogus "heading" match.
    first_line = text.splitlines()[0] if text else ""
    if first_line.lstrip().startswith("#"):
        heading_phrase = first_line.lstrip("# ")
        if heading_phrase and _phrase_verified(heading_phrase, whole_chapter):
            spans.append((0, len(first_line)))
    if not spans:
        return text
    out = list(text)
    for start, end in spans:
        for i in range(start, min(end, len(out))):
            out[i] = " "
    return "".join(out)


# prior-art-checked: reuses vf._content_words and vf._norm (this project's existing
# word-extraction and normalisation helpers, already used throughout this module) --
# no new text pipeline. Only the straddle-rescue rule below is new.
_CONTEXT_WORDS = 6      # words either side of the number that must travel with it
_CONTEXT_MATCH = 0.6    # share of them that must appear beside the number in the chapter


def _num_token(num: str) -> re.Pattern:
    """`num` as a whole numeric token, never a fragment of a longer one.

    Sol cross-review HIGH 0.99: a bare re.escape(num) search is an unbounded
    substring match, so a rule saying '5 metres' would ground against a chapter
    saying '15 metres' -- the '5' inside '15' matches, the surrounding wording is
    identical, the context threshold passes, and a WRONG control is marked
    source-verified. That is the masking failure this whole module exists to
    prevent, reintroduced in a new place.

    Leading (?<![\\d.]) rejects '5' inside '15' and inside '11.5'. Trailing
    (?!\\d)(?!\\.\\d) rejects '5' inside '51' and inside '5.5', while still
    accepting a number that legitimately ends a sentence ('set back 6.').

    Sol cross-review HIGH 0.97, second round: those two guards still let a
    THOUSANDS-SEPARATED value through -- '500' matched inside '1,500' because
    the preceding character is a comma, so a rule saying 'minimum lot size is
    500 square metres' grounded against a chapter saying '1,500 square metres'.
    (?<!\\d,) rejects a number sitting after a digit-comma group, and (?!,\\d)
    rejects one that STARTS such a group ('5' inside '5,000'). A leading sign is
    excluded too: '-5' is not the same value as '5'. A comma in ordinary prose
    ('3, 5 and 7') is unaffected, because there the number follows the space,
    not the comma.
    """
    return re.compile(
        r"(?<![\d.])(?<!\d,)(?<!-)" + re.escape(num) + r"(?!\d)(?!\.\d)(?!,\d)"
    )


def _straddle_grounded(num: str, text: str, whole_chapter: str) -> bool:
    """True when a number ruled absent from its narrow page window is found
    elsewhere in the SAME chapter carrying enough of its own surrounding words
    to be the same clause, not a coincidence.

    Why this exists: _number_window deliberately checks numbers against the
    anchor page only, because a +-1 page window let an unrelated identical value
    on a neighbouring page mask a wrong one (see that function's docstring). The
    accepted cost was that a clause straddling a page break gets wrongly flagged.
    Measured 2026-09-09, that cost was not small: of 433 flagged rows, 428 were
    this false alarm and 5 were real -- a 1.2% true-positive rate that made the
    human queue unworkable, so nothing got reviewed at all.

    Widening the window alone would reinstate the masking bug. Requiring the
    number to bring its own context does not: an unrelated '11.5' elsewhere in
    the chapter will not be surrounded by this clause's words. Verified against
    both directions on real data -- ku_ring_gai's '3 storey (11.5 metres) street
    wall' grounds in the St Ives chapter (whose PDF contains that exact phrase)
    and stays flagged in Gordon and Roseville (whose PDFs contain neither '11.5'
    nor 'consistent 3 storey'), which is a genuine cross-precinct copy error.
    """
    if not num or not text or not whole_chapter:
        return False
    hay = vf._norm(whole_chapter)
    token = _num_token(num)
    for m in token.finditer(text):
        before = vf._content_words(text[max(0, m.start() - 120): m.start()])[-_CONTEXT_WORDS:]
        after = vf._content_words(text[m.end(): m.end() + 120])[:_CONTEXT_WORDS]
        context = [w for w in (before + after) if w]
        if not context:
            continue
        # The number must appear in the chapter WITH its neighbours nearby, so
        # scan each occurrence's own local span rather than the whole document.
        for hm in token.finditer(hay):
            span = hay[max(0, hm.start() - 260): hm.end() + 260]
            hit = sum(1 for w in context if w in span)
            if hit / len(context) >= _CONTEXT_MATCH:
                return True
    return False


def ground_row(text: str, ref_number: str, pages: dict) -> dict:
    """Grade one row. Returns dict(status, detail, verified_page)."""
    prov_words = set(vf._content_words(text))
    page, confident = _best_page(prov_words, pages)
    verified_page = page if confident else None
    whole_chapter = " ".join(pages.values())
    # Words ground against the wider +-1/caption window (straddling text); numbers
    # against the narrower anchor+caption-only window (Sol HIGH 0.98, see _number_window).
    word_source = _page_window(page, pages, text) if confident else whole_chapter
    number_source = _number_window(page, pages, text) if confident else whole_chapter

    code_nums = set(vf._NUM_RE.findall((ref_number or "").split("__")[-1].replace("_", ".")))
    cleaned_text = _blank_verified_references(text, whole_chapter)
    nums = [n for n in vf._numbers(cleaned_text) if n not in code_nums]
    absent = [r["v"] for r in vf.value_absent_from_source(
        [{"v": n, "src": number_source} for n in nums], value_field="v", source_field="src")]
    # Straddle rescue: a number missing from the narrow anchor-page window is not
    # yet wrong -- the clause may simply continue onto the next page. Keep it
    # flagged only if it cannot be found elsewhere in this chapter carrying its
    # own surrounding words. See _straddle_grounded for why context is required
    # rather than just widening the window.
    if absent:
        absent = [n for n in absent if not _straddle_grounded(n, cleaned_text, whole_chapter)]
    grounded_words = sum(1 for w in prov_words if w in word_source)
    ground_ratio = grounded_words / len(prov_words) if prov_words else 1.0

    if absent or ground_ratio < 0.75:
        detail = []
        if absent:
            detail.append(f"numbers not in source: {', '.join(absent)}")
        if ground_ratio < 0.75:
            detail.append(f"only {int(ground_ratio*100)}% of words found in source")
        quote = _source_quote(text, absent, number_source) if absent else None
        return {"status": "flagged", "detail": "; ".join(detail),
                "verified_page": verified_page, "source_quote": quote}
    return {"status": "grounded", "detail": None, "verified_page": verified_page,
            "source_quote": None}


# prior-art-checked: reuses enrichment.extractors.actionable_classifier.classify_provision
# verbatim (regex-based, the project's one existing actionable/boilerplate classifier,
# already used at extraction time) -- no new classifier, no new pattern list. This call
# site is new (skip GRADING a row, not extraction), the classification logic is 100% reused.
def gate_chapter(cur, s3, council: str, chapter_key: str, r2_path: str) -> tuple[int, int, int]:
    """Grade every pending row of one chapter; return (grounded, flagged, skipped_not_actionable).

    A row whose own text classify_provision() says is boilerplate/administrative
    (introductions, definitions, legislative headers) is left ungraded entirely --
    not flagged, not marked grounded, fidelity_status untouched. It never becomes
    live/actionable regulatory content even once approved, so grading it against
    the source PDF spends real R2/CPU time on something that was never going to
    matter to a served user (2026-09-07, in direct response to being asked why
    this wasn't already automatic)."""
    try:
        pages = vf._page_text_for_chapter(s3, r2_path, council)
    except Exception as exc:  # noqa: BLE001 — a bad PDF shouldn't abort the run
        print(f"    [warn] {council}/{chapter_key}: cannot read PDF ({exc}); left unchecked.")
        return 0, 0, 0
    cur.execute(
        "SELECT id, ref_number, new_text FROM dcp_review_queue "
        "WHERE council=%s AND chapter_key=%s AND status IN ('pending','in_progress') "
        "AND change_type <> 'removed' AND new_text IS NOT NULL",
        (council, chapter_key),
    )
    grounded = flagged = skipped = 0
    for row_id, ref_number, new_text in cur.fetchall():
        is_actionable, _reason = classify_provision(new_text)
        if not is_actionable:
            skipped += 1
            continue
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
    return grounded, flagged, skipped


def chapters_query(council: str, chapter: str | None, include_backlog: bool) -> tuple[str, list]:
    """Build the SQL (+ params) that selects which pending chapters to grade.
    Pulled out of main() so a real-DB test can execute exactly this query,
    not a hand-copied approximation of it, against the actual tables.

    reg.is_active is required unconditionally, regardless of include_backlog:
    a retired/superseded registry entry should never be graded even when
    --include-backlog widens the live+actionable content requirement -- the
    two flags answer different questions (is this chapter still the one we
    serve at all vs has it ever had approved live content). Sol cross-review
    (MEDIUM 0.99, on push): this was a gap in the ORIGINAL main() query,
    present before this branch's refactor, not introduced by it -- caught
    because chapters_query's extraction made the query independently
    reviewable for the first time."""
    sql = ("SELECT DISTINCT q.chapter_key, reg.r2_current_path FROM dcp_review_queue q "
           "JOIN dcp_chapter_registry reg ON reg.council=q.council AND reg.chapter_key=q.chapter_key "
           "WHERE q.council=%s AND q.status IN ('pending','in_progress') "
           "AND reg.r2_current_path IS NOT NULL AND reg.is_active")
    params = [council]
    if not include_backlog:
        # prior-art-checked: is_current AND v2_is_actionable is the project's own
        # established definition of "live + actionable (the served set)" -- see
        # CLAUDE.md's Database Quick Reference table (19,957 of 55,696 provisions).
        # Reused verbatim, not a new definition of "live".
        sql += (" AND EXISTS (SELECT 1 FROM regulatory_provisions rp "
                "WHERE rp.source_council = q.council AND rp.source_chapter_key = q.chapter_key "
                "AND rp.is_current AND rp.v2_is_actionable)")
    if chapter:
        sql += " AND q.chapter_key=%s"
        params.append(chapter)
    return sql, params


def main() -> int:
    ap = argparse.ArgumentParser(description="Grade pending DCP review rows against source PDFs.")
    ap.add_argument("--council", required=True)
    ap.add_argument("--chapter", help="Limit to one chapter_key (default: all pending chapters).")
    ap.add_argument(
        "--include-backlog", action="store_true",
        help="Also grade chapters with no existing live+actionable regulatory_provisions "
             "(not-yet-approved/reference-only content). Default OFF: grading spends real "
             "R2/CPU time, so by default this only covers what a real user can currently see "
             "-- a chapter awaiting its first approval, or a pure reference document, isn't "
             "that yet. Rows are never deleted or hidden by omitting this flag, only left "
             "ungraded until explicitly asked for.",
    )
    args = ap.parse_args()

    s3 = dx.boto3.client(
        "s3", endpoint_url=dx.R2_ENDPOINT, aws_access_key_id=dx.R2_ACCESS_KEY_ID,
        aws_secret_access_key=dx.R2_SECRET_ACCESS_KEY, region_name="auto",
    )
    conn = psycopg2.connect(dx.DATABASE_URL)
    cur = conn.cursor()
    sql, params = chapters_query(args.council, args.chapter, args.include_backlog)
    cur.execute(sql, params)
    chapters = cur.fetchall()
    if not chapters:
        scope_note = "" if args.include_backlog else " with live+actionable content (see --include-backlog)"
        print(f"No pending chapters{scope_note}.")
        return 0

    tot_g = tot_f = tot_s = 0
    for chapter_key, r2_path in chapters:
        g, f, s = gate_chapter(cur, s3, args.council, chapter_key, r2_path)
        conn.commit()
        tot_g += g
        tot_f += f
        tot_s += s
        print(f"  {chapter_key:<40} grounded={g:>4}  flagged={f:>3}  skipped(non-actionable)={s:>3}")

    total = tot_g + tot_f
    pct = 100 * tot_g / total if total else 0
    print("-" * 60)
    print(f"graded {total} rows: {tot_g} grounded ({pct:.0f}%), {tot_f} flagged for human review "
          f"({tot_s} non-actionable rows skipped, not graded).")
    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
