# V2 Configuration Testing Addresses

**Date**: 2025-10-12
**Purpose**: Test external JSON config system (`lga-mappings.json`) vs old hardcoded mappings

---

## 🎯 Test Strategy

### What We're Testing:
1. ✅ Postcode-based council matching
2. ✅ Suburb-based council matching
3. ✅ Special case handling (Newtown boundary)
4. ✅ All 3 former councils (Ashfield, Leichhardt, Marrickville)
5. ✅ V2 returns same results as V1

---

## 📍 Test Addresses (Copy/Paste Ready)

### Test 1: Marrickville (Postcode 2204)
```
180 Addison Road Marrickville 2204
```
**Expected**:
- Former council: `Marrickville`
- Zone: `R2` (from Planning API)
- Should show: Marrickville DCP provisions

**Why**: Tests postcode `2204` → `Marrickville` mapping from config

---

### Test 2: Leichhardt (Postcode 2040)
```
123 Parramatta Road Leichhardt 2040
```
**Expected**:
- Former council: `Leichhardt`
- Zone: Likely `R2` or `B1`
- Should show: Leichhardt DCP provisions

**Why**: Tests postcode `2040` → `Leichhardt` mapping from config

---

### Test 3: Ashfield (Postcode 2131)
```
45 Liverpool Road Ashfield 2131
```
**Expected**:
- Former council: `Ashfield`
- Zone: Likely `R2` or `B2`
- Should show: Ashfield DCP provisions

**Why**: Tests postcode `2131` → `Ashfield` mapping from config

---

### Test 4: Newtown Boundary - Marrickville Side (CRITICAL TEST)
```
King Street Newtown 2204
```
**Expected**:
- Former council: `Marrickville` ← This was the bug we fixed!
- Zone: Likely `B1` (commercial)
- Should show: **Marrickville B1 commercial provisions** (4 hardcoded setback rules)

**Why**:
- Tests special case handling
- Old V1 bug: Newtown suburb matched to Leichhardt
- V2 fix: Postcode `2204` correctly maps to Marrickville

---

### Test 5: Newtown Boundary - Leichhardt Side
```
King Street Newtown 2042
```
**Expected**:
- Former council: `Leichhardt`
- Zone: Depends on location
- Should show: Leichhardt provisions

**Why**: Tests same street but different postcode (Newtown spans 2 councils)

---

### Test 6: Petersham (Marrickville)
```
40 Audley Street Petersham 2048
```
**Expected**:
- Former council: `Marrickville`
- Zone: Likely `R2`
- Should show: Marrickville DCP provisions

**Why**: Tests suburb `Petersham` in config

---

### Test 7: Balmain (Leichhardt)
```
20 Darling Street Balmain 2041
```
**Expected**:
- Former council: `Leichhardt`
- Zone: Likely `R2` or `B1`
- Should show: Leichhardt DCP provisions

**Why**: Tests postcode `2041` → `Leichhardt`

---

### Test 8: Haberfield (Ashfield)
```
10 Ramsay Street Haberfield 2045
```
**Expected**:
- Former council: `Ashfield`
- Zone: Likely `R2`
- Should show: Ashfield DCP provisions

**Why**: Tests postcode `2045` → `Ashfield` and suburb `Haberfield`

---

## 🧪 How to Test

### Method 1: Using curl (Fast)
```bash
# Test 1: Marrickville
curl -s -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"R2\",\"lga\":\"INNER WEST\",\"developmentType\":\"dwelling_house\",\"address\":\"180 Addison Road Marrickville 2204\"}" | python -m json.tool

# Test 4: Newtown/Marrickville (CRITICAL - was broken in V1)
curl -s -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"B1\",\"lga\":\"INNER WEST\",\"developmentType\":\"shop\",\"address\":\"King Street Newtown 2204\"}" | python -m json.tool

# Test 5: Newtown/Leichhardt
curl -s -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"B1\",\"lga\":\"INNER WEST\",\"developmentType\":\"shop\",\"address\":\"King Street Newtown 2042\"}" | python -m json.tool
```

### Method 2: Using UI (Thorough)
1. Go to: `http://localhost:3007/assessment`
2. Enter address in search box
3. Check right panel for provisions
4. Verify former council matches expected

---

## ✅ Success Criteria

### V2 Config System is Working If:
1. ✅ All 8 addresses return provisions
2. ✅ Each address maps to correct former council
3. ✅ **Test 4 (King Street Newtown 2204) returns Marrickville provisions** (not Leichhardt!)
4. ✅ Console logs show: `[Inner West Mapping] Postcode match: 2204 → Marrickville`
5. ✅ No errors about missing config file

