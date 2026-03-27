#!/usr/bin/env python3
"""
Run QA tests for DCP provision extraction.

Usage:
    # Run all unit tests (no database required)
    python run_qa_tests.py

    # Run with database validation tests
    python run_qa_tests.py --database

    # Run specific test file
    python run_qa_tests.py --file test_actionable_classifier.py

    # Run specific test class
    python run_qa_tests.py --class TestFalseNegativePrevention

    # Verbose output
    python run_qa_tests.py -v
"""
import subprocess
import sys
import argparse
import os

# Ensure we're in the right directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)


def run_tests(args):
    """Run pytest with specified options."""
    cmd = ["python", "-m", "pytest"]

    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-v")  # Always verbose for QA

    # Filter by database marker
    if not args.database:
        cmd.extend(["-m", "not database"])
    else:
        print("Including database validation tests...")

    # Filter by file
    if args.file:
        cmd.append(args.file)

    # Filter by class
    if args.test_class:
        cmd.extend(["-k", args.test_class])

    # Add coverage if requested
    if args.coverage:
        cmd.extend(["--cov=../../enrichment", "--cov-report=term-missing"])

    # Show output
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)

    # Run pytest
    result = subprocess.run(cmd)

    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run DCP extraction QA tests")
    parser.add_argument(
        "--database", "-d",
        action="store_true",
        help="Include database validation tests"
    )
    parser.add_argument(
        "--file", "-f",
        help="Run specific test file"
    )
    parser.add_argument(
        "--class", "-c",
        dest="test_class",
        help="Run specific test class"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("DCP EXTRACTION QA TEST SUITE")
    print("=" * 60)
    print(f"Database tests: {'INCLUDED' if args.database else 'EXCLUDED'}")
    print("=" * 60 + "\n")

    returncode = run_tests(args)

    print("\n" + "=" * 60)
    if returncode == 0:
        print("ALL TESTS PASSED")
    else:
        print(f"TESTS FAILED (exit code: {returncode})")
    print("=" * 60)

    sys.exit(returncode)


if __name__ == "__main__":
    main()
