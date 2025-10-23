# Next Session Scope

**Date:** 2025-10-23
**Current State:** Week 3 API + UI created, integration pending
**Estimated Time:** 2-3 hours

---

## Session Goal

**Complete Week 3 integration and begin testing** - Make categorized precinct requirements visible to users in production UI.

---

## Tasks Breakdown

### 1. Dashboard Integration (30-45 minutes)

**File:** `frontend-nextjs/components/compliance/ComplianceDashboard.tsx`

**What to do:**
1. Import `CategorizedRequirementsCard` component
2. Add state for categorized requirements
3. Add fetch function to call API
4. Integrate with existing precinct detection logic
5. Add component to JSX layout

**Code Location:** See `WEEK3_INTEGRATION_GUIDE.md` Step 1 for exact code

**Success Criteria:**
- ✓ Component renders when precinct detected
- ✓ Shows correct number of requirements
- ✓ Categories display properly
- ✓ No console errors

---

### 2. Source Traceability Handler (30-60 minutes)

**What to do:**
1. Create handler for "View Source" button clicks
2. Fetch source provisions by IDs from database
3. Show provisions in existing `LegalTextPanel` OR create new modal
4. Link to PDF pages if available

**Two Options:**

**Option A: Use Existing LegalTextPanel** (Faster - 30 min)
```tsx
const handleViewSource = async (provisionIds: number[], documentIds: string[]) => {
  // Fetch provisions
  const response = await fetch('/api/provisions/by-ids', {
    method: 'POST',
    body: JSON.stringify({ ids: provisionIds })
  });

  const provisions = await response.json();

  // Show in existing panel
  setSelectedProvision({
    id: provisions[0].id,
    ref_number: provisions[0].ref_number,
    section_header: 'Source Provisions',
    provision_text: provisions.map(p => p.provision_text).join('\n\n'),
    document_id: documentIds[0],
    source: 'DCP'
  });

  setPanelOpen(true);
};
```

**Option B: Create Dedicated Source Viewer** (Better UX - 60 min)
- New modal component
- Shows all source provisions
- Links to PDF pages
- Traceability breadcrumb

**Recommendation:** Start with Option A (faster), upgrade to Option B later if needed.

---

### 3. Testing with Addresses (30-45 minutes)

**Test Plan:**

**Test Addresses (10+):**

1. **Marrickville Precincts:**
   - 180 Addison Road (Abergeldie Estate) - Expect: 8 requirements
   - Address in Barwon Park - Expect: 5 requirements
   - Near Dulwich Hill Station - Expect: 6 requirements
   - Camdenville Precinct 14 - Expect: 8 requirements

2. **Leichhardt Precincts:**
   - Addresses in Part G precincts - Expect: 3-7 requirements

3. **Edge Cases:**
   - Address NOT in precinct - Expect: No categorized requirements card
   - Invalid precinct - Expect: Graceful error
   - Empty precinct - Expect: "No requirements" message

**Testing Checklist:**
- [ ] API returns data for all test addresses
- [ ] UI renders correctly
- [ ] Categories expand/collapse
- [ ] Confidence badges display
- [ ] Conditional warnings show
- [ ] Source links clickable
- [ ] No console errors
- [ ] Performance acceptable (<200ms API response)
- [ ] Mobile responsive
- [ ] Works in Chrome, Firefox, Safari

---

### 4. Bug Fixes & Polish (30-60 minutes)

**Expected Issues:**

1. **Precinct Detection:**
   - May need to adjust precinct matching logic
   - Currently depends on `ENABLE_PRECINCT_MATCHING` flag

2. **Styling:**
   - Card may need spacing adjustments
   - Colors may need tweaking
   - Mobile layout may need fixes

3. **Error Handling:**
   - API failures should show user-friendly message
   - Missing data should degrade gracefully

4. **Performance:**
   - Cache API responses
   - Optimize re-renders

**Polish Tasks:**
- [ ] Add loading skeleton while fetching
- [ ] Add error boundary
- [ ] Add empty state message
- [ ] Add help tooltip
- [ ] Optimize performance
- [ ] Fix any styling issues

---

### 5. Documentation & Handoff (15-30 minutes)

**Create:**
1. **User-facing documentation**
   - What categorized requirements are
   - How to interpret confidence badges
   - What validation status means
   - How to view sources

2. **Developer handoff docs**
   - How the integration works
   - How to add new categories
   - How to modify categorization logic
   - Troubleshooting guide

3. **Week 3 completion report**
   - What was built
   - How it works
   - Testing results
   - Known issues
   - Next steps

---

## Optional: Week 4 Preview (If time permits)

### Week 4 Goal: Production Rollout

**Tasks:**
1. **Feature Flag Management**
   - Create feature flag for categorized requirements
   - Enable for 10% of users first
   - Monitor metrics

2. **Monitoring Setup**
   - Track API response times
   - Track user interactions (clicks, expansions)
   - Track errors

3. **User Feedback Collection**
   - Add feedback button
   - Collect qualitative feedback
   - Track satisfaction metrics

4. **Expert Validation Workflow**
   - Review medium confidence requirements (46)
   - Validate high confidence samples (10%)
   - Mark validated in database

**Note:** Only start Week 4 if Week 3 integration is fully complete and tested.

---

## Session Timeline

### Hour 1: Core Integration
- 0:00-0:30: Dashboard integration
- 0:30-0:45: Test basic functionality
- 0:45-1:00: Fix any immediate issues

### Hour 2: Source Traceability
- 1:00-1:30: Implement "View Source" handler
- 1:30-1:45: Test source viewing
- 1:45-2:00: Polish and bug fixes

