#!/bin/bash
# PRP-M2: Google Autocomplete Integration
# Integrates Google Places Autocomplete into the new UI components

set -e  # Exit on error

echo "🚀 Executing PRP-M2: Google Autocomplete Integration"
echo "===================================================="

# Navigate to project root
cd "$(dirname "$0")/../.."
PROJECT_ROOT=$(pwd)
echo "📁 Project root: $PROJECT_ROOT"

# Step 1: Check for Google Maps API key
echo ""
echo "Step 1: Checking for Google Maps API configuration..."
echo "----------------------------------------------------"

API_KEY_FOUND=false

# Check .env file first
if [ -f ".env" ]; then
    if grep -q "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY" .env; then
        echo "✅ Google Maps API key found in .env"
        API_KEY_FOUND=true
    fi
fi

# Check .env.local as fallback
if [ "$API_KEY_FOUND" = false ] && [ -f ".env.local" ]; then
    if grep -q "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY" .env.local; then
        echo "✅ Google Maps API key found in .env.local"
        API_KEY_FOUND=true
    fi
fi

if [ "$API_KEY_FOUND" = false ]; then
    echo "⚠️ Google Maps API key not found in .env or .env.local"
    echo "ℹ️ Add NEXT_PUBLIC_GOOGLE_MAPS_API_KEY to your .env file"
    echo ""
    echo "Example:"
    echo "NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_api_key_here"
fi

# Step 2: Install Google Maps dependencies
echo ""
echo "Step 2: Installing Google Maps dependencies..."
echo "--------------------------------------------"

npm install --save @googlemaps/js-api-loader @types/google.maps
echo "✅ Google Maps dependencies installed"

# Step 3: Create Google Autocomplete component
echo ""
echo "Step 3: Creating Google Autocomplete component..."
echo "------------------------------------------------"

mkdir -p components/new-ui/autocomplete

cat > components/new-ui/autocomplete/google-autocomplete.tsx << 'EOF'
"use client"

import React, { useEffect, useRef, useState, useCallback } from 'react'
import { Loader } from '@googlemaps/js-api-loader'
import { Input } from '@/components/ui/input'
import { MapPin, X } from 'lucide-react'

interface GoogleAutocompleteProps {
  onAddressSelect?: (address: string, placeData: google.maps.places.PlaceResult) => void
  placeholder?: string
  defaultValue?: string
  className?: string
  required?: boolean
  disabled?: boolean
}

export function GoogleAutocomplete({
  onAddressSelect,
  placeholder = "Enter property address...",
  defaultValue = "",
  className = "",
  required = false,
  disabled = false
}: GoogleAutocompleteProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const autocompleteRef = useRef<google.maps.places.Autocomplete | null>(null)
  const [value, setValue] = useState(defaultValue)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Initialize Google Maps Autocomplete
  useEffect(() => {
    const initAutocomplete = async () => {
      try {
        setIsLoading(true)
        setError(null)

        const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
        if (!apiKey) {
          throw new Error('Google Maps API key not configured')
        }

        const loader = new Loader({
          apiKey,
          version: 'weekly',
          libraries: ['places']
        })

        await loader.load()

        if (inputRef.current && !autocompleteRef.current) {
          // Create autocomplete instance
          autocompleteRef.current = new google.maps.places.Autocomplete(
            inputRef.current,
            {
              componentRestrictions: { country: 'au' }, // Restrict to Australia
              fields: [
                'address_components',
                'formatted_address',
                'geometry',
                'place_id',
                'name',
                'types'
              ],
              types: ['address'] // Focus on addresses
            }
          )

          // Add place changed listener
          autocompleteRef.current.addListener('place_changed', () => {
            const place = autocompleteRef.current?.getPlace()

            if (place && place.formatted_address) {
              setValue(place.formatted_address)
              onAddressSelect?.(place.formatted_address, place)

              // Extract useful address components
              const components = extractAddressComponents(place)
              console.log('Address components:', components)
            }
          })
        }

        setIsLoading(false)
      } catch (err) {
        console.error('Failed to initialize Google Autocomplete:', err)
        setError(err instanceof Error ? err.message : 'Failed to load Google Maps')
        setIsLoading(false)
      }
    }

    initAutocomplete()

    // Cleanup
    return () => {
      if (autocompleteRef.current) {
        google.maps.event.clearInstanceListeners(autocompleteRef.current)
      }
    }
  }, [onAddressSelect])

  // Extract address components helper
  const extractAddressComponents = (place: google.maps.places.PlaceResult) => {
    const components: any = {}

    if (place.address_components) {
      place.address_components.forEach((component) => {
        const types = component.types

        if (types.includes('street_number')) {
          components.streetNumber = component.long_name
        }
        if (types.includes('route')) {
          components.streetName = component.long_name
        }
        if (types.includes('locality')) {
          components.suburb = component.long_name
        }
        if (types.includes('administrative_area_level_1')) {
          components.state = component.short_name
        }
        if (types.includes('postal_code')) {
          components.postcode = component.long_name
        }
      })
    }

    if (place.geometry?.location) {
      components.lat = place.geometry.location.lat()
      components.lng = place.geometry.location.lng()
    }

    return components
  }

  // Clear input
  const handleClear = useCallback(() => {
    setValue('')
    if (inputRef.current) {
      inputRef.current.value = ''
      inputRef.current.focus()
    }
    onAddressSelect?.('', {} as google.maps.places.PlaceResult)
  }, [onAddressSelect])

  // Handle manual input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value)
  }

  return (
    <div className="relative">
      <div className="relative">
        <MapPin className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
        <Input
          ref={inputRef}
          type="text"
          value={value}
          onChange={handleInputChange}
          placeholder={placeholder}
          className={`pl-10 pr-10 ${className}`}
          required={required}
          disabled={disabled || isLoading}
          autoComplete="off"
        />
        {value && !disabled && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
            aria-label="Clear address"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Loading indicator */}
      {isLoading && (
        <div className="absolute right-10 top-1/2 transform -translate-y-1/2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="absolute top-full left-0 mt-1 text-xs text-red-500">
          {error}
        </div>
      )}

      {/* NSW-specific hint */}
      <div className="mt-1 text-xs text-gray-500">
        Start typing an address in NSW, Australia
      </div>
    </div>
  )
}

