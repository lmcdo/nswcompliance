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

import psycopg2

import dcp_extract_changed as dx
import verify_extraction_fidelity as vf

# A confident page match needs the best page to clearly beat the runner-up (validated live:
# ~77% of provisions clear this; the ~23% that don't are repeated/short/straddling rules).
_MIN_BEST = 0.5
_MIN_MARGIN = 0.15


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


def ground_row(text: str, ref_number: str, pages: dict) -> dict:
    """Grade one row. Returns dict(status, detail, verified_page)."""
    prov_words = set(vf._content_words(text))
    page, confident = _best_page(prov_words, pages)
    verified_page = page if confident else None
    # Ground numbers/words against the confident page, else the whole chapter.
    source = pages.get(page, "") if confident else " ".join(pages.values())

    code_nums = set(vf._NUM_RE.findall((ref_number or "").split("__")[-1].replace("_", ".")))
    nums = [n for n in vf._numbers(text) if n not in code_nums]
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
        return {"status": "flagged", "detail": "; ".join(detail), "verified_page": verified_page}
    return {"status": "grounded", "detail": None, "verified_page": verified_page}


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
            "source_page_verified=%s WHERE id=%s",
            (r["status"], r["detail"], r["verified_page"], row_id),
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
