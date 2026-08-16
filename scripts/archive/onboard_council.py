#!/usr/bin/env python3
"""
LGA Onboarding Pipeline — single command to run steps 2.X.5 through 2.X.12.

Prerequisite (manual):
  1. Find PDF URLs on council website
  2. Download PDFs to local directory
  3. Survey PDFs: python scripts/survey_dcp.py <pdf>
  4. Update populate script with real URLs

This script then runs:
  Step 1: Populate registry (runs populate_{council}_registry.py)
  Step 2: Extract provisions (runs dcp_extract_changed.py --council X)
  Step 3: QA formatting (runs verify_dcp_formatting.py --council X)
  Step 4: Enrichment pipeline (actionability, topics, layers)
  Step 5: Rule extraction (deterministic)
  Step 6: Report stats

Usage:
    python scripts/onboard_council.py city_of_sydney --dry-run
    python scripts/onboard_council.py ku_ring_gai
    python scripts/onboard_council.py woollahra --skip-populate --skip-extract
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
REPORT_DIR = ROOT / "enrichment" / "onboarding_reports"


def run_step(name: str, cmd: list, dry_run: bool = False, max_retries: int = 2) -> dict:
    """
    Run a pipeline step with retry. Returns result dict:
      {"step": name, "status": "passed"|"failed", "attempts": N, "output": str, "error": str}
    """
    print(f"\n{'='*60}")
    print(f"STEP: {name}")
    print(f"CMD:  {' '.join(cmd)}")
    print(f"{'='*60}")

    if dry_run:
        print("[DRY RUN -- skipped]")
        return {"step": name, "status": "passed", "attempts": 0, "output": "", "error": ""}

    for attempt in range(1, max_retries + 1):
        print(f"\n  Attempt {attempt}/{max_retries}...")
        result = subprocess.run(
            cmd, cwd=str(ROOT),
            capture_output=True, text=True,
            timeout=600,  # 10 min max per step
        )

        # Print stdout live
        if result.stdout:
            print(result.stdout)

        if result.returncode in (0, 2):  # 0=success, 2="changes detected"
            print(f"  PASSED (attempt {attempt})")
            return {
                "step": name, "status": "passed", "attempts": attempt,
                "output": result.stdout[-2000:] if result.stdout else "",
                "error": "",
            }

        print(f"  FAILED (exit {result.returncode}, attempt {attempt}/{max_retries})")
        if result.stderr:
            print(f"  STDERR: {result.stderr[-500:]}")

        if attempt < max_retries:
            print(f"  Retrying...")

    # Failed after all retries
    return {
        "step": name, "status": "failed", "attempts": max_retries,
        "output": result.stdout[-2000:] if result.stdout else "",
        "error": result.stderr[-2000:] if result.stderr else f"Exit code {result.returncode}",
    }


def write_report(council: str, results: list, dry_run: bool = False):
    """Write JSON report of pipeline run. This is what you check."""
    REPORT_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"{council}_{ts}.json"

    failed = [r for r in results if r["status"] == "failed"]
    passed = [r for r in results if r["status"] == "passed"]

    report = {
        "council": council,
        "timestamp": ts,
        "dry_run": dry_run,
        "summary": {
            "total_steps": len(results),
            "passed": len(passed),
            "failed": len(failed),
            "status": "FAILED" if failed else "PASSED",
        },
        "failed_steps": [
            {"step": r["step"], "attempts": r["attempts"], "error": r["error"][:1000]}
            for r in failed
        ],
        "all_steps": [
            {"step": r["step"], "status": r["status"], "attempts": r["attempts"]}
            for r in results
        ],
    }

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary to terminal
    print(f"\n{'#'*60}")
    if failed:
        print(f"# PIPELINE FAILED: {council}")
        print(f"# {len(failed)} step(s) failed after 2 attempts each:")
        for r in failed:
            print(f"#   - {r['step']}")
            if r["error"]:
                # First line of error only
                print(f"#     Error: {r['error'].strip().split(chr(10))[-1][:100]}")
    else:
        print(f"# PIPELINE PASSED: {council}")
        print(f"# {len(passed)} steps completed")
    print(f"# Report: {report_path}")
    print(f"{'#'*60}")

    return report_path


def main():
    parser = argparse.ArgumentParser(description="LGA Onboarding Pipeline")
    parser.add_argument("council", help="Council name (e.g., city_of_sydney, ku_ring_gai, north_sydney)")
    parser.add_argument("--dry-run", action="store_true", help="Show commands without running")
    parser.add_argument("--skip-populate", action="store_true", help="Skip registry population")
    parser.add_argument("--skip-extract", action="store_true", help="Skip provision extraction")
    parser.add_argument("--skip-qa", action="store_true", help="Skip QA formatting check")
    parser.add_argument("--start-from", type=int, default=1, help="Start from step N (1-6)")
    args = parser.parse_args()

    council = args.council
    py = sys.executable

    # Resolve populate script name (underscores vs hyphens)
    populate_script = SCRIPTS / f"populate_{council}_registry.py"
    if not populate_script.exists():
        # Try with hyphens
        alt = SCRIPTS / f"populate_{council.replace('_', '-')}_registry.py"
        if alt.exists():
            populate_script = alt
        else:
            print(f"WARNING: No populate script found at {populate_script}")

    steps = []

    # Step 1: Populate registry
    if not args.skip_populate and args.start_from <= 1:
        if populate_script.exists():
            steps.append(("1. Populate registry", [py, str(populate_script)]))
        else:
            print(f"SKIP Step 1: No populate script for {council}")

    # Step 2: Extract provisions
    if not args.skip_extract and args.start_from <= 2:
        extract_cmd = [py, str(SCRIPTS / "dcp_extract_changed.py"), "--council", council]
        steps.append(("2. Extract provisions", extract_cmd))

    # Step 3: QA formatting
    if not args.skip_qa and args.start_from <= 3:
        qa_cmd = [py, str(SCRIPTS / "verify_dcp_formatting.py"), "--council", council]
        steps.append(("3. QA formatting check", qa_cmd))

    # Step 4: Enrichment (actionability, topics, layers)
    if args.start_from <= 4:
        enrich_cmd = [
            py, str(ROOT / "enrichment" / "pipeline.py"),
            "--council", council,
            "--phase", "actionability",
        ]
        steps.append(("4a. Enrichment: actionability", enrich_cmd))

        enrich_cmd2 = [
            py, str(ROOT / "enrichment" / "pipeline.py"),
            "--council", council,
            "--phase", "layer",
        ]
        steps.append(("4b. Enrichment: layer/topic tagging", enrich_cmd2))

    # Step 5: Rule extraction
    if args.start_from <= 5:
        rule_cmd = [
            py, str(ROOT / "enrichment" / "rule_extraction_pipeline.py"),
            "--phase", "deterministic",
        ]
        steps.append(("5. Rule extraction (deterministic)", rule_cmd))

    # Step 6: Stats report
    if args.start_from <= 6:
        stats_cmd = [
            py, "-c",
            f"""
