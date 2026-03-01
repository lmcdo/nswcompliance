# NSW Apartment Design Guide - Building Separation Standards

**Source**: NSW Department of Planning - Apartment Design Guide
**Document**: Part 3 - Siting the Development
**Section**: 3F Visual Privacy - Objective 3F-1
**URL**: https://www.planning.nsw.gov.au/sites/default/files/2023-03/apartment-design-guide-part-3-siting-the-development.pdf
**Legal Status**: **STATUTORY** (Referenced by SEPP (Housing) 2021)
**Last Updated**: March 2023

---

## Design Criteria 1: Minimum Building Separation Distances

Separation between windows and balconies is provided to ensure visual privacy is achieved. **Minimum required separation distances from buildings to the side and rear boundaries** are as follows:

| Building Height | Habitable Rooms & Balconies (to boundary) | Non-Habitable Rooms (to boundary) |
|----------------|------------------------------------------|----------------------------------|
| **Up to 12m** (4 storeys) | **6m** | **3m** |
| **Up to 25m** (5-8 storeys) | **9m** | **4.5m** |
| **Over 25m** (9+ storeys) | **12m** | **6m** |

### Key Notes:

1. **Between Buildings on Same Site**:
   Separation distances should **combine** required building separations depending on the type of room.
   - Example: 6m (Building A habitable) + 6m (Building B habitable) = **12m total** between habitable windows

2. **Gallery Access**:
   Gallery access circulation should be treated as **habitable space** when measuring privacy separation distances between neighbouring properties.

3. **Mixed Use Buildings**:
   For residential buildings next to commercial buildings:
   - Retail, office spaces, commercial balconies → use **habitable room distances**
   - Service and plant areas → use **non-habitable room distances**

4. **Transition to Lower Density Zones**:
   Apartment buildings should have an **additional 3m separation** (in addition to table requirements) when adjacent to a different zone that permits lower density residential development.
   - Example: R3 apartment next to R2 low density = 6m + 3m = **9m minimum to boundary**

5. **Blank Walls**:
   **No separation required** between blank walls (walls without windows).

6. **Corner Windows**:
   Direct lines of sight should be avoided for windows and balconies across corners.

---

## Application to Setback Resolution System

### For Single Dwellings (Dwelling Houses, Dual Occupancy)

**Ground floor**: Use DCP setback (e.g., Inner West DCP: 0.9m side setback)

**Upper floors (first, second)**:
- If DCP doesn't specify → Apply **privacy multipliers**:
  - First floor: 1.5x ground floor (min 1.5m)
  - Second floor: 2.0x ground floor (min 3.0m)
- Rationale: Common law privacy + BCA fire separation

### For Multi-Dwelling Developments (Up to 4 Storeys)

**Building height up to 12m (4 storeys)**:
- Habitable rooms/balconies: **6m to boundary** (ADG 3F-1)
- Non-habitable rooms: **3m to boundary** (ADG 3F-1)
- Status: **STATUTORY** - requires certifier approval

### For Apartment Buildings (5-8 Storeys)

**Building height 12m-25m (5-8 storeys)**:
- Habitable rooms/balconies: **9m to boundary** (ADG 3F-1)
- Non-habitable rooms: **4.5m to boundary** (ADG 3F-1)
- Status: **STATUTORY** - requires certifier approval

### For High-Rise Apartments (9+ Storeys)

**Building height over 25m (9+ storeys)**:
- Habitable rooms/balconies: **12m to boundary** (ADG 3F-1)
- Non-habitable rooms: **6m to boundary** (ADG 3F-1)
- Status: **STATUTORY** - requires certifier approval

---

## Updated Fallback Resolution Logic

