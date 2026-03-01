# DCP Philosophical Differences: Ashfield vs Leichhardt vs Marrickville

## Executive Summary

The three DCPs represent fundamentally different organizational philosophies:

| Council | Philosophy | Primary Organizer | Filtering Potential |
|---------|------------|-------------------|---------------------|
| **Ashfield** | Topic-centric | What issue? | Low (mostly heritage/precinct) |
| **Leichhardt** | Topic + Place | What issue? Where? | Low (mostly precinct) |
| **Marrickville** | Zone/Dev-type centric | Who? What zone? | High (explicit zone mapping) |

---

## Ashfield DCP 2016: Topic-Centric

### Structure Analysis (1,526 actionable provisions)

| Chapter | Provisions | Purpose | Filtering Logic |
|---------|------------|---------|-----------------|
| **A** | 216 | Miscellaneous | ALL - admin matters |
| **B** | 9 | Public Domain | ALL - public works |
| **C** | 188 | Sustainability | ALL - environmental |
| **D** | 197 | Precinct Guidelines | PRECINCT - 17 precincts |
| **E1** | 907 | Heritage | HERITAGE SITE CONDITION |
| **F** | 9 | Development Category | DEV-TYPE (but nearly empty!) |

### Key Insight: Heritage Dominates

59% of Ashfield provisions are heritage (Chapter E1). The DCP assumes:
- If you're doing heritage work, you need detailed heritage controls
- If you're not, you need general sustainability/admin controls
- Very little zone-specific guidance - Ashfield didn't bother with "R2 vs R3" distinctions

### Filtering Strategy for Ashfield

```
User enters address
    |
    v
Is property heritage item/HCA?
    |
    +-- YES --> Show Chapter E1 (907 provisions) + Chapters A,B,C
    |
    +-- NO --> Show Chapters A,B,C only (413 provisions)
    |
    v
Is property in a precinct?
    |
    +-- YES --> Also show relevant Chapter D provisions
```

**Implication**: Zone filtering has minimal value for Ashfield. The primary filter is **heritage site condition**.

---

## Leichhardt DCP 2013: Topic + Place

### Structure Analysis (2,989 actionable provisions)

| Part | Provisions | Purpose | Filtering Logic |
|------|------------|---------|-----------------|
| **A** | 128 | Introduction | ALL - admin |
| **C Section 1** | 1,554 | Place (General) | ALL - built form controls |
| **C Section 2** | 173 | Distinctive Neighbourhoods | PRECINCT - 24 neighbourhoods |
| **D** | 270 | Energy | ALL - sustainability |
| **E** | 357 | Water | ALL - WSUD |
| **F** | 21 | Food | DEV-TYPE (food premises only) |
| **G** | 486 | Neighbourhoods | PRECINCT - location-specific |

### Key Insight: Part C Section 1 is the Bulk