### Hour 3: Testing & Documentation
- 2:00-2:30: Comprehensive testing (10+ addresses)
- 2:30-2:45: Bug fixes
- 2:45-3:00: Create completion report

**Total:** 3 hours (flexible - can stop after 2 hours if core complete)

---

## Dependencies

**Required:**
- ✅ Week 2 complete (database with 330 requirements)
- ✅ Week 3 API endpoint created
- ✅ Week 3 UI component created

**Optional but helpful:**
- Next.js dev server running
- Database accessible
- Test addresses list ready

**Blockers:**
- None currently identified

---

## Success Criteria

**Minimum (Must Have):**
- [ ] CategorizedRequirementsCard displays in ComplianceDashboard
- [ ] Shows correct requirements for precinct addresses
- [ ] Categories expand/collapse
- [ ] No breaking errors

**Target (Should Have):**
- [ ] Source viewing works
- [ ] Tested with 10+ addresses
- [ ] All known bugs fixed
- [ ] Documentation complete

**Stretch (Nice to Have):**
- [ ] Loading states polished
- [ ] Mobile fully optimized
- [ ] Expert validation workflow started
- [ ] Week 4 monitoring setup begun

---

## Deliverables

### Code
1. Updated `ComplianceDashboard.tsx` with integration
2. Source traceability handler (new API endpoint or handler function)
3. Bug fixes and polish

### Documentation
1. Week 3 completion report (like `WEEK2_PROCESSING_COMPLETE.md`)
2. User guide for categorized requirements
3. Integration notes for future developers

### Testing
1. Test results for 10+ addresses
2. Bug list (if any)
3. Performance metrics

---

## Risk Assessment

**Low Risk:**
- API endpoint already working
- UI component already built
- Database ready

**Medium Risk:**
- Integration with existing ComplianceDashboard (lots of state management)
- Precinct detection logic (may need tweaking)
- Source traceability (depends on existing code structure)

**High Risk:**
- None identified

**Mitigation:**
- Follow integration guide exactly
- Test incrementally
- Have rollback plan (feature flag)

---

## Rollback Plan

If integration causes issues:

1. **Immediate:**
   - Remove CategorizedRequirementsCard from JSX
   - Comment out fetch function
   - Keep API endpoint (doesn't affect existing code)

2. **Feature Flag:**
   - Add `ENABLE_CATEGORIZED_REQUIREMENTS` env var
   - Only show if flag is true
   - Can disable without code changes

3. **Git Revert:**
   - Revert commit `571feee9` if needed
   - API and component won't affect existing code if not imported

---

## Questions to Answer in Session

1. **Where exactly should categorized requirements appear?**
   - After precinct provisions browser?
   - As replacement for precinct provisions browser?
   - As separate tab?

2. **How should source viewing work?**
   - Use existing LegalTextPanel?
   - Create new modal?
   - Open in new tab?

3. **Should we show for all precincts or only validated ones?**
   - Show all (current: 86% high confidence)
   - Only show validated (current: 0% validated)
   - Show with disclaimer for unvalidated

4. **Feature flag or direct rollout?**
   - Direct (simpler)
   - Feature flag (safer)

5. **Mobile experience priority?**
   - Must work perfectly
   - Can be simplified
   - Desktop-first is OK

**Recommendation:** Answer these first 15 minutes of session, then proceed with implementation.

---

## Pre-Session Prep

**Before starting:**
1. ✓ Read `WEEK3_INTEGRATION_GUIDE.md`
2. ✓ Read `WEEK2_PROCESSING_COMPLETE.md`
3. ✓ Review `ComplianceDashboard.tsx` structure
4. ✓ Have test addresses ready
5. ✓ Start Next.js dev server
6. ✓ Test API endpoint with `test_precinct_requirements_api.js`

---

## Post-Session

**After session complete:**
1. Create Week 3 completion report
2. Commit and push all changes
3. Create PR for review (optional)
4. Tag release (optional)
5. Plan Week 4 if appropriate

---

## Contacts & Resources

**Key Files:**
- `WEEK3_INTEGRATION_GUIDE.md` - Complete integration instructions
- `WEEK2_PROCESSING_COMPLETE.md` - Background on data
- `frontend-nextjs/components/compliance/ComplianceDashboard.tsx` - Integration point
- `frontend-nextjs/app/api/compliance/precinct-requirements/route.ts` - API endpoint

**Test Script:**
- `test_precinct_requirements_api.js` - API testing

**Database:**
- Table: `dcp_precinct_requirements` (330 rows)
- Categories: 12
- High confidence: 86.1%

---

## Estimated Effort

| Task | Best Case | Likely | Worst Case |
|------|-----------|--------|------------|
| Dashboard Integration | 20 min | 30 min | 60 min |
| Source Traceability | 20 min | 45 min | 90 min |
| Testing | 20 min | 30 min | 60 min |
| Bug Fixes | 10 min | 30 min | 60 min |
| Documentation | 10 min | 20 min | 30 min |
| **Total** | **80 min** | **2.5 hrs** | **5 hrs** |

**Realistic Estimate:** 2.5-3 hours

---

## Next Next Session (If Week 3 finishes early)

**Week 4 Preview:**
1. Expert validation workflow
2. Production monitoring setup
3. User feedback collection
4. Process base requirements (LGA/Zone/DevType)

**OR**

**Maintenance:**
1. Fix low-recall categories (fencing: 0%, privacy: 25%)
2. Re-process with improved prompts
3. Add missing categories
4. Improve extraction quality

---

**Session Scope:** ✅ CLEARLY DEFINED

**Ready to Start:** ✅ YES

**Estimated Duration:** 2.5-3 hours

**Blockers:** None

**Risk Level:** Low-Medium

**Confidence:** High (90%)
