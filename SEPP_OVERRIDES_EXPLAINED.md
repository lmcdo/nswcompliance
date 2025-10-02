# SEPP Overrides - Significance & Certifier Workflow

## 1. What Are These SEPP Overrides?

SEPP (State Environmental Planning Policy) provisions **override** local LEP and DCP controls. They are critical because:

### Critical SEPP Overrides Currently Shown:

#### **Provision 16964: Setback Override for Accessory Buildings**
- **Ref:** SEPP Exempt & Complying 3B.24(8)
- **Significance:** Allows sheds, gazebos, cabanas to be built **3m from road** (or abutting) for 50% of boundary
- **Overrides:** Local DCP front setbacks (which might require 6m+)
- **Impact:** Certifier must check this **before** applying DCP controls

#### **Provision 14130: Zoning Exclusion**
- **Ref:** SEPP Exempt & Complying 3D.1
- **Significance:** Says complying development Division 3D **does NOT apply** to zones RU5, R1, R2, R3, R4
- **Critical:** For R2 zones (like Marrickville), this excludes certain complying pathways
- **Impact:** Must check zone compatibility before approving complying development

#### **Provision 16963: Rear Lane Setback Override**
- **Ref:** SEPP Exempt & Complying 3B.24(6)
- **Significance:** If rear boundary has a **lane**, can build within 900mm or abutting for 50% of boundary
- **Overrides:** Local DCP rear setbacks
- **Impact:** Critical for infill development - changes what's permissible

#### **Provision 12638: Coastal Management Definitions**
- **Ref:** SEPP Resilience & Hazards 2.2(1)
- **Significance:** Defines "certified coastal management program"
- **Impact:** Triggers additional assessment for coastal properties

#### **Provisions 13429, 13469: Cross-References**
- **Significance:** Point to other SEPP provisions that may apply
- **Impact:** Certifier must follow the reference chain

---

## 2. Certifier's Workflow

### Step 1: Property Identification
```
Input: Address (e.g., "54 Illawarra Road, Marrickville 2204")
↓
Planning Portal API returns:
- Zone: R2 Low Density Residential
- LGA: Inner West
- FSR: 0.6:1
- Height: 9.5m
- Heritage: No
- Constraints: Flood prone, etc.
```

### Step 2: Development Type Selection
```
User selects: "Dwelling House"
↓
System queries database for applicable provisions:
1. LEP provisions (height, FSR from Planning API)
2. DCP provisions (setbacks, design controls) - filtered by:
   - Zone: R2
   - Development Type: dwelling_house
   - LGA: Marrickville (not Ashfield/Leichhardt)
3. SEPP provisions (overrides) - filtered by:
   - Zone: R2
   - Development Type: dwelling_house
```

### Step 3: Hierarchy Check (CRITICAL)
```
Certifier must check provisions in this order:

1. SEPP (State) - HIGHEST AUTHORITY
   ├─ Provision 14130: Does Division 3D apply? (NO for R2)
   ├─ Provision 16964: Shed setback override (3m allowed)
   └─ Provision 16963: Rear lane setback (900mm allowed)

2. LEP (Local Environmental Plan)
   ├─ Height: 9.5m (from Planning API)
   └─ FSR: 0.6:1 (from Planning API)

3. DCP (Development Control Plan) - LOWEST AUTHORITY
   ├─ Front setback: 6m (from Marrickville DCP)
   ├─ Side setback: 900mm (from Marrickville DCP)
   └─ Rear setback: 6m (from Marrickville DCP)

IF SEPP says "3m setback OK for shed" → DCP "6m front setback" is OVERRIDDEN for that shed.
```

### Step 4: Compliance Matrix
```
Certifier creates a table:

| Control Type | SEPP Value | LEP Value | DCP Value | APPLIES |
|--------------|------------|-----------|-----------|---------|
| Building Height | - | 9.5m | 8.5m (some DCPs) | **9.5m** (LEP wins) |
| Front Setback | 3m (sheds) | - | 6m | **3m for sheds, 6m for house** |
| Rear Setback (lane) | 900mm | - | 6m | **900mm** (SEPP wins) |
| FSR | - | 0.6:1 | - | **0.6:1** (LEP) |
```

### Step 5: Flag Conflicts
```
System highlights:
⚠️ "DCP requires 6m front setback, but SEPP allows 3m for accessory buildings"
✓ "Certifier must determine if proposal is an accessory building"
```

---

## 3. What Changes With Different Development Types?

### Current Implementation: Development Type Dropdown

#### Example 1: **Dwelling House** (dwelling_house)
```
Address: 54 Illawarra Road, Marrickville
Zone: R2
Development Type: Dwelling House

Returns:
✓ LEP: Height 9.5m, FSR 0.6:1
✓ DCP Marrickville 2011:
  - Front setback: 6m
  - Side setback: 900mm
  - Rear setback: 6m
  - Building height: 2-6 storeys
✓ SEPP Overrides:
  - Provision 16964: Shed setback 3m
  - Provision 16963: Rear lane 900mm
  - Provision 14130: Complying dev exclusion
```

