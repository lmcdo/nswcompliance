#!/bin/bash
# PRP-M3: UI State Management Bridge
# Connects new UI components to existing state management and APIs

set -e  # Exit on error

echo "🚀 Executing PRP-M3: UI State Management Bridge"
echo "================================================"

# Navigate to project root
cd "$(dirname "$0")/../.."
PROJECT_ROOT=$(pwd)
echo "📁 Project root: $PROJECT_ROOT"

# Step 1: Create state management bridge
echo ""
echo "Step 1: Creating state management bridge..."
echo "------------------------------------------"

mkdir -p hooks/new-ui

cat > hooks/new-ui/usePropertyData.ts << 'EOF'
import { useState, useEffect } from 'react'
import useSWR from 'swr'

interface PropertyData {
  propId?: number
  address: string
  zone?: string
  lga?: string
  area?: string
  lot?: string
  dpNumber?: string
  lat?: number
  lng?: number
  landValue?: string
  heritage?: boolean
}

interface UsePropertyDataReturn {
  property: PropertyData | null
  isLoading: boolean
  error: string | null
  setProperty: (property: PropertyData) => void
  refreshProperty: () => void
}

const fetcher = (url: string) => fetch(url).then(res => res.json())

export function usePropertyData(initialAddress?: string): UsePropertyDataReturn {
  const [property, setPropertyState] = useState<PropertyData | null>(
    initialAddress ? { address: initialAddress } : null
  )

  // Use existing API endpoint for property data
  const { data, error, mutate } = useSWR(
    property?.address ? `/api/property?address=${encodeURIComponent(property.address)}` : null,
    fetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 10000 // Cache for 10 seconds
    }
  )

  // Merge API data with local property data
  useEffect(() => {
    if (data && property) {
      setPropertyState(prev => ({
        ...prev,
        ...data,
        address: prev?.address || data.address // Keep user-entered address
      }))
    }
  }, [data])

  const setProperty = (newProperty: PropertyData) => {
    setPropertyState(newProperty)
    // Trigger API call if address changed
    if (newProperty.address && newProperty.address !== property?.address) {
      mutate()
    }
  }

  const refreshProperty = () => {
    mutate()
  }

  return {
    property,
    isLoading: !error && !data && !!property?.address,
    error: error?.message || null,
    setProperty,
    refreshProperty
  }
}
EOF

echo "✅ Created property data hook"

# Step 2: Create assessment context bridge
echo ""
echo "Step 2: Creating assessment context bridge..."
echo "--------------------------------------------"

cat > hooks/new-ui/useAssessmentContext.ts << 'EOF'
import { useState, useEffect } from 'react'
import useSWR from 'swr'

interface AssessmentContext {
  propertyId?: number
  developmentType: string
  assessmentDate: Date
  versionId?: number
}

interface ComplianceResult {
  provision: string
  clause: string
  status: 'compliant' | 'non-compliant' | 'pending'
  details?: string
  requirement?: string
}

interface UseAssessmentContextReturn {
  context: AssessmentContext
  setContext: (context: Partial<AssessmentContext>) => void
  complianceResults: ComplianceResult[]
  isAssessing: boolean
  runAssessment: () => Promise<void>
  error: string | null
}

const fetcher = (url: string) => fetch(url).then(res => res.json())

export function useAssessmentContext(
  initialContext?: Partial<AssessmentContext>
): UseAssessmentContextReturn {
  const [context, setContextState] = useState<AssessmentContext>({
    developmentType: 'Dual Occupancy',
    assessmentDate: new Date(),
    ...initialContext
  })

  const [complianceResults, setComplianceResults] = useState<ComplianceResult[]>([])
  const [isAssessing, setIsAssessing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const setContext = (newContext: Partial<AssessmentContext>) => {
    setContextState(prev => ({ ...prev, ...newContext }))
  }

  const runAssessment = async () => {
    if (!context.propertyId) {
      setError('No property selected for assessment')
      return
    }

    setIsAssessing(true)
    setError(null)

    try {
      // Use existing compliance API
      const response = await fetch('/api/compliance/live-check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          propertyId: context.propertyId,
          developmentType: context.developmentType,
          versionId: context.versionId
        })
      })

      if (!response.ok) {
        throw new Error('Assessment failed')
      }

      const results = await response.json()
      setComplianceResults(results.checks || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Assessment failed')
    } finally {
      setIsAssessing(false)
    }
  }

  return {
    context,
    setContext,
    complianceResults,
    isAssessing,
    runAssessment,
    error
  }
}
EOF

