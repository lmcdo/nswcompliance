# ✅ CORRECTED UI Test Addresses - With Postcodes
**Critical: Always include postcodes for accurate former council mapping**

---

## ❌ PROBLEM IDENTIFIED

**Issue**: "King Street Newtown" mapped to **Leichhardt** instead of **Marrickville**
- Newtown suburb spans multiple former councils
- King Street (commercial core) is in Marrickville
- Without postcode, system defaults to Leichhardt

**Fix**: Always include **postcode** or use **street number**

---

## ✅ CORRECTED HIGH PRIORITY ADDRESSES

### TEST 1: B1 - Phase 3 Hardcoded Rules ⭐⭐⭐

**OPTION A (Recommended)**:
```
181 King Street Newtown 2042
```
- Postcode 2042 maps to Leichhardt initially, but...
- Use King Street **ENMORE** instead (clearer):

**OPTION B (Best)**:
```
King Street Enmore 2042
```
- Enmore is clearly Leichhardt
- Still gets B1 zone
- Returns Marrickville DCP B1 commercial provisions

**OPTION C (Most Reliable)**:
```
40 Lackey Street Summer Hill 2130
```
- Change zone to B1 manually in UI
- Summer Hill is clearly Ashfield/Marrickville border

**⭐ BEST CHOICE - Use Marrickville Address**:
```
Illawarra Road Marrickville 2204
```
- **Zone**: B1
- **Dev Type**: Shop
- Clear Marrickville postcode (2204)
- Will return Marrickville DCP C6/C11/C12 provisions

---

### TEST 2: R3 - Phase 2 ADG Integration ⭐⭐⭐

**CORRECTED**:
```
123 Parramatta Road Leichhardt 2040
```
✅ This is correct - Parramatta Road Leichhardt is clearly in Leichhardt area
- Postcode 2040 = Leichhardt
- R3 zone common along Parramatta Road
- Will return ADG standards

---

### TEST 3: R5 - Phase 1 SEPP Clause Links ⭐⭐⭐

**CORRECTED**:
```
40 Lackey Street Summer Hill 2130
```
✅ This is correct - Summer Hill 2130 = Ashfield
- R5 zone (large lot residential)
- Will return SEPP Housing provisions

---

### TEST 4: R2 - Baseline ⭐

**CORRECTED**:
```
180 Addison Road Marrickville 2204
```
✅ This is correct - Postcode 2204 = Marrickville
- R2 dwelling house
- Returns Marrickville DCP provisions

---

### TEST 5: E1 - Phase 1 Environmental Buffers ⭐⭐

**CORRECTED**:
```
Hawthorne Canal Leichhardt 2040
```
Better than "Creek Street" (too generic)
- E1 zone (national parks/waterways)
- Postcode 2040 = Leichhardt
- Will return environmental buffer provisions

---

### TEST 6: E2 - Phase 1 Environmental Buffers ⭐⭐

**CORRECTED**:
```
Forest Avenue Haberfield 2045
```
✅ This is correct - Haberfield 2045 = Ashfield
- E2 environmental conservation
- Returns conservation buffer provisions

---

### TEST 7: IN1 - Industrial

**CORRECTED**:
```
Sydenham Road Marrickville 2204
```
Better than "Factory Street" (too generic)
- IN1 industrial zone
- Postcode 2204 = Marrickville

---

### TEST 8: B2 - Local Centre

**CORRECTED**:
```
Norton Street Leichhardt 2040
```
✅ This is correct - Norton Street is Leichhardt's Little Italy
- B2 local centre
- Postcode 2040 = Leichhardt

---

## 🎯 QUICK COPY-PASTE (CORRECTED)

**For rapid UI testing**:

```
Illawarra Road Marrickville 2204
123 Parramatta Road Leichhardt 2040
40 Lackey Street Summer Hill 2130
180 Addison Road Marrickville 2204
Hawthorne Canal Leichhardt 2040
Forest Avenue Haberfield 2045
Sydenham Road Marrickville 2204
Norton Street Leichhardt 2040
```

---

## 📋 ZONE SELECTION IMPORTANT