import os, sys
sys.path.insert(0, '{str(ROOT)}')
from dotenv import load_dotenv
load_dotenv('{str(ROOT / ".env")}')
import psycopg2
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()
cur.execute(\"\"\"
    SELECT v2_extraction_status, COUNT(*)
    FROM regulatory_provisions
    WHERE is_current = true AND source_council = %s
    GROUP BY v2_extraction_status
\"\"\", ('{council}',))
print('\\n=== {council} EXTRACTION STATS ===')
for row in cur.fetchall():
    print(f'  {{row[0] or "no_status"}}: {{row[1]}}')
cur.execute(\"\"\"
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE is_current = true AND source_council = %s
\"\"\", ('{council}',))
print(f'  TOTAL current: {{cur.fetchone()[0]}}')
cur.close()
conn.close()
""",
        ]
        steps.append(("6. Stats report", stats_cmd))

    if not steps:
        print("No steps to run.")
        return

    print(f"\n{'#'*60}")
    print(f"# LGA ONBOARDING: {council}")
    print(f"# Steps: {len(steps)}")
    print(f"# Dry run: {args.dry_run}")
    print(f"# Each step retries once on failure (2 attempts max)")
    print(f"{'#'*60}")

    results = []
    for name, cmd in steps:
        result = run_step(name, cmd, dry_run=args.dry_run)
        results.append(result)

        if result["status"] == "failed":
            # Stop pipeline — don't run downstream steps on bad data
            # Record remaining steps as skipped
            remaining_idx = [n for n, _ in steps].index(name) + 1
            for skip_name, _ in steps[remaining_idx:]:
                results.append({
                    "step": skip_name, "status": "skipped",
                    "attempts": 0, "output": "", "error": "Skipped due to earlier failure",
                })
            break

    report_path = write_report(council, results, dry_run=args.dry_run)

    # Exit with non-zero if anything failed
    if any(r["status"] == "failed" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
