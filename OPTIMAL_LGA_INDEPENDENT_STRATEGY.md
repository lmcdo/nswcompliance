# Optimal LGA-Independent DCP Section Strategy

## Problem Statement

**Current Issue:**
```typescript
// Hard-coded for Inner West only
const mapping = {
  'dwelling_house': { zones: ['R1','R2','R3','R4'], section: 'F.1' }
};
```

**This won't work for:**
- Canterbury-Bankstown (different DCP structure)
- Sydney City Council (different chapter naming)
- Future LGAs (need code changes for each)

---

## Solution Architecture

### **3-Tier Strategy: Database → Cache → Fallback**

```
┌─────────────────────────────────────────────────┐
│ Tier 1: Database-Driven Mapping Table          │
│ - Auto-extracts from existing provisions       │
│ - Scales to any LGA automatically               │
│ - No code changes needed for new LGAs           │
└─────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────┐
│ Tier 2: In-Memory Cache (API Layer)            │
│ - Loads mappings on server start               │
│ - Fast lookups (no DB query per request)        │
│ - Refreshes every 24 hours                      │
└─────────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────────┐
│ Tier 3: Dynamic Fallback (For New LGAs)        │
│ - Queries provisions_with_category directly     │
│ - Auto-detects section structure                │
│ - Adds to cache for future requests             │
└─────────────────────────────────────────────────┘
```

---

## Implementation

### **1. Database Layer (Already Created)**

**Table:** `dcp_section_mappings`
```sql
CREATE TABLE dcp_section_mappings (
  lga TEXT,                    -- "Inner West", "Canterbury-Bankstown"
  development_type TEXT,       -- "dwelling_house", "multi_dwelling"
  section_identifier TEXT,     -- "F.1", "3.2.1", "Part A"
  section_title TEXT,          -- "Dwelling Houses"
  applicable_zones TEXT[],     -- ['R1','R2','R3']
  document_id TEXT
);
```

**Function:** `get_dcp_section(lga, zone, dev_type)`
```sql
SELECT * FROM get_dcp_section('Inner West', 'R2', 'dwelling_house');
-- Returns: { section_identifier: 'F.1', document_id: '...' }
```

**Auto-population:**
```sql
-- Extracts from existing provisions (works for ANY LGA)
INSERT INTO dcp_section_mappings
SELECT
  extract_lga(document_id),
  development_type,
  extract_section(section_header),
  section_header,
  infer_zones(development_type),
  document_id
FROM provisions_with_category
WHERE document_category = 'DCP'
  AND development_type IS NOT NULL;
```

---

### **2. API Layer (Next.js)**

**New Service:** `lib/dcp-section-service.ts`

```typescript
// In-memory cache with automatic refresh
class DCPSectionService {
  private cache: Map<string, DCPMapping> = new Map();
  private lastRefresh: Date = new Date(0);
  private readonly CACHE_TTL = 24 * 60 * 60 * 1000; // 24 hours

  async getDCPSection(lga: string, zone: string, devType: string): Promise<DCPSection> {
    // Check cache first
    const cacheKey = `${lga}:${zone}:${devType}`;
    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey)!;
    }

    // Cache miss: Query database
    const result = await pool.query(
      `SELECT * FROM get_dcp_section($1, $2, $3)`,
      [lga, zone, devType]
    );

    if (result.rows.length > 0) {
      // Found in database
      const section = result.rows[0];
      this.cache.set(cacheKey, section);
      return section;
    }

    // Fallback: Dynamic detection
    return this.detectDCPSection(lga, zone, devType);
  }

  private async detectDCPSection(lga: string, zone: string, devType: string): Promise<DCPSection> {
    // Query provisions_with_category to find section structure
    const result = await pool.query(`
      SELECT DISTINCT
        section_header,
        document_id,
        SUBSTRING(section_header FROM '^[A-Z]?\.?\\d+\\.?\\d*') as section_id
      FROM provisions_with_category
      WHERE document_id LIKE $1
        AND development_type = $2
        AND section_header IS NOT NULL
      LIMIT 1
    `, [`%${lga}%DCP%`, devType]);

    if (result.rows.length > 0) {
      const detected = result.rows[0];

      // Add to database for future use
      await pool.query(`
        INSERT INTO dcp_section_mappings (lga, development_type, section_identifier, section_title, document_id, applicable_zones)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT DO NOTHING
      `, [lga, devType, detected.section_id, detected.section_header, detected.document_id, [zone]]);

      // Add to cache
      this.cache.set(`${lga}:${zone}:${devType}`, detected);
      return detected;
    }

    // Ultimate fallback: return generic
    return {
      section_identifier: 'General',
      section_title: 'General Development Controls',
      document_id: `${lga}_DCP`
    };
  }

  async refreshCache(): Promise<void> {
    if (Date.now() - this.lastRefresh.getTime() < this.CACHE_TTL) {
      return; // Cache still fresh
    }

    // Load all mappings from database
    const result = await pool.query(`SELECT * FROM dcp_section_mappings`);

    this.cache.clear();
    for (const row of result.rows) {
      for (const zone of row.applicable_zones) {
        const key = `${row.lga}:${zone}:${row.development_type}`;
        this.cache.set(key, row);
      }
    }

    this.lastRefresh = new Date();
    console.log(`[DCP Section Service] Cache refreshed: ${this.cache.size} mappings`);
  }
}

export const dcpSectionService = new DCPSectionService();
```

