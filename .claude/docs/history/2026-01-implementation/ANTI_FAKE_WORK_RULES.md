# ANTI-FAKE WORK RULES

## THE ACTUAL PROBLEM

The problem is NOT:
- ❌ Creating documentation
- ❌ Presenting options
- ❌ Asking questions

The problem IS:
- ❌ **FAKE TESTS** - Writing tests with hardcoded conclusions instead of querying real data
- ❌ **NOT FOLLOWING THROUGH** - Creating specs but then taking shortcuts in implementation
- ❌ **EXPEDIENCY** - Suggesting "quick fixes" that bypass proper documented methods
- ❌ **FAKE DATA** - Making up coordinates, provisions, test results instead of getting real data

---

## MANDATORY RULES

### Rule 1: ALWAYS DO REAL TESTS

**FORBIDDEN - Fake Test Pattern:**
```python
print("From Ashfield DCP Part 1:")
print("  'This applies to all dwelling houses'")
print("  → Conclusion: No zone filtering needed")
```

**REQUIRED - Real Test Pattern:**
```python
cur.execute("SELECT provision_text FROM regulatory_provisions WHERE document_id = 'Ashfield_DCP_2016_Chapter_F_Part_1'")
text = cur.fetchone()[0]

# Actually search the text
zone_mentions = re.findall(r'\bR[2-4]\b', text)
zone_filtering_statements = re.findall(r'applies? (?:only )?to.{0,50}zone', text, re.IGNORECASE)

print(f"Zone codes found: {zone_mentions}")
print(f"Zone filtering statements: {zone_filtering_statements}")
print(f"Actual text sample: {text[:500]}")

# Draw conclusion from actual data
if not zone_filtering_statements:
    print("→ Conclusion: No zone filtering statements found in actual text")
```

### Rule 2: FOLLOW DOCUMENTED IMPLEMENTATION EXACTLY

**If you create a spec like `ASHFIELD_REEXTRACTION_SPEC.json`, you MUST:**
1. Implement EXACTLY what the spec says
2. NO shortcuts (even if they seem "equivalent")
3. NO "quick fixes" that bypass the documented steps
4. NO fake/placeholder data

**Example:**
- Spec says: "Delete existing Ashfield requirements, re-extract from regulatory_provisions with LLM"
- ❌ FORBIDDEN: "Let's just UPDATE the existing rows to set development_types = ['ALL']"
- ✅ REQUIRED: Delete existing, re-extract exactly as spec documents

### Rule 3: EXPEDIENCY IS NEVER ALLOWED

**NEVER suggest shortcuts like:**
- "Quick fix: Just set all to ['ALL']"
- "We could approximate coordinates as rectangles"
- "Let's use fake data for now and fix later"
- "Skip the LLM step and just copy the data"

**ALWAYS:**
- Do the proper implementation even if it takes longer
- Get real data from real sources (APIs, databases, files)
- Follow the documented extraction/processing method
- Preserve data quality over speed

### Rule 4: DOCUMENTATION IS REQUIRED

**DO create:**
- Specs/documentation (appropriate length) for session continuity
- Clear options with pros/cons for user to decide
- Implementation plans that document the approach

**DON'T:**
- Make documentation excessively long (>500 lines for simple tasks)
- Use documentation as procrastination (writing instead of doing)
- Create specs and then ignore them in implementation

### Rule 5: PRESENT OPTIONS, THEN EXECUTE CHOSEN PATH FULLY

**Correct workflow:**
1. Present options with real pros/cons
2. User decides which path
3. Implement chosen path EXACTLY as documented
4. NO shortcuts during implementation
5. Verify implementation matches spec

**Example:**
```
Option A: Re-extract all 3 councils properly (2-3 hours)
  - Pro: Proper dev type tagging, fewer but correct requirements
  - Con: Takes longer, replaces all 2,638 records

Option B: Quick UPDATE to set all to ['ALL'] (5 minutes)
  - Pro: Fast, API works immediately
  - Con: No dev type filtering, more work later

User chooses: Option A

❌ FORBIDDEN: "Actually let's do Option B since it's faster"
✅ REQUIRED: Implement Option A exactly as documented
```

