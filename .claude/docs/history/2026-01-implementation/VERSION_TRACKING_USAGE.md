# Version Tracking - Usage Guide

## Database Schema

The `documents` table now includes version tracking columns:

```sql
regulation_year INTEGER         -- e.g., 2016, 2013, 2022
amendment_reference TEXT        -- e.g., "IWLEP 2022", "Amdt 19"
amendment_date DATE            -- e.g., 2023-11-01, 2023-03-28
source_url TEXT                -- NSW Legislation URL (future use)
last_verified_date DATE        -- Last manual verification (defaults to import date)
version_status TEXT            -- 'unverified', 'current', 'superseded'
```

## Current Coverage

After migration:
- **DCPs**: 99.3% have year (265/267), 27.7% have amendments (74/267), 7.5% have dates (20/267)
- **LEPs**: 100% have year (14/14)
- **SEPPs**: 40.7% have year (48/118) - lower due to split sections

## Example Queries

### 1. Get full version info for a provision

```sql
SELECT
    rp.id,
    rp.ref_number,
    rp.provision_text,
    d.regulation_year,
    d.amendment_reference,
    d.amendment_date,
    d.version_status,
    d.last_verified_date,
    -- Calculate days since last verification
    CURRENT_DATE - d.last_verified_date as days_since_verified
FROM regulatory_provisions rp
JOIN documents d ON rp.document_id = d.id
WHERE rp.id = 12345;
```

### 2. Find provisions with stale data (>60 days)

```sql
SELECT
    d.pdf_name,
    d.regulation_year,
    d.amendment_date,
    CURRENT_DATE - d.last_verified_date as days_stale,
    COUNT(rp.id) as provision_count
FROM documents d
LEFT JOIN regulatory_provisions rp ON rp.document_id = d.id
WHERE CURRENT_DATE - d.last_verified_date > 60
  AND d.version_status = 'unverified'
GROUP BY d.id, d.pdf_name, d.regulation_year, d.amendment_date
ORDER BY days_stale DESC;
```

### 3. Get version summary for search results

```sql
SELECT
    rp.id,
    rp.ref_number,
    LEFT(rp.provision_text, 100) as text_preview,
    d.document_type,
    -- Build version label
    CONCAT(
        d.pdf_name,
        CASE
            WHEN d.amendment_reference IS NOT NULL THEN
                ' (' || d.amendment_reference || ')'
            ELSE ''
        END
    ) as version_label,
    -- Staleness indicator
    CASE
        WHEN CURRENT_DATE - d.last_verified_date <= 30 THEN 'current'
        WHEN CURRENT_DATE - d.last_verified_date <= 60 THEN 'caution'
        ELSE 'stale'
    END as staleness_level
FROM regulatory_provisions rp
JOIN documents d ON rp.document_id = d.id
WHERE rp.provision_text ILIKE '%setback%'
ORDER BY staleness_level, d.document_type;
```

## UI Integration Points

### 1. Provision Cards (`frontend-nextjs/components/compliance/`)

Add version metadata section:

```tsx
interface ProvisionVersion {
  regulation_year: number | null;
  amendment_reference: string | null;
  amendment_date: Date | null;
  version_status: 'unverified' | 'current' | 'superseded';
  last_verified_date: Date;
  days_since_verified: number;
}

function ProvisionVersionBadge({ version }: { version: ProvisionVersion }) {
  const staleness = version.days_since_verified > 60 ? 'stale'
                   : version.days_since_verified > 30 ? 'caution'
                   : 'current';

  return (
    <div className="version-info">
      {version.regulation_year && (
        <span>{version.regulation_year}</span>
      )}
      {version.amendment_reference && (
        <span className="amendment">{version.amendment_reference}</span>
      )}
      {staleness === 'stale' && (
        <span className="warning">⚠️ Verify before use</span>
      )}
    </div>
  );
}
```

### 2. Search Results (`frontend-nextjs/app/assessment/`)

Add version column to results table:

```tsx
<td className="version">
  {provision.regulation_year}
  {provision.amendment_reference && (
    <span className="amendment">({provision.amendment_reference})</span>
  )}
  {provision.days_since_verified > 60 && (
    <Badge variant="warning">Verify</Badge>
  )}
</td>
```

### 3. Global Disclaimer Banner

```tsx
function RegulatoryCurrencyNotice() {
  return (
    <div className="regulatory-notice">
      ⚠️ Database last updated: {lastUpdateDate}
      <br />
      Certifiers must verify all provisions are current before issuing certificates.
      <br />
      <a href="https://legislation.nsw.gov.au">NSW Legislation</a>
    </div>
  );
}
```

## API Endpoints

### Existing Endpoints to Update

1. **`/api/provisions/route.ts`** - Add version fields to provision response
2. **`/api/provisions/[id]/enhanced/route.ts`** - Include full version metadata
3. **`/api/documents/route.ts`** - Return document version info

### New Endpoint: Manual Verification

```typescript
// /api/documents/[id]/verify/route.ts
export async function POST(
  request: Request,
  { params }: { params: { id: string } }
) {
  const { status } = await request.json();

  // Update document verification
  await pool.query(`
    UPDATE documents
    SET
      version_status = $1,
      last_verified_date = CURRENT_DATE
    WHERE id = $2
  `, [status, params.id]);

  return Response.json({ success: true });
}
```

## Staleness Thresholds

Recommended thresholds for UI warnings:

- **✅ Current**: < 30 days since verification
- **⚠️ Caution**: 30-60 days
- **🚨 Stale**: > 60 days

For certifier liability protection, always show warnings for `unverified` provisions.

## Future Enhancements

1. **Automatic version checking** - Scheduled job to check NSW Legislation website
2. **Notification system** - Email alerts when new versions detected
3. **Version history** - Track when provisions change between versions
4. **Bulk verification** - Certifiers can mark multiple provisions as verified
5. **Source URLs** - Populate `source_url` field with direct links to legislation

## Example Version Displays

See `CERTIFIER_VERSION_DISPLAY.md` for full UI mockups showing:
- Provision cards with version metadata
- Staleness warnings (>60 days)
- Search results with version badges
- Global disclaimer banner
- Assessment report footer with version sources
