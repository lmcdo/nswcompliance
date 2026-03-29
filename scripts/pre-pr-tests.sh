#!/usr/bin/env bash
# Run all local tests and save output to test-trail/ before opening a PR.
# Usage: bash scripts/pre-pr-tests.sh
# Output: test-trail/YYYY-MM-DD-{branch}.txt

set -euo pipefail

BRANCH=$(git rev-parse --abbrev-ref HEAD)
DATE=$(date +%Y-%m-%d-%H%M)
OUTFILE="test-trail/${DATE}-${BRANCH//\//-}.txt"

echo "Running tests for branch: $BRANCH"
echo "Output → $OUTFILE"
echo ""

{
  echo "=== TEST TRAIL ==="
  echo "Branch:  $BRANCH"
  echo "Date:    $(date)"
  echo "Commit:  $(git rev-parse HEAD)"
  echo ""

  echo "--- Python: enrichment tests ---"
  python -m pytest tests/enrichment/ -v --tb=short 2>&1 || true

  echo ""
  echo "--- TypeScript: jest component tests ---"
  cd frontend-nextjs && npx jest --passWithNoTests 2>&1 || true
  cd ..

  echo ""
  echo "--- TypeScript: type check ---"
  cd frontend-nextjs && npx tsc --noEmit 2>&1 | tail -5 || true
  cd ..

  echo ""
  echo "--- Smoke tests (requires running dev server on :3003) ---"
  REPO_ROOT="$(git rev-parse --show-toplevel)"
  bash "$REPO_ROOT/scripts/smoke_test.sh" 2>&1 || true

  echo ""
  echo "=== END ==="
} | tee "$OUTFILE"

echo ""
echo "Saved to $OUTFILE"
echo "Add this file to your branch commit before opening the PR."
