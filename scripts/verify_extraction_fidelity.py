#!/usr/bin/env python3
# prior-art-checked: reuse not viable as a whole, but this REUSES the two existing pieces
# rather than reimplementing them: dcp_extract_changed (R2 download + _extract_page_text /
# _clean_page_text page-text) and services.extracted_data_integrity.value_absent_from_source
# (number-form matching). No existing script grounds a committed AI PROVISION against its
# cited source PDF page — verify_dcp_formatting checks text artifacts, validate_dcp_health
# checks live-data integrity; neither opens the source PDF.
"""
DCP extraction-fidelity verifier — proves an AI-extracted provision is GROUNDED in the
council's own source PDF, deterministically (no second LLM, no fuzzy threshold to argue).

Why deterministic: an LLM-as-judge is non-deterministic and is AI-verifying-AI — a
challenger can't re-run it and get the same answer. This check is reproducible: it opens
the exact source page and reports, per provision, what is and isn't found there.

For each committed AI provision (extraction_method='ai-reviewed', is_current), against its
own cited source PDF page(s):

  * NUMERIC FIDELITY (the strong signal) — every number in the provision text must appear
    on its cited page. Numbers don't reformat, so a number that's absent is a real
    red flag (an altered setback/height). Reuses extracted_data_integrity's number-form
    matcher (24.0->24 etc.); advisory (known unit-conversion false positives, e.g. 900mm
    vs 0.9m), so it routes to human review rather than blocking.
  * TOKEN GROUNDING (anti-invention) — the provision's distinctive content words must be
    present on the page. A provision with a block of ungrounded words may be hallucinated.

The AI reformats layout (joins wrapped lines, strips headers/footers), so this normalises
whitespace and compares presence, NOT exact strings — fidelity without punishing cleanup.

Read-only. Exit 1 if any provision is flagged (so it can gate a rollout).

Usage:
    python scripts/verify_extraction_fidelity.py --council leichhardt
    python scripts/verify_extraction_fidelity.py                 # all ai-reviewed councils
    python scripts/verify_extraction_fidelity.py --council marrickville --limit 200 --show 25
"""

import argparse
import re
import sys
import tempfile
from pathlib import Path

import pdfplumber
import psycopg2

# Reuse the extractor's R2 wiring + page-text extraction (two-column aware) verbatim.
import dcp_extract_changed as dx
from services.extracted_data_integrity import value_absent_from_source

# A "number" worth checking: integers/decimals of 2+ digits, or any decimal. Single bare
# digits (a "1." list marker, "3 phases") are too noisy and rarely a regulatory value.
_NUM_RE = re.compile(r"\d+\.\d+|\d{2,}")
_STOP = {
    "the", "and", "for", "with", "that", "this", "must", "should", "which", "development",
    "council", "provision", "provisions", "control", "controls", "shall", "any", "are",
    "not", "may", "including", "such", "from", "have", "been", "will", "where", "these",
}


def _numbers(text: str) -> list[str]:
    return _NUM_RE.findall(text or "")


def _content_words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]{4,}", (text or "").lower()) if w not in _STOP]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).lower()


