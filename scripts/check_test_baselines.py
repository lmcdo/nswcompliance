#!/usr/bin/env python3
"""Check that mutation test counts haven't dropped below baselines.

Usage:
    python scripts/check_test_baselines.py mutation-baselines.json

Reads the baselines file, runs `pytest --co -q` on each service's test files,
and fails if the collected test count is below the minimum. This prevents
silent test deletion or quarantining from eroding mutation testing coverage.

Exit codes:
    0 — all services at or above baseline
    1 — one or more services below baseline
    2 — baselines file missing or malformed
"""
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_test_baselines.py <baselines.json>")
        return 2

    baselines_path = Path(sys.argv[1])
    if not baselines_path.exists():
        print(f"ERROR: Baselines file not found: {baselines_path}")
        return 2

    try:
        baselines = json.loads(baselines_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"ERROR: Could not read baselines: {e}")
        return 2

    failed = False
    for service, config in baselines.items():
        if service.startswith("_"):
            continue

        test_files = config.get("test_files", [])
        min_count = config.get("min_test_count", 0)

        # Filter to files that actually exist
        existing = [f for f in test_files if Path(f).exists()]
        if not existing:
            print(f"  {service}: SKIP (no test files found)")
            continue

        # Collect tests without running them
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--co", "-q", "--no-header"] + existing,
            capture_output=True, text=True, timeout=30,
        )

        # Count collected tests from the summary line "N tests collected"
        count = 0
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if "test" in line and "collected" in line:
                # "480 tests collected in 0.44s" or "480 tests collected"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part in ("test", "tests") and i > 0:
                        try:
                            count = int(parts[i - 1])
                        except ValueError:
                            pass
                        break
            # Also handle pytest's "<Function test_name>" format — count those lines
            elif line.startswith("<"):
                count += 1

        status = "OK" if count >= min_count else "FAIL"
        symbol = "+" if count >= min_count else "-"
        print(f"  {service}: {count}/{min_count} {status} ({symbol}{count - min_count})")

        if count < min_count:
            failed = True

    if failed:
        print("\nFAILED — mutation test count below baseline.")
        print("If tests were intentionally removed, update mutation-baselines.json.")
        return 1

    print("\nAll mutation test baselines met.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
