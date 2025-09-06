# PRP-I: Technical Implementation Specification
## Systematic Engineering Roadmap for Phase 1 Frontend Integration

**Date**: 2025-09-03  
**Status**: ✅ READY FOR IMPLEMENTATION  
**Priority**: CRITICAL - ENGINEERING RELIABILITY & QUALITY ASSURANCE  
**Duration**: 3 weeks parallel with PRP-H implementation  

---

## 📋 **EXECUTIVE SUMMARY**

This PRP provides the technical implementation specification for Phase 1, ensuring systematic and reliable development of the precision setback calculator and intelligence features. It complements PRP-H (business strategy) with engineering requirements, testing procedures, and operational specifications.

---

## 🏗️ **SYSTEM ARCHITECTURE**

### **Next.js Full-Stack Architecture:**
```
┌─────────────────────────────────────────────────────────────────┐
│                    NEXT.JS APPLICATION                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   CLIENT COMPONENTS                         │ │
│  │  ┌──────────────┐  ┌─────────────┐  ┌─────────────────┐  │ │
│  │  │   Address    │→ │   Property  │→ │  Analysis Tabs: │  │ │
│  │  │  Search      │  │   Panel     │  │  - Explanations │  │ │
│  │  │  (Google)    │  │   Display   │  │  - Heritage     │  │ │
│  │  └──────────────┘  └─────────────┘  │  - Pathways     │  │ │
│  │                                       │  - Setbacks     │  │ │
│  │                                       └─────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                               │                                  │
│                               ↓ Server Actions / API Routes      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   SERVER COMPONENTS                         │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │           Next.js API Routes (app/api/)              │  │ │
│  │  │  /api/property/[address]  - Property intelligence    │  │ │
│  │  │  /api/setbacks/calculate  - Precise calculations     │  │ │
│  │  │  /api/compliance/explain  - Reasoning engine         │  │ │
│  │  │  /api/heritage/analyze    - Heritage assessment      │  │ │
│  │  │  /api/pathway/optimize    - Pathway recommendations  │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    ↓                      ↓
┌──────────────────────────┐  ┌───────────────────────────────┐
│   EXTERNAL SERVICES      │  │   PYTHON SERVICES (Optional)  │
├──────────────────────────┤  ├───────────────────────────────┤
│  NSW Planning API        │  │  DatabaseIntelligence         │
│  - Property lookup       │  │  - ComplianceExplainer       │
│  - Planning controls     │  │  - HeritageIntelligence      │
│  - Lot geometry          │  │  - PathwayOptimizer          │
│  Google Places API       │  │  - PreciseSetbackCalculator  │
└──────────────────────────┘  └───────────────────────────────┘
                                           │
                                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE (SQLite/PostgreSQL)                  │
├─────────────────────────────────────────────────────────────────┤
│  development_controls  │  kg_relationships  │  quantitative_    │
│  (4,526 records)       │  (2,734 records)   │  standards (829)  │
│  regulatory_provisions │  development_       │  sepp_lep_        │
│  (9,364 records)       │  pathways          │  overrides (91)   │
└─────────────────────────────────────────────────────────────────┘
```

### **Data Flow Specification:**
```python
# 1. Frontend Request Flow
UserInput → GooglePlaces → PropertyAddress → APIRequest

# 2. Backend Processing Flow
APIRequest → Validation → ServiceOrchestration → DatabaseQuery → ExternalAPI → ResponseAggregation

# 3. Intelligence Processing
DatabaseQuery → RulesEngine → ReasoningExtraction → ConfidenceScoring → ResultFormatting

# 4. Response Flow  
FormattedResult → JSONSerialization → HTTPResponse → FrontendRendering
```

---

## 🚀 **NEXT.JS IMPLEMENTATION ARCHITECTURE**

