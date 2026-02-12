# Heritage Filtering UI - Space-Aware Recommendation
**Context**: Compliance assessment interface with limited vertical space

---

## Current Layout Constraints

```
┌────────────────────────────────────────────────────┐
│ Professional Compliance Assessment          [Pro]  │
├────────────────────────────────────────────────────┤
│                                                    │
│ ┌──────────┐  ┌───────────────────────────────┐  │
│ │          │  │ Topics:                       │  │
│ │ Property │  │  - Setbacks                   │  │
│ │ Search   │  │  - Parking                    │  │
│ │          │  │  ▼ Heritage (41 provisions)   │ ← Limited space!
│ │ Controls │  │     [Provisions here...]      │  │
│ │          │  │  - Solar Access               │  │
│ └──────────┘  │  - Building Form              │  │
│    Sidebar    │  ...more topics...            │  │
│    ~25%       └───────────────────────────────┘  │
│    width          Main content ~75% width        │
└────────────────────────────────────────────────────┘
```

**Key Constraints:**
- Heritage is 1 of ~10 topics in a scrollable list
- 41 provisions need to fit in ~600px height max before scrolling
- Certifiers scan quickly - need immediate visual hierarchy
- No room for large explanatory panels
- Mobile/tablet responsiveness required

---

## ❌ NOT RECOMMENDED: Bulky Options

### Option 1: Large Filter Panel (TOO MUCH SPACE)
```
┌─────────────────────────────────────────────┐
│ Heritage Provision Types          [ℹ️ Info] │ ← 80px height
│ [✓ Controls (33)] [✓ Character (6)]        │
│ [✓ Descriptive (2)]                         │
│ Showing 41 of 41 provisions                 │
├─────────────────────────────────────────────┤
│ ✓ Actionable Controls [33]                  │
│   ...provisions...                          │
└─────────────────────────────────────────────┘
```
**Problem**: Wastes 80px of precious vertical space

### Option 2: Scenario Ranking Input (TOO COMPLEX)
```
┌─────────────────────────────────────────────┐
│ 🎯 Scenario-Based Ranking                   │ ← 120px height
│ Describe your proposal:                     │
│ ┌─────────────────────────────────────────┐ │
│ │ Installing solar panels...              │ │
│ └─────────────────────────────────────────┘ │
│ [Rank Provisions] [Clear]                   │
└─────────────────────────────────────────────┘
```
**Problem**: Takes up 120px + adds cognitive load

---

## ✅ RECOMMENDED: Compact Inline Approach

### Design: Single-Line Filter Chips

```
┌──────────────────────────────────────────────────────┐
│ ▼ Heritage (41)   [✓ Controls 33] [Character 6] [Descriptive 2] [?] │ ← 40px
├──────────────────────────────────────────────────────┤
│                                                      │
│ ✓ Actionable Controls (33)                          │ ← Expanded by default
│   C7 Proposals must retain original roof line       │
│   C26 Solar panels must not be fitted to front...   │
│   ...more provisions...                              │
│                                                      │
│ > HCA Character Statements (6)                       │ ← Collapsed
│ > Background Information (2)                         │ ← Collapsed
└──────────────────────────────────────────────────────┘
```

**Key Features:**
1. **Inline filter chips** - 40px height (vs 80px panel)
2. **Active by default** - All types shown initially
3. **Click to filter** - Gray out chip → provisions hidden
4. **Tooltip on [?]** - Hover for explanation
5. **Visual priority** - Controls bold green, Character blue, Descriptive gray

---

## Detailed Spec

### 1. Topic Header (Existing + Add Chips)

**Current** (HeritageProvisions.tsx lines 136-160):
```tsx
<div className="space-y-3">
  {typeOrder.map(type => {
    // Three sections: control, character, descriptive
  })}
</div>
```

