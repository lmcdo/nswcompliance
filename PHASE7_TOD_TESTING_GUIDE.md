# Phase 7: TOD/HIA Integration Testing Guide

**Date:** 2025-10-27
**Status:** Ready for Testing
**Purpose:** Verify end-to-end TOD/HIA integration (Phases 1-6)

---

## Quick Start

### Option 1: Automated Test Script (Recommended)

```bash
# Ensure dev server is running
cd frontend-nextjs
npm run dev

# In another terminal, run test script
cd ..
node test_tod_integration.js
```

### Option 2: Manual Browser Testing

```bash
# Start dev server
cd frontend-nextjs
npm run dev

# Open browser to:
http://localhost:3000/assessment

# Test addresses below
```

---

## Test Addresses

### TOD Addresses (Should Show Blue Badge)

| Address | Expected Station | Notes |
|---------|------------------|-------|
| **370 Illawarra Rd, Marrickville NSW 2204** | Marrickville | Primary test case |
| **202 Marrickville Rd, Marrickville NSW 2204** | Marrickville | TOD area near station |
| **Dulwich Hill Station, NSW 2203** | Dulwich Hill | Station address |

### Control Addresses (Should NOT Show Badge)

| Address | Notes |
|---------|-------|
| **14 Hunter St, Lewisham NSW 2049** | Non-TOD Inner West |
| **3 Wilkinson Ln, Telopea NSW 2117** | Outside Inner West |

---

## Automated Testing

### Running the Test Script

```bash
# Default (localhost:3000)
node test_tod_integration.js

# Custom URL
API_BASE_URL=https://your-domain.com node test_tod_integration.js
```

### What the Script Tests

1. **API Connectivity**
   - Response time (<10s target)
   - HTTP status codes
   - Response structure

2. **TOD Detection**
   - TOD layers in response
   - Constraint extraction
   - Field completeness

3. **Data Validation**
   - Required fields present
   - FSR/Height reasonable values
   - Station name accuracy

4. **Control Tests**
   - Non-TOD addresses don't show TOD data
   - Graceful handling of missing data

### Expected Output

```
================================================================================
TOD/HIA INTEGRATION TEST SUITE
Phase 7: End-to-End Testing
================================================================================

API Base URL: http://localhost:3000
Total test cases: 5
  - TOD addresses: 3
  - Control addresses: 2

================================================================================
Testing: 370 Illawarra Rd, Marrickville NSW 2204
Description: Marrickville Station TOD - Primary test case
Expected TOD: YES

Fetching from API...
Response time: 5234ms
Status: 200

Results:
  Address: 370 ILLAWARRA RD, MARRICKVILLE NSW 2204
  Zone: R2
  LGA: Inner West
  Planning layers received: 16
  TOD layers found: Transport Oriented Development Sites Map

TOD Detection:
  TOD precinct present: YES
  Precinct name: Marrickville Station TOD
  Station name: Marrickville
  Max FSR: 2.5:1
  Max Height: 24m
  Legislative clause: Clause 4.4
  SEPP reference: SEPP (Housing) 2021

Validation:
  ✓ TOD detection matches expectation
  ✓ Station name matches expectation
  ✓ All required fields present
  ✓ FSR/Height values are reasonable

✓ TEST PASSED

... (other tests)

================================================================================
TEST SUMMARY
================================================================================

Total tests: 5
Passed: 5
Failed: 0
TOD detected: 3/3 expected

Detailed Results:
────────────────────────────────────────────────────────────────────────────────
PASS | 370 Illawarra Rd, Marrickville NSW 2204    | TOD: YES
PASS | 202 Marrickville Rd, Marrickville NSW 2204 | TOD: YES
PASS | Dulwich Hill Station, NSW 2203              | TOD: YES
PASS | 14 Hunter St, Lewisham NSW 2049             | TOD: NO
PASS | 3 Wilkinson Ln, Telopea NSW 2117            | TOD: NO
────────────────────────────────────────────────────────────────────────────────

Performance:
  Average response time: 5532ms
  Max response time: 7234ms
  Expected: <10,000ms
  ✓ Performance within target

================================================================================
ALL TESTS PASSED ✓

TOD/HIA integration is working correctly!
================================================================================
```

---

## Manual Browser Testing

### Step 1: Start Dev Server

```bash
cd frontend-nextjs
npm run dev
```

### Step 2: Open Assessment Page

Navigate to: `http://localhost:3000/assessment`

### Step 3: Test TOD Address

1. **Enter address:** `370 Illawarra Rd, Marrickville NSW 2204`
2. **Click search** or press Enter
3. **Wait** for property data to load (5-10 seconds)

