"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { MapPin, Home, Layers, Ruler, Building, DollarSign, BarChart3 } from "lucide-react"

interface PropertyData {
  propId?: number
  address: string
  zone?: string
  lga?: string
  area?: string
  lot?: string
  dpNumber?: string
  landValue?: string
  maxHeight?: number
  maxFsr?: number
}

export function PropertyCard() {
  const [address, setAddress] = useState("")
  const [property, setProperty] = useState<PropertyData>({ address: "" })
  const [isLoading, setIsLoading] = useState(false)

  const fetchPropertyData = async (addr: string) => {
    if (!addr) return

    setIsLoading(true)
    try {
      const response = await fetch(`/api/property?address=${encodeURIComponent(addr)}`)
      if (response.ok) {
        const apiResponse = await response.json()
        const data = apiResponse.data

        // Map API response to PropertyCard format
        const mappedData = {
          propId: data.propId,
          address: data.address,
          area: data.propertyArea, // Map propertyArea to area
          zone: data.constraints?.zone, // Map from constraints
          lga: data.constraints?.lga, // Map from constraints
          landValue: data.landValue, // Land value
          maxHeight: data.constraints?.maxHeight, // Max height
          maxFsr: data.constraints?.maxFsr, // Floor space ratio
        }

        setProperty(prev => ({ ...prev, ...mappedData }))
        console.log('🏠 PropertyCard updated with data:', mappedData)
      }
    } catch (error) {
      console.error('Failed to fetch property data:', error)
    }
    setIsLoading(false)
  }

  useEffect(() => {
    if (address) {
      fetchPropertyData(address)
    }
  }, [address])

  // Listen for address selection from header
  useEffect(() => {
    const handleAddressSelected = (event: CustomEvent) => {
      const newAddress = event.detail
      console.log('🏠 PropertyCard received address event:', newAddress)
      setAddress(newAddress)
    }

    console.log('🎧 PropertyCard setting up event listener for addressSelected')
    window.addEventListener('addressSelected', handleAddressSelected as EventListener)
    return () => {
      window.removeEventListener('addressSelected', handleAddressSelected as EventListener)
    }
  }, [])


  return (
    <Card className="shadow-sm border border-gray-200 bg-white">
      <CardContent className="p-6 space-y-4">
        <div>
          <label className="text-sm font-medium text-gray-700 mb-2 block">
            Current Property
          </label>
          <div className="p-3 bg-gray-50 rounded-md border">
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-gray-400" />
              <span className="text-sm font-medium text-gray-900">
                {address || 'No property selected'}
              </span>
            </div>
            {isLoading && (
              <div className="text-xs text-gray-500 mt-1">Loading property data...</div>
            )}
          </div>
          <div className="text-xs text-gray-500 mt-2 text-center">
            Use the search bar above to find a property
          </div>
        </div>

        {address && property.area && (
          <div className="space-y-4 pt-4 border-t">
            {/* Property data pills in grid */}
            <div className="grid grid-cols-2 gap-3">
              {/* Zone pill */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <Layers className="h-4 w-4 text-blue-600" />
                  <span className="text-xs font-medium text-blue-900">Zone</span>
                </div>
                <div className="text-sm font-semibold text-blue-900">
                  {property.zone || 'R2'}
                </div>
              </div>

              {/* Area pill */}
              <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <Ruler className="h-4 w-4 text-green-600" />
                  <span className="text-xs font-medium text-green-900">Area</span>
                </div>
                <div className="text-sm font-semibold text-green-900">
                  {property.area || '650 sqm'}
                </div>
              </div>

              {/* Land Value pill */}
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <DollarSign className="h-4 w-4 text-yellow-600" />
                  <span className="text-xs font-medium text-yellow-900">Land Value</span>
                </div>
                <div className="text-sm font-semibold text-yellow-900">
                  {property.landValue || 'N/A'}
                </div>
              </div>

              {/* Max Height pill */}
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <Building className="h-4 w-4 text-purple-600" />
                  <span className="text-xs font-medium text-purple-900">Max Height</span>
                </div>
                <div className="text-sm font-semibold text-purple-900">
                  {property.maxHeight ? `${property.maxHeight}m` : 'N/A'}
                </div>
              </div>

              {/* Max FSR pill */}
              <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <BarChart3 className="h-4 w-4 text-indigo-600" />
                  <span className="text-xs font-medium text-indigo-900">Max FSR</span>
                </div>
                <div className="text-sm font-semibold text-indigo-900">
                  {property.maxFsr ? `${property.maxFsr}:1` : 'N/A'}
                </div>
              </div>

              {/* LGA pill */}
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <MapPin className="h-4 w-4 text-gray-600" />
                  <span className="text-xs font-medium text-gray-900">LGA</span>
                </div>
                <div className="text-sm font-semibold text-gray-900">
                  {property.lga || 'Inner West Council'}
                </div>
              </div>
            </div>

            {/* Property ID if available */}
            {property.propId && (
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 mt-3">
                <div className="text-xs font-medium text-slate-900 mb-1">Property ID</div>
                <div className="text-sm font-semibold text-slate-900">#{property.propId}</div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
