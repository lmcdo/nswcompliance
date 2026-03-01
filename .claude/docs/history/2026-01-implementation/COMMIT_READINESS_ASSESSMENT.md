# Commit Readiness Assessment - Setback Branch
**Date:** 2025-11-05

---

## Current Branch State

**Branch:** `feature/precinct-requirements-architecture`
**Status:** Up to date with origin
**Recent commits:**
- `feb3351d` feat: Integrate NSW Spatial Services road classification API
- `0d86d2bd` docs: Add comprehensive documentation for zone filtering fix
- `d43768ff` fix: Zone filtering now returns 100% of provisions for all councils

---

## Uncommitted Changes

### New Files (Untracked)
**Production code:**
- ✅ `frontend-nextjs/components/compliance/GeneralDCPSection.tsx` - **READY TO COMMIT**
  - Display mode toggle (Separated/Combined)
  - Fixes DCP category duplication issue
  - User-controlled filtering transparency

**Documentation/Analysis (Should NOT commit):**
- ❌ 200+ markdown analysis files (ADG_*, SETBACK_*, LEP_*, etc.)
- ❌ Python test/utility scripts
- ❌ JSON data files
- ❌ Backup files

### Modified Tracked Files
- `CLAUDE.md` - Minor updates
- `check_progress.py` - Testing script
- `check_table_schemas.py` - Testing script
- `test_api_integration.py` - Testing script
- `.next/*` - Build artifacts (auto-generated, ignore)

---

## Recommendation

### Step 1: Commit Display Mode Toggle
**What:** GeneralDCPSection.tsx (DCP duplication fix)
**Message:**
```
feat: Add display mode toggle to fix DCP category duplication

- Adds "Separated" (default) / "Combined" display modes
- Separated mode: General section shows only general reqs, Precinct section shows only precinct reqs
- Combined mode: Both sections show all reqs (original behavior)
- Fixes user confusion from seeing same categories twice
- User-controlled with clear toggle buttons

Resolves: Landscaping appearing in both General and Precinct sections with duplicate content
```

### Step 2: Create Setback Branch
**From:** Current branch (feature/precinct-requirements-architecture)
**Branch name:** `feature/setback-calculator`
**Purpose:** Setback calculator component + permissibility-driven filtering

---

## Git Commands

```bash
# Step 1: Stage and commit GeneralDCPSection.tsx
git add frontend-nextjs/components/compliance/GeneralDCPSection.tsx
git commit -m "feat: Add display mode toggle to fix DCP category duplication

- Adds Separated (default) / Combined display modes
- Separated: General shows only general reqs, Precinct shows only precinct reqs
- Combined: Both sections show all reqs (original behavior)
- User-controlled with clear toggle in header
- Fixes duplication where categories appeared twice with same content

Resolves landscaping appearing in both sections issue

Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

# Step 2: Create and checkout setback branch
git checkout -b feature/setback-calculator

# Step 3: Verify branch
git branch --show-current
```

---

## Setback Branch Scope

**Purpose:** Implement setback calculator and permissibility-driven filtering

**Planned work:**
1. Remove top development type dropdown
2. Add setback calculator component with own dev type input
3. Auto-fill from permissibility check
4. Implement "Hide irrelevant controls" button after permissibility check
5. Show SEPP/ADG/DCP setbacks (LEP data pending extraction)
6. Cross-reference with DCP provisions

**Files to create:**
- `frontend-nextjs/components/compliance/SetbackCalculator.tsx`
- `frontend-nextjs/lib/setback-resolution-service.ts`
- Updates to `frontend-nextjs/app/assessment/page.tsx`
- Updates to `frontend-nextjs/components/compliance/ComplianceDashboard.tsx`

---

## .gitignore Update Needed

**Add to .gitignore:**
```
# Analysis and session documentation
*_ANALYSIS.md
*_REALITY_CHECK.md
*_IMPLEMENTATION_PLAN.md
*_STRATEGY.md
*_GUIDE.md
*_COMPLETE_SUMMARY.md
check_*.py
debug_*.py
test_*.py
investigate_*.py
extract_*.py
*.backup
backups/
extraction_*/
SETBACK_*.md
LEP_*.md
DCP_*.md
ADG_*.md
ASHFIELD_*.md
MARRICKVILLE_*.md
LEICHHARDT_*.md
DATABASE_*.md
COMPREHENSIVE_*.md

# Keep important docs
!README.md
!CLAUDE.md
!PLANNING.md
```

---

## Ready for Setback Work

**Status:** ✅ READY

**Checklist:**
- [x] Display mode toggle completed and tested
- [x] Ready to commit (one clean feature)
- [x] Branch strategy defined
- [x] Setback work scope documented
- [x] .gitignore plan prepared

**Next action:** Execute git commands above to commit and branch
