# Targeted Zone Testing Addresses - Inner West LGA
**All Zones Coverage - Phase 1, 2, 3 Validation**

---

## Residential Zones

### R2 - Low Density Residential ⭐ BASELINE
**Address**: `180 Addison Road, Marrickville NSW 2204`
**Zone**: R2
**Development**: `dwelling_house`
**Expected**:
- Front setback: 6m
- Side setback: 0.9m
- Rear setback: 6m
- Source: Marrickville DCP (established baseline)

**Test Command**:
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"R2\",\"lga\":\"INNER WEST\",\"developmentType\":\"dwelling_house\",\"address\":\"180 Addison Road Marrickville 2204\"}"
```

---

### R3 - Medium Density Residential ⭐ PHASE 2 (ADG Integration)
**Address**: `123 Parramatta Road, Leichhardt NSW 2040`
**Zone**: R3
**Development**: `multi_dwelling_housing`
**Expected**:
- 12 ADG building separation standards
- Habitable-to-habitable: 12m (up to 12m height)
- Habitable-to-habitable: 18m (12-25m height)
- Source: ADG integration (Phase 2)

**Test Command**:
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"R3\",\"lga\":\"INNER WEST\",\"developmentType\":\"multi_dwelling_housing\",\"address\":\"123 Parramatta Road Leichhardt 2040\"}"
```

---

### R5 - Large Lot Residential ⭐ PHASE 1 (SEPP Clause Links)
**Address**: `40 Lackey Street, Summer Hill NSW 2130`
**Zone**: R5
**Development**: `dwelling_house`
**Expected**:
- SEPP Housing 2021 clause references
- Clause 3C.28 (side boundary setbacks)
- Clause 3A.15, 3A.16 (various setbacks)
- Source: SEPP Housing integration (Phase 1)

**Test Command**:
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"R5\",\"lga\":\"INNER WEST\",\"developmentType\":\"dwelling_house\",\"address\":\"40 Lackey Street Summer Hill 2130\"}"
```

---

### R1 - General Residential (Not yet optimized)
**Address**: `45 Crystal Street, Petersham NSW 2049`
**Zone**: R1
**Development**: `dwelling_house`
**Expected**: General setback provisions (not yet optimized)

**Test Command**:
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"R1\",\"lga\":\"INNER WEST\",\"developmentType\":\"dwelling_house\",\"address\":\"45 Crystal Street Petersham 2049\"}"
```

---

### R4 - High Density Residential (Similar to R3)
**Address**: `78 Victoria Road, Rozelle NSW 2039`
**Zone**: R4
**Development**: `residential_flat_building`
**Expected**: Similar to R3 (may benefit from ADG standards)

**Test Command**:
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"R4\",\"lga\":\"INNER WEST\",\"developmentType\":\"residential_flat_building\",\"address\":\"78 Victoria Road Rozelle 2039\"}"
```

---

## Commercial Zones

### B1 - Neighbourhood Centre ⭐ PHASE 3 (Hardcoded Rules)
**Address**: `King Street, Newtown NSW 2042`
**Zone**: B1
**Development**: `shop`
**Expected**:
- Front (ground): 0m
- Side (ground): 0m
- Front (upper): 6m
- Secondary (corner): 3m
- Source: Hardcoded rules (Phase 3)

**Test Command**:
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"B1\",\"lga\":\"INNER WEST\",\"developmentType\":\"shop\",\"address\":\"King Street Newtown 2042\"}"
```

---

### B2 - Local Centre
**Address**: `Norton Street, Leichhardt NSW 2040`
**Zone**: B2
**Development**: `shop`
**Expected**: Similar to B1 (not yet optimized)

**Test Command**:
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"B2\",\"lga\":\"INNER WEST\",\"developmentType\":\"shop\",\"address\":\"Norton Street Leichhardt 2040\"}"
```

---

### B4 - Mixed Use
**Address**: `Enmore Road, Newtown NSW 2042`
**Zone**: B4
**Development**: `shop_top_housing`
**Expected**: Mixed-use provisions (commercial + residential)

**Test Command**:
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"B4\",\"lga\":\"INNER WEST\",\"developmentType\":\"shop_top_housing\",\"address\":\"Enmore Road Newtown 2042\"}"
```

---

## Environmental Zones