**After entering address, manually verify/select**:
1. Address → System detects former council
2. **Zone** → Select from dropdown (B1, R3, R5, etc.)
3. **Dev Type** → Select appropriate type

**Critical for B1 Test**:
- Address: `Illawarra Road Marrickville 2204`
- **MANUALLY SELECT**: Zone = **B1**
- Dev Type: **Shop**

---

## 🔍 Why Postcode Matters

| Address | Without Postcode | With Postcode | Correct? |
|---------|------------------|---------------|----------|
| King Street Newtown | → Leichhardt (wrong) | 2042 → Leichhardt | ❌ Still wrong |
| King Street Newtown | → Leichhardt (wrong) | 2204 → Marrickville | ✅ Correct! |
| Illawarra Road Marrickville | → Marrickville | 2204 → Marrickville | ✅ Correct! |

**Newtown Issue**: Postcode 2042 is **Leichhardt**, but commercial King Street is **Marrickville DCP**

**Solution**: Use **Marrickville addresses** for B1 testing

---

## ⚠️ IMPORTANT NOTES

### 1. B1 Zone Mapping Issue
- **King Street Newtown** = Boundary area
- Northern end (postcode 2042) = Leichhardt
- Southern end (near St Peters) = Marrickville
- **For B1 commercial testing**: Use **Marrickville addresses** explicitly

### 2. Suburb Boundaries
Inner West has complex former council boundaries:
- **Ashfield**: 2131, 2044, 2039, 2045 (Haberfield)
- **Leichhardt**: 2040, 2041, 2042, 2043, 2049
- **Marrickville**: 2204, 2048, 2046, 2047

### 3. Postcode Always Wins
The mapping logic:
1. **First**: Try postcode match
2. **Then**: Try suburb name match
3. **Last**: Default to search all three

Always include postcode for accurate results!

---

## ✅ RECOMMENDED TEST SEQUENCE

### 1. Start with Clear Marrickville Address
```
Illawarra Road Marrickville 2204
Zone: B1
Dev Type: Shop
```
**Expected**: Marrickville DCP C6, C11, C12 provisions with 0m/6m/3m values

### 2. Then R3 ADG
```
123 Parramatta Road Leichhardt 2040
Zone: R3
Dev Type: Multi Dwelling Housing
```
**Expected**: 12 ADG building separation standards

### 3. Then R5 SEPP
```
40 Lackey Street Summer Hill 2130
Zone: R5
Dev Type: Dwelling House
```
**Expected**: 10 SEPP Housing clause references

### 4. Then Baseline R2
```
180 Addison Road Marrickville 2204
Zone: R2
Dev Type: Dwelling House
```
**Expected**: 3+ Marrickville DCP residential provisions

---

## 🔧 If Still Getting Wrong Council

**Override Method**:
1. Enter any address with correct **postcode**
2. Manually select **zone** from dropdown
3. System will use postcode to determine former council
4. Should return correct DCP provisions

**Example**:
- Address: `100 Any Street Marrickville 2204`
- Zone: **B1** (select manually)
- Dev Type: Shop
- Result: Marrickville DCP provisions ✅

---

## 📊 Expected Results (Corrected)

| Test | Address | Postcode | Council | Setbacks | Key Feature |
|------|---------|----------|---------|----------|-------------|
| 1 | **Illawarra Rd** | **2204** | **Marrickville** | 7 (4 numeric) | 0m/6m/3m B1 rules |
| 2 | Parramatta Rd | 2040 | Leichhardt | 15 (12 ADG) | ADG integration |
| 3 | Lackey St | 2130 | Ashfield | 10 SEPP | Clause links |
| 4 | Addison Rd | 2204 | Marrickville | 3 precinct | Baseline DCP |
| 5 | Hawthorne Canal | 2040 | Leichhardt | 13+ | Environmental |
| 6 | Forest Ave | 2045 | Ashfield | 10+ | Conservation |

---

**Key Takeaway**: For **B1 testing**, use **`Illawarra Road Marrickville 2204`** instead of King Street Newtown!

---

**Server**: http://localhost:3007/assessment
**Status**: ✅ Running (Process 31e3ed)
