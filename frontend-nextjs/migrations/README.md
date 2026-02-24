# Database Migrations

## Why Use Migrations?

### 1. **Version Control for Database Schema**
Migrations are like Git commits for your database structure. They:
- Track **what changed** and **when** it changed
- Provide a **history** of schema evolution
- Allow **rollback** to previous schema states
- Enable **code review** of database changes

**Without migrations:**
```sql
-- Someone runs this in production console:
ALTER TABLE regulatory_provisions ADD COLUMN new_field TEXT;
-- ❌ No record of when/why/who made this change
-- ❌ Other developers don't know the field exists
-- ❌ Can't replicate the same schema on staging/local
```

**With migrations:**
```sql
-- migrations/003_add_new_field.sql
ALTER TABLE regulatory_provisions ADD COLUMN new_field TEXT;
-- ✅ Tracked in Git
-- ✅ Other devs run the same migration
-- ✅ Deployed consistently across all environments
```

---

### 2. **Reproducible Environments**

**The Problem:**
- **Local dev:** Database created 3 months ago, schema is stale
- **Staging:** Database manually tweaked during testing
- **Production:** Database has latest changes from last week

**Result:** Three different schemas = bugs only appear in production

**The Solution:**
Migrations ensure **all environments run the same schema**:
```bash
# Fresh database on any environment:
psql -U user -d database -f migrations/001_create_sepp_structured_requirements.sql
# ✅ Identical schema every time
```

---

### 3. **Safe Collaboration**

When multiple developers work on the same codebase:

**Developer A:**
```sql
-- migrations/003_add_exclusion_scope.sql
ALTER TABLE sepp_structured_requirements
  ADD COLUMN exclusion_scope TEXT;
```

**Developer B (working on different feature):**
```sql
-- migrations/004_add_override_condition.sql
ALTER TABLE sepp_structured_requirements
  ADD COLUMN override_condition TEXT;
```

Both migrations can be merged safely because:
- They're **numbered** (003, 004) = clear order
- They're **separate files** = no merge conflicts
- They're **idempotent** (can run multiple times safely)

---

### 4. **Audit Trail for Compliance**

For professional tools (like this one), you need to prove:
- **What data structure** was used at any point in time
- **When** schema changes were deployed to production
- **Who** approved the schema change (Git commit author)

**Example audit question:**
> "On 2026-01-15, did the app check for flood exclusions?"

**With migrations:**
```bash
git log --grep="flood" migrations/
# Shows migration 005_add_flood_exclusions.sql deployed on 2026-01-10
# ✅ Proves the feature existed on Jan 15
```

---

### 5. **Forward & Backward Compatibility**

Good migrations support **rollback**:

```sql
-- migrations/001_create_sepp_structured_requirements.sql
CREATE TABLE sepp_structured_requirements (...);

-- migrations/001_rollback.sql
DROP TABLE IF EXISTS sepp_structured_requirements;
```

If a migration breaks production:
```bash
# Rollback to previous state
psql -f migrations/001_rollback.sql
# ✅ Database restored to working state
```

---

## Migration Best Practices

### ✅ DO:
- **One logical change per migration** (create table, add column, add index)
- **Use numbered prefixes** (001_, 002_, 003_) for order
- **Include comments** explaining why the change was made
- **Test on local/staging** before running in production
- **Make migrations idempotent** (use `IF NOT EXISTS`, `IF EXISTS`)

### ❌ DON'T:
- Modify old migrations after they've run in production
- Delete migration files (they're your schema history)
- Skip migrations (run them in order: 001 → 002 → 003)
- Put data changes in schema migrations (use separate data migration scripts)

---

## How to Run Migrations

### Option 1: Manual (via psql)
```bash
cd frontend-nextjs/migrations

# Run a specific migration
psql -h aws-1-ap-southeast-2.pooler.supabase.com \
     -U postgres.llzdrxywpziewrzudwhj \
     -d postgres \
     -f 001_create_sepp_structured_requirements.sql
```

### Option 2: Node.js Script (recommended)
```bash
node scripts/run-migrations.js
```

This script:
- Reads all `*.sql` files in `migrations/` folder
- Tracks which migrations have run (in a `migrations_history` table)
- Only runs new migrations
- Logs success/failure for each migration

---

## Migration Naming Convention

```
<number>_<description>.sql
```

**Examples:**
- `001_create_sepp_structured_requirements.sql`
- `002_add_pattern_book_indexes.sql`
- `003_add_override_conditions.sql`
- `004_create_pathway_triage_functions.sql`

**Number prefix rules:**
- Start at `001`
- Increment by 1 for each new migration
- Always 3 digits (001, 002, ..., 099, 100)

---

## Current Migrations

| Migration | Description | Status |
|-----------|-------------|--------|
| `001_create_sepp_structured_requirements.sql` | Create structured SEPP requirements table | ⏳ Ready to run |

---

## Next Steps

1. **Review the migration file** to ensure schema matches requirements
2. **Run the migration** (see "How to Run Migrations" above)
3. **Verify the table was created**: `\dt sepp_structured_requirements`
4. **Proceed to Task #3**: Build extraction script
