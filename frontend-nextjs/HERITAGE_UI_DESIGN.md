# Heritage Provision Filtering & Ranking UI Design
**Date**: 2026-02-12

---

## Current UI (Already Implemented)

The `HeritageProvisions.tsx` component **already displays** heritage types:

```tsx
// Existing color-coded sections (lines 30-40)
┌──────────────────────────────────────────────┐
│ ✓ Actionable Controls           [33]        │ ← Green, expanded by default
│   "Checkable requirements"                   │
├──────────────────────────────────────────────┤
│ > HCA Character Statements       [6]         │ ← Blue, collapsed
├──────────────────────────────────────────────┤
│ > Background Information         [2]         │ ← Gray, collapsed
└──────────────────────────────────────────────┘
```

**What's missing:**
1. ❌ Filter controls (to toggle types on/off)
2. ❌ Explanatory tooltips (what each type means)
3. ❌ LLM ranking display (if Phase 2 implemented)

---

## Proposed UI: Filter Controls

### Location
Add above the collapsible sections, after property details

### Design - Option 1: Toggle Buttons (Recommended)

```tsx
┌─────────────────────────────────────────────────────────┐
│ Heritage Provision Types            [ℹ️ What are these?] │
│                                                          │
│ [✓ Controls (33)]  [✓ Character (6)]  [✓ Descriptive (2)]│
│                                                          │
│ ─────────────────────────────────────────────────────── │
│                                                          │
│ ✓ Actionable Controls           [33]                    │
│   ...provisions...                                       │
└──────────────────────────────────────────────────────────┘
```

**Behavior:**
- All enabled by default (show everything)
- Click to toggle on/off
- Disabled types: gray text, strikethrough count
- API called when toggled: `&heritage_type=control,character`

### Design - Option 2: Dropdown Filter

```tsx
┌─────────────────────────────────────────────────────────┐
│ Show types: [▼ All Types (41 provisions)    ]           │
│             ├─ All Types (41)                            │
│             ├─ Controls Only (33) ✓                      │
│             ├─ Character Only (6)                        │
│             ├─ Descriptive Only (2)                      │
│             └─ Custom... (multi-select)                  │
└──────────────────────────────────────────────────────────┘
```

---

## Explanatory Content

### Info Tooltip (ℹ️ icon)

**Trigger**: Click "ℹ️ What are these?" or hover over badge

**Content**:
```
┌───────────────────────────────────────────────┐
│ Heritage Provision Types                      │
├───────────────────────────────────────────────┤
│ ✓ CONTROLS (Green)                            │
│   Actionable requirements you must comply     │
│   with. Contains C1-C999 controls and         │
│   imperative verbs ("must", "shall").         │
│   Example: "C7 Retain original roof line"     │
│                                               │
│ ℹ️ CHARACTER (Blue)                            │
│   HCA-specific descriptions of heritage       │
│   significance, history, and key features.    │
│   Example: "HCA 10 is characterized by..."    │
│                                               │
│ 📄 DESCRIPTIVE (Gray)                          │
│   Background information, definitions, and    │
│   policy context. Useful for understanding    │
│   but not directly actionable.                │
│   Example: "Heritage conservation aims to..." │
│                                               │
│ Why categorize?                               │
│ To help certifiers focus on actionable        │
│ controls first, while still showing all       │
│ relevant information.                         │
└───────────────────────────────────────────────┘
```

### Inline Badges (Already Exist)

Keep existing inline labels:
- Controls: "Checkable requirements" (line 158)
- Add for others:
  - Character: "Context & significance"
  - Descriptive: "Background info"

---

## LLM Ranking UI (Phase 2)

### Scenario Input

```tsx
┌─────────────────────────────────────────────────────────┐
│ 🎯 Scenario-Based Ranking (Optional)                     │
│                                                          │
│ Describe your proposal:                                 │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Installing solar panels on pitched roof            │ │
│ └────────────────────────────────────────────────────┘ │
│                                                          │
│ [Rank Provisions]  [Clear]                              │
│                                                          │
│ ℹ️ This uses AI to rank provisions by relevance to your │
│    scenario. All 33 provisions are still shown.         │
└──────────────────────────────────────────────────────────┘
```

### Ranked Results Display

**Option A: Relevance Badges**