// Enhanced version with dropdown suggestions styling
export function EnhancedGoogleAutocomplete(props: GoogleAutocompleteProps) {
  useEffect(() => {
    // Add custom styles for Google autocomplete dropdown
    const style = document.createElement('style')
    style.innerHTML = `
      .pac-container {
        font-family: 'Inter', system-ui, sans-serif;
        border-radius: 8px;
        margin-top: 4px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        border: 1px solid #e5e7eb;
      }
      .pac-item {
        padding: 12px;
        font-size: 14px;
        border-bottom: 1px solid #f3f4f6;
      }
      .pac-item:hover {
        background-color: #f9fafb;
      }
      .pac-item-selected {
        background-color: #eff6ff;
      }
      .pac-matched {
        font-weight: 600;
        color: #2563eb;
      }
      .pac-item-query {
        color: #111827;
      }
    `
    document.head.appendChild(style)

    return () => {
      document.head.removeChild(style)
    }
  }, [])

  return <GoogleAutocomplete {...props} />
}
EOF

echo "✅ Created Google Autocomplete component"

# Step 4: Create integrated PropertyCard with autocomplete
echo ""
echo "Step 4: Creating enhanced PropertyCard with autocomplete..."
echo "---------------------------------------------------------"

cat > components/new-ui/core/property-card-enhanced.tsx << 'EOF'
"use client"

import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { EnhancedGoogleAutocomplete } from '../autocomplete/google-autocomplete'
import { MapPin, Home, Layers, Ruler } from 'lucide-react'

interface PropertyData {
  address: string
  zone?: string
  lga?: string
  area?: string
  lot?: string
  dpNumber?: string
  lat?: number
  lng?: number
}

interface PropertyCardEnhancedProps {
  onPropertySelect?: (property: PropertyData) => void
  initialProperty?: PropertyData
}

