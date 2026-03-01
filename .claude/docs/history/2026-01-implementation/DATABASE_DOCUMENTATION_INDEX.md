# DATABASE DOCUMENTATION INDEX
**NSW Planning Compliance Engine - Complete Schema Documentation**
**Generated:** 2025-10-05

---

## Quick Start Guide

**If you need to understand the database, start here:**

1. **Quick Overview** → `DATABASE_QUICK_REFERENCE.md` (9.4 KB)
   - Common queries
   - Table summaries
   - Connection info
   - Performance tips

2. **Complete Schema Details** → `DATABASE_SCHEMA_ANALYSIS.md` (62 KB)
   - Every table documented
   - All columns, indexes, constraints
   - Migration history
   - Data quality issues
   - Query patterns

3. **Visual Relationships** → `DATABASE_ERD_DETAILED.md` (39 KB)
   - ASCII entity-relationship diagrams
   - Foreign key mappings
   - Data type issues highlighted
   - Cardinality relationships

4. **Raw Schema Data** → `database_schema_complete.json` (95 KB)
   - Machine-readable schema
   - All tables, columns, indexes
   - Generated from live database

---

## Documentation Files

### Schema Analysis (NEW - 2025-10-05)

#### `DATABASE_SCHEMA_ANALYSIS.md` (62 KB)
**Complete database schema reference document**

Contents:
- Executive Summary
- All 34 tables documented in detail
- Entity Relationship Diagram (ASCII)
- Index Strategy Analysis
- Data Model Patterns
- Query Patterns
- Data Quality Issues & Recommendations
- Migration History
- Performance Optimization Recommendations

Key sections:
1. Core Tables (regulatory_provisions, documents, development_controls)
2. Linking Tables (cross_reference_index, provision_applicability, control_codes)
3. Knowledge Graph Tables (kg_entities, kg_relationships)
4. Document Tables (visual_elements_real, contextual_guidance_real)
5. Special Provisions Tables (quantitative_standards, permissibility_analysis)
6. Views (5 denormalized query helpers)

#### `DATABASE_ERD_DETAILED.md` (39 KB)
**Visual entity-relationship diagrams**

Contents:
- Core Regulatory Provision Flow (ASCII diagram)
- Extracted Development Control Data
- Knowledge Graph Structure
- Visual & Contextual Content
- Permission & Permissibility Data
- Hierarchy & Override Resolution
- Foreign Key Summary
- Data Type Issues
- Relationship Cardinality
- Index Coverage Analysis

#### `DATABASE_QUICK_REFERENCE.md` (9.4 KB)
**Quick lookup for common tasks**

Contents:
- Quick Stats
- Core Tables (what to query)
- Useful Views
- Important Column Meanings
- Common Queries (copy-paste ready)
- Data Quality Issues
- Migration History
- Performance Tips
- Table Sizes
- Connection Info

#### `database_schema_complete.json` (95 KB)
**Machine-readable schema export**

Contents:
- All tables with complete metadata
- Columns (name, type, nullable, default)
- Primary keys
- Foreign keys (with ON DELETE/UPDATE rules)
- Indexes (with definitions)
- Check constraints
- Unique constraints
- Row counts

Usage:
```python
import json
schema = json.load(open('database_schema_complete.json'))
tables = schema.keys()
columns = schema['regulatory_provisions']['columns']
```

#### `extract_full_schema.py` (7.3 KB)
**Schema extraction script**

Purpose: Extract live schema from database
Generates: `database_schema_complete.json`

Usage:
```bash
python extract_full_schema.py
```

Extracts:
- All tables in public schema
- Complete column definitions
- Primary keys, foreign keys
- Indexes with definitions
- Check constraints
- Unique constraints
- Row counts

---

### Existing Database Documentation

#### `DATABASE_CONFIGURATION.md` (3.1 KB)
Connection settings, environment variables, pool configuration

#### `DATABASE_SETUP.md` (3.2 KB)
PostgreSQL installation, database creation, initial setup