### **Project Structure:**
```
compliance-engine-frontend/
├── app/                              # Next.js 14 App Router
│   ├── (dashboard)/                  # Route group
│   │   ├── layout.tsx               # Dashboard layout
│   │   ├── page.tsx                 # Main dashboard page
│   │   └── property/[address]/      # Dynamic property routes
│   │       └── page.tsx
│   ├── api/                         # API Routes (Server-side)
│   │   ├── property/
│   │   │   └── [address]/route.ts   # Property intelligence
│   │   ├── setbacks/
│   │   │   └── calculate/route.ts   # Precise setback calculations
│   │   ├── compliance/
│   │   │   └── explain/route.ts     # Reasoning engine
│   │   ├── heritage/
│   │   │   └── analyze/route.ts     # Heritage assessment
│   │   └── pathway/
│   │       └── optimize/route.ts    # Pathway recommendations
│   ├── globals.css                  # Global styles
│   ├── layout.tsx                   # Root layout
│   └── page.tsx                     # Home page
├── components/                      # Reusable components
│   ├── ui/                         # Base UI components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── tabs.tsx
│   │   └── loading.tsx
│   ├── property/
│   │   ├── PropertySearch.tsx       # Google Places integration
│   │   ├── PropertyPanel.tsx        # Property info display
│   │   └── PropertyHeader.tsx       # Address header
│   ├── analysis/
│   │   ├── ComplianceExplanations.tsx
│   │   ├── HeritageIntelligence.tsx
│   │   ├── PathwayOptimizer.tsx
│   │   └── PreciseSetbackCalculator.tsx
│   └── dashboard/
│       ├── AnalysisTabs.tsx
│       └── ErrorBoundary.tsx
├── lib/                            # Utility functions
│   ├── api/                        # API client functions
│   │   ├── property.ts
│   │   ├── setbacks.ts
│   │   ├── compliance.ts
│   │   └── types.ts
│   ├── database/                   # Database utilities
│   │   ├── client.ts               # Database connection
│   │   └── queries.ts              # Query helpers
│   ├── geometry/                   # Geometry processing
│   │   ├── processor.ts
│   │   └── calculator.ts
│   └── utils.ts                    # General utilities
├── types/                          # TypeScript definitions
│   ├── property.ts
│   ├── setback.ts
│   ├── compliance.ts
│   └── database.ts
├── hooks/                          # Custom React hooks
│   ├── usePropertyData.ts
│   ├── useSetbackCalculation.ts
│   └── useGeometry.ts
├── styles/                         # Component styles
│   ├── globals.css
│   └── components.css
├── public/                         # Static assets
├── next.config.js                  # Next.js configuration
├── tailwind.config.js              # Tailwind CSS config
├── package.json
└── tsconfig.json
```

### **Key Component Implementations:**

#### **1. Main Dashboard Page:**
```typescript
// app/(dashboard)/page.tsx
'use client';

import { useState, useCallback } from 'react';
import { PropertySearch } from '@/components/property/PropertySearch';
import { PropertyPanel } from '@/components/property/PropertyPanel';
import { AnalysisTabs } from '@/components/dashboard/AnalysisTabs';
import { ErrorBoundary } from '@/components/dashboard/ErrorBoundary';
import { usePropertyData } from '@/hooks/usePropertyData';
import type { PropertyData } from '@/types/property';

export default function DashboardPage() {
  const [selectedAddress, setSelectedAddress] = useState<string>('');
  const { 
    property, 
    lotGeometry, 
    loading, 
    error, 
    analyzeProperty 
  } = usePropertyData();

  const handleAddressSelect = useCallback(async (address: string, coordinates?: google.maps.LatLngLiteral) => {
    setSelectedAddress(address);
    await analyzeProperty(address, coordinates);
  }, [analyzeProperty]);

  return (
    <ErrorBoundary error={error}>
      <div className="min-h-screen bg-gray-50">
        <div className="container mx-auto px-4 py-8">
          {/* Property Search */}
          <div className="mb-8">
            <PropertySearch 
              onAddressSelect={handleAddressSelect}
              loading={loading.property}
            />
          </div>

          {/* Main Content Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Property Information Panel */}
            <div className="lg:col-span-1">
              <PropertyPanel 
                property={property}
                loading={loading.property}
                error={error.property}
              />
            </div>

            {/* Analysis Tabs */}
            <div className="lg:col-span-3">
              <AnalysisTabs 
                property={property}
                lotGeometry={lotGeometry}
                loading={loading}
                error={error}
              />
            </div>
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}
```

