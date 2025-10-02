"""
Master execution script - Run all SEPP full text extraction steps in sequence

This script runs all 5 steps of the extraction pipeline:
1. Extract SEPPs with MinerU
2. Parse markdown to JSON
3. Update database schema
4. Import full provisions
5. Verify completeness

Each step must complete successfully before proceeding to the next.

Usage:
    python run_all.py                    # Run all steps
    python run_all.py --start-from 3     # Start from step 3
    python run_all.py --only 5           # Run only step 5
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

STEPS = [
    {
        'number': 1,
        'name': 'Extract SEPPs with MinerU',
        'script': '01_extract_sepps_mineru.py',
        'duration_estimate': '10-30 minutes',
        'description': 'Extract full text from SEPP PDFs using MinerU'
    },
    {
        'number': 2,
        'name': 'Parse Markdown to JSON',
        'script': '02_parse_markdown_to_json.py',
        'duration_estimate': '2-5 minutes',
        'description': 'Parse markdown into structured JSON provisions'
    },
    {
        'number': 3,
        'name': 'Update Database Schema',
        'script': '03_update_database_schema.py',
        'duration_estimate': '1-2 minutes',
        'description': 'Remove 500-char limit, add metadata columns'
    },
    {
        'number': 4,
        'name': 'Import Full Provisions',
        'script': '04_import_full_provisions.py',
        'duration_estimate': '5-10 minutes',
        'description': 'Import full text provisions to database'
    },
    {
        'number': 5,
        'name': 'Verify Completeness',
        'script': '05_verify_completeness.py',
        'duration_estimate': '2-5 minutes',
        'description': 'Run verification tests and generate reports'
    }
]

def print_header():
    """Print execution header"""
    print("\n" + "="*80)
    print("SEPP FULL TEXT EXTRACTION PIPELINE")
    print("="*80)
    print(f"\nExecution started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

def print_step_info(step):
    """Print information about a step"""
    print("\n" + "="*80)
    print(f"STEP {step['number']}: {step['name']}")
    print("="*80)
    print(f"Script:      {step['script']}")
    print(f"Description: {step['description']}")
    print(f"Est. Time:   {step['duration_estimate']}")
    print()

def run_step(step):
    """Execute a single step"""
    print_step_info(step)

    script_path = Path(__file__).parent / step['script']

    if not script_path.exists():
        print(f"[X] Script not found: {script_path}")
        return False

    print(f"Running: python {step['script']}\n")
    print("-"*80 + "\n")

    try:
        start_time = datetime.now()

        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=script_path.parent,
            timeout=3600  # 1 hour timeout per step
        )

        duration = (datetime.now() - start_time).total_seconds()
        minutes = int(duration // 60)
        seconds = int(duration % 60)

        print(f"\n{'-'*80}")
        print(f"Step {step['number']} completed in {minutes}m {seconds}s")

        if result.returncode == 0:
            print(f"[OK] Step {step['number']} SUCCESS")
            return True
        else:
            print(f"[X] Step {step['number']} FAILED (exit code {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print(f"\n[X] Step {step['number']} TIMEOUT (exceeded 1 hour)")
        return False
    except Exception as e:
        print(f"\n[X] Step {step['number']} ERROR: {e}")
        return False

def run_all_steps(start_from=1, only_step=None):
    """Run all steps in sequence"""
    print_header()

    if only_step:
        steps_to_run = [s for s in STEPS if s['number'] == only_step]
        if not steps_to_run:
            print(f"[X] Invalid step number: {only_step}")
            return False
    else:
        steps_to_run = [s for s in STEPS if s['number'] >= start_from]

    print(f"Pipeline: {len(steps_to_run)} steps to execute")
    print(f"Total estimated time: {sum_durations(steps_to_run)}\n")

    # Show steps
    for step in steps_to_run:
        print(f"  Step {step['number']}: {step['name']}")
    print()

    # Confirm
    if len(steps_to_run) > 1:
        print("Proceed? (yes/no): ", end='')
        response = input().strip().lower()
        if response != 'yes':
            print("Aborted.")
            return False

    # Run steps
    start_time = datetime.now()
    completed_steps = []
    failed_step = None

    for step in steps_to_run:
        success = run_step(step)

        if success:
            completed_steps.append(step['number'])
        else:
            failed_step = step['number']
            break

    # Print summary
    total_duration = (datetime.now() - start_time).total_seconds()
    total_minutes = int(total_duration // 60)
    total_seconds = int(total_duration % 60)

    print("\n" + "="*80)
    print("PIPELINE EXECUTION SUMMARY")
    print("="*80)
    print(f"\nTotal execution time: {total_minutes}m {total_seconds}s")
    print(f"Steps completed:      {len(completed_steps)}/{len(steps_to_run)}\n")

    if failed_step:
        print(f"[X] PIPELINE FAILED at Step {failed_step}")
        print(f"\nTo resume from failed step:")
        print(f"  python run_all.py --start-from {failed_step}")
        return False
    else:
        print("[SUCCESS] PIPELINE COMPLETED SUCCESSFULLY")
        print("\nFull text provisions are now available in the database.")
        print("\nKey outputs:")
        print("  - Extracted markdown: docs/sepps/extracted/")
        print("  - Provision JSON:     docs/sepps/extracted/*.json")
        print("  - Verification:       docs/sepps/verification/")
        return True

def sum_durations(steps):
    """Calculate total estimated duration"""
    # Extract max minutes from ranges like "5-10 minutes"
    total_minutes = 0
    for step in steps:
        duration = step['duration_estimate']
        if '-' in duration:
            max_time = duration.split('-')[1].strip().split()[0]
            total_minutes += int(max_time)
        else:
            total_minutes += int(duration.split()[0])

    return f"~{total_minutes} minutes"

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Run SEPP full text extraction pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_all.py                    # Run all steps
  python run_all.py --start-from 3     # Start from step 3
  python run_all.py --only 5           # Run only step 5

Steps:
  1. Extract SEPPs with MinerU (~10-30 min)
  2. Parse markdown to JSON (~2-5 min)
  3. Update database schema (~1-2 min)
  4. Import full provisions (~5-10 min)
  5. Verify completeness (~2-5 min)
        """
    )

    parser.add_argument('--start-from', type=int, metavar='N',
                       help='Start from step N (1-5)')
    parser.add_argument('--only', type=int, metavar='N',
                       help='Run only step N (1-5)')

    args = parser.parse_args()

    # Validate arguments
    if args.start_from and (args.start_from < 1 or args.start_from > 5):
        print("[X] --start-from must be between 1 and 5")
        return 1

    if args.only and (args.only < 1 or args.only > 5):
        print("[X] --only must be between 1 and 5")
        return 1

    if args.start_from and args.only:
        print("[X] Cannot use --start-from and --only together")
        return 1

    # Run pipeline
    success = run_all_steps(
        start_from=args.start_from or 1,
        only_step=args.only
    )

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())