```tsx
┌──────────────────────────────────────────────────────────┐
│ ✓ Actionable Controls  [33]  [🎯 Ranked by scenario]     │
│                                                           │
│   🔥 HIGH RELEVANCE (5 provisions)                        │
│   ┌─────────────────────────────────────────────────┐   │
│   │ 🔥 C26 Solar panels must not be fitted to front │   │
│   │    Relevance: 95% match                         │   │
│   │    💡 Directly addresses solar panel placement  │   │
│   │    [View Details]                                │   │
│   └─────────────────────────────────────────────────┘   │
│   ┌─────────────────────────────────────────────────┐   │
│   │ 🔥 C7 Retain original main roof line            │   │
│   │    Relevance: 92% match                         │   │
│   │    💡 Solar panels may affect roof line         │   │
│   └─────────────────────────────────────────────────┘   │
│   ...3 more                                             │
│                                                           │
│   🟡 MEDIUM RELEVANCE (10 provisions)                     │
│   [Expand to see 10 provisions]                          │
│                                                           │
│   🔵 LOW RELEVANCE (18 provisions)                        │
│   [Expand to see 18 provisions]                          │
│                                                           │
│   ℹ️ All 33 provisions shown - ranking helps you         │
│      prioritize. AI reasoning shown for transparency.    │
└───────────────────────────────────────────────────────────┘
```

**Option B: Inline Ranking Scores**

```tsx
┌──────────────────────────────────────────────────────────┐
│ ✓ Actionable Controls  [33]  [Sorted: Most Relevant ▼]   │
│                                                           │
│   ┌─────────────────────────────────────────────────┐   │
│   │ 🔥 95% │ C26 Solar panels must not be fitted... │   │
│   │        │ 💡 Directly addresses solar panels     │   │
│   └─────────────────────────────────────────────────┘   │
│   ┌─────────────────────────────────────────────────┐   │
│   │ 🔥 92% │ C7 Retain original main roof line      │   │
│   │        │ 💡 Solar panels may affect roof line   │   │
│   └─────────────────────────────────────────────────┘   │
│   ┌─────────────────────────────────────────────────┐   │
│   │ 🟡 78% │ C22 Existing roof forms must be...     │   │
│   └─────────────────────────────────────────────────┘   │
│   ...                                                    │
│   ┌─────────────────────────────────────────────────┐   │
│   │ 🔵 23% │ C29 Number of dormers to rear...       │   │
│   └─────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────┘
```

**Option C: Tabs (Recommended)**

```tsx
┌──────────────────────────────────────────────────────────┐
│ ✓ Actionable Controls  [33]                              │
│                                                           │
│ [All 33] [🔥 High (5)] [🟡 Medium (10)] [🔵 Low (18)]     │
│ ─────────────────────────────────────────────────────    │
│                                                           │
│ Showing: High Relevance (5 provisions)                    │
│                                                           │
│   C26 Solar panels must not be fitted to front roof      │
│   ┌─────────────────────────────────────────────────┐   │
│   │ Relevance: 95%                                   │   │
│   │ 💡 Reasoning: Directly addresses solar panel     │   │
│   │    installation restrictions for heritage        │   │
│   │    properties. Pitched roofs visible from        │   │
│   │    street are specifically regulated.            │   │
│   │                                                   │   │
│   │ Model: gemini-2.0-flash                          │   │
│   │ Timestamp: 2026-02-12 10:30 AM                   │   │
│   └─────────────────────────────────────────────────┘   │
│   [View PDF Page 186]                                    │
│                                                           │
│   C7 Proposals must retain the original main roof line   │
│   ...                                                     │
└───────────────────────────────────────────────────────────┘
```

### Ranking Transparency Panel (Expandable)

```tsx
┌──────────────────────────────────────────────────────────┐
│ ⚙️ How Ranking Works                        [Collapse ▲] │
├───────────────────────────────────────────────────────────┤
│ AI Model: Gemini 2.0 Flash                               │
│ Purpose: Rank provisions by scenario relevance           │
│ Authority: NSW AI Assessment Framework compliant         │
│                                                           │
│ ✓ All 33 provisions shown - ranking helps prioritize     │
│ ✓ Human oversight - certifier makes final decision       │
│ ✓ Transparent - AI reasoning shown for each provision    │
│ ✓ Auditable - rankings logged with timestamp & model     │
│                                                           │
│ Learn more: [NSW AIAF Principles]                        │
└───────────────────────────────────────────────────────────┘
```

---

## Component Modifications

### 1. Add Filter Controls Component

**File**: `components/compliance/HeritageTypeFilter.tsx` (NEW)