#### `DATABASE_BACKUP_INSTRUCTIONS.md` (4.7 KB)
Backup procedures, restore processes, safety protocols

#### `DATABASE_BACKUP_RESTORE_PROCEDURES.md` (5.2 KB)
Detailed backup and restore procedures

#### `DATABASE_LOCATIONS_AND_ACTIVE_FILES.md` (5.7 KB)
File locations, active schemas, migration tracking

---

## What Each File Is For

### For Developers

**Need to query the database?**
→ `DATABASE_QUICK_REFERENCE.md`
- Copy-paste queries for common tasks
- Performance tips
- Connection examples

**Building new features?**
→ `DATABASE_SCHEMA_ANALYSIS.md`
- Understand table relationships
- See all columns and their purposes
- Learn data model patterns
- Check migration history

**Debugging data issues?**
→ `DATABASE_ERD_DETAILED.md`
- See what foreign keys exist (or are missing)
- Identify type mismatches
- Find orphaned data

### For Database Administrators

**Need to optimize queries?**
→ `DATABASE_SCHEMA_ANALYSIS.md` - Index Strategy section
- Which indexes exist
- Which are missing
- Composite index recommendations

**Planning schema changes?**
→ `DATABASE_SCHEMA_ANALYSIS.md` - Data Quality Issues section
- Type mismatches to fix
- Missing foreign keys to add
- Normalization opportunities

**Creating backups?**
→ `DATABASE_BACKUP_INSTRUCTIONS.md`

### For System Architects

**Understanding the data model?**
→ `DATABASE_ERD_DETAILED.md`
- Complete relationship map
- Cardinality (1:N, N:M)
- Normalization analysis

**Migrating or replicating?**
→ `database_schema_complete.json`
- Machine-readable schema
- All constraints and indexes
- Can generate CREATE statements

### For Data Scientists

**Analyzing provision data?**
→ `DATABASE_QUICK_REFERENCE.md` - Common Queries section
- Zone-based lookups
- Cross-reference traversal
- Hierarchy queries

**Understanding data quality?**
→ `DATABASE_SCHEMA_ANALYSIS.md` - Data Quality section
- Known type issues
- Duplicate handling
- Confidence scores

---

## Key Database Facts

### Database: nsw_planning (PostgreSQL)

**Size:**
- 34 tables (including 5 views)
- 22,648 total provisions
- 20,111 canonical provisions (after deduplication)
- ~126,000 total records across all tables

**Main Table:** `regulatory_provisions`
- Central table for all planning provisions
- Links to 7 other tables via foreign keys
- 30 columns, 12 indexes
- 88.8% canonical, 11.2% duplicates

**Linking Tables (Phase 1 Migration):**
- `provision_applicability` - Zone/LGA applicability (22,979 rows)
- `control_codes` - Expanded code ranges (24,346 rows)
- `cross_reference_index` - Structured cross-refs (3,801 rows)
- `provision_diagrams` - Visual links (0 rows - future)

**Data Quality:**
- ✓ Good: Core tables well-indexed, deduplication working
- ⚠ Medium: Extract tables need foreign keys and indexes
- ✗ Poor: Knowledge graph incomplete (only 16 entities)

**Migration Status:**
- Phase 1: Deduplication complete (Sept 2025)
- Phase 2A: Cross-reference cleanup complete (Sept 2025)
- Phase 2B: Orphaned controls fixed (Oct 2025)
- Phase 1 Linking: Relationship tables added (Oct 2025)

---

## Common Tasks - Quick Links

### I want to...

**...understand what tables exist and what they do**
→ `DATABASE_SCHEMA_ANALYSIS.md` - Table of Contents + Core Tables section

**...write a query to get provisions for zone R2**
→ `DATABASE_QUICK_REFERENCE.md` - Common Queries section #1

**...see how tables are related**
→ `DATABASE_ERD_DETAILED.md` - Core Regulatory Provision Flow diagram