#### **2. Precise Setback Calculator Component:**
```typescript
// components/analysis/PreciseSetbackCalculator.tsx
'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useSetbackCalculation } from '@/hooks/useSetbackCalculation';
import type { PropertyData, LotGeometry } from '@/types/property';
import type { SetbackResult } from '@/types/setback';

interface PreciseSetbackCalculatorProps {
  property: PropertyData | null;
  lotGeometry: LotGeometry | null;
  loading?: boolean;
}

export function PreciseSetbackCalculator({ 
  property, 
  lotGeometry, 
  loading 
}: PreciseSetbackCalculatorProps) {
  const { 
    results, 
    buildableArea, 
    calculating, 
    error, 
    calculateSetbacks 
  } = useSetbackCalculation();

  useEffect(() => {
    if (property?.prop_id && lotGeometry) {
      calculateSetbacks({
        property_id: property.prop_id,
        lot_geometry: lotGeometry,
        property_zone: property.zone,
        lot_area: calculateLotArea(lotGeometry)
      });
    }
  }, [property, lotGeometry, calculateSetbacks]);

  if (loading || calculating) {
    return <SetbackCalculatorSkeleton />;
  }

  if (error) {
    return <SetbackCalculatorError error={error} />;
  }

  if (!results || results.length === 0) {
    return <SetbackCalculatorEmpty />;
  }

  return (
    <div className="space-y-6">
      {/* Results Header */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            📐 Precise Setback Calculations
            <span className="text-sm font-normal text-green-600 bg-green-50 px-2 py-1 rounded">
              Precision: Centimeter
            </span>
          </CardTitle>
        </CardHeader>
      </Card>

      {/* Setback Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {results.map((result) => (
          <SetbackCard key={result.boundary_type} result={result} />
        ))}
      </div>

      {/* Buildable Area Summary */}
      {buildableArea && (
        <Card>
          <CardHeader>
            <CardTitle>🏗️ Buildable Area Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-2xl font-bold">{buildableArea.total_lot_area}m²</div>
                <div className="text-sm text-gray-600">Total Lot Area</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-green-600">
                  {buildableArea.buildable_area}m²
                </div>
                <div className="text-sm text-gray-600">Buildable Area</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-blue-600">
                  {buildableArea.buildable_percentage}%
                </div>
                <div className="text-sm text-gray-600">Buildable Percentage</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-red-600">
                  {buildableArea.setback_area_lost}m²
                </div>
                <div className="text-sm text-gray-600">Area Lost to Setbacks</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Disclaimer */}
      <div className="text-sm text-gray-500 bg-yellow-50 p-3 rounded border-l-4 border-yellow-200">
        ⚠️ Professional verification required for final design. 
        Calculations based on NSW Planning API geometry and database intelligence.
      </div>
    </div>
  );
}

// Sub-components
function SetbackCard({ result }: { result: SetbackResult }) {
  const boundaryTypeColors = {
    front: 'bg-blue-50 border-blue-200',
    rear: 'bg-green-50 border-green-200', 
    side_left: 'bg-purple-50 border-purple-200',
    side_right: 'bg-orange-50 border-orange-200'
  };

  return (
    <Card className={`${boundaryTypeColors[result.boundary_type as keyof typeof boundaryTypeColors]}`}>
      <CardContent className="p-4">
        <div className="text-center">
          <div className="text-lg font-semibold capitalize mb-2">
            {result.boundary_type.replace('_', ' ')}
          </div>
          <div className="text-3xl font-bold mb-1">
            {result.required_setback}m
          </div>
          <div className="text-sm text-gray-600 mb-3">
            Buildable: {result.buildable_depth}m
          </div>
          <div className="text-xs bg-white p-2 rounded border">
            <div className="font-medium mb-1">Reasoning:</div>
            <div>{result.reasoning}</div>
            <div className="mt-2 text-xs text-gray-500">
              Confidence: {Math.round(result.confidence * 100)}%
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

#### **3. API Route Implementation:**
```typescript
// app/api/setbacks/calculate/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { PreciseSetbackCalculator } from '@/lib/geometry/calculator';
import { DatabaseClient } from '@/lib/database/client';
import { SetbackCalculationRequest, SetbackCalculationResponse } from '@/types/api';

export async function POST(request: NextRequest) {
  try {
    const body: SetbackCalculationRequest = await request.json();
    
    // Validate input
    if (!body.property_id || !body.lot_geometry || !body.property_zone) {
      return NextResponse.json(
        { success: false, error: 'Missing required fields' },
        { status: 400 }
      );
    }

    // Initialize services
    const calculator = new PreciseSetbackCalculator();
    const startTime = Date.now();

    // Calculate setbacks
    const results = await calculator.calculate_precise_setbacks(
      body.lot_geometry,
      body.property_zone,
      body.lot_area
    );

    // Calculate buildable area
    const buildableArea = await calculator.calculate_total_buildable_area(
      body.lot_geometry,
      results
    );

    const processingTime = Date.now() - startTime;

    const response: SetbackCalculationResponse = {
      success: true,
      setback_results: results,
      buildable_area_analysis: buildableArea,
      precision_level: 'centimeter',
      processing_method: 'NSW Planning API geometry + Database intelligence',
      processing_time_ms: processingTime
    };

    return NextResponse.json(response);

  } catch (error) {
    console.error('Setback calculation error:', error);
    
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Calculation failed',
        processing_time_ms: 0
      },
      { status: 500 }
    );
  }
}
```

#### **4. Custom Hooks for State Management:**
```typescript
// hooks/useSetbackCalculation.ts
import { useState, useCallback } from 'react';
import { calculateSetbacks } from '@/lib/api/setbacks';
import type { SetbackCalculationRequest, SetbackResult, BuildableAreaAnalysis } from '@/types/setback';