```tsx
import { Info } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Tooltip } from '@/components/ui/tooltip';

interface HeritageTypeFilterProps {
  selectedTypes: Set<'control' | 'character' | 'descriptive'>;
  typeCounts: { control: number; character: number; descriptive: number };
  onToggle: (type: 'control' | 'character' | 'descriptive') => void;
}

export function HeritageTypeFilter({ selectedTypes, typeCounts, onToggle }: HeritageTypeFilterProps) {
  return (
    <div className="mb-4 p-3 bg-slate-50 rounded-lg border">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">Heritage Provision Types</span>
        <Tooltip content={<TypesExplanation />}>
          <button className="text-slate-500 hover:text-slate-700">
            <Info className="h-4 w-4" />
          </button>
        </Tooltip>
      </div>

      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => onToggle('control')}
          className={`px-3 py-1.5 rounded-full border text-sm font-medium transition-all ${
            selectedTypes.has('control')
              ? 'bg-green-100 text-green-800 border-green-300'
              : 'bg-white text-gray-400 border-gray-200 line-through'
          }`}
        >
          ✓ Controls ({typeCounts.control})
        </button>

        <button
          onClick={() => onToggle('character')}
          className={`px-3 py-1.5 rounded-full border text-sm font-medium transition-all ${
            selectedTypes.has('character')
              ? 'bg-blue-100 text-blue-800 border-blue-300'
              : 'bg-white text-gray-400 border-gray-200 line-through'
          }`}
        >
          ℹ️ Character ({typeCounts.character})
        </button>

        <button
          onClick={() => onToggle('descriptive')}
          className={`px-3 py-1.5 rounded-full border text-sm font-medium transition-all ${
            selectedTypes.has('descriptive')
              ? 'bg-gray-100 text-gray-600 border-gray-300'
              : 'bg-white text-gray-400 border-gray-200 line-through'
          }`}
        >
          📄 Descriptive ({typeCounts.descriptive})
        </button>
      </div>

      <p className="text-xs text-slate-500 mt-2">
        Showing {Array.from(selectedTypes).map(t => typeCounts[t]).reduce((a,b) => a+b, 0)} of {typeCounts.control + typeCounts.character + typeCounts.descriptive} provisions
      </p>
    </div>
  );
}
```

### 2. Add Scenario Ranking Component (Phase 2)

**File**: `components/compliance/HeritageRanking.tsx` (NEW)

```tsx
import { useState } from 'react';
import { Sparkles, Info } from 'lucide-react';

interface HeritageRankingProps {
  onRank: (scenario: string) => Promise<void>;
  isRanking: boolean;
}

export function HeritageRanking({ onRank, isRanking }: HeritageRankingProps) {
  const [scenario, setScenario] = useState('');
  const [showExplanation, setShowExplanation] = useState(false);

  return (
    <div className="mb-4 p-3 bg-purple-50 rounded-lg border border-purple-200">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-purple-600" />
          <span className="text-sm font-medium">Scenario-Based Ranking (Optional)</span>
        </div>
        <button
          onClick={() => setShowExplanation(!showExplanation)}
          className="text-purple-600 hover:text-purple-800"
        >
          <Info className="h-4 w-4" />
        </button>
      </div>

      {showExplanation && (
        <div className="mb-3 p-2 bg-white rounded text-xs text-slate-600">
          <p className="mb-1">
            <strong>How it works:</strong> AI ranks provisions by relevance to your scenario.
          </p>
          <p>
            ✓ All provisions still shown • ✓ Transparent reasoning • ✓ Human oversight
          </p>
        </div>
      )}

      <div className="space-y-2">
        <textarea
          placeholder="Describe your proposal (e.g., 'Installing solar panels on pitched roof')"
          value={scenario}
          onChange={(e) => setScenario(e.target.value)}
          className="w-full px-3 py-2 border rounded text-sm resize-none"
          rows={2}
        />

        <div className="flex gap-2">
          <button
            onClick={() => onRank(scenario)}
            disabled={!scenario.trim() || isRanking}
            className="px-3 py-1.5 bg-purple-600 text-white rounded text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isRanking ? 'Ranking...' : 'Rank Provisions'}
          </button>

          <button
            onClick={() => { setScenario(''); onRank(''); }}
            className="px-3 py-1.5 border rounded text-sm"
          >
            Clear
          </button>
        </div>
      </div>
    </div>
  );
}
```

### 3. Update HeritageProvisions Component

**File**: `components/compliance/HeritageProvisions.tsx`

**Add ranking display** within each provision card:

