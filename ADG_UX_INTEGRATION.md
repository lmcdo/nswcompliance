# ADG Standards - Exact UX Integration Flow

## Current Page Layout

```
┌────────────────────────────────────────────────────────────────────────────┐
│ NSW Planning Assessment                                                    │
│ Professional compliance assessment using real-time planning data           │
├────────────────────────────────────────────────────────────────────────────┤
│ [Address Search Bar]                                                       │
├──────────────────┬─────────────────────────────────────────────────────────┤
│ LEFT COLUMN      │ RIGHT COLUMN                                            │
│ (1/4 width)      │ (3/4 width)                                             │
│                  │                                                         │
│ ┌──────────────┐ │ ┌─────────────────────────────────────────────────────┐ │
│ │ Property Info│ │ │ ComplianceDashboard                                 │ │
│ │              │ │ │                                                     │ │
│ │ Address      │ │ │ 🟥 SEPP Special Provisions (cards with "View      │ │
│ │ Zone: R2     │ │ │    Full Text" buttons)                             │ │
│ │ Area: 405m²  │ │ │                                                     │ │
│ │ LGA: Inner W │ │ │ 🟦 LEP Building Envelope (Height, FSR)            │ │
│ │ Heritage: No │ │ │                                                     │ │
│ │              │ │ │ 🟢 DCP Design Controls (setbacks, provisions)     │ │
│ │ [Dev Type ▼] │ │ │                                                     │ │
│ │  Dwelling    │ │ │ 🟤 Environmental Constraints                       │ │
│ │  Multi-dwell │ │ └─────────────────────────────────────────────────────┘ │
│ │  Apartment   │ │                                                         │
│ └──────────────┘ │                                                         │
│                  │                                                         │
│ ┌──────────────┐ │                                                         │
│ │Planning API  │ │                                                         │
│ │Data (all 15  │ │                                                         │
│ │layers)       │ │                                                         │
│ └──────────────┘ │                                                         │
└──────────────────┴─────────────────────────────────────────────────────────┘
```

## Where ADG Fits - RIGHT COLUMN Integration

### Current Right Column Structure (ComplianceDashboard.tsx):

```typescript
<div className="space-y-6">
  {/* 1. Property Header Card */}
  <Card>Property Compliance: {address}</Card>

  {/* 2. SEPP Special Provisions (🟥 Red) */}
  <Card className="border-red-200 bg-red-50">
    <CardHeader>🟥 SEPP Special Provisions</CardHeader>
    {/* SEPP provisions from Planning API + Database */}
  </Card>

  {/* 3. LEP Building Envelope (🟦 Blue) */}
  <Card className="border-blue-200">
    <CardHeader>🟦 LEP Building Envelope</CardHeader>
    {/* Height, FSR from Planning API */}
  </Card>

  {/* 4. DCP Design Controls (🟢 Green) */}
  <Card className="border-green-200">
    <CardHeader>🟢 DCP Design Controls</CardHeader>
    {/* Setbacks, design guidelines from Database */}
  </Card>

  {/* 5. Environmental Constraints (🟤 Brown) */}
  <Card className="border-amber-200">
    <CardHeader>🟤 Environmental Constraints</CardHeader>
    {/* Flooding, biodiversity, etc. */}
  </Card>
</div>
```

### PROPOSED: Add ADG Card BEFORE DCP (When Applicable)

```typescript
<div className="space-y-6">
  {/* 1. Property Header Card */}
  <Card>Property Compliance: {address}</Card>

  {/* 2. SEPP Special Provisions (🟥 Red) */}
  <Card className="border-red-200 bg-red-50">...</Card>

  {/* ⭐ NEW: 2.5. ADG Building Separation (🟥 Red - STATUTORY) */}
  {shouldShowADG && (
    <Card className="border-red-200 bg-red-50">
      <CardHeader>
        <div className="flex items-center gap-2">
          <CardTitle>🟥 Building Separation Standards (Multi-Storey)</CardTitle>
          <Badge variant="destructive">STATUTORY</Badge>
        </div>
        <CardDescription>
          NSW Apartment Design Guide Section 3F-1 - SEPP (Housing) 2021
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ADGBuildingSeparationTable
          buildingHeight={buildingHeight}
          developmentType={developmentType}
        />
      </CardContent>
    </Card>
  )}

  {/* 3. LEP Building Envelope (🟦 Blue) */}
  <Card className="border-blue-200">...</Card>

  {/* 4. DCP Design Controls (🟢 Green) */}
  <Card className="border-green-200">
    {/* Include note: "For upper floors of multi-dwelling, see ADG above" */}
  </Card>

  {/* 5. Environmental Constraints (🟤 Brown) */}
  <Card className="border-amber-200">...</Card>
</div>
```

