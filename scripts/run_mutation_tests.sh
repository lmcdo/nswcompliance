#!/usr/bin/env bash
# Mutation testing script — run via WSL:
#   wsl bash scripts/run_mutation_tests.sh
#
# Prerequisites (one-time):
#   python3 -m venv /tmp/mutmut_venv
#   /tmp/mutmut_venv/bin/pip install 'mutmut<3' pytest pydantic fastapi
#
# Runtime: ~3-4 hours for all 3 files on this codebase
#
# NOTE: This script copies the project to a native Linux path (/tmp/mutmut_workspace)
# to avoid SQLite disk I/O errors that occur when mutmut runs on /mnt/c/ (NTFS via WSL).
# Results are copied back to the Windows project directory when done.

set -e

VENV="/tmp/mutmut_venv"
PYTHON="$VENV/bin/python"
MUTMUT="$VENV/bin/mutmut"

# Detect source directory (works whether invoked from /mnt/c or native Linux)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Copy project to native Linux filesystem to avoid SQLite/NTFS locking issues
WORK_DIR="/tmp/mutmut_workspace"
RESULTS_DIR="$SRC_DIR/docs/mutation-testing"

echo "Setting up native Linux workspace..."
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR" "$RESULTS_DIR"

# Copy only what mutmut needs — services, tests, conftest, and config
cp -r "$SRC_DIR/services" "$WORK_DIR/services"
cp -r "$SRC_DIR/tests" "$WORK_DIR/tests"
cp -r "$SRC_DIR/src" "$WORK_DIR/src" 2>/dev/null || true
cp "$SRC_DIR/pytest.ini" "$WORK_DIR/" 2>/dev/null || true
cp "$SRC_DIR/requirements-test.txt" "$WORK_DIR/" 2>/dev/null || true

echo "Workspace ready at $WORK_DIR"
echo ""

cd "$WORK_DIR"

# Ensure venv exists and has deps
if [ ! -f "$MUTMUT" ]; then
    echo "Creating mutmut venv..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q 'mutmut<3' pytest pydantic fastapi
fi

run_mutmut() {
    local name="$1"
    local source="$2"
    local tests="$3"
    local output="$RESULTS_DIR/$name.txt"

    echo "=== $name ===" | tee "$output"

    # Clean cache for each run
    rm -f .mutmut-cache

    # Verify tests pass before mutating
    echo "Verifying tests pass cleanly..."
    if ! $PYTHON -m pytest $tests -x -q --no-header --tb=short 2>&1; then
        echo "SKIP: Tests don't pass for $name — fix tests first" | tee -a "$output"
        return 1
    fi

    $MUTMUT run \
        --paths-to-mutate="$source" \
        --tests-dir=tests/ \
        --runner="$PYTHON -m pytest $tests -x -q --no-header --tb=no" \
        2>&1 | tee -a "$output"

    echo "" | tee -a "$output"
    echo "=== RESULTS ===" | tee -a "$output"
    $MUTMUT results 2>&1 | tee -a "$output"

    # Extract survived mutant details
    echo "" >> "$output"
    echo "=== SURVIVED MUTANT DETAILS ===" >> "$output"

    # Get survived mutant IDs from cache
    $PYTHON -c "
import sqlite3
conn = sqlite3.connect('.mutmut-cache')
c = conn.cursor()
c.execute(\"SELECT id FROM Mutant WHERE status='bad_survived' ORDER BY id\")
ids = [str(r[0]) for r in c.fetchall()]
conn.close()
print(','.join(ids))
" > /tmp/survived_ids.txt

    # Show first 50 survived mutants
    IFS=',' read -ra IDS < /tmp/survived_ids.txt
    count=0
    for id in "${IDS[@]}"; do
        if [ $count -ge 50 ]; then
            echo "... ($(( ${#IDS[@]} - 50 )) more survived mutants not shown)" >> "$output"
            break
        fi
        echo "--- Mutant $id ---" >> "$output"
        $MUTMUT show "$id" >> "$output" 2>&1
        echo "" >> "$output"
        count=$((count + 1))
    done

    # Summary stats
    $PYTHON -c "
import sqlite3
conn = sqlite3.connect('.mutmut-cache')
c = conn.cursor()
c.execute(\"SELECT status, count(*) FROM Mutant GROUP BY status\")
results = dict(c.fetchall())
total = sum(results.values())
killed = results.get('ok_killed', 0)
survived = results.get('bad_survived', 0)
timeout = results.get('bad_timeout', 0)
score = killed / total * 100 if total > 0 else 0
print(f'Score: {killed}/{total} killed ({score:.1f}% mutation score)')
print(f'  Killed: {killed}')
print(f'  Survived: {survived}')
print(f'  Timeout: {timeout}')
conn.close()
" | tee -a "$output"

    echo ""
    echo "Results saved to: $output"
    echo ""

    # Save cache for later inspection
    cp .mutmut-cache "$RESULTS_DIR/.mutmut-cache-$name" 2>/dev/null || true

    # Restore source files in case mutmut crashed mid-mutation
    cp -r "$SRC_DIR/services" "$WORK_DIR/services"
}

echo "Starting mutation testing at $(date)"
echo "Source: $SRC_DIR"
echo "Workspace: $WORK_DIR"
echo ""

run_mutmut "threat_radar" \
    "services/threat_radar.py" \
    "tests/test_threat_radar.py"

run_mutmut "granny_flat" \
    "services/granny_flat.py" \
    "tests/test_granny_flat_logic.py tests/test_granny_flat_geometry.py"

run_mutmut "flood_truth" \
    "services/flood_truth.py" \
    "tests/test_flood_truth.py"

echo ""
echo "=== SUMMARY ==="
echo "Completed at $(date)"
for f in "$RESULTS_DIR"/*.txt; do
    name=$(basename "$f" .txt)
    echo ""
    echo "--- $name ---"
    tail -5 "$f"
done

# Cleanup workspace (source files are copies, safe to remove)
echo ""
echo "Cleaning up workspace..."
rm -rf "$WORK_DIR"
echo "Done."