export function useSetbackCalculation() {
  const [results, setResults] = useState<SetbackResult[]>([]);
  const [buildableArea, setBuildableArea] = useState<BuildableAreaAnalysis | null>(null);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calculate = useCallback(async (request: SetbackCalculationRequest) => {
    setCalculating(true);
    setError(null);

    try {
      const response = await calculateSetbacks(request);
      
      if (response.success) {
        setResults(response.setback_results);
        setBuildableArea(response.buildable_area_analysis);
      } else {
        throw new Error(response.error || 'Calculation failed');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      setResults([]);
      setBuildableArea(null);
    } finally {
      setCalculating(false);
    }
  }, []);

  return {
    results,
    buildableArea,
    calculating,
    error,
    calculateSetbacks: calculate
  };
}
```

#### **5. Database Integration Layer:**
```typescript
// lib/database/client.ts
import Database from 'better-sqlite3';
import type { 
  DevelopmentControl, 
  QuantitativeStandard, 
  KGRelationship 
} from '@/types/database';

export class DatabaseClient {
  private db: Database.Database;

  constructor(dbPath = 'nsw_planning.db') {
    this.db = new Database(dbPath);
    this.db.pragma('journal_mode = WAL'); // Performance optimization
  }

  getSetbackControls(zone: string): DevelopmentControl[] {
    const stmt = this.db.prepare(`
      SELECT dc.*, rpc.provision_text, rpc.document_id
      FROM development_controls dc
      JOIN regulatory_provisions_clean rpc ON dc.provision_id = rpc.id
      WHERE dc.control_type = 'setback'
      AND (dc.zone_applicable = ? OR dc.zone_applicable = 'general')
      ORDER BY dc.confidence_score DESC
      LIMIT 20
    `);
    
    return stmt.all(zone) as DevelopmentControl[];
  }

  getQuantitativeStandards(context: string): QuantitativeStandard[] {
    const stmt = this.db.prepare(`
      SELECT qs.*, rpc.provision_text
      FROM quantitative_standards qs
      JOIN regulatory_provisions_clean rpc ON qs.provision_id = rpc.id
      WHERE qs.context = ?
      AND qs.numeric_value IS NOT NULL
      ORDER BY qs.confidence_score DESC
      LIMIT 20
    `);
    
    return stmt.all(context) as QuantitativeStandard[];
  }

  getKGRelationships(predicate: string, subjectContains?: string): KGRelationship[] {
    let sql = `
      SELECT subject_text, predicate, object_text, confidence_score
      FROM kg_relationships
      WHERE predicate = ?
    `;
    
    const params = [predicate];
    
    if (subjectContains) {
      sql += ` AND subject_text LIKE ?`;
      params.push(`%${subjectContains}%`);
    }
    
    sql += ` ORDER BY confidence_score DESC LIMIT 10`;
    
    const stmt = this.db.prepare(sql);
    return stmt.all(...params) as KGRelationship[];
  }

  close() {
    this.db.close();
  }
}
```

### **Deployment Configuration:**

#### **Next.js Configuration:**
```javascript
// next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverActions: true,
    serverComponentsExternalPackages: ['better-sqlite3']
  },
  images: {
    domains: ['maps.googleapis.com']
  },
  env: {
    NSW_PLANNING_API_BASE_URL: process.env.NSW_PLANNING_API_BASE_URL,
    GOOGLE_PLACES_API_KEY: process.env.GOOGLE_PLACES_API_KEY,
    DATABASE_PATH: process.env.DATABASE_PATH || './nsw_planning.db'
  }
};

module.exports = nextConfig;
```

#### **Vercel Deployment:**
```json
// vercel.json
{
  "functions": {
    "app/api/**/route.ts": {
      "maxDuration": 30
    }
  },
  "env": {
    "NSW_PLANNING_API_BASE_URL": "@nsw_api_url",
    "GOOGLE_PLACES_API_KEY": "@google_places_key",
    "DATABASE_PATH": "./nsw_planning.db"
  }
}
```

---

## 🔌 **API SPECIFICATIONS**

### **1. Property Intelligence Endpoint**
```python
# GET /property-intelligence
class PropertyIntelligenceRequest(BaseModel):
    address: str = Field(..., min_length=5, max_length=200)
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lng: Optional[float] = Field(None, ge=-180, le=180)

class PropertyIntelligenceResponse(BaseModel):
    success: bool
    prop_id: Optional[int]
    zone: Optional[str]
    height_limit: Optional[float]
    fsr_limit: Optional[float]
    heritage_status: Optional[str]
    lga_name: Optional[str]
    applicable_lep: Optional[str]
    error: Optional[str] = None
```

### **2. Precise Setbacks Endpoint**
```python
# POST /precise-setbacks
class SetbackCalculationRequest(BaseModel):
    property_id: int = Field(..., gt=0)
    lot_geometry: Dict[str, Any] = Field(...)  # NSW API geometry format
    property_zone: str = Field(..., pattern="^[A-Z0-9]+$")
    lot_area: float = Field(..., gt=0)