### Step 4: Verify TOD Badge Appears

**Expected Result:**

You should see a blue badge in the left panel that looks like:

```
┌─────────────────────────────────────────────────────┐
│ ⚡ Transport Oriented Development Area              │
│                                                     │
│ Marrickville Station TOD                           │
│                                                     │
│ ┌──────────────┬──────────────┐                   │
│ │ Max FSR      │ Max Height   │                   │
│ │ 2.5:1        │ 24m          │                   │
│ └──────────────┴──────────────┘                   │
│                                                     │
│ SEPP (Housing) 2021                                │
└─────────────────────────────────────────────────────┘
```

**Badge Features to Check:**
- ✅ Blue background (bg-blue-50)
- ✅ Bold blue border (border-blue-300)
- ✅ Lightning bolt icon visible
- ✅ Precinct name displayed
- ✅ FSR bonus shown (should be 2.5:1 or similar)
- ✅ Height bonus shown (should be 24m or similar)
- ✅ SEPP reference shown at bottom

### Step 5: Test Control Address

1. **Enter address:** `14 Hunter St, Lewisham NSW 2049`
2. **Click search**
3. **Wait** for property data to load

**Expected Result:**
- ❌ NO blue TOD badge should appear
- ✅ Property details should still load normally
- ✅ Zone, LGA, Heritage fields should display

---

## Console Log Verification

### Step 1: Open Browser DevTools

Press **F12** or **Right-click → Inspect**

### Step 2: Go to Console Tab

### Step 3: Search TOD Address

Enter: `370 Illawarra Rd, Marrickville NSW 2204`

### Step 4: Check Console Logs

**You should see logs from Phases 1-5:**

#### Phase 2 Audit (Layer Detection)
```
=== LAYER COVERAGE AUDIT (Phase 2) ===
Total layers received: 16

All layer names:
  1. Land Zoning Map (1 results)
  2. Floor Space Ratio Map (1 results)
  ...
  16. Transport Oriented Development Sites Map (1 results)

✅ TOD/HIA-related layers FOUND:
  - Transport Oriented Development Sites Map

=== END LAYER AUDIT ===
```

#### Phase 3 Fetching
```
=== Fetching TOD/HIA Layers (Phase 3) ===
Geometry: { x: 151.155, y: -33.911 }
Querying TOD Sites Map...
✅ TOD layer found: 1 features
Querying Accelerated TOD Precincts...
❌ No Accelerated TOD features at this location
TOD/HIA query complete. Found 1 layer(s)
```

#### Phase 5 Extraction
```
Layer: Transport Oriented Development Sites Map (1 results)
✅ Extracting TOD precinct data: { ... }
TOD precinct extracted: {
  inTODArea: true,
  precinctName: "Marrickville Station TOD",
  ...
}
```

---

## Troubleshooting

### Issue: No TOD Badge Appears (But Should)

**Check Console for:**

1. **Phase 3 logs missing?**
   ```
   === Fetching TOD/HIA Layers (Phase 3) ===
   ```
   - If missing → getTODLayers() not being called
   - Check: `Promise.all` in getPropertyComplianceData

2. **TOD layers fetch failed?**
   ```
   TOD layers fetch failed, continuing without TOD data
   ```
   - Network issue or API timeout
   - Check: NSW Planning Portal API status

3. **No extraction logs?**
   ```
   ✅ Extracting TOD precinct data
   ```
   - If missing → Layer name not matching
   - Check: extractPlanningConstraints switch cases

4. **constraints.todPrecinct undefined?**
   - Check API response: `/api/property?address=...`
   - Verify `constraints.todPrecinct` in JSON

### Issue: Badge Appears for Non-TOD Address

**This is incorrect!**

1. **Check which address was actually queried**
   - Address autocomplete may have selected different address

2. **Check console logs**
   - Should show: `❌ No TOD features at this location`

3. **Verify address coordinates**
   - Property may actually be in TOD area despite address

### Issue: Slow Response (>10s)

**Check:**

1. **Network latency**
   ```
   Response time: 12000ms
   ```
   - NSW Planning Portal may be slow
   - Retry the query

2. **Timeout errors**
   - Check for AbortError in console
   - Phase 1 timeout protection should prevent hangs

3. **Too many retries**
   - Rate limiting (429 errors)
   - Wait and retry

### Issue: TypeError or Missing Fields

**Check:**

1. **TypeScript compilation**
   ```bash
   npm run build
   ```
   - Should compile without errors
   - Phase 4 interfaces should be recognized