**...find out why a query is slow**
→ `DATABASE_SCHEMA_ANALYSIS.md` - Index Strategy section

**...fix data type issues in development_controls**
→ `DATABASE_SCHEMA_ANALYSIS.md` - Data Quality Issues section #1

**...add missing foreign keys**
→ `DATABASE_SCHEMA_ANALYSIS.md` - Data Quality Issues section #2

**...understand the deduplication strategy**
→ `DATABASE_SCHEMA_ANALYSIS.md` - Data Model Patterns section #1

**...query cross-references**
→ `DATABASE_QUICK_REFERENCE.md` - Common Queries section #2

**...connect to the database from Python**
→ `DATABASE_QUICK_REFERENCE.md` - Connection Info section

**...export the schema programmatically**
→ Run `python extract_full_schema.py`

---

## Schema Change Checklist

When modifying the database schema:

1. **Create backup** (see `DATABASE_BACKUP_INSTRUCTIONS.md`)
2. **Write migration SQL** in `migrations/` folder
3. **Test migration** on dev database
4. **Document changes** in migration file header
5. **Run migration** with safety wrapper
6. **Update schema docs:**
   - Run `python extract_full_schema.py`
   - Update `DATABASE_SCHEMA_ANALYSIS.md` if needed
   - Update `DATABASE_ERD_DETAILED.md` if relationships changed
   - Update `DATABASE_QUICK_REFERENCE.md` if common queries affected
7. **Commit all changes** including updated docs

---

## Documentation Maintenance

These files were generated on **2025-10-05** from the live database.

**When to regenerate:**
- After schema migrations
- When adding new tables
- When adding/removing indexes
- After major data model changes

**How to regenerate:**
```bash
# Extract fresh schema
python extract_full_schema.py

# Review database_schema_complete.json
# Manually update markdown files as needed
```

**Automated updates:**
- `database_schema_complete.json` - Run extraction script
- `DATABASE_SCHEMA_ANALYSIS.md` - Manual updates
- `DATABASE_ERD_DETAILED.md` - Manual updates
- `DATABASE_QUICK_REFERENCE.md` - Manual updates

---

## File Size Summary
```
DATABASE_SCHEMA_ANALYSIS.md          62 KB  (Most comprehensive)
DATABASE_ERD_DETAILED.md             39 KB  (Visual diagrams)
DATABASE_QUICK_REFERENCE.md          9.4 KB (Quick lookup)
database_schema_complete.json        95 KB  (Machine-readable)
extract_full_schema.py               7.3 KB (Generator script)

Total documentation size: ~212 KB
```

---

## Getting Started

**New to this database?**
1. Read `DATABASE_QUICK_REFERENCE.md` (10 minutes)
2. Skim `DATABASE_ERD_DETAILED.md` (5 minutes)
3. Reference `DATABASE_SCHEMA_ANALYSIS.md` as needed

**Need to query data?**
1. Open `DATABASE_QUICK_REFERENCE.md`
2. Find relevant common query
3. Modify for your use case

**Need to understand schema?**
1. Open `DATABASE_SCHEMA_ANALYSIS.md`
2. Use Table of Contents
3. Jump to relevant section

**Need to fix data quality?**
1. Read `DATABASE_SCHEMA_ANALYSIS.md` - Data Quality Issues
2. Follow recommendations
3. Test on dev database first

---

## Support & Updates

**Questions about schema?**
- Check `DATABASE_SCHEMA_ANALYSIS.md` first
- Review `DATABASE_ERD_DETAILED.md` for relationships
- Use `DATABASE_QUICK_REFERENCE.md` for common patterns

**Found a schema issue?**
- Document in `DATABASE_SCHEMA_ANALYSIS.md` - Data Quality Issues
- Create migration to fix
- Update documentation after fix

**Need to make schema changes?**
- Follow Schema Change Checklist above
- Keep documentation in sync
- Regenerate JSON schema

---

*This index provides a roadmap to all database schema documentation for the NSW Planning Compliance Engine.*