class PreciseSetbackResult(BaseModel):
    boundary_type: Literal['front', 'rear', 'side_left', 'side_right']
    required_setback: float = Field(..., ge=0, description="Meters to 2 decimal places")
    buildable_depth: float = Field(..., ge=0)
    reasoning: str
    confidence: float = Field(..., ge=0, le=1)
    database_source: str
    precision_level: Literal['centimeter', 'meter', 'approximate']

class SetbackCalculationResponse(BaseModel):
    success: bool
    setback_results: List[PreciseSetbackResult]
    buildable_area_analysis: Dict[str, float]
    precision_level: str
    processing_method: str
    processing_time_ms: int
    error: Optional[str] = None
```

### **3. Compliance Explanations Endpoint**
```python
# POST /compliance-explanations  
class ExplanationRequest(BaseModel):
    requirement_type: Literal['height', 'fsr', 'setback', 'heritage', 'vegetation']
    property_context: Optional[Dict[str, Any]] = None

class ExplanationResponse(BaseModel):
    success: bool
    why_exists: str
    what_protects: str
    confidence: Literal['HIGH', 'MEDIUM', 'LOW']
    source_count: int
    database_relationships_used: List[str]
    error: Optional[str] = None
```

### **4. Heritage Intelligence Endpoint**
```python
# POST /heritage-intelligence
class HeritageRequest(BaseModel):
    property_id: int
    zone: str
    heritage_overlays: Optional[List[str]] = []

class HeritageResponse(BaseModel):
    success: bool
    heritage_status: str
    applicable_controls: int
    key_protections: List[str]
    controls_detail: List[Dict[str, Any]]
    confidence_assessment: str
    error: Optional[str] = None
```

---

## 🧪 **TESTING SPECIFICATIONS**

### **Unit Test Requirements:**

#### **1. Geometry Processing Tests**
```python
# tests/test_geometry_processor.py
class TestGeometryProcessor:
    def test_web_mercator_conversion(self):
        """Test Web Mercator to real-world meter conversion"""
        processor = GeometryProcessor()
        test_geometry = {
            'rings': [[[16826682.56, -4012906.53], ...]],
            'spatialReference': {'wkid': 3857}
        }
        boundaries = processor.api_geometry_to_boundaries(test_geometry)
        
        assert len(boundaries) == 4  # Rectangular lot
        assert 40 < boundaries[0].length < 70  # Realistic dimensions
        assert boundaries[0].boundary_type in ['front', 'rear', 'side_left', 'side_right']
    
    def test_boundary_classification(self):
        """Test correct classification of lot boundaries"""
        # Test rectangular lot
        # Test irregular lot
        # Test corner lot
        pass
    
    def test_precision_accuracy(self):
        """Verify centimeter-level precision is maintained"""
        # Test rounding to 2 decimal places
        # Test cumulative error < 0.01m
        pass
```

#### **2. Database Intelligence Tests**
```python
# tests/test_database_intelligence.py
class TestDatabaseIntelligence:
    def test_setback_rule_extraction(self):
        """Test extraction of setback rules from database"""
        db = DatabaseSetbackRules('test_db.sqlite')
        rules = db.get_setback_requirements('R2', 450.0)
        
        assert len(rules) > 0
        assert all(r.distance > 0 for r in rules)
        assert all(r.confidence >= 0 and r.confidence <= 1 for r in rules)
    
    def test_reasoning_extraction(self):
        """Test extraction of 'because' relationships"""
        explainer = ComplianceExplainer()
        result = explainer.explain_requirement('height')
        
        assert result['why_exists'] is not None
        assert result['source_count'] > 0
        assert result['confidence'] in ['HIGH', 'MEDIUM', 'LOW']
    
    def test_heritage_control_query(self):
        """Test heritage control database queries"""
        # Test with heritage overlay
        # Test without heritage overlay
        pass
```

### **Integration Test Requirements:**

#### **1. End-to-End Property Analysis**
```python
# tests/test_integration.py
class TestPropertyAnalysisFlow:
    @pytest.mark.asyncio
    async def test_complete_property_analysis(self):
        """Test complete flow from address to setback calculations"""
        # Step 1: Address to property ID
        prop_response = await client.get(
            "/property-intelligence",
            params={"address": "15 Norton Street, Leichhardt NSW 2040"}
        )
        assert prop_response.status_code == 200
        prop_data = prop_response.json()
        
        # Step 2: Get lot geometry
        # Step 3: Calculate precise setbacks
        setback_response = await client.post(
            "/precise-setbacks",
            json={
                "property_id": prop_data["prop_id"],
                "lot_geometry": prop_data["lot_geometry"],
                "property_zone": prop_data["zone"],
                "lot_area": 450.0
            }
        )
        assert setback_response.status_code == 200
        setback_data = setback_response.json()
        
        # Verify precision
        assert all(
            len(str(r["required_setback"]).split('.')[-1]) <= 2
            for r in setback_data["setback_results"]
        )
