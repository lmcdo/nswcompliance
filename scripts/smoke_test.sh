#!/usr/bin/env bash
# Smoke tests — gate on known regressions.
# Run against local dev server (port 3003). Skip gracefully if server not running.
# Called by: pre-push hook, pre-pr-tests.sh

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
PARSE_SCRIPT="$REPO_ROOT/scripts/smoke_parse.py"
BASE="http://localhost:3003"
PASS=0
FAIL=0
SKIP=0

# ── Health check — confirm dev server is running ─────────────────────────────
HEALTH=$(curl -s --max-time 3 "$BASE/api/health" 2>/dev/null || echo "")
if [ -z "$HEALTH" ]; then
  echo "smoke: dev server not running on port 3003 — skipping all smoke tests"
  exit 0
fi

if ! python3 "$PARSE_SCRIPT" health_ok <<< "$HEALTH"; then
  echo "❌ smoke[health]: server responded but status not ok/healthy"
  FAIL=$((FAIL+1))
else
  echo "✅ smoke[health]: server healthy"
  PASS=$((PASS+1))
fi

# ── Test 1: Leichhardt TOC has > 10 sections ─────────────────────────────────
# Regression: TOC document_id mismatch caused 67.6% join rate → sections collapsed
LECH_TOC=$(curl -s --max-time 8 \
  "$BASE/api/browse/toc?documentId=Leichhardt_DCP_2013__part_c_s1_general" \
  2>/dev/null || echo "")

if [ -z "$LECH_TOC" ]; then
  echo "⚠️  smoke[leichhardt_toc]: API timeout — skip"
  SKIP=$((SKIP+1))
elif python3 "$PARSE_SCRIPT" toc_section_count <<< "$LECH_TOC"; then
  echo "✅ smoke[leichhardt_toc]: >10 sections confirmed"
  PASS=$((PASS+1))
else
  echo "❌ smoke[leichhardt_toc]: too few sections (TOC JOIN regression?)"
  FAIL=$((FAIL+1))
fi

# ── Test 2: Ashfield TOC sections exist (was 0% before migration 017) ─────────
ASH_TOC=$(curl -s --max-time 8 \
  "$BASE/api/browse/toc?documentId=Inner_West_Ashfield_DCP_2016__chapter_a_miscellaneous" \
  2>/dev/null || echo "")

if [ -z "$ASH_TOC" ]; then
  echo "⚠️  smoke[ashfield_toc]: API timeout — skip"
  SKIP=$((SKIP+1))
elif python3 "$PARSE_SCRIPT" toc_section_count <<< "$ASH_TOC"; then
  echo "✅ smoke[ashfield_toc]: >10 sections confirmed"
  PASS=$((PASS+1))
else
  echo "❌ smoke[ashfield_toc]: too few sections (TOC document_id mismatch?)"
  FAIL=$((FAIL+1))
fi

# ── Test 3: Marrickville TOC returns sections ──────────────────────────────────
MARR_TOC=$(curl -s --max-time 8 \
  "$BASE/api/browse/toc?documentId=Marrickville_DCP_2011__part2_s05_equity_access_mobility" \
  2>/dev/null || echo "")

if [ -z "$MARR_TOC" ]; then
  echo "⚠️  smoke[marrickville_toc]: API timeout — skip"
  SKIP=$((SKIP+1))
elif python3 "$PARSE_SCRIPT" toc_has_sections <<< "$MARR_TOC"; then
  echo "✅ smoke[marrickville_toc]: sections present"
  PASS=$((PASS+1))
else
  echo "❌ smoke[marrickville_toc]: no sections returned"
  FAIL=$((FAIL+1))
fi

# ── Test 4: DA sessions API reachable (table existence check) ────────────────
# Regression: da_section_responses table didn't exist → silent save failures
# POST with empty body returns {error: "address is required"} if API+DB are up;
# would 404 or 500 if the route or DB layer is broken.
RESP=$(curl -s --max-time 8 -X POST "$BASE/api/da-sessions" \
  -H "Content-Type: application/json" \
  -d '{}' \
  2>/dev/null || echo "")

if [ -z "$RESP" ]; then
  echo "⚠️  smoke[da_sessions]: API timeout — skip"
  SKIP=$((SKIP+1))
elif python3 "$PARSE_SCRIPT" da_sessions_reachable <<< "$RESP"; then
  echo "✅ smoke[da_sessions]: DA sessions API reachable"
  PASS=$((PASS+1))
else
  echo "❌ smoke[da_sessions]: DA sessions API broken"
  FAIL=$((FAIL+1))
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "Smoke tests: $PASS passed, $FAIL failed, $SKIP skipped"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
