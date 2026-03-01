# Fix ALL 1,709 Requirements

## Current State
- **1,685 requirements (98.6%) are broken**
- Only 24 requirements (1.4%) work correctly

## The Problem
All categorization scripts dump ALL provision IDs into `source_provision_ids` array instead of using the single provision the LLM identified.

## The Fix
Change this ONE line in ALL categorization scripts:

```python
# OLD (WRONG):
source_provision_ids = provision_ids  # ALL provisions [0,1,2,3,4]

# NEW (CORRECT):
source_provision_ids = [req['source_provision_id']]  # Just ONE provision
```

## Scripts to Fix

1. `categorize_marrickville_provisions_v2.py` - 434 requirements
2. `categorize_leichhardt_provisions_v2.py` - 149 requirements
3. `categorize_ashfield_provisions.py` - 160 requirements
4. All others - 1,062 requirements

## Automated Fix Script

I'll create `fix_all_categorizations.py` that will:
1. Delete ALL broken requirements
2. Re-run extraction with FIXED logic for ALL precincts
3. Takes 2-3 hours + ~$20 OpenAI API

## Quick Alternative

Or I can just:
1. **Update the API to use `primary_source_provision_id` when available**
2. This fixes the 480 requirements (28%) that HAVE primary field
3. Takes 10 minutes
4. Leaves 1,228 still broken

**What do you want:**
- **Option A:** Fix API now (10 min, 28% working)
- **Option B:** Re-extract everything properly (2-3 hrs, 100% working)