```

#### **2. Performance Tests**
```python
class TestPerformance:
    def test_setback_calculation_speed(self):
        """Ensure setback calculations complete within 2 seconds"""
        start_time = time.time()
        result = calculator.calculate_precise_setbacks(test_geometry, 'R2', 450)
        elapsed = time.time() - start_time
        
        assert elapsed < 2.0  # Must complete in 2 seconds
        assert len(result) > 0
    
    def test_concurrent_requests(self):
        """Test system handles 10 concurrent requests"""
        # Simulate 10 concurrent API calls
        # Verify all complete successfully
        # Check no database locks or timeouts
        pass
```

---

## 🚨 **ERROR HANDLING & RESILIENCE**

### **External Service Failures:**
```python
class NSWAPIErrorHandler:
    def handle_api_failure(self, error: Exception) -> Dict:
        """Graceful degradation when NSW Planning API is unavailable"""
        
        if isinstance(error, TimeoutError):
            return {
                'fallback_mode': True,
                'message': 'NSW Planning API timeout - using cached data',
                'cache_age_minutes': self.get_cache_age()
            }
        
        elif isinstance(error, HTTPError) and error.status_code == 429:
            return {
                'rate_limited': True,
                'retry_after': error.headers.get('Retry-After', 60),
                'message': 'Rate limited - please retry later'
            }
        
        else:
            logger.error(f"NSW API error: {error}")
            return {
                'error': True,
                'message': 'Planning data temporarily unavailable',
                'support_contact': 'support@complianceengine.com.au'
            }
```

### **Database Query Optimization:**
```python
class DatabaseQueryOptimizer:
    def optimize_setback_query(self, zone: str) -> str:
        """Use indexed queries for performance"""
        
        # Use prepared statements
        query = """
        SELECT /*+ INDEX(dc idx_control_type_zone) */
               dc.*, rpc.provision_text
        FROM development_controls dc
        JOIN regulatory_provisions_clean rpc ON dc.provision_id = rpc.id
        WHERE dc.control_type = ? 
        AND (dc.zone_applicable = ? OR dc.zone_applicable = 'general')
        ORDER BY dc.confidence_score DESC
        LIMIT 20
        """
        
        return query
    
    def implement_query_caching(self):
        """Cache frequently accessed queries"""
        # Cache zone-specific setback rules for 1 hour
        # Cache 'because' relationships for 24 hours
        # Cache heritage controls for 12 hours
        pass
```

### **Input Validation:**
```python
class InputValidator:
    def validate_geometry(self, geometry: Dict) -> bool:
        """Validate NSW API geometry structure"""
        
        if not geometry or 'rings' not in geometry:
            raise ValueError("Invalid geometry: missing rings")
        
        rings = geometry.get('rings', [])
        if not rings or len(rings[0]) < 4:
            raise ValueError("Invalid geometry: insufficient points")
        
        # Validate coordinate ranges (Web Mercator bounds)
        for ring in rings:
            for coord in ring:
                if not (-20037508 <= coord[0] <= 20037508):
                    raise ValueError(f"Invalid X coordinate: {coord[0]}")
                if not (-20037508 <= coord[1] <= 20037508):
                    raise ValueError(f"Invalid Y coordinate: {coord[1]}")
        
        return True
    
    def sanitize_address(self, address: str) -> str:
        """Sanitize address input for security"""
        # Remove SQL injection attempts
        # Normalize whitespace
        # Validate NSW address format
        pass
```

---

## 📊 **MONITORING & OBSERVABILITY**

### **Application Metrics:**
```python
# metrics.py
class MetricsCollector:
    def __init__(self):
        self.metrics = {
            'api_calls': Counter('api_calls_total', 'Total API calls', ['endpoint']),
            'response_time': Histogram('response_time_seconds', 'Response time', ['endpoint']),
            'error_rate': Counter('errors_total', 'Total errors', ['type']),
            'cache_hits': Counter('cache_hits_total', 'Cache hit rate', ['cache_type'])
        }
    
    def record_api_call(self, endpoint: str, duration: float, success: bool):
        self.metrics['api_calls'].labels(endpoint=endpoint).inc()
        self.metrics['response_time'].labels(endpoint=endpoint).observe(duration)
        if not success:
            self.metrics['error_rate'].labels(type='api_error').inc()