---

## 🔍 What to Look For

### In API Response:
```json
{
  "setbacks": [
    {
      "type": "front_ground",
      "value": "0m",
      "provision_id": 8194,
      "ref_number": "Marrickville DCP C6",
      "section_header": "Street Front Building Line"
    }
  ]
}
```

### In Console Logs:
```
[Inner West Mapping] Postcode match: 2204 → Marrickville
[Constraints API] B1 commercial zone detected, adding hardcoded setback rules...
[Constraints API] Found 4 descriptive setback rules for B1
```

---

## 🐛 Known Issues to Verify Fixed

### Issue 1: Newtown Suburb Bug (V1)
- **Problem**: `'newtown': 'Leichhardt'` hardcoded in V1
- **Fix**: V2 uses postcode priority (2204 → Marrickville, 2042 → Leichhardt)
- **Test**: Test 4 and 5

### Issue 2: Zero Values Bug
- **Problem**: 0m setbacks showed "See provision"
- **Fix**: Explicit null checks in route.ts lines 825-827, 846
- **Test**: Test 4 (should show "0m" for front_ground and side_ground)

---

## 📊 Expected Results Summary

| Test | Address | Postcode | Expected Council | Zone | Key Check |
|------|---------|----------|------------------|------|-----------|
| 1 | Addison Rd Marrickville | 2204 | Marrickville | R2 | Postcode match |
| 2 | Parramatta Rd Leichhardt | 2040 | Leichhardt | R2/B1 | Postcode match |
| 3 | Liverpool Rd Ashfield | 2131 | Ashfield | R2/B2 | Postcode match |
| 4 | King St Newtown | 2204 | **Marrickville** | B1 | **Bug fix!** |
| 5 | King St Newtown | 2042 | Leichhardt | B1 | Boundary |
| 6 | Audley St Petersham | 2048 | Marrickville | R2 | Suburb match |
| 7 | Darling St Balmain | 2041 | Leichhardt | R2/B1 | Postcode match |
| 8 | Ramsay St Haberfield | 2045 | Ashfield | R2 | Suburb match |

---

## 🚀 Quick Test Script

Want to test all 8 at once? Run this:

```bash
# Save as test_v2_config.js
const addresses = [
  { address: "180 Addison Road Marrickville 2204", zone: "R2", type: "dwelling_house", expected: "Marrickville" },
  { address: "123 Parramatta Road Leichhardt 2040", zone: "R2", type: "dwelling_house", expected: "Leichhardt" },
  { address: "45 Liverpool Road Ashfield 2131", zone: "R2", type: "dwelling_house", expected: "Ashfield" },
  { address: "King Street Newtown 2204", zone: "B1", type: "shop", expected: "Marrickville" },
  { address: "King Street Newtown 2042", zone: "B1", type: "shop", expected: "Leichhardt" },
  { address: "40 Audley Street Petersham 2048", zone: "R2", type: "dwelling_house", expected: "Marrickville" },
  { address: "20 Darling Street Balmain 2041", zone: "R2", type: "dwelling_house", expected: "Leichhardt" },
  { address: "10 Ramsay Street Haberfield 2045", zone: "R2", type: "dwelling_house", expected: "Ashfield" }
];

addresses.forEach(async (test, i) => {
  const response = await fetch('http://localhost:3007/api/compliance/constraints', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      zone: test.zone,
      lga: "INNER WEST",
      developmentType: test.type,
      address: test.address
    })
  });
  const data = await response.json();
  console.log(`\nTest ${i+1}: ${test.address}`);
  console.log(`Expected council: ${test.expected}`);
  console.log(`Provisions returned: ${data.setbacks?.length || 0}`);
});
```

---

## 📝 V2 Config Files Reference

### Files Changed:
1. ✅ `config/lga-mappings.json` - External config
2. ✅ `lib/lga-config-loader.ts` - Config loader
3. ✅ `lib/inner-west-mapping-v2.ts` - V2 mapper
4. ✅ `app/api/compliance/constraints/route.ts` - Import changed to V2

### To Rollback (if needed):
```typescript
// In route.ts line 4, change back to:
import { determineFormerCouncilArea } from '@/lib/inner-west-mapping';
```

---

**Status**: Ready for testing! Start with Test 4 (King Street Newtown 2204) - this is the critical test that proves V2 fixes the hardcoding issue.
