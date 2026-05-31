#!/usr/bin/env bash
# Mutation testing script — run via WSL:
#   wsl bash scripts/run_mutation_tests.sh
#
# Prerequisites (one-time):
#   python3 -m venv /tmp/mutmut_venv
#   /tmp/mutmut_venv/bin/pip install 'mutmut<3' pytest pydantic fastapi
#
# Runtime: ~3-4 hours for all 3 files on this codebase

set -e

VENV="/tmp/mutmut_venv"
PYTHON="$VENV/bin/python"
MUTMUT="$VENV/bin/mutmut"
PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RESULTS_DIR="$PROJ_DIR/docs/mutation-testing"

mkdir -p "$RESULTS_DIR"

cd "$PROJ_DIR"

run_mutmut() {
    local name="$1"
    local source="$2"
    local tests="$3"
    local output="$RESULTS_DIR/$name.txt"

    echo "=== $name ===" | tee "$output"
    rm -f .mutmut-cache

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
    cp .mutmut-cache "$RESULTS_DIR/.mutmut-cache-$name"
}

echo "Starting mutation testing at $(date)"
echo "Project: $PROJ_DIR"
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
