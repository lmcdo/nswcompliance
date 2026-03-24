"use client"

/**
 * Enhanced Assessment Dashboard Page
 * Integrates expert-friendly compliance dashboard with existing property search
 * Follows Universal Technical Implementation Specification
 */

import { useState, useEffect } from "react"
import { Header } from "@/components/header"
import { PropertyPanel } from "@/components/property-panel"
import { ComplianceDashboard } from "@/components/compliance/ComplianceDashboard"
import { DevelopmentSelector } from "@/components/development-selector"
import { SeppOverrideAlert } from "@/components/sepp/SeppOverrideAlert"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ArrowLeft } from "lucide-react"
import Link from "next/link"

export default function AssessmentDashboard() {
  const [selectedProperty, setSelectedProperty] = useState<string | null>(null)
  const [propertyData, setPropertyData] = useState<any>(null)
  const [developmentType, setDevelopmentType] = useState("dual_occupancy")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Listen for address selection to update property data
  useEffect(() => {
    const handleAddressSelected = async (event: CustomEvent) => {
      const address = event.detail
      console.log('Dashboard received address:', address)
      setSelectedProperty(address)
      setLoading(true)
      setError(null)

      // Fetch property data using real API
      try {
        const response = await fetch(`/api/property?address=${encodeURIComponent(address)}`)
        if (response.ok) {
          const apiResponse = await response.json()
          if (apiResponse.success) {
            const data = apiResponse.data
            setPropertyData(data)
            console.log('Property data loaded for dashboard:', data)
          } else {
            throw new Error(apiResponse.error || 'Failed to load property data')
          }
        } else {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
      } catch (error) {
        console.error('Failed to fetch property data:', error)
        setError(error instanceof Error ? error.message : 'Unknown error occurred')
        setPropertyData(null)
      } finally {
        setLoading(false)
      }
    }

    // Listen for custom address selection event
    document.addEventListener('addressSelected', handleAddressSelected as unknown as EventListener)

    return () => {
      document.removeEventListener('addressSelected', handleAddressSelected as unknown as EventListener)
    }
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <main className="container mx-auto px-4 py-8 space-y-6">
        {/* Navigation */}
        <div className="flex items-center gap-4">
          <Link href="/">
            <Button variant="outline" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Assessment
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Compliance Dashboard</h1>
            <p className="text-gray-600">Expert-friendly compliance analysis and provision review</p>
          </div>
        </div>

        {/* Property Search */}
        <Card>
          <CardHeader>
            <CardTitle>Property Selection</CardTitle>
          </CardHeader>
          <CardContent>
            <PropertyPanel
              selectedProperty={selectedProperty}
              onPropertySelect={setSelectedProperty}
            />
          </CardContent>
        </Card>

        {/* Development Type Selection */}
        {propertyData && (
          <Card>
            <CardHeader>
              <CardTitle>Development Context</CardTitle>
            </CardHeader>
            <CardContent>
              <DevelopmentSelector
                value={developmentType}
                onChange={setDevelopmentType}
                zoneCode={propertyData.constraints?.zone || ''}
              />
            </CardContent>
          </Card>
        )}

        {/* Loading State */}
        {loading && (
          <Card>
            <CardContent className="p-8 text-center">
              <div className="text-lg mb-2">Loading Property Data...</div>
              <div className="w-8 h-8 border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin mx-auto"></div>
            </CardContent>
          </Card>
        )}

        {/* Error State */}
        {error && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="p-6">
              <div className="text-red-800">
                <div className="font-medium">Error Loading Property Data</div>
                <div className="text-sm mt-1">{error}</div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* SEPP Override Alert - ALWAYS SHOW FOR DEMONSTRATION */}
        {propertyData && (
          <SeppOverrideAlert
            sepps={[
              'SEPP_HOUSING_2021',
              'SEPP_SUSTAINABLE_BUILDINGS_2022',
              'SEPP_TRANSPORT_INFRASTRUCTURE_2021',
              'SEPP_EXEMPT_COMPLYING_2008'
            ]}
            propertyData={propertyData}
          />
        )}

        {/* Compliance Dashboard - Main Feature */}
        {propertyData && !loading && !error && (
          <ComplianceDashboard
            propertyData={propertyData}
            className="transition-all duration-300 ease-in-out"
          />
        )}

      </main>
    </div>
  )
}