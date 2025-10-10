'use client';

/**
 * PRIMARY ASSESSMENT PAGE - /assessment
 *
 * Two-column layout:
 * - Left (1/4): Property search + NSW Planning API data (all layers with clickable URLs)
 * - Right (3/4): ComplianceDashboard showing unfiltered SEPP/LEP/DCP provisions from database
 *
 * Database integration:
 * - Queries regulatory_provisions table (up to 50 provisions per zone)
 * - Displays color-coded by authority level (SEPP=red, LEP=blue, DCP=green)
 * - Expandable cards show full legal text via /api/provisions/[id]/complete
 */

import React, { useState } from 'react';
import { PropertySearch } from '@/components/property/PropertySearch';
import { ComplianceDashboard } from '@/components/compliance/ComplianceDashboard';
import { PropertyDetailsComprehensive } from '@/components/property-details-comprehensive';

export default function AssessmentPage() {
  const [selectedAddress, setSelectedAddress] = useState('');
  const [selectedProperty, setSelectedProperty] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [developmentType, setDevelopmentType] = useState('dwelling_house');
  const [buildingHeight, setBuildingHeight] = useState<number | null>(null);

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
          <h1 className="text-2xl font-bold text-gray-900">
            NSW Planning Assessment
          </h1>
          <p className="text-gray-600 mt-1">
            Professional compliance assessment using real-time planning data
          </p>
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

                  {/* Building Height Input (conditional on multi-dwelling types) */}
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
                </div>
              )}
            </div>

            {/* Planning API Data - All Layers */}
            {selectedProperty && (
              <PropertyDetailsComprehensive propertyData={selectedProperty} />
            )}
          </div>

          {/* Right Panel - ComplianceDashboard with SEPP/LEP/DCP provisions (3/4 width) */}
          <div className="lg:col-span-3">
            {!selectedProperty && (
              <div className="bg-white border rounded-lg p-12 shadow-sm text-center">
                <h3 className="text-lg font-medium mb-2 text-gray-500">No Property Selected</h3>
                <p className="text-gray-600">Enter a property address to see compliance provisions</p>
              </div>
            )}

            {selectedProperty && (
              <ComplianceDashboard
                propertyData={selectedProperty}
                developmentType={developmentType}
                buildingHeight={buildingHeight}
                className="transition-all duration-300 ease-in-out"
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}