#!/usr/bin/env python3
"""
DCP Chapter PDF Profiler
========================
Run BEFORE writing registry or config for a new DCP chapter.
Profiles a single PDF to determine the best extraction method.

Usage:
    python3 scripts/survey_dcp.py path/to/chapter.pdf
    python3 scripts/survey_dcp.py path/to/chapter.pdf --verbose

Output:
    - Page count
    - SECTION_RE hit rate + 5 sample matched headers
    - First 3 pages where SECTION_RE found NO match (catches multi-line header patterns)
    - Estimated TOC/index pages (pages containing "contents" or "index" near top)
    - Recommended extraction method: regex or page_ranges

Decision guide:
    SECTION_RE hit rate >= 50%  →  use regex extraction (normal path)
    SECTION_RE hit rate <  50%  →  add page_ranges to COUNCIL_PAGE_RANGES
                                   (multi-line header pattern, like Waverley)
"""

import argparse
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

try:
    import pdfplumber
except ImportError:
    print("[ERROR] pdfplumber not installed. Run: pip install pdfplumber")
    sys.exit(1)

# Same regex as DCPExtractor in dcp_extract_changed.py
SECTION_RE = re.compile(r'^([A-Z]?\d+(?:\.\d+)*)\s+([A-Z][^\n]+)$', re.MULTILINE)

TOC_KEYWORDS = re.compile(r'\b(contents|table of contents|index)\b', re.IGNORECASE)


def survey(pdf_path: Path, verbose: bool = False) -> None:
    print(f"\nSurveying: {pdf_path.name}")
    print("=" * 60)

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Pages: {total_pages}")

        matched_pages: list[int] = []
        unmatched_pages: list[int] = []
        sample_headers: list[tuple[int, str, str]] = []  # (page, code, title)
        toc_pages: list[int] = []

        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""

            # Check for TOC pages (first 200 chars of text)
            preview = text[:200].lower()
            if TOC_KEYWORDS.search(preview):
                toc_pages.append(page_num)

            match = SECTION_RE.search(text)
            if match:
                matched_pages.append(page_num)
                if len(sample_headers) < 5:
                    sample_headers.append((page_num, match.group(1), match.group(2).strip()))
            else:
                unmatched_pages.append(page_num)

            if verbose:
                status = "MATCH" if match else "     "
                print(f"  p{page_num:>3} {status}", end="\r")

        print()  # clear progress line

        # ── Results ────────────────────────────────────────────────────────────

        hit_count = len(matched_pages)
        hit_rate = hit_count / total_pages if total_pages > 0 else 0.0

        print(f"\nSECTION_RE hit rate: {hit_count}/{total_pages} pages ({hit_rate:.0%})")

        print("\nSample matched headers (up to 5):")
        if sample_headers:
            for page_num, code, title in sample_headers:
                print(f"  p{page_num}: [{code}] {title}")
        else:
            print("  (none)")

        print("\nFirst 3 unmatched pages:")
        for p in unmatched_pages[:3]:
            with pdfplumber.open(pdf_path) as pdf2:
                snippet = (pdf2.pages[p - 1].extract_text() or "")[:120].replace("\n", " ")
            print(f"  p{p}: {snippet!r}")

        if toc_pages:
            print(f"\nEstimated TOC/index pages: {toc_pages}")
        else:
            print("\nNo TOC/index pages detected in first 200 chars.")

        # ── Recommendation ─────────────────────────────────────────────────────

        print("\n" + "─" * 60)
        min_sections = max(2, total_pages // 30)

        if hit_rate >= 0.5:
            print(f"RECOMMENDATION: Use REGEX extraction (normal path)")
            print(f"  SECTION_RE hit rate {hit_rate:.0%} ≥ 50% threshold")
            expected_sections = hit_count
            print(f"  Expected ~{expected_sections} sections (sanity gate: ≥{min_sections})")
            if expected_sections < min_sections:
                print(f"  [WARN] Expected sections < sanity gate — may trigger page_ranges fallback")
        else:
            print(f"RECOMMENDATION: Add PAGE_RANGES config for this council")
            print(f"  SECTION_RE hit rate {hit_rate:.0%} < 50% threshold")
            print(f"  Headers are likely multi-line — regex cannot detect them reliably")
            print(f"  Sanity gate will fire ({hit_count} sections < {min_sections} minimum)")
            print(f"  → Add COUNCIL_PAGE_RANGES entry in dcp_extract_changed.py")

        print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Profile a DCP chapter PDF to determine the best extraction method."
    )
    parser.add_argument("pdf_path", type=Path, help="Path to the DCP chapter PDF")
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show per-page match status"
    )
    args = parser.parse_args()

    if not args.pdf_path.exists():
        print(f"[ERROR] File not found: {args.pdf_path}")
        sys.exit(1)

    if not args.pdf_path.suffix.lower() == ".pdf":
        print(f"[WARN] File does not have .pdf extension: {args.pdf_path}")

    survey(args.pdf_path, verbose=args.verbose)


if __name__ == "__main__":
    main()