```

### **Logging Standards:**
```python
# logging_config.py
LOGGING_CONFIG = {
    'version': 1,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]'
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/compliance_engine.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'detailed'
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/errors.log',
            'maxBytes': 10485760,
            'backupCount': 5,
            'formatter': 'detailed',
            'level': 'ERROR'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file', 'error_file']
    }
}
```

### **Performance Benchmarks:**
```python
# performance_benchmarks.py
PERFORMANCE_REQUIREMENTS = {
    'api_response_time': {
        'property_intelligence': 1000,  # ms
        'precise_setbacks': 2000,       # ms
        'compliance_explanations': 500,  # ms
        'heritage_intelligence': 1000,   # ms
    },
    'database_query_time': {
        'single_table': 100,    # ms
        'join_query': 500,      # ms
        'complex_join': 1000,   # ms
    },
    'concurrent_users': 100,
    'requests_per_second': 50,
    'error_rate_threshold': 0.01  # 1%
}
```

---

## 🚀 **DEPLOYMENT PROCEDURES**

### **Environment Configuration:**
```bash
# .env.production
# API Configuration
API_HOST=0.0.0.0
API_PORT=8006
API_WORKERS=4

# Database Configuration  
DATABASE_PATH=/app/data/nsw_planning.db
DATABASE_POOL_SIZE=20
DATABASE_TIMEOUT=30

# NSW Planning API
NSW_API_BASE_URL=https://api.apps1.nsw.gov.au/planning
NSW_API_TIMEOUT=10
NSW_API_RETRY_COUNT=3

# Google Places API
GOOGLE_PLACES_API_KEY=${GOOGLE_PLACES_API_KEY}

# Cache Configuration
REDIS_URL=redis://localhost:6379
CACHE_TTL_SECONDS=3600

# Monitoring
SENTRY_DSN=${SENTRY_DSN}
LOG_LEVEL=INFO
```

### **Database Migration:**
```python
# migrations/001_add_indexes.py
def upgrade():
    """Add performance indexes for Phase 1"""
    
    migrations = [
        "CREATE INDEX idx_dc_control_zone ON development_controls(control_type, zone_applicable);",
        "CREATE INDEX idx_qs_context ON quantitative_standards(context, numeric_value);",
        "CREATE INDEX idx_kg_predicate ON kg_relationships(predicate, subject_text);",
        "CREATE INDEX idx_rpc_document ON regulatory_provisions_clean(document_id, provision_text);"
    ]
    
    for migration in migrations:
        execute(migration)

def downgrade():
    """Remove indexes"""
    pass
```

### **Health Check Endpoints:**
```python
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy"}

@app.get("/health/detailed")
async def detailed_health():
    """Detailed health with dependency checks"""
    
    checks = {
        'database': check_database_connection(),
        'nsw_api': check_nsw_api_availability(),
        'cache': check_cache_connection(),
        'disk_space': check_disk_space(),
        'memory_usage': check_memory_usage()
    }
    
    overall_health = all(checks.values())
    
    return {
        'status': 'healthy' if overall_health else 'degraded',
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat()
    }
```

---

## 🔒 **SECURITY SPECIFICATIONS**

### **API Security:**
```python
# security.py
class SecurityMiddleware:
    def __init__(self, app):
        self.app = app
        self.rate_limiter = RateLimiter(
            requests_per_minute=60,
            requests_per_hour=1000
        )
    
    async def __call__(self, scope, receive, send):
        # Rate limiting
        client_ip = self.get_client_ip(scope)
        if not self.rate_limiter.allow_request(client_ip):
            await self.send_rate_limit_response(send)
            return
        
        # Input sanitization
        if scope['type'] == 'http':
            scope = self.sanitize_request(scope)
        
        # CORS headers
        if scope['path'].startswith('/api'):
            scope = self.add_cors_headers(scope)
        
        await self.app(scope, receive, send)
