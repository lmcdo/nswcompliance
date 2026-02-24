# SEPP Quarterly Review Workflow

## Overview

SEPPs (State Environmental Planning Policies) are updated regularly through EPIs (Environmental Planning Instruments). This workflow ensures our database stays current by checking for amendments every 90 days.

## Schedule

**Review Frequency**: Every 90 days
**Next Review Date**: Stored in `documents.next_check_date`
**Last Review**: Feb 20, 2026

## 1. Identify SEPPs Due for Review

Run this query to find SEPPs that need checking:

```bash
cd frontend-nextjs && npx tsx <<'EOF'
import { getPool } from '@/lib/database/pool-manager';

const pool = await getPool();

const query = `
  SELECT
    id,
    pdf_name,
    consolidated_as_of_date,
    next_check_date,
    last_verified_date,
    CURRENT_DATE - next_check_date as days_overdue
  FROM documents
  WHERE document_type = 'SEPP'
    AND is_superseded = false
    AND next_check_date <= CURRENT_DATE
  ORDER BY next_check_date;
`;

const result = await pool.query(query);

console.log(`=== SEPPs Due for Review (${result.rows.length}) ===\n`);
result.rows.forEach(row => {
  console.log(`${row.pdf_name.substring(0, 60)}...`);
  console.log(`  Consolidated: ${row.consolidated_as_of_date.toLocaleDateString()}`);
  console.log(`  Next check: ${row.next_check_date.toLocaleDateString()}`);
  console.log(`  Days overdue: ${row.days_overdue}`);
  console.log('');
});

await pool.end();
EOF
```

## 2. Research Amendments

### Manual Research (Required for First-Time Setup)

For each SEPP, visit the NSW Legislation website and check the historical notes:

| SEPP | EPI Number | URL |
|------|------------|-----|
| Housing SEPP 2021 | 2021-0714 | https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714 |
| Transport & Infrastructure SEPP 2021 | 2021-0732 | https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0732 |
| Biodiversity & Conservation SEPP 2021 | 2021-0722 | https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0722 |
| Resilience & Hazards SEPP 2021 | 2021-0730 | https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0730 |
| Planning Systems SEPP 2021 | 2021-0728 | https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0728 |
| Industry & Employment SEPP 2021 | 2021-0726 | https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0726 |
| Primary Production SEPP 2021 | 2021-0733 | https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0733 |
| Sustainable Buildings SEPP 2022 | 2022-0214 | https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2022-0214 |
| Exempt & Complying Codes SEPP 2008 | 2008-0572 | https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2008-0572 |

**Steps for Each SEPP:**
1. Open the URL
2. Look for "Historical notes" or "Legislative history"
3. Identify EPIs gazetted after the last `consolidated_as_of_date`
4. Record EPI number, effective date, and description
5. Update `sepp-amendments-research.json`

### Automated Research (Partial)

```bash
cd frontend-nextjs/scripts
npm exec tsx research-sepp-amendments.ts
```

This generates a research template. Fill in findings manually or use browser automation (may be blocked by NSW Legislation website).

## 3. Apply Amendments to Database

Once research is complete, run:

```bash
cd frontend-nextjs/scripts
npm exec tsx apply-sepp-amendments.ts
```

This script:
- Reads `sepp-amendments-research.json`
- Updates `amending_epis` array
- Updates `major_amendments` JSONB
- Sets new `consolidated_as_of_date`
- Resets `next_check_date` to +90 days
- Updates `last_verified_date` to today

## 4. Standardize References

Ensure human-readable amendment references are consistent:

```bash
cd frontend-nextjs/scripts
npm exec tsx standardize-amendment-references.ts
```

Format: `"EPIs 512/597/647 (2025), TBD (2026)"`

## 5. Verification

Check that all updates were applied correctly:

```bash
cd frontend-nextjs && npx tsx <<'EOF'
import { getPool } from '@/lib/database/pool-manager';

const pool = await getPool();

const query = `
  SELECT
    pdf_name,
    consolidated_as_of_date,
    amendment_reference,
    array_length(amending_epis, 1) as epi_count,
    jsonb_array_length(major_amendments) as amendment_count,
    next_check_date,
    version_status
  FROM documents
  WHERE document_type = 'SEPP'
    AND is_superseded = false
  ORDER BY pdf_name;
`;

const result = await pool.query(query);

console.log('=== SEPP Version Status ===\n');
result.rows.forEach(row => {
  console.log(`${row.pdf_name.substring(0, 50)}...`);
  console.log(`  Consolidated: ${row.consolidated_as_of_date?.toLocaleDateString() || 'NULL'}`);
  console.log(`  Reference: ${row.amendment_reference || 'NULL'}`);
  console.log(`  EPIs: ${row.epi_count || 0} | Amendments: ${row.amendment_count || 0}`);
  console.log(`  Next check: ${row.next_check_date?.toLocaleDateString() || 'NULL'}`);
  console.log(`  Status: ${row.version_status}`);
  console.log('');
});

await pool.end();
EOF
```

## 6. Update Frontend (If Needed)

If amendments affect provisions displayed in the UI:

1. Run extraction scripts for updated SEPPs
2. Update PDF page images if page numbers changed
3. Update provision citations if clause numbers changed
4. Test version badge display (Task #15)

## Database Schema Reference

Key columns in `documents` table:

| Column | Type | Purpose |
|--------|------|---------|
| `consolidated_as_of_date` | DATE | Date of current consolidated version |
| `consolidation_url` | TEXT | NSW Legislation point-in-time URL |
| `amending_epis` | TEXT[] | Array of EPI numbers (e.g., `["512/2025", "597/2025"]`) |
| `major_amendments` | JSONB | Full amendment details with dates and descriptions |
| `amendment_reference` | TEXT | Human-readable summary (e.g., "EPIs 512/597 (2025)") |
| `next_check_date` | DATE | When to check for new amendments (consolidated_as_of_date + 90 days) |
| `last_verified_date` | DATE | When we last checked NSW Legislation |
| `version_status` | TEXT | 'current', 'superseded', or 'unverified' |
| `is_superseded` | BOOLEAN | Whether this document version is no longer active |

## Troubleshooting

### "No amendments found"
- Check if you're looking at the correct date range (after last `consolidated_as_of_date`)
- Some SEPPs may not have been amended in the review period
- Mark as verified and reset `next_check_date` even if no amendments

### "NSW Legislation website blocks automated research"
- Use manual research workflow
- Copy EPI numbers from "Point-in-time versions" dropdown
- Cross-reference with "Reprints" table for effective dates

### "How do I know if an amendment affects provisions?"
- If the amendment adds/removes/modifies clauses in Parts relevant to Inner West LGA
- If the amendment is marked as "commenced" (not "not commenced")
- When in doubt, mark `affects_provisions: true` to be safe

## Quarterly Review Checklist

- [ ] Run query to identify overdue SEPPs
- [ ] Research amendments on NSW Legislation for each SEPP
- [ ] Update `sepp-amendments-research.json` with findings
- [ ] Run `apply-sepp-amendments.ts`
- [ ] Run `standardize-amendment-references.ts`
- [ ] Verify database updates
- [ ] Test frontend display of version info (if applicable)
- [ ] Document any significant amendments in project notes

## See Also

- `SEPP-VERSIONING-STRATEGY.md` - Full versioning design
- `sepp-amendments-research.json` - Research template
- `DB_SCHEMA.md` - Database documentation