2. **Optional chaining used?**
   ```tsx
   {propertyData.constraints?.todPrecinct && ...}
   ```
   - Should not crash if undefined

---

## Success Criteria

### Phase 1 ✅
- [x] No indefinite API hangs
- [x] Requests timeout after 10s
- [x] Retry logic works for timeouts

### Phase 2 ✅
- [x] Layer audit logs visible
- [x] TOD layers identified in audit
- [x] Clear ✅/❌ indicators

### Phase 3 ✅
- [x] getTODLayers() called for all addresses
- [x] NSW TOD MapServers queried
- [x] TOD layers merged with standard layers
- [x] Graceful failure (no crash)

### Phase 4 ✅
- [x] TypeScript compiles without errors
- [x] Interfaces exported/imported correctly
- [x] IntelliSense shows TOD fields

### Phase 5 ✅
- [x] TOD data extracted from layers
- [x] constraints.todPrecinct populated
- [x] All required fields present
- [x] Reasonable default values

### Phase 6 ✅
- [x] Blue badge appears for TOD addresses
- [x] Badge shows precinct name
- [x] FSR/height bonuses displayed
- [x] No badge for non-TOD addresses

### Phase 7 (Current) ✅
- [ ] All test addresses pass
- [ ] Performance <10s average
- [ ] No console errors
- [ ] UI matches design

---

## Test Results Template

Copy and fill in:

```
## Test Results

**Date:** 2025-10-27
**Tester:** [Your Name]
**Environment:** [Local/Staging/Production]

### Automated Tests
- [ ] All tests passed
- [ ] Performance acceptable
- Failures: [List any]

### Manual Browser Tests

#### TOD Address 1: 370 Illawarra Rd, Marrickville
- [ ] Badge appeared
- [ ] FSR displayed: _____
- [ ] Height displayed: _____
- [ ] Station name: _____
- Response time: _____ ms

#### TOD Address 2: 202 Marrickville Rd, Marrickville
- [ ] Badge appeared
- [ ] FSR displayed: _____
- [ ] Height displayed: _____
- Response time: _____ ms

#### TOD Address 3: Dulwich Hill Station
- [ ] Badge appeared
- [ ] FSR displayed: _____
- [ ] Height displayed: _____
- Response time: _____ ms

#### Control Address 1: 14 Hunter St, Lewisham
- [ ] No badge (correct)
- [ ] Property data loaded normally
- Response time: _____ ms

#### Control Address 2: 3 Wilkinson Ln, Telopea
- [ ] No badge (correct)
- [ ] Property data loaded normally
- Response time: _____ ms

### Console Logs
- [ ] Phase 2 audit visible
- [ ] Phase 3 fetching visible
- [ ] Phase 5 extraction visible
- [ ] No errors

### Issues Found
[List any issues encountered]

### Overall Assessment
- [ ] Integration working correctly
- [ ] Ready for production
- [ ] Issues need resolution

**Notes:**
```

---

## Next Steps After Testing

### If All Tests Pass ✅

1. **Update TOD_HIA_INTEGRATION_PLAN.md**
   - Mark Phase 7 complete
   - Add test results summary

2. **Create Integration Summary**
   - Document final architecture
   - API endpoints
   - UI components

3. **Optional: Create PR**
   - Summarize all 7 phases
   - Link to test results
   - Request code review

### If Tests Fail ❌

1. **Document failures** using template above
2. **Review console logs** for specific errors
3. **Check relevant phase** (1-6) for the failure
4. **Fix and re-test**

---

## Additional Testing (Optional)

### Test Different Scenarios

1. **Accelerated TOD Precincts**
   - Find address in one of 8 priority precincts
   - Should show purple badge

2. **HIA Areas**
   - Find address in Housing Infrastructure Area
   - Should show green badge

3. **Multiple Badges**
   - Address with both TOD + Accelerated
   - Should show both badges

4. **Edge Cases**
   - Very slow network
   - API timeout
   - Malformed address

### Performance Testing

```bash
# Run multiple times to check consistency
for i in {1..5}; do
  echo "Run $i"
  node test_tod_integration.js
done
```

---

## Contact/Support

If you encounter issues:

1. Check console logs first
2. Review troubleshooting section
3. Document the issue with:
   - Address tested
   - Expected result
   - Actual result
   - Console logs
   - Screenshots

---

**Testing Status:** ⏳ Pending
**Est. Time:** 30-60 minutes
**Prerequisites:** Dev server running

Phase 7 of TOD/HIA integration plan (TOD_HIA_INTEGRATION_PLAN.md)