### E1 - National Parks ⭐ PHASE 1 (Environmental Buffers)
**Address**: `Creek Street, Leichhardt NSW 2040`
**Zone**: E1
**Development**: `dwelling_house`
**Expected**:
- 10-20 environmental buffer provisions
- Riparian buffers
- Biodiversity buffers
- Vegetation buffers
- Source: Environmental buffer search (Phase 1)

**Test Command**:
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"E1\",\"lga\":\"INNER WEST\",\"developmentType\":\"dwelling_house\",\"address\":\"Creek Street Leichhardt 2040\"}"
```

---

### E2 - Environmental Conservation ⭐ PHASE 1 (Environmental Buffers)
**Address**: `Forest Avenue, Haberfield NSW 2045`
**Zone**: E2
**Development**: `dwelling_house`
**Expected**:
- 15-30 environmental buffer provisions
- Waterway setbacks
- Vegetation protection
- Source: Environmental buffer search (Phase 1)

**Test Command**:
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"E2\",\"lga\":\"INNER WEST\",\"developmentType\":\"dwelling_house\",\"address\":\"Forest Avenue Haberfield 2045\"}"
```

---

### E3 - Environmental Management ⭐ PHASE 1 (Environmental Buffers)
**Address**: `River Street, Haberfield NSW 2045`
**Zone**: E3
**Development**: `dwelling_house`
**Expected**:
- 10-20 environmental buffer provisions
- Creek buffers
- Asset protection zones
- Source: Environmental buffer search (Phase 1)

**Test Command**:
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"E3\",\"lga\":\"INNER WEST\",\"developmentType\":\"dwelling_house\",\"address\":\"River Street Haberfield 2045\"}"
```

---

### E4 - Environmental Living
**Address**: `Dobroyd Parade, Haberfield NSW 2045`
**Zone**: E4
**Development**: `dwelling_house`
**Expected**: Environmental provisions (not yet optimized)

**Test Command**:
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"E4\",\"lga\":\"INNER WEST\",\"developmentType\":\"dwelling_house\",\"address\":\"Dobroyd Parade Haberfield 2045\"}"
```

---

## Industrial Zones

### IN1 - General Industrial ⭐ PHASE 1 (Validated Sufficient)
**Address**: `Factory Street, Marrickville NSW 2204`
**Zone**: IN1
**Development**: `industrial`
**Expected**:
- 9 setback provisions
- Front setbacks: 3m or 1.5m
- Status: Validated sufficient (Phase 1)

**Test Command**:
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"IN1\",\"lga\":\"INNER WEST\",\"developmentType\":\"industrial\",\"address\":\"Factory Street Marrickville 2204\"}"
```

---

### IN2 - Light Industrial
**Address**: `Sydenham Road, Marrickville NSW 2204`
**Zone**: IN2
**Development**: `industrial`
**Expected**: Light industrial provisions (similar to IN1)

**Test Command**:
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"IN2\",\"lga\":\"INNER WEST\",\"developmentType\":\"industrial\",\"address\":\"Sydenham Road Marrickville 2204\"}"
```

---

## Special Purpose Zones

### SP2 - Infrastructure
**Address**: `Parramatta Road, Ashfield NSW 2131`
**Zone**: SP2
**Development**: `infrastructure`
**Expected**: Infrastructure-specific provisions

**Test Command**:
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"SP2\",\"lga\":\"INNER WEST\",\"developmentType\":\"infrastructure\",\"address\":\"Parramatta Road Ashfield 2131\"}"
```

---

### RE1 - Public Recreation
**Address**: `Camperdown Memorial Rest Park, Church Street, Newtown NSW 2042`
**Zone**: RE1
**Development**: `recreation_facility`
**Expected**: Recreation-specific provisions

**Test Command**:
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d "{\"zone\":\"RE1\",\"lga\":\"INNER WEST\",\"developmentType\":\"recreation_facility\",\"address\":\"Camperdown Memorial Rest Park Church Street Newtown 2042\"}"
```

---

## Testing Priority Order

### ⭐ HIGH PRIORITY (Phase 1, 2, 3 Validation)
1. **R2** (180 Addison Road) - Baseline dwelling house
2. **B1** (King Street Newtown) - Phase 3 hardcoded rules
3. **R3** (123 Parramatta Road) - Phase 2 ADG integration
4. **R5** (40 Lackey Street) - Phase 1 SEPP clause links
5. **E1/E2/E3** (Creek St, Forest Ave, River St) - Phase 1 environmental buffers
6. **IN1** (Factory Street) - Phase 1 validation

