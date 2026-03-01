# Part 4.2+/Part 9 Extraction Workflow (with Table References)

## Current Status

**Extraction Running:** `extract_marrickville_part4_part9_with_tables.py`
- Target: 415 provisions (Part 4.2+, 4.3+, Part 5, Part 6, Part 9)
- Expected output: 1,500-3,000 requirements with table references
- Output file: `extraction_outputs/marrickville_part4_part9_requirements_YYYYMMDD_HHMMSS.json`

---

## When Extraction Completes

### Step 1: Check Extraction Results

```bash
# Wait for extraction to complete
# Check the final statistics in console output

# Verify JSON was created
ls -lh extraction_outputs/marrickville_part4_part9_requirements_*.json

# Quick validation
python -c "import json; f = open('extraction_outputs/marrickville_part4_part9_requirements_20251029_223218.json'); data = json.load(f); print(f\"Requirements: {len(data['requirements'])}\"); print(f\"Table refs: {sum(1 for r in data['requirements'] if r.get('has_table_reference'))}\"); f.close()"
```

**Expected output:**
```
Requirements: 1500-3000
Table refs: 200-400
```

---

### Step 2: Run Table Reference Reconciliation

```bash
# Reconcile table references with visual_elements_real
python reconcile_table_references.py extraction_outputs/marrickville_part4_part9_requirements_20251029_223218.json

# This will create:
# extraction_outputs/marrickville_part4_part9_requirements_20251029_223218_reconciled.json
```

**Expected output:**
```
RECONCILIATION STATISTICS
Total table references: 250
Verified (matched to visual_elements): 200 (80%)
Assumed (not found in visual_elements): 50 (20%)
Page number changes: 35
```

---

### Step 3: Import to Database

```bash
# Import reconciled requirements to dcp_general_requirements table
python import_marrickville_general_requirements.py extraction_outputs/marrickville_part4_part9_requirements_20251029_223218_reconciled.json --skip-backup

# Or with backup (if pg_dump is available)
python import_marrickville_general_requirements.py extraction_outputs/marrickville_part4_part9_requirements_20251029_223218_reconciled.json
```

**Import will:**
1. Ask if you want to delete existing 163 Marrickville requirements (from Part 2, 4.1, 7, 8)
   - Answer: **YES** (replace with new data from Part 4.2+/Part 9)
2. Insert new requirements with table references
3. Create indexes on lga, category, zones, devtypes
4. Verify import count

---

### Step 4: Verify Database

```bash
# Check total requirements
python -c "from db_safety_wrapper import get_safe_connection; conn = get_safe_connection(); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM dcp_general_requirements WHERE lga = '\''Marrickville'\'''); print(f'Total Marrickville requirements: {cur.fetchone()[0]}'); conn.close()"

# Check table references
python -c "from db_safety_wrapper import get_safe_connection; conn = get_safe_connection(); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM dcp_general_requirements WHERE lga = '\''Marrickville'\'' AND has_table_reference = TRUE'); print(f'Requirements with table references: {cur.fetchone()[0]}'); conn.close()"

# Sample requirements with tables
python -c "from db_safety_wrapper import get_safe_connection; import json; conn = get_safe_connection(); cur = conn.cursor(); cur.execute('SELECT requirement_text, table_references FROM dcp_general_requirements WHERE lga = '\''Marrickville'\'' AND has_table_reference = TRUE LIMIT 5'); [print(f'{text[:60]}... -> {json.loads(refs)[0][\"identifier\"]} (p.{json.loads(refs)[0][\"pdf_page\"]})') for text, refs in cur.fetchall()]; conn.close()"
```

**Expected output:**
```
Total Marrickville requirements: 1500-3000
Requirements with table references: 200-400

Side setbacks must comply with Table 1... -> Table 1 (p.42)
Parking rates per Table 6... -> Table 6 (p.38)
Building heights shown in Figure 4.2... -> Figure 4.2 (p.52)
```

---

## Database Schema (for reference)

Requirements are stored in `dcp_general_requirements` with:

```sql
CREATE TABLE dcp_general_requirements (
    id SERIAL PRIMARY KEY,
    lga TEXT,
    part_number TEXT,
    category TEXT,
    requirement_text TEXT,
    verbatim_source_text TEXT,
    applicable_zones TEXT[],
    development_types TEXT[],
    value_numeric NUMERIC,
    unit TEXT,

    -- Table references
    table_references JSONB,  -- [{"identifier": "Table 1", "pdf_page": 42, "pdf_url": "...", "source": "verified"}]
    has_table_reference BOOLEAN,

    -- PDF links
    pdf_page INTEGER,
    pdf_page_image_url TEXT,
    pdf_source_file TEXT
);
```

---

## UI Integration (Next Steps)

### Frontend Component Example

```tsx
// components/compliance/RequirementWithTableLink.tsx
function RequirementWithTableLink({ requirement }) {
  const [showTable, setShowTable] = useState(false);

  return (
    <div className="space-y-2">
      <p>{requirement.requirement_text}</p>

      {/* Show PDF link for requirement text */}
      <a href={requirement.pdf_page_image_url} target="_blank" className="text-sm text-blue-600">
        📄 View page {requirement.pdf_page}
      </a>

      {/* Show table references if present */}
      {requirement.table_references?.map(ref => (
        <button
          key={ref.identifier}
          onClick={() => window.open(ref.pdf_url, '_blank')}
          className="text-blue-600 hover:underline flex items-center gap-1"
        >
          📊 View {ref.identifier} (p.{ref.pdf_page})
          {ref.source === 'verified' && <span className="text-green-600">✓</span>}
        </button>
      ))}
    </div>
  );
}
```

---

## Summary

**Workflow:**
1. ✅ Extraction (running) → Creates JSON with table references
2. ⏳ Reconciliation → Updates table page numbers with actual locations
3. ⏳ Import → Loads to database
4. ⏳ Verify → Check data quality
5. ⏳ UI Integration → Display table links to users

**Current approach:**
- Table references link to same page as requirement (assumption)
- Reconciliation script updates ~80% with actual page numbers from visual_elements
- ~20% remain as assumptions (tables not in visual_elements or in appendices)

**User experience:**
- Requirements show: "Side setbacks comply with Table 1"
- User clicks: "📊 View Table 1 (p.42)"
- Opens PDF page 42 showing the actual table
