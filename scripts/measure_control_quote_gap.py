#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no script measures WHY a control's
# quote fails to match the corpus. Checked: scripts/link_controls_to_provisions.py
# (#867) produces the outcome buckets but stops at "no provision contains the
# quote"; scripts/validate_controls_provenance.py (#866) classifies provenance
# from the repo, never the corpus; scripts/verify_setback_source_texts.py dumps
# text for a human; scripts/validate_dcp_health.py checks link integrity, not
# quote presence. This answers the follow-on question those leave open.
"""Why does a control's quoted source_text not appear in its council's provisions?

WHY THIS EXISTS
---------------
DQ-38 originally asserted that the 545 unmatched controls belong to councils
"whose specific chapter was never ingested". That was written without measuring
it, and it is false for most of them — Marrickville has 8,413 provisions loaded,
Ashfield 7,429, Woollahra 6,546. This script replaces the assertion with numbers,
and is committed rather than run once so the correction stays falsifiable.

WHAT IT MEASURES — two independent tests over the same rows
-----------------------------------------------------------
1. CHAPTER COVERAGE. Controls carry ``source_chapter_key``
   ('chapter-f-dev-category'); provisions carry ``document_id``
   ('Inner_West_Ashfield_DCP_2016__chapter_f_dev_category'). The vocabularies
   differ by separator, council prefix and year only, so once that noise is
   stripped a chapter key can be tested against the ingested document set.
   A "chapter_ingested" verdict DISPROVES "the chapter wasn't loaded" for that row.

2. VERBATIM-NESS. The longest contiguous run of words the quote shares with the
   best provision in that council, as a fraction of the quote's length. A run of
   ~1.0 means the sentence IS in the corpus and only punctuation/OCR blocked the
   substring match; ~0.0 means it is not there in any recognisable form.

WHAT IT DOES NOT ESTABLISH — stated because the first version of this finding
over-read its own evidence
--------------------------------------------------------------------------
A low verbatim band is equally consistent with "someone summarised the clause in
their own words" and with "that sentence is absent from the ingested text". This
script CANNOT tell those apart, and does not claim to. It reports the bands and
one weak side-signal (source_text that OPENS with a document citation is editorial
framing a PDF sentence would not contain) and leaves the cause open.

Two limits of test 1, so its number is not over-read: it compares identifier
token-sets, so a chapter whose key diverges by more than separators reads as "not
ingested" when it is present, and two chapters sharing a token-set could read as
ingested when the wrong one is. ``section_ref`` was tried as the test first and
abandoned — 0 of 530 control section_refs exist as a ref_number in their council,
because the two columns use unrelated vocabularies. That 0 measures the vocabulary
gap, not the corpus.

ADVISORY ONLY. Exit code is 0 whatever it finds: every band it reports is a
statement about corpus coverage, and failing on absent corpus would fail on
someone else's un-done extraction work rather than on a defect here.
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher

# A quote shorter than this is not distinctive; link_controls_to_provisions.py
# excludes the same rows, so the two scripts describe the same population.
MIN_QUOTE_CHARS = 30

# Extractors append a citation ("... (Ashfield DCP 2016 DS18.5)") that is not part
# of the provision text. Same pattern as the linker, for the same reason.
_CITATION = re.compile(
    r"\s*\([^()]*(?:dcp|lep|sepp|part|table|clause|s\d)[^()]*\)\s*$", re.I)

# A document name in the OPENING of the sentence. A clause inside a PDF does not
# name its own document; a person writing a note about it does.
_OPENS_WITH_DOC = re.compile(r"^[a-z' ]{3,40}(dcp|lep|sepp)\b", re.I)

# Tokens naming the council or instrument rather than the chapter. They appear on
# one side or the other inconsistently, so they cannot be part of the comparison.
_NOISE = {"dcp", "lep", "sepp", "inner", "west", "city", "of", "council", "the",
          "shire", "area", "local", "government"}
_YEAR = re.compile(r"^(19|20)\d{2}$")

# Only the top-N provisions by word overlap are scored with SequenceMatcher —
# scoring all 8,000+ of a large council against every quote is quadratic for no
# gain, since a provision sharing few words cannot hold a long contiguous run.
CANDIDATES = 40

BANDS = (
    (0.8, "verbatim_present_substring_failed_on_punctuation"),
    (0.4, "partly_verbatim"),
    (0.2, "fragmentary"),
    (0.0, "not_present_in_any_recognisable_form"),
)


def normalise(text: str | None) -> str:
    """Lowercase and collapse whitespace. Nothing else — no stemming, no fuzzing."""
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def quoted_clause(source_text: str | None) -> str:
    """The part of source_text that should appear in the provision itself."""
    return _CITATION.sub("", normalise(source_text)).strip()


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9.%]+", text)


def chapter_tokens(key: str | None) -> set[str]:
    """Comparable tokens of a chapter key or document id, council/year stripped."""
    parts = [p for p in re.split(r"[^a-z0-9]+", (key or "").lower()) if p]
    return {p for p in parts if p not in _NOISE and not _YEAR.match(p)}


def longest_run_fraction(quote: str, provision_words: list[str]) -> float:
    """Longest contiguous shared word-run, as a fraction of the quote's length.

    Pure and DB-free so both ends are testable: an identical string must score
    1.0 and a disjoint one 0.0.
    """
    qw = words(quote)
    if not qw or not provision_words:
        return 0.0
    match = SequenceMatcher(None, qw, provision_words, autojunk=False)
    return match.find_longest_match(0, len(qw), 0, len(provision_words)).size / len(qw)


def band_for(fraction: float) -> str:
    """The named band a run-fraction falls in. Always returns one — never None."""
    for threshold, name in BANDS:
        if fraction >= threshold:
            return name
    return BANDS[-1][1]  # unreachable: the last threshold is 0.0


def _fetch_council_provisions(cur, lga: str) -> list[tuple]:
    """(id, normalised_text, document_id) for one council's served provisions.

    is_current AND v2_is_actionable mirrors the linker's candidate set exactly, so
    "unmatched here" means the same population as "unmatched there".
    """
    cur.execute(
        """SELECT p.id, p.provision_text, p.document_id
           FROM regulatory_provisions p
           LEFT JOIN lga_registry r ON r.slug = %s AND r.is_active
           WHERE p.is_current AND p.v2_is_actionable
             AND (p.source_council = %s
               OR lower(p.source_council) = lower(r.display_name)
               OR lower(replace(p.source_council, ' ', '_')) = %s)""",
        (lga, lga, lga),
    )
    return [(pid, normalise(text), doc) for pid, text, doc in cur.fetchall()]


def measure(cur) -> tuple[Counter, dict, Counter, Counter]:
    """Walk every control; measure only those the linker could not match."""
    # DELIBERATELY UNFILTERED on is_current. This must describe the SAME population
    # as link_controls_to_provisions.py, which reads all 1,069 rows, or the two
    # scripts' numbers stop reconciling and DQ-38's table becomes unverifiable. The
    # column is selected and the split is reported instead, so the 80 superseded
    # rows are visible rather than silently mixed in.
    cur.execute(
        """SELECT id, lga, source_text, source_chapter_key, extraction_method,
                  is_current
           FROM dcp_setback_controls ORDER BY lga, id"""
    )
    columns = [d[0] for d in cur.description]
    by_lga: dict[str, list[dict]] = defaultdict(list)
    for record in cur.fetchall():
        row = dict(zip(columns, record))
        by_lga[row["lga"]].append(row)

    totals: Counter = Counter()
    per_lga: dict[str, Counter] = defaultdict(Counter)
    missing_chapters: Counter = Counter()
    examples: Counter = Counter()

    for lga, rows in sorted(by_lga.items()):
        provisions = _fetch_council_provisions(cur, lga)
        if not provisions:
            # Councils with nothing ingested are the separate, already-measured
            # 450 — counted, then skipped, so they cannot inflate any band here.
            totals["skipped_council_has_no_provisions"] += len(rows)
            continue
        doc_tokens = [chapter_tokens(d) for d in {d for _, _, d in provisions if d}]
        scored = [(words(text), set(words(text))) for _, text, _ in provisions]

        for row in rows:
            quote = quoted_clause(row["source_text"])
            if len(quote) < MIN_QUOTE_CHARS:
                totals["skipped_quote_too_short"] += 1
                continue
            if any(quote in text for _, text, _ in provisions):
                totals["skipped_matched_exactly"] += 1
                continue

            totals["measured"] += 1
            totals["measured_is_current" if row["is_current"]
                   else "measured_superseded"] += 1
            key_tokens = chapter_tokens(row["source_chapter_key"])
            if not key_tokens:
                verdict = "no_chapter_key"
            elif any(key_tokens <= dt for dt in doc_tokens):
                verdict = "chapter_ingested"
            else:
                verdict = "chapter_not_ingested"
                missing_chapters[f"{lga}:{row['source_chapter_key']}"] += 1
            totals[verdict] += 1

            quote_words = set(words(quote))
            ranked = sorted(scored, key=lambda p: -len(quote_words & p[1]))[:CANDIDATES]
            best = 0.0
            for provision_words, _ in ranked:
                best = max(best, longest_run_fraction(quote, provision_words))
                if best >= 0.98:
                    break
            band = band_for(best)
            totals[band] += 1
            per_lga[lga][band] += 1
            if _OPENS_WITH_DOC.match(row["source_text"] or ""):
                totals["opens_with_document_citation"] += 1

    return totals, per_lga, missing_chapters, examples


def main() -> int:  # pragma: no cover - CLI entry point
    from dotenv import load_dotenv

    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set — nothing was measured, which is not a "
              "pass. Exiting 2.", file=sys.stderr)
        return 2
    import psycopg2

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '120000'")
    try:
        totals, per_lga, missing_chapters, _ = measure(cur)
    finally:
        conn.close()

    measured = totals["measured"]
    print("\n=== population ===")
    print(f"  measured (linker found no match, council HAS provisions): {measured:>5}")
    for key in ("skipped_matched_exactly", "skipped_council_has_no_provisions",
                "skipped_quote_too_short"):
        print(f"  {key:<44}: {totals[key]:>5}")
    print(f"  of the measured, is_current TRUE            : "
          f"{totals['measured_is_current']:>5}")
    print(f"  of the measured, superseded (is_current FALSE): "
          f"{totals['measured_superseded']:>5}")

    print("\n=== test 1: does a provision document exist for the control's chapter? ===")
    for key in ("chapter_ingested", "chapter_not_ingested", "no_chapter_key"):
        pct = 100.0 * totals[key] / max(1, measured)
        print(f"  {key:<40}: {totals[key]:>5}  ({pct:4.1f}%)")
    print("  'chapter_ingested' DISPROVES \"the chapter wasn't loaded\" for those rows.")

    print("\n=== test 2: how much of the quote appears verbatim ===")
    for _, name in BANDS:
        pct = 100.0 * totals[name] / max(1, measured)
        print(f"  {name:<52}: {totals[name]:>5}  ({pct:4.1f}%)")
    print("\n  A LOW band does not identify a cause. It is equally consistent with"
          "\n  'someone reworded the clause' and 'that sentence is not in the ingested"
          "\n  text'. This script cannot separate them and does not try.")

    pct = 100.0 * totals["opens_with_document_citation"] / max(1, measured)
    print(f"\n=== side-signal: source_text OPENS with a document citation ===")
    print(f"  {totals['opens_with_document_citation']:>5}  ({pct:4.1f}%)  "
          f"editorial framing a PDF sentence would not contain")

    print("\n=== per council (verbatim bands) ===")
    print(f"  {'lga':<24}{'verbatim':>10}{'partly':>9}{'fragment':>10}{'absent':>9}")
    for lga in sorted(per_lga, key=lambda l: -sum(per_lga[l].values())):
        counts = per_lga[lga]
        print(f"  {lga:<24}"
              f"{counts['verbatim_present_substring_failed_on_punctuation']:>10}"
              f"{counts['partly_verbatim']:>9}"
              f"{counts['fragmentary']:>10}"
              f"{counts['not_present_in_any_recognisable_form']:>9}")

    print("\n=== chapter keys with no ingested document (top 20) ===")
    for key, count in missing_chapters.most_common(20):
        print(f"  {count:>4}  {key}")

    print("\nADVISORY — exit 0 whatever was found. These are statements about corpus"
          "\ncoverage, not defects in this repo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