52% of Leichhardt provisions are in Part C Section 1 "Place" - a massive general chapter covering:
- Setbacks (75 mentions)
- Heights (78 mentions)
- Parking (219 mentions)
- Landscaping (165 mentions)
- Heritage (153 mentions - even though there's no dedicated heritage chapter!)
- Privacy (15 mentions)
- Solar access (21 mentions)

This chapter applies to **ALL development** regardless of zone. Leichhardt's approach is:
> "Here are the generic built form controls. If your property is in a Distinctive Neighbourhood, check Part C Section 2 and Part G for additional/modified controls."

### Filtering Strategy for Leichhardt

```
User enters address
    |
    v
Show Part A, C Section 1, D, E always (~2,309 provisions)
    |
    v
Is property in a Distinctive Neighbourhood?
    |
    +-- YES --> Show Part C Section 2 provisions for that neighbourhood
    |
    v
Is property in a Part G Neighbourhood?
    |
    +-- YES --> Show Part G provisions for that neighbourhood
    |
    v
Is development food-related?
    |
    +-- YES --> Show Part F (21 provisions)
```

**Implication**: Zone filtering has almost no value for Leichhardt. The primary filters are:
1. **Precinct/Neighbourhood location** (spatial)
2. **Food premises dev-type** (only 21 provisions)

---

## Marrickville DCP 2011: Zone/Dev-Type Centric

### Structure Analysis (1,051 actionable provisions)

| Part | Provisions | Purpose | Filtering Logic |
|------|------------|---------|-----------------|
| **1** | 15 | Statutory Info | ALL |
| **2** | 186 | General Controls | ALL - parking, landscaping, etc. |
| **3** | 34 | Subdivision | SUBDIVISION dev-type |
| **4.1** | 42 | Low Density Residential | **R2 zone + dwelling house** |
| **4.2** | 16 | Multi Dwelling/RFB | **R3/R4 zone + multi-dwelling** |
| **4.3** | 8 | Boarding Houses | Boarding house dev-type |
| **5** | 35 | Commercial/Mixed Use | **B zones + commercial** |
| **6** | 39 | Industrial | **IN zones + industrial** |
| **7.1** | 5 | Childcare | Childcare dev-type |
| **7.3** | 18 | Sex Industry | Restricted zones + sex premises |
| **8** | 320 | Heritage | HERITAGE SITE CONDITION |
| **9** | 200 | Precincts | PRECINCT - 48 precincts |

### Key Insight: Explicit Zone/Dev-Type Mapping

Marrickville is the only DCP with explicit zone-based chapters. If a user is in:
- **R2 zone** --> Part 4.1 applies, Parts 4.2/5/6 DO NOT apply
- **R3/R4 zone** --> Part 4.2 applies, Part 4.1/5/6 DO NOT apply
- **B zone** --> Part 5 applies, Parts 4.x/6 DO NOT apply
- **IN zone** --> Part 6 applies, Parts 4.x/5 DO NOT apply

This is the only DCP where zone filtering actually reduces provision count significantly.

### Filtering Strategy for Marrickville

```
User enters address
    |
    v
Planning Portal returns: zone = "R2"
    |
    v
Show Part 1, 2 always (~201 provisions)
    |
    v
zone == R2?
    +-- YES --> Show Part 4.1 (42 provisions)
    |
zone == R3 or R4?
    +-- YES --> Show Part 4.2 (16 provisions)
    |
zone in [B1,B2,B3,B4...]?
    +-- YES --> Show Part 5 (35 provisions)
    |
zone in [IN1,IN2...]?
    +-- YES --> Show Part 6 (39 provisions)
    |
    v
Is property heritage?
    +-- YES --> Show Part 8 (320 provisions)
    |
    v
Is property in a precinct?
    +-- YES --> Show Part 9 provisions for that precinct
```

**Implication**: Marrickville is the ONLY DCP where zone filtering has significant value.

---

## Implications for Application Design

### 1. Unified Filtering Won't Work Equally

A naive approach of "filter by zone for all councils" would:
- Work well for Marrickville (28% zone-specific)
- Be nearly useless for Ashfield (2.1% zone-specific)
- Be nearly useless for Leichhardt (2.4% zone-specific)

### 2. Council-Specific UX May Be Needed

| Council | Primary Filter UX | Secondary Filter |
|---------|-------------------|------------------|
| Ashfield | "Is this a heritage property?" toggle | Precinct dropdown |
| Leichhardt | Neighbourhood/precinct selector | Food premises toggle |
| Marrickville | Zone auto-detected from address | Dev-type dropdown |

### 3. Heritage is the Universal Filter

All three DCPs have substantial heritage chapters that should only show for heritage properties:
- Ashfield: 907 provisions (59%)
- Marrickville: 320 provisions (30%)
- Leichhardt: Heritage embedded in Part C Section 1 (153 mentions)

### 4. "General" Provisions are the Bulk

Most provisions in Ashfield and Leichhardt are truly general - they apply to ALL development:

| Council | General Provisions | Filterable |
|---------|-------------------|------------|
| Ashfield | 413 (27%) non-heritage, non-precinct | 9 (0.6%) |
| Leichhardt | 2,309 (77%) topic chapters | 21 (0.7%) |
| Marrickville | 201 (19%) Part 1+2 | 130 (12%) |

---

## Recommended Approach

### For Ashfield/Leichhardt (Topic-Centric)

Accept that most provisions will show for most properties. Focus on:
1. **Heritage filter** - biggest impact
2. **Precinct filter** - second biggest impact
3. **Category grouping** - organize the "wall of provisions" by topic

### For Marrickville (Zone/Dev-Type Centric)

Exploit the explicit zone/dev-type structure:
1. **Zone filter** - actually reduces provision count
2. **Dev-type filter** - further reduces count
3. **Heritage filter** - standard
4. **Precinct filter** - final layer

### Universal Strategy

```
48,374 total --> 11,835 actionable (existing)
           |
           v
     Heritage filter (if property is NOT heritage)
           |
           +-- Ashfield: 1,526 --> 619 (-59%)
           +-- Leichhardt: 2,989 --> 2,989 (0% - heritage embedded)
           +-- Marrickville: 1,051 --> 731 (-30%)
           |
           v
     Zone filter (only works for Marrickville)
           |
           +-- Ashfield: 619 --> ~600 (minimal)
           +-- Leichhardt: 2,989 --> ~2,900 (minimal)
           +-- Marrickville: 731 --> ~250 (-66%)
           |
           v
     Precinct filter (if property in precinct)
           |
           +-- Further reduces for all councils
```

---

## Database Column Usage by Council

| Column | Ashfield Use | Leichhardt Use | Marrickville Use |
|--------|--------------|----------------|------------------|
| `v2_applicable_zones` | Minimal | Minimal | **High** |
| `v2_applicable_dev_types` | Low | Low (Part F only) | **High** |
| `v2_site_condition_required` | **Heritage critical** | Embedded | **Heritage critical** |
| `v2_precinct_id` | Moderate | **High** | Moderate |

---

## Precinct Coverage: The Critical Distinction

### Full Coverage vs Partial Coverage

| Council | Precinct/Neighbourhood Coverage | Implication |
|---------|--------------------------------|-------------|
| **Marrickville** | 48 precincts - **100% LGA coverage** | Every property is in exactly one precinct |
| **Leichhardt** | 23+ Distinctive Neighbourhoods - **100% LGA coverage** | Every property is in a neighbourhood |
| **Ashfield** | 17 precincts - **Partial coverage** | Only some areas have precinct controls |

### What This Means for Filtering

**Marrickville & Leichhardt (Full Coverage):**
- Precinct is **NOT a filter** - it's a **SELECTOR**
- Property in Precinct 6 sees Precinct 6 provisions
- Property in Precinct 7 sees Precinct 7 provisions
- **Same total count**, different provisions
- The precinct provisions **replace** each other, not filter out

**Ashfield (Partial Coverage):**
- Precinct **IS a filter**
- Property in a precinct: sees Chapter D provisions for that precinct
- Property NOT in a precinct: sees NO Chapter D provisions
- **Actually reduces** provision count for non-precinct properties

### DCP Design Philosophy

**Marrickville/Leichhardt approach:**
> "Your area has specific character. Here are the controls that preserve that character."
> Every property gets area-specific guidance, just different guidance.

**Ashfield approach:**
> "Most areas are covered by general controls. These special areas need extra attention."
> Only designated precincts get additional precinct-level controls.

---

## Actual Filtering Impact (After Fixes)

### Corrected Understanding:

**Ashfield (partial precinct coverage):**
| Stage | Provisions | Notes |
|-------|------------|-------|
| Total | 1,526 | |
| After heritage filter | 596 | -930 (61%) if NOT heritage |
| If NOT in precinct | 399 | -197 (Chapter D filtered) |
| **Final (non-heritage, non-precinct)** | **~399** | **74% reduction** |

**Leichhardt (full neighbourhood coverage):**
| Stage | Provisions | Notes |
|-------|------------|-------|
| Total | 2,989 | |
| After heritage filter | 2,780 | -209 (7%) if NOT heritage |
| Neighbourhood selection | ~2,200 | Shows YOUR neighbourhood, not all 23 |
| **Final** | **~2,200** | **26% reduction** (mostly heritage) |

**Marrickville (full precinct coverage):**
| Stage | Provisions | Notes |
|-------|------------|-------|
| Total | 1,051 | |
| After heritage filter | 406 | -645 (61%) if NOT heritage |
| Precinct selection | ~360 | Shows YOUR precinct provisions |
| Zone filter (R2) | ~200 | Part 4.1 only, not 4.2/5/6 |
| Dev-type filter | ~100-150 | Specific to dwelling house |
| **Final (non-heritage, R2, dwelling)** | **~100-150** | **86-90% reduction** |

### Key Takeaway

The filtering strategy must account for:
1. **Heritage**: Universal filter - biggest impact for Ashfield/Marrickville
2. **Precinct**:
   - Ashfield: Filter (reduces count if not in precinct)
   - Leichhardt/Marrickville: Selector (same count, different provisions)
3. **Zone/Dev-type**: Only valuable for Marrickville

---

*Analysis date: 2025-11-23*
*Heritage tagging fixed: 554 provisions updated*
