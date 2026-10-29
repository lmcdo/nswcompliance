#!/usr/bin/env python3
# prior-art-checked: OC-8's other checks (outreach_claim_checks.every_served_number_is_cited, DQ-39, the
# link query) prove a served number HAS a page, a sentence and a link; none opens the page and compares
# the words. The comparison is scripts/dcp_quote_status.classify, the same one that gates serving
# (migration 120), so the claim check and the serve gate cannot disagree. Separate module because
# outreach_claim_checks.py is past the 500-line limit.
"""OC-8, words part: every served number's sentence is printed word for word on its cited page.

Reads the served rules through the serve path (outreach_claim_checks.served_entries), opens each
rule's chapter PDF, and re-runs the word check live. It does not trust quote_status: a check must
call the machine it checks.

  python scripts/oc8_quote_words.py      # prints the result; exit 1 on FAIL or UNKNOWN
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import dcp_quote_status as Q  # noqa: E402

PagesFor = Callable[[str, str], "list[str] | None"]


def mismatches(entries: list[tuple[str, dict, dict]], pages_for: PagesFor) -> tuple[int, list[str]]:
    """(numbers checked, 'lga/type: verdict' for every served number whose words are not on its page)."""
    numbers, bad = 0, []
    for lga, e, _urls in entries:
        if e.get("value_min") is None and e.get("value_max") is None:
            continue  # a "no set number" note has no number to prove (same rule as every_served_number_is_cited)
        numbers += 1
        pages = pages_for(lga, e.get("source_chapter_key") or "")
        verdict = Q.classify(e.get("source_text"), pages, e.get("pdf_page"))
        if verdict != "verbatim":
            bad.append(f"{lga}/{e.get('semantic_type') or e.get('type')}: {verdict}")
    return numbers, bad


def _registry_pages() -> PagesFor:
    import psycopg2

    conn = psycopg2.connect(os.environ["DATABASE_URL"], options="-c statement_timeout=30000")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT council, chapter_key, r2_current_path FROM dcp_chapter_registry "
                        "WHERE is_active AND r2_current_path IS NOT NULL")
            paths: dict[tuple[str, str], str | None] = {}
            for c, k, p in cur.fetchall():
                # Two active PDFs for one council+chapter: the rule's source is ambiguous, so it is
                # not proven by either (None -> no_source -> red). 0 such pairs on 2026-10-29.
                paths[(c, k)] = p if (c, k) not in paths or paths[(c, k)] == p else None
    finally:
        conn.close()
    s3, bucket = Q._r2()
    cache: dict[str, list[str] | None] = {}

    def pages_for(lga: str, chapter_key: str) -> list[str] | None:
        path = paths.get((lga, chapter_key))
        if not path:
            return None
        if path not in cache:
            cache[path] = Q._page_texts(s3, bucket, path)
        return cache[path]

    return pages_for


def check():
    """OC-8 result tuple (status, message), in outreach_claim_checks' PASS/FAIL/UNKNOWN terms."""
    import logging

    import outreach_claim_checks as occ

    entries, why = occ.served_entries()
    if entries is None:
        return occ.UNKNOWN, f"served words: {why}"
    pdf_log = logging.getLogger("pypdf")
    level = pdf_log.level
    pdf_log.setLevel(logging.CRITICAL + 1)  # pypdf warns on every odd font; nothing else is silenced
    try:
        numbers, bad = mismatches(entries, _registry_pages())
    except Exception as exc:  # noqa: BLE001 - a source that cannot be read proves nothing
        return occ.UNKNOWN, f"served words: chapter PDFs could not be read ({exc})"
    finally:
        pdf_log.setLevel(level)
    if numbers == 0:
        return occ.UNKNOWN, "served words: the serve path returned no numbers, so nothing was checked"
    return ((occ.PASS if not bad else occ.FAIL),
            f"served numbers whose sentence is not word for word on its cited PDF page: "
            f"{len(bad)} of {numbers} {bad[:4]}")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    status, msg = check()
    print(status, msg)
    sys.exit(0 if status == "PASS" else 1)