export function PropertyCardEnhanced({
  onPropertySelect,
  initialProperty
}: PropertyCardEnhancedProps) {
  const [property, setProperty] = useState<PropertyData>(
    initialProperty || { address: '' }
  )
  const [isLoading, setIsLoading] = useState(false)

  const handleAddressSelect = async (
    address: string,
    placeData: google.maps.places.PlaceResult
  ) => {
    if (!address) {
      setProperty({ address: '' })
      return
    }

    setIsLoading(true)

    // Extract address components
    const updatedProperty: PropertyData = { address }

    // Extract suburb for LGA
    const suburb = placeData.address_components?.find(c =>
      c.types.includes('locality')
    )?.long_name

    if (suburb) {
      // Map suburb to LGA (simplified - in production, use proper mapping)
      updatedProperty.lga = getLGAFromSuburb(suburb)
    }

    // Set coordinates if available
    if (placeData.geometry?.location) {
      updatedProperty.lat = placeData.geometry.location.lat()
      updatedProperty.lng = placeData.geometry.location.lng()
    }

    // Fetch additional property data from API
    try {
      const response = await fetch(`/api/property?address=${encodeURIComponent(address)}`)
      if (response.ok) {
        const data = await response.json()
        Object.assign(updatedProperty, {
          zone: data.zone || 'R2',
          area: data.area || 'Loading...',
          lot: data.lot || 'Loading...',
          dpNumber: data.dpNumber || 'Loading...'
        })
      } else {
        // Use defaults if API fails
        Object.assign(updatedProperty, {
          zone: 'R2',
          area: 'N/A',
          lot: 'N/A',
          dpNumber: 'N/A'
        })
      }
    } catch (error) {
      console.error('Failed to fetch property data:', error)
      // Use defaults
      Object.assign(updatedProperty, {
        zone: 'R2',
        area: 'N/A',
        lot: 'N/A',
        dpNumber: 'N/A'
      })
    }

    setProperty(updatedProperty)
    onPropertySelect?.(updatedProperty)
    setIsLoading(false)
  }

  // Helper function to map suburb to LGA
  const getLGAFromSuburb = (suburb: string): string => {
    // Simplified mapping - in production, use comprehensive database
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
            defaultValue={property.address}
            onAddressSelect={handleAddressSelect}
            className="w-full"
          />
        </div>

        {/* Property Details Grid */}
        {property.address && (
          <div className="grid grid-cols-2 gap-4 pt-4 border-t">
            {/* Zone */}
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-sm text-gray-600">
                <Layers className="h-3 w-3" />
                <span>Zone</span>
              </div>
              <Badge variant="outline" className="font-medium">
                {isLoading ? 'Loading...' : property.zone || 'N/A'}
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

            {/* Lot/DP */}
            {property.lot && property.dpNumber && (
              <div className="space-y-1 col-span-2">
                <div className="text-sm text-gray-600">Lot/DP</div>
                <p className="font-medium text-sm">
                  Lot {property.lot} DP {property.dpNumber}
                </p>
              </div>
            )}

            {/* Coordinates (hidden by default) */}
            {property.lat && property.lng && (
              <div className="col-span-2 text-xs text-gray-500">
                Coordinates: {property.lat.toFixed(6)}, {property.lng.toFixed(6)}
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

echo "✅ Created enhanced PropertyCard with autocomplete"

# Step 5: Create Google Maps script loader
echo ""
echo "Step 5: Creating Google Maps script loader..."
echo "--------------------------------------------"

cat > app/layout-google-maps.tsx << 'EOF'
import Script from 'next/script'

export function GoogleMapsProvider({ children }: { children: React.ReactNode }) {
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY

  if (!apiKey) {
    console.warn('Google Maps API key not configured')
  }

  return (
    <>
      {apiKey && (
        <Script
          id="google-maps"
          strategy="afterInteractive"
          src={`https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places`}
        />
      )}
      {children}
    </>
  )
}
EOF

echo "✅ Created Google Maps script loader"

# Step 6: Create test page with autocomplete
echo ""
echo "Step 6: Creating test page with autocomplete..."
echo "----------------------------------------------"

cat > app/autocomplete-test/page.tsx << 'EOF'
"use client"

import { useState } from "react"
import { PropertyCardEnhanced } from "@/components/new-ui/core/property-card-enhanced"

export default function AutocompleteTest() {
  const [selectedProperty, setSelectedProperty] = useState<any>(null)

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-8">
          Google Autocomplete Integration Test
        </h1>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Property Card with Autocomplete */}
          <div>
            <PropertyCardEnhanced onPropertySelect={setSelectedProperty} />
          </div>

          {/* Selected Property Display */}
          <div>
            {selectedProperty && (
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h2 className="text-lg font-semibold mb-4">Selected Property Data</h2>
                <pre className="text-xs bg-gray-100 p-4 rounded overflow-auto">
                  {JSON.stringify(selectedProperty, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>

        {/* Instructions */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="font-semibold text-blue-900 mb-2">Testing Instructions</h3>
          <ul className="space-y-1 text-sm text-blue-800">
            <li>• Start typing an NSW address in the property card</li>
            <li>• Select an address from the dropdown suggestions</li>
            <li>• Property details will be fetched automatically</li>
            <li>• The selected property data will appear on the right</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
EOF

mkdir -p app/autocomplete-test
echo "✅ Created autocomplete test page at /autocomplete-test"

# Step 7: Update exports
echo ""
echo "Step 7: Updating component exports..."
echo "------------------------------------"

cat >> components/new-ui/index.ts << 'EOF'

// Autocomplete components
export { GoogleAutocomplete, EnhancedGoogleAutocomplete } from './autocomplete/google-autocomplete'
export { PropertyCardEnhanced } from './core/property-card-enhanced'
EOF

echo "✅ Updated component exports"

# Create summary
echo ""
echo "Creating PRP-M2 summary..."
cat > migratePRPs/results/prp_m2_summary.json << EOF
{
  "prp": "M2",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")",
  "components_created": [
    "google-autocomplete.tsx",
    "property-card-enhanced.tsx",
    "layout-google-maps.tsx"
  ],
  "test_pages": [
    "/autocomplete-test",
    "/new-ui-test"
  ],
  "status": "completed",
  "next_steps": [
    "Add Google Maps API key to .env.local",
    "Test autocomplete at /autocomplete-test",
    "Verify NSW address suggestions work",
    "Execute PRP-M3 for state management"
  ]
}
EOF

echo ""
echo "🎉 PRP-M2 EXECUTION COMPLETE!"
echo "============================="
echo ""
echo "✅ Google Maps dependencies installed"
echo "✅ Autocomplete component created"
echo "✅ Enhanced PropertyCard with autocomplete"
echo "✅ Test pages created"
echo ""
echo "⚠️ IMPORTANT: Add your Google Maps API key to .env.local:"
echo "   NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_api_key_here"
echo ""
echo "📋 Test URLs:"
echo "   http://localhost:3007/autocomplete-test"
echo "   http://localhost:3007/new-ui-test"
echo ""
echo "📋 Next: Execute PRP-M3 for state management bridge"