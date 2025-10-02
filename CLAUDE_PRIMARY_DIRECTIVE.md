# CLAUDE PRIMARY DIRECTIVE - READ FIRST
## **MANDATORY: Check this file at start of EVERY session**

---

## **MAIN REFERENCE DOCUMENT:**
**`documentation/prps/PRP-A_MICRO_PIPELINE_IMPLEMENTATION.md`**

This document contains the **ONLY VALID** implementation instructions for the 4-tool pipeline.

---

## **CRITICAL EXECUTION RULES:**

### **1. ONE PRP PER SESSION - NO EXCEPTIONS**
- Execute **ONLY ONE** PRP per conversation
- **STOP** after completing the assigned PRP
- **DO NOT** attempt multiple PRPs in one session
- **DO NOT** continue to "help" with next steps

### **2. ATOMIC PRP SEQUENCE:**
```
PRP-A1: Package Installation Verification (15 min)
PRP-A2: PDF Content Extraction (30 min) 
PRP-A3: Source Grounding (30 min)
PRP-A4: Knowledge Graph Construction (45 min)
PRP-A5: LightRAG Integration (30 min)
PRP-A6: Query Interface (20 min)
PRP-A7: Frontend Integration (20 min)
```

### **3. MANDATORY VERIFICATION BEFORE EACH PRP:**
```bash
# MUST RUN FIRST - Check what PRP to execute next
./prp_checkpoints/verify_completion.sh
```

### **DATABASE CONNECTION INFORMATION:**
**CORRECT DATABASE CREDENTIALS:**
- **Host:** localhost
- **Database:** `nsw_planning`
- **User:** postgres
- **Password:** `postgres`
- **Port:** 5432

**SEPP DATA LOCATION:**
- Main table: `regulatory_provisions` (2140+ SEPP provisions)
- Other tables: `sepp_lep_overrides`, `regulatory_provisions_clean`
- Total tables: 18 (most comprehensive database)

### **4. SESSION END PROTOCOL:**
- Mark PRP as completed: `./prp_checkpoints/mark_prp_complete.sh A1 "completion message"`
- **EXPLICITLY STATE**: "PRP-A1 completed. Start next session for PRP-A2"
- **STOP** - Do not suggest next steps

### **5. NO WORKAROUNDS ALLOWED:**
- No "close enough" solutions
- No manual summaries 
- No skipping failed steps
- No continuing without verification

---

## **CURRENT STATUS CHECK:**

**Before starting any work:**
1. Read `documentation/prps/PRP-A_MICRO_PIPELINE_IMPLEMENTATION.md`
2. Run `./prp_checkpoints/verify_completion.sh`
3. Execute ONLY the next incomplete PRP
4. Create completion marker
5. **STOP**

---

## **IF YOU VIOLATE THESE RULES:**
The user will restart the session and you will be reminded of this directive.

**The LLM execution failure pattern MUST be broken with strict session boundaries.**

---

**REMEMBER: One PRP, one session, atomic completion, STOP.**