### MEDIUM PRIORITY (Coverage Verification)
7. **B2** (Norton Street) - Commercial zone coverage
8. **B4** (Enmore Road) - Mixed-use coverage
9. **R1/R4** (Crystal St, Victoria Rd) - Residential coverage

### LOW PRIORITY (Completeness)
10. **IN2** (Sydenham Road) - Light industrial
11. **SP2/RE1** (Parramatta Rd, Camperdown Park) - Special zones

---

## Quick Test Script

Save this as `test_all_zones.sh`:

```bash
#!/bin/bash

echo "==================================================="
echo "ZONE COVERAGE TESTING - ALL PHASES"
echo "==================================================="

# Phase 3: B1 Hardcoded Rules
echo -e "\n[TEST 1] B1 - King Street Newtown (Phase 3)"
curl -s -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d '{"zone":"B1","lga":"INNER WEST","developmentType":"shop","address":"King Street Newtown 2042"}' \
  | jq '.data.building_envelope | map(select(.type=="setback")) | length'

# Phase 2: R3 ADG Integration
echo -e "\n[TEST 2] R3 - Parramatta Road (Phase 2 - ADG)"
curl -s -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d '{"zone":"R3","lga":"INNER WEST","developmentType":"multi_dwelling_housing","address":"123 Parramatta Road Leichhardt 2040"}' \
  | jq '.data.building_envelope | map(select(.type=="setback")) | length'

# Phase 1: R5 SEPP Clause Links
echo -e "\n[TEST 3] R5 - Lackey Street (Phase 1 - SEPP)"
curl -s -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d '{"zone":"R5","lga":"INNER WEST","developmentType":"dwelling_house","address":"40 Lackey Street Summer Hill 2130"}' \
  | jq '.data.building_envelope | map(select(.type=="setback")) | length'

# Phase 1: E1 Environmental Buffers
echo -e "\n[TEST 4] E1 - Creek Street (Phase 1 - Buffers)"
curl -s -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d '{"zone":"E1","lga":"INNER WEST","developmentType":"dwelling_house","address":"Creek Street Leichhardt 2040"}' \
  | jq '.data.building_envelope | map(select(.type=="setback")) | length'

# Phase 1: IN1 Validation
echo -e "\n[TEST 5] IN1 - Factory Street (Phase 1 - Validation)"
curl -s -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d '{"zone":"IN1","lga":"INNER WEST","developmentType":"industrial","address":"Factory Street Marrickville 2204"}' \
  | jq '.data.building_envelope | map(select(.type=="setback")) | length'

# Baseline: R2 Dwelling House
echo -e "\n[TEST 6] R2 - Addison Road (Baseline)"
curl -s -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d '{"zone":"R2","lga":"INNER WEST","developmentType":"dwelling_house","address":"180 Addison Road Marrickville 2204"}' \
  | jq '.data.building_envelope | map(select(.type=="setback")) | length'

echo -e "\n==================================================="
echo "TESTING COMPLETE"
echo "==================================================="
```

---

## Expected Results Summary

| Zone | Address | Phase | Expected Setbacks | Status |
|------|---------|-------|-------------------|--------|
| **R2** | 180 Addison Rd | Baseline | 3-5 (6m front, 0.9m side, 6m rear) | ✅ Established |
| **R3** | Parramatta Rd | Phase 2 | 12 ADG standards | ✅ Integrated |
| **R5** | Lackey St | Phase 1 | 10 SEPP clause refs | ✅ Linked |
| **B1** | King St | Phase 3 | 4 hardcoded (0m, 0m, 6m, 3m) | ✅ Complete |
| **E1** | Creek St | Phase 1 | 10-20 environmental buffers | ✅ Re-indexed |
| **E2** | Forest Ave | Phase 1 | 15-30 environmental buffers | ✅ Re-indexed |
| **E3** | River St | Phase 1 | 10-20 environmental buffers | ✅ Re-indexed |
| **IN1** | Factory St | Phase 1 | 9 industrial setbacks | ✅ Validated |

---

**Total Coverage**: 8 zones optimized (R2, R3, R5, B1, E1, E2, E3, IN1)
**Test Priority**: Start with HIGH PRIORITY tests (1-6) to validate Phase 1, 2, 3 improvements

---

**Ready to test!** Server starting at http://localhost:3007
