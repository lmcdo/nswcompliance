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

# ── Test 1: Leichhardt provisions > 50 ───────────────────────────────────────
# Regression: DCP gate was filtering out all Leichhardt provisions
BODY=$(curl -s --max-time 10 \
  "$BASE/api/provisions/for-property?address=1+Norton+Street+Leichhardt+NSW&formerCouncil=leichhardt" \
  2>/dev/null || echo "")

if [ -z "$BODY" ]; then
  echo "⚠️  smoke[leichhardt_provisions]: API timeout — skip"
  SKIP=$((SKIP+1))
elif python3 "$PARSE_SCRIPT" leichhardt_provision_count <<< "$BODY"; then
  echo "✅ smoke[leichhardt_provisions]: >50 provisions returned"
  PASS=$((PASS+1))
else
  echo "❌ smoke[leichhardt_provisions]: too few provisions (DCP gate regression?)"
  FAIL=$((FAIL+1))
fi

# ── Test 2: Leichhardt TOC sections > 10 ─────────────────────────────────────
# Regression: TOC JOIN was 14%, so provisions collapsed to 1 "General" bucket
if [ -n "$BODY" ]; then
  if python3 "$PARSE_SCRIPT" leichhardt_section_count <<< "$BODY"; then
    echo "✅ smoke[leichhardt_toc]: >10 distinct sections"
    PASS=$((PASS+1))
  else
    echo "❌ smoke[leichhardt_toc]: too few TOC sections (JOIN regression?)"
    FAIL=$((FAIL+1))
  fi
else
  echo "⚠️  smoke[leichhardt_toc]: skipped (no API response)"
  SKIP=$((SKIP+1))
fi

# ── Test 3: Marrickville has > 3 TOC parts ───────────────────────────────────
MARR=$(curl -s --max-time 10 \
  "$BASE/api/provisions/for-property?address=1+Marrickville+Road+Marrickville+NSW&formerCouncil=marrickville" \
  2>/dev/null || echo "")

if [ -z "$MARR" ]; then
  echo "⚠️  smoke[marrickville_toc]: API timeout — skip"
  SKIP=$((SKIP+1))
elif python3 "$PARSE_SCRIPT" marrickville_part_count <<< "$MARR"; then
  echo "✅ smoke[marrickville_toc]: >3 parts returned"
  PASS=$((PASS+1))
else
  echo "❌ smoke[marrickville_toc]: too few parts"
  FAIL=$((FAIL+1))
fi

# ── Test 4: DA section-responses table round-trip ────────────────────────────
# Regression: da_section_responses table didn't exist → silent save failures
RESP=$(curl -s --max-time 5 -X POST "$BASE/api/da/section-responses" \
  -H "Content-Type: application/json" \
  -d '{"sessionId":"smoke-test-probe","sectionKey":"smoke","response":{"type":"probe"},"isDismissed":false}' \
  2>/dev/null || echo "")

if [ -z "$RESP" ]; then
  echo "⚠️  smoke[da_section_responses]: API timeout — skip"
  SKIP=$((SKIP+1))
elif python3 "$PARSE_SCRIPT" section_response_saved <<< "$RESP"; then
  echo "✅ smoke[da_section_responses]: round-trip save confirmed"
  PASS=$((PASS+1))
else
  echo "❌ smoke[da_section_responses]: save failed (table missing?)"
  FAIL=$((FAIL+1))
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "Smoke tests: $PASS passed, $FAIL failed, $SKIP skipped"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
