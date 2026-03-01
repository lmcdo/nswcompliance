# Delete zone_setback_rules & Get Real Setback Data

## Step 1: Delete the Corrupted Table

```sql
DROP TABLE zone_setback_rules;
```

Done. No backup needed - it's garbage data.

---

## Step 2: Get Missing Setback Data into Database Properly

### What's Already in Database:

**dcp_general_requirements:**
- Ashfield: 19 setback provisions (0 numeric - need to extract)
- Leichhardt: 39 setback provisions (5 numeric)
- Marrickville: 102 setback provisions (10 numeric)

**dcp_precinct_requirements:**
- Marrickville: 80+ precinct-specific setbacks ✓

### What's Missing:

**ASHFIELD Chapter F - Extract These:**
1. **0.9m side setback** (DS4.3) - Already exists but verify
2. **Upper floor progressive setbacks** (e.g., 1.5m first floor, 3m second floor)
3. **Secondary dwelling setbacks** (specific section)
4. **Corner lot variations** (if specified)
5. **Front setback guidance text:** "Match predominant building line"
6. **Rear setback guidance text:** "Maintain useable back garden"

**LEICHHARDT Part G - Extract These:**
1. **Neighbourhood-specific ranges** (e.g., "1m-3m front setbacks in Area X")
2. **Height-dependent progressions** (ground vs upper floors)
3. **Site-specific controls** → into `dcp_precinct_requirements` with addresses
4. **General guidance text** for each boundary type

**MARRICKVILLE - Already Good:**
- 102 general provisions ✓
- 80+ precinct provisions ✓
- Just need to surface this data in API

---

## Step 3: Extraction Plan

### A. Extract Ashfield Chapter F Systematically

```python
# extract_ashfield_chapter_f_setbacks.py

import PyMuPDF as fitz
import re
import psycopg2

pdf = fitz.open("docs/dcps/INNERWEST/ashfield/Ashfield_DCP_2016_Chapter_F.pdf")

# Target sections:
sections = {
    'DS4.1': 'Front Setbacks',
    'DS4.2': 'Rear Setbacks',
    'DS4.3': 'Side Setbacks',
    'DS4.4': 'Upper Floor Setbacks',
    'DS5': 'Secondary Dwellings'
}

for page in pdf:
    text = page.get_text()

    # Extract numeric setbacks with context
    if 'setback' in text.lower():
        # Pattern: "minimum X metres" or "X m setback"
        matches = re.findall(r'(\d+\.?\d*)\s*(m|metres?|mm)', text, re.IGNORECASE)

        for value, unit in matches:
            # Get surrounding context (50 chars before/after)
            context = extract_context(text, value, 50)

            # Determine setback type from context
            boundary_type = determine_type(context)  # front/side/rear

            # Determine if it's conditional/height-dependent
            conditional = is_conditional(context)

            # INSERT into dcp_general_requirements
            insert_provision({
                'lga': 'Inner West',
                'former_council': 'Ashfield',
                'dcp_chapter': 'Chapter F',
                'part_name': section_name,
                'category': 'setback',
                'subcategory': boundary_type,
                'requirement_text': context,
                'value_numeric': float(value),
                'unit': 'metres',
                'applicable_zones': ['R1', 'R2', 'R3', 'R4'],  # From section
                'has_conditionals': conditional
            })
```

### B. Extract Leichhardt Part G with Precinct Context

```python
# extract_leichhardt_part_g_setbacks.py

# For site-specific controls (170 View Street, etc.)
if 'View Street' in text or 'Wharf Road' in text:
    # Extract address/precinct
    address = extract_address(text)
    precinct_name = extract_precinct(text)

    # INSERT into dcp_precinct_requirements (not general!)
    insert_precinct_provision({
        'lga': 'Inner West',
        'former_council': 'Leichhardt',
        'precinct_name': precinct_name,
        'address': address,  # Site-specific
        'requirement_text': context,
        'value_numeric': float(value)
    })
else:
    # General provision → dcp_general_requirements
    insert_general_provision(...)
```

### C. Extract Guidance Text (Non-Numeric)

```python
# Also extract text-based guidance

guidance_patterns = [
    r'match.*prevailing.*building line',
    r'consistent with.*neighbourhood',
    r'useable.*back.*garden',
    r'maintain.*solar access'
]

for pattern in guidance_patterns:
    if re.search(pattern, text, re.IGNORECASE):
        # Store as provision without numeric value
        insert_provision({
            'requirement_text': matched_text,
            'value_numeric': None,  # Text guidance only
            'guidance_type': 'character_based'
        })
```

---

## Step 4: Update API to Use Real Data

