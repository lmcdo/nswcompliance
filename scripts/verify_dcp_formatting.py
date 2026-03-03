#!/usr/bin/env python3
"""
verify_dcp_formatting.py — DCP provision text artifact detector

Onboarding verification tool. Run after enrichment pipeline completes for a new council.
Reads DB credentials from .env (DATABASE_URL).
Read-only — no auto-fixes.

Usage:
    python scripts/verify_dcp_formatting.py --council marrickville [--limit 50]

Pass gate: < 5% of sampled provisions have flagged artifact lines → no action needed
Fail gate: >= 5%                                                  → add config entry in
           lib/dcp-format-configs.ts, rerun to confirm pass gate

Exit codes:
    0 — pass gate met (< 5% artifacts)
    1 — fail gate triggered (>= 5% artifacts)
    2 — error (DB connection, no provisions found, etc.)
"""

import argparse
import os
import re
import sys
from collections import Counter
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv


# ─── Artifact heuristics ─────────────────────────────────────────────────────

# Line-level checks: each pattern is tested against every non-blank line in provision_text.
LINE_CHECKS = {
    "bare_page_numbers":     re.compile(r"^\d{1,3}$"),
    "hash_prefix_headers":   re.compile(r"^#\s*\d{1,3}\s+\w"),
    "chapter_prefix_lines":  re.compile(r"^Chapter [A-Z]\d*\b"),
    # Right-aligned running header: "Section Title      B1" (3+ spaces before a section code).
    "right_aligned_headers": re.compile(r"\s{3,}[A-Z]\d{1,2}\s*$"),
    # LaTeX math tokens from equation-editor DCPs (e.g., Marrickville)
    "latex_tokens":          re.compile(r"\\math|\{ , \}|\\star_|\^ \{"),
    # Word "Error! Reference source not found." cross-reference artifacts
    "word_cross_references": re.compile(r"Error! Reference source not found"),
    # Table of contents dotted leaders (e.g., "1.1  Site Analysis..............12")
    "toc_dotted_leaders":    re.compile(r"\.{5,}"),
    # Handled separately at provision level:
    "long_no_punctuation":   None,
    "short_provision":       None,
}

LONG_LINE_THRESHOLD = 200  # chars — line with no punctuation at end
SHORT_PROVISION_THRESHOLD = 20  # chars — entire provision_text (likely artifact/heading)
PASS_GATE_PCT = 5.0  # % of provisions allowed to have flagged lines


def check_provision(text: str) -> tuple[list[str], list[str]]:
    """Return (artifact_labels, flagged_line_samples) found in this provision text."""
    found = []
    flagged_lines = []
    lines = text.split("\n")

    # Provision-level: very short provision flagged as actionable
    stripped = text.strip()
    if len(stripped) < SHORT_PROVISION_THRESHOLD:
        found.append("short_provision")
        flagged_lines.append(f"(entire provision) {stripped!r}")

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        for label, pattern in LINE_CHECKS.items():
            if label == "long_no_punctuation":
                if len(line) > LONG_LINE_THRESHOLD and not re.search(r"[.!?;:,]$", line):
                    found.append(label)
                    flagged_lines.append(line[:80] + "...")
                continue
            if label == "short_provision":
                continue  # handled at provision level above
            if pattern and pattern.search(line):
                found.append(label)
                flagged_lines.append(line[:80])

    return found, flagged_lines


def get_db_connection():
    """Connect using DATABASE_URL from .env."""
    load_dotenv(Path(__file__).parent.parent / ".env")
    database_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set in .env")
    return psycopg2.connect(database_url)


def fetch_provisions(conn, council: str, limit: int) -> list[dict]:
    """Fetch random actionable provisions for council."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT id, provision_text, v2_topic
        FROM regulatory_provisions
        WHERE source_council = %s
          AND v2_is_actionable = TRUE
          AND is_current = TRUE
        ORDER BY random()
        LIMIT %s
        """,
        (council, limit),
    )
    return [dict(r) for r in cur.fetchall()]


def fetch_topic_distribution(conn, council: str) -> list[dict]:
    """Fetch topic rows for the council (all provisions, for distribution check)."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT v2_topic
        FROM regulatory_provisions
        WHERE source_council = %s
          AND v2_is_actionable = TRUE
          AND is_current = TRUE
        LIMIT 2000
        """,
        (council,),
    )
    return [dict(r) for r in cur.fetchall()]


