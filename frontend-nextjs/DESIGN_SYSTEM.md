# Frontend Design System Reference

**PURPOSE:** Complete CSS/color scheme documentation for the NSW Planning Compliance Engine.
**USAGE:** Reference when adding new components, debugging visual issues, or making design decisions.

**Last Updated:** 2026-02-15
**Status:** Rationalized color scheme (Phase 1 complete)

---

## Table of Contents

1. [Color Philosophy](#color-philosophy)
2. [Authority Colors](#authority-colors)
3. [Semantic Colors](#semantic-colors)
4. [Neutral Utility Colors](#neutral-utility-colors)
5. [Visual Hierarchy](#visual-hierarchy)
6. [Design Tokens](#design-tokens)
7. [Tailwind Configuration](#tailwind-configuration)
8. [UI Patterns](#ui-patterns)
9. [Component Styling Guidelines](#component-styling-guidelines)
10. [Troubleshooting](#troubleshooting)

---

## Color Philosophy

### Core Principles

**Authority Colors = Regulatory Hierarchy**
- Colors represent the Australian planning system hierarchy
- SEPP (State) > LEP (Local) > DCP (Council)
- Colors ONLY appear in tabs and their regulatory content
- Never used for utility UI or chrome

**Semantic Colors = Provision Status**
- Muted palette (30-50% saturation, 95% lightness backgrounds)
- Prohibited (rose), Permitted (emerald), Conditional (amber)
- Professional appearance, no harsh primary colors

**Neutral = Utility & Chrome**
- Headers, buttons, widgets, badges use gray/white
- No authority colors in navigation or utility elements
- Creates clear visual separation between content and chrome

### Color Rationalization Timeline

- **Jan 2026:** Original rainbow scheme (red/orange/blue/green)
- **Feb 2026:** Rationalized to purple/blue/teal authority colors
- **Feb 15 2026:** Complete rationalization (this document created)

---

## Authority Colors

### Purple - SEPP (State Environmental Planning Policies)

**When to use:**
- SEPP tab active state
- SEPP provisions, cards, badges
- State-level requirement indicators
- "Applied from NSW Planning Portal" sections

**Design Token:** `AuthorityColors.SEPP`

**Tailwind Classes:**
```typescript
bg-purple-50    // Lightest background
bg-purple-100   // Card backgrounds
bg-purple-600   // Active tab, primary elements
bg-purple-700   // Hover states, emphasis
text-purple-600 // Icons, badges
text-purple-700 // Body text
text-purple-900 // Headings, titles
border-purple-200  // Card borders
border-purple-500  // Emphasis borders
```

**Hex Values:**
- Primary: `#9333ea` (purple-600)
- Dark: `#7e22ce` (purple-700)

---

### Blue - LEP (Local Environmental Plan)

**When to use:**
- LEP tab active state
- LEP provisions, zoning cards, height/FSR displays
- "Additional Local Provisions" sections
- Planning layers that are LEP-sourced (Zoning Map, FSR Map, Height Map, Heritage Map)

**Design Token:** `AuthorityColors.LEP`

**Tailwind Classes:**
```typescript
bg-blue-50      // Lightest background
bg-blue-100     // Card backgrounds
bg-blue-600     // Active tab, primary elements
bg-blue-700     // Hover states, emphasis
text-blue-600   // Icons, badges
text-blue-700   // Body text, planning layer items
text-blue-900   // Headings, titles
border-blue-200    // Card borders
border-blue-500    // Emphasis borders
```

**Hex Values:**
- Primary: `#2563eb` (blue-600)
- Dark: `#1d4ed8` (blue-700)

**Important Note:**
- NSW Planning Layers card uses blue for individual LEP layers (FSR, Height, Zoning)
- Container itself is neutral gray-100

---

### Teal - DCP (Development Control Plan)

**When to use:**
- DCP tab active state
- DCP provisions, parts, sections
- Council-specific controls
- Precinct provisions
- "About Inner West DCPs" sections

**Design Token:** `AuthorityColors.DCP`

**Tailwind Classes:**
```typescript
bg-teal-50      // Lightest background
bg-teal-100     // Card backgrounds, inactive tab
bg-teal-600     // Active tab, primary elements
bg-teal-700     // Hover states, emphasis
text-teal-600   // Icons, badges
text-teal-700   // Body text
text-teal-900   // Headings, titles
border-teal-200    // Card borders
border-teal-500    // Emphasis borders, accent stripes
```

**Hex Values:**
- Primary: `#14b8a6` (teal-600)
- Dark: `#0f766e` (teal-700)

**Historical Note:**
- Before Feb 2026: Used green-500/600/700
- Rationale for change: Green clashed with emerald (permitted), teal is distinct cool color

---

## Semantic Colors

### Rose - Prohibited Uses

**When to use:**
- Land use table "Prohibited" rows
- Error states in compliance checks
- Rejection indicators

**Muted Palette (30-50% saturation):**
```typescript
bg-rose-50         // Light background (#fef2f2 equivalent)
border-rose-400    // Border accent
text-rose-600      // Icons
text-rose-800      // Body text
```

**Why muted:**
- Harsh red-500 (pure red) clashes with cool authority colors (purple/blue/teal)
- Rose-50/400/800 provides professional appearance
- Still clearly communicates "prohibited" without being alarming

---

### Emerald - Permitted Uses

**When to use:**
- Land use table "Permitted" rows
- Success states in compliance checks
- Approval indicators

**Muted Palette:**
```typescript
bg-emerald-50      // Light background
border-emerald-500 // Border accent (slightly stronger for green visibility)
text-emerald-600   // Icons
text-emerald-900   // Body text (darker for readability)
```

**Why emerald not green:**
- Emerald is blue-green (cooler) vs pure green (warmer)
- Harmonizes better with purple/blue/teal authority colors
- Distinct from old DCP green (now teal)

---

### Amber - Conditional / With Consent

**When to use:**
- Land use table "With consent" / "Conditional" rows
- Warning states
- Review required indicators

**Muted Palette:**
```typescript
bg-amber-50        // Light background
border-amber-400   // Border accent
text-amber-600     // Icons
text-amber-900     // Body text
```

**Why amber not yellow/orange:**
- Amber is brown-tinted yellow (warmer, more serious)
- Professional appearance for "review required" status
- Distinct from old LEP orange (now blue)

---

## Neutral Utility Colors

### Gray Palette - Primary Neutral

**When to use:**
- All utility UI (buttons, inputs, borders)
- Headers, navigation, chrome
- Non-authority-specific containers
- Text, icons, dividers

**Common Classes:**
```typescript
// Backgrounds
bg-white           // Cards, panels
bg-gray-50         // Subtle backgrounds, alternating rows
bg-gray-100        // Container backgrounds (Planning Layers)
bg-gray-200        // Stronger backgrounds
bg-gray-700        // Dark buttons (Analyze Property, Quick Reference Send)
bg-gray-800        // Very dark buttons, emphasis

// Text
text-gray-500      // Labels, secondary text
text-gray-600      // Body text, icons
text-gray-700      // Primary body text
text-gray-800      // Headings, emphasis
text-gray-900      // Strong headings

// Borders
border-gray-200    // Default borders
border-gray-300    // Emphasis borders
border-gray-400    // Strong borders
```

**Consistency Rules:**
- Utility buttons: `bg-gray-700 hover:bg-gray-800`
- Secondary buttons: `bg-gray-200 hover:bg-gray-300`
- Disabled states: `bg-gray-400 text-gray-200`

---

### Stone Palette - Warm Neutral (Limited Use)

**When to use:**
- Property Summary card (unique position emphasis)
- Warm contrast against cool gray

**Usage:**
```typescript
bg-stone-100       // (Was used in old design)
bg-stone-200       // Property Summary background
border-stone-500   // Property Summary left accent
text-stone-500     // Property Summary labels
text-stone-800     // Property Summary headings
```

**Why stone vs gray:**
- Stone is warmer (brown-tinted)
- Creates subtle visual distinction from Planning Layers (gray)
- Emphasizes Property Summary as primary reference context

---

### Slate Palette - Cool Neutral (Limited Use)

**When to use:**
- Quick Reference widget property context banner
- Informational panels that need subtle blue-gray tint

**Usage:**
```typescript
bg-slate-50        // Property context banner background
border-slate-200   // Property context border
text-slate-600     // Property context icons
text-slate-700     // Property context text
text-slate-800     // Property context emphasis
```

**Why slate vs gray:**
- Slate has subtle blue tint (cooler than gray)
- Distinguishes "current property context" without implying authority
- More subtle than blue-50 (LEP color)

---

## Visual Hierarchy

### Container Backgrounds (Lightest to Darkest)

```
Level 1: White (bg-white) - Cards, provisions, content panels
Level 2: Gray-50 - Subtle backgrounds, section dividers
Level 3: Gray-100 - Container backgrounds (Planning Layers)
Level 4: Stone-200 - Emphasized containers (Property Summary)
Level 5: Authority-50 - Authority-specific card backgrounds (purple-50, blue-50, teal-50)
```

### Text Hierarchy (Lightest to Darkest)

```
Label:     gray-500  - Field labels, metadata
Secondary: gray-600  - Secondary text, icons
Body:      gray-700  - Primary body text
Subhead:   gray-800  - Section subheadings
Heading:   gray-900  - Card titles, page headings
```

### Property Summary vs Planning Layers

**Design Decision (Feb 15 2026):**

```
Property Summary:
- Background: stone-200 (darker, warmer)
- Border: border-l-4 border-l-stone-500 (stronger left accent)
- Purpose: Primary property reference context

Planning Layers:
- Background: gray-100 (lighter, cooler)
- Border: border-gray-200
- Purpose: NSW Planning Portal data, not property-specific
```

**Rationale:**
- Darker background = more important/permanent reference
- Warm stone vs cool gray = subtle color distinction
- Left border accent emphasizes "sticky" reference position

---

## Design Tokens

### Location

`frontend-nextjs/lib/design-tokens.ts`

### Structure

**AuthorityColors:**
```typescript
export const AuthorityColors = {
  SEPP: {
    primary: '#9333ea',        // purple-600
    border: 'border-purple-500',
    bg: 'bg-purple-50',
    text: 'text-purple-700',
    hover: 'hover:bg-purple-100',
  },
  LEP: { /* ... */ },
  DCP: { /* ... */ }
};
```

**SemanticColors:**
```typescript
export const SemanticColors = {
  prohibited: {
    bg: 'bg-rose-50',
    border: 'border-rose-400',
    text: 'text-rose-800',
    icon: 'text-rose-600',
  },
  permitted: { /* ... */ },
  conditional: { /* ... */ }
};
```

**LayerBadges:**
```typescript
export const LayerBadges = {
  sepp: { bg: 'bg-purple-100', text: 'text-purple-800', border: 'border-purple-300' },
  lep: { bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-300' },
  dcp: { bg: 'bg-teal-100', text: 'text-teal-800', border: 'border-teal-300' }
};
```

### Usage in Components

```typescript
import { AuthorityColors, SemanticColors } from '@/lib/design-tokens';

// Authority-specific styling
<div className={AuthorityColors.SEPP.bg}>
  <Badge className={LayerBadges.sepp.bg}>SEPP</Badge>
</div>

// Semantic status styling
<div className={SemanticColors.prohibited.bg}>
  <span className={SemanticColors.prohibited.text}>Prohibited</span>
</div>
```

**Benefits:**
- Single source of truth for colors
- Easy to update globally
- Type-safe in TypeScript
- Discoverable via autocomplete

---

## Tailwind Configuration

### Location

`frontend-nextjs/tailwind.config.js`

### Safelist (Critical for Dynamic Classes)

**Why safelist is needed:**
- Tailwind purges unused classes in production
- Dynamic classes (via design tokens) won't be detected in JSX
- Safelist explicitly includes these classes in build

**Current safelist (lines 10-53):**

```javascript
safelist: [
  // Authority Colors - SEPP (Purple)
  'bg-purple-50', 'bg-purple-100', 'bg-purple-600', 'bg-purple-700',
  'text-purple-600', 'text-purple-700', 'text-purple-800', 'text-purple-900',
  'border-purple-200', 'border-purple-300', 'border-purple-500',
  'hover:bg-purple-100',

  // Authority Colors - LEP (Blue)
  'bg-blue-50', 'bg-blue-100', 'bg-blue-600', 'bg-blue-700',
  'text-blue-600', 'text-blue-700', 'text-blue-800', 'text-blue-900',
  'border-blue-200', 'border-blue-300', 'border-blue-500',
  'hover:bg-blue-100',

  // Authority Colors - DCP (Teal)
  'bg-teal-50', 'bg-teal-100', 'bg-teal-600', 'bg-teal-700',
  'text-teal-600', 'text-teal-700', 'text-teal-800', 'text-teal-900',
  'border-teal-200', 'border-teal-300', 'border-teal-500',
  'hover:bg-teal-100', 'hover:bg-teal-200',

  // Semantic Colors - Muted Palette
  'bg-rose-50', 'border-rose-400', 'text-rose-600', 'text-rose-800',
  'bg-emerald-50', 'border-emerald-500', 'text-emerald-600', 'text-emerald-900',
  'bg-amber-50', 'border-amber-400', 'text-amber-600', 'text-amber-900',

  // Layer Badges
  'bg-purple-100', 'border-purple-300',
  'bg-blue-100', 'border-blue-300',
  'bg-teal-100', 'border-teal-300',
],
```

**Maintenance:**
- Add new dynamic classes to safelist when adding design tokens
- Test production build to ensure classes aren't purged
- Use explicit class strings, not template literals: `'bg-purple-50'` not `` `bg-purple-${shade}` ``

### Custom Colors

Tailwind's default palette is used (no custom HSL definitions needed).

**Color Model:**
- Uses Tailwind's built-in HSL-based palette
- Consistent lightness/saturation across shades
- Example: `purple-600` = `hsl(258 90% 66%)`

---

## UI Patterns

### Tab Styling

**Active Tab:**
```typescript
// SEPP
className="bg-purple-600 text-white"

// LEP
className="bg-blue-600 text-white"

// DCP
className="bg-teal-600 text-white"
```

**Inactive Tab:**
```typescript
// SEPP
className="bg-purple-50 text-purple-700 hover:bg-purple-100"

// LEP
className="bg-blue-50 text-blue-700 hover:bg-blue-100"

// DCP (slightly darker for tonal distinction from LEP)
className="bg-teal-100 text-teal-700 hover:bg-teal-200"
```

**Why DCP inactive is teal-100 not teal-50:**
- User feedback: "LEP and DCP inactive tabs too similar tonally"
- Solution: DCP uses -100 shade (slightly darker) for better visual distinction

---

### Collapsible Sections (Chevron Pattern)

**Standard Pattern (Feb 15 2026):**

✅ **Correct:**
```typescript
<div className="flex items-center gap-2">
  {expanded ? (
    <ChevronDown className="w-4 h-4 text-gray-700 flex-shrink-0" />
  ) : (
    <ChevronRight className="w-4 h-4 text-gray-700 flex-shrink-0" />
  )}
  <IconComponent className="h-5 w-5" />
  <span className="flex-1">Section Heading</span>
</div>
```

❌ **Old Pattern (deprecated):**
```typescript
<div className="flex items-center justify-between">
  <div className="flex items-center gap-2">
    <IconComponent />
    <span>Section Heading</span>
  </div>
  {expanded ? <ChevronDown className="ml-auto" /> : <ChevronRight className="ml-auto" />}
</div>
```

**Consistency Rules:**
- Chevron ALWAYS on the LEFT of section headings
- Size: `w-4 h-4` for all section headers (not w-5, w-6, w-12)
- Add `flex-shrink-0` to prevent wrapping
- Use `flex-1` on heading text to fill space
- Color: Match section theme (gray-700 for neutral sections, authority colors for tab-specific)

**Components Updated (Feb 15 2026):**
- CategorySection.tsx (E/C development standards)
- ProvisionsByTocStructure.tsx ("About Inner West DCPs")
- ProvisionsByTopic.tsx ("About Inner West DCPs")
- GeneralDCPSection.tsx (category headers, DCP General Controls)
- property-details-comprehensive.tsx (NSW Planning Layers card)

**Exception:** Individual expandable items within sections may keep chevron on right if it improves clarity of click target.

---

### Badges

**Authority Badges:**
```typescript
// SEPP
<Badge className="bg-purple-100 text-purple-800 border-purple-300">State Policy</Badge>

// LEP
<Badge className="bg-blue-100 text-blue-800 border-blue-300">LEP Clause</Badge>

// DCP
<Badge className="bg-teal-100 text-teal-800 border-teal-300">DCP Provision</Badge>
```

**Status Badges:**
```typescript
// Prohibited
<Badge className="bg-rose-50 text-rose-800 border-rose-400">Prohibited</Badge>

// Permitted
<Badge className="bg-emerald-50 text-emerald-900 border-emerald-500">Permitted</Badge>

// Conditional
<Badge className="bg-amber-50 text-amber-900 border-amber-400">With Consent</Badge>
```

**Neutral Badges:**
```typescript
// Info/metadata
<Badge className="bg-gray-100 text-gray-700 border-gray-300">General</Badge>
```

---

### Buttons

**Primary Action (Authority Context):**
```typescript
// In SEPP tab context
className="bg-purple-600 hover:bg-purple-700 text-white"

// In LEP tab context
className="bg-blue-600 hover:bg-blue-700 text-white"

// In DCP tab context
className="bg-teal-600 hover:bg-teal-700 text-white"
```

**Neutral Utility Buttons:**
```typescript
// Primary utility (Analyze Property, Quick Reference Send)
className="bg-gray-700 hover:bg-gray-800 active:bg-gray-900 text-white"

// Secondary utility
className="bg-gray-200 hover:bg-gray-300 text-gray-700"

// Disabled
className="bg-gray-400 text-gray-200 cursor-not-allowed"
```

**Ghost Buttons:**
```typescript
className="text-gray-600 hover:bg-gray-100"
```

---

### Cards

**Neutral Cards:**
```typescript
<Card className="bg-white border-gray-200">
  <CardHeader>
    <CardTitle className="text-gray-900">Heading</CardTitle>
  </CardHeader>
  <CardContent className="text-gray-700">
    Content
  </CardContent>
</Card>
```

**Authority-Specific Cards:**
```typescript
// SEPP
<Card className="bg-purple-50 border-purple-200">
  <CardTitle className="text-purple-900">SEPP Requirements</CardTitle>
</Card>

// LEP
<Card className="bg-blue-50 border-blue-200">
  <CardTitle className="text-blue-900">LEP Controls</CardTitle>
</Card>

// DCP
<Card className="bg-teal-50 border-teal-200">
  <CardTitle className="text-teal-900">DCP Provisions</CardTitle>
</Card>
```

---

### Links

**External Links (Utility):**
```typescript
className="text-blue-600 hover:text-blue-700 underline"
```

**Why blue-600 not authority colors:**
- Links are utility elements (navigation to external resources)
- Blue is universally recognized as "clickable link" color
- Doesn't imply authority hierarchy (even if linking to LEP document)

---

## Component Styling Guidelines

### When to Use Authority Colors

✅ **DO use authority colors:**
- Tab active/inactive states
- Provision cards displaying SEPP/LEP/DCP content
- Badges indicating regulatory source
- Borders on authority-specific containers
- Icons within authority-specific sections

❌ **DON'T use authority colors:**
- Headers, navigation, chrome
- Utility buttons (analyze, search, submit)
- General-purpose widgets (Quick Reference)
- Property information displays
- Links to external resources

**Example Decision Tree:**

```
Q: Is this element displaying SEPP/LEP/DCP regulatory content?
  └─ Yes → Use authority color
  └─ No  → Is it a utility/chrome element?
           └─ Yes → Use neutral gray
           └─ No  → Does it show permit/prohibited/conditional status?
                    └─ Yes → Use semantic color (rose/emerald/amber)
                    └─ No  → Use neutral gray
```

---

### When to Use Semantic Colors

✅ **DO use semantic colors:**
- Land use permissibility tables (prohibited/permitted/conditional)
- Compliance check results
- Status indicators for provision applicability
- Warning/success/error states in regulatory context

❌ **DON'T use semantic colors:**
- General success/error UI (use gray/red for non-regulatory errors)
- Navigation states
- Form validation (unless directly related to regulatory compliance)

---

### When to Use Neutral Colors

✅ **Always use neutral (gray/white) for:**
- Page layout (headers, footers, sidebars)
- Navigation elements
- Utility buttons (search, analyze, submit)
- Form inputs, labels
- General-purpose widgets
- Text, icons (unless authority-specific)
- Borders, dividers (unless authority-specific)

---

### Property Summary vs Planning Layers

**Property Summary Card:**
```typescript
<div className="bg-stone-200 border-l-4 border-l-stone-500 rounded-r-lg p-4">
  <p className="text-xs text-stone-500">THE PROPERTY</p>
  <h3 className="text-lg text-stone-800">Property Summary</h3>
  {/* Property details */}
</div>
```

**Planning Layers Card:**
```typescript
<Card className="bg-gray-100 border-gray-200">
  <CardHeader>
    <CardTitle className="text-gray-900 flex items-center gap-2">
      <ChevronDown className="w-4 h-4 flex-shrink-0" />
      <FileText className="h-5 w-5 text-gray-700" />
      <span>NSW Planning Layers (12)</span>
    </CardTitle>
  </CardHeader>
</Card>
```

**Key Differences:**
- Background: stone-200 (darker/warmer) vs gray-100 (lighter/cooler)
- Border: stone-500 left accent vs gray-200 standard
- Purpose: Permanent reference vs collapsible data source

---

### Quick Reference Widget

**Color Scheme (Neutral):**
```typescript
// Floating button
className="bg-gray-600 hover:bg-gray-700"

// Header gradient
className="bg-gradient-to-r from-gray-50 to-white"

// Property context banner (subtle slate for current property)
className="bg-slate-50 border-slate-200 text-slate-800"

// Scope note (neutral informational)
className="bg-gray-100 border-gray-300 text-gray-900"

// Send button
className="bg-gray-700 hover:bg-gray-800"

// Bot avatar
className="bg-gray-100 text-gray-600"
```

**Why neutral:**
- Widget works across ALL tabs (SEPP/LEP/DCP)
- Not authority-specific
- Utility tool for quick lookups

**Property Context Uses Slate:**
- Slate-50 (subtle blue-gray tint) distinguishes "current property" banner
- More subtle than blue-50 (LEP color)
- Doesn't imply authority hierarchy

---

## Troubleshooting

### Dynamic Classes Not Appearing in Production

**Symptom:** Colors work in dev but disappear in production build.

**Cause:** Tailwind purges unused classes, doesn't detect dynamic classes from design tokens.

**Solution:**
1. Check if class is in `tailwind.config.js` safelist
2. Add missing class to safelist
3. Rebuild: `npm run build`
4. Test production build: `npm run start`

**Prevention:**
- Always add new design token classes to safelist
- Use explicit strings: `'bg-purple-50'` not template literals
- Test production build before deploying

---

### Colors Look Different Across Components

**Symptom:** "Purple looks different in SEPP tab vs SEPP card."

**Cause:** Inconsistent shade usage (purple-600 vs purple-700).

**Solution:**
1. Check design tokens in `lib/design-tokens.ts`
2. Use design token instead of hardcoding: `AuthorityColors.SEPP.bg`
3. Verify Tailwind class: `bg-purple-50` not `bg-purple-100`

**Reference:**
- Lightest background: `-50` (e.g., `purple-50`)
- Card background: `-100` (e.g., `purple-100`)
- Active element: `-600` (e.g., `purple-600`)
- Hover/emphasis: `-700` (e.g., `purple-700`)

---

### Chevrons Not Positioned Correctly

**Symptom:** Chevron appears on far right instead of left of heading.

**Cause:** Old pattern using `justify-between` and `ml-auto`.

**Solution:**
1. Remove `justify-between` from container
2. Move chevron to first element in flex container
3. Add `flex-shrink-0` to chevron
4. Add `flex-1` to heading text
5. Verify size is `w-4 h-4`

**Example Fix:**
```typescript
// BEFORE (wrong)
<div className="flex items-center justify-between">
  <div className="flex items-center gap-2">
    <Icon />
    <span>Heading</span>
  </div>
  <ChevronDown className="ml-auto" />
</div>

// AFTER (correct)
<div className="flex items-center gap-2">
  <ChevronDown className="w-4 h-4 flex-shrink-0" />
  <Icon className="h-5 w-5" />
  <span className="flex-1">Heading</span>
</div>
```

---

### Teal/Green Confusion

**Symptom:** "Is this DCP or permitted? Colors look similar."

**Historical Context:**
- Before Feb 2026: DCP used green-500/600, permitted used green-50/500
- This created confusion (DCP green vs semantic green)

**Solution (Feb 2026):**
- DCP changed to teal-500/600/700 (cool blue-green)
- Permitted changed to emerald-50/500/900 (blue-green, muted)
- Now visually distinct

**Check:**
- DCP elements: `bg-teal-600`, `text-teal-700`, `border-teal-500`
- Permitted status: `bg-emerald-50`, `text-emerald-900`, `border-emerald-500`

---

### Authority Color Appears in Wrong Context

**Symptom:** "Why is the header teal? It's not DCP-specific."

**Cause:** Authority color used for utility element.

**Solution:**
1. Identify element: Is it displaying regulatory content or utility UI?
2. If utility (header, button, widget) → change to neutral gray
3. If regulatory (provision, badge, tab) → keep authority color

**Examples of Fixes (Feb 2026):**
- Header background: `bg-teal-50` → `bg-white`
- Analyze Property button: `bg-teal-600` → `bg-gray-700`
- Quick Reference widget: `bg-emerald-600` → `bg-gray-600`
- NSW Planning Layers container: `bg-teal-100` → `bg-gray-100`

---

### Tab Colors Don't Match Tab Content

**Symptom:** "LEP tab is orange but content is blue."

**Cause:** Tab button colors not updated during rationalization.

**Solution:**
1. Find tab buttons in `app/assessment/page.tsx`
2. Update active state to authority color
3. Update inactive state to authority-50 or authority-100
4. Verify hover states

**Correct Tab Colors:**
```typescript
// SEPP
active: "bg-purple-600 text-white"
inactive: "bg-purple-50 text-purple-700 hover:bg-purple-100"

// LEP
active: "bg-blue-600 text-white"
inactive: "bg-blue-50 text-blue-700 hover:bg-blue-100"

// DCP
active: "bg-teal-600 text-white"
inactive: "bg-teal-100 text-teal-700 hover:bg-teal-200"
```

---

## Migration Checklist

**When adding a new component:**

- [ ] Determine authority context (SEPP/LEP/DCP/neutral)
- [ ] Import design tokens: `import { AuthorityColors, SemanticColors } from '@/lib/design-tokens'`
- [ ] Use design token classes instead of hardcoding
- [ ] Add any new dynamic classes to `tailwind.config.js` safelist
- [ ] If collapsible, use chevron-left pattern (w-4 h-4, flex-shrink-0)
- [ ] Test in all three tabs to verify colors
- [ ] Test production build to verify classes aren't purged

**When refactoring existing component:**

- [ ] Identify current color usage
- [ ] Determine correct authority/semantic/neutral context
- [ ] Replace hardcoded classes with design token classes
- [ ] Update safelist if needed
- [ ] Verify chevron positioning if collapsible
- [ ] Test visual appearance in context
- [ ] Check for color leakage (authority colors in wrong context)

---

## Reference Links

**Code Locations:**
- Design Tokens: `frontend-nextjs/lib/design-tokens.ts`
- Tailwind Config: `frontend-nextjs/tailwind.config.js`
- Main Page (Tabs): `frontend-nextjs/app/assessment/page.tsx`
- Component Map: `frontend-nextjs/COMPONENT_MAP.md`

**Related Documentation:**
- HERITAGE_UI_DESIGN.md - Heritage-specific UI patterns
- COMPONENT_MAP.md - UI route to component mapping

**Git History:**
- Initial rationalization: Commit `fdac60fd` (Feb 15 2026)
- Phase 1 work: Commits `3ae93207`, `dd08c12f` (Feb 2026)

---

## Quick Reference Table

| Element | Color | Tailwind Class | Rationale |
|---------|-------|----------------|-----------|
| SEPP Tab (active) | Purple-600 | `bg-purple-600` | State-level authority |
| LEP Tab (active) | Blue-600 | `bg-blue-600` | Local authority |
| DCP Tab (active) | Teal-600 | `bg-teal-600` | Council authority |
| DCP Tab (inactive) | Teal-100 | `bg-teal-100` | Darker than LEP for distinction |
| Prohibited Status | Rose-50/800 | `bg-rose-50 text-rose-800` | Muted red, professional |
| Permitted Status | Emerald-50/900 | `bg-emerald-50 text-emerald-900` | Muted green, cool tone |
| Conditional Status | Amber-50/900 | `bg-amber-50 text-amber-900` | Muted yellow, serious |
| Utility Button | Gray-700 | `bg-gray-700` | Neutral, not authority-specific |
| Header | White/Gray-800 | `bg-white text-gray-800` | Neutral chrome |
| Property Summary | Stone-200 | `bg-stone-200` | Warm, emphasized container |
| Planning Layers | Gray-100 | `bg-gray-100` | Cool, neutral container |
| Quick Reference | Gray-600 | `bg-gray-600` | Neutral widget |
| LEP Planning Layer | Blue-700 | `text-blue-700` | LEP data source |
| External Link | Blue-600 | `text-blue-600` | Universal link color |
| Section Chevron | Gray-700, w-4 h-4 | `text-gray-700 w-4 h-4` | Left of heading, consistent size |

---

**End of Design System Reference**
**For questions or updates, see COMPONENT_MAP.md or git history.**