#### Example 2: **Secondary Dwelling** (secondary_dwelling)
```
Address: 54 Illawarra Road, Marrickville
Zone: R2
Development Type: Secondary Dwelling

SHOULD Return (currently may not filter correctly):
✓ LEP: Height 9.5m, FSR 0.6:1
✓ DCP Marrickville 2011 - DIFFERENT SECTION:
  - Front setback: 3m (reduced for secondary dwelling)
  - Side setback: 900mm
  - Rear setback: 3m (reduced)
  - Max size: 60m² or 60% of main dwelling
✓ SEPP Overrides - DIFFERENT:
  - Provision XXXX: Secondary dwelling size cap 60m²
  - Provision XXXX: Parking exemption (may not need parking)
```

#### Example 3: **Multi Dwelling Housing** (multi_dwelling)
```
Address: 54 Illawarra Road, Marrickville
Zone: R2
Development Type: Multi Dwelling Housing

SHOULD Return:
✓ LEP: Height 9.5m, FSR 0.6:1
✓ DCP Marrickville 2011 - DIFFERENT SECTION:
  - Front setback: 6m
  - Side setback: 900mm (or 3m between buildings)
  - Rear setback: 6m
  - Deep soil: 15% minimum
  - Communal open space: 25m² per dwelling
✓ SEPP Overrides - DIFFERENT:
  - Provision XXXX: Parking rates (1 space per dwelling)
  - Provision XXXX: Apartment size minimums
```

---

## 4. Checkable Test Examples

### Test 1: Verify Development Type Filtering

#### Test Case A: Dwelling House
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d '{
    "address": "54 ILLAWARRA ROAD MARRICKVILLE 2204",
    "zone": "R2",
    "lga": "INNER WEST",
    "developmentType": "Dwelling House"
  }' | grep -o '"control_subtype":"[^"]*"' | sort | uniq

Expected:
"control_subtype":"front"
"control_subtype":"rear"
"control_subtype":"side"
"control_subtype":"building_height"
```

#### Test Case B: Secondary Dwelling
```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d '{
    "address": "54 ILLAWARRA ROAD MARRICKVILLE 2204",
    "zone": "R2",
    "lga": "INNER WEST",
    "developmentType": "Secondary Dwelling"
  }' | grep -o '"value_numeric":[^,}]*' | sort | uniq

Expected (DIFFERENT VALUES):
"value_numeric":3    # Front setback reduced for secondary dwelling
"value_numeric":60   # Max size 60m²
```

#### Test Case C: Check SEPP Overrides Change
```bash
# Dwelling House - should show shed override
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d '{"address":"54 ILLAWARRA ROAD MARRICKVILLE 2204","zone":"R2","lga":"INNER WEST","developmentType":"Dwelling House"}' \
  | grep "16964"

Expected: ✓ Found (shed setback override applies)

# Multi Dwelling - should NOT show shed override
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d '{"address":"54 ILLAWARRA ROAD MARRICKVILLE 2204","zone":"R2","lga":"INNER WEST","developmentType":"Multi Dwelling Housing"}' \
  | grep "16964"

Expected: ✗ Not found (shed override doesn't apply to multi-dwelling)
```

---

## 5. Current Issues & Required Fixes

### Issue 1: Development Type Filtering Not Complete
**Problem:** SEPP overrides show the same for all development types
**Fix Required:** Filter SEPP provisions by `development_type` column in database

### Issue 2: No Visual Hierarchy
**Problem:** Certifier can't see which provision "wins" in conflicts
**Fix Required:** Add visual indicators:
```
✓ SEPP Override Active (highest authority)
↓ LEP Control (middle authority)
↓ DCP Control (lowest authority, may be overridden)
```

### Issue 3: No Explanation of Override Impact
**Problem:** Shows "SEPP Override" but doesn't explain WHAT it overrides
**Fix Required:** Add explainer text:
```
⚠️ SEPP Provision 16964 overrides DCP front setback for:
   - Sheds, gazebos, cabanas
   - Allows 3m instead of 6m
   - Applies to 50% of boundary length only
```

---

## 6. Recommended Next Steps

1. **Add Development Type Filtering to SEPP Query**
   - Modify `/api/compliance/constraints` to filter SEPPs by `development_type`
   - Currently returns all SEPP overrides; should filter to relevant ones

2. **Add Override Impact Explanation**
   - Each SEPP provision should show:
     - What local control it overrides
     - Conditions for override to apply
     - Limitations (e.g., "50% of boundary only")

3. **Add Visual Hierarchy Indicators**
   - SEPP provisions: Red badge "OVERRIDE"
   - LEP provisions: Blue badge "STATUTORY"
   - DCP provisions: Green badge "GUIDELINE" (can be overridden)

4. **Create Conflict Detection**
   - If SEPP says 3m and DCP says 6m → Flag as "SEPP Override Active"
   - Show "Original DCP: 6m → SEPP Override: 3m (for sheds only)"

5. **Add Development Type-Specific Documentation**
   - Link to DCP section that applies to that development type
   - Show typical controls for that type (e.g., "Secondary dwellings typically have reduced setbacks")