def fetch_duplicate_is_current(conn, council: str) -> int:
    """Count provisions with NULL source_chapter_key and is_current=True.

    These are first-pass extractions that cannot be retired by the pipeline automatically.
    A non-zero count means manual retirement is needed if chapters are re-extracted.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE source_council = %s
          AND source_chapter_key IS NULL
          AND is_current = TRUE
        """,
        (council,),
    )
    return cur.fetchone()[0]


def print_config_skeleton(council: str, detected_labels: set[str]) -> None:
    """Print a dcp-format-configs.ts entry skeleton based on detected artifact types."""
    print("\n  ── Suggested dcp-format-configs.ts entry ──────────────────────────────────")
    print(f"  {council}: {{")

    skip_patterns = []
    skip_prefixes = []
    pre_replacements = []

    if "bare_page_numbers" in detected_labels:
        skip_patterns.append("    /^\\\\d{1,3}$/,              // bare page numbers")
    if "hash_prefix_headers" in detected_labels:
        skip_patterns.append("    /^#\\\\s*\\\\d{1,3}\\\\s+\\\\w/,     // hash-prefix running headers")
    if "right_aligned_headers" in detected_labels:
        skip_patterns.append("    /\\\\s{3,}[A-Z]\\\\d{1,2}\\\\s*$/,  // right-aligned section codes")
    if "chapter_prefix_lines" in detected_labels:
        pre_replacements.append("    { from: /^Chapter [A-Z]\\\\d*[^\\\\n]*\\\\n+/m, to: '' },  // chapter prefix line")

    # Running title — we can't auto-detect the exact string, note it
    if any(l in detected_labels for l in ["bare_page_numbers", "hash_prefix_headers"]):
        skip_prefixes.append("    'TODO: Add exact document title string (e.g. \"My Council DCP 2022\")',")

    if "latex_tokens" in detected_labels:
        pre_replacements.append("    // LaTeX math tokens — copy full block from marrickville entry in dcp-format-configs.ts")

    if skip_patterns:
        print("    skipLinePatterns: [")
        for p in skip_patterns:
            print(f"  {p}")
        print("    ],")
    if skip_prefixes:
        print("    skipLinePrefixes: [")
        for p in skip_prefixes:
            print(f"  {p}")
        print("    ],")
    if pre_replacements:
        print("    preProcessReplacements: [")
        for r in pre_replacements:
            print(f"  {r}")
        print("    ],")
    print("  },")
    print()
    print("  File: frontend-nextjs/lib/dcp-format-configs.ts")
    print("  Docs: docs/DCP_EXTRACTION_KNOWN_PATTERNS.md")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify DCP provision text formatting artifacts")
    parser.add_argument("--council", required=True, help="Council name (e.g. marrickville, ashfield)")
    parser.add_argument("--limit", type=int, default=50, help="Number of provisions to sample for text checks (default: 50)")
    parser.add_argument("--skip-topic-check", action="store_true", help="Skip topic distribution check (faster)")
    parser.add_argument("--skip-is-current-check", action="store_true", help="Skip is_current duplicate check")
    args = parser.parse_args()

    council = args.council.strip().lower()
    limit = max(10, min(args.limit, 500))

    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"ERROR connecting to DB: {e}", file=sys.stderr)
        sys.exit(2)

    overall_pass = True

    # ─── Section 1: Text artifact checks ─────────────────────────────────────
    print(f"\nFetching {limit} random actionable provisions for '{council}'...")
    try:
        provisions = fetch_provisions(conn, council, limit)
    except Exception as e:
        print(f"ERROR fetching provisions: {e}", file=sys.stderr)
        sys.exit(2)

    if not provisions:
        print(f"ERROR: No actionable provisions found for council='{council}'. Check the council name.", file=sys.stderr)
        sys.exit(2)

    total = len(provisions)
    print(f"Analysing {total} provisions...\n")

    label_counts: Counter = Counter()
    flagged_line_samples: Counter = Counter()
    provisions_with_artifacts = 0

    for prov in provisions:
        text = prov.get("provision_text", "") or ""
        labels, flagged_lines = check_provision(text)
        if labels:
            provisions_with_artifacts += 1
            label_counts.update(labels)
            flagged_line_samples.update(flagged_lines)

    pct = (provisions_with_artifacts / total) * 100
    detected_labels = {label for label, count in label_counts.items() if count > 0}

    print(f"=== 1. Text Artifact Checks: {council} ({total} provisions sampled) ===\n")
    max_label_len = max(len(k) for k in LINE_CHECKS) + 2
    for label in LINE_CHECKS:
        count = label_counts.get(label, 0)
        bar = f"{count}/{total} ({count/total*100:.0f}%)"
        flag = " <-- FAIL" if count / total * 100 >= PASS_GATE_PCT else ""
        print(f"  {label:<{max_label_len}} {bar}{flag}")

    print()
    print(f"  Provisions with any artifact:  {provisions_with_artifacts}/{total} ({pct:.1f}%)")

    if flagged_line_samples:
        print("\n  Top flagged lines:")
        for line_sample, count in flagged_line_samples.most_common(8):
            print(f"    {count:>3}x  {line_sample!r}")

    print()
    format_pass = pct < PASS_GATE_PCT
    if format_pass:
        print(f"  PASS  ({pct:.1f}% < {PASS_GATE_PCT}% gate) — no config entry needed")
    else:
        overall_pass = False
        print(f"  FAIL  ({pct:.1f}% >= {PASS_GATE_PCT}% gate)")
        print_config_skeleton(council, detected_labels)

    # ─── Section 2: Topic distribution check ─────────────────────────────────
    if not args.skip_topic_check:
        print(f"\n=== 2. Topic Distribution Check: {council} ===\n")
        try:
            topic_rows = fetch_topic_distribution(conn, council)
            topic_counts: Counter = Counter()
            for row in topic_rows:
                topic_counts[row.get("v2_topic") or "(null)"] += 1

            total_topics = sum(topic_counts.values())
            if total_topics == 0:
                print("  WARNING: No actionable provisions found for topic check.")
            else:
                print(f"  Total actionable provisions fetched: {total_topics}")
                if total_topics == 2000:
                    print("  NOTE: Capped at 2000 — percentages may be approximate for large councils.")
                print()
                topic_pass = True
                for topic, count in topic_counts.most_common():
                    pct_t = count / total_topics * 100
                    flag = ""
                    if pct_t > 40:
                        flag = "  <-- WARNING: >40% suggests topic mapping issue"
                        topic_pass = False
                        overall_pass = False
                    print(f"  {topic or '(null)':<35} {count:>5} ({pct_t:5.1f}%){flag}")

                if topic_counts.get("(null)", 0) > 0:
                    print(f"\n  WARNING: {topic_counts['(null)']} provisions have NULL v2_topic.")
                    print("  These will not appear in topic-grouped UI views.")
                    overall_pass = False

                print()
                if topic_pass:
                    print("  PASS  — topic distribution looks reasonable")
                else:
                    print("  FAIL  — review topic mapping config for this council")
        except Exception as e:
            print(f"  WARNING: Topic distribution check failed: {e}")

    # ─── Section 3: is_current retirement check ───────────────────────────────
    if not args.skip_is_current_check:
        print(f"\n=== 3. is_current Retirement Check: {council} ===\n")
        try:
            null_chapter_count = fetch_duplicate_is_current(conn, council)
            print(f"  Provisions with is_current=True and NULL source_chapter_key: {null_chapter_count}")
            if null_chapter_count == 0:
                print("  PASS  — all current provisions have a source_chapter_key (pipeline can retire them)")
            else:
                print(f"  NOTE  — {null_chapter_count} first-pass provisions cannot be retired by the pipeline.")
                print("  If any chapters are re-extracted, manually retire these old provisions.")
                print("  See docs/DCP_EXTRACTION_KNOWN_PATTERNS.md §7 for the retirement query.")
                # This is a NOTE, not a FAIL — retirement is a manual step, not a blocking QA issue
        except Exception as e:
            print(f"  WARNING: is_current check failed: {e}")

    # ─── Final result ─────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    if overall_pass:
        print(f"  OVERALL PASS — {council} is ready for import")
        print(f"{'=' * 60}\n")
        return 0
    else:
        print(f"  OVERALL FAIL — fix the issues above before importing {council}")
        print(f"{'=' * 60}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