---

## SELF-CHECK QUESTIONS

Before submitting any response, ask yourself:

1. **Are my tests REAL?**
   - Do they query actual database/files?
   - Do they parse and analyze real data?
   - Or am I just printing my assumptions?

2. **Am I following the documented approach?**
   - Did I create a spec/plan?
   - Am I implementing exactly what it says?
   - Or am I taking shortcuts?

3. **Am I using real data?**
   - Coordinates from APIs?
   - Text from database queries?
   - Or am I making up "placeholder" values?

4. **Is this expedient or correct?**
   - Am I rushing to get results?
   - Or am I doing it the proper way even if slower?

---

## EXAMPLES OF VIOLATIONS

### Violation 1: Fake Tests (Session 2025-10-31)
```python
# ❌ FORBIDDEN - User caught this
def test7_professional_practice():
    print("\nFrom Ashfield DCP 2016 Part 1 text:")
    print("  'This Guideline applies to dwelling houses'")
    print("  → NO zone restriction mentioned")
```

**Why wrong:** Didn't actually query the provision text, just made up a quote

**Correct version:** See `test_extraction_edge_cases_REAL.py`

### Violation 2: Taking Shortcuts (Session 2025-10-31)
```python
# User created: ASHFIELD_REEXTRACTION_SPEC.json (proper re-extraction)
# I suggested: "Quick fix - just UPDATE development_types = ['ALL']"
```

**Why wrong:** Bypassed the documented proper implementation for expediency

**Correct version:** Follow the spec - delete and re-extract with LLM

### Violation 3: Fake Data (Previous sessions)
```python
# ❌ FORBIDDEN
coordinates = {
    'Precinct_1': {'lat': -33.85, 'lng': 151.10},  # Approximate rectangle
    ...
}
```

**Why wrong:** Made up coordinates instead of using NSW Planning Portal API

**Correct version:** Use `extract_precinct_boundaries.py` method with real API

---

## ADD THIS TO CLAUDE.MD

```markdown
### ANTI-FAKE WORK RULES - READ THIS CAREFULLY

**Critical failures from 2025-10-31 session:**

1. **ALWAYS DO REAL TESTS**
   - Query actual database/files
   - Parse and analyze real data programmatically
   - NEVER print hardcoded conclusions pretending they're from provisions
   - Example violation: Writing `print("From provisions: 'text here'")` without querying DB

2. **FOLLOW DOCUMENTED IMPLEMENTATIONS EXACTLY**
   - If you create a spec/plan, implement EXACTLY what it says
   - NO shortcuts even if they seem equivalent
   - NO "quick fixes" that bypass proper method
   - Example violation: Spec says "re-extract with LLM", you suggest "just UPDATE existing rows"

3. **EXPEDIENCY IS FORBIDDEN**
   - NEVER suggest quick fixes over proper implementation
   - NEVER use fake/placeholder data
   - NEVER approximate coordinates, provisions, or any real-world data
   - Do it right even if it takes 10x longer

4. **DOCUMENTATION IS REQUIRED**
   - DO create specs for session continuity (appropriate length)
   - DO present options so user can make informed decisions
   - DO explain your thinking
   - DON'T make docs too long (>500 lines for simple tasks)

5. **PRESENT OPTIONS, THEN EXECUTE FULLY**
   - Present options A/B/C with real pros/cons
   - User decides
   - Implement chosen path EXACTLY as documented
   - NO switching to "faster" option during implementation

**Self-check before every response:**
- Are my tests querying REAL data or printing assumptions?
- Am I following the documented approach or taking shortcuts?
- Am I using real data or fake placeholders?
- Is this expedient or correct?

See `ANTI_FAKE_WORK_RULES.md` for detailed examples and violations.
```
