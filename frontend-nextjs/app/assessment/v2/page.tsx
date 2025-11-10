'use client';

/**
 * ASSESSMENT PAGE V2 - /assessment/v2
 *
 * Testing route for ComplianceDashboardV2 with Phase 2 APIs
 *
 * Two-column layout:
 * - Left (1/4): Property search + NSW Planning API data
 * - Right (3/4): ComplianceDashboardV2 with priority-based display
 *
 * Key Differences from V1:
 * - Uses /api/provisions/zone-applicability endpoint
 * - Priority-based grouping (Critical/Important/Reference)
 * - Lazy loading for low-priority provisions
 * - Cross-reference and control code inline display
 * - Database provisions only (no Planning API SEPP integration yet)
 */

import React, { useState } from 'react';
import { PropertySearch } from '@/components/property/PropertySearch';
import { ComplianceDashboardV2 } from '@/components/compliance/ComplianceDashboardV2';
import { PropertyDetailsComprehensive } from '@/components/property-details-comprehensive';

export default function AssessmentPageV2() {
  const [selectedAddress, setSelectedAddress] = useState('');
  const [selectedProperty, setSelectedProperty] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [developmentType, setDevelopmentType] = useState('dwelling_house');

  const handleAddressSelect = async (address: string) => {
    setSelectedAddress(address);
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/property?address=${encodeURIComponent(address)}`);
      if (response.ok) {
        const apiResponse = await response.json();
        if (apiResponse.success) {
          setSelectedProperty(apiResponse.data);
        } else {
          throw new Error(apiResponse.error || 'Failed to load property');
        }
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load property');
      setSelectedProperty(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                NSW Planning Assessment V2
              </h1>
              <p className="text-gray-600 mt-1">
                Testing Phase 2 APIs with priority-based display
              </p>
            </div>
            <div className="bg-blue-100 text-blue-800 text-xs px-3 py-1 rounded-full font-medium">
              V2 TESTING
            </div>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="bg-white border-b px-4 py-3">
        <div className="max-w-7xl mx-auto">
          <PropertySearch
            onAddressSelect={handleAddressSelect}
            selectedAddress={selectedAddress}
            loading={loading}
          />
        </div>
      </div>

      {/* Main Content - 2 Column Layout */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Left Panel - Property Card (1/4 width) */}
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-white border rounded-lg p-6 shadow-sm">
              <h3 className="text-lg font-semibold mb-4">Property Information</h3>

              {loading && (
                <div className="animate-pulse space-y-3">
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                  <div className="h-3 bg-gray-200 rounded"></div>
                  <div className="h-3 bg-gray-200 rounded w-3/4"></div>
                </div>
              )}

              {error && (
                <div className="text-red-600 text-sm">{error}</div>
              )}

              {!loading && !error && !selectedProperty && (
                <p className="text-gray-600 text-sm">Enter an address to load property data</p>
              )}

              {selectedProperty && (
                <div className="space-y-3">
                  <div>
                    <label className="text-sm text-gray-600">Address</label>
                    <p className="font-medium text-sm">{selectedProperty.address}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-gray-600">Zone</label>
                      <span className="block px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                        {selectedProperty.constraints?.zone || 'Unknown'}
                      </span>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Area</label>
                      <p className="font-medium text-sm">{selectedProperty.propertyArea || 'Unknown'}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-gray-600">LGA</label>
                      <p className="font-medium text-sm">{selectedProperty.constraints?.lga || 'Unknown'}</p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Heritage</label>
                      <p className="font-medium text-sm">{selectedProperty.heritage?.isHeritage ? 'Yes' : 'No'}</p>
                    </div>
                  </div>

                  {/* Development Type Selector */}
                  <div className="border-t pt-3">
                    <label className="text-sm text-gray-600 block mb-2">Development Type</label>
                    <select
                      value={developmentType}
                      onChange={(e) => setDevelopmentType(e.target.value)}
                      className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="dwelling_house">Dwelling House</option>
                      <option value="secondary_dwelling">Secondary Dwelling</option>
                      <option value="shop_top_housing">Shop Top Housing</option>
                      <option value="multi_dwelling">Multi Dwelling Housing</option>
                      <option value="residential_flat">Residential Flat Building</option>
                      <option value="boarding_house">Boarding House</option>
                      <option value="child_care">Child Care Centre</option>
                      <option value="commercial">Commercial Premises</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      Determines which DCP controls apply
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Planning API Data - All Layers */}
            {selectedProperty && (
              <PropertyDetailsComprehensive propertyData={selectedProperty} />
            )}
          </div>

          {/* Right Panel - ComplianceDashboardV2 (3/4 width) */}
          <div className="lg:col-span-3">
            {!selectedProperty && (
              <div className="bg-white border rounded-lg p-12 shadow-sm text-center">
                <h3 className="text-lg font-medium mb-2 text-gray-500">No Property Selected</h3>
                <p className="text-gray-600">Enter a property address to see compliance provisions</p>
                <div className="mt-4 text-sm text-blue-600">
                  <p className="font-medium">V2 Testing Features:</p>
                  <ul className="mt-2 space-y-1 text-left max-w-md mx-auto">
                    <li>✅ Priority-based grouping (Critical/Important/Reference)</li>
                    <li>✅ Lazy loading for low-priority provisions</li>
                    <li>✅ Cross-reference inline display with resolution</li>
                    <li>✅ Control code badges (C17, C18, etc.)</li>
                    <li>✅ Stats dashboard (provision counts by priority)</li>
                  </ul>
                </div>
              </div>
            )}

            {selectedProperty && (
              <ComplianceDashboardV2
                propertyData={selectedProperty}
                developmentType={developmentType}
                className="transition-all duration-300 ease-in-out"
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
