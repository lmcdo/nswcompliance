# Phase 2: TOD/HIA Layer Coverage Test

**Date:** 2025-10-27
**Purpose:** Determine if TOD/HIA layers are already included in NSW Planning Portal EPI response
**Decision Point:** If found → Skip Phase 3, go to Phase 5. If not found → Implement Phase 3.

---

## What Was Changed

**File:** `frontend-nextjs/lib/nsw-planning-portal.ts` (lines 253-275)

Added comprehensive logging to `extractPlanningConstraints()`:
- Lists all layer names received from API
- Searches for TOD/HIA-related keywords
- Reports findings clearly in console

---

## How to Test

### Option 1: Using Browser (Recommended)

1. **Start Development Server**
   ```bash
   cd frontend-nextjs
   npm run dev
   ```

2. **Open Browser Console**
   - Navigate to: `http://localhost:3000/assessment`
   - Open DevTools (F12)
   - Go to Console tab

3. **Test Known TOD Address**

   Enter one of these addresses in the search:
   ```
   370 Illawarra Rd, Marrickville NSW 2204
   ```

   Other test addresses:
   ```
   202 Marrickville Rd, Marrickville NSW 2204  (Marrickville Station area)
   Dulwich Hill Station, NSW 2203              (Dulwich Hill TOD)
   14 Hunter St, Lewisham NSW 2049             (Control - NOT TOD)
   ```

4. **Check Console Output**

   Look for this section:
   ```
   === LAYER COVERAGE AUDIT (Phase 2) ===
   Total layers received: 15

   All layer names:
     1. Land Zoning Map (1 results)
     2. Floor Space Ratio Map (1 results)
     3. Height of Buildings Map (1 results)
     ... etc ...

   ✅ TOD/HIA-related layers FOUND:
     - Transport Oriented Development Sites Map
     - SEPP Housing 2021

   OR

   ❌ NO TOD/HIA-related layers found in EPI response
     Will need separate API call (Phase 3)

   === END LAYER AUDIT ===
   ```

### Option 2: Using API Directly

```bash
# Test via API endpoint
curl "http://localhost:3000/api/property?address=370%20Illawarra%20Rd%2C%20Marrickville%20NSW%202204"
```

Check server console for the audit logs.

### Option 3: Node Script (Quick Check)

Create `test-tod-layers.js`:
```javascript
const fetch = require('node-fetch');

async function testTODLayers() {
  const addresses = [
    '370 Illawarra Rd, Marrickville NSW 2204',  // TOD
    '14 Hunter St, Lewisham NSW 2049'            // Non-TOD
  ];

  for (const address of addresses) {
    console.log(`\n\nTesting: ${address}`);
    console.log('='.repeat(60));

    const response = await fetch(
      `http://localhost:3000/api/property?address=${encodeURIComponent(address)}`
    );

    const data = await response.json();
    console.log('Layers received:', data.data?.planningLayers?.length || 0);

    if (data.data?.planningLayers) {
      console.log('Layer names:');
      data.data.planningLayers.forEach((layer, i) => {
        console.log(`  ${i + 1}. ${layer.layerName}`);
      });
    }
  }
}

testTODLayers().catch(console.error);
```

Run:
```bash
node test-tod-layers.js
```

---

## Expected Results

### Scenario A: TOD Layers ARE Included ✅

**Console Output:**
```
✅ TOD/HIA-related layers FOUND:
  - Transport Oriented Development Sites Map
  - SEPP (Housing) 2021 - TOD
  - Accelerated TOD Precincts
```

**Decision:** SKIP Phase 3 → Go directly to Phase 5 (extraction logic)

**Reason:** TOD data is already in the response, no separate API call needed

---

### Scenario B: TOD Layers NOT Included ❌

**Console Output:**
```
❌ NO TOD/HIA-related layers found in EPI response
  Will need separate API call (Phase 3)

All layer names:
  1. Land Zoning Map
  2. Floor Space Ratio Map
  3. Height of Buildings Map
  4. Heritage Map
  5. Lot Size Map
  6. Special Provisions
  ... (no TOD-related layers)
