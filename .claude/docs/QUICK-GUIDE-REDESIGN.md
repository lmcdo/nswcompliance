# Quick Guide Redesign - February 2026

## Changes Made

### **Before:**
- 4 complex diagrams (5MB+ PNG files each, 20MB+ total)
- Heavy images caused slow page loads
- Text in images unreadable on mobile
- Missing Pattern Book CDC pathway entirely
- Generic workflow descriptions
- Hard to scan on mobile devices

### **After:**
- **Zero image files required** (removed all 4 diagrams)
- CSS-based visual hierarchy using Tailwind
- Mobile-first responsive design
- **Added Pattern Book CDC** as Pathway 1 (most important new feature)
- Clear numbered steps with icons
- Timeline badges show speed differences (10 days vs 20 days vs 30-90 days)
- Larger text, better spacing for mobile readability
- Scannable with clear visual hierarchy

---

## New Structure

### 1. **Regulatory Hierarchy (CSS-based)**
Replaced complex diagram with 3 colored cards:
- Purple: SEPP (State)
- Orange: LEP (Council Zones)
- Green: DCP (Design Controls)

No image needed — uses Tailwind CSS styling with icons.

### 2. **Pathway Comparison Grid**
4-box grid showing approval timelines:
- Pattern Book: 10 days (fastest)
- E&C CDC: 20 days
- Heritage: 30-90 days
- Standard DA: 30-90 days

### 3. **Four Pathways (Priority Order)**

#### **Pathway 1: Pattern Book CDC** ✨ NEW
- Emerald green border (highlights fastest pathway)
- "FASTEST" badge
- 217 exclusion triggers + 199 numeric standards explained
- Common blockers listed (heritage, narrow lot, steep slope, etc.)
- 4 clear numbered steps

#### **Pathway 2: Exempt & Complying CDC**
- Purple theme
- "20 DAYS" badge
- Work type filtering explained (Deck/Garage/Pool/Fence)
- 4 numbered steps
- Pro tip about PDF viewing

#### **Pathway 3: Heritage Properties**
- Amber theme
- "30-90 DAYS" badge
- 5 numbered steps (heritage is more complex)
- Explains HCA objectives + DCP controls + SEPP overlays
- Notes about 63 Inner West HCAs

#### **Pathway 4: Standard DA**
- Blue theme
- "30-90 DAYS" badge
- Emphasizes DCP as bulk of assessment
- Topic filtering explained
- PDF export mentioned
- 4 numbered steps

### 4. **Quick Navigation Tips**
- Property summary panel usage
- PDF icon functionality
- Topic filters
- Pathway comparison card
- "All three tabs apply" principle

---

## Mobile Optimization

✅ **Responsive breakpoints:**
- Mobile (320px+): Single column, larger text, stacked layout
- Tablet (768px+): Some side-by-side elements
- Desktop (1024px+): Full multi-column layout

✅ **Touch-friendly:**
- Larger tap targets
- No hover-only interactions
- Buttons sized for fingers (not mouse pointers)

✅ **Readable text:**
- Base size: 12px (0.75rem) minimum
- Headings: 14px-18px
- No text embedded in images

✅ **Fast loading:**
- No 5MB+ images
- Pure CSS styling
- Lazy-loaded icons from lucide-react

---

## Optional: Simple Hierarchy Diagram (NotebookLM)

If you want **one simple visual** for social media or presentations, use NotebookLM to generate:

### **Prompt for NotebookLM Audio Overview:**

> "Create a simple visual diagram showing the NSW planning system's three-layer hierarchy:
>
> **Layer 1 - SEPP (Purple):** State Environmental Planning Policies. State-wide rules covering Exempt & Complying Development, BASIX targets, Heritage protections, and Apartment Design Guidelines. Overrides local rules where inconsistent.
>
> **Layer 2 - LEP (Orange):** Local Environmental Plans. Council-specific zoning maps and development standards including height limits, Floor Space Ratio (FSR), and land use permissibility tables.
>
> **Layer 3 - DCP (Green):** Development Control Plans. Detailed local design rules covering setbacks, landscaping, character controls, parking requirements, and materials.
>
> Show these as three horizontal layers stacked vertically, with SEPP at top (highest authority), LEP in middle, and DCP at bottom. Include the key message: 'All three layers apply to every property — check all tabs in PlotDetect.'
>
> Style: Clean, professional, minimal text, use purple/orange/green color coding."

### **Alternative: Figma/Canva Template**

If creating in design tool:
- **Dimensions:** 1200x800px (web-optimized)
- **File format:** WebP or optimized PNG (<100KB)
- **Colors:**
  - SEPP: `#9333ea` (purple-600)
  - LEP: `#f59e0b` (amber-500)
  - DCP: `#10b981` (emerald-500)
- **Fonts:** Inter or system fonts for web compatibility
- **Icons:** Use lucide-react icon set (Landmark, Building2, FileText)

---

## Files Changed

✅ **Modified:**
- `frontend-nextjs/app/quick-guide/page.tsx` - Complete rewrite

❌ **Can be deleted** (no longer used):
- `frontend-nextjs/public/userguidediagramforverify.png` (5.4MB)
- `frontend-nextjs/public/hierarchyandcompliance.png` (5.8MB)
- `frontend-nextjs/public/DAProcess.png` (5.1MB)
- `frontend-nextjs/public/sepp-lep-dcp-hierarchy-diagram.png` (5.2MB)

**Total file size reduction: 21.5MB → 0MB** 🎉

---

## Testing Checklist

- [ ] Mobile (iPhone): Text readable, no horizontal scroll
- [ ] Tablet (iPad): Layout adapts appropriately
- [ ] Desktop: Full layout displays correctly
- [ ] Pattern Book pathway shows emerald border
- [ ] All numbered steps display correctly
- [ ] Icons load from lucide-react
- [ ] Links to /assessment work
- [ ] Page loads fast (<1 second)

---

## GTM Alignment

This redesign directly supports your go-to-market strategy:

### **For Architects (Priority #2):**
✅ Pattern Book CDC shown first (10-day pathway)
✅ Clear eligibility criteria (217 triggers)
✅ Speed emphasis (timeline badges)

### **For Developers (Priority #3):**
✅ Approval timelines front and center
✅ "Can I build this?" answered quickly
✅ Common blockers listed upfront

### **For Town Planners (Priority #1):**
✅ Heritage workflow comprehensive (5 steps)
✅ Standard DA prep process detailed
✅ PDF export for DA packages mentioned

### **For Certifiers (Priority #4):**
✅ E&C CDC workflow clear
✅ PDF verification emphasized
✅ SEPP compliance checking explained

---

## Next Steps

1. **Test on mobile device** to validate readability
2. **Delete old diagram files** from `/public` folder (saves 21.5MB)
3. **Optional:** Create one simple hierarchy graphic for marketing using NotebookLM prompt above
4. **Update any external links** that reference old `/userguidediagramforverify.png` paths

---

## Maintenance

**When to update:**
- New pathways added (e.g., State-Led Rezoning fast track)
- SEPP amendments change timelines
- New features added to PlotDetect (e.g., AI chatbot integration)

**How to update:**
- Edit `frontend-nextjs/app/quick-guide/page.tsx`
- Add new pathway as a new colored card section
- Update timeline badges if approval speeds change
- Keep mobile-first responsive design