## Trigger Logic - When to Show ADG

### In ComplianceDashboard.tsx (Add this logic):

```typescript
// Near top of component
const [adgStandards, setAdgStandards] = useState<any>(null);
const [buildingHeight, setBuildingHeight] = useState<number | null>(null);

// Determine if ADG applies
const shouldShowADG = useMemo(() => {
  const adgApplicableTypes = [
    'multi_dwelling',
    'residential_flat',
    'shop_top_housing'
  ];

  return adgApplicableTypes.includes(developmentType);
}, [developmentType]);

// Fetch ADG standards when applicable
useEffect(() => {
  if (!shouldShowADG) {
    setAdgStandards(null);
    return;
  }

  // If building height not provided, prompt user or skip
  if (!buildingHeight) {
    console.log('[ComplianceDashboard] ADG applies but building height not provided');
    // Could show a prompt: "Enter building height to see ADG standards"
    return;
  }

  // Fetch ADG standards
  const fetchADG = async () => {
    try {
      const response = await fetch(
        `/api/setbacks/adg?building_height=${buildingHeight}&development_type=${developmentType}`
      );
      const data = await response.json();

      if (data.applies) {
        setAdgStandards(data);
      }
    } catch (error) {
      console.error('[ComplianceDashboard] Failed to fetch ADG standards:', error);
    }
  };

  fetchADG();
}, [shouldShowADG, buildingHeight, developmentType]);
```

## Building Height Input - Where to Add It

### Option 1: Left Column Property Card (RECOMMENDED)

Add building height input AFTER development type selector:

```typescript
{/* In page.tsx, Left Column Property Info Card */}
<div className="border-t pt-3">
  <label className="text-sm text-gray-600 block mb-2">Development Type</label>
  <select value={developmentType} onChange={(e) => setDevelopmentType(e.target.value)}>
    <option value="dwelling_house">Dwelling House</option>
    <option value="multi_dwelling">Multi Dwelling Housing</option>
    {/* ... */}
  </select>
</div>

{/* ⭐ NEW: Building Height Input (conditionally shown) */}
{(developmentType === 'multi_dwelling' ||
  developmentType === 'residential_flat' ||
  developmentType === 'shop_top_housing') && (
  <div className="border-t pt-3">
    <label className="text-sm text-gray-600 block mb-2">
      Building Height (meters)
      <span className="text-red-500 ml-1">*</span>
    </label>
    <input
      type="number"
      step="0.1"
      min="0"
      max="100"
      value={buildingHeight || ''}
      onChange={(e) => setBuildingHeight(parseFloat(e.target.value) || null)}
      className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      placeholder="e.g., 10.5"
    />
    <p className="text-xs text-gray-500 mt-1">
      Required for ADG building separation standards
    </p>
  </div>
)}
```

### Option 2: Inline Prompt in Right Column

If building height not provided, show prompt instead of full table:

```typescript
{shouldShowADG && !buildingHeight && (
  <Card className="border-yellow-200 bg-yellow-50">
    <CardHeader>
      <CardTitle className="text-sm">ℹ️ Building Height Required</CardTitle>
    </CardHeader>
    <CardContent>
      <p className="text-sm">
        Multi-dwelling developments must comply with NSW Apartment Design Guide
        building separation standards. Enter building height in the property
        panel to see applicable setbacks.
      </p>
    </CardContent>
  </Card>
)}
```

## Complete UX Flow

### User Journey:

1. **User enters address**: "40 Lackey Street, Summer Hill 2130"
2. **Planning API loads**: Left column shows zone, LGA, etc.
3. **User selects dev type**: Changes dropdown to "Multi Dwelling Housing"
4. **Building height input appears**: Left column shows new input field
5. **User enters height**: Types "10" (meters)
6. **ADG card appears**: Right column shows red STATUTORY card with:
   - "Building Height: Up to 12m (4 storeys)"
   - Table: Side habitable 6.0m, non-habitable 3.0m
   - Source citation with PDF link
7. **DCP card updated**: Shows note "For upper floors, see ADG above"

### Visual Flow Diagram:

```
User Action                     Left Column                Right Column
───────────────────────────────────────────────────────────────────────────
1. Enter address           →    Property Info loaded   →  [Loading...]
                                Zone: R2
                                Dev Type: [Dwelling ▼]

2. Change dev type to      →    Dev Type: [Multi-dwell ▼]  [SEPP cards]
   "Multi-dwelling"             ⭐ NEW INPUT APPEARS:      [LEP cards]
                                Building Height: [    ]    [DCP cards]

3. Enter height "10"       →    Building Height: [10  ]  → ⭐ NEW CARD:
                                                            🟥 ADG 3F-1
                                                            6.0m / 3.0m
                                                            [SEPP cards]
                                                            [LEP cards]
                                                            [DCP cards]
                                                            ↓ note added:
                                                            "Upper floors:
                                                             see ADG above"
```

