# Obsolete Files to Delete
## Generated: 2025-08-26

### ❌ OBSOLETE Python Scripts (Windows native approach - FAILED)
These scripts attempted Windows-native LightRAG which has async issues:

```bash
# Delete these failed Windows Python scripts
rm scripts/direct_dcp_access.py
rm scripts/direct_lep_access.py  
rm scripts/process_dcp_real_lightrag.py
rm scripts/process_lep_real_lightrag.py
rm scripts/test_integration.js
rm test_regulatory_retriever.js
rm test_all_regulatory_text.js
```

### ❌ OBSOLETE LightRAG Storage Directories (Windows native - INCOMPLETE)
These contain incomplete/broken LightRAG processing from Windows attempts:

```bash
# Delete failed Windows LightRAG storage directories
rm -rf lightrag_ashfield_dcp_storage/
rm -rf lightrag_leichhardt_dcp_storage/
rm -rf lightrag_marrickville_dcp_storage/
rm -rf lightrag_ashfield_storage/
rm -rf lightrag_leichhardt_storage/
rm -rf lightrag_marrickville_storage/
rm -rf lightrag_lep_storage/
```

### ❌ OBSOLETE Temporary Extraction Directories
These contain chunked documents from failed processing attempts:

```bash
# Delete temporary extraction directories
rm -rf temp_extraction_Ashfield/
rm -rf temp_extraction_Leichhardt/
rm -rf temp_extraction_Marrickville/
rm -rf temp_extraction_LEP/
rm -rf temp_extraction_SEPP_Housing/
```

### ❌ OBSOLETE Enhanced Setback JSON Files (Fake data)
These contain processed data with incorrect values:

```bash
# Delete enhanced setback cache files
rm public/regulatory-data/ashfield_enhanced_setbacks.json
rm public/regulatory-data/leichhardt_enhanced_setbacks.json
rm public/regulatory-data/marrickville_enhanced_setbacks.json
```

### ⚠️ KEEP BUT MARK AS OBSOLETE (May need for reference)
```bash
# Rename to indicate obsolete status
mv PRP_REGULATORY_TEXT_EXTRACTION.md OBSOLETE_PRP_REGULATORY_TEXT_EXTRACTION.md
mv lib/regulatory-text-retriever.ts.backup OBSOLETE_regulatory-text-retriever.ts.backup
```

### ✅ KEEP - Still Needed
```bash
# Active PRPs and status tracking
PRP_WSL2_LIGHTRAG_IMPLEMENTATION.md
PRP_STATUS.md
.claude/instructions.md

# Core application files (need updating for WSL2)
lib/regulatory-text-retriever.ts
lib/enhanced-compliance-engine.ts
lib/compliance-engine.ts

# Original document sources (needed for WSL2 processing)
docs/dcps/
docs/leps/
docs/sepps/

# Unified data (may have some useful rules)
public/regulatory-data/unified/
```

---

## Cleanup Commands

### Option 1: Interactive Cleanup (Safer)
```bash
# Review each file before deleting
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"

# Move obsolete files to a backup directory first
mkdir OBSOLETE_BACKUP
mv scripts/direct_*.py OBSOLETE_BACKUP/
mv scripts/process_*_lightrag.py OBSOLETE_BACKUP/
mv lightrag_*_storage/ OBSOLETE_BACKUP/
mv temp_extraction_*/ OBSOLETE_BACKUP/

# After verifying nothing breaks, delete the backup
# rm -rf OBSOLETE_BACKUP/
```

### Option 2: Direct Deletion (Faster but riskier)
```bash
# Delete all obsolete files at once
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"

# Delete obsolete scripts
rm scripts/direct_dcp_access.py scripts/direct_lep_access.py
rm scripts/process_dcp_real_lightrag.py scripts/process_lep_real_lightrag.py
rm scripts/test_integration.js test_regulatory_retriever.js test_all_regulatory_text.js

# Delete obsolete storage
rm -rf lightrag_*_storage/
rm -rf temp_extraction_*/

# Delete obsolete cache
rm public/regulatory-data/*_enhanced_setbacks.json
```

---

## Post-Cleanup Verification

After cleanup, verify:
1. ✅ Dev server still runs: `npm run dev -- --port 3000`
2. ✅ No broken imports in TypeScript files
3. ✅ PRP_STATUS.md and active PRPs remain
4. ✅ Original documents in docs/ remain
5. ✅ .claude/instructions.md remains

---

## Why Delete These Files?

1. **Prevent confusion**: Old scripts might be accidentally used
2. **Save space**: LightRAG storage directories are large (~100MB each)
3. **Clear path forward**: Only WSL2 approach should be visible
4. **Avoid backsliding**: Can't revert to failed approaches if files don't exist

---

## Recommendation

**Use Option 1 (Interactive Cleanup)** - Move files to OBSOLETE_BACKUP first, verify everything works, then delete the backup. This is safer and allows recovery if needed.