```
Query: Side setback for R3 zone, multi-dwelling housing, 3rd floor, main dwelling

Step 1: Check DCP
→ No explicit rule for "third floor"

Step 2: Check building height
→ 3rd floor ≈ 9-10m height → Falls in "up to 12m" category

Step 3: Apply ADG 3F-1
→ Building height up to 12m, habitable room → **6m to boundary**

Result:
  setback_meters: 6.0
  source_type: fallback (statutory)
  source_reference: NSW Apartment Design Guide Section 3F-1
  calculation_method: ADG Table - up to 12m height, habitable rooms
  reliability: statutory
  warnings: [NO_EXPLICIT_RULE, SEPP_HOUSING_APPLIES, REQUIRES_CERTIFIER]
  requires_approval: true
```

---

## Database Implementation

### Updated Fallback Rule

```sql
INSERT INTO setback_fallback_rules (
  rule_name,
  rule_description,
  applies_when_missing,
  development_type,
  storey_level,
  boundary_type,
  resolution_method,
  multiplier,
  absolute_minimum_meters,
  calculation_formula,
  authority_source,
  authority_clause,
  legal_basis,
  reliability_level,
  requires_certifier_approval,
  notes
) VALUES (
  'ADG 3F-1: Multi-Dwelling Up to 4 Storeys (Habitable)',
  'Apartment Design Guide building separation for habitable rooms - up to 12m height',
  ARRAY['storey_level'],
  ARRAY['multi_dwelling_housing', 'residential_flat_building', 'shop_top_housing'],
  ARRAY['first', 'second', 'third', 'fourth'],
  ARRAY['side', 'rear'],
  'minimum_absolute',
  NULL,
  6.0,
  'ADG Table 3F-1: Up to 12m (4 storeys) - Habitable rooms = 6m to boundary',
  'NSW Apartment Design Guide - Part 3: Siting the Development',
  'Section 3F-1 Visual Privacy - Design Criteria 1',
  'SEPP (Housing) 2021 - Apartment Design Guide (statutory)',
  'statutory',
  true,
  'Statutory requirement for multi-dwelling developments. Measured to side/rear boundary for habitable rooms and balconies.'
);
```

---

## Frontend Display Example

```
┌─────────────────────────────────────────────────────────────┐
│ Side Setback Requirements - Multi-Dwelling (R3 Zone)        │
├─────────────────────────────────────────────────────────────┤
│ Ground floor:  0.9m                                          │
│   Source: Inner West DCP 2016 DS4.3                          │
│   Status: ✓ DCP Requirement                                  │
├─────────────────────────────────────────────────────────────┤
│ First - Fourth floor:   6.0m                                 │
│   Source: NSW Apartment Design Guide Section 3F-1            │
│   Authority: SEPP (Housing) 2021 (STATUTORY)                 │
│   Criteria: Up to 12m height, habitable rooms to boundary    │
│   ⚠️ Requires certifier approval                             │
│   ⚠️ DCP does not specify upper floor setbacks               │
└─────────────────────────────────────────────────────────────┘

📋 Additional Requirements:
  - Between buildings on same site: 12m separation (6m + 6m)
  - Gallery access = habitable space (use 6m not 3m)
  - Blank walls: no separation required
  - Adjacent to R2 zone: Add 3m (total 9m)

💡 This is a statutory requirement under SEPP (Housing) 2021.
   Engage a licensed certifier for approval.
```

---

## Reliability Assessment

| Source | Legal Status | Certifier Approval Required? | Notes |
|--------|-------------|----------------------------|-------|
| ADG Section 3F-1 | **STATUTORY** | Yes | Referenced by SEPP (Housing) 2021 |
| DCP ground floor | Statutory | No | Direct provision |
| Privacy multipliers (1.5x, 2x) | Industry standard | No | For single dwellings only |

**Bottom Line**: ADG building separation standards are **legally binding** for multi-dwelling and apartment developments. They're not "fallback guidance" - they're **statutory requirements**.

For single dwelling houses (1-2 storeys), DCPs take precedence, and privacy multipliers fill gaps as industry standard practice.