## ADG Component Structure

### New Component: `ADGBuildingSeparationTable.tsx`

```typescript
interface ADGBuildingSeparationTableProps {
  buildingHeight: number;
  developmentType: string;
}

export function ADGBuildingSeparationTable({
  buildingHeight,
  developmentType
}: ADGBuildingSeparationTableProps) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch from /api/setbacks/adg
  }, [buildingHeight, developmentType]);

  if (loading) return <div>Loading ADG standards...</div>;
  if (!data?.applies) return null;

  return (
    <div className="space-y-4">
      {/* Alert: Statutory requirement */}
      <Alert>
        <Info className="h-4 w-4" />
        <AlertTitle>Statutory Requirement</AlertTitle>
        <AlertDescription>
          Mandatory under SEPP (Housing) 2021. Not discretionary.
        </AlertDescription>
      </Alert>

      {/* Building height category */}
      <div className="bg-white border rounded p-3">
        <p className="text-sm font-medium">
          Building Height Category: {data.height_category}
        </p>
        <p className="text-xs text-gray-600">
          ({data.storey_range})
        </p>
      </div>

      {/* Setbacks table */}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Boundary</TableHead>
            <TableHead>Room Type</TableHead>
            <TableHead>Minimum Setback</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>Side</TableCell>
            <TableCell>Habitable rooms & balconies</TableCell>
            <TableCell className="font-bold text-red-700">
              {data.setbacks.side.habitable_rooms_and_balconies}m
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell>Side</TableCell>
            <TableCell>Non-habitable (bathrooms, etc.)</TableCell>
            <TableCell>{data.setbacks.side.non_habitable_rooms}m</TableCell>
          </TableRow>
          {/* Rear rows */}
        </TableBody>
      </Table>

      {/* Additional requirements (collapsible) */}
      <Collapsible>
        <CollapsibleTrigger>
          <ChevronDown className="h-4 w-4" />
          Additional Requirements
        </CollapsibleTrigger>
        <CollapsibleContent>
          {data.additional_requirements.map((req, i) => (
            <p key={i} className="text-sm text-gray-600">• {req}</p>
          ))}
        </CollapsibleContent>
      </Collapsible>

      {/* Source citation */}
      <div className="border-t pt-3 text-xs text-gray-600">
        <p><strong>Source:</strong> {data.source.document}</p>
        <p><strong>Section:</strong> {data.source.section}</p>
        <p><strong>Authority:</strong> {data.source.authority}</p>
        <p>
          <a
            href={data.source.url}
            target="_blank"
            className="text-blue-600 underline"
          >
            View PDF (Page {data.source.page})
          </a>
        </p>
      </div>
    </div>
  );
}
```

## Summary: Complete Integration Points

### Files to Modify:

1. **`frontend-nextjs/app/assessment/page.tsx`**
   - Add `buildingHeight` state
   - Add building height input (conditional on dev type)
   - Pass `buildingHeight` to ComplianceDashboard

2. **`frontend-nextjs/components/compliance/ComplianceDashboard.tsx`**
   - Add ADG fetch logic
   - Add `shouldShowADG` computed property
   - Insert ADG card before DCP section
   - Add note to DCP: "Upper floors see ADG above"

3. **`frontend-nextjs/components/compliance/ADGBuildingSeparationTable.tsx`** (NEW)
   - Fetch from `/api/setbacks/adg`
   - Display table with proper styling
   - Show source citations
   - Handle loading/error states

### Visual Hierarchy (Right Column Order):

```
🟥 Priority 1: SEPP Special Provisions (Planning API SEPPs)
🟥 Priority 1: ADG Building Separation (STATUTORY - when applicable)
🟦 Priority 2: LEP Building Envelope (Height, FSR)
🟢 Priority 3: DCP Design Controls (Setbacks - with ADG note)
🟤 Priority 4: Environmental Constraints
```

### Key UX Principles:

✅ **Conditional Display**: ADG only shows for multi-dwelling/apartments
✅ **Clear Visual Priority**: Red border + "STATUTORY" badge
✅ **User Input Required**: Building height input in left column
✅ **Seamless Integration**: Fits into existing card layout
✅ **Source Transparency**: Full citation with clickable PDF link
✅ **Professional Workflow**: Matches DA assessment order (SEPP → LEP → DCP)

This ensures ADG standards integrate naturally into the existing 2-column layout without disrupting current UX!
