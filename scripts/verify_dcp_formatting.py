#!/usr/bin/env python3
"""
verify_dcp_formatting.py — DCP provision text artifact detector

Onboarding verification tool. Run after enrichment pipeline completes for a new council.
Reads DB credentials from .env.local (NEXT_PUBLIC_SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY).
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
import json
import os
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path


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


def load_env(root: Path) -> dict:
    """Load .env.local key=value pairs (no shell expansion)."""
    env_file = root / ".env.local"
    if not env_file.exists():
        raise FileNotFoundError(f".env.local not found at {env_file}")
    env = {}
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def fetch_provisions(supabase_url: str, service_key: str, council: str, limit: int) -> list[dict]:
    """Fetch random actionable provisions for council from Supabase REST API."""
    council_filter = council.lower()
    url = (
        f"{supabase_url.rstrip('/')}/rest/v1/regulatory_provisions"
        f"?former_council=ilike.{council_filter}"
        f"&v2_is_actionable=eq.true"
        f"&select=id,provision_text,v2_topic"
        f"&limit={limit}"
        f"&order=random()"
    )
    req = urllib.request.Request(url)
    req.add_header("apikey", service_key)
    req.add_header("Authorization", f"Bearer {service_key}")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_topic_distribution(supabase_url: str, service_key: str, council: str) -> list[dict]:
    """Fetch topic counts for the council (all provisions, not just sample)."""
    council_filter = council.lower()
    # Supabase doesn't natively do GROUP BY, but we can fetch all topics and count in Python.
    # Limit to 2000 to avoid timeout; enough for a distribution check.
    url = (
        f"{supabase_url.rstrip('/')}/rest/v1/regulatory_provisions"
        f"?former_council=ilike.{council_filter}"
        f"&v2_is_actionable=eq.true"
        f"&select=v2_topic"
        f"&limit=2000"
    )
    req = urllib.request.Request(url)
    req.add_header("apikey", service_key)
    req.add_header("Authorization", f"Bearer {service_key}")
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        rows = json.loads(resp.read().decode("utf-8"))
    return rows


def fetch_duplicate_is_current(supabase_url: str, service_key: str, council: str) -> int:
    """Count provisions with NULL source_chapter_key and is_current=True.

    These are first-pass extractions that cannot be retired by the pipeline automatically.
    A non-zero count means manual retirement is needed if chapters are re-extracted.
    """
    council_filter = council.lower()
    url = (
        f"{supabase_url.rstrip('/')}/rest/v1/regulatory_provisions"
        f"?former_council=ilike.{council_filter}"
        f"&source_chapter_key=is.null"
        f"&is_current=eq.true"
        f"&select=id"
        f"&limit=1"
        # Use Prefer: count=exact to get total without fetching all rows
    )
    req = urllib.request.Request(url)
    req.add_header("apikey", service_key)
    req.add_header("Authorization", f"Bearer {service_key}")
    req.add_header("Accept", "application/json")
    req.add_header("Prefer", "count=exact")
    with urllib.request.urlopen(req, timeout=30) as resp:
        content_range = resp.headers.get("Content-Range", "")
        # Content-Range: 0-0/N  — parse N
        if "/" in content_range:
            try:
                return int(content_range.split("/")[1])
            except (ValueError, IndexError):
                pass
        return len(json.loads(resp.read().decode("utf-8")))


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

    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent

    try:
        env = load_env(project_root / "frontend-nextjs")
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    supabase_url = env.get("NEXT_PUBLIC_SUPABASE_URL", "")
    service_key = env.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url or not service_key:
        print("ERROR: NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing from .env.local", file=sys.stderr)
        sys.exit(2)

    overall_pass = True

    # ─── Section 1: Text artifact checks ─────────────────────────────────────
    print(f"\nFetching {limit} random actionable provisions for '{council}'...")
    try:
        provisions = fetch_provisions(supabase_url, service_key, council, limit)
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
            topic_rows = fetch_topic_distribution(supabase_url, service_key, council)
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
            null_chapter_count = fetch_duplicate_is_current(supabase_url, service_key, council)
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