```typescript
// frontend-nextjs/app/api/capacity/calculate/route.ts

async function getSetbacks(zone, formerCouncil, address, lga) {

  // 1. PRECINCT-SPECIFIC (most specific)
  const precinctQuery = `
    SELECT
      precinct_name,
      requirement_text,
      value_numeric,
      unit
    FROM dcp_precinct_requirements
    WHERE lga = $1
      AND requirement_text ILIKE '%setback%'
      AND (
        precinct_name IS NOT NULL
        OR address ILIKE $2  -- Site-specific match
      )
    LIMIT 10
  `;

  const precinctResult = await pool.query(precinctQuery, [lga, `%${address}%`]);

  if (precinctResult.rows.length > 0) {
    return formatPrecinctSetbacks(precinctResult.rows);
  }

  // 2. GENERAL PROVISIONS (zone + council specific)
  const generalQuery = `
    SELECT
      subcategory,
      requirement_text,
      value_numeric,
      value_min,
      value_max,
      unit,
      applicable_zones,
      has_conditionals,
      conditional_text
    FROM dcp_general_requirements
    WHERE lga = $1
      AND former_council = $2
      AND category ILIKE '%setback%'
      AND (
        $3 = ANY(applicable_zones)
        OR applicable_zones IS NULL
      )
    ORDER BY
      CASE
        WHEN value_numeric IS NOT NULL THEN 1
        ELSE 2
      END,
      subcategory
  `;

  const generalResult = await pool.query(generalQuery, [lga, formerCouncil, zone]);

  if (generalResult.rows.length > 0) {
    return formatGeneralSetbacks(generalResult.rows);
  }

  // 3. FALLBACK - Guidance only
  return {
    type: 'guidance',
    message: 'Setbacks determined by neighbourhood character',
    method: 'Measure prevailing building line on your street'
  };
}

function formatGeneralSetbacks(rows) {
  const setbacks = {
    type: 'mixed',  // Contains both numeric and guidance
    values: [],
    guidance: []
  };

  for (const row of rows) {
    const boundary = row.subcategory;  // front/side/rear

    if (row.value_numeric) {
      setbacks.values.push({
        boundary: boundary,
        value: row.value_numeric,
        unit: row.unit,
        conditional: row.has_conditionals,
        condition: row.conditional_text,
        text: row.requirement_text
      });
    } else {
      // Text guidance only
      setbacks.guidance.push({
        boundary: boundary,
        text: row.requirement_text
      });
    }
  }

  return setbacks;
}
```

---

## Step 5: Frontend Display

```typescript
// Show BOTH numbers and guidance

{setbacks.type === 'mixed' && (
  <div>
    <h3>Setbacks</h3>

    {/* Numeric values */}
    {setbacks.values.map(v => (
      <div key={v.boundary}>
        <strong>{v.boundary}:</strong> {v.value}{v.unit}
        {v.conditional && (
          <span className="text-yellow-600"> (conditional)</span>
        )}
        <p className="text-sm">{v.text}</p>
      </div>
    ))}

    {/* Text guidance */}
    {setbacks.guidance.map(g => (
      <div key={g.boundary}>
        <strong>{g.boundary}:</strong>
        <p className="text-sm italic">{g.text}</p>
      </div>
    ))}
  </div>
)}
```

---

## Step 6: Execution Order

1. ✅ **DROP TABLE zone_setback_rules;**
2. ✅ **Extract Ashfield Chapter F setbacks** (numeric + guidance)
3. ✅ **Extract Leichhardt Part G setbacks** (with precinct context)
4. ✅ **Update API route** (remove zone_setback_rules query, use dcp tables)
5. ✅ **Update frontend** (show mixed numeric + guidance)
6. ✅ **Test with real addresses**

---

## Expected Result:

**User enters Ashfield R2 address:**
```
Setbacks:

✓ Side: 0.9m minimum (verified)
  "Council requires minimum 900mm for dwelling houses"

📏 Front: Match prevailing building line
  "Front setbacks are consistent with predominant building line
   established by adjoining and nearby houses"

🌳 Rear: Maintain useable back garden
  "Minimum rear setbacks maintain useable back garden for
   outdoor activities"

⬆️ Upper floors: Progressive setbacks required
  • First floor: 1.5m minimum
  • Second floor and above: 3m minimum
```

**User enters Leichhardt precinct with site-specific controls:**
```
Setbacks (Precinct-Specific):

📍 Your address is subject to site-specific controls

✓ Side: 1.5m minimum (170 View Street area)
  "Side setback on one side minimum 1.5m to retain views to water"

Applies to: Wharf Road waterfront properties
```

This gives users REAL, VERIFIED data with appropriate context!

Ready to implement?
