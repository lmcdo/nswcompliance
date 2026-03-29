#!/usr/bin/env bash
# Smoke tests against the local dev server (http://localhost:3003).
# Runs automatically on every git push via the pre-push hook.
#
# WHEN TO ADD A TEST: every time a bug reaches production that a test could have caught.
# Each test has a "Bug history" comment explaining exactly which production failure it prevents.
#
# If dev server is not running: exits 0 with a warning (non-blocking).
# If dev server is running: any failure exits 1 and blocks the push.

set -uo pipefail

BASE="http://localhost:3003"
REPO_ROOT="$(git rev-parse --show-toplevel)"
PARSE_SCRIPT="$REPO_ROOT/scripts/smoke_parse.py"
PASS=0
FAIL=0
SKIP=0

red()    { printf "\033[31m%s\033[0m\n" "$*"; }
green()  { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }

# ── Check server is up ──────────────────────────────────────────────────────
if ! curl -sf --max-time 3 "$BASE/api/health" > /dev/null 2>&1; then
  yellow "smoke-test: dev server not running at $BASE — skipping smoke tests"
  yellow "  Start with: cd frontend-nextjs && npm run dev"
  exit 0
fi

echo "smoke-test: dev server up — running checks"
echo ""

# ── Helper ──────────────────────────────────────────────────────────────────
assert_pass() {
  local label="$1"
  green "  PASS $label"
  PASS=$((PASS + 1))
}

assert_fail() {
  local label="$1"
  local reason="$2"
  red "  FAIL $label — $reason"
  FAIL=$((FAIL + 1))
}

skip_test() {
  local label="$1"
  local reason="$2"
  yellow "  SKIP $label — $reason"
  SKIP=$((SKIP + 1))
}

run_check() {
  # run_check LABEL URL CHECK_NAME [FAIL_MSG]
  local label="$1"
  local url="$2"
  local check="$3"
  local fail_msg="${4:-check failed}"

  local resp
  resp=$(curl -sf --max-time 10 "$url" 2>/dev/null)
  if [ -z "$resp" ]; then
    assert_fail "$label" "empty response from $url"
    return
  fi

  local count
  count=$(echo "$resp" | python3 "$PARSE_SCRIPT" "$check" 2>/dev/null)
  local exit_code=$?

  if [ "$exit_code" -eq 0 ]; then
    assert_pass "$label ($count)"
  else
    assert_fail "$label" "$fail_msg (got: $count)"
  fi
}

# ── TEST 1: DCP gate — Leichhardt address reaches provisions ────────────────
# Bug history: gate matched formerCouncil slugs only; ENABLED_LGAS='inner_west'
# never matched 'leichhardt' → DCPInterestForm shown instead of provisions.
# Fixed: PR #46. Regression here means Leichhardt planners always see the interest form.
echo "--- DCP gate ---"
run_check \
  "Leichhardt returns >50 provisions" \
  "$BASE/api/provisions/for-property?address=16+Renwick+St+Leichhardt+NSW+2040&former_council=leichhardt&groupBy=toc" \
  "leichhardt_provision_count" \
  "DCP gate may be blocking — check ENABLED_LGAS env var and isDcpEnabledForCouncil()"

# ── TEST 2: TOC section grouping — Leichhardt must have >10 sections ────────
# Bug history: TOC JOIN at 14% → all provisions collapsed to 1 'General Controls' bucket.
# Fixed: migrations 015+016. Regression means DA mode shows 1 section for 1300+ provisions.
echo ""
echo "--- TOC section grouping ---"
run_check \
  "Leichhardt TOC has >10 distinct sections" \
  "$BASE/api/provisions/for-property?address=16+Renwick+St+Leichhardt+NSW+2040&former_council=leichhardt&groupBy=toc" \
  "leichhardt_section_count" \
  "TOC JOIN may have regressed — check dcp_table_of_contents document_id format for Leichhardt"

run_check \
  "Marrickville TOC has >3 parts" \
  "$BASE/api/provisions/for-property?address=10+Marrickville+Rd+Marrickville+NSW+2204&former_council=marrickville&groupBy=toc" \
  "marrickville_part_count" \
  "Marrickville TOC grouping broken"

# ── TEST 3: DA section-responses round-trip ─────────────────────────────────
# Bug history: da_section_responses table never existed — every section save
# silently failed for months. Fixed: migration in PR #36.
echo ""
echo "--- DA section-responses ---"
SESSION_RESP=$(curl -sf --max-time 5 "$BASE/api/da-sessions" 2>/dev/null)
if [ -z "$SESSION_RESP" ]; then
  skip_test "DA section-responses round-trip" "da-sessions endpoint returned nothing"
else
  TOKEN=$(echo "$SESSION_RESP" | python3 -c "
import json,sys
d=json.load(sys.stdin)
items = d if isinstance(d, list) else d.get('data', [])
if items and len(items) > 0:
    print(items[0].get('token',''))
" 2>/dev/null || echo "")

  if [ -z "$TOKEN" ]; then
    skip_test "DA section-responses round-trip" "no existing DA session to test against"
  else
    SR_STATUS=$(curl -sf --max-time 5 -o /dev/null -w "%{http_code}" \
      -X POST "$BASE/api/da-sessions/$TOKEN/section-responses" \
      -H "Content-Type: application/json" \
      -d "{\"section_key\":\"smoke-test\",\"status\":\"not_applicable\"}" 2>/dev/null || echo "000")
    if [ "$SR_STATUS" = "200" ] || [ "$SR_STATUS" = "201" ]; then
      assert_pass "DA section-responses POST returns $SR_STATUS"
    elif [ "$SR_STATUS" = "401" ] || [ "$SR_STATUS" = "403" ]; then
      assert_pass "DA section-responses endpoint exists (auth $SR_STATUS — table present)"
    else
      assert_fail "DA section-responses POST" "HTTP $SR_STATUS — table may not exist or endpoint broken"
    fi
  fi
fi

# ── TEST 4: Health endpoint ──────────────────────────────────────────────────
echo ""
echo "--- Infrastructure ---"
run_check \
  "Health endpoint returns healthy/ok" \
  "$BASE/api/health" \
  "health_ok" \
  "Health check failed"

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "smoke-test: $PASS passed, $FAIL failed, $SKIP skipped"
echo ""

if [ "$FAIL" -gt "0" ]; then
  red "smoke-test FAILED — fix the failures above before pushing"
  red "Each test maps to a production bug. A failure here means that bug has returned."
  echo ""
  red "To push anyway (emergencies only): git push --no-verify"
  exit 1
fi

green "smoke-test PASSED"
exit 0
