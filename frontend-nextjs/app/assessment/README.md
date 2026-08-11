# Assessment Pages

## Primary Implementation
**Route:** `/assessment` (`page.tsx`)
- **Status:** ✅ ACTIVE - Primary user interface
- **Layout:** 2-column (1/4 property data + 3/4 compliance provisions)
- **Left Column:** NSW Planning API data with clickable legislation URLs
- **Right Column:** Unfiltered SEPP/LEP/DCP provisions from PostgreSQL database
- **Database:** Queries `regulatory_provisions` table (up to 50 provisions per zone)

## Alternative Implementations
These are preserved for reference but not actively used:

### `/assessment/dashboard` (`dashboard/page.tsx`)
- **Status:** 🟡 ALTERNATIVE - Same functionality as main page
- **Use Case:** Standalone dashboard with property selection panel
- **Note:** Kept for backward compatibility with existing bookmarks

### `/assessment/enhanced` (`enhanced/page.tsx`)
- **Status:** 📦 ARCHIVED - Experimental version
- **Note:** Development/testing version only

### `/assessment/professional` (`professional/page.tsx`)
- **Status:** 📦 ARCHIVED - Experimental version
- **Note:** Development/testing version only

### `/assessment/version-aware` (`version-aware/page.tsx`)
- **Status:** 📦 ARCHIVED - Version management experiment
- **Note:** Development/testing version only

### `/assessment/optimized` (`optimized/page.tsx`)
- **Status:** 📦 ARCHIVED - Performance testing version
- **Note:** Development/testing version only

## Quick Reference for Claude

When asked about "assessment page" or "provision display":
1. **Always check `/assessment/page.tsx` FIRST**
2. The right column renders **`ProvisionsByTocStructure`**, gated by
   `isDcpEnabledForCouncil()`. When the gate is false, or the council has no provision
   text, it falls back to `DcpStructuredControls` + `DCPInterestForm`.
3. Left column shows NSW Planning API data via PropertyDetailsComprehensive
4. Both columns populate after address search

> **⚠ CORRECTED 2026-08-08.** This file previously said the right column was
> `ComplianceDashboard`. **It is not, and has not been:** `git grep '<ComplianceDashboard'`
> returns **zero** JSX usages anywhere in the repo. The component and its route
> (`/api/compliance/dcp-complete`) are dead code — the route queries
> `dcp_general_provisions` and `dcp_general_requirements`, both renamed to `zz_legacy_*`,
> so it returns HTTP 500 for every address. Both are carried in
> `scripts/schema_contract_baseline.json` as accepted dead-code entries.
> Re-check with `git grep '<ComplianceDashboard'` rather than trusting this paragraph.

## Key Components
- `PropertyDetailsComprehensive` - Left column (Planning API layers)
- `ProvisionsByTocStructure` - Right column (DCP provisions, TOC-structured)
- `DcpStructuredControls` - Numeric DCP controls (renders where provision text is absent)
- ~~`ComplianceDashboard`~~ - **DEAD CODE, never rendered. Do not cite as the right column.**
- `ComplianceConstraint` - Individual provision cards
- `ConstraintCard` - Expandable card with full legal text

## API Endpoints Used
- `/api/property?address=...` - NSW Planning Portal data
- `/api/compliance/constraints` - Database provisions (SEPP/LEP/DCP)
- `/api/provisions/[id]/complete` - Full legal text for specific provision