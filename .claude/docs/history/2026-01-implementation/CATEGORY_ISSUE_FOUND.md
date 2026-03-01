# CRITICAL: Category Mismatch Found

## Issue Discovered

The extraction script `extract_marrickville_CATEGORIZED.py` is currently running but uses **SIMPLIFIED categories** that don't match the existing data schema.

### Current Script Categories (10 categories)
```
building_design, landscaping, parking, heritage, environmental,
subdivision, commercial, residential, infrastructure, general
```

### Existing Data Categories (56 categories!)
```
Top categories by usage:
- other (330)
- heritage (231)
- character (202)
- parking (174)
- waste_management (162)          ← MISSING!
- sustainability (150)              ← MISSING!
- contamination (133)               ← MISSING!
- water_management (128)            ← MISSING!
- landscaping (119)
- tree_preservation (100)           ← MISSING!
- da_requirements (96)              ← MISSING!
- signage (89)                      ← MISSING!
- drainage (85)                     ← MISSING!
- building_form (79)                ← MISSING!
- safety (75)                       ← MISSING!
- stormwater (70)                   ← MISSING!
- accessibility (68)                ← MISSING!
- building_height (43)
- setback_front (40)
- environmental (40)
- streetscape (29)
- privacy (26)
- energy_efficiency (26)            ← MISSING!
- solar_access (25)
... and 33 more
```

## Impact

If the extraction continues with simplified categories:
1. ❌ **Data inconsistency** - Marrickville will have different category structure than Ashfield/Leichhardt
2. ❌ **Lost granularity** - "environmental" is too broad, should be split into:
   - `waste_management`
   - `sustainability`
   - `contamination`
   - `water_management`
   - `stormwater`
   - `drainage`
   - `energy_efficiency`
   - etc.
3. ❌ **UI filtering broken** - If UI filters by specific categories like "waste_management", Marrickville won't appear

## Recommended Action

**STOP** the current extraction and create a new prompt with comprehensive categories matching existing data.

### Comprehensive Category List (56 categories)

**Core Planning:**
- `heritage`, `character`, `streetscape`
- `building_form`, `building_height`, `building_controls`
- `setback_front`, `setback_side`, `setback_rear`, `setbacks`
- `site_coverage`, `site_area`, `siting`

**Environmental:**
- `waste_management`
- `sustainability`
- `contamination`
- `water_management`, `water_efficiency`, `water_conservation`
- `stormwater`, `stormwater_management`, `drainage`
- `energy_efficiency`
- `solar_access`, `overshadowing`
- `biodiversity`, `tree_preservation`, `deep_soil`
- `flood_management`
- `environmental` (catch-all)

**Site Development:**
- `landscaping`, `open_space`, `private_open_space`
- `parking`, `visitor_parking`
- `subdivision`
- `fencing`
- `accessibility`, `universal_access`

**Building Design:**
- `privacy`, `acoustic_privacy`, `visual_privacy`
- `amenity`
- `safety`, `fire_safety`
- `materials and colour`, `detailing`

**Special Uses:**
- `signage`
- `commercial`, `shop_fronts`
- `residential`
- `da_requirements` (DA submission requirements)

**Infrastructure:**
- `infrastructure`
- `transport`
- `site facilities`

**Catch-all:**
- `other` (when nothing else fits)
- `process` (procedural requirements)

## How to Fix

1. **Stop current extraction:**
   ```bash
   # Kill process 303f9a
   ```

2. **Update prompt in extraction script** to include all 56 categories

3. **Add category mapping guidance:**
   - Waste/rubbish → `waste_management`
   - Green star/sustainability → `sustainability`
   - Contaminated land → `contamination`
   - Water sensitive design → `water_management`
   - Stormwater/drainage → `stormwater` or `drainage`
   - Trees/vegetation → `tree_preservation` or `landscaping`
   - Setbacks → `setback_front`, `setback_side`, `setback_rear`

4. **Re-run extraction** with corrected categories

## Files to Update

- `extract_marrickville_CATEGORIZED.py` - Update EXTRACTION_PROMPT with comprehensive category list
- Add category mapping examples to help LLM classify correctly

## Testing

After fixing, verify categories match existing data:
```sql
SELECT category, COUNT(*)
FROM dcp_general_requirements
WHERE former_council = 'Marrickville'
GROUP BY category
ORDER BY count DESC;
```

Should see distribution similar to Ashfield/Leichhardt with categories like:
- `waste_management`, `sustainability`, `contamination`, etc.

NOT just:
- `environmental` (too generic)