echo "✅ Created assessment context hook"

# Step 3: Update PropertyCard to use state management
echo ""
echo "Step 3: Updating PropertyCard with state management..."
echo "-----------------------------------------------------"

cat > components/new-ui/core/property-card-connected.tsx << 'EOF'
"use client"

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { EnhancedGoogleAutocomplete } from '../autocomplete/google-autocomplete'
import { usePropertyData } from '@/hooks/new-ui/usePropertyData'
import { MapPin, Home, Layers, Ruler, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface PropertyCardConnectedProps {
  onPropertySelect?: (property: any) => void
  initialAddress?: string
}

export function PropertyCardConnected({
  onPropertySelect,
  initialAddress
}: PropertyCardConnectedProps) {
  const {
    property,
    isLoading,
    error,
    setProperty,
    refreshProperty
  } = usePropertyData(initialAddress)

  const handleAddressSelect = async (
    address: string,
    placeData: google.maps.places.PlaceResult
  ) => {
    if (!address) {
      setProperty({ address: '' })
      return
    }

    // Extract address components from Google Places
    const newProperty: any = { address }

    // Extract suburb for LGA
    const suburb = placeData.address_components?.find(c =>
      c.types.includes('locality')
    )?.long_name

    if (suburb) {
      newProperty.lga = getLGAFromSuburb(suburb)
    }

    // Set coordinates if available
    if (placeData.geometry?.location) {
      newProperty.lat = placeData.geometry.location.lat()
      newProperty.lng = placeData.geometry.location.lng()
    }

    setProperty(newProperty)
    onPropertySelect?.(newProperty)
  }

  const getLGAFromSuburb = (suburb: string): string => {
    const lgaMap: { [key: string]: string } = {
      'Sydney': 'City of Sydney',
      'Parramatta': 'City of Parramatta',
      'Chatswood': 'Willoughby City Council',
      'Bondi': 'Waverley Council',
      'Manly': 'Northern Beaches Council',
      'Liverpool': 'Liverpool City Council',
      'Blacktown': 'Blacktown City Council',
      'Penrith': 'Penrith City Council'
    }
    return lgaMap[suburb] || `${suburb} Council`
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-4">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <Home className="h-5 w-5" />
          Property Information
          {property?.address && (
            <Button
              variant="ghost"
              size="sm"
              onClick={refreshProperty}
              disabled={isLoading}
              className="ml-auto"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Address Input with Autocomplete */}
        <div>
          <label className="text-sm font-medium text-gray-700 mb-2 block">
            Property Address
          </label>
          <EnhancedGoogleAutocomplete
            placeholder="Start typing an address..."
            defaultValue={property?.address || ''}
            onAddressSelect={handleAddressSelect}
            className="w-full"
          />
        </div>

        {/* Error Display */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Property Details Grid */}
        {property?.address && (
          <div className="grid grid-cols-2 gap-4 pt-4 border-t">
            {/* Zone */}
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-sm text-gray-600">
                <Layers className="h-3 w-3" />
                <span>Zone</span>
              </div>
              <Badge variant="outline" className="font-medium">
                {isLoading ? 'Loading...' : property.zone || 'R2'}
              </Badge>
            </div>

            {/* Area */}
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-sm text-gray-600">
                <Ruler className="h-3 w-3" />
                <span>Area</span>
              </div>
              <p className="font-medium text-sm">
                {isLoading ? 'Loading...' : property.area || 'N/A'}
              </p>
            </div>

            {/* LGA */}
            <div className="space-y-1 col-span-2">
              <div className="flex items-center gap-1 text-sm text-gray-600">
                <MapPin className="h-3 w-3" />
                <span>Local Government Area</span>
              </div>
              <p className="font-medium text-sm">
                {isLoading ? 'Loading...' : property.lga || 'N/A'}
              </p>
            </div>

            {/* Property ID */}
            {property.propId && (
              <div className="space-y-1 col-span-2">
                <div className="text-sm text-gray-600">Property ID</div>
                <p className="font-medium text-sm">#{property.propId}</p>
              </div>
            )}

            {/* Lot/DP */}
            {property.lot && property.dpNumber && (
              <div className="space-y-1 col-span-2">
                <div className="text-sm text-gray-600">Lot/DP</div>
                <p className="font-medium text-sm">
                  Lot {property.lot} DP {property.dpNumber}
                </p>
              </div>
            )}

            {/* Land Value */}
            {property.landValue && (
              <div className="space-y-1 col-span-2">
                <div className="text-sm text-gray-600">Land Value</div>
                <p className="font-medium text-sm">${property.landValue}</p>
              </div>
            )}

            {/* Heritage */}
            {property.heritage && (
              <div className="col-span-2">
                <Badge variant="secondary" className="text-amber-700 bg-amber-100">
                  Heritage Item
                </Badge>
              </div>
            )}
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-4">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            <span className="ml-2 text-sm text-gray-600">Fetching property details...</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
EOF

echo "✅ Created connected PropertyCard component"

# Step 4: Create integrated assessment panel
echo ""
echo "Step 4: Creating integrated assessment panel..."
echo "----------------------------------------------"

cat > components/new-ui/panels/assessment-panel-connected.tsx << 'EOF'
"use client"

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { useAssessmentContext } from '@/hooks/new-ui/useAssessmentContext'
import { usePropertyData } from '@/hooks/new-ui/usePropertyData'
import { CheckCircle, XCircle, Clock, Play, AlertTriangle } from 'lucide-react'

interface AssessmentPanelConnectedProps {
  property?: any
}

export function AssessmentPanelConnected({ property }: AssessmentPanelConnectedProps) {
  const {
    context,
    setContext,
    complianceResults,
    isAssessing,
    runAssessment,
    error
  } = useAssessmentContext({
    propertyId: property?.propId
  })

  const developmentTypes = [
    'Dwelling House',
    'Dual Occupancy',
    'Multi Dwelling Housing',
    'Residential Flat Building',
    'Commercial Premises',
    'Mixed Use Development'
  ]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'compliant':
        return <CheckCircle className="w-4 h-4 text-green-600" />
      case 'non-compliant':
        return <XCircle className="w-4 h-4 text-red-600" />
      default:
        return <Clock className="w-4 h-4 text-yellow-600" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'compliant':
        return <Badge variant="default" className="bg-green-100 text-green-800">Compliant</Badge>
      case 'non-compliant':
        return <Badge variant="destructive">Non-Compliant</Badge>
      default:
        return <Badge variant="secondary">Pending</Badge>
    }
  }

  return (
    <div className="flex-1 p-6 overflow-y-auto">
      <div className="space-y-6">
        {/* Development Type Selection */}
        <Card>
          <CardHeader>
            <CardTitle>Development Assessment</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700 mb-2 block">
                Development Type
              </label>
              <Select
                value={context.developmentType}
                onValueChange={(value) => setContext({ developmentType: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {developmentTypes.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {property?.address && (
              <div className="pt-4 border-t">
                <p className="text-sm text-gray-600 mb-3">
                  Assessing: <span className="font-medium">{property.address}</span>
                </p>
                <Button
                  onClick={runAssessment}
                  disabled={isAssessing || !property?.propId}
                  className="w-full"
                >
                  {isAssessing ? (
                    <>
                      <Clock className="w-4 h-4 mr-2 animate-spin" />
                      Running Assessment...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4 mr-2" />
                      Run Compliance Assessment
                    </>
                  )}
                </Button>
              </div>
            )}

            {!property?.address && (
              <div className="pt-4 border-t">
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <AlertTriangle className="w-4 h-4" />
                  Please select a property to begin assessment
                </div>
              </div>
            )}

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Compliance Results */}
        {complianceResults.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Compliance Checklist</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {complianceResults.map((result, index) => (
                  <div key={index} className="border rounded-lg p-4">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <h4 className="font-medium text-sm">{result.provision}</h4>
                        <p className="text-xs text-gray-600 mt-1">{result.clause}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        {getStatusIcon(result.status)}
                        {getStatusBadge(result.status)}
                      </div>
                    </div>
                    {result.requirement && (
                      <p className="text-xs text-gray-700 mt-2">
                        <span className="font-medium">Requirement:</span> {result.requirement}
                      </p>
                    )}
                    {result.details && (
                      <p className="text-xs text-gray-700 mt-1">
                        <span className="font-medium">Details:</span> {result.details}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Assessment Summary */}
        {complianceResults.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Assessment Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {complianceResults.filter(r => r.status === 'compliant').length}
                  </div>
                  <div className="text-sm text-gray-600">Compliant</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">
                    {complianceResults.filter(r => r.status === 'non-compliant').length}
                  </div>
                  <div className="text-sm text-gray-600">Non-Compliant</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-yellow-600">
                    {complianceResults.filter(r => r.status === 'pending').length}
                  </div>
                  <div className="text-sm text-gray-600">Pending</div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
EOF

echo "✅ Created connected assessment panel"

# Step 5: Create integrated main page
echo ""
echo "Step 5: Creating fully integrated page..."
echo "----------------------------------------"

cat > app/ui-connected-test/page.tsx << 'EOF'
"use client"

import { useState } from "react"
import { Header } from "@/components/new-ui/common/header"
import { PropertyCardConnected } from "@/components/new-ui/core/property-card-connected"
import { AssessmentPanelConnected } from "@/components/new-ui/panels/assessment-panel-connected"

export default function UIConnectedTest() {
  const [selectedProperty, setSelectedProperty] = useState<any>(null)

  return (
    <div className="min-h-screen bg-white">
      <Header />
      <main className="flex flex-col md:flex-row h-[calc(100vh-80px)] pt-[80px]">
        {/* Property Panel */}
        <div className="w-full md:w-[380px] lg:w-[320px] xl:w-[380px] bg-white border-r border-gray-100 p-6 overflow-y-auto">
          <div className="space-y-8">
            <PropertyCardConnected
              onPropertySelect={setSelectedProperty}
              initialAddress=""
            />

            {/* Quick Stats */}
            {selectedProperty && (
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="font-medium text-sm mb-3">Property Status</h3>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span>Zone:</span>
                    <span className="font-medium">{selectedProperty.zone || 'R2'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>LGA:</span>
                    <span className="font-medium">{selectedProperty.lga || 'N/A'}</span>
                  </div>
                  {selectedProperty.heritage && (
                    <div className="flex justify-between">
                      <span>Heritage:</span>
                      <span className="font-medium text-amber-600">Yes</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Assessment Panel */}
        <AssessmentPanelConnected property={selectedProperty} />
      </main>
    </div>
  )
}
EOF

mkdir -p app/ui-connected-test
echo "✅ Created fully integrated test page at /ui-connected-test"

# Step 6: Update exports
echo ""
echo "Step 6: Updating component exports..."
echo "------------------------------------"

cat >> components/new-ui/index.ts << 'EOF'

// Connected components (with state management)
export { PropertyCardConnected } from './core/property-card-connected'
export { AssessmentPanelConnected } from './panels/assessment-panel-connected'
EOF

echo "✅ Updated component exports"

# Create summary
echo ""
echo "Creating PRP-M3 summary..."
cat > migratePRPs/results/prp_m3_summary.json << EOF
{
  "prp": "M3",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")",
  "components_created": [
    "usePropertyData.ts",
    "useAssessmentContext.ts",
    "property-card-connected.tsx",
    "assessment-panel-connected.tsx"
  ],
  "test_pages": [
    "/ui-connected-test"
  ],
  "apis_connected": [
    "/api/property",
    "/api/compliance/live-check"
  ],
  "status": "completed",
  "next_steps": [
    "Test state management at /ui-connected-test",
    "Verify API connections work",
    "Execute PRP-M4 for additional API layers"
  ]
}
EOF

echo ""
echo "🎉 PRP-M3 EXECUTION COMPLETE!"
echo "============================="
echo ""
echo "✅ State management hooks created"
echo "✅ Connected components with existing APIs"
echo "✅ Fully integrated test page created"
echo ""
echo "📋 Test URL:"
echo "   http://localhost:3007/ui-connected-test"
echo ""
echo "📋 Next: Execute PRP-M4 for additional API connections"