**Proposed** (Add above, inside topic header):
```tsx
┌────────────────────────────────────────────────────┐
│ ▼ Heritage (41 provisions)                    [?]  │
│ ┌──────────────────────────────────────────────┐  │
│ │ Show: [✓ Controls 33] [Character 6] [Desc 2]│  │ ← Single row, 40px
│ └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

### 2. Filter Chip Styles

```tsx
// Active (enabled)
<button className="px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800 border border-green-300">
  ✓ Controls 33
</button>

// Inactive (disabled)
<button className="px-2 py-1 rounded text-xs text-gray-400 bg-white border border-gray-200 line-through">
  Controls 33
</button>
```

**Hover state**: Slight scale + tooltip preview

### 3. Info Tooltip (Compact)

**Trigger**: Hover [?] icon (12px, gray)

**Content** (200px wide):
```
┌───────────────────────────┐
│ Heritage Types            │
├───────────────────────────┤
│ CONTROLS                  │
│ Actionable requirements   │
│ (C1-C999, "must", "shall")│
│                           │
│ CHARACTER                 │
│ HCA descriptions          │
│                           │
│ DESCRIPTIVE               │
│ Background info           │
└───────────────────────────┘
```

### 4. Implementation

**File**: `components/compliance/HeritageProvisions.tsx`

**Add at line 136** (before the space-y-3 div):

```tsx
export function HeritageProvisions({ provisions }: HeritageProvisionsProps) {
  const [expandedTypes, setExpandedTypes] = useState<Set<string>>(new Set(['control']));
  const [expandedProvisions, setExpandedProvisions] = useState<Set<number>>(new Set());
  const [viewingPdfImage, setViewingPdfImage] = useState<{ url: string; page: number } | null>(null);

  // NEW: Filter state (all enabled by default)
  const [enabledTypes, setEnabledTypes] = useState<Set<string>>(
    new Set(['control', 'character', 'descriptive'])
  );

  // Group by heritage type
  const byType: Record<string, Provision[]> = { control: [], character: [], descriptive: [] };
  provisions.forEach(p => {
    const type = p.v2_heritage_type || 'descriptive';
    if (!byType[type]) byType[type] = [];
    byType[type].push(p);
  });

  // NEW: Toggle filter
  const toggleTypeFilter = (type: string) => {
    setEnabledTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  // NEW: Filter chips component
  const FilterChips = () => (
    <div className="flex items-center gap-1.5 mb-2 flex-wrap">
      <span className="text-xs text-gray-500 mr-1">Show:</span>

      <button
        onClick={() => toggleTypeFilter('control')}
        className={`px-2 py-1 rounded text-xs font-medium transition-all ${
          enabledTypes.has('control')
            ? 'bg-green-100 text-green-800 border border-green-300'
            : 'text-gray-400 bg-white border border-gray-200 line-through'
        }`}
      >
        {enabledTypes.has('control') ? '✓' : ''} Controls {byType.control.length}
      </button>

      <button
        onClick={() => toggleTypeFilter('character')}
        className={`px-2 py-1 rounded text-xs font-medium transition-all ${
          enabledTypes.has('character')
            ? 'bg-blue-100 text-blue-800 border border-blue-300'
            : 'text-gray-400 bg-white border border-gray-200 line-through'
        }`}
      >
        {enabledTypes.has('character') ? '✓' : ''} Character {byType.character.length}
      </button>

      <button
        onClick={() => toggleTypeFilter('descriptive')}
        className={`px-2 py-1 rounded text-xs font-medium transition-all ${
          enabledTypes.has('descriptive')
            ? 'bg-gray-100 text-gray-600 border border-gray-300'
            : 'text-gray-400 bg-white border border-gray-200 line-through'
        }`}
      >
        {enabledTypes.has('descriptive') ? '✓' : ''} Descriptive {byType.descriptive.length}
      </button>

      <Tooltip content={<TypesTooltip />}>
        <button className="ml-1 text-gray-400 hover:text-gray-600">
          <Info className="h-3 w-3" />
        </button>
      </Tooltip>
    </div>
  );

  const typeOrder = ['control', 'character', 'descriptive'];

  return (
    <>
      {/* NEW: Filter chips */}
      <FilterChips />

      {/* Existing collapsible sections (filtered) */}
      <div className="space-y-3">
        {typeOrder.map(type => {
          const typeProvisions = byType[type];

          // NEW: Hide if disabled
          if (!enabledTypes.has(type)) return null;

          if (!typeProvisions || typeProvisions.length === 0) return null;
          // ...rest of existing code...
        })}
      </div>

      {/* PDF Image Modal */}
      <PdfImageModal ... />
    </>
  );
}

// NEW: Compact tooltip
const TypesTooltip = () => (
  <div className="text-xs space-y-2 w-52">
    <div>
      <div className="font-semibold text-green-800">CONTROLS</div>
      <div className="text-gray-600">Actionable requirements (C1-C999, "must", "shall")</div>
    </div>
    <div>
      <div className="font-semibold text-blue-800">CHARACTER</div>
      <div className="text-gray-600">HCA descriptions and significance</div>
    </div>
    <div>
      <div className="font-semibold text-gray-600">DESCRIPTIVE</div>
      <div className="text-gray-600">Background info and policy context</div>
    </div>
  </div>
);
```

---

## Why This Approach Wins

### Space Efficiency ✅
- **40px overhead** (vs 80-120px for alternatives)
- Leaves ~560px for provisions (fits 15-20 provisions)
- Inline layout doesn't break topic flow

### Cognitive Load ✅
- **Default: show all** - no decision required
- Filters are optional - certifier uses if needed
- Visual hierarchy already clear (green > blue > gray)

### Mobile Responsive ✅
- Chips wrap naturally on narrow screens
- Still only 2 rows max (~60px)
- Touch-friendly tap targets (32px minimum)

### Progressive Disclosure ✅
- Tooltip hidden until needed
- Advanced features (LLM ranking) can be added later
- Doesn't overwhelm new users

---

## Future Enhancement: LLM Ranking

**If** certifiers request scenario-based ranking:

### Add Compact Ranking Toggle (Above Filter Chips)

```tsx
┌────────────────────────────────────────────────────┐
│ ▼ Heritage (41)                             [?]    │
│                                                    │
│ [ ] Rank by scenario [+]            ← Collapsed   │ ← 30px
│                                                    │
│ Show: [✓ Controls 33] [Character 6] [Desc 2]      │
└────────────────────────────────────────────────────┘

// When expanded:
┌────────────────────────────────────────────────────┐
│ ▼ Heritage (41)                             [?]    │
│                                                    │
│ [✓] Rank by scenario [-]            ← Expanded    │
│ ┌──────────────────────────────────────────────┐  │ ← 60px
│ │ Solar panels on pitched roof           [Go]  │  │
│ └──────────────────────────────────────────────┘  │
│                                                    │
│ Show: [✓ Controls 33] [Character 6] [Desc 2]      │
└────────────────────────────────────────────────────┘
```

**Then** provisions show inline ranking badges:
```
C26 Solar panels must not be fitted...    🔥 95%
C7 Retain original roof line               🔥 92%
C22 Existing roof forms...                 🟡 78%
```

**Total overhead**: 40px (filters) + 90px (ranking when expanded) = 130px max

---

## Implementation Priority

### Phase 1: Minimal (1-2 hours)
- ✅ Add filter chips above existing sections
- ✅ Add info tooltip
- ✅ Test on mobile/tablet
- **Deploy immediately** - low risk, high value

### Phase 2: Enhanced (If requested)
- Add scenario ranking toggle
- Integrate Gemini API
- Show inline ranking badges
- **Deploy after certifier feedback**

---

## Final Recommendation

**Implement Phase 1 ONLY:**

1. Add single-row filter chips (40px overhead)
2. Keep existing collapsible sections (already good)
3. Add compact info tooltip
4. **Skip LLM ranking** until certifiers explicitly request it

**Why?**
- Deterministic filtering already achieves 86% reduction (230 → 33)
- Minimal space overhead (40px)
- Zero cognitive load increase
- Can add ranking later if needed
- Implementation: ~1-2 hours

**Cost-benefit**: Maximum value, minimum disruption.