---

### **3. Updated API Endpoint**

**Updated:** `app/api/compliance/constraints/route.ts`

```typescript
import { dcpSectionService } from '@/lib/dcp-section-service';

export async function POST(request: NextRequest) {
  const { zone, developmentType, lga } = await request.json();

  // Get DCP section dynamically for ANY LGA
  const dcpSection = await dcpSectionService.getDCPSection(
    lga,           // From property data
    zone,          // From property data
    developmentType // From user selection
  );

  // Query provisions using detected section
  const query = `
    SELECT * FROM provisions_with_category
    WHERE document_id = $1
      AND section_header LIKE $2 || '%'
      AND (development_type = $3 OR development_type IS NULL)
  `;

  const result = await pool.query(query, [
    dcpSection.document_id,
    dcpSection.section_identifier,
    developmentType
  ]);

  // Return provisions
  return NextResponse.json({
    success: true,
    data: {
      dcpSection: dcpSection.section_identifier,
      dcpTitle: dcpSection.section_title,
      provisions: result.rows
    }
  });
}
```

---

### **4. Updated Frontend**

**Updated:** `components/compliance/ComplianceDashboard.tsx`

```typescript
// REMOVE hard-coded mapping function
// DELETE: getDCPSection() function (lines 64-84)

// UPDATE: Let API handle section detection
const response = await fetch('/api/compliance/constraints', {
  method: 'POST',
  body: JSON.stringify({
    address: propertyData.address,
    zone: propertyData.constraints.zone,
    lga: propertyData.constraints.lga,  // ← Add LGA
    developmentType: developmentType
  })
});

// API returns the correct section for this LGA
const { dcpSection, dcpTitle, provisions } = await response.json();

// Display: "F.1 - Dwelling Houses" or "3.2 - Residential Development"
```

---

## Benefits of This Approach

### **✓ LGA-Independent**
- Works for Inner West, Canterbury-Bankstown, Sydney, etc.
- No code changes for new LGAs

### **✓ Auto-Scaling**
- New LGAs added to database → immediately available
- No manual mapping needed

### **✓ Performance**
- In-memory cache: <1ms lookups
- Database function: ~5ms lookups
- Dynamic fallback: ~20ms (rare)

### **✓ Forward-Looking**
- Supports future DCP structure changes
- Handles mergers (e.g., Canterbury-Bankstown merged councils)
- Works with historical DCPs (old versions)

### **✓ Maintainable**
- Single source of truth: `dcp_section_mappings` table
- Override capability for edge cases
- Self-documenting (section titles stored)

---

## Migration Path

### **Phase 1: Database Setup** (5 minutes)
```bash
psql $DB_URL -f migrations/create_dcp_section_mappings.sql
```

### **Phase 2: Create Service** (15 minutes)
```bash
# Create lib/dcp-section-service.ts
# Implement caching + fallback logic
```

### **Phase 3: Update API** (10 minutes)
```bash
# Update app/api/compliance/constraints/route.ts
# Use dcpSectionService instead of hard-coded function
```

### **Phase 4: Update Frontend** (5 minutes)
```bash
# Remove getDCPSection() from ComplianceDashboard.tsx
# Pass LGA to API
```

### **Phase 5: Test** (10 minutes)
```bash
# Test Inner West (existing)
# Test with fake Canterbury-Bankstown data
# Verify cache warming
```

---

## Want me to implement this now?

This will make your system truly scalable to **any NSW LGA** without code changes!