```

### **Data Protection:**
```python
class DataProtection:
    def anonymize_logs(self, log_entry: Dict) -> Dict:
        """Remove PII from logs"""
        # Remove specific addresses
        # Hash property IDs
        # Remove personal identifiers
        pass
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive database fields"""
        # Use AES-256 encryption
        # Rotate keys quarterly
        pass
```

---

## 📈 **SUCCESS CRITERIA**

### **Technical Metrics:**
- ✅ All API endpoints respond within specified time limits
- ✅ Setback calculations achieve centimeter precision (0.01m)
- ✅ Database queries optimized with appropriate indexes
- ✅ 95%+ test coverage for critical paths
- ✅ Zero critical security vulnerabilities

### **Operational Metrics:**
- ✅ 99.9% uptime during business hours
- ✅ <1% error rate under normal load
- ✅ Handles 100 concurrent users
- ✅ Automated deployment pipeline functional
- ✅ Monitoring and alerting operational

### **Quality Gates:**
```python
# quality_gates.py
QUALITY_GATES = {
    'code_coverage': 85,        # Minimum test coverage %
    'cyclomatic_complexity': 10, # Maximum complexity per function
    'duplication': 5,            # Maximum duplication %
    'security_issues': 0,        # Critical security issues
    'performance_regression': 10 # Maximum % performance regression
}
```

---

## 🔄 **CONTINUOUS IMPROVEMENT**

### **Post-Launch Monitoring:**
- Daily error rate analysis
- Weekly performance review
- Monthly security audit
- Quarterly dependency updates

### **Optimization Opportunities:**
- Query performance tuning based on usage patterns
- Cache strategy refinement
- API response payload optimization
- Database index optimization

---

---

## 📁 **IMPLEMENTED FILE STRUCTURE - OPERATIONAL DEPLOYMENT**

### **✅ HIERARCHICAL COMPLIANCE ENGINE (CORE)**
```
frontend-nextjs/lib/compliance/
├── inner-west-engine.ts                 # Main compliance engine with domain rules
├── sepp-lep-processor.ts               # NSW legal hierarchy processor (SEPP > LEP > DCP)
└── kg-zone-extractor.ts                # Knowledge graph zone extraction

frontend-nextjs/lib/database/
├── client.ts                           # SQLite database client
├── postgres-client.ts                  # PostgreSQL hierarchical queries  
└── queries.ts                          # Database query helpers
```

### **✅ API ENDPOINTS (OPERATIONAL ON PORT 3007)**
```
frontend-nextjs/app/api/
├── property/[address]/route.ts         # Property intelligence endpoint
├── setbacks/calculate/route.ts         # Precise setback calculation API
└── compliance/assess/route.ts          # Hierarchical compliance assessment

Backend Integration:
├── inner_west_compliance_engine.py    # Python compliance engine bridge
└── dynamic_setback_calc.py            # Dynamic setback calculator
```

### **✅ FRONTEND COMPONENTS (DEPLOYED)**
```
frontend-nextjs/components/
├── property/PropertySearch.tsx         # Google Places address search
├── property/PropertyPanel.tsx          # Property information display  
├── dashboard/AnalysisTabs.tsx         # Analysis interface
└── ui/                                # Base UI components (button, card, tabs)

frontend-nextjs/hooks/
├── usePropertyData.ts                 # Property data state management
├── useSetbackCalculation.ts           # Setback calculation hooks
└── useGeometry.ts                     # Geometry processing hooks
```

### **✅ DATABASE INTELLIGENCE (ACTIVE)**
```
Database Files:
├── nsw_planning.db                    # Main compliance database
├── nsw_planning_backup_*.db          # Automated backups

Tables (Verified Active):
├── development_controls               # 4,526 setback controls
├── regulatory_provisions_clean        # 9,364 provisions  
├── kg_relationships                   # 2,734 knowledge graph relationships
├── quantitative_standards            # 829 numeric standards
└── sepp_lep_overrides               # 91 hierarchical overrides
```

### **✅ PYTHON BACKEND SERVICES (OPERATIONAL)**
```
Root Directory Services:
├── services/precise_setback_calculator.py      # Centimeter-precision calculations
├── services/full_clause_extractor.py          # Clause extraction service
├── services/integrated_multimodal_query.py    # Multimodal query processor
└── services/database_autoschema_query.py      # Database schema queries

Active Scripts:
├── simple_property_requirements.py            # Simple property analysis
├── database_setback_calculator.py            # Database setback calculations  
└── zone_compliance_mapper.py                 # Zone compliance mapping
```

### **✅ LEGAL AUTHORITY HIERARCHY (IMPLEMENTED)**
```
NSW Planning Law Precedence:
1. SEPP (State Environmental Planning Policy) - Precedence Level 1
2. LEP (Local Environmental Plan) - Precedence Level 2  
3. DCP (Development Control Plan) - Precedence Level 3+

Domain Classification System:
├── RESIDENTIAL_BUILDINGS               # Primary domain filter
├── Cross-contamination prevention      # Excludes signage/advertising
└── Legal precedence scoring           # 1=highest authority, 4=lowest
```

### **🚀 DEPLOYMENT STATUS: OPERATIONAL**
- **Server**: NextJS on port 3007 ✅ RUNNING
- **API Endpoints**: All functional ✅ TESTED  
- **Database**: SQLite + PostgreSQL ✅ ACTIVE
- **Python Services**: Compliance engine ✅ INTEGRATED
- **Google Maps**: Places API ✅ WORKING
- **Legal Hierarchy**: SEPP>LEP>DCP ✅ ENFORCED

---

**This Technical Implementation Specification ensures systematic, reliable, and maintainable development of Phase 1 features. It provides the engineering foundation for delivering professional-grade precision tools with confidence.**

**Implementation approach: Test-driven, monitored, secure**  
**Quality assurance: Comprehensive testing at all levels**  
**Operational readiness: Production-grade from day one**