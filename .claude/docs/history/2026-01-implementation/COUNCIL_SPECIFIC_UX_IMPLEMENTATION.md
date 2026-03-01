# Council-Specific UI/UX Implementation Plan

## The Problem

Current API applies identical filtering logic for all councils, but each council's DCP has a DIFFERENT structure:

| Council | Total Provisions | Primary Layer | Key Filter |
|---------|-----------------|---------------|------------|
| Marrickville | 1,051 | Balanced (precinct 34%, condition 30%) | Zone + Precinct |
| **Leichhardt** | **2,989** | **Generic (77%)** | **Topic (CRITICAL)** |
| Ashfield | 1,526 | Condition (59%) | Heritage/Condition |

## Impact on Professional Users

Without council-aware filtering:
- Marrickville R2 Dwelling: 228 provisions ✅ Workable
- **Leichhardt R2 Dwelling: 2,211 provisions** ❌ Unusable without topic filter
- Ashfield R2 Dwelling: 394 provisions ✅ Workable

## Implementation Changes

### 1. API Enhancement (`/api/provisions/for-property/route.ts`)

Add council-aware filtering logic:

```typescript
// Detect council from property or LGA
const council = detectCouncil(filters.lga, filters.formerCouncil);

// Council-specific layer behavior
switch (council) {
  case 'leichhardt':
    // Leichhardt: Topic filter is MANDATORY for DA queries
    // If no topic selected and results > 500, return warning
    if (!filters.topic && totalCount > 500) {
      return {
        warning: 'TOPIC_FILTER_RECOMMENDED',
        message: 'Leichhardt DCP has 2,989 provisions. Select a topic to narrow results.',
        suggested_topics: ['parking', 'building_form', 'landscaping', 'heritage']
      };
    }
    break;

  case 'ashfield':
    // Ashfield: Condition layer is primary
    // If property has heritage, condition layer is critical
    break;

  case 'marrickville':
    // Marrickville: Balanced - zone filtering works
    // Standard 4-layer approach is fine
    break;
}
```

### 2. UI Enhancement (`ProvisionsByTopic.tsx`)

Add council-aware filter prominence:

```typescript
// Props addition
interface ProvisionsByTopicProps {
  council?: string; // 'marrickville' | 'leichhardt' | 'ashfield'
  // ... existing props
}

// Render different filter layouts per council
{council === 'leichhardt' && (
  <div className="bg-amber-50 border-l-4 border-amber-400 p-3 mb-4">
    <p className="text-sm">
      <strong>Leichhardt DCP:</strong> Select a topic to narrow results
    </p>
    <TopicFilter
      topics={['parking', 'building_form', 'landscaping', 'heritage', 'setbacks']}
      onChange={setSelectedTopic}
      required={true}
    />
  </div>
)}

{council === 'marrickville' && (
  <div className="flex gap-4">
    <ZoneFilter zones={['R2', 'R3', 'R4', 'B1', 'B2']} />
    <TopicFilter topics={...} />
  </div>
)}

{council === 'ashfield' && (
  <div className="bg-blue-50 border-l-4 border-blue-400 p-3 mb-4">
    <p className="text-sm">
      <strong>Ashfield DCP:</strong> Heritage status drives requirements
    </p>
    <HeritageIndicator isHeritage={heritage} />
    <TopicFilter topics={...} />
  </div>
)}
```

### 3. Assessment Page Enhancement (`/assessment/page.tsx`)

Pass council to ProvisionsByTopic:

```typescript
// Extract council from property
const council = selectedProperty?.constraints?.formerCouncil?.toLowerCase() ||
                detectCouncilFromLGA(selectedProperty?.constraints?.lga);

<ProvisionsByTopic
  zone={selectedProperty?.constraints?.zone}
  heritage={selectedProperty?.heritage?.isHeritage}
  council={council}  // NEW
  devType={developmentType}
  assessmentType={assessmentType}
/>
```

### 4. Result Count Guidance

Add contextual guidance based on council:

```typescript
const COUNCIL_RESULT_GUIDANCE = {
  marrickville: {
    DA_expected: '200-400',
    CDC_expected: '15-30',
    warning_threshold: 500
  },
  leichhardt: {
    DA_expected: '50-100 (with topic filter)',
    DA_without_topic: '2,000+ (too many)',
    CDC_expected: '15-25',
    warning_threshold: 200
  },
  ashfield: {
    DA_expected: '300-500',
    CDC_expected: '1-5',
    warning_threshold: 600
  }
};

// In UI
{resultCount > guidance.warning_threshold && (
  <Alert variant="warning">
    {council === 'leichhardt'
      ? 'Select a topic to narrow results (currently 2,211)'
      : `Consider adding filters to reduce from ${resultCount} provisions`
    }
  </Alert>
)}
```

## Filter Behavior Matrix

| Filter | Marrickville | Leichhardt | Ashfield |
|--------|-------------|------------|----------|
| Zone | ✅ Primary | ❌ Skip/Hide | ❌ Skip/Hide |
| Topic | Optional | ✅ **MANDATORY** | Optional |
| Precinct | Useful | Secondary | Minor |
| Heritage | If applicable | Minor | ✅ Primary |
| Dev Type | Always | Always | Always |

## Expected Results After Implementation

| Scenario | Before | After |
|----------|--------|-------|
| Leichhardt dwelling DA | 2,211 (unusable) | 30-85 (with topic) |
| Leichhardt dwelling CDC | 21 | 21 (unchanged) |
| Marrickville R2 dwelling DA | 228 | 228 (unchanged) |
| Ashfield heritage dwelling DA | 394 | 394 + heritage highlighted |

## Files to Modify

1. `frontend-nextjs/app/api/provisions/for-property/route.ts` - Add council detection & guidance
2. `frontend-nextjs/components/compliance/ProvisionsByTopic.tsx` - Council-aware UI
3. `frontend-nextjs/app/assessment/page.tsx` - Pass council prop
4. `frontend-nextjs/lib/council-config.ts` (NEW) - Council-specific configuration

## Testing Checklist

- [ ] Leichhardt dwelling DA with topic filter returns 30-85
- [ ] Leichhardt dwelling DA without topic shows warning
- [ ] Marrickville R2 dwelling DA returns 200-250
- [ ] Ashfield heritage property shows condition layer prominently
- [ ] CDC queries work for all councils (< 30 results)