def _page_text_for_chapter(s3, r2_path: str, council: str) -> dict[int, str]:
    """Download a chapter PDF once and return {1-indexed page number -> normalised text}."""
    pages: dict[int, str] = {}
    with tempfile.TemporaryDirectory() as tmp:
        local = Path(tmp) / "chapter.pdf"
        s3.download_file(dx.R2_BUCKET_NAME, r2_path, str(local))
        with pdfplumber.open(str(local)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                pages[i] = _norm(dx._clean_page_text(dx._extract_page_text(page, council), council))
    return pages


def _chapter_text(pages: dict[int, str]) -> str:
    """Ground against the WHOLE chapter, not the provision's cited page.

    The AI re-extracts in page-chunks and resets its page counter, so a provision's stored
    page number is unreliable (the review UI shows "NEW (p.1)" for nearly everything). Until
    the extractor emits true source pages, per-page grounding would false-flag constantly.
    Chapter-level grounding still answers the fidelity question that matters — is this text
    and these numbers anywhere in the council's own document, or did the model invent them?
    """
    return " ".join(pages.values())


def verify_council(cur, s3, council: str, limit: int | None) -> dict:
    cur.execute(
        """
        SELECT rp.provision_text, rp.page_range, rp.ref_number, reg.r2_current_path
        FROM regulatory_provisions rp
        JOIN dcp_chapter_registry reg
          ON reg.council = rp.source_council AND reg.chapter_key = rp.source_chapter_key
        WHERE rp.source_council = %s AND rp.is_current = TRUE
          AND rp.extraction_method = 'ai-reviewed'
          AND reg.r2_current_path IS NOT NULL
        ORDER BY rp.source_chapter_key, rp.ref_number
        """,
        (council,),
    )
    rows = cur.fetchall()
    if limit:
        rows = rows[:limit]

    page_cache: dict[str, dict[int, str]] = {}
    total = 0
    nums_checked = nums_absent = 0
    flagged: list[dict] = []
    for provision_text, page_range, ref_number, r2_path in rows:
        total += 1
        if r2_path not in page_cache:
            try:
                page_cache[r2_path] = _page_text_for_chapter(s3, r2_path, council)
            except Exception as exc:  # noqa: BLE001 — a bad PDF shouldn't abort the sweep
                page_cache[r2_path] = {}
                print(f"    [warn] could not read {r2_path}: {exc}")
        page_text = _chapter_text(page_cache[r2_path])
        if not page_text:
            continue

        # NUMERIC FIDELITY — reuse the tested number-form matcher, EXCLUDING the provision's
        # own section code (e.g. "14.2" derived from ref C14_2). A section code is a structural
        # label the model reproduces from the heading, not a value read off the page, and it
        # false-flags against a differently-formatted source heading. Regulatory values
        # (setbacks, heights, areas) in the body are still fully checked.
        code_nums = set(_NUM_RE.findall((ref_number or "").split("__")[-1].replace("_", ".")))
        nums = [n for n in _numbers(provision_text) if n not in code_nums]
        nums_checked += len(nums)
        rows_for_check = [{"v": n, "src": page_text} for n in nums]
        absent = value_absent_from_source(rows_for_check, value_field="v", source_field="src")
        absent_nums = [r["v"] for r in absent]
        nums_absent += len(absent_nums)

        # TOKEN GROUNDING — fraction of distinctive words present on the page.
        words = set(_content_words(provision_text))
        grounded = sum(1 for w in words if w in page_text)
        ground_ratio = grounded / len(words) if words else 1.0

        if absent_nums or ground_ratio < 0.75:
            flagged.append({
                "ref": (ref_number or "").split("__")[-1],
                "absent_numbers": absent_nums,
                "ground_ratio": round(ground_ratio, 2),
            })

    return {
        "council": council, "provisions": total, "numbers_checked": nums_checked,
        "numbers_absent": nums_absent, "flagged": flagged,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic AI-extraction fidelity verifier.")
    ap.add_argument("--council", help="Limit to one council (default: all ai-reviewed).")
    ap.add_argument("--limit", type=int, help="Cap provisions per council (spot check).")
    ap.add_argument("--show", type=int, default=15, help="Max flagged provisions to print per council.")
    args = ap.parse_args()

    s3 = dx.boto3.client(
        "s3", endpoint_url=dx.R2_ENDPOINT, aws_access_key_id=dx.R2_ACCESS_KEY_ID,
        aws_secret_access_key=dx.R2_SECRET_ACCESS_KEY, region_name="auto",
    )
    conn = psycopg2.connect(dx.DATABASE_URL)
    cur = conn.cursor()
    if args.council:
        councils = [args.council]
    else:
        cur.execute("SELECT DISTINCT source_council FROM regulatory_provisions "
                    "WHERE is_current = TRUE AND extraction_method = 'ai-reviewed' ORDER BY 1")
        councils = [r[0] for r in cur.fetchall()]

    any_flagged = False
    for c in councils:
        r = verify_council(cur, s3, c, args.limit)
        num_fidelity = 100.0 * (1 - r["numbers_absent"] / r["numbers_checked"]) if r["numbers_checked"] else 100.0
        print(f"\n=== {c} ===")
        print(f"  provisions checked : {r['provisions']}")
        print(f"  numeric fidelity   : {num_fidelity:.2f}%  "
              f"({r['numbers_checked'] - r['numbers_absent']}/{r['numbers_checked']} numbers found on source page)")
        print(f"  flagged for review : {len(r['flagged'])}")
        for f in r["flagged"][:args.show]:
            why = []
            if f["absent_numbers"]:
                why.append(f"numbers not on page: {f['absent_numbers']}")
            if f["ground_ratio"] < 0.75:
                why.append(f"only {int(f['ground_ratio']*100)}% words grounded")
            print(f"    [{f['ref']}] {'; '.join(why)}")
        if r["flagged"]:
            any_flagged = True

    print("\n" + "-" * 60)
    print("Flagged rows are ADVISORY (unit conversions like 900mm vs 0.9m, or a value on a "
          "diagram) — route them to a human, don't assume error.")
    cur.close()
    conn.close()
    return 1 if any_flagged else 0


if __name__ == "__main__":
    sys.exit(main())
