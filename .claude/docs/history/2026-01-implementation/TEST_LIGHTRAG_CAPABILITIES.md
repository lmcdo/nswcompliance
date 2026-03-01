# LightRAG Capability Testing Protocol

**Purpose:** Objectively test what the LightRAG compliance engine can actually answer before deciding on data strategy.

**Status:** Server running at http://localhost:3007 (Next.js)

---

## Current Reality Check

### What We Know
- **LightRAG:** 217 Inner West documents, 1,725 provisions, 6.47MB knowledge graph
- **Frontend:** Uses PostgreSQL `regulatory_provisions` table directly (NOT LightRAG)
- **Problem:** DA data lacks detail ("Secondary dwelling" not "second storey addition")

### Critical Questions to Answer
1. Can LightRAG answer specific property questions better than database?
2. What types of questions CAN it answer accurately?
3. What types of questions CANNOT it answer?
4. Is the 4-tool pipeline worth the complexity?

---

## Test Protocol

### Phase 1: Basic Factual Queries (Expected to Work)

**Test these via Python CLI:**
```bash
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"
python lightrag_query_interface.py
```

**Test Queries:**
1. "What is the maximum building height in R2 Low Density Residential zone in Inner West LEP 2022?"
2. "What are the front setback requirements for Marrickville?"
3. "What SEPP provisions apply to dual occupancy development?"
4. "What are the parking requirements for a 2-bedroom dwelling?"
5. "Does heritage overlay affect building height limits?"

**Success Criteria:**
- Returns specific clause numbers
- Provides exact measurements/numbers
- Cites source documents

---

### Phase 2: Contextual/Interpretive Queries (May Struggle)

**Test Queries:**
1. "Can I build a second storey on 123 Smith St Marrickville?"
   - *Requires: property-specific data, current height, setbacks*
2. "What developments are similar to a rear granny flat?"
   - *Requires: understanding development type taxonomy*
3. "Which is stricter: LEP or DCP setback rules?"
   - *Requires: comparing multiple provisions*
4. "What gets approved more often: dual occupancy or secondary dwelling?"
   - *Requires: DA outcome data (not in LightRAG)*
5. "How long does a DA take to approve in Inner West?"
   - *Requires: processing time data (not in LightRAG)*

**Expected Result:** LightRAG will struggle or give generic answers

---

### Phase 3: Property-Specific Analysis (Will Definitely Fail)

**Test Queries:**
1. "What's the buildable area for a 600sqm R2 lot with 15m frontage?"
   - *Requires: lot dimensions + calculation*
2. "Show me recent DAs within 500m of 123 Smith St"
   - *Requires: DA database + geospatial query*
3. "Is this property contaminated?"
   - *Requires: EPA contaminated land register*
4. "What's my BASIX climate zone?"
   - *Requires: Planning Portal layer 149 data*
5. "Calculate parking requirements for 4-unit development"
   - *Requires: structured data + formula*

**Expected Result:** LightRAG cannot answer these (needs external data sources)

---

## Hypothesis: LightRAG Use Cases

### ✅ GOOD FOR:
1. **Regulatory Q&A:** "What does Clause 4.3 say?"
2. **Cross-referencing:** "Which SEPP overrides LEP height limits?"
3. **Definitions:** "What is 'dual occupancy' according to LEP?"
4. **Conceptual:** "What planning controls apply to heritage areas?"
5. **Education:** Training planners on DCP requirements

### ❌ BAD FOR:
1. **Property-specific analysis:** Needs lot dimensions, current conditions
2. **DA outcomes:** Needs DA database (approval rates, timelines)
3. **Calculations:** Setbacks, FSR, parking (needs structured data + formulas)
4. **Geospatial:** "Nearby DAs" requires coordinates + distance calc
5. **Real-time:** Planning Portal data (zoning, overlays) changes

---

## Alternative Architecture Decision

### Option A: Keep Both Systems
```
LightRAG (for Q&A):
- "What are the rules?"
- Chatbot interface
- Training/education tool

PostgreSQL (for property assessment):
- Structured provision data
- Calculations (setbacks, FSR)
- Filtering by zone, dev type
```

**Pros:**
- Best of both worlds
- LightRAG for exploration, DB for precision

**Cons:**
- Complexity (2 systems to maintain)
- Confusion (which to use when?)
- Duplication (same data, different formats)

---

### Option B: Abandon LightRAG, Double Down on Database
```
PostgreSQL + Structured Data:
- Provision table (already have 1,725 provisions)
- Add: Provision relationships (cross-references)
- Add: Provision applicability rules (which zones, dev types)
- Add: Calculation logic (setback formulas)
```

**Pros:**
- Single source of truth
- Fast, deterministic queries
- Easier to maintain
- No LLM costs

**Cons:**
- Lose conversational interface
- Harder to discover provisions
- No natural language queries

---

### Option C: Hybrid - Database + LLM Layer
```
PostgreSQL (source of truth):
- All provisions structured

LLM (query translator):
- "What are setbacks?" → SQL query → results
- No knowledge graph, just query translation
```

**Pros:**
- Natural language interface
- Database precision
- No 4-tool pipeline complexity

**Cons:**
- LLM costs per query
- Translation errors possible
- Still needs prompt engineering

---

## Recommended Testing Steps

### Step 1: Run Test Queries (30 min)
```bash
# Start LightRAG query interface
python lightrag_query_interface.py

# Test Phase 1 queries (basic facts)
# Document: What works? What fails?
```

### Step 2: Compare to Database (15 min)
```sql
-- Same questions, but as SQL queries
SELECT * FROM regulatory_provisions
WHERE zone = 'R2'
AND provision_type = 'building_height';
```

**Question:** Is LightRAG answer better/faster/more useful?

### Step 3: Analyze Results (15 min)
- What % of queries does LightRAG answer well?
- For property assessment, does LightRAG add value?
- Is the complexity worth it?

### Step 4: Decision (5 min)
Based on test results:
- **If LightRAG answers <50% accurately:** Abandon, use DB only
- **If LightRAG answers 50-80% accurately:** Keep for Q&A, use DB for assessment
- **If LightRAG answers >80% accurately:** Expand usage, integrate with frontend

---

## Next Actions

1. **You run Phase 1 tests** (I'll help interpret results)
2. **Document what works/fails**
3. **Make architecture decision** based on evidence, not assumptions
4. **Then decide:** What to build next?

---

**Current blocker:** We've been designing features based on ideal data that doesn't exist. Need to test reality first.

**Open the browser to http://localhost:3007 and we can also test the existing frontend while you run LightRAG tests.**