```

**Decision:** Implement Phase 3 (separate API call)

**Reason:** TOD data requires querying different MapServer endpoints

---

## Known TOD Precincts to Test

### Inner West TOD Stations

| Station | Address to Test | Expected |
|---------|----------------|----------|
| Marrickville | 370 Illawarra Rd, Marrickville NSW 2204 | TOD |
| Dulwich Hill | 202 Marrickville Rd, Marrickville NSW 2204 | TOD |
| Ashfield | Ashfield Station, NSW 2131 | TOD |
| Croydon | Croydon Station, NSW 2132 | TOD |

### Control (Non-TOD)

| Address | Expected |
|---------|----------|
| 14 Hunter St, Lewisham NSW 2049 | No TOD |
| 3 Wilkinson Ln, Telopea NSW 2117 | No TOD |

---

## What to Look For in Layers

### Potential TOD Layer Names (Based on NSW Planning Portal)

Check if any of these appear:

**Primary TOD Layers:**
- `Transport Oriented Development Sites Map`
- `TOD Precinct`
- `SEPP Housing 2021`
- `SEPP (Housing) 2021 - TOD`

**Accelerated TOD:**
- `Accelerated TOD Precincts`
- `Accelerated Transport Oriented Development`
- `Priority Precincts`

**HIA Layers:**
- `Housing Infrastructure Areas`
- `HIA Map`
- `State Significant Development`

**Generic SEPP Layers:**
- Anything with "SEPP" and "Housing"
- Anything with "Transport"
- Anything with "Station"

---

## Keywords Being Searched

The audit searches for these keywords (case-insensitive):
- `transport`
- `tod`
- `housing`
- `accelerated`
- `hia`
- `infrastructure`
- `station`
- `precinct`

If ANY layer name contains these, it will be flagged.

---

## Recording Results

### Test Results Table

| Address | Layers Found | TOD Layer? | Layer Name |
|---------|--------------|------------|------------|
| 370 Illawarra Rd | 15 | ❓ | ? |
| 202 Marrickville Rd | 15 | ❓ | ? |
| 14 Hunter St (control) | 14 | ❌ | N/A |

**Fill in this table during testing**

---

## Troubleshooting

### "Cannot read property 'length' of undefined"
- API might be failing before reaching layer extraction
- Check network tab for failed requests
- Verify NSW Planning Portal is responding

### No audit logs in console
- Clear browser cache
- Check dev server is running latest code
- Verify file was saved: `frontend-nextjs/lib/nsw-planning-portal.ts`

### Logs appear but no layers
- NSW API might be rate limiting
- Try different address
- Check network tab for 429 errors

---

## Next Steps Based on Results

### If TOD Layers Found (Scenario A)
1. Document which layer names contain TOD data
2. Update `TOD_HIA_INTEGRATION_PLAN.md` with findings
3. Skip Phase 3 entirely
4. Proceed to Phase 5: Add extraction logic for those specific layer names

### If TOD Layers NOT Found (Scenario B)
1. Confirm with 3 different TOD addresses
2. Document that separate API call is needed
3. Proceed to Phase 3: Implement `getTODLayers()` method
4. Add to `Promise.all` for parallel execution

---

## Completion Checklist

- [ ] Dev server running
- [ ] Tested with 370 Illawarra Rd (TOD address)
- [ ] Tested with 14 Hunter St (non-TOD control)
- [ ] Reviewed console audit logs
- [ ] Documented layer names found
- [ ] Recorded TOD layers (if any) in test results table
- [ ] Decision made: Skip Phase 3 OR Implement Phase 3
- [ ] Updated `TOD_HIA_INTEGRATION_PLAN.md` with findings
- [ ] Committed logging changes

---

## Commit After Testing

Once testing is complete, commit the logging:

```bash
git add frontend-nextjs/lib/nsw-planning-portal.ts
git commit -m "test: Add comprehensive layer audit logging for Phase 2 TOD detection

Added detailed logging to extractPlanningConstraints to identify if
TOD/HIA layers are already included in NSW Planning Portal EPI response.

Searches for keywords: transport, tod, housing, accelerated, hia,
infrastructure, station, precinct

Results will determine if Phase 3 (separate API call) is needed.

Phase 2 of TOD/HIA integration plan (TOD_HIA_INTEGRATION_PLAN.md)
"
```

---

## Contact/Questions

If unclear what to look for:
1. Share console logs in issue/PR
2. Include test address used
3. Include screenshot of "LAYER COVERAGE AUDIT" section

---

**Status:** Ready for Testing
**Est. Time:** 15-30 minutes
**Required:** Dev server + browser console