```tsx
{provision.ranking && (
  <div className="mt-2 p-2 bg-purple-50 rounded border border-purple-200">
    <div className="flex items-center justify-between mb-1">
      <span className="text-xs font-medium">
        {provision.ranking.relevance_level === 'HIGH' ? '🔥' :
         provision.ranking.relevance_level === 'MEDIUM' ? '🟡' : '🔵'}
        {' '}{provision.ranking.relevance_level} Relevance
        ({Math.round(provision.ranking.relevance_score * 100)}%)
      </span>
      <span className="text-xs text-slate-500">
        {new Date(provision.ranking.timestamp).toLocaleTimeString()}
      </span>
    </div>
    <p className="text-xs text-slate-600">
      💡 {provision.ranking.reasoning}
    </p>
  </div>
)}
```

---

## API Integration

### Filter Controls → API

```typescript
// When user toggles types
const selectedTypes = new Set(['control', 'character']); // descriptive disabled

// Build API params
const heritageTypeParam = Array.from(selectedTypes).join(',');

fetch(`/api/provisions/for-property?heritage_type=${heritageTypeParam}...`);
```

### Ranking → API

```typescript
// Step 1: Fetch provisions
const provisions = await fetch(`/api/provisions/for-property?heritage_type=control&topic=Roof`);

// Step 2: Rank via new endpoint
const ranked = await fetch('/api/heritage/rank', {
  method: 'POST',
  body: JSON.stringify({
    provisions: provisions.data.by_layer[0].provisions,
    scenario: "Installing solar panels on pitched roof",
    property: { address: "33 Cardigan St", hca: "HCA 10" }
  })
});

// Step 3: Merge ranking data
provisions.forEach(p => {
  p.ranking = ranked.find(r => r.provision_id === p.id);
});
```

---

## User Flow

### Current Flow (Phase 1 - Implemented)
```
1. User views property → API fetches all heritage provisions
2. UI groups by type: Controls (33), Character (6), Descriptive (2)
3. User clicks to expand/collapse each type
4. User reads provisions
```

### Proposed Flow (Optional Filtering)
```
1. User views property → API fetches all heritage provisions
2. Filter controls shown: [✓ Controls] [✓ Character] [✓ Descriptive]
3. User toggles off "Descriptive" → API re-fetches with heritage_type=control,character
4. UI updates to show only 39 provisions (Controls + Character)
```

### Proposed Flow (Phase 2 - Ranking)
```
1. User views property → 33 roof controls shown
2. User enters scenario: "Installing solar panels on pitched roof"
3. User clicks "Rank Provisions"
4. API sends provisions + scenario to Gemini
5. UI updates with ranking badges: 🔥 High (5), 🟡 Medium (10), 🔵 Low (18)
6. User tabs to "High" to see top 5 most relevant
7. User can still view all 33 via "All" tab
```

---

## Accessibility & UX

### Visual Hierarchy
- **HIGH**: 🔥 Red/orange, bold, at top
- **MEDIUM**: 🟡 Yellow, normal weight
- **LOW**: 🔵 Blue/gray, lighter text

### Cognitive Load
- Default: Show controls only (most relevant)
- Progressive disclosure: Expand character/descriptive if needed
- Ranking: Optional feature, clearly labeled

### Trust & Transparency
- Show AI reasoning inline
- Log model & timestamp
- "Learn more" link to AIAF principles
- Human oversight emphasized

---

## Implementation Priority

### Must Have (Phase 1)
- ✅ Already implemented: HeritageProvisions.tsx displays types
- ⬜ Add: Filter toggle controls
- ⬜ Add: Explanatory tooltips

### Nice to Have (Phase 2)
- ⬜ Scenario input box
- ⬜ Ranking API endpoint
- ⬜ Ranking display with badges
- ⬜ Audit trail logging

### Future Enhancement
- ⬜ Save common scenarios (templates)
- ⬜ Compare rankings across different scenarios
- ⬜ Export ranked provisions to PDF report

---

## Recommendations

### Option A: Minimal (Recommended for MVP)
- Keep current UI (already good)
- Add simple filter toggle buttons
- Add tooltip explaining types
- **No LLM ranking** (deterministic filtering sufficient)

### Option B: Enhanced (If user feedback positive)
- Add filter controls
- Add scenario-based ranking (Phase 2)
- Use tabs to organize High/Medium/Low
- Show AI reasoning inline

### Option C: Maximum (Future)
- All of Option B
- Plus: saved scenarios, comparison view, PDF export
- Plus: certifier feedback loop ("Was this ranking helpful?")

**Next step**: Which option aligns with your product vision?
